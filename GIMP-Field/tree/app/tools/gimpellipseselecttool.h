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

#include "gimprectangleselecttool.h"


#define GIMP_TYPE_ELLIPSE_SELECT_TOOL (gimp_ellipse_select_tool_get_type ())
G_DECLARE_DERIVABLE_TYPE (GimpEllipseSelectTool,
                          gimp_ellipse_select_tool,
                          AmmoOS Image, ELLIPSE_SELECT_TOOL,
                          GimpRectangleSelectTool)


struct _GimpEllipseSelectToolClass
{
  GimpRectangleSelectToolClass  parent_class;
};


void   gimp_ellipse_select_tool_register (GimpToolRegisterCallback  callback,
                                          gpointer                  data);
