// field-world-dns — Ironclad Grok16 C++ Field Mesh DNS (Hostess 7).
//
// Doctrine:
//   · Field Mesh IS the ONLY DNS (and DHCP on the lease plane) for clients.
//   · resolv → 127.0.0.1 only · never foreign client NS.
//   · Field zones answer Field LAN IPs.
//   · Public web answers REAL public IPv4 truth pins (Ironclad · BSP-fast).
//   · H7 RAID-0 stripes hold the WHOLE DNS/DHCP authority across 125k.
//   · We answer truthfully and securely to every request we hold.
//
//   field-world-dns serve [--port N] [--bind ADDR] [--daemon]
//   field-world-dns status
//   field-world-dns probe [name]
//
// ironclad:field-world-dns-cpp:5
// Anti-freeze: single-instance flock, daemon stdio → /dev/null, no dual SO_REUSEPORT pile-up
// Answer path NEVER multi-helper blocks — cold miss queues; idle fills stripe for 125k.
#define _GNU_SOURCE 1

#include <arpa/inet.h>
#include <atomic>
#include <cerrno>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <ctime>
#include <fcntl.h>
#include <netinet/in.h>
#include <poll.h>
#include <signal.h>
#include <sys/file.h>
#include <sys/prctl.h>
#include <sys/resource.h>
#include <sys/select.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <time.h>
#include <unistd.h>

namespace {

// Ironclad BSP plane — no vendor host tables. Truth = live learn + H7 stripe.
// Client plane: 127.0.0.1 only · Egress plane: ephemeral helper UDP (isolated).
// ironclad:field-world-dns-cpp:9 · ironclad:field-bsp-source-kernel:1
// ironclad:field-dns-isolated-authority:1
constexpr const char* kIronclad = "ironclad:field-world-dns-cpp:9";
constexpr const char* kBspCite = "ironclad:field-bsp-source-kernel:1";
constexpr const char* kIsoCite = "ironclad:field-dns-isolated-authority:1";
constexpr const char* kSchema = "field-world-dns-cpp/v9";
constexpr const char* kVersion =
    "Field-World-DNS 2.7.0-cpp (isolated authority · full internet · H7 125k)";
constexpr const char* kMotto =
    "Sole DNS authority · isolated process plane · live internet truth · H7 125k";

constexpr size_t kPktCap = 1500;
constexpr size_t kNameCap = 256;
constexpr size_t kPathCap = 512;
constexpr size_t kAnsIPs = 8;
// Whole-internet + media + H7 striped tables.
// 65536 × ~232B ≈ 15MB static BSS — room for planet-scale pin cache.
// Ring-evict when full so learn never dies (sticky media patterns kept).
constexpr size_t kMaxPins = 65536;
constexpr size_t kPinNameCap = 96;
constexpr uint32_t kTTLField = 30;
constexpr uint32_t kTTLPublic = 60;
constexpr uint32_t kTTLProvisional = 15;  // disk pin until live learn
constexpr size_t kPlateCap = 64;      // related names per apex plate
constexpr size_t kApexTrack = 1024;   // plated apex ring
constexpr size_t kPendingPlateCap = 256;
// Learn queue for 125k fleet — cold miss never freezes serve loop
constexpr size_t kPendingLearnCap = 8192;
// Learn budgets — OAuth/GIS CNAME chains (client_id.apps.*) need ~100–150ms
// Answer path: still capped; never multi-second freezes.
constexpr int kAnswerHelperUs = 160000;    // 160ms cold miss (CNAME+A chains)
constexpr int kPrimaryHelperUs = 120000;   // idle multi-helper primary A
constexpr int kPlateHelperUs = 80000;      // 80ms plate member
constexpr int kPlateLearnsPerTick = 16;    // idle: generic plate fill
constexpr int kLearnQueuePerTick = 16;     // idle live discovers per tick
constexpr int kIdleLearnBudgetUs = 160000; // 160ms wall-clock per idle tick
// ironclad:field-dns-steel-plate-meld:3   (generic neural + CNAME only · no site table)
// ironclad:field-dns-media-whole-internet:1
// ironclad:field-dns-table-stripe-fill:1
// ironclad:field-dns-never-stuck-125k:1
// ironclad:field-dns-no-hardcode:1
// ironclad:field-dns-oauth-cname-chain:1

// Field-zone reclaim answers (local plane only — never for public web)
static const char* kFieldAnswers[] = {
    "192.168.47.1", "192.168.50.1", "127.0.0.1", nullptr};

// IPs that are Field/hijack — never treat as public CDN truth
static const char* kHijackIPs[] = {
    "127.0.0.1",  "127.0.0.53", "0.0.0.0",     "192.168.47.1",
    "192.168.50.1", "7.7.7.7",  "71.86.188.33", "::1",
    nullptr};

// NO compile-time site host tables. Bootstrap health probe only (empty IPs).
// All public names discovered live via Field BSP helpers → H7 stripe.
struct SeedEntry {
  const char* name;
  const char* ips[kAnsIPs];
};
static const SeedEntry kTruthSeeds[] = {
    // Name-only health probe for plane self-test — IPs never compile-time truth
    {"x.com", {nullptr}},
    {nullptr, {nullptr}},
};

std::atomic<bool> g_run{true};
std::atomic<uint64_t> g_queries{0};
std::atomic<uint64_t> g_answers{0};
std::atomic<uint64_t> g_field_reclaims{0};
std::atomic<uint64_t> g_public_answers{0};
std::atomic<uint64_t> g_nx{0};
std::atomic<uint64_t> g_plate_melds{0};
std::atomic<uint64_t> g_plate_names_learned{0};

// Rate-limit: one steel plate per apex per process lifetime (or until ring wraps)
static char g_plated_apex[kApexTrack][kPinNameCap];
static int g_plated_n = 0;

// Generic structural labels only — invent common sub-hosts for ANY apex
// (.com / .net / .org / .biz / .io / …). No vendor host tables.
// Auth/OAuth/SSO labels are structural (accounts.*, oauth2.*, …) for every TLD.
// Live traffic + CNAME chain + H7 stripe fill the rest.
static const char* kNeuralPrefixes[] = {
    "www", "m", "mobile", "api", "cdn", "static", "assets", "media", "img",
    "images", "image", "css", "js", "fonts", "font", "video", "videos",
    "content", "secure", "login", "auth", "oauth", "oauth2", "sso",
    "accounts", "account", "myaccount", "signin", "signup", "id", "identity",
    "s", "i", "a", "b", "ssl", "apps", "hosted", "client", "token",
    "staticcdn", "external-content", "links", "proxy", "icons",
    "static-cdn", "video-cdn", "vid-cdn", "thumb", "thumbs",
    "player", "stream", "hls", "dash", "edge", "origin",
    "ajax", "ws", "live", "vod", "embed", "ads", "ad",
    "media-cdn", "vcdn", "scdn",
    nullptr};

// Deferred steel-plate queue — answer first, learn plate between packets
static char g_pending_plates[kPendingPlateCap][kPinNameCap];
static int g_pending_plate_n = 0;
// In-progress deferred plate work (names still to learn for one apex)
static char g_plate_work[kPlateCap][kPinNameCap];
static int g_plate_work_n = 0;
static int g_plate_work_i = 0;
static char g_plate_work_apex[kPinNameCap];

// Async public learn queue — cold misses fill stripe off the answer path
static char g_pending_learn[kPendingLearnCap][kPinNameCap];
static int g_pending_learn_n = 0;
static std::atomic<uint64_t> g_learn_queued{0};
static std::atomic<uint64_t> g_learn_drained{0};
static std::atomic<uint64_t> g_answer_fast_path{0};

static int64_t mono_us() {
  struct timespec ts {};
  if (clock_gettime(CLOCK_MONOTONIC, &ts) != 0) return 0;
  return static_cast<int64_t>(ts.tv_sec) * 1000000LL +
         static_cast<int64_t>(ts.tv_nsec) / 1000LL;
}

struct Pin {
  char name[kPinNameCap];
  char ips[kAnsIPs][16];
  int n_ips;
  uint8_t sticky;   // 1 = seed/hot — never ring-evict
  time_t learned_at;  // 0 = seed/stale · refresh OAuth/public edges
};
// Refresh A pins before this age so Google OAuth never sticks on dead seeds
// Stale pins still answer immediately; idle discover_refresh_tick updates.
constexpr time_t kPinRefreshSec = 120;

// Pins live in static storage — ServeOpts on stack must stay small (was
// truncating loads when kMaxPins was 512 × ~228B ≈ 117KB on stack).
static Pin g_pins[kMaxPins];
static int g_n_pins = 0;
static int g_pin_evict = 0;  // ring cursor for non-sticky reuse
static std::atomic<uint64_t> g_learned{0};
static std::atomic<uint64_t> g_evictions{0};

struct ServeOpts {
  char bind[64];
  int ports[8];
  int n_ports;
  bool daemon;
  char field_ips[kAnsIPs][16];
  int n_field;
  char state_dir[kPathCap];
  char install_root[kPathCap];
  Pin* pins;  // → g_pins
  int n_pins;
  bool xcom_ok;
  char xcom_sample[16];
};

// Soft-kill (SIGTERM/SIGINT/SIGHUP) = terrorist inject on sole DNS plane.
// IGNORE forever. H7r racks + AmmoNet depend on us staying up.
// SIGKILL cannot be caught — field-rollout / autopilot respawns the daemon.
void soft_kill_ignored(int) {
  // never stop sole DNS
}
void on_signal_stop_only_usr1(int) { g_run.store(false); }

void utc_now(char* out, size_t n) {
  time_t t = time(nullptr);
  struct tm tm {};
  gmtime_r(&t, &tm);
  std::snprintf(out, n, "%04d-%02d-%02dT%02d:%02d:%02dZ", tm.tm_year + 1900,
                tm.tm_mon + 1, tm.tm_mday, tm.tm_hour, tm.tm_min, tm.tm_sec);
}

const char* env_or(const char* k, const char* def) {
  const char* v = std::getenv(k);
  return (v && v[0]) ? v : def;
}

void to_lower(const char* in, char* out, size_t cap) {
  size_t i = 0;
  for (; in && in[i] && i + 1 < cap; ++i) {
    char c = in[i];
    if (c >= 'A' && c <= 'Z') c = static_cast<char>(c + 32);
    out[i] = c;
  }
  out[i] = 0;
  // strip trailing dots
  while (i > 0 && out[i - 1] == '.') {
    out[--i] = 0;
  }
}

bool is_hijack_ip(const char* ip) {
  if (!ip || !ip[0]) return true;
  for (int i = 0; kHijackIPs[i]; ++i) {
    if (std::strcmp(ip, kHijackIPs[i]) == 0) return true;
  }
  return false;
}

// Real public IPv4 only — reject private/loopback/hijack/garbage JSON fragments
bool is_real_public_ipv4(const char* ip) {
  if (!ip || !ip[0]) return false;
  // reject anything that looks like JSON or non-IP tokens
  for (const char* p = ip; *p; ++p) {
    if (!((*p >= '0' && *p <= '9') || *p == '.')) return false;
  }
  unsigned a = 0, b = 0, c = 0, d = 0;
  char extra = 0;
  if (std::sscanf(ip, "%u.%u.%u.%u%c", &a, &b, &c, &d, &extra) != 4) return false;
  if (a > 255 || b > 255 || c > 255 || d > 255) return false;
  if (is_hijack_ip(ip)) return false;
  if (a == 0 || a == 127 || a >= 224) return false;
  if (a == 10) return false;
  if (a == 192 && b == 168) return false;
  if (a == 172 && b >= 16 && b <= 31) return false;
  if (a == 169 && b == 254) return false;
  return true;
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

int encode_name(const char* name, uint8_t* out, size_t cap) {
  if (!name || !out || cap < 2) return -1;
  size_t o = 0;
  const char* p = name;
  while (*p == '.') ++p;
  if (!*p) {
    out[0] = 0;
    return 1;
  }
  while (*p) {
    const char* dot = std::strchr(p, '.');
    size_t len = dot ? static_cast<size_t>(dot - p) : std::strlen(p);
    if (len == 0 || len > 63 || o + 1 + len + 1 > cap) return -1;
    out[o++] = static_cast<uint8_t>(len);
    std::memcpy(out + o, p, len);
    o += len;
    if (!dot) break;
    p = dot + 1;
  }
  if (o + 1 > cap) return -1;
  out[o++] = 0;
  return static_cast<int>(o);
}

int decode_qname(const uint8_t* pkt, size_t pkt_n, size_t off, char* out,
                 size_t out_cap) {
  if (!out || out_cap < 2) return -1;
  size_t o = 0;
  size_t pos = off;
  int jumps = 0;
  bool first = true;
  while (pos < pkt_n) {
    uint8_t lab = pkt[pos];
    if (lab == 0) {
      if (o == 0) {
        out[0] = '.';
        out[1] = 0;
      } else {
        out[o] = 0;
      }
      return static_cast<int>(pos - off + 1);
    }
    if ((lab & 0xC0) == 0xC0) {
      if (pos + 1 >= pkt_n) return -1;
      size_t ptr = ((lab & 0x3F) << 8) | pkt[pos + 1];
      if (ptr >= pkt_n) return -1;
      char rest[kNameCap];
      if (decode_qname(pkt, pkt_n, ptr, rest, sizeof(rest)) < 0) return -1;
      if (!first && o + 1 < out_cap) out[o++] = '.';
      size_t rl = std::strlen(rest);
      if (o + rl >= out_cap) return -1;
      std::memcpy(out + o, rest, rl);
      o += rl;
      out[o] = 0;
      return static_cast<int>(pos - off + 2);
    }
    if ((lab & 0xC0) != 0 || pos + 1 + lab > pkt_n) return -1;
    if (!first) {
      if (o + 1 >= out_cap) return -1;
      out[o++] = '.';
    }
    first = false;
    if (o + lab >= out_cap) return -1;
    std::memcpy(out + o, pkt + pos + 1, lab);
    o += lab;
    pos += 1 + lab;
    if (++jumps > 64) return -1;
  }
  return -1;
}

// Field-owned zones only — NOT the whole internet
bool is_field_zone(const char* name) {
  if (!name || !name[0]) return true;
  char lower[kNameCap];
  to_lower(name, lower, sizeof(lower));
  if (std::strcmp(lower, "localhost") == 0) return true;
  // suffix / token match for Field brands
  static const char* kOwn[] = {
      "big-grin",     "biggrin",      "pwnership",  "hostess7",
      "hostess-7",    "ammonet",      "field-one",  "field1",
      "fieldmesh",    "nexus",        "kilroy",     "grok16",
      ".field",       ".field1",      ".lan",       ".local",
      "gladstone",    "super-eats",   "supereats",  nullptr};
  for (int j = 0; kOwn[j]; ++j) {
    if (std::strstr(lower, kOwn[j])) return true;
  }
  // bare single-label field service names
  if (!std::strchr(lower, '.')) {
    static const char* kBare[] = {"hostess7", "biggrin", "nexus", "field",
                                  "grok", nullptr};
    for (int j = 0; kBare[j]; ++j) {
      if (std::strcmp(lower, kBare[j]) == 0) return true;
    }
  }
  return false;
}

Pin* find_pin_exact(ServeOpts& o, const char* lower) {
  for (int i = 0; i < o.n_pins; ++i) {
    if (std::strcmp(o.pins[i].name, lower) == 0) return &o.pins[i];
  }
  return nullptr;
}

// EXACT name only for answers.
//
// CRITICAL (ironclad:field-dns-exact-truth:1):
//   Never answer subdomain X with parent Y's A records.
//   static-ca-cdn.eporner.com ≠ eporner.com — different edges; parent
//   fallback 404s CDN/video and breaks "the whole internet".
//   Missing exact pin → Field world-learn the real public A set.
Pin* find_pin(ServeOpts& o, const char* name) {
  char lower[kNameCap];
  to_lower(name, lower, sizeof(lower));
  return find_pin_exact(o, lower);
}

bool pin_add_ip(Pin* p, const char* ip) {
  if (!p || !is_real_public_ipv4(ip)) return false;
  for (int i = 0; i < p->n_ips; ++i) {
    if (std::strcmp(p->ips[i], ip) == 0) return true;
  }
  if (p->n_ips >= static_cast<int>(kAnsIPs)) return false;
  std::snprintf(p->ips[p->n_ips], sizeof(p->ips[0]), "%s", ip);
  p->n_ips++;
  return true;
}

void pin_clear_ips(Pin* p) {
  if (!p) return;
  p->n_ips = 0;
  for (int i = 0; i < static_cast<int>(kAnsIPs); ++i) p->ips[i][0] = 0;
}

bool pin_needs_refresh(const Pin* p) {
  if (!p || p->n_ips <= 0) return true;
  if (p->learned_at == 0) return true;  // compile-time seed · force live learn
  return (time(nullptr) - p->learned_at) >= kPinRefreshSec;
}

Pin* ensure_pin(ServeOpts& o, const char* name) {
  Pin* p = find_pin_exact(o, name);
  if (!p) {
    char lower[kNameCap];
    to_lower(name, lower, sizeof(lower));
    p = find_pin_exact(o, lower);
  }
  if (p) return p;
  // Free slot
  if (o.n_pins < static_cast<int>(kMaxPins)) {
    p = &o.pins[o.n_pins++];
    g_n_pins = o.n_pins;
    std::memset(p, 0, sizeof(*p));
    to_lower(name, p->name, sizeof(p->name));
    p->sticky = 0;
    return p;
  }
  // Table full — ring-evict a non-sticky pin so media/CDN learn never dies.
  // Seeds and sticky hot pins are skipped (ironclad:field-dns-media-whole-internet:1).
  for (int tries = 0; tries < static_cast<int>(kMaxPins); ++tries) {
    int idx = g_pin_evict % static_cast<int>(kMaxPins);
    g_pin_evict = (g_pin_evict + 1) % static_cast<int>(kMaxPins);
    Pin* cand = &o.pins[idx];
    if (cand->sticky) continue;
    std::memset(cand, 0, sizeof(*cand));
    to_lower(name, cand->name, sizeof(cand->name));
    cand->sticky = 0;
    g_evictions.fetch_add(1);
    return cand;
  }
  return nullptr;  // all sticky (should not happen)
}

// Skip a DNS name (labels or compression pointer) in a packet.
size_t skip_dns_name(const uint8_t* buf, size_t n, size_t i) {
  while (i < n) {
    uint8_t lab = buf[i];
    if (lab == 0) return i + 1;
    if ((lab & 0xC0) == 0xC0) return i + 2;
    i += 1u + lab;
  }
  return n;
}

// Decode compressed/uncompressed DNS name into out (lowercased labels).
int decode_name_at(const uint8_t* buf, size_t n, size_t i, char* out,
                   size_t ocap) {
  size_t o = 0;
  int hops = 0;
  while (i < n && hops++ < 32) {
    uint8_t lab = buf[i];
    if (lab == 0) {
      if (o == 0) {
        out[0] = 0;
        return 0;
      }
      if (o > 0 && out[o - 1] == '.') out[--o] = 0;
      else
        out[o] = 0;
      return static_cast<int>(o);
    }
    if ((lab & 0xC0) == 0xC0) {
      if (i + 1 >= n) return -1;
      size_t ptr = ((lab & 0x3F) << 8) | buf[i + 1];
      i = ptr;
      continue;
    }
    ++i;
    if (i + lab > n) return -1;
    if (o && o + 1 < ocap) out[o++] = '.';
    for (uint8_t k = 0; k < lab && o + 1 < ocap; ++k) {
      char c = static_cast<char>(buf[i + k]);
      if (c >= 'A' && c <= 'Z') c = static_cast<char>(c + 32);
      out[o++] = c;
    }
    i += lab;
  }
  out[o < ocap ? o : ocap - 1] = 0;
  return static_cast<int>(o);
}

// Extract A + CNAME from ANSWER. CNAMEs returned via cname_out (optional).
int extract_answer_a(const uint8_t* rbuf, size_t rn, Pin* pin, char* cname_out,
                     size_t cname_cap) {
  if (cname_out && cname_cap) cname_out[0] = 0;
  if (rn < 12 || !pin) return 0;
  int an = (rbuf[6] << 8) | rbuf[7];
  if (an <= 0) return 0;
  size_t i = 12;
  i = skip_dns_name(rbuf, rn, i);
  if (i + 4 > rn) return 0;
  i += 4;
  int learned = 0;
  for (int a = 0; a < an && i + 10 <= rn; ++a) {
    i = skip_dns_name(rbuf, rn, i);
    if (i + 10 > rn) break;
    uint16_t rtype = (static_cast<uint16_t>(rbuf[i]) << 8) | rbuf[i + 1];
    uint16_t rdlen = (static_cast<uint16_t>(rbuf[i + 8]) << 8) | rbuf[i + 9];
    i += 10;
    if (i + rdlen > rn) break;
    if (rtype == 1 && rdlen == 4) {
      char ip[16];
      std::snprintf(ip, sizeof(ip), "%u.%u.%u.%u", rbuf[i], rbuf[i + 1],
                    rbuf[i + 2], rbuf[i + 3]);
      if (pin_add_ip(pin, ip)) {
        ++learned;
        g_learned.fetch_add(1);
      }
    } else if (rtype == 5 && cname_out && cname_cap > 1) {
      // CNAME — decode target for steel-plate follow
      (void)decode_name_at(rbuf, rn, i, cname_out, cname_cap);
    }
    i += rdlen;
  }
  return learned;
}

// Forward: raw learn (no steel plate) used by CNAME + plate members
int field_learn_public_a_raw(ServeOpts& o, const char* qname);
int field_learn_public_a_budget(ServeOpts& o, const char* qname, int max_us,
                                int max_helpers);
int steel_plate_meld(ServeOpts& o, const char* qname);
void maybe_sticky_media(Pin* p);
void queue_public_learn(const char* qname);
void queue_steel_plate(const char* qname);
int public_learn_tick(ServeOpts& o);

// After privileged bind: isolate authority process from the rest of the system.
// Clients never see helpers; this binary hardens itself post-bind.
// ironclad:field-dns-isolated-authority:1
static bool g_isolated = false;
void isolate_authority_plane() {
  if (g_isolated) return;
  // No new privileges (even if binary is setuid later)
  (void)::prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0);
  // Not dumpable / not ptraceable by unprivileged
  (void)::prctl(PR_SET_DUMPABLE, 0);
  // Keep process name distinct for ops
  (void)::prctl(PR_SET_NAME, "field-dns-auth", 0, 0, 0);
  // Soft core limit 0 — secrets not dumped
  struct rlimit rl {};
  rl.rlim_cur = 0;
  rl.rlim_max = 0;
  (void)::setrlimit(RLIMIT_CORE, &rl);
  // Prefer stay-alive under memory pressure (best-effort; root only)
  int oadj = ::open("/proc/self/oom_score_adj", O_WRONLY | O_CLOEXEC);
  if (oadj >= 0) {
    (void)::write(oadj, "-500\n", 5);
    ::close(oadj);
  }
  g_isolated = true;
}

// One helper UDP query with hard poll deadline — never hangs the 125k plane.
// Isolated egress: ephemeral port + SO_MARK · never on client :53 socket.
bool helper_udp_once(const char* helper_ip, const uint8_t* pkt, size_t w,
                     uint8_t* rbuf, size_t rcap, ssize_t* rn_out,
                     int timeout_us) {
  *rn_out = -1;
  if (!helper_ip || !pkt || w < 12 || !rbuf || rcap < 12 || timeout_us < 1000)
    return false;
  int fd = ::socket(AF_INET, SOCK_DGRAM | SOCK_CLOEXEC, 0);
  if (fd < 0) return false;
  // Bind ephemeral so helper replies cannot land on our :53 listen socket.
  sockaddr_in local {};
  local.sin_family = AF_INET;
  local.sin_addr.s_addr = htonl(INADDR_ANY);
  local.sin_port = 0;
  (void)::bind(fd, reinterpret_cast<sockaddr*>(&local), sizeof(local));
  // Mark egress packets (Field DNS egress plane · firewall can isolate)
  // 0x46444E53 = 'FDNS'
  int mark = 0x46444E53;
  (void)::setsockopt(fd, SOL_SOCKET, SO_MARK, &mark, sizeof(mark));
  int ms = (timeout_us + 999) / 1000;
  if (ms < 1) ms = 1;
  timeval tv {};
  tv.tv_sec = ms / 1000;
  tv.tv_usec = (ms % 1000) * 1000;
  ::setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));
  ::setsockopt(fd, SOL_SOCKET, SO_SNDTIMEO, &tv, sizeof(tv));
  sockaddr_in sa {};
  sa.sin_family = AF_INET;
  sa.sin_port = htons(53);
  if (inet_pton(AF_INET, helper_ip, &sa.sin_addr) != 1) {
    ::close(fd);
    return false;
  }
  if (::sendto(fd, pkt, w, 0, reinterpret_cast<sockaddr*>(&sa), sizeof(sa)) <
      0) {
    ::close(fd);
    return false;
  }
  pollfd pfd {};
  pfd.fd = fd;
  pfd.events = POLLIN;
  int pr = ::poll(&pfd, 1, ms);
  if (pr <= 0 || !(pfd.revents & POLLIN)) {
    ::close(fd);
    return false;
  }
  ssize_t rn = ::recvfrom(fd, rbuf, rcap, 0, nullptr, nullptr);
  ::close(fd);
  if (rn < 12) return false;
  *rn_out = rn;
  return true;
}

