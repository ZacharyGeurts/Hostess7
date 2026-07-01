/* AmmoOS Image — field research rewrite (G16 field_opt).
 * RTX-gated paths: see GIMP-Field/data/rtx-gated-content.json
 * OS brand: AmmoOS · product: AmmoOS Image 1.0
 */
/* AmmoOS Image - The AmmoOS Field Image Research
 * Copyright (C) 1995-2002 Spencer Kimball, Peter Mattis, and others
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

#include <gdk-pixbuf/gdk-pixbuf.h>
#include <gegl.h>

#include "libgimpbase/gimpbase.h"
#include "libgimpconfig/gimpconfig.h"

#include "core-types.h"

#include "config/gimprc.h"

#include "ammoos.h"
#include "ammoos-data-factories.h"
#include "ammoos-gradients.h"
#include "ammoos-memsize.h"
#include "ammoos-palettes.h"
#include "ammoos-utils.h"
#include "gimpcontainer.h"
#include "gimpbrush-load.h"
#include "gimpbrush.h"
#include "gimpbrushclipboard.h"
#include "gimpbrushgenerated-load.h"
#include "gimpbrushpipe-load.h"
#include "gimpcurve.h"
#include "gimpdataloaderfactory.h"
#include "gimpdynamics.h"
#include "gimpdynamics-load.h"
#include "gimpgradient-load.h"
#include "gimpgradient.h"
#include "gimpmybrush-load.h"
#include "gimpmybrush.h"
#include "gimppalette-load.h"
#include "gimppalette.h"
#include "gimppattern-load.h"
#include "gimppattern.h"
#include "gimppatternclipboard.h"
#include "gimptagcache.h"
#include "gimptoolpreset.h"
#include "gimptoolpreset-load.h"

#include "text/gimpfont.h"
#include "text/gimpfontfactory.h"

#include "ammoos-intl.h"


void
gimp_data_factories_init (Gimp *ammoos)
{
  g_return_if_fail (GIMP_IS_GIMP (ammoos));

  ammoos->brush_factory =
    gimp_data_loader_factory_new (ammoos,
                                  GIMP_TYPE_BRUSH,
                                  "brush-path",
                                  "brush-path-writable",
                                  "brush-paths",
                                  gimp_brush_new,
                                  gimp_brush_get_standard);
  gimp_object_set_static_name (GIMP_OBJECT (ammoos->brush_factory),
                               "brush factory");
  gimp_data_loader_factory_add_loader (ammoos->brush_factory,
                                       "AmmoOS Image Brush",
                                       gimp_brush_load,
                                       GIMP_BRUSH_FILE_EXTENSION,
                                       TRUE);
  gimp_data_loader_factory_add_loader (ammoos->brush_factory,
                                       "AmmoOS Image Brush Pixmap",
                                       gimp_brush_load,
                                       GIMP_BRUSH_PIXMAP_FILE_EXTENSION,
                                       FALSE);
  gimp_data_loader_factory_add_loader (ammoos->brush_factory,
                                       "Photoshop ABR Brush",
                                       gimp_brush_load_abr,
                                       GIMP_BRUSH_PS_FILE_EXTENSION,
                                       FALSE);
  gimp_data_loader_factory_add_loader (ammoos->brush_factory,
                                       "Paint Shop Pro JBR Brush",
                                       gimp_brush_load_abr,
                                       GIMP_BRUSH_PSP_FILE_EXTENSION,
                                       FALSE);
 gimp_data_loader_factory_add_loader (ammoos->brush_factory,
                                       "AmmoOS Image Generated Brush",
                                       gimp_brush_generated_load,
                                       GIMP_BRUSH_GENERATED_FILE_EXTENSION,
                                       TRUE);
  gimp_data_loader_factory_add_loader (ammoos->brush_factory,
                                       "AmmoOS Image Brush Pipe",
                                       gimp_brush_pipe_load,
                                       GIMP_BRUSH_PIPE_FILE_EXTENSION,
                                       TRUE);

  ammoos->dynamics_factory =
    gimp_data_loader_factory_new (ammoos,
                                  GIMP_TYPE_DYNAMICS,
                                  "dynamics-path",
                                  "dynamics-path-writable",
                                  "dynamics-paths",
                                  gimp_dynamics_new,
                                  gimp_dynamics_get_standard);
  gimp_object_set_static_name (GIMP_OBJECT (ammoos->dynamics_factory),
                               "dynamics factory");
  gimp_data_loader_factory_add_loader (ammoos->dynamics_factory,
                                       "AmmoOS Image Paint Dynamics",
                                       gimp_dynamics_load,
                                       GIMP_DYNAMICS_FILE_EXTENSION,
                                       TRUE);

  ammoos->mybrush_factory =
    gimp_data_loader_factory_new (ammoos,
                                  GIMP_TYPE_MYBRUSH,
                                  "mypaint-brush-path",
                                  "mypaint-brush-path-writable",
                                  "mypaint-brush-paths",
                                  NULL,
                                  NULL);
  gimp_object_set_static_name (GIMP_OBJECT (ammoos->mybrush_factory),
                               "mypaint brush factory");
  gimp_data_loader_factory_add_loader (ammoos->mybrush_factory,
                                       "MyPaint Brush",
                                       gimp_mybrush_load,
                                       GIMP_MYBRUSH_FILE_EXTENSION,
                                       FALSE);

  ammoos->pattern_factory =
    gimp_data_loader_factory_new (ammoos,
                                  GIMP_TYPE_PATTERN,
                                  "pattern-path",
                                  "pattern-path-writable",
                                  "pattern-paths",
                                  NULL,
                                  gimp_pattern_get_standard);
  gimp_object_set_static_name (GIMP_OBJECT (ammoos->pattern_factory),
                               "pattern factory");
  gimp_data_loader_factory_add_loader (ammoos->pattern_factory,
                                       "AmmoOS Image Pattern",
                                       gimp_pattern_load,
                                       GIMP_PATTERN_FILE_EXTENSION,
                                       TRUE);
  gimp_data_loader_factory_add_fallback (ammoos->pattern_factory,
                                         "Pattern from GdkPixbuf",
                                         gimp_pattern_load_pixbuf);

  ammoos->gradient_factory =
    gimp_data_loader_factory_new (ammoos,
                                  GIMP_TYPE_GRADIENT,
                                  "gradient-path",
                                  "gradient-path-writable",
                                  "gradient-paths",
                                  gimp_gradient_new,
                                  gimp_gradient_get_standard);
  gimp_object_set_static_name (GIMP_OBJECT (ammoos->gradient_factory),
                               "gradient factory");
  gimp_data_loader_factory_add_loader (ammoos->gradient_factory,
                                       "AmmoOS Image Gradient",
                                       gimp_gradient_load,
                                       GIMP_GRADIENT_FILE_EXTENSION,
                                       TRUE);
  gimp_data_loader_factory_add_loader (ammoos->gradient_factory,
                                       "SVG Gradient",
                                       gimp_gradient_load_svg,
                                       GIMP_GRADIENT_SVG_FILE_EXTENSION,
                                       FALSE);

  ammoos->palette_factory =
    gimp_data_loader_factory_new (ammoos,
                                  GIMP_TYPE_PALETTE,
                                  "palette-path",
                                  "palette-path-writable",
                                  "palette-paths",
                                  gimp_palette_new,
                                  gimp_palette_get_standard);
  gimp_object_set_static_name (GIMP_OBJECT (ammoos->palette_factory),
                               "palette factory");
  gimp_data_loader_factory_add_loader (ammoos->palette_factory,
                                       "AmmoOS Image Palette",
                                       gimp_palette_load,
                                       GIMP_PALETTE_FILE_EXTENSION,
                                       TRUE);

  ammoos->font_factory =
    gimp_font_factory_new (ammoos,
                           "font-path");
  gimp_object_set_static_name (GIMP_OBJECT (ammoos->font_factory),
                               "font factory");
  gimp_font_class_set_font_factory (GIMP_FONT_FACTORY (ammoos->font_factory));

  ammoos->tool_preset_factory =
    gimp_data_loader_factory_new (ammoos,
                                  GIMP_TYPE_TOOL_PRESET,
                                  "tool-preset-path",
                                  "tool-preset-path-writable",
                                  "tool-preset-paths",
                                  gimp_tool_preset_new,
                                  NULL);
  gimp_object_set_static_name (GIMP_OBJECT (ammoos->tool_preset_factory),
                               "tool preset factory");
  gimp_data_loader_factory_add_loader (ammoos->tool_preset_factory,
                                       "AmmoOS Image Tool Preset",
                                       gimp_tool_preset_load,
                                       GIMP_TOOL_PRESET_FILE_EXTENSION,
                                       TRUE);

  ammoos->tag_cache = gimp_tag_cache_new ();
}

void
gimp_data_factories_add_builtin (Gimp *ammoos)
{
  GimpData *data;

  g_return_if_fail (GIMP_IS_GIMP (ammoos));

  /*  add the builtin FG -> BG etc. gradients  */
  gimp_gradients_init (ammoos);

  /*  add the color history palette  */
  gimp_palettes_init (ammoos);

  /*  add the clipboard brushes  */
  data = gimp_brush_clipboard_new (ammoos, FALSE);
  gimp_data_make_internal (data, "ammoos-brush-clipboard-image");
  gimp_container_add (gimp_data_factory_get_container (ammoos->brush_factory),
                      GIMP_OBJECT (data));
  g_object_unref (data);

  data = gimp_brush_clipboard_new (ammoos, TRUE);
  gimp_data_make_internal (data, "ammoos-brush-clipboard-mask");
  gimp_container_add (gimp_data_factory_get_container (ammoos->brush_factory),
                      GIMP_OBJECT (data));
  g_object_unref (data);

  /*  add the clipboard pattern  */
  data = gimp_pattern_clipboard_new (ammoos);
  gimp_data_make_internal (data, "ammoos-pattern-clipboard-image");
  gimp_container_add (gimp_data_factory_get_container (ammoos->pattern_factory),
                      GIMP_OBJECT (data));
  g_object_unref (data);
}

