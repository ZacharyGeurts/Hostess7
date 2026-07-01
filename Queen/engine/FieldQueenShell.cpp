#include "FieldQueenShell.hpp"

#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <filesystem>
#include <string>
#include <vector>

namespace {

std::filesystem::path queenRoot() noexcept {
    const char* env = std::getenv("QUEEN_ROOT");
    if (env && env[0]) return std::filesystem::path(env);
    return std::filesystem::current_path();
}

bool existsBin(const std::string& name) noexcept {
    for (const auto& dir : {"/usr/local/bin", "/usr/bin"}) {
        const auto p = std::filesystem::path(dir) / name;
        if (std::filesystem::exists(p)) return true;
    }
    return false;
}

} // namespace

namespace FieldQueenShell {

bool init(SDL_Window** outWindow, SDL_Renderer** outRenderer) noexcept {
    if (!SDL_Init(SDL_INIT_VIDEO | SDL_INIT_EVENTS)) {
        std::fprintf(stderr, "[Queen] SDL_Init: %s\n", SDL_GetError());
        return false;
    }
    SDL_Window* win = SDL_CreateWindow("Queen Browser", 1440, 900, SDL_WINDOW_RESIZABLE);
    if (!win) {
        std::fprintf(stderr, "[Queen] SDL_CreateWindow: %s\n", SDL_GetError());
        return false;
    }
    SDL_Renderer* ren = SDL_CreateRenderer(win, nullptr);
    if (!ren) {
        std::fprintf(stderr, "[Queen] SDL_CreateRenderer: %s\n", SDL_GetError());
        SDL_DestroyWindow(win);
        return false;
    }
    *outWindow = win;
    *outRenderer = ren;
    return true;
}

void shutdown(SDL_Window* window, SDL_Renderer* renderer) noexcept {
    if (renderer) SDL_DestroyRenderer(renderer);
    if (window) SDL_DestroyWindow(window);
    SDL_Quit();
}

void renderBootFrame(SDL_Renderer* renderer, const BootState& boot, const Theme& theme,
                     int w, int h) noexcept {
    (void)boot;
    (void)w;
    (void)h;
    SDL_SetRenderDrawColor(renderer,
        static_cast<Uint8>(theme.void_r * 255),
        static_cast<Uint8>(theme.void_g * 255),
        static_cast<Uint8>(theme.void_b * 255), 255);
    SDL_RenderClear(renderer);
    SDL_RenderPresent(renderer);
}

bool pickEngine(std::string& binary, std::string& engine_id) noexcept {
    const auto root = queenRoot();
    const std::vector<std::pair<std::string, std::string>> candidates = {
        {root.string() + "/vendor/ladybird/Build/release/bin/Ladybird", "ladybird"},
        {root.string() + "/vendor/ladybird/build/bin/Ladybird", "ladybird"},
        {root.string() + "/build/servo/servo", "servo"},
        {root.string() + "/build/rtx/bin/Linux/queen-browser", "queen-browser"},
        {root.string() + "/field-gecko/bin/queen-browser", "queen-field-engine"},
        {root.string() + "/build/field-gecko/bin/queen-browser", "queen-field-engine"},
        {"queen-browser", "queen-browser"},
        {"queen-field-engine", "queen-field-engine"},
        {"field-queen", "field-queen"},
    };
    for (const auto& [path, id] : candidates) {
        if (path.find('/') != std::string::npos) {
            if (std::filesystem::exists(path)) {
                binary = path;
                engine_id = id;
                return true;
            }
        } else if (existsBin(path)) {
            binary = path;
            engine_id = id;
            return true;
        }
    }
    return false;
}

bool launchEngine(const std::string& binary, const char* url) noexcept {
    if (binary.empty() || !url) return false;
    std::string cmd;
    if (binary.find('/') != std::string::npos) {
        cmd = "\"" + binary + "\" \"" + url + "\" &";
    } else {
        const char* queen = std::getenv("QUEEN_ROOT");
        std::string launcher;
        if (queen) {
            launcher = std::string(queen) + "/field-gecko/bin/launch-field-gecko.sh";
            if (std::filesystem::exists(launcher)) {
                cmd = "QUEEN_ROOT=\"" + std::string(queen) + "\" \"" + launcher + "\" \"" +
                      url + "\" &";
                return std::system(cmd.c_str()) == 0;
            }
        }
        cmd = binary + " --new-window \"" + url + "\" &";
    }
    std::fprintf(stderr, "[Queen] launch: %s\n", cmd.c_str());
    return std::system(cmd.c_str()) == 0;
}

void pumpBoot(SDL_Renderer* renderer, BootState& boot, const Theme& theme,
              int w, int h, float dt) noexcept {
    (void)dt;
    boot.load_progress.store(1.f);
    boot.boot_done.store(true);
    renderBootFrame(renderer, boot, theme, w, h);
}

} // namespace FieldQueenShell