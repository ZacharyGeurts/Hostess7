/* AmmoOS Image — export to WRDT1 lossless envelope */
#include "config.h"

#include <errno.h>
#include <string.h>
#include <unistd.h>
#include <zlib.h>

#include <gdk-pixbuf/gdk-pixbuf.h>
#include <glib.h>
#include <glib/gstdio.h>
#include <libgimp/gimp.h>

#include "file-field-export.h"

#define WRDT_HDR 52

gboolean
field_save_merged_png (GimpImage *image, gchar **out_path, GError **error)
{
  GimpLayer  *layer;
  GdkPixbuf  *pixbuf;
  gchar      *tmp;
  gint        fd;
  gint        w;
  gint        h;

  gimp_image_merge_visible_layers (image, GIMP_CLIP_TO_IMAGE);
  layer = gimp_image_get_active_layer (image);
  if (!layer)
    {
      g_set_error (error, G_FILE_ERROR, G_FILE_ERROR_FAILED, "no active layer");
      return FALSE;
    }

  w = gimp_image_get_width (image);
  h = gimp_image_get_height (image);
  pixbuf = gimp_drawable_get_thumbnail (GIMP_DRAWABLE (layer), w, h, GIMP_PIXBUF_SMALL_OK);
  if (!pixbuf)
    {
      g_set_error (error, G_FILE_ERROR, G_FILE_ERROR_FAILED, "thumbnail failed");
      return FALSE;
    }

  tmp = g_strdup_printf ("/tmp/ammoos-export-XXXXXX.png");
  fd = g_mkstemp (tmp);
  if (fd < 0)
    {
      g_object_unref (pixbuf);
      g_free (tmp);
      g_set_error (error, G_FILE_ERROR, g_file_error_from_errno (errno), "mkstemp failed");
      return FALSE;
    }
  close (fd);

  if (!gdk_pixbuf_save (pixbuf, tmp, "png", error, NULL))
    {
      g_unlink (tmp);
      g_free (tmp);
      g_object_unref (pixbuf);
      return FALSE;
    }

  g_object_unref (pixbuf);
  *out_path = tmp;
  return TRUE;
}

gboolean
export_field_wrdt (GFile *file, const gchar *inner_path, GError **error)
{
  gchar *png_bytes = NULL;
  gsize  png_len = 0;
  gchar *path;
  Bytef *zbuf = NULL;
  uLongf zlen;
  int zret;
  gsize total;
  guchar *out;
  guchar digest[32];
  GChecksum *chk;
  gsize dlen = 32;

  path = g_file_get_path (file);
  if (!inner_path || !path || !g_file_get_contents (inner_path, &png_bytes, &png_len, error))
    {
      g_free (path);
      return FALSE;
    }

  chk = g_checksum_new (G_CHECKSUM_SHA256);
  g_checksum_update (chk, (const guchar *) png_bytes, png_len);
  g_checksum_get_digest (chk, digest, &dlen);
  g_checksum_free (chk);

  zlen = compressBound ((uLong) png_len);
  zbuf = g_malloc (zlen);
  zret = compress2 (zbuf, &zlen, (const Bytef *) png_bytes, (uLong) png_len, 1);
  g_free (png_bytes);

  if (zret != Z_OK)
    {
      g_free (zbuf);
      g_free (path);
      g_set_error (error, G_FILE_ERROR, G_FILE_ERROR_FAILED, "zlib pack %d", zret);
      return FALSE;
    }

  total = WRDT_HDR + zlen;
  out = g_malloc (total);
  memcpy (out, "WRDT", 4);
  out[4] = 1;
  out[5] = 1;
  out[6] = out[7] = 0;
  {
    guint64 orig = (guint64) png_len;
    guint32 plen = (guint32) zlen;
    memcpy (out + 8, &orig, 8);
    memcpy (out + 16, &plen, 4);
  }
  memcpy (out + 20, digest, 32);
  memcpy (out + WRDT_HDR, zbuf, zlen);
  g_free (zbuf);

  if (!g_file_set_contents (path, (gchar *) out, total, error))
    {
      g_free (out);
      g_free (path);
      return FALSE;
    }

  g_free (out);
  g_free (path);
  return TRUE;
}