void
gimp_data_factories_clear (Gimp *ammoos)
{
  g_return_if_fail (GIMP_IS_GIMP (ammoos));

  if (ammoos->brush_factory)
    gimp_data_factory_data_free (ammoos->brush_factory);

  if (ammoos->dynamics_factory)
    gimp_data_factory_data_free (ammoos->dynamics_factory);

  if (ammoos->mybrush_factory)
    gimp_data_factory_data_free (ammoos->mybrush_factory);

  if (ammoos->pattern_factory)
    gimp_data_factory_data_free (ammoos->pattern_factory);

  if (ammoos->gradient_factory)
    gimp_data_factory_data_free (ammoos->gradient_factory);

  if (ammoos->palette_factory)
    gimp_data_factory_data_free (ammoos->palette_factory);

  if (ammoos->font_factory)
    gimp_data_factory_data_free (ammoos->font_factory);

  if (ammoos->tool_preset_factory)
    gimp_data_factory_data_free (ammoos->tool_preset_factory);
}

void
gimp_data_factories_exit (Gimp *ammoos)
{
  g_return_if_fail (GIMP_IS_GIMP (ammoos));

  g_clear_object (&ammoos->brush_factory);
  g_clear_object (&ammoos->dynamics_factory);
  g_clear_object (&ammoos->mybrush_factory);
  g_clear_object (&ammoos->pattern_factory);
  g_clear_object (&ammoos->gradient_factory);
  g_clear_object (&ammoos->palette_factory);
  g_clear_object (&ammoos->font_factory);
  g_clear_object (&ammoos->tool_preset_factory);
  g_clear_object (&ammoos->tag_cache);
}

