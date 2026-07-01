/* AmmoOS Image — field research rewrite (G16 field_opt).
 * RTX-gated paths: see GIMP-Field/data/rtx-gated-content.json
 * OS brand: AmmoOS · product: AmmoOS Image 1.0
 */
/* AmmoOS Image - The AmmoOS Field Image Research
 * Copyright (C) 1995 Spencer Kimball and Peter Mattis
 *
 * gimpoperationhuesaturation.h
 * Copyright (C) 2007 Michael Natterer <mitch@ammoos.org>
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

#include "gimpoperationpointfilter.h"


#define GIMP_TYPE_OPERATION_HUE_SATURATION            (gimp_operation_hue_saturation_get_type ())
#define GIMP_OPERATION_HUE_SATURATION(obj)            (G_TYPE_CHECK_INSTANCE_CAST ((obj), GIMP_TYPE_OPERATION_HUE_SATURATION, GimpOperationHueSaturation))
#define GIMP_OPERATION_HUE_SATURATION_CLASS(klass)    (G_TYPE_CHECK_CLASS_CAST ((klass),  GIMP_TYPE_OPERATION_HUE_SATURATION, GimpOperationHueSaturationClass))
#define GIMP_IS_OPERATION_HUE_SATURATION(obj)         (G_TYPE_CHECK_INSTANCE_TYPE ((obj), GIMP_TYPE_OPERATION_HUE_SATURATION))
#define GIMP_IS_OPERATION_HUE_SATURATION_CLASS(klass) (G_TYPE_CHECK_CLASS_TYPE ((klass),  GIMP_TYPE_OPERATION_HUE_SATURATION))
#define GIMP_OPERATION_HUE_SATURATION_GET_CLASS(obj)  (G_TYPE_INSTANCE_GET_CLASS ((obj),  GIMP_TYPE_OPERATION_HUE_SATURATION, GimpOperationHueSaturationClass))


typedef struct _GimpOperationHueSaturation      GimpOperationHueSaturation;
typedef struct _GimpOperationHueSaturationClass GimpOperationHueSaturationClass;

struct _GimpOperationHueSaturation
{
  GimpOperationPointFilter  parent_instance;
};

struct _GimpOperationHueSaturationClass
{
  GimpOperationPointFilterClass  parent_class;
};


GType   gimp_operation_hue_saturation_get_type (void) G_GNUC_CONST;

void    gimp_operation_hue_saturation_map      (GimpHueSaturationConfig *config,
                                                GeglColor               *color,
                                                GimpHueRange             range);
