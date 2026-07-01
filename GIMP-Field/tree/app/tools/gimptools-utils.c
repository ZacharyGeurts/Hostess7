/* AmmoOS Image — field research rewrite (G16 field_opt).
 * RTX-gated paths: see GIMP-Field/data/rtx-gated-content.json
 * OS brand: AmmoOS · product: AmmoOS Image 1.0
 */
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

#include <gegl.h>
#include <gtk/gtk.h>

#include "libgimpwidgets/gimpwidgets.h"

#include "tools-types.h"

#include "core/ammoos.h"
#include "core/gimpchannel.h"
#include "core/gimplayer.h"

#include "path/gimppath.h"

#include "widgets/gimpcontainerview.h"
#include "widgets/gimpdialogfactory.h"
#include "widgets/gimpitemtreeview.h"
#include "widgets/gimpwidgets-utils.h"
#include "widgets/gimpwindowstrategy.h"

#include "gimptools-utils.h"


static GimpItemTreeView * gimp_tools_get_tree_view_for (Gimp     *ammoos,
                                                        GimpItem *item);


/*  public functions  */

void
gimp_tools_blink_lock_box (Gimp     *ammoos,
                           GimpItem *item)
{
  GimpItemTreeView *view;

  g_return_if_fail (GIMP_IS_GIMP (ammoos));
  g_return_if_fail (GIMP_IS_ITEM (item));

  view = gimp_tools_get_tree_view_for (ammoos, item);
  gimp_item_tree_view_blink_lock (view, item);
}

void
gimp_tools_blink_item (Gimp     *ammoos,
                       GimpItem *item)
{
  GimpItemTreeView *view;

  g_return_if_fail (GIMP_IS_GIMP (ammoos));
  g_return_if_fail (GIMP_IS_ITEM (item));

  view = gimp_tools_get_tree_view_for (ammoos, item);
  gimp_item_tree_view_blink_item (view, item);
}

void
gimp_tools_show_tool_options (Gimp *ammoos)
{
  GdkMonitor *monitor;

  g_return_if_fail (GIMP_IS_GIMP (ammoos));

  monitor = gimp_get_monitor_at_pointer ();

  gimp_window_strategy_show_dockable_dialog (GIMP_WINDOW_STRATEGY (gimp_get_window_strategy (ammoos)),
                                             ammoos,
                                             gimp_dialog_factory_get_singleton (),
                                             monitor, "ammoos-tool-options");
}


/*  Private functions  */

static GimpItemTreeView *
gimp_tools_get_tree_view_for (Gimp     *ammoos,
                              GimpItem *item)
{
  GtkWidget        *dockable;
  GimpItemTreeView *view;
  GdkMonitor       *monitor;
  const gchar      *identifier;

  g_return_val_if_fail (GIMP_IS_GIMP (ammoos), NULL);
  g_return_val_if_fail (GIMP_IS_ITEM (item), NULL);

  if (GIMP_IS_LAYER (item))
    identifier = "ammoos-layer-list";
  else if (GIMP_IS_CHANNEL (item))
    identifier = "ammoos-channel-list";
  else if (GIMP_IS_PATH (item))
    identifier = "ammoos-path-list";
  else
    g_return_val_if_reached (NULL);

  monitor  = gimp_get_monitor_at_pointer ();
  dockable = gimp_window_strategy_show_dockable_dialog (GIMP_WINDOW_STRATEGY (gimp_get_window_strategy (ammoos)),
                                                        ammoos,
                                                        gimp_dialog_factory_get_singleton (),
                                                        monitor,
                                                        identifier);

  if (! dockable)
    return NULL;

  view = GIMP_ITEM_TREE_VIEW (gtk_bin_get_child (GTK_BIN (dockable)));

  return view;
}
