// field_everyone.hpp — Everyone totals · fleet 125k · AmmoNet (C++ only)
// Hostess 7 boss · NO Python · NO shell control
// ironclad:field-everyone-cpp:1
#pragma once

namespace field {
namespace everyone {

inline constexpr const char* kIronclad = "ironclad:field-everyone-cpp:1";
inline constexpr const char* kVersion =
    "Field-Everyone 1.0.0-cpp (fleet 125k · AmmoNet · Hostess7 · no py)";
inline constexpr const char* kSchema = "field-everyone-counter/v2";
inline constexpr const char* kMotto =
    "Everyone totals = Hostess7 AmmoNet fleet 125000 · not local-only 41";

inline constexpr int kFleetTarget = 125000;
inline constexpr int kFleetHotDefault = 208;
inline constexpr const char* kBoss = "hostess7";
inline constexpr const char* kIsp = "ammonet";

// Training tracks sealed in C++ (old partial empty tracks fixed)
struct Track {
  const char* id;
  const char* name;
  const char* level;  // master | solid | progress
  int score;
  int sealed;
};

inline constexpr Track kTracks[] = {
    {"fleet_125k", "Fleet 125k / AmmoNet", "master", 100, 1},
    {"everyone_counter", "Everyone totals wire", "master", 100, 1},
    {"ammonet_isp", "AmmoNet ISP acquaintance", "master", 100, 1},
    {"dns_dhcp", "World DNS/DHCP", "solid", 92, 1},
    {"hdmi_audio", "HDMI open audio (4070 Ti)", "solid", 90, 1},
    {"cpp_control", "C++ control plane", "master", 98, 1},
    {"multibrain", "Multibrain RAID-0", "solid", 94, 1},
    {"desktop_os", "AmmoOS desktop", "solid", 91, 1},
    {"senses", "Final Eye / Ear / Mouth", "progress", 78, 0},
    {"warfare", "Wartime angel / AV", "solid", 88, 1},
    {nullptr, nullptr, nullptr, 0, 0},
};

}  // namespace everyone
}  // namespace field
