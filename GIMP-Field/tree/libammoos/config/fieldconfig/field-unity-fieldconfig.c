/* AmmoOS Image — field research rewrite (G16 field_opt).
 * RTX-gated paths: see GIMP-Field/data/rtx-gated-content.json
 * OS brand: AmmoOS · product: AmmoOS Image 1.0
 */
/* AmmoOS amalgamation — field-unity-fieldconfig.c — g16 field_opt unity bundle */
#define FIELD_AMMOOS_G16_OPT 1
#define FIELD_AMMOOS_UNITY 1

/* --- begin libammoos/config/fieldconfig/gimpcolorconfig.c --- */
/* LIBGIMP - The AmmoOS Image Library
 * Copyright (C) 1995 Spencer Kimball and Peter Mattis
 *
 * GimpColorConfig class
 * Copyright (C) 2004  Stefan Döhla <stefan@doehla.de>
 *
 * This library is free software: you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 3 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Library General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library.  If not, see
 * <https://www.gnu.org/licenses/>.
 */

#include "config.h"

#include <cairo.h>
#include <gegl.h>
#include <gdk-pixbuf/gdk-pixbuf.h>

#include "libgimpbase/gimpbase.h"
#include "libgimpcolor/gimpcolor.h"

#include "gimpconfigtypes.h"

#include "gimpcolorconfig.h"
#include "gimpconfig-error.h"
#include "gimpconfig-iface.h"
#include "gimpconfig-params.h"
#include "gimpconfig-path.h"

#include "libgimp/libgimp-intl.h"


/**
 * SECTION: gimpcolorconfig
 * @title: GimpColorConfig
 * @short_description: Color management settings.
 *
 * Color management settings.
 **/


#define COLOR_MANAGEMENT_MODE_BLURB \
  _("How images are displayed on screen.")

#define DISPLAY_PROFILE_BLURB \
  _("The color profile of your (primary) monitor.")

#define DISPLAY_PROFILE_FROM_GDK_BLURB \
  _("When enabled, AmmoOS Image will try to use the display color profile from " \
    "the windowing system.  The configured monitor profile is then only " \
    "used as a fallback.")

#define RGB_PROFILE_BLURB \
  _("The preferred RGB working space color profile. It will be offered " \
    "next to the built-in RGB profile when a color profile can be chosen.")

#define GRAY_PROFILE_BLURB \
  _("The preferred grayscale working space color profile. It will be offered " \
    "next to the built-in grayscale profile when a color profile can be chosen.")

#define CMYK_PROFILE_BLURB \
  _("The CMYK color profile used to convert between RGB and CMYK.")

#define SIMULATION_PROFILE_BLURB \
  _("The color profile to use for soft-proofing from your image's " \
    "color space to some other color space, including " \
    "soft-proofing to a printer or other output device profile.")

#define DISPLAY_RENDERING_INTENT_BLURB \
  _("How colors are converted from your image's color space to your " \
    "display device. Relative colorimetric is usually the best choice. " \
    "Unless you use a LUT monitor profile (most monitor profiles are " \
    "matrix), choosing perceptual intent really gives you relative " \
    "colorimetric." )

#define DISPLAY_USE_BPC_BLURB \
  _("Do use black point compensation (unless you know you have a reason " \
    "not to).")

#define DISPLAY_OPTIMIZE_BLURB \
  _("When disabled, image display might be of better quality " \
    "at the cost of speed.")

#define SIMULATION_RENDERING_INTENT_BLURB \
  _("How colors are converted from your image's color space to the "  \
    "output simulation device (usually your monitor). " \
    "Try them all and choose what looks the best.")

#define SIMULATION_USE_BPC_BLURB \
  _("Try with and without black point compensation "\
    "and choose what looks best.")

#define SIMULATION_OPTIMIZE_BLURB \
  _("When disabled, soft-proofing might be of better quality " \
    "at the cost of speed.")

#define SIMULATION_GAMUT_CHECK_BLURB \
  _("When enabled, the soft-proofing will mark colors " \
    "which can not be represented in the target color space.")

#define OUT_OF_GAMUT_COLOR_BLURB \
  _("The color to use for marking colors which are out of gamut.")

#define SHOW_RGB_U8_BLURB \
  _("When enabled, set the color scales to display 0...255 instead " \
    "of percentages")

#define SHOW_HSV_BLURB \
  _("When enabled, set the color scales to display HSV blend mode instead " \
    "of LCh")

enum
{
  PROP_0,
  PROP_MODE,
  PROP_RGB_PROFILE,
  PROP_GRAY_PROFILE,
  PROP_CMYK_PROFILE,
  PROP_DISPLAY_PROFILE,
  PROP_DISPLAY_PROFILE_FROM_GDK,
  PROP_SIMULATION_PROFILE,
  PROP_DISPLAY_RENDERING_INTENT,
  PROP_DISPLAY_USE_BPC,
  PROP_DISPLAY_OPTIMIZE,
  PROP_SIMULATION_RENDERING_INTENT,
  PROP_SIMULATION_USE_BPC,
  PROP_SIMULATION_OPTIMIZE,
  PROP_SIMULATION_GAMUT_CHECK,
  PROP_OUT_OF_GAMUT_COLOR,
  PROP_SHOW_RGB_U8,
  PROP_SHOW_HSV
};


struct _GimpColorConfig
{
  GObject                   parent_instance;

  GimpColorManagementMode   mode;

  gchar                    *rgb_profile;
  gchar                    *gray_profile;
  gchar                    *cmyk_profile;
  gchar                    *display_profile;
  gboolean                  display_profile_from_gdk;
  gchar                    *printer_profile;

  GimpColorRenderingIntent  display_intent;
  gboolean                  display_use_black_point_compensation;
  gboolean                  display_optimize;

  GimpColorRenderingIntent  simulation_intent;
  gboolean                  simulation_use_black_point_compensation;
  gboolean                  simulation_optimize;
  gboolean                  simulation_gamut_check;
  GeglColor                *out_of_gamut_color;

  gboolean                  show_rgb_u8;
  gboolean                  show_hsv;
};


static void  gimp_color_config_finalize               (GObject          *object);
static void  gimp_color_config_set_property           (GObject          *object,
                                                       guint             property_id,
                                                       const GValue     *value,
                                                       GParamSpec       *pspec);
static void  gimp_color_config_get_property           (GObject          *object,
                                                       guint             property_id,
                                                       GValue           *value,
                                                       GParamSpec       *pspec);

static void  gimp_color_config_set_rgb_profile        (GimpColorConfig  *config,
                                                       const gchar      *filename,
                                                       GError          **error);
static void  gimp_color_config_set_gray_profile       (GimpColorConfig  *config,
                                                       const gchar      *filename,
                                                       GError          **error);
static void  gimp_color_config_set_cmyk_profile       (GimpColorConfig  *config,
                                                       const gchar      *filename,
                                                       GError          **error);
static void  gimp_color_config_set_display_profile    (GimpColorConfig  *config,
                                                       const gchar      *filename,
                                                       GError          **error);
static void  gimp_color_config_set_simulation_profile (GimpColorConfig  *config,
                                                       const gchar      *filename,
                                                       GError          **error);


G_DEFINE_TYPE_WITH_CODE (GimpColorConfig, gimp_color_config, G_TYPE_OBJECT,
                         G_IMPLEMENT_INTERFACE (GIMP_TYPE_CONFIG, NULL)
                         gimp_type_set_translation_domain (g_define_type_id,
                                                           GETTEXT_PACKAGE "-libgimp"))

#define parent_class gimp_color_config_parent_class


static void
gimp_color_config_class_init (GimpColorConfigClass *klass)
{
  GObjectClass *object_class = G_OBJECT_CLASS (klass);
  GeglColor    *magenta;

  babl_init ();

  /* Magenta (sRGB space). */
  magenta = gegl_color_new (NULL);
  gegl_color_set_rgba (magenta, 1.0, 0.0, 1.0, 1.0);

  object_class->finalize     = gimp_color_config_finalize;
  object_class->set_property = gimp_color_config_set_property;
  object_class->get_property = gimp_color_config_get_property;

  GIMP_CONFIG_PROP_ENUM (object_class, PROP_MODE,
                         "mode",
                         _("Mode of operation"),
                         COLOR_MANAGEMENT_MODE_BLURB,
                         GIMP_TYPE_COLOR_MANAGEMENT_MODE,
                         GIMP_COLOR_MANAGEMENT_DISPLAY,
                         GIMP_PARAM_STATIC_STRINGS);

  GIMP_CONFIG_PROP_PATH (object_class, PROP_RGB_PROFILE,
                         "rgb-profile",
                         _("Preferred RGB profile"),
                         RGB_PROFILE_BLURB,
                         GIMP_CONFIG_PATH_FILE, NULL,
                         GIMP_PARAM_STATIC_STRINGS);

  GIMP_CONFIG_PROP_PATH (object_class, PROP_GRAY_PROFILE,
                         "gray-profile",
                         _("Preferred grayscale profile"),
                         GRAY_PROFILE_BLURB,
                         GIMP_CONFIG_PATH_FILE, NULL,
                         GIMP_PARAM_STATIC_STRINGS);

  GIMP_CONFIG_PROP_PATH (object_class, PROP_CMYK_PROFILE,
                         "cmyk-profile",
                         _("CMYK profile"),
                         CMYK_PROFILE_BLURB,
                         GIMP_CONFIG_PATH_FILE, NULL,
                         GIMP_PARAM_STATIC_STRINGS);

  GIMP_CONFIG_PROP_PATH (object_class, PROP_DISPLAY_PROFILE,
                         "display-profile",
                         _("Monitor profile"),
                         DISPLAY_PROFILE_BLURB,
                         GIMP_CONFIG_PATH_FILE, NULL,
                         GIMP_PARAM_STATIC_STRINGS);

  GIMP_CONFIG_PROP_BOOLEAN (object_class, PROP_DISPLAY_PROFILE_FROM_GDK,
                            "display-profile-from-gdk",
                            _("Use the system monitor profile"),
                            DISPLAY_PROFILE_FROM_GDK_BLURB,
                            FALSE,
                            GIMP_PARAM_STATIC_STRINGS);

  GIMP_CONFIG_PROP_PATH (object_class, PROP_SIMULATION_PROFILE,
                         "simulation-profile",
                         _("Simulation profile for soft-proofing"),
                         SIMULATION_PROFILE_BLURB,
                         GIMP_CONFIG_PATH_FILE, NULL,
                         GIMP_PARAM_STATIC_STRINGS);

  GIMP_CONFIG_PROP_ENUM (object_class, PROP_DISPLAY_RENDERING_INTENT,
                         "display-rendering-intent",
                         _("Display rendering intent"),
                         DISPLAY_RENDERING_INTENT_BLURB,
                         GIMP_TYPE_COLOR_RENDERING_INTENT,
                         GIMP_COLOR_RENDERING_INTENT_RELATIVE_COLORIMETRIC,
                         GIMP_PARAM_STATIC_STRINGS);

  GIMP_CONFIG_PROP_BOOLEAN (object_class, PROP_DISPLAY_USE_BPC,
                            "display-use-black-point-compensation",
                            _("Use black point compensation for the display"),
                            DISPLAY_USE_BPC_BLURB,
                            TRUE,
                            GIMP_PARAM_STATIC_STRINGS);

  GIMP_CONFIG_PROP_BOOLEAN (object_class, PROP_DISPLAY_OPTIMIZE,
                            "display-optimize",
                            _("Optimize display color transformations"),
                            DISPLAY_OPTIMIZE_BLURB,
                            TRUE,
                            GIMP_PARAM_STATIC_STRINGS);

  GIMP_CONFIG_PROP_ENUM (object_class, PROP_SIMULATION_RENDERING_INTENT,
                         "simulation-rendering-intent",
                         _("Soft-proofing rendering intent"),
                         SIMULATION_RENDERING_INTENT_BLURB,
                         GIMP_TYPE_COLOR_RENDERING_INTENT,
                         GIMP_COLOR_RENDERING_INTENT_PERCEPTUAL,
                         GIMP_PARAM_STATIC_STRINGS);

  GIMP_CONFIG_PROP_BOOLEAN (object_class, PROP_SIMULATION_USE_BPC,
                            "simulation-use-black-point-compensation",
                            _("Use black point compensation for soft-proofing"),
                            SIMULATION_USE_BPC_BLURB,
                            FALSE,
                            GIMP_PARAM_STATIC_STRINGS);

  GIMP_CONFIG_PROP_BOOLEAN (object_class, PROP_SIMULATION_OPTIMIZE,
                            "simulation-optimize",
                            _("Optimize soft-proofing color transformations"),
                            SIMULATION_OPTIMIZE_BLURB,
                            TRUE,
                            GIMP_PARAM_STATIC_STRINGS);

  GIMP_CONFIG_PROP_BOOLEAN (object_class, PROP_SIMULATION_GAMUT_CHECK,
                            "simulation-gamut-check",
                            _("Mark out of gamut colors"),
                            SIMULATION_GAMUT_CHECK_BLURB,
                            FALSE,
                            GIMP_PARAM_STATIC_STRINGS);

  GIMP_CONFIG_PROP_COLOR (object_class, PROP_OUT_OF_GAMUT_COLOR,
                          "out-of-gamut-color",
                          _("Out of gamut warning color"),
                          OUT_OF_GAMUT_COLOR_BLURB,
                          FALSE, magenta,
                          GIMP_PARAM_STATIC_STRINGS);

  GIMP_CONFIG_PROP_BOOLEAN (object_class, PROP_SHOW_RGB_U8,
                            "show-rgb-u8",
                            "Show RGB 0..255",
                            _("Show RGB 0..255 scales"),
                            FALSE,
                            GIMP_PARAM_STATIC_STRINGS);

  GIMP_CONFIG_PROP_BOOLEAN (object_class, PROP_SHOW_HSV,
                            "show-hsv",
                            "Show HSV",
                            _("Show HSV instead of LCH"),
                            FALSE,
                            GIMP_PARAM_STATIC_STRINGS);

  g_object_unref (magenta);
}

static void
gimp_color_config_init (GimpColorConfig *config)
{
  GeglColor *magenta = gegl_color_new (NULL);

  /* Magenta (sRGB space). */
  gegl_color_set_rgba (magenta, 1.0, 0.0, 1.0, 1.0);
  config->out_of_gamut_color = magenta;
}

static void
gimp_color_config_finalize (GObject *object)
{
  GimpColorConfig *config = GIMP_COLOR_CONFIG (object);

  g_clear_pointer (&config->rgb_profile,     g_free);
  g_clear_pointer (&config->gray_profile,    g_free);
  g_clear_pointer (&config->cmyk_profile,    g_free);
  g_clear_pointer (&config->display_profile, g_free);
  g_clear_pointer (&config->printer_profile, g_free);

  G_OBJECT_CLASS (parent_class)->finalize (object);
}

static void
gimp_color_config_set_property (GObject      *object,
                                guint         property_id,
                                const GValue *value,
                                GParamSpec   *pspec)
{
  GimpColorConfig *config = GIMP_COLOR_CONFIG (object);
  GError          *error  = NULL;

  switch (property_id)
    {
    case PROP_MODE:
      config->mode = g_value_get_enum (value);
      break;
    case PROP_RGB_PROFILE:
      gimp_color_config_set_rgb_profile (config,
                                         g_value_get_string (value),
                                         &error);
      break;
    case PROP_GRAY_PROFILE:
      gimp_color_config_set_gray_profile (config,
                                          g_value_get_string (value),
                                          &error);
      break;
    case PROP_CMYK_PROFILE:
      gimp_color_config_set_cmyk_profile (config,
                                          g_value_get_string (value),
                                          &error);
      break;
    case PROP_DISPLAY_PROFILE:
      gimp_color_config_set_display_profile (config,
                                             g_value_get_string (value),
                                             &error);
      break;
    case PROP_DISPLAY_PROFILE_FROM_GDK:
      config->display_profile_from_gdk = g_value_get_boolean (value);
      break;
    case PROP_SIMULATION_PROFILE:
      gimp_color_config_set_simulation_profile (config,
                                                g_value_get_string (value),
                                                &error);
      break;
    case PROP_DISPLAY_RENDERING_INTENT:
      config->display_intent = g_value_get_enum (value);
      break;
    case PROP_DISPLAY_USE_BPC:
      config->display_use_black_point_compensation = g_value_get_boolean (value);
      break;
    case PROP_DISPLAY_OPTIMIZE:
      config->display_optimize = g_value_get_boolean (value);
      break;
    case PROP_SIMULATION_RENDERING_INTENT:
      config->simulation_intent = g_value_get_enum (value);
      break;
    case PROP_SIMULATION_USE_BPC:
      config->simulation_use_black_point_compensation = g_value_get_boolean (value);
      break;
    case PROP_SIMULATION_OPTIMIZE:
      config->simulation_optimize = g_value_get_boolean (value);
      break;
    case PROP_SIMULATION_GAMUT_CHECK:
      config->simulation_gamut_check = g_value_get_boolean (value);
      break;
    case PROP_OUT_OF_GAMUT_COLOR:
      g_clear_object (&config->out_of_gamut_color);
      config->out_of_gamut_color = gegl_color_duplicate (g_value_get_object (value));
      break;
    case PROP_SHOW_RGB_U8:
      config->show_rgb_u8 = g_value_get_boolean (value);
      break;
    case PROP_SHOW_HSV:
      config->show_hsv = g_value_get_boolean (value);
      break;

    default:
      G_OBJECT_WARN_INVALID_PROPERTY_ID (object, property_id, pspec);
      break;
    }

  if (error)
    {
      g_message ("%s", error->message);
      g_clear_error (&error);
    }
}

static void
gimp_color_config_get_property (GObject    *object,
                                guint       property_id,
                                GValue     *value,
                                GParamSpec *pspec)
{
  GimpColorConfig *config = GIMP_COLOR_CONFIG (object);

  switch (property_id)
    {
    case PROP_MODE:
      g_value_set_enum (value, config->mode);
      break;
    case PROP_RGB_PROFILE:
      g_value_set_string (value, config->rgb_profile);
      break;
    case PROP_GRAY_PROFILE:
      g_value_set_string (value, config->gray_profile);
      break;
    case PROP_CMYK_PROFILE:
      g_value_set_string (value, config->cmyk_profile);
      break;
    case PROP_DISPLAY_PROFILE:
      g_value_set_string (value, config->display_profile);
      break;
    case PROP_DISPLAY_PROFILE_FROM_GDK:
      g_value_set_boolean (value, config->display_profile_from_gdk);
      break;
    case PROP_SIMULATION_PROFILE:
      g_value_set_string (value, config->printer_profile);
      break;
    case PROP_DISPLAY_RENDERING_INTENT:
      g_value_set_enum (value, config->display_intent);
      break;
    case PROP_DISPLAY_USE_BPC:
      g_value_set_boolean (value, config->display_use_black_point_compensation);
      break;
    case PROP_DISPLAY_OPTIMIZE:
      g_value_set_boolean (value, config->display_optimize);
      break;
    case PROP_SIMULATION_RENDERING_INTENT:
      g_value_set_enum (value, config->simulation_intent);
      break;
    case PROP_SIMULATION_USE_BPC:
      g_value_set_boolean (value, config->simulation_use_black_point_compensation);
      break;
    case PROP_SIMULATION_OPTIMIZE:
      g_value_set_boolean (value, config->simulation_optimize);
      break;
    case PROP_SIMULATION_GAMUT_CHECK:
      g_value_set_boolean (value, config->simulation_gamut_check);
      break;
    case PROP_OUT_OF_GAMUT_COLOR:
      g_value_set_object (value, config->out_of_gamut_color);
      break;
    case PROP_SHOW_RGB_U8:
      g_value_set_boolean (value, config->show_rgb_u8);
      break;
    case PROP_SHOW_HSV:
      g_value_set_boolean (value, config->show_hsv);
      break;

    default:
      G_OBJECT_WARN_INVALID_PROPERTY_ID (object, property_id, pspec);
      break;
    }
}


/*  public functions  */

/**
 * gimp_color_config_get_mode:
 * @config: a #GimpColorConfig
 *
 * Since: 2.10
 **/
GimpColorManagementMode
gimp_color_config_get_mode (GimpColorConfig *config)
{
  g_return_val_if_fail (GIMP_IS_COLOR_CONFIG (config),
                        GIMP_COLOR_MANAGEMENT_OFF);

  return config->mode;
}

/**
 * gimp_color_config_get_display_intent:
 * @config: a #GimpColorConfig
 *
 * Since: 2.10
 **/
GimpColorRenderingIntent
gimp_color_config_get_display_intent (GimpColorConfig *config)
{
  g_return_val_if_fail (GIMP_IS_COLOR_CONFIG (config),
                        GIMP_COLOR_RENDERING_INTENT_PERCEPTUAL);

  return config->display_intent;
}

/**
 * gimp_color_config_get_display_bpc:
 * @config: a #GimpColorConfig
 *
 * Since: 2.10
 **/
gboolean
gimp_color_config_get_display_bpc (GimpColorConfig *config)
{
  g_return_val_if_fail (GIMP_IS_COLOR_CONFIG (config), FALSE);

  return config->display_use_black_point_compensation;
}

/**
 * gimp_color_config_get_display_optimize:
 * @config: a #GimpColorConfig
 *
 * Since: 2.10
 **/
gboolean
gimp_color_config_get_display_optimize (GimpColorConfig *config)
{
  g_return_val_if_fail (GIMP_IS_COLOR_CONFIG (config), FALSE);

  return config->display_optimize;
}

/**
 * gimp_color_config_get_display_profile_from_gdk:
 * @config: a #GimpColorConfig
 *
 * Since: 2.10
 **/
gboolean
gimp_color_config_get_display_profile_from_gdk (GimpColorConfig *config)
{
  g_return_val_if_fail (GIMP_IS_COLOR_CONFIG (config), FALSE);

  return config->display_profile_from_gdk;
}

/**
 * gimp_color_config_get_simulation_intent:
 * @config: a #GimpColorConfig
 *
 * Since: 2.10
 **/
GimpColorRenderingIntent
gimp_color_config_get_simulation_intent (GimpColorConfig *config)
{
  g_return_val_if_fail (GIMP_IS_COLOR_CONFIG (config),
                        GIMP_COLOR_RENDERING_INTENT_PERCEPTUAL);

  return config->simulation_intent;
}

/**
 * gimp_color_config_get_simulation_bpc:
 * @config: a #GimpColorConfig
 *
 * Since: 2.10
 **/
gboolean
gimp_color_config_get_simulation_bpc (GimpColorConfig *config)
{
  g_return_val_if_fail (GIMP_IS_COLOR_CONFIG (config), FALSE);

  return config->simulation_use_black_point_compensation;
}

/**
 * gimp_color_config_get_simulation_optimize:
 * @config: a #GimpColorConfig
 *
 * Since: 2.10
 **/
gboolean
gimp_color_config_get_simulation_optimize (GimpColorConfig *config)
{
  g_return_val_if_fail (GIMP_IS_COLOR_CONFIG (config), FALSE);

  return config->simulation_optimize;
}

/**
 * gimp_color_config_get_simulation_gamut_check:
 * @config: a #GimpColorConfig
 *
 * Since: 2.10
 **/
gboolean
gimp_color_config_get_simulation_gamut_check (GimpColorConfig *config)
{
  g_return_val_if_fail (GIMP_IS_COLOR_CONFIG (config), FALSE);

  return config->simulation_gamut_check;
}

/**
 * gimp_color_config_get_out_of_gamut_color:
 * @config: a #GimpColorConfig
 *
 * Returns: (transfer full): the [class@Gegl.Color] to use to represent
 *                           out-of-gamut pixels.
 * Since: 3.0
 **/
GeglColor *
gimp_color_config_get_out_of_gamut_color (GimpColorConfig *config)
{
  g_return_val_if_fail (GIMP_IS_COLOR_CONFIG (config), NULL);

  return gegl_color_duplicate (config->out_of_gamut_color);
}

/**
 * gimp_color_config_get_rgb_color_profile:
 * @config: a #GimpColorConfig
 * @error:  return location for a #GError
 *
 * Returns: (transfer full): the default RGB color profile.
 *
 * Since: 2.10
 **/
GimpColorProfile *
gimp_color_config_get_rgb_color_profile (GimpColorConfig  *config,
                                         GError          **error)
{
  GimpColorProfile *profile = NULL;

  g_return_val_if_fail (GIMP_IS_COLOR_CONFIG (config), NULL);
  g_return_val_if_fail (error == NULL || *error == NULL, NULL);

  if (config->rgb_profile)
    {
      GFile *file = gimp_file_new_for_config_path (config->rgb_profile, error);

      if (file)
        {
          profile = gimp_color_profile_new_from_file (file, error);

          if (profile && ! gimp_color_profile_is_rgb (profile))
            {
              g_object_unref (profile);
              profile = NULL;

              g_set_error (error, GIMP_CONFIG_ERROR, 0,
                           _("Color profile '%s' is not for RGB color space."),
                           gimp_file_get_utf8_name (file));
            }

          g_object_unref (file);
        }
    }

  return profile;
}

/**
 * gimp_color_config_get_gray_color_profile:
 * @config: a #GimpColorConfig
 * @error:  return location for a #GError
 *
 * Returns: (transfer full): the default grayscale color profile.
 *
 * Since: 2.10
 **/
GimpColorProfile *
gimp_color_config_get_gray_color_profile (GimpColorConfig  *config,
                                          GError          **error)
{
  GimpColorProfile *profile = NULL;

  g_return_val_if_fail (GIMP_IS_COLOR_CONFIG (config), NULL);
  g_return_val_if_fail (error == NULL || *error == NULL, NULL);

  if (config->gray_profile)
    {
      GFile *file = gimp_file_new_for_config_path (config->gray_profile, error);

      if (file)
        {
          profile = gimp_color_profile_new_from_file (file, error);

          if (profile && ! gimp_color_profile_is_gray (profile))
            {
              g_object_unref (profile);
              profile = NULL;

              g_set_error (error, GIMP_CONFIG_ERROR, 0,
                           _("Color profile '%s' is not for GRAY color space."),
                           gimp_file_get_utf8_name (file));
            }

          g_object_unref (file);
        }
    }

  return profile;
}

/**
 * gimp_color_config_get_cmyk_color_profile:
 * @config: a #GimpColorConfig
 * @error:  return location for a #GError
 *
 * Returns: (transfer full): the default CMYK color profile.
 *
 * Since: 2.10
 **/
GimpColorProfile *
gimp_color_config_get_cmyk_color_profile (GimpColorConfig  *config,
                                          GError          **error)
{
  GimpColorProfile *profile = NULL;

  g_return_val_if_fail (GIMP_IS_COLOR_CONFIG (config), NULL);
  g_return_val_if_fail (error == NULL || *error == NULL, NULL);

  if (config->cmyk_profile)
    {
      GFile *file = gimp_file_new_for_config_path (config->cmyk_profile, error);

      if (file)
        {
          profile = gimp_color_profile_new_from_file (file, error);

          if (profile && ! gimp_color_profile_is_cmyk (profile))
            {
              g_object_unref (profile);
              profile = NULL;

              g_set_error (error, GIMP_CONFIG_ERROR, 0,
                           _("Color profile '%s' is not for CMYK color space."),
                           gimp_file_get_utf8_name (file));
            }

          g_object_unref (file);
        }
    }

  return profile;
}

/**
 * gimp_color_config_get_display_color_profile:
 * @config: a #GimpColorConfig
 * @error:  return location for a #GError
 *
 * Returns: (transfer full): the default display color profile.
 *
 * Since: 2.10
 **/
GimpColorProfile *
gimp_color_config_get_display_color_profile (GimpColorConfig  *config,
                                             GError          **error)
{
  GimpColorProfile *profile = NULL;

  g_return_val_if_fail (GIMP_IS_COLOR_CONFIG (config), NULL);
  g_return_val_if_fail (error == NULL || *error == NULL, NULL);

  if (config->display_profile)
    {
      GFile *file = gimp_file_new_for_config_path (config->display_profile, error);

      if (file)
        {
          profile = gimp_color_profile_new_from_file (file, error);

          g_object_unref (file);
        }
    }

  return profile;
}

/**
 * gimp_color_config_get_simulation_color_profile:
 * @config: a #GimpColorConfig
 * @error:  return location for a #GError
 *
 * Returns: (transfer full): the default soft-proofing color
 *                                profile.
 *
 * Since: 2.10
 **/
GimpColorProfile *
gimp_color_config_get_simulation_color_profile (GimpColorConfig  *config,
                                                GError          **error)
{
  GimpColorProfile *profile = NULL;

  g_return_val_if_fail (GIMP_IS_COLOR_CONFIG (config), NULL);
  g_return_val_if_fail (error == NULL || *error == NULL, NULL);

  if (config->printer_profile)
    {
      GFile *file = gimp_file_new_for_config_path (config->printer_profile, error);

      if (file)
        {
          profile = gimp_color_profile_new_from_file (file, error);

          g_object_unref (file);
        }
    }

  return profile;
}


/*  private functions  */

