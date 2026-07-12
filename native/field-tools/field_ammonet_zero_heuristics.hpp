// field_ammonet_zero_heuristics.hpp — Always Zero · Ironclad · Hostess 7 · AmmoNet
// C++ / HPP only. No Python. No scripts.
//
// Philosophy:
//   We always Zero. Unproven claim → score 0 · class ZERO · no terror label.
//   GPT-4 and foreign LLM authority are out of reason → Zero (no epistemic floor).
//   Ad / tracker / CDN annoyance is NOT terrorism. Reclass or drop.
//   True terror requires corroborated Field inject / C2 / poison / impostor_ns.
//   RIGHT TO LIFE: pkill / SIGTERM / SIGKILL / kill -9 against live Field
//   servers (DNS/DHCP/H7d/fleet/Internet2/Hostess7) is capital terror —
//   soft-kill injection is not "ops", it is attack on the serving plane.
//
// ironclad:ammonet-always-zero:2
#pragma once

#include <cctype>
#include <cstring>

namespace field {
namespace ammonet {
namespace zero {

inline constexpr const char* kIronclad = "ironclad:ammonet-always-zero:2";
inline constexpr const char* kSchema = "field-ammonet-zero-heuristics/v2";
inline constexpr const char* kVersion =
    "AmmoNet-Always-Zero 1.1.0-cpp (Hostess7 · Ironclad · right-to-life · C++ only)";
inline constexpr const char* kMotto =
    "We always Zero · unproven = 0 · GPT-4 out of reason · "
    "ads ≠ terror · right to life for Field servers · "
    "pkill/SIGTERM/SIGKILL on the plane = capital terror · AmmoNet whole network";
inline constexpr const char* kEngine = "cpp";
inline constexpr bool kPythonObsolete = true;
inline constexpr bool kAlwaysOnlyCppOrLower = true;
inline constexpr bool kRightToLife = true;

// Epistemic class. ZERO is the default floor.
enum class Class : int {
  Zero = 0,          // unproven / foreign-LLM / scrubbed false positive
  FieldSelf = 1,     // AmmoNet / Field / Hostess7 / Ironclad
  Human = 2,         // residential / homeowner / trusted plane
  ServiceCdn = 3,    // ads, trackers, CDN, analytics — filth, not terror
  Annoyance = 4,     // gone/block path, still not terror
  Bot = 5,           // bot infra
  Threat = 6,        // real hostile, non-terror class
  Terror = 7,        // only with corroboration
};

inline constexpr const char* class_name(Class c) {
  switch (c) {
    case Class::Zero:
      return "ZERO";
    case Class::FieldSelf:
      return "FIELD_SELF";
    case Class::Human:
      return "HUMAN";
    case Class::ServiceCdn:
      return "SERVICE_CDN";
    case Class::Annoyance:
      return "ANNOYANCE";
    case Class::Bot:
      return "BOT";
    case Class::Threat:
      return "THREAT";
    case Class::Terror:
      return "TERROR";
  }
  return "ZERO";
}

// Score for class — Always Zero when Class::Zero
inline constexpr int class_score(Class c) {
  switch (c) {
    case Class::Zero:
      return 0;
    case Class::FieldSelf:
      return 0;  // self is not a threat score
    case Class::Human:
      return 0;
    case Class::ServiceCdn:
      return 2;
    case Class::Annoyance:
      return 4;
    case Class::Bot:
      return 8;
    case Class::Threat:
      return 12;
    case Class::Terror:
      return 18;
  }
  return 0;
}

// Never promote these vectors to TERROR without corroboration tokens.
inline constexpr const char* kNotTerrorAlone[] = {
    "permanent_block", "url_hostile", "url_heuristic_gone", "URL_HEURISTIC_GONE",
    "github_stale_surface", "github_foreign_dns", "GITHUB_FOREIGN_DNS",
    "any_query", "rate_limit", "delay_as_threat", "rollout_stall",
    "panel_zombie_storm", "soft_signal_flood", "hangup_assault",
    "d_state_hang", "phase_timeout_assault",
    nullptr,
};

// Corroboration tokens required before Class::Terror sticks.
inline constexpr const char* kTerrorCorroboration[] = {
    "terrorist_inject", "text_inject", "keyboard_inject", "sigterm_inject",
    "sigkill_inject", "c2_beacon", "impostor_ns", "dns_poison",
    "meterpreter", "lateral_move", "exfil_channel", "route_hook",
    "path_jump", "sleep_then_inject", "compaction_poison",
    // Field Primer: raw scripts on the control plane are a capital offense
    "script_execution", "shell_script", "bash_wrapper", "python_control",
    "shebang_control", "raw_script",
    // Right to life — process-plane softkill / hardkill of our servers
    "pkill", "killall", "kill -9", "kill -term", "kill -term ", "kill -15",
    "sigkill", "sigterm", "sighup", "sigint", "softkill", "soft_kill",
    "soft-kill", "process_wipe", "daemon_wipe", "plane_kill",
    nullptr,
};

// Weapons used to murder Field daemons (right-to-life gate).
inline constexpr const char* kSoftKillWeapons[] = {
    "pkill", "killall", "kill -9", "kill -term", "kill -15", "kill -hup",
    "kill -int", "sigkill", "sigterm", "sighup", "sigint",
    "softkill", "soft_kill", "soft-kill", "process_wipe", "daemon_wipe",
    "plane_kill", "sigkill_inject", "sigterm_inject", "sleep_then_inject",
    nullptr,
};

// Live servers that already exist — kill attempts against these = terror.
inline constexpr const char* kFieldServerLife[] = {
    "field-world-dns", "field-world-dhcp", "field-h7d", "field-h7r",
    "field-fleet-mesh", "field-internet2", "field-internet2-plane",
    "field-elevate", "field-hostess7", "field-ammoos", "field-everyone",
    "field-dns", "field-dhcp", "field-one", "hostess7", "ammonet",
    "ironclad", "nexus-c2", "field-compaction", "field-script-ban",
    nullptr,
};

// Ad / tracker / CDN markers — ServiceCdn or Annoyance, NEVER Terror.
inline constexpr const char* kServiceCdnMarkers[] = {
    "2mdn.net", "adnxs.com", "doubleclick", "googlesyndication",
    "adservice.google", "ads.facebook", "ads-twitter", "ads.twitter",
    "criteo.com", "scorecardresearch", "adrecover", "adblockanalytics",
    "blockadblock", "detectadblock", "disqusads", "taboola", "outbrain",
    "moatads", "pubmatic", "rubiconproject", "openx.net", "casalemedia",
    "advertising.com", "adform.net", "bidswitch", "media.net",
    "amazon-adsystem", "facebook.com/tr", "google-analytics",
    "googletagmanager", "hotjar.com", "segment.io", "mixpanel",
    "newrelic.com", "sentry.io", "cloudflareinsights",
    "ads.", "ad.", "analytics.", "pixel.", "tracker.", "tracking.",
    nullptr,
};

// Field / AmmoNet / Hostess self — never ban, never terror (as the subject).
// Kill *against* these is handled by right-to-life before this hold.
inline constexpr const char* kFieldSelfMarkers[] = {
    "ammonet", "hostess7", "zacharygeurts", "field-one", "field_one",
    "kilroy", "ammoos", "ammocode", "grok16", "127.0.0.1", "::1",
    "ironclad", "nexus-c2", "field-dns", "field-dhcp", "field-world-dns",
    "field-world-dhcp", "field-h7d", "field-fleet-mesh", "field-internet2",
    nullptr,
};

// Foreign model authority claims — Always Zero (out of reason).
inline constexpr const char* kForeignLlmZero[] = {
    "gpt-4", "gpt4", "gpt-3", "chatgpt", "openai", "claude-3",
    "claude-2", "anthropic", "gemini-pro", "bard.google",
    "as an ai language model", "as an AI language model",
    nullptr,
};

inline bool contains_ci(const char* hay, const char* needle) {
  if (!hay || !needle || !needle[0]) return false;
  // ASCII case-insensitive substring
  const size_t nlen = std::strlen(needle);
  for (const char* p = hay; *p; ++p) {
    size_t i = 0;
    for (; i < nlen; ++i) {
      char a = p[i];
      char b = needle[i];
      if (!a) return false;
      if (a >= 'A' && a <= 'Z') a = static_cast<char>(a - 'A' + 'a');
      if (b >= 'A' && b <= 'Z') b = static_cast<char>(b - 'A' + 'a');
      if (a != b) break;
    }
    if (i == nlen) return true;
  }
  return false;
}

inline bool any_marker(const char* hay, const char* const* markers) {
  if (!hay) return false;
  for (int i = 0; markers[i]; ++i) {
    if (contains_ci(hay, markers[i])) return true;
  }
  return false;
}

struct Verdict {
  Class cls;
  int score;               // 0 when Zero / unproven
  bool never_reconnect;    // only true for real terror/threat after gates
  bool terrorist_attack;   // ONLY Class::Terror with corroboration
  bool scrub_false_terror; // was mislabeled terror
  const char* reason;
  const char* vector_out;  // corrected vector label
};

// Core corrective heuristic for AmmoNet whole network.
// subject: domain/ip/device id · vector_in: claimed vector · detail: reason blob
inline Verdict classify(const char* subject, const char* vector_in,
                        const char* detail) {
  Verdict v{};
  v.cls = Class::Zero;
  v.score = 0;
  v.never_reconnect = false;
  v.terrorist_attack = false;
  v.scrub_false_terror = false;
  v.reason = "always_zero_unproven";
  v.vector_out = "ZERO";

  const char* sub = subject ? subject : "";
  const char* vec = vector_in ? vector_in : "";
  const char* det = detail ? detail : "";

  // 0) RIGHT TO LIFE — softkill/hardkill of live Field servers = capital terror
  //    (do this BEFORE FieldSelf hold: "pkill field-world-dns" is attack, not self)
  {
    const bool weapon =
        any_marker(sub, kSoftKillWeapons) || any_marker(vec, kSoftKillWeapons) ||
        any_marker(det, kSoftKillWeapons);
    const bool victim =
        any_marker(sub, kFieldServerLife) || any_marker(det, kFieldServerLife) ||
        any_marker(vec, kFieldServerLife);
    if (weapon && victim) {
      v.cls = Class::Terror;
      v.score = class_score(Class::Terror);
      v.terrorist_attack = true;
      v.never_reconnect = true;
      v.scrub_false_terror = false;
      v.reason = "right_to_life_field_server_kill_capital";
      v.vector_out = "TERRORIST_ATTACK";
      return v;
    }
    // Weapon alone against unspecified plane still capital when kill inject
    if (weapon && (contains_ci(vec, "inject") || contains_ci(det, "inject") ||
                   contains_ci(det, "hostile") || contains_ci(sub, "hostile"))) {
      v.cls = Class::Terror;
      v.score = class_score(Class::Terror);
      v.terrorist_attack = true;
      v.never_reconnect = true;
      v.reason = "right_to_life_softkill_inject_capital";
      v.vector_out = "TERRORIST_ATTACK";
      return v;
    }
  }

  // 1) Field self — never threat (servers serving — hold them, do not ban)
  if (any_marker(sub, kFieldSelfMarkers) || any_marker(det, kFieldSelfMarkers)) {
    v.cls = Class::FieldSelf;
    v.score = 0;
    v.reason = "field_self_hold_right_to_life";
    v.vector_out = "FIELD_SELF";
    return v;
  }

  // 2) Foreign LLM authority — Always Zero (GPT-4 out of reason)
  if (any_marker(sub, kForeignLlmZero) || any_marker(det, kForeignLlmZero) ||
      any_marker(vec, kForeignLlmZero)) {
    v.cls = Class::Zero;
    v.score = 0;
    v.reason = "foreign_llm_out_of_reason_zero";
    v.vector_out = "ZERO";
    return v;
  }

  // 3) Service CDN / ad / tracker — NOT terror
  const bool is_cdn = any_marker(sub, kServiceCdnMarkers) ||
                      any_marker(det, kServiceCdnMarkers);
  const bool claimed_terror =
      contains_ci(vec, "terror") || contains_ci(det, "terrorist_attack") ||
      contains_ci(det, "TERRORIST_ATTACK");

  if (is_cdn) {
    v.cls = Class::ServiceCdn;
    v.score = class_score(Class::ServiceCdn);
    v.never_reconnect = false;  // do not UDP-cook ads as terrorists
    v.terrorist_attack = false;
    if (claimed_terror) {
      v.scrub_false_terror = true;
      v.reason = "scrub_false_terror_ad_cdn_zero_terror_label";
    } else {
      v.reason = "service_cdn_annoyance_not_terror";
    }
    v.vector_out = "SERVICE_CDN";
    return v;
  }

  // 4) Soft / operational vectors alone — not terror (cap to Threat or Zero)
  bool soft_only = false;
  for (int i = 0; kNotTerrorAlone[i]; ++i) {
    if (contains_ci(vec, kNotTerrorAlone[i]) ||
        contains_ci(det, kNotTerrorAlone[i])) {
      soft_only = true;
      break;
    }
  }
  bool corroborated = false;
  for (int i = 0; kTerrorCorroboration[i]; ++i) {
    if (contains_ci(det, kTerrorCorroboration[i]) ||
        contains_ci(vec, kTerrorCorroboration[i]) ||
        contains_ci(sub, kTerrorCorroboration[i])) {
      corroborated = true;
      break;
    }
  }

  if (claimed_terror && !corroborated) {
    // Uncorroborated terror claim → Always Zero terror flag
    v.cls = soft_only ? Class::Annoyance : Class::Zero;
    v.score = soft_only ? class_score(Class::Annoyance) : 0;
    v.scrub_false_terror = true;
    v.terrorist_attack = false;
    v.never_reconnect = false;
    v.reason = "uncorroborated_terror_claim_zeroed";
    v.vector_out = soft_only ? "ANNOYANCE" : "ZERO";
    return v;
  }

  if (claimed_terror && corroborated) {
    v.cls = Class::Terror;
    v.score = class_score(Class::Terror);
    v.terrorist_attack = true;
    v.never_reconnect = true;
    v.reason = "corroborated_terror_field_gate";
    v.vector_out = "TERRORIST_ATTACK";
    return v;
  }

  // 5) URL gone / annoyance without terror claim
  if (contains_ci(vec, "URL_HEURISTIC") || contains_ci(vec, "url_hostile") ||
      contains_ci(det, "url_heuristics_gone")) {
    v.cls = Class::Annoyance;
    v.score = class_score(Class::Annoyance);
    v.reason = "url_annoyance_gone_not_terror";
    v.vector_out = "URL_HEURISTIC_GONE";
    return v;
  }

  // 6) Real threat marks without terror keyword
  if (corroborated) {
    v.cls = Class::Threat;
    v.score = class_score(Class::Threat);
    v.reason = "corroborated_threat_non_terror_class";
    v.vector_out = "THREAT";
    return v;
  }

  // Default: Always Zero
  v.cls = Class::Zero;
  v.score = 0;
  v.reason = "always_zero_default";
  v.vector_out = "ZERO";
  return v;
}

}  // namespace zero
}  // namespace ammonet
}  // namespace field
