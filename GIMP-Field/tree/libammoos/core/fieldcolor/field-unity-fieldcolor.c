/* AmmoOS Image — field research rewrite (G16 field_opt).
 * RTX-gated paths: see GIMP-Field/data/rtx-gated-content.json
 * OS brand: AmmoOS · product: AmmoOS Image 1.0
 */
/* AmmoOS amalgamation — field-unity-fieldcolor.c — g16 field_opt unity bundle */
#define FIELD_AMMOOS_G16_OPT 1
#define FIELD_AMMOOS_UNITY 1

/* --- begin libammoos/core/fieldcolor/gimpadaptivesupersample.c --- */
/* LIBGIMP - The AmmoOS Image Library
 * Copyright (C) 1995-1997 Peter Mattis and Spencer Kimball
 *
 * This library is free software: you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 3 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Library General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library.  If not, see
 * <https://www.gnu.org/licenses/>.
 */

#include "config.h"

#include <gegl.h>
#include <glib-object.h>

#include "libgimpmath/gimpmath.h"

#include "gimpcolortypes.h"

#include "gimpadaptivesupersample.h"


/**
 * SECTION: gimpadaptivesupersample
 * @title: GimpAdaptiveSupersample
 * @short_description: Functions to perform adaptive supersampling on
 *                     an area.
 *
 * Functions to perform adaptive supersampling on an area.
 **/


/*********************************************************************/
/* Sumpersampling code (Quartic)                                     */
/* This code is *largely* based on the sources for POV-Ray 3.0. I am */
/* grateful to the POV-Team for such a great program and for making  */
/* their sources available.  All comments / bug reports /            */
/* etc. regarding this code should be addressed to me, not to the    */
/* POV-Ray team.  Any bugs are my responsibility, not theirs.        */
/*********************************************************************/


typedef struct _GimpSampleType GimpSampleType;

struct _GimpSampleType
{
  guchar  ready;
  gdouble color[4];
};

static gdouble
gimp_rgba_distance_legacy (gdouble *rgba1,
                           gdouble *rgba2)
{
  g_return_val_if_fail (rgba1 != NULL, 0.0);
  g_return_val_if_fail (rgba2 != NULL, 0.0);

  return (fabs (rgba1[0] - rgba2[0]) +
          fabs (rgba1[1] - rgba2[1]) +
          fabs (rgba1[2] - rgba2[2]) +
          fabs (rgba1[3] - rgba2[3]));
}

static gulong
gimp_render_sub_pixel (gint             max_depth,
                       gint             depth,
                       GimpSampleType **block,
                       gint             x,
                       gint             y,
                       gint             x1,
                       gint             y1,
                       gint             x3,
                       gint             y3,
                       gdouble          threshold,
                       gint             sub_pixel_size,
                       gdouble         *color,
                       GimpRenderFunc   render_func,
                       gpointer         render_data)
{
  gint     x2, y2;                     /* Coords of center sample */
  gdouble  dx1, dy1;                   /* Delta to upper left sample */
  gdouble  dx3, dy3;                   /* Delta to lower right sample */
  gdouble  c0[4], c1[4], c2[4], c3[4]; /* Sample colors */
  gulong   num_samples = 0;

  g_return_val_if_fail (render_func != NULL, 0);

  /* Get offsets for corners */

  dx1 = (gdouble) (x1 - sub_pixel_size / 2) / sub_pixel_size;
  dx3 = (gdouble) (x3 - sub_pixel_size / 2) / sub_pixel_size;

  dy1 = (gdouble) (y1 - sub_pixel_size / 2) / sub_pixel_size;
  dy3 = (gdouble) (y3 - sub_pixel_size / 2) / sub_pixel_size;

  /* Render upper left sample */

  if (! block[y1][x1].ready)
    {
      num_samples++;

      render_func (x + dx1, y + dy1, c0, render_data);

      block[y1][x1].ready = TRUE;
      for (gint i = 0; i < 4; i++)
        block[y1][x1].color[i] = c0[i];
    }
  else
    {
      for (gint i = 0; i < 4; i++)
        c0[i] = block[y1][x1].color[i];
    }

  /* Render upper right sample */

  if (! block[y1][x3].ready)
    {
      num_samples++;

      render_func (x + dx3, y + dy1, c1, render_data);

      block[y1][x3].ready = TRUE;
      for (gint i = 0; i < 4; i++)
        block[y1][x3].color[i] = c1[i];
    }
  else
    {
      for (gint i = 0; i < 4; i++)
        c1[i] = block[y1][x3].color[i];
    }

  /* Render lower left sample */

  if (! block[y3][x1].ready)
    {
      num_samples++;

      render_func (x + dx1, y + dy3, c2, render_data);

      block[y3][x1].ready = TRUE;
      for (gint i = 0; i < 4; i++)
        block[y3][x1].color[i] = c2[i];
    }
  else
    {
      for (gint i = 0; i < 4; i++)
        c2[i] = block[y3][x1].color[i];
    }

  /* Render lower right sample */

  if (! block[y3][x3].ready)
    {
      num_samples++;

      render_func (x + dx3, y + dy3, c3, render_data);

      block[y3][x3].ready = TRUE;
      for (gint i = 0; i < 4; i++)
        block[y3][x3].color[i] = c3[i];
    }
  else
    {
      for (gint i = 0; i < 4; i++)
        c3[i] = block[y3][x3].color[i];
    }

  /* Check for supersampling */

  if (depth <= max_depth)
    {
      /* Check whether we have to supersample */

      if ((gimp_rgba_distance_legacy (c0, c1) >= threshold) ||
          (gimp_rgba_distance_legacy (c0, c2) >= threshold) ||
          (gimp_rgba_distance_legacy (c0, c3) >= threshold) ||
          (gimp_rgba_distance_legacy (c1, c2) >= threshold) ||
          (gimp_rgba_distance_legacy (c1, c3) >= threshold) ||
          (gimp_rgba_distance_legacy (c2, c3) >= threshold))
        {
          /* Calc coordinates of center subsample */

          x2 = (x1 + x3) / 2;
          y2 = (y1 + y3) / 2;

          /* Render sub-blocks */

          num_samples += gimp_render_sub_pixel (max_depth, depth + 1, block,
                                                x, y, x1, y1, x2, y2,
                                                threshold, sub_pixel_size,
                                                c0,
                                                render_func, render_data);

          num_samples += gimp_render_sub_pixel (max_depth, depth + 1, block,
                                                x, y, x2, y1, x3, y2,
                                                threshold, sub_pixel_size,
                                                c1,
                                                render_func, render_data);

          num_samples += gimp_render_sub_pixel (max_depth, depth + 1, block,
                                                x, y, x1, y2, x2, y3,
                                                threshold, sub_pixel_size,
                                                c2,
                                                render_func, render_data);

          num_samples += gimp_render_sub_pixel (max_depth, depth + 1, block,
                                                x, y, x2, y2, x3, y3,
                                                threshold, sub_pixel_size,
                                                c3,
                                                render_func, render_data);
        }
    }

  if (c0[3] == 0.0 || c1[3] == 0.0 || c2[3] == 0.0 || c3[3] == 0.0)
    {
      gdouble tmpcol[3] = { 0.0, 0.0, 0.0 };
      gdouble weight;

      weight = 2.0;

      if (c0[3] != 0.0)
        {
          tmpcol[0] += c0[0];
          tmpcol[1] += c0[1];
          tmpcol[2] += c0[2];

          weight /= 2.0;
        }
      if (c1[3] != 0.0)
        {
          tmpcol[0] += c1[0];
          tmpcol[1] += c1[1];
          tmpcol[2] += c1[2];

          weight /= 2.0;
        }
      if (c2[3] != 0.0)
        {
          tmpcol[0] += c2[0];
          tmpcol[1] += c2[1];
          tmpcol[2] += c2[2];

          weight /= 2.0;
        }
      if (c3[3] != 0.0)
        {
          tmpcol[0] += c3[0];
          tmpcol[1] += c3[1];
          tmpcol[2] += c3[2];

          weight /= 2.0;
        }

      color[0] = weight * tmpcol[0];
      color[1] = weight * tmpcol[1];
      color[2] = weight * tmpcol[2];
    }
  else
    {
      color[0] = 0.25 * (c0[0] + c1[0] + c2[0] + c3[0]);
      color[1] = 0.25 * (c0[1] + c1[1] + c2[1] + c3[1]);
      color[2] = 0.25 * (c0[2] + c1[2] + c2[2] + c3[2]);
    }

  color[3] = 0.25 * (c0[3] + c1[3] + c2[3] + c3[3]);

  return num_samples;
}

/**
 * gimp_adaptive_supersample_area:
 * @x1:             left x coordinate of the area to process.
 * @y1:             top y coordinate of the area to process.
 * @x2:             right x coordinate of the area to process.
 * @y2:             bottom y coordinate of the area to process.
 * @max_depth:      maximum depth of supersampling.
 * @threshold:      lower threshold of pixel difference that stops
 *                  supersampling.
 * @render_func:    (scope call): function calculate the color value at
 *                  given  coordinates.
 * @render_data:    user data passed to @render_func.
 * @put_pixel_func: (scope call): function to a pixels to a color at
 *                  given coordinates.
 * @put_pixel_data: user data passed to @put_pixel_func.
 * @progress_func:  (scope call): function to report progress.
 * @progress_data:  user data passed to @progress_func.
 *
 * Returns: the number of pixels processed.
 **/
gulong
gimp_adaptive_supersample_area (gint              x1,
                                gint              y1,
                                gint              x2,
                                gint              y2,
                                gint              max_depth,
                                gdouble           threshold,
                                GimpRenderFunc    render_func,
                                gpointer          render_data,
                                GimpPutPixelFunc  put_pixel_func,
                                gpointer          put_pixel_data,
                                GimpProgressFunc  progress_func,
                                gpointer          progress_data)
{
  gint             x, y, width;                 /* Counters, width of region */
  gint             xt, xtt, yt;                 /* Temporary counters */
  gint             sub_pixel_size;              /* Number of samples per pixel (1D) */
  gdouble          color[4];                    /* Rendered pixel's color */
  GimpSampleType   tmp_sample;                  /* For swapping samples */
  GimpSampleType  *top_row, *bot_row, *tmp_row; /* Sample rows */
  GimpSampleType **block;                       /* Sample block matrix */
  gulong           num_samples;

  g_return_val_if_fail (render_func != NULL, 0);
  g_return_val_if_fail (put_pixel_func != NULL, 0);

  /* Initialize color */

  for (gint i = 0; i < 4; i++)
    color[i] = 0.0;

  /* Calculate sub-pixel size */

  sub_pixel_size = 1 << max_depth;

  /* Create row arrays */

  width = x2 - x1 + 1;

  top_row = gegl_scratch_new (GimpSampleType, sub_pixel_size * width + 1);
  bot_row = gegl_scratch_new (GimpSampleType, sub_pixel_size * width + 1);

  for (x = 0; x < (sub_pixel_size * width + 1); x++)
    {
      top_row[x].ready = FALSE;
      bot_row[x].ready = FALSE;

      for (gint i = 0; i < 4; i++)
        {
          top_row[x].color[i] = 0.0;
          bot_row[x].color[i] = 0.0;
        }
    }

  /* Allocate block matrix */

  block = gegl_scratch_new (GimpSampleType *, sub_pixel_size + 1); /* Rows */

  for (y = 0; y < (sub_pixel_size + 1); y++)
    {
      block[y] = gegl_scratch_new (GimpSampleType, sub_pixel_size + 1); /* Columns */

      for (x = 0; x < (sub_pixel_size + 1); x++)
        {
          block[y][x].ready = FALSE;

          for (gint i = 0; i < 4; i++)
            block[y][x].color[i] = 0.0;
        }
    }

  /* Render region */

  num_samples = 0;

  for (y = y1; y <= y2; y++)
    {
      /* Clear the bottom row */

      for (xt = 0; xt < (sub_pixel_size * width + 1); xt++)
        bot_row[xt].ready = FALSE;

      /* Clear first column */

      for (yt = 0; yt < (sub_pixel_size + 1); yt++)
        block[yt][0].ready = FALSE;

      /* Render row */

      for (x = x1; x <= x2; x++)
        {
          /* Initialize block by clearing all but first row/column */

          for (yt = 1; yt < (sub_pixel_size + 1); yt++)
            for (xt = 1; xt < (sub_pixel_size + 1); xt++)
              block[yt][xt].ready = FALSE;

          /* Copy samples from top row to block */

          for (xtt = 0, xt = (x - x1) * sub_pixel_size;
               xtt < (sub_pixel_size + 1);
               xtt++, xt++)
            block[0][xtt] = top_row[xt];

          /* Render pixel on (x, y) */

          num_samples += gimp_render_sub_pixel (max_depth, 1, block, x, y, 0, 0,
                                                sub_pixel_size, sub_pixel_size,
                                                threshold, sub_pixel_size,
                                                color,
                                                render_func, render_data);

          if (put_pixel_func)
            (* put_pixel_func) (x, y, color, put_pixel_data);

          /* Copy block information to rows */

          top_row[(x - x1 + 1) * sub_pixel_size] = block[0][sub_pixel_size];

          for (xtt = 0, xt = (x - x1) * sub_pixel_size;
               xtt < (sub_pixel_size + 1);
               xtt++, xt++)
            bot_row[xt] = block[sub_pixel_size][xtt];

          /* Swap first and last columns */

          for (yt = 0; yt < (sub_pixel_size + 1); yt++)
            {
              tmp_sample                = block[yt][0];
              block[yt][0]              = block[yt][sub_pixel_size];
              block[yt][sub_pixel_size] = tmp_sample;
            }
        }

      /* Swap rows */

      tmp_row = top_row;
      top_row = bot_row;
      bot_row = tmp_row;

      /* Call progress display function (if any) */

      if (progress_func != NULL)
        (* progress_func) (y1, y2, y, progress_data);
    }

  /* Free memory */

  for (y = 0; y < (sub_pixel_size + 1); y++)
    gegl_scratch_free (block[y]);

  gegl_scratch_free (block);
  gegl_scratch_free (top_row);
  gegl_scratch_free (bot_row);

  return num_samples;
}

/* --- end libammoos/core/fieldcolor/gimpadaptivesupersample.c --- */

/* --- begin libammoos/core/fieldcolor/gimpbilinear.c --- */
/* LIBGIMP - The AmmoOS Image Library
 * Copyright (C) 1995-1997 Peter Mattis and Spencer Kimball
 *
 * This library is free software: you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 3 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Library General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library.  If not, see
 * <https://www.gnu.org/licenses/>.
 */

#include "config.h"

#include <gegl.h>
#include <glib-object.h>

#include "libgimpmath/gimpmath.h"

#include "gimpcolortypes.h"

#include "gimpbilinear.h"


/**
 * SECTION: gimpbilinear
 * @title: GimpBilinear
 * @short_description: Utility functions for bilinear interpolation.
 *
 * Utility functions for bilinear interpolation.
 **/


/**
 * gimp_bilinear:
 * @x:
 * @y:
 * @values: (array fixed-size=4):
 */
gdouble
gimp_bilinear (gdouble  x,
               gdouble  y,
               gdouble *values)
{
  gdouble m0, m1;

  g_return_val_if_fail (values != NULL, 0.0);

  x = fmod (x, 1.0);
  y = fmod (y, 1.0);

  if (x < 0.0)
    x += 1.0;
  if (y < 0.0)
    y += 1.0;

  m0 = (1.0 - x) * values[0] + x * values[1];
  m1 = (1.0 - x) * values[2] + x * values[3];

  return (1.0 - y) * m0 + y * m1;
}

/**
 * gimp_bilinear_8:
 * @x:
 * @y:
 * @values: (array fixed-size=4):
 */
guchar
gimp_bilinear_8 (gdouble x,
                 gdouble y,
                 guchar *values)
{
  gdouble m0, m1;

  g_return_val_if_fail (values != NULL, 0);

  x = fmod (x, 1.0);
  y = fmod (y, 1.0);

  if (x < 0.0)
    x += 1.0;
  if (y < 0.0)
    y += 1.0;

  m0 = (1.0 - x) * values[0] + x * values[1];
  m1 = (1.0 - x) * values[2] + x * values[3];

  return (guchar) ((1.0 - y) * m0 + y * m1);
}

/**
 * gimp_bilinear_16:
 * @x:
 * @y:
 * @values: (array fixed-size=4):
 */
guint16
gimp_bilinear_16 (gdouble  x,
                  gdouble  y,
                  guint16 *values)
{
  gdouble m0, m1;

  g_return_val_if_fail (values != NULL, 0);

  x = fmod (x, 1.0);
  y = fmod (y, 1.0);

  if (x < 0.0)
    x += 1.0;
  if (y < 0.0)
    y += 1.0;

  m0 = (1.0 - x) * values[0] + x * values[1];
  m1 = (1.0 - x) * values[2] + x * values[3];

  return (guint16) ((1.0 - y) * m0 + y * m1);
}

/**
 * gimp_bilinear_32:
 * @x:
 * @y:
 * @values: (array fixed-size=4):
 */
guint32
gimp_bilinear_32 (gdouble  x,
                  gdouble  y,
                  guint32 *values)
{
  gdouble m0, m1;

  g_return_val_if_fail (values != NULL, 0);

  x = fmod (x, 1.0);
  y = fmod (y, 1.0);

  if (x < 0.0)
    x += 1.0;
  if (y < 0.0)
    y += 1.0;

  m0 = (1.0 - x) * values[0] + x * values[1];
  m1 = (1.0 - x) * values[2] + x * values[3];

  return (guint32) ((1.0 - y) * m0 + y * m1);
}

/**
 * gimp_bilinear_rgb:
 * @x:
 * @y:
 * @values:    (array fixed-size=16): Array of pixels in RGBA double format
 * @has_alpha: Whether @values has an alpha channel
 * @retvalues: (array fixed-size=4):  Resulting pixel
 */
void
gimp_bilinear_rgb (gdouble    x,
                   gdouble    y,
                   gdouble   *values,
                   gboolean   has_alpha,
                   gdouble   *retvalues)
{
  gdouble  m0;
  gdouble  m1;
  gdouble  ix;
  gdouble  iy;
  gdouble  a[4]  = { 1.0, 1.0, 1.0, 1.0 };
  gdouble  alpha = 1.0;

  for (gint i = 0; i < 3; i++)
    retvalues[i] = 0.0;
  retvalues[3] = 1.0;

  g_return_if_fail (values != NULL);

  x = fmod (x, 1.0);
  y = fmod (y, 1.0);

  if (x < 0)
    x += 1.0;
  if (y < 0)
    y += 1.0;

  ix = 1.0 - x;
  iy = 1.0 - y;

  if (has_alpha)
    {
      for (gint i = 0; i < 4; i++)
        a[i] = values[(i * 4) + 3];

      m0 = ix * a[0] + x * a[1];
      m1 = ix * a[2] + x * a[3];

      alpha = retvalues[3] = iy * m0 + y * m1;
    }

  if (alpha > 0)
    {
      for (gint i = 0; i < 3; i++)
        {
          m0 = ix * a[0] * values[0 + i] + x * a[1] * values[4 + i];
          m1 = ix * a[2] * values[8 + i] + x * a[3] * values[12 + i];

          retvalues[i] = (iy * m0 + y * m1) / alpha;
        }
    }
}

/* --- end libammoos/core/fieldcolor/gimpbilinear.c --- */

/* --- begin libammoos/core/fieldcolor/gimpcairo.c --- */
/* LIBGIMP - The AmmoOS Image Library
 * Copyright (C) 1995-1997 Peter Mattis and Spencer Kimball
 *
 * gimpcairo.c
 * Copyright (C) 2007      Sven Neumann <sven@ammoos.org>
 *               2010-2012 Michael Natterer <mitch@ammoos.org>
 *
 * This library is free software: you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 3 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library.  If not, see
 * <https://www.gnu.org/licenses/>.
 */

#include "config.h"

#include <cairo.h>
#include <gio/gio.h>
#include <gegl.h>

#include "libgimpbase/gimpbase.h"

#include "gimpcolortypes.h"

#include "gimpcairo.h"
#include "gimpcolor-private.h"


/**
 * SECTION: gimpcairo
 * @title: GimpCairo
 * @short_description: Color utility functions for cairo
 *
 * Utility functions that make cairo easier to use with AmmoOS Image color
 * data types.
 **/


static void gimp_cairo_surface_buffer_changed (GeglBuffer          *buffer,
                                               const GeglRectangle *rect,
                                               cairo_surface_t     *surface);


/**
 * gimp_cairo_checkerboard_create:
 * @cr:    Cairo context
 * @size:  check size
 * @light: light check color or %NULL to use the default light gray
 * @dark:  dark check color or %NULL to use the default dark gray
 *
 * Create a repeating checkerboard pattern.
 *
 * Returns: a new Cairo pattern that can be used as a source on @cr.
 *
 * Since: 2.6
 **/