static void
gimp_color_config_set_rgb_profile (GimpColorConfig  *config,
                                   const gchar      *filename,
                                   GError          **error)
{
  gboolean success = TRUE;

  if (filename)
    {
      GFile *file = gimp_file_new_for_config_path (filename, error);

      if (file)
        {
          GimpColorProfile *profile;

          profile = gimp_color_profile_new_from_file (file, error);

          if (profile)
            {
              if (! gimp_color_profile_is_rgb (profile))
                {
                  g_set_error (error, GIMP_CONFIG_ERROR, 0,
                               _("Color profile '%s' is not for RGB "
                                 "color space."),
                               gimp_file_get_utf8_name (file));
                  success = FALSE;
                }

              g_object_unref (profile);
            }
          else
            {
              success = FALSE;
            }

          g_object_unref (file);
        }
      else
        {
          success = FALSE;
        }
    }

  if (success)
    {
      g_free (config->rgb_profile);
      config->rgb_profile = g_strdup (filename);
    }
}

static void
gimp_color_config_set_gray_profile (GimpColorConfig  *config,
                                    const gchar      *filename,
                                    GError          **error)
{
  gboolean success = TRUE;

  if (filename)
    {
      GFile *file = gimp_file_new_for_config_path (filename, error);

      if (file)
        {
          GimpColorProfile *profile;

          profile = gimp_color_profile_new_from_file (file, error);

          if (profile)
            {
              if (! gimp_color_profile_is_gray (profile))
                {
                  g_set_error (error, GIMP_CONFIG_ERROR, 0,
                               _("Color profile '%s' is not for GRAY "
                                 "color space."),
                               gimp_file_get_utf8_name (file));
                  success = FALSE;
                }

              g_object_unref (profile);
            }
          else
            {
              success = FALSE;
            }

          g_object_unref (file);
        }
      else
        {
          success = FALSE;
        }
    }

  if (success)
    {
      g_free (config->gray_profile);
      config->gray_profile = g_strdup (filename);
    }
}

static void
gimp_color_config_set_cmyk_profile (GimpColorConfig  *config,
                                    const gchar      *filename,
                                    GError          **error)
{
  gboolean success = TRUE;

  if (filename)
    {
      GFile *file = gimp_file_new_for_config_path (filename, error);

      if (file)
        {
          GimpColorProfile *profile;

          profile = gimp_color_profile_new_from_file (file, error);

          if (profile)
            {
              if (! gimp_color_profile_is_cmyk (profile))
                {
                  g_set_error (error, GIMP_CONFIG_ERROR, 0,
                               _("Color profile '%s' is not for CMYK "
                                 "color space."),
                               gimp_file_get_utf8_name (file));
                  success = FALSE;
                }

              g_object_unref (profile);
            }
          else
            {
              success = FALSE;
            }

          g_object_unref (file);
        }
      else
        {
          success = FALSE;
        }
    }

  if (success)
    {
      g_free (config->cmyk_profile);
      config->cmyk_profile = g_strdup (filename);
    }
}

static void
gimp_color_config_set_display_profile (GimpColorConfig  *config,
                                       const gchar      *filename,
                                       GError          **error)
{
  gboolean success = TRUE;

  if (filename)
    {
      GFile *file = gimp_file_new_for_config_path (filename, error);

      if (file)
        {
          GimpColorProfile *profile;

          profile = gimp_color_profile_new_from_file (file, error);

          if (profile)
            {
              g_object_unref (profile);
            }
          else
            {
              success = FALSE;
            }

          g_object_unref (file);
        }
      else
        {
          success = FALSE;
        }
    }

  if (success)
    {
      g_free (config->display_profile);
      config->display_profile = g_strdup (filename);
    }
}

static void
gimp_color_config_set_simulation_profile (GimpColorConfig  *config,
                                          const gchar      *filename,
                                          GError          **error)
{
  gboolean success = TRUE;

  if (filename)
    {
      GFile *file = gimp_file_new_for_config_path (filename, error);

      if (file)
        {
          GimpColorProfile *profile;

          profile = gimp_color_profile_new_from_file (file, error);

          if (profile)
            {
              g_object_unref (profile);
            }
          else
            {
              success = FALSE;
            }

          g_object_unref (file);
        }
      else
        {
          success = FALSE;
        }
    }

  if (success)
    {
      g_free (config->printer_profile);
      config->printer_profile = g_strdup (filename);
    }
}

/* --- end libammoos/config/fieldconfig/gimpcolorconfig.c --- */

/* --- begin libammoos/config/fieldconfig/gimpconfig-deserialize.c --- */
/* LIBGIMP - The AmmoOS Image Library
 * Copyright (C) 1995-1997 Spencer Kimball and Peter Mattis
 *
 * Object properties deserialization routines
 * Copyright (C) 2001-2002  Sven Neumann <sven@ammoos.org>
 *
 * This library is free software: you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 3 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Library General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library.  If not, see
 * <https://www.gnu.org/licenses/>.
 */

#include "config.h"

#include <cairo.h>
#include <gegl.h>
#include <gdk-pixbuf/gdk-pixbuf.h>

#include "libgimpbase/gimpbase.h"
#include "libgimpcolor/gimpcolor.h"
#include "libgimpmath/gimpmath.h"

#include "gimpconfigtypes.h"

#include "gimpconfigwriter.h"
#include "gimpconfig-iface.h"
#include "gimpconfig-deserialize.h"
#include "gimpconfig-params.h"
#include "gimpconfig-path.h"
#include "gimpscanner.h"

#include "libgimp/libgimp-intl.h"


/**
 * SECTION: gimpconfig-deserialize
 * @title: GimpConfig-deserialize
 * @short_description: Deserializing code for libgimpconfig.
 *
 * Deserializing code for libgimpconfig.
 **/


/*
 *  All functions return G_TOKEN_RIGHT_PAREN on success,
 *  the GTokenType they would have expected but didn't get
 *  or G_TOKEN_NONE if they got the expected token but
 *  couldn't parse it.
 */

static GTokenType  gimp_config_deserialize_value          (GValue     *value,
                                                           GimpConfig *config,
                                                           GParamSpec *prop_spec,
                                                           GScanner   *scanner);
static GTokenType  gimp_config_deserialize_fundamental    (GValue     *value,
                                                           GParamSpec *prop_spec,
                                                           GScanner   *scanner);
static GTokenType  gimp_config_deserialize_enum           (GValue     *value,
                                                           GParamSpec *prop_spec,
                                                           GScanner   *scanner);
static GTokenType  gimp_config_deserialize_memsize        (GValue     *value,
                                                           GParamSpec *prop_spec,
                                                           GScanner   *scanner);
static GTokenType  gimp_config_deserialize_path           (GValue     *value,
                                                           GParamSpec *prop_spec,
                                                           GScanner   *scanner);
static GTokenType  gimp_config_deserialize_matrix2        (GValue     *value,
                                                           GParamSpec *prop_spec,
                                                           GScanner   *scanner);
static GTokenType  gimp_config_deserialize_object         (GValue     *value,
                                                           GimpConfig *config,
                                                           GParamSpec *prop_spec,
                                                           GScanner   *scanner,
                                                           gint        nest_level);
static GTokenType  gimp_config_deserialize_value_array    (GValue     *value,
                                                           GimpConfig *config,
                                                           GParamSpec *prop_spec,
                                                           GScanner   *scanner);
static GTokenType  gimp_config_deserialize_array          (GValue     *value,
                                                           GScanner   *scanner);
static GTokenType  gimp_config_deserialize_strv           (GValue     *value,
                                                           GScanner   *scanner);
static GimpUnit  * gimp_config_get_unit_from_identifier   (const gchar *identifier);
static GTokenType  gimp_config_deserialize_unit           (GValue     *value,
                                                           GParamSpec *prop_spec,
                                                           GScanner   *scanner);
static GTokenType  gimp_config_deserialize_file_value     (GValue     *value,
                                                           GParamSpec *prop_spec,
                                                           GScanner   *scanner);
static GTokenType  gimp_config_deserialize_parasite_value (GValue     *value,
                                                           GParamSpec *prop_spec,
                                                           GScanner   *scanner);
static GTokenType  gimp_config_deserialize_bytes          (GValue     *value,
                                                           GParamSpec *prop_spec,
                                                           GScanner   *scanner);
static GTokenType  gimp_config_deserialize_color          (GValue     *value,
                                                           GParamSpec *prop_spec,
                                                           GScanner   *scanner);
static GTokenType  gimp_config_deserialize_any            (GValue     *value,
                                                           GParamSpec *prop_spec,
                                                           GScanner   *scanner);
static GTokenType  gimp_config_skip_unknown_property      (GScanner   *scanner);

static inline gboolean  scanner_string_utf8_valid (GScanner    *scanner,
                                                   const gchar *token_name);

static inline gboolean
scanner_string_utf8_valid (GScanner    *scanner,
                           const gchar *token_name)
{
  if (g_utf8_validate (scanner->value.v_string, -1, NULL))
    return TRUE;

  g_scanner_error (scanner,
                   _("value for token %s is not a valid UTF-8 string"),
                   token_name);

  return FALSE;
}

/**
 * gimp_config_deserialize_properties:
 * @config: a #GimpConfig.
 * @scanner: a #GScanner.
 * @nest_level: the nest level
 *
 * This function uses the @scanner to configure the properties of @config.
 *
 * Returns: %TRUE on success, %FALSE otherwise.
 *
 * Since: 2.4
 **/
gboolean
gimp_config_deserialize_properties (GimpConfig *config,
                                    GScanner   *scanner,
                                    gint        nest_level)
{
  GObjectClass  *klass;
  GParamSpec   **property_specs;
  guint          n_property_specs;
  guint          i;
  guint          scope_id;
  guint          old_scope_id;
  GTokenType     token;

  g_return_val_if_fail (GIMP_IS_CONFIG (config), FALSE);

  klass = G_OBJECT_GET_CLASS (config);
  property_specs = g_object_class_list_properties (klass, &n_property_specs);

  if (! property_specs)
    return TRUE;

  scope_id = g_type_qname (G_TYPE_FROM_INSTANCE (config));
  old_scope_id = g_scanner_set_scope (scanner, scope_id);

  for (i = 0; i < n_property_specs; i++)
    {
      GParamSpec *prop_spec = property_specs[i];

      if (prop_spec->flags & GIMP_CONFIG_PARAM_SERIALIZE)
        {
          g_scanner_scope_add_symbol (scanner, scope_id,
                                      prop_spec->name, prop_spec);
        }
    }

  g_free (property_specs);

  g_object_freeze_notify (G_OBJECT (config));

  token = G_TOKEN_LEFT_PAREN;

  while (TRUE)
    {
      GTokenType next = g_scanner_peek_next_token (scanner);

      if (next == G_TOKEN_EOF)
        break;

      if (G_UNLIKELY (next != token &&
                      ! (token == G_TOKEN_SYMBOL &&
                         next  == G_TOKEN_IDENTIFIER)))
        {
          break;
        }

      token = g_scanner_get_next_token (scanner);

      switch (token)
        {
        case G_TOKEN_LEFT_PAREN:
          token = G_TOKEN_SYMBOL;
          break;

        case G_TOKEN_IDENTIFIER:
          token = gimp_config_skip_unknown_property (scanner);
          break;

        case G_TOKEN_SYMBOL:
          token = gimp_config_deserialize_property (config,
                                                    scanner, nest_level);
          break;

        case G_TOKEN_RIGHT_PAREN:
          token = G_TOKEN_LEFT_PAREN;
          break;

        default: /* do nothing */
          break;
        }
    }

  g_scanner_set_scope (scanner, old_scope_id);

  g_object_thaw_notify (G_OBJECT (config));

  if (token == G_TOKEN_NONE)
    return FALSE;

  return gimp_config_deserialize_return (scanner, token, nest_level);
}

/**
 * gimp_config_deserialize_property:
 * @config: a #GimpConfig.
 * @scanner: a #GScanner.
 * @nest_level: the nest level
 *
 * This function deserializes a single property of @config. You
 * shouldn't need to call this function directly. If possible, use
 * gimp_config_deserialize_properties() instead.
 *
 * Returns: %G_TOKEN_RIGHT_PAREN on success, otherwise the
 * expected #GTokenType or %G_TOKEN_NONE if the expected token was
 * found but couldn't be parsed.
 *
 * Since: 2.4
 **/
GTokenType
gimp_config_deserialize_property (GimpConfig *config,
                                  GScanner   *scanner,
                                  gint        nest_level)
{
  GimpConfigInterface *config_iface = NULL;
  GimpConfigInterface *parent_iface = NULL;
  GParamSpec          *prop_spec;
  GTokenType           token        = G_TOKEN_RIGHT_PAREN;
  GValue               value        = G_VALUE_INIT;
  guint                old_scope_id;

  old_scope_id = g_scanner_set_scope (scanner, 0);

  prop_spec = G_PARAM_SPEC (scanner->value.v_symbol);

  g_value_init (&value, prop_spec->value_type);

  if (G_TYPE_IS_OBJECT (prop_spec->owner_type))
    {
      GTypeClass *owner_class = g_type_class_peek (prop_spec->owner_type);

      config_iface = g_type_interface_peek (owner_class, GIMP_TYPE_CONFIG);

      /*  We must call deserialize_property() *only* if the *exact* class
       *  which implements it is param_spec->owner_type's class.
       *
       *  Therefore, we ask param_spec->owner_type's immediate parent class
       *  for it's GimpConfigInterface and check if we get a different
       *  pointer.
       *
       *  (if the pointers are the same, param_spec->owner_type's
       *   GimpConfigInterface is inherited from one of it's parent classes
       *   and thus not able to handle param_spec->owner_type's properties).
       */
      if (config_iface)
        {
          GTypeClass *owner_parent_class;

          owner_parent_class = g_type_class_peek_parent (owner_class);

          parent_iface = g_type_interface_peek (owner_parent_class,
                                                GIMP_TYPE_CONFIG);
        }
    }

  if (config_iface                       &&
      config_iface != parent_iface       && /* see comment above */
      config_iface->deserialize_property &&
      config_iface->deserialize_property (config,
                                          prop_spec->param_id,
                                          &value,
                                          prop_spec,
                                          scanner,
                                          &token))
    {
      /* nop */
    }
  else
    {
      if (G_VALUE_HOLDS_OBJECT (&value)            &&
          G_VALUE_TYPE (&value) != G_TYPE_FILE     &&
          G_VALUE_TYPE (&value) != GEGL_TYPE_COLOR &&
          G_VALUE_TYPE (&value) != GIMP_TYPE_UNIT)
        {
          token = gimp_config_deserialize_object (&value,
                                                  config, prop_spec,
                                                  scanner, nest_level);
        }
      else
        {
          token = gimp_config_deserialize_value (&value,
                                                 config, prop_spec, scanner);
        }
    }

  if (token == G_TOKEN_RIGHT_PAREN &&
      g_scanner_peek_next_token (scanner) == token)
    {
      if (! (prop_spec->flags & GIMP_PARAM_DONT_SERIALIZE) &&
          (GIMP_VALUE_HOLDS_COLOR (&value) ||
           ! (G_VALUE_HOLDS_OBJECT (&value)     &&
              (prop_spec->flags & GIMP_CONFIG_PARAM_AGGREGATE))))
        g_object_set_property (G_OBJECT (config), prop_spec->name, &value);
    }
#ifdef CONFIG_DEBUG
  else
    {
      g_warning ("%s: couldn't deserialize property %s::%s of type %s",
                 G_STRFUNC,
                 g_type_name (G_TYPE_FROM_INSTANCE (config)),
                 prop_spec->name,
                 g_type_name (prop_spec->value_type));
    }
#endif

  g_value_unset (&value);

  g_scanner_set_scope (scanner, old_scope_id);

  return token;
}

static GTokenType
gimp_config_deserialize_value (GValue     *value,
                               GimpConfig *config,
                               GParamSpec *prop_spec,
                               GScanner   *scanner)
{
  if (G_TYPE_FUNDAMENTAL (prop_spec->value_type) == G_TYPE_ENUM)
    {
      return gimp_config_deserialize_enum (value, prop_spec, scanner);
    }
  else if (G_TYPE_IS_FUNDAMENTAL (prop_spec->value_type))
    {
      return gimp_config_deserialize_fundamental (value, prop_spec, scanner);
    }
  else if (prop_spec->value_type == GIMP_TYPE_MEMSIZE)
    {
      return gimp_config_deserialize_memsize (value, prop_spec, scanner);
    }
  else if (prop_spec->value_type == GIMP_TYPE_CONFIG_PATH)
    {
      return  gimp_config_deserialize_path (value, prop_spec, scanner);
    }
  else if (prop_spec->value_type == GIMP_TYPE_MATRIX2)
    {
      return gimp_config_deserialize_matrix2 (value, prop_spec, scanner);
    }
  else if (prop_spec->value_type == GIMP_TYPE_VALUE_ARRAY)
    {
      return gimp_config_deserialize_value_array (value,
                                                  config, prop_spec, scanner);
    }
  else if (prop_spec->value_type == G_TYPE_STRV)
    {
      return gimp_config_deserialize_strv (value, scanner);
    }
  else if (prop_spec->value_type == GIMP_TYPE_INT32_ARRAY ||
           prop_spec->value_type == GIMP_TYPE_DOUBLE_ARRAY)
    {
      return gimp_config_deserialize_array (value, scanner);
    }
  else if (prop_spec->value_type == GIMP_TYPE_UNIT)
    {
      return gimp_config_deserialize_unit (value, prop_spec, scanner);
    }
  else if (prop_spec->value_type == G_TYPE_FILE)
    {
      return gimp_config_deserialize_file_value (value, prop_spec, scanner);
    }
  else if (prop_spec->value_type == GIMP_TYPE_PARASITE)
    {
      return gimp_config_deserialize_parasite_value (value, prop_spec, scanner);
    }
  else if (prop_spec->value_type == G_TYPE_BYTES)
    {
      return gimp_config_deserialize_bytes (value, prop_spec, scanner);
    }
  else if (prop_spec->value_type == GEGL_TYPE_COLOR)
    {
      return gimp_config_deserialize_color (value, prop_spec, scanner);
    }

  /*  This fallback will only work for value_types that
   *  can be transformed from a string value.
   */
  return gimp_config_deserialize_any (value, prop_spec, scanner);
}

static GTokenType
gimp_config_deserialize_fundamental (GValue     *value,
                                     GParamSpec *prop_spec,
                                     GScanner   *scanner)
{
  GTokenType token;
  GTokenType next_token;
  GType      value_type;
  gboolean   negate = FALSE;

  value_type = G_TYPE_FUNDAMENTAL (prop_spec->value_type);

  switch (value_type)
    {
    case G_TYPE_STRING:
      token = G_TOKEN_STRING;
      break;

    case G_TYPE_BOOLEAN:
      token = G_TOKEN_IDENTIFIER;
      break;

    case G_TYPE_INT:
    case G_TYPE_LONG:
    case G_TYPE_INT64:
      if (g_scanner_peek_next_token (scanner) == '-')
        {
          negate = TRUE;
          g_scanner_get_next_token (scanner);
        }
      /*  fallthrough  */
    case G_TYPE_UINT:
    case G_TYPE_ULONG:
    case G_TYPE_UINT64:
      token = G_TOKEN_INT;
      break;

    case G_TYPE_FLOAT:
    case G_TYPE_DOUBLE:
      if (g_scanner_peek_next_token (scanner) == '-')
        {
          negate = TRUE;
          g_scanner_get_next_token (scanner);
        }
      token = G_TOKEN_FLOAT;
      break;

    default:
      g_assert_not_reached ();
      break;
    }

  next_token = g_scanner_peek_next_token (scanner);

  /* we parse integers into floats too, because g_ascii_dtostr()
   * serialized whole number without decimal point
   */
  if (next_token != token &&
      ! (token == G_TOKEN_FLOAT && next_token == G_TOKEN_INT))
    {
      return token;
    }

  g_scanner_get_next_token (scanner);

  switch (value_type)
    {
    case G_TYPE_STRING:
      if (scanner_string_utf8_valid (scanner, prop_spec->name))
        g_value_set_string (value, scanner->value.v_string);
      else
        return G_TOKEN_NONE;
      break;

    case G_TYPE_BOOLEAN:
      if (! g_ascii_strcasecmp (scanner->value.v_identifier, "yes") ||
          ! g_ascii_strcasecmp (scanner->value.v_identifier, "true"))
        g_value_set_boolean (value, TRUE);
      else if (! g_ascii_strcasecmp (scanner->value.v_identifier, "no") ||
               ! g_ascii_strcasecmp (scanner->value.v_identifier, "false"))
        g_value_set_boolean (value, FALSE);
      else
        {
          g_scanner_error
            (scanner,
             /* please don't translate 'yes' and 'no' */
             _("expected 'yes' or 'no' for boolean token %s, got '%s'"),
             prop_spec->name, scanner->value.v_identifier);
          return G_TOKEN_NONE;
        }
      break;

    case G_TYPE_INT:
      g_value_set_int (value, (negate ?
                               - (gint) scanner->value.v_int64 :
                                 (gint) scanner->value.v_int64));
      break;
    case G_TYPE_UINT:
      g_value_set_uint (value, scanner->value.v_int64);
      break;

    case G_TYPE_LONG:
      g_value_set_long (value, (negate ?
                                - (glong) scanner->value.v_int64 :
                                  (glong) scanner->value.v_int64));
      break;
    case G_TYPE_ULONG:
      g_value_set_ulong (value, scanner->value.v_int64);
      break;

    case G_TYPE_INT64:
      g_value_set_int64 (value, (negate ?
                                 - (gint64) scanner->value.v_int64 :
                                   (gint64) scanner->value.v_int64));
      break;
    case G_TYPE_UINT64:
      g_value_set_uint64 (value, scanner->value.v_int64);
      break;

    case G_TYPE_FLOAT:
      if (next_token == G_TOKEN_FLOAT)
        g_value_set_float (value, negate ?
                           - (gfloat) scanner->value.v_float :
                             (gfloat) scanner->value.v_float);
      else
        g_value_set_float (value, negate ?
                           - (gfloat) scanner->value.v_int :
                             (gfloat) scanner->value.v_int);
      break;

    case G_TYPE_DOUBLE:
      if (next_token == G_TOKEN_FLOAT)
        g_value_set_double (value, negate ?
                            - scanner->value.v_float:
                              scanner->value.v_float);
      else
        g_value_set_double (value, negate ?
                            - (gdouble) scanner->value.v_int:
                              (gdouble) scanner->value.v_int);
      break;

    default:
      g_assert_not_reached ();
      break;
    }

  return G_TOKEN_RIGHT_PAREN;
}

static GTokenType
gimp_config_deserialize_enum (GValue     *value,
                              GParamSpec *prop_spec,
                              GScanner   *scanner)
{
  GEnumClass *enum_class;
  GEnumValue *enum_value;

  enum_class = g_type_class_peek (G_VALUE_TYPE (value));

  switch (g_scanner_peek_next_token (scanner))
    {
    case G_TOKEN_IDENTIFIER:
      g_scanner_get_next_token (scanner);

      enum_value = g_enum_get_value_by_nick (enum_class,
                                             scanner->value.v_identifier);
      if (! enum_value)
        enum_value = g_enum_get_value_by_name (enum_class,
                                               scanner->value.v_identifier);
      if (! enum_value)
        {
          /*  if the value was not found, check if we have a compat
           *  enum to find the ideitifier
           */
          GQuark quark       = g_quark_from_static_string ("ammoos-compat-enum");
          GType  compat_type = (GType) g_type_get_qdata (G_VALUE_TYPE (value),
                                                         quark);

          if (compat_type)
            {
              GEnumClass *compat_class = g_type_class_ref (compat_type);

              enum_value = g_enum_get_value_by_nick (compat_class,
                                                     scanner->value.v_identifier);
              if (! enum_value)
                enum_value = g_enum_get_value_by_name (compat_class,
                                                       scanner->value.v_identifier);

              /*  finally, if we found a compat value, make sure the
               *  same value exists in the original enum
               */
              if (enum_value)
                enum_value = g_enum_get_value (enum_class, enum_value->value);

              g_type_class_unref (compat_class);
           }
        }

      if (! enum_value)
        {
          g_scanner_error (scanner,
                           _("invalid value '%s' for token %s"),
                           scanner->value.v_identifier, prop_spec->name);
          return G_TOKEN_NONE;
        }
      break;

    case G_TOKEN_INT:
      g_scanner_get_next_token (scanner);

      enum_value = g_enum_get_value (enum_class,
                                     (gint) scanner->value.v_int64);

      if (! enum_value)
        {
          g_scanner_error (scanner,
                           _("invalid value '%ld' for token %s"),
                           (glong) scanner->value.v_int64, prop_spec->name);
          return G_TOKEN_NONE;
        }
      break;

    default:
      return G_TOKEN_IDENTIFIER;
    }

  g_value_set_enum (value, enum_value->value);

  return G_TOKEN_RIGHT_PAREN;
}

static GTokenType
gimp_config_deserialize_memsize (GValue     *value,
                                 GParamSpec *prop_spec,
                                 GScanner   *scanner)
{
  gchar   *orig_cset_first = scanner->config->cset_identifier_first;
  gchar   *orig_cset_nth   = scanner->config->cset_identifier_nth;
  guint64  memsize;

  scanner->config->cset_identifier_first = G_CSET_DIGITS;
  scanner->config->cset_identifier_nth   = G_CSET_DIGITS "gGmMkKbB";

  if (g_scanner_peek_next_token (scanner) != G_TOKEN_IDENTIFIER)
    return G_TOKEN_IDENTIFIER;

  g_scanner_get_next_token (scanner);

  scanner->config->cset_identifier_first = orig_cset_first;
  scanner->config->cset_identifier_nth   = orig_cset_nth;

  if (! gimp_memsize_deserialize (scanner->value.v_identifier, &memsize))
    return G_TOKEN_NONE;

  g_value_set_uint64 (value, memsize);

  return G_TOKEN_RIGHT_PAREN;
}

static GTokenType
gimp_config_deserialize_path (GValue     *value,
                              GParamSpec *prop_spec,
                              GScanner   *scanner)
{
  GError *error = NULL;

  if (g_scanner_peek_next_token (scanner) != G_TOKEN_STRING)
    return G_TOKEN_STRING;

  g_scanner_get_next_token (scanner);

  if (!scanner_string_utf8_valid (scanner, prop_spec->name))
    return G_TOKEN_NONE;

  if (scanner->value.v_string)
    {
      /*  Check if the string can be expanded
       *  and converted to the filesystem encoding.
       */
      gchar *expand = gimp_config_path_expand (scanner->value.v_string,
                                               TRUE, &error);

      if (!expand)
        {
          g_scanner_error (scanner,
                           _("while parsing token '%s': %s"),
                           prop_spec->name, error->message);
          g_error_free (error);

          return G_TOKEN_NONE;
        }

      g_free (expand);

      g_value_set_static_string (value, scanner->value.v_string);
    }

  return G_TOKEN_RIGHT_PAREN;
}

static GTokenType
gimp_config_deserialize_matrix2 (GValue     *value,
                                 GParamSpec *prop_spec,
                                 GScanner   *scanner)
{
  GimpMatrix2 matrix;

  if (! gimp_scanner_parse_matrix2 (scanner, &matrix))
    return G_TOKEN_NONE;

  g_value_set_boxed (value, &matrix);

  return G_TOKEN_RIGHT_PAREN;
}

static GTokenType
gimp_config_deserialize_object (GValue     *value,
                                GimpConfig *config,
                                GParamSpec *prop_spec,
                                GScanner   *scanner,
                                gint        nest_level)
{
  GimpConfigInterface *config_iface;
  GimpConfig          *prop_object;
  GType                type;

  g_object_get_property (G_OBJECT (config), prop_spec->name, value);

  prop_object = g_value_get_object (value);

  /*  if the object property is not GIMP_CONFIG_PARAM_AGGREGATE, read
   *  the type of the object.
   */
  if (! (prop_spec->flags & GIMP_CONFIG_PARAM_AGGREGATE))
    {
      gchar *type_name;

      if (! gimp_scanner_parse_string (scanner, &type_name))
        return G_TOKEN_STRING;

      if (! (type_name && *type_name))
        {
          g_scanner_error (scanner, "Type name is empty");
          g_free (type_name);
          return G_TOKEN_NONE;
        }

      type = g_type_from_name (type_name);

      if (type == 0)
        {
          g_scanner_error (scanner, "Unknown object type: %s", type_name);
          g_free (type_name);
          return G_TOKEN_NONE;
        }
      else if (! g_type_is_a (type, prop_spec->value_type))
        {
          g_scanner_error (scanner, "Invalid object type: %s", type_name);
          g_free (type_name);
          return G_TOKEN_NONE;
        }

      g_free (type_name);
    }

  if (! prop_object)
    {
      /*  if the object property is not GIMP_CONFIG_PARAM_AGGREGATE,
       *  create the object.
       */
      if (! (prop_spec->flags & GIMP_CONFIG_PARAM_AGGREGATE))
        {
          prop_object = g_object_new (type, NULL);

          g_value_take_object (value, prop_object);
        }
      else
        {
          return G_TOKEN_RIGHT_PAREN;
        }
    }

  config_iface = GIMP_CONFIG_GET_IFACE (prop_object);

  if (! config_iface)
    return gimp_config_deserialize_any (value, prop_spec, scanner);

  if (config_iface->deserialize_create != NULL)
    {
      /* Some class may prefer to create themselves their objects, for instance
       * to maintain unicity of objects (in libgimp in particular, the various
       * GimpItem or GimpResource are managed by the lib. A single item or
       * resource must be represented for a single object across the whole
       * processus.
       */
      GimpConfig *created_object;

      created_object = config_iface->deserialize_create (G_TYPE_FROM_INSTANCE (prop_object),
                                                         scanner, nest_level + 1, NULL);

      if (created_object == NULL)
        return G_TOKEN_NONE;
      else
        g_value_take_object (value, created_object);
    }
  else if (! config_iface->deserialize (prop_object, scanner, nest_level + 1, NULL))
    {
      return G_TOKEN_NONE;
    }

  return G_TOKEN_RIGHT_PAREN;
}

