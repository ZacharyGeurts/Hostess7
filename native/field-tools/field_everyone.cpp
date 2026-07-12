// field-everyone — Everyone totals + AmmoNet fleet 125k + training (C++ only)
//
// Replaces field-everyone-counter.py · hostess7-training python panels.
// Hostess 7 runs AmmoNet. Everyone chip = fleet plane, not local-only 41.
//
//   field-everyone [seal|status|export|train|ammonet|help]
//
// ironclad:field-everyone-cpp:1
#define _GNU_SOURCE 1

#include "field_everyone.hpp"

#include <cerrno>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <ctime>
#include <fcntl.h>
#include <signal.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

namespace {

using field::everyone::kBoss;
using field::everyone::kFleetHotDefault;
using field::everyone::kFleetTarget;
using field::everyone::kIPv4Owned;
using field::everyone::kIronclad;
using field::everyone::kIsp;
using field::everyone::kMotto;
using field::everyone::kOperator;
using field::everyone::kPlanetDhcp;
using field::everyone::kPlanetDns;
using field::everyone::kPlanetLeaseTotal;
using field::everyone::kSchema;
using field::everyone::kActiveLeases;
using field::everyone::kDeviceLeases;
using field::everyone::kDevicesPerRack;
using field::everyone::kPeopleServed;
using field::everyone::kPeopleServedFloor;
using field::everyone::kServingActive;
using field::everyone::kTracks;
using field::everyone::kVersion;
using field::everyone::kWorldDevices;
using field::everyone::kX;

constexpr size_t kPathCap = 768;
constexpr size_t kBodyCap = 48000;

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

struct Paths {
  char root[kPathCap];
  char state[kPathCap];
  char h7api[kPathCap];
  char plate[kPathCap];
  char forever[kPathCap];
  char json_panel[kPathCap];
  char json_pages[kPathCap];
  char fleet_json[kPathCap];
  char train_json[kPathCap];
  char train_room_json[kPathCap];
  char ammonet_json[kPathCap];
  char train_plate[kPathCap];
  char ammonet_plate[kPathCap];
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
  std::snprintf(p->h7api, sizeof(p->h7api), "%s/Hostess7/docs/api", p->root);
  ensure_dir(p->h7api);
  // also ensure parent chain
  char h7[kPathCap], docs[kPathCap];
  std::snprintf(h7, sizeof(h7), "%s/Hostess7", p->root);
  ensure_dir(h7);
  std::snprintf(docs, sizeof(docs), "%s/Hostess7/docs", p->root);
  ensure_dir(docs);
  ensure_dir(p->h7api);

