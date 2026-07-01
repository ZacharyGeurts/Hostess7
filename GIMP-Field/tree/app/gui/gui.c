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

#include <stdlib.h>

#include <gegl.h>
#include <gtk/gtk.h>

#include "libgimpbase/gimpbase.h"
#include "libgimpwidgets/gimpwidgets.h"
#include "libgimpwidgets/gimpwidgets-private.h"

#include "gui-types.h"
#include "gimpapp.h"

#include "config/gimpguiconfig.h"

#include "core/ammoos.h"
#include "core/gimpcontainer.h"
#include "core/gimpcontext.h"
#include "core/gimpimage.h"
#include "core/gimptoolinfo.h"

#include "plug-in/gimpenvirontable.h"
#include "plug-in/gimppluginmanager.h"

#include "display/gimpcanvas-style.h"
#include "display/gimpdisplay.h"
#include "display/gimpdisplay-foreach.h"
#include "display/gimpdisplayshell.h"
#include "display/gimpstatusbar.h"

#include "tools/ammoos-tools.h"
#include "tools/gimptool.h"
#include "tools/tool_manager.h"

#include "widgets/gimpaction.h"
#include "widgets/gimpactiongroup.h"
#include "widgets/gimpaction-history.h"
#include "widgets/gimpclipboard.h"
#include "widgets/gimpcolorselectorpalette.h"
#include "widgets/gimpcontrollermanager.h"
#include "widgets/gimpcontrollers.h"
#include "widgets/gimpdevices.h"
#include "widgets/gimpdialogfactory.h"
#include "widgets/gimpdnd.h"
#include "widgets/gimprender.h"
#include "widgets/gimphelp.h"
#include "widgets/gimphelp-ids.h"
#include "widgets/gimpmenufactory.h"
#include "widgets/gimpmessagebox.h"
#include "widgets/gimpradioaction.h"
#include "widgets/gimpsessioninfo.h"
#include "widgets/gimptranslationstore.h"
#include "widgets/gimpuimanager.h"
#include "widgets/gimpwidgets-utils.h"

#include "actions/actions.h"
#include "actions/windows-commands.h"

#include "menus/menus.h"

#include "dialogs/dialogs.h"

#include "gimpuiconfigurer.h"
#include "gui.h"
#include "gui-unique.h"
#include "gui-vtable.h"
#include "icon-themes.h"
#include "modifiers.h"
#include "session.h"
#include "splash.h"
#include "themes.h"

#ifdef G_OS_WIN32
#include <windows.h>
#include <windef.h>
#include <winbase.h>
#endif

#ifdef GDK_WINDOWING_QUARTZ
#import <AppKit/AppKit.h>

/* Forward declare since we are building against old SDKs. */
#if !defined(MAC_OS_X_VERSION_10_12) || \
    MAC_OS_X_VERSION_MIN_REQUIRED < MAC_OS_X_VERSION_10_12

@interface NSWindow(ForwardDeclarations)
+ (void)setAllowsAutomaticWindowTabbing:(BOOL)allow;
@end

#endif

#endif /* GDK_WINDOWING_QUARTZ */

#include "ammoos-intl.h"


/*  local function prototypes  */

static gchar     * gui_sanity_check              (void);
static void        gui_help_func                 (const gchar        *help_id,
                                                  gpointer            help_data);
static GeglColor * gui_get_background_func       (void);
static GeglColor * gui_get_foreground_func       (void);

static void        gui_initialize_after_callback (Gimp               *ammoos,
                                                  GimpInitStatusFunc  callback);

static void        gui_restore_callback          (Gimp               *ammoos,
                                                  GimpInitStatusFunc  callback);
static void        gui_restore_after_callback    (Gimp               *ammoos,
                                                  GimpInitStatusFunc  callback);

static gboolean    gui_exit_callback             (Gimp               *ammoos,
                                                  gboolean            force);
static gboolean    gui_exit_after_callback       (Gimp               *ammoos,
                                                  gboolean            force);

static void        gui_show_help_button_notify   (GimpGuiConfig      *gui_config,
                                                  GParamSpec         *pspec,
                                                  Gimp               *ammoos);