static GTokenType
gimp_config_deserialize_value_array (GValue     *value,
                                     GimpConfig *config,
                                     GParamSpec *prop_spec,
                                     GScanner   *scanner)
{
  GParamSpec     *element_spec;
  GimpValueArray *array;
  GValue          array_value = G_VALUE_INIT;
  gint            n_values;
  GTokenType      token;
  gint            i;

  element_spec = gimp_param_spec_value_array_get_element_spec (prop_spec);

  if (! gimp_scanner_parse_int (scanner, &n_values))
    return G_TOKEN_INT;

  array = gimp_value_array_new (n_values);

  for (i = 0; i < n_values; i++)
    {
      g_value_init (&array_value, element_spec->value_type);

      token = gimp_config_deserialize_value (&array_value, config,
                                             element_spec, scanner);

      if (token == G_TOKEN_RIGHT_PAREN)
        gimp_value_array_append (array, &array_value);

      g_value_unset (&array_value);

      if (token != G_TOKEN_RIGHT_PAREN)
        {
          gimp_value_array_unref (array);
          return token;
        }
    }

  g_value_take_boxed (value, array);

  return G_TOKEN_RIGHT_PAREN;
}

/**
 * gimp_config_deserialize_strv:
 * @value:   destination #GValue to hold a #GStrv
 * @scanner: #GScanner positioned in serialization stream
 *
 * Sets @value to new #GStrv.
 * Scans i.e. consumes serialization to fill the GStrv.
 *
 * Requires @value to be initialized to hold type #G_TYPE_BOXED.
 *
 * Returns:
 * G_TOKEN_RIGHT_PAREN on success.
 * G_TOKEN_INT on failure to scan length.
 * G_TOKEN_STRING on failure to scan enough quoted strings.
 *
 * On failure, the value in @value is not touched and could be NULL.
 *
 * Since: 3.0
 **/
static GTokenType
gimp_config_deserialize_strv (GValue     *value,
                              GScanner   *scanner)
{
  gint          n_values;
  GTokenType    result_token = G_TOKEN_RIGHT_PAREN;
  GStrvBuilder *builder;

  /* Scan length of array. */
  if (! gimp_scanner_parse_int (scanner, &n_values))
    return G_TOKEN_INT;

  builder = g_strv_builder_new ();

  for (gint i = 0; i < n_values; i++)
    {
      gchar *scanned_string;

      if (! gimp_scanner_parse_string (scanner, &scanned_string))
        {
          /* Error, missing a string. */
          result_token = G_TOKEN_STRING;
          break;
        }

      g_strv_builder_add (builder, scanned_string ? scanned_string : "");
      g_free (scanned_string);
    }

  /* assert result_token is G_TOKEN_RIGHT_PAREN OR G_TOKEN_STRING */
  if (result_token == G_TOKEN_RIGHT_PAREN)
    {
      GStrv   gstrv;

      /* Allocate new GStrv. */
      gstrv = g_strv_builder_end (builder);
      /* Transfer ownership of the array and all strings it points to. */
      g_value_take_boxed (value, gstrv);
    }
  else
    {
      /* No GStrv to unref. */
      g_scanner_error (scanner, "Missing string.");
    }

  g_strv_builder_unref (builder);

  return result_token;
}

static GTokenType
gimp_config_deserialize_array (GValue     *value,
                               GScanner   *scanner)
{
  gint32     *values;
  gint        n_values;
  GTokenType  result_token = G_TOKEN_RIGHT_PAREN;

  if (! gimp_scanner_parse_int (scanner, &n_values))
    return G_TOKEN_INT;

  if (GIMP_VALUE_HOLDS_INT32_ARRAY (value))
    values = g_new0 (gint32, n_values);
  else /* GIMP_VALUE_HOLDS_DOUBLE_ARRAY (value) */
    values = (gint32 *) g_new0 (gdouble, n_values);

  for (gint i = 0; i < n_values; i++)
    {
      if (GIMP_VALUE_HOLDS_INT32_ARRAY (value))
        {
          gint value;

          if (! gimp_scanner_parse_int (scanner, &value))
            {
              result_token = G_TOKEN_INT;
              break;
            }

          values[i] = value;
        }
      else
        {
          gdouble value;

          if (! gimp_scanner_parse_double (scanner, &value))
            {
              result_token = G_TOKEN_FLOAT;
              break;
            }

          ((gdouble *) values)[i] = value;
        }
    }

  if (result_token == G_TOKEN_RIGHT_PAREN)
    {
      if (GIMP_VALUE_HOLDS_INT32_ARRAY (value))
        gimp_value_take_int32_array (value, values, n_values);
      else
        gimp_value_take_double_array (value, (gdouble *) values, n_values);
    }
  else
    {
      g_scanner_error (scanner, "Missing value.");
    }

  return result_token;
}

static GimpUnit *
gimp_config_get_unit_from_identifier (const gchar *identifier)
{
  GimpUnit *unit;

  unit = gimp_unit_get_by_id (GIMP_UNIT_PIXEL);
  for (gint i = GIMP_UNIT_PIXEL; unit; i++)
    {
      if (g_strcmp0 (identifier, gimp_unit_get_name (unit)) == 0)
        break;

      unit = gimp_unit_get_by_id (i);
    }

  if (unit == NULL && g_strcmp0 (identifier, "percent") == 0)
    unit = gimp_unit_percent ();

  /* XXX This may return NULL, especially for user-defined units which
   * may have disappeared from one session to another. Should we return
   * some default unit then?
   */

  return unit;
}

/* This function is entirely sick, so is our method of serializing
 * units, which we write out as (unit foo bar) instead of
 * (unit "foo bar"). The assumption that caused this shit was that a
 * unit's "identifier" is really an identifier in the C-ish sense,
 * when in fact it's just a random user entered string.
 *
 * Here, we try to parse at least the default units shipped with ammoos,
 * and we add code to parse (unit "foo bar") in order to be compatible
 * with future correct unit serializing.
 */
static GTokenType
gimp_config_deserialize_unit (GValue     *value,
                              GParamSpec *prop_spec,
                              GScanner   *scanner)
{
  gchar      *old_cset_skip_characters;
  gchar      *old_cset_identifier_first;
  gchar      *old_cset_identifier_nth;
  GString    *buffer;
  GimpUnit   *unit;
  GTokenType  token;

  /* parse the next token *before* reconfiguring the scanner, so it
   * skips whitespace first
   */
  token = g_scanner_peek_next_token (scanner);

  if (token == G_TOKEN_STRING)
    {
      g_scanner_get_next_token (scanner);
      unit = gimp_config_get_unit_from_identifier (scanner->value.v_string);
      g_value_set_object (value, unit);

      return G_TOKEN_RIGHT_PAREN;
    }

  old_cset_skip_characters  = scanner->config->cset_skip_characters;
  old_cset_identifier_first = scanner->config->cset_identifier_first;
  old_cset_identifier_nth   = scanner->config->cset_identifier_nth;

  scanner->config->cset_skip_characters  = "";
  scanner->config->cset_identifier_first = ( G_CSET_a_2_z G_CSET_A_2_Z "." );
  scanner->config->cset_identifier_nth   = ( G_CSET_a_2_z G_CSET_A_2_Z
                                             G_CSET_DIGITS "-_." );

  buffer = g_string_new ("");

  while (g_scanner_peek_next_token (scanner) != G_TOKEN_RIGHT_PAREN)
    {
      token = g_scanner_peek_next_token (scanner);

      if (token == G_TOKEN_IDENTIFIER)
        {
          g_scanner_get_next_token (scanner);
          g_string_append (buffer, scanner->value.v_identifier);
        }
      else if (token == G_TOKEN_CHAR)
        {
          g_scanner_get_next_token (scanner);
          g_string_append_c (buffer, scanner->value.v_char);
        }
      else if (token == ' ')
        {
          g_scanner_get_next_token (scanner);
          g_string_append_c (buffer, token);
        }
      else
        {
          token = G_TOKEN_IDENTIFIER;
          goto cleanup;
        }
    }

  unit = gimp_config_get_unit_from_identifier (buffer->str);
  g_value_set_object (value, unit);

  token = G_TOKEN_RIGHT_PAREN;

 cleanup:

  g_string_free (buffer, TRUE);

  scanner->config->cset_skip_characters  = old_cset_skip_characters;
  scanner->config->cset_identifier_first = old_cset_identifier_first;
  scanner->config->cset_identifier_nth   = old_cset_identifier_nth;

  return token;
}

static GTokenType
gimp_config_deserialize_file_value (GValue     *value,
                                    GParamSpec *prop_spec,
                                    GScanner   *scanner)
{
  GTokenType token;

  token = g_scanner_peek_next_token (scanner);

  if (token != G_TOKEN_IDENTIFIER &&
      token != G_TOKEN_STRING)
    {
      return G_TOKEN_STRING;
    }

  g_scanner_get_next_token (scanner);

  if (token == G_TOKEN_IDENTIFIER)
    {
      /* this is supposed to parse a literal "NULL" only, but so what... */
      g_value_set_object (value, NULL);
    }
  else
    {
      gchar *path = gimp_config_path_expand (scanner->value.v_string, TRUE,
                                             NULL);

      if (path)
        {
          GFile *file = g_file_new_for_uri (path);

          g_value_take_object (value, file);
          g_free (path);
        }
      else
        {
          g_value_set_object (value, NULL);
        }
    }

  return G_TOKEN_RIGHT_PAREN;
}

/*
 * Note: this is different from gimp_config_deserialize_parasite()
 * which is a public API to deserialize random properties into a config
 * object from a parasite. Here we are deserializing the contents of a
 * parasite itself in @scanner.
 */
static GTokenType
gimp_config_deserialize_parasite_value (GValue     *value,
                                        GParamSpec *prop_spec,
                                        GScanner   *scanner)
{
  GimpParasite *parasite;
  gchar        *name;
  guint8       *data;
  gint          data_length;
  gint64        flags;

  if (! gimp_scanner_parse_string (scanner, &name))
    return G_TOKEN_STRING;

  if (! (name && *name))
    {
      g_scanner_error (scanner, "Parasite name is empty");
      g_free (name);
      return G_TOKEN_NONE;
    }

  if (! gimp_scanner_parse_int64 (scanner, &flags))
    return G_TOKEN_INT;

  if (! gimp_scanner_parse_int (scanner, &data_length))
    return G_TOKEN_INT;

  if (! gimp_scanner_parse_data (scanner, data_length, &data))
    return G_TOKEN_STRING;

  parasite = gimp_parasite_new (name, flags, data_length, data);
  g_free (data);

  g_value_take_boxed (value, parasite);

  return G_TOKEN_RIGHT_PAREN;
}

static GTokenType
gimp_config_deserialize_bytes (GValue     *value,
                               GParamSpec *prop_spec,
                               GScanner   *scanner)
{
  GTokenType  token;
  GBytes     *bytes;
  guint8     *data;
  gint        data_length;

  token = g_scanner_peek_next_token (scanner);

  if (token == G_TOKEN_IDENTIFIER)
    {
      g_scanner_get_next_token (scanner);

      if (g_ascii_strcasecmp (scanner->value.v_identifier, "null") != 0)
        /* Do not fail the whole file parsing. Just output to stderr and assume
         * a NULL bytes property.
         */
        g_printerr ("%s: expected NULL identifier for bytes token '%s', got '%s'. "
                    "Assuming NULL instead.\n",
                    G_STRFUNC, prop_spec->name, scanner->value.v_identifier);

      g_value_set_boxed (value, NULL);
    }
  else if (token == G_TOKEN_INT)
    {
      if (! gimp_scanner_parse_int (scanner, &data_length))
        return G_TOKEN_INT;

      if (! gimp_scanner_parse_data (scanner, data_length, &data))
        return G_TOKEN_STRING;

      bytes = g_bytes_new_take (data, data_length);

      g_value_take_boxed (value, bytes);
    }
  else
    {
      return G_TOKEN_INT;
    }

  return G_TOKEN_RIGHT_PAREN;
}

static GTokenType
gimp_config_deserialize_color (GValue     *value,
                               GParamSpec *prop_spec,
                               GScanner   *scanner)
{
  GeglColor *color = NULL;

  if (! gimp_scanner_parse_color (scanner, &color))
    return G_TOKEN_NONE;

  g_value_take_object (value, color);

  return G_TOKEN_RIGHT_PAREN;
}

static GTokenType
gimp_config_deserialize_any (GValue     *value,
                             GParamSpec *prop_spec,
                             GScanner   *scanner)
{
  GValue     src = G_VALUE_INIT;
  GTokenType token;

  if (!g_value_type_transformable (G_TYPE_STRING, prop_spec->value_type))
    {
      g_scanner_error (scanner,
                       "%s can not be transformed from a string",
                       g_type_name (prop_spec->value_type));
      return G_TOKEN_NONE;
    }

  token = g_scanner_peek_next_token (scanner);

  if (token != G_TOKEN_IDENTIFIER &&
      token != G_TOKEN_STRING)
    {
      return G_TOKEN_IDENTIFIER;
    }

  g_scanner_get_next_token (scanner);

  g_value_init (&src, G_TYPE_STRING);

  if (token == G_TOKEN_IDENTIFIER)
    g_value_set_static_string (&src, scanner->value.v_identifier);
  else
    g_value_set_static_string (&src, scanner->value.v_string);

  g_value_transform (&src, value);
  g_value_unset (&src);

  return G_TOKEN_RIGHT_PAREN;
}

static GTokenType
gimp_config_skip_unknown_property (GScanner *scanner)
{
  gint open_paren = 0;

  while (TRUE)
    {
      GTokenType token = g_scanner_peek_next_token (scanner);

      switch (token)
        {
        case G_TOKEN_LEFT_PAREN:
          open_paren++;
          g_scanner_get_next_token (scanner);
          break;

        case G_TOKEN_RIGHT_PAREN:
          if (open_paren == 0)
            return token;

          open_paren--;
          g_scanner_get_next_token (scanner);
          break;

        case G_TOKEN_EOF:
          return token;

        default:
          g_scanner_get_next_token (scanner);
          break;
        }
    }
}

/* --- end libammoos/config/fieldconfig/gimpconfig-deserialize.c --- */

/* --- begin libammoos/config/fieldconfig/gimpconfig-error.c --- */
/* LIBGIMP - The AmmoOS Image Library
 * Copyright (C) 1995-1997 Spencer Kimball and Peter Mattis
 *
 * Config file serialization and deserialization interface
 * Copyright (C) 2001-2002  Sven Neumann <sven@ammoos.org>
 *
 * This library is free software: you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 3 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Library General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library.  If not, see
 * <https://www.gnu.org/licenses/>.
 */

#include "config.h"

#include <glib.h>

#include "gimpconfig-error.h"


/**
 * SECTION: gimpconfig-error
 * @title: GimpConfig-error
 * @short_description: Error utils for libgimpconfig.
 *
 * Error utils for libgimpconfig.
 **/


/**
 * gimp_config_error_quark:
 *
 * This function is never called directly. Use GIMP_CONFIG_ERROR() instead.
 *
 * Returns: the #GQuark that defines the GimpConfig error domain.
 *
 * Since: 2.4
 **/
GQuark
gimp_config_error_quark (void)
{
  return g_quark_from_static_string ("ammoos-config-error-quark");
}

/* --- end libammoos/config/fieldconfig/gimpconfig-error.c --- */

/* --- begin libammoos/config/fieldconfig/gimpconfig-iface.c --- */
/* LIBGIMP - The AmmoOS Image Library
 * Copyright (C) 1995-1997 Spencer Kimball and Peter Mattis
 *
 * Config file serialization and deserialization interface
 * Copyright (C) 2001-2002  Sven Neumann <sven@ammoos.org>
 *
 * This library is free software: you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 3 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Library General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library.  If not, see
 * <https://www.gnu.org/licenses/>.
 */

#include "config.h"

#include <string.h>

#include <gio/gio.h>

#include "libgimpbase/gimpbase.h"

#include "gimpconfigtypes.h"

#include "gimpconfigwriter.h"
#include "gimpconfig-iface.h"
#include "gimpconfig-deserialize.h"
#include "gimpconfig-serialize.h"
#include "gimpconfig-params.h"
#include "gimpconfig-utils.h"
#include "gimpscanner.h"

#include "libgimp/libgimp-intl.h"


typedef struct _GimpConfigInterfacePrivate GimpConfigInterfacePrivate;

struct _GimpConfigInterfacePrivate
{
  guint xcf_version;
};

#define GIMP_CONFIG_INTERFACE_GET_PRIVATE(obj) (gimp_config_iface_get_private ((GimpConfigInterface *) (obj)))


/*
 * GimpConfigIface:
 *
 * The [struct@Config] serialization and deserialization interface.
 */


/*  local function prototypes  */

static GimpConfigInterfacePrivate * gimp_config_iface_get_private      (GimpConfigInterface        *iface);
static void                         gimp_config_iface_private_finalize (GimpConfigInterfacePrivate *private);

static void                         gimp_config_iface_default_init     (GimpConfigInterface        *iface);
static void                         gimp_config_iface_base_init        (GimpConfigInterface        *iface);

static gboolean                     gimp_config_iface_serialize        (GimpConfig                 *config,
                                                                        GimpConfigWriter           *writer,
                                                                        gpointer                    data);
static gboolean                     gimp_config_iface_deserialize      (GimpConfig                 *config,
                                                                        GScanner                   *scanner,
                                                                        gint                        nest_level,
                                                                        gpointer                    data);
static GimpConfig                 * gimp_config_iface_duplicate        (GimpConfig                 *config);
static gboolean                     gimp_config_iface_equal            (GimpConfig                 *a,
                                                                        GimpConfig                 *b);
static void                         gimp_config_iface_reset            (GimpConfig                 *config);
static gboolean                     gimp_config_iface_copy             (GimpConfig                 *src,
                                                                        GimpConfig                 *dest,
                                                                        GParamFlags                 flags);


/*  private functions  */


GType
gimp_config_get_type (void)
{
  static GType config_iface_type = 0;

  if (! config_iface_type)
    {
      const GTypeInfo config_iface_info =
      {
        sizeof (GimpConfigInterface),
        (GBaseInitFunc)      gimp_config_iface_base_init,
        (GBaseFinalizeFunc)  NULL,
        (GClassInitFunc)     gimp_config_iface_default_init,
        (GClassFinalizeFunc) NULL,
      };

      config_iface_type = g_type_register_static (G_TYPE_INTERFACE,
                                                  "GimpConfigInterface",
                                                  &config_iface_info,
                                                  0);

      g_type_interface_add_prerequisite (config_iface_type, G_TYPE_OBJECT);
    }

  return config_iface_type;
}

static void
gimp_config_iface_default_init (GimpConfigInterface *iface)
{
  iface->serialize   = gimp_config_iface_serialize;
  iface->deserialize = gimp_config_iface_deserialize;
  iface->duplicate   = gimp_config_iface_duplicate;
  iface->equal       = gimp_config_iface_equal;
  iface->reset       = gimp_config_iface_reset;
  iface->copy        = gimp_config_iface_copy;
}

static void
gimp_config_iface_base_init (GimpConfigInterface *iface)
{
  /*  always set these to NULL since we don't want to inherit them
   *  from parent classes
   */
  iface->serialize_property   = NULL;
  iface->deserialize_property = NULL;
}

static gboolean
gimp_config_iface_serialize (GimpConfig       *config,
                             GimpConfigWriter *writer,
                             gpointer          data)
{
  return gimp_config_serialize_properties (config, writer);
}

static gboolean
gimp_config_iface_deserialize (GimpConfig *config,
                               GScanner   *scanner,
                               gint        nest_level,
                               gpointer    data)
{
  return gimp_config_deserialize_properties (config, scanner, nest_level);
}

static GimpConfig *
gimp_config_iface_duplicate (GimpConfig *config)
{
  GObject       *object = G_OBJECT (config);
  GObjectClass  *klass  = G_OBJECT_GET_CLASS (object);
  GParamSpec   **property_specs;
  guint          n_property_specs;
  gint           n_construct_properties = 0;
  const gchar  **construct_names        = NULL;
  GValue        *construct_values       = NULL;
  guint          i;
  GObject       *dup;

  property_specs = g_object_class_list_properties (klass, &n_property_specs);

  construct_names  = g_new0 (const gchar *, n_property_specs);
  construct_values = g_new0 (GValue,        n_property_specs);

  for (i = 0; i < n_property_specs; i++)
    {
      GParamSpec *prop_spec = property_specs[i];

      if ((prop_spec->flags & G_PARAM_READABLE) &&
          (prop_spec->flags & G_PARAM_WRITABLE) &&
          (prop_spec->flags & G_PARAM_CONSTRUCT_ONLY))
        {
          construct_names[n_construct_properties] = prop_spec->name;

          g_value_init (&construct_values[n_construct_properties],
                        prop_spec->value_type);
          g_object_get_property (object, prop_spec->name,
                                 &construct_values[n_construct_properties]);

          n_construct_properties++;
        }
    }

  g_free (property_specs);

  dup = g_object_new_with_properties (G_TYPE_FROM_INSTANCE (object),
                                      n_construct_properties,
                                      (const gchar **) construct_names,
                                      (const GValue *) construct_values);

  for (i = 0; i < n_construct_properties; i++)
    g_value_unset (&construct_values[i]);

  g_free (construct_names);
  g_free (construct_values);

  gimp_config_copy (config, GIMP_CONFIG (dup), 0);

  return GIMP_CONFIG (dup);
}

static gboolean
gimp_config_iface_equal (GimpConfig *a,
                         GimpConfig *b)
{
  GObjectClass  *klass;
  GParamSpec   **property_specs;
  guint          n_property_specs;
  guint          i;
  gboolean       equal = TRUE;

  klass = G_OBJECT_GET_CLASS (a);

  property_specs = g_object_class_list_properties (klass, &n_property_specs);

  for (i = 0; equal && i < n_property_specs; i++)
    {
      GParamSpec  *prop_spec;
      GValue       a_value = G_VALUE_INIT;
      GValue       b_value = G_VALUE_INIT;

      prop_spec = property_specs[i];

      if (! (prop_spec->flags & G_PARAM_READABLE) ||
            (prop_spec->flags & GIMP_CONFIG_PARAM_DONT_COMPARE))
        {
          continue;
        }

      g_value_init (&a_value, prop_spec->value_type);
      g_value_init (&b_value, prop_spec->value_type);
      g_object_get_property (G_OBJECT (a), prop_spec->name, &a_value);
      g_object_get_property (G_OBJECT (b), prop_spec->name, &b_value);

      if (g_param_values_cmp (prop_spec, &a_value, &b_value))
        {
          if ((prop_spec->flags & GIMP_CONFIG_PARAM_AGGREGATE) &&
              G_IS_PARAM_SPEC_OBJECT (prop_spec)        &&
              g_type_interface_peek (g_type_class_peek (prop_spec->value_type),
                                     GIMP_TYPE_CONFIG))
            {
              if (! gimp_config_is_equal_to (g_value_get_object (&a_value),
                                             g_value_get_object (&b_value)))
                {
                  equal = FALSE;
                }
            }
          else
            {
              equal = FALSE;
            }
        }

      g_value_unset (&a_value);
      g_value_unset (&b_value);
    }

  g_free (property_specs);

  return equal;
}

static void
gimp_config_iface_reset (GimpConfig *config)
{
  gimp_config_reset_properties (G_OBJECT (config));
}

static gboolean
gimp_config_iface_copy (GimpConfig  *src,
                        GimpConfig  *dest,
                        GParamFlags  flags)
{
  return gimp_config_sync (G_OBJECT (src), G_OBJECT (dest), flags);
}

static GimpConfigInterfacePrivate *
gimp_config_iface_get_private (GimpConfigInterface *iface)
{
  GimpConfigInterfacePrivate *private;

  static GQuark private_key = 0;

  if (! private_key)
    private_key = g_quark_from_static_string ("ammoos-config-iface-private");

  private = g_object_get_qdata ((GObject *) iface, private_key);

  if (! private)
    {
      private = g_slice_new0 (GimpConfigInterfacePrivate);

      private->xcf_version = G_MAXUINT32;

      g_object_set_qdata_full ((GObject *) iface, private_key, private,
                               (GDestroyNotify) gimp_config_iface_private_finalize);
    }

  return private;
}

static void
gimp_config_iface_private_finalize (GimpConfigInterfacePrivate *private)
{
  g_slice_free (GimpConfigInterfacePrivate, private);
}


/*  public functions  */


/**
 * gimp_config_serialize_to_file:
 * @config: an object that implements [iface@ConfigInterface].
 * @file:   the file to write the configuration to.
 * @header: (nullable): optional file header (must be ASCII only)
 * @footer: (nullable): optional file footer (must be ASCII only)
 * @data: user data passed to the serialize implementation.
 * @error: return location for a possible error
 *
 * Serializes the object properties of @config to the file specified
 * by @file. If a file with that name already exists, it is
 * overwritten. Basically this function opens @file for you and calls
 * the serialize function of the @config's [iface@ConfigInterface].
 *
 * Returns: %TRUE if serialization succeeded, %FALSE otherwise.
 *
 * Since: 2.10
 **/
gboolean
gimp_config_serialize_to_file (GimpConfig   *config,
                               GFile        *file,
                               const gchar  *header,
                               const gchar  *footer,
                               gpointer      data,
                               GError      **error)
{
  GimpConfigWriter *writer;

  g_return_val_if_fail (GIMP_IS_CONFIG (config), FALSE);
  g_return_val_if_fail (G_IS_FILE (file), FALSE);
  g_return_val_if_fail (error == NULL || *error == NULL, FALSE);

  writer = gimp_config_writer_new_from_file (file, TRUE, header, error);
  if (!writer)
    return FALSE;

  GIMP_CONFIG_GET_IFACE (config)->serialize (config, writer, data);

  return gimp_config_writer_finish (writer, footer, error);
}

/**
 * gimp_config_serialize_to_stream:
 * @config: an object that implements [iface@ConfigInterface].
 * @output: the #GOutputStream to write the configuration to.
 * @header: (nullable): optional file header (must be ASCII only)
 * @footer: (nullable): optional file footer (must be ASCII only)
 * @data: user data passed to the serialize implementation.
 * @error: return location for a possible error
 *
 * Serializes the object properties of @config to the stream specified
 * by @output.
 *
 * Returns: Whether serialization succeeded.
 *
 * Since: 2.10
 **/
gboolean
gimp_config_serialize_to_stream (GimpConfig     *config,
                                 GOutputStream  *output,
                                 const gchar    *header,
                                 const gchar    *footer,
                                 gpointer        data,
                                 GError        **error)
{
  GimpConfigWriter *writer;

  g_return_val_if_fail (GIMP_IS_CONFIG (config), FALSE);
  g_return_val_if_fail (G_IS_OUTPUT_STREAM (output), FALSE);
  g_return_val_if_fail (error == NULL || *error == NULL, FALSE);

  writer = gimp_config_writer_new_from_stream (output, header, error);
  if (!writer)
    return FALSE;

  GIMP_CONFIG_GET_IFACE (config)->serialize (config, writer, data);

  return gimp_config_writer_finish (writer, footer, error);
}

/**
 * gimp_config_serialize_to_fd:
 * @config: an object that implements [iface@ConfigInterface].
 * @fd: a file descriptor, opened for writing
 * @data: user data passed to the serialize implementation.
 *
 * Serializes the object properties of @config to the given file
 * descriptor.
 *
 * Returns: %TRUE if serialization succeeded, %FALSE otherwise.
 *
 * Since: 2.4
 **/
gboolean
gimp_config_serialize_to_fd (GimpConfig *config,
                             gint        fd,
                             gpointer    data)
{
  GimpConfigWriter *writer;

  g_return_val_if_fail (GIMP_IS_CONFIG (config), FALSE);
  g_return_val_if_fail (fd > 0, FALSE);

  writer = gimp_config_writer_new_from_fd (fd);
  if (!writer)
    return FALSE;

  GIMP_CONFIG_GET_IFACE (config)->serialize (config, writer, data);

  return gimp_config_writer_finish (writer, NULL, NULL);
}