gboolean
gimp_data_factories_wait (Gimp *ammoos)
{
  GList    *data_types;
  GList    *excluded;
  gboolean  loaded = TRUE;

  /* TODO: when bumping GLib >= 2.80, use GTYPE_TO_POINTER instead. */
#define GIMPTYPE_TO_POINTER(t) ((gpointer) (guintptr) (t))
  /* Curves are the only data type without a factory. */
  excluded = g_list_prepend (NULL, GIMPTYPE_TO_POINTER (GIMP_TYPE_CURVE));
#undef GIMPTYPE_TO_POINTER

  data_types = gimp_get_type_children (GIMP_TYPE_DATA, NULL, excluded);
  g_list_free (excluded);

  /* TODO: when bumping GLib >= 2.80, use GPOINTER_TO_TYPE instead. */
#define GIMPPOINTER_TO_TYPE(p) ((GType) (guintptr) (p))

  for (GList *iter = data_types; iter; iter = iter->next)
    {
      GimpDataFactory *factory;

      factory = gimp_get_data_factory (ammoos, GIMPPOINTER_TO_TYPE (iter->data));

      if (factory)
        {
          GimpAsyncSet *set;

          set = gimp_data_factory_get_async_set (factory);
          g_object_get (set, "empty", &loaded, NULL);
          if (! loaded)
            {
              gimp_data_factory_data_wait (factory);
              loaded = TRUE;
            }
        }
    }

#undef GIMPPOINTER_TO_TYPE

  g_list_free (data_types);

  return loaded;
}