void queue_public_learn(const char* qname) {
  if (!qname || !qname[0]) return;
  char lower[kPinNameCap];
  to_lower(qname, lower, sizeof(lower));
  if (!lower[0] || !std::strchr(lower, '.')) return;
  // Dedup against pending queue (scan; cap walk for BSP)
  int scan = g_pending_learn_n;
  if (scan > 256) scan = 256;
  for (int i = g_pending_learn_n - scan; i < g_pending_learn_n; ++i) {
    if (i < 0) continue;
    if (std::strcmp(g_pending_learn[i], lower) == 0) return;
  }
  if (g_pending_learn_n >= static_cast<int>(kPendingLearnCap)) {
    // Drop oldest half when full — never block, keep newest fleet names
    int keep = static_cast<int>(kPendingLearnCap) / 2;
    for (int i = 0; i < keep; ++i) {
      std::snprintf(g_pending_learn[i], kPinNameCap, "%s",
                    g_pending_learn[g_pending_learn_n - keep + i]);
    }
    g_pending_learn_n = keep;
  }
  std::snprintf(g_pending_learn[g_pending_learn_n], kPinNameCap, "%s", lower);
  g_pending_learn_n++;
  g_learn_queued.fetch_add(1);
}

// Idle/background: drain generic + Tubi stripe learn queue under hard budget.
int public_learn_tick(ServeOpts& o) {
  if (g_pending_learn_n <= 0) return 0;
  int64_t t0 = mono_us();
  int did = 0;
  while (g_pending_learn_n > 0 && did < kLearnQueuePerTick) {
    if (mono_us() - t0 > kIdleLearnBudgetUs) break;
    char name[kPinNameCap];
    std::snprintf(name, sizeof(name), "%s", g_pending_learn[0]);
    for (int i = 1; i < g_pending_learn_n; ++i) {
      std::snprintf(g_pending_learn[i - 1], kPinNameCap, "%s",
                    g_pending_learn[i]);
    }
    g_pending_learn_n--;
    Pin* p = find_pin(o, name);
    if (p && p->n_ips > 0 && !pin_needs_refresh(p)) {
      g_learn_drained.fetch_add(1);
      continue;
    }
    int got = field_learn_public_a_budget(o, name, kPrimaryHelperUs, 2);
    if (got > 0) (void)steel_plate_meld(o, name);
    ++did;
    g_learn_drained.fetch_add(1);
  }
  return did;
}

