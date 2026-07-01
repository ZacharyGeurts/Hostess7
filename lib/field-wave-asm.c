/*
 * field-wave-asm — field-fast RTL-SDR USB probe (direct sysfs, no lsusb).
 * NEXUS Field Wave: no shell deps for dongle detect. Field-fast.
 *
 * Build: gcc -O2 -pipe -fstack-protector-strong -D_FORTIFY_SOURCE=2 \
 *          -o field-wave-asm field-wave-asm.c
 *
 * Usage: field-wave-asm probe
 */
#define _GNU_SOURCE
#include <dirent.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

#define RTL_VID "0bda"
#define RTL_PID_2838 "2838"
#define RTL_PID_2832 "2832"
#define LINE_SZ 64

static int read_trim(const char *path, char *out, size_t out_sz) {
    FILE *f = fopen(path, "r");
    if (!f) return -1;
    if (!fgets(out, (int)out_sz, f)) {
        fclose(f);
        return -1;
    }
    fclose(f);
    size_t n = strlen(out);
    while (n > 0 && (out[n - 1] == '\n' || out[n - 1] == '\r' || out[n - 1] == ' ')) {
        out[--n] = '\0';
    }
    return 0;
}

static int is_rtl_pair(const char *vid, const char *pid) {
    if (strcmp(vid, RTL_VID) != 0) return 0;
    return strcmp(pid, RTL_PID_2838) == 0 || strcmp(pid, RTL_PID_2832) == 0;
}

static int mode_probe(void) {
    DIR *dir = opendir("/sys/bus/usb/devices");
    if (!dir) {
        printf("{\"ok\":false,\"dongle_present\":false,\"engine\":\"asm\",\"error\":\"sysfs_unavailable\"}\n");
        return 1;
    }
    struct dirent *ent;
    char vpath[256], ppath[256], vid[LINE_SZ], pid[LINE_SZ];
    int found = 0;
    char found_vid[LINE_SZ] = "";
    char found_pid[LINE_SZ] = "";

    while ((ent = readdir(dir)) != NULL) {
        if (ent->d_name[0] == '.') continue;
        snprintf(vpath, sizeof(vpath), "/sys/bus/usb/devices/%s/idVendor", ent->d_name);
        snprintf(ppath, sizeof(ppath), "/sys/bus/usb/devices/%s/idProduct", ent->d_name);
        if (read_trim(vpath, vid, sizeof(vid)) < 0) continue;
        if (read_trim(ppath, pid, sizeof(pid)) < 0) continue;
        if (is_rtl_pair(vid, pid)) {
            found = 1;
            strncpy(found_vid, vid, sizeof(found_vid) - 1);
            strncpy(found_pid, pid, sizeof(found_pid) - 1);
            break;
        }
    }
    closedir(dir);

    if (found) {
        printf(
            "{\"ok\":true,\"dongle_present\":true,\"vendor_id\":\"%s\",\"product_id\":\"%s\","
            "\"usb_id\":\"%s:%s\",\"engine\":\"asm\"}\n",
            found_vid, found_pid, found_vid, found_pid);
        return 0;
    }
    printf("{\"ok\":true,\"dongle_present\":false,\"engine\":\"asm\"}\n");
    return 0;
}

int main(int argc, char **argv) {
    const char *mode = (argc > 1) ? argv[1] : "probe";
    if (strcmp(mode, "probe") == 0) return mode_probe();
    printf("{\"ok\":false,\"error\":\"usage: field-wave-asm probe\",\"engine\":\"asm\"}\n");
    return 1;
}