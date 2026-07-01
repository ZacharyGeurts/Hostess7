// Queen Browser — single RTX executable entry (AMOURANTHRTX navigator_main)
#include "Navigator.hpp"
#include "engine/FieldQueenBrowser.hpp"

#include <cstdlib>
#include <filesystem>
#include <string>
#include <vector>

namespace {

void setDefaultEnv(const char* key, const std::string& value) {
    if (!std::getenv(key) || !std::getenv(key)[0])
        setenv(key, value.c_str(), 1);
}

std::string detectSgRoot() {
    if (const char* v = std::getenv("SG_ROOT"); v && v[0]) return v;
    std::error_code ec;
    auto queen = std::filesystem::path(__FILE__).parent_path().parent_path();
    auto sg = queen.parent_path().parent_path();
    if (std::filesystem::exists(sg / "KILROY", ec))
        return sg.string();
    if (std::filesystem::exists(sg / "Queen", ec) || std::filesystem::exists(sg / "NewLatest", ec))
        return sg.string();
    return "/home/default/Desktop/SG";
}

std::string detectQueenRoot(const std::string& sg) {
    if (const char* v = std::getenv("QUEEN_ROOT"); v && v[0]) return v;
    std::error_code ec;
    const std::vector<std::filesystem::path> candidates = {
        std::filesystem::path(sg) / "Queen",
        std::filesystem::path(sg) / "NewLatest" / "Queen",
    };
    for (const auto& c : candidates) {
        if (std::filesystem::exists(c / "world", ec) || std::filesystem::exists(c / "lib", ec))
            return c.string();
    }
    return (std::filesystem::path(sg) / "Queen").string();
}

std::string detectInstallRoot(const std::string& sg, const std::string& queen) {
    if (const char* v = std::getenv("NEXUS_INSTALL_ROOT"); v && v[0]) return v;
    std::error_code ec;
    const auto nested = std::filesystem::path(sg) / "NewLatest";
    if (std::filesystem::exists(nested / "lib", ec))
        return nested.string();
    if (std::filesystem::exists(std::filesystem::path(queen).parent_path() / "lib", ec))
        return std::filesystem::path(queen).parent_path().string();
    return queen;
}

} // namespace

int main(int argc, char* argv[]) {
    FieldQueenBrowser::enableSovereignMode();
    FieldQueenSovereign::enableFieldRtxSovereign();
    setenv("NEXUS_PANEL_AUTO_OPEN", "1", 1);
    setenv("QUEEN_FIELD_GPU", "1", 1);
    setenv("QUEEN_AUTO_BOOT", "1", 1);
    setenv("QUEEN_WORLD_AUTO_BOOT", "1", 1);
    setenv("QUEEN_INSTANT_BROWSER", "1", 1);
    setenv("NEXUS_EMBED_PANEL_IN_ENGINE", "0", 1);
    setenv("NEXUS_FIELD_BROWSER_QUEEN", "1", 1);
    setDefaultEnv("QUEEN_DISPLAY_REFRESH", "120");

    const std::string sg = detectSgRoot();
    const std::string queen = detectQueenRoot(sg);
    const std::string install = detectInstallRoot(sg, queen);
    const std::string kilroy = sg + "/KILROY";
    const std::string rtx = sg + "/AMOURANTHRTX";
    const std::string g16 = sg + "/Grok16";

    setDefaultEnv("SG_ROOT", sg);
    setDefaultEnv("NEXUS_INSTALL_ROOT", install);
    setDefaultEnv("QUEEN_ROOT", queen);
    setDefaultEnv("GROK16_ROOT", g16);
    setDefaultEnv("KILROY_ROOT", kilroy);
    setDefaultEnv("AMOURANTHRTX_ROOT", rtx);
    setDefaultEnv("HOSTESS7_ROOT", sg + "/Hostess7");

    FieldQueenBrowser::parseArgvQueen(argc, argv);
    return navigator_main(argc, argv);
}