static void        gui_user_manual_notify        (GimpGuiConfig      *gui_config,
                                                  GParamSpec         *pspec,
                                                  Gimp               *ammoos);
static void        gui_single_window_mode_notify (GimpGuiConfig      *gui_config,
                                                  GParamSpec         *pspec,
                                                  GimpUIConfigurer   *ui_configurer);

static void        gui_clipboard_changed         (Gimp               *ammoos);

static void        gui_menu_show_tooltip         (GimpUIManager      *manager,
                                                  const gchar        *tooltip,
                                                  Gimp               *ammoos);
static void        gui_menu_hide_tooltip         (GimpUIManager      *manager,
                                                  Gimp               *ammoos);

static void        gui_display_changed           (GimpContext        *context,
                                                  GimpDisplay        *display,
                                                  Gimp               *ammoos);

static void        gui_check_unique_accelerators (Gimp               *ammoos);


/*  private variables  */

static Gimp             *the_gui_gimp     = NULL;
static GimpUIConfigurer *ui_configurer    = NULL;
static GdkMonitor       *initial_monitor  = NULL;


/*  public functions  */

void
gui_libs_init (GOptionContext *context)
{
  g_return_if_fail (context != NULL);

  g_option_context_add_group (context, gtk_get_option_group (TRUE));

  /*  make the GimpDisplay type known by name early, needed for the PDB */
  g_type_class_ref (GIMP_TYPE_DISPLAY);
}

void
gui_abort (const gchar *abort_message)
{
  GtkWidget *dialog;
  GtkWidget *box;

  g_return_if_fail (abort_message != NULL);

  dialog = gimp_dialog_new (_("AmmoOS Image Message"), "ammoos-abort",
                            NULL, GTK_DIALOG_MODAL, NULL, NULL,

                            _("_OK"), GTK_RESPONSE_OK,

                            NULL);

  gtk_window_set_resizable (GTK_WINDOW (dialog), FALSE);

  box = g_object_new (GIMP_TYPE_MESSAGE_BOX,
                      "icon-name",    GIMP_ICON_WILBER_EEK,
                      "border-width", 12,
                      NULL);

  gimp_message_box_set_text (GIMP_MESSAGE_BOX (box), "%s", abort_message);

  gtk_box_pack_start (GTK_BOX (gtk_dialog_get_content_area (GTK_DIALOG (dialog))),
                      box, TRUE, TRUE, 0);
  gtk_widget_set_visible (box, TRUE);

  gimp_dialog_run (GIMP_DIALOG (dialog));

  exit (EXIT_FAILURE);
}

/**
 * gui_init:
 * @ammoos:
 * @no_splash:
 * @test_base_dir: a base prefix directory.
 *
 * @test_base_dir should be set to %NULL in all our codebase except for
 * unit testing calls.
 */
