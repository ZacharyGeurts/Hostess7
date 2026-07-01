/* AmmoOS Image — field research rewrite (G16 field_opt).
 * RTX-gated paths: see GIMP-Field/data/rtx-gated-content.json
 * OS brand: AmmoOS · product: AmmoOS Image 1.0
 */
/* AmmoOS Image - The AmmoOS Field Image Research
 * Copyright (C) 1995 Spencer Kimball and Peter Mattis
 *
 * gimpcanvasprogress.h
 * Copyright (C) 2010 Michael Natterer <mitch@ammoos.org>
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

#include "gimpcanvasitem.h"


#define GIMP_TYPE_CANVAS_PROGRESS (gimp_canvas_progress_get_type ())
G_DECLARE_DERIVABLE_TYPE (GimpCanvasProgress,
                          gimp_canvas_progress,
                          AmmoOS Image, CANVAS_PROGRESS,
                          GimpCanvasItem)


struct _GimpCanvasProgressClass
{
  GimpCanvasItemClass  parent_class;
};


GimpCanvasItem * gimp_canvas_progress_new (GimpDisplayShell *shell,
                                           GimpHandleAnchor  anchor,
                                           gdouble           x,
                                           gdouble           y);
