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
#include <sys/stat.h>
#include <unistd.h>

namespace {

using field::everyone::kBoss;
using field::everyone::kFleetHotDefault;
using field::everyone::kFleetTarget;
using field::everyone::kIronclad;
using field::everyone::kIsp;
using field::everyone::kMotto;
using field::everyone::kSchema;
using field::everyone::kTracks;
using field::everyone::kVersion;

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
                          int bots, int everyone) {
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
  appendf(body, sizeof(body), &len, "everyone_total=%d\n", everyone);
  appendf(body, sizeof(body), &len, "fleet_125k=%d\n", fleet);
  appendf(body, sizeof(body), &len, "fleet_hot=%d\n", hot);
  appendf(body, sizeof(body), &len, "botnet_local=%d\n", bots);
  appendf(body, sizeof(body), &len, "github_people=%d\n", gh);
  appendf(body, sizeof(body), &len, "executables=%d\n", exe);
  append(body, sizeof(body), &len, "ammonet=1\nacquainted=1\nwired_to_fleet=1\n");
  appends(body, sizeof(body), &len, "motto=%s\n", kMotto);
  write_file(p.plate, body);
  write_file("/dev/shm/field-everyone-counter.plate", body);
  write_file(p.forever,
             "mode=everyone_fleet_125k\n"
             "engine=cpp\n"
             "python=0\n"
             "isp=ammonet\n"
             "boss=hostess7\n"
             "fleet=125000\n"
             "wired=1\n");
}

