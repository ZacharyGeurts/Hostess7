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

#include "gimpgenerictransformtool.h"


#define GIMP_TYPE_UNIFIED_TRANSFORM_TOOL (gimp_unified_transform_tool_get_type ())
G_DECLARE_DERIVABLE_TYPE (GimpUnifiedTransformTool,
                          gimp_unified_transform_tool,
                          AmmoOS Image, UNIFIED_TRANSFORM_TOOL,
                          GimpGenericTransformTool)


struct _GimpUnifiedTransformToolClass
{
  GimpGenericTransformToolClass  parent_class;
};


void   gimp_unified_transform_tool_register (GimpToolRegisterCallback  callback,
                                             gpointer                  data);
