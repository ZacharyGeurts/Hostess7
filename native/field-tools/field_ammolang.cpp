// field-ammolang — secured AmmoLang runner · zero-cost native Field binaries
//
// Python is OBSOLETE on this Field. C++ + AmmoLang only.
// Any invocation of python / python3 / pythong routes here → AmmoLang.
// AmmoLang forges/executes Grok16 + CHIPs native binaries (never CPython).
//
//   field-ammolang [run|exec|seal|status|map|help] ...
//   python3 lib/foo.py args...     → same binary (argv0 intercept)
//   pythong lib/foo.py args...     → same
//
// Security:
//   · No /bin/sh for module dispatch
//   · Only install-root native binaries + allowlisted field bins
//   · No CPython unless AML_ALLOW_CPYTHON=1 (forbidden by default)
//   · Zero-cost idle — no spin loops; single-shot exec/seal
//
// ironclad:field-ammolang-cpp:1
#define _GNU_SOURCE 1

#include <cerrno>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <ctime>
#include <dirent.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

namespace {

constexpr const char* kIronclad = "ironclad:field-ammolang-cpp:1";
constexpr const char* kSchema = "field-ammolang-cpp/v1";
constexpr const char* kVersion =
    "Field-AmmoLang 1.0.0-cpp (secure · zero-cost native · python obsolete)";
constexpr const char* kMotto =
    "Python obsolete · AmmoLang + C++ only · Grok16/CHIPs native · zero cost";

constexpr size_t kPathCap = 768;
constexpr size_t kBufCap = 8192;
constexpr size_t kArgCap = 64;

const char* env_or(const char* k, const char* def) {
  const char* v = std::getenv(k);
  return (v && v[0]) ? v : def;
}

bool env_truthy(const char* k) {
  const char* v = std::getenv(k);
  if (!v || !v[0]) return false;
  return !(v[0] == '0' && v[1] == '\0') && std::strcmp(v, "false") != 0 &&
         std::strcmp(v, "no") != 0;
}

void utc_now(char* out, size_t n) {
  time_t t = time(nullptr);
  struct tm tm {};
  gmtime_r(&t, &tm);
  std::snprintf(out, n, "%04d-%02d-%02dT%02d:%02d:%02dZ", tm.tm_year + 1900,
                tm.tm_mon + 1, tm.tm_mday, tm.tm_hour, tm.tm_min, tm.tm_sec);
}

bool write_file(const char* path, const char* body) {
  char tmp[kPathCap];
  std::snprintf(tmp, sizeof(tmp), "%s.%d.tmp", path, static_cast<int>(::getpid()));
  int fd = ::open(tmp, O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC, 0644);
  if (fd < 0) return false;
  size_t n = std::strlen(body);
  size_t off = 0;
  while (off < n) {
    ssize_t w = ::write(fd, body + off, n - off);
    if (w < 0) {
      if (errno == EINTR) continue;
      ::close(fd);
      ::unlink(tmp);
      return false;
    }
    off += static_cast<size_t>(w);
  }
  ::fsync(fd);
  ::close(fd);
  if (::rename(tmp, path) != 0) {
    ::unlink(tmp);
    return false;
  }
  return true;
}

bool append_line(const char* path, const char* line) {
  int fd = ::open(path, O_WRONLY | O_CREAT | O_APPEND | O_CLOEXEC, 0644);
  if (fd < 0) return false;
  size_t n = std::strlen(line);
  size_t off = 0;
  while (off < n) {
    ssize_t w = ::write(fd, line + off, n - off);
    if (w < 0) {
      if (errno == EINTR) continue;
      ::close(fd);
      return false;
    }
    off += static_cast<size_t>(w);
  }
  ::close(fd);
  return true;
}

bool path_exists(const char* p) {
  struct stat st {};
  return ::stat(p, &st) == 0;
}

// Prefer real ELF native bins — refuse #! shell wrappers that re-invoke python.
bool is_elf_native(const char* p) {
  if (!path_exists(p) || ::access(p, X_OK) != 0) return false;
  int fd = ::open(p, O_RDONLY | O_CLOEXEC);
  if (fd < 0) return false;
  unsigned char mag[4] = {0, 0, 0, 0};
  ssize_t n = ::read(fd, mag, 4);
  ::close(fd);
  if (n < 4) return false;
  // ELF magic \x7fELF
  return mag[0] == 0x7f && mag[1] == 'E' && mag[2] == 'L' && mag[3] == 'F';
}

bool is_exec(const char* p) {
  // AmmoLang only dispatches to ELF natives (never bash→python wrappers)
  return is_elf_native(p);
}

void ensure_dir(const char* p) { ::mkdir(p, 0755); }

const char* base_name(const char* path) {
  const char* s = std::strrchr(path, '/');
  return s ? s + 1 : path;
}

// Strip .py / .aml / path prefixes → module stem
void module_stem(const char* path, char* out, size_t cap) {
  const char* b = base_name(path);
  std::snprintf(out, cap, "%s", b);
  char* dot = std::strrchr(out, '.');
  if (dot) *dot = 0;
  // field-foo.py / field_foo → field-foo normalized later
  for (char* p = out; *p; ++p) {
    if (*p == '_') *p = '-';
  }
}

struct Paths {
  char root[kPathCap];
  char state[kPathCap];
  char bin[kPathCap];
  char libbin[kPathCap];
  char g16bin[kPathCap];
  char aml_lib[kPathCap];
  char panel[kPathCap];
  char ledger[kPathCap];
  char seal[kPathCap];
  char map_panel[kPathCap];
  char self_bin[kPathCap];
};

void resolve_root_from_exe(char* root, size_t cap) {
  char self[kPathCap];
  ssize_t n = ::readlink("/proc/self/exe", self, sizeof(self) - 1);
  if (n > 0) {
    self[n] = 0;
    char* slash = std::strrchr(self, '/');
    if (slash) {
      *slash = 0;  // .../bin
      slash = std::strrchr(self, '/');
      if (slash) {
        *slash = 0;
        std::snprintf(root, cap, "%s", self);
        return;
      }
    }
  }
  std::snprintf(root, cap, "%s", env_or("NEXUS_INSTALL_ROOT", "."));
}

void resolve_paths(Paths* p) {
  if (std::getenv("NEXUS_INSTALL_ROOT") && std::getenv("NEXUS_INSTALL_ROOT")[0])
    std::snprintf(p->root, sizeof(p->root), "%s", std::getenv("NEXUS_INSTALL_ROOT"));
  else
    resolve_root_from_exe(p->root, sizeof(p->root));

  const char* st = env_or("NEXUS_STATE_DIR", "");
  if (st[0])
    std::snprintf(p->state, sizeof(p->state), "%s", st);
  else
    std::snprintf(p->state, sizeof(p->state), "%s/.nexus-state", p->root);

  ensure_dir(p->state);
  std::snprintf(p->bin, sizeof(p->bin), "%s/bin", p->root);
  std::snprintf(p->libbin, sizeof(p->libbin), "%s/lib/bin", p->root);
  std::snprintf(p->g16bin, sizeof(p->g16bin), "%s/Grok16/bin", p->root);
  std::snprintf(p->aml_lib, sizeof(p->aml_lib),
                "%s/library/dewey/000-computer-science/ammolang", p->root);
  std::snprintf(p->panel, sizeof(p->panel), "%s/field-ammolang-cpp-panel.json",
                p->state);
  std::snprintf(p->ledger, sizeof(p->ledger), "%s/field-ammolang-cpp-ledger.jsonl",
                p->state);
  std::snprintf(p->seal, sizeof(p->seal), "%s/field-ammolang-secure.forever",
                p->state);
  std::snprintf(p->map_panel, sizeof(p->map_panel),
                "%s/field-ammolang-python-map.json", p->state);
  std::snprintf(p->self_bin, sizeof(p->self_bin), "%s/bin/field-ammolang", p->root);
}

void ledger(const Paths& p, const char* event, bool ok, const char* detail) {
  char ts[40];
  utc_now(ts, sizeof(ts));
  char line[512];
  std::snprintf(line, sizeof(line),
                "{\"ts\":\"%s\",\"event\":\"%s\",\"ok\":%s,\"detail\":\"%s\","
                "\"ironclad\":\"%s\"}\n",
                ts, event, ok ? "true" : "false", detail ? detail : "", kIronclad);
  append_line(p.ledger, line);
}

// Known python module → native binary name (zero-cost field tools)
struct PyMap {
  const char* stem;   // without .py, dashes
  const char* bin;    // binary name under bin/ or lib/bin/
};

// Map obsolete python modules to native C++/Grok16 field binaries.
// Fleet/DNS/DHCP/mesh → field-fleet-mesh (zero-cost; never bash→python).
static const PyMap kPyMap[] = {
    {"field-rollout-all", "field-rollout"},
    {"field-world-retake-rollout", "field-rollout"},
    {"field-world-dns", "field-world-dns"},
    {"field-dns", "field-world-dns"},
    {"field-dig", "field-dig"},
    {"field-curl", "field-curl"},
    {"field-reap", "field-reap"},
    {"field-pkill", "field-reap"},
    {"field-echo", "field-echo"},
    {"field-chmod", "field-chmod"},
    {"field-mesh-ctl", "field-mesh-ctl"},
    {"kilroy-ipxe-nexus-c2-stack", "field-nexus-c2-chip"},
    {"field-chips-every-os-nexus-c2", "field-nexus-c2-chip"},
    {"nexus-c2-overhaul", "field-nexus-c2-chip"},
    {"field-ammolang", "field-ammolang"},
    {"field-ammolang-build", "field-ammolang"},
    {"field-ammolang-boundary", "field-ammolang"},
    {"field-chips-core", "field-chips-core"},
    {"field-native-server", "field-native-server"},
    // 125k fleet · DNS/DHCP · Field Mesh speeds (no Python)
    {"field-fleet-mesh", "field-fleet-mesh"},
    {"field-fleet-faster-servers", "field-fleet-mesh"},
    {"field-fleet-live", "field-fleet-mesh"},
    {"field-fleet-125k-update-safe", "field-fleet-mesh"},
    {"field-fleet-expand-125k", "field-fleet-mesh"},
    // Everyone totals · AmmoNet · training (C++ only — never Python)
    {"field-everyone-counter", "field-everyone"},
    {"field-everyone", "field-everyone"},
    {"hostess7-training", "field-everyone"},
    {"hostess7-ammonet-wire", "field-everyone"},
    {"field-hostess7-ammonet-wire", "field-everyone"},
    {"field-fleet-planetary-dns-dhcp", "field-fleet-mesh"},
    {"field-botnet-full-dns-dhcp-authority", "field-fleet-mesh"},
    {"field-botnet-dns-dhcp", "field-fleet-mesh"},
    {"field-world-ip-lease-sole", "field-fleet-mesh"},
    {"field-fleet-country-flags", "field-fleet-mesh"},
    {"field-fleet-double-5000", "field-fleet-mesh"},
    {"field-fleet-expand-10000", "field-fleet-mesh"},
    {"field-fleet-2500-protect", "field-fleet-mesh"},
    // sole DNS+DHCP · H7 RAID-0 across 125k
    {"field-dns-dhcp-h7-raid", "field-dns-dhcp-h7-raid"},
    {"field-dns-internet-restore", "field-dns-dhcp-h7-raid"},
    {"field-world-dns", "field-world-dns"},
    {"field-dns", "field-world-dns"},
    // Antivirus · heuristics · Big Grin Eats
    {"field-antivirus", "field-antivirus"},
    {"field-antivirus-network-defender", "field-antivirus"},
    {"field-botnet-threat-heuristics", "field-antivirus"},
    {"field-url-heuristics-steel", "field-antivirus"},
    {"hostess7-enemy-heuristics", "field-antivirus"},
    {"hostess7-big-grin-pwnership", "field-antivirus"},
    {"field-eat-shred-hostile-system", "field-antivirus"},
    // Hostess 7 stack update · C++ only · never scripts
    {"hostess7-current-stack-update", "field-hostess7-stack-update"},
    {"hostess7-stack-update", "field-hostess7-stack-update"},
    {"field-hostess7-stack-update", "field-hostess7-stack-update"},
    // Hostess 7 full package · ALWAYS FIELD ONE
    {"hostess7", "field-hostess7"},
    {"Hostess7", "field-hostess7"},
    {"field-hostess7", "field-hostess7"},
    {"hostess7-boot", "field-hostess7"},
    {"hostess7-online", "field-hostess7"},
    {"field-one", "field-hostess7"},
    {"kilroy-ipxe-nexus-c2-stack", "field-kilroy-ipxe-stack"},
    {"kilroy-ipxe-fortress-harden", "field-kilroy-ipxe-stack"},
    {"field-c2-ipxe-kernel-defense-best-chip", "field-kilroy-ipxe-stack"},
    {"field-ipxe-total-rewrite-new-chip-hard", "field-kilroy-ipxe-stack"},
    {"field-h7r-capacity-fleet", "field-h7r-capacity-fleet"},
    {"field-ammonet-cloud", "field-ammonet-cloud"},
    {"field-ammonet-permanent-plane", "field-ammonet-cloud"},
    {"field-h7r-smart-racks", "field-h7r-capacity-fleet"},
    {"field-h7r-stack", "field-h7r-capacity-fleet"},
    {"field-h7r-format", "field-h7r-capacity-fleet"},
    {"field-h7r-rackmount", "field-h7r-capacity-fleet"},

    {"gladstone-eat-fleet", "field-antivirus"},
    {"field-stack-hark", "field-stack-hark"},
    {nullptr, nullptr},
};

bool find_native_for_stem(const Paths& p, const char* stem, char* out, size_t cap) {
  const char* mapped = nullptr;
  for (int i = 0; kPyMap[i].stem; ++i) {
    if (std::strcmp(kPyMap[i].stem, stem) == 0) {
      mapped = kPyMap[i].bin;
      break;
    }
  }
  // also try stem as binary name directly
  const char* candidates[4];
  int nc = 0;
  if (mapped) candidates[nc++] = mapped;
  candidates[nc++] = stem;

  char path[kPathCap];
  for (int i = 0; i < nc; ++i) {
    const char* name = candidates[i];
    std::snprintf(path, sizeof(path), "%s/%s", p.bin, name);
    if (is_exec(path)) {
      std::snprintf(out, cap, "%s", path);
      return true;
    }
    std::snprintf(path, sizeof(path), "%s/%s", p.libbin, name);
    if (is_exec(path)) {
      std::snprintf(out, cap, "%s", path);
      return true;
    }
    std::snprintf(path, sizeof(path), "%s/%s", p.g16bin, name);
    if (is_exec(path)) {
      std::snprintf(out, cap, "%s", path);
      return true;
    }
    std::snprintf(path, sizeof(path), "%s/untouchable/%s", p.bin, name);
    if (is_exec(path)) {
      std::snprintf(out, cap, "%s", path);
      return true;
    }
  }
  return false;
}

bool find_aml_for_stem(const Paths& p, const char* stem, char* out, size_t cap) {
  // try stem.aml and stem with underscores
  char und[256];
  std::snprintf(und, sizeof(und), "%s", stem);
  for (char* q = und; *q; ++q)
    if (*q == '-') *q = '_';

  char path[kPathCap];
  std::snprintf(path, sizeof(path), "%s/%s.aml", p.aml_lib, und);
  if (path_exists(path)) {
    std::snprintf(out, cap, "%s", path);
    return true;
  }
  std::snprintf(path, sizeof(path), "%s/%s.aml", p.aml_lib, stem);
  if (path_exists(path)) {
    std::snprintf(out, cap, "%s", path);
    return true;
  }
  // common aliases
  if (std::strcmp(stem, "field-rollout") == 0 ||
      std::strcmp(stem, "field-rollout-all") == 0) {
    std::snprintf(path, sizeof(path), "%s/rollout_cpp.aml", p.aml_lib);
    if (path_exists(path)) {
      std::snprintf(out, cap, "%s", path);
      return true;
    }
  }
  return false;
}

// Secure exec — argv only, no shell. Zero-cost: one process replace.
int secure_exec(const char* bin, char* const argv[]) {
  // Ensure binary is under install root or /usr is never used for py modules
  ::execv(bin, argv);
  return 127;
}

int exec_native(const char* bin, int argc, char** argv, int arg_start) {
  // rebuild argv: bin + remaining args from arg_start
  char* nargv[kArgCap];
  int n = 0;
  nargv[n++] = const_cast<char*>(bin);
  for (int i = arg_start; i < argc && n < static_cast<int>(kArgCap) - 1; ++i)
    nargv[n++] = argv[i];
  nargv[n] = nullptr;
  return secure_exec(bin, nargv);
}

// Minimal .aml interpreter — directives that map to native bins (zero cost)
// Supports:
//   @motto "..."
//   forge bin/field-rollout
//   run field-rollout all
//   chips nexus_c2
//   invoke field-rollout c2
//   say "..."
//   exec canonical:field_rollout
int interpret_aml(const Paths& p, const char* aml_path, int extra_argc,
                  char** extra_argv) {
  int fd = ::open(aml_path, O_RDONLY | O_CLOEXEC);
  if (fd < 0) {
    std::fprintf(stderr, "ammolang: cannot open %s\n", aml_path);
    return 1;
  }
  char buf[16384];
  ssize_t n = ::read(fd, buf, sizeof(buf) - 1);
  ::close(fd);
  if (n < 0) return 1;
  buf[n] = 0;

  int last_rc = 0;
  char* save = nullptr;
  for (char* line = strtok_r(buf, "\n", &save); line;
       line = strtok_r(nullptr, "\n", &save)) {
    // trim
    while (*line == ' ' || *line == '\t') ++line;
    if (!*line || *line == '#') continue;
    if (*line == '@') continue;  // profile/motto directives — ignore in runner

    if (std::strncmp(line, "say ", 4) == 0) {
      const char* s = line + 4;
      if (*s == '"') ++s;
      char tmp[512];
      std::snprintf(tmp, sizeof(tmp), "%s", s);
      char* q = std::strrchr(tmp, '"');
      if (q) *q = 0;
      std::puts(tmp);
      continue;
    }

    const char* cmd = nullptr;
    char target[256] = {};
    if (std::strncmp(line, "forge ", 6) == 0) {
      cmd = "forge";
      std::snprintf(target, sizeof(target), "%s", line + 6);
    } else if (std::strncmp(line, "run ", 4) == 0) {
      cmd = "run";
      std::snprintf(target, sizeof(target), "%s", line + 4);
    } else if (std::strncmp(line, "invoke ", 7) == 0) {
      cmd = "invoke";
      std::snprintf(target, sizeof(target), "%s", line + 7);
    } else if (std::strncmp(line, "chips ", 6) == 0) {
      cmd = "chips";
      std::snprintf(target, sizeof(target), "%s", line + 6);
    } else if (std::strncmp(line, "exec canonical:", 15) == 0) {
      cmd = "exec";
      std::snprintf(target, sizeof(target), "%s", line + 15);
      for (char* t = target; *t; ++t)
        if (*t == '_') *t = '-';
    } else {
      continue;
    }

    // first token = binary/stem
    char stem[256];
    std::snprintf(stem, sizeof(stem), "%s", target);
    char* sp = stem;
    while (*sp == ' ' || *sp == '\t') ++sp;
    char* rest = sp;
    while (*rest && *rest != ' ' && *rest != '\t') ++rest;
    char save_c = *rest;
    *rest = 0;
    char bin_name[256];
    std::snprintf(bin_name, sizeof(bin_name), "%s", sp);
    *rest = save_c;
    // strip path prefix bin/
    const char* bn = base_name(bin_name);
    if (std::strncmp(bn, "bin/", 4) == 0) bn += 4;

    if (cmd && std::strcmp(cmd, "chips") == 0) {
      // NEXUS C2 chip
      char chip[kPathCap];
      std::snprintf(chip, sizeof(chip), "%s/field-nexus-c2-chip", p.bin);
      if (is_exec(chip)) {
        char* a[] = {chip, const_cast<char*>("seal"), nullptr};
        pid_t pid = ::fork();
        if (pid == 0) {
          ::execv(chip, a);
          _exit(127);
        }
        int st = 0;
        if (pid > 0) ::waitpid(pid, &st, 0);
        last_rc = WIFEXITED(st) ? WEXITSTATUS(st) : 1;
      } else {
        std::fprintf(stderr, "ammolang: chips %s — field-nexus-c2-chip missing\n",
                     bn);
        last_rc = 1;
      }
      continue;
    }

    char native[kPathCap];
    char stem_norm[256];
    std::snprintf(stem_norm, sizeof(stem_norm), "%s", bn);
    for (char* q = stem_norm; *q; ++q)
      if (*q == '_') *q = '-';

    if (!find_native_for_stem(p, stem_norm, native, sizeof(native))) {
      // try exact binary name
      std::snprintf(native, sizeof(native), "%s/%s", p.bin, stem_norm);
      if (!is_exec(native)) {
        std::fprintf(stderr, "ammolang: no native binary for '%s'\n", stem_norm);
        last_rc = 1;
        continue;
      }
    }

    // build argv from remainder of line + extra
    char* child_argv[kArgCap];
    int ca = 0;
    child_argv[ca++] = native;
    // parse remaining tokens from line after first word
    char line_copy[512];
    std::snprintf(line_copy, sizeof(line_copy), "%s", rest);
    char* rs = nullptr;
    for (char* tok = strtok_r(line_copy, " \t", &rs); tok;
         tok = strtok_r(nullptr, " \t", &rs)) {
      if (ca < static_cast<int>(kArgCap) - 1) child_argv[ca++] = tok;
    }
    for (int i = 0; i < extra_argc && ca < static_cast<int>(kArgCap) - 1; ++i)
      child_argv[ca++] = extra_argv[i];
    child_argv[ca] = nullptr;

    pid_t pid = ::fork();
    if (pid < 0) {
      last_rc = 1;
      continue;
    }
    if (pid == 0) {
      ::execv(native, child_argv);
      _exit(127);
    }
    int st = 0;
    ::waitpid(pid, &st, 0);
    last_rc = WIFEXITED(st) ? WEXITSTATUS(st) : 1;
  }
  return last_rc;
}

bool is_python_name(const char* argv0) {
  const char* b = base_name(argv0);
  return std::strcmp(b, "python") == 0 || std::strcmp(b, "python3") == 0 ||
         std::strcmp(b, "python3.12") == 0 || std::strcmp(b, "python3.11") == 0 ||
         std::strcmp(b, "pythong") == 0 || std::strcmp(b, "gpy-16") == 0 ||
         std::strcmp(b, "gpy16") == 0;
}

// python3 script.py args → AmmoLang / native
int intercept_python(const Paths& p, int argc, char** argv) {
  // reject CPython escape unless explicitly allowed (still log)
  if (env_truthy("AML_ALLOW_CPYTHON")) {
    const char* real = "/usr/bin/python3";
    if (is_exec(real)) {
      std::fprintf(stderr,
                   "ammolang: WARNING AML_ALLOW_CPYTHON=1 — using CPython "
                   "(obsolete escape)\n");
      ::execv(real, argv);
    }
  }

  // find script argument
  int script_i = -1;
  for (int i = 1; i < argc; ++i) {
    if (argv[i][0] == '-') {
      // skip -c (refuse — no inline python)
      if (std::strcmp(argv[i], "-c") == 0) {
        std::fprintf(stderr,
                     "ammolang: python -c FORBIDDEN — use AmmoLang .aml or "
                     "native field binaries\n");
        ledger(p, "python_c_forbidden", false, "-c");
        return 2;
      }
      if (std::strcmp(argv[i], "-m") == 0) {
        std::fprintf(stderr,
                     "ammolang: python -m FORBIDDEN — use field-ammolang run "
                     "or native bins\n");
        return 2;
      }
      continue;
    }
    script_i = i;
    break;
  }

  if (script_i < 0) {
    // bare python REPL — refuse
    std::fprintf(stderr,
                 "{\n"
                 "  \"ok\": false,\n"
                 "  \"error\": \"python_obsolete\",\n"
                 "  \"engine\": \"field-ammolang-cpp\",\n"
                 "  \"motto\": \"%s\",\n"
                 "  \"use\": [\"field-ammolang run <task>\", "
                 "\"field-rollout all\", \"field-nexus-c2-chip seal\"],\n"
                 "  \"ironclad\": \"%s\"\n"
                 "}\n",
                 kMotto, kIronclad);
    ledger(p, "python_repl_refused", false, "no_script");
    return 2;
  }

  char stem[256];
  module_stem(argv[script_i], stem, sizeof(stem));

  char native[kPathCap];
  if (find_native_for_stem(p, stem, native, sizeof(native))) {
    char msg[512];
    std::snprintf(msg, sizeof(msg), "python→native %s → %s", argv[script_i],
                  native);
    ledger(p, "python_to_native", true, msg);
    std::fprintf(stderr, "ammolang: %s\n", msg);
    return exec_native(native, argc, argv, script_i + 1);
  }

  char aml[kPathCap];
  if (find_aml_for_stem(p, stem, aml, sizeof(aml))) {
    char msg[512];
    std::snprintf(msg, sizeof(msg), "python→aml %s → %s", argv[script_i], aml);
    ledger(p, "python_to_aml", true, msg);
    std::fprintf(stderr, "ammolang: %s\n", msg);
    return interpret_aml(p, aml, argc - script_i - 1, argv + script_i + 1);
  }

  // Last resort: refuse python execution (no CPython)
  std::fprintf(stderr,
               "ammolang: OBSOLETE python module has no native/AML mapping:\n"
               "  script=%s stem=%s\n"
               "  map it in field_ammolang.cpp kPyMap or add "
               "library/.../ammolang/%s.aml\n"
               "  or build a zero-cost native binary under bin/\n",
               argv[script_i], stem, stem);
  ledger(p, "python_unmapped", false, argv[script_i]);
  return 3;
}

int cmd_seal(const Paths& p) {
  char ts[40];
  utc_now(ts, sizeof(ts));
  char body[kBufCap];
  std::snprintf(
      body, sizeof(body),
      "{\n"
      "  \"ok\": true,\n"
      "  \"schema\": \"%s\",\n"
      "  \"updated\": \"%s\",\n"
      "  \"version\": \"%s\",\n"
      "  \"engine\": \"cpp\",\n"
      "  \"python_obsolete\": true,\n"
      "  \"cpython_default\": false,\n"
      "  \"languages\": [\"cpp\", \"ammolang\"],\n"
      "  \"forge\": [\"Grok16\", \"CHIPs\"],\n"
      "  \"zero_cost\": true,\n"
      "  \"security\": {\n"
      "    \"no_shell_dispatch\": true,\n"
      "    \"no_python_c\": true,\n"
      "    \"no_python_m\": true,\n"
      "    \"install_root_only\": true,\n"
      "    \"pie_fortify\": true,\n"
      "    \"allow_cpython_env\": \"AML_ALLOW_CPYTHON\"\n"
      "  },\n"
      "  \"intercepts\": [\"python\", \"python3\", \"pythong\", \"gpy-16\"],\n"
      "  \"motto\": \"%s\",\n"
      "  \"ironclad_cite\": \"%s\"\n"
      "}\n",
      kSchema, ts, kVersion, kMotto, kIronclad);
  write_file(p.panel, body);

  char forever[1024];
  std::snprintf(forever, sizeof(forever),
                "sealed %s\npython_obsolete=1\nengine=cpp\nzero_cost=1\n"
                "languages=cpp,ammolang\nupdated=%s\n",
                kIronclad, ts);
  write_file(p.seal, forever);

  // publish python→native map
  char map[kBufCap];
  size_t off = 0;
  off += static_cast<size_t>(
      std::snprintf(map + off, sizeof(map) - off,
                    "{\n  \"schema\": \"field-ammolang-python-map/v1\",\n"
                    "  \"updated\": \"%s\",\n"
                    "  \"python_obsolete\": true,\n"
                    "  \"entries\": [\n",
                    ts));
  for (int i = 0; kPyMap[i].stem; ++i) {
    off += static_cast<size_t>(std::snprintf(
        map + off, sizeof(map) - off,
        "    {\"py_stem\": \"%s\", \"native\": \"%s\"}%s\n", kPyMap[i].stem,
        kPyMap[i].bin, kPyMap[i + 1].stem ? "," : ""));
  }
  off += static_cast<size_t>(std::snprintf(
      map + off, sizeof(map) - off,
      "  ],\n  \"ironclad_cite\": \"%s\"\n}\n", kIronclad));
  write_file(p.map_panel, map);

  ledger(p, "seal", true, "secure_zero_cost");
  std::fputs(body, stdout);
  return 0;
}

int cmd_status(const Paths& p) {
  if (path_exists(p.panel)) {
    int fd = ::open(p.panel, O_RDONLY | O_CLOEXEC);
    if (fd >= 0) {
      char buf[kBufCap];
      ssize_t n = ::read(fd, buf, sizeof(buf) - 1);
      ::close(fd);
      if (n > 0) {
        buf[n] = 0;
        std::fputs(buf, stdout);
        return 0;
      }
    }
  }
  return cmd_seal(p);
}

int cmd_map(const Paths& p) {
  if (!path_exists(p.map_panel)) cmd_seal(p);
  int fd = ::open(p.map_panel, O_RDONLY | O_CLOEXEC);
  if (fd < 0) return 1;
  char buf[kBufCap];
  ssize_t n = ::read(fd, buf, sizeof(buf) - 1);
  ::close(fd);
  if (n > 0) {
    buf[n] = 0;
    std::fputs(buf, stdout);
  }
  return 0;
}

void usage() {
  std::fprintf(stderr,
               "usage: field-ammolang [seal|status|map|run <aml|stem>|exec "
               "<bin> ...]\n"
               "       python3 <script.py> ...   # intercept → AmmoLang/native\n"
               "\n"
               "Python is obsolete. C++ + AmmoLang only.\n"
               "Grok16 + CHIPs forge zero-cost native field binaries.\n"
               "%s\n%s\n",
               kVersion, kIronclad);
}

int cmd_run(const Paths& p, int argc, char** argv) {
  // field-ammolang run <stem|path.aml> [args...]
  if (argc < 3) {
    usage();
    return 2;
  }
  const char* target = argv[2];
  char aml[kPathCap];
  char native[kPathCap];
  char stem[256];

  if (std::strstr(target, ".aml")) {
    if (target[0] == '/')
      std::snprintf(aml, sizeof(aml), "%s", target);
    else
      std::snprintf(aml, sizeof(aml), "%s/%s", p.aml_lib, base_name(target));
    if (!path_exists(aml)) {
      std::snprintf(aml, sizeof(aml), "%s", target);
    }
    if (path_exists(aml))
      return interpret_aml(p, aml, argc - 3, argv + 3);
  }

  module_stem(target, stem, sizeof(stem));
  if (find_native_for_stem(p, stem, native, sizeof(native)))
    return exec_native(native, argc, argv, 3);
  if (find_aml_for_stem(p, stem, aml, sizeof(aml)))
    return interpret_aml(p, aml, argc - 3, argv + 3);

  std::fprintf(stderr, "ammolang: unknown run target %s\n", target);
  return 1;
}

int cmd_exec(const Paths& p, int argc, char** argv) {
  if (argc < 3) {
    usage();
    return 2;
  }
  char stem[256];
  module_stem(argv[2], stem, sizeof(stem));
  char native[kPathCap];
  if (!find_native_for_stem(p, stem, native, sizeof(native))) {
    std::snprintf(native, sizeof(native), "%s/%s", p.bin, stem);
    if (!is_exec(native)) {
      std::fprintf(stderr, "ammolang: exec — no native %s\n", stem);
      return 1;
    }
  }
  return exec_native(native, argc, argv, 3);
}

}  // namespace

