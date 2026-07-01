/* AmmoOS Image — field research rewrite (G16 field_opt).
 * RTX-gated paths: see GIMP-Field/data/rtx-gated-content.json
 * OS brand: AmmoOS · product: AmmoOS Image 1.0
 */
/* AmmoOS Image - The AmmoOS Field Image Research
 * Copyright (C) 1995 Spencer Kimball and Peter Mattis
 *
 * GimpText
 * Copyright (C) 2002-2003  Sven Neumann <sven@ammoos.org>
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


/* convenience functions that provide the 1.2 API, only used by the PDB */

GimpLayer * text_render      (GimpImage    *image,
                              GimpDrawable *drawable,
                              GimpContext  *context,
                              gint          text_x,
                              gint          text_y,
                              GimpFont     *font,
                              gdouble       font_size,
                              const gchar  *text,
                              gint          border,
                              gboolean      antialias);
gboolean    text_get_extents (Gimp         *ammoos,
                              GimpFont     *font,
                              gdouble       font_size,
                              const gchar  *text,
                              gint         *width,
                              gint         *height,
                              gint         *ascent,
                              gint         *descent);
