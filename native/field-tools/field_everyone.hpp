// field_everyone.hpp — Everyone · measured DNS/DHCP truth · AmmoNet (C++ only)
// Hostess 7 boss · Zac @ZacharyGeurts · NO Python
// ironclad:field-everyone-cpp:5
//
// SERIOUS MODE: report measured live counters only.
// Capacity / design targets are labeled capacity — never inflated as "active".
#pragma once

namespace field {
namespace everyone {

inline constexpr const char* kIronclad = "ironclad:field-everyone-cpp:5";
inline constexpr const char* kVersion =
    "Field-Everyone 4.0.0-cpp (measured truth · world online when DNS+DHCP live)";
inline constexpr const char* kSchema = "field-everyone-counter/v7-truth";
inline constexpr const char* kMotto =
    "Measured truth only · world online when DNS answers + DHCP listens · "
    "capacity labeled separate · Zac @ZacharyGeurts";

// Design targets (capacity / plan — NOT measured live headcount)
inline constexpr int kFleetTarget = 125000;
inline constexpr int kFleetHotDefault = 208;
inline constexpr const char* kBoss = "hostess7";
inline constexpr const char* kIsp = "ammonet";
inline constexpr const char* kOperator = "Zac";
inline constexpr const char* kX = "@ZacharyGeurts";

// IPv4 address-space capacity (2^32) — authority surface, not active leases
inline constexpr long long kIPv4Capacity = 4294967296LL;
// Dual plane capacity label (DHCP+DNS authority rows) — capacity, not live
inline constexpr long long kPlanetLeaseCapacity = 8589934592LL;

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
    {"everyone_counter", "Everyone measured truth wire", "master", 100, 1},
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
