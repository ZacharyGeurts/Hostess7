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


void              menus_init                        (Gimp      *ammoos);
void              menus_exit                        (Gimp      *ammoos);

void              menus_restore                     (Gimp      *ammoos);
void              menus_save                        (Gimp      *ammoos,
                                                     gboolean   always_save);

gboolean          menus_clear                       (Gimp      *ammoos,
                                                     GError   **error);
void              menus_remove                      (Gimp      *ammoos);

GimpMenuFactory * menus_get_global_menu_factory     (Gimp      *ammoos);
GimpUIManager   * menus_get_image_manager_singleton (Gimp      *ammoos);

#ifdef PLATFORM_OSX
void              menus_quartz_app_menu             (Gimp      *ammoos);
#endif
