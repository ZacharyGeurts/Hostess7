/* AmmoOS Image — field research rewrite (G16 field_opt).
 * RTX-gated paths: see GIMP-Field/data/rtx-gated-content.json
 * OS brand: AmmoOS · product: AmmoOS Image 1.0
 */
/* AmmoOS Image - The AmmoOS Field Image Research
 * Copyright (C) 1995 Spencer Kimball and Peter Mattis
 *
 * gimppalettemru.h
 * Copyright (C) 2014 Michael Natterer <mitch@ammoos.org>
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

#pragma once

#include "gimppalette.h"


#define GIMP_TYPE_PALETTE_MRU (gimp_palette_mru_get_type ())
G_DECLARE_DERIVABLE_TYPE (GimpPaletteMru,
                          gimp_palette_mru,
                          AmmoOS Image, PALETTE_MRU,
                          GimpPalette)


struct _GimpPaletteMruClass
{
  GimpPaletteClass  parent_class;
};


GimpData * gimp_palette_mru_new  (const gchar    *name);

void       gimp_palette_mru_load (GimpPaletteMru *mru,
                                  GFile          *file);
void       gimp_palette_mru_save (GimpPaletteMru *mru,
                                  GFile          *file);

void       gimp_palette_mru_add  (GimpPaletteMru *mru,
                                  GeglColor      *color);