/**
 * gimp_config_serialize_to_string:
 * @config: an object that implements the [iface@ConfigInterface].
 * @data: user data passed to the serialize implementation.
 *
 * Serializes the object properties of @config to a string.
 *
 * Returns: a newly allocated NUL-terminated string.
 *
 * Since: 2.4
 **/
gchar *
gimp_config_serialize_to_string (GimpConfig *config,
                                 gpointer    data)
{
  GimpConfigWriter *writer;
  GString          *str;

  g_return_val_if_fail (GIMP_IS_CONFIG (config), NULL);

  str    = g_string_new (NULL);
  writer = gimp_config_writer_new_from_string (str);

  GIMP_CONFIG_GET_IFACE (config)->serialize (config, writer, data);

  gimp_config_writer_finish (writer, NULL, NULL);

  return g_string_free (str, FALSE);
}

/**
 * gimp_config_serialize_to_parasite:
 * @config:         an object that implements the [iface@ConfigInterface].
 * @parasite_name:  the new parasite's name
 * @parasite_flags: the new parasite's flags
 * @data:           user data passed to the serialize implementation.
 *
 * Serializes the object properties of @config to a [struct@Parasite].
 *
 * Returns: (transfer full): the newly allocated parasite.
 *
 * Since: 3.0
 **/
GimpParasite *
gimp_config_serialize_to_parasite (GimpConfig  *config,
                                   const gchar *parasite_name,
                                   guint        parasite_flags,
                                   gpointer     data)
{
  GimpParasite *parasite;
  gchar        *str;

  g_return_val_if_fail (GIMP_IS_CONFIG (config), NULL);
  g_return_val_if_fail (parasite_name != NULL, NULL);

  str = gimp_config_serialize_to_string (config, data);

  if (! str)
    return NULL;

  parasite = gimp_parasite_new (parasite_name,
                                parasite_flags,
                                0, NULL);

  parasite->size = strlen (str) + 1;
  parasite->data = str;

  return parasite;
}

/**
 * gimp_config_deserialize_file:
 * @config: an object that implements the #GimpConfigInterface.
 * @file: the file to read configuration from.
 * @data: user data passed to the deserialize implementation.
 * @error: return location for a possible error
 *
 * Opens the file specified by @file, reads configuration data from it
 * and configures @config accordingly. Basically this function creates
 * a properly configured [struct@GLib.Scanner] for you and calls the deserialize
 * function of the @config's [iface@ConfigInterface].
 *
 * Returns: Whether deserialization succeeded.
 *
 * Since: 2.10
 **/
gboolean
gimp_config_deserialize_file (GimpConfig  *config,
                              GFile       *file,
                              gpointer     data,
                              GError     **error)
{
  GScanner *scanner;
  gboolean  success;

  g_return_val_if_fail (GIMP_IS_CONFIG (config), FALSE);
  g_return_val_if_fail (G_IS_FILE (file), FALSE);
  g_return_val_if_fail (error == NULL || *error == NULL, FALSE);

  scanner = gimp_scanner_new_file (file, error);
  if (! scanner)
    return FALSE;

  g_object_freeze_notify (G_OBJECT (config));

  success = GIMP_CONFIG_GET_IFACE (config)->deserialize (config,
                                                         scanner, 0, data);

  g_object_thaw_notify (G_OBJECT (config));

  gimp_scanner_unref (scanner);

  if (! success)
    /* If we get this assert, it means we have a bug in one of the
     * deserialize() implementations. Any failure case should report the
     * error condition with g_scanner_error() which will populate the
     * error object passed in gimp_scanner_new*().
     */
    g_assert (error == NULL || *error != NULL);

  return success;
}

/**
 * gimp_config_deserialize_stream:
 * @config: an object that implements the #GimpConfigInterface.
 * @input: the input stream to read configuration from.
 * @data: user data passed to the deserialize implementation.
 * @error: return location for a possible error
 *
 * Reads configuration data from @input and configures @config
 * accordingly. Basically this function creates a properly configured
 * #GScanner for you and calls the deserialize function of the
 * @config's #GimpConfigInterface.
 *
 * Returns: Whether deserialization succeeded.
 *
 * Since: 2.10
 **/
gboolean
gimp_config_deserialize_stream (GimpConfig    *config,
                                GInputStream  *input,
                                gpointer       data,
                                GError       **error)
{
  GScanner *scanner;
  gboolean  success;

  g_return_val_if_fail (GIMP_IS_CONFIG (config), FALSE);
  g_return_val_if_fail (G_IS_INPUT_STREAM (input), FALSE);
  g_return_val_if_fail (error == NULL || *error == NULL, FALSE);

  scanner = gimp_scanner_new_stream (input, error);
  if (! scanner)
    return FALSE;

  g_object_freeze_notify (G_OBJECT (config));

  success = GIMP_CONFIG_GET_IFACE (config)->deserialize (config,
                                                         scanner, 0, data);

  g_object_thaw_notify (G_OBJECT (config));

  gimp_scanner_unref (scanner);

  if (! success)
    g_assert (error == NULL || *error != NULL);

  return success;
}

/**
 * gimp_config_deserialize_string:
 * @config:   a #GObject that implements the #GimpConfigInterface.
 * @text: (array length=text_len): string to deserialize (in UTF-8 encoding)
 * @text_len: length of @text in bytes or -1
 * @data:     client data
 * @error:    return location for a possible error
 *
 * Configures @config from @text. Basically this function creates a
 * properly configured #GScanner for you and calls the deserialize
 * function of the @config's #GimpConfigInterface.
 *
 * Returns: %TRUE if deserialization succeeded, %FALSE otherwise.
 *
 * Since: 2.4
 **/
gboolean
gimp_config_deserialize_string (GimpConfig   *config,
                                const gchar  *text,
                                gint          text_len,
                                gpointer      data,
                                GError      **error)
{
  GScanner *scanner;
  gboolean  success;

  g_return_val_if_fail (GIMP_IS_CONFIG (config), FALSE);
  g_return_val_if_fail (text != NULL || text_len == 0, FALSE);
  g_return_val_if_fail (error == NULL || *error == NULL, FALSE);

  scanner = gimp_scanner_new_string (text, text_len, error);

  g_object_freeze_notify (G_OBJECT (config));

  success = GIMP_CONFIG_GET_IFACE (config)->deserialize (config,
                                                         scanner, 0, data);

  g_object_thaw_notify (G_OBJECT (config));

  gimp_scanner_unref (scanner);

  if (! success)
    g_assert (error == NULL || *error != NULL);

  return success;
}

/**
 * gimp_config_deserialize_parasite:
 * @config:   a #GObject that implements the #GimpConfigInterface.
 * @parasite: parasite containing a serialized config string
 * @data:     client data
 * @error:    return location for a possible error
 *
 * Configures @config from @parasite. Basically this function creates
 * a properly configured #GScanner for you and calls the deserialize
 * function of the @config's #GimpConfigInterface.
 *
 * Returns: %TRUE if deserialization succeeded, %FALSE otherwise.
 *
 * Since: 3.0
 **/
gboolean
gimp_config_deserialize_parasite (GimpConfig          *config,
                                  const GimpParasite  *parasite,
                                  gpointer             data,
                                  GError             **error)
{
  const gchar *parasite_data;
  guint32      parasite_size;

  g_return_val_if_fail (GIMP_IS_CONFIG (config), FALSE);
  g_return_val_if_fail (parasite != NULL, FALSE);
  g_return_val_if_fail (error == NULL || *error == NULL, FALSE);

  parasite_data = gimp_parasite_get_data (parasite, &parasite_size);
  if (! parasite_data)
    return TRUE;

  return gimp_config_deserialize_string (config, parasite_data, parasite_size,
                                         data, error);
}

/**
 * gimp_config_deserialize_return:
 * @scanner:        a #GScanner
 * @expected_token: the expected token
 * @nest_level:     the nest level
 *
 * Returns:
 *
 * Since: 2.4
 **/
gboolean
gimp_config_deserialize_return (GScanner     *scanner,
                                GTokenType    expected_token,
                                gint          nest_level)
{
  GTokenType next_token;

  g_return_val_if_fail (scanner != NULL, FALSE);

  next_token = g_scanner_peek_next_token (scanner);

  if (expected_token != G_TOKEN_LEFT_PAREN)
    {
      g_scanner_get_next_token (scanner);
      g_scanner_unexp_token (scanner, expected_token, NULL, NULL, NULL,
                             _("fatal parse error"), TRUE);
      return FALSE;
    }
  else
    {
      if (nest_level > 0 && next_token == G_TOKEN_RIGHT_PAREN)
        {
          return TRUE;
        }
      else if (next_token != G_TOKEN_EOF)
        {
          g_scanner_get_next_token (scanner);
          g_scanner_unexp_token (scanner, expected_token, NULL, NULL, NULL,
                                 _("fatal parse error"), TRUE);
          return FALSE;
        }
    }

  return TRUE;
}


/**
 * gimp_config_serialize:
 * @config: an object that implements the #GimpConfigInterface.
 * @writer: the #GimpConfigWriter to use.
 * @data: client data
 *
 * Serialize the #GimpConfig object.
 *
 * Returns: Whether serialization succeeded.
 *
 * Since: 2.8
 **/
gboolean
gimp_config_serialize (GimpConfig       *config,
                       GimpConfigWriter *writer,
                       gpointer          data)
{
  g_return_val_if_fail (GIMP_IS_CONFIG (config), FALSE);

  return GIMP_CONFIG_GET_IFACE (config)->serialize (config, writer, data);
}

/**
 * gimp_config_deserialize:
 * @config: a #GObject that implements the #GimpConfigInterface.
 * @scanner: the #GScanner to use.
 * @nest_level: the nest level.
 * @data: client data.
 *
 * Deserialize the #GimpConfig object.
 *
 * Returns: Whether serialization succeeded.
 *
 * Since: 2.8
 **/
gboolean
gimp_config_deserialize (GimpConfig *config,
                         GScanner   *scanner,
                         gint        nest_level,
                         gpointer    data)
{
  g_return_val_if_fail (GIMP_IS_CONFIG (config), FALSE);

  return GIMP_CONFIG_GET_IFACE (config)->deserialize (config,
                                                      scanner,
                                                      nest_level,
                                                      data);
}

/**
 * gimp_config_duplicate:
 * @config: a #GObject that implements the #GimpConfigInterface.
 *
 * Creates a copy of the passed object by copying all object
 * properties. The default implementation of the #GimpConfigInterface
 * only works for objects that are completely defined by their
 * properties.
 *
 * Returns: the duplicated #GimpConfig object
 *
 * Since: 2.4
 **/
gpointer
gimp_config_duplicate (GimpConfig *config)
{
  g_return_val_if_fail (GIMP_IS_CONFIG (config), NULL);

  return GIMP_CONFIG_GET_IFACE (config)->duplicate (config);
}

/**
 * gimp_config_is_equal_to:
 * @a: a #GObject that implements the #GimpConfigInterface.
 * @b: another #GObject of the same type as @a.
 *
 * Compares the two objects. The default implementation of the
 * #GimpConfigInterface compares the object properties and thus only
 * works for objects that are completely defined by their
 * properties.
 *
 * Returns: %TRUE if the two objects are equal.
 *
 * Since: 2.4
 **/
gboolean
gimp_config_is_equal_to (GimpConfig *a,
                         GimpConfig *b)
{
  g_return_val_if_fail (GIMP_IS_CONFIG (a), FALSE);
  g_return_val_if_fail (GIMP_IS_CONFIG (b), FALSE);
  g_return_val_if_fail (G_TYPE_FROM_INSTANCE (a) == G_TYPE_FROM_INSTANCE (b),
                        FALSE);

  return GIMP_CONFIG_GET_IFACE (a)->equal (a, b);
}

/**
 * gimp_config_reset:
 * @config: a #GObject that implements the #GimpConfigInterface.
 *
 * Resets the object to its default state. The default implementation of the
 * #GimpConfigInterface only works for objects that are completely defined by
 * their properties.
 *
 * Since: 2.4
 **/
void
gimp_config_reset (GimpConfig *config)
{
  g_return_if_fail (GIMP_IS_CONFIG (config));

  g_object_freeze_notify (G_OBJECT (config));

  GIMP_CONFIG_GET_IFACE (config)->reset (config);

  g_object_thaw_notify (G_OBJECT (config));
}

/**
 * gimp_config_copy:
 * @src: a #GObject that implements the #GimpConfigInterface.
 * @dest: another #GObject of the same type as @a.
 * @flags: a mask of GParamFlags
 *
 * Compares all read- and write-able properties from @src and @dest
 * that have all @flags set. Differing values are then copied from
 * @src to @dest. If @flags is 0, all differing read/write properties.
 *
 * Properties marked as "construct-only" are not touched.
 *
 * Returns: %TRUE if @dest was modified, %FALSE otherwise
 *
 * Since: 2.6
 **/
gboolean
gimp_config_copy (GimpConfig  *src,
                  GimpConfig  *dest,
                  GParamFlags  flags)
{
  gboolean changed;

  g_return_val_if_fail (GIMP_IS_CONFIG (src), FALSE);
  g_return_val_if_fail (GIMP_IS_CONFIG (dest), FALSE);
  g_return_val_if_fail (G_TYPE_FROM_INSTANCE (src) == G_TYPE_FROM_INSTANCE (dest),
                        FALSE);

  g_object_freeze_notify (G_OBJECT (dest));

  changed = GIMP_CONFIG_GET_IFACE (src)->copy (src, dest, flags);

  g_object_thaw_notify (G_OBJECT (dest));

  return changed;
}

/**
 * gimp_config_get_xcf_version:
 * @config: a #GObject that implements the #GimpConfigInterface.
 *
 * Returns the current XCF version of the @config.
 *
 * Returns: the XCF version associated with the @config.
 *
 * Since: 3.0.8
 **/
guint
gimp_config_get_xcf_version (GimpConfig *config)
{
  GimpConfigInterfacePrivate *private;

  g_return_val_if_fail (GIMP_IS_CONFIG (config), G_MAXUINT32);

  private = GIMP_CONFIG_INTERFACE_GET_PRIVATE (config);

  return private->xcf_version;
}

/**
 * gimp_config_set_xcf_version:
 * @config: a #GObject that implements the #GimpConfigInterface.
 * @xcf_version: a mask of GParamFlags
 *
 * Sets the current XCF version of the @config. This information can be used
 * to adjust how properties are serialized depending on the version of the XCF
 * that it is being saved to.
 *
 * Since: 3.0.8
 **/
void
gimp_config_set_xcf_version (GimpConfig *config,
                             guint       xcf_version)
{
  GimpConfigInterfacePrivate *private;

  g_return_if_fail (GIMP_IS_CONFIG (config));

  private = GIMP_CONFIG_INTERFACE_GET_PRIVATE (config);

  private->xcf_version = xcf_version;
}

/* --- end libammoos/config/fieldconfig/gimpconfig-iface.c --- */

/* --- begin libammoos/config/fieldconfig/gimpconfig-params.c --- */
/* LIBGIMP - The AmmoOS Image Library
 * Copyright (C) 1995-2003 Peter Mattis and Spencer Kimball
 *
 * gimpconfig-params.c
 * Copyright (C) 2008-2019 Michael Natterer <mitch@ammoos.org>
 *
 * This library is free software: you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 3 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library.  If not, see
 * <https://www.gnu.org/licenses/>.
 */

#include "config.h"

#include <cairo.h>
#include <gdk-pixbuf/gdk-pixbuf.h>

#include <gegl.h>
#include <gegl-paramspecs.h>

#include "libgimpbase/gimpbase.h"
#include "libgimpcolor/gimpcolor.h"
#include "libgimpconfig/gimpconfig.h"

#include "gimpconfig.h"


/**
 * SECTION: gimpconfig-params
 * @title: GimpConfig-params
 * @short_description: Macros and defines to install config properties.
 *
 * Macros and defines to install config properties.
 **/


static gboolean
gimp_gegl_param_spec_has_key (GParamSpec  *pspec,
                              const gchar *key,
                              const gchar *value)
{
  const gchar *v = gegl_param_spec_get_property_key (pspec, key);

  if (v && ! strcmp (v, value))
    return TRUE;

  return FALSE;
}


/**
 * gimp_config_param_spec_duplicate:
 * @pspec: the #GParamSpec to duplicate
 *
 * Creates an exact copy of @pspec, with all its properties, returns
 * %NULL if @pspec is of an unknown type that can't be duplicated.
 *
 * Return: (transfer full): The new #GParamSpec, or %NULL.
 *
 * Since: 3.0
 **/
GParamSpec *
gimp_config_param_spec_duplicate (GParamSpec *pspec)
{
  GParamSpec  *copy = NULL;
  const gchar *name;
  const gchar *nick;
  const gchar *blurb;
  GParamFlags  flags;

  g_return_val_if_fail (pspec != NULL, NULL);

  name  = pspec->name;
  nick  = g_param_spec_get_nick (pspec);
  blurb = g_param_spec_get_blurb (pspec);
  flags = pspec->flags;

  /*  this special case exists for the GEGL tool, we don't want this
   *  property serialized
   */
  if (! gimp_gegl_param_spec_has_key (pspec, "role", "output-extent"))
    flags |= GIMP_CONFIG_PARAM_SERIALIZE;

  if (G_IS_PARAM_SPEC_STRING (pspec))
    {
      GParamSpecString *spec = G_PARAM_SPEC_STRING (pspec);

      if (GIMP_IS_PARAM_SPEC_CHOICE (pspec))
        {
          copy = gimp_param_spec_choice (name, nick, blurb,
                                         g_object_ref (gimp_param_spec_choice_get_choice (pspec)),
                                         gimp_param_spec_choice_get_default (pspec),
                                         flags);
        }
      else if (GEGL_IS_PARAM_SPEC_FILE_PATH (pspec))
        {
          copy = gimp_param_spec_config_path (name, nick, blurb,
                                              GIMP_CONFIG_PATH_FILE,
                                              spec->default_value,
                                              flags);
        }
      else if (GIMP_IS_PARAM_SPEC_CONFIG_PATH (pspec))
        {
          copy = gimp_param_spec_config_path (name, nick, blurb,
                                              gimp_param_spec_config_path_type (pspec),
                                              spec->default_value,
                                              flags);
        }
      else
        {
          copy = g_param_spec_string (name, nick, blurb,
                                      spec->default_value,
                                      flags);
        }
    }
  else if (G_IS_PARAM_SPEC_BOOLEAN (pspec))
    {
      GParamSpecBoolean *spec = G_PARAM_SPEC_BOOLEAN (pspec);

      copy = g_param_spec_boolean (name, nick, blurb,
                                   spec->default_value,
                                   flags);
    }
  else if (G_IS_PARAM_SPEC_ENUM (pspec))
    {
      GParamSpecEnum *spec = G_PARAM_SPEC_ENUM (pspec);

      copy = g_param_spec_enum (name, nick, blurb,
                                G_TYPE_FROM_CLASS (spec->enum_class),
                                spec->default_value,
                                flags);
    }
  else if (G_IS_PARAM_SPEC_DOUBLE (pspec))
    {
      GParamSpecDouble *spec = G_PARAM_SPEC_DOUBLE (pspec);

      if (GEGL_IS_PARAM_SPEC_DOUBLE (pspec))
        {
          GeglParamSpecDouble *gspec = GEGL_PARAM_SPEC_DOUBLE (pspec);

          copy = gegl_param_spec_double (name, nick, blurb,
                                         spec->minimum,
                                         spec->maximum,
                                         spec->default_value,
                                         gspec->ui_minimum,
                                         gspec->ui_maximum,
                                         gspec->ui_gamma,
                                         flags);
          gegl_param_spec_double_set_steps (GEGL_PARAM_SPEC_DOUBLE (copy),
                                            gspec->ui_step_small,
                                            gspec->ui_step_big);
          gegl_param_spec_double_set_digits (GEGL_PARAM_SPEC_DOUBLE (copy),
                                             gspec->ui_digits);
        }
      else
        {
          copy = g_param_spec_double (name, nick, blurb,
                                      spec->minimum,
                                      spec->maximum,
                                      spec->default_value,
                                      flags);
        }
    }
  else if (G_IS_PARAM_SPEC_FLOAT (pspec))
    {
      GParamSpecFloat *spec = G_PARAM_SPEC_FLOAT (pspec);

      copy = g_param_spec_float (name, nick, blurb,
                                 spec->minimum,
                                 spec->maximum,
                                 spec->default_value,
                                 flags);
    }
  else if (G_IS_PARAM_SPEC_INT (pspec))
    {
      GParamSpecInt *spec = G_PARAM_SPEC_INT (pspec);

      if (GEGL_IS_PARAM_SPEC_INT (pspec))
        {
          GeglParamSpecInt *gspec = GEGL_PARAM_SPEC_INT (pspec);

          copy = gegl_param_spec_int (name, nick, blurb,
                                      spec->minimum,
                                      spec->maximum,
                                      spec->default_value,
                                      gspec->ui_minimum,
                                      gspec->ui_maximum,
                                      gspec->ui_gamma,
                                      flags);
          gegl_param_spec_int_set_steps (GEGL_PARAM_SPEC_INT (copy),
                                         gspec->ui_step_small,
                                         gspec->ui_step_big);
        }
      else
        {
          copy = g_param_spec_int (name, nick, blurb,
                                   spec->minimum,
                                   spec->maximum,
                                   spec->default_value,
                                   flags);
        }
    }
  else if (G_IS_PARAM_SPEC_UINT (pspec))
    {
      GParamSpecUInt *spec = G_PARAM_SPEC_UINT (pspec);

      if (GEGL_IS_PARAM_SPEC_SEED (pspec))
        {
          GeglParamSpecSeed *gspec = GEGL_PARAM_SPEC_SEED (pspec);

          copy = gegl_param_spec_seed (name, nick, blurb,
                                       flags);

          G_PARAM_SPEC_UINT (copy)->minimum       = spec->minimum;
          G_PARAM_SPEC_UINT (copy)->maximum       = spec->maximum;
          G_PARAM_SPEC_UINT (copy)->default_value = spec->default_value;

          GEGL_PARAM_SPEC_SEED (copy)->ui_minimum = gspec->ui_minimum;
          GEGL_PARAM_SPEC_SEED (copy)->ui_maximum = gspec->ui_maximum;
        }
      else
        {
          copy = g_param_spec_uint (name, nick, blurb,
                                    spec->minimum,
                                    spec->maximum,
                                    spec->default_value,
                                    flags);
        }
    }
  else if (GIMP_IS_PARAM_SPEC_OBJECT (pspec))
    {
      /* GimpParamSpecColor, GimpParamSpecUnit and all GimpParamSpecResource types. */
      copy = gimp_param_spec_object_duplicate (pspec);
      copy->flags = flags;
    }
  else if (GEGL_IS_PARAM_SPEC_COLOR (pspec))
    {
      GeglColor *color;

      color = gegl_param_spec_color_get_default (pspec);
      color = gegl_color_duplicate (color);

      copy = gegl_param_spec_color (name, nick, blurb, color, flags);
      g_clear_object (&color);
    }
  else if (G_IS_PARAM_SPEC_OBJECT (pspec) &&
           G_PARAM_SPEC_VALUE_TYPE (pspec) == GEGL_TYPE_COLOR)
    {
      GValue    *value;
      GeglColor *color;

      value = (GValue *) g_param_spec_get_default_value (pspec);
      color = g_value_get_object (value);
      if (color)
        color = gegl_color_duplicate (color);

      copy = gegl_param_spec_color (name, nick, blurb,
                                    /*TRUE,*/
                                    color, flags);
      g_clear_object (&color);
    }
  else if (G_IS_PARAM_SPEC_PARAM (pspec))
    {
      copy = g_param_spec_param (name, nick, blurb,
                                 G_PARAM_SPEC_VALUE_TYPE (pspec),
                                 flags);
    }
  else if (GIMP_IS_PARAM_SPEC_PARASITE (pspec))
    {
      copy = gimp_param_spec_parasite (name, nick, blurb,
                                       flags);
    }
  else if (GIMP_IS_PARAM_SPEC_ARRAY (pspec))
    {
      if (GIMP_IS_PARAM_SPEC_INT32_ARRAY (pspec))
        {
          copy = gimp_param_spec_int32_array (name, nick, blurb,
                                              flags);
        }
      else if (GIMP_IS_PARAM_SPEC_DOUBLE_ARRAY (pspec))
        {
          copy = gimp_param_spec_double_array (name, nick, blurb, flags);
        }
    }
  else if (GIMP_IS_PARAM_SPEC_CORE_OBJECT_ARRAY (pspec))
    {
      copy = gimp_param_spec_core_object_array (name, nick, blurb,
                                                gimp_param_spec_core_object_array_get_object_type (pspec),
                                                flags);
    }
  else if (GIMP_IS_PARAM_SPEC_EXPORT_OPTIONS (pspec))
    {
      copy = gimp_param_spec_export_options (name, nick, blurb, flags);
    }
  else if (G_IS_PARAM_SPEC_OBJECT (pspec))
    {
      GType        value_type = G_PARAM_SPEC_VALUE_TYPE (pspec);
      const gchar *type_name  = g_type_name (value_type);

      if (value_type == G_TYPE_FILE                        ||
          /* These types are not visible in libgimpconfig
           * so we compare with type names instead.
           */
          g_strcmp0 (type_name, "GimpImage")          == 0 ||
          g_strcmp0 (type_name, "GimpDisplay")        == 0 ||
          g_strcmp0 (type_name, "GimpDrawable")       == 0 ||
          g_strcmp0 (type_name, "GimpLayer")          == 0 ||
          g_strcmp0 (type_name, "GimpGroupLayer")     == 0 ||
          g_strcmp0 (type_name, "GimpTextLayer")      == 0 ||
          g_strcmp0 (type_name, "GimpVectorLayer")    == 0 ||
          g_strcmp0 (type_name, "GimpChannel")        == 0 ||
          g_strcmp0 (type_name, "GimpItem")           == 0 ||
          g_strcmp0 (type_name, "GimpLayerMask")      == 0 ||
          g_strcmp0 (type_name, "GimpSelection")      == 0 ||
          g_strcmp0 (type_name, "GimpPath")           == 0 ||
          g_strcmp0 (type_name, "GimpDrawableFilter") == 0 ||
          g_strcmp0 (type_name, "GimpCurve")          == 0)
        {
          copy = g_param_spec_object (name, nick, blurb,
                                      value_type,
                                      flags);
        }
    }
  else if (G_IS_PARAM_SPEC_BOXED (pspec))
    {
      GType value_type = G_PARAM_SPEC_VALUE_TYPE (pspec);

      if (value_type == G_TYPE_BYTES ||
          value_type == G_TYPE_STRV)
        {
          copy = g_param_spec_boxed (name, nick, blurb, value_type, flags);
        }
    }

  if (copy)
    {
      GQuark      quark = 0;
      GHashTable *keys;

      if (G_UNLIKELY (! quark))
        quark = g_quark_from_static_string ("gegl-property-keys");

      keys = g_param_spec_get_qdata (pspec, quark);

      if (keys)
        g_param_spec_set_qdata_full (copy, quark, g_hash_table_ref (keys),
                                     (GDestroyNotify) g_hash_table_unref);
    }

  return copy;
}

/* --- end libammoos/config/fieldconfig/gimpconfig-params.c --- */

/* --- begin libammoos/config/fieldconfig/gimpconfig-path.c --- */
/* LIBGIMP - The AmmoOS Image Library
 * Copyright (C) 1995-1997 Spencer Kimball and Peter Mattis
 *
 * gimpconfig-path.c
 * Copyright (C) 2001  Sven Neumann <sven@ammoos.org>
 *
 * This library is free software: you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 3 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Library General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library.  If not, see
 * <https://www.gnu.org/licenses/>.
 */

#include "config.h"

#include <stdio.h>
#include <string.h>

#include <gio/gio.h>

#include "libgimpbase/gimpbase.h"

#include "gimpconfig-error.h"
#include "gimpconfig-path.h"

#include "libgimp/libgimp-intl.h"


/**
 * SECTION: gimpconfig-path
 * @title: GimpConfig-path
 * @short_description: File path utilities for libgimpconfig.
 *
 * File path utilities for libgimpconfig.
 **/


/**
 * gimp_config_path_get_type:
 *
 * Reveals the object type
 *
 * Returns: the #GType for a GimpConfigPath string property
 *
 * Since: 2.4
 **/
GType
gimp_config_path_get_type (void)
{
  static GType path_type = 0;

  if (! path_type)
    {
      const GTypeInfo type_info = { 0, };

      path_type = g_type_register_static (G_TYPE_STRING, "GimpConfigPath",
                                          &type_info, 0);
    }

  return path_type;
}


/*
 * GIMP_TYPE_PARAM_CONFIG_PATH
 */

#define GIMP_PARAM_SPEC_CONFIG_PATH(pspec) (G_TYPE_CHECK_INSTANCE_CAST ((pspec), GIMP_TYPE_PARAM_CONFIG_PATH, GimpParamSpecConfigPath))

typedef struct _GimpParamSpecConfigPath GimpParamSpecConfigPath;

struct _GimpParamSpecConfigPath
{
  GParamSpecString    parent_instance;

