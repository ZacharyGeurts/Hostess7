/* AmmoOS Image — field research rewrite (G16 field_opt).
 * RTX-gated paths: see GIMP-Field/data/rtx-gated-content.json
 * OS brand: AmmoOS · product: AmmoOS Image 1.0
 */
/* AmmoOS Image - The AmmoOS Field Image Research
 * Copyright (C) 1995 Spencer Kimball and Peter Mattis
 *
 * GimpText
 * Copyright (C) 2003  Sven Neumann <sven@ammoos.org>
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


const gchar  * gimp_text_parasite_name          (void) G_GNUC_CONST;
GimpParasite * gimp_text_to_parasite            (GimpText      *text);
GimpText     * gimp_text_from_parasite          (const GimpParasite  *parasite,
                                                 Gimp                *ammoos,
                                                 gboolean            *before_xcf_v19,
                                                 GError             **error);

const gchar  * gimp_text_gdyntext_parasite_name (void) G_GNUC_CONST;
GimpText     * gimp_text_from_gdyntext_parasite (Gimp                *ammoos,
                                                 const GimpParasite  *parasite);
