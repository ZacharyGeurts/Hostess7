// field_hostess7.hpp — Hostess 7 Field package doctrine (C++ / HPP only)
// ALWAYS FIELD ONE (1) · DISALLOW OTHERS · All Field all day · Grok16
// NO Python · NO shell · NO polkit · plates + forever + binary .h7m
// Distributed multibrain RAID-0 · shared redundant · like our servers
// ironclad:field-hostess7-cpp:2
#pragma once

namespace field {
namespace hostess7 {

inline constexpr const char* kIronclad = "ironclad:field-hostess7-cpp:2";
inline constexpr const char* kVersion =
    "Field-Hostess7 4.0.0-cpp (Field One · multibrain RAID-0 · no sh/py/json)";
inline constexpr const char* kMotto =
    "ALWAYS FIELD ONE · DISALLOW OTHERS · All Field all day · Grok16 · "
    "Hostess 7 full package · distributed brain · polkit HOSTILE · C++/HPP";
inline constexpr const char* kSchema = "hostess7-field-package/v2";

// ALWAYS FIELD ONE (1) — never multi-field / never foreign field plane
inline constexpr int kFieldOne = 1;
inline constexpr const char* kFieldOneId = "FIELD_ONE";
inline constexpr const char* kFieldPolicy = "ALWAYS_FIELD_ONE_DISALLOW_OTHERS";
inline constexpr const char* kGrok16 = "Grok16-16.1.0-hard";
inline constexpr const char* kPlaneDay = "ALL_FIELD_ALL_DAY";

// Distributed brain plane (logical) — still Field One only
// Shared across our servers · redundant · RAID-0 stripe doctrine
inline constexpr int kBrainNodes = 32;
inline constexpr int kBrainRaid = 0;  // RAID-0 stripe doctrine
inline constexpr int kBrainStripeWidth = 8;
inline constexpr int kBrainHorses = 4;
inline constexpr const char* kBrainPlane = "hostess7_multibrain_dc_mesh";
inline constexpr const char* kBrainMode = "shared_redundant_raid0_stripe";

inline constexpr const char* kElevation = "field-elevate autoelevate";
inline constexpr const char* kPolkit = "HOSTILE";

// GitHub / online surface (optional distributed mirror · package boots local)
inline constexpr const char* kGithub =
    "https://github.com/ZacharyGeurts/Hostess7";
inline constexpr const char* kPages =
    "https://zacharygeurts.github.io/Hostess7/";

// Core Field binaries that ARE Hostess 7 ops (NewLatest package)
inline constexpr const char* kCoreBins[] = {
    "field-hostess7",
    "field-hostess7-stack-update",
    "field-elevate",
    "field-world-dns",
    "field-world-dhcp",
    "field-dns-dhcp-h7-raid",
    "field-fleet-mesh",
    "field-h7r-capacity-fleet",
    "field-plane-autopilot",
    "field-plane-chip",
    "field-nexus-c2-chip",
    "field-nexus-c2-bank",
    "field-all-chip",
    "field-antivirus",
    "field-big-grin-swallows",
    "field-up-eats",
    "field-ammolang",
    "field-ironclad-bsp",
    "field-rollout",
    "field-kilroy-ipxe-stack",
    "field-ammonet-cloud",
    "field-compile-truth",
    "field-ammoos",
    "field-everyone",
    "field-hdmi-audio",
    nullptr,
};

// Role labels for multibrain stripe members (cycles)
inline constexpr const char* kBrainRoles[] = {
    "grow",     "think",       "learn",      "guard",
    "serve",    "raid_stripe", "ammonet_horse", "tools_carry",
    nullptr,
};

}  // namespace hostess7
}  // namespace field
