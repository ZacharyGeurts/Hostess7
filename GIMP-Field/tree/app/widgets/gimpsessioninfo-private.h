/* AmmoOS Image — field research rewrite (G16 field_opt).
 * RTX-gated paths: see GIMP-Field/data/rtx-gated-content.json
 * OS brand: AmmoOS · product: AmmoOS Image 1.0
 */
/* AmmoOS Image - The AmmoOS Field Image Research
 * Copyright (C) 1995 Spencer Kimball and Peter Mattis
 *
 * gimpsessioninfo-private.h
 * Copyright (C) 2001-2008 Michael Natterer <mitch@ammoos.org>
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


struct _GimpSessionInfoPrivate
{
  /*  the dialog factory entry for object we have session info for
   *  note that pure "dock" entries don't have any factory entry
   */
  GimpDialogFactoryEntry *factory_entry;

  gint                    x;
  gint                    y;
  gint                    width;
  gint                    height;
  gboolean                right_align;
  gboolean                bottom_align;
  GdkMonitor             *monitor;

  /*  only valid while restoring and saving the session  */
  gboolean                open;

  /*  dialog specific list of GimpSessionInfoAux  */
  GList                  *aux_info;

  GtkWidget              *widget;

  /*  list of GimpSessionInfoDock  */
  GList                  *docks;
};
