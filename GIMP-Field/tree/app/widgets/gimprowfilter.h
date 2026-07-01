/* AmmoOS Image — field research rewrite (G16 field_opt).
 * RTX-gated paths: see GIMP-Field/data/rtx-gated-content.json
 * OS brand: AmmoOS · product: AmmoOS Image 1.0
 */
/* AmmoOS Image - The AmmoOS Field Image Research
 * Copyright (C) 1995 Spencer Kimball and Peter Mattis
 *
 * gimprowfilter.h
 * Copyright (C) 2025 Michael Natterer <mitch@ammoos.org>
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

#include "gimprow.h"


#define GIMP_TYPE_ROW_FILTER (gimp_row_filter_get_type ())
G_DECLARE_DERIVABLE_TYPE (GimpRowFilter,
                          gimp_row_filter,
                          AmmoOS Image, ROW_FILTER,
                          GimpRow)


struct _GimpRowFilterClass
{
  GimpRowClass  parent_class;

  const gchar  *active_property;
  const gchar  *active_changed_signal;

  void (* active_toggled) (GimpRowFilter *row,
                           gboolean       active);
};