cairo_pattern_t *
gimp_cairo_checkerboard_create (cairo_t         *cr,
                                gint             size,
                                const GeglColor *light,
                                const GeglColor *dark)
{
  cairo_t         *context;
  cairo_surface_t *surface;
  cairo_pattern_t *pattern;

  g_return_val_if_fail (cr != NULL, NULL);
  g_return_val_if_fail (size > 0, NULL);

  surface = cairo_surface_create_similar (cairo_get_target (cr),
                                          CAIRO_CONTENT_COLOR,
                                          2 * size, 2 * size);
  context = cairo_create (surface);

  if (light)
    {
      gdouble rgb[3];

      gegl_color_get_pixel (GEGL_COLOR (light), babl_format ("R'G'B' double"), rgb);
      cairo_set_source_rgb (context, rgb[0], rgb[1], rgb[2]);
    }
  else
    {
      cairo_set_source_rgb (context,
                            GIMP_CHECK_LIGHT, GIMP_CHECK_LIGHT, GIMP_CHECK_LIGHT);
    }

  cairo_rectangle (context, 0,    0,    size, size);
  cairo_rectangle (context, size, size, size, size);
  cairo_fill (context);

  if (dark)
    {
      gdouble rgb[3];

      gegl_color_get_pixel (GEGL_COLOR (dark), babl_format ("R'G'B' double"), rgb);
      cairo_set_source_rgb (context, rgb[0], rgb[1], rgb[2]);
    }
  else
    {
      cairo_set_source_rgb (context,
                            GIMP_CHECK_DARK, GIMP_CHECK_DARK, GIMP_CHECK_DARK);
    }

  cairo_rectangle (context, 0,    size, size, size);
  cairo_rectangle (context, size, 0,    size, size);
  cairo_fill (context);

  cairo_destroy (context);

  pattern = cairo_pattern_create_for_surface (surface);
  cairo_pattern_set_extend (pattern, CAIRO_EXTEND_REPEAT);

  cairo_surface_destroy (surface);

  return pattern;
}

/**
 * gimp_cairo_surface_get_format:
 * @surface: a Cairo surface
 *
 * This function returns a #Babl format that corresponds to @surface's
 * pixel format.
 *
 * Returns: the #Babl format of @surface.
 *
 * Since: 2.10
 **/
const Babl *
gimp_cairo_surface_get_format (cairo_surface_t *surface)
{
  g_return_val_if_fail (surface != NULL, NULL);
  g_return_val_if_fail (cairo_surface_get_type (surface) ==
                        CAIRO_SURFACE_TYPE_IMAGE, NULL);

  switch (cairo_image_surface_get_format (surface))
    {
    case CAIRO_FORMAT_RGB24:    return babl_format ("cairo-RGB24");
    case CAIRO_FORMAT_ARGB32:   return babl_format ("cairo-ARGB32");
    case CAIRO_FORMAT_A8:       return babl_format ("cairo-A8");
#if CAIRO_VERSION >= CAIRO_VERSION_ENCODE(1, 17, 2)
    /* Since Cairo 1.17.2 */
    case CAIRO_FORMAT_RGB96F:   return babl_format ("R'G'B' float");
    case CAIRO_FORMAT_RGBA128F: return babl_format ("R'aG'aB'aA float");
#endif

    default:
      break;
    }

  g_return_val_if_reached (NULL);
}

/**
 * gimp_cairo_surface_create_buffer:
 * @surface: a Cairo surface
 * @format:  a Babl format.
 *
 * This function returns a #GeglBuffer which wraps @surface's pixels.
 * It must only be called on image surfaces, calling it on other surface
 * types is an error.
 *
 * If @format is set, the returned [class@Gegl.Buffer] will use it. It has to
 * map with @surface Cairo format. If unset, the buffer format will be
 * determined from @surface. The main difference is that automatically
 * determined format has sRGB space and TRC by default.
 *
 * Returns: (transfer full): a #GeglBuffer
 *
 * Since: 2.10
 *
 * Deprecated: 3.0.8: Use gimp_cairo_surface_get_buffer().
 **/
GeglBuffer *
gimp_cairo_surface_create_buffer (cairo_surface_t *surface,
                                  const Babl      *format)
{
  return gimp_cairo_surface_get_buffer (surface, format, TRUE);
}

/**
 * gimp_cairo_surface_get_buffer:
 * @surface: a Cairo surface
 * @format:  a Babl format.
 * @sync_back: whether changes on the returned buffer should be synced
 *             back to @surface.
 *
 * This function returns a [class@Gegl.Buffer] containing @surface's
 * pixels. It must only be called on image surfaces, calling it on other
 * surface types is an error.
 *
 * If @format is set, the returned buffer will use it. It has to map
 * with @surface Cairo format. If unset, the buffer format will be
 * determined from @surface. The main difference is that automatically
 * determined format has sRGB space and TRC by default.
 *
 * If you want the changes to the returned buffer to be synced back to
 * @surface data, set @sync_back to %TRUE. If you don't need this and
 * only want a copy of @surface at a given time, %FALSE will be less
 * costly.
 *
 * When @sync_back is %TRUE, [method@Gegl.Buffer.freeze_changed] and
 * [method@Gegl.Buffer.thaw_changed] may be useful to block intermediate
 * syncing.
 *
 * Returns: (transfer full): a #GeglBuffer
 *
 * Since: 3.0.8
 **/
GeglBuffer *
gimp_cairo_surface_get_buffer (cairo_surface_t *surface,
                               const Babl      *format,
                               gboolean         sync_back)
{
  const Babl    *surface_format;
  GeglBuffer    *buffer;
  GeglRectangle  extent = {0};
  gint           rowstride;
  gint           bpp;

  g_return_val_if_fail (surface != NULL, NULL);
  g_return_val_if_fail (cairo_surface_get_type (surface) == CAIRO_SURFACE_TYPE_IMAGE, NULL);

  surface_format = gimp_cairo_surface_get_format (surface);
  rowstride      = cairo_image_surface_get_stride (surface);
  bpp            = babl_format_get_bytes_per_pixel (surface_format);

  g_return_val_if_fail (format == NULL || babl_format_get_bytes_per_pixel (format) == bpp, NULL);

  if (format == NULL)
    format = surface_format;

  extent.width  = cairo_image_surface_get_width  (surface);
  extent.height = cairo_image_surface_get_height (surface);

  if ( ! sync_back || rowstride % bpp != 0 ||
      extent.width * extent.height > GIMP_LINEAR_BUFFER_MAX_SIZE)
    buffer = gegl_buffer_new (&extent, format);
  else
    return gegl_buffer_linear_new_from_data (cairo_image_surface_get_data (surface),
                                             format, &extent, rowstride,
                                             (GDestroyNotify) cairo_surface_destroy,
                                             cairo_surface_reference (surface));

  gegl_buffer_set (buffer, &extent, 0, format,
                   cairo_image_surface_get_data (surface),
                   rowstride);

  if (sync_back)
    {
      /* Making sure we don't work on a destroyed surface. */
      g_object_set_data_full (G_OBJECT (buffer),
                              "ammoos-cairo-surface-get-buffer-surface",
                              cairo_surface_reference (surface),
                              (GDestroyNotify) cairo_surface_destroy);
      gegl_buffer_signal_connect (buffer, "changed",
                                  G_CALLBACK (gimp_cairo_surface_buffer_changed),
                                  surface);
    }

  return buffer;
}


/* Private functions */

static void
gimp_cairo_surface_buffer_changed (GeglBuffer          *buffer,
                                   const GeglRectangle *rect,
                                   cairo_surface_t     *surface)
{
  unsigned char *data;
  gint           stride;
  gint           bpp;

  data   = cairo_image_surface_get_data (surface);
  stride = cairo_image_surface_get_stride (surface);
  bpp    = babl_format_get_bytes_per_pixel (gegl_buffer_get_format (buffer));

  data += stride * rect->y + rect->x * bpp;

  if ((rect->x == 0 && rect->width == gegl_buffer_get_width (buffer)) || rect->height == 1)
    {
      gegl_buffer_get (buffer, rect, 1.0, NULL,
                       data, stride, GEGL_ABYSS_NONE);
    }
  else
    {
      GeglRectangle extent;

      extent.x      = rect->x;
      extent.width  = rect->width;
      extent.height = 1;

      for (gint y = rect->y; y < rect->y + rect->height; y++)
        {
          extent.y = y;
          gegl_buffer_get (buffer, &extent, 1.0, NULL,
                           data, stride, GEGL_ABYSS_NONE);
          data += stride;
        }
    }

  cairo_surface_mark_dirty (surface);
}

/* --- end libammoos/core/fieldcolor/gimpcairo.c --- */

/* --- begin libammoos/core/fieldcolor/gimpcolor-parse.c --- */
/* LIBGIMP - The AmmoOS Image Library
 * Copyright (C) 1995-1997 Peter Mattis and Spencer Kimball
 *
 * gimpcolor-parse.c
 * Copyright (C) 2023 Jehan
 *
 * Some of the code in here was inspired and partly copied from pango
 * and librsvg.
 *
 * This library is free software: you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 3 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Library General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library.  If not, see
 * <https://www.gnu.org/licenses/>.
 */

#include "config.h"

#include <babl/babl.h>
#include <cairo.h>
#include <gdk-pixbuf/gdk-pixbuf.h>
#include <gegl.h>

#include "libgimpbase/gimpbase.h"

#include "gimpcolor.h"


static GeglColor * gimp_color_parse_name_internal (const gchar   *name);
static GeglColor * gimp_color_parse_hex_internal  (const gchar   *hex);
static GeglColor * gimp_color_parse_css_numeric   (const gchar   *css);
static GeglColor * gimp_color_parse_css_internal  (const gchar   *css);
static gchar     * gimp_color_parse_strip         (const gchar   *str,
                                                   gint           len);
static gint        gimp_color_entry_compare       (gconstpointer  a,
                                                   gconstpointer  b);
static gboolean    gimp_color_parse_hex_component (const gchar   *hex,
                                                   gint           len,
                                                   gdouble       *value);


typedef struct
{
  const gchar  *name;
  const guchar  red;
  const guchar  green;
  const guchar  blue;
} ColorEntry;

static const ColorEntry named_colors[] =
{
  { "aliceblue",             240, 248, 255 },
  { "antiquewhite",          250, 235, 215 },
  { "aqua",                    0, 255, 255 },
  { "aquamarine",            127, 255, 212 },
  { "azure",                 240, 255, 255 },
  { "beige",                 245, 245, 220 },
  { "bisque",                255, 228, 196 },
  { "black",                   0,   0,   0 },
  { "blanchedalmond",        255, 235, 205 },
  { "blue",                    0,   0, 255 },
  { "blueviolet",            138,  43, 226 },
  { "brown",                 165,  42,  42 },
  { "burlywood",             222, 184, 135 },
  { "cadetblue",              95, 158, 160 },
  { "chartreuse",            127, 255,   0 },
  { "chocolate",             210, 105,  30 },
  { "coral",                 255, 127,  80 },
  { "cornflowerblue",        100, 149, 237 },
  { "cornsilk",              255, 248, 220 },
  { "crimson",               220,  20,  60 },
  { "cyan",                    0, 255, 255 },
  { "darkblue",                0,   0, 139 },
  { "darkcyan",                0, 139, 139 },
  { "darkgoldenrod",         184, 134,  11 },
  { "darkgray",              169, 169, 169 },
  { "darkgreen",               0, 100,   0 },
  { "darkgrey",              169, 169, 169 },
  { "darkkhaki",             189, 183, 107 },
  { "darkmagenta",           139,   0, 139 },
  { "darkolivegreen",         85, 107,  47 },
  { "darkorange",            255, 140,   0 },
  { "darkorchid",            153,  50, 204 },
  { "darkred",               139,   0,   0 },
  { "darksalmon",            233, 150, 122 },
  { "darkseagreen",          143, 188, 143 },
  { "darkslateblue",          72,  61, 139 },
  { "darkslategray",          47,  79,  79 },
  { "darkslategrey",          47,  79,  79 },
  { "darkturquoise",           0, 206, 209 },
  { "darkviolet",            148,   0, 211 },
  { "deeppink",              255,  20, 147 },
  { "deepskyblue",             0, 191, 255 },
  { "dimgray",               105, 105, 105 },
  { "dimgrey",               105, 105, 105 },
  { "dodgerblue",             30, 144, 255 },
  { "firebrick",             178,  34,  34 },
  { "floralwhite" ,          255, 250, 240 },
  { "forestgreen",            34, 139,  34 },
  { "fuchsia",               255,   0, 255 },
  { "gainsboro",             220, 220, 220 },
  { "ghostwhite",            248, 248, 255 },
  { "gold",                  255, 215,   0 },
  { "goldenrod",             218, 165,  32 },
  { "gray",                  128, 128, 128 },
  { "green",                   0, 128,   0 },
  { "greenyellow",           173, 255,  47 },
  { "grey",                  128, 128, 128 },
  { "honeydew",              240, 255, 240 },
  { "hotpink",               255, 105, 180 },
  { "indianred",             205,  92,  92 },
  { "indigo",                 75,   0, 130 },
  { "ivory",                 255, 255, 240 },
  { "khaki",                 240, 230, 140 },
  { "lavender",              230, 230, 250 },
  { "lavenderblush",         255, 240, 245 },
  { "lawngreen",             124, 252,   0 },
  { "lemonchiffon",          255, 250, 205 },
  { "lightblue",             173, 216, 230 },
  { "lightcoral",            240, 128, 128 },
  { "lightcyan",             224, 255, 255 },
  { "lightgoldenrodyellow",  250, 250, 210 },
  { "lightgray",             211, 211, 211 },
  { "lightgreen",            144, 238, 144 },
  { "lightgrey",             211, 211, 211 },
  { "lightpink",             255, 182, 193 },
  { "lightsalmon",           255, 160, 122 },
  { "lightseagreen",          32, 178, 170 },
  { "lightskyblue",          135, 206, 250 },
  { "lightslategray",        119, 136, 153 },
  { "lightslategrey",        119, 136, 153 },
  { "lightsteelblue",        176, 196, 222 },
  { "lightyellow",           255, 255, 224 },
  { "lime",                    0, 255,   0 },
  { "limegreen",              50, 205,  50 },
  { "linen",                 250, 240, 230 },
  { "magenta",               255,   0, 255 },
  { "maroon",                128,   0,   0 },
  { "mediumaquamarine",      102, 205, 170 },
  { "mediumblue",              0,   0, 205 },
  { "mediumorchid",          186,  85, 211 },
  { "mediumpurple",          147, 112, 219 },
  { "mediumseagreen",         60, 179, 113 },
  { "mediumslateblue",       123, 104, 238 },
  { "mediumspringgreen",       0, 250, 154 },
  { "mediumturquoise",        72, 209, 204 },
  { "mediumvioletred",       199,  21, 133 },
  { "midnightblue",           25,  25, 112 },
  { "mintcream",             245, 255, 250 },
  { "mistyrose",             255, 228, 225 },
  { "moccasin",              255, 228, 181 },
  { "navajowhite",           255, 222, 173 },
  { "navy",                    0,   0, 128 },
  { "oldlace",               253, 245, 230 },
  { "olive",                 128, 128,   0 },
  { "olivedrab",             107, 142,  35 },
  { "orange",                255, 165,   0 },
  { "orangered",             255,  69,   0 },
  { "orchid",                218, 112, 214 },
  { "palegoldenrod",         238, 232, 170 },
  { "palegreen",             152, 251, 152 },
  { "paleturquoise",         175, 238, 238 },
  { "palevioletred",         219, 112, 147 },
  { "papayawhip",            255, 239, 213 },
  { "peachpuff",             255, 218, 185 },
  { "peru",                  205, 133,  63 },
  { "pink",                  255, 192, 203 },
  { "plum",                  221, 160, 221 },
  { "powderblue",            176, 224, 230 },
  { "purple",                128,   0, 128 },
  { "red",                   255,   0,   0 },
  { "rosybrown",             188, 143, 143 },
  { "royalblue",              65, 105, 225 },
  { "saddlebrown",           139,  69,  19 },
  { "salmon",                250, 128, 114 },
  { "sandybrown",            244, 164,  96 },
  { "seagreen",               46, 139,  87 },
  { "seashell",              255, 245, 238 },
  { "sienna",                160,  82,  45 },
  { "silver",                192, 192, 192 },
  { "skyblue",               135, 206, 235 },
  { "slateblue",             106,  90, 205 },
  { "slategray",             112, 128, 144 },
  { "slategrey",             112, 128, 144 },
  { "snow",                  255, 250, 250 },
  { "springgreen",             0, 255, 127 },
  { "steelblue",              70, 130, 180 },
  { "tan",                   210, 180, 140 },
  { "teal",                    0, 128, 128 },
  { "thistle",               216, 191, 216 },
  { "tomato",                255,  99,  71 },
  { "turquoise",              64, 224, 208 },
  { "violet",                238, 130, 238 },
  { "wheat",                 245, 222, 179 },
  { "white",                 255, 255, 255 },
  { "whitesmoke",            245, 245, 245 },
  { "yellow",                255, 255,   0 },
  { "yellowgreen",           154, 205,  50 }
};


/**
 * gimp_color_parse_css:
 * @css: (type utf8): a string describing a color in CSS notation
 *
 * Attempts to parse a string describing an sRGB color in CSS notation. This can
 * be either a numerical representation (`rgb(255,0,0)` or `rgb(100%,0%,0%)`)
 * or a hexadecimal notation as parsed by [func@color_parse_hex] (`##ff0000`) or
 * a color name as parsed by [func@color_parse_css] (`red`).
 *
 * Additionally the `rgba()`, `hsl()` and `hsla()` functions are supported too.
 *
 * Returns: (transfer full): a newly allocated [class@Gegl.Color] if @css was
 *                           parsed successfully, %NULL otherwise
 **/
GeglColor *
gimp_color_parse_css (const gchar *css)
{
  return gimp_color_parse_css_substring (css, -1);
}

/**
 * gimp_color_parse_hex:
 * @hex: (type utf8): a string describing a color in hexadecimal notation
 *
 * Attempts to parse a string describing a sRGB color in hexadecimal
 * notation (optionally prefixed with a '#').
 *
 * Returns: (transfer full): a newly allocated color representing @hex.
 **/
GeglColor *
gimp_color_parse_hex (const gchar *hex)
{
  return gimp_color_parse_hex_substring (hex, -1);
}

/**
 * gimp_color_parse_name:
 * @name: (type utf8): a color name (in UTF-8 encoding)
 *
 * Attempts to parse a color name. This function accepts [SVG 1.1 color
 * keywords](https://www.w3.org/TR/SVG11/types.html#ColorKeywords).
 *
 * Returns: (transfer full): a sRGB color as defined in "4.4. Recognized color
 *          keyword names" list of SVG 1.1 specification, if @name was parsed
 *          successfully, %NULL otherwise
 **/
GeglColor *
gimp_color_parse_name (const gchar *name)
{
  return gimp_color_parse_name_substring (name, -1);
}

/**
 * gimp_color_list_names:
 * @colors: (out) (optional) (array zero-terminated=1) (element-type GeglColor) (transfer full): return location for an array of [class@Gegl.Color]
 *
 * Returns the list of [SVG 1.0 color
 * keywords](https://www.w3.org/TR/SVG/types.html) that is recognized by
 * [func@color_parse_name].
 *
 * The returned strings are const and must not be freed. Only the array
 * must be freed with `g_free()`.
 *
 * The optional @colors arrays must be freed with [func@color_array_free] when
 * they are no longer needed.
 *
 * Returns: (array zero-terminated=1) (transfer container): an array of color names.
 *
 * Since: 2.2
 **/
const gchar **
gimp_color_list_names (GimpColorArray *colors)
{
  const gchar **names;
  gint    i;

  names = g_new0 (const gchar *, G_N_ELEMENTS (named_colors) + 1);

  if (colors)
    *colors = g_new0 (GeglColor *, G_N_ELEMENTS (named_colors) + 1);

  for (i = 0; i < G_N_ELEMENTS (named_colors); i++)
    {
      names[i] = named_colors[i].name;

      if (colors)
        {
          GeglColor *color = gegl_color_new (NULL);

          gegl_color_set_rgba_with_space (color,
                                          (gdouble) named_colors[i].red / 255.0,
                                          (gdouble) named_colors[i].green / 255.0,
                                          (gdouble) named_colors[i].blue / 255.0,
                                          1.0, NULL);
          (*colors)[i] = color;
        }
    }

  return names;
}

/**
 * gimp_color_parse_css_substring: (skip)
 * @css: (array length=len): a string describing a color in CSS notation
 * @len: the length of @css, in bytes. or -1 if @css is nul-terminated
 *
 * Attempts to parse a string describing an sRGB color in CSS notation. This can
 * be either a numerical representation (`rgb(255,0,0)` or `rgb(100%,0%,0%)`) or
 * a hexadecimal notation as parsed by [func@color_parse_hex] (`##ff0000`) or a
 * color name as parsed by [func@color_parse_name] (`red`).
 *
 * Additionally the `rgba()`, `hsl()` and `hsla()` functions are supported too.
 *
 * Returns: (transfer full): a newly allocated [class@Gegl.Color] if @css was
 *                           parsed successfully, %NULL otherwise
 *
 * Since: 2.2
 **/
GeglColor *
gimp_color_parse_css_substring (const gchar *css,
                                gint         len)
{
  gchar     *tmp;
  GeglColor *color;

  g_return_val_if_fail (css != NULL, FALSE);

  tmp = gimp_color_parse_strip (css, len);

  if (g_strcmp0 (tmp, "transparent") == 0)
    color = gegl_color_new ("transparent");
  else
    color = gimp_color_parse_css_internal (tmp);

  g_free (tmp);

  return color;
}

