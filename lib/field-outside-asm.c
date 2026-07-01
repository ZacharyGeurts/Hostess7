/*
 * field-outside-asm — minimal egress probe (direct syscalls, fixed buffers).
 * NEXUS Outside Talk: no shell, no curl, no openssl CLI. Field-fast.
 *
 * Build: gcc -O2 -pipe -fstack-protector-strong -D_FORTIFY_SOURCE=2 \
 *          -o field-outside-asm field-outside-asm.c
 *
 * Usage: field-outside-asm <mode> <host> <port> [arg]
 * Modes: tcp | udp | banner | http | tls | smtp | dns | ssh
 */
#define _GNU_SOURCE
#include <arpa/inet.h>
#include <errno.h>
#include <fcntl.h>
#include <netdb.h>
#include <netinet/in.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <unistd.h>

#define BUF_SZ 512
#define CONNECT_MS 5000
#define IO_MS 3000

static long long now_ms(void) {
    struct timeval tv;
    gettimeofday(&tv, NULL);
    return (long long)tv.tv_sec * 1000LL + tv.tv_usec / 1000;
}

static int set_timeouts(int fd, int ms) {
    struct timeval tv;
    tv.tv_sec = ms / 1000;
    tv.tv_usec = (ms % 1000) * 1000;
    if (setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv)) < 0) return -1;
    if (setsockopt(fd, SOL_SOCKET, SO_SNDTIMEO, &tv, sizeof(tv)) < 0) return -1;
    return 0;
}

static int resolve_host(const char *host, struct sockaddr_in *out) {
    struct addrinfo hints, *res = NULL;
    memset(&hints, 0, sizeof(hints));
    hints.ai_family = AF_INET;
    hints.ai_socktype = SOCK_STREAM;
    int rc = getaddrinfo(host, NULL, &hints, &res);
    if (rc != 0 || !res) return -1;
    memcpy(out, res->ai_addr, sizeof(struct sockaddr_in));
    freeaddrinfo(res);
    return 0;
}

