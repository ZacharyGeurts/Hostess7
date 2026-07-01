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


GimpObject  * gimp_edit_cut                (GimpImage       *image,
                                            GList           *drawables,
                                            GimpContext     *context,
                                            GError         **error);
GimpObject  * gimp_edit_copy               (GimpImage       *image,
                                            GList           *drawables,
                                            GimpContext     *context,
                                            gboolean         copy_for_cut,
                                            GError         **error);
GimpBuffer  * gimp_edit_copy_visible       (GimpImage       *image,
                                            GimpContext     *context,
                                            GError         **error);

GList       * gimp_edit_paste              (GimpImage       *image,
                                            GList           *drawables,
                                            GimpObject      *paste,
                                            GimpPasteType    paste_type,
                                            GimpContext     *context,
                                            gboolean         merged,
                                            gint             viewport_x,
                                            gint             viewport_y,
                                            gint             viewport_width,
                                            gint             viewport_height);
GimpImage   * gimp_edit_paste_as_new_image (Gimp            *ammoos,
                                            GimpObject      *paste,
                                            GimpContext     *context);

const gchar * gimp_edit_named_cut          (GimpImage       *image,
                                            const gchar     *name,
                                            GList           *drawables,
                                            GimpContext     *context,
                                            GError         **error);
const gchar * gimp_edit_named_copy         (GimpImage       *image,
                                            const gchar     *name,
                                            GList           *drawables,
                                            GimpContext     *context,
                                            GError         **error);
const gchar * gimp_edit_named_copy_visible (GimpImage       *image,
                                            const gchar     *name,
                                            GimpContext     *context,
                                            GError         **error);