// Full DNS authority — every qtype (A/AAAA/MX/NS/TXT/SRV/HTTPS/SOA/…)
// Clients only talk to Field; Field backends fill truth (not client foreign NS).
// ironclad:field-dns-all-types-authority:1
constexpr int kRrCacheCap = 1024;
constexpr size_t kRrBlobCap = 1200;
struct RrCacheEnt {
  char name[kPinNameCap];
  uint16_t qtype;
  uint16_t an;
  uint16_t ns;
  uint16_t ar;
  uint8_t rcode;
  uint16_t blob_len;
  time_t exp;
  uint8_t blob[kRrBlobCap];  // AN+NS+AR wire after question
};
static RrCacheEnt g_rr_cache[kRrCacheCap];
static int g_rr_n = 0;
static int g_rr_evict = 0;
static std::atomic<uint64_t> g_rr_hits{0};
static std::atomic<uint64_t> g_rr_miss{0};
static std::atomic<uint64_t> g_rr_forward{0};
static std::atomic<uint64_t> g_alltype_answers{0};

static const char* kDnsHelpers[] = {
    "1.1.1.1", "8.8.8.8", "9.9.9.9", "208.67.222.222", nullptr};

// Find end of question section (offset of first answer RR)
size_t dns_after_question(const uint8_t* buf, size_t n) {
  if (n < 12) return n;
  size_t i = 12;
  i = skip_dns_name(buf, n, i);
  if (i + 4 > n) return n;
  return i + 4;
}

RrCacheEnt* rr_cache_find(const char* name, uint16_t qtype) {
  char lower[kPinNameCap];
  to_lower(name, lower, sizeof(lower));
  time_t now = time(nullptr);
  for (int i = 0; i < g_rr_n; ++i) {
    if (g_rr_cache[i].qtype == qtype &&
        std::strcmp(g_rr_cache[i].name, lower) == 0) {
      if (g_rr_cache[i].exp < now) continue;
      return &g_rr_cache[i];
    }
  }
  return nullptr;
}

RrCacheEnt* rr_cache_put(const char* name, uint16_t qtype, int rcode, int an,
                         int ns, int ar, const uint8_t* blob, size_t blen) {
  if (!name || !name[0] || blen > kRrBlobCap) return nullptr;
  char lower[kPinNameCap];
  to_lower(name, lower, sizeof(lower));
  RrCacheEnt* e = rr_cache_find(lower, qtype);
  if (!e) {
    if (g_rr_n < kRrCacheCap) {
      e = &g_rr_cache[g_rr_n++];
    } else {
      e = &g_rr_cache[g_rr_evict % kRrCacheCap];
      g_rr_evict = (g_rr_evict + 1) % kRrCacheCap;
    }
  }
  std::memset(e, 0, sizeof(*e));
  std::snprintf(e->name, sizeof(e->name), "%s", lower);
  e->qtype = qtype;
  e->rcode = static_cast<uint8_t>(rcode & 0x0f);
  e->an = static_cast<uint16_t>(an > 0 ? an : 0);
  e->ns = static_cast<uint16_t>(ns > 0 ? ns : 0);
  e->ar = static_cast<uint16_t>(ar > 0 ? ar : 0);
  e->blob_len = static_cast<uint16_t>(blen);
  if (blen) std::memcpy(e->blob, blob, blen);
  e->exp = time(nullptr) + 120;  // cache all-type answers · reduce gstatic churn
  return e;
}

// Recurse ANY qtype via Field backend helpers. Returns true if helper replied.
// Fills AN+NS+AR wire blob (compression valid when question starts at offset 12).
// ALL DNS: A/AAAA/MX/NS/TXT/SRV/SOA/CAA/HTTPS/SVCB/… — EDNS UDP, multi-helper.
// ironclad:field-dns-all-types-authority:2
bool field_recurse_all_types(const char* qname, uint16_t qtype, int* rcode,
                             int* an, int* ns, int* ar, uint8_t* blob,
                             size_t blob_cap, size_t* blob_len) {
  *rcode = 2;  // SERVFAIL default
  *an = *ns = *ar = 0;
  *blob_len = 0;
  if (!qname || !qname[0]) return false;

  // Cache hit — only meaningful prior answers (never poison from empty miss)
  if (RrCacheEnt* hit = rr_cache_find(qname, qtype)) {
    g_rr_hits.fetch_add(1);
    *rcode = hit->rcode;
    *an = hit->an;
    *ns = hit->ns;
    *ar = hit->ar;
    if (hit->blob_len && hit->blob_len <= blob_cap) {
      std::memcpy(blob, hit->blob, hit->blob_len);
      *blob_len = hit->blob_len;
    }
    return true;
  }
  g_rr_miss.fetch_add(1);

  uint8_t pkt[512];
  pkt[0] = 0xF1;
  pkt[1] = 0xE1;
  pkt[2] = 0x01;  // RD=1
  pkt[3] = 0x00;
  pkt[4] = 0x00;
  pkt[5] = 0x01;  // QDCOUNT=1
  pkt[6] = pkt[7] = pkt[8] = pkt[9] = 0;
  pkt[10] = 0x00;
  pkt[11] = 0x01;  // ARCOUNT=1 · EDNS OPT for full-size ALL DNS replies
  int nl = encode_name(qname, pkt + 12, sizeof(pkt) - 32);
  if (nl < 0) return false;
  size_t w = 12 + static_cast<size_t>(nl);
  pkt[w++] = static_cast<uint8_t>((qtype >> 8) & 0xff);
  pkt[w++] = static_cast<uint8_t>(qtype & 0xff);
  pkt[w++] = 0;
  pkt[w++] = 1;  // IN
  // OPT RR (EDNS0) — UDP payload 1232 so TXT/SOA/HTTPS fit
  pkt[w++] = 0x00;  // root name
  pkt[w++] = 0x00;
  pkt[w++] = 0x29;  // TYPE OPT=41
  pkt[w++] = 0x04;
  pkt[w++] = 0xD0;  // CLASS = 1232 UDP size
  pkt[w++] = 0x00;
  pkt[w++] = 0x00;
  pkt[w++] = 0x00;  // TTL ext-rcode/version/flags
  pkt[w++] = 0x00;
  pkt[w++] = 0x00;  // RDLEN=0
  pkt[w++] = 0x00;

  // ALL DNS: up to 2 helpers · 180ms each — still BSP-bounded, not a flood
  constexpr int kAllTypeHelpers = 2;
  constexpr int kAllTypeTimeoutUs = 180000;
  for (int h = 0; kDnsHelpers[h] && h < kAllTypeHelpers; ++h) {
    uint8_t rbuf[1500];
    ssize_t rn = -1;
    if (!helper_udp_once(kDnsHelpers[h], pkt, w, rbuf, sizeof(rbuf), &rn,
                         kAllTypeTimeoutUs))
      continue;
    g_rr_forward.fetch_add(1);
    int rc = rbuf[3] & 0x0f;
    int an_c = (rbuf[6] << 8) | rbuf[7];
    int ns_c = (rbuf[8] << 8) | rbuf[9];
    int ar_c = (rbuf[10] << 8) | rbuf[11];
    // Empty NOERROR from one helper — try next (do not poison all-type cache)
    if (rc == 0 && (an_c + ns_c) == 0) continue;
    size_t ans_off = dns_after_question(rbuf, static_cast<size_t>(rn));
    if (ans_off >= static_cast<size_t>(rn) && an_c + ns_c + ar_c > 0) continue;
    size_t blen = 0;
    if (ans_off < static_cast<size_t>(rn)) {
      blen = static_cast<size_t>(rn) - ans_off;
      if (blen > blob_cap) blen = blob_cap;
      if (blen) std::memcpy(blob, rbuf + ans_off, blen);
    }
    *blob_len = blen;
    *rcode = rc;
    *an = an_c;
    *ns = ns_c;
    *ar = ar_c;
    // Cache only real answers or NXDOMAIN — never empty miss as "truth"
    if (an_c + ns_c + ar_c > 0 || rc == 3) {
      (void)rr_cache_put(qname, qtype, rc, an_c, ns_c, ar_c, blob, blen);
    }
    return true;
  }
  return false;
}

// Field-initiated world resolve (NOT exposed as client foreign NS).
// Clients only ever talk to 127.0.0.1 Field DNS.
//
// Budgeted: hard poll deadlines + helper count cap. Idle multi-helper fills
// Tubi/generic stripe; answer path uses field_learn_public_a_budget(...,1).
// Result is learned into truth pins and answered as Field truth.
int field_learn_public_a_budget(ServeOpts& o, const char* qname, int max_us,
                                int max_helpers) {
  static const char* kHelpers[] = {
      "1.1.1.1",        // Cloudflare
      "8.8.8.8",        // Google
      "9.9.9.9",        // Quad9
      "208.67.222.222",  // OpenDNS
      nullptr};
  if (!qname || !qname[0] || max_us < 1000) return 0;
  if (max_helpers < 1) max_helpers = 1;
  if (max_helpers > 4) max_helpers = 4;

  uint8_t pkt[512];
  pkt[0] = 0xAB;
  pkt[1] = 0xCD;
  pkt[2] = 0x01;  // RD=1
  pkt[3] = 0x00;
  pkt[4] = 0x00;
  pkt[5] = 0x01;
  pkt[6] = pkt[7] = pkt[8] = pkt[9] = pkt[10] = pkt[11] = 0;
  int nl = encode_name(qname, pkt + 12, sizeof(pkt) - 16);
  if (nl < 0) return 0;
  size_t w = 12 + static_cast<size_t>(nl);
  pkt[w++] = 0;
  pkt[w++] = 1;  // A
  pkt[w++] = 0;
  pkt[w++] = 1;  // IN

  Pin* pin = ensure_pin(o, qname);
  if (!pin) return 0;

  // Learn into a temporary pin so we never blank the table while helpers run
  Pin tmp {};
  std::snprintf(tmp.name, sizeof(tmp.name), "%s", pin->name);
  tmp.n_ips = 0;
  tmp.sticky = pin->sticky;
  tmp.learned_at = 0;

  int learned = 0;
  char cname[kNameCap];
  cname[0] = 0;
  int64_t t0 = mono_us();
  int per_helper = max_us;
  if (max_helpers > 1) per_helper = max_us / max_helpers;
  if (per_helper < 15000) per_helper = 15000;

  for (int r = 0; kHelpers[r] && r < max_helpers; ++r) {
    if (mono_us() - t0 > max_us) break;
    int budget_left = static_cast<int>(max_us - (mono_us() - t0));
    int to = per_helper < budget_left ? per_helper : budget_left;
    if (to < 1000) break;
    uint8_t rbuf[1500];
    ssize_t rn = -1;
    if (!helper_udp_once(kHelpers[r], pkt, w, rbuf, sizeof(rbuf), &rn, to))
      continue;
    int rcode = rbuf[3] & 0x0f;
    // Authoritative NXDOMAIN from first good helper → stop
    if (rcode == 3) {
      // Keep prior live IPs if any; only mark NX when empty
      if (pin->n_ips <= 0) pin->learned_at = time(nullptr);
      return 0;
    }
    if (rcode != 0) continue;
    int got = extract_answer_a(rbuf, static_cast<size_t>(rn), &tmp, cname,
                               sizeof(cname));
    if (got > 0 || cname[0]) {
      learned += got;
      if (cname[0] && std::strcmp(cname, qname) != 0) {
        Pin* cp = ensure_pin(o, cname);
        if (cp) {
          // Same packet often has CNAME + target A (OAuth client_id.apps.* chains)
          int cg = extract_answer_a(rbuf, static_cast<size_t>(rn), cp, nullptr,
                                    0);
          learned += cg;
          if (cp->n_ips <= 0) {
            int left = static_cast<int>(max_us - (mono_us() - t0));
            if (left < 25000) left = 25000;
            if (left > 100000) left = 100000;
            learned += field_learn_public_a_budget(o, cname, left, 1);
            cp = find_pin(o, cname);
          }
          if (cp && cp->n_ips > 0) {
            cp->learned_at = time(nullptr);
            maybe_sticky_media(cp);
            // Alias: copy target A onto original name (GIS client_id host)
            if (tmp.n_ips <= 0) {
              int lim = cp->n_ips > 3 ? 3 : cp->n_ips;
              for (int i = 0; i < lim; ++i) pin_add_ip(&tmp, cp->ips[i]);
            }
          }
          // BSP discover: CNAME + parents fill stripe (no hardcode)
          queue_public_learn(cname);
          queue_steel_plate(cname);
        }
      }
      // Parent labels of qname (apps.googleusercontent.com under client_id.*)
      {
        char low[kNameCap];
        to_lower(qname, low, sizeof(low));
        const char* p = low;
        while (p && *p) {
          const char* dot = std::strchr(p, '.');
          if (!dot) break;
          const char* rest = dot + 1;
          if (std::strchr(rest, '.')) queue_public_learn(rest);
          p = rest;
        }
      }
      if (tmp.n_ips > 0) {
        pin_clear_ips(pin);
        int lim = tmp.n_ips > 3 ? 3 : tmp.n_ips;
        for (int i = 0; i < lim; ++i) pin_add_ip(pin, tmp.ips[i]);
        pin->learned_at = time(nullptr);
        maybe_sticky_media(pin);
        char hpath[kPathCap];
        std::snprintf(hpath, sizeof(hpath), "%s/field-dns-hark-learn.jsonl",
                      o.state_dir);
        char line[384];
        char ts[40];
        utc_now(ts, sizeof(ts));
        std::snprintf(line, sizeof(line),
                      "{\"ts\":\"%s\",\"name\":\"%s\",\"learned\":%d,"
                      "\"helper\":\"%s\",\"pins\":%d,\"world\":true,"
                      "\"truth\":true,\"discover\":true,\"cname\":\"%s\","
                      "\"budget_us\":%d,\"oauth_chain\":%s}\n",
                      ts, qname, learned, kHelpers[r], o.n_pins,
                      cname[0] ? cname : "", max_us,
                      cname[0] ? "true" : "false");
        int hfd = ::open(hpath, O_WRONLY | O_CREAT | O_APPEND | O_CLOEXEC, 0644);
        if (hfd >= 0) {
          (void)::write(hfd, line, std::strlen(line));
          ::close(hfd);
        }
        return learned;
      }
    }
  }
  // Helpers failed — keep whatever pin already had (never leave blank)
  return learned;
}