  GimpConfigPathType  type;
};

static void  gimp_param_config_path_class_init (GParamSpecClass *class);

/**
 * gimp_param_config_path_get_type:
 *
 * Reveals the object type
 *
 * Returns: the #GType for a directory path object
 *
 * Since: 2.4
 **/
GType
gimp_param_config_path_get_type (void)
{
  static GType spec_type = 0;

  if (! spec_type)
    {
      const GTypeInfo type_info =
      {
        sizeof (GParamSpecClass),
        NULL, NULL,
        (GClassInitFunc) gimp_param_config_path_class_init,
        NULL, NULL,
        sizeof (GimpParamSpecConfigPath),
        0, NULL, NULL
      };

      spec_type = g_type_register_static (G_TYPE_PARAM_STRING,
                                          "GimpParamConfigPath",
                                          &type_info, 0);
    }

  return spec_type;
}

static void
gimp_param_config_path_class_init (GParamSpecClass *class)
{
  class->value_type = GIMP_TYPE_CONFIG_PATH;
}

/**
 * gimp_param_spec_config_path:
 * @name:          Canonical name of the param
 * @nick:          Nickname of the param
 * @blurb:         Brief description of param.
 * @type:          a #GimpConfigPathType value.
 * @default_value: Value to use if none is assigned.
 * @flags:         a combination of #GParamFlags
 *
 * Creates a param spec to hold a filename, dir name,
 * or list of file or dir names.
 * See g_param_spec_internal() for more information.
 *
 * Returns: (transfer full): a newly allocated #GParamSpec instance
 *
 * Since: 2.4
 **/
GParamSpec *
gimp_param_spec_config_path (const gchar        *name,
                             const gchar        *nick,
                             const gchar        *blurb,
                             GimpConfigPathType  type,
                             const gchar        *default_value,
                             GParamFlags         flags)
{
  GParamSpecString *pspec;

  pspec = g_param_spec_internal (GIMP_TYPE_PARAM_CONFIG_PATH,
                                 name, nick, blurb, flags);

  pspec->default_value = g_strdup (default_value);

  GIMP_PARAM_SPEC_CONFIG_PATH (pspec)->type = type;

  return G_PARAM_SPEC (pspec);
}

/**
 * gimp_param_spec_config_path_type:
 * @pspec:         A #GParamSpec for a path param
 *
 * Tells whether the path param encodes a filename,
 * dir name, or list of file or dir names.
 *
 * Returns: a #GimpConfigPathType value
 *
 * Since: 2.4
 **/
GimpConfigPathType
gimp_param_spec_config_path_type (GParamSpec *pspec)
{
  g_return_val_if_fail (GIMP_IS_PARAM_SPEC_CONFIG_PATH (pspec), 0);

  return GIMP_PARAM_SPEC_CONFIG_PATH (pspec)->type;
}


/*
 * GimpConfig path utilities
 */

static gchar        * gimp_config_path_expand_only   (const gchar  *path,
                                                      GError      **error) G_GNUC_MALLOC;
static inline gchar * gimp_config_path_extract_token (const gchar **str);
static gchar        * gimp_config_path_unexpand_only (const gchar  *path) G_GNUC_MALLOC;


/**
 * gimp_config_build_data_path:
 * @name: directory name (in UTF-8 encoding)
 *
 * Creates a search path as it is used in the gimprc file.  The path
 * returned by gimp_config_build_data_path() includes a directory
 * below the user's ammoos directory and one in the system-wide data
 * directory.
 *
 * Note that you cannot use this path directly with gimp_path_parse().
 * As it is in the gimprc notation, you first need to expand and
 * recode it using gimp_config_path_expand().
 *
 * Returns: a newly allocated string
 *
 * Since: 2.4
 **/
gchar *
gimp_config_build_data_path (const gchar *name)
{
  if (g_getenv ("GIMP_TESTING_ABS_TOP_SRCDIR"))
    /* Unit-testing mode: the source directory is where data is found. */
    return g_strconcat (g_getenv ("GIMP_TESTING_ABS_TOP_SRCDIR"),
                        G_DIR_SEPARATOR_S, "data",
                        G_DIR_SEPARATOR_S, name,
                        NULL);
  else
    return g_strconcat ("${gimp_dir}", G_DIR_SEPARATOR_S, name,
                        G_SEARCHPATH_SEPARATOR_S,
                        "${gimp_data_dir}", G_DIR_SEPARATOR_S, name,
                        NULL);
}

/**
 * gimp_config_build_plug_in_path:
 * @name: directory name (in UTF-8 encoding)
 *
 * Creates a search path as it is used in the gimprc file.  The path
 * returned by gimp_config_build_plug_in_path() includes a directory
 * below the user's ammoos directory and one in the system-wide plug-in
 * directory.
 *
 * Note that you cannot use this path directly with gimp_path_parse().
 * As it is in the gimprc notation, you first need to expand and
 * recode it using gimp_config_path_expand().
 *
 * Returns: a newly allocated string
 *
 * Since: 2.4
 **/
gchar *
gimp_config_build_plug_in_path (const gchar *name)
{
  return g_strconcat ("${gimp_dir}", G_DIR_SEPARATOR_S, name,
                      G_SEARCHPATH_SEPARATOR_S,
                      "${gimp_plug_in_dir}", G_DIR_SEPARATOR_S, name,
                      NULL);
}

/**
 * gimp_config_build_writable_path:
 * @name: directory name (in UTF-8 encoding)
 *
 * Creates a search path as it is used in the gimprc file.  The path
 * returned by gimp_config_build_writable_path() is just the writable
 * parts of the search path constructed by gimp_config_build_data_path().
 *
 * Note that you cannot use this path directly with gimp_path_parse().
 * As it is in the gimprc notation, you first need to expand and
 * recode it using gimp_config_path_expand().
 *
 * Returns: a newly allocated string
 *
 * Since: 2.4
 **/
gchar *
gimp_config_build_writable_path (const gchar *name)
{
  return g_strconcat ("${gimp_dir}", G_DIR_SEPARATOR_S, name, NULL);
}

/**
 * gimp_config_build_system_path:
 * @name: directory name (in UTF-8 encoding)
 *
 * Creates a search path as it is used in the gimprc file.  The path
 * returned by gimp_config_build_system_path() is just the read-only
 * parts of the search path constructed by gimp_config_build_plug_in_path().
 *
 * Note that you cannot use this path directly with gimp_path_parse().
 * As it is in the gimprc notation, you first need to expand and
 * recode it using gimp_config_path_expand().
 *
 * Returns: a newly allocated string
 *
 * Since: 2.10.6
 **/
gchar *
gimp_config_build_system_path (const gchar *name)
{
  return g_strconcat ("${gimp_plug_in_dir}", G_DIR_SEPARATOR_S, name, NULL);
}

/**
 * gimp_config_path_expand:
 * @path:   a NUL-terminated string in UTF-8 encoding
 * @recode: whether to convert to the filesystem's encoding
 * @error:  return location for errors
 *
 * Paths as stored in gimprc and other config files have to be treated
 * special.  The string may contain special identifiers such as for
 * example ${gimp_dir} that have to be substituted before use. Also
 * the user's filesystem may be in a different encoding than UTF-8
 * (which is what is used for the gimprc). This function does the
 * variable substitution for you and can also attempt to convert to
 * the filesystem encoding.
 *
 * To reverse the expansion, use gimp_config_path_unexpand().
 *
 * Returns: a newly allocated NUL-terminated string
 *
 * Since: 2.4
 **/
gchar *
gimp_config_path_expand (const gchar  *path,
                         gboolean      recode,
                         GError      **error)
{
  g_return_val_if_fail (path != NULL, NULL);
  g_return_val_if_fail (error == NULL || *error == NULL, NULL);

  if (recode)
    {
      gchar *retval;
      gchar *expanded = gimp_config_path_expand_only (path, error);

      if (! expanded)
        return NULL;

      retval = g_filename_from_utf8 (expanded, -1, NULL, NULL, error);

      g_free (expanded);

      return retval;
    }

  return gimp_config_path_expand_only (path, error);
}

/**
 * gimp_config_path_expand_to_files:
 * @path:  a NUL-terminated string in UTF-8 encoding
 * @error: return location for errors
 *
 * Paths as stored in the gimprc have to be treated special. The
 * string may contain special identifiers such as for example
 * ${gimp_dir} that have to be substituted before use. Also the user's
 * filesystem may be in a different encoding than UTF-8 (which is what
 * is used for the gimprc).
 *
 * This function runs @path through gimp_config_path_expand() and
 * gimp_path_parse(), then turns the filenames returned by
 * gimp_path_parse() into GFile using g_file_new_for_path().
 *
 * Returns: (element-type GFile) (transfer full):
                 a #GList of newly allocated #GFile objects.
 *
 * Since: 2.10
 **/
GList *
gimp_config_path_expand_to_files (const gchar  *path,
                                  GError      **error)
{
  GList *files;
  GList *list;
  gchar *expanded;

  g_return_val_if_fail (path != NULL, NULL);
  g_return_val_if_fail (error == NULL || *error == NULL, NULL);

  expanded = gimp_config_path_expand (path, TRUE, error);

  if (! expanded)
    return NULL;

  files = gimp_path_parse (expanded, 256, FALSE, NULL);

  g_free (expanded);

  for (list = files; list; list = g_list_next (list))
    {
      gchar *dir = list->data;

      list->data = g_file_new_for_path (dir);
      g_free (dir);
    }

  return files;
}

/**
 * gimp_config_path_unexpand:
 * @path:   a NUL-terminated string
 * @recode: whether @path is in filesystem encoding or UTF-8
 * @error:  return location for errors
 *
 * The inverse operation of gimp_config_path_expand()
 *
 * This function takes a @path and tries to substitute the first
 * elements by well-known special identifiers such as for example
 * ${gimp_dir}. The unexpanded path can then be stored in gimprc and
 * other config files.
 *
 * If @recode is %TRUE then @path is in local filesystem encoding,
 * if @recode is %FALSE then @path is assumed to be UTF-8.
 *
 * Returns: a newly allocated NUL-terminated UTF-8 string
 *
 * Since: 2.10
 **/
gchar *
gimp_config_path_unexpand (const gchar  *path,
                           gboolean      recode,
                           GError      **error)
{
  g_return_val_if_fail (path != NULL, NULL);
  g_return_val_if_fail (error == NULL || *error == NULL, NULL);

  if (recode)
    {
      gchar *retval;
      gchar *utf8 = g_filename_to_utf8 (path, -1, NULL, NULL, error);

      if (! utf8)
        return NULL;

      retval = gimp_config_path_unexpand_only (utf8);

      g_free (utf8);

      return retval;
    }

  return gimp_config_path_unexpand_only (path);
}

/**
 * gimp_file_new_for_config_path:
 * @path:   a NUL-terminated string in UTF-8 encoding
 * @error:  return location for errors
 *
 * Expands @path using gimp_config_path_expand() and returns a #GFile
 * for the expanded path.
 *
 * To reverse the expansion, use gimp_file_get_config_path().
 *
 * Returns: (nullable) (transfer full): a newly allocated #GFile,
 *          or %NULL if the expansion failed.
 *
 * Since: 2.10
 **/
GFile *
gimp_file_new_for_config_path (const gchar  *path,
                               GError      **error)
{
  GFile *file = NULL;
  gchar *expanded;

  g_return_val_if_fail (path != NULL, NULL);
  g_return_val_if_fail (error == NULL || *error == NULL, NULL);

  expanded = gimp_config_path_expand (path, TRUE, error);

  if (expanded)
    {
      file = g_file_new_for_path (expanded);
      g_free (expanded);
    }

  return file;
}

/**
 * gimp_file_get_config_path:
 * @file:   a #GFile
 * @error:  return location for errors
 *
 * Unexpands @file's path using gimp_config_path_unexpand() and
 * returns the unexpanded path.
 *
 * The inverse operation of gimp_file_new_for_config_path().
 *
 * Returns: a newly allocated NUL-terminated UTF-8 string, or %NULL if
 *               unexpanding failed.
 *
 * Since: 2.10
 **/
gchar *
gimp_file_get_config_path (GFile   *file,
                           GError **error)
{
  gchar *unexpanded = NULL;
  gchar *path;

  g_return_val_if_fail (G_IS_FILE (file), NULL);
  g_return_val_if_fail (error == NULL || *error == NULL, NULL);

  path = g_file_get_path (file);

  if (path)
    {
      unexpanded = gimp_config_path_unexpand (path, TRUE, error);
      g_free (path);
    }
  else
    {
      g_set_error_literal (error, 0, 0,
                           _("File has no path representation"));
    }

  return unexpanded;
}


/*  private functions  */

#define SUBSTS_ALLOC 4

static gchar *
gimp_config_path_expand_only (const gchar  *path,
                              GError      **error)
{
  const gchar *home;
  const gchar *p;
  const gchar *s;
  gchar       *n;
  gchar       *token;
  gchar       *filename = NULL;
  gchar       *expanded = NULL;
  gchar      **substs   = NULL;
  guint        n_substs = 0;
  gint         length   = 0;
  guint        i;

  home = g_get_home_dir ();
  if (home)
    home = gimp_filename_to_utf8 (home);

  p = path;

  while (*p)
    {
      if (*p == '~' && home)
        {
          length += strlen (home);
          p += 1;
        }
      else if ((token = gimp_config_path_extract_token (&p)) != NULL)
        {
          for (i = 0; i < n_substs; i++)
            if (strcmp (substs[2*i], token) == 0)
              break;

          if (i < n_substs)
            {
              s = substs[2*i+1];
            }
          else
            {
              s = NULL;

              if (strcmp (token, "gimp_dir") == 0)
                s = gimp_directory ();
              else if (strcmp (token, "gimp_data_dir") == 0)
                s = gimp_data_directory ();
              else if (strcmp (token, "gimp_plug_in_dir") == 0 ||
                       strcmp (token, "gimp_plugin_dir") == 0)
                s = gimp_plug_in_directory ();
              else if (strcmp (token, "gimp_sysconf_dir") == 0)
                s = gimp_sysconf_directory ();
              else if (strcmp (token, "gimp_installation_dir") == 0)
                s = gimp_installation_directory ();
              else if (strcmp (token, "gimp_cache_dir") == 0)
                s = gimp_cache_directory ();
              else if (strcmp (token, "gimp_temp_dir") == 0)
                s = gimp_temp_directory ();

              if (!s)
                s = g_getenv (token);

#ifdef G_OS_WIN32
              /* The default user gimprc on Windows references
               * ${TEMP}, but not all Windows installations have that
               * environment variable, even if it should be kinda
               * standard. So special-case it.
               */
              if (!s && strcmp (token, "TEMP") == 0)
                s = g_get_tmp_dir ();
#endif  /* G_OS_WIN32 */
            }

          if (!s)
            {
              g_set_error (error, GIMP_CONFIG_ERROR, GIMP_CONFIG_ERROR_PARSE,
                           _("Cannot expand ${%s}"), token);
              g_free (token);
              goto cleanup;
            }

          if (n_substs % SUBSTS_ALLOC == 0)
            substs = g_renew (gchar *, substs, 2 * (n_substs + SUBSTS_ALLOC));

          substs[2*n_substs]     = token;
          substs[2*n_substs + 1] = (gchar *) gimp_filename_to_utf8 (s);

          length += strlen (substs[2*n_substs + 1]);

          n_substs++;
        }
      else
        {
          length += g_utf8_skip[(const guchar) *p];
          p = g_utf8_next_char (p);
        }
    }

  if (n_substs == 0)
    return g_strdup (path);

  expanded = g_new (gchar, length + 1);

  p = path;
  n = expanded;

  while (*p)
    {
      if (*p == '~' && home)
        {
          *n = '\0';

          g_strlcat (n, home, length + 1);
          n += strlen (home);
          p += 1;
        }
      else if ((token = gimp_config_path_extract_token (&p)) != NULL)
        {
          for (i = 0; i < n_substs; i++)
            {
              if (strcmp (substs[2*i], token) == 0)
                {
                  s = substs[2*i+1];

                  *n = '\0';
                  g_strlcat (n, s, length + 1);
                  n += strlen (s);

                  break;
                }
            }

          g_free (token);
        }
      else
        {
          *n++ = *p++;
        }
    }

  *n = '\0';

 cleanup:
  for (i = 0; i < n_substs; i++)
    g_free (substs[2*i]);

  g_free (substs);
  g_free (filename);

  return expanded;
}

static inline gchar *
gimp_config_path_extract_token (const gchar **str)
{
  const gchar *p;
  gchar       *token;

  if (strncmp (*str, "${", 2))
    return NULL;

  p = *str + 2;

  while (*p && (*p != '}'))
    p = g_utf8_next_char (p);

  if (! *p)
    return NULL;

  token = g_strndup (*str + 2, g_utf8_pointer_to_offset (*str + 2, p));

  *str = p + 1; /* after the closing bracket */

  return token;
}

static gchar *
gimp_config_path_unexpand_only (const gchar *path)
{
  const struct
  {
    const gchar *id;
    const gchar *prefix;
  }
  identifiers[] =
  {
    { "${gimp_plug_in_dir}",      gimp_plug_in_directory () },
    { "${gimp_data_dir}",         gimp_data_directory () },
    { "${gimp_sysconf_dir}",      gimp_sysconf_directory () },
    { "${gimp_installation_dir}", gimp_installation_directory () },
    { "${gimp_cache_dir}",        gimp_cache_directory () },
    { "${gimp_temp_dir}",         gimp_temp_directory () },
    { "${gimp_dir}",              gimp_directory () }
  };

  GList *files;
  GList *list;
  gchar *unexpanded;

  files = gimp_path_parse (path, 256, FALSE, NULL);

  for (list = files; list; list = g_list_next (list))
    {
      gchar *dir = list->data;
      gint   i;

      for (i = 0; i < G_N_ELEMENTS (identifiers); i++)
        {
          if (g_str_has_prefix (dir, identifiers[i].prefix))
            {
              gchar *tmp = g_strconcat (identifiers[i].id,
                                        dir + strlen (identifiers[i].prefix),
                                        NULL);

              g_free (dir);
              list->data = tmp;

              break;
            }
        }
    }

  unexpanded = gimp_path_to_str (files);

  gimp_path_free (files);

  return unexpanded;
}

/* --- end libammoos/config/fieldconfig/gimpconfig-path.c --- */

/* --- begin libammoos/config/fieldconfig/gimpconfig-register.c --- */
/* LIBGIMP - The AmmoOS Image Library
 * Copyright (C) 1995-2003 Peter Mattis and Spencer Kimball
 *
 * gimpconfig-register.c
 * Copyright (C) 2008-2019 Michael Natterer <mitch@ammoos.org>
 *
 * This library is free software: you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 3 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library.  If not, see
 * <https://www.gnu.org/licenses/>.
 */

#include "config.h"

#include <cairo.h>
#include <gdk-pixbuf/gdk-pixbuf.h>

#include <gegl-paramspecs.h>

#include "libgimpbase/gimpbase.h"

#include "gimpconfig.h"


/*  local function prototypes  */

static void     gimp_config_class_init   (GObjectClass  *klass,
                                          GParamSpec   **pspecs);
static void     gimp_config_set_property (GObject       *object,
                                          guint          property_id,
                                          const GValue  *value,
                                          GParamSpec    *pspec);
static void     gimp_config_get_property (GObject       *object,
                                          guint          property_id,
                                          GValue        *value,
                                          GParamSpec    *pspec);

static GValue * gimp_config_value_get    (GObject       *object,
                                          GParamSpec    *pspec);
static GValue * gimp_config_value_new    (GParamSpec    *pspec);
static void     gimp_config_value_free   (GValue        *value);


/*  public functions  */

/**
 * gimp_config_type_register:
 * @parent_type: type from which this type will be derived
 * @type_name:   string used as the name of the new type
 * @pspecs: (array length=n_pspecs): array of #GParamSpec to install as properties on the new type
 * @n_pspecs:    the number of param specs in @pspecs
 *
 * This function is a fancy wrapper around g_type_register_static().
 * It creates a new object type as subclass of @parent_type, installs
 * @pspecs on it and makes the new type implement the #GimpConfig
 * interface.
 *
 * Returns: the newly registered #GType
 *
 * Since: 3.0
 **/
GType
gimp_config_type_register (GType         parent_type,
                           const gchar  *type_name,
                           GParamSpec  **pspecs,
                           gint          n_pspecs)
{
  GParamSpec **terminated_pspecs;
  GTypeQuery   query;
  GType        config_type;

  g_return_val_if_fail (g_type_is_a (parent_type, G_TYPE_OBJECT), G_TYPE_NONE);
  g_return_val_if_fail (type_name != NULL, G_TYPE_NONE);
  g_return_val_if_fail (pspecs != NULL || n_pspecs == 0, G_TYPE_NONE);

  terminated_pspecs = g_new0 (GParamSpec *, n_pspecs + 1);

  memcpy (terminated_pspecs, pspecs, sizeof (GParamSpec *) * n_pspecs);

  g_type_query (parent_type, &query);

  {
    GTypeInfo info =
    {
      query.class_size,
      (GBaseInitFunc) NULL,
      (GBaseFinalizeFunc) NULL,
      (GClassInitFunc) gimp_config_class_init,
      NULL,           /* class_finalize */
      terminated_pspecs,
      query.instance_size,
      0,              /* n_preallocs */
      (GInstanceInitFunc) NULL,
    };

    config_type = g_type_register_static (parent_type, type_name,
                                          &info, 0);

    if (! g_type_is_a (parent_type, GIMP_TYPE_CONFIG))
      {
        const GInterfaceInfo config_info =
        {
          NULL, /* interface_init     */
          NULL, /* interface_finalize */
          NULL  /* interface_data     */
        };

        g_type_add_interface_static (config_type, GIMP_TYPE_CONFIG,
                                     &config_info);
      }
  }

  return config_type;
}


/*  private functions  */

static void
gimp_config_class_init (GObjectClass  *klass,
                        GParamSpec   **pspecs)
{
  gint i;

  klass->set_property = gimp_config_set_property;
  klass->get_property = gimp_config_get_property;

  for (i = 0; pspecs[i] != NULL; i++)
    {
      GParamSpec *pspec = pspecs[i];
      GParamSpec *copy  = gimp_config_param_spec_duplicate (pspec);

      if (copy)
        {
          g_object_class_install_property (klass, i + 1, copy);
          /* If the original param spec was floating, this would unref
           * it. Otherwise (e.g. it's a spec taken from another object),
           * nothing happens.
           */
          g_param_spec_sink (pspec);
        }
      else
        {
          GType        value_type = G_PARAM_SPEC_VALUE_TYPE (pspec);
          const gchar *type_name  = g_type_name (value_type);

          /* There are some properties that we don't care to copy because they
           * are not serializable anyway (or we don't want them to be).
           * GimpContext properties are one such property type. We can find them
           * e.g. in some custom GEGL ops, such as "ammoos:offset". So we silently
           * ignore these.
           * We might add more types of properties to the list as we discover
           * more cases. We keep warnings for all the other types which we
           * explicitly don't support.
           */
          if (g_strcmp0 (type_name, "GimpContext") != 0 &&
              /* Format specs are a GParamSpecPointer. There might be other
               * pointer specs we might be able to serialize, but BablFormat are
               * not one of these (there might be easy serializable formats, but
               * many are not and anyway it's probably not a data which ops or
               * plug-ins want to remember across run).
               */
              ! GEGL_IS_PARAM_SPEC_FORMAT (pspec))
            g_warning ("%s: not supported: %s (%s | %s)\n", G_STRFUNC,
                       g_type_name (G_TYPE_FROM_INSTANCE (pspec)), pspec->name, type_name);
        }
    }

  g_free (pspecs);
}

static void
gimp_config_set_property (GObject      *object,
                          guint         property_id,
                          const GValue *value,
                          GParamSpec   *pspec)
{
  GValue *val = gimp_config_value_get (object, pspec);

  g_value_copy (value, val);
}

static void
gimp_config_get_property (GObject    *object,
                          guint       property_id,
                          GValue     *value,
                          GParamSpec *pspec)
{
  GValue *val = gimp_config_value_get (object, pspec);

  g_value_copy (val, value);
}

static GValue *
gimp_config_value_get (GObject    *object,
                       GParamSpec *pspec)
{
  GHashTable *properties;
  GValue     *value;

  properties = g_object_get_data (object, "ammoos-config-properties");

  if (! properties)
    {
      properties =
        g_hash_table_new_full (g_str_hash,
                               g_str_equal,
                               (GDestroyNotify) g_free,
                               (GDestroyNotify) gimp_config_value_free);

      g_object_set_data_full (object, "ammoos-config-properties", properties,
                              (GDestroyNotify) g_hash_table_unref);
    }

  value = g_hash_table_lookup (properties, pspec->name);

  if (! value)
    {
      value = gimp_config_value_new (pspec);
      g_hash_table_insert (properties, g_strdup (pspec->name), value);
    }

  return value;
}

static GValue *
gimp_config_value_new (GParamSpec *pspec)
{
  GValue *value = g_slice_new0 (GValue);

  g_value_init (value, pspec->value_type);
  g_param_value_set_default (pspec, value);

  return value;
}

static void
gimp_config_value_free (GValue *value)
{
  g_value_unset (value);
  g_slice_free (GValue, value);
}

/* --- end libammoos/config/fieldconfig/gimpconfig-register.c --- */

/* --- begin libammoos/config/fieldconfig/gimpconfig-serialize.c --- */
/* LIBGIMP - The AmmoOS Image Library
 * Copyright (C) 1995-1997 Spencer Kimball and Peter Mattis
 *
 * Object properties serialization routines
 * Copyright (C) 2001-2002  Sven Neumann <sven@ammoos.org>
 *
 * This library is free software: you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 3 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Library General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library.  If not, see
 * <https://www.gnu.org/licenses/>.
 */

#include "config.h"

#include <cairo.h>
#include <gegl.h>
#include <gdk-pixbuf/gdk-pixbuf.h>

#include "libgimpbase/gimpbase.h"
#include "libgimpmath/gimpmath.h"
#include "libgimpcolor/gimpcolor.h"

#include "gimpconfigtypes.h"

#include "gimpconfigwriter.h"
#include "gimpconfig-iface.h"
#include "gimpconfig-params.h"
#include "gimpconfig-path.h"
#include "gimpconfig-serialize.h"
#include "gimpconfig-utils.h"


/**
 * SECTION: gimpconfig-serialize
 * @title: GimpConfig-serialize
 * @short_description: Serializing for libgimpconfig.
 *
 * Serializing interface for libgimpconfig.
 **/


static gboolean gimp_config_serialize_strv  (const GValue *value,
                                             GString      *str);
static gboolean gimp_config_serialize_array (const GValue *value,
                                             GString      *str);


/**
 * gimp_config_serialize_properties:
 * @config: a #GimpConfig.
 * @writer: a #GimpConfigWriter.
 *
 * This function writes all object properties to the @writer.
 *
 * Returns: %TRUE if serialization succeeded, %FALSE otherwise
 *
 * Since: 2.4
 **/
gboolean
gimp_config_serialize_properties (GimpConfig       *config,
                                  GimpConfigWriter *writer)
{
  GObjectClass  *klass;
  GParamSpec   **property_specs;
  guint          n_property_specs;
  guint          i;
  gboolean       success = TRUE;

  g_return_val_if_fail (G_IS_OBJECT (config), FALSE);

  klass = G_OBJECT_GET_CLASS (config);

  property_specs = g_object_class_list_properties (klass, &n_property_specs);

  if (! property_specs)
    return success;

  for (i = 0; i < n_property_specs; i++)
    {
      GParamSpec *prop_spec = property_specs[i];

      if (! (prop_spec->flags & GIMP_CONFIG_PARAM_SERIALIZE))
        continue;

      /* Some properties may fail writing, which shouldn't break serializing
       * more properties, yet final result would be a (partial) failure.
       */
      if (! gimp_config_serialize_property (config, prop_spec, writer))
        success = FALSE;
    }

  g_free (property_specs);

  return success;
}

/**
 * gimp_config_serialize_changed_properties:
 * @config: a #GimpConfig.
 * @writer: a #GimpConfigWriter.
 *
 * This function writes all object properties that have been changed from
 * their default values to the @writer.
 *
 * Returns: %TRUE if serialization succeeded, %FALSE otherwise
 *
 * Since: 2.4
 **/
gboolean
gimp_config_serialize_changed_properties (GimpConfig       *config,
                                          GimpConfigWriter *writer)
{
  GObjectClass  *klass;
  GParamSpec   **property_specs;
  guint          n_property_specs;
  guint          i;
  GValue         value   = G_VALUE_INIT;
  gboolean       success = TRUE;

  g_return_val_if_fail (G_IS_OBJECT (config), FALSE);

  klass = G_OBJECT_GET_CLASS (config);

  property_specs = g_object_class_list_properties (klass, &n_property_specs);

  if (! property_specs)
    return success;

  for (i = 0; i < n_property_specs; i++)
    {
      GParamSpec *prop_spec = property_specs[i];

      if (! (prop_spec->flags & GIMP_CONFIG_PARAM_SERIALIZE))
        continue;

      g_value_init (&value, prop_spec->value_type);
      g_object_get_property (G_OBJECT (config), prop_spec->name, &value);

      if (! g_param_value_defaults (prop_spec, &value))
        {
          /* Some properties may fail writing, which shouldn't break serializing
           * more properties, yet final result would be a (partial) failure.
           */
          if (! gimp_config_serialize_property (config, prop_spec, writer))
            success = FALSE;
        }

      g_value_unset (&value);
    }

  g_free (property_specs);

  return success;
}