static int tcp_connect(const char *host, int port) {
    struct sockaddr_in addr;
    if (resolve_host(host, &addr) < 0) return -1;
    addr.sin_port = htons((uint16_t)port);
    int fd = socket(AF_INET, SOCK_STREAM, 0);
    if (fd < 0) return -1;
    set_timeouts(fd, CONNECT_MS);
    if (connect(fd, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        close(fd);
        return -1;
    }
    set_timeouts(fd, IO_MS);
    return fd;
}

static int udp_open(const char *host, int port, struct sockaddr_in *peer) {
    if (resolve_host(host, peer) < 0) return -1;
    peer->sin_port = htons((uint16_t)port);
    int fd = socket(AF_INET, SOCK_DGRAM, 0);
    if (fd < 0) return -1;
    set_timeouts(fd, IO_MS);
    return fd;
}

static void json_escape(const char *in, char *out, size_t out_sz) {
    size_t j = 0;
    for (size_t i = 0; in[i] && j + 2 < out_sz; i++) {
        unsigned char c = (unsigned char)in[i];
        if (c == '"' || c == '\\') {
            out[j++] = '\\';
            out[j++] = (char)c;
        } else if (c >= 32 && c < 127) {
            out[j++] = (char)c;
        } else {
            out[j++] = '.';
        }
    }
    out[j] = '\0';
}

static void emit_json(int ok, int bytes, const char *payload, long long elapsed) {
    char esc[BUF_SZ * 2];
    json_escape(payload, esc, sizeof(esc));
    printf("{\"ok\":%s,\"bytes\":%d,\"output\":\"%s\",\"elapsed_ms\":%lld,\"engine\":\"asm\"}\n",
           ok ? "true" : "false", bytes, esc, elapsed);
}

static int read_some(int fd, char *buf, size_t sz) {
    ssize_t n = recv(fd, buf, sz - 1, 0);
    if (n < 0) return -1;
    buf[n] = '\0';
    return (int)n;
}

static int mode_tcp(const char *host, int port) {
    long long t0 = now_ms();
    int fd = tcp_connect(host, port);
    if (fd < 0) {
        emit_json(0, 0, "asm: tcp connect failed", now_ms() - t0);
        return 1;
    }
    close(fd);
    emit_json(1, 0, "asm: tcp connect ok", now_ms() - t0);
    return 0;
}

static int mode_udp(const char *host, int port) {
    long long t0 = now_ms();
    struct sockaddr_in peer;
    int fd = udp_open(host, port, &peer);
    if (fd < 0) {
        emit_json(0, 0, "asm: udp socket failed", now_ms() - t0);
        return 1;
    }
    char ping[4] = { 'N', 'X', 'S', 0 };
    ssize_t sent = sendto(fd, ping, 3, 0, (struct sockaddr *)&peer, sizeof(peer));
    close(fd);
    if (sent < 0) {
        emit_json(0, 0, "asm: udp send failed", now_ms() - t0);
        return 1;
    }
    emit_json(1, (int)sent, "asm: udp send ok", now_ms() - t0);
    return 0;
}

static int mode_banner(const char *host, int port) {
    long long t0 = now_ms();
    int fd = tcp_connect(host, port);
    if (fd < 0) {
        emit_json(0, 0, "asm: banner connect failed", now_ms() - t0);
        return 1;
    }
    char buf[BUF_SZ];
    int n = read_some(fd, buf, sizeof(buf));
    close(fd);
    if (n < 0) {
        emit_json(0, 0, "asm: banner read timeout", now_ms() - t0);
        return 1;
    }
    emit_json(1, n, buf, now_ms() - t0);
    return 0;
}

static int mode_ssh(const char *host, int port) {
    long long t0 = now_ms();
    int fd = tcp_connect(host, port);
    if (fd < 0) {
        emit_json(0, 0, "asm: ssh connect failed", now_ms() - t0);
        return 1;
    }
    char buf[BUF_SZ];
    int n = read_some(fd, buf, sizeof(buf));
    close(fd);
    if (n < 0 || strncmp(buf, "SSH-", 4) != 0) {
        emit_json(0, n > 0 ? n : 0, n > 0 ? buf : "asm: no SSH banner", now_ms() - t0);
        return 1;
    }
    emit_json(1, n, buf, now_ms() - t0);
    return 0;
}

static int mode_http(const char *host, int port, const char *path) {
    long long t0 = now_ms();
    int fd = tcp_connect(host, port);
    if (fd < 0) {
        emit_json(0, 0, "asm: http connect failed", now_ms() - t0);
        return 1;
    }
    char req[BUF_SZ];
    snprintf(req, sizeof(req), "HEAD %s HTTP/1.0\r\nHost: %s\r\nConnection: close\r\n\r\n",
             path && path[0] ? path : "/", host);
    if (send(fd, req, strlen(req), 0) < 0) {
        close(fd);
        emit_json(0, 0, "asm: http send failed", now_ms() - t0);
        return 1;
    }
    char buf[BUF_SZ];
    int n = read_some(fd, buf, sizeof(buf));
    close(fd);
    if (n < 0) {
        emit_json(0, 0, "asm: http read timeout", now_ms() - t0);
        return 1;
    }
    emit_json(1, n, buf, now_ms() - t0);
    return 0;
}

static int mode_smtp(const char *host, int port) {
    long long t0 = now_ms();
    int fd = tcp_connect(host, port);
    if (fd < 0) {
        emit_json(0, 0, "asm: smtp connect failed", now_ms() - t0);
        return 1;
    }
    char buf[BUF_SZ];
    int n = read_some(fd, buf, sizeof(buf));
    if (n < 0) {
        close(fd);
        emit_json(0, 0, "asm: smtp banner timeout", now_ms() - t0);
        return 1;
    }
    const char *ehlo = "EHLO nexus-field.local\r\n";
    send(fd, ehlo, strlen(ehlo), 0);
    char buf2[BUF_SZ];
    int n2 = read_some(fd, buf2, sizeof(buf2));
    close(fd);
    char out[BUF_SZ * 2];
    snprintf(out, sizeof(out), "%s\n%s", buf, n2 > 0 ? buf2 : "");
    emit_json(1, n + (n2 > 0 ? n2 : 0), out, now_ms() - t0);
    return 0;
}

static int mode_tls(const char *host, int port) {
    /* ASM-fast: TCP + TLS record sniff (0x16 0x03) without openssl */
    long long t0 = now_ms();
    int fd = tcp_connect(host, port);
    if (fd < 0) {
        emit_json(0, 0, "asm: tls connect failed", now_ms() - t0);
        return 1;
    }
    char buf[BUF_SZ];
    int n = read_some(fd, buf, sizeof(buf));
    close(fd);
    if (n >= 3 && (unsigned char)buf[0] == 0x16 && (unsigned char)buf[1] == 0x03) {
        emit_json(1, n, "asm: tls record detected (handshake offered)", now_ms() - t0);
        return 0;
    }
    if (n > 0) {
        emit_json(1, n, buf, now_ms() - t0);
        return 0;
    }
    emit_json(0, 0, "asm: tls no response", now_ms() - t0);
    return 1;
}

static int mode_dns(const char *host, int port) {
    long long t0 = now_ms();
    struct sockaddr_in peer;
    int fd = udp_open(host, port, &peer);
    if (fd < 0) {
        emit_json(0, 0, "asm: dns socket failed", now_ms() - t0);
        return 1;
    }
    /* Minimal query: example.com A */
    unsigned char q[] = {
        0x4e, 0x58, 0x01, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x07, 'e', 'x', 'a', 'm', 'p', 'l', 'e',
        0x03, 'c', 'o', 'm',
        0x00, 0x00, 0x01, 0x00, 0x01
    };
    if (sendto(fd, q, sizeof(q), 0, (struct sockaddr *)&peer, sizeof(peer)) < 0) {
        close(fd);
        emit_json(0, 0, "asm: dns send failed", now_ms() - t0);
        return 1;
    }
    char buf[BUF_SZ];
    ssize_t n = recvfrom(fd, buf, sizeof(buf) - 1, 0, NULL, NULL);
    close(fd);
    if (n < 12) {
        emit_json(0, (int)(n > 0 ? n : 0), "asm: dns no/short response", now_ms() - t0);
        return 1;
    }
    emit_json(1, (int)n, "asm: dns response received", now_ms() - t0);
    return 0;
}

int main(int argc, char **argv) {
    if (argc < 4) {
        fprintf(stderr, "usage: %s <tcp|udp|banner|http|tls|smtp|dns|ssh> <host> <port> [path]\n", argv[0]);
        return 2;
    }
    const char *mode = argv[1];
    const char *host = argv[2];
    int port = atoi(argv[3]);
    if (port < 1 || port > 65535 || !host[0]) return 2;
    if (strlen(host) > 253) return 2;

    if (strcmp(mode, "tcp") == 0) return mode_tcp(host, port);
    if (strcmp(mode, "udp") == 0) return mode_udp(host, port);
    if (strcmp(mode, "banner") == 0) return mode_banner(host, port);
    if (strcmp(mode, "ssh") == 0) return mode_ssh(host, port);
    if (strcmp(mode, "http") == 0) return mode_http(host, port, argc > 4 ? argv[4] : "/");
    if (strcmp(mode, "tls") == 0) return mode_tls(host, port);
    if (strcmp(mode, "smtp") == 0) return mode_smtp(host, port);
    if (strcmp(mode, "dns") == 0) return mode_dns(host, port);
    return 2;
}