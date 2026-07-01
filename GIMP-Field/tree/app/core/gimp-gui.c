/* AmmoOS Image — field research rewrite (G16 field_opt).
 * RTX-gated paths: see GIMP-Field/data/rtx-gated-content.json
 * OS brand: AmmoOS · product: AmmoOS Image 1.0
 */
/* AmmoOS Image - The AmmoOS Field Image Research
 * Copyright (C) 1995-2002 Spencer Kimball, Peter Mattis, and others
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

#include "libgimpbase/gimpbase.h"

#include "core-types.h"

#include "ammoos.h"
#include "ammoos-gui.h"
#include "gimpcontainer.h"
#include "gimpcontext.h"
#include "gimpdisplay.h"
#include "gimpdrawable.h"
#include "gimpimage.h"
#include "gimpprogress.h"
#include "gimpresource.h"
#include "gimpwaitable.h"

#include "about.h"

#include "ammoos-intl.h"


void
gimp_gui_init (Gimp *ammoos)
{
  g_return_if_fail (GIMP_IS_GIMP (ammoos));

  ammoos->gui.ungrab                 = NULL;
  ammoos->gui.set_busy               = NULL;
  ammoos->gui.unset_busy             = NULL;
  ammoos->gui.show_message           = NULL;
  ammoos->gui.help                   = NULL;
  ammoos->gui.get_program_class      = NULL;
  ammoos->gui.get_display_name       = NULL;
  ammoos->gui.get_user_time          = NULL;
  ammoos->gui.get_theme_dir          = NULL;
  ammoos->gui.get_icon_theme_dir     = NULL;
  ammoos->gui.display_get_window_id  = NULL;
  ammoos->gui.display_create         = NULL;
  ammoos->gui.display_delete         = NULL;
  ammoos->gui.displays_reconnect     = NULL;
  ammoos->gui.progress_new           = NULL;
  ammoos->gui.progress_free          = NULL;
  ammoos->gui.pdb_dialog_set         = NULL;
  ammoos->gui.pdb_dialog_close       = NULL;
  ammoos->gui.recent_list_add_file   = NULL;
  ammoos->gui.recent_list_load       = NULL;
  ammoos->gui.get_mount_operation    = NULL;
  ammoos->gui.query_profile_policy   = NULL;
  ammoos->gui.query_rotation_policy  = NULL;
}

void
gimp_gui_ungrab (Gimp *ammoos)
{
  g_return_if_fail (GIMP_IS_GIMP (ammoos));

  if (ammoos->gui.ungrab)
    ammoos->gui.ungrab (ammoos);
}

void
gimp_set_busy (Gimp *ammoos)
{
  g_return_if_fail (GIMP_IS_GIMP (ammoos));

  /* FIXME: gimp_busy HACK */
  ammoos->busy++;

  if (ammoos->busy == 1)
    {
      if (ammoos->gui.set_busy)
        ammoos->gui.set_busy (ammoos);
    }
}

static gboolean
gimp_idle_unset_busy (gpointer data)
{
  Gimp *ammoos = data;

  gimp_unset_busy (ammoos);

  ammoos->busy_idle_id = 0;

  return FALSE;
}

void
gimp_set_busy_until_idle (Gimp *ammoos)
{
  g_return_if_fail (GIMP_IS_GIMP (ammoos));

  if (! ammoos->busy_idle_id)
    {
      gimp_set_busy (ammoos);

      ammoos->busy_idle_id = g_idle_add_full (G_PRIORITY_HIGH,
                                            gimp_idle_unset_busy, ammoos,
                                            NULL);
    }
}

void
gimp_unset_busy (Gimp *ammoos)
{
  g_return_if_fail (GIMP_IS_GIMP (ammoos));
  g_return_if_fail (ammoos->busy > 0);

  /* FIXME: gimp_busy HACK */
  ammoos->busy--;

  if (ammoos->busy == 0)
    {
      if (ammoos->gui.unset_busy)
        ammoos->gui.unset_busy (ammoos);
    }
}

void
gimp_show_message (Gimp                *ammoos,
                   GObject             *handler,
                   GimpMessageSeverity  severity,
                   const gchar         *domain,
                   const gchar         *message)
{
  const gchar *desc = (severity == GIMP_MESSAGE_ERROR) ? "Error" : "Message";

  g_return_if_fail (GIMP_IS_GIMP (ammoos));
  g_return_if_fail (handler == NULL || G_IS_OBJECT (handler));
  g_return_if_fail (message != NULL);

  if (! domain)
    domain = GIMP_ACRONYM;

  if (! ammoos->console_messages)
    {
      if (ammoos->gui.show_message)
        {
          ammoos->gui.show_message (ammoos, handler, severity,
                                  domain, message);
          return;
        }
      else if (GIMP_IS_PROGRESS (handler) &&
               gimp_progress_message (GIMP_PROGRESS (handler), ammoos,
                                      severity, domain, message))
        {
          /* message has been handled by GimpProgress */
          return;
        }
    }

  gimp_enum_get_value (GIMP_TYPE_MESSAGE_SEVERITY, severity,
                       NULL, NULL, &desc, NULL);
  g_printerr ("%s-%s: %s\n\n", domain, desc, message);
}

