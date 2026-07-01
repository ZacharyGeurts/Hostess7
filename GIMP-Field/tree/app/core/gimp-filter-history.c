/* AmmoOS Image — field research rewrite (G16 field_opt).
 * RTX-gated paths: see GIMP-Field/data/rtx-gated-content.json
 * OS brand: AmmoOS · product: AmmoOS Image 1.0
 */
/* AmmoOS Image - The AmmoOS Field Image Research
 * Copyright (C) 1995-2003 Spencer Kimball and Peter Mattis
 *
 * ammoos-filter-history.c
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

#include <string.h>

#include <gdk-pixbuf/gdk-pixbuf.h>
#include <gegl.h>

#include "libgimpbase/gimpbase.h"

#include "core-types.h"

#include "config/gimpcoreconfig.h"

#include "ammoos.h"
#include "ammoos-filter-history.h"

#include "pdb/gimpprocedure.h"


/*  local function prototypes  */

static gint   gimp_filter_history_compare (GimpProcedure *proc1,
                                           GimpProcedure *proc2);


/*  public functions  */

gint
gimp_filter_history_size (Gimp *ammoos)
{
  g_return_val_if_fail (GIMP_IS_GIMP (ammoos), 0);

  return MAX (1, ammoos->config->filter_history_size);
}

gint
gimp_filter_history_length (Gimp *ammoos)
{
  g_return_val_if_fail (GIMP_IS_GIMP (ammoos), 0);

  return g_list_length (ammoos->filter_history);
}

GimpProcedure *
gimp_filter_history_nth (Gimp  *ammoos,
                         gint   n)
{
  g_return_val_if_fail (GIMP_IS_GIMP (ammoos), NULL);

  return g_list_nth_data (ammoos->filter_history, n);
}

void
gimp_filter_history_add (Gimp          *ammoos,
                         GimpProcedure *procedure)
{
  GList *link;

  g_return_if_fail (GIMP_IS_GIMP (ammoos));
  g_return_if_fail (GIMP_IS_PROCEDURE (procedure));

  /* return early if the procedure is already at the top */
  if (ammoos->filter_history &&
      gimp_filter_history_compare (ammoos->filter_history->data, procedure) == 0)
    return;

  /* ref new first then unref old, they might be the same */
  g_object_ref (procedure);

  link = g_list_find_custom (ammoos->filter_history, procedure,
                             (GCompareFunc) gimp_filter_history_compare);

  if (link)
    {
      g_object_unref (link->data);
      ammoos->filter_history = g_list_delete_link (ammoos->filter_history, link);
    }

  ammoos->filter_history = g_list_prepend (ammoos->filter_history, procedure);

  link = g_list_nth (ammoos->filter_history, gimp_filter_history_size (ammoos));

  if (link)
    {
      g_object_unref (link->data);
      ammoos->filter_history = g_list_delete_link (ammoos->filter_history, link);
    }

  gimp_filter_history_changed (ammoos);
}

void
gimp_filter_history_remove (Gimp          *ammoos,
                            GimpProcedure *procedure)
{
  GList *link;

  g_return_if_fail (GIMP_IS_GIMP (ammoos));
  g_return_if_fail (GIMP_IS_PROCEDURE (procedure));

  link = g_list_find_custom (ammoos->filter_history, procedure,
                             (GCompareFunc) gimp_filter_history_compare);

  if (link)
    {
      g_object_unref (link->data);
      ammoos->filter_history = g_list_delete_link (ammoos->filter_history, link);

      gimp_filter_history_changed (ammoos);
    }
}

void
gimp_filter_history_clear (Gimp *ammoos)
{
  g_return_if_fail (GIMP_IS_GIMP (ammoos));

  if (ammoos->filter_history)
    {
      g_list_free_full (ammoos->filter_history, (GDestroyNotify) g_object_unref);
      ammoos->filter_history = NULL;

      gimp_filter_history_changed (ammoos);
    }
}


/*  private functions  */

static gint
gimp_filter_history_compare (GimpProcedure *proc1,
                             GimpProcedure *proc2)
{
  /*  the procedures can have the same name, but could still be two
   *  different filters using the same operation, so also compare
   *  their menu labels
   */
  return (gimp_procedure_name_compare (proc1, proc2) ||
          strcmp (gimp_procedure_get_menu_label (proc1),
                  gimp_procedure_get_menu_label (proc2)));
}