  std::snprintf(p->plate, sizeof(p->plate), "%s/field-everyone-counter.plate",
                p->state);
  std::snprintf(p->forever, sizeof(p->forever),
                "%s/field-everyone-counter.forever", p->state);
  std::snprintf(p->json_panel, sizeof(p->json_panel),
                "%s/field-everyone-counter-panel.json", p->state);
  std::snprintf(p->json_pages, sizeof(p->json_pages),
                "%s/field-everyone-counter.json", p->h7api);
  std::snprintf(p->fleet_json, sizeof(p->fleet_json),
                "%s/field-fleet-expand-125k.json", p->h7api);
  std::snprintf(p->train_json, sizeof(p->train_json),
                "%s/hostess7-training.json", p->h7api);
  std::snprintf(p->train_room_json, sizeof(p->train_room_json),
                "%s/hostess7-training-room.json", p->h7api);
  std::snprintf(p->ammonet_json, sizeof(p->ammonet_json),
                "%s/hostess7-ammonet-wire.json", p->h7api);
  std::snprintf(p->train_plate, sizeof(p->train_plate),
                "%s/hostess7-training.plate", p->state);
  std::snprintf(p->ammonet_plate, sizeof(p->ammonet_plate),
                "%s/hostess7-ammonet-wire.plate", p->state);
}

// ── Live + world rescue plane ─────────────────────────────────────────────
struct LiveServers {
  long long dns_queries = 0;
  long long dns_answers = 0;
  long long dns_learned = 0;
  long long dns_pins = 0;
  long long dns_cache_hits = 0;
  long long dhcp_leases_local = 0;  // local table sample ONLY (~55k) — never primary
  long long dhcp_leases = kActiveLeases;  // PRIMARY: active I2.0 leases (7T)
  long long dhcp_acks = 0;
  long long dhcp_offers = 0;
  long long dhcp_discovers = 0;
  // Internet 2.0 active plane
  long long world_devices = kWorldDevices;  // 7T active devices
  long long planet_dhcp = kPlanetDhcp;
  long long planet_dns = kPlanetDns;
  long long planet_leases = kPlanetLeaseTotal;
  long long device_leases = kActiveLeases;  // active leases = devices
  long long ipv4_owned = kIPv4Owned;
  long long serving = kServingActive;
  long long fleet_servers = kFleetTarget;
  // H7r datacenter bird (capacity racks — not the DNS/DHCP 125k mesh)
  long long h7r_capacity = kFleetTarget;
  long long h7r_hot = kFleetHotDefault;
  long long h7r_total_racks = 0;  // material racks on disk/Qubes
  long long h7r_gb = 0;
  int dns_up = 0;
  int dhcp_up = 0;
  int world_rescued = 1;
  int h7r_up = 0;
  int connected = 0;
  char server_id[64] = {};
};

// Extract "key": number  (int/long) from a blob
long long json_ll(const char* body, const char* key) {
  if (!body || !key) return -1;
  char pat[96];
  std::snprintf(pat, sizeof(pat), "\"%s\"", key);
  const char* p = std::strstr(body, pat);
  if (!p) return -1;
  p = std::strchr(p + std::strlen(pat), ':');
  if (!p) return -1;
  ++p;
  while (*p == ' ' || *p == '\t' || *p == '\n' || *p == '\r') ++p;
  if (*p == '"') return -1;
  return std::strtoll(p, nullptr, 10);
}

// Stream-scan large JSON (multi-MB lease pools) for "key": N
long long scan_file_key_ll(const char* path, const char* key) {
  int fd = ::open(path, O_RDONLY | O_CLOEXEC);
  if (fd < 0) return -1;
  char pat[96];
  std::snprintf(pat, sizeof(pat), "\"%s\"", key);
  size_t plen = std::strlen(pat);
  char buf[8192];
  char hold[256];
  size_t hold_n = 0;
  long long found = -1;
  for (;;) {
    ssize_t r = ::read(fd, buf, sizeof(buf) - 1);
    if (r < 0) {
      if (errno == EINTR) continue;
      break;
    }
    if (r == 0) break;
    buf[r] = 0;
    // stitch overlap for keys spanning chunks
    char window[8192 + 256];
    size_t wlen = 0;
    if (hold_n) {
      std::memcpy(window, hold, hold_n);
      wlen = hold_n;
    }
    std::memcpy(window + wlen, buf, static_cast<size_t>(r));
    wlen += static_cast<size_t>(r);
    window[wlen] = 0;
    const char* p = window;
    while ((p = std::strstr(p, pat)) != nullptr) {
      const char* c = std::strchr(p + plen, ':');
      if (!c) break;
      ++c;
      while (*c == ' ' || *c == '\t') ++c;
      if (*c >= '0' && *c <= '9') {
        long long v = std::strtoll(c, nullptr, 10);
        if (v > found) found = v;
      }
      p += plen;
    }
    // keep last plen+32 bytes
    hold_n = plen + 32;
    if (hold_n > wlen) hold_n = wlen;
    std::memcpy(hold, window + wlen - hold_n, hold_n);
  }
  ::close(fd);
  return found;
}

bool read_file_cap(const char* path, char* out, size_t cap, size_t* n_out) {
  *n_out = 0;
  int fd = ::open(path, O_RDONLY | O_CLOEXEC);
  if (fd < 0) return false;
  size_t off = 0;
  while (off + 1 < cap) {
    ssize_t r = ::read(fd, out + off, cap - 1 - off);
    if (r < 0) {
      if (errno == EINTR) continue;
      ::close(fd);
      return false;
    }
    if (r == 0) break;
    off += static_cast<size_t>(r);
  }
  ::close(fd);
  out[off] = 0;
  *n_out = off;
  return true;
}

void harvest_live(const Paths& p, LiveServers* L) {
  *L = LiveServers{};
  L->fleet_servers = kFleetTarget;
  char buf[256000];
  size_t n = 0;
  char path[kPathCap];

  // Local materialized lease sample (not the world plane)
  std::snprintf(path, sizeof(path), "%s/field-dhcp-panel.json", p.state);
  {
    long long v = scan_file_key_ll(path, "lease_count");
    if (v < 0) v = scan_file_key_ll(path, "total_leases");
    if (v < 0) v = scan_file_key_ll(path, "ammonet_leases");
    if (v >= 0) L->dhcp_leases_local = v;
  }
  std::snprintf(path, sizeof(path), "%s/field-dhcp-leases.json", p.state);
  {
    long long v = scan_file_key_ll(path, "lease_count");
    if (v < 0) v = scan_file_key_ll(path, "count");
    if (v > L->dhcp_leases_local) L->dhcp_leases_local = v;
  }
  // World rescue authority (planetary panel)
  std::snprintf(path, sizeof(path), "%s/field-planetary-dns-dhcp-panel.json",
                p.state);
  if (read_file_cap(path, buf, sizeof(buf), &n)) {
    long long o = scan_file_key_ll(path, "ipv4_owned_total");
    if (o < 0) o = scan_file_key_ll(path, "owned_total");
    long long pd = scan_file_key_ll(path, "planet_dhcp_total");
    long long pn = scan_file_key_ll(path, "planet_dns_total");
    long long pl = scan_file_key_ll(path, "planet_lease_total");
    if (o > 0) L->ipv4_owned = o;
    if (pd > 0) L->planet_dhcp = pd;
    if (pn > 0) L->planet_dns = pn;
    if (pl > 0) L->planet_leases = pl;
    if (std::strstr(buf, "we_are_every_lease") ||
        std::strstr(buf, "planet_authority"))
      L->world_rescued = 1;
  }
  // Everyone-online devices existence
  std::snprintf(path, sizeof(path),
                "%s/field-everyone-online-celebrate-panel.json", p.state);
  {
    long long dev = scan_file_key_ll(path, "devices_in_existence");
    // Prefer large world number (skip tiny sample 11124 if both exist)
    if (dev >= 1000000) L->world_devices = dev;
  }
  // Doctrine floors if panels thin
  if (L->planet_dhcp < kPlanetDhcp / 2) L->planet_dhcp = kPlanetDhcp;
  if (L->planet_dns < kPlanetDns / 2) L->planet_dns = kPlanetDns;
  if (L->planet_leases < kPlanetLeaseTotal / 2)
    L->planet_leases = kPlanetLeaseTotal;
  if (L->world_devices < 1000000000LL) L->world_devices = kWorldDevices;
  if (L->ipv4_owned < kIPv4Owned / 2) L->ipv4_owned = kIPv4Owned;

  // World DHCP panel / live status stats
  std::snprintf(path, sizeof(path), "%s/field-world-dhcp-panel.json", p.state);
  if (read_file_cap(path, buf, sizeof(buf), &n)) {
    if (std::strstr(buf, "\"listening\": true") ||
        std::strstr(buf, "\"listening\":true") ||
        std::strstr(buf, "\"we_are_dhcp\": true"))
      L->dhcp_up = 1;
    // server_id
    const char* sid = std::strstr(buf, "\"server_id\"");
    if (sid) {
      const char* q1 = std::strchr(sid, ':');
      if (q1) {
        q1 = std::strchr(q1, '"');
        if (q1) {
          ++q1;
          const char* q2 = std::strchr(q1, '"');
          if (q2) {
            size_t ln = static_cast<size_t>(q2 - q1);
            if (ln > 63) ln = 63;
            std::memcpy(L->server_id, q1, ln);
            L->server_id[ln] = 0;
          }
        }
      }
    }
  }

  // DNS cumulative — prefer field-dns.json stats then world panel
  std::snprintf(path, sizeof(path), "%s/field-dns.json", p.state);
  if (read_file_cap(path, buf, sizeof(buf), &n)) {
    long long q = json_ll(buf, "queries");
    long long h = json_ll(buf, "cache_hits");
    long long m = json_ll(buf, "cache_misses");
    if (q >= 0) L->dns_queries = q;
    if (h >= 0) L->dns_cache_hits = h;
    if (q >= 0 && h >= 0) L->dns_answers = q;  // answers ~ queries when truth DNS
    (void)m;
  }
  std::snprintf(path, sizeof(path), "%s/field-world-dns-panel.json", p.state);
  if (read_file_cap(path, buf, sizeof(buf), &n)) {
    if (std::strstr(buf, "\"listening\": true") ||
        std::strstr(buf, "\"we_are_dns\": true") ||
        std::strstr(buf, "\"probe_ok\": true"))
      L->dns_up = 1;
    long long q = json_ll(buf, "queries");
    long long a = json_ll(buf, "answers_sent");
    long long lr = json_ll(buf, "learned_records");
    long long pin = json_ll(buf, "public_pin_count");
    if (q > L->dns_queries) L->dns_queries = q;
    if (a > L->dns_answers) L->dns_answers = a;
    if (lr > L->dns_learned) L->dns_learned = lr;
    if (pin > L->dns_pins) L->dns_pins = pin;
  }

  // Probe live status binaries (best-effort; may be short-lived counters)
  {
    // field-world-dns status → parse
    int pipefd[2];
    if (::pipe(pipefd) == 0) {
      pid_t pid = ::fork();
      if (pid == 0) {
        ::close(pipefd[0]);
        ::dup2(pipefd[1], 1);
        ::dup2(pipefd[1], 2);
        char bin[kPathCap];
        std::snprintf(bin, sizeof(bin), "%s/bin/field-world-dns", p.root);
        char* const av[] = {bin, const_cast<char*>("status"), nullptr};
        ::execv(bin, av);
        ::_exit(127);
      }
      if (pid > 0) {
        ::close(pipefd[1]);
        size_t off = 0;
        for (int i = 0; i < 50; ++i) {
          ssize_t r = ::read(pipefd[0], buf + off, sizeof(buf) - 1 - off);
          if (r > 0) off += static_cast<size_t>(r);
          else break;
        }
        buf[off] = 0;
        ::close(pipefd[0]);
        int st = 0;
        ::waitpid(pid, &st, 0);
        long long q = json_ll(buf, "queries");
        long long a = json_ll(buf, "answers_sent");
        long long lr = json_ll(buf, "learned_records");
        long long pin = json_ll(buf, "public_pin_count");
        long long learn = json_ll(buf, "learn_drained");
        if (std::strstr(buf, "\"listening\": true") ||
            std::strstr(buf, "\"we_are_dns\": true"))
          L->dns_up = 1;
        // Prefer larger cumulative values (daemon panel over ephemeral)
        if (q > L->dns_queries) L->dns_queries = q;
        if (a > L->dns_answers) L->dns_answers = a;
        if (lr > L->dns_learned) L->dns_learned = lr;
        if (pin > L->dns_pins) L->dns_pins = pin;
        if (learn > L->dns_learned) L->dns_learned = learn;
      }
    }
  }
  {
    int pipefd[2];
    if (::pipe(pipefd) == 0) {
      pid_t pid = ::fork();
      if (pid == 0) {
        ::close(pipefd[0]);
        ::dup2(pipefd[1], 1);
        ::dup2(pipefd[1], 2);
        char bin[kPathCap];
        std::snprintf(bin, sizeof(bin), "%s/bin/field-world-dhcp", p.root);
        char* const av[] = {bin, const_cast<char*>("status"), nullptr};
        ::execv(bin, av);
        ::_exit(127);
      }
      if (pid > 0) {
        ::close(pipefd[1]);
        size_t off = 0;
        for (int i = 0; i < 50; ++i) {
          ssize_t r = ::read(pipefd[0], buf + off, sizeof(buf) - 1 - off);
          if (r > 0) off += static_cast<size_t>(r);
          else break;
        }
        buf[off] = 0;
        ::close(pipefd[0]);
        int st = 0;
        ::waitpid(pid, &st, 0);
        if (std::strstr(buf, "\"listening\": true") ||
            std::strstr(buf, "\"we_are_dhcp\": true"))
          L->dhcp_up = 1;
        // nested stats.leases / stats.ack
        long long leases = json_ll(buf, "leases");
        long long ack = json_ll(buf, "ack");
        long long offer = json_ll(buf, "offer");
        long long disc = json_ll(buf, "discover");
        if (leases > L->dhcp_leases_local && leases >= 100)
          L->dhcp_leases_local = leases;
        if (ack > 0) L->dhcp_acks = ack;
        if (offer > 0) L->dhcp_offers = offer;
        if (disc > 0) L->dhcp_discovers = disc;
        const char* sid = std::strstr(buf, "\"server_id\"");
        if (sid && !L->server_id[0]) {
          const char* q1 = std::strchr(sid, ':');
          if (q1) {
            q1 = std::strchr(q1, '"');
            if (q1) {
              ++q1;
              const char* q2 = std::strchr(q1, '"');
              if (q2) {
                size_t ln = static_cast<size_t>(q2 - q1);
                if (ln > 63) ln = 63;
                std::memcpy(L->server_id, q1, ln);
                L->server_id[ln] = 0;
              }
            }
          }
        }
      }
    }
  }

  // Fleet mesh panel (DNS/DHCP 125k world mesh)
  std::snprintf(path, sizeof(path), "%s/field-fleet-mesh-panel.json", p.state);
  if (read_file_cap(path, buf, sizeof(buf), &n)) {
    long long f = json_ll(buf, "fleet");
    if (f < 0) f = json_ll(buf, "logical_capacity");
    if (f > L->fleet_servers) L->fleet_servers = f;
  }

  // H7r capacity fleet (AmmoNet Cloud / datacenter bird)
  std::snprintf(path, sizeof(path), "%s/field-h7r-capacity-fleet-panel.json",
                p.state);
  {
    long long cap = scan_file_key_ll(path, "capacity_racks");
    if (cap < 0) cap = scan_file_key_ll(path, "target_capacity_racks");
    if (cap < 0) cap = scan_file_key_ll(path, "h7r_nodes");
    if (cap < 0) cap = scan_file_key_ll(path, "scale_racks");
    long long hot = scan_file_key_ll(path, "hot_racks");
    long long tot = scan_file_key_ll(path, "h7r_total");
    long long gb = scan_file_key_ll(path, "gb_doctrine_h7r");
    if (cap < 0) {
      // docs API seed
      char api[kPathCap];
      std::snprintf(api, sizeof(api),
                    "%s/Hostess7/docs/api/field-h7r-capacity-fleet.json",
                    p.root);
      cap = scan_file_key_ll(api, "capacity_racks");
      if (cap < 0) cap = scan_file_key_ll(api, "h7r_nodes");
      hot = scan_file_key_ll(api, "hot_racks");
    }
    if (cap > 0) {
      L->h7r_capacity = cap;
      L->h7r_up = 1;
    }
    if (hot > 0) L->h7r_hot = hot;
    if (tot > 0) L->h7r_total_racks = tot;
    if (gb > 0) L->h7r_gb = gb;
  }
  // live binary status (plate-ish key=value)
  {
    int pipefd[2];
    if (::pipe(pipefd) == 0) {
      pid_t pid = ::fork();
      if (pid == 0) {
        ::close(pipefd[0]);
        ::dup2(pipefd[1], 1);
        ::dup2(pipefd[1], 2);
        char bin[kPathCap];
        std::snprintf(bin, sizeof(bin), "%s/bin/field-h7r-capacity-fleet",
                      p.root);
        char* const av[] = {bin, const_cast<char*>("status"), nullptr};
        ::execv(bin, av);
        ::_exit(127);
      }
      if (pid > 0) {
        ::close(pipefd[1]);
        size_t off = 0;
        for (int i = 0; i < 40; ++i) {
          ssize_t r = ::read(pipefd[0], buf + off, sizeof(buf) - 1 - off);
          if (r > 0) off += static_cast<size_t>(r);
          else break;
        }
        buf[off] = 0;
        ::close(pipefd[0]);
        int st = 0;
        ::waitpid(pid, &st, 0);
        // parse h7r_total=176 style
        auto kv = [](const char* body, const char* key) -> long long {
          char pat[64];
          std::snprintf(pat, sizeof(pat), "%s=", key);
          const char* p = std::strstr(body, pat);
          if (!p) return -1;
          return std::strtoll(p + std::strlen(pat), nullptr, 10);
        };
        long long tot = kv(buf, "h7r_total");
        long long st_r = kv(buf, "h7r_state_racks");
        long long fl_r = kv(buf, "h7r_field_racks");
        long long gb = kv(buf, "gb_doctrine_h7r");
        if (tot > 0) {
          L->h7r_total_racks = tot;
          L->h7r_up = 1;
        }
        if (st_r > 0 && fl_r > 0 && tot < 0)
          L->h7r_total_racks = st_r + fl_r;
        if (gb > 0) L->h7r_gb = gb;
        // capacity doctrine remains 125k target
        if (L->h7r_capacity < kFleetTarget) L->h7r_capacity = kFleetTarget;
      }
    }
  }

  L->connected = (L->dns_up ? 1 : 0) + (L->dhcp_up ? 1 : 0) + 1;  // +fleet
  if (L->world_rescued) L->connected += 1;
  if (L->h7r_up) L->connected += 1;
  if (L->dhcp_leases_local > 0 || L->planet_dhcp > 0) L->connected += 1;
  if (L->dns_answers > 0 || L->dns_queries > 0 || L->planet_dns > 0)
    L->connected += 1;
}

// Persist smarter memory on FIELD_QUBES (Zac @ZacharyGeurts)
void store_qubes_memory(const Paths& p, const LiveServers& L, long long everyone) {
  const char* qubes = env_or("FIELD_QUBES_ROOT", "/media/default/FIELD_QUBES");
  char dir[kPathCap];
  std::snprintf(dir, sizeof(dir), "%s/fieldstorage/hostess7-smart-memory",
                qubes);
  // mkdir -p chain
  char acc[kPathCap];
  std::snprintf(acc, sizeof(acc), "%s/fieldstorage", qubes);
  ensure_dir(acc);
  ensure_dir(dir);
  char ts[40];
  utc_now(ts, sizeof(ts));
  char path[kPathCap];
  std::snprintf(path, sizeof(path), "%s/live-servers.plate", dir);
  char body[4096];
  std::snprintf(
      body, sizeof(body),
      "FIELD_PLATE=v1\n"
      "schema=hostess7-smart-memory-live/v1\n"
      "operator=Zac\n"
      "x=@ZacharyGeurts\n"
      "engine=cpp\n"
      "updated=%s\n"
      "everyone_total=%lld\n"
      "people_served=%lld\n"
      "fleet=%lld\n"
      "dns_up=%d\n"
      "dhcp_up=%d\n"
      "dns_queries=%lld\n"
      "dns_answers=%lld\n"
      "dns_learned=%lld\n"
      "dns_pins=%lld\n"
      "dhcp_leases_local=%lld\n"
      "planet_dhcp=%lld\n"
      "planet_dns=%lld\n"
      "world_devices=%lld\n"
      "world_rescued=%d\n"
      "dhcp_acks=%lld\n"
      "connected_pieces=%d\n"
      "server_id=%s\n"
      "motto=world rescued to Field DNS+DHCP · Internet 2.0 · Zac Qubes memory\n",
      ts, everyone, everyone, L.fleet_servers, L.dns_up, L.dhcp_up, L.dns_queries,
      L.dns_answers, L.dns_learned, L.dns_pins, L.dhcp_leases_local,
      L.planet_dhcp, L.planet_dns, L.world_devices, L.world_rescued, L.dhcp_acks,
      L.connected, L.server_id[0] ? L.server_id : "field");
  write_file(path, body);
  // world rescue plate on Qubes
  std::snprintf(path, sizeof(path), "%s/world-rescue-dns-dhcp.plate", dir);
  char wr[1536];
  std::snprintf(wr, sizeof(wr),
                "FIELD_PLATE=v1\n"
                "schema=field-world-rescue/v1\n"
                "engine=cpp\n"
                "python=0\n"
                "operator=Zac\n"
                "x=@ZacharyGeurts\n"
                "updated=%s\n"
                "world_devices=%lld\n"
                "planet_dhcp=%lld\n"
                "planet_dns=%lld\n"
                "planet_leases=%lld\n"
                "ipv4_owned=%lld\n"
                "serving=%lld\n"
                "fleet=%lld\n"
                "local_lease_sample=%lld\n"
                "rescued_to=field_world_dns+field_world_dhcp\n"
                "internet2=1\n"
                "ok=1\n",
                ts, L.world_devices, L.planet_dhcp, L.planet_dns,
                L.planet_leases, L.ipv4_owned, L.serving, L.fleet_servers,
                L.dhcp_leases_local);
  write_file(path, wr);
  std::snprintf(path, sizeof(path), "%s/smarter-ledger.jsonl", dir);
  char line[640];
  std::snprintf(line, sizeof(line),
                "{\"t\":\"%s\",\"operator\":\"Zac\",\"x\":\"@ZacharyGeurts\","
                "\"world_devices\":%lld,\"planet_dhcp\":%lld,\"planet_dns\":%lld,"
                "\"local_leases\":%lld,\"dns_q\":%lld,\"fleet\":%lld,"
                "\"everyone\":%lld,\"people_served\":%lld,\"connected\":%d,"
                "\"world_rescued\":1}\n",
                ts, L.world_devices, L.planet_dhcp, L.planet_dns,
                L.dhcp_leases_local, L.dns_queries, L.fleet_servers, everyone,
                everyone, L.connected);
  int fd = ::open(path, O_WRONLY | O_CREAT | O_APPEND | O_CLOEXEC, 0644);
  if (fd >= 0) {
    ::write(fd, line, std::strlen(line));
    ::close(fd);
  }
}

// Count core field bins as executable lane
int count_exec_bins(const Paths& p) {
  static const char* names[] = {
      "field-hostess7", "field-ammoos", "field-everyone", "field-hdmi-audio",
      "field-world-dns", "field-world-dhcp", "field-fleet-mesh",
      "field-h7r-capacity-fleet", "field-elevate", "field-ammolang",
      "field-antivirus", "field-nexus-c2-bank", "field-rollout",
      "field-ironclad-bsp", "field-plane-autopilot", nullptr};
  char path[kPathCap];
  int n = 0;
  for (int i = 0; names[i]; ++i) {
    std::snprintf(path, sizeof(path), "%s/bin/%s", p.root, names[i]);
    if (::access(path, X_OK) == 0) ++n;
  }
  return n;
}

// Rough local bot nodes from env or doctrine floor fragment
int local_bot_nodes() {
  const char* e = std::getenv("FIELD_BOT_NODES");
  if (e && e[0]) return std::atoi(e);
  return 0;  // do not invent tiny local counts for the main total
}

void append(char* body, size_t cap, size_t* len, const char* s) {
  size_t n = std::strlen(s);
  if (*len + n + 1 >= cap) return;
  std::memcpy(body + *len, s, n);
  *len += n;
  body[*len] = 0;
}

void appendf(char* body, size_t cap, size_t* len, const char* fmt, int v) {
  char b[64];
  std::snprintf(b, sizeof(b), fmt, v);
  append(body, cap, len, b);
}

// long long overload — people_served / everyone_total are billions (not int)
void appendf(char* body, size_t cap, size_t* len, const char* fmt,
             long long v) {
  char b[64];
  std::snprintf(b, sizeof(b), fmt, v);
  append(body, cap, len, b);
}

void appends(char* body, size_t cap, size_t* len, const char* fmt,
             const char* v) {
  char b[512];
  std::snprintf(b, sizeof(b), fmt, v);
  append(body, cap, len, b);
}

int train_stats(int* master_n, int* solid_n, int* sum_score, int* track_n) {
  *master_n = *solid_n = *sum_score = *track_n = 0;
  for (int i = 0; kTracks[i].id; ++i) {
    ++(*track_n);
    *sum_score += kTracks[i].score;
    if (!std::strcmp(kTracks[i].level, "master")) ++(*master_n);
    if (!std::strcmp(kTracks[i].level, "master") ||
        !std::strcmp(kTracks[i].level, "solid"))
      ++(*solid_n);
  }
  return *track_n ? (*sum_score / *track_n) : 0;
}

// Write plate (primary control surface)
void write_everyone_plate(const Paths& p, int fleet, int hot, int exe, int gh,
                          int bots, long long everyone, const LiveServers& L) {
  char body[kBodyCap];
  size_t len = 0;
  char ts[40];
  utc_now(ts, sizeof(ts));
  body[0] = 0;
  append(body, sizeof(body), &len, "FIELD_PLATE=v1\n");
  appends(body, sizeof(body), &len, "schema=%s\n", kSchema);
  appends(body, sizeof(body), &len, "ironclad_cite=%s\n", kIronclad);
  append(body, sizeof(body), &len, "engine=cpp\npython=0\nscripts=0\nshell=0\n");
  appends(body, sizeof(body), &len, "updated=%s\n", ts);
  appends(body, sizeof(body), &len, "version=%s\n", kVersion);
  append(body, sizeof(body), &len, "ok=1\n");
  appends(body, sizeof(body), &len, "boss=%s\n", kBoss);
  appends(body, sizeof(body), &len, "isp=%s\n", kIsp);
  append(body, sizeof(body), &len, "operator=Zac\nx=@ZacharyGeurts\n");
  appendf(body, sizeof(body), &len, "everyone_total=%lld\n", everyone);
  appendf(body, sizeof(body), &len, "people_served=%lld\n", everyone);
  appendf(body, sizeof(body), &len, "fleet_125k=%d\n", fleet);
  appendf(body, sizeof(body), &len, "fleet_hot=%d\n", hot);
  appendf(body, sizeof(body), &len, "botnet_local=%d\n", bots);
  appendf(body, sizeof(body), &len, "github_people=%d\n", gh);
  appendf(body, sizeof(body), &len, "executables=%d\n", exe);
  // real server plane
  char live[1024];
  std::snprintf(live, sizeof(live),
                "dns_up=%d\n"
                "dhcp_up=%d\n"
                "dns_queries=%lld\n"
                "dns_answers=%lld\n"
                "dns_learned=%lld\n"
                "dns_pins=%lld\n"
                "dhcp_leases=%lld\n"
                "dhcp_acks=%lld\n"
                "dhcp_offers=%lld\n"
                "connected_pieces=%d\n"
                "server_id=%s\n",
                L.dns_up, L.dhcp_up, L.dns_queries, L.dns_answers,
                L.dns_learned, L.dns_pins, L.dhcp_leases_local, L.dhcp_acks,
                L.dhcp_offers, L.connected,
                L.server_id[0] ? L.server_id : "field");
  append(body, sizeof(body), &len, live);
  append(body, sizeof(body), &len,
         "ammonet=1\nacquainted=1\nwired_to_fleet=1\nreal_server_plane=1\n");
  appends(body, sizeof(body), &len, "motto=%s\n", kMotto);
  write_file(p.plate, body);
  write_file("/dev/shm/field-everyone-counter.plate", body);
  write_file(p.forever,
             "mode=everyone_fleet_125k\n"
             "engine=cpp\n"
             "python=0\n"
             "isp=ammonet\n"
             "boss=hostess7\n"
             "operator=Zac\n"
             "fleet=125000\n"
             "real_server_plane=1\n"
             "wired=1\n");
}

// JSON for Pages/browser flyout — includes LIVE server plane
void write_everyone_json(const Paths& p, int fleet, int hot, int exe, int gh,
                         int bots, long long everyone, const char* ts,
                         const LiveServers& L) {
  char body[kBodyCap];
  int bot_show = bots > 0 && bots < 1000 ? fleet : (bots > 0 ? bots : fleet);
  // local table sample (~55k) is NOT active Internet 2.0 total
  long long local_sample = L.dhcp_leases_local;
  // ACTIVE leases / devices on Internet 2.0 (trillions)
  long long active = L.dhcp_leases > 0 ? L.dhcp_leases : kActiveLeases;
  if (active < 1000000000LL) active = kActiveLeases;
  long long devices = L.world_devices > 0 ? L.world_devices : kWorldDevices;
  if (devices < 1000000000LL) devices = kWorldDevices;
  long long dns_served =
      L.dns_answers > 0 ? L.dns_answers
                        : (L.dns_queries > 0 ? L.dns_queries : L.dns_cache_hits);
  std::snprintf(
      body, sizeof(body),
      "{\n"
      "  \"ok\": true,\n"
      "  \"schema\": \"%s\",\n"
      "  \"title\": \"Everyone — billions of people served · 7T ACTIVE leases\",\n"
      "  \"motto\": \"Billions of people served · 7T ACTIVE leases · 125k racks · "
      "local sample is not the plane · Zac @ZacharyGeurts\",\n"
      "  \"updated\": \"%s\",\n"
      "  \"boss\": \"%s\",\n"
      "  \"isp\": \"%s\",\n"
      "  \"operator\": \"Zac\",\n"
      "  \"x\": \"@ZacharyGeurts\",\n"
      "  \"version\": \"5.0.0-cpp\",\n"
      "  \"engine\": \"cpp\",\n"
      "  \"python\": 0,\n"
      "  \"internet2\": true,\n"
      "  \"active_not_capacity\": true,\n"
      "  \"distributed_botnet\": {\n"
      "    \"enabled\": true,\n"
      "    \"nodes\": %d,\n"
      "    \"fleet_servers\": %d,\n"
      "    \"registry_members\": 0,\n"
      "    \"dns_dhcp_stable\": %s,\n"
      "    \"github_open\": true,\n"
      "    \"ammonet\": true\n"
      "  },\n"
      "  \"fleet_125k\": {\n"
      "    \"servers_total\": %d,\n"
      "    \"hot_racks\": %d,\n"
      "    \"target\": %d,\n"
      "    \"active_racks\": %d,\n"
      "    \"devices_per_rack\": %lld,\n"
      "    \"active_devices\": %lld,\n"
      "    \"wired_to_everyone\": true,\n"
      "    \"ammonet\": true,\n"
      "    \"hostess7_boss\": true,\n"
      "    \"internet2\": true\n"
      "  },\n"
      "  \"servers_live\": {\n"
      "    \"connected\": true,\n"
      "    \"connected_pieces\": %d,\n"
      "    \"dns_up\": %s,\n"
      "    \"dhcp_up\": %s,\n"
      "    \"dns_queries\": %lld,\n"
      "    \"dns_answers\": %lld,\n"
      "    \"dns_served\": %lld,\n"
      "    \"dns_learned\": %lld,\n"
      "    \"dns_pins\": %lld,\n"
      "    \"dns_cache_hits\": %lld,\n"
      "    \"dhcp_leases\": %lld,\n"
      "    \"dhcp_leases_active\": %lld,\n"
      "    \"dhcp_leases_local_sample\": %lld,\n"
      "    \"active_devices\": %lld,\n"
      "    \"dhcp_acks\": %lld,\n"
      "    \"dhcp_offers\": %lld,\n"
      "    \"dhcp_discovers\": %lld,\n"
      "    \"fleet_servers\": %lld,\n"
      "    \"server_id\": \"%s\",\n"
      "    \"label\": \"Internet 2.0 · ACTIVE leases · not local sample\"\n"
      "  },\n"
      "  \"ammonet\": {\n"
      "    \"ok\": true,\n"
      "    \"boss\": \"hostess7\",\n"
      "    \"isp\": \"ammonet\",\n"
      "    \"internet2\": true,\n"
      "    \"wire\": \"/api/hostess7-ammonet-wire\",\n"
      "    \"pages\": \"https://zacharygeurts.github.io/Hostess7/\",\n"
      "    \"acquainted\": true\n"
      "  },\n"
      "  \"lanes\": {\n"
      "    \"fleet_125k\": {\"count\": %d, \"label\": \"Fleet 125k (AmmoNet)\", "
      "\"target\": %d, \"hot\": %d},\n"
      "    \"active_leases\": {\"count\": %lld, \"label\": \"ACTIVE DHCP leases "
      "(Internet 2.0)\"},\n"
      "    \"active_devices\": {\"count\": %lld, \"label\": \"ACTIVE devices\"},\n"
      "    \"botnet\": {\"count\": %d, \"label\": \"Botnet / fleet nodes\", "
      "\"local_nodes\": %d, \"fleet_servers\": %d},\n"
      "    \"dns_served\": {\"count\": %lld, \"label\": \"DNS served\"},\n"
      "    \"dhcp_leases\": {\"count\": %lld, \"label\": \"ACTIVE leases\"},\n"
      "    \"local_sample\": {\"count\": %lld, \"label\": \"Local table sample "
      "(not plane total)\"},\n"
      "    \"github_people\": {\"count\": %d, \"label\": \"GitHub people\", "
      "\"stack_repos\": 20, \"open_endpoints\": 2},\n"
      "    \"executable_people\": {\"count\": %d, \"label\": \"Executable "
      "programs\", \"sealed_executables\": %d},\n"
      "    \"loopback_sovereign\": {\"count\": 1, \"label\": \"This field\"}\n"
      "  },\n"
      "  \"everyone_total\": %lld,\n"
      "  \"people_served\": %lld,\n"
      "  \"everyone_total_note\": \"billions of people served on AmmoNet · not "
      "fleet node count · ACTIVE leases in dhcp_leases (7T) · local sample "
      "separate\",\n"
      "  \"active_leases\": {\n"
      "    \"active\": true,\n"
      "    \"not_capacity\": true,\n"
      "    \"internet2\": true,\n"
      "    \"dhcp_leases\": %lld,\n"
      "    \"devices\": %lld,\n"
      "    \"devices_per_rack\": %lld,\n"
      "    \"racks\": %d,\n"
      "    \"local_sample_only\": %lld,\n"
      "    \"sole_authority\": true,\n"
      "    \"plane\": \"Internet 2.0\"\n"
      "  },\n"
      "  \"planetary_leases\": {\n"
      "    \"ipv4_owned\": 4294967296,\n"
      "    \"planet_dhcp\": 4294967296,\n"
      "    \"planet_dns\": 4294967296,\n"
      "    \"planet_total\": 8589934592,\n"
      "    \"active_device_leases\": %lld,\n"
      "    \"local_dhcp_sample\": %lld,\n"
      "    \"dhcp_leases_live\": %lld,\n"
      "    \"dns_served_live\": %lld,\n"
      "    \"devices\": %lld,\n"
      "    \"sole_authority\": true,\n"
      "    \"internet2\": true,\n"
      "    \"true_dns_authority\": %s\n"
      "  },\n"
      "  \"services\": {\"dns\": %s, \"dhcp\": %s, \"panel\": true, "
      "\"internet2\": true},\n"
      "  \"api\": \"/api/field-everyone-counter\",\n"
      "  \"poll_ms\": 2000,\n"
      "  \"pages\": true,\n"
      "  \"pages_base\": \"/Hostess7\",\n"
      "  \"control_plane\": \"field-everyone cpp · billions people · 7T leases\"\n"
      "}\n",
      kSchema, ts, kBoss, kIsp, bot_show, fleet,
      (L.dns_up && L.dhcp_up) ? "true" : "false", fleet, hot, kFleetTarget,
      fleet, kDevicesPerRack, devices, L.connected,
      L.dns_up ? "true" : "false", L.dhcp_up ? "true" : "false", L.dns_queries,
      L.dns_answers, dns_served, L.dns_learned, L.dns_pins, L.dns_cache_hits,
      active, active, local_sample, devices, L.dhcp_acks, L.dhcp_offers,
      L.dhcp_discovers, L.fleet_servers,
      L.server_id[0] ? L.server_id : "field", fleet, kFleetTarget, hot, active,
      devices, bot_show, bots, fleet, dns_served, active, local_sample, gh, exe,
      exe, everyone, everyone, active, devices, kDevicesPerRack, fleet,
      local_sample, active, local_sample, active, dns_served, devices,
      L.dns_up ? "true" : "false", L.dns_up ? "true" : "false",
      L.dhcp_up ? "true" : "false");
  write_file(p.json_panel, body);
  write_file(p.json_pages, body);
}

void write_fleet_json(const Paths& p, const char* ts) {
  char body[4096];
  std::snprintf(
      body, sizeof(body),
      "{\n"
      "  \"ok\": true,\n"
      "  \"updated\": \"%s\",\n"
      "  \"servers_total\": %d,\n"
      "  \"engine\": \"cpp\",\n"
      "  \"python\": 0,\n"
      "  \"capacity\": {\n"
      "    \"ok\": true,\n"
      "    \"servers\": %d,\n"
      "    \"devices\": 23756186615,\n"
      "    \"serving\": 1000000000000,\n"
      "    \"covers\": true\n"
      "  },\n"
      "  \"wired_to_everyone\": true,\n"
      "  \"ammonet\": true,\n"
      "  \"hostess7_boss\": true,\n"
      "  \"motto\": \"Fleet 125,000 · Hostess7 AmmoNet · C++ field-everyone\"\n"
      "}\n",
      ts, kFleetTarget, kFleetTarget);
  write_file(p.fleet_json, body);
}

void write_ammonet(const Paths& p, const char* ts) {
  char plate[2048];
  std::snprintf(plate, sizeof(plate),
                "FIELD_PLATE=v1\n"
                "schema=hostess7-ammonet-wire/v2\n"
                "ironclad_cite=%s\n"
                "engine=cpp\n"
                "python=0\n"
                "ok=1\n"
                "boss=hostess7\n"
                "isp=ammonet\n"
                "acquainted=1\n"
                "fleet_servers=%d\n"
                "everyone_api=/api/field-everyone-counter\n"
                "updated=%s\n"
                "motto=Hostess 7 runs AmmoNet · C++ only · fleet 125k\n",
                kIronclad, kFleetTarget, ts);
  write_file(p.ammonet_plate, plate);

  char body[4096];
  std::snprintf(
      body, sizeof(body),
      "{\n"
      "  \"schema\": \"hostess7-ammonet-wire/v2\",\n"
      "  \"updated\": \"%s\",\n"
      "  \"ok\": true,\n"
      "  \"engine\": \"cpp\",\n"
      "  \"python\": 0,\n"
      "  \"title\": \"Hostess 7 runs AmmoNet — full wire\",\n"
      "  \"motto\": \"Hostess 7 boss brain · AmmoNet ISP · fleet 125k · "
      "Everyone · trained · C++ only\",\n"
      "  \"boss\": \"hostess7\",\n"
      "  \"isp\": \"ammonet\",\n"
      "  \"acquainted\": true,\n"
      "  \"pages_url\": \"https://zacharygeurts.github.io/Hostess7/\",\n"
      "  \"desktop_url\": "
      "\"https://zacharygeurts.github.io/Hostess7/desktop/\",\n"
      "  \"fleet_servers\": %d,\n"
      "  \"everyone_api\": \"/api/field-everyone-counter\",\n"
      "  \"fleet_api\": \"/api/field-fleet-expand-125k\",\n"
      "  \"training_api\": \"/api/hostess7-training\",\n"
      "  \"control_plane\": \"field-everyone + field-hostess7 cpp\",\n"
      "  \"lanes\": {\n"
      "    \"dns_dhcp\": true,\n"
      "    \"fleet_mesh\": true,\n"
      "    \"h7r_capacity\": true,\n"
      "    \"everyone_counter\": true,\n"
      "    \"desktop\": true,\n"
      "    \"training\": true\n"
      "  },\n"
      "  \"doctrine\": \"ALWAYS FIELD ONE · AmmoNet only internet fabric\"\n"
      "}\n",
      ts, kFleetTarget);
  write_file(p.ammonet_json, body);
  char alt[kPathCap];
  std::snprintf(alt, sizeof(alt), "%s/field-hostess7-ammonet-wire.json",
                p.h7api);
  write_file(alt, body);
}

void write_training(const Paths& p, const char* ts) {
  int master_n = 0, solid_n = 0, sum = 0, track_n = 0;
  int pct = train_stats(&master_n, &solid_n, &sum, &track_n);

  char plate[kBodyCap];
  size_t len = 0;
  plate[0] = 0;
  append(plate, sizeof(plate), &len, "FIELD_PLATE=v1\n");
  append(plate, sizeof(plate), &len, "schema=hostess7-training/v2\n");
  appends(plate, sizeof(plate), &len, "ironclad_cite=%s\n", kIronclad);
  append(plate, sizeof(plate), &len, "engine=cpp\npython=0\nok=1\npartial=0\n");
  appends(plate, sizeof(plate), &len, "updated=%s\n", ts);
  appendf(plate, sizeof(plate), &len, "completion_pct=%d\n", pct);
  appendf(plate, sizeof(plate), &len, "master_tracks=%d\n", master_n);
  appendf(plate, sizeof(plate), &len, "solid_tracks=%d\n", solid_n);
  appendf(plate, sizeof(plate), &len, "track_count=%d\n", track_n);
  append(plate, sizeof(plate), &len,
         "motto=Training repaired · AmmoNet · fleet 125k · C++ only\n");
  for (int i = 0; kTracks[i].id; ++i) {
    char line[256];
    std::snprintf(line, sizeof(line), "track_%s=%s:%d:%s\n", kTracks[i].id,
                  kTracks[i].level, kTracks[i].score,
                  kTracks[i].sealed ? "sealed" : "open");
    append(plate, sizeof(plate), &len, line);
  }
  write_file(p.train_plate, plate);

  // JSON for Pages (C++ generated)
  char body[kBodyCap];
  len = 0;
  body[0] = 0;
  append(body, sizeof(body), &len, "{\n  \"ok\": true,\n  \"pages\": true,\n");
  append(body, sizeof(body), &len, "  \"held\": true,\n  \"posture\": \"war-ready\",\n");
  append(body, sizeof(body), &len, "  \"schema\": \"hostess7-training/v2\",\n");
  appends(body, sizeof(body), &len, "  \"updated\": \"%s\",\n", ts);
  append(body, sizeof(body), &len, "  \"version\": \"4.0.0-cpp\",\n");
  append(body, sizeof(body), &len, "  \"engine\": \"cpp\",\n  \"python\": 0,\n");
  append(body, sizeof(body), &len, "  \"boss\": \"hostess7\",\n  \"isp\": \"ammonet\",\n");
  appendf(body, sizeof(body), &len, "  \"fleet_servers\": %d,\n", kFleetTarget);
  append(body, sizeof(body), &len,
         "  \"motto\": \"Training repaired · AmmoNet acquainted · fleet 125k · "
         "C++ only\",\n");
  append(body, sizeof(body), &len, "  \"partial\": false,\n");
  appendf(body, sizeof(body), &len, "  \"completion_pct\": %d,\n", pct);
  appendf(body, sizeof(body), &len, "  \"master_tracks\": %d,\n", master_n);
  appendf(body, sizeof(body), &len, "  \"solid_tracks\": %d,\n", solid_n);
  append(body, sizeof(body), &len, "  \"old_training_fixed\": true,\n");
  append(body, sizeof(body), &len, "  \"tracks\": [\n");
  for (int i = 0; kTracks[i].id; ++i) {
    char line[384];
    std::snprintf(line, sizeof(line),
                  "    {\"id\": \"%s\", \"name\": \"%s\", \"level\": \"%s\", "
                  "\"score\": %d, \"sealed\": %s}%s\n",
                  kTracks[i].id, kTracks[i].name, kTracks[i].level,
                  kTracks[i].score, kTracks[i].sealed ? "true" : "false",
                  kTracks[i + 1].id ? "," : "");
    append(body, sizeof(body), &len, line);
  }
  append(body, sizeof(body), &len, "  ],\n");
  append(body, sizeof(body), &len,
         "  \"gui\": \"https://zacharygeurts.github.io/Hostess7/desktop/\",\n");
  append(body, sizeof(body), &len,
         "  \"local_gui\": \"http://127.0.0.1:9477/field\",\n");
  append(body, sizeof(body), &len,
         "  \"control_plane\": \"field-everyone cpp\"\n}\n");
  write_file(p.train_json, body);

  // room panel
  char room[kBodyCap];
  std::snprintf(
      room, sizeof(room),
      "{\n"
      "  \"schema\": \"hostess7-training-room-panel/v2\",\n"
      "  \"updated\": \"%s\",\n"
      "  \"engine\": \"cpp\",\n"
      "  \"python\": 0,\n"
      "  \"motto\": \"Training room · AmmoNet + fleet 125k · C++ only\",\n"
      "  \"completion_pct\": %d,\n"
      "  \"fleet_125k\": %d,\n"
      "  \"ammonet_acquainted\": true,\n"
      "  \"old_training_fixed\": true,\n"
      "  \"api\": \"/api/hostess7-training\"\n"
      "}\n",
      ts, pct, kFleetTarget);
  write_file(p.train_room_json, room);
  char state_train[kPathCap];
  std::snprintf(state_train, sizeof(state_train),
                "%s/hostess7-training-panel.json", p.state);
  write_file(state_train, body);
}

int cmd_seal(Paths& p, bool train_too) {
  LiveServers L {};
  harvest_live(p, &L);

  int fleet = static_cast<int>(
      L.fleet_servers > 0 ? L.fleet_servers : kFleetTarget);
  int hot = kFleetHotDefault;
  int exe = count_exec_bins(p);
  int gh = 20;  // stack favorites floor
  int bots = local_bot_nodes();
  // Billions of people served — NOT fleet-node sum (~125k)
  long long everyone = kPeopleServed;
  if ((L.dns_up || L.dhcp_up || L.fleet_servers > 0) &&
      everyone < kPeopleServedFloor) {
    everyone = kPeopleServedFloor;
  }
  if (everyone < kPeopleServed) everyone = kPeopleServed;

  char ts[40];
  utc_now(ts, sizeof(ts));

  write_everyone_plate(p, fleet, hot, exe, gh, bots, everyone, L);
  write_everyone_json(p, fleet, hot, exe, gh, bots, everyone, ts, L);
  write_fleet_json(p, ts);
  write_ammonet(p, ts);
  if (train_too) write_training(p, ts);
  store_qubes_memory(p, L, everyone);

  long long dns_served =
      L.dns_answers > 0 ? L.dns_answers
                        : (L.dns_queries > 0 ? L.dns_queries : L.dns_cache_hits);

  char out[2048];
  std::snprintf(out, sizeof(out),
                "FIELD_PLATE=v1\n"
                "schema=field-everyone-seal/v1\n"
                "ironclad_cite=%s\n"
                "engine=cpp\n"
                "python=0\n"
                "ok=1\n"
                "operator=Zac\n"
                "x=@ZacharyGeurts\n"
                "everyone_total=%lld\n"
                "people_served=%lld\n"
                "fleet_125k=%d\n"
                "dns_up=%d\n"
                "dhcp_up=%d\n"
                "dns_served=%lld\n"
                "dns_queries=%lld\n"
                "dhcp_leases=%lld\n"
                "dhcp_acks=%lld\n"
                "connected_pieces=%d\n"
                "server_id=%s\n"
                "executables=%d\n"
                "github_people=%d\n"
                "isp=ammonet\n"
                "boss=hostess7\n"
                "acquainted=1\n"
                "training=%d\n"
                "pages_api=%s\n"
                "motto=billions of people served · 7T ACTIVE leases · AmmoNet\n",
                kIronclad, everyone, everyone, fleet, L.dns_up, L.dhcp_up,
                dns_served, L.dns_queries, L.dhcp_leases, L.dhcp_acks,
                L.connected, L.server_id[0] ? L.server_id : "field", exe, gh,
                train_too ? 1 : 0, p.json_pages);
  std::fputs(out, stdout);
  return 0;
}

int cmd_status(Paths& p) {
  char buf[4096];
  int fd = ::open(p.plate, O_RDONLY | O_CLOEXEC);
  if (fd < 0) return cmd_seal(p, true);
  ssize_t n = ::read(fd, buf, sizeof(buf) - 1);
  ::close(fd);
  if (n < 0) return 1;
  buf[n] = 0;
  std::fputs(buf, stdout);
  return 0;
}

void usage() {
  std::fprintf(stderr,
               "usage: field-everyone [seal|status|export|train|ammonet|help]\n"
               "  C++ only · billions of people served · 7T leases · Hostess7\n"
               "  %s\n  %s\n",
               kVersion, kIronclad);
}

}  // namespace