/**
 * gimp_color_parse_hex_substring: (skip)
 * @hex: (array length=len): a string describing a color in hexadecimal notation
 * @len: the length of @hex, in bytes. or -1 if @hex is nul-terminated
 *
 * Attempts to parse a string describing an RGB color in hexadecimal
 * notation (optionally prefixed with a '#').
 *
 * This function does not touch the alpha component of @rgb.
 *
 * Returns: (transfer full): a newly allocated color representing @hex.
 *
 * Since: 2.2
 **/
GeglColor *
gimp_color_parse_hex_substring (const gchar *hex,
                                gint         len)
{
  GeglColor *result;
  gchar     *tmp;

  g_return_val_if_fail (hex != NULL, FALSE);

  tmp = gimp_color_parse_strip (hex, len);

  result = gimp_color_parse_hex_internal (tmp);

  g_free (tmp);

  return result;
}

/**
 * gimp_color_parse_name_substring: (skip)
 * @name: (array length=len): a color name (in UTF-8 encoding)
 * @len:  the length of @name, in bytes. or -1 if @name is nul-terminated
 *
 * Attempts to parse a color name. This function accepts [SVG 1.1 color
 * keywords](https://www.w3.org/TR/SVG11/types.html#ColorKeywords).
 *
 * Returns: (transfer full): a sRGB color as defined in "4.4. Recognized color
 *          keyword names" list of SVG 1.1 specification, if @name was parsed
 *          successfully, %NULL otherwise
 *
 * Since: 2.2
 **/
GeglColor *
gimp_color_parse_name_substring (const gchar *name,
                                 gint         len)
{
  gchar     *tmp;
  GeglColor *result;

  g_return_val_if_fail (name != NULL, FALSE);

  tmp = gimp_color_parse_strip (name, len);

  result = gimp_color_parse_name_internal (tmp);

  g_free (tmp);

  return result;
}


/* Private functions. */

static GeglColor *
gimp_color_parse_name_internal (const gchar *name)
{
  /* GeglColor also has name reading support. It supports HTML 4.01 standard
   * whereas here we have SVG 1.0 name support. Moreover we support a lot more
   * colors.
   */
  const ColorEntry *entry = bsearch (name, named_colors,
                                     G_N_ELEMENTS (named_colors), sizeof (ColorEntry),
                                     gimp_color_entry_compare);

  if (entry)
    {
      GeglColor *color = gegl_color_new (NULL);

      gegl_color_set_rgba_with_space (color, (gdouble) entry->red / 255.0,
                                      (gdouble) entry->green / 255.0, (gdouble) entry->blue / 255.0,
                                      1.0, NULL);

      return color;
    }

  return NULL;
}

static GeglColor *
gimp_color_parse_hex_internal (const gchar *hex)
{
  GeglColor *color;
  gint       i;
  gsize      len;
  gdouble    val[3];

  if (hex[0] == '#')
    hex++;

  len = strlen (hex);
  /* TODO: current implementation has 2 issues:
   * 1. It doesn't support the alpha channel, even though CSS spec now has
   *    support for it with either 8 or 4 digits.
   * 2. The spec has nothing about channels on 3 or 4 digits, which we support
   *    here (for higher precision?). Is this format really supported somewhere?
   *    Do we want to keep this?
   * See: https://drafts.csswg.org/css-color/#hex-notation
   */
  if (len % 3 || len < 3 || len > 12)
    return NULL;

  len /= 3;

  for (i = 0; i < 3; i++, hex += len)
    {
      if (! gimp_color_parse_hex_component (hex, len, val + i))
        return NULL;
    }

  color = gegl_color_new (NULL);
  gegl_color_set_pixel (color, babl_format ("R'G'B' double"), val);

  return color;
}

static GeglColor *
gimp_color_parse_css_numeric (const gchar *css)
{
  GeglColor *color;
  gdouble    values[4];
  gboolean   alpha;
  gboolean   hsl;
  gint       i;

  if (css[0] == 'r' && css[1] == 'g' && css[2] == 'b')
    hsl = FALSE;
  else if (css[0] == 'h' && css[1] == 's' && css[2] == 'l')
    hsl = TRUE;
  else
    g_return_val_if_reached (NULL);

  if (css[3] == 'a' && css[4] == '(')
    alpha = TRUE;
  else if (css[3] == '(')
    alpha = FALSE;
  else
    g_return_val_if_reached (NULL);

  css += (alpha ? 5 : 4);

  for (i = 0; i < (alpha ? 4 : 3); i++)
    {
      const gchar *end = css;

      while (*end && *end != ',' && *end != '%' && *end != ')')
        end++;

      if (i == 3 || *end == '%')
        {
          values[i] = g_ascii_strtod (css, (gchar **) &end);

          if (errno == ERANGE)
            return FALSE;

          if (*end == '%')
            {
              end++;
              values[i] /= 100.0;
            }
        }
      else
        {
          glong value = strtol (css, (gchar **) &end, 10);

          if (errno == ERANGE)
            return FALSE;

          if (hsl)
            values[i] = value / (i == 0 ? 360.0 : 100.0);
          else
            values[i] = value / 255.0;
        }

      /* CSS Color specs indicates:
       * > Values outside these ranges are not invalid, but are clamped to the
       * > ranges defined here at parsed-value time.
       * See: https://drafts.csswg.org/css-color/#rgb-functions
       * So even though we might hope being able to reach non-sRGB colors when
       * using the percentage syntax, the spec explicitly forbids it.
       */
      values[i] = CLAMP (values[i], 0.0, 1.0);

      while (*end == ',' || g_ascii_isspace (*end))
        end++;

      css = end;
    }

  if (*css != ')')
    return NULL;

  color = gegl_color_new (NULL);
  if (hsl)
    {
      gfloat values_f[4];

      for (i = 0; i < (alpha ? 4 : 3); i++)
        values_f[i] = (gfloat) values[i];

      if (alpha)
        gegl_color_set_pixel (color, babl_format ("HSLA float"), values_f);
      else
        gegl_color_set_pixel (color, babl_format ("HSL float"), values_f);
    }
  else
    {
      if (alpha)
        gegl_color_set_pixel (color, babl_format ("R'G'B'A double"), values);
      else
        gegl_color_set_pixel (color, babl_format ("R'G'B' double"), values);
    }

  return color;
}

static GeglColor *
gimp_color_parse_css_internal (const gchar *css)
{
  if (css[0] == '#')
    {
      return gimp_color_parse_hex_internal (css);
    }
  else if (strncmp (css, "rgb(", 4)  == 0 ||
           strncmp (css, "hsl(", 4)  == 0 ||
           strncmp (css, "rgba(", 5) == 0 ||
           strncmp (css, "hsla(", 5) == 0)
    {
      return gimp_color_parse_css_numeric (css);
    }
  else
    {
      return gimp_color_parse_name_internal (css);
    }
}

static gchar *
gimp_color_parse_strip (const gchar *str,
                        gint         len)
{
  gchar *result;

  while (len > 0 && g_ascii_isspace (*str))
    {
      str++;
      len--;
    }

  if (len < 0)
    {
      while (g_ascii_isspace (*str))
        str++;

      len = strlen (str);
    }

  while (len > 0 && g_ascii_isspace (str[len - 1]))
    len--;

  result = g_malloc (len + 1);

  memcpy (result, str, len);
  result[len] = '\0';

  return result;
}

static gint
gimp_color_entry_compare (gconstpointer a,
                          gconstpointer b)
{
  const gchar      *name  = a;
  const ColorEntry *entry = b;

  return g_ascii_strcasecmp (name, entry->name);
}

static gboolean
gimp_color_parse_hex_component (const gchar *hex,
                                gint         len,
                                gdouble     *value)
{
  gint  i;
  guint c = 0;

  for (i = 0; i < len; i++, hex++)
    {
      if (!*hex || !g_ascii_isxdigit (*hex))
        return FALSE;

      c = (c << 4) | g_ascii_xdigit_value (*hex);
    }

  switch (len)
    {
    case 1: *value = (gdouble) c /    15.0;  break;
    case 2: *value = (gdouble) c /   255.0;  break;
    case 3: *value = (gdouble) c /  4095.0;  break;
    case 4: *value = (gdouble) c / 65535.0;  break;
    default:
      g_return_val_if_reached (FALSE);
    }

  return TRUE;
}

/* --- end libammoos/core/fieldcolor/gimpcolor-parse.c --- */

/* --- begin libammoos/core/fieldcolor/gimpcolor.c --- */
/* LIBGIMP - The AmmoOS Image Library
 * Copyright (C) 1995-1997 Peter Mattis and Spencer Kimball
 *
 * gimpcolor.c
 * Copyright (C) 2023 Jehan <jehan@ammoos.org>
 *
 * This library is free software: you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 3 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library.  If not, see
 * <https://www.gnu.org/licenses/>.
 */

#include "config.h"

#include <cairo.h>
#include <gdk-pixbuf/gdk-pixbuf.h>
#include <math.h>

#include <babl/babl.h>
#include <gegl.h>

#include "libgimpbase/gimpbase.h"

#include "gimpcolor.h"


/**
 * SECTION: gimpcolor
 * @title: GimpColor
 * @short_description: API to manipulate [class@Gegl.Color] objects.
 *
 * #GimpColor contains a few helper functions to manipulate [class@Gegl.Color]
 * objects more easily.
 **/


static const Babl * gimp_babl_format_get_with_alpha (const Babl *format);
static gfloat       gimp_color_get_CIE2000_distance (GeglColor  *color1,
                                                     GeglColor  *color2);


/*
 * GEGL_TYPE_COLOR
 */

/**
 * gimp_color_set_alpha:
 * @color: a [class@Gegl.Color]
 * @alpha: new value for the alpha channel.
 *
 * Update the @alpha channel, and any other component if necessary (e.g. in case
 * of premultiplied channels), without changing the format of @color.
 *
 * If @color has no alpha component, this function is a no-op.
 *
 * Since: 3.0
 **/
void
gimp_color_set_alpha (GeglColor *color,
                      gdouble    alpha)
{
  const Babl *format;
  gdouble     red;
  gdouble     green;
  gdouble     blue;
  guint8      pixel[40];

  format = gegl_color_get_format (color);

  gegl_color_get_rgba (color, &red, &green, &blue, NULL);
  gegl_color_set_rgba (color, red, green, blue, alpha);

  /* I could stop at this point, but we want to keep the initial format as much
   * as possible. Since we made a round-trip through linear RGBA float, we need
   * to reset the right format.
   *
   * Also why we do this round trip is because we know we can just change the
   * alpha channel and babl fishes will do the appropriate conversion. I first
   * thought of updating the alpha channel directly by editing the raw data
   * depending on the format, but doing so would break e.g. with premultiplied
   * channels. Babl already has all the internal knowledge so let it do its
   * thing. The only risk is the possible precision loss during conversion.
   * Let's assume that since we use an unbounded 32-bit intermediate value
   * (float), the loss would be acceptable.
   */
  format = gimp_babl_format_get_with_alpha (format);
  gegl_color_get_pixel (color, format, pixel);
  gegl_color_set_pixel (color, format, pixel);
}

/**
 * gimp_color_is_perceptually_identical:
 * @color1: a [class@Gegl.Color]
 * @color2: a [class@Gegl.Color]
 *
 * Determine whether @color1 and @color2 can be considered identical to the
 * human eyes, by computing the distance in a color space as perceptually
 * uniform as possible.
 *
 * This function will also consider any transparency channel, so that if you
 * only want to compare the pure color, you could for instance set both color's
 * alpha channel to 1.0 first (possibly on duplicates of the colors if originals
 * should not be modified), such as:
 *
 * ```C
 * gimp_color_set_alpha (color1, 1.0);
 * gimp_color_set_alpha (color2, 1.0);
 * if (gimp_color_is_perceptually_identical (color1, color2))
 *   {
 *     printf ("Both colors are identical, ignoring their alpha component");
 *   }
 * ```
 *
 * Note that this relation is not transitive, because it is based on a
 * color distance algorithm. It means that if color1 is perceptually
 * identical to color2, which is perceptually identical to color3, it
 * does not mean that color1 is perceptually identical to color3, as far
 * this algorithm is concerned.
 *
 * Returns: whether the 2 colors can be considered the same for the human eyes.
 *
 * Since: 3.0
 **/
gboolean
gimp_color_is_perceptually_identical (GeglColor *color1,
                                      GeglColor *color2)
{
  gdouble a1;
  gdouble a2;

  g_return_val_if_fail (GEGL_IS_COLOR (color1), FALSE);
  g_return_val_if_fail (GEGL_IS_COLOR (color2), FALSE);

  gegl_color_get_rgba (color1, NULL, NULL, NULL, &a1);
  gegl_color_get_rgba (color2, NULL, NULL, NULL, &a2);

  /* With different transparency, don't look further. */
  if (ABS (a1 - a2) > 1e-4)
    return FALSE;

  /* All CIE deltaE distances were designed with a 1.0 JND (Just Noticeable
   * Difference), though there was some revision to 2.3 for the CIE76 version.
   * I could not find a reliable source about whether such a revision happened
   * for the CIE2000 algorithm. My own tests though seemed to lean towards
   * using ~0.6 for the JND. That's what I'm using for the time being.
   */
  return (gimp_color_get_CIE2000_distance (color1, color2) < 0.6);
}

/**
 * gimp_color_is_out_of_self_gamut:
 * @color: a [class@Gegl.Color]
 *
 * Determine whether @color is out of its own space gamut. This can only
 * happen if the color space is unbounded and any of the color component
 * is out of the `[0; 1]` range.
 * A small error of margin is accepted, so that for instance a component
 * at -0.0000001 is not making the whole color to be considered as
 * out-of-gamut while it may just be computation imprecision.
 *
 * Returns: whether the color is out of its own color space gamut.
 *
 * Since: 3.0
 **/
gboolean
gimp_color_is_out_of_self_gamut (GeglColor *color)
{
  const Babl *format;
  const Babl *space;
  const Babl *ctype;
  gboolean    oog = FALSE;

  format = gegl_color_get_format (color);
  space  = babl_format_get_space (format);
  /* XXX assuming that all components have the same type. */
  ctype  = babl_format_get_type (format, 0);

  if (ctype == babl_type ("half")  ||
      ctype == babl_type ("float") ||
      ctype == babl_type ("double"))
  {
      /* Only unbounded colors can be out-of-gamut. */
      const Babl *model;

      model = babl_format_get_model (format);

#define CHANNEL_EPSILON 1e-3
        if (model == babl_model ("R'G'B'")  ||
            model == babl_model ("R~G~B~")  ||
            model == babl_model ("RGB")     ||
            model == babl_model ("R'G'B'A") ||
            model == babl_model ("R~G~B~A") ||
            model == babl_model ("RGBA"))
        {
            gdouble rgb[3];

            gegl_color_get_pixel (color, babl_format_with_space ("RGB double", space), rgb);

            oog = ((rgb[0] < 0.0 && -rgb[0] > CHANNEL_EPSILON)      ||
                   (rgb[0] > 1.0 && rgb[0] - 1.0 > CHANNEL_EPSILON) ||
                   (rgb[1] < 0.0 && -rgb[1] > CHANNEL_EPSILON)      ||
                   (rgb[1] > 1.0 && rgb[1] - 1.0 > CHANNEL_EPSILON) ||
                   (rgb[2] < 0.0 && -rgb[2] > CHANNEL_EPSILON)      ||
                   (rgb[2] > 1.0 && rgb[2] - 1.0 > CHANNEL_EPSILON));
        }
        else if (model == babl_model ("Y'")  ||
                 model == babl_model ("Y~")  ||
                 model == babl_model ("Y")   ||
                 model == babl_model ("Y'A") ||
                 model == babl_model ("Y~A") ||
                 model == babl_model ("YA"))
        {
            gdouble gray[1];

            gegl_color_get_pixel (color, babl_format_with_space ("Y double", space), gray);
            oog = ((gray[0] < 0.0 && -gray[0] > CHANNEL_EPSILON)      ||
                   (gray[0] > 1.0 && gray[0] - 1.0 > CHANNEL_EPSILON));
        }
        else if (model == babl_model ("CMYK")  ||
                 model == babl_model ("CMYKA") ||
                 model == babl_model ("cmyk")  ||
                 model == babl_model ("cmykA"))
        {
            gfloat cmyk[4];

            gegl_color_get_pixel (color, babl_format_with_space ("CMYK float", space), cmyk);
            oog = ((cmyk[0] < 0.0 && -cmyk[0] > CHANNEL_EPSILON)      ||
                   (cmyk[0] > 1.0 && cmyk[0] - 1.0 > CHANNEL_EPSILON) ||
                   (cmyk[1] < 0.0 && -cmyk[1] > CHANNEL_EPSILON)      ||
                   (cmyk[1] > 1.0 && cmyk[1] - 1.0 > CHANNEL_EPSILON) ||
                   (cmyk[2] < 0.0 && -cmyk[2] > CHANNEL_EPSILON)      ||
                   (cmyk[2] > 1.0 && cmyk[2] - 1.0 > CHANNEL_EPSILON) ||
                   (cmyk[3] < 0.0 && -cmyk[3] > CHANNEL_EPSILON)      ||
                   (cmyk[3] > 1.0 && cmyk[3] - 1.0 > CHANNEL_EPSILON));
        }
#undef CHANNEL_EPSILON
    }

  return oog;
}

/**
 * gimp_color_is_out_of_gamut:
 * @color: a [class@Gegl.Color]
 * @space: a color space to convert @color to.
 *
 * Determine whether @color is out of its @space gamut.
 * A small error of margin is accepted, so that for instance a component
 * at -0.0000001 is not making the whole color to be considered as
 * out-of-gamut while it may just be computation imprecision.
 *
 * Returns: whether the color is out of @space gamut.
 *
 * Since: 3.0
 **/
gboolean
gimp_color_is_out_of_gamut (GeglColor  *color,
                            const Babl *space)
{
  gboolean is_out_of_gamut = FALSE;

#define CHANNEL_EPSILON 1e-3
  if (babl_space_is_gray (space))
    {
      gfloat gray[1];

      gegl_color_get_pixel (color,
                            babl_format_with_space ("Y' float", space),
                            gray);
      is_out_of_gamut = ((gray[0] < 0.0 && -gray[0] > CHANNEL_EPSILON)       ||
                         (gray[0] > 1.0 && gray[0] - 1.0 > CHANNEL_EPSILON));

      if (! is_out_of_gamut)
        {
          gdouble rgb[3];

          /* Grayscale colors can be out of gamut if the color is out of the [0;
           * 1] range in the target space and also if they can be converted to
           * RGB with non-equal components.
           */
          gegl_color_get_pixel (color,
                                babl_format_with_space ("R'G'B' double", space),
                                rgb);
          is_out_of_gamut = (ABS (rgb[0] - rgb[0]) > CHANNEL_EPSILON ||
                             ABS (rgb[1] - rgb[1]) > CHANNEL_EPSILON ||
                             ABS (rgb[2] - rgb[2]) > CHANNEL_EPSILON);
        }
    }
  else if (babl_space_is_cmyk (space))
    {
      GeglColor *c = gegl_color_new (NULL);
      gfloat     cmyk[4];

      /* CMYK conversion always produces colors in [0; 1] range. What we want
       * to check is whether the source and converted colors are the same in
       * Lab space.
       */
      gegl_color_get_pixel (color,
                            babl_format_with_space ("CMYK float", space),
                            cmyk);
      gegl_color_set_pixel (c, babl_format_with_space ("CMYK float", space), cmyk);
      is_out_of_gamut = (! gimp_color_is_perceptually_identical (color, c));
      g_object_unref (c);
    }
  else
    {
      gdouble rgb[3];

      gegl_color_get_pixel (color,
                            babl_format_with_space ("R'G'B' double", space),
                            rgb);
      is_out_of_gamut = ((rgb[0] < 0.0 && -rgb[0] > CHANNEL_EPSILON)       ||
                         (rgb[0] > 1.0 && rgb[0] - 1.0 > CHANNEL_EPSILON) ||
                         (rgb[1] < 0.0 && -rgb[1] > CHANNEL_EPSILON)       ||
                         (rgb[1] > 1.0 && rgb[1] - 1.0 > CHANNEL_EPSILON) ||
                         (rgb[2] < 0.0 && -rgb[2] > CHANNEL_EPSILON)       ||
                         (rgb[2] > 1.0 && rgb[2] - 1.0 > CHANNEL_EPSILON));
    }
#undef CHANNEL_EPSILON

  return is_out_of_gamut;
}


/*
 * GIMP_TYPE_PARAM_COLOR
 */

#define GIMP_PARAM_SPEC_COLOR(pspec)    (G_TYPE_CHECK_INSTANCE_CAST ((pspec), GIMP_TYPE_PARAM_COLOR, GimpParamSpecColor))

typedef struct _GimpParamSpecColor GimpParamSpecColor;

struct _GimpParamSpecColor
{
  GimpParamSpecObject  parent_instance;

  gboolean             has_alpha;

