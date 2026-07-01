#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <signal.h>
#include <time.h>
#include <sys/mman.h>
#include <sys/prctl.h>
#include <seccomp.h>
#include <openssl/evp.h>
#include <openssl/rand.h>
#include <argon2.h>

#define MAX_DATA 32768
#define TIMEOUT_SEC 180
#define ARGON2_TIME 4
#define ARGON2_MEM  (1<<18)

static unsigned char key[32];
static unsigned char iv[12];
static char *data_enc = NULL;
static time_t last = 0;
static int paste_once = 0;
static int wayland = 0;

static void wipe(void *p, size_t n) { explicit_bzero(p, n); }

static void derive_key(const char *pass) {
  uint8_t salt[16];
  RAND_bytes(salt, sizeof(salt));
  argon2id_hash_raw(ARGON2_TIME, ARGON2_MEM/1024, 1,
                    pass, strlen(pass), salt, 16, key, 32);
  RAND_bytes(iv, 12);
}

static void aes_gcm(char *buf, size_t len, int enc) {
  EVP_CIPHER_CTX *ctx = EVP_CIPHER_CTX_new();
  EVP_CipherInit_ex(ctx, EVP_aes_256_gcm(), NULL, key, iv, enc);
  int olen;
  EVP_CipherUpdate(ctx, (unsigned char*)buf, &olen, (unsigned char*)buf, (int)len);
  EVP_CipherFinal_ex(ctx, (unsigned char*)buf + olen, &olen);
  EVP_CIPHER_CTX_free(ctx);
}

static void clear_all(void) {
  if (data_enc) {
    wipe(data_enc, MAX_DATA);
    munlock(data_enc, MAX_DATA);
    free(data_enc);
    data_enc = NULL;
  }
  last = 0;
  if (wayland) system("wl-copy --clear 2>/dev/null || true");
  else system("xclip -selection clipboard -i /dev/null 2>/dev/null || true");
  prctl(PR_SET_DUMPABLE, 0);
}

static void sig(int s) { (void)s; clear_all(); _exit(0); }

int main(void) {
  signal(SIGTERM, sig);
  signal(SIGINT, sig);
  signal(SIGSEGV, sig);
  mlockall(MCL_CURRENT|MCL_FUTURE);
  prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0);

  scmp_filter_ctx ctx = seccomp_init(SCMP_ACT_KILL);
  seccomp_rule_add(ctx, SCMP_ACT_ALLOW, SCMP_SYS(read), 0);
  seccomp_rule_add(ctx, SCMP_ACT_ALLOW, SCMP_SYS(write), 0);
  seccomp_rule_add(ctx, SCMP_ACT_ALLOW, SCMP_SYS(exit), 0);
  seccomp_rule_add(ctx, SCMP_ACT_ALLOW, SCMP_SYS(exit_group), 0);
  seccomp_rule_add(ctx, SCMP_ACT_ALLOW, SCMP_SYS(rt_sigreturn), 0);
  seccomp_rule_add(ctx, SCMP_ACT_ALLOW, SCMP_SYS(nanosleep), 0);
  seccomp_rule_add(ctx, SCMP_ACT_ALLOW, SCMP_SYS(clock_nanosleep), 0);
  seccomp_load(ctx);

  wayland = (getenv("WAYLAND_DISPLAY") != NULL);

  char pass[256] = {0};
  fputs("Enter vault passphrase for clipboard daemon: ", stdout);
  fflush(stdout);
  if (!fgets(pass, sizeof(pass), stdin)) return 1;
  pass[strcspn(pass, "\n")] = 0;
  derive_key(pass);
  wipe(pass, sizeof(pass));

  fputs("sg_clipd: RAM vault daemon running\n", stdout);

  while (1) {
    sleep(10);
    if (data_enc && (time(NULL) - last > TIMEOUT_SEC)) clear_all();
  }
  return 0;
}