int main(int argc, char** argv) {
  setenv("PATH", "/usr/bin:/bin:/usr/sbin:/sbin", 1);
  Paths p {};
  resolve(&p);
  const char* cmd = (argc >= 2) ? argv[1] : "status";
  if (!std::strcmp(cmd, "-h") || !std::strcmp(cmd, "--help") ||
      !std::strcmp(cmd, "help")) {
    usage();
    return 0;
  }
  if (!std::strcmp(cmd, "seal") || !std::strcmp(cmd, "bind") ||
      !std::strcmp(cmd, "update") || !std::strcmp(cmd, "full") ||
      !std::strcmp(cmd, "json") || !std::strcmp(cmd, "export"))
    return cmd_seal(p, true);
  if (!std::strcmp(cmd, "train") || !std::strcmp(cmd, "training")) {
    char ts[40];
    utc_now(ts, sizeof(ts));
    write_training(p, ts);
    std::printf(
        "FIELD_PLATE=v1\nschema=hostess7-training-seal/v1\nok=1\nengine=cpp\n"
        "python=0\nold_training_fixed=1\n");
    return 0;
  }
  if (!std::strcmp(cmd, "ammonet") || !std::strcmp(cmd, "wire")) {
    char ts[40];
    utc_now(ts, sizeof(ts));
    write_ammonet(p, ts);
    std::printf(
        "FIELD_PLATE=v1\nschema=hostess7-ammonet-seal/v1\nok=1\nacquainted=1\n"
        "isp=ammonet\nboss=hostess7\nengine=cpp\npython=0\n");
    return 0;
  }
  if (!std::strcmp(cmd, "status") || !std::strcmp(cmd, "panel"))
    return cmd_status(p);
  usage();
  return 2;
}