  /* TODO: these 2 settings are not currently settable:
   * - none_ok: whether a parameter were to allow NULL as a value. Of course, it
   *   should imply that default_color must be set.
   * - validate: legacy GimpRGB code was implying checking if the RGB values
   *             were out of [0; 1], i.e. that new code should check if the
   *             color is out of self-gamut (bounded value).
   *             We could also add a check for invalid values regardless of
   *             gamut (though maybe this validation should happen regardless
   *             and the settings should just be oog_validate).
   * These can be implemented later as independent functions, especially as the
   * GimpParamSpecColor struct is private.
   */
  gboolean              none_ok;
  gboolean              validate;
};

static void         gimp_param_color_class_init     (GimpParamSpecObjectClass *klass);
static void         gimp_param_color_init           (GParamSpec               *pspec);
static GParamSpec * gimp_param_color_duplicate      (GParamSpec               *pspec);
static gboolean     gimp_param_color_validate       (GParamSpec               *pspec,
                                                     GValue                   *value);
static void         gimp_param_color_set_default    (GParamSpec               *pspec,
                                                     GValue                   *value);
static gint         gimp_param_color_cmp            (GParamSpec               *param_spec,
                                                     const GValue             *value1,
                                                     const GValue             *value2);

GType
gimp_param_color_get_type (void)
{
  static GType type = 0;

  if (G_UNLIKELY (type == 0))
    {
      const GTypeInfo info =
      {
        sizeof (GimpParamSpecObjectClass),
        NULL, NULL,
        (GClassInitFunc) gimp_param_color_class_init,
        NULL, NULL,
        sizeof (GimpParamSpecColor),
        0,
        (GInstanceInitFunc) gimp_param_color_init
      };

      type = g_type_register_static (GIMP_TYPE_PARAM_OBJECT, "GimpParamColor", &info, 0);
    }

  return type;
}

static void
gimp_param_color_class_init (GimpParamSpecObjectClass *klass)
{
  GParamSpecClass *pclass = G_PARAM_SPEC_CLASS (klass);

  klass->duplicate          = gimp_param_color_duplicate;

  pclass->value_type        = GEGL_TYPE_COLOR;
  pclass->value_validate    = gimp_param_color_validate;
  pclass->value_set_default = gimp_param_color_set_default;
  pclass->values_cmp        = gimp_param_color_cmp;
}

static void
gimp_param_color_init (GParamSpec *pspec)
{
  GimpParamSpecColor *cspec = GIMP_PARAM_SPEC_COLOR (pspec);

  cspec->has_alpha     = TRUE;
  cspec->none_ok       = TRUE;
  cspec->validate      = FALSE;
}

static GParamSpec *
gimp_param_color_duplicate (GParamSpec *pspec)
{
  GParamSpec         *duplicate;
  GimpParamSpecColor *cspec;

  g_return_val_if_fail (GIMP_IS_PARAM_SPEC_COLOR (pspec), NULL);

  cspec = GIMP_PARAM_SPEC_COLOR (pspec);
  duplicate = gimp_param_spec_color (pspec->name,
                                     g_param_spec_get_nick (pspec),
                                     g_param_spec_get_blurb (pspec),
                                     cspec->has_alpha,
                                     GEGL_COLOR (gimp_param_spec_object_get_default (pspec)),
                                     pspec->flags);

  return duplicate;
}

static gboolean
gimp_param_color_validate (GParamSpec *pspec,
                           GValue     *value)
{
  GimpParamSpecColor *cspec = GIMP_PARAM_SPEC_COLOR (pspec);
  GeglColor          *color = value->data[0].v_pointer;

  if (! cspec->none_ok && color == NULL)
    return TRUE;

  if (color && ! GEGL_IS_COLOR (color))
    {
      g_object_unref (color);
      value->data[0].v_pointer = NULL;
      return TRUE;
    }

  if (cspec->validate && gimp_color_is_out_of_self_gamut (color))
    {
      /* TODO: See g_param_value_validate() documentation. The value_validate()
       * method must also modify the value to ensure validity. When it's done,
       * return TRUE.
       */
      return FALSE;
    }
  return FALSE;
}

static void
gimp_param_color_set_default (GParamSpec *pspec,
                              GValue     *value)
{
  GeglColor *color;

  color = GEGL_COLOR (gimp_param_spec_object_get_default (pspec));
  if (color)
    g_value_take_object (value, gegl_color_duplicate (color));
}

static gint
gimp_param_color_cmp (GParamSpec   *param_spec,
                      const GValue *value1,
                      const GValue *value2)
{
  GeglColor  *color1 = g_value_get_object (value1);
  GeglColor  *color2 = g_value_get_object (value2);
  const Babl *format1;

  if (! color1 || ! color2)
    return color2 ? -1 : (color1 ? 1 : 0);

  format1 = gegl_color_get_format (color1);
  if (format1 != gegl_color_get_format (color2))
    {
      return 1;
    }
  else
    {
      guint8 pixel1[48];
      guint8 pixel2[48];

      gegl_color_get_pixel (color1, format1, pixel1);
      gegl_color_get_pixel (color2, format1, pixel2);

      return memcmp (pixel1, pixel2, babl_format_get_bytes_per_pixel (format1));
    }
}

/**
 * gimp_param_spec_color:
 * @name: canonical name of the property specified
 * @nick: nick name for the property specified
 * @blurb: description of the property specified
 * @has_alpha: %TRUE if the alpha channel has relevance.
 * @default_color: the default value for the property specified
 * @flags: flags for the property specified
 *
 * Creates a new #GParamSpec instance specifying a #GeglColor property.
 * Note that the @default_color is duplicated, so reusing object will
 * not change the default color of the returned %GimpParamSpecColor.
 *
 * Returns: (transfer full): a newly created parameter specification
 */
GParamSpec *
gimp_param_spec_color (const gchar *name,
                       const gchar *nick,
                       const gchar *blurb,
                       gboolean     has_alpha,
                       GeglColor   *default_color,
                       GParamFlags  flags)
{
  GimpParamSpecColor *cspec;
  GeglColor          *dup_color = NULL;

  cspec = g_param_spec_internal (GIMP_TYPE_PARAM_COLOR, name, nick, blurb, flags);

  if (default_color)
    dup_color = gegl_color_duplicate (default_color);

  gimp_param_spec_object_set_default (G_PARAM_SPEC (cspec), G_OBJECT (dup_color));
  g_clear_object (&dup_color);

  cspec->has_alpha = has_alpha;

  return G_PARAM_SPEC (cspec);
}

/**
 * gimp_param_spec_color_from_string:
 * @name: canonical name of the property specified
 * @nick: nick name for the property specified
 * @blurb: description of the property specified
 * @has_alpha: %TRUE if the alpha channel has relevance.
 * @default_color_string: the default value for the property specified
 * @flags: flags for the property specified
 *
 * Creates a new #GParamSpec instance specifying a #GeglColor property.
 *
 * Returns: (transfer full): a newly created parameter specification
 */
GParamSpec *
gimp_param_spec_color_from_string (const gchar *name,
                                   const gchar *nick,
                                   const gchar *blurb,
                                   gboolean     has_alpha,
                                   const gchar *default_color_string,
                                   GParamFlags  flags)
{
  GimpParamSpecColor *cspec;
  GeglColor          *default_color;

  cspec = g_param_spec_internal (GIMP_TYPE_PARAM_COLOR,
                                 name, nick, blurb, flags);

  default_color = g_object_new (GEGL_TYPE_COLOR,
                                "string", default_color_string,
                                NULL);
  gimp_param_spec_object_set_default (G_PARAM_SPEC (cspec), G_OBJECT (default_color));
  cspec->has_alpha = has_alpha;

  g_clear_object (&default_color);

  return G_PARAM_SPEC (cspec);
}

/**
 * gimp_param_spec_color_has_alpha:
 * @pspec: a #GParamSpec to hold an #GeglColor value.
 *
 * Returns: %TRUE if the alpha channel is relevant.
 *
 * Since: 2.4
 **/
gboolean
gimp_param_spec_color_has_alpha (GParamSpec *pspec)
{
  g_return_val_if_fail (GIMP_IS_PARAM_SPEC_COLOR (pspec), FALSE);

  return GIMP_PARAM_SPEC_COLOR (pspec)->has_alpha;
}


/* Private functions. */

static const Babl *
gimp_babl_format_get_with_alpha (const Babl *format)
{
  const Babl  *new_format = NULL;
  const gchar *new_model  = NULL;
  const gchar *model;
  const gchar *type;
  gchar       *name;

  if (babl_format_has_alpha (format))
    return format;

  model = babl_get_name (babl_format_get_model (format));

  /* Assuming we use Babl formats with same type for all components. */
  type  = babl_get_name (babl_format_get_type (format, 0));

  if (babl_format_is_palette (format))
    {
      gchar *alpha_palette = g_strdup (model);
      gchar *last_hyphen;

      /* Retrieving the alpha variant of the same palette.
       * 1. The alpha variant starts with '\'.
       * 2. Removing the last part of the name which represents the
       *    space because babl will add it itself.
       */
      alpha_palette[0] = '\\';
      last_hyphen = g_strrstr (alpha_palette, "-");
      if (last_hyphen != NULL)
        *last_hyphen = '\0';
      babl_new_palette_with_space (alpha_palette, babl_format_get_space (format),
                                   NULL, &new_format);
      g_free (alpha_palette);

      return new_format;
    }

  if (g_strcmp0 (model, "Y") == 0)
    new_model = "YA";
  else if (g_strcmp0 (model, "RGB") == 0)
    new_model = "RGBA";
  else if (g_strcmp0 (model, "Y'") == 0)
    new_model = "Y'A";
  else if (g_strcmp0 (model, "R'G'B'") == 0)
    new_model = "R'G'B'A";
  else if (g_strcmp0 (model, "Y~") == 0)
    new_model = "Y~A";
  else if (g_strcmp0 (model, "R~G~B~") == 0)
    new_model = "R~G~B~A";
  else if (g_strcmp0 (model, "CIE Lab") == 0)
    new_model = "CIE Lab alpha";
  else if (g_strcmp0 (model, "CIE xyY") == 0)
    new_model = "CIE xyY alpha";
  else if (g_strcmp0 (model, "CIE XYZ") == 0)
    new_model = "CIE XYZ alpha";
  else if (g_strcmp0 (model, "CIE Yuv") == 0)
    new_model = "CIE Yuv alpha";
  else if (g_strcmp0 (model, "CIE LCH(ab)") == 0)
    new_model = "CIE LCH(ab) alpha";
  else if (g_strcmp0 (model, "CMYK") == 0)
    new_model = "CMYKA";
  else if (g_strcmp0 (model, "cmyk") == 0)
    new_model = "cmykA";
  else if (g_strcmp0 (model, "HSL") == 0)
    new_model = "HSLA";
  else if (g_strcmp0 (model, "HSV") == 0)
    new_model = "HSVA";
  else if (g_strcmp0 (model, "cairo-RGB24") == 0)
    new_model = "cairo-ARGB32";

  if (new_model == NULL)
    {
      g_warning ("%s: unsupported format \"%s\".", G_STRFUNC, babl_get_name (format));
      return format;
    }

  name = g_strdup_printf ("%s %s", new_model, type);
  new_format = babl_format_with_space (name, format);
  g_free (name);

  return new_format;
}

/**
 * gimp_color_get_CIE2000_distance:
 * @color1: a [class@Gegl.Color]
 * @color2: a [class@Gegl.Color]
 *
 * Compute the CIEDE2000 distance between @color1 and @color2 which tries to
 * measure visual difference in the CIELAB color space while correcting the
 * computation to take into account the space being not perfectly perceptual
 * uniform.
 *
 * This function does not take into account any transparency channel.
 *
 * Returns: the distance computed using the CIEDE2000 algorithm.
 *
 * Since: 3.0
 **/
static gfloat
gimp_color_get_CIE2000_distance (GeglColor *color1,
                                 GeglColor *color2)
{
  gfloat lab1[3];
  gfloat lab2[3];
  gfloat dL;
  gfloat C_prime;
  gfloat dC;
  gfloat dh;
  gfloat dH;
  gfloat h_prime;
  gfloat T;
  gfloat L_50_2;
  gfloat SL;
  gfloat SC;
  gfloat SH;
  gfloat C_prime7;
  gfloat RT;
  gfloat dE00;
  gfloat RC;
  gfloat d0;

  g_return_val_if_fail (GEGL_IS_COLOR (color1), FALSE);
  g_return_val_if_fail (GEGL_IS_COLOR (color2), FALSE);

  gegl_color_get_pixel (color1, babl_format ("CIE LCH(ab) float"), lab1);
  gegl_color_get_pixel (color2, babl_format ("CIE LCH(ab) float"), lab2);

  dL = lab2[0] - lab1[0];
  dC = lab2[1] - lab1[1];
  dh = lab2[2] - lab1[2];
  dH = 2.f * sqrtf (lab1[1] * lab2[1]) * sinf (dh / 2.0f * M_PI / 180.f);

  h_prime = lab1[2] + lab2[2] ;
  if (lab1[1] * lab2[1] != 0.f)
    {
      if (fabsf (dh) <= 180.0f)
        {
          h_prime /= 2.0f;
        }
      else
        {
          if (h_prime < 360.f)
            h_prime = (h_prime + 360.f) / 2.f;
          else
            h_prime = (h_prime - 360.f) / 2.f;
        }
    }
  T = 1.f - 0.17f * cosf ((h_prime - 30.f) * M_PI / 180.f) + 0.24f * cosf (2.f * h_prime * M_PI / 180.f) +
      0.32f * cosf ((3.f * h_prime + 6.f) * M_PI / 180.f) - 0.2f * cosf ((4.f * h_prime - 63.f) * M_PI / 180.f);
  C_prime = (lab1[1] + lab2[1]) / 2.f;
  L_50_2 = (((lab1[0] + lab2[0]) / 2.f) - 50.f);
  L_50_2 *= L_50_2;
  SL = 1.f + 0.015f * L_50_2 / sqrtf (20.f + L_50_2);
  SC = 1.f + 0.045f * C_prime;
  SH = 1.f + 0.015f * C_prime * T;

  C_prime7 = powf (C_prime, 7.f);
  d0 = 30.f * expf (- powf ((h_prime - 275.f) / 25.f, 2.f));
#define CONST_25_POWER_7 6103515625.0f
  RC = 2.f * sqrtf (C_prime7  / (C_prime7 + CONST_25_POWER_7));
#undef CONST_25_POWER_7
  RT = - sinf (2.f * d0 * M_PI / 180.f) * RC;
  dE00 = sqrtf (powf (dL / SL, 2.f) + powf (dC / SC, 2.f) + powf (dH / SH, 2.f) +
                RT * dC * dH / SC / SH);

  return dE00;
}


/*
 * GIMP_TYPE_BABL_FORMAT
 */

static const Babl * gimp_babl_object_copy (const Babl *object);
static void         gimp_babl_object_free (const Babl *object);

G_DEFINE_BOXED_TYPE (GimpBablFormat, gimp_babl_format, (GBoxedCopyFunc) gimp_babl_object_copy, (GBoxedFreeFunc) gimp_babl_object_free)

/**
 * gimp_babl_object_copy: (skip)
 * @object: a Babl object.
 *
 * Bogus function since [struct@Babl.Object] should just be used as
 * never-ending pointers.
 *
 * Returns: (transfer none): the passed @object.
 **/
const Babl *
gimp_babl_object_copy (const Babl *object)
{
  return object;
}

/**
 * gimp_babl_object_free: (skip)
 * @object: a Babl object.
 *
 * Bogus function since [struct@Babl.Object] must not be freed.
 **/
void
gimp_babl_object_free (const Babl *object)
{
}

/* --- end libammoos/core/fieldcolor/gimpcolor.c --- */

/* --- begin libammoos/core/fieldcolor/gimpcolormanaged.c --- */
/* LIBGIMP - The AmmoOS Image Library
 * Copyright (C) 1995-1997 Spencer Kimball and Peter Mattis
 *
 * GimpColorManaged interface
 * Copyright (C) 2007  Sven Neumann <sven@ammoos.org>
 *
 * This library is free software: you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 3 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Library General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library.  If not, see
 * <https://www.gnu.org/licenses/>.
 */

#include "config.h"

#include <gio/gio.h>
#include <gegl.h>

#include "gimpcolortypes.h"

#include "gimpcolormanaged.h"
#include "gimpcolorprofile.h"


/**
 * SECTION: gimpcolormanaged
 * @title: GimpColorManaged
 * @short_description: An interface dealing with color profiles.
 *
 * An interface dealing with color profiles.
 **/


enum
{
  PROFILE_CHANGED,
  SIMULATION_PROFILE_CHANGED,
  SIMULATION_INTENT_CHANGED,
  SIMULATION_BPC_CHANGED,
  LAST_SIGNAL
};


G_DEFINE_INTERFACE (GimpColorManaged, gimp_color_managed, G_TYPE_OBJECT)


static guint gimp_color_managed_signals[LAST_SIGNAL] = { 0 };


/*  private functions  */


static void
gimp_color_managed_default_init (GimpColorManagedInterface *iface)
{
  gimp_color_managed_signals[PROFILE_CHANGED] =
    g_signal_new ("profile-changed",
                  G_TYPE_FROM_INTERFACE (iface),
                  G_SIGNAL_RUN_FIRST,
                  G_STRUCT_OFFSET (GimpColorManagedInterface,
                                   profile_changed),
                  NULL, NULL, NULL,
                  G_TYPE_NONE, 0);

  gimp_color_managed_signals[SIMULATION_PROFILE_CHANGED] =
    g_signal_new ("simulation-profile-changed",
                  G_TYPE_FROM_INTERFACE (iface),
                  G_SIGNAL_RUN_FIRST,
                  G_STRUCT_OFFSET (GimpColorManagedInterface,
                                   simulation_profile_changed),
                  NULL, NULL, NULL,
                  G_TYPE_NONE, 0);

  gimp_color_managed_signals[SIMULATION_INTENT_CHANGED] =
    g_signal_new ("simulation-intent-changed",
                  G_TYPE_FROM_INTERFACE (iface),
                  G_SIGNAL_RUN_FIRST,
                  G_STRUCT_OFFSET (GimpColorManagedInterface,
                                   simulation_intent_changed),
                  NULL, NULL, NULL,
                  G_TYPE_NONE, 0);

  gimp_color_managed_signals[SIMULATION_BPC_CHANGED] =
    g_signal_new ("simulation-bpc-changed",
                  G_TYPE_FROM_INTERFACE (iface),
                  G_SIGNAL_RUN_FIRST,
                  G_STRUCT_OFFSET (GimpColorManagedInterface,
                                   simulation_bpc_changed),
                  NULL, NULL, NULL,
                  G_TYPE_NONE, 0);
}


/*  public functions  */


/**
 * gimp_color_managed_get_icc_profile:
 * @managed: an object the implements the #GimpColorManaged interface
 * @len: (out): return location for the number of bytes in the profile data
 *
 * Returns: (array length=len): A blob of data that represents an ICC color
 *                              profile.
 *
 * Since: 2.4
 */
const guint8 *
gimp_color_managed_get_icc_profile (GimpColorManaged *managed,
                                    gsize            *len)
{
  GimpColorManagedInterface *iface;

  g_return_val_if_fail (GIMP_IS_COLOR_MANAGED (managed), NULL);
  g_return_val_if_fail (len != NULL, NULL);

  *len = 0;

  iface = GIMP_COLOR_MANAGED_GET_IFACE (managed);

  if (iface->get_icc_profile)
    return iface->get_icc_profile (managed, len);

  return NULL;
}

/**
 * gimp_color_managed_get_color_profile:
 * @managed: an object the implements the #GimpColorManaged interface
 *
 * This function always returns a #GimpColorProfile and falls back to
 * gimp_color_profile_new_rgb_srgb() if the method is not implemented.
 *
 * Returns: (transfer full): The @managed's #GimpColorProfile.
 *
 * Since: 2.10
 **/
GimpColorProfile *
gimp_color_managed_get_color_profile (GimpColorManaged *managed)
{
  GimpColorManagedInterface *iface;

  g_return_val_if_fail (GIMP_IS_COLOR_MANAGED (managed), NULL);

  iface = GIMP_COLOR_MANAGED_GET_IFACE (managed);

  if (iface->get_color_profile)
    return iface->get_color_profile (managed);

  return NULL;
}

/**
 * gimp_color_managed_get_simulation_profile:
 * @managed: an object the implements the #GimpColorManaged interface
 *
 * This function always returns a #GimpColorProfile
 *
 * Returns: (transfer full): The @managed's simulation #GimpColorProfile.
 *
 * Since: 3.0
 **/
GimpColorProfile *
gimp_color_managed_get_simulation_profile (GimpColorManaged *managed)
{
  GimpColorManagedInterface *iface;

  g_return_val_if_fail (GIMP_IS_COLOR_MANAGED (managed), NULL);

  iface = GIMP_COLOR_MANAGED_GET_IFACE (managed);

  if (iface->get_simulation_profile)
    return iface->get_simulation_profile (managed);

  return NULL;
}

/**
 * gimp_color_managed_get_simulation_intent:
 * @managed: an object the implements the #GimpColorManaged interface
 *
 * This function always returns a #GimpColorRenderingIntent
 *
 * Returns: The @managed's simulation #GimpColorRenderingIntent.
 *
 * Since: 3.0
 **/