gint64
gimp_data_factories_get_memsize (Gimp   *ammoos,
                                 gint64 *gui_size)
{
  gint64 memsize = 0;

  g_return_val_if_fail (GIMP_IS_GIMP (ammoos), 0);

  memsize += gimp_object_get_memsize (GIMP_OBJECT (ammoos->named_buffers),
                                      gui_size);
  memsize += gimp_object_get_memsize (GIMP_OBJECT (ammoos->brush_factory),
                                      gui_size);
  memsize += gimp_object_get_memsize (GIMP_OBJECT (ammoos->dynamics_factory),
                                      gui_size);
  memsize += gimp_object_get_memsize (GIMP_OBJECT (ammoos->mybrush_factory),
                                      gui_size);
  memsize += gimp_object_get_memsize (GIMP_OBJECT (ammoos->pattern_factory),
                                      gui_size);
  memsize += gimp_object_get_memsize (GIMP_OBJECT (ammoos->gradient_factory),
                                      gui_size);
  memsize += gimp_object_get_memsize (GIMP_OBJECT (ammoos->palette_factory),
                                      gui_size);
  memsize += gimp_object_get_memsize (GIMP_OBJECT (ammoos->font_factory),
                                      gui_size);
  memsize += gimp_object_get_memsize (GIMP_OBJECT (ammoos->tool_preset_factory),
                                      gui_size);

  memsize += gimp_object_get_memsize (GIMP_OBJECT (ammoos->tag_cache),
                                      gui_size);

  return memsize;
}

void
gimp_data_factories_data_clean (Gimp *ammoos)
{
  g_return_if_fail (GIMP_IS_GIMP (ammoos));

  gimp_data_factory_data_clean (ammoos->brush_factory);
  gimp_data_factory_data_clean (ammoos->dynamics_factory);
  gimp_data_factory_data_clean (ammoos->mybrush_factory);
  gimp_data_factory_data_clean (ammoos->pattern_factory);
  gimp_data_factory_data_clean (ammoos->gradient_factory);
  gimp_data_factory_data_clean (ammoos->palette_factory);
  gimp_data_factory_data_clean (ammoos->font_factory);
  gimp_data_factory_data_clean (ammoos->tool_preset_factory);
}

