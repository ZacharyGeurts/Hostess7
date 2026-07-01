/* AmmoOS Image — field I/O dispatch (g16 field_opt + RTX batch) */
#include "config.h"

#include <string.h>
#include <zlib.h>

#include <glib.h>
#include <glib/gstdio.h>

#include "field-io-dispatch.h"

#define WRDT_HDR 52

static gboolean
field_env_rtx_force (void)
{
  const gchar *v = g_getenv ("G16_RTX_GATE_FORCE");
  return v && (*v == '1' || g_ascii_strcasecmp (v, "true") == 0 || g_ascii_strcasecmp (v, "yes") == 0);
}

static gboolean
field_io_gate_via_python (void)
{
  gchar *sg = g_getenv ("SG_ROOT");
  gchar *script;
  gchar *out = NULL;
  gchar *err = NULL;
  gint status = 0;
  gboolean permit = FALSE;

  if (!sg)
    sg = g_strdup ("/home/default/Desktop/SG");

  script = g_build_filename (sg, "GIMP-Field", "lib", "field-image-io.py", NULL);
  if (!g_file_test (script, G_FILE_TEST_EXISTS))
    {
      g_free (script);
      if (sg != g_getenv ("SG_ROOT"))
        g_free (sg);
      return FALSE;
    }

  gchar *argv[] = { "python3", script, "rtx", NULL };
  if (g_spawn_sync (NULL, argv, NULL, G_SPAWN_SEARCH_PATH, NULL, NULL, &out, &err, &status, NULL))
    {
      if (out && strstr (out, "\"permit\": true"))
        permit = TRUE;
    }

  g_free (out);
  g_free (err);
  g_free (script);
  if (sg != g_getenv ("SG_ROOT"))
    g_free (sg);
  return permit;
}

gboolean
field_io_rtx_permit (void)
{
  gchar *state;
  gchar *panel;
  gboolean permit = FALSE;

  if (field_env_rtx_force ())
    return TRUE;

  state = g_build_filename (g_get_user_cache_dir (), "ammoos-rtx-gate", NULL);
  panel = g_build_filename (state, "permit", NULL);
  if (g_file_test (panel, G_FILE_TEST_EXISTS))
    permit = TRUE;
  g_free (panel);
  g_free (state);

  if (!permit)
    permit = field_io_gate_via_python ();

  return permit;
}

FieldIoPosture *
field_io_posture_new (void)
{
  FieldIoPosture *p = g_slice_new0 (FieldIoPosture);
  p->rtx_permit = field_io_rtx_permit ();
  p->path = p->rtx_permit ? FIELD_IO_RTX : FIELD_IO_CPU;
  p->profile = g_strdup (p->rtx_permit ? "queen_rtx" : "field_opt");
  return p;
}

void
field_io_posture_free (FieldIoPosture *p)
{
  if (!p)
    return;
  g_free (p->profile);
  g_slice_free (FieldIoPosture, p);
}

FieldIoPath
field_io_select_path (void)
{
  return field_io_rtx_permit () ? FIELD_IO_RTX : FIELD_IO_CPU;
}

uint32_t
field_io_sniff_magic (const guint8 *buf, gsize len)
{
  if (!buf || len < 4)
    return 0;
  return (uint32_t) buf[0] | ((uint32_t) buf[1] << 8) | ((uint32_t) buf[2] << 16) | ((uint32_t) buf[3] << 24);
}

