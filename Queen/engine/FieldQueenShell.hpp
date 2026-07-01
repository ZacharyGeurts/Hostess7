#pragma once
// Queen Browser 2026 — sovereign shell (SDL3 · Webbrowser default · optional RTX legacy)

#include <SDL3/SDL.h>

#include <atomic>
#include <cstdint>
#include <string>

namespace FieldQueenShell {

struct Theme {
    float void_r = 0.02f, void_g = 0.025f, void_b = 0.04f;
    float aqua_r = 0.18f, aqua_g = 0.72f, aqua_b = 0.88f;
    float rose_r = 0.92f, rose_g = 0.28f, rose_b = 0.55f;
};

struct BootState {
    std::atomic<float> sealed_time{0.f};
    std::atomic<float> load_progress{0.f};
    std::atomic<bool> boot_done{false};
};

bool init(SDL_Window** outWindow, SDL_Renderer** outRenderer) noexcept;
void shutdown(SDL_Window* window, SDL_Renderer* renderer) noexcept;
void renderBootFrame(SDL_Renderer* renderer, const BootState& boot, const Theme& theme,
                     int w, int h) noexcept;
bool pickEngine(std::string& binary, std::string& engine_id) noexcept;
bool launchEngine(const std::string& binary, const char* url) noexcept;
void pumpBoot(SDL_Renderer* renderer, BootState& boot, const Theme& theme,
              int w, int h, float dt) noexcept;

} // namespace FieldQueenShell