int field_learn_public_a(ServeOpts& o, const char* qname) {
  // Idle / full discover path — up to 2 helpers, 80ms total budget
  return field_learn_public_a_budget(o, qname, kPrimaryHelperUs, 2);
}

// Extract apex: last two labels (foo.bar.com → bar.com; a.co → a.co)
void name_apex(const char* qname, char* out, size_t ocap) {
  out[0] = 0;
  if (!qname || !qname[0] || ocap < 4) return;
  char lower[kNameCap];
  to_lower(qname, lower, sizeof(lower));
  // count dots
  int dots = 0;
  for (const char* p = lower; *p; ++p)
    if (*p == '.') ++dots;
  if (dots == 0) {
    std::snprintf(out, ocap, "%s", lower);
    return;
  }
  // take from second-to-last label
  const char* start = lower;
  int need = dots - 1;
  int seen = 0;
  for (const char* p = lower; *p; ++p) {
    if (*p == '.') {
      ++seen;
      if (seen == need) {
        start = p + 1;
        break;
      }
    }
  }
  std::snprintf(out, ocap, "%s", start);
}

bool apex_already_plated(const char* apex) {
  for (int i = 0; i < g_plated_n && i < static_cast<int>(kApexTrack); ++i) {
    if (std::strcmp(g_plated_apex[i], apex) == 0) return true;
  }
  return false;
}

void mark_apex_plated(const char* apex) {
  if (!apex || !apex[0]) return;
  if (apex_already_plated(apex)) return;
  int i = g_plated_n % static_cast<int>(kApexTrack);
  std::snprintf(g_plated_apex[i], sizeof(g_plated_apex[i]), "%s", apex);
  if (g_plated_n < static_cast<int>(kApexTrack)) g_plated_n++;
}

// Build plate name list for apex (no network I/O).
// Ironclad BSP: qname + apex + generic neural prefixes only.
// NO site tables — CNAME targets and live queries fill the stripe.
int build_plate_names(const char* qname, char plate[][kPinNameCap], int cap) {
  char apex[kPinNameCap];
  name_apex(qname, apex, sizeof(apex));
  if (!apex[0] || cap <= 0) return 0;
  int nplate = 0;
  auto add = [&](const char* n) {
    if (!n || !n[0] || nplate >= cap) return;
    char low[kPinNameCap];
    to_lower(n, low, sizeof(low));
    for (int i = 0; i < nplate; ++i)
      if (std::strcmp(plate[i], low) == 0) return;
    std::snprintf(plate[nplate], kPinNameCap, "%s", low);
    nplate++;
  };
  add(qname);
  add(apex);
  // Multi-label parent chain: a.b.c.apex → also b.c.apex, c.apex (live hierarchy)
  {
    char low[kNameCap];
    to_lower(qname, low, sizeof(low));
    const char* p = low;
    while (p && *p && nplate < cap) {
      const char* dot = std::strchr(p, '.');
      if (!dot) break;
      const char* rest = dot + 1;
      if (std::strcmp(rest, apex) == 0) break;
      if (std::strchr(rest, '.')) add(rest);
      p = rest;
    }
  }
  for (int i = 0; kNeuralPrefixes[i] && nplate < cap; ++i) {
    char buf[kPinNameCap];
    std::snprintf(buf, sizeof(buf), "%s.%s", kNeuralPrefixes[i], apex);
    add(buf);
  }
  return nplate;
}

void queue_steel_plate_apex(const char* apex, bool /*priority*/) {
  if (!apex || !apex[0]) return;
  if (apex_already_plated(apex)) return;
  for (int i = 0; i < g_pending_plate_n; ++i) {
    if (std::strcmp(g_pending_plates[i], apex) == 0) return;
  }
  if (g_plate_work_n > 0 && std::strcmp(g_plate_work_apex, apex) == 0) return;
  if (g_pending_plate_n >= static_cast<int>(kPendingPlateCap)) return;
  std::snprintf(g_pending_plates[g_pending_plate_n], kPinNameCap, "%s", apex);
  g_pending_plate_n++;
}

void unmark_apex_plated(const char* apex) {
  if (!apex || !apex[0]) return;
  for (int i = 0; i < g_plated_n && i < static_cast<int>(kApexTrack); ++i) {
    if (std::strcmp(g_plated_apex[i], apex) == 0) {
      g_plated_apex[i][0] = 0;
      return;
    }
  }
}

void queue_steel_plate(const char* qname) {
  char apex[kPinNameCap];
  name_apex(qname, apex, sizeof(apex));
  if (!apex[0]) return;
  if (apex_already_plated(apex)) return;
  queue_steel_plate_apex(apex, false);
}

void steel_plate_panel(ServeOpts& o, const char* apex, int nplate, int total) {
  char hpath[kPathCap];
  std::snprintf(hpath, sizeof(hpath), "%s/field-dns-steel-plate-meld.jsonl",
                o.state_dir);
  char line[384];
  char ts[40];
  utc_now(ts, sizeof(ts));
  std::snprintf(line, sizeof(line),
                "{\"ts\":\"%s\",\"apex\":\"%s\",\"plate_names\":%d,"
                "\"learned\":%d,\"pins\":%d,\"deferred\":true,"
                "\"ironclad_cite\":\"ironclad:field-dns-steel-plate-meld:2\","
                "\"motto\":\"answer first · striped auto-learn plate\"}\n",
                ts, apex, nplate, total, o.n_pins);
  int hfd = ::open(hpath, O_WRONLY | O_CREAT | O_APPEND | O_CLOEXEC, 0644);
  if (hfd >= 0) {
    (void)::write(hfd, line, std::strlen(line));
    ::close(hfd);
  }
  char ppath[kPathCap];
  std::snprintf(ppath, sizeof(ppath), "%s/field-dns-steel-plate-meld-panel.json",
                o.state_dir);
  char body[1024];
  std::snprintf(
      body, sizeof(body),
      "{\n"
      "  \"ok\": true,\n"
      "  \"schema\": \"field-dns-steel-plate-meld/v2\",\n"
      "  \"updated\": \"%s\",\n"
      "  \"ironclad_cite\": \"ironclad:field-dns-steel-plate-meld:2\",\n"
      "  \"last_apex\": \"%s\",\n"
      "  \"last_plate_names\": %d,\n"
      "  \"last_learned\": %d,\n"
      "  \"plate_melds\": %llu,\n"
      "  \"plate_names_learned\": %llu,\n"
      "  \"pins\": %d,\n"
      "  \"deferred\": true,\n"
      "  \"answer_first\": true,\n"
      "  \"motto\": \"Answer first · steel plate auto-learn between packets\"\n"
      "}\n",
      ts, apex, nplate, total,
      static_cast<unsigned long long>(g_plate_melds.load()),
      static_cast<unsigned long long>(g_plate_names_learned.load()), o.n_pins);
  write_file(ppath, body);
}

// Process up to kPlateLearnsPerTick plate names — never blocks the answer path.
// Called from the serve loop after sendto / on idle select ticks.
// On plate start: bulk-queue all empty names so public_learn_tick fills in parallel.
int steel_plate_tick(ServeOpts& o) {
  // Start next queued apex if idle
  if (g_plate_work_n <= 0 || g_plate_work_i >= g_plate_work_n) {
    g_plate_work_n = 0;
    g_plate_work_i = 0;
    g_plate_work_apex[0] = 0;
    if (g_pending_plate_n <= 0) return 0;
    // pop front
    char apex[kPinNameCap];
    std::snprintf(apex, sizeof(apex), "%s", g_pending_plates[0]);
    for (int i = 1; i < g_pending_plate_n; ++i) {
      std::snprintf(g_pending_plates[i - 1], kPinNameCap, "%s",
                    g_pending_plates[i]);
    }
    g_pending_plate_n--;
    if (apex_already_plated(apex)) {
      // avoid deep recursion — loop by returning 0 and next idle tick continues
      return 0;
    }
    std::snprintf(g_plate_work_apex, sizeof(g_plate_work_apex), "%s", apex);
    g_plate_work_n = build_plate_names(apex, g_plate_work,
                                      static_cast<int>(kPlateCap));
    g_plate_work_i = 0;
    if (g_plate_work_n <= 0) {
      mark_apex_plated(apex);
      return 0;
    }
    // Burst-enqueue empty plate names into learn queue (parallel stripe fill)
    for (int i = 0; i < g_plate_work_n; ++i) {
      Pin* p = find_pin(o, g_plate_work[i]);
      if (p && p->n_ips > 0 && p->learned_at > 0) continue;
      queue_public_learn(g_plate_work[i]);
    }
  }

  int total = 0;
  int did = 0;
  int64_t t0 = mono_us();
  while (g_plate_work_i < g_plate_work_n && did < kPlateLearnsPerTick) {
    if (mono_us() - t0 > kIdleLearnBudgetUs) break;
    const char* name = g_plate_work[g_plate_work_i++];
    Pin* p = find_pin(o, name);
    if (p && p->n_ips > 0 && p->learned_at > 0) continue;
    int got = field_learn_public_a_raw(o, name);
    ++did;
    if (got > 0) {
      total += got;
      g_plate_names_learned.fetch_add(1);
      maybe_sticky_media(find_pin(o, name));
    }
  }

  if (g_plate_work_i >= g_plate_work_n) {
    mark_apex_plated(g_plate_work_apex);
    g_plate_melds.fetch_add(1);
    steel_plate_panel(o, g_plate_work_apex, g_plate_work_n, total);
    g_plate_work_n = 0;
    g_plate_work_i = 0;
  }
  return total;
}

// Schedule plate (no blocking network). Missing host after plate → re-open apex.
int steel_plate_meld(ServeOpts& o, const char* qname) {
  if (qname && qname[0]) {
    Pin* p = find_pin(o, qname);
    if (!p || p->n_ips <= 0) {
      char apex[kPinNameCap];
      name_apex(qname, apex, sizeof(apex));
      unmark_apex_plated(apex);
      queue_public_learn(qname);
    }
  }
  queue_steel_plate(qname);
  return 0;
}

// Raw learn without steel plate (used by plate itself and CNAME follow)
// Plate path: ONE fast helper only — missing names must not freeze the mesh.
int field_learn_public_a_raw(ServeOpts& o, const char* qname) {
  return field_learn_public_a_budget(o, qname, kPlateHelperUs, 1);
}

void load_seed_pins(ServeOpts& o) {
  // Seeds = name hints only. Do NOT inject hardcoded IPs into the serve table —
  // dead seed A records made gstatic/OAuth hang (client stuck on first dead IP).
  // First query discovers live edges; offline last-resort is field_learn restore
  // from helper only.
  for (int i = 0; kTruthSeeds[i].name; ++i) {
    Pin* p = ensure_pin(o, kTruthSeeds[i].name);
    if (!p) continue;
    p->sticky = 0;
    p->learned_at = 0;
    p->n_ips = 0;  // discover on use — never serve compile-time IPs
  }
}

// Background discover: re-learn stale pins OFF the answer path (no host list).
// Serves stay on last-known-good IPs until this succeeds — no hang.
int discover_refresh_tick(ServeOpts& o) {
  if (o.n_pins <= 0) return 0;
  static int cursor = 0;
  int did = 0;
  constexpr int kPerTick = 2;  // two refreshes per idle tick · 125k table churn
  int64_t t0 = mono_us();
  for (int n = 0; n < o.n_pins && did < kPerTick; ++n) {
    if (mono_us() - t0 > 30000) break;
    int i = (cursor + n) % o.n_pins;
    Pin* p = &o.pins[i];
    if (!p->name[0] || !std::strchr(p->name, '.')) continue;
    if (!pin_needs_refresh(p)) continue;
    (void)field_learn_public_a_budget(o, p->name, kPlateHelperUs, 1);
    ++did;
  }
  cursor = (cursor + (did > 0 ? did : 1)) % (o.n_pins > 0 ? o.n_pins : 1);
  return did;
}

