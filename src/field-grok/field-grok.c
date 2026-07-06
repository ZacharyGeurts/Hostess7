#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <getopt.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#define FIELD_GROK_VERSION "1.0.0"
#define FIELD_GROK_SCHEMA  "field-grok/v1"

static int endswith(const char *hay, const char *needle)
{
    size_t hlen = strlen(hay);
    size_t nlen = strlen(needle);
    if (nlen > hlen)
        return 0;
    return strcmp(hay + hlen - nlen, needle) == 0;
}

static void usage(const char *prog)
{
    fprintf(stderr,
            "Field Grok v%s — secure operator CLI binary\n\n"
            "Usage: %s <command> [args...]\n"
            "  json              posture JSON for UI\n"
            "  dispatch          read JSON body from stdin\n"
            "  launch [args...]  secure grok desktop launch\n"
            "  version           version stamp\n"
            "  -h, --help        show help\n\n"
            "Env: NEXUS_INSTALL_ROOT, FIELD_GROK_OPERATOR_TOKEN, GROK_MAX_SOCKETS\n",
            FIELD_GROK_VERSION, prog);
}

static int resolve_install_root(char *out, size_t outlen)
{
    const char *env = getenv("NEXUS_INSTALL_ROOT");
    if (env && env[0]) {
        snprintf(out, outlen, "%s", env);
        return 0;
    }
    char self[PATH_MAX];
    ssize_t n = readlink("/proc/self/exe", self, sizeof(self) - 1);
    if (n < 0)
        return -1;
    self[n] = '\0';
    char *slash = strrchr(self, '/');
    if (!slash)
        return -1;
    *slash = '\0';
    if (endswith(self, "/lib/bin")) {
        size_t len = strlen(self);
        if (len > 8) {
            self[len - 8] = '\0';
            snprintf(out, outlen, "%s", self);
            return 0;
        }
    }
    snprintf(out, outlen, "%s", self);
    return 0;
}

static void apply_secure_env(void)
{
    setenv("NEXUS_AI_SECURE_CHANNEL", "1", 1);
    setenv("QUEEN_AI_TELEMETRY_OK", "1", 1);
    setenv("QUEEN_GROK_BUILD", "1", 1);
    setenv("QUEEN_GROK_BUILD_SECURE", "1", 1);
    setenv("GROK_SECURE_CHANNEL", "1", 1);
    if (!getenv("GROK_MAX_SOCKETS"))
        setenv("GROK_MAX_SOCKETS", "5", 1);
    if (!getenv("SSL_CERT_FILE"))
        setenv("SSL_CERT_FILE", "/etc/ssl/certs/ca-certificates.crt", 1);
    if (!getenv("REQUESTS_CA_BUNDLE"))
        setenv("REQUESTS_CA_BUNDLE", "/etc/ssl/certs/ca-certificates.crt", 1);
    unsetenv("HTTP_PROXY");
    unsetenv("HTTPS_PROXY");
    unsetenv("http_proxy");
    unsetenv("https_proxy");
    unsetenv("ALL_PROXY");
    unsetenv("all_proxy");
}

static int exec_python_backend(const char *root, const char *subcmd)
{
    char cli[PATH_MAX];
    snprintf(cli, sizeof(cli), "%s/lib/field-grok-cli.py", root);
    apply_secure_env();
    setenv("NEXUS_INSTALL_ROOT", root, 1);
    execlp("python3", "python3", cli, subcmd, (char *)NULL);
    execlp("pythong", "pythong", cli, subcmd, (char *)NULL);
    fprintf(stderr, "field-grok: cannot exec %s (%s)\n", cli, strerror(errno));
    return 127;
}

static int cmd_version(void)
{
    printf("{\"schema\":\"%s\",\"version\":\"%s\",\"binary\":\"field-grok\"}\n",
           FIELD_GROK_SCHEMA, FIELD_GROK_VERSION);
    return 0;
}

static int cmd_launch(const char *root, int argc, char **argv)
{
    char launch[PATH_MAX];
    snprintf(launch, sizeof(launch), "%s/lib/grok-launch.sh", root);
    apply_secure_env();
    setenv("NEXUS_INSTALL_ROOT", root, 1);
    char *args[argc + 3];
    int i;
    args[0] = "bash";
    args[1] = (char *)launch;
    for (i = 0; i < argc; i++)
        args[i + 2] = argv[i];
    args[argc + 2] = NULL;
    execvp("bash", args);
    fprintf(stderr, "field-grok: cannot exec %s (%s)\n", launch, strerror(errno));
    return 127;
}

int main(int argc, char **argv)
{
    char root[PATH_MAX];
    const char *cmd;

    if (argc < 2 || !strcmp(argv[1], "-h") || !strcmp(argv[1], "--help")) {
        usage(argv[0]);
        return argc < 2 ? 1 : 0;
    }

    if (resolve_install_root(root, sizeof(root)) != 0) {
        fprintf(stderr, "field-grok: cannot resolve install root\n");
        return 1;
    }

    cmd = argv[1];
    if (!strcmp(cmd, "version"))
        return cmd_version();
    if (!strcmp(cmd, "json"))
        return exec_python_backend(root, "json");
    if (!strcmp(cmd, "dispatch"))
        return exec_python_backend(root, "dispatch");
    if (!strcmp(cmd, "launch"))
        return cmd_launch(root, argc - 2, argv + 2);

    fprintf(stderr, "field-grok: unknown command '%s'\n", cmd);
    usage(argv[0]);
    return 1;
}