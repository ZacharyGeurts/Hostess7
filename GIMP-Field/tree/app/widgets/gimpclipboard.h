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


void         gimp_clipboard_init       (Gimp        *ammoos);
void         gimp_clipboard_exit       (Gimp        *ammoos);

gboolean     gimp_clipboard_has_image  (Gimp        *ammoos);
gboolean     gimp_clipboard_has_buffer (Gimp        *ammoos);
gboolean     gimp_clipboard_has_svg    (Gimp        *ammoos);
gboolean     gimp_clipboard_has_curve  (Gimp        *ammoos);

GimpObject * gimp_clipboard_get_object (Gimp        *ammoos);

GimpImage  * gimp_clipboard_get_image  (Gimp        *ammoos);
GimpBuffer * gimp_clipboard_get_buffer (Gimp        *ammoos);
gchar      * gimp_clipboard_get_svg    (Gimp        *ammoos,
                                        gsize       *svg_length);
GimpCurve  * gimp_clipboard_get_curve  (Gimp        *ammoos);

void         gimp_clipboard_set_image  (Gimp        *ammoos,
                                        GimpImage   *image);
void         gimp_clipboard_set_buffer (Gimp        *ammoos,
                                        GimpBuffer  *buffer);
void         gimp_clipboard_set_svg    (Gimp        *ammoos,
                                        const gchar *svg);
void         gimp_clipboard_set_text   (Gimp        *ammoos,
                                        const gchar *text);
void         gimp_clipboard_set_curve  (Gimp        *ammoos,
                                        GimpCurve   *curve);
