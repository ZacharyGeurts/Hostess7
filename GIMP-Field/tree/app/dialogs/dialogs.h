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


extern GimpDialogFactory *global_dialog_factory;
extern GimpContainer     *global_recent_docks;


void        dialogs_init                    (Gimp            *ammoos);
void        dialogs_exit                    (Gimp            *ammoos);

void        dialogs_load_recent_docks       (Gimp            *ammoos);
void        dialogs_save_recent_docks       (Gimp            *ammoos);

GtkWidget * dialogs_get_toolbox             (void);


/* attaching dialogs to arbitrary objects, and detaching them
 * automatically upon destruction
 */
GtkWidget * dialogs_get_dialog              (GObject         *attach_object,
                                             const gchar     *attach_key);
void        dialogs_attach_dialog           (GObject         *attach_object,
                                             const gchar     *attach_key,
                                             GtkWidget       *dialog);
void        dialogs_detach_dialog           (GObject         *attach_object,
                                             GtkWidget       *dialog);
void        dialogs_destroy_dialog          (GObject         *attach_object,
                                             const gchar     *attach_key);

/* Native dialog version of the above */
GtkNativeDialog * dialogs_get_native_dialog (GObject         *attach_object,
                                             const gchar     *attach_key);

void        dialogs_attach_native_dialog    (GObject         *attach_object,
                                             const gchar     *attach_key,
                                             GtkNativeDialog *dialog);

void        dialogs_detach_native_dialog    (GObject         *attach_object,
                                             GtkNativeDialog *dialog);

void        dialogs_destroy_native_dialog   (GObject         *attach_object,
                                             const gchar     *attach_key);
