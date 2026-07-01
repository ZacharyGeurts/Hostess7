#include "kgo.h"

#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static char *read_file(const char *path, size_t *len_out)
{
    FILE *f = fopen(path, "r");
    if (!f)
        return NULL;
    if (fseek(f, 0, SEEK_END) != 0) {
        fclose(f);
        return NULL;
    }
    long sz = ftell(f);
    if (sz < 0) {
        fclose(f);
        return NULL;
    }
    rewind(f);
    char *buf = malloc((size_t)sz + 1);
    if (!buf) {
        fclose(f);
        return NULL;
    }
    size_t n = fread(buf, 1, (size_t)sz, f);
    fclose(f);
    buf[n] = '\0';
    *len_out = n;
    return buf;
}

static const char *json_str(const char *obj, const char *key, char *out, size_t outlen)
{
    char needle[128];
    snprintf(needle, sizeof(needle), "\"%s\"", key);
    const char *p = strstr(obj, needle);
    if (!p)
        return NULL;
    p = strchr(p + strlen(needle), '"');
    if (!p)
        return NULL;
    p++;
    const char *end = strchr(p, '"');
    if (!end)
        return NULL;
    size_t n = (size_t)(end - p);
    if (n >= outlen)
        n = outlen - 1;
    memcpy(out, p, n);
    out[n] = '\0';
    return out;
}

static int json_int(const char *json, const char *key, int fallback)
{
    char needle[128];
    snprintf(needle, sizeof(needle), "\"%s\"", key);
    const char *p = strstr(json, needle);
    if (!p)
        return fallback;
    p = strchr(p, ':');
    if (!p)
        return fallback;
    return atoi(p + 1);
}

static bool json_bool_in_obj(const char *obj, const char *key)
{
    char needle[64];
    snprintf(needle, sizeof(needle), "\"%s\"", key);
    const char *p = strstr(obj, needle);
    if (!p)
        return false;
    p = strchr(p, ':');
    if (!p)
        return false;
    while (*++p && isspace((unsigned char)*p))
        ;
    return strncmp(p, "true", 4) == 0;
}

int kgo_load_config(const char *path, kgo_config_t *cfg)
{
    memset(cfg, 0, sizeof(*cfg));
    cfg->interval_sec = 3;
    cfg->grace_sec = 2;
    cfg->min_age_sec = 1;

    size_t len = 0;
    char *json = read_file(path, &len);
    if (!json)
        return -1;

    cfg->interval_sec = json_int(json, "interval_sec", cfg->interval_sec);
    cfg->grace_sec = json_int(json, "grace_sec", cfg->grace_sec);
    cfg->min_age_sec = json_int(json, "min_age_sec", cfg->min_age_sec);

    const char *arr = strstr(json, "\"patterns\"");
    if (!arr) {
        free(json);
        return -1;
    }
    arr = strchr(arr, '[');
    if (!arr) {
        free(json);
        return -1;
    }

    const char *obj = arr;
    while (cfg->pattern_count < KGO_MAX_PATTERNS) {
        obj = strchr(obj, '{');
        if (!obj)
            break;
        const char *obj_end = strchr(obj, '}');
        if (!obj_end)
            break;

        char block[1024];
        size_t blen = (size_t)(obj_end - obj + 1);
        if (blen >= sizeof(block))
            blen = sizeof(block) - 1;
        memcpy(block, obj, blen);
        block[blen] = '\0';

        kgo_pattern_t *p = &cfg->patterns[cfg->pattern_count];
        if (!json_str(block, "id", p->id, sizeof(p->id))
            || !json_str(block, "match", p->match, sizeof(p->match))) {
            obj = obj_end + 1;
            continue;
        }
        json_str(block, "reason", p->reason, sizeof(p->reason));
        p->shell_only = json_bool_in_obj(block, "shell_only");
        if (p->shell_only)
            cfg->require_shell_any = true;
        cfg->pattern_count++;
        obj = obj_end + 1;
    }

    free(json);
    return cfg->pattern_count > 0 ? 0 : -1;
}