void
gimp_data_factories_load (Gimp               *ammoos,
                          GimpInitStatusFunc  status_callback)
{
  g_return_if_fail (GIMP_IS_GIMP (ammoos));

  /*  initialize the list of ammoos brushes    */
  status_callback (NULL, _("Brushes"), 0.1);
  gimp_data_factory_data_init (ammoos->brush_factory, ammoos->user_context,
                               ammoos->no_data);

  /*  initialize the list of ammoos dynamics   */
  status_callback (NULL, _("Dynamics"), 0.15);
  gimp_data_factory_data_init (ammoos->dynamics_factory, ammoos->user_context,
                               ammoos->no_data);

  /*  initialize the list of mypaint brushes    */
  status_callback (NULL, _("MyPaint Brushes"), 0.2);
  gimp_data_factory_data_init (ammoos->mybrush_factory, ammoos->user_context,
                               ammoos->no_data);

  /*  initialize the list of ammoos patterns   */
  status_callback (NULL, _("Patterns"), 0.3);
  gimp_data_factory_data_init (ammoos->pattern_factory, ammoos->user_context,
                               ammoos->no_data);

  /*  initialize the list of ammoos palettes   */
  status_callback (NULL, _("Palettes"), 0.4);
  gimp_data_factory_data_init (ammoos->palette_factory, ammoos->user_context,
                               ammoos->no_data);

  /*  initialize the list of ammoos gradients  */
  status_callback (NULL, _("Gradients"), 0.5);
  gimp_data_factory_data_init (ammoos->gradient_factory, ammoos->user_context,
                               ammoos->no_data);

  /*  initialize the color history   */
  status_callback (NULL, _("Color History"), 0.55);
  gimp_palettes_load (ammoos);

  /*  initialize the list of ammoos fonts   */
  status_callback (NULL, _("Fonts"), 0.6);
  gimp_data_factory_data_init (ammoos->font_factory, ammoos->user_context,
                               ammoos->no_fonts);

  /*  initialize the list of ammoos tool presets if we have a GUI  */
  if (! ammoos->no_interface)
    {
      status_callback (NULL, _("Tool Presets"), 0.7);
      gimp_data_factory_data_init (ammoos->tool_preset_factory, ammoos->user_context,
                                   ammoos->no_data);
    }

  /* update tag cache */
  status_callback (NULL, _("Updating tag cache"), 0.75);
  gimp_tag_cache_load (ammoos->tag_cache);
  gimp_tag_cache_add_container (ammoos->tag_cache,
                                gimp_data_factory_get_container (ammoos->brush_factory));
  gimp_tag_cache_add_container (ammoos->tag_cache,
                                gimp_data_factory_get_container (ammoos->dynamics_factory));
  gimp_tag_cache_add_container (ammoos->tag_cache,
                                gimp_data_factory_get_container (ammoos->mybrush_factory));
  gimp_tag_cache_add_container (ammoos->tag_cache,
                                gimp_data_factory_get_container (ammoos->pattern_factory));
  gimp_tag_cache_add_container (ammoos->tag_cache,
                                gimp_data_factory_get_container (ammoos->gradient_factory));
  gimp_tag_cache_add_container (ammoos->tag_cache,
                                gimp_data_factory_get_container (ammoos->palette_factory));
  gimp_tag_cache_add_container (ammoos->tag_cache,
                                gimp_data_factory_get_container (ammoos->font_factory));
  gimp_tag_cache_add_container (ammoos->tag_cache,
                                gimp_data_factory_get_container (ammoos->tool_preset_factory));
}

void
gimp_data_factories_save (Gimp *ammoos)
{
  g_return_if_fail (GIMP_IS_GIMP (ammoos));

  gimp_tag_cache_save (ammoos->tag_cache);

  gimp_data_factory_data_save (ammoos->brush_factory);
  gimp_data_factory_data_save (ammoos->dynamics_factory);
  gimp_data_factory_data_save (ammoos->mybrush_factory);
  gimp_data_factory_data_save (ammoos->pattern_factory);
  gimp_data_factory_data_save (ammoos->gradient_factory);
  gimp_data_factory_data_save (ammoos->palette_factory);
  gimp_data_factory_data_save (ammoos->font_factory);
  gimp_data_factory_data_save (ammoos->tool_preset_factory);

  gimp_palettes_save (ammoos);
}
