// field-x-producer-static — bake Producer HTML from feed JSON · NO scripts in output
// C++ only. Public static surface for Hostess7/docs/x-producer/
//
//   field-x-producer-static [bake|status|seal]
//
// ironclad:field-x-producer-static:1
#define _GNU_SOURCE 1

#include <cerrno>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <ctime>
#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>

namespace {

constexpr const char* kIronclad = "ironclad:field-x-producer-static:1";
constexpr const char* kSchema = "field-x-producer-static/v1";
constexpr const char* kVersion =
    "Field-X-Producer-Static 1.0.0-cpp (HTML/CSS only · no scripts · public)";
constexpr size_t kPathCap = 768;
constexpr size_t kReadCap = 2 * 1024 * 1024;
constexpr size_t kOutCap = 4 * 1024 * 1024;

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

bool write_file(const char* path, const char* body, size_t n) {
  char tmp[kPathCap];
  std::snprintf(tmp, sizeof(tmp), "%s.%d.tmp", path, static_cast<int>(::getpid()));
  int fd = ::open(tmp, O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC, 0644);
  if (fd < 0) return false;
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
  return ::rename(tmp, path) == 0;
}

bool read_all(const char* path, char* out, size_t cap, size_t* got) {
  int fd = ::open(path, O_RDONLY | O_CLOEXEC);
  if (fd < 0) return false;
  size_t n = 0;
  for (;;) {
    if (n + 1 >= cap) break;
    ssize_t r = ::read(fd, out + n, cap - 1 - n);
    if (r < 0) {
      if (errno == EINTR) continue;
      ::close(fd);
      return false;
    }
    if (r == 0) break;
    n += static_cast<size_t>(r);
  }
  ::close(fd);
  out[n] = 0;
  if (got) *got = n;
  return n > 0;
}

void html_escape(const char* in, char* out, size_t cap) {
  size_t o = 0;
  if (!in) {
    if (cap) out[0] = 0;
    return;
  }
  for (size_t i = 0; in[i] && o + 8 < cap; ++i) {
    char c = in[i];
    if (c == '&') {
      std::memcpy(out + o, "&amp;", 5);
      o += 5;
    } else if (c == '<') {
      std::memcpy(out + o, "&lt;", 4);
      o += 4;
    } else if (c == '>') {
      std::memcpy(out + o, "&gt;", 4);
      o += 4;
    } else if (c == '"') {
      std::memcpy(out + o, "&quot;", 6);
      o += 6;
    } else {
      out[o++] = c;
    }
  }
  out[o] = 0;
}

// Minimal JSON string extract after "key":
bool json_string_after(const char* body, const char* key, char* out, size_t cap) {
  char pat[96];
  std::snprintf(pat, sizeof(pat), "\"%s\"", key);
  const char* p = std::strstr(body, pat);
  if (!p) return false;
  p = std::strchr(p + std::strlen(pat), ':');
  if (!p) return false;
  ++p;
  while (*p == ' ' || *p == '\t' || *p == '\n' || *p == '\r') ++p;
  if (*p != '"') return false;
  ++p;
  size_t o = 0;
  while (*p && *p != '"' && o + 1 < cap) {
    if (*p == '\\' && p[1]) {
      ++p;
      out[o++] = *p++;
      continue;
    }
    out[o++] = *p++;
  }
  out[o] = 0;
  return o > 0 || (p && *p == '"');
}

struct Paths {
  char root[kPathCap];
  char state[kPathCap];
  char feed[kPathCap];
  char out_html[kPathCap];
  char out_index[kPathCap];
  char panel[kPathCap];
  char forever[kPathCap];
};

void resolve(Paths* p) {
  std::snprintf(p->root, sizeof(p->root), "%s",
                env_or("NEXUS_INSTALL_ROOT",
                       "/home/default/Desktop/SG/NewLatest"));
  std::snprintf(p->state, sizeof(p->state), "%s",
                env_or("NEXUS_STATE_DIR",
                       "/home/default/Desktop/SG/NewLatest/.nexus-state"));
  ensure_dir(p->state);
  std::snprintf(p->feed, sizeof(p->feed),
                "%s/Hostess7/docs/data/x-producer-feed.json", p->root);
  std::snprintf(p->out_html, sizeof(p->out_html),
                "%s/Hostess7/docs/x-producer/posts.inc.html", p->root);
  std::snprintf(p->out_index, sizeof(p->out_index),
                "%s/Hostess7/docs/x-producer/index.html", p->root);
  std::snprintf(p->panel, sizeof(p->panel),
                "%s/field-x-producer-static-panel.json", p->state);
  std::snprintf(p->forever, sizeof(p->forever),
                "%s/field-x-producer-static.forever", p->state);
}

// Secure page format: full static index.html · zero cost · no scripts
int cmd_bake(Paths& p) {
  static char feed[kReadCap];
  static char posts[kOutCap / 2];
  static char page[kOutCap];
  size_t flen = 0;
  if (!read_all(p.feed, feed, sizeof(feed), &flen)) {
    std::printf("{\"ok\":false,\"error\":\"no_feed\",\"path\":\"%s\","
                "\"ironclad\":\"%s\"}\n",
                p.feed, kIronclad);
    return 1;
  }

  size_t o = 0;
  auto append_posts = [&](const char* s) {
    size_t n = std::strlen(s);
    if (o + n + 1 >= sizeof(posts)) return;
    std::memcpy(posts + o, s, n);
    o += n;
    posts[o] = 0;
  };

  int nposts = 0;
  const char* cur = feed;
  while ((cur = std::strstr(cur, "\"id\"")) != nullptr && nposts < 40) {
    char id[64] = {}, text[2048] = {}, created[96] = {}, url[512] = {};
    json_string_after(cur, "id", id, sizeof(id));
    json_string_after(cur, "text", text, sizeof(text));
    json_string_after(cur, "created_at", created, sizeof(created));
    json_string_after(cur, "url", url, sizeof(url));
    if (!url[0] && !text[0]) {
      ++cur;
      continue;
    }
    char et[4096], ec[256], eu[1024];
    html_escape(text[0] ? text : "(media)", et, sizeof(et));
    html_escape(created, ec, sizeof(ec));
    html_escape(url, eu, sizeof(eu));
    char block[8192];
    std::snprintf(block, sizeof(block),
                  "<article class=\"post\">\n"
                  "  <div class=\"post-meta\">%s</div>\n"
                  "  <div class=\"post-text\">%s</div>\n"
                  "  <a href=\"%s\" rel=\"noopener\">Open on X →</a>\n"
                  "</article>\n",
                  ec[0] ? ec : id, et, eu[0] ? eu : "#");
    append_posts(block);
    ++nposts;
    cur += 4;
  }
  write_file(p.out_html, posts, o);

  char now[40];
  utc_now(now, sizeof(now));

  // Full secure page (single file · CSP · no scripts · zero-cost static)
  int n = std::snprintf(
      page, sizeof(page),
      "<!DOCTYPE html>\n"
      "<html lang=\"en\">\n"
      "<head>\n"
      "  <meta charset=\"utf-8\" />\n"
      "  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1, "
      "viewport-fit=cover\" />\n"
      "  <meta name=\"color-scheme\" content=\"dark\" />\n"
      "  <meta name=\"theme-color\" content=\"#050403\" />\n"
      "  <meta http-equiv=\"Content-Security-Policy\" content=\"default-src "
      "'self'; img-src 'self' data:; style-src 'self'; script-src 'none'; "
      "object-src 'none'; base-uri 'self'; form-action 'none'; "
      "frame-ancestors 'none'\" />\n"
      "  <meta http-equiv=\"X-Content-Type-Options\" content=\"nosniff\" />\n"
      "  <meta http-equiv=\"Referrer-Policy\" content=\"no-referrer\" />\n"
      "  <meta name=\"description\" content=\"X Producer — secure static "
      "public page. C++ baked. No scripts. Zero cost.\" />\n"
      "  <title>𝕏 Producer — Secure Static</title>\n"
      "  <link rel=\"stylesheet\" href=\"producer.css\" />\n"
      "  <link rel=\"icon\" href=\"assets/producer-logo.jpg\" />\n"
      "  <!-- field-x-producer-static · ironclad:field-x-producer-static:1 · "
      "no JS -->\n"
      "</head>\n"
      "<body>\n"
      "  <div class=\"x-stage\" aria-hidden=\"true\"></div>\n"
      "  <div class=\"app\">\n"
      "    <header class=\"top\" role=\"banner\">\n"
      "      <div class=\"top-inner\">\n"
      "        <div class=\"brand\">\n"
      "          <div class=\"x-emboss\" aria-label=\"X\"><span>𝕏</span></div>\n"
      "          <img class=\"producer-logo\" src=\"assets/producer-logo.jpg\" "
      "width=\"52\" height=\"52\" alt=\"Producer logo\" />\n"
      "          <div class=\"brand-text\">\n"
      "            <p class=\"brand-title\">Producer</p>\n"
      "            <p class=\"brand-sub\">secure static · C++ bake · zero "
      "cost · no scripts</p>\n"
      "          </div>\n"
      "        </div>\n"
      "        <span class=\"badge public\">Public</span>\n"
      "        <span class=\"badge\">Secure</span>\n"
      "        <div class=\"top-actions\">\n"
      "          <span class=\"live\">Baked %s · %d posts</span>\n"
      "          <a class=\"btn btn-ghost\" href=\"sources/\">Sources</a>\n"
      "          <a class=\"btn btn-light\" "
      "href=\"https://studio.x.com/producer/sources\" "
      "rel=\"noopener\">Open X Studio</a>\n"
      "        </div>\n"
      "      </div>\n"
      "    </header>\n"
      "    <main class=\"main\">\n"
      "      <div class=\"col-primary\">\n"
      "        <section class=\"card\">\n"
      "          <div class=\"hero-cover\"><div class=\"x-watermark\" "
      "aria-hidden=\"true\">𝕏</div></div>\n"
      "          <div class=\"hero-body\">\n"
      "            <div class=\"avatar-row\"><div class=\"avatar\">"
      "<img src=\"assets/producer-logo.jpg\" alt=\"\" /></div></div>\n"
      "            <h1>BIG GRIN</h1>\n"
      "            <p class=\"handle\">@ZacharyGeurts · Producer</p>\n"
      "            <div class=\"stats\">\n"
      "              <div><strong>6953</strong><span>posts truth</span></div>\n"
      "              <div><strong>%d</strong><span>baked</span></div>\n"
      "              <div><strong>0</strong><span>scripts</span></div>\n"
      "            </div>\n"
      "            <p class=\"bio\">Secure Producer page — embossed X, black "
      "&amp; brown, colorblind-safe, full-width. <strong>No JavaScript.</strong> "
      "Formatted and sealed by C++ <code style=\"color:var(--copper)\">"
      "field-x-producer-static</code>. Zero cost. Studio: "
      "<a href=\"https://studio.x.com/producer/sources\" "
      "style=\"color:var(--ok);font-weight:700\" rel=\"noopener\">"
      "studio.x.com/producer/sources</a>.</p>\n"
      "            <p class=\"verdict\">Secure static format · CSP script-src "
      "'none' · public Field surface · Angel Sealed plane</p>\n"
      "            <div class=\"cta\">\n"
      "              <a class=\"btn btn-primary\" href=\"sources/\">Sources</a>\n"
      "              <a class=\"btn btn-light\" "
      "href=\"https://x.com/ZacharyGeurts\" rel=\"noopener\">View on X</a>\n"
      "              <a class=\"btn btn-ghost\" "
      "href=\"https://studio.x.com/producer/sources\" "
      "rel=\"noopener\">X Studio</a>\n"
      "            </div>\n"
      "          </div>\n"
      "        </section>\n"
      "        <section class=\"card timeline\">\n"
      "          <div class=\"card-head\">Restored posts · secure bake "
      "(%d)</div>\n"
      "%s"
      "        </section>\n"
      "      </div>\n"
      "      <aside class=\"side\">\n"
      "        <div class=\"card\">\n"
      "          <h2>For Elon</h2>\n"
      "          <p class=\"lede\">Secure Producer: embossed X, custom logo, "
      "black+brown, bigger type, full-width, orientation CSS. "
      "<strong>Zero scripts · C++ sealed · zero cost.</strong></p>\n"
      "          <div class=\"shield\">CSP · nosniff · no-referrer · "
      "script-src none · ironclad:field-x-producer-static:1</div>\n"
      "        </div>\n"
      "      </aside>\n"
      "    </main>\n"
      "    <p class=\"elon-note\">Public secure static page · C++ bake · no "
      "userscript · Hostess7 /x-producer/</p>\n"
      "  </div>\n"
      "</body>\n"
      "</html>\n",
      now, nposts, nposts, nposts, posts);

  if (n <= 0 || (size_t)n >= sizeof(page)) {
    std::printf("{\"ok\":false,\"error\":\"page_too_large\",\"ironclad\":\"%s\"}\n",
                kIronclad);
    return 1;
  }
  if (!write_file(p.out_index, page, static_cast<size_t>(n))) {
    std::printf("{\"ok\":false,\"error\":\"write_index\",\"ironclad\":\"%s\"}\n",
                kIronclad);
    return 1;
  }

  char panel[1200];
  std::snprintf(panel, sizeof(panel),
                "{\n"
                "  \"ok\": true,\n"
                "  \"schema\": \"%s\",\n"
                "  \"updated\": \"%s\",\n"
                "  \"version\": \"%s\",\n"
                "  \"ironclad_cite\": \"%s\",\n"
                "  \"secure_page\": true,\n"
                "  \"csp\": \"script-src 'none'\",\n"
                "  \"scripts\": false,\n"
                "  \"javascript\": false,\n"
                "  \"zero_cost\": true,\n"
                "  \"engine\": \"cpp\",\n"
                "  \"posts_baked\": %d,\n"
                "  \"index\": \"%s\",\n"
                "  \"public\": true,\n"
                "  \"pages\": \"/x-producer/\"\n"
                "}\n",
                kSchema, now, kVersion, kIronclad, nposts, p.out_index);
  write_file(p.panel, panel, std::strlen(panel));
  char forever[320];
  std::snprintf(forever, sizeof(forever),
                "sealed %s\n"
                "secure_page=1\n"
                "csp=script-src-none\n"
                "scripts=0\n"
                "javascript=0\n"
                "zero_cost=1\n"
                "engine=cpp\n"
                "posts=%d\n"
                "ironclad=%s\n",
                now, nposts, kIronclad);
  write_file(p.forever, forever, std::strlen(forever));

  std::printf(
      "{\"ok\":true,\"cmd\":\"bake\",\"secure_page\":true,\"posts\":%d,"
      "\"index\":\"%s\",\"scripts\":false,\"javascript\":false,"
      "\"zero_cost\":true,\"csp\":\"script-src 'none'\","
      "\"engine\":\"cpp\",\"ironclad\":\"%s\"}\n",
      nposts, p.out_index, kIronclad);
  return 0;
}

int cmd_status(Paths& p) {
  int fd = ::open(p.panel, O_RDONLY | O_CLOEXEC);
  if (fd < 0) {
    std::printf("{\"ok\":false,\"pending\":\"bake\",\"scripts\":false,"
                "\"ironclad\":\"%s\"}\n",
                kIronclad);
    return 1;
  }
  char buf[2048];
  ssize_t n = ::read(fd, buf, sizeof(buf) - 1);
  ::close(fd);
  if (n < 0) n = 0;
  buf[n] = 0;
  std::fputs(buf, stdout);
  if (n == 0 || buf[n - 1] != '\n') std::fputc('\n', stdout);
  return 0;
}

int cmd_seal(Paths& p) {
  int rc = cmd_bake(p);
  // remove userscript from public surface if present
  char us[kPathCap];
  std::snprintf(us, sizeof(us), "%s/Hostess7/docs/x-producer/userscript.js",
                p.root);
  if (::access(us, F_OK) == 0) {
    char q[kPathCap];
    std::snprintf(q, sizeof(q), "%s/script-quarantine-terror", p.state);
    ensure_dir(q);
    char dst[kPathCap];
    std::snprintf(dst, sizeof(dst), "%s/x-producer-userscript.js", q);
    ::rename(us, dst);
  }
  return rc;
}

}  // namespace

int main(int argc, char** argv) {
  Paths p {};
  resolve(&p);
  const char* cmd = (argc > 1 && argv[1] && argv[1][0]) ? argv[1] : "status";
  if (std::strcmp(cmd, "bake") == 0) return cmd_bake(p);
  if (std::strcmp(cmd, "seal") == 0) return cmd_seal(p);
  if (std::strcmp(cmd, "status") == 0) return cmd_status(p);
  if (std::strcmp(cmd, "help") == 0 || std::strcmp(cmd, "-h") == 0) {
    std::printf(
        "{\"usage\":\"field-x-producer-static [bake|seal|status]\","
        "\"scripts\":false,\"javascript\":false,\"engine\":\"cpp\","
        "\"ironclad\":\"%s\"}\n",
        kIronclad);
    return 0;
  }
  return cmd_status(p);
}
