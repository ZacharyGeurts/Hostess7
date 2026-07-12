// field-dig — Grok16 Field-native DNS dig. From scratch. No ISC dig.
// Ironclad: ironclad:field-dig-cpp:3
//
//   field-dig [@server] name [type] [+short] [+json] [+time=N] [+tries=N] [-p N]
//   dig ...   (same binary; PATH scrub replaces ISC dig)
//
// Security model:
//   · Client resolv.conf stays Field Truth only (127.0.0.1) — dig never writes it.
//   · Default dig name → Field local mesh (isolated to our plane).
//   · dig @1.1.1.1 name → allowed as Field tool isolated egress (old dig compat).
//     We talk OUT from this binary's isolated space to fill/debug world DNS.
//     That is NOT installing foreign NS for the OS.
//
// Built with Grok16 g++16 field_opt: PIE, RELRO, NOW, noexecstack, no exceptions/rtti.
#define _GNU_SOURCE 1

#include <arpa/inet.h>
#include <cerrno>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <netinet/in.h>
#include <sys/select.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <unistd.h>

namespace {

// Dual cite: C++ dig seal + Ironclad BSP plate (it just works)
// Anti-freeze: Field mesh first when no @server; short per-try timeout
constexpr const char* kIronclad = "ironclad:field-dig-cpp:3";
constexpr const char* kIroncladBsp = "ironclad:field-bsp-dns:1";
constexpr const char* kVersion =
    "Field-DiG 3.0.0-g16 (old dig secure · isolated egress · no ISC dig)";
constexpr size_t kPktCap = 4096;
constexpr size_t kNameCap = 256;
constexpr size_t kAnsCap = 32;
constexpr size_t kSrvCap = 8;
constexpr int kDefaultTimeMs = 800;
constexpr int kDefaultPort = 53;  // classic dig default; Field mesh walks ports

// Known public recursive edges — NOT client defaults. Only for explicit @server
// or Field world-learn isolated egress from this tool.
static const char* kPublicHelpers[] = {
    "1.1.1.1", "1.0.0.1", "8.8.8.8", "8.8.4.4", "9.9.9.9",
    "208.67.222.222", "208.67.220.220", nullptr};

// Ironclad BSP multipoint — local mesh first when no @server
static const char* kFieldServers[] = {"127.0.0.1", "192.168.47.1", "192.168.50.1",
                                      "127.0.0.53", nullptr};
// Field mesh ports (prefer live :53, then high mesh)
static const int kFieldPorts[] = {53, 9053, 5353, 0};

struct Opts {
  char server[64];
  char name[kNameCap];
  char qtype[16];
  int port;
  int tries;
  int time_ms;
  bool short_out;
  bool json;
  bool answer_only;
  bool noall;
  bool stats;
  bool help;
  bool version;
  bool servers_cmd;
  bool user_server;   // explicit @server
  bool user_port;     // explicit -p
  bool isolated_out;  // talking out of Field plane to a public helper
};

struct Answer {
  char name[kNameCap];
  char type[12];
  char data[kNameCap];
  uint32_t ttl;
};

struct Result {
  bool ok;
  char qname[kNameCap];
  char qtype[16];
  char server[64];
  int port;
  int rcode;
  bool aa;
  bool ra;
  int elapsed_ms;
  int n_ans;
  Answer ans[kAnsCap];
  char err[128];
};

static bool is_field_server(const char* s) {
  if (!s || !s[0]) return false;
  for (int i = 0; kFieldServers[i]; ++i) {
    if (std::strcmp(s, kFieldServers[i]) == 0) return true;
  }
  // RFC1918 / loopback treated as Field/local plane
  if (std::strncmp(s, "127.", 4) == 0) return true;
  if (std::strncmp(s, "192.168.", 8) == 0) return true;
  if (std::strncmp(s, "10.", 3) == 0) return true;
  if (std::strncmp(s, "172.", 4) == 0) {
    // 172.16–31
    int b = std::atoi(s + 4);
    if (b >= 16 && b <= 31) return true;
  }
  return false;
}

static bool is_public_helper(const char* s) {
  if (!s || !s[0]) return false;
  for (int i = 0; kPublicHelpers[i]; ++i) {
    if (std::strcmp(s, kPublicHelpers[i]) == 0) return true;
  }
  return false;
}

// ALL DNS qtypes — Field is sole authority · not A-only
static uint16_t qtype_num(const char* t) {
  if (!t) return 1;
  if (std::strcmp(t, "A") == 0) return 1;
  if (std::strcmp(t, "NS") == 0) return 2;
  if (std::strcmp(t, "CNAME") == 0) return 5;
  if (std::strcmp(t, "SOA") == 0) return 6;
  if (std::strcmp(t, "PTR") == 0) return 12;
  if (std::strcmp(t, "MX") == 0) return 15;
  if (std::strcmp(t, "TXT") == 0) return 16;
  if (std::strcmp(t, "AAAA") == 0) return 28;
  if (std::strcmp(t, "SRV") == 0) return 33;
  if (std::strcmp(t, "NAPTR") == 0) return 35;
  if (std::strcmp(t, "DS") == 0) return 43;
  if (std::strcmp(t, "RRSIG") == 0) return 46;
  if (std::strcmp(t, "NSEC") == 0) return 47;
  if (std::strcmp(t, "DNSKEY") == 0) return 48;
  if (std::strcmp(t, "SVCB") == 0) return 64;
  if (std::strcmp(t, "HTTPS") == 0) return 65;
  if (std::strcmp(t, "SPF") == 0) return 99;
  if (std::strcmp(t, "CAA") == 0) return 257;
  if (std::strcmp(t, "ANY") == 0 || std::strcmp(t, "*") == 0) return 255;
  // TYPE123 form
  if (t[0] == 'T' && t[1] == 'Y' && t[2] == 'P' && t[3] == 'E' && t[4]) {
    int v = 0;
    for (int i = 4; t[i]; ++i) {
      if (t[i] < '0' || t[i] > '9') return 1;
      v = v * 10 + (t[i] - '0');
      if (v > 65535) return 1;
    }
    if (v > 0) return static_cast<uint16_t>(v);
  }
  return 1;
}

static const char* qtype_name(uint16_t t) {
  switch (t) {
    case 1: return "A";
    case 2: return "NS";
    case 5: return "CNAME";
    case 6: return "SOA";
    case 12: return "PTR";
    case 15: return "MX";
    case 16: return "TXT";
    case 28: return "AAAA";
    case 33: return "SRV";
    case 35: return "NAPTR";
    case 43: return "DS";
    case 46: return "RRSIG";
    case 47: return "NSEC";
    case 48: return "DNSKEY";
    case 64: return "SVCB";
    case 65: return "HTTPS";
    case 99: return "SPF";
    case 257: return "CAA";
    case 255: return "ANY";
    default: return "TYPE";
  }
}

static bool is_type_token(const char* a) {
  if (!a) return false;
  char u[16];
  size_t n = 0;
  for (; a[n] && n + 1 < sizeof(u); ++n) {
    char c = a[n];
    if (c >= 'a' && c <= 'z') c = static_cast<char>(c - 32);
    u[n] = c;
  }
  u[n] = 0;
  if (std::strcmp(u, "A") == 0) return true;
  // Known named types OR TYPE#### — qtype_num returns 1 for unknown non-A
  if (std::strcmp(u, "ANY") == 0 || std::strcmp(u, "*") == 0) return true;
  if (u[0] == 'T' && u[1] == 'Y' && u[2] == 'P' && u[3] == 'E' && u[4])
    return true;
  uint16_t q = qtype_num(u);
  return q != 1 || std::strcmp(u, "A") == 0;
}

static void upper_copy(char* dst, size_t cap, const char* src) {
  size_t i = 0;
  for (; src[i] && i + 1 < cap; ++i) {
    char c = src[i];
    if (c >= 'a' && c <= 'z') c = static_cast<char>(c - 32);
    dst[i] = c;
  }
  dst[i] = 0;
}

static int encode_name(const char* name, uint8_t* out, size_t cap) {
  if (!name || !out || cap < 2) return -1;
  size_t o = 0;
  const char* p = name;
  // strip trailing dots
  size_t len = std::strlen(name);
  while (len > 0 && name[len - 1] == '.') --len;
  if (len == 0) {
    out[0] = 0;
    return 1;
  }
  while (p < name + len) {
    const char* dot = static_cast<const char*>(std::memchr(p, '.', static_cast<size_t>(name + len - p)));
    size_t lab = dot ? static_cast<size_t>(dot - p) : static_cast<size_t>(name + len - p);
    if (lab == 0 || lab > 63) return -1;
    if (o + 1 + lab + 1 > cap) return -1;
    out[o++] = static_cast<uint8_t>(lab);
    for (size_t i = 0; i < lab; ++i) {
      char c = p[i];
      if (c >= 'A' && c <= 'Z') c = static_cast<char>(c + 32);
      out[o++] = static_cast<uint8_t>(c);
    }
    p += lab;
    if (p < name + len && *p == '.') ++p;
  }
  out[o++] = 0;
  return static_cast<int>(o);
}

static int decode_name(const uint8_t* data, size_t dlen, size_t offset, char* out,
                       size_t ocap, size_t* end_off) {
  if (!data || !out || ocap < 2 || offset >= dlen) return -1;
  size_t o = 0;
  size_t i = offset;
  size_t jumped_end = 0;
  bool jumped = false;
  int guard = 0;
  while (i < dlen && guard++ < 64) {
    uint8_t n = data[i];
    if (n == 0) {
      if (!jumped) jumped_end = i + 1;
      break;
    }
    if ((n & 0xC0) == 0xC0) {
      if (i + 1 >= dlen) return -1;
      size_t ptr = ((static_cast<size_t>(n & 0x3F) << 8) | data[i + 1]);
      if (!jumped) jumped_end = i + 2;
      jumped = true;
      i = ptr;
      continue;
    }
    if (n > 63 || i + 1 + n > dlen) return -1;
    if (o && o + 1 < ocap) out[o++] = '.';
    for (uint8_t k = 0; k < n && o + 1 < ocap; ++k) {
      out[o++] = static_cast<char>(data[i + 1 + k]);
    }
    i += 1u + n;
    if (!jumped) jumped_end = i;
  }
  out[o] = 0;
  if (end_off) *end_off = jumped ? jumped_end : (i < dlen && data[i] == 0 ? i + 1 : jumped_end);
  if (!jumped && end_off && *end_off == 0) *end_off = i + 1;
  return 0;
}

static int build_query(const char* qname, const char* qtype, uint8_t* pkt, size_t cap,
                       uint16_t* txn_out) {
  if (cap < 18) return -1;
  struct timeval tvseed {};
  gettimeofday(&tvseed, nullptr);
  uint16_t txn = static_cast<uint16_t>(
      (getpid() ^ static_cast<unsigned>(tvseed.tv_sec) ^ static_cast<unsigned>(tvseed.tv_usec)) &
      0xFFFF);
  if (txn == 0) txn = 1;
  if (txn_out) *txn_out = txn;
  uint16_t flags = 0x0100;  // RD
  uint16_t qd = 1, an = 0, ns = 0, ar = 0;
  pkt[0] = static_cast<uint8_t>(txn >> 8);
  pkt[1] = static_cast<uint8_t>(txn & 0xFF);
  pkt[2] = static_cast<uint8_t>(flags >> 8);
  pkt[3] = static_cast<uint8_t>(flags & 0xFF);
  pkt[4] = 0;
  pkt[5] = 1;
  pkt[6] = pkt[7] = pkt[8] = pkt[9] = pkt[10] = pkt[11] = 0;
  (void)qd;
  (void)an;
  (void)ns;
  (void)ar;
  int nlen = encode_name(qname, pkt + 12, cap - 16);
  if (nlen < 0) return -1;
  size_t o = 12 + static_cast<size_t>(nlen);
  if (o + 4 > cap) return -1;
  uint16_t qt = qtype_num(qtype);
  pkt[o++] = static_cast<uint8_t>(qt >> 8);
  pkt[o++] = static_cast<uint8_t>(qt & 0xFF);
  pkt[o++] = 0;
  pkt[o++] = 1;  // IN
  return static_cast<int>(o);
}

static int parse_answers(const uint8_t* data, size_t dlen, Result* r) {
  if (!data || !r || dlen < 12) {
    if (r) {
      r->ok = false;
      std::snprintf(r->err, sizeof(r->err), "short_packet");
    }
    return -1;
  }
  uint16_t flags = (static_cast<uint16_t>(data[2]) << 8) | data[3];
  uint16_t qd = (static_cast<uint16_t>(data[4]) << 8) | data[5];
  uint16_t an = (static_cast<uint16_t>(data[6]) << 8) | data[7];
  r->rcode = flags & 0xF;
  r->aa = (flags & 0x0400) != 0;
  r->ra = (flags & 0x0080) != 0;
  r->ok = (r->rcode == 0);
  r->n_ans = 0;
  size_t off = 12;
  for (uint16_t i = 0; i < qd && off < dlen; ++i) {
    char junk[kNameCap];
    size_t end = 0;
    if (decode_name(data, dlen, off, junk, sizeof(junk), &end) != 0) break;
    off = end;
    if (off + 4 > dlen) break;
    off += 4;
  }
  for (uint16_t i = 0; i < an && r->n_ans < kAnsCap && off + 10 <= dlen; ++i) {
    Answer* a = &r->ans[r->n_ans];
    std::memset(a, 0, sizeof(*a));
    size_t end = 0;
    if (decode_name(data, dlen, off, a->name, sizeof(a->name), &end) != 0) break;
    off = end;
    if (off + 10 > dlen) break;
    uint16_t rtype = (static_cast<uint16_t>(data[off]) << 8) | data[off + 1];
    // uint16_t rclass = (data[off+2]<<8)|data[off+3];
    a->ttl = (static_cast<uint32_t>(data[off + 4]) << 24) |
             (static_cast<uint32_t>(data[off + 5]) << 16) |
             (static_cast<uint32_t>(data[off + 6]) << 8) | data[off + 7];
    uint16_t rdlen = (static_cast<uint16_t>(data[off + 8]) << 8) | data[off + 9];
    off += 10;
    if (off + rdlen > dlen) break;
    std::snprintf(a->type, sizeof(a->type), "%s", qtype_name(rtype));
    if (rtype == 1 && rdlen == 4) {
      std::snprintf(a->data, sizeof(a->data), "%u.%u.%u.%u", data[off], data[off + 1],
                    data[off + 2], data[off + 3]);
    } else if (rtype == 28 && rdlen == 16) {
      char buf[INET6_ADDRSTRLEN];
      if (inet_ntop(AF_INET6, data + off, buf, sizeof(buf)))
        std::snprintf(a->data, sizeof(a->data), "%s", buf);
      else
        std::snprintf(a->data, sizeof(a->data), "(aaaa)");
    } else if (rtype == 5 || rtype == 2 || rtype == 12) {
      size_t nend = 0;
      if (decode_name(data, dlen, off, a->data, sizeof(a->data), &nend) != 0)
        std::snprintf(a->data, sizeof(a->data), "(name)");
    } else if (rtype == 15 && rdlen >= 3) {
      uint16_t pref = (static_cast<uint16_t>(data[off]) << 8) | data[off + 1];
      char mx[kNameCap];
      size_t nend = 0;
      if (decode_name(data, dlen, off + 2, mx, sizeof(mx), &nend) == 0)
        std::snprintf(a->data, sizeof(a->data), "%u %s", pref, mx);
      else
        std::snprintf(a->data, sizeof(a->data), "%u", pref);
    } else if (rtype == 6 && rdlen >= 22) {
      // SOA — mname rname + 5×uint32
      char mname[kNameCap], rname[kNameCap];
      size_t nend = 0;
      size_t so = off;
      if (decode_name(data, dlen, so, mname, sizeof(mname), &nend) != 0)
        std::snprintf(mname, sizeof(mname), "?");
      so = nend;
      if (decode_name(data, dlen, so, rname, sizeof(rname), &nend) != 0)
        std::snprintf(rname, sizeof(rname), "?");
      so = nend;
      uint32_t serial = 0, refresh = 0, retry = 0, expire = 0, minimum = 0;
      if (so + 20 <= off + rdlen) {
        serial = (static_cast<uint32_t>(data[so]) << 24) |
                 (static_cast<uint32_t>(data[so + 1]) << 16) |
                 (static_cast<uint32_t>(data[so + 2]) << 8) | data[so + 3];
        refresh = (static_cast<uint32_t>(data[so + 4]) << 24) |
                  (static_cast<uint32_t>(data[so + 5]) << 16) |
                  (static_cast<uint32_t>(data[so + 6]) << 8) | data[so + 7];
        retry = (static_cast<uint32_t>(data[so + 8]) << 24) |
                (static_cast<uint32_t>(data[so + 9]) << 16) |
                (static_cast<uint32_t>(data[so + 10]) << 8) | data[so + 11];
        expire = (static_cast<uint32_t>(data[so + 12]) << 24) |
                 (static_cast<uint32_t>(data[so + 13]) << 16) |
                 (static_cast<uint32_t>(data[so + 14]) << 8) | data[so + 15];
        minimum = (static_cast<uint32_t>(data[so + 16]) << 24) |
                  (static_cast<uint32_t>(data[so + 17]) << 16) |
                  (static_cast<uint32_t>(data[so + 18]) << 8) | data[so + 19];
      }
      std::snprintf(a->data, sizeof(a->data),
                    "%s %s %u %u %u %u %u", mname, rname, serial, refresh, retry,
                    expire, minimum);
    } else if (rtype == 33 && rdlen >= 7) {
      // SRV priority weight port target
      uint16_t pri = (static_cast<uint16_t>(data[off]) << 8) | data[off + 1];
      uint16_t weight = (static_cast<uint16_t>(data[off + 2]) << 8) | data[off + 3];
      uint16_t port = (static_cast<uint16_t>(data[off + 4]) << 8) | data[off + 5];
      char tgt[kNameCap];
      size_t nend = 0;
      if (decode_name(data, dlen, off + 6, tgt, sizeof(tgt), &nend) == 0)
        std::snprintf(a->data, sizeof(a->data), "%u %u %u %s", pri, weight, port,
                      tgt);
      else
        std::snprintf(a->data, sizeof(a->data), "%u %u %u", pri, weight, port);
    } else if (rtype == 16) {
      // TXT — concatenate character-strings (ALL DNS)
      size_t o = 0;
      size_t p = 0;
      while (p < rdlen && o + 1 < sizeof(a->data)) {
        uint8_t n = data[off + p];
        p += 1;
        if (p + n > rdlen) break;
        size_t cpy = n;
        if (o + cpy >= sizeof(a->data)) cpy = sizeof(a->data) - 1 - o;
        std::memcpy(a->data + o, data + off + p, cpy);
        o += cpy;
        p += n;
        if (p < rdlen && o + 1 < sizeof(a->data)) a->data[o++] = ' ';
      }
      a->data[o] = 0;
    } else if (rtype == 257 && rdlen >= 2) {
      // CAA flags tag value
      uint8_t flags = data[off];
      uint8_t tlen = data[off + 1];
      if (2u + tlen <= rdlen) {
        char tag[64];
        size_t tl = tlen < sizeof(tag) - 1 ? tlen : sizeof(tag) - 1;
        std::memcpy(tag, data + off + 2, tl);
        tag[tl] = 0;
        size_t vlen = rdlen - 2u - tlen;
        char val[192];
        size_t vl = vlen < sizeof(val) - 1 ? vlen : sizeof(val) - 1;
        std::memcpy(val, data + off + 2 + tlen, vl);
        val[vl] = 0;
        std::snprintf(a->data, sizeof(a->data), "%u %s \"%s\"", flags, tag, val);
      }
    } else {
      // hex dump short (HTTPS/SVCB/DNSKEY/etc still visible)
      size_t h = 0;
      for (uint16_t b = 0; b < rdlen && h + 3 < sizeof(a->data); ++b)
        h += static_cast<size_t>(
            std::snprintf(a->data + h, sizeof(a->data) - h, "%02x", data[off + b]));
    }
    off += rdlen;
    r->n_ans++;
  }
  return 0;
}

static int query_one(const char* server, int port, const char* qname, const char* qtype,
                     int timeout_ms, Result* r) {
  std::memset(r, 0, sizeof(*r));
  std::snprintf(r->qname, sizeof(r->qname), "%s", qname);
  std::snprintf(r->qtype, sizeof(r->qtype), "%s", qtype);
  std::snprintf(r->server, sizeof(r->server), "%s", server);
  r->port = port;

  uint8_t pkt[kPktCap];
  uint16_t txn = 0;
  int qlen = build_query(qname, qtype, pkt, sizeof(pkt), &txn);
  if (qlen < 0) {
    std::snprintf(r->err, sizeof(r->err), "build_query_fail");
    return -1;
  }

  int fd = ::socket(AF_INET, SOCK_DGRAM | SOCK_CLOEXEC, 0);
  if (fd < 0) {
    std::snprintf(r->err, sizeof(r->err), "socket:%d", errno);
    return -1;
  }

  struct sockaddr_in sa {};
  sa.sin_family = AF_INET;
  sa.sin_port = htons(static_cast<uint16_t>(port));
  if (inet_pton(AF_INET, server, &sa.sin_addr) != 1) {
    ::close(fd);
    std::snprintf(r->err, sizeof(r->err), "bad_server");
    return -1;
  }

  struct timeval t0 {};
  gettimeofday(&t0, nullptr);

  if (::sendto(fd, pkt, static_cast<size_t>(qlen), 0,
               reinterpret_cast<struct sockaddr*>(&sa), sizeof(sa)) < 0) {
    std::snprintf(r->err, sizeof(r->err), "send:%d", errno);
    ::close(fd);
    return -1;
  }

  fd_set rfds;
  FD_ZERO(&rfds);
  FD_SET(fd, &rfds);
  struct timeval tv {};
  tv.tv_sec = timeout_ms / 1000;
  tv.tv_usec = (timeout_ms % 1000) * 1000;
  int sel = ::select(fd + 1, &rfds, nullptr, nullptr, &tv);
  if (sel <= 0) {
    std::snprintf(r->err, sizeof(r->err), sel == 0 ? "timeout" : "select");
    ::close(fd);
    return -1;
  }

  uint8_t resp[kPktCap];
  ssize_t n = ::recvfrom(fd, resp, sizeof(resp), 0, nullptr, nullptr);
  ::close(fd);
  if (n < 12) {
    std::snprintf(r->err, sizeof(r->err), "short_reply");
    return -1;
  }

  struct timeval t1 {};
  gettimeofday(&t1, nullptr);
  r->elapsed_ms = static_cast<int>((t1.tv_sec - t0.tv_sec) * 1000 +
                                   (t1.tv_usec - t0.tv_usec) / 1000);
  parse_answers(resp, static_cast<size_t>(n), r);
  return r->ok || r->n_ans > 0 ? 0 : -1;
}

static void print_help() {
  std::fputs(
      "field-dig — Grok16 Ironclad dig (C++ · old dig secure · no ISC dig)\n"
      "\n"
      "Usage (classic dig-compatible):\n"
      "  dig [@server] name [type] [+short] [+json] [+time=N] [+tries=N] [-p N]\n"
      "  dig +short duckduckgo.com\n"
      "  dig @1.1.1.1 duckduckgo.com A          # isolated egress (tool plane)\n"
      "  dig @127.0.0.1 -p 53 x.com             # Field Truth plane\n"
      "  field-dig servers | version | help\n"
      "\n"
      "Security:\n"
      "  - OS resolver stays Field (127.0.0.1) — dig never writes resolv.conf\n"
      "  - No @server → Field local mesh only (53/9053/5353)\n"
      "  - Explicit @public → allowed: we talk OUT from isolated dig space\n"
      "    (Field tool egress for world-learn / classic dig) · not client NS\n"
      "  - cite: ironclad:field-bsp-dns:1 · ironclad:field-dig-cpp:3\n"
      "  - motto: Ironclad BSP — it just works\n",
      stdout);
}

static void json_escape_print(const char* s) {
  if (!s) {
    std::fputs("null", stdout);
    return;
  }
  std::fputc('"', stdout);
  for (const unsigned char* p = reinterpret_cast<const unsigned char*>(s); *p; ++p) {
    if (*p == '"' || *p == '\\') {
      std::fputc('\\', stdout);
      std::fputc(static_cast<char>(*p), stdout);
    } else if (*p < 0x20) {
      std::fprintf(stdout, "\\u%04x", *p);
    } else {
      std::fputc(static_cast<char>(*p), stdout);
    }
  }
  std::fputc('"', stdout);
}

static void print_json(const Result& r) {
  std::fputs("{\n  \"ok\": ", stdout);
  std::fputs(r.ok ? "true" : "false", stdout);
  std::fputs(",\n  \"qname\": ", stdout);
  json_escape_print(r.qname);
  std::fputs(",\n  \"qtype\": ", stdout);
  json_escape_print(r.qtype);
  std::fputs(",\n  \"server\": ", stdout);
  json_escape_print(r.server);
  std::fprintf(stdout,
               ",\n  \"port\": %d,\n  \"rcode\": %d,\n  \"aa\": %s,\n  \"ra\": %s,\n"
               "  \"elapsed_ms\": %d,\n  \"field_udp\": true,\n  \"field_dig\": true,\n"
               "  \"tool\": \"field-dig-cpp\",\n  \"bsp\": \"binary_secure_path\",\n"
               "  \"ironclad_cite\": \"%s\",\n  \"ironclad_bsp\": \"%s\",\n"
               "  \"motto\": \"Ironclad BSP — it just works\",\n"
               "  \"replaces\": \"dig\",\n  \"answers\": [",
               r.port, r.rcode, r.aa ? "true" : "false", r.ra ? "true" : "false",
               r.elapsed_ms, kIronclad, kIroncladBsp);
  for (int i = 0; i < r.n_ans; ++i) {
    if (i) std::fputc(',', stdout);
    std::fputs("\n    {\"name\": ", stdout);
    json_escape_print(r.ans[i].name);
    std::fputs(", \"type\": ", stdout);
    json_escape_print(r.ans[i].type);
    std::fprintf(stdout, ", \"ttl\": %u, \"data\": ", r.ans[i].ttl);
    json_escape_print(r.ans[i].data);
    std::fputc('}', stdout);
  }
  std::fputs("\n  ],\n  \"ips\": [", stdout);
  bool first = true;
  for (int i = 0; i < r.n_ans; ++i) {
    if (std::strcmp(r.ans[i].type, "A") == 0 || std::strcmp(r.ans[i].type, "AAAA") == 0) {
      if (!first) std::fputc(',', stdout);
      first = false;
      json_escape_print(r.ans[i].data);
    }
  }
  if (r.err[0]) {
    std::fputs("],\n  \"error\": ", stdout);
    json_escape_print(r.err);
    std::fputs("\n}\n", stdout);
  } else {
    std::fputs("]\n}\n", stdout);
  }
}

static void print_text(const Result& r, const Opts& o) {
  if (o.short_out) {
    for (int i = 0; i < r.n_ans; ++i) {
      if (std::strcmp(r.ans[i].type, "A") == 0 || std::strcmp(r.ans[i].type, "AAAA") == 0 ||
          std::strcmp(r.qtype, r.ans[i].type) == 0) {
        std::fprintf(stdout, "%s\n", r.ans[i].data);
      }
    }
    return;
  }
  if (!o.noall && !o.answer_only) {
    std::fprintf(stdout, "; <<>> Field-DiG Ironclad BSP <<>> %s %s\n", r.qname, r.qtype);
    std::fprintf(stdout, ";; Field UDP server: %s#%d\n", r.server, r.port);
    std::fprintf(stdout, ";; tool: field-dig-cpp · bsp: %s · cite: %s\n", kIroncladBsp,
                 kIronclad);
    if (o.isolated_out || (!is_field_server(r.server) && r.server[0])) {
      std::fputs(";; mode: isolated_egress (tool plane · not client NS)\n", stdout);
    } else {
      std::fputs(";; mode: field_truth_plane\n", stdout);
    }
    std::fprintf(stdout, ";; flags: qr%s%s rcode=%d\n", r.ra ? " ra" : "", r.aa ? " aa" : "",
                 r.rcode);
    std::fputs(";; QUESTION SECTION:\n", stdout);
    std::fprintf(stdout, ";%s.\t\tIN\t%s\n\n", r.qname, r.qtype);
    std::fputs(";; ANSWER SECTION:\n", stdout);
  }
  for (int i = 0; i < r.n_ans; ++i) {
    std::fprintf(stdout, "%s.\t\t%u\tIN\t%s\t%s\n", r.ans[i].name[0] ? r.ans[i].name : r.qname,
                 r.ans[i].ttl, r.ans[i].type, r.ans[i].data);
  }
  if (r.n_ans == 0 && !o.short_out) std::fputs("; no answers\n", stdout);
  if (o.stats || (!o.short_out && !o.noall)) {
    std::fprintf(stdout, "\n;; Query time: %d msec\n", r.elapsed_ms);
    std::fprintf(stdout, ";; SERVER: %s#%d (Field UDP)\n", r.server, r.port);
    std::fprintf(stdout, ";; MSG: field-native Grok16 C++ (no ISC dig)\n");
  }
}

static void parse_argv(int argc, char** argv, Opts* o) {
  std::memset(o, 0, sizeof(*o));
  o->port = kDefaultPort;
  o->tries = 2;
  o->time_ms = kDefaultTimeMs;
  std::snprintf(o->qtype, sizeof(o->qtype), "A");

  char pos[8][kNameCap];
  int npos = 0;

  for (int i = 1; i < argc; ++i) {
    const char* a = argv[i];
    if (!a) continue;
    if (std::strcmp(a, "-h") == 0 || std::strcmp(a, "--help") == 0 ||
        std::strcmp(a, "help") == 0) {
      o->help = true;
      return;
    }
    if (std::strcmp(a, "version") == 0 || std::strcmp(a, "-v") == 0) {
      o->version = true;
      return;
    }
    if (std::strcmp(a, "servers") == 0) {
      o->servers_cmd = true;
      return;
    }
    if (a[0] == '@' && a[1]) {
      std::snprintf(o->server, sizeof(o->server), "%s", a + 1);
      o->user_server = true;
      continue;
    }
    if (a[0] == '+') {
      const char* f = a + 1;
      if (std::strcmp(f, "short") == 0)
        o->short_out = true;
      else if (std::strcmp(f, "json") == 0 || std::strcmp(f, "yaml") == 0)
        o->json = true;
      else if (std::strcmp(f, "noall") == 0)
        o->noall = true;
      else if (std::strcmp(f, "answer") == 0)
        o->answer_only = true;
      else if (std::strcmp(f, "stats") == 0)
        o->stats = true;
      else if (std::strncmp(f, "time=", 5) == 0) {
        int sec = static_cast<int>(std::atoi(f + 5));
        if (sec > 0) o->time_ms = sec * 1000;
        // classic dig +time=N is seconds; also accept ms if huge
        if (sec > 30) o->time_ms = sec;  // already ms-ish
      } else if (std::strncmp(f, "tries=", 6) == 0) {
        int t = static_cast<int>(std::atoi(f + 6));
        if (t > 0) o->tries = t;
      }
      // ignore unknown +flags for classic dig compatibility
      continue;
    }
    if (std::strcmp(a, "-t") == 0 && i + 1 < argc) {
      upper_copy(o->qtype, sizeof(o->qtype), argv[++i]);
      continue;
    }
    if (std::strcmp(a, "-p") == 0 && i + 1 < argc) {
      o->port = static_cast<int>(std::atoi(argv[++i]));
      if (o->port <= 0 || o->port > 65535) o->port = 53;
      o->user_port = true;
      continue;
    }
    if (std::strcmp(a, "-4") == 0 || std::strcmp(a, "-6") == 0) continue;
    // classic dig: -q name
    if (std::strcmp(a, "-q") == 0 && i + 1 < argc) {
      std::snprintf(o->name, sizeof(o->name), "%s", argv[++i]);
      continue;
    }
    if (npos < 8) {
      std::snprintf(pos[npos], sizeof(pos[npos]), "%s", a);
      ++npos;
    }
  }

  for (int i = 0; i < npos; ++i) {
    char u[16];
    upper_copy(u, sizeof(u), pos[i]);
    if (is_type_token(pos[i]) && o->name[0] == 0) {
      // type-first only if another token looks like a name
      bool has_name = false;
      for (int j = 0; j < npos; ++j) {
        if (j == i) continue;
        if (!is_type_token(pos[j]) || std::strchr(pos[j], '.') != nullptr) {
          has_name = true;
          break;
        }
      }
      if (has_name && std::strchr(pos[i], '.') == nullptr) {
        std::snprintf(o->qtype, sizeof(o->qtype), "%s", u);
        continue;
      }
    }
    if (o->name[0] == 0) {
      if (!is_type_token(pos[i]) || std::strchr(pos[i], '.') != nullptr) {
        std::snprintf(o->name, sizeof(o->name), "%s", pos[i]);
        continue;
      }
    }
    if (is_type_token(pos[i])) upper_copy(o->qtype, sizeof(o->qtype), pos[i]);
  }
  if (o->name[0] == 0 && npos > 0) {
    for (int i = npos - 1; i >= 0; --i) {
      if (!is_type_token(pos[i]) || std::strchr(pos[i], '.') != nullptr) {
        std::snprintf(o->name, sizeof(o->name), "%s", pos[i]);
        break;
      }
    }
  }
  // lowercase qname
  for (char* p = o->name; *p; ++p) {
    if (*p >= 'A' && *p <= 'Z') *p = static_cast<char>(*p + 32);
    if (*p == '.' && p[1] == 0) {
      *p = 0;
      break;
    }
  }
}

}  // namespace

