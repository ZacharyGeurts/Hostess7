#define _GNU_SOURCE
#include "kgo.h"

#include <errno.h>
#include <getopt.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>
#include <syslog.h>

static volatile sig_atomic_t g_stop = 0;

static void on_signal(int sig)
{
    (void)sig;
    g_stop = 1;
}

static void usage(const char *prog)
{
    fprintf(stderr,
            "Kill Grok Orphans v%s — fast orphan grok process watchdog\n\n"
            "Usage: %s [options]\n"
            "  -c, --config PATH   patterns JSON (default: /etc/kgo/kgo-patterns.json)\n"
            "  -f, --foreground    run in foreground (no daemonize)\n"
            "  -n, --dry-run       scan only, do not kill\n"
            "  -o, --once          single scan then exit\n"
            "  -s, --stats         print scan stats (with --once or --dry-run)\n"
            "  -h, --help          show help\n",
            KGO_VERSION, prog);
}

static int resolve_config(const char *opt, char *out, size_t outlen)
{
    if (opt && opt[0]) {
        snprintf(out, outlen, "%s", opt);
        return 0;
    }
    const char *env = getenv("KGO_CONFIG");
    if (env && env[0]) {
        snprintf(out, outlen, "%s", env);
        return 0;
    }
    snprintf(out, outlen, "/etc/kgo/kgo-patterns.json");
    return 0;
}

static int daemonize(void)
{
    pid_t pid = fork();
    if (pid < 0)
        return -1;
    if (pid > 0)
        _exit(0);
    if (setsid() < 0)
        return -1;
    pid = fork();
    if (pid < 0)
        return -1;
    if (pid > 0)
        _exit(0);
    chdir("/");
    umask(027);
    close(STDIN_FILENO);
    close(STDOUT_FILENO);
    close(STDERR_FILENO);
    return 0;
}

static int run_scan(const kgo_config_t *cfg, int grace_sec, bool dry_run, bool show_stats)
{
    kgo_target_t targets[256];
    size_t found = 0;
    kgo_scan_stats_t stats;
    memset(&stats, 0, sizeof(stats));

    if (kgo_scan_orphans(cfg, targets, 256, &found, &stats) != 0)
        return -1;

    int killed = 0;
    for (size_t i = 0; i < found; i++) {
        if (dry_run) {
            printf("orphan pid=%d ppid=%d reason=%s cmd=%s\n",
                   (int)targets[i].pid, (int)targets[i].ppid,
                   targets[i].reason, targets[i].cmdline);
            continue;
        }
        if (kgo_kill_target(&targets[i], grace_sec) == 0) {
            killed++;
            stats.killed++;
        }
    }

    if (show_stats) {
        printf("stats scanned=%u orphan_checked=%u matched=%u killed=%u\n",
               stats.scanned, stats.orphan_checked, stats.matched, stats.killed);
    }

    return (int)found;
}

int main(int argc, char **argv)
{
    const char *config_opt = NULL;
    bool foreground = false;
    bool dry_run = false;
    bool once = false;
    bool show_stats = false;

    static struct option long_opts[] = {
        {"config", required_argument, 0, 'c'},
        {"foreground", no_argument, 0, 'f'},
        {"dry-run", no_argument, 0, 'n'},
        {"once", no_argument, 0, 'o'},
        {"stats", no_argument, 0, 's'},
        {"help", no_argument, 0, 'h'},
        {0, 0, 0, 0}
    };

    int ch;
    while ((ch = getopt_long(argc, argv, "c:fnosh", long_opts, NULL)) != -1) {
        switch (ch) {
        case 'c': config_opt = optarg; break;
        case 'f': foreground = true; break;
        case 'n': dry_run = true; break;
        case 'o': once = true; break;
        case 's': show_stats = true; break;
        case 'h': usage(argv[0]); return 0;
        default: usage(argv[0]); return 1;
        }
    }

    char config_path[512];
    resolve_config(config_opt, config_path, sizeof(config_path));

    kgo_config_t cfg;
    if (kgo_load_config(config_path, &cfg) != 0) {
        fprintf(stderr, "kgo: cannot load config %s\n", config_path);
        return 1;
    }

    if (!foreground && !dry_run && !once) {
        if (daemonize() != 0) {
            fprintf(stderr, "kgo: daemonize failed\n");
            return 1;
        }
    }

    if (!dry_run || !foreground)
        openlog("kgo", LOG_PID | LOG_CONS, LOG_DAEMON);

    kgo_log(LOG_INFO,
            "Kill Grok Orphans v%s started (patterns=%zu interval=%ds grace=%ds min_age=%ds)",
            KGO_VERSION, cfg.pattern_count, cfg.interval_sec, cfg.grace_sec,
            cfg.min_age_sec);

    signal(SIGTERM, on_signal);
    signal(SIGINT, on_signal);

    do {
        int n = run_scan(&cfg, cfg.grace_sec, dry_run, show_stats && (once || dry_run));
        if (n < 0) {
            kgo_log(LOG_ERR, "scan failed");
            if (once)
                return 1;
        } else if (n > 0) {
            kgo_log(LOG_NOTICE, "scan found %d orphan(s)", n);
        }
        if (once)
            break;
        for (int i = 0; i < cfg.interval_sec && !g_stop; i++)
            sleep(1);
    } while (!g_stop);

    kgo_log(LOG_INFO, "kgo stopped");
    closelog();
    return 0;
}