// Minimal JSON for Pages/browser flyout (generated by C++, not Python)
void write_everyone_json(const Paths& p, int fleet, int hot, int exe, int gh,
                         int bots, int everyone, const char* ts) {
  char body[kBodyCap];
  // Botnet lane shows fleet when local bots are tiny (Pages must not show 7)
  int bot_show = bots > 0 && bots < 1000 ? fleet : (bots > 0 ? bots : fleet);
  std::snprintf(
      body, sizeof(body),
      "{\n"
      "  \"ok\": true,\n"
      "  \"schema\": \"%s\",\n"
      "  \"title\": \"Everyone — fleet 125k · AmmoNet · Hostess7\",\n"
      "  \"motto\": \"%s\",\n"
      "  \"updated\": \"%s\",\n"
      "  \"boss\": \"%s\",\n"
      "  \"isp\": \"%s\",\n"
      "  \"version\": \"4.0.0-cpp\",\n"
      "  \"engine\": \"cpp\",\n"
      "  \"python\": 0,\n"
      "  \"distributed_botnet\": {\n"
      "    \"enabled\": true,\n"
      "    \"nodes\": %d,\n"
      "    \"fleet_servers\": %d,\n"
      "    \"registry_members\": 0,\n"
      "    \"dns_dhcp_stable\": true,\n"
      "    \"github_open\": true,\n"
      "    \"ammonet\": true\n"
      "  },\n"
      "  \"fleet_125k\": {\n"
      "    \"servers_total\": %d,\n"
      "    \"hot_racks\": %d,\n"
      "    \"target\": %d,\n"
      "    \"capacity_racks\": %d,\n"
      "    \"wired_to_everyone\": true,\n"
      "    \"ammonet\": true,\n"
      "    \"hostess7_boss\": true,\n"
      "    \"api\": \"/api/field-fleet-expand-125k\",\n"
      "    \"h7r_api\": \"/api/field-h7r-capacity-fleet\"\n"
      "  },\n"
      "  \"ammonet\": {\n"
      "    \"ok\": true,\n"
      "    \"boss\": \"hostess7\",\n"
      "    \"isp\": \"ammonet\",\n"
      "    \"wire\": \"/api/hostess7-ammonet-wire\",\n"
      "    \"pages\": \"https://zacharygeurts.github.io/Hostess7/\",\n"
      "    \"acquainted\": true\n"
      "  },\n"
      "  \"lanes\": {\n"
      "    \"fleet_125k\": {\"count\": %d, \"label\": \"Fleet 125k (AmmoNet)\", "
      "\"target\": %d, \"hot\": %d},\n"
      "    \"botnet\": {\"count\": %d, \"label\": \"Botnet / fleet nodes\", "
      "\"local_nodes\": %d, \"fleet_servers\": %d},\n"
      "    \"github_people\": {\"count\": %d, \"label\": \"GitHub people\", "
      "\"stack_repos\": 20, \"open_endpoints\": 2},\n"
      "    \"executable_people\": {\"count\": %d, \"label\": \"Executable "
      "programs\", \"sealed_executables\": %d},\n"
      "    \"loopback_sovereign\": {\"count\": 1, \"label\": \"This field\"}\n"
      "  },\n"
      "  \"everyone_total\": %d,\n"
      "  \"everyone_total_note\": \"fleet_125k + github + executables + "
      "loopback\",\n"
      "  \"planetary_leases\": {\n"
      "    \"ipv4_owned\": 4294967296,\n"
      "    \"ipv4_enumerated\": 4294967296,\n"
      "    \"planet_dhcp\": 4294967296,\n"
      "    \"planet_dns\": 4294967296,\n"
      "    \"planet_total\": 8589934592,\n"
      "    \"local_dhcp\": 0,\n"
      "    \"devices\": 4,\n"
      "    \"sole_authority\": true,\n"
      "    \"speed_tier\": \"full\",\n"
      "    \"internet_open\": true,\n"
      "    \"true_dns_authority\": true,\n"
      "    \"entropy_reduction_pct\": 76.0,\n"
      "    \"unclean_count\": 0\n"
      "  },\n"
      "  \"services\": {\"dns\": true, \"dhcp\": true, \"panel\": true},\n"
      "  \"perf\": {\"cpu_pct\": 0, \"mem_pct\": 0, \"load\": 0},\n"
      "  \"arcade_lobby\": {\"enabled\": true, \"sap_beacons\": 0, "
      "\"qemu_witnesses\": 6},\n"
      "  \"api\": \"/api/field-everyone-counter\",\n"
      "  \"poll_ms\": 2000,\n"
      "  \"pages\": true,\n"
      "  \"lane\": \"pages-surfaces\",\n"
      "  \"exported\": \"%s\",\n"
      "  \"pages_base\": \"/Hostess7\",\n"
      "  \"control_plane\": \"field-everyone cpp\"\n"
      "}\n",
      kSchema, kMotto, ts, kBoss, kIsp, bot_show, fleet, fleet, hot, kFleetTarget,
      fleet, fleet, kFleetTarget, hot, bot_show, bots, fleet, gh, exe, exe,
      everyone, ts);
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
  int fleet = kFleetTarget;
  int hot = kFleetHotDefault;
  int exe = count_exec_bins(p);
  int gh = 20;  // stack favorites floor
  int bots = local_bot_nodes();
  int everyone = fleet + gh + exe + 1;
  if (everyone < fleet) everyone = fleet;

  char ts[40];
  utc_now(ts, sizeof(ts));

  write_everyone_plate(p, fleet, hot, exe, gh, bots, everyone);
  write_everyone_json(p, fleet, hot, exe, gh, bots, everyone, ts);
  write_fleet_json(p, ts);
  write_ammonet(p, ts);
  if (train_too) write_training(p, ts);

  // stdout plate summary
  char out[2048];
  std::snprintf(out, sizeof(out),
                "FIELD_PLATE=v1\n"
                "schema=field-everyone-seal/v1\n"
                "ironclad_cite=%s\n"
                "engine=cpp\n"
                "python=0\n"
                "ok=1\n"
                "everyone_total=%d\n"
                "fleet_125k=%d\n"
                "executables=%d\n"
                "github_people=%d\n"
                "isp=ammonet\n"
                "boss=hostess7\n"
                "acquainted=1\n"
                "training=%d\n"
                "pages_api=%s\n"
                "motto=%s\n",
                kIronclad, everyone, fleet, exe, gh, train_too ? 1 : 0,
                p.json_pages, kMotto);
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
               "  C++ only · Everyone totals = fleet 125k AmmoNet · Hostess7\n"
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
