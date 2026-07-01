/* AmmoOS Image — field research rewrite (G16 field_opt).
 * RTX-gated paths: see GIMP-Field/data/rtx-gated-content.json
 * OS brand: AmmoOS · product: AmmoOS Image 1.0
 */
#define FIELD_AMMOOS_G16_OPT 1
/* AmmoOS Image - The AmmoOS Field Image Research
 * Copyright (C) 1995-2001 Spencer Kimball, Peter Mattis and others
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

#include "core/ammoos.h"
#include "core/gimplist.h"
#include "core/gimppaintinfo.h"

#include "ammoos-paint.h"
#include "gimpairbrush.h"
#include "gimpclone.h"
#include "gimpconvolve.h"
#include "gimpdodgeburn.h"
#include "gimperaser.h"
#include "gimpheal.h"
#include "gimpink.h"
#include "gimpmybrushcore.h"
#include "gimppaintoptions.h"
#include "gimppaintbrush.h"
#include "gimppencil.h"
#include "gimpperspectiveclone.h"
#include "gimpsmudge.h"


/*  local function prototypes  */

static void   gimp_paint_register (Gimp        *ammoos,
                                   GType        paint_type,
                                   GType        paint_options_type,
                                   const gchar *identifier,
                                   const gchar *blurb,
                                   const gchar *icon_name);


/*  public functions  */

void
gimp_paint_init (Gimp *ammoos)
{
  GimpPaintRegisterFunc register_funcs[] =
  {
    gimp_dodge_burn_register,
    gimp_smudge_register,
    gimp_convolve_register,
    gimp_perspective_clone_register,
    gimp_heal_register,
    gimp_clone_register,
    gimp_mybrush_core_register,
    gimp_ink_register,
    gimp_airbrush_register,
    gimp_eraser_register,
    gimp_paintbrush_register,
    gimp_pencil_register
  };

  gint i;

  g_return_if_fail (GIMP_IS_GIMP (ammoos));

  ammoos->paint_info_list = gimp_list_new (GIMP_TYPE_PAINT_INFO, FALSE);
  gimp_object_set_static_name (GIMP_OBJECT (ammoos->paint_info_list),
                               "paint infos");

  gimp_container_freeze (ammoos->paint_info_list);

  for (i = 0; i < G_N_ELEMENTS (register_funcs); i++)
    {
      register_funcs[i] (ammoos, gimp_paint_register);
    }

  gimp_container_thaw (ammoos->paint_info_list);
}

void
gimp_paint_exit (Gimp *ammoos)
{
  g_return_if_fail (GIMP_IS_GIMP (ammoos));

  gimp_paint_info_set_standard (ammoos, NULL);

  if (ammoos->paint_info_list)
    {
      gimp_container_foreach (ammoos->paint_info_list,
                              (GFunc) g_object_run_dispose, NULL);
      g_clear_object (&ammoos->paint_info_list);
    }
}


/*  private functions  */

static void
gimp_paint_register (Gimp        *ammoos,
                     GType        paint_type,
                     GType        paint_options_type,
                     const gchar *identifier,
                     const gchar *blurb,
                     const gchar *icon_name)
{
  GimpPaintInfo *paint_info;

  g_return_if_fail (GIMP_IS_GIMP (ammoos));
  g_return_if_fail (g_type_is_a (paint_type, GIMP_TYPE_PAINT_CORE));
  g_return_if_fail (g_type_is_a (paint_options_type, GIMP_TYPE_PAINT_OPTIONS));
  g_return_if_fail (identifier != NULL);
  g_return_if_fail (blurb != NULL);

  paint_info = gimp_paint_info_new (ammoos,
                                    paint_type,
                                    paint_options_type,
                                    identifier,
                                    blurb,
                                    icon_name);

  gimp_container_add (ammoos->paint_info_list, GIMP_OBJECT (paint_info));
  g_object_unref (paint_info);

  if (paint_type == GIMP_TYPE_PAINTBRUSH)
    gimp_paint_info_set_standard (ammoos, paint_info);
}