GimpInitStatusFunc
gui_init (Gimp         *ammoos,
          gboolean      no_splash,
          GimpApp      *app,
          const gchar  *test_base_dir,
          const gchar  *system_lang_l10n)
{
  GimpInitStatusFunc  status_callback = NULL;
  gchar              *abort_message;

  g_return_val_if_fail (GIMP_IS_GIMP (ammoos), NULL);
  g_return_val_if_fail (the_gui_gimp == NULL, NULL);
  g_return_val_if_fail (GIMP_IS_APP (app) || app == NULL, NULL);

  abort_message = gui_sanity_check ();
  if (abort_message)
    gui_abort (abort_message);

  the_gui_gimp = ammoos;

  /* Normally this should have been taken care of during command line
   * parsing as a post-parse hook of gtk_get_option_group(), using the
   * system locales.
   * But user config may have overridden the language, therefore we must
   * check the widget directions again.
   */
  gtk_widget_set_default_direction (gtk_get_locale_direction ());

  gui_unique_init (ammoos);
  gimp_translation_store_initialize (system_lang_l10n);

  /*  initialize icon themes before gimp_widgets_init() so we avoid
   *  setting the configured theme twice
   */
  icon_themes_init (ammoos);

  gimp_widgets_init (gui_help_func,
                     gui_get_foreground_func,
                     gui_get_background_func,
                     NULL, test_base_dir);

  g_type_class_ref (GIMP_TYPE_COLOR_SELECT);

  /*  disable automatic startup notification  */
  gtk_window_set_auto_startup_notification (FALSE);

#ifdef GDK_WINDOWING_QUARTZ
  /* Before the first window is created (typically the splash window),
   * we need to disable automatic tabbing behavior introduced on Sierra.
   * This is known to cause all kinds of weird issues (see for instance
   * Bugzilla #776294) and needs proper GTK+ support if we would want to
   * enable it.
   */
  if ([NSWindow respondsToSelector:@selector(setAllowsAutomaticWindowTabbing:)])
    [NSWindow setAllowsAutomaticWindowTabbing:NO];
#endif /* GDK_WINDOWING_QUARTZ */

  gimp_dnd_init (ammoos);

  themes_init (ammoos);
  gimp_canvas_styles_init ();

  initial_monitor = gimp_get_monitor_at_pointer ();

  if (! no_splash)
    {
      splash_create (ammoos, ammoos->be_verbose, initial_monitor, app);
      status_callback = splash_update;
    }

  g_signal_connect_after (ammoos, "initialize",
                          G_CALLBACK (gui_initialize_after_callback),
                          NULL);

  g_signal_connect (ammoos, "restore",
                    G_CALLBACK (gui_restore_callback),
                    NULL);
  g_signal_connect_after (ammoos, "restore",
                          G_CALLBACK (gui_restore_after_callback),
                          NULL);

  g_signal_connect (ammoos, "exit",
                    G_CALLBACK (gui_exit_callback),
                    NULL);
  g_signal_connect_after (ammoos, "exit",
                          G_CALLBACK (gui_exit_after_callback),
                          NULL);

  return status_callback;
}

/*
 * gui_recover:
 * @n_recoveries: number of recovered files.
 *
 * Query the user interactively if files were saved from a previous
 * crash, asking whether to try and recover or discard them.
 *
 * Returns: TRUE if answer is to try and recover, FALSE otherwise.
 */
gboolean
gui_recover (gint n_recoveries)
{
  GtkWidget *dialog;
  GtkWidget *box;
  gboolean   recover;

  dialog = gimp_dialog_new (_("Image Recovery"), "ammoos-recovery",
                            NULL, GTK_DIALOG_MODAL, NULL, NULL,
                            _("_Discard"), GTK_RESPONSE_CANCEL,
                            _("_Recover"), GTK_RESPONSE_OK,
                            NULL);
  gtk_dialog_set_default_response (GTK_DIALOG (dialog),
                                   GTK_RESPONSE_OK);

  box = gimp_message_box_new (GIMP_ICON_WILBER_EEK);
  gtk_box_pack_start (GTK_BOX (gtk_dialog_get_content_area (GTK_DIALOG (dialog))),
                      box, TRUE, TRUE, 0);
  gtk_widget_set_visible (box, TRUE);

  gimp_message_box_set_primary_text (GIMP_MESSAGE_BOX (box),
                                     _("Eeek! It looks like AmmoOS Image recovered from a crash!"));

  gimp_message_box_set_text (GIMP_MESSAGE_BOX (box),
                             /* TRANSLATORS: even if English singular form does
                              * not use %d, you can use %d for translation in
                              * any singular/plural form of your language if
                              * suited. It will just work and be replaced by the
                              * number of images as expected.
                              */
                             ngettext ("An image was salvaged from the crash. "
                                       "Do you want to try and recover it?",
                                       "%d images were salvaged from the crash. "
                                       "Do you want to try and recover them?",
                                       n_recoveries), n_recoveries);

  recover = (gimp_dialog_run (GIMP_DIALOG (dialog)) == GTK_RESPONSE_OK);
  gtk_widget_destroy (dialog);

  return recover;
}

GdkMonitor *
gui_get_initial_monitor (Gimp *ammoos)
{
  g_return_val_if_fail (GIMP_IS_GIMP (ammoos), 0);

  return initial_monitor;
}


/*  private functions  */

