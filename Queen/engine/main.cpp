// Legacy SDL-only launcher — superseded by queen-main.cpp + AMOURANTHRTX RTX exe.
// Use ../build/rtx/bin/Linux/queen-browser for full in-engine UI + RTX goodies.
#include "FieldQueenShell.hpp"

#include <cstdio>
#include <cstdlib>
#include <string>

int main(int argc, char** argv) {
    const char* rtx = std::getenv("QUEEN_RTX_BINARY");
    if (!rtx || !rtx[0])
        rtx = "../build/rtx/bin/Linux/queen-browser";
    if (argc > 0) {
        std::string cmd = "NEXUS_INSTALL_ROOT=\"";
        cmd += (std::getenv("NEXUS_INSTALL_ROOT") ? std::getenv("NEXUS_INSTALL_ROOT") : "..");
        cmd += "\" \"";
        cmd += rtx;
        cmd += "\" --queen --extended-field";
        for (int i = 1; i < argc; ++i)
            if (argv[i] && argv[i][0]) { cmd += " \""; cmd += argv[i]; cmd += "\""; }
        cmd += " &";
        std::fprintf(stderr, "[Queen] delegating to RTX exe: %s\n", cmd.c_str());
        return std::system(cmd.c_str()) == 0 ? 0 : 1;
    }
    return 1;
}