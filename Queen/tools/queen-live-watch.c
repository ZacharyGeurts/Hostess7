/* queen-live-watch — field-compiled forge log tail + stall detector
 * Writes data/queen-live-watch.json and refreshes gui/queen-live-build.html
 * Copyright (C) 2026 Zachary Geurts — GPLv3
 */
#define _GNU_SOURCE
#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>

static volatile sig_atomic_t g_stop;

static void on_sig(int sig) { (void)sig; g_stop = 1; }

static long file_size(const char *path)
{
    struct stat st;
    if (stat(path, &st) != 0)
        return -1;
    return (long)st.st_size;
}

static int tail_lines(const char *path, char *out, size_t out_sz, int max_lines)
{
    FILE *f;
    char buf[8192];
    char lines[32][512];
    int count = 0, i, start;
    size_t pos = 0;

    if (!out || out_sz < 2)
        return -1;
    out[0] = '\0';
    f = fopen(path, "r");
    if (!f)
        return -1;
    while (fgets(buf, sizeof buf, f)) {
        size_t n = strlen(buf);
        while (n > 0 && (buf[n - 1] == '\n' || buf[n - 1] == '\r'))
            buf[--n] = '\0';
        snprintf(lines[count % 32], sizeof lines[0], "%s", buf);
        count++;
    }
    fclose(f);
    start = count > max_lines ? count - max_lines : 0;
    for (i = start; i < count; i++) {
        size_t ln = strlen(lines[i % 32]);
        if (pos + ln + 2 >= out_sz)
            break;
        memcpy(out + pos, lines[i % 32], ln);
        pos += ln;
        out[pos++] = '\n';
    }
    out[pos] = '\0';
    return 0;
}

static int contains(const char *hay, const char *needle)
{
    return hay && needle && strstr(hay, needle) != NULL;
}

static void write_json(const char *json_path, const char *status, long bytes, long delta,
                       int stall, int hangups, const char *tail)
{
    FILE *f = fopen(json_path, "w");
    if (!f)
        return;
    fprintf(f,
            "{\n"
            "  \"schema\": \"queen-live-watch/v1\",\n"
            "  \"updated\": \"%ld\",\n"
            "  \"status\": \"%s\",\n"
            "  \"bytes\": %ld,\n"
            "  \"delta\": %ld,\n"
            "  \"stall_count\": %d,\n"
            "  \"hangup_count\": %d,\n"
            "  \"tail\": ",
            (long)time(NULL), status, bytes, delta, stall, hangups);
    fputc('"', f);
    if (tail) {
        for (const char *p = tail; *p; p++) {
            if (*p == '"' || *p == '\\')
                fputc('\\', f);
            if (*p == '\n')
                fputs("\\n", f);
            else if (*p != '\r')
                fputc(*p, f);
        }
    }
    fprintf(f, "\"\n}\n");
    fclose(f);
}

static void write_html(const char *html_path, const char *json_path, const char *log_path)
{
    FILE *f = fopen(html_path, "w");
    if (!f)
        return;
    fprintf(f,
            "<!DOCTYPE html><html><head><meta charset=utf-8>\n"
            "<meta http-equiv=\"refresh\" content=\"3\">\n"
            "<title>Queen Live Build</title>\n"
            "<style>"
            "body{font-family:ui-monospace,monospace;background:#0a0e14;color:#c8d0e0;"
            "margin:0;padding:1rem}h1{color:#6ee7b7;font-size:1.1rem}"
            ".ok{color:#6ee7b7}.warn{color:#fbbf24}.bad{color:#f87171}"
            "pre{background:#111827;padding:1rem;border-radius:8px;overflow:auto;"
            "max-height:70vh;white-space:pre-wrap;font-size:12px}"
            ".meta{opacity:.75;font-size:12px;margin:.5rem 0}"
            "</style></head><body>\n"
            "<h1>Queen Live Build — g16 field watch</h1>\n"
            "<p class=meta>Log: %s · JSON: %s · auto-refresh 3s</p>\n"
            "<p>Open this file in your browser while the build runs.</p>\n"
            "<div id=s>Loading…</div><pre id=t></pre>\n"
            "<script>\n"
            "fetch('%s?'+Date.now()).then(r=>r.json()).then(d=>{\n"
            "  const s=document.getElementById('s');\n"
            "  const cls=d.status&&d.status.indexOf('HANGUP')>=0?'bad':"
            "(d.status&&d.status.indexOf('STALL')>=0?'warn':'ok');\n"
            "  s.innerHTML='<span class='+cls+'>'+d.status+'</span> · bytes='+d.bytes"
            "+' stall='+d.stall_count+' hangups='+d.hangup_count;\n"
            "  document.getElementById('t').textContent=d.tail||'';\n"
            "}).catch(e=>{document.getElementById('s').textContent='waiting…';});\n"
            "</script></body></html>\n",
            log_path, json_path, json_path);
    fclose(f);
}