GimpColorRenderingIntent
gimp_color_managed_get_simulation_intent (GimpColorManaged *managed)
{
  GimpColorManagedInterface *iface;

  g_return_val_if_fail (GIMP_IS_COLOR_MANAGED (managed),
                        GIMP_COLOR_RENDERING_INTENT_RELATIVE_COLORIMETRIC);

  iface = GIMP_COLOR_MANAGED_GET_IFACE (managed);

  if (iface->get_simulation_intent)
    return iface->get_simulation_intent (managed);

  return GIMP_COLOR_RENDERING_INTENT_RELATIVE_COLORIMETRIC;
}

/**
 * gimp_color_managed_get_simulation_bpc:
 * @managed: an object the implements the #GimpColorManaged interface
 *
 * This function always returns a gboolean representing whether
 * Black Point Compensation is enabled
 *
 * Returns: The @managed's simulation Black Point Compensation value.
 *
 * Since: 3.0
 **/
gboolean
gimp_color_managed_get_simulation_bpc (GimpColorManaged *managed)
{
  GimpColorManagedInterface *iface;

  g_return_val_if_fail (GIMP_IS_COLOR_MANAGED (managed), FALSE);

  iface = GIMP_COLOR_MANAGED_GET_IFACE (managed);

  if (iface->get_simulation_bpc)
    return iface->get_simulation_bpc (managed);

  return FALSE;
}


/**
 * gimp_color_managed_profile_changed:
 * @managed: an object that implements the #GimpColorManaged interface
 *
 * Emits the "profile-changed" signal.
 *
 * Since: 2.4
 **/
void
gimp_color_managed_profile_changed (GimpColorManaged *managed)
{
  g_return_if_fail (GIMP_IS_COLOR_MANAGED (managed));

  g_signal_emit (managed, gimp_color_managed_signals[PROFILE_CHANGED], 0);
}

/**
 * gimp_color_managed_simulation_profile_changed:
 * @managed: an object that implements the #GimpColorManaged interface
 *
 * Emits the "simulation-profile-changed" signal.
 *
 * Since: 3.0
 **/
void
gimp_color_managed_simulation_profile_changed (GimpColorManaged *managed)
{
  g_return_if_fail (GIMP_IS_COLOR_MANAGED (managed));

  g_signal_emit (managed, gimp_color_managed_signals[SIMULATION_PROFILE_CHANGED], 0);
}

/**
 * gimp_color_managed_simulation_intent_changed:
 * @managed: an object that implements the #GimpColorManaged interface
 *
 * Emits the "simulation-intent-changed" signal.
 *
 * Since: 3.0
 **/
void
gimp_color_managed_simulation_intent_changed (GimpColorManaged *managed)
{
  g_return_if_fail (GIMP_IS_COLOR_MANAGED (managed));

  g_signal_emit (managed, gimp_color_managed_signals[SIMULATION_INTENT_CHANGED], 0);
}

/**
 * gimp_color_managed_simulation_bpc_changed:
 * @managed: an object that implements the #GimpColorManaged interface
 *
 * Emits the "simulation-bpc-changed" signal.
 *
 * Since: 3.0
 **/
void
gimp_color_managed_simulation_bpc_changed (GimpColorManaged *managed)
{
  g_return_if_fail (GIMP_IS_COLOR_MANAGED (managed));

  g_signal_emit (managed, gimp_color_managed_signals[SIMULATION_BPC_CHANGED], 0);
}

/* --- end libammoos/core/fieldcolor/gimpcolormanaged.c --- */

/* --- begin libammoos/core/fieldcolor/gimpcolorprofile.c --- */
/* LIBGIMP - The AmmoOS Image Library
 * Copyright (C) 1995-1997 Spencer Kimball and Peter Mattis
 *
 * gimpcolorprofile.c
 * Copyright (C) 2014  Michael Natterer <mitch@ammoos.org>
 *                     Elle Stone <ellestone@ninedegreesbelow.com>
 *                     Øyvind Kolås <pippin@ammoos.org>
 *
 * This library is free software: you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 3 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Library General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library.  If not, see
 * <https://www.gnu.org/licenses/>.
 */

#include "config.h"

#include <string.h>

#include <lcms2.h>

#include <gio/gio.h>
#include <gegl.h>

#include "libgimpbase/gimpbase.h"

#include "gimpcolortypes.h"

#include "gimpcolorprofile.h"

#include "libgimp/libgimp-intl.h"


#ifndef TYPE_RGBA_DBL
#define TYPE_RGBA_DBL       (FLOAT_SH(1)|COLORSPACE_SH(PT_RGB)|EXTRA_SH(1)|CHANNELS_SH(3)|BYTES_SH(0))
#endif

#ifndef TYPE_GRAYA_HALF_FLT
#define TYPE_GRAYA_HALF_FLT (FLOAT_SH(1)|COLORSPACE_SH(PT_GRAY)|EXTRA_SH(1)|CHANNELS_SH(1)|BYTES_SH(2))
#endif

#ifndef TYPE_GRAYA_FLT
#define TYPE_GRAYA_FLT      (FLOAT_SH(1)|COLORSPACE_SH(PT_GRAY)|EXTRA_SH(1)|CHANNELS_SH(1)|BYTES_SH(4))
#endif

#ifndef TYPE_GRAYA_DBL
#define TYPE_GRAYA_DBL      (FLOAT_SH(1)|COLORSPACE_SH(PT_GRAY)|EXTRA_SH(1)|CHANNELS_SH(1)|BYTES_SH(0))
#endif

#ifndef TYPE_CMYKA_DBL
#define TYPE_CMYKA_DBL      (FLOAT_SH(1)|COLORSPACE_SH(PT_CMYK)|EXTRA_SH(1)|CHANNELS_SH(4)|BYTES_SH(0))
#endif

#ifndef TYPE_CMYKA_HALF_FLT
#define TYPE_CMYKA_HALF_FLT (FLOAT_SH(1)|COLORSPACE_SH(PT_CMYK)|EXTRA_SH(1)|CHANNELS_SH(4)|BYTES_SH(2))
#endif

#ifndef TYPE_CMYKA_FLT
#define TYPE_CMYKA_FLT      (FLOAT_SH(1)|COLORSPACE_SH(PT_CMYK)|EXTRA_SH(1)|CHANNELS_SH(4)|BYTES_SH(4))
#endif

#ifndef TYPE_CMYKA_16
#define TYPE_CMYKA_16       (COLORSPACE_SH(PT_CMYK)|EXTRA_SH(1)|CHANNELS_SH(4)|BYTES_SH(2))
#endif


/**
 * SECTION: gimpcolorprofile
 * @title: GimpColorProfile
 * @short_description: Definitions and Functions relating to LCMS.
 *
 * Definitions and Functions relating to LCMS.
 **/

/**
 * GimpColorProfile:
 *
 * Simply a typedef to #gpointer, but actually is a cmsHPROFILE. It's
 * used in public AmmoOS Image APIs in order to avoid having to include LCMS
 * headers.
 **/


struct _GimpColorProfile
{
  GObject      parent_instance;

  cmsHPROFILE  lcms_profile;
  guint8      *data;
  gsize        length;

  gchar       *description;
  gchar       *manufacturer;
  gchar       *model;
  gchar       *copyright;
  gchar       *label;
  gchar       *summary;
};


static void   gimp_color_profile_finalize (GObject *object);


G_DEFINE_TYPE (GimpColorProfile, gimp_color_profile, G_TYPE_OBJECT)

#define parent_class gimp_color_profile_parent_class


#define GIMP_COLOR_PROFILE_ERROR gimp_color_profile_error_quark ()

static GQuark
gimp_color_profile_error_quark (void)
{
  static GQuark quark = 0;

  if (G_UNLIKELY (quark == 0))
    quark = g_quark_from_static_string ("ammoos-color-profile-error-quark");

  return quark;
}

static void
gimp_color_profile_class_init (GimpColorProfileClass *klass)
{
  GObjectClass *object_class = G_OBJECT_CLASS (klass);

  object_class->finalize = gimp_color_profile_finalize;
}

static void
gimp_color_profile_init (GimpColorProfile *profile)
{
}

static void
gimp_color_profile_finalize (GObject *object)
{
  GimpColorProfile *profile = GIMP_COLOR_PROFILE (object);

  g_clear_pointer (&profile->lcms_profile, cmsCloseProfile);

  g_clear_pointer (&profile->data, g_free);
  profile->length = 0;

  g_clear_pointer (&profile->description,  g_free);
  g_clear_pointer (&profile->manufacturer, g_free);
  g_clear_pointer (&profile->model,        g_free);
  g_clear_pointer (&profile->copyright,    g_free);
  g_clear_pointer (&profile->label,        g_free);
  g_clear_pointer (&profile->summary,      g_free);

  G_OBJECT_CLASS (parent_class)->finalize (object);
}


/**
 * gimp_color_profile_new_from_file:
 * @file:  a #GFile
 * @error: return location for #GError
 *
 * This function opens an ICC color profile from @file.
 *
 * Returns: (nullable): the #GimpColorProfile, or %NULL. On error, %NULL is
 *               returned and @error is set.
 *
 * Since: 2.10
 **/
GimpColorProfile *
gimp_color_profile_new_from_file (GFile   *file,
                                  GError **error)
{
  GimpColorProfile *profile      = NULL;
  cmsHPROFILE       lcms_profile = NULL;
  guint8           *data         = NULL;
  gsize             length       = 0;
  gchar            *path;

  g_return_val_if_fail (G_IS_FILE (file), NULL);
  g_return_val_if_fail (error == NULL || *error == NULL, NULL);

  path = g_file_get_path (file);

  if (path)
    {
      GMappedFile *mapped;

      mapped = g_mapped_file_new (path, FALSE, error);
      g_free (path);

      if (! mapped)
        return NULL;

      length = g_mapped_file_get_length (mapped);
      data   = g_memdup2 (g_mapped_file_get_contents (mapped), length);

      lcms_profile = cmsOpenProfileFromMem (data, length);

      g_mapped_file_unref (mapped);
    }
  else
    {
      GFileInfo *info;

      info = g_file_query_info (file,
                                G_FILE_ATTRIBUTE_STANDARD_SIZE,
                                G_FILE_QUERY_INFO_NONE,
                                NULL, error);
      if (info)
        {
          GInputStream *input;

          length = g_file_info_get_attribute_uint64 (info, G_FILE_ATTRIBUTE_STANDARD_SIZE);
          data   = g_malloc (length);

          g_object_unref (info);

          input = G_INPUT_STREAM (g_file_read (file, NULL, error));

          if (input)
            {
              gsize bytes_read;

              if (g_input_stream_read_all (input, data, length,
                                           &bytes_read, NULL, error) &&
                  bytes_read == length)
                {
                  lcms_profile = cmsOpenProfileFromMem (data, length);
                }

              g_object_unref (input);
            }
        }
    }

  if (lcms_profile)
    {
      profile = g_object_new (GIMP_TYPE_COLOR_PROFILE, NULL);

      profile->lcms_profile = lcms_profile;
      profile->data         = data;
      profile->length       = length;
    }
  else
    {
      if (data)
        g_free (data);

      if (error && *error == NULL)
        {
          g_set_error (error, GIMP_COLOR_PROFILE_ERROR, 0,
                       _("'%s' does not appear to be an ICC color profile"),
                       gimp_file_get_utf8_name (file));
        }
    }

  return profile;
}

/**
 * gimp_color_profile_new_from_icc_profile:
 * @data: (array length=length): The memory containing an ICC profile
 * @length: length of the profile in memory, in bytes
 * @error:  return location for #GError
 *
 * This function opens an ICC color profile from memory. On error,
 * %NULL is returned and @error is set.
 *
 * Returns: (nullable): the #GimpColorProfile, or %NULL.
 *
 * Since: 2.10
 **/
GimpColorProfile *
gimp_color_profile_new_from_icc_profile (const guint8  *data,
                                         gsize          length,
                                         GError       **error)
{
  cmsHPROFILE       lcms_profile = 0;
  GimpColorProfile *profile      = NULL;

  g_return_val_if_fail (data != NULL || length == 0, NULL);
  g_return_val_if_fail (error == NULL || *error == NULL, NULL);

  if (length > 0)
    lcms_profile = cmsOpenProfileFromMem (data, length);

  if (lcms_profile)
    {
      profile = g_object_new (GIMP_TYPE_COLOR_PROFILE, NULL);

      profile->lcms_profile = lcms_profile;
      profile->data         = g_memdup2 (data, length);
      profile->length       = length;
    }
  else
    {
      g_set_error_literal (error, GIMP_COLOR_PROFILE_ERROR, 0,
                           _("Data does not appear to be an ICC color profile"));
    }

  return profile;
}

/**
 * gimp_color_profile_new_from_lcms_profile:
 * @lcms_profile: an LCMS cmsHPROFILE pointer
 * @error:        return location for #GError
 *
 * This function creates a GimpColorProfile from a cmsHPROFILE. On
 * error, %NULL is returned and @error is set. The passed
 * @lcms_profile pointer is not retained by the created
 * #GimpColorProfile.
 *
 * Returns: (nullable): the #GimpColorProfile, or %NULL.
 *
 * Since: 2.10
 **/
GimpColorProfile *
gimp_color_profile_new_from_lcms_profile (gpointer   lcms_profile,
                                          GError   **error)
{
  cmsUInt32Number size;

  g_return_val_if_fail (lcms_profile != NULL, NULL);
  g_return_val_if_fail (error == NULL || *error == NULL, NULL);

  if (cmsSaveProfileToMem (lcms_profile, NULL, &size))
    {
      guint8 *data = g_malloc (size);

      if (cmsSaveProfileToMem (lcms_profile, data, &size))
        {
          gsize length = size;

          lcms_profile = cmsOpenProfileFromMem (data, length);

          if (lcms_profile)
            {
              GimpColorProfile *profile;

              profile = g_object_new (GIMP_TYPE_COLOR_PROFILE, NULL);

              profile->lcms_profile = lcms_profile;
              profile->data         = data;
              profile->length       = length;

              return profile;
            }
        }

      g_free (data);
    }

  g_set_error_literal (error, GIMP_COLOR_PROFILE_ERROR, 0,
                       _("Could not save color profile to memory"));

  return NULL;
}

/**
 * gimp_color_profile_save_to_file:
 * @profile: a #GimpColorProfile
 * @file:    a #GFile
 * @error:   return location for #GError
 *
 * This function saves @profile to @file as ICC profile.
 *
 * Returns: %TRUE on success, %FALSE if an error occurred.
 *
 * Since: 2.10
 **/
gboolean
gimp_color_profile_save_to_file (GimpColorProfile  *profile,
                                 GFile             *file,
                                 GError           **error)
{
  g_return_val_if_fail (GIMP_IS_COLOR_PROFILE (profile), FALSE);
  g_return_val_if_fail (G_IS_FILE (file), FALSE);
  g_return_val_if_fail (error == NULL || *error == NULL, FALSE);

  return g_file_replace_contents (file,
                                  (const gchar *) profile->data,
                                  profile->length,
                                  NULL, FALSE,
                                  G_FILE_CREATE_NONE,
                                  NULL,
                                  NULL,
                                  error);
}

/**
 * gimp_color_profile_get_icc_profile:
 * @profile: a #GimpColorProfile
 * @length: (out): return location for the number of bytes
 *
 * This function returns @profile as ICC profile data. The returned
 * memory belongs to @profile and must not be modified or freed.
 *
 * Returns: (array length=length): a pointer to the IIC profile data.
 *
 * Since: 2.10
 **/
const guint8 *
gimp_color_profile_get_icc_profile (GimpColorProfile  *profile,
                                    gsize             *length)
{
  g_return_val_if_fail (GIMP_IS_COLOR_PROFILE (profile), NULL);
  g_return_val_if_fail (length != NULL, NULL);

  *length = profile->length;

  return profile->data;
}

/**
 * gimp_color_profile_get_lcms_profile:
 * @profile: a #GimpColorProfile
 *
 * This function returns @profile's cmsHPROFILE. The returned
 * value belongs to @profile and must not be modified or freed.
 *
 * Returns: a pointer to the cmsHPROFILE.
 *
 * Since: 2.10
 **/
gpointer
gimp_color_profile_get_lcms_profile (GimpColorProfile *profile)
{
  g_return_val_if_fail (GIMP_IS_COLOR_PROFILE (profile), NULL);

  return profile->lcms_profile;
}

static gchar *
gimp_color_profile_get_info (GimpColorProfile *profile,
                             cmsInfoType       info)
{
  cmsUInt32Number  size;
  gchar           *text = NULL;

  size = cmsGetProfileInfoASCII (profile->lcms_profile, info,
                                 "en", "US", NULL, 0);
  if (size > 0)
    {
      gchar *data = g_new (gchar, size + 1);

      size = cmsGetProfileInfoASCII (profile->lcms_profile, info,
                                     "en", "US", data, size);
      if (size > 0)
        text = gimp_any_to_utf8 (data, -1, NULL);

      g_free (data);
    }

  return text;
}

/**
 * gimp_color_profile_get_description:
 * @profile: a #GimpColorProfile
 *
 * Returns: a string containing @profile's description. The
 *               returned value belongs to @profile and must not be
 *               modified or freed.
 *
 * Since: 2.10
 **/
const gchar *
gimp_color_profile_get_description (GimpColorProfile *profile)
{
  g_return_val_if_fail (GIMP_IS_COLOR_PROFILE (profile), NULL);

  if (! profile->description)
    profile->description =
      gimp_color_profile_get_info (profile, cmsInfoDescription);

  return profile->description;
}

/**
 * gimp_color_profile_get_manufacturer:
 * @profile: a #GimpColorProfile
 *
 * Returns: a string containing @profile's manufacturer. The
 *               returned value belongs to @profile and must not be
 *               modified or freed.
 *
 * Since: 2.10
 **/
const gchar *
gimp_color_profile_get_manufacturer (GimpColorProfile *profile)
{
  g_return_val_if_fail (GIMP_IS_COLOR_PROFILE (profile), NULL);

  if (! profile->manufacturer)
    profile->manufacturer =
      gimp_color_profile_get_info (profile, cmsInfoManufacturer);

  return profile->manufacturer;
}

/**
 * gimp_color_profile_get_model:
 * @profile: a #GimpColorProfile
 *
 * Returns: a string containing @profile's model. The returned
 *               value belongs to @profile and must not be modified or
 *               freed.
 *
 * Since: 2.10
 **/
const gchar *
gimp_color_profile_get_model (GimpColorProfile *profile)
{
  g_return_val_if_fail (GIMP_IS_COLOR_PROFILE (profile), NULL);

  if (! profile->model)
    profile->model =
      gimp_color_profile_get_info (profile, cmsInfoModel);

  return profile->model;
}

/**
 * gimp_color_profile_get_copyright:
 * @profile: a #GimpColorProfile
 *
 * Returns: a string containing @profile's copyright. The
 *               returned value belongs to @profile and must not be
 *               modified or freed.
 *
 * Since: 2.10
 **/
const gchar *
gimp_color_profile_get_copyright (GimpColorProfile *profile)
{
  g_return_val_if_fail (GIMP_IS_COLOR_PROFILE (profile), NULL);

  if (! profile->copyright)
    profile->copyright =
      gimp_color_profile_get_info (profile, cmsInfoCopyright);

  return profile->copyright;
}

/**
 * gimp_color_profile_get_label:
 * @profile: a #GimpColorProfile
 *
 * This function returns a string containing @profile's "title", a
 * string that can be used to label the profile in a user interface.
 *
 * Unlike gimp_color_profile_get_description(), this function always
 * returns a string (as a fallback, it returns "(unnamed profile)").
 *
 * Returns: the @profile's label. The returned value belongs to
 *               @profile and must not be modified or freed.
 *
 * Since: 2.10
 **/
const gchar *
gimp_color_profile_get_label (GimpColorProfile *profile)
{

  g_return_val_if_fail (GIMP_IS_COLOR_PROFILE (profile), NULL);

  if (! profile->label)
    {
      const gchar *label = gimp_color_profile_get_description (profile);

      if (! label || ! strlen (label))
        label = _("(unnamed profile)");

      profile->label = g_strdup (label);
    }

  return profile->label;
}

/**
 * gimp_color_profile_get_summary:
 * @profile: a #GimpColorProfile
 *
 * This function return a string containing a multi-line summary of
 * @profile's description, model, manufacturer and copyright, to be
 * used as detailed information about the profile in a user
 * interface.
 *
 * Returns: the @profile's summary. The returned value belongs to
 *               @profile and must not be modified or freed.
 *
 * Since: 2.10
 **/
const gchar *
gimp_color_profile_get_summary (GimpColorProfile *profile)
{
  g_return_val_if_fail (GIMP_IS_COLOR_PROFILE (profile), NULL);

  if (! profile->summary)
    {
      GString     *string = g_string_new (NULL);
      const gchar *text;

      text = gimp_color_profile_get_description (profile);
      if (text)
        g_string_append (string, text);

      text = gimp_color_profile_get_model (profile);
      if (text)
        {
          if (string->len > 0)
            g_string_append (string, "\n");

          g_string_append_printf (string, _("Model: %s"), text);
        }

      text = gimp_color_profile_get_manufacturer (profile);
      if (text)
        {
          if (string->len > 0)
            g_string_append (string, "\n");

          g_string_append_printf (string, _("Manufacturer: %s"), text);
        }

      text = gimp_color_profile_get_copyright (profile);
      if (text)
        {
          if (string->len > 0)
            g_string_append (string, "\n");

          g_string_append_printf (string, _("Copyright: %s"), text);
        }

      profile->summary = g_string_free (string, FALSE);
    }

  return profile->summary;
}

