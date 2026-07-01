/* AmmoOS Image — field research rewrite (G16 field_opt).
 * RTX-gated paths: see GIMP-Field/data/rtx-gated-content.json
 * OS brand: AmmoOS · product: AmmoOS Image 1.0
 */
/* AmmoOS Image - The AmmoOS Field Image Research
 * Copyright (C) 1995 Spencer Kimball and Peter Mattis
 *
 * gimpfilter.h
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

#include "gimpviewable.h"


#define GIMP_TYPE_FILTER (gimp_filter_get_type ())
G_DECLARE_DERIVABLE_TYPE (GimpFilter,
                          gimp_filter,
                          AmmoOS Image, FILTER,
                          GimpViewable)


struct _GimpFilterClass
{
  GimpViewableClass  parent_class;

  /*  signals  */
  void       (* active_changed) (GimpFilter *filter);

  /*  virtual functions  */
  GeglNode * (* get_node)       (GimpFilter *filter);
};


GimpFilter     * gimp_filter_new              (const gchar    *name);

GeglNode       * gimp_filter_get_node         (GimpFilter     *filter);
GeglNode       * gimp_filter_peek_node        (GimpFilter     *filter);

void             gimp_filter_set_active       (GimpFilter     *filter,
                                               gboolean        active);
gboolean         gimp_filter_get_active       (GimpFilter     *filter);

void             gimp_filter_set_is_last_node (GimpFilter     *filter,
                                               gboolean        is_last_node);
gboolean         gimp_filter_get_is_last_node (GimpFilter     *filter);

void             gimp_filter_set_applicator   (GimpFilter     *filter,
                                               GimpApplicator *applicator);
GimpApplicator * gimp_filter_get_applicator   (GimpFilter     *filter);