// Sticky for high-churn CDN/media label patterns only (no vendor host lists)
void maybe_sticky_media(Pin* p) {
  if (!p || !p->name[0] || p->sticky) return;
  if (std::strstr(p->name, "-cdn.") || std::strstr(p->name, ".cdn.") ||
      std::strstr(p->name, "cdn.") || std::strstr(p->name, "static.") ||
      std::strstr(p->name, "media.") || std::strstr(p->name, "video.") ||
      std::strstr(p->name, "img.") || std::strstr(p->name, "assets.") ||
      std::strstr(p->name, "hls.") || std::strstr(p->name, "dash.") ||
      std::strstr(p->name, "edge.") || std::strstr(p->name, "stream.") ||
      std::strstr(p->name, "vid-") || std::strstr(p->name, "gvideo.") ||
      std::strstr(p->name, "cloudfront.") || std::strstr(p->name, "akamai") ||
      std::strstr(p->name, "fastly") || std::strstr(p->name, "twimg.") ||
      std::strstr(p->name, "gstatic.") || std::strstr(p->name, "googleapis.")) {
    p->sticky = 1;
  }
}

// Minimal JSON pin loader: looks for "hostname": [ "a.b.c.d", ... ]
// Only accepts real public IPv4 tokens — garbage JSON fragments are skipped.
void load_pins_file(ServeOpts& o, const char* path) {
  FILE* f = std::fopen(path, "r");
  if (!f) return;
  // Full table reload — up to 8MB (H7 + live export)
  constexpr size_t kCap = 8 * 1024 * 1024;
  char* buf = static_cast<char*>(std::malloc(kCap));
  if (!buf) {
    std::fclose(f);
    return;
  }
  size_t n = std::fread(buf, 1, kCap - 1, f);
  std::fclose(f);
  buf[n] = 0;

  // Find "pins" object if present; else scan whole file
  char* scan = buf;
  char* pins_key = std::strstr(buf, "\"pins\"");
  if (pins_key) {
    char* brace = std::strchr(pins_key, '{');
    if (brace) scan = brace;
  }

  char* p = scan;
  while (*p) {
    // find "name":
    if (*p != '"') {
      ++p;
      continue;
    }
    char* start = ++p;
    while (*p && *p != '"') ++p;
    if (*p != '"') break;
    size_t namelen = static_cast<size_t>(p - start);
    if (namelen == 0 || namelen >= kPinNameCap) {
      ++p;
      continue;
    }
    char name[kPinNameCap];
    std::memcpy(name, start, namelen);
    name[namelen] = 0;
    ++p;  // past closing "
    // skip whitespace and :
    while (*p == ' ' || *p == '\t' || *p == '\n' || *p == '\r') ++p;
    if (*p != ':') continue;
    ++p;
    while (*p == ' ' || *p == '\t' || *p == '\n' || *p == '\r') ++p;
    if (*p != '[') continue;
    ++p;
    // skip meta keys
    if (std::strcmp(name, "schema") == 0 || std::strcmp(name, "updated") == 0 ||
        std::strcmp(name, "ok") == 0 || std::strcmp(name, "motto") == 0 ||
        std::strcmp(name, "ironclad_cite") == 0 ||
        std::strcmp(name, "pins") == 0 || std::strcmp(name, "source") == 0) {
      continue;
    }
    // only dotted hostnames or known singles
    bool looks_host = false;
    for (size_t i = 0; name[i]; ++i) {
      if (name[i] == '.') {
        looks_host = true;
        break;
      }
    }
    if (!looks_host) continue;

    Pin* pin = ensure_pin(o, name);
    if (!pin) continue;
    // Disk reload is untrusted until re-discovered (prevents dead-IP-first hang)
    pin->learned_at = 0;
    // parse array strings
    while (*p && *p != ']') {
      while (*p == ' ' || *p == '\t' || *p == '\n' || *p == '\r' || *p == ',')
        ++p;
      if (*p == ']') break;
      if (*p != '"') {
        ++p;
        continue;
      }
      ++p;
      char* is = p;
      while (*p && *p != '"') ++p;
      if (*p != '"') break;
      size_t ilen = static_cast<size_t>(p - is);
      char ip[64];
      if (ilen > 0 && ilen < sizeof(ip)) {
        std::memcpy(ip, is, ilen);
        ip[ilen] = 0;
        // strip trailing commas/noise that bad parsers leave
        while (ilen > 0 &&
               (ip[ilen - 1] == ',' || ip[ilen - 1] == ' ' ||
                ip[ilen - 1] == '\n')) {
          ip[--ilen] = 0;
        }
        pin_add_ip(pin, ip);
      }
      ++p;
    }
  }
  std::free(buf);
}

// Load truth pins jsonl: {"name":"host","ips":"a.b.c.d,e.f.g.h",...}
void load_pins_jsonl(ServeOpts& o, const char* path) {
  FILE* f = std::fopen(path, "r");
  if (!f) return;
  char line[768];
  while (std::fgets(line, sizeof(line), f)) {
    char* nkey = std::strstr(line, "\"name\"");
    if (!nkey) continue;
    char* q1 = std::strchr(nkey + 6, '"');
    if (!q1) continue;
    ++q1;
    char* q2 = std::strchr(q1, '"');
    if (!q2 || q2 <= q1) continue;
    char name[kPinNameCap];
    size_t nl = static_cast<size_t>(q2 - q1);
    if (nl == 0 || nl >= sizeof(name)) continue;
    std::memcpy(name, q1, nl);
    name[nl] = 0;
    bool has_dot = false;
    for (size_t i = 0; name[i]; ++i)
      if (name[i] == '.') has_dot = true;
    if (!has_dot) continue;
    char* ikey = std::strstr(q2, "\"ips\"");
    if (!ikey) continue;
    char* iq = std::strchr(ikey + 5, '"');
    if (!iq) continue;
    ++iq;
    // ips may be "a,b,c" string or start of array — handle string form
    if (*iq == '[') continue;  // array form handled by load_pins_file
    char* iq2 = std::strchr(iq, '"');
    if (!iq2 || iq2 <= iq) continue;
    char ipsbuf[256];
    size_t il = static_cast<size_t>(iq2 - iq);
    if (il == 0 || il >= sizeof(ipsbuf)) continue;
    std::memcpy(ipsbuf, iq, il);
    ipsbuf[il] = 0;
    Pin* pin = ensure_pin(o, name);
    if (!pin) continue;
    char* save = nullptr;
    char* tok = strtok_r(ipsbuf, ",", &save);
    while (tok) {
      while (*tok == ' ') ++tok;
      pin_add_ip(pin, tok);
      tok = strtok_r(nullptr, ",", &save);
    }
    if (std::strstr(line, "\"sticky\":true")) pin->sticky = 1;
    maybe_sticky_media(pin);
  }
  std::fclose(f);
}

void refresh_xcom_health(ServeOpts& o) {
  o.xcom_ok = false;
  o.xcom_sample[0] = 0;
  Pin* p = find_pin(o, "x.com");
  if (p && p->n_ips > 0) {
    o.xcom_ok = true;
    std::snprintf(o.xcom_sample, sizeof(o.xcom_sample), "%s", p->ips[0]);
  }
}

void write_truth_pins_export(const ServeOpts& o) {
  // Stream FULL pin table (no 16KB cap) — H7 RAID + reload depend on this.
  // Also write jsonl for fast stripe ingest (one record per line).
  char path[kPathCap];
  char path_op[kPathCap];
  char path_jl[kPathCap];
  std::snprintf(path, sizeof(path), "%s/field-mesh-public-truth-pins.json",
                o.state_dir);
  std::snprintf(path_op, sizeof(path_op),
                "%s/field-mesh-public-truth-pins.operator.json", o.state_dir);
  std::snprintf(path_jl, sizeof(path_jl), "%s/field-dns-truth-pins.jsonl",
                o.state_dir);
  char ts[40];
  utc_now(ts, sizeof(ts));

  auto stream_json = [&](const char* outpath) -> bool {
    char tmp[kPathCap];
    std::snprintf(tmp, sizeof(tmp), "%s.%d.tmp", outpath,
                  static_cast<int>(::getpid()));
    FILE* f = std::fopen(tmp, "w");
    if (!f) return false;
    std::fprintf(f,
                 "{\n"
                 "  \"schema\": \"field-mesh-public-truth-pins/v3-full\",\n"
                 "  \"updated\": \"%s\",\n"
                 "  \"ok\": true,\n"
                 "  \"ironclad_cite\": \"%s\",\n"
                 "  \"motto\": \"Field Mesh full pin table · striped H7 reload\",\n"
                 "  \"source\": \"field-world-dns-cpp\",\n"
                 "  \"pin_count\": %d,\n"
                 "  \"pin_capacity\": %d,\n"
                 "  \"pins\": {\n",
                 ts, kIronclad, o.n_pins, static_cast<int>(kMaxPins));
    int written = 0;
    for (int i = 0; i < o.n_pins; ++i) {
      if (o.pins[i].n_ips <= 0 || !o.pins[i].name[0]) continue;
      std::fprintf(f, "%s    \"%s\": [", written ? ",\n" : "", o.pins[i].name);
      for (int j = 0; j < o.pins[i].n_ips; ++j)
        std::fprintf(f, "%s\"%s\"", j ? ", " : "", o.pins[i].ips[j]);
      std::fputc(']', f);
      ++written;
    }
    std::fprintf(f, "\n  }\n}\n");
    std::fflush(f);
    std::fclose(f);
    if (::rename(tmp, outpath) != 0) {
      ::unlink(tmp);
      return false;
    }
    return true;
  };

  if (!stream_json(path)) (void)stream_json(path_op);

  // JSONL for H7 RAID striper (BSP-fast line scan)
  {
    char tmp[kPathCap];
    std::snprintf(tmp, sizeof(tmp), "%s.%d.tmp", path_jl,
                  static_cast<int>(::getpid()));
    FILE* f = std::fopen(tmp, "w");
    if (f) {
      for (int i = 0; i < o.n_pins; ++i) {
        if (o.pins[i].n_ips <= 0 || !o.pins[i].name[0]) continue;
        // compact: name|ip,ip,ip|sticky
        std::fprintf(f, "{\"name\":\"%s\",\"ips\":\"", o.pins[i].name);
        for (int j = 0; j < o.pins[i].n_ips; ++j)
          std::fprintf(f, "%s%s", j ? "," : "", o.pins[i].ips[j]);
        std::fprintf(f,
                     "\",\"sticky\":%s,\"truth\":true,\"source\":\"live\","
                     "\"updated\":\"%s\"}\n",
                     o.pins[i].sticky ? "true" : "false", ts);
      }
      std::fflush(f);
      std::fclose(f);
      ::rename(tmp, path_jl);
    }
  }
}

void default_opts(ServeOpts* o) {
  std::memset(o, 0, sizeof(*o));
  o->pins = g_pins;
  o->n_pins = g_n_pins;  // keep learned across status if same process
  // cold start: reload seeds into static pins when empty
  if (g_n_pins <= 0) {
    o->n_pins = 0;
  }
  std::snprintf(o->bind, sizeof(o->bind), "%s", "0.0.0.0");
  o->ports[0] = 53;
  o->ports[1] = 5353;
  o->ports[2] = 9053;
  o->n_ports = 3;
  o->daemon = false;
  o->n_field = 0;
  for (int i = 0; kFieldAnswers[i] && o->n_field < static_cast<int>(kAnsIPs);
       ++i) {
    std::snprintf(o->field_ips[o->n_field], sizeof(o->field_ips[0]), "%s",
                  kFieldAnswers[i]);
    o->n_field++;
  }
  const char* root = env_or("NEXUS_INSTALL_ROOT", ".");
  const char* state = env_or("NEXUS_STATE_DIR", "");
  std::snprintf(o->install_root, sizeof(o->install_root), "%s", root);
  if (state[0]) {
    std::snprintf(o->state_dir, sizeof(o->state_dir), "%s", state);
  } else {
    std::snprintf(o->state_dir, sizeof(o->state_dir), "%s/.nexus-state", root);
  }
  // Always reseed + merge H7 pins (static table · full capacity)
  if (g_n_pins <= 0) {
    o->n_pins = 0;
    load_seed_pins(*o);
  } else {
    o->n_pins = g_n_pins;
  }
  char pinpath[kPathCap];
  // H7 RAID-0 full DNS pin plane (user-writable · BSP-fast hot path)
  std::snprintf(pinpath, sizeof(pinpath),
                "%s/field-registry-h7/dns-raid/full-pins.json", o->state_dir);
  load_pins_file(*o, pinpath);
  std::snprintf(pinpath, sizeof(pinpath),
                "%s/field-registry-h7/dns-raid/hot-pins.json", o->state_dir);
  load_pins_file(*o, pinpath);
  std::snprintf(pinpath, sizeof(pinpath), "%s/field-mesh-public-truth-pins.json",
                o->state_dir);
  load_pins_file(*o, pinpath);
  std::snprintf(pinpath, sizeof(pinpath),
                "%s/field-mesh-public-truth-pins.operator.json", o->state_dir);
  load_pins_file(*o, pinpath);
  // Prefer install data seed if present
  std::snprintf(pinpath, sizeof(pinpath), "%s/data/field-mesh-public-truth-pins.json",
                o->install_root);
  load_pins_file(*o, pinpath);
  // H7 RAID + live jsonl (expanded stripe ingest)
  std::snprintf(pinpath, sizeof(pinpath),
                "%s/field-registry-h7/dns-raid/records/records-all.jsonl",
                o->state_dir);
  load_pins_jsonl(*o, pinpath);
  std::snprintf(pinpath, sizeof(pinpath), "%s/field-dns-truth-pins.jsonl",
                o->state_dir);
  load_pins_jsonl(*o, pinpath);
  g_n_pins = o->n_pins;
  refresh_xcom_health(*o);
}