/**
 * gimp_color_profile_is_equal:
 * @profile1: a #GimpColorProfile
 * @profile2: a #GimpColorProfile
 *
 * Compares two profiles.
 *
 * Returns: %TRUE if the profiles are equal, %FALSE otherwise.
 *
 * Since: 2.10
 **/
gboolean
gimp_color_profile_is_equal (GimpColorProfile *profile1,
                             GimpColorProfile *profile2)
{
  const gsize header_len = sizeof (cmsICCHeader);

  g_return_val_if_fail (GIMP_IS_COLOR_PROFILE (profile1), FALSE);
  g_return_val_if_fail (GIMP_IS_COLOR_PROFILE (profile2), FALSE);

  return profile1 == profile2                              ||
         (profile1->length == profile2->length &&
          memcmp (profile1->data + header_len,
                  profile2->data + header_len,
                  profile1->length - header_len) == 0);
}

/**
 * gimp_color_profile_is_rgb:
 * @profile: a #GimpColorProfile
 *
 * Returns: %TRUE if the profile's color space is RGB, %FALSE
 * otherwise.
 *
 * Since: 2.10
 **/
gboolean
gimp_color_profile_is_rgb (GimpColorProfile *profile)
{
  g_return_val_if_fail (GIMP_IS_COLOR_PROFILE (profile), FALSE);

  return (cmsGetColorSpace (profile->lcms_profile) == cmsSigRgbData);
}

/**
 * gimp_color_profile_is_gray:
 * @profile: a #GimpColorProfile
 *
 * Returns: %TRUE if the profile's color space is grayscale, %FALSE
 * otherwise.
 *
 * Since: 2.10
 **/
gboolean
gimp_color_profile_is_gray (GimpColorProfile *profile)
{
  g_return_val_if_fail (GIMP_IS_COLOR_PROFILE (profile), FALSE);

  return (cmsGetColorSpace (profile->lcms_profile) == cmsSigGrayData);
}

/**
 * gimp_color_profile_is_cmyk:
 * @profile: a #GimpColorProfile
 *
 * Returns: %TRUE if the profile's color space is CMYK, %FALSE
 * otherwise.
 *
 * Since: 2.10
 **/
gboolean
gimp_color_profile_is_cmyk (GimpColorProfile *profile)
{
  g_return_val_if_fail (GIMP_IS_COLOR_PROFILE (profile), FALSE);

  return (cmsGetColorSpace (profile->lcms_profile) == cmsSigCmykData);
}


/**
 * gimp_color_profile_is_linear:
 * @profile: a #GimpColorProfile
 *
 * This function determines is the ICC profile represented by a GimpColorProfile
 * is a linear RGB profile or not, some profiles that are LUTs though linear
 * will also return FALSE;
 *
 * Returns: %TRUE if the profile is a matrix shaping profile with linear
 * TRCs, %FALSE otherwise.
 *
 * Since: 2.10
 **/
gboolean
gimp_color_profile_is_linear (GimpColorProfile *profile)
{
  cmsHPROFILE   prof;
  cmsToneCurve *curve;

  g_return_val_if_fail (GIMP_IS_COLOR_PROFILE (profile), FALSE);

  prof = profile->lcms_profile;

  if (! cmsIsMatrixShaper (prof))
    return FALSE;

  if (cmsIsCLUT (prof, INTENT_PERCEPTUAL, LCMS_USED_AS_INPUT))
    return FALSE;

  if (cmsIsCLUT (prof, INTENT_PERCEPTUAL, LCMS_USED_AS_OUTPUT))
    return FALSE;

  if (gimp_color_profile_is_rgb (profile))
    {
      curve = cmsReadTag(prof, cmsSigRedTRCTag);
      if (curve == NULL || ! cmsIsToneCurveLinear (curve))
        return FALSE;

      curve = cmsReadTag (prof, cmsSigGreenTRCTag);
      if (curve == NULL || ! cmsIsToneCurveLinear (curve))
        return FALSE;

      curve = cmsReadTag (prof, cmsSigBlueTRCTag);
      if (curve == NULL || ! cmsIsToneCurveLinear (curve))
        return FALSE;
    }
  else if (gimp_color_profile_is_gray (profile))
    {
      curve = cmsReadTag(prof, cmsSigGrayTRCTag);
      if (curve == NULL || ! cmsIsToneCurveLinear (curve))
        return FALSE;
    }
  else
    {
      return FALSE;
    }

  return TRUE;
}

static void
gimp_color_profile_set_tag (cmsHPROFILE      profile,
                            cmsTagSignature  sig,
                            const gchar     *tag)
{
  cmsMLU *mlu;

  mlu = cmsMLUalloc (NULL, 1);
  cmsMLUsetASCII (mlu, "en", "US", tag);
  cmsWriteTag (profile, sig, mlu);
  cmsMLUfree (mlu);
}

static gboolean
gimp_color_profile_get_rgb_matrix_colorants (GimpColorProfile *profile,
                                             GimpMatrix3      *matrix)
{
  cmsHPROFILE  lcms_profile;
  cmsCIEXYZ   *red;
  cmsCIEXYZ   *green;
  cmsCIEXYZ   *blue;

  g_return_val_if_fail (GIMP_IS_COLOR_PROFILE (profile), FALSE);

  lcms_profile = profile->lcms_profile;

  red   = cmsReadTag (lcms_profile, cmsSigRedColorantTag);
  green = cmsReadTag (lcms_profile, cmsSigGreenColorantTag);
  blue  = cmsReadTag (lcms_profile, cmsSigBlueColorantTag);

  if (red && green && blue)
    {
      if (matrix)
        {
          matrix->coeff[0][0] = red->X;
          matrix->coeff[0][1] = red->Y;
          matrix->coeff[0][2] = red->Z;

          matrix->coeff[1][0] = green->X;
          matrix->coeff[1][1] = green->Y;
          matrix->coeff[1][2] = green->Z;

          matrix->coeff[2][0] = blue->X;
          matrix->coeff[2][1] = blue->Y;
          matrix->coeff[2][2] = blue->Z;
        }

      return TRUE;
    }

  return FALSE;
}

static void
gimp_color_profile_make_tag (cmsHPROFILE       profile,
                             cmsTagSignature   sig,
                             const gchar      *gimp_tag,
                             const gchar      *gimp_prefix,
                             const gchar      *gimp_prefix_alt,
                             const gchar      *original_tag)
{
  if (! original_tag || ! strlen (original_tag) ||
      ! strcmp (original_tag, gimp_tag))
    {
      /* if there is no original tag (or it is the same as the new
       * tag), just use the new tag
       */

      gimp_color_profile_set_tag (profile, sig, gimp_tag);
    }
  else
    {
      /* otherwise prefix the existing tag with a ammoos prefix
       * indicating that the profile has been generated
       */

      if (g_str_has_prefix (original_tag, gimp_prefix))
        {
          /* don't add multiple AmmoOS Image prefixes */
          gimp_color_profile_set_tag (profile, sig, original_tag);
        }
      else if (gimp_prefix_alt &&
               g_str_has_prefix (original_tag, gimp_prefix_alt))
        {
          /* replace AmmoOS Image prefix_alt by prefix */
          gchar *new_tag = g_strconcat (gimp_prefix,
                                        original_tag + strlen (gimp_prefix_alt),
                                        NULL);

          gimp_color_profile_set_tag (profile, sig, new_tag);
          g_free (new_tag);
        }
      else
        {
          gchar *new_tag = g_strconcat (gimp_prefix,
                                        original_tag,
                                        NULL);

          gimp_color_profile_set_tag (profile, sig, new_tag);
          g_free (new_tag);
        }
    }
}

static GimpColorProfile *
gimp_color_profile_new_from_color_profile (GimpColorProfile *profile,
                                           gboolean          linear)
{
  GimpColorProfile *new_profile;
  cmsHPROFILE       target_profile;
  GimpMatrix3       matrix = { { { 0, } } };
  cmsCIEXYZ        *whitepoint;
  cmsToneCurve     *curve;

  g_return_val_if_fail (GIMP_IS_COLOR_PROFILE (profile), NULL);

  if (gimp_color_profile_is_rgb (profile))
    {
      if (! gimp_color_profile_get_rgb_matrix_colorants (profile, &matrix))
        return NULL;
    }
  else if (! gimp_color_profile_is_gray (profile))
    {
      return NULL;
    }

  whitepoint = cmsReadTag (profile->lcms_profile,
                           cmsSigMediaWhitePointTag);

  target_profile = cmsCreateProfilePlaceholder (0);

  cmsSetProfileVersion (target_profile, 4.3);
  cmsSetDeviceClass (target_profile, cmsSigDisplayClass);
  cmsSetPCS (target_profile, cmsSigXYZData);

  cmsWriteTag (target_profile, cmsSigMediaWhitePointTag, whitepoint);

  if (linear)
    {
      /* linear light */
      curve = cmsBuildGamma (NULL, 1.00);

      gimp_color_profile_make_tag (target_profile, cmsSigProfileDescriptionTag,
                                   "linear TRC from unnamed profile",
                                   "linear TRC from ",
                                   "sRGB TRC from ",
                                   gimp_color_profile_get_description (profile));
    }
  else
    {
      cmsFloat64Number srgb_parameters[5] =
        { 2.4, 1.0 / 1.055,  0.055 / 1.055, 1.0 / 12.92, 0.04045 };

      /* sRGB curve */
      curve = cmsBuildParametricToneCurve (NULL, 4, srgb_parameters);

      gimp_color_profile_make_tag (target_profile, cmsSigProfileDescriptionTag,
                                   "sRGB TRC from unnamed profile",
                                   "sRGB TRC from ",
                                   "linear TRC from ",
                                   gimp_color_profile_get_description (profile));
    }

  if (gimp_color_profile_is_rgb (profile))
    {
      cmsCIEXYZ red;
      cmsCIEXYZ green;
      cmsCIEXYZ blue;

      cmsSetColorSpace (target_profile, cmsSigRgbData);

      red.X = matrix.coeff[0][0];
      red.Y = matrix.coeff[0][1];
      red.Z = matrix.coeff[0][2];

      green.X = matrix.coeff[1][0];
      green.Y = matrix.coeff[1][1];
      green.Z = matrix.coeff[1][2];

      blue.X = matrix.coeff[2][0];
      blue.Y = matrix.coeff[2][1];
      blue.Z = matrix.coeff[2][2];

      cmsWriteTag (target_profile, cmsSigRedColorantTag,   &red);
      cmsWriteTag (target_profile, cmsSigGreenColorantTag, &green);
      cmsWriteTag (target_profile, cmsSigBlueColorantTag,  &blue);

      cmsWriteTag (target_profile, cmsSigRedTRCTag,   curve);
      cmsWriteTag (target_profile, cmsSigGreenTRCTag, curve);
      cmsWriteTag (target_profile, cmsSigBlueTRCTag,  curve);
    }
  else
    {
      cmsSetColorSpace (target_profile, cmsSigGrayData);

      cmsWriteTag (target_profile, cmsSigGrayTRCTag, curve);
    }

  cmsFreeToneCurve (curve);

  gimp_color_profile_make_tag (target_profile, cmsSigDeviceMfgDescTag,
                               "AmmoOS Image",
                               "AmmoOS Image from ", NULL,
                               gimp_color_profile_get_manufacturer (profile));
  gimp_color_profile_make_tag (target_profile, cmsSigDeviceModelDescTag,
                               "Generated by AmmoOS Image",
                               "AmmoOS Image from ", NULL,
                               gimp_color_profile_get_model (profile));
  gimp_color_profile_make_tag (target_profile, cmsSigCopyrightTag,
                               "Public Domain",
                               "AmmoOS Image from ", NULL,
                               gimp_color_profile_get_copyright (profile));

  new_profile = gimp_color_profile_new_from_lcms_profile (target_profile, NULL);

  cmsCloseProfile (target_profile);

  return new_profile;
}

/**
 * gimp_color_profile_new_srgb_trc_from_color_profile:
 * @profile: a #GimpColorProfile
 *
 * This function creates a new RGB #GimpColorProfile with a sRGB gamma
 * TRC and @profile's RGB chromacities and whitepoint.
 *
 * Returns: (nullable) (transfer full): the new #GimpColorProfile, or %NULL if
 *               @profile is not an RGB profile or not matrix-based.
 *
 * Since: 2.10
 **/
GimpColorProfile *
gimp_color_profile_new_srgb_trc_from_color_profile (GimpColorProfile *profile)
{
  g_return_val_if_fail (GIMP_IS_COLOR_PROFILE (profile), NULL);

  return gimp_color_profile_new_from_color_profile (profile, FALSE);
}

/**
 * gimp_color_profile_new_linear_from_color_profile:
 * @profile: a #GimpColorProfile
 *
 * This function creates a new RGB #GimpColorProfile with a linear TRC
 * and @profile's RGB chromacities and whitepoint.
 *
 * Returns: (nullable) (transfer full): the new #GimpColorProfile, or %NULL if
 *               @profile is not an RGB profile or not matrix-based.
 *
 * Since: 2.10
 **/
GimpColorProfile *
gimp_color_profile_new_linear_from_color_profile (GimpColorProfile *profile)
{
  g_return_val_if_fail (GIMP_IS_COLOR_PROFILE (profile), NULL);

  return gimp_color_profile_new_from_color_profile (profile, TRUE);
}

static cmsHPROFILE *
gimp_color_profile_new_rgb_srgb_internal (void)
{
  cmsHPROFILE profile;

  /* white point is D65 from the sRGB specs */
  cmsCIExyY whitepoint = { 0.3127, 0.3290, 1.0 };

  /* primaries are ITU‐R BT.709‐5 (xYY), which are also the primaries
   * from the sRGB specs, modified to properly account for hexadecimal
   * quantization during the profile making process.
   */
  cmsCIExyYTRIPLE primaries =
    {
      /* R { 0.6400, 0.3300, 1.0 }, */
      /* G { 0.3000, 0.6000, 1.0 }, */
      /* B { 0.1500, 0.0600, 1.0 }  */
      /* R */ { 0.639998686, 0.330010138, 1.0 },
      /* G */ { 0.300003784, 0.600003357, 1.0 },
      /* B */ { 0.150002046, 0.059997204, 1.0 }
    };

  cmsFloat64Number srgb_parameters[5] =
    { 2.4, 1.0 / 1.055,  0.055 / 1.055, 1.0 / 12.92, 0.04045 };

  cmsToneCurve *curve[3];

  /* sRGB curve */
  curve[0] = curve[1] = curve[2] = cmsBuildParametricToneCurve (NULL, 4,
                                                                srgb_parameters);

  profile = cmsCreateRGBProfile (&whitepoint, &primaries, curve);

  cmsFreeToneCurve (curve[0]);

  gimp_color_profile_set_tag (profile, cmsSigProfileDescriptionTag,
                              "AmmoOS Image built-in sRGB");
  gimp_color_profile_set_tag (profile, cmsSigDeviceMfgDescTag,
                              "AmmoOS Image");
  gimp_color_profile_set_tag (profile, cmsSigDeviceModelDescTag,
                              "sRGB");
  gimp_color_profile_set_tag (profile, cmsSigCopyrightTag,
                              "Public Domain");

  /* The following line produces a V2 profile with a point curve TRC.
   * Profiles with point curve TRCs can't be used in LCMS2 unbounded
   * mode ICC profile conversions. A V2 profile might be appropriate
   * for embedding in sRGB images saved to disk, if the image is to be
   * opened by an image editing application that doesn't understand V4
   * profiles.
   *
   * cmsSetProfileVersion (srgb_profile, 2.1);
   */

  return profile;
}

/**
 * gimp_color_profile_new_rgb_srgb:
 *
 * This function is a replacement for cmsCreate_sRGBProfile() and
 * returns an sRGB profile that is functionally the same as the
 * ArgyllCMS sRGB.icm profile. "Functionally the same" means it has
 * the same red, green, and blue colorants and the V4 "chad"
 * equivalent of the ArgyllCMS V2 white point. The profile TRC is also
 * functionally equivalent to the ArgyllCMS sRGB.icm TRC and is the
 * same as the LCMS sRGB built-in profile TRC.
 *
 * The actual primaries in the sRGB specification are
 * red xy:   {0.6400, 0.3300, 1.0}
 * green xy: {0.3000, 0.6000, 1.0}
 * blue xy:  {0.1500, 0.0600, 1.0}
 *
 * The sRGB primaries given below are "pre-quantized" to compensate
 * for hexadecimal quantization during the profile-making process.
 * Unless the profile-making code compensates for this quantization,
 * the resulting profile's red, green, and blue colorants will deviate
 * slightly from the correct XYZ values.
 *
 * LCMS2 doesn't compensate for hexadecimal quantization. The
 * "pre-quantized" primaries below were back-calculated from the
 * ArgyllCMS sRGB.icm profile. The resulting sRGB profile's colorants
 * exactly matches the ArgyllCMS sRGB.icm profile colorants.
 *
 * Returns: the sRGB #GimpColorProfile.
 *
 * Since: 2.10
 **/
GimpColorProfile *
gimp_color_profile_new_rgb_srgb (void)
{
  static GimpColorProfile *profile = NULL;

  const guint8 *data;
  gsize         length = 0;

  if (G_UNLIKELY (profile == NULL))
    {
      cmsHPROFILE lcms_profile = gimp_color_profile_new_rgb_srgb_internal ();

      profile = gimp_color_profile_new_from_lcms_profile (lcms_profile, NULL);

      cmsCloseProfile (lcms_profile);
    }

  data = gimp_color_profile_get_icc_profile (profile, &length);

  return gimp_color_profile_new_from_icc_profile (data, length, NULL);
}

static cmsHPROFILE
gimp_color_profile_new_rgb_srgb_linear_internal (void)
{
  cmsHPROFILE profile;

  /* white point is D65 from the sRGB specs */
  cmsCIExyY whitepoint = { 0.3127, 0.3290, 1.0 };

  /* primaries are ITU‐R BT.709‐5 (xYY), which are also the primaries
   * from the sRGB specs, modified to properly account for hexadecimal
   * quantization during the profile making process.
   */
  cmsCIExyYTRIPLE primaries =
    {
      /* R { 0.6400, 0.3300, 1.0 }, */
      /* G { 0.3000, 0.6000, 1.0 }, */
      /* B { 0.1500, 0.0600, 1.0 }  */
      /* R */ { 0.639998686, 0.330010138, 1.0 },
      /* G */ { 0.300003784, 0.600003357, 1.0 },
      /* B */ { 0.150002046, 0.059997204, 1.0 }
    };

  cmsToneCurve *curve[3];

  /* linear light */
  curve[0] = curve[1] = curve[2] = cmsBuildGamma (NULL, 1.0);

  profile = cmsCreateRGBProfile (&whitepoint, &primaries, curve);

  cmsFreeToneCurve (curve[0]);

  gimp_color_profile_set_tag (profile, cmsSigProfileDescriptionTag,
                              "AmmoOS Image built-in Linear sRGB");
  gimp_color_profile_set_tag (profile, cmsSigDeviceMfgDescTag,
                              "AmmoOS Image");
  gimp_color_profile_set_tag (profile, cmsSigDeviceModelDescTag,
                              "Linear sRGB");
  gimp_color_profile_set_tag (profile, cmsSigCopyrightTag,
                              "Public Domain");

  return profile;
}

/**
 * gimp_color_profile_new_rgb_srgb_linear:
 *
 * This function creates a profile for babl_model("RGB"). Please
 * somebody write something smarter here.
 *
 * Returns: the linear RGB #GimpColorProfile.
 *
 * Since: 2.10
 **/
GimpColorProfile *
gimp_color_profile_new_rgb_srgb_linear (void)
{
  static GimpColorProfile *profile = NULL;

  const guint8 *data;
  gsize         length = 0;

  if (G_UNLIKELY (profile == NULL))
    {
      cmsHPROFILE lcms_profile = gimp_color_profile_new_rgb_srgb_linear_internal ();

      profile = gimp_color_profile_new_from_lcms_profile (lcms_profile, NULL);

      cmsCloseProfile (lcms_profile);
    }

  data = gimp_color_profile_get_icc_profile (profile, &length);

  return gimp_color_profile_new_from_icc_profile (data, length, NULL);
}

static cmsHPROFILE *
gimp_color_profile_new_rgb_adobe_internal (void)
{
  cmsHPROFILE profile;

  /* white point is D65 from the sRGB specs */
  cmsCIExyY whitepoint = { 0.3127, 0.3290, 1.0 };

  /* AdobeRGB1998 and sRGB have the same white point.
   *
   * The primaries below are technically correct, but because of
   * hexadecimal rounding these primaries don't make a profile that
   * matches the original.
   *
   *  cmsCIExyYTRIPLE primaries = {
   *    { 0.6400, 0.3300, 1.0 },
   *    { 0.2100, 0.7100, 1.0 },
   *    { 0.1500, 0.0600, 1.0 }
   *  };
   */
  cmsCIExyYTRIPLE primaries =
    {
      { 0.639996511, 0.329996864, 1.0 },
      { 0.210005295, 0.710004866, 1.0 },
      { 0.149997606, 0.060003644, 1.0 }
    };

  cmsToneCurve *curve[3];

  /* gamma 2.2 */
  curve[0] = curve[1] = curve[2] = cmsBuildGamma (NULL, 2.19921875);

  profile = cmsCreateRGBProfile (&whitepoint, &primaries, curve);

  cmsFreeToneCurve (curve[0]);

  gimp_color_profile_set_tag (profile, cmsSigProfileDescriptionTag,
                              "Compatible with Adobe RGB (1998)");
  gimp_color_profile_set_tag (profile, cmsSigDeviceMfgDescTag,
                              "AmmoOS Image");
  gimp_color_profile_set_tag (profile, cmsSigDeviceModelDescTag,
                              "Compatible with Adobe RGB (1998)");
  gimp_color_profile_set_tag (profile, cmsSigCopyrightTag,
                              "Public Domain");

  return profile;
}

