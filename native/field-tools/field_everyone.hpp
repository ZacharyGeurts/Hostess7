// field_everyone.hpp — Everyone · world rescue DNS/DHCP · AmmoNet (C++ only)
// Hostess 7 boss · Zac @ZacharyGeurts · NO Python
// ironclad:field-everyone-cpp:2
#pragma once

namespace field {
namespace everyone {

inline constexpr const char* kIronclad = "ironclad:field-everyone-cpp:3";
inline constexpr const char* kVersion =
    "Field-Everyone 3.1.0-cpp (Internet 2.0 · 7T ACTIVE leases · not capacity)";
inline constexpr const char* kSchema = "field-everyone-counter/v5";
inline constexpr const char* kMotto =
    "Internet 2.0 · 7 trillion ACTIVE leases · 125k racks · not local 55k";

inline constexpr int kFleetTarget = 125000;
inline constexpr int kFleetHotDefault = 208;
inline constexpr const char* kBoss = "hostess7";
inline constexpr const char* kIsp = "ammonet";
inline constexpr const char* kOperator = "Zac";
inline constexpr const char* kX = "@ZacharyGeurts";

// World plane — Field owns the authority surface (not tiny local ~55k sample)
// 7 trillion devices on 125k racks (fleet-mesh doctrine)
inline constexpr long long kWorldDevices = 7000000000000LL;  // 7T
// Per-rack fan-out (7T / 125000)
inline constexpr long long kDevicesPerRack = 56000000LL;
// Full IPv4 space under Field DNS/DHCP authority
inline constexpr long long kIPv4Owned = 4294967296LL;
// Planet DHCP + DNS authority rows (IPv4 plane)
inline constexpr long long kPlanetDhcp = 4294967296LL;
inline constexpr long long kPlanetDns = 4294967296LL;
// Combined lease authority surface (IPv4×2 doctrine surface)
inline constexpr long long kPlanetLeaseTotal = 8589934592LL;
// ACTIVE device leases on Internet 2.0 plane (trillions) — not capacity label
inline constexpr long long kActiveLeases = 7000000000000LL;
// alias for harvest defaults
inline constexpr long long kDeviceLeases = kActiveLeases;
// Serving plane (active)
inline constexpr long long kServingActive = 1000000000000LL;

// Training tracks (C++ sealed)
struct Track {
  const char* id;
  const char* name;
  const char* level;
  int score;
  int sealed;
};

inline constexpr Track kTracks[] = {
    {"world_rescue", "World rescue → Field DNS/DHCP", "master", 100, 1},
    {"fleet_125k", "Fleet 125k / AmmoNet", "master", 100, 1},
    {"everyone_counter", "Everyone totals wire", "master", 100, 1},
    {"ammonet_isp", "AmmoNet ISP / Internet 2.0", "master", 100, 1},
    {"x_truth", "X @ZacharyGeurts both-ways truth", "solid", 95, 1},
    {"cpp_control", "C++ control plane", "master", 98, 1},
    {"u_pee_swallows", "U Pee / Big Grin Swallows", "solid", 90, 1},
    {"multibrain", "Multibrain RAID-0", "solid", 94, 1},
    {"desktop_os", "AmmoOS desktop", "solid", 91, 1},
    {"warfare", "Wartime angel / AV", "solid", 88, 1},
    {nullptr, nullptr, nullptr, 0, 0},
};

}  // namespace everyone
}  // namespace field