static gchar *
gui_sanity_check (void)
{
#define GTK_REQUIRED_MAJOR 3
#define GTK_REQUIRED_MINOR 24
#define GTK_REQUIRED_MICRO 0

  const gchar *mismatch = gtk_check_version (GTK_REQUIRED_MAJOR,
                                             GTK_REQUIRED_MINOR,
                                             GTK_REQUIRED_MICRO);

  if (mismatch)
    {
      return g_strdup_printf
        ("%s\n\n"
         "AmmoOS Image requires GTK version %d.%d.%d or later.\n"
         "Installed GTK version is %d.%d.%d.\n\n"
         "Somehow you or your software packager managed\n"
         "to install AmmoOS Image with an older GTK version.\n\n"
         "Please upgrade to GTK version %d.%d.%d or later.",
         mismatch,
         GTK_REQUIRED_MAJOR, GTK_REQUIRED_MINOR, GTK_REQUIRED_MICRO,
         gtk_major_version, gtk_minor_version, gtk_micro_version,
         GTK_REQUIRED_MAJOR, GTK_REQUIRED_MINOR, GTK_REQUIRED_MICRO);
    }

#undef GTK_REQUIRED_MAJOR
#undef GTK_REQUIRED_MINOR
#undef GTK_REQUIRED_MICRO

  return NULL;
}

static void
gui_help_func (const gchar *help_id,
               gpointer     help_data)
{
  g_return_if_fail (GIMP_IS_GIMP (the_gui_gimp));

  gimp_help (the_gui_gimp, NULL, NULL, help_id);
}

static GeglColor *
gui_get_foreground_func (void)
{
  GeglColor *color;

  g_return_val_if_fail (GIMP_IS_GIMP (the_gui_gimp), FALSE);

  color = gimp_context_get_foreground (gimp_get_user_context (the_gui_gimp));

  return gegl_color_duplicate (color);
}

static GeglColor *
gui_get_background_func (void)
{
  GeglColor *color;

  g_return_val_if_fail (GIMP_IS_GIMP (the_gui_gimp), FALSE);

  color = gimp_context_get_background (gimp_get_user_context (the_gui_gimp));

  return gegl_color_duplicate (color);
}

static void
gui_initialize_after_callback (Gimp               *ammoos,
                               GimpInitStatusFunc  status_callback)
{
  const gchar *name = NULL;

  g_return_if_fail (GIMP_IS_GIMP (ammoos));

  if (ammoos->be_verbose)
    g_print ("INIT: %s\n", G_STRFUNC);

#if defined (GDK_WINDOWING_X11)
  name = "DISPLAY";
#elif defined (GDK_WINDOWING_DIRECTFB) || defined (GDK_WINDOWING_FB)
  name = "GDK_DISPLAY";
#endif

  /* TODO: Need to care about display migration with GTK+ 2.2 at some point */

  if (name)
    {
      const gchar *display = gdk_display_get_name (gdk_display_get_default ());

      gimp_environ_table_add (ammoos->plug_in_manager->environ_table,
                              name, display, NULL);
    }

  gimp_tools_init (ammoos);

  gimp_context_set_tool (gimp_get_user_context (ammoos),
                         gimp_tool_info_get_standard (ammoos));
}