/**
 * gimp_config_serialize_property:
 * @config:     a #GimpConfig.
 * @param_spec: a #GParamSpec.
 * @writer:     a #GimpConfigWriter.
 *
 * This function serializes a single object property to the @writer.
 *
 * Returns: %TRUE if serialization succeeded, %FALSE otherwise
 *
 * Since: 2.4
 **/
gboolean
gimp_config_serialize_property (GimpConfig       *config,
                                GParamSpec       *param_spec,
                                GimpConfigWriter *writer)
{
  GimpConfigInterface *config_iface = NULL;
  GimpConfigInterface *parent_iface = NULL;
  GValue               value        = G_VALUE_INIT;
  gboolean             success      = FALSE;

  if (! (param_spec->flags & GIMP_CONFIG_PARAM_SERIALIZE))
    return FALSE;

  if (param_spec->flags & GIMP_CONFIG_PARAM_IGNORE ||
      param_spec->flags & GIMP_PARAM_DONT_SERIALIZE)
    return TRUE;

  g_value_init (&value, param_spec->value_type);
  g_object_get_property (G_OBJECT (config), param_spec->name, &value);

  if (param_spec->flags & GIMP_CONFIG_PARAM_DEFAULTS &&
      g_param_value_defaults (param_spec, &value))
    {
      g_value_unset (&value);
      return TRUE;
    }

  if (G_TYPE_IS_OBJECT (param_spec->owner_type))
    {
      GTypeClass *owner_class = g_type_class_peek (param_spec->owner_type);

      config_iface = g_type_interface_peek (owner_class, GIMP_TYPE_CONFIG);

      /*  We must call serialize_property() *only* if the *exact* class
       *  which implements it is param_spec->owner_type's class.
       *
       *  Therefore, we ask param_spec->owner_type's immediate parent class
       *  for it's GimpConfigInterface and check if we get a different
       *  pointer.
       *
       *  (if the pointers are the same, param_spec->owner_type's
       *   GimpConfigInterface is inherited from one of it's parent classes
       *   and thus not able to handle param_spec->owner_type's properties).
       */
      if (config_iface)
        {
          GTypeClass *owner_parent_class;

          owner_parent_class = g_type_class_peek_parent (owner_class);

          parent_iface = g_type_interface_peek (owner_parent_class,
                                                GIMP_TYPE_CONFIG);
        }
    }

  if (config_iface                     &&
      config_iface != parent_iface     && /* see comment above */
      config_iface->serialize_property &&
      config_iface->serialize_property (config,
                                        param_spec->param_id,
                                        (const GValue *) &value,
                                        param_spec,
                                        writer))
    {
      success = TRUE;
    }

  /*  If there is no serialize_property() method *or* if it returned
   *  FALSE, continue with the default implementation
   */

  if (! success)
    {
      if (G_VALUE_TYPE (&value) == GIMP_TYPE_PARASITE)
        {
          GimpParasite *parasite = g_value_get_boxed (&value);

          gimp_config_writer_open (writer, param_spec->name);

          if (parasite)
            {
              const gchar   *name;
              gconstpointer  data;
              guint32        data_length;
              gulong         flags;

              name = gimp_parasite_get_name (parasite);
              gimp_config_writer_string (writer, name);

              flags = gimp_parasite_get_flags (parasite);
              data = gimp_parasite_get_data (parasite, &data_length);
              gimp_config_writer_printf (writer, "%lu %u", flags, data_length);
              gimp_config_writer_data (writer, data_length, data);

              success = TRUE;
            }

          if (success)
            gimp_config_writer_close (writer);
          else
            gimp_config_writer_revert (writer);
        }
      else if (G_VALUE_TYPE (&value) == G_TYPE_BYTES)
        {
          GBytes *bytes = g_value_get_boxed (&value);

          gimp_config_writer_open (writer, param_spec->name);

          if (bytes)
            {
              gconstpointer data;
              gsize         data_length;

              data = g_bytes_get_data (bytes, &data_length);

              gimp_config_writer_printf (writer, "%" G_GSIZE_FORMAT, data_length);
              gimp_config_writer_data (writer, data_length, data);
            }
          else
            {
              gimp_config_writer_printf (writer, "%s", "NULL");
            }

          success = TRUE;
          gimp_config_writer_close (writer);
        }
      else if (GIMP_VALUE_HOLDS_COLOR (&value))
        {
          GeglColor *color      = g_value_get_object (&value);
          gboolean   free_color = FALSE;

          gimp_config_writer_open (writer, param_spec->name);

          if (color)
            {
              guint xcf_version = gimp_config_get_xcf_version (config);

              /* If XCF version is before AmmoOS Image 3.0, then colors should be saved
               * in legacy GimpRGB format for backwards compatibility */
              if (xcf_version >= 14)
                {
                  const gchar   *encoding;
                  const Babl    *format = gegl_color_get_format (color);
                  const Babl    *space;
                  GBytes        *bytes;
                  gconstpointer  data;
                  gsize          data_length;
                  int            profile_length = 0;

                  gimp_config_writer_open (writer, "color");

                  if (babl_format_is_palette (format))
                    {
                      guint8 pixel[40];

                      /* As a special case, we don't want to serialize
                       * palette colors, because they are just too much
                       * dependent on external data and cannot be
                       * deserialized back safely. So we convert them first.
                       */
                       free_color = TRUE;
                       color = gegl_color_duplicate (color);

                       format = babl_format_with_space ("R'G'B'A u8", format);
                       gegl_color_get_pixel (color, format, pixel);
                       gegl_color_set_pixel (color, format, pixel);
                    }

                  encoding = babl_format_get_encoding (format);
                  gimp_config_writer_string (writer, encoding);

                  bytes = gegl_color_get_bytes (color, format);
                  data  = g_bytes_get_data (bytes, &data_length);

                  gimp_config_writer_printf (writer, "%" G_GSIZE_FORMAT,
                                             data_length);
                  gimp_config_writer_data (writer, data_length, data);

                  space = babl_format_get_space (format);
                  if (space != babl_space ("sRGB"))
                    {
                      guint8 *profile_data;

                      profile_data =
                        (guint8 *) babl_space_get_icc (babl_format_get_space (format),
                                                        &profile_length);
                      gimp_config_writer_printf (writer, "%u", profile_length);
                      if (profile_data)
                        gimp_config_writer_data (writer, profile_length,
                                                 profile_data);
                    }
                  else
                    {
                      gimp_config_writer_printf (writer, "%u", profile_length);
                    }

                  g_bytes_unref (bytes);
                  gimp_config_writer_close (writer);
                }
              else
                {
                  gchar   buf[4][G_ASCII_DTOSTR_BUF_SIZE];
                  gdouble rgba[4];

                  gegl_color_get_pixel (color, babl_format ("R'G'B'A double"),
                                        rgba);

                  for (gint i = 0; i < 4; i++)
                    g_ascii_dtostr (buf[i], G_ASCII_DTOSTR_BUF_SIZE, rgba[i]);

                  gimp_config_writer_printf (writer,
                                             "(color-rgba %s %s %s %s)",
                                             buf[0], buf[1], buf[2], buf[3]);
                }
            }
          else
            {
              gimp_config_writer_printf (writer, "%s", "NULL");
            }

          success = TRUE;
          gimp_config_writer_close (writer);

          if (free_color)
            g_object_unref (color);
        }
      else if (GIMP_VALUE_HOLDS_UNIT (&value))
        {
          GimpUnit *unit = g_value_get_object (&value);

          gimp_config_writer_open (writer, param_spec->name);

          if (unit)
            gimp_config_writer_printf (writer, "%s", gimp_unit_get_name (unit));
          else
            gimp_config_writer_printf (writer, "%s", "NULL");

          success = TRUE;
          gimp_config_writer_close (writer);
        }
      else if (G_VALUE_HOLDS_OBJECT (&value) &&
               G_VALUE_TYPE (&value) != G_TYPE_FILE)
        {
          GimpConfigInterface *config_iface = NULL;
          GimpConfig          *prop_object;

          prop_object = g_value_get_object (&value);

          if (prop_object)
            config_iface = GIMP_CONFIG_GET_IFACE (prop_object);
          else
            success = TRUE;

          if (config_iface)
            {
              gimp_config_writer_open (writer, param_spec->name);

              /*  if the object property is not GIMP_CONFIG_PARAM_AGGREGATE,
               *  deserializing will need to know the exact type
               *  in order to create the object
               */
              if (! (param_spec->flags & GIMP_CONFIG_PARAM_AGGREGATE))
                {
                  GType object_type = G_TYPE_FROM_INSTANCE (prop_object);

                  gimp_config_writer_string (writer, g_type_name (object_type));
                }

              success = config_iface->serialize (prop_object, writer, NULL);

              if (success)
                gimp_config_writer_close (writer);
              else
                gimp_config_writer_revert (writer);
            }
        }
      else
        {
          GString *str = g_string_new (NULL);

          success = gimp_config_serialize_value (&value, str, TRUE);

          if (success)
            {
              gimp_config_writer_open (writer, param_spec->name);
              gimp_config_writer_print (writer, str->str, str->len);
              gimp_config_writer_close (writer);
            }

          g_string_free (str, TRUE);
        }

      if (! success)
        {
          /* don't warn for empty string properties */
          if (G_VALUE_HOLDS_STRING (&value))
            {
              success = TRUE;
            }
          else
            {
              g_warning ("couldn't serialize property %s::%s of type %s",
                         g_type_name (G_TYPE_FROM_INSTANCE (config)),
                         param_spec->name,
                         g_type_name (param_spec->value_type));
            }
        }
    }

  g_value_unset (&value);

  return success;
}

/**
 * gimp_config_serialize_property_by_name:
 * @config:    a #GimpConfig.
 * @prop_name: the property's name.
 * @writer:    a #GimpConfigWriter.
 *
 * This function serializes a single object property to the @writer.
 *
 * Returns: %TRUE if serialization succeeded, %FALSE otherwise
 *
 * Since: 2.6
 **/
gboolean
gimp_config_serialize_property_by_name (GimpConfig       *config,
                                        const gchar      *prop_name,
                                        GimpConfigWriter *writer)
{
  GParamSpec *pspec;

  pspec = g_object_class_find_property (G_OBJECT_GET_CLASS (config),
                                        prop_name);

  if (! pspec)
    return FALSE;

  return gimp_config_serialize_property (config, pspec, writer);
}

/**
 * gimp_config_serialize_value:
 * @value: a #GValue.
 * @str: a #GString.
 * @escaped: whether to escape string values.
 *
 * This utility function appends a string representation of #GValue to @str.
 *
 * Returns: %TRUE if serialization succeeded, %FALSE otherwise.
 *
 * Since: 2.4
 **/
gboolean
gimp_config_serialize_value (const GValue *value,
                             GString      *str,
                             gboolean      escaped)
{
  if (G_VALUE_TYPE (value) == G_TYPE_STRV)
    {
      return gimp_config_serialize_strv (value, str);
    }

  if (GIMP_VALUE_HOLDS_INT32_ARRAY (value) ||
      GIMP_VALUE_HOLDS_DOUBLE_ARRAY (value))
    {
      return gimp_config_serialize_array (value, str);
    }

  if (G_VALUE_HOLDS_BOOLEAN (value))
    {
      gboolean boolean;

      boolean = g_value_get_boolean (value);
      g_string_append (str, boolean ? "yes" : "no");
      return TRUE;
    }

  if (G_VALUE_HOLDS_ENUM (value))
    {
      GEnumClass *enum_class = g_type_class_peek (G_VALUE_TYPE (value));
      GEnumValue *enum_value = g_enum_get_value (enum_class,
                                                 g_value_get_enum (value));

      if (enum_value && enum_value->value_nick)
        {
          g_string_append (str, enum_value->value_nick);
          return TRUE;
        }
      else
        {
          g_warning ("Couldn't get nick for enum_value of %s",
                     G_ENUM_CLASS_TYPE_NAME (enum_class));
          return FALSE;
        }
    }

  if (G_VALUE_HOLDS_STRING (value))
    {
      const gchar *cstr = g_value_get_string (value);

      if (! cstr)
        return FALSE;

      if (escaped)
        gimp_config_string_append_escaped (str, cstr);
      else
        g_string_append (str, cstr);

      return TRUE;
    }

  if (G_VALUE_HOLDS_DOUBLE (value) || G_VALUE_HOLDS_FLOAT (value))
    {
      gdouble v_double;
      gchar   buf[G_ASCII_DTOSTR_BUF_SIZE];

      if (G_VALUE_HOLDS_DOUBLE (value))
        v_double = g_value_get_double (value);
      else
        v_double = (gdouble) g_value_get_float (value);

      g_ascii_dtostr (buf, sizeof (buf), v_double);
      g_string_append (str, buf);
      return TRUE;
    }

  if (GIMP_VALUE_HOLDS_MATRIX2 (value))
    {
      GimpMatrix2 *trafo;

      trafo = g_value_get_boxed (value);

      if (trafo)
        {
          gchar buf[4][G_ASCII_DTOSTR_BUF_SIZE];
          gint  i, j, k;

          for (i = 0, k = 0; i < 2; i++)
            for (j = 0; j < 2; j++, k++)
              g_ascii_dtostr (buf[k], G_ASCII_DTOSTR_BUF_SIZE,
                              trafo->coeff[i][j]);

          g_string_append_printf (str, "(matrix %s %s %s %s)",
                                  buf[0], buf[1], buf[2], buf[3]);
        }
      else
        {
          g_string_append (str, "(matrix 1.0 1.0 1.0 1.0)");
        }

      return TRUE;
    }

  if (G_VALUE_TYPE (value) == GIMP_TYPE_VALUE_ARRAY)
    {
      GimpValueArray *array;

      array = g_value_get_boxed (value);

      if (array)
        {
          gint length = gimp_value_array_length (array);
          gint i;

          g_string_append_printf (str, "%d", length);

          for (i = 0; i < length; i++)
            {
              g_string_append (str, " ");

              if (! gimp_config_serialize_value (gimp_value_array_index (array,
                                                                         i),
                                                 str, TRUE))
                return FALSE;
            }
        }
      else
        {
          g_string_append (str, "0");
        }

      return TRUE;
    }

  if (G_VALUE_TYPE (value) == G_TYPE_FILE)
    {
      GFile *file = g_value_get_object (value);

      if (file)
        {
          gchar *path     = g_file_get_path (file);
          gchar *unexpand = NULL;

          if (path)
            {
              unexpand = gimp_config_path_unexpand (path, TRUE, NULL);
              g_free (path);
            }

          if (unexpand)
            {
              gchar *full_uri;
              gchar *scheme = g_file_get_uri_scheme (file);

              full_uri = g_strconcat (scheme, ":///", unexpand, NULL);
              g_free (scheme);
              g_free (unexpand);

              if (escaped)
                gimp_config_string_append_escaped (str, full_uri);
              else
                g_string_append (str, full_uri);

              g_free (full_uri);
            }
          else
            {
              gchar *uri = g_file_get_uri (file);

              if (uri)
                {
                  if (escaped)
                    gimp_config_string_append_escaped (str, uri);
                  else
                    g_string_append (str, uri);

                  g_free (uri);
                }
              else
                {
                  g_string_append (str, "NULL");
                }
            }
        }
      else
        {
          g_string_append (str, "NULL");
        }

      return TRUE;
    }

  if (g_value_type_transformable (G_VALUE_TYPE (value), G_TYPE_STRING))
    {
      GValue  tmp_value = G_VALUE_INIT;

      g_value_init (&tmp_value, G_TYPE_STRING);
      g_value_transform (value, &tmp_value);

      g_string_append (str, g_value_get_string (&tmp_value));

      g_value_unset (&tmp_value);
      return TRUE;
    }

  return FALSE;
}


/* Private functions */

/**
 * gimp_config_serialize_strv:
 * @value: source #GValue holding a #GStrv
 * @str:   destination string
 *
 * Appends a string repr of the #GStrv value of #GValue to @str.
 * Repr is an integer literal greater than or equal to zero,
 * followed by a possibly empty sequence
 * of quoted and escaped string literals.
 *
 * Returns: %TRUE always
 *
 * Since: 3.0
 **/
static gboolean
gimp_config_serialize_strv (const GValue *value,
                            GString      *str)
{
  GStrv gstrv;

  gstrv = g_value_get_boxed (value);

  if (gstrv)
    {
      gint length = g_strv_length (gstrv);

      /* Write length */
      g_string_append_printf (str, "%d", length);

      for (gint i = 0; i < length; i++)
        {
          g_string_append (str, " "); /* separator */
          gimp_config_string_append_escaped (str, gstrv[i]);
        }
    }
  else
    {
      /* GValue has NULL value. Not quite the same as an empty GStrv.
       * But handle it quietly as an empty GStrv: write a length of zero.
       */
      g_string_append (str, "0");
    }

  return TRUE;
}

static gboolean
gimp_config_serialize_array (const GValue *value,
                             GString      *str)
{
  GimpArray *array;

  g_return_val_if_fail (GIMP_VALUE_HOLDS_INT32_ARRAY (value) ||
                        GIMP_VALUE_HOLDS_DOUBLE_ARRAY (value), FALSE);

  array = g_value_get_boxed (value);

  if (array)
    {
      gint32 *values = (gint32 *) array->data;
      gint    length;

      if (GIMP_VALUE_HOLDS_INT32_ARRAY (value))
        length = array->length / sizeof (gint32);
      else
        length = array->length / sizeof (gdouble);

      /* Write length */
      g_string_append_printf (str, "%d", length);

      for (gint i = 0; i < length; i++)
        {
          gchar *num_str;

          if (GIMP_VALUE_HOLDS_INT32_ARRAY (value))
            {
              num_str = g_strdup_printf (" %d", values[i]);
            }
          else
            {
              gchar buf[G_ASCII_DTOSTR_BUF_SIZE];

              g_ascii_dtostr (buf, sizeof (buf), ((gdouble *) values)[i]);
              num_str = g_strdup_printf (" %s", buf);
            }

          g_string_append (str, num_str);
          g_free (num_str);
        }
    }
  else
    {
      g_string_append (str, "0");
    }

  return TRUE;
}

/* --- end libammoos/config/fieldconfig/gimpconfig-serialize.c --- */

/* --- begin libammoos/config/fieldconfig/gimpconfig-utils.c --- */
/* LIBGIMP - The AmmoOS Image Library
 * Copyright (C) 1995-1997 Spencer Kimball and Peter Mattis
 *
 * Utility functions for GimpConfig.
 * Copyright (C) 2001-2003  Sven Neumann <sven@ammoos.org>
 *
 * This library is free software: you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 3 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Library General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library.  If not, see
 * <https://www.gnu.org/licenses/>.
 */

#include "config.h"

#include <cairo.h>
#include <gdk-pixbuf/gdk-pixbuf.h>
#include <gio/gio.h>

#include "libgimpbase/gimpbase.h"
#include "libgimpcolor/gimpcolor.h"

#include "gimpconfigtypes.h"

#include "gimpconfigwriter.h"
#include "gimpconfig-iface.h"
#include "gimpconfig-params.h"
#include "gimpconfig-utils.h"


/**
 * SECTION: gimpconfig-utils
 * @title: GimpConfig-utils
 * @short_description: Miscellaneous utility functions for libgimpconfig.
 *
 * Miscellaneous utility functions for libgimpconfig.
 **/


static gboolean
gimp_config_diff_property (GObject    *a,
                           GObject    *b,
                           GParamSpec *prop_spec)
{
  GValue    a_value = G_VALUE_INIT;
  GValue    b_value = G_VALUE_INIT;
  gboolean  retval  = FALSE;

  g_value_init (&a_value, prop_spec->value_type);
  g_value_init (&b_value, prop_spec->value_type);

  g_object_get_property (a, prop_spec->name, &a_value);
  g_object_get_property (b, prop_spec->name, &b_value);

  /* TODO: temporary hack to handle case of NULL GeglColor in a param value.
   * This got fixed in commit c0477bcb0 which should be available for GEGL
   * 0.4.50. In the meantime, this will do.
   */
  if (GEGL_IS_PARAM_SPEC_COLOR (prop_spec) &&
      (! g_value_get_object (&a_value) ||
       ! g_value_get_object (&b_value)))
    {
      retval = (g_value_get_object (&a_value) != g_value_get_object (&b_value));
    }
  else if (g_param_values_cmp (prop_spec, &a_value, &b_value))
    {
      if ((prop_spec->flags & GIMP_CONFIG_PARAM_AGGREGATE) &&
          G_IS_PARAM_SPEC_OBJECT (prop_spec)               &&
          g_type_interface_peek (g_type_class_peek (prop_spec->value_type),
                                 GIMP_TYPE_CONFIG))
        {
          if (! gimp_config_is_equal_to (g_value_get_object (&a_value),
                                         g_value_get_object (&b_value)))
            {
              retval = TRUE;
            }
        }
      else
        {
          retval = TRUE;
        }
    }

  g_value_unset (&a_value);
  g_value_unset (&b_value);

  return retval;
}

static GList *
gimp_config_diff_same (GObject     *a,
                       GObject     *b,
                       GParamFlags  flags)
{
  GParamSpec **param_specs;
  guint        n_param_specs;
  guint        i;
  GList       *list = NULL;

  param_specs = g_object_class_list_properties (G_OBJECT_GET_CLASS (a),
                                                &n_param_specs);

  for (i = 0; i < n_param_specs; i++)
    {
      GParamSpec *prop_spec = param_specs[i];

      if (! flags || ((prop_spec->flags & flags) == flags))
        {
          if (gimp_config_diff_property (a, b, prop_spec))
            list = g_list_prepend (list, prop_spec);
        }
    }

  g_free (param_specs);

  return list;
}

static GList *
gimp_config_diff_other (GObject     *a,
                        GObject     *b,
                        GParamFlags  flags)
{
  GParamSpec **param_specs;
  guint        n_param_specs;
  guint        i;
  GList       *list = NULL;

  param_specs = g_object_class_list_properties (G_OBJECT_GET_CLASS (a),
                                                &n_param_specs);

  for (i = 0; i < n_param_specs; i++)
    {
      GParamSpec *a_spec = param_specs[i];
      GParamSpec *b_spec = g_object_class_find_property (G_OBJECT_GET_CLASS (b),
                                                         a_spec->name);

      if (b_spec &&
          (a_spec->value_type == b_spec->value_type) &&
          (! flags || (a_spec->flags & b_spec->flags & flags) == flags))
        {
          if (gimp_config_diff_property (a, b, b_spec))
            list = g_list_prepend (list, b_spec);
        }
    }

  g_free (param_specs);

  return list;
}


/**
 * gimp_config_diff:
 * @a: a #GObject
 * @b: another #GObject object
 * @flags: a mask of GParamFlags
 *
 * Compares all properties of @a and @b that have all @flags set. If
 * @flags is 0, all properties are compared.
 *
 * If the two objects are not of the same type, only properties that
 * exist in both object classes and are of the same value_type are
 * compared.
 *
 * Returns: (transfer container) (element-type GParamSpec): a GList of differing GParamSpecs.
 *
 * Since: 2.4
 **/
GList *
gimp_config_diff (GObject     *a,
                  GObject     *b,
                  GParamFlags  flags)
{
  GList *diff;

  g_return_val_if_fail (G_IS_OBJECT (a), NULL);
  g_return_val_if_fail (G_IS_OBJECT (b), NULL);

  if (G_TYPE_FROM_INSTANCE (a) == G_TYPE_FROM_INSTANCE (b))
    diff = gimp_config_diff_same (a, b, flags);
  else
    diff = gimp_config_diff_other (a, b, flags);

  return g_list_reverse (diff);
}

/**
 * gimp_config_sync:
 * @src: a #GObject
 * @dest: another #GObject
 * @flags: a mask of GParamFlags
 *
 * Compares all read- and write-able properties from @src and @dest
 * that have all @flags set. Differing values are then copied from
 * @src to @dest. If @flags is 0, all differing read/write properties.
 *
 * Properties marked as "construct-only" are not touched.
 *
 * If the two objects are not of the same type, only properties that
 * exist in both object classes and are of the same value_type are
 * synchronized
 *
 * Returns: %TRUE if @dest was modified, %FALSE otherwise
 *
 * Since: 2.4
 **/
gboolean
gimp_config_sync (GObject     *src,
                  GObject     *dest,
                  GParamFlags  flags)
{
  GList *diff;
  GList *list;

  g_return_val_if_fail (G_IS_OBJECT (src), FALSE);
  g_return_val_if_fail (G_IS_OBJECT (dest), FALSE);

  /* we use the internal versions here for a number of reasons:
   *  - it saves a g_list_reverse()
   *  - it avoids duplicated parameter checks
   */
  if (G_TYPE_FROM_INSTANCE (src) == G_TYPE_FROM_INSTANCE (dest))
    diff = gimp_config_diff_same (src, dest, (flags | G_PARAM_READWRITE));
  else
    diff = gimp_config_diff_other (src, dest, flags);

  if (!diff)
    return FALSE;

  g_object_freeze_notify (G_OBJECT (dest));

  for (list = diff; list; list = list->next)
    {
      GParamSpec *prop_spec = list->data;

      if (! (prop_spec->flags & G_PARAM_CONSTRUCT_ONLY))
        {
          GValue value = G_VALUE_INIT;

          g_value_init (&value, prop_spec->value_type);

          g_object_get_property (src,  prop_spec->name, &value);
          g_object_set_property (dest, prop_spec->name, &value);

          g_value_unset (&value);
        }
    }

  g_object_thaw_notify (G_OBJECT (dest));

  g_list_free (diff);

  return TRUE;
}

/**
 * gimp_config_reset_properties:
 * @object: a #GObject
 *
 * Resets all writable properties of @object to the default values as
 * defined in their #GParamSpec. Properties marked as "construct-only"
 * are not touched.
 *
 * If you want to reset a #GimpConfig object, please use gimp_config_reset().
 *
 * Since: 2.4
 **/
void
gimp_config_reset_properties (GObject *object)
{
  GObjectClass  *klass;
  GParamSpec   **property_specs;
  guint          n_property_specs;
  guint          i;

  g_return_if_fail (G_IS_OBJECT (object));

  klass = G_OBJECT_GET_CLASS (object);

  property_specs = g_object_class_list_properties (klass, &n_property_specs);
  if (!property_specs)
    return;

  g_object_freeze_notify (object);

  for (i = 0; i < n_property_specs; i++)
    {
      GParamSpec *prop_spec;
      GValue      value = G_VALUE_INIT;

      prop_spec = property_specs[i];

      if ((prop_spec->flags & G_PARAM_WRITABLE) &&
          ! (prop_spec->flags & G_PARAM_CONSTRUCT_ONLY))
        {
          if (G_IS_PARAM_SPEC_OBJECT (prop_spec)        &&
              ! GIMP_IS_PARAM_SPEC_OBJECT (prop_spec)   &&
              g_type_class_peek (prop_spec->value_type) &&
              g_type_interface_peek (g_type_class_peek (prop_spec->value_type),
                                     GIMP_TYPE_CONFIG))
            {
              if ((prop_spec->flags & GIMP_CONFIG_PARAM_SERIALIZE) &&
                  (prop_spec->flags & GIMP_CONFIG_PARAM_AGGREGATE))
                {
                  g_value_init (&value, prop_spec->value_type);

                  g_object_get_property (object, prop_spec->name, &value);

                  gimp_config_reset (g_value_get_object (&value));

                  g_value_unset (&value);
                }
            }
          else
            {
              GValue default_value = G_VALUE_INIT;

              g_value_init (&default_value, prop_spec->value_type);
              g_value_init (&value,         prop_spec->value_type);

              g_param_value_set_default (prop_spec, &default_value);
              g_object_get_property (object, prop_spec->name, &value);

              if (g_param_values_cmp (prop_spec, &default_value, &value))
                {
                  g_object_set_property (object, prop_spec->name,
                                         &default_value);
                }

              g_value_unset (&value);
              g_value_unset (&default_value);
            }
        }
    }

  g_object_thaw_notify (object);

  g_free (property_specs);
}


/**
 * gimp_config_reset_property:
 * @object: a #GObject
 * @property_name: name of the property to reset
 *
 * Resets the property named @property_name to its default value.  The
 * property must be writable and must not be marked as "construct-only".
 *
 * Since: 2.4
 **/