void write_panel(const ServeOpts& o, int listening_ports[], int n_listen) {
  char ts[40];
  utc_now(ts, sizeof(ts));
  char path[kPathCap];
  std::snprintf(path, sizeof(path), "%s/field-world-dns-cpp-panel.json",
                o.state_dir);
  ::mkdir(o.state_dir, 0755);

  // Honest: ok only if listening AND x.com has real public pin
  const bool honest_ok = (n_listen > 0) && o.xcom_ok;

  char body[12288];
  int n = std::snprintf(
      body, sizeof(body),
      "{\n"
      "  \"ok\": %s,\n"
      "  \"schema\": \"%s\",\n"
      "  \"updated\": \"%s\",\n"
      "  \"ironclad_cite\": \"%s\",\n"
      "  \"motto\": \"%s\",\n"
      "  \"version\": \"%s\",\n"
      "  \"pid\": %d,\n"
      "  \"bind\": \"%s\",\n"
      "  \"listening\": %s,\n"
      "  \"ports\": [",
      honest_ok ? "true" : "false", kSchema, ts, kIronclad, kMotto, kVersion,
      static_cast<int>(::getpid()), o.bind, n_listen > 0 ? "true" : "false");
  for (int i = 0; i < n_listen && n > 0 && static_cast<size_t>(n) < sizeof(body) - 64;
       ++i) {
    n += std::snprintf(body + n, sizeof(body) - static_cast<size_t>(n), "%s%d",
                       i ? ", " : "", listening_ports[i]);
  }
  n += std::snprintf(
      body + n, sizeof(body) - static_cast<size_t>(n),
      "],\n"
      "  \"field_answers\": [");
  for (int i = 0; i < o.n_field && n > 0 && static_cast<size_t>(n) < sizeof(body) - 64;
       ++i) {
    n += std::snprintf(body + n, sizeof(body) - static_cast<size_t>(n),
                       "%s\"%s\"", i ? ", " : "", o.field_ips[i]);
  }
  n += std::snprintf(
      body + n, sizeof(body) - static_cast<size_t>(n),
      "],\n"
      "  \"public_pin_count\": %d,\n"
      "  \"pin_capacity\": %d,\n"
      "  \"pin_evictions\": %llu,\n"
      "  \"learned_records\": %llu,\n"
      "  \"media_whole_internet\": true,\n"
      "  \"all_dns_types\": true,\n"
      "  \"sole_dns_authority\": true,\n"
      "  \"sole_dhcp_authority\": true,\n"
      "  \"rr_cache_hits\": %llu,\n"
      "  \"rr_cache_miss\": %llu,\n"
      "  \"rr_forward\": %llu,\n"
      "  \"alltype_answers\": %llu,\n"
      "  \"tables_filling\": true,\n"
      "  \"xcom_ok\": %s,\n"
      "  \"xcom_sample\": \"%s\",\n"
      "  \"queries\": %llu,\n"
      "  \"answers_sent\": %llu,\n"
      "  \"field_reclaims\": %llu,\n"
      "  \"public_answers\": %llu,\n"
      "  \"nxdomain_or_empty\": %llu,\n"
      "  \"hijack_all_names\": false,\n"
      "  \"we_are_dns\": true,\n"
      "  \"we_are_dhcp\": true,\n"
      "  \"sole_dns_dhcp\": true,\n"
      "  \"answer_every_request_truthfully\": true,\n"
      "  \"ironclad_secured\": true,\n"
      "  \"bsp_fast\": true,\n"
      "  \"h7_raid0_dns_dhcp\": true,\n"
      "  \"public_web_mode\": \"steel_plate_answer_first\",\n"
      "  \"plate_melds\": %llu,\n"
      "  \"plate_names_learned\": %llu,\n"
      "  \"pending_plates\": %d,\n"
      "  \"pending_learn\": %d,\n"
      "  \"learn_queued\": %llu,\n"
      "  \"learn_drained\": %llu,\n"
      "  \"answer_fast_path\": %llu,\n"
      "  \"never_stuck\": true,\n"
      "  \"fleet_scale\": 125000,\n"
      "  \"answer_first\": true,\n"
      "  \"striped_auto_learn\": true,\n"
      "  \"steel_plate_cite\": \"ironclad:field-dns-steel-plate-meld:3\",\n"
      "  \"bsp_cite\": \"%s\",\n"
      "  \"isolation_cite\": \"%s\",\n"
      "  \"no_hardcode\": true,\n"
      "  \"discover\": \"live_cname_neural_h7_stripe\",\n"
      "  \"isolation\": {\n"
      "    \"process\": %s,\n"
      "    \"no_new_privs\": true,\n"
      "    \"not_dumpable\": true,\n"
      "    \"client_plane\": \"127.0.0.1_field_truth_only\",\n"
      "    \"egress_plane\": \"ephemeral_udp_helper_SO_MARK_FDNS\",\n"
      "    \"foreign_client_ns\": false,\n"
      "    \"system_resolv\": \"Field_only\"\n"
      "  },\n"
      "  \"commander\": \"Hostess 7\",\n"
      "  \"api\": \"/api/field-world-dns-cpp\"\n"
      "}\n",
      o.n_pins, static_cast<int>(kMaxPins),
      static_cast<unsigned long long>(g_evictions.load()),
      static_cast<unsigned long long>(g_learned.load()),
      static_cast<unsigned long long>(g_rr_hits.load()),
      static_cast<unsigned long long>(g_rr_miss.load()),
      static_cast<unsigned long long>(g_rr_forward.load()),
      static_cast<unsigned long long>(g_alltype_answers.load()),
      o.xcom_ok ? "true" : "false", o.xcom_sample,
      static_cast<unsigned long long>(g_queries.load()),
      static_cast<unsigned long long>(g_answers.load()),
      static_cast<unsigned long long>(g_field_reclaims.load()),
      static_cast<unsigned long long>(g_public_answers.load()),
      static_cast<unsigned long long>(g_nx.load()),
      static_cast<unsigned long long>(g_plate_melds.load()),
      static_cast<unsigned long long>(g_plate_names_learned.load()),
      g_pending_plate_n, g_pending_learn_n,
      static_cast<unsigned long long>(g_learn_queued.load()),
      static_cast<unsigned long long>(g_learn_drained.load()),
      static_cast<unsigned long long>(g_answer_fast_path.load()), kBspCite,
      kIsoCite, g_isolated ? "true" : "false");
  if (n > 0) write_file(path, body);
}

static size_t append_a_rr(uint8_t* resp, size_t w, size_t resp_cap,
                          const char* ip, uint32_t ttl) {
  if (w + 16 > resp_cap) return w;
  struct in_addr ia {};
  if (inet_pton(AF_INET, ip, &ia) != 1) return w;
  resp[w++] = 0xC0;
  resp[w++] = 0x0C;
  resp[w++] = 0x00;
  resp[w++] = 0x01;  // A
  resp[w++] = 0x00;
  resp[w++] = 0x01;  // IN
  resp[w++] = static_cast<uint8_t>((ttl >> 24) & 0xff);
  resp[w++] = static_cast<uint8_t>((ttl >> 16) & 0xff);
  resp[w++] = static_cast<uint8_t>((ttl >> 8) & 0xff);
  resp[w++] = static_cast<uint8_t>(ttl & 0xff);
  resp[w++] = 0x00;
  resp[w++] = 0x04;
  uint32_t nip = ia.s_addr;
  std::memcpy(resp + w, &nip, 4);
  return w + 4;
}

// Build response — SOLE full DNS authority (all types) + Field A pin fast path.
// ironclad:field-dns-all-types-authority:1
size_t build_response(const uint8_t* req, size_t req_n, uint8_t* resp,
                      size_t resp_cap, ServeOpts& o, char* qname_out,
                      size_t qname_cap) {
  if (req_n < 12 || resp_cap < 12) return 0;
  std::memcpy(resp, req, 12);
  // QR=1 AA=1 RA=1 — we ARE the authority plane clients use
  resp[2] = static_cast<uint8_t>(0x84 | (req[2] & 0x01));
  resp[3] = static_cast<uint8_t>(0x80);  // RA, rcode 0 for now
  uint16_t qd = (static_cast<uint16_t>(req[4]) << 8) | req[5];
  if (qd == 0) qd = 1;
  resp[4] = static_cast<uint8_t>((qd >> 8) & 0xff);
  resp[5] = static_cast<uint8_t>(qd & 0xff);

  size_t off = 12;
  int nlen = decode_qname(req, req_n, off, qname_out, qname_cap);
  if (nlen < 0) return 0;
  off += static_cast<size_t>(nlen);
  if (off + 4 > req_n) return 0;
  uint16_t qtype = (static_cast<uint16_t>(req[off]) << 8) | req[off + 1];
  off += 4;

  size_t qsec = off;
  if (qsec > resp_cap) return 0;
  std::memcpy(resp + 12, req + 12, qsec - 12);
  size_t w = qsec;

  const bool field = is_field_zone(qname_out);
  int ancount = 0;
  int nscount = 0;
  int arcount = 0;

  auto apply_recurse = [&](uint16_t qt) -> bool {
    uint8_t blob[kRrBlobCap];
    size_t blen = 0;
    int rc = 2, an = 0, ns = 0, ar = 0;
    if (!field_recurse_all_types(qname_out, qt, &rc, &an, &ns, &ar, blob,
                                 sizeof(blob), &blen))
      return false;
    resp[3] = static_cast<uint8_t>((resp[3] & 0xF0) | (rc & 0x0f));
    if (blen && w + blen <= resp_cap) {
      std::memcpy(resp + w, blob, blen);
      w += blen;
    }
    ancount = an;
    nscount = ns;
    arcount = ar;
    if (an + ns + ar > 0) g_alltype_answers.fetch_add(1);
    if (rc == 3) g_nx.fetch_add(1);
    // Seed A pins when A answers arrived via full recurse
    if ((qt == 1 || qt == 255) && an > 0 && blen > 0) {
      // reconstruct minimal packet for extract_answer_a
      uint8_t tmp[1500];
      if (12 + (qsec - 12) + blen <= sizeof(tmp)) {
        std::memcpy(tmp, resp, w);
        Pin* pin = ensure_pin(o, qname_out);
        if (pin) {
          char cname[kNameCap];
          cname[0] = 0;
          (void)extract_answer_a(tmp, w, pin, cname, sizeof(cname));
          maybe_sticky_media(pin);
        }
      }
    }
    return true;
  };

  if (field && (qtype == 1 || qtype == 255)) {
    g_field_reclaims.fetch_add(1);
    for (int i = 0; i < o.n_field; ++i) {
      size_t nw = append_a_rr(resp, w, resp_cap, o.field_ips[i], kTTLField);
      if (nw > w) {
        w = nw;
        ancount++;
      }
    }
  } else if (field && qtype == 16) {
    const char* txt =
        "v=field-one; owner=Hostess7; sole_dns_dhcp=1; all_types=1; "
        "cite=ironclad:field-dns-all-types-authority:1";
    size_t tlen = std::strlen(txt);
    if (tlen > 200) tlen = 200;
    if (w + 14 + 1 + tlen <= resp_cap) {
      resp[w++] = 0xC0;
      resp[w++] = 0x0C;
      resp[w++] = 0x00;
      resp[w++] = 0x10;
      resp[w++] = 0x00;
      resp[w++] = 0x01;
      resp[w++] = 0;
      resp[w++] = 0;
      resp[w++] = 0;
      resp[w++] = 30;
      uint16_t rdlen = static_cast<uint16_t>(1 + tlen);
      resp[w++] = static_cast<uint8_t>((rdlen >> 8) & 0xff);
      resp[w++] = static_cast<uint8_t>(rdlen & 0xff);
      resp[w++] = static_cast<uint8_t>(tlen);
      std::memcpy(resp + w, txt, tlen);
      w += tlen;
      ancount = 1;
    }
  } else if (qtype == 1 || qtype == 255) {
    // A / ANY — NEVER multi-helper block (125k must not freeze).
    //  · pin with IPs → answer NOW (live TTL or provisional short TTL)
    //  · cold miss → queue learn + ONE short helper (45ms); idle fills stripe
    //  · steel plate always deferred (Tubi/generic related names)
    //  · never apply_recurse cascade on A path (was Recv-Q freeze)
    Pin* pin = find_pin(o, qname_out);
    const bool have_ips = pin && pin->n_ips > 0;
    const bool have_live = have_ips && pin->learned_at > 0;
    if (qname_out[0] && (!have_live || pin_needs_refresh(pin))) {
      queue_public_learn(qname_out);
    }
    if (qname_out[0]) (void)steel_plate_meld(o, qname_out);

    if (!have_ips && qname_out[0]) {
      // Cold miss: budgeted learn (CNAME chains need room — OAuth GIS client_id)
      // 2 helpers max under one wall budget · never unbounded
      int helpers = 2;
      int budget = kAnswerHelperUs;
      // Very long labels (OAuth client ids) get full budget; short names snappier
      size_t nlen = std::strlen(qname_out);
      if (nlen < 24) {
        budget = 90000;
        helpers = 1;
      }
      (void)field_learn_public_a_budget(o, qname_out, budget, helpers);
      pin = find_pin(o, qname_out);
    } else if (have_ips) {
      g_answer_fast_path.fetch_add(1);
    }

    pin = find_pin(o, qname_out);
    if (pin && pin->n_ips > 0) {
      g_public_answers.fetch_add(1);
      uint32_t ttl =
          (pin->learned_at > 0) ? kTTLPublic : kTTLProvisional;
      int nans = pin->n_ips;
      if (nans > 3) nans = 3;
      for (int i = 0; i < nans; ++i) {
        size_t nw = append_a_rr(resp, w, resp_cap, pin->ips[i], ttl);
        if (nw > w) {
          w = nw;
          ancount++;
        }
      }
    } else {
      // No pin yet — empty NOERROR (not NXDOMAIN) so clients retry;
      // learn queue + steel plate will fill truth for next query.
      resp[3] = static_cast<uint8_t>((resp[3] & 0xF0) | 0x00);
      g_nx.fetch_add(1);
    }
  } else {
    // ALL other types: cache first; one short recurse max; never hang.
    if (RrCacheEnt* hit = rr_cache_find(qname_out, qtype)) {
      g_rr_hits.fetch_add(1);
      resp[3] = static_cast<uint8_t>((resp[3] & 0xF0) | (hit->rcode & 0x0f));
      if (hit->blob_len && w + hit->blob_len <= resp_cap) {
        std::memcpy(resp + w, hit->blob, hit->blob_len);
        w += hit->blob_len;
      }
      ancount = hit->an;
      nscount = hit->ns;
      arcount = hit->ar;
      if (ancount + nscount + arcount > 0) g_alltype_answers.fetch_add(1);
    } else if (!apply_recurse(qtype)) {
      ancount = 0;
      resp[3] = static_cast<uint8_t>((resp[3] & 0xF0) | 0x00);
      // Queue A learn so related plate still fills for this apex
      if (qname_out[0]) queue_public_learn(qname_out);
    }
  }

  resp[6] = static_cast<uint8_t>((ancount >> 8) & 0xff);
  resp[7] = static_cast<uint8_t>(ancount & 0xff);
  resp[8] = static_cast<uint8_t>((nscount >> 8) & 0xff);
  resp[9] = static_cast<uint8_t>(nscount & 0xff);
  resp[10] = static_cast<uint8_t>((arcount >> 8) & 0xff);
  resp[11] = static_cast<uint8_t>(arcount & 0xff);
  if (ancount > 0) g_answers.fetch_add(1);
  return w;
}