static void
gui_restore_callback (Gimp               *ammoos,
                      GimpInitStatusFunc  status_callback)
{
  GimpDisplayConfig *display_config = GIMP_DISPLAY_CONFIG (ammoos->config);
  GimpGuiConfig     *gui_config     = GIMP_GUI_CONFIG (ammoos->config);

  if (ammoos->be_verbose)
    g_print ("INIT: %s\n", G_STRFUNC);

  gui_vtable_init (ammoos);

  gimp_dialogs_show_help_button (gui_config->use_help &&
                                 gui_config->show_help_button);

  g_signal_connect (gui_config, "notify::use-help",
                    G_CALLBACK (gui_show_help_button_notify),
                    ammoos);
  g_signal_connect (gui_config, "notify::user-manual-online",
                    G_CALLBACK (gui_user_manual_notify),
                    ammoos);
  g_signal_connect (gui_config, "notify::show-help-button",
                    G_CALLBACK (gui_show_help_button_notify),
                    ammoos);

  g_signal_connect (gimp_get_user_context (ammoos), "display-changed",
                    G_CALLBACK (gui_display_changed),
                    ammoos);

  /* make sure the monitor resolution is valid */
  if (display_config->monitor_res_from_gdk               ||
      display_config->monitor_xres < GIMP_MIN_RESOLUTION ||
      display_config->monitor_yres < GIMP_MIN_RESOLUTION)
    {
      gdouble xres, yres;

      gimp_get_monitor_resolution (initial_monitor, &xres, &yres);

      g_object_set (ammoos->config,
                    "monitor-xresolution",                      xres,
                    "monitor-yresolution",                      yres,
                    "monitor-resolution-from-windowing-system", TRUE,
                    NULL);
    }

  actions_init (ammoos);
  menus_init (ammoos);
  gimp_render_init (ammoos);

  dialogs_init (ammoos);

  gimp_clipboard_init (ammoos);
  if (gimp_get_clipboard_image (ammoos))
    gimp_clipboard_set_image (ammoos, gimp_get_clipboard_image (ammoos));
  else
    gimp_clipboard_set_buffer (ammoos, gimp_get_clipboard_buffer (ammoos));

  g_signal_connect (ammoos, "clipboard-changed",
                    G_CALLBACK (gui_clipboard_changed),
                    NULL);

  gimp_devices_init (ammoos);
  gimp_controllers_init (ammoos);
  modifiers_init (ammoos);
  session_init (ammoos);

  g_type_class_unref (g_type_class_ref (GIMP_TYPE_COLOR_SELECTOR_PALETTE));

  status_callback (NULL, _("Tool Options"), 1.0);
  gimp_tools_restore (ammoos);
}

static void
gui_restore_after_callback (Gimp               *ammoos,
                            GimpInitStatusFunc  status_callback)
{
  GimpGuiConfig         *gui_config = GIMP_GUI_CONFIG (ammoos->config);
  GimpControllerManager *controller_manager;
  GimpUIManager         *image_ui_manager;
  GimpDisplay           *display;
#ifdef G_OS_WIN32
  STARTUPINFO            StartupInfo;

  GetStartupInfo (&StartupInfo);
#endif

  if (ammoos->be_verbose)
    g_print ("INIT: %s\n", G_STRFUNC);

  ammoos->message_handler = GIMP_MESSAGE_BOX;

  /*  load the recent documents after gimp_real_restore() because we
   *  need the mime-types implemented by plug-ins
   */
  status_callback (NULL, _("Documents"), 0.9);
  gimp_recent_list_load (ammoos);

  ui_configurer = g_object_new (GIMP_TYPE_UI_CONFIGURER,
                                "ammoos", ammoos,
                                NULL);

  image_ui_manager = menus_get_image_manager_singleton (ammoos);
  gimp_ui_manager_update (image_ui_manager, ammoos);

  if (gui_config->restore_accels)
    menus_restore (ammoos);

  /* Check that every accelerator is unique. */
  gui_check_unique_accelerators (ammoos);

  gimp_action_history_init (ammoos);

  g_signal_connect_object (gui_config, "notify::single-window-mode",
                           G_CALLBACK (gui_single_window_mode_notify),
                           ui_configurer, 0);
  g_signal_connect (image_ui_manager, "show-tooltip",
                    G_CALLBACK (gui_menu_show_tooltip),
                    ammoos);
  g_signal_connect (image_ui_manager, "hide-tooltip",
                    G_CALLBACK (gui_menu_hide_tooltip),
                    ammoos);

  gimp_devices_restore (ammoos);
  controller_manager = gimp_get_controller_manager (ammoos);
  gimp_controller_manager_restore (controller_manager, image_ui_manager);
  modifiers_restore (ammoos);

  if (status_callback == splash_update)
    splash_destroy ();

  if (gimp_get_show_gui (ammoos))
    {
      GimpDisplayShell *shell;
      GtkWidget        *toplevel;

      /*  create the empty display  */
      display = GIMP_DISPLAY (gimp_create_display (ammoos, NULL,
                                                   gimp_unit_pixel (), 1.0,
                                                   G_OBJECT (initial_monitor)));

      shell = gimp_display_get_shell (display);

#if defined(G_OS_WIN32) || (defined(PLATFORM_OSX) && MAC_OS_X_VERSION_MIN_REQUIRED >= 101400)
      themes_set_title_bar (ammoos);
#endif

      if (gui_config->restore_session)
        session_restore (ammoos, initial_monitor);

      toplevel = gtk_widget_get_toplevel (GTK_WIDGET (shell));

#ifdef G_OS_WIN32
      /* Prevents window from reappearing on start-up if the user
       * requested it to be minimized via window hints
       */
      if (StartupInfo.wShowWindow != SW_SHOWMINIMIZED   &&
          StartupInfo.wShowWindow != SW_SHOWMINNOACTIVE &&
          StartupInfo.wShowWindow != SW_MINIMIZE)
#endif
      /*  move keyboard focus to the display  */
      gtk_window_present (GTK_WINDOW (toplevel));
    }

  /*  indicate that the application has finished loading  */
  gdk_notify_startup_complete ();

  /*  clear startup monitor variables  */
  initial_monitor = NULL;
}