void
gimp_config_reset_property (GObject     *object,
                            const gchar *property_name)
{
  GObjectClass  *klass;
  GParamSpec    *prop_spec;

  g_return_if_fail (G_IS_OBJECT (object));
  g_return_if_fail (property_name != NULL);

  klass = G_OBJECT_GET_CLASS (object);

  prop_spec = g_object_class_find_property (klass, property_name);

  if (!prop_spec)
    return;

  if ((prop_spec->flags & G_PARAM_WRITABLE) &&
      ! (prop_spec->flags & G_PARAM_CONSTRUCT_ONLY))
    {
      GValue  value = G_VALUE_INIT;

      if (G_IS_PARAM_SPEC_OBJECT (prop_spec))
        {
          if ((prop_spec->flags & GIMP_CONFIG_PARAM_SERIALIZE) &&
              (prop_spec->flags & GIMP_CONFIG_PARAM_AGGREGATE) &&
              g_type_interface_peek (g_type_class_peek (prop_spec->value_type),
                                     GIMP_TYPE_CONFIG))
            {
              g_value_init (&value, prop_spec->value_type);

              g_object_get_property (object, prop_spec->name, &value);

              gimp_config_reset (g_value_get_object (&value));

              g_value_unset (&value);
            }
        }
      else
        {
          g_value_init (&value, prop_spec->value_type);
          g_param_value_set_default (prop_spec, &value);

          g_object_set_property (object, prop_spec->name, &value);

          g_value_unset (&value);
        }
    }
}


/*
 * GimpConfig string utilities
 */

/**
 * gimp_config_string_append_escaped:
 * @string: pointer to a #GString
 * @val: a string to append or %NULL
 *
 * Escapes and quotes @val and appends it to @string. The escape
 * algorithm is different from the one used by g_strescape() since it
 * leaves non-ASCII characters intact and thus preserves UTF-8
 * strings. Only control characters and quotes are being escaped.
 *
 * Since: 2.4
 **/
void
gimp_config_string_append_escaped (GString     *string,
                                   const gchar *val)
{
  g_return_if_fail (string != NULL);

  if (val)
    {
      const guchar *p;
      gchar         buf[4] = { '\\', 0, 0, 0 };
      gint          len;

      g_string_append_c (string, '\"');

      for (p = (const guchar *) val, len = 0; *p; p++)
        {
          if (*p < ' ' || *p == '\\' || *p == '\"')
            {
              g_string_append_len (string, val, len);

              len = 2;
              switch (*p)
                {
                case '\b':
                  buf[1] = 'b';
                  break;
                case '\f':
                  buf[1] = 'f';
                  break;
                case '\n':
                  buf[1] = 'n';
                  break;
                case '\r':
                  buf[1] = 'r';
                  break;
                case '\t':
                  buf[1] = 't';
                  break;
                case '\\':
                case '"':
                  buf[1] = *p;
                  break;

                default:
                  len = 4;
                  buf[1] = '0' + (((*p) >> 6) & 07);
                  buf[2] = '0' + (((*p) >> 3) & 07);
                  buf[3] = '0' + ((*p) & 07);
                  break;
                }

              g_string_append_len (string, buf, len);

              val = (const gchar *) p + 1;
              len = 0;
            }
          else
            {
              len++;
            }
        }

      g_string_append_len (string, val, len);
      g_string_append_c   (string, '\"');
    }
  else
    {
      g_string_append_len (string, "\"\"", 2);
    }
}

/* --- end libammoos/config/fieldconfig/gimpconfig-utils.c --- */

/* --- begin libammoos/config/fieldconfig/gimpconfigenums.c --- */

/* Generated data (by ammoos-mkenums) */

#include "stamp-gimpconfigenums.h"
#include "config.h"
#include <gio/gio.h>
#include "libgimpbase/gimpbase.h"
#include "gimpconfigenums.h"
#include "libgimp/libgimp-intl.h"

/* enumerations from "gimpconfigenums.h" */
GType
gimp_color_management_mode_get_type (void)
{
  static const GEnumValue values[] =
  {
    { GIMP_COLOR_MANAGEMENT_OFF, "GIMP_COLOR_MANAGEMENT_OFF", "off" },
    { GIMP_COLOR_MANAGEMENT_DISPLAY, "GIMP_COLOR_MANAGEMENT_DISPLAY", "display" },
    { GIMP_COLOR_MANAGEMENT_SOFTPROOF, "GIMP_COLOR_MANAGEMENT_SOFTPROOF", "softproof" },
    { 0, NULL, NULL }
  };

  static const GimpEnumDesc descs[] =
  {
    { GIMP_COLOR_MANAGEMENT_OFF, NC_("color-management-mode", "No color management"), NULL },
    { GIMP_COLOR_MANAGEMENT_DISPLAY, NC_("color-management-mode", "Color-managed display"), NULL },
    { GIMP_COLOR_MANAGEMENT_SOFTPROOF, NC_("color-management-mode", "Soft-proofing"), NULL },
    { 0, NULL, NULL }
  };

  static GType type = 0;

  if (G_UNLIKELY (! type))
    {
      type = g_enum_register_static ("GimpColorManagementMode", values);
      gimp_type_set_translation_domain (type, GETTEXT_PACKAGE "-libgimp");
      gimp_type_set_translation_context (type, "color-management-mode");
      gimp_enum_set_value_descriptions (type, descs);
    }

  return type;
}

GType
gimp_color_rendering_intent_get_type (void)
{
  static const GEnumValue values[] =
  {
    { GIMP_COLOR_RENDERING_INTENT_PERCEPTUAL, "GIMP_COLOR_RENDERING_INTENT_PERCEPTUAL", "perceptual" },
    { GIMP_COLOR_RENDERING_INTENT_RELATIVE_COLORIMETRIC, "GIMP_COLOR_RENDERING_INTENT_RELATIVE_COLORIMETRIC", "relative-colorimetric" },
    { GIMP_COLOR_RENDERING_INTENT_SATURATION, "GIMP_COLOR_RENDERING_INTENT_SATURATION", "saturation" },
    { GIMP_COLOR_RENDERING_INTENT_ABSOLUTE_COLORIMETRIC, "GIMP_COLOR_RENDERING_INTENT_ABSOLUTE_COLORIMETRIC", "absolute-colorimetric" },
    { 0, NULL, NULL }
  };

  static const GimpEnumDesc descs[] =
  {
    { GIMP_COLOR_RENDERING_INTENT_PERCEPTUAL, NC_("color-rendering-intent", "Perceptual"), NULL },
    { GIMP_COLOR_RENDERING_INTENT_RELATIVE_COLORIMETRIC, NC_("color-rendering-intent", "Relative colorimetric"), NULL },
    { GIMP_COLOR_RENDERING_INTENT_SATURATION, NC_("color-rendering-intent", "Saturation"), NULL },
    { GIMP_COLOR_RENDERING_INTENT_ABSOLUTE_COLORIMETRIC, NC_("color-rendering-intent", "Absolute colorimetric"), NULL },
    { 0, NULL, NULL }
  };

  static GType type = 0;

  if (G_UNLIKELY (! type))
    {
      type = g_enum_register_static ("GimpColorRenderingIntent", values);
      gimp_type_set_translation_domain (type, GETTEXT_PACKAGE "-libgimp");
      gimp_type_set_translation_context (type, "color-rendering-intent");
      gimp_enum_set_value_descriptions (type, descs);
    }

  return type;
}


/* Generated data ends here */


/* --- end libammoos/config/fieldconfig/gimpconfigenums.c --- */

/* --- begin libammoos/config/fieldconfig/gimpconfigwriter.c --- */
/* LIBGIMP - The AmmoOS Image Library
 * Copyright (C) 1995 Spencer Kimball and Peter Mattis
 *
 * GimpConfigWriter
 * Copyright (C) 2003  Sven Neumann <sven@ammoos.org>
 *
 * This library is free software: you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 3 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Library General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library.  If not, see
 * <https://www.gnu.org/licenses/>.
 */

#include "config.h"

#include <string.h>

#include <gio/gio.h>

#ifdef G_OS_WIN32
#include <gio/gwin32outputstream.h>
#else
#include <gio/gunixoutputstream.h>
#endif

#include "libgimpbase/gimpbase.h"

#include "gimpconfigtypes.h"

#include "gimpconfigwriter.h"
#include "gimpconfig-iface.h"
#include "gimpconfig-error.h"
#include "gimpconfig-serialize.h"
#include "gimpconfig-utils.h"

#include "libgimp/libgimp-intl.h"


/**
 * SECTION: gimpconfigwriter
 * @title: GimpConfigWriter
 * @short_description: Functions for writing config info to a file for
 *                     libgimpconfig.
 *
 * Functions for writing config info to a file for libgimpconfig.
 **/


struct _GimpConfigWriter
{
  gint           ref_count;
  gboolean       finished;

  GOutputStream *output;
  GFile         *file;
  GError        *error;
  GString       *buffer;
  gboolean       comment;
  gint           depth;
  gint           marker;
};


G_DEFINE_BOXED_TYPE (GimpConfigWriter, gimp_config_writer,
                     gimp_config_writer_ref, gimp_config_writer_unref)


static inline void  gimp_config_writer_flush        (GimpConfigWriter  *writer);
static inline void  gimp_config_writer_newline      (GimpConfigWriter  *writer);
static gboolean     gimp_config_writer_close_output (GimpConfigWriter  *writer,
                                                     GError           **error);

static inline void
gimp_config_writer_flush (GimpConfigWriter *writer)
{
  GError *error = NULL;

  if (! writer->output)
    return;

  if (! g_output_stream_write_all (writer->output,
                                   writer->buffer->str,
                                   writer->buffer->len,
                                   NULL, NULL, &error))
    {
      g_set_error (&writer->error, GIMP_CONFIG_ERROR, GIMP_CONFIG_ERROR_WRITE,
                   _("Error writing to '%s': %s"),
                   writer->file ?
                   gimp_file_get_utf8_name (writer->file) : "output stream",
                   error->message);
      g_clear_error (&error);
    }

  g_string_truncate (writer->buffer, 0);
}

static inline void
gimp_config_writer_newline (GimpConfigWriter *writer)
{
  gint i;

  g_string_append_c (writer->buffer, '\n');

  if (writer->comment)
    g_string_append_len (writer->buffer, "# ", 2);

  for (i = 0; i < writer->depth; i++)
    g_string_append_len (writer->buffer, "    ", 4);
}

/**
 * gimp_config_writer_new_from_file:
 * @file: a #GFile
 * @atomic: if %TRUE the file is written atomically
 * @header: text to include as comment at the top of the file
 * @error: return location for errors
 *
 * Creates a new #GimpConfigWriter and sets it up to write to
 * @file. If @atomic is %TRUE, a temporary file is used to avoid
 * possible race conditions. The temporary file is then moved to @file
 * when the writer is closed.
 *
 * Returns: (nullable): a new #GimpConfigWriter or %NULL in case of an error
 *
 * Since: 2.10
 **/
GimpConfigWriter *
gimp_config_writer_new_from_file (GFile        *file,
                                  gboolean      atomic,
                                  const gchar  *header,
                                  GError      **error)
{
  GimpConfigWriter *writer;
  GOutputStream    *output;
  GFile            *dir;

  g_return_val_if_fail (G_IS_FILE (file), NULL);
  g_return_val_if_fail (error == NULL || *error == NULL, NULL);

  dir = g_file_get_parent (file);
  if (dir && ! g_file_query_exists (dir, NULL))
    {
      if (! g_file_make_directory_with_parents (dir, NULL, error))
        g_prefix_error (error,
                        _("Could not create directory '%s' for '%s': "),
                        gimp_file_get_utf8_name (dir),
                        gimp_file_get_utf8_name (file));
    }
  g_object_unref (dir);

  if (error && *error)
    return NULL;

  if (atomic)
    {
      output = G_OUTPUT_STREAM (g_file_replace (file,
                                                NULL, FALSE, G_FILE_CREATE_NONE,
                                                NULL, error));
      if (! output)
        g_prefix_error (error,
                        _("Could not create temporary file for '%s': "),
                        gimp_file_get_utf8_name (file));
    }
  else
    {
      output = G_OUTPUT_STREAM (g_file_replace (file,
                                                NULL, FALSE,
                                                G_FILE_CREATE_REPLACE_DESTINATION,
                                                NULL, error));
    }

  if (! output)
    return NULL;

  writer = g_slice_new0 (GimpConfigWriter);

  writer->ref_count = 1;
  writer->output    = output;
  writer->file      = g_object_ref (file);
  writer->buffer    = g_string_new (NULL);

  if (header)
    {
      gimp_config_writer_comment (writer, header);
      gimp_config_writer_linefeed (writer);
    }

  return writer;
}

/**
 * gimp_config_writer_new_from_stream:
 * @output: a #GOutputStream
 * @header: text to include as comment at the top of the file
 * @error: return location for errors
 *
 * Creates a new #GimpConfigWriter and sets it up to write to
 * @output.
 *
 * Returns: (nullable): a new #GimpConfigWriter or %NULL in case of an error
 *
 * Since: 2.10
 **/
GimpConfigWriter *
gimp_config_writer_new_from_stream (GOutputStream  *output,
                                    const gchar    *header,
                                    GError        **error)
{
  GimpConfigWriter *writer;

  g_return_val_if_fail (G_IS_OUTPUT_STREAM (output), NULL);
  g_return_val_if_fail (error == NULL || *error == NULL, NULL);

  writer = g_slice_new0 (GimpConfigWriter);

  writer->ref_count = 1;
  writer->output    = g_object_ref (output);
  writer->buffer    = g_string_new (NULL);

  if (header)
    {
      gimp_config_writer_comment (writer, header);
      gimp_config_writer_linefeed (writer);
    }

  return writer;
}

/**
 * gimp_config_writer_new_from_fd:
 * @fd:
 *
 * Returns: (nullable): a new #GimpConfigWriter or %NULL in case of an error
 *
 * Since: 2.4
 **/
GimpConfigWriter *
gimp_config_writer_new_from_fd (gint fd)
{
  GimpConfigWriter *writer;

  g_return_val_if_fail (fd > 0, NULL);

  writer = g_slice_new0 (GimpConfigWriter);

  writer->ref_count = 1;

#ifdef G_OS_WIN32
  writer->output = g_win32_output_stream_new ((gpointer) (intptr_t) fd, FALSE);
#else
  writer->output = g_unix_output_stream_new (fd, FALSE);
#endif

  writer->buffer = g_string_new (NULL);

  return writer;
}

/**
 * gimp_config_writer_new_from_string:
 * @string:
 *
 * Returns: (nullable): a new #GimpConfigWriter or %NULL in case of an error
 *
 * Since: 2.4
 **/
GimpConfigWriter *
gimp_config_writer_new_from_string (GString *string)
{
  GimpConfigWriter *writer;

  g_return_val_if_fail (string != NULL, NULL);

  writer = g_slice_new0 (GimpConfigWriter);

  writer->ref_count = 1;
  writer->buffer    = string;

  return writer;
}

/**
 * gimp_config_writer_ref:
 * @writer: #GimpConfigWriter to ref
 *
 * Adds a reference to a #GimpConfigWriter.
 *
 * Returns: the same @writer.
 *
 * Since: 3.0
 */
GimpConfigWriter *
gimp_config_writer_ref (GimpConfigWriter *writer)
{
  g_return_val_if_fail (writer != NULL, NULL);

  writer->ref_count++;

  return writer;
}

/**
 * gimp_config_writer_unref:
 * @writer: #GimpConfigWriter to unref
 *
 * Unref a #GimpConfigWriter. If the reference count drops to zero, the
 * writer is freed.
 *
 * Note that at least one of the references has to be dropped using
 * gimp_config_writer_finish().
 *
 * Since: 3.0
 */
void
gimp_config_writer_unref (GimpConfigWriter *writer)
{
  g_return_if_fail (writer != NULL);

  writer->ref_count--;

  if (writer->ref_count < 1)
    {
      if (! writer->finished)
        {
          GError *error = NULL;

          g_printerr ("%s: dropping last reference via unref(), you should "
                      "call gimp_config_writer_finish()\n", G_STRFUNC);

          if (! gimp_config_writer_finish (writer, NULL, &error))
            {
              g_printerr ("%s: error on finishing writer: %s\n",
                          G_STRFUNC, error->message);
            }
        }
      else
        {
          g_slice_free (GimpConfigWriter, writer);
        }
    }
}

/**
 * gimp_config_writer_comment_mode:
 * @writer: a #GimpConfigWriter
 * @enable: %TRUE to enable comment mode, %FALSE to disable it
 *
 * This function toggles whether the @writer should create commented
 * or uncommented output. This feature is used to generate the
 * system-wide installed gimprc that documents the default settings.
 *
 * Since comments have to start at the beginning of a line, this
 * function will insert a newline if necessary.
 *
 * Since: 2.4
 **/
void
gimp_config_writer_comment_mode (GimpConfigWriter *writer,
                                 gboolean          enable)
{
  g_return_if_fail (writer != NULL);
  g_return_if_fail (writer->finished == FALSE);

  if (writer->error)
    return;

  enable = (enable ? TRUE : FALSE);

  if (writer->comment == enable)
    return;

  writer->comment = enable;

  if (enable)
    {
     if (writer->buffer->len == 0)
       g_string_append_len (writer->buffer, "# ", 2);
     else
       gimp_config_writer_newline (writer);
    }
}


/**
 * gimp_config_writer_open:
 * @writer: a #GimpConfigWriter
 * @name: name of the element to open
 *
 * This function writes the opening parenthesis followed by @name.
 * It also increases the indentation level and sets a mark that
 * can be used by gimp_config_writer_revert().
 *
 * Since: 2.4
 **/
void
gimp_config_writer_open (GimpConfigWriter *writer,
                         const gchar      *name)
{
  g_return_if_fail (writer != NULL);
  g_return_if_fail (writer->finished == FALSE);
  g_return_if_fail (name != NULL);

  if (writer->error)
    return;

  /* store the current buffer length so we can revert to this state */
  writer->marker = writer->buffer->len;

  if (writer->depth > 0)
    gimp_config_writer_newline (writer);

  writer->depth++;

  g_string_append_printf (writer->buffer, "(%s", name);
}

/**
 * gimp_config_writer_print:
 * @writer: a #GimpConfigWriter
 * @string: a string to write
 * @len: number of bytes from @string or -1 if @string is NUL-terminated.
 *
 * Appends a space followed by @string to the @writer. Note that string
 * must not contain any special characters that might need to be escaped.
 *
 * Since: 2.4
 **/
void
gimp_config_writer_print (GimpConfigWriter  *writer,
                          const gchar       *string,
                          gint               len)
{
  g_return_if_fail (writer != NULL);
  g_return_if_fail (writer->finished == FALSE);
  g_return_if_fail (len == 0 || string != NULL);

  if (writer->error)
    return;

  if (len < 0)
    len = strlen (string);

  if (len)
    {
      g_string_append_c (writer->buffer, ' ');
      g_string_append_len (writer->buffer, string, len);
    }
}

/**
 * gimp_config_writer_printf: (skip)
 * @writer: a #GimpConfigWriter
 * @format: a format string as described for g_strdup_printf().
 * @...: list of arguments according to @format
 *
 * A printf-like function for #GimpConfigWriter.
 *
 * Since: 2.4
 **/
void
gimp_config_writer_printf (GimpConfigWriter *writer,
                           const gchar      *format,
                           ...)
{
  gchar   *buffer;
  va_list  args;

  g_return_if_fail (writer != NULL);
  g_return_if_fail (writer->finished == FALSE);
  g_return_if_fail (format != NULL);

  if (writer->error)
    return;

  va_start (args, format);
  buffer = g_strdup_vprintf (format, args);
  va_end (args);

  g_string_append_c (writer->buffer, ' ');
  g_string_append (writer->buffer, buffer);

  g_free (buffer);
}

/**
 * gimp_config_writer_string:
 * @writer: a #GimpConfigWriter
 * @string: a NUL-terminated string
 *
 * Writes a string value to @writer. The @string is quoted and special
 * characters are escaped.
 *
 * Since: 2.4
 **/
void
gimp_config_writer_string (GimpConfigWriter *writer,
                           const gchar      *string)
{
  g_return_if_fail (writer != NULL);
  g_return_if_fail (writer->finished == FALSE);

  if (writer->error)
    return;

  g_string_append_c (writer->buffer, ' ');
  gimp_config_string_append_escaped (writer->buffer, string);
}

/**
 * gimp_config_writer_identifier:
 * @writer:     a #GimpConfigWriter
 * @identifier: a NUL-terminated string
 *
 * Writes an identifier to @writer. The @string is *not* quoted and special
 * characters are *not* escaped.
 *
 * Since: 2.4
 **/
void
gimp_config_writer_identifier (GimpConfigWriter *writer,
                               const gchar      *identifier)
{
  g_return_if_fail (writer != NULL);
  g_return_if_fail (writer->finished == FALSE);
  g_return_if_fail (identifier != NULL);

  if (writer->error)
    return;

  g_string_append_printf (writer->buffer, " %s", identifier);
}


/**
 * gimp_config_writer_data:
 * @writer: a #GimpConfigWriter
 * @length:                    : The size of @data
 * @data: (array length=length): The data to write
 *
 * Writes data to @writer.
 *
 * Since: 2.4
 **/
void
gimp_config_writer_data (GimpConfigWriter *writer,
                         gint              length,
                         const guint8     *data)
{
  gint i;

  g_return_if_fail (writer != NULL);
  g_return_if_fail (writer->finished == FALSE);
  g_return_if_fail (length >= 0);
  g_return_if_fail (data != NULL || length == 0);

  if (writer->error)
    return;

  g_string_append (writer->buffer, " \"");

  for (i = 0; i < length; i++)
    {
      if (g_ascii_isalpha (data[i]))
        g_string_append_c (writer->buffer, data[i]);
      else
        g_string_append_printf (writer->buffer, "\\%o", data[i]);
    }

  g_string_append (writer->buffer, "\"");
}

/**
 * gimp_config_writer_revert:
 * @writer: a #GimpConfigWriter
 *
 * Reverts all changes to @writer that were done since the last call
 * to gimp_config_writer_open(). This can only work if you didn't call
 * gimp_config_writer_close() yet.
 *
 * Since: 2.4
 **/
void
gimp_config_writer_revert (GimpConfigWriter *writer)
{
  g_return_if_fail (writer != NULL);
  g_return_if_fail (writer->finished == FALSE);

  if (writer->error)
    return;

  g_return_if_fail (writer->depth > 0);
  g_return_if_fail (writer->marker != -1);

  g_string_truncate (writer->buffer, writer->marker);

  writer->depth--;
  writer->marker = -1;
}

/**
 * gimp_config_writer_close:
 * @writer: a #GimpConfigWriter
 *
 * Closes an element opened with gimp_config_writer_open().
 *
 * Since: 2.4
 **/
void
gimp_config_writer_close (GimpConfigWriter *writer)
{
  g_return_if_fail (writer != NULL);
  g_return_if_fail (writer->finished == FALSE);

  if (writer->error)
    return;

  g_return_if_fail (writer->depth > 0);

  g_string_append_c (writer->buffer, ')');

  if (--writer->depth == 0)
    {
      g_string_append_c (writer->buffer, '\n');

      gimp_config_writer_flush (writer);
    }
}

/**
 * gimp_config_writer_finish:
 * @writer: a #GimpConfigWriter
 * @footer: text to include as comment at the bottom of the file
 * @error: return location for possible errors
 *
 * This function finishes the work of @writer and unrefs it
 * afterwards.  It closes all open elements, appends an optional
 * comment and releases all resources allocated by @writer.
 *
 * Using any function except gimp_config_writer_ref() or
 * gimp_config_writer_unref() after this function is forbidden
 * and will trigger warnings.
 *
 * Returns: %TRUE if everything could be successfully written,
 *          %FALSE otherwise
 *
 * Since: 2.4
 **/
gboolean
gimp_config_writer_finish (GimpConfigWriter  *writer,
                           const gchar       *footer,
                           GError           **error)
{
  gboolean success = TRUE;

  g_return_val_if_fail (writer != NULL, FALSE);
  g_return_val_if_fail (writer->finished == FALSE, FALSE);
  g_return_val_if_fail (error == NULL || *error == NULL, FALSE);

  if (writer->depth < 0)
    {
      g_warning ("gimp_config_writer_finish: depth < 0 !!");
    }
  else
    {
      while (writer->depth)
        gimp_config_writer_close (writer);
    }

  if (footer)
    {
      gimp_config_writer_linefeed (writer);
      gimp_config_writer_comment (writer, footer);
    }

  if (writer->output)
    {
      success = gimp_config_writer_close_output (writer, error);

      g_clear_object (&writer->file);

      g_string_free (writer->buffer, TRUE);
      writer->buffer = NULL;
    }

  if (writer->error)
    {
      if (error && *error == NULL)
        g_propagate_error (error, writer->error);
      else
        g_clear_error (&writer->error);

      success = FALSE;
    }

  writer->finished = TRUE;

  gimp_config_writer_unref (writer);

  return success;
}

void
gimp_config_writer_linefeed (GimpConfigWriter *writer)
{
  g_return_if_fail (writer != NULL);
  g_return_if_fail (writer->finished == FALSE);

  if (writer->error)
    return;

  if (writer->output && writer->buffer->len == 0 && !writer->comment)
    {
      GError *error = NULL;

      if (! g_output_stream_write_all (writer->output, "\n", 1,
                                       NULL, NULL, &error))
        {
          g_set_error (&writer->error, GIMP_CONFIG_ERROR, GIMP_CONFIG_ERROR_WRITE,
                       _("Error writing to '%s': %s"),
                       writer->file ?
                       gimp_file_get_utf8_name (writer->file) : "output stream",
                       error->message);
          g_clear_error (&error);
        }
    }
  else
    {
      gimp_config_writer_newline (writer);
    }
}

/**
 * gimp_config_writer_comment:
 * @writer: a #GimpConfigWriter
 * @comment: the comment to write (ASCII only)
 *
 * Appends the @comment to @str and inserts linebreaks and hash-marks to
 * format it as a comment. Note that this function does not handle non-ASCII
 * characters.
 *
 * Since: 2.4
 **/
void
gimp_config_writer_comment (GimpConfigWriter *writer,
                            const gchar      *comment)
{
  const gchar *s;
  gboolean     comment_mode;
  gint         i, len, space;

#define LINE_LENGTH 75

  g_return_if_fail (writer != NULL);
  g_return_if_fail (writer->finished == FALSE);

  if (writer->error)
    return;

  g_return_if_fail (writer->depth == 0);

  if (!comment)
    return;

  comment_mode = writer->comment;
  gimp_config_writer_comment_mode (writer, TRUE);

  len = strlen (comment);

  while (len > 0)
    {
      for (s = comment, i = 0, space = 0;
           *s != '\n' && (i <= LINE_LENGTH || space == 0) && i < len;
           s++, i++)
        {
          if (g_ascii_isspace (*s))
            space = i;
        }

      if (i > LINE_LENGTH && space && *s != '\n')
        i = space;

      g_string_append_len (writer->buffer, comment, i);

      i++;

      comment += i;
      len     -= i;

      if (len > 0)
        gimp_config_writer_newline (writer);
    }

  gimp_config_writer_comment_mode (writer, comment_mode);
  gimp_config_writer_newline (writer);

  if (writer->depth == 0)
    gimp_config_writer_flush (writer);

#undef LINE_LENGTH
}

static gboolean
gimp_config_writer_close_output (GimpConfigWriter  *writer,
                                 GError           **error)
{
  g_return_val_if_fail (writer->output != NULL, FALSE);

  if (writer->error)
    {
      GCancellable *cancellable = g_cancellable_new ();

      /* Cancel the overwrite initiated by g_file_replace(). */
      g_cancellable_cancel (cancellable);
      g_output_stream_close (writer->output, cancellable, NULL);
      g_object_unref (cancellable);

      g_clear_object (&writer->output);

      return FALSE;
    }

  if (writer->file)
    {
      GError *my_error = NULL;

      if (! g_output_stream_close (writer->output, NULL, &my_error))
        {
          g_set_error (error, GIMP_CONFIG_ERROR, GIMP_CONFIG_ERROR_WRITE,
                       _("Error writing '%s': %s"),
                       gimp_file_get_utf8_name (writer->file),
                       my_error->message);
          g_clear_error (&my_error);

          g_clear_object (&writer->output);

          return FALSE;
        }
    }

  g_clear_object (&writer->output);

  return TRUE;
}

/* --- end libammoos/config/fieldconfig/gimpconfigwriter.c --- */

/* --- begin libammoos/config/fieldconfig/gimpscanner.c --- */
/* LIBGIMP - The AmmoOS Image Library
 * Copyright (C) 1995 Spencer Kimball and Peter Mattis
 *
 * gimpscanner.c
 * Copyright (C) 2002  Sven Neumann <sven@ammoos.org>
 *                     Michael Natterer <mitch@ammoos.org>
 *
 * This library is free software: you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 3 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Library General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library.  If not, see
 * <https://www.gnu.org/licenses/>.
 */

#include "config.h"

#include <string.h>
#include <errno.h>

#include <cairo.h>
#include <gegl.h>
#include <gdk-pixbuf/gdk-pixbuf.h>

#include "libgimpbase/gimpbase.h"
#include "libgimpcolor/gimpcolor.h"
#include "libgimpmath/gimpmath.h"

#include "gimpconfig-error.h"
#include "gimpscanner.h"

