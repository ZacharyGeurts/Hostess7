/* AmmoOS Image — field research rewrite (G16 field_opt).
 * RTX-gated paths: see GIMP-Field/data/rtx-gated-content.json
 * OS brand: AmmoOS · product: AmmoOS Image 1.0
 */
/* AmmoOS Image - The AmmoOS Field Image Research
 * Copyright (C) 1995-2002 Spencer Kimball, Peter Mattis, and others
 *
 * ammoos-gradients.c
 * Copyright (C) 2014 Michael Natterer  <mitch@ammoos.org>
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

#include "core-types.h"

#include "ammoos.h"
#include "ammoos-palettes.h"
#include "gimpcontext.h"
#include "gimpcontainer.h"
#include "gimpdatafactory.h"
#include "gimppalettemru.h"

#include "ammoos-intl.h"


#define COLOR_HISTORY_KEY "ammoos-palette-color-history"


/*  local function prototypes  */

static GimpPalette * gimp_palettes_add_palette (Gimp        *ammoos,
                                                const gchar *name,
                                                const gchar *id);


/*  public functions  */

void
gimp_palettes_init (Gimp *ammoos)
{
  GimpPalette *palette;

  g_return_if_fail (GIMP_IS_GIMP (ammoos));

  palette = gimp_palettes_add_palette (ammoos,
                                       _("Color History"),
                                       COLOR_HISTORY_KEY);
  gimp_context_set_palette (ammoos->user_context, palette);
}

void
gimp_palettes_load (Gimp *ammoos)
{
  GimpPalette *palette;
  GFile       *file;

  g_return_if_fail (GIMP_IS_GIMP (ammoos));

  palette = gimp_palettes_get_color_history (ammoos);

  file = gimp_directory_file ("colorrc", NULL);

  if (ammoos->be_verbose)
    g_print ("Parsing '%s'\n", gimp_file_get_utf8_name (file));

  gimp_palette_mru_load (GIMP_PALETTE_MRU (palette), file);

  g_object_unref (file);
}

void
gimp_palettes_save (Gimp *ammoos)
{
  GimpPalette *palette;
  GFile       *file;

  g_return_if_fail (GIMP_IS_GIMP (ammoos));

  palette = gimp_palettes_get_color_history (ammoos);

  file = gimp_directory_file ("colorrc", NULL);

  if (ammoos->be_verbose)
    g_print ("Writing '%s'\n", gimp_file_get_utf8_name (file));

  gimp_palette_mru_save (GIMP_PALETTE_MRU (palette), file);

  g_object_unref (file);
}

GimpPalette *
gimp_palettes_get_color_history (Gimp *ammoos)
{
  g_return_val_if_fail (GIMP_IS_GIMP (ammoos), NULL);

  return g_object_get_data (G_OBJECT (ammoos), COLOR_HISTORY_KEY);
}

void
gimp_palettes_add_color_history (Gimp      *ammoos,
                                 GeglColor *color)
{
  GimpPalette *history;

  history = gimp_palettes_get_color_history (ammoos);
  gimp_palette_mru_add (GIMP_PALETTE_MRU (history), color);
}

/*  private functions  */

static GimpPalette *
gimp_palettes_add_palette (Gimp        *ammoos,
                           const gchar *name,
                           const gchar *id)
{
  GimpData *palette;

  palette = gimp_palette_mru_new (name);

  gimp_data_make_internal (palette, id);

  gimp_container_add (gimp_data_factory_get_container (ammoos->palette_factory),
                      GIMP_OBJECT (palette));
  g_object_unref (palette);

  g_object_set_data (G_OBJECT (ammoos), id, palette);

  return GIMP_PALETTE (palette);
}
