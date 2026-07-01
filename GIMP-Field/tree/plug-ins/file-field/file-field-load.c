/* AmmoOS Image — field format loader */
#include "config.h"

#include <unistd.h>

#include <glib/gstdio.h>
#include <libgimp/gimp.h>

#include "field-io-dispatch.h"
#include "file-field-load.h"

static GimpImage *
load_inner_file (const gchar *path, GError **error)
{
  GimpValueArray *vals;
  GimpProcedure  *proc;
  GFile          *f;
  GimpImage      *image = NULL;

  f = g_file_new_for_path (path);
  proc = gimp_pdb_lookup_procedure ("gimp-file-load");
  if (!proc)
    {
      g_set_error (error, G_FILE_ERROR, G_FILE_ERROR_FAILED, "gimp-file-load missing");
      g_object_unref (f);
      return NULL;
    }

  vals = gimp_procedure_run (proc,
                             "run-mode", GIMP_RUN_NONINTERACTIVE,
                             "file", f,
                             NULL);
  g_object_unref (f);

  if (GIMP_VALUES_GET_ENUM (vals, 0) == GIMP_PDB_SUCCESS)
    image = GIMP_VALUES_GET_IMAGE (vals, 1);

  gimp_value_array_unref (vals);
  return image;
}

GimpImage *
load_field_image (GFile *file, GError **error)
{
  gchar  *path = g_file_get_path (file);
  gchar  *contents = NULL;
  gsize   len = 0;
  GBytes *body = NULL;
  GimpImage *image = NULL;
  uint32_t magic;

  if (!path || !g_file_get_contents (path, &contents, &len, error))
    {
      g_free (path);
      return NULL;
    }

  magic = field_io_sniff_magic ((const guint8 *) contents, len);

  if (magic == FIELD_MAGIC_WRDT)
    {
      body = field_io_unpack_auto ((const guint8 *) contents, len, error);
      g_free (contents);
      if (body)
        {
          gchar *tmp = g_strdup_printf ("/tmp/ammoos-field-XXXXXX");
          gint fd = g_mkstemp (tmp);
          if (fd >= 0)
            {
              gsize blen = g_bytes_get_size (body);
              if (write (fd, g_bytes_get_data (body, NULL), blen) == (ssize_t) blen)
                {
                  close (fd);
                  image = load_inner_file (tmp, error);
                }
              else
                close (fd);
              g_unlink (tmp);
              g_free (tmp);
            }
          g_bytes_unref (body);
        }
      g_free (path);
      return image;
    }

  g_free (contents);

  {
    gchar *temp = NULL;
    gchar *profile = NULL;
    if (field_io_load_via_python (path, &temp, &profile, error) && temp)
      {
        image = load_inner_file (temp, error);
        g_unlink (temp);
        g_free (temp);
      }
    g_free (profile);
  }

  g_free (path);
  return image;
}