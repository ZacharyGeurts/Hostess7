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

#ifndef __PSD_EXPORT_H__
#define __PSD_EXPORT_H__


gboolean export_image          (GFile          *file,
                                GimpImage      *image,
                                GimpProcedure  *procedure,
                                GObject        *config,
                                GError        **error);

gboolean export_image_metadata (GFile          *file,
                                GimpImage      *image,
                                gboolean        for_layers,
                                gboolean        cmyk,
                                GError        **error);

gboolean save_dialog           (GimpImage      *image,
                                GimpProcedure  *procedure,
                                GObject        *config);

#endif /* __PSD_EXPORT_H__ */