static GBytes *
field_wrdt_unpack_impl (const guint8 *blob, gsize len, gboolean rtx_path, GError **error)
{
  guint8 digest[32];
  guint64 orig;
  guint32 pay_len;
  guint8 method;
  gsize body_len;
  Bytef *body = NULL;

  if (len < WRDT_HDR || field_io_sniff_magic (blob, len) != FIELD_MAGIC_WRDT)
    {
      g_set_error (error, G_FILE_ERROR, G_FILE_ERROR_INVAL, "not WRDT1");
      return NULL;
    }

  method = blob[5];
  memcpy (&orig, blob + 8, 8);
  memcpy (&pay_len, blob + 16, 4);
  memcpy (digest, blob + 20, 32);

  if (WRDT_HDR + pay_len > len)
    {
      g_set_error (error, G_FILE_ERROR, G_FILE_ERROR_INVAL, "truncated WRDT");
      return NULL;
    }

  if (method == 0)
    {
      body = g_memdup2 (blob + WRDT_HDR, pay_len);
      body_len = pay_len;
    }
  else if (method == 1)
    {
      uLongf dest_len = (uLongf) orig;
      body = g_malloc (dest_len);
      int z = uncompress (body, &dest_len, blob + WRDT_HDR, pay_len);
      if (z != Z_OK)
        {
          g_free (body);
          g_set_error (error, G_FILE_ERROR, G_FILE_ERROR_FAILED, "zlib %d", z);
          return NULL;
        }
      body_len = dest_len;
      (void) rtx_path;
    }
  else
    {
      g_set_error (error, G_FILE_ERROR, G_FILE_ERROR_INVAL, "unknown WRDT method");
      return NULL;
    }

  if (body_len != orig)
    {
      g_free (body);
      g_set_error (error, G_FILE_ERROR, G_FILE_ERROR_FAILED, "WRDT size mismatch");
      return NULL;
    }

  return g_bytes_new_take (body, body_len);
}

GBytes *
field_wrdt_unpack_cpu (const guint8 *blob, gsize len, GError **error)
{
  return field_wrdt_unpack_impl (blob, len, FALSE, error);
}

GBytes *
field_wrdt_unpack_rtx (const guint8 *blob, gsize len, GError **error)
{
  return field_wrdt_unpack_impl (blob, len, TRUE, error);
}

GBytes *
field_io_unpack_auto (const guint8 *blob, gsize len, GError **error)
{
  if (field_io_select_path () == FIELD_IO_RTX)
    return field_wrdt_unpack_rtx (blob, len, error);
  return field_wrdt_unpack_cpu (blob, len, error);
}

gboolean
field_io_load_via_python (const gchar *path, gchar **temp_image, gchar **profile, GError **error)
{
  gchar *sg = g_getenv ("SG_ROOT");
  gchar *script;
  gchar *out = NULL;
  gchar *err = NULL;
  gint status = 0;
  gboolean ok = FALSE;

  if (!sg)
    sg = g_strdup ("/home/default/Desktop/SG");

  script = g_build_filename (sg, "GIMP-Field", "lib", "field-image-io.py", NULL);

  if (!g_file_test (script, G_FILE_TEST_EXISTS))
    {
      g_set_error (error, G_FILE_ERROR, G_FILE_ERROR_NOENT, "field-image-io.py missing");
      g_free (script);
      g_free (sg);
      return FALSE;
    }

  gchar *argv[] = { "python3", script, "dispatch", (gchar *) path, NULL };
  if (!g_spawn_sync (NULL, argv, NULL, G_SPAWN_SEARCH_PATH, NULL, NULL, &out, &err, &status, error))
    {
      g_free (script);
      if (sg != g_getenv ("SG_ROOT"))
        g_free (sg);
      return FALSE;
    }

  if (out && strstr (out, "\"ok\": true"))
    {
      ok = TRUE;
      if (profile)
        *profile = g_strdup (strstr (out, "field_opt") ? "field_opt" : "queen_rtx");
      if (temp_image)
        {
          gchar *p = strstr (out, "\"temp_image\":");
          if (p)
            {
              p = strchr (p, '"');
              if (p)
                {
                  p = strchr (p + 1, '"');
                  if (p)
                    {
                      gchar *q = strchr (p + 1, '"');
                      if (q)
                        *temp_image = g_strndup (p + 1, q - p - 1);
                    }
                }
            }
        }
    }

  g_free (out);
  g_free (err);
  g_free (script);
  if (sg != g_getenv ("SG_ROOT"))
    g_free (sg);
  return ok;
}