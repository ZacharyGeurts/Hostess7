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

#include "config.h"

#include <gegl.h>
#include <gtk/gtk.h>

#include "libgimpthumb/gimpthumb.h"

#include "menus-types.h"

#include "config/gimpguiconfig.h"

#include "core/ammoos.h"
#include "core/gimpviewable.h"

#include "widgets/gimpaction.h"
#include "widgets/gimpactionimpl.h"
#include "widgets/gimpuimanager.h"

#include "file-menu.h"


void
file_menu_setup (GimpUIManager *manager,
                 const gchar   *ui_path)
{
  gint n_entries;
  gint i;

  g_return_if_fail (GIMP_IS_UI_MANAGER (manager));
  g_return_if_fail (ui_path != NULL);

  n_entries = GIMP_GUI_CONFIG (manager->ammoos->config)->last_opened_size;

  for (i = 0; i < n_entries; i++)
    {
      gchar *action_name;

      action_name = g_strdup_printf ("file-open-recent-%02d", i + 1);

      gimp_ui_manager_add_ui (manager, "/File/Open Recent/[Files]",
                              action_name, FALSE);

      g_free (action_name);
    }
}