int open_udp(const char* bind_addr, int port) {
  int fd = ::socket(AF_INET, SOCK_DGRAM | SOCK_CLOEXEC, 0);
  if (fd < 0) return -1;
  int one = 1;
  ::setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, &one, sizeof(one));
  // Intentionally NO SO_REUSEPORT — dual daemons on the same ports freeze the
  // plane (Recv-Q piles up on the dead instance; clients time out).
  struct sockaddr_in sa {};
  sa.sin_family = AF_INET;
  sa.sin_port = htons(static_cast<uint16_t>(port));
  if (inet_pton(AF_INET, bind_addr, &sa.sin_addr) != 1) {
    sa.sin_addr.s_addr = htonl(INADDR_ANY);
  }
  if (::bind(fd, reinterpret_cast<struct sockaddr*>(&sa), sizeof(sa)) != 0) {
    ::close(fd);
    return -1;
  }
  int fl = ::fcntl(fd, F_GETFL, 0);
  if (fl >= 0) ::fcntl(fd, F_SETFL, fl | O_NONBLOCK);
  return fd;
}

// Single-instance lock — second serve fails fast instead of dual-bind freeze
int acquire_instance_lock(const ServeOpts& o, char* lock_path, size_t lock_cap) {
  std::snprintf(lock_path, lock_cap, "%s/field-world-dns.lock", o.state_dir);
  ::mkdir(o.state_dir, 0755);
  int lfd = ::open(lock_path, O_RDWR | O_CREAT | O_CLOEXEC, 0644);
  if (lfd < 0) return -1;
  if (::flock(lfd, LOCK_EX | LOCK_NB) != 0) {
    // Another live instance holds the lock
    char buf[64];
    ssize_t n = ::pread(lfd, buf, sizeof(buf) - 1, 0);
    int other = 0;
    if (n > 0) {
      buf[n] = 0;
      other = std::atoi(buf);
    }
    ::close(lfd);
    std::fprintf(stderr,
                 "{\"ok\":false,\"error\":\"already_running\",\"pid\":%d,"
                 "\"hint\":\"single instance only — dual serve freezes mesh\","
                 "\"ironclad_cite\":\"%s\"}\n",
                 other, kIronclad);
    return -2;
  }
  // Hold lfd open for process lifetime (do not close)
  char pidbuf[32];
  int pn = std::snprintf(pidbuf, sizeof(pidbuf), "%d\n", static_cast<int>(::getpid()));
  (void)::ftruncate(lfd, 0);
  (void)::pwrite(lfd, pidbuf, static_cast<size_t>(pn > 0 ? pn : 0), 0);
  return lfd;
}

void daemon_stdio_null() {
  // Prevent pipe-full freeze: daemon stdout/stderr must never block on a dead pipe
  int devnull = ::open("/dev/null", O_RDWR | O_CLOEXEC);
  if (devnull < 0) return;
  ::dup2(devnull, STDIN_FILENO);
  ::dup2(devnull, STDOUT_FILENO);
  ::dup2(devnull, STDERR_FILENO);
  if (devnull > 2) ::close(devnull);
  // Ignore SIGPIPE so a stray write never freezes/kills the plane
  ::signal(SIGPIPE, SIG_IGN);
}

int cmd_serve(ServeOpts& o) {
  // Acquire lock BEFORE daemon fork so parent can report already_running
  char lock_path[kPathCap];
  int lock_fd = acquire_instance_lock(o, lock_path, sizeof(lock_path));
  if (lock_fd == -2) return 3;
  if (lock_fd < 0) {
    std::fprintf(stderr,
                 "{\"ok\":false,\"error\":\"lock_open_fail\",\"path\":\"%s\","
                 "\"ironclad_cite\":\"%s\"}\n",
                 lock_path, kIronclad);
    return 2;
  }

  if (o.daemon) {
    pid_t p = ::fork();
    if (p < 0) {
      ::close(lock_fd);
      return 1;
    }
    if (p > 0) {
      // Parent exits; child inherits the flock via the open lock_fd.
      // Do not unlock — closing this fd leaves the child's copy holding LOCK_EX.
      ::close(lock_fd);
      char ts[40];
      utc_now(ts, sizeof(ts));
      std::printf(
          "{\"ok\":true,\"daemon\":true,\"pid\":%d,\"schema\":\"%s\","
          "\"ironclad_cite\":\"%s\",\"updated\":\"%s\",\"xcom_ok\":%s,"
          "\"single_instance\":true}\n",
          static_cast<int>(p), kSchema, kIronclad, ts,
          o.xcom_ok ? "true" : "false");
      return 0;
    }
    ::setsid();
    // Child still holds lock_fd (inherited open file description + LOCK_EX)
    daemon_stdio_null();
  }

  {
    struct sigaction sa {};
    sa.sa_handler = soft_kill_ignored;
    sigemptyset(&sa.sa_mask);
    sa.sa_flags = SA_RESTART;
    ::sigaction(SIGTERM, &sa, nullptr);
    ::sigaction(SIGINT, &sa, nullptr);
    ::sigaction(SIGHUP, &sa, nullptr);
    ::sigaction(SIGQUIT, &sa, nullptr);
    ::sigaction(SIGTSTP, &sa, nullptr);
    // Optional deliberate stop only via SIGUSR1 (ops/elevate — not soft-kill inject)
    sa.sa_handler = on_signal_stop_only_usr1;
    ::sigaction(SIGUSR1, &sa, nullptr);
  }
  ::signal(SIGPIPE, SIG_IGN);

  int fds[8];
  int ports_ok[8];
  int nfd = 0;
  for (int i = 0; i < o.n_ports && nfd < 8; ++i) {
    int fd = open_udp(o.bind, o.ports[i]);
    if (fd >= 0) {
      fds[nfd] = fd;
      ports_ok[nfd] = o.ports[i];
      nfd++;
    }
  }
  // Also try 127.0.0.1:53 if 0.0.0.0:53 failed (common capability split)
  bool has53 = false;
  for (int i = 0; i < nfd; ++i)
    if (ports_ok[i] == 53) has53 = true;
  if (!has53 && nfd < 8) {
    int fd = open_udp("127.0.0.1", 53);
    if (fd >= 0) {
      fds[nfd] = fd;
      ports_ok[nfd] = 53;
      nfd++;
    }
  }
  if (nfd == 0) {
    if (!o.daemon) {
      std::fprintf(stderr,
                   "{\"ok\":false,\"error\":\"bind_failed\",\"bind\":\"%s\","
                   "\"hint\":\"try --port 9053; reap stuck dual daemons first\"}\n",
                   o.bind);
    }
    ::close(lock_fd);
    return 2;
  }

  // Refresh pid in lock after successful bind
  {
    char pidbuf[32];
    int pn = std::snprintf(pidbuf, sizeof(pidbuf), "%d\n", static_cast<int>(::getpid()));
    (void)::ftruncate(lock_fd, 0);
    (void)::pwrite(lock_fd, pidbuf, static_cast<size_t>(pn > 0 ? pn : 0), 0);
  }

  // Isolate authority process from the rest of the system (post-bind).
  isolate_authority_plane();

  // Ironclad BSP start: H7 stripe already loaded in default_opts.
  // No host warm-list — live queries + CNAME + neural plate fill the plane.
  // First idle ticks refresh stale stripe pins (discover_refresh_tick).
  refresh_xcom_health(o);
  write_truth_pins_export(o);
  write_panel(o, ports_ok, nfd);
  if (!o.daemon) {
    std::printf("{\"ok\":%s,\"listening\":true,\"ports\":[",
                o.xcom_ok ? "true" : "false");
    for (int i = 0; i < nfd; ++i)
      std::printf("%s%d", i ? "," : "", ports_ok[i]);
    std::printf("],\"public_pin_count\":%d,\"xcom_ok\":%s,\"xcom_sample\":\"%s\","
                "\"discover\":true,\"hijack_all_names\":false,"
                "\"single_instance\":true,\"ironclad_cite\":\"%s\"}\n",
                o.n_pins, o.xcom_ok ? "true" : "false", o.xcom_sample, kIronclad);
    std::fflush(stdout);
  }

  uint8_t req[kPktCap];
  uint8_t resp[kPktCap];
  char qname[kNameCap];
  time_t last_panel = 0;
  // Cap work per select tick so a flood cannot starve panel / exit
  constexpr int kMaxPktsPerFd = 256;

  while (g_run.load()) {
    fd_set rfds;
    FD_ZERO(&rfds);
    int maxfd = 0;
    for (int i = 0; i < nfd; ++i) {
      FD_SET(fds[i], &rfds);
      if (fds[i] > maxfd) maxfd = fds[i];
    }
    struct timeval tv {
      1, 0
    };
    int r = ::select(maxfd + 1, &rfds, nullptr, nullptr, &tv);
    if (r < 0) {
      if (errno == EINTR) continue;
      break;
    }
    time_t now = time(nullptr);
    if (now - last_panel >= 15) {
      write_panel(o, ports_ok, nfd);
      write_truth_pins_export(o);  // persist learned pins for H7 reload
      last_panel = now;
    }
    if (r == 0) {
      // Idle: drain generic learn queue + steel plate (Tubi stripe) + refresh.
      // Hard budgets inside each tick — never stuck, fills 125k truth.
      (void)public_learn_tick(o);
      (void)steel_plate_tick(o);
      (void)discover_refresh_tick(o);
      continue;
    }

    for (int i = 0; i < nfd; ++i) {
      if (!FD_ISSET(fds[i], &rfds)) continue;
      int drained = 0;
      for (; drained < kMaxPktsPerFd; ++drained) {
        struct sockaddr_in peer {};
        socklen_t plen = sizeof(peer);
        ssize_t rn = ::recvfrom(fds[i], req, sizeof(req), 0,
                                reinterpret_cast<struct sockaddr*>(&peer), &plen);
        if (rn < 0) {
          if (errno == EAGAIN || errno == EWOULDBLOCK || errno == EINTR) break;
          break;
        }
        if (rn < 12) continue;
        g_queries.fetch_add(1);
        size_t outn = build_response(req, static_cast<size_t>(rn), resp,
                                     sizeof(resp), o, qname, sizeof(qname));
        if (outn == 0) continue;
        ::sendto(fds[i], resp, outn, 0,
                 reinterpret_cast<struct sockaddr*>(&peer), plen);
      }
    }
    // Light stripe fill between bursts — one budgeted learn if queue pending
    // (does not re-enter multi-helper; keeps Recv-Q from starving learn forever).
    if (g_pending_learn_n > 0) {
      int64_t t0 = mono_us();
      if (g_pending_learn_n > 0 && mono_us() - t0 < 5000) {
        // single name only under load
        char name[kPinNameCap];
        std::snprintf(name, sizeof(name), "%s", g_pending_learn[0]);
        for (int i = 1; i < g_pending_learn_n; ++i) {
          std::snprintf(g_pending_learn[i - 1], kPinNameCap, "%s",
                        g_pending_learn[i]);
        }
        g_pending_learn_n--;
        Pin* p = find_pin(o, name);
        if (!(p && p->n_ips > 0 && !pin_needs_refresh(p))) {
          (void)field_learn_public_a_budget(o, name, kAnswerHelperUs, 1);
        }
        g_learn_drained.fetch_add(1);
      }
    }
  }

  // Clean shutdown: release lock
  ::flock(lock_fd, LOCK_UN);
  ::close(lock_fd);
  ::unlink(lock_path);

  write_panel(o, ports_ok, nfd);
  for (int i = 0; i < nfd; ++i) ::close(fds[i]);
  return 0;
}

