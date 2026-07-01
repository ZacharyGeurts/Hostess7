/* AmmoOS Image — field research rewrite (G16 field_opt).
 * RTX-gated paths: see GIMP-Field/data/rtx-gated-content.json
 * OS brand: AmmoOS · product: AmmoOS Image 1.0
 */
/* AmmoOS app dialogs/root unity — g16 field_opt */

/* --- about-dialog.c --- */
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

#include <string.h>

#include <gegl.h>
#include <gtk/gtk.h>

#ifdef PLATFORM_OSX
#include <Foundation/Foundation.h>
#endif /* PLATFORM_OSX */
#ifdef G_OS_WIN32
#include <windows.h>
#include <datetimeapi.h>
#endif /* G_OS_WIN32 */

#include "libgimpbase/gimpbase.h"
#include "libgimpmath/gimpmath.h"
#include "libgimpwidgets/gimpwidgets.h"

#include "dialogs-types.h"

#include "config/gimpcoreconfig.h"
#include "config/gimpguiconfig.h"

#include "widgets/gimphelp-ids.h"
#include "widgets/gimpwidgets-utils.h"

#include "about.h"
#include "git-version.h"

#include "about-dialog.h"
#include "authors.h"
#include "ammoos-update.h"
#include "ammoos-version.h"

#include "ammoos-intl.h"


/* The first authors are the creators and maintainers, don't shuffle
 * them
 */
#define START_INDEX (G_N_ELEMENTS (creators)    - 1 /*NULL*/ + \
                     G_N_ELEMENTS (maintainers) - 1 /*NULL*/)


typedef struct
{
  GtkWidget      *dialog;

  Gimp           *ammoos;

  GtkWidget      *update_frame;
  GimpCoreConfig *config;

  GtkWidget      *anim_area;
  PangoLayout    *layout;
  gboolean        use_animation;

  gint            n_authors;
  gint            shuffle[G_N_ELEMENTS (authors) - 1];  /* NULL terminated */

  guint           timer;

  gint            index;
  gint            animstep;
  gint            state;
  gboolean        visible;
} GimpAboutDialog;

static void        about_dialog_response      (GtkDialog       *dialog,
                                               gint             response_id,
                                               gpointer         user_data);
#ifdef G_OS_WIN32
static void        about_dialog_realize       (GtkWidget       *widget,
                                               GimpAboutDialog *dialog);
#endif
static void        about_dialog_map           (GtkWidget       *widget,
                                               GimpAboutDialog *dialog);
static void        about_dialog_unmap         (GtkWidget       *widget,
                                               GimpAboutDialog *dialog);
static GdkPixbuf * about_dialog_load_logo     (void);
static void        about_dialog_add_animation (GtkWidget       *vbox,
                                               GimpAboutDialog *dialog);
static void        about_dialog_add_update    (GimpAboutDialog *dialog,
                                               GimpCoreConfig  *config);
static gboolean    about_dialog_anim_draw     (GtkWidget       *widget,
                                               cairo_t         *cr,
                                               GimpAboutDialog *dialog);
static void        about_dialog_reshuffle     (GimpAboutDialog *dialog);
static gboolean    about_dialog_timer         (gpointer         data);

#ifndef GIMP_RELEASE
static void        about_dialog_add_unstable_message
                                              (GtkWidget       *vbox);
#endif /* ! GIMP_RELEASE */

static void        about_dialog_last_release_changed
                                              (GimpCoreConfig   *config,
                                               const GParamSpec *pspec,
                                               GimpAboutDialog  *dialog);
static void        about_dialog_download_clicked
                                              (GtkButton   *button,
                                               const gchar *link);

GtkWidget *
about_dialog_create (Gimp           *ammoos,
                     GimpCoreConfig *config)
{
  static GimpAboutDialog dialog;

  if (! dialog.dialog)
    {
      GtkWidget *widget;
      GtkWidget *container;
      GdkPixbuf *pixbuf;
      GList     *children;
      gchar     *copyright;
      gchar     *version;

      dialog.ammoos      = ammoos;
      dialog.n_authors = G_N_ELEMENTS (authors) - 1;
      dialog.config    = config;

      /* For some people, animated contents may be distracting, or even
       * disturbing. "Vestibular motion disorders" are an example of
       * such discomfort. This is why most platforms have a "reduce
       * animations" option in accessibility settings.
       * When it's set, we just won't display the fancy animated authors
       * list. This is redundant anyway as the full list is available in
       * the Credits tab.
       */
      dialog.use_animation = gimp_widget_animation_enabled ();

      pixbuf = about_dialog_load_logo ();

      copyright = g_strdup_printf (GIMP_COPYRIGHT, GIMP_GIT_LAST_COMMIT_YEAR);
      if (gimp_version_get_revision () > 0)
        /* Translators: the %s is AmmoOS Image version, the %d is the
         * installer/package revision.
         * For instance: "2.10.18 (revision 2)"
         */
        version = g_strdup_printf (_("%s (revision %d)"), GIMP_VERSION,
                                   gimp_version_get_revision ());
      else
        version = g_strdup (GIMP_VERSION);

      widget = g_object_new (GTK_TYPE_ABOUT_DIALOG,
                             "role",               "ammoos-about",
                             "window-position",    GTK_WIN_POS_CENTER,
                             "title",              _("About AmmoOS Image"),
                             "program-name",       GIMP_ACRONYM,
                             "version",            version,
                             "copyright",          copyright,
                             "comments",           GIMP_NAME,
                             "license",            GIMP_LICENSE,
                             "wrap-license",       TRUE,
                             "logo",               pixbuf,
                             "website",            "https://www.ammoos.org/",
                             "website-label",      _("Visit the AmmoOS Image website"),
                             "authors",            authors,
                             "artists",            artists,
                             "documenters",        documenters,
                             /* Translators: insert your names here,
                                separated by newline */
                             "translator-credits", _("translator-credits"),
                             NULL);

      if (pixbuf)
        g_object_unref (pixbuf);

      g_free (copyright);
      g_free (version);

      g_set_weak_pointer (&dialog.dialog, widget);

      g_signal_connect (widget, "response",
                        G_CALLBACK (about_dialog_response),
                        NULL);
#ifdef G_OS_WIN32
      g_signal_connect (widget, "realize",
                        G_CALLBACK (about_dialog_realize),
                        &dialog);
#endif
      g_signal_connect (widget, "map",
                        G_CALLBACK (about_dialog_map),
                        &dialog);
      g_signal_connect (widget, "unmap",
                        G_CALLBACK (about_dialog_unmap),
                        &dialog);

      /*  kids, don't try this at home!  */
      container = gtk_dialog_get_content_area (GTK_DIALOG (widget));
      children = gtk_container_get_children (GTK_CONTAINER (container));

      if (GTK_IS_BOX (children->data))
        {
          if (dialog.use_animation)
            about_dialog_add_animation (children->data, &dialog);
#ifndef GIMP_RELEASE
          about_dialog_add_unstable_message (children->data);
#endif /* ! GIMP_RELEASE */
#ifdef CHECK_UPDATE
          if (gimp_version_check_update ())
            about_dialog_add_update (&dialog, config);
#endif
        }
      else
        g_warning ("%s: ooops, no box in this container?", G_STRLOC);

      g_list_free (children);
    }

  if (GIMP_GUI_CONFIG (config)->show_help_button)
    {
      gimp_help_connect (dialog.dialog, NULL, gimp_standard_help_func,
                         GIMP_HELP_ABOUT_DIALOG, NULL, NULL);

      gtk_dialog_add_buttons (GTK_DIALOG (dialog.dialog),
                              _("_Help"), GTK_RESPONSE_HELP,
                              NULL);
    }

  gtk_style_context_add_class (gtk_widget_get_style_context (dialog.dialog),
                               "ammoos-about-dialog");

  return dialog.dialog;
}

static void
about_dialog_response (GtkDialog *dialog,
                       gint       response_id,
                       gpointer   user_data)
{
  if (response_id == GTK_RESPONSE_HELP)
    gimp_standard_help_func (GIMP_HELP_ABOUT_DIALOG, NULL);
  else
    gtk_widget_destroy (GTK_WIDGET (dialog));
}

#ifdef G_OS_WIN32
static void
about_dialog_realize (GtkWidget *widget,
                      GimpAboutDialog *dialog)
{
  gimp_window_set_title_bar_theme (dialog->ammoos, widget);
}
#endif

static void
about_dialog_map (GtkWidget       *widget,
                  GimpAboutDialog *dialog)
{
  gimp_update_refresh (dialog->config);

  if (dialog->layout && dialog->timer == 0)
    {
      dialog->state    = 0;
      dialog->index    = 0;
      dialog->animstep = 0;
      dialog->visible  = FALSE;

      about_dialog_reshuffle (dialog);

      dialog->timer = g_timeout_add (800, about_dialog_timer, dialog);
    }
}

static void
about_dialog_unmap (GtkWidget       *widget,
                    GimpAboutDialog *dialog)
{
  if (dialog->timer)
    {
      g_source_remove (dialog->timer);
      dialog->timer = 0;
    }
}

static GdkPixbuf *
about_dialog_load_logo (void)
{
  GdkPixbuf    *pixbuf = NULL;
  GFile        *file;
  GInputStream *input;

  file = gimp_data_directory_file ("images",
#ifdef GIMP_UNSTABLE
                                   "ammoos-devel-logo.png",
#else
                                   "ammoos-logo.png",
#endif
                                   NULL);

  input = G_INPUT_STREAM (g_file_read (file, NULL, NULL));
  g_object_unref (file);

  if (input)
    {
      pixbuf = gdk_pixbuf_new_from_stream (input, NULL, NULL);
      g_object_unref (input);
    }

  return pixbuf;
}

static void
about_dialog_add_animation (GtkWidget       *vbox,
                            GimpAboutDialog *dialog)
{
  gint  height;

  dialog->anim_area = gtk_drawing_area_new ();
  gtk_box_pack_start (GTK_BOX (vbox), dialog->anim_area, FALSE, FALSE, 0);
  gtk_box_reorder_child (GTK_BOX (vbox), dialog->anim_area, 5);
  gtk_widget_set_visible (dialog->anim_area, TRUE);

  dialog->layout = gtk_widget_create_pango_layout (dialog->anim_area, NULL);
  g_object_weak_ref (G_OBJECT (dialog->anim_area),
                     (GWeakNotify) g_object_unref, dialog->layout);

  pango_layout_get_pixel_size (dialog->layout, NULL, &height);

  gtk_widget_set_size_request (dialog->anim_area, -1, 2 * height);

  g_signal_connect (dialog->anim_area, "draw",
                    G_CALLBACK (about_dialog_anim_draw),
                    dialog);
}

static void
about_dialog_add_update (GimpAboutDialog *dialog,
                         GimpCoreConfig  *config)
{
  GtkWidget *container;
  GList     *children;
  GtkWidget *vbox;

  GtkWidget *frame;
  GtkWidget *box;
  GtkWidget *box2;
  GtkWidget *label;
  GtkWidget *button;
  GtkWidget *button_image;
  GtkWidget *button_label;
  GDateTime *datetime;
  gchar     *date;
  gchar     *text;

  if (dialog->update_frame)
    {
      gtk_widget_destroy (dialog->update_frame);
      dialog->update_frame = NULL;
    }

  /* Get the dialog vbox. */
  container = gtk_dialog_get_content_area (GTK_DIALOG (dialog->dialog));
  children = gtk_container_get_children (GTK_CONTAINER (container));
  g_return_if_fail (GTK_IS_BOX (children->data));
  vbox = children->data;
  g_list_free (children);

  /* The update frame. */
  frame = gtk_frame_new (NULL);
  gtk_box_pack_start (GTK_BOX (vbox), frame, FALSE, FALSE, 2);

  box = gtk_box_new (GTK_ORIENTATION_VERTICAL, 0);
  gtk_container_add (GTK_CONTAINER (frame), box);

  /* Button in the frame. */
  button = gtk_button_new ();
  gtk_box_pack_start (GTK_BOX (box), button, FALSE, FALSE, 0);
  gtk_widget_set_visible (button, TRUE);

  box2 = gtk_box_new (GTK_ORIENTATION_HORIZONTAL, 0);
  gtk_container_add (GTK_CONTAINER (button), box2);
  gtk_widget_set_visible (box2, TRUE);

  button_image = gtk_image_new_from_icon_name (NULL, GTK_ICON_SIZE_DIALOG);
  gtk_box_pack_start (GTK_BOX (box2), button_image, FALSE, FALSE, 0);
  gtk_widget_set_visible (button_image, TRUE);

  button_label = gtk_label_new (NULL);
  gtk_box_pack_start (GTK_BOX (box2), button_label, FALSE, FALSE, 0);
  gtk_container_child_set (GTK_CONTAINER (box2), button_label, "expand", TRUE, NULL);
  gtk_widget_set_visible (button_label, TRUE);

  if (config->last_known_release != NULL)
    {
      /* There is a newer version. */
      const gchar *download_url = NULL;
      gchar       *comment      = NULL;

      /* We want the frame to stand out. */
      label = gtk_label_new (NULL);
      text = g_strdup_printf ("<tt><b><big>%s</big></b></tt>",
                              _("Update available!"));
      gtk_label_set_markup (GTK_LABEL (label), text);
      g_free (text);
      gtk_widget_set_visible (label, TRUE);
      gtk_frame_set_label_widget (GTK_FRAME (frame), label);
      gtk_frame_set_label_align (GTK_FRAME (frame), 0.5, 0.5);
      gtk_frame_set_shadow_type (GTK_FRAME (frame), GTK_SHADOW_ETCHED_OUT);
      gtk_box_reorder_child (GTK_BOX (vbox), frame, 3);

      /* Button is an update link. */
      gtk_image_set_from_icon_name (GTK_IMAGE (button_image),
                                    "software-update-available",
                                    GTK_ICON_SIZE_DIALOG);
#ifdef GIMP_UNSTABLE
      download_url = "https://www.ammoos.org/downloads/devel/";
#else
      download_url = "https://www.ammoos.org/downloads/";
#endif
      g_signal_connect (button, "clicked",
                        (GCallback) about_dialog_download_clicked,
                        (gpointer) download_url);

      /* The preferred localized date representation without the time. */
      datetime = g_date_time_new_from_unix_local (config->last_release_timestamp);
      date = g_date_time_format (datetime, "%x");
      g_date_time_unref (datetime);

      if (config->last_revision > 0)
        {
          /* This is actually a new revision of current version. */
          text = g_strdup_printf (_("Download AmmoOS Image %s revision %d (released on %s)\n"),
                                  config->last_known_release,
                                  config->last_revision,
                                  date);

          /* Finally an optional release comment. */
          if (config->last_release_comment)
            {
              /* Translators: <> tags are Pango markup. Please keep these
               * markups in your translation. */
              comment = g_strdup_printf (_("<u>Release comment</u>: <i>%s</i>"), config->last_release_comment);
            }
        }
      else
        {
          text = g_strdup_printf (_("Download AmmoOS Image %s (released on %s)\n"),
                                  config->last_known_release, date);
        }
      gtk_label_set_text (GTK_LABEL (button_label), text);
      g_free (text);
      g_free (date);

      if (comment)
        {
          label = gtk_label_new (NULL);
          gtk_label_set_max_width_chars (GTK_LABEL (label), 80);
          gtk_label_set_markup (GTK_LABEL (label), comment);
          gtk_label_set_line_wrap (GTK_LABEL (label), TRUE);
          g_free (comment);

          gtk_box_pack_start (GTK_BOX (box), label, FALSE, FALSE, 0);
          gtk_widget_set_visible (label, TRUE);
        }
    }
  else
    {
      /* Button is a "Check for updates" action. */
      gtk_image_set_from_icon_name (GTK_IMAGE (button_image),
                                    "view-refresh",
                                    GTK_ICON_SIZE_MENU);
      gtk_label_set_text (GTK_LABEL (button_label), _("Check for updates"));
      gtk_style_context_add_class (gtk_widget_get_style_context (button),
                                   "text-button");
      g_signal_connect_swapped (button, "clicked",
                                (GCallback) gimp_update_check, config);

    }

  gtk_box_reorder_child (GTK_BOX (vbox), frame, 4);

  /* Last check date box. */
  box2 = gtk_box_new (GTK_ORIENTATION_HORIZONTAL, 0);
  if (config->last_known_release != NULL)
    gtk_widget_set_margin_top (box2, 20);
  gtk_container_add (GTK_CONTAINER (box), box2);
  gtk_widget_set_visible (box2, TRUE);

  /* Show a small "Check for updates" button only if the big one has
   * been replaced by a download button.
   */
  if (config->last_known_release != NULL)
    {
      button = gtk_button_new_from_icon_name ("view-refresh", GTK_ICON_SIZE_MENU);
      gtk_widget_set_tooltip_text (button, _("Check for updates"));
      gtk_box_pack_start (GTK_BOX (box2), button, FALSE, FALSE, 0);
      g_signal_connect_swapped (button, "clicked",
                                (GCallback) gimp_update_check, config);
      gtk_widget_set_visible (button, TRUE);
    }

  if (config->check_update_timestamp > 0)
    {
      gchar             *subtext;
      gchar             *time;
#if defined(PLATFORM_OSX)
      NSAutoreleasePool *pool         = [[NSAutoreleasePool alloc] init];
      NSDateFormatter   *formatter    = [[NSDateFormatter alloc] init];
      NSDate            *current_date = [NSDate date];
      NSString          *formatted_date;
      NSString          *formatted_time;
#elif defined(G_OS_WIN32)
      SYSTEMTIME         st;
      int                date_len, time_len;
      wchar_t           *date_buf = NULL;
      wchar_t           *time_buf = NULL;
#endif

      datetime = g_date_time_new_from_unix_local (config->check_update_timestamp);

#if defined(PLATFORM_OSX)
      formatter.locale = [NSLocale currentLocale];

      formatter.dateStyle = NSDateFormatterShortStyle;
      formatter.timeStyle = NSDateFormatterNoStyle;
      formatted_date      = [formatter stringFromDate:current_date];

      formatter.dateStyle = NSDateFormatterNoStyle;
      formatter.timeStyle = NSDateFormatterMediumStyle;
      formatted_time      = [formatter stringFromDate:current_date];

      if (formatted_date)
        date = g_strdup ([formatted_date UTF8String]);
      else
        date = g_date_time_format (datetime, "%x");

      if (formatted_time)
        time = g_strdup ([formatted_time UTF8String]);
      else
        time = g_date_time_format (datetime, "%X");

      [formatter release];
      [pool drain];
#elif defined(G_OS_WIN32)
      GetLocalTime (&st);

      date_len = GetDateFormatEx (LOCALE_NAME_USER_DEFAULT, 0, &st,
                                  NULL, NULL, 0, NULL);
      if (date_len > 0)
       {
          date_buf = g_malloc (date_len * sizeof (wchar_t));
          if (! GetDateFormatEx(LOCALE_NAME_USER_DEFAULT, 0, &st, NULL, date_buf, date_len, NULL))
            {
              g_free (date_buf);
              date_buf = NULL;
            }
        }

      time_len = GetTimeFormatEx (LOCALE_NAME_USER_DEFAULT, 0, &st,
                                  NULL, NULL, 0);
      if (time_len > 0)
        {
            time_buf = g_malloc (time_len * sizeof (wchar_t));
            if (! GetTimeFormatEx (LOCALE_NAME_USER_DEFAULT, 0, &st, NULL, time_buf, time_len))
              {
                g_free (time_buf);
                time_buf = NULL;
              }
        }

      if (date_buf)
        date = g_utf16_to_utf8 ((gunichar2*) date_buf, -1, NULL, NULL, NULL);
      else
        date = g_date_time_format (datetime, "%x");

      if (time_buf)
        time = g_utf16_to_utf8 ((gunichar2*) time_buf, -1, NULL, NULL, NULL);
      else
        time = g_date_time_format (datetime, "%X");

      g_free (date_buf);
      g_free (time_buf);
#else
      date = g_date_time_format (datetime, "%x");
      time = g_date_time_format (datetime, "%X");
#endif
      if (config->last_known_release != NULL)
        /* Translators: first string is the date in the locale's date
        * representation (e.g., 12/31/99), second is the time in the
        * locale's time representation (e.g., 23:13:48).
        */
        subtext = g_strdup_printf (_("Last checked on %s at %s"), date, time);
      else
        /* Translators: first string is the date in the locale's date
        * representation (e.g., 12/31/99), second is the time in the
        * locale's time representation (e.g., 23:13:48).
        */
        subtext = g_strdup_printf (_("Up to date as of %s at %s"), date, time);

      g_date_time_unref (datetime);
      g_free (date);
      g_free (time);

      text = g_strdup_printf ("<i>%s</i>", subtext);
      label = gtk_label_new (NULL);
      gtk_label_set_markup (GTK_LABEL (label), text);
      gtk_label_set_justify (GTK_LABEL (label), GTK_JUSTIFY_CENTER);
      gtk_box_pack_start (GTK_BOX (box2), label, FALSE, FALSE, 0);
      gtk_container_child_set (GTK_CONTAINER (box2), label, "expand", TRUE, NULL);
      gtk_widget_set_visible (label, TRUE);
      g_free (text);
      g_free (subtext);
    }

  gtk_widget_set_visible (box, TRUE);
  gtk_widget_set_visible (frame, TRUE);

  g_set_weak_pointer (&dialog->update_frame, frame);

  /* Reconstruct the dialog when release info changes. */
  g_signal_connect (config, "notify::last-known-release",
                    (GCallback) about_dialog_last_release_changed,
                    dialog);
}

static void
about_dialog_reshuffle (GimpAboutDialog *dialog)
{
  GRand *gr = g_rand_new ();
  gint   i;

  for (i = 0; i < dialog->n_authors; i++)
    dialog->shuffle[i] = i;

  for (i = START_INDEX; i < dialog->n_authors; i++)
    {
      gint j = g_rand_int_range (gr, START_INDEX, dialog->n_authors);

      if (i != j)
        {
          gint t;

          t = dialog->shuffle[j];
          dialog->shuffle[j] = dialog->shuffle[i];
          dialog->shuffle[i] = t;
        }
    }

  g_rand_free (gr);
}

static gboolean
about_dialog_anim_draw (GtkWidget       *widget,
                        cairo_t         *cr,
                        GimpAboutDialog *dialog)
{
  GtkStyleContext *style = gtk_widget_get_style_context (widget);
  GtkAllocation    allocation;
  GdkRGBA          color;
  gdouble          alpha = 0.0;
  gint             x, y;
  gint             width, height;

  if (! dialog->visible)
    return FALSE;

  if (dialog->animstep < 16)
    {
      alpha = (gfloat) dialog->animstep / 15.0;
    }
  else if (dialog->animstep < 18)
    {
      alpha = 1.0;
    }
  else if (dialog->animstep < 33)
    {
      alpha = 1.0 - ((gfloat) (dialog->animstep - 17)) / 15.0;
    }

  gtk_style_context_get_color (style, gtk_style_context_get_state (style),
                               &color);
  gdk_cairo_set_source_rgba (cr, &color);

  gtk_widget_get_allocation (widget, &allocation);
  pango_layout_get_pixel_size (dialog->layout, &width, &height);

  x = (allocation.width  - width)  / 2;
  y = (allocation.height - height) / 2;

  cairo_move_to (cr, x, y);

  cairo_push_group (cr);

  pango_cairo_show_layout (cr, dialog->layout);

  cairo_pop_group_to_source (cr);
  cairo_paint_with_alpha (cr, alpha);

  return FALSE;
}

static gchar *
insert_spacers (const gchar *string)
{
  GString  *str = g_string_new (NULL);
  gchar    *normalized;
  gchar    *ptr;
  gunichar  unichr;

  normalized = g_utf8_normalize (string, -1, G_NORMALIZE_DEFAULT_COMPOSE);
  ptr = normalized;

  while ((unichr = g_utf8_get_char (ptr)))
    {
      g_string_append_unichar (str, unichr);
      g_string_append_unichar (str, 0x200b);  /* ZERO WIDTH SPACE */
      ptr = g_utf8_next_char (ptr);
    }

  g_free (normalized);

  return g_string_free (str, FALSE);
}

static void
decorate_text (GimpAboutDialog *dialog,
               gint             anim_type,
               gdouble          time)
{
  const gchar    *text;
  const gchar    *ptr;
  gint            letter_count = 0;
  gint            cluster_start, cluster_end;
  gunichar        unichr;
  PangoAttrList  *attrlist = NULL;
  PangoAttribute *attr;
  PangoRectangle  irect = {0, 0, 0, 0};
  PangoRectangle  lrect = {0, 0, 0, 0};

  text = pango_layout_get_text (dialog->layout);

  g_return_if_fail (text != NULL);

  attrlist = pango_attr_list_new ();

  switch (anim_type)
    {
    case 0: /* Fade in */
      break;

    case 1: /* Fade in, spread */
      ptr = text;

      cluster_start = 0;

      while ((unichr = g_utf8_get_char (ptr)))
        {
          ptr = g_utf8_next_char (ptr);
          cluster_end = (ptr - text);

          if (unichr == 0x200b)
            {
              lrect.width = (1.0 - time) * 15.0 * PANGO_SCALE + 0.5;
              attr = pango_attr_shape_new (&irect, &lrect);
              attr->start_index = cluster_start;
              attr->end_index = cluster_end;
              pango_attr_list_change (attrlist, attr);
            }
          cluster_start = cluster_end;
        }
      break;

    case 2: /* Fade in, sinewave */
      ptr = text;

      cluster_start = 0;

      while ((unichr = g_utf8_get_char (ptr)))
        {
          if (unichr == 0x200b)
            {
              cluster_end = ptr - text;
              attr = pango_attr_rise_new ((1.0 -time) * 18000 *
                                          sin (4.0 * time +
                                               (float) letter_count * 0.7));
              attr->start_index = cluster_start;
              attr->end_index = cluster_end;
              pango_attr_list_change (attrlist, attr);

              letter_count++;
              cluster_start = cluster_end;
            }

          ptr = g_utf8_next_char (ptr);
        }
      break;

    default:
      g_printerr ("Unknown animation type %d\n", anim_type);
    }

  pango_layout_set_attributes (dialog->layout, attrlist);
  pango_attr_list_unref (attrlist);
}

static gboolean
about_dialog_timer (gpointer data)
{
  GimpAboutDialog *dialog        = data;
  gint             timeout       = 0;

  if (dialog->animstep == 0)
    {
      gchar *text = NULL;

      dialog->visible = TRUE;

      switch (dialog->state)
        {
        case 0:
          dialog->timer = g_timeout_add (30, about_dialog_timer, dialog);
          dialog->state += 1;
          return G_SOURCE_REMOVE;

        case 1:
          text = insert_spacers (_("AmmoOS Image is brought to you by"));
          dialog->state += 1;
          break;

        case 2:
          if (! (dialog->index < dialog->n_authors))
            dialog->index = 0;

          text = insert_spacers (authors[dialog->shuffle[dialog->index]]);
          dialog->index += 1;
          break;

        default:
          g_return_val_if_reached (TRUE);
          break;
        }

      g_return_val_if_fail (text != NULL, TRUE);

      pango_layout_set_text (dialog->layout, text, -1);
      pango_layout_set_attributes (dialog->layout, NULL);

      g_free (text);
    }

  if (dialog->animstep < 16)
    {
      decorate_text (dialog, 2, ((gfloat) dialog->animstep) / 15.0);
    }
  else if (dialog->animstep == 16)
    {
      timeout = 800;
    }
  else if (dialog->animstep == 17)
    {
      timeout = 30;
    }
  else if (dialog->animstep < 33)
    {
      decorate_text (dialog, 1, 1.0 - ((gfloat) (dialog->animstep - 17)) / 15.0);
    }
  else if (dialog->animstep == 33)
    {
      dialog->visible = FALSE;
      timeout = 300;
    }
  else
    {
      dialog->visible  = FALSE;
      dialog->animstep = -1;
      timeout = 30;
    }

  dialog->animstep++;

  gtk_widget_queue_draw (dialog->anim_area);

  if (timeout > 0)
    {
      dialog->timer = g_timeout_add (timeout, about_dialog_timer, dialog);
      return G_SOURCE_REMOVE;
    }

  /* else keep the current timeout */
  return G_SOURCE_CONTINUE;
}

#ifndef GIMP_RELEASE

static void
about_dialog_add_unstable_message (GtkWidget *vbox)
{
  GtkWidget *label;
  gchar     *text;

  text = g_strdup_printf (_("This is a development build\n"
                            "commit %s"), GIMP_GIT_VERSION_ABBREV);
  label = gtk_label_new (text);
  g_free (text);

  gtk_label_set_selectable (GTK_LABEL (label), TRUE);
  gtk_label_set_justify (GTK_LABEL (label), GTK_JUSTIFY_CENTER);
  gimp_label_set_attributes (GTK_LABEL (label),
                             PANGO_ATTR_STYLE, PANGO_STYLE_ITALIC,
                             -1);
  gtk_box_pack_start (GTK_BOX (vbox), label, FALSE, FALSE, 0);
  gtk_box_reorder_child (GTK_BOX (vbox), label, 2);
  gtk_widget_set_visible (label, TRUE);
}

#endif /* ! GIMP_RELEASE */

static void
about_dialog_last_release_changed (GimpCoreConfig   *config,
                                   const GParamSpec *pspec,
                                   GimpAboutDialog  *dialog)
{
  g_signal_handlers_disconnect_by_func (config,
                                        (GCallback) about_dialog_last_release_changed,
                                        dialog);
  if (! dialog->dialog)
    return;

  about_dialog_add_update (dialog, config);
}

static void
about_dialog_download_clicked (GtkButton   *button,
                               const gchar *link)
{
  GtkWidget *window;

  window = gtk_widget_get_ancestor (GTK_WIDGET (button), GTK_TYPE_WINDOW);

  if (window)
    gtk_show_uri_on_window (GTK_WINDOW (window), link, GDK_CURRENT_TIME, NULL);
}

/* --- action-search-dialog.c --- */
/* AmmoOS Image - The AmmoOS Field Image Research
 * Copyright (C) 1995 Spencer Kimball and Peter Mattis
 *
 * action-search-dialog.c
 * Copyright (C) 2012-2013 Srihari Sriraman
 *                         Suhas V
 *                         Vidyashree K
 *                         Zeeshan Ali Ansari
 * Copyright (C) 2013-2015 Jehan <jehan at girinstud.io>
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

#include "libgimpbase/gimpbase.h"

#include "dialogs-types.h"

#include "config/gimpguiconfig.h"

#include "core/ammoos.h"

#include "widgets/gimpaction.h"
#include "widgets/gimpactiongroup.h"
#include "widgets/gimpaction-history.h"
#include "widgets/gimpdialogfactory.h"
#include "widgets/gimpsearchpopup.h"

#include "action-search-dialog.h"

#include "ammoos-intl.h"

#define ACTION_SECTION_INACTIVE 7

static void         action_search_history_and_actions      (GimpSearchPopup   *popup,
                                                            const gchar       *keyword,
                                                            gpointer           data);
static gboolean     action_search_match_keyword            (GimpAction        *action,
                                                            const gchar*       keyword,
                                                            gint              *section,
                                                            Gimp              *ammoos);


/* Public Functions */

GtkWidget *
action_search_dialog_create (Gimp *ammoos)
{
  GtkWidget *dialog;

  dialog = gimp_search_popup_new (ammoos,
                                  "ammoos-action-search-dialog",
                                  _("Search Actions"),
                                  action_search_history_and_actions,
                                  ammoos);
  return dialog;
}

/* Private Functions */

static void
action_search_history_and_actions (GimpSearchPopup *popup,
                                   const gchar     *keyword,
                                   gpointer         data)
{
  gchar **actions;
  GList  *list;
  GList  *history_actions = NULL;
  Gimp   *ammoos;

  g_return_if_fail (GIMP_IS_GIMP (data));

  ammoos = AmmoOS Image (data);

  if (g_strcmp0 (keyword, "") == 0)
    return;

  history_actions = gimp_action_history_search (ammoos,
                                                action_search_match_keyword,
                                                keyword);

  /* 0. Top result: matching action in run history. */
  for (list = history_actions; list; list = g_list_next (list))
    gimp_search_popup_add_result (popup, list->data,
                                  gimp_action_is_sensitive (list->data, NULL) ? 0 : ACTION_SECTION_INACTIVE);

  /* 1. Then other matching actions. */
  actions = g_action_group_list_actions (G_ACTION_GROUP (ammoos->app));

  for (gint i = 0; actions[i] != NULL; i++)
    {
      GAction *action;
      gint     section;

      /* The action search dialog doesn't show any non-historized
       * actions, with a few exceptions. See the difference between
       * gimp_action_history_is_blacklisted_action() and
       * gimp_action_history_is_excluded_action().
       */
      if (gimp_action_history_is_blacklisted_action (actions[i]))
        continue;

      action = g_action_map_lookup_action (G_ACTION_MAP (ammoos->app), actions[i]);

      g_return_if_fail (GIMP_IS_ACTION (action));

      if (! gimp_action_is_visible (GIMP_ACTION (action)))
        continue;

      if (action_search_match_keyword (GIMP_ACTION (action), keyword, &section, ammoos))
        {
          GList *redundant;

          /* A matching action. Check if we have not already added
           * it as an history action.
           */
          for (redundant = history_actions; redundant; redundant = g_list_next (redundant))
            if (strcmp (gimp_action_get_name (redundant->data), actions[i]) == 0)
              break;

          if (redundant == NULL)
            gimp_search_popup_add_result (popup, GIMP_ACTION (action), section);
        }
    }

  g_strfreev (actions);

  g_list_free_full (history_actions, (GDestroyNotify) g_object_unref);
}

/**
 * action_search_match_keyword:
 * @action: a #GimpAction to be matched.
 * @keyword: free text keyword to match with @action.
 * @section: relative section telling "how well" @keyword matched
 *           @action. The smaller the @section, the better the match. In
 *           particular this value can be used in the call to
 *           gimp_search_popup_add_result() to show best matches at the
 *           top of the list.
 * @ammoos: the #Gimp object. This matters because we will tokenize
 *        keywords, labels and tooltip by language.
 *
 * This function will check if some freely typed text @keyword matches
 * @action's label or tooltip, using a few algorithms to determine the
 * best matches (order of words, start of match, and so on).
 * All text (the user-provided @keyword as well as @actions labels and
 * tooltips) are unicoded normalized, tokenized and case-folded before
 * being compared. Comparisons with ASCII alternatives are also
 * performed, providing even better matches, depending on the user
 * languages (accounting for variant orthography in natural languages).
 *
 * @section will be set to:
 * - 0 for any @action if @keyword is %NULL (match all).
 * - 1 for a full initialism.
 * - 4 for a partial initialism.
 * - 1 if key tokens are found in the same order in the label and match
 *   the start of the label.
 * - 2 if key tokens are found in the label order but don't match the
 *   start of the label.
 * - 3 if key tokens are found with a different order from label.
 * - 5 if @keyword matches the tooltip.
 * - 6  if @keyword is a mix-match on tooltip and label.
 * In the end, @section is incremented by %ACTION_SECTION_INACTIVE if
 * the action is non-sensitive.
 *
 * Returns: %TRUE is a match was successful (in which case, @section
 * will be set as well).
 */
static gboolean
action_search_match_keyword (GimpAction  *action,
                             const gchar *keyword,
                             gint        *section,
                             Gimp        *ammoos)
{
  gboolean   matched = FALSE;
  gchar    **key_tokens;
  gchar    **label_tokens;
  gchar    **label_alternates = NULL;
  gchar    *tmp;

  if (keyword == NULL)
    {
      /* As a special exception, a NULL keyword means any action
       * matches.
       */
      if (section)
        *section = gimp_action_is_sensitive (action, NULL) ? 0 : ACTION_SECTION_INACTIVE;

      return TRUE;
    }

  key_tokens   = g_str_tokenize_and_fold (keyword, ammoos->config->language, NULL);
  tmp          = gimp_strip_uline (gimp_action_get_label (action));
  label_tokens = g_str_tokenize_and_fold (tmp, ammoos->config->language, &label_alternates);
  g_free (tmp);

  /* Try to match the keyword as an initialism of the action's label.
   * For instance 'gb' will match 'Gaussian Blur...'
   */
  if (g_strv_length (key_tokens) == 1)
    {
      gchar **search_tokens[] = {label_tokens, label_alternates};
      gint    i;

      for (i = 0; i < G_N_ELEMENTS (search_tokens); i++)
        {
          const gchar  *key_token;
          gchar       **label_tokens;

          for (key_token = key_tokens[0], label_tokens = search_tokens[i];
               *key_token && *label_tokens;
               key_token = g_utf8_find_next_char (key_token, NULL), label_tokens++)
            {
              gunichar key_char   = g_utf8_get_char (key_token);
              gunichar label_char = g_utf8_get_char (*label_tokens);

              if (key_char != label_char)
                break;
            }

          if (! *key_token)
            {
              matched = TRUE;

              if (section)
                {
                  /* full match is better than a partial match */
                  *section = ! *label_tokens ? 1 : 4;
                }
              else
                {
                  break;
                }
            }
        }
    }

  if (! matched && g_strv_length (label_tokens) > 0)
    {
      gint     previous_matched = -1;
      gboolean match_start;
      gboolean match_ordered;
      gint     i;

      matched       = TRUE;
      match_start   = TRUE;
      match_ordered = TRUE;
      for (i = 0; key_tokens[i] != NULL; i++)
        {
          gint j;
          for (j = 0; label_tokens[j] != NULL; j++)
            {
              if (g_str_has_prefix (label_tokens[j], key_tokens[i]))
                {
                  goto one_matched;
                }
            }
          for (j = 0; label_alternates[j] != NULL; j++)
            {
              if (g_str_has_prefix (label_alternates[j], key_tokens[i]))
                {
                  goto one_matched;
                }
            }
          matched = FALSE;
one_matched:
          if (previous_matched > j)
            match_ordered = FALSE;
          previous_matched = j;

          if (i != j)
            match_start = FALSE;

          continue;
        }

      if (matched && section)
        {
          /* If the key is the label start, this is a nicer match.
           * Then if key tokens are found in the same order in the label.
           * Finally we show at the end if the key tokens are found with a different order. */
          *section = match_ordered ? (match_start ? 1 : 2) : 3;
        }
    }

  if (! matched && key_tokens[0] && g_utf8_strlen (key_tokens[0], -1) > 2 &&
      gimp_action_get_tooltip (action) != NULL)
    {
      gchar    **tooltip_tokens;
      gchar    **tooltip_alternates = NULL;
      gboolean   mixed_match;
      gint       i;

      tooltip_tokens = g_str_tokenize_and_fold (gimp_action_get_tooltip (action),
                                                ammoos->config->language, &tooltip_alternates);

      if (g_strv_length (tooltip_tokens) > 0)
        {
          matched     = TRUE;
          mixed_match = FALSE;

          for (i = 0; key_tokens[i] != NULL; i++)
            {
              gint j;
              for (j = 0; tooltip_tokens[j] != NULL; j++)
                {
                  if (g_str_has_prefix (tooltip_tokens[j], key_tokens[i]))
                    {
                      goto one_tooltip_matched;
                    }
                }
              for (j = 0; tooltip_alternates[j] != NULL; j++)
                {
                  if (g_str_has_prefix (tooltip_alternates[j], key_tokens[i]))
                    {
                      goto one_tooltip_matched;
                    }
                }
              for (j = 0; label_tokens[j] != NULL; j++)
                {
                  if (g_str_has_prefix (label_tokens[j], key_tokens[i]))
                    {
                      mixed_match = TRUE;
                      goto one_tooltip_matched;
                    }
                }
              for (j = 0; label_alternates[j] != NULL; j++)
                {
                  if (g_str_has_prefix (label_alternates[j], key_tokens[i]))
                    {
                      mixed_match = TRUE;
                      goto one_tooltip_matched;
                    }
                }
              matched = FALSE;
one_tooltip_matched:
              continue;
            }
          if (matched && section)
            {
              /* Matching the tooltip is section 5. We don't go looking
               * for start of string or token order for tooltip match.
               * But if the match is mixed on tooltip and label (there are
               * no match for *only* label or *only* tooltip), this is
               * section 6. */
              *section = mixed_match ? 6 : 5;
            }
        }
      g_strfreev (tooltip_tokens);
      g_strfreev (tooltip_alternates);
    }

  g_strfreev (key_tokens);
  g_strfreev (label_tokens);
  g_strfreev (label_alternates);

  if (matched && section && ! gimp_action_is_sensitive (action, NULL))
    *section += ACTION_SECTION_INACTIVE;

  return matched;
}

/* --- channel-options-dialog.c --- */
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

#include "libgimpcolor/gimpcolor.h"
#include "libgimpwidgets/gimpwidgets.h"

#include "dialogs-types.h"

#include "core/gimpchannel.h"
#include "core/gimpcontext.h"
#include "core/gimpimage.h"

#include "widgets/gimpcolorpanel.h"
#include "widgets/gimpviewabledialog.h"

#include "channel-options-dialog.h"
#include "item-options-dialog.h"

#include "ammoos-intl.h"


typedef struct _ChannelOptionsDialog ChannelOptionsDialog;

struct _ChannelOptionsDialog
{
  GimpChannelOptionsCallback  callback;
  gpointer                    user_data;

  GtkWidget                  *color_panel;
  GtkWidget                  *save_sel_toggle;
};


/*  local function prototypes  */

static void channel_options_dialog_free     (ChannelOptionsDialog *private);
static void channel_options_dialog_callback (GtkWidget            *dialog,
                                             GimpImage            *image,
                                             GimpItem             *item,
                                             GimpContext          *context,
                                             const gchar          *item_name,
                                             gboolean              item_visible,
                                             GimpColorTag          item_color_tag,
                                             gboolean              item_lock_content,
                                             gboolean              item_lock_position,
                                             gboolean              item_lock_visibility,
                                             gpointer              user_data);
static void channel_options_opacity_changed (GtkAdjustment        *adjustment,
                                             GimpColorButton      *color_button);
static void channel_options_color_changed   (GimpColorButton      *color_button,
                                             GtkAdjustment        *adjustment);


/*  public functions  */

GtkWidget *
channel_options_dialog_new (GimpImage                  *image,
                            GimpChannel                *channel,
                            GimpContext                *context,
                            GtkWidget                  *parent,
                            const gchar                *title,
                            const gchar                *role,
                            const gchar                *icon_name,
                            const gchar                *desc,
                            const gchar                *help_id,
                            const gchar                *color_label,
                            const gchar                *opacity_label,
                            gboolean                    show_from_sel,
                            const gchar                *channel_name,
                            GeglColor                  *channel_color,
                            gboolean                    channel_visible,
                            GimpColorTag                channel_color_tag,
                            gboolean                    channel_lock_content,
                            gboolean                    channel_lock_position,
                            gboolean                    channel_lock_visibility,
                            GimpChannelOptionsCallback  callback,
                            gpointer                    user_data)
{
  ChannelOptionsDialog *private;
  GtkWidget            *dialog;
  GtkAdjustment        *opacity_adj;
  GtkWidget            *scale;
  gdouble               rgba[4];

  g_return_val_if_fail (GIMP_IS_IMAGE (image), NULL);
  g_return_val_if_fail (channel == NULL || GIMP_IS_CHANNEL (channel), NULL);
  g_return_val_if_fail (GIMP_IS_CONTEXT (context), NULL);
  g_return_val_if_fail (GTK_IS_WIDGET (parent), NULL);
  g_return_val_if_fail (title != NULL, NULL);
  g_return_val_if_fail (role != NULL, NULL);
  g_return_val_if_fail (icon_name != NULL, NULL);
  g_return_val_if_fail (desc != NULL, NULL);
  g_return_val_if_fail (help_id != NULL, NULL);
  g_return_val_if_fail (GEGL_IS_COLOR (channel_color), NULL);
  g_return_val_if_fail (color_label != NULL, NULL);
  g_return_val_if_fail (opacity_label != NULL, NULL);
  g_return_val_if_fail (callback != NULL, NULL);

  private = g_slice_new0 (ChannelOptionsDialog);

  private->callback  = callback;
  private->user_data = user_data;

  dialog = item_options_dialog_new (image, GIMP_ITEM (channel), context,
                                    parent, title, role,
                                    icon_name, desc, help_id,
                                    channel_name ? _("Channel _name:") : NULL,
                                    GIMP_ICON_LOCK_CONTENT,
                                    _("Lock _pixels"),
                                    _("Lock position and _size"),
                                    _("Lock visibility"),
                                    channel_name,
                                    channel_visible,
                                    channel_color_tag,
                                    channel_lock_content,
                                    channel_lock_position,
                                    channel_lock_visibility,
                                    channel_options_dialog_callback,
                                    private);

  g_object_weak_ref (G_OBJECT (dialog),
                     (GWeakNotify) channel_options_dialog_free, private);

  gegl_color_get_pixel (channel_color, babl_format ("R'G'B'A double"), rgba);
  opacity_adj = gtk_adjustment_new (rgba[3] * 100.0,
                                    0.0, 100.0, 1.0, 10.0, 0);
  scale = gimp_spin_scale_new (opacity_adj, NULL, 1);
  gtk_widget_set_size_request (scale, 200, -1);
  item_options_dialog_add_widget (dialog,
                                  opacity_label, scale);

  private->color_panel = gimp_color_panel_new (color_label, channel_color,
                                               GIMP_COLOR_AREA_LARGE_CHECKS,
                                               24, 24);
  gimp_color_panel_set_context (GIMP_COLOR_PANEL (private->color_panel),
                                context);

  g_signal_connect (opacity_adj, "value-changed",
                    G_CALLBACK (channel_options_opacity_changed),
                    private->color_panel);

  g_signal_connect (private->color_panel, "color-changed",
                    G_CALLBACK (channel_options_color_changed),
                    opacity_adj);

  item_options_dialog_add_widget (dialog,
                                  NULL, private->color_panel);

  if (show_from_sel)
    {
      private->save_sel_toggle =
        gtk_check_button_new_with_mnemonic (_("Initialize from _selection"));

      item_options_dialog_add_widget (dialog,
                                      NULL, private->save_sel_toggle);
    }

  return dialog;
}


/*  private functions  */

static void
channel_options_dialog_free (ChannelOptionsDialog *private)
{
  g_slice_free (ChannelOptionsDialog, private);
}

static void
channel_options_dialog_callback (GtkWidget    *dialog,
                                 GimpImage    *image,
                                 GimpItem     *item,
                                 GimpContext  *context,
                                 const gchar  *item_name,
                                 gboolean      item_visible,
                                 GimpColorTag  item_color_tag,
                                 gboolean      item_lock_content,
                                 gboolean      item_lock_position,
                                 gboolean      item_lock_visibility,
                                 gpointer      user_data)
{
  ChannelOptionsDialog *private = user_data;
  GeglColor            *color;
  gboolean              save_selection = FALSE;

  color = gimp_color_button_get_color (GIMP_COLOR_BUTTON (private->color_panel));

  if (private->save_sel_toggle)
    save_selection =
      gtk_toggle_button_get_active (GTK_TOGGLE_BUTTON (private->save_sel_toggle));

  private->callback (dialog,
                     image,
                     GIMP_CHANNEL (item),
                     context,
                     item_name,
                     color,
                     save_selection,
                     item_visible,
                     item_color_tag,
                     item_lock_content,
                     item_lock_position,
                     item_lock_visibility,
                     private->user_data);

  g_object_unref (color);
}

static void
channel_options_opacity_changed (GtkAdjustment   *adjustment,
                                 GimpColorButton *color_button)
{
  GeglColor *color;

  color = gimp_color_button_get_color (color_button);
  gimp_color_set_alpha (color, gtk_adjustment_get_value (adjustment) / 100.0);
  gimp_color_button_set_color (color_button, color);
  g_object_unref (color);
}

static void
channel_options_color_changed (GimpColorButton *button,
                               GtkAdjustment   *adjustment)
{
  GeglColor *color;
  gdouble    rgba[4];

  color = gimp_color_button_get_color (button);
  gegl_color_get_pixel (color, babl_format ("R'G'B'A double"), rgba);
  gtk_adjustment_set_value (adjustment, rgba[3] * 100.0);
  g_object_unref (color);
}

/* --- color-profile-dialog.c --- */
/* AmmoOS Image - The AmmoOS Field Image Research
 * Copyright (C) 1995 Spencer Kimball and Peter Mattis
 *
 * color-profile-dialog.h
 * Copyright (C) 2015 Michael Natterer <mitch@ammoos.org>
 *
 * Partly based on the lcms plug-in
 * Copyright (C) 2006, 2007  Sven Neumann <sven@ammoos.org>
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

#include "libgimpbase/gimpbase.h"
#include "libgimpcolor/gimpcolor.h"
#include "libgimpwidgets/gimpwidgets.h"

#include "dialogs-types.h"

#include "config/gimpcoreconfig.h"

#include "core/ammoos.h"
#include "core/gimpcontext.h"
#include "core/gimpimage.h"

#include "widgets/gimphelp-ids.h"
#include "widgets/gimpviewabledialog.h"
#include "widgets/gimpwidgets-constructors.h"
#include "widgets/gimpwidgets-utils.h"

#include "color-profile-dialog.h"

#include "ammoos-intl.h"


typedef struct
{
  ColorProfileDialogType    dialog_type;
  GimpImage                *image;
  GimpColorProfile         *current_profile;
  GimpColorProfile         *default_profile;
  GimpColorRenderingIntent  intent;
  gboolean                  bpc;
  GimpColorProfileCallback  callback;
  gpointer                  user_data;

  GimpColorConfig          *config;
  GtkWidget                *dialog;
  GtkWidget                *main_vbox;
  GtkWidget                *combo;
  GtkWidget                *dest_view;

} ProfileDialog;


static void        color_profile_dialog_free     (ProfileDialog *private);
static GtkWidget * color_profile_combo_box_new   (ProfileDialog *private);
static void        color_profile_dialog_response (GtkWidget     *dialog,
                                                  gint           response_id,
                                                  ProfileDialog *private);
static void        color_profile_dest_changed    (GtkWidget     *combo,
                                                  ProfileDialog *private);


/*  public functions  */

GtkWidget *
color_profile_dialog_new (ColorProfileDialogType    dialog_type,
                          GimpImage                *image,
                          GimpContext              *context,
                          GtkWidget                *parent,
                          GimpColorProfile         *current_profile,
                          GimpColorProfile         *default_profile,
                          GimpColorRenderingIntent  intent,
                          gboolean                  bpc,
                          GimpColorProfileCallback  callback,
                          gpointer                  user_data)
{
  ProfileDialog *private;
  GtkWidget     *dialog;
  GtkWidget     *frame;
  GtkWidget     *vbox;
  GtkWidget     *expander;
  GtkWidget     *label;
  const gchar   *dest_label;

  g_return_val_if_fail (GIMP_IS_IMAGE (image), NULL);
  g_return_val_if_fail (GIMP_IS_CONTEXT (context), NULL);
  g_return_val_if_fail (GTK_IS_WIDGET (parent), NULL);
  g_return_val_if_fail (current_profile == NULL ||
                        GIMP_IS_COLOR_PROFILE (current_profile), NULL);
  g_return_val_if_fail (default_profile == NULL ||
                        GIMP_IS_COLOR_PROFILE (default_profile), NULL);
  g_return_val_if_fail (callback != NULL, NULL);

  private = g_slice_new0 (ProfileDialog);

  private->dialog_type     = dialog_type;
  private->image           = image;
  private->current_profile = current_profile;
  private->default_profile = default_profile;
  private->intent          = intent;
  private->bpc             = bpc;
  private->callback        = callback;
  private->user_data       = user_data;
  private->config          = image->ammoos->config->color_management;

  switch (dialog_type)
    {
    case COLOR_PROFILE_DIALOG_ASSIGN_PROFILE:
      dialog =
        gimp_viewable_dialog_new (g_list_prepend (NULL, image), context,
                                  _("Assign ICC Color Profile"),
                                  "ammoos-image-color-profile-assign",
                                  NULL,
                                  _("Assign a color profile to the image"),
                                  parent,
                                  gimp_standard_help_func,
                                  GIMP_HELP_IMAGE_COLOR_PROFILE_ASSIGN,

                                  _("_Cancel"), GTK_RESPONSE_CANCEL,
                                  _("_Assign"), GTK_RESPONSE_OK,

                                  NULL);
      dest_label = _("Assign");
      break;

    case COLOR_PROFILE_DIALOG_CONVERT_TO_PROFILE:
      dialog =
        gimp_viewable_dialog_new (g_list_prepend (NULL, image), context,
                                  _("Convert to ICC Color Profile"),
                                  "ammoos-image-color-profile-convert",
                                  NULL,
                                  _("Convert the image to a color profile"),
                                  parent,
                                  gimp_standard_help_func,
                                  GIMP_HELP_IMAGE_COLOR_PROFILE_CONVERT,

                                  _("_Cancel"),  GTK_RESPONSE_CANCEL,
                                  _("C_onvert"), GTK_RESPONSE_OK,

                                  NULL);
      dest_label = _("Convert to");
      break;

    case COLOR_PROFILE_DIALOG_CONVERT_TO_RGB:
      dialog =
        gimp_viewable_dialog_new (g_list_prepend (NULL, image), context,
                                  _("RGB Conversion"),
                                  "ammoos-image-convert-rgb",
                                  GIMP_ICON_CONVERT_RGB,
                                  _("Convert Image to RGB"),
                                  parent,
                                  gimp_standard_help_func,
                                  GIMP_HELP_IMAGE_CONVERT_RGB,

                                  _("_Cancel"),  GTK_RESPONSE_CANCEL,
                                  _("C_onvert"), GTK_RESPONSE_OK,

                                  NULL);
      dest_label = _("Convert to");
      break;

    case COLOR_PROFILE_DIALOG_CONVERT_TO_GRAY:
      dialog =
        gimp_viewable_dialog_new (g_list_prepend (NULL, image), context,
                                  _("Grayscale Conversion"),
                                  "ammoos-image-convert-gray",
                                  GIMP_ICON_CONVERT_GRAYSCALE,
                                  _("Convert Image to Grayscale"),
                                  parent,
                                  gimp_standard_help_func,
                                  GIMP_HELP_IMAGE_CONVERT_GRAYSCALE,

                                  _("_Cancel"),  GTK_RESPONSE_CANCEL,
                                  _("C_onvert"), GTK_RESPONSE_OK,

                                  NULL);
      dest_label = _("Convert to");
      break;

    case COLOR_PROFILE_DIALOG_SELECT_SOFTPROOF_PROFILE:
      dialog =
        gimp_viewable_dialog_new (g_list_prepend (NULL, image), context,
                                  _("Soft-Proof Profile"),
                                  "ammoos-select-softproof-profile",
                                  GIMP_ICON_DOCUMENT_PRINT,
                                  _("Select Soft-Proof Profile"),
                                  parent,
                                  gimp_standard_help_func,
                                  GIMP_HELP_VIEW_COLOR_MANAGEMENT,

                                  _("_Cancel"), GTK_RESPONSE_CANCEL,
                                  _("_Select"), GTK_RESPONSE_OK,

                                  NULL);
      dest_label = _("New Color Profile");
      break;

    default:
      g_return_val_if_reached (NULL);
    }

  private->dialog = dialog;

  gimp_dialog_set_alternative_button_order (GTK_DIALOG (dialog),
                                           GTK_RESPONSE_OK,
                                           GTK_RESPONSE_CANCEL,
                                           -1);

  gtk_window_set_resizable (GTK_WINDOW (dialog), FALSE);

  g_object_weak_ref (G_OBJECT (dialog),
                     (GWeakNotify) color_profile_dialog_free, private);

  g_signal_connect (dialog, "response",
                    G_CALLBACK (color_profile_dialog_response),
                    private);

  private->main_vbox = gtk_box_new (GTK_ORIENTATION_VERTICAL, 12);
  gtk_container_set_border_width (GTK_CONTAINER (private->main_vbox), 12);
  gtk_box_pack_start (GTK_BOX (gtk_dialog_get_content_area (GTK_DIALOG (dialog))),
                      private->main_vbox, TRUE, TRUE, 0);
  gtk_widget_set_visible (private->main_vbox, TRUE);

  frame = gimp_frame_new (_("Current Color Profile"));
  gtk_box_pack_start (GTK_BOX (private->main_vbox), frame, FALSE, FALSE, 0);
  gtk_widget_set_visible (frame, TRUE);

  label = gimp_color_profile_label_new (private->current_profile);
  gtk_container_add (GTK_CONTAINER (frame), label);
  gtk_widget_set_visible (label, TRUE);

  frame = gimp_frame_new (dest_label);
  gtk_box_pack_start (GTK_BOX (private->main_vbox), frame, FALSE, FALSE, 0);
  gtk_widget_set_visible (frame, TRUE);

  vbox = gtk_box_new (GTK_ORIENTATION_VERTICAL, 6);
  gtk_container_add (GTK_CONTAINER (frame), vbox);
  gtk_widget_set_visible (vbox, TRUE);

  private->combo = color_profile_combo_box_new (private);
  gtk_box_pack_start (GTK_BOX (vbox), private->combo, FALSE, FALSE, 0);
  gtk_widget_set_visible (private->combo, TRUE);

  expander = gtk_expander_new_with_mnemonic (_("Profile _details"));
  gtk_box_pack_start (GTK_BOX (vbox), expander, FALSE, FALSE, 0);
  gtk_widget_set_visible (expander, TRUE);

  private->dest_view = gimp_color_profile_view_new ();
  gtk_container_add (GTK_CONTAINER (expander), private->dest_view);
  gtk_widget_set_visible (private->dest_view, TRUE);

  g_signal_connect (private->combo, "changed",
                    G_CALLBACK (color_profile_dest_changed),
                    private);

  color_profile_dest_changed (private->combo, private);

  if (dialog_type == COLOR_PROFILE_DIALOG_CONVERT_TO_PROFILE)
    {
      GtkWidget *vbox;
      GtkWidget *hbox;
      GtkWidget *combo;
      GtkWidget *toggle;

      vbox = gtk_box_new (GTK_ORIENTATION_VERTICAL, 6);
      gtk_box_pack_start (GTK_BOX (private->main_vbox), vbox, FALSE, FALSE, 0);
      gtk_widget_set_visible (vbox, TRUE);

      hbox = gtk_box_new (GTK_ORIENTATION_HORIZONTAL, 6);
      gtk_box_pack_start (GTK_BOX (vbox), hbox, FALSE, FALSE, 0);
      gtk_widget_set_visible (hbox, TRUE);

      label = gtk_label_new_with_mnemonic (_("_Rendering Intent:"));
      gtk_box_pack_start (GTK_BOX (hbox), label, FALSE, FALSE, 0);
      gtk_widget_set_visible (label, TRUE);

      combo = gimp_enum_combo_box_new (GIMP_TYPE_COLOR_RENDERING_INTENT);
      gtk_box_pack_start (GTK_BOX (hbox), combo, TRUE, TRUE, 0);
      gtk_widget_set_visible (combo, TRUE);

      gimp_int_combo_box_connect (GIMP_INT_COMBO_BOX (combo),
                                  private->intent,
                                  G_CALLBACK (gimp_int_combo_box_get_active),
                                  &private->intent, NULL);

      gtk_label_set_mnemonic_widget (GTK_LABEL (label), combo);

      toggle =
        gtk_check_button_new_with_mnemonic (_("_Black Point Compensation"));
      gtk_toggle_button_set_active (GTK_TOGGLE_BUTTON (toggle), private->bpc);
      gtk_box_pack_start (GTK_BOX (vbox), toggle, FALSE, FALSE, 0);
      gtk_widget_set_visible (toggle, TRUE);

      g_signal_connect (toggle, "toggled",
                        G_CALLBACK (gimp_toggle_button_update),
                        &private->bpc);
    }

  return dialog;
}


/*  private functions  */

static void
color_profile_dialog_free (ProfileDialog *private)
{
  g_slice_free (ProfileDialog, private);
}

static GtkWidget *
color_profile_combo_box_new (ProfileDialog *private)
{
  GtkListStore *store;
  GtkWidget    *combo;
  GtkWidget    *chooser;
  GFile        *history;

  history = gimp_directory_file ("profilerc", NULL);
  store = gimp_color_profile_store_new (history);
  g_object_unref (history);

  if (private->default_profile)
    {
      GimpImageBaseType  base_type;
      GimpPrecision      precision;
      GError            *error = NULL;

      switch (private->dialog_type)
        {
        case COLOR_PROFILE_DIALOG_ASSIGN_PROFILE:
        case COLOR_PROFILE_DIALOG_CONVERT_TO_PROFILE:
          base_type = gimp_image_get_base_type (private->image);
          break;

        case COLOR_PROFILE_DIALOG_CONVERT_TO_RGB:
          base_type = GIMP_RGB;
          break;

        case COLOR_PROFILE_DIALOG_CONVERT_TO_GRAY:
          base_type = GIMP_GRAY;
          break;

        default:
          g_return_val_if_reached (NULL);
        }

      precision = gimp_image_get_precision (private->image);

      if (! gimp_color_profile_store_add_defaults (GIMP_COLOR_PROFILE_STORE (store),
                                                   private->config,
                                                   base_type,
                                                   precision,
                                                   &error))
        {
          gimp_message (private->image->ammoos, G_OBJECT (private->dialog),
                        GIMP_MESSAGE_ERROR,
                        "%s", error->message);
          g_clear_error (&error);
        }
    }
  else
    {
      gimp_color_profile_store_add_file (GIMP_COLOR_PROFILE_STORE (store),
                                         NULL, NULL);
    }

  chooser =
    gimp_color_profile_chooser_dialog_new (_("Select Destination Profile"),
                                           NULL,
                                           GTK_FILE_CHOOSER_ACTION_OPEN);

  gimp_color_profile_chooser_dialog_connect_path (chooser,
                                                  G_OBJECT (private->image->ammoos->config),
                                                  "color-profile-path");

  combo = gimp_color_profile_combo_box_new_with_model (chooser,
                                                       GTK_TREE_MODEL (store));
  g_object_unref (store);

  gimp_color_profile_combo_box_set_active_file (GIMP_COLOR_PROFILE_COMBO_BOX (combo),
                                                NULL, NULL);

  return combo;
}

static void
color_profile_dialog_response (GtkWidget     *dialog,
                               gint           response_id,
                               ProfileDialog *private)
{
  if (response_id == GTK_RESPONSE_OK)
    {
      GimpColorProfile *profile = NULL;
      GFile            *file;

      file = gimp_color_profile_combo_box_get_active_file (GIMP_COLOR_PROFILE_COMBO_BOX (private->combo));

      if (file)
        {
          GError *error = NULL;

          profile = gimp_color_profile_new_from_file (file, &error);
          g_object_unref (file);

          if (! profile)
            {
              gimp_message (private->image->ammoos, G_OBJECT (dialog),
                            GIMP_MESSAGE_ERROR,
                            "%s", error->message);
              g_clear_error (&error);

              return;
            }
        }
      else if (private->default_profile)
        {
          profile = g_object_ref (private->default_profile);
        }

      private->callback (dialog,
                         private->image,
                         profile,
                         file,
                         private->intent,
                         private->bpc,
                         private->user_data);

      if (profile)
        g_object_unref (profile);
    }
  else
    {
      gtk_widget_destroy (dialog);
    }
}

static void
color_profile_dest_changed (GtkWidget     *combo,
                            ProfileDialog *private)
{
  GimpColorProfile *dest_profile = NULL;
  GFile            *file;

  file = gimp_color_profile_combo_box_get_active_file (GIMP_COLOR_PROFILE_COMBO_BOX (combo));

  if (file)
    {
      GError *error = NULL;

      dest_profile = gimp_color_profile_new_from_file (file, &error);
      g_object_unref (file);

      if (! dest_profile)
        {
          gimp_color_profile_view_set_error (GIMP_COLOR_PROFILE_VIEW (private->dest_view),
                                             error->message);
          g_clear_error (&error);
        }
    }
  else if (private->default_profile)
    {
      dest_profile = g_object_ref (private->default_profile);
    }
  else
    {
      gimp_color_profile_view_set_error (GIMP_COLOR_PROFILE_VIEW (private->dest_view),
                                         C_("profile", "None"));
    }

  if (dest_profile)
    {
      gimp_color_profile_view_set_profile (GIMP_COLOR_PROFILE_VIEW (private->dest_view),
                                           dest_profile);
      g_object_unref (dest_profile);
    }
}

/* --- color-profile-import-dialog.c --- */
/* AmmoOS Image - The AmmoOS Field Image Research
 * Copyright (C) 1995 Spencer Kimball and Peter Mattis
 *
 * color-profile-import-dialog.h
 * Copyright (C) 2015 Michael Natterer <mitch@ammoos.org>
 *
 * Partly based on the lcms plug-in
 * Copyright (C) 2006, 2007  Sven Neumann <sven@ammoos.org>
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

#include "libgimpbase/gimpbase.h"
#include "libgimpcolor/gimpcolor.h"
#include "libgimpconfig/gimpconfig.h"
#include "libgimpwidgets/gimpwidgets.h"

#include "dialogs-types.h"

#include "config/gimpcoreconfig.h"

#include "core/ammoos.h"
#include "core/gimpcontext.h"
#include "core/gimpimage.h"
#include "core/gimpimage-color-profile.h"

#include "widgets/gimphelp-ids.h"
#include "widgets/gimpviewabledialog.h"
#include "widgets/gimpwidgets-constructors.h"

#include "color-profile-import-dialog.h"

#include "ammoos-intl.h"


/*  public functions  */

GimpColorProfilePolicy
color_profile_import_dialog_run (GimpImage                 *image,
                                 GimpContext               *context,
                                 GtkWidget                 *parent,
                                 GimpColorProfile         **dest_profile,
                                 GimpColorRenderingIntent  *intent,
                                 gboolean                  *bpc,
                                 gboolean                  *dont_ask)
{
  GtkWidget              *dialog;
  GtkWidget              *main_vbox;
  GtkWidget              *vbox;
  GtkWidget              *stack;
  GtkWidget              *switcher;
  GtkWidget              *frame;
  GtkWidget              *label;
  GtkWidget              *intent_combo;
  GtkWidget              *bpc_toggle;
  GtkWidget              *dont_ask_toggle;
  GimpColorProfile       *src_profile;
  GimpColorProfile       *pref_profile = NULL;
  GimpColorProfilePolicy  policy;
  const gchar            *frame_title;
  gchar                  *text;

  g_return_val_if_fail (GIMP_IS_IMAGE (image), GIMP_COLOR_PROFILE_POLICY_KEEP);
  g_return_val_if_fail (GIMP_IS_CONTEXT (context), GIMP_COLOR_PROFILE_POLICY_KEEP);
  g_return_val_if_fail (parent == NULL || GTK_IS_WIDGET (parent),
                        GIMP_COLOR_PROFILE_POLICY_KEEP);
  g_return_val_if_fail (dest_profile != NULL, GIMP_COLOR_PROFILE_POLICY_KEEP);

  src_profile   = gimp_image_get_color_profile (image);
  *dest_profile = gimp_image_get_builtin_color_profile (image);

  if (gimp_image_get_base_type (image) == GIMP_GRAY)
    {
      frame_title = _("Convert the image to the built-in grayscale color profile?");

      pref_profile = gimp_color_config_get_gray_color_profile (image->ammoos->config->color_management, NULL);
      if (pref_profile && gimp_color_profile_is_equal (pref_profile, *dest_profile))
        g_clear_object (&pref_profile);
    }
  else
    {
      frame_title = _("Convert the image to the built-in sRGB color profile?");

      pref_profile = gimp_color_config_get_rgb_color_profile (image->ammoos->config->color_management, NULL);
      if (pref_profile && gimp_color_profile_is_equal (pref_profile, *dest_profile))
        g_clear_object (&pref_profile);
    }

  dialog =
    gimp_viewable_dialog_new (g_list_prepend (NULL, image), context,
                              _("Keep the Embedded Working Space?"),
                              "ammoos-image-color-profile-import",
                              "ammoos-prefs-color-management",
                              _("Keep the image's color profile"),
                              parent,
                              gimp_standard_help_func,
                              GIMP_HELP_IMAGE_COLOR_PROFILE_IMPORT,

                              _("_Keep"),    GTK_RESPONSE_YES,
                              _("_Convert"), GTK_RESPONSE_NO,

                              NULL);

  gtk_dialog_set_default_response (GTK_DIALOG (dialog), GTK_RESPONSE_YES);

  gtk_window_set_resizable (GTK_WINDOW (dialog), FALSE);

  main_vbox = gtk_box_new (GTK_ORIENTATION_VERTICAL, 12);
  gtk_container_set_border_width (GTK_CONTAINER (main_vbox), 12);
  gtk_box_pack_start (GTK_BOX (gtk_dialog_get_content_area (GTK_DIALOG (dialog))),
                      main_vbox, TRUE, TRUE, 0);
  gtk_widget_set_visible (main_vbox, TRUE);

  text = g_strdup_printf (_("The image '%s' has an embedded color profile"),
                          gimp_image_get_display_name (image));
  frame = gimp_frame_new (text);
  g_free (text);
  gtk_box_pack_start (GTK_BOX (main_vbox), frame, FALSE, FALSE, 0);
  gtk_widget_set_visible (frame, TRUE);

  label = gimp_color_profile_label_new (src_profile);
  gtk_container_add (GTK_CONTAINER (frame), label);
  gtk_widget_set_visible (label, TRUE);

  switcher = gtk_stack_switcher_new ();

  stack = gtk_stack_new ();
  gtk_stack_switcher_set_stack (GTK_STACK_SWITCHER (switcher), GTK_STACK (stack));
  gtk_box_pack_start (GTK_BOX (main_vbox), stack, FALSE, FALSE, 0);
  gtk_box_pack_start (GTK_BOX (main_vbox), switcher, FALSE, FALSE, 0);
  gtk_widget_set_visible (stack, TRUE);

  frame = gimp_frame_new (frame_title);
  gtk_stack_add_titled (GTK_STACK (stack), frame, "builtin",
                        _("Built-in Profile"));
  gtk_widget_set_visible (frame, TRUE);

  label = gimp_color_profile_label_new (*dest_profile);
  gtk_container_add (GTK_CONTAINER (frame), label);
  gtk_widget_set_visible (label, TRUE);

  if (pref_profile)
    {
      if (gimp_image_get_base_type (image) == GIMP_GRAY)
        frame_title  = _("Convert the image to the preferred grayscale color profile?");
      else
        frame_title = _("Convert the image to the preferred RGB color profile?");

      frame = gimp_frame_new (frame_title);
      gtk_stack_add_titled (GTK_STACK (stack), frame, "preferred",
                            _("Preferred Profile"));
      gtk_widget_set_visible (frame, TRUE);

      label = gimp_color_profile_label_new (pref_profile);
      gtk_container_add (GTK_CONTAINER (frame), label);
      gtk_widget_set_visible (label, TRUE);

      gtk_widget_set_visible (switcher, TRUE);
      gtk_stack_set_visible_child_name (GTK_STACK (stack), "preferred");
    }

  if (intent && bpc)
    {
      vbox = gtk_box_new (GTK_ORIENTATION_VERTICAL, 6);
      gtk_box_pack_start (GTK_BOX (main_vbox), vbox, FALSE, FALSE, 0);
      gtk_widget_set_visible (vbox, TRUE);
    }
  else
    {
      vbox = main_vbox;
    }

  if (intent)
    {
      GtkWidget *hbox;

      hbox = gtk_box_new (GTK_ORIENTATION_HORIZONTAL, 6);
      gtk_box_pack_start (GTK_BOX (vbox), hbox, FALSE, FALSE, 0);
      gtk_widget_set_visible (hbox, TRUE);

      label = gtk_label_new_with_mnemonic (_("_Rendering Intent:"));
      gtk_box_pack_start (GTK_BOX (hbox), label, FALSE, FALSE, 0);
      gtk_widget_set_visible (label, TRUE);

      intent_combo = gimp_enum_combo_box_new (GIMP_TYPE_COLOR_RENDERING_INTENT);
      gimp_int_combo_box_set_active (GIMP_INT_COMBO_BOX (intent_combo),
                                     *intent);
      gtk_box_pack_start (GTK_BOX (hbox), intent_combo, TRUE, TRUE, 0);
      gtk_widget_set_visible (intent_combo, TRUE);

      gtk_label_set_mnemonic_widget (GTK_LABEL (label), intent_combo);
    }

  if (bpc)
    {
      bpc_toggle =
        gtk_check_button_new_with_mnemonic (_("_Black Point Compensation"));
      gtk_toggle_button_set_active (GTK_TOGGLE_BUTTON (bpc_toggle), *bpc);
      gtk_box_pack_start (GTK_BOX (vbox), bpc_toggle, FALSE, FALSE, 0);
      gtk_widget_set_visible (bpc_toggle, TRUE);
    }

  if (dont_ask)
    {
      dont_ask_toggle =
        gtk_check_button_new_with_mnemonic (_("_Don't ask me again"));
      gtk_widget_set_tooltip_text (dont_ask_toggle,
                                   _("Your choice can later be edited in Preferences > Color Management"));
      gtk_box_pack_end (GTK_BOX (main_vbox), dont_ask_toggle, FALSE, FALSE, 0);
      gtk_toggle_button_set_active (GTK_TOGGLE_BUTTON (dont_ask_toggle), FALSE);
      gtk_widget_set_visible (dont_ask_toggle, TRUE);
    }

  switch (gtk_dialog_run (GTK_DIALOG (dialog)))
    {
    case GTK_RESPONSE_NO:
      if (g_strcmp0 (gtk_stack_get_visible_child_name (GTK_STACK (stack)),
                     "builtin") == 0)
        {
          policy = GIMP_COLOR_PROFILE_POLICY_CONVERT_BUILTIN;
          g_object_ref (*dest_profile);
        }
      else
        {
          policy = GIMP_COLOR_PROFILE_POLICY_CONVERT_PREFERRED;
          *dest_profile = g_object_ref (pref_profile);
        }
      break;

    default:
      policy = GIMP_COLOR_PROFILE_POLICY_KEEP;
      break;
    }

  if (intent)
    gimp_int_combo_box_get_active (GIMP_INT_COMBO_BOX (intent_combo),
                                   (gint *) intent);

  if (bpc)
    *bpc = gtk_toggle_button_get_active (GTK_TOGGLE_BUTTON (bpc_toggle));

  if (dont_ask)
    *dont_ask = gtk_toggle_button_get_active (GTK_TOGGLE_BUTTON (dont_ask_toggle));

  gtk_widget_destroy (dialog);
  g_clear_object (&pref_profile);

  return policy;
}

/* --- convert-indexed-dialog.c --- */
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

#include "libgimpwidgets/gimpwidgets.h"

#include "dialogs-types.h"

#include "core/ammoos.h"
#include "core/gimpcontainer-filter.h"
#include "core/gimpcontext.h"
#include "core/gimpdatafactory.h"
#include "core/gimpimage.h"
#include "core/gimplist.h"
#include "core/gimppalette.h"

#include "widgets/gimphelp-ids.h"
#include "widgets/gimpviewablebox.h"
#include "widgets/gimpviewabledialog.h"
#include "widgets/gimpwidgets-utils.h"

#include "convert-indexed-dialog.h"

#include "ammoos-intl.h"


typedef struct _IndexedDialog IndexedDialog;

struct _IndexedDialog
{
  GimpImage                  *image;
  GimpConvertPaletteType      palette_type;
  gint                        max_colors;
  gboolean                    remove_duplicates;
  GimpConvertDitherType       dither_type;
  gboolean                    dither_alpha;
  gboolean                    dither_text_layers;
  GimpPalette                *custom_palette;
  GimpConvertIndexedCallback  callback;
  gpointer                    user_data;

  GtkWidget                  *dialog;
  GimpContext                *context;
  GimpContainer              *container;
  GtkWidget                  *duplicates_toggle;
};


static void        convert_dialog_free            (IndexedDialog *private);
static void        convert_dialog_response        (GtkWidget     *widget,
                                                   gint           response_id,
                                                   IndexedDialog *private);
static GtkWidget * convert_dialog_palette_box     (IndexedDialog *private);
static gboolean    convert_dialog_palette_filter  (GimpObject    *object,
                                                   gpointer       user_data);
static void        convert_dialog_palette_changed (GimpContext   *context,
                                                   GimpPalette   *palette,
                                                   IndexedDialog *private);
static void        convert_dialog_type_update     (GtkWidget     *widget,
                                                   IndexedDialog *private);



/*  public functions  */

GtkWidget *
convert_indexed_dialog_new (GimpImage                  *image,
                            GimpContext                *context,
                            GtkWidget                  *parent,
                            GimpConvertPaletteType      palette_type,
                            gint                        max_colors,
                            gboolean                    remove_duplicates,
                            GimpConvertDitherType       dither_type,
                            gboolean                    dither_alpha,
                            gboolean                    dither_text_layers,
                            GimpPalette                *custom_palette,
                            GimpConvertIndexedCallback  callback,
                            gpointer                    user_data)
{
  IndexedDialog *private;
  GtkWidget     *dialog;
  GtkWidget     *button;
  GtkWidget     *main_vbox;
  GtkWidget     *vbox;
  GtkWidget     *hbox;
  GtkWidget     *label;
  GtkAdjustment *adjustment;
  GtkWidget     *spinbutton;
  GtkWidget     *frame;
  GtkWidget     *toggle;
  GtkWidget     *palette_box;
  GtkWidget     *combo;

  g_return_val_if_fail (GIMP_IS_IMAGE (image), NULL);
  g_return_val_if_fail (GIMP_IS_CONTEXT (context), NULL);
  g_return_val_if_fail (GTK_IS_WIDGET (parent), NULL);
  g_return_val_if_fail (custom_palette == NULL ||
                        GIMP_IS_PALETTE (custom_palette), NULL);
  g_return_val_if_fail (callback != NULL, NULL);

  private = g_slice_new0 (IndexedDialog);

  private->image              = image;
  private->palette_type       = palette_type;
  private->max_colors         = max_colors;
  private->remove_duplicates  = remove_duplicates;
  private->dither_type        = dither_type;
  private->dither_alpha       = dither_alpha;
  private->dither_text_layers = dither_text_layers;
  private->custom_palette     = custom_palette;
  private->callback           = callback;
  private->user_data          = user_data;

  private->dialog = dialog =
    gimp_viewable_dialog_new (g_list_prepend (NULL, image), context,
                              _("Indexed Color Conversion"),
                              "ammoos-image-convert-indexed",
                              GIMP_ICON_CONVERT_INDEXED,
                              _("Convert Image to Indexed Colors"),
                              parent,
                              gimp_standard_help_func,
                              GIMP_HELP_IMAGE_CONVERT_INDEXED,

                              _("_Cancel"),  GTK_RESPONSE_CANCEL,
                              _("C_onvert"), GTK_RESPONSE_OK,

                              NULL);

  gimp_dialog_set_alternative_button_order (GTK_DIALOG (dialog),
                                           GTK_RESPONSE_OK,
                                           GTK_RESPONSE_CANCEL,
                                           -1);

  gtk_window_set_resizable (GTK_WINDOW (dialog), FALSE);

  g_object_weak_ref (G_OBJECT (dialog),
                     (GWeakNotify) convert_dialog_free, private);

  g_signal_connect (dialog, "response",
                    G_CALLBACK (convert_dialog_response),
                    private);

  palette_box = convert_dialog_palette_box (private);

  main_vbox = gtk_box_new (GTK_ORIENTATION_VERTICAL, 12);
  gtk_container_set_border_width (GTK_CONTAINER (main_vbox), 12);
  gtk_box_pack_start (GTK_BOX (gtk_dialog_get_content_area (GTK_DIALOG (dialog))),
                      main_vbox, TRUE, TRUE, 0);
  gtk_widget_set_visible (main_vbox, TRUE);


  /*  palette  */

  frame =
    gimp_enum_radio_frame_new_with_range (GIMP_TYPE_CONVERT_PALETTE_TYPE,
                                          GIMP_CONVERT_PALETTE_GENERATE,
                                          (palette_box ?
                                           GIMP_CONVERT_PALETTE_CUSTOM :
                                           GIMP_CONVERT_PALETTE_MONO),
                                          gtk_label_new (_("Colormap")),
                                          G_CALLBACK (convert_dialog_type_update),
                                          private, NULL,
                                          &button);

  gimp_int_radio_group_set_active (GTK_RADIO_BUTTON (button),
                                   private->palette_type);
  gtk_box_pack_start (GTK_BOX (main_vbox), frame, FALSE, FALSE, 0);
  gtk_widget_set_visible (frame, TRUE);

  /*  max n_colors  */
  hbox = gtk_box_new (GTK_ORIENTATION_HORIZONTAL, 6);
  gimp_enum_radio_frame_add (GTK_FRAME (frame), hbox,
                             GIMP_CONVERT_PALETTE_GENERATE, TRUE);
  gtk_widget_set_visible (hbox, TRUE);

  label = gtk_label_new_with_mnemonic (_("_Maximum number of colors:"));
  gtk_box_pack_start (GTK_BOX (hbox), label, FALSE, FALSE, 0);
  gtk_widget_set_visible (label, TRUE);

  if (private->max_colors == 256 && gimp_image_has_alpha (image))
    private->max_colors = 255;

  adjustment = gtk_adjustment_new (private->max_colors, 2, 256, 1, 8, 0);
  spinbutton = gimp_spin_button_new (adjustment, 1.0, 0);
  gtk_spin_button_set_numeric (GTK_SPIN_BUTTON (spinbutton), TRUE);
  gtk_label_set_mnemonic_widget (GTK_LABEL (label), spinbutton);
  gtk_box_pack_start (GTK_BOX (hbox), spinbutton, FALSE, FALSE, 0);
  gtk_widget_set_visible (spinbutton, TRUE);

  g_signal_connect (adjustment, "value-changed",
                    G_CALLBACK (gimp_int_adjustment_update),
                    &private->max_colors);

  /*  custom palette  */
  if (palette_box)
    {
      gimp_enum_radio_frame_add (GTK_FRAME (frame), palette_box,
                                 GIMP_CONVERT_PALETTE_CUSTOM, TRUE);
      gtk_widget_set_visible (palette_box, TRUE);
    }

  vbox = gtk_bin_get_child (GTK_BIN (frame));

  private->duplicates_toggle = toggle =
    gtk_check_button_new_with_mnemonic (_("_Remove unused and duplicate "
                                          "colors from colormap"));
  gtk_toggle_button_set_active (GTK_TOGGLE_BUTTON (toggle),
                                private->remove_duplicates);
  gtk_box_pack_start (GTK_BOX (vbox), toggle, FALSE, FALSE, 3);
  gtk_widget_set_visible (toggle, TRUE);

  if (private->palette_type == GIMP_CONVERT_PALETTE_GENERATE ||
      private->palette_type == GIMP_CONVERT_PALETTE_MONO)
    gtk_widget_set_sensitive (toggle, FALSE);

  g_signal_connect (toggle, "toggled",
                    G_CALLBACK (gimp_toggle_button_update),
                    &private->remove_duplicates);

  /*  dithering  */

  frame = gimp_frame_new (_("Dithering"));
  gtk_box_pack_start (GTK_BOX (main_vbox), frame, FALSE, FALSE, 0);
  gtk_widget_set_visible (frame, TRUE);

  vbox = gtk_box_new (GTK_ORIENTATION_VERTICAL, 6);
  gtk_container_add (GTK_CONTAINER (frame), vbox);
  gtk_widget_set_visible (vbox, TRUE);

  hbox = gtk_box_new (GTK_ORIENTATION_HORIZONTAL, 6);
  gtk_box_pack_start (GTK_BOX (vbox), hbox, FALSE, FALSE, 0);
  gtk_widget_set_visible (hbox, TRUE);

  label = gtk_label_new_with_mnemonic (_("Color _dithering:"));
  gtk_box_pack_start (GTK_BOX (hbox), label, FALSE, FALSE, 0);
  gtk_widget_set_visible (label, TRUE);

  combo = gimp_enum_combo_box_new (GIMP_TYPE_CONVERT_DITHER_TYPE);
  gtk_label_set_mnemonic_widget (GTK_LABEL (label), combo);
  gtk_box_pack_start (GTK_BOX (hbox), combo, TRUE, TRUE, 0);
  gtk_widget_set_visible (combo, TRUE);

  gimp_int_combo_box_connect (GIMP_INT_COMBO_BOX (combo),
                              private->dither_type,
                              G_CALLBACK (gimp_int_combo_box_get_active),
                              &private->dither_type, NULL);

  toggle =
    gtk_check_button_new_with_mnemonic (_("Enable dithering of _transparency"));
  gtk_toggle_button_set_active (GTK_TOGGLE_BUTTON (toggle),
                                private->dither_alpha);
  gtk_box_pack_start (GTK_BOX (vbox), toggle, FALSE, FALSE, 0);
  gtk_widget_set_visible (toggle, TRUE);

  g_signal_connect (toggle, "toggled",
                    G_CALLBACK (gimp_toggle_button_update),
                    &private->dither_alpha);


  toggle =
    gtk_check_button_new_with_mnemonic (_("Enable dithering of text _layers"));
  gtk_toggle_button_set_active (GTK_TOGGLE_BUTTON (toggle),
                                private->dither_text_layers);
  gtk_box_pack_start (GTK_BOX (vbox), toggle, FALSE, FALSE, 0);
  gtk_widget_set_visible (toggle, TRUE);

  g_signal_connect (toggle, "toggled",
                    G_CALLBACK (gimp_toggle_button_update),
                    &private->dither_text_layers);

  gimp_help_set_help_data (toggle,
                           _("Dithering text layers will make them uneditable"),
                           NULL);

  return dialog;
}


/*  private functions  */

static void
convert_dialog_free (IndexedDialog *private)
{
  if (private->container)
    g_object_unref (private->container);

  if (private->context)
    g_object_unref (private->context);

  g_slice_free (IndexedDialog, private);
}

static void
convert_dialog_response (GtkWidget     *dialog,
                         gint           response_id,
                         IndexedDialog *private)
{
  if (response_id == GTK_RESPONSE_OK)
    {
      private->callback (dialog,
                         private->image,
                         private->palette_type,
                         private->max_colors,
                         private->remove_duplicates,
                         private->dither_type,
                         private->dither_alpha,
                         private->dither_text_layers,
                         private->custom_palette,
                         private->user_data);
    }
  else
    {
      gtk_widget_destroy (dialog);
    }
}

static GtkWidget *
convert_dialog_palette_box (IndexedDialog *private)
{
  Gimp        *ammoos = private->image->ammoos;
  GList       *list;
  GimpPalette *web_palette  = NULL;
  gboolean     custom_found = FALSE;

  /* We can't dither to > 256 colors */
  private->container =
    gimp_container_filter (gimp_data_factory_get_container (ammoos->palette_factory),
                           convert_dialog_palette_filter,
                           NULL);

  if (gimp_container_is_empty (private->container))
    {
      g_object_unref (private->container);
      private->container = NULL;
      return NULL;
    }

  private->context = gimp_context_new (ammoos, "convert-dialog", NULL);

  for (list = GIMP_LIST (private->container)->queue->head;
       list;
       list = g_list_next (list))
    {
      GimpPalette *palette = list->data;

      /* Preferentially, the initial default is 'Web' if available */
      if (web_palette == NULL &&
          g_ascii_strcasecmp (gimp_object_get_name (palette), "Web") == 0)
        {
          web_palette = palette;
        }

      if (private->custom_palette == palette)
        custom_found = TRUE;
    }

  if (! custom_found)
    {
      if (web_palette)
        private->custom_palette = web_palette;
      else
        private->custom_palette = GIMP_LIST (private->container)->queue->head->data;
    }

  gimp_context_set_palette (private->context, private->custom_palette);

  g_signal_connect (private->context, "palette-changed",
                    G_CALLBACK (convert_dialog_palette_changed),
                    private);

  return gimp_palette_box_new (private->container, private->context, NULL, 4);
}

static gboolean
convert_dialog_palette_filter (GimpObject *object,
                               gpointer    user_data)
{
  GimpPalette *palette = GIMP_PALETTE (object);

  return (gimp_palette_get_n_colors (palette) > 0 &&
          gimp_palette_get_n_colors (palette) <= 256);
}

static void
convert_dialog_palette_changed (GimpContext   *context,
                                GimpPalette   *palette,
                                IndexedDialog *private)
{
  if (! palette)
    return;

  if (gimp_palette_get_n_colors (palette) > 256)
    {
      gimp_message (private->image->ammoos, G_OBJECT (private->dialog),
                    GIMP_MESSAGE_WARNING,
                    _("Cannot convert to a palette "
                      "with more than 256 colors."));
    }
  else
    {
      private->custom_palette = palette;
    }
}

static void
convert_dialog_type_update (GtkWidget     *widget,
                            IndexedDialog *private)
{
  gimp_radio_button_update (widget, &private->palette_type);

  if (private->duplicates_toggle)
    gtk_widget_set_sensitive (private->duplicates_toggle,
                              private->palette_type !=
                              GIMP_CONVERT_PALETTE_GENERATE &&
                              private->palette_type !=
                              GIMP_CONVERT_PALETTE_MONO);
}

/* --- convert-precision-dialog.c --- */
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

#include "libgimpbase/gimpbase.h"
#include "libgimpwidgets/gimpwidgets.h"

#include "dialogs-types.h"

#include "gegl/ammoos-babl.h"

#include "core/gimpcontext.h"
#include "core/gimpimage.h"
#include "core/ammoos-utils.h"

#include "widgets/gimphelp-ids.h"
#include "widgets/gimpviewabledialog.h"
#include "widgets/gimpwidgets-utils.h"

#include "convert-precision-dialog.h"

#include "ammoos-intl.h"


typedef struct _ConvertDialog ConvertDialog;

struct _ConvertDialog
{
  GimpImage                    *image;
  GimpComponentType             component_type;
  GimpTRCType                   trc;
  GeglDitherMethod              layer_dither_method;
  GeglDitherMethod              text_layer_dither_method;
  GeglDitherMethod              channel_dither_method;
  GimpConvertPrecisionCallback  callback;
  gpointer                      user_data;
};


/*  local function prototypes  */

static void   convert_precision_dialog_free     (ConvertDialog    *private);
static void   convert_precision_dialog_response (GtkWidget        *widget,
                                                 gint              response_id,
                                                 ConvertDialog    *private);


/*  public functions  */

GtkWidget *
convert_precision_dialog_new (GimpImage                    *image,
                              GimpContext                  *context,
                              GtkWidget                    *parent,
                              GimpComponentType             component_type,
                              GeglDitherMethod              layer_dither_method,
                              GeglDitherMethod              text_layer_dither_method,
                              GeglDitherMethod              channel_dither_method,
                              GimpConvertPrecisionCallback  callback,
                              gpointer                      user_data)

{
  ConvertDialog *private;
  GtkWidget     *dialog;
  GtkWidget     *main_vbox;
  GtkWidget     *vbox;
  GtkWidget     *frame;
  GtkWidget     *perceptual_radio;
  const gchar   *enum_desc;
  gchar         *blurb;
  const Babl    *old_format;
  const Babl    *new_format;
  gint           old_bits;
  gint           new_bits;
  gboolean       dither;
  GimpTRCType    trc;

  g_return_val_if_fail (GIMP_IS_IMAGE (image), NULL);
  g_return_val_if_fail (GIMP_IS_CONTEXT (context), NULL);
  g_return_val_if_fail (GTK_IS_WIDGET (parent), NULL);
  g_return_val_if_fail (callback != NULL, NULL);

  /* random formats with the right precision */
  old_format = gimp_image_get_layer_format (image, FALSE);
  new_format = gimp_babl_format (GIMP_RGB,
                                 gimp_babl_precision (component_type, FALSE),
                                 FALSE,
                                 babl_format_get_space (old_format));

  old_bits = (babl_format_get_bytes_per_pixel (old_format) * 8 /
              babl_format_get_n_components (old_format));
  new_bits = (babl_format_get_bytes_per_pixel (new_format) * 8 /
              babl_format_get_n_components (new_format));

  /*  don't dither if we are converting to a higher bit depth,
   *  or to more than MAX_DITHER_BITS.
   */
  dither = (new_bits <  old_bits &&
            new_bits <= CONVERT_PRECISION_DIALOG_MAX_DITHER_BITS);

  trc = gimp_babl_format_get_trc (old_format);
  trc = gimp_suggest_trc_for_component_type (component_type, trc);

  private = g_slice_new0 (ConvertDialog);

  private->image                    = image;
  private->component_type           = component_type;
  private->trc                      = trc;
  private->layer_dither_method      = layer_dither_method;
  private->text_layer_dither_method = text_layer_dither_method;
  private->channel_dither_method    = channel_dither_method;
  private->callback                 = callback;
  private->user_data                = user_data;

  gimp_enum_get_value (GIMP_TYPE_COMPONENT_TYPE, component_type,
                       NULL, NULL, &enum_desc, NULL);

  blurb = g_strdup_printf (_("Convert Image to %s"), enum_desc);

  dialog = gimp_viewable_dialog_new (g_list_prepend (NULL, image), context,
                                     _("Encoding Conversion"),
                                     "ammoos-image-convert-precision",
                                     GIMP_ICON_CONVERT_PRECISION,
                                     blurb,
                                     parent,
                                     gimp_standard_help_func,
                                     GIMP_HELP_IMAGE_CONVERT_PRECISION,

                                     _("_Cancel"),  GTK_RESPONSE_CANCEL,
                                     _("C_onvert"), GTK_RESPONSE_OK,

                                     NULL);

  g_free (blurb);

  gimp_dialog_set_alternative_button_order (GTK_DIALOG (dialog),
                                           GTK_RESPONSE_OK,
                                           GTK_RESPONSE_CANCEL,
                                           -1);

  gtk_window_set_resizable (GTK_WINDOW (dialog), FALSE);

  g_object_weak_ref (G_OBJECT (dialog),
                     (GWeakNotify) convert_precision_dialog_free, private);

  g_signal_connect (dialog, "response",
                    G_CALLBACK (convert_precision_dialog_response),
                    private);

  main_vbox = gtk_box_new (GTK_ORIENTATION_VERTICAL, 12);
  gtk_container_set_border_width (GTK_CONTAINER (main_vbox), 12);
  gtk_box_pack_start (GTK_BOX (gtk_dialog_get_content_area (GTK_DIALOG (dialog))),
                      main_vbox, TRUE, TRUE, 0);
  gtk_widget_set_visible (main_vbox, TRUE);


  /*  gamma  */

  frame = gimp_frame_new (_("Gamma"));
  gtk_box_pack_start (GTK_BOX (main_vbox), frame, FALSE, FALSE, 0);
  gtk_widget_set_visible (frame, TRUE);

  vbox = gimp_int_radio_group_new (FALSE, NULL,
                                   G_CALLBACK (gimp_radio_button_update),
                                   &private->trc, NULL,
                                   trc,

                                   _("Linear light"),
                                   GIMP_TRC_LINEAR, NULL,

                                   _("Non-Linear"),
                                   GIMP_TRC_NON_LINEAR, NULL,

                                   _("Perceptual (sRGB)"),
                                   GIMP_TRC_PERCEPTUAL, &perceptual_radio,

                                   NULL);

  if (private->trc != GIMP_TRC_PERCEPTUAL)
    gtk_widget_set_visible (perceptual_radio, FALSE);

  gtk_container_add (GTK_CONTAINER (frame), vbox);
  gtk_widget_set_visible (vbox, TRUE);


  /*  dithering  */

  if (dither)
    {
      GtkWidget    *hbox;
      GtkWidget    *label;
      GtkWidget    *combo;
      GtkSizeGroup *size_group;

      frame = gimp_frame_new (_("Dithering"));
      gtk_box_pack_start (GTK_BOX (main_vbox), frame, FALSE, FALSE, 0);
      gtk_widget_set_visible (frame, TRUE);

      vbox = gtk_box_new (GTK_ORIENTATION_VERTICAL, 6);
      gtk_container_add (GTK_CONTAINER (frame), vbox);
      gtk_widget_set_visible (vbox, TRUE);

      size_group = gtk_size_group_new (GTK_SIZE_GROUP_HORIZONTAL);

      /*  layers  */

      hbox = gtk_box_new (GTK_ORIENTATION_HORIZONTAL, 6);
      gtk_box_pack_start (GTK_BOX (vbox), hbox, FALSE, FALSE, 0);
      gtk_widget_set_visible (hbox, TRUE);

      label = gtk_label_new_with_mnemonic (_("_Layers:"));
      gtk_label_set_xalign (GTK_LABEL (label), 0.0);
      gtk_box_pack_start (GTK_BOX (hbox), label, FALSE, FALSE, 0);
      gtk_size_group_add_widget (size_group, label);
      gtk_widget_set_visible (label, TRUE);

      combo = gimp_enum_combo_box_new (GEGL_TYPE_DITHER_METHOD);
      gtk_label_set_mnemonic_widget (GTK_LABEL (label), combo);
      gtk_box_pack_start (GTK_BOX (hbox), combo, TRUE, TRUE, 0);
      gtk_widget_set_visible (combo, TRUE);

      gimp_int_combo_box_connect (GIMP_INT_COMBO_BOX (combo),
                                  private->layer_dither_method,
                                  G_CALLBACK (gimp_int_combo_box_get_active),
                                  &private->layer_dither_method, NULL);

      /*  text layers  */

      hbox = gtk_box_new (GTK_ORIENTATION_HORIZONTAL, 6);
      gtk_box_pack_start (GTK_BOX (vbox), hbox, FALSE, FALSE, 0);
      gtk_widget_set_visible (hbox, TRUE);

      label = gtk_label_new_with_mnemonic (_("_Text Layers:"));
      gtk_label_set_xalign (GTK_LABEL (label), 0.0);
      gtk_box_pack_start (GTK_BOX (hbox), label, FALSE, FALSE, 0);
      gtk_size_group_add_widget (size_group, label);
      gtk_widget_set_visible (label, TRUE);

      combo = gimp_enum_combo_box_new (GEGL_TYPE_DITHER_METHOD);
      gtk_label_set_mnemonic_widget (GTK_LABEL (label), combo);
      gtk_box_pack_start (GTK_BOX (hbox), combo, TRUE, TRUE, 0);
      gtk_widget_set_visible (combo, TRUE);

      gimp_int_combo_box_connect (GIMP_INT_COMBO_BOX (combo),
                                  private->text_layer_dither_method,
                                  G_CALLBACK (gimp_int_combo_box_get_active),
                                  &private->text_layer_dither_method, NULL);

      gimp_help_set_help_data (combo,
                               _("Dithering text layers will make them "
                                 "uneditable"),
                               NULL);

      /*  channels  */

      hbox = gtk_box_new (GTK_ORIENTATION_HORIZONTAL, 6);
      gtk_box_pack_start (GTK_BOX (vbox), hbox, FALSE, FALSE, 0);
      gtk_widget_set_visible (hbox, TRUE);

      label = gtk_label_new_with_mnemonic (_("_Channels and Masks:"));
      gtk_label_set_xalign (GTK_LABEL (label), 0.0);
      gtk_box_pack_start (GTK_BOX (hbox), label, FALSE, FALSE, 0);
      gtk_size_group_add_widget (size_group, label);
      gtk_widget_set_visible (label, TRUE);

      combo = gimp_enum_combo_box_new (GEGL_TYPE_DITHER_METHOD);
      gtk_label_set_mnemonic_widget (GTK_LABEL (label), combo);
      gtk_box_pack_start (GTK_BOX (hbox), combo, TRUE, TRUE, 0);
      gtk_widget_set_visible (combo, TRUE);

      gimp_int_combo_box_connect (GIMP_INT_COMBO_BOX (combo),
                                  private->channel_dither_method,
                                  G_CALLBACK (gimp_int_combo_box_get_active),
                                  &private->channel_dither_method, NULL);

      g_object_unref (size_group);
    }

  return dialog;
}


/*  private functions  */

static void
convert_precision_dialog_free (ConvertDialog *private)
{
  g_slice_free (ConvertDialog, private);
}

static void
convert_precision_dialog_response (GtkWidget     *dialog,
                                   gint           response_id,
                                   ConvertDialog *private)
{
  if (response_id == GTK_RESPONSE_OK)
    {
      GimpPrecision precision = gimp_babl_precision (private->component_type,
                                                     private->trc);

      private->callback (dialog,
                         private->image,
                         precision,
                         private->layer_dither_method,
                         private->text_layer_dither_method,
                         private->channel_dither_method,
                         private->user_data);
    }
  else
    {
      gtk_widget_destroy (dialog);
    }
}

/* --- data-delete-dialog.c --- */
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

#include "libgimpwidgets/gimpwidgets.h"

#include "dialogs-types.h"

#include "core/ammoos.h"
#include "core/gimpcontainer.h"
#include "core/gimpcontext.h"
#include "core/gimpdata.h"
#include "core/gimpdatafactory.h"

#include "widgets/gimpmessagebox.h"
#include "widgets/gimpmessagedialog.h"

#include "data-delete-dialog.h"

#include "ammoos-intl.h"


typedef struct _DataDeleteDialog DataDeleteDialog;

struct _DataDeleteDialog
{
  GimpDataFactory *factory;
  GimpData        *data;
  GimpContext     *context;
  GtkWidget       *parent;
};


/*  local function prototypes  */

static void  data_delete_dialog_response (GtkWidget        *dialog,
                                          gint              response_id,
                                          DataDeleteDialog *private);


/*  public functions  */

GtkWidget *
data_delete_dialog_new (GimpDataFactory *factory,
                        GimpData        *data,
                        GimpContext     *context,
                        GtkWidget       *parent)
{
  DataDeleteDialog *private;
  GtkWidget        *dialog;

  g_return_val_if_fail (GIMP_IS_DATA_FACTORY (factory), NULL);
  g_return_val_if_fail (GIMP_IS_DATA (data), NULL);
  g_return_val_if_fail (context == NULL || GIMP_IS_CONTEXT (context), NULL);
  g_return_val_if_fail (GTK_IS_WIDGET (parent), NULL);

  private = g_slice_new0 (DataDeleteDialog);

  private->factory = factory;
  private->data    = data;
  private->context = context;
  private->parent  = parent;

  dialog = gimp_message_dialog_new (_("Delete Object"),
                                    GIMP_ICON_EDIT_DELETE,
                                    gtk_widget_get_toplevel (parent), 0,
                                    gimp_standard_help_func, NULL,

                                    _("_Cancel"), GTK_RESPONSE_CANCEL,
                                    _("_Delete"), GTK_RESPONSE_OK,

                                    NULL);

  gimp_dialog_set_alternative_button_order (GTK_DIALOG (dialog),
                                           GTK_RESPONSE_OK,
                                           GTK_RESPONSE_CANCEL,
                                           -1);

  g_signal_connect_object (data, "disconnect",
                           G_CALLBACK (gtk_widget_destroy),
                           dialog, G_CONNECT_SWAPPED);

  g_signal_connect (dialog, "response",
                    G_CALLBACK (data_delete_dialog_response),
                    private);

  gimp_message_box_set_primary_text (GIMP_MESSAGE_DIALOG (dialog)->box,
                                     _("Delete '%s'?"),
                                     gimp_object_get_name (data));
  gimp_message_box_set_text (GIMP_MESSAGE_DIALOG (dialog)->box,
                             _("Are you sure you want to remove '%s' "
                               "from the list and delete it on disk?"),
                             gimp_object_get_name (data));

  return dialog;
}


/*  private functions  */

static void
data_delete_dialog_response (GtkWidget        *dialog,
                             gint              response_id,
                             DataDeleteDialog *private)
{
  gtk_widget_destroy (dialog);

  if (response_id == GTK_RESPONSE_OK)
    {
      GimpDataFactory *factory    = private->factory;
      GimpData        *data       = private->data;
      GimpContainer   *container;
      GimpObject      *new_active = NULL;
      GError          *error      = NULL;

      container = gimp_data_factory_get_container (factory);

      if (private->context &&
          GIMP_OBJECT (data) ==
          gimp_context_get_by_type (private->context,
                                    gimp_container_get_child_type (container)))
        {
          new_active = gimp_container_get_neighbor_of (container,
                                                       GIMP_OBJECT (data));
        }

      if (! gimp_data_factory_data_delete (factory, data, TRUE, &error))
        {
          gimp_message (gimp_data_factory_get_gimp (factory),
                        G_OBJECT (private->parent), GIMP_MESSAGE_ERROR,
                        "%s", error->message);
          g_clear_error (&error);
        }

      if (new_active)
        gimp_context_set_by_type (private->context,
                                  gimp_container_get_child_type (container),
                                  new_active);
    }

  g_slice_free (DataDeleteDialog, private);
}

/* --- dialogs-constructors.c --- */
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

#include "libgimpwidgets/gimpwidgets.h"

#include "dialogs-types.h"

#include "core/ammoos.h"
#include "core/gimpcontext.h"

#include "config/gimpguiconfig.h"

#include "menus/menus.h"

#include "widgets/gimpbrusheditor.h"
#include "widgets/gimpbrushfactoryview.h"
#include "widgets/gimpbufferview.h"
#include "widgets/gimpchanneltreeview.h"
#include "widgets/gimpcoloreditor.h"
#include "widgets/gimpcolormapeditor.h"
#include "widgets/gimpcriticaldialog.h"
#include "widgets/gimpdashboard.h"
#include "widgets/gimpdevicestatus.h"
#include "widgets/gimpdialogfactory.h"
#include "widgets/gimpdockwindow.h"
#include "widgets/gimpdocumentview.h"
#include "widgets/gimpdynamicseditor.h"
#include "widgets/gimpdynamicsfactoryview.h"
#include "widgets/gimperrorconsole.h"
#include "widgets/gimperrordialog.h"
#include "widgets/gimpfontfactoryview.h"
#include "widgets/gimpgradienteditor.h"
#include "widgets/gimphistogrameditor.h"
#include "widgets/gimpimageview.h"
#include "widgets/gimplayertreeview.h"
#include "widgets/gimpmenudock.h"
#include "widgets/gimppaletteeditor.h"
#include "widgets/gimppatternfactoryview.h"
#include "widgets/gimpsamplepointeditor.h"
#include "widgets/gimpselectioneditor.h"
#include "widgets/gimpsymmetryeditor.h"
#include "widgets/gimptemplateview.h"
#include "widgets/gimptoolbox.h"
#include "widgets/gimptooloptionseditor.h"
#include "widgets/gimptoolpresetfactoryview.h"
#include "widgets/gimptoolpreseteditor.h"
#include "widgets/gimpundoeditor.h"
#include "widgets/gimppathtreeview.h"

#include "display/gimpcursorview.h"
#include "display/gimpnavigationeditor.h"

#include "about-dialog.h"
#include "action-search-dialog.h"
#include "dialogs.h"
#include "dialogs-constructors.h"
#include "extensions-dialog.h"
#include "file-open-dialog.h"
#include "file-open-location-dialog.h"
#include "file-save-dialog.h"
#include "image-new-dialog.h"
#include "input-devices-dialog.h"
#include "keyboard-shortcuts-dialog.h"
#include "module-dialog.h"
#include "palette-import-dialog.h"
#include "preferences-dialog.h"
#include "quit-dialog.h"
#include "tips-dialog.h"
#include "welcome-dialog.h"

#include "ammoos-intl.h"


/**********************/
/*  toplevel dialogs  */
/**********************/

GtkWidget *
dialogs_image_new_new (GimpDialogFactory *factory,
                       GimpContext       *context,
                       GimpUIManager     *ui_manager,
                       gint               view_size)
{
  return image_new_dialog_new (context);
}

GtkWidget *
dialogs_file_open_new (GimpDialogFactory *factory,
                       GimpContext       *context,
                       GimpUIManager     *ui_manager,
                       gint               view_size)
{
  return file_open_dialog_new (context->ammoos);
}

GtkWidget *
dialogs_file_open_location_new (GimpDialogFactory *factory,
                                GimpContext       *context,
                                GimpUIManager     *ui_manager,
                                gint               view_size)
{
  return file_open_location_dialog_new (context->ammoos);
}

GtkWidget *
dialogs_file_save_new (GimpDialogFactory *factory,
                       GimpContext       *context,
                       GimpUIManager     *ui_manager,
                       gint               view_size)
{
  return file_save_dialog_new (context->ammoos, FALSE);
}

GtkWidget *
dialogs_file_export_new (GimpDialogFactory *factory,
                         GimpContext       *context,
                         GimpUIManager     *ui_manager,
                         gint               view_size)
{
  return file_save_dialog_new (context->ammoos, TRUE);
}

GtkWidget *
dialogs_preferences_get (GimpDialogFactory *factory,
                         GimpContext       *context,
                         GimpUIManager     *ui_manager,
                         gint               view_size)
{
  return preferences_dialog_create (context->ammoos);
}

GtkWidget *
dialogs_extensions_get (GimpDialogFactory *factory,
                        GimpContext       *context,
                        GimpUIManager     *ui_manager,
                        gint               view_size)
{
  return extensions_dialog_new (context->ammoos);
}

GtkWidget *
dialogs_keyboard_shortcuts_get (GimpDialogFactory *factory,
                                GimpContext       *context,
                                GimpUIManager     *ui_manager,
                                gint               view_size)
{
  return keyboard_shortcuts_dialog_new (context->ammoos);
}

GtkWidget *
dialogs_input_devices_get (GimpDialogFactory *factory,
                           GimpContext       *context,
                           GimpUIManager     *ui_manager,
                           gint               view_size)
{
  return input_devices_dialog_new (context->ammoos);
}

GtkWidget *
dialogs_module_get (GimpDialogFactory *factory,
                    GimpContext       *context,
                    GimpUIManager     *ui_manager,
                    gint               view_size)
{
  return module_dialog_new (context->ammoos);
}

GtkWidget *
dialogs_palette_import_get (GimpDialogFactory *factory,
                            GimpContext       *context,
                            GimpUIManager     *ui_manager,
                            gint               view_size)
{
  return palette_import_dialog_new (context);
}

GtkWidget *
dialogs_tips_get (GimpDialogFactory *factory,
                  GimpContext       *context,
                  GimpUIManager     *ui_manager,
                  gint               view_size)
{
  return tips_dialog_create (context->ammoos);
}

GtkWidget *
dialogs_welcome_get (GimpDialogFactory *factory,
                     GimpContext       *context,
                     GimpUIManager     *ui_manager,
                     gint               view_size)
{
  return welcome_dialog_create (context->ammoos, TRUE);
}

GtkWidget *
dialogs_about_get (GimpDialogFactory *factory,
                   GimpContext       *context,
                   GimpUIManager     *ui_manager,
                   gint               view_size)
{
  return about_dialog_create (context->ammoos, context->ammoos->edit_config);
}

GtkWidget *
dialogs_action_search_get (GimpDialogFactory *factory,
                           GimpContext       *context,
                           GimpUIManager     *ui_manager,
                           gint               view_size)
{
  return action_search_dialog_create (context->ammoos);
}

GtkWidget *
dialogs_error_get (GimpDialogFactory *factory,
                   GimpContext       *context,
                   GimpUIManager     *ui_manager,
                   gint               view_size)
{
  return gimp_error_dialog_new (_("AmmoOS Image Message"));
}

GtkWidget *
dialogs_critical_get (GimpDialogFactory *factory,
                      GimpContext       *context,
                      GimpUIManager     *ui_manager,
                      gint               view_size)
{
  return gimp_critical_dialog_new (_("AmmoOS Image Debug"),
                                   context->ammoos->config->last_known_release,
                                   context->ammoos->config->last_release_timestamp);
}

GtkWidget *
dialogs_close_all_get (GimpDialogFactory *factory,
                       GimpContext       *context,
                       GimpUIManager     *ui_manager,
                       gint               view_size)
{
  return close_all_dialog_new (context->ammoos);
}

GtkWidget *
dialogs_quit_get (GimpDialogFactory *factory,
                  GimpContext       *context,
                  GimpUIManager     *ui_manager,
                  gint               view_size)
{
  return quit_dialog_new (context->ammoos);
}


/***********/
/*  docks  */
/***********/

GtkWidget *
dialogs_toolbox_new (GimpDialogFactory *factory,
                     GimpContext       *context,
                     GimpUIManager     *ui_manager,
                     gint               view_size)
{
  return gimp_toolbox_new (factory,
                           context,
                           ui_manager);
}

GtkWidget *
dialogs_toolbox_dock_window_new (GimpDialogFactory *factory,
                                 GimpContext       *context,
                                 GimpUIManager     *ui_manager,
                                 gint               view_size)
{
  static gint  role_serial = 1;
  GtkWidget   *dock;
  gchar       *role;

  role = g_strdup_printf ("ammoos-toolbox-%d", role_serial++);
  dock = gimp_dock_window_new (role,
                               "<Toolbox>",
                               TRUE,
                               factory,
                               context);
  g_free (role);

  return dock;
}

GtkWidget *
dialogs_dock_new (GimpDialogFactory *factory,
                  GimpContext       *context,
                  GimpUIManager     *ui_manager,
                  gint               view_size)
{
  return gimp_menu_dock_new ();
}

GtkWidget *
dialogs_dock_window_new (GimpDialogFactory *factory,
                         GimpContext       *context,
                         GimpUIManager     *ui_manager,
                         gint               view_size)
{
  static gint  role_serial = 1;
  GtkWidget   *dock;
  gchar       *role;

  role = g_strdup_printf ("ammoos-dock-%d", role_serial++);
  dock = gimp_dock_window_new (role,
                               "<Dock>",
                               FALSE,
                               factory,
                               context);
  g_free (role);

  return dock;
}


/***************/
/*  dockables  */
/***************/

/*****  singleton dialogs  *****/

GtkWidget *
dialogs_tool_options_new (GimpDialogFactory *factory,
                          GimpContext       *context,
                          GimpUIManager     *ui_manager,
                          gint               view_size)
{
  return gimp_tool_options_editor_new (context->ammoos,
                                       menus_get_global_menu_factory (context->ammoos));
}

GtkWidget *
dialogs_device_status_new (GimpDialogFactory *factory,
                           GimpContext       *context,
                           GimpUIManager     *ui_manager,
                           gint               view_size)
{
  return gimp_device_status_new (context->ammoos);
}

GtkWidget *
dialogs_error_console_new (GimpDialogFactory *factory,
                           GimpContext       *context,
                           GimpUIManager     *ui_manager,
                           gint               view_size)
{
  return gimp_error_console_new (context->ammoos,
                                 menus_get_global_menu_factory (context->ammoos));
}

GtkWidget *
dialogs_cursor_view_new (GimpDialogFactory *factory,
                         GimpContext       *context,
                         GimpUIManager     *ui_manager,
                         gint               view_size)
{
  return gimp_cursor_view_new (context->ammoos,
                               menus_get_global_menu_factory (context->ammoos));
}

GtkWidget *
dialogs_dashboard_new (GimpDialogFactory *factory,
                       GimpContext       *context,
                       GimpUIManager     *ui_manager,
                       gint               view_size)
{
  return gimp_dashboard_new (context->ammoos,
                             menus_get_global_menu_factory (context->ammoos));
}


/*****  list views  *****/

GtkWidget *
dialogs_image_list_view_new (GimpDialogFactory *factory,
                             GimpContext       *context,
                             GimpUIManager     *ui_manager,
                             gint               view_size)
{
  return gimp_image_view_new (GIMP_VIEW_TYPE_LIST,
                              context->ammoos->images,
                              context,
                              view_size, 1,
                              menus_get_global_menu_factory (context->ammoos));
}

GtkWidget *
dialogs_brush_list_view_new (GimpDialogFactory *factory,
                             GimpContext       *context,
                             GimpUIManager     *ui_manager,
                             gint               view_size)
{
  return gimp_brush_factory_view_new (GIMP_VIEW_TYPE_LIST,
                                      context->ammoos->brush_factory,
                                      context,
                                      TRUE,
                                      view_size, 1,
                                      menus_get_global_menu_factory (context->ammoos));
}

GtkWidget *
dialogs_dynamics_list_view_new (GimpDialogFactory *factory,
                                GimpContext       *context,
                                GimpUIManager     *ui_manager,
                                gint               view_size)
{
  return gimp_dynamics_factory_view_new (GIMP_VIEW_TYPE_LIST,
                                         context->ammoos->dynamics_factory,
                                         context,
                                         view_size, 0,
                                         menus_get_global_menu_factory (context->ammoos));
}

GtkWidget *
dialogs_mypaint_brush_list_view_new (GimpDialogFactory *factory,
                                     GimpContext       *context,
                                     GimpUIManager     *ui_manager,
                                     gint               view_size)
{
  return gimp_data_factory_view_new (GIMP_VIEW_TYPE_LIST,
                                     context->ammoos->mybrush_factory,
                                     context,
                                     view_size, 0,
                                     menus_get_global_menu_factory (context->ammoos),
                                     "<MyPaintBrushes>",
                                     "/mypaint-brushes-popup",
                                     "mypaint-brushes");
}

GtkWidget *
dialogs_pattern_list_view_new (GimpDialogFactory *factory,
                               GimpContext       *context,
                               GimpUIManager     *ui_manager,
                               gint               view_size)
{
  return gimp_pattern_factory_view_new (GIMP_VIEW_TYPE_LIST,
                                        context->ammoos->pattern_factory,
                                        context,
                                        view_size, 1,
                                        menus_get_global_menu_factory (context->ammoos));
}

GtkWidget *
dialogs_gradient_list_view_new (GimpDialogFactory *factory,
                                GimpContext       *context,
                                GimpUIManager     *ui_manager,
                                gint               view_size)
{
  return gimp_data_factory_view_new (GIMP_VIEW_TYPE_LIST,
                                     context->ammoos->gradient_factory,
                                     context,
                                     view_size, 1,
                                     menus_get_global_menu_factory (context->ammoos),
                                     "<Gradients>",
                                     "/gradients-popup",
                                     "gradients");
}

GtkWidget *
dialogs_palette_list_view_new (GimpDialogFactory *factory,
                               GimpContext       *context,
                               GimpUIManager     *ui_manager,
                               gint               view_size)
{
  return gimp_data_factory_view_new (GIMP_VIEW_TYPE_LIST,
                                     context->ammoos->palette_factory,
                                     context,
                                     view_size, 1,
                                     menus_get_global_menu_factory (context->ammoos),
                                     "<Palettes>",
                                     "/palettes-popup",
                                     "palettes");
}

GtkWidget *
dialogs_font_list_view_new (GimpDialogFactory *factory,
                            GimpContext       *context,
                            GimpUIManager     *ui_manager,
                            gint               view_size)
{
  return gimp_font_factory_view_new (GIMP_VIEW_TYPE_LIST,
                                     context->ammoos->font_factory,
                                     context,
                                     view_size, 1,
                                     menus_get_global_menu_factory (context->ammoos));
}

GtkWidget *
dialogs_buffer_list_view_new (GimpDialogFactory *factory,
                              GimpContext       *context,
                              GimpUIManager     *ui_manager,
                              gint               view_size)
{
  return gimp_buffer_view_new (GIMP_VIEW_TYPE_LIST,
                               context->ammoos->named_buffers,
                               context,
                               view_size, 1,
                               menus_get_global_menu_factory (context->ammoos));
}

GtkWidget *
dialogs_tool_preset_list_view_new (GimpDialogFactory *factory,
                                   GimpContext       *context,
                                   GimpUIManager     *ui_manager,
                                   gint               view_size)
{
  return gimp_tool_preset_factory_view_new (GIMP_VIEW_TYPE_LIST,
                                            context->ammoos->tool_preset_factory,
                                            context,
                                            view_size, 0,
                                            menus_get_global_menu_factory (context->ammoos));
}

GtkWidget *
dialogs_document_list_view_new (GimpDialogFactory *factory,
                                GimpContext       *context,
                                GimpUIManager     *ui_manager,
                                gint               view_size)
{
  return gimp_document_view_new (GIMP_VIEW_TYPE_LIST,
                                 context->ammoos->documents,
                                 context,
                                 view_size, 0,
                                 menus_get_global_menu_factory (context->ammoos));
}

GtkWidget *
dialogs_template_list_view_new (GimpDialogFactory *factory,
                                GimpContext       *context,
                                GimpUIManager     *ui_manager,
                                gint               view_size)
{
  return gimp_template_view_new (GIMP_VIEW_TYPE_LIST,
                                 context->ammoos->templates,
                                 context,
                                 view_size, 0,
                                 menus_get_global_menu_factory (context->ammoos));
}


/*****  grid views  *****/

GtkWidget *
dialogs_image_grid_view_new (GimpDialogFactory *factory,
                             GimpContext       *context,
                             GimpUIManager     *ui_manager,
                             gint               view_size)
{
  return gimp_image_view_new (GIMP_VIEW_TYPE_GRID,
                              context->ammoos->images,
                              context,
                              view_size, 1,
                              menus_get_global_menu_factory (context->ammoos));
}

GtkWidget *
dialogs_brush_grid_view_new (GimpDialogFactory *factory,
                             GimpContext       *context,
                             GimpUIManager     *ui_manager,
                             gint               view_size)
{
  return gimp_brush_factory_view_new (GIMP_VIEW_TYPE_GRID,
                                      context->ammoos->brush_factory,
                                      context,
                                      TRUE,
                                      view_size, 1,
                                      menus_get_global_menu_factory (context->ammoos));
}

GtkWidget *
dialogs_dynamics_grid_view_new (GimpDialogFactory *factory,
                                GimpContext       *context,
                                GimpUIManager     *ui_manager,
                                gint               view_size)
{
  return gimp_dynamics_factory_view_new (GIMP_VIEW_TYPE_GRID,
                                         context->ammoos->dynamics_factory,
                                         context,
                                         view_size, 1,
                                         menus_get_global_menu_factory (context->ammoos));
}

GtkWidget *
dialogs_mypaint_brush_grid_view_new (GimpDialogFactory *factory,
                                     GimpContext       *context,
                                     GimpUIManager     *ui_manager,
                                     gint               view_size)
{
  return gimp_data_factory_view_new (GIMP_VIEW_TYPE_GRID,
                                     context->ammoos->mybrush_factory,
                                     context,
                                     view_size, 1,
                                     menus_get_global_menu_factory (context->ammoos),
                                     "<MyPaintBrushes>",
                                     "/mypaint-brushes-popup",
                                     "mypaint-brushes");
}

GtkWidget *
dialogs_pattern_grid_view_new (GimpDialogFactory *factory,
                               GimpContext       *context,
                               GimpUIManager     *ui_manager,
                               gint               view_size)
{
  return gimp_pattern_factory_view_new (GIMP_VIEW_TYPE_GRID,
                                        context->ammoos->pattern_factory,
                                        context,
                                        view_size, 1,
                                        menus_get_global_menu_factory (context->ammoos));
}

GtkWidget *
dialogs_gradient_grid_view_new (GimpDialogFactory *factory,
                                GimpContext       *context,
                                GimpUIManager     *ui_manager,
                                gint               view_size)
{
  return gimp_data_factory_view_new (GIMP_VIEW_TYPE_GRID,
                                     context->ammoos->gradient_factory,
                                     context,
                                     view_size, 1,
                                     menus_get_global_menu_factory (context->ammoos),
                                     "<Gradients>",
                                     "/gradients-popup",
                                     "gradients");
}

GtkWidget *
dialogs_palette_grid_view_new (GimpDialogFactory *factory,
                               GimpContext       *context,
                               GimpUIManager     *ui_manager,
                               gint               view_size)
{
  return gimp_data_factory_view_new (GIMP_VIEW_TYPE_GRID,
                                     context->ammoos->palette_factory,
                                     context,
                                     view_size, 1,
                                     menus_get_global_menu_factory (context->ammoos),
                                     "<Palettes>",
                                     "/palettes-popup",
                                     "palettes");
}

GtkWidget *
dialogs_font_grid_view_new (GimpDialogFactory *factory,
                            GimpContext       *context,
                            GimpUIManager     *ui_manager,
                            gint               view_size)
{
  return gimp_font_factory_view_new (GIMP_VIEW_TYPE_GRID,
                                     context->ammoos->font_factory,
                                     context,
                                     view_size, 1,
                                     menus_get_global_menu_factory (context->ammoos));
}

GtkWidget *
dialogs_buffer_grid_view_new (GimpDialogFactory *factory,
                              GimpContext       *context,
                              GimpUIManager     *ui_manager,
                              gint               view_size)
{
  return gimp_buffer_view_new (GIMP_VIEW_TYPE_GRID,
                               context->ammoos->named_buffers,
                               context,
                               view_size, 1,
                               menus_get_global_menu_factory (context->ammoos));
}

GtkWidget *
dialogs_tool_preset_grid_view_new (GimpDialogFactory *factory,
                                   GimpContext       *context,
                                   GimpUIManager     *ui_manager,
                                   gint               view_size)
{
  return gimp_tool_preset_factory_view_new (GIMP_VIEW_TYPE_GRID,
                                            context->ammoos->tool_preset_factory,
                                            context,
                                            view_size, 1,
                                            menus_get_global_menu_factory (context->ammoos));
}

GtkWidget *
dialogs_document_grid_view_new (GimpDialogFactory *factory,
                                GimpContext       *context,
                                GimpUIManager     *ui_manager,
                                gint               view_size)
{
  return gimp_document_view_new (GIMP_VIEW_TYPE_GRID,
                                 context->ammoos->documents,
                                 context,
                                 view_size, 0,
                                 menus_get_global_menu_factory (context->ammoos));
}

GtkWidget *
dialogs_template_grid_view_new (GimpDialogFactory *factory,
                                GimpContext       *context,
                                GimpUIManager     *ui_manager,
                                gint               view_size)
{
  return gimp_template_view_new (GIMP_VIEW_TYPE_GRID,
                                 context->ammoos->templates,
                                 context,
                                 view_size, 0,
                                 menus_get_global_menu_factory (context->ammoos));
}


/*****  image related dialogs  *****/

GtkWidget *
dialogs_layer_list_view_new (GimpDialogFactory *factory,
                             GimpContext       *context,
                             GimpUIManager     *ui_manager,
                             gint               view_size)
{
  if (view_size < 1)
    view_size = context->ammoos->config->layer_preview_size;

  return gimp_item_tree_view_new (GIMP_TYPE_LAYER_TREE_VIEW,
                                  view_size, 2, TRUE,
                                  gimp_context_get_image (context),
                                  menus_get_global_menu_factory (context->ammoos),
                                  "<Layers>",
                                  "/layers-popup");
}

GtkWidget *
dialogs_channel_list_view_new (GimpDialogFactory *factory,
                               GimpContext       *context,
                               GimpUIManager     *ui_manager,
                               gint               view_size)
{
  if (view_size < 1)
    view_size = context->ammoos->config->layer_preview_size;

  return gimp_item_tree_view_new (GIMP_TYPE_CHANNEL_TREE_VIEW,
                                  view_size, 1, TRUE,
                                  gimp_context_get_image (context),
                                  menus_get_global_menu_factory (context->ammoos),
                                  "<Channels>",
                                  "/channels-popup");
}

GtkWidget *
dialogs_path_list_view_new (GimpDialogFactory *factory,
                            GimpContext       *context,
                            GimpUIManager     *ui_manager,
                            gint               view_size)
{
  if (view_size < 1)
    view_size = context->ammoos->config->layer_preview_size;

  return gimp_item_tree_view_new (GIMP_TYPE_PATH_TREE_VIEW,
                                  view_size, 1, TRUE,
                                  gimp_context_get_image (context),
                                  menus_get_global_menu_factory (context->ammoos),
                                  "<Paths>",
                                  "/paths-popup");
}

GtkWidget *
dialogs_colormap_editor_new (GimpDialogFactory *factory,
                             GimpContext       *context,
                             GimpUIManager     *ui_manager,
                             gint               view_size)
{
  return gimp_colormap_editor_new (menus_get_global_menu_factory (context->ammoos));
}

GtkWidget *
dialogs_histogram_editor_new (GimpDialogFactory *factory,
                              GimpContext       *context,
                              GimpUIManager     *ui_manager,
                              gint               view_size)
{
  return gimp_histogram_editor_new ();
}

GtkWidget *
dialogs_selection_editor_new (GimpDialogFactory *factory,
                              GimpContext       *context,
                              GimpUIManager     *ui_manager,
                              gint               view_size)
{
  return gimp_selection_editor_new (menus_get_global_menu_factory (context->ammoos));
}

GtkWidget *
dialogs_symmetry_editor_new (GimpDialogFactory *factory,
                             GimpContext       *context,
                             GimpUIManager     *ui_manager,
                             gint               view_size)
{
  return gimp_symmetry_editor_new (menus_get_global_menu_factory (context->ammoos));
}

GtkWidget *
dialogs_undo_editor_new (GimpDialogFactory *factory,
                         GimpContext       *context,
                         GimpUIManager     *ui_manager,
                         gint               view_size)
{
  return gimp_undo_editor_new (context->ammoos->config,
                               menus_get_global_menu_factory (context->ammoos));
}

GtkWidget *
dialogs_sample_point_editor_new (GimpDialogFactory *factory,
                                 GimpContext       *context,
                                 GimpUIManager     *ui_manager,
                                 gint               view_size)
{
  return gimp_sample_point_editor_new (menus_get_global_menu_factory (context->ammoos));
}


/*****  display related dialogs  *****/

GtkWidget *
dialogs_navigation_editor_new (GimpDialogFactory *factory,
                               GimpContext       *context,
                               GimpUIManager     *ui_manager,
                               gint               view_size)
{
  return gimp_navigation_editor_new (menus_get_global_menu_factory (context->ammoos));
}


/*****  misc dockables  *****/

GtkWidget *
dialogs_color_editor_new (GimpDialogFactory *factory,
                          GimpContext       *context,
                          GimpUIManager     *ui_manager,
                          gint               view_size)
{
  return gimp_color_editor_new (context);
}


/*************/
/*  editors  */
/*************/

GtkWidget *
dialogs_brush_editor_get (GimpDialogFactory *factory,
                          GimpContext       *context,
                          GimpUIManager     *ui_manager,
                          gint               view_size)
{
  return gimp_brush_editor_new (context,
                                menus_get_global_menu_factory (context->ammoos));
}

GtkWidget *
dialogs_dynamics_editor_get (GimpDialogFactory *factory,
                             GimpContext       *context,
                             GimpUIManager     *ui_manager,
                             gint               view_size)
{
  return gimp_dynamics_editor_new (context,
                                   menus_get_global_menu_factory (context->ammoos));
}

GtkWidget *
dialogs_gradient_editor_get (GimpDialogFactory *factory,
                             GimpContext       *context,
                             GimpUIManager     *ui_manager,
                             gint               view_size)
{
  return gimp_gradient_editor_new (context,
                                   menus_get_global_menu_factory (context->ammoos));
}

GtkWidget *
dialogs_palette_editor_get (GimpDialogFactory *factory,
                            GimpContext       *context,
                            GimpUIManager     *ui_manager,
                            gint               view_size)
{
  return gimp_palette_editor_new (context,
                                  menus_get_global_menu_factory (context->ammoos));
}

GtkWidget *
dialogs_tool_preset_editor_get (GimpDialogFactory *factory,
                                GimpContext       *context,
                                GimpUIManager     *ui_manager,
                                gint               view_size)
{
  return gimp_tool_preset_editor_new (context,
                                      menus_get_global_menu_factory (context->ammoos));
}

/* --- dialogs.c --- */
/* AmmoOS Image - The AmmoOS Field Image Research
 * Copyright (C) 1995 Spencer Kimball and Peter Mattis
 *
 * dialogs.c
 * Copyright (C) 2010 Martin Nordholts <martinn@src.gnome.org>
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

#include "libgimpbase/gimpbase.h"
#include "libgimpconfig/gimpconfig.h"
#include "libgimpwidgets/gimpwidgets.h"

#include "dialogs-types.h"

#include "config/gimpguiconfig.h"

#include "display/gimpdisplay.h"
#include "display/gimpdisplayshell.h"

#include "core/ammoos.h"
#include "core/gimpcontext.h"
#include "core/gimplist.h"

#include "widgets/gimpdialogfactory.h"
#include "widgets/gimpdockwindow.h"
#include "widgets/gimphelp-ids.h"
#include "widgets/gimpmenufactory.h"
#include "widgets/gimpsessioninfo.h"
#include "widgets/gimpsessioninfo-aux.h"
#include "widgets/gimpsessionmanaged.h"
#include "widgets/gimptoolbox.h"

#include "dialogs.h"
#include "dialogs-constructors.h"

#include "ammoos-log.h"

#include "ammoos-intl.h"


GimpContainer *global_recent_docks = NULL;


#define FOREIGN(id, singleton, remember_size) \
  { id                     /* identifier       */, \
    NULL                   /* name             */, \
    NULL                   /* blurb            */, \
    NULL                   /* icon_name        */, \
    NULL                   /* help_id          */, \
    NULL                   /* new_func         */, \
    dialogs_restore_dialog /* restore_func     */, \
    0                      /* view_size        */, \
    singleton              /* singleton        */, \
    TRUE                   /* session_managed  */, \
    remember_size          /* remember_size    */, \
    FALSE                  /* remember_if_open */, \
    TRUE                   /* hideable         */, \
    FALSE                  /* image_window     */, \
    FALSE                  /* dockable         */}

#define IMAGE_WINDOW(id, singleton, remember_size) \
  { id                     /* identifier       */, \
    NULL                   /* name             */, \
    NULL                   /* blurb            */, \
    NULL                   /* icon_name        */, \
    NULL                   /* help_id          */, \
    NULL                   /* new_func         */, \
    dialogs_restore_window /* restore_func     */, \
    0                      /* view_size        */, \
    singleton              /* singleton        */, \
    TRUE                   /* session_managed  */, \
    remember_size          /* remember_size    */, \
    TRUE                   /* remember_if_open */, \
    FALSE                  /* hideable         */, \
    TRUE                   /* image_window     */, \
    FALSE                  /* dockable         */}

#define TOPLEVEL(id, new_func, singleton, session_managed, remember_size) \
  { id                     /* identifier       */, \
    NULL                   /* name             */, \
    NULL                   /* blurb            */, \
    NULL                   /* icon_name        */, \
    NULL                   /* help_id          */, \
    new_func               /* new_func         */, \
    dialogs_restore_dialog /* restore_func     */, \
    0                      /* view_size        */, \
    singleton              /* singleton        */, \
    session_managed        /* session_managed  */, \
    remember_size          /* remember_size    */, \
    FALSE                  /* remember_if_open */, \
    TRUE                   /* hideable         */, \
    FALSE                  /* image_window     */, \
    FALSE                  /* dockable         */}

#define DOCKABLE(id, name, blurb, icon_name, help_id, new_func, view_size, singleton) \
  { id                     /* identifier       */, \
    name                   /* name             */, \
    blurb                  /* blurb            */, \
    icon_name              /* icon_name        */, \
    help_id                /* help_id          */, \
    new_func               /* new_func         */, \
    NULL                   /* restore_func     */, \
    view_size              /* view_size        */, \
    singleton              /* singleton        */, \
    FALSE                  /* session_managed  */, \
    FALSE                  /* remember_size    */, \
    TRUE                   /* remember_if_open */, \
    TRUE                   /* hideable         */, \
    FALSE                  /* image_window     */, \
    TRUE                   /* dockable         */}

#define DOCK(id, new_func) \
  { id                     /* identifier       */, \
    NULL                   /* name             */, \
    NULL                   /* blurb            */, \
    NULL                   /* icon_name        */, \
    NULL                   /* help_id          */, \
    new_func               /* new_func         */, \
    dialogs_restore_dialog /* restore_func     */, \
    0                      /* view_size        */, \
    FALSE                  /* singleton        */, \
    FALSE                  /* session_managed  */, \
    FALSE                  /* remember_size    */, \
    FALSE                  /* remember_if_open */, \
    TRUE                   /* hideable         */, \
    FALSE                  /* image_window     */, \
    FALSE                  /* dockable         */}

#define DOCK_WINDOW(id, new_func) \
  { id                     /* identifier       */, \
    NULL                   /* name             */, \
    NULL                   /* blurb            */, \
    NULL                   /* icon_name        */, \
    NULL                   /* help_id          */, \
    new_func               /* new_func         */, \
    dialogs_restore_dialog /* restore_func     */, \
    0                      /* view_size        */, \
    FALSE                  /* singleton        */, \
    TRUE                   /* session_managed  */, \
    TRUE                   /* remember_size    */, \
    TRUE                   /* remember_if_open */, \
    TRUE                   /* hideable         */, \
    FALSE                  /* image_window     */, \
    FALSE                  /* dockable         */}

#define LISTGRID(id, new_func, name, blurb, icon_name, help_id, view_size) \
  { "ammoos-"#id"-list"             /* identifier       */,  \
    name                          /* name             */,  \
    blurb                         /* blurb            */,  \
    icon_name                     /* icon_name        */,  \
    help_id                       /* help_id          */,  \
    dialogs_##new_func##_list_view_new /* new_func         */,  \
    NULL                          /* restore_func     */,  \
    view_size                     /* view_size        */,  \
    FALSE                         /* singleton        */,  \
    FALSE                         /* session_managed  */,  \
    FALSE                         /* remember_size    */,  \
    TRUE                          /* remember_if_open */,  \
    TRUE                          /* hideable         */,  \
    FALSE                         /* image_window     */,  \
    TRUE                          /* dockable         */}, \
  { "ammoos-"#id"-grid"             /* identifier       */,  \
    name                          /* name             */,  \
    blurb                         /* blurb            */,  \
    icon_name                     /* icon_name        */,  \
    help_id                       /* help_id          */,  \
    dialogs_##new_func##_grid_view_new /* new_func         */,  \
    NULL                          /* restore_func     */,  \
    view_size                     /* view_size        */,  \
    FALSE                         /* singleton        */,  \
    FALSE                         /* session_managed  */,  \
    FALSE                         /* remember_size    */,  \
    TRUE                          /* remember_if_open */,  \
    TRUE                          /* hideable         */,  \
    FALSE                         /* image_window     */,  \
    TRUE                          /* dockable         */}

#define LIST(id, new_func, name, blurb, icon_name, help_id, view_size) \
  { "ammoos-"#id"-list"                   /* identifier       */, \
    name                                /* name             */, \
    blurb                               /* blurb            */, \
    icon_name                            /* icon_name         */, \
    help_id                             /* help_id          */, \
    dialogs_##new_func##_list_view_new  /* new_func         */, \
    NULL                                /* restore_func     */, \
    view_size                           /* view_size        */, \
    FALSE                               /* singleton        */, \
    FALSE                               /* session_managed  */, \
    FALSE                               /* remember_size    */, \
    TRUE                                /* remember_if_open */, \
    TRUE                                /* hideable         */, \
    FALSE                               /* image_window     */, \
    TRUE                                /* dockable         */}


static GtkWidget * dialogs_restore_dialog (GimpDialogFactory *factory,
                                           GdkMonitor        *monitor,
                                           GimpSessionInfo   *info);
static GtkWidget * dialogs_restore_window (GimpDialogFactory *factory,
                                           GdkMonitor        *monitor,
                                           GimpSessionInfo   *info);


static const GimpDialogFactoryEntry entries[] =
{
  /*  foreign toplevels without constructor  */
  FOREIGN ("ammoos-brightness-contrast-tool-dialog", TRUE,  FALSE),
  FOREIGN ("ammoos-color-balance-tool-dialog",       TRUE,  FALSE),
  FOREIGN ("ammoos-color-picker-tool-dialog",        TRUE,  TRUE),
  FOREIGN ("ammoos-colorize-tool-dialog",            TRUE,  FALSE),
  FOREIGN ("ammoos-crop-tool-dialog",                TRUE,  FALSE),
  FOREIGN ("ammoos-curves-tool-dialog",              TRUE,  TRUE),
  FOREIGN ("ammoos-desaturate-tool-dialog",          TRUE,  FALSE),
  FOREIGN ("ammoos-foreground-select-tool-dialog",   TRUE,  FALSE),
  FOREIGN ("ammoos-gegl-tool-dialog",                TRUE,  FALSE),
  FOREIGN ("ammoos-gradient-tool-dialog",            TRUE,  FALSE),
  FOREIGN ("ammoos-hue-saturation-tool-dialog",      TRUE,  FALSE),
  FOREIGN ("ammoos-levels-tool-dialog",              TRUE,  TRUE),
  FOREIGN ("ammoos-measure-tool-dialog",             TRUE,  FALSE),
  FOREIGN ("ammoos-offset-tool-dialog",              TRUE,  FALSE),
  FOREIGN ("ammoos-operation-tool-dialog",           TRUE,  FALSE),
  FOREIGN ("ammoos-posterize-tool-dialog",           TRUE,  FALSE),
  FOREIGN ("ammoos-rotate-tool-dialog",              TRUE,  FALSE),
  FOREIGN ("ammoos-scale-tool-dialog",               TRUE,  FALSE),
  FOREIGN ("ammoos-shear-tool-dialog",               TRUE,  FALSE),
  FOREIGN ("ammoos-text-tool-dialog",                TRUE,  TRUE),
  FOREIGN ("ammoos-threshold-tool-dialog",           TRUE,  FALSE),
  FOREIGN ("ammoos-transform-3d-tool-dialog",        TRUE,  FALSE),
  FOREIGN ("ammoos-perspective-tool-dialog",         TRUE,  FALSE),
  FOREIGN ("ammoos-unified-transform-tool-dialog",   TRUE,  FALSE),
  FOREIGN ("ammoos-handle-transform-tool-dialog",    TRUE,  FALSE),

  FOREIGN ("ammoos-toolbox-color-dialog",            TRUE,  FALSE),
  FOREIGN ("ammoos-gradient-editor-color-dialog",    TRUE,  FALSE),
  FOREIGN ("ammoos-palette-editor-color-dialog",     TRUE,  FALSE),
  FOREIGN ("ammoos-colormap-editor-color-dialog",    TRUE,  FALSE),
  FOREIGN ("ammoos-colormap-selection-color-dialog", TRUE,  FALSE),

  FOREIGN ("ammoos-controller-editor-dialog",        FALSE, TRUE),
  FOREIGN ("ammoos-controller-action-dialog",        FALSE, TRUE),
  FOREIGN ("ammoos-pad-action-dialog",               FALSE, TRUE),

  /*  ordinary toplevels  */
  TOPLEVEL ("ammoos-image-new-dialog",
            dialogs_image_new_new,          FALSE, TRUE, FALSE),
  TOPLEVEL ("ammoos-file-open-dialog",
            dialogs_file_open_new,          TRUE,  TRUE, TRUE),
  TOPLEVEL ("ammoos-file-open-location-dialog",
            dialogs_file_open_location_new, FALSE, TRUE, FALSE),
  TOPLEVEL ("ammoos-file-save-dialog",
            dialogs_file_save_new,          FALSE, TRUE, TRUE),
  TOPLEVEL ("ammoos-file-export-dialog",
            dialogs_file_export_new,        FALSE, TRUE, TRUE),

  /*  singleton toplevels  */
  TOPLEVEL ("ammoos-preferences-dialog",
            dialogs_preferences_get,        TRUE, TRUE,  TRUE),
  TOPLEVEL ("ammoos-input-devices-dialog",
            dialogs_input_devices_get,      TRUE, TRUE,  FALSE),
  TOPLEVEL ("ammoos-keyboard-shortcuts-dialog",
            dialogs_keyboard_shortcuts_get, TRUE, TRUE,  TRUE),
  TOPLEVEL ("ammoos-module-dialog",
            dialogs_module_get,             TRUE, TRUE,  TRUE),
  TOPLEVEL ("ammoos-palette-import-dialog",
            dialogs_palette_import_get,     TRUE, TRUE,  TRUE),
  TOPLEVEL ("ammoos-tips-dialog",
            dialogs_tips_get,               TRUE, FALSE, FALSE),
  TOPLEVEL ("ammoos-welcome-dialog",
            dialogs_welcome_get,            TRUE, FALSE, FALSE),
  TOPLEVEL ("ammoos-about-dialog",
            dialogs_about_get,              TRUE, FALSE, FALSE),
  TOPLEVEL ("ammoos-action-search-dialog",
            dialogs_action_search_get,      TRUE, TRUE,  TRUE),
  TOPLEVEL ("ammoos-error-dialog",
            dialogs_error_get,              TRUE, FALSE, FALSE),
  TOPLEVEL ("ammoos-critical-dialog",
            dialogs_critical_get,           TRUE, FALSE, FALSE),
  TOPLEVEL ("ammoos-close-all-dialog",
            dialogs_close_all_get,          TRUE, FALSE, FALSE),
  TOPLEVEL ("ammoos-quit-dialog",
            dialogs_quit_get,               TRUE, FALSE, FALSE),
  TOPLEVEL ("ammoos-extensions-dialog",
            dialogs_extensions_get,         TRUE, TRUE,  TRUE),

  /*  docks  */
  DOCK ("ammoos-dock",
        dialogs_dock_new),
  DOCK ("ammoos-toolbox",
        dialogs_toolbox_new),

  /*  dock windows  */
  DOCK_WINDOW ("ammoos-dock-window",
               dialogs_dock_window_new),
  DOCK_WINDOW ("ammoos-toolbox-window",
               dialogs_toolbox_dock_window_new),

  /*  singleton dockables  */
  DOCKABLE ("ammoos-tool-options",
            N_("Tool Options"), NULL, GIMP_ICON_DIALOG_TOOL_OPTIONS,
            GIMP_HELP_TOOL_OPTIONS_DIALOG,
            dialogs_tool_options_new, 0, TRUE),
  DOCKABLE ("ammoos-device-status",
            N_("Devices"), N_("Device Status"), GIMP_ICON_DIALOG_DEVICE_STATUS,
            GIMP_HELP_DEVICE_STATUS_DIALOG,
            dialogs_device_status_new, 0, TRUE),
  DOCKABLE ("ammoos-error-console",
            N_("Errors"), N_("Error Console"), GIMP_ICON_DIALOG_WARNING,
            GIMP_HELP_ERRORS_DIALOG,
            dialogs_error_console_new, 0, TRUE),
  DOCKABLE ("ammoos-cursor-view",
            N_("Pointer"), N_("Pointer Information"), GIMP_ICON_CURSOR,
            GIMP_HELP_POINTER_INFO_DIALOG,
            dialogs_cursor_view_new, 0, TRUE),
  DOCKABLE ("ammoos-dashboard",
            N_("Dashboard"), N_("Dashboard"), GIMP_ICON_DIALOG_DASHBOARD,
            GIMP_HELP_DASHBOARD_DIALOG,
            dialogs_dashboard_new, 0, TRUE),

  /*  list & grid views  */
  LISTGRID (image, image,
            N_("Images"), NULL, GIMP_ICON_DIALOG_IMAGES,
            GIMP_HELP_IMAGE_DIALOG, GIMP_VIEW_SIZE_MEDIUM),
  LISTGRID (brush, brush,
            N_("Brushes"), NULL, GIMP_ICON_BRUSH,
            GIMP_HELP_BRUSH_DIALOG, GIMP_VIEW_SIZE_MEDIUM),
  LISTGRID (dynamics, dynamics,
            N_("Paint Dynamics"), NULL, GIMP_ICON_DYNAMICS,
            GIMP_HELP_DYNAMICS_DIALOG, GIMP_VIEW_SIZE_MEDIUM),
  LISTGRID (mypaint-brush, mypaint_brush,
            N_("MyPaint Brushes"), NULL, GIMP_ICON_MYPAINT_BRUSH,
            GIMP_HELP_MYPAINT_BRUSH_DIALOG, GIMP_VIEW_SIZE_LARGE),
  LISTGRID (pattern, pattern,
            N_("Patterns"), NULL, GIMP_ICON_PATTERN,
            GIMP_HELP_PATTERN_DIALOG, GIMP_VIEW_SIZE_MEDIUM),
  LISTGRID (gradient, gradient,
            N_("Gradients"), NULL, GIMP_ICON_GRADIENT,
            GIMP_HELP_GRADIENT_DIALOG, GIMP_VIEW_SIZE_MEDIUM),
  LISTGRID (palette, palette,
            N_("Palettes"), NULL, GIMP_ICON_PALETTE,
            GIMP_HELP_PALETTE_DIALOG, GIMP_VIEW_SIZE_MEDIUM),
  LISTGRID (font, font,
            N_("Fonts"), NULL, GIMP_ICON_FONT,
            GIMP_HELP_FONT_DIALOG, GIMP_VIEW_SIZE_MEDIUM),
  LISTGRID (buffer, buffer,
            N_("Buffers"), NULL, GIMP_ICON_BUFFER,
            GIMP_HELP_BUFFER_DIALOG, GIMP_VIEW_SIZE_MEDIUM),
  LISTGRID (tool-preset, tool_preset,
            N_("Tool Presets"), NULL, GIMP_ICON_TOOL_PRESET,
            GIMP_HELP_TOOL_PRESET_DIALOG, GIMP_VIEW_SIZE_MEDIUM),
  LISTGRID (document, document,
            N_("History"), N_("Document History"), GIMP_ICON_DOCUMENT_OPEN_RECENT,
            GIMP_HELP_DOCUMENT_DIALOG, GIMP_VIEW_SIZE_LARGE),
  LISTGRID (template, template,
            N_("Templates"), N_("Image Templates"), GIMP_ICON_TEMPLATE,
            GIMP_HELP_TEMPLATE_DIALOG, GIMP_VIEW_SIZE_SMALL),

  /*  image related  */
  DOCKABLE ("ammoos-layer-list",
            N_("Layers"), NULL, GIMP_ICON_DIALOG_LAYERS,
            GIMP_HELP_LAYER_DIALOG,
            dialogs_layer_list_view_new, 0, FALSE),
  DOCKABLE ("ammoos-channel-list",
            N_("Channels"), NULL, GIMP_ICON_DIALOG_CHANNELS,
            GIMP_HELP_CHANNEL_DIALOG,
            dialogs_channel_list_view_new, 0, FALSE),
  DOCKABLE ("ammoos-path-list",
            N_("Paths"), NULL, GIMP_ICON_DIALOG_PATHS,
            GIMP_HELP_PATH_DIALOG,
            dialogs_path_list_view_new, 0, FALSE),
  DOCKABLE ("ammoos-indexed-palette",
            N_("Colormap"), NULL, GIMP_ICON_COLORMAP,
            GIMP_HELP_INDEXED_PALETTE_DIALOG,
            dialogs_colormap_editor_new, 0, FALSE),
  DOCKABLE ("ammoos-histogram-editor",
            N_("Histogram"), NULL, GIMP_ICON_HISTOGRAM,
            GIMP_HELP_HISTOGRAM_DIALOG,
            dialogs_histogram_editor_new, 0, FALSE),
  DOCKABLE ("ammoos-selection-editor",
            N_("Selection"), N_("Selection Editor"), GIMP_ICON_SELECTION,
            GIMP_HELP_SELECTION_DIALOG,
            dialogs_selection_editor_new, 0, FALSE),
  DOCKABLE ("ammoos-symmetry-editor",
            N_("Symmetry Painting"), NULL, GIMP_ICON_SYMMETRY,
            GIMP_HELP_SYMMETRY_DIALOG,
            dialogs_symmetry_editor_new, 0, FALSE),
  DOCKABLE ("ammoos-undo-history",
            N_("Undo"), N_("Undo History"), GIMP_ICON_DIALOG_UNDO_HISTORY,
            GIMP_HELP_UNDO_DIALOG,
            dialogs_undo_editor_new, 0, FALSE),
  DOCKABLE ("ammoos-sample-point-editor",
            N_("Sample Points"), N_("Sample Points"), GIMP_ICON_SAMPLE_POINT,
            GIMP_HELP_SAMPLE_POINT_DIALOG,
            dialogs_sample_point_editor_new, 0, FALSE),

  /*  display related  */
  DOCKABLE ("ammoos-navigation-view",
            N_("Navigation"), N_("Display Navigation"), GIMP_ICON_DIALOG_NAVIGATION,
            GIMP_HELP_NAVIGATION_DIALOG,
            dialogs_navigation_editor_new, 0, FALSE),

  /*  editors  */
  DOCKABLE ("ammoos-color-editor",
            N_("FG/BG"), N_("FG/BG Color"), GIMP_ICON_COLORS_DEFAULT,
            GIMP_HELP_COLOR_DIALOG,
            dialogs_color_editor_new, 0, FALSE),

  /*  singleton editors  */
  DOCKABLE ("ammoos-brush-editor",
            N_("Brush Editor"), NULL, GIMP_ICON_BRUSH,
            GIMP_HELP_BRUSH_EDITOR_DIALOG,
            dialogs_brush_editor_get, 0, TRUE),
  DOCKABLE ("ammoos-dynamics-editor",
            N_("Paint Dynamics Editor"), NULL, GIMP_ICON_DYNAMICS,
            GIMP_HELP_DYNAMICS_EDITOR_DIALOG,
            dialogs_dynamics_editor_get, 0, TRUE),
  DOCKABLE ("ammoos-gradient-editor",
            N_("Gradient Editor"), NULL, GIMP_ICON_GRADIENT,
            GIMP_HELP_GRADIENT_EDITOR_DIALOG,
            dialogs_gradient_editor_get, 0, TRUE),
  DOCKABLE ("ammoos-palette-editor",
            N_("Palette Editor"), NULL, GIMP_ICON_PALETTE,
            GIMP_HELP_PALETTE_EDITOR_DIALOG,
            dialogs_palette_editor_get, 0, TRUE),
  DOCKABLE ("ammoos-tool-preset-editor",
            N_("Tool Preset Editor"), NULL, GIMP_ICON_TOOL_PRESET,
            GIMP_HELP_TOOL_PRESET_EDITOR_DIALOG,
            dialogs_tool_preset_editor_get, 0, TRUE),

  /*  image windows  */
  IMAGE_WINDOW ("ammoos-empty-image-window",
                TRUE, TRUE),
  IMAGE_WINDOW ("ammoos-single-image-window",
                TRUE, TRUE)
};

/**
 * dialogs_restore_dialog:
 * @factory:
 * @screen:
 * @info:
 *
 * Creates a top level widget based on the given session info object
 * in which other widgets later can be be put, typically also restored
 * from the same session info object.
 *
 * Returns:
 **/
static GtkWidget *
dialogs_restore_dialog (GimpDialogFactory *factory,
                        GdkMonitor        *monitor,
                        GimpSessionInfo   *info)
{
  GtkWidget        *dialog;
  Gimp             *ammoos    = gimp_dialog_factory_get_context (factory)->ammoos;
  GimpCoreConfig   *config  = ammoos->config;
  GimpDisplay      *display = gimp_context_get_display (gimp_get_user_context (ammoos));
  GimpDisplayShell *shell   = gimp_display_get_shell (display);

  GIMP_LOG (DIALOG_FACTORY, "restoring toplevel \"%s\" (info %p)",
            gimp_session_info_get_factory_entry (info)->identifier,
            info);

  dialog =
    gimp_dialog_factory_dialog_new (factory, monitor,
                                    NULL /*ui_manager*/,
                                    GTK_WIDGET (gimp_display_shell_get_window (shell)),
                                    gimp_session_info_get_factory_entry (info)->identifier,
                                    gimp_session_info_get_factory_entry (info)->view_size,
                                    ! GIMP_GUI_CONFIG (config)->hide_docks);

  g_object_set_data (G_OBJECT (dialog), GIMP_DIALOG_VISIBILITY_KEY,
                     GINT_TO_POINTER (GIMP_GUI_CONFIG (config)->hide_docks ?
                                      GIMP_DIALOG_VISIBILITY_HIDDEN :
                                      GIMP_DIALOG_VISIBILITY_VISIBLE));

  return dialog;
}

/**
 * dialogs_restore_window:
 * @factory:
 * @monitor:
 * @info:
 *
 * "restores" the image window. We don't really restore anything since
 * the image window is created earlier, so we just look for and return
 * the already-created image window.
 *
 * Returns:
 **/
static GtkWidget *
dialogs_restore_window (GimpDialogFactory *factory,
                        GdkMonitor        *monitor,
                        GimpSessionInfo   *info)
{
  Gimp             *ammoos    = gimp_dialog_factory_get_context (factory)->ammoos;
  GimpDisplay      *display = GIMP_DISPLAY (gimp_get_empty_display (ammoos));
  GimpDisplayShell *shell   = gimp_display_get_shell (display);
  GtkWidget        *dialog;

  dialog = GTK_WIDGET (gimp_display_shell_get_window (shell));

  return dialog;
}


/*  public functions  */

void
dialogs_init (Gimp *ammoos)
{
  GimpDialogFactory *factory = NULL;
  gint               i       = 0;

  g_return_if_fail (GIMP_IS_GIMP (ammoos));

  factory = gimp_dialog_factory_new ("toplevel", gimp_get_user_context (ammoos));
  gimp_dialog_factory_set_singleton (factory);

  for (i = 0; i < G_N_ELEMENTS (entries); i++)
    gimp_dialog_factory_register_entry (factory,
                                        entries[i].identifier,
                                        entries[i].name ? gettext(entries[i].name) : NULL,
                                        entries[i].blurb ? gettext(entries[i].blurb) : NULL,
                                        entries[i].icon_name,
                                        entries[i].help_id,
                                        entries[i].new_func,
                                        entries[i].restore_func,
                                        entries[i].view_size,
                                        entries[i].singleton,
                                        entries[i].session_managed,
                                        entries[i].remember_size,
                                        entries[i].remember_if_open,
                                        entries[i].hideable,
                                        entries[i].image_window,
                                        entries[i].dockable);

  global_recent_docks = gimp_list_new (GIMP_TYPE_SESSION_INFO, FALSE);
}

void
dialogs_exit (Gimp *ammoos)
{
  g_return_if_fail (GIMP_IS_GIMP (ammoos));

  if (gimp_dialog_factory_get_singleton ())
    {
      /* run dispose manually so the factory destroys its dialogs, which
       * might in turn directly or indirectly ref the factory
       */
      g_object_run_dispose (G_OBJECT (gimp_dialog_factory_get_singleton ()));

      g_object_unref (gimp_dialog_factory_get_singleton ());
      gimp_dialog_factory_set_singleton (NULL);
    }

  g_clear_object (&global_recent_docks);
}

static void
dialogs_ensure_factory_entry_on_recent_dock (GimpSessionInfo *info)
{
  if (! gimp_session_info_get_factory_entry (info))
    {
      GimpDialogFactoryEntry *entry = NULL;

      /* The recent docks container only contains session infos for
       * dock windows
       */
      entry = gimp_dialog_factory_find_entry (gimp_dialog_factory_get_singleton (),
                                              "ammoos-dock-window");

      gimp_session_info_set_factory_entry (info, entry);
    }
}

static GFile *
dialogs_get_dockrc_file (void)
{
  const gchar *basename;

  basename = g_getenv ("GIMP_TESTING_DOCKRC_NAME");
  if (! basename)
    basename = "dockrc";

  return gimp_directory_file (basename, NULL);
}

void
dialogs_load_recent_docks (Gimp *ammoos)
{
  GFile  *file;
  GError *error = NULL;

  g_return_if_fail (GIMP_IS_GIMP (ammoos));

  file = dialogs_get_dockrc_file ();

  if (ammoos->be_verbose)
    g_print ("Parsing '%s'\n", gimp_file_get_utf8_name (file));

  if (! gimp_config_deserialize_file (GIMP_CONFIG (global_recent_docks),
                                      file,
                                      NULL, &error))
    {
      if (error->code != GIMP_CONFIG_ERROR_OPEN_ENOENT)
        gimp_message_literal (ammoos, NULL, GIMP_MESSAGE_ERROR, error->message);

      g_clear_error (&error);
    }

  g_object_unref (file);

  /* In AmmoOS Image 2.6 dockrc did not contain the factory entries for the
   * session infos, so set that up manually if needed
   */
  gimp_container_foreach (global_recent_docks,
                          (GFunc) dialogs_ensure_factory_entry_on_recent_dock,
                          NULL);

  gimp_list_reverse (GIMP_LIST (global_recent_docks));
}

void
dialogs_save_recent_docks (Gimp *ammoos)
{
  GFile  *file;
  GError *error = NULL;

  g_return_if_fail (GIMP_IS_GIMP (ammoos));

  file = dialogs_get_dockrc_file ();

  if (ammoos->be_verbose)
    g_print ("Writing '%s'\n", gimp_file_get_utf8_name (file));

  if (! gimp_config_serialize_to_file (GIMP_CONFIG (global_recent_docks),
                                       file,
                                       "recently closed docks",
                                       "end of recently closed docks",
                                       NULL, &error))
    {
      gimp_message_literal (ammoos, NULL, GIMP_MESSAGE_ERROR, error->message);
      g_clear_error (&error);
    }

  g_object_unref (file);
}

GtkWidget *
dialogs_get_toolbox (void)
{
  GList *list;

  g_return_val_if_fail (GIMP_IS_DIALOG_FACTORY (gimp_dialog_factory_get_singleton ()), NULL);

  for (list = gimp_dialog_factory_get_open_dialogs (gimp_dialog_factory_get_singleton ());
       list;
       list = g_list_next (list))
    {
      if (GIMP_IS_DOCK_WINDOW (list->data) &&
          gimp_dock_window_has_toolbox (list->data))
        return list->data;
    }

  return NULL;
}

GtkWidget *
dialogs_get_dialog (GObject     *attach_object,
                    const gchar *attach_key)
{
  g_return_val_if_fail (G_IS_OBJECT (attach_object), NULL);
  g_return_val_if_fail (attach_key != NULL, NULL);

  return g_object_get_data (attach_object, attach_key);
}

void
dialogs_attach_dialog (GObject     *attach_object,
                       const gchar *attach_key,
                       GtkWidget   *dialog)
{
  g_return_if_fail (G_IS_OBJECT (attach_object));
  g_return_if_fail (attach_key != NULL);
  g_return_if_fail (GTK_IS_WIDGET (dialog));

  g_object_set_data (attach_object, attach_key, dialog);
  g_object_set_data (G_OBJECT (dialog), "ammoos-dialogs-attach-key",
                     (gpointer) attach_key);

  g_signal_connect_object (dialog, "destroy",
                           G_CALLBACK (dialogs_detach_dialog),
                           attach_object,
                           G_CONNECT_SWAPPED);
}

void
dialogs_detach_dialog (GObject   *attach_object,
                       GtkWidget *dialog)
{
  const gchar *attach_key;

  g_return_if_fail (G_IS_OBJECT (attach_object));
  g_return_if_fail (GTK_IS_WIDGET (dialog));

  attach_key = g_object_get_data (G_OBJECT (dialog),
                                  "ammoos-dialogs-attach-key");

  g_return_if_fail (attach_key != NULL);

  g_object_set_data (attach_object, attach_key, NULL);

  g_signal_handlers_disconnect_by_func (dialog,
                                        dialogs_detach_dialog,
                                        attach_object);
}

void
dialogs_destroy_dialog (GObject     *attach_object,
                        const gchar *attach_key)
{
  GtkWidget *dialog;

  g_return_if_fail (G_IS_OBJECT (attach_object));
  g_return_if_fail (attach_key != NULL);

  dialog = g_object_get_data (attach_object, attach_key);

  if (dialog)
    gtk_widget_destroy (dialog);
}

GtkNativeDialog *
dialogs_get_native_dialog (GObject     *attach_object,
                           const gchar *attach_key)
{
  g_return_val_if_fail (G_IS_OBJECT (attach_object), NULL);
  g_return_val_if_fail (attach_key != NULL, NULL);

  return g_object_get_data (attach_object, attach_key);
}

void
dialogs_attach_native_dialog (GObject         *attach_object,
                              const gchar     *attach_key,
                              GtkNativeDialog *dialog)
{
  g_return_if_fail (G_IS_OBJECT (attach_object));
  g_return_if_fail (attach_key != NULL);
  g_return_if_fail (GTK_IS_NATIVE_DIALOG (dialog));

  g_object_set_data (attach_object, attach_key, dialog);
  g_object_set_data (G_OBJECT (dialog), "ammoos-dialogs-attach-key",
                     (gpointer) attach_key);
}

void
dialogs_detach_native_dialog (GObject         *attach_object,
                              GtkNativeDialog *dialog)
{
  const gchar *attach_key;

  g_return_if_fail (G_IS_OBJECT (attach_object));
  g_return_if_fail (GTK_IS_NATIVE_DIALOG (dialog));

  attach_key = g_object_get_data (G_OBJECT (dialog),
                                  "ammoos-dialogs-attach-key");

  g_return_if_fail (attach_key != NULL);

  g_object_set_data (attach_object, attach_key, NULL);

  g_signal_handlers_disconnect_by_func (dialog,
                                        dialogs_detach_dialog,
                                        attach_object);
}

void
dialogs_destroy_native_dialog (GObject     *attach_object,
                               const gchar *attach_key)
{
  GtkNativeDialog *dialog;

  g_return_if_fail (G_IS_OBJECT (attach_object));
  g_return_if_fail (attach_key != NULL);

  dialog = g_object_get_data (attach_object, attach_key);

  if (dialog)
    gtk_native_dialog_destroy (dialog);
}

/* --- extensions-dialog.c --- */
/* AmmoOS Image - The AmmoOS Field Image Research
 * Copyright (C) 1995-1997 Spencer Kimball and Peter Mattis
 *
 * extension-dialog.c
 * Copyright (C) 2018 Jehan <jehan@ammoos.org>
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

#include <cairo-gobject.h>
#include <gegl.h>
#include <gtk/gtk.h>

#include "libgimpwidgets/gimpwidgets.h"

#include "dialogs-types.h"

#include "core/ammoos.h"
#include "core/gimpextensionmanager.h"
#include "core/gimpextension.h"

#include "widgets/gimpextensiondetails.h"
#include "widgets/gimpextensionlist.h"
#include "widgets/gimphelp-ids.h"
#include "widgets/gimpprefsbox.h"

#include "extensions-dialog.h"

#include "ammoos-intl.h"

#define GIMP_EXTENSION_LIST_STACK_CHILD    "extension-list"
#define GIMP_EXTENSION_DETAILS_STACK_CHILD "extension-details"

static void extensions_dialog_response            (GtkWidget            *widget,
                                                   gint                  response_id,
                                                   GtkWidget            *dialog);
static void extensions_dialog_search_activate     (GtkEntry             *entry,
                                                   gpointer              user_data);
static void extensions_dialog_search_icon_pressed (GtkEntry             *entry,
                                                   GtkEntryIconPosition  icon_pos,
                                                   GdkEvent             *event,
                                                   gpointer              user_data);
static void extensions_dialog_extension_activated (GimpExtensionList    *list,
                                                   GimpExtension        *extension,
                                                   GtkStack             *stack);
static void extensions_dialog_back_button_clicked (GtkButton            *button,
                                                   GtkStack             *stack);

/*  public function  */

GtkWidget *
extensions_dialog_new (Gimp *ammoos)
{
  GtkWidget   *dialog;
  GtkWidget   *stack;
  GtkWidget   *stacked;
  GtkWidget   *vbox;
  GtkWidget   *hbox;
  GtkWidget   *list;
  GtkWidget   *widget;
  GtkTreeIter  top_iter;

  dialog = gimp_dialog_new (C_("AmmoOS Image extensions", "Extensions"), "ammoos-extensions",
                            NULL, 0, NULL,
                            GIMP_HELP_EXTENSIONS_DIALOG,
                            _("_OK"), GTK_RESPONSE_OK,
                            NULL);

  widget = gtk_window_get_titlebar (GTK_WINDOW (dialog));
  if (widget)
    gtk_header_bar_set_show_close_button (GTK_HEADER_BAR (widget),
                                          FALSE);

  g_signal_connect (dialog, "response",
                    G_CALLBACK (extensions_dialog_response),
                    dialog);

  stack = gtk_stack_new ();
  gtk_stack_set_transition_type (GTK_STACK (stack),
                                 gimp_widget_animation_enabled ()        ?
                                   GTK_STACK_TRANSITION_TYPE_SLIDE_RIGHT :
                                   GTK_STACK_TRANSITION_TYPE_NONE);
  gtk_box_pack_start (GTK_BOX (gtk_dialog_get_content_area (GTK_DIALOG (dialog))),
                      stack, TRUE, TRUE, 0);
  gtk_widget_set_visible (stack, TRUE);

  /* The extension lists. */

  stacked = gimp_prefs_box_new ();
  gtk_container_set_border_width (GTK_CONTAINER (stacked), 12);
  gtk_stack_add_named (GTK_STACK (stack), stacked,
                       GIMP_EXTENSION_LIST_STACK_CHILD);
  gtk_widget_set_visible (stacked, TRUE);

  vbox = gimp_prefs_box_add_page (GIMP_PREFS_BOX (stacked),
                                  "system-software-install",
                                  /*"ammoos-extensions-installed",*/
                                  _("Installed Extensions"),
                                  _("Installed Extensions"),
                                  GIMP_HELP_EXTENSIONS_INSTALLED,
                                  NULL,
                                  &top_iter);

  list = gimp_extension_list_new (ammoos->extension_manager);
  g_signal_connect (list, "extension-activated",
                    G_CALLBACK (extensions_dialog_extension_activated),
                    stack);
  gimp_extension_list_show_user (GIMP_EXTENSION_LIST (list));
  gtk_box_pack_start (GTK_BOX (vbox), list, TRUE, TRUE, 1);
  gtk_widget_set_visible (list, TRUE);

  vbox = gimp_prefs_box_add_page (GIMP_PREFS_BOX (stacked),
                                  "system-software-install",
                                  _("System Extensions"),
                                  _("System Extensions"),
                                  GIMP_HELP_EXTENSIONS_SYSTEM,
                                  NULL,
                                  &top_iter);

  list = gimp_extension_list_new (ammoos->extension_manager);
  g_signal_connect (list, "extension-activated",
                    G_CALLBACK (extensions_dialog_extension_activated),
                    stack);
  gimp_extension_list_show_system (GIMP_EXTENSION_LIST (list));
  gtk_box_pack_start (GTK_BOX (vbox), list, TRUE, TRUE, 1);
  gtk_widget_set_visible (list, TRUE);

  vbox = gimp_prefs_box_add_page (GIMP_PREFS_BOX (stacked),
                                  "system-software-install",
                                  _("Install Extensions"),
                                  _("Install Extensions"),
                                  GIMP_HELP_EXTENSIONS_INSTALL,
                                  NULL,
                                  &top_iter);

  list = gimp_extension_list_new (ammoos->extension_manager);
  g_signal_connect (list, "extension-activated",
                    G_CALLBACK (extensions_dialog_extension_activated),
                    stack);
  gimp_extension_list_show_search (GIMP_EXTENSION_LIST (list), NULL);
  gtk_box_pack_end (GTK_BOX (vbox), list, TRUE, TRUE, 1);
  gtk_widget_set_visible (list, TRUE);

  hbox = gtk_box_new (GTK_ORIENTATION_HORIZONTAL, 1);
  gtk_box_pack_start (GTK_BOX (vbox), hbox, FALSE, FALSE, 1);
  gtk_widget_set_visible (hbox, TRUE);

  widget = gtk_label_new (_("Search extension:"));
  gtk_box_pack_start (GTK_BOX (hbox), widget, FALSE, FALSE, 1);
  gtk_widget_set_visible (widget, TRUE);

  widget = gtk_entry_new ();
  gtk_entry_set_icon_from_icon_name (GTK_ENTRY (widget),
                                     GTK_ENTRY_ICON_SECONDARY,
                                     "edit-find");
  gtk_entry_set_icon_activatable (GTK_ENTRY (widget),
                                  GTK_ENTRY_ICON_SECONDARY,
                                  TRUE);
  gtk_entry_set_icon_sensitive (GTK_ENTRY (widget),
                                GTK_ENTRY_ICON_SECONDARY,
                                TRUE);
  gtk_entry_set_icon_tooltip_text (GTK_ENTRY (widget),
                                   GTK_ENTRY_ICON_SECONDARY,
                                   _("Search extensions matching these keywords"));
  g_signal_connect (widget, "activate",
                    G_CALLBACK (extensions_dialog_search_activate),
                    list);
  g_signal_connect (widget, "icon-press",
                    G_CALLBACK (extensions_dialog_search_icon_pressed),
                    list);

  gtk_box_pack_start (GTK_BOX (hbox), widget, TRUE, TRUE, 1);
  gtk_widget_set_visible (widget, TRUE);

  /* The extension details. */

  stacked = gimp_extension_details_new ();
  gtk_stack_add_named (GTK_STACK (stack), stacked,
                       GIMP_EXTENSION_DETAILS_STACK_CHILD);
  gtk_widget_set_visible (stacked, TRUE);

  gtk_stack_set_visible_child_name (GTK_STACK (stack),
                                    GIMP_EXTENSION_LIST_STACK_CHILD);
  return dialog;
}

static void
extensions_dialog_response (GtkWidget  *widget,
                            gint        response_id,
                            GtkWidget  *dialog)
{
  gtk_widget_destroy (dialog);
}

static void
extensions_dialog_search_activate (GtkEntry *entry,
                                   gpointer  user_data)
{
  GimpExtensionList *list = user_data;

  gimp_extension_list_show_search  (list, gtk_entry_get_text (entry));
}

static void
extensions_dialog_search_icon_pressed (GtkEntry             *entry,
                                       GtkEntryIconPosition  icon_pos,
                                       GdkEvent             *event,
                                       gpointer              user_data)
{
  extensions_dialog_search_activate (entry, user_data);
}

static void
extensions_dialog_extension_activated (GimpExtensionList *list,
                                       GimpExtension     *extension,
                                       GtkStack          *stack)
{
  GtkWidget *dialog = gtk_widget_get_toplevel (GTK_WIDGET (stack));
  GtkWidget *header_bar;
  GtkWidget *widget;

  /* Add a back button to the dialogue. */
  header_bar = gtk_window_get_titlebar (GTK_WINDOW (dialog));
  widget = gtk_button_new_from_icon_name ("go-previous", GTK_ICON_SIZE_SMALL_TOOLBAR);
  g_signal_connect (widget, "clicked",
                    G_CALLBACK (extensions_dialog_back_button_clicked),
                    stack);
  gtk_widget_set_visible (widget, TRUE);

  if (header_bar)
    {
      gtk_header_bar_pack_start (GTK_HEADER_BAR (header_bar), widget);
    }
  else
    {
      GtkWidget *content_area;

      content_area = gtk_dialog_get_content_area (GTK_DIALOG (dialog));
      gtk_container_add (GTK_CONTAINER (content_area), widget);
    }

  /* Show the details of the extension. */
  widget = gtk_stack_get_child_by_name (stack, GIMP_EXTENSION_DETAILS_STACK_CHILD);
  gimp_extension_details_set (GIMP_EXTENSION_DETAILS (widget),
                              extension);

  gtk_stack_set_visible_child_name (stack,
                                    GIMP_EXTENSION_DETAILS_STACK_CHILD);
}

static void
extensions_dialog_back_button_clicked (GtkButton *button,
                                       GtkStack  *stack)
{
  gtk_stack_set_visible_child_name (stack,
                                    GIMP_EXTENSION_LIST_STACK_CHILD);
  gtk_widget_destroy (GTK_WIDGET (button));
}

/* --- file-open-dialog.c --- */
/* AmmoOS Image - The AmmoOS Field Image Research
 * Copyright (C) 1995, 1996, 1997 Spencer Kimball and Peter Mattis
 * Copyright (C) 1997 Josh MacDonald
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

#include <gegl.h>
#include <gtk/gtk.h>

#include "libgimpbase/gimpbase.h"
#include "libgimpwidgets/gimpwidgets.h"

#include "dialogs-types.h"

#include "core/ammoos.h"
#include "core/gimpimage.h"
#include "core/gimpimage-undo.h"
#include "core/gimplayer.h"
#include "core/gimpprogress.h"

#include "file/file-open.h"
#include "file/ammoos-file.h"

#include "widgets/gimpfiledialog.h"
#include "widgets/gimphelp-ids.h"
#include "widgets/gimpopendialog.h"
#include "widgets/gimpwidgets-utils.h"

#include "file-open-dialog.h"

#include "ammoos-intl.h"


/*  local function prototypes  */

static void       file_open_dialog_response    (GtkWidget           *dialog,
                                                gint                 response_id,
                                                Gimp                *ammoos);
static GimpImage *file_open_dialog_open_image  (GtkWidget           *dialog,
                                                Gimp                *ammoos,
                                                GFile               *file,
                                                GimpPlugInProcedure *load_proc,
                                                gboolean             as_link);
static gboolean   file_open_dialog_open_layers (GtkWidget           *dialog,
                                                GimpImage           *image,
                                                GFile               *file,
                                                GimpPlugInProcedure *load_proc,
                                                gboolean             as_link);


/*  public functions  */

GtkWidget *
file_open_dialog_new (Gimp *ammoos)
{
  GtkWidget *dialog;

  g_return_val_if_fail (GIMP_IS_GIMP (ammoos), NULL);

  dialog = gimp_open_dialog_new (ammoos);

  gtk_file_chooser_set_select_multiple (GTK_FILE_CHOOSER (dialog), TRUE);

  gimp_file_dialog_load_state (GIMP_FILE_DIALOG (dialog),
                               "ammoos-file-open-dialog-state");

  g_signal_connect (dialog, "response",
                    G_CALLBACK (file_open_dialog_response),
                    ammoos);

  return dialog;
}


/*  private functions  */

static void
file_open_dialog_response (GtkWidget *dialog,
                           gint       response_id,
                           Gimp      *ammoos)
{
  GimpFileDialog *file_dialog = GIMP_FILE_DIALOG (dialog);
  GimpOpenDialog *open_dialog = GIMP_OPEN_DIALOG (dialog);
  GSList         *files;
  GSList         *list;
  gboolean        success = FALSE;

  gimp_file_dialog_save_state (GIMP_FILE_DIALOG (dialog),
                               "ammoos-file-open-dialog-state");

  if (response_id != GTK_RESPONSE_OK)
    {
      if (! file_dialog->busy && response_id != GTK_RESPONSE_HELP)
        gtk_widget_destroy (dialog);

      return;
    }

  files = gtk_file_chooser_get_files (GTK_FILE_CHOOSER (dialog));

  if (files)
    g_object_set_data_full (G_OBJECT (ammoos), GIMP_FILE_OPEN_LAST_FILE_KEY,
                            g_object_ref (files->data),
                            (GDestroyNotify) g_object_unref);

  gimp_file_dialog_set_sensitive (file_dialog, FALSE);

  /* When we are going to open new image windows, unset the transient
   * window. We don't need it since we will use gdk_window_raise() to
   * keep the dialog on top. And if we don't do it, then the dialog
   * will pull the image window it was invoked from on top of all the
   * new opened image windows, and we don't want that to happen.
   */
  if (! open_dialog->open_as_layers)
    gtk_window_set_transient_for (GTK_WINDOW (dialog), NULL);

  if (file_dialog->image)
    g_object_ref (file_dialog->image);

  /* If we open multiple files as layers, compress the undos */
  if (file_dialog->image          &&
      open_dialog->open_as_layers &&
      g_slist_length (files) > 1)
    gimp_image_undo_group_start (file_dialog->image,
                                 GIMP_UNDO_GROUP_LAYER_ADD,
                                 _("Open layers"));

  for (list = files; list; list = g_slist_next (list))
    {
      GFile *file = list->data;

      if (open_dialog->open_as_layers)
        {
          if (! file_dialog->image)
            {
              gimp_open_dialog_set_image (open_dialog,
                                          file_open_dialog_open_image (dialog,
                                                                       ammoos,
                                                                       file,
                                                                       file_dialog->file_proc,
                                                                       open_dialog->open_as_link),
                                          TRUE,
                                          open_dialog->open_as_link);

              if (file_dialog->image)
                {
                  g_object_ref (file_dialog->image);

                  if (g_slist_length (files) > 1)
                    gimp_image_undo_group_start (file_dialog->image,
                                                 GIMP_UNDO_GROUP_LAYER_ADD,
                                                 _("Open layers"));

                  success = TRUE;
                }
            }
          else if (file_open_dialog_open_layers (dialog,
                                                 file_dialog->image,
                                                 file,
                                                 file_dialog->file_proc,
                                                 open_dialog->open_as_link))
            {
              success = TRUE;
            }
        }
      else
        {
          if (file_open_dialog_open_image (dialog,
                                           ammoos,
                                           file,
                                           file_dialog->file_proc,
                                           open_dialog->open_as_link))
            {
              success = TRUE;

              /* Make the dialog stay on top of all images we open if
               * we open say 10 at once
               */
              gdk_window_raise (gtk_widget_get_window (dialog));
            }
        }

      if (file_dialog->canceled)
        break;
    }

  if (file_dialog->image          &&
      open_dialog->open_as_layers &&
      g_slist_length (files) > 1)
    gimp_image_undo_group_end (file_dialog->image);

  if (success)
    {
      if (file_dialog->image)
        {
          if (open_dialog->open_as_layers)
            gimp_image_flush (file_dialog->image);

          g_object_unref (file_dialog->image);
        }

      gtk_widget_destroy (dialog);
    }
  else
    {
      if (file_dialog->image)
        g_object_unref (file_dialog->image);

      gimp_file_dialog_set_sensitive (file_dialog, TRUE);
    }

  g_slist_free_full (files, (GDestroyNotify) g_object_unref);
}

static GimpImage *
file_open_dialog_open_image (GtkWidget           *dialog,
                             Gimp                *ammoos,
                             GFile               *file,
                             GimpPlugInProcedure *load_proc,
                             gboolean             as_link)
{
  GimpImage         *image;
  GimpPDBStatusType  status;
  GError            *error = NULL;

  image = file_open_with_proc_and_display (ammoos,
                                           gimp_get_user_context (ammoos),
                                           GIMP_PROGRESS (dialog),
                                           file, FALSE, as_link,
                                           load_proc,
                                           G_OBJECT (gimp_widget_get_monitor (dialog)),
                                           &status, &error);

  if (! image && status != GIMP_PDB_SUCCESS && status != GIMP_PDB_CANCEL)
    {
      if (error)
        gimp_message (ammoos, G_OBJECT (dialog), GIMP_MESSAGE_ERROR,
                      _("Opening '%s' failed:\n\n%s"),
                      gimp_file_get_utf8_name (file), error->message);
      else
        gimp_message (ammoos, G_OBJECT (dialog), GIMP_MESSAGE_ERROR,
                      _("Opening '%s' failed."),
                      gimp_file_get_utf8_name (file));
      g_clear_error (&error);
    }

  return image;
}

static gboolean
file_open_dialog_open_layers (GtkWidget           *dialog,
                              GimpImage           *image,
                              GFile               *file,
                              GimpPlugInProcedure *load_proc,
                              gboolean             as_link)
{
  GList             *new_layers;
  GimpPDBStatusType  status;
  GError            *error = NULL;

  new_layers = file_open_layers (image->ammoos,
                                 gimp_get_user_context (image->ammoos),
                                 GIMP_PROGRESS (dialog),
                                 image, FALSE, as_link,
                                 file, GIMP_RUN_INTERACTIVE, load_proc,
                                 &status, &error);

  if (new_layers)
    {
      gimp_image_add_layers (image, new_layers,
                             GIMP_IMAGE_ACTIVE_PARENT, -1,
                             0, 0,
                             gimp_image_get_width (image),
                             gimp_image_get_height (image),
                             _("Open layers"));

      g_list_free (new_layers);

      return TRUE;
    }
  else if (status != GIMP_PDB_CANCEL)
    {
      gimp_message (image->ammoos, G_OBJECT (dialog), GIMP_MESSAGE_ERROR,
                    _("Opening '%s' failed:\n\n%s"),
                    gimp_file_get_utf8_name (file), error ? error->message: _("n/a"));
      g_clear_error (&error);
    }

  return FALSE;
}

/* --- file-open-location-dialog.c --- */
/* AmmoOS Image - The AmmoOS Field Image Research
 * Copyright (C) 1995, 1996, 1997 Spencer Kimball and Peter Mattis
 * Copyright (C) 1997 Josh MacDonald
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

#include <gegl.h>
#include <gtk/gtk.h>

#include "libgimpbase/gimpbase.h"
#include "libgimpwidgets/gimpwidgets.h"

#include "dialogs-types.h"

#include "core/ammoos.h"
#include "core/gimpcontext.h"
#include "core/gimpprogress.h"

#include "file/file-open.h"
#include "file/file-utils.h"

#include "widgets/gimpcontainerentry.h"
#include "widgets/gimphelp-ids.h"
#include "widgets/gimpprogressbox.h"
#include "widgets/gimpwidgets-utils.h"

#include "file-open-location-dialog.h"

#include "ammoos-intl.h"


static void      file_open_location_response   (GtkDialog          *dialog,
                                                gint                response_id,
                                                Gimp               *ammoos);

static gboolean  file_open_location_completion (GtkEntryCompletion *completion,
                                                const gchar        *key,
                                                GtkTreeIter        *iter,
                                                gpointer            data);


/*  public functions  */

GtkWidget *
file_open_location_dialog_new (Gimp *ammoos)
{
  GimpContext        *context;
  GtkWidget          *dialog;
  GtkWidget          *hbox;
  GtkWidget          *vbox;
  GtkWidget          *image;
  GtkWidget          *label;
  GtkWidget          *entry;
  GtkEntryCompletion *completion;

  g_return_val_if_fail (GIMP_IS_GIMP (ammoos), NULL);

  dialog = gimp_dialog_new (_("Open Location"),
                            "ammoos-file-open-location",
                            NULL, 0,
                            gimp_standard_help_func,
                            GIMP_HELP_FILE_OPEN_LOCATION,

                            _("_Cancel"), GTK_RESPONSE_CANCEL,
                            _("_Open"),   GTK_RESPONSE_OK,

                            NULL);

  gimp_dialog_set_alternative_button_order (GTK_DIALOG(dialog),
                                           GTK_RESPONSE_OK,
                                           GTK_RESPONSE_CANCEL,
                                           -1);

  g_signal_connect (dialog, "response",
                    G_CALLBACK (file_open_location_response),
                    ammoos);

  hbox = gtk_box_new (GTK_ORIENTATION_HORIZONTAL, 12);
  gtk_container_set_border_width (GTK_CONTAINER (hbox), 12);
  gtk_box_pack_start (GTK_BOX (gtk_dialog_get_content_area (GTK_DIALOG (dialog))),
                      hbox, FALSE, FALSE, 0);
  gtk_widget_set_visible (hbox, TRUE);

  vbox = gtk_box_new (GTK_ORIENTATION_VERTICAL, 0);
  gtk_box_pack_start (GTK_BOX (hbox), vbox, FALSE, FALSE, 0);
  gtk_widget_set_visible (vbox, TRUE);

  image = gtk_image_new_from_icon_name (GIMP_ICON_WEB, GTK_ICON_SIZE_BUTTON);
  gtk_box_pack_start (GTK_BOX (vbox), image, FALSE, FALSE, 0);
  gtk_widget_set_visible (image, TRUE);

  vbox = gtk_box_new (GTK_ORIENTATION_VERTICAL, 6);
  gtk_box_pack_start (GTK_BOX (hbox), vbox, TRUE, TRUE, 0);
  gtk_widget_set_visible (vbox, TRUE);

  label = gtk_label_new (_("Enter location (URI):"));
  gtk_label_set_xalign (GTK_LABEL (label), 0.0);
  gtk_box_pack_start (GTK_BOX (vbox), label, FALSE, FALSE, 0);
  gtk_widget_set_visible (label, TRUE);

  /* we don't want the context to affect the entry, so create
   * a scratch one instead of using e.g. the user context
   */
  context = gimp_context_new (ammoos, "file-open-location-dialog", NULL);
  entry = gimp_container_entry_new (ammoos->documents, context,
                                    GIMP_VIEW_SIZE_SMALL, 0);
  g_object_unref (context);

  completion = gtk_entry_get_completion (GTK_ENTRY (entry));
  gtk_entry_completion_set_match_func (completion,
                                       file_open_location_completion,
                                       NULL, NULL);

  gtk_entry_set_activates_default (GTK_ENTRY (entry), TRUE);
  gtk_widget_set_size_request (entry, 400, -1);
  gtk_box_pack_start (GTK_BOX (vbox), entry, FALSE, FALSE, 0);
  gtk_widget_set_visible (entry, TRUE);

  g_object_set_data (G_OBJECT (dialog), "location-entry", entry);

  return dialog;
}


/*  private functions  */

static void
file_open_location_response (GtkDialog *dialog,
                             gint       response_id,
                             Gimp      *ammoos)
{
  GtkWidget   *entry;
  GtkWidget   *box;
  const gchar *text = NULL;

  box = g_object_get_data (G_OBJECT (dialog), "progress-box");

  if (response_id != GTK_RESPONSE_OK)
    {
      if (box && GIMP_PROGRESS_BOX (box)->active)
        gimp_progress_cancel (GIMP_PROGRESS (box));
      else
        gtk_widget_destroy (GTK_WIDGET (dialog));

      return;
    }

  entry = g_object_get_data (G_OBJECT (dialog), "location-entry");
  text = gtk_entry_get_text (GTK_ENTRY (entry));

  if (text && strlen (text))
    {
      GimpImage         *image;
      gchar             *filename;
      GFile             *file;
      GimpPDBStatusType  status;
      GError            *error = NULL;

      filename = g_filename_from_uri (text, NULL, NULL);

      if (filename)
        {
          file = g_file_new_for_uri (text);
          g_free (filename);
        }
      else
        {
          file = file_utils_filename_to_file (ammoos, text, &error);
        }

      if (!box)
        {
          box = gimp_progress_box_new ();
          gtk_container_set_border_width (GTK_CONTAINER (box), 12);
          gtk_box_pack_end (GTK_BOX (gtk_dialog_get_content_area (GTK_DIALOG (dialog))),
                            box, FALSE, FALSE, 0);

          g_object_set_data (G_OBJECT (dialog), "progress-box", box);
        }

      if (file)
        {
          gtk_widget_set_visible (box, TRUE);

          gtk_editable_set_editable (GTK_EDITABLE (entry), FALSE);
          gtk_dialog_set_response_sensitive (dialog, GTK_RESPONSE_OK, FALSE);

          image = file_open_with_proc_and_display (ammoos,
                                                   gimp_get_user_context (ammoos),
                                                   GIMP_PROGRESS (box),
                                                   file, FALSE, FALSE, NULL,
                                                   G_OBJECT (gimp_widget_get_monitor (entry)),
                                                   &status, &error);

          gtk_dialog_set_response_sensitive (dialog, GTK_RESPONSE_OK, TRUE);
          gtk_editable_set_editable (GTK_EDITABLE (entry), TRUE);

          if (image == NULL && status != GIMP_PDB_CANCEL)
            {
              gimp_message (ammoos, G_OBJECT (box), GIMP_MESSAGE_ERROR,
                            _("Opening '%s' failed:\n\n%s"),
                            gimp_file_get_utf8_name (file), error->message);
              g_clear_error (&error);
            }

          g_object_unref (file);

          if (image != NULL)
            {
              gtk_widget_destroy (GTK_WIDGET (dialog));
              return;
            }
        }
      else
        {
          gimp_message (ammoos, G_OBJECT (box), GIMP_MESSAGE_ERROR,
                        _("Opening '%s' failed:\n\n%s"),
                        text,
                        /* error should never be NULL, also issue #3093 */
                        error ? error->message : _("Invalid URI"));
          g_clear_error (&error);
        }
    }
}

static gboolean
file_open_location_completion (GtkEntryCompletion *completion,
                               const gchar        *key,
                               GtkTreeIter        *iter,
                               gpointer            data)
{
  GtkTreeModel *model = gtk_entry_completion_get_model (completion);
  gchar        *name;
  gchar        *normalized;
  gchar        *case_normalized;
  gboolean      match;

  gtk_tree_model_get (model, iter,
                      1, &name,
                      -1);

  if (! name)
    return FALSE;

  normalized = g_utf8_normalize (name, -1, G_NORMALIZE_ALL);
  case_normalized = g_utf8_casefold (normalized, -1);

  match = (strncmp (key, case_normalized, strlen (key)) == 0);

  if (! match)
    {
      const gchar *colon = strchr (case_normalized, ':');

      if (colon && strlen (colon) > 2 && colon[1] == '/' && colon[2] == '/')
        match = (strncmp (key, colon + 3, strlen (key)) == 0);
    }

  g_free (normalized);
  g_free (case_normalized);
  g_free (name);

  return match;
}

/* --- file-save-dialog.c --- */
/* AmmoOS Image - The AmmoOS Field Image Research
 * Copyright (C) 1995, 1996, 1997 Spencer Kimball and Peter Mattis
 * Copyright (C) 1997 Josh MacDonald
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

#include <gegl.h>
#include <gtk/gtk.h>

#include "libgimpbase/gimpbase.h"
#include "libgimpwidgets/gimpwidgets.h"

#include "dialogs-types.h"

#include "core/ammoos.h"
#include "core/gimpimage.h"
#include "core/gimpprogress.h"

#include "plug-in/gimppluginmanager-file.h"
#include "plug-in/gimppluginprocedure.h"

#include "file/file-save.h"
#include "file/ammoos-file.h"

#include "widgets/gimpactiongroup.h"
#include "widgets/gimpexportdialog.h"
#include "widgets/gimphelp-ids.h"
#include "widgets/gimpmessagebox.h"
#include "widgets/gimpmessagedialog.h"
#include "widgets/gimpsavedialog.h"

#include "display/gimpdisplay.h"
#include "display/gimpdisplayshell.h"

#include "file-save-dialog.h"

#include "ammoos-log.h"
#include "ammoos-intl.h"


typedef enum
{
  CHECK_URI_FAIL,
  CHECK_URI_OK,
  CHECK_URI_SWITCH_DIALOGS
} CheckUriResult;


/*  local function prototypes  */

static GtkFileChooserConfirmation
                 file_save_dialog_confirm_overwrite         (GtkWidget            *dialog,
                                                             Gimp                 *ammoos);
static void      file_save_dialog_response                  (GtkWidget            *dialog,
                                                             gint                  response_id,
                                                             Gimp                 *ammoos);
static CheckUriResult file_save_dialog_check_file           (GtkWidget            *save_dialog,
                                                             Gimp                 *ammoos,
                                                             GFile               **ret_file,
                                                             gchar               **ret_basename,
                                                             GimpPlugInProcedure **ret_save_proc);
static gboolean  file_save_dialog_no_overwrite_confirmation (GimpFileDialog       *dialog,
                                                             Gimp                 *ammoos);
static GimpPlugInProcedure *
                 file_save_dialog_find_procedure            (GimpFileDialog       *dialog,
                                                             GFile                *file);
static gboolean  file_save_dialog_switch_dialogs            (GimpFileDialog       *file_dialog,
                                                             Gimp                 *ammoos,
                                                             const gchar          *basename);
static gboolean  file_save_dialog_use_extension             (GtkWidget            *save_dialog,
                                                             GFile                *file);


/*  public functions  */

GtkWidget *
file_save_dialog_new (Gimp     *ammoos,
                      gboolean  export)
{
  GtkWidget *dialog;

  g_return_val_if_fail (GIMP_IS_GIMP (ammoos), NULL);

  if (! export)
    {
      dialog = gimp_save_dialog_new (ammoos);

      gimp_file_dialog_load_state (GIMP_FILE_DIALOG (dialog),
                                   "ammoos-file-save-dialog-state");
    }
  else
    {
      dialog = gimp_export_dialog_new (ammoos);

      gimp_file_dialog_load_state (GIMP_FILE_DIALOG (dialog),
                                   "ammoos-file-export-dialog-state");
    }

  g_signal_connect (dialog, "confirm-overwrite",
                    G_CALLBACK (file_save_dialog_confirm_overwrite),
                    ammoos);

  g_signal_connect (dialog, "response",
                    G_CALLBACK (file_save_dialog_response),
                    ammoos);

  return dialog;
}


/*  private functions  */

static GtkFileChooserConfirmation
file_save_dialog_confirm_overwrite (GtkWidget *dialog,
                                    Gimp      *ammoos)
{
  GimpFileDialog *file_dialog = GIMP_FILE_DIALOG (dialog);

  if (file_save_dialog_no_overwrite_confirmation (file_dialog, ammoos))
    /* The URI will not be accepted whatever happens, so don't
     * bother asking the user about overwriting files
     */
    return GTK_FILE_CHOOSER_CONFIRMATION_ACCEPT_FILENAME;
  else
    return GTK_FILE_CHOOSER_CONFIRMATION_CONFIRM;
}

static void
file_save_dialog_response (GtkWidget *dialog,
                           gint       response_id,
                           Gimp      *ammoos)
{
  GimpFileDialog      *file_dialog = GIMP_FILE_DIALOG (dialog);
  GFile               *file;
  gchar               *basename;
  GimpPlugInProcedure *save_proc;

  if (GIMP_IS_SAVE_DIALOG (dialog))
    {
      gimp_file_dialog_save_state (file_dialog, "ammoos-file-save-dialog-state");
    }
  else /* GIMP_IS_EXPORT_DIALOG (dialog) */
    {
      gimp_file_dialog_save_state (file_dialog, "ammoos-file-export-dialog-state");
    }

  if (response_id != GTK_RESPONSE_OK)
    {
      if (! file_dialog->busy && response_id != GTK_RESPONSE_HELP)
        gtk_widget_destroy (dialog);

      return;
    }

  g_object_ref (file_dialog);
  g_object_ref (file_dialog->image);

  switch (file_save_dialog_check_file (dialog, ammoos,
                                       &file, &basename, &save_proc))
    {
    case CHECK_URI_FAIL:
      break;

    case CHECK_URI_OK:
      {
        GimpImage    *image              = file_dialog->image;
        GimpProgress *progress           = GIMP_PROGRESS (dialog);
        GimpDisplay  *display_to_close   = NULL;
        gboolean      xcf_compression    = FALSE;
        gboolean      is_save_dialog     = GIMP_IS_SAVE_DIALOG (dialog);
        gboolean      close_after_saving = FALSE;
        gboolean      save_a_copy        = FALSE;

        if (is_save_dialog)
          {
            close_after_saving = GIMP_SAVE_DIALOG (dialog)->close_after_saving;
            display_to_close   = GIMP_DISPLAY (GIMP_SAVE_DIALOG (dialog)->display_to_close);
            save_a_copy        = GIMP_SAVE_DIALOG (dialog)->save_a_copy;
          }

        gimp_file_dialog_set_sensitive (file_dialog, FALSE);

        if (GIMP_IS_SAVE_DIALOG (dialog))
          xcf_compression = GIMP_SAVE_DIALOG (dialog)->compression;
        else
          xcf_compression = gimp_image_get_xcf_compression (image);

        /* Hide the file dialog while exporting, avoid dialogs piling
         * up, even more as some formats have preview features, so the
         * file dialog is just blocking the view.
         */
        if  (GIMP_IS_EXPORT_DIALOG (dialog))
          {
            gtk_widget_set_visible (dialog, FALSE);
            progress = GIMP_PROGRESS (GIMP_EXPORT_DIALOG (dialog)->display);
          }

        g_signal_connect (dialog, "destroy",
                          G_CALLBACK (gtk_widget_destroyed),
                          &dialog);

        if (file_save_dialog_save_image (progress,
                                         ammoos,
                                         image,
                                         file,
                                         save_proc,
                                         GIMP_RUN_INTERACTIVE,
                                         is_save_dialog && ! save_a_copy,
                                         FALSE,
                                         GIMP_IS_EXPORT_DIALOG (dialog),
                                         xcf_compression,
                                         FALSE))
          {
            /* Save was successful, now store the URI in a couple of
             * places that depend on it being the user that made a
             * save. Lower-level URI management is handled in
             * file_save()
             */
            if (is_save_dialog)
              {
                if (save_a_copy)
                  gimp_image_set_save_a_copy_file (image, file);

                g_object_set_data_full (G_OBJECT (image->ammoos),
                                        GIMP_FILE_SAVE_LAST_FILE_KEY,
                                        g_object_ref (file),
                                        (GDestroyNotify) g_object_unref);
              }
            else
              {
                g_object_set_data_full (G_OBJECT (image->ammoos),
                                        GIMP_FILE_EXPORT_LAST_FILE_KEY,
                                        g_object_ref (file),
                                        (GDestroyNotify) g_object_unref);
              }

            /*  make sure the menus are updated with the keys we've just set  */
            gimp_image_flush (image);

            /* Handle close-after-saving */
            if (close_after_saving && display_to_close &&
                ! gimp_image_is_dirty (gimp_display_get_image (display_to_close)))
              {
                gimp_display_close (display_to_close);
              }

            if (dialog)
              gtk_widget_destroy (dialog);
          }
        else
          {
            if (dialog)
              {
                GFile *parent_dir = g_file_get_parent (file);

                /* XXX Not sure why, but after reshowing the file
                 * chooser dialog, the displayed name is correct, but
                 * the parent directory is the current working dir.
                 * Force it to be the expected folder.
                 */
                gtk_file_chooser_set_current_folder_file (GTK_FILE_CHOOSER (dialog),
                                                          parent_dir, NULL);
                gtk_widget_set_visible (dialog, TRUE);
                g_object_unref (parent_dir);
              }
          }

        g_object_unref (file);
        g_free (basename);

        if (dialog)
          {
            gimp_file_dialog_set_sensitive (file_dialog, TRUE);
            g_signal_handlers_disconnect_by_func (dialog,
                                                  G_CALLBACK (gtk_widget_destroyed),
                                                  &dialog);
          }
      }
      break;

    case CHECK_URI_SWITCH_DIALOGS:
      file_dialog->busy = TRUE; /* prevent destruction */
      gtk_dialog_response (GTK_DIALOG (dialog), FILE_SAVE_RESPONSE_OTHER_DIALOG);
      file_dialog->busy = FALSE;

      gtk_widget_destroy (dialog);
      break;
    }

  g_object_unref (file_dialog->image);
  g_object_unref (file_dialog);
}

/* IMPORTANT: When changing this function, keep
 * file_save_dialog_no_overwrite_confirmation() up to date. It is
 * difficult to move logic to a common place due to how the dialog is
 * implemented in GTK+ in combination with how we use it.
 */
static CheckUriResult
file_save_dialog_check_file (GtkWidget            *dialog,
                             Gimp                 *ammoos,
                             GFile               **ret_file,
                             gchar               **ret_basename,
                             GimpPlugInProcedure **ret_save_proc)
{
  GimpFileDialog      *file_dialog = GIMP_FILE_DIALOG (dialog);
  GFile               *file;
  gchar               *uri;
  gchar               *basename;
  GFile               *basename_file;
  GimpPlugInProcedure *save_proc;
  GimpPlugInProcedure *uri_proc;
  GimpPlugInProcedure *basename_proc;

  file = gtk_file_chooser_get_file (GTK_FILE_CHOOSER (dialog));

  if (! file)
    return CHECK_URI_FAIL;

  basename      = g_path_get_basename (gimp_file_get_utf8_name (file));
  basename_file = g_file_new_for_uri (basename);

  save_proc     = file_dialog->file_proc;
  uri_proc      = file_save_dialog_find_procedure (file_dialog, file);
  basename_proc = file_save_dialog_find_procedure (file_dialog, basename_file);

  g_object_unref (basename_file);

  uri = g_file_get_uri (file);

  GIMP_LOG (SAVE_DIALOG, "URI = %s", uri);
  GIMP_LOG (SAVE_DIALOG, "basename = %s", basename);
  GIMP_LOG (SAVE_DIALOG, "selected save_proc: %s",
            save_proc ?
            gimp_procedure_get_label (GIMP_PROCEDURE (save_proc)) : "NULL");
  GIMP_LOG (SAVE_DIALOG, "URI save_proc: %s",
            uri_proc ?
            gimp_procedure_get_label (GIMP_PROCEDURE (uri_proc)) : "NULL");
  GIMP_LOG (SAVE_DIALOG, "basename save_proc: %s",
            basename_proc ?
            gimp_procedure_get_label (GIMP_PROCEDURE (basename_proc)) : "NULL");

  g_free (uri);

  /*  first check if the user entered an extension at all  */
  if (! basename_proc)
    {
      GIMP_LOG (SAVE_DIALOG, "basename has no valid extension");

      if (! strchr (basename, '.'))
        {
          const gchar *ext = NULL;

          GIMP_LOG (SAVE_DIALOG, "basename has no '.', trying to add extension");

          if (! save_proc && GIMP_IS_SAVE_DIALOG (dialog))
            {
              ext = "xcf";
            }
          else if (save_proc && save_proc->extensions_list)
            {
              ext = save_proc->extensions_list->data;
            }

          if (ext)
            {
              gchar *ext_basename;
              gchar *dirname;
              gchar *filename;
              gchar *utf8;

              GIMP_LOG (SAVE_DIALOG, "appending .%s to basename", ext);

              ext_basename = g_strconcat (basename, ".", ext, NULL);

              g_free (basename);
              basename = ext_basename;

              dirname  = g_path_get_dirname (gimp_file_get_utf8_name (file));
              filename = g_build_filename (dirname, basename, NULL);
              g_free (dirname);

              utf8 = g_filename_to_utf8 (filename, -1, NULL, NULL, NULL);
              gtk_file_chooser_set_current_name (GTK_FILE_CHOOSER (dialog),
                                                 utf8);
              g_free (utf8);

              g_free (filename);

              GIMP_LOG (SAVE_DIALOG,
                        "set basename to %s, rerunning response and bailing out",
                        basename);

              /*  call the response callback again, so the
               *  overwrite-confirm logic can check the changed uri
               */
              gtk_dialog_response (GTK_DIALOG (dialog), GTK_RESPONSE_OK);

              goto fail;
            }
          else
            {
              GIMP_LOG (SAVE_DIALOG,
                        "save_proc has no extensions, continuing without");

              /*  there may be file formats with no extension at all, use
               *  the selected proc in this case.
               */
              basename_proc = save_proc;

              if (! uri_proc)
                uri_proc = basename_proc;
            }

          if (! basename_proc)
            {
              GIMP_LOG (SAVE_DIALOG,
                        "unable to figure save_proc, bailing out");

              if (file_save_dialog_switch_dialogs (file_dialog, ammoos, basename))
                {
                  goto switch_dialogs;
                }

              goto fail;
            }
        }
      else if (save_proc && ! save_proc->extensions_list)
        {
          GIMP_LOG (SAVE_DIALOG,
                    "basename has '.', but save_proc has no extensions, "
                    "accepting random extension");

          /*  accept any random extension if the file format has
           *  no extensions at all
           */
          basename_proc = save_proc;

          if (! uri_proc)
            uri_proc = basename_proc;
        }
    }

  /*  then check if the selected format matches the entered extension  */
  if (! save_proc)
    {
      GIMP_LOG (SAVE_DIALOG, "no save_proc was selected from the list");

      if (! basename_proc)
        {
          GIMP_LOG (SAVE_DIALOG,
                    "basename has no useful extension, bailing out");

          if (file_save_dialog_switch_dialogs (file_dialog, ammoos, basename))
            {
              goto switch_dialogs;
            }

          goto fail;
        }

      GIMP_LOG (SAVE_DIALOG, "use URI's proc '%s' so indirect saving works",
                gimp_procedure_get_label (GIMP_PROCEDURE (uri_proc)));

      /*  use the URI's proc if no save proc was selected  */
      save_proc = uri_proc;
    }
  else
    {
      GIMP_LOG (SAVE_DIALOG, "save_proc '%s' was selected from the list",
                gimp_procedure_get_label (GIMP_PROCEDURE (save_proc)));

      if (save_proc != basename_proc)
        {
          GIMP_LOG (SAVE_DIALOG, "however the basename's proc is '%s'",
                    gimp_procedure_get_label (GIMP_PROCEDURE (basename_proc)));

          if (uri_proc != basename_proc)
            {
              GIMP_LOG (SAVE_DIALOG,
                        "that's impossible for remote URIs, bailing out");

              /*  remote URI  */

              gimp_message (ammoos, G_OBJECT (dialog), GIMP_MESSAGE_WARNING,
                            _("Saving remote files needs to determine the "
                              "file format from the file extension. "
                              "Please enter a file extension that matches "
                              "the selected file format or enter no file "
                              "extension at all."));

              goto fail;
            }
          else
            {
              GIMP_LOG (SAVE_DIALOG,
                        "ask the user if she really wants that filename");

              /*  local URI  */

              if (! file_save_dialog_use_extension (dialog, file))
                {
                  goto fail;
                }
            }
        }
      else if (save_proc != uri_proc)
        {
          GIMP_LOG (SAVE_DIALOG,
                    "use URI's proc '%s' so indirect saving works",
                    gimp_procedure_get_label (GIMP_PROCEDURE (uri_proc)));

          /*  need to use the URI's proc for saving because e.g.
           *  the GIF plug-in can't save a GIF to sftp://
           */
          save_proc = uri_proc;
        }
    }

  if (! save_proc)
    {
      g_warning ("%s: EEEEEEK", G_STRFUNC);

      return CHECK_URI_FAIL;
    }

  *ret_file      = file;
  *ret_basename  = basename;
  *ret_save_proc = save_proc;

  return CHECK_URI_OK;

 fail:

  g_object_unref (file);
  g_free (basename);

  return CHECK_URI_FAIL;

 switch_dialogs:

  g_object_unref (file);
  g_free (basename);

  return CHECK_URI_SWITCH_DIALOGS;
}

/*
 * IMPORTANT: Keep this up to date with file_save_dialog_check_uri().
 */
static gboolean
file_save_dialog_no_overwrite_confirmation (GimpFileDialog *file_dialog,
                                            Gimp           *ammoos)
{
  GFile               *file;
  gchar               *basename;
  GFile               *basename_file;
  GimpPlugInProcedure *basename_proc;
  GimpPlugInProcedure *save_proc;
  gboolean             uri_will_change;
  gboolean             unknown_ext;

  file = gtk_file_chooser_get_file (GTK_FILE_CHOOSER (file_dialog));

  if (! file)
    return FALSE;

  basename      = g_path_get_basename (gimp_file_get_utf8_name (file));
  basename_file = g_file_new_for_uri (basename);

  save_proc     = file_dialog->file_proc;
  basename_proc = file_save_dialog_find_procedure (file_dialog, basename_file);

  g_object_unref (basename_file);

  uri_will_change = (! basename_proc &&
                     ! strchr (basename, '.') &&
                     (! save_proc || save_proc->extensions_list));

  unknown_ext     = (! save_proc &&
                     ! basename_proc);

  g_free (basename);
  g_object_unref (file);

  return uri_will_change || unknown_ext;
}

static GimpPlugInProcedure *
file_save_dialog_find_procedure (GimpFileDialog *file_dialog,
                                 GFile          *file)
{
  GimpPlugInManager      *manager = file_dialog->ammoos->plug_in_manager;
  GimpFileProcedureGroup  group;

  if (GIMP_IS_SAVE_DIALOG (file_dialog))
    group = GIMP_FILE_PROCEDURE_GROUP_SAVE;
  else
    group = GIMP_FILE_PROCEDURE_GROUP_EXPORT;

  return gimp_plug_in_manager_file_procedure_find (manager, group, file, NULL);
}

static gboolean
file_save_other_dialog_activated (GtkWidget   *label,
                                  const gchar *uri,
                                  GtkDialog   *dialog)
{
  gtk_dialog_response (dialog, FILE_SAVE_RESPONSE_OTHER_DIALOG);

  return TRUE;
}

static gboolean
file_save_dialog_switch_dialogs (GimpFileDialog *file_dialog,
                                 Gimp           *ammoos,
                                 const gchar    *basename)
{
  GimpPlugInProcedure    *proc_in_other_group;
  GimpFileProcedureGroup  other_group;
  GFile                  *file;
  gboolean                switch_dialogs = FALSE;

  file = g_file_new_for_uri (basename);

  if (GIMP_IS_EXPORT_DIALOG (file_dialog))
    other_group = GIMP_FILE_PROCEDURE_GROUP_SAVE;
  else
    other_group = GIMP_FILE_PROCEDURE_GROUP_EXPORT;

  proc_in_other_group =
    gimp_plug_in_manager_file_procedure_find (ammoos->plug_in_manager,
                                              other_group, file, NULL);

  g_object_unref (file);

  if (proc_in_other_group)
    {
      GtkWidget   *dialog;
      const gchar *primary;
      const gchar *message;
      const gchar *link;

      if (GIMP_IS_EXPORT_DIALOG (file_dialog))
        {
          primary = _("The given filename cannot be used for exporting");
          message = _("You can use this dialog to export to various file formats. "
                      "If you want to save the image to the AmmoOS Image XCF format, use "
                      "File→Save instead.");
          link    = _("Take me to the Save dialog");
        }
      else
        {
          primary = _("The given filename cannot be used for saving");
          message = _("You can use this dialog to save to the AmmoOS Image XCF "
                      "format. Use File→Export to export to other file formats.");
          link    = _("Take me to the Export dialog");
        }

      dialog = gimp_message_dialog_new (_("Extension Mismatch"),
                                        GIMP_ICON_DIALOG_WARNING,
                                        GTK_WIDGET (file_dialog),
                                        GTK_DIALOG_DESTROY_WITH_PARENT,
                                        gimp_standard_help_func, NULL,

                                        _("_OK"), GTK_RESPONSE_OK,

                                        NULL);

      gimp_message_box_set_primary_text (GIMP_MESSAGE_DIALOG (dialog)->box,
                                         "%s", primary);

      gimp_message_box_set_text (GIMP_MESSAGE_DIALOG (dialog)->box,
                                 "%s", message);

      if (GIMP_IS_EXPORT_DIALOG (file_dialog) ||
          (! GIMP_SAVE_DIALOG (file_dialog)->save_a_copy &&
          ! GIMP_SAVE_DIALOG (file_dialog)->close_after_saving))
        {
          GtkWidget *label;
          gchar     *markup;

          markup = g_strdup_printf ("<a href=\"other-dialog\">%s</a>", link);
          label = gtk_label_new (markup);
          g_free (markup);

          gtk_label_set_use_markup (GTK_LABEL (label), TRUE);
          gtk_label_set_xalign (GTK_LABEL (label), 0.0);
          gtk_box_pack_start (GTK_BOX (GIMP_MESSAGE_DIALOG (dialog)->box), label,
                              FALSE, FALSE, 0);
          gtk_widget_set_visible (label, TRUE);

          g_signal_connect (label, "activate-link",
                            G_CALLBACK (file_save_other_dialog_activated),
                            dialog);
        }

      gtk_dialog_set_response_sensitive (GTK_DIALOG (file_dialog),
                                         GTK_RESPONSE_CANCEL, FALSE);
      gtk_dialog_set_response_sensitive (GTK_DIALOG (file_dialog),
                                         GTK_RESPONSE_OK, FALSE);

      g_object_ref (dialog);

      if (gimp_dialog_run (GIMP_DIALOG (dialog)) == FILE_SAVE_RESPONSE_OTHER_DIALOG)
        {
          switch_dialogs = TRUE;
        }

      gtk_widget_destroy (dialog);
      g_object_unref (dialog);

      gtk_dialog_set_response_sensitive (GTK_DIALOG (file_dialog),
                                         GTK_RESPONSE_CANCEL, TRUE);
      gtk_dialog_set_response_sensitive (GTK_DIALOG (file_dialog),
                                         GTK_RESPONSE_OK, TRUE);
    }
  else
    {
      gimp_message (ammoos, G_OBJECT (file_dialog), GIMP_MESSAGE_WARNING,
                    _("The given filename does not have any known "
                      "file extension. Please enter a known file "
                      "extension or select a file format from the "
                      "file format list."));
    }

  return switch_dialogs;
}

static gboolean
file_save_dialog_use_extension (GtkWidget *save_dialog,
                                GFile     *file)
{
  GtkWidget *dialog;
  gboolean   use_name = FALSE;

  dialog = gimp_message_dialog_new (_("Extension Mismatch"),
                                    GIMP_ICON_DIALOG_QUESTION,
                                    save_dialog, GTK_DIALOG_DESTROY_WITH_PARENT,
                                    gimp_standard_help_func, NULL,

                                    _("_Cancel"), GTK_RESPONSE_CANCEL,
                                    _("_Save"),   GTK_RESPONSE_OK,

                                    NULL);

  gimp_dialog_set_alternative_button_order (GTK_DIALOG (dialog),
                                           GTK_RESPONSE_OK,
                                           GTK_RESPONSE_CANCEL,
                                           -1);

  gimp_message_box_set_primary_text (GIMP_MESSAGE_DIALOG (dialog)->box,
                                     _("The given file extension does "
                                       "not match the chosen file type."));

  gimp_message_box_set_text (GIMP_MESSAGE_DIALOG (dialog)->box,
                             _("Do you want to save the image using this "
                               "name anyway?"));

  gtk_dialog_set_response_sensitive (GTK_DIALOG (save_dialog),
                                     GTK_RESPONSE_CANCEL, FALSE);
  gtk_dialog_set_response_sensitive (GTK_DIALOG (save_dialog),
                                     GTK_RESPONSE_OK, FALSE);

  g_object_ref (dialog);

  use_name = (gimp_dialog_run (GIMP_DIALOG (dialog)) == GTK_RESPONSE_OK);

  gtk_widget_destroy (dialog);
  g_object_unref (dialog);

  gtk_dialog_set_response_sensitive (GTK_DIALOG (save_dialog),
                                     GTK_RESPONSE_CANCEL, TRUE);
  gtk_dialog_set_response_sensitive (GTK_DIALOG (save_dialog),
                                     GTK_RESPONSE_OK, TRUE);

  return use_name;
}

gboolean
file_save_dialog_save_image (GimpProgress        *progress,
                             Gimp                *ammoos,
                             GimpImage           *image,
                             GFile               *file,
                             GimpPlugInProcedure *save_proc,
                             GimpRunMode          run_mode,
                             gboolean             change_saved_state,
                             gboolean             export_backward,
                             gboolean             export_forward,
                             gboolean             xcf_compression,
                             gboolean             verbose_cancel)
{
  GimpPDBStatusType  status;
  GError            *error   = NULL;
  GList             *list;
  gboolean           success = FALSE;

  for (list = gimp_action_groups_from_name ("file");
       list;
       list = g_list_next (list))
    {
      gimp_action_group_set_action_sensitive (list->data, "file-quit", FALSE, NULL);
    }

  gimp_image_set_xcf_compression (image, xcf_compression);

  /* The save may fail and the progress widget be already freed if we
   * close the main window while the save dialog is running. So add a
   * weak pointer to avoid sending an error message to an already-freed
   * GimpProgress. See #11922.
   */
  g_object_add_weak_pointer (G_OBJECT (progress), (gpointer *) &progress);

  status = file_save (ammoos, image, progress, file,
                      save_proc, run_mode,
                      change_saved_state, export_backward, export_forward,
                      &error);

  switch (status)
    {
    case GIMP_PDB_SUCCESS:
      success = TRUE;
      break;

    case GIMP_PDB_CANCEL:
      if (verbose_cancel && progress)
        gimp_message_literal (ammoos,
                              G_OBJECT (progress), GIMP_MESSAGE_INFO,
                              _("Saving canceled"));
      break;

    default:
      {
        if (progress)
          gimp_message (ammoos, G_OBJECT (progress), GIMP_MESSAGE_ERROR,
                        _("Saving '%s' failed:\n\n%s"),
                        gimp_file_get_utf8_name (file),
                        error ? error->message : _("Unknown error"));
        g_clear_error (&error);
      }
      break;
    }

  if (progress)
    g_object_remove_weak_pointer (G_OBJECT (progress), (gpointer *) &progress);

  for (list = gimp_action_groups_from_name ("file");
       list;
       list = g_list_next (list))
    {
      gimp_action_group_set_action_sensitive (list->data, "file-quit", TRUE, NULL);
    }

  return success;
}

/* --- fill-dialog.c --- */
/* AmmoOS Image - The AmmoOS Field Image Research
 * Copyright (C) 1995 Spencer Kimball and Peter Mattis
 *
 * fill-dialog.c
 * Copyright (C) 2016  Michael Natterer <mitch@ammoos.org>
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

#include "libgimpconfig/gimpconfig.h"
#include "libgimpwidgets/gimpwidgets.h"

#include "dialogs-types.h"

#include "core/gimpdrawable.h"
#include "core/gimpfilloptions.h"

#include "widgets/gimpfilleditor.h"
#include "widgets/gimpviewabledialog.h"

#include "fill-dialog.h"

#include "ammoos-intl.h"


#define RESPONSE_RESET 1


typedef struct _FillDialog FillDialog;

struct _FillDialog
{
  GList            *items;
  GList            *drawables;
  GimpContext      *context;
  GimpFillOptions  *options;
  GimpFillCallback  callback;
  gpointer          user_data;
};


/*  local function prototypes  */

static void  fill_dialog_free     (FillDialog *private);
static void  fill_dialog_response (GtkWidget  *dialog,
                                   gint        response_id,
                                   FillDialog *private);


/*  public function  */

GtkWidget *
fill_dialog_new (GList            *items,
                 GList            *drawables,
                 GimpContext      *context,
                 const gchar      *title,
                 const gchar      *icon_name,
                 const gchar      *help_id,
                 GtkWidget        *parent,
                 GimpFillOptions  *options,
                 GimpFillCallback  callback,
                 gpointer          user_data)
{
  FillDialog *private;
  GtkWidget  *dialog;
  GtkWidget  *main_vbox;
  GtkWidget  *fill_editor;

  g_return_val_if_fail (items, NULL);
  g_return_val_if_fail (drawables, NULL);
  g_return_val_if_fail (GIMP_IS_CONTEXT (context), NULL);
  g_return_val_if_fail (GIMP_IS_FILL_OPTIONS (options), NULL);
  g_return_val_if_fail (icon_name != NULL, NULL);
  g_return_val_if_fail (help_id != NULL, NULL);
  g_return_val_if_fail (parent == NULL || GTK_IS_WIDGET (parent), NULL);
  g_return_val_if_fail (callback != NULL, NULL);

  private = g_slice_new0 (FillDialog);

  private->items     = g_list_copy (items);
  private->drawables = g_list_copy (drawables);
  private->context   = context;
  private->options   = gimp_fill_options_new (context->ammoos, context, TRUE);
  private->callback  = callback;
  private->user_data = user_data;

  gimp_config_sync (G_OBJECT (options),
                    G_OBJECT (private->options), 0);

  dialog = gimp_viewable_dialog_new (g_list_copy (items), context,
                                     title, "ammoos-fill-options",
                                     icon_name,
                                     _("Choose Fill Style"),
                                     parent,
                                     gimp_standard_help_func,
                                     help_id,

                                     _("_Reset"),  RESPONSE_RESET,
                                     _("_Cancel"), GTK_RESPONSE_CANCEL,
                                     _("_Fill"),   GTK_RESPONSE_OK,

                                     NULL);

  gimp_dialog_set_alternative_button_order (GTK_DIALOG (dialog),
                                           RESPONSE_RESET,
                                           GTK_RESPONSE_OK,
                                           GTK_RESPONSE_CANCEL,
                                           -1);

  gtk_window_set_resizable (GTK_WINDOW (dialog), FALSE);

  g_object_weak_ref (G_OBJECT (dialog),
                     (GWeakNotify) fill_dialog_free, private);

  g_signal_connect (dialog, "response",
                    G_CALLBACK (fill_dialog_response),
                    private);

  main_vbox = gtk_box_new (GTK_ORIENTATION_VERTICAL, 12);
  gtk_container_set_border_width (GTK_CONTAINER (main_vbox), 12);
  gtk_box_pack_start (GTK_BOX (gtk_dialog_get_content_area (GTK_DIALOG (dialog))),
                      main_vbox, TRUE, TRUE, 0);
  gtk_widget_set_visible (main_vbox, TRUE);

  fill_editor = gimp_fill_editor_new (private->options, FALSE, FALSE);
  gtk_box_pack_start (GTK_BOX (main_vbox), fill_editor, FALSE, FALSE, 0);
  gtk_widget_set_visible (fill_editor, TRUE);

  return dialog;
}


/*  private functions  */

static void
fill_dialog_free (FillDialog *private)
{
  g_object_unref (private->options);
  g_list_free (private->drawables);
  g_list_free (private->items);

  g_slice_free (FillDialog, private);
}

static void
fill_dialog_response (GtkWidget  *dialog,
                      gint        response_id,
                      FillDialog *private)
{
  switch (response_id)
    {
    case RESPONSE_RESET:
      gimp_config_reset (GIMP_CONFIG (private->options));
      break;

    case GTK_RESPONSE_OK:
      private->callback (dialog,
                         private->items,
                         private->drawables,
                         private->context,
                         private->options,
                         private->user_data);
      break;

    default:
      gtk_widget_destroy (dialog);
      break;
    }
}

/* --- grid-dialog.c --- */
/* AmmoOS Image - The AmmoOS Field Image Research
 * Copyright (C) 1995 Spencer Kimball and Peter Mattis
 *
 * Copyright (C) 2003  Henrik Brix Andersen <brix@ammoos.org>
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

#include "libgimpbase/gimpbase.h"
#include "libgimpconfig/gimpconfig.h"
#include "libgimpwidgets/gimpwidgets.h"

#include "dialogs-types.h"

#include "config/gimpcoreconfig.h"

#include "core/ammoos.h"
#include "core/gimpcontext.h"
#include "core/gimpimage.h"
#include "core/gimpimage-grid.h"
#include "core/gimpimage-undo.h"
#include "core/gimpimage-undo-push.h"
#include "core/gimpgrid.h"

#include "widgets/gimpgrideditor.h"
#include "widgets/gimphelp-ids.h"
#include "widgets/gimpviewabledialog.h"

#include "grid-dialog.h"

#include "ammoos-intl.h"


#define GRID_RESPONSE_RESET 1


typedef struct _GridDialog GridDialog;

struct _GridDialog
{
  GimpImage *image;
  GimpGrid  *grid;
  GimpGrid  *grid_backup;
};


/*  local functions  */

static void   grid_dialog_free     (GridDialog *private);
static void   grid_dialog_response (GtkWidget  *dialog,
                                    gint        response_id,
                                    GridDialog *private);


/*  public function  */

GtkWidget *
grid_dialog_new (GimpImage   *image,
                 GimpContext *context,
                 GtkWidget   *parent)
{
  GridDialog *private;
  GtkWidget  *dialog;
  GtkWidget  *editor;
  gdouble     xres;
  gdouble     yres;

  g_return_val_if_fail (GIMP_IS_IMAGE (image), NULL);
  g_return_val_if_fail (GIMP_IS_CONTEXT (context), NULL);
  g_return_val_if_fail (parent == NULL || GTK_IS_WIDGET (parent), NULL);

  private = g_slice_new0 (GridDialog);

  private->image       = image;
  private->grid        = gimp_image_get_grid (image);
  private->grid_backup = gimp_config_duplicate (GIMP_CONFIG (private->grid));

  dialog = gimp_viewable_dialog_new (g_list_prepend (NULL, image), context,
                                     _("Configure Grid"), "ammoos-grid-configure",
                                     GIMP_ICON_GRID, _("Configure Image Grid"),
                                     parent,
                                     gimp_standard_help_func,
                                     GIMP_HELP_IMAGE_GRID,

                                     _("_Reset"),  GRID_RESPONSE_RESET,
                                     _("_Cancel"), GTK_RESPONSE_CANCEL,
                                     _("_OK"),     GTK_RESPONSE_OK,

                                     NULL);

  gimp_dialog_set_alternative_button_order (GTK_DIALOG (dialog),
                                           GRID_RESPONSE_RESET,
                                           GTK_RESPONSE_OK,
                                           GTK_RESPONSE_CANCEL,
                                           -1);

  gtk_window_set_resizable (GTK_WINDOW (dialog), FALSE);

  g_object_weak_ref (G_OBJECT (dialog),
                     (GWeakNotify) grid_dialog_free, private);

  g_signal_connect (dialog, "response",
                    G_CALLBACK (grid_dialog_response),
                    private);

  gimp_image_get_resolution (image, &xres, &yres);

  editor = gimp_grid_editor_new (private->grid, context, xres, yres);
  gtk_container_set_border_width (GTK_CONTAINER (editor), 12);
  gtk_box_pack_start (GTK_BOX (gtk_dialog_get_content_area (GTK_DIALOG (dialog))),
                      editor, TRUE, TRUE, 0);

  gtk_widget_set_visible (editor, TRUE);

  return dialog;
}


/*  local functions  */

static void
grid_dialog_free (GridDialog *private)
{
  g_object_unref (private->grid_backup);

  g_slice_free (GridDialog, private);
}

static void
grid_dialog_response (GtkWidget  *dialog,
                      gint        response_id,
                      GridDialog *private)
{
  switch (response_id)
    {
    case GRID_RESPONSE_RESET:
      gimp_config_sync (G_OBJECT (private->image->ammoos->config->default_grid),
                        G_OBJECT (private->grid), 0);
      break;

    case GTK_RESPONSE_OK:
      if (! gimp_config_is_equal_to (GIMP_CONFIG (private->grid_backup),
                                     GIMP_CONFIG (private->grid)))
        {
          gimp_image_undo_push_image_grid (private->image, _("Grid"),
                                           private->grid_backup);
          gimp_image_flush (private->image);
        }

      gtk_widget_destroy (dialog);
      break;

    default:
      gimp_image_set_grid (private->image, private->grid_backup, FALSE);
      gtk_widget_destroy (dialog);
    }
}

/* --- image-merge-layers-dialog.c --- */
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

#include "libgimpwidgets/gimpwidgets.h"

#include "dialogs-types.h"

#include "core/gimpcontext.h"
#include "core/gimpimage.h"
#include "core/gimpitemstack.h"

#include "widgets/gimphelp-ids.h"
#include "widgets/gimpviewabledialog.h"

#include "image-merge-layers-dialog.h"

#include "ammoos-intl.h"


typedef struct _ImageMergeLayersDialog ImageMergeLayersDialog;

struct _ImageMergeLayersDialog
{
  GimpImage               *image;
  GimpContext             *context;
  GimpMergeType            merge_type;
  gboolean                 merge_active_group;
  gboolean                 discard_invisible;
  GimpMergeLayersCallback  callback;
  gpointer                 user_data;
};


/*  local function prototypes  */

static void  image_merge_layers_dialog_free     (ImageMergeLayersDialog *private);
static void  image_merge_layers_dialog_response (GtkWidget              *dialog,
                                                 gint                    response_id,
                                                 ImageMergeLayersDialog *private);


/*  public functions  */

GtkWidget *
image_merge_layers_dialog_new (GimpImage               *image,
                               GimpContext             *context,
                               GtkWidget               *parent,
                               GimpMergeType            merge_type,
                               gboolean                 merge_active_group,
                               gboolean                 discard_invisible,
                               GimpMergeLayersCallback  callback,
                               gpointer                 user_data)
{
  ImageMergeLayersDialog *private;
  GtkWidget              *dialog;
  GtkWidget              *vbox;
  GtkWidget              *frame;
  GtkWidget              *button;

  g_return_val_if_fail (GIMP_IS_IMAGE (image), NULL);
  g_return_val_if_fail (GIMP_IS_CONTEXT (context), NULL);

  private = g_slice_new0 (ImageMergeLayersDialog);

  private->image              = image;
  private->context            = context;
  private->merge_type         = merge_type;
  private->merge_active_group = merge_active_group;
  private->discard_invisible  = discard_invisible;
  private->callback           = callback;
  private->user_data          = user_data;

  dialog = gimp_viewable_dialog_new (g_list_prepend (NULL, image), context,
                                     _("Merge Layers"), "ammoos-image-merge-layers",
                                     GIMP_ICON_LAYER_MERGE_DOWN,
                                     _("Layers Merge Options"),
                                     parent,
                                     gimp_standard_help_func,
                                     GIMP_HELP_IMAGE_MERGE_LAYERS,

                                     _("_Cancel"), GTK_RESPONSE_CANCEL,
                                     _("_Merge"),  GTK_RESPONSE_OK,

                                     NULL);

  gimp_dialog_set_alternative_button_order (GTK_DIALOG (dialog),
                                           GTK_RESPONSE_OK,
                                           GTK_RESPONSE_CANCEL,
                                           -1);

  gtk_window_set_resizable (GTK_WINDOW (dialog), FALSE);

  g_object_weak_ref (G_OBJECT (dialog),
                     (GWeakNotify) image_merge_layers_dialog_free, private);

  g_signal_connect (dialog, "response",
                    G_CALLBACK (image_merge_layers_dialog_response),
                    private);

  vbox = gtk_box_new (GTK_ORIENTATION_VERTICAL, 12);
  gtk_container_set_border_width (GTK_CONTAINER (vbox), 12);
  gtk_box_pack_start (GTK_BOX (gtk_dialog_get_content_area (GTK_DIALOG (dialog))),
                      vbox, TRUE, TRUE, 0);
  gtk_widget_set_visible (vbox, TRUE);

  frame =
    gimp_enum_radio_frame_new_with_range (GIMP_TYPE_MERGE_TYPE,
                                          GIMP_EXPAND_AS_NECESSARY,
                                          GIMP_CLIP_TO_BOTTOM_LAYER,
                                          gtk_label_new (_("Final, Merged Layer should be:")),
                                          G_CALLBACK (gimp_radio_button_update),
                                          &private->merge_type, NULL,
                                          &button);
  gimp_int_radio_group_set_active (GTK_RADIO_BUTTON (button),
                                   private->merge_type);
  gtk_box_pack_start (GTK_BOX (vbox), frame, FALSE, FALSE, 0);
  gtk_widget_set_visible (frame, TRUE);

  button = gtk_check_button_new_with_mnemonic (_("Merge within active _groups only"));
  gtk_toggle_button_set_active (GTK_TOGGLE_BUTTON (button),
                                private->merge_active_group);
  gtk_box_pack_start (GTK_BOX (vbox), button, FALSE, FALSE, 0);
  gtk_widget_set_visible (button, TRUE);

  g_signal_connect (button, "toggled",
                    G_CALLBACK (gimp_toggle_button_update),
                    &private->merge_active_group);

  if (gimp_item_stack_is_flat (GIMP_ITEM_STACK (gimp_image_get_layers (image))))
    gtk_widget_set_sensitive (button, FALSE);

  button = gtk_check_button_new_with_mnemonic (_("_Discard invisible layers"));
  gtk_toggle_button_set_active (GTK_TOGGLE_BUTTON (button),
                                private->discard_invisible);
  gtk_box_pack_start (GTK_BOX (vbox), button, FALSE, FALSE, 0);
  gtk_widget_set_visible (button, TRUE);

  g_signal_connect (button, "toggled",
                    G_CALLBACK (gimp_toggle_button_update),
                    &private->discard_invisible);

  return dialog;
}


/*  private functions  */

static void
image_merge_layers_dialog_free (ImageMergeLayersDialog *private)
{
  g_slice_free (ImageMergeLayersDialog, private);
}

static void
image_merge_layers_dialog_response (GtkWidget              *dialog,
                                    gint                    response_id,
                                    ImageMergeLayersDialog *private)
{
  if (response_id == GTK_RESPONSE_OK)
    {
      private->callback (dialog,
                         private->image,
                         private->context,
                         private->merge_type,
                         private->merge_active_group,
                         private->discard_invisible,
                         private->user_data);
    }
  else
    {
      gtk_widget_destroy (dialog);
    }
}

/* --- image-new-dialog.c --- */
/* AmmoOS Image - The AmmoOS Field Image Research
 * Copyright (C) 1995-1999 Spencer Kimball and Peter Mattis
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

#include <gegl.h>
#include <gtk/gtk.h>

#include "libgimpbase/gimpbase.h"
#include "libgimpconfig/gimpconfig.h"
#include "libgimpwidgets/gimpwidgets.h"

#include "dialogs-types.h"

#include "config/gimpguiconfig.h"

#include "core/ammoos.h"
#include "core/gimpcontext.h"
#include "core/gimpimage.h"
#include "core/gimpimage-new.h"
#include "core/gimptemplate.h"

#include "widgets/gimpcontainercombobox.h"
#include "widgets/gimphelp-ids.h"
#include "widgets/gimpmessagebox.h"
#include "widgets/gimpmessagedialog.h"
#include "widgets/gimptemplateeditor.h"
#include "widgets/gimpwidgets-utils.h"

#include "image-new-dialog.h"

#include "ammoos-intl.h"


#define RESPONSE_RESET 1

typedef struct
{
  GtkWidget    *dialog;
  GtkWidget    *confirm_dialog;

  GtkWidget    *combo;
  GtkWidget    *editor;

  GimpContext  *context;
  GimpTemplate *template;
} ImageNewDialog;


/*  local function prototypes  */

static void   image_new_dialog_free      (ImageNewDialog *private);
static void   image_new_dialog_response  (GtkWidget      *widget,
                                          gint            response_id,
                                          ImageNewDialog *private);
static void   image_new_template_changed (GimpContext    *context,
                                          GimpTemplate   *template,
                                          ImageNewDialog *private);
static void   image_new_confirm_dialog   (ImageNewDialog *private);
static void   image_new_create_image     (ImageNewDialog *private);


/*  public functions  */

GtkWidget *
image_new_dialog_new (GimpContext *context)
{
  ImageNewDialog *private;
  GtkWidget      *dialog;
  GtkWidget      *main_vbox;
  GtkWidget      *hbox;
  GtkWidget      *label;
  GimpSizeEntry  *entry;

  g_return_val_if_fail (GIMP_IS_CONTEXT (context), NULL);

  private = g_slice_new0 (ImageNewDialog);

  private->context  = gimp_context_new (context->ammoos, "image-new-dialog",
                                        context);
  private->template = g_object_new (GIMP_TYPE_TEMPLATE, NULL);

  private->dialog = dialog =
    gimp_dialog_new (_("Create a New Image"),
                     "ammoos-image-new",
                     NULL, 0,
                     gimp_standard_help_func, GIMP_HELP_FILE_NEW,

                     _("_Reset"),  RESPONSE_RESET,
                     _("_Cancel"), GTK_RESPONSE_CANCEL,
                     _("_OK"),     GTK_RESPONSE_OK,

                     NULL);
  gtk_dialog_set_default_response (GTK_DIALOG (dialog), GTK_RESPONSE_OK);

  gimp_dialog_set_alternative_button_order (GTK_DIALOG (dialog),
                                           RESPONSE_RESET,
                                           GTK_RESPONSE_OK,
                                           GTK_RESPONSE_CANCEL,
                                           -1);

  gtk_window_set_resizable (GTK_WINDOW (dialog), FALSE);

  g_object_set_data_full (G_OBJECT (dialog),
                          "ammoos-image-new-dialog", private,
                          (GDestroyNotify) image_new_dialog_free);

  g_signal_connect_after (dialog, "response",
                          G_CALLBACK (image_new_dialog_response),
                          private);

  main_vbox = gtk_box_new (GTK_ORIENTATION_VERTICAL, 12);
  gtk_container_set_border_width (GTK_CONTAINER (main_vbox), 12);
  gtk_box_pack_start (GTK_BOX (gtk_dialog_get_content_area (GTK_DIALOG (dialog))),
                      main_vbox, TRUE, TRUE, 0);
  gtk_widget_set_visible (main_vbox, TRUE);

  /*  The template combo  */
  hbox = gtk_box_new (GTK_ORIENTATION_HORIZONTAL, 6);
  gtk_box_pack_start (GTK_BOX (main_vbox), hbox, FALSE, FALSE, 0);
  gtk_widget_set_visible (hbox, TRUE);

  label = gtk_label_new_with_mnemonic (_("_Template:"));
  gtk_box_pack_start (GTK_BOX (hbox), label, FALSE, FALSE, 0);
  gtk_widget_set_visible (label, TRUE);

  private->combo = g_object_new (GIMP_TYPE_CONTAINER_COMBO_BOX,
                                 "container",         context->ammoos->templates,
                                 "context",           private->context,
                                 "view-size",         16,
                                 "view-border-width", 0,
                                 "ellipsize",         PANGO_ELLIPSIZE_NONE,
                                 "focus-on-click",    FALSE,
                                 NULL);
  gtk_box_pack_start (GTK_BOX (hbox), private->combo, TRUE, TRUE, 0);
  gtk_widget_set_visible (private->combo, TRUE);

  gtk_label_set_mnemonic_widget (GTK_LABEL (label), private->combo);

  g_signal_connect (private->context, "template-changed",
                    G_CALLBACK (image_new_template_changed),
                    private);

  /*  Template editor  */
  private->editor = gimp_template_editor_new (private->template, context->ammoos,
                                              FALSE);
  gtk_box_pack_start (GTK_BOX (main_vbox), private->editor, FALSE, FALSE, 0);
  gtk_widget_set_visible (private->editor, TRUE);

  entry = GIMP_SIZE_ENTRY (gimp_template_editor_get_size_se (GIMP_TEMPLATE_EDITOR (private->editor)));
  gimp_size_entry_set_activates_default (entry, TRUE);
  gimp_size_entry_grab_focus (entry);

  image_new_template_changed (private->context,
                              gimp_context_get_template (private->context),
                              private);

  return dialog;
}

void
image_new_dialog_set (GtkWidget    *dialog,
                      GimpImage    *image,
                      GimpTemplate *template)
{
  ImageNewDialog *private;

  g_return_if_fail (GIMP_IS_DIALOG (dialog));
  g_return_if_fail (image == NULL || GIMP_IS_IMAGE (image));
  g_return_if_fail (template == NULL || GIMP_IS_TEMPLATE (template));

  private = g_object_get_data (G_OBJECT (dialog), "ammoos-image-new-dialog");

  g_return_if_fail (private != NULL);

  gimp_context_set_template (private->context, template);

  if (! template)
    {
      template = gimp_image_new_get_last_template (private->context->ammoos,
                                                   image);

      image_new_template_changed (private->context, template, private);

      g_object_unref (template);
    }
}


/*  private functions  */

static void
image_new_dialog_free (ImageNewDialog *private)
{
  g_object_unref (private->context);
  g_object_unref (private->template);

  g_slice_free (ImageNewDialog, private);
}

static void
image_new_dialog_response (GtkWidget      *dialog,
                           gint            response_id,
                           ImageNewDialog *private)
{
  switch (response_id)
    {
    case RESPONSE_RESET:
      gimp_config_sync (G_OBJECT (private->context->ammoos->config->default_image),
                        G_OBJECT (private->template), 0);
      gimp_context_set_template (private->context, NULL);
      break;

    case GTK_RESPONSE_OK:
      if (gimp_template_get_initial_size (private->template) >
          GIMP_GUI_CONFIG (private->context->ammoos->config)->max_new_image_size)
        image_new_confirm_dialog (private);
      else
        image_new_create_image (private);
      break;

    default:
      gtk_widget_destroy (dialog);
      break;
    }
}

static void
image_new_template_changed (GimpContext    *context,
                            GimpTemplate   *template,
                            ImageNewDialog *private)
{
  GimpTemplateEditor *editor;
  GtkWidget          *chain;
  gdouble             xres, yres;
  gchar              *comment;

  if (! template)
    return;

  editor = GIMP_TEMPLATE_EDITOR (private->editor);
  chain  = gimp_template_editor_get_resolution_chain (editor);

  xres = gimp_template_get_resolution_x (template);
  yres = gimp_template_get_resolution_y (template);

  gimp_chain_button_set_active (GIMP_CHAIN_BUTTON (chain),
                                ABS (xres - yres) < GIMP_MIN_RESOLUTION);

  comment = (gchar *) gimp_template_get_comment (template);

  if (! comment || ! strlen (comment))
    comment = g_strdup (gimp_template_get_comment (private->template));
  else
    comment = NULL;

  /*  make sure the resolution values are copied first (see bug #546924)  */
  gimp_config_sync (G_OBJECT (template), G_OBJECT (private->template),
                    GIMP_TEMPLATE_PARAM_COPY_FIRST);
  gimp_config_sync (G_OBJECT (template), G_OBJECT (private->template), 0);

  if (comment)
    {
      g_object_set (private->template,
                    "comment", comment,
                    NULL);

      g_free (comment);
    }
}


/*  the confirm dialog  */

static void
image_new_confirm_response (GtkWidget      *dialog,
                            gint            response_id,
                            ImageNewDialog *private)
{
  gtk_widget_destroy (dialog);

  private->confirm_dialog = NULL;

  if (response_id == GTK_RESPONSE_OK)
    image_new_create_image (private);
  else
    gtk_widget_set_sensitive (private->dialog, TRUE);
}

static void
image_new_confirm_dialog (ImageNewDialog *private)
{
  GimpGuiConfig *config;
  GtkWidget     *dialog;
  gchar         *size;

  if (private->confirm_dialog)
    {
      gtk_window_present (GTK_WINDOW (private->confirm_dialog));
      return;
    }

  private->confirm_dialog =
    dialog = gimp_message_dialog_new (_("Confirm Image Size"),
                                      GIMP_ICON_DIALOG_WARNING,
                                      private->dialog,
                                      GTK_DIALOG_DESTROY_WITH_PARENT,
                                      gimp_standard_help_func, NULL,

                                      _("_Cancel"), GTK_RESPONSE_CANCEL,
                                      _("_OK"),     GTK_RESPONSE_OK,

                                      NULL);

  gimp_dialog_set_alternative_button_order (GTK_DIALOG (private->confirm_dialog),
                                           GTK_RESPONSE_OK,
                                           GTK_RESPONSE_CANCEL,
                                           -1);

  g_signal_connect (dialog, "response",
                    G_CALLBACK (image_new_confirm_response),
                    private);

  size = g_format_size (gimp_template_get_initial_size (private->template));
  gimp_message_box_set_primary_text (GIMP_MESSAGE_DIALOG (dialog)->box,
                                     _("You are trying to create an image "
                                       "with a size of %s."), size);
  g_free (size);

  config = GIMP_GUI_CONFIG (private->context->ammoos->config);
  size = g_format_size (config->max_new_image_size);
  gimp_message_box_set_text (GIMP_MESSAGE_DIALOG (dialog)->box,
                              _("An image of the chosen size will use more "
                                "memory than what is configured as "
                                "\"Maximum new image size\" in the Preferences "
                                "dialog (currently %s)."), size);
  g_free (size);

  gtk_widget_set_sensitive (private->dialog, FALSE);

  gtk_widget_set_visible (dialog, TRUE);
}

static void
image_new_create_image (ImageNewDialog *private)
{
  GimpTemplate *template = g_object_ref (private->template);
  Gimp         *ammoos     = private->context->ammoos;
  GimpImage    *image;

  gtk_widget_set_visible (private->dialog, FALSE);

  image = gimp_image_new_from_template (ammoos, template,
                                        gimp_get_user_context (ammoos));
  gimp_create_display (ammoos, image, gimp_template_get_unit (template), 1.0,
                       G_OBJECT (gimp_widget_get_monitor (private->dialog)));
  g_object_unref (image);

  gtk_widget_destroy (private->dialog);

  gimp_image_new_set_last_template (ammoos, template);

  g_object_unref (template);
}

/* --- image-properties-dialog.c --- */
/* AmmoOS Image - The AmmoOS Field Image Research
 * Copyright (C) 1995 Spencer Kimball and Peter Mattis
 *
 * image-properties-dialog.c
 * Copyright (C) 2005 Michael Natterer <mitch@ammoos.org>
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

#include <gegl.h>
#include <gtk/gtk.h>

#include "libgimpwidgets/gimpwidgets.h"

#include "dialogs-types.h"

#include "core/gimpcontext.h"
#include "core/gimpimage.h"

#include "widgets/gimphelp-ids.h"
#include "widgets/gimpimagecommenteditor.h"
#include "widgets/gimpimagepropview.h"
#include "widgets/gimpimageprofileview.h"
#include "widgets/gimpviewabledialog.h"

#include "image-properties-dialog.h"

#include "ammoos-intl.h"


GtkWidget *
image_properties_dialog_new (GimpImage   *image,
                             GimpContext *context,
                             GtkWidget   *parent)
{
  GtkWidget *dialog;
  GtkWidget *notebook;
  GtkWidget *view;

  g_return_val_if_fail (GIMP_IS_IMAGE (image), NULL);
  g_return_val_if_fail (GIMP_IS_CONTEXT (context), NULL);
  g_return_val_if_fail (parent == NULL || GTK_IS_WIDGET (parent), NULL);

  dialog = gimp_viewable_dialog_new (g_list_prepend (NULL, image), context,
                                     _("Image Properties"),
                                     "ammoos-image-properties",
                                     "dialog-information",
                                     _("Image Properties"),
                                     parent,
                                     gimp_standard_help_func,
                                     GIMP_HELP_IMAGE_PROPERTIES,

                                     _("_Close"), GTK_RESPONSE_CLOSE,

                                     NULL);

  gtk_dialog_set_default_response (GTK_DIALOG (dialog), GTK_RESPONSE_CLOSE);

  g_signal_connect (dialog, "response",
                    G_CALLBACK (gtk_widget_destroy),
                    NULL);

  notebook = gtk_notebook_new ();
  gtk_box_pack_start (GTK_BOX (gtk_dialog_get_content_area (GTK_DIALOG (dialog))),
                      notebook, FALSE, FALSE, 0);
  gtk_widget_set_visible (notebook, TRUE);

  view = gimp_image_prop_view_new (image);
  gtk_container_set_border_width (GTK_CONTAINER (view), 12);
  gtk_notebook_append_page (GTK_NOTEBOOK (notebook),
                            view, gtk_label_new_with_mnemonic (_("_Properties")));
  gtk_widget_set_visible (view, TRUE);

  view = gimp_image_profile_view_new (image);
  gtk_notebook_append_page (GTK_NOTEBOOK (notebook),
                            view, gtk_label_new_with_mnemonic (_("C_olor Profile")));
  gtk_widget_set_visible (view, TRUE);

  view = gimp_image_comment_editor_new (image);
  gtk_notebook_append_page (GTK_NOTEBOOK (notebook),
                            view, gtk_label_new_with_mnemonic (_("Co_mment")));
  gtk_widget_set_visible (view, TRUE);

  gtk_notebook_set_current_page (GTK_NOTEBOOK (notebook), 0);

  return dialog;
}

/* --- image-scale-dialog.c --- */
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

#include <string.h>

#include <gegl.h>
#include <gtk/gtk.h>

#include "libgimpbase/gimpbase.h"
#include "libgimpwidgets/gimpwidgets.h"

#include "dialogs-types.h"

#include "config/gimpguiconfig.h"

#include "core/ammoos.h"
#include "core/gimpcontext.h"
#include "core/gimpimage.h"
#include "core/gimpimage-scale.h"

#include "widgets/gimphelp-ids.h"
#include "widgets/gimpmessagebox.h"
#include "widgets/gimpmessagedialog.h"

#include "scale-dialog.h"

#include "image-scale-dialog.h"

#include "ammoos-intl.h"


typedef struct
{
  GtkWidget             *dialog;

  GimpImage             *image;

  gint                   width;
  gint                   height;
  GimpUnit              *unit;
  GimpInterpolationType  interpolation;
  gdouble                xresolution;
  gdouble                yresolution;
  GimpUnit              *resolution_unit;

  GimpScaleCallback      callback;
  gpointer               user_data;
} ImageScaleDialog;


/*  local function prototypes  */

static void        image_scale_dialog_free      (ImageScaleDialog      *private);
static void        image_scale_callback         (GtkWidget             *widget,
                                                 GimpViewable          *viewable,
                                                 gint                   width,
                                                 gint                   height,
                                                 GimpUnit              *unit,
                                                 GimpInterpolationType  interpolation,
                                                 gdouble                xresolution,
                                                 gdouble                yresolution,
                                                 GimpUnit              *resolution_unit,
                                                 gpointer               data);

static GtkWidget * image_scale_confirm_dialog   (ImageScaleDialog      *private);
static void        image_scale_confirm_large    (ImageScaleDialog      *private,
                                                 gint64                 new_memsize,
                                                 gint64                 max_memsize);
static void        image_scale_confirm_small    (ImageScaleDialog      *private);
static void        image_scale_confirm_response (GtkWidget             *widget,
                                                 gint                   response_id,
                                                 ImageScaleDialog      *private);


/*  public functions  */

GtkWidget *
image_scale_dialog_new (GimpImage             *image,
                        GimpContext           *context,
                        GtkWidget             *parent,
                        GimpUnit              *unit,
                        GimpInterpolationType  interpolation,
                        GimpScaleCallback      callback,
                        gpointer               user_data)
{
  ImageScaleDialog *private;

  g_return_val_if_fail (GIMP_IS_IMAGE (image), NULL);
  g_return_val_if_fail (GIMP_IS_CONTEXT (context), NULL);
  g_return_val_if_fail (callback != NULL, NULL);

  private = g_slice_new0 (ImageScaleDialog);

  private->image     = image;
  private->callback  = callback;
  private->user_data = user_data;

  private->dialog = scale_dialog_new (GIMP_VIEWABLE (image), context,
                                      C_("dialog-title", "Scale Image"),
                                      "ammoos-image-scale",
                                      parent,
                                      gimp_standard_help_func,
                                      GIMP_HELP_IMAGE_SCALE,
                                      unit,
                                      interpolation,
                                      image_scale_callback,
                                      private);

  g_object_weak_ref (G_OBJECT (private->dialog),
                     (GWeakNotify) image_scale_dialog_free, private);

  return private->dialog;
}


/*  private functions  */

static void
image_scale_dialog_free (ImageScaleDialog *private)
{
  g_slice_free (ImageScaleDialog, private);
}

static void
image_scale_callback (GtkWidget             *widget,
                      GimpViewable          *viewable,
                      gint                   width,
                      gint                   height,
                      GimpUnit              *unit,
                      GimpInterpolationType  interpolation,
                      gdouble                xresolution,
                      gdouble                yresolution,
                      GimpUnit              *resolution_unit,
                      gpointer               data)
{
  ImageScaleDialog        *private = data;
  GimpImage               *image   = GIMP_IMAGE (viewable);
  GimpImageScaleCheckType  scale_check;
  gint64                   max_memsize;
  gint64                   new_memsize;

  private->width           = width;
  private->height          = height;
  private->unit            = unit;
  private->interpolation   = interpolation;
  private->xresolution     = xresolution;
  private->yresolution     = yresolution;
  private->resolution_unit = resolution_unit;

  gtk_widget_set_sensitive (widget, FALSE);

  max_memsize = GIMP_GUI_CONFIG (image->ammoos->config)->max_new_image_size;

  scale_check = gimp_image_scale_check (image,
                                        width, height, max_memsize,
                                        &new_memsize);
  switch (scale_check)
    {
    case GIMP_IMAGE_SCALE_TOO_BIG:
      image_scale_confirm_large (private, new_memsize, max_memsize);
      break;

    case GIMP_IMAGE_SCALE_TOO_SMALL:
      image_scale_confirm_small (private);
      break;

    case GIMP_IMAGE_SCALE_OK:
      private->callback (private->dialog,
                         GIMP_VIEWABLE (private->image),
                         private->width,
                         private->height,
                         private->unit,
                         private->interpolation,
                         private->xresolution,
                         private->yresolution,
                         private->resolution_unit,
                         private->user_data);
      break;
    }
}

static GtkWidget *
image_scale_confirm_dialog (ImageScaleDialog *private)
{
  GtkWidget *widget;

  widget = gimp_message_dialog_new (_("Confirm Scaling"),
                                    GIMP_ICON_DIALOG_WARNING,
                                    private->dialog,
                                    GTK_DIALOG_DESTROY_WITH_PARENT,
                                    gimp_standard_help_func,
                                    GIMP_HELP_IMAGE_SCALE_WARNING,

                                    _("_Cancel"), GTK_RESPONSE_CANCEL,
                                    _("_Scale"),  GTK_RESPONSE_OK,

                                    NULL);

  gimp_dialog_set_alternative_button_order (GTK_DIALOG (widget),
                                           GTK_RESPONSE_OK,
                                           GTK_RESPONSE_CANCEL,
                                           -1);

  g_signal_connect (widget, "response",
                    G_CALLBACK (image_scale_confirm_response),
                    private);

  return widget;
}

static void
image_scale_confirm_large (ImageScaleDialog *private,
                           gint64            new_memsize,
                           gint64            max_memsize)
{
  GtkWidget *widget = image_scale_confirm_dialog (private);
  gchar     *size;

  size = g_format_size (new_memsize);
  gimp_message_box_set_primary_text (GIMP_MESSAGE_DIALOG (widget)->box,
                                     _("You are trying to create an image "
                                       "with a size of %s."), size);
  g_free (size);

  size = g_format_size (max_memsize);
  gimp_message_box_set_text (GIMP_MESSAGE_DIALOG (widget)->box,
                             _("Scaling the image to the chosen size will "
                               "make it use more memory than what is "
                               "configured as \"Maximum new image size\" in "
                               "the Preferences dialog (currently %s)."), size);
  g_free (size);

  gtk_widget_set_visible (widget, TRUE);
}

static void
image_scale_confirm_small (ImageScaleDialog *private)
{
  GtkWidget *widget = image_scale_confirm_dialog (private);

  gimp_message_box_set_primary_text (GIMP_MESSAGE_DIALOG (widget)->box,
                                     _("Scaling the image to the chosen size "
                                       "will shrink some layers completely "
                                       "away."));
  gimp_message_box_set_text (GIMP_MESSAGE_DIALOG (widget)->box,
                             _("Is this what you want to do?"));

  gtk_widget_set_visible (widget, TRUE);
}

static void
image_scale_confirm_response (GtkWidget        *widget,
                              gint              response_id,
                              ImageScaleDialog *private)
{
  gtk_widget_destroy (widget);

  if (response_id == GTK_RESPONSE_OK)
    {
      private->callback (private->dialog,
                         GIMP_VIEWABLE (private->image),
                         private->width,
                         private->height,
                         private->unit,
                         private->interpolation,
                         private->xresolution,
                         private->yresolution,
                         private->resolution_unit,
                         private->user_data);
    }
  else
    {
      gtk_widget_set_sensitive (private->dialog, TRUE);
    }
}

/* --- input-devices-dialog.c --- */
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

#include "libgimpwidgets/gimpwidgets.h"

#include "dialogs-types.h"

#include "core/ammoos.h"

#include "widgets/gimpdeviceeditor.h"
#include "widgets/gimpdevicemanager.h"
#include "widgets/gimpdevices.h"
#include "widgets/gimphelp-ids.h"
#include "widgets/gimpmessagebox.h"
#include "widgets/gimpmessagedialog.h"

#include "input-devices-dialog.h"

#include "ammoos-intl.h"


/*  local function prototypes  */

static void   input_devices_dialog_response (GtkWidget *dialog,
                                             guint      response_id,
                                             Gimp      *ammoos);


/*  public functions  */

GtkWidget *
input_devices_dialog_new (Gimp *ammoos)
{
  GtkWidget *dialog;
  GtkWidget *content_area;
  GtkWidget *editor;

  g_return_val_if_fail (GIMP_IS_GIMP (ammoos), NULL);

  dialog = gimp_dialog_new (_("Configure Input Devices"),
                            "ammoos-input-devices-dialog",
                            NULL, 0,
                            gimp_standard_help_func,
                            GIMP_HELP_INPUT_DEVICES,

                            _("_Reset"),  GTK_RESPONSE_REJECT,
                            _("_Cancel"), GTK_RESPONSE_CANCEL,
                            _("_OK"),     GTK_RESPONSE_OK,

                            NULL);

  gimp_dialog_set_alternative_button_order (GTK_DIALOG (dialog),
                                            GTK_RESPONSE_REJECT,
                                            GTK_RESPONSE_OK,
                                            GTK_RESPONSE_CANCEL,
                                            -1);

  g_signal_connect (dialog, "response",
                    G_CALLBACK (input_devices_dialog_response),
                    ammoos);

  content_area = gtk_dialog_get_content_area (GTK_DIALOG (dialog));

  editor = gimp_device_editor_new (ammoos);
  gtk_container_set_border_width (GTK_CONTAINER (editor), 12);
  gtk_box_pack_start (GTK_BOX (content_area), editor, TRUE, TRUE, 0);
  gtk_widget_set_visible (editor, TRUE);

  return dialog;
}


/*  private functions  */

static void
input_devices_dialog_response (GtkWidget *dialog,
                               guint      response_id,
                               Gimp      *ammoos)
{
  switch (response_id)
    {
    case GTK_RESPONSE_OK:
      gimp_devices_save (ammoos, TRUE);
      break;

    case GTK_RESPONSE_DELETE_EVENT:
    case GTK_RESPONSE_CANCEL:
      gimp_devices_restore (ammoos);
      break;

    case GTK_RESPONSE_REJECT:
      {
        GtkWidget *confirm;

        confirm = gimp_message_dialog_new (_("Reset Input Device Configuration"),
                                           GIMP_ICON_DIALOG_QUESTION,
                                           dialog,
                                           GTK_DIALOG_MODAL |
                                           GTK_DIALOG_DESTROY_WITH_PARENT,
                                           gimp_standard_help_func, NULL,

                                           _("_Cancel"), GTK_RESPONSE_CANCEL,
                                           _("_Reset"),  GTK_RESPONSE_OK,

                                           NULL);

        gimp_dialog_set_alternative_button_order (GTK_DIALOG (confirm),
                                                  GTK_RESPONSE_OK,
                                                  GTK_RESPONSE_CANCEL,
                                                  -1);

        gimp_message_box_set_primary_text (GIMP_MESSAGE_DIALOG (confirm)->box,
                                           _("Do you really want to reset all "
                                             "input devices to default configuration?"));

        if (gimp_dialog_run (GIMP_DIALOG (confirm)) == GTK_RESPONSE_OK)
          {
            gimp_device_manager_reset (gimp_devices_get_manager (ammoos));
            gimp_devices_save (ammoos, TRUE);
            gimp_devices_restore (ammoos);
          }
        gtk_widget_destroy (confirm);
      }
      return;

    default:
      break;
    }

  gtk_widget_destroy (dialog);
}

/* --- item-options-dialog.c --- */
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

#include "libgimpbase/gimpbase.h"
#include "libgimpwidgets/gimpwidgets.h"

#include "dialogs-types.h"

#include "config/gimpcoreconfig.h"

#include "core/ammoos.h"
#include "core/gimpcontext.h"
#include "core/gimpimage.h"
#include "core/gimpitem.h"

#include "widgets/gimpviewabledialog.h"
#include "widgets/gimpwidgets-utils.h"

#include "item-options-dialog.h"

#include "ammoos-intl.h"


typedef struct _ItemOptionsDialog ItemOptionsDialog;

struct _ItemOptionsDialog
{
  GimpImage               *image;
  GimpItem                *item;
  GimpContext             *context;
  gboolean                 visible;
  GimpColorTag             color_tag;
  gboolean                 lock_content;
  gboolean                 lock_position;
  gboolean                 lock_visibility;
  GimpItemOptionsCallback  callback;
  gpointer                 user_data;

  GtkWidget               *left_vbox;
  GtkWidget               *left_grid;
  gint                     grid_row;
  GtkWidget               *name_entry;
  GtkWidget               *right_frame;
  GtkWidget               *right_vbox;
  GtkWidget               *lock_position_toggle;
};


/*  local function prototypes  */

static void        item_options_dialog_free          (ItemOptionsDialog *private);
static void        item_options_dialog_response      (GtkWidget         *dialog,
                                                      gint               response_id,
                                                      ItemOptionsDialog *private);
static GtkWidget * check_button_with_icon_new        (const gchar       *label,
                                                      const gchar       *icon_name,
                                                      GtkBox            *vbox);
static gint        check_button_get_bold_label_width (const gchar       *text);


/*  public functions  */

GtkWidget *
item_options_dialog_new (GimpImage               *image,
                         GimpItem                *item,
                         GimpContext             *context,
                         GtkWidget               *parent,
                         const gchar             *title,
                         const gchar             *role,
                         const gchar             *icon_name,
                         const gchar             *desc,
                         const gchar             *help_id,
                         const gchar             *name_label,
                         const gchar             *lock_content_icon_name,
                         const gchar             *lock_content_label,
                         const gchar             *lock_position_label,
                         const gchar             *lock_visibility_label,
                         const gchar             *item_name,
                         gboolean                 item_visible,
                         GimpColorTag             item_color_tag,
                         gboolean                 item_lock_content,
                         gboolean                 item_lock_position,
                         gboolean                 item_lock_visibility,
                         GimpItemOptionsCallback  callback,
                         gpointer                 user_data)
{
  ItemOptionsDialog *private;
  GtkWidget         *dialog;
  GimpViewable      *viewable;
  GtkWidget         *main_hbox;
  GtkWidget         *grid;
  GtkWidget         *button;

  g_return_val_if_fail (GIMP_IS_IMAGE (image), NULL);
  g_return_val_if_fail (item == NULL || GIMP_IS_ITEM (item), NULL);
  g_return_val_if_fail (GIMP_IS_CONTEXT (context), NULL);
  g_return_val_if_fail (GTK_IS_WIDGET (parent), NULL);
  g_return_val_if_fail (title != NULL, NULL);
  g_return_val_if_fail (role != NULL, NULL);
  g_return_val_if_fail (icon_name != NULL, NULL);
  g_return_val_if_fail (desc != NULL, NULL);
  g_return_val_if_fail (help_id != NULL, NULL);
  g_return_val_if_fail (callback != NULL, NULL);

  private = g_slice_new0 (ItemOptionsDialog);

  private->image           = image;
  private->item            = item;
  private->context         = context;
  private->visible         = item_visible;
  private->color_tag       = item_color_tag;
  private->lock_content    = item_lock_content;
  private->lock_position   = item_lock_position;
  private->lock_visibility = item_lock_visibility;
  private->callback        = callback;
  private->user_data       = user_data;

  if (item)
    viewable = GIMP_VIEWABLE (item);
  else
    viewable = GIMP_VIEWABLE (image);

  dialog = gimp_viewable_dialog_new (g_list_prepend (NULL, viewable), context,
                                     title, role, icon_name, desc,
                                     parent,
                                     gimp_standard_help_func, help_id,

                                     _("_Cancel"), GTK_RESPONSE_CANCEL,
                                     _("_OK"),     GTK_RESPONSE_OK,

                                     NULL);

  gtk_dialog_set_default_response (GTK_DIALOG (dialog), GTK_RESPONSE_OK);

  gimp_dialog_set_alternative_button_order (GTK_DIALOG (dialog),
                                           GTK_RESPONSE_OK,
                                           GTK_RESPONSE_CANCEL,
                                           -1);

  g_signal_connect (dialog, "response",
                    G_CALLBACK (item_options_dialog_response),
                    private);

  g_object_weak_ref (G_OBJECT (dialog),
                     (GWeakNotify) item_options_dialog_free, private);

  g_object_set_data (G_OBJECT (dialog), "item-options-dialog-private", private);

  main_hbox = gtk_box_new (GTK_ORIENTATION_HORIZONTAL, 12);
  gtk_container_set_border_width (GTK_CONTAINER (main_hbox), 12);
  gtk_box_pack_start (GTK_BOX (gtk_dialog_get_content_area (GTK_DIALOG (dialog))),
                      main_hbox, TRUE, TRUE, 0);
  gtk_widget_set_visible (main_hbox, TRUE);

  private->left_vbox = gtk_box_new (GTK_ORIENTATION_VERTICAL, 12);
  gtk_box_pack_start (GTK_BOX (main_hbox), private->left_vbox, TRUE, TRUE, 0);
  gtk_widget_set_visible (private->left_vbox, TRUE);

  private->left_grid = grid = gtk_grid_new ();
  gtk_grid_set_column_spacing (GTK_GRID (grid), 6);
  gtk_grid_set_row_spacing (GTK_GRID (grid), 6);
  gtk_box_pack_start (GTK_BOX (private->left_vbox), grid, FALSE, FALSE, 0);
  gtk_widget_set_visible (grid, TRUE);

  /*  The name label and entry  */
  if (name_label)
    {
      GtkWidget *radio;
      GtkWidget *radio_box;
      GList     *children;
      GList     *list;

      private->name_entry = gtk_entry_new ();
      gtk_entry_set_activates_default (GTK_ENTRY (private->name_entry), TRUE);
      gtk_entry_set_text (GTK_ENTRY (private->name_entry), item_name);
      gimp_grid_attach_aligned (GTK_GRID (grid), 0, private->grid_row++,
                                name_label, 0.0, 0.5,
                                private->name_entry, 1);
      /* Make the item name entry field have focus on creation */
      gtk_widget_grab_focus (private->name_entry);

      radio_box = gimp_enum_radio_box_new (GIMP_TYPE_COLOR_TAG,
                                           G_CALLBACK (gimp_radio_button_update),
                                           &private->color_tag, NULL,
                                           &radio);
      gtk_widget_set_name (radio_box, "ammoos-color-tag-box");
      gtk_orientable_set_orientation (GTK_ORIENTABLE (radio_box),
                                      GTK_ORIENTATION_HORIZONTAL);
      gimp_grid_attach_aligned (GTK_GRID (grid), 0, private->grid_row++,
                                _("Color tag:"), 0.0, 0.5,
                                radio_box, 1);

      gimp_int_radio_group_set_active (GTK_RADIO_BUTTON (radio),
                                       private->color_tag);

      children = gtk_container_get_children (GTK_CONTAINER (radio_box));

      for (list = children;
           list;
           list = g_list_next (list))
        {
          GimpColorTag  color_tag;
          GeglColor    *rgb = gegl_color_new ("none");
          GtkWidget    *image;

          radio = list->data;

          g_object_set (radio, "draw-indicator", FALSE, NULL);

          gtk_widget_destroy (gtk_bin_get_child (GTK_BIN (radio)));

          color_tag = GPOINTER_TO_INT (g_object_get_data (G_OBJECT (radio),
                                                          "ammoos-item-data"));

          if (gimp_get_color_tag_color (color_tag, rgb, FALSE))
            {
              gint w, h;

              image = gimp_color_area_new (rgb, GIMP_COLOR_AREA_FLAT, 0);
              gimp_color_area_set_color_config (GIMP_COLOR_AREA (image),
                                                context->ammoos->config->color_management);
              gtk_icon_size_lookup (GTK_ICON_SIZE_MENU, &w, &h);
              gtk_widget_set_size_request (image, w, h);
            }
          else
            {
              image = gtk_image_new_from_icon_name (GIMP_ICON_CLOSE,
                                                    GTK_ICON_SIZE_MENU);
            }
          g_object_unref (rgb);

          gtk_container_add (GTK_CONTAINER (radio), image);
          gtk_widget_set_visible (image, TRUE);
        }

      g_list_free (children);
    }

  /*  The switches frame & vbox  */

  private->right_frame = gimp_frame_new (_("Switches"));
  gtk_box_pack_start (GTK_BOX (main_hbox), private->right_frame,
                      FALSE, FALSE, 0);
  gtk_widget_set_visible (private->right_frame, TRUE);

  private->right_vbox = gtk_box_new (GTK_ORIENTATION_VERTICAL, 6);
  gtk_container_add (GTK_CONTAINER (private->right_frame), private->right_vbox);
  gtk_widget_set_visible (private->right_vbox, TRUE);

  button = check_button_with_icon_new (_("_Visible"),
                                       GIMP_ICON_VISIBLE,
                                       GTK_BOX (private->right_vbox));
  gtk_toggle_button_set_active (GTK_TOGGLE_BUTTON (button),
                                private->visible);
  g_signal_connect (button, "toggled",
                    G_CALLBACK (gimp_toggle_button_update),
                    &private->visible);

  button = check_button_with_icon_new (lock_content_label,
                                       lock_content_icon_name,
                                       GTK_BOX (private->right_vbox));
  gtk_toggle_button_set_active (GTK_TOGGLE_BUTTON (button),
                                private->lock_content);
  g_signal_connect (button, "toggled",
                    G_CALLBACK (gimp_toggle_button_update),
                    &private->lock_content);

  button = check_button_with_icon_new (lock_position_label,
                                       GIMP_ICON_LOCK_POSITION,
                                       GTK_BOX (private->right_vbox));
  gtk_toggle_button_set_active (GTK_TOGGLE_BUTTON (button),
                                private->lock_position);
  g_signal_connect (button, "toggled",
                    G_CALLBACK (gimp_toggle_button_update),
                    &private->lock_position);

  private->lock_position_toggle = button;

  button = check_button_with_icon_new (lock_visibility_label,
                                       GIMP_ICON_LOCK_VISIBILITY,
                                       GTK_BOX (private->right_vbox));
  gtk_toggle_button_set_active (GTK_TOGGLE_BUTTON (button),
                                private->lock_visibility);
  g_signal_connect (button, "toggled",
                    G_CALLBACK (gimp_toggle_button_update),
                    &private->lock_visibility);

  return dialog;
}

GtkWidget *
item_options_dialog_get_vbox (GtkWidget *dialog)
{
  ItemOptionsDialog *private;

  g_return_val_if_fail (GIMP_IS_VIEWABLE_DIALOG (dialog), NULL);

  private = g_object_get_data (G_OBJECT (dialog),
                               "item-options-dialog-private");

  g_return_val_if_fail (private != NULL, NULL);

  return private->left_vbox;
}

GtkWidget *
item_options_dialog_get_right_vbox (GtkWidget *dialog)
{
  ItemOptionsDialog *private;

  g_return_val_if_fail (GIMP_IS_VIEWABLE_DIALOG (dialog), NULL);

  private = g_object_get_data (G_OBJECT (dialog),
                               "item-options-dialog-private");

  g_return_val_if_fail (private != NULL, NULL);

  return private->right_vbox;
}

GtkWidget *
item_options_dialog_get_grid (GtkWidget *dialog,
                              gint      *next_row)
{
  ItemOptionsDialog *private;

  g_return_val_if_fail (GIMP_IS_VIEWABLE_DIALOG (dialog), NULL);
  g_return_val_if_fail (next_row != NULL, NULL);

  private = g_object_get_data (G_OBJECT (dialog),
                               "item-options-dialog-private");

  g_return_val_if_fail (private != NULL, NULL);

  *next_row = private->grid_row;

  return private->left_grid;
}

GtkWidget *
item_options_dialog_get_name_entry (GtkWidget *dialog)
{
  ItemOptionsDialog *private;

  g_return_val_if_fail (GIMP_IS_VIEWABLE_DIALOG (dialog), NULL);

  private = g_object_get_data (G_OBJECT (dialog),
                               "item-options-dialog-private");

  g_return_val_if_fail (private != NULL, NULL);

  return private->name_entry;
}

GtkWidget *
item_options_dialog_get_lock_position (GtkWidget *dialog)
{
  ItemOptionsDialog *private;

  g_return_val_if_fail (GIMP_IS_VIEWABLE_DIALOG (dialog), NULL);

  private = g_object_get_data (G_OBJECT (dialog),
                               "item-options-dialog-private");

  g_return_val_if_fail (private != NULL, NULL);

  return private->lock_position_toggle;
}

void
item_options_dialog_add_widget (GtkWidget   *dialog,
                                const gchar *label,
                                GtkWidget   *widget)
{
  ItemOptionsDialog *private;

  g_return_if_fail (GIMP_IS_VIEWABLE_DIALOG (dialog));
  g_return_if_fail (GTK_IS_WIDGET (widget));

  private = g_object_get_data (G_OBJECT (dialog),
                               "item-options-dialog-private");

  g_return_if_fail (private != NULL);

  gimp_grid_attach_aligned (GTK_GRID (private->left_grid),
                            0, private->grid_row++,
                            label, 0.0, 0.5,
                            widget, 1);
}

GtkWidget *
item_options_dialog_add_switch (GtkWidget   *dialog,
                                const gchar *icon_name,
                                const gchar *label)
{
  ItemOptionsDialog *private;

  g_return_val_if_fail (GIMP_IS_VIEWABLE_DIALOG (dialog), NULL);
  g_return_val_if_fail (icon_name != NULL, NULL);
  g_return_val_if_fail (label != NULL, NULL);

  private = g_object_get_data (G_OBJECT (dialog),
                               "item-options-dialog-private");

  g_return_val_if_fail (private != NULL, NULL);

  return check_button_with_icon_new (label, icon_name,
                                     GTK_BOX (private->right_vbox));
}

void
item_options_dialog_set_switches_visible (GtkWidget *dialog,
                                          gboolean   visible)
{
  ItemOptionsDialog *private;

  g_return_if_fail (GIMP_IS_VIEWABLE_DIALOG (dialog));

  private = g_object_get_data (G_OBJECT (dialog),
                               "item-options-dialog-private");

  g_return_if_fail (private != NULL);

  gtk_widget_set_visible (private->right_frame, visible);
}


/*  private functions  */

static void
item_options_dialog_free (ItemOptionsDialog *private)
{
  g_slice_free (ItemOptionsDialog, private);
}

static void
item_options_dialog_response (GtkWidget         *dialog,
                              gint               response_id,
                              ItemOptionsDialog *private)
{
  if (response_id == GTK_RESPONSE_OK)
    {
      const gchar *name = NULL;

      if (private->name_entry)
        name = gtk_entry_get_text (GTK_ENTRY (private->name_entry));

      private->callback (dialog,
                         private->image,
                         private->item,
                         private->context,
                         name,
                         private->visible,
                         private->color_tag,
                         private->lock_content,
                         private->lock_position,
                         private->lock_visibility,
                         private->user_data);
    }
  else
    {
      gtk_widget_destroy (dialog);
    }
}

static GtkWidget *
check_button_with_icon_new (const gchar *label,
                            const gchar *icon_name,
                            GtkBox      *vbox)
{
  GtkWidget *hbox;
  GtkWidget *button;
  GtkWidget *image;
  GtkWidget *label_widget;

  hbox = gtk_box_new (GTK_ORIENTATION_HORIZONTAL, 6);
  gtk_box_pack_start (vbox, hbox, FALSE, FALSE, 0);
  gtk_widget_set_visible (hbox, TRUE);

  image = gtk_image_new_from_icon_name (icon_name, GTK_ICON_SIZE_BUTTON);
  gtk_box_pack_start (GTK_BOX (hbox), image, FALSE, FALSE, 0);
  gtk_widget_set_visible (image, TRUE);

  button = gtk_check_button_new_with_mnemonic (label);
  gtk_box_pack_start (GTK_BOX (hbox), button, TRUE, TRUE, 0);
  gtk_widget_set_visible (button, TRUE);

  /* Resize the label to its bold size to avoid a GUI twitch */
  label_widget = gtk_bin_get_child (GTK_BIN (button));
  gtk_widget_set_size_request (label_widget,
                               check_button_get_bold_label_width (label),
                               -1);

  return button;
}

static gint
check_button_get_bold_label_width (const gchar *text)
{
  GtkWidget      *temp_label = gtk_label_new (NULL);
  GtkRequisition  natural_size;

  gtk_label_set_text (GTK_LABEL (temp_label), text);
  gtk_widget_set_visible (temp_label, TRUE);

  gimp_label_set_attributes (GTK_LABEL (temp_label),
                             PANGO_ATTR_WEIGHT, PANGO_WEIGHT_BOLD,
                             -1);

  gtk_widget_get_preferred_size (temp_label, NULL, &natural_size);
  gtk_widget_destroy (temp_label);

  return natural_size.width;
}

/* --- keyboard-shortcuts-dialog.c --- */
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

#include "libgimpwidgets/gimpwidgets.h"

#include "dialogs-types.h"

#include "core/ammoos.h"

#include "widgets/gimpactioneditor.h"
#include "widgets/gimphelp-ids.h"

#include "menus/menus.h"

#include "keyboard-shortcuts-dialog.h"

#include "ammoos-intl.h"


/*  local function prototypes  */

static void   keyboard_shortcuts_dialog_response (GtkWidget *dialog,
                                                  gint       response,
                                                  Gimp      *ammoos);


/*  public functions  */

GtkWidget *
keyboard_shortcuts_dialog_new (Gimp *ammoos)
{
  GtkWidget *dialog;
  GtkWidget *vbox;
  GtkWidget *editor;
  GtkWidget *box;
  GtkWidget *button;
  gchar     *hint;

  g_return_val_if_fail (GIMP_IS_GIMP (ammoos), NULL);

  dialog = gimp_dialog_new (_("Configure Keyboard Shortcuts"),
                            "ammoos-keyboard-shortcuts-dialog",
                            NULL, 0,
                            gimp_standard_help_func,
                            GIMP_HELP_KEYBOARD_SHORTCUTS,

                            _("_OK"), GTK_RESPONSE_OK,

                            NULL);

  g_signal_connect (dialog, "response",
                    G_CALLBACK (keyboard_shortcuts_dialog_response),
                    ammoos);

  vbox = gtk_box_new (GTK_ORIENTATION_VERTICAL, 12);
  gtk_container_set_border_width (GTK_CONTAINER (vbox), 12);
  gtk_box_pack_start (GTK_BOX (gtk_dialog_get_content_area (GTK_DIALOG (dialog))),
                      vbox, TRUE, TRUE, 0);
  gtk_widget_set_visible (vbox, TRUE);

  editor = gimp_action_editor_new (ammoos, NULL, TRUE);
  gtk_box_pack_start (GTK_BOX (vbox), editor, TRUE, TRUE, 0);
  gtk_widget_set_visible (editor, TRUE);

  hint = g_strdup_printf (_("To edit a shortcut key, select the "
                            "corresponding row, click on its \"%s\" "
                            "column and type a new accelerator, "
                            "or press backspace to clear."), _("Shortcut"));
  box = gimp_hint_box_new (hint);
  g_free (hint);

  gtk_box_pack_start (GTK_BOX (vbox), box, FALSE, FALSE, 0);
  gtk_widget_set_visible (box, TRUE);

  button = gimp_prop_check_button_new (G_OBJECT (ammoos->config), "save-accels",
                                       _("S_ave keyboard shortcuts on exit"));
  gtk_box_pack_start (GTK_BOX (vbox), button, FALSE, FALSE, 0);

  return dialog;
}


/*  private functions  */

static void
keyboard_shortcuts_dialog_response (GtkWidget *dialog,
                                    gint       response,
                                    Gimp      *ammoos)
{
  switch (response)
    {
    default:
      gtk_widget_destroy (dialog);
      break;
    }
}

/* --- layer-add-mask-dialog.c --- */
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

#include "libgimpwidgets/gimpwidgets.h"

#include "dialogs-types.h"

#include "core/ammoos.h"
#include "core/gimpchannel.h"
#include "core/gimpcontainer.h"
#include "core/gimpcontext.h"
#include "core/gimpimage.h"
#include "core/gimplayer.h"

#include "widgets/gimpcontainercombobox.h"
#include "widgets/gimpcontainerview.h"
#include "widgets/gimphelp-ids.h"
#include "widgets/gimpviewabledialog.h"
#include "widgets/gimpwidgets-utils.h"

#include "layer-add-mask-dialog.h"

#include "ammoos-intl.h"


typedef struct _LayerAddMaskDialog LayerAddMaskDialog;

struct _LayerAddMaskDialog
{
  GList               *layers;
  GimpAddMaskType      add_mask_type;
  GimpChannel         *channel;
  gboolean             invert;
  gboolean             edit_mask;
  GimpAddMaskCallback  callback;
  gpointer             user_data;
};


/*  local function prototypes  */

static void   layer_add_mask_dialog_free             (LayerAddMaskDialog *private);
static void   layer_add_mask_dialog_response         (GtkWidget          *dialog,
                                                      gint                response_id,
                                                      LayerAddMaskDialog *private);
static void   layer_add_mask_dialog_channel_selected (GimpContainerView  *view,
                                                      LayerAddMaskDialog *private);


/*  public functions  */

GtkWidget *
layer_add_mask_dialog_new (GList               *layers,
                           GimpContext         *context,
                           GtkWidget           *parent,
                           GimpAddMaskType      add_mask_type,
                           gboolean             invert,
                           gboolean             edit_mask,
                           GimpAddMaskCallback  callback,
                           gpointer             user_data)
{
  LayerAddMaskDialog *private;
  GtkWidget          *dialog;
  GtkWidget          *vbox;
  GtkWidget          *hbox;
  GtkWidget          *frame;
  GtkWidget          *combo;
  GtkWidget          *button;
  GimpImage          *image;
  GimpChannel        *channel;
  GList              *channels;
  gchar              *title;
  gchar              *desc;
  gint                n_layers = g_list_length (layers);

  g_return_val_if_fail (layers, NULL);
  g_return_val_if_fail (GTK_IS_WIDGET (parent), NULL);
  g_return_val_if_fail (GIMP_IS_CONTEXT (context), NULL);

  private = g_slice_new0 (LayerAddMaskDialog);

  private->layers        = layers;
  private->add_mask_type = add_mask_type;
  private->invert        = invert;
  private->edit_mask     = edit_mask;
  private->callback      = callback;
  private->user_data     = user_data;

  title = ngettext ("Add Layer Mask", "Add Layer Masks", n_layers);
  title = g_strdup_printf (title, n_layers);
  desc  = ngettext ("Add a Mask to the Layer", "Add Masks to %d Layers", n_layers);
  desc  = g_strdup_printf (desc, n_layers);

  dialog = gimp_viewable_dialog_new (layers, context,
                                     title,
                                     "ammoos-layer-add-mask",
                                     GIMP_ICON_LAYER_MASK,
                                     desc,
                                     parent,
                                     gimp_standard_help_func,
                                     GIMP_HELP_LAYER_MASK_ADD,

                                     _("_Cancel"), GTK_RESPONSE_CANCEL,
                                     _("_Add"),    GTK_RESPONSE_OK,

                                     NULL);

  g_free (title);
  g_free (desc);

  gimp_dialog_set_alternative_button_order (GTK_DIALOG (dialog),
                                           GTK_RESPONSE_OK,
                                           GTK_RESPONSE_CANCEL,
                                           -1);

  gtk_window_set_resizable (GTK_WINDOW (dialog), FALSE);

  g_object_weak_ref (G_OBJECT (dialog),
                     (GWeakNotify) layer_add_mask_dialog_free, private);

  g_signal_connect (dialog, "response",
                    G_CALLBACK (layer_add_mask_dialog_response),
                    private);

  vbox = gtk_box_new (GTK_ORIENTATION_VERTICAL, 12);
  gtk_container_set_border_width (GTK_CONTAINER (vbox), 12);
  gtk_box_pack_start (GTK_BOX (gtk_dialog_get_content_area (GTK_DIALOG (dialog))),
                      vbox, TRUE, TRUE, 0);
  gtk_widget_set_visible (vbox, TRUE);

  frame =
    gimp_enum_radio_frame_new (GIMP_TYPE_ADD_MASK_TYPE,
                               gtk_label_new (_("Initialize Layer Mask to:")),
                               G_CALLBACK (gimp_radio_button_update),
                               &private->add_mask_type, NULL,
                               &button);
  gimp_int_radio_group_set_active (GTK_RADIO_BUTTON (button),
                                   private->add_mask_type);

  gtk_box_pack_start (GTK_BOX (vbox), frame, FALSE, FALSE, 0);
  gtk_widget_set_visible (frame, TRUE);

  image = gimp_item_get_image (GIMP_ITEM (layers->data));

  combo = gimp_container_combo_box_new (gimp_image_get_channels (image),
                                        context,
                                        GIMP_VIEW_SIZE_SMALL, 1);
  gimp_enum_radio_frame_add (GTK_FRAME (frame), combo,
                             GIMP_ADD_MASK_CHANNEL, TRUE);
  gtk_widget_set_visible (combo, TRUE);

  g_signal_connect (combo, "selection-changed",
                    G_CALLBACK (layer_add_mask_dialog_channel_selected),
                    private);

  channels = gimp_image_get_selected_channels (image);
  if (channels)
    /* Mask dialog only requires one channel. Just take any of the
     * selected ones randomly.
     */
    channel = channels->data;
  else
    channel = GIMP_CHANNEL (gimp_container_get_first_child (gimp_image_get_channels (image)));

  gimp_container_view_set_1_selected (GIMP_CONTAINER_VIEW (combo),
                                      GIMP_VIEWABLE (channel));

  hbox = gtk_box_new (GTK_ORIENTATION_HORIZONTAL, 1);
  gtk_box_pack_end (GTK_BOX (vbox), hbox, FALSE, FALSE, 0);
  gtk_widget_set_visible (hbox, TRUE);

  button = gtk_check_button_new_with_mnemonic (_("In_vert mask"));
  gtk_toggle_button_set_active (GTK_TOGGLE_BUTTON (button), private->invert);
  gtk_box_pack_start (GTK_BOX (hbox), button, FALSE, FALSE, 0);
  gtk_widget_set_visible (button, TRUE);

  g_signal_connect (button, "toggled",
                    G_CALLBACK (gimp_toggle_button_update),
                    &private->invert);

  button = gtk_check_button_new_with_mnemonic (_("_Edit mask immediately"));
  gtk_toggle_button_set_active (GTK_TOGGLE_BUTTON (button), private->edit_mask);
  gtk_box_pack_end (GTK_BOX (hbox), button, FALSE, FALSE, 0);
  gtk_widget_set_visible (button, TRUE);

  g_signal_connect (button, "toggled",
                    G_CALLBACK (gimp_toggle_button_update),
                    &private->edit_mask);

  return dialog;
}


/*  private functions  */

static void
layer_add_mask_dialog_free (LayerAddMaskDialog *private)
{
  g_slice_free (LayerAddMaskDialog, private);
}

static void
layer_add_mask_dialog_response (GtkWidget          *dialog,
                                gint                response_id,
                                LayerAddMaskDialog *private)
{
  if (response_id == GTK_RESPONSE_OK)
    {
      GimpImage *image = gimp_item_get_image (GIMP_ITEM (private->layers->data));

      if (private->add_mask_type == GIMP_ADD_MASK_CHANNEL &&
          ! private->channel)
        {
          gimp_message_literal (image->ammoos,
                                G_OBJECT (dialog), GIMP_MESSAGE_WARNING,
                                _("Please select a channel first"));
          return;
        }

      private->callback (dialog,
                         private->layers,
                         private->add_mask_type,
                         private->channel,
                         private->invert,
                         private->edit_mask,
                         private->user_data);
    }
  else
    {
      gtk_widget_destroy (dialog);
    }
}

static void
layer_add_mask_dialog_channel_selected (GimpContainerView  *view,
                                        LayerAddMaskDialog *private)
{
  private->channel = GIMP_CHANNEL (gimp_container_view_get_1_selected (view));
}

/* --- layer-options-dialog.c --- */
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

#include "libgimpbase/gimpbase.h"
#include "libgimpmath/gimpmath.h"
#include "libgimpwidgets/gimpwidgets.h"

#include "dialogs-types.h"

#include "operations/layer-modes/ammoos-layer-modes.h"

#include "core/gimpcontext.h"
#include "core/gimpdrawable-filters.h"
#include "core/gimpimage.h"
#include "core/gimplayer.h"
#include "core/gimplink.h"
#include "core/gimplinklayer.h"
#include "core/gimprasterizable.h"

#include "path/gimppath.h"
#include "path/gimpvectorlayer.h"

#include "text/gimptext.h"
#include "text/gimptextlayer.h"

#include "widgets/gimpcontainercombobox.h"
#include "widgets/gimpcontainerlistview.h"
#include "widgets/gimpcontainerview.h"
#include "widgets/gimplayermodebox.h"
#include "widgets/gimpopendialog.h"
#include "widgets/gimpviewabledialog.h"

#include "item-options-dialog.h"
#include "layer-options-dialog.h"

#include "ammoos-intl.h"


typedef struct _LayerOptionsDialog LayerOptionsDialog;

struct _LayerOptionsDialog
{
  Gimp                     *ammoos;
  GimpLayer                *layer;
  GimpLayerMode             mode;
  GimpLayerColorSpace       blend_space;
  GimpLayerColorSpace       composite_space;
  GimpLayerCompositeMode    composite_mode;
  gdouble                   opacity;
  GimpFillType              fill_type;
  gboolean                  lock_alpha;
  gboolean                  rename_text_layers;
  GimpLayerOptionsCallback  callback;
  gpointer                  user_data;

  GtkWidget                *mode_box;
  GtkWidget                *blend_space_combo;
  GtkWidget                *composite_space_combo;
  GtkWidget                *composite_mode_combo;
  GtkWidget                *size_se;
  GtkWidget                *offset_se;

  GimpLink                 *link;
  GimpPath                 *initial_path;
};


/*  local function prototypes  */

static void   layer_options_dialog_free           (LayerOptionsDialog *private);
static void   layer_options_dialog_callback       (GtkWidget          *dialog,
                                                   GimpImage          *image,
                                                   GimpItem           *item,
                                                   GimpContext        *context,
                                                   const gchar        *item_name,
                                                   gboolean            item_visible,
                                                   GimpColorTag        item_color_tag,
                                                   gboolean            item_lock_content,
                                                   gboolean            item_lock_position,
                                                   gboolean            item_lock_visibility,
                                                   gpointer            user_data);
static void
     layer_options_dialog_update_mode_sensitivity (LayerOptionsDialog *private);
static void   layer_options_dialog_mode_notify    (GtkWidget          *widget,
                                                   const GParamSpec   *pspec,
                                                   LayerOptionsDialog *private);
static void   layer_options_dialog_rename_toggled (GtkWidget          *widget,
                                                   LayerOptionsDialog *private);

static void   layer_options_file_set              (GtkFileChooserButton *widget,
                                                   LayerOptionsDialog   *private);
static void   layer_options_dialog_path_selected  (GimpContainerView    *view,
                                                   LayerOptionsDialog   *private);


/*  public functions  */

GtkWidget *
layer_options_dialog_new (GimpImage                *image,
                          GimpLayer                *layer,
                          GimpContext              *context,
                          GtkWidget                *parent,
                          const gchar              *title,
                          const gchar              *role,
                          const gchar              *icon_name,
                          const gchar              *desc,
                          const gchar              *help_id,
                          const gchar              *layer_name,
                          GimpLayerMode             layer_mode,
                          GimpLayerColorSpace       layer_blend_space,
                          GimpLayerColorSpace       layer_composite_space,
                          GimpLayerCompositeMode    layer_composite_mode,
                          gdouble                   layer_opacity,
                          GimpFillType              layer_fill_type,
                          gboolean                  layer_visible,
                          GimpColorTag              layer_color_tag,
                          gboolean                  layer_lock_content,
                          gboolean                  layer_lock_position,
                          gboolean                  layer_lock_visibility,
                          gboolean                  layer_lock_alpha,
                          GimpLayerOptionsCallback  callback,
                          gpointer                  user_data)
{
  LayerOptionsDialog   *private;
  GtkWidget            *dialog;
  GtkWidget            *grid;
  GtkListStore         *space_model;
  GtkWidget            *combo;
  GtkWidget            *file_select;
  GtkWidget            *scale;
  GtkWidget            *label;
  GtkAdjustment        *adjustment;
  GtkWidget            *spinbutton;
  GtkWidget            *button;
  GimpLayerModeContext  mode_context;
  gdouble               xres;
  gdouble               yres;
  gint                  row = 0;

  g_return_val_if_fail (GIMP_IS_IMAGE (image), NULL);
  g_return_val_if_fail (layer == NULL || GIMP_IS_LAYER (layer), NULL);
  g_return_val_if_fail (GIMP_IS_CONTEXT (context), NULL);
  g_return_val_if_fail (GTK_IS_WIDGET (parent), NULL);

  private = g_slice_new0 (LayerOptionsDialog);

  private->ammoos               = image->ammoos;
  private->layer              = layer;
  private->mode               = layer_mode;
  private->blend_space        = layer_blend_space;
  private->composite_space    = layer_composite_space;
  private->composite_mode     = layer_composite_mode;
  private->opacity            = layer_opacity * 100.0;
  private->fill_type          = layer_fill_type;
  private->lock_alpha         = layer_lock_alpha;
  private->rename_text_layers = FALSE;
  private->callback           = callback;
  private->user_data          = user_data;

  private->link               = NULL;
  private->initial_path       = NULL;

  if (layer && gimp_item_is_text_layer (GIMP_ITEM (layer)))
    private->rename_text_layers = gimp_rasterizable_get_auto_rename (GIMP_RASTERIZABLE (layer));

  dialog = item_options_dialog_new (image, GIMP_ITEM (layer), context,
                                    parent, title, role,
                                    icon_name, desc, help_id,
                                    _("Layer _name:"),
                                    GIMP_ICON_LOCK_CONTENT,
                                    _("Lock _pixels"),
                                    _("Lock position and _size"),
                                    _("Lock visibility"),
                                    layer_name,
                                    layer_visible,
                                    layer_color_tag,
                                    layer_lock_content,
                                    layer_lock_position,
                                    layer_lock_visibility,
                                    layer_options_dialog_callback,
                                    private);

  g_object_weak_ref (G_OBJECT (dialog),
                     (GWeakNotify) layer_options_dialog_free, private);

  if (! layer || gimp_viewable_get_children (GIMP_VIEWABLE (layer)) == NULL)
    mode_context = GIMP_LAYER_MODE_CONTEXT_LAYER;
  else
    mode_context = GIMP_LAYER_MODE_CONTEXT_GROUP;

  private->mode_box = gimp_layer_mode_box_new (mode_context);
  item_options_dialog_add_widget (dialog, _("_Mode:"), private->mode_box);
  gimp_layer_mode_box_set_mode (GIMP_LAYER_MODE_BOX (private->mode_box),
                                private->mode);

  g_signal_connect (private->mode_box, "notify::layer-mode",
                    G_CALLBACK (layer_options_dialog_mode_notify),
                    private);

  space_model =
    gimp_enum_store_new_with_values (GIMP_TYPE_LAYER_COLOR_SPACE,
                                     4,
                                     GIMP_LAYER_COLOR_SPACE_AUTO,
                                     GIMP_LAYER_COLOR_SPACE_RGB_LINEAR,
                                     GIMP_LAYER_COLOR_SPACE_RGB_NON_LINEAR,
                                     GIMP_LAYER_COLOR_SPACE_RGB_PERCEPTUAL);

  private->blend_space_combo = combo =
    gimp_enum_combo_box_new_with_model (GIMP_ENUM_STORE (space_model));
  item_options_dialog_add_widget (dialog, _("_Blend space:"), combo);
  gimp_enum_combo_box_set_icon_prefix (GIMP_ENUM_COMBO_BOX (combo),
                                       "ammoos-layer-color-space");
  gimp_int_combo_box_connect (GIMP_INT_COMBO_BOX (combo),
                              private->blend_space,
                              G_CALLBACK (gimp_int_combo_box_get_active),
                              &private->blend_space, NULL);

  private->composite_space_combo = combo =
    gimp_enum_combo_box_new_with_model (GIMP_ENUM_STORE (space_model));
  item_options_dialog_add_widget (dialog, _("Compos_ite space:"), combo);
  gimp_enum_combo_box_set_icon_prefix (GIMP_ENUM_COMBO_BOX (combo),
                                       "ammoos-layer-color-space");
  gimp_int_combo_box_connect (GIMP_INT_COMBO_BOX (combo),
                              private->composite_space,
                              G_CALLBACK (gimp_int_combo_box_get_active),
                              &private->composite_space, NULL);

  g_object_unref (space_model);

  private->composite_mode_combo = combo =
    gimp_enum_combo_box_new (GIMP_TYPE_LAYER_COMPOSITE_MODE);
  item_options_dialog_add_widget (dialog, _("Composite mo_de:"), combo);
  gimp_enum_combo_box_set_icon_prefix (GIMP_ENUM_COMBO_BOX (combo),
                                       "ammoos-layer-composite");
  gimp_int_combo_box_connect (GIMP_INT_COMBO_BOX (combo),
                              private->composite_mode,
                              G_CALLBACK (gimp_int_combo_box_get_active),
                              &private->composite_mode, NULL);

  /*  set the sensitivity of above 3 menus  */
  layer_options_dialog_update_mode_sensitivity (private);

  adjustment = gtk_adjustment_new (private->opacity, 0.0, 100.0,
                                   1.0, 10.0, 0.0);
  scale = gimp_spin_scale_new (adjustment, NULL, 1);
  item_options_dialog_add_widget (dialog, _("_Opacity:"), scale);

  g_signal_connect (adjustment, "value-changed",
                    G_CALLBACK (gimp_double_adjustment_update),
                    &private->opacity);

  grid = item_options_dialog_get_grid (dialog, &row);

  gimp_image_get_resolution (image, &xres, &yres);

  if (! layer)
    {
      /*  The size labels  */
      label = gtk_label_new (_("Width:"));
      gtk_label_set_xalign (GTK_LABEL (label), 0.0);
      gtk_grid_attach (GTK_GRID (grid), label, 0, row, 1, 1);
      gtk_widget_set_visible (label, TRUE);

      label = gtk_label_new (_("Height:"));
      gtk_label_set_xalign (GTK_LABEL (label), 0.0);
      gtk_grid_attach (GTK_GRID (grid), label, 0, row + 1, 1, 1);
      gtk_widget_set_visible (label, TRUE);

      /*  The size sizeentry  */
      adjustment = gtk_adjustment_new (1, 1, 1, 1, 10, 0);
      spinbutton = gimp_spin_button_new (adjustment, 1.0, 2);
      gtk_spin_button_set_numeric (GTK_SPIN_BUTTON (spinbutton), TRUE);
      gtk_entry_set_width_chars (GTK_ENTRY (spinbutton), 10);

      private->size_se = gimp_size_entry_new (1, gimp_unit_pixel (), "%a",
                                              TRUE, TRUE, FALSE, 10,
                                              GIMP_SIZE_ENTRY_UPDATE_SIZE);

      gimp_size_entry_add_field (GIMP_SIZE_ENTRY (private->size_se),
                                 GTK_SPIN_BUTTON (spinbutton), NULL);
      gtk_grid_attach (GTK_GRID (private->size_se), spinbutton, 1, 0, 1, 1);
      gtk_widget_set_visible (spinbutton, TRUE);

      gtk_grid_attach (GTK_GRID (grid), private->size_se, 1, row, 1, 2);
      gtk_widget_set_visible (private->size_se, TRUE);

      gimp_size_entry_set_unit (GIMP_SIZE_ENTRY (private->size_se),
                                gimp_unit_pixel ());

      gimp_size_entry_set_resolution (GIMP_SIZE_ENTRY (private->size_se), 0,
                                      xres, FALSE);
      gimp_size_entry_set_resolution (GIMP_SIZE_ENTRY (private->size_se), 1,
                                      yres, FALSE);

      gimp_size_entry_set_refval_boundaries (GIMP_SIZE_ENTRY (private->size_se), 0,
                                             GIMP_MIN_IMAGE_SIZE,
                                             GIMP_MAX_IMAGE_SIZE);
      gimp_size_entry_set_refval_boundaries (GIMP_SIZE_ENTRY (private->size_se), 1,
                                             GIMP_MIN_IMAGE_SIZE,
                                             GIMP_MAX_IMAGE_SIZE);

      gimp_size_entry_set_size (GIMP_SIZE_ENTRY (private->size_se), 0,
                                0, gimp_image_get_width  (image));
      gimp_size_entry_set_size (GIMP_SIZE_ENTRY (private->size_se), 1,
                                0, gimp_image_get_height (image));

      gimp_size_entry_set_refval (GIMP_SIZE_ENTRY (private->size_se), 0,
                                  gimp_image_get_width  (image));
      gimp_size_entry_set_refval (GIMP_SIZE_ENTRY (private->size_se), 1,
                                  gimp_image_get_height (image));

      row += 2;
    }

  if (! layer || ! gimp_item_is_vector_layer (GIMP_ITEM (layer)))
    {
      /*  The offset labels  */
      label = gtk_label_new (_("Offset X:"));
      gtk_label_set_xalign (GTK_LABEL (label), 0.0);
      gtk_grid_attach (GTK_GRID (grid), label, 0, row, 1, 1);
      gtk_widget_set_visible (label, TRUE);

      label = gtk_label_new (_("Offset Y:"));
      gtk_label_set_xalign (GTK_LABEL (label), 0.0);
      gtk_grid_attach (GTK_GRID (grid), label, 0, row + 1, 1, 1);
      gtk_widget_set_visible (label, TRUE);

      /*  The offset sizeentry  */
      adjustment = gtk_adjustment_new (0, 1, 1, 1, 10, 0);
      spinbutton = gimp_spin_button_new (adjustment, 1.0, 2);
      gtk_spin_button_set_numeric (GTK_SPIN_BUTTON (spinbutton), TRUE);
      gtk_entry_set_width_chars (GTK_ENTRY (spinbutton), 10);

      private->offset_se = gimp_size_entry_new (1, gimp_unit_pixel (), "%a",
                                                TRUE, TRUE, FALSE, 10,
                                                GIMP_SIZE_ENTRY_UPDATE_SIZE);

      gimp_size_entry_add_field (GIMP_SIZE_ENTRY (private->offset_se),
                                 GTK_SPIN_BUTTON (spinbutton), NULL);
      gtk_grid_attach (GTK_GRID (private->offset_se), spinbutton, 1, 0, 1, 1);
      gtk_widget_set_visible (spinbutton, TRUE);

      gtk_grid_attach (GTK_GRID (grid), private->offset_se, 1, row, 1, 2);
      gtk_widget_set_visible (private->offset_se, TRUE);

      gimp_size_entry_set_unit (GIMP_SIZE_ENTRY (private->offset_se),
                                gimp_unit_pixel ());

      gimp_size_entry_set_resolution (GIMP_SIZE_ENTRY (private->offset_se), 0,
                                      xres, FALSE);
      gimp_size_entry_set_resolution (GIMP_SIZE_ENTRY (private->offset_se), 1,
                                      yres, FALSE);

      gimp_size_entry_set_refval_boundaries (GIMP_SIZE_ENTRY (private->offset_se), 0,
                                             -GIMP_MAX_IMAGE_SIZE,
                                             GIMP_MAX_IMAGE_SIZE);
      gimp_size_entry_set_refval_boundaries (GIMP_SIZE_ENTRY (private->offset_se), 1,
                                             -GIMP_MAX_IMAGE_SIZE,
                                             GIMP_MAX_IMAGE_SIZE);

      gimp_size_entry_set_size (GIMP_SIZE_ENTRY (private->offset_se), 0,
                                0, gimp_image_get_width  (image));
      gimp_size_entry_set_size (GIMP_SIZE_ENTRY (private->offset_se), 1,
                                0, gimp_image_get_height (image));

      if (layer)
        {
          gimp_size_entry_set_refval (GIMP_SIZE_ENTRY (private->offset_se), 0,
                                      gimp_item_get_offset_x (GIMP_ITEM (layer)));
          gimp_size_entry_set_refval (GIMP_SIZE_ENTRY (private->offset_se), 1,
                                      gimp_item_get_offset_y (GIMP_ITEM (layer)));
        }
      else
        {
          gimp_size_entry_set_refval (GIMP_SIZE_ENTRY (private->offset_se), 0, 0);
          gimp_size_entry_set_refval (GIMP_SIZE_ENTRY (private->offset_se), 1, 0);
        }

      row += 2;
    }

  if (layer)
    {
      GtkWidget     *left_vbox = item_options_dialog_get_vbox (dialog);
      GtkWidget     *frame;
      GimpContainer *filters;
      GtkWidget     *view;

      frame = gimp_frame_new (_("Active Filters"));
      gtk_box_pack_start (GTK_BOX (left_vbox), frame, TRUE, TRUE, 0);
      gtk_widget_set_visible (frame, TRUE);

      filters = gimp_drawable_get_filters (GIMP_DRAWABLE (layer));

      view = gimp_container_list_view_new (filters, context,
                                           GIMP_VIEW_SIZE_SMALL, 0);
      gtk_container_add (GTK_CONTAINER (frame), view);
      gtk_widget_set_visible (view, TRUE);

      if (gimp_item_is_link_layer (GIMP_ITEM (layer)))
        {
          GtkWidget *open_dialog;
          GimpLink  *link;

          /* File chooser dialog. */
          open_dialog = gimp_open_dialog_new (private->ammoos);
          gtk_window_set_title (GTK_WINDOW (open_dialog),
                                _("Select Linked Image"));

          /* File chooser button. */
          file_select = gtk_file_chooser_button_new_with_dialog (open_dialog);
          link = gimp_link_layer_get_link (GIMP_LINK_LAYER (layer));
          gtk_file_chooser_set_file (GTK_FILE_CHOOSER (file_select),
                                     gimp_link_get_file (link, NULL, NULL),
                                     NULL);
          gtk_widget_set_visible (file_select, TRUE);
          gimp_grid_attach_aligned (GTK_GRID (grid), 0, row++,
                                    _("_Linked image:"), 0.0, 0.5,
                                    file_select, 1);

          g_signal_connect (file_select, "file-set",
                            G_CALLBACK (layer_options_file_set),
                            private);

          private->link = gimp_link_duplicate (link);

          /* Absolute path checkbox. */
          button = gtk_check_button_new_with_mnemonic (_("S_tore with absolute path"));
          gimp_grid_attach_aligned (GTK_GRID (grid), 0, row++,
                                    NULL, 0.0, 0.5,
                                    button, 2);
          g_object_bind_property (G_OBJECT (private->link), "absolute-path",
                                  G_OBJECT (button),        "active",
                                  G_BINDING_SYNC_CREATE |
                                  G_BINDING_BIDIRECTIONAL);
          gtk_widget_set_visible (button, TRUE);
        }
      else if (gimp_item_is_vector_layer (GIMP_ITEM (layer)))
        {
          combo = gimp_container_combo_box_new (gimp_image_get_paths (image),
                                                context, GIMP_VIEW_SIZE_SMALL, 1);
          gimp_container_view_set_1_selected (GIMP_CONTAINER_VIEW (combo),
                                              GIMP_VIEWABLE (gimp_vector_layer_get_path (GIMP_VECTOR_LAYER (layer))));
          g_signal_connect (combo, "selection-changed",
                            G_CALLBACK (layer_options_dialog_path_selected),
                            private);
          gimp_grid_attach_aligned (GTK_GRID (grid), 0, row++,
                                    _("_Associated path:"), 0.0, 0.5,
                                    combo, 2);
          gtk_widget_set_visible (combo, TRUE);
        }
    }
  else
    {
      /*  The fill type  */
      combo = gimp_enum_combo_box_new (GIMP_TYPE_FILL_TYPE);
      gimp_grid_attach_aligned (GTK_GRID (grid), 0, row,
                                _("_Fill with:"), 0.0, 0.5,
                                combo, 1);
      gimp_int_combo_box_connect (GIMP_INT_COMBO_BOX (combo),
                                  private->fill_type,
                                  G_CALLBACK (gimp_int_combo_box_get_active),
                                  &private->fill_type, NULL);
    }

  button = item_options_dialog_get_lock_position (dialog);

  if (private->size_se)
    g_object_bind_property (G_OBJECT (button),           "active",
                            G_OBJECT (private->size_se), "sensitive",
                            G_BINDING_SYNC_CREATE |
                            G_BINDING_INVERT_BOOLEAN);

  if (private->offset_se)
    g_object_bind_property (G_OBJECT (button),             "active",
                            G_OBJECT (private->offset_se), "sensitive",
                            G_BINDING_SYNC_CREATE |
                            G_BINDING_INVERT_BOOLEAN);

  button = item_options_dialog_add_switch (dialog,
                                           GIMP_ICON_LOCK_ALPHA,
                                           _("Lock _alpha"));
  gtk_toggle_button_set_active (GTK_TOGGLE_BUTTON (button),
                                private->lock_alpha);
  g_signal_connect (button, "toggled",
                    G_CALLBACK (gimp_toggle_button_update),
                    &private->lock_alpha);

  /*  For text layers add a toggle to control "auto-rename"  */
  if (layer && gimp_item_is_text_layer (GIMP_ITEM (layer)))
    {
      button = item_options_dialog_add_switch (dialog,
                                               GIMP_ICON_TOOL_TEXT,
                                               _("Set name from _text"));
      gtk_toggle_button_set_active (GTK_TOGGLE_BUTTON (button),
                                    private->rename_text_layers);
      g_signal_connect (button, "toggled",
                        G_CALLBACK (gimp_toggle_button_update),
                        &private->rename_text_layers);

      g_signal_connect (button, "toggled",
                        G_CALLBACK (layer_options_dialog_rename_toggled),
                        private);
    }

  return dialog;
}


/*  private functions  */

static void
layer_options_dialog_free (LayerOptionsDialog *private)
{
  /* If not cleared already, it means we cancel.
   * Let's revert silently.
   */
  if (private->initial_path)
    {
      GimpLayer *layer = private->layer;

      g_return_if_fail (GIMP_IS_VECTOR_LAYER (layer));

      gimp_vector_layer_set_path (GIMP_VECTOR_LAYER (layer), private->initial_path, FALSE);
      g_clear_object (&private->initial_path);
    }
  g_clear_object (&private->link);

  g_slice_free (LayerOptionsDialog, private);
}

static void
layer_options_dialog_callback (GtkWidget    *dialog,
                               GimpImage    *image,
                               GimpItem     *item,
                               GimpContext  *context,
                               const gchar  *item_name,
                               gboolean      item_visible,
                               GimpColorTag  item_color_tag,
                               gboolean      item_lock_content,
                               gboolean      item_lock_position,
                               gboolean      item_lock_visibility,
                               gpointer      user_data)
{
  LayerOptionsDialog *private  = user_data;
  GimpPath           *path     = NULL;
  gint                width    = 0;
  gint                height   = 0;
  gint                offset_x = 0;
  gint                offset_y = 0;

  if (private->size_se)
    {
      width =
        RINT (gimp_size_entry_get_refval (GIMP_SIZE_ENTRY (private->size_se),
                                          0));
      height =
        RINT (gimp_size_entry_get_refval (GIMP_SIZE_ENTRY (private->size_se),
                                          1));
    }

  if (private->offset_se)
    {
      offset_x =
        RINT (gimp_size_entry_get_refval (GIMP_SIZE_ENTRY (private->offset_se),
                                          0));
      offset_y =
        RINT (gimp_size_entry_get_refval (GIMP_SIZE_ENTRY (private->offset_se),
                                          1));
    }

  if (gimp_item_is_vector_layer (item) && private->initial_path)
    {
      path = gimp_vector_layer_get_path (GIMP_VECTOR_LAYER (item));
      gimp_vector_layer_set_path (GIMP_VECTOR_LAYER (item), private->initial_path, FALSE);
      g_clear_object (&private->initial_path);
    }

  private->callback (dialog,
                     image,
                     GIMP_LAYER (item),
                     context,
                     item_name,
                     private->mode,
                     private->blend_space,
                     private->composite_space,
                     private->composite_mode,
                     private->opacity / 100.0,
                     private->fill_type,
                     private->link,
                     path,
                     width,
                     height,
                     offset_x,
                     offset_y,
                     item_visible,
                     item_color_tag,
                     item_lock_content,
                     item_lock_position,
                     item_lock_visibility,
                     private->lock_alpha,
                     private->rename_text_layers,
                     private->user_data);
}

static void
layer_options_dialog_update_mode_sensitivity (LayerOptionsDialog *private)
{
  gboolean mutable;

  mutable = gimp_layer_mode_is_blend_space_mutable (private->mode);
  gtk_widget_set_sensitive (private->blend_space_combo, mutable);

  mutable = gimp_layer_mode_is_composite_space_mutable (private->mode);
  gtk_widget_set_sensitive (private->composite_space_combo, mutable);

  mutable = gimp_layer_mode_is_composite_mode_mutable (private->mode);
  gtk_widget_set_sensitive (private->composite_mode_combo, mutable);
}

static void
layer_options_dialog_mode_notify (GtkWidget          *widget,
                                  const GParamSpec   *pspec,
                                  LayerOptionsDialog *private)
{
  private->mode = gimp_layer_mode_box_get_mode (GIMP_LAYER_MODE_BOX (widget));

  gimp_int_combo_box_set_active (GIMP_INT_COMBO_BOX (private->blend_space_combo),
                                 GIMP_LAYER_COLOR_SPACE_AUTO);
  gimp_int_combo_box_set_active (GIMP_INT_COMBO_BOX (private->composite_space_combo),
                                 GIMP_LAYER_COLOR_SPACE_AUTO);
  gimp_int_combo_box_set_active (GIMP_INT_COMBO_BOX (private->composite_mode_combo),
                                 GIMP_LAYER_COMPOSITE_AUTO);

  layer_options_dialog_update_mode_sensitivity (private);
}

static void
layer_options_dialog_rename_toggled (GtkWidget          *widget,
                                     LayerOptionsDialog *private)
{
  if (gtk_toggle_button_get_active (GTK_TOGGLE_BUTTON (widget)) &&
      gimp_item_is_text_layer (GIMP_ITEM (private->layer)))
    {
      GimpTextLayer *text_layer = GIMP_TEXT_LAYER (private->layer);
      GimpText      *text       = gimp_text_layer_get_text (text_layer);

      if (text && text->text)
        {
          GtkWidget *dialog;
          GtkWidget *name_entry;
          gchar     *name = gimp_utf8_strtrim (text->text, 30);

          dialog = gtk_widget_get_toplevel (widget);

          name_entry = item_options_dialog_get_name_entry (dialog);

          gtk_entry_set_text (GTK_ENTRY (name_entry), name);

          g_free (name);
        }
    }
}

static void
layer_options_file_set (GtkFileChooserButton *widget,
                        LayerOptionsDialog   *private)
{
  GFile *file;

  file = gtk_file_chooser_get_file (GTK_FILE_CHOOSER (widget));
  if (file)
    {
      gint width  = 0;
      gint height = 0;

      if (private->layer)
        {
          width  = gimp_item_get_width (GIMP_ITEM (private->layer));
          height = gimp_item_get_height (GIMP_ITEM (private->layer));

          if (width == 0 || height == 0)
            {
              GimpImage *image = gimp_item_get_image (GIMP_ITEM (private->layer));

              width  = gimp_image_get_width (image);
              height = gimp_image_get_height (image);
            }
        }

      gimp_link_set_file (private->link, file, width, height, TRUE, NULL, NULL);
      if (gimp_link_is_broken (private->link))
        {
          gimp_link_set_file (private->link, NULL, width, height, TRUE, NULL, NULL);
          g_signal_handlers_block_by_func (widget,
                                           G_CALLBACK (layer_options_file_set),
                                           private);
          gtk_file_chooser_unselect_file (GTK_FILE_CHOOSER (widget), file);
          g_signal_handlers_unblock_by_func (widget,
                                             G_CALLBACK (layer_options_file_set),
                                             private);
        }
    }
  g_clear_object (&file);
}

static void
layer_options_dialog_path_selected (GimpContainerView  *view,
                                    LayerOptionsDialog *private)
{
  GimpViewable    *item     = gimp_container_view_get_1_selected (view);
  GimpPath        *new_path = NULL;
  GimpPath        *path;
  GimpVectorLayer *layer;

  g_return_if_fail (GIMP_IS_VECTOR_LAYER (private->layer));

  layer = GIMP_VECTOR_LAYER (private->layer);

  if (item)
    new_path = GIMP_PATH (item);

  path = gimp_vector_layer_get_path (GIMP_VECTOR_LAYER (private->layer));

  if (new_path && new_path != path)
    {
      g_return_if_fail (GIMP_IS_PATH (new_path));
      gimp_vector_layer_set_path (layer, new_path, FALSE);

      if (private->initial_path == new_path)
        g_clear_object (&private->initial_path);
      else if (private->initial_path == NULL)
        private->initial_path = g_object_ref (path);

      gimp_vector_layer_refresh (layer);
    }
}

/* --- lebl-dialog.c --- */
#include "config.h"

#include <string.h>
#include <math.h>

#include <gegl.h>
#include <gtk/gtk.h>
#include <gdk/gdkkeysyms.h>

#include "libgimpwidgets/gimpwidgets.h"

#include "lebl-dialog.h"

#include "ammoos-intl.h"

/* phish code */
#define PHSHFRAMES 8
#define PHSHORIGWIDTH 288
#define PHSHORIGHEIGHT 22
#define PHSHWIDTH (PHSHORIGWIDTH/PHSHFRAMES)
#define PHSHHEIGHT PHSHORIGHEIGHT
#define PHSHCHECKTIMEOUT (g_random_int()%120*1000)
#define PHSHTIMEOUT 120
#define PHSHHIDETIMEOUT 80
#define PHSHXS 5
#define PHSHYS ((g_random_int() % 2) + 1)
#define PHSHXSHIDEFACTOR 2.5
#define PHSHYSHIDEFACTOR 2.5
#define PHSHPIXELSTOREMOVE(p) (p[3] < 55 || p[2] > 200)

static void
phsh_unsea(GdkPixbuf *gp)
{
        guchar *pixels = gdk_pixbuf_get_pixels (gp);
        int rs = gdk_pixbuf_get_rowstride (gp);
	int w = gdk_pixbuf_get_width (gp);
        int h = gdk_pixbuf_get_height (gp);
        int x, y;

        for (y = 0; y < h; y++, pixels += rs) {
                guchar *p = pixels;
                for (x = 0; x < w; x++, p+=4) {
                        if (PHSHPIXELSTOREMOVE(p))
                               p[3] = 0;
                }
        }
}

static GdkPixbuf *
get_phsh_frame (GdkPixbuf *pb, int frame)
{
        GdkPixbuf *newpb;

        newpb = gdk_pixbuf_new (GDK_COLORSPACE_RGB, TRUE, 8,
				PHSHWIDTH, PHSHHEIGHT);
        gdk_pixbuf_copy_area (pb, frame * PHSHWIDTH, 0,
			      PHSHWIDTH, PHSHHEIGHT, newpb, 0, 0);

	return newpb;
}

typedef struct {
	gboolean live;
	int x, y;
} InvGoat;

typedef struct {
	gboolean good;
	int y;
	int x;
} InvShot;


static GtkWidget *geginv = NULL;
static GtkWidget *geginv_canvas = NULL;
static GtkWidget *geginv_label = NULL;
static GdkPixbuf *inv_goat1 = NULL;
static GdkPixbuf *inv_goat2 = NULL;
static GdkPixbuf *inv_phsh1 = NULL;
static GdkPixbuf *inv_phsh2 = NULL;
static int inv_phsh_state = 0;
static int inv_goat_state = 0;
static int inv_width = 0;
static int inv_height = 0;
static int inv_goat_width = 0;
static int inv_goat_height = 0;
static int inv_phsh_width = 0;
static int inv_phsh_height = 0;
#define INV_ROWS 3
#define INV_COLS 5
static InvGoat invs[INV_COLS][INV_ROWS] = { { { FALSE, 0, 0 } } };
static int inv_num = INV_ROWS * INV_COLS;
static double inv_factor = 1.0;
static int inv_our_x = 0;
static int inv_x = 0;
static int inv_y = 0;
static int inv_first_col = 0;
static int inv_last_col = INV_COLS-1;
static int inv_level = 0;
static int inv_lives = 0;
static gboolean inv_do_pause = FALSE;
static gboolean inv_reverse = FALSE;
static gboolean inv_game_over = FALSE;
static gboolean inv_left_pressed = FALSE;
static gboolean inv_right_pressed = FALSE;
static gboolean inv_fire_pressed = FALSE;
static gboolean inv_left_released = FALSE;
static gboolean inv_right_released = FALSE;
static gboolean inv_fire_released = FALSE;
static gboolean inv_paused = FALSE;
static GSList *inv_shots = NULL;
static guint inv_draw_idle = 0;

static void
inv_show_status (void)
{
	gchar *s, *t, *u, *v, *w;
	if (geginv == NULL)
		return;

	if (inv_game_over) {
		t = g_strdup_printf (_("<b>GAME OVER</b> at level %d!"),
				     inv_level+1);
		u = g_strdup_printf ("<big>%s</big>", t);
		/* Translators: the first and third strings are similar to a
		 * title, and the second string is a small information text.
		 * The spaces are there only to separate all the strings, so
		 try to keep them as is. */
		s = g_strdup_printf (_("%1$s   %2$s   %3$s"),
				     u, _("Press 'q' to quit"), u);
		g_free (t);
		g_free (u);

	} else if (inv_paused) {
		t = g_strdup_printf("<big><b>%s</b></big>", _("Paused"));
		/* Translators: the first string is a title and the second
		 * string is a small information text. */
		s = g_strdup_printf (_("%1$s\t%2$s"),
				     t, _("Press 'p' to unpause"));
		g_free (t);

	} else {
		t = g_strdup_printf ("<b>%d</b>", inv_level+1);
		u = g_strdup_printf ("<b>%d</b>", inv_lives);
		v = g_strdup_printf (_("Level: %s,  Lives: %s"), t, u);
		w = g_strdup_printf ("<big>%s</big>", v);
		/* Translators: the first string is a title and the second
		 * string is a small information text. */
		s = g_strdup_printf (_("%1$s\t%2$s"), w,
				     _("Left/Right to move, Space to fire, 'p' to pause, 'q' to quit"));
		g_free (t);
		g_free (u);
		g_free (v);
		g_free (w);

	}
	gtk_label_set_markup (GTK_LABEL (geginv_label), s);

	g_free (s);
}

static gboolean
inv_queue_draw_idle (gpointer data)
{
        inv_draw_idle = 0;

        if (geginv)
                gtk_widget_queue_draw (data);

        return FALSE;
}

static void
inv_queue_draw (GtkWidget *window)
{
       if (inv_draw_idle == 0)
               inv_draw_idle = g_idle_add (inv_queue_draw_idle, window);
}

static void
inv_draw_explosion (int x, int y)
{
        GdkDrawingContext *context;
        cairo_rectangle_int_t rect;
        cairo_region_t *region;
        cairo_t *cr;
        int i;

        if ( ! gtk_widget_is_drawable (geginv_canvas))
                return;

        rect.x      = x - 100;
        rect.y      = y - 100;
        rect.width  = 200;
        rect.height = 200;

        region = cairo_region_create_rectangle (&rect);
        context = gdk_window_begin_draw_frame (gtk_widget_get_window (geginv_canvas),
                                               region);
        cairo_region_destroy (region);

        cr = gdk_drawing_context_get_cairo_context (context);

        cairo_set_source_rgb (cr, 1.0, 0.0, 0.0);

        for (i = 5; i < 100; i += 5) {
                cairo_arc (cr, x, y, i, 0, 2 * G_PI);
                cairo_fill (cr);
                gdk_display_flush (gtk_widget_get_display (geginv_canvas));
                g_usleep (50000);
        }

        cairo_set_source_rgb (cr, 1.0, 1.0, 1.0);

        for (i = 5; i < 100; i += 5) {
                cairo_arc (cr, x, y, i, 0, 2 * G_PI);
                cairo_fill (cr);
                gdk_display_flush (gtk_widget_get_display (geginv_canvas));
                g_usleep (50000);
        }

        gdk_window_end_draw_frame (gtk_widget_get_window (geginv_canvas),
                                   context);

	inv_queue_draw (geginv);
}


static void
inv_do_game_over (void)
{
	GSList *li;

	inv_game_over = TRUE;

	for (li = inv_shots; li != NULL; li = li->next) {
		InvShot *shot = li->data;
		shot->good = FALSE;
	}

	inv_queue_draw (geginv);

	inv_show_status ();
}


static GdkPixbuf *
pb_scale (GdkPixbuf *pb, double scale)
{
	int w, h;

	if (scale == 1.0)
		return (GdkPixbuf *)g_object_ref ((GObject *)pb);

	w = gdk_pixbuf_get_width (pb) * scale;
	h = gdk_pixbuf_get_height (pb) * scale;

	return gdk_pixbuf_scale_simple (pb, w, h,
					GDK_INTERP_BILINEAR);
}

static void
refind_first_and_last (void)
{
	int i, j;

	for (i = 0; i < INV_COLS; i++) {
		gboolean all_null = TRUE;
		for (j = 0; j < INV_ROWS; j++) {
			if (invs[i][j].live) {
				all_null = FALSE;
				break;
			}
		}
		if ( ! all_null) {
			inv_first_col = i;
			break;
		}
	}

	for (i = INV_COLS-1; i >= 0; i--) {
		gboolean all_null = TRUE;
		for (j = 0; j < INV_ROWS; j++) {
			if (invs[i][j].live) {
				all_null = FALSE;
				break;
			}
		}
		if ( ! all_null) {
			inv_last_col = i;
			break;
		}
	}
}

static void
whack_gegl (int i, int j)
{
	if ( ! invs[i][j].live)
		return;

	invs[i][j].live = FALSE;
	inv_num --;

	if (inv_num > 0) {
		refind_first_and_last ();
	} else {
		inv_x = 70;
		inv_y = 70;
		inv_first_col = 0;
		inv_last_col = INV_COLS-1;
		inv_reverse = FALSE;

		g_slist_foreach (inv_shots, (GFunc)g_free, NULL);
		g_slist_free (inv_shots);
		inv_shots = NULL;

		for (i = 0; i < INV_COLS; i++) {
			for (j = 0; j < INV_ROWS; j++) {
				invs[i][j].live = TRUE;
				invs[i][j].x = 70 + i * 100;
				invs[i][j].y = 70 + j * 80;
			}
		}
		inv_num = INV_ROWS * INV_COLS;

		inv_level ++;

		inv_show_status ();
	}

	inv_queue_draw (geginv);
}

static gboolean
geginv_timeout (gpointer data)
{
	int i, j;
	int limitx1;
	int limitx2;
	int speed;
	int shots;
	int max_shots;

	if (inv_paused)
		return TRUE;

	if (geginv != data ||
	    inv_num <= 0 ||
	    inv_y > 700)
		return FALSE;

	limitx1 = 70 - (inv_first_col * 100);
	limitx2 = 800 - 70 - (inv_last_col * 100);

	if (inv_game_over) {
		inv_y += 30;
	} else {
		if (inv_num < (INV_COLS*INV_ROWS)/3)
			speed = 45+2*inv_level;
		else if (inv_num < (2*INV_COLS*INV_ROWS)/3)
			speed = 30+2*inv_level;
		else
			speed = 15+2*inv_level;

		if (inv_reverse) {
			inv_x -= speed;
			if (inv_x < limitx1) {
				inv_reverse = FALSE;
				inv_x = (limitx1 + (limitx1 - inv_x));
				inv_y += 30+inv_level;
			}
		} else {
			inv_x += speed;
			if (inv_x > limitx2) {
				inv_reverse = TRUE;
				inv_x = (limitx2 - (inv_x - limitx2));
				inv_y += 30+inv_level;
			}
		}
	}

	for (i = 0; i < INV_COLS; i++) {
		for (j = 0; j < INV_ROWS; j++) {
			if (invs[i][j].live) {
				invs[i][j].x = inv_x + i * 100;
				invs[i][j].y = inv_y + j * 80;

				if ( ! inv_game_over &&
				    invs[i][j].y >= 570) {
					inv_do_game_over ();
				} else if ( ! inv_game_over &&
					   invs[i][j].y >= 530 &&
					   invs[i][j].x + 40 > inv_our_x - 25 &&
					   invs[i][j].x - 40 < inv_our_x + 25) {
					whack_gegl (i,j);
					inv_lives --;
					inv_draw_explosion (inv_our_x, 550);
					if (inv_lives <= 0) {
						inv_do_game_over ();
					} else {
						g_slist_foreach (inv_shots, (GFunc)g_free, NULL);
						g_slist_free (inv_shots);
						inv_shots = NULL;
						inv_our_x = 400;
						inv_do_pause = TRUE;
						inv_show_status ();
					}
				}
			}
		}
	}

	shots = 0;
	max_shots = (g_random_int () >> 3) % (2+inv_level);
	while ( ! inv_game_over && shots < MIN (max_shots, inv_num)) {
		int i = (g_random_int () >> 3) % INV_COLS;
		for (j = INV_ROWS-1; j >= 0; j--) {
			if (invs[i][j].live) {
				InvShot *shot = g_new0 (InvShot, 1);

				shot->good = FALSE;
				shot->x = invs[i][j].x + (g_random_int () % 6) - 3;
				shot->y = invs[i][j].y + inv_goat_height/2 + (g_random_int () % 3);

				inv_shots = g_slist_prepend (inv_shots, shot);
				shots++;
				break;
			}
		}
	}

	inv_goat_state = (inv_goat_state+1) % 2;

	inv_queue_draw (geginv);

	g_timeout_add (((inv_num/4)+1) * 100, geginv_timeout, geginv);

	return FALSE;
}

static gboolean
find_gegls (int x, int y)
{
	int i, j;

	/* FIXME: this is stupid, we can do better */
	for (i = 0; i < INV_COLS; i++) {
		for (j = 0; j < INV_ROWS; j++) {
			int ix = invs[i][j].x;
			int iy = invs[i][j].y;

			if ( ! invs[i][j].live)
				continue;

			if (y >= iy - 30 &&
			    y <= iy + 30 &&
			    x >= ix - 40 &&
			    x <= ix + 40) {
				whack_gegl (i, j);
				return TRUE;
			}
		}
	}

	return FALSE;
}


static gboolean
geginv_move_timeout (gpointer data)
{
	GSList *li;
	static int shot_inhibit = 0;

	if (inv_paused)
		return TRUE;

	if (geginv != data ||
	    inv_num <= 0 ||
	    inv_y > 700)
		return FALSE;

	inv_phsh_state = (inv_phsh_state+1)%10;

	/* we will be drawing something */
	if (inv_shots != NULL)
		inv_queue_draw (geginv);

	li = inv_shots;
	while (li != NULL) {
		InvShot *shot = li->data;

		if (shot->good) {
			shot->y -= 30;
			if (find_gegls (shot->x, shot->y) ||
			    shot->y <= 0) {
				GSList *list = li;
				/* we were restarted */
				if (inv_shots == NULL)
					return TRUE;
				li = li->next;
				g_free (shot);
				inv_shots = g_slist_delete_link (inv_shots, list);
				continue;
			}
		} else /* bad */ {
			shot->y += 30;
			if ( ! inv_game_over &&
			    shot->y >= 535 &&
			    shot->y <= 565 &&
			    shot->x >= inv_our_x - 25 &&
			    shot->x <= inv_our_x + 25) {
				inv_lives --;
				inv_draw_explosion (inv_our_x, 550);
				if (inv_lives <= 0) {
					inv_do_game_over ();
				} else {
					g_slist_foreach (inv_shots, (GFunc)g_free, NULL);
					g_slist_free (inv_shots);
					inv_shots = NULL;
					inv_our_x = 400;
					inv_do_pause = TRUE;
					inv_show_status ();
					return TRUE;
				}
			}

			if (shot->y >= 600) {
				GSList *list = li;
				li = li->next;
				g_free (shot);
				inv_shots = g_slist_delete_link (inv_shots, list);
				continue;
			}
		}

		li = li->next;
	}

	if ( ! inv_game_over) {
		if (inv_left_pressed && inv_our_x > 100) {
			inv_our_x -= 20;
			inv_queue_draw (geginv);
		} else if (inv_right_pressed && inv_our_x < 700) {
			inv_our_x += 20;
			inv_queue_draw (geginv);
		}
	}

	if (shot_inhibit > 0)
		shot_inhibit--;

	if ( ! inv_game_over && inv_fire_pressed && shot_inhibit == 0) {
		InvShot *shot = g_new0 (InvShot, 1);

		shot->good = TRUE;
		shot->x = inv_our_x;
		shot->y = 540;

		inv_shots = g_slist_prepend (inv_shots, shot);

		shot_inhibit = 5;

		inv_queue_draw (geginv);
	}

	if (inv_left_released)
		inv_left_pressed = FALSE;
	if (inv_right_released)
		inv_right_pressed = FALSE;
	if (inv_fire_released)
		inv_fire_pressed = FALSE;

	return TRUE;
}

static gboolean
inv_key_press (GtkWidget *widget, GdkEventKey *event, gpointer data)
{
	switch (event->keyval) {
	case GDK_KEY_Left:
	case GDK_KEY_KP_Left:
	case GDK_KEY_Pointer_Left:
		inv_left_pressed = TRUE;
		inv_left_released = FALSE;
		return TRUE;
	case GDK_KEY_Right:
	case GDK_KEY_KP_Right:
	case GDK_KEY_Pointer_Right:
		inv_right_pressed = TRUE;
		inv_right_released = FALSE;
		return TRUE;
	case GDK_KEY_space:
	case GDK_KEY_KP_Space:
		inv_fire_pressed = TRUE;
		inv_fire_released = FALSE;
		return TRUE;
	default:
		break;
	}
	return FALSE;
}

static gboolean
inv_key_release (GtkWidget *widget, GdkEventKey *event, gpointer data)
{
	switch (event->keyval) {
	case GDK_KEY_Left:
	case GDK_KEY_KP_Left:
	case GDK_KEY_Pointer_Left:
		inv_left_released = TRUE;
		return TRUE;
	case GDK_KEY_Right:
	case GDK_KEY_KP_Right:
	case GDK_KEY_Pointer_Right:
		inv_right_released = TRUE;
		return TRUE;
	case GDK_KEY_space:
	case GDK_KEY_KP_Space:
		inv_fire_released = TRUE;
		return TRUE;
	case GDK_KEY_q:
	case GDK_KEY_Q:
		gtk_widget_destroy (widget);
		return TRUE;
	case GDK_KEY_p:
	case GDK_KEY_P:
		inv_paused = ! inv_paused;
		inv_show_status ();
		return TRUE;
	default:
		break;
	}
	return FALSE;
}

static gboolean
ensure_creatures (void)
{
        GdkPixbuf *pb, *pb1;

	if (inv_goat1 != NULL)
		return TRUE;

	pb = gdk_pixbuf_new_from_resource ("/org/ammoos/lebl-dialog/wanda.png",
                                           NULL);
	if (pb == NULL)
		return FALSE;

	pb1 = get_phsh_frame (pb, 1);
	inv_phsh1 = pb_scale (pb1, inv_factor);
	g_object_unref (G_OBJECT (pb1));
	phsh_unsea (inv_phsh1);

	pb1 = get_phsh_frame (pb, 2);
	inv_phsh2 = pb_scale (pb1, inv_factor);
	g_object_unref (G_OBJECT (pb1));
	phsh_unsea (inv_phsh2);

	g_object_unref (G_OBJECT (pb));

	pb = gdk_pixbuf_new_from_resource ("/org/ammoos/lebl-dialog/gegl-1.png",
                                           NULL);
	if (pb == NULL) {
		g_object_unref (G_OBJECT (inv_phsh1));
		g_object_unref (G_OBJECT (inv_phsh2));
		return FALSE;
	}

	inv_goat1 = pb_scale (pb, inv_factor * 0.66);
	g_object_unref (pb);

	pb = gdk_pixbuf_new_from_resource ("/org/ammoos/lebl-dialog/gegl-2.png",
                                           NULL);
	if (pb == NULL) {
		g_object_unref (G_OBJECT (inv_goat1));
		g_object_unref (G_OBJECT (inv_phsh1));
		g_object_unref (G_OBJECT (inv_phsh2));
		return FALSE;
	}

	inv_goat2 = pb_scale (pb, inv_factor * 0.66);
	g_object_unref (pb);

	inv_goat_width = gdk_pixbuf_get_width (inv_goat1);
	inv_goat_height = gdk_pixbuf_get_height (inv_goat1);
	inv_phsh_width = gdk_pixbuf_get_width (inv_phsh1);
	inv_phsh_height = gdk_pixbuf_get_height (inv_phsh1);

	return TRUE;
}

static void
geginv_destroyed (GtkWidget *w, gpointer data)
{
	geginv = NULL;
}

static gboolean
inv_draw (GtkWidget *widget, cairo_t *cr)
{
	GdkPixbuf *goat;
	GSList *li;
	int i, j;

	if (geginv == NULL) {
		inv_draw_idle = 0;
		return TRUE;
	}

        cairo_set_source_rgb (cr, 1.0, 1.0, 1.0);
        cairo_paint (cr);

	if (inv_goat_state == 0)
		goat = inv_goat1;
	else
		goat = inv_goat2;

	for (i = 0; i < INV_COLS; i++) {
		for (j = 0; j < INV_ROWS; j++) {
			int x, y;
			if ( ! invs[i][j].live)
				continue;

			x = invs[i][j].x*inv_factor - inv_goat_width/2,
			y = invs[i][j].y*inv_factor - inv_goat_height/2,

                        gdk_cairo_set_source_pixbuf (cr, goat, x, y);
                        cairo_rectangle (cr,
                                         x, y,
                                         inv_goat_width,
                                         inv_goat_height);
                        cairo_fill (cr);
		}
	}

	for (li = inv_shots; li != NULL; li = li->next) {
		InvShot *shot = li->data;

                cairo_set_source_rgb (cr, 0.0, 0.0, 0.0);
                cairo_rectangle (cr,
                                 (shot->x-1)*inv_factor,
                                 (shot->y-4)*inv_factor,
                                 3, 8);
                cairo_fill (cr);
	}

	if ( ! inv_game_over) {
		GdkPixbuf *phsh;

		if (inv_phsh_state < 5) {
			phsh = inv_phsh1;
		} else {
			phsh = inv_phsh2;
		}

                gdk_cairo_set_source_pixbuf (cr, phsh,
                                             inv_our_x*inv_factor - inv_phsh_width/2,
                                             550*inv_factor - inv_phsh_height/2);
                cairo_rectangle (cr,
                                 inv_our_x*inv_factor - inv_phsh_width/2,
                                 550*inv_factor - inv_phsh_height/2,
                                 inv_phsh_width,
                                 inv_phsh_height);
                cairo_fill (cr);
	}

	if (inv_do_pause) {
		g_usleep (G_USEC_PER_SEC);
		inv_do_pause = FALSE;
	}

	inv_draw_idle = 0;
	return TRUE;
}

gboolean gimp_lebl_dialog (void);

gboolean
gimp_lebl_dialog (void)
{
        GdkMonitor *monitor;
        GdkRectangle workarea;
	GtkWidget *vbox;
	int i, j;

	if (geginv != NULL) {
		gtk_window_present (GTK_WINDOW (geginv));
		return FALSE;
	}

	inv_width = 800;
	inv_height = 600;

        monitor = gimp_get_monitor_at_pointer ();
        gdk_monitor_get_workarea (monitor, &workarea);

	if (inv_width > workarea.width * 0.9) {
		inv_width = workarea.width * 0.9;
		inv_height = inv_width * (600.0/800.0);
	}

	if (inv_height > workarea.height * 0.9) {
		inv_height = workarea.height * 0.9;
		inv_width = inv_height * (800.0/600.0);
	}

	inv_factor = (double)inv_width / 800.0;

	if ( ! ensure_creatures ())
		return FALSE;

	geginv = gtk_window_new (GTK_WINDOW_TOPLEVEL);
        gtk_window_set_position (GTK_WINDOW (geginv), GTK_WIN_POS_CENTER);
	gtk_window_set_title (GTK_WINDOW (geginv), _("Killer GEGLs from Outer Space"));
	g_object_set (G_OBJECT (geginv), "resizable", FALSE, NULL);
	g_signal_connect (G_OBJECT (geginv), "destroy",
			  G_CALLBACK (geginv_destroyed),
			  NULL);

	geginv_canvas = gtk_drawing_area_new ();
	gtk_widget_set_size_request (geginv_canvas, inv_width, inv_height);

	vbox = gtk_box_new (GTK_ORIENTATION_VERTICAL, 0);
	gtk_container_add (GTK_CONTAINER (geginv), vbox);
	gtk_box_pack_start (GTK_BOX (vbox), geginv_canvas, TRUE, TRUE, 0);

	geginv_label = gtk_label_new ("");
	gtk_box_pack_start (GTK_BOX (vbox), geginv_label, FALSE, FALSE, 0);

	inv_our_x = 400;
	inv_x = 70;
	inv_y = 70;
	inv_first_col = 0;
	inv_level = 0;
	inv_lives = 3;
	inv_last_col = INV_COLS-1;
	inv_reverse = FALSE;
	inv_game_over = FALSE;
	inv_left_pressed = FALSE;
	inv_right_pressed = FALSE;
	inv_fire_pressed = FALSE;
	inv_left_released = FALSE;
	inv_right_released = FALSE;
	inv_fire_released = FALSE;
	inv_paused = FALSE;

	gtk_widget_add_events (geginv, GDK_KEY_RELEASE_MASK);

	g_signal_connect (G_OBJECT (geginv), "key_press_event",
			  G_CALLBACK (inv_key_press), NULL);
	g_signal_connect (G_OBJECT (geginv), "key_release_event",
			  G_CALLBACK (inv_key_release), NULL);
	g_signal_connect (G_OBJECT (geginv_canvas), "draw",
			  G_CALLBACK (inv_draw), NULL);

	g_slist_foreach (inv_shots, (GFunc)g_free, NULL);
	g_slist_free (inv_shots);
	inv_shots = NULL;

	for (i = 0; i < INV_COLS; i++) {
		for (j = 0; j < INV_ROWS; j++) {
			invs[i][j].live = TRUE;
			invs[i][j].x = 70 + i * 100;
			invs[i][j].y = 70 + j * 80;
		}
	}
	inv_num = INV_ROWS * INV_COLS;

	g_timeout_add (((inv_num/4)+1) * 100, geginv_timeout, geginv);
	g_timeout_add (90, geginv_move_timeout, geginv);

	inv_show_status ();

	gtk_widget_show_all (geginv);
  return FALSE;
}

/* --- metadata-rotation-import-dialog.c --- */
/* AmmoOS Image - The AmmoOS Field Image Research
 * Copyright (C) 1995 Spencer Kimball and Peter Mattis
 *
 * metadata-rotation-import-dialog.h
 * Copyright (C) 2020 Jehan
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
#include <gexiv2/gexiv2.h>
#include <gtk/gtk.h>

#include "libgimpbase/gimpbase.h"
#include "libgimpwidgets/gimpwidgets.h"

#include "dialogs-types.h"

#include "core/ammoos.h"
#include "core/gimpcontext.h"
#include "core/gimpimage.h"
#include "core/gimpimage-metadata.h"
#include "core/gimppickable.h"

#include "widgets/gimphelp-ids.h"
#include "widgets/gimpviewabledialog.h"

#include "metadata-rotation-import-dialog.h"

#include "ammoos-intl.h"


static GimpMetadataRotationPolicy   gimp_image_metadata_rotate_dialog  (GimpImage         *image,
                                                                        GimpContext       *context,
                                                                        GtkWidget         *parent,
                                                                        GExiv2Orientation  orientation,
                                                                        gboolean          *dont_ask);
static GdkPixbuf                  * gimp_image_metadata_rotate_pixbuf  (GdkPixbuf         *pixbuf,
                                                                        GExiv2Orientation  orientation);
static gboolean                     gimp_image_metadata_rotate_release (GtkWidget         *widget,
                                                                        GdkEvent          *event,
                                                                        GtkDialog         *dialog);

static void                         gimp_image_metadata_rotate_realize (GtkWidget         *widget);

/*  public functions  */

GimpMetadataRotationPolicy
metadata_rotation_import_dialog_run (GimpImage   *image,
                                     GimpContext *context,
                                     GtkWidget   *parent,
                                     gboolean    *dont_ask)
{
  GimpMetadata      *metadata;
  GExiv2Orientation  orientation;

  metadata    = gimp_image_get_metadata (image);
  orientation = gexiv2_metadata_try_get_orientation (GEXIV2_METADATA (metadata), NULL);

  if (orientation <= GEXIV2_ORIENTATION_NORMAL ||
      orientation >  GEXIV2_ORIENTATION_MAX)
    return GIMP_METADATA_ROTATION_POLICY_KEEP;

  return gimp_image_metadata_rotate_dialog (image, context, parent,
                                            orientation, dont_ask);
}

static GimpMetadataRotationPolicy
gimp_image_metadata_rotate_dialog (GimpImage         *image,
                                   GimpContext       *context,
                                   GtkWidget         *parent,
                                   GExiv2Orientation  orientation,
                                   gboolean          *dont_ask)
{
  GtkWidget *dialog;
  GtkWidget *main_vbox;
  GtkWidget *vbox;
  GtkWidget *label;
  GtkWidget *toggle;
  gchar     *text;
  GdkPixbuf *pixbuf;
  gint       width;
  gint       scale_factor;
  gint       height;
  gint       response;

  dialog =
    gimp_viewable_dialog_new (g_list_prepend (NULL, image), context,
                              _("Rotate Image?"),
                              "ammoos-metadata-rotate-dialog",
                              GIMP_ICON_OBJECT_ROTATE_180,
                              _("Apply metadata rotation"),
                              parent,
                              gimp_standard_help_func,
                              GIMP_HELP_IMAGE_METADATA_ROTATION_IMPORT,

                              _("_Keep Original"), GTK_RESPONSE_CANCEL,
                              _("_Rotate"),        GTK_RESPONSE_OK,

                              NULL);

  gimp_dialog_set_alternative_button_order (GTK_DIALOG (dialog),
                                            GTK_RESPONSE_OK,
                                            GTK_RESPONSE_CANCEL,
                                            -1);

  gtk_window_set_resizable (GTK_WINDOW (dialog), FALSE);

  main_vbox = gtk_box_new (GTK_ORIENTATION_VERTICAL, 12);
  gtk_container_set_border_width (GTK_CONTAINER (main_vbox), 12);
  gtk_box_pack_start (GTK_BOX (gtk_dialog_get_content_area (GTK_DIALOG (dialog))),
                      main_vbox, FALSE, FALSE, 0);
  gtk_widget_set_visible (main_vbox, TRUE);

  text = g_strdup_printf (_("The image '%s' contains Exif orientation "
                            "metadata"),
                          gimp_image_get_display_name (image));
  label = g_object_new (GTK_TYPE_LABEL,
                        "label",   text,
                        "wrap",    TRUE,
                        "justify", GTK_JUSTIFY_LEFT,
                        "xalign",  0.0,
                        "yalign",  0.5,
                        NULL);
  g_free (text);

  gimp_label_set_attributes (GTK_LABEL (label),
                             PANGO_ATTR_WEIGHT, PANGO_WEIGHT_BOLD,
                             -1);
  gtk_box_pack_start (GTK_BOX (main_vbox), label, FALSE, FALSE, 0);
  gtk_widget_set_visible (label, TRUE);

  scale_factor = gtk_widget_get_scale_factor (main_vbox);
  width        = gimp_image_get_width  (image);
  height       = gimp_image_get_height (image);

#define MAX_THUMBNAIL_SIZE (128 * scale_factor)
  if (width > MAX_THUMBNAIL_SIZE || height > MAX_THUMBNAIL_SIZE)
    {
      /* Adjust the width/height ratio to a maximum size (relative to
       * current display scale factor.
       */
      if (width > height)
        {
          height = MAX_THUMBNAIL_SIZE * height / width;
          width  = MAX_THUMBNAIL_SIZE;
        }
      else
        {
          width  = MAX_THUMBNAIL_SIZE * width / height;
          height = MAX_THUMBNAIL_SIZE;
        }
    }

  gimp_pickable_flush (GIMP_PICKABLE (image));
  pixbuf = gimp_viewable_get_pixbuf (GIMP_VIEWABLE (image), context,
                                     width, height, 1, NULL);
  if (pixbuf)
    {
      GdkPixbuf *rotated;
      GtkWidget *hbox;
      GtkWidget *image;
      GtkWidget *event_box;

      hbox = gtk_box_new (GTK_ORIENTATION_HORIZONTAL, 12);
      gtk_box_set_homogeneous (GTK_BOX (hbox), TRUE);
      gtk_box_pack_start (GTK_BOX (main_vbox), hbox, FALSE, FALSE, 0);
      gtk_widget_set_visible (hbox, TRUE);

      vbox = gtk_box_new (GTK_ORIENTATION_VERTICAL, 6);
      gtk_box_pack_start (GTK_BOX (hbox), vbox, TRUE, TRUE, 0);
      gtk_widget_set_visible (vbox, TRUE);

      label = gtk_label_new (_("Original"));
      gtk_label_set_ellipsize (GTK_LABEL (label), PANGO_ELLIPSIZE_MIDDLE);
      gimp_label_set_attributes (GTK_LABEL (label),
                                 PANGO_ATTR_STYLE,  PANGO_STYLE_ITALIC,
                                 -1);
      gtk_box_pack_end (GTK_BOX (vbox), label, FALSE, FALSE, 0);
      gtk_widget_set_visible (label, TRUE);

      event_box = gtk_event_box_new ();
      image     = gtk_image_new_from_pixbuf (pixbuf);

      gtk_container_add (GTK_CONTAINER (event_box), image);
      gtk_box_pack_end (GTK_BOX (vbox), event_box, FALSE, FALSE, 0);
      gtk_widget_set_visible (image, TRUE);
      gtk_widget_set_visible (event_box, TRUE);

      g_object_set_data (G_OBJECT (event_box), "metadata-rotation-response",
                         GINT_TO_POINTER (GTK_RESPONSE_CANCEL));
      g_signal_connect_object (event_box, "button-release-event",
                               G_CALLBACK (gimp_image_metadata_rotate_release),
                               dialog, 0);
      g_signal_connect (event_box, "realize",
                        G_CALLBACK (gimp_image_metadata_rotate_realize),
                        NULL);

      vbox = gtk_box_new (GTK_ORIENTATION_VERTICAL, 6);
      gtk_box_pack_start (GTK_BOX (hbox), vbox, TRUE, TRUE, 0);
      gtk_widget_set_visible (vbox, TRUE);

      label = gtk_label_new (_("Rotated"));
      gimp_label_set_attributes (GTK_LABEL (label),
                                 PANGO_ATTR_STYLE,  PANGO_STYLE_ITALIC,
                                 -1);
      gtk_box_pack_end (GTK_BOX (vbox), label, FALSE, FALSE, 0);
      gtk_widget_set_visible (label, TRUE);

      rotated = gimp_image_metadata_rotate_pixbuf (pixbuf, orientation);

      event_box = gtk_event_box_new ();
      image     = gtk_image_new_from_pixbuf (rotated);
      g_object_unref (rotated);

      gtk_container_add (GTK_CONTAINER (event_box), image);
      gtk_box_pack_end (GTK_BOX (vbox), event_box, FALSE, FALSE, 0);
      gtk_widget_set_visible (image, TRUE);
      gtk_widget_set_visible (event_box, TRUE);

      g_object_set_data (G_OBJECT (event_box), "metadata-rotation-response",
                         GINT_TO_POINTER (GTK_RESPONSE_OK));
      g_signal_connect_object (event_box, "button-release-event",
                               G_CALLBACK (gimp_image_metadata_rotate_release),
                               dialog, 0);
      g_signal_connect (event_box, "realize",
                        G_CALLBACK (gimp_image_metadata_rotate_realize),
                        NULL);
    }

  label = g_object_new (GTK_TYPE_LABEL,
                        "label",   _("Would you like to rotate the image?"),
                        "wrap",    TRUE,
                        "justify", GTK_JUSTIFY_LEFT,
                        "xalign",  0.0,
                        "yalign",  0.5,
                        NULL);
  gimp_label_set_attributes (GTK_LABEL (label),
                             PANGO_ATTR_WEIGHT, PANGO_WEIGHT_BOLD,
                             -1);
  gtk_box_pack_start (GTK_BOX (main_vbox), label, FALSE, FALSE, 0);
  gtk_widget_set_visible (label, TRUE);

  toggle = gtk_check_button_new_with_mnemonic (_("_Don't ask me again"));
  gtk_box_pack_end (GTK_BOX (main_vbox), toggle, FALSE, FALSE, 0);
  gtk_toggle_button_set_active (GTK_TOGGLE_BUTTON (toggle), FALSE);
  gtk_widget_set_visible (toggle, TRUE);

  response  = gimp_dialog_run (GIMP_DIALOG (dialog));
  *dont_ask = (gtk_toggle_button_get_active (GTK_TOGGLE_BUTTON (toggle)));

  gtk_widget_destroy (dialog);

  return (response == GTK_RESPONSE_OK) ?
          GIMP_METADATA_ROTATION_POLICY_ROTATE :
          GIMP_METADATA_ROTATION_POLICY_KEEP;
}

static GdkPixbuf *
gimp_image_metadata_rotate_pixbuf (GdkPixbuf         *pixbuf,
                                   GExiv2Orientation  orientation)
{
  GdkPixbuf *rotated = NULL;
  GdkPixbuf *temp;

  switch (orientation)
    {
    case GEXIV2_ORIENTATION_UNSPECIFIED:
    case GEXIV2_ORIENTATION_NORMAL:  /* standard orientation, do nothing */
      rotated = g_object_ref (pixbuf);
      break;

    case GEXIV2_ORIENTATION_HFLIP:
      rotated = gdk_pixbuf_flip (pixbuf, TRUE);
      break;

    case GEXIV2_ORIENTATION_ROT_180:
      rotated = gdk_pixbuf_rotate_simple (pixbuf, GDK_PIXBUF_ROTATE_UPSIDEDOWN);
      break;

    case GEXIV2_ORIENTATION_VFLIP:
      rotated = gdk_pixbuf_flip (pixbuf, FALSE);
      break;

    case GEXIV2_ORIENTATION_ROT_90_HFLIP:  /* flipped diagonally around '\' */
      temp = gdk_pixbuf_rotate_simple (pixbuf, GDK_PIXBUF_ROTATE_CLOCKWISE);
      rotated = gdk_pixbuf_flip (temp, TRUE);
      g_object_unref (temp);
      break;

    case GEXIV2_ORIENTATION_ROT_90:  /* 90 CW */
      rotated = gdk_pixbuf_rotate_simple (pixbuf, GDK_PIXBUF_ROTATE_CLOCKWISE);
      break;

    case GEXIV2_ORIENTATION_ROT_90_VFLIP:  /* flipped diagonally around '/' */
      temp = gdk_pixbuf_rotate_simple (pixbuf, GDK_PIXBUF_ROTATE_CLOCKWISE);
      rotated = gdk_pixbuf_flip (temp, FALSE);
      g_object_unref (temp);
      break;

    case GEXIV2_ORIENTATION_ROT_270:  /* 90 CCW */
      rotated = gdk_pixbuf_rotate_simple (pixbuf, GDK_PIXBUF_ROTATE_COUNTERCLOCKWISE);
      break;

    default: /* shouldn't happen */
      break;
    }

  return rotated;
}

static gboolean
gimp_image_metadata_rotate_release (GtkWidget *widget,
                                    GdkEvent  *event,
                                    GtkDialog *dialog)
{
  gint response_id;

  response_id =
    GPOINTER_TO_INT (g_object_get_data (G_OBJECT (widget),
                                        "metadata-rotation-response"));

  gtk_dialog_response (dialog, response_id);
  return FALSE;
}

static void
gimp_image_metadata_rotate_realize (GtkWidget *widget)
{
  GdkCursor *cursor;

  cursor = gdk_cursor_new_from_name (gtk_widget_get_display (widget),
                                     "pointer");
  gdk_window_set_cursor (gtk_widget_get_window (widget), cursor);
  g_object_unref (cursor);
}

/* --- module-dialog.c --- */
/* AmmoOS Image - The AmmoOS Field Image Research
 * Copyright (C) 1995 Spencer Kimball and Peter Mattis
 *
 * module-dialog.c
 * (C) 1999 Austin Donnelly <austin@ammoos.org>
 * (C) 2008 Sven Neumann <sven@ammoos.org>
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

#include "libgimpbase/gimpbase.h"
#include "libgimpmodule/gimpmodule.h"
#include "libgimpwidgets/gimpwidgets.h"

#include "dialogs-types.h"

#include "core/ammoos.h"
#include "core/ammoos-modules.h"

#include "widgets/gimphelp-ids.h"

#include "module-dialog.h"

#include "ammoos-intl.h"


#define RESPONSE_REFRESH  1

enum
{
  INFO_AUTHOR,
  INFO_VERSION,
  INFO_DATE,
  INFO_COPYRIGHT,
  INFO_LOCATION,
  N_INFOS
};

typedef struct _ModuleDialog ModuleDialog;

struct _ModuleDialog
{
  Gimp         *ammoos;

  GimpModule   *selected;
  GtkListStore *list;
  GtkWidget    *listbox;

  GtkWidget    *hint;
  GtkWidget    *grid;
  GtkWidget    *label[N_INFOS];
  GtkWidget    *error_box;
  GtkWidget    *error_label;
};


/*  local function prototypes  */

static GtkWidget *   create_widget_for_module   (gpointer          item,
                                                 gpointer          user_data);
static void          dialog_response            (GtkWidget        *widget,
                                                 gint              response_id,
                                                 ModuleDialog     *private);
static void          dialog_destroy_callback    (GtkWidget        *widget,
                                                 ModuleDialog     *private);
static void          dialog_select_callback     (GtkListBox       *listbox,
                                                 GtkListBoxRow    *row,
                                                 ModuleDialog     *private);
static void          dialog_enabled_toggled     (GtkToggleButton  *checkbox,
                                                 ModuleDialog     *private);
static void          dialog_info_init            (ModuleDialog     *private,
                                                 GtkWidget         *grid);


/*  public functions  */

GtkWidget *
module_dialog_new (Gimp *ammoos)
{
  ModuleDialog      *private;
  GtkWidget         *dialog;
  GtkWidget         *vbox;
  GtkWidget         *sw;
  GtkWidget         *image;

  g_return_val_if_fail (GIMP_IS_GIMP (ammoos), NULL);

  private = g_slice_new0 (ModuleDialog);

  private->ammoos = ammoos;

  dialog = gimp_dialog_new (_("Module Manager"),
                            "ammoos-modules", NULL, 0,
                            gimp_standard_help_func, GIMP_HELP_MODULE_DIALOG,

                            _("_Refresh"), RESPONSE_REFRESH,
                            _("_Close"),   GTK_RESPONSE_CLOSE,

                            NULL);

  gimp_dialog_set_alternative_button_order (GTK_DIALOG (dialog),
                                           GTK_RESPONSE_CLOSE,
                                           RESPONSE_REFRESH,
                                           -1);

  g_signal_connect (dialog, "response",
                    G_CALLBACK (dialog_response),
                    private);

  vbox = gtk_box_new (GTK_ORIENTATION_VERTICAL, 12);
  gtk_container_set_border_width (GTK_CONTAINER (vbox), 12);
  gtk_box_pack_start (GTK_BOX (gtk_dialog_get_content_area (GTK_DIALOG (dialog))),
                      vbox, TRUE, TRUE, 0);
  gtk_widget_set_visible (vbox, TRUE);

  private->hint = gimp_hint_box_new (_("You will have to restart AmmoOS Image "
                                       "for the changes to take effect."));
  gtk_box_pack_start (GTK_BOX (vbox), private->hint, FALSE, FALSE, 0);

  if (ammoos->write_modulerc)
    gtk_widget_set_visible (private->hint, TRUE);

  sw = gtk_scrolled_window_new (NULL, NULL);
  gtk_scrolled_window_set_shadow_type (GTK_SCROLLED_WINDOW (sw),
                                       GTK_SHADOW_IN);
  gtk_scrolled_window_set_policy (GTK_SCROLLED_WINDOW (sw),
                                  GTK_POLICY_AUTOMATIC,
                                  GTK_POLICY_AUTOMATIC);
  gtk_box_pack_start (GTK_BOX (vbox), sw, TRUE, TRUE, 0);
  gtk_widget_set_size_request (sw, 124, 100);
  gtk_widget_set_visible (sw, TRUE);

  private->listbox = gtk_list_box_new ();
  gtk_list_box_set_selection_mode (GTK_LIST_BOX (private->listbox),
                                   GTK_SELECTION_BROWSE);
  gtk_list_box_bind_model (GTK_LIST_BOX (private->listbox),
                           G_LIST_MODEL (ammoos->module_db),
                           create_widget_for_module,
                           private,
                           NULL);
  gtk_style_context_add_class (gtk_widget_get_style_context (GTK_WIDGET (private->listbox)),
                               "view");
  g_signal_connect (private->listbox, "row-selected",
                    G_CALLBACK (dialog_select_callback),
                    private);

  gtk_container_add (GTK_CONTAINER (sw), private->listbox);
  gtk_widget_set_visible (private->listbox, TRUE);

  private->grid = gtk_grid_new ();
  gtk_grid_set_column_spacing (GTK_GRID (private->grid), 6);
  gtk_box_pack_start (GTK_BOX (vbox), private->grid, FALSE, FALSE, 0);
  gtk_widget_set_visible (private->grid, TRUE);

  private->error_box = gtk_box_new (GTK_ORIENTATION_HORIZONTAL, 6);
  gtk_box_pack_start (GTK_BOX (vbox), private->error_box, FALSE, FALSE, 0);

  image = gtk_image_new_from_icon_name (GIMP_ICON_DIALOG_WARNING,
                                        GTK_ICON_SIZE_BUTTON);
  gtk_box_pack_start (GTK_BOX (private->error_box), image, FALSE, FALSE, 0);
  gtk_widget_set_visible (image, TRUE);

  private->error_label = gtk_label_new (NULL);
  gtk_label_set_xalign (GTK_LABEL (private->error_label), 0.0);
  gtk_box_pack_start (GTK_BOX (private->error_box),
                      private->error_label, TRUE, TRUE, 0);
  gtk_widget_set_visible (private->error_label, TRUE);

  dialog_info_init (private, private->grid);

  g_signal_connect (dialog, "destroy",
                    G_CALLBACK (dialog_destroy_callback),
                    private);

  return dialog;
}


/*  private functions  */

static GtkWidget *
create_widget_for_module (gpointer item,
                          gpointer user_data)
{
  GimpModule           *module  = GIMP_MODULE (item);
  ModuleDialog         *private = user_data;
  const GimpModuleInfo *info    = gimp_module_get_info (module);
  GFile                *file    = gimp_module_get_file (module);
  GtkWidget            *row;
  GtkWidget            *grid;
  GtkWidget            *label;
  GtkWidget            *checkbox;

  row = gtk_list_box_row_new ();
  g_object_set_data (G_OBJECT (row), "module", module);
  gtk_widget_set_visible (row, TRUE);

  grid = gtk_grid_new ();
  gtk_grid_set_column_spacing (GTK_GRID (grid), 6);
  g_object_set (grid, "margin", 3, NULL);
  gtk_container_add (GTK_CONTAINER (row), grid);
  gtk_widget_set_visible (grid, TRUE);

  checkbox = gtk_check_button_new ();
  g_object_bind_property (module, "auto-load", checkbox, "active",
                          G_BINDING_SYNC_CREATE | G_BINDING_BIDIRECTIONAL);
  g_signal_connect (checkbox, "toggled",
                    G_CALLBACK (dialog_enabled_toggled),
                    private);
  gtk_widget_set_visible (checkbox, TRUE);
  gtk_grid_attach (GTK_GRID (grid), checkbox, 0, 0, 1, 1);

  label = gtk_label_new (info ? dgettext (GETTEXT_PACKAGE "-libgimp", info->purpose) :
                                gimp_file_get_utf8_name (file));
  gtk_widget_set_visible (label, TRUE);
  gtk_grid_attach (GTK_GRID (grid), label, 1, 0, 1, 1);

  return row;
}

static void
dialog_response (GtkWidget    *widget,
                 gint          response_id,
                 ModuleDialog *private)
{
  if (response_id == RESPONSE_REFRESH)
    gimp_modules_refresh (private->ammoos);
  else
    gtk_widget_destroy (widget);
}

static void
dialog_destroy_callback (GtkWidget    *widget,
                         ModuleDialog *private)
{
  g_slice_free (ModuleDialog, private);
}

static void
dialog_select_callback (GtkListBox    *listbox,
                        GtkListBoxRow *row,
                        ModuleDialog  *private)
{
  guint                 i;
  GimpModule           *module;
  const GimpModuleInfo *info;
  const gchar          *location      = NULL;
  const gchar          *text[N_INFOS] = { NULL, };
  gboolean              show_error;

  if (row == NULL)
    {
      for (i = 0; i < N_INFOS; i++)
        gtk_label_set_text (GTK_LABEL (private->label[i]), NULL);
      gtk_label_set_text (GTK_LABEL (private->error_label), NULL);
      gtk_widget_set_visible (private->error_box, FALSE);
      return;
    }

  module = g_object_get_data (G_OBJECT (row), "module");
  if (private->selected == module)
    return;

  private->selected = module;

  if (gimp_module_is_on_disk (module))
    location = gimp_file_get_utf8_name (gimp_module_get_file (module));

  info = gimp_module_get_info (module);

  if (info)
    {
      text[INFO_AUTHOR]    = info->author;
      text[INFO_VERSION]   = info->version;
      text[INFO_DATE]      = info->date;
      text[INFO_COPYRIGHT] = info->copyright;
      text[INFO_LOCATION]  = location ? location : _("Only in memory");
    }
  else
    {
      text[INFO_LOCATION]  = location ? location : _("No longer available");
    }

  for (i = 0; i < N_INFOS; i++)
    gtk_label_set_text (GTK_LABEL (private->label[i]),
                        text[i] ? text[i] : "--");

  /* Show errors */
  show_error = (gimp_module_get_state (module) == GIMP_MODULE_STATE_ERROR &&
                gimp_module_get_last_error (module));
  gtk_label_set_text (GTK_LABEL (private->error_label),
                      show_error ? gimp_module_get_last_error (module) : NULL);
  gtk_widget_set_visible (private->error_box, show_error);
}

static void
dialog_enabled_toggled (GtkToggleButton *checkbox,
                        ModuleDialog    *private)
{
  private->ammoos->write_modulerc = TRUE;
  gtk_widget_set_visible (private->hint, TRUE);
}

static void
dialog_info_init (ModuleDialog *private,
                  GtkWidget    *grid)
{
  GtkWidget *label;
  gint       i;

  const gchar * const text[] =
  {
    N_("Author:"),
    N_("Version:"),
    N_("Date:"),
    N_("Copyright:"),
    N_("Location:")
  };

  for (i = 0; i < G_N_ELEMENTS (text); i++)
    {
      label = gtk_label_new (gettext (text[i]));
      gtk_label_set_xalign (GTK_LABEL (label), 0.0);
      gtk_grid_attach (GTK_GRID (grid), label, 0, i, 1, 1);
      gtk_widget_set_visible (label, TRUE);

      private->label[i] = gtk_label_new ("");
      gtk_label_set_xalign (GTK_LABEL (private->label[i]), 0.0);
      gtk_label_set_ellipsize (GTK_LABEL (private->label[i]),
                               PANGO_ELLIPSIZE_END);
      gtk_grid_attach (GTK_GRID (grid), private->label[i], 1, i, 1, 1);
      gtk_widget_set_visible (private->label[i], TRUE);
    }
}

/* --- palette-import-dialog.c --- */
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

#include <string.h>

#include <gegl.h>
#include <gtk/gtk.h>

#include "libgimpmath/gimpmath.h"
#include "libgimpwidgets/gimpwidgets.h"

#include "dialogs-types.h"

#include "core/ammoos.h"
#include "core/gimpcontainer.h"
#include "core/gimpcontext.h"
#include "core/gimpdatafactory.h"
#include "core/gimpdrawable.h"
#include "core/gimpgradient.h"
#include "core/gimpimage.h"
#include "core/gimppalette.h"
#include "core/gimppalette-import.h"

#include "widgets/gimpcontainercombobox.h"
#include "widgets/gimpdnd.h"
#include "widgets/gimphelp-ids.h"
#include "widgets/gimpview.h"
#include "widgets/gimpwidgets-utils.h"

#include "palette-import-dialog.h"

#include "ammoos-intl.h"


typedef enum
{
  GRADIENT_IMPORT,
  IMAGE_IMPORT,
  FILE_IMPORT
} ImportType;


typedef struct _ImportDialog ImportDialog;

struct _ImportDialog
{
  GtkWidget     *dialog;

  ImportType     import_type;
  GimpContext   *context;
  GimpImage     *image;

  GimpPalette   *palette;

  GtkWidget     *gradient_radio;
  GtkWidget     *image_radio;
  GtkWidget     *file_radio;

  GtkWidget     *gradient_combo;
  GtkWidget     *image_combo;
  GtkWidget     *file_chooser;

  GtkWidget     *sample_merged_toggle;
  GtkWidget     *selection_only_toggle;

  GtkWidget     *entry;
  GtkWidget     *num_colors;
  GtkWidget     *columns;
  GtkWidget     *threshold;

  GtkWidget     *preview;
  GtkWidget     *no_colors_label;
};


static void   palette_import_free                 (ImportDialog   *private);
static void   palette_import_response             (GtkWidget      *dialog,
                                                   gint            response_id,
                                                   ImportDialog   *private);
static void   palette_import_gradient_changed     (GimpContext    *context,
                                                   GimpGradient   *gradient,
                                                   ImportDialog   *private);
static void   palette_import_image_changed        (GimpContext    *context,
                                                   GimpImage      *image,
                                                   ImportDialog   *private);
static void   palette_import_layer_changed        (GimpImage      *image,
                                                   ImportDialog   *private);
static void   palette_import_mask_changed         (GimpImage      *image,
                                                   ImportDialog   *private);
static void   palette_import_filename_changed     (GtkFileChooser *button,
                                                   ImportDialog   *private);
static void   import_dialog_drop_callback         (GtkWidget      *widget,
                                                   gint            x,
                                                   gint            y,
                                                   GimpViewable   *viewable,
                                                   gpointer        data);
static void   palette_import_grad_callback        (GtkWidget      *widget,
                                                   ImportDialog   *private);
static void   palette_import_image_callback       (GtkWidget      *widget,
                                                   ImportDialog   *private);
static void   palette_import_file_callback        (GtkWidget      *widget,
                                                   ImportDialog   *private);
static void   palette_import_columns_changed      (GimpLabelSpin  *columns,
                                                   ImportDialog   *private);
static void   palette_import_image_add            (GimpContainer  *container,
                                                   GimpImage      *image,
                                                   ImportDialog   *private);
static void   palette_import_image_remove         (GimpContainer  *container,
                                                   GimpImage      *image,
                                                   ImportDialog   *private);
static void   palette_import_make_palette         (ImportDialog   *private);
static void   palette_import_file_set_filters     (GtkFileChooser *file_chooser);

/*  public functions  */

GtkWidget *
palette_import_dialog_new (GimpContext *context)
{
  ImportDialog *private;
  GimpGradient *gradient;
  GtkWidget    *dialog;
  GtkWidget    *main_hbox;
  GtkWidget    *frame;
  GtkWidget    *vbox;
  GtkWidget    *grid;
  GtkSizeGroup *size_group;
  GSList       *group = NULL;

  g_return_val_if_fail (GIMP_IS_CONTEXT (context), NULL);

  gradient = gimp_context_get_gradient (context);

  private = g_slice_new0 (ImportDialog);

  private->import_type = GRADIENT_IMPORT;
  private->context     = gimp_context_new (context->ammoos, "Palette Import",
                                          context);

  dialog = private->dialog =
    gimp_dialog_new (_("Import a New Palette"),
                     "ammoos-palette-import", NULL, 0,
                     gimp_standard_help_func,
                     GIMP_HELP_PALETTE_IMPORT,

                     _("_Cancel"), GTK_RESPONSE_CANCEL,
                     _("_Import"), GTK_RESPONSE_OK,

                     NULL);

  gimp_dialog_set_alternative_button_order (GTK_DIALOG (dialog),
                                           GTK_RESPONSE_OK,
                                           GTK_RESPONSE_CANCEL,
                                           -1);

  g_object_weak_ref (G_OBJECT (dialog),
                     (GWeakNotify) palette_import_free, private);

  g_signal_connect (dialog, "response",
                    G_CALLBACK (palette_import_response),
                    private);

  gimp_dnd_viewable_dest_add (dialog,
                              GIMP_TYPE_GRADIENT,
                              import_dialog_drop_callback,
                              private);
  gimp_dnd_viewable_dest_add (dialog,
                              GIMP_TYPE_IMAGE,
                              import_dialog_drop_callback,
                              private);

  main_hbox = gtk_box_new (GTK_ORIENTATION_HORIZONTAL, 12);
  gtk_container_set_border_width (GTK_CONTAINER (main_hbox), 12);
  gtk_box_pack_start (GTK_BOX (gtk_dialog_get_content_area (GTK_DIALOG (dialog))),
                      main_hbox, TRUE, TRUE, 0);
  gtk_widget_set_visible (main_hbox, TRUE);

  vbox = gtk_box_new (GTK_ORIENTATION_VERTICAL, 12);
  gtk_box_pack_start (GTK_BOX (main_hbox), vbox, TRUE, TRUE, 0);
  gtk_widget_set_visible (vbox, TRUE);


  /*  The "Source" frame  */

  frame = gimp_frame_new (_("Select Source"));
  gtk_box_pack_start (GTK_BOX (vbox), frame, FALSE, FALSE, 0);
  gtk_widget_set_visible (frame, TRUE);

  grid = gtk_grid_new ();
  gtk_grid_set_column_spacing (GTK_GRID (grid), 6);
  gtk_grid_set_row_spacing (GTK_GRID (grid), 6);
  gtk_container_add (GTK_CONTAINER (frame), grid);
  gtk_widget_set_visible (grid, TRUE);

  private->gradient_radio =
    gtk_radio_button_new_with_mnemonic (group, _("_Gradient"));
  group = gtk_radio_button_get_group (GTK_RADIO_BUTTON (private->gradient_radio));
  gtk_grid_attach (GTK_GRID (grid), private->gradient_radio, 0, 0, 1, 1);
  gtk_widget_set_visible (private->gradient_radio, TRUE);

  g_signal_connect (private->gradient_radio, "toggled",
                    G_CALLBACK (palette_import_grad_callback),
                    private);

  private->image_radio =
    gtk_radio_button_new_with_mnemonic (group, _("I_mage"));
  group = gtk_radio_button_get_group (GTK_RADIO_BUTTON (private->image_radio));
  gtk_grid_attach (GTK_GRID (grid), private->image_radio, 0, 1, 1, 1);
  gtk_widget_set_visible (private->image_radio, TRUE);

  g_signal_connect (private->image_radio, "toggled",
                    G_CALLBACK (palette_import_image_callback),
                    private);

  gtk_widget_set_sensitive (private->image_radio,
                            ! gimp_container_is_empty (context->ammoos->images));

  private->sample_merged_toggle =
    gtk_check_button_new_with_mnemonic (_("Sample _Merged"));
  gtk_toggle_button_set_active (GTK_TOGGLE_BUTTON (private->sample_merged_toggle),
                                TRUE);
  gtk_grid_attach (GTK_GRID (grid), private->sample_merged_toggle, 1, 2, 1, 1);
  gtk_widget_set_visible (private->sample_merged_toggle, TRUE);

  g_signal_connect_swapped (private->sample_merged_toggle, "toggled",
                            G_CALLBACK (palette_import_make_palette),
                            private);

  private->selection_only_toggle =
    gtk_check_button_new_with_mnemonic (_("_Selected Pixels only"));
  gtk_toggle_button_set_active (GTK_TOGGLE_BUTTON (private->selection_only_toggle),
                                FALSE);
  gtk_grid_attach (GTK_GRID (grid), private->selection_only_toggle, 1, 3, 1, 1);
  gtk_widget_set_visible (private->selection_only_toggle, TRUE);

  g_signal_connect_swapped (private->selection_only_toggle, "toggled",
                            G_CALLBACK (palette_import_make_palette),
                            private);

  private->file_radio =
    gtk_radio_button_new_with_mnemonic (group, _("Palette _file"));
  group = gtk_radio_button_get_group (GTK_RADIO_BUTTON (private->image_radio));
  gtk_grid_attach (GTK_GRID (grid), private->file_radio, 0, 4, 1, 1);
  gtk_widget_set_visible (private->file_radio, TRUE);

  g_signal_connect (private->file_radio, "toggled",
                    G_CALLBACK (palette_import_file_callback),
                    private);

  size_group = gtk_size_group_new (GTK_SIZE_GROUP_VERTICAL);

  /*  The gradient menu  */
  private->gradient_combo =
    gimp_container_combo_box_new (gimp_data_factory_get_container (context->ammoos->gradient_factory),
                                  private->context, 24, 1);
  gimp_grid_attach_aligned (GTK_GRID (grid), 0, 0,
                            NULL, 0.0, 0.5, private->gradient_combo, 1);
  gtk_size_group_add_widget (size_group, private->gradient_combo);

  /*  The image menu  */
  private->image_combo =
    gimp_container_combo_box_new (context->ammoos->images, private->context,
                                  24, 1);
  gimp_grid_attach_aligned (GTK_GRID (grid), 0, 1,
                            NULL, 0.0, 0.5, private->image_combo, 1);
  gtk_size_group_add_widget (size_group, private->image_combo);

  /*  Palette file name entry  */
  private->file_chooser = gtk_file_chooser_button_new (_("Select Palette File"),
                                                       GTK_FILE_CHOOSER_ACTION_OPEN);
  gimp_grid_attach_aligned (GTK_GRID (grid), 0, 4,
                            NULL, 0.0, 0.5, private->file_chooser, 1);
  gtk_size_group_add_widget (size_group, private->file_chooser);

  /* Set valid palette files filters */
  palette_import_file_set_filters (GTK_FILE_CHOOSER (private->file_chooser));

  g_object_unref (size_group);

  /*  The "Import" frame  */

  frame = gimp_frame_new (_("Import Options"));
  gtk_box_pack_start (GTK_BOX (vbox), frame, FALSE, FALSE, 0);
  gtk_widget_set_visible (frame, TRUE);

  grid = gtk_grid_new ();
  gtk_grid_set_column_spacing (GTK_GRID (grid), 6);
  gtk_grid_set_row_spacing (GTK_GRID (grid), 6);
  gtk_container_add (GTK_CONTAINER (frame), grid);
  gtk_widget_set_visible (grid, TRUE);

  /*  The source's name  */
  private->entry = gtk_entry_new ();
  gtk_entry_set_text (GTK_ENTRY (private->entry),
                      gradient ?
                      gimp_object_get_name (gradient) : _("New import"));
  gimp_grid_attach_aligned (GTK_GRID (grid), 0, 0,
                            _("Palette _name:"), 0.0, 0.5,
                            private->entry, 2);

  /*  The # of colors  */
  private->num_colors = gimp_scale_entry_new (_("N_umber of colors:"),
                                              256, 2, 10000, 0);
  gimp_grid_attach_aligned (GTK_GRID (grid), -1, 1,
                            NULL, 0.0, 0.5,
                            private->num_colors, 3);
  gimp_scale_entry_set_logarithmic (GIMP_SCALE_ENTRY (private->num_colors), TRUE);

  g_signal_connect_swapped (private->num_colors,
                            "value-changed",
                            G_CALLBACK (palette_import_make_palette),
                            private);

  /*  The columns  */
  private->columns = gimp_scale_entry_new (_("C_olumns:"), 16, 0, 64, 0);
  gimp_grid_attach_aligned (GTK_GRID (grid), -1, 2,
                            NULL, 0.0, 0.5,
                            private->columns, 3);

  g_signal_connect (private->columns, "value-changed",
                    G_CALLBACK (palette_import_columns_changed),
                    private);

  /*  The interval  */
  private->threshold = gimp_scale_entry_new (_("I_nterval:"), 1, 1, 128, 0);
  gimp_grid_attach_aligned (GTK_GRID (grid), -1, 3,
                            NULL, 0.0, 0.5,
                            private->threshold, 3);

  g_signal_connect_swapped (private->threshold, "value-changed",
                            G_CALLBACK (palette_import_make_palette),
                            private);


  /*  The "Preview" frame  */
  frame = gimp_frame_new (_("Preview"));
  gtk_box_pack_start (GTK_BOX (main_hbox), frame, FALSE, FALSE, 0);
  gtk_widget_set_visible (frame, TRUE);

  vbox = gtk_box_new (GTK_ORIENTATION_VERTICAL, 6);
  gtk_container_add (GTK_CONTAINER (frame), vbox);
  gtk_widget_set_visible (vbox, TRUE);

  private->preview = gimp_view_new_full_by_types (private->context,
                                                 GIMP_TYPE_VIEW,
                                                 GIMP_TYPE_PALETTE,
                                                 192, 192, 1,
                                                 TRUE, FALSE, FALSE);
  gtk_widget_set_halign (private->preview, 0.0);
  gtk_box_pack_start (GTK_BOX (vbox), private->preview, FALSE, FALSE, 0);
  gtk_widget_set_visible (private->preview, TRUE);

  private->no_colors_label =
    gtk_label_new (_("The selected source contains no colors."));
  gtk_widget_set_size_request (private->no_colors_label, 194, -1);
  gtk_label_set_line_wrap (GTK_LABEL (private->no_colors_label), TRUE);
  gimp_label_set_attributes (GTK_LABEL (private->no_colors_label),
                             PANGO_ATTR_STYLE, PANGO_STYLE_ITALIC,
                             -1);
  gtk_box_pack_start (GTK_BOX (vbox), private->no_colors_label, FALSE, FALSE, 0);
  gtk_widget_set_visible (private->no_colors_label, TRUE);


  /*  keep the dialog up-to-date  */

  g_signal_connect (context->ammoos->images, "add",
                    G_CALLBACK (palette_import_image_add),
                    private);
  g_signal_connect (context->ammoos->images, "remove",
                    G_CALLBACK (palette_import_image_remove),
                    private);

  g_signal_connect (private->context, "gradient-changed",
                    G_CALLBACK (palette_import_gradient_changed),
                    private);
  g_signal_connect (private->context, "image-changed",
                    G_CALLBACK (palette_import_image_changed),
                    private);
  g_signal_connect (private->file_chooser, "selection-changed",
                    G_CALLBACK (palette_import_filename_changed),
                    private);

  palette_import_grad_callback (private->gradient_radio, private);

  return dialog;
}


/*  private functions  */

static void
palette_import_free (ImportDialog *private)
{
  Gimp *ammoos = private->context->ammoos;

  g_signal_handlers_disconnect_by_func (ammoos->images,
                                        palette_import_image_add,
                                        private);
  g_signal_handlers_disconnect_by_func (ammoos->images,
                                        palette_import_image_remove,
                                        private);

  if (private->palette)
    g_object_unref (private->palette);

  g_object_unref (private->context);

  g_slice_free (ImportDialog, private);
}


/*  the palette import response callback  ************************************/

static void
palette_import_response (GtkWidget    *dialog,
                         gint          response_id,
                         ImportDialog *private)
{
  palette_import_image_changed (private->context, NULL, private);

  if (response_id == GTK_RESPONSE_OK)
    {
      Gimp *ammoos = private->context->ammoos;

      if (private->palette &&
          gimp_palette_get_n_colors (private->palette) > 0)
        {
          const gchar *name = gtk_entry_get_text (GTK_ENTRY (private->entry));
          GError      *error = NULL;

          if (name && *name)
            gimp_object_set_name (GIMP_OBJECT (private->palette), name);

          if (! gimp_data_factory_data_save_single (ammoos->palette_factory,
                                                    GIMP_DATA (private->palette),
                                                    &error))
            {
              gimp_message (ammoos, G_OBJECT (dialog), GIMP_MESSAGE_ERROR,
                            _("The palette was not imported: %s"),
                            error->message);
              g_clear_error (&error);
              return;
            }

          gimp_container_add (gimp_data_factory_get_container (ammoos->palette_factory),
                              GIMP_OBJECT (private->palette));
        }
      else
        {
          gimp_message_literal (ammoos, G_OBJECT (dialog), GIMP_MESSAGE_ERROR,
                                _("There is no palette to import."));
          return;
        }
    }

  gtk_widget_destroy (dialog);
}


/*  functions to create & update the import dialog's gradient selection  *****/

static void
palette_import_gradient_changed (GimpContext  *context,
                                 GimpGradient *gradient,
                                 ImportDialog *private)
{
  if (gradient && private->import_type == GRADIENT_IMPORT)
    {
      gtk_entry_set_text (GTK_ENTRY (private->entry),
                          gimp_object_get_name (gradient));

      palette_import_make_palette (private);
    }
}

static void
palette_import_image_changed (GimpContext  *context,
                              GimpImage    *image,
                              ImportDialog *private)
{
  if (private->image)
    {
      g_signal_handlers_disconnect_by_func (private->image,
                                            palette_import_layer_changed,
                                            private);
      g_signal_handlers_disconnect_by_func (private->image,
                                            palette_import_mask_changed,
                                            private);
    }

  private->image = image;

  if (private->import_type == IMAGE_IMPORT)
    {
      gboolean sensitive = FALSE;

      if (image)
        {
          gchar *label;

          label = g_strdup_printf ("%s-%d",
                                   gimp_image_get_display_name (image),
                                   gimp_image_get_id (image));

          gtk_entry_set_text (GTK_ENTRY (private->entry), label);
          g_free (label);

          palette_import_make_palette (private);

          if (gimp_image_get_base_type (image) != GIMP_INDEXED)
            sensitive = TRUE;
        }

      gtk_widget_set_sensitive (private->sample_merged_toggle, sensitive);
      gtk_widget_set_sensitive (private->selection_only_toggle, sensitive);
      gtk_widget_set_sensitive (private->threshold, sensitive);
      gtk_widget_set_sensitive (private->num_colors, sensitive);
    }

  if (private->image)
    {
      g_signal_connect (private->image, "selected-layers-changed",
                        G_CALLBACK (palette_import_layer_changed),
                        private);
      g_signal_connect (private->image, "mask-changed",
                        G_CALLBACK (palette_import_mask_changed),
                        private);
    }
}

static void
palette_import_layer_changed (GimpImage    *image,
                              ImportDialog *private)
{
  if (private->import_type == IMAGE_IMPORT &&
      ! gtk_toggle_button_get_active
        (GTK_TOGGLE_BUTTON (private->sample_merged_toggle)))
    {
      palette_import_make_palette (private);
    }
}

static void
palette_import_mask_changed (GimpImage    *image,
                             ImportDialog *private)
{
  if (private->import_type == IMAGE_IMPORT &&
      gtk_toggle_button_get_active
      (GTK_TOGGLE_BUTTON (private->selection_only_toggle)))
    {
      palette_import_make_palette (private);
    }
}

static void
palette_import_filename_changed (GtkFileChooser *button,
                                 ImportDialog   *private)
{
  gchar *filename;

  if (private->import_type != FILE_IMPORT)
    return;

  filename = gtk_file_chooser_get_filename (button);

  if (filename)
    {
      gchar *basename = g_filename_display_basename (filename);

      /* TODO: strip filename extension */
      gtk_entry_set_text (GTK_ENTRY (private->entry), basename);
      g_free (basename);
    }
  else
    {
      gtk_entry_set_text (GTK_ENTRY (private->entry), "");
    }

  g_free (filename);

  palette_import_make_palette (private);
}

static void
import_dialog_drop_callback (GtkWidget    *widget,
                             gint          x,
                             gint          y,
                             GimpViewable *viewable,
                             gpointer      data)
{
  ImportDialog *private = data;

  gimp_context_set_by_type (private->context,
                            G_TYPE_FROM_INSTANCE (viewable),
                            GIMP_OBJECT (viewable));

  if (GIMP_IS_GRADIENT (viewable) &&
      private->import_type != GRADIENT_IMPORT)
    {
      gtk_toggle_button_set_active (GTK_TOGGLE_BUTTON (private->gradient_radio),
                                    TRUE);
    }
  else if (GIMP_IS_IMAGE (viewable) &&
           private->import_type != IMAGE_IMPORT)
    {
      gtk_toggle_button_set_active (GTK_TOGGLE_BUTTON (private->image_radio),
                                    TRUE);
    }
}


/*  the import source menu item callbacks  ***********************************/

static void
palette_import_set_sensitive (ImportDialog *private)
{
  gboolean gradient = (private->import_type == GRADIENT_IMPORT);
  gboolean image    = (private->import_type == IMAGE_IMPORT);
  gboolean file     = (private->import_type == FILE_IMPORT);

  gtk_widget_set_sensitive (private->gradient_combo,        gradient);
  gtk_widget_set_sensitive (private->image_combo,           image);
  gtk_widget_set_sensitive (private->sample_merged_toggle,  image);
  gtk_widget_set_sensitive (private->selection_only_toggle, image);
  gtk_widget_set_sensitive (private->file_chooser,          file);

  gtk_widget_set_sensitive (private->num_colors, ! file);
  gtk_widget_set_sensitive (private->columns,    ! file);
  gtk_widget_set_sensitive (private->threshold,  image);
}

static void
palette_import_grad_callback (GtkWidget    *widget,
                              ImportDialog *private)
{
  GimpGradient *gradient;

  if (! gtk_toggle_button_get_active (GTK_TOGGLE_BUTTON (widget)))
    return;

  private->import_type = GRADIENT_IMPORT;

  gradient = gimp_context_get_gradient (private->context);

  gtk_entry_set_text (GTK_ENTRY (private->entry),
                      gimp_object_get_name (gradient));

  palette_import_set_sensitive (private);

  palette_import_make_palette (private);
}

static void
palette_import_image_callback (GtkWidget    *widget,
                               ImportDialog *private)
{
  GimpImage *image;

  if (! gtk_toggle_button_get_active (GTK_TOGGLE_BUTTON (widget)))
    return;

  private->import_type = IMAGE_IMPORT;

  image = gimp_context_get_image (private->context);

  if (! image)
    {
      GimpContainer *images = private->context->ammoos->images;

      image = GIMP_IMAGE (gimp_container_get_first_child (images));
    }

  palette_import_set_sensitive (private);

  palette_import_image_changed (private->context, image, private);
}

static void
palette_import_file_callback (GtkWidget    *widget,
                              ImportDialog *private)
{
  gchar *filename;

  if (! gtk_toggle_button_get_active (GTK_TOGGLE_BUTTON (widget)))
    return;

  private->import_type = FILE_IMPORT;

  filename =
    gtk_file_chooser_get_filename (GTK_FILE_CHOOSER (private->file_chooser));

  if (filename)
    {
      gchar *basename = g_filename_display_basename (filename);

      /* TODO: strip filename extension */
      gtk_entry_set_text (GTK_ENTRY (private->entry), basename);
      g_free (basename);

      g_free (filename);
    }
  else
    {
      gtk_entry_set_text (GTK_ENTRY (private->entry), "");
    }

  palette_import_set_sensitive (private);
}

static void
palette_import_columns_changed (GimpLabelSpin *columns,
                                ImportDialog  *private)
{
  if (private->palette)
    gimp_palette_set_columns (private->palette,
                              ROUND (gimp_label_spin_get_value (columns)));
}


/*  functions & callbacks to keep the import dialog uptodate  ****************/

static void
palette_import_image_add (GimpContainer *container,
                          GimpImage     *image,
                          ImportDialog  *private)
{
  if (! gtk_widget_is_sensitive (private->image_radio))
    {
      gtk_widget_set_sensitive (private->image_radio, TRUE);
      gimp_context_set_image (private->context, image);
    }
}

static void
palette_import_image_remove (GimpContainer *container,
                             GimpImage     *image,
                             ImportDialog  *private)
{
  if (! gimp_container_get_n_children (private->context->ammoos->images))
    {
      if (gtk_toggle_button_get_active (GTK_TOGGLE_BUTTON (private->image_radio)))
        gtk_toggle_button_set_active (GTK_TOGGLE_BUTTON (private->gradient_radio),
                                      TRUE);

      gtk_widget_set_sensitive (private->image_radio, FALSE);
    }
}

static void
palette_import_make_palette (ImportDialog *private)
{
  GimpPalette  *palette = NULL;
  const gchar  *palette_name;
  gint          n_colors;
  gint          n_columns;
  gint          threshold;

  palette_name = gtk_entry_get_text (GTK_ENTRY (private->entry));

  if (! palette_name || ! strlen (palette_name))
    palette_name = _("Untitled");

  n_colors  = ROUND (gimp_label_spin_get_value (GIMP_LABEL_SPIN (private->num_colors)));
  n_columns = ROUND (gimp_label_spin_get_value (GIMP_LABEL_SPIN (private->columns)));
  threshold = ROUND (gimp_label_spin_get_value (GIMP_LABEL_SPIN (private->threshold)));

  switch (private->import_type)
    {
    case GRADIENT_IMPORT:
      {
        GimpGradient *gradient;

        gradient = gimp_context_get_gradient (private->context);

        palette = gimp_palette_import_from_gradient (gradient,
                                                     private->context,
                                                     FALSE,
                                                     GIMP_GRADIENT_BLEND_RGB_PERCEPTUAL,
                                                     palette_name,
                                                     n_colors);
      }
      break;

    case IMAGE_IMPORT:
      {
        GimpImage *image = gimp_context_get_image (private->context);
        gboolean   sample_merged;
        gboolean   selection_only;

        sample_merged =
          gtk_toggle_button_get_active
          (GTK_TOGGLE_BUTTON (private->sample_merged_toggle));

        selection_only =
          gtk_toggle_button_get_active
          (GTK_TOGGLE_BUTTON (private->selection_only_toggle));

        if (gimp_image_get_base_type (image) == GIMP_INDEXED)
          {
            palette = gimp_palette_import_from_indexed_image (image,
                                                              private->context,
                                                              palette_name);
          }
        else if (sample_merged)
          {
            palette = gimp_palette_import_from_image (image,
                                                      private->context,
                                                      palette_name,
                                                      n_colors,
                                                      threshold,
                                                      selection_only);
          }
        else
          {
            GList *drawables;

            drawables = gimp_image_get_selected_layers (image);

            if (drawables)
              palette = gimp_palette_import_from_drawables (drawables,
                                                            private->context,
                                                            palette_name,
                                                            n_colors,
                                                            threshold,
                                                            selection_only);
          }
      }
      break;

    case FILE_IMPORT:
      {
        GFile  *file;
        GError *error = NULL;

        file = gtk_file_chooser_get_file (GTK_FILE_CHOOSER (private->file_chooser));

        palette = gimp_palette_import_from_file (private->context,
                                                 file,
                                                 palette_name, &error);
        g_object_unref (file);

        if (! palette)
          {
            gimp_message_literal (private->context->ammoos,
                                  G_OBJECT (private->dialog), GIMP_MESSAGE_ERROR,
                                  error->message);
            g_error_free (error);
          }
        else
          {
            gint columns = gimp_palette_get_columns (palette);

            if (columns > 0)
              {
                n_columns = columns;

                gimp_label_spin_set_value (GIMP_LABEL_SPIN (private->columns),
                                           n_columns);
              }
          }
      }
      break;
    }

  if (private->palette)
    g_object_unref (private->palette);

  private->palette = palette;

  if (palette)
    {
      gimp_palette_set_columns (palette, n_columns);

      gimp_view_set_viewable (GIMP_VIEW (private->preview),
                              GIMP_VIEWABLE (palette));

    }

  gtk_widget_set_visible (private->no_colors_label,
                          ! (palette &&
                             gimp_palette_get_n_colors (palette) > 0));
}

static void
palette_import_file_set_filters (GtkFileChooser *file_chooser)
{
  GtkFileFilter *filter;

  filter = gtk_file_filter_new ();
  gtk_file_filter_set_name (filter, _("All palette files (*.*)"));
  gtk_file_filter_add_pattern (filter, "*");
  gtk_file_chooser_add_filter (file_chooser, filter);

  filter = gtk_file_filter_new ();
  gtk_file_filter_set_name (filter, _("AmmoOS Image Palette (*.gpl)"));
  gtk_file_filter_add_pattern (filter, "*.gpl");
  gtk_file_filter_add_pattern (filter, "*.GPL");
  gtk_file_chooser_add_filter (file_chooser, filter);

  filter = gtk_file_filter_new ();
  gtk_file_filter_set_name (filter, _("Adobe Color Table (*.act)"));
  gtk_file_filter_add_pattern (filter, "*.act");
  gtk_file_filter_add_pattern (filter, "*.ACT");
  gtk_file_chooser_add_filter (file_chooser, filter);

  filter = gtk_file_filter_new ();
  gtk_file_filter_set_name (filter, _("Adobe Color Swatch (*.aco)"));
  gtk_file_filter_add_pattern (filter, "*.aco");
  gtk_file_filter_add_pattern (filter, "*.ACO");
  gtk_file_chooser_add_filter (file_chooser, filter);

  filter = gtk_file_filter_new ();
  gtk_file_filter_set_name (filter, _("Adobe Color Book (*.acb)"));
  gtk_file_filter_add_pattern (filter, "*.acb");
  gtk_file_filter_add_pattern (filter, "*.ACB");
  gtk_file_chooser_add_filter (file_chooser, filter);

  filter = gtk_file_filter_new ();
  gtk_file_filter_set_name (filter, _("Adobe Swatch Exchange (*.ase)"));
  gtk_file_filter_add_pattern (filter, "*.ase");
  gtk_file_filter_add_pattern (filter, "*.ASE");
  gtk_file_chooser_add_filter (file_chooser, filter);

  filter = gtk_file_filter_new ();
  gtk_file_filter_set_name (filter, _("Cascading Style Sheet (*.css)"));
  gtk_file_filter_add_pattern (filter, "*.css");
  gtk_file_filter_add_pattern (filter, "*.CSS");
  gtk_file_chooser_add_filter (file_chooser, filter);

  filter = gtk_file_filter_new ();
  gtk_file_filter_set_name (filter, _("JASC or RIFF Palette (*.pal)"));
  gtk_file_filter_add_pattern (filter, "*.pal");
  gtk_file_filter_add_pattern (filter, "*.PAL");
  gtk_file_chooser_add_filter (file_chooser, filter);

 filter = gtk_file_filter_new ();
  gtk_file_filter_set_name (filter, "Krita (*.kpl)");
  gtk_file_filter_add_pattern (filter, "*.kpl");
  gtk_file_filter_add_pattern (filter, "*.KPL");
  gtk_file_chooser_add_filter (file_chooser, filter);

  filter = gtk_file_filter_new ();
  gtk_file_filter_set_name (filter, "Procreate (*.swatches)");
  gtk_file_filter_add_pattern (filter, "*.swatches");
  gtk_file_filter_add_pattern (filter, "*.SWATCHES");
  gtk_file_chooser_add_filter (file_chooser, filter);

  filter = gtk_file_filter_new ();
  gtk_file_filter_set_name (filter, _("SwatchBooker (*.sbz)"));
  gtk_file_filter_add_pattern (filter, "*.sbz");
  gtk_file_filter_add_pattern (filter, "*.SBZ");
  gtk_file_chooser_add_filter (file_chooser, filter);
}

/* --- path-export-dialog.c --- */
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

#include "libgimpwidgets/gimpwidgets.h"

#include "dialogs-types.h"

#include "core/gimpimage.h"

#include "widgets/gimpwidgets-utils.h"

#include "path-export-dialog.h"

#include "ammoos-intl.h"


typedef struct _PathExportDialog PathExportDialog;

struct _PathExportDialog
{
  GimpImage              *image;
  gboolean                active_only;
  GimpPathExportCallback  callback;
  gpointer                user_data;
};


/*  local function prototypes  */
#ifdef G_OS_WIN32
static void   path_export_dialog_realize  (GtkWidget           *dialog,
                                           PathExportDialog *data);
#endif
static void   path_export_dialog_free     (PathExportDialog *private);
static void   path_export_dialog_response (GtkWidget           *widget,
                                           gint                 response_id,
                                           PathExportDialog *private);


/*  public function  */

GtkWidget *
path_export_dialog_new (GimpImage              *image,
                        GtkWidget              *parent,
                        GFile                  *export_folder,
                        gboolean                active_only,
                        GimpPathExportCallback  callback,
                        gpointer                user_data)
{
  PathExportDialog *private;
  GtkWidget        *dialog;

  g_return_val_if_fail (GIMP_IS_IMAGE (image), NULL);
  g_return_val_if_fail (GTK_IS_WIDGET (parent), NULL);
  g_return_val_if_fail (export_folder == NULL || G_IS_FILE (export_folder),
                        NULL);
  g_return_val_if_fail (callback != NULL, NULL);

  private = g_slice_new0 (PathExportDialog);

  private->image       = image;
  private->active_only = active_only;
  private->callback    = callback;
  private->user_data   = user_data;

  dialog = gtk_file_chooser_dialog_new (_("Export Path to SVG"), NULL,
                                        GTK_FILE_CHOOSER_ACTION_SAVE,

                                        _("_Cancel"), GTK_RESPONSE_CANCEL,
                                        _("_Save"),   GTK_RESPONSE_OK,

                                        NULL);

  gtk_dialog_set_default_response (GTK_DIALOG (dialog), GTK_RESPONSE_OK);
  gimp_dialog_set_alternative_button_order (GTK_DIALOG (dialog),
                                            GTK_RESPONSE_OK,
                                            GTK_RESPONSE_CANCEL,
                                            -1);

  gtk_window_set_role (GTK_WINDOW (dialog), "ammoos-paths-export");
  gtk_window_set_position (GTK_WINDOW (dialog), GTK_WIN_POS_MOUSE);
  gtk_window_set_screen (GTK_WINDOW (dialog),
                         gtk_widget_get_screen (parent));

  gtk_file_chooser_set_do_overwrite_confirmation (GTK_FILE_CHOOSER (dialog),
                                                  TRUE);

  if (export_folder)
    gtk_file_chooser_set_current_folder_file (GTK_FILE_CHOOSER (dialog),
                                              export_folder, NULL);

  g_object_weak_ref (G_OBJECT (dialog),
                     (GWeakNotify) path_export_dialog_free, private);

  g_signal_connect_object (image, "disconnect",
                           G_CALLBACK (gtk_widget_destroy),
                           dialog, 0);

#ifdef G_OS_WIN32
  g_signal_connect (dialog, "realize",
                    G_CALLBACK (path_export_dialog_realize),
                    private);
#endif
  g_signal_connect (dialog, "delete-event",
                    G_CALLBACK (gtk_true),
                    NULL);

  g_signal_connect (dialog, "response",
                    G_CALLBACK (path_export_dialog_response),
                    private);

  /* Add dropdown option for which path(s) to export */
  if (dialog)
    {
      const gchar *options[3] = { "selected", "all", NULL };
      const gchar *labels[3]  = { _("Export the selected paths"),
                                  _("Export all paths from this image"),
                                  NULL };

      gtk_file_chooser_add_choice (GTK_FILE_CHOOSER (dialog), "export-paths",
                                   NULL, options, labels);
      gtk_file_chooser_set_choice (GTK_FILE_CHOOSER (dialog), "export-paths",
                                   private->active_only ? "selected" : "all");
    }

  return dialog;
}


/*  private functions  */

#ifdef G_OS_WIN32
static void
path_export_dialog_realize (GtkWidget        *dialog,
                            PathExportDialog *data)
{
  gimp_window_set_title_bar_theme (data->image->ammoos, dialog);
}
#endif

static void
path_export_dialog_free (PathExportDialog *private)
{
  g_slice_free (PathExportDialog, private);
}

static void
path_export_dialog_response (GtkWidget        *dialog,
                             gint              response_id,
                             PathExportDialog *private)
{
  if (response_id == GTK_RESPONSE_OK)
    {
      GtkFileChooser *chooser = GTK_FILE_CHOOSER (dialog);
      GFile          *file;
      const gchar    *export_paths;

      file         = gtk_file_chooser_get_file (chooser);
      export_paths = gtk_file_chooser_get_choice (chooser, "export-paths");

      private->active_only = (! g_strcmp0 (export_paths, "selected"));

      if (file)
        {
          GFile *folder;

          folder = gtk_file_chooser_get_current_folder_file (chooser);

          private->callback (dialog,
                             private->image,
                             file,
                             folder,
                             private->active_only,
                             private->user_data);

          if (folder)
            g_object_unref (folder);

          g_object_unref (file);
        }
    }
  else
    {
      gtk_widget_destroy (dialog);
    }
}

/* --- path-import-dialog.c --- */
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

#include "libgimpwidgets/gimpwidgets.h"

#include "dialogs-types.h"

#include "core/gimpimage.h"

#include "widgets/gimpwidgets-utils.h"

#include "path-import-dialog.h"

#include "ammoos-intl.h"


typedef struct _PathImportDialog PathImportDialog;

struct _PathImportDialog
{
  GimpImage              *image;
  gboolean                merge_paths;
  gboolean                scale_paths;
  GimpPathImportCallback  callback;
  gpointer                user_data;
};


/*  local function prototypes  */
#ifdef G_OS_WIN32
static void   path_import_dialog_realize  (GtkWidget        *dialog,
                                           PathImportDialog *data);
#endif
static void   path_import_dialog_free     (PathImportDialog *private);
static void   path_import_dialog_response (GtkWidget        *dialog,
                                           gint              response_id,
                                           PathImportDialog *private);


/*  public function  */

GtkWidget *
path_import_dialog_new (GimpImage              *image,
                        GtkWidget              *parent,
                        GFile                  *import_folder,
                        gboolean                merge_paths,
                        gboolean                scale_paths,
                        GimpPathImportCallback  callback,
                        gpointer                user_data)
{
  PathImportDialog *private;
  GtkWidget        *dialog;
  GtkWidget        *vbox;
  GtkWidget        *button;
  GtkFileFilter    *filter;

  g_return_val_if_fail (GIMP_IS_IMAGE (image), NULL);
  g_return_val_if_fail (GTK_IS_WIDGET (parent), NULL);
  g_return_val_if_fail (import_folder == NULL || G_IS_FILE (import_folder),
                        NULL);
  g_return_val_if_fail (callback != NULL, NULL);

  private = g_slice_new0 (PathImportDialog);

  private->image       = image;
  private->merge_paths = merge_paths;
  private->scale_paths = scale_paths;
  private->callback    = callback;
  private->user_data   = user_data;

  dialog = gtk_file_chooser_dialog_new (_("Import Paths from SVG"), NULL,
                                        GTK_FILE_CHOOSER_ACTION_OPEN,

                                        _("_Cancel"), GTK_RESPONSE_CANCEL,
                                        _("_Open"),   GTK_RESPONSE_OK,

                                        NULL);

  gtk_dialog_set_default_response (GTK_DIALOG (dialog), GTK_RESPONSE_OK);
  gimp_dialog_set_alternative_button_order (GTK_DIALOG (dialog),
                                           GTK_RESPONSE_OK,
                                           GTK_RESPONSE_CANCEL,
                                           -1);

  gtk_window_set_role (GTK_WINDOW (dialog), "ammoos-paths-import");
  gtk_window_set_position (GTK_WINDOW (dialog), GTK_WIN_POS_MOUSE);
  gtk_window_set_screen (GTK_WINDOW (dialog),
                         gtk_widget_get_screen (parent));

  if (import_folder)
    gtk_file_chooser_set_current_folder_file (GTK_FILE_CHOOSER (dialog),
                                              import_folder, NULL);

  g_object_weak_ref (G_OBJECT (dialog),
                     (GWeakNotify) path_import_dialog_free, private);

  g_signal_connect_object (image, "disconnect",
                           G_CALLBACK (gtk_widget_destroy),
                           dialog, 0);

#ifdef G_OS_WIN32
  g_signal_connect (dialog, "realize",
                    G_CALLBACK (path_import_dialog_realize),
                    private);
#endif
  g_signal_connect (dialog, "delete-event",
                    G_CALLBACK (gtk_true),
                    NULL);

  g_signal_connect (dialog, "response",
                    G_CALLBACK (path_import_dialog_response),
                    private);

  filter = gtk_file_filter_new ();
  gtk_file_filter_set_name (filter, _("All files (*.*)"));
  gtk_file_filter_add_pattern (filter, "*");
  gtk_file_chooser_add_filter (GTK_FILE_CHOOSER (dialog), filter);

  filter = gtk_file_filter_new ();
  gtk_file_filter_set_name (filter, _("Scalable SVG image (*.svg)"));
  gtk_file_filter_add_pattern (filter, "*.[Ss][Vv][Gg]");
  gtk_file_filter_add_mime_type (filter, "image/svg+xml");
  gtk_file_chooser_add_filter (GTK_FILE_CHOOSER (dialog), filter);

  gtk_file_chooser_set_filter (GTK_FILE_CHOOSER (dialog), filter);

  vbox = gtk_box_new (GTK_ORIENTATION_VERTICAL, 6);
  gtk_file_chooser_set_extra_widget (GTK_FILE_CHOOSER (dialog), vbox);
  gtk_widget_set_visible (vbox, TRUE);

  button = gtk_check_button_new_with_mnemonic (_("_Merge imported paths"));
  gtk_toggle_button_set_active (GTK_TOGGLE_BUTTON (button),
                                private->merge_paths);
  gtk_box_pack_start (GTK_BOX (vbox), button, FALSE, FALSE, 0);
  gtk_widget_set_visible (button, TRUE);

  g_signal_connect (button, "toggled",
                    G_CALLBACK (gimp_toggle_button_update),
                    &private->merge_paths);

  button = gtk_check_button_new_with_mnemonic (_("_Scale imported paths "
                                                 "to fit image"));
  gtk_toggle_button_set_active (GTK_TOGGLE_BUTTON (button),
                                private->scale_paths);
  gtk_box_pack_start (GTK_BOX (vbox), button, FALSE, FALSE, 0);
  gtk_widget_set_visible (button, TRUE);

  g_signal_connect (button, "toggled",
                    G_CALLBACK (gimp_toggle_button_update),
                    &private->scale_paths);

  return dialog;
}


/*  private functions  */

#ifdef G_OS_WIN32
static void
path_import_dialog_realize (GtkWidget        *dialog,
                            PathImportDialog *data)
{
  gimp_window_set_title_bar_theme (data->image->ammoos, dialog);
}
#endif

static void
path_import_dialog_free (PathImportDialog *private)
{
  g_slice_free (PathImportDialog, private);
}

static void
path_import_dialog_response (GtkWidget        *dialog,
                             gint              response_id,
                             PathImportDialog *private)
{
  if (response_id == GTK_RESPONSE_OK)
    {
      GtkFileChooser *chooser = GTK_FILE_CHOOSER (dialog);
      GFile          *file;

      file = gtk_file_chooser_get_file (chooser);

      if (file)
        {
          GFile *folder;

          folder = gtk_file_chooser_get_current_folder_file (chooser);

          private->callback (dialog,
                             private->image,
                             file,
                             folder,
                             private->merge_paths,
                             private->scale_paths,
                             private->user_data);

          if (folder)
            g_object_unref (folder);

          g_object_unref (file);
        }
    }
  else
    {
      gtk_widget_destroy (dialog);
    }
}

/* --- path-options-dialog.c --- */
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

#include "libgimpwidgets/gimpwidgets.h"

#include "dialogs-types.h"

#include "core/gimpcontext.h"
#include "core/gimpimage.h"

#include "path/gimppath.h"

#include "item-options-dialog.h"
#include "path-options-dialog.h"

#include "ammoos-intl.h"


typedef struct _PathOptionsDialog PathOptionsDialog;

struct _PathOptionsDialog
{
  GimpPathOptionsCallback  callback;
  gpointer                 user_data;
};


/*  local function prototypes  */

static void  path_options_dialog_free     (PathOptionsDialog *private);
static void  path_options_dialog_callback (GtkWidget         *dialog,
                                           GimpImage         *image,
                                           GimpItem          *item,
                                           GimpContext       *context,
                                           const gchar       *item_name,
                                           gboolean           item_visible,
                                           GimpColorTag       item_color_tag,
                                           gboolean           item_lock_content,
                                           gboolean           item_lock_position,
                                           gboolean           item_lock_visibility,
                                           gpointer           user_data);


/*  public functions  */

GtkWidget *
path_options_dialog_new (GimpImage               *image,
                         GimpPath                *path,
                         GimpContext             *context,
                         GtkWidget               *parent,
                         const gchar             *title,
                         const gchar             *role,
                         const gchar             *icon_name,
                         const gchar             *desc,
                         const gchar             *help_id,
                         const gchar             *path_name,
                         gboolean                 path_visible,
                         GimpColorTag             path_color_tag,
                         gboolean                 path_lock_content,
                         gboolean                 path_lock_position,
                         gboolean                 path_lock_visibility,
                         GimpPathOptionsCallback  callback,
                         gpointer                 user_data)
{
  PathOptionsDialog *private;
  GtkWidget         *dialog;

  g_return_val_if_fail (GIMP_IS_IMAGE (image), NULL);
  g_return_val_if_fail (path == NULL || GIMP_IS_PATH (path), NULL);
  g_return_val_if_fail (GIMP_IS_CONTEXT (context), NULL);
  g_return_val_if_fail (GTK_IS_WIDGET (parent), NULL);
  g_return_val_if_fail (title != NULL, NULL);
  g_return_val_if_fail (role != NULL, NULL);
  g_return_val_if_fail (icon_name != NULL, NULL);
  g_return_val_if_fail (desc != NULL, NULL);
  g_return_val_if_fail (help_id != NULL, NULL);
  g_return_val_if_fail (callback != NULL, NULL);

  private = g_slice_new0 (PathOptionsDialog);

  private->callback  = callback;
  private->user_data = user_data;

  dialog = item_options_dialog_new (image, GIMP_ITEM (path), context,
                                    parent, title, role,
                                    icon_name, desc, help_id,
                                    _("Path _name:"),
                                    GIMP_ICON_LOCK_PATH,
                                    _("Lock p_ath"),
                                    _("Lock path _position"),
                                    _("Lock path _visibility"),
                                    path_name,
                                    path_visible,
                                    path_color_tag,
                                    path_lock_content,
                                    path_lock_position,
                                    path_lock_visibility,
                                    path_options_dialog_callback,
                                    private);

  g_object_weak_ref (G_OBJECT (dialog),
                     (GWeakNotify) path_options_dialog_free, private);

  return dialog;
}


/*  private functions  */

static void
path_options_dialog_free (PathOptionsDialog *private)
{
  g_slice_free (PathOptionsDialog, private);
}

static void
path_options_dialog_callback (GtkWidget    *dialog,
                              GimpImage    *image,
                              GimpItem     *item,
                              GimpContext  *context,
                              const gchar  *item_name,
                              gboolean      item_visible,
                              GimpColorTag  item_color_tag,
                              gboolean      item_lock_content,
                              gboolean      item_lock_position,
                              gboolean      item_lock_visibility,
                              gpointer      user_data)
{
  PathOptionsDialog *private = user_data;

  private->callback (dialog,
                     image,
                     GIMP_PATH (item),
                     context,
                     item_name,
                     item_visible,
                     item_color_tag,
                     item_lock_content,
                     item_lock_position,
                     item_lock_visibility,
                     private->user_data);
}

/* --- preferences-dialog-utils.c --- */
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

#include "config.h"

#include <gegl.h>
#include <gtk/gtk.h>

#include "libgimpcolor/gimpcolor.h"
#include "libgimpconfig/gimpconfig.h"
#include "libgimpwidgets/gimpwidgets.h"

#include "dialogs-types.h"

#include "config/gimprc.h"

#include "widgets/gimpcolorpanel.h"
#include "widgets/gimppropwidgets.h"
#include "widgets/gimpwidgets-constructors.h"

#include "preferences-dialog-utils.h"


GtkWidget *
prefs_frame_new (const gchar  *label,
                 GtkContainer *parent,
                 gboolean      expand)
{
  GtkWidget *frame;
  GtkWidget *vbox;

  frame = gimp_frame_new (label);

  vbox = gtk_box_new (GTK_ORIENTATION_VERTICAL, 6);
  gtk_container_add (GTK_CONTAINER (frame), vbox);
  gtk_widget_set_visible (vbox, TRUE);

  if (GTK_IS_BOX (parent))
    gtk_box_pack_start (GTK_BOX (parent), frame, expand, expand, 0);
  else
    gtk_container_add (parent, frame);

  gtk_widget_set_visible (frame, TRUE);

  return vbox;
}

GtkWidget *
prefs_grid_new (GtkContainer *parent)
{
  GtkWidget *grid;

  grid = gtk_grid_new ();

  gtk_grid_set_row_spacing (GTK_GRID (grid), 6);
  gtk_grid_set_column_spacing (GTK_GRID (grid), 6);

  if (GTK_IS_BOX (parent))
    gtk_box_pack_start (GTK_BOX (parent), grid, FALSE, FALSE, 0);
  else
    gtk_container_add (parent, grid);

  gtk_widget_set_visible (grid, TRUE);

  return grid;
}

GtkWidget *
prefs_hint_box_new (const gchar  *icon_name,
                    const gchar  *text)
{
  GtkWidget *hbox;
  GtkWidget *image;
  GtkWidget *label;

  hbox = gtk_box_new (GTK_ORIENTATION_HORIZONTAL, 6);

  image = gtk_image_new_from_icon_name (icon_name, GTK_ICON_SIZE_BUTTON);
  gtk_box_pack_start (GTK_BOX (hbox), image, FALSE, FALSE, 0);
  gtk_widget_set_visible (image, TRUE);

  label = gtk_label_new (text);
  gimp_label_set_attributes (GTK_LABEL (label),
                             PANGO_ATTR_STYLE, PANGO_STYLE_ITALIC,
                             -1);
  gtk_label_set_line_wrap (GTK_LABEL (label), TRUE);
  gtk_label_set_xalign (GTK_LABEL (label), 0.0);

  gtk_box_pack_start (GTK_BOX (hbox), label, TRUE, TRUE, 0);
  gtk_widget_set_visible (label, TRUE);

  gtk_widget_set_visible (hbox, TRUE);

  return hbox;
}

GtkWidget *
prefs_button_add (const gchar *icon_name,
                  const gchar *label,
                  GtkBox      *box)
{
  GtkWidget *button;

  button = gimp_icon_button_new (icon_name, label);
  gtk_box_pack_start (GTK_BOX (box), button, FALSE, FALSE, 0);
  gtk_widget_set_visible (button, TRUE);

  return button;
}

GtkWidget *
prefs_check_button_add (GObject     *config,
                        const gchar *property_name,
                        const gchar *label,
                        GtkBox      *vbox)
{
  GtkWidget *button;

  button = gimp_prop_check_button_new (config, property_name, label);

  if (button)
    gtk_box_pack_start (vbox, button, FALSE, FALSE, 0);

  return button;
}

GtkWidget *
prefs_switch_add (GObject      *config,
                  const gchar  *property_name,
                  const gchar  *label,
                  GtkBox       *vbox,
                  GtkSizeGroup *group,
                  GtkWidget   **switch_out)
{
  GtkWidget *box;
  GtkWidget *plabel;

  box = gimp_prop_switch_new (config, property_name, label, &plabel,
                              switch_out);

  if (!box)
    return NULL;

  gtk_box_pack_start (vbox, box, FALSE, FALSE, 0);
  gtk_label_set_xalign (GTK_LABEL (plabel), 0.0);
  if (group)
    gtk_size_group_add_widget (group, plabel);

  return box;
}

GtkWidget *
prefs_check_button_add_with_icon (GObject      *config,
                                  const gchar  *property_name,
                                  const gchar  *label,
                                  const gchar  *icon_name,
                                  GtkBox       *vbox,
                                  GtkSizeGroup *group)
{
  GtkWidget *button;
  GtkWidget *hbox;
  GtkWidget *image;

  button = gimp_prop_check_button_new (config, property_name, label);
  if (! button)
    return NULL;

  hbox = gtk_box_new (GTK_ORIENTATION_HORIZONTAL, 6);
  gtk_box_pack_start (vbox, hbox, FALSE, FALSE, 0);
  gtk_widget_set_visible (hbox, TRUE);

  image = gtk_image_new_from_icon_name (icon_name, GTK_ICON_SIZE_BUTTON);
  g_object_set (image,
                "margin-start",  2,
                "margin-end",    2,
                "margin-top",    2,
                "margin-bottom", 2,
                NULL);
  gtk_box_pack_start (GTK_BOX (hbox), image, FALSE, FALSE, 0);
  gtk_widget_set_visible (image, TRUE);

  gtk_box_pack_start (GTK_BOX (hbox), button, TRUE, TRUE, 0);

  if (group)
    gtk_size_group_add_widget (group, image);

  return button;
}

GtkWidget *
prefs_widget_add_aligned (GtkWidget    *widget,
                          const gchar  *text,
                          GtkGrid      *grid,
                          gint          grid_top,
                          gboolean      left_align,
                          GtkSizeGroup *group)
{
  GtkWidget *label = gimp_grid_attach_aligned (grid, 0, grid_top,
                                               text, 0.0, 0.5,
                                               widget, 1);
  if (group)
    gtk_size_group_add_widget (group, label);

  if (left_align == TRUE)
    gtk_widget_set_halign (widget, GTK_ALIGN_START);

  return label;
}

GtkWidget *
prefs_color_button_add (GObject      *config,
                        const gchar  *property_name,
                        const gchar  *label,
                        const gchar  *title,
                        GtkGrid      *grid,
                        gint          grid_top,
                        GtkSizeGroup *group,
                        GimpContext  *context)
{
  GtkWidget  *button;
  GParamSpec *pspec;
  gboolean    has_alpha;

  pspec = g_object_class_find_property (G_OBJECT_GET_CLASS (config),
                                        property_name);

  has_alpha = gimp_param_spec_color_has_alpha (pspec);

  button = gimp_prop_color_button_new (config, property_name,
                                       title, FALSE,
                                       PREFS_COLOR_BUTTON_WIDTH,
                                       PREFS_COLOR_BUTTON_HEIGHT,
                                       has_alpha ?
                                       GIMP_COLOR_AREA_SMALL_CHECKS :
                                       GIMP_COLOR_AREA_FLAT);

  if (button)
    {
      if (context)
        gimp_color_panel_set_context (GIMP_COLOR_PANEL (button), context);

      prefs_widget_add_aligned (button, label, grid, grid_top, TRUE, group);
    }

  return button;
}

GtkWidget *
prefs_entry_add (GObject      *config,
                 const gchar  *property_name,
                 const gchar  *label,
                 GtkGrid      *grid,
                 gint          grid_top,
                 GtkSizeGroup *group)
{
  GtkWidget *entry = gimp_prop_entry_new (config, property_name, -1);

  if (entry)
    prefs_widget_add_aligned (entry, label, grid, grid_top, FALSE, group);

  return entry;
}

GtkWidget *
prefs_spin_button_add (GObject      *config,
                       const gchar  *property_name,
                       gdouble       step_increment,
                       gdouble       page_increment,
                       gint          digits,
                       const gchar  *label,
                       GtkGrid      *grid,
                       gint          grid_top,
                       GtkSizeGroup *group)
{
  GtkWidget *button = gimp_prop_spin_button_new (config, property_name,
                                                 step_increment,
                                                 page_increment,
                                                 digits);

  if (button)
    prefs_widget_add_aligned (button, label, grid, grid_top, TRUE, group);

  return button;
}

GtkWidget *
prefs_memsize_entry_add (GObject      *config,
                         const gchar  *property_name,
                         const gchar  *label,
                         GtkGrid      *grid,
                         gint          grid_top,
                         GtkSizeGroup *group)
{
  GtkWidget *entry = gimp_prop_memsize_entry_new (config, property_name);

  if (entry)
    prefs_widget_add_aligned (entry, label, grid, grid_top, TRUE, group);

  return entry;
}

GtkWidget *
prefs_file_chooser_button_add (GObject      *config,
                               const gchar  *property_name,
                               const gchar  *label,
                               const gchar  *dialog_title,
                               GtkGrid      *grid,
                               gint          grid_top,
                               GtkSizeGroup *group)
{
  GtkWidget *button;

  button = gimp_prop_file_chooser_button_new (config, property_name,
                                              dialog_title,
                                              GTK_FILE_CHOOSER_ACTION_SELECT_FOLDER);

  if (button)
    prefs_widget_add_aligned (button, label, grid, grid_top, FALSE, group);

  return button;
}

GtkWidget *
prefs_enum_combo_box_add (GObject      *config,
                          const gchar  *property_name,
                          gint          minimum,
                          gint          maximum,
                          const gchar  *label,
                          GtkGrid      *grid,
                          gint          grid_top,
                          GtkSizeGroup *group)
{
  GtkWidget *combo = gimp_prop_enum_combo_box_new (config, property_name,
                                                   minimum, maximum);

  if (combo)
    prefs_widget_add_aligned (combo, label, grid, grid_top, FALSE, group);

  return combo;
}

GtkWidget *
prefs_boolean_combo_box_add (GObject      *config,
                             const gchar  *property_name,
                             const gchar  *true_text,
                             const gchar  *false_text,
                             const gchar  *label,
                             GtkGrid      *grid,
                             gint          grid_top,
                             GtkSizeGroup *group)
{
  GtkWidget *combo = gimp_prop_boolean_combo_box_new (config, property_name,
                                                      true_text, false_text);

  if (combo)
    prefs_widget_add_aligned (combo, label, grid, grid_top, FALSE, group);

  return combo;
}

#ifdef HAVE_ISO_CODES
GtkWidget *
prefs_language_combo_box_add (GObject      *config,
                              const gchar  *property_name,
                              GtkBox       *vbox)
{
  GtkWidget *combo = gimp_prop_language_combo_box_new (config, property_name);

  if (combo)
    gtk_box_pack_start (vbox, combo, FALSE, FALSE, 0);

  return combo;
}
#endif

GtkWidget *
prefs_profile_combo_box_add (GObject      *config,
                             const gchar  *property_name,
                             GtkListStore *profile_store,
                             const gchar  *dialog_title,
                             const gchar  *label,
                             GtkGrid      *grid,
                             gint          grid_top,
                             GtkSizeGroup *group,
                             GObject      *profile_path_config,
                             const gchar  *profile_path_property_name)
{
  GtkWidget *combo = gimp_prop_profile_combo_box_new (config,
                                                      property_name,
                                                      profile_store,
                                                      dialog_title,
                                                      profile_path_config,
                                                      profile_path_property_name);

  if (combo)
    prefs_widget_add_aligned (combo, label, grid, grid_top, FALSE, group);

  return combo;
}

GtkWidget *
prefs_compression_combo_box_add (GObject      *config,
                                 const gchar  *property_name,
                                 const gchar  *label,
                                 GtkGrid      *grid,
                                 gint          grid_top,
                                 GtkSizeGroup *group)
{
  GtkWidget *combo = gimp_prop_compression_combo_box_new (config,
                                                          property_name);

  if (combo)
    prefs_widget_add_aligned (combo, label, grid, grid_top, FALSE, group);

  return combo;
}

void
prefs_message (GtkWidget      *dialog,
               GtkMessageType  type,
               gboolean        destroy_with_parent,
               const gchar    *message)
{
  GtkWidget *message_dialog;

  message_dialog = gtk_message_dialog_new (GTK_WINDOW (dialog),
                                           destroy_with_parent ?
                                           GTK_DIALOG_DESTROY_WITH_PARENT : 0,
                                           type, GTK_BUTTONS_OK,
                                           "%s", message);

  gtk_dialog_run (GTK_DIALOG (message_dialog));

  gtk_widget_destroy (message_dialog);
}

void
prefs_config_notify (GObject    *config,
                     GParamSpec *param_spec,
                     GObject    *config_copy)
{
  GValue global_value = G_VALUE_INIT;
  GValue copy_value   = G_VALUE_INIT;

  g_value_init (&global_value, param_spec->value_type);
  g_value_init (&copy_value,   param_spec->value_type);

  g_object_get_property (config,      param_spec->name, &global_value);
  g_object_get_property (config_copy, param_spec->name, &copy_value);

  if (g_param_values_cmp (param_spec, &global_value, &copy_value))
    {
      g_signal_handlers_block_by_func (config_copy,
                                       prefs_config_copy_notify,
                                       config);

      g_object_set_property (config_copy, param_spec->name, &global_value);

      g_signal_handlers_unblock_by_func (config_copy,
                                         prefs_config_copy_notify,
                                         config);
    }

  g_value_unset (&global_value);
  g_value_unset (&copy_value);
}

void
prefs_config_copy_notify (GObject    *config_copy,
                          GParamSpec *param_spec,
                          GObject    *config)
{
  GValue copy_value   = G_VALUE_INIT;
  GValue global_value = G_VALUE_INIT;

  g_value_init (&copy_value,   param_spec->value_type);
  g_value_init (&global_value, param_spec->value_type);

  g_object_get_property (config_copy, param_spec->name, &copy_value);
  g_object_get_property (config,      param_spec->name, &global_value);

  if (g_param_values_cmp (param_spec, &copy_value, &global_value))
    {
      if (param_spec->flags & GIMP_CONFIG_PARAM_CONFIRM)
        {
#ifdef GIMP_CONFIG_DEBUG
          g_print ("NOT Applying prefs change of '%s' to edit_config "
                   "because it needs confirmation\n",
                   param_spec->name);
#endif
        }
      else
        {
#ifdef GIMP_CONFIG_DEBUG
          g_print ("Applying prefs change of '%s' to edit_config\n",
                   param_spec->name);
#endif
          g_signal_handlers_block_by_func (config,
                                           prefs_config_notify,
                                           config_copy);

          g_object_set_property (config, param_spec->name, &copy_value);

          g_signal_handlers_unblock_by_func (config,
                                             prefs_config_notify,
                                             config_copy);
        }
    }

  g_value_unset (&copy_value);
  g_value_unset (&global_value);
}

void
prefs_font_size_value_changed (GtkRange      *range,
                               GimpGuiConfig *config)
{
  gdouble value = gtk_range_get_value (range);

  g_signal_handlers_block_by_func (config,
                                   G_CALLBACK (prefs_gui_config_notify_font_size),
                                   range);
  g_object_set (G_OBJECT (config),
                "font-relative-size", value / 100.0,
                NULL);
  g_signal_handlers_unblock_by_func (config,
                                     G_CALLBACK (prefs_gui_config_notify_font_size),
                                     range);
}

void
prefs_gui_config_notify_font_size (GObject    *config,
                                   GParamSpec *pspec,
                                   GtkRange   *range)
{
  g_signal_handlers_block_by_func (range,
                                   G_CALLBACK (prefs_font_size_value_changed),
                                   config);
  gtk_range_set_value (range,
                       GIMP_GUI_CONFIG (config)->font_relative_size * 100.0);
  g_signal_handlers_unblock_by_func (range,
                                     G_CALLBACK (prefs_font_size_value_changed),
                                     config);
}

void
prefs_icon_size_value_changed (GtkRange      *range,
                               GimpGuiConfig *config)
{
  gint value = (gint) gtk_range_get_value (range);

  g_signal_handlers_block_by_func (config,
                                   G_CALLBACK (prefs_gui_config_notify_icon_size),
                                   range);
  g_object_set (G_OBJECT (config),
                "custom-icon-size", (GimpIconSize) value,
                NULL);
  g_signal_handlers_unblock_by_func (config,
                                     G_CALLBACK (prefs_gui_config_notify_icon_size),
                                     range);
}

void
prefs_gui_config_notify_icon_size (GObject    *config,
                                   GParamSpec *pspec,
                                   GtkRange   *range)
{
  GimpIconSize size = GIMP_GUI_CONFIG (config)->custom_icon_size;

  g_signal_handlers_block_by_func (range,
                                   G_CALLBACK (prefs_icon_size_value_changed),
                                   config);
  gtk_range_set_value (range, (gdouble) size);
  g_signal_handlers_unblock_by_func (range,
                                     G_CALLBACK (prefs_icon_size_value_changed),
                                     config);
}

/* --- preferences-dialog.c --- */
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

#include "config.h"

#include <string.h>

#include <cairo-gobject.h>
#include <gegl.h>
#include <gtk/gtk.h>

#include "libgimpmath/gimpmath.h"
#include "libgimpbase/gimpbase.h"
#include "libgimpconfig/gimpconfig.h"
#include "libgimpwidgets/gimpwidgets.h"

#include "dialogs-types.h"

#include "ammoos-version.h"

#include "config/gimprc.h"

#include "core/ammoos.h"
#include "core/gimptemplate.h"
#include "core/ammoos-utils.h"

#include "display/gimpmodifiersmanager.h"

#include "plug-in/gimppluginmanager.h"

#include "widgets/gimpaction-history.h"
#include "widgets/gimpcolorpanel.h"
#include "widgets/gimpcontainercombobox.h"
#include "widgets/gimpcontainerview.h"
#include "widgets/gimpcontrollerlist.h"
#include "widgets/gimpcontrollers.h"
#include "widgets/gimpdevices.h"
#include "widgets/gimpdialogfactory.h"
#include "widgets/gimpgrideditor.h"
#include "widgets/gimphelp.h"
#include "widgets/gimphelp-ids.h"
#include "widgets/gimplanguagecombobox.h"
#include "widgets/gimpmessagebox.h"
#include "widgets/gimpmessagedialog.h"
#include "widgets/gimppluginview.h"
#include "widgets/gimpprefsbox.h"
#include "widgets/gimppropwidgets.h"
#include "widgets/gimpmodifierseditor.h"
#include "widgets/gimpstrokeeditor.h"
#include "widgets/gimptemplateeditor.h"
#include "widgets/gimptooleditor.h"
#include "widgets/gimpwidgets-utils.h"

#include "menus/menus.h"

#include "tools/ammoos-tools.h"

#include "gui/icon-themes.h"
#include "gui/session.h"
#include "gui/modifiers.h"
#include "gui/themes.h"

#include "preferences-dialog.h"
#include "preferences-dialog-utils.h"
#include "resolution-calibrate-dialog.h"

#include "ammoos-intl.h"


#define RESPONSE_RESET 1


/*  preferences local functions  */

static GtkWidget * prefs_dialog_new                (Gimp       *ammoos,
                                                    GimpConfig *config);
static void        prefs_response                  (GtkWidget  *widget,
                                                    gint        response_id,
                                                    GtkWidget  *dialog);
static void        prefs_box_style_updated         (GtkWidget  *widget);

static void   prefs_color_management_reset         (GtkWidget    *widget,
                                                    GObject      *config);
static void   prefs_dialog_defaults_reset          (GtkWidget    *widget,
                                                    GObject      *config);
static void   prefs_folders_reset                  (GtkWidget    *widget,
                                                    GObject      *config);
static void   prefs_path_reset                     (GtkWidget    *widget,
                                                    GObject      *config);

static void   prefs_import_raw_procedure_callback  (GtkWidget    *widget,
                                                    GObject      *config);
static void   prefs_resolution_source_callback     (GtkWidget    *widget,
                                                    GObject      *config);
static void   prefs_resolution_calibrate_callback  (GtkWidget    *widget,
                                                    GtkWidget    *entry);
static void   prefs_input_devices_dialog           (GtkWidget    *widget,
                                                    Gimp         *ammoos);
static void   prefs_keyboard_shortcuts_dialog      (GtkWidget    *widget,
                                                    Gimp         *ammoos);
static void   prefs_menus_save_callback            (GtkWidget    *widget,
                                                    Gimp         *ammoos);
static void   prefs_menus_clear_callback           (GtkWidget    *widget,
                                                    Gimp         *ammoos);
static void   prefs_menus_remove_callback          (GtkWidget    *widget,
                                                    Gimp         *ammoos);
static void   prefs_session_save_callback          (GtkWidget    *widget,
                                                    Gimp         *ammoos);
static void   prefs_session_clear_callback         (GtkWidget    *widget,
                                                    Gimp         *ammoos);
static void   prefs_devices_save_callback          (GtkWidget    *widget,
                                                    Gimp         *ammoos);
static void   prefs_devices_clear_callback         (GtkWidget    *widget,
                                                    Gimp         *ammoos);
static void   prefs_modifiers_clear_callback       (GtkWidget    *widget,
                                                    GimpModifiersEditor *editor);
static void   prefs_search_clear_callback          (GtkWidget    *widget,
                                                    Gimp         *ammoos);
static void   prefs_tool_options_save_callback     (GtkWidget    *widget,
                                                    Gimp         *ammoos);
static void   prefs_tool_options_clear_callback    (GtkWidget    *widget,
                                                    Gimp         *ammoos);
static void   prefs_help_language_change_callback  (GtkComboBox  *combo,
                                                    Gimp         *ammoos);
static void   prefs_help_language_change_callback2 (GtkComboBox  *combo,
                                                    GtkContainer *box);
static void   prefs_check_style_callback           (GObject      *config,
                                                    GParamSpec   *pspec,
                                                    GtkWidget    *widget);
static void   prefs_theme_reset_callback           (GObject      *config,
                                                    GParamSpec   *pspec,
                                                    GtkWidget    *widget);
static void   prefs_icon_theme_reset_callback      (GObject      *config,
                                                    GParamSpec   *pspec,
                                                    GtkWidget    *widget);


/*  private variables  */

static GtkWidget *prefs_dialog = NULL;
static GtkWidget *tool_editor  = NULL;


/*  public function  */

GtkWidget *
preferences_dialog_create (Gimp *ammoos)
{
  GimpConfig *config;
  GimpConfig *config_copy;
  GimpConfig *config_orig;

  g_return_val_if_fail (GIMP_IS_GIMP (ammoos), NULL);

  if (prefs_dialog)
    return prefs_dialog;

  /*  turn off autosaving while the prefs dialog is open  */
  gimp_rc_set_autosave (GIMP_RC (ammoos->edit_config), FALSE);

  config       = GIMP_CONFIG (ammoos->edit_config);
  config_copy  = gimp_config_duplicate (config);
  config_orig  = gimp_config_duplicate (config);

  g_signal_connect_object (config, "notify",
                           G_CALLBACK (prefs_config_notify),
                           config_copy, 0);
  g_signal_connect_object (config_copy, "notify",
                           G_CALLBACK (prefs_config_copy_notify),
                           config, 0);

  g_set_weak_pointer (&prefs_dialog, prefs_dialog_new (ammoos, config_copy));

  g_object_set_data (G_OBJECT (prefs_dialog), "ammoos", ammoos);

  g_object_set_data_full (G_OBJECT (prefs_dialog), "config-copy", config_copy,
                          (GDestroyNotify) g_object_unref);
  g_object_set_data_full (G_OBJECT (prefs_dialog), "config-orig", config_orig,
                          (GDestroyNotify) g_object_unref);

  return prefs_dialog;
}


/*  private functions  */

static void
prefs_response (GtkWidget *widget,
                gint       response_id,
                GtkWidget *dialog)
{
  Gimp   *ammoos = g_object_get_data (G_OBJECT (dialog), "ammoos");
  gulong  reset_handler;

  switch (response_id)
    {
    case RESPONSE_RESET:
      {
        GtkWidget *confirm;

        confirm = gimp_message_dialog_new (_("Reset All Preferences"),
                                           GIMP_ICON_DIALOG_QUESTION,
                                           dialog,
                                           GTK_DIALOG_MODAL |
                                           GTK_DIALOG_DESTROY_WITH_PARENT,
                                           gimp_standard_help_func, NULL,

                                           _("_Cancel"), GTK_RESPONSE_CANCEL,
                                           _("_Reset"),  GTK_RESPONSE_OK,

                                           NULL);

        gimp_dialog_set_alternative_button_order (GTK_DIALOG (confirm),
                                                  GTK_RESPONSE_OK,
                                                  GTK_RESPONSE_CANCEL,
                                                  -1);

        gimp_message_box_set_primary_text (GIMP_MESSAGE_DIALOG (confirm)->box,
                                           _("Do you really want to reset all "
                                             "preferences to default values?"));

        if (gimp_dialog_run (GIMP_DIALOG (confirm)) == GTK_RESPONSE_OK)
          {
            GimpConfig *config_copy;

            config_copy = g_object_get_data (G_OBJECT (dialog), "config-copy");

            gimp_config_reset (config_copy);
            gimp_rc_load_system (GIMP_RC (config_copy));
          }

        gtk_widget_destroy (confirm);

        return;
      }
      break;

    case GTK_RESPONSE_OK:
      {
        GObject *config_copy;
        GList   *restart_diff;
        GList   *confirm_diff;
        GList   *list;

        config_copy = g_object_get_data (G_OBJECT (dialog), "config-copy");

        /*  destroy config_orig  */
        g_object_set_data (G_OBJECT (dialog), "config-orig", NULL);

        gtk_widget_set_sensitive (GTK_WIDGET (dialog), FALSE);

        confirm_diff = gimp_config_diff (G_OBJECT (ammoos->edit_config),
                                         config_copy,
                                         GIMP_CONFIG_PARAM_CONFIRM);

        g_object_freeze_notify (G_OBJECT (ammoos->edit_config));

        for (list = confirm_diff; list; list = g_list_next (list))
          {
            GParamSpec *param_spec = list->data;
            GValue      value      = G_VALUE_INIT;

            g_value_init (&value, param_spec->value_type);

            g_object_get_property (config_copy,
                                   param_spec->name, &value);
            g_object_set_property (G_OBJECT (ammoos->edit_config),
                                   param_spec->name, &value);

            g_value_unset (&value);
          }

        g_object_thaw_notify (G_OBJECT (ammoos->edit_config));

        g_list_free (confirm_diff);

        gimp_rc_save (GIMP_RC (ammoos->edit_config));

        /*  spit out a solely informational warning about changed values
         *  which need restart
         */
        restart_diff = gimp_config_diff (G_OBJECT (ammoos->edit_config),
                                         G_OBJECT (ammoos->config),
                                         GIMP_CONFIG_PARAM_RESTART);

        if (restart_diff)
          {
            GString *string;

            string = g_string_new (_("You will have to restart AmmoOS Image for "
                                     "the following changes to take effect:"));
            g_string_append (string, "\n\n");

            for (list = restart_diff; list; list = g_list_next (list))
              {
                GParamSpec *param_spec = list->data;

                /* The first 3 bytes are the bullet unicode character
                 * for doing a list (U+2022).
                 */
                g_string_append_printf (string, "\xe2\x80\xa2 %s\n", g_param_spec_get_nick (param_spec));
              }

            prefs_message (prefs_dialog, GTK_MESSAGE_INFO, FALSE, string->str);

            g_string_free (string, TRUE);
          }

        g_list_free (restart_diff);
      }
      break;

    default:
      {
        GObject *config_orig;
        GList   *diff;
        GList   *list;

        config_orig = g_object_get_data (G_OBJECT (dialog), "config-orig");

        /*  destroy config_copy  */
        g_object_set_data (G_OBJECT (dialog), "config-copy", NULL);

        gtk_widget_set_sensitive (GTK_WIDGET (dialog), FALSE);

        diff = gimp_config_diff (G_OBJECT (ammoos->edit_config),
                                 config_orig,
                                 GIMP_CONFIG_PARAM_SERIALIZE);

        g_object_freeze_notify (G_OBJECT (ammoos->edit_config));

        for (list = diff; list; list = g_list_next (list))
          {
            GParamSpec *param_spec = list->data;
            GValue      value      = G_VALUE_INIT;

            g_value_init (&value, param_spec->value_type);

            g_object_get_property (config_orig,
                                   param_spec->name, &value);
            g_object_set_property (G_OBJECT (ammoos->edit_config),
                                   param_spec->name, &value);

            g_value_unset (&value);
          }

        gimp_tool_editor_revert_changes (GIMP_TOOL_EDITOR (tool_editor));

        g_object_thaw_notify (G_OBJECT (ammoos->edit_config));

        g_list_free (diff);
      }

      tool_editor = NULL;
    }

  /* Disconnect the signals used to update the selection of the
   * theme and icon theme list boxes, since they're not directly
   * connected to their properties like the other widgets */
  reset_handler = GPOINTER_TO_UINT (g_object_get_data (G_OBJECT (dialog),
                                    "ammoos-theme-reset-handler"));
  g_signal_handler_disconnect (ammoos->config, reset_handler);

  reset_handler = GPOINTER_TO_UINT (g_object_get_data (G_OBJECT (dialog),
                                    "ammoos-icon-theme-reset-handler"));
  g_signal_handler_disconnect (ammoos->config, reset_handler);

  /*  enable autosaving again  */
  gimp_rc_set_autosave (GIMP_RC (ammoos->edit_config), TRUE);

  gtk_widget_destroy (dialog);
}

static void
prefs_box_style_updated (GtkWidget *widget)
{
  GimpPrefsBox *box = GIMP_PREFS_BOX (widget);

  GTK_WIDGET_GET_CLASS (box)->style_updated (GTK_WIDGET (box));
}

static void
prefs_color_management_reset (GtkWidget *widget,
                              GObject   *config)
{
  GimpCoreConfig *core_config = GIMP_CORE_CONFIG (config);

  gimp_config_reset (GIMP_CONFIG (core_config->color_management));
  gimp_config_reset_property (config, "color-profile-policy");
}

static void
prefs_dialog_defaults_reset (GtkWidget *widget,
                             GObject   *config)
{
  GParamSpec **pspecs;
  guint        n_pspecs;
  guint        i;

  pspecs = g_object_class_list_properties (G_OBJECT_GET_CLASS (config),
                                           &n_pspecs);

  g_object_freeze_notify (config);

  for (i = 0; i < n_pspecs; i++)
    {
      GParamSpec *pspec = pspecs[i];

      if (pspec->owner_type == GIMP_TYPE_DIALOG_CONFIG)
        gimp_config_reset_property (config, pspec->name);
    }

  gimp_config_reset_property (config, "filter-tool-max-recent");
  gimp_config_reset_property (config, "filter-tool-use-last-settings");

  g_object_thaw_notify (config);

  g_free (pspecs);
}

static void
prefs_folders_reset (GtkWidget *widget,
                     GObject   *config)
{
  gimp_config_reset_property (config, "temp-path");
  gimp_config_reset_property (config, "swap-path");
}

static void
prefs_path_reset (GtkWidget *widget,
                  GObject   *config)
{
  const gchar *path_property;
  const gchar *writable_property;

  path_property     = g_object_get_data (G_OBJECT (widget), "path");
  writable_property = g_object_get_data (G_OBJECT (widget), "path-writable");

  gimp_config_reset_property (config, path_property);

  if (writable_property)
    gimp_config_reset_property (config, writable_property);
}

static void
prefs_template_select_callback (GimpContainerView *view,
                                GimpTemplate      *edit_template)
{
  GimpViewable *item = gimp_container_view_get_1_selected (view);

  if (item)
    {
      /*  make sure the resolution values are copied first (see bug #546924)  */
      gimp_config_sync (G_OBJECT (item), G_OBJECT (edit_template),
                        GIMP_TEMPLATE_PARAM_COPY_FIRST);
      gimp_config_sync (G_OBJECT (item), G_OBJECT (edit_template),
                        0);
    }
}

static void
prefs_import_raw_procedure_callback (GtkWidget *widget,
                                     GObject   *config)
{
  gchar *raw_plug_in;

  raw_plug_in = gimp_plug_in_view_get_plug_in (GIMP_PLUG_IN_VIEW (widget));

  g_object_set (config,
                "import-raw-plug-in", raw_plug_in,
                NULL);

  g_free (raw_plug_in);
}

static void
prefs_resolution_source_callback (GtkWidget *widget,
                                  GObject   *config)
{
  gdouble  xres;
  gdouble  yres;
  gboolean from_gdk;

  from_gdk = gtk_toggle_button_get_active (GTK_TOGGLE_BUTTON (widget));

  if (from_gdk)
    {
      gimp_get_monitor_resolution (gimp_widget_get_monitor (widget),
                                   &xres, &yres);
    }
  else
    {
      GimpSizeEntry *entry = g_object_get_data (G_OBJECT (widget),
                                                "monitor_resolution_sizeentry");

      g_return_if_fail (GIMP_IS_SIZE_ENTRY (entry));

      xres = gimp_size_entry_get_refval (entry, 0);
      yres = gimp_size_entry_get_refval (entry, 1);
    }

  g_object_set (config,
                "monitor-xresolution",                      xres,
                "monitor-yresolution",                      yres,
                "monitor-resolution-from-windowing-system", from_gdk,
                NULL);
}

static void
prefs_resolution_calibrate_callback (GtkWidget *widget,
                                     GtkWidget *entry)
{
  GtkWidget   *dialog;
  GtkWidget   *prefs_box;
  const gchar *icon_name;

  dialog = gtk_widget_get_toplevel (entry);

  prefs_box = g_object_get_data (G_OBJECT (dialog), "prefs-box");
  icon_name = gimp_prefs_box_get_current_icon_name (GIMP_PREFS_BOX (prefs_box));

  resolution_calibrate_dialog (entry, icon_name);
}

static void
prefs_input_devices_dialog (GtkWidget *widget,
                            Gimp      *ammoos)
{
  gimp_dialog_factory_dialog_raise (gimp_dialog_factory_get_singleton (),
                                    gimp_widget_get_monitor (widget),
                                    widget,
                                    "ammoos-input-devices-dialog", 0);
}

static void
prefs_keyboard_shortcuts_dialog (GtkWidget *widget,
                                 Gimp      *ammoos)
{
  gimp_dialog_factory_dialog_raise (gimp_dialog_factory_get_singleton (),
                                    gimp_widget_get_monitor (widget),
                                    widget,
                                    "ammoos-keyboard-shortcuts-dialog", 0);
}

static void
prefs_menus_save_callback (GtkWidget *widget,
                           Gimp      *ammoos)
{
  GtkWidget *clear_button;

  menus_save (ammoos, TRUE);

  clear_button = g_object_get_data (G_OBJECT (widget), "clear-button");

  if (clear_button)
    gtk_widget_set_sensitive (clear_button, TRUE);
}

static void
prefs_menus_clear_callback (GtkWidget *widget,
                            Gimp      *ammoos)
{
  GError *error = NULL;

  if (! menus_clear (ammoos, &error))
    {
      prefs_message (prefs_dialog, GTK_MESSAGE_ERROR, TRUE, error->message);
      g_clear_error (&error);
    }
  else
    {
      gtk_widget_set_sensitive (widget, FALSE);

      prefs_message (prefs_dialog, GTK_MESSAGE_INFO, TRUE,
                     _("Your keyboard shortcuts will be reset to "
                       "default values the next time you start AmmoOS Image."));
    }
}

static void
prefs_menus_remove_callback (GtkWidget *widget,
                             Gimp      *ammoos)
{
  GtkWidget *dialog;

  dialog = gimp_message_dialog_new (_("Remove all Keyboard Shortcuts"),
                                    GIMP_ICON_DIALOG_QUESTION,
                                    gtk_widget_get_toplevel (widget),
                                    GTK_DIALOG_MODAL |
                                    GTK_DIALOG_DESTROY_WITH_PARENT,
                                    gimp_standard_help_func, NULL,

                                    _("_Cancel"), GTK_RESPONSE_CANCEL,
                                    _("Cl_ear"),  GTK_RESPONSE_OK,

                                    NULL);

  gimp_dialog_set_alternative_button_order (GTK_DIALOG (dialog),
                                            GTK_RESPONSE_OK,
                                            GTK_RESPONSE_CANCEL,
                                            -1);

  g_signal_connect_object (gtk_widget_get_toplevel (widget), "unmap",
                           G_CALLBACK (gtk_widget_destroy),
                           dialog, G_CONNECT_SWAPPED);

  gimp_message_box_set_primary_text (GIMP_MESSAGE_DIALOG (dialog)->box,
                                     _("Do you really want to remove all "
                                       "keyboard shortcuts from all menus?"));

  if (gimp_dialog_run (GIMP_DIALOG (dialog)) == GTK_RESPONSE_OK)
    {
      menus_remove (ammoos);
    }

  gtk_widget_destroy (dialog);
}

static void
prefs_session_save_callback (GtkWidget *widget,
                             Gimp      *ammoos)
{
  GtkWidget *clear_button;

  session_save (ammoos, TRUE);

  clear_button = g_object_get_data (G_OBJECT (widget), "clear-button");

  if (clear_button)
    gtk_widget_set_sensitive (clear_button, TRUE);
}

static void
prefs_session_clear_callback (GtkWidget *widget,
                              Gimp      *ammoos)
{
  GError *error = NULL;

  if (! session_clear (ammoos, &error))
    {
      prefs_message (prefs_dialog, GTK_MESSAGE_ERROR, TRUE, error->message);
      g_clear_error (&error);
    }
  else
    {
      gtk_widget_set_sensitive (widget, FALSE);

      prefs_message (prefs_dialog, GTK_MESSAGE_INFO, TRUE,
                     _("Your window setup will be reset to "
                       "default values the next time you start AmmoOS Image."));
    }
}

static void
prefs_devices_save_callback (GtkWidget *widget,
                             Gimp      *ammoos)
{
  GtkWidget *clear_button;

  gimp_devices_save (ammoos, TRUE);

  clear_button = g_object_get_data (G_OBJECT (widget), "clear-button");

  if (clear_button)
    gtk_widget_set_sensitive (clear_button, TRUE);
}

static void
prefs_devices_clear_callback (GtkWidget *widget,
                              Gimp      *ammoos)
{
  GError *error = NULL;

  if (! gimp_devices_clear (ammoos, &error))
    {
      prefs_message (prefs_dialog, GTK_MESSAGE_ERROR, TRUE, error->message);
      g_clear_error (&error);
    }
  else
    {
      gtk_widget_set_sensitive (widget, FALSE);

      prefs_message (prefs_dialog, GTK_MESSAGE_INFO, TRUE,
                     _("Your input device settings will be reset to "
                       "default values the next time you start AmmoOS Image."));
    }
}

static void
prefs_modifiers_clear_callback (GtkWidget           *widget,
                                GimpModifiersEditor *editor)
{
  gimp_modifiers_editor_clear (editor);
}

#ifdef G_OS_WIN32

static gboolean
prefs_devices_api_sensitivity_func (gint      value,
                                    gpointer  data)
{
  static gboolean have_wintab      = TRUE;
  static gboolean have_windows_ink = TRUE;
  static gboolean inited           = FALSE;

  if (!inited)
    {
      have_wintab      = gimp_win32_have_wintab ();
      have_windows_ink = gimp_win32_have_windows_ink ();

      inited = TRUE;
    }

  switch (value)
    {
    case GIMP_WIN32_POINTER_INPUT_API_WINTAB:
      return have_wintab;
    case GIMP_WIN32_POINTER_INPUT_API_WINDOWS_INK:
      return have_windows_ink;
    default:
      return TRUE;
    }
}

#endif

static void
prefs_search_clear_callback (GtkWidget *widget,
                             Gimp      *ammoos)
{
  gimp_action_history_clear (ammoos);
}

static void
prefs_tool_options_save_callback (GtkWidget *widget,
                                  Gimp      *ammoos)
{
  GtkWidget *clear_button;

  gimp_tools_save (ammoos, TRUE, TRUE);

  clear_button = g_object_get_data (G_OBJECT (widget), "clear-button");

  if (clear_button)
    gtk_widget_set_sensitive (clear_button, TRUE);
}

static void
prefs_tool_options_clear_callback (GtkWidget *widget,
                                   Gimp      *ammoos)
{
  GError *error = NULL;

  if (! gimp_tools_clear (ammoos, &error))
    {
      prefs_message (prefs_dialog, GTK_MESSAGE_ERROR, TRUE, error->message);
      g_clear_error (&error);
    }
  else
    {
      gtk_widget_set_sensitive (widget, FALSE);

      prefs_message (prefs_dialog, GTK_MESSAGE_INFO, TRUE,
                     _("Your tool options will be reset to "
                       "default values the next time you start AmmoOS Image."));
    }
}

static void
prefs_help_language_change_callback (GtkComboBox *combo,
                                     Gimp        *ammoos)
{
  gchar *help_locales = NULL;
  gchar *code;

  code = gimp_language_combo_box_get_code (GIMP_LANGUAGE_COMBO_BOX (combo));
  if (code && g_strcmp0 ("", code) != 0)
    {
      help_locales = g_strdup_printf ("%s:", code);
    }
  g_object_set (ammoos->config,
                "help-locales", help_locales? help_locales : "",
                NULL);
  g_free (code);
  if (help_locales)
    g_free (help_locales);
}

static void
prefs_help_language_change_callback2 (GtkComboBox  *combo,
                                      GtkContainer *box)
{
  Gimp        *ammoos;
  GtkLabel    *label = NULL;
  GtkImage    *icon  = NULL;
  GList       *children;
  GList       *iter;
  const gchar *text;
  const gchar *icon_name;

  ammoos = g_object_get_data (G_OBJECT (box), "ammoos");
  children = gtk_container_get_children (box);
  for (iter = children; iter; iter = iter->next)
    {
      if (GTK_IS_LABEL (iter->data))
        {
          label = iter->data;
        }
      else if (GTK_IS_IMAGE (iter->data))
        {
          icon = iter->data;
        }
    }
  if (gimp_help_user_manual_is_installed (ammoos))
    {
      text = _("There's a local installation of the user manual.");
      icon_name = GIMP_ICON_DIALOG_INFORMATION;
    }
  else
    {
      text = _("The user manual is not installed locally.");
      icon_name = GIMP_ICON_DIALOG_WARNING;
    }
  if (label)
    {
      gtk_label_set_text (label, text);
    }
  if (icon)
    {
      gtk_image_set_from_icon_name (icon, icon_name,
                                    GTK_ICON_SIZE_BUTTON);
    }

  g_list_free (children);
}

static void
prefs_check_style_callback (GObject    *config,
                            GParamSpec *pspec,
                            GtkWidget  *widget)
{
  GimpDisplayConfig *display_config = GIMP_DISPLAY_CONFIG (config);

  gtk_widget_set_sensitive (widget,
                            display_config->transparency_type == GIMP_CHECK_TYPE_CUSTOM_CHECKS);
}

static void
prefs_format_string_select_callback (GtkListBox    *listbox,
                                     GtkListBoxRow *row,
                                     gpointer       user_data)
{
  GtkEntry *entry = GTK_ENTRY (user_data);

  gtk_entry_set_text (entry, g_object_get_data (G_OBJECT (row), "format"));
}

static void
prefs_theme_select_callback (GtkListBox    *listbox,
                             GtkListBoxRow *row,
                             Gimp          *ammoos)
{
  const char *theme;

  g_return_if_fail (row != NULL);

  theme = g_object_get_data (G_OBJECT (row), "theme");

  g_signal_handlers_block_by_func (ammoos->config,
                                   G_CALLBACK (prefs_theme_reset_callback),
                                   listbox);
  g_object_set (ammoos->config, "theme", theme, NULL);
  g_signal_handlers_unblock_by_func (ammoos->config,
                                     G_CALLBACK (prefs_theme_reset_callback),
                                     listbox);
}

static void
prefs_theme_reload_callback (GtkWidget *button,
                             Gimp      *ammoos)
{
  g_object_notify (G_OBJECT (ammoos->config), "theme");
}

static void
prefs_theme_reset_callback (GObject    *config,
                            GParamSpec *pspec,
                            GtkWidget  *widget)
{
  const gchar    *theme;
  GtkListBoxRow  *row;
  gint            i = 0;

  g_object_get (config, "theme", &theme, NULL);

  row = gtk_list_box_get_row_at_index (GTK_LIST_BOX (widget), i);

  while (row != NULL)
    {
      const gchar *row_theme = g_object_get_data (G_OBJECT (row), "theme");

      if (! strcmp (theme, row_theme))
        {
          gtk_list_box_select_row (GTK_LIST_BOX (widget), row);
          break;
        }

      i++;
      row = gtk_list_box_get_row_at_index (GTK_LIST_BOX (widget), i);
    }
}

static void
prefs_icon_theme_select_callback (GtkListBox    *listbox,
                                  GtkListBoxRow *row,
                                  Gimp          *ammoos)
{
  const char *icon_theme;

  g_return_if_fail (row != NULL);

  icon_theme = g_object_get_data (G_OBJECT (row), "icon-theme");

  g_signal_handlers_block_by_func (ammoos->config,
                                   G_CALLBACK (prefs_icon_theme_reset_callback),
                                   listbox);
  g_object_set (ammoos->config, "icon-theme", icon_theme, NULL);
  g_signal_handlers_unblock_by_func (ammoos->config,
                                     G_CALLBACK (prefs_icon_theme_reset_callback),
                                     listbox);
}

static void
prefs_icon_theme_reset_callback (GObject    *config,
                                 GParamSpec *pspec,
                                 GtkWidget  *widget)
{
  const gchar    *icon_theme;
  GtkListBoxRow  *row;
  gint            i = 0;

  g_object_get (config, "icon-theme", &icon_theme, NULL);

  row = gtk_list_box_get_row_at_index (GTK_LIST_BOX (widget), i);

  while (row != NULL)
    {
      const gchar *row_icon_theme =
        g_object_get_data (G_OBJECT (row), "icon-theme");

      if (! strcmp (icon_theme, row_icon_theme))
        {
          gtk_list_box_select_row (GTK_LIST_BOX (widget), row);
          break;
        }

      i++;
      row = gtk_list_box_get_row_at_index (GTK_LIST_BOX (widget), i);
    }
}

static void
prefs_canvas_padding_color_changed (GtkWidget *button,
                                    GtkWidget *combo)
{
  gimp_int_combo_box_set_active (GIMP_INT_COMBO_BOX (combo),
                                 GIMP_CANVAS_PADDING_MODE_CUSTOM);
}

static void
prefs_display_options_frame_add (Gimp         *ammoos,
                                 GObject      *object,
                                 const gchar  *label,
                                 GtkContainer *parent)
{
  GtkWidget *vbox;
  GtkWidget *hbox;
  GtkWidget *checks_vbox;
  GtkWidget *grid;
  GtkWidget *combo;
  GtkWidget *button;

  vbox = prefs_frame_new (label, parent, FALSE);

  hbox = gtk_box_new (GTK_ORIENTATION_HORIZONTAL, 6);
  gtk_box_pack_start (GTK_BOX (vbox), hbox, FALSE, FALSE, 0);
  gtk_widget_set_visible (hbox, TRUE);

  checks_vbox = gtk_box_new (GTK_ORIENTATION_VERTICAL, 2);
  gtk_box_pack_start (GTK_BOX (hbox), checks_vbox, TRUE, TRUE, 0);
  gtk_widget_set_visible (checks_vbox, TRUE);

  prefs_check_button_add (object, "show-selection",
                          _("Show s_election"),
                          GTK_BOX (checks_vbox));
  prefs_check_button_add (object, "show-layer-boundary",
                          _("Show _layer boundary"),
                          GTK_BOX (checks_vbox));
  prefs_check_button_add (object, "show-canvas-boundary",
                          _("Show can_vas boundary"),
                          GTK_BOX (checks_vbox));
  prefs_check_button_add (object, "show-guides",
                          _("Show _guides"),
                          GTK_BOX (checks_vbox));
  prefs_check_button_add (object, "show-grid",
                          _("Show gri_d"),
                          GTK_BOX (checks_vbox));
  prefs_check_button_add (object, "show-sample-points",
                          _("Show _sample points"),
                          GTK_BOX (checks_vbox));

  checks_vbox = gtk_box_new (GTK_ORIENTATION_VERTICAL, 2);
  gtk_box_pack_start (GTK_BOX (hbox), checks_vbox, TRUE, TRUE, 0);
  gtk_widget_set_visible (checks_vbox, TRUE);

#ifndef GDK_WINDOWING_QUARTZ
  prefs_check_button_add (object, "show-menubar",
                          _("Show _menubar"),
                          GTK_BOX (checks_vbox));
#endif /* !GDK_WINDOWING_QUARTZ */
  prefs_check_button_add (object, "show-rulers",
                          _("Show _rulers"),
                          GTK_BOX (checks_vbox));
  prefs_check_button_add (object, "show-scrollbars",
                          _("Show scroll_bars"),
                          GTK_BOX (checks_vbox));
  prefs_check_button_add (object, "show-statusbar",
                          _("Show s_tatusbar"),
                          GTK_BOX (checks_vbox));

  grid = prefs_grid_new (GTK_CONTAINER (vbox));

  combo = prefs_enum_combo_box_add (object, "padding-mode", 0, 0,
                                    _("Canvas _padding mode:"),
                                    GTK_GRID (grid), 0,
                                    NULL);

  button = prefs_color_button_add (object, "padding-color",
                                   _("Custom p_adding color:"),
                                   _("Select Custom Canvas Padding Color"),
                                   GTK_GRID (grid), 1, NULL,
                                   gimp_get_user_context (ammoos));

  g_signal_connect (button, "color-changed",
                    G_CALLBACK (prefs_canvas_padding_color_changed),
                    combo);

  prefs_check_button_add (object, "padding-in-show-all",
                          _("_Keep canvas padding in \"Show All\" mode"),
                          GTK_BOX (vbox));
}

static void
prefs_behavior_options_frame_add (Gimp         *ammoos,
                                  GObject      *object,
                                  const gchar  *label,
                                  GtkContainer *parent)
{
  GtkWidget *vbox;
  GtkWidget *hbox;
  GtkWidget *checks_vbox;

  vbox = prefs_frame_new (label, parent, FALSE);

  hbox = gtk_box_new (GTK_ORIENTATION_HORIZONTAL, 6);
  gtk_box_pack_start (GTK_BOX (vbox), hbox, FALSE, FALSE, 0);
  gtk_widget_set_visible (hbox, TRUE);

  checks_vbox = gtk_box_new (GTK_ORIENTATION_VERTICAL, 2);
  gtk_box_pack_start (GTK_BOX (hbox), checks_vbox, TRUE, TRUE, 0);
  gtk_widget_set_visible (checks_vbox, TRUE);

  prefs_check_button_add (object, "snap-to-guides",
                          _("Snap to _Guides"),
                          GTK_BOX (checks_vbox));
  prefs_check_button_add (object, "snap-to-grid",
                          _("S_nap to Grid"),
                          GTK_BOX (checks_vbox));
  prefs_check_button_add (object, "snap-to-canvas",
                          _("Snap to Canvas _Edges"),
                          GTK_BOX (checks_vbox));

  checks_vbox = gtk_box_new (GTK_ORIENTATION_VERTICAL, 2);
  gtk_box_pack_start (GTK_BOX (hbox), checks_vbox, TRUE, TRUE, 0);
  gtk_widget_set_visible (checks_vbox, TRUE);

  prefs_check_button_add (object, "snap-to-path",
                          _("Snap to _Active Path"),
                          GTK_BOX (checks_vbox));
  prefs_check_button_add (object, "snap-to-bbox",
                          _("Snap to _Bounding Box"),
                          GTK_BOX (checks_vbox));
  prefs_check_button_add (object, "snap-to-equidistance",
                          _("Snap to _Equidistance"),
                          GTK_BOX (checks_vbox));
}

static void
prefs_help_func (const gchar *help_id,
                 gpointer     help_data)
{
  GtkWidget *prefs_box;

  prefs_box = g_object_get_data (G_OBJECT (help_data), "prefs-box");

  help_id = gimp_prefs_box_get_current_help_id (GIMP_PREFS_BOX (prefs_box));

  gimp_standard_help_func (help_id, NULL);
}

static GtkWidget *
prefs_dialog_new (Gimp       *ammoos,
                  GimpConfig *config)
{
  GtkWidget         *dialog;
  GtkTreeIter        top_iter;
  GtkTreeIter        child_iter;

  GtkWidget         *prefs_box;
  GtkSizeGroup      *size_group = NULL;
  GtkWidget         *vbox;
  GtkWidget         *hbox;
  GtkWidget         *vbox2;
  GtkWidget         *vbox3;
  GtkWidget         *button;
  GtkWidget         *button2;
  GtkWidget         *grid;
  GtkWidget         *label;
  GtkWidget         *entry;
  GtkWidget         *calibrate_button;
  GSList            *group;
  GtkWidget         *separator;
  GtkWidget         *editor;
  gint               i;

  GObject           *object;
  GimpCoreConfig    *core_config;
  GimpDisplayConfig *display_config;
  GList             *manuals;

  g_return_val_if_fail (GIMP_IS_GIMP (ammoos), NULL);
  g_return_val_if_fail (GIMP_IS_CONFIG (config), NULL);

  object         = G_OBJECT (config);
  core_config    = GIMP_CORE_CONFIG (config);
  display_config = GIMP_DISPLAY_CONFIG (config);

  dialog = gimp_dialog_new (_("Preferences"), "ammoos-preferences",
                            NULL, 0,
                            prefs_help_func,
                            GIMP_HELP_PREFS_DIALOG,

                            _("_Reset"),  RESPONSE_RESET,
                            _("_Cancel"), GTK_RESPONSE_CANCEL,
                            _("_OK"),     GTK_RESPONSE_OK,

                            NULL);

  gimp_dialog_set_alternative_button_order (GTK_DIALOG (dialog),
                                            RESPONSE_RESET,
                                            GTK_RESPONSE_OK,
                                            GTK_RESPONSE_CANCEL,
                                            -1);

  g_signal_connect (dialog, "response",
                    G_CALLBACK (prefs_response),
                    dialog);

  /* The prefs box */
  prefs_box = gimp_prefs_box_new ();
  gtk_container_set_border_width (GTK_CONTAINER (prefs_box), 12);
  gtk_box_pack_start (GTK_BOX (gtk_dialog_get_content_area (GTK_DIALOG (dialog))),
                      prefs_box, TRUE, TRUE, 0);
  gtk_widget_set_visible (prefs_box, TRUE);

  g_object_set_data (G_OBJECT (dialog), "prefs-box", prefs_box);

  /* Notify the prefs box to update its tree icon sizes
   * based on user preferences */
  g_signal_connect_object (config,
                           "notify::override-theme-icon-size",
                           G_CALLBACK (prefs_box_style_updated),
                           prefs_box, G_CONNECT_AFTER | G_CONNECT_SWAPPED);
  g_signal_connect_object (config,
                           "notify::custom-icon-size",
                           G_CALLBACK (prefs_box_style_updated),
                           prefs_box, G_CONNECT_AFTER | G_CONNECT_SWAPPED);

  /**********************/
  /*  System Resources  */
  /**********************/
  vbox = gimp_prefs_box_add_page (GIMP_PREFS_BOX (prefs_box),
                                  "ammoos-prefs-system-resources",
                                  _("System Resources"),
                                  _("System Resources"),
                                  GIMP_HELP_PREFS_SYSTEM_RESOURCES,
                                  NULL,
                                  &top_iter);
  gimp_prefs_box_set_page_scrollable (GIMP_PREFS_BOX (prefs_box), vbox, TRUE);

  size_group = gtk_size_group_new (GTK_SIZE_GROUP_HORIZONTAL);

  vbox2 = prefs_frame_new (_("Resource Consumption"),
                           GTK_CONTAINER (vbox), FALSE);

  grid = prefs_grid_new (GTK_CONTAINER (vbox2));

  prefs_spin_button_add (object, "undo-levels", 1.0, 5.0, 0,
                         _("Minimal number of _undo levels:"),
                         GTK_GRID (grid), 0, size_group);
  prefs_memsize_entry_add (object, "undo-size",
                           _("Maximum undo _memory:"),
                           GTK_GRID (grid), 1, size_group);
  prefs_memsize_entry_add (object, "tile-cache-size",
                           _("Tile cache _size:"),
                           GTK_GRID (grid), 2, size_group);
  prefs_memsize_entry_add (object, "max-new-image-size",
                           _("Maximum _new image size:"),
                           GTK_GRID (grid), 3, size_group);

  prefs_compression_combo_box_add (object, "swap-compression",
                                   _("S_wap compression:"),
                                   GTK_GRID (grid), 4, size_group);

#ifdef ENABLE_MP
  prefs_spin_button_add (object, "num-processors", 1.0, 4.0, 0,
                         _("Number of _threads to use:"),
                         GTK_GRID (grid), 5, size_group);
#endif /* ENABLE_MP */

  /*  Internet access  */
#ifdef CHECK_UPDATE
  if (gimp_version_check_update ())
    {
      vbox2 = prefs_frame_new (_("Network access"), GTK_CONTAINER (vbox),
                               FALSE);

      prefs_switch_add (object, "check-updates",
                        _("Check for updates (requires internet)"),
                        GTK_BOX (vbox2),
                        size_group, NULL);
    }
#endif

  /*  Image Thumbnails  */
  vbox2 = prefs_frame_new (_("Image Thumbnails"), GTK_CONTAINER (vbox), FALSE);

  grid = prefs_grid_new (GTK_CONTAINER (vbox2));

  prefs_enum_combo_box_add (object, "thumbnail-size", 0, 0,
                            _("Size of _thumbnails:"),
                            GTK_GRID (grid), 0, size_group);

  prefs_memsize_entry_add (object, "thumbnail-filesize-limit",
                           _("Maximum _filesize for thumbnailing:"),
                           GTK_GRID (grid), 1, size_group);

  /*  Document History  */
  vbox2 = prefs_frame_new (_("Document History"), GTK_CONTAINER (vbox), FALSE);

  prefs_switch_add (object, "save-document-history",
                    _("_Keep record of used files in the Recent Documents list"),
                    GTK_BOX (vbox2),
                    size_group, NULL);

  g_clear_object (&size_group);


  /***************/
  /*  Debugging  */
  /***************/
  /* No debugging preferences are needed on win32. Either AmmoOS Image has been
   * built with DrMinGW support (HAVE_EXCHNDL) or not. If it has, then
   * the backtracing is enabled and can't be disabled. It assume it will
   * work only upon a crash.
   */
#ifndef G_OS_WIN32
  vbox = gimp_prefs_box_add_page (GIMP_PREFS_BOX (prefs_box),
                                  "ammoos-wilber-eek", /* TODO: icon needed. */
                                  _("Debugging"),
                                  _("Debugging"),
                                  GIMP_HELP_PREFS_DEBUGGING,
                                  NULL,
                                  &top_iter);

  hbox = g_object_new (GIMP_TYPE_HINT_BOX,
                       "icon-name", GIMP_ICON_DIALOG_WARNING,
                       "hint",      _("We hope you will never need these "
                                      "settings, but as all software, AmmoOS Image "
                                      "has bugs, and crashes can occur. If it "
                                      "happens, you can help us by reporting "
                                      "bugs."),
                        NULL);
  gtk_box_pack_start (GTK_BOX (vbox), hbox, FALSE, FALSE, 0);
  gtk_widget_set_visible (hbox, TRUE);

  vbox2 = prefs_frame_new (_("Bug Reporting"),
                           GTK_CONTAINER (vbox), FALSE);

  grid = prefs_grid_new (GTK_CONTAINER (vbox2));

  button = prefs_enum_combo_box_add (object, "debug-policy", 0, 0,
                                     _("Debug _policy:"),
                                     GTK_GRID (grid), 0, NULL);

  /* Check existence of gdb or lldb to activate the preference, as a
   * good hint of its prerequisite, unless backtrace() API exists, in
   * which case the feature is always available.
   */
  hbox = NULL;
  if (! gimp_stack_trace_available (TRUE))
    {
#ifndef HAVE_EXECINFO_H
      hbox = prefs_hint_box_new (GIMP_ICON_DIALOG_WARNING,
                                 _("This feature requires \"gdb\" or \"lldb\" installed on your system."));
      gtk_widget_set_sensitive (button, FALSE);
#else
      hbox = prefs_hint_box_new (GIMP_ICON_DIALOG_WARNING,
                                 _("This feature is more efficient with \"gdb\" or \"lldb\" installed on your system."));
#endif /* ! HAVE_EXECINFO_H */
    }
  if (hbox)
    gtk_box_pack_start (GTK_BOX (vbox2), hbox, FALSE, FALSE, 0);

#endif /* ! G_OS_WIN32 */

  /**********************/
  /*  Color Management  */
  /**********************/
  vbox = gimp_prefs_box_add_page (GIMP_PREFS_BOX (prefs_box),
                                  "ammoos-prefs-color-management",
                                  _("Color Management"),
                                  _("Color Management"),
                                  GIMP_HELP_PREFS_COLOR_MANAGEMENT,
                                  NULL,
                                  &top_iter);

  gimp_prefs_box_set_page_scrollable (GIMP_PREFS_BOX (prefs_box), vbox, TRUE);

  button = gimp_prefs_box_set_page_resettable (GIMP_PREFS_BOX (prefs_box),
                                               vbox,
                                               _("R_eset Color Management"));
  g_signal_connect (button, "clicked",
                    G_CALLBACK (prefs_color_management_reset),
                    config);

  {
    GObject      *color_config = G_OBJECT (core_config->color_management);
    GtkListStore *store;
    GFile        *file;
    gint          row = 0;

    file = gimp_directory_file ("profilerc", NULL);
    store = gimp_color_profile_store_new (file);
    g_object_unref (file);

    gimp_color_profile_store_add_file (GIMP_COLOR_PROFILE_STORE (store),
                                       NULL, NULL);

    size_group = gtk_size_group_new (GTK_SIZE_GROUP_HORIZONTAL);

    grid = prefs_grid_new (GTK_CONTAINER (vbox));

    prefs_enum_combo_box_add (color_config, "mode", 0, 0,
                              _("Image display _mode:"),
                              GTK_GRID (grid), row++, NULL);

    /*  Color Managed Display  */
    vbox2 = prefs_frame_new (_("Color Managed Display"), GTK_CONTAINER (vbox),
                             FALSE);

    grid = prefs_grid_new (GTK_CONTAINER (vbox2));
    row = 0;

    prefs_profile_combo_box_add (color_config,
                                 "display-profile",
                                 store,
                                 _("Select Monitor Color Profile"),
                                 _("_Monitor profile:"),
                                 GTK_GRID (grid), row++, size_group,
                                 object, "color-profile-path");

    button = gimp_prop_check_button_new (color_config,
                                         "display-profile-from-gdk",
                                         _("_Try to use the system monitor "
                                           "profile"));
    gtk_grid_attach (GTK_GRID (grid), button, 1, row, 1, 1);
    row++;

    prefs_enum_combo_box_add (color_config,
                              "display-rendering-intent", 0, 0,
                              _("_Rendering intent:"),
                              GTK_GRID (grid), row++, size_group);

    button = gimp_prop_check_button_new (color_config,
                                         "display-use-black-point-compensation",
                                         _("Use _black point compensation"));
    gtk_grid_attach (GTK_GRID (grid), button, 1, row, 1, 1);
    row++;

    prefs_boolean_combo_box_add (color_config,
                                 "display-optimize",
                                 _("Speed"),
                                 _("Precision / Color Fidelity"),
                                 _("_Optimize image display for:"),
                                 GTK_GRID (grid), row++, size_group);

    /*  Print Simulation (Soft-proofing)  */
    vbox2 = prefs_frame_new (_("Soft-Proofing"),
                             GTK_CONTAINER (vbox),
                             FALSE);

    grid = prefs_grid_new (GTK_CONTAINER (vbox2));
    row = 0;

    prefs_boolean_combo_box_add (color_config,
                                 "simulation-optimize",
                                 _("Speed"),
                                 _("Precision / Color Fidelity"),
                                 _("O_ptimize soft-proofing for:"),
                                 GTK_GRID (grid), row++, size_group);

    hbox = gtk_box_new (GTK_ORIENTATION_HORIZONTAL, 6);
    gtk_grid_attach (GTK_GRID (grid), hbox, 1, row, 1, 1);
    gtk_widget_set_visible (hbox, TRUE);
    row++;

    button = gimp_prop_check_button_new (color_config, "simulation-gamut-check",
                                         _("Mar_k out of gamut colors"));
    gtk_box_pack_start (GTK_BOX (hbox), button, TRUE, TRUE, 0);

    button = gimp_prop_color_button_new (color_config, "out-of-gamut-color",
                                         _("Select Warning Color"), FALSE,
                                         PREFS_COLOR_BUTTON_WIDTH,
                                         PREFS_COLOR_BUTTON_HEIGHT,
                                         GIMP_COLOR_AREA_FLAT);
    gtk_box_pack_start (GTK_BOX (hbox), button, FALSE, FALSE, 0);

    gimp_color_panel_set_context (GIMP_COLOR_PANEL (button),
                                  gimp_get_user_context (ammoos));

    /*  Preferred profiles  */
    vbox2 = prefs_frame_new (_("Preferred Profiles"), GTK_CONTAINER (vbox),
                             FALSE);

    grid = prefs_grid_new (GTK_CONTAINER (vbox2));
    row = 0;

    prefs_profile_combo_box_add (color_config,
                                 "rgb-profile",
                                 store,
                                 _("Select Preferred RGB Color Profile"),
                                 _("_RGB profile:"),
                                 GTK_GRID (grid), row++, size_group,
                                 object, "color-profile-path");

    prefs_profile_combo_box_add (color_config,
                                 "gray-profile",
                                 store,
                                 _("Select Preferred Grayscale Color Profile"),
                                 _("_Grayscale profile:"),
                                 GTK_GRID (grid), row++, size_group,
                                 object, "color-profile-path");

    prefs_profile_combo_box_add (color_config,
                                 "cmyk-profile",
                                 store,
                                 _("Select CMYK Color Profile"),
                                 _("_CMYK profile:"),
                                 GTK_GRID (grid), row++, size_group,
                                 object, "color-profile-path");

    /*  Policies  */
    vbox2 = prefs_frame_new (_("Policies"), GTK_CONTAINER (vbox),
                             FALSE);
    grid = prefs_grid_new (GTK_CONTAINER (vbox2));

    button = prefs_enum_combo_box_add (object, "color-profile-policy", 0, 0,
                                       _("_File Open behavior:"),
                                       GTK_GRID (grid), 0, size_group);

    g_clear_object (&size_group);

    g_object_unref (store);
  }


  /***************************/
  /*  Image Import / Export  */
  /***************************/
  vbox = gimp_prefs_box_add_page (GIMP_PREFS_BOX (prefs_box),
                                  "ammoos-prefs-import-export",
                                  _("Image Import & Export"),
                                  _("Image Import & Export"),
                                  GIMP_HELP_PREFS_IMPORT_EXPORT,
                                  NULL,
                                  &top_iter);

  gimp_prefs_box_set_page_scrollable (GIMP_PREFS_BOX (prefs_box), vbox, TRUE);

  size_group = gtk_size_group_new (GTK_SIZE_GROUP_HORIZONTAL);

  /*  Import Policies  */
  vbox2 = prefs_frame_new (_("Import Policies"),
                           GTK_CONTAINER (vbox), FALSE);

  button = prefs_check_button_add (object, "import-promote-float",
                                   _("Promote imported images to "
                                     "_floating point precision"),
                                   GTK_BOX (vbox2));

  vbox3 = prefs_frame_new (NULL, GTK_CONTAINER (vbox2), FALSE);
  g_object_bind_property (button, "active",
                          vbox3,  "sensitive",
                          G_BINDING_SYNC_CREATE);
  button = prefs_check_button_add (object, "import-promote-dither",
                                   _("_Dither images when promoting to "
                                     "floating point"),
                                   GTK_BOX (vbox3));

  button = prefs_check_button_add (object, "import-add-alpha",
                                   _("_Add an alpha channel to imported images"),
                                   GTK_BOX (vbox2));

  grid = prefs_grid_new (GTK_CONTAINER (vbox2));
  button = prefs_enum_combo_box_add (object, "color-profile-policy", 0, 0,
                                     _("Color _profile policy:"),
                                     GTK_GRID (grid), 0, size_group);
  button = prefs_enum_combo_box_add (object, "metadata-rotation-policy", 0, 0,
                                     _("Metadata _rotation policy:"),
                                     GTK_GRID (grid), 1, size_group);

  /*  Export Policies  */
  vbox2 = prefs_frame_new (_("Export Policies"),
                           GTK_CONTAINER (vbox), FALSE);

  button = prefs_check_button_add (object, "export-color-profile",
                                   _("Export the i_mage's color profile by default"),
                                   GTK_BOX (vbox2));
  button = prefs_check_button_add (object, "export-comment",
                                   _("Export the image's comment by default"),
                                   GTK_BOX (vbox2));
  button = prefs_check_button_add (object, "export-thumbnail",
                                   _("Export the image's thumbnail by default"),
                                   GTK_BOX (vbox2));
  button = prefs_check_button_add (object, "export-metadata-exif",
                                   /* Translators: label for
                                    * configuration option (checkbox).
                                    * It determines how file export
                                    * plug-ins handle Exif by default.
                                    */
                                   _("Export _Exif metadata by default when available"),
                                   GTK_BOX (vbox2));
  button = prefs_check_button_add (object, "export-metadata-xmp",
                                   /* Translators: label for
                                    * configuration option (checkbox).
                                    * It determines how file export
                                    * plug-ins handle XMP by default.
                                    */
                                   _("Export _XMP metadata by default when available"),
                                   GTK_BOX (vbox2));
  button = prefs_check_button_add (object, "export-metadata-iptc",
                                   /* Translators: label for
                                    * configuration option (checkbox).
                                    * It determines how file export
                                    * plug-ins handle IPTC by default.
                                    */
                                   _("Export _IPTC metadata by default when available"),
                                   GTK_BOX (vbox2));
  button = prefs_check_button_add (object, "export-update-metadata",
                                   _("Update metadata automatically"),
                                   GTK_BOX (vbox2));
  hbox = prefs_hint_box_new (GIMP_ICON_DIALOG_WARNING,
                             _("Metadata can contain sensitive information."));
  gtk_box_pack_start (GTK_BOX (vbox2), hbox, FALSE, FALSE, 0);

  /*  Export File Type  */
  vbox2 = prefs_frame_new (_("Export File Type"), GTK_CONTAINER (vbox), FALSE);
  grid = prefs_grid_new (GTK_CONTAINER (vbox2));

  prefs_enum_combo_box_add (object, "export-file-type", 0, 0,
                            _("Default export file t_ype:"),
                            GTK_GRID (grid), 0, size_group);

  /*  Raw Image Importer  */
  vbox2 = prefs_frame_new (_("Raw Image Importer"),
                           GTK_CONTAINER (vbox), TRUE);

  {
    GtkWidget *scrolled_window;
    GtkWidget *view;

    scrolled_window = gtk_scrolled_window_new (NULL, NULL);
    gtk_scrolled_window_set_policy (GTK_SCROLLED_WINDOW (scrolled_window),
                                    GTK_POLICY_AUTOMATIC, GTK_POLICY_AUTOMATIC);
    gtk_scrolled_window_set_shadow_type (GTK_SCROLLED_WINDOW (scrolled_window),
                                         GTK_SHADOW_IN);
    gtk_box_pack_start (GTK_BOX (vbox2), scrolled_window, TRUE, TRUE, 0);
    gtk_widget_set_visible (scrolled_window, TRUE);

    view = gimp_plug_in_view_new (ammoos->plug_in_manager->display_raw_load_procs);
    gimp_plug_in_view_set_plug_in (GIMP_PLUG_IN_VIEW (view),
                                   core_config->import_raw_plug_in);
    gtk_container_add (GTK_CONTAINER (scrolled_window), view);
    gtk_widget_set_visible (view, TRUE);

    g_signal_connect (view, "changed",
                      G_CALLBACK (prefs_import_raw_procedure_callback),
                      config);
  }

  g_clear_object (&size_group);


  /****************/
  /*  Playground  */
  /****************/
  if (ammoos->show_playground)
    {
      vbox = gimp_prefs_box_add_page (GIMP_PREFS_BOX (prefs_box),
                                      "ammoos-prefs-playground",
                                      _("Experimental Playground"),
                                      _("Playground"),
                                      GIMP_HELP_PREFS_PLAYGROUND,
                                      NULL,
                                      &top_iter);

      hbox = g_object_new (GIMP_TYPE_HINT_BOX,
                           "icon-name", GIMP_ICON_DIALOG_WARNING,
                           "hint",      _("These features are unfinished, buggy "
                                          "and may crash AmmoOS Image. It is unadvised to "
                                          "use them unless you really know what "
                                          "you are doing or you intend to contribute "
                                          "patches."),
                           NULL);
      gtk_box_pack_start (GTK_BOX (vbox), hbox, FALSE, FALSE, 0);
      gtk_widget_set_visible (hbox, TRUE);

      /*  Hardware Acceleration  */
      vbox2 = prefs_frame_new (_("Hardware Acceleration"), GTK_CONTAINER (vbox),
                               FALSE);

      hbox = prefs_hint_box_new (GIMP_ICON_DIALOG_WARNING,
                                 _("OpenCL drivers and support are experimental, "
                                   "expect slowdowns and possible crashes "
                                   "(please report)."));
      gtk_box_pack_start (GTK_BOX (vbox2), hbox, FALSE, FALSE, 0);

      prefs_switch_add (object, "use-opencl",
                        _("Use O_penCL"),
                        GTK_BOX (vbox2),
                        NULL, NULL);

      /*  Very unstable tools  */
      vbox2 = prefs_frame_new (_("Experimental"),
                               GTK_CONTAINER (vbox), FALSE);

      button = prefs_check_button_add (object, "playground-npd-tool",
                                       _("_N-Point Deformation tool"),
                                       GTK_BOX (vbox2));
      button = prefs_check_button_add (object, "playground-seamless-clone-tool",
                                       _("_Seamless Clone tool"),
                                       GTK_BOX (vbox2));
      button = prefs_check_button_add (object, "playground-paint-select-tool",
                                       _("_Paint Select tool"),
                                       GTK_BOX (vbox2));
      if (! gegl_has_operation ("gegl:paint-select"))
        {
          gtk_toggle_button_set_active (GTK_TOGGLE_BUTTON (button), FALSE);
          gtk_widget_set_sensitive (button, FALSE);
          /* The tooltip is not translated on purpose. By the time it
           * hits stable release, I sure hope this won't be considered
           * an optional operation anymore. The info is still useful for
           * dev-release testers, but no need to bother translators with
           * a temporary string otherwise.
           */
          gimp_help_set_help_data (button, "Missing GEGL operation 'gegl:paint-select'.", NULL);
        }
      button = prefs_check_button_add (object, "playground-use-list-box",
                                       _("Use GtkListBox in simple lists"),
                                       GTK_BOX (vbox2));
    }


  /******************/
  /*  Tool Options  */
  /******************/
  vbox = gimp_prefs_box_add_page (GIMP_PREFS_BOX (prefs_box),
                                  "ammoos-prefs-tool-options",
                                  C_("preferences", "Tool Options"),
                                  C_("preferences", "Tool Options"),
                                  GIMP_HELP_PREFS_TOOL_OPTIONS,
                                  NULL,
                                  &top_iter);
  gimp_prefs_box_set_page_scrollable (GIMP_PREFS_BOX (prefs_box), vbox, TRUE);

  size_group = gtk_size_group_new (GTK_SIZE_GROUP_HORIZONTAL);

  /*  General  */
  vbox2 = prefs_frame_new (_("General"), GTK_CONTAINER (vbox), FALSE);

  prefs_check_button_add (object, "edit-non-visible",
                          _("Allow _editing on non-visible layers"),
                          GTK_BOX (vbox2));

  prefs_check_button_add (object, "save-tool-options",
                          _("_Save tool options on exit"),
                          GTK_BOX (vbox2));

  button = prefs_button_add (GIMP_ICON_DOCUMENT_SAVE,
                             _("Save Tool Options _Now"),
                             GTK_BOX (vbox2));
  g_signal_connect (button, "clicked",
                    G_CALLBACK (prefs_tool_options_save_callback),
                    ammoos);

  button2 = prefs_button_add (GIMP_ICON_RESET,
                              _("_Reset Saved Tool Options to "
                                "Default Values"),
                              GTK_BOX (vbox2));
  g_signal_connect (button2, "clicked",
                    G_CALLBACK (prefs_tool_options_clear_callback),
                    ammoos);

  g_object_set_data (G_OBJECT (button), "clear-button", button2);

  /*  Scaling  */
  vbox2 = prefs_frame_new (_("Scaling"), GTK_CONTAINER (vbox), FALSE);
  grid = prefs_grid_new (GTK_CONTAINER (vbox2));

  prefs_enum_combo_box_add (object, "interpolation-type", 0, 0,
                            _("Default _interpolation:"),
                            GTK_GRID (grid), 0, size_group);

  g_object_unref (size_group);

  size_group = gtk_size_group_new (GTK_SIZE_GROUP_HORIZONTAL);

  /*  Global Brush, Pattern, ...  */
  vbox2 = prefs_frame_new (_("Paint Options Shared Between Tools"),
                           GTK_CONTAINER (vbox), FALSE);

  prefs_check_button_add_with_icon (object, "global-brush",
                                    _("_Brush"),    GIMP_ICON_BRUSH,
                                    GTK_BOX (vbox2), size_group);
  prefs_check_button_add_with_icon (object, "global-dynamics",
                                    _("_Dynamics"), GIMP_ICON_DYNAMICS,
                                    GTK_BOX (vbox2), size_group);
  prefs_check_button_add_with_icon (object, "global-pattern",
                                    _("_Pattern"),  GIMP_ICON_PATTERN,
                                    GTK_BOX (vbox2), size_group);
  prefs_check_button_add_with_icon (object, "global-gradient",
                                    _("_Gradient"), GIMP_ICON_GRADIENT,
                                    GTK_BOX (vbox2), size_group);
  prefs_check_button_add_with_icon (object, "global-expand",
                                    _("E_xpand Layers"), GIMP_ICON_TOOL_SCALE,
                                    GTK_BOX (vbox2), size_group);

  /*  Move Tool */
  vbox2 = prefs_frame_new (_("Move Tool"),
                           GTK_CONTAINER (vbox), FALSE);

  prefs_check_button_add_with_icon (object, "move-tool-changes-active",
                                    _("Set _layer or path as active"),
                                    GIMP_ICON_TOOL_MOVE,
                                    GTK_BOX (vbox2), size_group);

  g_clear_object (&size_group);


  /*******************/
  /*  Default Image  */
  /*******************/
  vbox = gimp_prefs_box_add_page (GIMP_PREFS_BOX (prefs_box),
                                  "ammoos-prefs-new-image",
                                  _("Default New Image"),
                                  _("Default Image"),
                                  GIMP_HELP_PREFS_NEW_IMAGE,
                                  NULL,
                                  &top_iter);

  gimp_prefs_box_set_page_scrollable (GIMP_PREFS_BOX (prefs_box), vbox, TRUE);

  grid = prefs_grid_new (GTK_CONTAINER (vbox));

  {
    GtkWidget *combo;

    combo = gimp_container_combo_box_new (ammoos->templates,
                                          gimp_get_user_context (ammoos),
                                          16, 0);
    gimp_grid_attach_aligned (GTK_GRID (grid), 0, 0,
                               _("_Template:"),  0.0, 0.5,
                               combo, 1);

    gimp_container_view_set_1_selected (GIMP_CONTAINER_VIEW (combo), NULL);

    g_signal_connect (combo, "selection-changed",
                      G_CALLBACK (prefs_template_select_callback),
                      core_config->default_image);
  }

  editor = gimp_template_editor_new (core_config->default_image, ammoos, FALSE);
  gtk_widget_set_vexpand (editor, FALSE);
  gimp_template_editor_show_advanced (GIMP_TEMPLATE_EDITOR (editor), TRUE);
  gtk_box_pack_start (GTK_BOX (vbox), editor, FALSE, FALSE, 0);
  gtk_widget_set_visible (editor, TRUE);

  /*  Quick Mask Color */
  vbox2 = prefs_frame_new (_("Quick Mask"), GTK_CONTAINER (vbox), FALSE);
  grid = prefs_grid_new (GTK_CONTAINER (vbox2));

  prefs_color_button_add (object, "quick-mask-color",
                          _("Quick Mask color:"),
                          _("Set the default Quick Mask color"),
                          GTK_GRID (grid), 0, NULL,
                          gimp_get_user_context (ammoos));


  /**********************************/
  /*  Default Image / Default Grid  */
  /**********************************/
  vbox = gimp_prefs_box_add_page (GIMP_PREFS_BOX (prefs_box),
                                  "ammoos-prefs-default-grid",
                                  _("Default Image Grid"),
                                  _("Default Grid"),
                                  GIMP_HELP_PREFS_DEFAULT_GRID,
                                  &top_iter,
                                  &child_iter);
  gimp_prefs_box_set_page_scrollable (GIMP_PREFS_BOX (prefs_box), vbox, TRUE);

  /*  Grid  */
  editor = gimp_grid_editor_new (core_config->default_grid,
                                 gimp_get_user_context (ammoos),
                                 gimp_template_get_resolution_x (core_config->default_image),
                                 gimp_template_get_resolution_y (core_config->default_image));
  gtk_box_pack_start (GTK_BOX (vbox), editor, TRUE, TRUE, 0);
  gtk_widget_set_visible (editor, TRUE);


  /***************/
  /*  Interface  */
  /***************/
  vbox = gimp_prefs_box_add_page (GIMP_PREFS_BOX (prefs_box),
                                  "ammoos-prefs-interface",
                                  _("User Interface"),
                                  _("Interface"),
                                  GIMP_HELP_PREFS_INTERFACE,
                                  NULL,
                                  &top_iter);
  gimp_prefs_box_set_page_scrollable (GIMP_PREFS_BOX (prefs_box), vbox, TRUE);

  /*  Language  */

  /*  Only add the language entry if the iso-codes package is available.  */
#ifdef HAVE_ISO_CODES
  vbox2 = prefs_frame_new (_("Language"), GTK_CONTAINER (vbox), FALSE);

  prefs_language_combo_box_add (object, "language", GTK_BOX (vbox2));
#endif

  /*  Previews  */
  vbox2 = prefs_frame_new (_("Previews"), GTK_CONTAINER (vbox), FALSE);

  button = prefs_check_button_add (object, "layer-previews",
                                   _("_Enable layer & channel previews"),
                                   GTK_BOX (vbox2));

  vbox3 = prefs_frame_new (NULL, GTK_CONTAINER (vbox2), FALSE);
  g_object_bind_property (button, "active",
                          vbox3,  "sensitive",
                          G_BINDING_SYNC_CREATE);
  button = prefs_check_button_add (object, "group-layer-previews",
                                   _("Enable layer _group previews"),
                                   GTK_BOX (vbox3));

  grid = prefs_grid_new (GTK_CONTAINER (vbox2));

  prefs_enum_combo_box_add (object, "layer-preview-size", 0, 0,
                            _("_Default layer & channel preview size:"),
                            GTK_GRID (grid), 0, NULL);
  prefs_enum_combo_box_add (object, "undo-preview-size", 0, 0,
                            _("_Undo preview size:"),
                            GTK_GRID (grid), 1, NULL);
  prefs_enum_combo_box_add (object, "navigation-preview-size", 0, 0,
                            _("Na_vigation preview size:"),
                            GTK_GRID (grid), 2, NULL);

  /*  Item   */
  vbox2 = prefs_frame_new (_("Item search"), GTK_CONTAINER (vbox), FALSE);
  grid = prefs_grid_new (GTK_CONTAINER (vbox2));
  prefs_enum_combo_box_add (object, "items-select-method", 0, 0,
                            _("Pattern syntax for searching and selecting items:"),
                            GTK_GRID (grid), 0, NULL);

  /* Keyboard Shortcuts */
  vbox2 = prefs_frame_new (_("Keyboard Shortcuts"),
                           GTK_CONTAINER (vbox), FALSE);

  button = prefs_button_add (GIMP_ICON_PREFERENCES_SYSTEM,
                             _("Configure _Keyboard Shortcuts..."),
                             GTK_BOX (vbox2));
  g_signal_connect (button, "clicked",
                    G_CALLBACK (prefs_keyboard_shortcuts_dialog),
                    ammoos);

  prefs_check_button_add (object, "save-accels",
                          _("_Save keyboard shortcuts on exit"),
                          GTK_BOX (vbox2));

  button = prefs_button_add (GIMP_ICON_DOCUMENT_SAVE,
                             _("Save Keyboard Shortcuts _Now"),
                             GTK_BOX (vbox2));
  g_signal_connect (button, "clicked",
                    G_CALLBACK (prefs_menus_save_callback),
                    ammoos);

  button2 = prefs_button_add (GIMP_ICON_RESET,
                              _("_Reset Keyboard Shortcuts to Default Values"),
                              GTK_BOX (vbox2));
  g_signal_connect (button2, "clicked",
                    G_CALLBACK (prefs_menus_clear_callback),
                    ammoos);

  g_object_set_data (G_OBJECT (button), "clear-button", button2);

  button = prefs_button_add (GIMP_ICON_EDIT_CLEAR,
                             _("Remove _All Keyboard Shortcuts"),
                             GTK_BOX (vbox2));
  g_signal_connect (button, "clicked",
                    G_CALLBACK (prefs_menus_remove_callback),
                    ammoos);


  /***********************/
  /*  Interface / Theme  */
  /***********************/
  vbox = gimp_prefs_box_add_page (GIMP_PREFS_BOX (prefs_box),
                                  "ammoos-prefs-theme",
                                  _("Theme"),
                                  _("Theme"),
                                  GIMP_HELP_PREFS_THEME,
                                  &top_iter,
                                  &child_iter);

  vbox2 = prefs_frame_new (_("Select Theme"), GTK_CONTAINER (vbox), TRUE);

  {
    GtkWidget         *scrolled_win;
    GtkWidget         *listbox;
    GtkWidget         *scale;
    gchar            **themes;
    gint               n_themes;
    gint               i;
    gulong             reset_handler;

    scrolled_win = gtk_scrolled_window_new (NULL, NULL);
    gtk_widget_set_size_request (scrolled_win, -1, 80);
    gtk_scrolled_window_set_shadow_type (GTK_SCROLLED_WINDOW (scrolled_win),
                                         GTK_SHADOW_IN);
    gtk_scrolled_window_set_policy (GTK_SCROLLED_WINDOW (scrolled_win),
                                    GTK_POLICY_AUTOMATIC,
                                    GTK_POLICY_AUTOMATIC);
    gtk_box_pack_start (GTK_BOX (vbox2), scrolled_win, TRUE, TRUE, 0);
    gtk_widget_set_visible (scrolled_win, TRUE);

    listbox = gtk_list_box_new ();
    gtk_list_box_set_selection_mode (GTK_LIST_BOX (listbox),
                                     GTK_SELECTION_BROWSE);
    gtk_style_context_add_class (gtk_widget_get_style_context (GTK_WIDGET (listbox)),
                                 "view");
    gtk_container_add (GTK_CONTAINER (scrolled_win), listbox);
    gtk_widget_set_visible (listbox, TRUE);

    themes = themes_list_themes (ammoos, &n_themes);

    for (i = 0; i < n_themes; i++)
      {
        GtkWidget *row;
        GtkWidget *grid;
        GtkWidget *name_label, *folder_label;
        GFile     *theme_dir = themes_get_theme_dir (ammoos, themes[i]);

        row = gtk_list_box_row_new ();
        g_object_set_data_full (G_OBJECT (row),
                                "theme",
                                g_strdup (themes[i]),
                                g_free);

        grid = gtk_grid_new ();
        gtk_grid_set_column_spacing (GTK_GRID (grid), 12);
        gtk_container_add (GTK_CONTAINER (row), grid);

        name_label = gtk_label_new (themes[i]);
        g_object_set (name_label, "xalign", 0.0, NULL);
        gtk_grid_attach (GTK_GRID (grid), name_label, 1, 0, 1, 1);

        folder_label = gtk_label_new (gimp_file_get_utf8_name (theme_dir));
        g_object_set (folder_label, "xalign", 0.0, NULL);
        gtk_style_context_add_class (gtk_widget_get_style_context (folder_label),
                                     "dim-label");
        gtk_grid_attach (GTK_GRID (grid), folder_label, 1, 1, 1, 1);

        gtk_widget_show_all (row);
        gtk_list_box_insert (GTK_LIST_BOX (listbox), row, -1);

        if (GIMP_GUI_CONFIG (object)->theme &&
            ! strcmp (GIMP_GUI_CONFIG (object)->theme, themes[i]))
          {
            gtk_list_box_select_row (GTK_LIST_BOX (listbox),
                                     GTK_LIST_BOX_ROW (row));
          }
      }

    g_strfreev (themes);

    g_signal_connect (listbox, "row-selected",
                      G_CALLBACK (prefs_theme_select_callback),
                      ammoos);
    reset_handler =
      g_signal_connect (G_OBJECT (ammoos->config), "notify::theme",
                        G_CALLBACK (prefs_theme_reset_callback),
                        listbox);
    g_object_set_data (G_OBJECT (dialog), "ammoos-theme-reset-handler",
                       GUINT_TO_POINTER (reset_handler));

    grid = prefs_grid_new (GTK_CONTAINER (vbox2));
    button = prefs_enum_combo_box_add (object, "theme-color-scheme",
                                       0, 0,
                                       _("Color scheme (if available)"),
                                       GTK_GRID (grid), 0, NULL);

    /* Override icon sizes. */
    button = prefs_check_button_add (object, "override-theme-icon-size",
                                     _("_Override icon sizes set by the theme"),
                                     GTK_BOX (vbox2));

    vbox3 = prefs_frame_new (NULL, GTK_CONTAINER (vbox2), FALSE);
    g_object_bind_property (button, "active",
                            vbox3,  "sensitive",
                            G_BINDING_SYNC_CREATE);
    scale = gtk_scale_new_with_range (GTK_ORIENTATION_HORIZONTAL,
                                      0.0, 3.0, 1.0);
    /* 'draw_value' updates round_digits. So set it first. */
    gtk_scale_set_draw_value (GTK_SCALE (scale), FALSE);
    gtk_range_set_round_digits (GTK_RANGE (scale), 0.0);
    gtk_scale_add_mark (GTK_SCALE (scale), 0.0, GTK_POS_BOTTOM,
                        _("Small"));
    gtk_scale_add_mark (GTK_SCALE (scale), 1.0, GTK_POS_BOTTOM,
                        _("Medium"));
    gtk_scale_add_mark (GTK_SCALE (scale), 2.0, GTK_POS_BOTTOM,
                        _("Large"));
    gtk_scale_add_mark (GTK_SCALE (scale), 3.0, GTK_POS_BOTTOM,
                        _("Huge"));
    gtk_range_set_value (GTK_RANGE (scale),
                         (gdouble) GIMP_GUI_CONFIG (object)->custom_icon_size);
    g_signal_connect (G_OBJECT (scale), "value-changed",
                      G_CALLBACK (prefs_icon_size_value_changed),
                      GIMP_GUI_CONFIG (object));
    g_signal_connect (G_OBJECT (object), "notify::custom-icon-size",
                      G_CALLBACK (prefs_gui_config_notify_icon_size),
                      scale);
    gtk_box_pack_start (GTK_BOX (vbox3), scale, FALSE, FALSE, 0);
    gtk_widget_set_visible (scale, TRUE);

    /* Font sizes. */
    vbox3 = prefs_frame_new (_("Font Scaling"), GTK_CONTAINER (vbox2), FALSE);
    gimp_help_set_help_data (vbox3,
                             _("Font scaling will not work with themes using absolute sizes."),
                             NULL);
    scale = gtk_scale_new_with_range (GTK_ORIENTATION_HORIZONTAL,
                                      50, 200, 10);
    gtk_scale_set_value_pos (GTK_SCALE (scale), GTK_POS_BOTTOM);
    gtk_scale_add_mark (GTK_SCALE (scale), 50.0, GTK_POS_BOTTOM,
                        _("50%"));
    gtk_scale_add_mark (GTK_SCALE (scale), 100.0, GTK_POS_BOTTOM,
                        _("100%"));
    gtk_scale_add_mark (GTK_SCALE (scale), 200.0, GTK_POS_BOTTOM,
                        _("200%"));
    gtk_range_set_value (GTK_RANGE (scale),
                         (gdouble) GIMP_GUI_CONFIG (object)->font_relative_size * 100.0);
    g_signal_connect (G_OBJECT (scale), "value-changed",
                      G_CALLBACK (prefs_font_size_value_changed),
                      GIMP_GUI_CONFIG (object));
    g_signal_connect (G_OBJECT (object), "notify::font-relative-size",
                      G_CALLBACK (prefs_gui_config_notify_font_size),
                      scale);
    gtk_box_pack_start (GTK_BOX (vbox3), scale, FALSE, FALSE, 0);
    gtk_widget_set_visible (scale, TRUE);

    /* Reload Current Theme button */
    hbox = gtk_box_new (GTK_ORIENTATION_HORIZONTAL, 6);
    gtk_box_pack_start (GTK_BOX (vbox2), hbox, FALSE, FALSE, 0);
    gtk_widget_set_visible (hbox, TRUE);

    button = prefs_button_add (GIMP_ICON_VIEW_REFRESH,
                               _("Reload C_urrent Theme"),
                               GTK_BOX (hbox));
    g_signal_connect (button, "clicked",
                      G_CALLBACK (prefs_theme_reload_callback),
                      ammoos);
  }

  /****************************/
  /*  Interface / Icon Theme  */
  /****************************/
  vbox = gimp_prefs_box_add_page (GIMP_PREFS_BOX (prefs_box),
                                  "ammoos-prefs-icon-theme",
                                  _("Icon Theme"),
                                  _("Icon Theme"),
                                  GIMP_HELP_PREFS_ICON_THEME,
                                  &top_iter,
                                  &child_iter);

  vbox2 = prefs_frame_new (_("Select an Icon Theme"), GTK_CONTAINER (vbox), TRUE);

  {
    GtkWidget         *scrolled_win;
    GtkWidget         *listbox;
    gchar            **icon_themes;
    gint               scale_factor;
    gint               n_icon_themes;
    gint               i;
    gulong             reset_handler;

    scrolled_win = gtk_scrolled_window_new (NULL, NULL);
    gtk_widget_set_size_request (scrolled_win, -1, 80);
    gtk_scrolled_window_set_shadow_type (GTK_SCROLLED_WINDOW (scrolled_win),
                                         GTK_SHADOW_IN);
    gtk_scrolled_window_set_policy (GTK_SCROLLED_WINDOW (scrolled_win),
                                    GTK_POLICY_AUTOMATIC,
                                    GTK_POLICY_AUTOMATIC);
    gtk_box_pack_start (GTK_BOX (vbox2), scrolled_win, TRUE, TRUE, 0);
    gtk_widget_set_visible (scrolled_win, TRUE);

    listbox = gtk_list_box_new ();
    gtk_list_box_set_selection_mode (GTK_LIST_BOX (listbox),
                                     GTK_SELECTION_BROWSE);
    gtk_style_context_add_class (gtk_widget_get_style_context (GTK_WIDGET (listbox)),
                                 "view");
    gtk_container_add (GTK_CONTAINER (scrolled_win), listbox);
    gtk_widget_set_visible (listbox, TRUE);

     /* _("Icon Theme"), */
     /* _("Folder"), */

    scale_factor = gtk_widget_get_scale_factor (scrolled_win);
    icon_themes = icon_themes_list_themes (ammoos, &n_icon_themes);

    for (i = 0; i < n_icon_themes; i++)
      {
        GtkWidget       *row;
        GtkWidget       *grid;
        GtkWidget       *image;
        GtkWidget       *name_label, *folder_label;
        GFile           *icon_theme_dir = icon_themes_get_theme_dir (ammoos, icon_themes[i]);
        GFile           *icon_theme_search_path = g_file_get_parent (icon_theme_dir);
        GtkIconTheme    *theme;
        gchar           *example;
        cairo_surface_t *surface;

        theme = gtk_icon_theme_new ();
        gtk_icon_theme_prepend_search_path (theme,
                                            gimp_file_get_utf8_name (icon_theme_search_path));
        g_object_unref (icon_theme_search_path);
        gtk_icon_theme_set_custom_theme (theme, icon_themes[i]);

        example = gtk_icon_theme_get_example_icon_name (theme);
        if (! example)
          {
            /* If the icon theme didn't explicitly specify an example
             * icon, try "ammoos-wilber".
             */
            example = g_strdup ("ammoos-wilber-symbolic");
          }
        surface = gtk_icon_theme_load_surface (theme, example, 30,
                                               scale_factor, NULL,
                                               GTK_ICON_LOOKUP_GENERIC_FALLBACK,
                                               NULL);

        row = gtk_list_box_row_new ();
        g_object_set_data_full (G_OBJECT (row),
                                "icon-theme",
                                g_strdup (icon_themes[i]),
                                g_free);

        grid = gtk_grid_new ();
        gtk_grid_set_column_spacing (GTK_GRID (grid), 12);
        gtk_container_add (GTK_CONTAINER (row), grid);

        image = gtk_image_new_from_surface (surface);
        gtk_grid_attach (GTK_GRID (grid), image, 0, 0, 1, 2);

        name_label = gtk_label_new (icon_themes[i]);
        g_object_set (name_label, "xalign", 0.0, NULL);
        gtk_grid_attach (GTK_GRID (grid), name_label, 1, 0, 1, 1);

        folder_label = gtk_label_new (gimp_file_get_utf8_name (icon_theme_dir));
        g_object_set (folder_label, "xalign", 0.0, NULL);
        gtk_style_context_add_class (gtk_widget_get_style_context (folder_label),
                                     "dim-label");
        gtk_grid_attach (GTK_GRID (grid), folder_label, 1, 1, 1, 1);

        gtk_widget_show_all (row);
        gtk_list_box_insert (GTK_LIST_BOX (listbox), row, -1);

        g_object_unref (theme);
        cairo_surface_destroy (surface);
        g_free (example);

        if (GIMP_GUI_CONFIG (object)->icon_theme &&
            ! strcmp (GIMP_GUI_CONFIG (object)->icon_theme, icon_themes[i]))
          {
            gtk_list_box_select_row (GTK_LIST_BOX (listbox),
                                     GTK_LIST_BOX_ROW (row));

          }
      }

    g_strfreev (icon_themes);

    g_signal_connect (listbox, "row-selected",
                      G_CALLBACK (prefs_icon_theme_select_callback),
                      ammoos);
    reset_handler =
      g_signal_connect (G_OBJECT (ammoos->config), "notify::icon-theme",
                        G_CALLBACK (prefs_icon_theme_reset_callback),
                        listbox);
    g_object_set_data (G_OBJECT (dialog), "ammoos-icon-theme-reset-handler",
                       GUINT_TO_POINTER (reset_handler));

    prefs_check_button_add (object, "prefer-symbolic-icons",
                            _("Use symbolic icons if available"),
                            GTK_BOX (vbox2));
  }


  /*************************/
  /*  Interface / Toolbox  */
  /*************************/
  vbox = gimp_prefs_box_add_page (GIMP_PREFS_BOX (prefs_box),
                                  "ammoos-prefs-toolbox",
                                  _("Toolbox"),
                                  _("Toolbox"),
                                  GIMP_HELP_PREFS_TOOLBOX,
                                  &top_iter,
                                  &child_iter);

  size_group = gtk_size_group_new (GTK_SIZE_GROUP_HORIZONTAL);

  /*  Appearance  */
  vbox2 = prefs_frame_new (_("Appearance"),
                           GTK_CONTAINER (vbox), FALSE);

  prefs_check_button_add_with_icon (object, "toolbox-wilber",
                                    _("Show AmmoOS Image _logo (drag-and-drop target)"),
                                    GIMP_ICON_WILBER,
                                    GTK_BOX (vbox2), size_group);
  prefs_check_button_add_with_icon (object, "toolbox-color-area",
                                    _("Show _foreground & background color"),
                                    GIMP_ICON_COLORS_DEFAULT,
                                    GTK_BOX (vbox2), size_group);
  prefs_check_button_add_with_icon (object, "toolbox-foo-area",
                                    _("Show active _brush, pattern & gradient"),
                                    GIMP_ICON_BRUSH,
                                    GTK_BOX (vbox2), size_group);
  prefs_check_button_add_with_icon (object, "toolbox-image-area",
                                    _("Show active _image"),
                                    GIMP_ICON_IMAGE,
                                    GTK_BOX (vbox2), size_group);

  separator = gtk_separator_new (GTK_ORIENTATION_HORIZONTAL);
  gtk_box_pack_start (GTK_BOX (vbox2), separator, FALSE, FALSE, 0);
  gtk_widget_set_visible (separator, TRUE);

  prefs_check_button_add_with_icon (object, "toolbox-groups",
                                    _("Use tool _groups"),
                                    NULL,
                                    GTK_BOX (vbox2), size_group);

  g_clear_object (&size_group);

  /* Tool Editor */
  vbox2 = prefs_frame_new (_("Tools Configuration"),
                           GTK_CONTAINER (vbox), TRUE);
  tool_editor = gimp_tool_editor_new (ammoos->tool_item_list, ammoos->user_context,
                                      GIMP_VIEW_SIZE_SMALL, 0);

  gtk_box_pack_start (GTK_BOX (vbox2), tool_editor, TRUE, TRUE, 0);
  gtk_widget_set_visible (tool_editor, TRUE);


  /*********************************/
  /*  Interface / Dialog Defaults  */
  /*********************************/
  vbox = gimp_prefs_box_add_page (GIMP_PREFS_BOX (prefs_box),
                                  /* FIXME need an icon */
                                  "ammoos-prefs-controllers",
                                  _("Dialog Defaults"),
                                  _("Dialog Defaults"),
                                  GIMP_HELP_PREFS_DIALOG_DEFAULTS,
                                  &top_iter,
                                  &child_iter);

  gimp_prefs_box_set_page_scrollable (GIMP_PREFS_BOX (prefs_box), vbox, TRUE);

  button = gimp_prefs_box_set_page_resettable (GIMP_PREFS_BOX (prefs_box),
                                               vbox,
                                               _("Reset Dialog _Defaults"));
  g_signal_connect (button, "clicked",
                    G_CALLBACK (prefs_dialog_defaults_reset),
                    config);

  size_group = gtk_size_group_new (GTK_SIZE_GROUP_HORIZONTAL);

  /*  Color profile import dialog  */
  vbox2 = prefs_frame_new (_("Color Profile Import Dialog"), GTK_CONTAINER (vbox),
                           FALSE);
  grid = prefs_grid_new (GTK_CONTAINER (vbox2));

  button = prefs_enum_combo_box_add (object, "color-profile-policy", 0, 0,
                                     _("Color profile policy:"),
                                     GTK_GRID (grid), 0, size_group);

  /*  All color profile chooser dialogs  */
  vbox2 = prefs_frame_new (_("Color Profile File Dialogs"), GTK_CONTAINER (vbox),
                           FALSE);
  grid = prefs_grid_new (GTK_CONTAINER (vbox2));

  prefs_file_chooser_button_add (object, "color-profile-path",
                                 _("Profile folder:"),
                                 _("Select Default Folder for Color Profiles"),
                                 GTK_GRID (grid), 0, size_group);

  /*  Convert to Color Profile Dialog  */
  vbox2 = prefs_frame_new (_("Convert to Color Profile Dialog"),
                           GTK_CONTAINER (vbox), FALSE);
  grid = prefs_grid_new (GTK_CONTAINER (vbox2));

  prefs_enum_combo_box_add (object, "image-convert-profile-intent", 0, 0,
                            _("Rendering intent:"),
                            GTK_GRID (grid), 0, size_group);

  prefs_check_button_add (object, "image-convert-profile-black-point-compensation",
                          _("Black point compensation"),
                          GTK_BOX (vbox2));

  /*  Convert Precision Dialog  */
  vbox2 = prefs_frame_new (_("Precision Conversion Dialog"),
                           GTK_CONTAINER (vbox), FALSE);
  grid = prefs_grid_new (GTK_CONTAINER (vbox2));

  prefs_enum_combo_box_add (object,
                            "image-convert-precision-layer-dither-method",
                            0, 0,
                            _("Dither layers:"),
                            GTK_GRID (grid), 0, size_group);
  prefs_enum_combo_box_add (object,
                            "image-convert-precision-text-layer-dither-method",
                            0, 0,
                            _("Dither text layers:"),
                            GTK_GRID (grid), 1, size_group);
  prefs_enum_combo_box_add (object,
                            "image-convert-precision-channel-dither-method",
                            0, 0,
                            _("Dither channels/masks:"),
                            GTK_GRID (grid), 2, size_group);

  /*  Convert Indexed Dialog  */
  vbox2 = prefs_frame_new (_("Indexed Conversion Dialog"),
                           GTK_CONTAINER (vbox), FALSE);
  grid = prefs_grid_new (GTK_CONTAINER (vbox2));

  prefs_enum_combo_box_add (object, "image-convert-indexed-palette-type", 0, 0,
                            _("Colormap:"),
                            GTK_GRID (grid), 0, size_group);
  prefs_spin_button_add (object, "image-convert-indexed-max-colors", 1.0, 8.0, 0,
                         _("Maximum number of colors:"),
                         GTK_GRID (grid), 1, size_group);

  prefs_check_button_add (object, "image-convert-indexed-remove-duplicates",
                          _("Remove unused and duplicate colors "
                            "from colormap"),
                          GTK_BOX (vbox2));

  grid = prefs_grid_new (GTK_CONTAINER (vbox2));
  prefs_enum_combo_box_add (object, "image-convert-indexed-dither-type", 0, 0,
                            _("Color dithering:"),
                            GTK_GRID (grid), 0, size_group);

  prefs_check_button_add (object, "image-convert-indexed-dither-alpha",
                          _("Enable dithering of transparency"),
                          GTK_BOX (vbox2));
  prefs_check_button_add (object, "image-convert-indexed-dither-text-layers",
                          _("Enable dithering of text layers"),
                          GTK_BOX (vbox2));

  /*  Filter Dialogs  */
  vbox2 = prefs_frame_new (_("Filter Dialogs"),
                           GTK_CONTAINER (vbox), FALSE);
  grid = prefs_grid_new (GTK_CONTAINER (vbox2));

  prefs_spin_button_add (object, "filter-tool-max-recent", 1.0, 8.0, 0,
                         _("Keep recent settings:"),
                         GTK_GRID (grid), 1, size_group);

  button = prefs_check_button_add (object, "filter-tool-use-last-settings",
                                   _("Default to the last used settings"),
                                   GTK_BOX (vbox2));

  /*  Canvas Size Dialog  */
  vbox2 = prefs_frame_new (_("Canvas Size Dialog"),
                           GTK_CONTAINER (vbox), FALSE);
  grid = prefs_grid_new (GTK_CONTAINER (vbox2));

  prefs_enum_combo_box_add (object, "image-resize-layer-set", 0, 0,
                            _("Resize layers:"),
                            GTK_GRID (grid), 0, size_group);
  prefs_enum_combo_box_add (object, "image-resize-fill-type", 0, 0,
                            _("Fill with:"),
                            GTK_GRID (grid), 1, size_group);

  prefs_check_button_add (object, "image-resize-resize-text-layers",
                          _("Resize text layers"),
                          GTK_BOX (vbox2));

  /*  New Layer Dialog  */
  vbox2 = prefs_frame_new (_("New Layer Dialog"),
                           GTK_CONTAINER (vbox), FALSE);
  grid = prefs_grid_new (GTK_CONTAINER (vbox2));

  prefs_entry_add (object, "layer-new-name",
                   _("Layer name:"),
                   GTK_GRID (grid), 0, size_group);

  prefs_enum_combo_box_add (object, "layer-new-fill-type", 0, 0,
                            _("Fill type:"),
                            GTK_GRID (grid), 1, size_group);

  /*  Layer Boundary Size Dialog  */
  vbox2 = prefs_frame_new (_("Layer Boundary Size Dialog"),
                           GTK_CONTAINER (vbox), FALSE);
  grid = prefs_grid_new (GTK_CONTAINER (vbox2));

  prefs_enum_combo_box_add (object, "layer-resize-fill-type", 0, 0,
                            _("Fill with:"),
                            GTK_GRID (grid), 0, size_group);

  /*  Add Layer Mask Dialog  */
  vbox2 = prefs_frame_new (_("Add Layer Mask Dialog"),
                           GTK_CONTAINER (vbox), FALSE);
  grid = prefs_grid_new (GTK_CONTAINER (vbox2));

  prefs_enum_combo_box_add (object, "layer-add-mask-type", 0, 0,
                            _("Layer mask type:"),
                            GTK_GRID (grid), 0, size_group);

  prefs_check_button_add (object, "layer-add-mask-invert",
                          _("Invert mask"),
                          GTK_BOX (vbox2));
  prefs_check_button_add (object, "layer-add-mask-edit-mask",
                          _("Edit mask immediately"),
                          GTK_BOX (vbox2));

  /*  Merge Layers Dialog  */
  vbox2 = prefs_frame_new (_("Merge Layers Dialog"),
                           GTK_CONTAINER (vbox), FALSE);
  grid = prefs_grid_new (GTK_CONTAINER (vbox2));

  prefs_enum_combo_box_add (object, "layer-merge-type",
                            GIMP_EXPAND_AS_NECESSARY,
                            GIMP_CLIP_TO_BOTTOM_LAYER,
                            _("Merged layer size:"),
                            GTK_GRID (grid), 0, size_group);

  prefs_check_button_add (object, "layer-merge-active-group-only",
                          _("Merge within active groups only"),
                          GTK_BOX (vbox2));
  prefs_check_button_add (object, "layer-merge-discard-invisible",
                          _("Discard invisible layers"),
                          GTK_BOX (vbox2));

  /*  New Channel Dialog  */
  vbox2 = prefs_frame_new (_("New Channel Dialog"),
                           GTK_CONTAINER (vbox), FALSE);
  grid = prefs_grid_new (GTK_CONTAINER (vbox2));

  prefs_entry_add (object, "channel-new-name",
                   _("Channel name:"),
                   GTK_GRID (grid), 0, size_group);

  prefs_color_button_add (object, "channel-new-color",
                          _("Color and opacity:"),
                          _("Default New Channel Color and Opacity"),
                          GTK_GRID (grid), 1, size_group,
                          gimp_get_user_context (ammoos));

  /*  New Path Dialog  */
  vbox2 = prefs_frame_new (_("New Path Dialog"),
                           GTK_CONTAINER (vbox), FALSE);
  grid = prefs_grid_new (GTK_CONTAINER (vbox2));

  prefs_entry_add (object, "path-new-name",
                   _("Path name:"),
                   GTK_GRID (grid), 0, size_group);

  /*  Export Path Dialog  */
  vbox2 = prefs_frame_new (_("Export Paths Dialog"),
                           GTK_CONTAINER (vbox), FALSE);
  grid = prefs_grid_new (GTK_CONTAINER (vbox2));

  prefs_file_chooser_button_add (object, "path-export-path",
                                 _("Export folder:"),
                                 _("Select Default Folder for Exporting Paths"),
                                 GTK_GRID (grid), 0, size_group);

  prefs_check_button_add (object, "path-export-active-only",
                          _("Export the selected paths only"),
                          GTK_BOX (vbox2));

  /*  Import Path Dialog  */
  vbox2 = prefs_frame_new (_("Import Paths Dialog"),
                           GTK_CONTAINER (vbox), FALSE);
  grid = prefs_grid_new (GTK_CONTAINER (vbox2));

  prefs_file_chooser_button_add (object, "path-import-path",
                                 _("Import folder:"),
                                 _("Select Default Folder for Importing Paths"),
                                 GTK_GRID (grid), 0, size_group);

  prefs_check_button_add (object, "path-import-merge",
                          _("Merge imported paths"),
                          GTK_BOX (vbox2));
  prefs_check_button_add (object, "path-import-scale",
                          _("Scale imported paths"),
                          GTK_BOX (vbox2));

  /*  Feather Selection Dialog  */
  vbox2 = prefs_frame_new (_("Feather Selection Dialog"),
                           GTK_CONTAINER (vbox), FALSE);
  grid = prefs_grid_new (GTK_CONTAINER (vbox2));

  prefs_spin_button_add (object, "selection-feather-radius", 1.0, 10.0, 2,
                         _("Feather radius:"),
                         GTK_GRID (grid), 0, size_group);

  prefs_check_button_add (object, "selection-feather-edge-lock",
                          _("Selected areas continue outside the image"),
                          GTK_BOX (vbox2));

  /*  Grow Selection Dialog  */
  vbox2 = prefs_frame_new (_("Grow Selection Dialog"),
                           GTK_CONTAINER (vbox), FALSE);
  grid = prefs_grid_new (GTK_CONTAINER (vbox2));

  prefs_spin_button_add (object, "selection-grow-radius", 1.0, 10.0, 0,
                         _("Grow radius:"),
                         GTK_GRID (grid), 0, size_group);

  /*  Shrink Selection Dialog  */
  vbox2 = prefs_frame_new (_("Shrink Selection Dialog"),
                           GTK_CONTAINER (vbox), FALSE);
  grid = prefs_grid_new (GTK_CONTAINER (vbox2));

  prefs_spin_button_add (object, "selection-shrink-radius", 1.0, 10.0, 0,
                         _("Shrink radius:"),
                         GTK_GRID (grid), 0, size_group);

  prefs_check_button_add (object, "selection-shrink-edge-lock",
                          _("Selected areas continue outside the image"),
                          GTK_BOX (vbox2));

  /*  Border Selection Dialog  */
  vbox2 = prefs_frame_new (_("Border Selection Dialog"),
                           GTK_CONTAINER (vbox), FALSE);
  grid = prefs_grid_new (GTK_CONTAINER (vbox2));

  prefs_spin_button_add (object, "selection-border-radius", 1.0, 10.0, 0,
                         _("Border radius:"),
                         GTK_GRID (grid), 0, size_group);

  prefs_enum_combo_box_add (object, "selection-border-style", 0, 0,
                            _("Border style:"),
                            GTK_GRID (grid), 1, size_group);

  prefs_check_button_add (object, "selection-border-edge-lock",
                          _("Selected areas continue outside the image"),
                          GTK_BOX (vbox2));

  /*  Fill Options Dialog  */
  vbox2 = prefs_frame_new (_("Fill Selection Outline & Fill Path Dialogs"),
                           GTK_CONTAINER (vbox), FALSE);

  editor = gimp_fill_editor_new (GIMP_DIALOG_CONFIG (object)->fill_options,
                                 FALSE, FALSE);
  gtk_box_pack_start (GTK_BOX (vbox2), editor, FALSE, FALSE, 0);
  gtk_widget_set_visible (editor, TRUE);

  /*  Stroke Options Dialog  */
  vbox2 = prefs_frame_new (_("Stroke Selection & Stroke Path Dialogs"),
                           GTK_CONTAINER (vbox), FALSE);

  /* The stroke line width physical values could be based on either the
   * x or y resolution, some average, or whatever which makes a bit of
   * sense. There is no perfect answer. The actual stroke dialog though
   * uses the y resolution on the opened image. So using the y resolution
   * of the default image seems like the best compromise in the preferences.
   */
  editor = gimp_stroke_editor_new (GIMP_DIALOG_CONFIG (object)->stroke_options,
                                   gimp_template_get_resolution_y (core_config->default_image),
                                   FALSE, FALSE);
  gtk_box_pack_start (GTK_BOX (vbox2), editor, FALSE, FALSE, 0);
  gtk_widget_set_visible (editor, TRUE);

  g_clear_object (&size_group);


  /*****************************/
  /*  Interface / Help System  */
  /*****************************/
  vbox = gimp_prefs_box_add_page (GIMP_PREFS_BOX (prefs_box),
                                  "ammoos-prefs-help-system",
                                  _("Help System"),
                                  _("Help System"),
                                  GIMP_HELP_PREFS_HELP,
                                  &top_iter,
                                  &child_iter);

  size_group = gtk_size_group_new (GTK_SIZE_GROUP_HORIZONTAL);

  /*  General  */
  vbox2 = prefs_frame_new (_("General"), GTK_CONTAINER (vbox), FALSE);

  prefs_check_button_add (object, "show-help-button",
                          _("Show help _buttons"),
                          GTK_BOX (vbox2));

  grid = prefs_grid_new (GTK_CONTAINER (vbox2));
  button = prefs_boolean_combo_box_add (object, "user-manual-online",
                                        _("Use the online version"),
                                        _("Use a locally installed copy"),
                                        _("U_ser manual:"),
                                        GTK_GRID (grid), 0, size_group);
  gimp_help_set_help_data (button, NULL, NULL);

  manuals = gimp_help_get_installed_languages ();
  entry   = NULL;
  if (manuals != NULL)
    {
      gchar *help_locales = NULL;

      entry = gimp_language_combo_box_new (TRUE,
                                           _("User interface language"));

      g_object_get (config, "help-locales", &help_locales, NULL);
      if (help_locales && strlen (help_locales))
        {
          gchar *sep;

          sep = strchr (help_locales, ':');
          if (sep)
            *sep = '\0';
        }
      if (help_locales)
        {
          gimp_language_combo_box_set_code (GIMP_LANGUAGE_COMBO_BOX (entry),
                                            help_locales);
          g_free (help_locales);
        }
      else
        {
          gimp_language_combo_box_set_code (GIMP_LANGUAGE_COMBO_BOX (entry),
                                            "");
        }
      g_signal_connect (entry, "changed",
                        G_CALLBACK (prefs_help_language_change_callback),
                        ammoos);
      gtk_grid_attach (GTK_GRID (grid), entry, 1, 1, 1, 1);
      gtk_widget_set_visible (entry, TRUE);
    }

  if (gimp_help_user_manual_is_installed (ammoos))
    {
      hbox = prefs_hint_box_new (GIMP_ICON_DIALOG_INFORMATION,
                                 _("There's a local installation "
                                   "of the user manual."));
    }
  else
    {
      hbox = prefs_hint_box_new (GIMP_ICON_DIALOG_WARNING,
                                 _("The user manual is not installed "
                                   "locally."));
    }
  if (manuals)
    {
      g_object_set_data (G_OBJECT (hbox), "ammoos", ammoos);
      g_signal_connect (entry, "changed",
                        G_CALLBACK (prefs_help_language_change_callback2),
                        hbox);
      g_list_free_full (manuals, g_free);
    }

  gtk_grid_attach (GTK_GRID (grid), hbox, 1, 2, 1, 1);
  gtk_widget_set_visible (hbox, TRUE);

  /* Action Search */
  vbox2 = prefs_frame_new (_("Action Search"), GTK_CONTAINER (vbox), FALSE);
  grid = prefs_grid_new (GTK_CONTAINER (vbox2));

  prefs_spin_button_add (object, "action-history-size", 1.0, 10.0, 0,
                         _("_Maximum History Size:"),
                         GTK_GRID (grid), 0, size_group);

  button = prefs_button_add (GIMP_ICON_SHRED,
                             _("C_lear Action History"),
                             GTK_BOX (vbox2));
  g_signal_connect (button, "clicked",
                    G_CALLBACK (prefs_search_clear_callback),
                    ammoos);

  g_clear_object (&size_group);


  /*************************/
  /*  Interface / Display  */
  /*************************/
  vbox = gimp_prefs_box_add_page (GIMP_PREFS_BOX (prefs_box),
                                  "ammoos-prefs-display",
                                  _("Display"),
                                  _("Display"),
                                  GIMP_HELP_PREFS_DISPLAY,
                                  &top_iter,
                                  &child_iter);
  gimp_prefs_box_set_page_scrollable (GIMP_PREFS_BOX (prefs_box), vbox, TRUE);

  size_group = gtk_size_group_new (GTK_SIZE_GROUP_HORIZONTAL);

  /*  Transparency  */
  vbox2 = prefs_frame_new (_("Transparency"), GTK_CONTAINER (vbox), FALSE);
  grid = prefs_grid_new (GTK_CONTAINER (vbox2));

  prefs_enum_combo_box_add (object, "transparency-type", 0, 0,
                            _("_Check style:"),
                            GTK_GRID (grid), 0, size_group);

  button = gimp_prop_label_color_new (object,
                                      "transparency-custom-color1",
                                      TRUE);
  gimp_grid_attach_aligned (GTK_GRID (grid), 0, 1,
                            NULL, 0.0, 0.5,
                            button, 1);
  gtk_widget_set_hexpand (button, FALSE);
  gimp_color_button_set_color_config (GIMP_COLOR_BUTTON (gimp_label_color_get_color_widget (GIMP_LABEL_COLOR (button))),
                                      ammoos->config->color_management);
  gtk_widget_set_sensitive (button,
                            display_config->transparency_type == GIMP_CHECK_TYPE_CUSTOM_CHECKS);
  g_signal_connect (object, "notify::transparency-type",
                    G_CALLBACK (prefs_check_style_callback),
                    button);

  button = gimp_prop_label_color_new (object,
                                      "transparency-custom-color2",
                                      TRUE);
  gimp_grid_attach_aligned (GTK_GRID (grid), 0, 2,
                            NULL, 0.0, 0.5,
                            button, 1);
  gtk_widget_set_hexpand (button, FALSE);
  gimp_color_button_set_color_config (GIMP_COLOR_BUTTON (gimp_label_color_get_color_widget (GIMP_LABEL_COLOR (button))),
                                      ammoos->config->color_management);
  gtk_widget_set_sensitive (button,
                            display_config->transparency_type == GIMP_CHECK_TYPE_CUSTOM_CHECKS);
  g_signal_connect (object, "notify::transparency-type",
                    G_CALLBACK (prefs_check_style_callback),
                    button);

  prefs_enum_combo_box_add (object, "transparency-size", 0, 0,
                            _("Check _size:"),
                            GTK_GRID (grid), 3, size_group);

  /*  Zoom Quality  */
  vbox2 = prefs_frame_new (_("Zoom Quality"), GTK_CONTAINER (vbox), FALSE);
  grid = prefs_grid_new (GTK_CONTAINER (vbox2));

  prefs_enum_combo_box_add (object, "zoom-quality", 0, 0,
                            _("_Zoom quality:"),
                            GTK_GRID (grid), 0, size_group);

  /*  Monitor Resolution  */
  vbox2 = prefs_frame_new (_("Monitor Resolution"),
                           GTK_CONTAINER (vbox), FALSE);

  {
    gchar *pixels_per_unit = g_strconcat (_("Pixels"), "/%a", NULL);

    entry = gimp_prop_coordinates_new (object,
                                       "monitor-xresolution",
                                       "monitor-yresolution",
                                       NULL,
                                       pixels_per_unit,
                                       GIMP_SIZE_ENTRY_UPDATE_RESOLUTION,
                                       0.0, 0.0,
                                       TRUE);

    g_free (pixels_per_unit);
  }

  gtk_grid_set_column_spacing (GTK_GRID (entry), 2);
  gtk_grid_set_row_spacing (GTK_GRID (entry), 2);

  gimp_size_entry_attach_label (GIMP_SIZE_ENTRY (entry),
                                _("Horizontal"), 0, 1, 0.0);
  gimp_size_entry_attach_label (GIMP_SIZE_ENTRY (entry),
                                _("Vertical"), 0, 2, 0.0);
  gimp_size_entry_attach_label (GIMP_SIZE_ENTRY (entry),
                                _("ppi"), 1, 4, 0.0);

  hbox = gtk_box_new (GTK_ORIENTATION_HORIZONTAL, 0);
  gtk_widget_set_halign (hbox, GTK_ALIGN_START);

  gtk_box_pack_start (GTK_BOX (hbox), entry, FALSE, FALSE, 24);
  gtk_widget_set_sensitive (entry, ! display_config->monitor_res_from_gdk);

  group = NULL;

  {
    gdouble  xres;
    gdouble  yres;
    gchar   *str;

    gimp_get_monitor_resolution (gdk_display_get_monitor (gdk_display_get_default (), 0),
                                 &xres, &yres);

    str = g_strdup_printf (_("_Detect automatically (currently %d × %d ppi)"),
                           ROUND (xres), ROUND (yres));

    button = gtk_radio_button_new_with_mnemonic (group, str);

    g_free (str);
  }

  group = gtk_radio_button_get_group (GTK_RADIO_BUTTON (button));
  gtk_box_pack_start (GTK_BOX (vbox2), button, FALSE, FALSE, 0);
  gtk_widget_set_visible (button, TRUE);

  g_object_set_data (G_OBJECT (button), "monitor_resolution_sizeentry", entry);

  g_signal_connect (button, "toggled",
                    G_CALLBACK (prefs_resolution_source_callback),
                    config);

  button = gtk_radio_button_new_with_mnemonic (group, _("_Enter manually"));
  group = gtk_radio_button_get_group (GTK_RADIO_BUTTON (button));
  gtk_box_pack_start (GTK_BOX (vbox2), button, FALSE, FALSE, 0);
  gtk_widget_set_visible (button, TRUE);

  gtk_box_pack_start (GTK_BOX (vbox2), hbox, FALSE, FALSE, 0);
  gtk_widget_set_visible (hbox, TRUE);

  if (! display_config->monitor_res_from_gdk)
    gtk_toggle_button_set_active (GTK_TOGGLE_BUTTON (button), TRUE);

  hbox = gtk_box_new (GTK_ORIENTATION_HORIZONTAL, 0);
  gtk_box_pack_start (GTK_BOX (vbox2), hbox, FALSE, FALSE, 0);
  gtk_widget_set_visible (hbox, TRUE);

  calibrate_button = gtk_button_new_with_mnemonic (_("C_alibrate..."));
  label = gtk_bin_get_child (GTK_BIN (calibrate_button));
  g_object_set (label,
                "margin-start", 4,
                "margin-end",   4,
                NULL);
  gtk_box_pack_start (GTK_BOX (hbox), calibrate_button, FALSE, FALSE, 0);
  gtk_widget_set_visible (calibrate_button, TRUE);
  gtk_widget_set_sensitive (calibrate_button,
                            ! display_config->monitor_res_from_gdk);

  g_object_bind_property (button, "active",
                          entry,  "sensitive",
                          G_BINDING_SYNC_CREATE);
  g_object_bind_property (button,           "active",
                          calibrate_button, "sensitive",
                          G_BINDING_SYNC_CREATE);

  g_signal_connect (calibrate_button, "clicked",
                    G_CALLBACK (prefs_resolution_calibrate_callback),
                    entry);

  g_clear_object (&size_group);


  /***********************************/
  /*  Interface / Window Management  */
  /***********************************/
  vbox = gimp_prefs_box_add_page (GIMP_PREFS_BOX (prefs_box),
                                  "ammoos-prefs-window-management",
                                  _("Window Management"),
                                  _("Window Management"),
                                  GIMP_HELP_PREFS_WINDOW_MANAGEMENT,
                                  &top_iter,
                                  &child_iter);

  vbox2 = prefs_frame_new (_("Window Manager Hints"),
                           GTK_CONTAINER (vbox), FALSE);

  grid = prefs_grid_new (GTK_CONTAINER (vbox2));

  prefs_enum_combo_box_add (object, "dock-window-hint", 0, 0,
                            _("Hint for _docks and toolbox:"),
                            GTK_GRID (grid), 1, NULL);

  vbox2 = prefs_frame_new (_("Focus"),
                           GTK_CONTAINER (vbox), FALSE);

  prefs_check_button_add (object, "activate-on-focus",
                          _("Activate the _focused image"),
                          GTK_BOX (vbox2));

  /* Window Positions */
  vbox2 = prefs_frame_new (_("Window Positions"), GTK_CONTAINER (vbox), FALSE);

  prefs_check_button_add (object, "save-session-info",
                          _("_Save window positions on exit"),
                          GTK_BOX (vbox2));
  prefs_check_button_add (object, "restore-monitor",
                          _("Open windows on the same _monitor they were open before"),
                          GTK_BOX (vbox2));

  button = prefs_button_add (GIMP_ICON_DOCUMENT_SAVE,
                             _("Save Window Positions _Now"),
                             GTK_BOX (vbox2));
  g_signal_connect (button, "clicked",
                    G_CALLBACK (prefs_session_save_callback),
                    ammoos);

  button2 = prefs_button_add (GIMP_ICON_RESET,
                              _("_Reset Saved Window Positions to "
                                "Default Values"),
                              GTK_BOX (vbox2));
  g_signal_connect (button2, "clicked",
                    G_CALLBACK (prefs_session_clear_callback),
                    ammoos);

  g_object_set_data (G_OBJECT (button), "clear-button", button2);


  /************************/
  /*  Canvas Interaction  */
  /************************/
  vbox = gimp_prefs_box_add_page (GIMP_PREFS_BOX (prefs_box),
                                  "ammoos-prefs-image-windows",
                                  _("Canvas Interaction"),
                                  _("Canvas Interaction"),
                                  GIMP_HELP_PREFS_CANVAS_INTERACTION,
                                  NULL,
                                  &top_iter);
  gimp_prefs_box_set_page_scrollable (GIMP_PREFS_BOX (prefs_box), vbox, TRUE);

  size_group = gtk_size_group_new (GTK_SIZE_GROUP_HORIZONTAL);

  /*  Space Bar  */
  vbox2 = prefs_frame_new (_("Space Bar"),
                           GTK_CONTAINER (vbox), FALSE);

  grid = prefs_grid_new (GTK_CONTAINER (vbox2));

  prefs_enum_combo_box_add (object, "space-bar-action", 0, 0,
                            _("_While space bar is pressed:"),
                            GTK_GRID (grid), 0, size_group);

  /*  Zoom by drag Behavior  */
  vbox2 = prefs_frame_new (_("Zoom"),
                           GTK_CONTAINER (vbox), FALSE);

  grid = prefs_grid_new (GTK_CONTAINER (vbox2));

  prefs_enum_combo_box_add (object, "drag-zoom-mode", 0, 0,
                            _("Dra_g-to-zoom behavior:"),
                            GTK_GRID (grid), 0, size_group);

  grid = prefs_grid_new (GTK_CONTAINER (vbox2));

  prefs_spin_button_add (object, "drag-zoom-speed", 5.0, 25.0, 0,
                         _("Drag-to-zoom spe_ed:"),
                         GTK_GRID (grid), 0, size_group);


  /************************************/
  /*  Canvas Interaction / Modifiers  */
  /************************************/
  vbox = gimp_prefs_box_add_page (GIMP_PREFS_BOX (prefs_box),
                                  /* TODO: custom icon. */
                                  "ammoos-prefs-image-windows",
                                  _("Modifiers"),
                                  _("Modifiers"),
                                  GIMP_HELP_PREFS_CANVAS_MODIFIERS,
                                  &top_iter,
                                  &child_iter);

  vbox2 = gimp_modifiers_editor_new (GIMP_MODIFIERS_MANAGER (display_config->modifiers_manager),
                                     ammoos);
  gtk_widget_set_visible (vbox2, TRUE);
  gtk_box_pack_start (GTK_BOX (vbox), vbox2, FALSE, FALSE, 0);

  button2 = prefs_button_add (GIMP_ICON_RESET,
                              _("_Reset Saved Modifiers Settings to "
                                "Default Values"),
                              GTK_BOX (vbox));
  g_signal_connect (button2, "clicked",
                    G_CALLBACK (prefs_modifiers_clear_callback),
                    vbox2);

  g_object_set_data (G_OBJECT (button), "clear-button", button2);

  /***********************************/
  /*  Canvas Interaction / Snapping  */
  /***********************************/
  vbox = gimp_prefs_box_add_page (GIMP_PREFS_BOX (prefs_box),
                                  "ammoos-prefs-image-windows-snapping",
                                  _("Snapping Behavior"),
                                  _("Snapping"),
                                  GIMP_HELP_PREFS_IMAGE_WINDOW_SNAPPING,
                                  &top_iter,
                                  &child_iter);

  prefs_behavior_options_frame_add (ammoos,
                                    G_OBJECT (display_config->default_view),
                                    _("Default Behavior in Normal Mode"),
                                    GTK_CONTAINER (vbox));
  prefs_behavior_options_frame_add (ammoos,
                                    G_OBJECT (display_config->default_fullscreen_view),
                                    _("Default Behavior in Fullscreen Mode"),
                                    GTK_CONTAINER (vbox));

  /*  Snapping Distance  */
  vbox2 = prefs_frame_new (_("General"),
                           GTK_CONTAINER (vbox), FALSE);
  grid = prefs_grid_new (GTK_CONTAINER (vbox2));

  prefs_spin_button_add (object, "snap-distance", 1.0, 5.0, 0,
                         _("_Snapping distance:"),
                         GTK_GRID (grid), 0, NULL);


  /*******************/
  /*  Image Windows  */
  /*******************/
  vbox = gimp_prefs_box_add_page (GIMP_PREFS_BOX (prefs_box),
                                  "ammoos-prefs-image-windows",
                                  _("Image Windows"),
                                  _("Image Windows"),
                                  GIMP_HELP_PREFS_IMAGE_WINDOW,
                                  NULL,
                                  &top_iter);
  gimp_prefs_box_set_page_scrollable (GIMP_PREFS_BOX (prefs_box), vbox, TRUE);

  size_group = gtk_size_group_new (GTK_SIZE_GROUP_HORIZONTAL);

  /*  General  */
  vbox2 = prefs_frame_new (_("General"), GTK_CONTAINER (vbox), FALSE);

  /* See app/display/gimpimagewindow.c: the code path where "custom-title-bar"
   * is verified never happens for macOS which always uses
   * gtk_application_set_menubar() instead.
   */
#ifndef GDK_WINDOWING_QUARTZ
  prefs_check_button_add (object, "custom-title-bar",
                          _("Merge menu and title bar"),
                          GTK_BOX (vbox2));
  hbox = prefs_hint_box_new (GIMP_ICON_DIALOG_WARNING,
                             _("AmmoOS Image will try to convince your system not to decorate image windows. "
                               "If it doesn't work properly on your system "
                               "(i.e. you get 2 title bars), please report."));
  gtk_box_pack_start (GTK_BOX (vbox2), hbox, FALSE, FALSE, 0);
  g_object_bind_property (object, "custom-title-bar",
                          hbox,   "visible",
                          G_BINDING_SYNC_CREATE);
#endif

  prefs_check_button_add (object, "default-show-all",
                          _("Use \"Show _all\" by default"),
                          GTK_BOX (vbox2));

  prefs_check_button_add (object, "default-dot-for-dot",
                          _("Use \"_Dot for dot\" by default"),
                          GTK_BOX (vbox2));

  grid = prefs_grid_new (GTK_CONTAINER (vbox2));

  prefs_spin_button_add (object, "marching-ants-speed", 1.0, 10.0, 0,
                         _("Marching ants s_peed:"),
                         GTK_GRID (grid), 0, size_group);

  /*  Zoom & Resize Behavior  */
  vbox2 = prefs_frame_new (_("Zoom & Resize Behavior"),
                           GTK_CONTAINER (vbox), FALSE);

  prefs_check_button_add (object, "resize-windows-on-zoom",
                          _("Resize window on _zoom"),
                          GTK_BOX (vbox2));
  prefs_check_button_add (object, "resize-windows-on-resize",
                          _("Resize window on image _size change"),
                          GTK_BOX (vbox2));

  grid = prefs_grid_new (GTK_CONTAINER (vbox2));

prefs_boolean_combo_box_add (object, "initial-zoom-to-fit",
                               _("Show entire image"),
                               "1:1",
                               _("Initial zoom _ratio:"),
                               GTK_GRID (grid), 0, size_group);

  /********************************/
  /*  Image Windows / Appearance  */
  /********************************/
  vbox = gimp_prefs_box_add_page (GIMP_PREFS_BOX (prefs_box),
                                  "ammoos-prefs-image-windows-appearance",
                                  _("Image Window Appearance"),
                                  _("Appearance"),
                                  GIMP_HELP_PREFS_IMAGE_WINDOW_APPEARANCE,
                                  &top_iter,
                                  &child_iter);

  gimp_prefs_box_set_page_scrollable (GIMP_PREFS_BOX (prefs_box), vbox, TRUE);

  prefs_display_options_frame_add (ammoos,
                                   G_OBJECT (display_config->default_view),
                                   _("Default Appearance in Normal Mode"),
                                   GTK_CONTAINER (vbox));

  prefs_display_options_frame_add (ammoos,
                                   G_OBJECT (display_config->default_fullscreen_view),
                                   _("Default Appearance in Fullscreen Mode"),
                                   GTK_CONTAINER (vbox));


  /****************************************************/
  /*  Image Windows / Image Title & Statusbar Format  */
  /****************************************************/
  vbox = gimp_prefs_box_add_page (GIMP_PREFS_BOX (prefs_box),
                                  "ammoos-prefs-image-title",
                                  _("Image Title & Statusbar Format"),
                                  _("Title & Status"),
                                  GIMP_HELP_PREFS_IMAGE_WINDOW_TITLE,
                                  &top_iter,
                                  &child_iter);

  {
    const gchar *format_strings[] =
    {
      NULL,
      NULL,
      "%f-%p.%i (%t) %z%%",
      "%f-%p.%i (%t) %d:%s",
      "%f-%p.%i (%t) %wx%h",
      "%f-%p-%i (%t) %wx%h (%xx%y)"
    };

    const gchar *format_names[] =
    {
      N_("Current format"),
      N_("Default format"),
      N_("Show zoom percentage"),
      N_("Show zoom ratio"),
      N_("Show image size"),
      N_("Show drawable size")
    };

    struct
    {
      gchar       *current_setting;
      const gchar *default_setting;
      const gchar *title;
      const gchar *property_name;
    }
    formats[] =
    {
      { NULL, GIMP_CONFIG_DEFAULT_IMAGE_TITLE_FORMAT,
        N_("Image Title Format"),     "image-title-format"  },
      { NULL, GIMP_CONFIG_DEFAULT_IMAGE_STATUS_FORMAT,
        N_("Image Statusbar Format"), "image-status-format" }
    };

    gint format;

    gimp_assert (G_N_ELEMENTS (format_strings) == G_N_ELEMENTS (format_names));

    formats[0].current_setting = display_config->image_title_format;
    formats[1].current_setting = display_config->image_status_format;

    for (format = 0; format < G_N_ELEMENTS (formats); format++)
      {
        GtkWidget     *scrolled_win;
        GtkWidget     *listbox;
        GtkSizeGroup  *name_group, *format_group;
        gint           i;

        format_strings[0] = formats[format].current_setting;
        format_strings[1] = formats[format].default_setting;

        vbox2 = prefs_frame_new (gettext (formats[format].title),
                                 GTK_CONTAINER (vbox), TRUE);

        entry = gimp_prop_entry_new (object, formats[format].property_name, 0);
        gtk_box_pack_start (GTK_BOX (vbox2), entry, FALSE, FALSE, 0);

        scrolled_win = gtk_scrolled_window_new (NULL, NULL);
        gtk_scrolled_window_set_shadow_type (GTK_SCROLLED_WINDOW (scrolled_win),
                                             GTK_SHADOW_IN);
        gtk_scrolled_window_set_policy (GTK_SCROLLED_WINDOW (scrolled_win),
                                        GTK_POLICY_AUTOMATIC,
                                        GTK_POLICY_AUTOMATIC);
        gtk_box_pack_start (GTK_BOX (vbox2), scrolled_win, TRUE, TRUE, 0);
        gtk_widget_set_visible (scrolled_win, TRUE);

        listbox = gtk_list_box_new ();
        gtk_list_box_set_selection_mode (GTK_LIST_BOX (listbox),
                                         GTK_SELECTION_BROWSE);
        gtk_style_context_add_class (gtk_widget_get_style_context (GTK_WIDGET (listbox)),
                                     "view");
        gtk_container_add (GTK_CONTAINER (scrolled_win), listbox);
        gtk_widget_set_visible (listbox, TRUE);

        name_group = gtk_size_group_new (GTK_SIZE_GROUP_HORIZONTAL);
        format_group = gtk_size_group_new (GTK_SIZE_GROUP_HORIZONTAL);

        for (i = 0; i < G_N_ELEMENTS (format_strings); i++)
          {
            GtkWidget *row;
            GtkWidget *grid;
            GtkWidget *name_label, *format_label;

            row = gtk_list_box_row_new ();
            g_object_set_data_full (G_OBJECT (row),
                                    "format",
                                    g_strdup (format_strings[i]),
                                    g_free);

            grid = gtk_grid_new ();
            gtk_grid_set_column_spacing (GTK_GRID (grid), 6);
            gtk_container_add (GTK_CONTAINER (row), grid);

            name_label = gtk_label_new (gettext (format_names[i]));
            g_object_set (name_label, "xalign", 0.0, "margin", 3, NULL);
            gtk_size_group_add_widget (name_group, name_label);
            gtk_grid_attach (GTK_GRID (grid), name_label, 0, 0, 1, 1);

            format_label = gtk_label_new (format_strings[i]);
            g_object_set (format_label, "xalign", 0.0, "margin", 3, NULL);
            gtk_size_group_add_widget (format_group, format_label);
            gtk_grid_attach (GTK_GRID (grid), format_label, 1, 0, 1, 1);

            gtk_widget_show_all (row);
            gtk_list_box_insert (GTK_LIST_BOX (listbox), row, -1);

            if (i == 0)
              {
                gtk_list_box_select_row (GTK_LIST_BOX (listbox),
                                         GTK_LIST_BOX_ROW (row));
              }
          }
        g_object_unref (name_group);
        g_object_unref (format_group);

        g_signal_connect (listbox, "row-selected",
                          G_CALLBACK (prefs_format_string_select_callback),
                          entry);
      }
  }


  /*******************/
  /*  Input Devices  */
  /*******************/
  vbox = gimp_prefs_box_add_page (GIMP_PREFS_BOX (prefs_box),
                                  "ammoos-prefs-input-devices",
                                  _("Input Devices"),
                                  _("Input Devices"),
                                  GIMP_HELP_PREFS_INPUT_DEVICES,
                                  NULL,
                                  &top_iter);

  /*  Mouse Pointers  */
  hbox = gtk_box_new (GTK_ORIENTATION_HORIZONTAL, 10);
  gtk_widget_set_halign (hbox, GTK_ALIGN_START);
  gtk_box_pack_start (GTK_BOX (vbox), hbox, FALSE, FALSE, 0);
  gtk_widget_set_visible (hbox, TRUE);

  vbox2 = prefs_frame_new (_("Pointers"),
                           GTK_CONTAINER (hbox), FALSE);

  grid = prefs_grid_new (GTK_CONTAINER (vbox2));

  size_group = gtk_size_group_new (GTK_SIZE_GROUP_HORIZONTAL);
  prefs_enum_combo_box_add (object, "cursor-mode", 0, 0,
                            _("Pointer _mode:"),
                            GTK_GRID (grid), 0, size_group);
  prefs_enum_combo_box_add (object, "cursor-handedness", 0, 0,
                            _("Pointer _handedness:"),
                            GTK_GRID (grid), 1, size_group);
  g_clear_object (&size_group);

  vbox2 = prefs_frame_new (_("Paint Tools"),
                           GTK_CONTAINER (hbox), FALSE);

  button = prefs_check_button_add (object, "show-brush-outline",
                                   _("Show _brush outline"),
                                   GTK_BOX (vbox2));

  vbox3 = prefs_frame_new (NULL, GTK_CONTAINER (vbox2), FALSE);
  g_object_bind_property (button, "active",
                          vbox3,  "sensitive",
                          G_BINDING_SYNC_CREATE);
  prefs_check_button_add (object, "snap-brush-outline",
                          _("S_nap brush outline to stroke"),
                          GTK_BOX (vbox3));

  prefs_check_button_add (object, "show-paint-tool-cursor",
                          _("Show pointer for paint _tools"),
                          GTK_BOX (vbox2));

  /*  Extended Input Devices  */
  vbox2 = prefs_frame_new (_("Extended Input Devices"),
                           GTK_CONTAINER (vbox), FALSE);

#ifdef G_OS_WIN32

  if ((gtk_get_major_version () == 3 &&
       gtk_get_minor_version () > 24) ||
      (gtk_get_major_version () == 3 &&
       gtk_get_minor_version () == 24 &&
       gtk_get_micro_version () >= 30))
    {
      GtkWidget *combo;

      grid = prefs_grid_new (GTK_CONTAINER (vbox2));

      combo = prefs_enum_combo_box_add (object, "win32-pointer-input-api", 0, 0,
                                        _("Pointer Input API:"),
                                        GTK_GRID (grid), 0, NULL);

      gimp_int_combo_box_set_sensitivity (GIMP_INT_COMBO_BOX (combo),
                                          prefs_devices_api_sensitivity_func,
                                          NULL, NULL);
    }

#endif

  prefs_check_button_add (object, "devices-share-tool",
                          _("S_hare tool and tool options between input devices"),
                          GTK_BOX (vbox2));

  button = prefs_button_add (GIMP_ICON_PREFERENCES_SYSTEM,
                             _("Configure E_xtended Input Devices..."),
                             GTK_BOX (vbox2));
  g_signal_connect (button, "clicked",
                    G_CALLBACK (prefs_input_devices_dialog),
                    ammoos);

  prefs_check_button_add (object, "save-device-status",
                          _("_Save input device settings on exit"),
                          GTK_BOX (vbox2));

  button = prefs_button_add (GIMP_ICON_DOCUMENT_SAVE,
                             _("Save Input Device Settings _Now"),
                             GTK_BOX (vbox2));
  g_signal_connect (button, "clicked",
                    G_CALLBACK (prefs_devices_save_callback),
                    ammoos);

  button2 = prefs_button_add (GIMP_ICON_RESET,
                              _("_Reset Saved Input Device Settings to "
                                "Default Values"),
                              GTK_BOX (vbox2));
  g_signal_connect (button2, "clicked",
                    G_CALLBACK (prefs_devices_clear_callback),
                    ammoos);

  g_object_set_data (G_OBJECT (button), "clear-button", button2);


  /****************************/
  /*  Additional Controllers  */
  /****************************/
  vbox = gimp_prefs_box_add_page (GIMP_PREFS_BOX (prefs_box),
                                  "ammoos-prefs-controllers",
                                  _("Additional Input Controllers"),
                                  _("Input Controllers"),
                                  GIMP_HELP_PREFS_INPUT_CONTROLLERS,
                                  &top_iter,
                                  &child_iter);

  vbox2 = gimp_controller_list_new (gimp_get_controller_manager (ammoos));
  gtk_box_pack_start (GTK_BOX (vbox), vbox2, TRUE, TRUE, 0);
  gtk_widget_set_visible (vbox2, TRUE);


  /*************/
  /*  Folders  */
  /*************/
  vbox = gimp_prefs_box_add_page (GIMP_PREFS_BOX (prefs_box),
                                  "ammoos-prefs-folders",
                                  _("Folders"),
                                  _("Folders"),
                                  GIMP_HELP_PREFS_FOLDERS,
                                  NULL,
                                  &top_iter);

  button = gimp_prefs_box_set_page_resettable (GIMP_PREFS_BOX (prefs_box),
                                               vbox,
                                               _("Reset _Folders"));
  g_signal_connect (button, "clicked",
                    G_CALLBACK (prefs_folders_reset),
                    config);

  {
    static const struct
    {
      const gchar *property_name;
      const gchar *label;
      const gchar *dialog_title;
    }
    dirs[] =
    {
      {
        "temp-path",
        N_("_Temporary folder:"),
        N_("Select Folder for Temporary Files")
      },
      {
        "swap-path",
        N_("_Swap folder:"),
        N_("Select Swap Folder")
      }
    };

    grid = prefs_grid_new (GTK_CONTAINER (vbox));

    for (i = 0; i < G_N_ELEMENTS (dirs); i++)
      {
        prefs_file_chooser_button_add (object, dirs[i].property_name,
                                       gettext (dirs[i].label),
                                       gettext (dirs[i].dialog_title),
                                       GTK_GRID (grid), i, NULL);
      }
  }


  /*********************/
  /* Folders / <paths> */
  /*********************/
  {
    static const struct
    {
      const gchar *tree_label;
      const gchar *label;
      const gchar *icon;
      const gchar *help_data;
      const gchar *reset_label;
      const gchar *fs_label;
      const gchar *path_property_name;
      const gchar *writable_property_name;
    }
    paths[] =
    {
      { N_("Brushes"), N_("Brush Folders"),
        "folders-brushes",
        GIMP_HELP_PREFS_FOLDERS_BRUSHES,
        N_("Reset Brush _Folders"),
        N_("Select Brush Folders"),
        "brush-path", "brush-path-writable" },
      { N_("Dynamics"), N_("Dynamics Folders"),
        "folders-dynamics",
        GIMP_HELP_PREFS_FOLDERS_DYNAMICS,
        N_("Reset Dynamics _Folders"),
        N_("Select Dynamics Folders"),
        "dynamics-path", "dynamics-path-writable" },
      { N_("Patterns"), N_("Pattern Folders"),
        "folders-patterns",
        GIMP_HELP_PREFS_FOLDERS_PATTERNS,
        N_("Reset Pattern _Folders"),
        N_("Select Pattern Folders"),
        "pattern-path", "pattern-path-writable" },
      { N_("Palettes"), N_("Palette Folders"),
        "folders-palettes",
        GIMP_HELP_PREFS_FOLDERS_PALETTES,
        N_("Reset Palette _Folders"),
        N_("Select Palette Folders"),
        "palette-path", "palette-path-writable" },
      { N_("Gradients"), N_("Gradient Folders"),
        "folders-gradients",
        GIMP_HELP_PREFS_FOLDERS_GRADIENTS,
        N_("Reset Gradient _Folders"),
        N_("Select Gradient Folders"),
        "gradient-path", "gradient-path-writable" },
      { N_("Fonts"), N_("Font Folders"),
        "folders-fonts",
        GIMP_HELP_PREFS_FOLDERS_FONTS,
        N_("Reset Font _Folders"),
        N_("Select Font Folders"),
        "font-path", NULL },
      { N_("Tool Presets"), N_("Tool Preset Folders"),
        "folders-tool-presets",
        GIMP_HELP_PREFS_FOLDERS_TOOL_PRESETS,
        N_("Reset Tool Preset _Folders"),
        N_("Select Tool Preset Folders"),
        "tool-preset-path", "tool-preset-path-writable" },
      { N_("MyPaint Brushes"), N_("MyPaint Brush Folders"),
        "folders-mypaint-brushes",
        GIMP_HELP_PREFS_FOLDERS_MYPAINT_BRUSHES,
        N_("Reset MyPaint Brush _Folders"),
        N_("Select MyPaint Brush Folders"),
        "mypaint-brush-path", "mypaint-brush-path-writable" },
      { N_("Plug-ins"), N_("Plug-in Folders"),
        "folders-plug-ins",
        GIMP_HELP_PREFS_FOLDERS_PLUG_INS,
        N_("Reset plug-in _Folders"),
        N_("Select plug-in Folders"),
        "plug-in-path", NULL },
      { N_("Scripts"), N_("Script-Fu Folders"),
        "folders-scripts",
        GIMP_HELP_PREFS_FOLDERS_SCRIPTS,
        N_("Reset Script-Fu _Folders"),
        N_("Select Script-Fu Folders"),
        "script-fu-path", NULL },
      { N_("Modules"), N_("Module Folders"),
        "folders-modules",
        GIMP_HELP_PREFS_FOLDERS_MODULES,
        N_("Reset Module _Folders"),
        N_("Select Module Folders"),
        "module-path", NULL },
      { N_("Interpreters"), N_("Interpreter Folders"),
        "folders-interp",
        GIMP_HELP_PREFS_FOLDERS_INTERPRETERS,
        N_("Reset Interpreter _Folders"),
        N_("Select Interpreter Folders"),
        "interpreter-path", NULL },
      { N_("Environment"), N_("Environment Folders"),
        "folders-environ",
        GIMP_HELP_PREFS_FOLDERS_ENVIRONMENT,
        N_("Reset Environment _Folders"),
        N_("Select Environment Folders"),
        "environ-path", NULL },
      { N_("Themes"), N_("Theme Folders"),
        "folders-themes",
        GIMP_HELP_PREFS_FOLDERS_THEMES,
        N_("Reset Theme _Folders"),
        N_("Select Theme Folders"),
        "theme-path", NULL },
      { N_("Icon Themes"), N_("Icon Theme Folders"),
        "folders-icon-themes",
        GIMP_HELP_PREFS_FOLDERS_ICON_THEMES,
        N_("Reset Icon Theme _Folders"),
        N_("Select Icon Theme Folders"),
        "icon-theme-path", NULL }
    };

    for (i = 0; i < G_N_ELEMENTS (paths); i++)
      {
        GtkWidget *editor;
        gchar     *icon_name;

        icon_name = g_strconcat ("ammoos-prefs-", paths[i].icon, NULL);
        vbox = gimp_prefs_box_add_page (GIMP_PREFS_BOX (prefs_box),
                                        icon_name,
                                        gettext (paths[i].label),
                                        gettext (paths[i].tree_label),
                                        paths[i].help_data,
                                        &top_iter,
                                        &child_iter);
        g_free (icon_name);

        button = gimp_prefs_box_set_page_resettable (GIMP_PREFS_BOX (prefs_box),
                                                     vbox,
                                                     gettext (paths[i].reset_label));
        g_object_set_data (G_OBJECT (button), "path",
                           (gpointer) paths[i].path_property_name);
        g_object_set_data (G_OBJECT (button), "path-writable",
                           (gpointer) paths[i].writable_property_name);
        g_signal_connect (button, "clicked",
                          G_CALLBACK (prefs_path_reset),
                          config);

        editor = gimp_prop_path_editor_new (object,
                                            paths[i].path_property_name,
                                            paths[i].writable_property_name,
                                            gettext (paths[i].fs_label));
        gtk_box_pack_start (GTK_BOX (vbox), editor, TRUE, TRUE, 0);
      }
  }

  {
    GtkWidget *tv;

    /* Expand all folders in the tree view by default. */
    tv = gimp_prefs_box_get_tree_view (GIMP_PREFS_BOX (prefs_box));
    gtk_tree_view_expand_all (GTK_TREE_VIEW (tv));

  }

  return dialog;
}

/* --- print-size-dialog.c --- */
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

#include "libgimpbase/gimpbase.h"
#include "libgimpwidgets/gimpwidgets.h"

#include "dialogs-types.h"

#include "core/gimpcontext.h"
#include "core/gimpimage.h"
#include "core/ammoos-utils.h"

#include "widgets/gimphelp-ids.h"
#include "widgets/gimpviewabledialog.h"

#include "print-size-dialog.h"

#include "ammoos-intl.h"


#define RESPONSE_RESET 1
#define SB_WIDTH       8


typedef struct _PrintSizeDialog PrintSizeDialog;

struct _PrintSizeDialog
{
  GimpImage              *image;
  GimpSizeEntry          *size_entry;
  GimpSizeEntry          *resolution_entry;
  GimpChainButton        *chain;
  gdouble                 xres;
  gdouble                 yres;
  GimpResolutionCallback  callback;
  gpointer                user_data;
};


/*  local function prototypes  */

static void   print_size_dialog_free               (PrintSizeDialog *private);
static void   print_size_dialog_response           (GtkWidget       *dialog,
                                                    gint             response_id,
                                                    PrintSizeDialog *private);
static void   print_size_dialog_reset              (PrintSizeDialog *private);

static void   print_size_dialog_size_changed       (GtkWidget       *widget,
                                                    PrintSizeDialog *private);
static void   print_size_dialog_resolution_changed (GtkWidget       *widget,
                                                    PrintSizeDialog *private);
static void   print_size_dialog_set_size           (PrintSizeDialog *private,
                                                    gdouble          width,
                                                    gdouble          height);
static void   print_size_dialog_set_resolution     (PrintSizeDialog *private,
                                                    gdouble          xres,
                                                    gdouble          yres);


/*  public functions  */

GtkWidget *
print_size_dialog_new (GimpImage              *image,
                       GimpContext            *context,
                       const gchar            *title,
                       const gchar            *role,
                       GtkWidget              *parent,
                       GimpHelpFunc            help_func,
                       const gchar            *help_id,
                       GimpResolutionCallback  callback,
                       gpointer                user_data)
{
  PrintSizeDialog *private;
  GtkWidget       *dialog;
  GtkWidget       *frame;
  GtkWidget       *grid;
  GtkWidget       *entry;
  GtkWidget       *label;
  GtkWidget       *width;
  GtkWidget       *height;
  GtkWidget       *hbox;
  GtkWidget       *chain;
  GtkAdjustment   *adj;

  g_return_val_if_fail (GIMP_IS_IMAGE (image), NULL);
  g_return_val_if_fail (GIMP_IS_CONTEXT (context), NULL);
  g_return_val_if_fail (callback != NULL, NULL);

  private = g_slice_new0 (PrintSizeDialog);

  private->image     = image;
  private->callback  = callback;
  private->user_data = user_data;

  gimp_image_get_resolution (image, &private->xres, &private->yres);

  dialog = gimp_viewable_dialog_new (g_list_prepend (NULL, image), context,
                                     title, role,
                                     GIMP_ICON_DOCUMENT_PRINT_RESOLUTION, title,
                                     parent,
                                     help_func, help_id,

                                     _("_Reset"),  RESPONSE_RESET,
                                     _("_Cancel"), GTK_RESPONSE_CANCEL,
                                     _("_OK"),     GTK_RESPONSE_OK,

                                     NULL);

  gimp_dialog_set_alternative_button_order (GTK_DIALOG (dialog),
                                           RESPONSE_RESET,
                                           GTK_RESPONSE_OK,
                                           GTK_RESPONSE_CANCEL,
                                           -1);

  gtk_window_set_resizable (GTK_WINDOW (dialog), FALSE);

  g_object_weak_ref (G_OBJECT (dialog),
                     (GWeakNotify) print_size_dialog_free, private);

  g_signal_connect (dialog, "response",
                    G_CALLBACK (print_size_dialog_response),
                    private);

  frame = gimp_frame_new (_("Print Size"));
  gtk_container_set_border_width (GTK_CONTAINER (frame), 12);
  gtk_box_pack_start (GTK_BOX (gtk_dialog_get_content_area (GTK_DIALOG (dialog))),
                      frame, FALSE, FALSE, 0);
  gtk_widget_set_visible (frame, TRUE);

  grid = gtk_grid_new ();
  gtk_grid_set_row_spacing (GTK_GRID (grid), 12);
  gtk_container_add (GTK_CONTAINER (frame), grid);
  gtk_widget_set_visible (grid, TRUE);

  /*  the print size entry  */

  adj = gtk_adjustment_new (1, 1, 1, 1, 10, 0);
  width = gimp_spin_button_new (adj, 1.0, 2);
  gtk_spin_button_set_numeric (GTK_SPIN_BUTTON (width), TRUE);
  gtk_entry_set_width_chars (GTK_ENTRY (width), SB_WIDTH);

  adj = gtk_adjustment_new (1, 1, 1, 1, 10, 0);
  height = gimp_spin_button_new (adj, 1.0, 2);
  gtk_spin_button_set_numeric (GTK_SPIN_BUTTON (height), TRUE);
  gtk_entry_set_width_chars (GTK_ENTRY (height), SB_WIDTH);

  entry = gimp_size_entry_new (0, gimp_get_default_unit (), "%n",
                               FALSE, FALSE, FALSE, SB_WIDTH,
                               GIMP_SIZE_ENTRY_UPDATE_SIZE);
  private->size_entry = GIMP_SIZE_ENTRY (entry);

  label = gtk_label_new_with_mnemonic (_("_Width:"));
  gtk_label_set_xalign (GTK_LABEL (label), 0.0);
  gtk_label_set_mnemonic_widget (GTK_LABEL (label), width);
  gtk_grid_attach (GTK_GRID (grid), label, 0, 0, 1, 1);
  gtk_widget_set_visible (label, TRUE);

  label = gtk_label_new_with_mnemonic (_("H_eight:"));
  gtk_label_set_xalign (GTK_LABEL (label), 0.0);
  gtk_label_set_mnemonic_widget (GTK_LABEL (label), height);
  gtk_grid_attach (GTK_GRID (grid), label, 0, 1, 1, 1);
  gtk_widget_set_visible (label, TRUE);

  hbox = gtk_box_new (GTK_ORIENTATION_HORIZONTAL, 0);
  gtk_grid_attach (GTK_GRID (grid), hbox, 1, 0, 1, 2);
  gtk_widget_set_visible (hbox, TRUE);

  gtk_box_pack_start (GTK_BOX (hbox), entry, FALSE, FALSE, 0);
  gtk_widget_set_visible (entry, TRUE);

  gimp_size_entry_add_field (GIMP_SIZE_ENTRY (entry),
                             GTK_SPIN_BUTTON (height), NULL);
  gtk_grid_attach (GTK_GRID (entry), height, 0, 1, 1, 1);
  gtk_widget_set_visible (height, TRUE);

  gimp_size_entry_add_field (GIMP_SIZE_ENTRY (entry),
                             GTK_SPIN_BUTTON (width), NULL);
  gtk_grid_attach (GTK_GRID (entry), width, 0, 0, 1, 1);
  gtk_widget_set_visible (width, TRUE);

  gimp_size_entry_set_resolution (GIMP_SIZE_ENTRY (entry), 0,
                                  private->xres, FALSE);
  gimp_size_entry_set_resolution (GIMP_SIZE_ENTRY (entry), 1,
                                  private->yres, FALSE);

  gimp_size_entry_set_refval_boundaries
    (GIMP_SIZE_ENTRY (entry), 0, GIMP_MIN_IMAGE_SIZE, GIMP_MAX_IMAGE_SIZE);
  gimp_size_entry_set_refval_boundaries
    (GIMP_SIZE_ENTRY (entry), 1, GIMP_MIN_IMAGE_SIZE, GIMP_MAX_IMAGE_SIZE);

  gimp_size_entry_set_refval (GIMP_SIZE_ENTRY (entry), 0,
                              gimp_image_get_width  (image));
  gimp_size_entry_set_refval (GIMP_SIZE_ENTRY (entry), 1,
                              gimp_image_get_height (image));

  /*  the resolution entry  */

  adj = gtk_adjustment_new (1, 1, 1, 1, 10, 0);
  width = gimp_spin_button_new (adj, 1.0, 2);
  gtk_spin_button_set_numeric (GTK_SPIN_BUTTON (width), TRUE);
  gtk_entry_set_width_chars (GTK_ENTRY (width), SB_WIDTH);

  adj = gtk_adjustment_new (1, 1, 1, 1, 10, 0);
  height = gimp_spin_button_new (adj, 1.0, 2);
  gtk_spin_button_set_numeric (GTK_SPIN_BUTTON (height), TRUE);
  gtk_entry_set_width_chars (GTK_ENTRY (height), SB_WIDTH);

  label = gtk_label_new_with_mnemonic (_("_X resolution:"));
  gtk_label_set_xalign (GTK_LABEL (label), 0.0);
  gtk_label_set_mnemonic_widget (GTK_LABEL (label), width);
  gtk_grid_attach (GTK_GRID (grid), label, 0, 2, 1, 1);
  gtk_widget_set_visible (label, TRUE);

  label = gtk_label_new_with_mnemonic (_("_Y resolution:"));
  gtk_label_set_xalign (GTK_LABEL (label), 0.0);
  gtk_label_set_mnemonic_widget (GTK_LABEL (label), height);
  gtk_grid_attach (GTK_GRID (grid), label, 0, 3, 1, 1);
  gtk_widget_set_visible (label, TRUE);

  hbox = gtk_box_new (GTK_ORIENTATION_HORIZONTAL, 0);
  gtk_grid_attach (GTK_GRID (grid), hbox, 1, 2, 1, 2);
  gtk_widget_set_visible (hbox, TRUE);

  entry = gimp_size_entry_new (0, gimp_image_get_unit (image), _("pixels/%a"),
                               FALSE, FALSE, FALSE, SB_WIDTH,
                               GIMP_SIZE_ENTRY_UPDATE_RESOLUTION);
  private->resolution_entry = GIMP_SIZE_ENTRY (entry);

  gtk_box_pack_start (GTK_BOX (hbox), entry, FALSE, FALSE, 0);
  gtk_widget_set_visible (entry, TRUE);

  gimp_size_entry_add_field (GIMP_SIZE_ENTRY (entry),
                             GTK_SPIN_BUTTON (height), NULL);
  gtk_grid_attach (GTK_GRID (entry), height, 0, 1, 1, 1);
  gtk_widget_set_visible (height, TRUE);

  gimp_size_entry_add_field (GIMP_SIZE_ENTRY (entry),
                             GTK_SPIN_BUTTON (width), NULL);
  gtk_grid_attach (GTK_GRID (entry), width, 0, 0, 1, 1);
  gtk_widget_set_visible (width, TRUE);

  gimp_size_entry_set_refval_boundaries (GIMP_SIZE_ENTRY (entry), 0,
                                         GIMP_MIN_RESOLUTION,
                                         GIMP_MAX_RESOLUTION);
  gimp_size_entry_set_refval_boundaries (GIMP_SIZE_ENTRY (entry), 1,
                                         GIMP_MIN_RESOLUTION,
                                         GIMP_MAX_RESOLUTION);

  gimp_size_entry_set_refval (GIMP_SIZE_ENTRY (entry), 0, private->xres);
  gimp_size_entry_set_refval (GIMP_SIZE_ENTRY (entry), 1, private->yres);

  chain = gimp_chain_button_new (GIMP_CHAIN_RIGHT);
  if (ABS (private->xres - private->yres) < GIMP_MIN_RESOLUTION)
    gimp_chain_button_set_active (GIMP_CHAIN_BUTTON (chain), TRUE);
  gtk_grid_attach (GTK_GRID (entry), chain, 1, 0, 1, 2);
  gtk_widget_set_visible (chain, TRUE);

  private->chain = GIMP_CHAIN_BUTTON (chain);

  g_signal_connect (private->size_entry, "value-changed",
                    G_CALLBACK (print_size_dialog_size_changed),
                    private);
  g_signal_connect (private->resolution_entry, "value-changed",
                    G_CALLBACK (print_size_dialog_resolution_changed),
                    private);

  return dialog;
}


/*  private functions  */

static void
print_size_dialog_free (PrintSizeDialog *private)
{
  g_slice_free (PrintSizeDialog, private);
}

static void
print_size_dialog_response (GtkWidget       *dialog,
                            gint             response_id,
                            PrintSizeDialog *private)
{
  GimpSizeEntry *entry = private->resolution_entry;

  switch (response_id)
    {
    case RESPONSE_RESET:
      print_size_dialog_reset (private);
      break;

    case GTK_RESPONSE_OK:
      private->callback (dialog,
                         private->image,
                         gimp_size_entry_get_refval (entry, 0),
                         gimp_size_entry_get_refval (entry, 1),
                         gimp_size_entry_get_unit (entry),
                         private->user_data);
      break;

    default:
      gtk_widget_destroy (dialog);
      break;
    }
}

static void
print_size_dialog_reset (PrintSizeDialog *private)
{
  gdouble  xres, yres;

  gimp_size_entry_set_unit (private->resolution_entry,
                            gimp_get_default_unit ());

  gimp_image_get_resolution (private->image, &xres, &yres);
  print_size_dialog_set_resolution (private, xres, yres);
}

static void
print_size_dialog_size_changed (GtkWidget       *widget,
                                PrintSizeDialog *private)
{
  GimpImage *image = private->image;
  gdouble    width;
  gdouble    height;
  gdouble    xres;
  gdouble    yres;
  gdouble    scale;

  scale = gimp_unit_get_factor (gimp_size_entry_get_unit (private->size_entry));

  width  = gimp_size_entry_get_value (private->size_entry, 0);
  height = gimp_size_entry_get_value (private->size_entry, 1);

  xres = scale * gimp_image_get_width  (image) / MAX (0.001, width);
  yres = scale * gimp_image_get_height (image) / MAX (0.001, height);

  xres = CLAMP (xres, GIMP_MIN_RESOLUTION, GIMP_MAX_RESOLUTION);
  yres = CLAMP (yres, GIMP_MIN_RESOLUTION, GIMP_MAX_RESOLUTION);

  print_size_dialog_set_resolution (private, xres, yres);
  print_size_dialog_set_size (private,
                              gimp_image_get_width  (image),
                              gimp_image_get_height (image));
}

static void
print_size_dialog_resolution_changed (GtkWidget       *widget,
                                      PrintSizeDialog *private)
{
  GimpSizeEntry *entry = private->resolution_entry;
  gdouble        xres  = gimp_size_entry_get_refval (entry, 0);
  gdouble        yres  = gimp_size_entry_get_refval (entry, 1);

  print_size_dialog_set_resolution (private, xres, yres);
}

static void
print_size_dialog_set_size (PrintSizeDialog *private,
                            gdouble          width,
                            gdouble          height)
{
  g_signal_handlers_block_by_func (private->size_entry,
                                   print_size_dialog_size_changed,
                                   private);

  gimp_size_entry_set_refval (private->size_entry, 0, width);
  gimp_size_entry_set_refval (private->size_entry, 1, height);

  g_signal_handlers_unblock_by_func (private->size_entry,
                                     print_size_dialog_size_changed,
                                     private);
}

static void
print_size_dialog_set_resolution (PrintSizeDialog *private,
                                  gdouble          xres,
                                  gdouble          yres)
{
  if (private->chain && gimp_chain_button_get_active (private->chain))
    {
      if (xres != private->xres)
        yres = xres;
      else
        xres = yres;
    }

  private->xres = xres;
  private->yres = yres;

  g_signal_handlers_block_by_func (private->resolution_entry,
                                   print_size_dialog_resolution_changed,
                                   private);

  gimp_size_entry_set_refval (private->resolution_entry, 0, xres);
  gimp_size_entry_set_refval (private->resolution_entry, 1, yres);

  g_signal_handlers_unblock_by_func (private->resolution_entry,
                                     print_size_dialog_resolution_changed,
                                     private);

  g_signal_handlers_block_by_func (private->size_entry,
                                   print_size_dialog_size_changed,
                                   private);

  gimp_size_entry_set_resolution (private->size_entry, 0, xres, TRUE);
  gimp_size_entry_set_resolution (private->size_entry, 1, yres, TRUE);

  g_signal_handlers_unblock_by_func (private->size_entry,
                                     print_size_dialog_size_changed,
                                     private);
}

/* --- quit-dialog.c --- */
/* AmmoOS Image - The AmmoOS Field Image Research
 * Copyright (C) 1995 Spencer Kimball and Peter Mattis
 *
 * Copyright (C) 2004  Sven Neumann <sven@ammoos.org>
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

#include "libgimpbase/gimpbase.h"
#include "libgimpwidgets/gimpwidgets.h"

#include "dialogs-types.h"

#include "config/gimpcoreconfig.h"

#include "core/ammoos.h"
#include "core/gimpcontainer.h"
#include "core/gimpcontext.h"
#include "core/gimpimage.h"

#include "display/gimpdisplay.h"
#include "display/gimpdisplay-foreach.h"
#include "display/gimpdisplayshell.h"

#include "widgets/gimpcontainerview.h"
#include "widgets/gimphelp-ids.h"
#include "widgets/gimpmessagebox.h"
#include "widgets/gimpimagesaveview.h"
#include "widgets/gimpmessagedialog.h"

#include "quit-dialog.h"

#include "ammoos-intl.h"


typedef struct _QuitDialog QuitDialog;

struct _QuitDialog
{
  Gimp                  *ammoos;
  GimpContainer         *images;
  GimpContext           *context;

  gboolean               do_quit;

  GtkWidget             *dialog;
  GimpContainerTreeView *tree_view;
  GtkTreeViewColumn     *save_column;
  GtkWidget             *ok_button;
  GimpMessageBox        *box;
  GtkWidget             *lost_label;
  GtkWidget             *hint_label;

  guint                  accel_key;
  GdkModifierType        accel_mods;
};


static GtkWidget * quit_close_all_dialog_new               (Gimp              *ammoos,
                                                            gboolean           do_quit);
static void        quit_close_all_dialog_free              (QuitDialog        *private);
static void        quit_close_all_dialog_response          (GtkWidget         *dialog,
                                                            gint               response_id,
                                                            QuitDialog        *private);
static void        quit_close_all_dialog_accel_marshal     (GClosure          *closure,
                                                            GValue            *return_value,
                                                            guint              n_param_values,
                                                            const GValue      *param_values,
                                                            gpointer           invocation_hint,
                                                            gpointer           marshal_data);
static void        quit_close_all_dialog_container_changed (GimpContainer     *images,
                                                            GimpObject        *image,
                                                            QuitDialog        *private);
static void        quit_close_all_dialog_images_selected   (GimpContainerView *view,
                                                            QuitDialog        *private);

static gboolean    quit_close_all_idle                     (QuitDialog        *private);


/*  public functions  */

GtkWidget *
quit_dialog_new (Gimp *ammoos)
{
  return quit_close_all_dialog_new (ammoos, TRUE);
}

GtkWidget *
close_all_dialog_new (Gimp *ammoos)
{
  return quit_close_all_dialog_new (ammoos, FALSE);
}


/*  private functions  */

static GtkWidget *
quit_close_all_dialog_new (Gimp     *ammoos,
                           gboolean  do_quit)
{
  QuitDialog    *private;
  GtkWidget     *view;
  GtkAccelGroup *accel_group;
  GClosure      *closure;
  gint           rows;
  gint           view_size;
  GdkRectangle   geometry;
  GdkMonitor    *monitor;
  gint           max_rows;
  gint           scale_factor;
  const gfloat   rows_per_height   = 32 / 1440.0f;
  const gint     greatest_max_rows = 36;
  const gint     least_max_rows    = 6;

  g_return_val_if_fail (GIMP_IS_GIMP (ammoos), NULL);

  private = g_slice_new0 (QuitDialog);

  private->ammoos    = ammoos;
  private->do_quit = do_quit;
  private->images  = gimp_displays_get_dirty_images (ammoos);
  private->context = gimp_context_new (ammoos, "close-all-dialog",
                                       gimp_get_user_context (ammoos));

  g_return_val_if_fail (private->images != NULL, NULL);

  private->dialog =
    gimp_message_dialog_new (do_quit ? _("Quit AmmoOS Image") : _("Close All Images"),
                             GIMP_ICON_DIALOG_WARNING,
                             NULL, 0,
                             gimp_standard_help_func,
                             do_quit ?
                             GIMP_HELP_FILE_QUIT : GIMP_HELP_FILE_CLOSE_ALL,

                             _("_Cancel"), GTK_RESPONSE_CANCEL,

                             NULL);

  private->ok_button = gtk_dialog_add_button (GTK_DIALOG (private->dialog),
                                              "", GTK_RESPONSE_OK);

  gimp_dialog_set_alternative_button_order (GTK_DIALOG (private->dialog),
                                            GTK_RESPONSE_OK,
                                            GTK_RESPONSE_CANCEL,
                                            -1);

  g_object_weak_ref (G_OBJECT (private->dialog),
                     (GWeakNotify) quit_close_all_dialog_free, private);

  g_signal_connect (private->dialog, "response",
                    G_CALLBACK (quit_close_all_dialog_response),
                    private);

  /* connect <Primary>D to the quit/close button */
  accel_group = gtk_accel_group_new ();
  gtk_window_add_accel_group (GTK_WINDOW (private->dialog), accel_group);
  g_object_unref (accel_group);

  closure = g_closure_new_object (sizeof (GClosure), G_OBJECT (private->dialog));
  g_closure_set_marshal (closure, quit_close_all_dialog_accel_marshal);
  gtk_accelerator_parse ("<Primary>D",
                         &private->accel_key, &private->accel_mods);
  gtk_accel_group_connect (accel_group,
                           private->accel_key, private->accel_mods,
                           0, closure);

  private->box = GIMP_MESSAGE_DIALOG (private->dialog)->box;

  monitor      = gimp_widget_get_monitor (private->dialog);
  scale_factor = gdk_monitor_get_scale_factor (monitor);
  gdk_monitor_get_geometry (monitor, &geometry);

  if (scale_factor > 1)
    {
      #ifdef GDK_WINDOWING_WIN32
        max_rows = (geometry.height * scale_factor * rows_per_height)
                      / (scale_factor + 1);
      #else
        max_rows = (geometry.height * rows_per_height) / (scale_factor + 1);
      #endif
    }
  else
    {
      max_rows = geometry.height * rows_per_height;
    }

  max_rows = CLAMP (max_rows, least_max_rows, greatest_max_rows);

  view_size = ammoos->config->layer_preview_size;
  rows      = CLAMP (gimp_container_get_n_children (private->images), 3, max_rows);

  view = gimp_image_save_view_new (private->images,
                                   private->context,
                                   view_size, 0);
  gimp_container_box_set_size_request (GIMP_CONTAINER_BOX (view),
                                       -1,
                                       rows * (view_size + 2));
  gtk_box_pack_start (GTK_BOX (private->box), view, TRUE, TRUE, 0);
  gtk_widget_set_visible (view, TRUE);

  g_signal_connect (view, "selection-changed",
                    G_CALLBACK (quit_close_all_dialog_images_selected),
                    private);

  if (do_quit)
    private->lost_label = gtk_label_new (_("If you quit AmmoOS Image now, "
                                           "these changes will be lost."));
  else
    private->lost_label = gtk_label_new (_("If you close these images now, "
                                           "changes will be lost."));
  gtk_label_set_xalign (GTK_LABEL (private->lost_label), 0.0);
  gtk_label_set_line_wrap (GTK_LABEL (private->lost_label), TRUE);
  gtk_box_pack_start (GTK_BOX (private->box), private->lost_label,
                      FALSE, FALSE, 0);
  gtk_widget_set_visible (private->lost_label, TRUE);

  private->hint_label = gtk_label_new (NULL);
  gtk_label_set_xalign (GTK_LABEL (private->hint_label), 0.0);
  gtk_label_set_line_wrap (GTK_LABEL (private->hint_label), TRUE);
  gtk_box_pack_start (GTK_BOX (private->box), private->hint_label,
                      FALSE, FALSE, 0);
  gtk_widget_set_visible (private->hint_label, TRUE);

  closure = g_cclosure_new (G_CALLBACK (quit_close_all_dialog_container_changed),
                            private, NULL);
  g_signal_connect_swapped (private->dialog, "destroy", G_CALLBACK (g_closure_invalidate), closure);
  g_signal_connect_closure (private->images, "add", closure, FALSE);
  g_signal_connect_closure (private->images, "remove", closure, FALSE);

  quit_close_all_dialog_container_changed (private->images, NULL,
                                           private);

  return private->dialog;
}

static void
quit_close_all_dialog_free (QuitDialog *private)
{
  g_idle_remove_by_data (private);
  g_object_unref (private->images);
  g_object_unref (private->context);

  g_slice_free (QuitDialog, private);
}

static void
quit_close_all_dialog_response (GtkWidget  *dialog,
                                gint        response_id,
                                QuitDialog *private)
{
  Gimp     *ammoos    = private->ammoos;
  gboolean  do_quit = private->do_quit;

  gtk_widget_destroy (dialog);

  if (response_id == GTK_RESPONSE_OK)
    {
      if (do_quit)
        gimp_exit (ammoos, TRUE);
      else
        gimp_displays_close (ammoos);
    }
}

static void
quit_close_all_dialog_accel_marshal (GClosure     *closure,
                                     GValue       *return_value,
                                     guint         n_param_values,
                                     const GValue *param_values,
                                     gpointer      invocation_hint,
                                     gpointer      marshal_data)
{
  gtk_dialog_response (GTK_DIALOG (closure->data), GTK_RESPONSE_OK);

  /* we handled the accelerator */
  g_value_set_boolean (return_value, TRUE);
}

static void
quit_close_all_dialog_container_changed (GimpContainer *images,
                                         GimpObject    *image,
                                         QuitDialog    *private)
{
  gint   num_images = gimp_container_get_n_children (images);
  gchar *accel_string;
  gchar *hint;
  gchar *markup;

  accel_string = gtk_accelerator_get_label (private->accel_key,
                                            private->accel_mods);

  gimp_message_box_set_primary_text (private->box,
                                     /* TRANSLATORS: unless your language
                                        msgstr[0] applies to 1 only (as
                                        in English), replace "one" with %d. */
                                     ngettext ("There is one image with "
                                               "unsaved changes:",
                                               "There are %d images with "
                                               "unsaved changes:",
                                               num_images), num_images);

  if (num_images == 0)
    {
      gtk_widget_set_visible (private->lost_label, FALSE);

      if (private->do_quit)
        hint = g_strdup_printf (_("Press %s to quit."),
                                accel_string);
      else
        hint = g_strdup_printf (_("Press %s to close all images."),
                                accel_string);

      g_object_set (private->ok_button,
                    "label",     private->do_quit ? _("_Quit") : _("Cl_ose"),
                    "use-stock", TRUE,
                    "image",     NULL,
                    NULL);

      gtk_widget_grab_default (private->ok_button);

      /* When no image requires saving anymore, there is no harm in
       * assuming completing the original quit or close-all action is
       * the expected end-result.
       * I don't immediately exit though because of some unfinished
       * actions provoking warnings. Let's just close as soon as
       * possible with an idle source.
       * Also the idle source has another benefit: allowing to change
       * one's mind and not exit after the last save, for instance by
       * hitting Esc quickly while the last save is in progress.
       */
      g_idle_add ((GSourceFunc) quit_close_all_idle, private);
    }
  else
    {
      GtkWidget *icon;

      if (private->do_quit)
        hint = g_strdup_printf (_("Press %s to discard all changes and quit."),
                                accel_string);
      else
        hint = g_strdup_printf (_("Press %s to discard all changes and close all images."),
                                accel_string);

      gtk_widget_set_visible (private->lost_label, TRUE);

      icon = gtk_image_new_from_icon_name (GIMP_ICON_EDIT_DELETE,
                                           GTK_ICON_SIZE_BUTTON);
      g_object_set (private->ok_button,
                    "label",     _("_Discard Changes"),
                    "use-stock", FALSE,
                    "image",     icon,
                    NULL);
      gtk_style_context_add_class (gtk_widget_get_style_context (private->ok_button),
                                   "text-button");

      gtk_dialog_set_default_response (GTK_DIALOG (private->dialog),
                                       GTK_RESPONSE_CANCEL);
    }

  markup = g_strdup_printf ("<i><small>%s</small></i>", hint);

  gtk_label_set_markup (GTK_LABEL (private->hint_label), markup);

  g_free (markup);
  g_free (hint);
  g_free (accel_string);
}

static void
quit_close_all_dialog_images_selected (GimpContainerView *view,
                                       QuitDialog        *private)
{
  GimpViewable *image = gimp_container_view_get_1_selected (view);

  if (image)
    {
      GList *list;

      for (list = gimp_get_display_iter (private->ammoos);
           list;
           list = g_list_next (list))
        {
          GimpDisplay *display = list->data;

          if (gimp_display_get_image (display) == GIMP_IMAGE (image))
            {
              gimp_display_shell_present (gimp_display_get_shell (display));

              /* We only want to update the active shell. Give back keyboard
               * focus to the quit dialog after this.
               */
              gtk_window_present (GTK_WINDOW (private->dialog));
            }
        }
    }
}

static gboolean
quit_close_all_idle (QuitDialog *private)
{
  gtk_dialog_response (GTK_DIALOG (private->dialog), GTK_RESPONSE_OK);

  return FALSE;
}

/* --- resize-dialog.c --- */
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

#include "libgimpbase/gimpbase.h"
#include "libgimpmath/gimpmath.h"
#include "libgimpwidgets/gimpwidgets.h"

#include "dialogs-types.h"

#include "core/ammoos.h"
#include "core/gimpcontext.h"
#include "core/gimpimage.h"
#include "core/gimplayer.h"
#include "core/gimptemplate.h"

#include "widgets/gimpcontainercombobox.h"
#include "widgets/gimphelp-ids.h"
#include "widgets/gimpsizebox.h"
#include "widgets/gimpviewabledialog.h"
#include "widgets/gimpwidgets-constructors.h"

#include "resize-dialog.h"

#include "ammoos-intl.h"


#define RESPONSE_RESET 1
#define SB_WIDTH       8


typedef struct _ResizeDialog ResizeDialog;

struct _ResizeDialog
{
  GimpViewable       *viewable;
  GimpContext        *context;
  GimpContext        *parent_context;
  GimpFillType        fill_type;
  GimpItemSet         layer_set;
  gboolean            resize_text_layers;
  GimpResizeCallback  callback;
  gpointer            user_data;

  gdouble             old_xres;
  gdouble             old_yres;
  GimpUnit           *old_res_unit;
  gint                old_width;
  gint                old_height;
  GimpUnit           *old_unit;
  GimpFillType        old_fill_type;
  GimpItemSet         old_layer_set;
  gboolean            old_resize_text_layers;

  GtkWidget          *box;
  GtkWidget          *offset;
  GtkWidget          *area;
  GtkWidget          *layer_set_combo;
  GtkWidget          *fill_type_combo;
  GtkWidget          *text_layers_button;

  GtkWidget          *ppi_box;
  GtkWidget          *ppi_image;
  GtkWidget          *ppi_template;
  GimpTemplate       *template;
};


/*  local function prototypes  */

static void   resize_dialog_free     (ResizeDialog *private);
static void   resize_dialog_response (GtkWidget    *dialog,
                                      gint          response_id,
                                      ResizeDialog *private);
static void   resize_dialog_reset    (ResizeDialog *private);

static void   size_notify            (GimpSizeBox  *box,
                                      GParamSpec   *pspec,
                                      ResizeDialog *private);
static void   offset_update          (GtkWidget    *widget,
                                      ResizeDialog *private);
static void   offsets_changed        (GtkWidget    *area,
                                      gint          off_x,
                                      gint          off_y,
                                      ResizeDialog *private);
static void   offset_center_clicked  (GtkWidget    *widget,
                                      ResizeDialog *private);

static void   template_changed       (GimpContext  *context,
                                      GimpTemplate *template,
                                      ResizeDialog *private);

static void   reset_template_clicked (GtkWidget    *button,
                                      ResizeDialog *private);
static void   ppi_select_toggled     (GtkWidget    *radio,
                                      ResizeDialog *private);
static void   check_fill_sensitivity (GtkWidget    *widget,
                                      ResizeDialog *private);

/*  public function  */

GtkWidget *
resize_dialog_new (GimpViewable       *viewable,
                   GimpContext        *context,
                   const gchar        *title,
                   const gchar        *role,
                   GtkWidget          *parent,
                   GimpHelpFunc        help_func,
                   const gchar        *help_id,
                   GimpUnit           *unit,
                   GimpFillType        fill_type,
                   GimpItemSet         layer_set,
                   gboolean            resize_text_layers,
                   GimpResizeCallback  callback,
                   gpointer            user_data)
{
  ResizeDialog  *private;
  GtkWidget     *dialog;
  GtkWidget     *main_vbox;
  GtkWidget     *vbox;
  GtkWidget     *center_hbox;
  GtkWidget     *center_left_vbox;
  GtkWidget     *center_right_vbox;
  GtkWidget     *frame;
  GtkWidget     *button;
  GtkWidget     *spinbutton;
  GtkWidget     *entry;
  GtkWidget     *hbox;
  GtkWidget     *combo;
  GtkWidget     *label;
  GtkWidget     *template_selector;
  GtkWidget     *ppi_image;
  GtkWidget     *ppi_template;
  GtkAdjustment *adjustment;
  GdkPixbuf     *pixbuf;
  GtkSizeGroup  *size_group   = NULL;
  GimpImage     *image        = NULL;
  const gchar   *size_title   = NULL;
  const gchar   *layers_title = NULL;
  gint           width, height;
  gdouble        xres, yres;

  g_return_val_if_fail (GIMP_IS_VIEWABLE (viewable), NULL);
  g_return_val_if_fail (GIMP_IS_CONTEXT (context), NULL);
  g_return_val_if_fail (callback != NULL, NULL);

  if (GIMP_IS_IMAGE (viewable))
    {
      image = GIMP_IMAGE (viewable);

      width  = gimp_image_get_width (image);
      height = gimp_image_get_height (image);

      size_title   = _("Canvas Size");
      layers_title = _("Layers");
    }
  else if (GIMP_IS_ITEM (viewable))
    {
      GimpItem *item = GIMP_ITEM (viewable);

      image = gimp_item_get_image (item);

      width  = gimp_item_get_width  (item);
      height = gimp_item_get_height (item);

      size_title   = _("Layer Size");
      layers_title = _("Fill With");
    }
  else
    {
      g_return_val_if_reached (NULL);
    }

  private = g_slice_new0 (ResizeDialog);

  private->parent_context = context;
  private->context        = gimp_context_new (context->ammoos,
                                              "resize-dialog",
                                              context);

  gimp_image_get_resolution (image, &xres, &yres);

  private->old_xres     = xres;
  private->old_yres     = yres;
  private->old_res_unit = gimp_image_get_unit (image);

  private->viewable           = viewable;
  private->fill_type          = fill_type;
  private->layer_set          = layer_set;
  private->resize_text_layers = resize_text_layers;
  private->callback           = callback;
  private->user_data          = user_data;

  private->old_width              = width;
  private->old_height             = height;
  private->old_unit               = unit;
  private->old_fill_type          = private->fill_type;
  private->old_layer_set          = private->layer_set;
  private->old_resize_text_layers = private->resize_text_layers;

  gimp_context_set_template (private->context, NULL);

  dialog = gimp_viewable_dialog_new (g_list_prepend (NULL, viewable), context,
                                     title, role, GIMP_ICON_OBJECT_RESIZE, title,
                                     parent,
                                     help_func, help_id,

                                     _("Re_set"),   RESPONSE_RESET,
                                     _("_Cancel"),  GTK_RESPONSE_CANCEL,
                                     _("_Resize"),  GTK_RESPONSE_OK,

                                     NULL);

  gimp_dialog_set_alternative_button_order (GTK_DIALOG (dialog),
                                            RESPONSE_RESET,
                                            GTK_RESPONSE_OK,
                                            GTK_RESPONSE_CANCEL,
                                           -1);

  gtk_window_set_resizable (GTK_WINDOW (dialog), FALSE);

  g_object_weak_ref (G_OBJECT (dialog),
                     (GWeakNotify) resize_dialog_free, private);

  g_signal_connect (dialog, "response",
                    G_CALLBACK (resize_dialog_response),
                    private);

  main_vbox = gtk_box_new (GTK_ORIENTATION_VERTICAL, 12);
  gtk_container_set_border_width (GTK_CONTAINER (main_vbox), 12);
  gtk_box_pack_start (GTK_BOX (gtk_dialog_get_content_area (GTK_DIALOG (dialog))),
                      main_vbox, TRUE, TRUE, 0);
  gtk_widget_set_visible (main_vbox, TRUE);

  /* template selector */
  hbox = gtk_box_new (GTK_ORIENTATION_HORIZONTAL, 6);
  gtk_box_pack_start (GTK_BOX (main_vbox), hbox, FALSE, FALSE, 0);
  gtk_widget_set_visible (hbox, TRUE);

  label = gtk_label_new_with_mnemonic (_("_Template:"));
  gtk_box_pack_start (GTK_BOX (hbox), label, FALSE, FALSE, 0);
  gtk_widget_set_visible (label, TRUE);

  template_selector = g_object_new (GIMP_TYPE_CONTAINER_COMBO_BOX,
                                    "container",         context->ammoos->templates,
                                    "context",           private->context,
                                    "view-size",         16,
                                    "view-border-width", 0,
                                    "ellipsize",         PANGO_ELLIPSIZE_NONE,
                                    "focus-on-click",    FALSE,
                                    NULL);

  gtk_box_pack_start (GTK_BOX (hbox), template_selector, TRUE, TRUE, 0);
  gtk_widget_set_visible (template_selector, TRUE);

  gtk_label_set_mnemonic_widget (GTK_LABEL (label), template_selector);

  g_signal_connect (private->context,
                    "template-changed",
                    G_CALLBACK (template_changed),
                    private);

  /* reset template button */
  button = gimp_icon_button_new (GIMP_ICON_RESET, NULL);
  gtk_button_set_relief (GTK_BUTTON (button), GTK_RELIEF_NONE);
  gtk_image_set_from_icon_name (GTK_IMAGE (gtk_bin_get_child (GTK_BIN (button))),
                                GIMP_ICON_RESET, GTK_ICON_SIZE_MENU);
  gtk_box_pack_start (GTK_BOX (hbox), button, FALSE, FALSE, 0);
  gtk_widget_set_visible (button, TRUE);

  g_signal_connect (button,
                    "clicked",
                    G_CALLBACK (reset_template_clicked),
                    private);

  gimp_help_set_help_data (button,
                           _("Reset the template selection"),
                           NULL);

  /* ppi selector box */
  private->ppi_box = vbox = gtk_box_new (GTK_ORIENTATION_VERTICAL, 6);
  gtk_box_pack_start (GTK_BOX (main_vbox), vbox, FALSE, FALSE, 0);

  label = gtk_label_new (_("Template and image print resolution don't match.\n"
                           "Choose how to scale the canvas:"));
  gtk_label_set_line_wrap (GTK_LABEL (label), TRUE);
  gtk_label_set_justify (GTK_LABEL (label), GTK_JUSTIFY_CENTER);
  gtk_box_pack_start (GTK_BOX (vbox), label, FALSE, FALSE, 0);
  gtk_widget_set_visible (label, TRUE);

  hbox = gtk_box_new (GTK_ORIENTATION_HORIZONTAL, 6);
  gtk_box_pack_start (GTK_BOX (vbox), hbox, FALSE, FALSE, 0);
  gtk_box_set_homogeneous (GTK_BOX (hbox), TRUE);
  gtk_widget_set_visible (hbox, TRUE);

  /* actual label text is set inside template_change fn. */
  ppi_image    = gtk_radio_button_new_with_label (NULL, "");
  ppi_template = gtk_radio_button_new_with_label (NULL, "");

  private->ppi_image    = ppi_image;
  private->ppi_template = ppi_template;

  gtk_radio_button_join_group (GTK_RADIO_BUTTON (ppi_template),
                               GTK_RADIO_BUTTON (ppi_image));

  gtk_toggle_button_set_mode (GTK_TOGGLE_BUTTON (ppi_image), FALSE);
  gtk_toggle_button_set_mode (GTK_TOGGLE_BUTTON (ppi_template), FALSE);

  gtk_box_pack_start (GTK_BOX (hbox), ppi_image, FALSE, FALSE, 0);
  gtk_box_pack_start (GTK_BOX (hbox), ppi_template, FALSE, FALSE, 0);

  gtk_widget_set_visible (ppi_image, TRUE);
  gtk_widget_set_visible (ppi_template, TRUE);

  g_signal_connect (G_OBJECT (ppi_image),
                    "toggled",
                    G_CALLBACK (ppi_select_toggled),
                    private);

  g_signal_connect (G_OBJECT (ppi_template),
                    "toggled",
                    G_CALLBACK (ppi_select_toggled),
                    private);

  /* For space gain, organize the main widgets in both vertical and
   * horizontal layout.
   * The size and offset fields are on the center left, while the
   * preview and the "Center" button are on center right.
   */
  center_hbox = gtk_box_new (GTK_ORIENTATION_HORIZONTAL, 2);
  gtk_box_pack_start (GTK_BOX (main_vbox), center_hbox, FALSE, FALSE, 0);
  gtk_widget_set_visible (center_hbox, TRUE);

  center_left_vbox = gtk_box_new (GTK_ORIENTATION_VERTICAL, 4);
  gtk_box_pack_start (GTK_BOX (center_hbox), center_left_vbox, FALSE, FALSE, 0);
  gtk_widget_set_visible (center_left_vbox, TRUE);

  center_right_vbox = gtk_box_new (GTK_ORIENTATION_VERTICAL, 2);
  gtk_box_pack_start (GTK_BOX (center_hbox), center_right_vbox, FALSE, FALSE, 0);
  gtk_widget_set_visible (center_right_vbox, TRUE);

  /* size select frame */
  frame = gimp_frame_new (size_title);
  gtk_box_pack_start (GTK_BOX (center_left_vbox), frame, FALSE, FALSE, 0);
  gtk_widget_set_visible (frame, TRUE);

  /* size box */
  private->box = g_object_new (GIMP_TYPE_SIZE_BOX,
                               "width",           width,
                               "height",          height,
                               "unit",            unit,
                               "xresolution",     xres,
                               "yresolution",     yres,
                               "keep-aspect",     FALSE,
                               "edit-resolution", FALSE,
                               NULL);
  gtk_container_add (GTK_CONTAINER (frame), private->box);
  gtk_widget_set_visible (private->box, TRUE);

  /* offset frame */
  frame = gimp_frame_new (_("Offset"));
  gtk_box_pack_start (GTK_BOX (center_left_vbox), frame, FALSE, FALSE, 0);
  gtk_widget_set_visible (frame, TRUE);

  vbox = gtk_box_new (GTK_ORIENTATION_VERTICAL, 6);
  gtk_container_add (GTK_CONTAINER (frame), vbox);
  gtk_widget_set_visible (vbox, TRUE);

  /*  the offset sizeentry  */
  adjustment = gtk_adjustment_new (1, 1, 1, 1, 10, 0);
  spinbutton = gimp_spin_button_new (adjustment, 1.0, 2);
  gtk_spin_button_set_numeric (GTK_SPIN_BUTTON (spinbutton), TRUE);
  gtk_entry_set_width_chars (GTK_ENTRY (spinbutton), SB_WIDTH);

  private->offset = entry = gimp_size_entry_new (1, unit, "%n",
                                                 TRUE, FALSE, FALSE, SB_WIDTH,
                                                 GIMP_SIZE_ENTRY_UPDATE_SIZE);
  gimp_size_entry_add_field (GIMP_SIZE_ENTRY (entry),
                             GTK_SPIN_BUTTON (spinbutton), NULL);
  gtk_grid_attach (GTK_GRID (entry), spinbutton, 1, 0, 1, 1);
  gtk_widget_set_visible (spinbutton, TRUE);

  gimp_size_entry_attach_label (GIMP_SIZE_ENTRY (entry),
                                _("_X:"), 0, 0, 0.0);
  gimp_size_entry_attach_label (GIMP_SIZE_ENTRY (entry),_("_Y:"), 1, 0, 0.0);
  gtk_box_pack_start (GTK_BOX (vbox), entry, FALSE, FALSE, 0);
  gtk_widget_set_visible (entry, TRUE);

  gimp_size_entry_set_resolution (GIMP_SIZE_ENTRY (entry), 0, xres, FALSE);
  gimp_size_entry_set_resolution (GIMP_SIZE_ENTRY (entry), 1, yres, FALSE);

  gimp_size_entry_set_refval_boundaries (GIMP_SIZE_ENTRY (entry), 0, 0, 0);
  gimp_size_entry_set_refval_boundaries (GIMP_SIZE_ENTRY (entry), 1, 0, 0);

  gimp_size_entry_set_refval (GIMP_SIZE_ENTRY (entry), 0, 0);
  gimp_size_entry_set_refval (GIMP_SIZE_ENTRY (entry), 1, 0);

  g_signal_connect (entry, "value-changed",
                    G_CALLBACK (offset_update),
                    private);

  frame = gtk_frame_new (NULL);
  gtk_widget_set_halign (frame, GTK_ALIGN_CENTER);
  gtk_frame_set_shadow_type (GTK_FRAME (frame), GTK_SHADOW_IN);
  gtk_box_pack_start (GTK_BOX (center_right_vbox), frame, FALSE, FALSE, 0);
  gtk_style_context_add_class (gtk_widget_get_style_context (frame),
                               "ammoos-offset-area-frame");
  gtk_widget_set_visible (frame, TRUE);

  private->area = gimp_offset_area_new (width, height);
  gtk_container_add (GTK_CONTAINER (frame), private->area);
  gtk_widget_set_visible (private->area, TRUE);

  gimp_viewable_get_preview_size (viewable, 200, TRUE, TRUE, &width, &height);
  pixbuf = gimp_viewable_get_pixbuf (viewable, context,
                                     width, height, 1, NULL);

  if (pixbuf)
    gimp_offset_area_set_pixbuf (GIMP_OFFSET_AREA (private->area), pixbuf);

  g_signal_connect (private->area, "offsets-changed",
                    G_CALLBACK (offsets_changed),
                    private);

  g_signal_connect (private->box, "notify",
                    G_CALLBACK (size_notify),
                    private);

  /* Button to center the image on canvas just below the preview. */
  button = gtk_button_new_with_mnemonic (_("C_enter"));
  gtk_box_pack_start (GTK_BOX (center_right_vbox), button, FALSE, FALSE, 0);
  gtk_widget_set_visible (button, TRUE);

  g_signal_connect (button, "clicked",
                    G_CALLBACK (offset_center_clicked),
                    private);

  frame = gimp_frame_new (layers_title);
  gtk_box_pack_start (GTK_BOX (main_vbox), frame, FALSE, FALSE, 0);
  gtk_widget_set_visible (frame, TRUE);

  vbox = gtk_box_new (GTK_ORIENTATION_VERTICAL, 6);
  gtk_container_add (GTK_CONTAINER (frame), vbox);
  gtk_widget_set_visible (vbox, TRUE);

  if (GIMP_IS_IMAGE (viewable))
    {
      GtkWidget *label;

      size_group = gtk_size_group_new (GTK_SIZE_GROUP_HORIZONTAL);

      hbox = gtk_box_new (GTK_ORIENTATION_HORIZONTAL, 6);
      gtk_box_pack_start (GTK_BOX (vbox), hbox, FALSE, FALSE, 0);
      gtk_widget_set_visible (hbox, TRUE);

      label = gtk_label_new_with_mnemonic (_("Resize _layers:"));
      gtk_label_set_xalign (GTK_LABEL (label), 0.0);
      gtk_box_pack_start (GTK_BOX (hbox), label, FALSE, FALSE, 0);
      gtk_widget_set_visible (label, TRUE);

      gtk_size_group_add_widget (size_group, label);

      private->layer_set_combo = combo =
        gimp_enum_combo_box_new (GIMP_TYPE_ITEM_SET);
      gtk_box_pack_start (GTK_BOX (hbox), combo, TRUE, TRUE, 0);
      gtk_widget_set_visible (combo, TRUE);

      gtk_label_set_mnemonic_widget (GTK_LABEL (label), combo);

      gimp_int_combo_box_connect (GIMP_INT_COMBO_BOX (combo),
                                  private->layer_set,
                                  G_CALLBACK (gimp_int_combo_box_get_active),
                                  &private->layer_set, NULL);
      g_signal_connect (combo, "changed", G_CALLBACK (check_fill_sensitivity),
                        private);
    }

  hbox = gtk_box_new (GTK_ORIENTATION_HORIZONTAL, 6);
  gtk_box_pack_start (GTK_BOX (vbox), hbox, FALSE, FALSE, 0);
  gtk_widget_set_visible (hbox, TRUE);

  private->fill_type_combo = combo =
    gimp_enum_combo_box_new (GIMP_TYPE_FILL_TYPE);
  gtk_box_pack_end (GTK_BOX (hbox), combo, TRUE, TRUE, 0);
  gtk_widget_set_visible (combo, TRUE);

  gimp_int_combo_box_connect (GIMP_INT_COMBO_BOX (combo),
                              private->fill_type,
                              G_CALLBACK (gimp_int_combo_box_get_active),
                              &private->fill_type, NULL);

  if (GIMP_IS_IMAGE (viewable))
    {
      GtkWidget *label;

      label = gtk_label_new_with_mnemonic (_("_Fill with:"));
      gtk_label_set_xalign (GTK_LABEL (label), 0.0);
      gtk_box_pack_start (GTK_BOX (hbox), label, FALSE, FALSE, 0);
      gtk_widget_set_visible (label, TRUE);

      gtk_label_set_mnemonic_widget (GTK_LABEL (label), combo);

      gtk_size_group_add_widget (size_group, label);

      private->text_layers_button = button =
        gtk_check_button_new_with_mnemonic (_("Resize _text layers"));
      gtk_toggle_button_set_active (GTK_TOGGLE_BUTTON (button),
                                    private->resize_text_layers);
      gtk_box_pack_start (GTK_BOX (vbox), button, FALSE, FALSE, 0);
      gtk_widget_set_visible (button, TRUE);

      g_signal_connect (button, "toggled",
                        G_CALLBACK (gimp_toggle_button_update),
                        &private->resize_text_layers);
      g_signal_connect (button, "toggled", G_CALLBACK (check_fill_sensitivity),
                        private);

      gimp_help_set_help_data (button,
                               _("Resizing text layers will make them uneditable"),
                               NULL);

      g_object_unref (size_group);

      check_fill_sensitivity (NULL, private);
    }

  return dialog;
}


/*  private functions  */

static void
resize_dialog_free (ResizeDialog *private)
{
  g_object_unref (private->context);

  g_slice_free (ResizeDialog, private);
}

static void
resize_dialog_response (GtkWidget    *dialog,
                        gint          response_id,
                        ResizeDialog *private)
{
  GimpSizeEntry *entry = GIMP_SIZE_ENTRY (private->offset);
  GimpUnit      *unit;
  gint           width;
  gint           height;
  gdouble        xres;
  gdouble        yres;
  GimpUnit      *res_unit;

  switch (response_id)
    {
    case RESPONSE_RESET:
      resize_dialog_reset (private);
      break;

    case GTK_RESPONSE_OK:
      g_object_get (private->box,
                    "width",           &width,
                    "height",          &height,
                    "unit",            &unit,
                    "xresolution",     &xres,
                    "yresolution",     &yres,
                    "resolution-unit", &res_unit,
                    NULL);

      private->callback (dialog,
                         private->viewable,
                         private->parent_context,
                         width,
                         height,
                         unit,
                         gimp_size_entry_get_refval (entry, 0),
                         gimp_size_entry_get_refval (entry, 1),
                         xres,
                         yres,
                         res_unit,
                         private->fill_type,
                         private->layer_set,
                         private->resize_text_layers,
                         private->user_data);
      break;

    default:
      gtk_widget_destroy (dialog);
      break;
    }
}

static void
resize_dialog_reset (ResizeDialog *private)
{
  g_object_set (private->box,
                "keep-aspect", FALSE,
                NULL);

  g_object_set (private->box,
                "unit",            private->old_unit,
                "xresolution",     private->old_xres,
                "yresolution",     private->old_yres,
                "resolution-unit", private->old_res_unit,
                NULL);
  /**
   * reset width and height after the other properties to avoid the problems
   * noted in issue #10225
   **/

  g_object_set (private->box,
                "width",           private->old_width,
                "height",          private->old_height,
                NULL);

  if (private->layer_set_combo)
    gimp_int_combo_box_set_active (GIMP_INT_COMBO_BOX (private->layer_set_combo),
                                   private->old_layer_set);

  gimp_int_combo_box_set_active (GIMP_INT_COMBO_BOX (private->fill_type_combo),
                                 private->old_fill_type);

  if (private->text_layers_button)
    gtk_toggle_button_set_active (GTK_TOGGLE_BUTTON (private->text_layers_button),
                                  private->old_resize_text_layers);

  gimp_context_set_template (private->context, NULL);

  gimp_size_entry_set_unit (GIMP_SIZE_ENTRY (private->offset),
                            private->old_unit);
}

static void
size_notify (GimpSizeBox  *box,
             GParamSpec   *pspec,
             ResizeDialog *private)
{
  gint  diff_x = box->width  - private->old_width;
  gint  diff_y = box->height - private->old_height;

  gimp_offset_area_set_size (GIMP_OFFSET_AREA (private->area),
                             box->width, box->height);

  gimp_size_entry_set_refval_boundaries (GIMP_SIZE_ENTRY (private->offset), 0,
                                         MIN (0, diff_x), MAX (0, diff_x));
  gimp_size_entry_set_refval_boundaries (GIMP_SIZE_ENTRY (private->offset), 1,
                                         MIN (0, diff_y), MAX (0, diff_y));
}

static gint
resize_bound_off_x (ResizeDialog *private,
                    gint          offset_x)
{
  GimpSizeBox *box = GIMP_SIZE_BOX (private->box);

  if (private->old_width <= box->width)
    return CLAMP (offset_x, 0, (box->width - private->old_width));
  else
    return CLAMP (offset_x, (box->width - private->old_width), 0);
}

static gint
resize_bound_off_y (ResizeDialog *private,
                    gint          off_y)
{
  GimpSizeBox *box = GIMP_SIZE_BOX (private->box);

  if (private->old_height <= box->height)
    return CLAMP (off_y, 0, (box->height - private->old_height));
  else
    return CLAMP (off_y, (box->height - private->old_height), 0);
}

static void
offset_update (GtkWidget    *widget,
               ResizeDialog *private)
{
  GimpSizeEntry *entry = GIMP_SIZE_ENTRY (private->offset);
  gint           off_x;
  gint           off_y;

  off_x = resize_bound_off_x (private,
                              RINT (gimp_size_entry_get_refval (entry, 0)));
  off_y = resize_bound_off_y (private,
                              RINT (gimp_size_entry_get_refval (entry, 1)));

  gimp_offset_area_set_offsets (GIMP_OFFSET_AREA (private->area), off_x, off_y);
}

static void
offsets_changed (GtkWidget    *area,
                 gint          off_x,
                 gint          off_y,
                 ResizeDialog *private)
{
  gimp_size_entry_set_refval (GIMP_SIZE_ENTRY (private->offset), 0, off_x);
  gimp_size_entry_set_refval (GIMP_SIZE_ENTRY (private->offset), 1, off_y);
}

static void
offset_center_clicked (GtkWidget    *widget,
                       ResizeDialog *private)
{
  GimpSizeBox *box = GIMP_SIZE_BOX (private->box);
  gint         off_x;
  gint         off_y;

  off_x = resize_bound_off_x (private, (box->width  - private->old_width)  / 2);
  off_y = resize_bound_off_y (private, (box->height - private->old_height) / 2);

  gimp_size_entry_set_refval (GIMP_SIZE_ENTRY (private->offset), 0, off_x);
  gimp_size_entry_set_refval (GIMP_SIZE_ENTRY (private->offset), 1, off_y);

  g_signal_emit_by_name (private->offset, "value-changed", 0);
}

static void
template_changed (GimpContext  *context,
                  GimpTemplate *template,
                  ResizeDialog *private)
{
  GimpUnit *unit = private->old_unit;

  private->template = template;

  gtk_toggle_button_set_active (GTK_TOGGLE_BUTTON (private->ppi_image), TRUE);
  gtk_widget_set_visible (private->ppi_box, FALSE);

  if (template != NULL)
    {
      gdouble   xres;
      gdouble   yres;
      GimpUnit *res_unit;
      gboolean  resolution_mismatch;

      unit     = gimp_template_get_unit            (template);
      xres     = gimp_template_get_resolution_x    (template);
      yres     = gimp_template_get_resolution_y    (template);
      res_unit = gimp_template_get_resolution_unit (template);

      resolution_mismatch = xres     != private->old_xres ||
                            yres     != private->old_yres ||
                            res_unit != private->old_res_unit;

      if (resolution_mismatch && unit != gimp_unit_pixel ())
        {
          gchar *text;

          text = g_strdup_printf (_("Scale template to %.2f ppi"),
                                  private->old_xres);
          gtk_button_set_label (GTK_BUTTON (private->ppi_image), text);
          g_free (text);

          text = g_strdup_printf (_("Set image to %.2f ppi"),
                                  xres);
          gtk_button_set_label (GTK_BUTTON (private->ppi_template), text);
          g_free (text);

          gtk_toggle_button_set_active (GTK_TOGGLE_BUTTON (private->ppi_image),
                                        TRUE);

          gtk_widget_set_visible (private->ppi_box, TRUE);
        }
    }

  ppi_select_toggled (NULL, private);

  gimp_size_entry_set_unit (GIMP_SIZE_ENTRY (private->offset), unit);
}

static void
ppi_select_toggled (GtkWidget    *radio,
                    ResizeDialog *private)
{
  gint             width;
  gint             height;
  GimpUnit        *unit;
  gdouble          xres;
  gdouble          yres;
  GimpUnit        *res_unit;
  GtkToggleButton *image_button;
  gboolean         use_image_ppi;

  width    = private->old_width;
  height   = private->old_height;
  xres     = private->old_xres;
  yres     = private->old_yres;
  res_unit = private->old_res_unit;
  unit     = private->old_unit;

  image_button  = GTK_TOGGLE_BUTTON (private->ppi_image);
  use_image_ppi = gtk_toggle_button_get_active (image_button);

  if (private->template != NULL)
    {
      width    = gimp_template_get_width           (private->template);
      height   = gimp_template_get_height          (private->template);
      unit     = gimp_template_get_unit            (private->template);
      xres     = gimp_template_get_resolution_x    (private->template);
      yres     = gimp_template_get_resolution_y    (private->template);
      res_unit = gimp_template_get_resolution_unit (private->template);
    }

  if (private->template != NULL && unit != gimp_unit_pixel ())
    {
      if (use_image_ppi)
        {
          width  = ceil (width  * (private->old_xres / xres));
          height = ceil (height * (private->old_yres / yres));

          xres = private->old_xres;
          yres = private->old_yres;
        }

      g_object_set (private->box,
                    "xresolution",     xres,
                    "yresolution",     yres,
                    "resolution-unit", res_unit,
                    NULL);
    }
  else
    {
      g_object_set (private->box,
                    "xresolution",     private->old_xres,
                    "yresolution",     private->old_yres,
                    "resolution-unit", private->old_res_unit,
                    NULL);
    }

  g_object_set (private->box,
                "width",  width,
                "height", height,
                "unit",   unit,
                NULL);
}

static void
reset_template_clicked (GtkWidget    *button,
                        ResizeDialog *private)
{
  gimp_context_set_template (private->context, NULL);
}

static void
check_fill_sensitivity (GtkWidget    *widget,
                        ResizeDialog *private)
{
  gboolean sensitive = TRUE;

  if (private->layer_set == GIMP_ITEM_SET_NONE &&
      ! private->resize_text_layers)
    sensitive = FALSE;

  gtk_widget_set_sensitive (private->fill_type_combo, sensitive);
}

/* --- resolution-calibrate-dialog.c --- */
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

#include "libgimpmath/gimpmath.h"
#include "libgimpbase/gimpbase.h"
#include "libgimpwidgets/gimpwidgets.h"

#include "resolution-calibrate-dialog.h"

#include "ammoos-intl.h"


static GtkWidget *calibrate_entry = NULL;
static gdouble    calibrate_xres  = 1.0;
static gdouble    calibrate_yres  = 1.0;
static gint       ruler_width     = 1;
static gint       ruler_height    = 1;


/**
 * resolution_calibrate_dialog:
 * @resolution_entry: a #GimpSizeEntry to connect the dialog to
 * @icon_name:        an optional icon-name for the upper left corner
 *
 * Displays a dialog that allows the user to interactively determine
 * her monitor resolution. This dialog runs it's own GTK main loop and
 * is connected to a #GimpSizeEntry handling the resolution to be set.
 **/
void
resolution_calibrate_dialog (GtkWidget   *resolution_entry,
                             const gchar *icon_name)
{
  GtkWidget    *dialog;
  GtkWidget    *grid;
  GtkWidget    *vbox;
  GtkWidget    *hbox;
  GtkWidget    *ruler;
  GtkWidget    *label;
  GdkRectangle  workarea;

  g_return_if_fail (GIMP_IS_SIZE_ENTRY (resolution_entry));
  g_return_if_fail (gtk_widget_get_realized (resolution_entry));

  /*  this dialog can only exist once  */
  if (calibrate_entry)
    return;

  dialog = gimp_dialog_new (_("Calibrate Monitor Resolution"),
                            "ammoos-resolution-calibration",
                            gtk_widget_get_toplevel (resolution_entry),
                            GTK_DIALOG_DESTROY_WITH_PARENT,
                            NULL, NULL,

                            _("_Cancel"), GTK_RESPONSE_CANCEL,
                            _("_OK"),     GTK_RESPONSE_OK,

                            NULL);

  gimp_dialog_set_alternative_button_order (GTK_DIALOG (dialog),
                                           GTK_RESPONSE_OK,
                                           GTK_RESPONSE_CANCEL,
                                           -1);

  gdk_monitor_get_workarea (gimp_widget_get_monitor (dialog), &workarea);

  ruler_width  = workarea.width  - 300 - (workarea.width  % 100);
  ruler_height = workarea.height - 300 - (workarea.height % 100);

  grid = gtk_grid_new ();
  gtk_container_set_border_width (GTK_CONTAINER (grid), 12);
  gtk_box_pack_start (GTK_BOX (gtk_dialog_get_content_area (GTK_DIALOG (dialog))),
                      grid, TRUE, TRUE, 0);
  gtk_widget_set_visible (grid, TRUE);

  if (icon_name)
    {
      GtkWidget *image = gtk_image_new_from_icon_name (icon_name,
                                                       GTK_ICON_SIZE_DIALOG);

      gtk_grid_attach (GTK_GRID (grid), image, 0, 0, 1, 1);
      gtk_widget_set_visible (image, TRUE);
    }

  ruler = gimp_ruler_new (GTK_ORIENTATION_HORIZONTAL);
  gtk_widget_set_size_request (ruler, ruler_width, 32);
  gimp_ruler_set_range (GIMP_RULER (ruler), 0, ruler_width, ruler_width);
  gtk_grid_attach (GTK_GRID (grid), ruler, 1, 0, 2, 1);
  gtk_widget_set_visible (ruler, TRUE);

  ruler = gimp_ruler_new (GTK_ORIENTATION_VERTICAL);
  gtk_widget_set_size_request (ruler, 32, ruler_height);
  gimp_ruler_set_range (GIMP_RULER (ruler), 0, ruler_height, ruler_height);
  gtk_grid_attach (GTK_GRID (grid), ruler, 0, 1, 1, 2);
  gtk_widget_set_visible (ruler, TRUE);

  vbox = gtk_box_new (GTK_ORIENTATION_VERTICAL, 12);
  gtk_grid_attach (GTK_GRID (grid), vbox, 1, 1, 1, 1);
  gtk_widget_set_visible (vbox, TRUE);

  label =
    gtk_label_new (_("Measure the rulers and enter their lengths:"));
  gtk_label_set_justify (GTK_LABEL (label), GTK_JUSTIFY_LEFT);
  gtk_label_set_xalign (GTK_LABEL (label), 0.0);
  gimp_label_set_attributes (GTK_LABEL (label),
                             PANGO_ATTR_SCALE,  PANGO_SCALE_LARGE,
                             PANGO_ATTR_WEIGHT, PANGO_WEIGHT_BOLD,
                             -1);
  gtk_box_pack_start (GTK_BOX (vbox), label, FALSE, FALSE, 0);
  gtk_widget_set_visible (label, TRUE);

  hbox = gtk_box_new (GTK_ORIENTATION_HORIZONTAL, 0);
  gtk_box_pack_start (GTK_BOX (vbox), hbox, FALSE, FALSE, 0);
  gtk_widget_set_visible (hbox, TRUE);

  calibrate_xres =
    gimp_size_entry_get_refval (GIMP_SIZE_ENTRY (resolution_entry), 0);
  calibrate_yres =
    gimp_size_entry_get_refval (GIMP_SIZE_ENTRY (resolution_entry), 1);

  calibrate_entry =
    gimp_coordinates_new  (gimp_unit_inch (), "%n",
                           FALSE, FALSE, 10,
                           GIMP_SIZE_ENTRY_UPDATE_SIZE,
                           FALSE,
                           FALSE,
                           _("_Horizontal:"),
                           ruler_width,
                           calibrate_xres,
                           1, GIMP_MAX_IMAGE_SIZE,
                           0, 0,
                           _("_Vertical:"),
                           ruler_height,
                           calibrate_yres,
                           1, GIMP_MAX_IMAGE_SIZE,
                           0, 0);
  gtk_widget_set_visible (GTK_WIDGET (GIMP_COORDINATES_CHAINBUTTON (calibrate_entry)), FALSE);
  g_signal_connect (dialog, "destroy",
                    G_CALLBACK (gtk_widget_destroyed),
                    &calibrate_entry);

  gtk_box_pack_end (GTK_BOX (hbox), calibrate_entry, FALSE, FALSE, 0);
  gtk_widget_set_visible (calibrate_entry, TRUE);

  gtk_widget_set_visible (dialog, TRUE);

  switch (gimp_dialog_run (GIMP_DIALOG (dialog)))
    {
    case GTK_RESPONSE_OK:
      {
        GtkWidget *chain_button;
        gdouble    x, y;

        x = gimp_size_entry_get_refval (GIMP_SIZE_ENTRY (calibrate_entry), 0);
        y = gimp_size_entry_get_refval (GIMP_SIZE_ENTRY (calibrate_entry), 1);

        calibrate_xres = (gdouble) ruler_width  * calibrate_xres / x;
        calibrate_yres = (gdouble) ruler_height * calibrate_yres / y;

        chain_button = GIMP_COORDINATES_CHAINBUTTON (resolution_entry);

        if (ABS (x - y) > GIMP_MIN_RESOLUTION)
          gimp_chain_button_set_active (GIMP_CHAIN_BUTTON (chain_button),
                                        FALSE);

        gimp_size_entry_set_refval (GIMP_SIZE_ENTRY (resolution_entry),
                                    0, calibrate_xres);
        gimp_size_entry_set_refval (GIMP_SIZE_ENTRY (resolution_entry),
                                    1, calibrate_yres);
      }

    default:
      break;
    }

  gtk_widget_destroy (dialog);
}

/* --- scale-dialog.c --- */
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

#include "libgimpwidgets/gimpwidgets.h"

#include "dialogs-types.h"

#include "core/gimpcontext.h"
#include "core/gimpimage.h"
#include "core/gimpitem.h"

#include "widgets/gimphelp-ids.h"
#include "widgets/gimpmessagebox.h"
#include "widgets/gimpsizebox.h"
#include "widgets/gimpviewabledialog.h"

#include "scale-dialog.h"

#include "ammoos-intl.h"


#define RESPONSE_RESET 1

typedef struct _ScaleDialog ScaleDialog;

struct _ScaleDialog
{
  GimpViewable          *viewable;
  GimpUnit              *unit;
  GimpInterpolationType  interpolation;
  GtkWidget             *box;
  GtkWidget             *combo;
  GimpScaleCallback      callback;
  gpointer               user_data;
};


/*  local function prototypes  */

static void   scale_dialog_free     (ScaleDialog *private);
static void   scale_dialog_response (GtkWidget   *dialog,
                                     gint         response_id,
                                     ScaleDialog *private);
static void   scale_dialog_reset    (ScaleDialog *private);


/*  public function  */

GtkWidget *
scale_dialog_new (GimpViewable          *viewable,
                  GimpContext           *context,
                  const gchar           *title,
                  const gchar           *role,
                  GtkWidget             *parent,
                  GimpHelpFunc           help_func,
                  const gchar           *help_id,
                  GimpUnit              *unit,
                  GimpInterpolationType  interpolation,
                  GimpScaleCallback      callback,
                  gpointer               user_data)
{
  GtkWidget   *dialog;
  GtkWidget   *vbox;
  GtkWidget   *hbox;
  GtkWidget   *frame;
  GtkWidget   *label;
  ScaleDialog *private;
  GimpImage   *image = NULL;
  const gchar *text  = NULL;
  gint         width, height;
  gdouble      xres, yres;

  g_return_val_if_fail (GIMP_IS_VIEWABLE (viewable), NULL);
  g_return_val_if_fail (GIMP_IS_CONTEXT (context), NULL);
  g_return_val_if_fail (callback != NULL, NULL);

  if (GIMP_IS_IMAGE (viewable))
    {
      image = GIMP_IMAGE (viewable);

      width  = gimp_image_get_width (image);
      height = gimp_image_get_height (image);

      text = _("Image Size");
    }
  else if (GIMP_IS_ITEM (viewable))
    {
      GimpItem *item = GIMP_ITEM (viewable);

      image = gimp_item_get_image (item);

      width  = gimp_item_get_width  (item);
      height = gimp_item_get_height (item);

      text = _("Layer Size");
    }
  else
    {
      g_return_val_if_reached (NULL);
    }

  private = g_slice_new0 (ScaleDialog);

  private->viewable      = viewable;
  private->interpolation = interpolation;
  private->unit          = unit;
  private->callback      = callback;
  private->user_data     = user_data;

  gimp_image_get_resolution (image, &xres, &yres);

  dialog = gimp_viewable_dialog_new (g_list_prepend (NULL, viewable), context,
                                     title, role, GIMP_ICON_OBJECT_SCALE, title,
                                     parent,
                                     help_func, help_id,

                                     _("_Reset"),  RESPONSE_RESET,
                                     _("_Cancel"), GTK_RESPONSE_CANCEL,
                                     _("_Scale"),  GTK_RESPONSE_OK,

                                     NULL);

  gimp_dialog_set_alternative_button_order (GTK_DIALOG (dialog),
                                           RESPONSE_RESET,
                                           GTK_RESPONSE_OK,
                                           GTK_RESPONSE_CANCEL,
                                           -1);

  gtk_window_set_resizable (GTK_WINDOW (dialog), FALSE);

  g_object_weak_ref (G_OBJECT (dialog),
                     (GWeakNotify) scale_dialog_free, private);

  g_signal_connect (dialog, "response",
                    G_CALLBACK (scale_dialog_response),
                    private);

  private->box = g_object_new (GIMP_TYPE_SIZE_BOX,
                               "width",           width,
                               "height",          height,
                               "unit",            unit,
                               "xresolution",     xres,
                               "yresolution",     yres,
                               "resolution-unit", gimp_image_get_unit (image),
                               "keep-aspect",     TRUE,
                               "edit-resolution", GIMP_IS_IMAGE (viewable),
                               NULL);

  vbox = gtk_box_new (GTK_ORIENTATION_VERTICAL, 12);
  gtk_container_set_border_width (GTK_CONTAINER (vbox), 12);
  gtk_box_pack_start (GTK_BOX (gtk_dialog_get_content_area (GTK_DIALOG (dialog))),
                      vbox, TRUE, TRUE, 0);
  gtk_widget_set_visible (vbox, TRUE);

  frame = gimp_frame_new (text);
  gtk_box_pack_start (GTK_BOX (vbox), frame, FALSE, FALSE, 0);
  gtk_widget_set_visible (frame, TRUE);

  gtk_container_add (GTK_CONTAINER (frame), private->box);
  gtk_widget_set_visible (private->box, TRUE);

  frame = gimp_frame_new (_("Quality"));
  gtk_box_pack_start (GTK_BOX (vbox), frame, FALSE, FALSE, 0);
  gtk_widget_set_visible (frame, TRUE);

  vbox = gtk_box_new (GTK_ORIENTATION_VERTICAL, 12);
  gtk_container_add (GTK_CONTAINER (frame), vbox);
  gtk_widget_set_visible (vbox, TRUE);

  hbox = gtk_box_new (GTK_ORIENTATION_HORIZONTAL, 6);
  gtk_box_pack_start (GTK_BOX (vbox), hbox, FALSE, FALSE, 0);
  gtk_widget_set_visible (hbox, TRUE);

  label = gtk_label_new_with_mnemonic (_("I_nterpolation:"));
  gtk_box_pack_start (GTK_BOX (hbox), label, FALSE, FALSE, 0);
  gtk_widget_set_visible (label, TRUE);

  gtk_size_group_add_widget (GIMP_SIZE_BOX (private->box)->size_group, label);

  private->combo = gimp_enum_combo_box_new (GIMP_TYPE_INTERPOLATION_TYPE);
  gtk_label_set_mnemonic_widget (GTK_LABEL (label), private->combo);
  gtk_box_pack_start (GTK_BOX (hbox), private->combo, TRUE, TRUE, 0);
  gtk_widget_set_visible (private->combo, TRUE);

  gimp_int_combo_box_set_active (GIMP_INT_COMBO_BOX (private->combo),
                                 private->interpolation);

  return dialog;
}


/*  private functions  */

static void
scale_dialog_free (ScaleDialog *private)
{
  g_slice_free (ScaleDialog, private);
}

static void
scale_dialog_response (GtkWidget   *dialog,
                       gint         response_id,
                       ScaleDialog *private)
{
  GimpUnit *unit          = private->unit;
  gint      interpolation = private->interpolation;
  GimpUnit *resolution_unit;
  gint      width, height;
  gdouble   xres, yres;

  switch (response_id)
    {
    case RESPONSE_RESET:
      scale_dialog_reset (private);
      break;

    case GTK_RESPONSE_OK:
      g_object_get (private->box,
                    "width",           &width,
                    "height",          &height,
                    "unit",            &unit,
                    "xresolution",     &xres,
                    "yresolution",     &yres,
                    "resolution-unit", &resolution_unit,
                    NULL);

      gimp_int_combo_box_get_active (GIMP_INT_COMBO_BOX (private->combo),
                                     &interpolation);

      private->callback (dialog,
                         private->viewable,
                         width, height, unit, interpolation,
                         xres, yres, resolution_unit,
                         private->user_data);
      break;

    default:
      gtk_widget_destroy (dialog);
      break;
    }
}

static void
scale_dialog_reset (ScaleDialog *private)
{
  GimpImage *image;
  gint       width, height;
  gdouble    xres, yres;

  if (GIMP_IS_IMAGE (private->viewable))
    {
      image = GIMP_IMAGE (private->viewable);

      width  = gimp_image_get_width (image);
      height = gimp_image_get_height (image);
    }
  else if (GIMP_IS_ITEM (private->viewable))
    {
      GimpItem *item = GIMP_ITEM (private->viewable);

      image = gimp_item_get_image (item);

      width  = gimp_item_get_width  (item);
      height = gimp_item_get_height (item);
    }
  else
    {
      g_return_if_reached ();
    }

  gimp_image_get_resolution (image, &xres, &yres);

  g_object_set (private->box,
                "keep-aspect",     FALSE,
                NULL);

  g_object_set (private->box,
                "width",           width,
                "height",          height,
                "unit",            private->unit,
                NULL);

  g_object_set (private->box,
                "keep-aspect",     TRUE,
                "xresolution",     xres,
                "yresolution",     yres,
                "resolution-unit", gimp_image_get_unit (image),
                NULL);

  gimp_int_combo_box_set_active (GIMP_INT_COMBO_BOX (private->combo),
                                 private->interpolation);
}

/* --- stroke-dialog.c --- */
/* AmmoOS Image - The AmmoOS Field Image Research
 * Copyright (C) 1995 Spencer Kimball and Peter Mattis
 *
 * Copyright (C) 2003  Henrik Brix Andersen <brix@ammoos.org>
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

#include "libgimpconfig/gimpconfig.h"
#include "libgimpwidgets/gimpwidgets.h"

#include "dialogs-types.h"

#include "core/ammoos.h"
#include "core/gimpdrawable.h"
#include "core/gimpimage.h"
#include "core/gimppaintinfo.h"
#include "core/gimpstrokeoptions.h"
#include "core/gimptoolinfo.h"

#include "widgets/gimpcontainercombobox.h"
#include "widgets/gimpcontainerview.h"
#include "widgets/gimpviewabledialog.h"
#include "widgets/gimpstrokeeditor.h"

#include "stroke-dialog.h"

#include "ammoos-intl.h"


#define RESPONSE_RESET 1


typedef struct _StrokeDialog StrokeDialog;

struct _StrokeDialog
{
  GList              *items;
  GList              *drawables;
  GimpContext        *context;
  GimpStrokeOptions  *options;
  GimpStrokeCallback  callback;
  gpointer            user_data;

  GtkWidget          *tool_combo;
  GtkWidget          *stack;
};


/*  local function prototypes  */

static void  stroke_dialog_free        (StrokeDialog *private);
static void  stroke_dialog_response    (GtkWidget    *dialog,
                                        gint          response_id,
                                        StrokeDialog *private);
static void  stroke_dialog_expand_tabs (GtkWidget    *widget,
                                        gpointer      data);


/*  public function  */

GtkWidget *
stroke_dialog_new (GList              *items,
                   GList              *drawables,
                   GimpContext        *context,
                   const gchar        *title,
                   const gchar        *icon_name,
                   const gchar        *help_id,
                   GtkWidget          *parent,
                   GimpStrokeOptions  *options,
                   GimpStrokeCallback  callback,
                   gpointer            user_data)
{
  StrokeDialog *private;
  GimpImage    *image;
  GtkWidget    *dialog;
  GtkWidget    *main_vbox;
  GtkWidget    *switcher;
  GtkWidget    *stack;
  GtkWidget    *frame;

  g_return_val_if_fail (items, NULL);
  g_return_val_if_fail (drawables, NULL);
  g_return_val_if_fail (GIMP_IS_CONTEXT (context), NULL);
  g_return_val_if_fail (icon_name != NULL, NULL);
  g_return_val_if_fail (help_id != NULL, NULL);
  g_return_val_if_fail (parent == NULL || GTK_IS_WIDGET (parent), NULL);
  g_return_val_if_fail (callback != NULL, NULL);

  image = gimp_item_get_image (items->data);

  private = g_slice_new0 (StrokeDialog);

  private->items     = g_list_copy (items);
  private->drawables = g_list_copy (drawables);
  private->context   = context;
  private->options   = gimp_stroke_options_new (context->ammoos, context, TRUE);
  private->callback  = callback;
  private->user_data = user_data;

  gimp_config_sync (G_OBJECT (options),
                    G_OBJECT (private->options), 0);

  dialog = gimp_viewable_dialog_new (g_list_copy (items), context,
                                     title, "ammoos-stroke-options",
                                     icon_name,
                                     _("Choose Stroke Style"),
                                     parent,
                                     gimp_standard_help_func,
                                     help_id,

                                     _("_Reset"),  RESPONSE_RESET,
                                     _("_Cancel"), GTK_RESPONSE_CANCEL,
                                     _("_Stroke"), GTK_RESPONSE_OK,

                                     NULL);

  gimp_dialog_set_alternative_button_order (GTK_DIALOG (dialog),
                                           RESPONSE_RESET,
                                           GTK_RESPONSE_OK,
                                           GTK_RESPONSE_CANCEL,
                                           -1);

  gtk_window_set_resizable (GTK_WINDOW (dialog), FALSE);

  g_object_weak_ref (G_OBJECT (dialog),
                     (GWeakNotify) stroke_dialog_free, private);

  g_signal_connect (dialog, "response",
                    G_CALLBACK (stroke_dialog_response),
                    private);

  main_vbox = gtk_box_new (GTK_ORIENTATION_VERTICAL, 12);
  gtk_container_set_border_width (GTK_CONTAINER (main_vbox), 12);
  gtk_box_pack_start (GTK_BOX (gtk_dialog_get_content_area (GTK_DIALOG (dialog))),
                      main_vbox, TRUE, TRUE, 0);
  gtk_widget_set_visible (main_vbox, TRUE);


  /* switcher */

  switcher = gtk_stack_switcher_new ();
  gtk_box_pack_start (GTK_BOX (main_vbox), switcher, TRUE, TRUE, 0);
  gtk_widget_set_visible (switcher, TRUE);

  stack = gtk_stack_new ();
  gtk_stack_switcher_set_stack (GTK_STACK_SWITCHER (switcher),
                                GTK_STACK (stack));
  gtk_box_pack_start (GTK_BOX (main_vbox), stack, TRUE, TRUE, 0);
  gtk_widget_set_visible (stack, TRUE);

  /*  the stroke frame  */

  frame = gimp_frame_new (NULL);
  gtk_stack_add_titled (GTK_STACK (stack),
                        frame,
                        "stroke-tool",
                        _("Line"));
  gtk_widget_set_visible (frame, TRUE);

  {
    GtkWidget *stroke_editor;
    gdouble    xres;
    gdouble    yres;

    gimp_image_get_resolution (image, &xres, &yres);

    stroke_editor = gimp_stroke_editor_new (private->options, yres, FALSE,
                                            FALSE);
    gtk_container_add (GTK_CONTAINER (frame), stroke_editor);
    gtk_widget_set_visible (stroke_editor, TRUE);

  }


  /*  the paint tool frame  */

  frame = gimp_frame_new (NULL);
  gtk_stack_add_titled (GTK_STACK (stack),
                        frame,
                        "paint-tool",
                        _("Paint tool"));
  gtk_widget_set_visible (frame, TRUE);

  {
    GtkWidget *vbox;
    GtkWidget *hbox;
    GtkWidget *label;
    GtkWidget *combo;
    GtkWidget *button;

    vbox = gtk_box_new (GTK_ORIENTATION_VERTICAL, 6);
    gtk_container_add (GTK_CONTAINER (frame), vbox);
    gtk_widget_set_visible (vbox, TRUE);

    hbox = gtk_box_new (GTK_ORIENTATION_HORIZONTAL, 6);
    gtk_box_pack_start (GTK_BOX (vbox), hbox, FALSE, FALSE, 0);
    gtk_widget_set_visible (hbox, TRUE);

    label = gtk_label_new_with_mnemonic (_("P_aint tool:"));
    gtk_box_pack_start (GTK_BOX (hbox), label, FALSE, FALSE, 0);
    gtk_widget_set_visible (label, TRUE);

    combo = gimp_container_combo_box_new (image->ammoos->paint_info_list,
                                          GIMP_CONTEXT (private->options),
                                          16, 0);
    gtk_box_pack_start (GTK_BOX (hbox), combo, TRUE, TRUE, 0);
    gtk_widget_set_visible (combo, TRUE);

    switch (gimp_stroke_options_get_method (private->options))
      {
      case GIMP_STROKE_LINE:
        gtk_stack_set_visible_child_name (GTK_STACK (stack), "stroke-tool");
        break;
      case GIMP_STROKE_PAINT_METHOD:
        gtk_stack_set_visible_child_name (GTK_STACK (stack), "paint-tool");
        break;
      }

    private->stack      = stack;
    private->tool_combo = combo;

    button = gimp_prop_check_button_new (G_OBJECT (private->options),
                                         "emulate-brush-dynamics",
                                         _("_Emulate brush dynamics"));
    gtk_box_pack_start (GTK_BOX (vbox), button, FALSE, FALSE, 0);
  }

  /* Setting hexpand property of all tabs to true */
  gtk_container_foreach (GTK_CONTAINER (switcher),
                         stroke_dialog_expand_tabs,
                         NULL);

  return dialog;
}


/*  private functions  */

static void
stroke_dialog_free (StrokeDialog *private)
{
  g_object_unref (private->options);
  g_list_free (private->drawables);
  g_list_free (private->items);

  g_slice_free (StrokeDialog, private);
}

static void
stroke_dialog_response (GtkWidget    *dialog,
                        gint          response_id,
                        StrokeDialog *private)
{
  switch (response_id)
    {
    case RESPONSE_RESET:
      {
        GimpToolInfo *tool_info = gimp_context_get_tool (private->context);

        gimp_config_reset (GIMP_CONFIG (private->options));

        gimp_container_view_set_1_selected (GIMP_CONTAINER_VIEW (private->tool_combo),
                                            GIMP_VIEWABLE (tool_info->paint_info));

      }
      break;

    case GTK_RESPONSE_OK:
      {
        gint        stroke_type;
        GValue      value = G_VALUE_INIT;
        GParamSpec *pspec;

        if (g_strcmp0 (gtk_stack_get_visible_child_name (GTK_STACK (private->stack)),
                       "stroke-tool") == 0)
          stroke_type = GIMP_STROKE_LINE;
        else
          stroke_type = GIMP_STROKE_PAINT_METHOD;

        pspec = g_object_class_find_property (G_OBJECT_GET_CLASS (G_OBJECT (private->options)),
                                              "method");
        if (pspec == NULL)
          {
            gtk_widget_destroy (dialog);
            return;
          }

        g_value_init (&value, pspec->value_type);
        g_value_set_enum (&value, stroke_type);

        g_object_set_property (G_OBJECT (private->options), "method", &value);

        private->callback (dialog,
                           private->items,
                           private->drawables,
                           private->context,
                           private->options,
                           private->user_data);
      }
      break;

    default:
      gtk_widget_destroy (dialog);
      break;
    }
}

static void
stroke_dialog_expand_tabs (GtkWidget *widget, gpointer data)
{
  gtk_widget_set_hexpand (widget, TRUE);
}

/* --- template-options-dialog.c --- */
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

#include "libgimpconfig/gimpconfig.h"
#include "libgimpwidgets/gimpwidgets.h"

#include "dialogs-types.h"

#include "config/gimpcoreconfig.h"

#include "core/ammoos.h"
#include "core/gimpcontext.h"
#include "core/gimptemplate.h"

#include "widgets/gimptemplateeditor.h"
#include "widgets/gimpviewabledialog.h"

#include "template-options-dialog.h"

#include "ammoos-intl.h"


typedef struct _TemplateOptionsDialog TemplateOptionsDialog;

struct _TemplateOptionsDialog
{
  GimpTemplate                *template;
  GimpContext                 *context;
  GimpTemplateOptionsCallback  callback;
  gpointer                     user_data;

  GtkWidget                   *editor;
};


/*  local function prototypes  */

static void   template_options_dialog_free     (TemplateOptionsDialog *private);
static void   template_options_dialog_response (GtkWidget             *dialog,
                                                gint                   response_id,
                                                TemplateOptionsDialog *private);


/*  public function  */

GtkWidget *
template_options_dialog_new (GimpTemplate *template,
                             GimpContext  *context,
                             GtkWidget    *parent,
                             const gchar  *title,
                             const gchar  *role,
                             const gchar  *icon_name,
                             const gchar  *desc,
                             const gchar  *help_id,
                             GimpTemplateOptionsCallback  callback,
                             gpointer                     user_data)
{
  TemplateOptionsDialog *private;
  GtkWidget             *dialog;
  GimpViewable          *viewable = NULL;
  GtkWidget             *vbox;

  g_return_val_if_fail (template == NULL || GIMP_IS_TEMPLATE (template), NULL);
  g_return_val_if_fail (GIMP_IS_CONTEXT (context), NULL);
  g_return_val_if_fail (GTK_IS_WIDGET (parent), NULL);
  g_return_val_if_fail (title != NULL, NULL);
  g_return_val_if_fail (role != NULL, NULL);
  g_return_val_if_fail (icon_name != NULL, NULL);
  g_return_val_if_fail (desc != NULL, NULL);
  g_return_val_if_fail (help_id != NULL, NULL);
  g_return_val_if_fail (callback != NULL, NULL);

  private = g_slice_new0 (TemplateOptionsDialog);

  private->template  = template;
  private->context   = context;
  private->callback  = callback;
  private->user_data = user_data;

  if (template)
    {
      viewable = GIMP_VIEWABLE (template);
      template = gimp_config_duplicate (GIMP_CONFIG (template));
    }
  else
    {
      template =
        gimp_config_duplicate (GIMP_CONFIG (context->ammoos->config->default_image));
      viewable = GIMP_VIEWABLE (template);

      gimp_object_set_static_name (GIMP_OBJECT (template), _("Unnamed"));
    }

  dialog = gimp_viewable_dialog_new (g_list_prepend (NULL, viewable), context,
                                     title, role, icon_name, desc,
                                     parent,
                                     gimp_standard_help_func, help_id,

                                     _("_Cancel"), GTK_RESPONSE_CANCEL,
                                     _("_OK"),     GTK_RESPONSE_OK,

                                     NULL);

  gimp_dialog_set_alternative_button_order (GTK_DIALOG (dialog),
                                           GTK_RESPONSE_OK,
                                           GTK_RESPONSE_CANCEL,
                                           -1);

  gtk_window_set_resizable (GTK_WINDOW (dialog), FALSE);

  g_object_weak_ref (G_OBJECT (dialog),
                     (GWeakNotify) template_options_dialog_free, private);

  g_signal_connect (dialog, "response",
                    G_CALLBACK (template_options_dialog_response),
                    private);

  vbox = gtk_box_new (GTK_ORIENTATION_VERTICAL, 12);
  gtk_container_set_border_width (GTK_CONTAINER (vbox), 12);
  gtk_box_pack_start (GTK_BOX (gtk_dialog_get_content_area (GTK_DIALOG (dialog))),
                      vbox, TRUE, TRUE, 0);
  gtk_widget_set_visible (vbox, TRUE);

  private->editor = gimp_template_editor_new (template, context->ammoos, TRUE);
  gtk_box_pack_start (GTK_BOX (vbox), private->editor, FALSE, FALSE, 0);
  gtk_widget_set_visible (private->editor, TRUE);

  g_object_unref (template);

  return dialog;
}


/*  private functions  */

static void
template_options_dialog_free (TemplateOptionsDialog *private)
{
  g_slice_free (TemplateOptionsDialog, private);
}

static void
template_options_dialog_response (GtkWidget             *dialog,
                                  gint                   response_id,
                                  TemplateOptionsDialog *private)
{
  if (response_id == GTK_RESPONSE_OK)
    {
      GimpTemplateEditor *editor = GIMP_TEMPLATE_EDITOR (private->editor);

      private->callback (dialog,
                         private->template,
                         gimp_template_editor_get_template (editor),
                         private->context,
                         private->user_data);
    }
  else
    {
      gtk_widget_destroy (dialog);
    }
}

/* --- tips-dialog.c --- */
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

#include "libgimpbase/gimpbase.h"
#include "libgimpwidgets/gimpwidgets.h"

#include "dialogs-types.h"

#include "config/gimpguiconfig.h"

#include "core/ammoos.h"

#include "widgets/gimphelp-ids.h"

#include "tips-dialog.h"
#include "tips-parser.h"

#include "ammoos-intl.h"

enum
{
  RESPONSE_PREVIOUS = 1,
  RESPONSE_NEXT     = 2
};

static void     tips_dialog_set_tip  (GimpTip       *tip);
static void     tips_dialog_response (GtkWidget     *dialog,
                                      gint           response);
static void     tips_dialog_destroy  (GtkWidget     *widget,
                                      GimpGuiConfig *config);
static gboolean more_button_clicked  (GtkWidget     *button,
                                      Gimp          *ammoos);


static GtkWidget *tips_dialog = NULL;
static GtkWidget *tip_label   = NULL;
static GtkWidget *more_button = NULL;
static GList     *tips        = NULL;
static GList     *current_tip = NULL;


GtkWidget *
tips_dialog_create (Gimp *ammoos)
{
  GimpGuiConfig *config;
  GtkWidget     *vbox;
  GtkWidget     *hbox;
  GtkWidget     *button;
  GtkWidget     *image;
  gint           tips_count;

  g_return_val_if_fail (GIMP_IS_GIMP (ammoos), NULL);

  if (!tips)
    {
      GError *error = NULL;
      GFile  *file;

      file = gimp_data_directory_file ("tips", "ammoos-tips.xml", NULL);

      tips = gimp_tips_from_file (file, &error);

      if (! tips)
        {
          GimpTip *tip;

          if (! error)
            {
              tip = gimp_tip_new (_("The AmmoOS Image tips file is empty!"), NULL);
            }
          else if (error->code == G_FILE_ERROR_NOENT)
            {
              tip = gimp_tip_new (_("The AmmoOS Image tips file appears to be "
                                    "missing!"),
                                  _("There should be a file called '%s'. "
                                    "Please check your installation."),
                                  gimp_file_get_utf8_name (file));
            }
          else
            {
              tip = gimp_tip_new (_("The AmmoOS Image tips file could not be parsed!"),
                                  "%s", error->message);
            }

          tips = g_list_prepend (tips, tip);
        }
      else if (error)
        {
          g_printerr ("Error while parsing '%s': %s\n",
                      gimp_file_get_utf8_name (file), error->message);
        }

      g_clear_error (&error);
      g_object_unref (file);
    }

  tips_count = g_list_length (tips);

  config = GIMP_GUI_CONFIG (ammoos->config);

  if (config->last_tip_shown >= tips_count || config->last_tip_shown < 0)
    config->last_tip_shown = 0;

  current_tip = g_list_nth (tips, config->last_tip_shown);

  if (tips_dialog)
    return tips_dialog;

  tips_dialog = gimp_dialog_new (_("AmmoOS Image Tip of the Day"),
                                 "ammoos-tip-of-the-day",
                                 NULL, 0, gimp_standard_help_func,
                                 GIMP_HELP_TIPS_DIALOG,
                                 NULL);

  button = gtk_dialog_add_button (GTK_DIALOG (tips_dialog),
                                  _("_Previous Tip"), RESPONSE_PREVIOUS);
  image = gtk_image_new_from_icon_name (GIMP_ICON_GO_PREVIOUS,
                                        GTK_ICON_SIZE_BUTTON);
  gtk_button_set_image (GTK_BUTTON (button), image);
  gtk_widget_set_visible (image, TRUE);

  button = gtk_dialog_add_button (GTK_DIALOG (tips_dialog),
                                  _("_Next Tip"), RESPONSE_NEXT);
  image = gtk_image_new_from_icon_name (GIMP_ICON_GO_NEXT,
                                        GTK_ICON_SIZE_BUTTON);
  gtk_button_set_image (GTK_BUTTON (button), image);
  gtk_widget_set_visible (image, TRUE);

  gtk_dialog_set_response_sensitive (GTK_DIALOG (tips_dialog),
                                     RESPONSE_NEXT, tips_count > 1);
  gtk_dialog_set_response_sensitive (GTK_DIALOG (tips_dialog),
                                     RESPONSE_PREVIOUS, tips_count > 1);

  g_signal_connect (tips_dialog, "response",
                    G_CALLBACK (tips_dialog_response),
                    NULL);
  g_signal_connect (tips_dialog, "destroy",
                    G_CALLBACK (tips_dialog_destroy),
                    config);

  vbox = gtk_box_new (GTK_ORIENTATION_VERTICAL, 12);
  gtk_container_set_border_width (GTK_CONTAINER (vbox), 12);
  gtk_box_pack_start (GTK_BOX (gtk_dialog_get_content_area (GTK_DIALOG (tips_dialog))),
                      vbox, TRUE, TRUE, 0);
  gtk_widget_set_visible (vbox, TRUE);

  hbox = gtk_box_new (GTK_ORIENTATION_HORIZONTAL, 6);
  gtk_container_set_border_width (GTK_CONTAINER (hbox), 6);
  gtk_box_pack_start (GTK_BOX (vbox), hbox, TRUE, TRUE, 0);
  gtk_widget_set_visible (hbox, TRUE);

  vbox = gtk_box_new (GTK_ORIENTATION_VERTICAL, 6);
  gtk_box_pack_start (GTK_BOX (hbox), vbox, TRUE, TRUE, 0);
  gtk_widget_set_visible (vbox, TRUE);

  image = gtk_image_new_from_icon_name (GIMP_ICON_DIALOG_INFORMATION,
                                        GTK_ICON_SIZE_DIALOG);
  gtk_widget_set_valign (image, GTK_ALIGN_START);
  gtk_box_pack_start (GTK_BOX (hbox), image, FALSE, FALSE, 0);
  gtk_widget_set_visible (image, TRUE);

  tip_label = gtk_label_new (NULL);
  gtk_label_set_max_width_chars (GTK_LABEL (tip_label), 70);
  gtk_label_set_selectable (GTK_LABEL (tip_label), TRUE);
  gtk_label_set_justify (GTK_LABEL (tip_label), GTK_JUSTIFY_LEFT);
  gtk_label_set_line_wrap (GTK_LABEL (tip_label), TRUE);
  gtk_label_set_yalign (GTK_LABEL (tip_label), 0.0);
  gtk_box_pack_start (GTK_BOX (vbox), tip_label, TRUE, TRUE, 0);
  gtk_widget_set_visible (tip_label, TRUE);

  hbox = gtk_box_new (GTK_ORIENTATION_HORIZONTAL, 0);
  gtk_box_pack_start (GTK_BOX (vbox), hbox, FALSE, FALSE, 0);
  gtk_widget_set_visible (hbox, TRUE);

  more_button = gtk_link_button_new_with_label ("https://docs.ammoos.org/",
  /*  a link to the related section in the user manual  */
                                                _("Learn more"));
  gtk_widget_set_visible (more_button, TRUE);
  gtk_box_pack_start (GTK_BOX (hbox), more_button, FALSE, FALSE, 0);

  g_signal_connect (more_button, "activate-link",
                    G_CALLBACK (more_button_clicked),
                    ammoos);

  tips_dialog_set_tip (current_tip->data);

  return tips_dialog;
}

static void
tips_dialog_destroy (GtkWidget     *widget,
                     GimpGuiConfig *config)
{
  /* the last-shown-tip is saved in sessionrc */
  config->last_tip_shown = g_list_position (tips, current_tip);

  tips_dialog = NULL;
  current_tip = NULL;

  gimp_tips_free (tips);
  tips = NULL;
}

static void
tips_dialog_response (GtkWidget *dialog,
                      gint       response)
{
  switch (response)
    {
    case RESPONSE_PREVIOUS:
      current_tip = current_tip->prev ? current_tip->prev : g_list_last (tips);
      tips_dialog_set_tip (current_tip->data);
      break;

    case RESPONSE_NEXT:
      current_tip = current_tip->next ? current_tip->next : tips;
      tips_dialog_set_tip (current_tip->data);
      break;

    default:
      gtk_widget_destroy (dialog);
      break;
    }
}

static void
tips_dialog_set_tip (GimpTip *tip)
{
  g_return_if_fail (tip != NULL);

  gtk_label_set_markup (GTK_LABEL (tip_label), tip->text);

  /*  set the URI to unset the "visited" state  */
  gtk_link_button_set_uri (GTK_LINK_BUTTON (more_button),
                           "https://docs.ammoos.org/");

  gtk_widget_set_sensitive (more_button, tip->help_id != NULL);
}

static gboolean
more_button_clicked (GtkWidget *button,
                     Gimp      *ammoos)
{
  GimpTip *tip = current_tip->data;

  if (tip->help_id)
    gimp_help (ammoos, NULL, NULL, tip->help_id);

  /* Do not run the link set at construction. */
  return TRUE;
}

/* --- tips-parser.c --- */
/* AmmoOS Image - The AmmoOS Field Image Research
 * Copyright (C) 1995 Spencer Kimball and Peter Mattis
 *
 * tips-parser.c - Parse the ammoos-tips.xml file.
 * Copyright (C) 2002, 2008  Sven Neumann <sven@ammoos.org>
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

#include <gio/gio.h>

#include "config/config-types.h"
#include "config/gimpxmlparser.h"

#include "tips-parser.h"

#include "ammoos-intl.h"


typedef enum
{
  TIPS_START,
  TIPS_IN_TIPS,
  TIPS_IN_TIP,
  TIPS_IN_THETIP,
  TIPS_IN_UNKNOWN
} TipsParserState;

typedef enum
{
  TIPS_LOCALE_NONE,
  TIPS_LOCALE_MATCH,
  TIPS_LOCALE_MISMATCH
} TipsParserLocaleState;

typedef struct
{
  TipsParserState        state;
  TipsParserState        last_known_state;
  const gchar           *locale;
  const gchar           *help_id;
  TipsParserLocaleState  locale_state;
  gint                   markup_depth;
  gint                   unknown_depth;
  GString               *value;
  GimpTip               *current_tip;
  GList                 *tips;
} TipsParser;


static void    tips_parser_start_element (GMarkupParseContext  *context,
                                          const gchar          *element_name,
                                          const gchar         **attribute_names,
                                          const gchar         **attribute_values,
                                          gpointer              user_data,
                                          GError              **error);
static void    tips_parser_end_element   (GMarkupParseContext  *context,
                                          const gchar          *element_name,
                                          gpointer              user_data,
                                          GError              **error);
static void    tips_parser_characters    (GMarkupParseContext  *context,
                                          const gchar          *text,
                                          gsize                 text_len,
                                          gpointer              user_data,
                                          GError              **error);

static void    tips_parser_start_markup   (TipsParser   *parser,
                                           const gchar  *markup_name);
static void    tips_parser_end_markup     (TipsParser   *parser,
                                           const gchar  *markup_name);
static void    tips_parser_start_unknown  (TipsParser   *parser);
static void    tips_parser_end_unknown    (TipsParser   *parser);

static gchar * tips_parser_parse_help_id  (TipsParser   *parser,
                                           const gchar **names,
                                           const gchar **values);

static void    tips_parser_parse_locale   (TipsParser   *parser,
                                           const gchar **names,
                                           const gchar **values);
static void    tips_parser_set_by_locale  (TipsParser   *parser,
                                           gchar       **dest);


static const GMarkupParser markup_parser =
{
  tips_parser_start_element,
  tips_parser_end_element,
  tips_parser_characters,
  NULL,  /*  passthrough  */
  NULL   /*  error        */
};


GimpTip *
gimp_tip_new (const gchar *title,
              const gchar *format,
              ...)
{
  GimpTip *tip = g_slice_new0 (GimpTip);
  GString *str = g_string_new (NULL);

  if (title)
    {
      g_string_append (str, "<b>");
      g_string_append (str, title);
      g_string_append (str, "</b>");

      if (format)
        g_string_append (str, "\n\n");
    }

  if (format)
    {
      va_list  args;

      va_start (args, format);
      g_string_append_vprintf (str, format, args);
      va_end (args);
    }

  tip->text = g_string_free (str, FALSE);

  return tip;
}

void
gimp_tip_free (GimpTip *tip)
{
  if (! tip)
    return;

  g_free (tip->text);
  g_free (tip->help_id);

  g_slice_free (GimpTip, tip);
}

/**
 * gimp_tips_from_file:
 * @file:  the tips file to parse
 * @error: return location for a #GError
 *
 * Reads a ammoos-tips XML file, creates a new #GimpTip for
 * each tip entry and returns a #GList of them. If a parser
 * error occurs at some point, the uncompleted list is
 * returned and @error is set (unless @error is %NULL).
 * The message set in @error contains a detailed description
 * of the problem.
 *
 * Returns: a #Glist of #GimpTips.
 **/
GList *
gimp_tips_from_file (GFile   *file,
                     GError **error)
{
  GimpXmlParser *xml_parser;
  TipsParser     parser = { 0, };
  const gchar   *tips_locale;
  GList         *tips   = NULL;

  g_return_val_if_fail (G_IS_FILE (file), NULL);
  g_return_val_if_fail (error == NULL || *error == NULL, NULL);

  parser.value = g_string_new (NULL);

  /* This is a special string to specify the language identifier to
     look for in the ammoos-tips.xml file. Please translate the C in it
     according to the name of the po file used for ammoos-tips.xml.
     E.g. for the german translation, that would be "tips-locale:de".
   */
  tips_locale = _("tips-locale:C");

  if (g_str_has_prefix (tips_locale, "tips-locale:"))
    {
      tips_locale += strlen ("tips-locale:");

      if (*tips_locale && *tips_locale != 'C')
        parser.locale = tips_locale;
    }
  else
    {
      g_warning ("Wrong translation for 'tips-locale:', fix the translation!");
    }

  xml_parser = gimp_xml_parser_new (&markup_parser, &parser);

  gimp_xml_parser_parse_gfile (xml_parser, file, error);

  gimp_xml_parser_free (xml_parser);

  tips = g_list_reverse (parser.tips);

  gimp_tip_free (parser.current_tip);
  g_string_free (parser.value, TRUE);

  return tips;
}

void
gimp_tips_free (GList *tips)
{
  GList *list;

  for (list = tips; list; list = list->next)
    gimp_tip_free (list->data);

  g_list_free (tips);
}

static void
tips_parser_start_element (GMarkupParseContext *context,
                           const gchar         *element_name,
                           const gchar        **attribute_names,
                           const gchar        **attribute_values,
                           gpointer             user_data,
                           GError             **error)
{
  TipsParser *parser = user_data;

  switch (parser->state)
    {
    case TIPS_START:
      if (strcmp (element_name, "ammoos-tips") == 0)
        {
          parser->state = TIPS_IN_TIPS;
        }
      else
        {
          tips_parser_start_unknown (parser);
        }
      break;

    case TIPS_IN_TIPS:
      if (strcmp (element_name, "tip") == 0)
        {
          parser->state = TIPS_IN_TIP;
          parser->current_tip = g_slice_new0 (GimpTip);
          parser->current_tip->help_id = tips_parser_parse_help_id (parser,
                                                                    attribute_names,
                                                                    attribute_values);
        }
      else
        {
          tips_parser_start_unknown (parser);
        }
      break;

    case TIPS_IN_TIP:
      if (strcmp (element_name, "thetip") == 0)
        {
          parser->state = TIPS_IN_THETIP;
          tips_parser_parse_locale (parser, attribute_names, attribute_values);
        }
      else
        {
          tips_parser_start_unknown (parser);
        }
      break;

    case TIPS_IN_THETIP:
      if (strcmp (element_name, "b"  ) == 0 ||
          strcmp (element_name, "big") == 0 ||
          strcmp (element_name, "tt" ) == 0)
        {
          tips_parser_start_markup (parser, element_name);
        }
      else
        {
          tips_parser_start_unknown (parser);
        }
      break;

    case TIPS_IN_UNKNOWN:
      tips_parser_start_unknown (parser);
      break;
    }
}

static void
tips_parser_end_element (GMarkupParseContext *context,
                         const gchar         *element_name,
                         gpointer             user_data,
                         GError             **error)
{
  TipsParser *parser = user_data;

  switch (parser->state)
    {
    case TIPS_START:
      g_warning ("%s: shouldn't get here", G_STRLOC);
      break;

    case TIPS_IN_TIPS:
      parser->state = TIPS_START;
      break;

    case TIPS_IN_TIP:
      parser->tips = g_list_prepend (parser->tips, parser->current_tip);
      parser->current_tip = NULL;
      parser->state = TIPS_IN_TIPS;
      break;

    case TIPS_IN_THETIP:
      if (parser->markup_depth == 0)
        {
          tips_parser_set_by_locale (parser, &parser->current_tip->text);
          g_string_truncate (parser->value, 0);
          parser->state = TIPS_IN_TIP;
        }
      else
        tips_parser_end_markup (parser, element_name);
      break;

    case TIPS_IN_UNKNOWN:
      tips_parser_end_unknown (parser);
      break;
    }
}

static void
tips_parser_characters (GMarkupParseContext *context,
                        const gchar         *text,
                        gsize                text_len,
                        gpointer             user_data,
                        GError             **error)
{
  TipsParser *parser = user_data;

  switch (parser->state)
    {
    case TIPS_IN_THETIP:
      if (parser->locale_state != TIPS_LOCALE_MISMATCH)
        {
          gint i;

          /* strip tabs, newlines and adjacent whitespace */
          for (i = 0; i < text_len; i++)
            {
              if (text[i] != ' ' &&
                  text[i] != '\t' && text[i] != '\n' && text[i] != '\r')
                {
                  g_string_append_c (parser->value, text[i]);
                }
              else if (parser->value->len > 0 &&
                       parser->value->str[parser->value->len - 1] != ' ')
                {
                  g_string_append_c (parser->value, ' ');
                }
            }
        }
      break;
    default:
      break;
    }
}

static void
tips_parser_start_markup (TipsParser  *parser,
                          const gchar *markup_name)
{
  parser->markup_depth++;
  g_string_append_printf (parser->value, "<%s>", markup_name);
}

static void
tips_parser_end_markup (TipsParser  *parser,
                        const gchar *markup_name)
{
  gimp_assert (parser->markup_depth > 0);

  parser->markup_depth--;
  g_string_append_printf (parser->value, "</%s>", markup_name);
}

static void
tips_parser_start_unknown (TipsParser *parser)
{
  if (parser->unknown_depth == 0)
    parser->last_known_state = parser->state;

  parser->state = TIPS_IN_UNKNOWN;
  parser->unknown_depth++;
}

static void
tips_parser_end_unknown (TipsParser *parser)
{
  gimp_assert (parser->unknown_depth > 0 && parser->state == TIPS_IN_UNKNOWN);

  parser->unknown_depth--;

  if (parser->unknown_depth == 0)
    parser->state = parser->last_known_state;
}

static gchar *
tips_parser_parse_help_id (TipsParser   *parser,
                           const gchar **names,
                           const gchar **values)
{
  while (*names && *values)
    {
      if (strcmp (*names, "help") == 0 && **values)
        return g_strdup (*values);

      names++;
      values++;
    }

  return NULL;
}

static void
tips_parser_parse_locale (TipsParser   *parser,
                          const gchar **names,
                          const gchar **values)
{
  parser->locale_state = TIPS_LOCALE_NONE;

  while (*names && *values)
    {
      if (strcmp (*names, "xml:lang") == 0 && **values)
        {
          parser->locale_state = (parser->locale &&
                                  strcmp (*values, parser->locale) == 0 ?
                                  TIPS_LOCALE_MATCH : TIPS_LOCALE_MISMATCH);
        }

      names++;
      values++;
    }
}

static void
tips_parser_set_by_locale (TipsParser  *parser,
                           gchar      **dest)
{
  switch (parser->locale_state)
    {
    case TIPS_LOCALE_NONE:
      if (!parser->locale)
        {
          g_free (*dest);
          *dest = g_strdup (parser->value->str);
        }
      else if (*dest == NULL)
        {
          *dest = g_strdup (parser->value->str);
        }
      break;

    case TIPS_LOCALE_MATCH:
      g_free (*dest);
      *dest = g_strdup (parser->value->str);
      break;

    case TIPS_LOCALE_MISMATCH:
      break;
    }
}


/* --- user-install-dialog.c --- */
/* AmmoOS Image - The AmmoOS Field Image Research
 * Copyright (C) 1995 Spencer Kimball and Peter Mattis
 *
 * user-install-dialog.c
 * Copyright (C) 2000-2006 Michael Natterer and Sven Neumann
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

#include "dialogs-types.h"

#include "core/ammoos-user-install.h"

#include "widgets/gimpmessagebox.h"
#include "widgets/gimpmessagedialog.h"

#include "user-install-dialog.h"

#include "ammoos-intl.h"


static GtkWidget * user_install_dialog_new (GimpUserInstall *install);
static void        user_install_dialog_log (const gchar     *message,
                                            gboolean         error,
                                            gpointer         data);


gboolean
user_install_dialog_run (GimpUserInstall *install)
{
  GtkWidget *dialog;
  gboolean   success;

  g_return_val_if_fail (install != NULL, FALSE);

  dialog = user_install_dialog_new (install);

  success = gimp_user_install_run (install,
                                   gtk_widget_get_scale_factor (dialog));

  if (! success)
    {
      g_signal_connect (dialog, "response",
                        G_CALLBACK (gtk_main_quit),
                        NULL);

      gtk_widget_set_visible (dialog, TRUE);

      gtk_main ();
    }

  gtk_widget_destroy (dialog);

  return success;
}

static GtkWidget *
user_install_dialog_new (GimpUserInstall *install)
{
  GtkWidget     *dialog;
  GtkWidget     *frame;
  GtkWidget     *scrolled;
  GtkTextBuffer *buffer;
  GtkWidget     *view;

  gimp_icons_init ();

  dialog = gimp_message_dialog_new (_("AmmoOS Image User Installation"),
                                    GIMP_ICON_WILBER_EEK,
                                    NULL, 0, NULL, NULL,

                                    _("_Quit"), GTK_RESPONSE_OK,

                                    NULL);

  gimp_message_box_set_primary_text (GIMP_MESSAGE_DIALOG (dialog)->box,
                                     _("User installation failed!"));
  gimp_message_box_set_text (GIMP_MESSAGE_DIALOG (dialog)->box,
                             _("The AmmoOS Image user installation failed; "
                               "see the log for details."));

  frame = gimp_frame_new (_("Installation Log"));
  gtk_container_set_border_width (GTK_CONTAINER (frame), 12);
  gtk_box_pack_start (GTK_BOX (gtk_dialog_get_content_area (GTK_DIALOG (dialog))),
                      frame, TRUE, TRUE, 0);
  gtk_widget_set_visible (frame, TRUE);

  scrolled = gtk_scrolled_window_new (NULL, NULL);
  gtk_scrolled_window_set_policy (GTK_SCROLLED_WINDOW (scrolled),
                                  GTK_POLICY_AUTOMATIC,
                                  GTK_POLICY_AUTOMATIC);
  gtk_container_add (GTK_CONTAINER (frame), scrolled);
  gtk_widget_set_visible (scrolled, TRUE);

  buffer = gtk_text_buffer_new (NULL);

  gtk_text_buffer_create_tag (buffer, "bold",
                              "weight", PANGO_WEIGHT_BOLD,
                              NULL);

  view = gtk_text_view_new_with_buffer (buffer);
  gtk_text_view_set_editable (GTK_TEXT_VIEW (view), FALSE);
  gtk_text_view_set_wrap_mode (GTK_TEXT_VIEW (view), GTK_WRAP_WORD);
  gtk_widget_set_size_request (view, -1, 200);
  gtk_container_add (GTK_CONTAINER (scrolled), view);
  gtk_widget_set_visible (view, TRUE);

  g_object_unref (buffer);

  gimp_user_install_set_log_handler (install, user_install_dialog_log, buffer);

  return dialog;
}

static void
user_install_dialog_log (const gchar *message,
                         gboolean     error,
                         gpointer     data)
{
  GtkTextBuffer *buffer = GTK_TEXT_BUFFER (data);
  GtkTextIter    cursor;

  gtk_text_buffer_get_end_iter (buffer, &cursor);

  if (error && message)
    {
      gtk_text_buffer_insert_with_tags_by_name (buffer, &cursor, message, -1,
                                                "bold", NULL);
    }
  else if (message)
    {
      gtk_text_buffer_insert (buffer, &cursor, message, -1);
    }

  gtk_text_buffer_insert (buffer, &cursor, "\n", -1);
}

/* --- welcome-dialog.c --- */
/* AmmoOS Image - The AmmoOS Field Image Research
 * Copyright (C) 1995 Spencer Kimball and Peter Mattis
 *
 * welcome-dialog.c
 * Copyright (C) 2022 Jehan
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

#include "libgimpbase/gimpbase.h"
#include "libgimpconfig/gimpconfig.h"
#include "libgimpwidgets/gimpwidgets.h"

#include "dialogs-types.h"

#include "config/gimprc.h"

#include "core/ammoos.h"
#include "core/gimpimagefile.h"

#include "file/file-open.h"

#include "widgets/gimpcontainerlistview.h"
#include "widgets/gimpcontainerview.h"
#include "widgets/gimpdialogfactory.h"
#include "widgets/gimphelp-ids.h"
#include "widgets/gimpprefsbox.h"
#include "widgets/gimpuimanager.h"
#include "widgets/gimpwidgets-utils.h"

#include "menus/menus.h"

#include "gui/icon-themes.h"

#include "file-open-dialog.h"
#include "ammoos-version.h"
#include "preferences-dialog-utils.h"
#include "welcome-dialog.h"
#include "welcome-dialog-data.h"

#include "ammoos-intl.h"


static GtkWidget * welcome_dialog_new                (Gimp          *ammoos,
                                                      GimpConfig    *config,
                                                      gboolean       show_welcome_page);
static void   welcome_dialog_response                (GtkWidget     *widget,
                                                      gint           response_id,
                                                      GtkWidget     *dialog);
static void   welcome_dialog_release_item_activated  (GtkListBox    *listbox,
                                                      GtkListBoxRow *row,
                                                      gpointer       user_data);
static void   welcome_add_link                       (GtkGrid        *grid,
                                                      GtkSizeGroup   *size_group,
                                                      gint            column,
                                                      gint           *row,
                                                      const gchar    *emoji,
                                                      const gchar    *title,
                                                      const gchar    *link);
static void   welcome_size_allocate                  (GtkWidget      *welcome_dialog,
                                                      GtkAllocation  *allocation,
                                                      gpointer        user_data);
static void   welcome_dialog_create_welcome_page     (Gimp           *ammoos,
                                                      GtkWidget      *welcome_dialog,
                                                      GtkWidget      *main_vbox);
static void   welcome_dialog_create_personalize_page (Gimp           *ammoos,
                                                      GimpConfig     *config,
                                                      GtkWidget      *welcome_dialog,
                                                      GtkWidget      *main_vbox);
static void   welcome_dialog_create_contribute_page  (Gimp           *ammoos,
                                                      GtkWidget      *welcome_dialog,
                                                      GtkWidget      *main_vbox);
static void   welcome_dialog_create_creation_page    (Gimp           *ammoos,
                                                      GimpConfig     *config,
                                                      GtkWidget      *welcome_dialog,
                                                      GtkWidget      *main_vbox);
static void   welcome_dialog_create_release_page     (Gimp           *ammoos,
                                                      GtkWidget      *welcome_dialog,
                                                      GtkWidget      *main_vbox);

static void   welcome_dialog_new_image_dialog        (GtkWidget      *button,
                                                      GtkWidget      *welcome_dialog);
static void   welcome_dialog_open_image_dialog       (GtkWidget      *button,
                                                      GtkWidget      *welcome_dialog);
static void   welcome_dialog_new_dialog_response     (GtkWidget      *dialog,
                                                      gint            response_id,
                                                      GtkWidget      *welcome_dialog);
static void   welcome_dialog_open_dialog_close       (GtkWidget      *dialog,
                                                      GtkWidget      *welcome_dialog);
static void   welcome_open_activated_callback        (GimpContainerView *view,
                                                      GimpViewable   *viewable,
                                                      GtkWidget      *welcome_dialog);
static void   welcome_open_images_callback           (GtkWidget      *button,
                                                      GimpContainerView *view);
static void   welcome_dialog_new_image_accelerator   (GtkAccelGroup  *accel_group,
                                                      GObject        *accelerator_widget,
                                                      guint           keyval,
                                                      GdkModifierType mods,
                                                      gpointer        user_data);
static void   welcome_dialog_open_image_dialog_accelerator
                                                     (GtkAccelGroup  *accel_group,
                                                      GObject        *accelerator_widget,
                                                      guint           keyval,
                                                      GdkModifierType mods,
                                                      gpointer        user_data);
static void   welcome_dialog_open_image_accelerator  (GtkAccelGroup  *accel_group,
                                                      GObject        *accelerator_widget,
                                                      guint           keyval,
                                                      GdkModifierType mods,
                                                      gpointer        user_data);

static gboolean welcome_scrollable_resize            (gpointer        data);


static GtkWidget *welcome_dialog;

GtkWidget *
welcome_dialog_create (Gimp     *ammoos,
                       gboolean  show_welcome_page)
{
  GimpConfig *config;
  GimpConfig *config_copy;
  GimpConfig *config_orig;

  g_return_val_if_fail (GIMP_IS_GIMP (ammoos), NULL);
  g_return_val_if_fail (GIMP_IS_CONFIG (ammoos->edit_config), NULL);

  if (welcome_dialog)
    return welcome_dialog;

  /*  turn off autosaving while the prefs dialog is open  */
  gimp_rc_set_autosave (GIMP_RC (ammoos->edit_config), FALSE);

  config       = GIMP_CONFIG (ammoos->edit_config);
  config_copy  = gimp_config_duplicate (config);
  config_orig  = gimp_config_duplicate (config);

  g_signal_connect_object (config, "notify",
                           G_CALLBACK (prefs_config_notify),
                           config_copy, 0);
  g_signal_connect_object (config_copy, "notify",
                           G_CALLBACK (prefs_config_copy_notify),
                           config, 0);

  g_set_weak_pointer (&welcome_dialog,
                      welcome_dialog_new (ammoos, config_copy, show_welcome_page));

  g_object_set_data (G_OBJECT (welcome_dialog), "ammoos", ammoos);

  g_object_set_data_full (G_OBJECT (welcome_dialog), "config-copy", config_copy,
                          (GDestroyNotify) g_object_unref);
  g_object_set_data_full (G_OBJECT (welcome_dialog), "config-orig", config_orig,
                          (GDestroyNotify) g_object_unref);

  gtk_style_context_add_class (gtk_widget_get_style_context (welcome_dialog),
                               "ammoos-welcome-dialog");

  return welcome_dialog;
}

static GtkWidget *
welcome_dialog_new (Gimp       *ammoos,
                    GimpConfig *config,
                    gboolean    show_welcome_page)
{
  GtkWidget      *dialog;
  GList          *windows;
  GtkWidget      *switcher;
  GtkWidget      *stack;
  GtkWidget      *tree_view;
  GtkTreeIter     top_iter;

  GtkWidget      *prefs_box;
  GtkWidget      *main_vbox;

  gchar          *title;

  GtkAccelGroup  *accel_group;
  guint           accel_key;
  GdkModifierType accel_mods;
  gchar         **accels;

  /* Translators: the %s string will be the version, e.g. "3.0". */
  title = g_strdup_printf (_("Welcome to AmmoOS Image %s"), GIMP_VERSION);
  windows = gimp_get_image_windows (ammoos);
  dialog = gimp_dialog_new (title,
                            "ammoos-welcome-dialog",
                            windows ?  windows->data : NULL,
                            0, gimp_standard_help_func,
                            GIMP_HELP_WELCOME_DIALOG,
                            _("_Close"), GTK_RESPONSE_CLOSE,
                            NULL);
  g_list_free (windows);
  gtk_window_set_position (GTK_WINDOW (dialog), GTK_WIN_POS_CENTER_ON_PARENT);
  g_free (title);

  gtk_widget_set_margin_start (GTK_WIDGET (gtk_dialog_get_content_area (GTK_DIALOG (dialog))), 0);
  gtk_widget_set_margin_end (GTK_WIDGET (gtk_dialog_get_content_area (GTK_DIALOG (dialog))), 0);

  g_signal_connect (dialog, "response",
                    G_CALLBACK (welcome_dialog_response),
                    dialog);

  /*****************/
  /* Page Switcher */
  /*****************/
  switcher  = gtk_stack_switcher_new ();
  prefs_box = gimp_prefs_box_new ();
  stack     = gimp_prefs_box_get_stack (GIMP_PREFS_BOX (prefs_box));

  gimp_prefs_box_set_header_visible (GIMP_PREFS_BOX (prefs_box), FALSE);
  gtk_stack_switcher_set_stack (GTK_STACK_SWITCHER (switcher),
                                GTK_STACK (stack));
  gtk_container_set_border_width (GTK_CONTAINER (switcher), 2);
  gtk_box_pack_start (GTK_BOX (gtk_dialog_get_content_area (GTK_DIALOG (dialog))),
                      switcher, FALSE, FALSE, 0);
  gtk_widget_set_halign (switcher, GTK_ALIGN_CENTER);
  gtk_widget_set_visible (switcher, TRUE);

  gtk_container_set_border_width (GTK_CONTAINER (prefs_box), 0);
  gtk_box_pack_start (GTK_BOX (gtk_dialog_get_content_area (GTK_DIALOG (dialog))),
                      prefs_box, TRUE, TRUE, 0);
  gtk_widget_set_visible (prefs_box, TRUE);

  tree_view = gimp_prefs_box_get_tree_view (GIMP_PREFS_BOX (prefs_box));
  /* Hide the side panel selection since we're using GtkStackSwitcher */
  gtk_widget_set_visible (gtk_widget_get_parent (tree_view), FALSE);

  g_object_set_data (G_OBJECT (dialog), "prefs-box", prefs_box);

  main_vbox = gimp_prefs_box_add_page (GIMP_PREFS_BOX (prefs_box),
                                       "ammoos-wilber",
                                       _("Welcome"),
                                       _("Welcome"),
                                       "ammoos-welcome",
                                       NULL,
                                       &top_iter);
  gtk_widget_set_margin_top (main_vbox, 0);
  gtk_widget_set_margin_bottom (main_vbox, 0);
  gtk_widget_set_margin_start (main_vbox, 0);
  gtk_widget_set_margin_end (main_vbox, 0);

  welcome_dialog_create_welcome_page (ammoos, dialog, main_vbox);
  gtk_widget_set_visible (main_vbox, TRUE);

  main_vbox = gimp_prefs_box_add_page (GIMP_PREFS_BOX (prefs_box),
                                       "ammoos-wilber",
                                       _("Personalize"),
                                       _("Personalize"),
                                       "ammoos-welcome-personalize",
                                       NULL,
                                       &top_iter);
  gtk_container_set_border_width (GTK_CONTAINER (main_vbox), 12);

  welcome_dialog_create_personalize_page (ammoos, config, dialog, main_vbox);
  gtk_widget_set_visible (main_vbox, TRUE);

  main_vbox = gimp_prefs_box_add_page (GIMP_PREFS_BOX (prefs_box),
                                       "ammoos-wilber",
                                       _("Contribute"),
                                       _("Contribute"),
                                       "ammoos-welcome-contribute",
                                       NULL,
                                       &top_iter);
  gtk_container_set_border_width (GTK_CONTAINER (main_vbox), 12);

  welcome_dialog_create_contribute_page (ammoos, dialog, main_vbox);
  gtk_widget_set_visible (main_vbox, TRUE);

  main_vbox = gimp_prefs_box_add_page (GIMP_PREFS_BOX (prefs_box),
                                       "ammoos-wilber",
                                       _("Create"),
                                       _("Create"),
                                       "ammoos-welcome-create",
                                       NULL,
                                       &top_iter);
  gtk_container_set_border_width (GTK_CONTAINER (main_vbox), 12);

  welcome_dialog_create_creation_page (ammoos, config, dialog, main_vbox);
  gtk_widget_set_visible (main_vbox, TRUE);

  /* If dialog is set to always show on load, switch to the Create page */
  if (! show_welcome_page)
    gtk_stack_set_visible_child_name (GTK_STACK (stack), "ammoos-welcome-create");

  if (gimp_welcome_dialog_n_items > 0)
    {
      main_vbox = gimp_prefs_box_add_page (GIMP_PREFS_BOX (prefs_box),
                                           "ammoos-wilber",
                                           _("Release Notes"),
                                           _("Release Notes"),
                                           "ammoos-welcome-release_notes",
                                           NULL,
                                           &top_iter);
      gtk_container_set_border_width (GTK_CONTAINER (main_vbox), 12);

      welcome_dialog_create_release_page (ammoos, dialog, main_vbox);
      gtk_widget_set_visible (main_vbox, TRUE);
    }

  /*************/
  /* Shortcuts */
  /*************/
  /* XXX: GtkAccelGroup will be deprecated in GTK4
   * See: https://docs.gtk.org/gtk4/migrating-3to4.html#use-the-new-apis-for-keyboard-shortcuts
   * This GtkAccelGroup must be converted to a GtkShortcutController
   */
  accel_group = gtk_accel_group_new ();
  gtk_window_add_accel_group (GTK_WINDOW (dialog), accel_group);

  accels = gtk_application_get_accels_for_action (GTK_APPLICATION (ammoos->app),
                                                  "app.image-new");
  if (accels && accels[0])
    {
      gtk_accelerator_parse (accels[0], &accel_key, &accel_mods);
      gtk_accel_group_connect (accel_group,
                              accel_key, accel_mods, 0,
                              g_cclosure_new (G_CALLBACK (welcome_dialog_new_image_accelerator),
                                              dialog, NULL));
      g_strfreev (accels);
    }

  accels = gtk_application_get_accels_for_action (GTK_APPLICATION (ammoos->app),
                                                  "app.file-open");
  if (accels && accels[0])
    {
      gtk_accelerator_parse (accels[0], &accel_key, &accel_mods);
      gtk_accel_group_connect (accel_group,
                              accel_key, accel_mods, 0,
                              g_cclosure_new (G_CALLBACK (welcome_dialog_open_image_dialog_accelerator),
                                              dialog, NULL));
      g_strfreev (accels);
    }

  for (guint i = 0; i < 10; i++)
    {
      gchar accel_str[24];

      g_snprintf (accel_str, sizeof (accel_str), "app.file-open-recent-%02u", i + 1);
      accels = gtk_application_get_accels_for_action (GTK_APPLICATION (ammoos->app),
                                                      accel_str);
      if (accels && accels[0])
        {
          gtk_accelerator_parse (accels[0], &accel_key, &accel_mods);
          gtk_accel_group_connect (accel_group,
                                  accel_key, accel_mods, 0,
                                  g_cclosure_new (G_CALLBACK (welcome_dialog_open_image_accelerator),
                                                  GUINT_TO_POINTER (i), NULL));
          g_strfreev (accels);
        }
    }

  return dialog;
}

static void
welcome_dialog_response (GtkWidget *widget,
                         gint       response_id,
                         GtkWidget *dialog)
{
  Gimp    *ammoos = g_object_get_data (G_OBJECT (dialog), "ammoos");
  GObject *config_copy;
  GList   *restart_diff;
  GList   *confirm_diff;
  GList   *list;

  config_copy = g_object_get_data (G_OBJECT (dialog), "config-copy");

  /*  destroy config_orig  */
  g_object_set_data (G_OBJECT (dialog), "config-orig", NULL);

  gtk_widget_set_sensitive (GTK_WIDGET (dialog), FALSE);

  confirm_diff = gimp_config_diff (G_OBJECT (ammoos->edit_config),
                                   config_copy,
                                   GIMP_CONFIG_PARAM_CONFIRM);

  g_object_freeze_notify (G_OBJECT (ammoos->edit_config));

  for (list = confirm_diff; list; list = g_list_next (list))
    {
      GParamSpec *param_spec = list->data;
      GValue      value      = G_VALUE_INIT;

      g_value_init (&value, param_spec->value_type);

      g_object_get_property (config_copy,
                             param_spec->name, &value);
      g_object_set_property (G_OBJECT (ammoos->edit_config),
                             param_spec->name, &value);

      g_value_unset (&value);
    }

  g_object_thaw_notify (G_OBJECT (ammoos->edit_config));

  g_list_free (confirm_diff);

  gimp_rc_save (GIMP_RC (ammoos->edit_config));

  /*  spit out a solely informational warning about changed values
   *  which need restart
   */
  restart_diff = gimp_config_diff (G_OBJECT (ammoos->edit_config),
                                   G_OBJECT (ammoos->config),
                                   GIMP_CONFIG_PARAM_RESTART);

  if (restart_diff)
    {
      GString *string;

      string = g_string_new (_("You will have to restart AmmoOS Image for "
                               "the following changes to take effect:"));
      g_string_append (string, "\n\n");

      for (list = restart_diff; list; list = g_list_next (list))
        {
          GParamSpec *param_spec = list->data;

          /* The first 3 bytes are the bullet unicode character
           * for doing a list (U+2022).
           */
          g_string_append_printf (string, "\xe2\x80\xa2 %s\n", g_param_spec_get_nick (param_spec));
        }

      prefs_message (dialog, GTK_MESSAGE_INFO, FALSE, string->str);

      g_string_free (string, TRUE);
    }

  g_list_free (restart_diff);

  gtk_widget_destroy (dialog);
}

static void
welcome_dialog_create_welcome_page (Gimp      *ammoos,
                                    GtkWidget *welcome_dialog,
                                    GtkWidget *main_vbox)
{
  GtkWidget    *grid;
  GtkSizeGroup *size_group;
  GtkWidget    *image;
  GtkWidget    *widget;
  gchar        *markup;
  gchar        *tmp;
  gint          row;

  /****************/
  /* Welcome page */
  /****************/

  image = gtk_image_new_from_icon_name ("ammoos-wilber",
                                        GTK_ICON_SIZE_DIALOG);
  gtk_widget_set_valign (image, GTK_ALIGN_CENTER);
  gtk_box_pack_start (GTK_BOX (main_vbox), image, TRUE, TRUE, 0);
  gtk_widget_set_visible (image, TRUE);

  g_object_set_data (G_OBJECT (welcome_dialog), "welcome-vbox", main_vbox);
  g_signal_connect (welcome_dialog,
                    "size-allocate",
                    G_CALLBACK (welcome_size_allocate),
                    image);

  /* Welcome title. */
  grid = gtk_grid_new ();
  gtk_grid_set_column_homogeneous (GTK_GRID (grid), TRUE);
  gtk_grid_set_column_spacing (GTK_GRID (grid), 12);
  gtk_box_pack_start (GTK_BOX (main_vbox), grid, TRUE, TRUE, 0);
  gtk_widget_set_margin_start (GTK_WIDGET (grid), 12);
  gtk_widget_set_margin_end (GTK_WIDGET (grid), 12);
  gtk_widget_set_visible (grid, TRUE);

  /* Translators: the %s string will be the version, e.g. "3.0". */
  tmp = g_strdup_printf (_("You installed AmmoOS Image %s"), GIMP_VERSION);
  widget = gtk_label_new (NULL);
  /* XXX For GTK4, we may just replace with gtk_widget_add_css_class() AFAICS. */
  gtk_style_context_add_class (gtk_widget_get_style_context (widget), "title-3");
  gtk_label_set_text (GTK_LABEL (widget), tmp);
  g_free (tmp);
  gtk_label_set_justify (GTK_LABEL (widget), GTK_JUSTIFY_CENTER);
  gtk_label_set_line_wrap (GTK_LABEL (widget), FALSE);
  gtk_widget_set_margin_bottom (widget, 10);
  gtk_grid_attach (GTK_GRID (grid), widget, 0, 0, 2, 1);
  gtk_widget_set_visible (widget, TRUE);

  /* Welcome message: left */

  markup = _("AmmoOS Image is Free Software for image authoring and manipulation.\n"
             "Want to know more?");

  widget = gtk_label_new (NULL);
  gtk_label_set_max_width_chars (GTK_LABEL (widget), 30);
  /*gtk_widget_set_size_request (widget, max_width / 2, -1);*/
  gtk_label_set_line_wrap (GTK_LABEL (widget), TRUE);
  gtk_widget_set_vexpand (widget, FALSE);
  gtk_widget_set_hexpand (widget, FALSE);

  /* Making sure the labels are well top aligned to avoid some ugly
   * misalignment if left and right labels have different sizes,
   * but also left-aligned so that the messages are slightly to the left
   * of the emoji/link list below.
   * Following design decisions by Aryeom.
   */
  gtk_label_set_xalign (GTK_LABEL (widget), 0.0);
  gtk_label_set_yalign (GTK_LABEL (widget), 0.0);
  gtk_widget_set_margin_bottom (widget, 10);
  gtk_label_set_markup (GTK_LABEL (widget), markup);

  gtk_grid_attach (GTK_GRID (grid), widget, 0, 1, 1, 1);

  gtk_widget_set_visible (widget, TRUE);

  size_group = gtk_size_group_new (GTK_SIZE_GROUP_HORIZONTAL);

  row = 2;
  welcome_add_link (GTK_GRID (grid), size_group, 0, &row,
                    /* "globe with meridians" emoticone in UTF-8. */
                    "\xf0\x9f\x8c\x90",
                    _("AmmoOS Image website"), "https://www.ammoos.org/");
  welcome_add_link (GTK_GRID (grid), size_group, 0, &row,
                    /* "open book" emoticone in UTF-8. */
                    "\xf0\x9f\x93\x96",
                    _("Documentation"),
                    "https://docs.ammoos.org/");
  welcome_add_link (GTK_GRID (grid), size_group, 0, &row,
                    /* "graduation cap" emoticone in UTF-8. */
                    "\xf0\x9f\x8e\x93",
                    _("Community Tutorials"),
                    "https://www.ammoos.org/tutorials/");

  /* XXX: should we add API docs for plug-in developers once it's
   * properly set up? */

  /* Welcome message: right */

  markup = _("AmmoOS Image is Community Software under the GNU general public license v3.\n"
             "Want to contribute?");

  widget = gtk_label_new (NULL);
  gtk_label_set_line_wrap (GTK_LABEL (widget), TRUE);
  gtk_label_set_max_width_chars (GTK_LABEL (widget), 30);
  /*gtk_widget_set_size_request (widget, max_width / 2, -1);*/

  /* Again the alignments are important. */
  gtk_label_set_xalign (GTK_LABEL (widget), 0.0);
  gtk_widget_set_vexpand (widget, FALSE);
  gtk_widget_set_hexpand (widget, FALSE);
  gtk_label_set_xalign (GTK_LABEL (widget), 0.0);
  gtk_label_set_yalign (GTK_LABEL (widget), 0.0);
  gtk_widget_set_margin_bottom (widget, 10);
  gtk_label_set_markup (GTK_LABEL (widget), markup);

  gtk_grid_attach (GTK_GRID (grid), widget, 1, 1, 1, 1);

  gtk_widget_set_visible (widget, TRUE);

  row = 2;
  welcome_add_link (GTK_GRID (grid), size_group, 1, &row,
                    /* "keyboard" emoticone in UTF-8. */
                    "\xe2\x8c\xa8",
                    _("Contributing"),
                    "https://www.ammoos.org/develop/");
  welcome_add_link (GTK_GRID (grid), size_group, 1, &row,
                    /* "love letter" emoticone in UTF-8. */
                    "\xf0\x9f\x92\x8c",
                    _("Donating"),
                    "https://www.ammoos.org/donating/");

  g_object_unref (size_group);
}

static void
welcome_dialog_create_personalize_page (Gimp       *ammoos,
                                        GimpConfig *config,
                                        GtkWidget  *welcome_dialog,
                                        GtkWidget  *main_vbox)
{
  GtkSizeGroup *size_group = NULL;
  GtkWidget    *scale;
  GtkListStore *store;

  GtkWidget    *vbox;
  GtkWidget    *hbox;
  GtkWidget    *widget;
  GtkWidget    *button;
  GtkWidget    *grid;

  GObject      *object;

  gchar       **themes;
  gint          n_themes;

  object = G_OBJECT (config);

  size_group = gtk_size_group_new (GTK_SIZE_GROUP_HORIZONTAL);

  /* Themes */
  vbox = prefs_frame_new (_("Theme"), GTK_CONTAINER (main_vbox), FALSE);

  hbox = gtk_box_new (GTK_ORIENTATION_HORIZONTAL, 12);
  gtk_container_set_border_width (GTK_CONTAINER (hbox), 0);
  gtk_widget_set_halign (GTK_WIDGET (hbox), GTK_ALIGN_START);
  gtk_box_pack_start (GTK_BOX (vbox), hbox, FALSE, FALSE, 0);
  gtk_widget_set_visible (hbox, TRUE);

  grid = prefs_grid_new (GTK_CONTAINER (hbox));
  button = prefs_enum_combo_box_add (object, "theme-color-scheme",
                                     0, 0,
                                     _("Color scheme"), GTK_GRID (grid),
                                     0, size_group);

  hbox = gtk_box_new (GTK_ORIENTATION_HORIZONTAL, 12);
  gtk_container_set_border_width (GTK_CONTAINER (hbox), 0);
  gtk_widget_set_halign (GTK_WIDGET (hbox), GTK_ALIGN_START);
  gtk_box_pack_start (GTK_BOX (vbox), hbox, FALSE, FALSE, 0);
  gtk_widget_set_visible (hbox, TRUE);


  /* Icon Theme */
  store = gtk_list_store_new (2, G_TYPE_STRING, G_TYPE_STRING);
  themes = icon_themes_list_themes (ammoos, &n_themes);
  for (gint i = 0; i < n_themes; i++)
    gtk_list_store_insert_with_values (store, NULL,
                                       -1,
                                       0, themes[i],
                                       1, themes[i],
                                       -1);
  g_strfreev (themes);

  widget = gimp_prop_string_combo_box_new (object, "icon-theme",
                                           GTK_TREE_MODEL (store), 0, 1);
  gtk_widget_set_visible (widget, TRUE);

  grid = prefs_grid_new (GTK_CONTAINER (hbox));
  prefs_widget_add_aligned (widget, _("Icon theme"), GTK_GRID (grid), 0, FALSE,
                            size_group);
  g_object_unref (store);

  /* Reset size group for next set of widgets */
  g_clear_object (&size_group);
  size_group = gtk_size_group_new (GTK_SIZE_GROUP_HORIZONTAL);

  prefs_switch_add (object, "prefer-symbolic-icons",
                    _("Use symbolic icons if available"),
                    GTK_BOX (hbox), NULL, &button);
  gtk_widget_set_valign (button, GTK_ALIGN_CENTER);

  vbox = prefs_frame_new (_("Icon Scaling"), GTK_CONTAINER (main_vbox), FALSE);

  prefs_switch_add (object, "override-theme-icon-size",
                    _("_Override icon sizes set by the theme"),
                    GTK_BOX (vbox), NULL, &button);

  scale = gtk_scale_new_with_range (GTK_ORIENTATION_HORIZONTAL,
                                    0.0, 3.0, 1.0);
  /* 'draw_value' updates round_digits. So set it first. */
  gtk_scale_set_draw_value (GTK_SCALE (scale), FALSE);
  gtk_range_set_round_digits (GTK_RANGE (scale), 0.0);
  gtk_scale_add_mark (GTK_SCALE (scale), 0.0, GTK_POS_BOTTOM,
                      _("Small"));
  gtk_scale_add_mark (GTK_SCALE (scale), 1.0, GTK_POS_BOTTOM,
                      _("Medium"));
  gtk_scale_add_mark (GTK_SCALE (scale), 2.0, GTK_POS_BOTTOM,
                      _("Large"));
  gtk_scale_add_mark (GTK_SCALE (scale), 3.0, GTK_POS_BOTTOM,
                      _("Huge"));
  gtk_range_set_value (GTK_RANGE (scale),
                       (gdouble) GIMP_GUI_CONFIG (object)->custom_icon_size);
  g_signal_connect (G_OBJECT (scale), "value-changed",
                    G_CALLBACK (prefs_icon_size_value_changed),
                    GIMP_GUI_CONFIG (object));
  g_signal_connect (G_OBJECT (object), "notify::custom-icon-size",
                    G_CALLBACK (prefs_gui_config_notify_icon_size),
                    scale);
  gtk_box_pack_start (GTK_BOX (vbox), scale, FALSE, FALSE, 0);
  gtk_widget_set_visible (scale, TRUE);

  g_object_bind_property (button, "active",
                          scale,  "sensitive",
                          G_BINDING_SYNC_CREATE);

  vbox = prefs_frame_new (_("Font Scaling"), GTK_CONTAINER (main_vbox), FALSE);
  gimp_help_set_help_data (vbox,
                           _("Font scaling will not work with themes using absolute sizes."),
                           NULL);
  scale = gtk_scale_new_with_range (GTK_ORIENTATION_HORIZONTAL,
                                    50, 200, 10);
  gtk_scale_set_value_pos (GTK_SCALE (scale), GTK_POS_BOTTOM);
  gtk_scale_add_mark (GTK_SCALE (scale), 50.0, GTK_POS_BOTTOM,
                      _("50%"));
  gtk_scale_add_mark (GTK_SCALE (scale), 100.0, GTK_POS_BOTTOM,
                      _("100%"));
  gtk_scale_add_mark (GTK_SCALE (scale), 200.0, GTK_POS_BOTTOM,
                      _("200%"));
  gtk_range_set_value (GTK_RANGE (scale),
                       GIMP_GUI_CONFIG (object)->font_relative_size * 100.0);
  g_signal_connect (G_OBJECT (scale), "value-changed",
                    G_CALLBACK (prefs_font_size_value_changed),
                    GIMP_GUI_CONFIG (object));
  g_signal_connect (G_OBJECT (object), "notify::font-relative-size",
                    G_CALLBACK (prefs_gui_config_notify_font_size),
                    scale);
  gtk_box_pack_start (GTK_BOX (vbox), scale, FALSE, FALSE, 0);
  gtk_widget_set_visible (scale, TRUE);

#ifdef HAVE_ISO_CODES
  vbox = prefs_frame_new (_("GUI Language (requires restart)"),
                          GTK_CONTAINER (main_vbox), FALSE);
  prefs_language_combo_box_add (object, "language", GTK_BOX (vbox));
#endif

  vbox = prefs_frame_new (_("Additional Customizations"), GTK_CONTAINER (main_vbox), FALSE);

#ifndef GDK_WINDOWING_QUARTZ
  prefs_switch_add (object, "custom-title-bar",
                    _("Merge menu and title bar (requires restart)"),
                    GTK_BOX (vbox), size_group, NULL);
#endif

#ifdef CHECK_UPDATE
  if (gimp_version_check_update ())
    {
      prefs_switch_add (object, "check-updates",
                        _("Enable check for updates (requires internet)"),
                        GTK_BOX (vbox), size_group, NULL);
    }
#endif

  prefs_switch_add (object, "toolbox-groups",
                    _("Use tool _groups"),
                    GTK_BOX (vbox), size_group, NULL);

  g_clear_object (&size_group);
}

static void
welcome_dialog_create_creation_page (Gimp       *ammoos,
                                     GimpConfig *config,
                                     GtkWidget  *welcome_dialog,
                                     GtkWidget  *main_vbox)
{
  GtkWidget *vbox;
  GtkWidget *hbox;
  GtkWidget *button;
  GtkWidget *view;
  GtkWidget *toggle;

  hbox = gtk_box_new (GTK_ORIENTATION_HORIZONTAL, 6);
  gtk_box_set_homogeneous (GTK_BOX (hbox), TRUE);
  gtk_box_pack_start (GTK_BOX (main_vbox), hbox, FALSE, FALSE, 0);
  gtk_widget_set_visible (hbox, TRUE);

  vbox = prefs_frame_new (_("Create a New Image"), GTK_CONTAINER (hbox),
                          FALSE);

  button = gtk_button_new_with_mnemonic (_("C_reate"));
  /* Balancing the indent from the frame */
  gtk_widget_set_margin_end (button, 12);
  gtk_box_pack_start (GTK_BOX (vbox), button, FALSE, FALSE, 0);
  gtk_widget_set_visible (button, TRUE);
  g_signal_connect (button, "clicked",
                    G_CALLBACK (welcome_dialog_new_image_dialog),
                    welcome_dialog);

  vbox = prefs_frame_new (_("Open an Existing Image"), GTK_CONTAINER (hbox),
                          FALSE);

  button = gtk_button_new_with_mnemonic (_("_Open"));
  gtk_widget_set_margin_end (button, 12);
  gtk_box_pack_start (GTK_BOX (vbox), button, FALSE, FALSE, 0);
  gtk_widget_set_visible (button, TRUE);
  g_signal_connect (button, "clicked",
                    G_CALLBACK (welcome_dialog_open_image_dialog),
                    welcome_dialog);

  /* Recent Files */
  vbox = prefs_frame_new (_("Recent Images"), GTK_CONTAINER (main_vbox),
                          TRUE);

  view = gimp_container_list_view_new (ammoos->documents,
                                       gimp_get_user_context (ammoos),
                                       32, 0);
  gimp_container_view_set_selection_mode (GIMP_CONTAINER_VIEW (view),
                                          GTK_SELECTION_MULTIPLE);
  gtk_box_pack_start (GTK_BOX (vbox), view, TRUE, TRUE, 0);
  gtk_widget_set_visible (view, TRUE);

  g_signal_connect (view, "item-activated",
                    G_CALLBACK (welcome_open_activated_callback),
                    welcome_dialog);

  button = gtk_button_new_with_mnemonic (_("O_pen Selected Images"));
  gtk_box_pack_start (GTK_BOX (vbox), button, FALSE, FALSE, 0);
  gtk_widget_set_visible (button, TRUE);

  g_signal_connect (button, "clicked",
                    G_CALLBACK (welcome_open_images_callback),
                    view);

  /* "Always show welcome dialog" checkbox */
  toggle = prefs_check_button_add (G_OBJECT (config), "show-welcome-dialog",
                                   _("Show on Start "
                                     "(You can show the Welcome dialog again from the \"Help\" menu)"),
                                   GTK_BOX (main_vbox));
  gtk_container_child_set (GTK_CONTAINER (main_vbox), toggle,
                           "pack-type", GTK_PACK_END,
                           NULL);
}

static void
welcome_dialog_create_contribute_page (Gimp       *ammoos,
                                       GtkWidget  *welcome_dialog,
                                       GtkWidget  *main_vbox)
{
  GtkWidget *hbox;
  GtkWidget *vbox;
  GtkWidget *button;
  GtkWidget *label;
  gchar     *markup;
  gchar     *tmp;

  gtk_box_set_spacing (GTK_BOX (main_vbox), 12);

  hbox = gtk_box_new (GTK_ORIENTATION_HORIZONTAL, 6);
  gtk_box_pack_start (GTK_BOX (main_vbox), hbox, FALSE, FALSE, 0);
  gtk_widget_set_visible (hbox, TRUE);

  tmp = g_strdup_printf (_("Ways to contribute"));
  markup = g_strdup_printf ("<big>%s</big>", tmp);
  g_free (tmp);
  label = gtk_label_new (NULL);
  gtk_label_set_markup (GTK_LABEL (label), markup);
  g_free (markup);
  gtk_box_set_center_widget (GTK_BOX (hbox), label);
  gtk_widget_set_visible (label, TRUE);

  vbox = prefs_frame_new (_("Report Bugs"), GTK_CONTAINER (main_vbox), FALSE);

  label = gtk_label_new (_("As any application, AmmoOS Image is not bug-free, so "
                           "reporting bugs that you encounter is very "
                           "important to the development."));
  gtk_label_set_max_width_chars (GTK_LABEL (label), 30);
  gtk_label_set_line_wrap (GTK_LABEL (label), TRUE);
  gtk_label_set_xalign (GTK_LABEL (label), 0.0);
  gtk_box_pack_start (GTK_BOX (vbox), label, FALSE, FALSE, 0);
  gtk_widget_set_visible (label, TRUE);
  button = gtk_link_button_new_with_label ("https://www.ammoos.org/bugs/",
                                           _("Report Bugs"));
  gtk_box_pack_start (GTK_BOX (vbox), button, FALSE, FALSE, 0);
  gtk_widget_set_visible (button, TRUE);

  vbox = prefs_frame_new (_("Write Code"), GTK_CONTAINER (main_vbox), FALSE);

  label = gtk_label_new (_("Our Developer Website is where you want to start "
                           "learning about being a code contributor."));
  gtk_label_set_max_width_chars (GTK_LABEL (label), 30);
  gtk_label_set_line_wrap (GTK_LABEL (label), TRUE);
  gtk_label_set_xalign (GTK_LABEL (label), 0.0);
  gtk_box_pack_start (GTK_BOX (vbox), label, FALSE, FALSE, 0);
  gtk_widget_set_visible (label, TRUE);
  button = gtk_link_button_new_with_label ("https://developer.ammoos.org/",
                                           _("Write Code"));
  gtk_box_pack_start (GTK_BOX (vbox), button, FALSE, FALSE, 0);
  gtk_widget_set_visible (button, TRUE);

  vbox = prefs_frame_new (_("Translate"), GTK_CONTAINER (main_vbox), FALSE);

  label = gtk_label_new (_("Contact the respective translation team for your "
                           "language"));
  gtk_label_set_max_width_chars (GTK_LABEL (label), 30);
  gtk_label_set_line_wrap (GTK_LABEL (label), TRUE);
  gtk_label_set_xalign (GTK_LABEL (label), 0.0);
  gtk_box_pack_start (GTK_BOX (vbox), label, FALSE, FALSE, 0);
  gtk_widget_set_visible (label, TRUE);
  button = gtk_link_button_new_with_label ("https://l10n.gnome.org/teams/",
                                           _("Translate"));
  gtk_box_pack_start (GTK_BOX (vbox), button, FALSE, FALSE, 0);
  gtk_widget_set_visible (button, TRUE);

  vbox = prefs_frame_new (_("Donate"), GTK_CONTAINER (main_vbox), FALSE);

  label = gtk_label_new (_("Donating money is important: it makes AmmoOS Image "
                           "sustainable."));
  gtk_label_set_max_width_chars (GTK_LABEL (label), 30);
  gtk_label_set_line_wrap (GTK_LABEL (label), TRUE);
  gtk_label_set_xalign (GTK_LABEL (label), 0.0);
  gtk_box_pack_start (GTK_BOX (vbox), label, FALSE, FALSE, 0);
  gtk_widget_set_visible (label, TRUE);
  button = gtk_link_button_new_with_label ("https://liberapay.com/AmmoOS Image/donate",
                                           _("Donate via Liberapay"));
  gtk_box_pack_start (GTK_BOX (vbox), button, FALSE, FALSE, 0);
  gtk_widget_set_visible (button, TRUE);
  button = gtk_link_button_new_with_label ("https://www.ammoos.org/donating/",
                                           _("Other donation options"));
  gtk_box_pack_start (GTK_BOX (vbox), button, FALSE, FALSE, 0);
  gtk_widget_set_visible (button, TRUE);
}

static void
welcome_dialog_create_release_page (Gimp      *ammoos,
                                    GtkWidget *welcome_dialog,
                                    GtkWidget *main_vbox)
{
  GtkWidget  *scrolled_window;
  GtkWidget  *hbox;
  GtkWidget  *image;
  GtkWidget  *listbox;
  GtkWidget  *widget;

  gchar      *release_link;
  gchar      *markup;
  gchar      *tmp;

  /*****************/
  /* Release Notes */
  /*****************/
  if (gimp_welcome_dialog_n_items > 0)
    {
      gint n_demos = 0;

      /* Release note title. */
      hbox = gtk_box_new (GTK_ORIENTATION_HORIZONTAL, 6);
      gtk_container_set_border_width (GTK_CONTAINER (hbox), 6);
      gtk_box_pack_start (GTK_BOX (main_vbox), hbox, FALSE, FALSE, 0);
      gtk_widget_set_visible (hbox, TRUE);

      /* Translators: the %s string will be the version, e.g. "3.0". */
      tmp = g_strdup_printf (_("AmmoOS Image %s Release Notes"), GIMP_VERSION);
      markup = g_strdup_printf ("<b><big>%s</big></b>", tmp);
      g_free (tmp);
      widget = gtk_label_new (NULL);
      gtk_label_set_markup (GTK_LABEL (widget), markup);
      g_free (markup);
      gtk_label_set_selectable (GTK_LABEL (widget), FALSE);
      gtk_label_set_justify (GTK_LABEL (widget), GTK_JUSTIFY_CENTER);
      gtk_label_set_line_wrap (GTK_LABEL (widget), FALSE);
      gtk_box_pack_start (GTK_BOX (hbox), widget, TRUE, TRUE, 0);
      gtk_widget_set_visible (widget, TRUE);

      image = gtk_image_new_from_icon_name ("ammoos-user-manual",
                                            GTK_ICON_SIZE_DIALOG);
      gtk_widget_set_valign (image, GTK_ALIGN_START);
      gtk_box_pack_start (GTK_BOX (hbox), image, FALSE, FALSE, 0);
      gtk_widget_set_visible (image, TRUE);

      /* Release note introduction. */

      if (gimp_welcome_dialog_intro_n_paragraphs)
        {
          GString *introduction = NULL;

          for (gint i = 0; i < gimp_welcome_dialog_intro_n_paragraphs; i++)
            {
              if (i == 0)
                introduction = g_string_new (_(gimp_welcome_dialog_intro[i]));
              else
                g_string_append_printf (introduction, "\n%s",
                                        _(gimp_welcome_dialog_intro[i]));
            }
          widget = gtk_label_new (NULL);
          gtk_label_set_markup (GTK_LABEL (widget), introduction->str);
          gtk_label_set_max_width_chars (GTK_LABEL (widget), 70);
          gtk_label_set_selectable (GTK_LABEL (widget), FALSE);
          gtk_label_set_justify (GTK_LABEL (widget), GTK_JUSTIFY_LEFT);
          gtk_label_set_line_wrap (GTK_LABEL (widget), TRUE);
          gtk_box_pack_start (GTK_BOX (main_vbox), widget, FALSE, FALSE, 0);
          gtk_widget_set_visible (widget, TRUE);

          g_string_free (introduction, TRUE);
        }

      /* Release note's change items. */

      scrolled_window = gtk_scrolled_window_new (NULL, NULL);
      gtk_box_pack_start (GTK_BOX (main_vbox), scrolled_window, TRUE, TRUE, 0);
      gtk_widget_set_visible (scrolled_window, TRUE);

      listbox = gtk_list_box_new ();
      gtk_style_context_add_class (gtk_widget_get_style_context (GTK_WIDGET (listbox)),
                                   "view");

      for (gint i = 0; i < gimp_welcome_dialog_n_items; i++)
        {
          GtkWidget *row;
          gchar     *markup;
          gchar     *text;

          text = g_markup_escape_text (_((gchar *) gimp_welcome_dialog_items[i]), -1);

          /* Add a bold dot for pretty listing. */
          if (i < gimp_welcome_dialog_n_items &&
              gimp_welcome_dialog_demos[i] != NULL)
            {
              markup = g_strdup_printf ("<span weight='ultrabold'>\xe2\x96\xb6</span>  %s", text);
              n_demos++;
            }
          else
            {
              markup = g_strdup_printf ("<span weight='ultrabold'>\xe2\x80\xa2</span>  %s", text);
            }

          row = gtk_list_box_row_new ();
          widget = gtk_label_new (NULL);
          gtk_label_set_markup (GTK_LABEL (widget), markup);
          gtk_label_set_line_wrap (GTK_LABEL (widget), TRUE);
          gtk_label_set_line_wrap_mode (GTK_LABEL (widget), PANGO_WRAP_WORD);
          gtk_label_set_justify (GTK_LABEL (widget), GTK_JUSTIFY_LEFT);
          gtk_widget_set_halign (widget, GTK_ALIGN_START);
          gtk_label_set_xalign (GTK_LABEL (widget), 0.0);
          gtk_container_add (GTK_CONTAINER (row), widget);

          gtk_list_box_insert (GTK_LIST_BOX (listbox), row, -1);
          gtk_widget_show_all (row);

          g_free (markup);
          g_free (text);
        }
      gtk_container_add (GTK_CONTAINER (scrolled_window), listbox);
      gtk_list_box_set_selection_mode (GTK_LIST_BOX (listbox),
                                       GTK_SELECTION_NONE);

      g_signal_connect (listbox, "row-activated",
                        G_CALLBACK (welcome_dialog_release_item_activated),
                        ammoos);
      gtk_widget_set_visible (listbox, TRUE);

      if (n_demos > 0)
        {
          /* A small explicative string to help discoverability of the demo
           * ability.
           */
          hbox = gtk_box_new (GTK_ORIENTATION_HORIZONTAL, 0);
          gtk_box_pack_start (GTK_BOX (main_vbox), hbox, FALSE, FALSE, 0);
          gtk_widget_set_visible (hbox, TRUE);

          image = gtk_image_new_from_icon_name ("dialog-information",
                                                GTK_ICON_SIZE_MENU);
          gtk_widget_set_valign (image, GTK_ALIGN_CENTER);
          gtk_box_pack_start (GTK_BOX (hbox), image, FALSE, FALSE, 0);
          gtk_widget_set_visible (image, TRUE);

          widget = gtk_label_new (NULL);
          tmp = g_strdup_printf (_("Click on release items with a %s bullet point to get a tour."),
                                 "<span weight='ultrabold'>\xe2\x96\xb6</span>");
          markup = g_strdup_printf ("<i>%s</i>", tmp);
          g_free (tmp);
          gtk_label_set_markup (GTK_LABEL (widget), markup);
          g_free (markup);
          gtk_box_pack_start (GTK_BOX (hbox), widget, FALSE, FALSE, 0);
          gtk_widget_set_visible (widget, TRUE);

          /* TODO: if a demo changed settings, should we add a "reset"
           * button to get back to previous state?
           */
        }

      /* Link to full release notes on web site at the bottom. */
      hbox = gtk_box_new (GTK_ORIENTATION_HORIZONTAL, 0);
      gtk_box_pack_start (GTK_BOX (main_vbox), hbox, FALSE, FALSE, 0);
      gtk_widget_set_visible (hbox, TRUE);

      if (GIMP_MINOR_VERSION % 2 == 0)
        {
          if (GIMP_MICRO_VERSION == 0)
#ifdef GIMP_RC_VERSION
            release_link = g_strdup_printf ("https://www.ammoos.org/release/%d.%d.0-RC%d/",
                                            GIMP_MAJOR_VERSION, GIMP_MINOR_VERSION,
                                            GIMP_RC_VERSION);
#else
            release_link = g_strdup_printf ("https://www.ammoos.org/release-notes/ammoos-%d.%d.html",
                                            GIMP_MAJOR_VERSION, GIMP_MINOR_VERSION);
#endif
          else
            release_link = g_strdup_printf ("https://www.ammoos.org/release/%d.%d.%d/",
                                            GIMP_MAJOR_VERSION, GIMP_MINOR_VERSION,
                                            GIMP_MICRO_VERSION);
        }
      else
        {
          release_link = g_strdup ("https://www.ammoos.org/");
        }

      widget = gtk_link_button_new_with_label (release_link, _("Learn more"));
      gtk_widget_set_visible (widget, TRUE);
      gtk_box_pack_start (GTK_BOX (hbox), widget, FALSE, FALSE, 0);
      g_free (release_link);
    }
}

/* Actions */
static void
welcome_dialog_new_image_dialog (GtkWidget *button,
                                 GtkWidget *welcome_dialog)
{
  GimpUIManager *manager;
  Gimp          *ammoos;
  GtkWidget     *dialog;

  ammoos    = g_object_get_data (G_OBJECT (welcome_dialog), "ammoos");
  manager = menus_get_image_manager_singleton (ammoos);

  /* XXX: to avoid code duplication and divergence, we just call the "image-new"
   * action, then we check that the new dialog singleton exists in order to
   * handle its responses.
   */
  if (gimp_ui_manager_activate_action (manager, "image", "image-new") &&
      (dialog = gimp_dialog_factory_find_widget (gimp_dialog_factory_get_singleton (),
                                                 "ammoos-image-new-dialog")))
    {
      gtk_widget_set_visible (welcome_dialog, FALSE);
      g_signal_connect (dialog, "response",
                        G_CALLBACK (welcome_dialog_new_dialog_response),
                        welcome_dialog);
      g_signal_connect_swapped (dialog, "destroy",
                                G_CALLBACK (gtk_widget_destroy),
                                welcome_dialog);
    }
}

static void
welcome_dialog_open_image_dialog (GtkWidget *button,
                                  GtkWidget *welcome_dialog)
{
  Gimp          *ammoos    = g_object_get_data (G_OBJECT (welcome_dialog), "ammoos");
  GtkWidget     *dialog  = file_open_dialog_new (ammoos);
  GimpUIManager *manager = menus_get_image_manager_singleton (ammoos);

  if (gimp_ui_manager_activate_action (manager, "file", "file-open") &&
      (dialog = gimp_dialog_factory_find_widget (gimp_dialog_factory_get_singleton (),
                                                 "ammoos-file-open-dialog")))
    {
      gtk_widget_set_visible (welcome_dialog, FALSE);

      gtk_window_present (GTK_WINDOW (dialog));

      g_signal_connect (dialog, "destroy",
                        G_CALLBACK (welcome_dialog_open_dialog_close),
                        welcome_dialog);
    }
}

static void
welcome_dialog_new_dialog_response (GtkWidget *dialog,
                                    gint       response_id,
                                    GtkWidget *welcome_dialog)
{
  switch (response_id)
    {
    case GTK_RESPONSE_OK:
      /* Don't destroy the welcome dialog directly, because it's possible to get
       * the OK response without the new image dialog closing (in case it
       * triggers a confirm dialog), followed by a GTK_RESPONSE_CANCEL.
       *
       * Let the "destroy" handlers take care of destroying the welcome dialog.
       */
      break;

    case GTK_RESPONSE_CANCEL:
    case GTK_RESPONSE_DELETE_EVENT:
      g_signal_handlers_disconnect_by_func (dialog,
                                            G_CALLBACK (gtk_widget_destroy),
                                            welcome_dialog);
      gtk_widget_set_visible (welcome_dialog, TRUE);
      break;

    default:
      break;
    }
}

static void
welcome_dialog_open_dialog_close (GtkWidget *dialog,
                                  GtkWidget *welcome_dialog)
{
  GSList *files = NULL;

  files = gtk_file_chooser_get_files (GTK_FILE_CHOOSER (dialog));

  if (files && welcome_dialog)
    {
      gtk_widget_destroy (welcome_dialog);
      g_slist_free_full (files, (GDestroyNotify) g_object_unref);
      return;
    }

  if (welcome_dialog)
    gtk_widget_set_visible (welcome_dialog, TRUE);
}

static void
welcome_open_activated_callback (GimpContainerView *view,
                                 GimpViewable      *viewable,
                                 GtkWidget         *welcome_dialog)
{
  welcome_open_images_callback (NULL, view);
}

static void
welcome_open_images_callback (GtkWidget         *button,
                              GimpContainerView *view)
{
  Gimp      *ammoos;
  GList     *images;
  GtkWidget *widget;
  gboolean   opened = FALSE;

  if (! welcome_dialog)
    return;

  ammoos = g_object_get_data (G_OBJECT (welcome_dialog), "ammoos");

  widget = GTK_WIDGET (view);

  if (gimp_container_view_get_selected (view, &images) > 0)
    {
      GList *iter;

      gtk_widget_set_sensitive (welcome_dialog, FALSE);

      for (iter = images; iter; iter = g_list_next (iter))
        {
          GFile              *file;
          GimpImage          *image;
          GimpPDBStatusType   status;
          GError             *error = NULL;

          file = gimp_imagefile_get_file (iter->data);

          image = file_open_with_display (ammoos,
                                          gimp_get_user_context (ammoos),
                                          NULL, file, FALSE,
                                          G_OBJECT (gimp_widget_get_monitor (widget)),
                                          &status, &error);

          if (! image && status != GIMP_PDB_CANCEL)
            {
              gimp_message (ammoos, G_OBJECT (view), GIMP_MESSAGE_ERROR,
                            _("Opening '%s' failed:\n\n%s"),
                            gimp_file_get_utf8_name (file), error->message);
              g_clear_error (&error);
            }

          if (image)
            opened = TRUE;
        }

      g_list_free (images);
    }

  /* If no images were successfully opened, leave the dialogue up */
  gtk_widget_set_sensitive (welcome_dialog, TRUE);
  if (opened)
    gtk_widget_destroy (welcome_dialog);
}

static void
welcome_dialog_release_item_activated (GtkListBox    *listbox,
                                       GtkListBoxRow *row,
                                       gpointer       user_data)
{
  Gimp         *ammoos          = user_data;
  GList        *blink_script  = NULL;
  const gchar  *script_string;
  gchar       **script_steps;
  gint          row_index;
  gint          i;

  row_index = gtk_list_box_row_get_index (row);

  g_return_if_fail (row_index < gimp_welcome_dialog_n_items);

  script_string = gimp_welcome_dialog_demos[row_index];

  if (script_string == NULL)
    /* Not an error. Some release items have no demos. */
    return;

  script_steps = g_strsplit (script_string, ",", 0);

  for (i = 0; script_steps[i]; i++)
    {
      gchar **ids;
      gchar  *dockable_id    = NULL;
      gchar  *widget_id      = NULL;
      gchar **settings       = NULL;
      gchar  *settings_value = NULL;

      ids = g_strsplit (script_steps[i], ":", 2);
      /* Even if the string doesn't contain a second part, it is
       * NULL-terminated, hence the widget_id will simply be NULL, which
       * is fine when you just want to blink a dialog.
       */
      dockable_id = ids[0];
      widget_id   = ids[1];

      if (widget_id != NULL)
        {
          settings = g_strsplit (widget_id, "=", 2);

          widget_id = settings[0];
          settings_value = settings[1];
        }

      /* Allowing white spaces so that the demo in XML metadata can be
       * spaced-out or even on multiple lines for clarity.
       */
      dockable_id = g_strstrip (dockable_id);
      if (widget_id != NULL)
        widget_id = g_strstrip (widget_id);

      /* All our dockable IDs start with "ammoos-". This allows to write
       * shorter names in the demo script.
       */
      if (! g_str_has_prefix (dockable_id, "ammoos-"))
        {
          gchar *tmp = g_strdup_printf ("ammoos-%s", dockable_id);

          g_free (ids[0]);
          dockable_id = ids[0] = tmp;
        }

      /* Blink widget. */
      if (g_strcmp0 (dockable_id, "ammoos-toolbox") == 0)
        {
          /* All tool button IDs start with "tools-". This allows to
           * write shorter tool names in the demo script.
           */
          if (widget_id != NULL && ! g_str_has_prefix (widget_id, "tools-"))
            {
              gchar *tmp = g_strdup_printf ("tools-%s", widget_id);

              g_free (settings[0]);
              widget_id = settings[0] = tmp;
            }

          gimp_blink_toolbox (ammoos, widget_id, &blink_script);
        }
      else
        {
          gimp_blink_dockable (ammoos, dockable_id,
                               widget_id, settings_value,
                               &blink_script);
        }

      g_strfreev (ids);
      if (settings)
        g_strfreev (settings);
    }
  if (blink_script != NULL)
    {
      GList *windows = gimp_get_image_windows (ammoos);

      /* Losing focus on the welcome dialog on purpose for the main GUI
       * to be more readable.
       */
      if (windows)
        gtk_window_present (windows->data);

      gimp_blink_play_script (blink_script);

      g_list_free (windows);
    }

  g_strfreev (script_steps);
}

static void
welcome_add_link (GtkGrid      *grid,
                  GtkSizeGroup *size_group,
                  gint          column,
                  gint         *row,
                  const gchar  *emoji,
                  const gchar  *title,
                  const gchar  *link)
{
  GtkWidget *hbox;
  GtkWidget *button;
  GtkWidget *icon;

  hbox = gtk_box_new (GTK_ORIENTATION_HORIZONTAL, 4);
  gtk_grid_attach (grid, hbox, column, *row, 1, 1);
  /* These margin are by design to emphasize a bit the link list by
   * moving them a tiny bit to the right instead of being exactly
   * aligned with the top text.
   */
  gtk_widget_set_margin_start (hbox, 10);
  gtk_widget_set_visible (hbox, TRUE);

  ++(*row);

  icon = gtk_label_new (emoji);
  gtk_size_group_add_widget (size_group, icon);
  gtk_box_pack_start (GTK_BOX (hbox), icon, FALSE, FALSE, 0);
  gtk_widget_set_visible (icon, TRUE);

  button = gtk_link_button_new_with_label (link, title);
  gtk_box_pack_start (GTK_BOX (hbox), button, FALSE, FALSE, 0);
  gtk_widget_set_visible (button, TRUE);
}

static void
welcome_size_allocate (GtkWidget     *welcome_dialog,
                       GtkAllocation *allocation,
                       gpointer       user_data)
{
  GtkWidget     *image = GTK_WIDGET (user_data);
  GError        *error = NULL;
  GFile         *splash_file;
  GdkPixbuf     *pixbuf;
  GdkMonitor    *monitor;
  GdkWindow     *gdk_window;
  GdkRectangle   workarea;
  gint           image_width;

  gdk_window = gtk_widget_get_window (welcome_dialog);
  if (gdk_window)
    monitor = gdk_display_get_monitor_at_window (gdk_display_get_default (), gdk_window);
  else
    monitor = gimp_get_monitor_at_pointer ();
  gdk_monitor_get_workarea (monitor, &workarea);

  if (gtk_image_get_storage_type (GTK_IMAGE (image)) == GTK_IMAGE_PIXBUF)
    {
      if (allocation->height > workarea.height - 10 &&
          ! g_object_get_data (G_OBJECT (welcome_dialog), "resized-once"))
        {
          g_object_set_data (G_OBJECT (welcome_dialog), "resized-once", GINT_TO_POINTER (TRUE));
          g_idle_add_full (G_PRIORITY_DEFAULT_IDLE,
                           welcome_scrollable_resize, NULL,
                           NULL);
        }
    return;
    }

  image_width = MAX (allocation->width - 2, workarea.width / 4);
  image_width = MIN (image_width, workarea.width / 3);
  /* Splash screens are fullHD. We should not load it bigger.
   * See: https://gitlab.gnome.org/GNOME/ammoos-data/-/blob/main/images/README.md#requirements
   */
  image_width = MIN (image_width, 1920);

  splash_file = gimp_data_directory_file ("images", "ammoos-splash.png", NULL);
  pixbuf = gdk_pixbuf_new_from_file_at_scale (g_file_peek_path (splash_file),
                                              image_width, -1,
                                              TRUE, &error);
  if (pixbuf)
    {
      gtk_image_set_from_pixbuf (GTK_IMAGE (image), pixbuf);
      g_object_unref (pixbuf);
    }
  else if (error)
    {
      g_printerr ("%s: %s\n", G_STRFUNC, error->message);
    }
  g_object_unref (splash_file);
  g_clear_error (&error);

  gtk_widget_set_visible (image, TRUE);

  gtk_window_set_resizable (GTK_WINDOW (welcome_dialog), FALSE);
}

static gboolean
welcome_scrollable_resize (gpointer data)
{
  if (welcome_dialog)
    {
      GtkWidget *prefs_box = g_object_get_data (G_OBJECT (welcome_dialog), "prefs-box");
      GtkWidget *main_vbox = g_object_get_data (G_OBJECT (welcome_dialog), "welcome-vbox");

      /* Make the first page scrollable to prevent height issues on
       * smaller screens */
      gimp_prefs_box_set_page_scrollable (GIMP_PREFS_BOX (prefs_box), main_vbox, TRUE);

      gtk_widget_queue_resize (GTK_WIDGET (welcome_dialog));
    }

  return G_SOURCE_REMOVE;
}

static void
welcome_dialog_new_image_accelerator (GtkAccelGroup  *accel_group,
                                      GObject        *accelerator_widget,
                                      guint           keyval,
                                      GdkModifierType mods,
                                      gpointer        user_data)
{
  GtkWidget *dialog = GTK_WIDGET (user_data);

  welcome_dialog_new_image_dialog (NULL, dialog);
}

static void
welcome_dialog_open_image_dialog_accelerator (GtkAccelGroup  *accel_group,
                                              GObject        *accelerator_widget,
                                              guint           keyval,
                                              GdkModifierType mods,
                                              gpointer        user_data)
{
  GtkWidget *dialog = GTK_WIDGET (user_data);

  welcome_dialog_open_image_dialog (NULL, dialog);
}

static void
welcome_dialog_open_image_accelerator (GtkAccelGroup  *accel_group,
                                       GObject        *accelerator_widget,
                                       guint           keyval,
                                       GdkModifierType mods,
                                       gpointer        user_data)
{
  Gimp          *ammoos    = g_object_get_data (G_OBJECT (welcome_dialog), "ammoos");
  GimpUIManager *manager = menus_get_image_manager_singleton (ammoos);
  guint          index   = GPOINTER_TO_UINT (user_data);
  gchar          action_name[20];

  g_snprintf (action_name, sizeof (action_name), "file-open-recent-%02u", index + 1);

  if (gimp_ui_manager_activate_action (manager, "file", action_name))
    gtk_widget_destroy (welcome_dialog);
}