static void usage(const char *argv0)
{
    fprintf(stderr,
            "Usage: %s [log_path] [interval_sec]\n"
            "  QUEEN_ROOT  — repo root (default: parent of tools/)\n"
            "  Writes data/queen-live-watch.json + gui/queen-live-build.html\n",
            argv0);
}

int main(int argc, char **argv)
{
    const char *queen_root;
    char log_path[4096], json_path[4096], html_path[4096], tail[12000];
    char queen_buf[4096];
    int interval = 5, stall = 0, hangups = 0, tick = 0;
    long last_size = -1, bytes, delta;
    const char *status = "STARTING";

    signal(SIGINT, on_sig);
    signal(SIGTERM, on_sig);

    queen_root = getenv("QUEEN_ROOT");
    if (!queen_root || !*queen_root) {
        if (realpath("../", queen_buf))
            queen_root = queen_buf;
        else
            queen_root = "..";
    }
    snprintf(log_path, sizeof log_path, "%s/.queen-forge.log", queen_root);
    if (argc >= 2 && argv[1][0] != '-')
        snprintf(log_path, sizeof log_path, "%s", argv[1]);
    if (argc >= 3)
        interval = atoi(argv[2]);
    if (interval < 1)
        interval = 5;

    snprintf(json_path, sizeof json_path, "%s/data/queen-live-watch.json", queen_root);
    snprintf(html_path, sizeof html_path, "%s/gui/queen-live-build.html", queen_root);

    fprintf(stderr, "queen-live-watch: log=%s interval=%ds\n", log_path, interval);
    fprintf(stderr, "  dashboard: file://%s\n", html_path);

    while (!g_stop) {
        bytes = file_size(log_path);
        if (bytes < 0)
            bytes = 0;
        delta = last_size >= 0 ? bytes - last_size : bytes;
        tail_lines(log_path, tail, sizeof tail, 18);

        if (contains(tail, "QUEEN BINARY READY") || contains(tail, "live_build_field OK")) {
            status = "COMPLETE";
            stall = 0;
        } else if (contains(tail, "ok=False") || contains(tail, "compile failed") ||
                   contains(tail, "CMake Error")) {
            status = "FAILED";
        } else if (last_size >= 0 && delta == 0) {
            stall++;
            if (stall >= 3) {
                hangups++;
                status = "HANGUP";
            } else {
                status = "STALL";
            }
        } else {
            stall = 0;
            status = delta > 0 ? "PROGRESS" : "WAITING";
        }

        tick++;
        printf("[%d] %s bytes=%ld delta=%ld stall=%d hangups=%d\n",
               tick, status, bytes, delta, stall, hangups);
        fflush(stdout);

        write_json(json_path, status, bytes, delta, stall, hangups, tail);
        write_html(html_path, json_path, log_path);

        if (strcmp(status, "COMPLETE") == 0 || strcmp(status, "FAILED") == 0)
            break;
        last_size = bytes;
        for (int s = 0; s < interval && !g_stop; s++)
            sleep(1);
    }

    return strcmp(status, "COMPLETE") == 0 ? 0 : 1;
}