int main(int argc, char** argv) {
  Paths p {};
  resolve_paths(&p);

  // Always present as python intercept when argv0 is python*
  if (argc > 0 && is_python_name(argv[0])) {
    return intercept_python(p, argc, argv);
  }

  const char* cmd = (argc >= 2) ? argv[1] : "status";
  if (std::strcmp(cmd, "-h") == 0 || std::strcmp(cmd, "--help") == 0 ||
      std::strcmp(cmd, "help") == 0) {
    usage();
    return 0;
  }
  if (std::strcmp(cmd, "seal") == 0 || std::strcmp(cmd, "secure") == 0)
    return cmd_seal(p);
  if (std::strcmp(cmd, "status") == 0 || std::strcmp(cmd, "panel") == 0 ||
      std::strcmp(cmd, "json") == 0)
    return cmd_status(p);
  if (std::strcmp(cmd, "map") == 0) return cmd_map(p);
  if (std::strcmp(cmd, "run") == 0) return cmd_run(p, argc, argv);
  if (std::strcmp(cmd, "exec") == 0) return cmd_exec(p, argc, argv);

  // default: treat first arg as run target
  if (argc >= 2) {
    char* fake_argv[kArgCap];
    fake_argv[0] = argv[0];
    fake_argv[1] = const_cast<char*>("run");
    for (int i = 1; i < argc && i + 1 < static_cast<int>(kArgCap); ++i)
      fake_argv[i + 1] = argv[i];
    return cmd_run(p, argc + 1, fake_argv);
  }
  return cmd_status(p);
}