/**
 * gimp_color_profile_new_rgb_adobe:
 *
 * This function creates a profile compatible with AbobeRGB (1998).
 *
 * Returns: the AdobeRGB-compatible #GimpColorProfile.
 *
 * Since: 2.10
 **/
GimpColorProfile *
gimp_color_profile_new_rgb_adobe (void)
{
  static GimpColorProfile *profile = NULL;

  const guint8 *data;
  gsize         length = 0;

  if (G_UNLIKELY (profile == NULL))
    {
      cmsHPROFILE lcms_profile = gimp_color_profile_new_rgb_adobe_internal ();

      profile = gimp_color_profile_new_from_lcms_profile (lcms_profile, NULL);

      cmsCloseProfile (lcms_profile);
    }

  data = gimp_color_profile_get_icc_profile (profile, &length);

  return gimp_color_profile_new_from_icc_profile (data, length, NULL);
}

static cmsHPROFILE *
gimp_color_profile_new_d65_gray_srgb_trc_internal (void)
{
  cmsHPROFILE profile;

  /* white point is D65 from the sRGB specs */
  cmsCIExyY whitepoint = { 0.3127, 0.3290, 1.0 };

  cmsFloat64Number srgb_parameters[5] =
    { 2.4, 1.0 / 1.055,  0.055 / 1.055, 1.0 / 12.92, 0.04045 };

  cmsToneCurve *curve = cmsBuildParametricToneCurve (NULL, 4,
                                                     srgb_parameters);

  profile = cmsCreateGrayProfile (&whitepoint, curve);

  cmsFreeToneCurve (curve);

  gimp_color_profile_set_tag (profile, cmsSigProfileDescriptionTag,
                              "AmmoOS Image built-in D65 Grayscale with sRGB TRC");
  gimp_color_profile_set_tag (profile, cmsSigDeviceMfgDescTag,
                              "AmmoOS Image");
  gimp_color_profile_set_tag (profile, cmsSigDeviceModelDescTag,
                              "D65 Grayscale with sRGB TRC");
  gimp_color_profile_set_tag (profile, cmsSigCopyrightTag,
                              "Public Domain");

  return profile;
}

/**
 * gimp_color_profile_new_d65_gray_srgb_trc
 *
 * This function creates a grayscale #GimpColorProfile with an
 * sRGB TRC. See gimp_color_profile_new_rgb_srgb().
 *
 * Returns: the sRGB-gamma grayscale #GimpColorProfile.
 *
 * Since: 2.10
 **/
GimpColorProfile *
gimp_color_profile_new_d65_gray_srgb_trc (void)
{
  static GimpColorProfile *profile = NULL;

  const guint8 *data;
  gsize         length = 0;

  if (G_UNLIKELY (profile == NULL))
    {
      cmsHPROFILE lcms_profile = gimp_color_profile_new_d65_gray_srgb_trc_internal ();

      profile = gimp_color_profile_new_from_lcms_profile (lcms_profile, NULL);

      cmsCloseProfile (lcms_profile);
    }

  data = gimp_color_profile_get_icc_profile (profile, &length);

  return gimp_color_profile_new_from_icc_profile (data, length, NULL);
}

static cmsHPROFILE
gimp_color_profile_new_d65_gray_linear_internal (void)
{
  cmsHPROFILE profile;

  /* white point is D65 from the sRGB specs */
  cmsCIExyY whitepoint = { 0.3127, 0.3290, 1.0 };

  cmsToneCurve *curve = cmsBuildGamma (NULL, 1.0);

  profile = cmsCreateGrayProfile (&whitepoint, curve);

  cmsFreeToneCurve (curve);

  gimp_color_profile_set_tag (profile, cmsSigProfileDescriptionTag,
                              "AmmoOS Image built-in D65 Linear Grayscale");
  gimp_color_profile_set_tag (profile, cmsSigDeviceMfgDescTag,
                              "AmmoOS Image");
  gimp_color_profile_set_tag (profile, cmsSigDeviceModelDescTag,
                              "D65 Linear Grayscale");
  gimp_color_profile_set_tag (profile, cmsSigCopyrightTag,
                              "Public Domain");

  return profile;
}

/**
 * gimp_color_profile_new_d65_gray_srgb_gray:
 *
 * This function creates a profile for babl_model("Y"). Please
 * somebody write something smarter here.
 *
 * Returns: the linear grayscale #GimpColorProfile.
 *
 * Since: 2.10
 **/
GimpColorProfile *
gimp_color_profile_new_d65_gray_linear (void)
{
  static GimpColorProfile *profile = NULL;

  const guint8 *data;
  gsize         length = 0;

  if (G_UNLIKELY (profile == NULL))
    {
      cmsHPROFILE lcms_profile = gimp_color_profile_new_d65_gray_linear_internal ();

      profile = gimp_color_profile_new_from_lcms_profile (lcms_profile, NULL);

      cmsCloseProfile (lcms_profile);
    }

  data = gimp_color_profile_get_icc_profile (profile, &length);

  return gimp_color_profile_new_from_icc_profile (data, length, NULL);
}

static cmsHPROFILE *
gimp_color_profile_new_d50_gray_lab_trc_internal (void)
{
  cmsHPROFILE profile;

  /* white point is D50 from the ICC profile illuminant specs */
  cmsCIExyY whitepoint = {0.345702915, 0.358538597, 1.0};

  cmsFloat64Number lab_parameters[5] =
    { 3.0, 1.0 / 1.16,  0.16 / 1.16, 2700.0 / 24389.0, 0.08000  };

  cmsToneCurve *curve = cmsBuildParametricToneCurve (NULL, 4,
                                                     lab_parameters);

  profile = cmsCreateGrayProfile (&whitepoint, curve);

  cmsFreeToneCurve (curve);

  gimp_color_profile_set_tag (profile, cmsSigProfileDescriptionTag,
                              "AmmoOS Image built-in D50 Grayscale with LAB L TRC");
  gimp_color_profile_set_tag (profile, cmsSigDeviceMfgDescTag,
                              "AmmoOS Image");
  gimp_color_profile_set_tag (profile, cmsSigDeviceModelDescTag,
                              "D50 Grayscale with LAB L TRC");
  gimp_color_profile_set_tag (profile, cmsSigCopyrightTag,
                              "Public Domain");

  return profile;
}


/**
 * gimp_color_profile_new_d50_gray_lab_trc
 *
 * This function creates a grayscale #GimpColorProfile with the
 * D50 ICC profile illuminant as the profile white point and the
 * LAB companding curve as the TRC.
 *
 * Returns: a gray profile with the D50 ICC profile illuminant
 * as the profile white point and the LAB companding curve as the TRC.
 * as the TRC.
 *
 * Since: 2.10
 **/
GimpColorProfile *
gimp_color_profile_new_d50_gray_lab_trc (void)
{
  static GimpColorProfile *profile = NULL;

  const guint8 *data;
  gsize         length = 0;

  if (G_UNLIKELY (profile == NULL))
    {
      cmsHPROFILE lcms_profile = gimp_color_profile_new_d50_gray_lab_trc_internal ();

      profile = gimp_color_profile_new_from_lcms_profile (lcms_profile, NULL);

      cmsCloseProfile (lcms_profile);
    }

  data = gimp_color_profile_get_icc_profile (profile, &length);

  return gimp_color_profile_new_from_icc_profile (data, length, NULL);
}

/**
 * gimp_color_profile_get_space:
 * @profile: a #GimpColorProfile
 * @intent:  a #GimpColorRenderingIntent
 * @error:   return location for #GError
 *
 * This function returns the #Babl space of @profile, for the
 * specified @intent.
 *
 * Returns: the new #Babl space.
 *
 * Since: 2.10.6
 **/
const Babl *
gimp_color_profile_get_space (GimpColorProfile          *profile,
                              GimpColorRenderingIntent   intent,
                              GError                   **error)
{
  const Babl  *space;
  const gchar *babl_error = NULL;

  g_return_val_if_fail (GIMP_IS_COLOR_PROFILE (profile), NULL);
  g_return_val_if_fail (error == NULL || *error == NULL, NULL);

  space = babl_space_from_icc ((const gchar *) profile->data,
                               profile->length,
                               (BablIccIntent) intent,
                               &babl_error);

  if (! space)
    g_set_error (error, GIMP_COLOR_PROFILE_ERROR, 0,
                 "%s: %s",
                 gimp_color_profile_get_label (profile), babl_error);

  return space;
}

/**
 * gimp_color_profile_get_format:
 * @profile: a #GimpColorProfile
 * @format:  a #Babl format
 * @intent:  a #GimpColorRenderingIntent
 * @error:   return location for #GError
 *
 * This function takes a #GimpColorProfile and a #Babl format and
 * returns a new #Babl format with @profile's RGB primaries and TRC,
 * and @format's pixel layout.
 *
 * Returns: the new #Babl format.
 *
 * Since: 2.10
 **/
const Babl *
gimp_color_profile_get_format (GimpColorProfile          *profile,
                               const Babl                *format,
                               GimpColorRenderingIntent   intent,
                               GError                   **error)
{
  const Babl *space;

  g_return_val_if_fail (GIMP_IS_COLOR_PROFILE (profile), NULL);
  g_return_val_if_fail (format != NULL, NULL);
  g_return_val_if_fail (error == NULL || *error == NULL, NULL);

  space = gimp_color_profile_get_space (profile, intent, error);

  if (! space)
    return NULL;

  return babl_format_with_space ((const gchar *) format, space);
}

/**
 * gimp_color_profile_get_lcms_format:
 * @format:      a #Babl format
 * @lcms_format: (out): return location for an lcms format
 *
 * This function takes a #Babl format and returns the lcms format to
 * be used with that @format. It also returns a #Babl format to be
 * used instead of the passed @format, which usually is the same as
 * @format, unless lcms doesn't support @format.
 *
 * Note that this function currently only supports RGB, RGBA, R'G'B',
 * R'G'B'A, Y, YA, Y', Y'A and the cairo-RGB24 and cairo-ARGB32 formats.
 *
 * Returns: (nullable): the #Babl format to be used instead of @format, or %NULL
 *               if the passed @format is not supported at all.
 *
 * Since: 2.10
 **/
const Babl *
gimp_color_profile_get_lcms_format (const Babl *format,
                                    guint32    *lcms_format)
{
  const Babl *output_format = NULL;
  const Babl *type;
  const Babl *model;
  const Babl *space;
  gboolean    has_alpha;
  gboolean    rgb      = FALSE;
  gboolean    gray     = FALSE;
  gboolean    cmyk     = FALSE;
  gboolean    linear   = FALSE;
  gboolean    srgb_trc = FALSE;

  g_return_val_if_fail (format != NULL, NULL);
  g_return_val_if_fail (lcms_format != NULL, NULL);

  has_alpha = babl_format_has_alpha (format);
  type      = babl_format_get_type (format, 0);
  model     = babl_format_get_model (format);
  space     = babl_format_get_space (format);

  if (format == babl_format ("cairo-RGB24"))
    {
#if G_BYTE_ORDER == G_LITTLE_ENDIAN
      *lcms_format = TYPE_BGRA_8;
#else
      *lcms_format = TYPE_ARGB_8;
#endif

      return format;
    }
  else if (format == babl_format ("cairo-ARGB32"))
    {
      rgb = TRUE;
    }
  else if (model == babl_model ("RGB")  ||
           model == babl_model ("RGBA") ||
           model == babl_model ("RaGaBaA"))
    {
      rgb    = TRUE;
      linear = TRUE;
    }
  else if (model == babl_model ("R~G~B~")  ||
           model == babl_model ("R~G~B~A") ||
           model == babl_model ("R~aG~aB~aA"))
    {
      rgb      = TRUE;
      srgb_trc = TRUE;
    }
  else if (model == babl_model ("R'G'B'")  ||
           model == babl_model ("R'G'B'A") ||
           model == babl_model ("R'aG'aB'aA"))
    {
      rgb = TRUE;
    }
  else if (model == babl_model ("Y")  ||
           model == babl_model ("YA") ||
           model == babl_model ("YaA"))
    {
      gray   = TRUE;
      linear = TRUE;
    }
  else if (model == babl_model ("Y~")  ||
           model == babl_model ("Y~A") ||
           model == babl_model ("Y~aA"))
    {
      gray     = TRUE;
      srgb_trc = TRUE;
    }
  else if (model == babl_model ("Y'")  ||
           model == babl_model ("Y'A") ||
           model == babl_model ("Y'aA"))
    {
      gray = TRUE;
    }
  else if (model == babl_model ("CMYK"))
#if 0
    /* FIXME missing from babl */
           || model == babl_model ("CMYKA"))
#endif
    {
      cmyk = TRUE;
    }
  else if (model == babl_model ("CIE Lab")       ||
           model == babl_model ("CIE Lab alpha") ||
           model == babl_model ("CIE LCH(ab)")   ||
           model == babl_model ("CIE LCH(ab) alpha"))
    {
      if (has_alpha)
        {
          *lcms_format = TYPE_RGBA_FLT;

          return babl_format_with_space ("RGBA float", space);
        }
      else
        {
          *lcms_format = TYPE_RGB_FLT;

          return babl_format_with_space ("RGB float", space);
        }
    }
  else if (babl_format_is_palette (format))
    {
      if (has_alpha)
        {
          *lcms_format = TYPE_RGBA_8;

          return babl_format_with_space ("R'G'B'A u8", space);
        }
      else
        {
          *lcms_format = TYPE_RGB_8;

          return babl_format_with_space ("R'G'B' u8", space);
        }
    }
  else
    {
      g_printerr ("format not supported: %s\n"
                  "has_alpha = %s\n"
                  "type = %s\n"
                  "model = %s\n",
                  babl_get_name (format),
                  has_alpha ? "TRUE" : "FALSE",
                  babl_get_name (type),
                  babl_get_name (model));
      g_return_val_if_reached (NULL);
    }

  *lcms_format = 0;

  #define FIND_FORMAT_FOR_TYPE(babl_t, lcms_t)                                 \
    do                                                                         \
      {                                                                        \
        if (has_alpha)                                                         \
          {                                                                    \
            if (rgb)                                                           \
              {                                                                \
                *lcms_format = TYPE_RGBA_##lcms_t;                             \
                                                                               \
                if (linear)                                                    \
                  output_format = babl_format_with_space ("RGBA " babl_t,      \
                                                          space);              \
                else if (srgb_trc)                                             \
                  output_format = babl_format_with_space ("R~G~B~A " babl_t,   \
                                                          space);              \
                else                                                           \
                  output_format = babl_format_with_space ("R'G'B'A " babl_t,   \
                                                          space);              \
              }                                                                \
            else if (gray)                                                     \
              {                                                                \
                *lcms_format = TYPE_GRAYA_##lcms_t;                            \
                                                                               \
                if (linear)                                                    \
                  output_format = babl_format_with_space ("YA " babl_t,        \
                                                          space);              \
                else if (srgb_trc)                                             \
                  output_format = babl_format_with_space ("Y~A " babl_t,       \
                                                          space);              \
                else                                                           \
                  output_format = babl_format_with_space ("Y'A " babl_t,       \
                                                          space);              \
              }                                                                \
            else if (cmyk)                                                     \
              {                                                                \
                *lcms_format = TYPE_CMYKA_##lcms_t;                            \
                                                                               \
                output_format = format;                                        \
              }                                                                \
          }                                                                    \
        else                                                                   \
          {                                                                    \
            if (rgb)                                                           \
              {                                                                \
                *lcms_format = TYPE_RGB_##lcms_t;                              \
                                                                               \
                if (linear)                                                    \
                  output_format = babl_format_with_space ("RGB " babl_t,       \
                                                          space);              \
                else if (srgb_trc)                                             \
                  output_format = babl_format_with_space ("R~G~B~ " babl_t,    \
                                                          space);              \
                else                                                           \
                  output_format = babl_format_with_space ("R'G'B' " babl_t,    \
                                                          space);              \
              }                                                                \
            else if (gray)                                                     \
              {                                                                \
                *lcms_format = TYPE_GRAY_##lcms_t;                             \
                                                                               \
                if (linear)                                                    \
                  output_format = babl_format_with_space ("Y " babl_t,         \
                                                          space);              \
                else if (srgb_trc)                                             \
                  output_format = babl_format_with_space ("Y~ " babl_t,        \
                                                          space);              \
                else                                                           \
                  output_format = babl_format_with_space ("Y' " babl_t,        \
                                                          space);              \
              }                                                                \
            else if (cmyk)                                                     \
              {                                                                \
                *lcms_format = TYPE_CMYK_##lcms_t;                             \
                                                                               \
                output_format = format;                                        \
              }                                                                \
          }                                                                    \
      }                                                                        \
    while (FALSE)

  if (type == babl_type ("u8"))
    FIND_FORMAT_FOR_TYPE ("u8", 8);
  else if (type == babl_type ("u16"))
    FIND_FORMAT_FOR_TYPE ("u16", 16);
  else if (type == babl_type ("half")) /* 16-bit floating point (half) */
    FIND_FORMAT_FOR_TYPE ("half", HALF_FLT);
  else if (type == babl_type ("float"))
    FIND_FORMAT_FOR_TYPE ("float", FLT);
  else if (type == babl_type ("double"))
    FIND_FORMAT_FOR_TYPE ("double", DBL);

  if (*lcms_format == 0)
    {
      g_printerr ("%s: format %s not supported, "
                  "falling back to float\n",
                  G_STRFUNC, babl_get_name (format));

      rgb = ! gray;

      FIND_FORMAT_FOR_TYPE ("float", FLT);

      g_return_val_if_fail (output_format != NULL, NULL);
    }

  #undef FIND_FORMAT_FOR_TYPE

  return output_format;
}

/* --- end libammoos/core/fieldcolor/gimpcolorprofile.c --- */

/* --- begin libammoos/core/fieldcolor/gimpcolortransform.c --- */
/* LIBGIMP - The AmmoOS Image Library
 * Copyright (C) 1995-1997 Spencer Kimball and Peter Mattis
 *
 * gimpcolortransform.c
 * Copyright (C) 2014  Michael Natterer <mitch@ammoos.org>
 *                     Elle Stone <ellestone@ninedegreesbelow.com>
 *                     Øyvind Kolås <pippin@ammoos.org>
 *
 * This library is free software: you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 3 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Library General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library.  If not, see
 * <https://www.gnu.org/licenses/>.
 */

#include "config.h"

#include <string.h>

#include <lcms2.h>

#include <gio/gio.h>
#include <gegl.h>

#include "libgimpbase/gimpbase.h"
#include "libgimpconfig/gimpconfig.h"

#include "gimpcolortypes.h"

#include "gimpcolorprofile.h"
#include "gimpcolortransform.h"

#include "libgimp/libgimp-intl.h"


/**
 * SECTION: gimpcolortransform
 * @title: GimpColorTransform
 * @short_description: Definitions and Functions relating to LCMS.
 *
 * Definitions and Functions relating to LCMS.
 **/

/**
 * GimpColorTransform:
 *
 * Simply a typedef to #gpointer, but actually is a cmsHTRANSFORM. It's
 * used in public AmmoOS Image APIs in order to avoid having to include LCMS
 * headers.
 **/


enum
{
  PROGRESS,
  LAST_SIGNAL
};


struct _GimpColorTransform
{
  GObject           parent_instance;

  GimpColorProfile *src_profile;
  const Babl       *src_format;

  GimpColorProfile *dest_profile;
  const Babl       *dest_format;

  cmsHTRANSFORM     transform;
  const Babl       *fish;
};


static void   gimp_color_transform_finalize (GObject *object);


G_DEFINE_TYPE (GimpColorTransform, gimp_color_transform, G_TYPE_OBJECT)

#define parent_class gimp_color_transform_parent_class

static guint gimp_color_transform_signals[LAST_SIGNAL] = { 0 };

static gchar *lcms_last_error = NULL;


static void
lcms_error_clear (void)
{
  if (lcms_last_error)
    {
      g_free (lcms_last_error);
      lcms_last_error = NULL;
    }
}

static void
lcms_error_handler (cmsContext       ContextID,
                    cmsUInt32Number  ErrorCode,
                    const gchar     *text)
{
  lcms_error_clear ();

  lcms_last_error = g_strdup_printf ("lcms2 error %d: %s", ErrorCode, text);
}

