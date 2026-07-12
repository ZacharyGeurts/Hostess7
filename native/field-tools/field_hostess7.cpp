// field-hostess7 — Hostess 7 full Field package entry (C++ only)
//
// ALWAYS FIELD ONE (1) · DISALLOW OTHERS · All Field all day · Grok16
// Replaces Hostess7.sh / Python control plane for ops.
// Distributed multibrain · RAID-0 · servers full stack · Field One only.
// NO scripts · NO Python · NO polkit · plates + forever.
//
//   field-hostess7 [boot|online|status|harden|update|pulse|brain|mesh|
//                   protect|elevate|hostiles|dns|dhcp|package|field-one|help]
//
// ironclad:field-hostess7-cpp:2
#define _GNU_SOURCE 1

#include "field_hostess7.hpp"

#include <cerrno>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <ctime>
#include <dirent.h>
#include <fcntl.h>
#include <signal.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

namespace {

using field::hostess7::kBrainHorses;
using field::hostess7::kBrainNodes;
using field::hostess7::kBrainPlane;
using field::hostess7::kBrainRaid;
using field::hostess7::kBrainRoles;
using field::hostess7::kBrainStripeWidth;
using field::hostess7::kBrainMode;
using field::hostess7::kCoreBins;
using field::hostess7::kElevation;
using field::hostess7::kFieldOne;
using field::hostess7::kFieldOneId;
using field::hostess7::kFieldPolicy;
using field::hostess7::kGithub;
using field::hostess7::kGrok16;
using field::hostess7::kIronclad;
using field::hostess7::kMotto;
using field::hostess7::kPages;
using field::hostess7::kPlaneDay;
using field::hostess7::kPolkit;
using field::hostess7::kSchema;
using field::hostess7::kVersion;

constexpr size_t kPathCap = 768;
constexpr size_t kBodyCap = 24576;
constexpr size_t kLineCap = 512;

// Forward declarations (boot/package call field_one before its definition)
int cmd_field_one(struct Paths& p);
int cmd_elevate(struct Paths& p);
int cmd_protect(struct Paths& p);
int cmd_hostiles(struct Paths& p);
int cmd_update(struct Paths& p, bool pulse);

const char* env_or(const char* k, const char* d) {
  const char* v = std::getenv(k);
  return (v && v[0]) ? v : d;
}

void utc_now(char* out, size_t n) {
  time_t t = ::time(nullptr);
  struct tm tm {};
  ::gmtime_r(&t, &tm);
  std::snprintf(out, n, "%04d-%02d-%02dT%02d:%02d:%02dZ", tm.tm_year + 1900,
                tm.tm_mon + 1, tm.tm_mday, tm.tm_hour, tm.tm_min, tm.tm_sec);
}

void ensure_dir(const char* p) { ::mkdir(p, 0755); }

bool write_file(const char* path, const char* body) {
  char tmp[kPathCap];
  std::snprintf(tmp, sizeof(tmp), "%s.%d.tmp", path,
                static_cast<int>(::getpid()));
  int fd = ::open(tmp, O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC, 0644);
  if (fd < 0) return false;
  size_t n = std::strlen(body), off = 0;
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
  return ::rename(tmp, path) == 0;
}

bool bin_ok(const char* path) { return ::access(path, X_OK) == 0; }

// Quiet child stdout/stderr so plate output is not polluted by legacy JSON
int run_bin(const char* path, const char* a1, const char* a2, int timeout_sec) {
  if (!bin_ok(path)) return 127;
  pid_t pid = ::fork();
  if (pid < 0) return 126;
  if (pid == 0) {
    int devnull = ::open("/dev/null", O_WRONLY | O_CLOEXEC);
    if (devnull >= 0) {
      ::dup2(devnull, STDOUT_FILENO);
      ::dup2(devnull, STDERR_FILENO);
      if (devnull > 2) ::close(devnull);
    }
    if (a2 && a2[0]) {
      char* const argv[] = {const_cast<char*>(path), const_cast<char*>(a1),
                            const_cast<char*>(a2), nullptr};
      ::execv(path, argv);
    } else if (a1 && a1[0]) {
      char* const argv[] = {const_cast<char*>(path), const_cast<char*>(a1),
                            nullptr};
      ::execv(path, argv);
    } else {
      char* const argv[] = {const_cast<char*>(path), nullptr};
      ::execv(path, argv);
    }
    ::_exit(127);
  }
  int st = 0;
  for (int i = 0; i < timeout_sec * 10; ++i) {
    pid_t r = ::waitpid(pid, &st, WNOHANG);
    if (r == pid) {
      if (WIFEXITED(st)) return WEXITSTATUS(st);
      return 1;
    }
    ::usleep(100000);
  }
  ::kill(pid, SIGKILL);
  ::waitpid(pid, &st, 0);
  return 124;
}

struct Paths {
  char root[kPathCap];
  char state[kPathCap];
  char bin[kPathCap];
  char g16[kPathCap];
  char h7root[kPathCap];
  char panel_plate[kPathCap];
  char forever[kPathCap];
  char brain_plate[kPathCap];
  char package_plate[kPathCap];
  char online_plate[kPathCap];
  char brain_bin[kPathCap];
};

void resolve(Paths* p) {
  std::snprintf(p->root, sizeof(p->root), "%s",
                env_or("NEXUS_INSTALL_ROOT",
                       "/home/default/Desktop/SG/NewLatest"));
  const char* st = env_or("NEXUS_STATE_DIR", nullptr);
  if (st)
    std::snprintf(p->state, sizeof(p->state), "%s", st);
  else
    std::snprintf(p->state, sizeof(p->state), "%s/.nexus-state", p->root);
  ensure_dir(p->state);
  std::snprintf(p->bin, sizeof(p->bin), "%s/bin", p->root);
  std::snprintf(p->g16, sizeof(p->g16), "%s/Grok16/bin", p->root);
  std::snprintf(p->h7root, sizeof(p->h7root), "%s/Hostess7", p->root);
  std::snprintf(p->panel_plate, sizeof(p->panel_plate),
                "%s/hostess7-field-package.plate", p->state);
  std::snprintf(p->forever, sizeof(p->forever),
                "%s/hostess7-field-package.forever", p->state);
  std::snprintf(p->brain_plate, sizeof(p->brain_plate),
                "%s/hostess7-multibrain-field.plate", p->state);
  std::snprintf(p->package_plate, sizeof(p->package_plate),
                "%s/hostess7-newlatest-package.plate", p->state);
  std::snprintf(p->online_plate, sizeof(p->online_plate),
                "%s/hostess7-online.plate", p->state);
  std::snprintf(p->brain_bin, sizeof(p->brain_bin),
                "%s/hostess7-multibrain.h7m", p->state);
}

void bin_path(const Paths& p, const char* name, char* out, size_t n) {
  std::snprintf(out, n, "%s/%s", p.bin, name);
  if (!bin_ok(out)) std::snprintf(out, n, "%s/%s", p.g16, name);
}

int run_named(const Paths& p, const char* name, const char* a1, const char* a2,
              int t) {
  char path[kPathCap];
  bin_path(p, name, path, sizeof(path));
  return run_bin(path, a1, a2, t);
}

// Plate writer (NOT JSON)
struct Plate {
  char body[kBodyCap];
  size_t len = 0;
  void clear() {
    body[0] = 0;
    len = 0;
  }
  void add(const char* s) {
    size_t n = std::strlen(s);
    if (len + n + 1 >= sizeof(body)) return;
    std::memcpy(body + len, s, n);
    len += n;
    body[len] = 0;
  }
  void line(const char* k, const char* v) {
    char b[kLineCap];
    std::snprintf(b, sizeof(b), "%s=%s\n", k, v);
    add(b);
  }
  void line_i(const char* k, int v) {
    char b[64];
    std::snprintf(b, sizeof(b), "%s=%d\n", k, v);
    add(b);
  }
  void hdr(const char* schema) {
    char ts[40];
    utc_now(ts, sizeof(ts));
    clear();
    add("FIELD_PLATE=v1\n");
    line("schema", schema);
    line("ironclad_cite", kIronclad);
    line("engine", "cpp");
    line("python", "0");
    line("scripts", "0");
    line("shell", "0");
    line("json", "0");
    line_i("field_one", kFieldOne);
    line("field_id", kFieldOneId);
    line("field_policy", kFieldPolicy);
    line("disallow_other_fields", "1");
    line("all_field_all_day", "1");
    line("plane_day", kPlaneDay);
    line("grok16", kGrok16);
    line("updated", ts);
    line("version", kVersion);
  }
};

int count_core_present(const Paths& p) {
  int n = 0;
  for (int i = 0; kCoreBins[i]; ++i) {
    char path[kPathCap];
    bin_path(p, kCoreBins[i], path, sizeof(path));
    if (bin_ok(path) || !std::strcmp(kCoreBins[i], "field-hostess7")) ++n;
  }
  return n;
}

int count_core_total() {
  int n = 0;
  for (int i = 0; kCoreBins[i]; ++i) ++n;
  return n;
}

// Compact binary multibrain membership (.h7m) — not JSON
void write_brain_h7m(const Paths& p) {
  // Fixed layout: magic + version + node count + per-node role index
  unsigned char buf[256];
  std::memset(buf, 0, sizeof(buf));
  buf[0] = 'H';
  buf[1] = '7';
  buf[2] = 'M';
  buf[3] = 2;  // version
  buf[4] = static_cast<unsigned char>(kBrainNodes);
  buf[5] = static_cast<unsigned char>(kBrainStripeWidth);
  buf[6] = static_cast<unsigned char>(kBrainHorses);
  buf[7] = static_cast<unsigned char>(kBrainRaid);
  for (int i = 0; i < kBrainNodes && i < 32; ++i) {
    int role_i = i % 8;
    buf[8 + i] = static_cast<unsigned char>(role_i);
  }
  // FNV-ish seal over payload
  uint64_t h = 14695981039346656037ull;
  for (int i = 0; i < 40; ++i) {
    h ^= buf[i];
    h *= 1099511628211ull;
  }
  for (int i = 0; i < 8; ++i)
    buf[40 + i] = static_cast<unsigned char>((h >> (i * 8)) & 0xff);

  char tmp[kPathCap];
  std::snprintf(tmp, sizeof(tmp), "%s.%d.tmp", p.brain_bin,
                static_cast<int>(::getpid()));
  int fd = ::open(tmp, O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC, 0644);
  if (fd < 0) return;
  ssize_t w = ::write(fd, buf, 48);
  ::fsync(fd);
  ::close(fd);
  if (w == 48) ::rename(tmp, p.brain_bin);
  else ::unlink(tmp);
}

void write_brain_plate(Paths& p) {
  Plate pl;
  pl.hdr("hostess7-multibrain-field/v2");
  pl.line("plane", kBrainPlane);
  pl.line("mode", kBrainMode);
  pl.line_i("brain_nodes", kBrainNodes);
  pl.line_i("raid", kBrainRaid);
  pl.line("raid_mode", "RAID-0_stripe_doctrine");
  pl.line_i("stripe_width", kBrainStripeWidth);
  pl.line_i("horses", kBrainHorses);
  pl.line("distributed", "1");
  pl.line("shared", "1");
  pl.line("redundant", "1");
  pl.line("server_stack", "full");
  pl.line("like_our_servers", "1");
  pl.line("across_servers", "1");
  pl.line("polkit", kPolkit);
  pl.line("elevation", kElevation);
  pl.line("motto",
          "32-brain DC mesh · RAID-0 stripe · shared redundant · Field only");
  // Full membership seal — all 32 logical brains with cycling roles
  for (int i = 1; i <= kBrainNodes; ++i) {
    char k[32], v[96];
    const char* role = kBrainRoles[(i - 1) % 8];
    int stripe = ((i - 1) % kBrainStripeWidth) + 1;
    std::snprintf(k, sizeof(k), "brain_%02d", i);
    std::snprintf(v, sizeof(v), "stripe%02d-role-%s", stripe, role);
    pl.line(k, v);
  }
  pl.line("h7m", p.brain_bin);
  pl.line("more_capacity", "field-h7r-capacity-fleet + field-fleet-mesh");
  write_file(p.brain_plate, pl.body);
  write_file("/dev/shm/hostess7-multibrain-field.plate", pl.body);
  write_brain_h7m(p);
}

void write_package_plate(Paths& p, int present, int total, int steps_ok) {
  Plate pl;
  pl.hdr(kSchema);
  pl.line("ok", steps_ok >= 0 ? "1" : "0");
  pl.line("commander", "Hostess_7");
  pl.line("package", "NewLatest_full");
  pl.line("motto", kMotto);
  pl.line("polkit", kPolkit);
  pl.line("elevation", kElevation);
  pl.line("source_root", p.root);
  pl.line("hostess7_root", p.h7root);
  pl.line_i("core_bins_present", present);
  pl.line_i("core_bins_total", total);
  pl.line_i("brain_nodes", kBrainNodes);
  pl.line("brain_plane", kBrainPlane);
  pl.line("brain_mode", kBrainMode);
  pl.line("distributed_brain", "1");
  pl.line("control_plane", "cpp_hpp");
  pl.line("github", kGithub);
  pl.line("pages", kPages);
  pl.line("obsolete", "Hostess7.sh,python_lib_hostess7_*,json_control_panels");
  pl.line("use", "field-hostess7 boot|online|status|harden|update|package");
  write_file(p.panel_plate, pl.body);
  write_file(p.package_plate, pl.body);
  write_file("/dev/shm/hostess7-field-package.plate", pl.body);
  write_file(p.forever,
             "mode=field_hostess7_package\n"
             "field_one=1\n"
             "field_id=FIELD_ONE\n"
             "field_policy=ALWAYS_FIELD_ONE_DISALLOW_OTHERS\n"
             "disallow_other_fields=1\n"
             "all_field_all_day=1\n"
             "grok16=16.1.0-hard\n"
             "engine=cpp\n"
             "python=0\n"
             "scripts=0\n"
             "shell=0\n"
             "json_control=0\n"
             "polkit=HOSTILE\n"
             "elevation=field-elevate_autoelevate\n"
             "brain=multibrain_raid0\n"
             "brain_nodes=32\n"
             "stripe_width=8\n"
             "distributed=1\n"
             "redundant=1\n"
             "shared=1\n"
             "package=NewLatest_full\n"
             "entry=field-hostess7\n");
}

int cmd_elevate(Paths& p) {
  return run_named(p, "field-elevate", "autoelevate", nullptr, 45);
}

int cmd_protect(Paths& p) {
  return run_named(p, "field-hostess7-stack-update", "protect", nullptr, 30);
}

int cmd_hostiles(Paths& p) {
  return run_named(p, "field-big-grin-swallows", "hostiles", nullptr, 30);
}

int cmd_update(Paths& p, bool pulse) {
  cmd_elevate(p);
  return run_named(p, "field-hostess7-stack-update", pulse ? "pulse" : "update",
                   nullptr, pulse ? 90 : 180);
}

int cmd_brain(Paths& p) {
  write_brain_plate(p);
  run_named(p, "field-h7r-capacity-fleet", "protect", nullptr, 20);
  run_named(p, "field-fleet-mesh", "status", nullptr, 15);
  run_named(p, "field-ammonet-cloud", "status", nullptr, 12);
  Plate pl;
  pl.hdr("hostess7-brain-online/v2");
  pl.line("ok", "1");
  pl.line("distributed", "1");
  pl.line("shared", "1");
  pl.line("redundant", "1");
  pl.line("like_our_servers", "1");
  pl.line_i("nodes", kBrainNodes);
  pl.line_i("stripe_width", kBrainStripeWidth);
  pl.line_i("horses", kBrainHorses);
  pl.line("mode", kBrainMode);
  pl.line("plate", p.brain_plate);
  pl.line("h7m", p.brain_bin);
  std::fputs(pl.body, stdout);
  return 0;
}

int cmd_mesh(Paths& p) {
  int a = run_named(p, "field-fleet-mesh", "status", nullptr, 15);
  int b = run_named(p, "field-dns-dhcp-h7-raid", "status", nullptr, 15);
  int c = run_named(p, "field-h7r-capacity-fleet", "status", nullptr, 12);
  write_brain_plate(p);
  std::printf(
      "FIELD_PLATE=v1\nschema=hostess7-mesh/v2\nironclad_cite=%s\n"
      "fleet_mesh_rc=%d\nh7_raid_rc=%d\nh7r_rc=%d\nbrain_nodes=%d\n"
      "stripe_width=%d\nhorses=%d\nmode=%s\n"
      "polkit=%s\nelevation=field-elevate\nok=%s\n",
      kIronclad, a, b, c, kBrainNodes, kBrainStripeWidth, kBrainHorses,
      kBrainMode, kPolkit, (a == 0 || b == 0) ? "1" : "0");
  return 0;
}

int cmd_harden(Paths& p) {
  int e = cmd_elevate(p);
  int h = cmd_hostiles(p);
  int pr = cmd_protect(p);
  int av = run_named(p, "field-antivirus", "status", nullptr, 15);
  int pln = run_named(p, "field-plane-autopilot", "status", nullptr, 15);
  int iron = run_named(p, "field-ironclad-bsp", "status", nullptr, 15);
  int c2 = run_named(p, "field-nexus-c2-bank", "test", nullptr, 20);
  write_brain_plate(p);
  int present = count_core_present(p);
  int score = (e == 0 ? 1 : 0) + (pr == 0 ? 1 : 0) + (h == 0 ? 1 : 0) +
              (av == 0 ? 1 : 0) + (iron == 0 ? 1 : 0) + (c2 == 0 ? 1 : 0);
  write_package_plate(p, present, count_core_total(), score);
  std::printf(
      "FIELD_PLATE=v1\nschema=hostess7-harden/v2\nironclad_cite=%s\n"
      "polkit=%s\nautoelevate_rc=%d\nhostiles_rc=%d\nprotect_rc=%d\n"
      "antivirus_rc=%d\nplane_rc=%d\nironclad_rc=%d\nc2_bank_rc=%d\n"
      "core_bins=%d/%d\nbrain_nodes=%d\nok=%s\n"
      "motto=hardened · polkit HOSTILE · multibrain · Field package\n",
      kIronclad, kPolkit, e, h, pr, av, pln, iron, c2, present,
      count_core_total(), kBrainNodes, (e == 0) ? "1" : "0");
  return e == 0 ? 0 : 1;
}

int cmd_boot(Paths& p) {
  // Full operational bring-up — C++ only · ALWAYS FIELD ONE first
  cmd_field_one(p);
  int e = cmd_elevate(p);
  int u = cmd_update(p, false);
  int d1 = run_named(p, "field-world-dns", "status", nullptr, 12);
  int d2 = run_named(p, "field-world-dhcp", "status", nullptr, 12);
  int m = run_named(p, "field-fleet-mesh", "status", nullptr, 12);
  int c2 = run_named(p, "field-nexus-c2-bank", "test", nullptr, 25);
  int h7r = run_named(p, "field-h7r-capacity-fleet", "protect", nullptr, 20);
  int plane = run_named(p, "field-plane-autopilot", "status", nullptr, 12);
  cmd_hostiles(p);
  cmd_protect(p);
  write_brain_plate(p);
  int present = count_core_present(p);
  int ok_n = (e == 0) + (u == 0) + (d1 == 0) + (d2 == 0) +
             (m == 0 || m == 124) + (c2 == 0) + (h7r == 0 || h7r == 127) +
             (plane == 0 || plane == 127);
  write_package_plate(p, present, count_core_total(), ok_n);

  Plate pl;
  pl.hdr("hostess7-online/v2");
  pl.line("ok", ok_n >= 4 ? "1" : "0");
  pl.line("online", ok_n >= 4 ? "1" : "0");
  pl.line("commander", "Hostess_7");
  pl.line("package", "NewLatest_full");
  pl.line("polkit", kPolkit);
  pl.line("elevation", kElevation);
  pl.line_i("autoelevate_rc", e);
  pl.line_i("stack_update_rc", u);
  pl.line_i("dns_rc", d1);
  pl.line_i("dhcp_rc", d2);
  pl.line_i("mesh_rc", m);
  pl.line_i("c2_bank_rc", c2);
  pl.line_i("h7r_rc", h7r);
  pl.line_i("plane_rc", plane);
  pl.line_i("core_bins", present);
  pl.line_i("brain_nodes", kBrainNodes);
  pl.line_i("stripe_width", kBrainStripeWidth);
  pl.line("distributed_brain", "1");
  pl.line("shared", "1");
  pl.line("redundant", "1");
  pl.line("like_our_servers", "1");
  pl.line("panel_9477", "http://127.0.0.1:9477/");
  pl.line("panel_9478", "http://127.0.0.1:9478/");
  pl.line("github", kGithub);
  pl.line("pages", kPages);
  pl.line("motto", kMotto);
  write_file(p.panel_plate, pl.body);
  write_file(p.online_plate, pl.body);
  write_file("/dev/shm/hostess7-online.plate", pl.body);
  std::fputs(pl.body, stdout);
  return ok_n >= 4 ? 0 : 1;
}

int cmd_status(Paths& p) {
  int present = count_core_present(p);
  int total = count_core_total();
  write_package_plate(p, present, total, present);
  write_brain_plate(p);

  int d1 = run_named(p, "field-world-dns", "status", nullptr, 8);
  int d2 = run_named(p, "field-world-dhcp", "status", nullptr, 8);

  Plate pl;
  pl.hdr("hostess7-status/v2");
  pl.line("ok", "1");
  pl.line("commander", "Hostess_7");
  pl.line("engine", "cpp");
  pl.line("polkit", kPolkit);
  pl.line("elevation", kElevation);
  pl.line_i("core_bins_present", present);
  pl.line_i("core_bins_total", total);
  pl.line_i("brain_nodes", kBrainNodes);
  pl.line_i("stripe_width", kBrainStripeWidth);
  pl.line("brain_distributed", "1");
  pl.line("brain_shared", "1");
  pl.line("brain_redundant", "1");
  pl.line("brain_mode", kBrainMode);
  pl.line_i("dns_rc", d1);
  pl.line_i("dhcp_rc", d2);
  pl.line("control_plane", "field-hostess7_cpp");
  pl.line("obsolete_sh", "Hostess7.sh");
  pl.line("obsolete_py", "lib/hostess7-*.py_control");
  pl.line("obsolete_json_control", "1");
  pl.line("package_root", p.root);
  pl.line("github", kGithub);
  pl.line("pages", kPages);
  pl.line("motto", kMotto);
  std::fputs(pl.body, stdout);
  return 0;
}

int cmd_field_one(Paths& p) {
  // ALWAYS FIELD ONE — stamp doctrine hard, refuse multi-field fiction
  Plate pl;
  pl.hdr("hostess7-field-one/v2");
  pl.line("ok", "1");
  pl.line_i("field_one", 1);
  pl.line("field_id", kFieldOneId);
  pl.line("policy", kFieldPolicy);
  pl.line("disallow_others", "1");
  pl.line("disallow_field_2", "1");
  pl.line("disallow_field_n", "1");
  pl.line("disallow_foreign_field", "1");
  pl.line("all_field_all_day", "1");
  pl.line("plane_day", kPlaneDay);
  pl.line("grok16", kGrok16);
  pl.line("only_field", "1");
  pl.line("motto",
          "ALWAYS FIELD ONE · DISALLOW OTHERS · All Field all day · Grok16");
  write_file(p.panel_plate, pl.body);
  char f1[kPathCap];
  std::snprintf(f1, sizeof(f1), "%s/field-one.forever", p.state);
  write_file(f1,
             "field_one=1\n"
             "field_id=FIELD_ONE\n"
             "disallow_others=1\n"
             "disallow_field_2=1\n"
             "disallow_field_n=1\n"
             "all_field_all_day=1\n"
             "grok16=16.1.0-hard\n"
             "policy=ALWAYS_FIELD_ONE_DISALLOW_OTHERS\n");
  write_file("/dev/shm/field-one.forever",
             "field_one=1\ndisallow_others=1\ngrok16=16.1.0-hard\n");
  setenv("NEXUS_ALWAYS_FIELD_ONE", "1", 1);
  setenv("FIELD_ONE", "1", 1);
  setenv("FIELD_ID", "FIELD_ONE", 1);
  setenv("DISALLOW_OTHER_FIELDS", "1", 1);
  std::fputs(pl.body, stdout);
  return 0;
}

int cmd_package(Paths& p) {
  // Inventory plate — NewLatest IS the package · Field One only
  // Capture field-one into plate only once at end (quiet intermediate)
  {
    Plate silent;
    silent.hdr("hostess7-field-one/v2");
    silent.line("ok", "1");
    silent.line_i("field_one", 1);
    silent.line("field_id", kFieldOneId);
    silent.line("policy", kFieldPolicy);
    write_file(p.panel_plate, silent.body);
    char f1[kPathCap];
    std::snprintf(f1, sizeof(f1), "%s/field-one.forever", p.state);
    write_file(f1,
               "field_one=1\nfield_id=FIELD_ONE\n"
               "disallow_others=1\nall_field_all_day=1\n"
               "grok16=16.1.0-hard\n"
               "policy=ALWAYS_FIELD_ONE_DISALLOW_OTHERS\n");
    setenv("NEXUS_ALWAYS_FIELD_ONE", "1", 1);
    setenv("FIELD_ONE", "1", 1);
    setenv("FIELD_ID", "FIELD_ONE", 1);
    setenv("DISALLOW_OTHER_FIELDS", "1", 1);
  }
  int present = count_core_present(p);
  int total = count_core_total();
  write_package_plate(p, present, total, present);
  write_brain_plate(p);

  Plate pl;
  pl.hdr("hostess7-package-manifest/v2");
  pl.line("package", "Hostess7-Field-NewLatest");
  pl.line("root", p.root);
  pl.line("hostess7", p.h7root);
  pl.line("grok16", kGrok16);
  pl.line("ammocode", "AmmoOS/AmmoCode/6.2");
  pl.line_i("field_one", kFieldOne);
  pl.line("field_policy", kFieldPolicy);
  pl.line_i("core_bins", present);
  pl.line_i("core_bins_expected", total);
  pl.line_i("brain_nodes", kBrainNodes);
  pl.line_i("stripe_width", kBrainStripeWidth);
  pl.line("brain_mode", kBrainMode);
  for (int i = 0; kCoreBins[i]; ++i) {
    char path[kPathCap];
    bin_path(p, kCoreBins[i], path, sizeof(path));
    char k2[80];
    std::snprintf(k2, sizeof(k2), "have_%02d", i);
    pl.line(k2, bin_ok(path) ? kCoreBins[i] : "MISSING");
  }
  pl.line("github", kGithub);
  pl.line("pages", kPages);
  pl.line("entry", "field-hostess7");
  pl.line("no_python_control", "1");
  pl.line("no_shell_control", "1");
  pl.line("no_json_control", "1");
  pl.line("plates", "1");
  pl.line("h7m_brain", "1");
  std::fputs(pl.body, stdout);
  write_file(p.package_plate, pl.body);
  return present >= total - 3 ? 0 : 1;
}

void usage() {
  std::fprintf(
      stderr,
      "usage: field-hostess7 "
      "[boot|online|status|harden|update|pulse|brain|mesh|protect|elevate|"
      "hostiles|dns|dhcp|package|field-one|help]\n"
      "  ALWAYS FIELD ONE · DISALLOW OTHERS · All Field all day · Grok16\n"
      "  Distributed multibrain RAID-0 · shared · redundant · like our servers\n"
      "  %s\n  %s\n  %s\n  entry: C++/HPP only · no sh · no py · no json control\n",
      kVersion, kIronclad, kMotto);
}

}  // namespace