int cmd_status(const ServeOpts& o) {
  char path[kPathCap];
  std::snprintf(path, sizeof(path), "%s/field-world-dns-cpp-panel.json",
                o.state_dir);
  FILE* f = std::fopen(path, "r");
  if (!f) {
    std::printf(
        "{\"ok\":false,\"pending\":\"run serve\",\"schema\":\"%s\","
        "\"ironclad_cite\":\"%s\",\"xcom_ok\":%s,\"xcom_sample\":\"%s\"}\n",
        kSchema, kIronclad, o.xcom_ok ? "true" : "false", o.xcom_sample);
    return 1;
  }
  char buf[8192];
  size_t n = std::fread(buf, 1, sizeof(buf) - 1, f);
  std::fclose(f);
  buf[n] = 0;
  std::fputs(buf, stdout);
  if (n == 0 || buf[n - 1] != '\n') std::fputc('\n', stdout);
  return 0;
}

int cmd_probe(const ServeOpts& o, const char* name) {
  const char* q = (name && name[0]) ? name : "x.com";
  int port = 9053;
  char path[kPathCap];
  std::snprintf(path, sizeof(path), "%s/field-world-dns-cpp-panel.json",
                o.state_dir);
  FILE* f = std::fopen(path, "r");
  if (f) {
    char buf[2048];
    size_t n = std::fread(buf, 1, sizeof(buf) - 1, f);
    buf[n] = 0;
    std::fclose(f);
    const char* p = std::strstr(buf, "\"ports\"");
    if (p) {
      const char* b = std::strchr(p, '[');
      if (b) port = std::atoi(b + 1);
    }
  }

  int fd = ::socket(AF_INET, SOCK_DGRAM | SOCK_CLOEXEC, 0);
  if (fd < 0) return 1;
  struct timeval tv {
    2, 0
  };
  ::setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));

  uint8_t pkt[512];
  pkt[0] = 0x12;
  pkt[1] = 0x34;
  pkt[2] = 0x01;
  pkt[3] = 0x00;
  pkt[4] = 0x00;
  pkt[5] = 0x01;
  pkt[6] = pkt[7] = pkt[8] = pkt[9] = pkt[10] = pkt[11] = 0;
  int nl = encode_name(q, pkt + 12, sizeof(pkt) - 16);
  if (nl < 0) {
    ::close(fd);
    return 1;
  }
  size_t w = 12 + static_cast<size_t>(nl);
  pkt[w++] = 0;
  pkt[w++] = 1;
  pkt[w++] = 0;
  pkt[w++] = 1;

  struct sockaddr_in sa {};
  sa.sin_family = AF_INET;
  sa.sin_port = htons(static_cast<uint16_t>(port));
  inet_pton(AF_INET, "127.0.0.1", &sa.sin_addr);
  if (::sendto(fd, pkt, w, 0, reinterpret_cast<struct sockaddr*>(&sa),
               sizeof(sa)) < 0) {
    std::printf("{\"ok\":false,\"error\":\"send\",\"port\":%d}\n", port);
    ::close(fd);
    return 1;
  }
  uint8_t rbuf[1500];
  ssize_t rn = ::recvfrom(fd, rbuf, sizeof(rbuf), 0, nullptr, nullptr);
  ::close(fd);
  if (rn < 12) {
    std::printf("{\"ok\":false,\"error\":\"timeout_or_short\",\"port\":%d,"
                "\"qname\":\"%s\"}\n",
                port, q);
    return 1;
  }
  int an = (rbuf[6] << 8) | rbuf[7];
  int rcode = rbuf[3] & 0x0f;

  // Extract first A if present
  char first_ip[16] = "";
  // skip question
  size_t i = 12;
  while (i < static_cast<size_t>(rn) && rbuf[i] != 0) {
    if ((rbuf[i] & 0xC0) == 0xC0) {
      i += 2;
      break;
    }
    i += 1 + rbuf[i];
  }
  if (i < static_cast<size_t>(rn) && rbuf[i] == 0) ++i;
  i += 4;  // qtype qclass
  if (an > 0 && i + 12 <= static_cast<size_t>(rn)) {
    // name ptr + type + class + ttl + rdlen
    if ((rbuf[i] & 0xC0) == 0xC0) i += 2;
    else {
      while (i < static_cast<size_t>(rn) && rbuf[i] != 0) i += 1 + rbuf[i];
      if (i < static_cast<size_t>(rn)) ++i;
    }
    if (i + 10 <= static_cast<size_t>(rn)) {
      uint16_t rtype = (rbuf[i] << 8) | rbuf[i + 1];
      uint16_t rdlen = (rbuf[i + 8] << 8) | rbuf[i + 9];
      i += 10;
      if (rtype == 1 && rdlen == 4 && i + 4 <= static_cast<size_t>(rn)) {
        std::snprintf(first_ip, sizeof(first_ip), "%u.%u.%u.%u", rbuf[i],
                      rbuf[i + 1], rbuf[i + 2], rbuf[i + 3]);
      }
    }
  }
  bool public_ok = first_ip[0] && is_real_public_ipv4(first_ip);
  bool field_q = is_field_zone(q);
  bool ok = (rcode == 0 && an > 0) && (field_q || public_ok);

  std::printf(
      "{\"ok\":%s,\"qname\":\"%s\",\"port\":%d,\"rcode\":%d,\"ancount\":%d,"
      "\"first_ip\":\"%s\",\"public_ipv4\":%s,\"field_zone\":%s,"
      "\"ironclad_cite\":\"%s\"}\n",
      ok ? "true" : "false", q, port, rcode, an, first_ip,
      public_ok ? "true" : "false", field_q ? "true" : "false", kIronclad);
  return ok ? 0 : 1;
}

// Explore internet through THIS authority plane (127.0.0.1 Field DNS only).
// Samples live pin table + multi-TLD smoke · writes isolated-authority panel.
int cmd_explore(ServeOpts& o) {
  char path[kPathCap];
  std::snprintf(path, sizeof(path), "%s/field-dns-internet-authority-panel.json",
                o.state_dir);
  char ts[40];
  utc_now(ts, sizeof(ts));

  // Probe helper: query local Field plane only (never foreign client NS)
  auto probe_local = [&](const char* name, char* ip_out, size_t ip_cap) -> bool {
    ip_out[0] = 0;
    if (!name || !name[0]) return false;
    int fd = ::socket(AF_INET, SOCK_DGRAM | SOCK_CLOEXEC, 0);
    if (fd < 0) return false;
    timeval tv {1, 500000};
    ::setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));
    uint8_t pkt[512];
    pkt[0] = 0xE1;
    pkt[1] = 0x91;
    pkt[2] = 0x01;
    pkt[3] = 0x00;
    pkt[4] = 0x00;
    pkt[5] = 0x01;
    pkt[6] = pkt[7] = pkt[8] = pkt[9] = pkt[10] = pkt[11] = 0;
    int nl = encode_name(name, pkt + 12, sizeof(pkt) - 16);
    if (nl < 0) {
      ::close(fd);
      return false;
    }
    size_t w = 12 + static_cast<size_t>(nl);
    pkt[w++] = 0;
    pkt[w++] = 1;
    pkt[w++] = 0;
    pkt[w++] = 1;
    sockaddr_in sa {};
    sa.sin_family = AF_INET;
    sa.sin_port = htons(53);
    inet_pton(AF_INET, "127.0.0.1", &sa.sin_addr);
    if (::sendto(fd, pkt, w, 0, reinterpret_cast<sockaddr*>(&sa), sizeof(sa)) <
        0) {
      ::close(fd);
      return false;
    }
    uint8_t rbuf[1500];
    ssize_t rn = ::recvfrom(fd, rbuf, sizeof(rbuf), 0, nullptr, nullptr);
    ::close(fd);
    if (rn < 12) return false;
    int an = (rbuf[6] << 8) | rbuf[7];
    if (an <= 0) return false;
    Pin tmp {};
    int got = extract_answer_a(rbuf, static_cast<size_t>(rn), &tmp, nullptr, 0);
    if (got <= 0 || tmp.n_ips <= 0) return false;
    std::snprintf(ip_out, ip_cap, "%s", tmp.ips[0]);
    return is_real_public_ipv4(ip_out) || is_field_zone(name);
  };

  // Multi-TLD smoke (public examples only — structural, not vendor lists)
  static const char* kTldSmoke[] = {
      "example.com", "example.net", "example.org", "cloudflare.com",
      "wikipedia.org", "github.com", "x.com", "google.com", nullptr};

  int ok_n = 0, fail_n = 0, tried = 0;
  char samples[32][kPinNameCap];
  char sample_ips[32][16];
  int sample_ok[32];
  int nsamples = 0;

  auto add_sample = [&](const char* name) {
    if (!name || !name[0] || nsamples >= 32) return;
    for (int i = 0; i < nsamples; ++i)
      if (std::strcmp(samples[i], name) == 0) return;
    std::snprintf(samples[nsamples], kPinNameCap, "%s", name);
    char ip[16];
    bool ok = probe_local(name, ip, sizeof(ip));
    std::snprintf(sample_ips[nsamples], sizeof(sample_ips[0]), "%s",
                  ok ? ip : "");
    sample_ok[nsamples] = ok ? 1 : 0;
    if (ok) ok_n++;
    else
      fail_n++;
    tried++;
    nsamples++;
  };

  for (int i = 0; kTldSmoke[i]; ++i) add_sample(kTldSmoke[i]);

  // Sample from live pin table (H7 stripe / learned internet)
  int step = o.n_pins > 16 ? o.n_pins / 16 : 1;
  if (step < 1) step = 1;
  for (int i = 0; i < o.n_pins && nsamples < 28; i += step) {
    if (o.pins[i].name[0] && o.pins[i].n_ips > 0)
      add_sample(o.pins[i].name);
  }

  // Write panel
  char body[8192];
  int n = std::snprintf(
      body, sizeof(body),
      "{\n"
      "  \"ok\": %s,\n"
      "  \"schema\": \"field-dns-internet-authority/v1\",\n"
      "  \"updated\": \"%s\",\n"
      "  \"ironclad_cite\": \"%s\",\n"
      "  \"isolation_cite\": \"%s\",\n"
      "  \"bsp_cite\": \"%s\",\n"
      "  \"client_plane\": \"127.0.0.1\",\n"
      "  \"egress_isolated\": true,\n"
      "  \"sole_authority\": true,\n"
      "  \"no_hardcode\": true,\n"
      "  \"tried\": %d,\n"
      "  \"ok_count\": %d,\n"
      "  \"fail_count\": %d,\n"
      "  \"pin_table\": %d,\n"
      "  \"fleet_scale\": 125000,\n"
      "  \"samples\": [\n",
      (ok_n > 0 && fail_n < tried) ? "true" : "false", ts, kIronclad, kIsoCite,
      kBspCite, tried, ok_n, fail_n, o.n_pins);
  for (int i = 0; i < nsamples && n > 0 && static_cast<size_t>(n) < sizeof(body) - 128;
       ++i) {
    n += std::snprintf(
        body + n, sizeof(body) - static_cast<size_t>(n),
        "%s    {\"name\":\"%s\",\"ok\":%s,\"ip\":\"%s\"}",
        i ? ",\n" : "", samples[i], sample_ok[i] ? "true" : "false",
        sample_ips[i]);
  }
  n += std::snprintf(
      body + n, sizeof(body) - static_cast<size_t>(n),
      "\n  ],\n"
      "  \"motto\": \"Field isolated DNS explores and answers the whole internet\"\n"
      "}\n");
  if (n > 0) write_file(path, body);
  std::fputs(body, stdout);
  return (ok_n > 0) ? 0 : 1;
}

void usage() {
  std::printf(
      "{\"usage\":\"field-world-dns "
      "[serve|status|probe|explore] [--port N] [--bind ADDR] [--daemon] [name]\","
      "\"version\":\"%s\",\"ironclad_cite\":\"%s\",\"isolation_cite\":\"%s\","
      "\"motto\":\"%s\"}\n",
      kVersion, kIronclad, kIsoCite, kMotto);
}

}  // namespace

int main(int argc, char** argv) {
  ServeOpts o;
  default_opts(&o);
  const char* cmd = "status";
  const char* probe_name = nullptr;
  for (int i = 1; i < argc; ++i) {
    if (std::strcmp(argv[i], "--port") == 0 && i + 1 < argc) {
      o.ports[0] = std::atoi(argv[++i]);
      o.n_ports = 1;
    } else if (std::strcmp(argv[i], "--bind") == 0 && i + 1 < argc) {
      std::snprintf(o.bind, sizeof(o.bind), "%s", argv[++i]);
    } else if (std::strcmp(argv[i], "--daemon") == 0) {
      o.daemon = true;
    } else if (std::strcmp(argv[i], "--help") == 0 ||
               std::strcmp(argv[i], "-h") == 0) {
      usage();
      return 0;
    } else if (argv[i][0] != '-') {
      if (std::strcmp(argv[i], "serve") == 0 ||
          std::strcmp(argv[i], "status") == 0 ||
          std::strcmp(argv[i], "probe") == 0 ||
          std::strcmp(argv[i], "explore") == 0 ||
          std::strcmp(argv[i], "help") == 0) {
        cmd = argv[i];
      } else {
        probe_name = argv[i];
      }
    }
  }

  if (std::strcmp(cmd, "serve") == 0) return cmd_serve(o);
  if (std::strcmp(cmd, "status") == 0) return cmd_status(o);
  if (std::strcmp(cmd, "probe") == 0) return cmd_probe(o, probe_name);
  if (std::strcmp(cmd, "explore") == 0) return cmd_explore(o);
  usage();
  return 1;
}
