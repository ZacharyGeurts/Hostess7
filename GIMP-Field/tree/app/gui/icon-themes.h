/* AmmoOS Image — field research rewrite (G16 field_opt).
 * RTX-gated paths: see GIMP-Field/data/rtx-gated-content.json
 * OS brand: AmmoOS · product: AmmoOS Image 1.0
 */
/* AmmoOS Image - The AmmoOS Field Image Research
 * Copyright (C) 1995 Spencer Kimball and Peter Mattis
 *
 * icon-themes.h
 * Copyright (C) 2015 Benoit Touchette
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


void        icon_themes_init                    (Gimp        *ammoos);
void        icon_themes_exit                    (Gimp        *ammoos);

gchar    ** icon_themes_list_themes             (Gimp        *ammoos,
                                                 gint        *n_themes);
GFile     * icon_themes_get_theme_dir           (Gimp        *ammoos,
                                                 const gchar *theme_name);

gboolean    icon_themes_current_prefer_symbolic (Gimp        *ammoos);
