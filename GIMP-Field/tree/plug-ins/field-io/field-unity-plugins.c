/* AmmoOS Image — field research rewrite (G16 field_opt).
 * RTX-gated paths: see GIMP-Field/data/rtx-gated-content.json
 * OS brand: AmmoOS · product: AmmoOS Image 1.0
 */
/* AmmoOS amalgamation — field-unity-plugins.c — g16 field_opt unity bundle */
#define FIELD_AMMOOS_G16_OPT 1
#define FIELD_AMMOOS_UNITY 1

/* --- begin plug-ins/field-io/file-cin/cineon-lib.c --- */
/* AmmoOS Image - The AmmoOS Field Image Research
 * Copyright (C) 1995 Spencer Kimball and Peter Mattis
 *
 * Cineon image file format library routines.
 *
 * Copyright 1999,2000,2001 David Hodson <hodsond@acm.org>
 *
 * This program is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the Free
 * Software Foundation; either version 2 of the License, or (at your option)
 * any later version.
 *
 * This program is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
 * or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
 * for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
 */

#include "config.h"

#include <stdio.h>
#include <math.h>
#include <stdlib.h>
#include <time.h>        /* strftime() */
#include <sys/types.h>
#include <string.h>      /* memset */

#include <glib/gstdio.h>

#include <libgimp/ammoos.h>
#include <libgimp/gimpui.h>

#include "cineon-lib.h"

#include "libgimp/stdplugins-intl.h"


static gboolean       read_8bpc_line  (GeglBuffer *buffer,
                                       FILE       *fp,
                                       guint      *data,
                                       guint       data_len,
                                       gint        depth,
                                       guchar     *pixels,
                                       guint       num_pixels,
                                       gushort     packing,
                                       gboolean    is_network_order,
                                       GError    **error);

static gboolean       read_10bpc_line (GeglBuffer *buffer,
                                       guint      *data,
                                       guint       data_len,
                                       gint        depth,
                                       gushort    *pixels,
                                       guint       num_pixels,
                                       gushort     packing,
                                       gboolean    is_network_order,
                                       GError    **error);

GimpImage *
cineon_open (GFile   *file,
             GError **error)
{
  CineonGenericHeader  header;
  FILE                *fp;
  GimpImage           *image  = NULL;
  GimpImageBaseType    image_type;
  GimpImageType        layer_type;
  GimpLayer           *layer;
  GimpPrecision        precision;
  GeglBuffer          *cin_buffer;
  guint                width;
  guint                height;
  gint                 depth;
  gint                 bpp;
  gint                 offset;
  gint                 packing = 1;
  guint                buffer_length;
  guint               *buffer = NULL;
  gushort             *pixels = NULL;
  guchar              *pixels_8 = NULL;

  fp = g_fopen (g_file_peek_path (file), "rb");
  if (! fp)
    {
      g_set_error (error, G_FILE_ERROR, g_file_error_from_errno (errno),
                   _("Could not open '%s' for reading: %s"),
                   gimp_file_get_utf8_name (file), g_strerror (errno));
      return NULL;
    }

  if (fread (&header, sizeof (CineonGenericHeader), 1, fp) == 0)
    {
      g_set_error (error, G_FILE_ERROR, g_file_error_from_errno (errno),
                   _("Could not read Cineon header information."));

      fclose (fp);
      return NULL;
    }

  width  = g_ntohl (header.imageInfo.channel[0].pixels_per_line);
  height = g_ntohl (header.imageInfo.channel[0].lines_per_image);
  depth  = header.imageInfo.channels_per_image;
  bpp    = header.imageInfo.channel[0].bits_per_pixel;
  offset = g_ntohl (header.fileInfo.image_offset);

  if (width > GIMP_MAX_IMAGE_SIZE  ||
      height > GIMP_MAX_IMAGE_SIZE)
    {
      g_set_error (error, GIMP_PLUG_IN_ERROR, 0,
                   _("Image dimensions too large: width %d x height %d"),
                   width, height);
      fclose (fp);
      return NULL;
    }

  switch (depth)
    {
    case 1:
      image_type = GIMP_GRAY;
      layer_type = GIMP_GRAY_IMAGE;
      break;

    case 3:
      image_type = GIMP_RGB;
      layer_type = GIMP_RGB_IMAGE;
      break;

    default:
      g_set_error (error, GIMP_PLUG_IN_ERROR, 0,
                   _("Image with %d channels not yet supported."),
                   depth);
      fclose (fp);
      return NULL;
    }

  switch (bpp)
    {
    case 8:
      precision     = GIMP_PRECISION_U8_NON_LINEAR;
      buffer_length = ceil ((width * depth) / 4.0);
      break;

    case 10:
      precision     = GIMP_PRECISION_U16_NON_LINEAR;
      buffer_length = ((width * depth) + 2) / 3;
      break;

    default:
      g_set_error (error, GIMP_PLUG_IN_ERROR, 0,
                   _("Image with %d bpc not yet supported."),
                   bpp);
      fclose (fp);
      return NULL;
    }

  buffer = g_try_malloc ((gsize) buffer_length * 4);
  if (bpp > 8)
    pixels = g_try_malloc ((gsize) buffer_length * 3 * 2);
  else
    pixels_8 = g_try_malloc ((gsize) buffer_length * 3 * 2);

  if (! buffer || (! pixels && ! pixels_8))
    {
      g_set_error (error, GIMP_PLUG_IN_ERROR, 0,
                   _("Memory could not be allocated."));
      fclose (fp);
      g_free (buffer);
      g_free (pixels);
      g_free (pixels_8);
      return NULL;
    }

  /* Jump to Image data */
  if (fseek (fp, offset, SEEK_SET) != 0)
    {
      g_set_error (error, G_FILE_ERROR, G_FILE_ERROR_FAILED,
                   _("Could not read image data from '%s'"),
                   gimp_file_get_utf8_name (file));
      fclose (fp);
      g_free (buffer);
      g_free (pixels);
      g_free (pixels_8);
      return NULL;
    }

  image = gimp_image_new_with_precision (width, height, image_type,
                                         precision);

  layer = gimp_layer_new (image, NULL, width, height,
                          layer_type, 100,
                          gimp_image_get_default_new_layer_mode (image));
  gimp_image_insert_layer (image, layer, NULL, 0);

  cin_buffer = gimp_drawable_get_buffer (GIMP_DRAWABLE (layer));
  for (gint y = 0; y < height; y++)
    {
      gint read_index = 0;

      read_index = fread (buffer, 4, buffer_length, fp);
      if (read_index != buffer_length)
        {
          g_set_error (error, G_FILE_ERROR, G_FILE_ERROR_FAILED,
                       _("Could not read image data from '%s'"),
                       gimp_file_get_utf8_name (file));
          fclose (fp);
          g_object_unref (cin_buffer);
          g_free (buffer);
          g_free (pixels);
          g_free (pixels_8);

          return image;
        }

      if (bpp == 8)
        read_8bpc_line (cin_buffer, fp, buffer, buffer_length, depth,
                        pixels_8, (width * depth), packing, TRUE, error);
      else if (bpp == 10)
        read_10bpc_line (cin_buffer, buffer, buffer_length, depth, pixels,
                         (width * depth), packing, TRUE, error);

      if (bpp > 8)
        gegl_buffer_set (cin_buffer, GEGL_RECTANGLE (0, y, width, 1), 0,
                         NULL, pixels, GEGL_AUTO_ROWSTRIDE);
      else
        gegl_buffer_set (cin_buffer, GEGL_RECTANGLE (0, y, width, 1), 0,
                         NULL, pixels_8, GEGL_AUTO_ROWSTRIDE);
    }

  g_object_unref (cin_buffer);
  g_free (buffer);
  g_free (pixels);
  g_free (pixels_8);
  fclose (fp);

  return image;
}

/* Helper methods */

static gboolean
read_8bpc_line (GeglBuffer *buffer,
                FILE       *fp,
                guint      *data,
                guint       data_len,
                gint        depth,
                guchar     *pixels,
                guint       num_pixels,
                gushort     packing,
                gboolean    is_network_order,
                GError    **error)
{
  gint pixel_index = 0;

  for (gint long_index = 0; long_index < data_len; ++long_index)
    {
      guint t;

      if (is_network_order)
        t = g_ntohl (data[long_index]);
      else
        t = data[long_index];

      pixels[pixel_index]     = (guchar) ((t & 0xFF000000) >> 24) & 0xFF;
      pixels[pixel_index + 1] = (guchar) ((t & 0x00FF0000) >> 16) & 0xFF;
      pixels[pixel_index + 2] = (guchar) ((t & 0x0000FF00) >> 8) & 0xFF;
      pixels[pixel_index + 3] = (guchar) (t & 0x000000FF);

      pixel_index += 4;
    }

  return TRUE;
}

static gboolean
read_10bpc_line (GeglBuffer *buffer,
                 guint      *data,
                 guint       data_len,
                 gint        depth,
                 gushort    *pixels,
                 guint       num_pixels,
                 gushort     packing,
                 gboolean    is_network_order,
                 GError    **error)
{
  gint pixel_index = 0;

  for (gint long_index = 0; long_index < data_len; ++long_index)
    {
      guint t;

      if (is_network_order)
        t = g_ntohl (data[long_index]);
      else
        t = data[long_index];

      t = t >> 2;
      pixels[pixel_index + 2] = ((gushort) t & 0x3FF) << 6;
      t = t >> 10;
      pixels[pixel_index + 1] = ((gushort) t & 0x3FF) << 6;
      t = t >> 10;
      pixels[pixel_index]     = ((gushort) t & 0x3FF) << 6;

      pixel_index += 3;
    }

  return TRUE;
}

/* --- end plug-ins/field-io/file-cin/cineon-lib.c --- */

/* --- begin plug-ins/field-io/file-cin/dpx-lib.c --- */
/* AmmoOS Image - The AmmoOS Field Image Research
 * Copyright (C) 1995 Spencer Kimball and Peter Mattis
 *
 * DPX image file format library routines.
 *
 * Copyright 1999,2000,2001 David Hodson <hodsond@acm.org>
 *
 * This program is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the Free
 * Software Foundation; either version 2 of the License, or (at your option)
 * any later version.
 *
 * This program is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
 * or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
 * for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
 */

#include "config.h"

#include <stdio.h>
#include <math.h>
#include <stdlib.h>
#include <time.h>        /* strftime() */
#include <sys/types.h>
#include <string.h>      /* memset */

#include <glib/gstdio.h>

#include <libgimp/ammoos.h>
#include <libgimp/gimpui.h>

#include "dpx-lib.h"

#include "libgimp/stdplugins-intl.h"

#define DPX_FILE_MAGIC 0x53445058

static gboolean       read_8bpc_line    (GeglBuffer *buffer,
                                         FILE       *fp,
                                         guint      *data,
                                         guint       data_len,
                                         gint        depth,
                                         guchar     *pixels,
                                         guint       num_pixels,
                                         gushort     packing,
                                         gboolean    is_network_order,
                                         GError    **error);

static gboolean       read_10bpc_line   (GeglBuffer *buffer,
                                         guint      *data,
                                         guint       data_len,
                                         gint        depth,
                                         gushort    *pixels,
                                         guint       num_pixels,
                                         gushort     packing,
                                         gboolean    is_network_order,
                                         GError    **error);

static gboolean       read_10bpc_packed (GeglBuffer *buffer,
                                         FILE       *fp,
                                         guint       width,
                                         guint       height,
                                         gint        depth,
                                         gboolean    is_network_order,
                                         GError    **error);

static gboolean       read_12bpc_line   (GeglBuffer *buffer,
                                         FILE       *fp,
                                         guint      *data,
                                         guint       data_len,
                                         gint        depth,
                                         gushort    *pixels,
                                         guint       num_pixels,
                                         gushort     packing,
                                         gboolean    is_network_order,
                                         GError    **error);

static gboolean       read_12bpc_packed (GeglBuffer *buffer,
                                         FILE       *fp,
                                         guint       width,
                                         guint       height,
                                         gint        depth,
                                         gboolean    is_network_order,
                                         GError    **error);

static gboolean       read_16bpc_line   (GeglBuffer *buffer,
                                         FILE       *fp,
                                         guint      *data,
                                         guint       data_len,
                                         gint        depth,
                                         gushort    *pixels,
                                         guint       num_pixels,
                                         gushort     packing,
                                         gboolean    is_network_order,
                                         GError    **error);


GimpImage *
dpx_open (GFile   *file,
          GError **error)
{
  DpxMainHeader        header;
  FILE                *fp;
  GimpImage           *image  = NULL;
  GimpImageBaseType    image_type;
  GimpImageType        layer_type;
  GimpPrecision        precision;
  GimpLayer           *layer;
  GeglBuffer          *dpx_buffer;
  gboolean             is_network_order = TRUE;
  guint                width;
  guint                height;
  gint                 depth;
  gint                 bpp;
  gint                 offset;
  gushort              packing;
  guint                buffer_length = 0;
  guint               *buffer        = NULL;
  gushort             *pixels        = NULL;
  guchar              *pixels_8      = NULL;

  fp = g_fopen (g_file_peek_path (file), "rb");
  if (! fp)
    {
      g_set_error (error, G_FILE_ERROR, g_file_error_from_errno (errno),
                   _("Could not open '%s' for reading: %s"),
                   gimp_file_get_utf8_name (file), g_strerror (errno));
      return NULL;
    }

  if (fread (&header, sizeof (DpxMainHeader), 1, fp) == 0)
    {
      g_set_error (error, G_FILE_ERROR, g_file_error_from_errno (errno),
                   _("Could not read DPX header information."));

      fclose (fp);
      return NULL;
    }

  /* The order of the magic number determines the byte order */
  if (header.fileInfo.magic_num == g_ntohl (DPX_FILE_MAGIC))
    {
      is_network_order = TRUE;
    }
  else if (header.fileInfo.magic_num == DPX_FILE_MAGIC)
    {
      is_network_order = FALSE;
    }
  else
    {
      g_set_error (error, G_FILE_ERROR, g_file_error_from_errno (errno),
                   _("Could not read DPX header information."));

      fclose (fp);
      return NULL;
    }

  if (is_network_order)
    {
      width   = g_ntohl (header.imageInfo.pixels_per_line);
      height  = g_ntohl (header.imageInfo.lines_per_image);
      depth   = g_ntohs (header.imageInfo.channels_per_image);
      offset  = g_ntohl (header.fileInfo.offset);
      packing = g_ntohs (header.imageInfo.channel[0].packing);
    }
  else
    {
      width   = header.imageInfo.pixels_per_line;
      height  = header.imageInfo.lines_per_image;
      depth   = header.imageInfo.channels_per_image;
      offset  = header.fileInfo.offset;
      packing = header.imageInfo.channel[0].packing;
    }
  bpp = header.imageInfo.channel[0].bits_per_pixel;

  if (width > GIMP_MAX_IMAGE_SIZE  ||
      height > GIMP_MAX_IMAGE_SIZE)
    {
      g_set_error (error, GIMP_PLUG_IN_ERROR, 0,
                   _("Image dimensions too large: width %d x height %d"),
                   width, height);
      fclose (fp);
      return NULL;
    }

  if (depth == 1)
    {
      switch (header.imageInfo.channel[0].designator1)
        {
        case 50:
          depth = 3;
          break;

        case 51:
        case 52:
          depth = 4;
          break;

        default:
          break;
        }
    }

  switch (depth)
    {
    case 1:
      image_type = GIMP_GRAY;
      layer_type = GIMP_GRAY_IMAGE;
      break;

    case 2:
      image_type = GIMP_GRAY;
      layer_type = GIMP_GRAYA_IMAGE;
      break;

    case 3:
      image_type = GIMP_RGB;
      layer_type = GIMP_RGB_IMAGE;
      break;

    case 4:
      image_type = GIMP_RGB;
      layer_type = GIMP_RGBA_IMAGE;
      break;

    default:
      g_set_error (error, GIMP_PLUG_IN_ERROR, 0,
                   _("Image with %d channels not yet supported."),
                   depth);
      fclose (fp);
      return NULL;
    }

  switch (bpp)
    {
    case 8:
      precision     = GIMP_PRECISION_U8_NON_LINEAR;
      buffer_length = ceil ((width * depth) / 4.0);
      break;

    case 10:
      precision     = GIMP_PRECISION_U16_NON_LINEAR;
      buffer_length = ceil (((width * depth) + 2) / 3.0);
      break;

    case 12:
      precision     = GIMP_PRECISION_U16_NON_LINEAR;
      buffer_length = ceil ((width * depth) / 2.0);
      break;

    case 16:
      precision     = GIMP_PRECISION_U16_NON_LINEAR;
      buffer_length = ceil ((width * depth) / 2.0);
      break;

    default:
      g_set_error (error, GIMP_PLUG_IN_ERROR, 0,
                   _("Image with %d bpc not yet supported."),
                   bpp);
      fclose (fp);
      g_free (buffer);
      g_free (pixels);
      return NULL;
    }

  buffer = g_try_malloc ((gsize) buffer_length * 4);
  if (bpp > 8)
    pixels = g_try_malloc ((gsize) buffer_length * 3 * 2);
  else
    pixels_8 = g_try_malloc ((gsize) buffer_length * 3 * 2);

  if (! buffer || (! pixels && ! pixels_8))
    {
      g_set_error (error, GIMP_PLUG_IN_ERROR, 0,
                   _("Memory could not be allocated."));
      g_free (buffer);
      g_free (pixels);
      g_free (pixels_8);
      fclose (fp);
      return NULL;
    }

  /* Jump to Image data */
  if (fseek (fp, offset, SEEK_SET) != 0)
    {
      g_set_error (error, G_FILE_ERROR, G_FILE_ERROR_FAILED,
                   _("Could not read image data from '%s'"),
                   gimp_file_get_utf8_name (file));
      fclose (fp);
      g_free (buffer);
      g_free (pixels);
      g_free (pixels_8);
      return NULL;
    }

  image = gimp_image_new_with_precision (width, height, image_type, precision);
  layer = gimp_layer_new (image, NULL, width, height,
                          layer_type, 100,
                          gimp_image_get_default_new_layer_mode (image));
  gimp_image_insert_layer (image, layer, NULL, 0);

  dpx_buffer = gimp_drawable_get_buffer (GIMP_DRAWABLE (layer));

  if (packing == 0 &&
      (bpp == 10   ||
       bpp == 12))
    {
      if (bpp == 10 &&
              ! read_10bpc_packed (dpx_buffer, fp, width, height, depth,
                                   is_network_order, error))
        {
           g_set_error (error, G_FILE_ERROR, G_FILE_ERROR_FAILED,
                        _("Could not read image data from '%s'"),
                        gimp_file_get_utf8_name (file));
           fclose (fp);
           g_free (buffer);
           g_free (pixels);
           g_free (pixels_8);
           return NULL;
        }
      else if (bpp == 12 &&
          ! read_12bpc_packed (dpx_buffer, fp, width, height, depth,
                               is_network_order, error))
        {
           g_set_error (error, G_FILE_ERROR, G_FILE_ERROR_FAILED,
                        _("Could not read image data from '%s'"),
                        gimp_file_get_utf8_name (file));
           fclose (fp);
           g_free (buffer);
           g_free (pixels);
           g_free (pixels_8);
           return NULL;
        }
    }
  else
    {
      for (gint y = 0; y < height; y++)
        {
          gint read_index = 0;
          gint read_data  = buffer_length;

          read_index = fread (buffer, 4, read_data, fp);
          if (read_index != read_data)
            {
              g_set_error (error, G_FILE_ERROR, G_FILE_ERROR_FAILED,
                           _("Could not read image data from '%s'"),
                           gimp_file_get_utf8_name (file));
              fclose (fp);
              g_object_unref (dpx_buffer);
              g_free (buffer);
              g_free (pixels);
              g_free (pixels_8);

              return image;
            }

          if (bpp == 8)
            {
              read_8bpc_line (dpx_buffer, fp, buffer, read_data, depth, pixels_8,
                              (width * depth), packing, is_network_order, error);
            }
          else if (bpp == 10)
            {
              read_10bpc_line (dpx_buffer, buffer, read_data, depth, pixels,
                               (width * depth), packing, is_network_order,
                               error);
            }
          else if (bpp == 12)
            {
              read_12bpc_line (dpx_buffer, fp, buffer, read_data, depth, pixels,
                               (width * depth), packing, is_network_order, error);
            }
          else if (bpp == 16)
            {
              read_16bpc_line (dpx_buffer, fp, buffer, read_data, depth, pixels,
                               (width * depth), packing, is_network_order,
                               error);
            }

          if (bpp > 8)
            gegl_buffer_set (dpx_buffer, GEGL_RECTANGLE (0, y, width, 1), 0,
                             NULL, pixels, GEGL_AUTO_ROWSTRIDE);
          else
            gegl_buffer_set (dpx_buffer, GEGL_RECTANGLE (0, y, width, 1), 0,
                             NULL, pixels_8, GEGL_AUTO_ROWSTRIDE);
        }
    }

  g_object_unref (dpx_buffer);
  g_free (buffer);
  g_free (pixels);
  g_free (pixels_8);
  fclose (fp);

  return image;
}

/* Helper methods */

static gboolean
read_8bpc_line (GeglBuffer *buffer,
                FILE       *fp,
                guint      *data,
                guint       data_len,
                gint        depth,
                guchar     *pixels,
                guint       num_pixels,
                gushort     packing,
                gboolean    is_network_order,
                GError    **error)
{
  gint pixel_index = 0;

  for (gint long_index = 0; long_index < data_len; ++long_index)
    {
      guint t;

      if (is_network_order)
        {
          t = g_ntohl (data[long_index]);

          pixels[pixel_index]     = (guchar) ((t & 0xFF000000) >> 24) & 0xFF;
          pixels[pixel_index + 1] = (guchar) ((t & 0x00FF0000) >> 16) & 0xFF;
          pixels[pixel_index + 2] = (guchar) ((t & 0x0000FF00) >> 8) & 0xFF;
          pixels[pixel_index + 3] = (guchar) (t & 0x000000FF);
        }
      else
        {
          t = data[long_index];

          pixels[pixel_index + 3] = (guchar) ((t & 0xFF000000) >> 24) & 0xFF;
          pixels[pixel_index + 2] = (guchar) ((t & 0x00FF0000) >> 16) & 0xFF;
          pixels[pixel_index + 1] = (guchar) ((t & 0x0000FF00) >> 8) & 0xFF;
          pixels[pixel_index]     = (guchar) (t & 0x000000FF);
        }
      pixel_index += 4;
    }

  return TRUE;
}

static gboolean
read_10bpc_line (GeglBuffer *buffer,
                 guint      *data,
                 guint       data_len,
                 gint        depth,
                 gushort    *pixels,
                 guint       num_pixels,
                 gushort     packing,
                 gboolean    is_network_order,
                 GError    **error)
{
  gint pixel_index = 0;

  for (gint long_index = 0; long_index < data_len; ++long_index)
    {
      guint t;

      if (is_network_order)
        t = g_ntohl (data[long_index]);
      else
        t = data[long_index];

      t = t >> 2;
      pixels[pixel_index + 2] = ((gushort) t & 0x3FF) << 6;
      t = t >> 10;
      pixels[pixel_index + 1] = ((gushort) t & 0x3FF) << 6;
      t = t >> 10;
      pixels[pixel_index]     = ((gushort) t & 0x3FF) << 6;

      pixel_index += 3;
    }

  return TRUE;
}

static gboolean
read_10bpc_packed (GeglBuffer *buffer,
                   FILE       *fp,
                   guint       width,
                   guint       height,
                   gint        depth,
                   gboolean    is_network_order,
                   GError    **error)
{
  gsize    current;
  gsize    data_len;
  gsize    num_pixels;
  gsize    pixel_len;
  guint   *data;
  gushort *pixels;
  guint    pixel_index = 0;
  guint    leftover    = 0;
  gint     shift       = 0;
  guint    mask        = 0x3FF;
  guint    odd_offset  = 0;

  current = ftell (fp);
  fseek (fp, 0, SEEK_END);
  data_len = ftell (fp);
  fseek (fp, current, SEEK_SET);

  data_len -= current;
  data = g_try_malloc0 (data_len);
  if (data == NULL)
    return FALSE;

  data_len /= 4;
  if (fread (data, 4, data_len, fp) == 0                    ||
      ! g_size_checked_mul (&num_pixels, width, height)     ||
      ! g_size_checked_mul (&num_pixels, num_pixels, depth) ||
      ! g_size_checked_mul (&pixel_len, num_pixels, 2)      ||
      ! g_size_checked_add (&pixel_len, pixel_len, 8))
   {
     g_free (data);
     return FALSE;
   }

  pixels = g_try_malloc0 (pixel_len);
  if (pixels == NULL)
    {
      g_free (data);
      return FALSE;
    }

  for (gint long_index = 0; long_index < data_len; ++long_index)
    {
      guint t;

      if (is_network_order)
        {
          t = g_ntohl (data[long_index]);

          /* Get remaining bytes from prior run */
          leftover += ((gushort) t & mask) << shift;
          pixels[pixel_index++] = (leftover & 0x3FF) << 6;
          t = t >> (10 - shift);

          /* If the dimensions of the image are odd, the remaining
           * packed bits are not part of the image and should be
           * skipped */
          odd_offset++;
          if (odd_offset >= (width * depth))
            {
              odd_offset = 0;
              shift      = 0;
              mask       = 0x3FF;
              leftover   = 0;
              continue;
            }

          /* Read remaining 10 bit pixel values */
          pixels[pixel_index++]   = ((gushort) t & 0x3FF) << 6;
          t = t >> 10;
          pixels[pixel_index++] = ((gushort) t & 0x3FF) << 6;
          t = t >> 10;
          leftover = (gushort) t;

          odd_offset  += 2;
          shift       += 2;
          mask        /= 4.0f;
          if (shift > 8)
            {
              shift = 0;
              mask  = 0x3FF;

              /* Copy the last leftover value into the pixel array */
              pixels[pixel_index++] = ((gushort) t & 0x3FF) << 6;
              leftover = 0;
              odd_offset++;
            }

          if (odd_offset >= (width * depth))
            {
              shift      = 0;
              mask       = 0x3FF;
              leftover   = 0;
              odd_offset = 0;
              pixel_index--;
            }
        }
    }

  gegl_buffer_set (buffer, GEGL_RECTANGLE (0, 0, width, height), 0,
                   NULL, pixels, GEGL_AUTO_ROWSTRIDE);

  return TRUE;
}

static gboolean
read_12bpc_line (GeglBuffer *buffer,
                 FILE       *fp,
                 guint      *data,
                 guint       data_len,
                 gint        depth,
                 gushort    *pixels,
                 guint       num_pixels,
                 gushort     packing,
                 gboolean    is_network_order,
                 GError    **error)
{
  gint pixel_index = 0;

  for (gint long_index = 0; long_index < data_len; ++long_index)
    {
      guint t;

      if (is_network_order)
        {
          t = g_ntohl (data[long_index]);

          t = t >> 4;
          pixels[pixel_index + 1] = ((gushort) t & 0xFFF) << 4;
          t = t >> 16;
          pixels[pixel_index]     = ((gushort) t & 0xFFF) << 4;
        }
      else
        {
          t = data[long_index];

          t = t >> 4;
          pixels[pixel_index]     = ((gushort) t & 0xFFF) << 4;
          t = t >> 16;
          pixels[pixel_index + 1] = ((gushort) t & 0xFFF) << 4;
        }
      pixel_index += 2;
    }

  return TRUE;
}

static gboolean
read_12bpc_packed (GeglBuffer *buffer,
                   FILE       *fp,
                   guint       width,
                   guint       height,
                   gint        depth,
                   gboolean    is_network_order,
                   GError    **error)
{
  gsize    current;
  gsize    data_len;
  gsize    num_pixels;
  gsize    pixel_len;
  guint   *data;
  gushort *pixels;
  guint    pixel_index = 0;
  guint    leftover    = 0;
  gint     shift       = 12;
  guint    mask        = 1;
  guint    odd_offset  = 0;

  current = ftell (fp);
  fseek (fp, 0, SEEK_END);
  data_len = ftell (fp);
  fseek (fp, current, SEEK_SET);

  data_len -= current;
  data = g_try_malloc0 (data_len);
  if (data == NULL)
    return FALSE;

  data_len /= 4;
  if (fread (data, 4, data_len, fp) == 0                    ||
      ! g_size_checked_mul (&num_pixels, width, height)     ||
      ! g_size_checked_mul (&num_pixels, num_pixels, depth) ||
      ! g_size_checked_mul (&pixel_len, num_pixels, 2)      ||
      ! g_size_checked_add (&pixel_len, pixel_len, 8))
   {
     g_free (data);
     return FALSE;
   }

  pixels = g_try_malloc0 (pixel_len);
  if (pixels == NULL)
    {
      g_free (data);
      return FALSE;
    }

  for (gint long_index = 0; long_index < data_len; ++long_index)
    {
      guint t;

      if (is_network_order)
        {
          t = g_ntohl (data[long_index]);

          /* Get remaining bytes from prior run */
          if (shift < 12)
            {
              leftover += ((gushort) t & mask) << shift;
              pixels[pixel_index++] = (leftover & 0xFFF) << 4;
              t = t >> (12 - shift);

              /* If the dimensions of the image are odd, the remaining
               * packed bits are not part of the image and should be
               * skipped */
              odd_offset++;
              if (odd_offset >= (width * depth))
                {
                  odd_offset = 0;
                  shift      = 12;
                  mask       = 0;
                  continue;
                }
            }

          /* Read remaining 12 bit pixel values */
          pixels[pixel_index++] = ((gushort) t & 0xFFF) << 4;
          t = t >> 12;
          pixels[pixel_index++] = ((gushort) t & 0xFFF) << 4;
          t = t >> 12;
          leftover = (gushort) t;

          odd_offset += 2;
          shift      -= 4;
          mask       = (mask << 4) + 0xF;
          if (shift == 0)
            {
              shift = 12;
              mask  = 0;
            }

          if (odd_offset >= (width * depth))
            odd_offset = 0;

          if (pixel_index + 3 > num_pixels)
            break;
        }
    }

  gegl_buffer_set (buffer, GEGL_RECTANGLE (0, 0, width, height), 0,
                   NULL, pixels, GEGL_AUTO_ROWSTRIDE);

  return TRUE;
}

static gboolean
read_16bpc_line (GeglBuffer *buffer,
                 FILE       *fp,
                 guint      *data,
                 guint       data_len,
                 gint        depth,
                 gushort    *pixels,
                 guint       num_pixels,
                 gushort     packing,
                 gboolean    is_network_order,
                 GError    **error)
{
  gint pixel_index = 0;

  for (gint long_index = 0; long_index < data_len; ++long_index)
    {
      guint t;

      if (is_network_order)
        {
          t = g_ntohl (data[long_index]);

          pixels[pixel_index]     = (gushort) ((t >> 16) & 0xFFFF);
          pixels[pixel_index + 1] = (gushort) (t & 0xFFFF);
        }
      else
        {
          t = data[long_index];

          pixels[pixel_index + 1] = (gushort) ((t >> 16) & 0xFFFF);
          pixels[pixel_index]     = (gushort) (t & 0xFFFF);
        }
      pixel_index += 2;
    }

  return TRUE;
}

/* --- end plug-ins/field-io/file-cin/dpx-lib.c --- */

/* --- begin plug-ins/field-io/file-cin/file-cin.c --- */
/* AmmoOS Image - The AmmoOS Field Image Research
 * Copyright (C) 1995 Spencer Kimball and Peter Mattis
 *
 * Cineon/DPX file plugin
 * reading and writing code Copyright (C) 1997 Peter Kirchgessner
 * e-mail: peter@kirchgessner.net, WWW: http://www.kirchgessner.net
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

#include "config.h"

#include <math.h>
#include <string.h>
#include <errno.h>

#include <libgimp/ammoos.h>
#include <libgimp/gimpui.h>

#include "cineon-lib.h"
#include "dpx-lib.h"

#include "libgimp/stdplugins-intl.h"


#define LOAD_PROC       "file-cin-load"
#define EXPORT_PROC     "file-cin-export"
#define LOAD_DPX_PROC   "file-dpx-load"
#define EXPORT_DPX_PROC "file-dpx-export"
#define PLUG_IN_BINARY  "file-cin"
#define PLUG_IN_ROLE    "ammoos-file-cin"


typedef struct _Cineon      Cineon;
typedef struct _CineonClass CineonClass;

struct _Cineon
{
  GimpPlugIn      parent_instance;
};

struct _CineonClass
{
  GimpPlugInClass parent_class;
};


#define CINEON_TYPE  (cineon_get_type ())
#define CINEON(obj) (G_TYPE_CHECK_INSTANCE_CAST ((obj), CINEON_TYPE, Cineon))

GType                   cineon_get_type         (void) G_GNUC_CONST;

static GList          * cineon_query_procedures (GimpPlugIn            *plug_in);
static GimpProcedure  * cineon_create_procedure (GimpPlugIn            *plug_in,
                                                 const gchar           *name);

static GimpValueArray * cineon_load             (GimpProcedure         *procedure,
                                                 GimpRunMode            run_mode,
                                                 GFile                 *file,
                                                 GimpMetadata          *metadata,
                                                 GimpMetadataLoadFlags *flags,
                                                 GimpProcedureConfig   *config,
                                                 gpointer               run_data);

static GimpValueArray * dpx_load                (GimpProcedure         *procedure,
                                                 GimpRunMode            run_mode,
                                                 GFile                 *file,
                                                 GimpMetadata          *metadata,
                                                 GimpMetadataLoadFlags *flags,
                                                 GimpProcedureConfig   *config,
                                                 gpointer               run_data);

static GimpImage      * load_image              (GFile                 *file,
                                                 GObject               *config,
                                                 gboolean               is_cineon,
                                                 GError               **error);



G_DEFINE_TYPE (Cineon, cineon, GIMP_TYPE_PLUG_IN)

GIMP_MAIN (CINEON_TYPE)
DEFINE_STD_SET_I18N


static void
cineon_class_init (CineonClass *klass)
{
  GimpPlugInClass *plug_in_class = GIMP_PLUG_IN_CLASS (klass);

  plug_in_class->query_procedures = cineon_query_procedures;
  plug_in_class->create_procedure = cineon_create_procedure;
  plug_in_class->set_i18n         = STD_SET_I18N;
}

static void
cineon_init (Cineon *cineon)
{
}

static GList *
cineon_query_procedures (GimpPlugIn *plug_in)
{
  GList *list = NULL;

  list = g_list_append (list, g_strdup (LOAD_PROC));
  list = g_list_append (list, g_strdup (LOAD_DPX_PROC));

  return list;
}

static GimpProcedure *
cineon_create_procedure (GimpPlugIn  *plug_in,
                         const gchar *name)
{
  GimpProcedure *procedure = NULL;

  if (! strcmp (name, LOAD_PROC))
    {
      procedure = gimp_load_procedure_new (plug_in, name,
                                           GIMP_PDB_PROC_TYPE_PLUGIN,
                                           cineon_load, NULL, NULL);

      gimp_procedure_set_menu_label (procedure,
                                     _("Kodak Cineon"));

      gimp_procedure_set_documentation (procedure,
                                        _("Load file of the Kodak Cineon file format"),
                                        _("Load file of the Kodak Cineon file format"),
                                        name);
      gimp_procedure_set_attribution (procedure,
                                      "David Hodson",
                                      "David Hodson",
                                      "1999 - 2002");

      gimp_file_procedure_set_mime_types (GIMP_FILE_PROCEDURE (procedure),
                                          "image/cineon");
      gimp_file_procedure_set_extensions (GIMP_FILE_PROCEDURE (procedure),
                                          "cin");
      gimp_file_procedure_set_magics (GIMP_FILE_PROCEDURE (procedure),
                                      "0,string,\xD7\x5F\x2A\x80,"
                                      "0,string,\x80\x2A\x5F\xD7");

    }
  else if (! strcmp (name, LOAD_DPX_PROC))
    {
      procedure = gimp_load_procedure_new (plug_in, name,
                                           GIMP_PDB_PROC_TYPE_PLUGIN,
                                           dpx_load, NULL, NULL);

      gimp_procedure_set_menu_label (procedure,
                                     _("DPX"));

      gimp_procedure_set_documentation (procedure,
                                        _("Load file of the DPX file format"),
                                        _("Load file of the Digital Picture "
                                          "Exchange file format"),
                                        name);
      gimp_procedure_set_attribution (procedure,
                                      "David Hodson",
                                      "David Hodson",
                                      "1999 - 2002");

      gimp_file_procedure_set_mime_types (GIMP_FILE_PROCEDURE (procedure),
                                          "image/dpx");
      gimp_file_procedure_set_extensions (GIMP_FILE_PROCEDURE (procedure),
                                          "dpx");
      gimp_file_procedure_set_magics (GIMP_FILE_PROCEDURE (procedure),
                                      "0,string,\x53\x44\x50\x58,"
                                      "0,string,\x58\x50\x44\x53");

    }

  return procedure;
}

static GimpValueArray *
cineon_load (GimpProcedure         *procedure,
             GimpRunMode            run_mode,
             GFile                 *file,
             GimpMetadata          *metadata,
             GimpMetadataLoadFlags *flags,
             GimpProcedureConfig   *config,
             gpointer               run_data)
{
  GimpValueArray *return_vals;
  GimpImage      *image = NULL;
  GError         *error = NULL;

  gegl_init (NULL, NULL);

  image = load_image (file, G_OBJECT (config), TRUE, &error);

  if (! image)
    return gimp_procedure_new_return_values (procedure,
                                             GIMP_PDB_EXECUTION_ERROR,
                                             error);

  return_vals = gimp_procedure_new_return_values (procedure,
                                                  GIMP_PDB_SUCCESS,
                                                  NULL);

  GIMP_VALUES_SET_IMAGE (return_vals, 1, image);

  return return_vals;
}

static GimpValueArray *
dpx_load (GimpProcedure         *procedure,
          GimpRunMode            run_mode,
          GFile                 *file,
          GimpMetadata          *metadata,
          GimpMetadataLoadFlags *flags,
          GimpProcedureConfig   *config,
          gpointer               run_data)
{
  GimpValueArray *return_vals;
  GimpImage      *image = NULL;
  GError         *error = NULL;

  gegl_init (NULL, NULL);

  image = load_image (file, G_OBJECT (config), FALSE, &error);

  if (! image)
    return gimp_procedure_new_return_values (procedure,
                                             GIMP_PDB_EXECUTION_ERROR,
                                             error);

  return_vals = gimp_procedure_new_return_values (procedure,
                                                  GIMP_PDB_SUCCESS,
                                                  NULL);

  GIMP_VALUES_SET_IMAGE (return_vals, 1, image);

  return return_vals;
}

static GimpImage *
load_image (GFile    *file,
            GObject  *config,
            gboolean  is_cineon,
            GError  **error)
{
  GimpImage *image = NULL;

  if (is_cineon)
    image = cineon_open (file, error);
  else
    image = dpx_open (file, error);

  return image;
}

/* --- end plug-ins/field-io/file-cin/file-cin.c --- */

/* --- begin plug-ins/field-io/file-dds/bc7.c --- */
/*
 * DDS AmmoOS Image plugin
 *
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public
 * License as published by the Free Software Foundation; either
 * version 2 of the License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; see the file COPYING.  If not, write to
 * the Free Software Foundation, 51 Franklin Street, Fifth Floor
 * Boston, MA 02110-1301, USA.
 */

/* ImageMagick's implementation of BC7 was referenced for our implementation.
 * The relevant commit: https://github.com/ImageMagick/ImageMagick/pull/4126/files
 */

#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <glib.h>

#include <libgimp/ammoos.h>

#include "bc7.h"

#define SWAP(a, b)  do { typeof(a) t; t = a; a = b; b = t; } while(0)

static guchar    get_bits             (const guchar *block,
                                       guchar       *start_bit,
                                       guchar        length);

static void      decode_rgba_channels (BC7_colors   *colors,
                                       guchar       *src,
                                       guint         mode,
                                       guchar       *start);

static gboolean  is_pixel_anchor      (guchar        subset_index,
                                       guint         precision,
                                       guchar        pixel_index,
                                       guint         partition_id);


gint
bc7_decompress (guchar *src,
                guint   size,
                guchar *block)
{
  /* BC7 blocks are always 16 bytes */
  guchar     s[16];
  BC7_colors colors;
  guchar     rgb_indexes[16];
  guchar     alpha_indexes[16];
  guchar     subset_indexes[16];
  guchar     rgba[4];
  guint      mode             = 0;
  guint      subset_count     = 0;
  guint      partition_id     = 0;
  guint      swap             = 0;
  guint      selector         = 0;
  guchar     current_bit      = 0;
  guint      i_precision      = 0;
  guint      no_sel_precision = 0;

  for (gint i = 0; i < 16; i++)
    s[i] = src[i];

  /* BC7 blocks are read from the last bit of the last byte, backwards.
   * The mode is determined by the first 1 bit encountered. For instance,
   * 1 is mode 0, 10 is mode 1, 100 is mode 2, and so on. */
  while (current_bit <= 8 && ! get_bits (s, &current_bit, 1))
    {
      continue;
    }
  mode = current_bit - 1;

  if (mode > 7)
    return 0;

  /* For modes that support partitions, we start counting
   * from left of the mode bit, and get the partition ID.
   * The size of the partition ID is defined by the mode. */
  subset_count = mode_info[mode].subset_count;
  if (subset_count > 1)
    {
      partition_id = get_bits (s, &current_bit,
                               mode_info[mode].partition_bits);

      if (partition_id > 63)
        return 0;
    }

  /* Mode 4 and 5 might swap channels for better compression. 2 bits after the mode bit
   * indicate which were swapped (if any) */
  if (mode == 4 || mode == 5)
    swap = get_bits (s, &current_bit, 2);

  /* Mode 4 also has a single selector bit, to the left of its swap bits.
   * This bit determines where the alpha channel indexes are located. */
  if (mode == 4)
    selector = get_bits (s, &current_bit, 1);

  /* Channel values are stored in RnGnBn(An) format, where the mode determines
   * how many bits of precision and how many values are stored. */
  decode_rgba_channels (&colors, s, mode, &current_bit);

  /* Next, we get the indexes to assemble pixels from the channel values. */
  i_precision      = mode_info[mode].index_precision;
  no_sel_precision = mode_info[mode].no_sel_precision;

  if (mode == 4 && selector)
    {
      i_precision      = 3;
      alpha_indexes[0] = get_bits (s, &current_bit, 1);

      for (gint i = 1; i < 16; i++)
        alpha_indexes[i] = get_bits (s, &current_bit, 2);
    }

  /* First, calculate the RGB channel indexes based on the partition ID
   * and the number of subsets.  */
  for (gint i = 0; i < 16; i++)
    {
      guint precision = i_precision;

      if (subset_count == 2)
        subset_indexes[i] = partition_table[0][partition_id][i];
      else if (subset_count == 3)
        subset_indexes[i] = partition_table[1][partition_id][i];
      else
        subset_indexes[i] = 0;

      if (is_pixel_anchor (subset_indexes[i], subset_count, i, partition_id))
        precision--;

      rgb_indexes[i]= get_bits (s, &current_bit, precision);
    }

  if (mode == 5 || (mode == 4 && ! selector))
    {
      alpha_indexes[0] = get_bits (s, &current_bit, no_sel_precision - 1);

      for (gint i = 1; i < 16; i++)
        alpha_indexes[i] = get_bits (s, &current_bit, no_sel_precision);
    }

  /* Create pixels from subset indexes */
  for (gint i = 0; i < 16; i++)
    {
      guint  weight;
      guint  c0 = 2 * subset_indexes[i];
      guint  c1 = (2 * subset_indexes[i]) + 1;

      if (i_precision == 2)
        weight = weight_2[rgb_indexes[i]];
      else if (i_precision == 3)
        weight = weight_3[rgb_indexes[i]];
      else
        weight = weight_4[rgb_indexes[i]];

      rgba[0] = ((64 - weight) * colors.r[c0] + weight * colors.r[c1] + 32) >> 6;
      rgba[1] = ((64 - weight) * colors.g[c0] + weight * colors.g[c1] + 32) >> 6;
      rgba[2] = ((64 - weight) * colors.b[c0] + weight * colors.b[c1] + 32) >> 6;

      if (mode == 4 || mode == 5)
        {
          weight = weight_2[alpha_indexes[i]];

          if (mode == 4 && ! selector)
            weight = weight_3[alpha_indexes[i]];
        }
      rgba[3] = ((64 - weight) * colors.a[c0] + weight * colors.a[c1] + 32) >> 6;

      switch (swap)
        {
          case 1:
            SWAP (rgba[3], rgba[0]);
            break;
          case 2:
            SWAP (rgba[3], rgba[1]);
            break;
          case 3:
            SWAP (rgba[3], rgba[2]);
            break;
          default:
            break;
         }

      for (gint j = 0; j < 4; j++)
        block[(i * 4) + j] = rgba[j];
    }

  return 1;
}


/* Private Functions */

static guchar
get_bits (const guchar *block,
          guchar       *start_bit,
          guchar        length)
{
  guchar bits;
  guint  index;
  guint  base;
  guint  first_bits;
  guint  next_bits;

  index = (*start_bit) >> 3;
  base  = (*start_bit) - (index << 3);

  if (index > 15)
    return 0;

  if (base + length > 8)
    {
      first_bits = 8 - base;
      next_bits  = length - first_bits;

      bits = block[index] >> base;
      bits |= (block[index + 1] & ((1 << next_bits) - 1)) << first_bits;
    }
  else
    {
      bits = (block[index] >> base) & ((1 << length) - 1);
    }
  (*start_bit) += length;

  return bits;
}

static void
decode_rgba_channels (BC7_colors *colors,
                      guchar     *src,
                      guint       mode,
                      guchar     *start)
{
  guint channel_count   = mode_info[mode].subset_count * 2;
  guint rgb_precision   = mode_info[mode].rgb_precision;
  guint alpha_precision = mode_info[mode].alpha_precision;

  /* Get RGB channel values */
  for (gint i = 0; i < channel_count; i++)
    colors->r[i] = get_bits (src, start, rgb_precision);

  for (gint i = 0; i < channel_count; i++)
    colors->g[i] = get_bits (src, start, rgb_precision);

  for (gint i = 0; i < channel_count; i++)
    colors->b[i] = get_bits (src, start, rgb_precision);

  /* Modes 4 - 7 also have alpha values */
  if (alpha_precision)
    {
      for (gint i = 0; i < channel_count; i++)
        colors->a[i] = get_bits (src, start, alpha_precision);
    }
  else
    {
      for (gint i = 0; i < channel_count; i++)
        colors->a[i] = 255;
    }

  /* Modes 0, 1, 3, 6, and 7 have P-bits, which increase the precision
   * by 1. */
  if (mode_info[mode].p_bit_count)
    {
      rgb_precision++;
      if (alpha_precision)
        alpha_precision++;

      /* P-bits are added at the least significant bit, so
       * we have to shift existing channel values over by 1 */
      for (gint i = 0; i < channel_count; i++)
        {
          colors->r[i] <<= 1;
          colors->g[i] <<= 1;
          colors->b[i] <<= 1;
          if (alpha_precision)
            colors->a[i] <<= 1;
        }

      if (mode == 1)
        {
          guint p_bit_1 = get_bits (src, start, 1);
          guint p_bit_2 = get_bits (src, start, 1);

          for (gint i = 0; i < 2; i++)
            {
              colors->r[i] |= p_bit_1;
              colors->g[i] |= p_bit_1;
              colors->b[i] |= p_bit_1;

              colors->r[i + 2] |= p_bit_2;
              colors->g[i + 2] |= p_bit_2;
              colors->b[i + 2] |= p_bit_2;
            }
        }
      else
        {
          for (gint i = 0; i < channel_count; i++)
            {
              guint p_bit = get_bits (src, start, 1);

              colors->r[i] |= p_bit;
              colors->g[i] |= p_bit;
              colors->b[i] |= p_bit;
              if (alpha_precision)
                colors->a[i] |= p_bit;
            }
        }
    }

  /* Normalize all channel values to 8 bits */
  for (gint i = 0; i < channel_count; i++)
    {
      colors->r[i] <<= (8 - rgb_precision);
      colors->g[i] <<= (8 - rgb_precision);
      colors->b[i] <<= (8 - rgb_precision);

      colors->r[i] = colors->r[i] | (colors->r[i] >> rgb_precision);
      colors->g[i] = colors->g[i] | (colors->g[i] >> rgb_precision);
      colors->b[i] = colors->b[i] | (colors->b[i] >> rgb_precision);

      if (alpha_precision)
        {
          colors->a[i] <<= (8 - alpha_precision);
          colors->a[i] = colors->a[i] | (colors->a[i] >> alpha_precision);
        }
    }
}

static gboolean
is_pixel_anchor (guchar  subset_index,
                 guint   precision,
                 guchar  pixel_index,
                 guint   partition_id)
{
  guint table_index;

  if (subset_index == 0)
    table_index = 0;
  else if (subset_index == 1 && precision == 2)
    table_index = 1;
  else if (subset_index == 1 && precision == 3)
    table_index = 2;
  else
    table_index = 3;

  if (anchor_index_table[table_index][partition_id] == pixel_index)
    return TRUE;

  return FALSE;
}

/* --- end plug-ins/field-io/file-dds/bc7.c --- */

/* --- begin plug-ins/field-io/file-dds/bc7enc_rdo/bc7enc.c --- */
/* File: bc7enc.c - Richard Geldreich, Jr. 3/31/2020 - MIT license or public domain (see end of file)
 * Currently supports modes 1, 6 for RGB blocks, and modes 5, 6, 7 for RGBA blocks. */
#include "bc7enc.h"
#include <math.h>
#include <memory.h>
#include <assert.h>
#include <limits.h>

typedef struct
{
    uint32_t m_mode;
    uint32_t m_partition;
    uint8_t m_selectors[16];
    uint8_t m_alpha_selectors[16];
    color_rgba m_low[3];
    color_rgba m_high[3];
    uint32_t m_pbits[3][2];
    uint32_t m_rotation;
    uint32_t m_index_selector;
} bc7_optimization_results;

void encode_bc7_block (void* pBlock, const bc7_optimization_results* pResults);

/* Helpers */
static inline int32_t clampi(int32_t value, int32_t low, int32_t high) { if (value < low) value = low; else if (value > high) value = high; return value; }
static inline float clampf(float value, float low, float high) { if (value < low) value = low; else if (value > high) value = high; return value; }
static inline float saturate(float value) { return clampf(value, 0, 1.0f); }
/*static inline uint8_t minimumub(uint8_t a, uint8_t b) { return (a < b) ? a : b; }*/
static inline int32_t minimumi(int32_t a, int32_t b) { return (a < b) ? a : b; }
static inline uint32_t minimumu(uint32_t a, uint32_t b) { return (a < b) ? a : b; }
static inline float minimumf(float a, float b) { return (a < b) ? a : b; }
/*static inline uint8_t maximumub(uint8_t a, uint8_t b) { return (a > b) ? a : b; }*/
static inline uint32_t maximumu(uint32_t a, uint32_t b) { return (a > b) ? a : b; }
/*static inline int32_t maximumi(int32_t a, int32_t b) { return (a > b) ? a : b; }*/
static inline float maximumf(float a, float b) { return (a > b) ? a : b; }
static inline int squarei(int i) { return i * i; }
static inline float squaref(float i) { return i * i; }

static inline int32_t iabs32(int32_t v) { uint32_t msk = v >> 31; return (v ^ msk) - msk; }
static inline void swapu(uint32_t* a, uint32_t* b) { uint32_t t = *a; *a = *b; *b = t; }

typedef struct { float m_c[4]; } vec4F;

static inline color_rgba *color_quad_u8_set_clamped(color_rgba *pRes, int32_t r, int32_t g, int32_t b, int32_t a) { pRes->m_c[0] = (uint8_t)clampi(r, 0, 255); pRes->m_c[1] = (uint8_t)clampi(g, 0, 255); pRes->m_c[2] = (uint8_t)clampi(b, 0, 255); pRes->m_c[3] = (uint8_t)clampi(a, 0, 255); return pRes; }
static inline color_rgba *color_quad_u8_set(color_rgba *pRes, int32_t r, int32_t g, int32_t b, int32_t a) { assert((uint32_t)(r | g | b | a) <= 255); pRes->m_c[0] = (uint8_t)r; pRes->m_c[1] = (uint8_t)g; pRes->m_c[2] = (uint8_t)b; pRes->m_c[3] = (uint8_t)a; return pRes; }
static inline gboolean color_quad_u8_notequals(const color_rgba *pLHS, const color_rgba *pRHS) { return (pLHS->m_c[0] != pRHS->m_c[0]) || (pLHS->m_c[1] != pRHS->m_c[1]) || (pLHS->m_c[2] != pRHS->m_c[2]) || (pLHS->m_c[3] != pRHS->m_c[3]); }
static inline vec4F *vec4F_set_scalar(vec4F *pV, float x) { pV->m_c[0] = x; pV->m_c[1] = x; pV->m_c[2] = x; pV->m_c[3] = x; return pV; }
static inline vec4F *vec4F_set(vec4F *pV, float x, float y, float z, float w) { pV->m_c[0] = x; pV->m_c[1] = y; pV->m_c[2] = z; pV->m_c[3] = w; return pV; }
static inline vec4F *vec4F_saturate_in_place(vec4F *pV) { pV->m_c[0] = saturate(pV->m_c[0]); pV->m_c[1] = saturate(pV->m_c[1]); pV->m_c[2] = saturate(pV->m_c[2]); pV->m_c[3] = saturate(pV->m_c[3]); return pV; }
static inline vec4F vec4F_saturate(const vec4F *pV) { vec4F res; res.m_c[0] = saturate(pV->m_c[0]); res.m_c[1] = saturate(pV->m_c[1]); res.m_c[2] = saturate(pV->m_c[2]); res.m_c[3] = saturate(pV->m_c[3]); return res; }
static inline vec4F vec4F_from_color(const color_rgba *pC) { vec4F res; vec4F_set(&res, pC->m_c[0], pC->m_c[1], pC->m_c[2], pC->m_c[3]); return res; }
static inline vec4F vec4F_add(const vec4F *pLHS, const vec4F *pRHS) { vec4F res; vec4F_set(&res, pLHS->m_c[0] + pRHS->m_c[0], pLHS->m_c[1] + pRHS->m_c[1], pLHS->m_c[2] + pRHS->m_c[2], pLHS->m_c[3] + pRHS->m_c[3]); return res; }
static inline vec4F vec4F_sub(const vec4F *pLHS, const vec4F *pRHS) { vec4F res; vec4F_set(&res, pLHS->m_c[0] - pRHS->m_c[0], pLHS->m_c[1] - pRHS->m_c[1], pLHS->m_c[2] - pRHS->m_c[2], pLHS->m_c[3] - pRHS->m_c[3]); return res; }
static inline float vec4F_dot(const vec4F *pLHS, const vec4F *pRHS) { return pLHS->m_c[0] * pRHS->m_c[0] + pLHS->m_c[1] * pRHS->m_c[1] + pLHS->m_c[2] * pRHS->m_c[2] + pLHS->m_c[3] * pRHS->m_c[3]; }
static inline vec4F vec4F_mul(const vec4F *pLHS, float s) { vec4F res; vec4F_set(&res, pLHS->m_c[0] * s, pLHS->m_c[1] * s, pLHS->m_c[2] * s, pLHS->m_c[3] * s); return res; }
static inline vec4F *vec4F_normalize_in_place(vec4F *pV) { float s = pV->m_c[0] * pV->m_c[0] + pV->m_c[1] * pV->m_c[1] + pV->m_c[2] * pV->m_c[2] + pV->m_c[3] * pV->m_c[3]; if (s != 0.0f) { s = 1.0f / sqrtf(s); pV->m_c[0] *= s; pV->m_c[1] *= s; pV->m_c[2] *= s; pV->m_c[3] *= s; } return pV; }

/* Various BC7 tables */
static const uint32_t g_bc7_weights2[4] = { 0, 21, 43, 64 };
static const uint32_t g_bc7_weights3[8] = { 0, 9, 18, 27, 37, 46, 55, 64 };
static const uint32_t g_bc7_weights4[16] = { 0, 4, 9, 13, 17, 21, 26, 30, 34, 38, 43, 47, 51, 55, 60, 64 };
/* Precomputed weight constants used during least fit determination.
 * For each entry in g_bc7_weights[]: w * w, (1.0f - w) * w, (1.0f - w) * (1.0f - w), w */
static const float g_bc7_weights2x[4 * 4] = { 0.000000f, 0.000000f, 1.000000f, 0.000000f, 0.107666f, 0.220459f, 0.451416f, 0.328125f, 0.451416f, 0.220459f, 0.107666f, 0.671875f, 1.000000f, 0.000000f, 0.000000f, 1.000000f };
static const float g_bc7_weights3x[8 * 4] = { 0.000000f, 0.000000f, 1.000000f, 0.000000f, 0.019775f, 0.120850f, 0.738525f, 0.140625f, 0.079102f, 0.202148f, 0.516602f, 0.281250f, 0.177979f, 0.243896f, 0.334229f, 0.421875f, 0.334229f, 0.243896f, 0.177979f, 0.578125f, 0.516602f, 0.202148f,
    0.079102f, 0.718750f, 0.738525f, 0.120850f, 0.019775f, 0.859375f, 1.000000f, 0.000000f, 0.000000f, 1.000000f };
static const float g_bc7_weights4x[16 * 4] = { 0.000000f, 0.000000f, 1.000000f, 0.000000f, 0.003906f, 0.058594f, 0.878906f, 0.062500f, 0.019775f, 0.120850f, 0.738525f, 0.140625f, 0.041260f, 0.161865f, 0.635010f, 0.203125f, 0.070557f, 0.195068f, 0.539307f, 0.265625f, 0.107666f, 0.220459f,
    0.451416f, 0.328125f, 0.165039f, 0.241211f, 0.352539f, 0.406250f, 0.219727f, 0.249023f, 0.282227f, 0.468750f, 0.282227f, 0.249023f, 0.219727f, 0.531250f, 0.352539f, 0.241211f, 0.165039f, 0.593750f, 0.451416f, 0.220459f, 0.107666f, 0.671875f, 0.539307f, 0.195068f, 0.070557f, 0.734375f,
    0.635010f, 0.161865f, 0.041260f, 0.796875f, 0.738525f, 0.120850f, 0.019775f, 0.859375f, 0.878906f, 0.058594f, 0.003906f, 0.937500f, 1.000000f, 0.000000f, 0.000000f, 1.000000f };

static const uint8_t g_bc7_partition1[16] = { 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0 };
static const uint8_t g_bc7_partition2[64 * 16] =
{
    0,0,1,1,0,0,1,1,0,0,1,1,0,0,1,1,        0,0,0,1,0,0,0,1,0,0,0,1,0,0,0,1,        0,1,1,1,0,1,1,1,0,1,1,1,0,1,1,1,        0,0,0,1,0,0,1,1,0,0,1,1,0,1,1,1,        0,0,0,0,0,0,0,1,0,0,0,1,0,0,1,1,        0,0,1,1,0,1,1,1,0,1,1,1,1,1,1,1,        0,0,0,1,0,0,1,1,0,1,1,1,1,1,1,1,        0,0,0,0,0,0,0,1,0,0,1,1,0,1,1,1,
    0,0,0,0,0,0,0,0,0,0,0,1,0,0,1,1,        0,0,1,1,0,1,1,1,1,1,1,1,1,1,1,1,        0,0,0,0,0,0,0,1,0,1,1,1,1,1,1,1,        0,0,0,0,0,0,0,0,0,0,0,1,0,1,1,1,        0,0,0,1,0,1,1,1,1,1,1,1,1,1,1,1,        0,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1,        0,0,0,0,1,1,1,1,1,1,1,1,1,1,1,1,        0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1,
    0,0,0,0,1,0,0,0,1,1,1,0,1,1,1,1,        0,1,1,1,0,0,0,1,0,0,0,0,0,0,0,0,        0,0,0,0,0,0,0,0,1,0,0,0,1,1,1,0,        0,1,1,1,0,0,1,1,0,0,0,1,0,0,0,0,        0,0,1,1,0,0,0,1,0,0,0,0,0,0,0,0,        0,0,0,0,1,0,0,0,1,1,0,0,1,1,1,0,        0,0,0,0,0,0,0,0,1,0,0,0,1,1,0,0,        0,1,1,1,0,0,1,1,0,0,1,1,0,0,0,1,
    0,0,1,1,0,0,0,1,0,0,0,1,0,0,0,0,        0,0,0,0,1,0,0,0,1,0,0,0,1,1,0,0,        0,1,1,0,0,1,1,0,0,1,1,0,0,1,1,0,        0,0,1,1,0,1,1,0,0,1,1,0,1,1,0,0,        0,0,0,1,0,1,1,1,1,1,1,0,1,0,0,0,        0,0,0,0,1,1,1,1,1,1,1,1,0,0,0,0,        0,1,1,1,0,0,0,1,1,0,0,0,1,1,1,0,        0,0,1,1,1,0,0,1,1,0,0,1,1,1,0,0,
    0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,        0,0,0,0,1,1,1,1,0,0,0,0,1,1,1,1,        0,1,0,1,1,0,1,0,0,1,0,1,1,0,1,0,        0,0,1,1,0,0,1,1,1,1,0,0,1,1,0,0,        0,0,1,1,1,1,0,0,0,0,1,1,1,1,0,0,        0,1,0,1,0,1,0,1,1,0,1,0,1,0,1,0,        0,1,1,0,1,0,0,1,0,1,1,0,1,0,0,1,        0,1,0,1,1,0,1,0,1,0,1,0,0,1,0,1,
    0,1,1,1,0,0,1,1,1,1,0,0,1,1,1,0,        0,0,0,1,0,0,1,1,1,1,0,0,1,0,0,0,        0,0,1,1,0,0,1,0,0,1,0,0,1,1,0,0,        0,0,1,1,1,0,1,1,1,1,0,1,1,1,0,0,        0,1,1,0,1,0,0,1,1,0,0,1,0,1,1,0,        0,0,1,1,1,1,0,0,1,1,0,0,0,0,1,1,        0,1,1,0,0,1,1,0,1,0,0,1,1,0,0,1,        0,0,0,0,0,1,1,0,0,1,1,0,0,0,0,0,
    0,1,0,0,1,1,1,0,0,1,0,0,0,0,0,0,        0,0,1,0,0,1,1,1,0,0,1,0,0,0,0,0,        0,0,0,0,0,0,1,0,0,1,1,1,0,0,1,0,        0,0,0,0,0,1,0,0,1,1,1,0,0,1,0,0,        0,1,1,0,1,1,0,0,1,0,0,1,0,0,1,1,        0,0,1,1,0,1,1,0,1,1,0,0,1,0,0,1,        0,1,1,0,0,0,1,1,1,0,0,1,1,1,0,0,        0,0,1,1,1,0,0,1,1,1,0,0,0,1,1,0,
    0,1,1,0,1,1,0,0,1,1,0,0,1,0,0,1,        0,1,1,0,0,0,1,1,0,0,1,1,1,0,0,1,        0,1,1,1,1,1,1,0,1,0,0,0,0,0,0,1,        0,0,0,1,1,0,0,0,1,1,1,0,0,1,1,1,        0,0,0,0,1,1,1,1,0,0,1,1,0,0,1,1,        0,0,1,1,0,0,1,1,1,1,1,1,0,0,0,0,        0,0,1,0,0,0,1,0,1,1,1,0,1,1,1,0,        0,1,0,0,0,1,0,0,0,1,1,1,0,1,1,1
};

static const uint8_t g_bc7_partition3[64 * 16] =
{
    0,0,1,1,0,0,1,1,0,2,2,1,2,2,2,2,        0,0,0,1,0,0,1,1,2,2,1,1,2,2,2,1,        0,0,0,0,2,0,0,1,2,2,1,1,2,2,1,1,        0,2,2,2,0,0,2,2,0,0,1,1,0,1,1,1,        0,0,0,0,0,0,0,0,1,1,2,2,1,1,2,2,        0,0,1,1,0,0,1,1,0,0,2,2,0,0,2,2,        0,0,2,2,0,0,2,2,1,1,1,1,1,1,1,1,        0,0,1,1,0,0,1,1,2,2,1,1,2,2,1,1,
    0,0,0,0,0,0,0,0,1,1,1,1,2,2,2,2,        0,0,0,0,1,1,1,1,1,1,1,1,2,2,2,2,        0,0,0,0,1,1,1,1,2,2,2,2,2,2,2,2,        0,0,1,2,0,0,1,2,0,0,1,2,0,0,1,2,        0,1,1,2,0,1,1,2,0,1,1,2,0,1,1,2,        0,1,2,2,0,1,2,2,0,1,2,2,0,1,2,2,        0,0,1,1,0,1,1,2,1,1,2,2,1,2,2,2,        0,0,1,1,2,0,0,1,2,2,0,0,2,2,2,0,
    0,0,0,1,0,0,1,1,0,1,1,2,1,1,2,2,        0,1,1,1,0,0,1,1,2,0,0,1,2,2,0,0,        0,0,0,0,1,1,2,2,1,1,2,2,1,1,2,2,        0,0,2,2,0,0,2,2,0,0,2,2,1,1,1,1,        0,1,1,1,0,1,1,1,0,2,2,2,0,2,2,2,        0,0,0,1,0,0,0,1,2,2,2,1,2,2,2,1,        0,0,0,0,0,0,1,1,0,1,2,2,0,1,2,2,        0,0,0,0,1,1,0,0,2,2,1,0,2,2,1,0,
    0,1,2,2,0,1,2,2,0,0,1,1,0,0,0,0,        0,0,1,2,0,0,1,2,1,1,2,2,2,2,2,2,        0,1,1,0,1,2,2,1,1,2,2,1,0,1,1,0,        0,0,0,0,0,1,1,0,1,2,2,1,1,2,2,1,        0,0,2,2,1,1,0,2,1,1,0,2,0,0,2,2,        0,1,1,0,0,1,1,0,2,0,0,2,2,2,2,2,        0,0,1,1,0,1,2,2,0,1,2,2,0,0,1,1,        0,0,0,0,2,0,0,0,2,2,1,1,2,2,2,1,
    0,0,0,0,0,0,0,2,1,1,2,2,1,2,2,2,        0,2,2,2,0,0,2,2,0,0,1,2,0,0,1,1,        0,0,1,1,0,0,1,2,0,0,2,2,0,2,2,2,        0,1,2,0,0,1,2,0,0,1,2,0,0,1,2,0,        0,0,0,0,1,1,1,1,2,2,2,2,0,0,0,0,        0,1,2,0,1,2,0,1,2,0,1,2,0,1,2,0,        0,1,2,0,2,0,1,2,1,2,0,1,0,1,2,0,        0,0,1,1,2,2,0,0,1,1,2,2,0,0,1,1,
    0,0,1,1,1,1,2,2,2,2,0,0,0,0,1,1,        0,1,0,1,0,1,0,1,2,2,2,2,2,2,2,2,        0,0,0,0,0,0,0,0,2,1,2,1,2,1,2,1,        0,0,2,2,1,1,2,2,0,0,2,2,1,1,2,2,        0,0,2,2,0,0,1,1,0,0,2,2,0,0,1,1,        0,2,2,0,1,2,2,1,0,2,2,0,1,2,2,1,        0,1,0,1,2,2,2,2,2,2,2,2,0,1,0,1,        0,0,0,0,2,1,2,1,2,1,2,1,2,1,2,1,
    0,1,0,1,0,1,0,1,0,1,0,1,2,2,2,2,        0,2,2,2,0,1,1,1,0,2,2,2,0,1,1,1,        0,0,0,2,1,1,1,2,0,0,0,2,1,1,1,2,        0,0,0,0,2,1,1,2,2,1,1,2,2,1,1,2,        0,2,2,2,0,1,1,1,0,1,1,1,0,2,2,2,        0,0,0,2,1,1,1,2,1,1,1,2,0,0,0,2,        0,1,1,0,0,1,1,0,0,1,1,0,2,2,2,2,        0,0,0,0,0,0,0,0,2,1,1,2,2,1,1,2,
    0,1,1,0,0,1,1,0,2,2,2,2,2,2,2,2,        0,0,2,2,0,0,1,1,0,0,1,1,0,0,2,2,        0,0,2,2,1,1,2,2,1,1,2,2,0,0,2,2,        0,0,0,0,0,0,0,0,0,0,0,0,2,1,1,2,        0,0,0,2,0,0,0,1,0,0,0,2,0,0,0,1,        0,2,2,2,1,2,2,2,0,2,2,2,1,2,2,2,        0,1,0,1,2,2,2,2,2,2,2,2,2,2,2,2,        0,1,1,1,2,0,1,1,2,2,0,1,2,2,2,0,
};

static const uint8_t g_bc7_table_anchor_index_third_subset_1[64] =
{
    3, 3,15,15, 8, 3,15,15,     8, 8, 6, 6, 6, 5, 3, 3,     3, 3, 8,15, 3, 3, 6,10,     5, 8, 8, 6, 8, 5,15,15,     8,15, 3, 5, 6,10, 8,15,     15, 3,15, 5,15,15,15,15,        3,15, 5, 5, 5, 8, 5,10,     5,10, 8,13,15,12, 3, 3
};

static const uint8_t g_bc7_table_anchor_index_third_subset_2[64] =
{
    15, 8, 8, 3,15,15, 3, 8,        15,15,15,15,15,15,15, 8,        15, 8,15, 3,15, 8,15, 8,        3,15, 6,10,15,15,10, 8,     15, 3,15,10,10, 8, 9,10,        6,15, 8,15, 3, 6, 6, 8,     15, 3,15,15,15,15,15,15,        15,15,15,15, 3,15,15, 8
};

static const uint8_t g_bc7_table_anchor_index_second_subset[64] = { 15,15,15,15,15,15,15,15,        15,15,15,15,15,15,15,15,        15, 2, 8, 2, 2, 8, 8,15,        2, 8, 2, 2, 8, 8, 2, 2,     15,15, 6, 8, 2, 8,15,15,        2, 8, 2, 2, 2,15,15, 6,     6, 2, 6, 8,15,15, 2, 2,     15,15,15,15,15, 2, 2,15 };
static const uint8_t g_bc7_num_subsets[8] = { 3, 2, 3, 2, 1, 1, 1, 2 };
static const uint8_t g_bc7_partition_bits[8] = { 4, 6, 6, 6, 0, 0, 0, 6 };
static const uint8_t g_bc7_color_index_bitcount[8] = { 3, 3, 2, 2, 2, 2, 4, 2 };
static int get_bc7_color_index_size(int mode, int index_selection_bit) { return g_bc7_color_index_bitcount[mode] + index_selection_bit; }
static uint8_t g_bc7_alpha_index_bitcount[8] = { 0, 0, 0, 0, 3, 2, 4, 2 };
static int get_bc7_alpha_index_size(int mode, int index_selection_bit) { return g_bc7_alpha_index_bitcount[mode] - index_selection_bit; }
static const uint8_t g_bc7_mode_has_p_bits[8] = { 1, 1, 0, 1, 0, 0, 1, 1 };
static const uint8_t g_bc7_mode_has_shared_p_bits[8] = { 0, 1, 0, 0, 0, 0, 0, 0 };
static const uint8_t g_bc7_color_precision_table[8] = { 4, 6, 5, 7, 5, 7, 7, 5 };
static const int8_t g_bc7_alpha_precision_table[8] = { 0, 0, 0, 0, 6, 8, 7, 5 };
static gboolean get_bc7_mode_has_seperate_alpha_selectors(int mode) { return (mode == 4) || (mode == 5); }

typedef struct { uint16_t m_error; uint8_t m_lo; uint8_t m_hi; } endpoint_err;

static endpoint_err g_bc7_mode_1_optimal_endpoints[256][2]; /* [c][pbit] */
static const uint32_t BC7ENC_MODE_1_OPTIMAL_INDEX = 2;

static endpoint_err g_bc7_mode_7_optimal_endpoints[256][2][2]; /* [c][pbit][hp][lp] */
const uint32_t BC7E_MODE_7_OPTIMAL_INDEX = 1;

static float g_mode1_rgba_midpoints[64][2];
static float g_mode5_rgba_midpoints[128];
static float g_mode7_rgba_midpoints[32][2];

static uint8_t g_mode6_reduced_quant[2048][2];

static gboolean g_initialized;


static void
bc7enc_compress_block_params_init_linear_weights (bc7enc_compress_block_params *p)
{
  p->m_perceptual = FALSE;
  p->m_weights[0] = 1;
  p->m_weights[1] = 1;
  p->m_weights[2] = 1;
  p->m_weights[3] = 1;
}

static void
bc7enc_compress_block_params_init_perceptual_weights (bc7enc_compress_block_params *p)
{
  p->m_perceptual = TRUE;
  p->m_weights[0] = 128;
  p->m_weights[1] = 64;
  p->m_weights[2] = 16;
  p->m_weights[3] = 32;
}

void
bc7enc_compress_block_params_init (bc7enc_compress_block_params *p)
{
    p->m_mode_mask = UINT32_MAX;
    p->m_max_partitions = BC7ENC_MAX_PARTITIONS;
    p->m_try_least_squares = TRUE;
    p->m_mode17_partition_estimation_filterbank = FALSE;
    p->m_uber_level = 4;
    p->m_force_selectors = FALSE;
    p->m_force_alpha = FALSE;
    p->m_quant_mode6_endpoints = TRUE;
    p->m_bias_mode1_pbits = TRUE;
    p->m_pbit1_weight = 1.0f;
    p->m_mode1_error_weight = 1.0f;
    p->m_mode5_error_weight = 1.0f;
    p->m_mode6_error_weight = 1.0f;
    p->m_mode7_error_weight = 1.0f;
    p->m_low_frequency_partition_weight = 1.0f;

    if (p->m_perceptual)
      bc7enc_compress_block_params_init_perceptual_weights (p);
    else
      bc7enc_compress_block_params_init_linear_weights (p);
}

/* Initialize the lookup table used for optimal single color compression in
 * mode 1/7. Must be called before encoding. */
void bc7enc_compress_block_init (void)
{
    if (g_initialized)
        return;

    /* Mode 7 endpoint midpoints */
    for (uint32_t p = 0; p < 2; p++)
    {
        for (uint32_t i = 0; i < 32; i++)
        {
            uint32_t vl = ((i << 1) | p) << 2;
            float    lo;
            uint32_t vh;
            float    hi;

            vl |= (vl >> 6);
            lo = vl / 255.0f;

            vh = ((minimumi(31, (i + 1)) << 1) | p) << 2;
            vh |= (vh >> 6);
            hi = vh / 255.0f;

            if (i == 31)
                g_mode7_rgba_midpoints[i][p] = 1.0f;
            else
                g_mode7_rgba_midpoints[i][p] = (lo + hi) / 2.0f;
        }
    }

    /* Mode 1 endpoint midpoints */
    for (uint32_t p = 0; p < 2; p++)
    {
        for (uint32_t i = 0; i < 64; i++)
        {
            uint32_t vl = ((i << 1) | p) << 1;
            float    lo;
            uint32_t vh;
            float    hi;

            vl |= (vl >> 7);
            lo = vl / 255.0f;

            vh = ((minimumi(63, (i + 1)) << 1) | p) << 1;
            vh |= (vh >> 7);
            hi = vh / 255.0f;

            if (i == 63)
                g_mode1_rgba_midpoints[i][p] = 1.0f;
            else
                g_mode1_rgba_midpoints[i][p] = (lo + hi) / 2.0f;
        }
    }

    /* Mode 5 endpoint midpoints */
    for (uint32_t i = 0; i < 128; i++)
    {
        uint32_t vl = (i << 1);
        float    lo;
        uint32_t vh;
        float    hi;

        vl |= (vl >> 7);
        lo = vl / 255.0f;

        vh = minimumi(127, i + 1) << 1;
        vh |= (vh >> 7);
        hi = vh / 255.0f;

        if (i == 127)
            g_mode5_rgba_midpoints[i] = 1.0f;
        else
            g_mode5_rgba_midpoints[i] = (lo + hi) / 2.0f;
    }

    for (uint32_t p = 0; p < 2; p++)
    {
        for (uint32_t i = 0; i < 2048; i++)
        {
            float f = i / 2047.0f;

            float best_err = 1e+9f;
            int best_index = 0;
            for (int j = 0; j < 64; j++)
            {
                int ik = (j * 127 + 31) / 63;
                float k = ((ik << 1) + p) / 255.0f;

                float e = fabsf(k - f);
                if (e < best_err)
                {
                    best_err = e;
                    best_index = ik;
                }
            }

            g_mode6_reduced_quant[i][p] = (uint8_t)best_index;
        }
    } /* p */

    /* Mode 1 */
    for (int c = 0; c < 256; c++)
    {
        for (uint32_t lp = 0; lp < 2; lp++)
        {
            endpoint_err best;
            best.m_error = (uint16_t)UINT16_MAX;
            for (uint32_t l = 0; l < 64; l++)
            {
                uint32_t low = ((l << 1) | lp) << 1;
                low |= (low >> 7);
                for (uint32_t h = 0; h < 64; h++)
                {
                    uint32_t high = ((h << 1) | lp) << 1;
                    int      k;
                    int      err;

                    high |= (high >> 7);
                    k = (low * (64 - g_bc7_weights3[BC7ENC_MODE_1_OPTIMAL_INDEX]) + high * g_bc7_weights3[BC7ENC_MODE_1_OPTIMAL_INDEX] + 32) >> 6;
                    err = (k - c) * (k - c);
                    if (err < best.m_error)
                    {
                        best.m_error = (uint16_t)err;
                        best.m_lo = (uint8_t)l;
                        best.m_hi = (uint8_t)h;
                    }
                } /* h */
            } /* l */
            g_bc7_mode_1_optimal_endpoints[c][lp] = best;
        } /* lp */
    } /* c */

    /* Mode 7: 555.1 2-bit indices */
    for (int c = 0; c < 256; c++)
    {
        for (uint32_t hp = 0; hp < 2; hp++)
        {
            for (uint32_t lp = 0; lp < 2; lp++)
            {
                endpoint_err best;
                best.m_error = (uint16_t)UINT16_MAX;
                best.m_lo = 0;
                best.m_hi = 0;

                for (uint32_t l = 0; l < 32; l++)
                {
                    uint32_t low = ((l << 1) | lp) << 2;
                    low |= (low >> 6);

                    for (uint32_t h = 0; h < 32; h++)
                    {
                        uint32_t high = ((h << 1) | hp) << 2;
                        int      k;
                        int      err;

                        high |= (high >> 6);

                        k = (low * (64 - g_bc7_weights2[BC7E_MODE_7_OPTIMAL_INDEX]) + high * g_bc7_weights2[BC7E_MODE_7_OPTIMAL_INDEX] + 32) >> 6;

                        err = (k - c) * (k - c);
                        if (err < best.m_error)
                        {
                            best.m_error = (uint16_t)err;
                            best.m_lo = (uint8_t)l;
                            best.m_hi = (uint8_t)h;
                        }
                    } /* h */
                } /* l */

                g_bc7_mode_7_optimal_endpoints[c][hp][lp] = best;

            } /* hp */

        } /* lp */

    } /* c */

    g_initialized = TRUE;
}

static void compute_least_squares_endpoints_rgba(uint32_t N, const uint8_t *pSelectors, const vec4F *pSelector_weights, vec4F *pXl, vec4F *pXh, const color_rgba *pColors)
{
    /* Least squares using normal equations: http://www.cs.cornell.edu/~bindel/class/cs3220-s12/notes/lec10.pdf
     * I did this in matrix form first, expanded out all the ops, then optimized it a bit. */
    float z00 = 0.0f, z01 = 0.0f, z10 = 0.0f, z11 = 0.0f;
    float q00_r = 0.0f, q10_r = 0.0f, t_r = 0.0f;
    float q00_g = 0.0f, q10_g = 0.0f, t_g = 0.0f;
    float q00_b = 0.0f, q10_b = 0.0f, t_b = 0.0f;
    float q00_a = 0.0f, q10_a = 0.0f, t_a = 0.0f;
    float det;
    float iz00, iz01, iz10, iz11;

    for (uint32_t i = 0; i < N; i++)
    {
        const uint32_t sel = pSelectors[i];
        float          w;

        z00 += pSelector_weights[sel].m_c[0];
        z10 += pSelector_weights[sel].m_c[1];
        z11 += pSelector_weights[sel].m_c[2];

        w = pSelector_weights[sel].m_c[3];

        q00_r += w * pColors[i].m_c[0]; t_r += pColors[i].m_c[0];
        q00_g += w * pColors[i].m_c[1]; t_g += pColors[i].m_c[1];
        q00_b += w * pColors[i].m_c[2]; t_b += pColors[i].m_c[2];
        q00_a += w * pColors[i].m_c[3]; t_a += pColors[i].m_c[3];
    }

    q10_r = t_r - q00_r;
    q10_g = t_g - q00_g;
    q10_b = t_b - q00_b;
    q10_a = t_a - q00_a;

    z01 = z10;

    det = z00 * z11 - z01 * z10;
    if (det != 0.0f)
        det = 1.0f / det;

    iz00 = z11 * det;
    iz01 = -z01 * det;
    iz10 = -z10 * det;
    iz11 = z00 * det;

    pXl->m_c[0] = (float)(iz00 * q00_r + iz01 * q10_r); pXh->m_c[0] = (float)(iz10 * q00_r + iz11 * q10_r);
    pXl->m_c[1] = (float)(iz00 * q00_g + iz01 * q10_g); pXh->m_c[1] = (float)(iz10 * q00_g + iz11 * q10_g);
    pXl->m_c[2] = (float)(iz00 * q00_b + iz01 * q10_b); pXh->m_c[2] = (float)(iz10 * q00_b + iz11 * q10_b);
    pXl->m_c[3] = (float)(iz00 * q00_a + iz01 * q10_a); pXh->m_c[3] = (float)(iz10 * q00_a + iz11 * q10_a);

    for (uint32_t c = 0; c < 4; c++)
    {
        if ((pXl->m_c[c] < 0.0f) || (pXh->m_c[c] > 255.0f))
        {
            uint32_t lo_v = UINT32_MAX, hi_v = 0;
            for (uint32_t i = 0; i < N; i++)
            {
                lo_v = minimumu(lo_v, pColors[i].m_c[c]);
                hi_v = maximumu(hi_v, pColors[i].m_c[c]);
            }

            if (lo_v == hi_v)
            {
                pXl->m_c[c] = (float)lo_v;
                pXh->m_c[c] = (float)hi_v;
            }
        }
    }
}

static void compute_least_squares_endpoints_rgb(uint32_t N, const uint8_t *pSelectors, const vec4F *pSelector_weights, vec4F *pXl, vec4F *pXh, const color_rgba*pColors)
{
    float z00 = 0.0f, z01 = 0.0f, z10 = 0.0f, z11 = 0.0f;
    float q00_r = 0.0f, q10_r = 0.0f, t_r = 0.0f;
    float q00_g = 0.0f, q10_g = 0.0f, t_g = 0.0f;
    float q00_b = 0.0f, q10_b = 0.0f, t_b = 0.0f;
    float det;
    float iz00, iz01, iz10, iz11;
    for (uint32_t i = 0; i < N; i++)
    {
        const uint32_t sel = pSelectors[i];
        float          w;

        z00 += pSelector_weights[sel].m_c[0];
        z10 += pSelector_weights[sel].m_c[1];
        z11 += pSelector_weights[sel].m_c[2];

        w = pSelector_weights[sel].m_c[3];

        q00_r += w * pColors[i].m_c[0]; t_r += pColors[i].m_c[0];
        q00_g += w * pColors[i].m_c[1]; t_g += pColors[i].m_c[1];
        q00_b += w * pColors[i].m_c[2]; t_b += pColors[i].m_c[2];
    }

    q10_r = t_r - q00_r;
    q10_g = t_g - q00_g;
    q10_b = t_b - q00_b;

    z01 = z10;

    det = z00 * z11 - z01 * z10;
    if (det != 0.0f)
        det = 1.0f / det;

    iz00 = z11 * det;
    iz01 = -z01 * det;
    iz10 = -z10 * det;
    iz11 = z00 * det;

    pXl->m_c[0] = (float)(iz00 * q00_r + iz01 * q10_r); pXh->m_c[0] = (float)(iz10 * q00_r + iz11 * q10_r);
    pXl->m_c[1] = (float)(iz00 * q00_g + iz01 * q10_g); pXh->m_c[1] = (float)(iz10 * q00_g + iz11 * q10_g);
    pXl->m_c[2] = (float)(iz00 * q00_b + iz01 * q10_b); pXh->m_c[2] = (float)(iz10 * q00_b + iz11 * q10_b);
    pXl->m_c[3] = 255.0f; pXh->m_c[3] = 255.0f;

    for (uint32_t c = 0; c < 3; c++)
    {
        if ((pXl->m_c[c] < 0.0f) || (pXh->m_c[c] > 255.0f))
        {
            uint32_t lo_v = UINT32_MAX, hi_v = 0;
            for (uint32_t i = 0; i < N; i++)
            {
                lo_v = minimumu (lo_v, pColors[i].m_c[c]);
                hi_v = maximumu (hi_v, pColors[i].m_c[c]);
            }

            if (lo_v == hi_v)
            {
                pXl->m_c[c] = (float)lo_v;
                pXh->m_c[c] = (float)hi_v;
            }
        }
    }
}

static void compute_least_squares_endpoints_a(uint32_t N, const uint8_t* pSelectors, const vec4F* pSelector_weights, float* pXl, float* pXh, const color_rgba *pColors)
{
    /* Least squares using normal equations: http://www.cs.cornell.edu/~bindel/class/cs3220-s12/notes/lec10.pdf
     8 I did this in matrix form first, expanded out all the ops, then optimized it a bit. */
    float z00 = 0.0f, z01 = 0.0f, z10 = 0.0f, z11 = 0.0f;
    float q00_a = 0.0f, q10_a = 0.0f, t_a = 0.0f;
    float det;
    float iz00, iz01, iz10, iz11;

    for (uint32_t i = 0; i < N; i++)
    {
        const uint32_t sel = pSelectors[i];
        float          w;

        z00 += pSelector_weights[sel].m_c[0];
        z10 += pSelector_weights[sel].m_c[1];
        z11 += pSelector_weights[sel].m_c[2];

        w = pSelector_weights[sel].m_c[3];

        q00_a += w * pColors[i].m_c[3]; t_a += pColors[i].m_c[3];
    }

    q10_a = t_a - q00_a;

    z01 = z10;

    det = z00 * z11 - z01 * z10;
    if (det != 0.0f)
        det = 1.0f / det;

    iz00 = z11 * det;
    iz01 = -z01 * det;
    iz10 = -z10 * det;
    iz11 = z00 * det;

    *pXl = (float)(iz00 * q00_a + iz01 * q10_a); *pXh = (float)(iz10 * q00_a + iz11 * q10_a);

    if ((*pXl < 0.0f) || (*pXh > 255.0f))
    {
        uint32_t lo_v = UINT32_MAX, hi_v = 0;
        for (uint32_t i = 0; i < N; i++)
        {
            lo_v = minimumu(lo_v, pColors[i].m_c[3]);
            hi_v = maximumu(hi_v, pColors[i].m_c[3]);
        }

        if (lo_v == hi_v)
        {
            *pXl = (float)lo_v;
            *pXh = (float)hi_v;
        }
    }
}

typedef struct
{
    uint32_t m_num_pixels;
    const color_rgba *m_pPixels;
    uint32_t m_num_selector_weights;
    const uint32_t *m_pSelector_weights;
    const vec4F *m_pSelector_weightsx;
    uint32_t m_comp_bits;
    uint32_t m_weights[4];
    gboolean m_has_alpha;
    gboolean m_has_pbits;
    gboolean m_endpoints_share_pbit;
    gboolean m_perceptual;
} color_cell_compressor_params;

typedef struct
{
    uint64_t m_best_overall_err;
    color_rgba m_low_endpoint;
    color_rgba m_high_endpoint;
    uint32_t m_pbits[2];
    uint8_t *m_pSelectors;
    uint8_t *m_pSelectors_temp;
} color_cell_compressor_results;

static inline color_rgba scale_color(const color_rgba *pC, const color_cell_compressor_params *pParams)
{
    color_rgba results;

    const uint32_t n = pParams->m_comp_bits + (pParams->m_has_pbits ? 1 : 0);
    assert((n >= 4) && (n <= 8));

    for (uint32_t i = 0; i < 4; i++)
    {
        uint32_t v = pC->m_c[i] << (8 - n);
        v |= (v >> n);
        assert(v <= 255);
        results.m_c[i] = (uint8_t)(v);
    }

    return results;
}

static inline uint64_t compute_color_distance_rgb(const color_rgba *pE1, const color_rgba *pE2, gboolean perceptual, const uint32_t weights[4])
{
    int dr, dg, db;

    if (perceptual)
    {
        const int l1 = pE1->m_c[0] * 109 + pE1->m_c[1] * 366 + pE1->m_c[2] * 37;
        const int cr1 = ((int)pE1->m_c[0] << 9) - l1;
        const int cb1 = ((int)pE1->m_c[2] << 9) - l1;
        const int l2 = pE2->m_c[0] * 109 + pE2->m_c[1] * 366 + pE2->m_c[2] * 37;
        const int cr2 = ((int)pE2->m_c[0] << 9) - l2;
        const int cb2 = ((int)pE2->m_c[2] << 9) - l2;
        dr = (l1 - l2) >> 8;
        dg = (cr1 - cr2) >> 8;
        db = (cb1 - cb2) >> 8;
    }
    else
    {
        dr = (int)pE1->m_c[0] - (int)pE2->m_c[0];
        dg = (int)pE1->m_c[1] - (int)pE2->m_c[1];
        db = (int)pE1->m_c[2] - (int)pE2->m_c[2];
    }

    return weights[0] * (uint32_t)(dr * dr) + weights[1] * (uint32_t)(dg * dg) + weights[2] * (uint32_t)(db * db);
}

static inline uint64_t compute_color_distance_rgba(const color_rgba *pE1, const color_rgba *pE2, gboolean perceptual, const uint32_t weights[4])
{
    int da = (int)pE1->m_c[3] - (int)pE2->m_c[3];
    return compute_color_distance_rgb(pE1, pE2, perceptual, weights) + (weights[3] * (uint32_t)(da * da));
}

static uint64_t pack_mode1_to_one_color(const color_cell_compressor_params *pParams, color_cell_compressor_results *pResults, uint32_t r, uint32_t g, uint32_t b, uint8_t *pSelectors)
{
    uint32_t      best_err = UINT_MAX;
    uint32_t      best_p = 0;
    endpoint_err *pEr;
    endpoint_err *pEg;
    endpoint_err *pEb;
    color_rgba    p;
    uint64_t      total_err = 0;

    for (uint32_t p = 0; p < 2; p++)
    {
        uint32_t err = g_bc7_mode_1_optimal_endpoints[r][p].m_error + g_bc7_mode_1_optimal_endpoints[g][p].m_error + g_bc7_mode_1_optimal_endpoints[b][p].m_error;
        if (err < best_err)
        {
            best_err = err;
            best_p = p;
            if (!best_err)
                break;
        }
    }

    pEr = &g_bc7_mode_1_optimal_endpoints[r][best_p];
    pEg = &g_bc7_mode_1_optimal_endpoints[g][best_p];
    pEb = &g_bc7_mode_1_optimal_endpoints[b][best_p];

    color_quad_u8_set(&pResults->m_low_endpoint, pEr->m_lo, pEg->m_lo, pEb->m_lo, 0);
    color_quad_u8_set(&pResults->m_high_endpoint, pEr->m_hi, pEg->m_hi, pEb->m_hi, 0);
    pResults->m_pbits[0] = best_p;
    pResults->m_pbits[1] = 0;

    memset(pSelectors, BC7ENC_MODE_1_OPTIMAL_INDEX, pParams->m_num_pixels);

    for (uint32_t i = 0; i < 3; i++)
    {
        uint32_t low = ((pResults->m_low_endpoint.m_c[i] << 1) | pResults->m_pbits[0]) << 1;
        uint32_t high;

        low |= (low >> 7);

        high = ((pResults->m_high_endpoint.m_c[i] << 1) | pResults->m_pbits[0]) << 1;
        high |= (high >> 7);

        p.m_c[i] = (uint8_t)((low * (64 - g_bc7_weights3[BC7ENC_MODE_1_OPTIMAL_INDEX]) + high * g_bc7_weights3[BC7ENC_MODE_1_OPTIMAL_INDEX] + 32) >> 6);
    }
    p.m_c[3] = 255;

    for (uint32_t i = 0; i < pParams->m_num_pixels; i++)
        total_err += compute_color_distance_rgb(&p, &pParams->m_pPixels[i], pParams->m_perceptual, pParams->m_weights);

    pResults->m_best_overall_err = total_err;

    return total_err;
}

static uint64_t pack_mode7_to_one_color(const color_cell_compressor_params* pParams, color_cell_compressor_results* pResults, uint32_t r, uint32_t g, uint32_t b, uint32_t a,
    uint8_t* pSelectors, uint32_t num_pixels, const color_rgba *pPixels)
{
    uint32_t            best_err = UINT_MAX;
    uint32_t            best_p = 0;
    uint32_t            best_hi_p;
    uint32_t            best_lo_p;
    color_rgba          p;
    const endpoint_err* pEr;
    const endpoint_err* pEg;
    const endpoint_err* pEb;
    const endpoint_err* pEa;
    uint64_t            total_err;

    for (uint32_t p = 0; p < 4; p++)
    {
        uint32_t hi_p = p >> 1;
        uint32_t lo_p = p & 1;
        uint32_t err = g_bc7_mode_7_optimal_endpoints[r][hi_p][lo_p].m_error + g_bc7_mode_7_optimal_endpoints[g][hi_p][lo_p].m_error + g_bc7_mode_7_optimal_endpoints[b][hi_p][lo_p].m_error + g_bc7_mode_7_optimal_endpoints[a][hi_p][lo_p].m_error;
        if (err < best_err)
        {
            best_err = err;
            best_p = p;
            if (!best_err)
                break;
        }
    }

    best_hi_p = best_p >> 1;
    best_lo_p = best_p & 1;

    pEr = &g_bc7_mode_7_optimal_endpoints[r][best_hi_p][best_lo_p];
    pEg = &g_bc7_mode_7_optimal_endpoints[g][best_hi_p][best_lo_p];
    pEb = &g_bc7_mode_7_optimal_endpoints[b][best_hi_p][best_lo_p];
    pEa = &g_bc7_mode_7_optimal_endpoints[a][best_hi_p][best_lo_p];

    color_quad_u8_set(&pResults->m_low_endpoint, pEr->m_lo, pEg->m_lo, pEb->m_lo, pEa->m_lo);
    color_quad_u8_set(&pResults->m_high_endpoint, pEr->m_hi, pEg->m_hi, pEb->m_hi, pEa->m_hi);
    pResults->m_pbits[0] = best_lo_p;
    pResults->m_pbits[1] = best_hi_p;

    for (uint32_t i = 0; i < num_pixels; i++)
        pSelectors[i] = (uint8_t)BC7E_MODE_7_OPTIMAL_INDEX;

    for (uint32_t i = 0; i < 4; i++)
    {
        uint32_t low = (pResults->m_low_endpoint.m_c[i] << 1) | pResults->m_pbits[0];
        uint32_t high = (pResults->m_high_endpoint.m_c[i] << 1) | pResults->m_pbits[1];

        low = (low << 2) | (low >> 6);
        high = (high << 2) | (high >> 6);

        p.m_c[i] = (uint8_t)((low * (64 - g_bc7_weights2[BC7E_MODE_7_OPTIMAL_INDEX]) + high * g_bc7_weights2[BC7E_MODE_7_OPTIMAL_INDEX] + 32) >> 6);
    }

    total_err = 0;
    for (uint32_t i = 0; i < num_pixels; i++)
        total_err += compute_color_distance_rgba(&p, &pPixels[i], pParams->m_perceptual, pParams->m_weights);

    pResults->m_best_overall_err = total_err;

    return total_err;
}

static uint64_t evaluate_solution(const color_rgba *pLow, const color_rgba *pHigh, const uint32_t pbits[2], const color_cell_compressor_params *pParams, color_cell_compressor_results *pResults,
    const bc7enc_compress_block_params* pComp_params)
{
    uint32_t N;
    uint32_t nc;
    int      lr;
    int      lg;
    int      lb;
    int      dr;
    int      dg;
    int      db;
    uint64_t total_err = 0;

    color_rgba quantMinColor = *pLow;
    color_rgba quantMaxColor = *pHigh;
    color_rgba actualMinColor;
    color_rgba actualMaxColor;
    color_rgba weightedColors[16];

    if (pParams->m_has_pbits)
    {
        uint32_t minPBit, maxPBit;

        if (pParams->m_endpoints_share_pbit)
            maxPBit = minPBit = pbits[0];
        else
        {
            minPBit = pbits[0];
            maxPBit = pbits[1];
        }

        quantMinColor.m_c[0] = (uint8_t)((pLow->m_c[0] << 1) | minPBit);
        quantMinColor.m_c[1] = (uint8_t)((pLow->m_c[1] << 1) | minPBit);
        quantMinColor.m_c[2] = (uint8_t)((pLow->m_c[2] << 1) | minPBit);
        quantMinColor.m_c[3] = (uint8_t)((pLow->m_c[3] << 1) | minPBit);

        quantMaxColor.m_c[0] = (uint8_t)((pHigh->m_c[0] << 1) | maxPBit);
        quantMaxColor.m_c[1] = (uint8_t)((pHigh->m_c[1] << 1) | maxPBit);
        quantMaxColor.m_c[2] = (uint8_t)((pHigh->m_c[2] << 1) | maxPBit);
        quantMaxColor.m_c[3] = (uint8_t)((pHigh->m_c[3] << 1) | maxPBit);
    }

    actualMinColor = scale_color(&quantMinColor, pParams);
    actualMaxColor = scale_color(&quantMaxColor, pParams);

    N = pParams->m_num_selector_weights;

    weightedColors[0] = actualMinColor;
    weightedColors[N - 1] = actualMaxColor;

    nc = pParams->m_has_alpha ? 4 : 3;
    for (uint32_t i = 1; i < (N - 1); i++)
        for (uint32_t j = 0; j < nc; j++)
            weightedColors[i].m_c[j] = (uint8_t)((actualMinColor.m_c[j] * (64 - pParams->m_pSelector_weights[i]) + actualMaxColor.m_c[j] * pParams->m_pSelector_weights[i] + 32) >> 6);

    lr = actualMinColor.m_c[0];
    lg = actualMinColor.m_c[1];
    lb = actualMinColor.m_c[2];
    dr = actualMaxColor.m_c[0] - lr;
    dg = actualMaxColor.m_c[1] - lg;
    db = actualMaxColor.m_c[2] - lb;

    if (pComp_params->m_force_selectors)
    {
        for (uint32_t i = 0; i < pParams->m_num_pixels; i++)
        {
            const uint32_t best_sel = pComp_params->m_selectors[i];

            uint64_t best_err;
            if (pParams->m_has_alpha)
                best_err = compute_color_distance_rgba(&weightedColors[best_sel], &pParams->m_pPixels[i], pParams->m_perceptual, pParams->m_weights);
            else
                best_err = compute_color_distance_rgb(&weightedColors[best_sel], &pParams->m_pPixels[i], pParams->m_perceptual, pParams->m_weights);

            total_err += best_err;

            pResults->m_pSelectors_temp[i] = (uint8_t)best_sel;
        }
    }
    else if (!pParams->m_perceptual)
    {
        if (pParams->m_has_alpha)
        {
            const int la = actualMinColor.m_c[3];
            const int da = actualMaxColor.m_c[3] - la;

            const float f = N / (float)(squarei(dr) + squarei(dg) + squarei(db) + squarei(da) + .00000125f);

            for (uint32_t i = 0; i < pParams->m_num_pixels; i++)
            {
                const color_rgba *pC = &pParams->m_pPixels[i];
                int               r = pC->m_c[0];
                int               g = pC->m_c[1];
                int               b = pC->m_c[2];
                int               a = pC->m_c[3];
                uint64_t          err0;
                uint64_t          err1;

                int best_sel = (int)((float)((r - lr) * dr + (g - lg) * dg + (b - lb) * db + (a - la) * da) * f + .5f);
                best_sel = clampi(best_sel, 1, N - 1);

                err0 = compute_color_distance_rgba(&weightedColors[best_sel - 1], pC, FALSE, pParams->m_weights);
                err1 = compute_color_distance_rgba(&weightedColors[best_sel], pC, FALSE, pParams->m_weights);

                if (err1 > err0)
                {
                    err1 = err0;
                    --best_sel;
                }
                total_err += err1;

                pResults->m_pSelectors_temp[i] = (uint8_t)best_sel;
            }
        }
        else
        {
            const float f = N / (float)(squarei(dr) + squarei(dg) + squarei(db) + .00000125f);

            for (uint32_t i = 0; i < pParams->m_num_pixels; i++)
            {
                const color_rgba *pC = &pParams->m_pPixels[i];
                int               r = pC->m_c[0];
                int               g = pC->m_c[1];
                int               b = pC->m_c[2];
                uint64_t          err0;
                uint64_t          err1;
                int               best_sel;
                uint64_t          best_err;

                int sel = (int)((float)((r - lr) * dr + (g - lg) * dg + (b - lb) * db) * f + .5f);
                sel = clampi(sel, 1, N - 1);

                err0 = compute_color_distance_rgb(&weightedColors[sel - 1], pC, FALSE, pParams->m_weights);
                err1 = compute_color_distance_rgb(&weightedColors[sel], pC, FALSE, pParams->m_weights);

                best_sel = sel;
                best_err = err1;
                if (err0 < best_err)
                {
                    best_err = err0;
                    best_sel = sel - 1;
                }

                total_err += best_err;

                pResults->m_pSelectors_temp[i] = (uint8_t)best_sel;
            }
        }
    }
    else
    {
        for (uint32_t i = 0; i < pParams->m_num_pixels; i++)
        {
            uint64_t best_err = UINT64_MAX;
            uint32_t best_sel = 0;

            if (pParams->m_has_alpha)
            {
                for (uint32_t j = 0; j < N; j++)
                {
                    uint64_t err = compute_color_distance_rgba(&weightedColors[j], &pParams->m_pPixels[i], TRUE, pParams->m_weights);
                    if (err < best_err)
                    {
                        best_err = err;
                        best_sel = j;
                    }
                }
            }
            else
            {
                for (uint32_t j = 0; j < N; j++)
                {
                    uint64_t err = compute_color_distance_rgb(&weightedColors[j], &pParams->m_pPixels[i], TRUE, pParams->m_weights);
                    if (err < best_err)
                    {
                        best_err = err;
                        best_sel = j;
                    }
                }
            }

            total_err += best_err;

            pResults->m_pSelectors_temp[i] = (uint8_t)best_sel;
        }
    }

    if (total_err < pResults->m_best_overall_err)
    {
        pResults->m_best_overall_err = total_err;

        pResults->m_low_endpoint = *pLow;
        pResults->m_high_endpoint = *pHigh;

        pResults->m_pbits[0] = pbits[0];
        pResults->m_pbits[1] = pbits[1];

        memcpy(pResults->m_pSelectors, pResults->m_pSelectors_temp, sizeof(pResults->m_pSelectors[0]) * pParams->m_num_pixels);
    }

    return total_err;
}

static void fixDegenerateEndpoints(uint32_t mode, color_rgba *pTrialMinColor,
                                   color_rgba *pTrialMaxColor,
                                   const vec4F *pXl,
                                   const vec4F *pXh,
                                   uint32_t iscale,
                                   const bc7enc_compress_block_params* pComp_params)
{
    if ( (mode == 1) || ((mode == 6) && (pComp_params->m_quant_mode6_endpoints)) )
    {
        for (uint32_t i = 0; i < 3; i++)
        {
            if (pTrialMinColor->m_c[i] == pTrialMaxColor->m_c[i])
            {
                if (fabs(pXl->m_c[i] - pXh->m_c[i]) > 0.0f)
                {
                    if (pTrialMinColor->m_c[i] > (iscale >> 1))
                    {
                        if (pTrialMinColor->m_c[i] > 0)
                            pTrialMinColor->m_c[i]--;
                        else
                            if (pTrialMaxColor->m_c[i] < iscale)
                                pTrialMaxColor->m_c[i]++;
                    }
                    else
                    {
                        if (pTrialMaxColor->m_c[i] < iscale)
                            pTrialMaxColor->m_c[i]++;
                        else if (pTrialMinColor->m_c[i] > 0)
                            pTrialMinColor->m_c[i]--;
                    }
                }
            }
        }
    }
}

static uint64_t find_optimal_solution(uint32_t mode, vec4F xl, vec4F xh, const color_cell_compressor_params *pParams, color_cell_compressor_results *pResults,
    const bc7enc_compress_block_params* pComp_params)
{
    vec4F_saturate_in_place(&xl); vec4F_saturate_in_place(&xh);

    if (pParams->m_has_pbits)
    {
        const int iscalep = (1 << (pParams->m_comp_bits + 1)) - 1;
        const float scalep = (float)iscalep;

        const int32_t totalComps = pParams->m_has_alpha ? 4 : 3;

        uint32_t best_pbits[2];
        color_rgba bestMinColor, bestMaxColor;

        if (!pParams->m_endpoints_share_pbit)
        {
            if ((pParams->m_comp_bits == 7) && (pComp_params->m_quant_mode6_endpoints))
            {
                best_pbits[0] = 0;
                bestMinColor.m_c[0] = g_mode6_reduced_quant[(int)((xl.m_c[0] * 2047.0f) + .5f)][0];
                bestMinColor.m_c[1] = g_mode6_reduced_quant[(int)((xl.m_c[1] * 2047.0f) + .5f)][0];
                bestMinColor.m_c[2] = g_mode6_reduced_quant[(int)((xl.m_c[2] * 2047.0f) + .5f)][0];
                bestMinColor.m_c[3] = g_mode6_reduced_quant[(int)((xl.m_c[3] * 2047.0f) + .5f)][0];

                best_pbits[1] = 1;
                bestMaxColor.m_c[0] = g_mode6_reduced_quant[(int)((xh.m_c[0] * 2047.0f) + .5f)][1];
                bestMaxColor.m_c[1] = g_mode6_reduced_quant[(int)((xh.m_c[1] * 2047.0f) + .5f)][1];
                bestMaxColor.m_c[2] = g_mode6_reduced_quant[(int)((xh.m_c[2] * 2047.0f) + .5f)][1];
                bestMaxColor.m_c[3] = g_mode6_reduced_quant[(int)((xh.m_c[3] * 2047.0f) + .5f)][1];
            }
            else
            {
                float best_err0 = 1e+9;
                float best_err1 = 1e+9;

                for (int p = 0; p < 2; p++)
                {
                    color_rgba xMinColor, xMaxColor;
                    color_rgba scaledLow;
                    color_rgba scaledHigh;
                    float      err0 = 0;
                    float      err1 = 0;

                    /* Notes: The pbit controls which quantization intervals are selected.
                     * total_levels=2^(comp_bits+1), where comp_bits=4 for mode 0, etc.
                     * pbit 0: v=(b*2)/(total_levels-1), pbit 1: v=(b*2+1)/(total_levels-1)
                     * where b is the component bin from [0,total_levels/2-1] and v is the [0,1] component value
                     * rearranging you get for pbit 0: b=floor(v*(total_levels-1)/2+.5)
                     * rearranging you get for pbit 1: b=floor((v*(total_levels-1)-1)/2+.5) */
                    if (pParams->m_comp_bits == 5)
                    {
                        for (uint32_t c = 0; c < 4; c++)
                        {
                            int vl = (int)(xl.m_c[c] * 31.0f);
                            int vh;

                            vl += (xl.m_c[c] > g_mode7_rgba_midpoints[vl][p]);
                            xMinColor.m_c[c] = (uint8_t)clampi(vl * 2 + p, p, 63 - 1 + p);

                            vh = (int)(xh.m_c[c] * 31.0f);
                            vh += (xh.m_c[c] > g_mode7_rgba_midpoints[vh][p]);
                            xMaxColor.m_c[c] = (uint8_t)clampi(vh * 2 + p, p, 63 - 1 + p);
                        }
                    }
                    else
                    {
                        for (uint32_t c = 0; c < 4; c++)
                        {
                            xMinColor.m_c[c] = (uint8_t)(clampi(((int)((xl.m_c[c] * scalep - p) / 2.0f + .5f)) * 2 + p, p, iscalep - 1 + p));
                            xMaxColor.m_c[c] = (uint8_t)(clampi(((int)((xh.m_c[c] * scalep - p) / 2.0f + .5f)) * 2 + p, p, iscalep - 1 + p));
                        }
                    }

                    scaledLow = scale_color(&xMinColor, pParams);
                    scaledHigh = scale_color(&xMaxColor, pParams);

                    for (int i = 0; i < totalComps; i++)
                    {
                        err0 += squaref(scaledLow.m_c[i] - xl.m_c[i] * 255.0f);
                        err1 += squaref(scaledHigh.m_c[i] - xh.m_c[i] * 255.0f);
                    }

                    if (p == 1)
                    {
                        err0 *= pComp_params->m_pbit1_weight;
                        err1 *= pComp_params->m_pbit1_weight;
                    }

                    if (err0 < best_err0)
                    {
                        best_err0 = err0;
                        best_pbits[0] = p;

                        bestMinColor.m_c[0] = xMinColor.m_c[0] >> 1;
                        bestMinColor.m_c[1] = xMinColor.m_c[1] >> 1;
                        bestMinColor.m_c[2] = xMinColor.m_c[2] >> 1;
                        bestMinColor.m_c[3] = xMinColor.m_c[3] >> 1;
                    }

                    if (err1 < best_err1)
                    {
                        best_err1 = err1;
                        best_pbits[1] = p;

                        bestMaxColor.m_c[0] = xMaxColor.m_c[0] >> 1;
                        bestMaxColor.m_c[1] = xMaxColor.m_c[1] >> 1;
                        bestMaxColor.m_c[2] = xMaxColor.m_c[2] >> 1;
                        bestMaxColor.m_c[3] = xMaxColor.m_c[3] >> 1;
                    }
                }
            }
        }
        else
        {
            if ((mode == 1) && (pComp_params->m_bias_mode1_pbits))
            {
                float      x = 0.0f;
                int        p = 0;
                color_rgba xMinColor, xMaxColor;

                for (uint32_t c = 0; c < 3; c++)
                    x = MAX (MAX (x, xl.m_c[c]), xh.m_c[c]);

                if (x > (253.0f / 255.0f))
                    p = 1;

                for (uint32_t c = 0; c < 4; c++)
                {
                    int vl = (int)(xl.m_c[c] * 63.0f);
                    int vh;

                    vl += (xl.m_c[c] > g_mode1_rgba_midpoints[vl][p]);
                    xMinColor.m_c[c] = (uint8_t)clampi(vl * 2 + p, p, 127 - 1 + p);

                    vh = (int)(xh.m_c[c] * 63.0f);
                    vh += (xh.m_c[c] > g_mode1_rgba_midpoints[vh][p]);
                    xMaxColor.m_c[c] = (uint8_t)clampi(vh * 2 + p, p, 127 - 1 + p);
                }

                best_pbits[0] = p;
                best_pbits[1] = p;
                for (uint32_t j = 0; j < 4; j++)
                {
                    bestMinColor.m_c[j] = xMinColor.m_c[j] >> 1;
                    bestMaxColor.m_c[j] = xMaxColor.m_c[j] >> 1;
                }
            }
            else
            {
                /* Endpoints share pbits */
                float best_err = 1e+9;

                for (int p = 0; p < 2; p++)
                {
                    color_rgba xMinColor, xMaxColor;
                    color_rgba scaledLow;
                    color_rgba scaledHigh;
                    float      err = 0;


                    if (pParams->m_comp_bits == 6)
                    {
                        for (uint32_t c = 0; c < 4; c++)
                        {
                            int vl = (int)(xl.m_c[c] * 63.0f);
                            int vh;

                            vl += (xl.m_c[c] > g_mode1_rgba_midpoints[vl][p]);
                            xMinColor.m_c[c] = (uint8_t)clampi(vl * 2 + p, p, 127 - 1 + p);

                            vh = (int)(xh.m_c[c] * 63.0f);
                            vh += (xh.m_c[c] > g_mode1_rgba_midpoints[vh][p]);
                            xMaxColor.m_c[c] = (uint8_t)clampi(vh * 2 + p, p, 127 - 1 + p);
                        }
                    }
                    else
                    {
                        for (uint32_t c = 0; c < 4; c++)
                        {
                            xMinColor.m_c[c] = (uint8_t)(clampi(((int)((xl.m_c[c] * scalep - p) / 2.0f + .5f)) * 2 + p, p, iscalep - 1 + p));
                            xMaxColor.m_c[c] = (uint8_t)(clampi(((int)((xh.m_c[c] * scalep - p) / 2.0f + .5f)) * 2 + p, p, iscalep - 1 + p));
                        }
                    }

                    scaledLow = scale_color(&xMinColor, pParams);
                    scaledHigh = scale_color(&xMaxColor, pParams);

                    for (int i = 0; i < totalComps; i++)
                        err += squaref((scaledLow.m_c[i] / 255.0f) - xl.m_c[i]) + squaref((scaledHigh.m_c[i] / 255.0f) - xh.m_c[i]);

                    if (p == 1)
                        err *= pComp_params->m_pbit1_weight;

                    if (err < best_err)
                    {
                        best_err = err;
                        best_pbits[0] = p;
                        best_pbits[1] = p;
                        for (uint32_t j = 0; j < 4; j++)
                        {
                            bestMinColor.m_c[j] = xMinColor.m_c[j] >> 1;
                            bestMaxColor.m_c[j] = xMaxColor.m_c[j] >> 1;
                        }
                    }
                }
            }
        }

        fixDegenerateEndpoints(mode, &bestMinColor, &bestMaxColor, &xl, &xh, iscalep >> 1, pComp_params);

        if ((pResults->m_best_overall_err == UINT64_MAX) || color_quad_u8_notequals(&bestMinColor, &pResults->m_low_endpoint) || color_quad_u8_notequals(&bestMaxColor, &pResults->m_high_endpoint) || (best_pbits[0] != pResults->m_pbits[0]) || (best_pbits[1] != pResults->m_pbits[1]))
            evaluate_solution(&bestMinColor, &bestMaxColor, best_pbits, pParams, pResults, pComp_params);
    }
    else
    {
        const int   iscale = (1 << pParams->m_comp_bits) - 1;
        const float scale = (float)iscale;

        color_rgba trialMinColor, trialMaxColor;
        if (pParams->m_comp_bits == 7)
        {
            for (uint32_t c = 0; c < 4; c++)
            {
                int vl = (int)(xl.m_c[c] * 127.0f);
                int vh;

                vl += (xl.m_c[c] > g_mode5_rgba_midpoints[vl]);
                trialMinColor.m_c[c] = (uint8_t)clampi(vl, 0, 127);

                vh = (int)(xh.m_c[c] * 127.0f);
                vh += (xh.m_c[c] > g_mode5_rgba_midpoints[vh]);
                trialMaxColor.m_c[c] = (uint8_t)clampi(vh, 0, 127);
            }
        }
        else
        {
            color_quad_u8_set_clamped(&trialMinColor,
                                      (int)(xl.m_c[0] * scale + .5f),
                                      (int)(xl.m_c[1] * scale + .5f),
                                      (int)(xl.m_c[2] * scale + .5f),
                                      (int)(xl.m_c[3] * scale + .5f));
            color_quad_u8_set_clamped(&trialMaxColor,
                                      (int)(xh.m_c[0] * scale + .5f),
                                      (int)(xh.m_c[1] * scale + .5f),
                                      (int)(xh.m_c[2] * scale + .5f),
                                      (int)(xh.m_c[3] * scale + .5f));
        }

        fixDegenerateEndpoints(mode, &trialMinColor, &trialMaxColor, &xl, &xh, iscale, pComp_params);

        if ((pResults->m_best_overall_err == UINT64_MAX) || color_quad_u8_notequals(&trialMinColor, &pResults->m_low_endpoint) || color_quad_u8_notequals(&trialMaxColor, &pResults->m_high_endpoint))
            evaluate_solution(&trialMinColor, &trialMaxColor, pResults->m_pbits, pParams, pResults, pComp_params);
    }

    return pResults->m_best_overall_err;
}

static uint64_t color_cell_compression(uint32_t mode,
                                       const color_cell_compressor_params *pParams,
                                       color_cell_compressor_results *pResults,
                                       const bc7enc_compress_block_params *pComp_params)
{
    vec4F meanColor, axis;
    vec4F meanColorScaled;
    float l = 1e+9f, h = -1e+9f;
    vec4F b0;
    vec4F b1;
    vec4F c0;
    vec4F c1;
    vec4F minColor;
    vec4F maxColor;

    vec4F whiteVec;

    assert((mode == 6) || (mode == 7) || (!pParams->m_has_alpha));

    pResults->m_best_overall_err = UINT64_MAX;

    /* If the partition's colors are all the same in mode 1,
     * then just pack them as a single color. */
    if (mode == 1)
    {
        const uint32_t cr = pParams->m_pPixels[0].m_c[0], cg = pParams->m_pPixels[0].m_c[1], cb = pParams->m_pPixels[0].m_c[2];

        gboolean allSame = TRUE;
        for (uint32_t i = 1; i < pParams->m_num_pixels; i++)
        {
            if ((cr != pParams->m_pPixels[i].m_c[0]) || (cg != pParams->m_pPixels[i].m_c[1]) || (cb != pParams->m_pPixels[i].m_c[2]))
            {
                allSame = FALSE;
                break;
            }
        }

        if (allSame)
            return pack_mode1_to_one_color(pParams, pResults, cr, cg, cb, pResults->m_pSelectors);
    }
    else if (mode == 7)
    {
        const uint32_t cr = pParams->m_pPixels[0].m_c[0], cg = pParams->m_pPixels[0].m_c[1], cb = pParams->m_pPixels[0].m_c[2], ca = pParams->m_pPixels[0].m_c[3];

        gboolean allSame = TRUE;
        for (uint32_t i = 1; i < pParams->m_num_pixels; i++)
        {
            if ((cr != pParams->m_pPixels[i].m_c[0]) || (cg != pParams->m_pPixels[i].m_c[1]) || (cb != pParams->m_pPixels[i].m_c[2]) || (ca != pParams->m_pPixels[i].m_c[3]))
            {
                allSame = FALSE;
                break;
            }
        }

        if (allSame)
            return pack_mode7_to_one_color(pParams, pResults, cr, cg, cb, ca, pResults->m_pSelectors, pParams->m_num_pixels, pParams->m_pPixels);
    }

    /* Compute partition's mean color and principle axis. */
    vec4F_set_scalar(&meanColor, 0.0f);

    for (uint32_t i = 0; i < pParams->m_num_pixels; i++)
    {
        vec4F color = vec4F_from_color(&pParams->m_pPixels[i]);
        meanColor = vec4F_add(&meanColor, &color);
    }

    meanColorScaled = vec4F_mul(&meanColor, 1.0f / (float)(pParams->m_num_pixels));

    meanColor = vec4F_mul(&meanColor, 1.0f / (float)(pParams->m_num_pixels * 255.0f));
    vec4F_saturate_in_place(&meanColor);

    if (pParams->m_has_alpha)
    {
        /* Use incremental PCA for RGBA PCA, because it's simple. */
        vec4F_set_scalar(&axis, 0.0f);
        for (uint32_t i = 0; i < pParams->m_num_pixels; i++)
        {
            vec4F color = vec4F_from_color(&pParams->m_pPixels[i]);
            vec4F a;
            vec4F b;
            vec4F c;
            vec4F d;
            vec4F n;

            color = vec4F_sub(&color, &meanColorScaled);
            a = vec4F_mul(&color, color.m_c[0]);
            b = vec4F_mul(&color, color.m_c[1]);
            c = vec4F_mul(&color, color.m_c[2]);
            d = vec4F_mul(&color, color.m_c[3]);
            n = i ? axis : color;
            vec4F_normalize_in_place(&n);
            axis.m_c[0] += vec4F_dot(&a, &n);
            axis.m_c[1] += vec4F_dot(&b, &n);
            axis.m_c[2] += vec4F_dot(&c, &n);
            axis.m_c[3] += vec4F_dot(&d, &n);
        }
        vec4F_normalize_in_place(&axis);
    }
    else
    {
        /* Use covar technique for RGB PCA, because it doesn't
         * require per-pixel normalization. */
        float cov[6] = { 0, 0, 0, 0, 0, 0 };
        float vfr = .9f, vfg = 1.0f, vfb = .7f;
        float len;

        for (uint32_t i = 0; i < pParams->m_num_pixels; i++)
        {
            const color_rgba *pV = &pParams->m_pPixels[i];
            float r = pV->m_c[0] - meanColorScaled.m_c[0];
            float g = pV->m_c[1] - meanColorScaled.m_c[1];
            float b = pV->m_c[2] - meanColorScaled.m_c[2];
            cov[0] += r*r; cov[1] += r*g; cov[2] += r*b; cov[3] += g*g; cov[4] += g*b; cov[5] += b*b;
        }

        for (uint32_t iter = 0; iter < 3; iter++)
        {
            float r = vfr*cov[0] + vfg*cov[1] + vfb*cov[2];
            float g = vfr*cov[1] + vfg*cov[3] + vfb*cov[4];
            float b = vfr*cov[2] + vfg*cov[4] + vfb*cov[5];

            float m = maximumf(maximumf(fabsf(r), fabsf(g)), fabsf(b));
            if (m > 1e-10f)
            {
                m = 1.0f / m;
                r *= m; g *= m; b *= m;
            }

            vfr = r; vfg = g; vfb = b;
        }

        len = vfr*vfr + vfg*vfg + vfb*vfb;
        if (len < 1e-10f)
            vec4F_set_scalar(&axis, 0.0f);
        else
        {
            len = 1.0f / sqrtf(len);
            vfr *= len; vfg *= len; vfb *= len;
            vec4F_set(&axis, vfr, vfg, vfb, 0);
        }
    }

    if (vec4F_dot(&axis, &axis) < .5f)
    {
        if (pParams->m_perceptual)
            vec4F_set(&axis, .213f, .715f, .072f, pParams->m_has_alpha ? .715f : 0);
        else
            vec4F_set(&axis, 1.0f, 1.0f, 1.0f, pParams->m_has_alpha ? 1.0f : 0);
        vec4F_normalize_in_place(&axis);
    }

    for (uint32_t i = 0; i < pParams->m_num_pixels; i++)
    {
        vec4F color = vec4F_from_color(&pParams->m_pPixels[i]);

        vec4F q = vec4F_sub(&color, &meanColorScaled);
        float d = vec4F_dot(&q, &axis);

        l = minimumf(l, d);
        h = maximumf(h, d);
    }

    l *= (1.0f / 255.0f);
    h *= (1.0f / 255.0f);

    b0 = vec4F_mul(&axis, l);
    b1 = vec4F_mul(&axis, h);
    c0 = vec4F_add(&meanColor, &b0);
    c1 = vec4F_add(&meanColor, &b1);
    minColor = vec4F_saturate(&c0);
    maxColor = vec4F_saturate(&c1);

    vec4F_set_scalar(&whiteVec, 1.0f);

    if (vec4F_dot(&minColor, &whiteVec) > vec4F_dot(&maxColor, &whiteVec))
    {
        float a = minColor.m_c[0], b = minColor.m_c[1], c = minColor.m_c[2], d = minColor.m_c[3];
        minColor.m_c[0] = maxColor.m_c[0];
        minColor.m_c[1] = maxColor.m_c[1];
        minColor.m_c[2] = maxColor.m_c[2];
        minColor.m_c[3] = maxColor.m_c[3];
        maxColor.m_c[0] = a;
        maxColor.m_c[1] = b;
        maxColor.m_c[2] = c;
        maxColor.m_c[3] = d;
    }

    /* First find a solution using the block's PCA. */
    if (!find_optimal_solution(mode, minColor, maxColor, pParams, pResults, pComp_params))
        return 0;

    if (pComp_params->m_try_least_squares)
    {
        /* Now try to refine the solution using least squares by computing the
         * optimal endpoints from the current selectors. */
        vec4F xl, xh;
        vec4F_set_scalar(&xl, 0.0f);
        vec4F_set_scalar(&xh, 0.0f);
        if (pParams->m_has_alpha)
            compute_least_squares_endpoints_rgba(pParams->m_num_pixels, pResults->m_pSelectors, pParams->m_pSelector_weightsx, &xl, &xh, pParams->m_pPixels);
        else
            compute_least_squares_endpoints_rgb(pParams->m_num_pixels, pResults->m_pSelectors, pParams->m_pSelector_weightsx, &xl, &xh, pParams->m_pPixels);

        xl = vec4F_mul(&xl, (1.0f / 255.0f));
        xh = vec4F_mul(&xh, (1.0f / 255.0f));

        if (!find_optimal_solution(mode, xl, xh, pParams, pResults, pComp_params))
            return 0;
    }

    if (pComp_params->m_uber_level > 0)
    {
        uint8_t  selectors_temp[16], selectors_temp1[16];
        int      max_selector;
        uint32_t min_sel = 16;
        uint32_t max_sel = 0;
        vec4F    xl, xh;
        uint32_t uber_err_thresh;

        memcpy(selectors_temp, pResults->m_pSelectors, pParams->m_num_pixels);

        max_selector = pParams->m_num_selector_weights - 1;

        for (uint32_t i = 0; i < pParams->m_num_pixels; i++)
        {
            uint32_t sel = selectors_temp[i];
            min_sel = minimumu(min_sel, sel);
            max_sel = maximumu(max_sel, sel);
        }

        for (uint32_t i = 0; i < pParams->m_num_pixels; i++)
        {
            uint32_t sel = selectors_temp[i];
            if ((sel == min_sel) && (sel < (pParams->m_num_selector_weights - 1)))
                sel++;
            selectors_temp1[i] = (uint8_t)sel;
        }

        vec4F_set_scalar(&xl, 0.0f);
        vec4F_set_scalar(&xh, 0.0f);
        if (pParams->m_has_alpha)
            compute_least_squares_endpoints_rgba(pParams->m_num_pixels, selectors_temp1, pParams->m_pSelector_weightsx, &xl, &xh, pParams->m_pPixels);
        else
            compute_least_squares_endpoints_rgb(pParams->m_num_pixels, selectors_temp1, pParams->m_pSelector_weightsx, &xl, &xh, pParams->m_pPixels);

        xl = vec4F_mul(&xl, (1.0f / 255.0f));
        xh = vec4F_mul(&xh, (1.0f / 255.0f));

        if (!find_optimal_solution(mode, xl, xh, pParams, pResults, pComp_params))
            return 0;

        for (uint32_t i = 0; i < pParams->m_num_pixels; i++)
        {
            uint32_t sel = selectors_temp[i];
            if ((sel == max_sel) && (sel > 0))
                sel--;
            selectors_temp1[i] = (uint8_t)sel;
        }

        if (pParams->m_has_alpha)
            compute_least_squares_endpoints_rgba(pParams->m_num_pixels, selectors_temp1, pParams->m_pSelector_weightsx, &xl, &xh, pParams->m_pPixels);
        else
            compute_least_squares_endpoints_rgb(pParams->m_num_pixels, selectors_temp1, pParams->m_pSelector_weightsx, &xl, &xh, pParams->m_pPixels);

        xl = vec4F_mul(&xl, (1.0f / 255.0f));
        xh = vec4F_mul(&xh, (1.0f / 255.0f));

        if (!find_optimal_solution(mode, xl, xh, pParams, pResults, pComp_params))
            return 0;

        for (uint32_t i = 0; i < pParams->m_num_pixels; i++)
        {
            uint32_t sel = selectors_temp[i];
            if ((sel == min_sel) && (sel < (pParams->m_num_selector_weights - 1)))
                sel++;
            else if ((sel == max_sel) && (sel > 0))
                sel--;
            selectors_temp1[i] = (uint8_t)sel;
        }

        if (pParams->m_has_alpha)
            compute_least_squares_endpoints_rgba(pParams->m_num_pixels, selectors_temp1, pParams->m_pSelector_weightsx, &xl, &xh, pParams->m_pPixels);
        else
            compute_least_squares_endpoints_rgb(pParams->m_num_pixels, selectors_temp1, pParams->m_pSelector_weightsx, &xl, &xh, pParams->m_pPixels);

        xl = vec4F_mul(&xl, (1.0f / 255.0f));
        xh = vec4F_mul(&xh, (1.0f / 255.0f));

        if (!find_optimal_solution(mode, xl, xh, pParams, pResults, pComp_params))
            return 0;

        /* In uber levels 2+, try taking more advantage of endpoint
         * extrapolation by scaling the selectors in one direction or another. */
        uber_err_thresh = (pParams->m_num_pixels * 56) >> 4;
        if ((pComp_params->m_uber_level >= 2) && (pResults->m_best_overall_err > uber_err_thresh))
        {
            const int Q = (pComp_params->m_uber_level >= 4) ? (pComp_params->m_uber_level - 2) : 1;
            for (int ly = -Q; ly <= 1; ly++)
            {
                for (int hy = max_selector - 1; hy <= (max_selector + Q); hy++)
                {
                    if ((ly == 0) && (hy == max_selector))
                        continue;

                    for (uint32_t i = 0; i < pParams->m_num_pixels; i++)
                        selectors_temp1[i] = (uint8_t)clampf(floorf((float)max_selector * ((float)selectors_temp[i] - (float)ly) / ((float)hy - (float)ly) + .5f), 0, (float)max_selector);

                    vec4F_set_scalar(&xl, 0.0f);
                    vec4F_set_scalar(&xh, 0.0f);
                    if (pParams->m_has_alpha)
                        compute_least_squares_endpoints_rgba(pParams->m_num_pixels, selectors_temp1, pParams->m_pSelector_weightsx, &xl, &xh, pParams->m_pPixels);
                    else
                        compute_least_squares_endpoints_rgb(pParams->m_num_pixels, selectors_temp1, pParams->m_pSelector_weightsx, &xl, &xh, pParams->m_pPixels);

                    xl = vec4F_mul(&xl, (1.0f / 255.0f));
                    xh = vec4F_mul(&xh, (1.0f / 255.0f));

                    if (!find_optimal_solution(mode, xl, xh, pParams, pResults, pComp_params))
                        return 0;
                }
            }
        }
    }

    if (mode == 1)
    {
        /* Try encoding the partition as a single color by using the optimal
         * singe colors tables to encode the block to its mean. */
        color_cell_compressor_results avg_results = *pResults;
        const uint32_t r = (int)(.5f + meanColor.m_c[0] * 255.0f), g = (int)(.5f + meanColor.m_c[1] * 255.0f), b = (int)(.5f + meanColor.m_c[2] * 255.0f);
        uint64_t avg_err = pack_mode1_to_one_color(pParams, &avg_results, r, g, b, pResults->m_pSelectors_temp);
        if (avg_err < pResults->m_best_overall_err)
        {
            *pResults = avg_results;
            memcpy(pResults->m_pSelectors, pResults->m_pSelectors_temp, sizeof(pResults->m_pSelectors[0]) * pParams->m_num_pixels);
            pResults->m_best_overall_err = avg_err;
        }
    }
    else if (mode == 7)
    {
        /* Try encoding the partition as a single color by using the optimal
         * singe colors tables to encode the block to its mean. */
        color_cell_compressor_results avg_results = *pResults;
        const uint32_t r = (int)(.5f + meanColor.m_c[0] * 255.0f), g = (int)(.5f + meanColor.m_c[1] * 255.0f), b = (int)(.5f + meanColor.m_c[2] * 255.0f), a = (int)(.5f + meanColor.m_c[3] * 255.0f);
        uint64_t avg_err = pack_mode7_to_one_color(pParams, &avg_results, r, g, b, a, pResults->m_pSelectors_temp, pParams->m_num_pixels, pParams->m_pPixels);
        if (avg_err < pResults->m_best_overall_err)
        {
            *pResults = avg_results;
            memcpy(pResults->m_pSelectors, pResults->m_pSelectors_temp, sizeof(pResults->m_pSelectors[0]) * pParams->m_num_pixels);
            pResults->m_best_overall_err = avg_err;
        }
    }

    return pResults->m_best_overall_err;
}

static uint64_t color_cell_compression_est_mode1(uint32_t num_pixels, const color_rgba *pPixels, gboolean perceptual, uint32_t pweights[4], uint64_t best_err_so_far)
{
    /* Find RGB bounds as an approximation of the block's principle axis */
    uint32_t   lr = 255, lg = 255, lb = 255;
    uint32_t   hr = 0, hg = 0, hb = 0;
    int        ar;
    int        ag;
    int        ab;
    int        dots[8];
    int        thresh[8 - 1];
    uint64_t   total_err = 0;
    color_rgba lowColor;
    color_rgba highColor;
    uint32_t   N = 8;
    color_rgba weightedColors[8];

    for (uint32_t i = 0; i < num_pixels; i++)
    {
        const color_rgba *pC = &pPixels[i];
        if (pC->m_c[0] < lr) lr = pC->m_c[0];
        if (pC->m_c[1] < lg) lg = pC->m_c[1];
        if (pC->m_c[2] < lb) lb = pC->m_c[2];
        if (pC->m_c[0] > hr) hr = pC->m_c[0];
        if (pC->m_c[1] > hg) hg = pC->m_c[1];
        if (pC->m_c[2] > hb) hb = pC->m_c[2];
    }

    color_quad_u8_set(&lowColor, lr, lg, lb, 0);
    color_quad_u8_set(&highColor, hr, hg, hb, 0);

    /* Place endpoints at bbox diagonals and compute interpolated colors */

    weightedColors[0] = lowColor;
    weightedColors[N - 1] = highColor;
    for (uint32_t i = 1; i < (N - 1); i++)
    {
        weightedColors[i].m_c[0] = (uint8_t)((lowColor.m_c[0] * (64 - g_bc7_weights3[i]) + highColor.m_c[0] * g_bc7_weights3[i] + 32) >> 6);
        weightedColors[i].m_c[1] = (uint8_t)((lowColor.m_c[1] * (64 - g_bc7_weights3[i]) + highColor.m_c[1] * g_bc7_weights3[i] + 32) >> 6);
        weightedColors[i].m_c[2] = (uint8_t)((lowColor.m_c[2] * (64 - g_bc7_weights3[i]) + highColor.m_c[2] * g_bc7_weights3[i] + 32) >> 6);
    }

    /* Compute dots and thresholds */
    ar = highColor.m_c[0] - lowColor.m_c[0];
    ag = highColor.m_c[1] - lowColor.m_c[1];
    ab = highColor.m_c[2] - lowColor.m_c[2];

    for (uint32_t i = 0; i < N; i++)
        dots[i] = weightedColors[i].m_c[0] * ar + weightedColors[i].m_c[1] * ag + weightedColors[i].m_c[2] * ab;

    for (uint32_t i = 0; i < (N - 1); i++)
        thresh[i] = (dots[i] + dots[i + 1] + 1) >> 1;

    if (perceptual)
    {
        /* Transform block's interpolated colors to YCbCr */
        int l1[8], cr1[8], cb1[8];
        for (int j = 0; j < 8; j++)
        {
            const color_rgba *pE1 = &weightedColors[j];
            l1[j] = pE1->m_c[0] * 109 + pE1->m_c[1] * 366 + pE1->m_c[2] * 37;
            cr1[j] = ((int)pE1->m_c[0] << 9) - l1[j];
            cb1[j] = ((int)pE1->m_c[2] << 9) - l1[j];
        }

        for (uint32_t i = 0; i < num_pixels; i++)
        {
            const color_rgba *pC = &pPixels[i];
            int   l2;
            int   cr2;
            int   cb2;
            int   dl;
            int   dcr;
            int   dcb;
            int   ie;

            int d = ar * pC->m_c[0] + ag * pC->m_c[1] + ab * pC->m_c[2];

            /* Find approximate selector */
            uint32_t s = 0;
            if (d >= thresh[6])
                s = 7;
            else if (d >= thresh[5])
                s = 6;
            else if (d >= thresh[4])
                s = 5;
            else if (d >= thresh[3])
                s = 4;
            else if (d >= thresh[2])
                s = 3;
            else if (d >= thresh[1])
                s = 2;
            else if (d >= thresh[0])
                s = 1;

            /* Compute error */
            l2 = pC->m_c[0] * 109 + pC->m_c[1] * 366 + pC->m_c[2] * 37;
            cr2 = ((int)pC->m_c[0] << 9) - l2;
            cb2 = ((int)pC->m_c[2] << 9) - l2;

            dl = (l1[s] - l2) >> 8;
            dcr = (cr1[s] - cr2) >> 8;
            dcb = (cb1[s] - cb2) >> 8;

            ie = (pweights[0] * dl * dl) + (pweights[1] * dcr * dcr) + (pweights[2] * dcb * dcb);

            total_err += ie;
            if (total_err > best_err_so_far)
                break;
        }
    }
    else
    {
        for (uint32_t i = 0; i < num_pixels; i++)
        {
            const color_rgba *pC = &pPixels[i];
            color_rgba       *pE1;
            int               dr;
            int               dg;
            int               db;


            int d = ar * pC->m_c[0] + ag * pC->m_c[1] + ab * pC->m_c[2];

            /* Find approximate selector */
            uint32_t s = 0;
            if (d >= thresh[6])
                s = 7;
            else if (d >= thresh[5])
                s = 6;
            else if (d >= thresh[4])
                s = 5;
            else if (d >= thresh[3])
                s = 4;
            else if (d >= thresh[2])
                s = 3;
            else if (d >= thresh[1])
                s = 2;
            else if (d >= thresh[0])
                s = 1;

            /* Compute error */
            pE1 = &weightedColors[s];

            dr = (int)pE1->m_c[0] - (int)pC->m_c[0];
            dg = (int)pE1->m_c[1] - (int)pC->m_c[1];
            db = (int)pE1->m_c[2] - (int)pC->m_c[2];

            total_err += pweights[0] * (dr * dr) + pweights[1] * (dg * dg) + pweights[2] * (db * db);
            if (total_err > best_err_so_far)
                break;
        }
    }

    return total_err;
}

static uint64_t color_cell_compression_est_mode7(uint32_t num_pixels, const color_rgba * pPixels, gboolean perceptual, uint32_t pweights[4], uint64_t best_err_so_far)
{
    /* Find RGB bounds as an approximation of the block's principle axis */
    uint32_t   lr = 255, lg = 255, lb = 255, la = 255;
    uint32_t   hr = 0, hg = 0, hb = 0, ha = 0;
    color_rgba lowColor;
    color_rgba highColor;
    uint32_t   N = 4;
    color_rgba weightedColors[4];
    int        ar;
    int        ag;
    int        ab;
    int        aa;
    int        dots[4];
    int        thresh[4 - 1];
    uint64_t   total_err = 0;


    for (uint32_t i = 0; i < num_pixels; i++)
    {
        const color_rgba* pC = &pPixels[i];
        if (pC->m_c[0] < lr) lr = pC->m_c[0];
        if (pC->m_c[1] < lg) lg = pC->m_c[1];
        if (pC->m_c[2] < lb) lb = pC->m_c[2];
        if (pC->m_c[3] < la) la = pC->m_c[3];

        if (pC->m_c[0] > hr) hr = pC->m_c[0];
        if (pC->m_c[1] > hg) hg = pC->m_c[1];
        if (pC->m_c[2] > hb) hb = pC->m_c[2];
        if (pC->m_c[3] > ha) ha = pC->m_c[3];
    }

    color_quad_u8_set(&lowColor, lr, lg, lb, la);
    color_quad_u8_set(&highColor, hr, hg, hb, ha);

    /* Place endpoints at bbox diagonals and compute interpolated colors  */
    weightedColors[0] = lowColor;
    weightedColors[N - 1] = highColor;
    for (uint32_t i = 1; i < (N - 1); i++)
    {
        weightedColors[i].m_c[0] = (uint8_t)((lowColor.m_c[0] * (64 - g_bc7_weights2[i]) + highColor.m_c[0] * g_bc7_weights2[i] + 32) >> 6);
        weightedColors[i].m_c[1] = (uint8_t)((lowColor.m_c[1] * (64 - g_bc7_weights2[i]) + highColor.m_c[1] * g_bc7_weights2[i] + 32) >> 6);
        weightedColors[i].m_c[2] = (uint8_t)((lowColor.m_c[2] * (64 - g_bc7_weights2[i]) + highColor.m_c[2] * g_bc7_weights2[i] + 32) >> 6);
        weightedColors[i].m_c[3] = (uint8_t)((lowColor.m_c[3] * (64 - g_bc7_weights2[i]) + highColor.m_c[3] * g_bc7_weights2[i] + 32) >> 6);
    }

    /* Compute dots and thresholds */
    ar = highColor.m_c[0] - lowColor.m_c[0];
    ag = highColor.m_c[1] - lowColor.m_c[1];
    ab = highColor.m_c[2] - lowColor.m_c[2];
    aa = highColor.m_c[3] - lowColor.m_c[3];

    for (uint32_t i = 0; i < N; i++)
        dots[i] = weightedColors[i].m_c[0] * ar + weightedColors[i].m_c[1] * ag + weightedColors[i].m_c[2] * ab + weightedColors[i].m_c[3] * aa;

    for (uint32_t i = 0; i < (N - 1); i++)
        thresh[i] = (dots[i] + dots[i + 1] + 1) >> 1;

    if (perceptual)
    {
        /* Transform block's interpolated colors to YCbCr */
        int l1[4], cr1[4], cb1[4];
        for (int j = 0; j < 4; j++)
        {
            const color_rgba* pE1 = &weightedColors[j];
            l1[j] = pE1->m_c[0] * 109 + pE1->m_c[1] * 366 + pE1->m_c[2] * 37;
            cr1[j] = ((int)pE1->m_c[0] << 9) - l1[j];
            cb1[j] = ((int)pE1->m_c[2] << 9) - l1[j];
        }

        for (uint32_t i = 0; i < num_pixels; i++)
        {
            const color_rgba* pC = &pPixels[i];
            int   l2;
            int   cr2;
            int   cb2;
            int   dl;
            int   dcr;
            int   dcb;
            int   dca;
            int   ie;

            int d = ar * pC->m_c[0] + ag * pC->m_c[1] + ab * pC->m_c[2] + aa * pC->m_c[3];

            /* Find approximate selector */
            uint32_t s = 0;
            if (d >= thresh[2])
                s = 3;
            else if (d >= thresh[1])
                s = 2;
            else if (d >= thresh[0])
                s = 1;

            /* Compute error */
            l2 = pC->m_c[0] * 109 + pC->m_c[1] * 366 + pC->m_c[2] * 37;
            cr2 = ((int)pC->m_c[0] << 9) - l2;
            cb2 = ((int)pC->m_c[2] << 9) - l2;

            dl = (l1[s] - l2) >> 8;
            dcr = (cr1[s] - cr2) >> 8;
            dcb = (cb1[s] - cb2) >> 8;

            dca = (int)pC->m_c[3] - (int)weightedColors[s].m_c[3];

            ie = (pweights[0] * dl * dl) + (pweights[1] * dcr * dcr) + (pweights[2] * dcb * dcb) + (pweights[3] * dca * dca);

            total_err += ie;
            if (total_err > best_err_so_far)
                break;
        }
    }
    else
    {
        for (uint32_t i = 0; i < num_pixels; i++)
        {
            const color_rgba* pC = &pPixels[i];
            color_rgba*       pE1;
            int               dr;
            int               dg;
            int               db;
            int               da;

            int d = ar * pC->m_c[0] + ag * pC->m_c[1] + ab * pC->m_c[2] + aa * pC->m_c[3];

            /* Find approximate selector */
            uint32_t s = 0;
            if (d >= thresh[2])
                s = 3;
            else if (d >= thresh[1])
                s = 2;
            else if (d >= thresh[0])
                s = 1;

            /* Compute error */
            pE1 = &weightedColors[s];

            dr = (int)pE1->m_c[0] - (int)pC->m_c[0];
            dg = (int)pE1->m_c[1] - (int)pC->m_c[1];
            db = (int)pE1->m_c[2] - (int)pC->m_c[2];
            da = (int)pE1->m_c[3] - (int)pC->m_c[3];

            total_err += pweights[0] * (dr * dr) + pweights[1] * (dg * dg) + pweights[2] * (db * db) + pweights[3] * (da * da);
            if (total_err > best_err_so_far)
                break;
        }
    }

    return total_err;
}

/* This table contains bitmasks indicating which "key" partitions must be best ranked before this partition is worth evaluating.
 * We first rank the best/most used 14 partitions (sorted by usefulness), record the best one found as the key partition, then use
 * that to control the other partitions to evaluate. The quality loss is ~.08 dB RGB PSNR, the perf gain is up to ~11% (at uber level 0). */
static const uint32_t g_partition_predictors[35] =
{
    UINT32_MAX,
    UINT32_MAX,
    UINT32_MAX,
    UINT32_MAX,
    UINT32_MAX,
    (1 << 1) | (1 << 2) | (1 << 8),
    (1 << 1) | (1 << 3) | (1 << 7),
    UINT32_MAX,
    UINT32_MAX,
    (1 << 2) | (1 << 8) | (1 << 16),
    (1 << 7) | (1 << 3) | (1 << 15),
    UINT32_MAX,
    (1 << 8) | (1 << 14) | (1 << 16),
    (1 << 7) | (1 << 14) | (1 << 15),
    UINT32_MAX,
    UINT32_MAX,
    UINT32_MAX,
    UINT32_MAX,
    (1 << 14) | (1 << 15),
    (1 << 16) | (1 << 22) | (1 << 14),
    (1 << 17) | (1 << 24) | (1 << 14),
    (1 << 2) | (1 << 14) | (1 << 15) | (1 << 1),
    UINT32_MAX,
    (1 << 1) | (1 << 3) | (1 << 14) | (1 << 16) | (1 << 22),
    UINT32_MAX,
    (1 << 1) | (1 << 2) | (1 << 15) | (1 << 17) | (1 << 24),
    (1 << 1) | (1 << 3) | (1 << 22),
    UINT32_MAX,
    UINT32_MAX,
    UINT32_MAX,
    (1 << 14) | (1 << 15) | (1 << 16) | (1 << 17),
    UINT32_MAX,
    UINT32_MAX,
    (1 << 1) | (1 << 2) | (1 << 3) | (1 << 27) | (1 << 4) | (1 << 24),
    (1 << 14) | (1 << 15) | (1 << 16) | (1 << 11) | (1 << 17) | (1 << 27)
};

/* Estimate the partition used by modes 1/7. This scans through each partition and computes an approximate error for each. */
static uint32_t estimate_partition(const color_rgba *pPixels, const bc7enc_compress_block_params *pComp_params, uint32_t pweights[4], uint32_t mode)
{
    const uint32_t total_partitions = minimumu(pComp_params->m_max_partitions, BC7ENC_MAX_PARTITIONS);
    uint64_t       best_err = UINT64_MAX;
    uint32_t       best_partition = 0;
    int            best_key_partition = 0;

    /* Partition order sorted by usage frequency across a large test corpus. Pattern 34 (checkerboard) must appear in slot 34.
     * Using a sorted order allows the user to decrease the # of partitions to scan with minimal loss in quality. */
    static const uint8_t s_sorted_partition_order[64] =
    {
        1 - 1, 14 - 1, 2 - 1, 3 - 1, 16 - 1, 15 - 1, 11 - 1, 17 - 1,
        4 - 1, 24 - 1, 27 - 1, 7 - 1, 8 - 1, 22 - 1, 20 - 1, 30 - 1,
        9 - 1, 5 - 1, 10 - 1, 21 - 1, 6 - 1, 32 - 1, 23 - 1, 18 - 1,
        19 - 1, 12 - 1, 13 - 1, 31 - 1, 25 - 1, 26 - 1, 29 - 1, 28 - 1,
        33 - 1, 34 - 1, 35 - 1, 46 - 1, 47 - 1, 52 - 1, 50 - 1, 51 - 1,
        49 - 1, 39 - 1, 40 - 1, 38 - 1, 54 - 1, 53 - 1, 55 - 1, 37 - 1,
        58 - 1, 59 - 1, 56 - 1, 42 - 1, 41 - 1, 43 - 1, 44 - 1, 60 - 1,
        45 - 1, 57 - 1, 48 - 1, 36 - 1, 61 - 1, 64 - 1, 63 - 1, 62 - 1
    };

    if (total_partitions <= 1)
        return 0;

    assert(s_sorted_partition_order[34] == 34);

    for (uint32_t partition_iter = 0; (partition_iter < total_partitions) && (best_err > 0); partition_iter++)
    {
        const uint32_t partition = s_sorted_partition_order[partition_iter];
        const uint8_t *pPartition = &g_bc7_partition2[partition * 16];
        color_rgba     subset_colors[2][16];
        uint32_t       subset_total_colors[2] = { 0, 0 };
        uint64_t       total_subset_err = 0;

        /* Check to see if we should bother evaluating this partition at all,
         * depending on the best partition found from the first 14. */
        if (pComp_params->m_mode17_partition_estimation_filterbank)
        {
            if ((partition_iter >= 14) && (partition_iter <= 34))
            {
                const uint32_t best_key_partition_bitmask = 1 << (best_key_partition + 1);
                if ((g_partition_predictors[partition] & best_key_partition_bitmask) == 0)
                {
                    if (partition_iter == 34)
                        break;

                    continue;
                }
            }
        }

        for (uint32_t index = 0; index < 16; index++)
            subset_colors[pPartition[index]][subset_total_colors[pPartition[index]]++] = pPixels[index];


        for (uint32_t subset = 0; (subset < 2) && (total_subset_err < best_err); subset++)
        {
            if (mode == 7)
                total_subset_err += color_cell_compression_est_mode7(subset_total_colors[subset], &subset_colors[subset][0], pComp_params->m_perceptual, pweights, best_err);
            else
                total_subset_err += color_cell_compression_est_mode1(subset_total_colors[subset], &subset_colors[subset][0], pComp_params->m_perceptual, pweights, best_err);
        }

        if (partition < 16)
        {
            total_subset_err = (uint64_t)((double)total_subset_err * pComp_params->m_low_frequency_partition_weight + .5f);
        }

        if (total_subset_err < best_err)
        {
            best_err = total_subset_err;
            best_partition = partition;
        }

        /* If the checkerboard pattern doesn't get the highest ranking vs. the previous (lower frequency) patterns,
         * then just stop now because statistically the subsequent patterns won't do well either. */
        if ((partition == 34) && (best_partition != 34))
            break;

        if (partition_iter == 13)
            best_key_partition = best_partition;

    }

    return best_partition;
}

static void set_block_bits(uint8_t *pBytes, uint32_t val, uint32_t num_bits, uint32_t *pCur_ofs)
{
    assert((num_bits <= 32) && (val < (1ULL << num_bits)));
    while (num_bits)
    {
        const uint32_t n = minimumu(8 - (*pCur_ofs & 7), num_bits);
        pBytes[*pCur_ofs >> 3] |= (uint8_t)(val << (*pCur_ofs & 7));
        val >>= n;
        num_bits -= n;
        *pCur_ofs += n;
    }
    assert(*pCur_ofs <= 128);
}

void encode_bc7_block(void* pBlock, const bc7_optimization_results* pResults)
{
    const uint32_t best_mode = pResults->m_mode;

    const uint32_t total_subsets = g_bc7_num_subsets[best_mode];
    const uint32_t total_partitions = 1 << g_bc7_partition_bits[best_mode];

    const uint8_t *pPartition;
    uint8_t        color_selectors[16];
    uint8_t        alpha_selectors[16];
    color_rgba     low[3], high[3];
    uint32_t       pbits[3][2];
    int            anchor[3] = { -1, -1, -1 };
    uint8_t       *pBlock_bytes;
    uint32_t       cur_bit_ofs = 0;
    uint32_t       total_comps;

    assert(pResults->m_index_selector <= 1);
    assert(pResults->m_rotation <= 3);

    if (total_subsets == 1)
        pPartition = &g_bc7_partition1[0];
    else if (total_subsets == 2)
        pPartition = &g_bc7_partition2[pResults->m_partition * 16];
    else
        pPartition = &g_bc7_partition3[pResults->m_partition * 16];

    memcpy(color_selectors, pResults->m_selectors, 16);

    memcpy(alpha_selectors, pResults->m_alpha_selectors, 16);

    memcpy(low, pResults->m_low, sizeof(low));
    memcpy(high, pResults->m_high, sizeof(high));

    memcpy(pbits, pResults->m_pbits, sizeof(pbits));

    for (uint32_t k = 0; k < total_subsets; k++)
    {
        uint32_t anchor_index = 0;
        uint32_t color_index_bits;
        uint32_t num_color_indices;

        if (k)
        {
            if ((total_subsets == 3) && (k == 1))
                anchor_index = g_bc7_table_anchor_index_third_subset_1[pResults->m_partition];
            else if ((total_subsets == 3) && (k == 2))
                anchor_index = g_bc7_table_anchor_index_third_subset_2[pResults->m_partition];
            else
                anchor_index = g_bc7_table_anchor_index_second_subset[pResults->m_partition];
        }

        anchor[k] = anchor_index;

        color_index_bits = get_bc7_color_index_size(best_mode, pResults->m_index_selector);
        num_color_indices = 1 << color_index_bits;

        if (color_selectors[anchor_index] & (num_color_indices >> 1))
        {
            for (uint32_t i = 0; i < 16; i++)
                if (pPartition[i] == k)
                    color_selectors[i] = (uint8_t)((num_color_indices - 1) - color_selectors[i]);

            if (get_bc7_mode_has_seperate_alpha_selectors(best_mode))
            {
                for (uint32_t q = 0; q < 3; q++)
                {
                    uint8_t t = low[k].m_c[q];
                    low[k].m_c[q] = high[k].m_c[q];
                    high[k].m_c[q] = t;
                }
            }
            else
            {
                color_rgba tmp = low[k];
                low[k] = high[k];
                high[k] = tmp;
            }

            if (!g_bc7_mode_has_shared_p_bits[best_mode])
            {
                uint32_t t = pbits[k][0];
                pbits[k][0] = pbits[k][1];
                pbits[k][1] = t;
            }
        }

        if (get_bc7_mode_has_seperate_alpha_selectors(best_mode))
        {
            const uint32_t alpha_index_bits = get_bc7_alpha_index_size(best_mode, pResults->m_index_selector);
            const uint32_t num_alpha_indices = 1 << alpha_index_bits;

            if (alpha_selectors[anchor_index] & (num_alpha_indices >> 1))
            {
                uint8_t t;

                for (uint32_t i = 0; i < 16; i++)
                    if (pPartition[i] == k)
                        alpha_selectors[i] = (uint8_t)((num_alpha_indices - 1) - alpha_selectors[i]);

                t = low[k].m_c[3];
                low[k].m_c[3] = high[k].m_c[3];
                high[k].m_c[3] = t;
            }
        }
    }

    pBlock_bytes = (uint8_t*)(pBlock);
    memset(pBlock_bytes, 0, BC7ENC_BLOCK_SIZE);

    set_block_bits(pBlock_bytes, 1 << best_mode, best_mode + 1, &cur_bit_ofs);

    if ((best_mode == 4) || (best_mode == 5))
        set_block_bits(pBlock_bytes, pResults->m_rotation, 2, &cur_bit_ofs);

    if (best_mode == 4)
        set_block_bits(pBlock_bytes, pResults->m_index_selector, 1, &cur_bit_ofs);

    if (total_partitions > 1)
        set_block_bits(pBlock_bytes, pResults->m_partition, (total_partitions == 64) ? 6 : 4, &cur_bit_ofs);

    total_comps = (best_mode >= 4) ? 4 : 3;
    for (uint32_t comp = 0; comp < total_comps; comp++)
    {
        for (uint32_t subset = 0; subset < total_subsets; subset++)
        {
            set_block_bits(pBlock_bytes, low[subset].m_c[comp], (comp == 3) ? g_bc7_alpha_precision_table[best_mode] : g_bc7_color_precision_table[best_mode], &cur_bit_ofs);
            set_block_bits(pBlock_bytes, high[subset].m_c[comp], (comp == 3) ? g_bc7_alpha_precision_table[best_mode] : g_bc7_color_precision_table[best_mode], &cur_bit_ofs);
        }
    }

    if (g_bc7_mode_has_p_bits[best_mode])
    {
        for (uint32_t subset = 0; subset < total_subsets; subset++)
        {
            set_block_bits(pBlock_bytes, pbits[subset][0], 1, &cur_bit_ofs);
            if (!g_bc7_mode_has_shared_p_bits[best_mode])
                set_block_bits(pBlock_bytes, pbits[subset][1], 1, &cur_bit_ofs);
        }
    }

    for (uint32_t y = 0; y < 4; y++)
    {
        for (uint32_t x = 0; x < 4; x++)
        {
            int idx = x + y * 4;

            uint32_t n = pResults->m_index_selector ? get_bc7_alpha_index_size(best_mode, pResults->m_index_selector) : get_bc7_color_index_size(best_mode, pResults->m_index_selector);

            if ((idx == anchor[0]) || (idx == anchor[1]) || (idx == anchor[2]))
                n--;

            set_block_bits(pBlock_bytes, pResults->m_index_selector ? alpha_selectors[idx] : color_selectors[idx], n, &cur_bit_ofs);
        }
    }

    if (get_bc7_mode_has_seperate_alpha_selectors(best_mode))
    {
        for (uint32_t y = 0; y < 4; y++)
        {
            for (uint32_t x = 0; x < 4; x++)
            {
                int idx = x + y * 4;

                uint32_t n = pResults->m_index_selector ? get_bc7_color_index_size(best_mode, pResults->m_index_selector) : get_bc7_alpha_index_size(best_mode, pResults->m_index_selector);

                if ((idx == anchor[0]) || (idx == anchor[1]) || (idx == anchor[2]))
                    n--;

                set_block_bits(pBlock_bytes, pResults->m_index_selector ? color_selectors[idx] : alpha_selectors[idx], n, &cur_bit_ofs);
            }
        }
    }

    assert(cur_bit_ofs == 128);
}

static void handle_alpha_block_mode5(const color_rgba* pPixels,
                                     const bc7enc_compress_block_params* pComp_params,
                                     color_cell_compressor_params* pParams,
                                     uint32_t lo_a,
                                     uint32_t hi_a,
                                     bc7_optimization_results* pOpt_results5,
                                     uint64_t* pMode5_err,
                                     uint64_t* pMode5_alpha_err)
{
    uint8_t                       selectors_temp[16];
    color_cell_compressor_results results5;

    pParams->m_pSelector_weights = g_bc7_weights2;
    pParams->m_pSelector_weightsx = (const vec4F*)g_bc7_weights2x;
    pParams->m_num_selector_weights = 4;

    pParams->m_comp_bits = 7;
    pParams->m_has_pbits = FALSE;
    pParams->m_endpoints_share_pbit = FALSE;
    pParams->m_has_alpha = FALSE;

    pParams->m_perceptual = pComp_params->m_perceptual;

    pParams->m_num_pixels = 16;
    pParams->m_pPixels = pPixels;

    results5.m_pSelectors = pOpt_results5->m_selectors;

    results5.m_pSelectors_temp = selectors_temp;

    *pMode5_err = color_cell_compression(5, pParams, &results5, pComp_params);
    assert(*pMode5_err == results5.m_best_overall_err);

    pOpt_results5->m_low[0] = results5.m_low_endpoint;
    pOpt_results5->m_high[0] = results5.m_high_endpoint;

    if (lo_a == hi_a)
    {
        *pMode5_alpha_err = 0;
        pOpt_results5->m_low[0].m_c[3] = (uint8_t)lo_a;
        pOpt_results5->m_high[0].m_c[3] = (uint8_t)hi_a;
        memset(pOpt_results5->m_alpha_selectors, 0, sizeof(pOpt_results5->m_alpha_selectors));
    }
    else
    {
        const uint32_t total_passes = (pComp_params->m_uber_level >= 1) ? 3 : 2;

        *pMode5_alpha_err = UINT64_MAX;
        for (uint32_t pass = 0; pass < total_passes; pass++)
        {
            int32_t       vals[4];
            const int32_t w_s1 = 21, w_s2 = 43;
            uint8_t       trial_alpha_selectors[16];
            uint64_t      trial_alpha_err = 0;

            vals[0] = lo_a;
            vals[3] = hi_a;

            vals[1] = (vals[0] * (64 - w_s1) + vals[3] * w_s1 + 32) >> 6;
            vals[2] = (vals[0] * (64 - w_s2) + vals[3] * w_s2 + 32) >> 6;

            for (uint32_t i = 0; i < 16; i++)
            {
                const int32_t a = pParams->m_pPixels[i].m_c[3];
                uint32_t      a_err;

                int s = 0;
                int32_t be = iabs32(a - vals[0]);
                int e = iabs32(a - vals[1]); if (e < be) { be = e; s = 1; }
                e = iabs32(a - vals[2]); if (e < be) { be = e; s = 2; }
                e = iabs32(a - vals[3]); if (e < be) { be = e; s = 3; }

                trial_alpha_selectors[i] = (uint8_t)s;

                a_err = (uint32_t)(be * be) * pParams->m_weights[3];

                trial_alpha_err += a_err;
            }

            if (trial_alpha_err < *pMode5_alpha_err)
            {
                *pMode5_alpha_err = trial_alpha_err;
                pOpt_results5->m_low[0].m_c[3] = (uint8_t)lo_a;
                pOpt_results5->m_high[0].m_c[3] = (uint8_t)hi_a;
                memcpy(pOpt_results5->m_alpha_selectors, trial_alpha_selectors, sizeof(pOpt_results5->m_alpha_selectors));
            }

            if (pass != (total_passes - 1U))
            {
                float    xl, xh;
                uint32_t new_lo_a;
                uint32_t new_hi_a;

                compute_least_squares_endpoints_a(16, trial_alpha_selectors, (const vec4F*)g_bc7_weights2x, &xl, &xh, pParams->m_pPixels);

                new_lo_a = clampi((int)floor(xl + .5f), 0, 255);
                new_hi_a = clampi((int)floor(xh + .5f), 0, 255);
                if (new_lo_a > new_hi_a)
                    swapu(&new_lo_a, &new_hi_a);

                if ((new_lo_a == lo_a) && (new_hi_a == hi_a))
                    break;

                lo_a = new_lo_a;
                hi_a = new_hi_a;
            }
        }

        *pMode5_err += *pMode5_alpha_err;
    }
}

static void handle_alpha_block(void *pBlock, const color_rgba *pPixels, const bc7enc_compress_block_params *pComp_params, color_cell_compressor_params *pParams)
{
    uint64_t                      best_err = UINT64_MAX;
    uint32_t                      best_mode = 0;
    uint8_t                       selectors_temp[16];
    bc7_optimization_results      opt_results6, opt_results5, opt_results7;
    color_cell_compressor_results results6;


    assert((pComp_params->m_mode_mask & (1 << 6)) || (pComp_params->m_mode_mask & (1 << 5)) || (pComp_params->m_mode_mask & (1 << 7)));

    pParams->m_pSelector_weights = g_bc7_weights4;
    pParams->m_pSelector_weightsx = (const vec4F *)g_bc7_weights4x;
    pParams->m_num_selector_weights = 16;
    pParams->m_comp_bits = 7;
    pParams->m_has_pbits = TRUE;
    pParams->m_endpoints_share_pbit = FALSE;
    pParams->m_has_alpha = TRUE;
    pParams->m_perceptual = pComp_params->m_perceptual;
    pParams->m_num_pixels = 16;
    pParams->m_pPixels = pPixels;

    memset(&results6, 0, sizeof(results6));

    if (pComp_params->m_mode_mask & (1 << 6))
    {
        results6.m_pSelectors = opt_results6.m_selectors;
        results6.m_pSelectors_temp = selectors_temp;

        best_err = (uint64_t)(color_cell_compression(6, pParams, &results6, pComp_params) * pComp_params->m_mode6_error_weight + .5f);
        best_mode = 6;
    }

    if ((best_err > 0) && (pComp_params->m_mode_mask & (1 << 5)))
    {
        uint32_t lo_a = 255, hi_a = 0;
        uint64_t mode5_err, mode5_alpha_err;

        for (uint32_t i = 0; i < 16; i++)
        {
            uint32_t a = pPixels[i].m_c[3];
            lo_a = minimumu(lo_a, a);
            hi_a = maximumu(hi_a, a);
        }

        handle_alpha_block_mode5(pPixels, pComp_params, pParams, lo_a, hi_a, &opt_results5, &mode5_err, &mode5_alpha_err);

        mode5_err = (uint64_t)(mode5_err * pComp_params->m_mode5_error_weight + .5f);

        if (mode5_err < best_err)
        {
            best_err = mode5_err;
            best_mode = 5;
        }
    }

    if ((best_err > 0) && (pComp_params->m_mode_mask & (1 << 7)))
    {
        const uint32_t trial_partition = estimate_partition(pPixels, pComp_params, pParams->m_weights, 7);
        const uint8_t *pPartition = &g_bc7_partition2[trial_partition * 16];
        color_rgba     subset_colors[2][16];
        uint32_t       subset_total_colors7[2] = { 0, 0 };
        uint8_t        subset_pixel_index7[2][16];
        uint8_t        subset_selectors7[2][16];
        color_cell_compressor_results subset_results7[2];
        uint64_t       trial_err = 0;
        uint64_t       mode7_trial_err;

        pParams->m_pSelector_weights = g_bc7_weights2;
        pParams->m_pSelector_weightsx = (const vec4F*)g_bc7_weights2x;
        pParams->m_num_selector_weights = 4;
        pParams->m_comp_bits = 5;
        pParams->m_has_pbits = TRUE;
        pParams->m_endpoints_share_pbit = FALSE;
        pParams->m_has_alpha = TRUE;

        for (uint32_t idx = 0; idx < 16; idx++)
        {
            const uint32_t p = pPartition[idx];
            subset_colors[p][subset_total_colors7[p]] = pPixels[idx];
            subset_pixel_index7[p][subset_total_colors7[p]] = (uint8_t)idx;
            subset_total_colors7[p]++;
        }

        for (uint32_t subset = 0; subset < 2; subset++)
        {
            uint64_t                       err;
            color_cell_compressor_results *pResults;

            pParams->m_num_pixels = subset_total_colors7[subset];
            pParams->m_pPixels = &subset_colors[subset][0];

            pResults = &subset_results7[subset];
            pResults->m_pSelectors = &subset_selectors7[subset][0];
            pResults->m_pSelectors_temp = selectors_temp;
            err = color_cell_compression(7, pParams, pResults, pComp_params);
            trial_err += err;
            if ((uint64_t)(trial_err * pComp_params->m_mode7_error_weight + .5f) > best_err)
                break;

        } /* subset */

        mode7_trial_err = (uint64_t)(trial_err * pComp_params->m_mode7_error_weight + .5f);

        if (mode7_trial_err < best_err)
        {
            best_err = mode7_trial_err;
            best_mode = 7;
            opt_results7.m_mode = 7;
            opt_results7.m_partition = trial_partition;
            opt_results7.m_index_selector = 0;
            opt_results7.m_rotation = 0;
            for (uint32_t subset = 0; subset < 2; subset++)
            {
                for (uint32_t i = 0; i < subset_total_colors7[subset]; i++)
                    opt_results7.m_selectors[subset_pixel_index7[subset][i]] = subset_selectors7[subset][i];
                opt_results7.m_low[subset] = subset_results7[subset].m_low_endpoint;
                opt_results7.m_high[subset] = subset_results7[subset].m_high_endpoint;
                opt_results7.m_pbits[subset][0] = subset_results7[subset].m_pbits[0];
                opt_results7.m_pbits[subset][1] = subset_results7[subset].m_pbits[1];
            }
        }
    }

    if (best_mode == 7)
    {
        encode_bc7_block(pBlock, &opt_results7);
    }
    else if (best_mode == 5)
    {
        opt_results5.m_mode = 5;
        opt_results5.m_partition = 0;
        opt_results5.m_rotation = 0;
        opt_results5.m_index_selector = 0;

        encode_bc7_block(pBlock, &opt_results5);
    }
    else if (best_mode == 6)
    {
        opt_results6.m_mode = 6;
        opt_results6.m_partition = 0;
        opt_results6.m_low[0] = results6.m_low_endpoint;
        opt_results6.m_high[0] = results6.m_high_endpoint;
        opt_results6.m_pbits[0][0] = results6.m_pbits[0];
        opt_results6.m_pbits[0][1] = results6.m_pbits[1];
        opt_results6.m_rotation = 0;
        opt_results6.m_index_selector = 0;

        encode_bc7_block(pBlock, &opt_results6);
    }
    else
    {
        assert(0);
    }
}

static void handle_opaque_block(void *pBlock, const color_rgba *pPixels, const bc7enc_compress_block_params *pComp_params, color_cell_compressor_params *pParams)
{
    uint8_t                  selectors_temp[16];
    uint64_t                 best_err = UINT64_MAX;
    bc7_optimization_results opt_results;

    assert((pComp_params->m_mode_mask & (1 << 6)) || (pComp_params->m_mode_mask & (1 << 1)));

    pParams->m_perceptual = pComp_params->m_perceptual;
    pParams->m_num_pixels = 16;
    pParams->m_pPixels = pPixels;
    pParams->m_has_alpha = FALSE;

    opt_results.m_partition = 0;
    opt_results.m_index_selector = 0;
    opt_results.m_rotation = 0;

    /* Mode 6 */
    if (pComp_params->m_mode_mask & (1 << 6))
    {
        color_cell_compressor_results results6;

        pParams->m_pSelector_weights = g_bc7_weights4;
        pParams->m_pSelector_weightsx = (const vec4F*)g_bc7_weights4x;
        pParams->m_num_selector_weights = 16;
        pParams->m_comp_bits = 7;
        pParams->m_has_pbits = TRUE;
        pParams->m_endpoints_share_pbit = FALSE;

        results6.m_pSelectors = opt_results.m_selectors;
        results6.m_pSelectors_temp = selectors_temp;

        best_err = (uint64_t)(color_cell_compression(6, pParams, &results6, pComp_params) * pComp_params->m_mode6_error_weight + .5f);

        opt_results.m_mode = 6;
        opt_results.m_low[0] = results6.m_low_endpoint;
        opt_results.m_high[0] = results6.m_high_endpoint;
        opt_results.m_pbits[0][0] = results6.m_pbits[0];
        opt_results.m_pbits[0][1] = results6.m_pbits[1];
    }

    /* Mode 1 */
    if ((best_err > 0) && (pComp_params->m_max_partitions > 0) && (pComp_params->m_mode_mask & (1 << 1)))
    {
        const uint32_t trial_partition = estimate_partition(pPixels, pComp_params, pParams->m_weights, 1);
        uint64_t       mode1_trial_err;
        const uint8_t *pPartition = &g_bc7_partition2[trial_partition * 16];
        color_rgba     subset_colors[2][16];
        uint32_t       subset_total_colors1[2] = { 0, 0 };
        uint8_t        subset_pixel_index1[2][16];
        uint8_t        subset_selectors1[2][16];
        uint64_t       trial_err = 0;

        color_cell_compressor_results subset_results1[2];

        pParams->m_pSelector_weights = g_bc7_weights3;
        pParams->m_pSelector_weightsx = (const vec4F *)g_bc7_weights3x;
        pParams->m_num_selector_weights = 8;
        pParams->m_comp_bits = 6;
        pParams->m_has_pbits = TRUE;
        pParams->m_endpoints_share_pbit = TRUE;

        for (uint32_t idx = 0; idx < 16; idx++)
        {
            const uint32_t p = pPartition[idx];
            subset_colors[p][subset_total_colors1[p]] = pPixels[idx];
            subset_pixel_index1[p][subset_total_colors1[p]] = (uint8_t)idx;
            subset_total_colors1[p]++;
        }

        for (uint32_t subset = 0; subset < 2; subset++)
        {
            uint64_t                       err;
            color_cell_compressor_results *pResults;

            pParams->m_num_pixels = subset_total_colors1[subset];
            pParams->m_pPixels = &subset_colors[subset][0];

            pResults = &subset_results1[subset];
            pResults->m_pSelectors = &subset_selectors1[subset][0];
            pResults->m_pSelectors_temp = selectors_temp;
            err = color_cell_compression(1, pParams, pResults, pComp_params);

            trial_err += err;
            if ((uint64_t)(trial_err * pComp_params->m_mode1_error_weight + .5f) > best_err)
                break;

        } /* subset */

        mode1_trial_err = (uint64_t)(trial_err * pComp_params->m_mode1_error_weight + .5f);
        if (mode1_trial_err < best_err)
        {
            best_err = mode1_trial_err;
            opt_results.m_mode = 1;
            opt_results.m_partition = trial_partition;
            for (uint32_t subset = 0; subset < 2; subset++)
            {
                for (uint32_t i = 0; i < subset_total_colors1[subset]; i++)
                    opt_results.m_selectors[subset_pixel_index1[subset][i]] = subset_selectors1[subset][i];
                opt_results.m_low[subset] = subset_results1[subset].m_low_endpoint;
                opt_results.m_high[subset] = subset_results1[subset].m_high_endpoint;
                opt_results.m_pbits[subset][0] = subset_results1[subset].m_pbits[0];
            }
        }
    }

    encode_bc7_block(pBlock, &opt_results);
}

gboolean bc7enc_compress_block(void *pBlock, const void *pPixelsRGBA, const bc7enc_compress_block_params *pComp_params)
{
    const color_rgba             *pPixels = (const color_rgba *)(pPixelsRGBA);
    color_cell_compressor_params  params;

    assert(g_bc7_mode_1_optimal_endpoints[255][0].m_hi != 0);

    if (pComp_params->m_perceptual)
    {
        /* https://en.wikipedia.org/wiki/YCbCr#ITU-R_BT.709_conversion */
        const float pr_weight = (.5f / (1.0f - .2126f)) * (.5f / (1.0f - .2126f));
        const float pb_weight = (.5f / (1.0f - .0722f)) * (.5f / (1.0f - .0722f));
        params.m_weights[0] = (int)(pComp_params->m_weights[0] * 4.0f);
        params.m_weights[1] = (int)(pComp_params->m_weights[1] * 4.0f * pr_weight);
        params.m_weights[2] = (int)(pComp_params->m_weights[2] * 4.0f * pb_weight);
        params.m_weights[3] = pComp_params->m_weights[3] * 4;
    }
    else
        memcpy(params.m_weights, pComp_params->m_weights, sizeof(params.m_weights));

    if (pComp_params->m_force_alpha)
    {
        handle_alpha_block(pBlock, pPixels, pComp_params, &params);
        return TRUE;
    }

    for (uint32_t i = 0; i < 16; i++)
    {
        if (pPixels[i].m_c[3] < 255)
        {
            handle_alpha_block(pBlock, pPixels, pComp_params, &params);
            return TRUE;
        }
    }
    handle_opaque_block(pBlock, pPixels, pComp_params, &params);
    return FALSE;
}

/*
------------------------------------------------------------------------------
This software is available under 2 licenses -- choose whichever you prefer.
If you use this software in a product, attribution / credits is requested but not required.
------------------------------------------------------------------------------
ALTERNATIVE A - MIT License
Copyright(c) 2020-2021 Richard Geldreich, Jr.
Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files(the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and / or sell copies
of the Software, and to permit persons to whom the Software is furnished to do
so, subject to the following conditions :
The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
------------------------------------------------------------------------------
ALTERNATIVE B - Public Domain(www.unlicense.org)
This is free and unencumbered software released into the public domain.
Anyone is free to copy, modify, publish, use, compile, sell, or distribute this
software, either in source code form or as a compiled binary, for any purpose,
commercial or non - commercial, and by any means.
In jurisdictions that recognize copyright laws, the author or authors of this
software dedicate any and all copyright interest in the software to the public
domain.We make this dedication for the benefit of the public at large and to
the detriment of our heirs and successors.We intend this dedication to be an
overt act of relinquishment in perpetuity of all present and future rights to
this software under copyright law.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.IN NO EVENT SHALL THE
AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
------------------------------------------------------------------------------
*/

/* --- end plug-ins/field-io/file-dds/bc7enc_rdo/bc7enc.c --- */

/* --- begin plug-ins/field-io/file-dds/dds.c --- */
/*
 * DDS AmmoOS Image plugin
 *
 * Copyright (C) 2004-2012 Shawn Kirst <skirst@gmail.com>,
 * with parts (C) 2003 Arne Reuter <homepage@arnereuter.de> where specified.
 *
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public
 * License as published by the Free Software Foundation; either
 * version 2 of the License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; see the file COPYING.  If not, write to
 * the Free Software Foundation, 51 Franklin Street, Fifth Floor
 * Boston, MA 02110-1301, USA.
 */

#include "config.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <gtk/gtk.h>

#include <libgimp/ammoos.h>
#include <libgimp/gimpui.h>

#include <libgimp/stdplugins-intl.h>

#include "dds.h"
#include "ddsread.h"
#include "ddswrite.h"
#include "misc.h"


#define LOAD_PROC                "file-dds-load"
#define EXPORT_PROC              "file-dds-export"


typedef struct _Dds      Dds;
typedef struct _DdsClass DdsClass;

struct _Dds
{
  GimpPlugIn      parent_instance;
};

struct _DdsClass
{
  GimpPlugInClass parent_class;
};


#define DDS_TYPE  (dds_get_type ())
#define DDS(obj) (G_TYPE_CHECK_INSTANCE_CAST ((obj), DDS_TYPE, Dds))

GType                   dds_get_type         (void) G_GNUC_CONST;

static GList          * dds_query_procedures (GimpPlugIn            *plug_in);
static GimpProcedure  * dds_create_procedure (GimpPlugIn            *plug_in,
                                              const gchar           *name);

static GimpValueArray * dds_load             (GimpProcedure         *procedure,
                                              GimpRunMode            run_mode,
                                              GFile                 *file,
                                              GimpMetadata          *metadata,
                                              GimpMetadataLoadFlags *flags,
                                              GimpProcedureConfig   *config,
                                              gpointer               run_data);
static GimpValueArray * dds_export           (GimpProcedure         *procedure,
                                              GimpRunMode            run_mode,
                                              GimpImage             *image,
                                              GFile                 *file,
                                              GimpExportOptions     *options,
                                              GimpMetadata          *metadata,
                                              GimpProcedureConfig   *config,
                                              gpointer               run_data);


G_DEFINE_TYPE (Dds, dds, GIMP_TYPE_PLUG_IN)

GIMP_MAIN (DDS_TYPE)
DEFINE_STD_SET_I18N


static void
dds_class_init (DdsClass *klass)
{
  GimpPlugInClass *plug_in_class = GIMP_PLUG_IN_CLASS (klass);

  plug_in_class->query_procedures = dds_query_procedures;
  plug_in_class->create_procedure = dds_create_procedure;
  plug_in_class->set_i18n         = STD_SET_I18N;
}

static void
dds_init (Dds *dds)
{
}

static GList *
dds_query_procedures (GimpPlugIn *plug_in)
{
  GList *list = NULL;

  list = g_list_append (list, g_strdup (LOAD_PROC));
  list = g_list_append (list, g_strdup (EXPORT_PROC));

  return list;
}

static GimpProcedure *
dds_create_procedure (GimpPlugIn  *plug_in,
                      const gchar *name)
{
  GimpProcedure *procedure = NULL;

  if (! strcmp (name, LOAD_PROC))
    {
      procedure = gimp_load_procedure_new (plug_in, name,
                                           GIMP_PDB_PROC_TYPE_PLUGIN,
                                           dds_load, NULL, NULL);

      gimp_procedure_set_menu_label (procedure, _("DDS image"));

      gimp_procedure_set_documentation (procedure,
                                        _("Loads files in DDS image format"),
                                        _("Loads files in DDS image format"),
                                        name);
      gimp_procedure_set_attribution (procedure,
                                      "Shawn Kirst",
                                      "Shawn Kirst",
                                      "2008");

      gimp_file_procedure_set_mime_types (GIMP_FILE_PROCEDURE (procedure),
                                          "image/dds");
      gimp_file_procedure_set_extensions (GIMP_FILE_PROCEDURE (procedure),
                                          "dds");
      gimp_file_procedure_set_magics (GIMP_FILE_PROCEDURE (procedure),
                                      "0,string,DDS");

      gimp_procedure_add_boolean_argument (procedure, "load-mipmaps",
                                           _("Load _mipmaps"),
                                           _("Load mipmaps if present"),
                                           TRUE,
                                           G_PARAM_READWRITE);

      gimp_procedure_add_boolean_argument (procedure, "flip-image",
                                           _("Flip image _vertically"),
                                           _("Flip the image vertically on import"),
                                           FALSE,
                                           G_PARAM_READWRITE);
    }
  else if (! strcmp (name, EXPORT_PROC))
    {
      GimpChoice *choice;

      procedure = gimp_export_procedure_new (plug_in, name,
                                             GIMP_PDB_PROC_TYPE_PLUGIN,
                                             FALSE, dds_export, NULL, NULL);

      gimp_procedure_set_image_types (procedure, "INDEXED, GRAY, RGB");

      gimp_procedure_set_menu_label (procedure, _("DDS image"));
      gimp_file_procedure_set_format_name (GIMP_FILE_PROCEDURE (procedure),
                                           _("DDS"));


      gimp_procedure_set_documentation (procedure,
                                        _("Exports files in DDS image format"),
                                        _("Exports files in DDS image format"),
                                        name);
      gimp_procedure_set_attribution (procedure,
                                      "Shawn Kirst",
                                      "Shawn Kirst",
                                      "2008");

      gimp_file_procedure_set_mime_types (GIMP_FILE_PROCEDURE (procedure),
                                          "image/dds");
      gimp_file_procedure_set_extensions (GIMP_FILE_PROCEDURE (procedure),
                                          "dds");

      gimp_export_procedure_set_capabilities (GIMP_EXPORT_PROCEDURE (procedure),
                                              GIMP_EXPORT_CAN_HANDLE_RGB     |
                                              GIMP_EXPORT_CAN_HANDLE_GRAY    |
                                              GIMP_EXPORT_CAN_HANDLE_INDEXED |
                                              GIMP_EXPORT_CAN_HANDLE_ALPHA   |
                                              GIMP_EXPORT_CAN_HANDLE_LAYERS,
                                              NULL, NULL, NULL);

      choice = gimp_choice_new_with_values ("none",   DDS_COMPRESS_NONE,   _("None"),                  NULL,
                                            "bc1",    DDS_COMPRESS_BC1,    _("BC1 / DXT1"),            NULL,
                                            "bc2",    DDS_COMPRESS_BC2,    _("BC2 / DXT3"),            NULL,
                                            "bc3",    DDS_COMPRESS_BC3,    _("BC3 / DXT5"),            NULL,
                                            "bc3n",   DDS_COMPRESS_BC3N,   _("BC3nm / DXT5nm"),        NULL,
                                            "bc4",    DDS_COMPRESS_BC4,    _("BC4 / ATI1 (3Dc+)"),     NULL,
                                            "bc5",    DDS_COMPRESS_BC5,    _("BC5 / ATI2 (3Dc)"),      NULL,
                                            "bc7",    DDS_COMPRESS_BC7,    "BC7",                      NULL,
                                            "rxgb",   DDS_COMPRESS_RXGB,   _("RXGB (DXT5)"),           NULL,
                                            "aexp",   DDS_COMPRESS_AEXP,   _("Alpha Exponent (DXT5)"), NULL,
                                            "ycocg",  DDS_COMPRESS_YCOCG,  _("YCoCg (DXT5)"),          NULL,
                                            "ycocgs", DDS_COMPRESS_YCOCGS, _("YCoCg scaled (DXT5)"),   NULL,
                                            NULL);
      gimp_choice_add_deprecated (choice, "bc3, ", DDS_COMPRESS_BC3, "bc3", NULL);

      gimp_procedure_add_choice_argument (procedure, "compression-format",
                                          _("Compressio_n"),
                                          _("Compression format"),
                                          choice,
                                          "none",
                                          G_PARAM_READWRITE);

      gimp_procedure_add_boolean_argument (procedure, "perceptual-metric",
                                           _("Use percept_ual error metric"),
                                           _("Use a perceptual error metric during compression"),
                                           FALSE,
                                           G_PARAM_READWRITE);

      choice = gimp_choice_new_with_values ("default", DDS_FORMAT_DEFAULT, _("Default"), NULL,
                                            "rgb8",    DDS_FORMAT_RGB8,    _("RGB8"),    NULL,
                                            "rgba8",   DDS_FORMAT_RGBA8,   _("RGBA8"),   NULL,
                                            "bgr8",    DDS_FORMAT_BGR8,    _("BGR8"),    NULL,
                                            "abgr8",   DDS_FORMAT_ABGR8,   _("ABGR8"),   NULL,
                                            "r5g6b5",  DDS_FORMAT_R5G6B5,  _("R5G6B5"),  NULL,
                                            "rgba4",   DDS_FORMAT_RGBA4,   _("RGBA4"),   NULL,
                                            "rgb5a1",  DDS_FORMAT_RGB5A1,  _("RGB5A1"),  NULL,
                                            "rgb10a2", DDS_FORMAT_RGB10A2, _("RGB10A2"), NULL,
                                            "r3g3b2",  DDS_FORMAT_R3G3B2,  _("R3G3B2"),  NULL,
                                            "a8",      DDS_FORMAT_A8,      _("A8"),      NULL,
                                            "l8",      DDS_FORMAT_L8,      _("L8"),      NULL,
                                            "l8a8",    DDS_FORMAT_L8A8,    _("L8A8"),    NULL,
                                            "aexp",    DDS_FORMAT_AEXP,    _("AEXP"),    NULL,
                                            "ycocg",   DDS_FORMAT_YCOCG,   _("YCOCG"),   NULL,
                                            NULL);
      gimp_choice_add_deprecated (choice, "abgr8, ", DDS_FORMAT_ABGR8, "abgr8", NULL);

      gimp_procedure_add_choice_argument (procedure, "format",
                                          _("_Format"),
                                          _("Pixel format"),
                                          choice,
                                          "default",
                                          G_PARAM_READWRITE);

      gimp_procedure_add_choice_argument (procedure, "save-type",
                                          _("Sav_e type"),
                                          _("How to export the image"),
                                          gimp_choice_new_with_values ("layer",  DDS_SAVE_SELECTED_LAYER, _("Selected layer"),     NULL,
                                                                       "canvas", DDS_SAVE_VISIBLE_LAYERS, _("All visible layers"), NULL,
                                                                       "cube",   DDS_SAVE_CUBEMAP,        _("As cube map"),        NULL,
                                                                       "volume", DDS_SAVE_VOLUMEMAP,      _("As volume map"),      NULL,
                                                                       "array",  DDS_SAVE_ARRAY,          _("As texture array"),   NULL,
                                                                       NULL),
                                          "layer",
                                          G_PARAM_READWRITE);

      gimp_procedure_add_boolean_argument (procedure, "flip-image",
                                           _("Flip image _vertically on export"),
                                           _("Flip the image vertically on export"),
                                           FALSE,
                                           G_PARAM_READWRITE);

      gimp_procedure_add_boolean_argument (procedure, "transparent-color",
                                           _("Set _transparent color"),
                                           _("Make an indexed color transparent"),
                                           FALSE,
                                           G_PARAM_READWRITE);

      gimp_procedure_add_int_argument (procedure, "transparent-index",
                                       _("Transparent inde_x"),
                                       _("Index of transparent color or -1 to disable "
                                         "(for indexed images only)."),
                                       0, 255, 0,
                                       G_PARAM_READWRITE);

      gimp_procedure_add_choice_argument (procedure, "mipmaps",
                                          _("_Mipmaps"),
                                          _("How to handle mipmaps"),
                                          gimp_choice_new_with_values ("none",     DDS_MIPMAP_NONE,     _("No mipmaps"),           NULL,
                                                                       "generate", DDS_MIPMAP_GENERATE, _("Generate mipmaps"),     NULL,
                                                                       "existing", DDS_MIPMAP_EXISTING, _("Use existing mipmaps"), NULL,
                                                                       NULL),
                                          "none",
                                          G_PARAM_READWRITE);

      gimp_procedure_add_choice_argument (procedure, "mipmap-filter",
                                          _("F_ilter"),
                                          _("Filtering to use when generating mipmaps"),
                                          gimp_choice_new_with_values ("default",   DDS_MIPMAP_FILTER_DEFAULT,   _("Default"),     NULL,
                                                                       "nearest",   DDS_MIPMAP_FILTER_NEAREST,   _("Nearest"),     NULL,
                                                                       "box",       DDS_MIPMAP_FILTER_BOX,       _("Box"),         NULL,
                                                                       "triangle",  DDS_MIPMAP_FILTER_TRIANGLE,  _("Triangle"),    NULL,
                                                                       "quadratic", DDS_MIPMAP_FILTER_QUADRATIC, _("Quadratic"),   NULL,
                                                                       "bspline",   DDS_MIPMAP_FILTER_BSPLINE,   _("B-Spline"),    NULL,
                                                                       "mitchell",  DDS_MIPMAP_FILTER_MITCHELL,  _("Mitchell"),    NULL,
                                                                       "catrom",    DDS_MIPMAP_FILTER_CATROM,    _("Catmull-Rom"), NULL,
                                                                       "lanczos",   DDS_MIPMAP_FILTER_LANCZOS,   _("Lanczos"),     NULL,
                                                                       "kaiser",    DDS_MIPMAP_FILTER_KAISER,    _("Kaiser"),      NULL,
                                                                       NULL),
                                          "default",
                                          G_PARAM_READWRITE);

      gimp_procedure_add_choice_argument (procedure, "mipmap-wrap",
                                          _("_Wrap mode"),
                                          _("Wrap mode to use when generating mipmaps"),
                                          gimp_choice_new_with_values ("default", DDS_MIPMAP_WRAP_DEFAULT, _("Default"), NULL,
                                                                       "mirror",  DDS_MIPMAP_WRAP_MIRROR,  _("Mirror"),  NULL,
                                                                       "repeat",  DDS_MIPMAP_WRAP_REPEAT,  _("Repeat"),  NULL,
                                                                       "clamp",   DDS_MIPMAP_WRAP_CLAMP,   _("Clamp"),   NULL,
                                                                       NULL),
                                          "default",
                                          G_PARAM_READWRITE);

      gimp_procedure_add_boolean_argument (procedure, "gamma-correct",
                                           _("Appl_y gamma correction"),
                                           _("Use gamma correct mipmap filtering"),
                                           FALSE,
                                           G_PARAM_READWRITE);

      gimp_procedure_add_boolean_argument (procedure, "srgb",
                                           _("Use sRG_B colorspace"),
                                           _("Use sRGB colorspace for gamma correction"),
                                           FALSE,
                                           G_PARAM_READWRITE);

      gimp_procedure_add_double_argument (procedure, "gamma",
                                          _("_Gamma"),
                                          _("Gamma value to use for gamma correction (e.g. 2.2)"),
                                          0.0, 10.0, 0.0,
                                          G_PARAM_READWRITE);

      gimp_procedure_add_boolean_argument (procedure, "preserve-alpha-coverage",
                                           _("Preserve al_pha test coverage"),
                                           _("Preserve alpha test coverage for alpha "
                                             "channel maps"),
                                           FALSE,
                                           G_PARAM_READWRITE);

      gimp_procedure_add_double_argument (procedure, "alpha-test-threshold",
                                          _("Alp_ha test threshold"),
                                          _("Alpha test threshold value for which alpha test "
                                            "coverage should be preserved"),
                                          0.0, 1.0, 0.5,
                                          G_PARAM_READWRITE);
    }

  return procedure;
}

static GimpValueArray *
dds_load (GimpProcedure         *procedure,
          GimpRunMode            run_mode,
          GFile                 *file,
          GimpMetadata          *metadata,
          GimpMetadataLoadFlags *flags,
          GimpProcedureConfig   *config,
          gpointer               run_data)
{
  GimpValueArray      *return_vals;
  GimpPDBStatusType    status;
  GimpImage           *image;
  GError              *error = NULL;

  gegl_init (NULL, NULL);

  status = read_dds (file, &image, run_mode == GIMP_RUN_INTERACTIVE,
                     procedure, config, &error);

  if (status != GIMP_PDB_SUCCESS)
    return gimp_procedure_new_return_values (procedure, status, error);

  return_vals = gimp_procedure_new_return_values (procedure,
                                                  GIMP_PDB_SUCCESS,
                                                  NULL);

  GIMP_VALUES_SET_IMAGE (return_vals, 1, image);

  return return_vals;
}

static GimpValueArray *
dds_export (GimpProcedure        *procedure,
            GimpRunMode           run_mode,
            GimpImage            *image,
            GFile                *file,
            GimpExportOptions    *options,
            GimpMetadata         *metadata,
            GimpProcedureConfig  *config,
            gpointer              run_data)
{
  GimpPDBStatusType  status = GIMP_PDB_SUCCESS;
  GimpExportReturn   export = GIMP_EXPORT_IGNORE;
  GimpLayer        **drawables;
  GError            *error  = NULL;
  gdouble            gamma;

  gegl_init (NULL, NULL);

  if (run_mode == GIMP_RUN_INTERACTIVE)
    gimp_ui_init ("dds");

  export    = gimp_export_options_get_image (options, &image);
  drawables = gimp_image_get_selected_layers (image);

  g_object_get (config,
                "gamma", &gamma,
                NULL);

  /* gimp_gamma () got removed and was always returning 2.2 anyway.
   * XXX Review this piece of code if we expect gamma value could be
   * parameterized.
   */
  if (gamma < 1e-04f)
    g_object_set (config,
                  "gamma", 2.2,
                  NULL);

  /* TODO: support multiple-layers selection, especially as DDS has
   * DDS_SAVE_SELECTED_LAYER option support.
   */
  status = write_dds (file, image, GIMP_DRAWABLE (drawables[0]),
                      run_mode == GIMP_RUN_INTERACTIVE,
                      procedure, config,
                      export == GIMP_EXPORT_EXPORT);

  if (export == GIMP_EXPORT_EXPORT)
    gimp_image_delete (image);

  g_free (drawables);
  return gimp_procedure_new_return_values (procedure, status, error);
}

/* --- end plug-ins/field-io/file-dds/dds.c --- */

/* --- begin plug-ins/field-io/file-dds/ddsread.c --- */
/*
 * DDS AmmoOS Image plugin
 *
 * Copyright (C) 2004-2012 Shawn Kirst <skirst@gmail.com>,
 * with parts (C) 2003 Arne Reuter <homepage@arnereuter.de> where specified.
 *
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public
 * License as published by the Free Software Foundation; either
 * version 2 of the License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; see the file COPYING.  If not, write to
 * the Free Software Foundation, 51 Franklin Street, Fifth Floor
 * Boston, MA 02110-1301, USA.
 */

/*
 ** !!! COPYRIGHT NOTICE !!!
 **
 ** The following is based on code (C) 2003 Arne Reuter <homepage@arnereuter.de>
 ** URL: http://www.dr-reuter.de/arne/dds.html
 **
 */

#include "config.h"

#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <gtk/gtk.h>
#include <glib/gstdio.h>

#include <libgimp/ammoos.h>
#include <libgimp/gimpui.h>

#include <libgimp/stdplugins-intl.h>

#include "dds.h"
#include "ddsread.h"
#include "dxt.h"
#include "endian_rw.h"
#include "formats.h"
#include "imath.h"
#include "misc.h"


/*
 * Struct containing all info needed to parse the file.
 * This can be thought of as a version-agnostic header,
 * holding all relevant data from the two headers
 * plus some AmmoOS Image-specific information.
 */
typedef struct
{
  fmt_read_info_t       read_info;
  gchar                 fourcc[4];
  gchar                 gimp_fourcc[4];
  guint                 flags;
  guint                 fmt_flags;
  guint                 bpp;
  guint                 gimp_bpp;
  DXGI_FORMAT           dxgi_format;
  D3DFORMAT             d3d9_format;
  DDS_COMPRESSION_TYPE  comp_format;
  guint                 width;
  guint                 height;
  gint                  tile_height;
  gsize                 linear_size;
  gsize                 pitch;
  guint                 mipmaps;
  guint                 volume_slices;
  guint                 array_items;
  guint                 cubemap_faces;
  guint                 gimp_version;
  guchar               *palette;
} dds_load_info_t;


static gboolean      read_header          (dds_header_t         *hdr,
                                           FILE                 *fp);
static gboolean      read_header_dx10     (dds_header_dx10_t    *hdr,
                                           FILE                 *fp);
static gboolean      validate_header      (dds_header_t         *hdr,
                                           GError              **error);
static gboolean      validate_dx10_header (dds_header_dx10_t    *dx10hdr,
                                           dds_load_info_t      *load_info,
                                           GError              **error);
static gboolean      load_layer           (FILE                 *fp,
                                           dds_load_info_t      *load_info,
                                           GimpImage            *image,
                                           guint                 level,
                                           gchar                *prefix,
                                           guint                *layer_index,
                                           guchar               *pixels,
                                           guchar               *buf,
                                           GError              **error);
static gboolean      load_mipmaps         (FILE                 *fp,
                                           dds_load_info_t      *load_info,
                                           GimpImage            *image,
                                           gchar                *prefix,
                                           guint                *layer_index,
                                           guchar               *pixels,
                                           guchar               *buf,
                                           gboolean              read_mipmaps,
                                           GError              **error);
static gboolean      load_face            (FILE                 *fp,
                                           dds_load_info_t      *load_info,
                                           GimpImage            *image,
                                           gchar                *prefix,
                                           guint                *layer_index,
                                           guchar               *pixels,
                                           guchar               *buf,
                                           gboolean              read_mipmaps,
                                           GError              **error);
static gboolean      load_dialog          (GimpProcedure        *procedure,
                                           GimpProcedureConfig  *config);


/* Read DDS file */
GimpPDBStatusType
read_dds (GFile                *file,
          GimpImage           **ret_image,
          gboolean              interactive,
          GimpProcedure        *procedure,
          GimpProcedureConfig  *config,
          GError              **error)
{
  GimpImage         *image       = NULL;
  guint              layer_index = 0;
  guchar            *buf, *pixels;
  FILE              *fp;
  gsize              file_size;
  dds_header_t       hdr;
  dds_header_dx10_t  dx10hdr;
  dds_load_info_t    load_info;
  GList             *layers;
  GimpImageBaseType  type;
  GimpPrecision      precision = GIMP_PRECISION_U8_NON_LINEAR;
  gboolean           read_mipmaps;
  gboolean           flip_import;
  gint               i;

  if (interactive)
    {
      gimp_ui_init ("dds");

      if (! load_dialog (procedure, config))
        return GIMP_PDB_CANCEL;
    }

  g_object_get (config,
                "load-mipmaps", &read_mipmaps,
                "flip-image",   &flip_import,
                NULL);

  fp = g_fopen (g_file_peek_path (file), "rb");

  if (! fp)
    {
      g_set_error (error, G_FILE_ERROR, g_file_error_from_errno (errno),
                   _("Could not open '%s' for reading: %s"),
                   gimp_file_get_utf8_name (file), g_strerror (errno));
      return GIMP_PDB_EXECUTION_ERROR;
    }

  /* Get total file size to compare against header info later */
  fseek (fp, 0L, SEEK_END);
  file_size = ftell (fp);
  fseek (fp, 0L, SEEK_SET);

  gimp_progress_init_printf (_("Loading: %s"), gimp_file_get_utf8_name (file));

  /* Read standard header */
  memset (&hdr, 0, sizeof (dds_header_t));
  read_header (&hdr, fp);

  /* Check that header is actually valid */
  if (! validate_header (&hdr, error))
    {
      fclose (fp);
      return GIMP_PDB_EXECUTION_ERROR;
    }

  /* Initialize load_info with data from header */
  memset (&load_info, 0, sizeof (dds_load_info_t));
  PUTL32 (load_info.fourcc, GETL32 (hdr.pixelfmt.fourcc));
  load_info.flags         = hdr.flags;
  load_info.fmt_flags     = hdr.pixelfmt.flags;
  load_info.width         = hdr.width;
  load_info.height        = hdr.height;
  load_info.gimp_version  = hdr.reserved.gimp_dds_special.version;
  PUTL32 (load_info.gimp_fourcc, hdr.reserved.gimp_dds_special.extra_fourcc);

  /* Get D3DFORMAT directly from FourCC if present there,
   * otherwise find it based on provided bpp, masks, and flags */
  if ((load_info.fmt_flags & DDPF_FOURCC) && (load_info.fourcc[1] == 0))
    load_info.d3d9_format = GETL32 (load_info.fourcc);
  else
    load_info.d3d9_format = get_d3d9format (hdr.pixelfmt.bpp,
                                            hdr.pixelfmt.rmask,
                                            hdr.pixelfmt.gmask,
                                            hdr.pixelfmt.bmask,
                                            hdr.pixelfmt.amask,
                                            hdr.pixelfmt.flags);

  /* Read DX10 header if present */
  memset (&dx10hdr, 0, sizeof (dds_header_dx10_t));
  if (GETL32 (load_info.fourcc) == FOURCC ('D','X','1','0'))
    {
      read_header_dx10 (&dx10hdr, fp);

      /* Check that DX10 header is actually valid */
      if (! validate_dx10_header (&dx10hdr, &load_info, error))
        {
          fclose (fp);
          return GIMP_PDB_EXECUTION_ERROR;
        }
      load_info.array_items = dx10hdr.arraySize;
    }

  /* If format search was successful, get info needed to parse the file */
  if (load_info.d3d9_format || load_info.dxgi_format)
    {
      gint d3d9_bpp = 0;
      gint dxgi_bpp = 0;

      load_info.read_info = get_format_read_info (load_info.d3d9_format,
                                                  load_info.dxgi_format);

      if (load_info.d3d9_format)
        d3d9_bpp = get_bpp_d3d9 (load_info.d3d9_format);
      else if (load_info.dxgi_format)
        dxgi_bpp = get_bpp_dxgi (load_info.dxgi_format);

      hdr.pixelfmt.bpp = MAX (MAX (hdr.pixelfmt.bpp, d3d9_bpp), dxgi_bpp);

      /* Unset the FourCC flag as D3D formats will be handled as uncompressed */
      if ((load_info.fmt_flags & DDPF_FOURCC) && load_info.d3d9_format)
        load_info.fmt_flags &= ~DDPF_FOURCC;
    }

  /* Exit if uncompressed format could not be determined by any method */
  if ((! (load_info.fmt_flags & DDPF_FOURCC)) &&
      (! (load_info.d3d9_format || load_info.dxgi_format)))
    {
      fclose (fp);
      g_set_error (error, G_FILE_ERROR, G_FILE_ERROR_FAILED,
                   _("Unsupported DDS pixel format:\n"
                     "bpp: %d, Rmask: %x, Gmask: %x, Bmask: %x, Amask: %x, flags: %u"),
                   hdr.pixelfmt.bpp,
                   hdr.pixelfmt.rmask, hdr.pixelfmt.gmask,
                   hdr.pixelfmt.bmask, hdr.pixelfmt.amask,
                   hdr.pixelfmt.flags);
      return GIMP_PDB_EXECUTION_ERROR;
    }

  /* If compressed, determine the format used */
  if (load_info.fmt_flags & DDPF_FOURCC)
    {
      if (GETL32 (load_info.fourcc) == FOURCC ('D','X','1','0'))
        {
          /* Compression type from DXGI format */
          switch (dx10hdr.dxgiFormat)
            {
            case DXGI_FORMAT_BC1_TYPELESS:
            case DXGI_FORMAT_BC1_UNORM:
            case DXGI_FORMAT_BC1_UNORM_SRGB:
              load_info.comp_format = DDS_COMPRESS_BC1;
              break;
            case DXGI_FORMAT_BC2_TYPELESS:
            case DXGI_FORMAT_BC2_UNORM:
            case DXGI_FORMAT_BC2_UNORM_SRGB:
              load_info.comp_format = DDS_COMPRESS_BC2;
              break;
            case DXGI_FORMAT_BC3_TYPELESS:
            case DXGI_FORMAT_BC3_UNORM:
            case DXGI_FORMAT_BC3_UNORM_SRGB:
              load_info.comp_format = DDS_COMPRESS_BC3;
              break;
            case DXGI_FORMAT_BC4_TYPELESS:
            case DXGI_FORMAT_BC4_UNORM:
            case DXGI_FORMAT_BC4_SNORM:
              load_info.comp_format = DDS_COMPRESS_BC4;
              break;
            case DXGI_FORMAT_BC5_TYPELESS:
            case DXGI_FORMAT_BC5_UNORM:
            case DXGI_FORMAT_BC5_SNORM:
              load_info.comp_format = DDS_COMPRESS_BC5;
              break;
            /* TODO: Implement BC6 format */
            case DXGI_FORMAT_BC7_TYPELESS:
            case DXGI_FORMAT_BC7_UNORM:
            case DXGI_FORMAT_BC7_UNORM_SRGB:
              load_info.comp_format = DDS_COMPRESS_BC7;
              break;

            default:
              load_info.comp_format = DDS_COMPRESS_MAX;
              break;
            }
        }
      else
        {
          /* Compression type from FourCC */
          switch (GETL32 (load_info.fourcc))
            {
            case FOURCC ('D','X','T','1'):
              load_info.comp_format = DDS_COMPRESS_BC1;
              break;
            case FOURCC ('D','X','T','2'):
            case FOURCC ('D','X','T','3'):
              load_info.comp_format = DDS_COMPRESS_BC2;
              break;
            case FOURCC ('D','X','T','4'):
            case FOURCC ('D','X','T','5'):
            case FOURCC ('R','X','G','B'):
              load_info.comp_format = DDS_COMPRESS_BC3;
              break;
            case FOURCC ('A','T','I','1'):
            case FOURCC ('B','C','4','U'):
            case FOURCC ('B','C','4','S'):
              load_info.comp_format = DDS_COMPRESS_BC4;
              break;
            case FOURCC ('A','T','I','2'):
            case FOURCC ('B','C','5','U'):
            case FOURCC ('B','C','5','S'):
              load_info.comp_format = DDS_COMPRESS_BC5;
              break;
            default:
              load_info.comp_format = DDS_COMPRESS_MAX;
              break;
            }
        }
    }

  /* Determine resource type (cubemap, volume, array) and number of mipmaps.
   * Filling in these variables conditionally here simplifies some checks later */
  if (load_info.dxgi_format)
    {
      if (dx10hdr.resourceDimension == D3D10_RESOURCE_DIMENSION_TEXTURE3D)
        load_info.volume_slices = hdr.depth;

      if ((dx10hdr.resourceDimension == D3D10_RESOURCE_DIMENSION_TEXTURE2D) &&
          (dx10hdr.miscFlag & D3D10_RESOURCE_MISC_TEXTURECUBE))
        load_info.cubemap_faces = DDSCAPS2_CUBEMAP_ALL_FACES;
    }
  else
    {
      /* This and the mipmap check below were originally AND, not OR,
       * but some images out there only have one of these two flags,
       * so for compatibility's sake we take the more lenient route */
      if ((hdr.caps.caps2 & DDSCAPS2_VOLUME) ||
          (load_info.flags & DDSD_DEPTH))
        load_info.volume_slices = hdr.depth;

      load_info.cubemap_faces = hdr.caps.caps2 & DDSCAPS2_CUBEMAP_ALL_FACES;
    }
  if ((hdr.caps.caps1 & DDSCAPS_MIPMAP) ||
      (load_info.flags & DDSD_MIPMAPCOUNT))
    load_info.mipmaps = hdr.num_mipmaps;

  /* Historically many DDS exporters haven't set pitch/linearsize and the corresponding flags,
   * or set them incorrectly, so it's more reliable to always compute these manually.
   * See: https://learn.microsoft.com/en-us/windows/win32/direct3ddds/dx-graphics-dds-pguide
   */
  if (load_info.fmt_flags & DDPF_FOURCC)
    {
      if (hdr.flags & DDSD_PITCH)
        {
          g_printerr ("Warning: DDSD_PITCH is incorrectly set for DDPF_FOURCC! (recovered)\n");
          load_info.flags &= ~DDSD_PITCH;
        }
      if (! (hdr.flags & DDSD_LINEARSIZE))
        {
          g_printerr ("Warning: DDSD_LINEARSIZE is incorrectly not set for DDPF_FOURCC! (recovered)\n");
          load_info.flags |= DDSD_LINEARSIZE;
        }

      load_info.pitch = MAX (1, (hdr.width + 3) >> 2);

      if (load_info.comp_format == DDS_COMPRESS_BC1 ||
          load_info.comp_format == DDS_COMPRESS_BC4)
        {
          load_info.pitch *= 8;
        }
      else
        {
          load_info.pitch *= 16;
        }

      if (! g_size_checked_mul (&load_info.linear_size,
                                MAX (1, (hdr.height + 3) >> 2),
                                load_info.pitch))
        {
          fclose (fp);
          g_set_error (error, GIMP_PLUG_IN_ERROR, 0,
                       _("Image size is too big to handle."));
          return GIMP_PDB_EXECUTION_ERROR;
        }

      if (load_info.linear_size != hdr.pitch_or_linsize)
        {
          g_printerr ("Unexpected linear size (%u) set to %u\n",
                      hdr.pitch_or_linsize, (guint32) load_info.linear_size);
        }
    }
  else
    {
      if (! (hdr.flags & DDSD_PITCH))
        {
          g_printerr ("Warning: DDSD_PITCH is incorrectly not set for an uncompressed texture! (recovered)\n");
          load_info.flags |= DDSD_PITCH;
        }
      if ((hdr.flags & DDSD_LINEARSIZE))
        {
          g_printerr ("Warning: DDSD_LINEARSIZE is incorrectly set for an uncompressed texture! (recovered)\n");
          load_info.flags &= ~DDSD_LINEARSIZE;
        }

      load_info.pitch = (hdr.width * hdr.pixelfmt.bpp + 7) >> 3;

      if (load_info.pitch != hdr.pitch_or_linsize)
        {
          g_printerr ("Unexpected pitch (%u) set to %u\n",
                      hdr.pitch_or_linsize, (guint32) load_info.pitch);
        }

      load_info.linear_size = load_info.pitch * hdr.height;
    }

  /* Determine bytes-per-pixel and AmmoOS Image type needed */
  if (load_info.fmt_flags & DDPF_FOURCC)
    {
      /* Compressed */
      switch (load_info.comp_format)
        {
        case DDS_COMPRESS_BC4:
          load_info.bpp = load_info.gimp_bpp = 1;  /* Gray */
          type = GIMP_GRAY;
          break;
        case DDS_COMPRESS_BC5:
          load_info.bpp = load_info.gimp_bpp = 3;  /* RGB */
          type = GIMP_RGB;
          break;
        default:
          load_info.bpp = load_info.gimp_bpp = 4;  /* RGBA */
          type = GIMP_RGB;
          break;
        }

      precision = GIMP_PRECISION_U8_NON_LINEAR;
    }
  else
    {
      /* Uncompressed */
      load_info.bpp = hdr.pixelfmt.bpp >> 3;
      type = load_info.read_info.gimp_type;

      /* Set up AmmoOS Image bytes-per-pixel */
      if (load_info.read_info.gimp_type == GIMP_INDEXED)
        {
          load_info.gimp_bpp = 1;

          if (load_info.read_info.use_alpha)
            load_info.gimp_bpp += 1;
        }
      else
        {
          if (load_info.read_info.gimp_type == GIMP_RGB)
            load_info.gimp_bpp = 3;
          else  /* load_info.read_info.gimp_type == GIMP_GRAY */
            load_info.gimp_bpp = 1;

          if (load_info.read_info.use_alpha)
            load_info.gimp_bpp += 1;

          if (load_info.read_info.output_bit_depth == 16)
            load_info.gimp_bpp *= 2;
          else if (load_info.read_info.output_bit_depth == 32)
            load_info.gimp_bpp *= 4;
        }

      /* Set up canvas precision */
      if (load_info.read_info.output_bit_depth == 8)
        {
          precision = GIMP_PRECISION_U8_NON_LINEAR;
        }
      else if (load_info.read_info.output_bit_depth == 16)
        {
          if (load_info.read_info.is_float)
            precision = GIMP_PRECISION_HALF_LINEAR;
          else
            precision = GIMP_PRECISION_U16_NON_LINEAR;
        }
      else if (load_info.read_info.output_bit_depth == 32)
        {
          if (load_info.read_info.is_float)
            precision = GIMP_PRECISION_FLOAT_LINEAR;
          else
            precision = GIMP_PRECISION_U32_NON_LINEAR;
        }
    }

  /* Verify header information is accurate to avoid allocating more memory than is actually needed */
  if (load_info.bpp < 1 ||
      (load_info.linear_size > (file_size - sizeof (hdr))))
    {
      fclose (fp);
      g_set_error (error, G_FILE_ERROR, g_file_error_from_errno (errno),
                   _("Invalid or corrupted DDS header."));
      return GIMP_PDB_EXECUTION_ERROR;
    }

  /* Generate AmmoOS Image image with set precision */
  image = gimp_image_new_with_precision (load_info.width,
                                         load_info.height,
                                         type, precision);

  if (! image)
    {
      g_set_error (error, G_FILE_ERROR, G_FILE_ERROR_NOMEM,
                   _("Could not allocate a new image."));
      fclose (fp);
      return GIMP_PDB_EXECUTION_ERROR;
    }

  /* Read palette for indexed DDS */
  if (load_info.fmt_flags & DDPF_PALETTEINDEXED8)
    {
      const Babl  *format  = babl_format ("R'G'B' u8");
      GimpPalette *palette = gimp_image_get_palette (image);
      GeglColor   *color   = gegl_color_new (NULL);

      load_info.palette = g_malloc (256 * 4);
      if (fread (load_info.palette, 1, 1024, fp) != 1024)
        {
          g_set_error (error, G_FILE_ERROR, G_FILE_ERROR_FAILED,
                       _("Error reading palette."));
          fclose (fp);
          gimp_image_delete (image);
          return GIMP_PDB_EXECUTION_ERROR;
        }
      for (i = 0; i < 1024; i += 4)
        {
          gint entry_num;

          /* Looks like DDS indexed images have an alpha channel (or
           * what else is this fourth byte?) and we just ignore it since
           * our own palette colors are opaque?
           */
          gegl_color_set_pixel (color, format, &load_info.palette[i]);
          gimp_palette_add_entry (palette, NULL, color, &entry_num);
        }

      g_object_unref (color);
    }

  load_info.tile_height = gimp_tile_height ();

  pixels = g_new (guchar, load_info.tile_height * load_info.width * load_info.gimp_bpp);
  buf = g_malloc (load_info.linear_size);

  if (load_info.cubemap_faces)  /* Cubemap texture */
    {
      if ((load_info.cubemap_faces & DDSCAPS2_CUBEMAP_POSITIVEX) &&
          ! load_face (fp, &load_info, image, "(positive x)",
                       &layer_index, pixels, buf, read_mipmaps, error))
        {
          fclose (fp);
          gimp_image_delete (image);
          return GIMP_PDB_EXECUTION_ERROR;
        }

      if ((load_info.cubemap_faces & DDSCAPS2_CUBEMAP_NEGATIVEX) &&
          ! load_face (fp, &load_info, image, "(negative x)",
                       &layer_index, pixels, buf, read_mipmaps, error))
        {
          fclose (fp);
          gimp_image_delete (image);
          return GIMP_PDB_EXECUTION_ERROR;
        }

      if ((load_info.cubemap_faces & DDSCAPS2_CUBEMAP_POSITIVEY) &&
          ! load_face (fp, &load_info, image, "(positive y)",
                       &layer_index, pixels, buf, read_mipmaps, error))
        {
          fclose (fp);
          gimp_image_delete (image);
          return GIMP_PDB_EXECUTION_ERROR;
        }

      if ((load_info.cubemap_faces & DDSCAPS2_CUBEMAP_NEGATIVEY) &&
          ! load_face (fp, &load_info, image, "(negative y)",
                       &layer_index, pixels, buf, read_mipmaps, error))
        {
          fclose (fp);
          gimp_image_delete (image);
          return GIMP_PDB_EXECUTION_ERROR;
        }

      if ((load_info.cubemap_faces & DDSCAPS2_CUBEMAP_POSITIVEZ) &&
          ! load_face (fp, &load_info, image, "(positive z)",
                       &layer_index, pixels, buf, read_mipmaps, error))
        {
          fclose (fp);
          gimp_image_delete (image);
          return GIMP_PDB_EXECUTION_ERROR;
        }

      if ((load_info.cubemap_faces & DDSCAPS2_CUBEMAP_NEGATIVEZ) &&
          ! load_face (fp, &load_info, image, "(negative z)",
                       &layer_index, pixels, buf, read_mipmaps, error))
        {
          fclose (fp);
          gimp_image_delete (image);
          return GIMP_PDB_EXECUTION_ERROR;
        }
    }
  else if (load_info.volume_slices > 0)  /* Volume texture */
    {
      guint  i, level;
      gchar *plane;

      for (i = 0; i < load_info.volume_slices; ++i)
        {
          plane = g_strdup_printf ("(z = %d)", i);

          if (! load_layer (fp, &load_info, image, 0, plane,
                            &layer_index, pixels, buf, error))
            {
              g_free (plane);
              fclose (fp);
              gimp_image_delete (image);
              return GIMP_PDB_EXECUTION_ERROR;
            }

          g_free (plane);
        }

      if (read_mipmaps)
        {
          for (level = 1; level < load_info.mipmaps; ++level)
            {
              int n = load_info.volume_slices >> level;

              if (n < 1)
                n = 1;

              for (i = 0; i < n; ++i)
                {
                  plane = g_strdup_printf ("(z = %d)", i);

                  if (! load_layer (fp, &load_info, image, level, plane,
                                    &layer_index, pixels, buf, error))
                    {
                      g_free (plane);
                      fclose (fp);
                      gimp_image_delete (image);
                      return GIMP_PDB_EXECUTION_ERROR;
                    }

                  g_free (plane);
                }
            }
        }
    }
  else if (load_info.array_items > 1)  /* Texture Array */
    {
      guint  i;
      gchar *elem;

      for (i = 0; i < load_info.array_items; ++i)
        {
          elem = g_strdup_printf ("(array element %d)", i);

          if (! load_layer (fp, &load_info, image, 0, elem, &layer_index,
                            pixels, buf, error))
            {
              fclose (fp);
              gimp_image_delete (image);
              return GIMP_PDB_EXECUTION_ERROR;
            }

          if (! load_mipmaps (fp, &load_info, image, elem, &layer_index,
                              pixels, buf, read_mipmaps, error))
            {
              fclose (fp);
              gimp_image_delete (image);
              return GIMP_PDB_EXECUTION_ERROR;
            }

          g_free (elem);
        }
    }
  else  /* Standard 2D texture */
    {
      if (! load_layer (fp, &load_info, image, 0, "", &layer_index,
                        pixels, buf, error))
        {
          fclose (fp);
          gimp_image_delete (image);
          return GIMP_PDB_EXECUTION_ERROR;
        }

      if (! load_mipmaps (fp, &load_info, image, "", &layer_index,
                          pixels, buf, read_mipmaps, error))
        {
          fclose (fp);
          gimp_image_delete (image);
          return GIMP_PDB_EXECUTION_ERROR;
        }
    }

  gimp_progress_update (1.0);

  if (load_info.fmt_flags & DDPF_PALETTEINDEXED8)
    g_free (load_info.palette);

  g_free (buf);
  g_free (pixels);
  fclose (fp);

  layers = gimp_image_list_layers (image);

  if (! layers)
    {
      /* XXX This error should never happen, and probably it should be a
       * CRITICAL/g_return_if_fail(). Yet let's just set it to the
       * GError until we better handle the debug dialog for plug-ins. A
       * pop-up with this message will be easier to track. No need to
       * localize it though.
       */
      g_set_error (error, G_FILE_ERROR, G_FILE_ERROR_FAILED,
                   "Oops! NULL image read! Please report this!");
      return GIMP_PDB_EXECUTION_ERROR;
    }

  gimp_image_take_selected_layers (image, layers);

  if (flip_import)
    gimp_image_flip (image, GIMP_ORIENTATION_VERTICAL);

  /* Store original format to use as a default for export */
  if (load_info.comp_format ||
      load_info.d3d9_format ||
      load_info.dxgi_format ||
      load_info.mipmaps)
    {
      GimpParasite *parasite = NULL;
      gchar        *import_settings;

      /* Save parasite version, compression format, pixel format,
       * DX10 format, flags, and number of mipmaps in the parasite */
      import_settings = g_strdup_printf ("1 %d %d %d %d %d",
                                         load_info.comp_format,
                                         load_info.d3d9_format,
                                         load_info.dxgi_format,
                                         load_info.flags,
                                         load_info.mipmaps);

      parasite = gimp_parasite_new ("dds-import-settings",
                                    GIMP_PARASITE_PERSISTENT,
                                    strlen (import_settings) + 1,
                                    (gpointer) import_settings);
      g_free (import_settings);

      gimp_image_attach_parasite (image, parasite);
      gimp_parasite_free (parasite);
    }

  *ret_image = image;

  return GIMP_PDB_SUCCESS;
}

/*
 * Read data from standard header
 */
static gboolean
read_header (dds_header_t *hdr,
             FILE         *fp)
{
  guchar buf[DDS_HEADERSIZE];

  if (fread (buf, 1, DDS_HEADERSIZE, fp) != DDS_HEADERSIZE)
    return FALSE;

  hdr->magic              = GETL32 (buf);

  hdr->size               = GETL32 (buf + 4);
  hdr->flags              = GETL32 (buf + 8);
  hdr->height             = GETL32 (buf + 12);
  hdr->width              = GETL32 (buf + 16);
  hdr->pitch_or_linsize   = GETL32 (buf + 20);
  hdr->depth              = GETL32 (buf + 24);
  hdr->num_mipmaps        = GETL32 (buf + 28);

  hdr->pixelfmt.size      = GETL32 (buf + 76);
  hdr->pixelfmt.flags     = GETL32 (buf + 80);
  hdr->pixelfmt.fourcc[0] = buf[84];
  hdr->pixelfmt.fourcc[1] = buf[85];
  hdr->pixelfmt.fourcc[2] = buf[86];
  hdr->pixelfmt.fourcc[3] = buf[87];
  hdr->pixelfmt.bpp       = GETL32 (buf + 88);
  hdr->pixelfmt.rmask     = GETL32 (buf + 92);
  hdr->pixelfmt.gmask     = GETL32 (buf + 96);
  hdr->pixelfmt.bmask     = GETL32 (buf + 100);
  hdr->pixelfmt.amask     = GETL32 (buf + 104);

  hdr->caps.caps1         = GETL32 (buf + 108);
  hdr->caps.caps2         = GETL32 (buf + 112);

  /* AmmoOS Image-DDS special info */
  if (GETL32 (buf + 32) == FOURCC ('G','I','M','P') &&
      GETL32 (buf + 36) == FOURCC ('-','D','D','S'))
    {
      hdr->reserved.gimp_dds_special.magic1       = GETL32 (buf + 32);
      hdr->reserved.gimp_dds_special.magic2       = GETL32 (buf + 36);
      hdr->reserved.gimp_dds_special.version      = GETL32 (buf + 40);
      hdr->reserved.gimp_dds_special.extra_fourcc = GETL32 (buf + 44);
    }

  return TRUE;
}

/*
 * Read data from DX10 header
 */
static gboolean
read_header_dx10 (dds_header_dx10_t *dx10hdr,
                  FILE              *fp)
{
  gchar buf[DDS_HEADERSIZE_DX10];

  if (fread (buf, 1, DDS_HEADERSIZE_DX10, fp) != DDS_HEADERSIZE_DX10)
    return FALSE;

  dx10hdr->dxgiFormat        = GETL32 (buf);
  dx10hdr->resourceDimension = GETL32 (buf + 4);
  dx10hdr->miscFlag          = GETL32 (buf + 8);
  dx10hdr->arraySize         = GETL32 (buf + 12);
  dx10hdr->reserved          = GETL32 (buf + 16);

  return TRUE;
}

/*
 * Check data from standard header for validity
 * Invalid header data is corrected where possible
 */
static gboolean
validate_header (dds_header_t  *hdr,
                 GError       **error)
{
  guint fourcc;

  /* Check  ~ m a g i c ~ */
  if (hdr->magic != FOURCC ('D','D','S',' '))
    {
      g_set_error (error, G_FILE_ERROR, G_FILE_ERROR_INVAL,
                   _("Invalid DDS format magic number."));
      return FALSE;
    }

  /* Check pixel format flags
   * If none are set, try to recover based on what information is available */
  fourcc = GETL32 (hdr->pixelfmt.fourcc);
  if (! (hdr->pixelfmt.flags & DDPF_RGB)           &&
      ! (hdr->pixelfmt.flags & DDPF_ALPHA)         &&
      ! (hdr->pixelfmt.flags & DDPF_BUMPDUDV)      &&
      ! (hdr->pixelfmt.flags & DDPF_BUMPLUMINANCE) &&
      ! (hdr->pixelfmt.flags & DDPF_ZBUFFER)       &&
      ! (hdr->pixelfmt.flags & DDPF_FOURCC)        &&
      ! (hdr->pixelfmt.flags & DDPF_LUMINANCE)     &&
      ! (hdr->pixelfmt.flags & DDPF_PALETTEINDEXED8))
    {
      g_message (_("File lacks expected pixel format flags! "
                   "Image may not be decoded correctly."));
      switch (fourcc)
        {
        case FOURCC ('D','X','T','1'):
        case FOURCC ('D','X','T','2'):
        case FOURCC ('D','X','T','3'):
        case FOURCC ('D','X','T','4'):
        case FOURCC ('D','X','T','5'):
        case FOURCC ('R','X','G','B'):
        case FOURCC ('A','T','I','1'):
        case FOURCC ('B','C','4','U'):
        case FOURCC ('B','C','4','S'):
        case FOURCC ('A','T','I','2'):
        case FOURCC ('B','C','5','U'):
        case FOURCC ('B','C','5','S'):
          hdr->pixelfmt.flags |= DDPF_FOURCC;
          break;
        default:
          switch (hdr->pixelfmt.bpp)
            {
            case 8:
              if (hdr->pixelfmt.flags & DDPF_ALPHAPIXELS)
                hdr->pixelfmt.flags |= DDPF_ALPHA;
              else
                hdr->pixelfmt.flags |= DDPF_LUMINANCE;
              break;
            case 16:
            case 24:
            case 32:
            case 64:
              hdr->pixelfmt.flags |= DDPF_RGB;
              break;
            default:
              g_set_error (error, G_FILE_ERROR, G_FILE_ERROR_FAILED,
                           _("Invalid pixel format."));
              return FALSE;
            }
          break;
        }
    }

  /* Check all supported FourCC codes */
  if ((hdr->pixelfmt.flags & DDPF_FOURCC) &&
      fourcc != FOURCC ('D','X','T','1')  &&
      fourcc != FOURCC ('D','X','T','2')  &&
      fourcc != FOURCC ('D','X','T','3')  &&
      fourcc != FOURCC ('D','X','T','4')  &&
      fourcc != FOURCC ('D','X','T','5')  &&
      fourcc != FOURCC ('R','X','G','B')  &&
      fourcc != FOURCC ('A','T','I','1')  &&
      fourcc != FOURCC ('B','C','4','U')  &&
      fourcc != FOURCC ('B','C','4','S')  &&
      fourcc != FOURCC ('A','T','I','2')  &&
      fourcc != FOURCC ('B','C','5','U')  &&
      fourcc != FOURCC ('B','C','5','S')  &&
      fourcc != FOURCC ('D','X','1','0')  &&
      hdr->pixelfmt.fourcc[1] != 0)
    {
      g_set_error (error, G_FILE_ERROR, G_FILE_ERROR_FAILED,
                   _("Unsupported format (FourCC: %c%c%c%c, hex: %08x)"),
                   hdr->pixelfmt.fourcc[0],
                   hdr->pixelfmt.fourcc[1] != 0 ? hdr->pixelfmt.fourcc[1] : ' ',
                   hdr->pixelfmt.fourcc[2] != 0 ? hdr->pixelfmt.fourcc[2] : ' ',
                   hdr->pixelfmt.fourcc[3] != 0 ? hdr->pixelfmt.fourcc[3] : ' ',
                   GETL32 (hdr->pixelfmt.fourcc));
      return FALSE;
    }

  /* Check bits-per-pixel */
  if (hdr->pixelfmt.flags & DDPF_RGB)
    {
      if ((hdr->pixelfmt.bpp !=  8) &&
          (hdr->pixelfmt.bpp != 16) &&
          (hdr->pixelfmt.bpp != 24) &&
          (hdr->pixelfmt.bpp != 32) &&
          (hdr->pixelfmt.bpp != 48) &&
          (hdr->pixelfmt.bpp != 64) &&
          (hdr->pixelfmt.bpp != 96) &&
          (hdr->pixelfmt.bpp != 128))
        {
          g_set_error (error, G_FILE_ERROR, G_FILE_ERROR_FAILED,
                       _("Invalid bpp value for RGB data: %d"),
                       hdr->pixelfmt.bpp);
          return FALSE;
        }
    }
  else if (hdr->pixelfmt.flags & DDPF_LUMINANCE)
    {
      if ((hdr->pixelfmt.bpp !=  8) &&
          (hdr->pixelfmt.bpp != 16))
        {
          g_set_error (error, G_FILE_ERROR, G_FILE_ERROR_FAILED,
                       _("Invalid bpp value for luminance data: %d"),
                       hdr->pixelfmt.bpp);
          return FALSE;
        }
    }

  return TRUE;
}

/*
 * Check data from DX10 header for validity
 */
static gboolean
validate_dx10_header (dds_header_dx10_t  *dx10hdr,
                      dds_load_info_t    *load_info,
                      GError            **error)
{
  if ((dx10hdr->resourceDimension != D3D10_RESOURCE_DIMENSION_TEXTURE1D) &&
      (dx10hdr->resourceDimension != D3D10_RESOURCE_DIMENSION_TEXTURE2D) &&
      (dx10hdr->resourceDimension != D3D10_RESOURCE_DIMENSION_TEXTURE3D))
    {
      g_set_error (error, G_FILE_ERROR, G_FILE_ERROR_FAILED,
                   _("Invalid DX10 header"));
      return FALSE;
    }

  switch (dx10hdr->dxgiFormat)
    {
    case DXGI_FORMAT_BC1_TYPELESS:
    case DXGI_FORMAT_BC1_UNORM:
    case DXGI_FORMAT_BC1_UNORM_SRGB:
    case DXGI_FORMAT_BC2_TYPELESS:
    case DXGI_FORMAT_BC2_UNORM:
    case DXGI_FORMAT_BC2_UNORM_SRGB:
    case DXGI_FORMAT_BC3_TYPELESS:
    case DXGI_FORMAT_BC3_UNORM:
    case DXGI_FORMAT_BC3_UNORM_SRGB:
    case DXGI_FORMAT_BC4_TYPELESS:
    case DXGI_FORMAT_BC4_UNORM:
    case DXGI_FORMAT_BC4_SNORM:
    case DXGI_FORMAT_BC5_TYPELESS:
    case DXGI_FORMAT_BC5_UNORM:
    case DXGI_FORMAT_BC5_SNORM:
    /* TODO: Implement BC6 format */
    case DXGI_FORMAT_BC7_TYPELESS:
    case DXGI_FORMAT_BC7_UNORM:
    case DXGI_FORMAT_BC7_UNORM_SRGB:

      /* Return early for supported compressed formats */
      load_info->dxgi_format = dx10hdr->dxgiFormat & 0xFF;
      return TRUE;
    default:
      /* Unset FourCC flag for uncompressed formats */
      load_info->fmt_flags &= ~DDPF_FOURCC;
      break;
    }

  if (! dxgiformat_supported (dx10hdr->dxgiFormat & 0xFF))
    {
      g_set_error (error, G_FILE_ERROR, G_FILE_ERROR_FAILED,
                   _("Unsupported DXGI Format: %u"),
                   dx10hdr->dxgiFormat & 0xFF);
      return FALSE;
    }

  load_info->dxgi_format = dx10hdr->dxgiFormat & 0xFF;

  return TRUE;
}

static const Babl *
premultiplied_variant (const Babl* format)
{
  if (format == babl_format ("R'G'B'A u8"))
    return babl_format ("R'aG'aB'aA u8");
  else
    g_printerr ("Add format %s to premultiplied_variant () %s: %d\n",
                babl_get_name (format), __FILE__, __LINE__);
  return format;
}

static gboolean
load_layer (FILE             *fp,
            dds_load_info_t  *load_info,
            GimpImage        *image,
            guint             level,
            gchar            *prefix,
            guint            *layer_index,
            guchar           *pixels,
            guchar           *buf,
            GError          **error)
{
  GeglBuffer    *buffer;
  const Babl    *bablfmt  = NULL;
  gchar         *babl_str = "";
  GimpImageType  type     = GIMP_RGBA_IMAGE;
  guint          width    = load_info->width  >> level;
  guint          height   = load_info->height >> level;
  guint          size     = width * height * load_info->bpp;
  gchar         *layer_name;
  GimpLayer     *layer;
  guint          layerw;
  gsize          file_size;
  gsize          current_position;
  gint           x, y, n;

  current_position = ftell (fp);
  fseek (fp, 0L, SEEK_END);
  file_size = ftell (fp);
  fseek (fp, current_position, SEEK_SET);

  if (width  < 1) width  = 1;
  if (height < 1) height = 1;

  /* Setup image type and Babl format */
  if (load_info->fmt_flags & DDPF_FOURCC)  /* Compressed */
    {
      /* Set Babl format */
      switch (load_info->comp_format)
        {
        case DDS_COMPRESS_BC4:
          type = GIMP_GRAY_IMAGE;
          babl_str = "Y'";
          break;
        case DDS_COMPRESS_BC5:
          type = GIMP_RGB_IMAGE;
          babl_str = "R'G'B'";
          break;
        default:
          type = GIMP_RGBA_IMAGE;
          babl_str = "R'G'B'A";
          break;
        }

      /* Set Babl precision */
      if ((GETL32 (load_info->fourcc) == FOURCC ('D','X','1','0')) &&
          (load_info->dxgi_format >= DXGI_FORMAT_BC6H_TYPELESS)    &&
          (load_info->dxgi_format <= DXGI_FORMAT_BC6H_SF16))
        {
          babl_str = g_strdup_printf ("%s %s", babl_str, "half");
        }
      else
        {
          babl_str = g_strdup_printf ("%s %s", babl_str, "u8");
        }
    }
  else  /* Uncompressed */
    {
      /* Set Babl format */
      if (load_info->read_info.gimp_type == GIMP_INDEXED)
        {
          if (load_info->read_info.use_alpha)
            type = GIMP_INDEXEDA_IMAGE;
          else
            type = GIMP_INDEXED_IMAGE;
        }
      else if (load_info->read_info.gimp_type == GIMP_RGB)
        {
          if (load_info->read_info.use_alpha)
            {
              type = GIMP_RGBA_IMAGE;
              babl_str = "R'G'B'A";
            }
          else
            {
              type = GIMP_RGB_IMAGE;
              babl_str = "R'G'B'";
            }
        }
      else  /* load_info->read_info.gimp_type == GIMP_GRAY */
        {
          if (load_info->read_info.use_alpha)
            {
              type = GIMP_GRAYA_IMAGE;
              babl_str = "Y'A";
            }
          else
            {
              type = GIMP_GRAY_IMAGE;
              babl_str = "Y'";
            }
        }

      /* Set Babl precision */
      if (load_info->read_info.is_float)
        {
          /* Floating-point */
          if (load_info->read_info.output_bit_depth == 16)
            babl_str = g_strdup_printf ("%s %s", babl_str, "half");
          else  /* load_info->read_info.output_bit_depth == 32 */
            babl_str = g_strdup_printf ("%s %s", babl_str, "float");
        }
      else
        {
          /* Integer */
          if (load_info->read_info.output_bit_depth == 32)
            babl_str = g_strdup_printf ("%s %s", babl_str, "u32");
          else if (load_info->read_info.output_bit_depth == 16)
            babl_str = g_strdup_printf ("%s %s", babl_str, "u16");
          else  /* load_info->read_info.output_bit_depth == 8 */
            babl_str = g_strdup_printf ("%s %s", babl_str, "u8");
        }
    }

  if (! (load_info->read_info.gimp_type == GIMP_INDEXED))
    bablfmt = babl_format (babl_str);

  g_free (babl_str);

  layer_name = (level) ? g_strdup_printf ("mipmap %d %s", level, prefix) :
                         g_strdup_printf ("main surface %s", prefix);

  layer = gimp_layer_new (image, layer_name, width, height, type, 100,
                          gimp_image_get_default_new_layer_mode (image));
  g_free (layer_name);

  gimp_image_insert_layer (image, layer, NULL, *layer_index);

  if (type == GIMP_INDEXED_IMAGE || type == GIMP_INDEXEDA_IMAGE)
    bablfmt = gimp_drawable_get_format (GIMP_DRAWABLE (layer));

  if ((*layer_index)++)
    gimp_item_set_visible (GIMP_ITEM (layer), FALSE);

  buffer = gimp_drawable_get_buffer (GIMP_DRAWABLE (layer));

  layerw = gegl_buffer_get_width (buffer);

  if (load_info->fmt_flags & DDPF_FOURCC)
    {
      size = ((width + 3) >> 2) * ((height + 3) >> 2);

      /* Let Babl handle premultiplied format conversion */
      if ((GETL32 (load_info->fourcc) == FOURCC ('D','X','T','2')) ||
          (GETL32 (load_info->fourcc) == FOURCC ('D','X','T','4')))
        bablfmt = premultiplied_variant (bablfmt);

      if ((load_info->comp_format == DDS_COMPRESS_BC1) ||
          (load_info->comp_format == DDS_COMPRESS_BC4))
        size *= 8;
      else
        size *= 16;
    }

  if (size > (file_size - current_position) ||
      size > load_info->linear_size)
    {
      g_set_error (error, G_FILE_ERROR, G_FILE_ERROR_FAILED,
                   _("Requested data exceeds size of file.\n"));
      return FALSE;
    }

  if ((load_info->flags & DDSD_LINEARSIZE) &&
      ! fread (buf, size, 1, fp))
    {
      g_set_error (error, G_FILE_ERROR, G_FILE_ERROR_FAILED,
                   _("Unexpected EOF.\n"));
      return FALSE;
    }

  if (! (load_info->fmt_flags & DDPF_FOURCC))  /* Read uncompressed pixel data */
    {
      guint   rowstride   = width * load_info->bpp;
      guint32 sign_add[4] = { 0, 0, 0, 0 };
      guint   idx_r = 0, idx_b = 2;

      /* Prior plug-in versions (3.9.91 and earlier) wrote the R and G channels reversed for RGB10A2. */
      if ((load_info->gimp_version > 0)       &&
          (load_info->gimp_version <= 199003) &&
          (load_info->d3d9_format == D3DFMT_A2R10G10B10))
        {
          g_printerr ("Switching incorrect red and green channels in RGB10A2 DDS "
                      "written by an older version of AmmoOS Image's DDS plug-in.\n");
          idx_r = 2;
          idx_b = 0;
        }

      /* Set up offset to apply to signed integer formats
       * Per-channel to accommodate for mixed formats  */
      if (load_info->read_info.is_signed &&
          (! load_info->read_info.is_float))
        {
          if (load_info->read_info.output_bit_depth == 8)
            {
              sign_add[0] = 128;
              sign_add[1] = 128;
              if (! (load_info->d3d9_format == D3DFMT_L6V5U5 ||
                     load_info->d3d9_format == D3DFMT_X8L8V8U8))
                sign_add[2] = 128;
              sign_add[3] = 128;
            }
          else if (load_info->read_info.output_bit_depth == 16)
            {
              sign_add[0] = 32768;
              sign_add[1] = 32768;
              sign_add[2] = 32768;
              if (! (load_info->d3d9_format == D3DFMT_A2W10V10U10 ||
                     load_info->dxgi_format == DXGI_FORMAT_R10G10B10_SNORM_A2_UNORM))
                sign_add[3] = 32768;
            }
          else  /* load_info->read_info.output_bit_depth == 32 */
            {
              sign_add[0] = 2147483648;
              sign_add[1] = 2147483648;
              sign_add[2] = 2147483648;
              sign_add[3] = 2147483648;
            }
        }

      if ((load_info->flags & DDSD_PITCH) && (rowstride > load_info->pitch))
        {
          g_set_error (error, G_FILE_ERROR, G_FILE_ERROR_FAILED,
                       _("Requested data exceeds size of file.\n"));
          return FALSE;
        }

      for (y = 0, n = 0; y < height; ++y, ++n)
        {
          if (n >= load_info->tile_height)
            {
              gegl_buffer_set (buffer, GEGL_RECTANGLE (0, y - n, layerw, n), 0,
                               bablfmt, pixels, GEGL_AUTO_ROWSTRIDE);
              n = 0;
              gimp_progress_update ((gdouble) y / (gdouble) load_info->height);
            }

          if (load_info->flags & DDSD_PITCH)
            {
              current_position = ftell (fp);
              if (rowstride > (file_size - current_position))
                {
                  g_set_error (error, G_FILE_ERROR, G_FILE_ERROR_FAILED,
                               _("Requested data exceeds size of file.\n"));
                  return FALSE;
                }
              if (! fread (buf, rowstride, 1, fp))
                {
                  g_set_error (error, G_FILE_ERROR, G_FILE_ERROR_FAILED,
                               _("Unexpected EOF.\n"));
                  return FALSE;
                }
            }

          for (x = 0; x < layerw; ++x)
            {
              guint   pos       = (n * layerw + x) * load_info->gimp_bpp;
              guint   buf_reads = 0;
              guchar  read_buf;
              guint32 ch_registers[4];

              memset (ch_registers, 0, sizeof (ch_registers));

              /* Format-agnostic bit-reader, driven by the 'format_read_info' table.
               * Reads one bit at a time from source bytes into per-channel registers.
               * While somewhat simplistic, reading bit-by-bit allows us to handle channels
               * that cross byte boundaries trivially, and without the need for look-ahead.
               */
              read_buf = *buf;
              for (gint reg = 0; reg < 4; reg++)
                {
                  const guchar  ch        = load_info->read_info.channel_order[reg];
                  const guchar  ch_bits   = load_info->read_info.channel_bits[reg];
                  const guint32 write_bit = 1 << (ch_bits - 1);

                  if (! ch_bits) continue;

                  /* Note: bits are written to the registers in the opposite order they're read in */
                  for (gint bit = 0; bit < ch_bits; bit++)
                    {
                      ch_registers[ch] >>= 1;
                      ch_registers[ch] |= read_buf & 1 ? write_bit : 0;
                      read_buf >>= 1;

                      buf_reads++;
                      if (buf_reads == 8)
                        {
                          /* Roll-over to next byte */
                          buf++;
                          read_buf = *buf;
                          buf_reads = 0;
                        }
                    }

                  /* Most DXGI small-float formats have 5 exponent bits, so can be interpreted as 16-bit floats with a simple shift.
                   * Integers meanwhile must be properly requantized to the output range */
                  if (load_info->read_info.is_float)
                    {
                      guint shift = load_info->read_info.output_bit_depth - ch_bits;

                      if (load_info->dxgi_format == DXGI_FORMAT_R9G9B9E5_SHAREDEXP     ||
                          load_info->dxgi_format == DXGI_FORMAT_R10G10B10_7E3_A2_FLOAT ||
                          load_info->dxgi_format == DXGI_FORMAT_R10G10B10_6E4_A2_FLOAT)
                        /* Skip shifting for float formats that require special handling */
                        shift = 0;
                      else if (! load_info->read_info.is_signed)
                        /* Don't shift into sign bit for unsigned floats, eg. R11G11B10 */
                        shift -= 1;

                      ch_registers[ch] = ch_registers[ch] << shift;
                    }
                  else
                    {
                      ch_registers[ch] = requantize_component (ch_registers[ch], ch_bits,
                                                               load_info->read_info.output_bit_depth);
                    }
                }

              /* Special cases for formats requiring extra decoding */
              if (load_info->dxgi_format == DXGI_FORMAT_R9G9B9E5_SHAREDEXP)
                float_from_9e5 (ch_registers);
              else if (load_info->dxgi_format == DXGI_FORMAT_R10G10B10_7E3_A2_FLOAT)
                float_from_7e3a2 (ch_registers);
              else if (load_info->dxgi_format == DXGI_FORMAT_R10G10B10_6E4_A2_FLOAT)
                float_from_6e4a2 (ch_registers);
              else if (load_info->d3d9_format == D3DFMT_CxV8U8)
                reconstruct_z (ch_registers);

              /* Clear alpha to all 1s instead of all 0s */
              if (! load_info->read_info.use_alpha)
                ch_registers[3] = G_MAXUINT32;

              /* Output converted values to canvas pixels */
              if (load_info->read_info.gimp_type == GIMP_RGB)
                {
                  if (load_info->read_info.output_bit_depth == 8)
                    {
                      guchar *pixel8 = (guchar *) &pixels[pos];
                      pixel8[0] = ch_registers[0] + sign_add[0];
                      pixel8[1] = ch_registers[1] + sign_add[1];
                      pixel8[2] = ch_registers[2] + sign_add[2];

                      if (load_info->read_info.use_alpha)
                        pixel8[3] = ch_registers[3] + sign_add[3];
                    }
                  else if (load_info->read_info.output_bit_depth == 16)
                    {
                      /* Variable indices for R and B to accommodate RGB10A2 fixup */
                      guint16 *pixel16 = (guint16 *) &pixels[pos];
                      pixel16[0] = ch_registers[idx_r] + sign_add[0];
                      pixel16[1] = ch_registers[1]     + sign_add[1];
                      pixel16[2] = ch_registers[idx_b] + sign_add[2];

                      if (load_info->read_info.use_alpha)
                        pixel16[3] = ch_registers[3] + sign_add[3];
                    }
                  else  /* load_info->read_info.output_bit_depth == 32 */
                    {
                      guint32 *pixel32 = (guint32 *) &pixels[pos];
                      pixel32[0] = (guint64) ch_registers[0] + sign_add[0];
                      pixel32[1] = (guint64) ch_registers[1] + sign_add[1];
                      pixel32[2] = (guint64) ch_registers[2] + sign_add[2];

                      if (load_info->read_info.use_alpha)
                        pixel32[3] = (guint64) ch_registers[3] + sign_add[3];
                    }
                }
              else if (load_info->read_info.gimp_type == GIMP_GRAY)
                {
                  if (load_info->read_info.output_bit_depth == 8)
                    {
                      guchar *pixel8 = (guchar *) &pixels[pos];
                      pixel8[0] = ch_registers[0] + sign_add[0];

                      if (load_info->read_info.use_alpha)
                        pixel8[1] = ch_registers[3] + sign_add[3];
                    }
                  else if (load_info->read_info.output_bit_depth == 16)
                    {
                      guint16 *pixel16 = (guint16 *) &pixels[pos];
                      pixel16[0] = ch_registers[0] + sign_add[0];

                      if (load_info->read_info.use_alpha)
                        pixel16[1] = ch_registers[3] + sign_add[3];
                    }
                  else  /* load_info->read_info.output_bit_depth == 32 */
                    {
                      guint32 *pixel32 = (guint32 *) &pixels[pos];
                      pixel32[0] = (guint64) ch_registers[0] + sign_add[0];

                      if (load_info->read_info.use_alpha)
                        pixel32[1] = (guint64) ch_registers[3] + sign_add[3];
                    }
                }
              else  /* load_info->read_info.gimp_type == GIMP_INDEXED */
                {
                  pixels[pos] = ch_registers[0] & 0xFF;
                  if (load_info->read_info.use_alpha)
                    pixels[pos + 1] = ch_registers[3] & 0xFF;
                }
            }
        }

      gegl_buffer_set (buffer, GEGL_RECTANGLE (0, y - n, layerw, n), 0,
                       bablfmt, pixels, GEGL_AUTO_ROWSTRIDE);
    }
  else  /* Read compressed pixel data */
    {
      guchar *dst;

      dst = g_malloc ((gsize) width * height * load_info->gimp_bpp);
      memset (dst, 0, (gsize) width * height * load_info->gimp_bpp);

      /* Initialize alpha to all 1s instead of all 0s */
      if (load_info->gimp_bpp == 4)
        {
          guchar *dst_line;

          dst_line = dst;
          for (y = 0; y < height; ++y)
            {
              for (x = 0; x < width; ++x)
                {
                  dst_line[(x * 4) + 3] = 255;
                }
              dst_line += width * 4;
            }
        }

      dxt_decompress (dst, buf, load_info->comp_format, size, width, height,
                      load_info->gimp_bpp, load_info->fmt_flags & DDPF_NORMAL);

      /* Prior plug-in versions (before 3.9.90) wrote the R and G channels reversed for BC5. */
      if ((load_info->gimp_version > 0)       &&
          (load_info->gimp_version <= 199002) &&
          (load_info->comp_format == DDS_COMPRESS_BC5))
        {
          g_printerr ("Switching incorrect red and green channels in BC5 DDS "
                      "written by an older version of AmmoOS Image's DDS plug-in.\n");

          for (y = 0; y < height; ++y)
            {
              for (x = 0; x < width; ++x)
                {
                  guchar tmpG;
                  guint  pix_width = width * load_info->gimp_bpp;
                  guint  x_width   = x * load_info->gimp_bpp;

                  tmpG = dst[y * pix_width + x_width];
                  dst[y * pix_width + x_width] = dst[y * pix_width + x_width + 1];
                  dst[y * pix_width + x_width + 1] = tmpG;
                }
            }
        }

      for (y = 0, n = 0; y < height; ++y, ++n)
        {
          if (n >= load_info->tile_height)
            {
              gegl_buffer_set (buffer, GEGL_RECTANGLE (0, y - n, layerw, n), 0,
                               bablfmt, pixels, GEGL_AUTO_ROWSTRIDE);
              n = 0;
              gimp_progress_update ((gdouble) y / (gdouble) load_info->height);
            }

          memcpy (pixels + n * layerw * load_info->gimp_bpp,
                  dst + y * layerw * load_info->gimp_bpp,
                  width * load_info->gimp_bpp);
        }

      gegl_buffer_set (buffer, GEGL_RECTANGLE (0, y - n, layerw, n), 0,
                       bablfmt, pixels, GEGL_AUTO_ROWSTRIDE);

      g_free (dst);
    }

  gegl_buffer_flush (buffer);

  g_object_unref (buffer);

  /* Decode files with AmmoOS Image-specific encodings */
  if (load_info->gimp_version > 0)
    {
      switch (GETL32 (load_info->gimp_fourcc))
        {
        case FOURCC ('A','E','X','P'):
          decode_alpha_exponent (GIMP_DRAWABLE (layer));
          break;
        case FOURCC ('Y','C','G','1'):
          decode_ycocg (GIMP_DRAWABLE (layer));
          break;
        case FOURCC ('Y','C','G','2'):
          decode_ycocg_scaled (GIMP_DRAWABLE (layer));
          break;
        default:
          break;
        }
    }

  return TRUE;
}

static gboolean
load_mipmaps (FILE             *fp,
              dds_load_info_t  *load_info,
              GimpImage        *image,
              gchar            *prefix,
              guint            *layer_index,
              guchar           *pixels,
              guchar           *buf,
              gboolean          read_mipmaps,
              GError          **error)
{
  guint level;

  if (read_mipmaps)
    {
      for (level = 1; level < load_info->mipmaps; ++level)
        {
          if (! load_layer (fp, load_info, image, level, prefix, layer_index,
                            pixels, buf, error))
            return FALSE;
        }
    }
  else
    {
      /* Skip past mipmaps, as simply not reading them leaves us in the wrong pos for subsequent layers */
      for (level = 1; level < load_info->mipmaps; ++level)
        {
          guint width  = MAX (1, load_info->width  >> level);
          guint height = MAX (1, load_info->height >> level);
          guint size   = load_info->linear_size >> (2 * level);

          if (load_info->fmt_flags & DDPF_FOURCC)
            {
              size = ((width + 3) >> 2) * ((height + 3) >> 2);
              if ((load_info->comp_format == DDS_COMPRESS_BC1) ||
                  (load_info->comp_format == DDS_COMPRESS_BC4))
                size *= 8;
              else
                size *= 16;
            }

          fseek (fp, size, SEEK_CUR);
        }
    }

  return TRUE;
}

static gboolean
load_face (FILE             *fp,
           dds_load_info_t  *load_info,
           GimpImage        *image,
           gchar            *prefix,
           guint            *layer_index,
           guchar           *pixels,
           guchar           *buf,
           gboolean          read_mipmaps,
           GError          **error)
{
  if (! load_layer (fp, load_info, image, 0, prefix,
                    layer_index, pixels, buf, error))
    return FALSE;

  return load_mipmaps (fp, load_info, image, prefix, layer_index,
                       pixels, buf, read_mipmaps, error);
}

static gboolean
load_dialog (GimpProcedure       *procedure,
             GimpProcedureConfig *config)
{
  GtkWidget *dialog;
  GtkWidget *vbox;
  gboolean   run;

  dialog = gimp_procedure_dialog_new (procedure,
                                      config,
                                      _("Open DDS"));

  vbox = gimp_procedure_dialog_fill_box (GIMP_PROCEDURE_DIALOG (dialog),
                                         "dds-read-box",
                                         "load-mipmaps",
                                         "flip-image",
                                         NULL);
  gtk_box_set_spacing (GTK_BOX (vbox), 8);
  gtk_container_set_border_width (GTK_CONTAINER (vbox), 8);

  gimp_procedure_dialog_fill (GIMP_PROCEDURE_DIALOG (dialog),
                              "dds-read-box", NULL);
  gtk_widget_set_visible (dialog, TRUE);

  run = gimp_procedure_dialog_run (GIMP_PROCEDURE_DIALOG (dialog));

  gtk_widget_destroy (dialog);

  return run;
}

/* --- end plug-ins/field-io/file-dds/ddsread.c --- */

/* --- begin plug-ins/field-io/file-dds/ddswrite.c --- */
/*
 * DDS AmmoOS Image plugin
 *
 * Copyright (C) 2004-2012 Shawn Kirst <skirst@gmail.com>,
 * with parts (C) 2003 Arne Reuter <homepage@arnereuter.de> where specified.
 *
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public
 * License as published by the Free Software Foundation; either
 * version 2 of the License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; see the file COPYING.  If not, write to
 * the Free Software Foundation, 51 Franklin Street, Fifth Floor
 * Boston, MA 02110-1301, USA.
 */

#include "config.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#include <gtk/gtk.h>
#include <glib/gstdio.h>

#include <libgimp/ammoos.h>
#include <libgimp/gimpui.h>

#include <libgimp/stdplugins-intl.h>

#include "dds.h"
#include "ddswrite.h"
#include "dxt.h"
#include "endian_rw.h"
#include "imath.h"
#include "mipmap.h"
#include "misc.h"


static gboolean      write_image        (FILE                *fp,
                                         GimpImage           *image,
                                         GimpDrawable        *drawable,
                                         GimpProcedureConfig *config);
static gboolean      save_dialog        (GimpImage           *image,
                                         GimpDrawable        *drawable,
                                         GimpProcedure       *procedure,
                                         GimpProcedureConfig *config);

static const gchar * check_comp_format  (guint32              format);

static const gchar *cubemap_face_names[4][6] =
{
  {
    "positive x", "negative x",
    "positive y", "negative y",
    "positive z", "negative z"
  },
  {
    "pos x", "neg x",
    "pos y", "neg y",
    "pos z", "neg z",
  },
  {
    "+x", "-x",
    "+y", "-y",
    "+z", "-z"
  },
  {
    "right", "left",
    "top", "bottom",
    "back", "front"
  }
};

static GimpImage *global_image          = NULL;
static GimpLayer *cubemap_faces[6];
static gboolean   is_cubemap            = FALSE;
static gboolean   is_volume             = FALSE;
static gboolean   is_array              = FALSE;
static gboolean   is_mipmap_chain_valid = FALSE;

static struct
{
  gint         format;
  DXGI_FORMAT  dxgi_format;
  gint         bpp;
  gboolean     alpha;
  guint        rmask;
  guint        gmask;
  guint        bmask;
  guint        amask;
} format_info[] =
{
  { DDS_FORMAT_RGB8,    DXGI_FORMAT_UNKNOWN,           3, FALSE, 0x00ff0000, 0x0000ff00, 0x000000ff, 0x00000000},
  { DDS_FORMAT_RGBA8,   DXGI_FORMAT_B8G8R8A8_UNORM,    4, TRUE,  0x00ff0000, 0x0000ff00, 0x000000ff, 0xff000000},
  { DDS_FORMAT_BGR8,    DXGI_FORMAT_UNKNOWN,           4, FALSE, 0x000000ff, 0x0000ff00, 0x00ff0000, 0x00000000},
  { DDS_FORMAT_ABGR8,   DXGI_FORMAT_R8G8B8A8_UNORM,    4, TRUE,  0x000000ff, 0x0000ff00, 0x00ff0000, 0xff000000},
  { DDS_FORMAT_R5G6B5,  DXGI_FORMAT_B5G6R5_UNORM,      2, FALSE, 0x0000f800, 0x000007e0, 0x0000001f, 0x00000000},
  { DDS_FORMAT_RGBA4,   DXGI_FORMAT_B4G4R4A4_UNORM,    2, TRUE,  0x00000f00, 0x000000f0, 0x0000000f, 0x0000f000},
  { DDS_FORMAT_RGB5A1,  DXGI_FORMAT_B5G5R5A1_UNORM,    2, TRUE,  0x00007c00, 0x000003e0, 0x0000001f, 0x00008000},
  { DDS_FORMAT_RGB10A2, DXGI_FORMAT_R10G10B10A2_UNORM, 4, TRUE,  0x000003ff, 0x000ffc00, 0x3ff00000, 0xc0000000},
  { DDS_FORMAT_R3G3B2,  DXGI_FORMAT_UNKNOWN,           1, FALSE, 0x000000e0, 0x0000001c, 0x00000003, 0x00000000},
  { DDS_FORMAT_A8,      DXGI_FORMAT_A8_UNORM,          1, FALSE, 0x00000000, 0x00000000, 0x00000000, 0x000000ff},
  { DDS_FORMAT_L8,      DXGI_FORMAT_R8_UNORM,          1, FALSE, 0x000000ff, 0x00000000, 0x00000000, 0x00000000},
  { DDS_FORMAT_L8A8,    DXGI_FORMAT_UNKNOWN,           2, TRUE,  0x000000ff, 0x00000000, 0x00000000, 0x0000ff00},
  { DDS_FORMAT_AEXP,    DXGI_FORMAT_B8G8R8A8_UNORM,    4, TRUE,  0x00ff0000, 0x0000ff00, 0x000000ff, 0xff000000},
  { DDS_FORMAT_YCOCG,   DXGI_FORMAT_B8G8R8A8_UNORM,    4, TRUE,  0x00ff0000, 0x0000ff00, 0x000000ff, 0xff000000}
};


static gboolean
check_mipmaps (gint savetype)
{
  GList         *layers;
  GList         *list;
  gint           num_layers;
  gint           i, j;
  gint           w, h;
  gint           mipw, miph;
  gint           num_mipmaps;
  gint           num_surfaces = 0;
  gint           min_surfaces = 1;
  gint           max_surfaces = 1;
  gboolean       valid        = TRUE;
  GimpImageType  type;

  /* not handling volume maps for the moment... */
  if (savetype == DDS_SAVE_VOLUMEMAP)
    return 0;

  if (savetype == DDS_SAVE_CUBEMAP)
    {
      min_surfaces = 6;
      max_surfaces = 6;
    }
  else if (savetype == DDS_SAVE_ARRAY)
    {
      min_surfaces = 2;
      max_surfaces = G_MAXINT;
    }

  layers = gimp_image_list_layers (global_image);
  num_layers = g_list_length (layers);

  w = gimp_image_get_width (global_image);
  h = gimp_image_get_height (global_image);

  num_mipmaps = get_num_mipmaps (w, h);

  type = gimp_drawable_type (layers->data);

  for (list = layers; list; list = g_list_next (list))
    {
      if (type != gimp_drawable_type (list->data))
        return 0;

      if ((gimp_drawable_get_width  (list->data) == w) &&
          (gimp_drawable_get_height (list->data) == h))
        ++num_surfaces;
    }

  if ((num_surfaces < min_surfaces) ||
      (num_surfaces > max_surfaces) ||
      (num_layers != (num_surfaces * num_mipmaps)))
    return 0;

  for (i = 0; valid && i < num_layers; i += num_mipmaps)
    {
      GimpDrawable *drawable = g_list_nth_data (layers, i);

      if ((gimp_drawable_get_width  (drawable) != w) ||
          (gimp_drawable_get_height (drawable) != h))
        {
          valid = FALSE;
          break;
        }

      for (j = 1; j < num_mipmaps; ++j)
        {
          drawable = g_list_nth_data (layers, i + j);

          mipw = w >> j;
          miph = h >> j;
          if (mipw < 1) mipw = 1;
          if (miph < 1) miph = 1;
          if ((gimp_drawable_get_width  (drawable) != mipw) ||
              (gimp_drawable_get_height (drawable) != miph))
            {
              valid = FALSE;
              break;
            }
        }
    }

  return valid;
}

static gboolean
check_cubemap (GimpImage *image)
{
  GimpLayer    **layers;
  gint           num_layers;
  gboolean       cubemap = TRUE;
  gint           i, j, k;
  gint           w, h;
  gchar         *layer_name;
  GimpImageType  type;

  layers     = gimp_image_get_layers (image);
  num_layers = gimp_core_object_array_get_length ((GObject **) layers);

  if (num_layers < 6)
    {
      g_free (layers);
      return FALSE;
    }

  /* Check for a valid cubemap with mipmap layers */
  if (num_layers > 6)
    {
      /* Check that mipmap layers are in order for a cubemap */
      if (! check_mipmaps (DDS_SAVE_CUBEMAP))
        return FALSE;

      /* Invalidate cubemap faces */
      for (i = 0; i < 6; ++i)
        cubemap_faces[i] = NULL;

      /* Find the mipmap level 0 layers */
      w = gimp_image_get_width (image);
      h = gimp_image_get_height (image);

      for (i = 0; i < num_layers; ++i)
        {
          GimpDrawable *drawable = GIMP_DRAWABLE (layers[i]);

          if ((gimp_drawable_get_width  (drawable) != w) ||
              (gimp_drawable_get_height (drawable) != h))
            continue;

          layer_name = (gchar *) gimp_item_get_name (GIMP_ITEM (drawable));
          for (j = 0; j < 6; ++j)
            {
              for (k = 0; k < 4; ++k)
                {
                  if (strstr (layer_name, cubemap_face_names[k][j]))
                    {
                      if (cubemap_faces[j] == NULL)
                        {
                          cubemap_faces[j] = GIMP_LAYER (drawable);
                          break;
                        }
                    }
                }
            }
        }

      /* Check for 6 valid faces */
      for (i = 0; i < 6; ++i)
        {
          if (cubemap_faces[i] == NULL)
            {
              cubemap = FALSE;
              break;
            }
        }

      /* Make sure all faces are of the same type */
      if (cubemap)
        {
          type = gimp_drawable_type (GIMP_DRAWABLE (cubemap_faces[0]));
          for (i = 1; i < 6 && cubemap; ++i)
            {
              if (gimp_drawable_type (GIMP_DRAWABLE (cubemap_faces[i])) != type)
                cubemap = FALSE;
            }
        }
    }

  if (num_layers == 6)
    {
      /* Invalidate cubemap faces */
      for (i = 0; i < 6; ++i)
        cubemap_faces[i] = NULL;

      for (i = 0; i < num_layers; ++i)
        {
          layer_name = (gchar *) gimp_item_get_name (GIMP_ITEM (layers[i]));

          for (j = 0; j < 6; ++j)
            {
              for (k = 0; k < 4; ++k)
                {
                  if (strstr (layer_name, cubemap_face_names[k][j]))
                    {
                      if (cubemap_faces[j] == NULL)
                        {
                          cubemap_faces[j] = layers[i];
                          break;
                        }
                    }
                }
            }
        }

      /* Check for 6 valid faces */
      for (i = 0; i < 6; ++i)
        {
          if (cubemap_faces[i] == NULL)
            {
              cubemap = FALSE;
              break;
            }
        }

      /* Make sure all faces are of the same size */
      if (cubemap)
        {
          w = gimp_drawable_get_width (GIMP_DRAWABLE (cubemap_faces[0]));
          h = gimp_drawable_get_height (GIMP_DRAWABLE (cubemap_faces[0]));

          for (i = 1; i < 6 && cubemap; ++i)
            {
              if ((gimp_drawable_get_width  (GIMP_DRAWABLE (cubemap_faces[i])) != w) ||
                  (gimp_drawable_get_height (GIMP_DRAWABLE (cubemap_faces[i])) != h))
                cubemap = FALSE;
            }
        }

      /* Make sure all faces are of the same type */
      if (cubemap)
        {
          type = gimp_drawable_type (GIMP_DRAWABLE (cubemap_faces[0]));
          for (i = 1; i < 6 && cubemap; ++i)
            {
              if (gimp_drawable_type (GIMP_DRAWABLE (cubemap_faces[i])) != type)
                cubemap = FALSE;
            }
        }
    }
  g_free (layers);

  return cubemap;
}

static gboolean
check_volume (GimpImage *image)
{
  GList         *layers;
  GList         *list;
  gint           num_layers;
  gboolean       volume = FALSE;
  gint           i;
  gint           w, h;
  GimpImageType  type;

  layers = gimp_image_list_layers (image);
  num_layers = g_list_length (layers);

  if (num_layers > 1)
    {
      volume = TRUE;

      /* Make sure all layers are of the same size */
      w = gimp_drawable_get_width  (layers->data);
      h = gimp_drawable_get_height (layers->data);

      for (i = 1, list = layers->next;
           i < num_layers && volume;
           ++i, list = g_list_next (list))
        {
          if ((gimp_drawable_get_width  (list->data) != w) ||
              (gimp_drawable_get_height (list->data) != h))
            volume = FALSE;
        }

      if (volume)
        {
          /* Make sure all layers are of the same type */
          type = gimp_drawable_type (layers->data);

          for (i = 1, list = layers->next;
               i < num_layers && volume;
               ++i, list = g_list_next (list))
            {
              if (gimp_drawable_type (list->data) != type)
                volume = FALSE;
            }
        }
    }

  return volume;
}

static gboolean
check_array (GimpImage *image)
{
  GList         *layers;
  gint           num_layers;
  gboolean       array = FALSE;
  gint           i;
  gint           w, h;
  GimpImageType  type;

  if (check_mipmaps (DDS_SAVE_ARRAY))
    return 1;

  layers = gimp_image_list_layers (image);
  num_layers = g_list_length (layers);

  if (num_layers > 1)
    {
      GList *list;

      array = TRUE;

      /* Make sure all layers are of the same size */
      w = gimp_drawable_get_width  (layers->data);
      h = gimp_drawable_get_height (layers->data);

      for (i = 1, list = g_list_next (layers);
           i < num_layers && array;
           ++i, list = g_list_next (list))
        {
          if ((gimp_drawable_get_width  (list->data)  != w) ||
              (gimp_drawable_get_height (list->data) != h))
            array = FALSE;
        }

      if (array)
        {
          /* Make sure all layers are of the same type */
          type = gimp_drawable_type (layers->data);

          for (i = 1, list = g_list_next (layers);
               i < num_layers;
               ++i, list = g_list_next (list))
            {
              if (gimp_drawable_type (list->data) != type)
                {
                  array = FALSE;
                  break;
                }
            }
        }
    }

  g_list_free (layers);

  return array;
}

static int
get_array_size (GimpImage *image)
{
  GList *layers;
  GList *list;
  gint   num_layers;
  gint   i;
  gint   w, h;
  gint   elements = 0;

  layers = gimp_image_list_layers (image);
  num_layers = g_list_length (layers);

  w = gimp_image_get_width  (image);
  h = gimp_image_get_height (image);

  for (i = 0, list = layers;
       i < num_layers;
       ++i, list = g_list_next (list))
    {
      if ((gimp_drawable_get_width  (list->data) == w) &&
          (gimp_drawable_get_height (list->data) == h))
        {
          elements++;
        }
    }

  g_list_free (layers);

  return elements;
}

GimpPDBStatusType
write_dds (GFile               *file,
           GimpImage           *image,
           GimpDrawable        *drawable,
           gboolean             interactive,
           GimpProcedure       *procedure,
           GimpProcedureConfig *config,
           gboolean             is_duplicate_image)
{
  FILE         *fp;
  GimpParasite *parasite = NULL;
  gint          rc       = 0;
  gint          compression;
  gint          mipmaps;
  gint          savetype;

  savetype = gimp_procedure_config_get_choice_id (config, "save-type");
  mipmaps  = gimp_procedure_config_get_choice_id (config, "mipmaps");

  global_image = image;

  is_mipmap_chain_valid = check_mipmaps (savetype);

  is_cubemap = check_cubemap (image);
  is_volume  = check_volume  (image);
  is_array   = check_array   (image);

  /* Check for imported DDS original settings */
  parasite = gimp_image_get_parasite (image, "dds-import-settings");
  if (parasite)
    {
      gchar   *parasite_data;
      guint32  parasite_size;
      gint     version     = 0;
      gint     comp_format = 0;
      gint     d3d9_format = 0;
      gint     dxgi_format = 0;
      guint    flags       = 0;
      guint    n_mipmaps   = 0;
      guint    n_params    = 0;

      parasite_data = (gchar *) gimp_parasite_get_data (parasite,
                                                        &parasite_size);
      parasite_data = g_strndup (parasite_data, parasite_size);

#ifndef _UCRT
      n_params = sscanf (parasite_data, "%d %d %d %d %d %d", &version,
                         &comp_format, &d3d9_format, &dxgi_format, &flags,
                         &n_mipmaps);
#else
      n_params = sscanf_s (parasite_data, "%d %d %d %d %d %d", &version,
                           &comp_format, &d3d9_format, &dxgi_format, &flags,
                           &n_mipmaps);
#endif
      if (n_params == 6)
        {
          const gchar *config_comp_format;

          config_comp_format = check_comp_format (comp_format);
          g_object_set (config,
                        "compression-format", config_comp_format,
                        NULL);
        }
      g_free (parasite_data);

      gimp_image_detach_parasite (image, "dds-import-settings");
      g_free (parasite);
    }

  compression = gimp_procedure_config_get_choice_id (config,
                                                     "compression-format");

  if (interactive)
    {
      if (! is_mipmap_chain_valid &&
          mipmaps == DDS_MIPMAP_EXISTING)
        {
          g_object_set (config,
                        "mipmaps", "none",
                        NULL);
        }

      if (! save_dialog (image, drawable, procedure, config))
        return GIMP_PDB_CANCEL;
    }
  else
    {
      if ((savetype == DDS_SAVE_CUBEMAP) && (! is_cubemap))
        {
          g_message ("DDS: Cannot save image as cube map");
          return GIMP_PDB_EXECUTION_ERROR;
        }

      if ((savetype == DDS_SAVE_VOLUMEMAP) && (! is_volume))
        {
          g_message ("DDS: Cannot save image as volume map");
          return GIMP_PDB_EXECUTION_ERROR;
        }

      if ((savetype == DDS_SAVE_VOLUMEMAP) && (compression != DDS_COMPRESS_NONE))
        {
          g_message ("DDS: Cannot save volume map with compression");
          return GIMP_PDB_EXECUTION_ERROR;
        }

      if ((mipmaps == DDS_MIPMAP_EXISTING) && (! is_mipmap_chain_valid))
        {
          g_message ("DDS: Cannot save with existing mipmaps as the mipmap chain is incomplete");
          return GIMP_PDB_EXECUTION_ERROR;
        }
    }

  /* Open up the file to write */
  fp = g_fopen (g_file_peek_path (file), "wb");

  if (! fp)
    {
      g_message ("Error opening %s", g_file_peek_path (file));
      return GIMP_PDB_EXECUTION_ERROR;
    }

  gimp_progress_init_printf (_("Saving: %s"), gimp_file_get_utf8_name (file));

  /* If destructive changes are going to happen to the image,
   * make sure we send a duplicate of it to write_image()
   */
  if (! is_duplicate_image)
    {
      GimpImage     *duplicate_image = gimp_image_duplicate (image);
      GimpDrawable **drawables;

      drawables = gimp_image_get_selected_drawables (duplicate_image);
      rc = write_image (fp, duplicate_image, drawables[0], config);
      gimp_image_delete (duplicate_image);
      g_free (drawables);
    }
  else
    {
      rc = write_image (fp, image, drawable, config);
    }

  fclose (fp);

  return rc ? GIMP_PDB_SUCCESS : GIMP_PDB_EXECUTION_ERROR;
}

static void
swap_rb (guchar *pixels,
         guint   n,
         gint    bpp)
{
  guint  i;
  guchar t;

  for (i = 0; i < n; ++i)
    {
      t = pixels[bpp * i + 0];
      pixels[bpp * i + 0] = pixels[bpp * i + 2];
      pixels[bpp * i + 2] = t;
    }
}

static void
convert_pixels (guchar *dst,
                guchar *src,
                gint    format,
                gint    w,
                gint    h,
                gint    d,
                gint    bpp,
                guchar *palette,
                gint    mipmaps)
{
  guint  i, num_pixels;
  guchar r, g, b, a;

  if (d > 0)
    num_pixels = get_volume_mipmapped_size (w, h, d, 1, 0, mipmaps, DDS_COMPRESS_NONE);
  else
    num_pixels = get_mipmapped_size (w, h, 1, 0, mipmaps, DDS_COMPRESS_NONE);

  for (i = 0; i < num_pixels; ++i)
    {
      if (bpp == 1)
        {
          if (palette)
            {
              r = palette[3 * src[i] + 0];
              g = palette[3 * src[i] + 1];
              b = palette[3 * src[i] + 2];
            }
          else
            r = g = b = src[i];

          if (format == DDS_FORMAT_A8)
            a = src[i];
          else
            a = 255;
        }
      else if (bpp == 2)
        {
          r = g = b = src[2 * i];
          a = src[2 * i + 1];
        }
      else if (bpp == 3)
        {
          b = src[3 * i + 0];
          g = src[3 * i + 1];
          r = src[3 * i + 2];
          a = 255;
        }
      else
        {
          b = src[4 * i + 0];
          g = src[4 * i + 1];
          r = src[4 * i + 2];
          a = src[4 * i + 3];
        }

      switch (format)
        {
        case DDS_FORMAT_RGB8:
          dst[3 * i + 0] = b;
          dst[3 * i + 1] = g;
          dst[3 * i + 2] = r;
          break;
        case DDS_FORMAT_RGBA8:
          dst[4 * i + 0] = b;
          dst[4 * i + 1] = g;
          dst[4 * i + 2] = r;
          dst[4 * i + 3] = a;
          break;
        case DDS_FORMAT_BGR8:
          dst[4 * i + 0] = r;
          dst[4 * i + 1] = g;
          dst[4 * i + 2] = b;
          dst[4 * i + 3] = 0;
          break;
        case DDS_FORMAT_ABGR8:
          dst[4 * i + 0] = r;
          dst[4 * i + 1] = g;
          dst[4 * i + 2] = b;
          dst[4 * i + 3] = a;
          break;
        case DDS_FORMAT_R5G6B5:
          PUTL16 (&dst[2 * i],
            (mul8bit (r, 31) << 11) |
            (mul8bit (g, 63) <<  5) |
            (mul8bit (b, 31)      ));
          break;
        case DDS_FORMAT_RGBA4:
          PUTL16 (&dst[2 * i],
            (mul8bit (a, 15) << 12) |
            (mul8bit (r, 15) <<  8) |
            (mul8bit (g, 15) <<  4) |
            (mul8bit (b, 15)      ));
          break;
        case DDS_FORMAT_RGB5A1:
          PUTL16 (&dst[2 * i],
            (((a >> 7) & 0x01) << 15) |
            (mul8bit (r, 31)   << 10) |
            (mul8bit (g, 31)   <<  5) |
            (mul8bit (b, 31)        ));
          break;
        case DDS_FORMAT_RGB10A2:
          PUTL32 (&dst[4 * i],
            ((guint) ((a >> 6) & 0x003) << 30) |
            ((guint) ((b << 2) & 0x3ff) << 20) |
            ((guint) ((g << 2) & 0x3ff) << 10) |
            ((guint) ((r << 2) & 0x3ff)      ));
          break;
        case DDS_FORMAT_R3G3B2:
          dst[i] =
            (mul8bit (r, 7) << 5) |
            (mul8bit (g, 7) << 2) |
            (mul8bit (b, 3)     );
          break;
        case DDS_FORMAT_A8:
          dst[i] = a;
          break;
        case DDS_FORMAT_L8:
          dst[i] =
            ((r * 54 + g * 182 + b * 20) + 128) >> 8;
          break;
        case DDS_FORMAT_L8A8:
          dst[2 * i + 0] =
            ((r * 54 + g * 182 + b * 20) + 128) >> 8;
          dst[2 * i + 1] = a;
          break;
        case DDS_FORMAT_YCOCG:
          dst[4 * i] = a;
          encode_ycocg (&dst[4 * i], r, g, b);
          break;
        case DDS_FORMAT_AEXP:
          encode_alpha_exponent (&dst[4 * i], r, g, b, a);
          break;
        default:
          break;
        }
    }
}

static void
get_mipmap_chain (guchar       *dst,
                  gint          w,
                  gint          h,
                  gint          bpp,
                  GimpImage    *image,
                  GimpDrawable *drawable)
{
  GList      *layers;
  GList      *list;
  gint        num_layers;
  GeglBuffer *buffer;
  const Babl *format;
  gint        i;
  gint        idx = 0;
  gint        offset;
  gint        mipw, miph;

  if (bpp == 1)
    format = babl_format ("Y' u8");
  else if (bpp == 2)
    format = babl_format ("Y'A u8");
  else if (bpp == 3)
    format = babl_format ("R'G'B' u8");
  else
    format = babl_format ("R'G'B'A u8");

  layers = gimp_image_list_layers (image);
  num_layers = g_list_length (layers);

  for (i = 0, list = layers;
       i < num_layers;
       ++i, list = g_list_next (list))
    {
      if (list->data == drawable)
        {
          idx = i;
          break;
        }
    }

  if (i == num_layers)
    return;

  offset = 0;

  while (get_next_mipmap_dimensions (&mipw, &miph, w, h))
    {
      buffer = gimp_drawable_get_buffer (g_list_nth_data (layers, ++idx));

      if ((gegl_buffer_get_width (buffer)  != mipw) ||
          (gegl_buffer_get_height (buffer) != miph))
        {
          g_object_unref (buffer);
          return;
        }

      gegl_buffer_get (buffer, GEGL_RECTANGLE (0, 0, mipw, miph), 1.0, format,
                       dst + offset, GEGL_AUTO_ROWSTRIDE, GEGL_ABYSS_NONE);
      g_object_unref (buffer);

      /* BGRX or BGRA needed */
      if (bpp >= 3)
        swap_rb (dst + offset, mipw * miph, bpp);

      offset += (mipw * miph * bpp);
      w = mipw;
      h = miph;
    }
}

static void
write_layer (FILE                *fp,
             GimpImage           *image,
             GimpDrawable        *drawable,
             GimpProcedureConfig *config,
             gint                 w,
             gint                 h,
             gint                 bpp,
             gint                 fmtbpp,
             gint                 num_mipmaps)
{
  GeglBuffer        *buffer;
  const Babl        *format;
  GimpImageBaseType  basetype;
  GimpImageType      type;
  guchar            *src;
  guchar            *dst;
  guchar            *fmtdst;
  guchar            *tmp;
  guchar            *palette = NULL;
  gint               i, c;
  gint               x, y;
  gint               size;
  gint               fmtsize;
  gint               offset  = 0;
  gint               colors;
  gint               compression;
  gint               mipmaps;
  gint               pixel_format;
  gboolean           perceptual_metric;
  gint               flags   = 0;

  g_object_get (config,
                "perceptual-metric",  &perceptual_metric,
                NULL);
  compression  = gimp_procedure_config_get_choice_id (config, "compression-format");
  pixel_format = gimp_procedure_config_get_choice_id (config, "format");
  mipmaps      = gimp_procedure_config_get_choice_id (config, "mipmaps");

  basetype = gimp_image_get_base_type (image);
  type = gimp_drawable_type (drawable);

  buffer = gimp_drawable_get_buffer (drawable);

  src = g_malloc (w * h * bpp);

  if (basetype == GIMP_INDEXED)
    format = gimp_drawable_get_format (drawable);
  else if (bpp == 1)
    format = babl_format ("Y' u8");
  else if (bpp == 2)
    format = babl_format ("Y'A u8");
  else if (bpp == 3)
    format = babl_format ("R'G'B' u8");
  else
    format = babl_format ("R'G'B'A u8");

  gegl_buffer_get (buffer, GEGL_RECTANGLE (0, 0, w, h), 1.0, format, src,
                   GEGL_AUTO_ROWSTRIDE, GEGL_ABYSS_NONE);

  if (basetype == GIMP_INDEXED)
    {
      palette = gimp_palette_get_colormap (gimp_image_get_palette (image), babl_format ("R'G'B' u8"), &colors, NULL);

      if (type == GIMP_INDEXEDA_IMAGE)
        {
          tmp = g_malloc (w * h);
          for (i = 0; i < w * h; ++i)
            tmp[i] = src[2 * i];
          g_free (src);
          src = tmp;
          bpp = 1;
        }
    }

  /* We want and assume BGRA ordered pixels for bpp >= 3 from here on  */
  if (bpp >= 3 && compression != DDS_COMPRESS_BC7)
    swap_rb (src, w * h, bpp);

  if (compression == DDS_COMPRESS_BC3N)
    {
      if (bpp != 4)
        {
          fmtsize = w * h * 4;
          fmtdst = g_malloc (fmtsize);
          convert_pixels (fmtdst, src, DDS_FORMAT_RGBA8, w, h, 0, bpp,
                          palette, 1);
          g_free (src);
          src = fmtdst;
          bpp = 4;
        }

      for (y = 0; y < h; ++y)
        {
          for (x = 0; x < w; ++x)
            {
              /* set alpha to red (x) */
              src[y * (w * 4) + (x * 4) + 3] =
                src[y * (w * 4) + (x * 4) + 2];
              /* set red to 1 */
              src[y * (w * 4) + (x * 4) + 2] = 255;
            }
        }
    }

  /* RXGB (Doom3) */
  if (compression == DDS_COMPRESS_RXGB)
    {
      if (bpp != 4)
        {
          fmtsize = w * h * 4;
          fmtdst = g_malloc (fmtsize);
          convert_pixels (fmtdst, src, DDS_FORMAT_RGBA8, w, h, 0, bpp,
                          palette, 1);
          g_free (src);
          src = fmtdst;
          bpp = 4;
        }

      for (y = 0; y < h; ++y)
        {
          for (x = 0; x < w; ++x)
            {
              /* swap red and alpha */
              c = src[y * (w * 4) + (x * 4) + 3];
              src[y * (w * 4) + (x * 4) + 3] =
                src[y * (w * 4) + (x * 4) + 2];
              src[y * (w * 4) + (x * 4) + 2] = c;
            }
        }
    }

  if (compression == DDS_COMPRESS_YCOCG ||
      compression == DDS_COMPRESS_YCOCGS) /* convert to YCoCG */
    {
      fmtsize = w * h * 4;
      fmtdst = g_malloc (fmtsize);
      convert_pixels (fmtdst, src, DDS_FORMAT_YCOCG, w, h, 0, bpp,
                      palette, 1);
      g_free (src);
      src = fmtdst;
      bpp = 4;
    }

  if (compression == DDS_COMPRESS_AEXP)
    {
      fmtsize = w * h * 4;
      fmtdst = g_malloc (fmtsize);
      convert_pixels (fmtdst, src, DDS_FORMAT_AEXP, w, h, 0, bpp,
                      palette, 1);
      g_free (src);
      src = fmtdst;
      bpp = 4;
    }

  if (compression == DDS_COMPRESS_NONE)
    {
      if (num_mipmaps > 1)
        {
          /* Pre-convert indexed images to RGB if not exporting as indexed */
          if (pixel_format > DDS_FORMAT_DEFAULT && basetype == GIMP_INDEXED)
            {
              fmtsize = get_mipmapped_size (w, h, 3, 0, num_mipmaps, DDS_COMPRESS_NONE);
              fmtdst = g_malloc (fmtsize);
              convert_pixels (fmtdst, src, DDS_FORMAT_RGB8, w, h, 0, bpp,
                              palette, 1);
              g_free (src);
              src = fmtdst;
              bpp = 3;
              palette = NULL;
            }

          size = get_mipmapped_size (w, h, bpp, 0, num_mipmaps,
                                     DDS_COMPRESS_NONE);
          dst = g_malloc (size);
          if (mipmaps == DDS_MIPMAP_GENERATE)
            {
              gint     mipmap_filter;
              gint     mipmap_wrap;
              gboolean gamma_correct;
              gboolean srgb;
              gdouble  gamma;
              gboolean preserve_alpha_coverage;
              gdouble  alpha_test_threshold;

              g_object_get (config,
                            "gamma-correct",           &gamma_correct,
                            "srgb",                    &srgb,
                            "gamma",                   &gamma,
                            "preserve-alpha-coverage", &preserve_alpha_coverage,
                            "alpha-test-threshold",    &alpha_test_threshold,
                            NULL);
              mipmap_filter = gimp_procedure_config_get_choice_id (config,
                                                                   "mipmap-filter");
              mipmap_wrap   = gimp_procedure_config_get_choice_id (config,
                                                                   "mipmap-wrap");

              generate_mipmaps (dst, src, w, h, bpp, palette != NULL,
                                num_mipmaps,
                                mipmap_filter,
                                mipmap_wrap,
                                gamma_correct + srgb,
                                gamma,
                                preserve_alpha_coverage,
                                alpha_test_threshold);
            }
          else
            {
              memcpy (dst, src, w * h * bpp);
              get_mipmap_chain (dst + (w * h * bpp), w, h, bpp, image, drawable);
            }

          if (pixel_format > DDS_FORMAT_DEFAULT)
            {
              fmtsize = get_mipmapped_size (w, h, fmtbpp, 0, num_mipmaps,
                                            DDS_COMPRESS_NONE);
              fmtdst = g_malloc (fmtsize);

              convert_pixels (fmtdst, dst, pixel_format, w, h, 0, bpp,
                              palette, num_mipmaps);

              g_free (dst);
              dst = fmtdst;
              bpp = fmtbpp;
            }

          for (i = 0; i < num_mipmaps; ++i)
            {
              size = get_mipmapped_size (w, h, bpp, i, 1, DDS_COMPRESS_NONE);
              fwrite (dst + offset, 1, size, fp);
              offset += size;
            }

          g_free (dst);
        }
      else
        {
          if (pixel_format > DDS_FORMAT_DEFAULT)
            {
              fmtdst = g_malloc (h * w * fmtbpp);
              convert_pixels (fmtdst, src, pixel_format, w, h, 0, bpp,
                              palette, 1);
              g_free (src);
              src = fmtdst;
              bpp = fmtbpp;
            }

          fwrite (src, 1, h * w * bpp, fp);
        }
    }
  else
    {
      size = get_mipmapped_size (w, h, bpp, 0, num_mipmaps, compression);

      dst = g_malloc (size);

      if (basetype == GIMP_INDEXED)
        {
          fmtsize = get_mipmapped_size (w, h, 3, 0, num_mipmaps,
                                        DDS_COMPRESS_NONE);
          fmtdst = g_malloc (fmtsize);
          convert_pixels (fmtdst, src, DDS_FORMAT_RGB8, w, h, 0, bpp,
                          palette, num_mipmaps);
          g_free (src);
          src = fmtdst;
          bpp = 3;
        }

      if (num_mipmaps > 1)
        {
          fmtsize = get_mipmapped_size (w, h, bpp, 0, num_mipmaps,
                                        DDS_COMPRESS_NONE);
          fmtdst = g_malloc (fmtsize);
          if (mipmaps == DDS_MIPMAP_GENERATE)
            {
              gint     mipmap_filter;
              gint     mipmap_wrap;
              gboolean gamma_correct;
              gboolean srgb;
              gdouble  gamma;
              gboolean preserve_alpha_coverage;
              gdouble  alpha_test_threshold;

              g_object_get (config,
                            "gamma-correct",           &gamma_correct,
                            "srgb",                    &srgb,
                            "gamma",                   &gamma,
                            "preserve-alpha-coverage", &preserve_alpha_coverage,
                            "alpha-test-threshold",    &alpha_test_threshold,
                            NULL);
              mipmap_filter = gimp_procedure_config_get_choice_id (config,
                                                                   "mipmap-filter");
              mipmap_wrap   = gimp_procedure_config_get_choice_id (config,
                                                                   "mipmap-wrap");

              generate_mipmaps (fmtdst, src, w, h, bpp, 0, num_mipmaps,
                                mipmap_filter,
                                mipmap_wrap,
                                gamma_correct + srgb,
                                gamma,
                                preserve_alpha_coverage,
                                alpha_test_threshold);
            }
          else
            {
              memcpy (fmtdst, src, w * h * bpp);
              get_mipmap_chain (fmtdst + (w * h * bpp), w, h, bpp, image, drawable);
            }

          g_free (src);
          src = fmtdst;
        }

      flags = 0;
      if (perceptual_metric)
        flags |= DXT_PERCEPTUAL;

      dxt_compress (dst, src, compression, w, h, bpp, num_mipmaps, flags);

      fwrite (dst, 1, size, fp);

      g_free (dst);
    }

  g_free (src);

  g_object_unref (buffer);
}

static void
write_volume_mipmaps (FILE                *fp,
                      GimpImage           *image,
                      GimpProcedureConfig *config,
                      GList               *layers,
                      gint                 w,
                      gint                 h,
                      gint                 d,
                      gint                 bpp,
                      gint                 fmtbpp,
                      gint                 num_mipmaps)
{
  GList             *list;
  gint               i;
  gint               size;
  gint               offset;
  gint               colors;
  guchar            *src;
  guchar            *dst;
  guchar            *tmp;
  guchar            *fmtdst;
  guchar            *palette = 0;
  GeglBuffer        *buffer;
  const Babl        *format;
  GimpImageBaseType  type;
  gint               compression;
  gint               pixel_format;
  gint               mipmap_filter;
  gint               mipmap_wrap;
  gboolean           gamma_correct;
  gboolean           srgb;
  gdouble            gamma;

  g_object_get (config,
                "gamma-correct",      &gamma_correct,
                "srgb",               &srgb,
                "gamma",              &gamma,
                NULL);
  compression = gimp_procedure_config_get_choice_id (config,
                                                     "compression-format");
  pixel_format = gimp_procedure_config_get_choice_id (config, "format");
  mipmap_filter = gimp_procedure_config_get_choice_id (config,
                                                       "mipmap-filter");
  mipmap_wrap = gimp_procedure_config_get_choice_id (config, "mipmap-wrap");

  type = gimp_image_get_base_type (image);

  if (compression != DDS_COMPRESS_NONE)
    return;

  src = g_malloc (w * h * bpp * d);

  if (bpp == 1)
    format = babl_format ("Y' u8");
  else if (bpp == 2)
    format = babl_format ("Y'A u8");
  else if (bpp == 3)
    format = babl_format ("R'G'B' u8");
  else
    format = babl_format ("R'G'B'A u8");

  if (gimp_image_get_base_type (image) == GIMP_INDEXED)
    palette = gimp_palette_get_colormap (gimp_image_get_palette (image), babl_format ("R'G'B' u8"), &colors, NULL);

  offset = 0;
  for (i = 0, list = layers;
       i < d;
       ++i, list = g_list_next (list))
    {
      buffer = gimp_drawable_get_buffer (list->data);
      gegl_buffer_get (buffer, GEGL_RECTANGLE (0, 0, w, h), 1.0, format,
                       src + offset, GEGL_AUTO_ROWSTRIDE, GEGL_ABYSS_NONE);
      offset += (w * h * bpp);
      g_object_unref (buffer);
    }

  if (gimp_drawable_type (layers->data) == GIMP_INDEXEDA_IMAGE)
    {
      tmp = g_malloc (w * h * d);
      for (i = 0; i < w * h * d; ++i)
        tmp[i] = src[2 * i];
      g_free (src);
      src = tmp;
      bpp = 1;
    }

  /* We want and assume BGRA ordered pixels for bpp >= 3 from here on */
  if (bpp >= 3 && compression != DDS_COMPRESS_BC7)
    swap_rb (src, w * h * d, bpp);

  /* Pre-convert indexed images to RGB if not exporting as indexed */
  if (pixel_format > DDS_FORMAT_DEFAULT && type == GIMP_INDEXED)
    {
      size = get_volume_mipmapped_size (w, h, d, 3, 0, num_mipmaps,
                                        DDS_COMPRESS_NONE);
      dst = g_malloc (size);
      convert_pixels (dst, src, DDS_FORMAT_RGB8, w, h, d, bpp, palette, 1);
      g_free (src);
      src = dst;
      bpp = 3;
      palette = NULL;
    }

  size = get_volume_mipmapped_size (w, h, d, bpp, 0, num_mipmaps,
                                    compression);

  dst = g_malloc (size);

  offset = get_volume_mipmapped_size (w, h, d, bpp, 0, 1,
                                      compression);

  generate_volume_mipmaps (dst, src, w, h, d, bpp,
                           palette != NULL, num_mipmaps,
                           mipmap_filter,
                           mipmap_wrap,
                           gamma_correct + srgb,
                           gamma);

  if (pixel_format > DDS_FORMAT_DEFAULT)
    {
      size = get_volume_mipmapped_size (w, h, d, fmtbpp, 0, num_mipmaps,
                                        compression);
      offset = get_volume_mipmapped_size (w, h, d, fmtbpp, 0, 1,
                                          compression);
      fmtdst = g_malloc (size);

      convert_pixels (fmtdst, dst, pixel_format, w, h, d, bpp,
                      palette, num_mipmaps);
      g_free (dst);
      dst = fmtdst;
    }

  fwrite (dst + offset, 1, size, fp);

  g_free (src);
  g_free (dst);
}

static gboolean
write_image (FILE                *fp,
             GimpImage           *image,
             GimpDrawable        *drawable,
             GimpProcedureConfig *config)
{
  GimpImageType      drawable_type;
  GimpImageBaseType  basetype;
  gint               i, w, h;
  gint               bpp        = 0;
  gint               fmtbpp     = 0;
  gboolean           has_alpha  = FALSE;
  gboolean           is_dx10    = FALSE;
  guint              fourcc     = 0;
  gint               array_size = 1;
  gint               num_mipmaps;
  guchar             hdr[DDS_HEADERSIZE];
  guchar             hdr10[DDS_HEADERSIZE_DX10];
  guint              flags = 0, pflags = 0, caps = 0, caps2 = 0, size = 0;
  guint              rmask = 0, gmask = 0, bmask = 0, amask = 0;
  DXGI_FORMAT        dxgi_format = DXGI_FORMAT_UNKNOWN;
  gint32             num_layers;
  GList             *layers, *list;
  guchar            *cmap;
  gint               colors;
  gint               compression, mipmaps;
  gint               savetype, pixel_format;
  gint               transindex;
  gboolean           flip_export;

  g_object_get (config,
                "transparent-index",  &transindex,
                "flip-image",         &flip_export,
                NULL);
  savetype     = gimp_procedure_config_get_choice_id (config, "save-type");
  compression  = gimp_procedure_config_get_choice_id (config, "compression-format");
  pixel_format = gimp_procedure_config_get_choice_id (config, "format");
  mipmaps      = gimp_procedure_config_get_choice_id (config, "mipmaps");

  if (flip_export)
    gimp_image_flip (image, GIMP_ORIENTATION_VERTICAL);

  layers = gimp_image_list_layers (image);
  num_layers = g_list_length (layers);

  if (mipmaps == DDS_MIPMAP_EXISTING)
    drawable = layers->data;

  if (savetype == DDS_SAVE_SELECTED_LAYER)
    {
      w = gimp_drawable_get_width  (drawable);
      h = gimp_drawable_get_height (drawable);
    }
  else
    {
      w = gimp_image_get_width  (image);
      h = gimp_image_get_height (image);
    }

  basetype = gimp_image_get_base_type (image);
  drawable_type = gimp_drawable_type (drawable);

  switch (drawable_type)
    {
    case GIMP_RGB_IMAGE:      bpp = 3; break;
    case GIMP_RGBA_IMAGE:     bpp = 4; break;
    case GIMP_GRAY_IMAGE:     bpp = 1; break;
    case GIMP_GRAYA_IMAGE:    bpp = 2; break;
    case GIMP_INDEXED_IMAGE:  bpp = 1; break;
    case GIMP_INDEXEDA_IMAGE: bpp = 2; break;
    default:                  break;
    }

  /* Get uncompressed format data */
  if (pixel_format > DDS_FORMAT_DEFAULT)
    {
      for (i = 0; ; ++i)
        {
          if (format_info[i].format == pixel_format)
            {
              fmtbpp = format_info[i].bpp;
              has_alpha = format_info[i].alpha;
              rmask = format_info[i].rmask;
              gmask = format_info[i].gmask;
              bmask = format_info[i].bmask;
              amask = format_info[i].amask;
              dxgi_format = format_info[i].dxgi_format;
              break;
            }
        }
    }
  else if (bpp == 1)
    {
      if (basetype == GIMP_INDEXED)
        {
          fmtbpp = 1;
          has_alpha = FALSE;
          rmask = bmask = gmask = amask = 0;
        }
      else
        {
          fmtbpp = 1;
          has_alpha = FALSE;
          rmask = 0x000000ff;
          gmask = bmask = amask = 0;
          dxgi_format = DXGI_FORMAT_R8_UNORM;
        }
    }
  else if (bpp == 2)
    {
      if (basetype == GIMP_INDEXED)
        {
          fmtbpp = 1;
          has_alpha = FALSE;
          rmask = gmask = bmask = amask = 0;
        }
      else
        {
          fmtbpp = 2;
          has_alpha = TRUE;
          rmask = 0x000000ff;
          gmask = 0x00000000;
          bmask = 0x00000000;
          amask = 0x0000ff00;
        }
    }
  else if (bpp == 3)
    {
      fmtbpp = 3;
      rmask = 0x00ff0000;
      gmask = 0x0000ff00;
      bmask = 0x000000ff;
      amask = 0x00000000;
    }
  else
    {
      fmtbpp = 4;
      has_alpha = TRUE;
      rmask = 0x00ff0000;
      gmask = 0x0000ff00;
      bmask = 0x000000ff;
      amask = 0xff000000;
      dxgi_format = DXGI_FORMAT_B8G8R8A8_UNORM;
    }

  /* Write header */
  memset (hdr, 0, DDS_HEADERSIZE);

  PUTL32 (hdr,       FOURCC ('D','D','S',' '));
  PUTL32 (hdr + 4,   124);  /* Header size */
  PUTL32 (hdr + 12,  h);
  PUTL32 (hdr + 16,  w);
  PUTL32 (hdr + 76,  32);  /* Pixel Format size */

  if (compression == DDS_COMPRESS_NONE)
    {
      PUTL32 (hdr + 88,  fmtbpp << 3);
      PUTL32 (hdr + 92,  rmask);
      PUTL32 (hdr + 96,  gmask);
      PUTL32 (hdr + 100, bmask);
      PUTL32 (hdr + 104, amask);
    }

  /* Put some custom info in the reserved area to identify the origin of the image */
  PUTL32 (hdr + 32, FOURCC ('G','I','M','P'));
  PUTL32 (hdr + 36, FOURCC ('-','D','D','S'));
  PUTL32 (hdr + 40, DDS_PLUGIN_VERSION);

  flags = DDSD_CAPS | DDSD_PIXELFORMAT | DDSD_WIDTH | DDSD_HEIGHT;

  caps = DDSCAPS_TEXTURE;
  if (mipmaps)
    {
      flags |= DDSD_MIPMAPCOUNT;
      caps  |= (DDSCAPS_COMPLEX | DDSCAPS_MIPMAP);
      num_mipmaps = get_num_mipmaps (w, h);
    }
  else
    {
      num_mipmaps = 1;
    }

  if ((savetype == DDS_SAVE_CUBEMAP) && is_cubemap)
    {
      caps  |= DDSCAPS_COMPLEX;
      caps2 |= (DDSCAPS2_CUBEMAP | DDSCAPS2_CUBEMAP_ALL_FACES);
    }
  else if ((savetype == DDS_SAVE_VOLUMEMAP) && is_volume)
    {
      PUTL32 (hdr + 24, num_layers);  /* Depth */
      flags |= DDSD_DEPTH;
      caps  |= DDSCAPS_COMPLEX;
      caps2 |= DDSCAPS2_VOLUME;
    }

  PUTL32 (hdr + 28,  num_mipmaps);
  PUTL32 (hdr + 108, caps);
  PUTL32 (hdr + 112, caps2);

  if (compression == DDS_COMPRESS_NONE)  /* Write uncompressed data */
    {
      flags |= DDSD_PITCH;

      if (pixel_format > DDS_FORMAT_DEFAULT)
        {
          if (pixel_format == DDS_FORMAT_A8)
            pflags |= DDPF_ALPHA;
          else
            {
              if (((fmtbpp == 1) || (pixel_format == DDS_FORMAT_L8A8)) &&
                  (pixel_format != DDS_FORMAT_R3G3B2))
                pflags |= DDPF_LUMINANCE;
              else
                pflags |= DDPF_RGB;
            }
        }
      else
        {
          if (bpp == 1 || bpp == 2)
            {
              if (basetype == GIMP_INDEXED)
                pflags |= DDPF_PALETTEINDEXED8;
              else
                pflags |= DDPF_LUMINANCE;
            }
          else
            {
              pflags |= DDPF_RGB;
            }
        }

      if (has_alpha)
        pflags |= DDPF_ALPHAPIXELS;

      PUTL32 (hdr + 8,  flags);
      PUTL32 (hdr + 20, w * fmtbpp);  /* Pitch */
      PUTL32 (hdr + 80, pflags);

      /* Write extra FourCC info specific to AmmoOS Image DDS. When the image
       * is read again we use this information to decode the pixels.
       */
      if (pixel_format == DDS_FORMAT_AEXP)
        {
          PUTL32 (hdr + 44, FOURCC ('A','E','X','P'));
        }
      else if (pixel_format == DDS_FORMAT_YCOCG)
        {
          PUTL32 (hdr + 44, FOURCC ('Y','C','G','1'));
        }
    }
  else  /* Write compressed data */
    {
      flags |= DDSD_LINEARSIZE;
      pflags = DDPF_FOURCC;

      switch (compression)
        {
        case DDS_COMPRESS_BC1:
          fourcc = FOURCC ('D','X','T','1');
          dxgi_format = DXGI_FORMAT_BC1_UNORM;
          break;

        case DDS_COMPRESS_BC2:
          fourcc = FOURCC ('D','X','T','3');
          dxgi_format = DXGI_FORMAT_BC2_UNORM;
          break;

        case DDS_COMPRESS_BC3:
        case DDS_COMPRESS_BC3N:
        case DDS_COMPRESS_YCOCG:
        case DDS_COMPRESS_YCOCGS:
        case DDS_COMPRESS_AEXP:
          fourcc = FOURCC ('D','X','T','5');
          dxgi_format = DXGI_FORMAT_BC3_UNORM;
          break;

        case DDS_COMPRESS_RXGB:
          fourcc = FOURCC ('R','X','G','B');
          dxgi_format = DXGI_FORMAT_BC3_UNORM;
          break;

        case DDS_COMPRESS_BC4:
          fourcc = FOURCC ('A','T','I','1');
          dxgi_format = DXGI_FORMAT_BC4_UNORM;
          /*is_dx10 = TRUE;*/
          break;

        case DDS_COMPRESS_BC5:
          fourcc = FOURCC ('A','T','I','2');
          dxgi_format = DXGI_FORMAT_BC5_UNORM;
          /*is_dx10 = TRUE;*/
          break;

        case DDS_COMPRESS_BC7:
          dxgi_format = DXGI_FORMAT_BC7_UNORM;
          is_dx10     = TRUE;
        }

      if ((compression == DDS_COMPRESS_BC3N) ||
          (compression == DDS_COMPRESS_RXGB))
        {
          pflags |= DDPF_NORMAL;
        }

      PUTL32 (hdr + 8,  flags);
      PUTL32 (hdr + 80, pflags);
      PUTL32 (hdr + 84, fourcc);

      /* Linear size */
      size = ((w + 3) >> 2) * ((h + 3) >> 2);
      if ((compression == DDS_COMPRESS_BC1) ||
          (compression == DDS_COMPRESS_BC4))
        size *= 8;
      else
        size *= 16;

      PUTL32 (hdr + 20, size);

      /*
       * write extra fourcc info - this is special to AmmoOS Image DDS. When the image
       * is read by the plugin, we can detect the added information to decode
       * the pixels
       */
      if (compression == DDS_COMPRESS_AEXP)
        {
          PUTL32 (hdr + 44, FOURCC ('A','E','X','P'));
        }
      else if (compression == DDS_COMPRESS_YCOCG)
        {
          PUTL32 (hdr + 44, FOURCC ('Y','C','G','1'));
        }
      else if (compression == DDS_COMPRESS_YCOCGS)
        {
          PUTL32 (hdr + 44, FOURCC ('Y','C','G','2'));
        }
    }

  /* Texture arrays always require a DX10 header */
  if (savetype == DDS_SAVE_ARRAY)
    is_dx10 = TRUE;

  /* Upgrade to DX10 header when desired */
  if (is_dx10)
    {
      array_size = ((savetype == DDS_SAVE_SELECTED_LAYER ||
                     savetype == DDS_SAVE_VISIBLE_LAYERS) ?
                    1 : get_array_size (image));

      PUTL32 (hdr10 +  0, dxgi_format);
      PUTL32 (hdr10 +  4, D3D10_RESOURCE_DIMENSION_TEXTURE2D);
      PUTL32 (hdr10 +  8, 0);
      PUTL32 (hdr10 + 12, array_size);
      PUTL32 (hdr10 + 16, 0);

      /* Update main header accordingly */
      PUTL32 (hdr + 80, pflags | DDPF_FOURCC);
      PUTL32 (hdr + 84, FOURCC ('D','X','1','0'));
    }

  fwrite (hdr, DDS_HEADERSIZE, 1, fp);

  if (is_dx10)
    fwrite (hdr10, DDS_HEADERSIZE_DX10, 1, fp);

  /* Write palette for indexed images */
  if ((basetype == GIMP_INDEXED) &&
      (pixel_format == DDS_FORMAT_DEFAULT) &&
      (compression == DDS_COMPRESS_NONE))
    {
      const guchar zero[4] = {0, 0, 0, 0};
      cmap = gimp_palette_get_colormap (gimp_image_get_palette (image), babl_format ("R'G'B' u8"), &colors, NULL);

      for (i = 0; i < colors; ++i)
        {
          fwrite (&cmap[3 * i], 1, 3, fp);
          if (i == transindex)
            fputc (0, fp);
          else
            fputc (255, fp);
        }

      /* Pad unused palette space with zeroes */
      for (; i < 256; ++i)
        fwrite (zero, 1, 4, fp);
    }

  if (savetype == DDS_SAVE_CUBEMAP)  /* Write cubemap layers */
    {
      for (i = 0; i < 6; ++i)
        {
          write_layer (fp, image, GIMP_DRAWABLE (cubemap_faces[i]), config,
                       w, h, bpp, fmtbpp,
                       num_mipmaps);
          gimp_progress_update ((float)(i + 1) / 6.0);
        }
    }
  else if (savetype == DDS_SAVE_VOLUMEMAP)  /* Write volume slices */
    {
      for (i = 0, list = layers;
           i < num_layers;
           ++i, list = g_list_next (list))
        {
          write_layer (fp, image, list->data, config,
                       w, h, bpp, fmtbpp, 1);
          gimp_progress_update ((float)i / (float)num_layers);
        }

      if (num_mipmaps > 1)
        write_volume_mipmaps (fp, image, config, layers, w, h, num_layers,
                              bpp, fmtbpp, num_mipmaps);
    }
  else if (savetype == DDS_SAVE_ARRAY)  /* Write array entries */
    {
      for (i = 0, list = layers;
           i < num_layers;
           ++i, list = g_list_next (list))
        {
          if ((gimp_drawable_get_width  (list->data) == w) &&
              (gimp_drawable_get_height (list->data) == h))
            {
              write_layer (fp, image, list->data, config,
                           w, h, bpp, fmtbpp, num_mipmaps);
            }

          gimp_progress_update ((float)i / (float)num_layers);
        }
    }
  else
    {
      if (savetype == DDS_SAVE_VISIBLE_LAYERS)
        drawable = GIMP_DRAWABLE (gimp_image_merge_visible_layers (image,
                                                                   GIMP_CLIP_TO_IMAGE));
      write_layer (fp, image, drawable, config,
                   w, h, bpp, fmtbpp, num_mipmaps);
    }

  gimp_progress_update (1.0);

  return TRUE;
}


static void
config_notify (GimpProcedureConfig *config,
               const GParamSpec    *pspec,
               GimpProcedureDialog *dialog)
{
  if (! strcmp (pspec->name, "compression-format"))
    {
      gint compression;

      compression = gimp_procedure_config_get_choice_id (config,
                                                         "compression-format");

      gimp_procedure_dialog_set_sensitive (GIMP_PROCEDURE_DIALOG (dialog),
                                           "format",
                                           compression == DDS_COMPRESS_NONE,
                                           NULL, NULL, FALSE);

      gimp_procedure_dialog_set_sensitive (GIMP_PROCEDURE_DIALOG (dialog),
                                           "perceptual-metric",
                                           compression != DDS_COMPRESS_NONE,
                                           NULL, NULL, FALSE);
    }
  else if (! strcmp (pspec->name, "save-type"))
    {
      GParamSpec *cspec;
      GimpChoice *choice;
      gint        savetype;

      savetype = gimp_procedure_config_get_choice_id (config, "save-type");

      switch (savetype)
        {
        case DDS_SAVE_SELECTED_LAYER:
        case DDS_SAVE_VISIBLE_LAYERS:
        case DDS_SAVE_CUBEMAP:
        case DDS_SAVE_ARRAY:
          gimp_procedure_dialog_set_sensitive (GIMP_PROCEDURE_DIALOG (dialog),
                                               "compression-format", TRUE,
                                               NULL, NULL, FALSE);
          break;

        case DDS_SAVE_VOLUMEMAP:
          g_object_set (config,
                        "compression-format", "none",
                        NULL);
          gimp_procedure_dialog_set_sensitive (GIMP_PROCEDURE_DIALOG (dialog),
                                               "compression-format", FALSE,
                                               NULL, NULL, FALSE);
          break;
        }

      cspec  = g_object_class_find_property (G_OBJECT_GET_CLASS (config), "mipmaps");
      choice = gimp_param_spec_choice_get_choice (cspec);
      gimp_choice_set_sensitive (choice, "existing", check_mipmaps (savetype));
    }
  else if (! strcmp (pspec->name, "mipmaps"))
    {
      gint     mipmaps;
      gboolean gamma_correct;
      gboolean srgb;
      gboolean preserve_alpha_coverage;

      g_object_get (config,
                    "gamma-correct",           &gamma_correct,
                    "srgb",                    &srgb,
                    "preserve-alpha-coverage", &preserve_alpha_coverage,
                    NULL);
      mipmaps = gimp_procedure_config_get_choice_id (config, "mipmaps");

      gimp_procedure_dialog_set_sensitive (GIMP_PROCEDURE_DIALOG (dialog),
                                           "mipmap-filter",
                                           mipmaps == DDS_MIPMAP_GENERATE,
                                           NULL, NULL, FALSE);

      gimp_procedure_dialog_set_sensitive (GIMP_PROCEDURE_DIALOG (dialog),
                                           "mipmap-wrap",
                                           mipmaps == DDS_MIPMAP_GENERATE,
                                           NULL, NULL, FALSE);

      gimp_procedure_dialog_set_sensitive (GIMP_PROCEDURE_DIALOG (dialog),
                                           "gamma-correct",
                                           mipmaps == DDS_MIPMAP_GENERATE,
                                           NULL, NULL, FALSE);

      gimp_procedure_dialog_set_sensitive (GIMP_PROCEDURE_DIALOG (dialog),
                                           "srgb",
                                           ((mipmaps == DDS_MIPMAP_GENERATE) &&
                                            gamma_correct),
                                           NULL, NULL, FALSE);

      gimp_procedure_dialog_set_sensitive (GIMP_PROCEDURE_DIALOG (dialog),
                                           "gamma",
                                           ((mipmaps == DDS_MIPMAP_GENERATE) &&
                                            gamma_correct && ! srgb),
                                           NULL, NULL, FALSE);

      gimp_procedure_dialog_set_sensitive (GIMP_PROCEDURE_DIALOG (dialog),
                                           "preserve-alpha-coverage",
                                           mipmaps == DDS_MIPMAP_GENERATE,
                                           NULL, NULL, FALSE);

      gimp_procedure_dialog_set_sensitive (GIMP_PROCEDURE_DIALOG (dialog),
                                           "alpha-test-threshold",
                                           ((mipmaps == DDS_MIPMAP_GENERATE) &&
                                            preserve_alpha_coverage),
                                           NULL, NULL, FALSE);
    }
  else if (! strcmp (pspec->name, "transparent-color"))
    {
      GtkWidget *transparent_check;
      gboolean   transparent_color;

      g_object_get (config,
                    "transparent-color", &transparent_color,
                    NULL);

      transparent_check = gimp_procedure_dialog_get_widget (GIMP_PROCEDURE_DIALOG (dialog),
                                                            "transparent-color",
                                                            G_TYPE_NONE);

      if ((transparent_check != NULL) &&
          gtk_widget_get_sensitive (transparent_check))
        gimp_procedure_dialog_set_sensitive (GIMP_PROCEDURE_DIALOG (dialog),
                                             "transparent-index",
                                             transparent_color,
                                             NULL, NULL, FALSE);
    }
  else if (! strcmp (pspec->name, "gamma-correct"))
    {
      gboolean gamma_correct;
      gboolean srgb;

      g_object_get (config,
                    "gamma-correct", &gamma_correct,
                    "srgb",          &srgb,
                    NULL);

      gimp_procedure_dialog_set_sensitive (GIMP_PROCEDURE_DIALOG (dialog),
                                           "srgb", gamma_correct,
                                           NULL, NULL, FALSE);

      gimp_procedure_dialog_set_sensitive (GIMP_PROCEDURE_DIALOG (dialog),
                                           "gamma",
                                           (gamma_correct && ! srgb),
                                           NULL, NULL, FALSE);
    }
  else if (! strcmp (pspec->name, "srgb"))
    {
      gboolean gamma_correct;
      gboolean srgb;

      g_object_get (config,
                    "gamma-correct", &gamma_correct,
                    "srgb",          &srgb,
                    NULL);

      gimp_procedure_dialog_set_sensitive (GIMP_PROCEDURE_DIALOG (dialog),
                                           "gamma",
                                           (gamma_correct && ! srgb),
                                           NULL, NULL, FALSE);
    }
  else if (! strcmp (pspec->name, "preserve-alpha-coverage"))
    {
      gboolean preserve_alpha_coverage;

      g_object_get (config,
                    "preserve-alpha-coverage", &preserve_alpha_coverage,
                    NULL);

      gimp_procedure_dialog_set_sensitive (GIMP_PROCEDURE_DIALOG (dialog),
                                           "alpha-test-threshold",
                                           preserve_alpha_coverage,
                                           NULL, NULL, FALSE);
    }
}


static gboolean
save_dialog (GimpImage           *image,
             GimpDrawable        *drawable,
             GimpProcedure       *procedure,
             GimpProcedureConfig *config)
{
  GtkWidget         *dialog;
  GParamSpec        *cspec;
  GimpChoice        *choice;
  GimpImageBaseType  base_type;
  gboolean           run;

  base_type = gimp_image_get_base_type (image);

  if (is_cubemap || is_volume || is_array)
    g_object_set (config,
                  "save-type", "layer",
                  NULL);

  dialog = gimp_export_procedure_dialog_new (GIMP_EXPORT_PROCEDURE (procedure),
                                             GIMP_PROCEDURE_CONFIG (config),
                                             image);

  gtk_window_set_resizable (GTK_WINDOW (dialog), FALSE);

  gimp_procedure_dialog_get_widget (GIMP_PROCEDURE_DIALOG (dialog),
                                    "transparent-color",
                                    G_TYPE_NONE);
  gimp_procedure_dialog_set_sensitive (GIMP_PROCEDURE_DIALOG (dialog),
                                       "transparent-color",
                                       base_type == GIMP_INDEXED,
                                       NULL, NULL, FALSE);

  gimp_procedure_dialog_fill_frame (GIMP_PROCEDURE_DIALOG (dialog),
                                    "transparency-frame",
                                    "transparent-color", FALSE,
                                    "transparent-index");

  gimp_procedure_dialog_get_label (GIMP_PROCEDURE_DIALOG (dialog),
                                   "mipmap-options-label",
                                   _("Mipmap Options"),
                                   FALSE, FALSE);

  gimp_procedure_dialog_fill_box (GIMP_PROCEDURE_DIALOG (dialog),
                                  "mipmap-options-box",
                                  "mipmap-filter", "mipmap-wrap",
                                  "gamma-correct", "srgb", "gamma",
                                  "preserve-alpha-coverage",
                                  "alpha-test-threshold", NULL);

  gimp_procedure_dialog_fill_frame (GIMP_PROCEDURE_DIALOG (dialog),
                                    "mipmap-options-frame",
                                    "mipmap-options-label", FALSE,
                                    "mipmap-options-box");

  gimp_procedure_dialog_get_widget (GIMP_PROCEDURE_DIALOG (dialog),
                                    "save-type", G_TYPE_NONE);
  cspec  = g_object_class_find_property (G_OBJECT_GET_CLASS (config), "save-type");
  choice = gimp_param_spec_choice_get_choice (cspec);
  gimp_choice_set_sensitive (choice, "cube",   is_cubemap);
  gimp_choice_set_sensitive (choice, "volume", is_volume);
  gimp_choice_set_sensitive (choice, "array",  is_array);

  gimp_procedure_dialog_get_widget (GIMP_PROCEDURE_DIALOG (dialog),
                                    "mipmaps", G_TYPE_NONE);
  cspec  = g_object_class_find_property (G_OBJECT_GET_CLASS (config), "mipmaps");
  choice = gimp_param_spec_choice_get_choice (cspec);
  gimp_choice_set_sensitive (choice, "existing",
                             ! (is_volume || is_cubemap) && is_mipmap_chain_valid);

  gimp_procedure_dialog_fill (GIMP_PROCEDURE_DIALOG (dialog),
                              "compression-format", "perceptual-metric",
                              "format", "save-type", "flip-image",
                              "mipmaps", "transparency-frame",
                              "mipmap-options-frame", NULL);

  config_notify (GIMP_PROCEDURE_CONFIG (config),
                 g_object_class_find_property (G_OBJECT_GET_CLASS (config),
                                               "compression-format"),
                 GIMP_PROCEDURE_DIALOG (dialog));

  config_notify (GIMP_PROCEDURE_CONFIG (config),
                 g_object_class_find_property (G_OBJECT_GET_CLASS (config),
                                               "mipmaps"),
                 GIMP_PROCEDURE_DIALOG (dialog));

  config_notify (GIMP_PROCEDURE_CONFIG (config),
                 g_object_class_find_property (G_OBJECT_GET_CLASS (config),
                                               "save-type"),
                 GIMP_PROCEDURE_DIALOG (dialog));

  config_notify (GIMP_PROCEDURE_CONFIG (config),
                 g_object_class_find_property (G_OBJECT_GET_CLASS (config),
                                               "transparent-color"),
                 GIMP_PROCEDURE_DIALOG (dialog));

  g_signal_connect (GIMP_PROCEDURE_CONFIG (config), "notify",
                    G_CALLBACK (config_notify),
                    GIMP_PROCEDURE_DIALOG (dialog));

  gtk_widget_set_visible (dialog, TRUE);

  run = gimp_procedure_dialog_run (GIMP_PROCEDURE_DIALOG (dialog));

  g_signal_handlers_disconnect_by_func (GIMP_PROCEDURE_CONFIG (config),
                                        config_notify,
                                        GIMP_PROCEDURE_DIALOG (dialog));

  gtk_widget_destroy (dialog);

  return run;
}

static const gchar *
check_comp_format (guint32 format)
{
  switch (format)
    {
    case DDS_COMPRESS_BC1:
      return "bc1";

    case DDS_COMPRESS_BC2:
      return "bc2";

    case DDS_COMPRESS_BC3:
      return "bc3";

    case DDS_COMPRESS_BC4:
      return "bc4";

    case DDS_COMPRESS_BC5:
      return "bc5";

    case DDS_COMPRESS_BC6H:
    case DDS_COMPRESS_BC7:
      return "bc7";

    default:
      return "none";
    }
}

/* --- end plug-ins/field-io/file-dds/ddswrite.c --- */

/* --- begin plug-ins/field-io/file-dds/dxt.c --- */
/*
 * DDS AmmoOS Image plugin
 *
 * Copyright (C) 2004-2012 Shawn Kirst <skirst@gmail.com>,
 * with parts (C) 2003 Arne Reuter <homepage@arnereuter.de> where specified.
 *
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public
 * License as published by the Free Software Foundation; either
 * version 2 of the License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; see the file COPYING.  If not, write to
 * the Free Software Foundation, 51 Franklin Street, Fifth Floor
 * Boston, MA 02110-1301, USA.
 */

/*
 * Parts of this code have been generously released in the public domain
 * by Fabian 'ryg' Giesen.  The original code can be found (at the time
 * of writing) here:  http://mollyrocket.com/forums/viewtopic.php?t=392
 *
 * For more information about this code, see the README.dxt file that
 * came with the source.
 */

#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <glib.h>

#include <libgimp/ammoos.h>

#include "bc7.h"
#include "dds.h"
#include "dxt.h"
#include "endian_rw.h"
#include "imath.h"
#include "mipmap.h"
#include "misc.h"
#include "vec.h"

#include "bc7enc_rdo/bc7enc.h"

#include "dxt_tables.h"

#define SWAP(a, b)  do { typeof(a) t; t = a; a = b; b = t; } while(0)

/* SIMD constants */
static const vec4_t V4ZERO      = VEC4_CONST1(0.0f);
static const vec4_t V4ONE       = VEC4_CONST1(1.0f);
static const vec4_t V4HALF      = VEC4_CONST1(0.5f);
static const vec4_t V4ONETHIRD  = VEC4_CONST3(1.0f / 3.0f, 1.0f / 3.0f, 1.0f / 3.0f);
static const vec4_t V4TWOTHIRDS = VEC4_CONST3(2.0f / 3.0f, 2.0f / 3.0f, 2.0f / 3.0f);
static const vec4_t V4GRID      = VEC4_CONST3(31.0f, 63.0f, 31.0f);
static const vec4_t V4GRIDRCP   = VEC4_CONST3(1.0f / 31.0f, 1.0f / 63.0f, 1.0f / 31.0f);
static const vec4_t V4EPSILON   = VEC4_CONST1(1e-04f);

typedef struct
{
  unsigned int single;
  unsigned int alphamask;
  vec4_t points[16];
  vec4_t palette[4];
  vec4_t max;
  vec4_t min;
  vec4_t metric;
} dxtblock_t;

/* extract 4x4 BGRA block */
static void
extract_block (const unsigned char *src,
               int                  x,
               int                  y,
               int                  w,
               int                  h,
               unsigned char       *block)
{
  int i, j;
  int bw = MIN(w - x, 4);
  int bh = MIN(h - y, 4);
  int bx, by;
  const int rem[] =
  {
    0, 0, 0, 0,
    0, 1, 0, 1,
    0, 1, 2, 0,
    0, 1, 2, 3
  };

  for (i = 0; i < 4; ++i)
    {
      by = rem[(bh - 1) * 4 + i] + y;
      for (j = 0; j < 4; ++j)
        {
          bx = rem[(bw - 1) * 4 + j] + x;
          block[(i * 4 * 4) + (j * 4) + 0] =
            src[(by * (w * 4)) + (bx * 4) + 0];
          block[(i * 4 * 4) + (j * 4) + 1] =
            src[(by * (w * 4)) + (bx * 4) + 1];
          block[(i * 4 * 4) + (j * 4) + 2] =
            src[(by * (w * 4)) + (bx * 4) + 2];
          block[(i * 4 * 4) + (j * 4) + 3] =
            src[(by * (w * 4)) + (bx * 4) + 3];
        }
    }
}

#if 0
/* Currently unused, hidden to avoid compilation warnings. */

/* pack BGR8 to RGB565 */
static inline unsigned short
pack_rgb565 (const unsigned char *c)
{
  return (mul8bit(c[2], 31) << 11) |
         (mul8bit(c[1], 63) <<  5) |
         (mul8bit(c[0], 31)      );
}
#endif

/* unpack RGB565 to BGR */
static void
unpack_rgb565 (unsigned char  *dst,
               unsigned short  v)
{
  int r = (v >> 11) & 0x1f;
  int g = (v >>  5) & 0x3f;
  int b = (v      ) & 0x1f;

  dst[0] = (b << 3) | (b >> 2);
  dst[1] = (g << 2) | (g >> 4);
  dst[2] = (r << 3) | (r >> 2);
}

/* linear interpolation at 1/3 point between a and b */
static void
lerp_rgb13 (unsigned char *dst,
            unsigned char *a,
            unsigned char *b)
{
#if 0
  dst[0] = blerp(a[0], b[0], 0x55);
  dst[1] = blerp(a[1], b[1], 0x55);
  dst[2] = blerp(a[2], b[2], 0x55);
#else
  /*
   * according to the S3TC/DX10 specs, this is the correct way to do the
   * interpolation (with no rounding bias)
   *
   * dst = (2 * a + b) / 3;
   */
  dst[0] = (2 * a[0] + b[0]) / 3;
  dst[1] = (2 * a[1] + b[1]) / 3;
  dst[2] = (2 * a[2] + b[2]) / 3;
#endif
}

static void
vec4_endpoints_to_565 (int          *start,
                       int          *end,
                       const vec4_t  a,
                       const vec4_t  b)
{
  int c[8] __attribute__((aligned(16)));
  vec4_t ta = a * V4GRID + V4HALF;
  vec4_t tb = b * V4GRID + V4HALF;

#ifdef USE_SSE
# ifdef __SSE2__
  const __m128i C565 = _mm_setr_epi16(31, 63, 31, 0, 31, 63, 31, 0);
  __m128i ia = _mm_cvttps_epi32(ta);
  __m128i ib = _mm_cvttps_epi32(tb);
  __m128i zero = _mm_setzero_si128();
  __m128i words = _mm_packs_epi32(ia, ib);
  words = _mm_min_epi16(C565, _mm_max_epi16(zero, words));
  *((__m128i *)&c[0]) = _mm_unpacklo_epi16(words, zero);
  *((__m128i *)&c[4]) = _mm_unpackhi_epi16(words, zero);
# else
  const __m64 C565 = _mm_setr_pi16(31, 63, 31, 0);
  __m64 lo, hi, c0, c1;
  __m64 zero = _mm_setzero_si64();
  lo = _mm_cvttps_pi32(ta);
  hi = _mm_cvttps_pi32(_mm_movehl_ps(ta, ta));
  c0 = _mm_packs_pi32(lo, hi);
  lo = _mm_cvttps_pi32(tb);
  hi = _mm_cvttps_pi32(_mm_movehl_ps(tb, tb));
  c1 = _mm_packs_pi32(lo, hi);
  c0 = _mm_min_pi16(C565, _mm_max_pi16(zero, c0));
  c1 = _mm_min_pi16(C565, _mm_max_pi16(zero, c1));
  *((__m64 *)&c[0]) = _mm_unpacklo_pi16(c0, zero);
  *((__m64 *)&c[2]) = _mm_unpackhi_pi16(c0, zero);
  *((__m64 *)&c[4]) = _mm_unpacklo_pi16(c1, zero);
  *((__m64 *)&c[6]) = _mm_unpackhi_pi16(c1, zero);
  _mm_empty();
# endif
#else
  c[0] = (int)ta[0]; c[4] = (int)tb[0];
  c[1] = (int)ta[1]; c[5] = (int)tb[1];
  c[2] = (int)ta[2]; c[6] = (int)tb[2];
  c[0] = MIN(31, MAX(0, c[0]));
  c[1] = MIN(63, MAX(0, c[1]));
  c[2] = MIN(31, MAX(0, c[2]));
  c[4] = MIN(31, MAX(0, c[4]));
  c[5] = MIN(63, MAX(0, c[5]));
  c[6] = MIN(31, MAX(0, c[6]));
#endif

  *start = ((c[2] << 11) | (c[1] << 5) | c[0]);
  *end   = ((c[6] << 11) | (c[5] << 5) | c[4]);
}

static void
dxtblock_init (dxtblock_t          *dxtb,
               const unsigned char *block,
               int                  flags)
{
  int i, c0, c;
  int bc1 = (flags & DXT_BC1);
  float x, y, z;
  vec4_t min, max, center, t, cov, inset;

  dxtb->single = 1;
  dxtb->alphamask = 0;

  if(flags & DXT_PERCEPTUAL)
    /* ITU-R BT.709 luma coefficients */
    dxtb->metric = vec4_set(0.2126f, 0.7152f, 0.0722f, 0.0f);
  else
    dxtb->metric = vec4_set(1.0f, 1.0f, 1.0f, 0.0f);

  c0 = GETL24(block);

  for (i = 0; i < 16; ++i)
    {
      if (bc1 && (block[4 * i + 3] < 128))
        dxtb->alphamask |= (3 << (2 * i));

      x = (float)block[4 * i + 0] / 255.0f;
      y = (float)block[4 * i + 1] / 255.0f;
      z = (float)block[4 * i + 2] / 255.0f;

      dxtb->points[i] = vec4_set(x, y, z, 0);

      c = GETL24(&block[4 * i]);
      dxtb->single = dxtb->single && (c == c0);
    }

  // no need to continue if this is a single color block
  if (dxtb->single)
    return;

  min = vec4_set1(1.0f);
  max = vec4_zero();

  // get bounding box extents
  for (i = 0; i < 16; ++i)
    {
      min = vec4_min(min, dxtb->points[i]);
      max = vec4_max(max, dxtb->points[i]);
    }

  // select diagonal
  center = (max + min) * V4HALF;
  cov = vec4_zero();
  for (i = 0; i < 16; ++i)
    {
      t = dxtb->points[i] - center;
      cov += t * vec4_splatz(t);
    }

#ifdef USE_SSE
  {
    __m128 mask, tmp;
    // get mask
    mask = _mm_cmplt_ps(cov, _mm_setzero_ps());
    // clear high bits (z, w)
    mask = _mm_movelh_ps(mask, _mm_setzero_ps());
    // mask and combine
    tmp = _mm_or_ps(_mm_and_ps(mask, min), _mm_andnot_ps(mask, max));
    min = _mm_or_ps(_mm_and_ps(mask, max), _mm_andnot_ps(mask, min));
    max = tmp;
  }
#else
  {
    float x0, x1, y0, y1;
    x0 = max[0];
    y0 = max[1];
    x1 = min[0];
    y1 = min[1];

    if (cov[0] < 0) SWAP(x0, x1);
    if (cov[1] < 0) SWAP(y0, y1);

    max[0] = x0;
    max[1] = y0;
    min[0] = x1;
    min[1] = y1;
  }
#endif

  // inset bounding box and clamp to [0,1]
  inset = (max - min) * vec4_set1(1.0f / 16.0f) - vec4_set1((8.0f / 255.0f) / 16.0f);
  max = vec4_min(V4ONE, vec4_max(V4ZERO, max - inset));
  min = vec4_min(V4ONE, vec4_max(V4ZERO, min + inset));

  // clamp to color space and save
  dxtb->max = vec4_trunc(V4GRID * max + V4HALF) * V4GRIDRCP;
  dxtb->min = vec4_trunc(V4GRID * min + V4HALF) * V4GRIDRCP;
}

static void
construct_palette3 (dxtblock_t *dxtb)
{
  dxtb->palette[0] = dxtb->max;
  dxtb->palette[1] = dxtb->min;
  dxtb->palette[2] = (dxtb->max * V4HALF) + (dxtb->min * V4HALF);
  dxtb->palette[3] = vec4_zero();
}

static void
construct_palette4 (dxtblock_t *dxtb)
{
  dxtb->palette[0] = dxtb->max;
  dxtb->palette[1] = dxtb->min;
  dxtb->palette[2] = (dxtb->max * V4TWOTHIRDS) + (dxtb->min * V4ONETHIRD );
  dxtb->palette[3] = (dxtb->max * V4ONETHIRD ) + (dxtb->min * V4TWOTHIRDS);
}

/*
 * from nvidia-texture-tools; see LICENSE.nvtt for copyright information
 */
static void
optimize_endpoints3 (dxtblock_t   *dxtb,
                     unsigned int  indices,
                     vec4_t       *max,
                     vec4_t       *min)
{
  float alpha, beta;
  vec4_t alpha2_sum, alphax_sum;
  vec4_t beta2_sum, betax_sum;
  vec4_t alphabeta_sum, a, b, factor;
  int i, bits;

  alpha2_sum = beta2_sum = alphabeta_sum = vec4_zero();
  alphax_sum = vec4_zero();
  betax_sum = vec4_zero();

  for (i = 0; i < 16; ++i)
    {
      bits = indices >> (2 * i);

      // skip alpha pixels
      if ((bits & 3) == 3)
        continue;

      beta = (float)(bits & 1);
      if (bits & 2)
        beta = 0.5f;
      alpha = 1.0f - beta;

      a = vec4_set1(alpha);
      b = vec4_set1(beta);
      alpha2_sum += a * a;
      beta2_sum += b * b;
      alphabeta_sum += a * b;
      alphax_sum += dxtb->points[i] * a;
      betax_sum  += dxtb->points[i] * b;
    }

  factor = alpha2_sum * beta2_sum - alphabeta_sum * alphabeta_sum;
  if (vec4_cmplt(factor, V4EPSILON))
    return;
  factor = vec4_rcp(factor);

  a = (alphax_sum * beta2_sum  - betax_sum  * alphabeta_sum) * factor;
  b = (betax_sum  * alpha2_sum - alphax_sum * alphabeta_sum) * factor;

  // clamp to the color space
  a = vec4_min(V4ONE, vec4_max(V4ZERO, a));
  b = vec4_min(V4ONE, vec4_max(V4ZERO, b));
  a = vec4_trunc(V4GRID * a + V4HALF) * V4GRIDRCP;
  b = vec4_trunc(V4GRID * b + V4HALF) * V4GRIDRCP;

  *max = a;
  *min = b;
}

/*
 * from nvidia-texture-tools; see LICENSE.nvtt for copyright information
 */
static void
optimize_endpoints4 (dxtblock_t   *dxtb,
                     unsigned int  indices,
                     vec4_t       *max,
                     vec4_t       *min)
{
  float alpha, beta;
  vec4_t alpha2_sum, alphax_sum;
  vec4_t beta2_sum, betax_sum;
  vec4_t alphabeta_sum, a, b, factor;
  int i, bits;

  alpha2_sum = beta2_sum = alphabeta_sum = vec4_zero();
  alphax_sum = vec4_zero();
  betax_sum = vec4_zero();

  for (i = 0; i < 16; ++i)
    {
      bits = indices >> (2 * i);

      beta = (float)(bits & 1);
      if (bits & 2)
        beta = (1.0f + beta) / 3.0f;
      alpha = 1.0f - beta;

      a = vec4_set1(alpha);
      b = vec4_set1(beta);
      alpha2_sum += a * a;
      beta2_sum += b * b;
      alphabeta_sum += a * b;
      alphax_sum += dxtb->points[i] * a;
      betax_sum  += dxtb->points[i] * b;
    }

  factor = alpha2_sum * beta2_sum - alphabeta_sum * alphabeta_sum;
  if (vec4_cmplt(factor, V4EPSILON))
    return;
  factor = vec4_rcp(factor);

  a = (alphax_sum * beta2_sum  - betax_sum  * alphabeta_sum) * factor;
  b = (betax_sum  * alpha2_sum - alphax_sum * alphabeta_sum) * factor;

  // clamp to the color space
  a = vec4_min(V4ONE, vec4_max(V4ZERO, a));
  b = vec4_min(V4ONE, vec4_max(V4ZERO, b));
  a = vec4_trunc(V4GRID * a + V4HALF) * V4GRIDRCP;
  b = vec4_trunc(V4GRID * b + V4HALF) * V4GRIDRCP;

  *max = a;
  *min = b;
}

static unsigned int
match_colors3 (dxtblock_t *dxtb)
{
  int i, idx;
  unsigned int indices = 0;
  vec4_t t0, t1, t2;
#ifdef USE_SSE
  vec4_t d, bits, zero = _mm_setzero_ps();
  int mask;
#else
  float d0, d1, d2;
#endif

  // match each point to the closest color
  for (i = 0; i < 16; ++i)
    {
      // skip alpha pixels
      if (((dxtb->alphamask >> (2 * i)) & 3) == 3)
        {
          indices |= (3 << (2 * i));
          continue;
        }

      t0 = (dxtb->points[i] - dxtb->palette[0]) * dxtb->metric;
      t1 = (dxtb->points[i] - dxtb->palette[1]) * dxtb->metric;
      t2 = (dxtb->points[i] - dxtb->palette[2]) * dxtb->metric;

#ifdef USE_SSE
      _MM_TRANSPOSE4_PS(t0, t1, t2, zero);
      d = t0 * t0 + t1 * t1 + t2 * t2;
      bits = _mm_cmplt_ps(_mm_shuffle_ps(d, d, _MM_SHUFFLE(3, 1, 0, 0)),
                          _mm_shuffle_ps(d, d, _MM_SHUFFLE(3, 2, 2, 1)));
      mask = _mm_movemask_ps(bits);
      if((mask & 3) == 3) idx = 0;
      else if(mask & 4)   idx = 1;
      else                idx = 2;
#else
      d0 = vec4_dot(t0, t0);
      d1 = vec4_dot(t1, t1);
      d2 = vec4_dot(t2, t2);

      if ((d0 < d1) && (d0 < d2))
        idx = 0;
      else if (d1 < d2)
        idx = 1;
      else
        idx = 2;
#endif

      indices |= (idx << (2 * i));
    }

   return indices;
}

static unsigned int
match_colors4 (dxtblock_t *dxtb)
{
  int i;
  unsigned int idx, indices = 0;
  unsigned int b0, b1, b2, b3, b4;
  unsigned int x0, x1, x2;
  vec4_t t0, t1, t2, t3;
#ifdef USE_SSE
  vec4_t d;
#else
  float d[4];
#endif

  // match each point to the closest color
  for (i = 0; i < 16; ++i)
    {
      t0 = (dxtb->points[i] - dxtb->palette[0]) * dxtb->metric;
      t1 = (dxtb->points[i] - dxtb->palette[1]) * dxtb->metric;
      t2 = (dxtb->points[i] - dxtb->palette[2]) * dxtb->metric;
      t3 = (dxtb->points[i] - dxtb->palette[3]) * dxtb->metric;

#ifdef USE_SSE
      _MM_TRANSPOSE4_PS(t0, t1, t2, t3);
      d = t0 * t0 + t1 * t1 + t2 * t2;
#else
      d[0] = vec4_dot(t0, t0);
      d[1] = vec4_dot(t1, t1);
      d[2] = vec4_dot(t2, t2);
      d[3] = vec4_dot(t3, t3);
#endif

      b0 = d[0] > d[3];
      b1 = d[1] > d[2];
      b2 = d[0] > d[2];
      b3 = d[1] > d[3];
      b4 = d[2] > d[3];

      x0 = b1 & b2;
      x1 = b0 & b3;
      x2 = b0 & b4;

      idx = x2 | ((x0 | x1) << 1);

      indices |= (idx << (2 * i));
    }

   return indices;
}

static float
compute_error3 (dxtblock_t   *dxtb,
                unsigned int  indices)
{
  int i, idx;
  float error = 0;
  vec4_t t;

  // compute error
  for (i = 0; i < 16; ++i)
    {
      idx = (indices >> (2 * i)) & 3;
      // skip alpha pixels
      if(idx == 3)
        continue;
      t = (dxtb->points[i] - dxtb->palette[idx]) * dxtb->metric;
      error += vec4_dot(t, t);
    }

  return error;
}

static float
compute_error4 (dxtblock_t   *dxtb,
                unsigned int  indices)
{
  int i, idx;
  float error = 0;

#ifdef USE_SSE
  vec4_t a0, a1, a2, a3;
  vec4_t b0, b1, b2, b3;
  vec4_t d;

  for (i = 0; i < 4; ++i)
    {
      idx = indices >> (8 * i);
      a0 = dxtb->points[4 * i + 0];
      a1 = dxtb->points[4 * i + 1];
      a2 = dxtb->points[4 * i + 2];
      a3 = dxtb->points[4 * i + 3];
      b0 = dxtb->palette[(idx     ) & 3];
      b1 = dxtb->palette[(idx >> 2) & 3];
      b2 = dxtb->palette[(idx >> 4) & 3];
      b3 = dxtb->palette[(idx >> 6) & 3];
      a0 = (a0 - b0) * dxtb->metric;
      a1 = (a1 - b1) * dxtb->metric;
      a2 = (a2 - b2) * dxtb->metric;
      a3 = (a3 - b3) * dxtb->metric;
      _MM_TRANSPOSE4_PS(a0, a1, a2, a3);
      d = a0 * a0 + a1 * a1 + a2 * a2;
      error += vec4_accum(d);
    }
#else
  vec4_t t;

  // compute error
  for (i = 0; i < 16; ++i)
    {
      idx = (indices >> (2 * i)) & 3;
      t = (dxtb->points[i] - dxtb->palette[idx]) * dxtb->metric;
      error += vec4_dot(t, t);
    }
#endif

  return error;
}

static unsigned int
compress3 (dxtblock_t *dxtb)
{
  const int MAX_ITERATIONS = 8;
  int i;
  unsigned int indices, bestindices;
  float error, besterror = FLT_MAX;
  vec4_t oldmax, oldmin;

  construct_palette3(dxtb);

  indices = match_colors3(dxtb);
  bestindices = indices;

  for (i = 0; i < MAX_ITERATIONS; ++i)
    {
      oldmax = dxtb->max;
      oldmin = dxtb->min;

      optimize_endpoints3(dxtb, indices, &dxtb->max, &dxtb->min);
      construct_palette3(dxtb);
      indices = match_colors3(dxtb);
      error = compute_error3(dxtb, indices);

      if (error < besterror)
        {
          besterror = error;
          bestindices = indices;
        }
      else
        {
          dxtb->max = oldmax;
          dxtb->min = oldmin;
          break;
        }
    }

  return bestindices;
}

static unsigned int
compress4 (dxtblock_t *dxtb)
{
  const int MAX_ITERATIONS = 8;
  int i;
  unsigned int indices, bestindices;
  float error, besterror = FLT_MAX;
  vec4_t oldmax, oldmin;

  construct_palette4(dxtb);

  indices = match_colors4(dxtb);
  bestindices = indices;

  for (i = 0; i < MAX_ITERATIONS; ++i)
    {
      oldmax = dxtb->max;
      oldmin = dxtb->min;

      optimize_endpoints4(dxtb, indices, &dxtb->max, &dxtb->min);
      construct_palette4(dxtb);
      indices = match_colors4(dxtb);
      error = compute_error4(dxtb, indices);

      if (error < besterror)
        {
          besterror = error;
          bestindices = indices;
        }
      else
        {
          dxtb->max = oldmax;
          dxtb->min = oldmin;
          break;
        }
    }

  return bestindices;
}

static void
encode_color_block (unsigned char *dst,
                    unsigned char *block,
                    int            flags)
{
  dxtblock_t dxtb;
  int max16, min16;
  unsigned int indices, mask;

  dxtblock_init(&dxtb, block, flags);

  if (dxtb.single) // single color block
    {
      max16 = (omatch5[block[2]][0] << 11) |
              (omatch6[block[1]][0] <<  5) |
              (omatch5[block[0]][0]      );
      min16 = (omatch5[block[2]][1] << 11) |
              (omatch6[block[1]][1] <<  5) |
              (omatch5[block[0]][1]      );

      indices = 0xaaaaaaaa; // 101010...

      if ((flags & DXT_BC1) && dxtb.alphamask)
        {
          // DXT1 compression, non-opaque block.  Add alpha indices.
          indices |= dxtb.alphamask;
          if (max16 > min16)
            SWAP(max16, min16);
        }
      else if (max16 < min16)
        {
          SWAP(max16, min16);
          indices ^= 0x55555555; // 010101...
        }
    }
  else if ((flags & DXT_BC1) && dxtb.alphamask) // DXT1 compression, non-opaque block
    {
      indices = compress3(&dxtb);

      vec4_endpoints_to_565(&max16, &min16, dxtb.max, dxtb.min);

      if (max16 > min16)
        {
          SWAP(max16, min16);
          // remap indices 0 -> 1, 1 -> 0
          mask = indices & 0xaaaaaaaa;
          mask = mask | (mask >> 1);
          indices = (indices & mask) | ((indices ^ 0x55555555) & ~mask);
        }
    }
  else
    {
      indices = compress4(&dxtb);

      vec4_endpoints_to_565(&max16, &min16, dxtb.max, dxtb.min);

      if (max16 < min16)
        {
          SWAP(max16, min16);
          indices ^= 0x55555555; // 010101...
        }
    }

  PUTL16(dst + 0, max16);
  PUTL16(dst + 2, min16);
  PUTL32(dst + 4, indices);
}

/* write DXT3 alpha block */
static void
encode_alpha_block_BC2 (unsigned char       *dst,
                        const unsigned char *block)
{
  int i, a1, a2;

  block += 3;

  for (i = 0; i < 8; ++i)
    {
      a1 = mul8bit(block[8 * i + 0], 0x0f);
      a2 = mul8bit(block[8 * i + 4], 0x0f);
      *dst++ = (a2 << 4) | a1;
    }
}

/* Write DXT5 alpha block */
static void
encode_alpha_block_BC3 (unsigned char       *dst,
                        const unsigned char *block,
                        const int            offset)
{
  int i, v, mn, mx;
  int dist, bias, dist2, dist4, bits, mask;
  int a, idx, t;

  block += offset;
  block += 3;

  /* find min/max alpha pair */
  mn = mx = block[0];
  for (i = 0; i < 16; ++i)
    {
      v = block[4 * i];
      if(v > mx) mx = v;
      if(v < mn) mn = v;
    }

  /* encode them */
  *dst++ = mx;
  *dst++ = mn;

  /*
   * determine bias and emit indices
   * given the choice of mx/mn, these indices are optimal:
   * http://fgiesen.wordpress.com/2009/12/15/dxt5-alpha-block-index-determination/
   */
  dist = mx - mn;
  dist4 = dist * 4;
  dist2 = dist * 2;
  bias = (dist < 8) ? (dist - 1) : (dist / 2 + 2);
  bias -= mn * 7;
  bits = 0;
  mask = 0;

  for (i = 0; i < 16; ++i)
    {
      a = block[4 * i] * 7 + bias;

      /* select index. this is a "linear scale" lerp factor between 0
         (val=min) and 7 (val=max). */
      t = (a >= dist4) ? -1 : 0; idx =  t & 4; a -= dist4 & t;
      t = (a >= dist2) ? -1 : 0; idx += t & 2; a -= dist2 & t;
      idx += (a >= dist);

      /* turn linear scale into DXT index (0/1 are extremal pts) */
      idx = -idx & 7;
      idx ^= (2 > idx);

      /* write index */
      mask |= idx << bits;
      if ((bits += 3) >= 8)
        {
          *dst++ = mask;
          mask >>= 8;
          bits -= 8;
        }
    }
}

#define BLOCK_COUNT(w, h)          ((((h) + 3) >> 2) * (((w) + 3) >> 2))
#define BLOCK_OFFSET(x, y, w, bs)  (((y) >> 2) * ((bs) * (((w) + 3) >> 2)) + ((bs) * ((x) >> 2)))

static void
compress_BC1 (unsigned char       *dst,
              const unsigned char *src,
              int                  w,
              int                  h,
              int                  flags)
{
  const unsigned int block_count = BLOCK_COUNT(w, h);
  unsigned int i;
  unsigned char block[64], *p;
  int x, y;

#ifdef _OPENMP
#pragma omp parallel for schedule(dynamic, 256) private(block, p, x, y)
#endif
  for (i = 0; i < block_count; ++i)
    {
      x = (i % ((w + 3) >> 2)) << 2;
      y = (i / ((w + 3) >> 2)) << 2;
      p = dst + BLOCK_OFFSET(x, y, w, 8);
      extract_block (src, x, y, w, h, block);
      encode_color_block(p, block, DXT_BC1 | flags);
    }
}

static void
compress_BC2 (unsigned char       *dst,
              const unsigned char *src,
              int                  w,
              int                  h,
              int                  flags)
{
  const unsigned int block_count = BLOCK_COUNT(w, h);
  unsigned int i;
  unsigned char block[64], *p;
  int x, y;

#ifdef _OPENMP
#pragma omp parallel for schedule(dynamic, 256) private(block, p, x, y)
#endif
  for (i = 0; i < block_count; ++i)
    {
      x = (i % ((w + 3) >> 2)) << 2;
      y = (i / ((w + 3) >> 2)) << 2;
      p = dst + BLOCK_OFFSET(x, y, w, 16);
      extract_block (src, x, y, w, h, block);
      encode_alpha_block_BC2(p, block);
      encode_color_block(p + 8, block, DXT_BC2 | flags);
    }
}

static void
compress_BC3 (unsigned char       *dst,
              const unsigned char *src,
              int                  w,
              int                  h,
              int                  flags)
{
  const unsigned int block_count = BLOCK_COUNT(w, h);
  unsigned int i;
  unsigned char block[64], *p;
  int x, y;

#ifdef _OPENMP
#pragma omp parallel for schedule(dynamic, 256) private(block, p, x, y)
#endif
  for (i = 0; i < block_count; ++i)
    {
      x = (i % ((w + 3) >> 2)) << 2;
      y = (i / ((w + 3) >> 2)) << 2;
      p = dst + BLOCK_OFFSET(x, y, w, 16);
      extract_block (src, x, y, w, h, block);
      encode_alpha_block_BC3(p, block, 0);
      encode_color_block(p + 8, block, DXT_BC3 | flags);
    }
}

static void
compress_BC4 (unsigned char       *dst,
              const unsigned char *src,
              int                  w,
              int                  h)
{
  const unsigned int block_count = BLOCK_COUNT(w, h);
  unsigned int i;
  unsigned char block[64], *p;
  int x, y;

#ifdef _OPENMP
#pragma omp parallel for schedule(dynamic, 256) private(block, p, x, y)
#endif
  for (i = 0; i < block_count; ++i)
    {
      x = (i % ((w + 3) >> 2)) << 2;
      y = (i / ((w + 3) >> 2)) << 2;
      p = dst + BLOCK_OFFSET(x, y, w, 8);
      extract_block (src, x, y, w, h, block);
      encode_alpha_block_BC3(p, block, -1);
    }
}

static void
compress_BC5 (unsigned char       *dst,
              const unsigned char *src,
              int                  w,
              int                  h)
{
  const unsigned int block_count = BLOCK_COUNT(w, h);
  unsigned int i;
  unsigned char block[64], *p;
  int x, y;

#ifdef _OPENMP
#pragma omp parallel for schedule(dynamic, 256) private(block, p, x, y)
#endif
  for (i = 0; i < block_count; ++i)
    {
      x = (i % ((w + 3) >> 2)) << 2;
      y = (i / ((w + 3) >> 2)) << 2;
      p = dst + BLOCK_OFFSET(x, y, w, 16);
      extract_block (src, x, y, w, h, block);
      /* Pixels are ordered as BGRA (see write_layer)
       * First we encode red  -1+3: channel 2;
       * then we encode green -2+3: channel 1.
       */
      encode_alpha_block_BC3(p, block, -1);
      encode_alpha_block_BC3(p + 8, block, -2);
    }
}

static void
compress_BC7 (guchar                       *dst,
              const guchar                 *src,
              gint                          w,
              gint                          h,
              bc7enc_compress_block_params *params)
{
  const guint block_count = BLOCK_COUNT (w, h);
  guchar      block[64]   = { 0 };
  guint       i;
  guchar     *p;
  gint        x;
  gint        y;

#ifdef _OPENMP
#pragma omp parallel for schedule(dynamic, 256) private(block, p, x, y)
#endif
  for (i = 0; i < block_count; ++i)
    {
      x = (i % ((w + 3) >> 2)) << 2;
      y = (i / ((w + 3) >> 2)) << 2;
      p = dst + BLOCK_OFFSET (x, y, w, 16);

      extract_block (src, x, y, w, h, block);
      bc7enc_compress_block (p, block, params);
    }
}

static void
compress_YCoCg (unsigned char       *dst,
                const unsigned char *src,
                int                  w,
                int                  h)
{
  const unsigned int block_count = BLOCK_COUNT(w, h);
  unsigned int i;
  unsigned char block[64], *p;
  int x, y;

#ifdef _OPENMP
#pragma omp parallel for schedule(dynamic, 256) private(block, p, x, y)
#endif
  for (i = 0; i < block_count; ++i)
    {
      x = (i % ((w + 3) >> 2)) << 2;
      y = (i / ((w + 3) >> 2)) << 2;
      p = dst + BLOCK_OFFSET(x, y, w, 16);
      extract_block (src, x, y, w, h, block);
      encode_alpha_block_BC3(p, block, 0);
      encode_YCoCg_block(p + 8, block);
    }
}

int
dxt_compress (unsigned char *dst,
              unsigned char *src,
              int            format,
              unsigned int   width,
              unsigned int   height,
              int            bpp,
              int            mipmaps,
              int            flags)
{
  gint                          i;
  gint                          size;
  gint                          w;
  gint                          h;
  guint                         offset;
  guchar                       *tmp = NULL;
  gint                          j;
  guchar                       *s;
  bc7enc_compress_block_params  bc7_params;

  if (bpp == 1)
    {
      /* grayscale promoted to BGRA */

      size = get_mipmapped_size(width, height, 4, 0, mipmaps,
                                DDS_COMPRESS_NONE);
      tmp = g_malloc(size);

      for (i = j = 0; j < size; ++i, j += 4)
        {
          tmp[j + 0] = src[i];
          tmp[j + 1] = src[i];
          tmp[j + 2] = src[i];
          tmp[j + 3] = 255;
        }

      bpp = 4;
    }
  else if (bpp == 2)
    {
      /* gray-alpha promoted to BGRA */

      size = get_mipmapped_size(width, height, 4, 0, mipmaps,
                                DDS_COMPRESS_NONE);
      tmp = g_malloc(size);

      for (i = j = 0; j < size; i += 2, j += 4)
        {
          tmp[j + 0] = src[i];
          tmp[j + 1] = src[i];
          tmp[j + 2] = src[i];
          tmp[j + 3] = src[i + 1];
        }

      bpp = 4;
    }
  else if (bpp == 3)
    {
      size = get_mipmapped_size(width, height, 4, 0, mipmaps,
                                DDS_COMPRESS_NONE);
      tmp = g_malloc(size);

      for (i = j = 0; j < size; i += 3, j += 4)
        {
          tmp[j + 0] = src[i + 0];
          tmp[j + 1] = src[i + 1];
          tmp[j + 2] = src[i + 2];
          tmp[j + 3] = 255;
        }

      bpp = 4;
    }

  offset = 0;
  w = width;
  h = height;
  s = tmp ? tmp : src;

  bc7_params.m_perceptual = (flags & DXT_PERCEPTUAL);
  if (format == DDS_COMPRESS_BC7)
    {
      bc7enc_compress_block_init ();
      bc7enc_compress_block_params_init (&bc7_params);
    }

  for (i = 0; i < mipmaps; ++i)
    {
      switch (format)
        {
        case DDS_COMPRESS_BC1:
          compress_BC1(dst + offset, s, w, h, flags);
          break;
        case DDS_COMPRESS_BC2:
          compress_BC2(dst + offset, s, w, h, flags);
          break;
        case DDS_COMPRESS_BC3:
        case DDS_COMPRESS_BC3N:
        case DDS_COMPRESS_RXGB:
        case DDS_COMPRESS_AEXP:
        case DDS_COMPRESS_YCOCG:
          compress_BC3(dst + offset, s, w, h, flags);
          break;
        case DDS_COMPRESS_BC4:
          compress_BC4(dst + offset, s, w, h);
          break;
        case DDS_COMPRESS_BC5:
          compress_BC5(dst + offset, s, w, h);
          break;
        case DDS_COMPRESS_BC7:
          compress_BC7 (dst + offset, s, w, h, &bc7_params);
          break;
        case DDS_COMPRESS_YCOCGS:
          compress_YCoCg(dst + offset, s, w, h);
          break;
        default:
          compress_BC3(dst + offset, s, w, h, flags);
          break;
        }
      s += (w * h * bpp);
      offset += get_mipmapped_size(w, h, 0, 0, 1, format);
      w = MAX(1, w >> 1);
      h = MAX(1, h >> 1);
    }

  if (tmp)
    g_free(tmp);

  return 1;
}

static void
decode_color_block (guchar *block,
                    guchar *src,
                    gint    format)
{
  guchar  *d = block;
  guint    indices, idx;
  guchar   colors[4][3];
  gushort  c0, c1;
  gint     i, x, y;

  c0 = GETL16 (&src[0]);
  c1 = GETL16 (&src[2]);

  unpack_rgb565 (colors[0], c0);
  unpack_rgb565 (colors[1], c1);

  if ((c0 > c1) || (format == DDS_COMPRESS_BC3))
    {
      /* Four-color mode */
      lerp_rgb13 (colors[2], colors[0], colors[1]);
      lerp_rgb13 (colors[3], colors[1], colors[0]);
    }
  else
    {
      /* Three-color mode */
      for (i = 0; i < 3; ++i)
        {
          colors[2][i] = (colors[0][i] + colors[1][i] + 1) >> 1;
          colors[3][i] = 0;  /* Three-color mode index 11 is always black */
        }
    }

  src += 4;
  for (y = 0; y < 4; ++y)
    {
      indices = src[y];
      for (x = 0; x < 4; ++x)
        {
          idx = indices & 0x03;
          d[0] = colors[idx][2];
          d[1] = colors[idx][1];
          d[2] = colors[idx][0];
          if (format == DDS_COMPRESS_BC1)
            d[3] = ((c0 <= c1) && idx == 3) ? 0 : 255;
          indices >>= 2;
          d += 4;
        }
    }
}

static void
decode_alpha_block_BC2 (unsigned char *block,
                        unsigned char *src)
{
  int x, y;
  unsigned char *d = block;
  unsigned int bits;

  for (y = 0; y < 4; ++y)
    {
      bits = GETL16(&src[2 * y]);
      for (x = 0; x < 4; ++x)
        {
          d[0] = (bits & 0x0f) * 17;
          bits >>= 4;
          d += 4;
        }
    }
}

static void
decode_alpha_block_BC3 (unsigned char *block,
                        unsigned char *src,
                        int            w)
{
  int x, y, code;
  unsigned char *d = block;
  unsigned char a0 = src[0];
  unsigned char a1 = src[1];
  unsigned long long bits = GETL64(src) >> 16;

  for (y = 0; y < 4; ++y)
    {
      for (x = 0; x < 4; ++x)
        {
          code = ((unsigned int)bits) & 0x07;
          if (code == 0)
            d[0] = a0;
          else if (code == 1)
            d[0] = a1;
          else if (a0 > a1)
            d[0] = ((8 - code) * a0 + (code - 1) * a1) / 7;
          else if (code >= 6)
            d[0] = (code == 6) ? 0 : 255;
          else
            d[0] = ((6 - code) * a0 + (code - 1) * a1) / 5;
          bits >>= 3;
          d += 4;
        }

      if (w < 4)
        bits >>= (3 * (4 - w));
    }
}

static void
make_normal (unsigned char *dst,
             unsigned char  x,
             unsigned char  y)
{
  float nx = 2.0f * ((float)x / 255.0f) - 1.0f;
  float ny = 2.0f * ((float)y / 255.0f) - 1.0f;
  float nz = 0.0f;
  float d = 1.0f - nx * nx + ny * ny;
  int z;

  if (d > 0)
    nz = sqrtf(d);

  z = (int)(255.0f * (nz + 1) / 2.0f);
  z = MAX(0, MIN(255, z));

  dst[0] = x;
  dst[1] = y;
  dst[2] = z;
}

static void
normalize_block (unsigned char *block,
                 int            format)
{
  int x, y, tmp;

  for (y = 0; y < 4; ++y)
    {
      for (x = 0; x < 4; ++x)
        {
          if (format == DDS_COMPRESS_BC3)
            {
              tmp = block[y * 16 + (x * 4)];
              make_normal(&block[y * 16 + (x * 4)],
                          block[y * 16 + (x * 4) + 3],
                          block[y * 16 + (x * 4) + 1]);
              block[y * 16 + (x * 4) + 3] = tmp;
            }
          else if (format == DDS_COMPRESS_BC5)
            {
              make_normal(&block[y * 16 + (x * 4)],
                          block[y * 16 + (x * 4)],
                          block[y * 16 + (x * 4) + 1]);
            }
        }
    }
}

static void
put_block (unsigned char *dst,
           unsigned char *block,
           unsigned int   bx,
           unsigned int   by,
           unsigned int   width,
           unsigned       height,
           int            bpp)
{
  int x, y, i;
  unsigned char *d;

  for (y = 0; y < 4 && ((by + y) < height); ++y)
    {
      d = dst + ((y + by) * width + bx) * bpp;
      for (x = 0; x < 4 && ((bx + x) < width); ++x)
        {
          for (i = 0; i < bpp; ++ i)
            *d++ = block[y * 16 + (x * 4) + i];
        }
    }
}

int
dxt_decompress (unsigned char *dst,
                unsigned char *src,
                int            format,
                unsigned int   size,
                unsigned int   width,
                unsigned int   height,
                int            bpp,
                int            normals)
{
  unsigned char *s;
  unsigned int x, y;
  unsigned char block[16 * 4];

  s = src;

  for (y = 0; y < height; y += 4)
    {
      for (x = 0; x < width; x += 4)
        {
          memset(block, 0, 16 * 4);

          if (format == DDS_COMPRESS_BC1)
            {
              decode_color_block(block, s, format);
              s += 8;
            }
          else if (format == DDS_COMPRESS_BC2)
            {
              decode_alpha_block_BC2(block + 3, s);
              decode_color_block(block, s + 8, format);
              s += 16;
            }
          else if (format == DDS_COMPRESS_BC3)
            {
              decode_alpha_block_BC3(block + 3, s, width);
              decode_color_block(block, s + 8, format);
              s += 16;
            }
          else if (format == DDS_COMPRESS_BC4)
            {
              decode_alpha_block_BC3(block, s, width);
              s += 8;
            }
          else if (format == DDS_COMPRESS_BC5)
            {
              decode_alpha_block_BC3(block, s, width);
              decode_alpha_block_BC3(block + 1, s + 8, width);
              s += 16;
            }
          else if (format == DDS_COMPRESS_BC7)
            {
              bc7_decompress (s, size, block);
              s += 16;
            }

          if (normals)
            normalize_block(block, format);

          put_block(dst, block, x, y, width, height, bpp);
        }
    }

  return 1;
}

/* --- end plug-ins/field-io/file-dds/dxt.c --- */

/* --- begin plug-ins/field-io/file-dds/formats.c --- */
/*
 * DDS AmmoOS Image plugin
 *
 * Copyright (C) 2004-2012 Shawn Kirst <skirst@gmail.com>,
 * with parts (C) 2003 Arne Reuter <homepage@arnereuter.de> where specified.
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

#include <libgimp/ammoos.h>

#include "dds.h"
#include "formats.h"


/* Table that determines how uncompressed D3D9 and DXGI formats are read and parsed */
static const fmt_read_info_t format_read_info[] =
{/*|D3D Format           |DXGI Format                           |Order     |Channel Bits |bpp|Alpha |Float |Signed|AmmoOS Image Type    */
  { D3DFMT_R8G8B8,        DXGI_FORMAT_UNKNOWN,                  {2,1,0,3}, { 8, 8, 8, 0},  8, FALSE, FALSE, FALSE, GIMP_RGB     },
  { D3DFMT_A8R8G8B8,      DXGI_FORMAT_UNKNOWN,                  {2,1,0,3}, { 8, 8, 8, 8},  8, TRUE,  FALSE, FALSE, GIMP_RGB     },
  { D3DFMT_X8R8G8B8,      DXGI_FORMAT_UNKNOWN,                  {2,1,0,3}, { 8, 8, 8, 8},  8, FALSE, FALSE, FALSE, GIMP_RGB     },
  { D3DFMT_R5G6B5,        DXGI_FORMAT_UNKNOWN,                  {2,1,0,3}, { 5, 6, 5, 0},  8, FALSE, FALSE, FALSE, GIMP_RGB     },
  { D3DFMT_X1R5G5B5,      DXGI_FORMAT_UNKNOWN,                  {2,1,0,3}, { 5, 5, 5, 1},  8, FALSE, FALSE, FALSE, GIMP_RGB     },
  { D3DFMT_A1R5G5B5,      DXGI_FORMAT_UNKNOWN,                  {2,1,0,3}, { 5, 5, 5, 1},  8, TRUE,  FALSE, FALSE, GIMP_RGB     },
  { D3DFMT_A4R4G4B4,      DXGI_FORMAT_UNKNOWN,                  {2,1,0,3}, { 4, 4, 4, 4},  8, TRUE,  FALSE, FALSE, GIMP_RGB     },
  { D3DFMT_R3G3B2,        DXGI_FORMAT_UNKNOWN,                  {2,1,0,3}, { 2, 3, 3, 0},  8, FALSE, FALSE, FALSE, GIMP_RGB     },
  { D3DFMT_A8,            DXGI_FORMAT_UNKNOWN,                  {3,2,1,0}, { 8, 0, 0, 0},  8, TRUE,  FALSE, FALSE, GIMP_GRAY    },
  { D3DFMT_A8R3G3B2,      DXGI_FORMAT_UNKNOWN,                  {2,1,0,3}, { 2, 3, 3, 8},  8, TRUE,  FALSE, FALSE, GIMP_RGB     },
  { D3DFMT_X4R4G4B4,      DXGI_FORMAT_UNKNOWN,                  {2,1,0,3}, { 4, 4, 4, 4},  8, FALSE, FALSE, FALSE, GIMP_RGB     },
  { D3DFMT_A2B10G10R10,   DXGI_FORMAT_UNKNOWN,                  {2,1,0,3}, {10,10,10, 2}, 16, TRUE,  FALSE, FALSE, GIMP_RGB     },
  { D3DFMT_A8B8G8R8,      DXGI_FORMAT_UNKNOWN,                  {0,1,2,3}, { 8, 8, 8, 8},  8, TRUE,  FALSE, FALSE, GIMP_RGB     },
  { D3DFMT_X8B8G8R8,      DXGI_FORMAT_UNKNOWN,                  {0,1,2,3}, { 8, 8, 8, 8},  8, FALSE, FALSE, FALSE, GIMP_RGB     },
  { D3DFMT_G16R16,        DXGI_FORMAT_UNKNOWN,                  {0,1,2,3}, {16,16, 0, 0}, 16, FALSE, FALSE, FALSE, GIMP_RGB     },
  { D3DFMT_A2R10G10B10,   DXGI_FORMAT_UNKNOWN,                  {0,1,2,3}, {10,10,10, 2}, 16, TRUE,  FALSE, FALSE, GIMP_RGB     },
  { D3DFMT_A16B16G16R16,  DXGI_FORMAT_UNKNOWN,                  {0,1,2,3}, {16,16,16,16}, 16, TRUE,  FALSE, FALSE, GIMP_RGB     },
  { D3DFMT_A8P8,          DXGI_FORMAT_UNKNOWN,                  {0,3,2,1}, { 8, 8, 0, 0},  8, TRUE,  FALSE, FALSE, GIMP_INDEXED },
  { D3DFMT_P8,            DXGI_FORMAT_UNKNOWN,                  {0,1,2,3}, { 8, 0, 0, 0},  8, FALSE, FALSE, FALSE, GIMP_INDEXED },
  { D3DFMT_L8,            DXGI_FORMAT_UNKNOWN,                  {0,3,2,1}, { 8, 0, 0, 0},  8, FALSE, FALSE, FALSE, GIMP_GRAY    },
  { D3DFMT_A8L8,          DXGI_FORMAT_UNKNOWN,                  {0,3,2,1}, { 8, 8, 0, 0},  8, TRUE,  FALSE, FALSE, GIMP_GRAY    },
  { D3DFMT_A4L4,          DXGI_FORMAT_UNKNOWN,                  {0,3,2,1}, { 4, 4, 0, 0},  8, TRUE,  FALSE, FALSE, GIMP_GRAY    },
  { D3DFMT_V8U8,          DXGI_FORMAT_UNKNOWN,                  {0,1,2,3}, { 8, 8, 0, 0},  8, FALSE, FALSE, TRUE,  GIMP_RGB     },
  { D3DFMT_L6V5U5,        DXGI_FORMAT_UNKNOWN,                  {0,1,2,3}, { 5, 5, 6, 0},  8, FALSE, FALSE, TRUE,  GIMP_RGB     },
  { D3DFMT_X8L8V8U8,      DXGI_FORMAT_UNKNOWN,                  {0,1,2,3}, { 8, 8, 8, 8},  8, FALSE, FALSE, TRUE,  GIMP_RGB     },
  { D3DFMT_Q8W8V8U8,      DXGI_FORMAT_UNKNOWN,                  {0,1,2,3}, { 8, 8, 8, 8},  8, TRUE,  FALSE, TRUE,  GIMP_RGB     },
  { D3DFMT_V16U16,        DXGI_FORMAT_UNKNOWN,                  {0,1,2,3}, {16,16, 0, 0}, 16, FALSE, FALSE, TRUE,  GIMP_RGB     },
  { D3DFMT_A2W10V10U10,   DXGI_FORMAT_UNKNOWN,                  {0,1,2,3}, {10,10,10, 2}, 16, TRUE,  FALSE, TRUE,  GIMP_RGB     },
  { D3DFMT_D16_LOCKABLE,  DXGI_FORMAT_UNKNOWN,                  {0,1,2,3}, {16, 0, 0, 0}, 16, FALSE, FALSE, FALSE, GIMP_GRAY    },
  { D3DFMT_D32,           DXGI_FORMAT_UNKNOWN,                  {0,1,2,3}, {32, 0, 0, 0}, 32, FALSE, FALSE, FALSE, GIMP_GRAY    },
  { D3DFMT_D15S1,         DXGI_FORMAT_UNKNOWN,                  {0,1,2,3}, {15, 1, 0, 0}, 16, FALSE, FALSE, FALSE, GIMP_RGB     },
  { D3DFMT_D24S8,         DXGI_FORMAT_UNKNOWN,                  {0,1,2,3}, {24, 8, 0, 0}, 32, FALSE, FALSE, FALSE, GIMP_RGB     },
  { D3DFMT_D24X8,         DXGI_FORMAT_UNKNOWN,                  {0,1,2,3}, {24, 8, 0, 0}, 32, FALSE, FALSE, FALSE, GIMP_RGB     },
  { D3DFMT_D24X4S4,       DXGI_FORMAT_UNKNOWN,                  {0,1,2,3}, {24, 4, 4, 0}, 32, FALSE, FALSE, FALSE, GIMP_RGB     },
  { D3DFMT_D16,           DXGI_FORMAT_UNKNOWN,                  {1,0,2,3}, {16, 0, 0, 0}, 16, FALSE, FALSE, FALSE, GIMP_GRAY    },
  { D3DFMT_L16,           DXGI_FORMAT_UNKNOWN,                  {0,1,2,3}, {16, 0, 0, 0}, 16, FALSE, FALSE, FALSE, GIMP_GRAY    },
  { D3DFMT_D32F_LOCKABLE, DXGI_FORMAT_UNKNOWN,                  {0,1,2,3}, {32, 0, 0, 0}, 32, FALSE, TRUE,  TRUE,  GIMP_GRAY    },
  { D3DFMT_D24FS8,        DXGI_FORMAT_UNKNOWN,                  {0,1,2,3}, {24, 8, 0, 0}, 32, FALSE, TRUE,  TRUE,  GIMP_RGB     },
  { D3DFMT_D32_LOCKABLE,  DXGI_FORMAT_UNKNOWN,                  {0,1,2,3}, {32, 0, 0, 0}, 32, FALSE, FALSE, FALSE, GIMP_GRAY    },
  { D3DFMT_S8_LOCKABLE,   DXGI_FORMAT_UNKNOWN,                  {0,1,2,3}, { 8, 0, 0, 0},  8, FALSE, FALSE, FALSE, GIMP_GRAY    },
  { D3DFMT_Q16W16V16U16,  DXGI_FORMAT_UNKNOWN,                  {0,1,2,3}, {16,16,16,16}, 16, TRUE,  FALSE, TRUE,  GIMP_RGB     },
  { D3DFMT_R16F,          DXGI_FORMAT_UNKNOWN,                  {0,1,2,3}, {16, 0, 0, 0}, 16, FALSE, TRUE,  TRUE,  GIMP_GRAY    },
  { D3DFMT_G16R16F,       DXGI_FORMAT_UNKNOWN,                  {0,1,2,3}, {16,16, 0, 0}, 16, FALSE, TRUE,  TRUE,  GIMP_RGB     },
  { D3DFMT_A16B16G16R16F, DXGI_FORMAT_UNKNOWN,                  {0,1,2,3}, {16,16,16,16}, 16, TRUE,  TRUE,  TRUE,  GIMP_RGB     },
  { D3DFMT_R32F,          DXGI_FORMAT_UNKNOWN,                  {0,1,2,3}, {32, 0, 0, 0}, 32, FALSE, TRUE,  TRUE,  GIMP_GRAY    },
  { D3DFMT_G32R32F,       DXGI_FORMAT_UNKNOWN,                  {0,1,2,3}, {32,32, 0, 0}, 32, FALSE, TRUE,  TRUE,  GIMP_RGB     },
  { D3DFMT_A32B32G32R32F, DXGI_FORMAT_UNKNOWN,                  {0,1,2,3}, {32,32,32,32}, 32, TRUE,  TRUE,  TRUE,  GIMP_RGB     },
  { D3DFMT_CxV8U8,        DXGI_FORMAT_UNKNOWN,                  {0,1,2,3}, { 8, 8, 0, 0},  8, FALSE, FALSE, TRUE,  GIMP_RGB     },
  { D3DFMT_A1,            DXGI_FORMAT_UNKNOWN,                  {3,2,1,0}, { 1, 0, 0, 0},  8, TRUE,  FALSE, FALSE, GIMP_GRAY    },

  /* Older AmmoOS Image wrote this when exporting to BGR8 */
  { D3DFMT_B8G8R8,        DXGI_FORMAT_UNKNOWN,                  {0,1,2,3}, { 8, 8, 8, 0},  8, FALSE, FALSE, FALSE, GIMP_RGB     },

  { D3DFMT_UNKNOWN,       DXGI_FORMAT_R32G32B32A32_FLOAT,       {0,1,2,3}, {32,32,32,32}, 32, TRUE,  TRUE,  TRUE,  GIMP_RGB     },
  { D3DFMT_UNKNOWN,       DXGI_FORMAT_R32G32B32A32_UINT,        {0,1,2,3}, {32,32,32,32}, 32, TRUE,  FALSE, FALSE, GIMP_RGB     },
  { D3DFMT_UNKNOWN,       DXGI_FORMAT_R32G32B32A32_SINT,        {0,1,2,3}, {32,32,32,32}, 32, TRUE,  FALSE, TRUE,  GIMP_RGB     },
  { D3DFMT_UNKNOWN,       DXGI_FORMAT_R32G32B32_FLOAT,          {0,1,2,3}, {32,32,32, 0}, 32, FALSE, TRUE,  TRUE,  GIMP_RGB     },
  { D3DFMT_UNKNOWN,       DXGI_FORMAT_R32G32B32_UINT,           {0,1,2,3}, {32,32,32, 0}, 32, FALSE, FALSE, FALSE, GIMP_RGB     },
  { D3DFMT_UNKNOWN,       DXGI_FORMAT_R32G32B32_SINT,           {0,1,2,3}, {32,32,32, 0}, 32, FALSE, FALSE, TRUE,  GIMP_RGB     },
  { D3DFMT_UNKNOWN,       DXGI_FORMAT_R16G16B16A16_FLOAT,       {0,1,2,3}, {16,16,16,16}, 16, TRUE,  TRUE,  TRUE,  GIMP_RGB     },
  { D3DFMT_UNKNOWN,       DXGI_FORMAT_R16G16B16A16_UNORM,       {0,1,2,3}, {16,16,16,16}, 16, TRUE,  FALSE, FALSE, GIMP_RGB     },
  { D3DFMT_UNKNOWN,       DXGI_FORMAT_R16G16B16A16_UINT,        {0,1,2,3}, {16,16,16,16}, 16, TRUE,  FALSE, FALSE, GIMP_RGB     },
  { D3DFMT_UNKNOWN,       DXGI_FORMAT_R16G16B16A16_SNORM,       {0,1,2,3}, {16,16,16,16}, 16, TRUE,  FALSE, TRUE,  GIMP_RGB     },
  { D3DFMT_UNKNOWN,       DXGI_FORMAT_R16G16B16A16_SINT,        {0,1,2,3}, {16,16,16,16}, 16, TRUE,  FALSE, TRUE,  GIMP_RGB     },
  { D3DFMT_UNKNOWN,       DXGI_FORMAT_R32G32_FLOAT,             {0,1,2,3}, {32,32, 0, 0}, 32, FALSE, TRUE,  TRUE,  GIMP_RGB     },
  { D3DFMT_UNKNOWN,       DXGI_FORMAT_R32G32_UINT,              {0,1,2,3}, {32,32, 0, 0}, 32, FALSE, FALSE, FALSE, GIMP_RGB     },
  { D3DFMT_UNKNOWN,       DXGI_FORMAT_R32G32_SINT,              {0,1,2,3}, {32,32, 0, 0}, 32, FALSE, FALSE, TRUE,  GIMP_RGB     },
  { D3DFMT_UNKNOWN,       DXGI_FORMAT_D32_FLOAT_S8X24_UINT,     {0,1,2,3}, {32, 8,24, 0}, 32, FALSE, TRUE,  TRUE,  GIMP_RGB     },
  { D3DFMT_UNKNOWN,       DXGI_FORMAT_R10G10B10A2_UNORM,        {0,1,2,3}, {10,10,10, 2}, 16, TRUE,  FALSE, FALSE, GIMP_RGB     },
  { D3DFMT_UNKNOWN,       DXGI_FORMAT_R10G10B10A2_UINT,         {0,1,2,3}, {10,10,10, 2}, 16, TRUE,  FALSE, FALSE, GIMP_RGB     },
  { D3DFMT_UNKNOWN,       DXGI_FORMAT_R11G11B10_FLOAT,          {0,1,2,3}, {11,11,10, 0}, 16, FALSE, TRUE,  FALSE, GIMP_RGB     },
  { D3DFMT_UNKNOWN,       DXGI_FORMAT_R8G8B8A8_UNORM,           {0,1,2,3}, { 8, 8, 8, 8},  8, TRUE,  FALSE, FALSE, GIMP_RGB     },
  { D3DFMT_UNKNOWN,       DXGI_FORMAT_R8G8B8A8_UNORM_SRGB,      {0,1,2,3}, { 8, 8, 8, 8},  8, TRUE,  FALSE, FALSE, GIMP_RGB     },
  { D3DFMT_UNKNOWN,       DXGI_FORMAT_R8G8B8A8_UINT,            {0,1,2,3}, { 8, 8, 8, 8},  8, TRUE,  FALSE, FALSE, GIMP_RGB     },
  { D3DFMT_UNKNOWN,       DXGI_FORMAT_R8G8B8A8_SNORM,           {0,1,2,3}, { 8, 8, 8, 8},  8, TRUE,  FALSE, TRUE,  GIMP_RGB     },
  { D3DFMT_UNKNOWN,       DXGI_FORMAT_R8G8B8A8_SINT,            {0,1,2,3}, { 8, 8, 8, 8},  8, TRUE,  FALSE, TRUE,  GIMP_RGB     },
  { D3DFMT_UNKNOWN,       DXGI_FORMAT_R16G16_FLOAT,             {0,1,2,3}, {16,16, 0, 0}, 16, FALSE, TRUE,  TRUE,  GIMP_RGB     },
  { D3DFMT_UNKNOWN,       DXGI_FORMAT_R16G16_UNORM,             {0,1,2,3}, {16,16, 0, 0}, 16, FALSE, FALSE, FALSE, GIMP_RGB     },
  { D3DFMT_UNKNOWN,       DXGI_FORMAT_R16G16_UINT,              {0,1,2,3}, {16,16, 0, 0}, 16, FALSE, FALSE, FALSE, GIMP_RGB     },
  { D3DFMT_UNKNOWN,       DXGI_FORMAT_R16G16_SNORM,             {0,1,2,3}, {16,16, 0, 0}, 16, FALSE, FALSE, TRUE,  GIMP_RGB     },
  { D3DFMT_UNKNOWN,       DXGI_FORMAT_R16G16_SINT,              {0,1,2,3}, {16,16, 0, 0}, 16, FALSE, FALSE, TRUE,  GIMP_RGB     },
  { D3DFMT_UNKNOWN,       DXGI_FORMAT_D32_FLOAT,                {0,1,2,3}, {32, 0, 0, 0}, 32, FALSE, TRUE,  TRUE,  GIMP_GRAY    },
  { D3DFMT_UNKNOWN,       DXGI_FORMAT_R32_FLOAT,                {0,1,2,3}, {32, 0, 0, 0}, 32, FALSE, TRUE,  TRUE,  GIMP_GRAY    },
  { D3DFMT_UNKNOWN,       DXGI_FORMAT_R32_UINT,                 {0,1,2,3}, {32, 0, 0, 0}, 32, FALSE, FALSE, FALSE, GIMP_GRAY    },
  { D3DFMT_UNKNOWN,       DXGI_FORMAT_R32_SINT,                 {0,1,2,3}, {32, 0, 0, 0}, 32, FALSE, FALSE, TRUE,  GIMP_GRAY    },
  { D3DFMT_UNKNOWN,       DXGI_FORMAT_D24_UNORM_S8_UINT,        {0,1,2,3}, {24, 8, 0, 0}, 32, FALSE, FALSE, FALSE, GIMP_RGB     },
  { D3DFMT_UNKNOWN,       DXGI_FORMAT_R8G8_UNORM,               {0,1,2,3}, { 8, 8, 0, 0},  8, FALSE, FALSE, FALSE, GIMP_RGB     },
  { D3DFMT_UNKNOWN,       DXGI_FORMAT_R8G8_UINT,                {0,1,2,3}, { 8, 8, 0, 0},  8, FALSE, FALSE, FALSE, GIMP_RGB     },
  { D3DFMT_UNKNOWN,       DXGI_FORMAT_R8G8_SNORM,               {0,1,2,3}, { 8, 8, 0, 0},  8, FALSE, FALSE, TRUE,  GIMP_RGB     },
  { D3DFMT_UNKNOWN,       DXGI_FORMAT_R8G8_SINT,                {0,1,2,3}, { 8, 8, 0, 0},  8, FALSE, FALSE, TRUE,  GIMP_RGB     },
  { D3DFMT_UNKNOWN,       DXGI_FORMAT_R16_FLOAT,                {0,1,2,3}, {16, 0, 0, 0}, 16, FALSE, TRUE,  TRUE,  GIMP_GRAY    },
  { D3DFMT_UNKNOWN,       DXGI_FORMAT_D16_UNORM,                {0,1,2,3}, {16, 0, 0, 0}, 16, FALSE, FALSE, FALSE, GIMP_GRAY    },
  { D3DFMT_UNKNOWN,       DXGI_FORMAT_R16_UNORM,                {0,1,2,3}, {16, 0, 0, 0}, 16, FALSE, FALSE, FALSE, GIMP_GRAY    },
  { D3DFMT_UNKNOWN,       DXGI_FORMAT_R16_UINT,                 {0,1,2,3}, {16, 0, 0, 0}, 16, FALSE, FALSE, FALSE, GIMP_GRAY    },
  { D3DFMT_UNKNOWN,       DXGI_FORMAT_R16_SNORM,                {0,1,2,3}, {16, 0, 0, 0}, 16, FALSE, FALSE, TRUE,  GIMP_GRAY    },
  { D3DFMT_UNKNOWN,       DXGI_FORMAT_R16_SINT,                 {0,1,2,3}, {16, 0, 0, 0}, 16, FALSE, FALSE, TRUE,  GIMP_GRAY    },
  { D3DFMT_UNKNOWN,       DXGI_FORMAT_R8_UNORM,                 {0,1,2,3}, { 8, 0, 0, 0},  8, FALSE, FALSE, FALSE, GIMP_GRAY    },
  { D3DFMT_UNKNOWN,       DXGI_FORMAT_R8_UINT,                  {0,1,2,3}, { 8, 0, 0, 0},  8, FALSE, FALSE, FALSE, GIMP_GRAY    },
  { D3DFMT_UNKNOWN,       DXGI_FORMAT_R8_SNORM,                 {0,1,2,3}, { 8, 0, 0, 0},  8, FALSE, FALSE, TRUE,  GIMP_GRAY    },
  { D3DFMT_UNKNOWN,       DXGI_FORMAT_R8_SINT,                  {0,1,2,3}, { 8, 0, 0, 0},  8, FALSE, FALSE, TRUE,  GIMP_GRAY    },
  { D3DFMT_UNKNOWN,       DXGI_FORMAT_A8_UNORM,                 {3,2,1,0}, { 8, 0, 0, 0},  8, TRUE,  FALSE, FALSE, GIMP_GRAY    },
  { D3DFMT_UNKNOWN,       DXGI_FORMAT_R9G9B9E5_SHAREDEXP,       {0,1,2,3}, { 9, 9, 9, 5}, 32, FALSE, TRUE,  FALSE, GIMP_RGB     },
  { D3DFMT_UNKNOWN,       DXGI_FORMAT_B5G6R5_UNORM,             {0,1,2,3}, { 5, 6, 5, 0},  8, FALSE, FALSE, FALSE, GIMP_RGB     },
  { D3DFMT_UNKNOWN,       DXGI_FORMAT_B5G5R5A1_UNORM,           {0,1,2,3}, { 5, 5, 5, 1},  8, TRUE,  FALSE, FALSE, GIMP_RGB     },
  { D3DFMT_UNKNOWN,       DXGI_FORMAT_B8G8R8A8_UNORM,           {2,1,0,3}, { 8, 8, 8, 8},  8, TRUE,  FALSE, FALSE, GIMP_RGB     },
  { D3DFMT_UNKNOWN,       DXGI_FORMAT_B8G8R8X8_UNORM,           {2,1,0,3}, { 8, 8, 8, 8},  8, FALSE, FALSE, FALSE, GIMP_RGB     },
  { D3DFMT_UNKNOWN,       DXGI_FORMAT_B8G8R8A8_UNORM_SRGB,      {2,1,0,3}, { 8, 8, 8, 8},  8, TRUE,  FALSE, FALSE, GIMP_RGB     },
  { D3DFMT_UNKNOWN,       DXGI_FORMAT_B8G8R8X8_UNORM_SRGB,      {2,1,0,3}, { 8, 8, 8, 8},  8, FALSE, FALSE, FALSE, GIMP_RGB     },
  { D3DFMT_UNKNOWN,       DXGI_FORMAT_P8,                       {0,1,2,3}, { 8, 0, 0, 0},  8, FALSE, FALSE, FALSE, GIMP_INDEXED },
  { D3DFMT_UNKNOWN,       DXGI_FORMAT_A8P8,                     {0,1,2,3}, { 8, 8, 0, 0},  8, TRUE,  FALSE, FALSE, GIMP_INDEXED },
  { D3DFMT_UNKNOWN,       DXGI_FORMAT_B4G4R4A4_UNORM,           {2,1,0,3}, { 4, 4, 4, 4},  8, TRUE,  FALSE, FALSE, GIMP_RGB     },
  { D3DFMT_UNKNOWN,       DXGI_FORMAT_R10G10B10_7E3_A2_FLOAT,   {0,1,2,3}, {10,10,10, 2}, 32, TRUE,  TRUE,  FALSE, GIMP_RGB     },
  { D3DFMT_UNKNOWN,       DXGI_FORMAT_R10G10B10_6E4_A2_FLOAT,   {0,1,2,3}, {10,10,10, 2}, 32, TRUE,  TRUE,  FALSE, GIMP_RGB     },
  { D3DFMT_UNKNOWN,       DXGI_FORMAT_D16_UNORM_S8_UINT,        {0,1,2,3}, {16, 8, 0, 0}, 16, FALSE, FALSE, FALSE, GIMP_RGB     },
  { D3DFMT_UNKNOWN,       DXGI_FORMAT_R16_UNORM_X8_TYPELESS,    {0,1,2,3}, {16, 8, 0, 0}, 16, FALSE, FALSE, FALSE, GIMP_RGB     },
  { D3DFMT_UNKNOWN,       DXGI_FORMAT_X16_TYPELESS_G8_UINT,     {0,1,2,3}, {16, 8, 0, 0}, 16, FALSE, FALSE, FALSE, GIMP_RGB     },
  { D3DFMT_UNKNOWN,       DXGI_FORMAT_R10G10B10_SNORM_A2_UNORM, {0,1,2,3}, {10,10,10, 2}, 16, TRUE,  FALSE, TRUE,  GIMP_RGB     },
  { D3DFMT_UNKNOWN,       DXGI_FORMAT_R4G4_UNORM,               {0,1,2,3}, { 4, 4, 0, 0},  8, FALSE, FALSE, FALSE, GIMP_RGB     },
  { D3DFMT_UNKNOWN,       DXGI_FORMAT_A4B4G4R4_UNORM,           {3,2,1,0}, { 4, 4, 4, 4},  8, TRUE,  FALSE, FALSE, GIMP_RGB     },
};
#define FORMAT_READ_INFO_COUNT (sizeof (format_read_info) / sizeof (fmt_read_info_t))

/* Table for mapping bpp, mask, and flag values to D3D9 format codes */
static struct _FMT_MAP
{
  D3DFORMAT    d3d9_format;
  gint         bpp;
  guint        rmask;
  guint        gmask;
  guint        bmask;
  guint        amask;
  guint        flags;
} format_map[] =
{/*|D3D Format          |bpp|R Mask     |G Mask     |B Mask     |A Mask     |Flags                                   */
  { D3DFMT_R8G8B8,       24, 0x00FF0000, 0x0000FF00, 0x000000FF, 0x00000000, DDPF_RGB                                },
  { D3DFMT_A8R8G8B8,     32, 0x00FF0000, 0x0000FF00, 0x000000FF, 0xFF000000, DDPF_RGB | DDPF_ALPHAPIXELS             },
  { D3DFMT_X8R8G8B8,     32, 0x00FF0000, 0x0000FF00, 0x000000FF, 0x00000000, DDPF_RGB                                },
  { D3DFMT_R5G6B5,       16, 0x0000F800, 0x000007E0, 0x0000001F, 0x00000000, DDPF_RGB                                },
  { D3DFMT_X1R5G5B5,     16, 0x00007C00, 0x000003E0, 0x0000001F, 0x00000000, DDPF_RGB                                },
  { D3DFMT_A1R5G5B5,     16, 0x00007C00, 0x000003E0, 0x0000001F, 0x00008000, DDPF_RGB | DDPF_ALPHAPIXELS             },
  { D3DFMT_A4R4G4B4,     16, 0x00000F00, 0x000000F0, 0x0000000F, 0x0000F000, DDPF_RGB | DDPF_ALPHAPIXELS             },
  { D3DFMT_R3G3B2,        8, 0x000000E0, 0x0000001C, 0x00000003, 0x00000000, DDPF_RGB                                },
  { D3DFMT_A8,            8, 0x00000000, 0x00000000, 0x00000000, 0x000000FF, DDPF_ALPHA                              },
  { D3DFMT_A8R3G3B2,     16, 0x000000E0, 0x0000001C, 0x00000003, 0x0000FF00, DDPF_RGB | DDPF_ALPHAPIXELS             },
  { D3DFMT_X4R4G4B4,     16, 0x00000F00, 0x000000F0, 0x0000000F, 0x00000000, DDPF_RGB                                },
  { D3DFMT_A2B10G10R10,  32, 0x000003FF, 0x000FFC00, 0x3FF00000, 0xC0000000, DDPF_RGB | DDPF_ALPHAPIXELS             },
  { D3DFMT_A8B8G8R8,     32, 0x000000FF, 0x0000FF00, 0x00FF0000, 0xFF000000, DDPF_RGB | DDPF_ALPHAPIXELS             },
  { D3DFMT_X8B8G8R8,     32, 0x000000FF, 0x0000FF00, 0x00FF0000, 0x00000000, DDPF_RGB                                },
  { D3DFMT_G16R16,       32, 0x0000FFFF, 0xFFFF0000, 0x00000000, 0x00000000, DDPF_RGB                                },
  { D3DFMT_A2R10G10B10,  32, 0x3FF00000, 0x000FFC00, 0x000003FF, 0xC0000000, DDPF_RGB | DDPF_ALPHAPIXELS             },
  { D3DFMT_A8P8,         16, 0x00000000, 0x00000000, 0x00000000, 0x0000FF00, DDPF_PALETTEINDEXED8 | DDPF_ALPHAPIXELS },
  { D3DFMT_P8,            8, 0x00000000, 0x00000000, 0x00000000, 0x00000000, DDPF_PALETTEINDEXED8                    },
  { D3DFMT_L8,            8, 0x000000FF, 0x00000000, 0x00000000, 0x00000000, DDPF_LUMINANCE                          },
  { D3DFMT_A8L8,         16, 0x000000FF, 0x00000000, 0x00000000, 0x0000FF00, DDPF_LUMINANCE | DDPF_ALPHAPIXELS       },
  { D3DFMT_A4L4,          8, 0x0000000F, 0x00000000, 0x00000000, 0x000000F0, DDPF_LUMINANCE | DDPF_ALPHAPIXELS       },
  { D3DFMT_UNKNOWN,      16, 0x000000FF, 0x0000FF00, 0x00000000, 0x00000000, DDPF_RGB                                },
  { D3DFMT_V8U8,         16, 0x000000FF, 0x0000FF00, 0x00000000, 0x00000000, DDPF_BUMPDUDV                           },
  { D3DFMT_L6V5U5,       16, 0x0000001F, 0x000003E0, 0x0000FC00, 0x00000000, DDPF_BUMPLUMINANCE                      },
  { D3DFMT_X8L8V8U8,     32, 0x000000FF, 0x0000FF00, 0x00FF0000, 0x00000000, DDPF_BUMPLUMINANCE                      },
  { D3DFMT_Q8W8V8U8,     32, 0x000000FF, 0x0000FF00, 0x00FF0000, 0xFF000000, DDPF_BUMPDUDV                           },
  { D3DFMT_V16U16,       32, 0x0000FFFF, 0xFFFF0000, 0x00000000, 0x00000000, DDPF_BUMPDUDV                           },
  { D3DFMT_A2W10V10U10,  32, 0x3FF00000, 0x000FFC00, 0x000003FF, 0xC0000000, DDPF_BUMPDUDV | DDPF_ALPHAPIXELS        },
  { D3DFMT_D16_LOCKABLE, 16, 0x00000000, 0x0000FFFF, 0x00000000, 0x00000000, DDPF_ZBUFFER                            },
  { D3DFMT_L16,          16, 0x0000FFFF, 0x00000000, 0x00000000, 0x00000000, DDPF_LUMINANCE                          },

  /* NVTT v1 wrote these with DDPF_RGB instead of DDPF_LUMINANCE */
  { D3DFMT_L8,            8, 0x000000FF, 0x00000000, 0x00000000, 0x00000000, DDPF_RGB                                },
  { D3DFMT_A8L8,         16, 0x000000FF, 0x00000000, 0x00000000, 0x0000FF00, DDPF_RGB | DDPF_ALPHAPIXELS             },
  { D3DFMT_L16,          16, 0x0000FFFF, 0x00000000, 0x00000000, 0x00000000, DDPF_RGB                                },

  /* Older versions of AmmoOS Image wrote these */
  { D3DFMT_B8G8R8,       24, 0x000000FF, 0x0000FF00, 0x00FF0000, 0x00000000, DDPF_RGB                                },
  { D3DFMT_L8,            8, 0x000000FF, 0x000000FF, 0x000000FF, 0x00000000, DDPF_LUMINANCE                          },
  { D3DFMT_A8L8,         16, 0x000000FF, 0x000000FF, 0x000000FF, 0x0000FF00, DDPF_LUMINANCE | DDPF_ALPHAPIXELS       },
  { D3DFMT_A8L8,         16, 0x000000FF, 0x000000FF, 0x000000FF, 0x0000FF00, DDPF_RGB | DDPF_ALPHAPIXELS             },
};
#define FORMAT_MAP_COUNT  (sizeof (format_map) / sizeof (format_map[0]))


/*
 * Get D3DFORMAT code that matches input bpp, masks, and flags
 */
guint
get_d3d9format (guint  bpp,
                guint  rmask,
                guint  gmask,
                guint  bmask,
                guint  amask,
                guint  flags)
{
  for (gint i = 0; i < FORMAT_MAP_COUNT; i++)
    {
      if (format_map[i].bpp   == bpp   &&
          format_map[i].rmask == rmask &&
          format_map[i].gmask == gmask &&
          format_map[i].bmask == bmask &&
          format_map[i].amask == amask &&
          (format_map[i].flags & flags) == format_map[i].flags)
        {
          return format_map[i].d3d9_format;
        }
    }
  return D3DFMT_UNKNOWN;
}

/*
 * Check that uncompressed DXGI format is supported
 */
gboolean
dxgiformat_supported (guint hdr_dxgifmt)
{
  for (gint i = 0; i < FORMAT_READ_INFO_COUNT; i++)
    {
      if (format_read_info[i].dxgi_format == hdr_dxgifmt)
        {
          return TRUE;
        }
    }
  return FALSE;
}

/*
 * Get read info from D3D9 or DXGI format code
 */
fmt_read_info_t
get_format_read_info (guint d3d9_fmt,
                      guint dxgi_fmt)
{
  gint index = 0;
  for (gint i = 0; i < FORMAT_READ_INFO_COUNT; i++)
    {
      if ((d3d9_fmt && (format_read_info[i].d3d9_format == d3d9_fmt)) ||
          (dxgi_fmt && (format_read_info[i].dxgi_format == dxgi_fmt)))
        {
          index = i;
          break;
        }
    }
  return format_read_info[index];
}

/*
 * Convert integer component from input size to output size (up to 32 bits)
 * Brute-force high-precision float method for minimum possible error
 */
guint32
requantize_component (guint32 bits,
                      guchar  size_in,
                      guchar  size_out)
{
  if (size_in == size_out)
    return bits;

  return (guint) ((gdouble) bits * ((gdouble) ((1ULL << size_out) - 1)
                                  / (gdouble) ((1ULL << size_in ) - 1)) + 0.5);
}

/* Special float handling for R9G9B9E5
 * https://microsoft.github.io/DirectX-Specs/d3d/archive/D3D11_3_FunctionalSpec.htm
 */
void
float_from_9e5 (guint32 channels[4])
{
  for (gint ch = 0; ch < 3; ch++)
    {
      gfloat val_f = (gfloat) exp2 ((gdouble) ((gint32) channels[3] - 15))
                                 * ((gdouble) channels[ch] / exp2 (9.0));
      memcpy (&channels[ch], &val_f, 4);
    }
}

/* Special float handling for R10G10B10_7E3_A2
 * https://github.com/microsoft/DirectXTex/blob/main/DirectXTex/DirectXTexConvert.cpp
 */
void
float_from_7e3a2 (guint32 channels[4])
{
  gint64 mantissa;
  gint64 exponent;
  gfloat alpha;

  for (gint ch = 0; ch < 3; ch++)
    {
      mantissa = channels[ch] & 0x0000007F;
      exponent = channels[ch] & 0x00000380;

      if (exponent != 0)  /* The value is normalized */
        {
          exponent = (channels[ch] >> 7) & 0x00000007;
        }
      else if (mantissa != 0)  /* The value is denormalized */
        {
          /* Normalize the value in the resulting float */
          exponent = 1;

          do
            {
              exponent--;
              mantissa <<= 1;
            }
          while ((mantissa & 0x80) == 0);

          mantissa &= 0x7F;
        }
      else  /* The value is zero */
        {
          exponent = -124;
        }

      channels[ch] = (guint32) (((exponent + 124) << 23) | (mantissa << 16));
    }
  alpha = (gfloat) channels[3] * (1.0f / 3.0f);
  memcpy (&channels[3], &alpha, 4);
}

/* Special float handling for R10G10B10_6E4_A2
 * https://github.com/microsoft/DirectXTex/blob/main/DirectXTex/DirectXTexConvert.cpp
 */
void
float_from_6e4a2 (guint32 channels[4])
{
  gint64 mantissa;
  gint64 exponent;
  gfloat alpha;

  for (gint ch = 0; ch < 3; ch++)
    {
      mantissa = channels[ch] & 0x0000003F;
      exponent = channels[ch] & 0x000003C0;

      if (exponent != 0)  /* The value is normalized */
        {
          exponent = (channels[ch] >> 6) & 0x0000000F;
        }
      else if (mantissa != 0)  /* The value is denormalized */
        {
          /* Normalize the value in the resulting float */
          exponent = 1;

          do
            {
              exponent--;
              mantissa <<= 1;
            }
          while ((mantissa & 0x40) == 0);

          mantissa &= 0x3F;
        }
      else  /* The value is zero */
        {
          exponent = -120;
        }

      channels[ch] = (guint32) (((exponent + 120) << 23) | (mantissa << 17));
    }
  alpha = (gfloat) channels[3] * (1.0f / 3.0f);
  memcpy (&channels[3], &alpha, 4);
}

/* Special handling for CxV8U8
 * Z-component is reconstructed from X and Y
 */
void
reconstruct_z (guint32 channels[4])
{
  gchar  ch_u, ch_v, ch_c;
  gfloat ch_uf, ch_vf;

  memcpy (&ch_u, &channels[0], 1);
  memcpy (&ch_v, &channels[1], 1);

  ch_uf = (gfloat) ch_u / 127.0f;
  ch_vf = (gfloat) ch_v / 127.0f;
  ch_c =  (gchar) (sqrtf (1.0f - (ch_uf * ch_uf + ch_vf * ch_vf)) * 127.0f);

  memcpy (&channels[2], &ch_c, 1);
}

/*
 * Get input bits-per-pixel from D3D9 format
 */
gsize
get_bpp_d3d9 (guint fmt)
{
  switch (fmt)
    {
    case D3DFMT_A32B32G32R32F:
      return 128;

    case D3DFMT_A16B16G16R16:
    case D3DFMT_Q16W16V16U16:
    case D3DFMT_A16B16G16R16F:
    case D3DFMT_G32R32F:
      return 64;

    case D3DFMT_A8R8G8B8:
    case D3DFMT_X8R8G8B8:
    case D3DFMT_A2B10G10R10:
    case D3DFMT_A8B8G8R8:
    case D3DFMT_X8B8G8R8:
    case D3DFMT_G16R16:
    case D3DFMT_A2R10G10B10:
    case D3DFMT_Q8W8V8U8:
    case D3DFMT_V16U16:
    case D3DFMT_X8L8V8U8:
    case D3DFMT_A2W10V10U10:
    case D3DFMT_D32:
    case D3DFMT_D24S8:
    case D3DFMT_D24X8:
    case D3DFMT_D24X4S4:
    case D3DFMT_D32F_LOCKABLE:
    case D3DFMT_D24FS8:
    case D3DFMT_INDEX32:
    case D3DFMT_G16R16F:
    case D3DFMT_R32F:
    case D3DFMT_D32_LOCKABLE:
      return 32;

    case D3DFMT_R8G8B8:
    case D3DFMT_B8G8R8:
      return 24;

    case D3DFMT_A4R4G4B4:
    case D3DFMT_X4R4G4B4:
    case D3DFMT_R5G6B5:
    case D3DFMT_L16:
    case D3DFMT_A8L8:
    case D3DFMT_X1R5G5B5:
    case D3DFMT_A1R5G5B5:
    case D3DFMT_A8R3G3B2:
    case D3DFMT_V8U8:
    case D3DFMT_CxV8U8:
    case D3DFMT_L6V5U5:
    case D3DFMT_D16_LOCKABLE:
    case D3DFMT_D15S1:
    case D3DFMT_D16:
    case D3DFMT_INDEX16:
    case D3DFMT_R16F:
      return 16;

    case D3DFMT_R3G3B2:
    case D3DFMT_A8:
    case D3DFMT_A8P8:
    case D3DFMT_P8:
    case D3DFMT_L8:
    case D3DFMT_A4L4:
    case D3DFMT_S8_LOCKABLE:
      return 8;

    case D3DFMT_A1:
      return 1;

    default:
      return 0;
  }
}

/*
 * Get input bits-per-pixel from DXGI format
 */
gsize
get_bpp_dxgi (guint fmt)
{
  switch (fmt)
    {
    case DXGI_FORMAT_R32G32B32A32_TYPELESS:
    case DXGI_FORMAT_R32G32B32A32_FLOAT:
    case DXGI_FORMAT_R32G32B32A32_UINT:
    case DXGI_FORMAT_R32G32B32A32_SINT:
      return 128;

    case DXGI_FORMAT_R32G32B32_TYPELESS:
    case DXGI_FORMAT_R32G32B32_FLOAT:
    case DXGI_FORMAT_R32G32B32_UINT:
    case DXGI_FORMAT_R32G32B32_SINT:
      return 96;

    case DXGI_FORMAT_R16G16B16A16_TYPELESS:
    case DXGI_FORMAT_R16G16B16A16_FLOAT:
    case DXGI_FORMAT_R16G16B16A16_UNORM:
    case DXGI_FORMAT_R16G16B16A16_UINT:
    case DXGI_FORMAT_R16G16B16A16_SNORM:
    case DXGI_FORMAT_R16G16B16A16_SINT:
    case DXGI_FORMAT_R32G32_TYPELESS:
    case DXGI_FORMAT_R32G32_FLOAT:
    case DXGI_FORMAT_R32G32_UINT:
    case DXGI_FORMAT_R32G32_SINT:
    case DXGI_FORMAT_R32G8X24_TYPELESS:
    case DXGI_FORMAT_D32_FLOAT_S8X24_UINT:
    case DXGI_FORMAT_R32_FLOAT_X8X24_TYPELESS:
    case DXGI_FORMAT_X32_TYPELESS_G8X24_UINT:
    case DXGI_FORMAT_Y416:
    case DXGI_FORMAT_Y210:
    case DXGI_FORMAT_Y216:
      return 64;

    case DXGI_FORMAT_R10G10B10A2_TYPELESS:
    case DXGI_FORMAT_R10G10B10A2_UNORM:
    case DXGI_FORMAT_R10G10B10A2_UINT:
    case DXGI_FORMAT_R11G11B10_FLOAT:
    case DXGI_FORMAT_R8G8B8A8_TYPELESS:
    case DXGI_FORMAT_R8G8B8A8_UNORM:
    case DXGI_FORMAT_R8G8B8A8_UNORM_SRGB:
    case DXGI_FORMAT_R8G8B8A8_UINT:
    case DXGI_FORMAT_R8G8B8A8_SNORM:
    case DXGI_FORMAT_R8G8B8A8_SINT:
    case DXGI_FORMAT_R16G16_TYPELESS:
    case DXGI_FORMAT_R16G16_FLOAT:
    case DXGI_FORMAT_R16G16_UNORM:
    case DXGI_FORMAT_R16G16_UINT:
    case DXGI_FORMAT_R16G16_SNORM:
    case DXGI_FORMAT_R16G16_SINT:
    case DXGI_FORMAT_R32_TYPELESS:
    case DXGI_FORMAT_D32_FLOAT:
    case DXGI_FORMAT_R32_FLOAT:
    case DXGI_FORMAT_R32_UINT:
    case DXGI_FORMAT_R32_SINT:
    case DXGI_FORMAT_R24G8_TYPELESS:
    case DXGI_FORMAT_D24_UNORM_S8_UINT:
    case DXGI_FORMAT_R24_UNORM_X8_TYPELESS:
    case DXGI_FORMAT_X24_TYPELESS_G8_UINT:
    case DXGI_FORMAT_R9G9B9E5_SHAREDEXP:
    case DXGI_FORMAT_R8G8_B8G8_UNORM:
    case DXGI_FORMAT_G8R8_G8B8_UNORM:
    case DXGI_FORMAT_B8G8R8A8_UNORM:
    case DXGI_FORMAT_B8G8R8X8_UNORM:
    case DXGI_FORMAT_R10G10B10_XR_BIAS_A2_UNORM:
    case DXGI_FORMAT_B8G8R8A8_TYPELESS:
    case DXGI_FORMAT_B8G8R8A8_UNORM_SRGB:
    case DXGI_FORMAT_B8G8R8X8_TYPELESS:
    case DXGI_FORMAT_B8G8R8X8_UNORM_SRGB:
    case DXGI_FORMAT_AYUV:
    case DXGI_FORMAT_Y410:
    case DXGI_FORMAT_YUY2:
    case DXGI_FORMAT_R10G10B10_7E3_A2_FLOAT:
    case DXGI_FORMAT_R10G10B10_6E4_A2_FLOAT:
    case DXGI_FORMAT_R10G10B10_SNORM_A2_UNORM:
      return 32;

    case DXGI_FORMAT_P010:
    case DXGI_FORMAT_P016:
    case DXGI_FORMAT_D16_UNORM_S8_UINT:
    case DXGI_FORMAT_R16_UNORM_X8_TYPELESS:
    case DXGI_FORMAT_X16_TYPELESS_G8_UINT:
    case DXGI_FORMAT_V408:
      return 24;

    case DXGI_FORMAT_R8G8_TYPELESS:
    case DXGI_FORMAT_R8G8_UNORM:
    case DXGI_FORMAT_R8G8_UINT:
    case DXGI_FORMAT_R8G8_SNORM:
    case DXGI_FORMAT_R8G8_SINT:
    case DXGI_FORMAT_R16_TYPELESS:
    case DXGI_FORMAT_R16_FLOAT:
    case DXGI_FORMAT_D16_UNORM:
    case DXGI_FORMAT_R16_UNORM:
    case DXGI_FORMAT_R16_UINT:
    case DXGI_FORMAT_R16_SNORM:
    case DXGI_FORMAT_R16_SINT:
    case DXGI_FORMAT_B5G6R5_UNORM:
    case DXGI_FORMAT_B5G5R5A1_UNORM:
    case DXGI_FORMAT_A8P8:
    case DXGI_FORMAT_B4G4R4A4_UNORM:
    case DXGI_FORMAT_P208:
    case DXGI_FORMAT_V208:
    case DXGI_FORMAT_A4B4G4R4_UNORM:
      return 16;

    case DXGI_FORMAT_NV12:
    case DXGI_FORMAT_420_OPAQUE:
    case DXGI_FORMAT_NV11:
      return 12;

    case DXGI_FORMAT_R8_TYPELESS:
    case DXGI_FORMAT_R8_UNORM:
    case DXGI_FORMAT_R8_UINT:
    case DXGI_FORMAT_R8_SNORM:
    case DXGI_FORMAT_R8_SINT:
    case DXGI_FORMAT_A8_UNORM:
    case DXGI_FORMAT_BC2_TYPELESS:
    case DXGI_FORMAT_BC2_UNORM:
    case DXGI_FORMAT_BC2_UNORM_SRGB:
    case DXGI_FORMAT_BC3_TYPELESS:
    case DXGI_FORMAT_BC3_UNORM:
    case DXGI_FORMAT_BC3_UNORM_SRGB:
    case DXGI_FORMAT_BC5_TYPELESS:
    case DXGI_FORMAT_BC5_UNORM:
    case DXGI_FORMAT_BC5_SNORM:
    case DXGI_FORMAT_BC6H_TYPELESS:
    case DXGI_FORMAT_BC6H_UF16:
    case DXGI_FORMAT_BC6H_SF16:
    case DXGI_FORMAT_BC7_TYPELESS:
    case DXGI_FORMAT_BC7_UNORM:
    case DXGI_FORMAT_BC7_UNORM_SRGB:
    case DXGI_FORMAT_AI44:
    case DXGI_FORMAT_IA44:
    case DXGI_FORMAT_P8:
    case DXGI_FORMAT_R4G4_UNORM:
      return 8;

    case DXGI_FORMAT_BC1_TYPELESS:
    case DXGI_FORMAT_BC1_UNORM:
    case DXGI_FORMAT_BC1_UNORM_SRGB:
    case DXGI_FORMAT_BC4_TYPELESS:
    case DXGI_FORMAT_BC4_UNORM:
    case DXGI_FORMAT_BC4_SNORM:
      return 4;

    case DXGI_FORMAT_R1_UNORM:
      return 1;

    default:
      return 0;
    }
}

/* --- end plug-ins/field-io/file-dds/formats.c --- */

/* --- begin plug-ins/field-io/file-dds/mipmap.c --- */
/*
 * DDS AmmoOS Image plugin
 *
 * Copyright (C) 2004-2012 Shawn Kirst <skirst@gmail.com>,
 * with parts (C) 2003 Arne Reuter <homepage@arnereuter.de> where specified.
 *
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public
 * License as published by the Free Software Foundation; either
 * version 2 of the License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; see the file COPYING.  If not, write to
 * the Free Software Foundation, 51 Franklin Street, Fifth Floor
 * Boston, MA 02110-1301, USA.
 */

#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <float.h>

#include <gtk/gtk.h>

#include <libgimp/ammoos.h>

#ifdef _OPENMP
#include <omp.h>
#endif

#include "dds.h"
#include "mipmap.h"
#include "imath.h"


typedef gfloat (*filterfunc_t)    (gfloat);
typedef gint   (*wrapfunc_t)      (gint, gint);
typedef void   (*mipmapfunc_t)    (guchar*, gint, gint, guchar*, gint, gint, gint,
                                   filterfunc_t, gfloat, wrapfunc_t, gint, gfloat);
typedef void   (*volmipmapfunc_t) (guchar*, gint, gint, gint, guchar*, gint, gint, gint,
                                   gint, filterfunc_t, gfloat, wrapfunc_t, gint, gfloat);


/**
 * Size Functions
 */

gint
get_num_mipmaps (gint  width,
                 gint  height)
{
  gint w = width  << 1;
  gint h = height << 1;
  gint n = 0;

  while (w != 1 || h != 1)
    {
      if (w > 1) w >>= 1;
      if (h > 1) h >>= 1;
      ++n;
    }

  return n;
}

guint
get_mipmapped_size (gint  width,
                    gint  height,
                    gint  bpp,
                    gint  level,
                    gint  num,
                    gint  format)
{
  gint  w, h, n = 0;
  guint size    = 0;

  w = width  >> level;
  h = height >> level;
  w = MAX (1, w);
  h = MAX (1, h);
  w <<= 1;
  h <<= 1;

  while (n < num && (w != 1 || h != 1))
    {
      if (w > 1) w >>= 1;
      if (h > 1) h >>= 1;
      if (format == DDS_COMPRESS_NONE)
        size += (w * h);
      else
        size += ((w + 3) >> 2) * ((h + 3) >> 2);
      ++n;
    }

  if (format == DDS_COMPRESS_NONE)
    {
      size *= bpp;
    }
  else
    {
      if (format == DDS_COMPRESS_BC1 || format == DDS_COMPRESS_BC4)
        size *= 8;
      else
        size *= 16;
    }

  return size;
}

guint
get_volume_mipmapped_size (gint  width,
                           gint  height,
                           gint  depth,
                           gint  bpp,
                           gint  level,
                           gint  num,
                           gint  format)
{
  gint  w, h, d, n = 0;
  guint size       = 0;

  w = width >> level;
  h = height >> level;
  d = depth >> level;
  w = MAX (1, w);
  h = MAX (1, h);
  d = MAX (1, d);
  w <<= 1;
  h <<= 1;
  d <<= 1;

  while (n < num && (w != 1 || h != 1))
    {
      if (w > 1) w >>= 1;
      if (h > 1) h >>= 1;
      if (d > 1) d >>= 1;
      if (format == DDS_COMPRESS_NONE)
        size += (w * h * d);
      else
        size += (((w + 3) >> 2) * ((h + 3) >> 2) * d);
      ++n;
    }

  if (format == DDS_COMPRESS_NONE)
    {
      size *= bpp;
    }
  else
    {
      if (format == DDS_COMPRESS_BC1 || format == DDS_COMPRESS_BC4)
        size *= 8;
      else
        size *= 16;
    }

  return size;
}

gint
get_next_mipmap_dimensions (gint *next_w,
                            gint *next_h,
                            gint  curr_w,
                            gint  curr_h)
{
  if (curr_w == 1 || curr_h == 1)
    return 0;

  if (next_w) *next_w = curr_w >> 1;
  if (next_h) *next_h = curr_h >> 1;

  return 1;
}


/**
 * Wrap Modes
 */

static gint
wrap_mirror (gint  x,
             gint  max)
{
  if (max == 1)
    x = 0;

  x = abs (x);
  while (x >= max)
    x = abs (max + max - x - 2);

  return x;
}

static gint
wrap_repeat (gint  x,
             gint  max)
{
  gfloat t;
  t = (gfloat) x / (gfloat) max;
  return (gint) ((t - floorf (t)) * (gfloat) max);
}

static gint
wrap_clamp (gint  x,
            gint  max)
{
  return MAX (0, MIN (max - 1, x));
}


/**
 * Gamma-correction
 */

static gfloat
linear_to_sRGB (gfloat c)
{
  gfloat v = (gfloat) c;

  if (v < 0.0f)
    v = 0.0f;
  else if (v > 1.0f)
    v = 1.0f;
  else if (v <= 0.0031308f)
    v = 12.92f * v;
  else
    v = 1.055f * powf (v, 0.41666f) - 0.055f;

  return v;
}

static gfloat
linear_to_gamma (gint    gc,
                 gfloat  v,
                 gfloat  gamma)
{
  if (gc == 1)
    {
      v = powf (v, 1.0f / gamma);
      if (v > 1.0f)
        v = 1.0f;
    }
  else if (gc == 2)
    {
      v = linear_to_sRGB (v);
    }

  return v;
}


static gfloat
sRGB_to_linear (gfloat c)
{
  gfloat v = (gfloat) c;

  if (v < 0.0f)
    v = 0.0f;
  else if (v > 1.0f)
    v = 1.0f;
  else if (v <= 0.04045f)
    v /= 12.92f;
  else
    v = powf ((v + 0.055f) / 1.055f, 2.4f);

  return v;
}

static gfloat
gamma_to_linear (gint    gc,
                 gfloat  v,
                 gfloat  gamma)
{
  if (gc == 1)
    {
      v = powf (v, gamma);
      if (v > 1.0f)
        v = 1.0f;
    }
  else if (gc == 2)
    {
      v = sRGB_to_linear (v);
    }

  return v;
}


/**
 * Filters
 */

static gfloat
box_filter (gfloat  t)
{
  if ((t >= -0.5f) && (t < 0.5f))
    return 1.0f;

  return 0.0f;
}

static gfloat
triangle_filter (gfloat  t)
{
  if (t < 0.0f) t = -t;
  if (t < 1.0f) return 1.0f - t;

  return 0.0f;
}

static gfloat
quadratic_filter (gfloat  t)
{
  if (t < 0.0f) t = -t;
  if (t < 0.5f) return 0.75f - t * t;
  if (t < 1.5f)
    {
      t -= 1.5f;
      return 0.5f * t * t;
    }

  return 0.0f;
}

static gfloat
mitchell (gfloat        t,
          const gfloat  B)
{
  gfloat C, tt;

  C  = 0.5f * (1.0f - B);
  tt = t * t;
  if (t < 0.0f)
    t = -t;

  if (t < 1.0f)
    {
      t = (((12.0f - 9.0f * B - 6.0f * C) * (t * tt)) +
           ((-18.0f + 12.0f * B + 6.0f * C) * tt) +
           (6.0f - 2.0f * B));

      return t / 6.0f;
    }
  else if (t < 2.0f)
    {
      t = (((-1.0f * B - 6.0f * C) * (t * tt)) +
           ((6.0f * B + 30.0f * C) * tt) +
           ((-12.0f * B - 48.0f * C) * t) +
           (8.0f * B + 24.0f * C));

      return t / 6.0f;
    }

  return 0.0f;
}

static gfloat
bspline_filter (gfloat  t)
{
  return mitchell (t, 1.0f);
}

static gfloat
mitchell_filter (gfloat  t)
{
  return mitchell (t, 1.0f / 3.0f);
}

static gfloat
catrom_filter (gfloat  t)
{
  return mitchell (t, 0.0f);
}

static gfloat
sinc (gfloat  x)
{
  x = (x * M_PI);
  if (fabsf (x) < 1e-04f)
    return 1.0f + x * x * (-1.0f / 6.0f + x * x * 1.0f / 120.0f);

  return sinf (x) / x;
}

static gfloat
lanczos_filter (gfloat  t)
{
  if (t < 0.0f) t = -t;
  if (t < 3.0f) return sinc (t) * sinc (t / 3.0f);

  return 0.0f;
}

static gfloat
bessel0 (gfloat  x)
{
  const gfloat EPSILON = 1e-6f;
  gfloat xh, sum, pow, ds;
  gint   k;

  xh  = 0.5f * x;
  sum = 1.0f;
  pow = 1.0f;
  k   = 0;
  ds  = 1.0f;

  while (ds > sum * EPSILON)
    {
      ++k;
      pow = pow * (xh / k);
      ds = pow * pow;
      sum += ds;
    }

  return sum;
}

static gfloat
kaiser_filter (gfloat  t)
{
  if (t < 0.0f) t = -t;

  if (t < 3.0f)
    {
      const gfloat alpha = 4.0f;
      const gfloat rb04  = 0.0884805322f; // 1.0f / bessel0(4.0f);
      const gfloat ratio = t / 3.0f;
      if ((1.0f - ratio * ratio) >= 0)
        return sinc (t) * bessel0 (alpha * sqrtf (1.0f - ratio * ratio)) * rb04;
    }

  return 0.0f;
}


/**
 * 2D Scaling
 */

static void
scale_image_nearest (guchar       *dst,
                     gint          dw,
                     gint          dh,
                     guchar       *src,
                     gint          sw,
                     gint          sh,
                     gint          bpp,
                     filterfunc_t  filter,
                     gfloat        support,
                     wrapfunc_t    wrap,
                     gint          gc,
                     gfloat        gamma)
{
  gint n, x, y;
  gint ix, iy;
  gint srowbytes = sw * bpp;
  gint drowbytes = dw * bpp;

  for (y = 0; y < dh; ++y)
    {
      iy = (y * sh + sh / 2) / dh;
      for (x = 0; x < dw; ++x)
        {
          ix = (x * sw + sw / 2) / dw;
          for (n = 0; n < bpp; ++n)
            {
              dst[y * drowbytes + (x * bpp) + n] =
                src[iy * srowbytes + (ix * bpp) + n];
            }
        }
    }
}

static void
scale_image (guchar       *dst,
             gint          dw,
             gint          dh,
             guchar       *src,
             gint          sw,
             gint          sh,
             gint          bpp,
             filterfunc_t  filter,
             gfloat        support,
             wrapfunc_t    wrap,
             gint          gc,
             gfloat        gamma)
{
  const gfloat xfactor = (gfloat) dw / (gfloat) sw;
  const gfloat yfactor = (gfloat) dh / (gfloat) sh;

  gint   x, y, start, stop, nmax, n, i;
  gfloat center, contrib, density, s, r, t;
  gint   sstride  = sw * bpp;
  gfloat xscale   = MIN (xfactor, 1.0f);
  gfloat yscale   = MIN (yfactor, 1.0f);
  gfloat xsupport = support / xscale;
  gfloat ysupport = support / yscale;
  guchar *d, *row, *col;
  guchar *tmp;

  if (xsupport <= 0.5f)
    {
      xsupport = 0.5f + 1e-10f;
      xscale = 1.0f;
    }

  if (ysupport <= 0.5f)
    {
      ysupport = 0.5f + 1e-10f;
      yscale = 1.0f;
    }

#ifdef _OPENMP
  tmp = g_malloc (sw * bpp * omp_get_max_threads ());
#else
  tmp = g_malloc (sw * bpp);
#endif

#ifdef _OPENMP
#pragma omp parallel for schedule(dynamic)                              \
  private(x, y, d, row, col, center, start, stop, nmax, s, i, n, density, r, t, contrib)
#endif
  for (y = 0; y < dh; ++y)
    {
      /* resample in Y direction to temp buffer */
      d = tmp;
#ifdef _OPENMP
      d += (sw * bpp * omp_get_thread_num ());
#endif

      center = ((gfloat) y + 0.5f) / yfactor;
      start = (gint) roundf ((center - ysupport) + 0.5f);
      stop  = (gint) roundf ((center + ysupport) + 0.5f);
      nmax = stop - start;
      s = (gfloat) start - center + 0.5f;

      for (x = 0; x < sw; ++x)
        {
          col = src + (x * bpp);

          for (i = 0; i < bpp; ++i)
            {
              density = 0.0f;
              r = 0.0f;

              for (n = 0; n < nmax; ++n)
                {
                  contrib = filter((s + n) * yscale);
                  density += contrib;
                  if (i == 3)
                    t = (gfloat) col[(wrap (start + n, sh) * sstride) + i] / 255.0f;
                  else
                    t = gamma_to_linear (gc, (gfloat) col[(wrap (start + n, sh) * sstride) + i] / 255.0f, gamma);
                  r += t * contrib;
                }

              if (density != 0.0f && density != 1.0f)
                r /= density;

              r = MIN (1.0f, MAX (0.0f, r));

              if (i != 3)
                r = linear_to_gamma (gc, r, gamma);

              d[(x * bpp) + i] = (guchar) floorf (r * 255.0f + 0.5f);
            }
        }

      /* resample in X direction using temp buffer */
      row = d;
      d = dst;

      for (x = 0; x < dw; ++x)
        {
          center = ((gfloat) x + 0.5f) / xfactor;
          start = (gint) roundf ((center - xsupport) + 0.5f);
          stop  = (gint) roundf ((center + xsupport) + 0.5f);
          nmax = stop - start;
          s = (gfloat) start - center + 0.5f;

          for (i = 0; i < bpp; ++i)
            {
              density = 0.0f;
              r = 0.0f;

              for (n = 0; n < nmax; ++n)
                {
                  contrib = filter((s + n) * xscale);
                  density += contrib;
                  if (i == 3)
                    t = (gfloat) row[(wrap (start + n, sw) * bpp) + i] / 255.0f;
                  else
                    t = gamma_to_linear (gc, (gfloat) row[(wrap (start + n, sw) * bpp) + i] / 255.0f, gamma);
                  r += t * contrib;
                }

              if (density != 0.0f && density != 1.0f)
                r /= density;

              r = MIN (1.0f, MAX (0.0f, r));

              if (i != 3)
                r = linear_to_gamma (gc, r, gamma);

              d[(y * (dw * bpp)) + (x * bpp) + i] = (guchar) floorf (r * 255.0f + 0.5f);
            }
        }
    }

  g_free (tmp);
}


/**
 * 3D Scaling
 */

static void
scale_volume_image_nearest (guchar       *dst,
                            gint          dw,
                            gint          dh,
                            gint          dd,
                            guchar       *src,
                            gint          sw,
                            gint          sh,
                            gint          sd,
                            gint          bpp,
                            filterfunc_t  filter,
                            gfloat        support,
                            wrapfunc_t    wrap,
                            gint          gc,
                            gfloat        gamma)
{
  gint n, x, y, z;
  gint ix, iy, iz;

  for (z = 0; z < dd; ++z)
    {
      iz = (z * sd + sd / 2) / dd;
      for (y = 0; y < dh; ++y)
        {
          iy = (y * sh + sh / 2) / dh;
          for (x = 0; x < dw; ++x)
            {
              ix = (x * sw + sw / 2) / dw;
              for (n = 0; n < bpp; ++n)
                {
                  dst[(z * (dw * dh)) + (y * dw) + (x * bpp) + n] =
                    src[(iz * (sw * sh)) + (iy * sw) + (ix * bpp) + n];
                }
            }
        }
    }
}

static void
scale_volume_image (guchar       *dst,
                    gint          dw,
                    gint          dh,
                    gint          dd,
                    guchar       *src,
                    gint          sw,
                    gint          sh,
                    gint          sd,
                    gint          bpp,
                    filterfunc_t  filter,
                    gfloat        support,
                    wrapfunc_t    wrap,
                    gint          gc,
                    gfloat        gamma)
{
  const gfloat xfactor = (gfloat) dw / (gfloat) sw;
  const gfloat yfactor = (gfloat) dh / (gfloat) sh;
  const gfloat zfactor = (gfloat) dd / (gfloat) sd;

  gint   x, y, z, start, stop, nmax, n, i;
  gfloat center, contrib, density, s, r, t;
  gint   sstride  = sw * bpp;
  gint   zstride  = sh * sw * bpp;
  gfloat xscale   = MIN (xfactor, 1.0f);
  gfloat yscale   = MIN (yfactor, 1.0f);
  gfloat zscale   = MIN (zfactor, 1.0f);
  gfloat xsupport = support / xscale;
  gfloat ysupport = support / yscale;
  gfloat zsupport = support / zscale;
  guchar *d, *row, *col, *slice;
  guchar *tmp1, *tmp2;

  /* down to a 2D image, use the faster 2D image resampler */
  if (dd == 1 && sd == 1)
    {
      scale_image (dst, dw, dh, src, sw, sh, bpp, filter, support, wrap, gc, gamma);
      return;
    }

  if (xsupport <= 0.5f)
    {
      xsupport = 0.5f + 1e-10f;
      xscale = 1.0f;
    }

  if (ysupport <= 0.5f)
    {
      ysupport = 0.5f + 1e-10f;
      yscale = 1.0f;
    }

  if (zsupport <= 0.5f)
    {
      zsupport = 0.5f + 1e-10f;
      zscale = 1.0f;
    }

  tmp1 = g_malloc (sh * sw * bpp);
  tmp2 = g_malloc (dh * sw * bpp);

  for (z = 0; z < dd; ++z)
    {
      /* resample in Z direction */
      d = tmp1;

      center = ((gfloat) z + 0.5f) / zfactor;
      start = (gint) roundf ((center - zsupport) + 0.5f);
      stop =  (gint) roundf ((center + zsupport) + 0.5f);
      nmax = stop - start;
      s = (gfloat) start - center + 0.5f;

#ifdef _OPENMP
#pragma omp parallel for schedule(dynamic)                      \
  private(x, y, slice, i, n, density, r, t, contrib)
#endif
      for (y = 0; y < sh; ++y)
        {
          for (x = 0; x < sw; ++x)
            {
              slice = src + (y * (sw * bpp)) + (x * bpp);

              for (i = 0; i < bpp; ++i)
                {
                  density = 0.0f;
                  r = 0.0f;

                  for (n = 0; n < nmax; ++n)
                    {
                      contrib = filter((s + n) * zscale);
                      density += contrib;
                      if (i == 3)
                        t = (gfloat) slice[(wrap (start + n, sd) * zstride) + i] / 255.0f;
                      else
                        t = gamma_to_linear (gc, (gfloat) slice[(wrap (start + n, sd) * zstride) + i] / 255.0f, gamma);
                      r += t * contrib;
                    }

                  if (density != 0.0f && density != 1.0f)
                    r /= density;

                  r = MIN (1.0f, MAX (0.0f, r));

                  if (i != 3)
                    r = linear_to_gamma (gc, r, gamma);

                  d[((y * sw) + x) * bpp + i] = (guchar) floorf (r * 255.0f + 0.5f);
                }
            }
        }

      /* resample in Y direction */
      d = tmp2;
#ifdef _OPENMP
#pragma omp parallel for schedule(dynamic)                              \
  private(x, y, col, center, start, stop, nmax, s, i, n, density, r, t, contrib)
#endif
      for (y = 0; y < dh; ++y)
        {
          center = ((gfloat) y + 0.5f) / yfactor;
          start = (gint) roundf ((center - ysupport) + 0.5f);
          stop =  (gint) roundf ((center + ysupport) + 0.5f);
          nmax = stop - start;
          s = (gfloat) start - center + 0.5f;

          for (x = 0; x < sw; ++x)
            {
              col = tmp1 + (x * bpp);

              for (i = 0; i < bpp; ++i)
                {
                  density = 0.0f;
                  r = 0.0f;

                  for (n = 0; n < nmax; ++n)
                    {
                      contrib = filter((s + n) * yscale);
                      density += contrib;
                      if (i == 3)
                        t = (gfloat) col[(wrap (start + n, sh) * sstride) + i] / 255.0f;
                      else
                        t = gamma_to_linear (gc, (gfloat) col[(wrap (start + n, sh) * sstride) + i] / 255.0f, gamma);
                      r += t * contrib;
                    }

                  if (density != 0.0f && density != 1.0f)
                    r /= density;

                  r = MIN (1.0f, MAX (0.0f, r));

                  if (i != 3)
                    r = linear_to_gamma (gc, r, gamma);

                  d[((y * sw) + x) * bpp + i] = (guchar) floorf (r * 255.0f + 0.5f);
                }
            }
        }

      /* resample in X direction */
      d = dst;
#ifdef _OPENMP
#pragma omp parallel for schedule(dynamic)                              \
  private(x, y, row, center, start, stop, nmax, s, i, n, density, r, t, contrib)
#endif
      for (y = 0; y < dh; ++y)
        {
          row = tmp2 + (y * sstride);

          for (x = 0; x < dw; ++x)
            {
              center = ((gfloat) x + 0.5f) / xfactor;
              start = (gint) roundf ((center - xsupport) + 0.5f);
              stop =  (gint) roundf ((center + xsupport) + 0.5f);
              nmax = stop - start;
              s = (gfloat) start - center + 0.5f;

              for (i = 0; i < bpp; ++i)
                {
                  density = 0.0f;
                  r = 0.0f;

                  for (n = 0; n < nmax; ++n)
                    {
                      contrib = filter((s + n) * xscale);
                      density += contrib;
                      if (i == 3)
                        t = (gfloat) row[(wrap (start + n, sw) * bpp) + i] / 255.0f;
                      else
                        t = gamma_to_linear (gc, (gfloat) row[(wrap (start + n, sw) * bpp) + i] / 255.0f, gamma);
                      r += t * contrib;
                    }

                  if (density != 0.0f && density != 1.0f)
                    r /= density;

                  r = MIN (1.0f, MAX (0.0f, r));

                  if (i != 3)
                    r = linear_to_gamma (gc, r, gamma);

                  d[((z * dh * dw) + (y * dw) + x) * bpp + i] = (guchar) floorf (r * 255.0f + 0.5f);
                }
            }
        }
    }

  g_free (tmp1);
  g_free (tmp2);
}


/**
 * Filter Lookup-table
 */

static struct
{
  gint         filter;
  filterfunc_t func;
  gfloat       support;
} filters[] =
{
  { DDS_MIPMAP_FILTER_BOX,       box_filter,       0.5f },
  { DDS_MIPMAP_FILTER_TRIANGLE,  triangle_filter,  1.0f },
  { DDS_MIPMAP_FILTER_QUADRATIC, quadratic_filter, 1.5f },
  { DDS_MIPMAP_FILTER_BSPLINE,   bspline_filter,   2.0f },
  { DDS_MIPMAP_FILTER_MITCHELL,  mitchell_filter,  2.0f },
  { DDS_MIPMAP_FILTER_CATROM,    catrom_filter,    2.0f },
  { DDS_MIPMAP_FILTER_LANCZOS,   lanczos_filter,   3.0f },
  { DDS_MIPMAP_FILTER_KAISER,    kaiser_filter,    3.0f },
  { DDS_MIPMAP_FILTER_MAX,       NULL,             0.0f }
};


/**
 * Alpha-test Coverage - portion of visible texels after alpha test:
 * if (texel_alpha < alpha_test_threshold) discard;
 */

static gfloat
calc_alpha_test_coverage (guchar *src,
                          guint   width,
                          guint   height,
                          gint    bpp,
                          gfloat  alpha_test_threshold,
                          gfloat  alpha_scale)
{
  const gint alpha_channel_idx = 3;
  gint  rowbytes = width * bpp;
  gint  coverage = 0;
  guint x, y;

  if (bpp <= alpha_channel_idx)
    {
      /* No alpha channel */
      return 1.0f;
    }

  for (y = 0; y < height; ++y)
    {
      for (x = 0; x < width; ++x)
        {
          const gfloat alpha = src[y * rowbytes + (x * bpp) + alpha_channel_idx];
          if ((alpha * alpha_scale) >= (alpha_test_threshold * 255))
            {
              ++coverage;
            }
        }
    }

  return (gfloat) coverage / (width * height);
}

static void
scale_alpha_to_coverage (guchar *img,
                         guint   width,
                         guint   height,
                         gint    bpp,
                         gfloat  desired_coverage,
                         gfloat  alpha_test_threshold)
{
  const gint rowbytes          = width * bpp;
  const gint alpha_channel_idx = 3;
  gfloat     min_alpha_scale   = 0.0f;
  gfloat     max_alpha_scale   = 4.0f;
  gfloat     alpha_scale       = 1.0f;
  guint      x, y;
  gint       i;

  if (bpp <= alpha_channel_idx)
    {
      /* No alpha channel */
      return;
    }

  /* Binary search */
  for (i = 0; i < 10; i++)
    {
      gfloat cur_coverage = calc_alpha_test_coverage (img, width, height, bpp, alpha_test_threshold, alpha_scale);

      if (cur_coverage < desired_coverage)
        {
          min_alpha_scale = alpha_scale;
        }
      else if (cur_coverage > desired_coverage)
        {
          max_alpha_scale = alpha_scale;
        }
      else
        {
          break;
        }

      alpha_scale = (min_alpha_scale + max_alpha_scale) / 2;
    }

  /* Scale alpha channel */
  for (y = 0; y < height; ++y)
    {
      for (x = 0; x < width; ++x)
        {
          gfloat new_alpha = img[y * rowbytes + (x * bpp) + alpha_channel_idx] * alpha_scale;
          if (new_alpha > 255.0f)
            {
              new_alpha = 255.0f;
            }

          img[y * rowbytes + (x * bpp) + alpha_channel_idx] = (guchar) new_alpha;
        }
    }
}


/**
 * Mipmap Generation
 */

gint
generate_mipmaps (guchar *dst,
                  guchar *src,
                  guint   width,
                  guint   height,
                  gint    bpp,
                  gint    indexed,
                  gint    mipmaps,
                  gint    filter,
                  gint    wrap,
                  gint    gc,
                  gfloat  gamma,
                  gint    preserve_alpha_coverage,
                  gfloat  alpha_test_threshold)
{
  const gint   has_alpha   = (bpp >= 3);
  mipmapfunc_t mipmap_func = NULL;
  filterfunc_t filter_func = NULL;
  wrapfunc_t   wrap_func   = NULL;
  gfloat       coverage    = 1.0f;
  gfloat       support     = 0.0f;
  guint        sw, sh, dw, dh;
  guchar      *s, *d;
  gint         i;

  if (indexed || filter == DDS_MIPMAP_FILTER_NEAREST)
    {
      mipmap_func = scale_image_nearest;
    }
  else
    {
      if ((filter < DDS_MIPMAP_FILTER_NEAREST) ||
          (filter >= DDS_MIPMAP_FILTER_MAX))
        filter = DDS_MIPMAP_FILTER_BOX;

      mipmap_func = scale_image;

      for (i = 0; filters[i].filter != DDS_MIPMAP_FILTER_MAX; ++i)
        {
          if (filter == filters[i].filter)
            {
              filter_func = filters[i].func;
              support = filters[i].support;
              break;
            }
        }
    }

  switch (wrap)
    {
    case DDS_MIPMAP_WRAP_MIRROR: wrap_func = wrap_mirror; break;
    case DDS_MIPMAP_WRAP_REPEAT: wrap_func = wrap_repeat; break;
    case DDS_MIPMAP_WRAP_CLAMP:  wrap_func = wrap_clamp;  break;
    default:                     wrap_func = wrap_clamp;  break;
    }

  if (has_alpha && preserve_alpha_coverage)
    {
      coverage = calc_alpha_test_coverage (src, width, height, bpp,
                                           alpha_test_threshold,
                                           1.0f);
    }

  memcpy (dst, src, width * height * bpp);

  s = dst;
  d = dst + (width * height * bpp);

  dw = sw = width;
  dh = sh = height;

  for (i = 1; i < mipmaps; ++i)
    {
      dw = MAX (1, dw >> 1);
      dh = MAX (1, dh >> 1);

      mipmap_func (d, dw, dh, s, sw, sh, bpp, filter_func, support, wrap_func, gc, gamma);

      if (has_alpha && preserve_alpha_coverage)
        {
          scale_alpha_to_coverage (d, dw, dh, bpp, coverage, alpha_test_threshold);
        }

      s = d;
      sw = dw;
      sh = dh;
      d += (dw * dh * bpp);
    }

  return 1;
}

gint
generate_volume_mipmaps (guchar *dst,
                         guchar *src,
                         guint   width,
                         guint   height,
                         guint   depth,
                         gint    bpp,
                         gint    indexed,
                         gint    mipmaps,
                         gint    filter,
                         gint    wrap,
                         gint    gc,
                         gfloat  gamma)
{
  volmipmapfunc_t mipmap_func = NULL;
  filterfunc_t    filter_func = NULL;
  wrapfunc_t      wrap_func   = NULL;
  gfloat          support     = 0.0f;
  guint           sw, sh, sd;
  guint           dw, dh, dd;
  guchar         *s, *d;
  gint            i;

  if (indexed || filter == DDS_MIPMAP_FILTER_NEAREST)
    {
      mipmap_func = scale_volume_image_nearest;
    }
  else
    {
      if ((filter < DDS_MIPMAP_FILTER_NEAREST) ||
          (filter >= DDS_MIPMAP_FILTER_MAX))
        filter = DDS_MIPMAP_FILTER_BOX;

      mipmap_func = scale_volume_image;

      for (i = 0; filters[i].filter != DDS_MIPMAP_FILTER_MAX; ++i)
        {
          if (filter == filters[i].filter)
            {
              filter_func = filters[i].func;
              support = filters[i].support;
              break;
            }
        }
    }

  switch (wrap)
    {
    case DDS_MIPMAP_WRAP_MIRROR: wrap_func = wrap_mirror; break;
    case DDS_MIPMAP_WRAP_REPEAT: wrap_func = wrap_repeat; break;
    case DDS_MIPMAP_WRAP_CLAMP:  wrap_func = wrap_clamp;  break;
    default:                     wrap_func = wrap_clamp;  break;
    }

  memcpy (dst, src, width * height * depth * bpp);

  s = dst;
  d = dst + (width * height * depth * bpp);

  sw = width;
  sh = height;
  sd = depth;

  for (i = 1; i < mipmaps; ++i)
    {
      dw = MAX (1, sw >> 1);
      dh = MAX (1, sh >> 1);
      dd = MAX (1, sd >> 1);

      mipmap_func (d, dw, dh, dd, s, sw, sh, sd, bpp, filter_func, support, wrap_func, gc, gamma);

      s = d;
      sw = dw;
      sh = dh;
      sd = dd;
      d += (dw * dh * dd * bpp);
    }

  return 1;
}

/* --- end plug-ins/field-io/file-dds/mipmap.c --- */

/* --- begin plug-ins/field-io/file-dds/misc.c --- */
/*
 * DDS AmmoOS Image plugin
 *
 * Copyright (C) 2004-2012 Shawn Kirst <skirst@gmail.com>,
 * with parts (C) 2003 Arne Reuter <homepage@arnereuter.de> where specified.
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

#include "config.h"

#include <libgimp/ammoos.h>

#include <libgimp/stdplugins-intl.h>

#include "endian_rw.h"
#include "imath.h"
#include "misc.h"


/*
 * Decoding Functions
 */

static inline gfloat
saturate (gfloat a)
{
  if (a < 0) a = 0;
  if (a > 1) a = 1;
  return a;
}

void
decode_ycocg (GimpDrawable *drawable)
{
  GeglBuffer   *buffer;
  const Babl   *format;
  guchar       *data;
  guint         num_pixels;
  guint         i, w, h;
  const gfloat  offset = 0.5f * 256.0f / 255.0f;
  gfloat        Y, Co, Cg;
  gfloat        R, G, B;

  buffer = gimp_drawable_get_buffer (drawable);

  format = babl_format ("R'G'B'A u8");

  w = gegl_buffer_get_width  (buffer);
  h = gegl_buffer_get_height (buffer);
  num_pixels = w * h;

  data = g_malloc (num_pixels * 4);

  gegl_buffer_get (buffer, GEGL_RECTANGLE (0, 0, w, h), 1.0, format, data,
                   GEGL_AUTO_ROWSTRIDE, GEGL_ABYSS_NONE);

  /* Translators: Do not translate YCoCg, it's the name of a colorspace */
  gimp_progress_init (_("Decoding YCoCg pixels..."));

  for (i = 0; i < num_pixels; ++i)
    {
      Y  = (gfloat) data[4 * i + 3] / 255.0f;
      Co = (gfloat) data[4 * i + 0] / 255.0f;
      Cg = (gfloat) data[4 * i + 1] / 255.0f;

      /* convert YCoCg to RGB */
      Co -= offset;
      Cg -= offset;

      R = saturate (Y + Co - Cg);
      G = saturate (Y + Cg);
      B = saturate (Y - Co - Cg);

      /* copy new alpha from blue */
      data[4 * i + 3] = data[4 * i + 2];

      data[4 * i + 0] = (guchar) (R * 255.0f);
      data[4 * i + 1] = (guchar) (G * 255.0f);
      data[4 * i + 2] = (guchar) (B * 255.0f);

      if ((i & 0x7fff) == 0)
        gimp_progress_update ((gdouble) i / (gdouble) num_pixels);
    }

  gegl_buffer_set (buffer, GEGL_RECTANGLE (0, 0, w, h), 0, format, data,
                   GEGL_AUTO_ROWSTRIDE);

  gimp_progress_update (1.0);

  gegl_buffer_flush (buffer);

  gimp_drawable_update (drawable, 0, 0, w, h);

  g_free (data);

  g_object_unref (buffer);
}

void
decode_ycocg_scaled (GimpDrawable *drawable)
{
  GeglBuffer   *buffer;
  const Babl   *format;
  guchar       *data;
  guint         num_pixels;
  guint         i, w, h;
  const gfloat  offset = 0.5f * 256.0f / 255.0f;
  gfloat        Y, Co, Cg;
  gfloat        R, G, B, s;

  buffer = gimp_drawable_get_buffer (drawable);

  format = babl_format ("R'G'B'A u8");

  w = gegl_buffer_get_width  (buffer);
  h = gegl_buffer_get_height (buffer);
  num_pixels = w * h;

  data = g_malloc (num_pixels * 4);

  gegl_buffer_get (buffer, GEGL_RECTANGLE (0, 0, w, h), 1.0, format, data,
                   GEGL_AUTO_ROWSTRIDE, GEGL_ABYSS_NONE);
                   
  /* Translators: Do not translate YCoCg, it's the name of a colorspace */
  gimp_progress_init (_("Decoding YCoCg (scaled) pixels..."));

  for (i = 0; i < num_pixels; ++i)
    {
      Y  = (gfloat) data[4 * i + 3] / 255.0f;
      Co = (gfloat) data[4 * i + 0] / 255.0f;
      Cg = (gfloat) data[4 * i + 1] / 255.0f;
      s  = (gfloat) data[4 * i + 2] / 255.0f;

      /* convert YCoCg to RGB */
      s = 1.0f / ((255.0f / 8.0f) * s + 1.0f);

      Co = (Co - offset) * s;
      Cg = (Cg - offset) * s;

      R = saturate (Y + Co - Cg);
      G = saturate (Y + Cg);
      B = saturate (Y - Co - Cg);

      data[4 * i + 0] = (guchar) (R * 255.0f);
      data[4 * i + 1] = (guchar) (G * 255.0f);
      data[4 * i + 2] = (guchar) (B * 255.0f);

      /* set alpha to 1 */
      data[4 * i + 3] = 255;

      if ((i & 0x7fff) == 0)
        gimp_progress_update ((gdouble) i / (gdouble) num_pixels);
    }

  gegl_buffer_set (buffer, GEGL_RECTANGLE (0, 0, w, h), 0, format, data,
                   GEGL_AUTO_ROWSTRIDE);

  gimp_progress_update (1.0);

  gegl_buffer_flush (buffer);

  gimp_drawable_update (drawable, 0, 0, w, h);

  g_free (data);

  g_object_unref (buffer);
}

void
decode_alpha_exponent (GimpDrawable *drawable)
{
  GeglBuffer *buffer;
  const Babl *format;
  guchar     *data;
  guint       num_pixels;
  guint       i, w, h;
  gint        R, G, B, A;

  buffer = gimp_drawable_get_buffer (drawable);

  format = babl_format ("R'G'B'A u8");

  w = gegl_buffer_get_width  (buffer);
  h = gegl_buffer_get_height (buffer);
  num_pixels = w * h;

  data = g_malloc (num_pixels * 4);

  gegl_buffer_get (buffer, GEGL_RECTANGLE (0, 0, w, h), 1.0, format, data,
                   GEGL_AUTO_ROWSTRIDE, GEGL_ABYSS_NONE);

  gimp_progress_init (_("Decoding Alpha-exponent pixels..."));

  for (i = 0; i < num_pixels; ++i)
    {
      R = data[4 * i + 0];
      G = data[4 * i + 1];
      B = data[4 * i + 2];
      A = data[4 * i + 3];

      R = (R * A + 1) >> 8;
      G = (G * A + 1) >> 8;
      B = (B * A + 1) >> 8;
      A = 255;

      data[4 * i + 0] = R;
      data[4 * i + 1] = G;
      data[4 * i + 2] = B;
      data[4 * i + 3] = A;

      if ((i & 0x7fff) == 0)
        gimp_progress_update ((gdouble) i / (gdouble) num_pixels);
    }

  gegl_buffer_set (buffer, GEGL_RECTANGLE (0, 0, w, h), 0, format, data,
                   GEGL_AUTO_ROWSTRIDE);

  gimp_progress_update (1.0);

  gegl_buffer_flush (buffer);

  gimp_drawable_update (drawable, 0, 0, w, h);

  g_free (data);

  g_object_unref (buffer);
}


/*
 * Encoding Functions
 */

void
encode_ycocg (guchar *dst,
              gint    r,
              gint    g,
              gint    b)
{
  gint y  = ((r +     (g << 1) + b) + 2) >> 2;
  gint co = ((((r << 1) - (b << 1)) + 2) >> 2) + 128;
  gint cg = (((-r +   (g << 1) - b) + 2) >> 2) + 128;

  dst[0] = 255;
  dst[1] = (cg > 255 ? 255 : (cg < 0 ? 0 : cg));
  dst[2] = (co > 255 ? 255 : (co < 0 ? 0 : co));
  dst[3] = (y  > 255 ? 255 : (y  < 0 ? 0 :  y));
}

void
encode_alpha_exponent (guchar *dst,
                       gint    r,
                       gint    g,
                       gint    b,
                       gint    a)
{
  gfloat ar, ag, ab, aa;

  ar = (gfloat) r / 255.0f;
  ag = (gfloat) g / 255.0f;
  ab = (gfloat) b / 255.0f;

  aa = MAX (ar, MAX (ag, ab));

  if (aa < 1e-04f)
    {
      dst[0] = b;
      dst[1] = g;
      dst[2] = r;
      dst[3] = 255;
      return;
    }

  ar /= aa;
  ag /= aa;
  ab /= aa;

  r = (gint) floorf (255.0f * ar + 0.5f);
  g = (gint) floorf (255.0f * ag + 0.5f);
  b = (gint) floorf (255.0f * ab + 0.5f);
  a = (gint) floorf (255.0f * aa + 0.5f);

  dst[0] = MAX (0, MIN (255, b));
  dst[1] = MAX (0, MIN (255, g));
  dst[2] = MAX (0, MIN (255, r));
  dst[3] = MAX (0, MIN (255, a));
}


/*
 * Compression Functions
 */

static void
get_min_max_YCoCg (const guchar *block,
                   guchar       *mincolor,
                   guchar       *maxcolor)
{
  gint i;

  mincolor[2] = mincolor[1] = 255;
  maxcolor[2] = maxcolor[1] = 0;

  for (i = 0; i < 16; ++i)
    {
      if (block[4 * i + 2] < mincolor[2]) mincolor[2] = block[4 * i + 2];
      if (block[4 * i + 1] < mincolor[1]) mincolor[1] = block[4 * i + 1];
      if (block[4 * i + 2] > maxcolor[2]) maxcolor[2] = block[4 * i + 2];
      if (block[4 * i + 1] > maxcolor[1]) maxcolor[1] = block[4 * i + 1];
    }
}

static void
scale_YCoCg (guchar *block,
             guchar *mincolor,
             guchar *maxcolor)
{
  const gint s0 = 128 / 2 - 1;
  const gint s1 = 128 / 4 - 1;
  gint       m0, m1, m2, m3;
  gint       mask0, mask1, scale;
  gint       i;

  m0 = abs (mincolor[2] - 128);
  m1 = abs (mincolor[1] - 128);
  m2 = abs (maxcolor[2] - 128);
  m3 = abs (maxcolor[1] - 128);

  if (m1 > m0) m0 = m1;
  if (m3 > m2) m2 = m3;
  if (m2 > m0) m0 = m2;

  mask0 = -(m0 <= s0);
  mask1 = -(m0 <= s1);
  scale = 1 + (1 & mask0) + (2 & mask1);

  mincolor[2] = (mincolor[2] - 128) * scale + 128;
  mincolor[1] = (mincolor[1] - 128) * scale + 128;
  mincolor[0] = (scale - 1) << 3;

  maxcolor[2] = (maxcolor[2] - 128) * scale + 128;
  maxcolor[1] = (maxcolor[1] - 128) * scale + 128;
  maxcolor[0] = (scale - 1) << 3;

  for (i = 0; i < 16; ++i)
    {
      block[i * 4 + 2] = (block[i * 4 + 2] - 128) * scale + 128;
      block[i * 4 + 1] = (block[i * 4 + 1] - 128) * scale + 128;
    }
}

#define INSET_SHIFT  4

static void
inset_bbox_YCoCg (guchar *mincolor,
                  guchar *maxcolor)
{
  gint inset[4], mini[4], maxi[4];

  inset[2] = (maxcolor[2] - mincolor[2]) - ((1 << (INSET_SHIFT - 1)) - 1);
  inset[1] = (maxcolor[1] - mincolor[1]) - ((1 << (INSET_SHIFT - 1)) - 1);

  mini[2] = ((mincolor[2] << INSET_SHIFT) + inset[2]) >> INSET_SHIFT;
  mini[1] = ((mincolor[1] << INSET_SHIFT) + inset[1]) >> INSET_SHIFT;

  maxi[2] = ((maxcolor[2] << INSET_SHIFT) - inset[2]) >> INSET_SHIFT;
  maxi[1] = ((maxcolor[1] << INSET_SHIFT) - inset[1]) >> INSET_SHIFT;

  mini[2] = (mini[2] >= 0) ? mini[2] : 0;
  mini[1] = (mini[1] >= 0) ? mini[1] : 0;

  maxi[2] = (maxi[2] <= 255) ? maxi[2] : 255;
  maxi[1] = (maxi[1] <= 255) ? maxi[1] : 255;

  mincolor[2] = (mini[2] & 0xf8) | (mini[2] >> 5);
  mincolor[1] = (mini[1] & 0xfc) | (mini[1] >> 6);

  maxcolor[2] = (maxi[2] & 0xf8) | (maxi[2] >> 5);
  maxcolor[1] = (maxi[1] & 0xfc) | (maxi[1] >> 6);
}

static void
select_diagonal_YCoCg (const guchar *block,
                       guchar       *mincolor,
                       guchar       *maxcolor)
{
  guchar mid0, mid1, side, mask, b0, b1, c0, c1;
  gint   i;

  mid0 = ((gint) mincolor[2] + maxcolor[2] + 1) >> 1;
  mid1 = ((gint) mincolor[1] + maxcolor[1] + 1) >> 1;

  side = 0;
  for (i = 0; i < 16; ++i)
    {
      b0 = block[i * 4 + 2] >= mid0;
      b1 = block[i * 4 + 1] >= mid1;
      side += (b0 ^ b1);
    }

  mask  = -(side > 8);
  mask &= -(mincolor[2] != maxcolor[2]);

  c0 = mincolor[1];
  c1 = maxcolor[1];

  c0 ^= c1;
  c1 ^= c0 & mask;
  c0 ^= c1;

  mincolor[1] = c0;
  maxcolor[1] = c1;
}

void
encode_YCoCg_block (guchar *dst,
                    guchar *block)
{
  guchar colors[4][3], *maxcolor, *mincolor;
  guint  mask;
  gint   c0, c1, d0, d1, d2, d3;
  gint   b0, b1, b2, b3, b4;
  gint   x0, x1, x2;
  gint   i, idx;

  maxcolor = &colors[0][0];
  mincolor = &colors[1][0];

  get_min_max_YCoCg (block, mincolor, maxcolor);
  scale_YCoCg (block, mincolor, maxcolor);
  inset_bbox_YCoCg (mincolor, maxcolor);
  select_diagonal_YCoCg (block, mincolor, maxcolor);

  colors[2][0] = (2 * maxcolor[0] + mincolor[0]) / 3;
  colors[2][1] = (2 * maxcolor[1] + mincolor[1]) / 3;
  colors[2][2] = (2 * maxcolor[2] + mincolor[2]) / 3;

  colors[3][0] = (2 * mincolor[0] + maxcolor[0]) / 3;
  colors[3][1] = (2 * mincolor[1] + maxcolor[1]) / 3;
  colors[3][2] = (2 * mincolor[2] + maxcolor[2]) / 3;

  mask = 0;

  for (i = 0; i < 16; ++i)
    {
      c0 = block[4 * i + 2];
      c1 = block[4 * i + 1];

      d0 = abs (colors[0][2] - c0) + abs (colors[0][1] - c1);
      d1 = abs (colors[1][2] - c0) + abs (colors[1][1] - c1);
      d2 = abs (colors[2][2] - c0) + abs (colors[2][1] - c1);
      d3 = abs (colors[3][2] - c0) + abs (colors[3][1] - c1);

      b0 = d0 > d3;
      b1 = d1 > d2;
      b2 = d0 > d2;
      b3 = d1 > d3;
      b4 = d2 > d3;

      x0 = b1 & b2;
      x1 = b0 & b3;
      x2 = b0 & b4;

      idx = (x2 | ((x0 | x1) << 1));

      mask |= idx << (2 * i);
    }

  PUTL16 (dst + 0, (mul8bit (maxcolor[2], 31) << 11) |
                   (mul8bit (maxcolor[1], 63) <<  5) |
                   (mul8bit (maxcolor[0], 31)      ));
  PUTL16 (dst + 2, (mul8bit (mincolor[2], 31) << 11) |
                   (mul8bit (mincolor[1], 63) <<  5) |
                   (mul8bit (mincolor[0], 31)      ));
  PUTL32 (dst + 4, mask);
}

/* --- end plug-ins/field-io/file-dds/misc.c --- */

/* --- begin plug-ins/field-io/file-exr/file-exr.c --- */
/* AmmoOS Image - The AmmoOS Field Image Research
 * Copyright (C) 1995 Spencer Kimball and Peter Mattis
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

#include "config.h"

#include <libgimp/ammoos.h>
#include <libgimp/gimpui.h>

#include "libgimp/stdplugins-intl.h"

#include "openexr-wrapper.h"

#define LOAD_PROC       "file-exr-load"
#define PLUG_IN_BINARY  "file-exr"
#define PLUG_IN_VERSION "0.0.0"


typedef struct _Exr      Exr;
typedef struct _ExrClass ExrClass;

struct _Exr
{
  GimpPlugIn      parent_instance;
};

struct _ExrClass
{
  GimpPlugInClass parent_class;
};


#define EXR_TYPE  (exr_get_type ())
#define EXR(obj) (G_TYPE_CHECK_INSTANCE_CAST ((obj), EXR_TYPE, Exr))

GType                   exr_get_type         (void) G_GNUC_CONST;

static GList          * exr_query_procedures (GimpPlugIn            *plug_in);
static GimpProcedure  * exr_create_procedure (GimpPlugIn            *plug_in,
                                              const gchar           *name);

static GimpValueArray * exr_load             (GimpProcedure         *procedure,
                                              GimpRunMode            run_mode,
                                              GFile                 *file,
                                              GimpMetadata          *metadata,
                                              GimpMetadataLoadFlags *flags,
                                              GimpProcedureConfig   *config,
                                              gpointer               run_data);

static GimpImage      * load_image           (GFile                 *file,
                                              GimpMetadata          *metadata,
                                              GimpMetadataLoadFlags *flags,
                                              gboolean               interactive,
                                              GError               **error);
static void             sanitize_comment     (gchar                 *comment);
void                    load_dialog          (EXRImageType           image_type);


G_DEFINE_TYPE (Exr, exr, GIMP_TYPE_PLUG_IN)

GIMP_MAIN (EXR_TYPE)
DEFINE_STD_SET_I18N


static void
exr_class_init (ExrClass *klass)
{
  GimpPlugInClass *plug_in_class = GIMP_PLUG_IN_CLASS (klass);

  plug_in_class->query_procedures = exr_query_procedures;
  plug_in_class->create_procedure = exr_create_procedure;
  plug_in_class->set_i18n         = STD_SET_I18N;
}

static void
exr_init (Exr *exr)
{
}

static GList *
exr_query_procedures (GimpPlugIn *plug_in)
{
  return g_list_append (NULL, g_strdup (LOAD_PROC));
}

static GimpProcedure *
exr_create_procedure (GimpPlugIn  *plug_in,
                      const gchar *name)
{
  GimpProcedure *procedure = NULL;

  if (! strcmp (name, LOAD_PROC))
    {
      procedure = gimp_load_procedure_new (plug_in, name,
                                           GIMP_PDB_PROC_TYPE_PLUGIN,
                                           exr_load, NULL, NULL);

      gimp_procedure_set_menu_label (procedure, _("OpenEXR image"));

      gimp_procedure_set_documentation (procedure,
                                        _("Loads files in the OpenEXR file format"),
                                        "This plug-in loads OpenEXR files. ",
                                        name);
      gimp_procedure_set_attribution (procedure,
                                      "Dominik Ernst <dernst@gmx.de>, "
                                      "Mukund Sivaraman <muks@banu.com>",
                                      "Dominik Ernst <dernst@gmx.de>, "
                                      "Mukund Sivaraman <muks@banu.com>",
                                      NULL);

      gimp_file_procedure_set_mime_types (GIMP_FILE_PROCEDURE (procedure),
                                          "image/x-exr");
      gimp_file_procedure_set_extensions (GIMP_FILE_PROCEDURE (procedure),
                                          "exr");
      gimp_file_procedure_set_magics (GIMP_FILE_PROCEDURE (procedure),
                                      "0,long,0x762f3101");
    }

  return procedure;
}

static GimpValueArray *
exr_load (GimpProcedure         *procedure,
          GimpRunMode            run_mode,
          GFile                 *file,
          GimpMetadata          *metadata,
          GimpMetadataLoadFlags *flags,
          GimpProcedureConfig   *config,
          gpointer               run_data)
{
  GimpValueArray *return_vals;
  GimpImage      *image;
  GError         *error  = NULL;

  gegl_init (NULL, NULL);

  image = load_image (file, metadata, flags, run_mode == GIMP_RUN_INTERACTIVE,
                      &error);

  if (! image)
    return gimp_procedure_new_return_values (procedure,
                                             GIMP_PDB_EXECUTION_ERROR,
                                             error);

  return_vals =  gimp_procedure_new_return_values (procedure,
                                                   GIMP_PDB_SUCCESS,
                                                   NULL);

  GIMP_VALUES_SET_IMAGE (return_vals, 1, image);

  return return_vals;
}

static GimpImage *
load_image (GFile                 *file,
            GimpMetadata          *metadata,
            GimpMetadataLoadFlags *flags,
            gboolean               interactive,
            GError               **error)
{
  EXRLoader        *loader;
  gint              width;
  gint              height;
  gboolean          has_alpha;
  GimpImageBaseType image_type;
  GimpPrecision     image_precision;
  GimpImage        *image = NULL;
  GimpImageType     layer_type;
  gint              layer_count = 0;
  gboolean          layers_only;
  const Babl       *format;
  gint              bpp;
  gint              tile_height;
  gchar            *pixels = NULL;
  gint              begin;
  gint32            success = FALSE;
  gchar            *comment = NULL;
  GimpColorProfile *profile = NULL;
  guchar           *exif_data;
  guint             exif_size;
  guchar           *xmp_data;
  guint             xmp_size;

  gimp_progress_init_printf (_("Opening '%s'"),
                             gimp_file_get_utf8_name (file));

  loader = exr_loader_new (g_file_peek_path (file));

  if (! loader)
    {
      g_set_error (error, G_FILE_ERROR, G_FILE_ERROR_FAILED,
                   _("Error opening file '%s'"),
                   gimp_file_get_utf8_name (file));
      goto out;
    }

  width  = exr_loader_get_width (loader);
  height = exr_loader_get_height (loader);

  if (width < 1 || height < 1 ||
      width > GIMP_MAX_IMAGE_SIZE || height > GIMP_MAX_IMAGE_SIZE)
    {
      g_set_error (error, G_FILE_ERROR, G_FILE_ERROR_FAILED,
                   _("Error querying image dimensions from '%s'"),
                   gimp_file_get_utf8_name (file));
      goto out;
    }

  has_alpha = exr_loader_has_alpha (loader) ? TRUE : FALSE;

  switch (exr_loader_get_precision (loader))
    {
    case PREC_UINT:
      image_precision = GIMP_PRECISION_U32_LINEAR;
      break;
    case PREC_HALF:
      image_precision = GIMP_PRECISION_HALF_LINEAR;
      break;
    case PREC_FLOAT:
      image_precision = GIMP_PRECISION_FLOAT_LINEAR;
      break;
    default:
      g_set_error (error, G_FILE_ERROR, G_FILE_ERROR_FAILED,
                   _("Error querying image precision from '%s'"),
                   gimp_file_get_utf8_name (file));
      goto out;
    }

  switch (exr_loader_get_image_type (loader))
    {
    case IMAGE_TYPE_RGB:
    case IMAGE_TYPE_YUV:
      image_type = GIMP_RGB;
      layer_type = has_alpha ? GIMP_RGBA_IMAGE : GIMP_RGB_IMAGE;
      break;
    case IMAGE_TYPE_GRAY:
    case IMAGE_TYPE_UNKNOWN_1_CHANNEL:
      image_type = GIMP_GRAY;
      layer_type = has_alpha ? GIMP_GRAYA_IMAGE : GIMP_GRAY_IMAGE;
      break;
    default:
      g_set_error (error, G_FILE_ERROR, G_FILE_ERROR_FAILED,
                   _("Error querying image type from '%s'"),
                   gimp_file_get_utf8_name (file));
      goto out;
    }

  image = gimp_image_new_with_precision (width, height,
                                         image_type, image_precision);
  if (! image)
    {
      g_set_error (error, 0, 0,
                   _("Could not create new image for '%s': %s"),
                   gimp_file_get_utf8_name (file),
                   gimp_pdb_get_last_error (gimp_get_pdb ()));
      goto out;
    }

  if (interactive                                                         &&
      (exr_loader_get_image_type (loader) == IMAGE_TYPE_UNKNOWN_1_CHANNEL))
    load_dialog (exr_loader_get_image_type (loader));

  /* try to load an icc profile, it will be generated on the fly if
   * chromaticities are given
   */
  if (image_type == GIMP_RGB)
    {
      profile = exr_loader_get_profile (loader);

      if (profile)
        gimp_image_set_color_profile (image, profile);
    }

  exr_loader_get_layer_info (loader, &layer_count, &layers_only);

  /* i == -1 represents an image with no named layers, just raw channels.
   * If layers_only is TRUE, there are only named layers and we skip these
   * entirely and just read the layers */
  for (gint i = (-1 + layers_only); i < layer_count; i++)
    {
      GimpLayer  *layer;
      GeglBuffer *buffer     = NULL;
      gchar      *layer_name = NULL;

      if (i > -1)
        layer_name = exr_loader_get_layer_name (loader, i);
      else
        layer_name = _("Background");

      layer = gimp_layer_new (image, layer_name, width, height,
                              layer_type, 100,
                              gimp_image_get_default_new_layer_mode (image));
      gimp_image_insert_layer (image, layer, NULL, -1);

      if (i > -1)
        g_free (layer_name);

      buffer = gimp_drawable_get_buffer (GIMP_DRAWABLE (layer));
      format = gimp_drawable_get_format (GIMP_DRAWABLE (layer));
      bpp = babl_format_get_bytes_per_pixel (format);

      tile_height = gimp_tile_height ();
      pixels = g_new0 (gchar, tile_height * width * bpp);

      for (begin = 0; begin < height; begin += tile_height)
        {
          gint end;
          gint num;

          end = MIN (begin + tile_height, height);
          num = end - begin;

          for (gint j = 0; j < num; j++)
            {
              gint retval;

              retval = exr_loader_read_pixel_row (loader,
                                                  pixels + (j * width * bpp),
                                                  bpp, begin + j, i);
              if (retval < 0)
                {
                  g_set_error (error, G_FILE_ERROR, G_FILE_ERROR_FAILED,
                               _("Error reading pixel data from '%s'"),
                               gimp_file_get_utf8_name (file));
                  goto out;
                }
            }

          gegl_buffer_set (buffer, GEGL_RECTANGLE (0, begin, width, num),
                           0, NULL, pixels, GEGL_AUTO_ROWSTRIDE);

          gimp_progress_update ((gdouble) begin / (gdouble) height);
        }

      g_clear_object (&buffer);
      g_clear_pointer (&pixels, g_free);
    }

  /* try to read the file comment */
  comment = exr_loader_get_comment (loader);
  if (comment)
    {
      GimpParasite *parasite;

      sanitize_comment (comment);
      parasite = gimp_parasite_new ("ammoos-comment",
                                    GIMP_PARASITE_PERSISTENT,
                                    strlen (comment) + 1,
                                    comment);
      gimp_image_attach_parasite (image, parasite);
      gimp_parasite_free (parasite);
    }

  /* check if the image contains Exif or Xmp data and read it */
  exif_data = exr_loader_get_exif (loader, &exif_size);
  xmp_data  = exr_loader_get_xmp  (loader, &xmp_size);

  if (metadata && (exif_data || xmp_data))
    {
      if (exif_data)
        {
          GError *error = NULL;

          if (! gimp_metadata_set_from_exif (metadata, exif_data, exif_size, &error))
            {
              g_message (_("Failed to load metadata: %s"),
                         error ? error->message : _("Unknown reason"));
              g_clear_error (&error);
            }

          g_free (exif_data);
        }

      if (xmp_data)
        {
          GError *error = NULL;

          if (! gimp_metadata_set_from_xmp (metadata, xmp_data, xmp_size, &error))
            {
              g_message (_("Failed to load metadata: %s"),
                         error ? error->message : _("Unknown reason"));
              g_clear_error (&error);
            }
          g_free (xmp_data);
        }

      if (comment)
        *flags &= ~GIMP_METADATA_LOAD_COMMENT;

      if (profile)
        *flags &= ~GIMP_METADATA_LOAD_COLORSPACE;

    }

  gimp_progress_update (1.0);

  success = TRUE;

 out:
  g_clear_object (&profile);
  g_clear_pointer (&comment, g_free);
  g_clear_pointer (&loader, exr_loader_unref);

  if (success)
    return image;

  if (image)
    gimp_image_delete (image);

  return NULL;
}

/* copy & pasted from file-jpeg/jpeg-load.c */
static void
sanitize_comment (gchar *comment)
{
  const gchar *start_invalid;

  if (! g_utf8_validate (comment, -1, &start_invalid))
    {
      guchar *c;

      for (c = (guchar *) start_invalid; *c; c++)
        {
          if (*c > 126 || (*c < 32 && *c != '\t' && *c != '\n' && *c != '\r'))
            *c = '?';
        }
    }
}

void
load_dialog (EXRImageType image_type)
{
  GtkWidget *dialog;
  GtkWidget *label;
  GtkWidget *vbox;
  gchar     *label_text = NULL;

  gimp_ui_init (PLUG_IN_BINARY);

  dialog = gimp_dialog_new (_("Import OpenEXR"),
                            "openexr-notice",
                            NULL, 0, NULL, NULL,
                            _("_OK"), GTK_RESPONSE_OK,
                            NULL);

  gimp_window_set_transient (GTK_WINDOW (dialog));

  vbox = gtk_box_new (GTK_ORIENTATION_VERTICAL, 2);
  gtk_container_set_border_width (GTK_CONTAINER (vbox), 12);
  gtk_box_pack_start (GTK_BOX (gtk_dialog_get_content_area (GTK_DIALOG (dialog))),
                      vbox, TRUE, TRUE, 0);
  gtk_widget_set_visible (vbox, TRUE);

  if (image_type == IMAGE_TYPE_UNKNOWN_1_CHANNEL)
    label_text = g_strdup_printf ("<b>%s</b>\n%s", _("Unknown Channel Name"),
                                  _("The image contains a single unknown channel.\n"
                                    "It has been converted to grayscale."));

  label = gtk_label_new (NULL);
  gtk_label_set_markup (GTK_LABEL (label), label_text);

  gtk_label_set_selectable (GTK_LABEL (label), TRUE);
  gtk_label_set_justify (GTK_LABEL (label), GTK_JUSTIFY_LEFT);
  gtk_label_set_line_wrap (GTK_LABEL (label), TRUE);
  gtk_label_set_yalign (GTK_LABEL (label), 0.0);
  gtk_box_pack_start (GTK_BOX (vbox), label, TRUE, TRUE, 0);
  gtk_widget_set_visible (label, TRUE);

  if (label_text)
    g_free (label_text);

  gtk_widget_set_visible (dialog, TRUE);

  /* run the dialog */
  gimp_dialog_run (GIMP_DIALOG (dialog));

  gtk_widget_destroy (dialog);
}

/* --- end plug-ins/field-io/file-exr/file-exr.c --- */

/* --- begin plug-ins/field-io/file-exr/openexr-wrapper.cc --- */
/* AmmoOS Image - The AmmoOS Field Image Research
 * Copyright (C) 1995 Spencer Kimball and Peter Mattis
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

#include "config.h"

#include <string>

/*  These libgimp includes are not needed here at all, but this is a
 *  convenient place to make sure the public libgimp headers are
 *  C++-clean. The C++ compiler will choke on stuff like naming
 *  a struct member or parameter "private".
 */
#include "libgimp/ammoos.h"
#include "libgimp/gimpui.h"
#include "libgimpbase/gimpbase.h"
#include "libgimpmath/gimpmath.h"
#include "libgimpcolor/gimpcolor.h"
#include "libgimpconfig/gimpconfig.h"
#include "libgimpmodule/gimpmodule.h"
#include "libgimpthumb/gimpthumb.h"
#include "libgimpwidgets/gimpwidgets.h"

#if defined(__MINGW32__)
#ifndef FLT_EPSILON
#define FLT_EPSILON  __FLT_EPSILON__
#endif
#ifndef DBL_EPSILON
#define DBL_EPSILON  __DBL_EPSILON__
#endif
#ifndef LDBL_EPSILON
#define LDBL_EPSILON __LDBL_EPSILON__
#endif
#endif

/* ignore deprecated warnings from OpenEXR headers */
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wdeprecated"

#include <lcms2.h>

#include <ImfInputFile.h>
#include <ImfChannelList.h>
#include <ImfRgbaFile.h>
#include <ImfArray.h>
#include <ImfRgbaYca.h>
#include <ImfStandardAttributes.h>

#pragma GCC diagnostic pop

#include "exr-attribute-blob.h"
#include "openexr-wrapper.h"

using namespace Imf;
using namespace Imf::RgbaYca;
using namespace Imath;

static bool XYZ_equal (cmsCIEXYZ *a, cmsCIEXYZ *b)
{
  static const double epsilon = 0.0001;
  /* Y is encoding the luminance, we normalize that for comparison */
  return fabs ((a->X / a->Y * b->Y) - b->X) < epsilon &&
         fabs ((a->Y / a->Y * b->Y) - b->Y) < epsilon &&
         fabs ((a->Z / a->Y * b->Y) - b->Z) < epsilon;
}

struct _EXRLoader
{
  _EXRLoader (const char* filename) :
    refcount_ (1),
    file_ (filename),
    rgbaInputFile_ (filename),
    data_window_ (file_.header ().dataWindow ()),
    channels_ (file_.header ().channels ())
  {
    std::set<string> layerNames;
    bool             loaded;

    channels_.layers (layerNames);
    layers_only_ = false;
    layer_count_ = layerNames.size ();

    loaded = initializeImage (false);

    /* The OpenEXR image may have named layers only, not loose channels.
     * In that case, we need to go through each layer name and append it
     * to the call for findChannel () */
    if (! loaded)
      {
        layers_only_ = true;

        for (std::set<std::string>::const_iterator i = layerNames.begin ();
             i != layerNames.end (); ++i)
          {
            loaded = initializeImage (true, *i + ".");

            if (loaded)
              break;
          }
      }
  }

  bool initializeImage (bool               has_layers,
                        const std::string &prefix = "")
  {
    const Channel* chan;

    can_load_ = true;

    /* Capitalization matters - channel "R" and "r" are both red,
     * but unless you use the specific one mentioned in the file,
     * it won't load. */
    if (channels_.findChannel (prefix + "R") ||
        channels_.findChannel (prefix + "G") ||
        channels_.findChannel (prefix + "B") ||
        channels_.findChannel (prefix + "r") ||
        channels_.findChannel (prefix + "g") ||
        channels_.findChannel (prefix + "b"))
      {
        format_string_ = "RGB";
        image_type_ = IMAGE_TYPE_RGB;

        if ((chan = channels_.findChannel (prefix + "R")) ||
            (chan = channels_.findChannel (prefix + "r")))
          pt_ = chan->type;
        else if ((chan = channels_.findChannel (prefix + "G")) ||
                 (chan = channels_.findChannel (prefix + "g")))
          pt_ = chan->type;
        else if ((chan = channels_.findChannel (prefix + "B")) ||
                 (chan = channels_.findChannel (prefix + "b")))
          pt_ = chan->type;
      }
    else if (channels_.findChannel (prefix + "Y") &&
             (channels_.findChannel (prefix + "RY") ||
              channels_.findChannel (prefix + "BY")))
      {
        format_string_ = "RGB";
        image_type_ = IMAGE_TYPE_YUV;

        pt_ = channels_.findChannel (prefix + "Y")->type;
      }
    else if (channels_.findChannel (prefix + "Y") ||
             channels_.findChannel (prefix + "y"))
      {
        format_string_ = "Y";
        image_type_ = IMAGE_TYPE_GRAY;

        if ((chan = channels_.findChannel (prefix + "Y")) ||
            (chan = channels_.findChannel (prefix + "y")))
          pt_ = chan->type;
      }
    else
      {
        int         channel_count = 0;
        const char *channel_name  = NULL;

        for (ChannelList::ConstIterator i = channels_.begin ();
             i != channels_.end (); ++i)
          {
            channel_count++;

            pt_ = i.channel ().type;
            channel_name = i.name ();
          }

       /* Assume single channel images are grayscale,
        * no matter what the channel name is. */
        if (channel_count == 1)
          {
            format_string_ = channel_name;
            image_type_ = IMAGE_TYPE_UNKNOWN_1_CHANNEL;
            unknown_channel_name_ = channel_name;

            /* TODO: Pass this information back so it can be displayed
             * in the UI. */
            printf ("OpenEXR Warning: Single channel image with unknown "
                    "channel %s, loading as grayscale\n", channel_name);
          }
        else
          {
            /* TODO: After string freeze ends add unsupported type notice. */
            can_load_ = false;
          }
      }

    if (channels_.findChannel (prefix + "A"))
      {
        format_string_.append (prefix + "A");
        has_alpha_ = true;
      }
    else if (channels_.findChannel (prefix + "a"))
      {
        format_string_.append (prefix + "a");
        has_alpha_ = true;
      }
    else
      {
        has_alpha_ = false;
      }

    switch (pt_)
      {
      case UINT:
        format_string_.append (" u32");
        bpc_ = 4;
        break;
      case HALF:
        format_string_.append (" half");
        bpc_ = 2;
        break;
      case FLOAT:
      default:
        format_string_.append (" float");
        bpc_ = 4;
      }

    return can_load_;
  }

  int readPixelRow (char *pixels,
                   int   bpp,
                   int   row,
                   int   layer_index)
  {
    const int        actual_row = data_window_.min.y + row;
    FrameBuffer      fb;
    std::set<string> layerNames;
    std::string      prefix     = "";
    /* This is necessary because OpenEXR expects the buffer to begin at
     * (0, 0). Though it probably results in some unmapped address,
     * hopefully OpenEXR will not make use of it. :/ */
    char* base = pixels - (data_window_.min.x * bpp);

    if (layer_index > -1)
      {
        channels_.layers (layerNames);

        prefix = *std::next (layerNames.begin (), layer_index) + ".";
      }

    switch (image_type_)
      {
      case IMAGE_TYPE_UNKNOWN_1_CHANNEL:
        fb.insert (unknown_channel_name_, Slice (pt_, base, bpp, 0, 1, 1, 0.5));
        break;

      case IMAGE_TYPE_YUV:
        {
           int width = getWidth();
           Array<Rgba> row_buffer (width);

           rgbaInputFile_.setFrameBuffer (&row_buffer[0] - data_window_.min.x,
                                          1,
                                          0);

          rgbaInputFile_.readPixels (actual_row, actual_row);

          for (int i = 0; i < width; i++)
            {
              half *pixel = (half *)(base + (i * bpp));
              pixel[0] = row_buffer[i].r;
              pixel[1] = row_buffer[i].g;
              pixel[2] = row_buffer[i].b;
              if (hasAlpha ())
                {
                  pixel[3] = row_buffer[i].a;
                }
            }
            /* return early to skip the file_.setFrameBuffer() and
             * file_.readPixels() calls below, which are used by the
             * RGB and GRAY cases.
             * YUV reading is handled entirely by rgbaInputFile_ above. */
            return 0;
        }
      case IMAGE_TYPE_GRAY:
        if (channels_.findChannel (prefix + "Y"))
          {
            fb.insert (prefix + "Y", Slice (pt_, base, bpp, 0, 1, 1, 0.5));
            if (hasAlpha ())
              {
                fb.insert (prefix + "A", Slice (pt_, base + bpc_, bpp, 0, 1, 1, 1.0));
              }
          }
        else
          {
            {
              fb.insert (prefix + "y", Slice (pt_, base, bpp, 0, 1, 1, 0.5));
              if (hasAlpha())
                {
                  fb.insert (prefix + "a", Slice (pt_, base + bpc_, bpp, 0, 1, 1, 1.0));
                }
            }
          }
        break;

      case IMAGE_TYPE_RGB:
      default:
        if (channels_.findChannel (prefix + "R"))
          {
            fb.insert (prefix + "R", Slice (pt_, base + (bpc_ * 0), bpp, 0, 1, 1, 0.0));
            fb.insert (prefix + "G", Slice (pt_, base + (bpc_ * 1), bpp, 0, 1, 1, 0.0));
            fb.insert (prefix + "B", Slice (pt_, base + (bpc_ * 2), bpp, 0, 1, 1, 0.0));
            if (hasAlpha ())
              {
                fb.insert (prefix + "A", Slice (pt_, base + (bpc_ * 3), bpp, 0, 1, 1, 1.0));
              }
          }
        else
          {
            fb.insert (prefix + "r", Slice (pt_, base + (bpc_ * 0), bpp, 0, 1, 1, 0.0));
            fb.insert (prefix + "g", Slice (pt_, base + (bpc_ * 1), bpp, 0, 1, 1, 0.0));
            fb.insert (prefix + "b", Slice (pt_, base + (bpc_ * 2), bpp, 0, 1, 1, 0.0));
            if (hasAlpha ())
              {
                fb.insert (prefix + "a", Slice (pt_, base + (bpc_ * 3), bpp, 0, 1, 1, 1.0));
              }
          }
      }

    file_.setFrameBuffer (fb);
    file_.readPixels (actual_row);

    return 0;
  }

  int getWidth () const {
    return data_window_.max.x - data_window_.min.x + 1;
  }

  int getHeight () const {
    return data_window_.max.y - data_window_.min.y + 1;
  }

  EXRPrecision getPrecision () const {
    EXRPrecision prec;

    switch (pt_)
      {
      case UINT:
        prec = PREC_UINT;
        break;
      case HALF:
        prec = PREC_HALF;
        break;
      case FLOAT:
      default:
        prec = PREC_FLOAT;
      }

    return prec;
  }

  EXRImageType getImageType () const {
    return image_type_;
  }

  int hasAlpha () const {
    return has_alpha_ ? 1 : 0;
  }

  int canLoad () const {
    return can_load_ ? 1 : 0;
  }

  GimpColorProfile *getProfile () const {
    Chromaticities chromaticities;
    float whiteLuminance = 1.0;

    GimpColorProfile *linear_srgb_profile;
    cmsHPROFILE linear_srgb_lcms;

    GimpColorProfile *profile;
    cmsHPROFILE lcms_profile;

    cmsCIEXYZ *gimp_r_XYZ, *gimp_g_XYZ, *gimp_b_XYZ, *gimp_w_XYZ;
    cmsCIEXYZ exr_r_XYZ, exr_g_XYZ, exr_b_XYZ, exr_w_XYZ;

    /* get the color information from the EXR */
    if (hasChromaticities (file_.header ()))
      chromaticities = Imf::chromaticities (file_.header ());
    else
      return NULL;

    if (Imf::hasWhiteLuminance (file_.header ()))
      whiteLuminance = Imf::whiteLuminance (file_.header ());
    else
      return NULL;

#if 0
    std::cout << "hasChromaticities: "
              << hasChromaticities (file_.header ())
              << std::endl;
    std::cout << "hasWhiteLuminance: "
              << hasWhiteLuminance (file_.header ())
              << std::endl;
    std::cout << whiteLuminance << std::endl;
    std::cout << chromaticities.red << std::endl;
    std::cout << chromaticities.green << std::endl;
    std::cout << chromaticities.blue << std::endl;
    std::cout << chromaticities.white << std::endl;
    std::cout << std::endl;
#endif

    cmsCIExyY whitePoint = { chromaticities.white.x,
                             chromaticities.white.y,
                             whiteLuminance };
    cmsCIExyYTRIPLE CameraPrimaries = { { chromaticities.red.x,
                                          chromaticities.red.y,
                                          whiteLuminance },
                                        { chromaticities.green.x,
                                          chromaticities.green.y,
                                          whiteLuminance },
                                        { chromaticities.blue.x,
                                          chromaticities.blue.y,
                                          whiteLuminance } };

    /* get the primaries + wp from AmmoOS Image's internal linear sRGB profile */
    linear_srgb_profile = gimp_color_profile_new_rgb_srgb_linear ();
    linear_srgb_lcms = gimp_color_profile_get_lcms_profile (linear_srgb_profile);

    gimp_r_XYZ = (cmsCIEXYZ *) cmsReadTag (linear_srgb_lcms, cmsSigRedColorantTag);
    gimp_g_XYZ = (cmsCIEXYZ *) cmsReadTag (linear_srgb_lcms, cmsSigGreenColorantTag);
    gimp_b_XYZ = (cmsCIEXYZ *) cmsReadTag (linear_srgb_lcms, cmsSigBlueColorantTag);
    gimp_w_XYZ = (cmsCIEXYZ *) cmsReadTag (linear_srgb_lcms, cmsSigMediaWhitePointTag);

    cmsxyY2XYZ (&exr_r_XYZ, &CameraPrimaries.Red);
    cmsxyY2XYZ (&exr_g_XYZ, &CameraPrimaries.Green);
    cmsxyY2XYZ (&exr_b_XYZ, &CameraPrimaries.Blue);
    cmsxyY2XYZ (&exr_w_XYZ, &whitePoint);

    /* ... and check if the data stored in the EXR matches AmmoOS Image's internal profile */
    bool exr_is_linear_srgb = XYZ_equal (&exr_r_XYZ, gimp_r_XYZ) &&
                              XYZ_equal (&exr_g_XYZ, gimp_g_XYZ) &&
                              XYZ_equal (&exr_b_XYZ, gimp_b_XYZ) &&
                              XYZ_equal (&exr_w_XYZ, gimp_w_XYZ);

    /* using AmmoOS Image's linear sRGB profile allows to skip the conversion popup */
    if (exr_is_linear_srgb)
      return linear_srgb_profile;

    /* nope, it's something else. Clean up and build a new profile */
    g_object_unref (linear_srgb_profile);

    /* TODO: maybe factor this out into libgimpcolor/gimpcolorprofile.h ? */
    double Parameters[2] = { 1.0, 0.0 };
    cmsToneCurve *Gamma[3];
    Gamma[0] = Gamma[1] = Gamma[2] = cmsBuildParametricToneCurve(0,
                                                                 1,
                                                                 Parameters);
    lcms_profile = cmsCreateRGBProfile (&whitePoint, &CameraPrimaries, Gamma);
    cmsFreeToneCurve (Gamma[0]);
    if (lcms_profile == NULL) return NULL;

    /* cmsSetProfileVersion (lcms_profile, 2.1); */
    cmsMLU *mlu0 = cmsMLUalloc (NULL, 1);
    cmsMLUsetASCII (mlu0, "en", "US", "(AmmoOS Image internal)");
    cmsMLU *mlu1 = cmsMLUalloc(NULL, 1);
    cmsMLUsetASCII (mlu1, "en", "US", "color profile from EXR chromaticities");
    cmsMLU *mlu2 = cmsMLUalloc(NULL, 1);
    cmsMLUsetASCII (mlu2, "en", "US", "color profile from EXR chromaticities");
    cmsWriteTag (lcms_profile, cmsSigDeviceMfgDescTag, mlu0);
    cmsWriteTag (lcms_profile, cmsSigDeviceModelDescTag, mlu1);
    cmsWriteTag (lcms_profile, cmsSigProfileDescriptionTag, mlu2);
    cmsMLUfree (mlu0);
    cmsMLUfree (mlu1);
    cmsMLUfree (mlu2);

    profile = gimp_color_profile_new_from_lcms_profile (lcms_profile,
                                                        NULL);
    cmsCloseProfile (lcms_profile);

    return profile;
  }

  gchar *getComment () const {
    char *result = NULL;
    const Imf::StringAttribute *comment = file_.header ().findTypedAttribute<Imf::StringAttribute>("comment");
    if (comment)
      result = g_strdup (comment->value().c_str());
    return result;
  }

  guchar *getExif (guint *size) const {
    guchar jpeg_exif[] = "Exif\0\0";
    guchar *exif_data = NULL;
    *size = 0;

    const Imf::BlobAttribute *exif = file_.header ().findTypedAttribute<Imf::BlobAttribute>("exif");

    if (exif)
      {
        exif_data = (guchar *)(exif->value ().data.get ());
        *size = exif->value ().size;
        /* darktable 4.0.0 and earlier appended a jpg-compatible exif00 string,
         * so get rid of that again. We explicitly reduce the size by 1 since
         * the compiler adds an extra \0 to the end of jpeg_exif. */
        if ( ! memcmp (jpeg_exif, exif_data, sizeof (jpeg_exif)-1))
          {
            *size -= 6;
            exif_data += 6;
          }
      }

    return (guchar *)g_memdup2 (exif_data, *size);
  }

  guchar *getXmp (guint *size) const {
    guchar *result = NULL;
    *size = 0;
    const Imf::StringAttribute *xmp = file_.header ().findTypedAttribute<Imf::StringAttribute>("xmp");
    if (xmp)
      {
        *size = xmp->value ().size ();
        result = (guchar *) g_memdup2 (xmp->value().data(), *size);
      }
    return result;
  }

  gchar *getLayerName (int index) const {
    gchar *result = NULL;

    if (index > -1 && index < layer_count_)
      {
        std::set<string> layerNames;
        std::string      name;

        channels_.layers (layerNames);

        name   = *std::next (layerNames.begin(), index);
        result = (gchar *) g_memdup2 (name.c_str(),
                                      name.size() + 1);
      }
    return result;
  }

  int getLayerInfo (gint *num_layers, int *layers_only) const {
    *num_layers  = layer_count_;
    *layers_only = layers_only_;

    return 1;
  }

  size_t refcount_;
  InputFile file_;
  RgbaInputFile rgbaInputFile_;
  const Box2i data_window_;
  const ChannelList& channels_;
  PixelType pt_;
  int bpc_;
  EXRImageType image_type_;
  bool has_alpha_;
  bool layers_only_;
  int  layer_count_;
  bool can_load_;
  std::string format_string_;
  std::string unknown_channel_name_;
};

EXRLoader*
exr_loader_new (const char *filename)
{
  EXRLoader* file;

  /* Don't let any exceptions propagate to the C layer. */
  try
    {
      Imf::BlobAttribute::registerAttributeType();
      file = new EXRLoader (filename);

      if (file && ! file->canLoad ())
        {
          exr_loader_unref (file);
          file = NULL;
        }
    }
  catch (...)
    {
      file = NULL;
    }

  return file;
}

EXRLoader*
exr_loader_ref (EXRLoader *loader)
{
  ++loader->refcount_;
  return loader;
}

void
exr_loader_unref (EXRLoader *loader)
{
  if (--loader->refcount_ == 0)
    {
      delete loader;
    }
}

int
exr_loader_get_width (EXRLoader *loader)
{
  int width;
  /* Don't let any exceptions propagate to the C layer. */
  try
    {
      width = loader->getWidth ();
    }
  catch (...)
    {
      width = -1;
    }

  return width;
}

int
exr_loader_get_height (EXRLoader *loader)
{
  int height;
  /* Don't let any exceptions propagate to the C layer. */
  try
    {
      height = loader->getHeight ();
    }
  catch (...)
    {
      height = -1;
    }

  return height;
}

EXRImageType
exr_loader_get_image_type (EXRLoader *loader)
{
  /* This does not throw. */
  return loader->getImageType ();
}

EXRPrecision
exr_loader_get_precision (EXRLoader *loader)
{
  /* This does not throw. */
  return loader->getPrecision ();
}

int
exr_loader_has_alpha (EXRLoader *loader)
{
  /* This does not throw. */
  return loader->hasAlpha ();
}

GimpColorProfile *
exr_loader_get_profile (EXRLoader *loader)
{
  return loader->getProfile ();
}

gchar *
exr_loader_get_comment (EXRLoader *loader)
{
  return loader->getComment ();
}

guchar *
exr_loader_get_exif (EXRLoader *loader,
                     guint *size)
{
  return loader->getExif (size);
}

guchar *
exr_loader_get_xmp (EXRLoader *loader,
                    guint *size)
{
  return loader->getXmp (size);
}

gchar *
exr_loader_get_layer_name (EXRLoader  *loader,
                           gint        index)
{
  return loader->getLayerName (index);
}

int
exr_loader_get_layer_info (EXRLoader *loader,
                           gint      *num_layers,
                           gboolean  *layers_only)
{
  return loader->getLayerInfo (num_layers, layers_only);
}

int
exr_loader_read_pixel_row (EXRLoader *loader,
                           char      *pixels,
                           int        bpp,
                           int        row,
                           int        layer_index)
{
  int retval = -1;
  /* Don't let any exceptions propagate to the C layer. */
  try
    {
      retval = loader->readPixelRow (pixels, bpp, row, layer_index);
    }
  catch (...)
    {
      retval = -1;
    }

  return retval;
}

/* --- end plug-ins/field-io/file-exr/openexr-wrapper.cc --- */

/* --- begin plug-ins/field-io/file-faxg3/faxg3.c --- */
/* This is a plugin for AmmoOS Image.
 *
 * Copyright (C) 1997 Jochen Friedrich
 * Parts Copyright (C) 1995 Gert Doering
 * Parts Copyright (C) 1995 Spencer Kimball and Peter Mattis
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

#include "config.h"

#include <errno.h>
#include <string.h>

#ifdef HAVE_UNISTD_H
#include <unistd.h>
#endif

#include <sys/types.h>
#include <fcntl.h>

#include <glib.h> /* For G_OS_WIN32 */
#include <glib/gstdio.h>

#ifdef G_OS_WIN32
#include <io.h>
#define read _read
#define close _close
#define lseek _lseek
#endif

#ifndef _O_BINARY
#define _O_BINARY 0
#endif

#include <libgimp/ammoos.h>

#include "g3.h"

#include "libgimp/stdplugins-intl.h"


#define LOAD_PROC "file-faxg3-load"
#define VERSION   "0.6"


typedef struct _Faxg3      Faxg3;
typedef struct _Faxg3Class Faxg3Class;

struct _Faxg3
{
  GimpPlugIn      parent_instance;
};

struct _Faxg3Class
{
  GimpPlugInClass parent_class;
};


#define FAXG3_TYPE  (faxg3_get_type ())
#define FAXG3 (obj) (G_TYPE_CHECK_INSTANCE_CAST ((obj), FAXG3_TYPE, Faxg3))

GType                   faxg3_get_type         (void) G_GNUC_CONST;

static GList          * faxg3_query_procedures (GimpPlugIn            *plug_in);
static GimpProcedure  * faxg3_create_procedure (GimpPlugIn            *plug_in,
                                                const gchar           *name);

static GimpValueArray * faxg3_load             (GimpProcedure         *procedure,
                                                GimpRunMode            run_mode,
                                                GFile                 *file,
                                                GimpMetadata          *metadata,
                                                GimpMetadataLoadFlags *flags,
                                                GimpProcedureConfig   *config,
                                                gpointer               run_data);

static GimpImage      * load_image             (GFile                 *file,
                                                GError               **error);

static GimpImage      *  emitgimp              (gint                   hcol,
                                                gint                   row,
                                                const gchar           *bitmap,
                                                gint                   bperrow,
                                                GFile                 *file,
                                                GError               **error);


G_DEFINE_TYPE (Faxg3, faxg3, GIMP_TYPE_PLUG_IN)

GIMP_MAIN (FAXG3_TYPE)
DEFINE_STD_SET_I18N


static void
faxg3_class_init (Faxg3Class *klass)
{
  GimpPlugInClass *plug_in_class = GIMP_PLUG_IN_CLASS (klass);

  plug_in_class->query_procedures = faxg3_query_procedures;
  plug_in_class->create_procedure = faxg3_create_procedure;
  plug_in_class->set_i18n         = STD_SET_I18N;
}

static void
faxg3_init (Faxg3 *faxg3)
{
}

static GList *
faxg3_query_procedures (GimpPlugIn *plug_in)
{
  return  g_list_append (NULL, g_strdup (LOAD_PROC));
}

static GimpProcedure *
faxg3_create_procedure (GimpPlugIn  *plug_in,
                        const gchar *name)
{
  GimpProcedure *procedure = NULL;

  if (! strcmp (name, LOAD_PROC))
    {
      procedure = gimp_load_procedure_new (plug_in, name,
                                           GIMP_PDB_PROC_TYPE_PLUGIN,
                                           faxg3_load, NULL, NULL);

      gimp_procedure_set_menu_label (procedure, _("G3 fax image"));

      gimp_procedure_set_documentation (procedure,
                                        "Loads g3 fax files",
                                        "This plug-in loads Fax G3 Image files.",
                                        name);
      gimp_procedure_set_attribution (procedure,
                                      "Jochen Friedrich",
                                      "Jochen Friedrich, Gert Doering, "
                                      "Spencer Kimball & Peter Mattis",
                                      NULL);

      gimp_file_procedure_set_mime_types (GIMP_FILE_PROCEDURE (procedure),
                                          "image/g3-fax");
      gimp_file_procedure_set_extensions (GIMP_FILE_PROCEDURE (procedure),
                                          "g3");
      gimp_file_procedure_set_magics (GIMP_FILE_PROCEDURE (procedure),
                                      "4,string,Research");
    }

  return procedure;
}

static GimpValueArray *
faxg3_load (GimpProcedure         *procedure,
            GimpRunMode            run_mode,
            GFile                 *file,
            GimpMetadata          *metadata,
            GimpMetadataLoadFlags *flags,
            GimpProcedureConfig   *config,
            gpointer               run_data)
{
  GimpValueArray *return_vals;
  GimpImage      *image;
  GError         *error = NULL;

  gegl_init (NULL, NULL);

  image = load_image (file, &error);

  if (! image)
    return gimp_procedure_new_return_values (procedure,
                                             GIMP_PDB_EXECUTION_ERROR,
                                             error);

  return_vals = gimp_procedure_new_return_values (procedure,
                                                  GIMP_PDB_SUCCESS,
                                                  NULL);

  GIMP_VALUES_SET_IMAGE (return_vals, 1, image);

  return return_vals;
}

#ifdef DEBUG
void
putbin (unsigned long d)
{
  unsigned long i = 0x80000000;

  while (i != 0)
    {
      putc((d & i) ? '1' : '0', stderr);
      i >>= 1;
    }
  putc('\n', stderr);
}
#endif

static int byte_tab[256];
/* static int o_stretch; */             /* -stretch: double each line */
/* static int o_stretch_force=-1; */    /* -1: guess from filename */
/* static int o_lj; */                  /* -l: LJ output */
/* static int o_turn; */                /* -t: turn 90 degrees right */

struct g3_tree * black, * white;

#define CHUNK 2048;
static  char rbuf[2048];        /* read buffer */
static  int  rp;                /* read pointer */
static  int  rs;                /* read buffer size */

#define MAX_ROWS 4300
#define MAX_COLS 1728           /* !! FIXME - command line parameter */


static GimpImage *
load_image (GFile   *file,
            GError **error)
{
  int             data;
  int             hibit;
  struct g3_tree *p;
  int             nr_pels;
  int             fd;
  int             color;
  int             i, rr, rsize;
  int             cons_eol;
  int             last_eol_row;

  GimpImage      *image   = NULL;
  gint            bperrow = MAX_COLS/8;  /* bytes per bit row */
  gchar          *bitmap;                /* MAX_ROWS by (bperrow) bytes */
  gchar          *bp;                    /* bitmap pointer */
  gint            row;
  gint            max_rows;              /* max. rows allocated */
  gint            col, hcol;             /* column, highest column ever used */

  gimp_progress_init_printf (_("Opening '%s'"),
                             gimp_file_get_utf8_name (file));

  /* initialize lookup trees */
  build_tree (&white, t_white);
  build_tree (&white, m_white);
  build_tree (&black, t_black);
  build_tree (&black, m_black);

  init_byte_tab (0, byte_tab);

  fd = g_open (g_file_peek_path (file), O_RDONLY | _O_BINARY, 0);

  if (fd < 0)
    {
      g_set_error (error, G_FILE_ERROR, g_file_error_from_errno (errno),
                   _("Could not open '%s' for reading: %s"),
                   gimp_file_get_utf8_name (file), g_strerror (errno));
      return NULL;
    }

  hibit = 0;
  data = 0;

  cons_eol = 0; /* consecutive EOLs read - zero yet */
  last_eol_row = 0;

  color = 0; /* start with white */
  rr = 0;

  rsize = lseek (fd, 0L, SEEK_END);
  lseek (fd, 0L, 0);

  rs = read (fd, rbuf, sizeof (rbuf));
  if (rs < 0)
    {
      close (fd);
      g_set_error (error, G_FILE_ERROR, g_file_error_from_errno (errno),
                   _("Error while reading '%s': %s"),
                   gimp_file_get_utf8_name (file), g_strerror (errno));
      return NULL;
    }

  rr += rs;
  gimp_progress_update ((float) rr / rsize / 2.0);

                        /* skip GhostScript header */
  rp = (rs >= 64 && strcmp (rbuf + 1, "PC Research, Inc") == 0) ? 64 : 0;

  /* initialize bitmap */

  row = col = hcol = 0;

  bitmap = g_new0 (gchar, (max_rows = MAX_ROWS) * MAX_COLS / 8);
  if (! bitmap)
    {
      g_set_error (error, G_FILE_ERROR, G_FILE_ERROR_FAILED,
                   _("Could not create buffer to process image data."));
      return NULL;
    }

  bp = &bitmap[row * MAX_COLS / 8];

  while (rs > 0 && cons_eol < 10)        /* i.e., while (!EOF) */
    {
#ifdef DEBUG
      g_printerr ("hibit=%2d, data=", hibit);
      putbin (data);
#endif

      while (hibit < 20)
        {
          data |= (byte_tab[(int) (unsigned char) rbuf[rp++]] << hibit);
          hibit += 8;

          if (rp >= rs)
            {
              rs = read (fd, rbuf, sizeof (rbuf));
              if (rs < 0)
                { perror ("read2");
                  break;
                }
              rr += rs;
              gimp_progress_update ((float) rr / rsize / 2.0);
              rp = 0;
              if (rs == 0)
                goto do_write;
            }

#ifdef DEBUG
          g_printerr ("hibit=%2d, data=", hibit);
          putbin (data);
#endif
        }

      if (color == 0) /* white */
        p = white->nextb[data & BITM];
      else /* black */
        p = black->nextb[data & BITM];

      while (p != NULL && ! (p->nr_bits))
        {
          data >>= FBITS;
          hibit -= FBITS;
          p = p->nextb[data & BITM];
        }

      if (p == NULL) /* invalid code */
        {
          g_printerr ("invalid code, row=%d, col=%d, file offset=%lx, skip to eol\n",
                      row, col, (unsigned long) lseek (fd, 0, 1) - rs + rp);

          while ((data & 0x03f) != 0)
            {
              data >>= 1; hibit--;

              if ( hibit < 20 )
                {
                  data |= (byte_tab[(int) (unsigned char) rbuf[rp++]] << hibit);
                  hibit += 8;

                  if (rp >= rs) /* buffer underrun */
                    {
                      rs = read (fd, rbuf, sizeof (rbuf));

                      if (rs < 0)
                        { perror ("read4");
                          break;
                        }

                      rr += rs;
                      gimp_progress_update ((float) rr / rsize / 2.0);
                      rp = 0;
                      if (rs == 0)
                        goto do_write;
                    }
                }
            }
          nr_pels = -1;         /* handle as if eol */
        }
      else /* p != NULL <-> valid code */
        {
          data >>= p->nr_bits;
          hibit -= p->nr_bits;

          nr_pels = ((struct g3_leaf *) p)->nr_pels;
#ifdef DEBUG
          g_printerr ("PELs: %d (%c)\n", nr_pels, '0' + color);
#endif
        }

        /* handle EOL (including fill bits) */
      if (nr_pels == -1)
        {
#ifdef DEBUG
          g_printerr ("hibit=%2d, data=", hibit);
          putbin (data);
#endif
          /* skip filler 0bits -> seek for "1"-bit */
          while ((data & 0x01) != 1)
            {
              if ((data & 0xf) == 0) /* nibble optimization */
                {
                  hibit-= 4;
                  data >>= 4;
                }
              else
                {
                  hibit--;
                  data >>= 1;
                }

              /* fill higher bits */
              if (hibit < 20)
                {
                  data |= ( byte_tab[(int) (unsigned char) rbuf[ rp++]] << hibit);
                  hibit += 8;

                  if (rp >= rs) /* buffer underrun */
                    {
                      rs = read (fd, rbuf, sizeof (rbuf));
                      if ( rs < 0 )
                        {
                          perror ("read3");
                          break;
                        }
                      rr += rs;
                      gimp_progress_update ((float) rr / rsize / 2.0);
                      rp = 0;
                      if (rs == 0)
                        goto do_write;
                    }
                }
#ifdef DEBUG
              g_printerr ("hibit=%2d, data=", hibit );
              putbin(data);
#endif
            } /* end skip 0bits */
          hibit--;
          data >>=1;

          color = 0;

          if (col == 0)
            {
              if (last_eol_row != row)
                {
                  cons_eol++; /* consecutive EOLs */
                  last_eol_row = row;
                }
            }
          else
            {
              if (col > hcol && col <= MAX_COLS)
                hcol = col;
              row++;

              /* bitmap memory full? make it larger! */
              if (row >= max_rows)
                {
                  gchar *p = g_try_realloc (bitmap,
                                            (max_rows += 500) * MAX_COLS / 8);
                  if (p == NULL)
                    {
                      perror ("realloc() failed, page truncated");
                      rs = 0;
                    }
                  else
                    {
                      bitmap = p;
                      memset (&bitmap[ row * MAX_COLS / 8 ], 0,
                              (max_rows - row) * MAX_COLS / 8);
                    }
                }

              col=0; bp = &bitmap[row * MAX_COLS / 8];
              cons_eol = 0;
            }
        }
      else /* not eol */
        {
          if (col + nr_pels > MAX_COLS)
            nr_pels = MAX_COLS - col;

          if (color == 0) /* white */
            {
              col += nr_pels;
            }
          else /* black */
            {
              register int bit = (0x80 >> (col & 07));
              register char *w = & bp[col >> 3];

              for (i = nr_pels; i > 0; i--)
                {
                  *w |= bit;
                  bit >>=1;
                  if (bit == 0)
                    {
                      bit = 0x80;
                      w++;
                    }
                  col++;
                }
            }

          if (nr_pels < 64)
            color = !color; /* terminating code */
        }
    } /* end main loop */

 do_write: /* write pbm (or whatever) file */

  if (fd != 0)
    close (fd); /* close input file */

#ifdef DEBUG
  g_printerr ("consecutive EOLs: %d, max columns: %d\n", cons_eol, hcol);
#endif

  image = emitgimp (hcol, row, bitmap, bperrow, file, error);

  g_free (bitmap);

  return image;
}

/* hcol is the number of columns, row the number of rows
 * bperrow is the number of bytes actually used by hcol, which may
 * be greater than (hcol+7)/8 [in case of an unscaled g3 image less
 * than 1728 pixels wide]
 */

static GimpImage *
emitgimp (gint         hcol,
          gint         row,
          const gchar *bitmap,
          gint         bperrow,
          GFile       *file,
          GError     **error)
{
  GeglBuffer *buffer;
  GimpImage  *image;
  GimpLayer  *layer;
  guchar     *buf;
  guchar      tmp;
  gint        x, y;
  gint        xx, yy;
  gint        tile_height;

  /* initialize */

  tmp = 0;

#ifdef DEBUG
  g_printerr ("emit ammoos: %d x %d\n", hcol, row);
#endif

  if (hcol > GIMP_MAX_IMAGE_SIZE || hcol <= 0 ||
      row > GIMP_MAX_IMAGE_SIZE || row <= 0)
    {
      g_set_error (error, G_FILE_ERROR, G_FILE_ERROR_FAILED,
                   _("Invalid image dimensions (%d x %d). "
                     "Image may be corrupt."),
                   hcol, row);
      return NULL;
    }

  image = gimp_image_new (hcol, row, GIMP_GRAY);
  if (! image)
    {
      g_set_error (error, G_FILE_ERROR, G_FILE_ERROR_FAILED,
                   _("Could not create image."));
      return NULL;
    }

  layer = gimp_layer_new (image, _("Background"),
                          hcol,
                          row,
                          GIMP_GRAY_IMAGE,
                          100,
                          gimp_image_get_default_new_layer_mode (image));
  gimp_image_insert_layer (image, layer, NULL, 0);

  buffer = gimp_drawable_get_buffer (GIMP_DRAWABLE (layer));

  tile_height = gimp_tile_height ();
#ifdef DEBUG
  g_printerr ("tile height: %d\n", tile_height);
#endif

  buf = g_new (guchar, hcol * tile_height);
  if (! buf)
    {
      g_set_error (error, G_FILE_ERROR, G_FILE_ERROR_FAILED,
                   _("Could not create buffer to process image data."));
      g_object_unref (buffer);
      gimp_image_delete(image);
      return NULL;
    }

  xx = 0;
  yy = 0;

  for (y = 0; y < row; y++)
    {
      for (x = 0; x < hcol; x++)
        {
          if ((x & 7) == 0)
            tmp = bitmap[y * bperrow + (x >> 3)];

          buf[xx++] = tmp&(128 >> (x & 7)) ? 0 : 255;
        }

      if ((y - yy) == tile_height - 1)
        {
#ifdef DEBUG
          g_printerr ("update tile height: %d\n", tile_height);
#endif

          gegl_buffer_set (buffer, GEGL_RECTANGLE (0, yy, hcol, tile_height), 0,
                           NULL, buf, GEGL_AUTO_ROWSTRIDE);

          gimp_progress_update (0.5 + (float) y / row / 2.0);

          xx = 0;
          yy += tile_height;
        }
    }

  if (row - yy)
    {
#ifdef DEBUG
      g_printerr ("update rest: %d\n", row-yy);
#endif

      gegl_buffer_set (buffer, GEGL_RECTANGLE (0, yy, hcol, row - yy), 0,
                       NULL, buf, GEGL_AUTO_ROWSTRIDE);
    }

  gimp_progress_update (1.0);

  g_free (buf);

  g_object_unref (buffer);

  return image;
}

/* --- end plug-ins/field-io/file-faxg3/faxg3.c --- */

/* --- begin plug-ins/field-io/file-faxg3/g3.c --- */
/* #ident "@(#)g3.c	3.1 95/08/30 Copyright (c) Gert Doering" */

#include "config.h"

#include <stdlib.h>
#include <stdio.h>

#include <glib.h>

#include "g3.h"

struct g3code t_white[66] = {
{ 0,   0, 0x0ac,  8 },
{ 0,   1, 0x038,  6 },
{ 0,   2, 0x00e,  4 },
{ 0,   3, 0x001,  4 },
{ 0,   4, 0x00d,  4 },
{ 0,   5, 0x003,  4 },
{ 0,   6, 0x007,  4 },
{ 0,   7, 0x00f,  4 },
{ 0,   8, 0x019,  5 },
{ 0,   9, 0x005,  5 },
{ 0,  10, 0x01c,  5 },
{ 0,  11, 0x002,  5 },
{ 0,  12, 0x004,  6 },
{ 0,  13, 0x030,  6 },
{ 0,  14, 0x00b,  6 },
{ 0,  15, 0x02b,  6 },
{ 0,  16, 0x015,  6 },
{ 0,  17, 0x035,  6 },
{ 0,  18, 0x072,  7 },
{ 0,  19, 0x018,  7 },
{ 0,  20, 0x008,  7 },
{ 0,  21, 0x074,  7 },
{ 0,  22, 0x060,  7 },
{ 0,  23, 0x010,  7 },
{ 0,  24, 0x00a,  7 },
{ 0,  25, 0x06a,  7 },
{ 0,  26, 0x064,  7 },
{ 0,  27, 0x012,  7 },
{ 0,  28, 0x00c,  7 },
{ 0,  29, 0x040,  8 },
{ 0,  30, 0x0c0,  8 },
{ 0,  31, 0x058,  8 },
{ 0,  32, 0x0d8,  8 },
{ 0,  33, 0x048,  8 },
{ 0,  34, 0x0c8,  8 },
{ 0,  35, 0x028,  8 },
{ 0,  36, 0x0a8,  8 },
{ 0,  37, 0x068,  8 },
{ 0,  38, 0x0e8,  8 },
{ 0,  39, 0x014,  8 },
{ 0,  40, 0x094,  8 },
{ 0,  41, 0x054,  8 },
{ 0,  42, 0x0d4,  8 },
{ 0,  43, 0x034,  8 },
{ 0,  44, 0x0b4,  8 },
{ 0,  45, 0x020,  8 },
{ 0,  46, 0x0a0,  8 },
{ 0,  47, 0x050,  8 },
{ 0,  48, 0x0d0,  8 },
{ 0,  49, 0x04a,  8 },
{ 0,  50, 0x0ca,  8 },
{ 0,  51, 0x02a,  8 },
{ 0,  52, 0x0aa,  8 },
{ 0,  53, 0x024,  8 },
{ 0,  54, 0x0a4,  8 },
{ 0,  55, 0x01a,  8 },
{ 0,  56, 0x09a,  8 },
{ 0,  57, 0x05a,  8 },
{ 0,  58, 0x0da,  8 },
{ 0,  59, 0x052,  8 },
{ 0,  60, 0x0d2,  8 },
{ 0,  61, 0x04c,  8 },
{ 0,  62, 0x0cc,  8 },
{ 0,  63, 0x02c,  8 },
{ 0, -1, 0, 11 },		/* 11 0-bits == EOL, special handling */
{ 0, -1, 0, 0 }};		/* end of table */

/* make-up codes white */
struct g3code m_white[28] = {
{ 0,  64, 0x01b,  5 },
{ 0, 128, 0x009,  5 },
{ 0, 192, 0x03a,  6 },
{ 0, 256, 0x076,  7 },
{ 0, 320, 0x06c,  8 },
{ 0, 384, 0x0ec,  8 },
{ 0, 448, 0x026,  8 },
{ 0, 512, 0x0a6,  8 },
{ 0, 576, 0x016,  8 },
{ 0, 640, 0x0e6,  8 },
{ 0, 704, 0x066,  9 },
{ 0, 768, 0x166,  9 },
{ 0, 832, 0x096,  9 },
{ 0, 896, 0x196,  9 },
{ 0, 960, 0x056,  9 },
{ 0,1024, 0x156,  9 },
{ 0,1088, 0x0d6,  9 },
{ 0,1152, 0x1d6,  9 },
{ 0,1216, 0x036,  9 },
{ 0,1280, 0x136,  9 },
{ 0,1344, 0x0b6,  9 },
{ 0,1408, 0x1b6,  9 },
{ 0,1472, 0x032,  9 },
{ 0,1536, 0x132,  9 },
{ 0,1600, 0x0b2,  9 },
{ 0,1664, 0x006,  6 },
{ 0,1728, 0x1b2,  9 },
{ 0,  -1, 0, 0} };


struct g3code t_black[66] = {
{ 0,   0, 0x3b0, 10 },
{ 0,   1, 0x002,  3 },
{ 0,   2, 0x003,  2 },
{ 0,   3, 0x001,  2 },
{ 0,   4, 0x006,  3 },
{ 0,   5, 0x00c,  4 },
{ 0,   6, 0x004,  4 },
{ 0,   7, 0x018,  5 },
{ 0,   8, 0x028,  6 },
{ 0,   9, 0x008,  6 },
{ 0,  10, 0x010,  7 },
{ 0,  11, 0x050,  7 },
{ 0,  12, 0x070,  7 },
{ 0,  13, 0x020,  8 },
{ 0,  14, 0x0e0,  8 },
{ 0,  15, 0x030,  9 },
{ 0,  16, 0x3a0, 10 },
{ 0,  17, 0x060, 10 },
{ 0,  18, 0x040, 10 },
{ 0,  19, 0x730, 11 },
{ 0,  20, 0x0b0, 11 },
{ 0,  21, 0x1b0, 11 },
{ 0,  22, 0x760, 11 },
{ 0,  23, 0x0a0, 11 },
{ 0,  24, 0x740, 11 },
{ 0,  25, 0x0c0, 11 },
{ 0,  26, 0x530, 12 },
{ 0,  27, 0xd30, 12 },
{ 0,  28, 0x330, 12 },
{ 0,  29, 0xb30, 12 },
{ 0,  30, 0x160, 12 },
{ 0,  31, 0x960, 12 },
{ 0,  32, 0x560, 12 },
{ 0,  33, 0xd60, 12 },
{ 0,  34, 0x4b0, 12 },
{ 0,  35, 0xcb0, 12 },
{ 0,  36, 0x2b0, 12 },
{ 0,  37, 0xab0, 12 },
{ 0,  38, 0x6b0, 12 },
{ 0,  39, 0xeb0, 12 },
{ 0,  40, 0x360, 12 },
{ 0,  41, 0xb60, 12 },
{ 0,  42, 0x5b0, 12 },
{ 0,  43, 0xdb0, 12 },
{ 0,  44, 0x2a0, 12 },
{ 0,  45, 0xaa0, 12 },
{ 0,  46, 0x6a0, 12 },
{ 0,  47, 0xea0, 12 },
{ 0,  48, 0x260, 12 },
{ 0,  49, 0xa60, 12 },
{ 0,  50, 0x4a0, 12 },
{ 0,  51, 0xca0, 12 },
{ 0,  52, 0x240, 12 },
{ 0,  53, 0xec0, 12 },
{ 0,  54, 0x1c0, 12 },
{ 0,  55, 0xe40, 12 },
{ 0,  56, 0x140, 12 },
{ 0,  57, 0x1a0, 12 },
{ 0,  58, 0x9a0, 12 },
{ 0,  59, 0xd40, 12 },
{ 0,  60, 0x340, 12 },
{ 0,  61, 0x5a0, 12 },
{ 0,  62, 0x660, 12 },
{ 0,  63, 0xe60, 12 },
{ 0,  -1, 0x000, 11 },
{ 0,  -1, 0, 0 } };

struct g3code m_black[28] = {
{ 0,  64, 0x3c0, 10 },
{ 0, 128, 0x130, 12 },
{ 0, 192, 0x930, 12 },
{ 0, 256, 0xda0, 12 },
{ 0, 320, 0xcc0, 12 },
{ 0, 384, 0x2c0, 12 },
{ 0, 448, 0xac0, 12 },
{ 0, 512, 0x6c0, 13 },
{ 0, 576,0x16c0, 13 },
{ 0, 640, 0xa40, 13 },
{ 0, 704,0x1a40, 13 },
{ 0, 768, 0x640, 13 },
{ 0, 832,0x1640, 13 },
{ 0, 896, 0x9c0, 13 },
{ 0, 960,0x19c0, 13 },
{ 0,1024, 0x5c0, 13 },
{ 0,1088,0x15c0, 13 },
{ 0,1152, 0xdc0, 13 },
{ 0,1216,0x1dc0, 13 },
{ 0,1280, 0x940, 13 },
{ 0,1344,0x1940, 13 },
{ 0,1408, 0x540, 13 },
{ 0,1472,0x1540, 13 },
{ 0,1536, 0xb40, 13 },
{ 0,1600,0x1b40, 13 },
{ 0,1664, 0x4c0, 13 },
{ 0,1728,0x14c0, 13 },
{ 0,  -1, 0, 0 } };

void tree_add_node( struct g3_tree *p, struct g3code * g3c,
		        int bit_code, int bit_length )
{
int i;

    if ( bit_length <= FBITS )		/* leaf (multiple bits) */
    {
	g3c->nr_bits = bit_length;	/* leaf tag */

	if ( bit_length == FBITS )	/* full width */
	{
	    p->nextb[ bit_code ] = (struct g3_tree *) g3c;
	}
	else				/* fill bits */
	  for ( i=0; i< ( 1 << (FBITS-bit_length)); i++ )
	  {
	    p->nextb[ bit_code + ( i << bit_length ) ] = (struct g3_tree *) g3c;
	  }
    }
    else				/* node */
    {
    struct g3_tree *p2;

	p2 = p->nextb[ bit_code & BITM ];
	if ( p2 == 0 )			/* no sub-node exists */
	{
	    p2 = p->nextb[ bit_code & BITM ] =
		( struct g3_tree * ) calloc( 1, sizeof( struct g3_tree ));
	    if ( p2 == NULL ) { perror( "malloc 3" ); exit(11); }
	    p2->nr_bits = 0;		/* node tag */

	}
	if ( p2->nr_bits != 0 )
	{
	    g_printerr ("internal table setup error\n" ); exit(6);
	}
	tree_add_node( p2, g3c, bit_code >> FBITS, bit_length - FBITS );
    }
}

void build_tree (struct g3_tree ** p, struct g3code * c )
{
    if ( *p == NULL )
    {
	(*p) = (struct g3_tree *) calloc( 1, sizeof(struct g3_tree) );
	if ( *p == NULL ) { perror( "malloc(1)" ); exit(10); }

	(*p)->nr_bits=0;
    }

    while ( c->bit_length != 0 )
    {
	tree_add_node( *p, c, c->bit_code, c->bit_length );
	c++;
    }
}

void init_byte_tab (int reverse, int byte_tab[] )
{
int i;
    if ( reverse ) for ( i=0; i<256; i++ ) byte_tab[i] = i;
    else
      for ( i=0; i<256; i++ )
	     byte_tab[i] = ( ((i & 0x01) << 7) | ((i & 0x02) << 5) |
			     ((i & 0x04) << 3) | ((i & 0x08) << 1) |
			     ((i & 0x10) >> 1) | ((i & 0x20) >> 3) |
			     ((i & 0x40) >> 5) | ((i & 0x80) >> 7) );
}

/* --- end plug-ins/field-io/file-faxg3/g3.c --- */

/* --- begin plug-ins/field-io/file-fits/fits.c --- */
/* AmmoOS Image - The AmmoOS Field Image Research
 * Copyright (C) 1995 Spencer Kimball and Peter Mattis
 * FITS file plugin
 * reading and writing code Copyright (C) 1997 Peter Kirchgessner
 * e-mail: peter@kirchgessner.net, WWW: http://www.kirchgessner.net
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 *
 */

/* Event history:
 * V 1.00, PK, 05-May-97: Creation
 * V 1.01, PK, 19-May-97: Problem with compilation on Irix fixed
 * V 1.02, PK, 08-Jun-97: Bug with saving gray images fixed
 * V 1.03, PK, 05-Oct-97: Parse rc-file
 * V 1.04, PK, 12-Oct-97: No progress bars for non-interactive mode
 * V 1.05, nn, 20-Dec-97: Initialize image_ID in run()
 * V 1.06, PK, 21-Nov-99: Internationalization
 *                        Fix bug with gimp_export_image()
 *                        (moved it from load to save)
 * V 1.07, PK, 16-Aug-06: Fix problems with internationalization
 *                        (writing 255,0 instead of 255.0)
 *                        Fix problem with not filling up properly last record
 */

#include "config.h"

#include <math.h>
#include <string.h>
#include <errno.h>

#include <glib/gstdio.h>

#include <libgimp/ammoos.h>
#include <libgimp/gimpui.h>

#include <fitsio.h>

#include "libgimp/stdplugins-intl.h"


#define LOAD_PROC      "file-fits-load"
#define EXPORT_PROC    "file-fits-export"
#define PLUG_IN_BINARY "file-fits"
#define PLUG_IN_ROLE   "ammoos-file-fits"


typedef struct _Fits      Fits;
typedef struct _FitsClass FitsClass;

struct _Fits
{
  GimpPlugIn      parent_instance;
};

struct _FitsClass
{
  GimpPlugInClass parent_class;
};


#define FITS_TYPE  (fits_get_type ())
#define FITS(obj) (G_TYPE_CHECK_INSTANCE_CAST ((obj), FITS_TYPE, Fits))

GType                   fits_get_type         (void) G_GNUC_CONST;

typedef struct
{
  gint   naxis;
  glong  naxisn[3];
  gint   bitpix;
  gint   bpp;
  gint   datatype;
} FitsHduData;

static GList          * fits_query_procedures (GimpPlugIn            *plug_in);
static GimpProcedure  * fits_create_procedure (GimpPlugIn            *plug_in,
                                               const gchar           *name);

static GimpValueArray * fits_load             (GimpProcedure         *procedure,
                                               GimpRunMode            run_mode,
                                               GFile                 *file,
                                               GimpMetadata          *metadata,
                                               GimpMetadataLoadFlags *flags,
                                               GimpProcedureConfig   *config,
                                               gpointer               run_data);
static GimpValueArray * fits_export           (GimpProcedure         *procedure,
                                               GimpRunMode            run_mode,
                                               GimpImage             *image,
                                               GFile                 *file,
                                               GimpExportOptions     *options,
                                               GimpMetadata          *metadata,
                                               GimpProcedureConfig   *config,
                                               gpointer               run_data);

static GimpImage      * load_image            (GFile                 *file,
                                               GObject               *config,
                                               GimpRunMode            run_mode,
                                               GError               **error);
static gint             export_image          (GFile                 *file,
                                               GimpImage             *image,
                                               GimpDrawable          *drawable,
                                               GError               **error);

static gint             export_fits           (GFile                 *file,
                                               GimpImage             *image,
                                               GimpDrawable          *drawable);

static GimpImage      * create_new_image      (GFile                 *file,
                                               guint                  pagenum,
                                               guint                  width,
                                               guint                  height,
                                               GimpImageBaseType      itype,
                                               GimpImageType          dtype,
                                               GimpPrecision          iprecision,
                                               GimpLayer            **layer,
                                               GeglBuffer           **buffer);

static gboolean         load_dialog           (GimpProcedure         *procedure,
                                               GObject               *config);
static void             show_fits_errors      (gint                   status);


G_DEFINE_TYPE (Fits, fits, GIMP_TYPE_PLUG_IN)

GIMP_MAIN (FITS_TYPE)
DEFINE_STD_SET_I18N


static void
fits_class_init (FitsClass *klass)
{
  GimpPlugInClass *plug_in_class = GIMP_PLUG_IN_CLASS (klass);

  plug_in_class->query_procedures = fits_query_procedures;
  plug_in_class->create_procedure = fits_create_procedure;
  plug_in_class->set_i18n         = STD_SET_I18N;
}

static void
fits_init (Fits *fits)
{
}

static GList *
fits_query_procedures (GimpPlugIn *plug_in)
{
  GList *list = NULL;

  list = g_list_append (list, g_strdup (LOAD_PROC));
  list = g_list_append (list, g_strdup (EXPORT_PROC));

  return list;
}

static GimpProcedure *
fits_create_procedure (GimpPlugIn  *plug_in,
                       const gchar *name)
{
  GimpProcedure *procedure = NULL;

  if (! strcmp (name, LOAD_PROC))
    {
      procedure = gimp_load_procedure_new (plug_in, name,
                                           GIMP_PDB_PROC_TYPE_PLUGIN,
                                           fits_load, NULL, NULL);

      gimp_procedure_set_menu_label (procedure,
                                     _("Flexible Image Transport System"));

      gimp_procedure_set_documentation (procedure,
                                        _("Load file of the FITS file format"),
                                        _("Load file of the FITS file format "
                                          "(Flexible Image Transport System)"),
                                        name);
      gimp_procedure_set_attribution (procedure,
                                      "Peter Kirchgessner",
                                      "Peter Kirchgessner (peter@kirchgessner.net), "
                                      "Alex Sa.",
                                      "1997 - 2023");

      gimp_file_procedure_set_mime_types (GIMP_FILE_PROCEDURE (procedure),
                                          "image/x-fits");
      gimp_file_procedure_set_extensions (GIMP_FILE_PROCEDURE (procedure),
                                          "fit,fits");
      gimp_file_procedure_set_magics (GIMP_FILE_PROCEDURE (procedure),
                                      "0,string,SIMPLE");

      gimp_procedure_add_choice_aux_argument (procedure, "replace",
                                              _("Re_placement for undefined pixels"),
                                              _("Replacement for undefined pixels"),
                                              gimp_choice_new_with_values ("black",  0,   _("Black"), NULL,
                                                                           "white",  255, _("White"), NULL,
                                                                           NULL),
                                              "black",
                                              G_PARAM_READWRITE);
    }
  else if (! strcmp (name, EXPORT_PROC))
    {
      procedure = gimp_export_procedure_new (plug_in, name,
                                             GIMP_PDB_PROC_TYPE_PLUGIN,
                                             FALSE, fits_export, NULL, NULL);

      gimp_procedure_set_image_types (procedure, "RGB, GRAY, INDEXED");

      gimp_procedure_set_menu_label (procedure,
                                     _("Flexible Image Transport System"));

      gimp_procedure_set_documentation (procedure,
                                        _("Export file in the FITS file format"),
                                        _("FITS exporting handles all image "
                                          "types except those with alpha channels."),
                                        name);
      gimp_procedure_set_attribution (procedure,
                                      "Peter Kirchgessner",
                                      "Peter Kirchgessner (peter@kirchgessner.net), "
                                      "Alex Sa.",
                                      "1997 - 2023");

      gimp_file_procedure_set_mime_types (GIMP_FILE_PROCEDURE (procedure),
                                          "image/x-fits");
      gimp_file_procedure_set_extensions (GIMP_FILE_PROCEDURE (procedure),
                                          "fit,fits");

      gimp_export_procedure_set_capabilities (GIMP_EXPORT_PROCEDURE (procedure),
                                              GIMP_EXPORT_CAN_HANDLE_RGB  |
                                              GIMP_EXPORT_CAN_HANDLE_GRAY |
                                              GIMP_EXPORT_CAN_HANDLE_INDEXED,
                                              NULL, NULL, NULL);
    }

  return procedure;
}

static GimpValueArray *
fits_load (GimpProcedure         *procedure,
           GimpRunMode            run_mode,
           GFile                 *file,
           GimpMetadata          *metadata,
           GimpMetadataLoadFlags *flags,
           GimpProcedureConfig   *config,
           gpointer               run_data)
{
  GimpValueArray *return_vals;
  GimpImage      *image;
  GError         *error = NULL;

  gegl_init (NULL, NULL);

  if (run_mode == GIMP_RUN_INTERACTIVE)
    {
      if (! load_dialog (procedure, G_OBJECT (config)))
        return gimp_procedure_new_return_values (procedure,
                                                 GIMP_PDB_CANCEL,
                                                 NULL);
    }

  image = load_image (file, G_OBJECT (config), run_mode, &error);

  if (! image)
    return gimp_procedure_new_return_values (procedure,
                                             GIMP_PDB_EXECUTION_ERROR,
                                             error);

  return_vals = gimp_procedure_new_return_values (procedure,
                                                  GIMP_PDB_SUCCESS,
                                                  NULL);

  GIMP_VALUES_SET_IMAGE (return_vals, 1, image);

  return return_vals;
}

static GimpValueArray *
fits_export (GimpProcedure        *procedure,
             GimpRunMode           run_mode,
             GimpImage            *image,
             GFile                *file,
             GimpExportOptions    *options,
             GimpMetadata         *metadata,
             GimpProcedureConfig  *config,
             gpointer              run_data)
{
  GimpImage          *duplicate_image;
  GimpDrawable      **flipped_drawables;
  GimpPDBStatusType   status = GIMP_PDB_SUCCESS;
  GimpExportReturn    export = GIMP_EXPORT_IGNORE;
  GList             *drawables;
  GError             *error  = NULL;

  gegl_init (NULL, NULL);

  if (run_mode == GIMP_RUN_INTERACTIVE)
    gimp_ui_init (PLUG_IN_BINARY);

  export = gimp_export_options_get_image (options, &image);

  drawables = gimp_image_list_layers (image);

  /* Flip image vertical since FITS writes from bottom to top */
  duplicate_image = gimp_image_duplicate (image);
  gimp_image_flip (duplicate_image, GIMP_ORIENTATION_VERTICAL);
  flipped_drawables = gimp_image_get_selected_drawables (duplicate_image);

  if (! export_image (file, image, flipped_drawables[0], &error))
    status = GIMP_PDB_EXECUTION_ERROR;

  gimp_image_delete (duplicate_image);
  g_free (flipped_drawables);

  if (export == GIMP_EXPORT_EXPORT)
    gimp_image_delete (image);

  g_list_free (drawables);
  return gimp_procedure_new_return_values (procedure, status, error);
}

static GimpImage *
load_image (GFile        *file,
            GObject      *config,
            GimpRunMode   run_mode,
            GError      **error)
{
  GimpImage         *image       = NULL;
  GimpLayer         *layer;
  GeglBuffer        *buffer;
  FILE              *fp;
  fitsfile          *ifp;
  FitsHduData        hdu;
  gint               n_pics;
  gint               count       = 1;
  gint               width;
  gint               height;
  gint               row_length;
  int                status      = 0;
  glong              fpixel[3]   = {1, 1, 1};
  GimpImageBaseType  itype       = GIMP_GRAY;
  GimpImageType      dtype       = GIMP_GRAYA_IMAGE;
  GimpPrecision      iprecision  = GIMP_PRECISION_U16_NON_LINEAR;
  const Babl        *type        = NULL;
  const Babl        *format      = NULL;
  gdouble           *pixels;
  gdouble            datamin     = 1.0E30f;
  gdouble            datamax     = -1.0E30f;
  gint               channels    = 1;
  gint               replace;
  gdouble            replace_val = 0;

  replace = gimp_procedure_config_get_choice_id (GIMP_PROCEDURE_CONFIG (config),
                                                 "replace");

  fp = g_fopen (g_file_peek_path (file), "rb");

  if (! fp)
    {
      g_set_error (error, G_FILE_ERROR, g_file_error_from_errno (errno),
                   _("Could not open '%s' for reading: %s"),
                   gimp_file_get_utf8_name (file), g_strerror (errno));
      return NULL;
    }

  fclose (fp);

  if (fits_open_diskfile (&ifp, g_file_peek_path (file), READONLY, &status))
    show_fits_errors (status);

  if (! ifp)
    {
      g_set_error (error, G_FILE_ERROR, G_FILE_ERROR_FAILED,
                   "%s", _("Error during opening of FITS file"));
      return NULL;
    }

  /* Get first item */
  fits_get_num_hdus (ifp, &n_pics, &status);

  if (status)
    show_fits_errors (status);

  if (n_pics <= 0)
    {
      g_set_error (error, G_FILE_ERROR, G_FILE_ERROR_FAILED,
                   "%s", _("FITS file keeps no displayable images"));
      fits_close_file (ifp, &status);
      return NULL;
    }

  while (count <= n_pics)
    {
      hdu.naxis = 0;

      fits_movabs_hdu (ifp, count, NULL, &status);

      fits_get_img_param (ifp, 3, &hdu.bitpix, &hdu.naxis, hdu.naxisn,
                          &status);

      /* Skip if invalid dimensions; possibly header data */
      if (hdu.naxis < 2)
        {
          count++;
          continue;
        }

      width  = hdu.naxisn[0];
      height = hdu.naxisn[1];

      type = babl_type ("double");
      switch (hdu.bitpix)
      {
        case 8:
          iprecision = GIMP_PRECISION_U8_LINEAR;
          if (replace)
            replace_val = 255;
          break;
        case 16:
          iprecision = GIMP_PRECISION_U16_NON_LINEAR;
          if (replace)
            replace_val = G_MAXSHORT;
          break;
        case 32:
          iprecision = GIMP_PRECISION_U32_LINEAR;
          if (replace)
            replace_val = G_MAXINT;
          break;
        case -32:
          iprecision = GIMP_PRECISION_FLOAT_LINEAR;
          if (replace)
            replace_val = G_MAXFLOAT;
          break;
        case -64:
          iprecision = GIMP_PRECISION_DOUBLE_LINEAR;
          if (replace)
            replace_val = G_MAXDOUBLE;
          break;
      }

      if (hdu.naxis == 2)
        {
          itype = GIMP_GRAY;
          dtype = GIMP_GRAYA_IMAGE;
          format = babl_format_new (babl_model ("Y'"),
                                    type,
                                    babl_component ("Y'"),
                                    NULL);
        }
      else if (hdu.naxisn[2])
        {
          /* Original RGB format */
          if (hdu.naxisn[0] == 3)
            {
              width  = hdu.naxisn[1];
              height = hdu.naxisn[2];
            }
          channels = 3;

          itype  = GIMP_RGB;
          dtype  = GIMP_RGB_IMAGE;
          format = babl_format_new (babl_model ("R'G'B'"),
                                    type,
                                    babl_component ("R'"),
                                    babl_component ("G'"),
                                    babl_component ("B'"),
                                    NULL);
        }

      if (width  <= 0                  ||
          height <= 0                  ||
          width  > GIMP_MAX_IMAGE_SIZE ||
          height > GIMP_MAX_IMAGE_SIZE)
        {
          g_set_error (error, GIMP_PLUG_IN_ERROR, 0,
                       _("'%s' has a larger image size (%d x %d) "
                         "than AmmoOS Image can handle."),
                       gimp_file_get_utf8_name (file), width, height);
          fits_close_file (ifp, &status);
          return NULL;
        }

      /* If RGB FITS image, we need to read in the whole image so we can
       * convert the planes format to RGB */
      if (hdu.naxis == 2)
        pixels =
          (gdouble *) g_try_malloc (width * sizeof (gdouble) * channels);
      else
        pixels =
          (gdouble *) g_try_malloc (width * height * sizeof (gdouble) * channels);

      if (pixels == NULL)
        {
          g_set_error (error, G_FILE_ERROR, 0,
                       "Memory could not be allocated.");
          fits_close_file (ifp, &status);
          return NULL;
        }

      if (! image)
        {
          image = create_new_image (file, count, width, height,
                                    itype, dtype, iprecision,
                                    &layer, &buffer);
        }
      else
        {
          layer = gimp_layer_new (image, _("FITS HDU"), width, height,
                                  dtype, 100,
                                  gimp_image_get_default_new_layer_mode (image));
          gimp_image_insert_layer (image, layer, NULL, 0);
          buffer = gimp_drawable_get_buffer (GIMP_DRAWABLE (layer));
        }

      row_length = width * channels;

      /* Calculate min/max pixel value for normalizing */
      for (fpixel[1] = height; fpixel[1] >= 1; fpixel[1]--)
        {
          if (fits_read_pix (ifp, TDOUBLE, fpixel, row_length, NULL,
                             pixels, NULL, &status))
            break;

          for (gint ii = 0; ii < row_length; ii++)
            {
              if (pixels[ii] < datamin)
                datamin = pixels[ii];

              if (pixels[ii] > datamax)
                datamax = pixels[ii];
            }
        }

      if (status)
        show_fits_errors (status);

      /* Read pixel values in */
      if (hdu.naxis == 2)
        {
          for (fpixel[1] = height; fpixel[1] >= 1; fpixel[1]--)
            {
              if (fits_read_pix (ifp, TDOUBLE, fpixel, row_length, &replace_val,
                                 pixels, NULL, &status))
                break;

              if (datamin < datamax)
                {
                  for (gint ii = 0; ii < row_length; ii++)
                    pixels[ii] = (pixels[ii] - datamin) / (datamax - datamin);
                }

              gegl_buffer_set (buffer,
                               GEGL_RECTANGLE (0, height - fpixel[1],
                                               width, 1), 0,
                               format, pixels, GEGL_AUTO_ROWSTRIDE);
            }
        }
      else if (hdu.naxisn[2] && hdu.naxisn[2] == 3)
        {
          gint total_size = width * height * channels;

          fits_read_img (ifp, TDOUBLE, 1, total_size, &replace_val,
                         pixels, NULL, &status);

          if (! status)
            {
              gdouble *temp;

              temp = (gdouble *) malloc (width * height * sizeof (gdouble) * channels);

              if (temp == NULL)
                {
                  g_set_error (error, G_FILE_ERROR, 0,
                               "Memory could not be allocated.");
                  fits_close_file (ifp, &status);
                  g_object_unref (buffer);
                  return image;
                }

              if (datamin < datamax)
                {
                  for (gint ii = 0; ii < total_size; ii++)
                    pixels[ii] = (pixels[ii] - datamin) / (datamax - datamin);
                }

              for (gint ii = 0; ii < (total_size / 3); ii++)
                {
                  temp[(ii * 3)]     = pixels[ii];
                  temp[(ii * 3) + 1] = pixels[ii + (total_size / 3)];
                  temp[(ii * 3) + 2] = pixels[ii + ((total_size / 3) * 2)];
                }

              gegl_buffer_set (buffer, GEGL_RECTANGLE (0, 0, width, height), 0,
                               format, temp, GEGL_AUTO_ROWSTRIDE);

              if (temp)
                g_free (temp);
            }
        }

      if (status)
        show_fits_errors (status);

      g_object_unref (buffer);

      if (hdu.naxisn[2] && hdu.naxisn[2] == 3)
        {
          /* Per SiriL developers, FITS images should be loaded from the
           * bottom up. fits_read_img () loads them from top down, so we
           * should flip the layer. */
          gimp_item_transform_flip_simple (GIMP_ITEM (layer),
                                           GIMP_ORIENTATION_VERTICAL,
                                           TRUE, -1.0);
        }

      if (pixels)
        g_free (pixels);

      count++;
    }

  if (! image)
    {
      g_set_error (error, G_FILE_ERROR, G_FILE_ERROR_FAILED,
                   "%s", _("FITS file keeps no displayable images"));
      fits_close_file (ifp, &status);
      return NULL;
    }

  /* As there might be different sized layers,
   * we need to resize the canvas afterwards */
  gimp_image_resize_to_layers (image);

  fits_close_file (ifp, &status);

  return image;
}

static gint
export_image (GFile         *file,
              GimpImage     *image,
              GimpDrawable  *drawable,
              GError       **error)
{
  GimpImageType  drawable_type;
  gint           retval;

  drawable_type = gimp_drawable_type (drawable);

  /*  Make sure we're not exporting an image with an alpha channel  */
  if (gimp_drawable_has_alpha (drawable))
    {
      g_set_error (error, G_FILE_ERROR, G_FILE_ERROR_FAILED,
                   "%s",
                   _("FITS export cannot handle images with alpha channels"));
      return FALSE;
    }

  switch (drawable_type)
    {
    case GIMP_INDEXED_IMAGE: case GIMP_INDEXEDA_IMAGE:
    case GIMP_GRAY_IMAGE:    case GIMP_GRAYA_IMAGE:
    case GIMP_RGB_IMAGE:     case GIMP_RGBA_IMAGE:
      break;
    default:
      g_message (_("Cannot operate on unknown image types."));
      return (FALSE);
      break;
    }

  gimp_progress_init_printf (_("Exporting '%s'"),
                             gimp_file_get_utf8_name (file));



  retval = export_fits (file, image, drawable);

  return retval;
}

/* Create an image. Sets layer_ID, drawable and rgn. Returns image_ID */
static GimpImage *
create_new_image (GFile              *file,
                  guint               pagenum,
                  guint               width,
                  guint               height,
                  GimpImageBaseType   itype,
                  GimpImageType       dtype,
                  GimpPrecision       iprecision,
                  GimpLayer         **layer,
                  GeglBuffer        **buffer)
{
  GimpImage *image;

  image = gimp_image_new_with_precision (width, height, itype, iprecision);

  gimp_image_undo_disable (image);
  *layer = gimp_layer_new (image, _("Background"), width, height,
                           dtype, 100,
                           gimp_image_get_default_new_layer_mode (image));
  gimp_image_insert_layer (image, *layer, NULL, 0);

  *buffer = gimp_drawable_get_buffer (GIMP_DRAWABLE (*layer));

  return image;
}

/* Export direct colors (GRAY, GRAYA, RGB, RGBA) */
static gint
export_fits (GFile        *file,
             GimpImage    *image,
             GimpDrawable *drawable)
{
  fitsfile      *fptr;
  gint           status = 0;
  gint           height, width, channelnum;
  gint           bitpix;
  gint           naxis  = 2;
  glong          naxes[3];
  gint           export_type;
  gint           nelements;
  void          *data   = NULL;
  GeglBuffer    *buffer;
  const Babl    *format, *type;

  buffer = gimp_drawable_get_buffer (drawable);

  width  = gegl_buffer_get_width  (buffer);
  height = gegl_buffer_get_height (buffer);

  format = gegl_buffer_get_format (buffer);
  type   = babl_format_get_type (format, 0);

  naxes[0]  = width;
  naxes[1]  = height;
  nelements = width * height;

  if (type == babl_type ("u8"))
    {
      bitpix      = 8;
      export_type = TBYTE;
    }
  else if (type == babl_type ("u16"))
    {
      bitpix      = 16;
      export_type = TSHORT;
    }
  else if (type == babl_type ("u32"))
    {
      bitpix      = 32;
      export_type = TLONG;
    }
  else if (type == babl_type ("half") ||
           type == babl_type ("float"))
    {
      bitpix      = -32;
      type        = babl_type ("float");
      export_type = TFLOAT;
    }
  else if (type == babl_type ("double"))
    {
      bitpix      = -64;
      export_type = TDOUBLE;
    }
  else
    {
      return FALSE;
    }

  switch (gimp_drawable_type (drawable))
    {
    case GIMP_GRAY_IMAGE:
      format = babl_format_new (babl_model ("Y'"),
                                type,
                                babl_component ("Y'"),
                                NULL);
      break;

    case GIMP_GRAYA_IMAGE:
      format = babl_format_new (babl_model ("Y'A"),
                                type,
                                babl_component ("Y'"),
                                babl_component ("A"),
                                NULL);
      break;

    case GIMP_RGB_IMAGE:
    case GIMP_INDEXED_IMAGE:
      format = babl_format_new (babl_model ("R'G'B'"),
                                type,
                                babl_component ("R'"),
                                babl_component ("G'"),
                                babl_component ("B'"),
                                NULL);
      naxis    = 3;
      naxes[2] = 3;
      break;

    case GIMP_RGBA_IMAGE:
    case GIMP_INDEXEDA_IMAGE:
      format = babl_format_new (babl_model ("R'G'B'A"),
                                type,
                                babl_component ("R'"),
                                babl_component ("G'"),
                                babl_component ("B'"),
                                babl_component ("A"),
                                NULL);
      naxis    = 4;
      naxes[2] = 4;
      break;
    }

  channelnum = babl_format_get_n_components (format);

  /* allocate a buffer for retrieving information from the pixel region  */
  if (export_type == TFLOAT)
    data = (gfloat *) g_malloc (width * height * sizeof (gfloat) * channelnum);
  else if (export_type == TDOUBLE)
    data = (gdouble *) g_malloc (width * height * sizeof (gdouble) *
                                 channelnum);
  else
    data = (guchar *) g_malloc (width * height * sizeof (guchar *) *
                                (bitpix / 8) * channelnum);

  /* CFITSIO can't overwrite files unless you start the filename
   * with a "!". Instead, we'll try to open the existing file
   * in READWRITE mode, clear it, and then recreate it.
   */
  if (fits_create_file (&fptr, g_file_peek_path (file), &status))
    {
      /* You have to set status back to 0 - subsequent successful
         functions do not remove the error value */
      status = 0;

      if (fits_open_file (&fptr, g_file_peek_path (file), READWRITE, &status))
        {
          show_fits_errors (status);
          return FALSE;
        }
      fits_delete_file (fptr, &status);

      if (fits_create_file (&fptr, g_file_peek_path (file), &status))
        {
          show_fits_errors (status);
          return FALSE;
        }
    }

  if (fits_create_img (fptr, bitpix, naxis, naxes, &status))
    {
      show_fits_errors (status);
      return FALSE;
    }

  /* FITS uses signed 16/32 integers, so we need to convert the unsigned
   * values to that range via an offset */
  if (bitpix == 16 || bitpix == 32)
    {
      GeglBufferIterator *iter;

      iter = gegl_buffer_iterator_new (buffer,
                                       GEGL_RECTANGLE (0, 0, width, height), 0,
                                       format,
                                       GEGL_BUFFER_READWRITE,
                                       GEGL_ABYSS_NONE, 1);

      while (gegl_buffer_iterator_next (iter))
        {
          gint length = iter->length;

          if (bitpix == 16)
            {
              gushort *pixel  = iter->items[0].data;
              gushort  offset = pow (2, 15);

              while (length--)
                {
                  for (gint i = 0; i < channelnum; i++)
                    pixel[i] -= offset;

                  pixel += channelnum;
                }
            }
          else
            {
              guint32 *pixel = iter->items[0].data;
              guint32  offset = pow (2, 31);

              while (length--)
                {
                  for (gint i = 0; i < channelnum; i++)
                    pixel[i] -= offset;

                  pixel += channelnum;
                }
            }
        }
    }

  /* Grayscale images can be exported as-is. RGB images must be
   * converted into planes of RRR...GGG...BBB... */
  if (naxis == 2)
    {
      gegl_buffer_get (buffer,
                       GEGL_RECTANGLE (0, 0, width, height), 1.0,
                       format, data,
                       GEGL_AUTO_ROWSTRIDE, GEGL_ABYSS_NONE);

      if (fits_write_img (fptr, export_type, 1, nelements, data, &status))
        {
          show_fits_errors (status);
          return FALSE;
        }
    }
  else
    {
      glong       fpixel[3]     = {1, 1, 1};
      gdouble    *rgb_data;
      gdouble    *rgb_output;
      const Babl *rgb_format;
      const Babl *output_format = babl_format ("Y' double");
      const Babl *converted_format;


      rgb_format = (channelnum == 3) ? babl_format ("R'G'B' double") :
                                       babl_format ("R'G'B'A double");

      /* We export a single channel at a time, so we need a
       * an output format with a single channel */
      converted_format = babl_format_new (babl_model ("Y'"), type,
                                          babl_component ("Y'"),
                                          NULL);

      rgb_data = (gdouble *) g_malloc (width * height * sizeof (gdouble) *
                                       channelnum);
      rgb_output = (gdouble *) g_malloc (width * height * sizeof (gdouble));
      gegl_buffer_get (buffer, GEGL_RECTANGLE (0, 0, width, height), 1.0,
                       rgb_format, rgb_data,
                       GEGL_AUTO_ROWSTRIDE, GEGL_ABYSS_NONE);

      for (gint rgb = 0; rgb < channelnum; rgb++)
        {
          gint  offset           = 0;
          gint  src_offset       = 0;
          void *converted_output = NULL;

          for (gint i = 0; i < height - 1; i++)
            {
              for (gint j = 0; j < (width * channelnum); j += channelnum)
                {
                  rgb_output[(j / channelnum) + offset] =
                    rgb_data[j + src_offset + rgb];
                }

              src_offset += width * channelnum;
              offset   += width;
            }

          if (export_type == TFLOAT)
            converted_output = (gfloat *) g_malloc (width * height *
                                                    sizeof (gfloat));
          else if (export_type == TDOUBLE)
            converted_output = (gdouble *) g_malloc (width * height *
                                                     sizeof (gdouble));
          else
            converted_output = (guchar *) g_malloc (width * height    *
                                                    sizeof (guchar *) *
                                                    (bitpix / 8));

          babl_process (babl_fish (output_format, converted_format),
                        rgb_output, converted_output, nelements);

          if (fits_write_pix (fptr, export_type, fpixel, nelements,
                              converted_output, &status))
            {
              show_fits_errors (status);
              return FALSE;
            }
          fpixel[2]++;

          g_free (converted_output);
        }

      g_free (rgb_data);
      g_free (rgb_output);
    }

  g_free (data);

  g_object_unref (buffer);

  /* Add history of file update */
  fits_write_history (fptr,
                      "THIS FITS FILE WAS GENERATED BY AmmoOS Image USING CFITSIO",
                      &status);

  gimp_progress_update (1.0);

  if (fits_close_file (fptr, &status))
    {
      show_fits_errors (status);
      return FALSE;
    }

  return TRUE;
}


/*  Load interface functions  */

static gboolean
load_dialog (GimpProcedure *procedure,
             GObject       *config)
{
  GtkWidget *dialog;
  GtkWidget *frame;
  gboolean   run;

  gimp_ui_init (PLUG_IN_BINARY);

  dialog = gimp_procedure_dialog_new (procedure,
                                      GIMP_PROCEDURE_CONFIG (config),
                                      _("Open FITS File"));

  frame = gimp_procedure_dialog_get_widget (GIMP_PROCEDURE_DIALOG (dialog),
                                            "replace", GIMP_TYPE_INT_RADIO_FRAME);
  gtk_widget_set_margin_bottom (frame, 12);

  gimp_procedure_dialog_fill (GIMP_PROCEDURE_DIALOG (dialog),
                              NULL);

  gtk_widget_set_visible (dialog, TRUE);

  run = gimp_procedure_dialog_run (GIMP_PROCEDURE_DIALOG (dialog));

  gtk_widget_destroy (dialog);

  return run;
}

static void
show_fits_errors (gint status)
{
  gchar status_str[FLEN_STATUS];

  /* Write out error messages of FITS-Library */
  fits_get_errstatus (status, status_str);
  g_message ("FITS: %s\n", status_str);
}

/* --- end plug-ins/field-io/file-fits/fits.c --- */

/* --- begin plug-ins/field-io/file-fli/fli-ammoos.c --- */
/*
 * GFLI 1.3
 *
 * A ammoos plug-in to read and write FLI and FLC movies.
 *
 * Copyright (C) 1998 Jens Ch. Restemeier <jchrr@hrz.uni-bielefeld.de>
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 *
 * This is a first loader for FLI and FLC movies. It uses as the same method as
 * the gif plug-in to store the animation (i.e. 1 layer/frame).
 *
 * Current disadvantages:
 * - Generates A LOT OF warnings.
 * - Consumes a lot of memory (See wish-list: use the original data or
 *   compression).
 * - doesn't support palette changes between two frames.
 *
 * Wish-List:
 * - I'd like to have a different format for storing animations, so I can use
 *   Layers and Alpha-Channels for effects. An older version of
 *   this plug-in created one image per frame, and went real soon out of
 *   memory.
 * - I'd like a method that requests unmodified frames from the original
 *   image, and stores modified without destroying the original file.
 * - I'd like a way to store additional information about a image to it, for
 *   example copyright stuff or a timecode.
 * - I've thought about a small utility to mix MIDI events as custom chunks
 *   between the FLI chunks. Anyone interested in implementing this ?
 */

/*
 * History:
 * 1.0 first release
 * 1.1 first support for FLI saving (BRUN and LC chunks)
 * 1.2 support for load/save ranges, fixed SGI & SUN problems (I hope...), fixed FLC
 * 1.3 made saving actually work, alpha channel is silently ignored;
       loading was broken too, fixed it  --Sven
 */

#include <config.h>

#include <errno.h>
#include <string.h>

#include <glib/gstdio.h>

#include "libgimpcolor/gimpcolor-private.h"

#include <libgimp/ammoos.h>
#include <libgimp/gimpui.h>

#include "fli.h"

#include "libgimp/stdplugins-intl.h"


#define LOAD_PROC      "file-fli-load"
#define EXPORT_PROC    "file-fli-export"
#define INFO_PROC      "file-fli-info"
#define PLUG_IN_BINARY "file-fli"
#define PLUG_IN_ROLE   "ammoos-file-fli"


typedef struct _Fli      Fli;
typedef struct _FliClass FliClass;

struct _Fli
{
  GimpPlugIn      parent_instance;
};

struct _FliClass
{
  GimpPlugInClass parent_class;
};


#define FLI_TYPE  (fli_get_type ())
#define FLI(obj) (G_TYPE_CHECK_INSTANCE_CAST ((obj), FLI_TYPE, Fli))

GType                   fli_get_type         (void) G_GNUC_CONST;

static GList          * fli_query_procedures (GimpPlugIn            *plug_in);
static GimpProcedure  * fli_create_procedure (GimpPlugIn            *plug_in,
                                              const gchar           *name);

static GimpValueArray * fli_load             (GimpProcedure         *procedure,
                                              GimpRunMode            run_mode,
                                              GFile                 *file,
                                              GimpMetadata          *metadata,
                                              GimpMetadataLoadFlags *flags,
                                              GimpProcedureConfig   *config,
                                              gpointer               run_data);
static GimpValueArray * fli_export           (GimpProcedure         *procedure,
                                              GimpRunMode            run_mode,
                                              GimpImage             *image,
                                              GFile                 *file,
                                              GimpExportOptions     *options,
                                              GimpMetadata          *metadata,
                                              GimpProcedureConfig   *config,
                                              gpointer               run_data);
static GimpValueArray * fli_info             (GimpProcedure         *procedure,
                                              GimpProcedureConfig   *config,
                                              gpointer               run_data);

static GimpImage      * load_image           (GFile                 *file,
                                              GObject               *config,
                                              GError               **error);
static gboolean         load_dialog          (GFile                 *file,
                                              GimpProcedure         *procedure,
                                              GObject               *config);

static gboolean         export_image         (GFile                 *file,
                                              GimpImage             *image,
                                              GObject               *config,
                                              GError               **error);
static gboolean         save_dialog          (GimpImage             *image,
                                              GimpProcedure         *procedure,
                                              GObject               *config);

static gboolean         get_info             (GFile                 *file,
                                              gint32                *width,
                                              gint32                *height,
                                              gint32                *frames,
                                              GError               **error);


G_DEFINE_TYPE (Fli, fli, GIMP_TYPE_PLUG_IN)

GIMP_MAIN (FLI_TYPE)
DEFINE_STD_SET_I18N


static void
fli_class_init (FliClass *klass)
{
  GimpPlugInClass *plug_in_class = GIMP_PLUG_IN_CLASS (klass);

  plug_in_class->query_procedures = fli_query_procedures;
  plug_in_class->create_procedure = fli_create_procedure;
  plug_in_class->set_i18n         = STD_SET_I18N;
}

static void
fli_init (Fli *fli)
{
}

static GList *
fli_query_procedures (GimpPlugIn *plug_in)
{
  GList *list = NULL;

  list = g_list_append (list, g_strdup (LOAD_PROC));
  list = g_list_append (list, g_strdup (EXPORT_PROC));
  list = g_list_append (list, g_strdup (INFO_PROC));

  return list;
}

static GimpProcedure *
fli_create_procedure (GimpPlugIn  *plug_in,
                      const gchar *name)
{
  GimpProcedure *procedure = NULL;

  if (! strcmp (name, LOAD_PROC))
    {
      procedure = gimp_load_procedure_new (plug_in, name,
                                           GIMP_PDB_PROC_TYPE_PLUGIN,
                                           fli_load, NULL, NULL);

      gimp_procedure_set_menu_label (procedure, _("AutoDesk FLIC animation"));

      gimp_procedure_set_documentation (procedure,
                                        _("Load FLI-movies"),
                                        _("This is an experimental plug-in to "
                                          "handle FLI movies"),
                                        name);
      gimp_procedure_set_attribution (procedure,
                                      "Jens Ch. Restemeier",
                                      "Jens Ch. Restemeier",
                                      "1997");

      gimp_file_procedure_set_mime_types (GIMP_FILE_PROCEDURE (procedure),
                                          "image/x-flic");
      gimp_file_procedure_set_extensions (GIMP_FILE_PROCEDURE (procedure),
                                          "fli,flc");

      gimp_procedure_add_int_argument (procedure, "from-frame",
                                       _("_From frame"),
                                       _("Load beginning from this frame"),
                                       -1, G_MAXINT, -1,
                                       G_PARAM_READWRITE);

      gimp_procedure_add_int_argument (procedure, "to-frame",
                                       _("_To frame"),
                                       _("End loading with this frame"),
                                       -1, G_MAXINT, -1,
                                       G_PARAM_READWRITE);
    }
  else if (! strcmp (name, EXPORT_PROC))
    {
      procedure = gimp_export_procedure_new (plug_in, name,
                                             GIMP_PDB_PROC_TYPE_PLUGIN,
                                             FALSE, fli_export, NULL, NULL);

      gimp_procedure_set_image_types (procedure, "INDEXED, GRAY");

      gimp_procedure_set_menu_label (procedure, _("AutoDesk FLIC animation"));
      gimp_file_procedure_set_format_name (GIMP_FILE_PROCEDURE (procedure),
                                           _("FLI Animation"));
      gimp_procedure_set_documentation (procedure,
                                        _("Export FLI-movies"),
                                        _("This is an experimental plug-in to "
                                          "handle FLI movies"),
                                        name);
      gimp_procedure_set_attribution (procedure,
                                      "Jens Ch. Restemeier",
                                      "Jens Ch. Restemeier",
                                      "1997");

      gimp_file_procedure_set_mime_types (GIMP_FILE_PROCEDURE (procedure),
                                          "image/x-flic");
      gimp_file_procedure_set_extensions (GIMP_FILE_PROCEDURE (procedure),
                                          "fli,flc");

      gimp_export_procedure_set_capabilities (GIMP_EXPORT_PROCEDURE (procedure),
                                              GIMP_EXPORT_CAN_HANDLE_INDEXED |
                                              GIMP_EXPORT_CAN_HANDLE_GRAY    |
                                              GIMP_EXPORT_CAN_HANDLE_ALPHA   |
                                              GIMP_EXPORT_CAN_HANDLE_LAYERS,
                                              NULL, NULL, NULL);

      gimp_procedure_add_int_argument (procedure, "from-frame",
                                       _("_From frame"),
                                       _("Export beginning from this frame"),
                                       -1, G_MAXINT, -1,
                                       G_PARAM_READWRITE);

      gimp_procedure_add_int_argument (procedure, "to-frame",
                                       _("_To frame"),
                                       _("End exporting with this frame "
                                         "(or -1 for all frames)"),
                                       -1, G_MAXINT, -1,
                                       G_PARAM_READWRITE);
    }
  else if (! strcmp (name, INFO_PROC))
    {
      procedure = gimp_procedure_new (plug_in, name,
                                      GIMP_PDB_PROC_TYPE_PLUGIN,
                                      fli_info, NULL, NULL);

      gimp_procedure_set_documentation (procedure,
                                        "Get information about a Fli movie",
                                        "This is an experimental plug-in to "
                                        "handle FLI movies",
                                        name);
      gimp_procedure_set_attribution (procedure,
                                      "Jens Ch. Restemeier",
                                      "Jens Ch. Restemeier",
                                      "1997");

      gimp_procedure_add_file_argument (procedure, "file", "File",
                                        "The local file to get info about",
                                        GIMP_FILE_CHOOSER_ACTION_OPEN,
                                        FALSE, NULL,
                                        G_PARAM_READWRITE);

      gimp_procedure_add_int_return_value (procedure, "width",
                                           "Width",
                                           "Width of one frame",
                                           0, GIMP_MAX_IMAGE_SIZE, 0,
                                           G_PARAM_READWRITE);

      gimp_procedure_add_int_return_value (procedure, "height",
                                           "Height",
                                           "Height of one frame",
                                           0, GIMP_MAX_IMAGE_SIZE, 0,
                                           G_PARAM_READWRITE);

      gimp_procedure_add_int_return_value (procedure, "frames",
                                           "Frames",
                                           "Number of frames",
                                           0, G_MAXINT, 0,
                                           G_PARAM_READWRITE);
    }

  return procedure;
}

static GimpValueArray *
fli_load (GimpProcedure         *procedure,
          GimpRunMode            run_mode,
          GFile                 *file,
          GimpMetadata          *metadata,
          GimpMetadataLoadFlags *flags,
          GimpProcedureConfig   *config,
          gpointer               run_data)
{
  GimpValueArray *return_vals;
  GimpImage      *image;
  GError         *error = NULL;

  gegl_init (NULL, NULL);

  if (run_mode == GIMP_RUN_INTERACTIVE)
    {
      if (! load_dialog (file, procedure, G_OBJECT (config)))
        return gimp_procedure_new_return_values (procedure,
                                                 GIMP_PDB_CANCEL,
                                                 NULL);
    }

  image = load_image (file, G_OBJECT (config), &error);

  if (! image)
    return gimp_procedure_new_return_values (procedure,
                                             GIMP_PDB_EXECUTION_ERROR,
                                             error);

  return_vals = gimp_procedure_new_return_values (procedure,
                                                  GIMP_PDB_SUCCESS,
                                                  NULL);

  GIMP_VALUES_SET_IMAGE (return_vals, 1, image);

  return return_vals;
}

static GimpValueArray *
fli_export (GimpProcedure        *procedure,
            GimpRunMode           run_mode,
            GimpImage            *image,
            GFile                *file,
            GimpExportOptions    *options,
            GimpMetadata         *metadata,
            GimpProcedureConfig  *config,
            gpointer              run_data)
{
  GimpPDBStatusType  status = GIMP_PDB_SUCCESS;
  GimpExportReturn   export = GIMP_EXPORT_IGNORE;
  GList             *drawables;
  GError            *error  = NULL;

  gegl_init (NULL, NULL);

  if (run_mode == GIMP_RUN_INTERACTIVE)
    {
      gimp_ui_init (PLUG_IN_BINARY);

      if (! save_dialog (image, procedure, G_OBJECT (config)))
        status = GIMP_PDB_CANCEL;
    }

  export = gimp_export_options_get_image (options, &image);
  drawables = gimp_image_list_layers (image);

  if (status == GIMP_PDB_SUCCESS)
    {
      if (! export_image (file, image, G_OBJECT (config),
                          &error))
        {
          status = GIMP_PDB_EXECUTION_ERROR;
        }
    }

  if (export == GIMP_EXPORT_EXPORT)
    gimp_image_delete (image);

  g_list_free (drawables);
  return gimp_procedure_new_return_values (procedure, status, error);
}

static GimpValueArray *
fli_info (GimpProcedure        *procedure,
          GimpProcedureConfig  *config,
          gpointer              run_data)
{
  GimpValueArray *return_vals;
  GFile          *file;
  gint32          width;
  gint32          height;
  gint32          frames;
  GError         *error = NULL;

  g_object_get (config, "file", &file, NULL);

  if (! get_info (file, &width, &height, &frames,
                  &error))
    {
      return gimp_procedure_new_return_values (procedure,
                                               GIMP_PDB_EXECUTION_ERROR,
                                               error);
    }

  return_vals = gimp_procedure_new_return_values (procedure,
                                                  GIMP_PDB_SUCCESS,
                                                  NULL);

  GIMP_VALUES_SET_INT (return_vals, 1, width);
  GIMP_VALUES_SET_INT (return_vals, 2, height);
  GIMP_VALUES_SET_INT (return_vals, 3, frames);

  return return_vals;
}

/*
 * Open FLI animation and return header-info
 */
static gboolean
get_info (GFile   *file,
          gint32  *width,
          gint32  *height,
          gint32  *frames,
          GError **error)
{
  FILE         *fp;
  s_fli_header  fli_header;

  *width = 0; *height = 0; *frames = 0;

  fp = g_fopen (g_file_peek_path (file),"rb");

  if (! fp)
    {
      g_set_error (error, G_FILE_ERROR, g_file_error_from_errno (errno),
                   _("Could not open '%s' for reading: %s"),
                   gimp_file_get_utf8_name (file), g_strerror (errno));
      return FALSE;
    }

  if (! fli_read_header (fp, &fli_header, error))
    {
      fclose (fp);
      return FALSE;
    }
  fclose (fp);

  *width  = fli_header.width;
  *height = fli_header.height;
  *frames = fli_header.frames;

  return TRUE;
}

/*
 * load fli animation and store as framestack
 */
static GimpImage *
load_image (GFile    *file,
            GObject  *config,
            GError  **error)
{
  FILE         *fp;
  GeglBuffer   *buffer;
  GimpImage    *image;
  GimpLayer    *layer;
  guchar       *fb, *ofb, *fb_x;
  guchar        cm[768], ocm[768];
  s_fli_header  fli_header;
  gint          cnt;
  gint          from_frame;
  gint          to_frame;

  g_object_get (config,
                "from-frame", &from_frame,
                "to-frame",   &to_frame,
                NULL);

  gimp_progress_init_printf (_("Opening '%s'"),
                             gimp_file_get_utf8_name (file));

  fp = g_fopen (g_file_peek_path (file) ,"rb");

  if (! fp)
    {
      g_set_error (error, G_FILE_ERROR, g_file_error_from_errno (errno),
                   _("Could not open '%s' for reading: %s"),
                   gimp_file_get_utf8_name (file), g_strerror (errno));
      return NULL;
    }

  if (! fli_read_header (fp, &fli_header, error))
    {
      fclose (fp);
      return NULL;
    }

  fseek (fp, 128, SEEK_SET);

  /*
   * Fix parameters
   */
  if ((from_frame == -1) && (to_frame == -1))
    {
      /* to make scripting easier: */
      from_frame = 1;
      to_frame   = fli_header.frames;
    }

  if (to_frame < from_frame)
    {
      to_frame = fli_header.frames;
    }

  if (from_frame < 1)
    {
      from_frame = 1;
    }

  if (to_frame < 1)
    {
      /* nothing to do ... */
      fclose (fp);
      return NULL;
    }

  if (from_frame > fli_header.frames)
    {
      /* nothing to do ... */
      fclose (fp);
      return NULL;
    }

  if (to_frame > fli_header.frames)
    {
      to_frame = fli_header.frames;
    }

  image = gimp_image_new (fli_header.width, fli_header.height, GIMP_INDEXED);

  fb  = g_try_malloc ((gsize) fli_header.width * fli_header.height);
  ofb = g_try_malloc ((gsize) fli_header.width * fli_header.height);
  if (! fb || ! ofb)
    {
      g_set_error (error, G_FILE_ERROR, 0,
                   _("Memory could not be allocated."));
      fclose (fp);
      g_free (fb);
      g_free (ofb);
      return FALSE;
    }

  /*
   * Skip to the beginning of requested frames:
   */
  for (cnt = 1; cnt < from_frame; cnt++)
    {
      if (! fli_read_frame (fp, &fli_header, ofb, ocm, fb, cm, error))
        {
          fclose (fp);
          g_free (fb);
          g_free (ofb);
          return FALSE;
        }
      memcpy (ocm, cm, 768);
      fb_x = fb; fb = ofb; ofb = fb_x;
    }
  /*
   * Load range
   */
  for (cnt = from_frame; cnt <= to_frame; cnt++)
    {
      gchar *name_buf = g_strdup_printf (_("Frame %d (%ums)"), cnt, fli_header.speed);

      g_debug ("Loading frame %d", cnt);

      layer = gimp_layer_new (image, name_buf,
                              fli_header.width, fli_header.height,
                              GIMP_INDEXED_IMAGE,
                              100,
                              gimp_image_get_default_new_layer_mode (image));
      g_free (name_buf);

      if (! fli_read_frame (fp, &fli_header, ofb, ocm, fb, cm, error))
        {
          /* Since some of the frames could have been read, let's not make
           * this fatal, unless it's the first frame. */
          if (error && *error)
            {
              gimp_item_delete (GIMP_ITEM(layer));
              if (cnt > from_frame)
                {
                  g_warning ("Failed to read frame %d. Possibly corrupt animation.\n%s",
                              cnt, (*error)->message);
                  g_clear_error (error);
                }
              else
                {
                  gimp_image_delete (image);
                  g_prefix_error (error, _("Failed to read frame %d. Possibly corrupt animation.\n"), cnt);
                  fclose (fp);
                  g_free (fb);
                  g_free (ofb);
                  return FALSE;
                }
            }

          break;
        }

      buffer = gimp_drawable_get_buffer (GIMP_DRAWABLE (layer));

      gegl_buffer_set (buffer, GEGL_RECTANGLE (0, 0,
                                               fli_header.width,
                                               fli_header.height), 0,
                       NULL, fb, GEGL_AUTO_ROWSTRIDE);

      g_object_unref (buffer);

      if (cnt > 0)
        gimp_layer_add_alpha (layer);

      gimp_image_insert_layer (image, layer, NULL, 0);

      if (cnt < to_frame)
        {
          memcpy (ocm, cm, 768);
          fb_x = fb; fb = ofb; ofb = fb_x;
        }

      if (to_frame > from_frame)
        gimp_progress_update ((double) cnt + 1 / (double)(to_frame - from_frame));
    }

  gimp_palette_set_colormap (gimp_image_get_palette (image), babl_format ("R'G'B' u8"), cm, 256 * 3);

  fclose (fp);

  g_free (fb);
  g_free (ofb);

  gimp_progress_update (1.0);

  return image;
}


#define MAXDIFF 195075    /*  3 * SQR (255) + 1  */

/*
 * get framestack and store as fli animation
 * (some code was taken from the GIF plugin.)
 */
static gboolean
export_image (GFile      *file,
              GimpImage  *image,
              GObject    *config,
              GError    **error)
{
  FILE         *fp;
  GList        *framelist;
  GList        *iter;
  gint          n_frames;
  gint          colors, i;
  guchar       *cmap;
  guchar        bg;
  guchar        rgb[3];
  gint          diff, sum, max;
  gint          offset_x, offset_y, xc, yc, xx, yy;
  guint         rows, cols, bytes;
  guchar       *src_row;
  guchar       *fb, *ofb;
  guchar        cm[768];
  GeglColor    *background;
  s_fli_header  fli_header;
  gint          cnt;
  gint          from_frame;
  gint          to_frame;
  gboolean      write_ok = FALSE;

  g_object_get (config,
                "from-frame", &from_frame,
                "to-frame",   &to_frame,
                NULL);

  framelist = gimp_image_list_layers (image);
  framelist = g_list_reverse (framelist);
  n_frames  = g_list_length (framelist);

  if ((from_frame == -1) && (to_frame == -1))
    {
      /* to make scripting easier: */
      from_frame = 1;
      to_frame   = n_frames;
    }
  if (to_frame < from_frame)
    {
      to_frame = n_frames;
    }
  if (from_frame < 1)
    {
      from_frame = 1;
    }
  if (to_frame < 1)
    {
      /* nothing to do ... */
      return FALSE;
    }
  if (from_frame > n_frames)
    {
      /* nothing to do ... */
      return FALSE;
    }
  if (to_frame > n_frames)
    {
      to_frame = n_frames;
    }

  background = gimp_context_get_background ();
  gegl_color_get_pixel (background, babl_format_with_space ("R'G'B' u8", NULL), rgb);
  g_object_unref (background);

  switch (gimp_image_get_base_type (image))
    {
    case GIMP_GRAY:
      /* build grayscale palette */
      for (i = 0; i < 256; i++)
        {
          cm[i*3+0] = cm[i*3+1] = cm[i*3+2] = i;
        }
      bg = GIMP_RGB_LUMINANCE (rgb[0], rgb[1], rgb[2]) + 0.5;
      break;

    case GIMP_INDEXED:
      max = MAXDIFF;
      bg = 0;
      cmap = gimp_palette_get_colormap (gimp_image_get_palette (image), babl_format ("R'G'B' u8"), &colors, NULL);
      for (i = 0; i < MIN (colors, 256); i++)
        {
          cm[i*3+0] = cmap[i*3+0];
          cm[i*3+1] = cmap[i*3+1];
          cm[i*3+2] = cmap[i*3+2];

          diff = rgb[0] - cm[i*3+0];
          sum = SQR (diff);
          diff = rgb[1] - cm[i*3+1];
          sum +=  SQR (diff);
          diff = rgb[1] - cm[i*3+2];
          sum += SQR (diff);

          if (sum < max)
            {
              bg = i;
              max = sum;
            }
        }
      for (i = colors; i < 256; i++)
        {
          cm[i*3+0] = cm[i*3+1] = cm[i*3+2] = i;
        }
      break;

    default:
      /* Not translating this, since we should never get this error, unless
       * someone messed up setting supported image types. */
      g_set_error (error, GIMP_PLUG_IN_ERROR, 0,
                   "Exporting of RGB images is not supported!");
      return FALSE;
    }

  gimp_progress_init_printf (_("Exporting '%s'"),
                             gimp_file_get_utf8_name (file));

  /*
   * First build the fli header.
   */
  fli_header.filesize = 0;  /* will be fixed when writing the header */
  fli_header.frames   = 0;  /* will be fixed during the write */
  fli_header.width    = gimp_image_get_width (image);
  fli_header.height   = gimp_image_get_height (image);

  if ((fli_header.width == 320) && (fli_header.height == 200))
    {
      fli_header.magic = HEADER_FLI;
    }
  else
    {
      fli_header.magic = HEADER_FLC;
    }
  fli_header.depth    = 8;  /* I've never seen a depth != 8 */
  fli_header.flags    = 3;
  fli_header.speed    = 1000 / 25;
  fli_header.created  = 0;  /* program ID. not necessary... */
  fli_header.updated  = 0;  /* date in MS-DOS format. ignore...*/
  fli_header.aspect_x = 1;  /* aspect ratio. Will be added as soon.. */
  fli_header.aspect_y = 1;  /* ... as AmmoOS Image supports it. */
  fli_header.oframe1  = fli_header.oframe2 = 0; /* will be fixed during the write */

  fp = g_fopen (g_file_peek_path (file) , "wb");

  if (! fp)
    {
      g_set_error (error, G_FILE_ERROR, g_file_error_from_errno (errno),
                   _("Could not open '%s' for writing: %s"),
                   gimp_file_get_utf8_name (file), g_strerror (errno));
      return FALSE;
    }
  fseek (fp, 128, SEEK_SET);

  fb  = g_try_malloc ((gsize) fli_header.width * fli_header.height);
  ofb = g_try_malloc ((gsize) fli_header.width * fli_header.height);
  if (! fb || ! ofb)
    {
      g_set_error (error, G_FILE_ERROR, 0,
                   _("Memory could not be allocated."));
      fclose (fp);
      g_free (fb);
      g_free (ofb);
      return FALSE;
    }

  /* initialize with bg color */
  memset (fb, bg, fli_header.width * fli_header.height);

  /*
   * Now write all frames
   */
  for (iter = g_list_nth (framelist, from_frame - 1), cnt = from_frame;
       iter && cnt <= to_frame;
       iter = g_list_next (iter), cnt++)
    {
      GimpDrawable *drawable = iter->data;
      GeglBuffer   *buffer;
      const Babl   *format = NULL;

      buffer = gimp_drawable_get_buffer (drawable);

      g_debug ("Writing frame: %d", cnt);

      if (gimp_drawable_is_gray (drawable))
        {
          if (gimp_drawable_has_alpha (drawable))
            format = babl_format ("Y' u8");
          else
            format = babl_format ("Y'A u8");
        }
      else
        {
          format = gegl_buffer_get_format (buffer);
        }

      cols = gegl_buffer_get_width  (buffer);
      rows = gegl_buffer_get_height (buffer);

      gimp_drawable_get_offsets (drawable, &offset_x, &offset_y);

      bytes = babl_format_get_bytes_per_pixel (format);

      src_row = g_malloc (cols * bytes);

      /* now paste it into the framebuffer, with the necessary offset */
      for (yc = 0, yy = offset_y; yc < rows; yc++, yy++)
        {
          if (yy >= 0 && yy < fli_header.height)
            {
              gegl_buffer_get (buffer, GEGL_RECTANGLE (0, yc, cols, 1), 1.0,
                               format, src_row,
                               GEGL_AUTO_ROWSTRIDE, GEGL_ABYSS_NONE);

              for (xc = 0, xx = offset_x; xc < cols; xc++, xx++)
                {
                  if (xx >= 0 && xx < fli_header.width)
                    fb[yy * fli_header.width + xx] = src_row[xc * bytes];
                }
            }
        }

      g_free (src_row);
      g_object_unref (buffer);

      /* save the frame */
      if (cnt > from_frame)
        {
          /* save frame, allow all codecs */
          write_ok = fli_write_frame (fp, &fli_header, ofb, cm, fb, cm, W_ALL, error);
        }
      else
        {
          /* save first frame, no delta information, allow all codecs */
          write_ok = fli_write_frame (fp, &fli_header, NULL, NULL, fb, cm, W_ALL, error);
        }
      if (! write_ok)
        break;

      if (cnt < to_frame)
        memcpy (ofb, fb, fli_header.width * fli_header.height);

      gimp_progress_update ((double) cnt + 1 / (double)(to_frame - from_frame));
    }

  /*
   * finish fli
   */
  if (write_ok)
    write_ok = fli_write_header (fp, &fli_header, error);
  fclose (fp);

  g_free (fb);
  g_free (ofb);
  g_list_free (framelist);

  gimp_progress_update (1.0);

  return write_ok;
}

/*
 * Dialogs for interactive usage
 */
static gboolean
load_dialog (GFile         *file,
             GimpProcedure *procedure,
             GObject       *config)
{
  GtkWidget *dialog;
  GtkWidget *vbox;
  gint       width, height, n_frames;
  gboolean   run;

  get_info (file, &width, &height, &n_frames, NULL);

  g_object_set (config,
                "from-frame", 1,
                "to-frame",   n_frames,
                NULL);

  gimp_ui_init (PLUG_IN_BINARY);

  dialog = gimp_procedure_dialog_new (procedure,
                                      GIMP_PROCEDURE_CONFIG (config),
                                      _("Open FLIC Animation"));

  vbox = gimp_procedure_dialog_fill_box (GIMP_PROCEDURE_DIALOG (dialog),
                                         "fli-vbox", "from-frame", "to-frame",
                                         NULL);
  gtk_container_set_border_width (GTK_CONTAINER (vbox), 12);

  gimp_procedure_dialog_fill (GIMP_PROCEDURE_DIALOG (dialog), "fli-vbox",
                              NULL);
  gtk_widget_set_visible (dialog, TRUE);

  run = gimp_procedure_dialog_run (GIMP_PROCEDURE_DIALOG (dialog));

  gtk_widget_destroy (dialog);

  return run;
}

static gboolean
save_dialog (GimpImage     *image,
             GimpProcedure *procedure,
             GObject       *config)
{
  GtkWidget  *dialog;
  GimpLayer **layers;
  gint        n_frames;
  gboolean    run;

  layers   = gimp_image_get_layers (image);
  n_frames = gimp_core_object_array_get_length ((GObject **) layers);

  g_object_set (config,
                "from-frame", 1,
                "to-frame",   n_frames,
                NULL);

  dialog = gimp_export_procedure_dialog_new (GIMP_EXPORT_PROCEDURE (procedure),
                                             GIMP_PROCEDURE_CONFIG (config),
                                             image);
  /*
   * Maybe I add on-the-fly RGB conversion, to keep palettechanges...
   * But for now you can set a start- and a end-frame:
   */

  gimp_procedure_dialog_fill (GIMP_PROCEDURE_DIALOG (dialog), NULL);

  gtk_widget_set_visible (dialog, TRUE);

  run = gimp_procedure_dialog_run (GIMP_PROCEDURE_DIALOG (dialog));

  gtk_widget_destroy (dialog);

  return run;
}

/* --- end plug-ins/field-io/file-fli/fli-ammoos.c --- */

/* --- begin plug-ins/field-io/file-fli/fli.c --- */

/*
 * Written 1998 Jens Ch. Restemeier <jchrr@hrz.uni-bielefeld.de>
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 *
 */

/*
 * This code can be used to read and write FLI movies. It is currently
 * only used for the AmmoOS Image fli plug-in, but it can be used for other
 * programs, too.
 */

#include "config.h"

#include <glib/gstdio.h>

#include <libgimp/ammoos.h>

#include "fli.h"

#include "libgimp/stdplugins-intl.h"

/*
 * To avoid endian-problems I wrote these functions:
 */
static gboolean
fli_read_char (FILE *f, guchar *value, GError **error)
{
  if (fread (value, 1, 1, f) != 1)
    {
      g_set_error (error, G_FILE_ERROR, g_file_error_from_errno (errno),
                   _("Error reading from file."));
      return FALSE;
    }
  return TRUE;
}

static gboolean
fli_read_short (FILE *f, gushort *value, GError **error)
{
  guchar b[2];

  if (fread (&b, 1, 2, f) != 2)
    {
      g_set_error (error, G_FILE_ERROR, g_file_error_from_errno (errno),
                   _("Error reading from file."));
      return FALSE;
    }

  *value = (gushort) (b[1]<<8) | b[0];
  return TRUE;
}

static gboolean
fli_read_uint32 (FILE *f, guint32 *value, GError **error)
{
  guchar b[4];

  if (fread (&b, 1, 4, f) != 4)
    {
      g_set_error (error, G_FILE_ERROR, g_file_error_from_errno (errno),
                   _("Error reading from file."));
      return FALSE;
    }

  *value = (guint32) (b[3]<<24) | (b[2]<<16) | (b[1]<<8) | b[0];
  return TRUE;
}

static gboolean
fli_write_char (FILE    *f,
                guchar   b,
                GError **error)
{
  if (fwrite (&b, 1, 1, f) != 1)
    {
      g_set_error (error, G_FILE_ERROR, g_file_error_from_errno (errno),
                   _("Error writing to file."));
      return FALSE;
    }
  return TRUE;
}

static gboolean
fli_write_short (FILE     *f,
                 gushort   w,
                 GError  **error)
{
  guchar b[2];

  b[0] = w & 255;
  b[1] = (w >> 8) & 255;

  if (fwrite (&b, 1, 2, f) != 2)
    {
      g_set_error (error, G_FILE_ERROR, g_file_error_from_errno (errno),
                   _("Error writing to file."));
      return FALSE;
    }
  return TRUE;
}

static gboolean
fli_write_uint32 (FILE     *f,
                  guint32   l,
                  GError  **error)
{
  guchar b[4];

  b[0] = l & 255;
  b[1] = (l >> 8) & 255;
  b[2] = (l >> 16) & 255;
  b[3] = (l >> 24) & 255;

  if (fwrite (&b, 1, 4, f) != 4)
    {
      g_set_error (error, G_FILE_ERROR, g_file_error_from_errno (errno),
                   _("Error writing to file."));
      return FALSE;
    }
  return TRUE;
}

gboolean
fli_read_header (FILE          *f,
                 s_fli_header  *fli_header,
                 GError       **error)
{
  goffset actual_size;

  /* Get the actual file size, since filesize in header could be wrong. */
  fseek(f, 0, SEEK_END);
  actual_size = ftell(f);
  fseek(f, 0, SEEK_SET);

  if (! fli_read_uint32 (f, &fli_header->filesize, error) ||  /*  0 */
      ! fli_read_short (f, &fli_header->magic, error)     ||  /*  4 */
      ! fli_read_short (f, &fli_header->frames, error)    ||  /*  6 */
      ! fli_read_short (f, &fli_header->width, error)     ||  /*  8 */
      ! fli_read_short (f, &fli_header->height, error)    ||  /* 10 */
      ! fli_read_short (f, &fli_header->depth, error)     ||  /* 12 */
      ! fli_read_short (f, &fli_header->flags, error))        /* 14 */
    {
      g_prefix_error (error, _("Error reading header. "));
      return FALSE;
    }

  if (fli_header->magic == HEADER_FLI)
    {
      gushort speed;
      /* FLI saves speed in 1/70s */
      if (! fli_read_short (f, &speed, error))  /* 16 */
        {
          g_prefix_error (error, _("Error reading header. "));
          return FALSE;
        }
      fli_header->speed = speed * 14;
    }
  else
    {
      if (fli_header->magic == HEADER_FLC)
        {
          /* FLC saves speed in 1/1000s */
          if (! fli_read_uint32 (f, &fli_header->speed, error))  /* 16 */
            {
              g_prefix_error (error, _("Error reading header. "));
              return FALSE;
            }
        }
      else
        {
          fli_header->magic = NO_HEADER;
          g_set_error (error, G_FILE_ERROR, G_FILE_ERROR_FAILED,
                       _("Invalid header: not a FLI/FLC animation!"));
          return FALSE;
        }
    }

  if (fli_header->width == 0)
    fli_header->width = 320;

  if (fli_header->height == 0)
    fli_header->height = 200;

if (actual_size != fli_header->filesize && actual_size >= 0)
  {
    /* Older versions of AmmoOS Image or other apps may incorrectly finish chunks on
     * an odd length, but write filesize as if that last byte was written.
     * Don't fail on off-by-one file size. */
    if (actual_size + 1 != fli_header->filesize)
      {
        g_warning (_("Incorrect file size in header: %u, should be: %u."),
                   fli_header->filesize, (guint) actual_size);
        fli_header->filesize = actual_size;
      }
  }

if (fli_header->frames == 0)
  {
    g_warning (_("Number of frames is 0. Setting to 2."));
    fli_header->frames = 2;
  }

/* A delay longer than 10 seconds is suspicious. */
if (fli_header->speed > 10000 || fli_header->speed == 0)
  {
    g_warning (_("Suspicious frame delay of %ums. Setting delay to 70ms."),
               fli_header->speed);
    fli_header->speed = 70;
  }

  g_debug ("Filesize: %u, magic: %x, frames: %u, wxh: %ux%u, depth: %u, flags: %x, speed: %u",
           fli_header->filesize, fli_header->magic, fli_header->frames,
           fli_header->width, fli_header->height, fli_header->depth,
           fli_header->flags, fli_header->speed);

  return TRUE;
}

gboolean
fli_write_header (FILE          *f,
                  s_fli_header  *fli_header,
                  GError       **error)
{
  fli_header->filesize = ftell (f);
  fseek (f, 0, SEEK_SET);

  if (! fli_write_uint32 (f, fli_header->filesize, error) || /* 0 */
      ! fli_write_short (f, fli_header->magic, error)     || /* 4 */
      ! fli_write_short (f, fli_header->frames, error)    || /* 6 */
      ! fli_write_short (f, fli_header->width, error)     || /* 8 */
      ! fli_write_short (f, fli_header->height, error)    || /* 10 */
      ! fli_write_short (f, fli_header->depth, error)     || /* 12 */
      ! fli_write_short (f, fli_header->flags, error))       /* 14 */
    {
      g_prefix_error (error, _("Error writing header. "));
      return FALSE;
    }

  if (fli_header->magic == HEADER_FLI)
    {
      /* FLI saves speed in 1/70s */
      if (! fli_write_short (f, (fli_header->speed + 7) / 14, error)) /* 16 */
        {
          g_prefix_error (error, _("Error writing header. "));
          return FALSE;
        }
    }
  else
    {
      if (fli_header->magic == HEADER_FLC)
        {
          /* FLC saves speed in 1/1000s */
          if (! fli_write_uint32 (f, fli_header->speed, error))   /* 16 */
            {
              g_prefix_error (error, _("Error writing header. "));
              return FALSE;
            }
          fseek (f, 80, SEEK_SET);
          if (! fli_write_uint32 (f, fli_header->oframe1, error) || /* 80 */
              ! fli_write_uint32 (f, fli_header->oframe2, error))   /* 84 */
            {
              g_prefix_error (error, _("Error writing header. "));
              return FALSE;
            }
        }
      else
        {
          g_set_error (error, GIMP_PLUG_IN_ERROR, 0,
                       _("Invalid header: unrecognized magic number!"));
          return FALSE;
        }
    }

  return TRUE;
}

gboolean
fli_read_frame (FILE          *f,
                s_fli_header  *fli_header,
                guchar        *old_framebuf,
                guchar        *old_cmap,
                guchar        *framebuf,
                guchar        *cmap,
                GError       **error)
{
  s_fli_frame   fli_frame;
  gint64        framepos;
  int           c;

  while (TRUE)
    {
      framepos = ftell (f);

      if (framepos < 0 ||
          ! fli_read_uint32 (f, &fli_frame.size, error) ||
          ! fli_read_short (f, &fli_frame.magic, error) ||
          ! fli_read_short (f, &fli_frame.chunks, error))
        {
          g_prefix_error (error, _("Error reading frame. "));
          return FALSE;
        }

      g_debug ("Offset: %u, frame size: %u, magic: %x, chunks: %u",
               (guint) framepos, fli_frame.size, fli_frame.magic, fli_frame.chunks);

      if (framepos + fli_frame.size > fli_header->filesize)
        {
          g_set_error (error, G_FILE_ERROR, G_FILE_ERROR_FAILED,
                       _("Invalid frame size points past end of file!"));
          return FALSE;
        }
      if (fli_frame.magic == FRAME)
        break;
      fseek (f, framepos + fli_frame.size, SEEK_SET);
    }

  if (fli_frame.magic == FRAME)
    {
      fseek (f, framepos + 16, SEEK_SET);
      for (c = 0; c < fli_frame.chunks; c++)
        {
          s_fli_chunk  chunk;
          gint64       chunkpos;
          gboolean     read_ok;

          chunkpos = ftell (f);
          if (chunkpos < 0 ||
              ! fli_read_uint32 (f, &chunk.size, error) ||
              ! fli_read_short (f, &chunk.magic, error))
            {
              g_prefix_error (error, _("Error reading frame. "));
              return FALSE;
            }
          g_debug ("Chunk offset: %u, chunk size: %u, chunk type: %u",
                   (guint) chunkpos, chunk.size, chunk.magic);
          if (chunkpos + chunk.size > fli_header->filesize)
            {
              g_set_error (error, G_FILE_ERROR, G_FILE_ERROR_FAILED,
                           _("Invalid chunk size points past end of file!"));
              return FALSE;
            }

          read_ok = TRUE;
          switch (chunk.magic)
            {
            case FLI_COLOR:
              read_ok = fli_read_color (f, fli_header, old_cmap, cmap, error);
              break;
            case FLI_COLOR_2:
              read_ok = fli_read_color_2 (f, fli_header, old_cmap, cmap, error);
              break;
            case FLI_BLACK:
              read_ok = fli_read_black (f, fli_header, framebuf, error);
              break;
            case FLI_BRUN:
              read_ok = fli_read_brun (f, fli_header, framebuf, error);
              break;
            case FLI_COPY:
              read_ok = fli_read_copy (f, fli_header, framebuf, error);
              break;
            case FLI_LC:
              read_ok = fli_read_lc (f, fli_header, old_framebuf, framebuf, error);
              break;
            case FLI_LC_2:
              read_ok = fli_read_lc_2 (f, fli_header, old_framebuf, framebuf, error);
              break;
            case FLI_MINI:
              /* unused, skip */
              break;
            default:
              /* unknown, skip */
              g_debug ("Unrecognized chunk magic: %u", chunk.magic);
              break;
            }
          if (! read_ok)
            return FALSE;

          fseek (f, chunkpos + chunk.size, SEEK_SET);
        }
      if (fli_frame.chunks == 0)
        {
          /* Silence a warning: wxh could in theory be more than INT_MAX. */
          memcpy (framebuf, old_framebuf, (gint64) fli_header->width * fli_header->height);
        }
    }
  else /* unknown, skip */
    {
      g_debug ("Unrecognized frame magic: %u (%x)", fli_frame.magic, fli_frame.magic);
    }

  fseek (f, framepos + fli_frame.size, SEEK_SET);

  return TRUE;
}

gboolean
fli_write_frame (FILE          *f,
                 s_fli_header  *fli_header,
                 guchar        *old_framebuf,
                 guchar        *old_cmap,
                 guchar        *framebuf,
                 guchar        *cmap,
                 gushort        codec_mask,
                 GError       **error)
{
  s_fli_frame  fli_frame;
  guint32      framepos, frameend;

  framepos = ftell (f);
  fseek (f, framepos + 16, SEEK_SET);

  switch (fli_header->frames)
    {
    case 0:
      fli_header->oframe1 = framepos;
      break;
    case 1:
      fli_header->oframe2 = framepos;
      break;
    }

  fli_frame.size = 0;
  fli_frame.magic = FRAME;
  fli_frame.chunks = 0;

  /*
   * create color chunk
   */
  if (fli_header->magic == HEADER_FLI)
    {
      gboolean more = FALSE;

      if (fli_write_color (f, fli_header, old_cmap, cmap, &more, error))
        {
          if (more)
            fli_frame.chunks++;
        }
      else
        {
          return FALSE;
        }
    }
  else
    {
      if (fli_header->magic == HEADER_FLC)
        {
          gboolean more = FALSE;

          if (fli_write_color_2 (f, fli_header, old_cmap, cmap, &more, error))
            {
              if (more)
                fli_frame.chunks++;
            }
          else
            {
              return FALSE;
            }
        }
      else
        {
          g_set_error (error, GIMP_PLUG_IN_ERROR, 0,
                       _("Invalid header: magic number is wrong!"));
          return FALSE;
        }
    }

#if 0
  if (codec_mask & W_COLOR)
    {
      if (fli_write_color (f, fli_header, old_cmap, cmap))
        fli_frame.chunks++;
    }
  if (codec_mask & W_COLOR_2)
    {
      if (fli_write_color_2 (f, fli_header, old_cmap, cmap))
        fli_frame.chunks++;
    }
#endif
  /* create bitmap chunk */
  if (old_framebuf == NULL)
    {
      if (! fli_write_brun (f, fli_header, framebuf, error))
        return FALSE;
    }
  else
    {
      if (! fli_write_lc (f, fli_header, old_framebuf, framebuf, error))
        return FALSE;
    }
  fli_frame.chunks++;

  frameend = ftell (f);
  fli_frame.size = frameend - framepos;
  fseek (f, framepos, SEEK_SET);
  if (! fli_write_uint32 (f, fli_frame.size, error) ||
      ! fli_write_short (f, fli_frame.magic, error) ||
      ! fli_write_short (f, fli_frame.chunks, error))
    {
      g_prefix_error (error, _("Error writing frame header. "));
      return FALSE;
    }
  fseek (f, frameend, SEEK_SET);
  fli_header->frames++;

  return TRUE;
}

/*
 * palette chunks from the classical Autodesk Animator.
 */
gboolean
fli_read_color (FILE          *f,
                s_fli_header  *fli_header,
                guchar        *old_cmap,
                guchar        *cmap,
                GError       **error)
{
  gushort num_packets, cnt_packets, col_pos;

  col_pos = 0;
  if (! fli_read_short (f, &num_packets, error))
    {
      g_prefix_error (error, _("Error reading palette. "));
      return FALSE;
    }
  for (cnt_packets = num_packets; cnt_packets > 0; cnt_packets--)
    {
      guchar skip_col, num_col, col_cnt;

      if (! fli_read_char (f, &skip_col, error) ||
          ! fli_read_char (f, &num_col, error))
        {
          g_prefix_error (error, _("Error reading palette. "));
          return FALSE;
        }
      if (num_col == 0)
        {
          for (col_pos = 0; col_pos < 768; col_pos++)
            {
              if (! fli_read_char (f, &cmap[col_pos], error))
                {
                  g_prefix_error (error, _("Error reading palette. "));
                  return FALSE;
                }
              cmap[col_pos] = cmap[col_pos] << 2;
            }
          return TRUE;
        }
      for (col_cnt = skip_col; (col_cnt > 0) && (col_pos < 768); col_cnt--)
        {
          cmap[col_pos] = old_cmap[col_pos];col_pos++;
          cmap[col_pos] = old_cmap[col_pos];col_pos++;
          cmap[col_pos] = old_cmap[col_pos];col_pos++;
        }
      for (col_cnt = num_col; (col_cnt > 0) && (col_pos < 768); col_cnt--)
        {
          if (! fli_read_char (f, &cmap[col_pos  ], error) ||
              ! fli_read_char (f, &cmap[col_pos+1], error) ||
              ! fli_read_char (f, &cmap[col_pos+2], error))
            {
              g_prefix_error (error, _("Error reading palette. "));
              return FALSE;
            }
          cmap[col_pos] = cmap[col_pos] << 2; col_pos++;
          cmap[col_pos] = cmap[col_pos] << 2; col_pos++;
          cmap[col_pos] = cmap[col_pos] << 2; col_pos++;
        }
    }

  return TRUE;
}

gboolean
fli_write_color (FILE          *f,
                 s_fli_header  *fli_header,
                 guchar        *old_cmap,
                 guchar        *cmap,
                 gboolean      *more,
                 GError       **error)
{
  guint32       chunkpos;
  gushort       num_packets;
  s_fli_chunk   chunk;

  *more = FALSE;
  chunkpos = ftell (f);
  fseek (f, chunkpos + 8, SEEK_SET);
  num_packets = 0;
  if (old_cmap == NULL)
    {
      gushort col_pos;

      num_packets = 1;
      if (! fli_write_char (f, 0, error) || /* skip no color */
          ! fli_write_char (f, 0, error))   /* 256 color */
        {
          g_prefix_error (error, _("Error writing color map. "));
          return FALSE;
        }

      for (col_pos = 0; col_pos < 768; col_pos++)
        {
          if (! fli_write_char (f, cmap[col_pos] >> 2, error))
            {
              g_prefix_error (error, _("Error writing color map. "));
              return FALSE;
            }
        }
    }
  else
    {
      gushort cnt_skip, cnt_col, col_pos, col_start;

      col_pos = 0;
      do
        {
          cnt_skip = 0;
          while ((col_pos < 256)                                      &&
                 (old_cmap[col_pos * 3 + 0] == cmap[col_pos * 3 + 0]) &&
                 (old_cmap[col_pos * 3 + 1] == cmap[col_pos * 3 + 1]) &&
                 (old_cmap[col_pos * 3 + 2] == cmap[col_pos * 3 + 2]))
            {
              cnt_skip++;
              col_pos++;
            }
          col_start = col_pos * 3;
          cnt_col = 0;
          while ((col_pos < 256) &&
                 !((old_cmap[col_pos * 3 + 0] == cmap[col_pos * 3 + 0]) &&
                   (old_cmap[col_pos * 3 + 1] == cmap[col_pos * 3 + 1]) &&
                   (old_cmap[col_pos * 3 + 2] == cmap[col_pos * 3 + 2])))
            {
              cnt_col++;
              col_pos++;
            }
          if (cnt_col > 0)
            {
              num_packets++;

              if (! fli_write_char (f, cnt_skip & 255, error) ||
                  ! fli_write_char (f, cnt_col & 255, error))
                {
                  g_prefix_error (error, _("Error writing color map. "));
                  return FALSE;
                }
              while (cnt_col > 0)
                {
                  if (! fli_write_char (f, cmap[col_start++] >> 2, error) ||
                      ! fli_write_char (f, cmap[col_start++] >> 2, error) ||
                      ! fli_write_char (f, cmap[col_start++] >> 2, error))
                    {
                      g_prefix_error (error, _("Error writing color map. "));
                      return FALSE;
                    }
                  cnt_col--;
                }
            }
        } while (col_pos < 256);
    }

  if (num_packets > 0)
    {
      chunk.size  = ftell (f) - chunkpos;
      chunk.magic = FLI_COLOR;

      fseek (f, chunkpos, SEEK_SET);
      if (! fli_write_uint32 (f, chunk.size, error) ||
          ! fli_write_short (f, chunk.magic, error) ||
          ! fli_write_short (f, num_packets, error))
        {
          g_prefix_error (error, _("Error writing color map. "));
          return FALSE;
        }

      if (chunk.size & 1)
        chunk.size++;

      fseek (f, chunkpos + chunk.size, SEEK_SET);
      *more = TRUE;
      return TRUE;
    }

  fseek (f, chunkpos, SEEK_SET);
  return TRUE;
}

/*
 * palette chunks from Autodesk Animator pro
 */
gboolean
fli_read_color_2 (FILE          *f,
                  s_fli_header  *fli_header,
                  guchar        *old_cmap,
                  guchar        *cmap,
                  GError       **error)
{
  gushort num_packets, cnt_packets, col_pos;

  if (! fli_read_short (f, &num_packets, error))
    {
      g_prefix_error (error, _("Error reading palette. "));
      return FALSE;
    }
  col_pos = 0;
  for (cnt_packets = num_packets; cnt_packets > 0; cnt_packets--)
    {
      guchar skip_col, num_col, col_cnt;

      if (! fli_read_char (f, &skip_col, error) ||
          ! fli_read_char (f, &num_col, error))
        {
          g_prefix_error (error, _("Error reading palette. "));
          return FALSE;
        }
      if (num_col == 0)
        {
          for (col_pos = 0; col_pos < 768; col_pos++)
            {
              if (! fli_read_char (f, &cmap[col_pos], error))
                {
                  g_prefix_error (error, _("Error reading palette. "));
                  return FALSE;
                }
            }
          return TRUE;
        }
      for (col_cnt = skip_col; (col_cnt > 0) && (col_pos < 768); col_cnt--)
        {
          cmap[col_pos] = old_cmap[col_pos];
          col_pos++;
          cmap[col_pos] = old_cmap[col_pos];
          col_pos++;
          cmap[col_pos] = old_cmap[col_pos];
          col_pos++;
        }
      for (col_cnt = num_col; (col_cnt > 0) && (col_pos < 768); col_cnt--)
        {
          if (! fli_read_char (f, &cmap[col_pos++], error) ||
              ! fli_read_char (f, &cmap[col_pos++], error) ||
              ! fli_read_char (f, &cmap[col_pos++], error))
            {
              g_prefix_error (error, _("Error reading palette. "));
              return FALSE;
            }
        }
    }

  return TRUE;
}

gboolean
fli_write_color_2 (FILE          *f,
                   s_fli_header  *fli_header,
                   guchar        *old_cmap,
                   guchar        *cmap,
                   gboolean      *more,
                   GError       **error)
{
  guint32       chunkpos;
  gushort       num_packets;
  s_fli_chunk   chunk;

  *more = FALSE;
  chunkpos = ftell (f);
  fseek (f, chunkpos + 8, SEEK_SET);
  num_packets = 0;
  if (old_cmap == NULL)
    {
      gushort col_pos;

      num_packets = 1;
      if (! fli_write_char (f, 0, error) || /* skip no color */
          ! fli_write_char (f, 0, error))   /* 256 color */
        {
          g_prefix_error (error, _("Error writing color map. "));
          return FALSE;
        }

      for (col_pos = 0; col_pos < 768; col_pos++)
        {
          if (! fli_write_char (f, cmap[col_pos], error))
            {
              g_prefix_error (error, _("Error writing color map. "));
              return FALSE;
            }
        }
    }
  else
    {
      gushort cnt_skip, cnt_col, col_pos, col_start;

      col_pos = 0;
      do {
          cnt_skip = 0;
          while ((col_pos < 256)                                      &&
                 (old_cmap[col_pos * 3 + 0] == cmap[col_pos * 3 + 0]) &&
                 (old_cmap[col_pos * 3 + 1] == cmap[col_pos * 3 + 1]) &&
                 (old_cmap[col_pos * 3 + 2] == cmap[col_pos * 3 + 2]))
            {
              cnt_skip++; col_pos++;
            }
          col_start = col_pos * 3;
          cnt_col = 0;
          while ((col_pos < 256) &&
                 !((old_cmap[col_pos * 3 + 0] == cmap[col_pos * 3 + 0]) &&
                   (old_cmap[col_pos * 3 + 1] == cmap[col_pos * 3 + 1]) &&
                   (old_cmap[col_pos * 3 + 2] == cmap[col_pos * 3 + 2])))
            {
              cnt_col++;
              col_pos++;
            }
          if (cnt_col > 0)
            {
              num_packets++;
              if (! fli_write_char (f, cnt_skip, error) ||
                  ! fli_write_char (f, cnt_col, error))
                {
                  g_prefix_error (error, _("Error writing color map. "));
                  return FALSE;
                }

              while (cnt_col > 0)
                {
                  if (! fli_write_char (f, cmap[col_start++], error) ||
                      ! fli_write_char (f, cmap[col_start++], error) ||
                      ! fli_write_char (f, cmap[col_start++], error))
                    {
                      g_prefix_error (error, _("Error writing color map. "));
                      return FALSE;
                    }

                  cnt_col--;
                }
            }
      } while (col_pos < 256);
    }

  if (num_packets > 0)
    {
      chunk.size = ftell (f) - chunkpos;
      chunk.magic = FLI_COLOR_2;

      fseek (f, chunkpos, SEEK_SET);
      if (! fli_write_uint32 (f, chunk.size, error) ||
          ! fli_write_short (f, chunk.magic, error) ||
          ! fli_write_short (f, num_packets, error))
        {
          g_prefix_error (error, _("Error writing color map. "));
          return FALSE;
        }

      if (chunk.size & 1)
        chunk.size++;
      fseek (f, chunkpos + chunk.size, SEEK_SET);
      *more = TRUE;
      return TRUE;
    }
  fseek (f, chunkpos, SEEK_SET);

  return TRUE;
}

/*
 * completely black frame
 */
gboolean
fli_read_black (FILE          *f,
                s_fli_header  *fli_header,
                guchar        *framebuf,
                GError       **error)
{
  memset (framebuf, 0, (gsize) fli_header->width * fli_header->height);

  return TRUE;
}

gboolean
fli_write_black (FILE          *f,
                 s_fli_header  *fli_header,
                 guchar        *framebuf,
                 GError       **error)
{
  s_fli_chunk chunk;

  chunk.size = 6;
  chunk.magic = FLI_BLACK;

  if (! fli_write_uint32 (f, chunk.size, error) ||
      ! fli_write_short (f, chunk.magic, error))
    {
      g_prefix_error (error, _("Error writing black. "));
      return FALSE;
    }

  return TRUE;
}

/*
 * Uncompressed frame
 */
gboolean
fli_read_copy (FILE          *f,
               s_fli_header  *fli_header,
               guchar        *framebuf,
               GError       **error)
{
  if (fread (framebuf, fli_header->width, fli_header->height, f) != fli_header->height)
    {
      g_set_error (error, G_FILE_ERROR, g_file_error_from_errno (errno),
                   _("Error reading from file."));
      return FALSE;
    }

  return TRUE;
}

gboolean
fli_write_copy (FILE          *f,
                s_fli_header  *fli_header,
                guchar        *framebuf,
                GError       **error)
{
  guint32      chunkpos;
  s_fli_chunk  chunk;

  chunkpos = ftell (f);
  fseek (f, chunkpos + 6, SEEK_SET);
  if (fwrite (framebuf, fli_header->width, fli_header->height, f) != fli_header->height)
    {
      g_prefix_error (error, _("Error writing frame. "));
      return FALSE;
    }
  chunk.size = ftell (f) - chunkpos;
  chunk.magic = FLI_COPY;

  if (chunk.size & 1)
    {
      /* Dummy char to make the chunk end on an even boundary. */
      if (! fli_write_char (f, 0, error))
        {
          g_prefix_error (error, _("Error writing frame. "));
          return FALSE;
        }
      chunk.size++;
    }

  fseek (f, chunkpos, SEEK_SET);
  if (! fli_write_uint32 (f, chunk.size, error) ||
      ! fli_write_short (f, chunk.magic, error))
    {
      g_prefix_error (error, _("Error writing frame. "));
      return FALSE;
    }

  fseek (f, chunkpos + chunk.size, SEEK_SET);
  return TRUE;
}

/*
 * This is a RLE algorithm, used for the first image of an animation
 */
gboolean
fli_read_brun (FILE          *f,
               s_fli_header  *fli_header,
               guchar        *framebuf,
               GError       **error)
{
  gushort  yc;
  guchar  *pos;

  for (yc = 0; yc < fli_header->height; yc++)
    {
      guchar pc, pcnt;
      size_t n, xc;

      if (! fli_read_char (f, &pc, error))
        {
          g_prefix_error (error, _("Error reading compressed data. "));
          return FALSE;
        }
      xc = 0;
      pos = framebuf + (fli_header->width * yc);
      n = (size_t) fli_header->width * (fli_header->height - yc);
      for (pcnt = pc; pcnt > 0; pcnt--)
        {
          guchar ps;

          if (! fli_read_char (f, &ps, error))
            {
              g_prefix_error (error, _("Error reading compressed data. "));
              return FALSE;
            }
          if (ps & 0x80)
            {
              gushort len;

              for (len = -(signed char) ps; len > 0 && xc < n; len--)
                {
                  if (! fli_read_char (f, &pos[xc++], error))
                    {
                      g_prefix_error (error, _("Error reading compressed data. "));
                      return FALSE;
                    }
                }
              if (len > 0 && xc >= n)
                {
                  g_set_error (error, G_FILE_ERROR, 0,
                               _("Overflow reading compressed data. Possibly corrupt file."));
                  return FALSE;
                }
            }
          else
            {
              guchar  val;
              size_t  len;

              len = MIN (n - xc, ps);
              if (! fli_read_char (f, &val, error))
                {
                  g_prefix_error (error, _("Error reading compressed data. "));
                  return FALSE;
                }
              memset (&(pos[xc]), val, len);
              xc+=len;
            }
        }
    }
  return TRUE;
}

gboolean
fli_write_brun (FILE          *f,
                s_fli_header  *fli_header,
                guchar        *framebuf,
                GError       **error)
{
  guint32       chunkpos;
  s_fli_chunk   chunk;
  gushort       yc;
  guchar       *linebuf;

  chunkpos = ftell (f);
  fseek (f, chunkpos + 6, SEEK_SET);

  for (yc = 0; yc < fli_header->height; yc++)
    {
      gushort  xc, t1, pc, tc;
      guint32  linepos, lineend, bc;

      linepos = ftell (f); bc = 0;
      fseek (f, 1, SEEK_CUR);
      linebuf = framebuf + (yc * fli_header->width);
      xc = 0; tc = 0; t1 = 0;
      while (xc < fli_header->width)
        {
          pc = 1;
          while ((pc < 120)                      &&
                 ((xc + pc) < fli_header->width) &&
                 (linebuf[xc + pc] == linebuf[xc]))
            {
              pc++;
            }
          if (pc > 2)
            {
              if (tc > 0)
                {
                  bc++;
                  if (! fli_write_char (f, (tc - 1)^0xFF, error) ||
                      fwrite (linebuf + t1, 1, tc, f) != tc)
                    {
                      g_prefix_error (error, _("Error writing frame. "));
                      return FALSE;
                    }
                  tc = 0;
                }
              bc++;
              if (! fli_write_char (f, pc, error) ||
                  ! fli_write_char (f, linebuf[xc], error))
                {
                  g_prefix_error (error, _("Error writing frame. "));
                  return FALSE;
                }
              t1 = xc + pc;
            }
          else
            {
              tc+=pc;
              if (tc > 120)
                {
                  bc++;
                  if (! fli_write_char (f, (tc - 1)^0xFF, error) ||
                      fwrite (linebuf + t1, 1, tc, f) != tc)
                    {
                      g_prefix_error (error, _("Error writing frame. "));
                      return FALSE;
                    }
                  tc = 0;
                  t1 = xc + pc;
                }
            }
          xc+=pc;
        }
      if (tc > 0)
        {
          bc++;
          if (! fli_write_char (f, (tc - 1)^0xFF, error) ||
              fwrite (linebuf + t1, 1, tc, f) != tc)
            {
              g_prefix_error (error, _("Error writing frame. "));
              return FALSE;
            }
          tc = 0;
        }
      lineend = ftell (f);
      fseek (f, linepos, SEEK_SET);
      if (! fli_write_char (f, bc, error))
        {
          g_prefix_error (error, _("Error writing frame. "));
          return FALSE;
        }
      fseek (f, lineend, SEEK_SET);
    }

  chunk.size = ftell (f) - chunkpos;
  chunk.magic = FLI_BRUN;

  if (chunk.size & 1)
    {
      /* Dummy char to make the chunk end on an even boundary. */
      if (! fli_write_char (f, 0, error))
        {
          g_prefix_error (error, _("Error writing frame. "));
          return FALSE;
        }
      chunk.size++;
    }

  fseek (f, chunkpos, SEEK_SET);
  if (! fli_write_uint32 (f, chunk.size, error) ||
      ! fli_write_short (f, chunk.magic, error))
    {
      g_prefix_error (error, _("Error writing frame. "));
      return FALSE;
    }

  fseek (f, chunkpos + chunk.size, SEEK_SET);
  return TRUE;
}

/*
 * This is the delta-compression method from the classic Autodesk
 * Animator.  It's basically the RLE method from above, but it
 * supports skipping unchanged lines at the beginning and end of an
 * image, and unchanged pixels in a line. This chunk is used in FLI
 * files.
 */
gboolean
fli_read_lc (FILE          *f,
             s_fli_header  *fli_header,
             guchar        *old_framebuf,
             guchar        *framebuf,
             GError       **error)
{
  gushort  yc, firstline, numline;
  guchar  *pos;

  memcpy (framebuf, old_framebuf,
          (gint64) fli_header->width * fli_header->height);

  if (! fli_read_short (f, &firstline, error) ||
      ! fli_read_short (f, &numline, error))
    {
      g_prefix_error (error, _("Error reading compressed data. "));
      return FALSE;
    }

  if (numline > fli_header->height || fli_header->height - numline < firstline)
    return TRUE;

  for (yc = 0; yc < numline; yc++)
    {
      guchar  pc, pcnt;
      size_t  n, xc;

      if (! fli_read_char (f, &pc, error))
        {
          g_prefix_error (error, _("Error reading compressed data. "));
          return FALSE;
        }
      xc = 0;
      pos = framebuf + (fli_header->width * (firstline + yc));
      n = (size_t) fli_header->width * (fli_header->height - firstline - yc);
      for (pcnt = pc; pcnt > 0; pcnt--)
        {
          guchar ps, skip;

          if (! fli_read_char (f, &skip, error) ||
              ! fli_read_char (f, &ps, error))
            {
              g_prefix_error (error, _("Error reading compressed data. "));
              return FALSE;
            }

          xc += MIN (n - xc, skip);
          if (ps & 0x80)
            {
              guchar val;
              size_t len;

              ps = -(signed char) ps;
              if (! fli_read_char (f, &val, error))
                {
                  g_prefix_error (error, _("Error reading compressed data. "));
                  return FALSE;
                }
              len = MIN (n - xc, ps);
              memset (&(pos[xc]), val, len);
              xc += len;
            }
          else
            {
              size_t len, len_read;

              len = MIN (n - xc, ps);
              if (len > 0)
                {
                  len_read = fread (&pos[xc], len, 1, f);
                  if (len_read != 1)
                    {
                      g_set_error (error, G_FILE_ERROR, g_file_error_from_errno (errno),
                                   _("Error reading from file."));
                      g_prefix_error (error, _("Error reading compressed data. "));
                      return FALSE;
                    }
                }
              xc += len;
            }
        }
    }
  return TRUE;
}

gboolean
fli_write_lc (FILE          *f,
              s_fli_header  *fli_header,
              guchar        *old_framebuf,
              guchar        *framebuf,
              GError       **error)
{
  guint32       chunkpos;
  s_fli_chunk   chunk;
  gushort       yc, firstline, numline, lastline;
  guchar       *linebuf, *old_linebuf;

  chunkpos = ftell (f);
  fseek (f, chunkpos + 6, SEEK_SET);

  /* first check, how many lines are unchanged at the beginning */
  firstline = 0;
  while ((memcmp (old_framebuf + (firstline * fli_header->width),
                  framebuf + (firstline * fli_header->width),
                  fli_header->width) == 0) &&
         (firstline < fli_header->height))
    firstline++;

  /* then check from the end, how many lines are unchanged */
  if (firstline < fli_header->height)
    {
      lastline = fli_header->height - 1;
      while ((memcmp (old_framebuf + (lastline * fli_header->width),
                      framebuf + (lastline * fli_header->width),
                      fli_header->width) == 0) &&
             (lastline > firstline))
        lastline--;
      numline = (lastline - firstline) + 1;
    }
  else
    {
      numline = 0;
    }
  if (numline == 0)
    firstline = 0;

  if (! fli_write_short (f, firstline, error) ||
      ! fli_write_short (f, numline, error))
    {
      g_prefix_error (error, _("Error writing frame. "));
      return FALSE;
    }

  for (yc = 0; yc < numline; yc++)
    {
      gushort xc, sc, cc, tc;
      guint32 linepos, lineend, bc;

      linepos = ftell (f); bc = 0;
      fseek (f, 1, SEEK_CUR);

      linebuf = framebuf + ((firstline + yc)*fli_header->width);
      old_linebuf = old_framebuf + ((firstline + yc)*fli_header->width);
      xc = 0;
      while (xc < fli_header->width)
        {
          sc = 0;
          while ((xc < fli_header->width)         &&
                 (linebuf[xc] == old_linebuf[xc]) &&
                 (sc < 255))
            {
              xc++;
              sc++;
            }
          if (! fli_write_char (f, sc, error))
            {
              g_prefix_error (error, _("Error writing frame. "));
              return FALSE;
            }
          cc = 1;
          while ((linebuf[xc] == linebuf[xc + cc]) &&
                 ((xc + cc)<fli_header->width)     &&
                 (cc < 120))
            {
              cc++;
            }
          if (cc > 2)
            {
              bc++;
              if (! fli_write_char (f, (cc - 1)^0xFF, error) ||
                  ! fli_write_char (f, linebuf[xc], error))
                {
                  g_prefix_error (error, _("Error writing frame. "));
                  return FALSE;
                }
              xc += cc;
            }
          else
            {
              tc = 0;
              do {
                  sc = 0;
                  while ((linebuf[tc + xc + sc] == old_linebuf[tc + xc + sc]) &&
                         ((tc + xc + sc)<fli_header->width)                   &&
                         (sc < 5))
                    {
                      sc++;
                    }
                  cc = 1;
                  while ((linebuf[tc + xc] == linebuf[tc + xc + cc]) &&
                         ((tc + xc + cc)<fli_header->width)          &&
                         (cc < 10))
                    {
                      cc++;
                    }
                  tc++;
              } while ((tc < 120) &&
                       (cc < 9)   &&
                       (sc < 4)   &&
                       ((xc + tc) < fli_header->width));
              bc++;
              if (! fli_write_char (f, tc, error) ||
                  fwrite (linebuf + xc, tc, 1, f) != 1)
                {
                  g_prefix_error (error, _("Error writing frame. "));
                  return FALSE;
                }
              xc += tc;
            }
        }
      lineend = ftell (f);
      fseek (f, linepos, SEEK_SET);
      if (! fli_write_char (f, bc, error))
        {
          g_prefix_error (error, _("Error writing frame. "));
          return FALSE;
        }
      fseek (f, lineend, SEEK_SET);
    }

  chunk.size = ftell (f) - chunkpos;
  chunk.magic = FLI_LC;

  if (chunk.size & 1)
    {
      /* Dummy char to make the chunk end on an even boundary. */
      if (! fli_write_char (f, 0, error))
        {
          g_prefix_error (error, _("Error writing frame. "));
          return FALSE;
        }
      chunk.size++;
    }

  fseek (f, chunkpos, SEEK_SET);
  if (! fli_write_uint32 (f, chunk.size, error) ||
      ! fli_write_short (f, chunk.magic, error))
    {
      g_prefix_error (error, _("Error writing frame. "));
      return FALSE;
    }

  fseek (f, chunkpos + chunk.size, SEEK_SET);
  return TRUE;
}


/*
 * This is an enhanced version of the old delta-compression used by
 * the autodesk animator pro. It's word-oriented, and supports
 * skipping larger parts of the image. This chunk is used in FLC
 * files.
 */
gboolean
fli_read_lc_2 (FILE          *f,
               s_fli_header  *fli_header,
               guchar        *old_framebuf,
               guchar        *framebuf,
               GError       **error)
{
  gushort  yc, lc, numline;
  guchar  *pos;
  guint32  len_read;

  memcpy (framebuf, old_framebuf,
          (gint64) fli_header->width * fli_header->height);
  yc = 0;

  if (! fli_read_short (f, &numline, error))
    {
      g_prefix_error (error, _("Error reading compressed data. "));
      return FALSE;
    }
  if (numline > fli_header->height)
    {
      g_warning ("Number of lines %u larger than frame height %u.", numline, fli_header->height);
      numline = fli_header->height;
    }

  for (lc = 0; lc < numline; lc++)
    {
      gushort pc, pcnt, lpf, lpn;
      size_t  n, xc;

      if (! fli_read_short (f, &pc, error))
        {
          g_prefix_error (error, _("Error reading compressed data. "));
          return FALSE;
        }

      lpf = 0; lpn = 0;
      while (pc & 0x8000)
        {
          if (pc & 0x4000)
            {
              yc += -(signed short) pc;
            }
          else
            {
              lpf = 1;
              lpn = pc & 0xFF;
            }

          if (! fli_read_short (f, &pc, error))
            {
              g_prefix_error (error, _("Error reading compressed data. "));
              return FALSE;
            }
        }
      yc = MIN (yc, fli_header->height);
      xc = 0;
      pos = framebuf + (fli_header->width * yc);
      n = (size_t) fli_header->width * (fli_header->height - yc);
      for (pcnt = pc; pcnt > 0; pcnt--)
        {
          guchar ps, skip;

          if (! fli_read_char (f, &skip, error) ||
              ! fli_read_char (f, &ps, error))
            {
              g_prefix_error (error, _("Error reading compressed data. "));
              return FALSE;
            }

          xc += MIN (n - xc, skip);
          if (ps & 0x80)
            {
              guchar v1, v2;

              ps = -(signed char) ps;
              if (! fli_read_char (f, &v1, error) ||
                  ! fli_read_char (f, &v2, error))
                {
                  g_prefix_error (error, _("Error reading compressed data. "));
                  return FALSE;
                }
              while (ps > 0 && xc + 1 < n)
                {
                  pos[xc++] = v1;
                  pos[xc++] = v2;
                  ps--;
                }
            }
          else
            {
              size_t len;

              len = MIN ((n - xc)/2, ps);
              if (len > 0)
                {
                  len_read = fread (&pos[xc], len, 2, f);
                  if (len_read != 2)
                    {
                      g_set_error (error, G_FILE_ERROR, g_file_error_from_errno (errno),
                                   _("Error reading from file."));
                      g_prefix_error (error, _("Error reading compressed data. "));
                      return FALSE;
                    }
                }
              xc += len << 1;
            }
        }
      if (lpf && xc < n)
        pos[xc] = lpn;
      yc++;
    }
  return TRUE;
}

/* --- end plug-ins/field-io/file-fli/fli.c --- */

/* --- begin plug-ins/field-io/file-icns/file-icns-data.c --- */
/* AmmoOS Image - The AmmoOS Field Image Research
 * Copyright (C) 1995-1999 Spencer Kimball and Peter Mattis
 *
 * file-icns-data.c
 * Copyright (C) 2004 Brion Vibber <brion@pobox.com>
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

#include <glib.h>
#include "file-icns-data.h"

/* Ported from Brion Vibber's icnsdata.c code, under the GPL license, version 3
 * or any later version of the license */
IconType iconTypes[] =
{
  /* 1-bit, no mask? */
  {"SICN",  16,  16,  1, 0, FALSE},
  {"ICON",  32,  32,  1, 0, FALSE},

  /* 1-bit image and hitmask */
  {"icm#",  12,  12,  1, "icm#", FALSE},
  {"ics#",  16,  16,  1, "ics#", FALSE},
  {"ICN#",  32,  32,  1, "ICN#", FALSE},
  {"ich#",  48,  48,  1, "ich#", FALSE},

  /* 4-bit. Use mask from binary. */
  {"icm4",  12,  12,  4, "icm#", FALSE},
  {"ics4",  16,  16,  4, "ics#", FALSE},
  {"icl4",  32,  32,  4, "ICN#", FALSE},
  {"ich4",  48,  48,  4, "ich#", FALSE},

  /* 8-bit. Use mask from binary. */
  {"icm8",  12,  12,  8, "icm#", FALSE},
  {"ics8",  16,  16,  8, "ics#", FALSE},
  {"icl8",  32,  32,  8, "ICN#", FALSE},
  {"ich8",  48,  48,  8, "ich#", FALSE},

  /* 32-bit color icons; separate 8-bit alpha */
  {"is32",  16,  16, 32, "s8mk", FALSE},
  {"il32",  32,  32, 32, "l8mk", FALSE},
  {"ih32",  48,  48, 32, "h8mk", FALSE},
  {"it32", 128, 128, 32, "t8mk", FALSE},

  /* Post-MacOS 10.0 ICNS formats */
  /* PNG, JPEG 2000, or 24-bit RGB */
  {"icp4",   16,   16, 32, "N/A", TRUE},
  {"icp5",   32,   32, 32, "N/A", TRUE},

  /* PNG or JPEG 2000 */
  {"icp6",   48,   48, 0, "N/A", TRUE},
  {"ic07",  128,  128, 0, "N/A", TRUE},
  {"ic08",  256,  256, 0, "N/A", TRUE},
  {"ic09",  512,  512, 0, "N/A", TRUE},
  {"sb24",   24,   24, 0, "N/A", TRUE},

  /* PNG or JPEG 2000 (Retina) */
  {"ic10", 1024, 1024, 0, "N/A", TRUE},
  {"ic11",   32,   32, 0, "N/A", TRUE},
  {"ic12",   64,   64, 0, "N/A", TRUE},
  {"ic13",  256,  256, 0, "N/A", TRUE},
  {"ic14",  512,  512, 0, "N/A", TRUE},
  {"icsB",   36,   36, 0, "N/A", TRUE},
  {"SB24",   48,   48, 0, "N/A", TRUE},

  /* ARGB, PNG, or JPEG 2000 */
  {"ic04",   16,   16, 0, "N/A", TRUE},
  {"ic05",   32,   32, 0, "N/A", TRUE},
  {"icsb",   18,   18, 0, "N/A", TRUE},

  {0, 0, 0, 0, 0}
};

IconType maskTypes[] =
{
  /* 8-bit masks */
  {"s8mk",  16,  16,  8, 0},
  {"l8mk",  32,  32,  8, 0},
  {"h8mk",  48,  48,  8, 0},
  {"t8mk", 128, 128,  8, 0},

  {0, 0, 0, 0, 0}
};

guchar icns_colormap_4[] =
{
    0xFF, 0xFF, 0xFF,
    0xFC, 0xF3, 0x05,
    0xFF, 0x64, 0x02,
    0xDD, 0x08, 0x06,
    0xF2, 0x08, 0x84,
    0x46, 0x00, 0xA5,
    0x00, 0x00, 0xD4,
    0x02, 0xAB, 0xEA,
    0x1F, 0xB7, 0x14,
    0x00, 0x64, 0x11,
    0x56, 0x2C, 0x05,
    0x90, 0x71, 0x3A,
    0xC0, 0xC0, 0xC0,
    0x80, 0x80, 0x80,
    0x40, 0x40, 0x40,
    0x00, 0x00, 0x00
};

guchar icns_colormap_8[] =
{
    0xFF, 0xFF, 0xFF,
    0xFF, 0xFF, 0xCC,
    0xFF, 0xFF, 0x99,
    0xFF, 0xFF, 0x66,
    0xFF, 0xFF, 0x33,
    0xFF, 0xFF, 0x00,
    0xFF, 0xCC, 0xFF,
    0xFF, 0xCC, 0xCC,
    0xFF, 0xCC, 0x99,
    0xFF, 0xCC, 0x66,
    0xFF, 0xCC, 0x33,
    0xFF, 0xCC, 0x00,
    0xFF, 0x99, 0xFF,
    0xFF, 0x99, 0xCC,
    0xFF, 0x99, 0x99,
    0xFF, 0x99, 0x66,
    0xFF, 0x99, 0x33,
    0xFF, 0x99, 0x00,
    0xFF, 0x66, 0xFF,
    0xFF, 0x66, 0xCC,
    0xFF, 0x66, 0x99,
    0xFF, 0x66, 0x66,
    0xFF, 0x66, 0x33,
    0xFF, 0x66, 0x00,
    0xFF, 0x33, 0xFF,
    0xFF, 0x33, 0xCC,
    0xFF, 0x33, 0x99,
    0xFF, 0x33, 0x66,
    0xFF, 0x33, 0x33,
    0xFF, 0x33, 0x00,
    0xFF, 0x00, 0xFF,
    0xFF, 0x00, 0xCC,
    0xFF, 0x00, 0x99,
    0xFF, 0x00, 0x66,
    0xFF, 0x00, 0x33,
    0xFF, 0x00, 0x00,
    0xCC, 0xFF, 0xFF,
    0xCC, 0xFF, 0xCC,
    0xCC, 0xFF, 0x99,
    0xCC, 0xFF, 0x66,
    0xCC, 0xFF, 0x33,
    0xCC, 0xFF, 0x00,
    0xCC, 0xCC, 0xFF,
    0xCC, 0xCC, 0xCC,
    0xCC, 0xCC, 0x99,
    0xCC, 0xCC, 0x66,
    0xCC, 0xCC, 0x33,
    0xCC, 0xCC, 0x00,
    0xCC, 0x99, 0xFF,
    0xCC, 0x99, 0xCC,
    0xCC, 0x99, 0x99,
    0xCC, 0x99, 0x66,
    0xCC, 0x99, 0x33,
    0xCC, 0x99, 0x00,
    0xCC, 0x66, 0xFF,
    0xCC, 0x66, 0xCC,
    0xCC, 0x66, 0x99,
    0xCC, 0x66, 0x66,
    0xCC, 0x66, 0x33,
    0xCC, 0x66, 0x00,
    0xCC, 0x33, 0xFF,
    0xCC, 0x33, 0xCC,
    0xCC, 0x33, 0x99,
    0xCC, 0x33, 0x66,
    0xCC, 0x33, 0x33,
    0xCC, 0x33, 0x00,
    0xCC, 0x00, 0xFF,
    0xCC, 0x00, 0xCC,
    0xCC, 0x00, 0x99,
    0xCC, 0x00, 0x66,
    0xCC, 0x00, 0x33,
    0xCC, 0x00, 0x00,
    0x99, 0xFF, 0xFF,
    0x99, 0xFF, 0xCC,
    0x99, 0xFF, 0x99,
    0x99, 0xFF, 0x66,
    0x99, 0xFF, 0x33,
    0x99, 0xFF, 0x00,
    0x99, 0xCC, 0xFF,
    0x99, 0xCC, 0xCC,
    0x99, 0xCC, 0x99,
    0x99, 0xCC, 0x66,
    0x99, 0xCC, 0x33,
    0x99, 0xCC, 0x00,
    0x99, 0x99, 0xFF,
    0x99, 0x99, 0xCC,
    0x99, 0x99, 0x99,
    0x99, 0x99, 0x66,
    0x99, 0x99, 0x33,
    0x99, 0x99, 0x00,
    0x99, 0x66, 0xFF,
    0x99, 0x66, 0xCC,
    0x99, 0x66, 0x99,
    0x99, 0x66, 0x66,
    0x99, 0x66, 0x33,
    0x99, 0x66, 0x00,
    0x99, 0x33, 0xFF,
    0x99, 0x33, 0xCC,
    0x99, 0x33, 0x99,
    0x99, 0x33, 0x66,
    0x99, 0x33, 0x33,
    0x99, 0x33, 0x00,
    0x99, 0x00, 0xFF,
    0x99, 0x00, 0xCC,
    0x99, 0x00, 0x99,
    0x99, 0x00, 0x66,
    0x99, 0x00, 0x33,
    0x99, 0x00, 0x00,
    0x66, 0xFF, 0xFF,
    0x66, 0xFF, 0xCC,
    0x66, 0xFF, 0x99,
    0x66, 0xFF, 0x66,
    0x66, 0xFF, 0x33,
    0x66, 0xFF, 0x00,
    0x66, 0xCC, 0xFF,
    0x66, 0xCC, 0xCC,
    0x66, 0xCC, 0x99,
    0x66, 0xCC, 0x66,
    0x66, 0xCC, 0x33,
    0x66, 0xCC, 0x00,
    0x66, 0x99, 0xFF,
    0x66, 0x99, 0xCC,
    0x66, 0x99, 0x99,
    0x66, 0x99, 0x66,
    0x66, 0x99, 0x33,
    0x66, 0x99, 0x00,
    0x66, 0x66, 0xFF,
    0x66, 0x66, 0xCC,
    0x66, 0x66, 0x99,
    0x66, 0x66, 0x66,
    0x66, 0x66, 0x33,
    0x66, 0x66, 0x00,
    0x66, 0x33, 0xFF,
    0x66, 0x33, 0xCC,
    0x66, 0x33, 0x99,
    0x66, 0x33, 0x66,
    0x66, 0x33, 0x33,
    0x66, 0x33, 0x00,
    0x66, 0x00, 0xFF,
    0x66, 0x00, 0xCC,
    0x66, 0x00, 0x99,
    0x66, 0x00, 0x66,
    0x66, 0x00, 0x33,
    0x66, 0x00, 0x00,
    0x33, 0xFF, 0xFF,
    0x33, 0xFF, 0xCC,
    0x33, 0xFF, 0x99,
    0x33, 0xFF, 0x66,
    0x33, 0xFF, 0x33,
    0x33, 0xFF, 0x00,
    0x33, 0xCC, 0xFF,
    0x33, 0xCC, 0xCC,
    0x33, 0xCC, 0x99,
    0x33, 0xCC, 0x66,
    0x33, 0xCC, 0x33,
    0x33, 0xCC, 0x00,
    0x33, 0x99, 0xFF,
    0x33, 0x99, 0xCC,
    0x33, 0x99, 0x99,
    0x33, 0x99, 0x66,
    0x33, 0x99, 0x33,
    0x33, 0x99, 0x00,
    0x33, 0x66, 0xFF,
    0x33, 0x66, 0xCC,
    0x33, 0x66, 0x99,
    0x33, 0x66, 0x66,
    0x33, 0x66, 0x33,
    0x33, 0x66, 0x00,
    0x33, 0x33, 0xFF,
    0x33, 0x33, 0xCC,
    0x33, 0x33, 0x99,
    0x33, 0x33, 0x66,
    0x33, 0x33, 0x33,
    0x33, 0x33, 0x00,
    0x33, 0x00, 0xFF,
    0x33, 0x00, 0xCC,
    0x33, 0x00, 0x99,
    0x33, 0x00, 0x66,
    0x33, 0x00, 0x33,
    0x33, 0x00, 0x00,
    0x00, 0xFF, 0xFF,
    0x00, 0xFF, 0xCC,
    0x00, 0xFF, 0x99,
    0x00, 0xFF, 0x66,
    0x00, 0xFF, 0x33,
    0x00, 0xFF, 0x00,
    0x00, 0xCC, 0xFF,
    0x00, 0xCC, 0xCC,
    0x00, 0xCC, 0x99,
    0x00, 0xCC, 0x66,
    0x00, 0xCC, 0x33,
    0x00, 0xCC, 0x00,
    0x00, 0x99, 0xFF,
    0x00, 0x99, 0xCC,
    0x00, 0x99, 0x99,
    0x00, 0x99, 0x66,
    0x00, 0x99, 0x33,
    0x00, 0x99, 0x00,
    0x00, 0x66, 0xFF,
    0x00, 0x66, 0xCC,
    0x00, 0x66, 0x99,
    0x00, 0x66, 0x66,
    0x00, 0x66, 0x33,
    0x00, 0x66, 0x00,
    0x00, 0x33, 0xFF,
    0x00, 0x33, 0xCC,
    0x00, 0x33, 0x99,
    0x00, 0x33, 0x66,
    0x00, 0x33, 0x33,
    0x00, 0x33, 0x00,
    0x00, 0x00, 0xFF,
    0x00, 0x00, 0xCC,
    0x00, 0x00, 0x99,
    0x00, 0x00, 0x66,
    0x00, 0x00, 0x33,
    0xEE, 0x00, 0x00,
    0xDD, 0x00, 0x00,
    0xBB, 0x00, 0x00,
    0xAA, 0x00, 0x00,
    0x88, 0x00, 0x00,
    0x77, 0x00, 0x00,
    0x55, 0x00, 0x00,
    0x44, 0x00, 0x00,
    0x22, 0x00, 0x00,
    0x11, 0x00, 0x00,
    0x00, 0xEE, 0x00,
    0x00, 0xDD, 0x00,
    0x00, 0xBB, 0x00,
    0x00, 0xAA, 0x00,
    0x00, 0x88, 0x00,
    0x00, 0x77, 0x00,
    0x00, 0x55, 0x00,
    0x00, 0x44, 0x00,
    0x00, 0x22, 0x00,
    0x00, 0x11, 0x00,
    0x00, 0x00, 0xEE,
    0x00, 0x00, 0xDD,
    0x00, 0x00, 0xBB,
    0x00, 0x00, 0xAA,
    0x00, 0x00, 0x88,
    0x00, 0x00, 0x77,
    0x00, 0x00, 0x55,
    0x00, 0x00, 0x44,
    0x00, 0x00, 0x22,
    0x00, 0x00, 0x11,
    0xEE, 0xEE, 0xEE,
    0xDD, 0xDD, 0xDD,
    0xBB, 0xBB, 0xBB,
    0xAA, 0xAA, 0xAA,
    0x88, 0x88, 0x88,
    0x77, 0x77, 0x77,
    0x55, 0x55, 0x55,
    0x44, 0x44, 0x44,
    0x22, 0x22, 0x22,
    0x11, 0x11, 0x11,
    0x00, 0x00, 0x00
};

/* --- end plug-ins/field-io/file-icns/file-icns-data.c --- */

/* --- begin plug-ins/field-io/file-icns/file-icns-export.c --- */
/* AmmoOS Image - The AmmoOS Field Image Research
 * Copyright (C) 1995-1999 Spencer Kimball and Peter Mattis
 *
 * file-icns-export.c
 * Copyright (C) 2004 Brion Vibber <brion@pobox.com>
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

#include "config.h"

#include <errno.h>
#include <string.h>

#include <glib/gstdio.h>

#include <libgimp/ammoos.h>
#include <libgimp/gimpui.h>

#include "file-icns.h"
#include "file-icns-data.h"
#include "file-icns-load.h"
#include "file-icns-export.h"

#include "libgimp/stdplugins-intl.h"

GtkWidget *        icns_dialog_new       (IcnsSaveInfo         *info,
                                          GimpImage            *image,
                                          GimpProcedure        *procedure,
                                          GimpProcedureConfig  *config);

static gboolean    icns_save_dialog      (IcnsSaveInfo         *info,
                                          GimpImage            *image,
                                          GimpProcedure        *procedure,
                                          GimpProcedureConfig  *config);

void               icns_dialog_add_icon  (GtkWidget            *dialog,
                                          GimpDrawable         *layer,
                                          gint                  layer_num,
                                          gint                  duplicates[]);

static GtkWidget * icns_preview_new      (GimpDrawable         *layer);

static GtkWidget * icns_create_icon_item (GtkWidget            *icon_preview,
                                          GimpDrawable         *layer,
                                          gint                  layer_num,
                                          IcnsSaveInfo         *info,
                                          gint                  duplicates[]);

static gint        icns_find_type        (gint                  width,
                                          gint                  height);
static gboolean    icns_check_dimensions (gint                  width,
                                          gint                  height);
static gboolean    icns_check_compat     (GtkWidget            *dialog,
                                          IcnsSaveInfo         *info);

GimpPDBStatusType  icns_export_image     (GFile                *file,
                                          IcnsSaveInfo         *info,
                                          GimpImage            *image,
                                          gboolean              include_color_profile,
                                          GError              **error);

static guchar    * icns_compress         (guint                 width,
                                          guint                 height,
                                          guchar               *rgba,
                                          gint                 *out_size);

static void        icns_save_info_free   (IcnsSaveInfo *info);

/* Referenced from plug-ins/file-ico/ico-dialog.c */
void
icns_dialog_add_icon (GtkWidget    *dialog,
                      GimpDrawable *layer,
                      gint          layer_num,
                      gint          duplicates[])
{
  GtkWidget    *flowbox;
  GtkWidget    *vbox_item;
  GtkWidget    *preview;
  gchar         key[ICNS_MAXBUF];
  IcnsSaveInfo *info;

  flowbox = g_object_get_data (G_OBJECT (dialog), "icons_flowbox");
  info    = g_object_get_data (G_OBJECT (dialog), "save_info");

  preview   = icns_preview_new (layer);
  vbox_item = icns_create_icon_item (preview, layer, layer_num, info,
                                     duplicates);
  gtk_flow_box_insert (GTK_FLOW_BOX (flowbox), vbox_item, -1);
  gtk_widget_set_visible (vbox_item, TRUE);

  /* Let's make the vbox_item accessible through the layer ID */
  g_snprintf (key, sizeof (key), "layer_%i_hbox",
              gimp_item_get_id (GIMP_ITEM (layer)));
  g_object_set_data (G_OBJECT (dialog), key, vbox_item);

  icns_check_compat (dialog, info);
}

static GtkWidget *
icns_preview_new (GimpDrawable *layer)
{
  GtkWidget *image;
  GdkPixbuf *pixbuf;
  gint       width  = gimp_drawable_get_width (layer);
  gint       height = gimp_drawable_get_height (layer);

  pixbuf = gimp_drawable_get_thumbnail (layer,
                                        MIN (width, 128), MIN (height, 128),
                                        GIMP_PIXBUF_SMALL_CHECKS);
  image = gtk_image_new_from_pixbuf (pixbuf);

  g_object_unref (pixbuf);

  return image;
}

static gint
icns_find_type (gint width,
                gint height)
{
  gint match = -1;

  for (gint j = 0; iconTypes[j].type; j++)
    {
      /* TODO: Currently, this chooses the first "modern" ICNS format for a
       * ICNS file. This is because newer formats are not supported well in
       * non-native MacOS programs like Inkscape. It'd be nice to design
       * a GUI with enough information for users to make their own decisions
       */
      if (iconTypes[j].width == width   &&
          iconTypes[j].height == height &&
          iconTypes[j].isModern)
        {
          match = j;
          break;
        }
    }

  return match;
}

static gboolean
icns_check_dimensions (gint width,
                       gint height)
{
  gboolean isValid = TRUE;

  if (width != height)
    {
      /* Only valid non-square size is 16x12 */
      if (! (width == 16 && height == 12))
        isValid = FALSE;
    }
  else
    {
      /* Valid square ICNS sizes */
      if (width != 16   &&
          width != 18   &&
          width != 24   &&
          width != 32   &&
          width != 36   &&
          width != 48   &&
          width != 64   &&
          width != 128  &&
          width != 256  &&
          width != 512  &&
          width != 1024)
        isValid = FALSE;
    }

  return isValid;
}

static GtkWidget *
icns_create_icon_item (GtkWidget    *icon_preview,
                       GimpDrawable *layer,
                       gint          layer_num,
                       IcnsSaveInfo *info,
                       gint          duplicates[])
{
  static GtkSizeGroup *size = NULL;

  GtkWidget *vbox_item;
  GtkWidget *frame;
  gchar     *frame_header;
  gint       match  = -1;
  gint       width  = gimp_drawable_get_width (layer);
  gint       height = gimp_drawable_get_height (layer);

  vbox_item = gtk_box_new (GTK_ORIENTATION_VERTICAL, 6);

  /* To make life easier for the callbacks, we store the
     layer's ID and stacking number with vbox_item. */

  g_object_set_data (G_OBJECT (vbox_item),
                     "icon_layer", layer);
  g_object_set_data (G_OBJECT (vbox_item),
                     "icon_layer_num", GINT_TO_POINTER (layer_num));

  frame_header = g_strdup_printf ("%dx%d", width, height);

  frame = gimp_frame_new (frame_header);
  gtk_box_pack_start (GTK_BOX (vbox_item), frame, FALSE, FALSE, 0);
  gtk_widget_set_visible (frame, TRUE);
  g_free (frame_header);

  g_object_set_data (G_OBJECT (vbox_item), "icon_preview", icon_preview);
  gtk_container_add (GTK_CONTAINER (frame), icon_preview);
  gtk_widget_set_visible (icon_preview, TRUE);

  if (! size)
    size = gtk_size_group_new (GTK_SIZE_GROUP_VERTICAL);

  gtk_size_group_add_widget (size, icon_preview);

  match = icns_find_type (gimp_drawable_get_width (layer),
                          gimp_drawable_get_height (layer));

  if (! icns_check_dimensions (width, height) ||
      (match != -1 && duplicates[match] != 0))
    {
      GtkWidget *label;
      gchar     *warning;
      gchar     *markup;

      if (! icns_check_dimensions (width, height))
        warning = g_strdup_printf (_("Invalid icon size. \n"
                                     "It will not be exported"));
      else
        warning = g_strdup_printf (_("Duplicate layer size. \n"
                                     "It will not be exported"));

      markup = g_strdup_printf ("<i>%s</i>", warning);

      label = gtk_label_new (NULL);
      gtk_label_set_markup (GTK_LABEL (label), markup);
      g_free (markup);
      g_free (warning);

      gtk_box_pack_start (GTK_BOX (vbox_item), label, FALSE, FALSE, 0);
      gtk_widget_set_visible (label, TRUE);
      gtk_style_context_add_class (gtk_widget_get_style_context (vbox_item),
                                   "background");
    }

  if (match != -1)
    duplicates[match] = 1;

  return vbox_item;
}

static gboolean
icns_check_compat (GtkWidget    *dialog,
                   IcnsSaveInfo *info)
{
  GtkWidget *warning;
  GList     *iter;
  gboolean   warn = FALSE;

  for (iter = info->layers; iter; iter = iter->next)
    {
      gint width  = gimp_drawable_get_width (iter->data);
      gint height = gimp_drawable_get_height (iter->data);

      warn = ! icns_check_dimensions (width, height);
      if (warn)
        break;
    }

  if (dialog)
    {
      warning = g_object_get_data (G_OBJECT (dialog), "warning");
      gtk_widget_set_visible (warning, warn);
    }

  return ! warn;
}

GtkWidget *
icns_dialog_new (IcnsSaveInfo        *info,
                 GimpImage           *image,
                 GimpProcedure       *procedure,
                 GimpProcedureConfig *config)
{
  GtkWidget     *dialog;
  GtkWidget     *main_vbox;
  GtkWidget     *frame;
  GtkWidget     *scrolled_window;
  GtkWidget     *viewport;
  GtkWidget     *flowbox;
  GtkWidget     *warning;

  dialog = gimp_export_procedure_dialog_new (GIMP_EXPORT_PROCEDURE (procedure),
                                             config, image);

  g_object_set_data (G_OBJECT (dialog), "save_info", info);

  main_vbox = gtk_box_new (GTK_ORIENTATION_VERTICAL, 6);
  gtk_container_set_border_width (GTK_CONTAINER (main_vbox), 6);
  gtk_box_pack_start (GTK_BOX (gtk_dialog_get_content_area (GTK_DIALOG (dialog))),
                      main_vbox, TRUE, TRUE, 0);
  gtk_widget_set_visible (main_vbox, TRUE);

  warning = g_object_new (GIMP_TYPE_HINT_BOX,
                          "icon-name", GIMP_ICON_DIALOG_WARNING,
                          "hint",
                          _("Valid ICNS icons sizes are:\n "
                            "16x12, 16x16, 18x18, 24x24, 32x32, 36x36, 48x48,\n"
                            "64x64, 128x128, 256x256, 512x512, and 1024x1024.\n"
                            "Any other sized layers will be ignored on export."),
                          NULL);
  gtk_box_pack_end (GTK_BOX (main_vbox), warning, FALSE, FALSE, 12);
  /* Don't show warning by default */

  frame = gimp_frame_new (_("Export Icons"));
  gtk_box_pack_start (GTK_BOX (main_vbox), frame, TRUE, TRUE, 4);
  gtk_widget_set_visible (frame, TRUE);

  scrolled_window = gtk_scrolled_window_new (NULL, NULL);
  gtk_scrolled_window_set_policy (GTK_SCROLLED_WINDOW (scrolled_window),
                                  GTK_POLICY_NEVER, GTK_POLICY_AUTOMATIC);
  gtk_container_add (GTK_CONTAINER (frame), scrolled_window);
  gtk_widget_set_size_request (scrolled_window, -1, 256);
  gtk_widget_set_visible (scrolled_window, TRUE);

  viewport = gtk_viewport_new (NULL, NULL);
  gtk_container_add (GTK_CONTAINER (scrolled_window), viewport);
  gtk_widget_set_visible (viewport, TRUE);

  flowbox = gtk_flow_box_new ();
  gtk_flow_box_set_column_spacing (GTK_FLOW_BOX (flowbox), 6);
  gtk_flow_box_set_row_spacing (GTK_FLOW_BOX (flowbox), 6);
  gtk_flow_box_set_selection_mode (GTK_FLOW_BOX (flowbox), GTK_SELECTION_NONE);
  g_object_set_data (G_OBJECT (dialog), "icons_flowbox", flowbox);
  gtk_container_add (GTK_CONTAINER (viewport), flowbox);
  gtk_widget_set_visible (flowbox, TRUE);

  g_object_set_data (G_OBJECT (dialog), "warning", warning);

  return dialog;
}

static gboolean
icns_save_dialog (IcnsSaveInfo        *info,
                  GimpImage           *image,
                  GimpProcedure       *procedure,
                  GimpProcedureConfig *config)
{
  GtkWidget *dialog;
  GList     *iter;
  gint       i;
  gboolean   response;
  gint       duplicates[ICNS_TYPE_NUM];
  gint       ordered[12] =
    {12, 16, 18, 24, 32, 36, 48, 64, 128, 256, 512, 1024};

  gimp_ui_init (PLUG_IN_BINARY);

  for (i = 0; i < ICNS_TYPE_NUM; i++)
    duplicates[i] = 0;

  dialog = icns_dialog_new (info, image, procedure, config);

  /* Add icons in order, smallest to largest */
  for (i = 0; i < 12; i++)
    {
      for (iter = info->layers;
           iter;
           iter = g_list_next (iter))
        {
          /* Put the icons in order in dialog */
          gint width  = gimp_drawable_get_width (iter->data);
          gint height = gimp_drawable_get_height (iter->data);

          if (height != ordered[i] || ! icns_check_dimensions (width, height))
            continue;

          icns_dialog_add_icon (dialog, iter->data, i, duplicates);
        }
    }

  /* Add any invalid icons at the end */
  for (iter = info->layers, i = 0;
       iter;
       iter = g_list_next (iter), i++)
    {
      if (! icns_check_dimensions (gimp_drawable_get_width (iter->data),
                                   gimp_drawable_get_height (iter->data)))
        icns_dialog_add_icon (dialog, iter->data, i, duplicates);
    }

  /* Scale the thing to approximately fit its content, but not too large ... */
  gtk_window_set_default_size (GTK_WINDOW (dialog),
                               200 + (info->num_icons > 4 ?
                                      500 : info->num_icons * 120),
                               200 + (info->num_icons > 4 ?
                                      250 : info->num_icons * 60));

  gtk_widget_set_visible (dialog, TRUE);

  response = gimp_procedure_dialog_run (GIMP_PROCEDURE_DIALOG (dialog));

  gtk_widget_destroy (dialog);

  return response;
}

GimpPDBStatusType
icns_export_image (GFile        *file,
                   IcnsSaveInfo *info,
                   GimpImage    *image,
                   gboolean      include_color_profile,
                   GError      **error)
{
  FILE           *fp;
  GList          *iter;
  gint            i;
  guint32         file_size   = 8;
  gint            duplicates[ICNS_TYPE_NUM];

  for (i = 0; i < ICNS_TYPE_NUM; i++)
    duplicates[i] = 0;

  fp = g_fopen (g_file_peek_path (file), "wb");

  if (! fp)
    {
      icns_save_info_free (info);
      g_set_error (error, G_FILE_ERROR, g_file_error_from_errno (errno),
                   _("Could not open '%s' for writing: %s"),
                   gimp_file_get_utf8_name (file), g_strerror (errno));
      return GIMP_PDB_EXECUTION_ERROR;
    }

  /* Write Header */
  fwrite ("icns", sizeof (gchar), 4, fp);
  fwrite ("\0\0\0\0", sizeof (gchar), 4, fp);  /* will be filled in later */

  /* Write Icon Data */
  for (iter = info->layers, i = 0;
       iter;
       iter = g_list_next (iter), i++)
    {
      gint match  = -1;
      gint width  = gimp_drawable_get_width (iter->data);
      gint height = gimp_drawable_get_height (iter->data);

      /* Don't export icons with invalid dimensions */
      if (! icns_check_dimensions (width, height))
        continue;

      match = icns_find_type (width, height);

      /* MacOS X format icons */
      if (match != -1 && duplicates[match] == 0)
        {
          gint temp_size;
          gint macos_size;

          /* icp4 - 6 types (16x16, 32x32 and 48x48 icons) do not render well
           * in applications if saved as PNGs. Therefore, we will save those
           * in the older format for compatibility. */
          if (! g_strcmp0 (iconTypes[match].type, "icp4") ||
              ! g_strcmp0 (iconTypes[match].type, "icp5") ||
              ! g_strcmp0 (iconTypes[match].type, "icp6"))
            {
              GeglBuffer *buffer;
              guchar     *pixels;
              guchar     *alpha     = NULL;
              guchar     *output    = NULL;
              gint        compat_id = -1;

              macos_size = 0;

              for (compat_id = 0; iconTypes[compat_id].type; compat_id++)
                {
                  if (iconTypes[compat_id].width == width   &&
                      iconTypes[compat_id].height == height &&
                      iconTypes[compat_id].bits == 32)
                    break;
                }

              fwrite (iconTypes[compat_id].type, sizeof (gchar), 4, fp);
              temp_size = width * height * 4;

              buffer = gimp_drawable_get_buffer (iter->data);
              pixels = g_malloc (temp_size);
              alpha  = g_malloc (width * height);

              gegl_buffer_get (buffer, GEGL_RECTANGLE (0, 0, width, height),
                               1.0, babl_format ("R'G'B'A u8"), pixels,
                               GEGL_AUTO_ROWSTRIDE, GEGL_ABYSS_NONE);
              gegl_buffer_get (buffer, GEGL_RECTANGLE (0, 0, width, height),
                               1.0, babl_format ("A u8"), alpha,
                               GEGL_AUTO_ROWSTRIDE, GEGL_ABYSS_NONE);

              output = icns_compress (width, height, pixels, &macos_size);

              /* ---------------------- */

              temp_size = GUINT32_TO_BE (macos_size + 8);
              fwrite (&temp_size, sizeof (temp_size), 1, fp);

              if (fwrite (output, 1, macos_size, fp) < macos_size)
                {
                  icns_save_info_free (info);
                  g_set_error (error, G_FILE_ERROR,
                               g_file_error_from_errno (errno),
                               _("Error writing icns: %s"),
                               g_strerror (errno));
                  return GIMP_PDB_EXECUTION_ERROR;
                }

              file_size += macos_size + 8;

              /* Write uncompressed mask */
              fwrite (iconTypes[compat_id].mask, sizeof (gchar), 4, fp);
              macos_size = GUINT32_TO_BE ((width * height) + 8);
              fwrite (&macos_size, sizeof (macos_size), 1, fp);
              macos_size = width * height;

              if (fwrite (alpha, 1, macos_size, fp) < macos_size)
                {
                  icns_save_info_free (info);
                  g_set_error (error, G_FILE_ERROR,
                               g_file_error_from_errno (errno),
                               _("Error writing icns: %s"),
                               g_strerror (errno));
                  return GIMP_PDB_EXECUTION_ERROR;
                }

              file_size += (width * height) + 8;

              g_free (pixels);
              g_free (alpha);
              g_object_unref (buffer);
            }
          else
            {
              GimpProcedure  *procedure;
              GimpValueArray *return_vals;
              GimpImage      *temp_image;
              GimpLayer      *temp_layer;
              GFile          *temp_file = NULL;
              FILE           *temp_fp;

              temp_file  = gimp_temp_file ("png");

              /* TODO: Use GimpExportOptions for this when available */
              temp_image = gimp_image_new (width, height,
                                           gimp_image_get_base_type (image));
              if (gimp_image_get_base_type (image) == GIMP_INDEXED)
                gimp_image_set_palette (temp_image,
                                        gimp_image_get_palette (image));

              temp_layer = gimp_layer_new_from_drawable (GIMP_DRAWABLE (iter->data),
                                                         temp_image);
              gimp_image_insert_layer (temp_image, temp_layer, NULL, 0);

              if (include_color_profile &&
                  gimp_image_get_color_profile (image))
                {
                  GimpColorProfile *profile;

                  profile =  gimp_image_get_color_profile (image);
                  gimp_image_set_color_profile (temp_image, profile);
                }

              procedure   = gimp_pdb_lookup_procedure (gimp_get_pdb (), "file-png-export");
              return_vals = gimp_procedure_run (procedure,
                                                "run-mode",              GIMP_RUN_NONINTERACTIVE,
                                                "image",                 temp_image,
                                                "file",                  temp_file,
                                                "interlaced",            FALSE,
                                                "compression",           9,
                                                "bkgd",                  FALSE,
                                                "offs",                  FALSE,
                                                "phys",                  FALSE,
                                                "time",                  FALSE,
                                                "save-transparent",      FALSE,
                                                "optimize-palette",      FALSE,
                                                "include-color-profile", include_color_profile,
                                                NULL);
              gimp_image_delete (temp_image);

              if (GIMP_VALUES_GET_ENUM (return_vals, 0) != GIMP_PDB_SUCCESS)
                {
                  icns_save_info_free (info);
                  g_set_error (error, 0, 0,
                               "Running procedure 'file-png-export' "
                               "for icns export failed: %s",
                               gimp_pdb_get_last_error (gimp_get_pdb ()));

                  return GIMP_PDB_EXECUTION_ERROR;
                }

              temp_fp = g_fopen (g_file_peek_path (temp_file), "rb");
              fseek (temp_fp, 0L, SEEK_END);
              temp_size = ftell (temp_fp);
              fseek (temp_fp, 0L, SEEK_SET);

              g_file_delete (temp_file, NULL, NULL);
              g_object_unref (temp_file);

              fwrite (iconTypes[match].type, sizeof (gchar), 4, fp);
              macos_size = GUINT32_TO_BE (temp_size + 8);
              fwrite (&macos_size, sizeof (macos_size), 1, fp);

              if (temp_size > 0)
                {
                  guchar buf[temp_size];

                  fread (buf, 1, sizeof (buf), temp_fp);

                  if (fwrite (buf, 1, temp_size, fp) < temp_size)
                    {
                      icns_save_info_free (info);
                      g_set_error (error, G_FILE_ERROR,
                                   g_file_error_from_errno (errno),
                                   _("Error writing icns: %s"),
                                   g_strerror (errno));
                      return GIMP_PDB_EXECUTION_ERROR;
                    }
                }
              fclose (temp_fp);

              file_size += temp_size + 8;
          }
          duplicates[match] = 1;
        }

      gimp_progress_update (i / info->num_icons);
    }

  /* Update header with full file size */
  file_size = GUINT32_TO_BE (file_size);
  fseek (fp, 4L, SEEK_SET);
  fwrite (&file_size, sizeof (file_size), 1, fp);

  gimp_progress_update (1.0);

  icns_save_info_free (info);
  fclose (fp);
  return GIMP_PDB_SUCCESS;
}

static guchar *
icns_compress (guint   width,
               guint   height,
               guchar *rgba,
               gint   *out_size)
{
  const guint npixels  = width * height;
  const guint max_size = (npixels * 3) + ((npixels * 3) / 4);

  const guint min_run = 3;   /* Shorter run must be stored as uncompressed */
  const guint max_run = 130; /* Longest same-value run that can be stored */
  const guint min_raw = 1;
  const guint max_raw = 128; /* Longest run of non-matching pixels */

  guint   i;
  guint   j;
  guint   size;
  guint   channel;
  guint   run;
  guint   marker;
  guchar *out_data;
  guchar *run_length;

  run_length = g_new (guchar, npixels);
  if (! run_length)
    {
      g_warning ("icns_compress: couldn't allocate run count buffer (%d bytes)", npixels);
      return NULL;
    }

  out_data = g_new (guchar, max_size);
  if (! out_data)
    {
      g_free (run_length);
      return NULL;
    }

  size = 0;
  /* For some reason 128x128 icons have an extra 4 bytes at the start */
  if (width == 128 && height == 128)
    {
      out_data[size++] = 0;
      out_data[size++] = 0;
      out_data[size++] = 0;
      out_data[size++] = 0;
    }

  for (channel = 0; channel < 3; channel++)
    {
      /* Count all run lengths */
      for (i = 0; i < npixels; i++)
        {
          for (run = 1; run < max_run && (run + i - 1) < npixels; run++)
            if (rgba[i * 4 + channel] != rgba[(i + run) * 4 + channel])
              break;

          run_length[i] = run;
        }

      for (i = 0; i < npixels; i++)
        {
          if (run_length[i] >= min_run)
            {
              /* Compressable! Store and skip ahead */
              out_data[size++] = (run_length[i] - min_run) | 0x80;
              out_data[size++] = rgba[i * 4 + channel];
              i += run_length[i] - 1;
            }
          else
            {
              /* Too short: stuff together as many as you can in a raw run */
              marker = size++;
              run = 0;
              while (run < max_raw && i < npixels && run_length[i] < min_run)
                {
                  for (j = 0; j < run_length[i]; j++)
                    {
                      out_data[size++] = rgba[(i + j) * 4 + channel];
                      run++;
                    }
                  i += run_length[i];
                }
              out_data[marker] = run - min_raw;
              i--;
            }
        }
    }

  g_free (run_length);
  *out_size = size;

  return out_data;
}

static void
icns_save_info_free (IcnsSaveInfo *info)
{
  g_list_free (info->layers);
  memset (info, 0, sizeof (IcnsSaveInfo));
}

GimpPDBStatusType
icns_save_image (GFile                *file,
                 GimpImage            *image,
                 GimpProcedure        *procedure,
                 GimpProcedureConfig  *config,
                 gint32                run_mode,
                 GError              **error)
{
  IcnsSaveInfo  info;
  GList        *iter;
  gboolean      isValidLayers         = FALSE;
  gboolean      include_color_profile = FALSE;

  info.layers    = gimp_image_list_layers (image);
  info.num_icons = g_list_length (info.layers);

  /* Initial check if we have any valid layers to export */
  for (iter = info.layers; iter; iter = iter->next)
    {
      gint width  = gimp_drawable_get_width (iter->data);
      gint height = gimp_drawable_get_height (iter->data);

      if (icns_check_dimensions (width, height))
        {
          isValidLayers = TRUE;
          break;
        }
    }
  if (! isValidLayers)
    {
      g_set_error (error, G_FILE_ERROR, 0,
                   _("No valid sized layers. Only valid layer sizes are "
                     "16x12, 16x16, 18x18, 24x24, 32x32, 36x36, 48x48, "
                     "64x64, 128x128, 256x256, 512x512, or 1024x1024."));

      return GIMP_PDB_EXECUTION_ERROR;
    }

  if (run_mode == GIMP_RUN_INTERACTIVE)
    {
      /* Allow user to override default values */
      if (! icns_save_dialog (&info, image, procedure, config))
        return GIMP_PDB_CANCEL;
    }
  else if (run_mode == GIMP_RUN_NONINTERACTIVE)
    {
      if (! icns_check_compat (NULL, &info))
        {
          g_set_error (error, G_FILE_ERROR, 0,
                       _("Invalid layer size(s). Only valid layer sizes are "
                         "16x12, 16x16, 18x18, 24x24, 32x32, 36x36, 48x48, "
                         "64x64, 128x128, 256x256, 512x512, or 1024x1024."));

          return GIMP_PDB_EXECUTION_ERROR;
        }
    }

  g_object_get (config,
                "include-color-profile", &include_color_profile,
                NULL);

  gimp_progress_init_printf (_("Exporting '%s'"),
                             gimp_file_get_utf8_name (file));

  return icns_export_image (file, &info, image, include_color_profile, error);
}

/* --- end plug-ins/field-io/file-icns/file-icns-export.c --- */

/* --- begin plug-ins/field-io/file-icns/file-icns-load.c --- */
/* AmmoOS Image - The AmmoOS Field Image Research
 * Copyright (C) 1995-1999 Spencer Kimball and Peter Mattis
 *
 * file-icns-load.c
 * Copyright (C) 2004 Brion Vibber <brion@pobox.com>
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

#include "config.h"

#include <errno.h>
#include <string.h>

#include <glib/gstdio.h>

#include <libgimp/ammoos.h>
#include <libgimp/gimpui.h>

#include <png.h>

/* #define ICNS_DBG */

#include "file-icns.h"
#include "file-icns-data.h"
#include "file-icns-load.h"

#include "libgimp/stdplugins-intl.h"

IcnsResource * resource_load     (FILE         *file);

IcnsResource * resource_find     (GList        *resources,
                                  gchar        *type,
                                  gint          max);

gboolean       resource_get_next (IcnsResource *icns,
                                  IcnsResource *res);

void           icns_slurp        (guchar       *dest,
                                  IconType     *icontype,
                                  IcnsResource *icns,
                                  IcnsResource *mask);

gboolean       icns_decompress   (guchar       *dest,
                                  IconType     *icontype,
                                  gint          n_channels,
                                  IcnsResource *image,
                                  IcnsResource *mask);

void           icns_attach_image (GimpImage    *image,
                                  IconType     *icontype,
                                  IcnsResource *icns,
                                  IcnsResource *mask,
                                  gboolean      isOSX);

GimpImage *    icns_load         (IcnsResource *icns,
                                  GFile        *file);

/* Ported from Brion Vibber's icnsload.c code, under the GPL license, version 3
 * or any later version of the license */
IcnsResource *
resource_load (FILE *file)
{
  IcnsResource *res = NULL;

  if (file)
    {
      IcnsResourceHeader header;

      if (1 == fread (&header, sizeof (IcnsResourceHeader), 1, file))
        {
          gchar   type[5];
          guint32 size;

#ifndef _UCRT
          strncpy (type, header.type, 4);
#else
          strncpy_s (type, 5, header.type, 4);
#endif
          type[4] = '\0';
          size = GUINT32_FROM_BE (header.size);

          if (! strncmp (header.type, "icns", 4) && size > sizeof (IcnsResourceHeader))
            {
              res = (IcnsResource *) g_new (guchar, sizeof (IcnsResource) + size);
#ifndef _UCRT
              strncpy (res->type, header.type, 4);
#else
              strncpy_s (res->type, 5, header.type, 4);
#endif
              res->type[4] = '\0';
              res->size = size;
              res->cursor = sizeof (IcnsResourceHeader);
              res->data = (guchar *) res + sizeof (IcnsResource);
              fseek (file, 0, SEEK_SET);

              if (size != fread (res->data, 1, res->size, file))
                {
                  g_message ("** expected %d bytes\n", size);
                  g_free (res);
                  res = NULL;
                }
            }
        }
      else
        {
          g_message (("** couldn't read icns header.\n"));
        }
    }
  else
    {
      g_message (("** couldn't open file.\n"));
    }
  return res;
}

IcnsResource *
resource_find (GList        *resources,
               gchar        *type,
               gint          max)
{
  GList *list;

  for (list = resources; list; list = g_list_next (list))
    {
      IcnsResource *res = list->data;

      if (! strncmp (res->type, type, 4))
        return res;
    }
  return NULL;
}

gboolean
resource_get_next (IcnsResource *icns,
                   IcnsResource *res)
{
  IcnsResourceHeader *header;

  if (icns->size - icns->cursor < sizeof (IcnsResourceHeader))
    return FALSE;

  header = (IcnsResourceHeader *) &(icns->data[icns->cursor]);
#ifndef _UCRT
  strncpy (res->type, header->type, 4);
#else
  strncpy_s (res->type, 5, header->type, 4);
#endif
  res->size   = GUINT32_FROM_BE (header->size);
  res->cursor = sizeof (IcnsResourceHeader);
  res->data   = &(icns->data[icns->cursor]);

  if (! res->size)
    return FALSE;

  icns->cursor += res->size;
  if (icns->cursor > icns->size)
    {
      gchar typestring[5];

      fourcc_get_string (icns->type, typestring);
      g_message ("icns resource_get_next: resource too big! type '%s', size %u\n",
                 typestring, icns->size);

      return FALSE;
    }
  return TRUE;
}

GimpImage *
icns_load (IcnsResource *icns,
           GFile        *file)
{
  GList        *resources;
  IcnsResource *resource;
  guint         nResources;
  gfloat        current_resources = 0;
  GimpImage    *image;

  resources = NULL;
  resource  = g_new (IcnsResource, 1);

  /* Largest .icns icon is 1024 x 1024 */
  image = gimp_image_new (1024, 1024, GIMP_RGB);

  nResources = 0;
  while (resource_get_next (icns, resource))
    {
      resources = g_list_append (resources, resource);

      resource = g_new (IcnsResource, 1);
    }

  for (gint i = 0; iconTypes[i].type; i++)
    {
      IcnsResource *icns;
      IcnsResource *mask = NULL;

      if ((icns = resource_find (resources, iconTypes[i].type, nResources)))
        {
          if (! iconTypes[i].isModern && iconTypes[i].mask)
            mask = resource_find (resources, iconTypes[i].mask, nResources);

          icns_attach_image (image, &iconTypes[i], icns, mask, iconTypes[i].isModern);

          gimp_progress_update (current_resources++ / nResources);
        }
    }

  gimp_image_resize_to_layers (image);
  g_list_free_full (resources, g_free);
  g_free (resource);
  return image;
}

void
icns_slurp (guchar       *dest,
            IconType     *icontype,
            IcnsResource *icns,
            IcnsResource *mask)
{
  guint  out;
  guint  max;
  guchar bucket = 0;
  guchar bit;
  guint  index;

  max          = icontype->width * icontype->height;
  icns->cursor = sizeof (IcnsResourceHeader);

  switch (icontype->bits)
    {
      case 1:
        for (out = 0; out < max; out++)
          {
            if (out % 8 == 0)
              {
                if (icns->cursor >= icns->size)
                  {
                    g_message ("Invalid or corrupt icns resource file.");
                    return;
                  }

                bucket = icns->data[icns->cursor++];
              }

            bit = (bucket & 0x80) ? 0 : 255;
            bucket = bucket << 1;
            dest[out * 4]     = bit;
            dest[out * 4 + 1] = bit;
            dest[out * 4 + 2] = bit;
            if (! mask)
              dest[out * 4 + 3] = 255;
          }
        break;

      case 4:
        for (out = 0; out < max; out++)
          {
            if (icns->cursor >= icns->size)
              {
                g_message ("Invalid or corrupt icns resource file.");
                return;
              }

            if (out % 2 == 0)
              bucket = icns->data[icns->cursor++];

            index = 3 * (bucket & 0xf0) >> 4;
            bucket = bucket << 4;
            dest[out * 4]     = icns_colormap_4[index];
            dest[out * 4 + 1] = icns_colormap_4[index + 1];
            dest[out * 4 + 2] = icns_colormap_4[index + 2];
          }
        break;

      case 8:
        for (out = 0; out < max; out++)
          {
            if (icns->cursor >= icns->size)
              {
                g_message ("Invalid or corrupt icns resource file.");
                return;
              }

            index = 3 * icns->data[icns->cursor++];
            dest[out * 4]     = icns_colormap_8[index];
            dest[out * 4 + 1] = icns_colormap_8[index + 1];
            dest[out * 4 + 2] = icns_colormap_8[index + 2];
            dest[out * 4 + 3] = 255;
          }
        break;

      case 32:
        for (out = 0; out < max; out++)
          {
            if (icns->cursor >= (icns->size + 2))
              {
                g_message ("Invalid or corrupt icns resource file.");
                return;
              }

            dest[out * 4]     = icns->data[icns->cursor++];
            dest[out * 4 + 1] = icns->data[icns->cursor++];
            dest[out * 4 + 2] = icns->data[icns->cursor++];
            /* Throw away alpha, use the mask */
            icns->cursor++;

            if (mask && mask->cursor >= (icns->size))
              {
                g_message ("Invalid or corrupt icns resource file.");
                return;
              }

            if (mask)
              dest[out * 4 + 3] = icns->data[mask->cursor++];
            else
              dest[out * 4 + 3] = 255;
          }
        break;
      }

    /* Now for the mask */
    if (mask && icontype->bits != 32)
      {
        mask->cursor =
          sizeof (IcnsResourceHeader) + icontype->width * icontype->height / 8;

        for (out = 0; out < max; out++)
          {
            if (out % 8 == 0)
              {
                if (mask->cursor >= mask->size)
                  {
                    g_message ("Invalid or corrupt icns resource file.");
                    return;
                  }
                bucket = mask->data[mask->cursor++];
              }

            bit = (bucket & 0x80) ? 255 : 0;
            bucket = bucket << 1;
            dest[out * 4 + 3] = bit;
          }
      }
}

gboolean
icns_decompress (guchar       *dest,
                 IconType     *icontype,
                 gint          n_channels,
                 IcnsResource *image,
                 IcnsResource *mask)
{
  guint  max;
  guint  channel;
  guint  out;
  guchar run;
  guchar val;

  max = icontype->width * icontype->height;
  memset (dest, 255, max * 4);

  /* For some reason there seem to be 4 null bytes at the start of an it32. */
  if (! strncmp (icontype->type, "it32", 4))
    image->cursor += 4;

  for (channel = 0; channel < n_channels; channel++)
    {
      out = 0;
      while (out < max)
        {
          run = image->data[image->cursor++];

          if (run & 0x80)
            {
              /* Compressed */
              if (image->cursor >= image->size)
                {
                  g_message ("Corrupt icon: compressed run overflows input size.");
                  return FALSE;
                }

              val = image->data[image->cursor++];

              for (run -= 125; run > 0; run--)
                {
                  if (out >= max)
                    {
                      g_message ("Corrupt icon? compressed run overflows output size.");
                      return FALSE;
                    }
                  dest[out++ * 4 + channel] = val;
                }
            }
          else
            {
              /* Uncompressed */
              for (run += 1; run > 0; run--)
                {
                  if (image->cursor >= image->size)
                    {
                      g_message ("Corrupt icon: uncompressed run overflows input size.");
                      return FALSE;
                    }
                  if (out >= max)
                    {
                      g_message ("Corrupt icon: uncompressed run overflows output size.");
                      return FALSE;
                    }
                  dest[out++ * 4 + channel] = image->data[image->cursor++];
                }
            }
        }
    }

  /* If we have four channels, this is compressed ARGB data and
     we need to rotate the channels */
  if (n_channels == 4)
    {
      gint pixel_max = max * 4;

      for (gint i = 0; i < pixel_max; i += 4)
        {
          guchar alpha = dest[i];

          for (gint j = 0; j < 3; j++)
            dest[i + j] = dest[i + j + 1];

          dest[i + 3] = alpha;
        }
    }
  else if (mask)
    {
      gchar typestring[5];
      fourcc_get_string (mask->type, typestring);

      for (out = 0; out < max; out++)
        dest[out * 4 + 3] = mask->data[mask->cursor++];
    }
  return TRUE;
}

void
icns_attach_image (GimpImage    *image,
                   IconType     *icontype,
                   IcnsResource *icns,
                   IcnsResource *mask,
                   gboolean      isOSX)
{
  gchar           layer_name[5];
  guchar         *dest;
  GimpLayer      *layer;
  GeglBuffer     *buffer;
  guint           row;
  guint           expected_size;
  gboolean        layer_loaded = FALSE;

#ifndef _UCRT
  strncpy (layer_name, icontype->type, 4);
#else
  strncpy_s (layer_name, 5, icontype->type, 4);
#endif
  layer_name[4] = '\0';

  row = 4 * icontype->width;
  dest = g_malloc (row * icontype->height);

  expected_size =
    (icontype->width * icontype->height * icontype->bits) / 8;

  if (icns == mask)
    expected_size *= 2;

  expected_size += sizeof (IcnsResourceHeader);

  if (isOSX)
    {
      gchar           image_type[5];
      GimpImage      *temp_image;
      GFile          *temp_file      = NULL;
      FILE           *fp;
      GimpValueArray *return_vals    = NULL;
      GimpLayer     **layers;
      GimpLayer      *new_layer;
      gchar          *temp_file_type = NULL;
      gchar          *procedure_name = NULL;

#ifndef _UCRT
      strncpy (image_type, (gchar *) icns->data + 8, 4);
#else
      strncpy_s (image_type, 5, (gchar *) icns->data + 8, 4);
#endif
      image_type[4] = '\0';

      /* PNG */
      if (! strncmp (image_type, "\x89\x50\x4E\x47", 4))
        {
          temp_file_type = "png";
          procedure_name = "file-png-load";
        }
      /* JPEG 2000 */
      else if (! strncmp (image_type, "\x0CjP", 3))
        {
          temp_file_type = "jp2";
          procedure_name = "file-jp2-load";
        }
      /* ARGB (compressed) */
      else if (! strncmp (image_type, "ARGB", 4))
        {
          icns->cursor += 4;
          icns_decompress (dest, icontype, 4, icns, FALSE);
        }

      if (temp_file_type && procedure_name)
        {
          GimpProcedure *procedure;

          temp_file = gimp_temp_file (temp_file_type);
          fp = g_fopen (g_file_peek_path (temp_file), "wb");

          if (! fp)
            {
              g_message (_("Error trying to open temporary %s file '%s' "
                         "for icns loading: %s"),
                         temp_file_type,
                         gimp_file_get_utf8_name (temp_file),
                         g_strerror (errno));
              return;
            }

          fwrite (icns->data + 8, sizeof (guchar), icns->size - 8, fp);
          fclose (fp);

          procedure   = gimp_pdb_lookup_procedure (gimp_get_pdb (), procedure_name);
          return_vals = gimp_procedure_run (procedure,
                                            "run-mode", GIMP_RUN_NONINTERACTIVE,
                                            "file",     temp_file,
                                            NULL);
        }

      if (return_vals)
        {
          temp_image = g_value_get_object (gimp_value_array_index (return_vals, 1));

          layers = gimp_image_get_layers (temp_image);
          new_layer = gimp_layer_new_from_drawable (GIMP_DRAWABLE (layers[0]), image);
          gimp_item_set_name (GIMP_ITEM (new_layer), layer_name);
          gimp_image_insert_layer (image, new_layer, NULL, 0);

          layer_loaded = TRUE;

          /* Use the first color profile we encounter */
          if (! gimp_image_get_color_profile (image) &&
              gimp_image_get_color_profile (temp_image))
            {
              GimpColorProfile *profile;

              profile = gimp_image_get_color_profile (temp_image);
              gimp_image_set_color_profile (image, profile);

              g_object_unref (profile);
            }

          g_file_delete (temp_file, NULL, NULL);
          g_object_unref (temp_file);
          g_free (layers);
          gimp_image_delete (temp_image);
        }
      g_clear_pointer (&return_vals, gimp_value_array_unref);
    }
  else
    {
      if (icontype->bits != 32 || expected_size == icns->size)
        icns_slurp (dest, icontype, icns, mask);
      else
        icns_decompress (dest, icontype, 3, icns, mask);
    }

  if (! layer_loaded)
    {
      layer = gimp_layer_new (image, layer_name, icontype->width, icontype->height,
                              GIMP_RGBA_IMAGE, 100,
                              gimp_image_get_default_new_layer_mode (image));

      buffer = gimp_drawable_get_buffer (GIMP_DRAWABLE (layer));

      gegl_buffer_set (buffer,
                       GEGL_RECTANGLE (0, 0, icontype->width, icontype->height),
                       0, NULL,
                       dest, GEGL_AUTO_ROWSTRIDE);

      gimp_image_insert_layer (image, layer, NULL, 0);

      g_object_unref (buffer);
    }

  g_free (dest);
}

GimpImage *
icns_load_image (GFile        *file,
                 gint32       *file_offset,
                 GError      **error)
{
  FILE          *fp;
  IcnsResource  *icns;
  GimpImage     *image;

  gegl_init (NULL, NULL);

  gimp_progress_init_printf (_("Opening '%s'"),
                             gimp_file_get_utf8_name (file));

  fp = g_fopen (g_file_peek_path (file), "rb");

  if (! fp)
    {
      g_set_error (error, G_FILE_ERROR, g_file_error_from_errno (errno),
                   _("Could not open '%s' for reading: %s"),
                   gimp_file_get_utf8_name (file), g_strerror (errno));
      return NULL;
    }

  icns = resource_load (fp);

  fclose (fp);

  if (! icns)
    {
      g_message ("Invalid or corrupt icns resource file.");
      return NULL;
    }

  image = icns_load (icns, file);

  g_free (icns);

  gimp_progress_update (1.0);

  return image;
}

GimpImage *
icns_load_thumbnail_image (GFile   *file,
                           gint    *width,
                           gint    *height,
                           gint32   file_offset,
                           GError **error)
{
  gint          w          = 0;
  gint          target_w   = *width;
  FILE         *fp;
  GimpImage    *image      = NULL;
  IcnsResource *icns;
  GList        *resources;
  IcnsResource *resource;
  IcnsResource *mask       = NULL;
  guint         i;
  gint          match      = -1;
  guint         nResources = 0;

  gegl_init (NULL, NULL);

  gimp_progress_init_printf (_("Opening thumbnail for '%s'"),
                             gimp_file_get_utf8_name (file));

  fp = g_fopen (g_file_peek_path (file), "rb");

  if (! fp)
    {
      g_set_error (error, G_FILE_ERROR, g_file_error_from_errno (errno),
                   _("Could not open '%s' for reading: %s"),
                   gimp_file_get_utf8_name (file), g_strerror (errno));
      return NULL;
    }

  icns = resource_load (fp);
  fclose (fp);

  if (! icns)
    {
      g_message ("Invalid or corrupt icns resource file.");
      return NULL;
    }

  image = gimp_image_new (1024, 1024, GIMP_RGB);

  resources = NULL;
  resource  = g_new (IcnsResource, 1);

  while (resource_get_next (icns, resource))
    {
      resources = g_list_append (resources, resource);

      resource = g_new (IcnsResource, 1);
    }

  *width  = 0;
  *height = 0;
  for (i = 0; iconTypes[i].type; i++)
    {
      if ((icns = resource_find (resources, iconTypes[i].type, nResources)))
        {
          if (iconTypes[i].width > w && iconTypes[i].width <= target_w)
            {
              w = iconTypes[i].width;
              match = i;
            }
        }
      *width  = MAX (*width, iconTypes[i].width);
      *height = MAX (*height, iconTypes[i].height);
    }

  if (match == -1)
    {
      /* We didn't find any icon with size smaller or equal to the target.
       * Settle with the smallest bigger icon instead.
       */
      for (i = 0; iconTypes[i].type; i++)
        {
          if ((icns = resource_find (resources, iconTypes[i].type, nResources)))
            {
              if (match == -1 || iconTypes[i].width < w)
                {
                  w = iconTypes[i].width;
                  match = i;
                }
            }
        }
    }

  if (match > -1)
    {
      icns = resource_find (resources, iconTypes[match].type, nResources);

      if (! iconTypes[match].isModern && iconTypes[i].mask)
        mask = resource_find (resources, iconTypes[match].mask, nResources);

      icns_attach_image (image, &iconTypes[match], icns, mask, iconTypes[match].isModern);

      gimp_image_resize_to_layers (image);
    }
  else
    {
      g_message ("Invalid or corrupt icns resource file.");
      return NULL;
    }

  g_list_free_full (resources, g_free);
  g_free (resource);

  gimp_progress_update (1.0);

  return image;
}

/* --- end plug-ins/field-io/file-icns/file-icns-load.c --- */

/* --- begin plug-ins/field-io/file-icns/file-icns.c --- */
/* AmmoOS Image - The AmmoOS Field Image Research
 * Copyright (C) 1995-1999 Spencer Kimball and Peter Mattis
 *
 * file-icns.c
 * Copyright (C) 2004 Brion Vibber <brion@pobox.com>
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

#include "config.h"

#include <stdlib.h>
#include <string.h>

#include <glib/gstdio.h>

#include <libgimp/ammoos.h>
#include <libgimp/gimpui.h>

/* #define ICNS_DBG */

#include "file-icns.h"
#include "file-icns-load.h"
#include "file-icns-export.h"

#include "libgimp/stdplugins-intl.h"

#define LOAD_PROC           "file-icns-load"
#define LOAD_THUMB_PROC     "file-icns-load-thumb"
#define EXPORT_PROC         "file-icns-export"


typedef struct _Icns      Icns;
typedef struct _IcnsClass IcnsClass;

struct _Icns
{
  GimpPlugIn      parent_instance;
};

struct _IcnsClass
{
  GimpPlugInClass parent_class;
};


#define ICNS_TYPE (icns_get_type ())
#define ICNS(obj) (G_TYPE_CHECK_INSTANCE_CAST ((obj), ICNS_TYPE, Icns))

GType                   icns_get_type         (void) G_GNUC_CONST;

static GList          * icns_query_procedures (GimpPlugIn            *plug_in);
static GimpProcedure  * icns_create_procedure (GimpPlugIn            *plug_in,
                                               const gchar           *name);

static GimpValueArray * icns_load             (GimpProcedure         *procedure,
                                               GimpRunMode            run_mode,
                                               GFile                 *file,
                                               GimpMetadata          *metadata,
                                               GimpMetadataLoadFlags *flags,
                                               GimpProcedureConfig   *config,
                                               gpointer               run_data);
static GimpValueArray * icns_load_thumb       (GimpProcedure         *procedure,
                                               GFile                 *file,
                                               gint                   size,
                                               GimpProcedureConfig   *config,
                                               gpointer               run_data);
static GimpValueArray * icns_export           (GimpProcedure         *procedure,
                                               GimpRunMode            run_mode,
                                               GimpImage             *image,
                                               GFile                 *file,
                                               GimpExportOptions     *options,
                                               GimpMetadata          *metadata,
                                               GimpProcedureConfig   *config,
                                               gpointer               run_data);


G_DEFINE_TYPE (Icns, icns, GIMP_TYPE_PLUG_IN)

GIMP_MAIN (ICNS_TYPE)
DEFINE_STD_SET_I18N

static void
icns_class_init (IcnsClass *klass)
{
  GimpPlugInClass *plug_in_class  = GIMP_PLUG_IN_CLASS (klass);

  plug_in_class->query_procedures = icns_query_procedures;
  plug_in_class->create_procedure = icns_create_procedure;
  plug_in_class->set_i18n         = STD_SET_I18N;
}

static void
icns_init (Icns *icns)
{
}

static GList *
icns_query_procedures (GimpPlugIn *plug_in)
{
  GList *list = NULL;

  list = g_list_append (list, g_strdup (LOAD_THUMB_PROC));
  list = g_list_append (list, g_strdup (LOAD_PROC));
  list = g_list_append (list, g_strdup (EXPORT_PROC));

  return list;
}

static GimpProcedure *
icns_create_procedure (GimpPlugIn  *plug_in,
                       const gchar *name)
{
  GimpProcedure *procedure = NULL;

  if (! strcmp (name, LOAD_PROC))
    {
      procedure = gimp_load_procedure_new (plug_in, name,
                                           GIMP_PDB_PROC_TYPE_PLUGIN,
                                           icns_load, NULL, NULL);

      gimp_procedure_set_menu_label (procedure, _("Icns"));

      gimp_procedure_set_documentation (procedure,
                                        _("Loads files in Apple Icon Image format"),
                                        _("Loads Apple Icon Image files."),
                                        name);
      gimp_procedure_set_attribution (procedure,
                                      "Brion Vibber <brion@pobox.com>",
                                      "Brion Vibber <brion@pobox.com>",
                                      "2004");

      gimp_file_procedure_set_mime_types (GIMP_FILE_PROCEDURE (procedure),
                                          "image/x-icns");
      gimp_file_procedure_set_extensions (GIMP_FILE_PROCEDURE (procedure),
                                          "icns");
      gimp_file_procedure_set_magics (GIMP_FILE_PROCEDURE (procedure),
                                      "0,string,\x69\x63\x6E\x73");

      gimp_load_procedure_set_thumbnail_loader (GIMP_LOAD_PROCEDURE (procedure),
                                                LOAD_THUMB_PROC);
    }
  else if (! strcmp (name, LOAD_THUMB_PROC))
    {
      procedure = gimp_thumbnail_procedure_new (plug_in, name,
                                                GIMP_PDB_PROC_TYPE_PLUGIN,
                                                icns_load_thumb, NULL, NULL);

      gimp_procedure_set_documentation (procedure,
                                        "Loads a preview from an Apple Icon Image file",
                                        "",
                                        name);
      gimp_procedure_set_attribution (procedure,
                                      "Brion Vibber <brion@pobox.com>",
                                      "Brion Vibber <brion@pobox.com>",
                                      "2004");
    }
  else if (! strcmp (name, EXPORT_PROC))
    {
      procedure = gimp_export_procedure_new (plug_in, name,
                                             GIMP_PDB_PROC_TYPE_PLUGIN,
                                             FALSE, icns_export, NULL, NULL);

      gimp_procedure_set_image_types (procedure, "*");

      gimp_procedure_set_menu_label (procedure, _("Apple Icon Image"));
      gimp_procedure_set_icon_name (procedure, GIMP_ICON_BRUSH);

      gimp_procedure_set_documentation (procedure,
                                        "Exports files in Apple Icon Image file format",
                                        "Exports files in Apple Icon Image file format",
                                        name);
      gimp_procedure_set_attribution (procedure,
                                      "Brion Vibber <brion@pobox.com>",
                                      "Brion Vibber <brion@pobox.com>",
                                      "2004");

      gimp_file_procedure_set_format_name (GIMP_FILE_PROCEDURE (procedure),
                                           "Apple Icon Image");
      gimp_file_procedure_set_mime_types (GIMP_FILE_PROCEDURE (procedure),
                                          "image/x-icns");
      gimp_file_procedure_set_extensions (GIMP_FILE_PROCEDURE (procedure),
                                          "icns");

      gimp_export_procedure_set_support_profile (GIMP_EXPORT_PROCEDURE (procedure), TRUE);
    }

  return procedure;
}

static GimpValueArray *
icns_load (GimpProcedure         *procedure,
           GimpRunMode            run_mode,
           GFile                 *file,
           GimpMetadata          *metadata,
           GimpMetadataLoadFlags *flags,
           GimpProcedureConfig   *config,
           gpointer               run_data)
{
  GimpValueArray *return_vals;
  GimpImage      *image;
  GError         *error       = NULL;

  gegl_init (NULL, NULL);

  image = icns_load_image (file, NULL, &error);

  if (! image)
    return gimp_procedure_new_return_values (procedure,
                                             GIMP_PDB_EXECUTION_ERROR,
                                             error);

  return_vals = gimp_procedure_new_return_values (procedure,
                                                  GIMP_PDB_SUCCESS,
                                                  NULL);

  GIMP_VALUES_SET_IMAGE (return_vals, 1, image);

  return return_vals;
}

static GimpValueArray *
icns_load_thumb (GimpProcedure       *procedure,
                 GFile               *file,
                 gint                 size,
                 GimpProcedureConfig *config,
                 gpointer             run_data)
{
  GimpValueArray *return_vals;
  gint            width;
  gint            height;
  GimpImage      *image;
  GError         *error = NULL;

  gegl_init (NULL, NULL);

  width  = size;
  height = size;

  image = icns_load_thumbnail_image (file,
                                     &width, &height, 0, &error);

  if (! image)
    return gimp_procedure_new_return_values (procedure,
                                             GIMP_PDB_EXECUTION_ERROR,
                                             error);

  return_vals = gimp_procedure_new_return_values (procedure,
                                                  GIMP_PDB_SUCCESS,
                                                  NULL);

  GIMP_VALUES_SET_IMAGE (return_vals, 1, image);
  GIMP_VALUES_SET_INT   (return_vals, 2, width);
  GIMP_VALUES_SET_INT   (return_vals, 3, height);

  gimp_value_array_truncate (return_vals, 4);

  return return_vals;
}

static GimpValueArray *
icns_export (GimpProcedure        *procedure,
             GimpRunMode           run_mode,
             GimpImage            *image,
             GFile                *file,
             GimpExportOptions    *options,
             GimpMetadata         *metadata,
             GimpProcedureConfig  *config,
             gpointer              run_data)
{
  GimpPDBStatusType  status;
  GError            *error = NULL;

  gegl_init (NULL, NULL);

  status = icns_save_image (file, image, procedure, config, run_mode, &error);

  return gimp_procedure_new_return_values (procedure, status, error);
}

/* Buffer should point to *at least 5 byte buffer*! */
void
fourcc_get_string (gchar *fourcc,
                   gchar *buf)
{
  buf = fourcc;
  buf[4] = 0;
}

/* --- end plug-ins/field-io/file-icns/file-icns.c --- */

/* --- begin plug-ins/field-io/file-sgi/sgi-lib.c --- */
/*
 * SGI image file format library routines.
 *
 * Copyright 1997-1998 Michael Sweet (mike@easysw.com)
 *
 * This program is free software: you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the Free
 * Software Foundation; either version 3 of the License, or (at your option)
 * any later version.
 *
 * This program is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
 * or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
 * for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 *
 * Contents:
 *
 *   sgiClose()    - Close an SGI image file.
 *   sgiGetRow()   - Get a row of image data from a file.
 *   sgiOpen()     - Open an SGI image file for reading or writing.
 *   sgiOpenFile() - Open an SGI image file for reading or writing.
 *   sgiPutRow()   - Put a row of image data to a file.
 *   getlong()     - Get a 32-bit big-endian integer.
 *   getshort()    - Get a 16-bit big-endian integer.
 *   putlong()     - Put a 32-bit big-endian integer.
 *   putshort()    - Put a 16-bit big-endian integer.
 *   read_rle8()   - Read 8-bit RLE data.
 *   read_rle16()  - Read 16-bit RLE data.
 *   write_rle8()  - Write 8-bit RLE data.
 *   write_rle16() - Write 16-bit RLE data.
 *
 * Revision History:
 *
 *   $Log$
 *   Revision 1.9  2005/03/04 13:23:31  neo
 *   2005-03-04  Sven Neumann  <sven@ammoos.org>
 *
 *      * plug-ins/FractalExplorer
 *      * plug-ins/Lighting
 *      * plug-ins/bmp
 *      * plug-ins/dbbrowser
 *      * plug-ins/faxg3
 *      * plug-ins/fits
 *      * plug-ins/flame
 *      * plug-ins/gfig
 *      * plug-ins/gflare
 *      * plug-ins/gfli
 *      * plug-ins/gimpressionist
 *      * plug-ins/ifscompose
 *      * plug-ins/jpeg
 *      * plug-ins/maze
 *      * plug-ins/pagecurl
 *      * plug-ins/print
 *      * plug-ins/rcm
 *      * plug-ins/script-fu
 *      * plug-ins/sel2path
 *      * plug-ins/sgi
 *      * plug-ins/twain
 *      * plug-ins/winicon
 *      * plug-ins/xjt: ported to gstdio, removed unnecessary includes,
 *      minor fixes to filename handling here and there.
 *
 *   Revision 1.8  2003/04/07 11:59:33  neo
 *   2003-04-07  Sven Neumann  <sven@ammoos.org>
 *
 *      * plug-ins/sgi/sgi.h
 *      * plug-ins/sgi/sgilib.c: applied a patch from marek@aki.cz that
 *      adds support for reading SGI files in little-endian format. Fixes
 *      bug #106610.
 *
 *   Revision 1.7  1998/06/06 23:22:21  yosh
 *   * adding Lighting plugin
 *
 *   * updated despeckle, png, sgi, and sharpen
 *
 *   -Yosh
 *
 *   Revision 1.5  1998/04/23  17:40:49  mike
 *   Updated to support 16-bit <unsigned> image data.
 *
 *   Revision 1.4  1998/02/05  17:10:58  mike
 *   Added sgiOpenFile() function for opening an existing file pointer.
 *
 *   Revision 1.3  1997/07/02  16:40:16  mike
 *   sgiOpen() wasn't opening files with "rb" or "wb+".  This caused problems
 *   on PCs running Windows/DOS...
 *
 *   Revision 1.2  1997/06/18  00:55:28  mike
 *   Updated to hold length table when writing.
 *   Updated to hold current length when doing ARLE.
 *   Wasn't writing length table on close.
 *   Wasn't saving new line into arle_row when necessary.
 *
 *   Revision 1.1  1997/06/15  03:37:19  mike
 *   Initial revision
 */

#include "config.h"

#include <stdlib.h>
#include <string.h>

#include <glib.h>
#include <glib/gstdio.h>

#include "sgi-lib.h"


/*
 * Local functions...
 */

static int      getlong(sgi_t*);
static int      getshort(sgi_t*);
static int      putlong(long, sgi_t*);
static int      putshort(unsigned short, sgi_t*);
static int      read_rle8(sgi_t*, unsigned short *, int);
static int      read_rle16(sgi_t*, unsigned short *, int);
static int      write_rle8(sgi_t*, unsigned short *, int);
static int      write_rle16(sgi_t*, unsigned short *, int);


/*
 * 'sgiClose()' - Close an SGI image file.
 */

int
sgiClose(sgi_t *sgip)   /* I - SGI image */
{
  int   i;              /* Return status */
  long  *offset;        /* Looping var for offset table */


  if (sgip == NULL)
    return (-1);

  if (sgip->mode == SGI_WRITE && sgip->comp != SGI_COMP_NONE)
  {
   /*
    * Write the scanline offset table to the file...
    */

    fseek(sgip->file, 512, SEEK_SET);

    for (i = sgip->ysize * sgip->zsize, offset = sgip->table[0];
         i > 0;
         i --, offset ++)
      if (putlong(offset[0], sgip) < 0)
        return (-1);

    for (i = sgip->ysize * sgip->zsize, offset = sgip->length[0];
         i > 0;
         i --, offset ++)
      if (putlong(offset[0], sgip) < 0)
        return (-1);
  };

  if (sgip->table != NULL)
  {
    free(sgip->table[0]);
    free(sgip->table);
  };

  if (sgip->length != NULL)
  {
    free(sgip->length[0]);
    free(sgip->length);
  };

  if (sgip->comp == SGI_COMP_ARLE)
    free(sgip->arle_row);

  i = fclose(sgip->file);
  free(sgip);

  return (i);
}


/*
 * 'sgiGetRow()' - Get a row of image data from a file.
 */

int
sgiGetRow(sgi_t          *sgip, /* I - SGI image */
          unsigned short *row,  /* O - Row to read */
          int            y,     /* I - Line to read */
          int            z)     /* I - Channel to read */
{
  int   x;              /* X coordinate */
  long  offset;         /* File offset */


  if (sgip == NULL ||
      row == NULL ||
      y < 0 || y >= sgip->ysize ||
      z < 0 || z >= sgip->zsize)
    return (-1);

  switch (sgip->comp)
  {
    case SGI_COMP_NONE :
       /*
        * Seek to the image row - optimize buffering by only seeking if
        * necessary...
        */

        offset = 512 + (y + z * sgip->ysize) * sgip->xsize * sgip->bpp;
        if (offset != ftell(sgip->file))
          fseek(sgip->file, offset, SEEK_SET);

        if (sgip->bpp == 1)
        {
          for (x = sgip->xsize; x > 0; x --, row ++)
            *row = getc(sgip->file);
        }
        else
        {
          for (x = sgip->xsize; x > 0; x --, row ++)
            *row = getshort(sgip);
        };
        break;

    case SGI_COMP_RLE :
        offset = sgip->table[z][y];
        if (offset != ftell(sgip->file))
          fseek(sgip->file, offset, SEEK_SET);

        if (sgip->bpp == 1)
          return (read_rle8(sgip, row, sgip->xsize));
        else
          return (read_rle16(sgip, row, sgip->xsize));
        break;
  };

  return (0);
}


/*
 * 'sgiOpen()' - Open an SGI image file for reading or writing.
 */

sgi_t *
sgiOpen(const char *filename,   /* I - File to open */
        int         mode,       /* I - Open mode (SGI_READ or SGI_WRITE) */
        int         comp,       /* I - Type of compression */
        int         bpp,        /* I - Bytes per pixel */
        int         xsize,      /* I - Width of image in pixels */
        int         ysize,      /* I - Height of image in pixels */
        int         zsize)      /* I - Number of channels */
{
  sgi_t *sgip;          /* New SGI image file */
  FILE  *file;          /* Image file pointer */


  if (mode == SGI_READ)
    file = g_fopen(filename, "rb");
  else
    file = g_fopen(filename, "w+b");

  if (file == NULL)
    return (NULL);

  if ((sgip = sgiOpenFile(file, mode, comp, bpp, xsize, ysize, zsize)) == NULL)
    fclose(file);

  return (sgip);
}


/*
 * 'sgiOpenFile()' - Open an SGI image file for reading or writing.
 */

sgi_t *
sgiOpenFile(FILE *file, /* I - File to open */
            int  mode,  /* I - Open mode (SGI_READ or SGI_WRITE) */
            int  comp,  /* I - Type of compression */
            int  bpp,   /* I - Bytes per pixel */
            int  xsize, /* I - Width of image in pixels */
            int  ysize, /* I - Height of image in pixels */
            int  zsize) /* I - Number of channels */
{
  int   i, j;           /* Looping var */
  char  name[80];       /* Name of file in image header */
  short magic;          /* Magic number */
  sgi_t *sgip;          /* New image pointer */


  if ((sgip = calloc(sizeof(sgi_t), 1)) == NULL)
    return (NULL);

  sgip->file = file;
  sgip->swapBytes = 0;

  switch (mode)
  {
    case SGI_READ :
        sgip->mode = SGI_READ;

        magic = getshort(sgip);
        if (magic != SGI_MAGIC)
        {
          /* try little endian format */
          magic = ((magic >> 8) & 0x00ff) | ((magic << 8) & 0xff00);
          if(magic != SGI_MAGIC) {
            free(sgip);
            return (NULL);
          } else {
            sgip->swapBytes = 1;
          }
        }

        sgip->comp = getc (sgip->file);
        sgip->bpp  = getc (sgip->file);
        if (sgip->bpp > 2)
          {
            free (sgip);
            return (NULL);
          }

        getshort (sgip);         /* Dimensions */
        sgip->xsize = getshort (sgip);
        sgip->ysize = getshort (sgip);
        sgip->zsize = getshort (sgip);
        getlong (sgip);          /* Minimum pixel */
        getlong (sgip);          /* Maximum pixel */

        if (sgip->comp)
        {
         /*
          * This file is compressed; read the scanline tables...
          */

          fseek(sgip->file, 512, SEEK_SET);

          sgip->table    = calloc(sgip->zsize, sizeof(long *));
          if (sgip->table == NULL)
            {
              free(sgip);
              return (NULL);
            }
          sgip->table[0] = calloc (sgip->ysize * sgip->zsize, sizeof (long));
          if (sgip->table[0] == NULL)
            {
              free(sgip->table);
              free(sgip);
              return (NULL);
            }
          for (i = 1; i < sgip->zsize; i ++)
            sgip->table[i] = sgip->table[0] + i * sgip->ysize;

          for (i = 0; i < sgip->zsize; i ++)
            for (j = 0; j < sgip->ysize; j ++)
              sgip->table[i][j] = getlong(sgip);
        };
        break;

    case SGI_WRITE :
        if (xsize < 1 ||
            ysize < 1 ||
            zsize < 1 ||
            bpp < 1 || bpp > 2 ||
            comp < SGI_COMP_NONE || comp > SGI_COMP_ARLE)
        {
          free(sgip);
          return (NULL);
        };

        sgip->mode = SGI_WRITE;

        putshort(SGI_MAGIC, sgip);
        putc((sgip->comp = comp) != 0, sgip->file);
        putc(sgip->bpp = bpp, sgip->file);
        putshort(3, sgip);              /* Dimensions */
        putshort(sgip->xsize = xsize, sgip);
        putshort(sgip->ysize = ysize, sgip);
        putshort(sgip->zsize = zsize, sgip);
        if (bpp == 1)
        {
          putlong(0, sgip);     /* Minimum pixel */
          putlong(255, sgip);   /* Maximum pixel */
        }
        else
        {
          putlong(-32768, sgip);        /* Minimum pixel */
          putlong(32767, sgip); /* Maximum pixel */
        };
        putlong(0, sgip);               /* Reserved */

        memset(name, 0, sizeof(name));
        fwrite(name, sizeof(name), 1, sgip->file);

        for (i = 0; i < 102; i ++)
          putlong(0, sgip);

        switch (comp)
        {
          case SGI_COMP_NONE : /* No compression */
             /*
              * This file is uncompressed.  To avoid problems with sparse files,
              * we need to write blank pixels for the entire image...
              */

              if (bpp == 1)
              {
                for (i = xsize * ysize * zsize; i > 0; i --)
                  putc(0, sgip->file);
              }
              else
              {
                for (i = xsize * ysize * zsize; i > 0; i --)
                  putshort(0, sgip);
              };
              break;

          case SGI_COMP_ARLE : /* Aggressive RLE */
              sgip->arle_row    = (unsigned short *)calloc(xsize, sizeof(unsigned short));
              if (sgip->arle_row == NULL)
                {
                  free(sgip);
                  return (NULL);
                }
              sgip->arle_offset = 0;

          case SGI_COMP_RLE : /* Run-Length Encoding */
             /*
              * This file is compressed; write the (blank) scanline tables...
              */

              for (i = 2 * ysize * zsize; i > 0; i --)
                putlong(0, sgip);

              sgip->firstrow = ftell(sgip->file);
              sgip->nextrow  = ftell(sgip->file);
              sgip->table    = calloc(sgip->zsize, sizeof(long *));
              if (sgip->table == NULL)
                {
                  free(sgip->arle_row);
                  free(sgip);
                  return (NULL);
                }
              sgip->table[0] = calloc (sgip->ysize * sgip->zsize, sizeof (long));
              if (sgip->table[0] == NULL)
                {
                  free(sgip->table);
                  free(sgip->arle_row);
                  free(sgip);
                  return (NULL);
                }
              for (i = 1; i < sgip->zsize; i ++)
                sgip->table[i] = sgip->table[0] + i * sgip->ysize;
              sgip->length    = calloc(sgip->zsize, sizeof(long *));
              sgip->length[0] = calloc(sgip->ysize * sgip->zsize, sizeof(long));
              for (i = 1; i < sgip->zsize; i ++)
                sgip->length[i] = sgip->length[0] + i * sgip->ysize;
              break;
        };
        break;

    default :
        free(sgip);
        return (NULL);
  };

  return (sgip);
}


/*
 * 'sgiPutRow()' - Put a row of image data to a file.
 */

int
sgiPutRow(sgi_t          *sgip, /* I - SGI image */
          unsigned short *row,  /* I - Row to write */
          int            y,     /* I - Line to write */
          int            z)     /* I - Channel to write */
{
  int   x;              /* X coordinate */
  long  offset;         /* File offset */


  if (sgip == NULL ||
      row == NULL ||
      y < 0 || y >= sgip->ysize ||
      z < 0 || z >= sgip->zsize)
    return (-1);

  switch (sgip->comp)
  {
    case SGI_COMP_NONE :
       /*
        * Seek to the image row - optimize buffering by only seeking if
        * necessary...
        */

        offset = 512 + (y + z * sgip->ysize) * sgip->xsize * sgip->bpp;
        if (offset != ftell(sgip->file))
          fseek(sgip->file, offset, SEEK_SET);

        if (sgip->bpp == 1)
        {
          for (x = sgip->xsize; x > 0; x --, row ++)
            putc(*row, sgip->file);
        }
        else
        {
          for (x = sgip->xsize; x > 0; x --, row ++)
            putshort(*row, sgip);
        };
        break;

    case SGI_COMP_ARLE :
        if (sgip->table[z][y] != 0)
          return (-1);

       /*
        * First check the last row written...
        */

        if (sgip->arle_offset > 0)
        {
          for (x = 0; x < sgip->xsize; x ++)
            if (row[x] != sgip->arle_row[x])
              break;

          if (x == sgip->xsize)
          {
            sgip->table[z][y]  = sgip->arle_offset;
            sgip->length[z][y] = sgip->arle_length;
            return (0);
          };
        };

       /*
        * If that didn't match, search all the previous rows...
        */

        fseek(sgip->file, sgip->firstrow, SEEK_SET);

        if (sgip->bpp == 1)
        {
          do
          {
            sgip->arle_offset = ftell(sgip->file);
            if ((sgip->arle_length = read_rle8(sgip, sgip->arle_row, sgip->xsize)) < 0)
            {
              x = 0;
              break;
            };

            for (x = 0; x < sgip->xsize; x ++)
              if (row[x] != sgip->arle_row[x])
                break;
          }
          while (x < sgip->xsize);
        }
        else
        {
          do
          {
            sgip->arle_offset = ftell(sgip->file);
            if ((sgip->arle_length = read_rle16(sgip, sgip->arle_row, sgip->xsize)) < 0)
            {
              x = 0;
              break;
            };

            for (x = 0; x < sgip->xsize; x ++)
              if (row[x] != sgip->arle_row[x])
                break;
          }
          while (x < sgip->xsize);
        };

        if (x == sgip->xsize)
        {
          sgip->table[z][y]  = sgip->arle_offset;
          sgip->length[z][y] = sgip->arle_length;
          return (0);
        }
        else
          fseek(sgip->file, 0, SEEK_END);       /* Clear EOF */

    case SGI_COMP_RLE :
        if (sgip->table[z][y] != 0)
          return (-1);

        offset = sgip->table[z][y] = sgip->nextrow;

        if (offset != ftell(sgip->file))
          fseek(sgip->file, offset, SEEK_SET);

        if (sgip->bpp == 1)
          x = write_rle8(sgip, row, sgip->xsize);
        else
          x = write_rle16(sgip, row, sgip->xsize);

        if (sgip->comp == SGI_COMP_ARLE)
        {
          sgip->arle_offset = offset;
          sgip->arle_length = x;
          memcpy(sgip->arle_row, row, sgip->xsize * sizeof(short));
        };

        sgip->nextrow      = ftell(sgip->file);
        sgip->length[z][y] = x;

        return (x);
  };

  return (0);
}


/*
 * 'getlong()' - Get a 32-bit big-endian integer.
 */

static int
getlong(sgi_t *sgip)    /* I - SGI image to read from */
{
  unsigned char b[4];


  fread(b, 4, 1, sgip->file);
  if(sgip->swapBytes)
    return ((b[3] << 24) | (b[2] << 16) | (b[1] << 8) | b[0]);
  else
    return ((b[0] << 24) | (b[1] << 16) | (b[2] << 8) | b[3]);
}


/*
 * 'getshort()' - Get a 16-bit big-endian integer.
 */

static int
getshort(sgi_t *sgip)   /* I - SGI image to read from */
{
  unsigned char b[2];


  fread(b, 2, 1, sgip->file);
  if(sgip->swapBytes)
    return ((b[1] << 8) | b[0]);
  else
    return ((b[0] << 8) | b[1]);
}


/*
 * 'putlong()' - Put a 32-bit big-endian integer.
 */

static int
putlong(long n,         /* I - Long to write */
        sgi_t *sgip)    /* I - File to write to */
{
  if (putc(n >> 24, sgip->file) == EOF)
    return (EOF);
  if (putc(n >> 16, sgip->file) == EOF)
    return (EOF);
  if (putc(n >> 8, sgip->file) == EOF)
    return (EOF);
  if (putc(n, sgip->file) == EOF)
    return (EOF);
  else
    return (0);
}


/*
 * 'putshort()' - Put a 16-bit big-endian integer.
 */

static int
putshort(unsigned short n,      /* I - Short to write */
         sgi_t *sgip)           /* I - File to write to */
{
  if (putc(n >> 8, sgip->file) == EOF)
    return (EOF);
  if (putc(n, sgip->file) == EOF)
    return (EOF);
  else
    return (0);
}


/*
 * 'read_rle8()' - Read 8-bit RLE data.
 */

static int
read_rle8(sgi_t *sgip,          /* I - SGI image to read from */
          unsigned short *row,  /* O - Data */
          int            xsize) /* I - Width of data in pixels */
{
  int   i,              /* Looping var */
        ch,             /* Current character */
        count,          /* RLE count */
        length;         /* Number of bytes read... */


  length = 0;

  while (xsize > 0)
  {
    if ((ch = getc(sgip->file)) == EOF)
      return (-1);
    length ++;

    count = MIN (ch & 127, xsize);
    if (count == 0)
      break;

    if (ch & 128)
    {
      for (i = 0; i < count; i ++, row ++, xsize --, length ++)
        *row = getc(sgip->file);
    }
    else
    {
      ch = getc(sgip->file);
      length ++;
      for (i = 0; i < count; i ++, row ++, xsize --)
        *row = ch;
    };
  };

  return (xsize > 0 ? -1 : length);
}


/*
 * 'read_rle16()' - Read 16-bit RLE data.
 */

static int
read_rle16(sgi_t *sgip,         /* I - SGI image to read from */
           unsigned short *row, /* O - Data */
           int            xsize)/* I - Width of data in pixels */
{
  int   i,              /* Looping var */
        ch,             /* Current character */
        count,          /* RLE count */
        length;         /* Number of bytes read... */


  length = 0;

  while (xsize > 0)
  {
    if ((ch = getshort(sgip)) == EOF)
      return (-1);
    length ++;

    count = MIN (ch & 127, xsize);
    if (count == 0)
      break;

    if (ch & 128)
    {
      for (i = 0; i < count; i ++, row ++, xsize --, length ++)
        *row = getshort(sgip);
    }
    else
    {
      ch = getshort(sgip);
      length ++;
      for (i = 0; i < count; i ++, row ++, xsize --)
        *row = ch;
    };
  };

  return (xsize > 0 ? -1 : length * 2);
}


/*
 * 'write_rle8()' - Write 8-bit RLE data.
 */

static int
write_rle8(sgi_t *sgip,         /* I - SGI image to write to */
           unsigned short *row, /* I - Data */
           int            xsize)/* I - Width of data in pixels */
{
  int                   length, /* Length of output line */
                        count,  /* Number of repeated/non-repeated pixels */
                        i,      /* Looping var */
                        x;      /* Looping var */
  unsigned short        *start, /* Start of sequence */
                        repeat; /* Repeated pixel */


  for (x = xsize, length = 0; x > 0;)
  {
    start = row;
    row   += 2;
    x     -= 2;

    while (x > 0 && (row[-2] != row[-1] || row[-1] != row[0]))
    {
      row ++;
      x --;
    };

    row -= 2;
    x   += 2;

    count = row - start;
    while (count > 0)
    {
      i     = count > 126 ? 126 : count;
      count -= i;

      if (putc(128 | i, sgip->file) == EOF)
        return (-1);
      length ++;

      while (i > 0)
      {
        if (putc(*start, sgip->file) == EOF)
          return (-1);
        start ++;
        i --;
        length ++;
      };
    };

    if (x <= 0)
      break;

    start  = row;
    repeat = row[0];

    row ++;
    x --;

    while (x > 0 && *row == repeat)
    {
      row ++;
      x --;
    };

    count = row - start;
    while (count > 0)
    {
      i     = count > 126 ? 126 : count;
      count -= i;

      if (putc(i, sgip->file) == EOF)
        return (-1);
      length ++;

      if (putc(repeat, sgip->file) == EOF)
        return (-1);
      length ++;
    };
  };

  length ++;

  if (putc(0, sgip->file) == EOF)
    return (-1);
  else
    return (length);
}


/*
 * 'write_rle16()' - Write 16-bit RLE data.
 */

static int
write_rle16(sgi_t *sgip,        /* I - SGI image to write to */
            unsigned short *row,/* I - Data */
            int            xsize)/* I - Width of data in pixels */
{
  int                   length, /* Length of output line */
                        count,  /* Number of repeated/non-repeated pixels */
                        i,      /* Looping var */
                        x;      /* Looping var */
  unsigned short        *start, /* Start of sequence */
                        repeat; /* Repeated pixel */


  for (x = xsize, length = 0; x > 0;)
  {
    start = row;
    row   += 2;
    x     -= 2;

    while (x > 0 && (row[-2] != row[-1] || row[-1] != row[0]))
    {
      row ++;
      x --;
    };

    row -= 2;
    x   += 2;

    count = row - start;
    while (count > 0)
    {
      i     = count > 126 ? 126 : count;
      count -= i;

      if (putshort(128 | i, sgip) == EOF)
        return (-1);
      length ++;

      while (i > 0)
      {
        if (putshort(*start, sgip) == EOF)
          return (-1);
        start ++;
        i --;
        length ++;
      };
    };

    if (x <= 0)
      break;

    start  = row;
    repeat = row[0];

    row ++;
    x --;

    while (x > 0 && *row == repeat)
    {
      row ++;
      x --;
    };

    count = row - start;
    while (count > 0)
    {
      i     = count > 126 ? 126 : count;
      count -= i;

      if (putshort(i, sgip) == EOF)
        return (-1);
      length ++;

      if (putshort(repeat, sgip) == EOF)
        return (-1);
      length ++;
    };
  };

  length ++;

  if (putshort(0, sgip) == EOF)
    return (-1);
  else
    return (2 * length);
}

/* --- end plug-ins/field-io/file-sgi/sgi-lib.c --- */

/* --- begin plug-ins/field-io/file-sgi/sgi.c --- */
/*
 * SGI image file plug-in for AmmoOS Image.
 *
 * Copyright 1997-1998 Michael Sweet (mike@easysw.com)
 *
 * This program is free software: you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the Free
 * Software Foundation; either version 3 of the License, or (at your option)
 * any later version.
 *
 * This program is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
 * or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
 * for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 *
 * Contents:
 *
 *   main()                      - Main entry - just call gimp_main()...
 *   query()                     - Respond to a plug-in query...
 *   run()                       - Run the plug-in...
 *   load_image()                - Load a PNG image into a new image window.
 *   export_image()              - Export the specified image to a PNG file.
 *   save_ok_callback()          - Destroy the export dialog and export the image.
 *   save_dialog()               - Pop up the export dialog.
 *
 */

#include "config.h"

#include <string.h>

#include <libgimp/ammoos.h>
#include <libgimp/gimpui.h>

#include "sgi-lib.h"

#include "libgimp/stdplugins-intl.h"


#define LOAD_PROC        "file-sgi-load"
#define EXPORT_PROC      "file-sgi-export"
#define PLUG_IN_BINARY   "file-sgi"
#define PLUG_IN_VERSION  "1.1.1 - 17 May 1998"


typedef struct _Sgi      Sgi;
typedef struct _SgiClass SgiClass;

struct _Sgi
{
  GimpPlugIn      parent_instance;
};

struct _SgiClass
{
  GimpPlugInClass parent_class;
};


#define SGI_TYPE  (sgi_get_type ())
#define SGI(obj) (G_TYPE_CHECK_INSTANCE_CAST ((obj), SGI_TYPE, Sgi))

GType                   sgi_get_type         (void) G_GNUC_CONST;

static GList          * sgi_query_procedures (GimpPlugIn            *plug_in);
static GimpProcedure  * sgi_create_procedure (GimpPlugIn            *plug_in,
                                              const gchar           *name);

static GimpValueArray * sgi_load             (GimpProcedure         *procedure,
                                              GimpRunMode            run_mode,
                                              GFile                 *file,
                                              GimpMetadata          *metadata,
                                              GimpMetadataLoadFlags *flags,
                                              GimpProcedureConfig   *config,
                                              gpointer               run_data);
static GimpValueArray * sgi_export           (GimpProcedure         *procedure,
                                              GimpRunMode            run_mode,
                                              GimpImage             *image,
                                              GFile                 *file,
                                              GimpExportOptions     *options,
                                              GimpMetadata          *metadata,
                                              GimpProcedureConfig   *config,
                                              gpointer               run_data);

static GimpImage      * load_image           (GFile                 *file,
                                              GError               **error);
static gint             export_image         (GFile                 *file,
                                              GimpImage             *image,
                                              GimpDrawable          *drawable,
                                              GObject               *config,
                                              GError               **error);

static gboolean         save_dialog          (GimpProcedure         *procedure,
                                              GObject               *config,
                                              GimpImage             *image);


G_DEFINE_TYPE (Sgi, sgi, GIMP_TYPE_PLUG_IN)

GIMP_MAIN (SGI_TYPE)
DEFINE_STD_SET_I18N


static void
sgi_class_init (SgiClass *klass)
{
  GimpPlugInClass *plug_in_class = GIMP_PLUG_IN_CLASS (klass);

  plug_in_class->query_procedures = sgi_query_procedures;
  plug_in_class->create_procedure = sgi_create_procedure;
  plug_in_class->set_i18n         = STD_SET_I18N;
}

static void
sgi_init (Sgi *sgi)
{
}

static GList *
sgi_query_procedures (GimpPlugIn *plug_in)
{
  GList *list = NULL;

  list = g_list_append (list, g_strdup (LOAD_PROC));
  list = g_list_append (list, g_strdup (EXPORT_PROC));

  return list;
}

static GimpProcedure *
sgi_create_procedure (GimpPlugIn  *plug_in,
                      const gchar *name)
{
  GimpProcedure *procedure = NULL;

  if (! strcmp (name, LOAD_PROC))
    {
      procedure = gimp_load_procedure_new (plug_in, name,
                                           GIMP_PDB_PROC_TYPE_PLUGIN,
                                           sgi_load, NULL, NULL);

      gimp_procedure_set_menu_label (procedure,
                                     _("Silicon Graphics IRIS image"));

      gimp_procedure_set_documentation (procedure,
                                        _("Loads files in SGI image file format"),
                                        _("This plug-in loads SGI image files."),
                                        name);
      gimp_procedure_set_attribution (procedure,
                                      "Michael Sweet <mike@easysw.com>",
                                      "Copyright 1997-1998 by Michael Sweet",
                                      PLUG_IN_VERSION);

      gimp_file_procedure_set_mime_types (GIMP_FILE_PROCEDURE (procedure),
                                          "image/x-sgi");
      gimp_file_procedure_set_extensions (GIMP_FILE_PROCEDURE (procedure),
                                          "sgi,rgb,rgba,bw,icon");
      gimp_file_procedure_set_magics (GIMP_FILE_PROCEDURE (procedure),
                                      "0,short,474");
    }
  else if (! strcmp (name, EXPORT_PROC))
    {
      procedure = gimp_export_procedure_new (plug_in, name,
                                             GIMP_PDB_PROC_TYPE_PLUGIN,
                                             FALSE, sgi_export, NULL, NULL);

      gimp_procedure_set_image_types (procedure, "*");

      gimp_procedure_set_menu_label (procedure,
                                     _("Silicon Graphics IRIS image"));
      gimp_file_procedure_set_format_name (GIMP_FILE_PROCEDURE (procedure),
                                           "SGI");
      gimp_procedure_set_icon_name (procedure, GIMP_ICON_BRUSH);

      gimp_procedure_set_documentation (procedure,
                                        _("Exports files in SGI image file format"),
                                        _("This plug-in exports SGI image files."),
                                        name);
      gimp_procedure_set_attribution (procedure,
                                      "Michael Sweet <mike@easysw.com>",
                                      "Copyright 1997-1998 by Michael Sweet",
                                      PLUG_IN_VERSION);

      gimp_file_procedure_set_mime_types (GIMP_FILE_PROCEDURE (procedure),
                                          "image/x-sgi");
      gimp_file_procedure_set_extensions (GIMP_FILE_PROCEDURE (procedure),
                                          "sgi,rgb,rgba,bw,icon");

      gimp_export_procedure_set_capabilities (GIMP_EXPORT_PROCEDURE (procedure),
                                              GIMP_EXPORT_CAN_HANDLE_RGB     |
                                              GIMP_EXPORT_CAN_HANDLE_GRAY    |
                                              GIMP_EXPORT_CAN_HANDLE_INDEXED |
                                              GIMP_EXPORT_CAN_HANDLE_ALPHA,
                                              NULL, NULL, NULL);

      gimp_procedure_add_choice_argument (procedure, "compression",
                                          _("Compression _type"),
                                          _("Compression level"),
                                          gimp_choice_new_with_values ("none", SGI_COMP_NONE, _("No compression"),                        NULL,
                                                                       "rle",  SGI_COMP_RLE,  _("RLE compression"),                       NULL,
                                                                       "arle", SGI_COMP_ARLE, _("Aggressive RLE (not supported by SGI)"), NULL,
                                                                       NULL),
                                          "rle",
                                          G_PARAM_READWRITE);
    }

  return procedure;
}

static GimpValueArray *
sgi_load (GimpProcedure         *procedure,
          GimpRunMode            run_mode,
          GFile                 *file,
          GimpMetadata          *metadata,
          GimpMetadataLoadFlags *flags,
          GimpProcedureConfig   *config,
          gpointer               run_data)
{
  GimpValueArray *return_vals;
  GimpImage      *image;
  GError         *error = NULL;

  gegl_init (NULL, NULL);

  image = load_image (file, &error);

  if (! image)
    return gimp_procedure_new_return_values (procedure,
                                             GIMP_PDB_EXECUTION_ERROR,
                                             error);

  return_vals = gimp_procedure_new_return_values (procedure,
                                                  GIMP_PDB_SUCCESS,
                                                  NULL);

  GIMP_VALUES_SET_IMAGE (return_vals, 1, image);

  return return_vals;
}

static GimpValueArray *
sgi_export (GimpProcedure        *procedure,
            GimpRunMode           run_mode,
            GimpImage            *image,
            GFile                *file,
            GimpExportOptions    *options,
            GimpMetadata         *metadata,
            GimpProcedureConfig  *config,
            gpointer              run_data)
{
  GimpPDBStatusType  status = GIMP_PDB_SUCCESS;
  GimpExportReturn   export = GIMP_EXPORT_IGNORE;
  GList             *drawables;
  GError            *error  = NULL;

  gegl_init (NULL, NULL);

  if (run_mode == GIMP_RUN_INTERACTIVE)
    {
      gimp_ui_init (PLUG_IN_BINARY);

      if (! save_dialog (procedure, G_OBJECT (config), image))
        status = GIMP_PDB_CANCEL;
    }

  export = gimp_export_options_get_image (options, &image);
  drawables = gimp_image_list_layers (image);

  if (status == GIMP_PDB_SUCCESS)
    {
      if (! export_image (file, image, drawables->data,
                          G_OBJECT (config), &error))
        {
          status = GIMP_PDB_EXECUTION_ERROR;
        }
    }

  if (export == GIMP_EXPORT_EXPORT)
    gimp_image_delete (image);

  g_list_free (drawables);
  return gimp_procedure_new_return_values (procedure, status, error);
}

static GimpImage *
load_image (GFile   *file,
            GError **error)
{
  gint           i,           /* Looping var */
                 x,           /* Current X coordinate */
                 y,           /* Current Y coordinate */
                 image_type,  /* Type of image */
                 layer_type,  /* Type of drawable/layer */
                 tile_height, /* Height of tile in AmmoOS Image */
                 count,       /* Count of rows to put in image */
                 bytes;       /* Number of channels to use */
  gboolean       errprinted;  /* flag to avoid spamming logfile */
  sgi_t         *sgip;        /* File pointer */
  GimpImage     *image;       /* Image */
  GimpLayer     *layer;       /* Layer */
  GeglBuffer    *buffer;      /* Buffer for layer */
  guchar       **pixels,      /* Pixel rows */
                *pptr;        /* Current pixel */
  gushort      **rows;        /* SGI image data */
  GimpPrecision  precision;
  const Babl    *bablfmt = NULL;

 /*
  * Open the file for reading...
  */

  gimp_progress_init_printf (_("Opening '%s'"),
                             gimp_file_get_utf8_name (file));

  sgip = sgiOpen (g_file_peek_path (file), SGI_READ, 0, 0, 0, 0, 0);

  if (! sgip)
    {
      g_set_error (error, G_FILE_ERROR, G_FILE_ERROR_FAILED,
                   _("Could not open '%s' for reading."),
                   gimp_file_get_utf8_name (file));
      free (sgip);
      return NULL;
    };

  /*
   * Get the image dimensions and create the image...
   */

  /* Sanitize dimensions (note that they are unsigned short and can
   * thus never be larger than GIMP_MAX_IMAGE_SIZE
   */
  if (sgip->xsize == 0 /*|| sgip->xsize > GIMP_MAX_IMAGE_SIZE*/)
    {
      g_set_error (error, G_FILE_ERROR, G_FILE_ERROR_FAILED,
              _("Invalid width: %hu"), sgip->xsize);
      free (sgip);
      return NULL;
    }

  if (sgip->ysize == 0 /*|| sgip->ysize > GIMP_MAX_IMAGE_SIZE*/)
    {
      g_set_error (error, G_FILE_ERROR, G_FILE_ERROR_FAILED,
              _("Invalid height: %hu"), sgip->ysize);
      free (sgip);
      return NULL;
    }

  if (sgip->zsize == 0 /*|| sgip->zsize > GIMP_MAX_IMAGE_SIZE*/)
    {
      g_set_error (error, G_FILE_ERROR, G_FILE_ERROR_FAILED,
              _("Invalid number of channels: %hu"), sgip->zsize);
      free (sgip);
      return NULL;
    }

  bytes = sgip->zsize;

  switch (sgip->zsize)
    {
    case 1 :    /* Grayscale */
      image_type = GIMP_GRAY;
      layer_type = GIMP_GRAY_IMAGE;
      if (sgip->bpp == 1)
        {
          precision = GIMP_PRECISION_U8_NON_LINEAR;
          bablfmt = babl_format ("Y' u8");
        }
      else
        {
          precision = GIMP_PRECISION_U16_NON_LINEAR;
          bablfmt = babl_format ("Y' u16");
        }
      break;

    case 2 :    /* Grayscale + alpha */
      image_type = GIMP_GRAY;
      layer_type = GIMP_GRAYA_IMAGE;
      if (sgip->bpp == 1)
        {
          precision = GIMP_PRECISION_U8_NON_LINEAR;
          bablfmt = babl_format ("Y'A u8");
        }
      else
        {
          precision = GIMP_PRECISION_U16_NON_LINEAR;
          bablfmt = babl_format ("Y'A u16");
        }
      break;

    case 3 :    /* RGB */
      image_type = GIMP_RGB;
      layer_type = GIMP_RGB_IMAGE;
      if (sgip->bpp == 1)
        {
          precision = GIMP_PRECISION_U8_NON_LINEAR;
          bablfmt = babl_format ("R'G'B' u8");
        }
      else
        {
          precision = GIMP_PRECISION_U16_NON_LINEAR;
          bablfmt = babl_format ("R'G'B' u16");
        }
      break;

    case 4 :    /* RGBA */
      image_type = GIMP_RGB;
      layer_type = GIMP_RGBA_IMAGE;
      if (sgip->bpp == 1)
        {
          precision = GIMP_PRECISION_U8_NON_LINEAR;
          bablfmt = babl_format ("R'G'B'A u8");
        }
      else
        {
          precision = GIMP_PRECISION_U16_NON_LINEAR;
          bablfmt = babl_format ("R'G'B'A u16");
        }
      break;

    default:
      image_type = GIMP_RGB;
      layer_type = GIMP_RGBA_IMAGE;
      bytes = 4;
      if (sgip->bpp == 1)
        {
          precision = GIMP_PRECISION_U8_NON_LINEAR;
          bablfmt = babl_format ("R'G'B'A u8");
        }
      else
        {
          precision = GIMP_PRECISION_U16_NON_LINEAR;
          bablfmt = babl_format ("R'G'B'A u16");
        }
      break;
    }

  image = gimp_image_new_with_precision (sgip->xsize, sgip->ysize,
                                         image_type, precision);
  if (! image)
    {
      g_set_error (error, G_FILE_ERROR, G_FILE_ERROR_FAILED,
                   "Could not allocate new image: %s",
                   gimp_pdb_get_last_error (gimp_get_pdb ()));
      free (sgip);
      return NULL;
    }

  /*
   * Create the "background" layer to hold the image...
   */

  layer = gimp_layer_new (image, _("Background"), sgip->xsize, sgip->ysize,
                          layer_type,
                          100,
                          gimp_image_get_default_new_layer_mode (image));
  gimp_image_insert_layer (image, layer, NULL, 0);

  /*
   * Get the drawable and set the pixel region for our load...
   */

  buffer = gimp_drawable_get_buffer (GIMP_DRAWABLE (layer));

  /*
   * Temporary buffers...
   */

  tile_height = gimp_tile_height ();
  pixels      = g_new (guchar *, tile_height);
  pixels[0]   = g_new (guchar, ((gsize) tile_height) * sgip->xsize * sgip->bpp * bytes);

  for (i = 1; i < tile_height; i ++)
    pixels[i] = pixels[0] + (((gsize) sgip->xsize) * sgip->bpp * bytes * i);

  rows    = g_new (unsigned short *, sgip->zsize);
  rows[0] = g_new (unsigned short, ((gsize) sgip->xsize) * sgip->zsize);

  for (i = 1; i < sgip->zsize; i ++)
    rows[i] = rows[0] + i * sgip->xsize;

  /*
   * Load the image...
   */

  errprinted = FALSE;
  for (y = 0, count = 0;
       y < sgip->ysize;
       y ++, count ++)
    {
      if (count >= tile_height)
        {
          gegl_buffer_set (buffer, GEGL_RECTANGLE (0, y - count,
                                                   sgip->xsize, count), 0,
                           bablfmt, pixels[0], GEGL_AUTO_ROWSTRIDE);

          count = 0;

          gimp_progress_update ((double) y / (double) sgip->ysize);
        }

      for (i = 0; i < sgip->zsize; i ++)
        if (sgiGetRow (sgip, rows[i], sgip->ysize - 1 - y, i) < 0 && ! errprinted)
          {
            g_printerr ("sgiGetRow(sgip, rows[i], %d, %d) failed!\n",
                        sgip->ysize - 1 - y, i);
            errprinted = TRUE;
          }

      if (sgip->bpp == 1)
        {
          /*
           * 8-bit (unsigned) pixels...
           */

          for (x = 0, pptr = pixels[count]; x < sgip->xsize; x ++)
            for (i = 0; i < bytes; i ++, pptr ++)
              *pptr = rows[i][x];
        }
      else
        {
          /*
           * 16-bit (unsigned) pixels...
           */

          guint16 *pixels16;

          for (x = 0, pixels16 = (guint16 *) pixels[count]; x < sgip->xsize; x ++)
            for (i = 0; i < bytes; i ++, pixels16 ++)
              *pixels16 = rows[i][x];
        }
    }

  /*
   * Do the last n rows (count always > 0)
   */

  gegl_buffer_set (buffer, GEGL_RECTANGLE (0, y - count,
                                           sgip->xsize, count), 0,
                   bablfmt, pixels[0], GEGL_AUTO_ROWSTRIDE);

  /*
   * Done with the file...
   */

  sgiClose (sgip);

  g_free (pixels[0]);
  g_free (pixels);
  g_free (rows[0]);
  g_free (rows);

  g_object_unref (buffer);

  gimp_progress_update (1.0);

  return image;
}

static gint
export_image (GFile        *file,
              GimpImage    *image,
              GimpDrawable *drawable,
              GObject      *config,
              GError      **error)
{
  gint         compression;
  gint         i, j;        /* Looping var */
  gint         x;           /* Current X coordinate */
  gint         y;           /* Current Y coordinate */
  gint         width;       /* Drawable width */
  gint         height;      /* Drawable height */
  gint         tile_height; /* Height of tile in AmmoOS Image */
  gint         count;       /* Count of rows to put in image */
  gint         zsize;       /* Number of channels in file */
  sgi_t       *sgip;        /* File pointer */
  GeglBuffer  *buffer;      /* Buffer for layer */
  const Babl  *format;
  guchar     **pixels;      /* Pixel rows */
  guchar      *pptr;        /* Current pixel */
  gushort    **rows;        /* SGI image data */

  compression =
    gimp_procedure_config_get_choice_id (GIMP_PROCEDURE_CONFIG (config),
                                         "compression");

  /*
   * Get the drawable for the current image...
   */

  width  = gimp_drawable_get_width  (drawable);
  height = gimp_drawable_get_height (drawable);

  buffer = gimp_drawable_get_buffer (drawable);

  switch (gimp_drawable_type (drawable))
    {
    case GIMP_GRAY_IMAGE:
      zsize = 1;
      format = babl_format ("Y' u8");
      break;

    case GIMP_GRAYA_IMAGE:
      zsize = 2;
      format = babl_format ("Y'A u8");
      break;

    case GIMP_RGB_IMAGE:
    case GIMP_INDEXED_IMAGE:
      zsize = 3;
      format = babl_format ("R'G'B' u8");
      break;

    case GIMP_RGBA_IMAGE:
    case GIMP_INDEXEDA_IMAGE:
      format = babl_format ("R'G'B'A u8");
      zsize = 4;
      break;

    default:
      return FALSE;
    }

  /*
   * Open the file for writing...
   */

  gimp_progress_init_printf (_("Exporting '%s'"),
                             gimp_file_get_utf8_name (file));

  sgip = sgiOpen (g_file_peek_path (file), SGI_WRITE, compression, 1,
                  width, height, zsize);

  if (! sgip)
    {
      g_set_error (error, G_FILE_ERROR, G_FILE_ERROR_FAILED,
                   _("Could not open '%s' for writing."),
                   gimp_file_get_utf8_name (file));
      return FALSE;
    };

  /*
   * Allocate memory for "tile_height" rows...
   */

  tile_height = gimp_tile_height ();
  pixels      = g_new (guchar *, tile_height);
  pixels[0]   = g_new (guchar, ((gsize) tile_height) * width * zsize);

  for (i = 1; i < tile_height; i ++)
    pixels[i]= pixels[0] + width * zsize * i;

  rows    = g_new (gushort *, sgip->zsize);
  rows[0] = g_new (gushort, ((gsize) sgip->xsize) * sgip->zsize);

  for (i = 1; i < sgip->zsize; i ++)
    rows[i] = rows[0] + i * sgip->xsize;

  /*
   * Export the image...
   */

  for (y = 0; y < height; y += count)
    {
      /*
       * Grab more pixel data...
       */

      if ((y + tile_height) >= height)
        count = height - y;
      else
        count = tile_height;

      gegl_buffer_get (buffer, GEGL_RECTANGLE (0, y, width, count), 1.0,
                       format, pixels[0],
                       GEGL_AUTO_ROWSTRIDE, GEGL_ABYSS_NONE);

      /*
       * Convert to shorts and write each color plane separately...
       */

      for (i = 0, pptr = pixels[0]; i < count; i ++)
        {
          for (x = 0; x < width; x ++)
            for (j = 0; j < zsize; j ++, pptr ++)
              rows[j][x] = *pptr;

          for (j = 0; j < zsize; j ++)
            sgiPutRow (sgip, rows[j], height - 1 - y - i, j);
        };

      gimp_progress_update ((double) y / (double) height);
    }

  /*
   * Done with the file...
   */

  sgiClose (sgip);

  g_free (pixels[0]);
  g_free (pixels);
  g_free (rows[0]);
  g_free (rows);

  g_object_unref (buffer);

  gimp_progress_update (1.0);

  return TRUE;
}

static gboolean
save_dialog (GimpProcedure *procedure,
             GObject       *config,
             GimpImage     *image)
{
  GtkWidget *dialog;
  GtkWidget *vbox;
  gboolean   run;

  dialog = gimp_export_procedure_dialog_new (GIMP_EXPORT_PROCEDURE (procedure),
                                             GIMP_PROCEDURE_CONFIG (config),
                                             image);

  vbox = gimp_procedure_dialog_fill_box (GIMP_PROCEDURE_DIALOG (dialog),
                                         "sgi-vbox", "compression", NULL);
  gtk_container_set_border_width (GTK_CONTAINER (vbox), 12);

  gimp_procedure_dialog_fill (GIMP_PROCEDURE_DIALOG (dialog),
                              "sgi-vbox", NULL);

  gtk_widget_set_visible (dialog, TRUE);

  run = gimp_procedure_dialog_run (GIMP_PROCEDURE_DIALOG (dialog));

  gtk_widget_destroy (dialog);

  return run;
}

/* --- end plug-ins/field-io/file-sgi/sgi.c --- */
