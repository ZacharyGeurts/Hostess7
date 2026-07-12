// field_ammoos.hpp — AmmoOS classic desktop · Field One (C++ / HPP)
// Serves full stack panel on :9477 · no Python · no shell control
// ironclad:field-ammoos-cpp:1
#pragma once

namespace field {
namespace ammoos {

inline constexpr const char* kIronclad = "ironclad:field-ammoos-cpp:1";
inline constexpr const char* kVersion =
    "Field-AmmoOS 4.0.0-cpp (classic desktop · full stack · no sh/py)";
inline constexpr const char* kSchema = "field-ammoos/v1";
inline constexpr const char* kMotto =
    "AmmoOS classic · Field One · NEXUS C2 → Ironclad → KILROY → DNS/DHCP · "
    "Hostess 7 multibrain";

inline constexpr int kPort = 9477;
inline constexpr int kPortAlt = 9478;
inline constexpr const char* kBind = "127.0.0.1";

// Canonical desktop entry paths (under panel/)
inline constexpr const char* kDesktopFile = "field-desktop.html";
inline constexpr const char* kFieldFile = "field.html";

// GitHub Pages OS surface
inline constexpr const char* kPagesOs =
    "https://zacharygeurts.github.io/Hostess7/desktop/";
inline constexpr const char* kPagesAmmo =
    "https://zacharygeurts.github.io/AmmoOS/";
inline constexpr const char* kPagesHostess =
    "https://zacharygeurts.github.io/Hostess7/";

}  // namespace ammoos
}  // namespace field
