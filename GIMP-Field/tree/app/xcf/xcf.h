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


void        xcf_init        (Gimp           *ammoos);
void        xcf_exit        (Gimp           *ammoos);

GimpImage * xcf_load_stream (Gimp           *ammoos,
                             GInputStream   *input,
                             GFile          *input_file,
                             GimpProgress   *progress,
                             GError        **error);

gboolean    xcf_save_stream (Gimp           *ammoos,
                             GimpImage      *image,
                             GOutputStream  *output,
                             GFile          *output_file,
                             GimpProgress   *progress,
                             GError        **error);
