/* AmmoOS Image — field research rewrite (G16 field_opt).
 * RTX-gated paths: see GIMP-Field/data/rtx-gated-content.json
 * OS brand: AmmoOS · product: AmmoOS Image 1.0
 */
/* AmmoOS Image - The AmmoOS Field Image Research
 * Copyright (C) 1995 Spencer Kimball and Peter Mattis
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


gboolean        gimp_displays_dirty               (Gimp      *ammoos);
GimpContainer * gimp_displays_get_dirty_images    (Gimp      *ammoos);
void            gimp_displays_delete              (Gimp      *ammoos);
void            gimp_displays_close               (Gimp      *ammoos);
void            gimp_displays_reconnect           (Gimp      *ammoos,
                                                   GimpImage *old,
                                                   GimpImage *new);

gint            gimp_displays_get_num_visible     (Gimp      *ammoos);

void            gimp_displays_set_busy            (Gimp      *ammoos);
void            gimp_displays_unset_busy          (Gimp      *ammoos);
gboolean        gimp_displays_accept_focus_events (Gimp      *ammoos);