int main(int argc, char** argv) {
  Opts o;
  parse_argv(argc, argv, &o);

  if (o.help) {
    print_help();
    return 0;
  }
  if (o.version) {
    std::fprintf(stdout, "%s\ncite: %s\nbsp: %s\nmotto: Ironclad BSP — it just works\n",
                 kVersion, kIronclad, kIroncladBsp);
    return 0;
  }
  if (o.servers_cmd) {
    std::fputs(
        "{\n"
        "  \"field_servers\": [\"127.0.0.1\", \"192.168.47.1\", \"192.168.50.1\", "
        "\"127.0.0.53\"],\n"
        "  \"isolated_egress_helpers\": [\"1.1.1.1\", \"8.8.8.8\", \"9.9.9.9\", "
        "\"208.67.222.222\"],\n"
        "  \"policy\": {\n"
        "    \"default\": \"field_truth_plane\",\n"
        "    \"explicit_at_server\": \"honored\",\n"
        "    \"public_helper_mode\": \"isolated_egress_tool_plane\",\n"
        "    \"writes_resolv_conf\": false,\n"
        "    \"client_foreign_ns\": false\n"
        "  },\n"
        "  \"ironclad_cite\": \"",
        stdout);
    std::fputs(kIronclad, stdout);
    std::fputs(
        "\",\n  \"bsp\": \"binary_secure_path\",\n"
        "  \"motto\": \"Old dig secure · talk out from isolated spaces\"\n}\n",
        stdout);
    return 0;
  }

  if (!o.name[0]) {
    std::fputs(";; Usage: dig [@server] name [type] [+short|+json]\n", stderr);
    return 1;
  }

  char servers[kSrvCap][64];
  int nsrv = 0;

  if (o.user_server && o.server[0]) {
    // Explicit @server always honored — classic dig + Field isolated egress.
    // We talk OUT from this tool process only; never install as OS NS.
    std::snprintf(servers[nsrv++], sizeof(servers[0]), "%s", o.server);
    o.isolated_out = !is_field_server(o.server);
    if (o.isolated_out && o.time_ms < 1200) o.time_ms = 1200;
  } else {
    // No @server → Field Truth plane only
    for (int i = 0; kFieldServers[i] && nsrv < kSrvCap; ++i)
      std::snprintf(servers[nsrv++], sizeof(servers[0]), "%s", kFieldServers[i]);
    o.isolated_out = false;
  }

  Result best {};
  bool any = false;
  for (int t = 0; t < o.tries && !any; ++t) {
    for (int s = 0; s < nsrv && !any; ++s) {
      int ports_try[8];
      int np = 0;
      if (o.user_port) {
        ports_try[np++] = o.port;
      } else if (o.user_server) {
        // Explicit @server → classic dig port 53 (public helpers expect 53)
        ports_try[np++] = 53;
        if (is_field_server(servers[s])) {
          // Also try mesh high ports for Field servers
          ports_try[np++] = 9053;
          ports_try[np++] = 5353;
        }
      } else {
        for (int pi = 0; kFieldPorts[pi] && np < 8; ++pi)
          ports_try[np++] = kFieldPorts[pi];
      }
      for (int pi = 0; pi < np && !any; ++pi) {
        Result r {};
        if (query_one(servers[s], ports_try[pi], o.name, o.qtype, o.time_ms, &r) ==
                0 ||
            r.n_ans > 0) {
          best = r;
          any = true;
          break;
        }
        if (!any) best = r;
      }
    }
  }

  // Honest: timed-out empty is not a quiet success
  if (!any && best.err[0] == 0)
    std::snprintf(best.err, sizeof(best.err), "no_response");

  // Stamp isolated mode for text printer
  if (any && best.server[0] && !is_field_server(best.server)) o.isolated_out = true;

  if (o.json ||
      (std::getenv("FIELD_DIG_JSON") &&
       std::strcmp(std::getenv("FIELD_DIG_JSON"), "1") == 0))
    print_json(best);
  else
    print_text(best, o);

  return (best.ok || best.n_ans > 0) ? 0 : 1;
}