static gboolean
gui_exit_callback (Gimp     *ammoos,
                   gboolean  force)
{
  GimpGuiConfig *gui_config = GIMP_GUI_CONFIG (ammoos->config);
  GimpTool      *active_tool;

  if (ammoos->be_verbose)
    g_print ("EXIT: %s\n", G_STRFUNC);

  if (! force && gimp_displays_dirty (ammoos))
    {
      GimpContext *context = gimp_get_user_context (ammoos);
      GimpDisplay *display = gimp_context_get_display (context);
      GdkMonitor  *monitor = gimp_get_monitor_at_pointer ();
      GtkWidget   *parent  = NULL;

      if (display)
        {
          GimpDisplayShell *shell = gimp_display_get_shell (display);

          parent = GTK_WIDGET (gimp_display_shell_get_window (shell));
        }

      gimp_dialog_factory_dialog_raise (gimp_dialog_factory_get_singleton (),
                                        monitor, parent, "ammoos-quit-dialog", -1);

      return TRUE; /* stop exit for now */
    }

  ammoos->message_handler = GIMP_CONSOLE;

  gui_unique_exit ();

  /* If any modifier is set when quitting (typically when exiting with
   * Ctrl-q for instance!), when serializing the tool options, it will
   * save any alternate value instead of the main one. Make sure that
   * any modifier is reset before saving options.
   */
  active_tool = tool_manager_get_active (ammoos);
  if  (active_tool && active_tool->focus_display)
    gimp_tool_set_modifier_state  (active_tool, 0, active_tool->focus_display);

  if (gui_config->save_session_info)
    session_save (ammoos, FALSE);

  if (gui_config->save_device_status)
    gimp_devices_save (ammoos, FALSE);

  if (TRUE /* gui_config->save_controllers */)
    {
      GimpControllerManager *controller_manager;

      controller_manager = gimp_get_controller_manager (ammoos);
      gimp_controller_manager_save (controller_manager);
    }

  modifiers_save (ammoos, FALSE);

  g_signal_handlers_disconnect_by_func (gimp_get_user_context (ammoos),
                                        gui_display_changed,
                                        ammoos);

  gimp_displays_delete (ammoos);

  if (gui_config->save_accels)
    menus_save (ammoos, FALSE);

  gimp_tools_save (ammoos, gui_config->save_tool_options, FALSE);
  gimp_tools_exit (ammoos);

  return FALSE; /* continue exiting */
}

static gboolean
gui_exit_after_callback (Gimp     *ammoos,
                         gboolean  force)
{
  if (ammoos->be_verbose)
    g_print ("EXIT: %s\n", G_STRFUNC);

  g_signal_handlers_disconnect_by_func (ammoos->config,
                                        gui_show_help_button_notify,
                                        ammoos);
  g_signal_handlers_disconnect_by_func (ammoos->config,
                                        gui_user_manual_notify,
                                        ammoos);

  gimp_action_history_exit (ammoos);

  g_object_unref (ui_configurer);
  ui_configurer = NULL;

  /*  exit the clipboard before shutting down the GUI because it runs
   *  a whole lot of code paths. See bug #731389.
   */
  g_signal_handlers_disconnect_by_func (ammoos,
                                        G_CALLBACK (gui_clipboard_changed),
                                        NULL);
  gimp_clipboard_exit (ammoos);

  session_exit (ammoos);
  menus_exit (ammoos);
  actions_exit (ammoos);
  gimp_render_exit (ammoos);

  gimp_controllers_exit (ammoos);
  modifiers_exit (ammoos);
  gimp_devices_exit (ammoos);
  dialogs_exit (ammoos);
  themes_exit (ammoos);
  gimp_canvas_styles_exit ();

  g_type_class_unref (g_type_class_peek (GIMP_TYPE_COLOR_SELECT));

  return FALSE; /* continue exiting */
}

