/**
 * KILROY Universal Shell — browser engine (POSIX · CMD · PowerShell · BSD · same shit).
 */
(function (global) {
  "use strict";

  var COMMANDS = [
    { id: "list_dir", aliases: ["ls", "dir", "gci", "get-childitem"], posix: "ls", builtin: true },
    { id: "print", aliases: ["echo", "write-output", "write-host"], posix: "echo", builtin: true },
    { id: "cat", aliases: ["cat", "type", "get-content", "gc"], posix: "cat", builtin: true },
    { id: "pwd", aliases: ["pwd", "get-location", "gl"], posix: "pwd", builtin: true },
    { id: "cd", aliases: ["cd", "chdir", "set-location", "sl"], posix: "cd", builtin: true },
    { id: "clear", aliases: ["clear", "cls", "clear-host", "reset"], posix: "clear", builtin: true },
    { id: "whoami", aliases: ["whoami"], posix: "whoami", builtin: true },
    { id: "hostname", aliases: ["hostname"], posix: "hostname", builtin: true },
    { id: "uname", aliases: ["uname", "ver", "sw_vers"], posix: "uname", builtin: true },
    { id: "mkdir", aliases: ["mkdir", "md", "new-item"], posix: "mkdir", builtin: true },
    { id: "help", aliases: ["help", "?", "man"], posix: "help", builtin: true },
    { id: "kilroy_status", aliases: ["kilroy", "kilroy-status", "kernel"], posix: "kilroy-status", builtin: true },
    { id: "source_tree", aliases: ["source", "tree"], posix: "source", builtin: true },
    { id: "date", aliases: ["date", "get-date"], posix: "date", builtin: false },
    { id: "which", aliases: ["which", "where", "where.exe", "get-command", "gcm"], posix: "which", builtin: false },
    { id: "grep", aliases: ["grep", "findstr", "rg", "select-string", "sls"], posix: "grep", builtin: false },
    { id: "find", aliases: ["find", "locate"], posix: "find", builtin: false },
    { id: "copy", aliases: ["cp", "copy", "copy-item", "cpi"], posix: "cp", builtin: false },
    { id: "move", aliases: ["mv", "move", "ren", "rename", "move-item", "mi"], posix: "mv", builtin: false },
    { id: "remove", aliases: ["rm", "del", "erase", "remove-item", "ri"], posix: "rm", builtin: false },
    { id: "git", aliases: ["git"], posix: "git", builtin: false },
    { id: "python", aliases: ["python", "python3", "pythong", "py"], posix: "python3", builtin: false },
  ];

  var INDEX = {};
  COMMANDS.forEach(function (row) {
    (row.aliases || []).forEach(function (a) {
      INDEX[a.toLowerCase()] = row;
    });
    if (row.posix) INDEX[row.posix.toLowerCase()] = row;
  });

  function tokenize(line) {
    var parts = [];
    var cur = "";
    var q = null;
    for (var i = 0; i < line.length; i++) {
      var c = line[i];
      if (q) {
        if (c === q) q = null;
        else cur += c;
        continue;
      }
      if (c === '"' || c === "'") {
        q = c;
        continue;
      }
      if (/\s/.test(c)) {
        if (cur) {
          parts.push(cur);
          cur = "";
        }
        continue;
      }
      cur += c;
    }
    if (cur) parts.push(cur);
    return parts;
  }

  function guessFamily(raw, row) {
    var low = raw.toLowerCase();
    if (["dir", "type", "cls", "copy", "del", "erase", "md", "chdir", "ren", "findstr", "ver"].indexOf(low) >= 0) return "cmd";
    if (low.indexOf("get-") === 0 || ["gci", "gc", "sls", "gcm"].indexOf(low) >= 0) return "powershell";
    return "posix";
  }

  function resolveLine(line) {
    var parts = tokenize((line || "").trim());
    if (!parts.length) return { ok: false, error: "empty" };
    var raw = parts[0];
    var key = raw.toLowerCase().replace(/\.exe$/, "");
    var row = INDEX[key];
    if (!row) {
      return { ok: true, canonical: null, argv: parts, posixArgv: parts, posixLine: line, builtin: false };
    }
    var posixArgv = [row.posix].concat(parts.slice(1));
    return {
      ok: true,
      canonical: row.id,
      argv: parts,
      posixArgv: posixArgv,
      posixLine: posixArgv.join(" "),
      builtin: !!row.builtin,
      family: guessFamily(raw, row),
      label: row.id,
    };
  }

  function runVfsBuiltin(canonical, argv, ctx) {
    var vfs = ctx.vfs;
    var args = argv.slice(1);
    if (!vfs) return null;

    if (canonical === "list_dir") {
      var showAll = args.indexOf("-a") >= 0 || args.indexOf("-la") >= 0;
      var r = vfs.resolve(vfs.root, ctx.cwd, ".");
      if (r.err) return { ok: false, output: r.err };
      return {
        ok: true,
        output: vfs
          .listEntries(r.node, showAll)
          .map(function (e) {
            var mark = e.node && e.node.t === "d" ? "/" : e.node && e.node.t === "l" ? "@" : "";
            return e.name + mark;
          })
          .join("  "),
      };
    }
    if (canonical === "pwd") return { ok: true, output: ctx.cwd };
    if (canonical === "cat") {
      if (!args[0]) return { ok: false, output: "usage: cat <path>  (also: type, get-content)" };
      var cr = vfs.resolve(vfs.root, ctx.cwd, args[0]);
      if (cr.err) return { ok: false, output: cr.err };
      return { ok: true, output: vfs.read(cr.node) };
    }
    if (canonical === "cd") {
      var target = args[0] || "/home/kilroy";
      var rr = vfs.resolve(vfs.root, ctx.cwd, target);
      if (rr.err) return { ok: false, output: rr.err };
      if (rr.node.t !== "d") return { ok: false, output: "not a directory" };
      ctx.cwd = rr.path;
      return { ok: true, output: "", cwd: ctx.cwd };
    }
    if (canonical === "print") return { ok: true, output: args.join(" ") };
    if (canonical === "clear") return { ok: true, clear: true };
    if (canonical === "whoami") return { ok: true, output: "kilroy" };
    if (canonical === "hostname") return { ok: true, output: "kilroy-pages" };
    if (canonical === "uname" || canonical === "ver") {
      return { ok: true, output: "KILROY Field OS 1.1.0 Sanctuary (universal shell · Pages)" };
    }
    if (canonical === "kilroy_status") {
      return {
        ok: true,
        output: [
          "mode=universal_shell",
          "vfs=browser",
          "authority=github.io",
          "compat=POSIX,CMD,PowerShell,GNU,BSD",
          "source=github.com/ZacharyGeurts/KILROY",
        ].join("\n"),
      };
    }
    if (canonical === "source_tree") return { ok: true, output: "see Source panel · GitHub API tree" };
    if (canonical === "help") {
      var lines = ["KILROY Universal CLI — same name, same shit", ""];
      COMMANDS.forEach(function (row) {
        lines.push("  " + row.id + "  " + (row.aliases || []).slice(0, 5).join(", "));
      });
      return { ok: true, output: lines.join("\n") };
    }
    return null;
  }

  function execLine(line, ctx) {
    var res = resolveLine(line);
    if (!res.ok) return { ok: false, output: res.error || "parse error" };
    if (res.builtin && ctx.vfs) {
      var built = runVfsBuiltin(res.canonical, res.argv, ctx);
      if (built) {
        built.resolved = res;
        return built;
      }
    }
    return { ok: true, delegate: true, posixLine: res.posixLine || line, resolved: res };
  }

  global.KilroyUniversalShell = {
    COMMANDS: COMMANDS,
    resolveLine: resolveLine,
    execLine: execLine,
    runVfsBuiltin: runVfsBuiltin,
  };
})(typeof window !== "undefined" ? window : globalThis);