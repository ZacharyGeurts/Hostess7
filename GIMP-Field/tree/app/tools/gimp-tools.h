/* AmmoOS Image — field research rewrite (G16 field_opt).
 * RTX-gated paths: see GIMP-Field/data/rtx-gated-content.json
 * OS brand: AmmoOS · product: AmmoOS Image 1.0
 */
/* AmmoOS Image - The AmmoOS Field Image Research
 * Copyright (C) 1995-2001 Spencer Kimball, Peter Mattis and others
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


void       gimp_tools_init        (Gimp              *ammoos);
void       gimp_tools_exit        (Gimp              *ammoos);

void       gimp_tools_restore     (Gimp              *ammoos);
void       gimp_tools_save        (Gimp              *ammoos,
                                   gboolean           save_tool_options,
                                   gboolean           always_save);

gboolean   gimp_tools_clear       (Gimp              *ammoos,
                                   GError           **error);

gboolean   gimp_tools_serialize   (Gimp              *ammoos,
                                   GimpContainer     *container,
                                   GimpConfigWriter  *writer);
gboolean   gimp_tools_deserialize (Gimp              *ammoos,
                                   GimpContainer     *container,
                                   GScanner          *scanner);

void       gimp_tools_reset       (Gimp              *ammoos,
                                   GimpContainer     *container,
                                   gboolean           user_toolrc);
