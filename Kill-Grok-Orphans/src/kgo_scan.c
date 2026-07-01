#define _GNU_SOURCE
#include "kgo.h"

#include <ctype.h>
#include <dirent.h>
#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <fcntl.h>
#include <sys/types.h>
#include <unistd.h>
#include <stdarg.h>
#include <syslog.h>

static pid_t g_self_pid;

static int read_cmdline_fast(pid_t pid, char *buf, size_t buflen)
{
    char path[64];
    snprintf(path, sizeof(path), "/proc/%d/cmdline", (int)pid);
    int fd = open(path, O_RDONLY | O_CLOEXEC);
    if (fd < 0)
        return -1;
    ssize_t n = read(fd, buf, buflen - 1);
    close(fd);
    if (n <= 0)
        return -1;
    for (ssize_t i = 0; i < n; i++)
        if (buf[i] == '\0')
            buf[i] = ' ';
    buf[n] = '\0';
    while (n > 0 && isspace((unsigned char)buf[n - 1]))
        buf[--n] = '\0';
    return (int)n;
}

static int read_ppid_fast(pid_t pid, pid_t *ppid_out)
{
    char path[64];
    char line[384];
    snprintf(path, sizeof(path), "/proc/%d/stat", (int)pid);
    int fd = open(path, O_RDONLY | O_CLOEXEC);
    if (fd < 0)
        return -1;
    ssize_t n = read(fd, line, sizeof(line) - 1);
    close(fd);
    if (n <= 0)
        return -1;
    line[n] = '\0';
    char *rp = strrchr(line, ')');
    if (!rp)
        return -1;
    rp++;
    long ppid = 0;
    if (sscanf(rp, " %*c %ld", &ppid) != 1)
        return -1;
    *ppid_out = (pid_t)ppid;
    return 0;
}

static int read_age_sec(pid_t pid)
{
    char path[64];
    char line[512];
    snprintf(path, sizeof(path), "/proc/%d/stat", (int)pid);
    int fd = open(path, O_RDONLY | O_CLOEXEC);
    if (fd < 0)
        return -1;
    ssize_t n = read(fd, line, sizeof(line) - 1);
    close(fd);
    if (n <= 0)
        return -1;
    line[n] = '\0';
    char *rp = strrchr(line, ')');
    if (!rp)
        return -1;
    char *p = rp + 2;
    unsigned long fields[20];
    int count = 0;
    while (count < 20 && *p) {
        while (*p == ' ')
            p++;
        if (!*p)
            break;
        fields[count++] = strtoul(p, &p, 10);
    }
    if (count < 20)
        return -1;
    unsigned long starttime = fields[19];
    unsigned long clk_tck = (unsigned long)sysconf(_SC_CLK_TCK);
    if (clk_tck == 0)
        return -1;
    FILE *f = fopen("/proc/uptime", "r");
    if (!f)
        return -1;
    double up = 0.0;
    if (fscanf(f, "%lf", &up) != 1) {
        fclose(f);
        return -1;
    }
    fclose(f);
    long age = (long)(unsigned long)up - (long)(starttime / clk_tck);
    return age < 0 ? 0 : (int)age;
}

bool kgo_is_orphan_ppid(pid_t ppid)
{
    return ppid == 1;
}

static bool is_shell_cmd(const char *cmdline)
{
    return strstr(cmdline, "bash") != NULL
        || strstr(cmdline, "/sh ") != NULL
        || strstr(cmdline, "/sh\0") != NULL
        || strstr(cmdline, "dash") != NULL
        || strstr(cmdline, "zsh") != NULL;
}

bool kgo_match_target(const kgo_config_t *cfg, pid_t pid, pid_t ppid,
                      const char *cmdline, kgo_target_t *out)
{
    if (!kgo_is_orphan_ppid(ppid))
        return false;
    if (pid <= 1)
        return false;
    if (g_self_pid == 0)
        g_self_pid = getpid();
    if (g_self_pid == pid)
        return false;

    for (size_t i = 0; i < cfg->pattern_count; i++) {
        const kgo_pattern_t *p = &cfg->patterns[i];
        if (!strstr(cmdline, p->match))
            continue;
        if (p->shell_only && !is_shell_cmd(cmdline))
            continue;
        memset(out, 0, sizeof(*out));
        out->pid = pid;
        out->ppid = ppid;
        snprintf(out->cmdline, sizeof(out->cmdline), "%s", cmdline);
        snprintf(out->reason, sizeof(out->reason), "%s", p->reason);
        return true;
    }
    return false;
}

int kgo_scan_orphans(const kgo_config_t *cfg, kgo_target_t *out,
                     size_t max_out, size_t *found, kgo_scan_stats_t *stats)
{
    DIR *d = opendir("/proc");
    if (!d)
        return -1;

    if (g_self_pid == 0)
        g_self_pid = getpid();

    size_t n = 0;
    struct dirent *ent;
    char cmdbuf[KGO_CMDLINE_SCAN];

    while ((ent = readdir(d)) != NULL && n < max_out) {
        if (ent->d_type != DT_UNKNOWN && ent->d_type != DT_DIR)
            continue;
        const char *name = ent->d_name;
        if (!isdigit((unsigned char)name[0]))
            continue;
        if (stats)
            stats->scanned++;

        pid_t pid = (pid_t)atoi(name);
        if (pid <= 1 || pid == g_self_pid)
            continue;

        pid_t ppid = 0;
        if (read_ppid_fast(pid, &ppid) != 0)
            continue;
        if (!kgo_is_orphan_ppid(ppid))
            continue;
        if (stats)
            stats->orphan_checked++;

        if (cfg->min_age_sec > 0) {
            int age = read_age_sec(pid);
            if (age >= 0 && age < cfg->min_age_sec)
                continue;
        }

        if (read_cmdline_fast(pid, cmdbuf, sizeof(cmdbuf)) <= 0)
            continue;

        kgo_target_t t;
        if (!kgo_match_target(cfg, pid, ppid, cmdbuf, &t))
            continue;

        if (stats)
            stats->matched++;
        out[n++] = t;
    }
    closedir(d);
    *found = n;
    return 0;
}

int kgo_kill_target(const kgo_target_t *target, int grace_sec)
{
    if (kill(target->pid, 0) != 0)
        return -1;

    kgo_log(LOG_WARNING, "killing orphan pid=%d ppid=%d reason=%s cmd=%s",
            (int)target->pid, (int)target->ppid, target->reason, target->cmdline);

    if (kill(target->pid, SIGTERM) != 0)
        return -1;

    for (int i = 0; i < grace_sec * 20; i++) {
        if (kill(target->pid, 0) != 0)
            return 0;
        usleep(50000);
    }

    if (kill(target->pid, SIGKILL) == 0)
        kgo_log(LOG_WARNING, "SIGKILL pid=%d", (int)target->pid);
    return 0;
}

void kgo_log(int priority, const char *fmt, ...)
{
    va_list ap;
    va_start(ap, fmt);
    vsyslog(priority, fmt, ap);
    va_end(ap);
}