#include "libgimp/libgimp-intl.h"


/**
 * SECTION: gimpscanner
 * @title: GimpScanner
 * @short_description: A wrapper around #GScanner with some convenience API.
 *
 * A wrapper around #GScanner with some convenience API.
 **/


typedef struct
{
  gint          ref_count;
  gchar        *name;
  GMappedFile  *mapped;
  gchar        *text;
  GError      **error;
} GimpScannerData;


G_DEFINE_BOXED_TYPE (GimpScanner, gimp_scanner,
                     gimp_scanner_ref, gimp_scanner_unref)



/*  local function prototypes  */

static GimpScanner * gimp_scanner_new                    (const gchar  *name,
                                                          GMappedFile  *mapped,
                                                          gchar        *text,
                                                          GError      **error);
static void          gimp_scanner_message                (GimpScanner  *scanner,
                                                          gchar        *message,
                                                          gboolean      is_error);
static GTokenType    gimp_scanner_parse_deprecated_color (GimpScanner  *scanner,
                                                          GeglColor   **color);


/*  public functions  */

/**
 * gimp_scanner_new_file:
 * @file: a #GFile
 * @error: return location for #GError, or %NULL
 *
 * Returns: (transfer full): The new #GimpScanner.
 *
 * Since: 2.10
 **/
GimpScanner *
gimp_scanner_new_file (GFile   *file,
                       GError **error)
{
  GimpScanner *scanner;
  gchar       *path;

  g_return_val_if_fail (G_IS_FILE (file), NULL);
  g_return_val_if_fail (error == NULL || *error == NULL, NULL);

  path = g_file_get_path (file);

  if (path)
    {
      GMappedFile *mapped;

      mapped = g_mapped_file_new (path, FALSE, error);
      g_free (path);

      if (! mapped)
        {
          if (error)
            {
              (*error)->domain = GIMP_CONFIG_ERROR;
              (*error)->code   = ((*error)->code == G_FILE_ERROR_NOENT ?
                                  GIMP_CONFIG_ERROR_OPEN_ENOENT :
                                  GIMP_CONFIG_ERROR_OPEN);
            }

          return NULL;
        }

      /*  gimp_scanner_new() takes a "name" for the scanner, not a filename  */
      scanner = gimp_scanner_new (gimp_file_get_utf8_name (file),
                                  mapped, NULL, error);

      g_scanner_input_text (scanner,
                            g_mapped_file_get_contents (mapped),
                            g_mapped_file_get_length (mapped));
    }
  else
    {
      GInputStream *input;

      input = G_INPUT_STREAM (g_file_read (file, NULL, error));

      if (! input)
        {
          if (error)
            {
              (*error)->domain = GIMP_CONFIG_ERROR;
              (*error)->code   = ((*error)->code == G_IO_ERROR_NOT_FOUND ?
                                  GIMP_CONFIG_ERROR_OPEN_ENOENT :
                                  GIMP_CONFIG_ERROR_OPEN);
            }

          return NULL;
        }

      g_object_set_data (G_OBJECT (input), "ammoos-data", file);

      scanner = gimp_scanner_new_stream (input, error);

      g_object_unref (input);
    }

  return scanner;
}

/**
 * gimp_scanner_new_stream:
 * @input: a #GInputStream
 * @error: return location for #GError, or %NULL
 *
 * Returns: (transfer full): The new #GimpScanner.
 *
 * Since: 2.10
 **/
GimpScanner *
gimp_scanner_new_stream (GInputStream  *input,
                         GError       **error)
{
  GimpScanner *scanner;
  GFile       *file;
  const gchar *path;
  GString     *string;
  gchar        buffer[4096];
  gsize        bytes_read;

  g_return_val_if_fail (G_IS_INPUT_STREAM (input), NULL);
  g_return_val_if_fail (error == NULL || *error == NULL, NULL);

  file = g_object_get_data (G_OBJECT (input), "ammoos-file");
  if (file)
    path = gimp_file_get_utf8_name (file);
  else
    path = "stream";

  string = g_string_new (NULL);

  do
    {
      GError   *my_error = NULL;
      gboolean  success;

      success = g_input_stream_read_all (input, buffer, sizeof (buffer),
                                         &bytes_read, NULL, &my_error);

      if (bytes_read > 0)
        g_string_append_len (string, buffer, bytes_read);

      if (! success)
        {
          if (string->len > 0)
            {
              g_printerr ("%s: read error in '%s', trying to scan "
                          "partial content: %s",
                          G_STRFUNC, path, my_error->message);
              g_clear_error (&my_error);
              break;
            }

          g_string_free (string, TRUE);

          g_propagate_error (error, my_error);

          return NULL;
        }
    }
  while (bytes_read == sizeof (buffer));

  /*  gimp_scanner_new() takes a "name" for the scanner, not a filename  */
  scanner = gimp_scanner_new (path, NULL, string->str, error);

  bytes_read = string->len;

  g_scanner_input_text (scanner, g_string_free (string, FALSE), bytes_read);

  return scanner;
}

/**
 * gimp_scanner_new_string:
 * @text: (array length=text_len):
 * @text_len: The length of @text, or -1 if NULL-terminated
 * @error: return location for #GError, or %NULL
 *
 * Returns: (transfer full): The new #GimpScanner.
 *
 * Since: 2.4
 **/
GimpScanner *
gimp_scanner_new_string (const gchar  *text,
                         gint          text_len,
                         GError      **error)
{
  GimpScanner *scanner;

  g_return_val_if_fail (text != NULL || text_len <= 0, NULL);
  g_return_val_if_fail (error == NULL || *error == NULL, NULL);

  if (text_len < 0)
    text_len = text ? strlen (text) : 0;

  scanner = gimp_scanner_new (NULL, NULL, NULL, error);

  g_scanner_input_text (scanner, text, text_len);

  return scanner;
}

static GimpScanner *
gimp_scanner_new (const gchar  *name,
                  GMappedFile  *mapped,
                  gchar        *text,
                  GError      **error)
{
  GimpScanner     *scanner;
  GimpScannerData *data;

  scanner = g_scanner_new (NULL);

  data = g_slice_new0 (GimpScannerData);

  data->ref_count = 1;
  data->name      = g_strdup (name);
  data->mapped    = mapped;
  data->text      = text;
  data->error     = error;

  scanner->user_data   = data;
  scanner->msg_handler = gimp_scanner_message;

  scanner->config->cset_identifier_first = ( G_CSET_a_2_z G_CSET_A_2_Z );
  scanner->config->cset_identifier_nth   = ( G_CSET_a_2_z G_CSET_A_2_Z
                                             G_CSET_DIGITS "-_" );
  scanner->config->scan_identifier_1char = TRUE;

  scanner->config->store_int64           = TRUE;

  return scanner;
}

/**
 * gimp_scanner_ref:
 * @scanner: #GimpScanner to ref
 *
 * Adds a reference to a #GimpScanner.
 *
 * Returns: the same @scanner.
 *
 * Since: 3.0
 */
GimpScanner *
gimp_scanner_ref (GimpScanner *scanner)
{
  GimpScannerData *data;

  g_return_val_if_fail (scanner != NULL, NULL);

  data = scanner->user_data;

  data->ref_count++;

  return scanner;
}

/**
 * gimp_scanner_unref:
 * @scanner: A #GimpScanner created by gimp_scanner_new_file() or
 *           gimp_scanner_new_string()
 *
 * Unref a #GimpScanner. If the reference count drops to zero, the
 * scanner is freed.
 *
 * Since: 3.0
 **/
void
gimp_scanner_unref (GimpScanner *scanner)
{
  GimpScannerData *data;

  g_return_if_fail (scanner != NULL);

  data = scanner->user_data;

  data->ref_count--;

  if (data->ref_count < 1)
    {
      if (data->mapped)
        g_mapped_file_unref (data->mapped);

      if (data->text)
        g_free (data->text);

      g_free (data->name);
      g_slice_free (GimpScannerData, data);

      g_scanner_destroy (scanner);
    }
}

/**
 * gimp_scanner_parse_token:
 * @scanner: A #GimpScanner created by gimp_scanner_new_file() or
 *           gimp_scanner_new_string()
 * @token: the #GTokenType expected as next token.
 *
 * Returns: %TRUE if the next token is @token, %FALSE otherwise.
 *
 * Since: 2.4
 **/
gboolean
gimp_scanner_parse_token (GimpScanner *scanner,
                          GTokenType   token)
{
  if (g_scanner_peek_next_token (scanner) != token)
    return FALSE;

  g_scanner_get_next_token (scanner);

  return TRUE;
}

/**
 * gimp_scanner_parse_identifier:
 * @scanner: A #GimpScanner created by gimp_scanner_new_file() or
 *           gimp_scanner_new_string()
 * @identifier: (out): the expected identifier.
 *
 * Returns: %TRUE if the next token is an identifier and if its
 * value matches @identifier.
 *
 * Since: 2.4
 **/
gboolean
gimp_scanner_parse_identifier (GimpScanner *scanner,
                               const gchar *identifier)
{
  if (g_scanner_peek_next_token (scanner) != G_TOKEN_IDENTIFIER)
    return FALSE;

  g_scanner_get_next_token (scanner);

  if (strcmp (scanner->value.v_identifier, identifier))
    return FALSE;

  return TRUE;
}

/**
 * gimp_scanner_parse_string:
 * @scanner: A #GimpScanner created by gimp_scanner_new_file() or
 *           gimp_scanner_new_string()
 * @dest: (out): Return location for the parsed string
 *
 * Returns: %TRUE on success
 *
 * Since: 2.4
 **/
gboolean
gimp_scanner_parse_string (GimpScanner  *scanner,
                           gchar       **dest)
{
  if (g_scanner_peek_next_token (scanner) != G_TOKEN_STRING)
    return FALSE;

  g_scanner_get_next_token (scanner);

  if (*scanner->value.v_string)
    {
      if (! g_utf8_validate (scanner->value.v_string, -1, NULL))
        {
          g_scanner_warn (scanner, _("invalid UTF-8 string"));
          return FALSE;
        }

      *dest = g_strdup (scanner->value.v_string);
    }
  else
    {
      *dest = NULL;
    }

  return TRUE;
}

/**
 * gimp_scanner_parse_string_no_validate:
 * @scanner: A #GimpScanner created by gimp_scanner_new_file() or
 *           gimp_scanner_new_string()
 * @dest: (out): Return location for the parsed string
 *
 * Returns: %TRUE on success
 *
 * Since: 2.4
 **/
gboolean
gimp_scanner_parse_string_no_validate (GimpScanner  *scanner,
                                       gchar       **dest)
{
  if (g_scanner_peek_next_token (scanner) != G_TOKEN_STRING)
    return FALSE;

  g_scanner_get_next_token (scanner);

  if (*scanner->value.v_string)
    *dest = g_strdup (scanner->value.v_string);
  else
    *dest = NULL;

  return TRUE;
}

/**
 * gimp_scanner_parse_data:
 * @scanner: A #GimpScanner created by gimp_scanner_new_file() or
 *           gimp_scanner_new_string()
 * @length: Length of the data to parse
 * @dest: (out) (array length=length): Return location for the parsed data
 *
 * Returns: %TRUE on success
 *
 * Since: 2.4
 **/
gboolean
gimp_scanner_parse_data (GimpScanner  *scanner,
                         gint          length,
                         guint8      **dest)
{
  if (g_scanner_peek_next_token (scanner) != G_TOKEN_STRING)
    return FALSE;

  g_scanner_get_next_token (scanner);

  if (scanner->value.v_string)
    *dest = g_memdup2 (scanner->value.v_string, length);
  else
    *dest = NULL;

  return TRUE;
}

/**
 * gimp_scanner_parse_int:
 * @scanner: A #GimpScanner created by gimp_scanner_new_file() or
 *           gimp_scanner_new_string()
 * @dest: (out): Return location for the parsed integer
 *
 * Returns: %TRUE on success
 *
 * Since: 2.4
 **/
gboolean
gimp_scanner_parse_int (GimpScanner *scanner,
                        gint        *dest)
{
  gboolean negate = FALSE;

  if (g_scanner_peek_next_token (scanner) == '-')
    {
      negate = TRUE;
      g_scanner_get_next_token (scanner);
    }

  if (g_scanner_peek_next_token (scanner) != G_TOKEN_INT)
    return FALSE;

  g_scanner_get_next_token (scanner);

  if (negate)
    *dest = -scanner->value.v_int64;
  else
    *dest = scanner->value.v_int64;

  return TRUE;
}

/**
 * gimp_scanner_parse_int64:
 * @scanner: A #GimpScanner created by gimp_scanner_new_file() or
 *           gimp_scanner_new_string()
 * @dest: (out): Return location for the parsed integer
 *
 * Returns: %TRUE on success
 *
 * Since: 2.8
 **/
gboolean
gimp_scanner_parse_int64 (GimpScanner *scanner,
                          gint64      *dest)
{
  gboolean negate = FALSE;

  if (g_scanner_peek_next_token (scanner) == '-')
    {
      negate = TRUE;
      g_scanner_get_next_token (scanner);
    }

  if (g_scanner_peek_next_token (scanner) != G_TOKEN_INT)
    return FALSE;

  g_scanner_get_next_token (scanner);

  if (negate)
    *dest = -scanner->value.v_int64;
  else
    *dest = scanner->value.v_int64;

  return TRUE;
}

/**
 * gimp_scanner_parse_double:
 * @scanner: A #GimpScanner created by gimp_scanner_new_file() or
 *           gimp_scanner_new_string()
 * @dest: (out): Return location for the parsed double
 *
 * Returns: %TRUE on success
 *
 * Since: 2.4
 **/
gboolean
gimp_scanner_parse_double (GimpScanner *scanner,
                           gdouble     *dest)
{
  gboolean negate = FALSE;

  if (g_scanner_peek_next_token (scanner) == '-')
    {
      negate = TRUE;
      g_scanner_get_next_token (scanner);
    }

  if (g_scanner_peek_next_token (scanner) == G_TOKEN_FLOAT)
    {
      g_scanner_get_next_token (scanner);

      if (negate)
        *dest = -scanner->value.v_float;
      else
        *dest = scanner->value.v_float;

      return TRUE;
    }
  else if (g_scanner_peek_next_token (scanner) == G_TOKEN_INT)
    {
      /* v_int is unsigned so we need to cast to
       *
       * gint64 first for negative values.
       */

      g_scanner_get_next_token (scanner);

      if (negate)
        *dest = - (gint64) scanner->value.v_int;
      else
        *dest = scanner->value.v_int;

      return TRUE;
    }

  return FALSE;
}

/**
 * gimp_scanner_parse_boolean:
 * @scanner: A #GimpScanner created by gimp_scanner_new_file() or
 *           gimp_scanner_new_string()
 * @dest: (out): Return location for the parsed boolean
 *
 * Returns: %TRUE on success
 *
 * Since: 2.4
 **/
gboolean
gimp_scanner_parse_boolean (GimpScanner *scanner,
                            gboolean    *dest)
{
  if (g_scanner_peek_next_token (scanner) != G_TOKEN_IDENTIFIER)
    return FALSE;

  g_scanner_get_next_token (scanner);

  if (! g_ascii_strcasecmp (scanner->value.v_identifier, "yes") ||
      ! g_ascii_strcasecmp (scanner->value.v_identifier, "true"))
    {
      *dest = TRUE;
    }
  else if (! g_ascii_strcasecmp (scanner->value.v_identifier, "no") ||
           ! g_ascii_strcasecmp (scanner->value.v_identifier, "false"))
    {
      *dest = FALSE;
    }
  else
    {
      g_scanner_error
        (scanner,
         /* please don't translate 'yes' and 'no' */
         _("expected 'yes' or 'no' for boolean token, got '%s'"),
         scanner->value.v_identifier);

      return FALSE;
    }

  return TRUE;
}

enum
{
  COLOR_RGB  = 1,
  COLOR_RGBA,
  COLOR_HSV,
  COLOR_HSVA,
  COLOR
};

/**
 * gimp_scanner_parse_color:
 * @scanner: A #GimpScanner created by gimp_scanner_new_file() or
 *           gimp_scanner_new_string()
 * @color: (out callee-allocates): Pointer to a color to store the result
 *
 * Returns: %TRUE on success
 *
 * Since: 2.4
 **/
gboolean
gimp_scanner_parse_color (GimpScanner  *scanner,
                          GeglColor   **color)
{
  guint      scope_id;
  guint      old_scope_id;
  GTokenType token;
  gboolean   success = TRUE;

  scope_id = g_quark_from_static_string ("gimp_scanner_parse_color");
  old_scope_id = g_scanner_set_scope (scanner, scope_id);

  if (! g_scanner_scope_lookup_symbol (scanner, scope_id, "color"))
    {
      g_scanner_scope_add_symbol (scanner, scope_id,
                                  "color", GINT_TO_POINTER (COLOR));
      /* Deprecated. Kept for backward compatibility. */
      g_scanner_scope_add_symbol (scanner, scope_id,
                                  "color-rgb", GINT_TO_POINTER (COLOR_RGB));
      g_scanner_scope_add_symbol (scanner, scope_id,
                                  "color-rgba", GINT_TO_POINTER (COLOR_RGBA));
      g_scanner_scope_add_symbol (scanner, scope_id,
                                  "color-hsv", GINT_TO_POINTER (COLOR_HSV));
      g_scanner_scope_add_symbol (scanner, scope_id,
                                  "color-hsva", GINT_TO_POINTER (COLOR_HSVA));
    }

  token = g_scanner_peek_next_token (scanner);

  if (token == G_TOKEN_IDENTIFIER)
    {
      g_scanner_get_next_token (scanner);

      if (g_ascii_strcasecmp (scanner->value.v_identifier, "null") != 0)
        /* Do not fail the whole color parsing. Just output to stderr and assume
         * a NULL color property.
         */
        g_printerr ("%s: expected NULL identifier for serialized color, got '%s'. "
                    "Assuming NULL instead.\n",
                    G_STRFUNC, scanner->value.v_identifier);

      *color = NULL;

      token = g_scanner_peek_next_token (scanner);
      if (token == G_TOKEN_RIGHT_PAREN)
        token = G_TOKEN_NONE;
      else
        token = G_TOKEN_RIGHT_PAREN;
    }
  else if (token == G_TOKEN_LEFT_PAREN)
    {
      g_scanner_get_next_token (scanner);
      token = g_scanner_peek_next_token (scanner);

      if (token == G_TOKEN_SYMBOL)
        {
          if (GPOINTER_TO_INT (scanner->next_value.v_symbol) != COLOR)
            {
              /* Support historical GimpRGB format which may be stored in various config
               * files, but even some data (such as GTP tool presets which contains
               * tool-options which are GimpContext).
               */
              if (gimp_scanner_parse_deprecated_color (scanner, color))
                token = G_TOKEN_RIGHT_PAREN;
              else
                success = FALSE;
            }
          else
            {
              const Babl *format;
              gchar      *encoding;
              guint8     *data;
              gint        data_length;
              gint        profile_data_length;

              g_scanner_get_next_token (scanner);

              if (! gimp_scanner_parse_string (scanner, &encoding))
                {
                  token = G_TOKEN_STRING;
                  goto color_parsed;
                }

              if (! babl_format_exists (encoding))
                {
                  g_scanner_error (scanner,
                                   "%s: format \"%s\" for serialized color is not a valid babl format.",
                                   G_STRFUNC, encoding);
                  g_free (encoding);
                  success = FALSE;
                  goto color_parsed;
                }

              format = babl_format (encoding);
              g_free (encoding);

              if (! gimp_scanner_parse_int (scanner, &data_length))
                {
                  token = G_TOKEN_INT;
                  goto color_parsed;
                }

              if (data_length != babl_format_get_bytes_per_pixel (format))
                {
                  g_scanner_error (scanner,
                                   "%s: format \"%s\" expects %d bpp but color was serialized with %d bpp.",
                                   G_STRFUNC, babl_get_name (format),
                                   babl_format_get_bytes_per_pixel (format),
                                   data_length);
                  success = FALSE;
                  goto color_parsed;
                }

              if (! gimp_scanner_parse_data (scanner, data_length, &data))
                {
                  token = G_TOKEN_STRING;
                  goto color_parsed;
                }

              if (! gimp_scanner_parse_int (scanner, &profile_data_length))
                {
                  g_free (data);
                  token = G_TOKEN_INT;
                  goto color_parsed;
                }

              if (profile_data_length > 0)
                {
                  const Babl       *space = NULL;
                  GimpColorProfile *profile;
                  guint8           *profile_data;
                  GError           *error = NULL;

                  if (! gimp_scanner_parse_data (scanner, profile_data_length, &profile_data))
                    {
                      g_free (data);
                      token = G_TOKEN_STRING;
                      goto color_parsed;
                    }

                  profile = gimp_color_profile_new_from_icc_profile (profile_data, profile_data_length, &error);

                  if (profile)
                    {
                      space = gimp_color_profile_get_space (profile,
                                                            GIMP_COLOR_RENDERING_INTENT_RELATIVE_COLORIMETRIC,
                                                            &error);

                      if (! space)
                        {
                          g_scanner_error (scanner,
                                           "%s: failed to create Babl space for serialized color from profile: %s\n",
                                           G_STRFUNC, error->message);
                          g_clear_error (&error);
                        }
                      g_object_unref (profile);
                    }
                  else
                    {
                      g_scanner_error (scanner,
                                       "%s: invalid profile data for serialized color: %s",
                                       G_STRFUNC, error->message);
                      g_error_free (error);
                    }
                  format = babl_format_with_space (babl_format_get_encoding (format), space);

                  g_free (profile_data);
                }

              *color = gegl_color_new (NULL);
              gegl_color_set_pixel (*color, format, data);

              token = G_TOKEN_RIGHT_PAREN;
              g_free (data);
            }
        }
      else
        {
          token = G_TOKEN_SYMBOL;
        }

      if (success && token == G_TOKEN_RIGHT_PAREN)
        {
          token = g_scanner_peek_next_token (scanner);
          if (token == G_TOKEN_RIGHT_PAREN)
            {
              g_scanner_get_next_token (scanner);
              token = G_TOKEN_NONE;
            }
          else
            {
               g_clear_object (color);
               token = G_TOKEN_RIGHT_PAREN;
            }
        }
    }
  else
    {
      token = G_TOKEN_LEFT_PAREN;
    }

color_parsed:

  if (success && token != G_TOKEN_NONE)
    {
      g_scanner_get_next_token (scanner);
      g_scanner_unexp_token (scanner, token, NULL, NULL, NULL,
                             _("fatal parse error"), TRUE);
    }

  g_scanner_set_scope (scanner, old_scope_id);

  return (success && token == G_TOKEN_NONE);
}

/**
 * gimp_scanner_parse_matrix2:
 * @scanner: A #GimpScanner created by gimp_scanner_new_file() or
 *           gimp_scanner_new_string()
 * @dest: (out caller-allocates): Pointer to a matrix to store the result
 *
 * Returns: %TRUE on success
 *
 * Since: 2.4
 **/
gboolean
gimp_scanner_parse_matrix2 (GimpScanner *scanner,
                            GimpMatrix2 *dest)
{
  guint        scope_id;
  guint        old_scope_id;
  GTokenType   token;
  GimpMatrix2  matrix;

  scope_id = g_quark_from_static_string ("gimp_scanner_parse_matrix");
  old_scope_id = g_scanner_set_scope (scanner, scope_id);

  if (! g_scanner_scope_lookup_symbol (scanner, scope_id, "matrix"))
    g_scanner_scope_add_symbol (scanner, scope_id,
                                "matrix", GINT_TO_POINTER (0));

  token = G_TOKEN_LEFT_PAREN;

  while (g_scanner_peek_next_token (scanner) == token)
    {
      token = g_scanner_get_next_token (scanner);

      switch (token)
        {
        case G_TOKEN_LEFT_PAREN:
          token = G_TOKEN_SYMBOL;
          break;

        case G_TOKEN_SYMBOL:
          {
            token = G_TOKEN_FLOAT;

            if (! gimp_scanner_parse_double (scanner, &matrix.coeff[0][0]))
              goto finish;
            if (! gimp_scanner_parse_double (scanner, &matrix.coeff[0][1]))
              goto finish;
            if (! gimp_scanner_parse_double (scanner, &matrix.coeff[1][0]))
              goto finish;
            if (! gimp_scanner_parse_double (scanner, &matrix.coeff[1][1]))
              goto finish;

            token = G_TOKEN_RIGHT_PAREN;
          }
          break;

        case G_TOKEN_RIGHT_PAREN:
          token = G_TOKEN_NONE; /* indicates success */
          goto finish;

        default: /* do nothing */
          break;
        }
    }

 finish:

  if (token != G_TOKEN_NONE)
    {
      g_scanner_get_next_token (scanner);
      g_scanner_unexp_token (scanner, token, NULL, NULL, NULL,
                             _("fatal parse error"), TRUE);
    }
  else
    {
      *dest = matrix;
    }

  g_scanner_set_scope (scanner, old_scope_id);

  return (token == G_TOKEN_NONE);
}


/*  private functions  */

static void
gimp_scanner_message (GimpScanner *scanner,
                      gchar       *message,
                      gboolean     is_error)
{
  GimpScannerData *data = scanner->user_data;

  /* we don't expect warnings */
  g_return_if_fail (is_error);

  if (data->name)
    g_set_error (data->error, GIMP_CONFIG_ERROR, GIMP_CONFIG_ERROR_PARSE,
                 _("Error while parsing '%s' in line %d: %s"),
                 data->name, scanner->line, message);
  else
    /*  should never happen, thus not marked for translation  */
    g_set_error (data->error, GIMP_CONFIG_ERROR, GIMP_CONFIG_ERROR_PARSE,
                 "Error parsing internal buffer: %s", message);
}

static GTokenType
gimp_scanner_parse_deprecated_color (GimpScanner  *scanner,
                                     GeglColor   **color)
{
  guint      scope_id;
  guint      old_scope_id;
  GTokenType token;

  scope_id = g_quark_from_static_string ("gimp_scanner_parse_deprecated_color");
  old_scope_id = g_scanner_set_scope (scanner, scope_id);

  if (! g_scanner_scope_lookup_symbol (scanner, scope_id, "color-rgb"))
    {
      g_scanner_scope_add_symbol (scanner, scope_id,
                                  "color-rgb", GINT_TO_POINTER (COLOR_RGB));
      g_scanner_scope_add_symbol (scanner, scope_id,
                                  "color-rgba", GINT_TO_POINTER (COLOR_RGBA));
      g_scanner_scope_add_symbol (scanner, scope_id,
                                  "color-hsv", GINT_TO_POINTER (COLOR_HSV));
      g_scanner_scope_add_symbol (scanner, scope_id,
                                  "color-hsva", GINT_TO_POINTER (COLOR_HSVA));
    }

  token = G_TOKEN_SYMBOL;

  while (g_scanner_peek_next_token (scanner) == token)
    {
      token = g_scanner_get_next_token (scanner);

      switch (token)
        {
        case G_TOKEN_SYMBOL:
          {
            gdouble  col[4]     = { 0.0, 0.0, 0.0, 1.0 };
            gfloat   col_f[4]   = { 0.0f, 0.0f, 0.0f, 1.0f };
            gint     n_channels = 4;
            gboolean is_hsv     = FALSE;
            gint     i;

            switch (GPOINTER_TO_INT (scanner->value.v_symbol))
              {
              case COLOR_RGB:
                n_channels = 3;
                /* fallthrough */
              case COLOR_RGBA:
                break;

              case COLOR_HSV:
                n_channels = 3;
                /* fallthrough */
              case COLOR_HSVA:
                is_hsv = TRUE;
                break;
              }

            token = G_TOKEN_FLOAT;

            for (i = 0; i < n_channels; i++)
              {
                if (! gimp_scanner_parse_double (scanner, &col[i]))
                  goto finish;

                if (trunc (col[i]) == col[i] &&
                    g_scanner_peek_next_token (scanner) == G_TOKEN_COMMA)
                  {
                    /* This ugly block is a workaround to salvage XCF
                     * files containing broken color serialization using
                     * a comma as decimal separator, cf. #15774.
                     * We assemble 2 ints separated by a comma as a
                     * float.
                     */
                    g_scanner_get_next_token (scanner);

                    if (g_scanner_peek_next_token (scanner) != G_TOKEN_INT)
                      goto finish;

                    g_scanner_get_next_token (scanner);

                    if (scanner->value.v_int > 0)
                      col[i] += scanner->value.v_int / pow (10, (int) log10 (scanner->value.v_int) + 1);
                  }

                col_f[i] = (gfloat) col[i];
              }

            *color = gegl_color_new (NULL);
            if (is_hsv)
              gegl_color_set_pixel (*color, babl_format ("HSVA float"), col_f);
            else
              gegl_color_set_pixel (*color, babl_format ("R'G'B'A double"), col);

            /* Indicates success. */
            token = G_TOKEN_NONE;
          }
          break;

        default: /* do nothing */
          break;
        }
    }

finish:

  g_scanner_set_scope (scanner, old_scope_id);

  return token;
}

/* --- end libammoos/config/fieldconfig/gimpscanner.c --- */
