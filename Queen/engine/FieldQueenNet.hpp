#pragma once

// Queen FieldNet — AmmoOS network takeover inside RTX secure memory.
// INT 2Ah / 2Ch / 2Dh redirector (replaces DOS "network not installed").
// Guest modules compiled with FIELDC v4 + Grok16 field_opt — see data/queen-field-net.json.

#include <cstdint>
#include <cstdlib>

namespace FieldQueenNet {

constexpr std::uint8_t INT_DOS_NET  = 0x2A;
constexpr std::uint8_t INT_DOS_NET2 = 0x2C;
constexpr std::uint8_t INT_DOS_NET3 = 0x2D;

constexpr std::uint16_t WORLD_PORT_DEFAULT = 9481;

// IFF tag on every Queen datagram (mirrors Hostess7 civilian/hostile doctrine).
enum class Iff : std::uint8_t {
    Civilian = 0,
    Hostile  = 1,
    Legacy   = 2,
};

inline bool sovereignInternalOnly() noexcept {
    const char* v = std::getenv("QUEEN_INTERNAL_ONLY");
    if (!v || !v[0]) return true;
    return v[0] != '0' && v[0] != 'f' && v[0] != 'F' && v[0] != 'n' && v[0] != 'N';
}

// Guest x86 INT handler — return 0 to fall through, 1 handled, 2 re-dispatch.
int handleIntNet(struct x86emu_t* emu, std::uint8_t intNum) noexcept;

// Loopback-only policy for browser / FieldWebPanel navigation.
bool permitUrl(const char* url) noexcept;

} // namespace FieldQueenNet