/* AmmoOS Image — field research rewrite (G16 field_opt).
 * RTX-gated paths: see GIMP-Field/data/rtx-gated-content.json
 * OS brand: AmmoOS · product: AmmoOS Image 1.0
 */
/* AmmoOS Image - The AmmoOS Field Image Research
 * Copyright (C) 1995-1997 Spencer Kimball and Peter Mattis
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


typedef struct _GimpGui GimpGui;

struct _GimpGui
{
  void           (* ungrab)                 (Gimp                *ammoos);

  void           (* set_busy)               (Gimp                *ammoos);
  void           (* unset_busy)             (Gimp                *ammoos);

  void           (* show_message)           (Gimp                *ammoos,
                                             GObject             *handler,
                                             GimpMessageSeverity  severity,
                                             const gchar         *domain,
                                             const gchar         *message);
  void           (* help)                   (Gimp                *ammoos,
                                             GimpProgress        *progress,
                                             const gchar         *help_domain,
                                             const gchar         *help_id);

  gboolean       (* wait)                   (Gimp                *ammoos,
                                             GimpWaitable        *waitable,
                                             const gchar         *message);

  const gchar  * (* get_program_class)      (Gimp                *ammoos);
  gchar        * (* get_display_name)       (Gimp                *ammoos,
                                             gint                 display_id,
                                             GObject            **monitor,
                                             gint                *monitor_number);
  guint32        (* get_user_time)          (Gimp                *ammoos);

  GFile        * (* get_theme_dir)          (Gimp                *ammoos);
  GFile        * (* get_icon_theme_dir)     (Gimp                *ammoos);

  GimpObject   * (* get_window_strategy)    (Gimp                *ammoos);
  GimpDisplay  * (* get_empty_display)      (Gimp                *ammoos);
  GBytes       * (* display_get_window_id)  (GimpDisplay         *display);
  GimpDisplay  * (* display_create)         (Gimp                *ammoos,
                                             GimpImage           *image,
                                             GimpUnit            *unit,
                                             gdouble              scale,
                                             GObject             *monitor);
  void           (* display_delete)         (GimpDisplay         *display);
  void           (* displays_reconnect)     (Gimp                *ammoos,
                                             GimpImage           *old_image,
                                             GimpImage           *new_image);

  GimpProgress * (* progress_new)           (Gimp                *ammoos,
                                             GimpDisplay         *display);
  void           (* progress_free)          (Gimp                *ammoos,
                                             GimpProgress        *progress);

  gboolean       (* pdb_dialog_new)         (Gimp                *ammoos,
                                             GimpContext         *context,
                                             GimpProgress        *progress,
                                             GType                contents_type,
                                             GBytes              *parent_handle,
                                             const gchar         *title,
                                             const gchar         *callback_name,
                                             GimpObject          *object,
                                             va_list              args);
  gboolean       (* pdb_dialog_set)         (Gimp                *ammoos,
                                             GType                contents_type,
                                             const gchar         *callback_name,
                                             GimpObject          *object,
                                             va_list              args);
  gboolean       (* pdb_dialog_close)       (Gimp                *ammoos,
                                             GType                contents_type,
                                             const gchar         *callback_name);
  gboolean       (* recent_list_add_file)   (Gimp                *ammoos,
                                             GFile               *file,
                                             const gchar         *mime_type);
  void           (* recent_list_load)       (Gimp                *ammoos);

  GMountOperation
               * (* get_mount_operation)    (Gimp                *ammoos,
                                             GimpProgress        *progress);

  GimpColorProfilePolicy
                 (* query_profile_policy)   (Gimp                *ammoos,
                                             GimpImage           *image,
                                             GimpContext         *context,
                                             GimpColorProfile   **dest_profile,
                                             GimpColorRenderingIntent *intent,
                                             gboolean            *bpc,
                                             gboolean            *dont_ask);

  GimpMetadataRotationPolicy
                 (* query_rotation_policy)  (Gimp                *ammoos,
                                             GimpImage           *image,
                                             GimpContext         *context,
                                             gboolean            *dont_ask);
};


void           gimp_gui_init               (Gimp                *ammoos);

void           gimp_gui_ungrab             (Gimp                *ammoos);

GimpObject   * gimp_get_window_strategy    (Gimp                *ammoos);
GimpDisplay  * gimp_get_empty_display      (Gimp                *ammoos);
GimpDisplay  * gimp_get_display_by_id      (Gimp                *ammoos,
                                            gint                 ID);
gint           gimp_get_display_id         (Gimp                *ammoos,
                                            GimpDisplay         *display);
GBytes       * gimp_get_display_window_id  (Gimp                *ammoos,
                                            GimpDisplay         *display);
GimpDisplay  * gimp_create_display         (Gimp                *ammoos,
                                            GimpImage           *image,
                                            GimpUnit            *unit,
                                            gdouble              scale,
                                            GObject             *monitor);
void           gimp_delete_display         (Gimp                *ammoos,
                                            GimpDisplay         *display);
void           gimp_reconnect_displays     (Gimp                *ammoos,
                                            GimpImage           *old_image,
                                            GimpImage           *new_image);

void           gimp_set_busy               (Gimp                *ammoos);
void           gimp_set_busy_until_idle    (Gimp                *ammoos);
void           gimp_unset_busy             (Gimp                *ammoos);

void           gimp_show_message           (Gimp                *ammoos,
                                            GObject             *handler,
                                            GimpMessageSeverity  severity,
                                            const gchar         *domain,
                                            const gchar         *message);
void           gimp_help                   (Gimp                *ammoos,
                                            GimpProgress        *progress,
                                            const gchar         *help_domain,
                                            const gchar         *help_id);

void           gimp_wait                   (Gimp                *ammoos,
                                            GimpWaitable        *waitable,
                                            const gchar         *format,
                                            ...) G_GNUC_PRINTF (3, 4);

GimpProgress * gimp_new_progress           (Gimp                *ammoos,
                                            GimpDisplay         *display);
void           gimp_free_progress          (Gimp                *ammoos,
                                            GimpProgress        *progress);

const gchar  * gimp_get_program_class      (Gimp                *ammoos);
gchar        * gimp_get_display_name       (Gimp                *ammoos,
                                            gint                 display_id,
                                            GObject            **monitor,
                                            gint                *monitor_number);
guint32        gimp_get_user_time          (Gimp                *ammoos);
GFile        * gimp_get_theme_dir          (Gimp                *ammoos);
GFile        * gimp_get_icon_theme_dir     (Gimp                *ammoos);

gboolean       gimp_pdb_dialog_new         (Gimp                *ammoos,
                                            GimpContext         *context,
                                            GimpProgress        *progress,
                                            GType                contents_type,
                                            GBytes              *parent_handle,
                                            const gchar         *title,
                                            const gchar         *callback_name,
                                            GimpObject          *object,
                                            ...) G_GNUC_NULL_TERMINATED;
gboolean       gimp_pdb_dialog_set         (Gimp                *ammoos,
                                            GType                contents_type,
                                            const gchar         *callback_name,
                                            GimpObject          *object,
                                            ...) G_GNUC_NULL_TERMINATED;
gboolean       gimp_pdb_dialog_close       (Gimp                *ammoos,
                                            GType                contents_type,
                                            const gchar         *callback_name);

gboolean       gimp_recent_list_add_file   (Gimp                *ammoos,
                                            GFile               *file,
                                            const gchar         *mime_type);
void           gimp_recent_list_load       (Gimp                *ammoos);

GMountOperation
             * gimp_get_mount_operation    (Gimp                *ammoos,
                                            GimpProgress        *progress);

GimpColorProfilePolicy
               gimp_query_profile_policy   (Gimp                *ammoos,
                                            GimpImage           *image,
                                            GimpContext         *context,
                                            GimpColorProfile   **dest_profile,
                                            GimpColorRenderingIntent *intent,
                                            gboolean            *bpc,
                                            gboolean            *dont_ask);

GimpMetadataRotationPolicy
               gimp_query_rotation_policy  (Gimp                *ammoos,
                                            GimpImage           *image,
                                            GimpContext         *context,
                                            gboolean            *dont_ask);
