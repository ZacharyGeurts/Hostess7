#include "FieldQueenNet.hpp"

#include <cstdio>
#include <cstring>

// Forward declare guest CPU — same layout as AMOURANTHRTX x86emu.
struct x86emu_t;

namespace FieldQueenNet {

namespace {

bool isLoopbackHost(const char* host) noexcept {
    if (!host || !host[0]) return false;
    return std::strcmp(host, "127.0.0.1") == 0
        || std::strcmp(host, "localhost") == 0
        || std::strncmp(host, "queen.", 6) == 0
        || std::strncmp(host, "hostess7.", 9) == 0;
}

bool urlInternal(const char* url) noexcept {
    if (!url || !url[0]) return true;
    if (std::strncmp(url, "about:", 6) == 0) return true;
    if (std::strncmp(url, "file:", 5) == 0) return true;
    if (std::strncmp(url, "queen://", 8) == 0) return true;
    if (std::strncmp(url, "http://127.0.0.1", 16) == 0) return true;
    if (std::strncmp(url, "http://localhost", 16) == 0) return true;
    if (!sovereignInternalOnly()) return true;
    return false;
}

} // namespace

int handleIntNet(struct x86emu_t* /*emu*/, std::uint8_t intNum) noexcept {
    // FIELDC guest modules (FieldNetDos.fld) will replace this stub.
    std::fprintf(stderr, "[Queen FieldNet] INT %02X — sovereign redirector (FIELDC pending)\n", intNum);
    return 1;
}

bool permitUrl(const char* url) noexcept {
    if (!sovereignInternalOnly()) return true;
    const bool ok = urlInternal(url);
    if (!ok)
        std::fprintf(stderr, "[Queen FieldNet] BLOCK external: %s\n", url ? url : "(null)");
    return ok;
}

} // namespace FieldQueenNet