static void
gimp_color_transform_class_init (GimpColorTransformClass *klass)
{
  GObjectClass *object_class = G_OBJECT_CLASS (klass);

  object_class->finalize = gimp_color_transform_finalize;

  gimp_color_transform_signals[PROGRESS] =
    g_signal_new ("progress",
                  G_OBJECT_CLASS_TYPE (object_class),
                  G_SIGNAL_RUN_FIRST,
                  0,
                  NULL, NULL, NULL,
                  G_TYPE_NONE, 1,
                  G_TYPE_DOUBLE);

  cmsSetLogErrorHandler (lcms_error_handler);
}

static void
gimp_color_transform_init (GimpColorTransform *transform)
{
}

static void
gimp_color_transform_finalize (GObject *object)
{
  GimpColorTransform *transform = GIMP_COLOR_TRANSFORM (object);

  g_clear_object (&transform->src_profile);
  g_clear_object (&transform->dest_profile);

  g_clear_pointer (&transform->transform, cmsDeleteTransform);

  G_OBJECT_CLASS (parent_class)->finalize (object);
}


/**
 * gimp_color_transform_new:
 * @src_profile:      the source #GimpColorProfile
 * @src_format:       the source #Babl format
 * @dest_profile:     the destination #GimpColorProfile
 * @dest_format:      the destination #Babl format
 * @rendering_intent: the rendering intent
 * @flags:            transform flags
 *
 * This function creates an color transform.
 *
 * The color transform is determined exclusively by @src_profile and
 * @dest_profile. The color spaces of @src_format and @dest_format are
 * ignored, the formats are only used to decide between what pixel
 * encodings to transform.
 *
 * Note: this function used to return %NULL if
 * gimp_color_transform_can_gegl_copy() returned %TRUE for
 * @src_profile and @dest_profile. This is no longer the case because
 * special care has to be taken not to perform multiple implicit color
 * transforms caused by babl formats with color spaces. Now, it always
 * returns a non-%NULL transform and the code takes care of doing only
 * exactly the requested color transform.
 *
 * Returns: (nullable): the #GimpColorTransform, or %NULL if there was an error.
 *
 * Since: 2.10
 **/
GimpColorTransform *
gimp_color_transform_new (GimpColorProfile         *src_profile,
                          const Babl               *src_format,
                          GimpColorProfile         *dest_profile,
                          const Babl               *dest_format,
                          GimpColorRenderingIntent  rendering_intent,
                          GimpColorTransformFlags   flags)
{
  GimpColorTransform *transform;
  cmsHPROFILE         src_lcms;
  cmsHPROFILE         dest_lcms;
  cmsUInt32Number     lcms_src_format;
  cmsUInt32Number     lcms_dest_format;
  GError             *error = NULL;

  g_return_val_if_fail (GIMP_IS_COLOR_PROFILE (src_profile), NULL);
  g_return_val_if_fail (src_format != NULL, NULL);
  g_return_val_if_fail (GIMP_IS_COLOR_PROFILE (dest_profile), NULL);
  g_return_val_if_fail (dest_format != NULL, NULL);

  transform = g_object_new (GIMP_TYPE_COLOR_TRANSFORM, NULL);

  /* only src_profile and dest_profile must determine the transform's
   * color spaces, create formats with src_format's and dest_format's
   * encoding, and the profiles' color spaces; see process_pixels()
   * and process_buffer().
   */

  transform->src_format = gimp_color_profile_get_format (src_profile,
                                                         src_format,
                                                         GIMP_COLOR_RENDERING_INTENT_RELATIVE_COLORIMETRIC,
                                                         &error);
  if (! transform->src_format)
    {
      g_printerr ("%s: error making src format: %s\n",
                  G_STRFUNC, error->message);
      g_clear_error (&error);
    }

  transform->dest_format = gimp_color_profile_get_format (dest_profile,
                                                          dest_format,
                                                          rendering_intent,
                                                          &error);
  if (! transform->dest_format)
    {
      g_printerr ("%s: error making dest format: %s\n",
                  G_STRFUNC, error->message);
      g_clear_error (&error);
    }

  if (! g_getenv ("GIMP_COLOR_TRANSFORM_DISABLE_BABL") &&
      transform->src_format && transform->dest_format)
    {
      transform->fish = babl_fish (transform->src_format,
                                   transform->dest_format);

      g_debug ("%s: using babl for '%s' -> '%s'",
               G_STRFUNC,
               gimp_color_profile_get_label (src_profile),
               gimp_color_profile_get_label (dest_profile));

      return transform;
    }

  /* see above: when using lcms, don't mess with formats with color
   * spaces, gimp_color_profile_get_lcms_format() might return the
   * same format and it must be without space
   */
  src_format  = babl_format_with_space ((const gchar *) src_format,  NULL);
  dest_format = babl_format_with_space ((const gchar *) dest_format, NULL);

  transform->src_format  = gimp_color_profile_get_lcms_format (src_format,
                                                               &lcms_src_format);
  transform->dest_format = gimp_color_profile_get_lcms_format (dest_format,
                                                               &lcms_dest_format);

  src_lcms  = gimp_color_profile_get_lcms_profile (src_profile);
  dest_lcms = gimp_color_profile_get_lcms_profile (dest_profile);

  lcms_error_clear ();

  transform->transform = cmsCreateTransform (src_lcms,  lcms_src_format,
                                             dest_lcms, lcms_dest_format,
                                             rendering_intent,
                                             flags |
                                             cmsFLAGS_COPY_ALPHA);

  if (lcms_last_error)
    {
      if (transform->transform)
        {
          cmsDeleteTransform (transform->transform);
          transform->transform = NULL;
        }

      g_printerr ("%s: %s\n", G_STRFUNC, lcms_last_error);
    }

  if (! transform->transform)
    {
      g_object_unref (transform);
      transform = NULL;
    }

  return transform;
}

/**
 * gimp_color_transform_new_proofing:
 * @src_profile:    the source #GimpColorProfile
 * @src_format:     the source #Babl format
 * @dest_profile:   the destination #GimpColorProfile
 * @dest_format:    the destination #Babl format
 * @proof_profile:  the proof #GimpColorProfile
 * @proof_intent:   the proof intent
 * @display_intent: the display intent
 * @flags:          transform flags
 *
 * This function creates a simulation / proofing color transform.
 *
 * See gimp_color_transform_new() about the color spaces to transform
 * between.
 *
 * Returns: (nullable): the #GimpColorTransform, or %NULL if there was an error.
 *
 * Since: 2.10
 **/
GimpColorTransform *
gimp_color_transform_new_proofing (GimpColorProfile         *src_profile,
                                   const Babl               *src_format,
                                   GimpColorProfile         *dest_profile,
                                   const Babl               *dest_format,
                                   GimpColorProfile         *proof_profile,
                                   GimpColorRenderingIntent  proof_intent,
                                   GimpColorRenderingIntent  display_intent,
                                   GimpColorTransformFlags   flags)
{
  GimpColorTransform *transform;
  cmsHPROFILE         src_lcms;
  cmsHPROFILE         dest_lcms;
  cmsHPROFILE         proof_lcms;
  cmsUInt32Number     lcms_src_format;
  cmsUInt32Number     lcms_dest_format;

  g_return_val_if_fail (GIMP_IS_COLOR_PROFILE (src_profile), NULL);
  g_return_val_if_fail (src_format != NULL, NULL);
  g_return_val_if_fail (GIMP_IS_COLOR_PROFILE (dest_profile), NULL);
  g_return_val_if_fail (dest_format != NULL, NULL);
  g_return_val_if_fail (GIMP_IS_COLOR_PROFILE (proof_profile), NULL);

  transform = g_object_new (GIMP_TYPE_COLOR_TRANSFORM, NULL);

  src_lcms   = gimp_color_profile_get_lcms_profile (src_profile);
  dest_lcms  = gimp_color_profile_get_lcms_profile (dest_profile);
  proof_lcms = gimp_color_profile_get_lcms_profile (proof_profile);

  /* see gimp_color_transform_new(), we can't have color spaces
   * on the formats
   */
  src_format  = babl_format_with_space ((const gchar *) src_format,  NULL);
  dest_format = babl_format_with_space ((const gchar *) dest_format, NULL);

  transform->src_format  = gimp_color_profile_get_lcms_format (src_format,
                                                               &lcms_src_format);
  transform->dest_format = gimp_color_profile_get_lcms_format (dest_format,
                                                               &lcms_dest_format);

  lcms_error_clear ();

  transform->transform = cmsCreateProofingTransform (src_lcms,  lcms_src_format,
                                                     dest_lcms, lcms_dest_format,
                                                     proof_lcms,
                                                     proof_intent,
                                                     display_intent,
                                                     flags                 |
                                                     cmsFLAGS_SOFTPROOFING |
                                                     cmsFLAGS_COPY_ALPHA);

  if (lcms_last_error)
    {
      if (transform->transform)
        {
          cmsDeleteTransform (transform->transform);
          transform->transform = NULL;
        }

      g_printerr ("%s: %s\n", G_STRFUNC, lcms_last_error);
    }

  if (! transform->transform)
    {
      g_object_unref (transform);
      transform = NULL;
    }

  return transform;
}

/**
 * gimp_color_transform_process_pixels:
 * @transform:   a #GimpColorTransform
 * @src_format:  #Babl format of @src_pixels
 * @src_pixels:  pointer to the source pixels
 * @dest_format: #Babl format of @dest_pixels
 * @dest_pixels: pointer to the destination pixels
 * @length:      number of pixels to process
 *
 * This function transforms a contiguous line of pixels.
 *
 * See gimp_color_transform_new(): only the pixel encoding of
 * @src_format and @dest_format is honored, their color spaces are
 * ignored. The transform always takes place between the color spaces
 * determined by @transform's color profiles.
 *
 * Since: 2.10
 **/
void
gimp_color_transform_process_pixels (GimpColorTransform *transform,
                                     const Babl         *src_format,
                                     gconstpointer       src_pixels,
                                     const Babl         *dest_format,
                                     gpointer            dest_pixels,
                                     gsize               length)
{
  gpointer *src;
  gpointer *dest;

  g_return_if_fail (GIMP_IS_COLOR_TRANSFORM (transform));
  g_return_if_fail (src_format != NULL);
  g_return_if_fail (src_pixels != NULL);
  g_return_if_fail (dest_format != NULL);
  g_return_if_fail (dest_pixels != NULL);

  /* we must not do any babl color transforms when reading from
   * src_pixels or writing to dest_pixels, so construct formats with
   * src_format's and dest_format's encoding, and the transform's
   * input and output color spaces.
   */
  src_format =
    babl_format_with_space ((const gchar *) src_format,
                            babl_format_get_space (transform->src_format));
  dest_format =
    babl_format_with_space ((const gchar *) dest_format,
                            babl_format_get_space (transform->dest_format));

  if (src_format != transform->src_format)
    {
      src = g_malloc (length * babl_format_get_bytes_per_pixel (transform->src_format));

      babl_process (babl_fish (src_format,
                               transform->src_format),
                    src_pixels, src, length);
    }
  else
    {
      src = (gpointer) src_pixels;
    }

  if (dest_format != transform->dest_format)
    {
      dest = g_malloc (length * babl_format_get_bytes_per_pixel (transform->dest_format));
    }
  else
    {
      dest = dest_pixels;
    }

  if (transform->transform)
    {
      cmsDoTransform (transform->transform, src, dest, length);
    }
  else
    {
      babl_process (transform->fish, src, dest, length);
    }

  if (src_format != transform->src_format)
    {
      g_free (src);
    }

  if (dest_format != transform->dest_format)
    {
      babl_process (babl_fish (transform->dest_format,
                               dest_format),
                    dest, dest_pixels, length);

      g_free (dest);
    }
}

/**
 * gimp_color_transform_process_buffer:
 * @transform:   a #GimpColorTransform
 * @src_buffer:  source #GeglBuffer
 * @src_rect:    rectangle in @src_buffer
 * @dest_buffer: destination #GeglBuffer
 * @dest_rect:   rectangle in @dest_buffer
 *
 * This function transforms buffer into another buffer.
 *
 * See gimp_color_transform_new(): only the pixel encoding of
 * @src_buffer's and @dest_buffer's formats honored, their color
 * spaces are ignored. The transform always takes place between the
 * color spaces determined by @transform's color profiles.
 *
 * Since: 2.10
 **/
void
gimp_color_transform_process_buffer (GimpColorTransform  *transform,
                                     GeglBuffer          *src_buffer,
                                     const GeglRectangle *src_rect,
                                     GeglBuffer          *dest_buffer,
                                     const GeglRectangle *dest_rect)
{
  const Babl         *src_format;
  const Babl         *dest_format;
  GeglBufferIterator *iter;
  gint                total_pixels;
  gint                done_pixels = 0;

  g_return_if_fail (GIMP_IS_COLOR_TRANSFORM (transform));
  g_return_if_fail (GEGL_IS_BUFFER (src_buffer));
  g_return_if_fail (GEGL_IS_BUFFER (dest_buffer));

  if (src_rect)
    {
      total_pixels = src_rect->width * src_rect->height;
    }
  else
    {
      total_pixels = (gegl_buffer_get_width  (src_buffer) *
                      gegl_buffer_get_height (src_buffer));
    }

  /* we must not do any babl color transforms when reading from
   * src_buffer or writing to dest_buffer, so construct formats with
   * the transform's expected input and output encoding and
   * src_buffer's and dest_buffers's color spaces.
   */
  src_format  = gegl_buffer_get_format (src_buffer);
  dest_format = gegl_buffer_get_format (dest_buffer);

  src_format =
    babl_format_with_space ((const gchar *) transform->src_format,
                            babl_format_get_space (src_format));
  dest_format =
    babl_format_with_space ((const gchar *) transform->dest_format,
                            babl_format_get_space (dest_format));

  if (src_buffer != dest_buffer)
    {
      iter = gegl_buffer_iterator_new (src_buffer, src_rect, 0,
                                       src_format,
                                       GEGL_ACCESS_READ,
                                       GEGL_ABYSS_NONE, 2);

      gegl_buffer_iterator_add (iter, dest_buffer, dest_rect, 0,
                                dest_format,
                                GEGL_ACCESS_WRITE,
                                GEGL_ABYSS_NONE);

      while (gegl_buffer_iterator_next (iter))
        {
          if (transform->transform)
            {
              cmsDoTransform (transform->transform,
                              iter->items[0].data, iter->items[1].data, iter->length);
            }
          else
            {
              babl_process (transform->fish,
                            iter->items[0].data, iter->items[1].data, iter->length);
            }

          done_pixels += iter->items[0].roi.width * iter->items[0].roi.height;

          g_signal_emit (transform, gimp_color_transform_signals[PROGRESS], 0,
                         (gdouble) done_pixels /
                         (gdouble) total_pixels);
        }
    }
  else
    {
      iter = gegl_buffer_iterator_new (src_buffer, src_rect, 0,
                                       src_format,
                                       GEGL_ACCESS_READWRITE,
                                       GEGL_ABYSS_NONE, 1);

      while (gegl_buffer_iterator_next (iter))
        {
          if (transform->transform)
            {
              cmsDoTransform (transform->transform,
                              iter->items[0].data, iter->items[0].data, iter->length);
            }
          else
            {
              babl_process (transform->fish,
                            iter->items[0].data, iter->items[0].data, iter->length);
            }

          done_pixels += iter->items[0].roi.width * iter->items[0].roi.height;

          g_signal_emit (transform, gimp_color_transform_signals[PROGRESS], 0,
                         (gdouble) done_pixels /
                         (gdouble) total_pixels);
        }
    }

  g_signal_emit (transform, gimp_color_transform_signals[PROGRESS], 0,
                 1.0);
}

/**
 * gimp_color_transform_can_gegl_copy:
 * @src_profile:  source #GimpColorProfile
 * @dest_profile: destination #GimpColorProfile
 *
 * This function checks if a GimpColorTransform is needed at all.
 *
 * Returns: %TRUE if pixels can be correctly converted between
 *               @src_profile and @dest_profile by simply using
 *               gegl_buffer_copy(), babl_process() or similar.
 *
 * Since: 2.10
 **/
gboolean
gimp_color_transform_can_gegl_copy (GimpColorProfile *src_profile,
                                    GimpColorProfile *dest_profile)
{
  g_return_val_if_fail (GIMP_IS_COLOR_PROFILE (src_profile), FALSE);
  g_return_val_if_fail (GIMP_IS_COLOR_PROFILE (dest_profile), FALSE);

  if (gimp_color_profile_is_equal (src_profile, dest_profile))
    return TRUE;

  if (gimp_color_profile_get_space (src_profile,
                                    GIMP_COLOR_RENDERING_INTENT_RELATIVE_COLORIMETRIC,
                                    NULL) &&
      gimp_color_profile_get_space (dest_profile,
                                    GIMP_COLOR_RENDERING_INTENT_RELATIVE_COLORIMETRIC,
                                    NULL))
    {
      return TRUE;
    }

  return FALSE;
}

/* --- end libammoos/core/fieldcolor/gimpcolortransform.c --- */

/* --- begin libammoos/core/fieldcolor/gimppixbuf.c --- */
/* LIBGIMP - The AmmoOS Image Library
 * Copyright (C) 1995-1997 Spencer Kimball and Peter Mattis
 *
 * gimppixbuf.c
 * Copyright (C) 2012  Michael Natterer <mitch@ammoos.org>
 *
 * This library is free software: you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 3 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Library General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library.  If not, see
 * <https://www.gnu.org/licenses/>.
 */

#include "config.h"

#include <gegl.h>
#include <gdk-pixbuf/gdk-pixbuf.h>

#include "gimpcolortypes.h"

#include "gimppixbuf.h"


/**
 * SECTION: gimppixbuf
 * @title: GimpPixbuf
 * @short_description: Definitions and Functions relating to GdkPixbuf.
 *
 * Definitions and Functions relating to GdkPixbuf.
 **/

/**
 * gimp_pixbuf_get_format:
 * @pixbuf: a #GdkPixbuf
 *
 * Returns the Babl format that corresponds to the @pixbuf's pixel format.
 *
 * Returns: the @pixbuf's pixel format
 *
 * Since: 2.10
 **/
const Babl *
gimp_pixbuf_get_format (GdkPixbuf *pixbuf)
{
  g_return_val_if_fail (GDK_IS_PIXBUF (pixbuf), NULL);

  switch (gdk_pixbuf_get_n_channels (pixbuf))
    {
    case 3: return babl_format ("R'G'B' u8");
    case 4: return babl_format ("R'G'B'A u8");
    }

  g_return_val_if_reached (NULL);
}

/**
 * gimp_pixbuf_create_buffer:
 * @pixbuf: a #GdkPixbuf
 *
 * Returns a #GeglBuffer that's either backed by the @pixbuf's pixels,
 * or a copy of them. This function tries to not copy the @pixbuf's
 * pixels. If the pixbuf's rowstride is a multiple of its bpp, a
 * simple reference to the @pixbuf's pixels is made and @pixbuf will
 * be kept around for as long as the buffer exists; otherwise the
 * pixels are copied.
 *
 * Returns: (transfer full): a new #GeglBuffer.
 *
 * Since: 2.10
 **/
GeglBuffer *
gimp_pixbuf_create_buffer (GdkPixbuf *pixbuf)
{
  gint width;
  gint height;
  gint rowstride;
  gint bpp;

  g_return_val_if_fail (GDK_IS_PIXBUF (pixbuf), NULL);

  width     = gdk_pixbuf_get_width (pixbuf);
  height    = gdk_pixbuf_get_height (pixbuf);
  rowstride = gdk_pixbuf_get_rowstride (pixbuf);
  bpp       = gdk_pixbuf_get_n_channels (pixbuf);

  if ((rowstride % bpp) == 0)
    {
      return gegl_buffer_linear_new_from_data (gdk_pixbuf_get_pixels (pixbuf),
                                               gimp_pixbuf_get_format (pixbuf),
                                               GEGL_RECTANGLE (0, 0,
                                                               width, height),
                                               rowstride,
                                               (GDestroyNotify) g_object_unref,
                                               g_object_ref (pixbuf));
    }
  else
    {
      GeglBuffer *buffer = gegl_buffer_new (GEGL_RECTANGLE (0, 0,
                                                            width, height),
                                            gimp_pixbuf_get_format (pixbuf));

      gegl_buffer_set (buffer, NULL, 0, NULL,
                       gdk_pixbuf_get_pixels (pixbuf),
                       gdk_pixbuf_get_rowstride (pixbuf));

      return buffer;
    }
}

/**
 * gimp_pixbuf_get_icc_profile:
 * @pixbuf: a #GdkPixbuf
 * @length: (out): return location for the ICC profile's length
 *
 * Returns the ICC profile attached to the @pixbuf, or %NULL if there
 * is none.
 *
 * Returns: (array length=length) (nullable): The ICC profile data, or %NULL.
 *          The value should be freed with g_free().
 *
 * Since: 2.10
 **/
guint8 *
gimp_pixbuf_get_icc_profile (GdkPixbuf *pixbuf,
                             gsize     *length)
{
  const gchar *icc_base64;

  g_return_val_if_fail (GDK_IS_PIXBUF (pixbuf), NULL);
  g_return_val_if_fail (length != NULL, NULL);

  icc_base64 = gdk_pixbuf_get_option (pixbuf, "icc-profile");

  if (icc_base64)
    {
      guint8 *icc_data;

      icc_data = g_base64_decode (icc_base64, length);

      return icc_data;
    }

  return NULL;
}

/* --- end libammoos/core/fieldcolor/gimppixbuf.c --- */
