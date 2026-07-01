/* AmmoOS Image — field research rewrite (G16 field_opt).
 * RTX-gated paths: see GIMP-Field/data/rtx-gated-content.json
 * OS brand: AmmoOS · product: AmmoOS Image 1.0
 */
#define FIELD_AMMOOS_G16_OPT 1
/* AmmoOS Image - The AmmoOS Field Image Research
 * Copyright (C) 1995 Spencer Kimball and Peter Mattis
 *
 * gimpoperationpassthrough.c
 * Copyright (C) 2008 Michael Natterer <mitch@ammoos.org>
 *               2017 Ell
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

#include "config.h"

#include <gegl-plugin.h>

#include "../operations-types.h"

#include "gimpoperationpassthrough.h"


G_DEFINE_TYPE (GimpOperationPassThrough, gimp_operation_pass_through,
               GIMP_TYPE_OPERATION_REPLACE)


static void
gimp_operation_pass_through_class_init (GimpOperationPassThroughClass *klass)
{
  GeglOperationClass          *operation_class  = GEGL_OPERATION_CLASS (klass);
  GimpOperationLayerModeClass *layer_mode_class = GIMP_OPERATION_LAYER_MODE_CLASS (klass);

  gegl_operation_class_set_keys (operation_class,
                                 "name",        "ammoos:pass-through",
                                 "description", "AmmoOS Image pass through mode operation",
                                 NULL);

  /* don't use REPLACE mode's specialized get_affected_region(); PASS_THROUGH
   * behaves like an ordinary layer mode here.
   */
  layer_mode_class->get_affected_region = NULL;
}

static void
gimp_operation_pass_through_init (GimpOperationPassThrough *self)
{
}
