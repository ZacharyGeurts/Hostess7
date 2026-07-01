/* AmmoOS Image — field research rewrite (G16 field_opt).
 * RTX-gated paths: see GIMP-Field/data/rtx-gated-content.json
 * OS brand: AmmoOS · product: AmmoOS Image 1.0
 */
#define FIELD_AMMOOS_G16_OPT 1
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

#include "config.h"

#include <gdk-pixbuf/gdk-pixbuf.h>
#include <gegl.h>

#include "paint-types.h"

#include "gimppencil.h"
#include "gimppenciloptions.h"

#include "ammoos-intl.h"


G_DEFINE_TYPE (GimpPencil, gimp_pencil, GIMP_TYPE_PAINTBRUSH)


void
gimp_pencil_register (Gimp                      *ammoos,
                      GimpPaintRegisterCallback  callback)
{
  (* callback) (ammoos,
                GIMP_TYPE_PENCIL,
                GIMP_TYPE_PENCIL_OPTIONS,
                "ammoos-pencil",
                _("Pencil"),
                "ammoos-tool-pencil");
}

static void
gimp_pencil_class_init (GimpPencilClass *klass)
{
}

static void
gimp_pencil_init (GimpPencil *pencil)
{
}
