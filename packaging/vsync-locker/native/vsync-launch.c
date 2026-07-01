/* VSYNC-Locker native launcher — Grok16-built stub; exec python guard in install root. */
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#ifndef VSYNC_VERSION
#define VSYNC_VERSION "1.0.0"
#endif

static int launch_python(const char *root) {
    char script[PATH_MAX];
    snprintf(script, sizeof(script), "%s/lib/field-vsync-locker.py", root);
    if (access(script, R_OK) != 0) {
        fprintf(stderr, "vsync-launch: missing %s\n", script);
        return 1;
    }
    execlp("python3", "python3", script, "guard", "--quiet", (char *)NULL);
    fprintf(stderr, "vsync-launch: python3 exec failed\n");
    return 1;
}

int main(int argc, char **argv) {
    (void)argc;
    const char *root = getenv("NEXUS_INSTALL_ROOT");
    if (!root || !*root) {
        char self[PATH_MAX];
        ssize_t n = readlink("/proc/self/exe", self, sizeof(self) - 1);
        if (n > 0) {
            self[n] = '\0';
            char *slash = strrchr(self, '/');
            if (slash) {
                *slash = '\0';
                slash = strrchr(self, '/');
                if (slash) {
                    *slash = '\0';
                    root = self;
                }
            }
        }
    }
    if (!root || !*root) {
        root = ".";
    }
    setenv("NEXUS_INSTALL_ROOT", root, 1);
    return launch_python(root);
}