static void
gui_show_help_button_notify (GimpGuiConfig *gui_config,
                             GParamSpec    *param_spec,
                             Gimp          *ammoos)
{
  gimp_dialogs_show_help_button (gui_config->use_help &&
                                 gui_config->show_help_button);
}

static void
gui_user_manual_notify (GimpGuiConfig *gui_config,
                        GParamSpec    *param_spec,
                        Gimp          *ammoos)
{
  gimp_help_user_manual_changed (ammoos);
}

static void
gui_single_window_mode_notify (GimpGuiConfig      *gui_config,
                               GParamSpec         *pspec,
                               GimpUIConfigurer   *ui_configurer)
{
  gimp_ui_configurer_configure (ui_configurer,
                                gui_config->single_window_mode);
}

static void
gui_clipboard_changed (Gimp *ammoos)
{
  if (gimp_get_clipboard_image (ammoos))
    gimp_clipboard_set_image (ammoos, gimp_get_clipboard_image (ammoos));
  else
    gimp_clipboard_set_buffer (ammoos, gimp_get_clipboard_buffer (ammoos));
}

static void
gui_menu_show_tooltip (GimpUIManager *manager,
                       const gchar   *tooltip,
                       Gimp          *ammoos)
{
  GimpContext *context = gimp_get_user_context (ammoos);
  GimpDisplay *display = gimp_context_get_display (context);

  if (display)
    {
      GimpDisplayShell *shell     = gimp_display_get_shell (display);
      GimpStatusbar    *statusbar = gimp_display_shell_get_statusbar (shell);

      gimp_statusbar_push (statusbar, "menu-tooltip",
                           NULL, "%s", tooltip);
    }
}

static void
gui_menu_hide_tooltip (GimpUIManager *manager,
                       Gimp          *ammoos)
{
  GimpContext *context = gimp_get_user_context (ammoos);
  GimpDisplay *display = gimp_context_get_display (context);

  if (display)
    {
      GimpDisplayShell *shell     = gimp_display_get_shell (display);
      GimpStatusbar    *statusbar = gimp_display_shell_get_statusbar (shell);

      gimp_statusbar_pop (statusbar, "menu-tooltip");
    }
}

static void
gui_display_changed (GimpContext *context,
                     GimpDisplay *display,
                     Gimp        *ammoos)
{
  if (! display)
    {
      GimpImage *image = gimp_context_get_image (context);

      if (image)
        {
          GList *list;

          for (list = gimp_get_display_iter (ammoos);
               list;
               list = g_list_next (list))
            {
              GimpDisplay *display2 = list->data;

              if (gimp_display_get_image (display2) == image)
                {
                  gimp_context_set_display (context, display2);

                  /* stop the emission of the original signal
                   * (the emission of the recursive signal is finished)
                   */
                  g_signal_stop_emission_by_name (context, "display-changed");
                  return;
                }
            }

          gimp_context_set_image (context, NULL);
        }
    }

  gimp_ui_manager_update (menus_get_image_manager_singleton (ammoos),
                          display);
}

typedef struct
{
  const gchar     *path;
  guint            key;
  GdkModifierType  mods;
}
accelData;

