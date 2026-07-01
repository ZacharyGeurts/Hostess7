/* AmmoOS Image — field I/O dispatch: field_opt CPU vs RTX batch paths */
#pragma once

#include <glib.h>
#include <stdint.h>

#define FIELD_MAGIC_WRDT 0x54445257u /* 'WRDT' LE */
#define FIELD_MAGIC_WRZC 0x43525a57u /* 'WRZC' LE */
#define FIELD_MAGIC_ZAC7 0x3743415au /* 'ZAC7' LE */

typedef enum {
  FIELD_IO_CPU    = 0,
  FIELD_IO_RTX    = 1
} FieldIoPath;

typedef struct {
  uint32_t magic;
  FieldIoPath path;
  gboolean   rtx_permit;
  gchar     *profile;
} FieldIoPosture;

FieldIoPosture *field_io_posture_new (void);
void            field_io_posture_free (FieldIoPosture *p);

gboolean field_io_rtx_permit (void);
FieldIoPath field_io_select_path (void);

uint32_t field_io_sniff_magic (const guint8 *buf, gsize len);

GBytes *field_wrdt_unpack_cpu (const guint8 *blob, gsize len, GError **error);
GBytes *field_wrdt_unpack_rtx  (const guint8 *blob, gsize len, GError **error);
GBytes *field_io_unpack_auto   (const guint8 *blob, gsize len, GError **error);

gboolean field_io_load_via_python (const gchar *path, gchar **temp_image, gchar **profile, GError **error);