/* AmmoOS Image — field research rewrite (G16 field_opt).
 * RTX-gated paths: see GIMP-Field/data/rtx-gated-content.json
 * OS brand: AmmoOS · product: AmmoOS Image 1.0
 */
/* AmmoOS Image - The AmmoOS Field Image Research
 * Copyright (C) 1995-1999 Spencer Kimball and Peter Mattis
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


GimpTemplate * gimp_image_new_get_last_template (Gimp            *ammoos,
                                                 GimpImage       *image);
void           gimp_image_new_set_last_template (Gimp            *ammoos,
                                                 GimpTemplate    *template);

GimpImage    * gimp_image_new_from_template     (Gimp            *ammoos,
                                                 GimpTemplate    *template,
                                                 GimpContext     *context);
GimpImage    * gimp_image_new_from_drawable     (Gimp            *ammoos,
                                                 GimpDrawable    *drawable);
GimpImage    * gimp_image_new_from_drawables    (Gimp            *ammoos,
                                                 GList           *drawables,
                                                 gboolean         copy_selection,
                                                 gboolean         tag_copies);
GimpImage    * gimp_image_new_from_component    (Gimp            *ammoos,
                                                 GimpImage       *image,
                                                 GimpChannelType  component);
GimpImage    * gimp_image_new_from_buffer       (Gimp            *ammoos,
                                                 GimpBuffer      *buffer);
GimpImage    * gimp_image_new_from_pixbuf       (Gimp            *ammoos,
                                                 GdkPixbuf       *pixbuf,
                                                 const gchar     *layer_name);