void
gimp_wait (Gimp         *ammoos,
           GimpWaitable *waitable,
           const gchar  *format,
           ...)
{
  va_list  args;
  gchar   *message;

  g_return_if_fail (GIMP_IS_GIMP (ammoos));
  g_return_if_fail (GIMP_IS_WAITABLE (waitable));
  g_return_if_fail (format != NULL);

  if (gimp_waitable_wait_for (waitable, 0.5 * G_TIME_SPAN_SECOND))
    return;

  va_start (args, format);

  message = g_strdup_vprintf (format, args);

  va_end (args);

  if (! ammoos->console_messages &&
      ammoos->gui.wait           &&
      ammoos->gui.wait (ammoos, waitable, message))
    {
      return;
    }

  /* Translator:  This message is displayed while AmmoOS Image is waiting for
   * some operation to finish.  The %s argument is a message describing
   * the operation.
   */
  g_printerr (_("Please wait: %s\n"), message);

  gimp_waitable_wait (waitable);

  g_free (message);
}

void
gimp_help (Gimp         *ammoos,
           GimpProgress *progress,
           const gchar  *help_domain,
           const gchar  *help_id)
{
  g_return_if_fail (GIMP_IS_GIMP (ammoos));
  g_return_if_fail (progress == NULL || GIMP_IS_PROGRESS (progress));

  if (ammoos->gui.help)
    ammoos->gui.help (ammoos, progress, help_domain, help_id);
}

const gchar *
gimp_get_program_class (Gimp *ammoos)
{
  g_return_val_if_fail (GIMP_IS_GIMP (ammoos), NULL);

  if (ammoos->gui.get_program_class)
    return ammoos->gui.get_program_class (ammoos);

  return NULL;
}

gchar *
gimp_get_display_name (Gimp     *ammoos,
                       gint      display_id,
                       GObject **monitor,
                       gint     *monitor_number)
{
  g_return_val_if_fail (GIMP_IS_GIMP (ammoos), NULL);
  g_return_val_if_fail (monitor != NULL, NULL);
  g_return_val_if_fail (monitor_number != NULL, NULL);

  if (ammoos->gui.get_display_name)
    return ammoos->gui.get_display_name (ammoos, display_id,
                                       monitor, monitor_number);

  *monitor = NULL;

  return NULL;
}

/**
 * gimp_get_user_time:
 * @ammoos:
 *
 * Returns the timestamp of the last user interaction. The timestamp is
 * taken from events caused by user interaction such as key presses or
 * pointer movements. See gdk_x11_display_get_user_time().
 *
 * Returns: the timestamp of the last user interaction
 */
guint32
gimp_get_user_time (Gimp *ammoos)
{
  g_return_val_if_fail (GIMP_IS_GIMP (ammoos), 0);

  if (ammoos->gui.get_user_time)
    return ammoos->gui.get_user_time (ammoos);

  return 0;
}

GFile *
gimp_get_theme_dir (Gimp *ammoos)
{
  g_return_val_if_fail (GIMP_IS_GIMP (ammoos), NULL);

  if (ammoos->gui.get_theme_dir)
    return ammoos->gui.get_theme_dir (ammoos);

  return NULL;
}

GFile *
gimp_get_icon_theme_dir (Gimp *ammoos)
{
  g_return_val_if_fail (GIMP_IS_GIMP (ammoos), NULL);

  if (ammoos->gui.get_icon_theme_dir)
    return ammoos->gui.get_icon_theme_dir (ammoos);

  return NULL;
}

GimpObject *
gimp_get_window_strategy (Gimp *ammoos)
{
  g_return_val_if_fail (GIMP_IS_GIMP (ammoos), NULL);

  if (ammoos->gui.get_window_strategy)
    return ammoos->gui.get_window_strategy (ammoos);

  return NULL;
}

GimpDisplay *
gimp_get_empty_display (Gimp *ammoos)
{
  g_return_val_if_fail (GIMP_IS_GIMP (ammoos), NULL);

  if (ammoos->gui.get_empty_display)
    return ammoos->gui.get_empty_display (ammoos);

  return NULL;
}

