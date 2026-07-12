// field-ammoos — AmmoOS classic desktop HTTP plane (C++ only)
//
// Full stack field panel on :9477 (optional :9478).
// Serves panel/ static assets + /field desktop + plate APIs.
// NO Python · NO shell · polkit HOSTILE elevation via field-elevate.
//
//   field-ammoos [start|stop|status|online|update|serve|help]
//
// ironclad:field-ammoos-cpp:1
#define _GNU_SOURCE 1

#include "field_ammoos.hpp"

#include <arpa/inet.h>
#include <cerrno>
#include <csignal>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <ctime>
#include <dirent.h>
#include <fcntl.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

namespace {

using field::ammoos::kBind;
using field::ammoos::kDesktopFile;
using field::ammoos::kFieldFile;
using field::ammoos::kIronclad;
using field::ammoos::kMotto;
using field::ammoos::kPagesAmmo;
using field::ammoos::kPagesHostess;
using field::ammoos::kPagesOs;
using field::ammoos::kPort;
using field::ammoos::kPortAlt;
using field::ammoos::kSchema;
using field::ammoos::kVersion;

constexpr size_t kPathCap = 1024;
constexpr size_t kReqCap = 8192;
constexpr size_t kBodyCap = 16384;
constexpr size_t kHdrCap = 1024;
constexpr size_t kFileCap = 8 * 1024 * 1024;  // 8 MiB per response

volatile sig_atomic_t g_run = 1;

void on_sig(int) { g_run = 0; }

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

bool path_is_reg(const char* p) {
  struct stat st {};
  return ::stat(p, &st) == 0 && S_ISREG(st.st_mode);
}

bool path_is_dir(const char* p) {
  struct stat st {};
  return ::stat(p, &st) == 0 && S_ISDIR(st.st_mode);
}

// Plate-safe status body
struct Paths {
  char root[kPathCap];
  char state[kPathCap];
  char panel[kPathCap];
  char docs[kPathCap];
  char pidfile[kPathCap];
  char plate[kPathCap];
  char forever[kPathCap];
  char bin[kPathCap];
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
  std::snprintf(p->panel, sizeof(p->panel), "%s/panel", p->root);
  // Prefer Hostess7 docs assets when panel missing file
  std::snprintf(p->docs, sizeof(p->docs), "%s/Hostess7/docs", p->root);
  std::snprintf(p->pidfile, sizeof(p->pidfile), "%s/field-ammoos.pid",
                p->state);
  std::snprintf(p->plate, sizeof(p->plate), "%s/field-ammoos.plate", p->state);
  std::snprintf(p->forever, sizeof(p->forever), "%s/field-ammoos.forever",
                p->state);
  std::snprintf(p->bin, sizeof(p->bin), "%s/bin", p->root);
}

const char* mime_of(const char* path) {
  const char* dot = std::strrchr(path, '.');
  if (!dot) return "application/octet-stream";
  if (!std::strcmp(dot, ".html") || !std::strcmp(dot, ".htm"))
    return "text/html; charset=utf-8";
  if (!std::strcmp(dot, ".css")) return "text/css; charset=utf-8";
  if (!std::strcmp(dot, ".js")) return "application/javascript; charset=utf-8";
  if (!std::strcmp(dot, ".json")) return "application/json; charset=utf-8";
  if (!std::strcmp(dot, ".plate")) return "text/plain; charset=utf-8";
  if (!std::strcmp(dot, ".png")) return "image/png";
  if (!std::strcmp(dot, ".jpg") || !std::strcmp(dot, ".jpeg"))
    return "image/jpeg";
  if (!std::strcmp(dot, ".svg")) return "image/svg+xml";
  if (!std::strcmp(dot, ".ico")) return "image/x-icon";
  if (!std::strcmp(dot, ".woff2")) return "font/woff2";
  if (!std::strcmp(dot, ".woff")) return "font/woff";
  if (!std::strcmp(dot, ".ttf")) return "font/ttf";
  if (!std::strcmp(dot, ".map")) return "application/json";
  if (!std::strcmp(dot, ".txt") || !std::strcmp(dot, ".md"))
    return "text/plain; charset=utf-8";
  if (!std::strcmp(dot, ".wasm")) return "application/wasm";
  return "application/octet-stream";
}

// Reject path traversal
bool safe_rel(const char* rel) {
  if (!rel || !rel[0]) return false;
  if (rel[0] == '/') return false;
  if (std::strstr(rel, "..")) return false;
  return true;
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

bool send_all(int fd, const char* buf, size_t n) {
  size_t off = 0;
  while (off < n) {
    ssize_t w = ::write(fd, buf + off, n - off);
    if (w < 0) {
      if (errno == EINTR) continue;
      return false;
    }
    off += static_cast<size_t>(w);
  }
  return true;
}

void send_resp(int fd, int code, const char* ctype, const char* body,
               size_t n) {
  char hdr[kHdrCap];
  const char* reason = (code == 200)   ? "OK"
                       : (code == 301) ? "Moved Permanently"
                       : (code == 302) ? "Found"
                       : (code == 404) ? "Not Found"
                       : (code == 403) ? "Forbidden"
                                       : "Error";
  int hlen = std::snprintf(
      hdr, sizeof(hdr),
      "HTTP/1.1 %d %s\r\n"
      "Server: field-ammoos/4.0.0-cpp\r\n"
      "Content-Type: %s\r\n"
      "Content-Length: %zu\r\n"
      "Access-Control-Allow-Origin: *\r\n"
      "Cache-Control: no-store\r\n"
      "X-Field-One: 1\r\n"
      "X-AmmoOS: cpp\r\n"
      "Connection: close\r\n"
      "\r\n",
      code, reason, ctype, n);
  if (hlen > 0) send_all(fd, hdr, static_cast<size_t>(hlen));
  if (body && n) send_all(fd, body, n);
}

void send_redirect(int fd, const char* loc) {
  char hdr[kHdrCap];
  int hlen = std::snprintf(
      hdr, sizeof(hdr),
      "HTTP/1.1 302 Found\r\n"
      "Server: field-ammoos/4.0.0-cpp\r\n"
      "Location: %s\r\n"
      "Content-Length: 0\r\n"
      "Access-Control-Allow-Origin: *\r\n"
      "Connection: close\r\n"
      "\r\n",
      loc);
  if (hlen > 0) send_all(fd, hdr, static_cast<size_t>(hlen));
}

void send_file(int fd, const char* path) {
  struct stat st {};
  if (::stat(path, &st) != 0 || !S_ISREG(st.st_mode)) {
    const char* b = "not found\n";
    send_resp(fd, 404, "text/plain; charset=utf-8", b, std::strlen(b));
    return;
  }
  if (st.st_size < 0 || static_cast<size_t>(st.st_size) > kFileCap) {
    const char* b = "too large\n";
    send_resp(fd, 403, "text/plain; charset=utf-8", b, std::strlen(b));
    return;
  }
  size_t n = static_cast<size_t>(st.st_size);
  char* buf = static_cast<char*>(std::malloc(n + 1));
  if (!buf) {
    const char* b = "oom\n";
    send_resp(fd, 500, "text/plain; charset=utf-8", b, std::strlen(b));
    return;
  }
  size_t got = 0;
  if (!read_file_cap(path, buf, n + 1, &got)) {
    std::free(buf);
    const char* b = "read error\n";
    send_resp(fd, 500, "text/plain; charset=utf-8", b, std::strlen(b));
    return;
  }
  send_resp(fd, 200, mime_of(path), buf, got);
  std::free(buf);
}

// Map URL path → filesystem under panel (or docs fallback)
bool resolve_url(const Paths& p, const char* url_path, char* out, size_t n) {
  // strip query
  char clean[kPathCap];
  std::snprintf(clean, sizeof(clean), "%s", url_path);
  char* q = std::strchr(clean, '?');
  if (q) *q = 0;
  // normalize
  if (!std::strcmp(clean, "/") || !clean[0]) {
    std::snprintf(out, n, "%s/%s", p.panel, kDesktopFile);
    return path_is_reg(out);
  }
  // AmmoOS OS routes
  if (!std::strcmp(clean, "/field") || !std::strcmp(clean, "/field/") ||
      !std::strcmp(clean, "/desktop") || !std::strcmp(clean, "/desktop/") ||
      !std::strcmp(clean, "/os") || !std::strcmp(clean, "/os/") ||
      !std::strcmp(clean, "/ammoos") || !std::strcmp(clean, "/ammoos/")) {
    std::snprintf(out, n, "%s/%s", p.panel, kDesktopFile);
    return path_is_reg(out);
  }
  if (!std::strcmp(clean, "/home") || !std::strcmp(clean, "/home/")) {
    std::snprintf(out, n, "%s/control-panel.html", p.panel);
    if (path_is_reg(out)) return true;
    std::snprintf(out, n, "%s/%s", p.panel, kDesktopFile);
    return path_is_reg(out);
  }
  // strip leading slash
  const char* rel = clean;
  if (rel[0] == '/') ++rel;
  if (!safe_rel(rel)) return false;

  // try panel first
  std::snprintf(out, n, "%s/%s", p.panel, rel);
  if (path_is_reg(out)) return true;
  if (path_is_dir(out)) {
    char idx[kPathCap];
    std::snprintf(idx, sizeof(idx), "%s/index.html", out);
    if (path_is_reg(idx)) {
      std::snprintf(out, n, "%s", idx);
      return true;
    }
  }
  // bare name → .html
  if (!std::strchr(rel, '.')) {
    std::snprintf(out, n, "%s/%s.html", p.panel, rel);
    if (path_is_reg(out)) return true;
  }
  // Hostess7/docs fallback (Pages-synced OS assets)
  std::snprintf(out, n, "%s/%s", p.docs, rel);
  if (path_is_reg(out)) return true;
  return false;
}

void plate_status_body(const Paths& p, char* body, size_t cap, int listening,
                       int port) {
  char ts[40];
  utc_now(ts, sizeof(ts));
  std::snprintf(
      body, cap,
      "FIELD_PLATE=v1\n"
      "schema=%s\n"
      "ironclad_cite=%s\n"
      "engine=cpp\n"
      "python=0\n"
      "scripts=0\n"
      "shell=0\n"
      "json=0\n"
      "field_one=1\n"
      "updated=%s\n"
      "version=%s\n"
      "ok=%d\n"
      "online=%d\n"
      "listening=%d\n"
      "bind=%s\n"
      "port=%d\n"
      "panel_root=%s\n"
      "desktop=/field\n"
      "desktop_file=%s\n"
      "url=http://%s:%d/field\n"
      "pages_os=%s\n"
      "pages_ammoos=%s\n"
      "pages_hostess7=%s\n"
      "motto=%s\n"
      "stack=hardware,nexus_c2,ironclad,kilroy,dns_dhcp,ammoos,queen,hostess7\n"
      "full_stack=1\n",
      kSchema, kIronclad, ts, kVersion, listening ? 1 : 0, listening ? 1 : 0,
      listening ? 1 : 0, kBind, port, p.panel, kDesktopFile, kBind, port,
      kPagesOs, kPagesAmmo, kPagesHostess, kMotto);
}

void write_online_plate(const Paths& p, int listening, int port, pid_t pid) {
  char body[kBodyCap];
  plate_status_body(p, body, sizeof(body), listening, port);
  char extra[256];
  std::snprintf(extra, sizeof(extra), "pid=%d\ncommander=AmmoOS\npackage=NewLatest_full\n",
                static_cast<int>(pid));
  // append pid line
  size_t L = std::strlen(body);
  if (L + std::strlen(extra) + 1 < sizeof(body))
    std::memcpy(body + L, extra, std::strlen(extra) + 1);
  write_file(p.plate, body);
  write_file("/dev/shm/field-ammoos.plate", body);
  write_file(p.forever,
             "mode=field_ammoos\n"
             "field_one=1\n"
             "engine=cpp\n"
             "python=0\n"
             "scripts=0\n"
             "port=9477\n"
             "desktop=/field\n"
             "full_stack=1\n"
             "pages=https://zacharygeurts.github.io/Hostess7/desktop/\n");
}

void api_status_plate(int fd, const Paths& p, int port) {
  char body[kBodyCap];
  plate_status_body(p, body, sizeof(body), 1, port);
  send_resp(fd, 200, "text/plain; charset=utf-8", body, std::strlen(body));
}

void api_stack(int fd) {
  char body[kBodyCap];
  char ts[40];
  utc_now(ts, sizeof(ts));
  std::snprintf(
      body, sizeof(body),
      "FIELD_PLATE=v1\n"
      "schema=field-ammoos-stack/v1\n"
      "ironclad_cite=%s\n"
      "updated=%s\n"
      "layer_0=hardware\n"
      "layer_1=nexus_c2\n"
      "layer_2=ironclad\n"
      "layer_3=kilroy_ipxe\n"
      "layer_4=dns_dhcp_mesh\n"
      "layer_5=ammoos_desktop\n"
      "layer_6=queen_browser\n"
      "layer_7=hostess7_multibrain\n"
      "field_one=1\n"
      "full_stack=1\n"
      "ok=1\n",
      kIronclad, ts);
  send_resp(fd, 200, "text/plain; charset=utf-8", body, std::strlen(body));
}

void handle_client(int cfd, const Paths& p, int port) {
  char req[kReqCap];
  ssize_t n = ::recv(cfd, req, sizeof(req) - 1, 0);
  if (n <= 0) {
    ::close(cfd);
    return;
  }
  req[n] = 0;
  char method[16] = {}, path[kPathCap] = {};
  if (std::sscanf(req, "%15s %1023s", method, path) != 2) {
    const char* b = "bad request\n";
    send_resp(cfd, 400, "text/plain; charset=utf-8", b, std::strlen(b));
    ::close(cfd);
    return;
  }
  if (std::strcmp(method, "GET") && std::strcmp(method, "HEAD") &&
      std::strcmp(method, "OPTIONS")) {
    const char* b = "method not allowed\n";
    send_resp(cfd, 405, "text/plain; charset=utf-8", b, std::strlen(b));
    ::close(cfd);
    return;
  }
  if (!std::strcmp(method, "OPTIONS")) {
    send_resp(cfd, 204, "text/plain", "", 0);
    ::close(cfd);
    return;
  }

  // API routes (plates, not JSON control)
  if (!std::strncmp(path, "/api/status", 11) ||
      !std::strcmp(path, "/api/ammoos") ||
      !std::strcmp(path, "/api/field-ammoos")) {
    api_status_plate(cfd, p, port);
    ::close(cfd);
    return;
  }
  if (!std::strcmp(path, "/api/stack") ||
      !std::strcmp(path, "/api/field-stack")) {
    api_stack(cfd);
    ::close(cfd);
    return;
  }
  // live plate files
  if (!std::strcmp(path, "/api/hostess7") ||
      !std::strcmp(path, "/api/hostess7-status")) {
    char pp[kPathCap];
    std::snprintf(pp, sizeof(pp), "%s/hostess7-online.plate", p.state);
    if (!path_is_reg(pp))
      std::snprintf(pp, sizeof(pp), "%s/hostess7-field-package.plate", p.state);
    if (path_is_reg(pp))
      send_file(cfd, pp);
    else {
      const char* b = "hostess7 plate missing — run field-hostess7 online\n";
      send_resp(cfd, 404, "text/plain; charset=utf-8", b, std::strlen(b));
    }
    ::close(cfd);
    return;
  }

  char fpath[kPathCap];
  if (!resolve_url(p, path, fpath, sizeof(fpath))) {
    const char* b =
        "AmmoOS · not found\n"
        "try /field · /desktop · /api/status · /api/stack\n";
    send_resp(cfd, 404, "text/plain; charset=utf-8", b, std::strlen(b));
    ::close(cfd);
    return;
  }
  if (!std::strcmp(method, "HEAD")) {
    struct stat st {};
    if (::stat(fpath, &st) == 0) {
      char hdr[kHdrCap];
      int hlen = std::snprintf(
          hdr, sizeof(hdr),
          "HTTP/1.1 200 OK\r\nContent-Type: %s\r\nContent-Length: %lld\r\n"
          "Access-Control-Allow-Origin: *\r\nConnection: close\r\n\r\n",
          mime_of(fpath), static_cast<long long>(st.st_size));
      if (hlen > 0) send_all(cfd, hdr, static_cast<size_t>(hlen));
    }
  } else {
    send_file(cfd, fpath);
  }
  ::close(cfd);
}

int open_listen(int port) {
  int s = ::socket(AF_INET, SOCK_STREAM | SOCK_CLOEXEC, 0);
  if (s < 0) return -1;
  int on = 1;
  ::setsockopt(s, SOL_SOCKET, SO_REUSEADDR, &on, sizeof(on));
  sockaddr_in addr {};
  addr.sin_family = AF_INET;
  addr.sin_port = htons(static_cast<uint16_t>(port));
  ::inet_pton(AF_INET, kBind, &addr.sin_addr);
  if (::bind(s, reinterpret_cast<sockaddr*>(&addr), sizeof(addr)) < 0) {
    ::close(s);
    return -1;
  }
  if (::listen(s, 64) < 0) {
    ::close(s);
    return -1;
  }
  return s;
}

int serve_loop(Paths& p, int port) {
  if (!path_is_dir(p.panel)) {
    std::fprintf(stderr, "field-ammoos: missing panel root %s\n", p.panel);
    return 2;
  }
  int s = open_listen(port);
  if (s < 0) {
    std::fprintf(stderr, "field-ammoos: bind %s:%d failed: %s\n", kBind, port,
                 std::strerror(errno));
    return 1;
  }
  write_online_plate(p, 1, port, ::getpid());
  {
    char pb[32];
    std::snprintf(pb, sizeof(pb), "%d\n", static_cast<int>(::getpid()));
    write_file(p.pidfile, pb);
  }
  std::fprintf(stderr,
               "field-ammoos online http://%s:%d/field  panel=%s  %s\n", kBind,
               port, p.panel, kIronclad);

  while (g_run) {
    fd_set rfds;
    FD_ZERO(&rfds);
    FD_SET(s, &rfds);
    timeval tv {1, 0};
    int r = ::select(s + 1, &rfds, nullptr, nullptr, &tv);
    if (r < 0) {
      if (errno == EINTR) continue;
      break;
    }
    if (r == 0) continue;
    int cfd = ::accept4(s, nullptr, nullptr, SOCK_CLOEXEC);
    if (cfd < 0) continue;
    handle_client(cfd, p, port);
  }
  ::close(s);
  ::unlink(p.pidfile);
  write_online_plate(p, 0, port, 0);
  return 0;
}

int read_pid(const Paths& p) {
  char buf[64];
  size_t n = 0;
  if (!read_file_cap(p.pidfile, buf, sizeof(buf), &n)) return -1;
  return std::atoi(buf);
}

bool pid_alive(int pid) {
  if (pid <= 0) return false;
  return ::kill(pid, 0) == 0;
}

int cmd_status(Paths& p) {
  int pid = read_pid(p);
  bool up = pid_alive(pid);
  // also probe bind
  int s = open_listen(kPort);
  bool port_free = (s >= 0);
  if (s >= 0) ::close(s);
  bool listening = up || !port_free;
  char body[kBodyCap];
  plate_status_body(p, body, sizeof(body), listening ? 1 : 0, kPort);
  char extra[128];
  std::snprintf(extra, sizeof(extra), "pid=%d\npid_alive=%d\n", pid, up ? 1 : 0);
  size_t L = std::strlen(body);
  if (L + std::strlen(extra) + 1 < sizeof(body))
    std::memcpy(body + L, extra, std::strlen(extra) + 1);
  std::fputs(body, stdout);
  write_file(p.plate, body);
  return listening ? 0 : 1;
}

int cmd_stop(Paths& p) {
  int pid = read_pid(p);
  if (pid_alive(pid)) {
    ::kill(pid, SIGTERM);
    for (int i = 0; i < 30; ++i) {
      if (!pid_alive(pid)) break;
      ::usleep(100000);
    }
    if (pid_alive(pid)) ::kill(pid, SIGKILL);
  }
  ::unlink(p.pidfile);
  write_online_plate(p, 0, kPort, 0);
  std::printf(
      "FIELD_PLATE=v1\nschema=field-ammoos-stop/v1\nok=1\nstopped=1\n");
  return 0;
}

int run_named(const Paths& p, const char* name, const char* a1, int tsec) {
  char path[kPathCap];
  std::snprintf(path, sizeof(path), "%s/%s", p.bin, name);
  if (::access(path, X_OK) != 0) return 127;
  pid_t pid = ::fork();
  if (pid < 0) return 126;
  if (pid == 0) {
    int dn = ::open("/dev/null", O_WRONLY | O_CLOEXEC);
    if (dn >= 0) {
      ::dup2(dn, 1);
      ::dup2(dn, 2);
      if (dn > 2) ::close(dn);
    }
    if (a1 && a1[0]) {
      char* const argv[] = {path, const_cast<char*>(a1), nullptr};
      ::execv(path, argv);
    } else {
      char* const argv[] = {path, nullptr};
      ::execv(path, argv);
    }
    ::_exit(127);
  }
  int st = 0;
  for (int i = 0; i < tsec * 10; ++i) {
    if (::waitpid(pid, &st, WNOHANG) == pid) {
      if (WIFEXITED(st)) return WEXITSTATUS(st);
      return 1;
    }
    ::usleep(100000);
  }
  ::kill(pid, SIGKILL);
  ::waitpid(pid, &st, 0);
  return 124;
}

int cmd_update(Paths& p) {
  // refresh stack siblings used by desktop
  run_named(p, "field-elevate", "autoelevate", 30);
  run_named(p, "field-hostess7-stack-update", "pulse", 60);
  run_named(p, "field-hostess7", "brain", 20);
  run_named(p, "field-fleet-mesh", "status", 12);
  run_named(p, "field-world-dns", "status", 10);
  run_named(p, "field-world-dhcp", "status", 10);
  char body[kBodyCap];
  char ts[40];
  utc_now(ts, sizeof(ts));
  std::snprintf(body, sizeof(body),
                "FIELD_PLATE=v1\n"
                "schema=field-ammoos-update/v1\n"
                "ironclad_cite=%s\n"
                "updated=%s\n"
                "ok=1\n"
                "desktop=/field\n"
                "pages_os=%s\n"
                "motto=AmmoOS stack refreshed · full field plane\n",
                kIronclad, ts, kPagesOs);
  write_file(p.plate, body);
  std::fputs(body, stdout);
  return 0;
}

int cmd_start(Paths& p, bool foreground) {
  // already up?
  int old = read_pid(p);
  if (pid_alive(old)) {
    std::printf(
        "FIELD_PLATE=v1\nschema=field-ammoos-start/v1\nok=1\nalready=1\n"
        "pid=%d\nurl=http://%s:%d/field\n",
        old, kBind, kPort);
    return 0;
  }
  // free stale port holders if our pidfile dead
  if (foreground) {
    std::signal(SIGINT, on_sig);
    std::signal(SIGTERM, on_sig);
    std::signal(SIGPIPE, SIG_IGN);
    return serve_loop(p, kPort);
  }
  // daemonize
  pid_t pid = ::fork();
  if (pid < 0) return 126;
  if (pid > 0) {
    // parent wait briefly for bind
    for (int i = 0; i < 30; ++i) {
      ::usleep(100000);
      if (pid_alive(static_cast<int>(pid))) {
        int s = open_listen(kPort);
        if (s < 0) {
          // port taken = server up
          std::printf(
              "FIELD_PLATE=v1\nschema=field-ammoos-start/v1\nok=1\n"
              "online=1\npid=%d\nurl=http://%s:%d/field\n"
              "pages_os=%s\nengine=cpp\nfull_stack=1\n",
              static_cast<int>(pid), kBind, kPort, kPagesOs);
          write_online_plate(p, 1, kPort, pid);
          return 0;
        }
        ::close(s);
      }
    }
    std::printf(
        "FIELD_PLATE=v1\nschema=field-ammoos-start/v1\nok=0\n"
        "pid=%d\nerr=bind_timeout\n",
        static_cast<int>(pid));
    return 1;
  }
  // child
  ::setsid();
  int dn = ::open("/dev/null", O_RDWR | O_CLOEXEC);
  if (dn >= 0) {
    ::dup2(dn, 0);
    // keep stderr for first bind log? silence for daemon
    ::dup2(dn, 1);
    if (dn > 2) ::close(dn);
  }
  std::signal(SIGINT, on_sig);
  std::signal(SIGTERM, on_sig);
  std::signal(SIGPIPE, SIG_IGN);
  // ignore soft-kill storm on field plane
  std::signal(SIGUSR1, on_sig);
  int rc = serve_loop(p, kPort);
  ::_exit(rc);
}

int cmd_online(Paths& p) {
  cmd_update(p);
  int rc = cmd_start(p, false);
  // ensure hostess7 plate present
  run_named(p, "field-hostess7", "status", 15);
  cmd_status(p);
  return rc;
}

void usage() {
  std::fprintf(stderr,
               "usage: field-ammoos [start|stop|status|online|update|serve|"
               "help]\n"
               "  AmmoOS classic desktop on http://%s:%d/field\n"
               "  Pages OS: %s\n"
               "  %s\n  %s\n",
               kBind, kPort, kPagesOs, kVersion, kIronclad);
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
  if (!std::strcmp(cmd, "start") || !std::strcmp(cmd, "up"))
    return cmd_start(p, false);
  if (!std::strcmp(cmd, "serve") || !std::strcmp(cmd, "fg") ||
      !std::strcmp(cmd, "foreground"))
    return cmd_start(p, true);
  if (!std::strcmp(cmd, "stop") || !std::strcmp(cmd, "down"))
    return cmd_stop(p);
  if (!std::strcmp(cmd, "status") || !std::strcmp(cmd, "panel"))
    return cmd_status(p);
  if (!std::strcmp(cmd, "online") || !std::strcmp(cmd, "boot") ||
      !std::strcmp(cmd, "on"))
    return cmd_online(p);
  if (!std::strcmp(cmd, "update") || !std::strcmp(cmd, "refresh"))
    return cmd_update(p);
  usage();
  return 2;
}