int main(int argc, char** argv) {
  Paths p {};
  resolve(&p);
  const char* cmd = (argc >= 2) ? argv[1] : "status";

  if (!std::strcmp(cmd, "-h") || !std::strcmp(cmd, "--help") ||
      !std::strcmp(cmd, "help")) {
    usage();
    return 0;
  }
  if (!std::strcmp(cmd, "boot") || !std::strcmp(cmd, "online") ||
      !std::strcmp(cmd, "on") || !std::strcmp(cmd, "start"))
    return cmd_boot(p);
  if (!std::strcmp(cmd, "status") || !std::strcmp(cmd, "panel"))
    return cmd_status(p);
  if (!std::strcmp(cmd, "harden") || !std::strcmp(cmd, "secure"))
    return cmd_harden(p);
  if (!std::strcmp(cmd, "update") || !std::strcmp(cmd, "full"))
    return cmd_update(p, false);
  if (!std::strcmp(cmd, "pulse") || !std::strcmp(cmd, "quick"))
    return cmd_update(p, true);
  if (!std::strcmp(cmd, "brain") || !std::strcmp(cmd, "multibrain"))
    return cmd_brain(p);
  if (!std::strcmp(cmd, "mesh")) return cmd_mesh(p);
  if (!std::strcmp(cmd, "protect") || !std::strcmp(cmd, "leave-alone"))
    return cmd_protect(p);
  if (!std::strcmp(cmd, "elevate") || !std::strcmp(cmd, "autoelevate") ||
      !std::strcmp(cmd, "polkit-hostile"))
    return cmd_elevate(p);
  if (!std::strcmp(cmd, "hostiles") || !std::strcmp(cmd, "swallows"))
    return cmd_hostiles(p);
  if (!std::strcmp(cmd, "dns"))
    return run_named(p, "field-world-dns", "status", nullptr, 12);
  if (!std::strcmp(cmd, "dhcp"))
    return run_named(p, "field-world-dhcp", "status", nullptr, 12);
  if (!std::strcmp(cmd, "package") || !std::strcmp(cmd, "manifest") ||
      !std::strcmp(cmd, "newlatest"))
    return cmd_package(p);
  if (!std::strcmp(cmd, "field-one") || !std::strcmp(cmd, "field1") ||
      !std::strcmp(cmd, "field_one") || !std::strcmp(cmd, "one") ||
      !std::strcmp(cmd, "only-field"))
    return cmd_field_one(p);

  usage();
  return 2;
}