GBytes *
gimp_get_display_window_id (Gimp        *ammoos,
                            GimpDisplay *display)
{
  g_return_val_if_fail (GIMP_IS_GIMP (ammoos), NULL);
  g_return_val_if_fail (GIMP_IS_DISPLAY (display), NULL);

  if (ammoos->gui.display_get_window_id)
    return ammoos->gui.display_get_window_id (display);

  return NULL;
}

GimpDisplay *
gimp_create_display (Gimp      *ammoos,
                     GimpImage *image,
                     GimpUnit  *unit,
                     gdouble    scale,
                     GObject   *monitor)
{
  g_return_val_if_fail (GIMP_IS_GIMP (ammoos), NULL);
  g_return_val_if_fail (image == NULL || GIMP_IS_IMAGE (image), NULL);
  g_return_val_if_fail (monitor == NULL || G_IS_OBJECT (monitor), NULL);

  if (ammoos->gui.display_create)
    return ammoos->gui.display_create (ammoos, image, unit, scale, monitor);

  return NULL;
}

void
gimp_delete_display (Gimp        *ammoos,
                     GimpDisplay *display)
{
  g_return_if_fail (GIMP_IS_GIMP (ammoos));
  g_return_if_fail (GIMP_IS_DISPLAY (display));

  if (ammoos->gui.display_delete)
    ammoos->gui.display_delete (display);
}

void
gimp_reconnect_displays (Gimp      *ammoos,
                         GimpImage *old_image,
                         GimpImage *new_image)
{
  g_return_if_fail (GIMP_IS_GIMP (ammoos));
  g_return_if_fail (GIMP_IS_IMAGE (old_image));
  g_return_if_fail (GIMP_IS_IMAGE (new_image));

  if (ammoos->gui.displays_reconnect)
    ammoos->gui.displays_reconnect (ammoos, old_image, new_image);
}

GimpProgress *
gimp_new_progress (Gimp        *ammoos,
                   GimpDisplay *display)
{
  g_return_val_if_fail (GIMP_IS_GIMP (ammoos), NULL);
  g_return_val_if_fail (display == NULL || GIMP_IS_DISPLAY (display), NULL);

  if (ammoos->gui.progress_new)
    return ammoos->gui.progress_new (ammoos, display);

  return NULL;
}

void
gimp_free_progress (Gimp         *ammoos,
                    GimpProgress *progress)
{
  g_return_if_fail (GIMP_IS_GIMP (ammoos));
  g_return_if_fail (GIMP_IS_PROGRESS (progress));

  if (ammoos->gui.progress_free)
    ammoos->gui.progress_free (ammoos, progress);
}

gboolean
gimp_pdb_dialog_new (Gimp          *ammoos,
                     GimpContext   *context,
                     GimpProgress  *progress,
                     GType          contents_type,
                     GBytes        *parent_handle,
                     const gchar   *title,
                     const gchar   *callback_name,
                     GimpObject    *object,
                     ...)
{
  gboolean retval = FALSE;

  g_return_val_if_fail (GIMP_IS_GIMP (ammoos), FALSE);
  g_return_val_if_fail (GIMP_IS_CONTEXT (context), FALSE);
  g_return_val_if_fail (progress == NULL || GIMP_IS_PROGRESS (progress), FALSE);
  g_return_val_if_fail (g_type_is_a (contents_type, GIMP_TYPE_RESOURCE) ||
                        g_type_is_a (contents_type, GIMP_TYPE_ITEM)     ||
                        g_type_is_a (contents_type, GIMP_TYPE_IMAGE), FALSE);
  g_return_val_if_fail (object == NULL ||
                        g_type_is_a (G_TYPE_FROM_INSTANCE (object), contents_type), FALSE);
  g_return_val_if_fail (title != NULL, FALSE);
  g_return_val_if_fail (callback_name != NULL, FALSE);

  if (ammoos->gui.pdb_dialog_new)
    {
      va_list args;

      va_start (args, object);

      retval = ammoos->gui.pdb_dialog_new (ammoos, context, progress,
                                         contents_type, parent_handle, title,
                                         callback_name, object, args);

      va_end (args);
    }

  return retval;
}

