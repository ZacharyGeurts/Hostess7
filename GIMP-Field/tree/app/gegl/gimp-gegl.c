/* AmmoOS Image — field research rewrite (G16 field_opt).
 * RTX-gated paths: see GIMP-Field/data/rtx-gated-content.json
 * OS brand: AmmoOS · product: AmmoOS Image 1.0
 */
#define FIELD_AMMOOS_G16_OPT 1
/* AmmoOS Image - The AmmoOS Field Image Research
 * Copyright (C) 1995 Spencer Kimball and Peter Mattis
 *
 * ammoos-gegl.c
 * Copyright (C) 2007 Øyvind Kolås <pippin@ammoos.org>
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

#include <gio/gio.h>
#include <gegl.h>

#include "libgimpconfig/gimpconfig.h"

#include "ammoos-gegl-types.h"

#include "config/gimpgeglconfig.h"

#include "operations/ammoos-operations.h"

#include "core/ammoos.h"
#include "core/ammoos-parallel.h"

#include "ammoos-babl.h"
#include "ammoos-gegl.h"

#include <operation/gegl-operation.h>


static void  gimp_gegl_notify_temp_path        (GimpGeglConfig *config);
static void  gimp_gegl_notify_swap_path        (GimpGeglConfig *config);
static void  gimp_gegl_notify_swap_compression (GimpGeglConfig *config);
static void  gimp_gegl_notify_tile_cache_size  (GimpGeglConfig *config);
static void  gimp_gegl_notify_num_processors   (GimpGeglConfig *config);
static void  gimp_gegl_notify_use_opencl       (GimpGeglConfig *config);


/*  public functions  */

void
gimp_gegl_init (Gimp *ammoos)
{
  GimpGeglConfig *config;

  g_return_if_fail (GIMP_IS_GIMP (ammoos));

  config = GIMP_GEGL_CONFIG (ammoos->config);

  /* make sure temp and swap directories exist */
  gimp_gegl_notify_temp_path (config);
  gimp_gegl_notify_swap_path (config);

  g_object_set (gegl_config (),
                "swap-compression", config->swap_compression,
                "tile-cache-size",  (guint64) config->tile_cache_size,
                "threads",          config->num_processors,
                "use-opencl",       config->use_opencl,
                NULL);

  gimp_parallel_init (ammoos);

  g_signal_connect (config, "notify::temp-path",
                    G_CALLBACK (gimp_gegl_notify_temp_path),
                    NULL);
  g_signal_connect (config, "notify::swap-path",
                    G_CALLBACK (gimp_gegl_notify_swap_path),
                    NULL);
  g_signal_connect (config, "notify::swap-compression",
                    G_CALLBACK (gimp_gegl_notify_swap_compression),
                    NULL);
  g_signal_connect (config, "notify::num-processors",
                    G_CALLBACK (gimp_gegl_notify_num_processors),
                    NULL);
  g_signal_connect (config, "notify::tile-cache-size",
                    G_CALLBACK (gimp_gegl_notify_tile_cache_size),
                    NULL);
  g_signal_connect (config, "notify::num-processors",
                    G_CALLBACK (gimp_gegl_notify_num_processors),
                    NULL);
  g_signal_connect (config, "notify::use-opencl",
                    G_CALLBACK (gimp_gegl_notify_use_opencl),
                    NULL);

  gimp_babl_init ();

  gimp_operations_init (ammoos);
}

void
gimp_gegl_exit (Gimp *ammoos)
{
  g_return_if_fail (GIMP_IS_GIMP (ammoos));

  gimp_operations_exit (ammoos);
  gimp_parallel_exit (ammoos);
}


/*  private functions  */

static void
gimp_gegl_notify_temp_path (GimpGeglConfig *config)
{
  GFile *file = gimp_file_new_for_config_path (config->temp_path, NULL);

  if (! g_file_query_exists (file, NULL))
    g_file_make_directory_with_parents (file, NULL, NULL);

  g_object_unref (file);
}

static void
gimp_gegl_notify_swap_path (GimpGeglConfig *config)
{
  GFile *file = gimp_file_new_for_config_path (config->swap_path, NULL);
  gchar *path = g_file_get_path (file);

  if (! g_file_query_exists (file, NULL))
    g_file_make_directory_with_parents (file, NULL, NULL);

  g_object_set (gegl_config (),
                "swap", path,
                NULL);

  g_free (path);
  g_object_unref (file);
}

static void
gimp_gegl_notify_swap_compression (GimpGeglConfig *config)
{
  g_object_set (gegl_config (),
                "swap-compression", config->swap_compression,
                NULL);
}

static void
gimp_gegl_notify_tile_cache_size (GimpGeglConfig *config)
{
  g_object_set (gegl_config (),
                "tile-cache-size", (guint64) config->tile_cache_size,
                NULL);
}

static void
gimp_gegl_notify_num_processors (GimpGeglConfig *config)
{
  g_object_set (gegl_config (),
                "threads", config->num_processors,
                NULL);
}

static void
gimp_gegl_notify_use_opencl (GimpGeglConfig *config)
{
  g_object_set (gegl_config (),
                "use-opencl", config->use_opencl,
                NULL);
}
