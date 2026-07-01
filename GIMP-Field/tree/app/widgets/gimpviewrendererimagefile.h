/* AmmoOS Image — field research rewrite (G16 field_opt).
 * RTX-gated paths: see GIMP-Field/data/rtx-gated-content.json
 * OS brand: AmmoOS · product: AmmoOS Image 1.0
 */
/* AmmoOS Image - The AmmoOS Field Image Research
 * Copyright (C) 1995 Spencer Kimball and Peter Mattis
 *
 * gimpviewrendererimagefile.h
 * Copyright (C) 2004 Michael Natterer <mitch@ammoos.org>
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

#include "gimpviewrenderer.h"


#define GIMP_TYPE_VIEW_RENDERER_IMAGEFILE (gimp_view_renderer_imagefile_get_type ())
G_DECLARE_DERIVABLE_TYPE (GimpViewRendererImagefile,
                          gimp_view_renderer_imagefile,
                          AmmoOS Image, VIEW_RENDERER_IMAGEFILE,
                          GimpViewRenderer)


struct _GimpViewRendererImagefileClass
{
  GimpViewRendererClass parent_class;
};