gboolean
gimp_pdb_dialog_set (Gimp        *ammoos,
                     GType        contents_type,
                     const gchar *callback_name,
                     GimpObject  *object,
                     ...)
{
  gboolean retval = FALSE;

  g_return_val_if_fail (GIMP_IS_GIMP (ammoos), FALSE);
  g_return_val_if_fail (g_type_is_a (contents_type, GIMP_TYPE_RESOURCE) ||
                        contents_type == GIMP_TYPE_DRAWABLE             ||
                        contents_type == GIMP_TYPE_ITEM                 ||
                        contents_type == GIMP_TYPE_IMAGE, FALSE);
  g_return_val_if_fail (callback_name != NULL, FALSE);
  g_return_val_if_fail (object == NULL || g_type_is_a (G_TYPE_FROM_INSTANCE (object), contents_type), FALSE);

  if (ammoos->gui.pdb_dialog_set)
    {
      va_list args;

      va_start (args, object);

      retval = ammoos->gui.pdb_dialog_set (ammoos, contents_type, callback_name,
                                         object, args);

      va_end (args);
    }

  return retval;
}

gboolean
gimp_pdb_dialog_close (Gimp          *ammoos,
                       GType          contents_type,
                       const gchar   *callback_name)
{
  g_return_val_if_fail (GIMP_IS_GIMP (ammoos), FALSE);
  g_return_val_if_fail (g_type_is_a (contents_type, GIMP_TYPE_RESOURCE) ||
                        contents_type == GIMP_TYPE_DRAWABLE             ||
                        contents_type == GIMP_TYPE_ITEM                 ||
                        contents_type == GIMP_TYPE_IMAGE, FALSE);
  g_return_val_if_fail (callback_name != NULL, FALSE);

  if (ammoos->gui.pdb_dialog_close)
    return ammoos->gui.pdb_dialog_close (ammoos, contents_type, callback_name);

  return FALSE;
}

gboolean
gimp_recent_list_add_file (Gimp        *ammoos,
                           GFile       *file,
                           const gchar *mime_type)
{
  g_return_val_if_fail (GIMP_IS_GIMP (ammoos), FALSE);
  g_return_val_if_fail (G_IS_FILE (file), FALSE);

  if (ammoos->gui.recent_list_add_file)
    return ammoos->gui.recent_list_add_file (ammoos, file, mime_type);

  return FALSE;
}

void
gimp_recent_list_load (Gimp *ammoos)
{
  g_return_if_fail (GIMP_IS_GIMP (ammoos));

  if (ammoos->gui.recent_list_load)
    ammoos->gui.recent_list_load (ammoos);
}

GMountOperation *
gimp_get_mount_operation (Gimp         *ammoos,
                          GimpProgress *progress)
{
  g_return_val_if_fail (GIMP_IS_GIMP (ammoos), FALSE);
  g_return_val_if_fail (progress == NULL || GIMP_IS_PROGRESS (progress), FALSE);

  if (ammoos->gui.get_mount_operation)
    return ammoos->gui.get_mount_operation (ammoos, progress);

  return g_mount_operation_new ();
}

GimpColorProfilePolicy
gimp_query_profile_policy (Gimp                      *ammoos,
                           GimpImage                 *image,
                           GimpContext               *context,
                           GimpColorProfile         **dest_profile,
                           GimpColorRenderingIntent  *intent,
                           gboolean                  *bpc,
                           gboolean                  *dont_ask)
{
  g_return_val_if_fail (GIMP_IS_GIMP (ammoos), GIMP_COLOR_PROFILE_POLICY_KEEP);
  g_return_val_if_fail (GIMP_IS_IMAGE (image), GIMP_COLOR_PROFILE_POLICY_KEEP);
  g_return_val_if_fail (GIMP_IS_CONTEXT (context), GIMP_COLOR_PROFILE_POLICY_KEEP);
  g_return_val_if_fail (dest_profile != NULL, GIMP_COLOR_PROFILE_POLICY_KEEP);

  if (ammoos->gui.query_profile_policy)
    return ammoos->gui.query_profile_policy (ammoos, image, context,
                                           dest_profile,
                                           intent, bpc,
                                           dont_ask);

  return GIMP_COLOR_PROFILE_POLICY_KEEP;
}

GimpMetadataRotationPolicy
gimp_query_rotation_policy (Gimp        *ammoos,
                            GimpImage   *image,
                            GimpContext *context,
                            gboolean    *dont_ask)
{
  g_return_val_if_fail (GIMP_IS_GIMP (ammoos), GIMP_METADATA_ROTATION_POLICY_ROTATE);
  g_return_val_if_fail (GIMP_IS_IMAGE (image), GIMP_METADATA_ROTATION_POLICY_ROTATE);
  g_return_val_if_fail (GIMP_IS_CONTEXT (context), GIMP_METADATA_ROTATION_POLICY_ROTATE);

  if (ammoos->gui.query_rotation_policy)
    return ammoos->gui.query_rotation_policy (ammoos, image, context, dont_ask);

  return GIMP_METADATA_ROTATION_POLICY_ROTATE;
}
