"""Queen Forge engine — logging, subprocess streaming, tool dispatch."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class ForgeContext:
    queen: Path
    install: Path
    state: Path
    jobs: int = field(default_factory=lambda: max(1, os.cpu_count() or 4))

    @classmethod
    def from_env(cls) -> ForgeContext:
        queen = Path(__file__).resolve().parents[2]
        install = Path(os.environ.get("NEXUS_INSTALL_ROOT", queen))
        state = Path(os.environ.get("NEXUS_STATE_DIR", queen / ".nexus-state"))
        jobs = int(os.environ.get("QUEEN_BUILD_JOBS", max(1, os.cpu_count() or 4)))
        return cls(queen=queen, install=install, state=state, jobs=jobs)

    @property
    def nl(self) -> Path:
        return self.queen.parent

    @property
    def rtx(self) -> Path:
        link = self.queen / "engine/AMOURANTHRTX"
        if link.is_dir() or link.is_symlink():
            return link.resolve()
        return self.nl / "AMOURANTHRTX"

    @property
    def build(self) -> Path:
        return self.queen / "build/rtx"

    @property
    def preset(self) -> Path:
        return self.queen / "cmake/queen-inside.cmake"

    @property
    def vendor(self) -> Path:
        return self.queen / "vendor"

    @property
    def deps(self) -> Path:
        return self.queen / "vendor/deps"

    @property
    def forge_log(self) -> Path:
        return self.queen / ".queen-forge.log"

    @property
    def state_log(self) -> Path:
        return self.state / "queen-build.log"

    def env(self) -> dict[str, str]:
        sg = self.queen.parent.parent
        return {
            **os.environ,
            "SG_ROOT": os.environ.get("SG_ROOT", str(sg)),
            "NEXUS_INSTALL_ROOT": str(self.install),
            "NEXUS_STATE_DIR": str(self.state),
            "QUEEN_ROOT": str(self.queen),
            "KILROY_ROOT": os.environ.get("KILROY_ROOT", str(sg / "KILROY")),
            "AMOURANTHRTX_ROOT": os.environ.get("AMOURANTHRTX_ROOT", str(self.rtx)),
            "QUEEN_BUILD_JOBS": str(self.jobs),
            "PKG_CONFIG_PATH": os.environ.get(
                "PKG_CONFIG_PATH", "/usr/local/lib/pkgconfig:"
            ),
        }


@dataclass
class ForgeResult:
    ok: bool
    tool: str
    message: str = ""
    returncode: int = 0
    tail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "tool": self.tool,
            "message": self.message,
            "returncode": self.returncode,
            "tail": self.tail[-4000:] if self.tail else "",
        }


ToolFn = Callable[[ForgeContext, "ForgeEngine"], ForgeResult]
CheckFn = Callable[[ForgeContext], bool]


@dataclass
class ForgeTool:
    id: str
    label: str
    track: str
    run: ToolFn
    check: CheckFn
    optional: bool = False
    replaces: str = ""
    kind: str = "core"


class ForgeEngine:
    def __init__(self, ctx: ForgeContext | None = None) -> None:
        self.ctx = ctx or ForgeContext.from_env()
        self._buffers: list[str] = []

    def log(self, line: str) -> None:
        stamp = f"[{_now()}] {line}"
        self._buffers.append(stamp)
        print(stamp, file=sys.stderr, flush=True)
        for path in (self.ctx.forge_log, self.ctx.state_log):
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as f:
                f.write(stamp + "\n")

    def clear_log(self) -> None:
        for path in (self.ctx.forge_log, self.ctx.state_log):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("", encoding="utf-8")
        self._buffers.clear()

    def which(self, name: str) -> str | None:
        return shutil.which(name)

    def run(
        self,
        cmd: list[str],
        *,
        cwd: Path | None = None,
        env: dict[str, str] | None = None,
        timeout: int | None = None,
        check: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        self.log(f"$ {' '.join(cmd)}")
        proc = subprocess.run(
            cmd,
            cwd=str(cwd or self.ctx.queen),
            env=env or self.ctx.env(),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        for stream in (proc.stdout, proc.stderr):
            if stream:
                for line in stream.splitlines():
                    self.log(line)
        if check and proc.returncode != 0:
            raise subprocess.CalledProcessError(proc.returncode, cmd, proc.stdout, proc.stderr)
        return proc

    def run_stream(
        self,
        cmd: list[str],
        *,
        cwd: Path | None = None,
        env: dict[str, str] | None = None,
        timeout: int | None = None,
    ) -> int:
        self.log(f"$ {' '.join(cmd)}")
        proc = subprocess.Popen(
            cmd,
            cwd=str(cwd or self.ctx.queen),
            env=env or self.ctx.env(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        assert proc.stdout is not None
        try:
            for line in proc.stdout:
                self.log(line.rstrip("\n"))
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            self.log("TIMEOUT — process killed")
            return 124
        return proc.returncode or 0

    def link_or_copy(self, src: Path, dst: Path) -> bool:
        if not src.exists():
            self.log(f"skip missing {src}")
            return False
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists() or dst.is_symlink():
            self.log(f"ok {dst}")
            return True
        dst.symlink_to(src.resolve())
        self.log(f"link {dst}")
        return True

    def symlink_dep(self, name: str, srcname: str) -> bool:
        cache = self.ctx.build / "_deps"
        src = cache / srcname
        dst = self.ctx.deps / name
        if src.is_dir():
            dst.parent.mkdir(parents=True, exist_ok=True)
            if dst.is_symlink() or dst.is_dir():
                dst.unlink(missing_ok=True)
            dst.symlink_to(src.resolve())
            self.log(f"  {name} ← {srcname}")
            return True
        if dst.is_symlink() or dst.is_dir():
            if dst.exists() and (dst.resolve() / "CMakeLists.txt").is_file():
                self.log(f"  {name} (already staged)")
                return True
            dst.unlink(missing_ok=True)
        self.log(f"  WARN: missing {srcname}")
        return False

    def tail_buffer(self, n: int = 4000) -> str:
        text = "\n".join(self._buffers)
        return text[-n:] if len(text) > n else text