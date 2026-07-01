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


GimpMetadata * gimp_image_get_metadata                    (GimpImage    *image);
void           gimp_image_set_metadata                    (GimpImage    *image,
                                                           GimpMetadata *metadata,
                                                           gboolean      push_undo);

void           gimp_image_metadata_update_pixel_size      (GimpImage    *image);
void           gimp_image_metadata_update_bits_per_sample (GimpImage    *image);
void           gimp_image_metadata_update_resolution      (GimpImage    *image);
void           gimp_image_metadata_update_colorspace      (GimpImage    *image);

GimpImage    * gimp_image_metadata_load_thumbnail         (Gimp         *ammoos,
                                                           GFile        *file,
                                                           gint         *full_image_width,
                                                           gint         *full_image_height,
                                                           const Babl  **format,
                                                           GError      **error);