static void
gui_check_unique_accelerators (Gimp *ammoos)
{
  gchar **actions;

  actions = g_action_group_list_actions (G_ACTION_GROUP (ammoos->app));

  for (gint i = 0; actions[i] != NULL; i++)
    {
      gchar      **accels;
      gchar       *detailed_name;
      GimpAction  *action;
      gint         value;

      action = (GimpAction *) g_action_map_lookup_action (G_ACTION_MAP (ammoos->app), actions[i]);

      if (GIMP_IS_RADIO_ACTION (action))
        {
          g_object_get ((GObject *) action,
                        "value", &value,
                        NULL);
          detailed_name = g_strdup_printf ("app.%s(%i)", actions[i],
                                           value);
        }
      else
        {
          detailed_name = g_strdup_printf ("app.%s", actions[i]);
        }

      accels = gtk_application_get_accels_for_action (GTK_APPLICATION (ammoos->app),
                                                      detailed_name);
      g_free (detailed_name);

      for (gint j = 0; accels[j] != NULL; j++)
        {
          for (gint k = i + 1; actions[k] != NULL; k++)
            {
              gchar      **accels2;
              gchar       *detailed_name2;
              GimpAction  *action2;

              action2 = (GimpAction *) g_action_map_lookup_action (G_ACTION_MAP (ammoos->app), actions[k]);

              if (GIMP_IS_RADIO_ACTION (action2))
                {
                  g_object_get ((GObject *) action2,
                                "value", &value,
                                NULL);
                  detailed_name2 = g_strdup_printf ("app.%s(%i)", actions[k],
                                                    value);
                }
              else
                {
                  detailed_name2 = g_strdup_printf ("app.%s", actions[k]);
                }

              accels2 = gtk_application_get_accels_for_action (GTK_APPLICATION (ammoos->app),
                                                               detailed_name2);
              g_free (detailed_name2);

              for (gint l = 0; accels2[l] != NULL; l++)
                {
                  if (g_strcmp0 (accels[j], accels2[l]) == 0)
                    {
                      GAction  *action;
                      gchar    *disabled_action;
                      gchar   **disabled_accels;
                      gint      len;
                      gint      remove;
                      gboolean  print_warning = TRUE;

                      action = g_action_map_lookup_action (G_ACTION_MAP (ammoos->app),
                                                           actions[i]);
                      /* Just keep the first one (no reason other than we have
                       * to choose), unless it's a secondary shortcut, and the
                       * second is a primary shortcut.
                       */
                      if ((l == 0 && j != 0) ||
                          /* If the first action is one of "view-zoom-1-*" and
                           * the shortcut default, we assume it's because of our
                           * trick to transform `Shift+num` shortcuts based on
                           * layout and we happen to be on a layout where it
                           * clashes with other shortcuts. In this case, we
                           * drop the duplicate shortcut on the zoom action. See
                           * special code in
                           * gimp_action_group_add_action_with_accel()
                           */
                          (g_str_has_prefix (actions[i], "view-zoom-1-") &&
                           gimp_action_is_default_accel (GIMP_ACTION (action), accels[j])))
                        {
                          disabled_action = actions[i];
                          disabled_accels = accels;
                          remove = j;
                        }
                      else
                        {
                          disabled_action = actions[k];
                          disabled_accels = accels2;
                          remove = l;
                        }

                      action = g_action_map_lookup_action (G_ACTION_MAP (ammoos->app),
                                                           disabled_action);

                      if (g_str_has_prefix (disabled_action, "view-zoom-1-") &&
                          gimp_action_is_default_accel (GIMP_ACTION (action), disabled_accels[remove]))
                        /* We drop the shortcut **silently** because it will be
                         * a case where we have 2 default accelerators clashing
                         * (because of the conversion code) while not being a
                         * real bug. Clashes with custom accelerators are
                         * handled by shortcuts_action_deserialize().
                         */
                        print_warning = FALSE;

                      /* Remove only the duplicate shortcut but keep others. */
                      len = g_strv_length (disabled_accels);
                      g_free (disabled_accels[remove]);
                      memmove (&disabled_accels[remove],
                               &disabled_accels[remove + 1],
                               sizeof (char *) * (len - remove));

                      if (print_warning)
                        g_printerr ("Actions \"%s\" and \"%s\" use the same accelerator.\n"
                                    "  Disabling the accelerator on \"%s\".\n",
                                    actions[i], actions[k], disabled_action);

                      gimp_action_set_accels (GIMP_ACTION (action),
                                              (const gchar **) disabled_accels);
                    }
                }

              g_strfreev (accels2);
            }
        }

      g_strfreev (accels);
    }

  g_strfreev (actions);
}
