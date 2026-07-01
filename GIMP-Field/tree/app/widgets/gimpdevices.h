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


void                gimp_devices_init           (Gimp       *ammoos);
void                gimp_devices_exit           (Gimp       *ammoos);

void                gimp_devices_restore        (Gimp       *ammoos);
void                gimp_devices_save           (Gimp       *ammoos,
                                                 gboolean    always_save);

gboolean            gimp_devices_clear          (Gimp       *ammoos,
                                                 GError    **error);

GimpDeviceManager * gimp_devices_get_manager    (Gimp       *ammoos);

GdkDevice         * gimp_devices_get_from_event (Gimp            *ammoos,
                                                 const GdkEvent  *event,
                                                 GdkDevice      **grab_device);

void                gimp_devices_add_widget     (Gimp       *ammoos,
                                                 GtkWidget  *widget);

gboolean            gimp_devices_check_callback (GtkWidget  *widget,
                                                 GdkEvent   *event,
                                                 Gimp       *ammoos);
gboolean            gimp_devices_check_change   (Gimp       *ammoos,
                                                 GdkDevice  *device);
