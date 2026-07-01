/* AmmoOS Image — field research rewrite (G16 field_opt).
 * RTX-gated paths: see GIMP-Field/data/rtx-gated-content.json
 * OS brand: AmmoOS · product: AmmoOS Image 1.0
 */
/* AmmoOS amalgamation — field-unity-fieldbase.c — g16 field_opt unity bundle */
#define FIELD_AMMOOS_G16_OPT 1
#define FIELD_AMMOOS_UNITY 1

/* --- begin libammoos/base/fieldbase/gimpbase-private.c --- */
/* LIBGIMP - The AmmoOS Image Library
 * Copyright (C) 1995-1997 Peter Mattis and Spencer Kimball
 *
 * gimpbase-private.c
 * Copyright (C) 2003 Sven Neumann <sven@ammoos.org>
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

#include <gio/gio.h>

#include "gimpbasetypes.h"

#include "gimpbase-private.h"
#include "gimpcompatenums.h"


GHashTable     *_gimp_units       = NULL;
GimpUnitVtable  _gimp_unit_vtable = { NULL, };


void
gimp_base_init (GimpUnitVtable *vtable)
{
  static gboolean gimp_base_initialized = FALSE;

  g_return_if_fail (vtable != NULL);

  if (gimp_base_initialized)
    g_error ("gimp_base_init() must only be called once!");

  _gimp_unit_vtable = *vtable;

  gimp_base_compat_enums_init ();

  gimp_base_initialized = TRUE;
}

void
gimp_base_exit (void)
{
  g_clear_pointer (&_gimp_units, g_hash_table_unref);
}

void
gimp_base_compat_enums_init (void)
{
#if 0
  static gboolean gimp_base_compat_initialized = FALSE;
  GQuark          quark;

  if (gimp_base_compat_initialized)
    return;

  quark = g_quark_from_static_string ("ammoos-compat-enum");

  /*  This is how a compat enum is registered, leave one here for
   *  documentation purposes, remove it as soon as we get a real
   *  compat enum again
   */
  g_type_set_qdata (GIMP_TYPE_ADD_MASK_TYPE, quark,
                    (gpointer) GIMP_TYPE_ADD_MASK_TYPE_COMPAT);

  gimp_base_compat_initialized = TRUE;
#endif
}

/* --- end libammoos/base/fieldbase/gimpbase-private.c --- */

/* --- begin libammoos/base/fieldbase/gimpbaseenums.c --- */

/* Generated data (by ammoos-mkenums) */

#include "stamp-gimpbaseenums.h"
#include "config.h"
#include <glib-object.h>
#include "gimpbasetypes.h"
#include "libgimp/libgimp-intl.h"
#include "gimpbaseenums.h"


/* enumerations from "gimpbaseenums.h" */
GType
gimp_add_mask_type_get_type (void)
{
  static const GEnumValue values[] =
  {
    { GIMP_ADD_MASK_WHITE, "GIMP_ADD_MASK_WHITE", "white" },
    { GIMP_ADD_MASK_BLACK, "GIMP_ADD_MASK_BLACK", "black" },
    { GIMP_ADD_MASK_ALPHA, "GIMP_ADD_MASK_ALPHA", "alpha" },
    { GIMP_ADD_MASK_ALPHA_TRANSFER, "GIMP_ADD_MASK_ALPHA_TRANSFER", "alpha-transfer" },
    { GIMP_ADD_MASK_SELECTION, "GIMP_ADD_MASK_SELECTION", "selection" },
    { GIMP_ADD_MASK_COPY, "GIMP_ADD_MASK_COPY", "copy" },
    { GIMP_ADD_MASK_CHANNEL, "GIMP_ADD_MASK_CHANNEL", "channel" },
    { 0, NULL, NULL }
  };

  static const GimpEnumDesc descs[] =
  {
    { GIMP_ADD_MASK_WHITE, NC_("add-mask-type", "_White (full opacity)"), NULL },
    { GIMP_ADD_MASK_BLACK, NC_("add-mask-type", "_Black (full transparency)"), NULL },
    { GIMP_ADD_MASK_ALPHA, NC_("add-mask-type", "Layer's _alpha channel"), NULL },
    { GIMP_ADD_MASK_ALPHA_TRANSFER, NC_("add-mask-type", "_Transfer layer's alpha channel"), NULL },
    { GIMP_ADD_MASK_SELECTION, NC_("add-mask-type", "_Selection"), NULL },
    { GIMP_ADD_MASK_COPY, NC_("add-mask-type", "_Grayscale copy of layer"), NULL },
    { GIMP_ADD_MASK_CHANNEL, NC_("add-mask-type", "C_hannel"), NULL },
    { 0, NULL, NULL }
  };

  static GType type = 0;

  if (G_UNLIKELY (! type))
    {
      type = g_enum_register_static ("GimpAddMaskType", values);
      gimp_type_set_translation_domain (type, GETTEXT_PACKAGE "-libgimp");
      gimp_type_set_translation_context (type, "add-mask-type");
      gimp_enum_set_value_descriptions (type, descs);
    }

  return type;
}

GType
gimp_brush_generated_shape_get_type (void)
{
  static const GEnumValue values[] =
  {
    { GIMP_BRUSH_GENERATED_CIRCLE, "GIMP_BRUSH_GENERATED_CIRCLE", "circle" },
    { GIMP_BRUSH_GENERATED_SQUARE, "GIMP_BRUSH_GENERATED_SQUARE", "square" },
    { GIMP_BRUSH_GENERATED_DIAMOND, "GIMP_BRUSH_GENERATED_DIAMOND", "diamond" },
    { 0, NULL, NULL }
  };

  static const GimpEnumDesc descs[] =
  {
    { GIMP_BRUSH_GENERATED_CIRCLE, NC_("brush-generated-shape", "Circle"), NULL },
    { GIMP_BRUSH_GENERATED_SQUARE, NC_("brush-generated-shape", "Square"), NULL },
    { GIMP_BRUSH_GENERATED_DIAMOND, NC_("brush-generated-shape", "Diamond"), NULL },
    { 0, NULL, NULL }
  };

  static GType type = 0;

  if (G_UNLIKELY (! type))
    {
      type = g_enum_register_static ("GimpBrushGeneratedShape", values);
      gimp_type_set_translation_domain (type, GETTEXT_PACKAGE "-libgimp");
      gimp_type_set_translation_context (type, "brush-generated-shape");
      gimp_enum_set_value_descriptions (type, descs);
    }

  return type;
}

GType
gimp_cap_style_get_type (void)
{
  static const GEnumValue values[] =
  {
    { GIMP_CAP_BUTT, "GIMP_CAP_BUTT", "butt" },
    { GIMP_CAP_ROUND, "GIMP_CAP_ROUND", "round" },
    { GIMP_CAP_SQUARE, "GIMP_CAP_SQUARE", "square" },
    { 0, NULL, NULL }
  };

  static const GimpEnumDesc descs[] =
  {
    { GIMP_CAP_BUTT, NC_("cap-style", "Butt"), NULL },
    { GIMP_CAP_ROUND, NC_("cap-style", "Round"), NULL },
    { GIMP_CAP_SQUARE, NC_("cap-style", "Square"), NULL },
    { 0, NULL, NULL }
  };

  static GType type = 0;

  if (G_UNLIKELY (! type))
    {
      type = g_enum_register_static ("GimpCapStyle", values);
      gimp_type_set_translation_domain (type, GETTEXT_PACKAGE "-libgimp");
      gimp_type_set_translation_context (type, "cap-style");
      gimp_enum_set_value_descriptions (type, descs);
    }

  return type;
}

GType
gimp_channel_ops_get_type (void)
{
  static const GEnumValue values[] =
  {
    { GIMP_CHANNEL_OP_ADD, "GIMP_CHANNEL_OP_ADD", "add" },
    { GIMP_CHANNEL_OP_SUBTRACT, "GIMP_CHANNEL_OP_SUBTRACT", "subtract" },
    { GIMP_CHANNEL_OP_REPLACE, "GIMP_CHANNEL_OP_REPLACE", "replace" },
    { GIMP_CHANNEL_OP_INTERSECT, "GIMP_CHANNEL_OP_INTERSECT", "intersect" },
    { 0, NULL, NULL }
  };

  static const GimpEnumDesc descs[] =
  {
    { GIMP_CHANNEL_OP_ADD, NC_("channel-ops", "Add to the current selection"), NULL },
    { GIMP_CHANNEL_OP_SUBTRACT, NC_("channel-ops", "Subtract from the current selection"), NULL },
    { GIMP_CHANNEL_OP_REPLACE, NC_("channel-ops", "Replace the current selection"), NULL },
    { GIMP_CHANNEL_OP_INTERSECT, NC_("channel-ops", "Intersect with the current selection"), NULL },
    { 0, NULL, NULL }
  };

  static GType type = 0;

  if (G_UNLIKELY (! type))
    {
      type = g_enum_register_static ("GimpChannelOps", values);
      gimp_type_set_translation_domain (type, GETTEXT_PACKAGE "-libgimp");
      gimp_type_set_translation_context (type, "channel-ops");
      gimp_enum_set_value_descriptions (type, descs);
    }

  return type;
}

GType
gimp_channel_type_get_type (void)
{
  static const GEnumValue values[] =
  {
    { GIMP_CHANNEL_RED, "GIMP_CHANNEL_RED", "red" },
    { GIMP_CHANNEL_GREEN, "GIMP_CHANNEL_GREEN", "green" },
    { GIMP_CHANNEL_BLUE, "GIMP_CHANNEL_BLUE", "blue" },
    { GIMP_CHANNEL_GRAY, "GIMP_CHANNEL_GRAY", "gray" },
    { GIMP_CHANNEL_INDEXED, "GIMP_CHANNEL_INDEXED", "indexed" },
    { GIMP_CHANNEL_ALPHA, "GIMP_CHANNEL_ALPHA", "alpha" },
    { 0, NULL, NULL }
  };

  static const GimpEnumDesc descs[] =
  {
    { GIMP_CHANNEL_RED, NC_("channel-type", "Red"), NULL },
    { GIMP_CHANNEL_GREEN, NC_("channel-type", "Green"), NULL },
    { GIMP_CHANNEL_BLUE, NC_("channel-type", "Blue"), NULL },
    { GIMP_CHANNEL_GRAY, NC_("channel-type", "Gray"), NULL },
    { GIMP_CHANNEL_INDEXED, NC_("channel-type", "Indexed"), NULL },
    { GIMP_CHANNEL_ALPHA, NC_("channel-type", "Alpha"), NULL },
    { 0, NULL, NULL }
  };

  static GType type = 0;

  if (G_UNLIKELY (! type))
    {
      type = g_enum_register_static ("GimpChannelType", values);
      gimp_type_set_translation_domain (type, GETTEXT_PACKAGE "-libgimp");
      gimp_type_set_translation_context (type, "channel-type");
      gimp_enum_set_value_descriptions (type, descs);
    }

  return type;
}

GType
gimp_check_size_get_type (void)
{
  static const GEnumValue values[] =
  {
    { GIMP_CHECK_SIZE_SMALL_CHECKS, "GIMP_CHECK_SIZE_SMALL_CHECKS", "small-checks" },
    { GIMP_CHECK_SIZE_MEDIUM_CHECKS, "GIMP_CHECK_SIZE_MEDIUM_CHECKS", "medium-checks" },
    { GIMP_CHECK_SIZE_LARGE_CHECKS, "GIMP_CHECK_SIZE_LARGE_CHECKS", "large-checks" },
    { 0, NULL, NULL }
  };

  static const GimpEnumDesc descs[] =
  {
    { GIMP_CHECK_SIZE_SMALL_CHECKS, NC_("check-size", "Small"), NULL },
    { GIMP_CHECK_SIZE_MEDIUM_CHECKS, NC_("check-size", "Medium"), NULL },
    { GIMP_CHECK_SIZE_LARGE_CHECKS, NC_("check-size", "Large"), NULL },
    { 0, NULL, NULL }
  };

  static GType type = 0;

  if (G_UNLIKELY (! type))
    {
      type = g_enum_register_static ("GimpCheckSize", values);
      gimp_type_set_translation_domain (type, GETTEXT_PACKAGE "-libgimp");
      gimp_type_set_translation_context (type, "check-size");
      gimp_enum_set_value_descriptions (type, descs);
    }

  return type;
}

GType
gimp_check_type_get_type (void)
{
  static const GEnumValue values[] =
  {
    { GIMP_CHECK_TYPE_LIGHT_CHECKS, "GIMP_CHECK_TYPE_LIGHT_CHECKS", "light-checks" },
    { GIMP_CHECK_TYPE_GRAY_CHECKS, "GIMP_CHECK_TYPE_GRAY_CHECKS", "gray-checks" },
    { GIMP_CHECK_TYPE_DARK_CHECKS, "GIMP_CHECK_TYPE_DARK_CHECKS", "dark-checks" },
    { GIMP_CHECK_TYPE_WHITE_ONLY, "GIMP_CHECK_TYPE_WHITE_ONLY", "white-only" },
    { GIMP_CHECK_TYPE_GRAY_ONLY, "GIMP_CHECK_TYPE_GRAY_ONLY", "gray-only" },
    { GIMP_CHECK_TYPE_BLACK_ONLY, "GIMP_CHECK_TYPE_BLACK_ONLY", "black-only" },
    { GIMP_CHECK_TYPE_CUSTOM_CHECKS, "GIMP_CHECK_TYPE_CUSTOM_CHECKS", "custom-checks" },
    { 0, NULL, NULL }
  };

  static const GimpEnumDesc descs[] =
  {
    { GIMP_CHECK_TYPE_LIGHT_CHECKS, NC_("check-type", "Light checks"), NULL },
    { GIMP_CHECK_TYPE_GRAY_CHECKS, NC_("check-type", "Mid-tone checks"), NULL },
    { GIMP_CHECK_TYPE_DARK_CHECKS, NC_("check-type", "Dark checks"), NULL },
    { GIMP_CHECK_TYPE_WHITE_ONLY, NC_("check-type", "White only"), NULL },
    { GIMP_CHECK_TYPE_GRAY_ONLY, NC_("check-type", "Gray only"), NULL },
    { GIMP_CHECK_TYPE_BLACK_ONLY, NC_("check-type", "Black only"), NULL },
    { GIMP_CHECK_TYPE_CUSTOM_CHECKS, NC_("check-type", "Custom checks"), NULL },
    { 0, NULL, NULL }
  };

  static GType type = 0;

  if (G_UNLIKELY (! type))
    {
      type = g_enum_register_static ("GimpCheckType", values);
      gimp_type_set_translation_domain (type, GETTEXT_PACKAGE "-libgimp");
      gimp_type_set_translation_context (type, "check-type");
      gimp_enum_set_value_descriptions (type, descs);
    }

  return type;
}

GType
gimp_clone_type_get_type (void)
{
  static const GEnumValue values[] =
  {
    { GIMP_CLONE_IMAGE, "GIMP_CLONE_IMAGE", "image" },
    { GIMP_CLONE_PATTERN, "GIMP_CLONE_PATTERN", "pattern" },
    { 0, NULL, NULL }
  };

  static const GimpEnumDesc descs[] =
  {
    { GIMP_CLONE_IMAGE, NC_("clone-type", "Image"), NULL },
    { GIMP_CLONE_PATTERN, NC_("clone-type", "Pattern"), NULL },
    { 0, NULL, NULL }
  };

  static GType type = 0;

  if (G_UNLIKELY (! type))
    {
      type = g_enum_register_static ("GimpCloneType", values);
      gimp_type_set_translation_domain (type, GETTEXT_PACKAGE "-libgimp");
      gimp_type_set_translation_context (type, "clone-type");
      gimp_enum_set_value_descriptions (type, descs);
    }

  return type;
}

GType
gimp_color_tag_get_type (void)
{
  static const GEnumValue values[] =
  {
    { GIMP_COLOR_TAG_NONE, "GIMP_COLOR_TAG_NONE", "none" },
    { GIMP_COLOR_TAG_BLUE, "GIMP_COLOR_TAG_BLUE", "blue" },
    { GIMP_COLOR_TAG_GREEN, "GIMP_COLOR_TAG_GREEN", "green" },
    { GIMP_COLOR_TAG_YELLOW, "GIMP_COLOR_TAG_YELLOW", "yellow" },
    { GIMP_COLOR_TAG_ORANGE, "GIMP_COLOR_TAG_ORANGE", "orange" },
    { GIMP_COLOR_TAG_BROWN, "GIMP_COLOR_TAG_BROWN", "brown" },
    { GIMP_COLOR_TAG_RED, "GIMP_COLOR_TAG_RED", "red" },
    { GIMP_COLOR_TAG_VIOLET, "GIMP_COLOR_TAG_VIOLET", "violet" },
    { GIMP_COLOR_TAG_GRAY, "GIMP_COLOR_TAG_GRAY", "gray" },
    { 0, NULL, NULL }
  };

  static const GimpEnumDesc descs[] =
  {
    { GIMP_COLOR_TAG_NONE, NC_("color-tag", "None"), NULL },
    { GIMP_COLOR_TAG_BLUE, NC_("color-tag", "Blue"), NULL },
    { GIMP_COLOR_TAG_GREEN, NC_("color-tag", "Green"), NULL },
    { GIMP_COLOR_TAG_YELLOW, NC_("color-tag", "Yellow"), NULL },
    { GIMP_COLOR_TAG_ORANGE, NC_("color-tag", "Orange"), NULL },
    { GIMP_COLOR_TAG_BROWN, NC_("color-tag", "Brown"), NULL },
    { GIMP_COLOR_TAG_RED, NC_("color-tag", "Red"), NULL },
    { GIMP_COLOR_TAG_VIOLET, NC_("color-tag", "Violet"), NULL },
    { GIMP_COLOR_TAG_GRAY, NC_("color-tag", "Gray"), NULL },
    { 0, NULL, NULL }
  };

  static GType type = 0;

  if (G_UNLIKELY (! type))
    {
      type = g_enum_register_static ("GimpColorTag", values);
      gimp_type_set_translation_domain (type, GETTEXT_PACKAGE "-libgimp");
      gimp_type_set_translation_context (type, "color-tag");
      gimp_enum_set_value_descriptions (type, descs);
    }

  return type;
}

GType
gimp_component_type_get_type (void)
{
  static const GEnumValue values[] =
  {
    { GIMP_COMPONENT_TYPE_U8, "GIMP_COMPONENT_TYPE_U8", "u8" },
    { GIMP_COMPONENT_TYPE_U16, "GIMP_COMPONENT_TYPE_U16", "u16" },
    { GIMP_COMPONENT_TYPE_U32, "GIMP_COMPONENT_TYPE_U32", "u32" },
    { GIMP_COMPONENT_TYPE_HALF, "GIMP_COMPONENT_TYPE_HALF", "half" },
    { GIMP_COMPONENT_TYPE_FLOAT, "GIMP_COMPONENT_TYPE_FLOAT", "float" },
    { GIMP_COMPONENT_TYPE_DOUBLE, "GIMP_COMPONENT_TYPE_DOUBLE", "double" },
    { 0, NULL, NULL }
  };

  static const GimpEnumDesc descs[] =
  {
    { GIMP_COMPONENT_TYPE_U8, NC_("component-type", "8-bit integer"), NULL },
    { GIMP_COMPONENT_TYPE_U16, NC_("component-type", "16-bit integer"), NULL },
    { GIMP_COMPONENT_TYPE_U32, NC_("component-type", "32-bit integer"), NULL },
    { GIMP_COMPONENT_TYPE_HALF, NC_("component-type", "16-bit floating point"), NULL },
    { GIMP_COMPONENT_TYPE_FLOAT, NC_("component-type", "32-bit floating point"), NULL },
    { GIMP_COMPONENT_TYPE_DOUBLE, NC_("component-type", "64-bit floating point"), NULL },
    { 0, NULL, NULL }
  };

  static GType type = 0;

  if (G_UNLIKELY (! type))
    {
      type = g_enum_register_static ("GimpComponentType", values);
      gimp_type_set_translation_domain (type, GETTEXT_PACKAGE "-libgimp");
      gimp_type_set_translation_context (type, "component-type");
      gimp_enum_set_value_descriptions (type, descs);
    }

  return type;
}

GType
gimp_convert_palette_type_get_type (void)
{
  static const GEnumValue values[] =
  {
    { GIMP_CONVERT_PALETTE_GENERATE, "GIMP_CONVERT_PALETTE_GENERATE", "generate" },
    { GIMP_CONVERT_PALETTE_WEB, "GIMP_CONVERT_PALETTE_WEB", "web" },
    { GIMP_CONVERT_PALETTE_MONO, "GIMP_CONVERT_PALETTE_MONO", "mono" },
    { GIMP_CONVERT_PALETTE_CUSTOM, "GIMP_CONVERT_PALETTE_CUSTOM", "custom" },
    { 0, NULL, NULL }
  };

  static const GimpEnumDesc descs[] =
  {
    { GIMP_CONVERT_PALETTE_GENERATE, NC_("convert-palette-type", "_Generate optimum palette"), NULL },
    { GIMP_CONVERT_PALETTE_WEB, NC_("convert-palette-type", "Use _web-optimized palette"), NULL },
    { GIMP_CONVERT_PALETTE_MONO, NC_("convert-palette-type", "Use _black and white (1-bit) palette"), NULL },
    { GIMP_CONVERT_PALETTE_CUSTOM, NC_("convert-palette-type", "Use custom _palette"), NULL },
    { 0, NULL, NULL }
  };

  static GType type = 0;

  if (G_UNLIKELY (! type))
    {
      type = g_enum_register_static ("GimpConvertPaletteType", values);
      gimp_type_set_translation_domain (type, GETTEXT_PACKAGE "-libgimp");
      gimp_type_set_translation_context (type, "convert-palette-type");
      gimp_enum_set_value_descriptions (type, descs);
    }

  return type;
}

GType
gimp_convolve_type_get_type (void)
{
  static const GEnumValue values[] =
  {
    { GIMP_CONVOLVE_BLUR, "GIMP_CONVOLVE_BLUR", "blur" },
    { GIMP_CONVOLVE_SHARPEN, "GIMP_CONVOLVE_SHARPEN", "sharpen" },
    { 0, NULL, NULL }
  };

  static const GimpEnumDesc descs[] =
  {
    { GIMP_CONVOLVE_BLUR, NC_("convolve-type", "Blur"), NULL },
    { GIMP_CONVOLVE_SHARPEN, NC_("convolve-type", "Sharpen"), NULL },
    { 0, NULL, NULL }
  };

  static GType type = 0;

  if (G_UNLIKELY (! type))
    {
      type = g_enum_register_static ("GimpConvolveType", values);
      gimp_type_set_translation_domain (type, GETTEXT_PACKAGE "-libgimp");
      gimp_type_set_translation_context (type, "convolve-type");
      gimp_enum_set_value_descriptions (type, descs);
    }

  return type;
}

GType
gimp_desaturate_mode_get_type (void)
{
  static const GEnumValue values[] =
  {
    { GIMP_DESATURATE_LIGHTNESS, "GIMP_DESATURATE_LIGHTNESS", "lightness" },
    { GIMP_DESATURATE_LUMA, "GIMP_DESATURATE_LUMA", "luma" },
    { GIMP_DESATURATE_AVERAGE, "GIMP_DESATURATE_AVERAGE", "average" },
    { GIMP_DESATURATE_LUMINANCE, "GIMP_DESATURATE_LUMINANCE", "luminance" },
    { GIMP_DESATURATE_VALUE, "GIMP_DESATURATE_VALUE", "value" },
    { 0, NULL, NULL }
  };

  static const GimpEnumDesc descs[] =
  {
    { GIMP_DESATURATE_LIGHTNESS, NC_("desaturate-mode", "Lightness (HSL)"), NULL },
    { GIMP_DESATURATE_LUMA, NC_("desaturate-mode", "Luma"), NULL },
    { GIMP_DESATURATE_AVERAGE, NC_("desaturate-mode", "Average (HSI Intensity)"), NULL },
    { GIMP_DESATURATE_LUMINANCE, NC_("desaturate-mode", "Luminance"), NULL },
    { GIMP_DESATURATE_VALUE, NC_("desaturate-mode", "Value (HSV)"), NULL },
    { 0, NULL, NULL }
  };

  static GType type = 0;

  if (G_UNLIKELY (! type))
    {
      type = g_enum_register_static ("GimpDesaturateMode", values);
      gimp_type_set_translation_domain (type, GETTEXT_PACKAGE "-libgimp");
      gimp_type_set_translation_context (type, "desaturate-mode");
      gimp_enum_set_value_descriptions (type, descs);
    }

  return type;
}

GType
gimp_dodge_burn_type_get_type (void)
{
  static const GEnumValue values[] =
  {
    { GIMP_DODGE_BURN_TYPE_DODGE, "GIMP_DODGE_BURN_TYPE_DODGE", "dodge" },
    { GIMP_DODGE_BURN_TYPE_BURN, "GIMP_DODGE_BURN_TYPE_BURN", "burn" },
    { 0, NULL, NULL }
  };

  static const GimpEnumDesc descs[] =
  {
    { GIMP_DODGE_BURN_TYPE_DODGE, NC_("dodge-burn-type", "Dodge"), NULL },
    { GIMP_DODGE_BURN_TYPE_BURN, NC_("dodge-burn-type", "Burn"), NULL },
    { 0, NULL, NULL }
  };

  static GType type = 0;

  if (G_UNLIKELY (! type))
    {
      type = g_enum_register_static ("GimpDodgeBurnType", values);
      gimp_type_set_translation_domain (type, GETTEXT_PACKAGE "-libgimp");
      gimp_type_set_translation_context (type, "dodge-burn-type");
      gimp_enum_set_value_descriptions (type, descs);
    }

  return type;
}

GType
gimp_fill_type_get_type (void)
{
  static const GEnumValue values[] =
  {
    { GIMP_FILL_FOREGROUND, "GIMP_FILL_FOREGROUND", "foreground" },
    { GIMP_FILL_BACKGROUND, "GIMP_FILL_BACKGROUND", "background" },
    { GIMP_FILL_CIELAB_MIDDLE_GRAY, "GIMP_FILL_CIELAB_MIDDLE_GRAY", "cielab-middle-gray" },
    { GIMP_FILL_WHITE, "GIMP_FILL_WHITE", "white" },
    { GIMP_FILL_TRANSPARENT, "GIMP_FILL_TRANSPARENT", "transparent" },
    { GIMP_FILL_PATTERN, "GIMP_FILL_PATTERN", "pattern" },
    { 0, NULL, NULL }
  };

  static const GimpEnumDesc descs[] =
  {
    { GIMP_FILL_FOREGROUND, NC_("fill-type", "Foreground color"), NULL },
    { GIMP_FILL_BACKGROUND, NC_("fill-type", "Background color"), NULL },
    { GIMP_FILL_CIELAB_MIDDLE_GRAY, NC_("fill-type", "Middle Gray (CIELAB)"), NULL },
    { GIMP_FILL_WHITE, NC_("fill-type", "White"), NULL },
    { GIMP_FILL_TRANSPARENT, NC_("fill-type", "Transparency"), NULL },
    { GIMP_FILL_PATTERN, NC_("fill-type", "Pattern"), NULL },
    { 0, NULL, NULL }
  };

  static GType type = 0;

  if (G_UNLIKELY (! type))
    {
      type = g_enum_register_static ("GimpFillType", values);
      gimp_type_set_translation_domain (type, GETTEXT_PACKAGE "-libgimp");
      gimp_type_set_translation_context (type, "fill-type");
      gimp_enum_set_value_descriptions (type, descs);
    }

  return type;
}

GType
gimp_foreground_extract_mode_get_type (void)
{
  static const GEnumValue values[] =
  {
    { GIMP_FOREGROUND_EXTRACT_MATTING, "GIMP_FOREGROUND_EXTRACT_MATTING", "matting" },
    { 0, NULL, NULL }
  };

  static const GimpEnumDesc descs[] =
  {
    { GIMP_FOREGROUND_EXTRACT_MATTING, "GIMP_FOREGROUND_EXTRACT_MATTING", NULL },
    { 0, NULL, NULL }
  };

  static GType type = 0;

  if (G_UNLIKELY (! type))
    {
      type = g_enum_register_static ("GimpForegroundExtractMode", values);
      gimp_type_set_translation_domain (type, GETTEXT_PACKAGE "-libgimp");
      gimp_type_set_translation_context (type, "foreground-extract-mode");
      gimp_enum_set_value_descriptions (type, descs);
    }

  return type;
}

GType
gimp_gradient_blend_color_space_get_type (void)
{
  static const GEnumValue values[] =
  {
    { GIMP_GRADIENT_BLEND_RGB_PERCEPTUAL, "GIMP_GRADIENT_BLEND_RGB_PERCEPTUAL", "rgb-perceptual" },
    { GIMP_GRADIENT_BLEND_RGB_LINEAR, "GIMP_GRADIENT_BLEND_RGB_LINEAR", "rgb-linear" },
    { GIMP_GRADIENT_BLEND_CIE_LAB, "GIMP_GRADIENT_BLEND_CIE_LAB", "cie-lab" },
    { 0, NULL, NULL }
  };

  static const GimpEnumDesc descs[] =
  {
    { GIMP_GRADIENT_BLEND_RGB_PERCEPTUAL, NC_("gradient-blend-color-space", "Perceptual RGB"), NULL },
    { GIMP_GRADIENT_BLEND_RGB_LINEAR, NC_("gradient-blend-color-space", "Linear RGB"), NULL },
    { GIMP_GRADIENT_BLEND_CIE_LAB, NC_("gradient-blend-color-space", "CIE Lab"), NULL },
    { 0, NULL, NULL }
  };

  static GType type = 0;

  if (G_UNLIKELY (! type))
    {
      type = g_enum_register_static ("GimpGradientBlendColorSpace", values);
      gimp_type_set_translation_domain (type, GETTEXT_PACKAGE "-libgimp");
      gimp_type_set_translation_context (type, "gradient-blend-color-space");
      gimp_enum_set_value_descriptions (type, descs);
    }

  return type;
}

GType
gimp_gradient_segment_color_get_type (void)
{
  static const GEnumValue values[] =
  {
    { GIMP_GRADIENT_SEGMENT_RGB, "GIMP_GRADIENT_SEGMENT_RGB", "rgb" },
    { GIMP_GRADIENT_SEGMENT_HSV_CCW, "GIMP_GRADIENT_SEGMENT_HSV_CCW", "hsv-ccw" },
    { GIMP_GRADIENT_SEGMENT_HSV_CW, "GIMP_GRADIENT_SEGMENT_HSV_CW", "hsv-cw" },
    { 0, NULL, NULL }
  };

  static const GimpEnumDesc descs[] =
  {
    { GIMP_GRADIENT_SEGMENT_RGB, NC_("gradient-segment-color", "RGB"), NULL },
    { GIMP_GRADIENT_SEGMENT_HSV_CCW, NC_("gradient-segment-color", "HSV (counter-clockwise hue)"), NULL },
    /* Translators: this is an abbreviated version of "HSV (counter-clockwise hue)".
       Keep it short. */
    { GIMP_GRADIENT_SEGMENT_HSV_CCW, NC_("gradient-segment-color", "HSV (ccw)"), NULL },
    { GIMP_GRADIENT_SEGMENT_HSV_CW, NC_("gradient-segment-color", "HSV (clockwise hue)"), NULL },
    /* Translators: this is an abbreviated version of "HSV (clockwise hue)".
       Keep it short. */
    { GIMP_GRADIENT_SEGMENT_HSV_CW, NC_("gradient-segment-color", "HSV (cw)"), NULL },
    { 0, NULL, NULL }
  };

  static GType type = 0;

  if (G_UNLIKELY (! type))
    {
      type = g_enum_register_static ("GimpGradientSegmentColor", values);
      gimp_type_set_translation_domain (type, GETTEXT_PACKAGE "-libgimp");
      gimp_type_set_translation_context (type, "gradient-segment-color");
      gimp_enum_set_value_descriptions (type, descs);
    }

  return type;
}

GType
gimp_gradient_segment_type_get_type (void)
{
  static const GEnumValue values[] =
  {
    { GIMP_GRADIENT_SEGMENT_LINEAR, "GIMP_GRADIENT_SEGMENT_LINEAR", "linear" },
    { GIMP_GRADIENT_SEGMENT_CURVED, "GIMP_GRADIENT_SEGMENT_CURVED", "curved" },
    { GIMP_GRADIENT_SEGMENT_SINE, "GIMP_GRADIENT_SEGMENT_SINE", "sine" },
    { GIMP_GRADIENT_SEGMENT_SPHERE_INCREASING, "GIMP_GRADIENT_SEGMENT_SPHERE_INCREASING", "sphere-increasing" },
    { GIMP_GRADIENT_SEGMENT_SPHERE_DECREASING, "GIMP_GRADIENT_SEGMENT_SPHERE_DECREASING", "sphere-decreasing" },
    { GIMP_GRADIENT_SEGMENT_STEP, "GIMP_GRADIENT_SEGMENT_STEP", "step" },
    { 0, NULL, NULL }
  };

  static const GimpEnumDesc descs[] =
  {
    { GIMP_GRADIENT_SEGMENT_LINEAR, NC_("gradient-segment-type", "Linear"), NULL },
    { GIMP_GRADIENT_SEGMENT_CURVED, NC_("gradient-segment-type", "Curved"), NULL },
    { GIMP_GRADIENT_SEGMENT_SINE, NC_("gradient-segment-type", "Sinusoidal"), NULL },
    { GIMP_GRADIENT_SEGMENT_SPHERE_INCREASING, NC_("gradient-segment-type", "Spherical (increasing)"), NULL },
    /* Translators: this is an abbreviated version of "Spherical (increasing)".
       Keep it short. */
    { GIMP_GRADIENT_SEGMENT_SPHERE_INCREASING, NC_("gradient-segment-type", "Spherical (inc)"), NULL },
    { GIMP_GRADIENT_SEGMENT_SPHERE_DECREASING, NC_("gradient-segment-type", "Spherical (decreasing)"), NULL },
    /* Translators: this is an abbreviated version of "Spherical (decreasing)".
       Keep it short. */
    { GIMP_GRADIENT_SEGMENT_SPHERE_DECREASING, NC_("gradient-segment-type", "Spherical (dec)"), NULL },
    { GIMP_GRADIENT_SEGMENT_STEP, NC_("gradient-segment-type", "Step"), NULL },
    { 0, NULL, NULL }
  };

  static GType type = 0;

  if (G_UNLIKELY (! type))
    {
      type = g_enum_register_static ("GimpGradientSegmentType", values);
      gimp_type_set_translation_domain (type, GETTEXT_PACKAGE "-libgimp");
      gimp_type_set_translation_context (type, "gradient-segment-type");
      gimp_enum_set_value_descriptions (type, descs);
    }

  return type;
}

GType
gimp_gradient_type_get_type (void)
{
  static const GEnumValue values[] =
  {
    { GIMP_GRADIENT_LINEAR, "GIMP_GRADIENT_LINEAR", "linear" },
    { GIMP_GRADIENT_BILINEAR, "GIMP_GRADIENT_BILINEAR", "bilinear" },
    { GIMP_GRADIENT_RADIAL, "GIMP_GRADIENT_RADIAL", "radial" },
    { GIMP_GRADIENT_SQUARE, "GIMP_GRADIENT_SQUARE", "square" },
    { GIMP_GRADIENT_CONICAL_SYMMETRIC, "GIMP_GRADIENT_CONICAL_SYMMETRIC", "conical-symmetric" },
    { GIMP_GRADIENT_CONICAL_ASYMMETRIC, "GIMP_GRADIENT_CONICAL_ASYMMETRIC", "conical-asymmetric" },
    { GIMP_GRADIENT_SHAPEBURST_ANGULAR, "GIMP_GRADIENT_SHAPEBURST_ANGULAR", "shapeburst-angular" },
    { GIMP_GRADIENT_SHAPEBURST_SPHERICAL, "GIMP_GRADIENT_SHAPEBURST_SPHERICAL", "shapeburst-spherical" },
    { GIMP_GRADIENT_SHAPEBURST_DIMPLED, "GIMP_GRADIENT_SHAPEBURST_DIMPLED", "shapeburst-dimpled" },
    { GIMP_GRADIENT_SPIRAL_CLOCKWISE, "GIMP_GRADIENT_SPIRAL_CLOCKWISE", "spiral-clockwise" },
    { GIMP_GRADIENT_SPIRAL_ANTICLOCKWISE, "GIMP_GRADIENT_SPIRAL_ANTICLOCKWISE", "spiral-anticlockwise" },
    { 0, NULL, NULL }
  };

  static const GimpEnumDesc descs[] =
  {
    { GIMP_GRADIENT_LINEAR, NC_("gradient-type", "Linear"), NULL },
    { GIMP_GRADIENT_BILINEAR, NC_("gradient-type", "Bi-linear"), NULL },
    { GIMP_GRADIENT_RADIAL, NC_("gradient-type", "Radial"), NULL },
    { GIMP_GRADIENT_SQUARE, NC_("gradient-type", "Square"), NULL },
    { GIMP_GRADIENT_CONICAL_SYMMETRIC, NC_("gradient-type", "Conical (symmetric)"), NULL },
    /* Translators: this is an abbreviated version of "Conical (symmetric)".
       Keep it short. */
    { GIMP_GRADIENT_CONICAL_SYMMETRIC, NC_("gradient-type", "Conical (sym)"), NULL },
    { GIMP_GRADIENT_CONICAL_ASYMMETRIC, NC_("gradient-type", "Conical (asymmetric)"), NULL },
    /* Translators: this is an abbreviated version of "Conical (asymmetric)".
       Keep it short. */
    { GIMP_GRADIENT_CONICAL_ASYMMETRIC, NC_("gradient-type", "Conical (asym)"), NULL },
    { GIMP_GRADIENT_SHAPEBURST_ANGULAR, NC_("gradient-type", "Shaped (angular)"), NULL },
    { GIMP_GRADIENT_SHAPEBURST_SPHERICAL, NC_("gradient-type", "Shaped (spherical)"), NULL },
    { GIMP_GRADIENT_SHAPEBURST_DIMPLED, NC_("gradient-type", "Shaped (dimpled)"), NULL },
    { GIMP_GRADIENT_SPIRAL_CLOCKWISE, NC_("gradient-type", "Spiral (clockwise)"), NULL },
    /* Translators: this is an abbreviated version of "Spiral (clockwise)".
       Keep it short. */
    { GIMP_GRADIENT_SPIRAL_CLOCKWISE, NC_("gradient-type", "Spiral (cw)"), NULL },
    { GIMP_GRADIENT_SPIRAL_ANTICLOCKWISE, NC_("gradient-type", "Spiral (counter-clockwise)"), NULL },
    /* Translators: this is an abbreviated version of "Spiral (counter-clockwise)".
       Keep it short. */
    { GIMP_GRADIENT_SPIRAL_ANTICLOCKWISE, NC_("gradient-type", "Spiral (ccw)"), NULL },
    { 0, NULL, NULL }
  };

  static GType type = 0;

  if (G_UNLIKELY (! type))
    {
      type = g_enum_register_static ("GimpGradientType", values);
      gimp_type_set_translation_domain (type, GETTEXT_PACKAGE "-libgimp");
      gimp_type_set_translation_context (type, "gradient-type");
      gimp_enum_set_value_descriptions (type, descs);
    }

  return type;
}

GType
gimp_grid_style_get_type (void)
{
  static const GEnumValue values[] =
  {
    { GIMP_GRID_DOTS, "GIMP_GRID_DOTS", "dots" },
    { GIMP_GRID_INTERSECTIONS, "GIMP_GRID_INTERSECTIONS", "intersections" },
    { GIMP_GRID_ON_OFF_DASH, "GIMP_GRID_ON_OFF_DASH", "on-off-dash" },
    { GIMP_GRID_DOUBLE_DASH, "GIMP_GRID_DOUBLE_DASH", "double-dash" },
    { GIMP_GRID_SOLID, "GIMP_GRID_SOLID", "solid" },
    { 0, NULL, NULL }
  };

  static const GimpEnumDesc descs[] =
  {
    { GIMP_GRID_DOTS, NC_("grid-style", "Intersections (dots)"), NULL },
    { GIMP_GRID_INTERSECTIONS, NC_("grid-style", "Intersections (crosshairs)"), NULL },
    { GIMP_GRID_ON_OFF_DASH, NC_("grid-style", "Dashed"), NULL },
    { GIMP_GRID_DOUBLE_DASH, NC_("grid-style", "Double dashed"), NULL },
    { GIMP_GRID_SOLID, NC_("grid-style", "Solid"), NULL },
    { 0, NULL, NULL }
  };

  static GType type = 0;

  if (G_UNLIKELY (! type))
    {
      type = g_enum_register_static ("GimpGridStyle", values);
      gimp_type_set_translation_domain (type, GETTEXT_PACKAGE "-libgimp");
      gimp_type_set_translation_context (type, "grid-style");
      gimp_enum_set_value_descriptions (type, descs);
    }

  return type;
}

GType
gimp_hue_range_get_type (void)
{
  static const GEnumValue values[] =
  {
    { GIMP_HUE_RANGE_ALL, "GIMP_HUE_RANGE_ALL", "all" },
    { GIMP_HUE_RANGE_RED, "GIMP_HUE_RANGE_RED", "red" },
    { GIMP_HUE_RANGE_YELLOW, "GIMP_HUE_RANGE_YELLOW", "yellow" },
    { GIMP_HUE_RANGE_GREEN, "GIMP_HUE_RANGE_GREEN", "green" },
    { GIMP_HUE_RANGE_CYAN, "GIMP_HUE_RANGE_CYAN", "cyan" },
    { GIMP_HUE_RANGE_BLUE, "GIMP_HUE_RANGE_BLUE", "blue" },
    { GIMP_HUE_RANGE_MAGENTA, "GIMP_HUE_RANGE_MAGENTA", "magenta" },
    { 0, NULL, NULL }
  };

  static const GimpEnumDesc descs[] =
  {
    { GIMP_HUE_RANGE_ALL, "GIMP_HUE_RANGE_ALL", NULL },
    { GIMP_HUE_RANGE_RED, "GIMP_HUE_RANGE_RED", NULL },
    { GIMP_HUE_RANGE_YELLOW, "GIMP_HUE_RANGE_YELLOW", NULL },
    { GIMP_HUE_RANGE_GREEN, "GIMP_HUE_RANGE_GREEN", NULL },
    { GIMP_HUE_RANGE_CYAN, "GIMP_HUE_RANGE_CYAN", NULL },
    { GIMP_HUE_RANGE_BLUE, "GIMP_HUE_RANGE_BLUE", NULL },
    { GIMP_HUE_RANGE_MAGENTA, "GIMP_HUE_RANGE_MAGENTA", NULL },
    { 0, NULL, NULL }
  };

  static GType type = 0;

  if (G_UNLIKELY (! type))
    {
      type = g_enum_register_static ("GimpHueRange", values);
      gimp_type_set_translation_domain (type, GETTEXT_PACKAGE "-libgimp");
      gimp_type_set_translation_context (type, "hue-range");
      gimp_enum_set_value_descriptions (type, descs);
    }

  return type;
}

GType
gimp_icon_type_get_type (void)
{
  static const GEnumValue values[] =
  {
    { GIMP_ICON_TYPE_ICON_NAME, "GIMP_ICON_TYPE_ICON_NAME", "icon-name" },
    { GIMP_ICON_TYPE_PIXBUF, "GIMP_ICON_TYPE_PIXBUF", "pixbuf" },
    { GIMP_ICON_TYPE_IMAGE_FILE, "GIMP_ICON_TYPE_IMAGE_FILE", "image-file" },
    { 0, NULL, NULL }
  };

  static const GimpEnumDesc descs[] =
  {
    { GIMP_ICON_TYPE_ICON_NAME, NC_("icon-type", "Icon name"), NULL },
    { GIMP_ICON_TYPE_PIXBUF, NC_("icon-type", "Pixbuf"), NULL },
    { GIMP_ICON_TYPE_IMAGE_FILE, NC_("icon-type", "Image file"), NULL },
    { 0, NULL, NULL }
  };

  static GType type = 0;

  if (G_UNLIKELY (! type))
    {
      type = g_enum_register_static ("GimpIconType", values);
      gimp_type_set_translation_domain (type, GETTEXT_PACKAGE "-libgimp");
      gimp_type_set_translation_context (type, "icon-type");
      gimp_enum_set_value_descriptions (type, descs);
    }

  return type;
}

GType
gimp_image_base_type_get_type (void)
{
  static const GEnumValue values[] =
  {
    { GIMP_RGB, "GIMP_RGB", "rgb" },
    { GIMP_GRAY, "GIMP_GRAY", "gray" },
    { GIMP_INDEXED, "GIMP_INDEXED", "indexed" },
    { 0, NULL, NULL }
  };

  static const GimpEnumDesc descs[] =
  {
    { GIMP_RGB, NC_("image-base-type", "RGB color"), NULL },
    { GIMP_GRAY, NC_("image-base-type", "Grayscale"), NULL },
    { GIMP_INDEXED, NC_("image-base-type", "Indexed color"), NULL },
    { 0, NULL, NULL }
  };

  static GType type = 0;

  if (G_UNLIKELY (! type))
    {
      type = g_enum_register_static ("GimpImageBaseType", values);
      gimp_type_set_translation_domain (type, GETTEXT_PACKAGE "-libgimp");
      gimp_type_set_translation_context (type, "image-base-type");
      gimp_enum_set_value_descriptions (type, descs);
    }

  return type;
}

GType
gimp_image_type_get_type (void)
{
  static const GEnumValue values[] =
  {
    { GIMP_RGB_IMAGE, "GIMP_RGB_IMAGE", "rgb-image" },
    { GIMP_RGBA_IMAGE, "GIMP_RGBA_IMAGE", "rgba-image" },
    { GIMP_GRAY_IMAGE, "GIMP_GRAY_IMAGE", "gray-image" },
    { GIMP_GRAYA_IMAGE, "GIMP_GRAYA_IMAGE", "graya-image" },
    { GIMP_INDEXED_IMAGE, "GIMP_INDEXED_IMAGE", "indexed-image" },
    { GIMP_INDEXEDA_IMAGE, "GIMP_INDEXEDA_IMAGE", "indexeda-image" },
    { 0, NULL, NULL }
  };

  static const GimpEnumDesc descs[] =
  {
    { GIMP_RGB_IMAGE, NC_("image-type", "RGB"), NULL },
    { GIMP_RGBA_IMAGE, NC_("image-type", "RGB-alpha"), NULL },
    { GIMP_GRAY_IMAGE, NC_("image-type", "Grayscale"), NULL },
    { GIMP_GRAYA_IMAGE, NC_("image-type", "Grayscale-alpha"), NULL },
    { GIMP_INDEXED_IMAGE, NC_("image-type", "Indexed"), NULL },
    { GIMP_INDEXEDA_IMAGE, NC_("image-type", "Indexed-alpha"), NULL },
    { 0, NULL, NULL }
  };

  static GType type = 0;

  if (G_UNLIKELY (! type))
    {
      type = g_enum_register_static ("GimpImageType", values);
      gimp_type_set_translation_domain (type, GETTEXT_PACKAGE "-libgimp");
      gimp_type_set_translation_context (type, "image-type");
      gimp_enum_set_value_descriptions (type, descs);
    }

  return type;
}

GType
gimp_ink_blob_type_get_type (void)
{
  static const GEnumValue values[] =
  {
    { GIMP_INK_BLOB_TYPE_CIRCLE, "GIMP_INK_BLOB_TYPE_CIRCLE", "circle" },
    { GIMP_INK_BLOB_TYPE_SQUARE, "GIMP_INK_BLOB_TYPE_SQUARE", "square" },
    { GIMP_INK_BLOB_TYPE_DIAMOND, "GIMP_INK_BLOB_TYPE_DIAMOND", "diamond" },
    { 0, NULL, NULL }
  };

  static const GimpEnumDesc descs[] =
  {
    { GIMP_INK_BLOB_TYPE_CIRCLE, NC_("ink-blob-type", "Circle"), NULL },
    { GIMP_INK_BLOB_TYPE_SQUARE, NC_("ink-blob-type", "Square"), NULL },
    { GIMP_INK_BLOB_TYPE_DIAMOND, NC_("ink-blob-type", "Diamond"), NULL },
    { 0, NULL, NULL }
  };

  static GType type = 0;

  if (G_UNLIKELY (! type))
    {
      type = g_enum_register_static ("GimpInkBlobType", values);
      gimp_type_set_translation_domain (type, GETTEXT_PACKAGE "-libgimp");
      gimp_type_set_translation_context (type, "ink-blob-type");
      gimp_enum_set_value_descriptions (type, descs);
    }

  return type;
}

GType
gimp_interpolation_type_get_type (void)
{
  static const GEnumValue values[] =
  {
    { GIMP_INTERPOLATION_NONE, "GIMP_INTERPOLATION_NONE", "none" },
    { GIMP_INTERPOLATION_LINEAR, "GIMP_INTERPOLATION_LINEAR", "linear" },
    { GIMP_INTERPOLATION_CUBIC, "GIMP_INTERPOLATION_CUBIC", "cubic" },
    { GIMP_INTERPOLATION_NOHALO, "GIMP_INTERPOLATION_NOHALO", "nohalo" },
    { GIMP_INTERPOLATION_LOHALO, "GIMP_INTERPOLATION_LOHALO", "lohalo" },
    { 0, NULL, NULL }
  };

  static const GimpEnumDesc descs[] =
  {
    { GIMP_INTERPOLATION_NONE, NC_("interpolation-type", "None"), NULL },
    { GIMP_INTERPOLATION_LINEAR, NC_("interpolation-type", "Linear"), NULL },
    { GIMP_INTERPOLATION_CUBIC, NC_("interpolation-type", "Cubic"), NULL },
    { GIMP_INTERPOLATION_NOHALO, NC_("interpolation-type", "NoHalo"), NULL },
    { GIMP_INTERPOLATION_LOHALO, NC_("interpolation-type", "LoHalo"), NULL },
    { 0, NULL, NULL }
  };

  static GType type = 0;

  if (G_UNLIKELY (! type))
    {
      type = g_enum_register_static ("GimpInterpolationType", values);
      gimp_type_set_translation_domain (type, GETTEXT_PACKAGE "-libgimp");
      gimp_type_set_translation_context (type, "interpolation-type");
      gimp_enum_set_value_descriptions (type, descs);
    }

  return type;
}

GType
gimp_join_style_get_type (void)
{
  static const GEnumValue values[] =
  {
    { GIMP_JOIN_MITER, "GIMP_JOIN_MITER", "miter" },
    { GIMP_JOIN_ROUND, "GIMP_JOIN_ROUND", "round" },
    { GIMP_JOIN_BEVEL, "GIMP_JOIN_BEVEL", "bevel" },
    { 0, NULL, NULL }
  };

  static const GimpEnumDesc descs[] =
  {
    { GIMP_JOIN_MITER, NC_("join-style", "Miter"), NULL },
    { GIMP_JOIN_ROUND, NC_("join-style", "Round"), NULL },
    { GIMP_JOIN_BEVEL, NC_("join-style", "Bevel"), NULL },
    { 0, NULL, NULL }
  };

  static GType type = 0;

  if (G_UNLIKELY (! type))
    {
      type = g_enum_register_static ("GimpJoinStyle", values);
      gimp_type_set_translation_domain (type, GETTEXT_PACKAGE "-libgimp");
      gimp_type_set_translation_context (type, "join-style");
      gimp_enum_set_value_descriptions (type, descs);
    }

  return type;
}

GType
gimp_mask_apply_mode_get_type (void)
{
  static const GEnumValue values[] =
  {
    { GIMP_MASK_APPLY, "GIMP_MASK_APPLY", "apply" },
    { GIMP_MASK_DISCARD, "GIMP_MASK_DISCARD", "discard" },
    { 0, NULL, NULL }
  };

  static const GimpEnumDesc descs[] =
  {
    { GIMP_MASK_APPLY, "GIMP_MASK_APPLY", NULL },
    { GIMP_MASK_DISCARD, "GIMP_MASK_DISCARD", NULL },
    { 0, NULL, NULL }
  };

  static GType type = 0;

  if (G_UNLIKELY (! type))
    {
      type = g_enum_register_static ("GimpMaskApplyMode", values);
      gimp_type_set_translation_domain (type, GETTEXT_PACKAGE "-libgimp");
      gimp_type_set_translation_context (type, "mask-apply-mode");
      gimp_enum_set_value_descriptions (type, descs);
    }

  return type;
}

GType
gimp_merge_type_get_type (void)
{
  static const GEnumValue values[] =
  {
    { GIMP_EXPAND_AS_NECESSARY, "GIMP_EXPAND_AS_NECESSARY", "expand-as-necessary" },
    { GIMP_CLIP_TO_IMAGE, "GIMP_CLIP_TO_IMAGE", "clip-to-image" },
    { GIMP_CLIP_TO_BOTTOM_LAYER, "GIMP_CLIP_TO_BOTTOM_LAYER", "clip-to-bottom-layer" },
    { GIMP_FLATTEN_IMAGE, "GIMP_FLATTEN_IMAGE", "flatten-image" },
    { 0, NULL, NULL }
  };

  static const GimpEnumDesc descs[] =
  {
    { GIMP_EXPAND_AS_NECESSARY, NC_("merge-type", "Expanded as necessary"), NULL },
    { GIMP_CLIP_TO_IMAGE, NC_("merge-type", "Clipped to image"), NULL },
    { GIMP_CLIP_TO_BOTTOM_LAYER, NC_("merge-type", "Clipped to bottom layer"), NULL },
    { GIMP_FLATTEN_IMAGE, NC_("merge-type", "Flatten"), NULL },
    { 0, NULL, NULL }
  };

  static GType type = 0;

  if (G_UNLIKELY (! type))
    {
      type = g_enum_register_static ("GimpMergeType", values);
      gimp_type_set_translation_domain (type, GETTEXT_PACKAGE "-libgimp");
      gimp_type_set_translation_context (type, "merge-type");
      gimp_enum_set_value_descriptions (type, descs);
    }

  return type;
}

GType
gimp_message_handler_type_get_type (void)
{
  static const GEnumValue values[] =
  {
    { GIMP_MESSAGE_BOX, "GIMP_MESSAGE_BOX", "message-box" },
    { GIMP_CONSOLE, "GIMP_CONSOLE", "console" },
    { GIMP_ERROR_CONSOLE, "GIMP_ERROR_CONSOLE", "error-console" },
    { 0, NULL, NULL }
  };

  static const GimpEnumDesc descs[] =
  {
    { GIMP_MESSAGE_BOX, "GIMP_MESSAGE_BOX", NULL },
    { GIMP_CONSOLE, "GIMP_CONSOLE", NULL },
    { GIMP_ERROR_CONSOLE, "GIMP_ERROR_CONSOLE", NULL },
    { 0, NULL, NULL }
  };

  static GType type = 0;

  if (G_UNLIKELY (! type))
    {
      type = g_enum_register_static ("GimpMessageHandlerType", values);
      gimp_type_set_translation_domain (type, GETTEXT_PACKAGE "-libgimp");
      gimp_type_set_translation_context (type, "message-handler-type");
      gimp_enum_set_value_descriptions (type, descs);
    }

  return type;
}

GType
gimp_offset_type_get_type (void)
{
  static const GEnumValue values[] =
  {
    { GIMP_OFFSET_COLOR, "GIMP_OFFSET_COLOR", "color" },
    { GIMP_OFFSET_TRANSPARENT, "GIMP_OFFSET_TRANSPARENT", "transparent" },
    { GIMP_OFFSET_WRAP_AROUND, "GIMP_OFFSET_WRAP_AROUND", "wrap-around" },
    { 0, NULL, NULL }
  };

  static const GimpEnumDesc descs[] =
  {
    { GIMP_OFFSET_COLOR, "GIMP_OFFSET_COLOR", NULL },
    { GIMP_OFFSET_TRANSPARENT, "GIMP_OFFSET_TRANSPARENT", NULL },
    { GIMP_OFFSET_WRAP_AROUND, "GIMP_OFFSET_WRAP_AROUND", NULL },
    { 0, NULL, NULL }
  };

  static GType type = 0;

  if (G_UNLIKELY (! type))
    {
      type = g_enum_register_static ("GimpOffsetType", values);
      gimp_type_set_translation_domain (type, GETTEXT_PACKAGE "-libgimp");
      gimp_type_set_translation_context (type, "offset-type");
      gimp_enum_set_value_descriptions (type, descs);
    }

  return type;
}

GType
gimp_orientation_type_get_type (void)
{
  static const GEnumValue values[] =
  {
    { GIMP_ORIENTATION_HORIZONTAL, "GIMP_ORIENTATION_HORIZONTAL", "horizontal" },
    { GIMP_ORIENTATION_VERTICAL, "GIMP_ORIENTATION_VERTICAL", "vertical" },
    { GIMP_ORIENTATION_UNKNOWN, "GIMP_ORIENTATION_UNKNOWN", "unknown" },
    { 0, NULL, NULL }
  };

  static const GimpEnumDesc descs[] =
  {
    { GIMP_ORIENTATION_HORIZONTAL, NC_("orientation-type", "Horizontal"), NULL },
    { GIMP_ORIENTATION_VERTICAL, NC_("orientation-type", "Vertical"), NULL },
    { GIMP_ORIENTATION_UNKNOWN, NC_("orientation-type", "Unknown"), NULL },
    { 0, NULL, NULL }
  };

  static GType type = 0;

  if (G_UNLIKELY (! type))
    {
      type = g_enum_register_static ("GimpOrientationType", values);
      gimp_type_set_translation_domain (type, GETTEXT_PACKAGE "-libgimp");
      gimp_type_set_translation_context (type, "orientation-type");
      gimp_enum_set_value_descriptions (type, descs);
    }

  return type;
}

GType
gimp_paint_application_mode_get_type (void)
{
  static const GEnumValue values[] =
  {
    { GIMP_PAINT_CONSTANT, "GIMP_PAINT_CONSTANT", "constant" },
    { GIMP_PAINT_INCREMENTAL, "GIMP_PAINT_INCREMENTAL", "incremental" },
    { 0, NULL, NULL }
  };

  static const GimpEnumDesc descs[] =
  {
    { GIMP_PAINT_CONSTANT, NC_("paint-application-mode", "Constant"), NULL },
    { GIMP_PAINT_INCREMENTAL, NC_("paint-application-mode", "Incremental"), NULL },
    { 0, NULL, NULL }
  };

  static GType type = 0;

  if (G_UNLIKELY (! type))
    {
      type = g_enum_register_static ("GimpPaintApplicationMode", values);
      gimp_type_set_translation_domain (type, GETTEXT_PACKAGE "-libgimp");
      gimp_type_set_translation_context (type, "paint-application-mode");
      gimp_enum_set_value_descriptions (type, descs);
    }

  return type;
}

GType
gimp_pdb_error_handler_get_type (void)
{
  static const GEnumValue values[] =
  {
    { GIMP_PDB_ERROR_HANDLER_INTERNAL, "GIMP_PDB_ERROR_HANDLER_INTERNAL", "internal" },
    { GIMP_PDB_ERROR_HANDLER_PLUGIN, "GIMP_PDB_ERROR_HANDLER_PLUGIN", "plugin" },
    { 0, NULL, NULL }
  };

  static const GimpEnumDesc descs[] =
  {
    { GIMP_PDB_ERROR_HANDLER_INTERNAL, "GIMP_PDB_ERROR_HANDLER_INTERNAL", NULL },
    { GIMP_PDB_ERROR_HANDLER_PLUGIN, "GIMP_PDB_ERROR_HANDLER_PLUGIN", NULL },
    { 0, NULL, NULL }
  };

  static GType type = 0;

  if (G_UNLIKELY (! type))
    {
      type = g_enum_register_static ("GimpPDBErrorHandler", values);
      gimp_type_set_translation_domain (type, GETTEXT_PACKAGE "-libgimp");
      gimp_type_set_translation_context (type, "pdb-error-handler");
      gimp_enum_set_value_descriptions (type, descs);
    }

  return type;
}

GType
gimp_pdb_proc_type_get_type (void)
{
  static const GEnumValue values[] =
  {
    { GIMP_PDB_PROC_TYPE_INTERNAL, "GIMP_PDB_PROC_TYPE_INTERNAL", "internal" },
    { GIMP_PDB_PROC_TYPE_PLUGIN, "GIMP_PDB_PROC_TYPE_PLUGIN", "plugin" },
    { GIMP_PDB_PROC_TYPE_PERSISTENT, "GIMP_PDB_PROC_TYPE_PERSISTENT", "persistent" },
    { GIMP_PDB_PROC_TYPE_TEMPORARY, "GIMP_PDB_PROC_TYPE_TEMPORARY", "temporary" },
    { 0, NULL, NULL }
  };

  static const GimpEnumDesc descs[] =
  {
    { GIMP_PDB_PROC_TYPE_INTERNAL, NC_("pdb-proc-type", "Internal AmmoOS Image procedure"), NULL },
    { GIMP_PDB_PROC_TYPE_PLUGIN, NC_("pdb-proc-type", "AmmoOS Image Plug-In"), NULL },
    { GIMP_PDB_PROC_TYPE_PERSISTENT, NC_("pdb-proc-type", "AmmoOS Image Persistent Plug-In"), NULL },
    { GIMP_PDB_PROC_TYPE_TEMPORARY, NC_("pdb-proc-type", "Temporary Procedure"), NULL },
    { 0, NULL, NULL }
  };

  static GType type = 0;

  if (G_UNLIKELY (! type))
    {
      type = g_enum_register_static ("GimpPDBProcType", values);
      gimp_type_set_translation_domain (type, GETTEXT_PACKAGE "-libgimp");
      gimp_type_set_translation_context (type, "pdb-proc-type");
      gimp_enum_set_value_descriptions (type, descs);
    }

  return type;
}

GType
gimp_pdb_status_type_get_type (void)
{
  static const GEnumValue values[] =
  {
    { GIMP_PDB_EXECUTION_ERROR, "GIMP_PDB_EXECUTION_ERROR", "execution-error" },
    { GIMP_PDB_CALLING_ERROR, "GIMP_PDB_CALLING_ERROR", "calling-error" },
    { GIMP_PDB_PASS_THROUGH, "GIMP_PDB_PASS_THROUGH", "pass-through" },
    { GIMP_PDB_SUCCESS, "GIMP_PDB_SUCCESS", "success" },
    { GIMP_PDB_CANCEL, "GIMP_PDB_CANCEL", "cancel" },
    { 0, NULL, NULL }
  };

  static const GimpEnumDesc descs[] =
  {
    { GIMP_PDB_EXECUTION_ERROR, "GIMP_PDB_EXECUTION_ERROR", NULL },
    { GIMP_PDB_CALLING_ERROR, "GIMP_PDB_CALLING_ERROR", NULL },
    { GIMP_PDB_PASS_THROUGH, "GIMP_PDB_PASS_THROUGH", NULL },
    { GIMP_PDB_SUCCESS, "GIMP_PDB_SUCCESS", NULL },
    { GIMP_PDB_CANCEL, "GIMP_PDB_CANCEL", NULL },
    { 0, NULL, NULL }
  };

  static GType type = 0;

  if (G_UNLIKELY (! type))
    {
      type = g_enum_register_static ("GimpPDBStatusType", values);
      gimp_type_set_translation_domain (type, GETTEXT_PACKAGE "-libgimp");
      gimp_type_set_translation_context (type, "pdb-status-type");
      gimp_enum_set_value_descriptions (type, descs);
    }

  return type;
}

GType
gimp_precision_get_type (void)
{
  static const GEnumValue values[] =
  {
    { GIMP_PRECISION_U8_LINEAR, "GIMP_PRECISION_U8_LINEAR", "u8-linear" },
    { GIMP_PRECISION_U8_NON_LINEAR, "GIMP_PRECISION_U8_NON_LINEAR", "u8-non-linear" },
    { GIMP_PRECISION_U8_PERCEPTUAL, "GIMP_PRECISION_U8_PERCEPTUAL", "u8-perceptual" },
    { GIMP_PRECISION_U16_LINEAR, "GIMP_PRECISION_U16_LINEAR", "u16-linear" },
    { GIMP_PRECISION_U16_NON_LINEAR, "GIMP_PRECISION_U16_NON_LINEAR", "u16-non-linear" },
    { GIMP_PRECISION_U16_PERCEPTUAL, "GIMP_PRECISION_U16_PERCEPTUAL", "u16-perceptual" },
    { GIMP_PRECISION_U32_LINEAR, "GIMP_PRECISION_U32_LINEAR", "u32-linear" },
    { GIMP_PRECISION_U32_NON_LINEAR, "GIMP_PRECISION_U32_NON_LINEAR", "u32-non-linear" },
    { GIMP_PRECISION_U32_PERCEPTUAL, "GIMP_PRECISION_U32_PERCEPTUAL", "u32-perceptual" },
    { GIMP_PRECISION_HALF_LINEAR, "GIMP_PRECISION_HALF_LINEAR", "half-linear" },
    { GIMP_PRECISION_HALF_NON_LINEAR, "GIMP_PRECISION_HALF_NON_LINEAR", "half-non-linear" },
    { GIMP_PRECISION_HALF_PERCEPTUAL, "GIMP_PRECISION_HALF_PERCEPTUAL", "half-perceptual" },
    { GIMP_PRECISION_FLOAT_LINEAR, "GIMP_PRECISION_FLOAT_LINEAR", "float-linear" },
    { GIMP_PRECISION_FLOAT_NON_LINEAR, "GIMP_PRECISION_FLOAT_NON_LINEAR", "float-non-linear" },
    { GIMP_PRECISION_FLOAT_PERCEPTUAL, "GIMP_PRECISION_FLOAT_PERCEPTUAL", "float-perceptual" },
    { GIMP_PRECISION_DOUBLE_LINEAR, "GIMP_PRECISION_DOUBLE_LINEAR", "double-linear" },
    { GIMP_PRECISION_DOUBLE_NON_LINEAR, "GIMP_PRECISION_DOUBLE_NON_LINEAR", "double-non-linear" },
    { GIMP_PRECISION_DOUBLE_PERCEPTUAL, "GIMP_PRECISION_DOUBLE_PERCEPTUAL", "double-perceptual" },
    { 0, NULL, NULL }
  };

  static const GimpEnumDesc descs[] =
  {
    { GIMP_PRECISION_U8_LINEAR, NC_("precision", "8-bit linear integer"), NULL },
    { GIMP_PRECISION_U8_NON_LINEAR, NC_("precision", "8-bit non-linear integer"), NULL },
    { GIMP_PRECISION_U8_PERCEPTUAL, NC_("precision", "8-bit perceptual integer"), NULL },
    { GIMP_PRECISION_U16_LINEAR, NC_("precision", "16-bit linear integer"), NULL },
    { GIMP_PRECISION_U16_NON_LINEAR, NC_("precision", "16-bit non-linear integer"), NULL },
    { GIMP_PRECISION_U16_PERCEPTUAL, NC_("precision", "16-bit perceptual integer"), NULL },
    { GIMP_PRECISION_U32_LINEAR, NC_("precision", "32-bit linear integer"), NULL },
    { GIMP_PRECISION_U32_NON_LINEAR, NC_("precision", "32-bit non-linear integer"), NULL },
    { GIMP_PRECISION_U32_PERCEPTUAL, NC_("precision", "32-bit perceptual integer"), NULL },
    { GIMP_PRECISION_HALF_LINEAR, NC_("precision", "16-bit linear floating point"), NULL },
    { GIMP_PRECISION_HALF_NON_LINEAR, NC_("precision", "16-bit non-linear floating point"), NULL },
    { GIMP_PRECISION_HALF_PERCEPTUAL, NC_("precision", "16-bit perceptual floating point"), NULL },
    { GIMP_PRECISION_FLOAT_LINEAR, NC_("precision", "32-bit linear floating point"), NULL },
    { GIMP_PRECISION_FLOAT_NON_LINEAR, NC_("precision", "32-bit non-linear floating point"), NULL },
    { GIMP_PRECISION_FLOAT_PERCEPTUAL, NC_("precision", "32-bit perceptual floating point"), NULL },
    { GIMP_PRECISION_DOUBLE_LINEAR, NC_("precision", "64-bit linear floating point"), NULL },
    { GIMP_PRECISION_DOUBLE_NON_LINEAR, NC_("precision", "64-bit non-linear floating point"), NULL },
    { GIMP_PRECISION_DOUBLE_PERCEPTUAL, NC_("precision", "64-bit perceptual floating point"), NULL },
    { 0, NULL, NULL }
  };

  static GType type = 0;

  if (G_UNLIKELY (! type))
    {
      type = g_enum_register_static ("GimpPrecision", values);
      gimp_type_set_translation_domain (type, GETTEXT_PACKAGE "-libgimp");
      gimp_type_set_translation_context (type, "precision");
      gimp_enum_set_value_descriptions (type, descs);
    }

  return type;
}

GType
gimp_procedure_sensitivity_mask_get_type (void)
{
  static const GFlagsValue values[] =
  {
    { GIMP_PROCEDURE_SENSITIVE_DRAWABLE, "GIMP_PROCEDURE_SENSITIVE_DRAWABLE", "drawable" },
    { GIMP_PROCEDURE_SENSITIVE_DRAWABLES, "GIMP_PROCEDURE_SENSITIVE_DRAWABLES", "drawables" },
    { GIMP_PROCEDURE_SENSITIVE_NO_DRAWABLES, "GIMP_PROCEDURE_SENSITIVE_NO_DRAWABLES", "no-drawables" },
    { GIMP_PROCEDURE_SENSITIVE_NO_IMAGE, "GIMP_PROCEDURE_SENSITIVE_NO_IMAGE", "no-image" },
    { GIMP_PROCEDURE_SENSITIVE_ALWAYS, "GIMP_PROCEDURE_SENSITIVE_ALWAYS", "always" },
    { 0, NULL, NULL }
  };

  static const GimpFlagsDesc descs[] =
  {
    { GIMP_PROCEDURE_SENSITIVE_DRAWABLE, "GIMP_PROCEDURE_SENSITIVE_DRAWABLE", NULL },
    { GIMP_PROCEDURE_SENSITIVE_DRAWABLES, "GIMP_PROCEDURE_SENSITIVE_DRAWABLES", NULL },
    { GIMP_PROCEDURE_SENSITIVE_NO_DRAWABLES, "GIMP_PROCEDURE_SENSITIVE_NO_DRAWABLES", NULL },
    { GIMP_PROCEDURE_SENSITIVE_NO_IMAGE, "GIMP_PROCEDURE_SENSITIVE_NO_IMAGE", NULL },
    { GIMP_PROCEDURE_SENSITIVE_ALWAYS, "GIMP_PROCEDURE_SENSITIVE_ALWAYS", NULL },
    { 0, NULL, NULL }
  };

  static GType type = 0;

  if (G_UNLIKELY (! type))
    {
      type = g_flags_register_static ("GimpProcedureSensitivityMask", values);
      gimp_type_set_translation_domain (type, GETTEXT_PACKAGE "-libgimp");
      gimp_type_set_translation_context (type, "procedure-sensitivity-mask");
      gimp_flags_set_value_descriptions (type, descs);
    }

  return type;
}

GType
gimp_progress_command_get_type (void)
{
  static const GEnumValue values[] =
  {
    { GIMP_PROGRESS_COMMAND_START, "GIMP_PROGRESS_COMMAND_START", "start" },
    { GIMP_PROGRESS_COMMAND_END, "GIMP_PROGRESS_COMMAND_END", "end" },
    { GIMP_PROGRESS_COMMAND_SET_TEXT, "GIMP_PROGRESS_COMMAND_SET_TEXT", "set-text" },
    { GIMP_PROGRESS_COMMAND_SET_VALUE, "GIMP_PROGRESS_COMMAND_SET_VALUE", "set-value" },
    { GIMP_PROGRESS_COMMAND_PULSE, "GIMP_PROGRESS_COMMAND_PULSE", "pulse" },
    { GIMP_PROGRESS_COMMAND_GET_WINDOW, "GIMP_PROGRESS_COMMAND_GET_WINDOW", "get-window" },
    { 0, NULL, NULL }
  };

  static const GimpEnumDesc descs[] =
  {
    { GIMP_PROGRESS_COMMAND_START, "GIMP_PROGRESS_COMMAND_START", NULL },
    { GIMP_PROGRESS_COMMAND_END, "GIMP_PROGRESS_COMMAND_END", NULL },
    { GIMP_PROGRESS_COMMAND_SET_TEXT, "GIMP_PROGRESS_COMMAND_SET_TEXT", NULL },
    { GIMP_PROGRESS_COMMAND_SET_VALUE, "GIMP_PROGRESS_COMMAND_SET_VALUE", NULL },
    { GIMP_PROGRESS_COMMAND_PULSE, "GIMP_PROGRESS_COMMAND_PULSE", NULL },
    { GIMP_PROGRESS_COMMAND_GET_WINDOW, "GIMP_PROGRESS_COMMAND_GET_WINDOW", NULL },
    { 0, NULL, NULL }
  };

  static GType type = 0;

  if (G_UNLIKELY (! type))
    {
      type = g_enum_register_static ("GimpProgressCommand", values);
      gimp_type_set_translation_domain (type, GETTEXT_PACKAGE "-libgimp");
      gimp_type_set_translation_context (type, "progress-command");
      gimp_enum_set_value_descriptions (type, descs);
    }

  return type;
}

GType
gimp_repeat_mode_get_type (void)
{
  static const GEnumValue values[] =
  {
    { GIMP_REPEAT_NONE, "GIMP_REPEAT_NONE", "none" },
    { GIMP_REPEAT_TRUNCATE, "GIMP_REPEAT_TRUNCATE", "truncate" },
    { GIMP_REPEAT_SAWTOOTH, "GIMP_REPEAT_SAWTOOTH", "sawtooth" },
    { GIMP_REPEAT_TRIANGULAR, "GIMP_REPEAT_TRIANGULAR", "triangular" },
    { 0, NULL, NULL }
  };

  static const GimpEnumDesc descs[] =
  {
    { GIMP_REPEAT_NONE, NC_("repeat-mode", "None (extend)"), NULL },
    { GIMP_REPEAT_TRUNCATE, NC_("repeat-mode", "None (truncate)"), NULL },
    { GIMP_REPEAT_SAWTOOTH, NC_("repeat-mode", "Sawtooth wave"), NULL },
    { GIMP_REPEAT_TRIANGULAR, NC_("repeat-mode", "Triangular wave"), NULL },
    { 0, NULL, NULL }
  };

  static GType type = 0;

  if (G_UNLIKELY (! type))
    {
      type = g_enum_register_static ("GimpRepeatMode", values);
      gimp_type_set_translation_domain (type, GETTEXT_PACKAGE "-libgimp");
      gimp_type_set_translation_context (type, "repeat-mode");
      gimp_enum_set_value_descriptions (type, descs);
    }

  return type;
}

GType
gimp_rotation_type_get_type (void)
{
  static const GEnumValue values[] =
  {
    { GIMP_ROTATE_DEGREES90, "GIMP_ROTATE_DEGREES90", "degrees90" },
    { GIMP_ROTATE_DEGREES180, "GIMP_ROTATE_DEGREES180", "degrees180" },
    { GIMP_ROTATE_DEGREES270, "GIMP_ROTATE_DEGREES270", "degrees270" },
    { 0, NULL, NULL }
  };

  static const GimpEnumDesc descs[] =
  {
    { GIMP_ROTATE_DEGREES90, "GIMP_ROTATE_DEGREES90", NULL },
    { GIMP_ROTATE_DEGREES180, "GIMP_ROTATE_DEGREES180", NULL },
    { GIMP_ROTATE_DEGREES270, "GIMP_ROTATE_DEGREES270", NULL },
    { 0, NULL, NULL }
  };

  static GType type = 0;

  if (G_UNLIKELY (! type))
    {
      type = g_enum_register_static ("GimpRotationType", values);
      gimp_type_set_translation_domain (type, GETTEXT_PACKAGE "-libgimp");
      gimp_type_set_translation_context (type, "rotation-type");
      gimp_enum_set_value_descriptions (type, descs);
    }

  return type;
}

GType
gimp_run_mode_get_type (void)
{
  static const GEnumValue values[] =
  {
    { GIMP_RUN_INTERACTIVE, "GIMP_RUN_INTERACTIVE", "interactive" },
    { GIMP_RUN_NONINTERACTIVE, "GIMP_RUN_NONINTERACTIVE", "noninteractive" },
    { GIMP_RUN_WITH_LAST_VALS, "GIMP_RUN_WITH_LAST_VALS", "with-last-vals" },
    { 0, NULL, NULL }
  };

  static const GimpEnumDesc descs[] =
  {
    { GIMP_RUN_INTERACTIVE, NC_("run-mode", "Run interactively"), NULL },
    { GIMP_RUN_NONINTERACTIVE, NC_("run-mode", "Run non-interactively"), NULL },
    { GIMP_RUN_WITH_LAST_VALS, NC_("run-mode", "Run with last used values"), NULL },
    { 0, NULL, NULL }
  };

  static GType type = 0;

  if (G_UNLIKELY (! type))
    {
      type = g_enum_register_static ("GimpRunMode", values);
      gimp_type_set_translation_domain (type, GETTEXT_PACKAGE "-libgimp");
      gimp_type_set_translation_context (type, "run-mode");
      gimp_enum_set_value_descriptions (type, descs);
    }

  return type;
}

GType
gimp_select_criterion_get_type (void)
{
  static const GEnumValue values[] =
  {
    { GIMP_SELECT_CRITERION_COMPOSITE, "GIMP_SELECT_CRITERION_COMPOSITE", "composite" },
    { GIMP_SELECT_CRITERION_RGB_RED, "GIMP_SELECT_CRITERION_RGB_RED", "rgb-red" },
    { GIMP_SELECT_CRITERION_RGB_GREEN, "GIMP_SELECT_CRITERION_RGB_GREEN", "rgb-green" },
    { GIMP_SELECT_CRITERION_RGB_BLUE, "GIMP_SELECT_CRITERION_RGB_BLUE", "rgb-blue" },
    { GIMP_SELECT_CRITERION_HSV_HUE, "GIMP_SELECT_CRITERION_HSV_HUE", "hsv-hue" },
    { GIMP_SELECT_CRITERION_HSV_SATURATION, "GIMP_SELECT_CRITERION_HSV_SATURATION", "hsv-saturation" },
    { GIMP_SELECT_CRITERION_HSV_VALUE, "GIMP_SELECT_CRITERION_HSV_VALUE", "hsv-value" },
    { GIMP_SELECT_CRITERION_LCH_LIGHTNESS, "GIMP_SELECT_CRITERION_LCH_LIGHTNESS", "lch-lightness" },
    { GIMP_SELECT_CRITERION_LCH_CHROMA, "GIMP_SELECT_CRITERION_LCH_CHROMA", "lch-chroma" },
    { GIMP_SELECT_CRITERION_LCH_HUE, "GIMP_SELECT_CRITERION_LCH_HUE", "lch-hue" },
    { GIMP_SELECT_CRITERION_ALPHA, "GIMP_SELECT_CRITERION_ALPHA", "alpha" },
    { 0, NULL, NULL }
  };

  static const GimpEnumDesc descs[] =
  {
    { GIMP_SELECT_CRITERION_COMPOSITE, NC_("select-criterion", "Composite"), NULL },
    { GIMP_SELECT_CRITERION_RGB_RED, NC_("select-criterion", "Red"), NULL },
    { GIMP_SELECT_CRITERION_RGB_GREEN, NC_("select-criterion", "Green"), NULL },
    { GIMP_SELECT_CRITERION_RGB_BLUE, NC_("select-criterion", "Blue"), NULL },
    { GIMP_SELECT_CRITERION_HSV_HUE, NC_("select-criterion", "HSV Hue"), NULL },
    { GIMP_SELECT_CRITERION_HSV_SATURATION, NC_("select-criterion", "HSV Saturation"), NULL },
    { GIMP_SELECT_CRITERION_HSV_VALUE, NC_("select-criterion", "HSV Value"), NULL },
    { GIMP_SELECT_CRITERION_LCH_LIGHTNESS, NC_("select-criterion", "LCh Lightness"), NULL },
    { GIMP_SELECT_CRITERION_LCH_CHROMA, NC_("select-criterion", "LCh Chroma"), NULL },
    { GIMP_SELECT_CRITERION_LCH_HUE, NC_("select-criterion", "LCh Hue"), NULL },
    { GIMP_SELECT_CRITERION_ALPHA, NC_("select-criterion", "Alpha"), NULL },
    { 0, NULL, NULL }
  };

  static GType type = 0;

  if (G_UNLIKELY (! type))
    {
      type = g_enum_register_static ("GimpSelectCriterion", values);
      gimp_type_set_translation_domain (type, GETTEXT_PACKAGE "-libgimp");
      gimp_type_set_translation_context (type, "select-criterion");
      gimp_enum_set_value_descriptions (type, descs);
    }

  return type;
}

GType
gimp_size_type_get_type (void)
{
  static const GEnumValue values[] =
  {
    { GIMP_PIXELS, "GIMP_PIXELS", "pixels" },
    { GIMP_POINTS, "GIMP_POINTS", "points" },
    { 0, NULL, NULL }
  };

  static const GimpEnumDesc descs[] =
  {
    { GIMP_PIXELS, NC_("size-type", "Pixels"), NULL },
    { GIMP_POINTS, NC_("size-type", "Points"), NULL },
    { 0, NULL, NULL }
  };

  static GType type = 0;

  if (G_UNLIKELY (! type))
    {
      type = g_enum_register_static ("GimpSizeType", values);
      gimp_type_set_translation_domain (type, GETTEXT_PACKAGE "-libgimp");
      gimp_type_set_translation_context (type, "size-type");
      gimp_enum_set_value_descriptions (type, descs);
    }

  return type;
}

GType
gimp_stack_trace_mode_get_type (void)
{
  static const GEnumValue values[] =
  {
    { GIMP_STACK_TRACE_NEVER, "GIMP_STACK_TRACE_NEVER", "never" },
    { GIMP_STACK_TRACE_QUERY, "GIMP_STACK_TRACE_QUERY", "query" },
    { GIMP_STACK_TRACE_ALWAYS, "GIMP_STACK_TRACE_ALWAYS", "always" },
    { 0, NULL, NULL }
  };

  static const GimpEnumDesc descs[] =
  {
    { GIMP_STACK_TRACE_NEVER, "GIMP_STACK_TRACE_NEVER", NULL },
    { GIMP_STACK_TRACE_QUERY, "GIMP_STACK_TRACE_QUERY", NULL },
    { GIMP_STACK_TRACE_ALWAYS, "GIMP_STACK_TRACE_ALWAYS", NULL },
    { 0, NULL, NULL }
  };

  static GType type = 0;

  if (G_UNLIKELY (! type))
    {
      type = g_enum_register_static ("GimpStackTraceMode", values);
      gimp_type_set_translation_domain (type, GETTEXT_PACKAGE "-libgimp");
      gimp_type_set_translation_context (type, "stack-trace-mode");
      gimp_enum_set_value_descriptions (type, descs);
    }

  return type;
}

GType
gimp_stroke_method_get_type (void)
{
  static const GEnumValue values[] =
  {
    { GIMP_STROKE_LINE, "GIMP_STROKE_LINE", "line" },
    { GIMP_STROKE_PAINT_METHOD, "GIMP_STROKE_PAINT_METHOD", "paint-method" },
    { 0, NULL, NULL }
  };

  static const GimpEnumDesc descs[] =
  {
    { GIMP_STROKE_LINE, NC_("stroke-method", "Stroke line"), NULL },
    { GIMP_STROKE_PAINT_METHOD, NC_("stroke-method", "Stroke with a paint tool"), NULL },
    { 0, NULL, NULL }
  };

  static GType type = 0;

  if (G_UNLIKELY (! type))
    {
      type = g_enum_register_static ("GimpStrokeMethod", values);
      gimp_type_set_translation_domain (type, GETTEXT_PACKAGE "-libgimp");
      gimp_type_set_translation_context (type, "stroke-method");
      gimp_enum_set_value_descriptions (type, descs);
    }

  return type;
}

GType
gimp_text_direction_get_type (void)
{
  static const GEnumValue values[] =
  {
    { GIMP_TEXT_DIRECTION_LTR, "GIMP_TEXT_DIRECTION_LTR", "ltr" },
    { GIMP_TEXT_DIRECTION_RTL, "GIMP_TEXT_DIRECTION_RTL", "rtl" },
    { GIMP_TEXT_DIRECTION_TTB_RTL, "GIMP_TEXT_DIRECTION_TTB_RTL", "ttb-rtl" },
    { GIMP_TEXT_DIRECTION_TTB_RTL_UPRIGHT, "GIMP_TEXT_DIRECTION_TTB_RTL_UPRIGHT", "ttb-rtl-upright" },
    { GIMP_TEXT_DIRECTION_TTB_LTR, "GIMP_TEXT_DIRECTION_TTB_LTR", "ttb-ltr" },
    { GIMP_TEXT_DIRECTION_TTB_LTR_UPRIGHT, "GIMP_TEXT_DIRECTION_TTB_LTR_UPRIGHT", "ttb-ltr-upright" },
    { 0, NULL, NULL }
  };

  static const GimpEnumDesc descs[] =
  {
    { GIMP_TEXT_DIRECTION_LTR, NC_("text-direction", "From left to right"), NULL },
    { GIMP_TEXT_DIRECTION_RTL, NC_("text-direction", "From right to left"), NULL },
    { GIMP_TEXT_DIRECTION_TTB_RTL, NC_("text-direction", "Vertical, right to left (mixed orientation)"), NULL },
    { GIMP_TEXT_DIRECTION_TTB_RTL_UPRIGHT, NC_("text-direction", "Vertical, right to left (upright orientation)"), NULL },
    { GIMP_TEXT_DIRECTION_TTB_LTR, NC_("text-direction", "Vertical, left to right (mixed orientation)"), NULL },
    { GIMP_TEXT_DIRECTION_TTB_LTR_UPRIGHT, NC_("text-direction", "Vertical, left to right (upright orientation)"), NULL },
    { 0, NULL, NULL }
  };

  static GType type = 0;

  if (G_UNLIKELY (! type))
    {
      type = g_enum_register_static ("GimpTextDirection", values);
      gimp_type_set_translation_domain (type, GETTEXT_PACKAGE "-libgimp");
      gimp_type_set_translation_context (type, "text-direction");
      gimp_enum_set_value_descriptions (type, descs);
    }

  return type;
}

GType
gimp_text_hint_style_get_type (void)
{
  static const GEnumValue values[] =
  {
    { GIMP_TEXT_HINT_STYLE_NONE, "GIMP_TEXT_HINT_STYLE_NONE", "none" },
    { GIMP_TEXT_HINT_STYLE_SLIGHT, "GIMP_TEXT_HINT_STYLE_SLIGHT", "slight" },
    { GIMP_TEXT_HINT_STYLE_MEDIUM, "GIMP_TEXT_HINT_STYLE_MEDIUM", "medium" },
    { GIMP_TEXT_HINT_STYLE_FULL, "GIMP_TEXT_HINT_STYLE_FULL", "full" },
    { 0, NULL, NULL }
  };

  static const GimpEnumDesc descs[] =
  {
    { GIMP_TEXT_HINT_STYLE_NONE, NC_("text-hint-style", "None"), NULL },
    { GIMP_TEXT_HINT_STYLE_SLIGHT, NC_("text-hint-style", "Slight"), NULL },
    { GIMP_TEXT_HINT_STYLE_MEDIUM, NC_("text-hint-style", "Medium"), NULL },
    { GIMP_TEXT_HINT_STYLE_FULL, NC_("text-hint-style", "Full"), NULL },
    { 0, NULL, NULL }
  };

  static GType type = 0;

  if (G_UNLIKELY (! type))
    {
      type = g_enum_register_static ("GimpTextHintStyle", values);
      gimp_type_set_translation_domain (type, GETTEXT_PACKAGE "-libgimp");
      gimp_type_set_translation_context (type, "text-hint-style");
      gimp_enum_set_value_descriptions (type, descs);
    }

  return type;
}

GType
gimp_text_justification_get_type (void)
{
  static const GEnumValue values[] =
  {
    { GIMP_TEXT_JUSTIFY_LEFT, "GIMP_TEXT_JUSTIFY_LEFT", "left" },
    { GIMP_TEXT_JUSTIFY_RIGHT, "GIMP_TEXT_JUSTIFY_RIGHT", "right" },
    { GIMP_TEXT_JUSTIFY_CENTER, "GIMP_TEXT_JUSTIFY_CENTER", "center" },
    { GIMP_TEXT_JUSTIFY_FILL, "GIMP_TEXT_JUSTIFY_FILL", "fill" },
    { 0, NULL, NULL }
  };

  static const GimpEnumDesc descs[] =
  {
    { GIMP_TEXT_JUSTIFY_LEFT, NC_("text-justification", "Left justified"), NULL },
    { GIMP_TEXT_JUSTIFY_RIGHT, NC_("text-justification", "Right justified"), NULL },
    { GIMP_TEXT_JUSTIFY_CENTER, NC_("text-justification", "Centered"), NULL },
    { GIMP_TEXT_JUSTIFY_FILL, NC_("text-justification", "Filled"), NULL },
    { 0, NULL, NULL }
  };

  static GType type = 0;

  if (G_UNLIKELY (! type))
    {
      type = g_enum_register_static ("GimpTextJustification", values);
      gimp_type_set_translation_domain (type, GETTEXT_PACKAGE "-libgimp");
      gimp_type_set_translation_context (type, "text-justification");
      gimp_enum_set_value_descriptions (type, descs);
    }

  return type;
}

GType
gimp_text_outline_get_type (void)
{
  static const GEnumValue values[] =
  {
    { GIMP_TEXT_OUTLINE_NONE, "GIMP_TEXT_OUTLINE_NONE", "none" },
    { GIMP_TEXT_OUTLINE_STROKE_ONLY, "GIMP_TEXT_OUTLINE_STROKE_ONLY", "stroke-only" },
    { GIMP_TEXT_OUTLINE_STROKE_FILL, "GIMP_TEXT_OUTLINE_STROKE_FILL", "stroke-fill" },
    { 0, NULL, NULL }
  };

  static const GimpEnumDesc descs[] =
  {
    { GIMP_TEXT_OUTLINE_NONE, NC_("text-outline", "Filled"), NULL },
    { GIMP_TEXT_OUTLINE_STROKE_ONLY, NC_("text-outline", "Outlined"), NULL },
    { GIMP_TEXT_OUTLINE_STROKE_FILL, NC_("text-outline", "Outlined and filled"), NULL },
    { 0, NULL, NULL }
  };

  static GType type = 0;

  if (G_UNLIKELY (! type))
    {
      type = g_enum_register_static ("GimpTextOutline", values);
      gimp_type_set_translation_domain (type, GETTEXT_PACKAGE "-libgimp");
      gimp_type_set_translation_context (type, "text-outline");
      gimp_enum_set_value_descriptions (type, descs);
    }

  return type;
}

GType
gimp_text_outline_direction_get_type (void)
{
  static const GEnumValue values[] =
  {
    { GIMP_TEXT_OUTLINE_DIRECTION_OUTER, "GIMP_TEXT_OUTLINE_DIRECTION_OUTER", "outer" },
    { GIMP_TEXT_OUTLINE_DIRECTION_INNER, "GIMP_TEXT_OUTLINE_DIRECTION_INNER", "inner" },
    { GIMP_TEXT_OUTLINE_DIRECTION_CENTERED, "GIMP_TEXT_OUTLINE_DIRECTION_CENTERED", "centered" },
    { 0, NULL, NULL }
  };

  static const GimpEnumDesc descs[] =
  {
    { GIMP_TEXT_OUTLINE_DIRECTION_OUTER, NC_("text-outline-direction", "Outer"), NULL },
    { GIMP_TEXT_OUTLINE_DIRECTION_INNER, NC_("text-outline-direction", "Inner"), NULL },
    { GIMP_TEXT_OUTLINE_DIRECTION_CENTERED, NC_("text-outline-direction", "Centered"), NULL },
    { 0, NULL, NULL }
  };

  static GType type = 0;

  if (G_UNLIKELY (! type))
    {
      type = g_enum_register_static ("GimpTextOutlineDirection", values);
      gimp_type_set_translation_domain (type, GETTEXT_PACKAGE "-libgimp");
      gimp_type_set_translation_context (type, "text-outline-direction");
      gimp_enum_set_value_descriptions (type, descs);
    }

  return type;
}

GType
gimp_transfer_mode_get_type (void)
{
  static const GEnumValue values[] =
  {
    { GIMP_TRANSFER_SHADOWS, "GIMP_TRANSFER_SHADOWS", "shadows" },
    { GIMP_TRANSFER_MIDTONES, "GIMP_TRANSFER_MIDTONES", "midtones" },
    { GIMP_TRANSFER_HIGHLIGHTS, "GIMP_TRANSFER_HIGHLIGHTS", "highlights" },
    { 0, NULL, NULL }
  };

  static const GimpEnumDesc descs[] =
  {
    { GIMP_TRANSFER_SHADOWS, NC_("transfer-mode", "Shadows"), NULL },
    { GIMP_TRANSFER_MIDTONES, NC_("transfer-mode", "Midtones"), NULL },
    { GIMP_TRANSFER_HIGHLIGHTS, NC_("transfer-mode", "Highlights"), NULL },
    { 0, NULL, NULL }
  };

  static GType type = 0;

  if (G_UNLIKELY (! type))
    {
      type = g_enum_register_static ("GimpTransferMode", values);
      gimp_type_set_translation_domain (type, GETTEXT_PACKAGE "-libgimp");
      gimp_type_set_translation_context (type, "transfer-mode");
      gimp_enum_set_value_descriptions (type, descs);
    }

  return type;
}

GType
gimp_transform_direction_get_type (void)
{
  static const GEnumValue values[] =
  {
    { GIMP_TRANSFORM_FORWARD, "GIMP_TRANSFORM_FORWARD", "forward" },
    { GIMP_TRANSFORM_BACKWARD, "GIMP_TRANSFORM_BACKWARD", "backward" },
    { 0, NULL, NULL }
  };

  static const GimpEnumDesc descs[] =
  {
    { GIMP_TRANSFORM_FORWARD, NC_("transform-direction", "Normal (Forward)"), NULL },
    { GIMP_TRANSFORM_BACKWARD, NC_("transform-direction", "Corrective (Backward)"), NULL },
    { 0, NULL, NULL }
  };

  static GType type = 0;

  if (G_UNLIKELY (! type))
    {
      type = g_enum_register_static ("GimpTransformDirection", values);
      gimp_type_set_translation_domain (type, GETTEXT_PACKAGE "-libgimp");
      gimp_type_set_translation_context (type, "transform-direction");
      gimp_enum_set_value_descriptions (type, descs);
    }

  return type;
}

GType
gimp_transform_resize_get_type (void)
{
  static const GEnumValue values[] =
  {
    { GIMP_TRANSFORM_RESIZE_ADJUST, "GIMP_TRANSFORM_RESIZE_ADJUST", "adjust" },
    { GIMP_TRANSFORM_RESIZE_CLIP, "GIMP_TRANSFORM_RESIZE_CLIP", "clip" },
    { GIMP_TRANSFORM_RESIZE_CROP, "GIMP_TRANSFORM_RESIZE_CROP", "crop" },
    { GIMP_TRANSFORM_RESIZE_CROP_WITH_ASPECT, "GIMP_TRANSFORM_RESIZE_CROP_WITH_ASPECT", "crop-with-aspect" },
    { 0, NULL, NULL }
  };

  static const GimpEnumDesc descs[] =
  {
    { GIMP_TRANSFORM_RESIZE_ADJUST, NC_("transform-resize", "Adjust"), NULL },
    { GIMP_TRANSFORM_RESIZE_CLIP, NC_("transform-resize", "Clip"), NULL },
    { GIMP_TRANSFORM_RESIZE_CROP, NC_("transform-resize", "Crop to result"), NULL },
    { GIMP_TRANSFORM_RESIZE_CROP_WITH_ASPECT, NC_("transform-resize", "Crop with aspect"), NULL },
    { 0, NULL, NULL }
  };

  static GType type = 0;

  if (G_UNLIKELY (! type))
    {
      type = g_enum_register_static ("GimpTransformResize", values);
      gimp_type_set_translation_domain (type, GETTEXT_PACKAGE "-libgimp");
      gimp_type_set_translation_context (type, "transform-resize");
      gimp_enum_set_value_descriptions (type, descs);
    }

  return type;
}

GType
gimp_path_stroke_type_get_type (void)
{
  static const GEnumValue values[] =
  {
    { GIMP_PATH_STROKE_TYPE_BEZIER, "GIMP_PATH_STROKE_TYPE_BEZIER", "bezier" },
    { 0, NULL, NULL }
  };

  static const GimpEnumDesc descs[] =
  {
    { GIMP_PATH_STROKE_TYPE_BEZIER, "GIMP_PATH_STROKE_TYPE_BEZIER", NULL },
    { 0, NULL, NULL }
  };

  static GType type = 0;

  if (G_UNLIKELY (! type))
    {
      type = g_enum_register_static ("GimpPathStrokeType", values);
      gimp_type_set_translation_domain (type, GETTEXT_PACKAGE "-libgimp");
      gimp_type_set_translation_context (type, "path-stroke-type");
      gimp_enum_set_value_descriptions (type, descs);
    }

  return type;
}

GType
gimp_export_capabilities_get_type (void)
{
  static const GFlagsValue values[] =
  {
    { GIMP_EXPORT_CAN_HANDLE_RGB, "GIMP_EXPORT_CAN_HANDLE_RGB", "can-handle-rgb" },
    { GIMP_EXPORT_CAN_HANDLE_GRAY, "GIMP_EXPORT_CAN_HANDLE_GRAY", "can-handle-gray" },
    { GIMP_EXPORT_CAN_HANDLE_INDEXED, "GIMP_EXPORT_CAN_HANDLE_INDEXED", "can-handle-indexed" },
    { GIMP_EXPORT_CAN_HANDLE_BITMAP, "GIMP_EXPORT_CAN_HANDLE_BITMAP", "can-handle-bitmap" },
    { GIMP_EXPORT_CAN_HANDLE_ALPHA, "GIMP_EXPORT_CAN_HANDLE_ALPHA", "can-handle-alpha" },
    { GIMP_EXPORT_CAN_HANDLE_LAYERS, "GIMP_EXPORT_CAN_HANDLE_LAYERS", "can-handle-layers" },
    { GIMP_EXPORT_CAN_HANDLE_LAYERS_AS_ANIMATION, "GIMP_EXPORT_CAN_HANDLE_LAYERS_AS_ANIMATION", "can-handle-layers-as-animation" },
    { GIMP_EXPORT_CAN_HANDLE_LAYER_MASKS, "GIMP_EXPORT_CAN_HANDLE_LAYER_MASKS", "can-handle-layer-masks" },
    { GIMP_EXPORT_CAN_HANDLE_LAYER_EFFECTS, "GIMP_EXPORT_CAN_HANDLE_LAYER_EFFECTS", "can-handle-layer-effects" },
    { GIMP_EXPORT_NEEDS_ALPHA, "GIMP_EXPORT_NEEDS_ALPHA", "needs-alpha" },
    { GIMP_EXPORT_NEEDS_CROP, "GIMP_EXPORT_NEEDS_CROP", "needs-crop" },
    { 0, NULL, NULL }
  };

  static const GimpFlagsDesc descs[] =
  {
    { GIMP_EXPORT_CAN_HANDLE_RGB, "GIMP_EXPORT_CAN_HANDLE_RGB", NULL },
    { GIMP_EXPORT_CAN_HANDLE_GRAY, "GIMP_EXPORT_CAN_HANDLE_GRAY", NULL },
    { GIMP_EXPORT_CAN_HANDLE_INDEXED, "GIMP_EXPORT_CAN_HANDLE_INDEXED", NULL },
    { GIMP_EXPORT_CAN_HANDLE_BITMAP, "GIMP_EXPORT_CAN_HANDLE_BITMAP", NULL },
    { GIMP_EXPORT_CAN_HANDLE_ALPHA, "GIMP_EXPORT_CAN_HANDLE_ALPHA", NULL },
    { GIMP_EXPORT_CAN_HANDLE_LAYERS, "GIMP_EXPORT_CAN_HANDLE_LAYERS", NULL },
    { GIMP_EXPORT_CAN_HANDLE_LAYERS_AS_ANIMATION, "GIMP_EXPORT_CAN_HANDLE_LAYERS_AS_ANIMATION", NULL },
    { GIMP_EXPORT_CAN_HANDLE_LAYER_MASKS, "GIMP_EXPORT_CAN_HANDLE_LAYER_MASKS", NULL },
    { GIMP_EXPORT_CAN_HANDLE_LAYER_EFFECTS, "GIMP_EXPORT_CAN_HANDLE_LAYER_EFFECTS", NULL },
    { GIMP_EXPORT_NEEDS_ALPHA, "GIMP_EXPORT_NEEDS_ALPHA", NULL },
    { GIMP_EXPORT_NEEDS_CROP, "GIMP_EXPORT_NEEDS_CROP", NULL },
    { 0, NULL, NULL }
  };

  static GType type = 0;

  if (G_UNLIKELY (! type))
    {
      type = g_flags_register_static ("GimpExportCapabilities", values);
      gimp_type_set_translation_domain (type, GETTEXT_PACKAGE "-libgimp");
      gimp_type_set_translation_context (type, "export-capabilities");
      gimp_flags_set_value_descriptions (type, descs);
    }

  return type;
}

GType
gimp_file_chooser_action_get_type (void)
{
  static const GEnumValue values[] =
  {
    { GIMP_FILE_CHOOSER_ACTION_ANY, "GIMP_FILE_CHOOSER_ACTION_ANY", "any" },
    { GIMP_FILE_CHOOSER_ACTION_OPEN, "GIMP_FILE_CHOOSER_ACTION_OPEN", "open" },
    { GIMP_FILE_CHOOSER_ACTION_SAVE, "GIMP_FILE_CHOOSER_ACTION_SAVE", "save" },
    { GIMP_FILE_CHOOSER_ACTION_SELECT_FOLDER, "GIMP_FILE_CHOOSER_ACTION_SELECT_FOLDER", "select-folder" },
    { GIMP_FILE_CHOOSER_ACTION_CREATE_FOLDER, "GIMP_FILE_CHOOSER_ACTION_CREATE_FOLDER", "create-folder" },
    { 0, NULL, NULL }
  };

  static const GimpEnumDesc descs[] =
  {
    { GIMP_FILE_CHOOSER_ACTION_ANY, "GIMP_FILE_CHOOSER_ACTION_ANY", NULL },
    { GIMP_FILE_CHOOSER_ACTION_OPEN, "GIMP_FILE_CHOOSER_ACTION_OPEN", NULL },
    { GIMP_FILE_CHOOSER_ACTION_SAVE, "GIMP_FILE_CHOOSER_ACTION_SAVE", NULL },
    { GIMP_FILE_CHOOSER_ACTION_SELECT_FOLDER, "GIMP_FILE_CHOOSER_ACTION_SELECT_FOLDER", NULL },
    { GIMP_FILE_CHOOSER_ACTION_CREATE_FOLDER, "GIMP_FILE_CHOOSER_ACTION_CREATE_FOLDER", NULL },
    { 0, NULL, NULL }
  };

  static GType type = 0;

  if (G_UNLIKELY (! type))
    {
      type = g_enum_register_static ("GimpFileChooserAction", values);
      gimp_type_set_translation_domain (type, GETTEXT_PACKAGE "-libgimp");
      gimp_type_set_translation_context (type, "file-chooser-action");
      gimp_enum_set_value_descriptions (type, descs);
    }

  return type;
}


/* Generated data ends here */


/* --- end libammoos/base/fieldbase/gimpbaseenums.c --- */

/* --- begin libammoos/base/fieldbase/gimpbasetypes.c --- */
/* LIBGIMP - The AmmoOS Image Library
 * Copyright (C) 1995-1997 Spencer Kimball and Peter Mattis
 *
 * gimpbasetypes.c
 * Copyright (C) 2004 Sven Neumann <sven@ammoos.org>
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

#include <glib-object.h>

#include "gimpbasetypes.h"


/**
 * SECTION: gimpbasetypes
 * @title: gimpbasetypes
 * @short_description: Translation between gettext translation domain
 *                     identifier and GType.
 *
 * Translation between gettext translation domain identifier and
 * GType.
 **/


static GQuark  gimp_translation_domain_quark  (void) G_GNUC_CONST;
static GQuark  gimp_translation_context_quark (void) G_GNUC_CONST;
static GQuark  gimp_value_descriptions_quark  (void) G_GNUC_CONST;


/**
 * gimp_type_set_translation_domain:
 * @type:   a #GType
 * @domain: a constant string that identifies a translation domain or %NULL
 *
 * This function attaches a constant string as a gettext translation
 * domain identifier to a #GType. The only purpose of this function is
 * to use it when registering a #G_TYPE_ENUM with translatable value
 * names.
 *
 * Since: 2.2
 **/
void
gimp_type_set_translation_domain (GType        type,
                                  const gchar *domain)
{
  g_type_set_qdata (type,
                    gimp_translation_domain_quark (), (gpointer) domain);
}

/**
 * gimp_type_get_translation_domain:
 * @type: a #GType
 *
 * Retrieves the gettext translation domain identifier that has been
 * previously set using gimp_type_set_translation_domain(). You should
 * not need to use this function directly, use gimp_enum_get_value()
 * or gimp_enum_value_get_desc() instead.
 *
 * Returns: the translation domain associated with @type
 *               or %NULL if no domain was set
 *
 * Since: 2.2
 **/
const gchar *
gimp_type_get_translation_domain (GType type)
{
  return (const gchar *) g_type_get_qdata (type,
                                           gimp_translation_domain_quark ());
}

/**
 * gimp_type_set_translation_context:
 * @type:    a #GType
 * @context: a constant string that identifies a translation context or %NULL
 *
 * This function attaches a constant string as a translation context
 * to a #GType. The only purpose of this function is to use it when
 * registering a #G_TYPE_ENUM with translatable value names.
 *
 * Since: 2.8
 **/
void
gimp_type_set_translation_context (GType        type,
                                   const gchar *context)
{
  g_type_set_qdata (type,
                    gimp_translation_context_quark (), (gpointer) context);
}

/**
 * gimp_type_get_translation_context:
 * @type: a #GType
 *
 * Retrieves the translation context that has been previously set
 * using gimp_type_set_translation_context(). You should not need to
 * use this function directly, use gimp_enum_get_value() or
 * gimp_enum_value_get_desc() instead.
 *
 * Returns: the translation context associated with @type
 *               or %NULL if no context was set
 *
 * Since: 2.8
 **/
const gchar *
gimp_type_get_translation_context (GType type)
{
  return (const gchar *) g_type_get_qdata (type,
                                           gimp_translation_context_quark ());
}

/**
 * gimp_enum_set_value_descriptions:
 * @enum_type:    a #GType
 * @descriptions: a %NULL terminated constant static array of #GimpEnumDesc
 *
 * Sets the array of human readable and translatable descriptions
 * and help texts for enum values.
 *
 * Since: 2.2
 **/
void
gimp_enum_set_value_descriptions (GType               enum_type,
                                  const GimpEnumDesc *descriptions)
{
  g_return_if_fail (g_type_is_a (enum_type, G_TYPE_ENUM));
  g_return_if_fail (descriptions != NULL);

  g_type_set_qdata (enum_type,
                    gimp_value_descriptions_quark (),
                    (gpointer) descriptions);
}

/**
 * gimp_enum_get_value_descriptions:
 * @enum_type: a #GType
 *
 * Retrieves the array of human readable and translatable descriptions
 * and help texts for enum values.
 *
 * Returns: a %NULL terminated constant array of #GimpEnumDesc
 *
 * Since: 2.2
 **/
const GimpEnumDesc *
gimp_enum_get_value_descriptions (GType enum_type)
{
  g_return_val_if_fail (g_type_is_a (enum_type, G_TYPE_ENUM), NULL);

  return (const GimpEnumDesc *)
    g_type_get_qdata (enum_type, gimp_value_descriptions_quark ());
}

/**
 * gimp_flags_set_value_descriptions:
 * @flags_type:   a #GType
 * @descriptions: a %NULL terminated constant static array of #GimpFlagsDesc
 *
 * Sets the array of human readable and translatable descriptions
 * and help texts for flags values.
 *
 * Since: 2.2
 **/
void
gimp_flags_set_value_descriptions (GType                flags_type,
                                   const GimpFlagsDesc *descriptions)
{
  g_return_if_fail (g_type_is_a (flags_type, G_TYPE_FLAGS));
  g_return_if_fail (descriptions != NULL);

  g_type_set_qdata (flags_type,
                    gimp_value_descriptions_quark (),
                    (gpointer) descriptions);
}

/**
 * gimp_flags_get_value_descriptions:
 * @flags_type: a #GType
 *
 * Retrieves the array of human readable and translatable descriptions
 * and help texts for flags values.
 *
 * Returns: a %NULL terminated constant array of #GimpFlagsDesc
 *
 * Since: 2.2
 **/
const GimpFlagsDesc *
gimp_flags_get_value_descriptions (GType flags_type)
{
  g_return_val_if_fail (g_type_is_a (flags_type, G_TYPE_FLAGS), NULL);

  return (const GimpFlagsDesc *)
    g_type_get_qdata (flags_type, gimp_value_descriptions_quark ());
}


/*  private functions  */

static GQuark
gimp_translation_domain_quark (void)
{
  static GQuark quark = 0;

  if (! quark)
    quark = g_quark_from_static_string ("ammoos-translation-domain-quark");

  return quark;
}

static GQuark
gimp_translation_context_quark (void)
{
  static GQuark quark = 0;

  if (! quark)
    quark = g_quark_from_static_string ("ammoos-translation-context-quark");

  return quark;
}

static GQuark
gimp_value_descriptions_quark (void)
{
  static GQuark quark = 0;

  if (! quark)
    quark = g_quark_from_static_string ("ammoos-value-descriptions-quark");

  return quark;
}

/* --- end libammoos/base/fieldbase/gimpbasetypes.c --- */

/* --- begin libammoos/base/fieldbase/gimpchecks.c --- */
/* LIBGIMP - The AmmoOS Image Library
 * Copyright (C) 1995-1997 Spencer Kimball and Peter Mattis
 *
 * gimpchecks.c
 * Copyright (C) 2004  Sven Neumann <sven@ammoos.org>
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

#include <gegl.h>
#include <glib-object.h>

#include "gimpbasetypes.h"

#include "gimpchecks.h"


/**
 * SECTION: gimpchecks
 * @title: gimpchecks
 * @short_description: Constants and functions related to rendering
 *                     checkerboards.
 *
 * Constants and functions related to rendering checkerboards.
 **/


/**
 * gimp_checks_get_colors:
 * @type:            the checkerboard type
 * @color1: (inout): current custom color and return location for the first color.
 * @color2: (inout): current custom color and return location for the second color.
 *
 * Retrieves the colors to use when drawing a checkerboard for a certain
 * #GimpCheckType and custom colors.
 * If @type is %GIMP_CHECK_TYPE_CUSTOM_CHECKS, then @color1 and @color2
 * will remain untouched, which means you must initialize them to the
 * values expected for custom checks.
 *
 * To obtain the user-set colors in Preferences, just call:
 * |[<!-- language="C" -->
 * GeglColor *color1 = gimp_check_custom_color1 ();
 * GeglColor *color2 = gimp_check_custom_color2 ();
 * gimp_checks_get_colors (gimp_check_type (), &color1, &color2);
 * ]|
 *
 * Since: 3.0
 **/
void
gimp_checks_get_colors (GimpCheckType   type,
                        GeglColor     **color1,
                        GeglColor     **color2)
{
  g_return_if_fail ((color1 != NULL && GEGL_IS_COLOR (*color1)) || (color2 != NULL && GEGL_IS_COLOR (*color2)));

  if (color1)
    {
      *color1 = gegl_color_duplicate (*color1);
      switch (type)
        {
        case GIMP_CHECK_TYPE_LIGHT_CHECKS:
          gegl_color_set_pixel (*color1, babl_format ("R'G'B'A double"), GIMP_CHECKS_LIGHT_COLOR_LIGHT);
          break;
        case GIMP_CHECK_TYPE_DARK_CHECKS:
          gegl_color_set_pixel (*color1, babl_format ("R'G'B'A double"), GIMP_CHECKS_DARK_COLOR_LIGHT);
          break;
        case GIMP_CHECK_TYPE_WHITE_ONLY:
          gegl_color_set_pixel (*color1, babl_format ("R'G'B'A double"), GIMP_CHECKS_WHITE_COLOR);
          break;
        case GIMP_CHECK_TYPE_GRAY_ONLY:
          gegl_color_set_pixel (*color1, babl_format ("R'G'B'A double"), GIMP_CHECKS_GRAY_COLOR);
          break;
        case GIMP_CHECK_TYPE_BLACK_ONLY:
          gegl_color_set_pixel (*color1, babl_format ("R'G'B'A double"), GIMP_CHECKS_BLACK_COLOR);
          break;
        case GIMP_CHECK_TYPE_CUSTOM_CHECKS:
          /* Keep the current value. */
          break;
        default:
          gegl_color_set_pixel (*color1, babl_format ("R'G'B'A double"), GIMP_CHECKS_GRAY_COLOR_LIGHT);
          break;
        }
    }

  if (color2)
    {
      *color2 = gegl_color_duplicate (*color2);
      switch (type)
        {
        case GIMP_CHECK_TYPE_LIGHT_CHECKS:
          gegl_color_set_pixel (*color2, babl_format ("R'G'B'A double"), GIMP_CHECKS_LIGHT_COLOR_DARK);
          break;
        case GIMP_CHECK_TYPE_DARK_CHECKS:
          gegl_color_set_pixel (*color2, babl_format ("R'G'B'A double"), GIMP_CHECKS_DARK_COLOR_DARK);
          break;
        case GIMP_CHECK_TYPE_WHITE_ONLY:
          gegl_color_set_pixel (*color2, babl_format ("R'G'B'A double"), GIMP_CHECKS_WHITE_COLOR);
          break;
        case GIMP_CHECK_TYPE_GRAY_ONLY:
          gegl_color_set_pixel (*color2, babl_format ("R'G'B'A double"), GIMP_CHECKS_GRAY_COLOR);
          break;
        case GIMP_CHECK_TYPE_BLACK_ONLY:
          gegl_color_set_pixel (*color2, babl_format ("R'G'B'A double"), GIMP_CHECKS_BLACK_COLOR);
          break;
        case GIMP_CHECK_TYPE_CUSTOM_CHECKS:
          /* Keep the current value. */
          break;
        default:
          gegl_color_set_pixel (*color2, babl_format ("R'G'B'A double"), GIMP_CHECKS_GRAY_COLOR_DARK);
          break;
        }
    }
}

/* --- end libammoos/base/fieldbase/gimpchecks.c --- */

/* --- begin libammoos/base/fieldbase/gimpchoice.c --- */
/* LIBGIMP - The AmmoOS Image Library
 * Copyright (C) 1995-2000 Peter Mattis and Spencer Kimball
 *
 * gimpchoice.c
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

#include <gegl.h>
#include <gio/gio.h>
#include <glib-object.h>

#include "gimpbasetypes.h"

#include "gimpchoice.h"
#include "gimpparamspecs.h"


typedef struct _GimpChoiceDesc
{
  gchar    *label;
  gchar    *help;
  gint      id;
  gboolean  sensitive;

  gboolean  deprecated;
  gchar    *redirect_to;
  gchar    *reason;

  GList    *aliases;
} GimpChoiceDesc;

enum
{
  SENSITIVITY_CHANGED,
  LAST_SIGNAL
};

struct _GimpChoice
{
  GObject     parent_instance;

  GHashTable *choices;
  GList      *keys;
};


static void gimp_choice_finalize     (GObject        *object);

static void gimp_choice_desc_free    (GimpChoiceDesc *desc);


G_DEFINE_TYPE (GimpChoice, gimp_choice, G_TYPE_OBJECT)

#define parent_class gimp_choice_parent_class

static guint gimp_choice_signals[LAST_SIGNAL] = { 0 };

static void
gimp_choice_class_init (GimpChoiceClass *klass)
{
  GObjectClass *object_class = G_OBJECT_CLASS (klass);

  gimp_choice_signals[SENSITIVITY_CHANGED] =
    g_signal_new ("sensitivity-changed",
                  G_TYPE_FROM_CLASS (klass),
                  G_SIGNAL_RUN_FIRST,
                  0, /*G_STRUCT_OFFSET (GimpChoiceClass, sensitivity_changed),*/
                  NULL, NULL, NULL,
                  G_TYPE_NONE, 1,
                  G_TYPE_STRING);

  object_class->finalize = gimp_choice_finalize;
}

static void
gimp_choice_init (GimpChoice *choice)
{
  choice->choices =
    g_hash_table_new_full (g_str_hash, g_str_equal, g_free,
                           (GDestroyNotify) gimp_choice_desc_free);
}

static void
gimp_choice_finalize (GObject *object)
{
  GimpChoice *choice = GIMP_CHOICE (object);

  g_hash_table_unref (choice->choices);
  g_list_free_full (choice->keys, (GDestroyNotify) g_free);
}

/* Public API */

/**
 * gimp_choice_new:
 *
 * Returns: (transfer full): a #GimpChoice.
 *
 * Since: 3.0
 **/
GimpChoice *
gimp_choice_new (void)
{
  GimpChoice *choice;

  choice = g_object_new (GIMP_TYPE_CHOICE, NULL);

  return choice;
}

/**
 * gimp_choice_new_with_values:
 * @nick:  the first value.
 * @id:    integer ID for @nick.
 * @label: the label of @nick.
 * @help:  longer help text for @nick.
 * ...:    more triplets of string to pre-fill the created %GimpChoice.
 *
 * Returns: (transfer full): a #GimpChoice.
 *
 * Since: 3.0
 **/
GimpChoice *
gimp_choice_new_with_values (const gchar *nick,
                             gint         id,
                             const gchar *label,
                             const gchar *help,
                             ...)
{
  GimpChoice *choice;
  va_list     va_args;

  g_return_val_if_fail (nick != NULL, NULL);
  g_return_val_if_fail (label != NULL, NULL);

  choice = gimp_choice_new ();

  va_start (va_args, help);

  do
    {
      gimp_choice_add (choice, nick, id, label, help);
      nick  = va_arg (va_args, const gchar *);
      if (nick == NULL)
        break;
      id    = va_arg (va_args, gint);
      label = va_arg (va_args, const gchar *);
      if (label == NULL)
        {
          g_critical ("%s: nick '%s' cannot have a NULL label.", G_STRFUNC, nick);
          break;
        }
      help  = va_arg (va_args, const gchar *);
    }
  while (TRUE);

  va_end (va_args);

  return choice;
}

/**
 * gimp_choice_add:
 * @choice: the %GimpChoice.
 * @nick:   the nick of @choice.
 * @id:     optional integer ID for @nick.
 * @label:  the label of @choice.
 * @help:   optional longer help text for @nick.
 *
 * This procedure adds a new possible value to @choice list of values.
 * The @id is an optional integer identifier. This can be useful for instance
 * when you want to work with different enum values mapped to each @nick.
 *
 * Since: 3.0
 **/
void
gimp_choice_add (GimpChoice  *choice,
                 const gchar *nick,
                 gint         id,
                 const gchar *label,
                 const gchar *help)
{
  GimpChoiceDesc *desc;
  GList          *duplicate;

  g_return_if_fail (label != NULL);

  desc              = g_new0 (GimpChoiceDesc, 1);
  desc->id          = id;
  desc->label       = g_strdup (label);
  desc->help        = help != NULL ? g_strdup (help) : NULL;
  desc->sensitive   = TRUE;
  desc->deprecated  = FALSE;
  desc->redirect_to = NULL;
  desc->reason      = NULL;
  desc->aliases     = NULL;
  g_hash_table_insert (choice->choices, g_strdup (nick), desc);

  duplicate = g_list_find_custom (choice->keys, nick, (GCompareFunc) g_strcmp0);
  if (duplicate != NULL)
    {
      choice->keys = g_list_remove_link (choice->keys, duplicate);
      g_free (duplicate->data);
      g_list_free (duplicate);
    }
  choice->keys = g_list_append (choice->keys, g_strdup (nick));
}

/**
 * gimp_choice_add_deprecated:
 * @choice:      the %GimpChoice.
 * @nick:        the nick of the deprecated @choice.
 * @id:          optional integer ID for @nick.
 * @redirect_to: (nullable): the valid nick to redirect the deprecated one to
 * @reason: (nullable): the deprecation reason.
 *
 * This procedure is used to add a deprecated nick. It must either have
 * a valid @redirect_to alias (when you are basically renaming a choice)
 * or a free-text @reason (e.g. for planning choice removal through a
 * deprecation period).
 *
 * If @redirect_to is non %NULL, then @id must be identical to the ID
 * of @redirect_to. The @redirect_to value must not be deprecated itself.
 *
 * Since: 3.4
 **/
void
gimp_choice_add_deprecated (GimpChoice  *choice,
                            const gchar *nick,
                            gint         id,
                            const gchar *redirect_to,
                            const gchar *reason)
{
  GimpChoiceDesc *deprecated_desc;
  GimpChoiceDesc *redirect_desc = NULL;
  GList          *duplicate;

  g_return_if_fail (nick != NULL);
  g_return_if_fail (redirect_to == NULL || g_strcmp0 (nick, redirect_to) != 0);
  g_return_if_fail ((redirect_to == NULL && reason != NULL) ||
                    (reason == NULL && redirect_to != NULL && g_strcmp0 (nick, redirect_to) != 0));

  if (redirect_to)
    {
      redirect_desc = g_hash_table_lookup (choice->choices, redirect_to);
      g_return_if_fail (redirect_desc != NULL       &&
                        ! redirect_desc->deprecated &&
                        redirect_desc->id == id);
      redirect_desc->aliases = g_list_prepend (redirect_desc->aliases, g_strdup (nick));
    }

  deprecated_desc              = g_new0 (GimpChoiceDesc, 1);
  deprecated_desc->id          = redirect_desc ? redirect_desc->id : id;
  deprecated_desc->label       = NULL;
  deprecated_desc->help        = NULL;
  deprecated_desc->sensitive   = redirect_desc ? redirect_desc->sensitive : TRUE;
  deprecated_desc->deprecated  = TRUE;
  deprecated_desc->redirect_to = g_strdup (redirect_to);
  deprecated_desc->reason      = g_strdup (reason);
  deprecated_desc->aliases     = NULL;

  g_hash_table_insert (choice->choices, g_strdup (nick), deprecated_desc);

  duplicate = g_list_find_custom (choice->keys, nick, (GCompareFunc) g_strcmp0);
  if (duplicate != NULL)
    {
      choice->keys = g_list_remove_link (choice->keys, duplicate);
      g_free (duplicate->data);
      g_list_free (duplicate);
    }
  choice->keys = g_list_append (choice->keys, g_strdup (nick));
}

/**
 * gimp_choice_is_valid:
 * @choice: a %GimpChoice.
 * @nick:   the nick to check.
 *
 * This procedure checks if the given @nick is valid and refers to
 * an existing and sensitive choice.
 *
 * Returns: Whether the choice is valid.
 *
 * Since: 3.0
 **/
gboolean
gimp_choice_is_valid (GimpChoice  *choice,
                      const gchar *nick)
{
  GimpChoiceDesc *desc;

  g_return_val_if_fail (GIMP_IS_CHOICE (choice), FALSE);
  g_return_val_if_fail (nick != NULL, FALSE);

  desc = g_hash_table_lookup (choice->choices, nick);
  return (desc != NULL && desc->sensitive);
}

/**
 * gimp_choice_list_nicks:
 * @choice: a %GimpChoice.
 *
 * This procedure returns the list of nicks allowed for @choice.
 *
 * Returns: (element-type gchar*) (transfer none): The list of @choice's nicks.
 *
 * Since: 3.0
 **/
GList *
gimp_choice_list_nicks (GimpChoice *choice)
{
  /* I don't use g_hash_table_get_keys() on purpose, because I want to retain
   * the adding-time order.
   */
  return choice->keys;
}

/**
 * gimp_choice_get_id:
 * @choice: a %GimpChoice.
 * @nick:   the nick to lookup.
 *
 * Returns: the ID of @nick.
 *
 * Since: 3.0
 **/
gint
gimp_choice_get_id (GimpChoice  *choice,
                    const gchar *nick)
{
  GimpChoiceDesc *desc;

  g_return_val_if_fail (GIMP_IS_CHOICE (choice), 0);
  g_return_val_if_fail (nick != NULL, 0);

  desc = g_hash_table_lookup (choice->choices, nick);
  g_return_val_if_fail (desc != NULL, 0);

  return desc->id;
}

/**
 * gimp_choice_get_label:
 * @choice: a %GimpChoice.
 * @nick:   the nick to lookup.
 *
 * Returns: (transfer none): the label of @nick.
 *
 * Since: 3.0
 **/
const gchar *
gimp_choice_get_label (GimpChoice  *choice,
                       const gchar *nick)
{
  GimpChoiceDesc *desc;

  g_return_val_if_fail (GIMP_IS_CHOICE (choice), NULL);
  g_return_val_if_fail (nick != NULL, NULL);

  desc = g_hash_table_lookup (choice->choices, nick);
  if (desc && ! desc->deprecated)
    return desc->label;
  else
    return NULL;
}

/**
 * gimp_choice_get_help:
 * @choice: a %GimpChoice.
 * @nick:   the nick to lookup.
 *
 * Returns the longer documentation for @nick.
 *
 * Returns: (transfer none): the help text of @nick.
 *
 * Since: 3.0
 **/
const gchar *
gimp_choice_get_help (GimpChoice  *choice,
                      const gchar *nick)
{
  GimpChoiceDesc *desc;

  desc = g_hash_table_lookup (choice->choices, nick);
  if (desc)
    return desc->help;
  else
    return NULL;
}

/**
 * gimp_choice_get_documentation:
 * @choice: the %GimpChoice.
 * @nick:   the possible value's nick you need documentation for.
 * @label: (transfer none): the label of @nick.
 * @help:  (transfer none): the help text of @nick.
 *
 * Returns the documentation strings for @nick.
 *
 * Returns: %TRUE if @nick is found, %FALSE otherwise.
 *
 * Since: 3.0
 **/
gboolean
gimp_choice_get_documentation (GimpChoice   *choice,
                               const gchar  *nick,
                               const gchar **label,
                               const gchar **help)
{
  GimpChoiceDesc *desc;

  desc = g_hash_table_lookup (choice->choices, nick);
  if (desc)
    {
      *label = desc->label;
      *help  = desc->help;
      return TRUE;
    }

  return FALSE;
}

/**
 * gimp_choice_is_deprecated:
 * @choice: a %GimpChoice.
 * @nick:   the nick to lookup.
 * @redirect_to: (out) (nullable) (transfer none): the non-deprecated alias, if any.
 * @reason: (out) (nullable) (transfer none): the deprecation reason if @redirect_to is %NULL.
 *
 * Lookup whether @nick is a deprecated choice or not. If it is
 * deprecated, either @redirect_to will be set or @reason will be,
 * depending on whether @nick was simply renamed or if the deprecation
 * requires a more complex human-readable reason.
 *
 * Returns: %TRUE if @nick is deprecated.
 *
 * Since: 3.4
 **/
gboolean
gimp_choice_is_deprecated (GimpChoice   *choice,
                           const gchar  *nick,
                           const gchar **redirect_to,
                           const gchar **reason)
{
  GimpChoiceDesc *desc;

  g_return_val_if_fail (GIMP_IS_CHOICE (choice), FALSE);
  g_return_val_if_fail (nick != NULL, FALSE);

  desc = g_hash_table_lookup (choice->choices, nick);
  g_return_val_if_fail (desc != NULL, FALSE);

  if (redirect_to)
    *redirect_to = desc->redirect_to;
  if (reason)
    *reason = desc->reason;

  return desc->deprecated;
}

/**
 * gimp_choice_set_sensitive:
 * @choice: the %GimpChoice.
 * @nick:   the nick to lookup.
 *
 * Change the sensitivity of a possible @nick. Technically a non-sensitive @nick
 * means it cannot be chosen anymore (so [method@Gimp.Choice.is_valid] will
 * return %FALSE; nevertheless [method@Gimp.Choice.list_nicks] and other
 * functions to get information about a choice will still function).
 *
 * Since: 3.0
 **/
void
gimp_choice_set_sensitive (GimpChoice  *choice,
                           const gchar *nick,
                           gboolean     sensitive)
{
  GimpChoiceDesc *desc;

  g_return_if_fail (GIMP_IS_CHOICE (choice));
  g_return_if_fail (nick != NULL);

  desc = g_hash_table_lookup (choice->choices, nick);
  g_return_if_fail (desc != NULL);
  if (desc->sensitive != sensitive)
    {
      if (desc->redirect_to)
        {
          gimp_choice_set_sensitive (choice, desc->redirect_to, sensitive);
        }
      else
        {
          desc->sensitive = sensitive;
          for (GList *iter = desc->aliases; iter; iter = iter->next)
            {
              GimpChoiceDesc *alias_desc;

              alias_desc = g_hash_table_lookup (choice->choices, iter->data);
              alias_desc->sensitive = sensitive;
              g_signal_emit (choice, gimp_choice_signals[SENSITIVITY_CHANGED], 0, (gchar *) iter->data);
            }
          g_signal_emit (choice, gimp_choice_signals[SENSITIVITY_CHANGED], 0, nick);
        }
    }
}


/* Private functions */

static void
gimp_choice_desc_free (GimpChoiceDesc *desc)
{
  g_free (desc->label);
  g_free (desc->help);
  g_free (desc->redirect_to);
  g_free (desc->reason);
  g_list_free_full (desc->aliases, g_free);
  g_free (desc);
}


/*
 * GIMP_TYPE_PARAM_CHOICE
 */

#define GIMP_PARAM_SPEC_CHOICE(pspec)    (G_TYPE_CHECK_INSTANCE_CAST ((pspec), GIMP_TYPE_PARAM_CHOICE, GimpParamSpecChoice))

typedef struct _GimpParamSpecChoice GimpParamSpecChoice;

struct _GimpParamSpecChoice
{
  GParamSpecString  parent_instance;

  GimpChoice       *choice;
};

static void       gimp_param_choice_class_init        (GParamSpecClass *klass);
static void       gimp_param_choice_init              (GParamSpec      *pspec);
static void       gimp_param_choice_finalize          (GParamSpec      *pspec);
static gboolean   gimp_param_choice_validate          (GParamSpec      *pspec,
                                                       GValue          *value);
static gboolean   gimp_param_choice_value_is_valid    (GParamSpec      *pspec,
                                                       const GValue    *value);
static gint       gimp_param_choice_values_cmp        (GParamSpec      *pspec,
                                                       const GValue    *value1,
                                                       const GValue    *value2);

GType
gimp_param_choice_get_type (void)
{
  static GType type = 0;

  if (! type)
    {
      const GTypeInfo info =
      {
        sizeof (GParamSpecClass),
        NULL, NULL,
        (GClassInitFunc) gimp_param_choice_class_init,
        NULL, NULL,
        sizeof (GimpParamSpecChoice),
        0,
        (GInstanceInitFunc) gimp_param_choice_init
      };

      type = g_type_register_static (G_TYPE_PARAM_STRING,
                                     "GimpParamChoice", &info, 0);
    }

  return type;
}

static void
gimp_param_choice_class_init (GParamSpecClass *klass)
{
  klass->value_type     = G_TYPE_STRING;
  klass->finalize       = gimp_param_choice_finalize;
  klass->value_validate = gimp_param_choice_validate;
  klass->value_is_valid = gimp_param_choice_value_is_valid;
  klass->values_cmp     = gimp_param_choice_values_cmp;
}

static void
gimp_param_choice_init (GParamSpec *pspec)
{
  GimpParamSpecChoice *choice = GIMP_PARAM_SPEC_CHOICE (pspec);

  choice->choice = NULL;
}

static void
gimp_param_choice_finalize (GParamSpec *pspec)
{
  GimpParamSpecChoice *spec_choice  = GIMP_PARAM_SPEC_CHOICE (pspec);
  GParamSpecClass     *parent_class = g_type_class_peek (g_type_parent (GIMP_TYPE_PARAM_CHOICE));

  g_object_unref (spec_choice->choice);

  parent_class->finalize (pspec);
}

static gboolean
gimp_param_choice_validate (GParamSpec *pspec,
                            GValue     *value)
{
  GimpParamSpecChoice *spec_choice = GIMP_PARAM_SPEC_CHOICE (pspec);
  GParamSpecString    *spec_string = G_PARAM_SPEC_STRING (pspec);
  GimpChoice          *choice      = spec_choice->choice;
  const gchar         *strval      = g_value_get_string (value);

  if (! gimp_choice_is_valid (choice, strval))
    {
      if (gimp_choice_is_valid (choice, spec_string->default_value))
        {
          g_value_set_string (value, spec_string->default_value);
        }
      else
        {
          /* This might happen if the default value is set insensitive. Then we
           * should just set any valid random nick.
           */
          GList *nicks;

          nicks = gimp_choice_list_nicks (choice);
          for (GList *iter = nicks; iter; iter = iter->next)
            if (gimp_choice_is_valid (choice, (gchar *) iter->data))
              {
                g_value_set_string (value, (gchar *) iter->data);
                break;
              }
        }
      return TRUE;
    }

  return FALSE;
}

static gboolean
gimp_param_choice_value_is_valid (GParamSpec   *pspec,
                                  const GValue *value)
{
  GimpParamSpecChoice *cspec  = GIMP_PARAM_SPEC_CHOICE (pspec);
  const gchar         *strval = g_value_get_string (value);
  GimpChoice          *choice = cspec->choice;
  const gchar         *reason = NULL;
  const gchar         *alias  = NULL;
  gboolean             valid;

  valid = gimp_choice_is_valid (choice, strval);
  if (valid && gimp_choice_is_deprecated (choice, strval, &alias, &reason) &&
      /* Typically when calling a PDB procedure, we will first set
       * properties to a GimpProcedureConfig, which will later be copied
       * to a second one prefixed with "GimpProcedureConfigRun-".
       * Plug-in developers don't have much say to this second config
       * object, so let's avoid 2 WARNINGs for a single object set.
       */
      ! g_str_has_prefix (g_type_name (pspec->owner_type), "GimpProcedureConfigRun-"))
    {
      if (alias)
        g_critical ("Value \"%s\" is deprecated for property \"%s\" of %s. "
                    "Use \"%s\" instead.", strval, pspec->name,
                    g_type_name (pspec->owner_type), alias);
      else
        g_critical ("Value \"%s\" is deprecated for property \"%s\" of %s. %s",
                    strval, pspec->name, g_type_name (pspec->owner_type), reason);
    }

  return valid;
}

static gint
gimp_param_choice_values_cmp (GParamSpec   *pspec,
                              const GValue *value1,
                              const GValue *value2)
{
  const gchar *choice1 = g_value_get_string (value1);
  const gchar *choice2 = g_value_get_string (value2);

  return g_strcmp0 (choice1, choice2);
}

/**
 * gimp_param_spec_choice:
 * @name:  Canonical name of the property specified.
 * @nick:  Nick name of the property specified.
 * @blurb: Description of the property specified.
 * @choice: (transfer full): the %GimpChoice describing allowed choices.
 * @flags: Flags for the property specified.
 *
 * Creates a new #GimpParamSpecChoice specifying a
 * #G_TYPE_STRING property.
 * This %GimpParamSpecChoice takes ownership of the reference on @choice.
 *
 * See g_param_spec_internal() for details on property names.
 *
 * Returns: (transfer floating): The newly created #GimpParamSpecChoice.
 *
 * Since: 3.0
 **/
GParamSpec *
gimp_param_spec_choice (const gchar *name,
                        const gchar *nick,
                        const gchar *blurb,
                        GimpChoice  *choice,
                        const gchar *default_value,
                        GParamFlags  flags)
{
  GimpParamSpecChoice *choice_spec;
  GParamSpecString    *string_spec;

  g_return_val_if_fail (GIMP_IS_CHOICE (choice), NULL);
  g_return_val_if_fail (gimp_choice_is_valid (choice, default_value), NULL);

  choice_spec = g_param_spec_internal (GIMP_TYPE_PARAM_CHOICE,
                                       name, nick, blurb, flags);

  g_return_val_if_fail (choice_spec, NULL);

  string_spec = G_PARAM_SPEC_STRING (choice_spec);

  choice_spec->choice        = choice;
  string_spec->default_value = g_strdup (default_value);

  return G_PARAM_SPEC (choice_spec);
}

/**
 * gimp_param_spec_choice_get_choice:
 * @pspec: a #GParamSpec to hold a #GimpParamSpecChoice value.
 *
 * Returns: (transfer none): the choice object defining the valid values.
 *
 * Since: 3.0
 **/
GimpChoice *
gimp_param_spec_choice_get_choice (GParamSpec *pspec)
{
  g_return_val_if_fail (GIMP_IS_PARAM_SPEC_CHOICE (pspec), NULL);

  return GIMP_PARAM_SPEC_CHOICE (pspec)->choice;
}

/**
 * gimp_param_spec_choice_get_default:
 * @pspec: a #GParamSpec to hold a #GimpParamSpecChoice value.
 *
 * Returns: the default value.
 *
 * Since: 3.0
 **/
const gchar *
gimp_param_spec_choice_get_default (GParamSpec *pspec)
{
  const GValue *value;

  g_return_val_if_fail (GIMP_IS_PARAM_SPEC_CHOICE (pspec), NULL);

  value = g_param_spec_get_default_value (pspec);

  return g_value_get_string (value);
}

/* --- end libammoos/base/fieldbase/gimpchoice.c --- */

/* --- begin libammoos/base/fieldbase/gimpcompatenums.c --- */

/* Generated data (by ammoos-mkenums) */

#include "stamp-gimpcompatenums.h"
#include "config.h"
#include <glib-object.h>
#include "gimpbasetypes.h"
#include "gimpcompatenums.h"
#include "libgimp/libgimp-intl.h"

/* Generated data ends here */


/* --- end libammoos/base/fieldbase/gimpcompatenums.c --- */

/* --- begin libammoos/base/fieldbase/gimpcpuaccel.c --- */
/* LIBGIMP - The AmmoOS Image Library
 * Copyright (C) 1995-1997 Peter Mattis and Spencer Kimball
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

/*
 * x86 bits Copyright (C) Manish Singh <yosh@ammoos.org>
 */

/*
 * PPC CPU acceleration detection was taken from DirectFB but seems to be
 * originating from mpeg2dec with the following copyright:
 *
 * Copyright (C) 1999-2001 Aaron Holtzman <aholtzma@ess.engr.uvic.ca>
 */

#include "config.h"

#include <string.h>
#include <signal.h>
#include <setjmp.h>

#include <glib.h>

#include "gimpcpuaccel.h"
#include "gimpcpuaccel-private.h"


/**
 * SECTION: gimpcpuaccel
 * @title: gimpcpuaccel
 * @short_description: Functions to query and configure CPU acceleration.
 *
 * Functions to query and configure CPU acceleration.
 **/


static GimpCpuAccelFlags  cpu_accel (void) G_GNUC_CONST;


static gboolean  use_cpu_accel = TRUE;


/**
 * gimp_cpu_accel_get_support:
 *
 * Query for CPU acceleration support.
 *
 * Returns: #GimpCpuAccelFlags as supported by the CPU.
 *
 * Since: 2.4
 */
GimpCpuAccelFlags
gimp_cpu_accel_get_support (void)
{
  return use_cpu_accel ? cpu_accel () : GIMP_CPU_ACCEL_NONE;
}

/**
 * gimp_cpu_accel_set_use:
 * @use:  whether to use CPU acceleration features or not
 *
 * This function is for internal use only.
 *
 * Since: 2.4
 */
void
gimp_cpu_accel_set_use (gboolean use)
{
  use_cpu_accel = use ? TRUE : FALSE;
}


#if defined(ARCH_X86) && defined(USE_MMX) && defined(__GNUC__)

#define HAVE_ACCEL 1


typedef enum
{
  ARCH_X86_VENDOR_NONE,
  ARCH_X86_VENDOR_INTEL,
  ARCH_X86_VENDOR_AMD,
  ARCH_X86_VENDOR_CENTAUR,
  ARCH_X86_VENDOR_CYRIX,
  ARCH_X86_VENDOR_NSC,
  ARCH_X86_VENDOR_TRANSMETA,
  ARCH_X86_VENDOR_NEXGEN,
  ARCH_X86_VENDOR_RISE,
  ARCH_X86_VENDOR_UMC,
  ARCH_X86_VENDOR_SIS,
  ARCH_X86_VENDOR_HYGON,
  ARCH_X86_VENDOR_UNKNOWN    = 0xff
} X86Vendor;

enum
{
  ARCH_X86_INTEL_FEATURE_MMX      = 1 << 23,
  ARCH_X86_INTEL_FEATURE_XMM      = 1 << 25,
  ARCH_X86_INTEL_FEATURE_XMM2     = 1 << 26,

  ARCH_X86_AMD_FEATURE_MMXEXT     = 1 << 22,
  ARCH_X86_AMD_FEATURE_3DNOW      = 1 << 31,

  ARCH_X86_CENTAUR_FEATURE_MMX    = 1 << 23,
  ARCH_X86_CENTAUR_FEATURE_MMXEXT = 1 << 24,
  ARCH_X86_CENTAUR_FEATURE_3DNOW  = 1 << 31,

  ARCH_X86_CYRIX_FEATURE_MMX      = 1 << 23,
  ARCH_X86_CYRIX_FEATURE_MMXEXT   = 1 << 24
};

enum
{
  ARCH_X86_INTEL_FEATURE_PNI      = 1 << 0,
  ARCH_X86_INTEL_FEATURE_SSSE3    = 1 << 9,
  ARCH_X86_INTEL_FEATURE_SSE4_1   = 1 << 19,
  ARCH_X86_INTEL_FEATURE_SSE4_2   = 1 << 20,
  ARCH_X86_INTEL_FEATURE_AVX      = 1 << 28
};

#if !defined(ARCH_X86_64) && (defined(PIC) || defined(__PIC__))
#define cpuid(op,eax,ebx,ecx,edx)  \
  __asm__ ("movl %%ebx, %%esi\n\t" \
           "cpuid\n\t"             \
           "xchgl %%ebx,%%esi"     \
           : "=a" (eax),           \
             "=S" (ebx),           \
             "=c" (ecx),           \
             "=d" (edx)            \
           : "0" (op))
#else
#define cpuid(op,eax,ebx,ecx,edx)  \
  __asm__ ("cpuid"                 \
           : "=a" (eax),           \
             "=b" (ebx),           \
             "=c" (ecx),           \
             "=d" (edx)            \
           : "0" (op))
#endif


static X86Vendor
arch_get_vendor (void)
{
  guint32 eax, ebx, ecx, edx;
  union{
      gchar idaschar[16];
      int   idasint[4];
  }id;

#ifndef ARCH_X86_64
  /* Only need to check this on ia32 */
  __asm__ ("pushfl\n\t"
           "pushfl\n\t"
           "popl %0\n\t"
           "movl %0,%1\n\t"
           "xorl $0x200000,%0\n\t"
           "pushl %0\n\t"
           "popfl\n\t"
           "pushfl\n\t"
           "popl %0\n\t"
           "popfl"
           : "=a" (eax),
             "=c" (ecx)
           :
           : "cc");

  if (eax == ecx)
    return ARCH_X86_VENDOR_NONE;
#endif

  cpuid (0, eax, ebx, ecx, edx);

  if (eax == 0)
    return ARCH_X86_VENDOR_NONE;

  id.idasint[0] = ebx;
  id.idasint[1] = edx;
  id.idasint[2] = ecx;

  id.idaschar[12] = '\0';

#ifdef ARCH_X86_64
  if (strcmp (id.idaschar, "AuthenticAMD") == 0)
    return ARCH_X86_VENDOR_AMD;
  else if (strcmp (id.idaschar, "HygonGenuine") == 0)
    return ARCH_X86_VENDOR_HYGON;
  else if (strcmp (id.idaschar, "GenuineIntel") == 0)
    return ARCH_X86_VENDOR_INTEL;
#else
  if (strcmp (id.idaschar, "GenuineIntel") == 0)
    return ARCH_X86_VENDOR_INTEL;
  else if (strcmp (id.idaschar, "AuthenticAMD") == 0)
    return ARCH_X86_VENDOR_AMD;
  else if (strcmp (id.idaschar, "HygonGenuine") == 0)
    return ARCH_X86_VENDOR_HYGON;
  else if (strcmp (id.idaschar, "CentaurHauls") == 0)
    return ARCH_X86_VENDOR_CENTAUR;
  else if (strcmp (id.idaschar, "CyrixInstead") == 0)
    return ARCH_X86_VENDOR_CYRIX;
  else if (strcmp (id.idaschar, "Geode by NSC") == 0)
    return ARCH_X86_VENDOR_NSC;
  else if (strcmp (id.idaschar, "GenuineTMx86") == 0 ||
           strcmp (id.idaschar, "TransmetaCPU") == 0)
    return ARCH_X86_VENDOR_TRANSMETA;
  else if (strcmp (id.idaschar, "NexGenDriven") == 0)
    return ARCH_X86_VENDOR_NEXGEN;
  else if (strcmp (id.idaschar, "RiseRiseRise") == 0)
    return ARCH_X86_VENDOR_RISE;
  else if (strcmp (id.idaschar, "UMC UMC UMC ") == 0)
    return ARCH_X86_VENDOR_UMC;
  else if (strcmp (id.idaschar, "SiS SiS SiS ") == 0)
    return ARCH_X86_VENDOR_SIS;
#endif

  return ARCH_X86_VENDOR_UNKNOWN;
}

static guint32
arch_accel_intel (void)
{
  guint32 caps = 0;

#ifdef USE_MMX
  {
    guint32 eax, ebx, ecx, edx;

    cpuid (1, eax, ebx, ecx, edx);

    if ((edx & ARCH_X86_INTEL_FEATURE_MMX) == 0)
      return 0;

    caps = GIMP_CPU_ACCEL_X86_MMX;

#ifdef USE_SSE
    if (edx & ARCH_X86_INTEL_FEATURE_XMM)
      caps |= GIMP_CPU_ACCEL_X86_SSE | GIMP_CPU_ACCEL_X86_MMXEXT;

    if (edx & ARCH_X86_INTEL_FEATURE_XMM2)
      caps |= GIMP_CPU_ACCEL_X86_SSE2;

    if (ecx & ARCH_X86_INTEL_FEATURE_PNI)
      caps |= GIMP_CPU_ACCEL_X86_SSE3;

    if (ecx & ARCH_X86_INTEL_FEATURE_SSSE3)
      caps |= GIMP_CPU_ACCEL_X86_SSSE3;

    if (ecx & ARCH_X86_INTEL_FEATURE_SSE4_1)
      caps |= GIMP_CPU_ACCEL_X86_SSE4_1;

    if (ecx & ARCH_X86_INTEL_FEATURE_SSE4_2)
      caps |= GIMP_CPU_ACCEL_X86_SSE4_2;

    if (ecx & ARCH_X86_INTEL_FEATURE_AVX)
      caps |= GIMP_CPU_ACCEL_X86_AVX;
#endif /* USE_SSE */
  }
#endif /* USE_MMX */

  return caps;
}

static guint32
arch_accel_amd (void)
{
  guint32 caps;

  caps = arch_accel_intel ();

#ifdef USE_MMX
  {
    guint32 eax, ebx, ecx, edx;

    cpuid (0x80000000, eax, ebx, ecx, edx);

    if (eax < 0x80000001)
      return caps;

#ifdef USE_SSE
    cpuid (0x80000001, eax, ebx, ecx, edx);

    if (edx & ARCH_X86_AMD_FEATURE_3DNOW)
      caps |= GIMP_CPU_ACCEL_X86_3DNOW;

    if (edx & ARCH_X86_AMD_FEATURE_MMXEXT)
      caps |= GIMP_CPU_ACCEL_X86_MMXEXT;
#endif /* USE_SSE */
  }
#endif /* USE_MMX */

  return caps;
}

static guint32
arch_accel_centaur (void)
{
  guint32 caps;

  caps = arch_accel_intel ();

#ifdef USE_MMX
  {
    guint32 eax, ebx, ecx, edx;

    cpuid (0x80000000, eax, ebx, ecx, edx);

    if (eax < 0x80000001)
      return caps;

    cpuid (0x80000001, eax, ebx, ecx, edx);

    if (edx & ARCH_X86_CENTAUR_FEATURE_MMX)
      caps |= GIMP_CPU_ACCEL_X86_MMX;

#ifdef USE_SSE
    if (edx & ARCH_X86_CENTAUR_FEATURE_3DNOW)
      caps |= GIMP_CPU_ACCEL_X86_3DNOW;

    if (edx & ARCH_X86_CENTAUR_FEATURE_MMXEXT)
      caps |= GIMP_CPU_ACCEL_X86_MMXEXT;
#endif /* USE_SSE */
  }
#endif /* USE_MMX */

  return caps;
}

static guint32
arch_accel_cyrix (void)
{
  guint32 caps;

  caps = arch_accel_intel ();

#ifdef USE_MMX
  {
    guint32 eax, ebx, ecx, edx;

    cpuid (0, eax, ebx, ecx, edx);

    if (eax != 2)
      return caps;

    cpuid (0x80000001, eax, ebx, ecx, edx);

    if (edx & ARCH_X86_CYRIX_FEATURE_MMX)
      caps |= GIMP_CPU_ACCEL_X86_MMX;

#ifdef USE_SSE
    if (edx & ARCH_X86_CYRIX_FEATURE_MMXEXT)
      caps |= GIMP_CPU_ACCEL_X86_MMXEXT;
#endif /* USE_SSE */
  }
#endif /* USE_MMX */

  return caps;
}

#ifdef USE_SSE
static jmp_buf sigill_return;

static void
sigill_handler (gint n)
{
  longjmp (sigill_return, 1);
}

static gboolean
arch_accel_sse_os_support (void)
{
  if (setjmp (sigill_return))
    {
      return FALSE;
    }
  else
    {
      signal (SIGILL, sigill_handler);
      __asm__ __volatile__ ("xorps %xmm0, %xmm0");
      signal (SIGILL, SIG_DFL);
    }

  return TRUE;
}
#endif /* USE_SSE */

static guint32
arch_accel (void)
{
  guint32 caps;
  X86Vendor vendor;

  vendor = arch_get_vendor ();

  switch (vendor)
    {
    case ARCH_X86_VENDOR_NONE:
      caps = 0;
      break;

    case ARCH_X86_VENDOR_AMD:
    case ARCH_X86_VENDOR_HYGON:
      caps = arch_accel_amd ();
      break;

    case ARCH_X86_VENDOR_CENTAUR:
      caps = arch_accel_centaur ();
      break;

    case ARCH_X86_VENDOR_CYRIX:
    case ARCH_X86_VENDOR_NSC:
      caps = arch_accel_cyrix ();
      break;

    /* check for what Intel speced, even if UNKNOWN */
    default:
      caps = arch_accel_intel ();
      break;
    }

#ifdef USE_SSE
  if ((caps & GIMP_CPU_ACCEL_X86_SSE) && !arch_accel_sse_os_support ())
    caps &= ~(GIMP_CPU_ACCEL_X86_SSE | GIMP_CPU_ACCEL_X86_SSE2);
#endif

  return caps;
}

#endif /* ARCH_X86 && USE_MMX && __GNUC__ */


#if defined(ARCH_PPC) && defined (USE_ALTIVEC)

#if defined(HAVE_ALTIVEC_SYSCTL)

#include <sys/sysctl.h>

#define HAVE_ACCEL 1

static guint32
arch_accel (void)
{
  gint     sels[2] = { CTL_HW, HW_VECTORUNIT };
  gboolean has_vu  = FALSE;
  gsize    length  = sizeof(has_vu);
  gint     err;

  err = sysctl (sels, 2, &has_vu, &length, NULL, 0);

  if (err == 0 && has_vu)
    return GIMP_CPU_ACCEL_PPC_ALTIVEC;

  return 0;
}

#elif defined(__GNUC__)

#define HAVE_ACCEL 1

static          sigjmp_buf   jmpbuf;
static volatile sig_atomic_t canjump = 0;

static void
sigill_handler (gint sig)
{
  if (!canjump)
    {
      signal (sig, SIG_DFL);
      raise (sig);
    }

  canjump = 0;
  siglongjmp (jmpbuf, 1);
}

static guint32
arch_accel (void)
{
  signal (SIGILL, sigill_handler);

  if (sigsetjmp (jmpbuf, 1))
    {
      signal (SIGILL, SIG_DFL);
      return 0;
    }

  canjump = 1;

  asm volatile ("mtspr 256, %0\n\t"
                "vand %%v0, %%v0, %%v0"
                :
                : "r" (-1));

  signal (SIGILL, SIG_DFL);

  return GIMP_CPU_ACCEL_PPC_ALTIVEC;
}
#endif /* __GNUC__ */

#endif /* ARCH_PPC && USE_ALTIVEC */


static GimpCpuAccelFlags
cpu_accel (void)
{
#ifdef HAVE_ACCEL
  static guint32 accel = ~0U;

  if (accel != ~0U)
    return accel;

  accel = arch_accel ();

  return (GimpCpuAccelFlags) accel;

#else /* !HAVE_ACCEL */
  return GIMP_CPU_ACCEL_NONE;
#endif
}

/* --- end libammoos/base/fieldbase/gimpcpuaccel.c --- */

/* --- begin libammoos/base/fieldbase/gimpenv.c --- */
/* LIBGIMP - The AmmoOS Image Library
 * Copyright (C) 1995-1997 Peter Mattis and Spencer Kimball
 *
 * gimpenv.c
 * Copyright (C) 1999 Tor Lillqvist <tml@iki.fi>
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

#include <errno.h>
#include <string.h>
#include <sys/types.h>

#ifdef HAVE_UNISTD_H
#include <unistd.h>
#endif

#ifdef PLATFORM_OSX
#include <AppKit/AppKit.h>
#endif

#include <gio/gio.h>
#include <glib/gstdio.h>

#ifdef G_OS_WIN32
#include "libgimpbase/gimpwin32-io.h"
#endif

#include "gimpbasetypes.h"

#define __GIMP_ENV_C__
#include "gimpenv.h"
#include "gimpenv-private.h"
#include "gimpversion.h"
#include "gimpreloc.h"

#ifdef G_OS_WIN32
#define STRICT
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <io.h>
#ifndef S_IWUSR
# define S_IWUSR _S_IWRITE
#endif
#ifndef S_IWGRP
#define S_IWGRP (_S_IWRITE>>3)
#define S_IWOTH (_S_IWRITE>>6)
#endif
#ifndef S_ISDIR
# define __S_ISTYPE(mode, mask) (((mode) & _S_IFMT) == (mask))
# define S_ISDIR(mode)  __S_ISTYPE((mode), _S_IFDIR)
#endif
#define uid_t gint
#define gid_t gint
#define geteuid() 0
#define getegid() 0

#include <shlobj.h>

/* Constant available since Shell32.dll 4.72 */
#ifndef CSIDL_APPDATA
#define CSIDL_APPDATA 0x001a
#endif

#endif


/**
 * SECTION: gimpenv
 * @title: gimpenv
 * @short_description: Functions to access the AmmoOS Image environment.
 *
 * A set of functions to find the locations of AmmoOS Image's data directories
 * and configuration files.
 **/


static gchar * gimp_env_get_dir   (const gchar *gimp_env_name,
                                   const gchar *compile_time_dir,
                                   const gchar *relative_subdir);


static gchar    *gimp_temp_dir           = NULL;
static gboolean  gimp_temp_dir_generated = FALSE;

const guint gimp_major_version = GIMP_MAJOR_VERSION;
const guint gimp_minor_version = GIMP_MINOR_VERSION;
const guint gimp_micro_version = GIMP_MICRO_VERSION;


/**
 * gimp_env_init:
 * @plug_in: must be %TRUE if this function is called from a plug-in
 *
 * You should never call this function directly. While the symbol is
 * exported, the function is not declared in header and it is therefore
 * neither considered public nor stable.
 *
 * It is being called for you automatically (by means of the
 * [func@Gimp.MAIN] macro that every C plug-in runs or directly with
 * [func@Gimp.main] in binding). Calling it again will cause a fatal
 * error.
 *
 * Since: 2.4
 */
void
gimp_env_init (gboolean plug_in)
{
  static gboolean  gimp_env_initialized = FALSE;
  const gchar     *data_home = g_get_user_data_dir ();

  if (gimp_env_initialized)
    g_error ("gimp_env_init() must only be called once!");

  gimp_env_initialized = TRUE;

#ifndef G_OS_WIN32
  if (plug_in)
    {
      _gimp_reloc_init_lib (NULL);
    }
  else if (_gimp_reloc_init (NULL))
    {
      /* Set $LD_LIBRARY_PATH to ensure that plugins can be loaded. */

      const gchar *ldpath = g_getenv ("LD_LIBRARY_PATH");
      gchar       *libdir = g_build_filename (gimp_installation_directory (),
                                              "lib",
                                              NULL);

      if (ldpath && *ldpath)
        {
          gchar *tmp = g_strconcat (libdir, ":", ldpath, NULL);

          g_setenv ("LD_LIBRARY_PATH", tmp, TRUE);

          g_free (tmp);
        }
      else
        {
          g_setenv ("LD_LIBRARY_PATH", libdir, TRUE);
        }

      g_free (libdir);
    }
#endif

  /* The user data directory (XDG_DATA_HOME on Unix) is used to store
   * various data, like crash logs (win32) or recently used file history
   * (by GTK+). Yet it may be absent, in particular on non-Linux
   * platforms. Make sure it exists.
   */
  if (! g_file_test (data_home, G_FILE_TEST_IS_DIR))
    {
      if (g_mkdir_with_parents (data_home, S_IRUSR | S_IWUSR | S_IXUSR) != 0)
        {
          g_warning ("Failed to create the data directory '%s': %s",
                     data_home, g_strerror (errno));
        }
    }
}

/**
 * gimp_env_exit:
 * @plug_in: must be %TRUE if this function is called from a plug-in
 *
 * You should never call this function directly. While the symbol is
 * exported, the function is not declared in header and it is therefore
 * neither considered public nor stable.
 *
 * It is being called for you automatically (by means of the
 * [func@Gimp.MAIN] macro that every C plug-in runs or directly with
 * [func@Gimp.main] in binding).
 *
 * Since: 3.2.2
 */
void
gimp_env_exit (gboolean plug_in)
{
  if (gimp_temp_dir_generated)
    {
      if (g_rmdir (gimp_temp_dir) == -1)
        g_printerr ("%s: failed to delete the temporary folder `%s`: %s\n",
                    G_STRFUNC, gimp_temp_dir, g_strerror (errno));
    }

  g_clear_pointer (&gimp_temp_dir, g_free);
}

#ifdef G_OS_WIN32

static char *
get_known_folder (REFKNOWNFOLDERID id)
{
  wchar_t *path_utf16 = NULL;
  char    *path       = NULL;

  if (SUCCEEDED (SHGetKnownFolderPath (id, KF_FLAG_DEFAULT, NULL, &path_utf16)))
    path = g_utf16_to_utf8 (path_utf16, -1, NULL, NULL, NULL);

  if (path_utf16)
    CoTaskMemFree (path_utf16);

  return path;
}

extern IMAGE_DOS_HEADER __ImageBase;

static HMODULE
this_module (void)
{
  return (HMODULE) &__ImageBase;
}

#endif

/**
 * gimp_directory:
 *
 * Returns the user-specific AmmoOS Image settings directory. If the
 * environment variable GIMP3_DIRECTORY exists, it is used. If it is
 * an absolute path, it is used as is.  If it is a relative path, it
 * is taken to be a subdirectory of the home directory. If it is a
 * relative path, and no home directory can be determined, it is taken
 * to be a subdirectory of gimp_data_directory().
 *
 * The usual case is that no GIMP3_DIRECTORY environment variable
 * exists, and then we use the GIMPDIR subdirectory of the local
 * configuration directory:
 *
 * - UNIX: $XDG_CONFIG_HOME (defaults to $HOME/.config/)
 *
 * - Windows: CSIDL_APPDATA
 *
 * - OSX (UNIX exception): the Application Support Directory.
 *
 * If neither the configuration nor home directory exist,
 * g_get_user_config_dir() will return {tmp}/{user_name}/.config/ where
 * the temporary directory {tmp} and the {user_name} are determined
 * according to platform rules.
 *
 * In any case, we always return some non-empty string, whether it
 * corresponds to an existing directory or not.
 *
 * In config files such as gimprc, the string ${gimp_dir} expands to
 * this directory.
 *
 * The returned string is owned by AmmoOS Image and must not be modified or
 * freed. The returned string is in the encoding used for filenames by
 * GLib, which isn't necessarily UTF-8 (on Windows it is always
 * UTF-8.)
 *
 * Returns: The user-specific AmmoOS Image settings directory.
 **/
const gchar *
gimp_directory (void)
{
  static gchar *gimp_dir          = NULL;
  static gchar *last_env_gimp_dir = NULL;

  const gchar  *env_gimp_dir;

  env_gimp_dir = g_getenv ("GIMP3_DIRECTORY");

  if (gimp_dir)
    {
      gboolean gimp3_directory_changed = FALSE;

      /* We have constructed the gimp_dir already. We can return
       * gimp_dir unless some parameter gimp_dir depends on has
       * changed. For now we just check for changes to GIMP3_DIRECTORY
       */
      gimp3_directory_changed =
        (env_gimp_dir == NULL &&
         last_env_gimp_dir != NULL) ||
        (env_gimp_dir != NULL &&
         last_env_gimp_dir == NULL) ||
        (env_gimp_dir != NULL &&
         last_env_gimp_dir != NULL &&
         strcmp (env_gimp_dir, last_env_gimp_dir) != 0);

      if (! gimp3_directory_changed)
        {
          return gimp_dir;
        }
      else
        {
          /* Free the old gimp_dir and go on to update it */
          g_free (gimp_dir);
          gimp_dir = NULL;
        }
    }

  /* Remember the GIMP3_DIRECTORY to next invocation so we can check
   * if it changes
   */
  g_free (last_env_gimp_dir);
  last_env_gimp_dir = g_strdup (env_gimp_dir);

  if (env_gimp_dir)
    {
      if (g_path_is_absolute (env_gimp_dir))
        {
          gimp_dir = g_strdup (env_gimp_dir);
        }
      else
        {
          const gchar *home_dir = g_get_home_dir ();

          if (home_dir)
            gimp_dir = g_build_filename (home_dir, env_gimp_dir, NULL);
          else
            gimp_dir = g_build_filename (gimp_data_directory (), env_gimp_dir, NULL);
        }
    }
  else if (g_path_is_absolute (GIMPDIR))
    {
      gimp_dir = g_strdup (GIMPDIR);
    }
  else
    {
#ifdef PLATFORM_OSX

      NSAutoreleasePool *pool;
      NSArray           *path;
      NSString          *library_dir;

      pool = [[NSAutoreleasePool alloc] init];

      path = NSSearchPathForDirectoriesInDomains (NSApplicationSupportDirectory,
                                                  NSUserDomainMask, YES);
      library_dir = [path objectAtIndex:0];

      gimp_dir = g_build_filename ([library_dir UTF8String],
                                   GIMPDIR, GIMP_USER_VERSION, NULL);

      [pool drain];

#elif defined G_OS_WIN32

      char *conf_dir = get_known_folder (&FOLDERID_RoamingAppData);

      gimp_dir = g_build_filename (conf_dir,
                                   GIMPDIR, GIMP_USER_VERSION, NULL);
      g_free(conf_dir);

#else /* UNIX */

      const gchar *snap_path;

      if (g_file_test ("/.flatpak-info", G_FILE_TEST_EXISTS))
        {                       /* Linux flatpak version */
          const gchar *host_xdg_config_home = g_getenv ("HOST_XDG_CONFIG_HOME");

          if (host_xdg_config_home == NULL)
            gimp_dir =  g_build_filename (g_get_home_dir (),
                                          ".config",
                                          GIMPDIR, GIMP_USER_VERSION,
                                          NULL);
          else
            gimp_dir =  g_build_filename (host_xdg_config_home,
                                          GIMPDIR, GIMP_USER_VERSION,
                                          NULL);
        }

      snap_path = g_getenv ("SNAP");
      if (snap_path && g_file_test (snap_path, G_FILE_TEST_IS_DIR))
        {
          const gchar *snap_real_home = g_getenv ("SNAP_REAL_HOME");

          if (snap_real_home == NULL)
            gimp_dir =  g_build_filename (g_get_home_dir (),
                                          ".config",
                                          GIMPDIR, GIMP_USER_VERSION,
                                          NULL);
          else
            gimp_dir =  g_build_filename (snap_real_home,
                                          ".config",
                                          GIMPDIR, GIMP_USER_VERSION,
                                          NULL);
        }

      if (gimp_dir == NULL)
        {
          /* g_get_user_config_dir () always returns a path as a non-null
           * and non-empty string
           */
          gimp_dir = g_build_filename (g_get_user_config_dir (),
                                       GIMPDIR, GIMP_USER_VERSION, NULL);
        }

#endif /* PLATFORM_OSX */
    }

  return gimp_dir;
}

/**
 * gimp_installation_directory:
 *
 * Returns the top installation directory of AmmoOS Image. On Unix the
 * compile-time defined installation prefix is used. On Windows, the
 * installation directory as deduced from the executable's full
 * filename is used. On OSX we ask [NSBundle mainBundle] for the
 * resource path to check if AmmoOS Image is part of a relocatable bundle.
 *
 * In config files such as gimprc, the string ${gimp_installation_dir}
 * expands to this directory.
 *
 * The returned string is owned by AmmoOS Image and must not be modified or
 * freed. The returned string is in the encoding used for filenames by
 * GLib, which isn't necessarily UTF-8. (On Windows it always is
 * UTF-8.)
 *
 * Since: 2.8
 *
 * Returns: The toplevel installation directory of AmmoOS Image.
 **/
const gchar *
gimp_installation_directory (void)
{
  static gchar *toplevel = NULL;

  if (toplevel)
    return toplevel;

#ifdef G_OS_WIN32

  toplevel = g_win32_get_package_installation_directory_of_module (this_module ());
  if (! toplevel)
    g_error ("g_win32_get_package_installation_directory_of_module() failed");

#elif PLATFORM_OSX

  {
    NSAutoreleasePool *pool;
    NSString          *resource_path;
    gchar             *resource_path_test;
    NSString          *app_path;
    gchar             *basename;
    gchar             *basepath;
    gchar             *dirname;

    pool = [[NSAutoreleasePool alloc] init];

    resource_path = [[NSBundle mainBundle] resourcePath];
    app_path = [[NSBundle mainBundle] bundlePath];

    resource_path_test = g_build_filename([resource_path UTF8String], "share",
                                          GIMP_PACKAGE, GIMP_DATA_VERSION, NULL);
    if (g_file_test (resource_path_test, G_FILE_TEST_IS_DIR))
      {
        /* Legacy CircleCI era relocatable code */
        basename = g_path_get_basename ([resource_path UTF8String]);
        basepath = g_path_get_dirname ([resource_path UTF8String]);
      }
    else
      {
         /* Modern GitLab CI era relocatable code */
        basename = g_path_get_basename ([app_path UTF8String]);
        basepath = g_path_get_dirname ([app_path UTF8String]);
      }
    dirname  = g_path_get_basename (basepath);

    if (! strcmp (basename, ".libs"))
      {
        /*  we are running from the source dir, do normal unix things  */

        toplevel = _gimp_reloc_find_prefix (PREFIX);
      }
    else if (! strcmp (basename, "bin"))
      {
        /*  we are running the main app, but not from a bundle, the resource
         *  path is the directory which contains the executable
         */

        toplevel = g_strdup (basepath);
      }
    else if (! strcmp (dirname, "plug-ins") ||
             ! strcmp (dirname, "extensions"))
      {
        /*  same for plug-ins and extensions in subdirectory, go three
         *  levels up from prefix/lib/ammoos/x.y
         */

        gchar *tmp  = g_path_get_dirname (basepath);
        gchar *tmp2 = g_path_get_dirname (tmp);
        gchar *tmp3 = g_path_get_dirname (tmp2);

        toplevel = g_path_get_dirname (tmp3);

        g_free (tmp);
        g_free (tmp2);
        g_free (tmp3);
      }
    else if (strstr (basepath, "/Cellar/"))
      {
        /*  we are running from a Python.framework bundle built in homebrew
         *  during the build phase
         */

        gchar *fulldir = g_strdup (basepath);
        gchar *lastdir = g_path_get_basename (fulldir);
        gchar *tmp_fulldir;

        while (strcmp (lastdir, "Cellar"))
          {
            tmp_fulldir = g_path_get_dirname (fulldir);

            g_free (lastdir);
            g_free (fulldir);

            fulldir = tmp_fulldir;
            lastdir = g_path_get_basename (fulldir);
          }
        toplevel = g_path_get_dirname (fulldir);

        g_free (fulldir);
        g_free (lastdir);
      }
    else
      {
        /*  if none of the above match, we assume that we are really in a bundle  */

        if (g_file_test (resource_path_test, G_FILE_TEST_IS_DIR))
          {
            /* Legacy CircleCI era relocatable prefix */
            toplevel = g_strdup ([resource_path UTF8String]);
          }
        else
          {
            /* Modern GitLab CI era relocatable prefix */
            toplevel = g_strconcat ([app_path UTF8String], "/Contents", NULL);
          }
      }

    g_free (basename);
    g_free (basepath);
    g_free (dirname);
    g_free (resource_path_test);

    [pool drain];
  }

#else

  toplevel = _gimp_reloc_find_prefix (PREFIX);

#endif

  return toplevel;
}

/**
 * gimp_data_directory:
 *
 * Returns the default top directory for AmmoOS Image data. If the environment
 * variable GIMP3_DATADIR exists, that is used.  It should be an
 * absolute pathname.  Otherwise, on Unix the compile-time defined
 * directory is used. On Windows, the installation directory as
 * deduced from the executable's full filename is used.
 *
 * Note that the actual directories used for AmmoOS Image data files can be
 * overridden by the user in the preferences dialog.
 *
 * In config files such as gimprc, the string ${gimp_data_dir} expands
 * to this directory.
 *
 * The returned string is owned by AmmoOS Image and must not be modified or
 * freed. The returned string is in the encoding used for filenames by
 * GLib, which isn't necessarily UTF-8. (On Windows it always is
 * UTF-8.)
 *
 * Returns: The top directory for AmmoOS Image data.
 **/
const gchar *
gimp_data_directory (void)
{
  static gchar *gimp_data_dir = NULL;

  if (! gimp_data_dir)
    {
      gchar *tmp = g_build_filename ("share",
                                     GIMP_PACKAGE,
                                     GIMP_DATA_VERSION,
                                     NULL);

      gimp_data_dir = gimp_env_get_dir ("GIMP3_DATADIR", GIMPDATADIR, tmp);
      g_free (tmp);
    }

  return gimp_data_dir;
}

/**
 * gimp_locale_directory:
 *
 * Returns the top directory for AmmoOS Image locale files. If the environment
 * variable GIMP3_LOCALEDIR exists, that is used.  It should be an
 * absolute pathname.  Otherwise, on Unix the compile-time defined
 * directory is used. On Windows, the installation directory as deduced
 * from the executable's full filename is used.
 *
 * The returned string is owned by AmmoOS Image and must not be modified or
 * freed. The returned string encoding depends on the system where AmmoOS Image
 * is running: on UNIX it's in the encoding used for filenames by
 * the C library (which isn't necessarily UTF-8); on Windows it's UTF-8.
 *
 * On UNIX the returned string can be passed directly to the bindtextdomain()
 * function from libintl; on Windows the returned string can be converted to
 * UTF-16 and passed to the wbindtextdomain() function from libintl.
 *
 * Returns: (type filename): The top directory for AmmoOS Image locale files.
 */
const gchar *
gimp_locale_directory (void)
{
  static gchar *gimp_locale_dir = NULL;

  if (! gimp_locale_dir)
    {
      gchar *tmp = g_build_filename ("share",
                                     "locale",
                                     NULL);

      gimp_locale_dir = gimp_env_get_dir ("GIMP3_LOCALEDIR", LOCALEDIR, tmp);
      g_free (tmp);
    }

  return gimp_locale_dir;
}

/**
 * gimp_sysconf_directory:
 *
 * Returns the top directory for AmmoOS Image config files. If the environment
 * variable GIMP3_SYSCONFDIR exists, that is used.  It should be an
 * absolute pathname.  Otherwise, on Unix the compile-time defined
 * directory is used. On Windows, the installation directory as deduced
 * from the executable's full filename is used.
 *
 * In config files such as gimprc, the string ${gimp_sysconf_dir}
 * expands to this directory.
 *
 * The returned string is owned by AmmoOS Image and must not be modified or
 * freed. The returned string is in the encoding used for filenames by
 * GLib, which isn't necessarily UTF-8. (On Windows it always is
 * UTF-8.).
 *
 * Returns: The top directory for AmmoOS Image config files.
 **/
const gchar *
gimp_sysconf_directory (void)
{
  static gchar *gimp_sysconf_dir = NULL;

  if (! gimp_sysconf_dir)
    {
      gchar *tmp = g_build_filename ("etc",
                                     GIMP_PACKAGE,
                                     GIMP_SYSCONF_VERSION,
                                     NULL);

      gimp_sysconf_dir = gimp_env_get_dir ("GIMP3_SYSCONFDIR", GIMPSYSCONFDIR, tmp);
      g_free (tmp);
    }

  return gimp_sysconf_dir;
}

/**
 * gimp_plug_in_directory:
 *
 * Returns the default top directory for AmmoOS Image plug-ins and modules. If
 * the environment variable GIMP3_PLUGINDIR exists, that is used.  It
 * should be an absolute pathname. Otherwise, on Unix the compile-time
 * defined directory is used. On Windows, the installation directory
 * as deduced from the executable's full filename is used.
 *
 * Note that the actual directories used for AmmoOS Image plug-ins and modules
 * can be overridden by the user in the preferences dialog.
 *
 * In config files such as gimprc, the string ${gimp_plug_in_dir}
 * expands to this directory.
 *
 * The returned string is owned by AmmoOS Image and must not be modified or
 * freed. The returned string is in the encoding used for filenames by
 * GLib, which isn't necessarily UTF-8. (On Windows it always is
 * UTF-8.)
 *
 * Returns: The top directory for AmmoOS Image plug_ins and modules.
 **/
const gchar *
gimp_plug_in_directory (void)
{
  static gchar *gimp_plug_in_dir = NULL;

  if (! gimp_plug_in_dir)
    {
      gchar *tmp = g_build_filename ("lib",
                                     GIMP_PACKAGE,
                                     GIMP_PLUGIN_VERSION,
                                     NULL);

      gimp_plug_in_dir = gimp_env_get_dir ("GIMP3_PLUGINDIR", PLUGINDIR, tmp);
      g_free (tmp);
    }

  return gimp_plug_in_dir;
}

/**
 * gimp_cache_directory:
 *
 * Returns the default top directory for AmmoOS Image cached files. If the
 * environment variable GIMP3_CACHEDIR exists, that is used.  It
 * should be an absolute pathname.  Otherwise, a subdirectory of the
 * directory returned by g_get_user_cache_dir() is used.
 *
 * Note that the actual directories used for AmmoOS Image caches files can
 * be overridden by the user in the preferences dialog.
 *
 * In config files such as gimprc, the string ${gimp_cache_dir}
 * expands to this directory.
 *
 * The returned string is owned by AmmoOS Image and must not be modified or
 * freed. The returned string is in the encoding used for filenames by
 * GLib, which isn't necessarily UTF-8. (On Windows it always is
 * UTF-8.).
 *
 * Since: 2.10.10
 *
 * Returns: The default top directory for AmmoOS Image cached files.
 **/
const gchar *
gimp_cache_directory (void)
{
  static gchar *gimp_cache_dir = NULL;

  if (! gimp_cache_dir)
    {
      gchar *tmp = g_build_filename (g_get_user_cache_dir (),
                                     GIMP_PACKAGE,
                                     GIMP_USER_VERSION,
                                     NULL);

      gimp_cache_dir = gimp_env_get_dir ("GIMP3_CACHEDIR", NULL, tmp);
      g_free (tmp);
    }

  return gimp_cache_dir;
}

/**
 * gimp_temp_directory:
 *
 * Returns the default top directory for AmmoOS Image temporary files. If the
 * environment variable `GIMP3_TEMPDIR` exists, that is used. It
 * should be an absolute pathname. Otherwise, a subdirectory of the
 * directory returned by [func@GLib.get_tmp_dir] is used.
 *
 * In config files such as gimprc, the string ${gimp_temp_dir} expands
 * to this directory.
 *
 * Note that the actual directories used for AmmoOS Image temporary files can
 * be overridden by the user in the preferences dialog.
 *
 * The returned string is owned by AmmoOS Image and must not be modified or
 * freed. The returned string is in the encoding used for filenames by
 * GLib, which isn't necessarily UTF-8 (On Windows it always is UTF-8.).
 *
 * The returned directory path might already exists, or it might not. It
 * is your responsibility to make sure it does before using it.
 *
 * Since: 2.10.10
 *
 * Returns: The default top directory for AmmoOS Image temporary files.
 **/
const gchar *
gimp_temp_directory (void)
{
  if (! gimp_temp_dir)
    {
      GError *error = NULL;

      gimp_temp_dir = gimp_env_get_dir ("GIMP3_TEMPDIR", NULL, NULL);
      if (gimp_temp_dir)
        return gimp_temp_dir;

      gimp_temp_dir = g_dir_make_tmp (GIMP_PACKAGE "-" GIMP_USER_VERSION "-XXXXXXX", &error);
      gimp_temp_dir_generated = TRUE;
      if (gimp_temp_dir == NULL)
        {
          g_critical ("%s: failed to create temporary directory: %s\n",
                      G_STRFUNC, error->message);
          g_clear_error (&error);

          gimp_temp_dir_generated = FALSE;
        }
    }

  return gimp_temp_dir;
}

static GFile *
gimp_child_file (const gchar *parent,
                 const gchar *element,
                 va_list      args)
{
  GFile *file = g_file_new_for_path (parent);

  while (element)
    {
      GFile *child = g_file_get_child (file, element);

      g_object_unref (file);
      file = child;

      element = va_arg (args, const gchar *);
    }

  return file;
}

/**
 * gimp_directory_file: (skip)
 * @first_element: the first element of a path to a file in the
 *                 user's AmmoOS Image directory, or %NULL.
 * @...: a %NULL terminated list of the remaining elements of the path
 *       to the file.
 *
 * Returns a #GFile in the user's AmmoOS Image directory, or the AmmoOS Image
 * directory itself if @first_element is %NULL.
 *
 * See also: gimp_directory().
 *
 * Since: 2.10
 *
 * Returns: (transfer full):
 *          a new @GFile for the path, Free with g_object_unref().
 **/
GFile *
gimp_directory_file (const gchar *first_element,
                     ...)
{
  GFile   *file;
  va_list  args;

  va_start (args, first_element);
  file = gimp_child_file (gimp_directory (), first_element, args);
  va_end (args);

  return file;
}

/**
 * gimp_installation_directory_file: (skip)
 * @first_element: the first element of a path to a file in the
 *                 top installation directory, or %NULL.
 * @...: a %NULL terminated list of the remaining elements of the path
 *       to the file.
 *
 * Returns a #GFile in the installation directory, or the installation
 * directory itself if @first_element is %NULL.
 *
 * See also: gimp_installation_directory().
 *
 * Since: 2.10.10
 *
 * Returns: (transfer full):
 *          a new @GFile for the path, Free with g_object_unref().
 **/
GFile *
gimp_installation_directory_file (const gchar *first_element,
                                  ...)
{
  GFile   *file;
  va_list  args;

  va_start (args, first_element);
  file = gimp_child_file (gimp_installation_directory (), first_element, args);
  va_end (args);

  return file;
}

/**
 * gimp_data_directory_file: (skip)
 * @first_element: the first element of a path to a file in the
 *                 data directory, or %NULL.
 * @...: a %NULL terminated list of the remaining elements of the path
 *       to the file.
 *
 * Returns a #GFile in the data directory, or the data directory
 * itself if @first_element is %NULL.
 *
 * See also: gimp_data_directory().
 *
 * Since: 2.10
 *
 * Returns: (transfer full):
 *          a new @GFile for the path, Free with g_object_unref().
 **/
GFile *
gimp_data_directory_file (const gchar *first_element,
                          ...)
{
  GFile   *file;
  va_list  args;

  va_start (args, first_element);
  file = gimp_child_file (gimp_data_directory (), first_element, args);
  va_end (args);

  return file;
}

/**
 * gimp_locale_directory_file: (skip)
 * @first_element: the first element of a path to a file in the
 *                 locale directory, or %NULL.
 * @...: a %NULL terminated list of the remaining elements of the path
 *       to the file.
 *
 * Returns a #GFile in the locale directory, or the locale directory
 * itself if @first_element is %NULL.
 *
 * See also: gimp_locale_directory().
 *
 * Since: 2.10
 *
 * Returns: (transfer full):
 *          a new @GFile for the path, Free with g_object_unref().
 **/
GFile *
gimp_locale_directory_file (const gchar *first_element,
                            ...)
{
  GFile   *file;
  va_list  args;

  va_start (args, first_element);
  file = gimp_child_file (gimp_locale_directory (), first_element, args);
  va_end (args);

  return file;
}

/**
 * gimp_sysconf_directory_file:
 * @first_element: the first element of a path to a file in the
 *                 sysconf directory, or %NULL.
 * @...: a %NULL terminated list of the remaining elements of the path
 *       to the file.
 *
 * Returns a #GFile in the sysconf directory, or the sysconf directory
 * itself if @first_element is %NULL.
 *
 * See also: gimp_sysconf_directory().
 *
 * Since: 2.10
 *
 * Returns: (transfer full):
 *          a new @GFile for the path, Free with g_object_unref().
 **/
GFile *
gimp_sysconf_directory_file (const gchar *first_element,
                             ...)
{
  GFile   *file;
  va_list  args;

  va_start (args, first_element);
  file = gimp_child_file (gimp_sysconf_directory (), first_element, args);
  va_end (args);

  return file;
}

/**
 * gimp_plug_in_directory_file:
 * @first_element: the first element of a path to a file in the
 *                 plug-in directory, or %NULL.
 * @...: a %NULL terminated list of the remaining elements of the path
 *       to the file.
 *
 * Returns a #GFile in the plug-in directory, or the plug-in directory
 * itself if @first_element is %NULL.
 *
 * See also: gimp_plug_in_directory().
 *
 * Since: 2.10
 *
 * Returns: (transfer full):
 *          a new @GFile for the path, Free with g_object_unref().
 **/
GFile *
gimp_plug_in_directory_file (const gchar *first_element,
                             ...)
{
  GFile   *file;
  va_list  args;

  va_start (args, first_element);
  file = gimp_child_file (gimp_plug_in_directory (), first_element, args);
  va_end (args);

  return file;
}

/**
 * gimp_path_runtime_fix:
 * @path: A pointer to a string (allocated with g_malloc) that is
 *        (or could be) a pathname.
 *
 * On Windows, this function checks if the string pointed to by @path
 * starts with the compile-time prefix, and in that case, replaces the
 * prefix with the run-time one.  @path should be a pointer to a
 * dynamically allocated (with g_malloc, g_strconcat, etc) string. If
 * the replacement takes place, the original string is deallocated,
 * and *@path is replaced with a pointer to a new string with the
 * run-time prefix spliced in.
 *
 * On Linux and other Unices, it does the same thing, but only if BinReloc
 * support is enabled, and only if we are not running AmmoOS Image in-build directory.
 */
static void
gimp_path_runtime_fix (gchar **path)
{
#if defined (G_OS_WIN32) && defined (PREFIX)
  gchar *p;

  /* Yes, I do mean forward slashes below */
  if (strncmp (*path, PREFIX "/", strlen (PREFIX "/")) == 0)
    {
      /* This is a compile-time entry. Replace the path with the
       * real one on this machine.
       */
      p = *path;
      *path = g_strconcat (gimp_installation_directory (),
                           "\\",
                           *path + strlen (PREFIX "/"),
                           NULL);
      g_free (p);
    }
  /* Replace forward slashes with backslashes, just for
   * completeness */
  p = *path;
  while ((p = strchr (p, '/')) != NULL)
    {
      *p = '\\';
      p++;
    }
#elif defined (G_OS_WIN32)
  /* without defineing PREFIX do something useful too */
  gchar *p = *path;
  if (!g_path_is_absolute (p))
    {
      *path = g_build_filename (gimp_installation_directory (), *path, NULL);
      g_free (p);
    }
#elif defined (ENABLE_RELOCATABLE_RESOURCES)
  gchar *p;

  /* XXX: I could actually test any of the other GIMP_TESTING_* environment
   * variables. The goal is only to check if we are running AmmoOS Image from within the
   * build directory. In such case, no substitution should happen.
   */
  if (! g_getenv ("GIMP_TESTING_PLUGINDIRS") &&
      strncmp (*path, PREFIX G_DIR_SEPARATOR_S,
               strlen (PREFIX G_DIR_SEPARATOR_S)) == 0)
    {
      /* This is a compile-time entry. Replace the path with the
       * real one on this machine.
       */
      p = *path;
      *path = g_build_filename (gimp_installation_directory (),
                                *path + strlen (PREFIX G_DIR_SEPARATOR_S),
                                NULL);
      g_free (p);
    }
#endif
}

/**
 * gimp_path_parse:
 * @path:         A list of directories separated by #G_SEARCHPATH_SEPARATOR.
 * @max_paths:    The maximum number of directories to return.
 * @check:        %TRUE if you want the directories to be checked.
 * @check_failed: (element-type filename) (out callee-allocates):
                  Returns a #GList of path elements for which the check failed.
 *
 * Returns: (element-type filename) (transfer full):
            A #GList of all directories in @path.
 **/
GList *
gimp_path_parse (const gchar  *path,
                 gint          max_paths,
                 gboolean      check,
                 GList       **check_failed)
{
  gchar    **patharray;
  GList     *list      = NULL;
  GList     *fail_list = NULL;
  gint       i;
  gboolean   exists    = TRUE;

  if (!path || !*path || max_paths < 1 || max_paths > 256)
    return NULL;

  patharray = g_strsplit (path, G_SEARCHPATH_SEPARATOR_S, max_paths);

  for (i = 0; i < max_paths; i++)
    {
      GString *dir;

      if (! patharray[i])
        break;

#ifndef G_OS_WIN32
      if (*patharray[i] == '~')
        {
          dir = g_string_new (g_get_home_dir ());
          g_string_append (dir, patharray[i] + 1);
        }
      else
#endif
        {
          gimp_path_runtime_fix (&patharray[i]);
          dir = g_string_new (patharray[i]);
        }

      if (check)
        exists = g_file_test (dir->str, G_FILE_TEST_IS_DIR);

      if (exists)
        {
          GList *dup;

          /*  check for duplicate entries, see bug #784502  */
          for (dup = list; dup; dup = g_list_next (dup))
            {
              if (! strcmp (dir->str, dup->data))
                break;
            }

          /*  only add to the list if it's not a duplicate  */
          if (! dup)
            list = g_list_prepend (list, g_strdup (dir->str));
        }
      else if (check_failed)
        {
          fail_list = g_list_prepend (fail_list, g_strdup (dir->str));
        }

      g_string_free (dir, TRUE);
    }

  g_strfreev (patharray);

  list = g_list_reverse (list);

  if (check && check_failed)
    {
      fail_list = g_list_reverse (fail_list);
      *check_failed = fail_list;
    }

  return list;
}

/**
 * gimp_path_to_str:
 * @path: (element-type filename):
 *        A list of directories as returned by gimp_path_parse().
 *
 * Returns: (type filename) (transfer full):
 *          A searchpath string separated by #G_SEARCHPATH_SEPARATOR.
 **/
gchar *
gimp_path_to_str (GList *path)
{
  GString *str    = NULL;
  GList   *list;
  gchar   *retval = NULL;

  for (list = path; list; list = g_list_next (list))
    {
      gchar *dir = list->data;

      if (str)
        {
          g_string_append_c (str, G_SEARCHPATH_SEPARATOR);
          g_string_append (str, dir);
        }
      else
        {
          str = g_string_new (dir);
        }
    }

  if (str)
    retval = g_string_free (str, FALSE);

  return retval;
}

/**
 * gimp_path_free:
 * @path: (element-type filename):
 *        A list of directories as returned by gimp_path_parse().
 *
 * This function frees the memory allocated for the list and the strings
 * it contains.
 **/
void
gimp_path_free (GList *path)
{
  g_list_free_full (path, (GDestroyNotify) g_free);
}

/**
 * gimp_path_get_user_writable_dir:
 * @path: (element-type filename):
 *        A list of directories as returned by gimp_path_parse().
 *
 * Note that you have to g_free() the returned string.
 *
 * Returns: The first directory in @path where the user has write permission.
 **/
gchar *
gimp_path_get_user_writable_dir (GList *path)
{
  GList    *list;
  uid_t     euid;
  gid_t     egid;
  GStatBuf  filestat;
  gint      err;

  g_return_val_if_fail (path != NULL, NULL);

  euid = geteuid ();
  egid = getegid ();

  for (list = path; list; list = g_list_next (list))
    {
      gchar *dir = list->data;

      /*  check if directory exists  */
      err = g_stat (dir, &filestat);

      /*  this is tricky:
       *  if a file is e.g. owned by the current user but not user-writable,
       *  the user has no permission to write to the file regardless
       *  of their group's or other's write permissions
       */
      if (!err && S_ISDIR (filestat.st_mode) &&

          ((filestat.st_mode & S_IWUSR) ||

           ((filestat.st_mode & S_IWGRP) &&
            (euid != filestat.st_uid)) ||

           ((filestat.st_mode & S_IWOTH) &&
            (euid != filestat.st_uid) &&
            (egid != filestat.st_gid))))
        {
          return g_strdup (dir);
        }
    }

  return NULL;
}

static gchar *
gimp_env_get_dir (const gchar *gimp_env_name,
                  const gchar *compile_time_dir,
                  const gchar *relative_subdir)
{
  const gchar *env = g_getenv (gimp_env_name);

  if (env)
    {
      if (! g_path_is_absolute (env))
        g_error ("%s environment variable should be an absolute path.",
                 gimp_env_name);

      return g_strdup (env);
    }
  else if (compile_time_dir)
    {
      gchar *retval = g_strdup (compile_time_dir);

      gimp_path_runtime_fix (&retval);

      return retval;
    }
  else if (relative_subdir && ! g_path_is_absolute (relative_subdir))
    {
      return g_build_filename (gimp_installation_directory (),
                               relative_subdir,
                               NULL);
    }

  return g_strdup (relative_subdir);
}

/* --- end libammoos/base/fieldbase/gimpenv.c --- */

/* --- begin libammoos/base/fieldbase/gimpexportoptions.c --- */
/* AmmoOS Image - The AmmoOS Field Image Research
 * Copyright (C) 1995 Spencer Kimball and Peter Mattis
 *
 * gimpexportoptions.h
 * Copyright (C) 2024 Alx Sa.
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

#include "gimpbasetypes.h"

#include "gimpexportoptions.h"

/**
 * SECTION: gimpexportoptions
 * @title: gimpexportoptions
 * @short_description: Generic Export Options
 *
 * A class holding generic export options.

 * Note: right now, AmmoOS Image does not provide any generic export option to
 * manipulate, and there is practically no reason for you to create this
 * object yourself. In Export PDB procedure, or again in functions such
 * as [func@Gimp.file_save], you may just pass %NULL.
 *
 * In the future, this object will enable to pass various generic
 * options, such as ability to crop or resize images at export time.
 **/

enum
{
  PROP_0,
  PROP_CAPABILITIES,
  N_PROPS
};

struct _GimpExportOptions
{
  GObject                 parent_instance;

  GimpExportCapabilities  capabilities;
};


static void   gimp_export_options_finalize      (GObject              *object);
static void   gimp_export_options_set_property  (GObject              *object,
                                                 guint                 property_id,
                                                 const GValue         *value,
                                                 GParamSpec           *pspec);
static void   gimp_export_options_get_property  (GObject              *object,
                                                 guint                 property_id,
                                                 GValue               *value,
                                                 GParamSpec           *pspec);


G_DEFINE_TYPE (GimpExportOptions, gimp_export_options, G_TYPE_OBJECT)

#define parent_class gimp_export_options_parent_class

static GParamSpec *props[N_PROPS] = { NULL, };

static void
gimp_export_options_class_init (GimpExportOptionsClass *klass)
{
  GObjectClass *object_class = G_OBJECT_CLASS (klass);

  object_class->finalize     = gimp_export_options_finalize;
  object_class->get_property = gimp_export_options_get_property;
  object_class->set_property = gimp_export_options_set_property;

  /**
   * GimpExportOptions:capabilities:
   *
   * What [flags@ExportCapabilities] are supported.
   *
   * Since: 3.0.0
   */
  props[PROP_CAPABILITIES] = g_param_spec_flags ("capabilities",
                                                 "Supported image capabilities",
                                                 NULL,
                                                 GIMP_TYPE_EXPORT_CAPABILITIES,
                                                 0,
                                                 G_PARAM_CONSTRUCT |
                                                 G_PARAM_READWRITE);

  g_object_class_install_properties (object_class, N_PROPS, props);
}

static void
gimp_export_options_init (GimpExportOptions *options)
{
  options->capabilities = 0;
}

static void
gimp_export_options_finalize (GObject *object)
{
  G_OBJECT_CLASS (parent_class)->finalize (object);
}

static void
gimp_export_options_set_property (GObject      *object,
                                  guint         property_id,
                                  const GValue *value,
                                  GParamSpec   *pspec)
{
  GimpExportOptions *options = GIMP_EXPORT_OPTIONS (object);

  switch (property_id)
    {
    case PROP_CAPABILITIES:
      options->capabilities = g_value_get_flags (value);
      break;

    default:
      G_OBJECT_WARN_INVALID_PROPERTY_ID (object, property_id, pspec);
      break;
    }
}

static void
gimp_export_options_get_property (GObject    *object,
                                  guint       property_id,
                                  GValue     *value,
                                  GParamSpec *pspec)
{
  GimpExportOptions *options = GIMP_EXPORT_OPTIONS (object);

  switch (property_id)
    {
    case PROP_CAPABILITIES:
      g_value_set_flags (value, options->capabilities);
      break;

    default:
      G_OBJECT_WARN_INVALID_PROPERTY_ID (object, property_id, pspec);
      break;
    }
}


/*
 * GIMP_TYPE_PARAM_EXPORT_OPTIONS
 */

static void       gimp_param_export_options_class_init        (GParamSpecClass *klass);
static void       gimp_param_export_options_init              (GParamSpec      *pspec);

GType
gimp_param_export_options_get_type (void)
{
  static GType type = 0;

  if (! type)
    {
      const GTypeInfo info =
      {
        sizeof (GParamSpecClass),
        NULL, NULL,
        (GClassInitFunc) gimp_param_export_options_class_init,
        NULL, NULL,
        sizeof (GParamSpecObject),
        0,
        (GInstanceInitFunc) gimp_param_export_options_init
      };

      type = g_type_register_static (G_TYPE_PARAM_OBJECT,
                                     "GimpParamExportOptions", &info, 0);
    }

  return type;
}

static void
gimp_param_export_options_class_init (GParamSpecClass *klass)
{
  klass->value_type = GIMP_TYPE_EXPORT_OPTIONS;
}

static void
gimp_param_export_options_init (GParamSpec *pspec)
{
}

/**
 * gimp_param_spec_export_options:
 * @name:         Canonical name of the property specified.
 * @nick:         Nick name of the property specified.
 * @blurb:        Description of the property specified.
 * @flags:        Flags for the property specified.
 *
 * Creates a new #GimpParamSpecExportOptions specifying a
 * #G_TYPE_INT property.
 *
 * See g_param_spec_internal() for details on property names.
 *
 * Returns: (transfer floating): The newly created #GimpParamSpecExportOptions.
 *
 * Since: 3.0
 **/
GParamSpec *
gimp_param_spec_export_options (const gchar *name,
                                const gchar *nick,
                                const gchar *blurb,
                                GParamFlags  flags)
{
  GParamSpec *options_spec;

  options_spec = g_param_spec_internal (GIMP_TYPE_PARAM_EXPORT_OPTIONS,
                                        name, nick, blurb, flags);

  g_return_val_if_fail (options_spec, NULL);

  return options_spec;
}

/* --- end libammoos/base/fieldbase/gimpexportoptions.c --- */

/* --- begin libammoos/base/fieldbase/gimpmemsize.c --- */
/* LIBGIMP - The AmmoOS Image Library
 * Copyright (C) 1995-1997 Peter Mattis and Spencer Kimball
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

#include <errno.h>

#include <glib-object.h>

#include "gimpbasetypes.h"

#include "gimpmemsize.h"

#include "libgimp/libgimp-intl.h"


/**
 * SECTION: gimpmemsize
 * @title: gimpmemsize
 * @short_description: Functions to (de)serialize a given memory size.
 *
 * Functions to (de)serialize a given memory size.
 **/


static void   memsize_to_string (const GValue *src_value,
                                 GValue       *dest_value);
static void   string_to_memsize (const GValue *src_value,
                                 GValue       *dest_value);


GType
gimp_memsize_get_type (void)
{
  static GType memsize_type = 0;

  if (! memsize_type)
    {
      const GTypeInfo type_info = { 0, };

      memsize_type = g_type_register_static (G_TYPE_UINT64, "GimpMemsize",
                                             &type_info, 0);

      g_value_register_transform_func (memsize_type, G_TYPE_STRING,
                                       memsize_to_string);
      g_value_register_transform_func (G_TYPE_STRING, memsize_type,
                                       string_to_memsize);
    }

  return memsize_type;
}

/**
 * gimp_memsize_serialize:
 * @memsize: memory size in bytes
 *
 * Creates a string representation of a given memory size. This string
 * can be parsed by gimp_memsize_deserialize() and can thus be used in
 * config files. It should not be displayed to the user. If you need a
 * nice human-readable string please use g_format_size().
 *
 * Returns: A newly allocated string representation of @memsize.
 *
 * Since: 2.2
 **/
gchar *
gimp_memsize_serialize (guint64 memsize)
{
  if (memsize > (1 << 30) && memsize % (1 << 30) == 0)
    return g_strdup_printf ("%" G_GUINT64_FORMAT "G", memsize >> 30);
  else if (memsize > (1 << 20) && memsize % (1 << 20) == 0)
    return g_strdup_printf ("%" G_GUINT64_FORMAT "M", memsize >> 20);
  else if (memsize > (1 << 10) && memsize % (1 << 10) == 0)
    return g_strdup_printf ("%" G_GUINT64_FORMAT "k", memsize >> 10);
  else
    return g_strdup_printf ("%" G_GUINT64_FORMAT, memsize);
}

/**
 * gimp_memsize_deserialize:
 * @string:  a string as returned by gimp_memsize_serialize()
 * @memsize: (out): return location for memory size in bytes
 *
 * Parses a string representation of a memory size as returned by
 * gimp_memsize_serialize().
 *
 * Returns: %TRUE if the @string was successfully parsed and
 *               @memsize has been set, %FALSE otherwise.
 *
 * Since: 2.2
 **/
gboolean
gimp_memsize_deserialize (const gchar *string,
                          guint64     *memsize)
{
  gchar   *end;
  guint64  size;

  g_return_val_if_fail (string != NULL, FALSE);
  g_return_val_if_fail (memsize != NULL, FALSE);

  size = g_ascii_strtoull (string, &end, 0);

  if (size == G_MAXUINT64 && errno == ERANGE)
    return FALSE;

  if (end && *end)
    {
      guint shift;

      switch (g_ascii_tolower (*end))
        {
        case 'b':
          shift = 0;
          break;
        case 'k':
          shift = 10;
          break;
        case 'm':
          shift = 20;
          break;
        case 'g':
          shift = 30;
          break;
        default:
          return FALSE;
        }

      /* protect against overflow */
      if (shift)
        {
          guint64  limit = G_MAXUINT64 >> shift;

          if (size != (size & limit))
            return FALSE;

          size <<= shift;
        }
    }

  *memsize = size;

  return TRUE;
}


static void
memsize_to_string (const GValue *src_value,
                   GValue       *dest_value)
{
  g_value_take_string (dest_value,
                       gimp_memsize_serialize (g_value_get_uint64 (src_value)));
}

static void
string_to_memsize (const GValue *src_value,
                   GValue       *dest_value)
{
  const gchar *str;
  guint64      memsize;

  str = g_value_get_string (src_value);

  if (str && gimp_memsize_deserialize (str, &memsize))
    {
      g_value_set_uint64 (dest_value, memsize);
    }
  else
    {
      g_warning ("Can't convert string to GimpMemsize.");
    }
}


/*
 * GIMP_TYPE_PARAM_MEMSIZE
 */

static void  gimp_param_memsize_class_init (GParamSpecClass *class);

/**
 * gimp_param_memsize_get_type:
 *
 * Reveals the object type
 *
 * Returns: the #GType for a memsize object
 *
 * Since: 2.4
 **/
GType
gimp_param_memsize_get_type (void)
{
  static GType spec_type = 0;

  if (! spec_type)
    {
      const GTypeInfo type_info =
      {
        sizeof (GParamSpecClass),
        NULL, NULL,
        (GClassInitFunc) gimp_param_memsize_class_init,
        NULL, NULL,
        sizeof (GParamSpecUInt64),
        0, NULL, NULL
      };

      spec_type = g_type_register_static (G_TYPE_PARAM_UINT64,
                                          "GimpParamMemsize",
                                          &type_info, 0);
    }

  return spec_type;
}

static void
gimp_param_memsize_class_init (GParamSpecClass *class)
{
  class->value_type = GIMP_TYPE_MEMSIZE;
}

/**
 * gimp_param_spec_memsize:
 * @name:          Canonical name of the param
 * @nick:          Nickname of the param
 * @blurb:         Brief description of param.
 * @minimum:       Smallest allowed value of the parameter.
 * @maximum:       Largest allowed value of the parameter.
 * @default_value: Value to use if none is assigned.
 * @flags:         a combination of #GParamFlags
 *
 * Creates a param spec to hold a memory size value.
 * See g_param_spec_internal() for more information.
 *
 * Returns: (transfer full): a newly allocated #GParamSpec instance
 *
 * Since: 2.4
 **/
GParamSpec *
gimp_param_spec_memsize (const gchar *name,
                         const gchar *nick,
                         const gchar *blurb,
                         guint64      minimum,
                         guint64      maximum,
                         guint64      default_value,
                         GParamFlags  flags)
{
  GParamSpecUInt64 *pspec;

  pspec = g_param_spec_internal (GIMP_TYPE_PARAM_MEMSIZE,
                                 name, nick, blurb, flags);

  pspec->minimum       = minimum;
  pspec->maximum       = maximum;
  pspec->default_value = default_value;

  return G_PARAM_SPEC (pspec);
}


/* --- end libammoos/base/fieldbase/gimpmemsize.c --- */

/* --- begin libammoos/base/fieldbase/gimpmetadata.c --- */
/* LIBGIMPBASE - The AmmoOS Image Basic Library
 * Copyright (C) 1995-1997 Peter Mattis and Spencer Kimball
 *
 * gimpmetadata.c
 * Copyright (C) 2013 Hartmut Kuhse <hartmutkuhse@src.gnome.org>
 *                    Michael Natterer <mitch@ammoos.org>
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

#include <stdlib.h>
#include <string.h>

#include <gegl.h>
#include <gio/gio.h>

#include "libgimpbase/gimpversion-private.h"
#include "libgimpmath/gimpmath.h"

#include "gimpbasetypes.h"
#include "gimpversion.h"

#include "gimplimits.h"
#include "gimpmetadata.h"
#include "gimpparamspecs.h"
#include "gimpunit.h"

#include "libgimp/libgimp-intl.h"


GIMP_WARNING_API_BREAK("libgimpbase/gimpmetadata.h: rename GIMP_METADATA_SAVE_UPDATE as GIMP_METADATA_UPDATE?")

/**
 * SECTION: gimpmetadata
 * @title: GimpMetadata
 * @short_description: Basic functions for handling #GimpMetadata objects.
 *
 * Basic functions for handling #GimpMetadata objects.
 **/

struct _GimpMetadata
{
  GExiv2Metadata parent_instance;
};

#define GIMP_METADATA_ERROR gimp_metadata_error_quark ()

static GQuark   gimp_metadata_error_quark     (void);
static void     gimp_metadata_copy_tag        (GExiv2Metadata  *src,
                                               GExiv2Metadata  *dest,
                                               const gchar     *tag);
static void     gimp_metadata_copy_tags       (GExiv2Metadata  *src,
                                               GExiv2Metadata  *dest,
                                               const gchar    **tags);
static void     gimp_metadata_add             (GimpMetadata    *src,
                                               GimpMetadata    *dest);
static void     gimp_metadata_add_namespace   (GHashTable      *namespaces,
                                               GString         *xml,
                                               gchar           *prefix);
static void gimp_metadata_add_xmp_namespaces  (GHashTable      *namespaces,
                                               GString         *xml,
                                               const gchar     *tag);


static const gchar *tiff_tags[] =
{
  "Xmp.tiff",
  "Exif.Image.ImageWidth",
  "Exif.Image.ImageLength",
  "Exif.Image.BitsPerSample",
  "Exif.Image.Compression",
  "Exif.Image.PhotometricInterpretation",
  "Exif.Image.FillOrder",
  "Exif.Image.SamplesPerPixel",
  "Exif.Image.StripOffsets",
  "Exif.Image.RowsPerStrip",
  "Exif.Image.StripByteCounts",
  "Exif.Image.PlanarConfiguration"
};

static const gchar *jpeg_tags[] =
{
  "Exif.Image.JPEGProc",
  "Exif.Image.JPEGInterchangeFormat",
  "Exif.Image.JPEGInterchangeFormatLength",
  "Exif.Image.JPEGRestartInterval",
  "Exif.Image.JPEGLosslessPredictors",
  "Exif.Image.JPEGPointTransforms",
  "Exif.Image.JPEGQTables",
  "Exif.Image.JPEGDCTables",
  "Exif.Image.JPEGACTables"
};

static const gchar *unsupported_tags[] =
{
  "Exif.Image.SubIFDs",
  "Exif.Image.ClipPath",
  "Exif.Image.XClipPathUnits",
  "Exif.Image.YClipPathUnits",
  "Exif.Image.XPTitle",
  "Exif.Image.XPComment",
  "Exif.Image.XPAuthor",
  "Exif.Image.XPKeywords",
  "Exif.Image.XPSubject",
  "Exif.Image.DNGVersion",
  "Exif.Image.DNGBackwardVersion",
  "Exif.Iop",
  /* FIXME Even though adding the tags below fixes the issue it's not very flexible.
     It might be better in the long run if there was a way for a user to configure which
     tags to block or a way for us to detect problems with tags before writing them. */
  /* Issues #1367, #2253. Offending tag is PreviewOffset but the other Preview tags
     (PreviewResolution, PreviewLength, PreviewImageBorders) also make no sense because
     we are not including a Pentax specific preview image. */
  "Exif.Pentax.Preview",
  "Exif.PentaxDng.Preview",
  /* Never save the complete brand specific MakerNote data. We load and
   * should only save the specific brand tags inside the MakerNote.
   * Sometimes the MakerNote is invalid or exiv2 doesn't know how to parse
   * it. In that case we still get the (invalid) MakerNote, but not the
   * individual tags or just a subset of them.
   * If there are recognized brand specific tags, exiv2 will create the
   * required MakerNote itself (which in can still be invalid but that's an
   * exiv2 issue not ours). */
  "Exif.Photo.MakerNote",
  "Exif.MakerNote.ByteOrder",
  "Exif.MakerNote.Offset",
  /* Photoshop resources can contain sensitive data. We should not save the
   * unedited original state. */
  "Exif.Image.ImageResources",
  "Exif.Image.0x935c",
  /* Issue #12518 Metadata fails to be exported when certain Sony Exif tags
   * are present. */
  "Exif.SonyMisc3c",
};

static const guint8 minimal_exif[] =
{
  0xff, 0xd8, 0xff, 0xe0, 0x00, 0x10, 0x4a, 0x46, 0x49, 0x46, 0x00, 0x01,
  0x01, 0x01, 0x00, 0x5a, 0x00, 0x5a, 0x00, 0x00, 0xff, 0xe1
};

static const guint8 wilber_jpg[] =
{
  0xff, 0xd8, 0xff, 0xe0, 0x00, 0x10, 0x4a, 0x46, 0x49, 0x46, 0x00, 0x01,
  0x01, 0x01, 0x00, 0x5a, 0x00, 0x5a, 0x00, 0x00, 0xff, 0xdb, 0x00, 0x43,
  0x00, 0x50, 0x37, 0x3c, 0x46, 0x3c, 0x32, 0x50, 0x46, 0x41, 0x46, 0x5a,
  0x55, 0x50, 0x5f, 0x78, 0xc8, 0x82, 0x78, 0x6e, 0x6e, 0x78, 0xf5, 0xaf,
  0xb9, 0x91, 0xc8, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff,
  0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff,
  0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff,
  0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xdb, 0x00, 0x43, 0x01, 0x55, 0x5a,
  0x5a, 0x78, 0x69, 0x78, 0xeb, 0x82, 0x82, 0xeb, 0xff, 0xff, 0xff, 0xff,
  0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff,
  0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff,
  0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff,
  0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff,
  0xff, 0xff, 0xff, 0xc0, 0x00, 0x11, 0x08, 0x00, 0x10, 0x00, 0x10, 0x03,
  0x01, 0x22, 0x00, 0x02, 0x11, 0x01, 0x03, 0x11, 0x01, 0xff, 0xc4, 0x00,
  0x16, 0x00, 0x01, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x03, 0x01, 0x02, 0xff, 0xc4, 0x00,
  0x1e, 0x10, 0x00, 0x01, 0x05, 0x00, 0x02, 0x03, 0x00, 0x00, 0x00, 0x00,
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0x00, 0x02, 0x03, 0x11, 0x31,
  0x04, 0x12, 0x51, 0x61, 0x71, 0xff, 0xc4, 0x00, 0x14, 0x01, 0x01, 0x00,
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
  0x00, 0x00, 0x00, 0xff, 0xc4, 0x00, 0x14, 0x11, 0x01, 0x00, 0x00, 0x00,
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
  0x00, 0xff, 0xda, 0x00, 0x0c, 0x03, 0x01, 0x00, 0x02, 0x11, 0x03, 0x11,
  0x00, 0x3f, 0x00, 0x18, 0xa0, 0x0e, 0x6d, 0xbc, 0xf5, 0xca, 0xf7, 0x78,
  0xb6, 0xfe, 0x3b, 0x23, 0xb2, 0x1d, 0x64, 0x68, 0xf0, 0x8a, 0x39, 0x4b,
  0x74, 0x9c, 0xa5, 0x5f, 0x35, 0x8a, 0xb2, 0x7e, 0xa0, 0xff, 0xd9, 0x00
};

static const guint wilber_jpg_len = G_N_ELEMENTS (wilber_jpg);

G_DEFINE_TYPE (GimpMetadata, gimp_metadata, GEXIV2_TYPE_METADATA)


static void
gimp_metadata_class_init (GimpMetadataClass *klass)
{
  GError *error = NULL;

  if (! gexiv2_metadata_try_register_xmp_namespace ("http://ns.adobe.com/DICOM/",
                                                    "DICOM", &error))
    {
      g_printerr ("Failed to register XMP namespace 'DICOM': %s\n", error->message);
      g_clear_error (&error);
    }

  if (! gexiv2_metadata_try_register_xmp_namespace ("http://darktable.sf.net/",
                                                    "darktable", &error))
    {
      g_printerr ("Failed to register XMP namespace 'darktable': %s\n", error->message);
      g_clear_error (&error);
    }

  /* Usage example Xmp.AmmoOS Image.tagname */
  if (! gexiv2_metadata_try_register_xmp_namespace ("http://www.ammoos.org/xmp/",
                                                    "AmmoOS Image", &error))
    {
      g_printerr ("Failed to register XMP namespace 'AmmoOS Image': %s\n", error->message);
      g_clear_error (&error);
    }
}

static void
gimp_metadata_init (GimpMetadata *metadata)
{
}

/**
 * gimp_metadata_get_guid:
 *
 * Generate Version 4 UUID/GUID.
 *
 * Returns: The new GUID/UUID string.
 *
 * Since: 2.10
 */
gchar *
gimp_metadata_get_guid (void)
{
  GRand       *rand;
  gint         bake;
  gchar       *GUID;
  const gchar *szHex = "0123456789abcdef-";

  rand = g_rand_new ();

#define DALLOC 36

  GUID = g_malloc0 (DALLOC + 1);

  for (bake = 0; bake < DALLOC; bake++)
    {
      gint  r = g_rand_int (rand) % 16;
      gchar c = ' ';

      switch (bake)
        {
        default:
          c = szHex [r];
          break;

        case 19 :
          c = szHex [(r & 0x03) | 0x08];
          break;

        case 8:
        case 13:
        case 18:
        case 23:
          c = '-';
          break;

        case 14:
          c = '4';
          break;
        }

      GUID[bake] = (bake < DALLOC) ? c : 0x00;
    }

  g_rand_free (rand);

  return GUID;
}

/**
 * gimp_metadata_add_history:
 *
 * Add XMP mm History data to file metadata.
 *
 * Since: 2.10
 */
void
gimp_metadata_add_xmp_history (GimpMetadata *metadata,
                               gchar        *state_status)
{
  GDateTime *now_tm;
  gchar     *tmp;
  char       timestr[256];
  char       tzstr[7];
  gchar      strdata[1024];
  gchar      tagstr[1024];
  gchar     *uuid;
  gchar     *str;
  gchar     *did;
  gchar     *odid;
  GError    *error = NULL;
  gint       id_count;
  gint       found;
  gint       lastfound;
  gint       count;
  int        ii;

  static const gchar *tags[] =
  {
    "Xmp.xmpMM.InstanceID",
    "Xmp.xmpMM.DocumentID",
    "Xmp.xmpMM.OriginalDocumentID",
    "Xmp.xmpMM.History"
  };

  static const gchar *history_tags[] =
  {
    "/stEvt:action",
    "/stEvt:instanceID",
    "/stEvt:when",
    "/stEvt:softwareAgent",
    "/stEvt:changed"
  };

  g_return_if_fail (GIMP_IS_METADATA (metadata));

  /* Update new Instance ID */
  uuid = gimp_metadata_get_guid ();

  str = g_strconcat ("xmp.iid:", uuid, NULL);

  gexiv2_metadata_try_set_tag_string (GEXIV2_METADATA (metadata),
                                      tags[0], str, NULL);
  g_free (uuid);
  g_free (str);

  /* Update new Document ID if none found */
  did = gexiv2_metadata_try_get_tag_interpreted_string (GEXIV2_METADATA (metadata),
                                                        tags[1], NULL);
  if (! did || ! strlen (did))
    {
      gchar *did_data;
      gchar *uuid = gimp_metadata_get_guid ();

      did_data = g_strconcat ("ammoos:docid:ammoos:", uuid, NULL);

      gexiv2_metadata_try_set_tag_string (GEXIV2_METADATA (metadata),
                                          tags[1], did_data, NULL);
      g_free (uuid);
      g_free (did_data);
    }

  /* Update new Original Document ID if none found */
  odid = gexiv2_metadata_try_get_tag_interpreted_string (GEXIV2_METADATA (metadata),
                                                         tags[2], NULL);
  if (! odid || ! strlen (odid))
    {
      gchar *did_data;
      gchar *uuid = gimp_metadata_get_guid ();

      did_data = g_strconcat ("xmp.did:", uuid, NULL);

      gexiv2_metadata_try_set_tag_string (GEXIV2_METADATA (metadata),
                                          tags[2], did_data, NULL);
      g_free (uuid);
      g_free (did_data);
    }

  /* Handle Xmp.xmpMM.History */

  gexiv2_metadata_try_set_xmp_tag_struct (GEXIV2_METADATA (metadata),
                                          tags[3],
                                          GEXIV2_STRUCTURE_XA_SEQ,
                                          NULL);

  /* Find current number of entries for Xmp.xmpMM.History */
  found = 0;
  for (count = 1; count < 65536; count++)
    {
      lastfound = 0;
      for (ii = 0; ii < 5; ii++)
        {
          g_snprintf (tagstr, sizeof (tagstr), "%s[%d]%s",
                      tags[3], count, history_tags[ii]);

          if (gexiv2_metadata_try_has_tag (GEXIV2_METADATA (metadata),
                                           tagstr, NULL))
            {
              lastfound = 1;
            }
        }

      if (lastfound == 0)
        break;

      found++;
    }

  id_count = found + 1;

  memset (tagstr, 0, sizeof (tagstr));

  g_snprintf (tagstr, sizeof (tagstr), "%s[%d]%s",
              tags[3], id_count, history_tags[0]);

  gexiv2_metadata_try_set_tag_string (GEXIV2_METADATA (metadata),
                                      tagstr, "saved", &error);
  if (error)
    {
      g_printerr ("%s: failed to set metadata '%s': %s\n",
                  G_STRFUNC, tagstr, error->message);
      g_clear_error (&error);
    }

  memset (tagstr, 0, sizeof (tagstr));
  memset (strdata, 0, sizeof (strdata));

  uuid = gimp_metadata_get_guid ();

  g_snprintf (tagstr, sizeof (tagstr), "%s[%d]%s",
              tags[3], id_count, history_tags[1]);
  g_snprintf (strdata, sizeof (strdata), "xmp.iid:%s",
              uuid);

  gexiv2_metadata_try_set_tag_string (GEXIV2_METADATA (metadata),
                                      tagstr, strdata, &error);
  if (error)
    {
      g_printerr ("%s: failed to set metadata '%s': %s\n",
                  G_STRFUNC, tagstr, error->message);
      g_clear_error (&error);
    }
  g_free(uuid);

  memset (tagstr, 0, sizeof (tagstr));

  g_snprintf (tagstr, sizeof (tagstr), "%s[%d]%s",
              tags[3], id_count, history_tags[2]);

  /* get local time */
  now_tm = g_date_time_new_now_local ();

  /* get timezone and fix format */
  tmp = g_date_time_format (now_tm, "%:::z");
  g_strlcpy (tzstr, tmp, 7);
  g_free (tmp);

  /* get current time and timezone string */
  tmp = g_date_time_format (now_tm, "%Y-%m-%dT%H:%M:%S");
  g_strlcpy (timestr, tmp, 256);
  g_free (tmp);
  tmp = g_strdup_printf ("%s%s", timestr, tzstr);
  gexiv2_metadata_try_set_tag_string (GEXIV2_METADATA (metadata),
                                      tagstr, tmp, &error);
  if (error)
    {
      g_printerr ("%s: failed to set metadata '%s': %s\n",
                  G_STRFUNC, tagstr, error->message);
      g_clear_error (&error);
    }
  g_free (tmp);
  g_date_time_unref (now_tm);

  memset (tagstr, 0, sizeof (tagstr));

  g_snprintf (tagstr, sizeof (tagstr), "%s[%d]%s",
              tags[3], id_count, history_tags[3]);

  gexiv2_metadata_try_set_tag_string (GEXIV2_METADATA (metadata),
                                      tagstr,
                                      PACKAGE_STRING " "
#if defined(_WIN32) || defined(__CYGWIN__) || defined(__MINGW32__)
                                      "(Windows)",
#elif defined(__linux__)
                                      "(Linux)",
#elif defined(__APPLE__) && defined(__MACH__)
                                      "(Mac OS)",
#elif defined(unix) || defined(__unix__) || defined(__unix)
                                      "(Unix)",
#else
                                      "(Unknown)",
#endif
                                      &error);
  if (error)
    {
      g_printerr ("%s: failed to set metadata '%s': %s\n",
                  G_STRFUNC, tagstr, error->message);
      g_clear_error (&error);
    }

  memset (tagstr, 0, sizeof (tagstr));

  g_snprintf (tagstr, sizeof (tagstr), "%s[%d]%s",
              tags[3], id_count, history_tags[4]);

  str = g_strconcat ("/", state_status, NULL);

  gexiv2_metadata_try_set_tag_string (GEXIV2_METADATA (metadata),
                                      tagstr, str, &error);
  g_free (str);
  if (error)
    {
      g_printerr ("%s: failed to set metadata '%s': %s\n",
                  G_STRFUNC, tagstr, error->message);
      g_clear_error (&error);
    }
}

/**
 * gimp_metadata_new:
 *
 * Creates a new #GimpMetadata instance.
 *
 * Returns: (transfer full): The new #GimpMetadata.
 *
 * Since: 2.10
 */
GimpMetadata *
gimp_metadata_new (void)
{
  GimpMetadata *metadata = NULL;

  if (gexiv2_initialize ())
    {
      metadata = g_object_new (GIMP_TYPE_METADATA, NULL);

      if (! gexiv2_metadata_open_buf (GEXIV2_METADATA (metadata),
                                      wilber_jpg, wilber_jpg_len,
                                      NULL))
        {
          g_object_unref (metadata);

          return NULL;
        }
    }

  return metadata;
}

/**
 * gimp_metadata_duplicate:
 * @metadata: The object to duplicate, or %NULL.
 *
 * Duplicates a #GimpMetadata instance.
 *
 * Returns: (transfer full):
 *               The new #GimpMetadata, or %NULL if @metadata is %NULL.
 *
 * Since: 2.10
 */
GimpMetadata *
gimp_metadata_duplicate (GimpMetadata *metadata)
{
  GimpMetadata *new_metadata = NULL;

  g_return_val_if_fail (metadata == NULL || GIMP_IS_METADATA (metadata), NULL);

  if (metadata)
    {
      gchar *xml;

      xml = gimp_metadata_serialize (metadata);
      new_metadata = gimp_metadata_deserialize (xml);
      g_free (xml);
    }

  return new_metadata;
}

typedef struct
{
  gchar         name[1024];
  gchar         prefix[256];
  gboolean      base64;
  gboolean      excessive_message_shown;
  GimpMetadata *metadata;
} GimpMetadataParseData;

static const gchar*
gimp_metadata_attribute_name_to_value (const gchar **attribute_names,
                                       const gchar **attribute_values,
                                       const gchar  *name)
{
  while (*attribute_names)
    {
      if (! strcmp (*attribute_names, name))
        {
          return *attribute_values;
        }

      attribute_names++;
      attribute_values++;
    }

  return NULL;
}

static void
gimp_metadata_deserialize_start_element (GMarkupParseContext *context,
                                         const gchar         *element_name,
                                         const gchar        **attribute_names,
                                         const gchar        **attribute_values,
                                         gpointer             user_data,
                                         GError             **error)
{
  GimpMetadataParseData *parse_data = user_data;

  if (! strcmp (element_name, "tag"))
    {
      const gchar *name;
      const gchar *encoding;

      name = gimp_metadata_attribute_name_to_value (attribute_names,
                                                    attribute_values,
                                                    "name");
      encoding = gimp_metadata_attribute_name_to_value (attribute_names,
                                                        attribute_values,
                                                        "encoding");

      if (! name)
        {
          g_set_error (error, GIMP_METADATA_ERROR, 1001,
                       "Element 'tag' does not contain required attribute 'name'.");
          return;
        }

      g_strlcpy (parse_data->name, name, sizeof (parse_data->name));

      parse_data->base64 = (encoding && ! strcmp (encoding, "base64"));
    }
  else if (! strcmp (element_name, "namespace"))
    {
      const gchar *url;
      const gchar *prefix;

      prefix = gimp_metadata_attribute_name_to_value (attribute_names,
                                                      attribute_values,
                                                      "prefix");
      url = gimp_metadata_attribute_name_to_value (attribute_names,
                                                   attribute_values,
                                                   "url");
      if (! prefix)
        {
          g_set_error (error, GIMP_METADATA_ERROR, 1002,
                       "Element 'namespace' does not contain required attribute 'prefix'.");
          return;
        }
      if (! url)
        {
          g_set_error (error, GIMP_METADATA_ERROR, 1003,
                       "Element 'namespace' does not contain required attribute 'url'.");
          return;
        }

      g_strlcpy (parse_data->prefix, prefix, sizeof (parse_data->prefix));
      g_strlcpy (parse_data->name, url, sizeof (parse_data->name));
    }
}

static void
gimp_metadata_deserialize_end_element (GMarkupParseContext *context,
                                       const gchar         *element_name,
                                       gpointer             user_data,
                                       GError             **error)
{
}

static void
gimp_metadata_deserialize_text (GMarkupParseContext  *context,
                                const gchar          *text,
                                gsize                 text_len,
                                gpointer              user_data,
                                GError              **error)
{
  GimpMetadataParseData *parse_data = user_data;
  const gchar           *current_element;

  current_element = g_markup_parse_context_get_element (context);

  if (! g_strcmp0 (current_element, "tag"))
    {
      gchar *value = g_strndup (text, text_len);

      if (parse_data->base64)
        {
          guchar *decoded;
          gsize   len;

          decoded = g_base64_decode (value, &len);

          if (decoded[len - 1] == '\0')
            {
              g_free (value);
              value = (gchar *) decoded;
            }
          else
            {
              g_clear_pointer (&value,   g_free);
              g_clear_pointer (&decoded, g_free);
            }
        }

      if (value)
        {
          GExiv2Metadata  *g2_metadata = GEXIV2_METADATA (parse_data->metadata);
          GError          *error       = NULL;
          gchar          **values;

          values = gexiv2_metadata_try_get_tag_multiple (g2_metadata,
                                                         parse_data->name,
                                                         &error);

          if (error)
            {
              g_printerr ("%s: %s\n", G_STRFUNC, error->message);
              g_clear_error (&error);
              g_strfreev (values);
            }
          else if (values)
            {
              guint length = g_strv_length (values);

              if (length > 1000 &&
                  ! g_strcmp0 (parse_data->name, "Xmp.photoshop.DocumentAncestors"))
                {
                  /* Issue #8025, see also #7464 Some XCF images can have huge
                   * amounts of this tag, apparently due to a bug in PhotoShop.
                   * This makes deserializing it in the way we currently do
                   * too slow. Until we can change this let's ignore everything
                   * but the first 1000 values when serializing. */

                  if (! parse_data->excessive_message_shown)
                    {
                      g_message ("Excessive number of Xmp.photoshop.DocumentAncestors tags found. "
                                 "Only keeping the first 1000 values.");
                      parse_data->excessive_message_shown = TRUE;
                    }
                }
              else
                {
                  values = g_renew (gchar *, values, length + 2);
                  values[length]     = g_strdup (value);
                  values[length + 1] = NULL;

                  gexiv2_metadata_try_set_tag_multiple (g2_metadata,
                                                        parse_data->name,
                                                        (const gchar **) values,
                                                        &error);
                  if (error)
                    {
                      g_warning ("%s: failed to set multiple metadata '%s': %s\n",
                                 G_STRFUNC, parse_data->name, error->message);
                      g_clear_error (&error);
                    }
                }
              g_strfreev (values);
            }
          else
            {
              gexiv2_metadata_try_set_tag_string (GEXIV2_METADATA (g2_metadata),
                                                  parse_data->name,
                                                  value, &error);
              if (error)
                {
                  g_warning ("%s: failed to set metadata '%s': %s\n",
                             G_STRFUNC, parse_data->name, error->message);
                  g_clear_error (&error);
                }
            }
          g_free (value);
        }
    }
  else if (! g_strcmp0 (current_element, "namespace"))
    {
      GError *error = NULL;

      gexiv2_metadata_try_register_xmp_namespace (parse_data->name,
                                                  parse_data->prefix,
                                                  &error);
      if (error) {
          g_warning ("%s: failed to register namespace %s (url: '%s'): %s\n",
                     G_STRFUNC, parse_data->prefix, parse_data->name,
                     error->message);
          g_clear_error(&error);
      }
    }
}

static  void
gimp_metadata_deserialize_error (GMarkupParseContext *context,
                                 GError              *error,
                                 gpointer             user_data)
{
  g_printerr ("Metadata parse error: %s\n", error->message);
}

/**
 * gimp_metadata_deserialize:
 * @metadata_xml: A string of serialized metadata XML.
 *
 * Deserializes a string of XML that has been created by
 * gimp_metadata_serialize().
 *
 * Returns: (transfer full): The new #GimpMetadata.
 *
 * Since: 2.10
 */
GimpMetadata *
gimp_metadata_deserialize (const gchar *metadata_xml)
{
  GimpMetadata          *metadata;
  GMarkupParser          markup_parser;
  GimpMetadataParseData  parse_data;
  GMarkupParseContext   *context;

  g_return_val_if_fail (metadata_xml != NULL, NULL);

  metadata = gimp_metadata_new ();

  parse_data.metadata = metadata;
  parse_data.excessive_message_shown = FALSE;

  markup_parser.start_element = gimp_metadata_deserialize_start_element;
  markup_parser.end_element   = gimp_metadata_deserialize_end_element;
  markup_parser.text          = gimp_metadata_deserialize_text;
  markup_parser.passthrough   = NULL;
  markup_parser.error         = gimp_metadata_deserialize_error;

  context = g_markup_parse_context_new (&markup_parser, 0, &parse_data, NULL);

  g_markup_parse_context_parse (context,
                                metadata_xml, strlen (metadata_xml),
                                NULL);

  g_markup_parse_context_unref (context);

  return metadata;
}

static gchar *
gimp_metadata_escape (const gchar *name,
                      const gchar *value,
                      gboolean    *base64)
{
  if (! g_utf8_validate (value, -1, NULL))
    {
      gchar *encoded;

      encoded = g_base64_encode ((const guchar *) value, strlen (value) + 1);

      g_printerr ("Invalid UTF-8 in metadata value %s, encoding as base64: %s\n",
                  name, encoded);

      *base64 = TRUE;

      return encoded;
    }

  *base64 = FALSE;

  return g_markup_escape_text (value, -1);
}

static void
gimp_metadata_append_tag (GString     *string,
                          const gchar *name,
                          gchar       *value,
                          gboolean     base64)
{
  if (value)
    {
      if (base64)
        {
          g_string_append_printf (string, "  <tag name=\"%s\" encoding=\"base64\">%s</tag>\n",
                                  name, value);
        }
      else
        {
          g_string_append_printf (string, "  <tag name=\"%s\">%s</tag>\n",
                                  name, value);
        }

      g_free (value);
    }
}

static void
gimp_metadata_add_namespace (GHashTable  *namespaces,
                             GString     *xml,
                             gchar       *prefix)
{
  if (! g_hash_table_lookup (namespaces, prefix))
    {
      gchar  *namespace_url;
      GError *error = NULL;

      namespace_url = gexiv2_metadata_try_get_xmp_namespace_for_tag (prefix, &error);

      if (! namespace_url)
        {
          /* Weird, we didn't find the namespace url.
             Let's add a dummy url, that way we can keep the tags. */
          if (error)
            {
              g_warning ("XMP namespace url not found! %s", error->message);
              g_clear_error (&error);
            }

          /* Fix the one namespace url we know of, and add a generic fix for
             any others. */
          if (g_strcmp0 (prefix, "Item") == 0)
            /* FIXME Remove this specific check for Item after this is fixed
               in our dependencies (exiv2?), see issue #10557. */
            namespace_url = g_strdup ("http://ns.google.com/photos/1.0/container/item/");
          else
            namespace_url = g_strdup_printf ("http://missing-url.org/%s/", prefix);

          if (! gexiv2_metadata_try_register_xmp_namespace (namespace_url,
                                                            prefix, &error))
            {
              g_warning ("Registering XMP namespace failed! %s\n", error->message);
              g_clear_error (&error);
            }
        }

      if (namespace_url)
        {
          g_debug ("Adding namespace %s, url: %s", prefix, namespace_url);

          if (! g_hash_table_insert (namespaces, prefix, namespace_url))
            g_warning ("Namespace already present: %s!", prefix);

          g_string_append_printf (xml,
                                  "  <namespace prefix=\"%s\" url=\"%s\"></namespace>\n",
                                  prefix, namespace_url);

          /* namespace_url and prefix are added to hashtable, so we don't free here */
        }
      else
        {
          g_free (prefix);
        }
    }
  else
    {
      g_free (prefix);
    }
}

/* Register a namespace in our xml metadata for each XMP namespace.
 * We use the following XML format:
 * <namespace prefix="namespace-prefix" url="namespace-url"></namespace>
 *
 * There are two types of namespace prefixes:
 * - Xmp.prefix.whatever, and
 * - /prefix:something, which is prefixed by the above
 *
 * We use a hashtable to keep track of which namespaces we have already
 * seen in the current run.
 */

static void
gimp_metadata_add_xmp_namespaces (GHashTable  *namespaces,
                                  GString     *xml,
                                  const gchar *tag)
{
  gchar  *tag_ptr = (gchar *) tag;
  gchar  *prefix;
  gchar **substrings;

  /* Find word between the first and second '.' */
  substrings = g_strsplit ((gchar *) tag_ptr, ".", 3);
  if (substrings && substrings[1])
    {
      prefix = g_strdup (substrings[1]);

      gimp_metadata_add_namespace (namespaces, xml, prefix);
    }
  g_strfreev (substrings);

  /* Multiple namespaces in the form /prefix:value are possible in one tag. */
  while (tag_ptr)
    {
      gchar *tag_next = NULL;

      tag_ptr = strstr (tag_ptr, "/");
      if (! tag_ptr || strlen (tag_ptr) <= 1)
        break;
      tag_ptr++;
      tag_next = strstr (tag_ptr, ":");

      if (tag_next)
        {
          gsize prefix_len = (gsize) tag_next - (gsize) tag_ptr + 1;

          prefix = g_new (gchar, prefix_len);
          g_strlcpy (prefix, tag_ptr, prefix_len);

          gimp_metadata_add_namespace (namespaces, xml, prefix);

          tag_ptr = tag_next;
        }
    }
}

/**
 * gimp_metadata_serialize:
 * @metadata: A #GimpMetadata instance.
 *
 * Serializes @metadata into an XML string that can later be deserialized
 * using gimp_metadata_deserialize().
 *
 * Returns: The serialized XML string.
 *
 * Since: 2.10
 */
gchar *
gimp_metadata_serialize (GimpMetadata *metadata)
{
  GString  *string;
  gchar   **exif_data = NULL;
  gchar   **iptc_data = NULL;
  gchar   **xmp_data  = NULL;
  gchar    *value;
  gchar    *escaped;
  GError   *error     = NULL;
  gboolean  base64;
  gint      i;

  g_return_val_if_fail (GIMP_IS_METADATA (metadata), NULL);

  string = g_string_new (NULL);

  g_string_append (string, "<?xml version='1.0' encoding='UTF-8'?>\n");
  g_string_append (string, "<metadata>\n");

  exif_data = gexiv2_metadata_get_exif_tags (GEXIV2_METADATA (metadata));

  if (exif_data)
    {
      for (i = 0; exif_data[i] != NULL; i++)
        {
          value = gexiv2_metadata_try_get_tag_string (GEXIV2_METADATA (metadata),
                                                      exif_data[i], &error);
          if (value)
            {
              escaped = gimp_metadata_escape (exif_data[i], value, &base64);
              g_free (value);

              gimp_metadata_append_tag (string, exif_data[i], escaped, base64);
            }
          else if (error)
            {
              g_printerr ("%s: failed to get Exif metadata '%s': %s\n",
                          G_STRFUNC, exif_data[i], error->message);
              g_clear_error (&error);
            }
        }

      g_strfreev (exif_data);
    }

  xmp_data = gexiv2_metadata_get_xmp_tags (GEXIV2_METADATA (metadata));

  if (xmp_data)
    {
      GHashTable *namespaces = g_hash_table_new_full (g_str_hash, g_str_equal, g_free, g_free);

      for (i = 0; xmp_data[i] != NULL; i++)
        {
          gimp_metadata_add_xmp_namespaces (namespaces, string, xmp_data[i]);

          /* XmpText is always a single value, but structures like
           * XmpBag and XmpSeq can have multiple values that need to be
           * treated separately or else saving will do things wrong. */
          if (! g_strcmp0 (gexiv2_metadata_try_get_tag_type (xmp_data[i], NULL), "XmpText"))
            {
              value = gexiv2_metadata_try_get_tag_string (GEXIV2_METADATA (metadata),
                                                          xmp_data[i], &error);
              if (value)
                {
                  escaped = gimp_metadata_escape (xmp_data[i], value, &base64);
                  g_free (value);

                  gimp_metadata_append_tag (string, xmp_data[i], escaped, base64);
                }
              else if (error)
                {
                  g_printerr ("%s: failed to get XMP metadata '%s': %s\n",
                              G_STRFUNC, xmp_data[i], error->message);
                  g_clear_error (&error);
                }
            }
          else
            {
              gchar **values;

              values = gexiv2_metadata_try_get_tag_multiple (GEXIV2_METADATA (metadata),
                                                             xmp_data[i], &error);

              if (values)
                {
                  gint  vi;
                  gint  cnt = 0;

                  if (! g_strcmp0 (xmp_data[i], "Xmp.photoshop.DocumentAncestors"))
                    {
                      /* Issue #7464 Some images can have huge amounts of this
                       * tag (more than 100000 in certain cases), apparently
                       * due to a bug in PhotoShop. This makes deserializing it
                       * in the way we currently do too slow. Until we can
                       * change this let's remove everything but the first 1000
                       * values when serializing. */
                      cnt = g_strv_length (values);

                      if (cnt > 1000)
                        {
                          g_message ("Excessive number of Xmp.photoshop.DocumentAncestors tags found: %d. "
                                     "Only keeping the first 1000 values.", cnt);
                        }
                    }

                  for (vi = 0; values[vi] != NULL && (cnt <= 1000 || vi < 1000); vi++)
                    {
                      escaped = gimp_metadata_escape (xmp_data[i], values[vi], &base64);
                      gimp_metadata_append_tag (string, xmp_data[i], escaped, base64);
                    }

                  g_strfreev (values);
                }
              else if (error)
                {
                  g_printerr ("%s: failed to get multiple XMP metadata '%s': %s\n",
                              G_STRFUNC, xmp_data[i], error->message);
                  g_clear_error (&error);
                }
            }
        }
      g_strfreev (xmp_data);
      g_hash_table_destroy (namespaces);
    }

  iptc_data = gexiv2_metadata_get_iptc_tags (GEXIV2_METADATA (metadata));

  if (iptc_data)
    {
      gchar **iptc_tags = iptc_data;
      gchar  *last_tag  = NULL;

      while (*iptc_tags)
        {
          gchar **values;

          if (last_tag && ! strcmp (*iptc_tags, last_tag))
            {
              iptc_tags++;
              continue;
            }
          last_tag = *iptc_tags;

          values = gexiv2_metadata_try_get_tag_multiple (GEXIV2_METADATA (metadata),
                                                         *iptc_tags, &error);

          if (values)
            {
              for (i = 0; values[i] != NULL; i++)
                {
                  escaped = gimp_metadata_escape (*iptc_tags, values[i], &base64);
                  gimp_metadata_append_tag (string, *iptc_tags, escaped, base64);
                }

              g_strfreev (values);
            }
          else if (error)
            {
              g_printerr ("%s: failed to get multiple IPTC metadata '%s': %s\n",
                          G_STRFUNC, *iptc_tags, error->message);
              g_clear_error (&error);
            }

          iptc_tags++;
        }

      g_strfreev (iptc_data);
    }

  g_string_append (string, "</metadata>\n");

  return g_string_free (string, FALSE);
}

/**
 * gimp_metadata_load_from_file:
 * @file:  The #GFile to load the metadata from
 * @error: Return location for error message
 *
 * Loads #GimpMetadata from @file.
 *
 * Returns: (transfer full): The loaded #GimpMetadata.
 *
 * Since: 2.10
 */
GimpMetadata  *
gimp_metadata_load_from_file (GFile   *file,
                              GError **error)
{
  GimpMetadata *meta = NULL;
  gchar        *path;
  gchar        *filename;

  g_return_val_if_fail (G_IS_FILE (file), NULL);
  g_return_val_if_fail (error == NULL || *error == NULL, NULL);

  path = g_file_get_path (file);

  if (! path)
    {
      g_set_error (error, GIMP_METADATA_ERROR, 0,
                   _("Can load metadata only from local files"));
      return NULL;
    }

  filename = g_strdup (path);

  g_free (path);

  if (gexiv2_initialize ())
    {
      meta = g_object_new (GIMP_TYPE_METADATA, NULL);

      if (! gexiv2_metadata_open_path (GEXIV2_METADATA (meta), filename, error))
        {
          g_object_unref (meta);
          g_free (filename);

          return NULL;
        }
    }

  g_free (filename);

  return meta;
}

/**
 * gimp_metadata_save_to_file:
 * @metadata: A #GimpMetadata instance.
 * @file:     The file to save the metadata to
 * @error:    Return location for error message
 *
 * Saves @metadata to @file.
 *
 * Returns: %TRUE on success, %FALSE otherwise.
 *
 * Since: 2.10
 */
gboolean
gimp_metadata_save_to_file (GimpMetadata  *metadata,
                            GFile         *file,
                            GError       **error)
{
  gchar    *path;
  gchar    *filename;
  gboolean  success;

  g_return_val_if_fail (GIMP_IS_METADATA (metadata), FALSE);
  g_return_val_if_fail (G_IS_FILE (file), FALSE);
  g_return_val_if_fail (error == NULL || *error == NULL, FALSE);

  path = g_file_get_path (file);

  if (! path)
    {
      g_set_error (error, GIMP_METADATA_ERROR, 0,
                   _("Can save metadata only to local files"));
      return FALSE;
    }

  filename = g_strdup (path);

  g_free (path);

  success = gexiv2_metadata_save_file (GEXIV2_METADATA (metadata),
                                       filename, error);

  g_free (filename);

  return success;
}

/**
 * gimp_metadata_set_from_exif:
 * @metadata:         A #GimpMetadata instance.
 * @exif_data: (array length=exif_data_length): The blob of Exif data to set
 * @exif_data_length: Length of @exif_data, in bytes
 * @error:            Return location for error message
 *
 * Sets the tags from a piece of Exif data on @metadata.
 *
 * Returns: %TRUE on success, %FALSE otherwise.
 *
 * Since: 2.10
 */
gboolean
gimp_metadata_set_from_exif (GimpMetadata  *metadata,
                             const guchar  *exif_data,
                             gint           exif_data_length,
                             GError       **error)
{

  GByteArray   *exif_bytes     = NULL;
  GimpMetadata *exif_metadata;
  const guchar  exif_marker[6] = "Exif\0\0";
  const guchar *data;
  gint          data_length;

  g_return_val_if_fail (GIMP_IS_METADATA (metadata), FALSE);
  g_return_val_if_fail (exif_data != NULL || exif_data_length == 0, FALSE);
  g_return_val_if_fail (error == NULL || *error == NULL, FALSE);

  if (exif_data_length < 0 || exif_data_length + 2 >= 65536)
    {
      g_set_error (error, GIMP_METADATA_ERROR, 0,
                   _("Invalid Exif data size."));
      return FALSE;
    }

  /* Old AmmoOS Image exif parasite marker "Exif\0\0" needs special handling. */
  if (exif_data_length >= 6 &&
      ! memcmp (exif_marker, exif_data, sizeof(exif_marker)))
    {
      guint8        data_size[2]  = { 0, };
      const guint8  eoi[2]        = { 0xff, 0xd9 };

      data_size[0] = ((exif_data_length + 2) & 0xFF00) >> 8;
      data_size[1] = ((exif_data_length + 2) & 0x00FF);

      exif_bytes = g_byte_array_new ();
      exif_bytes = g_byte_array_append (exif_bytes,
                                        minimal_exif, G_N_ELEMENTS (minimal_exif));
      exif_bytes = g_byte_array_append (exif_bytes,
                                        data_size, 2);
      exif_bytes = g_byte_array_append (exif_bytes,
                                        (guint8 *) exif_data, exif_data_length);
      exif_bytes = g_byte_array_append (exif_bytes, eoi, 2);
      data = exif_bytes->data;
      data_length = exif_bytes->len;
    }
  else
    {
      data = exif_data;
      data_length = exif_data_length;
    }

  exif_metadata = gimp_metadata_new ();

  if (! gexiv2_metadata_open_buf (GEXIV2_METADATA (exif_metadata),
                                  data, data_length, error))
    {
      g_object_unref (exif_metadata);
      if (exif_bytes)
        g_byte_array_free (exif_bytes, TRUE);
      return FALSE;
    }

  if (! gexiv2_metadata_has_exif (GEXIV2_METADATA (exif_metadata)))
    {
      g_set_error (error, GIMP_METADATA_ERROR, 0,
                   _("Parsing Exif data failed."));
      g_object_unref (exif_metadata);
      if (exif_bytes)
        g_byte_array_free (exif_bytes, TRUE);
      return FALSE;
    }

  gimp_metadata_add (exif_metadata, metadata);
  g_object_unref (exif_metadata);
  if (exif_bytes)
    g_byte_array_free (exif_bytes, TRUE);

  return TRUE;
}

/**
 * gimp_metadata_set_from_iptc:
 * @metadata:        A #GimpMetadata instance.
 * @iptc_data: (array length=iptc_data_length): The blob of Iptc data to set
 * @iptc_data_length:Length of @iptc_data, in bytes
 * @error:           Return location for error message
 *
 * Sets the tags from a piece of IPTC data on @metadata.
 *
 * Returns: %TRUE on success, %FALSE otherwise.
 *
 * Since: 2.10
 */
gboolean
gimp_metadata_set_from_iptc (GimpMetadata  *metadata,
                             const guchar  *iptc_data,
                             gint           iptc_data_length,
                             GError       **error)
{
  GimpMetadata *iptc_metadata;

  g_return_val_if_fail (GIMP_IS_METADATA (metadata), FALSE);
  g_return_val_if_fail (iptc_data != NULL || iptc_data_length == 0, FALSE);
  g_return_val_if_fail (error == NULL || *error == NULL, FALSE);

  iptc_metadata = gimp_metadata_new ();

  if (! gexiv2_metadata_open_buf (GEXIV2_METADATA (iptc_metadata),
                                  iptc_data, iptc_data_length, error))
    {
      g_object_unref (iptc_metadata);
      return FALSE;
    }

  if (! gexiv2_metadata_has_iptc (GEXIV2_METADATA (iptc_metadata)))
    {
      g_set_error (error, GIMP_METADATA_ERROR, 0,
                   _("Parsing IPTC data failed."));
      g_object_unref (iptc_metadata);
      return FALSE;
    }

  gimp_metadata_add (iptc_metadata, metadata);
  g_object_unref (iptc_metadata);

  return TRUE;
}

/**
 * gimp_metadata_set_from_xmp:
 * @metadata:        A #GimpMetadata instance.
 * @xmp_data: (array length=xmp_data_length): The blob of XMP data to set
 * @xmp_data_length: Length of @xmp_data, in bytes
 * @error:           Return location for error message
 *
 * Sets the tags from a piece of XMP data on @metadata.
 *
 * Returns: %TRUE on success, %FALSE otherwise.
 *
 * Since: 2.10
 */
gboolean
gimp_metadata_set_from_xmp (GimpMetadata  *metadata,
                            const guchar  *xmp_data,
                            gint           xmp_data_length,
                            GError       **error)
{
  GimpMetadata *xmp_metadata;

  g_return_val_if_fail (GIMP_IS_METADATA (metadata), FALSE);
  g_return_val_if_fail (xmp_data != NULL || xmp_data_length == 0, FALSE);
  g_return_val_if_fail (error == NULL || *error == NULL, FALSE);

  xmp_metadata = gimp_metadata_new ();

  if (! gexiv2_metadata_open_buf (GEXIV2_METADATA (xmp_metadata),
                                  xmp_data, xmp_data_length, error))
    {
      g_object_unref (xmp_metadata);
      return FALSE;
    }

  if (! gexiv2_metadata_has_xmp (GEXIV2_METADATA (xmp_metadata)))
    {
      g_set_error (error, GIMP_METADATA_ERROR, 0,
                   _("Parsing XMP data failed."));
      g_object_unref (xmp_metadata);
      return FALSE;
    }

  gimp_metadata_add (xmp_metadata, metadata);
  g_object_unref (xmp_metadata);

  return TRUE;
}

/**
 * gimp_metadata_set_pixel_size:
 * @metadata: A #GimpMetadata instance.
 * @width:    Width in pixels
 * @height:   Height in pixels
 *
 * Sets Exif.Image.ImageWidth and Exif.Image.ImageLength on @metadata.
 * If already present, also sets Exif.Photo.PixelXDimension and
 * Exif.Photo.PixelYDimension.
 *
 * Since: 2.10
 */
void
gimp_metadata_set_pixel_size (GimpMetadata *metadata,
                              gint          width,
                              gint          height)
{
  gchar buffer[32];

  g_return_if_fail (GIMP_IS_METADATA (metadata));

  g_snprintf (buffer, sizeof (buffer), "%d", width);
  gexiv2_metadata_try_set_tag_string (GEXIV2_METADATA (metadata),
                                      "Exif.Image.ImageWidth", buffer, NULL);
  if (gexiv2_metadata_try_has_tag (GEXIV2_METADATA (metadata),
                                   "Exif.Photo.PixelXDimension", NULL))
    {
      gexiv2_metadata_try_set_tag_string (GEXIV2_METADATA (metadata),
                                          "Exif.Photo.PixelXDimension",
                                          buffer, NULL);
    }

  g_snprintf (buffer, sizeof (buffer), "%d", height);
  gexiv2_metadata_try_set_tag_string (GEXIV2_METADATA (metadata),
                                      "Exif.Image.ImageLength", buffer, NULL);
  if (gexiv2_metadata_try_has_tag (GEXIV2_METADATA (metadata),
                                   "Exif.Photo.PixelYDimension", NULL))
    {
      gexiv2_metadata_try_set_tag_string (GEXIV2_METADATA (metadata),
                                          "Exif.Photo.PixelYDimension",
                                          buffer, NULL);
    }
}

/**
 * gimp_metadata_set_bits_per_sample:
 * @metadata:        A #GimpMetadata instance.
 * @bits_per_sample: Bits per pixel, per component
 *
 * Sets Exif.Image.BitsPerSample on @metadata.
 *
 * Since: 2.10
 */
void
gimp_metadata_set_bits_per_sample (GimpMetadata *metadata,
                                   gint          bits_per_sample)
{
  gchar buffer[32];

  g_return_if_fail (GIMP_IS_METADATA (metadata));

  g_snprintf (buffer, sizeof (buffer), "%d %d %d",
              bits_per_sample, bits_per_sample, bits_per_sample);
  gexiv2_metadata_try_set_tag_string (GEXIV2_METADATA (metadata),
                                      "Exif.Image.BitsPerSample", buffer, NULL);
}

/**
 * gimp_metadata_get_resolution:
 * @metadata: A #GimpMetadata instance.
 * @xres: (out) (optional): Return location for the X Resolution, in ppi
 * @yres: (out) (optional): Return location for the Y Resolution, in ppi
 * @unit: (out) (optional): Return location for the unit unit
 *
 * Returns values based on Exif.Image.XResolution,
 * Exif.Image.YResolution and Exif.Image.ResolutionUnit of @metadata.
 *
 * Returns: %TRUE on success, %FALSE otherwise.
 *
 * Since: 2.10
 */
gboolean
gimp_metadata_get_resolution (GimpMetadata  *metadata,
                              gdouble       *xres,
                              gdouble       *yres,
                              GimpUnit     **unit)
{
  gint xnom, xdenom;
  gint ynom, ydenom;

  g_return_val_if_fail (GIMP_IS_METADATA (metadata), FALSE);

  if (gexiv2_metadata_try_get_exif_tag_rational (GEXIV2_METADATA (metadata),
                                                 "Exif.Image.XResolution",
                                                 &xnom, &xdenom, NULL) &&
      gexiv2_metadata_try_get_exif_tag_rational (GEXIV2_METADATA (metadata),
                                                 "Exif.Image.YResolution",
                                                 &ynom, &ydenom, NULL))
    {
      gchar *un;
      gint   exif_unit = 2;

      un = gexiv2_metadata_try_get_tag_string (GEXIV2_METADATA (metadata),
                                               "Exif.Image.ResolutionUnit", NULL);
      if (un)
        {
          exif_unit = atoi (un);
          g_free (un);
        }

      if (xnom != 0 && xdenom != 0 &&
          ynom != 0 && ydenom != 0)
        {
          gdouble xresolution = (gdouble) xnom / (gdouble) xdenom;
          gdouble yresolution = (gdouble) ynom / (gdouble) ydenom;

          if (exif_unit == 3)
            {
              xresolution *= 2.54;
              yresolution *= 2.54;
            }

         if (xresolution >= GIMP_MIN_RESOLUTION &&
             xresolution <= GIMP_MAX_RESOLUTION &&
             yresolution >= GIMP_MIN_RESOLUTION &&
             yresolution <= GIMP_MAX_RESOLUTION)
           {
             if (xres)
               *xres = xresolution;

             if (yres)
               *yres = yresolution;

             if (unit)
               {
                 if (exif_unit == 3)
                   *unit = gimp_unit_mm ();
                 else
                   *unit = gimp_unit_inch ();
               }

             return TRUE;
           }
        }
    }

  return FALSE;
}

/**
 * gimp_metadata_set_resolution:
 * @metadata: A #GimpMetadata instance.
 * @xres:     The image's X Resolution, in ppi
 * @yres:     The image's Y Resolution, in ppi
 * @unit:     The image's unit
 *
 * Sets Exif.Image.XResolution, Exif.Image.YResolution and
 * Exif.Image.ResolutionUnit of @metadata.
 *
 * Since: 2.10
 */
void
gimp_metadata_set_resolution (GimpMetadata *metadata,
                              gdouble       xres,
                              gdouble       yres,
                              GimpUnit     *unit)
{
  gchar buffer[32];
  gint  exif_unit;
  gint  factor;

  g_return_if_fail (GIMP_IS_METADATA (metadata));

  if (gimp_unit_is_metric (unit))
    {
      xres /= 2.54;
      yres /= 2.54;

      exif_unit = 3;
    }
  else
    {
      exif_unit = 2;
    }

  for (factor = 1; factor <= 100 /* arbitrary */; factor++)
    {
      if (fabs (xres * factor - ROUND (xres * factor)) < 0.01 &&
          fabs (yres * factor - ROUND (yres * factor)) < 0.01)
        break;
    }

  gexiv2_metadata_try_set_exif_tag_rational (GEXIV2_METADATA (metadata),
                                             "Exif.Image.XResolution",
                                             ROUND (xres * factor), factor, NULL);

  gexiv2_metadata_try_set_exif_tag_rational (GEXIV2_METADATA (metadata),
                                             "Exif.Image.YResolution",
                                             ROUND (yres * factor), factor, NULL);

  g_snprintf (buffer, sizeof (buffer), "%d", exif_unit);
  gexiv2_metadata_try_set_tag_string (GEXIV2_METADATA (metadata),
                                      "Exif.Image.ResolutionUnit", buffer, NULL);
}

/**
 * gimp_metadata_set_creation_date:
 * @metadata: A #GimpMetadata instance.
 * @datetime: A #GDateTime value
 *
 * Sets `Iptc.Application2.DateCreated`, `Iptc.Application2.TimeCreated`,
 * `Exif.Image.DateTime`, `Exif.Image.DateTimeOriginal`,
 * `Exif.Photo.DateTimeOriginal`, `Exif.Photo.DateTimeDigitized`,
 * `Exif.Photo.OffsetTime`, `Exif.Photo.OffsetTimeOriginal`,
 * `Exif.Photo.OffsetTimeDigitized`, `Xmp.xmp.CreateDate`, `Xmp.xmp.ModifyDate`,
 * `Xmp.xmp.MetadataDate`, `Xmp.photoshop.DateCreated` of @metadata.
 *
 * Since: 3.0
 */
void
gimp_metadata_set_creation_date (GimpMetadata *metadata,
                                 GDateTime    *datetime)
{
  gchar          *datetime_buf = NULL;
  GExiv2Metadata *g2metadata   = GEXIV2_METADATA (metadata);

  g_return_if_fail (GIMP_IS_METADATA (metadata));

  /* IPTC: set creation date and time; there is no tag for modified date/time. */

  datetime_buf = g_date_time_format (datetime, "%Y-%m-%d");
  gexiv2_metadata_try_set_tag_string (g2metadata,
                                      "Iptc.Application2.DateCreated",
                                      datetime_buf, NULL);
  g_free (datetime_buf);

  /* time and timezone */
  datetime_buf = g_date_time_format (datetime, "%T\%:z");
  gexiv2_metadata_try_set_tag_string (g2metadata,
                                      "Iptc.Application2.TimeCreated",
                                      datetime_buf, NULL);
  g_free (datetime_buf);

  /* Exif: Exif.Image.DateTime = Modified datetime
   * Exif.Image.DateTimeOriginal and Exif.Photo.DateTimeOriginal = When the
   *   original image data was generated.
   * Exif.Photo.DateTimeDigitized = when the image was stored as digital data.
   */
  datetime_buf = g_date_time_format (datetime, "%Y:%m:%d %T");

  gexiv2_metadata_try_set_tag_string (g2metadata,
                                      "Exif.Image.DateTime",
                                      datetime_buf, NULL);
  gexiv2_metadata_try_set_tag_string (g2metadata,
                                      "Exif.Image.DateTimeOriginal",
                                      datetime_buf, NULL);
  gexiv2_metadata_try_set_tag_string (g2metadata,
                                      "Exif.Photo.DateTimeOriginal",
                                      datetime_buf, NULL);
  gexiv2_metadata_try_set_tag_string (g2metadata,
                                      "Exif.Photo.DateTimeDigitized",
                                      datetime_buf, NULL);
  g_free (datetime_buf);

  /* Timezone is separate */
  datetime_buf = g_date_time_format (datetime, "\%:z");
  gexiv2_metadata_try_set_tag_string (g2metadata,
                                      "Exif.Photo.OffsetTime",
                                      datetime_buf, NULL);
  gexiv2_metadata_try_set_tag_string (g2metadata,
                                      "Exif.Photo.OffsetTimeOriginal",
                                      datetime_buf, NULL);
  gexiv2_metadata_try_set_tag_string (g2metadata,
                                      "Exif.Photo.OffsetTimeDigitized",
                                      datetime_buf, NULL);
  g_free (datetime_buf);

  /* XMP: Xmp.photoshop.DateCreated = date when the original image was
   *   taken, this can be before Xmp.xmp.CreateDate. */
  datetime_buf = g_date_time_format (datetime, "%Y-%m-%dT%T\%:z");

  gexiv2_metadata_try_set_tag_string (g2metadata,
                                      "Xmp.xmp.CreateDate",
                                      datetime_buf, NULL);
  gexiv2_metadata_try_set_tag_string (g2metadata,
                                      "Xmp.xmp.ModifyDate",
                                      datetime_buf, NULL);
  gexiv2_metadata_try_set_tag_string (g2metadata,
                                      "Xmp.xmp.MetadataDate",
                                      datetime_buf, NULL);
  gexiv2_metadata_try_set_tag_string (g2metadata,
                                      "Xmp.photoshop.DateCreated",
                                      datetime_buf, NULL);

  g_free (datetime_buf);
}

/**
 * gimp_metadata_get_colorspace:
 * @metadata: A #GimpMetadata instance.
 *
 * Returns values based on Exif.Photo.ColorSpace, Xmp.exif.ColorSpace,
 * Exif.Iop.InteroperabilityIndex, Exif.Nikon3.ColorSpace,
 * Exif.Canon.ColorSpace of @metadata.
 *
 * Returns: The colorspace specified by above tags.
 *
 * Since: 2.10
 */
GimpMetadataColorspace
gimp_metadata_get_colorspace (GimpMetadata *metadata)
{
  glong exif_cs = -1;

  g_return_val_if_fail (GIMP_IS_METADATA (metadata),
                        GIMP_METADATA_COLORSPACE_UNSPECIFIED);

  /*  the logic here was mostly taken from darktable and libkexiv2  */

  if (gexiv2_metadata_try_has_tag (GEXIV2_METADATA (metadata),
                                   "Exif.Photo.ColorSpace", NULL))
    {
      exif_cs = gexiv2_metadata_try_get_tag_long (GEXIV2_METADATA (metadata),
                                                  "Exif.Photo.ColorSpace", NULL);
    }
  else if (gexiv2_metadata_try_has_tag (GEXIV2_METADATA (metadata),
                                        "Xmp.exif.ColorSpace", NULL))
    {
      exif_cs = gexiv2_metadata_try_get_tag_long (GEXIV2_METADATA (metadata),
                                                  "Xmp.exif.ColorSpace", NULL);
    }

  if (exif_cs == 0x01)
    {
      return GIMP_METADATA_COLORSPACE_SRGB;
    }
  else if (exif_cs == 0x02)
    {
      return GIMP_METADATA_COLORSPACE_ADOBERGB;
    }
  else
    {
      if (exif_cs == 0xffff)
        {
          gchar *iop_index;

          iop_index = gexiv2_metadata_try_get_tag_string (GEXIV2_METADATA (metadata),
                                                          "Exif.Iop.InteroperabilityIndex", NULL);

          if (! g_strcmp0 (iop_index, "R03"))
            {
              g_free (iop_index);

              return GIMP_METADATA_COLORSPACE_ADOBERGB;
            }
          else if (! g_strcmp0 (iop_index, "R98"))
            {
              g_free (iop_index);

              return GIMP_METADATA_COLORSPACE_SRGB;
            }

          g_free (iop_index);
        }

      if (gexiv2_metadata_try_has_tag (GEXIV2_METADATA (metadata),
                                       "Exif.Nikon3.ColorSpace", NULL))
        {
          glong nikon_cs;

          nikon_cs = gexiv2_metadata_try_get_tag_long (GEXIV2_METADATA (metadata),
                                                       "Exif.Nikon3.ColorSpace", NULL);

          if (nikon_cs == 0x01)
            {
              return GIMP_METADATA_COLORSPACE_SRGB;
            }
          else if (nikon_cs == 0x02)
            {
              return GIMP_METADATA_COLORSPACE_ADOBERGB;
            }
        }

      if (gexiv2_metadata_try_has_tag (GEXIV2_METADATA (metadata),
                                       "Exif.Canon.ColorSpace", NULL))
        {
          glong canon_cs;

          canon_cs = gexiv2_metadata_try_get_tag_long (GEXIV2_METADATA (metadata),
                                                       "Exif.Canon.ColorSpace", NULL);

          if (canon_cs == 0x01)
            {
              return GIMP_METADATA_COLORSPACE_SRGB;
            }
          else if (canon_cs == 0x02)
            {
              return GIMP_METADATA_COLORSPACE_ADOBERGB;
            }
        }

      if (exif_cs == 0xffff)
        return GIMP_METADATA_COLORSPACE_UNCALIBRATED;
    }

  return GIMP_METADATA_COLORSPACE_UNSPECIFIED;
}

/**
 * gimp_metadata_set_colorspace:
 * @metadata:   A #GimpMetadata instance.
 * @colorspace: The color space.
 *
 * Sets Exif.Photo.ColorSpace, Xmp.exif.ColorSpace,
 * Exif.Iop.InteroperabilityIndex, Exif.Nikon3.ColorSpace,
 * Exif.Canon.ColorSpace of @metadata.
 *
 * Since: 2.10
 */
void
gimp_metadata_set_colorspace (GimpMetadata           *metadata,
                              GimpMetadataColorspace  colorspace)
{
  GExiv2Metadata *g2metadata = GEXIV2_METADATA (metadata);

  switch (colorspace)
    {
    case GIMP_METADATA_COLORSPACE_UNSPECIFIED:
      gexiv2_metadata_try_clear_tag (g2metadata, "Exif.Photo.ColorSpace", NULL);
      gexiv2_metadata_try_clear_tag (g2metadata, "Xmp.exif.ColorSpace", NULL);
      gexiv2_metadata_try_clear_tag (g2metadata, "Exif.Iop.InteroperabilityIndex", NULL);
      gexiv2_metadata_try_clear_tag (g2metadata, "Exif.Nikon3.ColorSpace", NULL);
      gexiv2_metadata_try_clear_tag (g2metadata, "Exif.Canon.ColorSpace", NULL);
      break;

    case GIMP_METADATA_COLORSPACE_UNCALIBRATED:
      gexiv2_metadata_try_set_tag_long (g2metadata, "Exif.Photo.ColorSpace", 0xffff, NULL);
      if (gexiv2_metadata_try_has_tag (g2metadata, "Xmp.exif.ColorSpace", NULL))
        gexiv2_metadata_try_set_tag_long (g2metadata, "Xmp.exif.ColorSpace", 0xffff, NULL);
      gexiv2_metadata_try_clear_tag (g2metadata, "Exif.Iop.InteroperabilityIndex", NULL);
      gexiv2_metadata_try_clear_tag (g2metadata, "Exif.Nikon3.ColorSpace", NULL);
      gexiv2_metadata_try_clear_tag (g2metadata, "Exif.Canon.ColorSpace", NULL);
      break;

    case GIMP_METADATA_COLORSPACE_SRGB:
      gexiv2_metadata_try_set_tag_long (g2metadata, "Exif.Photo.ColorSpace", 0x01, NULL);

      if (gexiv2_metadata_try_has_tag (g2metadata, "Xmp.exif.ColorSpace", NULL))
        gexiv2_metadata_try_set_tag_long (g2metadata, "Xmp.exif.ColorSpace", 0x01, NULL);

      if (gexiv2_metadata_try_has_tag (g2metadata, "Exif.Iop.InteroperabilityIndex", NULL))
        gexiv2_metadata_try_set_tag_string (g2metadata,
                                            "Exif.Iop.InteroperabilityIndex",
                                            "R98", NULL);

      if (gexiv2_metadata_try_has_tag (g2metadata, "Exif.Nikon3.ColorSpace", NULL))
        gexiv2_metadata_try_set_tag_long (g2metadata, "Exif.Nikon3.ColorSpace", 0x01, NULL);

      if (gexiv2_metadata_try_has_tag (g2metadata, "Exif.Canon.ColorSpace", NULL))
        gexiv2_metadata_try_set_tag_long (g2metadata, "Exif.Canon.ColorSpace", 0x01, NULL);
      break;

    case GIMP_METADATA_COLORSPACE_ADOBERGB:
      gexiv2_metadata_try_set_tag_long (g2metadata, "Exif.Photo.ColorSpace", 0x02, NULL);

      if (gexiv2_metadata_try_has_tag (g2metadata, "Xmp.exif.ColorSpace", NULL))
        gexiv2_metadata_try_set_tag_long (g2metadata, "Xmp.exif.ColorSpace", 0x02, NULL);

      if (gexiv2_metadata_try_has_tag (g2metadata, "Exif.Iop.InteroperabilityIndex", NULL))
        gexiv2_metadata_try_set_tag_string (g2metadata,
                                            "Exif.Iop.InteroperabilityIndex",
                                            "R03", NULL);

      if (gexiv2_metadata_try_has_tag (g2metadata, "Exif.Nikon3.ColorSpace", NULL))
        gexiv2_metadata_try_set_tag_long (g2metadata, "Exif.Nikon3.ColorSpace", 0x02, NULL);

      if (gexiv2_metadata_try_has_tag (g2metadata, "Exif.Canon.ColorSpace", NULL))
        gexiv2_metadata_try_set_tag_long (g2metadata, "Exif.Canon.ColorSpace", 0x02, NULL);
      break;
    }
}

/**
 * gimp_metadata_is_tag_supported:
 * @tag:       A metadata tag name
 * @mime_type: A mime type
 *
 * Returns whether @tag is supported in a file of type @mime_type.
 *
 * Returns: %TRUE if the @tag supported with @mime_type, %FALSE otherwise.
 *
 * Since: 2.10
 */
gboolean
gimp_metadata_is_tag_supported (const gchar *tag,
                                const gchar *mime_type)
{
  gint j;

  g_return_val_if_fail (tag != NULL, FALSE);
  g_return_val_if_fail (mime_type != NULL, FALSE);

  for (j = 0; j < G_N_ELEMENTS (unsupported_tags); j++)
    {
      if (g_str_has_prefix (tag, unsupported_tags[j]))
        {
          return FALSE;
        }
    }

  if (! strcmp (mime_type, "image/jpeg"))
    {
      for (j = 0; j < G_N_ELEMENTS (tiff_tags); j++)
        {
          if (g_str_has_prefix (tag, tiff_tags[j]))
            {
              return FALSE;
            }
        }
    }
  else if (! strcmp (mime_type, "image/tiff"))
    {
      for (j = 0; j < G_N_ELEMENTS (jpeg_tags); j++)
        {
          if (g_str_has_prefix (tag, jpeg_tags[j]))
            {
              return FALSE;
            }
        }
    }

  return TRUE;
}


/* private functions */

static GQuark
gimp_metadata_error_quark (void)
{
  static GQuark quark = 0;

  if (G_UNLIKELY (quark == 0))
    quark = g_quark_from_static_string ("ammoos-metadata-error-quark");

  return quark;
}

static void
gimp_metadata_copy_tag (GExiv2Metadata *src,
                        GExiv2Metadata *dest,
                        const gchar    *tag)
{
  gchar  **values;
  GError  *error = NULL;

  values = gexiv2_metadata_try_get_tag_multiple (src, tag, &error);

  if (error)
    {
      g_printerr ("%s: %s\n", G_STRFUNC, error->message);
      g_clear_error (&error);
      g_strfreev (values);
    }
  else if (values)
    {
      gexiv2_metadata_try_set_tag_multiple (dest, tag, (const gchar **) values, &error);
      if (error)
        {
          g_warning ("%s: failed to set multiple metadata '%s': %s\n",
                     G_STRFUNC, tag, error->message);
          g_clear_error (&error);
        }

      g_strfreev (values);
    }
  else
    {
      gchar *value = gexiv2_metadata_try_get_tag_string (src, tag, &error);

      if (value)
        {
          gexiv2_metadata_try_set_tag_string (dest, tag, value, &error);
          if (error)
            {
              g_warning ("%s: failed to set metadata '%s': %s\n",
                         G_STRFUNC, tag, error->message);
              g_clear_error (&error);
            }
          g_free (value);
        }
      else if (error)
        {
          g_warning ("%s: failed to get metadata '%s': %s\n",
                     G_STRFUNC, tag, error->message);
          g_clear_error (&error);
        }
    }
}

static void
gimp_metadata_copy_tags (GExiv2Metadata  *src,
                         GExiv2Metadata  *dest,
                         const gchar    **tags)
{
  gint i;

  for (i = 0; tags[i] != NULL; i++)
    {
      /* don't copy the same tag multiple times */
      if (i > 0 && ! strcmp (tags[i], tags[i - 1]))
        continue;

      gimp_metadata_copy_tag (src, dest, tags[i]);
    }
 }

static void
gimp_metadata_add (GimpMetadata *src,
                   GimpMetadata *dest)
{
  GExiv2Metadata *g2src  = GEXIV2_METADATA (src);
  GExiv2Metadata *g2dest = GEXIV2_METADATA (dest);

  if (gexiv2_metadata_get_supports_exif (g2src) &&
      gexiv2_metadata_get_supports_exif (g2dest))
    {
      gchar **exif_tags = gexiv2_metadata_get_exif_tags (g2src);

      if (exif_tags)
        {
          gimp_metadata_copy_tags (g2src, g2dest,
                                   (const gchar **) exif_tags);
          g_strfreev (exif_tags);
        }
    }

  if (gexiv2_metadata_get_supports_xmp (g2src) &&
      gexiv2_metadata_get_supports_xmp (g2dest))
    {
      gchar **xmp_tags = gexiv2_metadata_get_xmp_tags (g2src);

      if (xmp_tags)
        {
          gimp_metadata_copy_tags (g2src, g2dest,
                                   (const gchar **) xmp_tags);
          g_strfreev (xmp_tags);
        }
    }

  if (gexiv2_metadata_get_supports_iptc (g2src) &&
      gexiv2_metadata_get_supports_iptc (g2dest))
    {
      gchar **iptc_tags = gexiv2_metadata_get_iptc_tags (g2src);

      if (iptc_tags)
        {
          gimp_metadata_copy_tags (g2src, g2dest,
                                   (const gchar **) iptc_tags);
          g_strfreev (iptc_tags);
        }
    }
}

/* --- end libammoos/base/fieldbase/gimpmetadata.c --- */

/* --- begin libammoos/base/fieldbase/gimpparamspecs.c --- */
/* LIBGIMP - The AmmoOS Image Library
 * Copyright (C) 1995-2003 Peter Mattis and Spencer Kimball
 *
 * gimpparamspecs.c
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

#include <gio/gio.h>

#include "gimpbase.h"


/*
 * GIMP_TYPE_PARAM_OBJECT
 */

static void         gimp_param_object_class_init            (GimpParamSpecObjectClass *klass);
static void         gimp_param_object_init                  (GimpParamSpecObject      *pspec);
static void         gimp_param_object_finalize              (GParamSpec               *pspec);
static void         gimp_param_object_value_set_default     (GParamSpec               *pspec,
                                                             GValue                   *value);

static GParamSpec * gimp_param_spec_object_real_duplicate   (GParamSpec               *pspec);
static GObject    * gimp_param_spec_object_real_get_default (GParamSpec               *pspec);


GType
gimp_param_object_get_type (void)
{
  static GType type = 0;

  if (! type)
    {
      const GTypeInfo info =
      {
        sizeof (GimpParamSpecObjectClass),
        NULL, NULL,
        (GClassInitFunc) gimp_param_object_class_init,
        NULL, NULL,
        sizeof (GimpParamSpecObject),
        0,
        (GInstanceInitFunc) gimp_param_object_init
      };

      type = g_type_register_static (G_TYPE_PARAM_OBJECT,
                                     "GimpParamObject", &info, G_TYPE_FLAG_ABSTRACT);
    }

  return type;
}

static void
gimp_param_object_class_init (GimpParamSpecObjectClass *klass)
{
  GParamSpecClass *pclass = G_PARAM_SPEC_CLASS (klass);

  klass->duplicate          = gimp_param_spec_object_real_duplicate;
  klass->get_default        = gimp_param_spec_object_real_get_default;

  pclass->value_type        = G_TYPE_OBJECT;
  pclass->finalize          = gimp_param_object_finalize;
  pclass->value_set_default = gimp_param_object_value_set_default;
}

static void
gimp_param_object_init (GimpParamSpecObject *ospec)
{
  ospec->_default_value = NULL;
}

static void
gimp_param_object_finalize (GParamSpec *pspec)
{
  GimpParamSpecObject *ospec        = GIMP_PARAM_SPEC_OBJECT (pspec);
  GParamSpecClass     *parent_class = g_type_class_peek (g_type_parent (GIMP_TYPE_PARAM_OBJECT));

  g_clear_object (&ospec->_default_value);

  parent_class->finalize (pspec);
}

static void
gimp_param_object_value_set_default (GParamSpec *pspec,
                                     GValue     *value)
{
  GObject *default_value;

  g_return_if_fail (GIMP_IS_PARAM_SPEC_OBJECT (pspec));

  default_value = gimp_param_spec_object_get_default (pspec);
  g_value_set_object (value, default_value);
}

static GParamSpec *
gimp_param_spec_object_real_duplicate (GParamSpec *pspec)
{
  GimpParamSpecObject *ospec;
  GimpParamSpecObject *duplicate;

  g_return_val_if_fail (GIMP_IS_PARAM_SPEC_OBJECT (pspec), NULL);

  ospec = GIMP_PARAM_SPEC_OBJECT (pspec);
  duplicate = g_param_spec_internal (G_TYPE_FROM_INSTANCE (pspec),
                                     pspec->name,
                                     g_param_spec_get_nick (pspec),
                                     g_param_spec_get_blurb (pspec),
                                     pspec->flags);

  duplicate->_default_value = ospec->_default_value ? g_object_ref (ospec->_default_value) : NULL;
  duplicate->_has_default   = ospec->_has_default;

  return G_PARAM_SPEC (duplicate);
}

static GObject *
gimp_param_spec_object_real_get_default (GParamSpec *pspec)
{
  g_return_val_if_fail (GIMP_IS_PARAM_SPEC_OBJECT (pspec), NULL);
  g_return_val_if_fail (GIMP_PARAM_SPEC_OBJECT (pspec)->_has_default, NULL);

  return GIMP_PARAM_SPEC_OBJECT (pspec)->_default_value;
}

/**
 * gimp_param_spec_object_get_default:
 * @pspec: a #GObject #GParamSpec
 *
 * Get the default object value of the param spec.
 *
 * If the @pspec has been registered with a specific default (which can
 * be verified with [func@Gimp.ParamSpecObject.has_default]), it will be
 * returned, though some specific subtypes may support returning dynamic
 * default (e.g. based on context).
 *
 * Returns: (transfer none): the default value.
 */
GObject *
gimp_param_spec_object_get_default (GParamSpec *pspec)
{
  g_return_val_if_fail (GIMP_IS_PARAM_SPEC_OBJECT (pspec), NULL);

  return GIMP_PARAM_SPEC_OBJECT_GET_CLASS (pspec)->get_default (pspec);
}

/**
 * gimp_param_spec_object_set_default:
 * @pspec: a #GObject #GParamSpec
 * @default_value: (transfer none) (nullable): a default value.
 *
 * Set the default object value of the param spec. This will switch the
 * `has_default` flag so that [func@Gimp.ParamSpecObject.has_default]
 * will now return %TRUE.
 *
 * A %NULL @default_value still counts as a default (unless the specific
 * @pspec does not allow %NULL as a default).
 */
void
gimp_param_spec_object_set_default (GParamSpec *pspec,
                                    GObject    *default_value)
{
  g_return_if_fail (GIMP_IS_PARAM_SPEC_OBJECT (pspec));

  GIMP_PARAM_SPEC_OBJECT (pspec)->_has_default = TRUE;
  g_set_object (&GIMP_PARAM_SPEC_OBJECT (pspec)->_default_value, default_value);
}

/**
 * gimp_param_spec_object_has_default:
 * @pspec: a #GObject #GParamSpec
 *
 * This function tells whether a default was set, typically with
 * [func@Gimp.ParamSpecObject.set_default] or any other way. It
 * does not guarantee that the default is an actual object (it may be
 * %NULL if valid as a default).
 *
 * Returns: whether a default value was set.
 */
gboolean
gimp_param_spec_object_has_default (GParamSpec *pspec)
{
  g_return_val_if_fail (GIMP_IS_PARAM_SPEC_OBJECT (pspec), FALSE);

  return GIMP_PARAM_SPEC_OBJECT (pspec)->_has_default;
}

/**
 * gimp_param_spec_object_duplicate:
 * @pspec: a [struct@Gimp.ParamSpecObject].
 *
 * This function duplicates @pspec appropriately, depending on the
 * accurate spec type.
 *
 * Returns: (transfer floating): a newly created param spec.
 */
GParamSpec *
gimp_param_spec_object_duplicate (GParamSpec *pspec)
{
  g_return_val_if_fail (GIMP_IS_PARAM_SPEC_OBJECT (pspec), NULL);

  return GIMP_PARAM_SPEC_OBJECT_GET_CLASS (pspec)->duplicate (pspec);
}


/*
 * GIMP_TYPE_PARAM_FILE
 */

#define GIMP_PARAM_SPEC_FILE(pspec)    (G_TYPE_CHECK_INSTANCE_CAST ((pspec), GIMP_TYPE_PARAM_FILE, GimpParamSpecFile))

typedef struct _GimpParamSpecFile GimpParamSpecFile;

struct _GimpParamSpecFile
{
  GimpParamSpecObject   parent_instance;

  /*< private >*/
  GimpFileChooserAction action;
  gboolean              none_ok;
};

static void         gimp_param_file_class_init     (GimpParamSpecObjectClass *klass);
static void         gimp_param_file_init           (GimpParamSpecFile        *fspec);

static gboolean     gimp_param_spec_file_validate  (GParamSpec               *pspec,
                                                    GValue                   *value);
static gint         gimp_param_spec_file_cmp       (GParamSpec               *pspec,
                                                    const GValue             *value1,
                                                    const GValue             *value2);
static GParamSpec * gimp_param_spec_file_duplicate (GParamSpec               *pspec);


/**
 * gimp_param_file_get_type:
 *
 * Reveals the object type
 *
 * Returns: the #GType for a file param object.
 *
 * Since: 3.0
 **/
GType
gimp_param_file_get_type (void)
{
  static GType type = 0;

  if (! type)
    {
      const GTypeInfo info =
      {
        sizeof (GimpParamSpecObjectClass),
        NULL, NULL,
        (GClassInitFunc) gimp_param_file_class_init,
        NULL, NULL,
        sizeof (GimpParamSpecFile),
        0,
        (GInstanceInitFunc) gimp_param_file_init
      };

      type = g_type_register_static (GIMP_TYPE_PARAM_OBJECT,
                                     "GimpParamFile", &info, 0);
    }

  return type;
}

static void
gimp_param_file_class_init (GimpParamSpecObjectClass *klass)
{
  GParamSpecClass          *pclass = G_PARAM_SPEC_CLASS (klass);
  GimpParamSpecObjectClass *oclass = GIMP_PARAM_SPEC_OBJECT_CLASS (klass);

  pclass->value_type     = G_TYPE_FILE;
  pclass->value_validate = gimp_param_spec_file_validate;
  pclass->values_cmp     = gimp_param_spec_file_cmp;
  oclass->duplicate      = gimp_param_spec_file_duplicate;
}

static void
gimp_param_file_init (GimpParamSpecFile *fspec)
{
  fspec->none_ok = TRUE;
  fspec->action  = GIMP_FILE_CHOOSER_ACTION_OPEN;
}

static gboolean
gimp_param_spec_file_validate (GParamSpec *pspec,
                               GValue     *value)
{
  GimpParamSpecFile   *fspec     = GIMP_PARAM_SPEC_FILE (pspec);
  GimpParamSpecObject *ospec     = GIMP_PARAM_SPEC_OBJECT (pspec);
  GFile               *file      = value->data[0].v_pointer;
  gboolean             modifying = FALSE;

  if (file == NULL && ! fspec->none_ok && ospec->_default_value != NULL)
    {
      modifying = TRUE;
    }
  else if (file != NULL && g_file_is_native (file))
    {
      gboolean  exists = g_file_query_exists (file, NULL);
      GFileType type   = g_file_query_file_type (file, G_FILE_QUERY_INFO_NONE, NULL);

      switch (fspec->action)
        {
        case GIMP_FILE_CHOOSER_ACTION_OPEN:
          modifying = (! exists || type != G_FILE_TYPE_REGULAR);
          break;
        case GIMP_FILE_CHOOSER_ACTION_SAVE:
          modifying = (exists && type != G_FILE_TYPE_REGULAR);
          break;
        case GIMP_FILE_CHOOSER_ACTION_SELECT_FOLDER:
          modifying = (! exists || type != G_FILE_TYPE_DIRECTORY);
          break;
        case GIMP_FILE_CHOOSER_ACTION_CREATE_FOLDER:
          modifying = (exists && type != G_FILE_TYPE_DIRECTORY);
          break;
        case GIMP_FILE_CHOOSER_ACTION_ANY:
          break;
        }
    }

  if (modifying)
    {
      g_clear_object (&file);
      value->data[0].v_pointer = ospec->_default_value ? g_object_ref (ospec->_default_value) : NULL;
    }

  return modifying;
}

static gint
gimp_param_spec_file_cmp (GParamSpec   *pspec,
                          const GValue *value1,
                          const GValue *value2)
{
  GFile *file1 = g_value_get_object (value1);
  GFile *file2 = g_value_get_object (value2);
  gchar *uri1;
  gchar *uri2;
  gint   retval;

  if (! file1 || ! file2)
    return file2 ? -1 : (file1 ? 1 : 0);

  uri1 = g_file_get_uri (file1);
  uri2 = g_file_get_uri (file2);

  retval = g_strcmp0 (uri1, uri2);

  g_free (uri1);
  g_free (uri2);

  return retval;
}

static GParamSpec *
gimp_param_spec_file_duplicate (GParamSpec *pspec)
{
  GimpParamSpecObject *ospec;
  GimpParamSpecFile   *fspec;
  GParamSpec          *duplicate;

  g_return_val_if_fail (GIMP_IS_PARAM_SPEC_FILE (pspec), NULL);

  ospec     = GIMP_PARAM_SPEC_OBJECT (pspec);
  fspec     = GIMP_PARAM_SPEC_FILE (pspec);
  duplicate = gimp_param_spec_file (pspec->name,
                                    g_param_spec_get_nick (pspec),
                                    g_param_spec_get_blurb (pspec),
                                    fspec->action, fspec->none_ok,
                                    G_FILE (ospec->_default_value),
                                    pspec->flags);
  return duplicate;
}

/**
 * gimp_param_spec_file:
 * @name:          Canonical name of the param
 * @nick:          Nickname of the param
 * @blurb:         Brief description of param.
 * @action:        The type of file to expect.
 * @none_ok:       Whether %NULL is allowed.
 * @default_value: (nullable): File to use if none is assigned.
 * @flags:         a combination of #GParamFlags
 *
 * Creates a param spec to hold a file param.
 * See g_param_spec_internal() for more information.
 *
 * Returns: (transfer full): a newly allocated #GParamSpec instance
 *
 * Since: 3.0
 **/
GParamSpec *
gimp_param_spec_file (const gchar           *name,
                      const gchar           *nick,
                      const gchar           *blurb,
                      GimpFileChooserAction  action,
                      gboolean               none_ok,
                      GFile                 *default_value,
                      GParamFlags            flags)
{
  GimpParamSpecFile   *fspec;
  GimpParamSpecObject *ospec;

  g_return_val_if_fail (default_value == NULL || G_IS_FILE (default_value), NULL);

  fspec = g_param_spec_internal (GIMP_TYPE_PARAM_FILE,
                                 name, nick, blurb, flags);

  g_return_val_if_fail (fspec, NULL);

  fspec->action         = action;
  fspec->none_ok        = none_ok;

  ospec                 = GIMP_PARAM_SPEC_OBJECT (fspec);
  ospec->_has_default   = TRUE;
  /* Note that we don't check none_ok and allows even NULL as default
   * value. What we won't allow will be trying to set a NULL value
   * later.
   */
  ospec->_default_value = default_value ? g_object_ref (G_OBJECT (default_value)) : NULL;

  return G_PARAM_SPEC (fspec);
}

/**
 * gimp_param_spec_file_get_action:
 * @pspec: a #GParamSpec to hold a #GFile value.
 *
 * Returns: the file action tied to @pspec.
 *
 * Since: 3.0
 **/
GimpFileChooserAction
gimp_param_spec_file_get_action (GParamSpec *pspec)
{
  g_return_val_if_fail (GIMP_IS_PARAM_SPEC_FILE (pspec), GIMP_FILE_CHOOSER_ACTION_ANY);

  return GIMP_PARAM_SPEC_FILE (pspec)->action;
}

/**
 * gimp_param_spec_file_set_action:
 * @pspec:  a #GParamSpec to hold a #GFile value.
 * @action: new action for @pspec.
 *
 * Change the file action tied to @pspec.
 *
 * Since: 3.0
 **/
void
gimp_param_spec_file_set_action (GParamSpec            *pspec,
                                 GimpFileChooserAction  action)
{
  g_return_if_fail (GIMP_IS_PARAM_SPEC_FILE (pspec));

  GIMP_PARAM_SPEC_FILE (pspec)->action = action;
}

/**
 * gimp_param_spec_file_none_allowed:
 * @pspec: a #GParamSpec to hold a #GFile value.
 *
 * Returns: %TRUE if a %NULL value is allowed.
 *
 * Since: 3.0
 **/
gboolean
gimp_param_spec_file_none_allowed (GParamSpec *pspec)
{
  g_return_val_if_fail (GIMP_IS_PARAM_SPEC_FILE (pspec), FALSE);

  return GIMP_PARAM_SPEC_FILE (pspec)->none_ok;
}

/*
 * GIMP_TYPE_ARRAY
 */

/**
 * gimp_array_new:
 * @data: (array length=length):
 * @length:
 * @static_data:
 */
GimpArray *
gimp_array_new (const guint8 *data,
                gsize         length,
                gboolean      static_data)
{
  GimpArray *array;

  g_return_val_if_fail ((data == NULL && length == 0) ||
                        (data != NULL && length  > 0), NULL);

  array = g_slice_new0 (GimpArray);

  array->data        = static_data ? (guint8 *) data : g_memdup2 (data, length);
  array->length      = length;
  array->static_data = static_data;

  return array;
}

GimpArray *
gimp_array_copy (const GimpArray *array)
{
  if (array)
    return gimp_array_new (array->data, array->length, FALSE);

  return NULL;
}

void
gimp_array_free (GimpArray *array)
{
  if (array)
    {
      if (! array->static_data)
        g_free (array->data);

      g_slice_free (GimpArray, array);
    }
}

G_DEFINE_BOXED_TYPE (GimpArray, gimp_array, gimp_array_copy, gimp_array_free)


/*
 * GIMP_TYPE_PARAM_ARRAY
 */

static void       gimp_param_array_class_init  (GParamSpecClass *klass);
static void       gimp_param_array_init        (GParamSpec      *pspec);
static gboolean   gimp_param_array_validate    (GParamSpec      *pspec,
                                                GValue          *value);
static gint       gimp_param_array_values_cmp  (GParamSpec      *pspec,
                                                const GValue    *value1,
                                                const GValue    *value2);

GType
gimp_param_array_get_type (void)
{
  static GType type = 0;

  if (! type)
    {
      const GTypeInfo info =
      {
        sizeof (GParamSpecClass),
        NULL, NULL,
        (GClassInitFunc) gimp_param_array_class_init,
        NULL, NULL,
        sizeof (GParamSpecBoxed),
        0,
        (GInstanceInitFunc) gimp_param_array_init
      };

      type = g_type_register_static (G_TYPE_PARAM_BOXED,
                                     "GimpParamArray", &info, 0);
    }

  return type;
}

static void
gimp_param_array_class_init (GParamSpecClass *klass)
{
  klass->value_type     = GIMP_TYPE_ARRAY;
  klass->value_validate = gimp_param_array_validate;
  klass->values_cmp     = gimp_param_array_values_cmp;
}

static void
gimp_param_array_init (GParamSpec *pspec)
{
}

static gboolean
gimp_param_array_validate (GParamSpec *pspec,
                           GValue     *value)
{
  GimpArray *array = value->data[0].v_pointer;

  if (array)
    {
      if ((array->data == NULL && array->length != 0) ||
          (array->data != NULL && array->length == 0))
        {
          g_value_set_boxed (value, NULL);
          return TRUE;
        }
    }

  return FALSE;
}

static gint
gimp_param_array_values_cmp (GParamSpec   *pspec,
                             const GValue *value1,
                             const GValue *value2)
{
  GimpArray *array1 = value1->data[0].v_pointer;
  GimpArray *array2 = value2->data[0].v_pointer;

  /*  try to return at least *something*, it's useless anyway...  */

  if (! array1)
    return array2 != NULL ? -1 : 0;
  else if (! array2)
    return array1 != NULL ? 1 : 0;
  else if (array1->length < array2->length)
    return -1;
  else if (array1->length > array2->length)
    return 1;

  return 0;
}

/**
 * gimp_param_spec_array:
 * @name:  Canonical name of the property specified.
 * @nick:  Nick name of the property specified.
 * @blurb: Description of the property specified.
 * @flags: Flags for the property specified.
 *
 * Creates a new #GimpParamSpecArray specifying a
 * [type@Array] property.
 *
 * See g_param_spec_internal() for details on property names.
 *
 * Returns: (transfer floating): The newly created #GimpParamSpecArray.
 *
 * Since: 3.0
 **/
GParamSpec *
gimp_param_spec_array (const gchar *name,
                       const gchar *nick,
                       const gchar *blurb,
                       GParamFlags  flags)
{
  GParamSpec *array_spec;

  array_spec = g_param_spec_internal (GIMP_TYPE_PARAM_ARRAY,
                                      name, nick, blurb, flags);

  return array_spec;
}

static const guint8 *
gimp_value_get_array (const GValue *value)
{
  GimpArray *array = value->data[0].v_pointer;

  if (array)
    return array->data;

  return NULL;
}

static guint8 *
gimp_value_dup_array (const GValue *value)
{
  GimpArray *array = value->data[0].v_pointer;

  if (array)
    return g_memdup2 (array->data, array->length);

  return NULL;
}

static void
gimp_value_set_array (GValue       *value,
                      const guint8 *data,
                      gsize         length)
{
  GimpArray *array = gimp_array_new (data, length, FALSE);

  g_value_take_boxed (value, array);
}

static void
gimp_value_set_static_array (GValue       *value,
                             const guint8 *data,
                             gsize         length)
{
  GimpArray *array = gimp_array_new (data, length, TRUE);

  g_value_take_boxed (value, array);
}

static void
gimp_value_take_array (GValue *value,
                       guint8 *data,
                       gsize   length)
{
  GimpArray *array = gimp_array_new (data, length, TRUE);

  array->static_data = FALSE;

  g_value_take_boxed (value, array);
}


/*
 * GIMP_TYPE_INT32_ARRAY
 */

typedef GimpArray GimpInt32Array;
G_DEFINE_BOXED_TYPE (GimpInt32Array, gimp_int32_array, gimp_array_copy, gimp_array_free)

/**
 * gimp_int32_array_get_values:
 * @array: the #GimpArray representing #int32 values.
 * @length: the number of #int32 values in the returned array.
 *
 * Returns: (array length=length) (transfer none): a C-array of #gint32.
 */
const gint32 *
gimp_int32_array_get_values (GimpArray *array,
                             gsize     *length)
{
  g_return_val_if_fail (array->length % sizeof (gint32) == 0, NULL);

  if (length)
    *length = array->length / sizeof (gint32);

  return (const gint32 *) array->data;
}

/**
 * gimp_int32_array_set_values:
 * @array: the array to modify.
 * @values: (array length=length): the C-array.
 * @length: the number of #int32 values in @data.
 * @static_data: whether @data is a static rather than allocated array.
 */
void
gimp_int32_array_set_values (GimpArray    *array,
                             const gint32 *values,
                             gsize         length,
                             gboolean      static_data)
{
  g_return_if_fail ((values == NULL && length == 0) || (values != NULL && length  > 0));

  if (! array->static_data)
    g_free (array->data);

  array->length      = length * sizeof (gint32);
  array->data        = static_data ? (guint8 *) values : g_memdup2 (values, array->length);
  array->static_data = static_data;
}


/*
 * GIMP_TYPE_PARAM_INT32_ARRAY
 */

static void   gimp_param_int32_array_class_init (GParamSpecClass *klass);
static void   gimp_param_int32_array_init       (GParamSpec      *pspec);

GType
gimp_param_int32_array_get_type (void)
{
  static GType type = 0;

  if (! type)
    {
      const GTypeInfo info =
      {
        sizeof (GParamSpecClass),
        NULL, NULL,
        (GClassInitFunc) gimp_param_int32_array_class_init,
        NULL, NULL,
        sizeof (GParamSpecBoxed),
        0,
        (GInstanceInitFunc) gimp_param_int32_array_init
      };

      type = g_type_register_static (GIMP_TYPE_PARAM_ARRAY,
                                     "GimpParamInt32Array", &info, 0);
    }

  return type;
}

static void
gimp_param_int32_array_class_init (GParamSpecClass *klass)
{
  klass->value_type = GIMP_TYPE_INT32_ARRAY;
}

static void
gimp_param_int32_array_init (GParamSpec *pspec)
{
}

/**
 * gimp_param_spec_int32_array:
 * @name:  Canonical name of the property specified.
 * @nick:  Nick name of the property specified.
 * @blurb: Description of the property specified.
 * @flags: Flags for the property specified.
 *
 * Creates a new #GimpParamSpecInt32Array specifying a
 * %GIMP_TYPE_INT32_ARRAY property.
 *
 * See g_param_spec_internal() for details on property names.
 *
 * Returns: (transfer floating): The newly created #GimpParamSpecInt32Array.
 *
 * Since: 3.0
 **/
GParamSpec *
gimp_param_spec_int32_array (const gchar *name,
                             const gchar *nick,
                             const gchar *blurb,
                             GParamFlags  flags)
{
  GParamSpec *array_spec;

  array_spec = g_param_spec_internal (GIMP_TYPE_PARAM_INT32_ARRAY,
                                      name, nick, blurb, flags);

  return array_spec;
}

/**
 * gimp_value_get_int32_array:
 * @value: A valid value of type %GIMP_TYPE_INT32_ARRAY
 * @length: the number of returned #int32 elements.
 *
 * Gets the contents of a %GIMP_TYPE_INT32_ARRAY #GValue
 *
 * Returns: (transfer none) (array length=length): The contents of @value
 */
const gint32 *
gimp_value_get_int32_array (const GValue *value,
                            gsize        *length)
{
  GimpArray *array;

  g_return_val_if_fail (GIMP_VALUE_HOLDS_INT32_ARRAY (value), NULL);

  array = value->data[0].v_pointer;

  g_return_val_if_fail (array->length % sizeof (gint32) == 0, NULL);

  if (length)
    *length = array->length / sizeof (gint32);

  return (const gint32 *) gimp_value_get_array (value);
}

/**
 * gimp_value_dup_int32_array:
 * @value: A valid value of type %GIMP_TYPE_INT32_ARRAY
 * @length: the number of returned #int32 elements.
 *
 * Gets the contents of a %GIMP_TYPE_INT32_ARRAY #GValue
 *
 * Returns: (transfer full) (array length=length): The contents of @value
 */
gint32 *
gimp_value_dup_int32_array (const GValue *value,
                            gsize        *length)
{
  GimpArray *array;

  g_return_val_if_fail (GIMP_VALUE_HOLDS_INT32_ARRAY (value), NULL);

  array = value->data[0].v_pointer;

  g_return_val_if_fail (array->length % sizeof (gint32) == 0, NULL);

  if (length)
    *length = array->length / sizeof (gint32);

  return (gint32 *) gimp_value_dup_array (value);
}

/**
 * gimp_value_set_int32_array:
 * @value: A valid value of type %GIMP_TYPE_INT32_ARRAY
 * @data: (array length=length): A #gint32 array
 * @length: The number of elements in @data
 *
 * Sets the contents of @value to @data.
 */
void
gimp_value_set_int32_array (GValue       *value,
                            const gint32 *data,
                            gsize         length)
{
  g_return_if_fail (GIMP_VALUE_HOLDS_INT32_ARRAY (value));

  gimp_value_set_array (value, (const guint8 *) data,
                        length * sizeof (gint32));
}

/**
 * gimp_value_set_static_int32_array:
 * @value: A valid value of type %GIMP_TYPE_INT32_ARRAY
 * @data: (array length=length): A #gint32 array
 * @length: The number of elements in @data
 *
 * Sets the contents of @value to @data, without copying the data.
 */
void
gimp_value_set_static_int32_array (GValue       *value,
                                   const gint32 *data,
                                   gsize         length)
{
  g_return_if_fail (GIMP_VALUE_HOLDS_INT32_ARRAY (value));

  gimp_value_set_static_array (value, (const guint8 *) data,
                               length * sizeof (gint32));
}

/**
 * gimp_value_take_int32_array:
 * @value: A valid value of type %GIMP_TYPE_int32_ARRAY
 * @data: (transfer full) (array length=length): A #gint32 array
 * @length: The number of elements in @data
 *
 * Sets the contents of @value to @data, and takes ownership of @data.
 */
void
gimp_value_take_int32_array (GValue *value,
                             gint32 *data,
                             gsize   length)
{
  g_return_if_fail (GIMP_VALUE_HOLDS_INT32_ARRAY (value));

  gimp_value_take_array (value, (guint8 *) data,
                         length * sizeof (gint32));
}


/*
 * GIMP_TYPE_DOUBLE_ARRAY
 */

typedef GimpArray GimpDoubleArray;
G_DEFINE_BOXED_TYPE (GimpDoubleArray, gimp_double_array, gimp_array_copy, gimp_array_free)

/**
 * gimp_double_array_get_values:
 * @array: the #GimpArray representing #double values.
 * @length: the number of #double values in the returned array.
 *
 * Returns: (array length=length) (transfer none): a C-array of #gdouble.
 */
const gdouble *
gimp_double_array_get_values (GimpArray *array,
                              gsize     *length)
{
  g_return_val_if_fail (array->length % sizeof (gdouble) == 0, NULL);

  if (length)
    *length = array->length / sizeof (gdouble);

  return (const gdouble *) array->data;
}

/**
 * gimp_double_array_set_values:
 * @array: the array to modify.
 * @values: (array length=length): the C-array.
 * @length: the number of #double values in @data.
 * @static_data: whether @data is a static rather than allocated array.
 */
void
gimp_double_array_set_values (GimpArray     *array,
                              const gdouble *values,
                              gsize          length,
                              gboolean       static_data)
{
  g_return_if_fail ((values == NULL && length == 0) || (values != NULL && length  > 0));

  if (! array->static_data)
    g_free (array->data);

  array->length      = length * sizeof (gdouble);
  array->data        = static_data ? (guint8 *) values : g_memdup2 (values, array->length);
  array->static_data = static_data;
}


/*
 * GIMP_TYPE_PARAM_DOUBLE_ARRAY
 */

static void   gimp_param_double_array_class_init (GParamSpecClass *klass);
static void   gimp_param_double_array_init       (GParamSpec      *pspec);

GType
gimp_param_double_array_get_type (void)
{
  static GType type = 0;

  if (! type)
    {
      const GTypeInfo info =
      {
        sizeof (GParamSpecClass),
        NULL, NULL,
        (GClassInitFunc) gimp_param_double_array_class_init,
        NULL, NULL,
        sizeof (GParamSpecBoxed),
        0,
        (GInstanceInitFunc) gimp_param_double_array_init
      };

      type = g_type_register_static (GIMP_TYPE_PARAM_ARRAY,
                                     "GimpParamDoubleArray", &info, 0);
    }

  return type;
}

static void
gimp_param_double_array_class_init (GParamSpecClass *klass)
{
  klass->value_type = GIMP_TYPE_DOUBLE_ARRAY;
}

static void
gimp_param_double_array_init (GParamSpec *pspec)
{
}

/**
 * gimp_param_spec_double_array:
 * @name:  Canonical name of the property specified.
 * @nick:  Nick name of the property specified.
 * @blurb: Description of the property specified.
 * @flags: Flags for the property specified.
 *
 * Creates a new #GimpParamSpecDoubleArray specifying a
 * %GIMP_TYPE_DOUBLE_ARRAY property.
 *
 * See g_param_spec_internal() for details on property names.
 *
 * Returns: (transfer floating): The newly created #GimpParamSpecDoubleArray.
 *
 * Since: 3.0
 **/
GParamSpec *
gimp_param_spec_double_array (const gchar *name,
                              const gchar *nick,
                              const gchar *blurb,
                              GParamFlags  flags)
{
  GParamSpec *array_spec;

  array_spec = g_param_spec_internal (GIMP_TYPE_PARAM_DOUBLE_ARRAY,
                                      name, nick, blurb, flags);

  return array_spec;
}

/**
 * gimp_value_get_double_array:
 * @value: A valid value of type %GIMP_TYPE_DOUBLE_ARRAY
 * @length: the number of returned #double elements.
 *
 * Gets the contents of a %GIMP_TYPE_DOUBLE_ARRAY #GValue
 *
 * Returns: (transfer none) (array length=length): The contents of @value
 */
const gdouble *
gimp_value_get_double_array (const GValue *value,
                             gsize        *length)
{
  GimpArray *array;

  g_return_val_if_fail (GIMP_VALUE_HOLDS_DOUBLE_ARRAY (value), NULL);

  array = value->data[0].v_pointer;

  g_return_val_if_fail (array->length % sizeof (gdouble) == 0, NULL);

  if (length)
    *length = array->length / sizeof (gdouble);

  return (const gdouble *) gimp_value_get_array (value);
}

/**
 * gimp_value_dup_double_array:
 * @value: A valid value of type %GIMP_TYPE_DOUBLE_ARRAY
 * @length: the number of returned #double elements.
 *
 * Gets the contents of a %GIMP_TYPE_DOUBLE_ARRAY #GValue
 *
 * Returns: (transfer full) (array length=length): The contents of @value
 */
gdouble *
gimp_value_dup_double_array (const GValue *value,
                             gsize        *length)
{
  GimpArray *array;

  g_return_val_if_fail (GIMP_VALUE_HOLDS_DOUBLE_ARRAY (value), NULL);

  array = value->data[0].v_pointer;

  g_return_val_if_fail (array->length % sizeof (gdouble) == 0, NULL);

  if (length)
    *length = array->length / sizeof (gdouble);

  return (gdouble *) gimp_value_dup_array (value);
}

/**
 * gimp_value_set_double_array:
 * @value: A valid value of type %GIMP_TYPE_DOUBLE_ARRAY
 * @data: (array length=length): A #gdouble array
 * @length: The number of elements in @data
 *
 * Sets the contents of @value to @data.
 */
void
gimp_value_set_double_array (GValue        *value,
                             const gdouble *data,
                             gsize         length)
{
  g_return_if_fail (GIMP_VALUE_HOLDS_DOUBLE_ARRAY (value));

  gimp_value_set_array (value, (const guint8 *) data,
                        length * sizeof (gdouble));
}

/**
 * gimp_value_set_static_double_array:
 * @value: A valid value of type %GIMP_TYPE_DOUBLE_ARRAY
 * @data: (array length=length): A #gdouble array
 * @length: The number of elements in @data
 *
 * Sets the contents of @value to @data, without copying the data.
 */
void
gimp_value_set_static_double_array (GValue        *value,
                                    const gdouble *data,
                                    gsize         length)
{
  g_return_if_fail (GIMP_VALUE_HOLDS_DOUBLE_ARRAY (value));

  gimp_value_set_static_array (value, (const guint8 *) data,
                               length * sizeof (gdouble));
}

/**
 * gimp_value_take_double_array:
 * @value: A valid value of type %GIMP_TYPE_DOUBLE_ARRAY
 * @data: (transfer full) (array length=length): A #gdouble array
 * @length: The number of elements in @data
 *
 * Sets the contents of @value to @data, and takes ownership of @data.
 */
void
gimp_value_take_double_array (GValue  *value,
                              gdouble *data,
                              gsize    length)
{
  g_return_if_fail (GIMP_VALUE_HOLDS_DOUBLE_ARRAY (value));

  gimp_value_take_array (value, (guint8 *) data,
                         length * sizeof (gdouble));
}


/*
 * GIMP_TYPE_COLOR_ARRAY
 */

GType
gimp_color_array_get_type (void)
{
  static gsize static_g_define_type_id = 0;

  if (g_once_init_enter (&static_g_define_type_id))
    {
      GType g_define_type_id =
        g_boxed_type_register_static (g_intern_static_string ("GimpColorArray"),
                                      (GBoxedCopyFunc) gimp_color_array_copy,
                                      (GBoxedFreeFunc) gimp_color_array_free);

      g_once_init_leave (&static_g_define_type_id, g_define_type_id);
    }

  return static_g_define_type_id;
}

/**
 * gimp_color_array_copy:
 * @array: an array of colors.
 *
 * Creates a new #GimpColorArray containing a deep copy of a %NULL-terminated
 * array of [class@Gegl.Color].
 *
 * Returns: (transfer full): a new #GimpColorArray.
 **/
GimpColorArray
gimp_color_array_copy (GimpColorArray array)
{
  GeglColor **copy;
  gint        length = gimp_color_array_get_length (array);

  copy = g_malloc0 (sizeof (GeglColor *) * (length + 1));

  for (gint i = 0; i < length; i++)
    copy[i] = gegl_color_duplicate (array[i]);

  return copy;
}

/**
 * gimp_color_array_free:
 * @array: an array of colors.
 *
 * Frees a %NULL-terminated array of [class@Gegl.Color].
 **/
void
gimp_color_array_free (GimpColorArray array)
{
  gint i = 0;

  while (array[i] != NULL)
    g_object_unref (array[i++]);

  g_free (array);
}

/**
 * gimp_color_array_get_length:
 * @array: an array of colors.
 *
 * Returns: the number of [class@Gegl.Color] in @array.
 **/
gint
gimp_color_array_get_length (GimpColorArray array)
{
  gint length = 0;

  while (array[length] != NULL)
    length++;

  return length;
}


/*
 * GIMP_TYPE_CORE_OBJECT_ARRAY
 */

static GimpCoreObjectArray gimp_core_object_array_copy (GimpCoreObjectArray array);

GType
gimp_core_object_array_get_type (void)
{
  static gsize static_g_define_type_id = 0;

  if (g_once_init_enter (&static_g_define_type_id))
    {
      GType g_define_type_id =
        g_boxed_type_register_static (g_intern_static_string ("GimpCoreObjectArray"),
                                      (GBoxedCopyFunc) gimp_core_object_array_copy,
                                      (GBoxedFreeFunc) g_free);

      g_once_init_leave (&static_g_define_type_id, g_define_type_id);
    }

  return static_g_define_type_id;
}

/**
 * gimp_core_object_array_get_length:
 * @array: a %NULL-terminated array of objects.
 *
 * Returns: the number of [class@GObject.Object] in @array.
 **/
gsize
gimp_core_object_array_get_length (GObject **array)
{
  gsize length = 0;

  while (array && array[length] != NULL)
    length++;

  return length;
}

/**
 * gimp_core_object_array_copy:
 * @array: an array of core_objects.
 *
 * Duplicate a new #GimpCoreObjectArray, which is basically simply a
 * %NULL-terminated array of [class@GObject.Object]. Note that you
 * should only use this alias type for arrays of core type objects
 * internally hold by `libgimp`, such as layers, channels, paths, images
 * and so on, because no reference is hold to the element objects.
 *
 * As a consequence, the copy also makes a shallow copy of the elements.
 *
 * Returns: (transfer container) (array zero-terminated=1): a new #GimpCoreObjectArray.
 **/
static GimpCoreObjectArray
gimp_core_object_array_copy (GimpCoreObjectArray array)
{
  GObject **copy;
  gsize     length = gimp_core_object_array_get_length (array);

  copy = g_malloc0 (sizeof (GObject *) * (length + 1));

  for (gint i = 0; i < length; i++)
    copy[i] = array[i];

  return copy;
}


/*
 * GIMP_TYPE_PARAM_CORE_OBJECT_ARRAY
 */

#define GIMP_PARAM_SPEC_CORE_OBJECT_ARRAY(pspec)    (G_TYPE_CHECK_INSTANCE_CAST ((pspec), GIMP_TYPE_PARAM_CORE_OBJECT_ARRAY, GimpParamSpecCoreObjectArray))

typedef struct _GimpParamSpecCoreObjectArray GimpParamSpecCoreObjectArray;

struct _GimpParamSpecCoreObjectArray
{
  GParamSpecBoxed parent_instance;

  GType           object_type;
};

static void       gimp_param_core_object_array_class_init  (GParamSpecClass *klass);
static void       gimp_param_core_object_array_init        (GParamSpec      *pspec);
static gboolean   gimp_param_core_object_array_validate    (GParamSpec      *pspec,
                                                            GValue          *value);
static gint       gimp_param_core_object_array_values_cmp  (GParamSpec      *pspec,
                                                            const GValue    *value1,
                                                            const GValue    *value2);

GType
gimp_param_core_object_array_get_type (void)
{
  static GType type = 0;

  if (! type)
    {
      const GTypeInfo info =
      {
        sizeof (GParamSpecClass),
        NULL, NULL,
        (GClassInitFunc) gimp_param_core_object_array_class_init,
        NULL, NULL,
        sizeof (GimpParamSpecCoreObjectArray),
        0,
        (GInstanceInitFunc) gimp_param_core_object_array_init
      };

      type = g_type_register_static (G_TYPE_PARAM_BOXED,
                                     "GimpParamCoreObjectArray", &info, 0);
    }

  return type;
}

static void
gimp_param_core_object_array_class_init (GParamSpecClass *klass)
{
  klass->value_type     = GIMP_TYPE_CORE_OBJECT_ARRAY;
  klass->value_validate = gimp_param_core_object_array_validate;
  klass->values_cmp     = gimp_param_core_object_array_values_cmp;
}

static void
gimp_param_core_object_array_init (GParamSpec *pspec)
{
}

static gboolean
gimp_param_core_object_array_validate (GParamSpec *pspec,
                                       GValue     *value)
{
  GimpParamSpecCoreObjectArray  *array_spec = GIMP_PARAM_SPEC_CORE_OBJECT_ARRAY (pspec);
  GObject                      **array      = value->data[0].v_pointer;

  if (array)
    {
      gsize length = gimp_core_object_array_get_length (array);
      gsize i;

      if (length == 0)
        {
          g_value_set_boxed (value, NULL);
          return FALSE;
        }

      for (i = 0; i < length; i++)
        {
          if (array[i] && ! g_type_is_a (G_OBJECT_TYPE (array[i]), array_spec->object_type))
            {
              g_value_set_boxed (value, NULL);
              return TRUE;
            }
        }
    }

  return FALSE;
}

static gint
gimp_param_core_object_array_values_cmp (GParamSpec   *pspec,
                                         const GValue *value1,
                                         const GValue *value2)
{
  GObject **array1 = value1->data[0].v_pointer;
  GObject **array2 = value2->data[0].v_pointer;

  /*  try to return at least *something*, it's useless anyway...  */

  if (! array1)
    return array2 != NULL ? -1 : 0;
  else if (! array2)
    return array1 != NULL ? 1 : 0;
  else if (gimp_core_object_array_get_length (array1) < gimp_core_object_array_get_length (array2))
    return -1;
  else if (gimp_core_object_array_get_length (array1) > gimp_core_object_array_get_length (array2))
    return 1;

  for (gsize i = 0; i < gimp_core_object_array_get_length (array1); i++)
    if (array1[0] != array2[0])
      return 1;

  return 0;
}

/**
 * gimp_param_spec_core_object_array:
 * @name:        Canonical name of the property specified.
 * @nick:        Nick name of the property specified.
 * @blurb:       Description of the property specified.
 * @object_type: GType of the array's elements.
 * @flags:       Flags for the property specified.
 *
 * Creates a new #GimpParamSpecCoreObjectArray specifying a
 * [type@CoreObjectArray] property.
 *
 * See g_param_spec_internal() for details on property names.
 *
 * Returns: (transfer floating): The newly created #GimpParamSpecCoreObjectArray.
 *
 * Since: 3.0
 **/
GParamSpec *
gimp_param_spec_core_object_array (const gchar *name,
                                   const gchar *nick,
                                   const gchar *blurb,
                                   GType        object_type,
                                   GParamFlags  flags)
{
  GimpParamSpecCoreObjectArray *array_spec;

  g_return_val_if_fail (g_type_is_a (object_type, G_TYPE_OBJECT), NULL);

  array_spec = g_param_spec_internal (GIMP_TYPE_PARAM_CORE_OBJECT_ARRAY,
                                      name, nick, blurb, flags);

  g_return_val_if_fail (array_spec, NULL);

  array_spec->object_type = object_type;

  return G_PARAM_SPEC (array_spec);
}

/**
 * gimp_param_spec_core_object_array_get_object_type:
 * @pspec: a #GParamSpec to hold a #GimpParamSpecCoreObjectArray value.
 *
 * Returns: the type for objects in the object array.
 *
 * Since: 3.0
 **/
GType
gimp_param_spec_core_object_array_get_object_type (GParamSpec *pspec)
{
  g_return_val_if_fail (GIMP_IS_PARAM_SPEC_CORE_OBJECT_ARRAY (pspec), G_TYPE_NONE);

  return GIMP_PARAM_SPEC_CORE_OBJECT_ARRAY (pspec)->object_type;
}

/* --- end libammoos/base/fieldbase/gimpparamspecs.c --- */

/* --- begin libammoos/base/fieldbase/gimpparasite.c --- */
/* LIBGIMP - The AmmoOS Image Library
 * Copyright (C) 1995-1997 Peter Mattis and Spencer Kimball
 *
 * gimpparasite.c
 * Copyright (C) 1998 Jay Cox <jaycox@ammoos.org>
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
#ifdef HAVE_UNISTD_H
#include <unistd.h>
#endif
#include <string.h>

#include <glib-object.h>

#ifdef G_OS_WIN32
#include <process.h>                /* For _getpid() */
#endif

#include "gimpbasetypes.h"

#include "gimpparasite.h"


/**
 * SECTION: gimpparasite
 * @title: GimpParasite
 * @short_description: Arbitrary pieces of data which can be attached
 *                     to various AmmoOS Image objects.
 * @see_also: gimp_image_attach_parasite(), gimp_item_attach_parasite(),
 *            gimp_attach_parasite() and their related functions.
 *
 * Arbitrary pieces of data which can be attached to various AmmoOS Image objects.
 **/


/*
 * GIMP_TYPE_PARASITE
 */

G_DEFINE_BOXED_TYPE (GimpParasite, gimp_parasite, gimp_parasite_copy, gimp_parasite_free)

/*
 * GIMP_TYPE_PARAM_PARASITE
 */


static void       gimp_param_parasite_class_init  (GParamSpecClass *class);
static void       gimp_param_parasite_init        (GParamSpec      *pspec);
static gboolean   gimp_param_parasite_validate    (GParamSpec      *pspec,
                                                   GValue          *value);
static gint       gimp_param_parasite_values_cmp  (GParamSpec      *pspec,
                                                   const GValue    *value1,
                                                   const GValue    *value2);

GType
gimp_param_parasite_get_type (void)
{
  static GType type = 0;

  if (! type)
    {
      const GTypeInfo type_info =
      {
        sizeof (GParamSpecClass),
        NULL, NULL,
        (GClassInitFunc) gimp_param_parasite_class_init,
        NULL, NULL,
        sizeof (GParamSpecBoxed),
        0,
        (GInstanceInitFunc) gimp_param_parasite_init
      };

      type = g_type_register_static (G_TYPE_PARAM_BOXED,
                                     "GimpParamParasite",
                                     &type_info, 0);
    }

  return type;
}

static void
gimp_param_parasite_class_init (GParamSpecClass *class)
{
  class->value_type     = GIMP_TYPE_PARASITE;
  class->value_validate = gimp_param_parasite_validate;
  class->values_cmp     = gimp_param_parasite_values_cmp;
}

static void
gimp_param_parasite_init (GParamSpec *pspec)
{
}

static gboolean
gimp_param_parasite_validate (GParamSpec *pspec,
                              GValue     *value)
{
  GimpParasite *parasite = value->data[0].v_pointer;

  if (! parasite)
    {
      return TRUE;
    }
  else if (parasite->name == NULL                          ||
           *parasite->name == '\0'                         ||
           ! g_utf8_validate (parasite->name, -1, NULL)    ||
           (parasite->size == 0 && parasite->data != NULL) ||
           (parasite->size >  0 && parasite->data == NULL))
    {
      g_value_set_boxed (value, NULL);
      return TRUE;
    }

  return FALSE;
}

static gint
gimp_param_parasite_values_cmp (GParamSpec   *pspec,
                                const GValue *value1,
                                const GValue *value2)
{
  GimpParasite *parasite1 = value1->data[0].v_pointer;
  GimpParasite *parasite2 = value2->data[0].v_pointer;

  /*  try to return at least *something*, it's useless anyway...  */

  if (! parasite1)
    return parasite2 != NULL ? -1 : 0;
  else if (! parasite2)
    return parasite1 != NULL;
  else
    return gimp_parasite_compare (parasite1, parasite2);
}

/**
 * gimp_param_spec_parasite:
 * @name:  Canonical name of the property specified.
 * @nick:  Nick name of the property specified.
 * @blurb: Description of the property specified.
 * @flags: Flags for the property specified.
 *
 * Creates a new #GimpParamSpecParasite specifying a
 * [type@Parasite] property.
 *
 * See g_param_spec_internal() for details on property names.
 *
 * Returns: (transfer full): The newly created #GimpParamSpecParasite.
 *
 * Since: 2.4
 **/
GParamSpec *
gimp_param_spec_parasite (const gchar *name,
                          const gchar *nick,
                          const gchar *blurb,
                          GParamFlags  flags)
{
  GParamSpec *parasite_spec;

  parasite_spec = g_param_spec_internal (GIMP_TYPE_PARAM_PARASITE,
                                         name, nick, blurb, flags);

  return parasite_spec;
}


#ifdef DEBUG
static void
gimp_parasite_print (GimpParasite *parasite)
{
  if (parasite == NULL)
    {
      g_print ("pid %d: attempt to print a null parasite\n", getpid ());
      return;
    }

  g_print ("pid %d: parasite: %p\n", getpid (), parasite);

  if (parasite->name)
    g_print ("\tname: %s\n", parasite->name);
  else
    g_print ("\tname: NULL\n");

  g_print ("\tflags: %d\n", parasite->flags);
  g_print ("\tsize: %d\n", parasite->size);
  if (parasite->size > 0)
    g_print ("\tdata: %p\n", parasite->data);
}
#endif

/**
 * gimp_parasite_new:
 * @name:  the new #GimpParasite name.
 * @flags: see [const@Gimp.PARASITE_PERSISTENT] and [const@Gimp.PARASITE_UNDOABLE];
 *   other values are mainly intended for internal use.
 * @size:  the size of @data, including a terminal %NULL byte if needed.
 * @data:  (nullable) (array length=size) (element-type char): the data to save in a parasite.
 *
 * Creates a new parasite and save @data which may be a proper text (in
 * which case you may want to set @size as strlen(@data) + 1) or not.
 *
 * Returns: (transfer full): a new #GimpParasite.
 */
GimpParasite *
gimp_parasite_new (const gchar    *name,
                   guint32         flags,
                   guint32         size,
                   gconstpointer   data)
{
  GimpParasite *parasite;

  if (! (name && *name))
    return NULL;

  parasite = g_slice_new (GimpParasite);
  parasite->name  = g_strdup (name);
  parasite->flags = (flags & 0xFF);
  parasite->size  = size;

  if (size)
    parasite->data = g_memdup2 (data, size);
  else
    parasite->data = NULL;

  return parasite;
}

/**
 * gimp_parasite_free:
 * @parasite: a #GimpParasite
 *
 * Free @parasite's dynamically allocated memory.
 */
void
gimp_parasite_free (GimpParasite *parasite)
{
  if (parasite == NULL)
    return;

  if (parasite->name)
    g_free (parasite->name);

  if (parasite->data)
    g_free (parasite->data);

  g_slice_free (GimpParasite, parasite);
}

/**
 * gimp_parasite_is_type:
 * @parasite: a #GimpParasite
 * @name:     a parasite name.
 *
 * Compare parasite's names.
 *
 * Returns: %TRUE if @parasite is named @name, %FALSE otherwise.
 */
gboolean
gimp_parasite_is_type (const GimpParasite *parasite,
                       const gchar        *name)
{
  if (!parasite || !parasite->name)
    return FALSE;

  return (strcmp (parasite->name, name) == 0);
}

/**
 * gimp_parasite_copy:
 * @parasite: a #GimpParasite
 *
 * Create a new parasite with all the same values.
 *
 * Returns: (transfer full): a newly allocated #GimpParasite with same contents.
 */
GimpParasite *
gimp_parasite_copy (const GimpParasite *parasite)
{
  if (parasite == NULL)
    return NULL;

  return gimp_parasite_new (parasite->name, parasite->flags,
                            parasite->size, parasite->data);
}

/**
 * gimp_parasite_compare:
 * @a: a #GimpParasite
 * @b: a #GimpParasite
 *
 * Compare parasite's contents.
 *
 * Returns: %TRUE if @a and @b have same contents, %FALSE otherwise.
 */
gboolean
gimp_parasite_compare (const GimpParasite *a,
                       const GimpParasite *b)
{
  if (a && b &&
      a->name && b->name &&
      strcmp (a->name, b->name) == 0 &&
      a->flags == b->flags &&
      a->size == b->size)
    {
      if (a->data == NULL && b->data == NULL)
        return TRUE;
      else if (a->data && b->data && memcmp (a->data, b->data, a->size) == 0)
        return TRUE;
    }

  return FALSE;
}

/**
 * gimp_parasite_get_flags:
 * @parasite: a #GimpParasite
 *
 * Get the flags of the parasite.
 *
 * Returns: @parasite flags.
 */
gulong
gimp_parasite_get_flags (const GimpParasite *parasite)
{
  if (parasite == NULL)
    return 0;

  return parasite->flags;
}

/**
 * gimp_parasite_is_persistent:
 * @parasite: a #GimpParasite
 *
 * Returns: %TRUE if @parasite is persistent, %FALSE otherwise.
 */
gboolean
gimp_parasite_is_persistent (const GimpParasite *parasite)
{
  if (parasite == NULL)
    return FALSE;

  return (parasite->flags & GIMP_PARASITE_PERSISTENT);
}

/**
 * gimp_parasite_is_undoable:
 * @parasite: a #GimpParasite
 *
 * Returns: %TRUE if @parasite is undoable, %FALSE otherwise.
 */
gboolean
gimp_parasite_is_undoable (const GimpParasite *parasite)
{
  if (parasite == NULL)
    return FALSE;

  return (parasite->flags & GIMP_PARASITE_UNDOABLE);
}

/**
 * gimp_parasite_has_flag:
 * @parasite: a #GimpParasite
 * @flag:     a parasite flag
 *
 * Returns: %TRUE if @parasite has @flag set, %FALSE otherwise.
 */
gboolean
gimp_parasite_has_flag (const GimpParasite *parasite,
                        gulong              flag)
{
  if (parasite == NULL)
    return FALSE;

  return (parasite->flags & flag);
}

/**
 * gimp_parasite_get_name:
 * @parasite: a #GimpParasite
 *
 * Returns: @parasite's name.
 */
const gchar *
gimp_parasite_get_name (const GimpParasite *parasite)
{
  if (parasite)
    return parasite->name;

  return NULL;
}

/**
 * gimp_parasite_get_data:
 * @parasite: a #GimpParasite
 * @num_bytes: (out) (nullable): size of the returned data.
 *
 * Gets the parasite's data. It may not necessarily be text, nor is it
 * guaranteed to be %NULL-terminated. It is your responsibility to know
 * how to deal with this data.
 * Even when you expect a nul-terminated string, it is advised not to
 * assume the returned data to be, as parasites can be edited by third
 * party scripts. You may end up reading out-of-bounds data. So you
 * should only ignore @num_bytes when you all you care about is checking
 * if the parasite has contents.
 *
 * Returns: (array length=num_bytes) (element-type char): parasite's data.
 */
gconstpointer
gimp_parasite_get_data (const GimpParasite *parasite,
                        guint32            *num_bytes)
{
  if (parasite)
    {
      if (num_bytes)
        *num_bytes = parasite->size;

      return parasite->data;
    }

  if (num_bytes)
    *num_bytes = 0;

  return NULL;
}

/* --- end libammoos/base/fieldbase/gimpparasite.c --- */

/* --- begin libammoos/base/fieldbase/gimpparasiteio.c --- */
/* LIBGIMP - The AmmoOS Image Library
 * Copyright (C) 1995-1997 Peter Mattis and Spencer Kimball
 *
 * gimpparasiteio.c
 * Copyright (C) 1999 Tor Lillqvist <tml@iki.fi>
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

/*
 * Functions for building and parsing string representations of
 * various standard parasite types.
 */

#include "config.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <glib.h>

#include "gimpparasiteio.h"
#include "gimpversion-private.h"


GIMP_WARNING_API_BREAK("Undeprecate this whole API and make it private instead")


/**
 * SECTION: gimpparasiteio
 * @title: gimpparasiteio
 * @short_description: Utility functions to (de)serialize certain C
 *                     structures to/from #GimpParasite's.
 * @see_also: #GimpParasite
 *
 * Utility functions to (de)serialize certain C structures to/from*
 * #GimpParasite's.
 **/


/**
 * gimp_pixpipe_params_init:
 * @params:
 *
 * Do not use this function. It is deprecated and will be removed
 * eventually.
 *
 * Deprecated: 3.2: Only for core use.
 */
void
gimp_pixpipe_params_init (GimpPixPipeParams *params)
{
  gint i;

  g_return_if_fail (params != NULL);

  params->step       = 100;
  params->ncells     = 1;
  params->cellwidth  = 1;
  params->cellheight = 1;
  params->dim        = 1;
  params->cols       = 1;
  params->rows       = 1;
  params->placement  = g_strdup ("constant");

  for (i = 0; i < GIMP_PIXPIPE_MAXDIM; i++)
    params->selection[i] = g_strdup ("random");

  params->rank[0] = 1;
  for (i = 1; i < GIMP_PIXPIPE_MAXDIM; i++)
    params->rank[i] = 0;
}

/**
 * gimp_pixpipe_params_parse:
 * @parameters:
 * @params:
 *
 * Do not use this function. It is deprecated and will be removed
 * eventually.
 *
 * Deprecated: 3.2: Only for core use.
 */
void
gimp_pixpipe_params_parse (const gchar       *parameters,
                           GimpPixPipeParams *params)
{
  gchar *copy;
  gchar *p, *q, *r;
  gint   i;
#ifdef _UCRT
  gchar *context = NULL;
#endif

  g_return_if_fail (parameters != NULL);
  g_return_if_fail (params != NULL);

  copy = g_strdup (parameters);

  q = copy;
#ifndef _UCRT
  while ((p = strtok (q, " \r\n")) != NULL)
#else
  while ((p = strtok_s (q, " \r\n", &context)) != NULL)
#endif
    {
      q = NULL;
      r = strchr (p, ':');
      if (r)
        *r = 0;

      if (strcmp (p, "ncells") == 0)
        {
          if (r)
            params->ncells = atoi (r + 1);
        }
      else if (strcmp (p, "step") == 0)
        {
          if (r)
            params->step = atoi (r + 1);
        }
      else if (strcmp (p, "dim") == 0)
        {
          if (r)
            {
              params->dim = atoi (r + 1);
              params->dim = CLAMP (params->dim, 1, GIMP_PIXPIPE_MAXDIM);
            }
        }
      else if (strcmp (p, "cols") == 0)
        {
          if (r)
            params->cols = atoi (r + 1);
        }
      else if (strcmp (p, "rows") == 0)
        {
          if (r)
            params->rows = atoi (r + 1);
        }
      else if (strcmp (p, "cellwidth") == 0)
        {
          if (r)
            params->cellwidth = atoi (r + 1);
        }
      else if (strcmp (p, "cellheight") == 0)
        {
          if (r)
            params->cellheight = atoi (r + 1);
        }
      else if (strcmp (p, "placement") == 0)
        {
          if (r)
            {
              g_free (params->placement);
              params->placement = g_strdup (r + 1);
            }
        }
      else if (strncmp (p, "rank", strlen ("rank")) == 0 && r)
        {
          if (r)
            {
              i = atoi (p + strlen ("rank"));
              if (i >= 0 && i < params->dim)
                params->rank[i] = atoi (r + 1);
            }
        }
      else if (strncmp (p, "sel", strlen ("sel")) == 0 && r)
        {
          if (r)
            {
              i = atoi (p + strlen ("sel"));
              if (i >= 0 && i < params->dim)
                {
                  g_free (params->selection[i]);
                  params->selection[i] = g_strdup (r + 1);
                }
            }
        }
      if (r)
        *r = ':';
    }

  g_free (copy);
}

/**
 * gimp_pixpipe_params_build:
 * @params:
 *
 * Do not use this function. It is deprecated and will be removed
 * eventually.
 *
 * Deprecated: 3.2: Only for core use.
 */
gchar *
gimp_pixpipe_params_build (GimpPixPipeParams *params)
{
  GString *str;
  gint     i;

  g_return_val_if_fail (params != NULL, NULL);

  str = g_string_new (NULL);

  g_string_printf (str, "ncells:%d cellwidth:%d cellheight:%d "
                   "step:%d dim:%d cols:%d rows:%d placement:%s",
                   params->ncells, params->cellwidth, params->cellheight,
                   params->step, params->dim,
                   params->cols, params->rows,
                   params->placement);

  for (i = 0; i < params->dim; i++)
    {
      g_string_append_printf (str, " rank%d:%d", i, params->rank[i]);
      g_string_append_printf (str, " sel%d:%s", i, params->selection[i]);
    }

  return g_string_free (str, FALSE);
}

/**
 * gimp_pixpipe_params_free:
 * @params:
 *
 * Do not use this function. It is deprecated and will be removed
 * eventually.
 *
 * Deprecated: 3.2: Only for core use.
 */
void
gimp_pixpipe_params_free (GimpPixPipeParams *params)
{
  gint i;

  g_free (params->placement);

  for (i = 0; i < GIMP_PIXPIPE_MAXDIM; i++)
    g_free (params->selection[i]);
}

/* --- end libammoos/base/fieldbase/gimpparasiteio.c --- */

/* --- begin libammoos/base/fieldbase/gimpprotocol.c --- */
/* LIBGIMP - The AmmoOS Image Library
 * Copyright (C) 1995-1997 Peter Mattis and Spencer Kimball
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

#include <gegl.h>
#include <gio/gio.h>
#include <glib-object.h>

#include "gimpbasetypes.h"

#include "gimpchoice.h"
#include "gimpparamspecs.h"
#include "gimpparasite.h"
#include "gimpprotocol.h"
#include "gimpversion-private.h"
#include "gimpwire.h"


static void _gp_quit_read                (GIOChannel       *channel,
                                          GimpWireMessage  *msg,
                                          gpointer          user_data);
static void _gp_quit_write               (GIOChannel       *channel,
                                          GimpWireMessage  *msg,
                                          gpointer          user_data);
static void _gp_quit_destroy             (GimpWireMessage  *msg);

static void _gp_config_read              (GIOChannel       *channel,
                                          GimpWireMessage  *msg,
                                          gpointer          user_data);
static void _gp_config_write             (GIOChannel       *channel,
                                          GimpWireMessage  *msg,
                                          gpointer          user_data);
static void _gp_config_destroy           (GimpWireMessage  *msg);

static void _gp_tile_req_read            (GIOChannel       *channel,
                                          GimpWireMessage  *msg,
                                          gpointer          user_data);
static void _gp_tile_req_write           (GIOChannel       *channel,
                                          GimpWireMessage  *msg,
                                          gpointer          user_data);
static void _gp_tile_req_destroy         (GimpWireMessage  *msg);

static void _gp_tile_ack_read            (GIOChannel       *channel,
                                          GimpWireMessage  *msg,
                                          gpointer          user_data);
static void _gp_tile_ack_write           (GIOChannel       *channel,
                                          GimpWireMessage  *msg,
                                          gpointer          user_data);
static void _gp_tile_ack_destroy         (GimpWireMessage  *msg);

static void _gp_tile_data_read           (GIOChannel       *channel,
                                          GimpWireMessage  *msg,
                                          gpointer          user_data);
static void _gp_tile_data_write          (GIOChannel       *channel,
                                          GimpWireMessage  *msg,
                                          gpointer          user_data);
static void _gp_tile_data_destroy        (GimpWireMessage  *msg);

static void _gp_proc_run_read            (GIOChannel       *channel,
                                          GimpWireMessage  *msg,
                                          gpointer          user_data);
static void _gp_proc_run_write           (GIOChannel       *channel,
                                          GimpWireMessage  *msg,
                                          gpointer          user_data);
static void _gp_proc_run_destroy         (GimpWireMessage  *msg);

static void _gp_proc_return_read         (GIOChannel       *channel,
                                          GimpWireMessage  *msg,
                                          gpointer          user_data);
static void _gp_proc_return_write        (GIOChannel       *channel,
                                          GimpWireMessage  *msg,
                                          gpointer          user_data);
static void _gp_proc_return_destroy      (GimpWireMessage  *msg);

static void _gp_temp_proc_run_read       (GIOChannel       *channel,
                                          GimpWireMessage  *msg,
                                          gpointer          user_data);
static void _gp_temp_proc_run_write      (GIOChannel       *channel,
                                          GimpWireMessage  *msg,
                                          gpointer          user_data);
static void _gp_temp_proc_run_destroy    (GimpWireMessage  *msg);

static void _gp_temp_proc_return_read    (GIOChannel       *channel,
                                          GimpWireMessage  *msg,
                                          gpointer          user_data);
static void _gp_temp_proc_return_write   (GIOChannel       *channel,
                                          GimpWireMessage  *msg,
                                          gpointer          user_data);
static void _gp_temp_proc_return_destroy (GimpWireMessage  *msg);

static void _gp_proc_install_read        (GIOChannel       *channel,
                                          GimpWireMessage  *msg,
                                          gpointer          user_data);
static void _gp_proc_install_write       (GIOChannel       *channel,
                                          GimpWireMessage  *msg,
                                          gpointer          user_data);
static void _gp_proc_install_destroy     (GimpWireMessage  *msg);

static void _gp_proc_uninstall_read      (GIOChannel       *channel,
                                          GimpWireMessage  *msg,
                                          gpointer          user_data);
static void _gp_proc_uninstall_write     (GIOChannel       *channel,
                                          GimpWireMessage  *msg,
                                          gpointer          user_data);
static void _gp_proc_uninstall_destroy   (GimpWireMessage  *msg);

static void _gp_persistent_ack_read      (GIOChannel       *channel,
                                          GimpWireMessage  *msg,
                                          gpointer          user_data);
static void _gp_persistent_ack_write     (GIOChannel       *channel,
                                          GimpWireMessage  *msg,
                                          gpointer          user_data);
static void _gp_persistent_ack_destroy   (GimpWireMessage  *msg);

static void _gp_params_read              (GIOChannel       *channel,
                                          GPParam         **params,
                                          guint            *n_params,
                                          gpointer          user_data);
static void _gp_params_write             (GIOChannel       *channel,
                                          GPParam          *params,
                                          gint              n_params,
                                          gpointer          user_data);
static void _gp_params_destroy           (GPParam          *params,
                                          gint              n_params);


static void _gp_has_init_read            (GIOChannel       *channel,
                                          GimpWireMessage  *msg,
                                          gpointer          user_data);
static void _gp_has_init_write           (GIOChannel       *channel,
                                          GimpWireMessage  *msg,
                                          gpointer          user_data);
static void _gp_has_init_destroy         (GimpWireMessage  *msg);



void
gp_init (void)
{
  gimp_wire_register (GP_QUIT,
                      _gp_quit_read,
                      _gp_quit_write,
                      _gp_quit_destroy);
  gimp_wire_register (GP_CONFIG,
                      _gp_config_read,
                      _gp_config_write,
                      _gp_config_destroy);
  gimp_wire_register (GP_TILE_REQ,
                      _gp_tile_req_read,
                      _gp_tile_req_write,
                      _gp_tile_req_destroy);
  gimp_wire_register (GP_TILE_ACK,
                      _gp_tile_ack_read,
                      _gp_tile_ack_write,
                      _gp_tile_ack_destroy);
  gimp_wire_register (GP_TILE_DATA,
                      _gp_tile_data_read,
                      _gp_tile_data_write,
                      _gp_tile_data_destroy);
  gimp_wire_register (GP_PROC_RUN,
                      _gp_proc_run_read,
                      _gp_proc_run_write,
                      _gp_proc_run_destroy);
  gimp_wire_register (GP_PROC_RETURN,
                      _gp_proc_return_read,
                      _gp_proc_return_write,
                      _gp_proc_return_destroy);
  gimp_wire_register (GP_TEMP_PROC_RUN,
                      _gp_temp_proc_run_read,
                      _gp_temp_proc_run_write,
                      _gp_temp_proc_run_destroy);
  gimp_wire_register (GP_TEMP_PROC_RETURN,
                      _gp_temp_proc_return_read,
                      _gp_temp_proc_return_write,
                      _gp_temp_proc_return_destroy);
  gimp_wire_register (GP_PROC_INSTALL,
                      _gp_proc_install_read,
                      _gp_proc_install_write,
                      _gp_proc_install_destroy);
  gimp_wire_register (GP_PROC_UNINSTALL,
                      _gp_proc_uninstall_read,
                      _gp_proc_uninstall_write,
                      _gp_proc_uninstall_destroy);
  gimp_wire_register (GP_PERSISTENT_ACK,
                      _gp_persistent_ack_read,
                      _gp_persistent_ack_write,
                      _gp_persistent_ack_destroy);
  gimp_wire_register (GP_HAS_INIT,
                      _gp_has_init_read,
                      _gp_has_init_write,
                      _gp_has_init_destroy);
}

/* public writing API */

gboolean
gp_quit_write (GIOChannel *channel,
               gpointer    user_data)
{
  GimpWireMessage msg;

  msg.type = GP_QUIT;
  msg.data = NULL;

  if (! gimp_wire_write_msg (channel, &msg, user_data))
    return FALSE;

  if (! gimp_wire_flush (channel, user_data))
    return FALSE;

  return TRUE;
}

gboolean
gp_config_write (GIOChannel *channel,
                 GPConfig   *config,
                 gpointer    user_data)
{
  GimpWireMessage msg;

  msg.type = GP_CONFIG;
  msg.data = config;

  if (! gimp_wire_write_msg (channel, &msg, user_data))
    return FALSE;

  if (! gimp_wire_flush (channel, user_data))
    return FALSE;

  return TRUE;
}

gboolean
gp_tile_req_write (GIOChannel *channel,
                   GPTileReq  *tile_req,
                   gpointer    user_data)
{
  GimpWireMessage msg;

  msg.type = GP_TILE_REQ;
  msg.data = tile_req;

  if (! gimp_wire_write_msg (channel, &msg, user_data))
    return FALSE;

  if (! gimp_wire_flush (channel, user_data))
    return FALSE;

  return TRUE;
}

gboolean
gp_tile_ack_write (GIOChannel *channel,
                   gpointer    user_data)
{
  GimpWireMessage msg;

  msg.type = GP_TILE_ACK;
  msg.data = NULL;

  if (! gimp_wire_write_msg (channel, &msg, user_data))
    return FALSE;

  if (! gimp_wire_flush (channel, user_data))
    return FALSE;

  return TRUE;
}

gboolean
gp_tile_data_write (GIOChannel *channel,
                    GPTileData *tile_data,
                    gpointer    user_data)
{
  GimpWireMessage msg;

  msg.type = GP_TILE_DATA;
  msg.data = tile_data;

  if (! gimp_wire_write_msg (channel, &msg, user_data))
    return FALSE;

  if (! gimp_wire_flush (channel, user_data))
    return FALSE;

  return TRUE;
}

gboolean
gp_proc_run_write (GIOChannel *channel,
                   GPProcRun  *proc_run,
                   gpointer    user_data)
{
  GimpWireMessage msg;

  msg.type = GP_PROC_RUN;
  msg.data = proc_run;

  if (! gimp_wire_write_msg (channel, &msg, user_data))
    return FALSE;

  if (! gimp_wire_flush (channel, user_data))
    return FALSE;

  return TRUE;
}

gboolean
gp_proc_return_write (GIOChannel   *channel,
                      GPProcReturn *proc_return,
                      gpointer      user_data)
{
  GimpWireMessage msg;

  msg.type = GP_PROC_RETURN;
  msg.data = proc_return;

  if (! gimp_wire_write_msg (channel, &msg, user_data))
    return FALSE;

  if (! gimp_wire_flush (channel, user_data))
    return FALSE;

  return TRUE;
}

gboolean
gp_temp_proc_run_write (GIOChannel *channel,
                        GPProcRun  *proc_run,
                        gpointer    user_data)
{
  GimpWireMessage msg;

  msg.type = GP_TEMP_PROC_RUN;
  msg.data = proc_run;

  if (! gimp_wire_write_msg (channel, &msg, user_data))
    return FALSE;

  if (! gimp_wire_flush (channel, user_data))
    return FALSE;

  return TRUE;
}

gboolean
gp_temp_proc_return_write (GIOChannel   *channel,
                           GPProcReturn *proc_return,
                           gpointer      user_data)
{
  GimpWireMessage msg;

  msg.type = GP_TEMP_PROC_RETURN;
  msg.data = proc_return;

  if (! gimp_wire_write_msg (channel, &msg, user_data))
    return FALSE;

  if (! gimp_wire_flush (channel, user_data))
    return FALSE;

  return TRUE;
}

gboolean
gp_proc_install_write (GIOChannel    *channel,
                       GPProcInstall *proc_install,
                       gpointer       user_data)
{
  GimpWireMessage msg;

  msg.type = GP_PROC_INSTALL;
  msg.data = proc_install;

  if (! gimp_wire_write_msg (channel, &msg, user_data))
    return FALSE;

  if (! gimp_wire_flush (channel, user_data))
    return FALSE;

  return TRUE;
}

gboolean
gp_proc_uninstall_write (GIOChannel      *channel,
                         GPProcUninstall *proc_uninstall,
                         gpointer         user_data)
{
  GimpWireMessage msg;

  msg.type = GP_PROC_UNINSTALL;
  msg.data = proc_uninstall;

  if (! gimp_wire_write_msg (channel, &msg, user_data))
    return FALSE;

  if (! gimp_wire_flush (channel, user_data))
    return FALSE;

  return TRUE;
}

gboolean
gp_extension_ack_write (GIOChannel *channel,
                        gpointer    user_data)
{
  return gp_persistent_ack_write (channel, user_data);
}

gboolean
gp_persistent_ack_write (GIOChannel *channel,
                         gpointer    user_data)
{
  GimpWireMessage msg;

  msg.type = GP_PERSISTENT_ACK;
  msg.data = NULL;

  if (! gimp_wire_write_msg (channel, &msg, user_data))
    return FALSE;

  if (! gimp_wire_flush (channel, user_data))
    return FALSE;

  return TRUE;
}

gboolean
gp_has_init_write (GIOChannel *channel,
                   gpointer    user_data)
{
  GimpWireMessage msg;

  msg.type = GP_HAS_INIT;
  msg.data = NULL;

  if (! gimp_wire_write_msg (channel, &msg, user_data))
    return FALSE;

  if (! gimp_wire_flush (channel, user_data))
    return FALSE;

  return TRUE;
}

/*  quit  */

static void
_gp_quit_read (GIOChannel      *channel,
               GimpWireMessage *msg,
               gpointer         user_data)
{
}

static void
_gp_quit_write (GIOChannel      *channel,
                GimpWireMessage *msg,
                gpointer         user_data)
{
}

static void
_gp_quit_destroy (GimpWireMessage *msg)
{
}

/*  config  */

static void
_gp_config_read (GIOChannel      *channel,
                 GimpWireMessage *msg,
                 gpointer         user_data)
{
  GPConfig *config = g_slice_new0 (GPConfig);

  if (! _gimp_wire_read_int32 (channel,
                               &config->tile_width, 1, user_data))
    goto cleanup;
  if (! _gimp_wire_read_int32 (channel,
                               &config->tile_height, 1, user_data))
    goto cleanup;
  if (! _gimp_wire_read_int32 (channel,
                               (guint32 *) &config->shm_id, 1, user_data))
    goto cleanup;
  if (! _gimp_wire_read_int8 (channel,
                              (guint8 *) &config->check_size, 1, user_data))
    goto cleanup;
  if (! _gimp_wire_read_int8 (channel,
                              (guint8 *) &config->check_type, 1, user_data))
    goto cleanup;
  if (! _gimp_wire_read_gegl_color (channel,
                                    &config->check_custom_color1,
                                    &config->check_custom_icc1,
                                    &config->check_custom_encoding1,
                                    1, user_data))
    goto cleanup;
  if (! _gimp_wire_read_gegl_color (channel,
                                    &config->check_custom_color2,
                                    &config->check_custom_icc2,
                                    &config->check_custom_encoding2,
                                    1, user_data))
    goto cleanup;
  if (! _gimp_wire_read_int8 (channel,
                              (guint8 *) &config->show_help_button, 1,
                              user_data))
    goto cleanup;
  if (! _gimp_wire_read_int8 (channel,
                              (guint8 *) &config->use_cpu_accel, 1,
                              user_data))
    goto cleanup;
  if (! _gimp_wire_read_int8 (channel,
                              (guint8 *) &config->use_opencl, 1,
                              user_data))
    goto cleanup;
  if (! _gimp_wire_read_int8 (channel,
                              (guint8 *) &config->export_color_profile, 1,
                              user_data))
    goto cleanup;
  if (! _gimp_wire_read_int8 (channel,
                              (guint8 *) &config->export_comment, 1,
                              user_data))
    goto cleanup;
  if (! _gimp_wire_read_int8 (channel,
                              (guint8 *) &config->export_exif, 1,
                              user_data))
    goto cleanup;
  if (! _gimp_wire_read_int8 (channel,
                              (guint8 *) &config->export_xmp, 1,
                              user_data))
    goto cleanup;
  if (! _gimp_wire_read_int8 (channel,
                              (guint8 *) &config->export_iptc, 1,
                              user_data))
    goto cleanup;
  if (! _gimp_wire_read_int8 (channel,
                              (guint8 *) &config->update_metadata, 1,
                              user_data))
    goto cleanup;
  if (! _gimp_wire_read_int32 (channel,
                               (guint32 *) &config->default_display_id, 1,
                               user_data))
    goto cleanup;

  if (! _gimp_wire_read_string (channel,
                                &config->app_name, 1, user_data))
    goto cleanup;
  if (! _gimp_wire_read_string (channel,
                                &config->wm_class, 1, user_data))
    goto cleanup;
  if (! _gimp_wire_read_string (channel,
                                &config->display_name, 1, user_data))
    goto cleanup;
  if (! _gimp_wire_read_int32 (channel,
                               (guint32 *) &config->monitor_number, 1,
                               user_data))
    goto cleanup;
  if (! _gimp_wire_read_int32 (channel,
                               &config->timestamp, 1, user_data))
    goto cleanup;
  if (! _gimp_wire_read_string (channel,
                                &config->icon_theme_dir, 1, user_data))
    goto cleanup;
  if (! _gimp_wire_read_int64 (channel,
                               &config->tile_cache_size, 1, user_data))
    goto cleanup;
  if (! _gimp_wire_read_string (channel,
                                &config->swap_path, 1, user_data))
    goto cleanup;
  if (! _gimp_wire_read_string (channel,
                                &config->swap_compression, 1, user_data))
    goto cleanup;
  if (! _gimp_wire_read_int32 (channel,
                               (guint32 *) &config->num_processors, 1,
                               user_data))
    goto cleanup;

  msg->data = config;
  return;

 cleanup:
  g_bytes_unref (config->check_custom_color1);
  g_bytes_unref (config->check_custom_icc1);
  g_free (config->check_custom_encoding1);
  g_bytes_unref (config->check_custom_color2);
  g_bytes_unref (config->check_custom_icc2);
  g_free (config->check_custom_encoding2);

  g_free (config->app_name);
  g_free (config->wm_class);
  g_free (config->display_name);
  g_free (config->icon_theme_dir);
  g_free (config->swap_path);
  g_free (config->swap_compression);
  g_slice_free (GPConfig, config);
}

static void
_gp_config_write (GIOChannel      *channel,
                  GimpWireMessage *msg,
                  gpointer         user_data)
{
  GPConfig *config = msg->data;

  if (! _gimp_wire_write_int32 (channel,
                                &config->tile_width, 1, user_data))
    return;
  if (! _gimp_wire_write_int32 (channel,
                                &config->tile_height, 1, user_data))
    return;
  if (! _gimp_wire_write_int32 (channel,
                                (const guint32 *) &config->shm_id, 1,
                                user_data))
    return;
  if (! _gimp_wire_write_int8 (channel,
                               (const guint8 *) &config->check_size, 1,
                               user_data))
    return;
  if (! _gimp_wire_write_int8 (channel,
                               (const guint8 *) &config->check_type, 1,
                               user_data))
    return;
  if (! _gimp_wire_write_gegl_color (channel,
                                     &config->check_custom_color1,
                                     &config->check_custom_icc1,
                                     &config->check_custom_encoding1,
                                     1, user_data))
    return;
  if (! _gimp_wire_write_gegl_color (channel,
                                     &config->check_custom_color2,
                                     &config->check_custom_icc2,
                                     &config->check_custom_encoding2,
                                     1, user_data))
    return;
  if (! _gimp_wire_write_int8 (channel,
                               (const guint8 *) &config->show_help_button, 1,
                               user_data))
    return;
  if (! _gimp_wire_write_int8 (channel,
                               (const guint8 *) &config->use_cpu_accel, 1,
                               user_data))
    return;
  if (! _gimp_wire_write_int8 (channel,
                               (const guint8 *) &config->use_opencl, 1,
                               user_data))
    return;
  if (! _gimp_wire_write_int8 (channel,
                               (const guint8 *) &config->export_color_profile, 1,
                               user_data))
    return;
  if (! _gimp_wire_write_int8 (channel,
                               (const guint8 *) &config->export_comment, 1,
                               user_data))
    return;
  if (! _gimp_wire_write_int8 (channel,
                               (const guint8 *) &config->export_exif, 1,
                               user_data))
    return;
  if (! _gimp_wire_write_int8 (channel,
                               (const guint8 *) &config->export_xmp, 1,
                               user_data))
    return;
  if (! _gimp_wire_write_int8 (channel,
                               (const guint8 *) &config->export_iptc, 1,
                               user_data))
    return;
  if (! _gimp_wire_write_int8 (channel,
                               (const guint8 *) &config->update_metadata, 1,
                               user_data))
    return;
  if (! _gimp_wire_write_int32 (channel,
                                (const guint32 *) &config->default_display_id, 1,
                                user_data))
    return;
  if (! _gimp_wire_write_string (channel,
                                 &config->app_name, 1, user_data))
    return;
  if (! _gimp_wire_write_string (channel,
                                 &config->wm_class, 1, user_data))
    return;
  if (! _gimp_wire_write_string (channel,
                                 &config->display_name, 1, user_data))
    return;
  if (! _gimp_wire_write_int32 (channel,
                                (const guint32 *) &config->monitor_number, 1,
                                user_data))
    return;
  if (! _gimp_wire_write_int32 (channel,
                                (const guint32 *) &config->timestamp, 1,
                                user_data))
    return;
  if (! _gimp_wire_write_string (channel,
                                 &config->icon_theme_dir, 1, user_data))
    return;
  if (! _gimp_wire_write_int64 (channel,
                                &config->tile_cache_size, 1, user_data))
    return;
  if (! _gimp_wire_write_string (channel,
                                 &config->swap_path, 1, user_data))
    return;
  if (! _gimp_wire_write_string (channel,
                                 &config->swap_compression, 1, user_data))
    return;
  if (! _gimp_wire_write_int32 (channel,
                                (const guint32 *) &config->num_processors, 1,
                                user_data))
    return;
}

static void
_gp_config_destroy (GimpWireMessage *msg)
{
  GPConfig *config = msg->data;

  if (config)
    {
      g_bytes_unref (config->check_custom_color1);
      g_bytes_unref (config->check_custom_icc1);
      g_free (config->check_custom_encoding1);
      g_bytes_unref (config->check_custom_color2);
      g_bytes_unref (config->check_custom_icc2);
      g_free (config->check_custom_encoding2);

      g_free (config->app_name);
      g_free (config->wm_class);
      g_free (config->display_name);
      g_free (config->icon_theme_dir);
      g_free (config->swap_path);
      g_free (config->swap_compression);
      g_slice_free (GPConfig, config);
    }
}

/*  tile_req  */

static void
_gp_tile_req_read (GIOChannel      *channel,
                   GimpWireMessage *msg,
                   gpointer         user_data)
{
  GPTileReq *tile_req = g_slice_new0 (GPTileReq);

  if (! _gimp_wire_read_int32 (channel,
                               (guint32 *) &tile_req->drawable_id, 1,
                               user_data))
    goto cleanup;
  if (! _gimp_wire_read_int32 (channel,
                               &tile_req->tile_num, 1, user_data))
    goto cleanup;
  if (! _gimp_wire_read_int32 (channel,
                               &tile_req->shadow, 1, user_data))
    goto cleanup;

  msg->data = tile_req;
  return;

 cleanup:
  g_slice_free (GPTileReq, tile_req);
  msg->data = NULL;
}

static void
_gp_tile_req_write (GIOChannel      *channel,
                    GimpWireMessage *msg,
                    gpointer         user_data)
{
  GPTileReq *tile_req = msg->data;

  if (! _gimp_wire_write_int32 (channel,
                                (const guint32 *) &tile_req->drawable_id, 1,
                                user_data))
    return;
  if (! _gimp_wire_write_int32 (channel,
                                &tile_req->tile_num, 1, user_data))
    return;
  if (! _gimp_wire_write_int32 (channel,
                                &tile_req->shadow, 1, user_data))
    return;
}

static void
_gp_tile_req_destroy (GimpWireMessage *msg)
{
  GPTileReq *tile_req = msg->data;

  if (tile_req)
    g_slice_free (GPTileReq, msg->data);
}

/*  tile_ack  */

static void
_gp_tile_ack_read (GIOChannel      *channel,
                   GimpWireMessage *msg,
                   gpointer         user_data)
{
}

static void
_gp_tile_ack_write (GIOChannel      *channel,
                    GimpWireMessage *msg,
                    gpointer         user_data)
{
}

static void
_gp_tile_ack_destroy (GimpWireMessage *msg)
{
}

/*  tile_data  */

static void
_gp_tile_data_read (GIOChannel      *channel,
                    GimpWireMessage *msg,
                    gpointer         user_data)
{
  GPTileData *tile_data = g_slice_new0 (GPTileData);

  if (! _gimp_wire_read_int32 (channel,
                               (guint32 *) &tile_data->drawable_id, 1,
                               user_data))
    goto cleanup;
  if (! _gimp_wire_read_int32 (channel,
                               &tile_data->tile_num, 1, user_data))
    goto cleanup;
  if (! _gimp_wire_read_int32 (channel,
                               &tile_data->shadow, 1, user_data))
    goto cleanup;
  if (! _gimp_wire_read_int32 (channel,
                               &tile_data->bpp, 1, user_data))
    goto cleanup;
  if (! _gimp_wire_read_int32 (channel,
                               &tile_data->width, 1, user_data))
    goto cleanup;
  if (! _gimp_wire_read_int32 (channel,
                               &tile_data->height, 1, user_data))
    goto cleanup;
  if (! _gimp_wire_read_int32 (channel,
                               &tile_data->use_shm, 1, user_data))
    goto cleanup;

  if (!tile_data->use_shm)
    {
      guint length = tile_data->width * tile_data->height * tile_data->bpp;

      tile_data->data = g_new (guchar, length);

      if (! _gimp_wire_read_int8 (channel,
                                  (guint8 *) tile_data->data, length,
                                  user_data))
        goto cleanup;
    }

  msg->data = tile_data;
  return;

 cleanup:
  g_free (tile_data->data);
  g_slice_free (GPTileData, tile_data);
  msg->data = NULL;
}

static void
_gp_tile_data_write (GIOChannel      *channel,
                     GimpWireMessage *msg,
                     gpointer         user_data)
{
  GPTileData *tile_data = msg->data;

  if (! _gimp_wire_write_int32 (channel,
                                (const guint32 *) &tile_data->drawable_id, 1,
                                user_data))
    return;
  if (! _gimp_wire_write_int32 (channel,
                                &tile_data->tile_num, 1, user_data))
    return;
  if (! _gimp_wire_write_int32 (channel,
                                &tile_data->shadow, 1, user_data))
    return;
  if (! _gimp_wire_write_int32 (channel,
                                &tile_data->bpp, 1, user_data))
    return;
  if (! _gimp_wire_write_int32 (channel,
                                &tile_data->width, 1, user_data))
    return;
  if (! _gimp_wire_write_int32 (channel,
                                &tile_data->height, 1, user_data))
    return;
  if (! _gimp_wire_write_int32 (channel,
                                &tile_data->use_shm, 1, user_data))
    return;

  if (!tile_data->use_shm)
    {
      guint length = tile_data->width * tile_data->height * tile_data->bpp;

      if (! _gimp_wire_write_int8 (channel,
                                   (const guint8 *) tile_data->data, length,
                                   user_data))
        return;
    }
}

static void
_gp_tile_data_destroy (GimpWireMessage *msg)
{
  GPTileData *tile_data = msg->data;

  if  (tile_data)
    {
      if (tile_data->data)
        {
          g_free (tile_data->data);
          tile_data->data = NULL;
        }

      g_slice_free (GPTileData, tile_data);
    }
}

/*  proc_run  */

static void
_gp_proc_run_read (GIOChannel      *channel,
                   GimpWireMessage *msg,
                   gpointer         user_data)
{
  GPProcRun *proc_run = g_slice_new0 (GPProcRun);

  if (! _gimp_wire_read_string (channel, &proc_run->name, 1, user_data))
    goto cleanup;

  _gp_params_read (channel,
                   &proc_run->params, (guint *) &proc_run->n_params,
                   user_data);

  msg->data = proc_run;
  return;

 cleanup:
  g_slice_free (GPProcRun, proc_run);
  msg->data = NULL;
}

static void
_gp_proc_run_write (GIOChannel      *channel,
                    GimpWireMessage *msg,
                    gpointer         user_data)
{
  GPProcRun *proc_run = msg->data;

  if (! _gimp_wire_write_string (channel, &proc_run->name, 1, user_data))
    return;

  _gp_params_write (channel, proc_run->params, proc_run->n_params, user_data);
}

static void
_gp_proc_run_destroy (GimpWireMessage *msg)
{
  GPProcRun *proc_run = msg->data;

  if (proc_run)
    {
      _gp_params_destroy (proc_run->params, proc_run->n_params);

      g_free (proc_run->name);
      g_slice_free (GPProcRun, proc_run);
    }
}

/*  proc_return  */

static void
_gp_proc_return_read (GIOChannel      *channel,
                      GimpWireMessage *msg,
                      gpointer         user_data)
{
  GPProcReturn *proc_return = g_slice_new0 (GPProcReturn);

  if (! _gimp_wire_read_string (channel, &proc_return->name, 1, user_data))
    goto cleanup;

  _gp_params_read (channel,
                   &proc_return->params, (guint *) &proc_return->n_params,
                   user_data);

  msg->data = proc_return;
  return;

 cleanup:
  g_slice_free (GPProcReturn, proc_return);
  msg->data = NULL;
}

static void
_gp_proc_return_write (GIOChannel      *channel,
                       GimpWireMessage *msg,
                       gpointer         user_data)
{
  GPProcReturn *proc_return = msg->data;

  if (! _gimp_wire_write_string (channel, &proc_return->name, 1, user_data))
    return;

  _gp_params_write (channel,
                    proc_return->params, proc_return->n_params, user_data);
}

static void
_gp_proc_return_destroy (GimpWireMessage *msg)
{
  GPProcReturn *proc_return = msg->data;

  if (proc_return)
    {
      _gp_params_destroy (proc_return->params, proc_return->n_params);

      g_free (proc_return->name);
      g_slice_free (GPProcReturn, proc_return);
    }
}

/*  temp_proc_run  */

static void
_gp_temp_proc_run_read (GIOChannel      *channel,
                        GimpWireMessage *msg,
                        gpointer         user_data)
{
  _gp_proc_run_read (channel, msg, user_data);
}

static void
_gp_temp_proc_run_write (GIOChannel      *channel,
                         GimpWireMessage *msg,
                         gpointer         user_data)
{
  _gp_proc_run_write (channel, msg, user_data);
}

static void
_gp_temp_proc_run_destroy (GimpWireMessage *msg)
{
  _gp_proc_run_destroy (msg);
}

/*  temp_proc_return  */

static void
_gp_temp_proc_return_read (GIOChannel      *channel,
                           GimpWireMessage *msg,
                           gpointer         user_data)
{
  _gp_proc_return_read (channel, msg, user_data);
}

static void
_gp_temp_proc_return_write (GIOChannel      *channel,
                            GimpWireMessage *msg,
                            gpointer         user_data)
{
  _gp_proc_return_write (channel, msg, user_data);
}

static void
_gp_temp_proc_return_destroy (GimpWireMessage *msg)
{
  _gp_proc_return_destroy (msg);
}

/*  proc_install  */

static gboolean
_gp_param_def_read (GIOChannel *channel,
                    GPParamDef *param_def,
                    gpointer    user_data)
{
  if (! _gimp_wire_read_int32 (channel,
                               (guint32 *) &param_def->param_def_type, 1,
                               user_data))
    return FALSE;

  if (! _gimp_wire_read_string (channel,
                                &param_def->type_name, 1,
                                user_data))
    return FALSE;

  if (! _gimp_wire_read_string (channel,
                                &param_def->value_type_name, 1,
                                user_data))
    return FALSE;

  if (! _gimp_wire_read_string (channel,
                                &param_def->name, 1,
                                user_data))
    return FALSE;

  if (! _gimp_wire_read_string (channel,
                                &param_def->nick, 1,
                                user_data))
    return FALSE;

  if (! _gimp_wire_read_string (channel,
                                &param_def->blurb, 1,
                                user_data))
    return FALSE;

  if (! _gimp_wire_read_int32 (channel,
                               &param_def->flags, 1,
                               user_data))
    return FALSE;

  switch (param_def->param_def_type)
    {
    case GP_PARAM_DEF_TYPE_DEFAULT:
    case GP_PARAM_DEF_TYPE_EXPORT_OPTIONS:
      break;

    case GP_PARAM_DEF_TYPE_INT:
      if (! _gimp_wire_read_int64 (channel,
                                   (guint64 *) &param_def->meta.m_int.min_val, 1,
                                   user_data) ||
          ! _gimp_wire_read_int64 (channel,
                                   (guint64 *) &param_def->meta.m_int.max_val, 1,
                                   user_data) ||
          ! _gimp_wire_read_int64 (channel,
                                   (guint64 *) &param_def->meta.m_int.default_val, 1,
                                   user_data))
        return FALSE;
      break;

    case GP_PARAM_DEF_TYPE_CHOICE:
        {
          GimpChoice *choice;
          guint32     size;
          gchar      *nick;

          if (! _gimp_wire_read_string (channel, &nick, (int) 1, user_data))
            return FALSE;

          param_def->meta.m_choice.default_val = g_strdup (nick);

          if (! _gimp_wire_read_int32 (channel, &size, 1, user_data))
            return FALSE;

          choice = gimp_choice_new ();

          for (gint i = 0; i < size; i++)
            {
              gchar    *label    = NULL;
              gchar    *help     = NULL;
              gchar    *redirect = NULL;
              gchar    *reason   = NULL;
              gint      id;
              gboolean  is_deprecated;

              if (! _gimp_wire_read_string (channel, &nick,
                                           (int) 1, user_data)  ||
                  ! _gimp_wire_read_int32 (channel, (guint32 *) &id,
                                           1, user_data)        ||
                  ! _gimp_wire_read_string (channel, &label,
                                            (int) 1, user_data) ||
                  ! _gimp_wire_read_string (channel, &help,
                                            (int) 1, user_data) ||
                  ! _gimp_wire_read_int32 (channel, (guint32 *) &is_deprecated,
                                           1, user_data)        ||
                  ! _gimp_wire_read_string (channel, &redirect,
                                            (int) 1, user_data) ||
                  ! _gimp_wire_read_string (channel, &reason,
                                            (int) 1, user_data))
                {
                  g_object_unref (choice);
                  g_free (redirect);
                  return FALSE;
                }

              if (! is_deprecated)
                gimp_choice_add (choice, nick, id, label, help);
              else
                gimp_choice_add_deprecated (choice, nick, id, redirect, reason);

              g_free (label);
              g_free (help);
              g_free (redirect);
              g_free (reason);
            }
          param_def->meta.m_choice.choice = choice;
        }
      break;

    case GP_PARAM_DEF_TYPE_UNIT:
      if (! _gimp_wire_read_int32 (channel,
                                   (guint32 *) &param_def->meta.m_unit.allow_pixels, 1,
                                   user_data) ||
          ! _gimp_wire_read_int32 (channel,
                                   (guint32 *) &param_def->meta.m_unit.allow_percent, 1,
                                   user_data) ||
          ! _gimp_wire_read_int32 (channel,
                                   (guint32 *) &param_def->meta.m_unit.default_val, 1,
                                   user_data))
        return FALSE;
      break;

    case GP_PARAM_DEF_TYPE_ENUM:
      if (! _gimp_wire_read_int32 (channel,
                                   (guint32 *) &param_def->meta.m_enum.default_val, 1,
                                   user_data))
        return FALSE;
      break;

    case GP_PARAM_DEF_TYPE_BOOLEAN:
      if (! _gimp_wire_read_int32 (channel,
                                   (guint32 *) &param_def->meta.m_boolean.default_val, 1,
                                   user_data))
        return FALSE;
      break;

    case GP_PARAM_DEF_TYPE_DOUBLE:
      if (! _gimp_wire_read_double (channel,
                                    &param_def->meta.m_double.min_val, 1,
                                    user_data) ||
          ! _gimp_wire_read_double (channel,
                                    &param_def->meta.m_double.max_val, 1,
                                    user_data) ||
          ! _gimp_wire_read_double (channel,
                                    &param_def->meta.m_double.default_val, 1,
                                    user_data))
        return FALSE;
      break;

    case GP_PARAM_DEF_TYPE_STRING:
      if (! _gimp_wire_read_string (channel,
                                    &param_def->meta.m_string.default_val, 1,
                                    user_data))
        return FALSE;
      break;

    case GP_PARAM_DEF_TYPE_GEGL_COLOR:
        {
          GPParamColor *default_val = NULL;
          GBytes       *pixel_data = NULL;
          GBytes       *icc_data   = NULL;
          gchar        *encoding   = NULL;

          if (! _gimp_wire_read_int32 (channel,
                                       (guint32 *) &param_def->meta.m_gegl_color.has_alpha, 1,
                                       user_data) ||
              ! _gimp_wire_read_gegl_color (channel, &pixel_data, &icc_data, &encoding,
                                            1, user_data))
            return FALSE;

          if (pixel_data != NULL)
            {
              default_val = g_new0 (GPParamColor, 1);

              default_val->format.encoding = encoding;
              default_val->size            = g_bytes_get_size (pixel_data);
              if (default_val->size > 40)
                {
                  g_free (default_val);
                  g_free (encoding);
                  g_bytes_unref (pixel_data);
                  g_bytes_unref (icc_data);
                  return FALSE;
                }
              memcpy (default_val->data, g_bytes_get_data (pixel_data, NULL),
                      default_val->size);
              g_bytes_unref (pixel_data);
              if (icc_data)
                {
                  gsize profile_size;

                  default_val->format.profile_data = g_bytes_unref_to_data (icc_data, &profile_size);
                  default_val->format.profile_size = (guint32) profile_size;
                }
              else
                {
                  default_val->format.profile_data = NULL;
                  default_val->format.profile_size = 0;
                }
            }
          param_def->meta.m_gegl_color.default_val = default_val;
        }
      break;

    case GP_PARAM_DEF_TYPE_ID:
      if (! _gimp_wire_read_int32 (channel,
                                   (guint32 *) &param_def->meta.m_id.none_ok, 1,
                                   user_data))
        return FALSE;
      break;

    case GP_PARAM_DEF_TYPE_ID_ARRAY:
      if (! _gimp_wire_read_string (channel,
                                    &param_def->meta.m_id_array.type_name, 1,
                                    user_data))
        return FALSE;
      break;

    case GP_PARAM_DEF_TYPE_RESOURCE:
      if (! _gimp_wire_read_int32 (channel,
                                   (guint32 *) &param_def->meta.m_resource.none_ok, 1,
                                   user_data))
        return FALSE;
      if (! _gimp_wire_read_int32 (channel,
                                   (guint32 *) &param_def->meta.m_resource.default_to_context, 1,
                                   user_data))
        return FALSE;
      if (! _gimp_wire_read_int32 (channel,
                                   (guint32 *) &param_def->meta.m_resource.default_resource_id, 1,
                                   user_data))
        return FALSE;
      break;

    case GP_PARAM_DEF_TYPE_FILE:
      if (! _gimp_wire_read_int32 (channel,
                                   (guint32 *) &param_def->meta.m_file.action, 1,
                                   user_data))
        return FALSE;
      if (! _gimp_wire_read_int32 (channel,
                                   (guint32 *) &param_def->meta.m_file.none_ok, 1,
                                   user_data))
        return FALSE;
      if (! _gimp_wire_read_string (channel,
                                    &param_def->meta.m_file.default_uri, 1,
                                    user_data))
        return FALSE;
      break;

    case GP_PARAM_DEF_TYPE_CURVE:
      if (! _gimp_wire_read_int32 (channel,
                                   (guint32 *) &param_def->meta.m_curve.none_ok, 1,
                                   user_data))
        return FALSE;
      break;
    }

  return TRUE;
}

static void
_gp_param_def_destroy (GPParamDef *param_def)
{
  g_free (param_def->type_name);
  g_free (param_def->value_type_name);
  g_free (param_def->name);
  g_free (param_def->nick);
  g_free (param_def->blurb);

  switch (param_def->param_def_type)
    {
    case GP_PARAM_DEF_TYPE_DEFAULT:
    case GP_PARAM_DEF_TYPE_INT:
    case GP_PARAM_DEF_TYPE_UNIT:
    case GP_PARAM_DEF_TYPE_ENUM:
      break;

    case GP_PARAM_DEF_TYPE_BOOLEAN:
    case GP_PARAM_DEF_TYPE_DOUBLE:
      break;

    case GP_PARAM_DEF_TYPE_CHOICE:
      g_free (param_def->meta.m_choice.default_val);
      g_object_unref (param_def->meta.m_choice.choice);
      break;

    case GP_PARAM_DEF_TYPE_STRING:
      g_free (param_def->meta.m_string.default_val);
      break;

    case GP_PARAM_DEF_TYPE_GEGL_COLOR:
      if (param_def->meta.m_gegl_color.default_val)
        {
          g_free (param_def->meta.m_gegl_color.default_val->format.encoding);
          g_free (param_def->meta.m_gegl_color.default_val->format.profile_data);
        }
      g_free (param_def->meta.m_gegl_color.default_val);
      break;

    case GP_PARAM_DEF_TYPE_ID:
      break;

    case GP_PARAM_DEF_TYPE_ID_ARRAY:
      g_free (param_def->meta.m_id_array.type_name);
      break;

    case GP_PARAM_DEF_TYPE_EXPORT_OPTIONS:
      break;

    case GP_PARAM_DEF_TYPE_RESOURCE:
      break;

    case GP_PARAM_DEF_TYPE_FILE:
      g_free (param_def->meta.m_file.default_uri);
      break;

    case GP_PARAM_DEF_TYPE_CURVE:
      break;
    }
}

static void
_gp_proc_install_read (GIOChannel      *channel,
                       GimpWireMessage *msg,
                       gpointer         user_data)
{
  GPProcInstall *proc_install = g_slice_new0 (GPProcInstall);
  gint           i;

  if (! _gimp_wire_read_string (channel,
                                &proc_install->name, 1, user_data)    ||
      ! _gimp_wire_read_int32 (channel,
                               &proc_install->type, 1, user_data)     ||
      ! _gimp_wire_read_int32 (channel,
                               &proc_install->n_params, 1, user_data) ||
      ! _gimp_wire_read_int32 (channel,
                               &proc_install->n_return_vals, 1, user_data))
    goto cleanup;

  proc_install->params = g_new0 (GPParamDef, proc_install->n_params);

  for (i = 0; i < proc_install->n_params; i++)
    {
      if (! _gp_param_def_read (channel,
                                &proc_install->params[i],
                                user_data))
        goto cleanup;
    }

  proc_install->return_vals = g_new0 (GPParamDef, proc_install->n_return_vals);

  for (i = 0; i < proc_install->n_return_vals; i++)
    {
      if (! _gp_param_def_read (channel,
                                &proc_install->return_vals[i],
                                user_data))
        goto cleanup;
    }

  msg->data = proc_install;
  return;

 cleanup:
  g_free (proc_install->name);

  if (proc_install->params)
    {
      for (i = 0; i < proc_install->n_params; i++)
        {
          if (! proc_install->params[i].name)
            break;

          _gp_param_def_destroy (&proc_install->params[i]);
        }

      g_free (proc_install->params);
    }

  if (proc_install->return_vals)
    {
      for (i = 0; i < proc_install->n_return_vals; i++)
        {
          if (! proc_install->return_vals[i].name)
            break;

          _gp_param_def_destroy (&proc_install->return_vals[i]);
        }

      g_free (proc_install->return_vals);
    }

  g_slice_free (GPProcInstall, proc_install);
  msg->data = NULL;
}

static gboolean
_gp_param_def_write (GIOChannel *channel,
                     GPParamDef *param_def,
                     gpointer    user_data)
{
  if (! _gimp_wire_write_int32 (channel,
                                (const guint32 *) &param_def->param_def_type, 1,
                                user_data))
    return FALSE;

  if (! _gimp_wire_write_string (channel,
                                 &param_def->type_name, 1,
                                 user_data))
    return FALSE;

  if (! _gimp_wire_write_string (channel,
                                 &param_def->value_type_name, 1,
                                 user_data))
    return FALSE;

  if (! _gimp_wire_write_string (channel,
                                 &param_def->name, 1,
                                 user_data))
    return FALSE;

  if (! _gimp_wire_write_string (channel,
                                 &param_def->nick, 1,
                                 user_data))
    return FALSE;

  if (! _gimp_wire_write_string (channel,
                                 &param_def->blurb, 1,
                                 user_data))
    return FALSE;

  if (! _gimp_wire_write_int32 (channel,
                                &param_def->flags, 1,
                                user_data))
    return FALSE;

  switch (param_def->param_def_type)
    {
    case GP_PARAM_DEF_TYPE_DEFAULT:
    case GP_PARAM_DEF_TYPE_EXPORT_OPTIONS:
      break;

    case GP_PARAM_DEF_TYPE_INT:
      if (! _gimp_wire_write_int64 (channel,
                                    (guint64 *) &param_def->meta.m_int.min_val, 1,
                                    user_data) ||
          ! _gimp_wire_write_int64 (channel,
                                    (guint64 *) &param_def->meta.m_int.max_val, 1,
                                    user_data) ||
          ! _gimp_wire_write_int64 (channel,
                                    (guint64 *) &param_def->meta.m_int.default_val, 1,
                                    user_data))
        return FALSE;
      break;

    case GP_PARAM_DEF_TYPE_CHOICE:
        {
          GList *values;
          gint   size;

          if (! _gimp_wire_write_string (channel,
                                         &param_def->meta.m_choice.default_val,
                                         1, user_data))
            return FALSE;

          values = gimp_choice_list_nicks (param_def->meta.m_choice.choice);
          size   = g_list_length (values);

          if (! _gimp_wire_write_int32 (channel,
                                        (guint32 *) &size, 1,
                                        user_data))
            return FALSE;

          for (GList *iter = values; iter; iter = iter->next)
            {
              const gchar *label;
              const gchar *help;
              const gchar *redirect;
              const gchar *reason;
              gint         id;
              gboolean     is_deprecated;

              gimp_choice_get_documentation (param_def->meta.m_choice.choice,
                                             iter->data, &label, &help);
              is_deprecated =
                gimp_choice_is_deprecated (param_def->meta.m_choice.choice,
                                           iter->data, &redirect, &reason);

              id = gimp_choice_get_id (param_def->meta.m_choice.choice,
                                       iter->data);
              if (! _gimp_wire_write_string (channel,
                                             (gchar **) &iter->data,
                                             1, user_data)  ||
                  ! _gimp_wire_write_int32 (channel,
                                            (guint32 *) &id, 1,
                                            user_data)      ||
                  ! _gimp_wire_write_string (channel,
                                             (gchar **) &label,
                                             1, user_data)  ||
                  ! _gimp_wire_write_string (channel,
                                             (gchar **) &help,
                                             1, user_data)  ||
                  ! _gimp_wire_write_int32 (channel,
                                            (guint32 *) &is_deprecated, 1,
                                            user_data)      ||
                  ! _gimp_wire_write_string (channel,
                                             (gchar **) &redirect,
                                             1, user_data)  ||
                  ! _gimp_wire_write_string (channel,
                                             (gchar **) &reason,
                                             1, user_data))
                return FALSE;
            }
        }
      break;

    case GP_PARAM_DEF_TYPE_UNIT:
      if (! _gimp_wire_write_int32 (channel,
                                    (guint32 *) &param_def->meta.m_unit.allow_pixels, 1,
                                    user_data) ||
          ! _gimp_wire_write_int32 (channel,
                                    (guint32 *) &param_def->meta.m_unit.allow_percent, 1,
                                    user_data) ||
          ! _gimp_wire_write_int32 (channel,
                                    (guint32 *) &param_def->meta.m_unit.default_val, 1,
                                    user_data))
        return FALSE;
      break;

    case GP_PARAM_DEF_TYPE_ENUM:
      if (! _gimp_wire_write_int32 (channel,
                                    (guint32 *) &param_def->meta.m_enum.default_val, 1,
                                    user_data))
        return FALSE;
      break;

    case GP_PARAM_DEF_TYPE_BOOLEAN:
      if (! _gimp_wire_write_int32 (channel,
                                    (guint32 *) &param_def->meta.m_boolean.default_val, 1,
                                    user_data))
        return FALSE;
      break;

    case GP_PARAM_DEF_TYPE_DOUBLE:
      if (! _gimp_wire_write_double (channel,
                                     &param_def->meta.m_double.min_val, 1,
                                     user_data) ||
          ! _gimp_wire_write_double (channel,
                                     &param_def->meta.m_double.max_val, 1,
                                     user_data) ||
          ! _gimp_wire_write_double (channel,
                                     &param_def->meta.m_double.default_val, 1,
                                     user_data))
        return FALSE;
      break;

    case GP_PARAM_DEF_TYPE_STRING:
      if (! _gimp_wire_write_string (channel,
                                     &param_def->meta.m_string.default_val, 1,
                                     user_data))
        return FALSE;
      break;

    case GP_PARAM_DEF_TYPE_GEGL_COLOR:
        {
          GBytes *pixel_data = NULL;
          GBytes *icc_data   = NULL;
          gchar  *encoding   = "";

          if (! _gimp_wire_write_int32 (channel,
                                        (guint32 *) &param_def->meta.m_gegl_color.has_alpha, 1,
                                        user_data))
            return FALSE;

          if (param_def->meta.m_gegl_color.default_val)
            {
              pixel_data = g_bytes_new_static (param_def->meta.m_gegl_color.default_val->data,
                                               param_def->meta.m_gegl_color.default_val->size);
              icc_data   = g_bytes_new_static (param_def->meta.m_gegl_color.default_val->format.profile_data,
                                               param_def->meta.m_gegl_color.default_val->format.profile_size);
              encoding   = param_def->meta.m_gegl_color.default_val->format.encoding;
            }

          if (! _gimp_wire_write_gegl_color (channel,
                                             &pixel_data,
                                             &icc_data,
                                             &encoding,
                                             1, user_data))
            {
              g_bytes_unref (pixel_data);
              g_bytes_unref (icc_data);
              return FALSE;
            }

          g_bytes_unref (pixel_data);
          g_bytes_unref (icc_data);
        }
      break;

    case GP_PARAM_DEF_TYPE_ID:
      if (! _gimp_wire_write_int32 (channel,
                                    (guint32 *) &param_def->meta.m_id.none_ok, 1,
                                    user_data))
        return FALSE;
      break;

    case GP_PARAM_DEF_TYPE_ID_ARRAY:
      if (! _gimp_wire_write_string (channel,
                                     &param_def->meta.m_id_array.type_name, 1,
                                     user_data))
        return FALSE;
      break;

    case GP_PARAM_DEF_TYPE_RESOURCE:
      if (! _gimp_wire_write_int32 (channel,
                                    (guint32 *) &param_def->meta.m_resource.none_ok, 1,
                                    user_data))
        return FALSE;
      if (! _gimp_wire_write_int32 (channel,
                                    (guint32 *) &param_def->meta.m_resource.default_to_context, 1,
                                    user_data))
        return FALSE;
      if (! _gimp_wire_write_int32 (channel,
                                    (guint32 *) &param_def->meta.m_resource.default_resource_id, 1,
                                    user_data))
        return FALSE;
      break;

    case GP_PARAM_DEF_TYPE_FILE:
      if (! _gimp_wire_write_int32 (channel,
                                    (guint32 *) &param_def->meta.m_file.action, 1,
                                    user_data))
        return FALSE;
      if (! _gimp_wire_write_int32 (channel,
                                    (guint32 *) &param_def->meta.m_file.none_ok, 1,
                                    user_data))
        return FALSE;
      if (! _gimp_wire_write_string (channel,
                                     &param_def->meta.m_file.default_uri, 1,
                                     user_data))
        return FALSE;
      break;

    case GP_PARAM_DEF_TYPE_CURVE:
      if (! _gimp_wire_write_int32 (channel,
                                    (guint32 *) &param_def->meta.m_curve.none_ok, 1,
                                    user_data))
        return FALSE;
      break;
    }

  return TRUE;
}

  static void
_gp_proc_install_write (GIOChannel      *channel,
                        GimpWireMessage *msg,
                        gpointer         user_data)
{
  GPProcInstall *proc_install = msg->data;
  gint           i;

  if (! _gimp_wire_write_string (channel,
                                 &proc_install->name, 1, user_data)    ||
      ! _gimp_wire_write_int32 (channel,
                                &proc_install->type, 1, user_data)     ||
      ! _gimp_wire_write_int32 (channel,
                                &proc_install->n_params, 1, user_data) ||
      ! _gimp_wire_write_int32 (channel,
                                &proc_install->n_return_vals, 1, user_data))
    return;

  for (i = 0; i < proc_install->n_params; i++)
    {
      if (! _gp_param_def_write (channel,
                                 &proc_install->params[i],
                                 user_data))
        return;
    }

  for (i = 0; i < proc_install->n_return_vals; i++)
    {
      if (! _gp_param_def_write (channel,
                                 &proc_install->return_vals[i],
                                 user_data))
        return;
    }
}

static void
_gp_proc_install_destroy (GimpWireMessage *msg)
{
  GPProcInstall *proc_install = msg->data;

  if (proc_install)
    {
      gint i;

      g_free (proc_install->name);

      for (i = 0; i < proc_install->n_params; i++)
        {
          _gp_param_def_destroy (&proc_install->params[i]);
        }

      for (i = 0; i < proc_install->n_return_vals; i++)
        {
          _gp_param_def_destroy (&proc_install->return_vals[i]);
        }

      g_free (proc_install->params);
      g_free (proc_install->return_vals);
      g_slice_free (GPProcInstall, proc_install);
    }
}

/*  proc_uninstall  */

static void
_gp_proc_uninstall_read (GIOChannel      *channel,
                         GimpWireMessage *msg,
                         gpointer         user_data)
{
  GPProcUninstall *proc_uninstall = g_slice_new0 (GPProcUninstall);

  if (! _gimp_wire_read_string (channel, &proc_uninstall->name, 1, user_data))
    goto cleanup;

  msg->data = proc_uninstall;
  return;

 cleanup:
  g_slice_free (GPProcUninstall, proc_uninstall);
}

static void
_gp_proc_uninstall_write (GIOChannel      *channel,
                          GimpWireMessage *msg,
                          gpointer         user_data)
{
  GPProcUninstall *proc_uninstall = msg->data;

  if (! _gimp_wire_write_string (channel, &proc_uninstall->name, 1, user_data))
    return;
}

static void
_gp_proc_uninstall_destroy (GimpWireMessage *msg)
{
  GPProcUninstall *proc_uninstall = msg->data;

  if (proc_uninstall)
    {
      g_free (proc_uninstall->name);
      g_slice_free (GPProcUninstall, proc_uninstall);
    }
}

/*  persistent_ack  */

/* What used to be called extensions are now called persistent plug-ins
 * and we will use the wording "extensions" to name the new packaging
 * format able to contain plug-ins (including persistent ones), but also
 * other types of resources.
 * TODO: API using the old (confusing) wording will have to be deleted
 * for AmmoOS Image 4.
 */
GIMP_WARNING_API_BREAK("Delete deprecated GP_EXTENSION_ACK")

static void
_gp_persistent_ack_read (GIOChannel      *channel,
                         GimpWireMessage *msg,
                         gpointer         user_data)
{
}

static void
_gp_persistent_ack_write (GIOChannel      *channel,
                          GimpWireMessage *msg,
                          gpointer         user_data)
{
}

static void
_gp_persistent_ack_destroy (GimpWireMessage *msg)
{
}

/*  params  */

static void
_gp_params_read (GIOChannel  *channel,
                 GPParam    **params,
                 guint       *n_params,
                 gpointer     user_data)
{
  guint i;

  if (! _gimp_wire_read_int32 (channel, (guint32 *) n_params, 1, user_data))
    return;

  if (*n_params == 0)
    {
      *params = NULL;
      return;
    }

  *params = g_try_new0 (GPParam, *n_params);

  /* We may read crap on the wire (and as a consequence try to allocate
   * far too much), which would be a plug-in error.
   */
  if (*params == NULL)
    {
      /* Output on stderr but no WARNING/CRITICAL. This is likely a
       * plug-in bug sending bogus data, not a core bug.
       */
      g_printerr ("%s: failed to allocate %u parameters\n",
                  G_STRFUNC, *n_params);
      *n_params = 0;
      return;
    }

  for (i = 0; i < *n_params; i++)
    {
      if (! _gimp_wire_read_int32 (channel,
                                   (guint32 *) &(*params)[i].param_type, 1,
                                   user_data) ||
          ! _gimp_wire_read_string (channel,
                                    &(*params)[i].type_name, 1,
                                    user_data))
        return;

      switch ((*params)[i].param_type)
        {
        case GP_PARAM_TYPE_INT:
          if (! _gimp_wire_read_int32 (channel,
                                       (guint32 *) &(*params)[i].data.d_int, 1,
                                       user_data))
            goto cleanup;
          break;

        case GP_PARAM_TYPE_DOUBLE:
          if (! _gimp_wire_read_double (channel,
                                        &(*params)[i].data.d_double, 1,
                                        user_data))
            goto cleanup;
          break;

        case GP_PARAM_TYPE_STRING:
        case GP_PARAM_TYPE_FILE:
          if (! _gimp_wire_read_string (channel,
                                        &(*params)[i].data.d_string, 1,
                                        user_data))
            goto cleanup;
          break;

        case GP_PARAM_TYPE_BABL_FORMAT:
          /* Read encoding. */
          if (! _gimp_wire_read_string (channel,
                                        &(*params)[i].data.d_format.encoding, 1,
                                        user_data))
            goto cleanup;

          /* Read space (profile data). */
          if (! _gimp_wire_read_int32 (channel,
                                       &(*params)[i].data.d_format.profile_size, 1,
                                       user_data))
            {
              g_clear_pointer (&(*params)[i].data.d_format.encoding, g_free);
              goto cleanup;
            }

          (*params)[i].data.d_format.profile_data = g_new0 (guint8, (*params)[i].data.d_format.profile_size);
          if (! _gimp_wire_read_int8 (channel,
                                      (*params)[i].data.d_format.profile_data,
                                      (*params)[i].data.d_format.profile_size,
                                      user_data))
            {
              g_clear_pointer (&(*params)[i].data.d_format.encoding, g_free);
              g_clear_pointer (&(*params)[i].data.d_format.profile_data, g_free);
              goto cleanup;
            }

          break;

        case GP_PARAM_TYPE_GEGL_COLOR:
          /* Read the color data. */
          if (! _gimp_wire_read_int32 (channel,
                                       &(*params)[i].data.d_gegl_color.size, 1,
                                       user_data))
            goto cleanup;

          if ((*params)[i].data.d_gegl_color.size > 40 ||
              ! _gimp_wire_read_int8 (channel,
                                      (*params)[i].data.d_gegl_color.data,
                                      (*params)[i].data.d_gegl_color.size,
                                      user_data))
            goto cleanup;

          /* Read encoding. */
          if (! _gimp_wire_read_string (channel,
                                        &(*params)[i].data.d_gegl_color.format.encoding, 1,
                                        user_data))
            goto cleanup;

          /* Read space (profile data). */
          if (! _gimp_wire_read_int32 (channel,
                                       &(*params)[i].data.d_gegl_color.format.profile_size, 1,
                                       user_data))
            {
              g_clear_pointer (&(*params)[i].data.d_gegl_color.format.encoding, g_free);
              goto cleanup;
            }

          (*params)[i].data.d_gegl_color.format.profile_data = g_new0 (guint8, (*params)[i].data.d_gegl_color.format.profile_size);
          if (! _gimp_wire_read_int8 (channel,
                                      (*params)[i].data.d_gegl_color.format.profile_data,
                                      (*params)[i].data.d_gegl_color.format.profile_size,
                                      user_data))
            {
              g_clear_pointer (&(*params)[i].data.d_gegl_color.format.encoding, g_free);
              g_clear_pointer (&(*params)[i].data.d_gegl_color.format.profile_data, g_free);
              goto cleanup;
            }

          break;

        case GP_PARAM_TYPE_COLOR_ARRAY:
          if (! _gimp_wire_read_int32 (channel,
                                       &(*params)[i].data.d_color_array.size, 1,
                                       user_data))
            goto cleanup;

          (*params)[i].data.d_color_array.colors = g_new0 (GPParamColor,
                                                           (*params)[i].data.d_color_array.size);

          for (gint j = 0; j < (*params)[i].data.d_color_array.size; j++)
            {
              /* Read the color data. */
              if (! _gimp_wire_read_int32 (channel,
                                           &(*params)[i].data.d_color_array.colors[j].size, 1,
                                           user_data))
                {
                  for (gint k = 0; k < j; k++)
                    {
                      g_free ((*params)[i].data.d_color_array.colors[k].format.encoding);
                      g_free ((*params)[i].data.d_color_array.colors[k].format.profile_data);
                    }
                  g_clear_pointer (&(*params)[i].data.d_color_array.colors, g_free);
                  goto cleanup;
                }

              if ((*params)[i].data.d_color_array.colors[j].size > 40 ||
                  ! _gimp_wire_read_int8 (channel,
                                          (*params)[i].data.d_color_array.colors[j].data,
                                          (*params)[i].data.d_color_array.colors[j].size,
                                          user_data))
                {
                  for (gint k = 0; k < j; k++)
                    {
                      g_free ((*params)[i].data.d_color_array.colors[k].format.encoding);
                      g_free ((*params)[i].data.d_color_array.colors[k].format.profile_data);
                    }
                  g_clear_pointer (&(*params)[i].data.d_color_array.colors, g_free);
                  goto cleanup;
                }

              /* Read encoding. */
              if (! _gimp_wire_read_string (channel,
                                            &(*params)[i].data.d_color_array.colors[j].format.encoding, 1,
                                            user_data))
                {
                  for (gint k = 0; k < j; k++)
                    {
                      g_free ((*params)[i].data.d_color_array.colors[k].format.encoding);
                      g_free ((*params)[i].data.d_color_array.colors[k].format.profile_data);
                    }
                  g_clear_pointer (&(*params)[i].data.d_color_array.colors, g_free);
                  goto cleanup;
                }

              /* Read space (profile data). */
              if (! _gimp_wire_read_int32 (channel,
                                           &(*params)[i].data.d_color_array.colors[j].format.profile_size, 1,
                                           user_data))
                {
                  for (gint k = 0; k < j; k++)
                    {
                      g_free ((*params)[i].data.d_color_array.colors[k].format.encoding);
                      g_free ((*params)[i].data.d_color_array.colors[k].format.profile_data);
                    }
                  g_clear_pointer (&(*params)[i].data.d_color_array.colors[j].format.encoding, g_free);
                  g_clear_pointer (&(*params)[i].data.d_color_array.colors, g_free);
                  goto cleanup;
                }

              if ((*params)[i].data.d_color_array.colors[j].format.profile_size > 0)
                {
                  (*params)[i].data.d_color_array.colors[j].format.profile_data = g_new0 (guint8, (*params)[i].data.d_color_array.colors[j].format.profile_size);
                  if (! _gimp_wire_read_int8 (channel,
                                              (*params)[i].data.d_color_array.colors[j].format.profile_data,
                                              (*params)[i].data.d_color_array.colors[j].format.profile_size,
                                              user_data))
                    {
                      for (gint k = 0; k < j; k++)
                        {
                          g_free ((*params)[i].data.d_color_array.colors[k].format.encoding);
                          g_free ((*params)[i].data.d_color_array.colors[k].format.profile_data);
                        }
                      g_clear_pointer (&(*params)[i].data.d_color_array.colors[j].format.encoding, g_free);
                      g_clear_pointer (&(*params)[i].data.d_color_array.colors[j].format.profile_data, g_free);
                      g_clear_pointer (&(*params)[i].data.d_color_array.colors, g_free);
                      goto cleanup;
                    }
                }
            }
          break;

        case GP_PARAM_TYPE_ARRAY:
          if (! _gimp_wire_read_int32 (channel,
                                       &(*params)[i].data.d_array.size, 1,
                                       user_data))
            goto cleanup;

          (*params)[i].data.d_array.data = g_new0 (guint8,
                                                   (*params)[i].data.d_array.size);

          if (! _gimp_wire_read_int8 (channel,
                                      (*params)[i].data.d_array.data,
                                      (*params)[i].data.d_array.size,
                                      user_data))
            {
              g_free ((*params)[i].data.d_array.data);
              (*params)[i].data.d_array.data = NULL;
              goto cleanup;
            }
          break;

        case GP_PARAM_TYPE_BYTES:
          {
            guint32 data_len;
            guint8* data;

            if (! _gimp_wire_read_int32 (channel, &data_len, 1, user_data))
              goto cleanup;

            data = g_new0 (guint8, data_len);

            if (! _gimp_wire_read_int8 (channel, data, data_len, user_data))
              {
                g_free (data);
                goto cleanup;
              }

            (*params)[i].data.d_bytes = g_bytes_new_take (data, data_len);
          }
          break;

        case GP_PARAM_TYPE_STRV:
          {
            guint32 size;

            if (! _gimp_wire_read_int32 (channel, &size, 1, user_data))
              goto cleanup;

            (*params)[i].data.d_strv = g_new0 (gchar *, size + 1);

            if (! _gimp_wire_read_string (channel,
                                          (*params)[i].data.d_strv,
                                          (int) size,
                                          user_data))
              {
                g_strfreev ((*params)[i].data.d_strv);
                (*params)[i].data.d_strv = NULL;
                goto cleanup;
              }
            break;
          }

        case GP_PARAM_TYPE_ID_ARRAY:
          if (! _gimp_wire_read_string (channel,
                                        &(*params)[i].data.d_id_array.type_name, 1,
                                        user_data))
            goto cleanup;

          if (! _gimp_wire_read_int32 (channel,
                                       &(*params)[i].data.d_id_array.size, 1,
                                       user_data))
            goto cleanup;

          (*params)[i].data.d_id_array.data = g_new0 (gint32,
                                                      (*params)[i].data.d_id_array.size);

          if (! _gimp_wire_read_int32 (channel,
                                       (guint32 *) (*params)[i].data.d_id_array.data,
                                       (*params)[i].data.d_id_array.size,
                                       user_data))
            {
              g_free ((*params)[i].data.d_id_array.data);
              (*params)[i].data.d_id_array.data = NULL;
              goto cleanup;
            }
          break;

        case GP_PARAM_TYPE_PARASITE:
          if (! _gimp_wire_read_string (channel,
                                        &(*params)[i].data.d_parasite.name, 1,
                                        user_data))
            goto cleanup;
          if ((*params)[i].data.d_parasite.name == NULL)
            {
              /* we have a null parasite */
              (*params)[i].data.d_parasite.data = NULL;
              break;
            }
          if (! _gimp_wire_read_int32 (channel,
                                       &((*params)[i].data.d_parasite.flags), 1,
                                       user_data))
            goto cleanup;
          if (! _gimp_wire_read_int32 (channel,
                                       &((*params)[i].data.d_parasite.size), 1,
                                       user_data))
            goto cleanup;
          if ((*params)[i].data.d_parasite.size > 0)
            {
              (*params)[i].data.d_parasite.data =
                g_malloc ((*params)[i].data.d_parasite.size);
              if (! _gimp_wire_read_int8 (channel,
                                          (*params)[i].data.d_parasite.data,
                                          (*params)[i].data.d_parasite.size,
                                          user_data))
                {
                  g_free ((*params)[i].data.d_parasite.data);
                  goto cleanup;
                }
            }
          else
            (*params)[i].data.d_parasite.data = NULL;
          break;

        case GP_PARAM_TYPE_EXPORT_OPTIONS:
          /* XXX: reading export options when we'll have any. */
          break;

        case GP_PARAM_TYPE_PARAM_DEF:
          if (! _gp_param_def_read (channel,
                                    &(*params)[i].data.d_param_def,
                                    user_data))
            goto cleanup;
          break;

        case GP_PARAM_TYPE_VALUE_ARRAY:
          {
            guint n_values = 0;

            (*params)[i].data.d_value_array.values = NULL;
            _gp_params_read (channel,
                             &(*params)[i].data.d_value_array.values,
                             &n_values,
                             user_data);
            (*params)[i].data.d_value_array.n_values = (guint32) n_values;
            break;
          }

        case GP_PARAM_TYPE_CURVE:
          {
            if (! _gimp_wire_read_int32 (channel,
                                         &(*params)[i].data.d_curve.curve_type, 1,
                                         user_data))
              goto cleanup;

            if (! _gimp_wire_read_int32 (channel,
                                         &(*params)[i].data.d_curve.n_points, 1,
                                         user_data))
              goto cleanup;

            if (! _gimp_wire_read_int32 (channel,
                                         &(*params)[i].data.d_curve.n_samples, 1,
                                         user_data))
              goto cleanup;

            (*params)[i].data.d_curve.points = g_new0 (gdouble,
                                                       2 * (*params)[i].data.d_curve.n_points);

            if (! _gimp_wire_read_double (channel,
                                          (*params)[i].data.d_curve.points,
                                          2 * (*params)[i].data.d_curve.n_points,
                                          user_data))
              {
                g_free ((*params)[i].data.d_curve.points);
                (*params)[i].data.d_curve.points = NULL;
                goto cleanup;
              }

            (*params)[i].data.d_curve.point_types = g_new0 (guint32,
                                                            (*params)[i].data.d_curve.n_points);

            if (! _gimp_wire_read_int32 (channel,
                                         (*params)[i].data.d_curve.point_types,
                                         (*params)[i].data.d_curve.n_points,
                                         user_data))
              {
                g_free ((*params)[i].data.d_curve.point_types);
                (*params)[i].data.d_curve.point_types = NULL;
                goto cleanup;
              }

            (*params)[i].data.d_curve.samples = g_new0 (gdouble,
                                                        (*params)[i].data.d_curve.n_samples);

            if (! _gimp_wire_read_double (channel,
                                          (*params)[i].data.d_curve.samples,
                                          (*params)[i].data.d_curve.n_samples,
                                          user_data))
              {
                g_free ((*params)[i].data.d_curve.samples);
                (*params)[i].data.d_curve.samples = NULL;
                goto cleanup;
              }
          }
          break;
        }
    }

  return;

 cleanup:
  *n_params = 0;
  g_free (*params);
  *params = NULL;
}

static void
_gp_params_write (GIOChannel *channel,
                  GPParam    *params,
                  gint        n_params,
                  gpointer    user_data)
{
  gint i;

  if (! _gimp_wire_write_int32 (channel,
                                (const guint32 *) &n_params, 1, user_data))
    return;

  for (i = 0; i < n_params; i++)
    {
      if (! _gimp_wire_write_int32 (channel,
                                    (const guint32 *) &params[i].param_type, 1,
                                    user_data))
        return;

      if (! _gimp_wire_write_string (channel,
                                     &params[i].type_name, 1,
                                     user_data))
        return;

      switch (params[i].param_type)
        {
        case GP_PARAM_TYPE_INT:
          if (! _gimp_wire_write_int32 (channel,
                                        (const guint32 *) &params[i].data.d_int, 1,
                                        user_data))
            return;
          break;

        case GP_PARAM_TYPE_DOUBLE:
          if (! _gimp_wire_write_double (channel,
                                         (const gdouble *) &params[i].data.d_double, 1,
                                         user_data))
            return;
          break;

        case GP_PARAM_TYPE_STRING:
        case GP_PARAM_TYPE_FILE:
          if (! _gimp_wire_write_string (channel,
                                         &params[i].data.d_string, 1,
                                         user_data))
            return;
          break;

        case GP_PARAM_TYPE_BABL_FORMAT:
          if (! _gimp_wire_write_string (channel,
                                         &params[i].data.d_format.encoding, 1,
                                         user_data) ||
              ! _gimp_wire_write_int32 (channel,
                                        (const guint32 *) &params[i].data.d_format.profile_size, 1,
                                        user_data)  ||
              ! _gimp_wire_write_int8 (channel,
                                       (const guint8 *) params[i].data.d_format.profile_data,
                                       params[i].data.d_format.profile_size,
                                       user_data))
            return;
          break;

        case GP_PARAM_TYPE_GEGL_COLOR:
          if (! _gimp_wire_write_int32 (channel,
                                        (const guint32 *) &params[i].data.d_gegl_color.size, 1,
                                        user_data)  ||
              ! _gimp_wire_write_int8 (channel,
                                       (const guint8 *) params[i].data.d_gegl_color.data,
                                       params[i].data.d_gegl_color.size,
                                       user_data)   ||
              ! _gimp_wire_write_string (channel,
                                         &params[i].data.d_gegl_color.format.encoding, 1,
                                         user_data) ||
              ! _gimp_wire_write_int32 (channel,
                                        (const guint32 *) &params[i].data.d_gegl_color.format.profile_size, 1,
                                        user_data)  ||
              ! _gimp_wire_write_int8 (channel,
                                       (const guint8 *) params[i].data.d_gegl_color.format.profile_data,
                                       params[i].data.d_gegl_color.format.profile_size,
                                       user_data))
            return;
          break;

        case GP_PARAM_TYPE_COLOR_ARRAY:
          if (! _gimp_wire_write_int32 (channel,
                                        (const guint32 *) &params[i].data.d_color_array.size, 1,
                                        user_data))
            return;

          for (gint j = 0; j < params[i].data.d_color_array.size; j++)
            {
              if (! _gimp_wire_write_int32 (channel,
                                            (const guint32 *) &params[i].data.d_color_array.colors[j].size, 1,
                                            user_data)  ||
                  ! _gimp_wire_write_int8 (channel,
                                           (const guint8 *) params[i].data.d_color_array.colors[j].data,
                                           params[i].data.d_color_array.colors[j].size,
                                           user_data)   ||
                  ! _gimp_wire_write_string (channel,
                                             &params[i].data.d_color_array.colors[j].format.encoding, 1,
                                             user_data) ||
                  ! _gimp_wire_write_int32 (channel,
                                            (const guint32 *) &params[i].data.d_color_array.colors[j].format.profile_size, 1,
                                            user_data)  ||
                  ! _gimp_wire_write_int8 (channel,
                                           (const guint8 *) params[i].data.d_color_array.colors[j].format.profile_data,
                                           params[i].data.d_color_array.colors[j].format.profile_size,
                                           user_data))
                return;
            }
          break;

        case GP_PARAM_TYPE_ARRAY:
          if (! _gimp_wire_write_int32 (channel,
                                        (const guint32 *) &params[i].data.d_array.size, 1,
                                        user_data) ||
              ! _gimp_wire_write_int8 (channel,
                                       (const guint8 *) params[i].data.d_array.data,
                                       params[i].data.d_array.size,
                                       user_data))
            return;
          break;

        case GP_PARAM_TYPE_BYTES:
          {
            const guint8 *bytes = NULL;
            guint32       size  = 0;

            if (params[i].data.d_bytes)
              {
                bytes = g_bytes_get_data (params[i].data.d_bytes, NULL);
                size = g_bytes_get_size (params[i].data.d_bytes);
              }

            if (! _gimp_wire_write_int32 (channel, &size, 1, user_data) ||
                ! _gimp_wire_write_int8 (channel, bytes, size, user_data))
              return;
          }
          break;

        case GP_PARAM_TYPE_STRV:
          {
            gint size;

            if (params[i].data.d_strv)
              size = g_strv_length (params[i].data.d_strv);
            else
              size = 0;

            if (! _gimp_wire_write_int32 (channel,
                                          (guint32*) &size, 1,
                                          user_data) ||
                ! _gimp_wire_write_string (channel,
                                           params[i].data.d_strv,
                                           size,
                                           user_data))
              return;
          }
          break;

        case GP_PARAM_TYPE_ID_ARRAY:
          if (! _gimp_wire_write_string (channel,
                                         &params[i].data.d_id_array.type_name, 1,
                                         user_data) ||
              ! _gimp_wire_write_int32 (channel,
                                        (const guint32 *) &params[i].data.d_id_array.size, 1,
                                        user_data) ||
              ! _gimp_wire_write_int32 (channel,
                                        (const guint32 *) params[i].data.d_id_array.data,
                                        params[i].data.d_id_array.size,
                                        user_data))
            return;
          break;

        case GP_PARAM_TYPE_PARASITE:
          {
            GimpParasite *p = &params[i].data.d_parasite;

            if (p->name == NULL)
              {
                /* write a null string to signal a null parasite */
                _gimp_wire_write_string (channel,  &p->name, 1, user_data);
                break;
              }

            if (! _gimp_wire_write_string (channel, &p->name, 1, user_data))
              return;
            if (! _gimp_wire_write_int32 (channel, &p->flags, 1, user_data))
              return;
            if (! _gimp_wire_write_int32 (channel, &p->size, 1, user_data))
              return;
            if (p->size > 0)
              {
                if (! _gimp_wire_write_int8 (channel,
                                             p->data, p->size, user_data))
                  return;
              }
          }
          break;

        case GP_PARAM_TYPE_EXPORT_OPTIONS:
          /* XXX When we'll have actual export options, this is where
           * we'll want to pass them through the wire.
           */
          break;

        case GP_PARAM_TYPE_PARAM_DEF:
          if (! _gp_param_def_write (channel,
                                     &params[i].data.d_param_def,
                                     user_data))
            return;
          break;

        case GP_PARAM_TYPE_VALUE_ARRAY:
          _gp_params_write (channel,
                            params[i].data.d_value_array.values,
                            params[i].data.d_value_array.n_values,
                            user_data);
          break;

        case GP_PARAM_TYPE_CURVE:
          if (! _gimp_wire_write_int32 (channel,
                                        (const guint32 *) &params[i].data.d_curve.curve_type, 1,
                                        user_data))
            return;

          if (! _gimp_wire_write_int32 (channel,
                                        (const guint32 *) &params[i].data.d_curve.n_points, 1,
                                        user_data))
            return;

          if (! _gimp_wire_write_int32 (channel,
                                        (const guint32 *) &params[i].data.d_curve.n_samples, 1,
                                        user_data))
            return;

          if (! _gimp_wire_write_double (channel,
                                         params[i].data.d_curve.points,
                                         2 * params[i].data.d_curve.n_points,
                                         user_data))
            return;

          if (! _gimp_wire_write_int32 (channel,
                                        (const guint32 *) params[i].data.d_curve.point_types,
                                        params[i].data.d_curve.n_points,
                                        user_data))
            return;

          if (! _gimp_wire_write_double (channel,
                                         params[i].data.d_curve.samples,
                                         params[i].data.d_curve.n_samples,
                                         user_data))
            return;

          break;
        }
    }
}

static void
_gp_params_destroy (GPParam *params,
                    gint     n_params)
{
  gint i;

  for (i = 0; i < n_params; i++)
    {
      g_free (params[i].type_name);

      switch (params[i].param_type)
        {
        case GP_PARAM_TYPE_INT:
        case GP_PARAM_TYPE_DOUBLE:
          break;

        case GP_PARAM_TYPE_STRING:
        case GP_PARAM_TYPE_FILE:
          g_free (params[i].data.d_string);
          break;

        case GP_PARAM_TYPE_BABL_FORMAT:
          g_free (params[i].data.d_format.profile_data);
          break;

        case GP_PARAM_TYPE_GEGL_COLOR:
          g_free (params[i].data.d_gegl_color.format.encoding);
          g_free (params[i].data.d_gegl_color.format.profile_data);
          break;

        case GP_PARAM_TYPE_COLOR_ARRAY:
         for (gint j = 0; j < params[i].data.d_color_array.size; j++)
           {
             g_free (params[i].data.d_color_array.colors[j].format.encoding);
             g_free (params[i].data.d_color_array.colors[j].format.profile_data);
           }
          g_free (params[i].data.d_color_array.colors);
          break;

        case GP_PARAM_TYPE_ARRAY:
          g_free (params[i].data.d_array.data);
          break;

        case GP_PARAM_TYPE_BYTES:
          g_bytes_unref (params[i].data.d_bytes);
          break;

        case GP_PARAM_TYPE_STRV:
          g_strfreev (params[i].data.d_strv);
          break;

        case GP_PARAM_TYPE_ID_ARRAY:
          g_free (params[i].data.d_id_array.type_name);
          g_free (params[i].data.d_id_array.data);
          break;

        case GP_PARAM_TYPE_PARASITE:
          if (params[i].data.d_parasite.name)
            g_free (params[i].data.d_parasite.name);
          if (params[i].data.d_parasite.data)
            g_free (params[i].data.d_parasite.data);
          break;

        case GP_PARAM_TYPE_EXPORT_OPTIONS:
          break;

        case GP_PARAM_TYPE_PARAM_DEF:
          _gp_param_def_destroy (&params[i].data.d_param_def);
          break;

        case GP_PARAM_TYPE_VALUE_ARRAY:
          _gp_params_destroy (params[i].data.d_value_array.values,
                              params[i].data.d_value_array.n_values);
          break;

        case GP_PARAM_TYPE_CURVE:
          if (params[i].data.d_curve.points)
            g_free (params[i].data.d_curve.points);
          if (params[i].data.d_curve.point_types)
            g_free (params[i].data.d_curve.point_types);
          if (params[i].data.d_curve.samples)
            g_free (params[i].data.d_curve.samples);
          break;
        }
    }

  g_free (params);
}

/* has_init */

static void
_gp_has_init_read (GIOChannel      *channel,
                   GimpWireMessage *msg,
                   gpointer         user_data)
{
}

static void
_gp_has_init_write (GIOChannel      *channel,
                    GimpWireMessage *msg,
                    gpointer         user_data)
{
}

static void
_gp_has_init_destroy (GimpWireMessage *msg)
{
}

/* --- end libammoos/base/fieldbase/gimpprotocol.c --- */

/* --- begin libammoos/base/fieldbase/gimprectangle.c --- */
/* LIBGIMP - The AmmoOS Image Library
 * Copyright (C) 1995-1997 Spencer Kimball and Peter Mattis
 *
 * gimprectangle.c
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

#include <glib.h>

#include "gimprectangle.h"


/**
 * SECTION: gimprectangle
 * @title: gimprectangle
 * @short_description: Utility functions dealing with rectangle extents.
 *
 * Utility functions dealing with rectangle extents.
 **/


/**
 * gimp_rectangle_intersect:
 * @x1:          origin of first rectangle
 * @y1:          origin of first rectangle
 * @width1:      width of first rectangle
 * @height1:     height of first rectangle
 * @x2:          origin of second rectangle
 * @y2:          origin of second rectangle
 * @width2:      width of second rectangle
 * @height2:     height of second rectangle
 * @dest_x: (out) (optional): return location for origin of intersection,
 *                            or %NULL
 * @dest_y: (out) (optional): return location for origin of intersection,
 *                            or %NULL
 * @dest_width: (out) (optional): return location for width of intersection,
 *                                or %NULL
 * @dest_height: (out) (optional): return location for height of intersection,
 *                                 or %NULL
 *
 * Calculates the intersection of two rectangles.
 *
 * Returns: %TRUE if the intersection is non-empty, %FALSE otherwise
 *
 * Since: 2.4
 **/
gboolean
gimp_rectangle_intersect (gint  x1,
                          gint  y1,
                          gint  width1,
                          gint  height1,
                          gint  x2,
                          gint  y2,
                          gint  width2,
                          gint  height2,
                          gint *dest_x,
                          gint *dest_y,
                          gint *dest_width,
                          gint *dest_height)
{
  gint d_x, d_y;
  gint d_w, d_h;

  d_x = MAX (x1, x2);
  d_y = MAX (y1, y2);
  d_w = MIN (x1 + width1,  x2 + width2)  - d_x;
  d_h = MIN (y1 + height1, y2 + height2) - d_y;

  if (dest_x)      *dest_x      = d_x;
  if (dest_y)      *dest_y      = d_y;
  if (dest_width)  *dest_width  = d_w;
  if (dest_height) *dest_height = d_h;

  return (d_w > 0 && d_h > 0);
}

/**
 * gimp_rectangle_union:
 * @x1:          origin of first rectangle
 * @y1:          origin of first rectangle
 * @width1:      width of first rectangle
 * @height1:     height of first rectangle
 * @x2:          origin of second rectangle
 * @y2:          origin of second rectangle
 * @width2:      width of second rectangle
 * @height2:     height of second rectangle
 * @dest_x: (out) (optional): return location for origin of union, or %NULL
 * @dest_y: (out) (optional): return location for origin of union, or %NULL
 * @dest_width: (out) (optional): return location for width of union, or %NULL
 * @dest_height: (out) (optional): return location for height of union, or %NULL
 *
 * Calculates the union of two rectangles.
 *
 * Since: 2.8
 **/
void
gimp_rectangle_union (gint  x1,
                      gint  y1,
                      gint  width1,
                      gint  height1,
                      gint  x2,
                      gint  y2,
                      gint  width2,
                      gint  height2,
                      gint *dest_x,
                      gint *dest_y,
                      gint *dest_width,
                      gint *dest_height)
{
  gint d_x, d_y;
  gint d_w, d_h;

  d_x = MIN (x1, x2);
  d_y = MIN (y1, y2);
  d_w = MAX (x1 + width1,  x2 + width2)  - d_x;
  d_h = MAX (y1 + height1, y2 + height2) - d_y;

  if (dest_x)      *dest_x      = d_x;
  if (dest_y)      *dest_y      = d_y;
  if (dest_width)  *dest_width  = d_w;
  if (dest_height) *dest_height = d_h;
}

/* --- end libammoos/base/fieldbase/gimprectangle.c --- */

/* --- begin libammoos/base/fieldbase/gimpreloc.c --- */
/*
 * BinReloc - a library for creating relocatable executables
 * Written by: Hongli Lai <h.lai@chello.nl>
 * http://autopackage.org/
 *
 * This source code is public domain. You can relicense this code
 * under whatever license you want.
 *
 * See http://autopackage.org/docs/binreloc/ for
 * more information and how to use this.
 */

#include "config.h"

#include <stdlib.h>
#include <limits.h>
#include <string.h>

#if defined(ENABLE_RELOCATABLE_RESOURCES) && ! defined(_WIN32)
#include <sys/types.h>
#include <sys/stat.h>
#include <unistd.h>
#endif /* ENABLE_RELOCATABLE_RESOURCES && ! _WIN32 */

#include <gio/gio.h>
#include <glib.h>
#include <glib/gstdio.h>

#include "gimpreloc.h"


/*
 * Find the canonical filename of the executable. Returns the filename
 * (which must be freed) or NULL on error. If the parameter 'error' is
 * not NULL, the error code will be stored there, if an error occurred.
 */
static char *
_br_find_exe (GimpBinrelocInitError *error)
{
#if ! defined(ENABLE_RELOCATABLE_RESOURCES) || defined(G_OS_WIN32) || defined(__APPLE__)
  if (error)
    *error = GIMP_RELOC_INIT_ERROR_DISABLED;
  return NULL;
#else
  GDataInputStream *data_input;
  GInputStream     *input;
  GFile            *file;
  GError           *gerror = NULL;
  gchar            *path;
  gchar            *sym_path;
  gchar            *maps_line;

  sym_path = g_strdup ("/proc/self/exe");

  while (1)
    {
      struct stat stat_buf;
      int         i;

      /* Do not use readlink() with a buffer of size PATH_MAX because
       * some systems actually allow paths of bigger size. Thus this
       * macro is kind of bogus. Some systems like Hurd will not even
       * define it (see MR !424).
       * g_file_read_link() on the other hand will return a size of
       * appropriate size, with newline removed and NUL terminator
       * added.
       */
      path = g_file_read_link (sym_path, &gerror);
      g_free (sym_path);
      if (! path)
        {
          /* Read link fails but we can try reading /proc/self/maps as
           * an alternate method.
           */
          g_printerr ("%s: %s\n", G_STRFUNC, gerror->message);
          g_clear_error (&gerror);

          break;
        }

      /* Check whether the symlink's target is also a symlink.
       * We want to get the final target. */
      i = stat (path, &stat_buf);
      if (i == -1)
        {
          /* Error. */
          break;
        }

      /* stat() success. */
      if (! S_ISLNK (stat_buf.st_mode))
        {
          /* path is not a symlink. Done. */
          return path;
        }

      /* path is a symlink. Continue loop and resolve this. */
      sym_path = path;
    }

  /* readlink() or stat() failed; this can happen when the program is
   * running in Valgrind 2.2. Read from /proc/self/maps as fallback. */

  file = g_file_new_for_path ("/proc/self/maps");
  input = G_INPUT_STREAM (g_file_read (file, NULL, &gerror));
  g_object_unref (file);
  if (! input)
    {
      g_printerr ("%s: %s", G_STRFUNC, gerror->message);
      g_clear_error (&gerror);

      if (error)
        *error = GIMP_RELOC_INIT_ERROR_OPEN_MAPS;

      return NULL;
    }

  data_input = g_data_input_stream_new (input);
  g_object_unref (input);

  /* The first entry with r-xp permission should be the executable name. */
  while ((maps_line = g_data_input_stream_read_line (data_input, NULL, NULL, &gerror)))
    {
      if (maps_line == NULL)
        {
          if (gerror)
            {
              g_printerr ("%s: %s\n", G_STRFUNC, gerror->message);
              g_error_free (gerror);
            }
          g_object_unref (data_input);

          if (error)
            *error = GIMP_RELOC_INIT_ERROR_READ_MAPS;

          return NULL;
        }

      /* Extract the filename; it is always an absolute path. */
      path = strchr (maps_line, '/');

      /* Sanity check. */
      if (path && strstr (maps_line, " r-xp "))
        {
          /* We found the executable name. */
          path = g_strdup (path);
          break;
        }

      g_free (maps_line);
      maps_line = NULL;
      path = NULL;
    }

  if (path == NULL && error)
    *error = GIMP_RELOC_INIT_ERROR_INVALID_MAPS;

  g_object_unref (data_input);
  g_free (maps_line);

  return path;
#endif /* ! ENABLE_RELOCATABLE_RESOURCES || G_OS_WIN32 */
}


/*
 * Find the canonical filename of the executable which owns symbol.
 * Returns a filename which must be freed, or NULL on error.
 */
static char *
_br_find_exe_for_symbol (const void *symbol, GimpBinrelocInitError *error)
{
#if ! defined(ENABLE_RELOCATABLE_RESOURCES) || defined(G_OS_WIN32) || defined(__APPLE__)
  if (error)
    *error = GIMP_RELOC_INIT_ERROR_DISABLED;
  return (char *) NULL;
#else
  GDataInputStream *data_input;
  GInputStream     *input;
  GFile            *file;
  GError           *gerror = NULL;
  gchar            *maps_line;
  char             *found = NULL;
  char             *address_string;
  size_t            address_string_len;

  if (symbol == NULL)
    return (char *) NULL;

  file = g_file_new_for_path ("/proc/self/maps");
  input = G_INPUT_STREAM (g_file_read (file, NULL, &gerror));
  g_object_unref (file);
  if (! input)
    {
      g_printerr ("%s: %s", G_STRFUNC, gerror->message);
      g_error_free (gerror);

      if (error)
        *error = GIMP_RELOC_INIT_ERROR_OPEN_MAPS;

      return NULL;
    }

  data_input = g_data_input_stream_new (input);
  g_object_unref (input);

  address_string_len = 4;
  address_string = g_try_new (char, address_string_len);

  while ((maps_line = g_data_input_stream_read_line (data_input, NULL, NULL, &gerror)))
    {
      char   *start_addr, *end_addr, *end_addr_end;
      char   *path;
      void   *start_addr_p, *end_addr_p;
      size_t  len;

      if (maps_line == NULL)
        {
          if (gerror)
            {
              g_printerr ("%s: %s\n", G_STRFUNC, gerror->message);
              g_error_free (gerror);
            }

          if (error)
            *error = GIMP_RELOC_INIT_ERROR_READ_MAPS;

          break;
        }

      /* Sanity check. */
      /* XXX Early versions of this code would check that the mapped
       * region was with r-xp permission. It might have been true at
       * some point in time, but last I tested, the searched pointer was
       * in a r--p region for libgimpbase. Thus _br_find_exe_for_symbol()
       * would fail to find the executable's path.
       * So now we don't test the region's permission anymore.
       */
      if (strchr (maps_line, '/') == NULL)
        {
          g_free (maps_line);
          continue;
        }

      /* Parse line. */
      start_addr = maps_line;
      end_addr = strchr (maps_line, '-');
      path = strchr (maps_line, '/');

      /* More sanity check. */
      if (!(path > end_addr && end_addr != NULL && end_addr[0] == '-'))
        {
          g_free (maps_line);
          continue;
        }

      end_addr[0] = '\0';
      end_addr++;
      end_addr_end = strchr (end_addr, ' ');
      if (end_addr_end == NULL)
        {
          g_free (maps_line);
          continue;
        }

      end_addr_end[0] = '\0';
      len = strlen (path);
      if (len == 0)
        {
          g_free (maps_line);
          continue;
        }
      if (path[len - 1] == '\n')
        path[len - 1] = '\0';

      /* Get rid of "(deleted)" from the filename. */
      len = strlen (path);
      if (len > 10 && strcmp (path + len - 10, " (deleted)") == 0)
        path[len - 10] = '\0';

      /* I don't know whether this can happen but better safe than sorry. */
      len = strlen (start_addr);
      if (len != strlen (end_addr))
        {
          g_free (maps_line);
          continue;
        }

      /* Transform the addresses into a string in the form of 0xdeadbeef,
       * then transform that into a pointer. */
      if (address_string_len < len + 3)
        {
          address_string_len = len + 3;
          address_string = (char *) g_try_realloc (address_string, address_string_len);
        }

      memcpy (address_string, "0x", 2);
      memcpy (address_string + 2, start_addr, len);
      address_string[2 + len] = '\0';
#ifndef _UCRT
      sscanf (address_string, "%p", &start_addr_p);
#else
      sscanf_s (address_string, "%p", &start_addr_p);
#endif

      memcpy (address_string, "0x", 2);
      memcpy (address_string + 2, end_addr, len);
      address_string[2 + len] = '\0';
#ifndef _UCRT
      sscanf (address_string, "%p", &end_addr_p);
#else
      sscanf_s (address_string, "%p", &end_addr_p);
#endif

      if (symbol >= start_addr_p && symbol < end_addr_p)
        {
          found = g_strdup (path);
          g_free (maps_line);
          break;
        }

      g_free (maps_line);
    }

  g_free (address_string);
  g_object_unref (data_input);

  return found;
#endif /* ! ENABLE_RELOCATABLE_RESOURCES || G_OS_WIN32 */
}


static gchar *exe = NULL;

static void set_gerror (GError **error, GimpBinrelocInitError errcode);


/* Initialize the BinReloc library (for applications).
 *
 * This function must be called before using any other BinReloc functions.
 * It attempts to locate the application's canonical filename.
 *
 * @note If you want to use BinReloc for a library, then you should call
 *       _gimp_reloc_init_lib() instead.
 * @note Initialization failure is not fatal. BinReloc functions will just
 *       fallback to the supplied default path.
 *
 * @param error  If BinReloc failed to initialize, then the error report will
 *               be stored in this variable. Set to NULL if you don't want an
 *               error report. See the #GimpBinrelocInitError for a list of error
 *               codes.
 *
 * @returns TRUE on success, FALSE if BinReloc failed to initialize.
 */
gboolean
_gimp_reloc_init (GError **error)
{
  GimpBinrelocInitError errcode;

  /* Shut up compiler warning about uninitialized variable. */
  errcode = GIMP_RELOC_INIT_ERROR_NOMEM;

  /* Locate the application's filename. */
  exe = _br_find_exe (&errcode);
  if (exe != NULL)
    /* Success! */
    return TRUE;
  else
    {
      /* Failed :-( */
      set_gerror (error, errcode);
      return FALSE;
    }
}


/* Initialize the BinReloc library (for libraries).
 *
 * This function must be called before using any other BinReloc functions.
 * It attempts to locate the calling library's canonical filename.
 *
 * @note The BinReloc source code MUST be included in your library, or this
 *       function won't work correctly.
 * @note Initialization failure is not fatal. BinReloc functions will just
 *       fallback to the supplied default path.
 *
 * @returns TRUE on success, FALSE if a filename cannot be found.
 */
gboolean
_gimp_reloc_init_lib (GError **error)
{
  GimpBinrelocInitError errcode;

  /* Shut up compiler warning about uninitialized variable. */
  errcode = GIMP_RELOC_INIT_ERROR_NOMEM;

  exe = _br_find_exe_for_symbol ((const void *) "", &errcode);
  if (exe != NULL)
    {
      /* Success! */
      return TRUE;
    }
  else
    {
      /* Failed :-( */
      set_gerror (error, errcode);
      return exe != NULL;
    }
}

static void
set_gerror (GError **error, GimpBinrelocInitError errcode)
{
  const gchar *error_message;

  if (error == NULL)
    return;

  switch (errcode)
    {
    case GIMP_RELOC_INIT_ERROR_NOMEM:
      error_message = "Cannot allocate memory.";
      break;
    case GIMP_RELOC_INIT_ERROR_OPEN_MAPS:
      error_message = "Unable to open /proc/self/maps for reading.";
      break;
    case GIMP_RELOC_INIT_ERROR_READ_MAPS:
      error_message = "Unable to read from /proc/self/maps.";
      break;
    case GIMP_RELOC_INIT_ERROR_INVALID_MAPS:
      error_message = "The file format of /proc/self/maps is invalid.";
      break;
    case GIMP_RELOC_INIT_ERROR_DISABLED:
      error_message = "Binary relocation support is disabled.";
      break;
    default:
      error_message = "Unknown error.";
      break;
    };
  g_set_error (error, g_quark_from_static_string ("GBinReloc"),
               errcode, "%s", error_message);
}


/* Locate the prefix in which the current application is installed.
 *
 * The prefix is generated by the following pseudo-code evaluation:
 * \code
 * dirname(dirname(exename))
 * \endcode
 *
 * @param default_prefix  A default prefix which will used as fallback.
 * @return A string containing the prefix, which must be freed when no
 *         longer necessary. If BinReloc is not initialized, or if the
 *         initialization function failed, then a copy of default_prefix
 *         will be returned. If default_prefix is NULL, then NULL will be
 *         returned.
 */
gchar *
_gimp_reloc_find_prefix (const gchar *default_prefix)
{
  gchar *dir1, *dir2;
  gchar *exe_dir;

  if (exe == NULL)
    {
      /* BinReloc not initialized. */
      if (default_prefix != NULL)
        return g_strdup (default_prefix);
      else
        return NULL;
    }

  dir1 = g_path_get_dirname (exe);
  dir2 = g_path_get_dirname (dir1);

  exe_dir = g_path_get_basename (dir1);
  if (g_strcmp0 (exe_dir, "bin") != 0 && ! g_str_has_prefix (exe_dir, "lib"))
    {
      g_free (exe_dir);
      exe_dir = g_path_get_basename (dir2);
      if (g_str_has_prefix (exe_dir, "lib"))
        {
          /* Supporting multiarch folders, such as lib/x86_64-linux-gnu/ */
          gchar *dir3 = g_path_get_dirname (dir2);

          g_free (dir2);
          dir2 = dir3;
        }
    }

  g_free (dir1);
  g_free (exe_dir);

  return dir2;
}

/* --- end libammoos/base/fieldbase/gimpreloc.c --- */

/* --- begin libammoos/base/fieldbase/gimpsignal.c --- */
/* LIBGIMP - The AmmoOS Image Library
 * Copyright (C) 1995-1997 Peter Mattis and Spencer Kimball
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
 *
 * $Revision$
 */

#include "config.h"

#define _GNU_SOURCE  /* for the sigaction stuff */

#include <glib.h>

#include "gimpsignal.h"


/**
 * SECTION: gimpsignal
 * @title: gimpsignal
 * @short_description: Portable signal handling.
 * @see_also: signal(2), signal(5 or 7), sigaction(2).
 *
 * Portable signal handling.
 **/


/* Courtesy of Austin Donnelly 06-04-2000 to address bug #2742 */

/**
 * gimp_signal_private: (skip)
 * @signum: Selects signal to be handled (see `man 7 signal`)
 * @handler: Handler that maps to signum. Invoked by O/S.
 *           Handler gets signal that caused invocation. Corresponds
 *           to the @sa_handler field of the @sigaction struct.
 * @flags: Preferences. OR'ed SA_&lt;xxx&gt;. See man sigaction. Corresponds
 *         to the @sa_flags field of the @sigaction struct.
 *
 * This function furnishes a workalike for signal(2) but
 * which internally invokes sigaction(2) after certain
 * sa_flags are set; these primarily to ensure restarting
 * of interrupted system calls. See sigaction(2)  It is a
 * aid to transition and not new development: that effort
 * should employ sigaction directly. [gosgood 18.04.2000]
 *
 * Cause @handler to be run when @signum is delivered.  We
 * use sigaction(2) rather than signal(2) so that we can control the
 * signal handler's environment completely via @flags: some signal(2)
 * implementations differ in their semantics, so we need to nail down
 * exactly what we want. [austin 06.04.2000]
 *
 * Returns: A reference to the signal handling function which was
 *          active before the call to gimp_signal_private().
 */
GimpSignalHandlerFunc
gimp_signal_private (gint                   signum,
                     GimpSignalHandlerFunc  handler,
                     gint                   flags)
{
#ifndef G_OS_WIN32
  gint ret;
  struct sigaction sa;
  struct sigaction osa;

  /*  The sa_handler (mandated by POSIX.1) and sa_sigaction (a
   *  common extension) are often implemented by the OS as members
   *  of a union.  This means you CAN NOT set both, you set one or
   *  the other.  Caveat programmer!
   */

  /*  Passing gimp_signal_private a gimp_sighandler of NULL is not
   *  an error, and generally results in the action for that signal
   *  being set to SIG_DFL (default behavior).  Many OSes define
   *  SIG_DFL as (void (*)()0, so setting sa_handler to NULL is
   *  the same thing as passing SIG_DFL to it.
   */
  sa.sa_handler = handler;

  /*  Mask all signals while handler runs to avoid re-entrancy
   *  problems.
   */
  sigfillset (&sa.sa_mask);

  sa.sa_flags = flags;

  ret = sigaction (signum, &sa, &osa);

  if (ret < 0)
    g_error ("unable to set handler for signal %d\n", signum);

  return (GimpSignalHandlerFunc) osa.sa_handler;
#else
  return NULL;                  /* Or g_error()? Should all calls to
                                 * this function really be inside
                                 * #ifdef G_OS_UNIX?
                                 */
#endif
}

/* --- end libammoos/base/fieldbase/gimpsignal.c --- */

/* --- begin libammoos/base/fieldbase/gimpunit.c --- */
/* LIBGIMP - The AmmoOS Image Library
 * Copyright (C) 1995-1997 Peter Mattis and Spencer Kimball
 *
 * gimpunit.c
 * Copyright (C) 2003 Michael Natterer <mitch@ammoos.org>
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

#include <math.h>
#include <string.h>

#include <gegl.h>
#include <gio/gio.h>
#include <glib-object.h>

#include "gimpbasetypes.h"

#include "gimpbase-private.h"
#include "gimpparamspecs.h"
#include "gimpunit.h"

#include "libgimp/libgimp-intl.h"


enum
{
  PROP_0,
  PROP_ID,
  PROP_NAME,
  PROP_FACTOR,
  PROP_DIGITS,
  PROP_SYMBOL,
  PROP_ABBREVIATION,
};

struct _GimpUnit
{
  GObject   parent_instance;

  gint      id;
  gchar    *name;

  gboolean  delete_on_exit;
  gdouble   factor;
  gint      digits;
  gchar    *symbol;
  gchar    *abbreviation;
};


typedef struct
{
  gdouble   factor;
  gint      digits;
  gchar    *identifier;
  gchar    *symbol;
  gchar    *abbreviation;
} GimpUnitDef;

/*  these are the built-in units
 */
static const GimpUnitDef _gimp_unit_defs[GIMP_UNIT_END] =
{
  /* pseudo unit */
  {
    0.0,  0,
    NC_("unit-plural", "pixels"),
    "px", "px",
  },

  /* standard units */
  {
    1.0,  2,
    NC_("unit-plural", "inches"),
    "''", "in",
  },

  {
    25.4, 1,
    NC_("unit-plural", "millimeters"),
    "mm", "mm",
  },

  /* professional units */
  {
    72.0, 0,
    NC_("unit-plural", "points"),
    "pt", "pt",
  },

  {
    6.0,  1,
    NC_("unit-plural", "picas"),
    "pc", "pc",
  }
};

/*  not a unit at all but kept here to have the strings in one place
 */
static const GimpUnitDef _gimp_unit_percent_def =
{
  0.0,  0,
  NC_("unit-plural", "percent"),
  "%",  "%",
};


static void       gimp_unit_constructed       (GObject             *object);
static void       gimp_unit_finalize          (GObject             *object);
static void       gimp_unit_set_property      (GObject             *object,
                                               guint                property_id,
                                               const GValue        *value,
                                               GParamSpec          *pspec);
static void       gimp_unit_get_property      (GObject             *object,
                                               guint                property_id,
                                               GValue              *value,
                                               GParamSpec          *pspec);

static gint       print                       (gchar               *buf,
                                               gint                 len,
                                               gint                 start,
                                               const gchar         *fmt,
                                               ...) G_GNUC_PRINTF (4, 5);


G_DEFINE_TYPE (GimpUnit, gimp_unit, G_TYPE_OBJECT)

#define parent_class gimp_unit_parent_class


static void
gimp_unit_class_init (GimpUnitClass *klass)
{
  GObjectClass *object_class = G_OBJECT_CLASS (klass);

  parent_class = g_type_class_peek_parent (klass);

  object_class->constructed  = gimp_unit_constructed;
  object_class->finalize     = gimp_unit_finalize;
  object_class->set_property = gimp_unit_set_property;
  object_class->get_property = gimp_unit_get_property;

  g_object_class_install_property (object_class, PROP_ID,
                                   g_param_spec_int ("id", NULL, NULL,
                                                     0, G_MAXINT, 0,
                                                     GIMP_PARAM_READWRITE |
                                                     G_PARAM_CONSTRUCT_ONLY));
  g_object_class_install_property (object_class, PROP_NAME,
                                   g_param_spec_string ("name", NULL, NULL,
                                                        NULL,
                                                        GIMP_PARAM_READWRITE |
                                                        G_PARAM_CONSTRUCT_ONLY));
  g_object_class_install_property (object_class, PROP_FACTOR,
                                   g_param_spec_double ("factor", NULL, NULL,
                                                        0.0, G_MAXDOUBLE, 1.0,
                                                        GIMP_PARAM_READWRITE |
                                                        G_PARAM_CONSTRUCT_ONLY));
  g_object_class_install_property (object_class, PROP_DIGITS,
                                   g_param_spec_int ("digits", NULL, NULL,
                                                     0, G_MAXINT, 0,
                                                     GIMP_PARAM_READWRITE |
                                                     G_PARAM_CONSTRUCT_ONLY));
  g_object_class_install_property (object_class, PROP_SYMBOL,
                                   g_param_spec_string ("symbol", NULL, NULL,
                                                        NULL,
                                                        GIMP_PARAM_READWRITE |
                                                        G_PARAM_CONSTRUCT_ONLY));
  g_object_class_install_property (object_class, PROP_ABBREVIATION,
                                   g_param_spec_string ("abbreviation", NULL, NULL,
                                                        NULL,
                                                        GIMP_PARAM_READWRITE |
                                                        G_PARAM_CONSTRUCT_ONLY));

  /*klass->id_table = gimp_id_table_new ();*/
}

static void
gimp_unit_init (GimpUnit *unit)
{
  unit->name         = NULL;
  unit->symbol       = NULL;
  unit->abbreviation = NULL;
}

static void
gimp_unit_constructed (GObject *object)
{
  G_OBJECT_CLASS (parent_class)->constructed (object);
}

static void
gimp_unit_finalize (GObject *object)
{
  GimpUnit *unit = GIMP_UNIT (object);

  g_free (unit->name);
  g_free (unit->symbol);
  g_free (unit->abbreviation);

  G_OBJECT_CLASS (parent_class)->finalize (object);
}

static void
gimp_unit_set_property (GObject      *object,
                        guint         property_id,
                        const GValue *value,
                        GParamSpec   *pspec)
{
  GimpUnit *unit = GIMP_UNIT (object);

  switch (property_id)
    {
    case PROP_ID:
      unit->id = g_value_get_int (value);
      break;
    case PROP_NAME:
      unit->name = g_value_dup_string (value);
      break;
    case PROP_FACTOR:
      unit->factor = g_value_get_double (value);
      break;
    case PROP_DIGITS:
      unit->digits = g_value_get_int (value);
      break;
    case PROP_SYMBOL:
      unit->symbol = g_value_dup_string (value);
      break;
    case PROP_ABBREVIATION:
      unit->abbreviation = g_value_dup_string (value);
      break;

    default:
      G_OBJECT_WARN_INVALID_PROPERTY_ID (object, property_id, pspec);
      break;
    }
}

static void
gimp_unit_get_property (GObject    *object,
                        guint       property_id,
                        GValue     *value,
                        GParamSpec *pspec)
{
  GimpUnit *unit = GIMP_UNIT (object);

  switch (property_id)
    {
    case PROP_ID:
      g_value_set_int (value, unit->id);
      break;
    case PROP_NAME:
      g_value_set_string (value, unit->name);
      break;
    case PROP_FACTOR:
      g_value_set_double (value, unit->factor);
      break;
    case PROP_DIGITS:
      g_value_set_int (value, unit->digits);
      break;
    case PROP_SYMBOL:
      g_value_set_string (value, unit->symbol);
      break;
    case PROP_ABBREVIATION:
      g_value_set_string (value, unit->abbreviation);
      break;

    default:
      G_OBJECT_WARN_INVALID_PROPERTY_ID (object, property_id, pspec);
      break;
    }
}

/* public functions */


/**
 * gimp_unit_get_id:
 * @unit: The unit you want to know the integer ID of.
 *
 * The ID can be used to retrieve the unit with [func@Unit.get_by_id].
 *
 * Note that this ID will be stable within a single session of AmmoOS Image, but
 * you should not expect this ID to stay the same across multiple runs.
 *
 * Returns: The unit's ID.
 **/
gint
gimp_unit_get_id (GimpUnit *unit)
{
  g_return_val_if_fail (GIMP_IS_UNIT (unit), -1);

  return unit->id;
}

/**
 * gimp_unit_get_name:
 * @unit: The unit you want to know the name of.
 *
 * This function returns the usual name of the unit (e.g. "inches").
 * It can be used as the long label for the unit in the interface.
 * For short labels, use [method@Unit.get_abbreviation].
 *
 * NOTE: This string must not be changed or freed.
 *
 * Returns: The unit's name.
 **/
const gchar *
gimp_unit_get_name (GimpUnit *unit)
{
  g_return_val_if_fail (GIMP_IS_UNIT (unit), NULL);

  return unit->name;
}

/**
 * gimp_unit_get_factor:
 * @unit: The unit you want to know the factor of.
 *
 * A #GimpUnit's @factor is defined to be:
 *
 * distance_in_units == (@factor * distance_in_inches)
 *
 * Returns 0 for @unit == GIMP_UNIT_PIXEL.
 *
 * Returns: The unit's factor.
 **/
gdouble
gimp_unit_get_factor (GimpUnit *unit)
{
  g_return_val_if_fail (GIMP_IS_UNIT (unit), 1.0);

  return unit->factor;
}

/**
 * gimp_unit_get_digits:
 * @unit: The unit you want to know the digits.
 *
 * Returns the number of digits set for @unit.
 * Built-in units' accuracy is approximately the same as an inch with
 * two digits. User-defined units can suggest a different accuracy.
 *
 * Note: the value is as-set by defaults or by the user and does not
 * necessary provide enough precision on high-resolution units.
 * When the information is needed for a specific unit, the use of
 * gimp_unit_get_scaled_digits() may be more appropriate.
 *
 * Returns 0 for @unit == GIMP_UNIT_PIXEL.
 *
 * Returns: The suggested number of digits.
 **/
gint
gimp_unit_get_digits (GimpUnit *unit)
{
  g_return_val_if_fail (GIMP_IS_UNIT (unit), 0);

  return unit->digits;
}

/**
 * gimp_unit_get_scaled_digits:
 * @unit: The unit you want to know the digits.
 * @resolution: the resolution in PPI.
 *
 * Returns the number of digits a @unit field should provide to get
 * enough accuracy so that every pixel position shows a different
 * value from neighboring pixels.
 *
 * Note: when needing digit accuracy to display a diagonal distance,
 * the @resolution may not correspond to the unit's horizontal or
 * vertical resolution, but instead to the result of:
 * `distance_in_pixel / distance_in_inch`.
 *
 * Returns: The suggested number of digits.
 **/
gint
gimp_unit_get_scaled_digits (GimpUnit *unit,
                             gdouble   resolution)
{
  gint digits;

  g_return_val_if_fail (GIMP_IS_UNIT (unit), 0);

  digits = ceil (log10 (1.0 /
                        gimp_pixels_to_units (1.0, unit, resolution)));

  return MAX (digits, gimp_unit_get_digits (unit));
}

/**
 * gimp_unit_get_symbol:
 * @unit: The unit you want to know the symbol of.
 *
 * This is e.g. "''" for UNIT_INCH.
 *
 * NOTE: This string must not be changed or freed.
 *
 * Returns: The unit's symbol.
 **/
const gchar *
gimp_unit_get_symbol (GimpUnit *unit)
{
  g_return_val_if_fail (GIMP_IS_UNIT (unit), NULL);

  return unit->symbol;
}

/**
 * gimp_unit_get_abbreviation:
 * @unit: The unit you want to know the abbreviation of.
 *
 * This function returns the abbreviation of the unit (e.g. "in" for
 * inches).
 * It can be used as a short label for the unit in the interface.
 * For long labels, use [method@Unit.get_name].
 *
 * NOTE: This string must not be changed or freed.
 *
 * Returns: The unit's abbreviation.
 **/
const gchar *
gimp_unit_get_abbreviation (GimpUnit *unit)
{
  g_return_val_if_fail (GIMP_IS_UNIT (unit), NULL);

  return unit->abbreviation;
}

/**
 * gimp_unit_get_deletion_flag:
 * @unit: The unit you want to know the @deletion_flag of.
 *
 * Returns: The unit's @deletion_flag.
 **/
gboolean
gimp_unit_get_deletion_flag (GimpUnit *unit)
{
  g_return_val_if_fail (GIMP_IS_UNIT (unit), TRUE);

  if ((unit->id >= 0 && unit->id < GIMP_UNIT_END) ||
      unit->id == GIMP_UNIT_PERCENT)
    return FALSE;

  if (_gimp_unit_vtable.get_deletion_flag != NULL)
    /* This code path will only happen in libgimp. */
    return _gimp_unit_vtable.get_deletion_flag (unit);
  else
    return unit->delete_on_exit;
}

/**
 * gimp_unit_set_deletion_flag:
 * @unit: The unit you want to set the @deletion_flag for.
 * @deletion_flag: The new deletion_flag.
 *
 * Sets a #GimpUnit's @deletion_flag. If the @deletion_flag of a unit is
 * %TRUE when AmmoOS Image exits, this unit will not be saved in the users's
 * "unitrc" file.
 *
 * Trying to change the @deletion_flag of a built-in unit will be silently
 * ignored.
 **/
void
gimp_unit_set_deletion_flag (GimpUnit *unit,
                             gboolean  deletion_flag)
{
  g_return_if_fail (GIMP_IS_UNIT (unit));

  if ((unit->id >= 0 && unit->id < GIMP_UNIT_END) ||
      unit->id == GIMP_UNIT_PERCENT)
    return;

  unit->delete_on_exit = deletion_flag;

  if (_gimp_unit_vtable.set_deletion_flag != NULL)
    /* This code path will only happen in libgimp. */
    _gimp_unit_vtable.set_deletion_flag (unit, deletion_flag);
}

/**
 * gimp_unit_get_by_id:
 * @unit_id: The unit id.
 *
 * Returns the unique [class@Unit] object corresponding to @unit_id,
 * which is the integer identifier as returned by [method@Unit.get_id].
 *
 * Returns: (transfer none): the #GimpUnit object with ID @unit_id.
 *
 * Since: 3.0
 **/
GimpUnit *
gimp_unit_get_by_id (gint unit_id)
{
  GimpUnit *unit = NULL;

  if (unit_id < 0)
    return NULL;

  if (G_UNLIKELY (! _gimp_units))
    _gimp_units = g_hash_table_new_full (g_direct_hash,
                                         g_direct_equal,
                                         NULL,
                                         (GDestroyNotify) g_object_unref);

  unit = g_hash_table_lookup (_gimp_units, GINT_TO_POINTER (unit_id));

  if (! unit)
    {
      if (unit_id < GIMP_UNIT_END)
        {
          GimpUnitDef def = _gimp_unit_defs[unit_id];

          unit = g_object_new (GIMP_TYPE_UNIT,
                               "id",           unit_id,
                               "name",         def.identifier,
                               "factor",       def.factor,
                               "digits",       def.digits,
                               "symbol",       def.symbol,
                               "abbreviation", def.abbreviation,
                               NULL);
          unit->delete_on_exit = FALSE;
        }
      else if (unit_id == GIMP_UNIT_PERCENT)
        {
          unit = g_object_new (GIMP_TYPE_UNIT,
                               "id",           unit_id,
                               "name",         _gimp_unit_percent_def.identifier,
                               "factor",       _gimp_unit_percent_def.factor,
                               "digits",       _gimp_unit_percent_def.digits,
                               "symbol",       _gimp_unit_percent_def.symbol,
                               "abbreviation", _gimp_unit_percent_def.abbreviation,
                               NULL);
          unit->delete_on_exit = FALSE;
        }
      else if (_gimp_unit_vtable.get_data != NULL)
        {
          /* This code path should never happen in app/ where get_data()
           * is NULL, because non built-in units are created in app/
           * whereas they are only queried in libgimp.
           */
          gchar   *identifier   = NULL;
          gdouble  factor;
          gint     digits;
          gchar   *symbol       = NULL;
          gchar   *abbreviation = NULL;

          identifier = _gimp_unit_vtable.get_data (unit_id,
                                                   &factor,
                                                   &digits,
                                                   &symbol,
                                                   &abbreviation);

          if (identifier != NULL)
            unit = g_object_new (GIMP_TYPE_UNIT,
                                 "id",           unit_id,
                                 "name",         identifier,
                                 "factor",       factor,
                                 "digits",       digits,
                                 "symbol",       symbol,
                                 "abbreviation", abbreviation,
                                 NULL);

          g_free (identifier);
          g_free (symbol);
          g_free (abbreviation);
        }
      else if (_gimp_unit_vtable.get_user_unit != NULL)
        {
          /* This code path should never happen in libgimp, only in app/. */

          unit = _gimp_unit_vtable.get_user_unit (unit_id);

          if (unit != NULL)
            g_object_ref (unit);
        }

      if (unit != NULL)
        g_hash_table_insert (_gimp_units, GINT_TO_POINTER (unit_id), unit);
    }

  return unit;
}

/**
 * gimp_unit_pixel:
 *
 * Returns the unique object representing pixel unit.
 *
 * This procedure returns the unit representing pixel. The returned
 * object is unique across the whole run.
 *
 * Returns: (transfer none): The unique pixel unit.
 *
 * Since: 3.0
 **/
GimpUnit *
gimp_unit_pixel (void)
{
  return gimp_unit_get_by_id (GIMP_UNIT_PIXEL);
}

/**
 * gimp_unit_inch:
 *
 * Returns the unique object representing inch unit.
 *
 * This procedure returns the unit representing inch. The returned
 * object is unique across the whole run.
 *
 * Returns: (transfer none): The unique inch unit.
 *
 * Since: 3.0
 **/
GimpUnit *
gimp_unit_inch (void)
{
  return gimp_unit_get_by_id (GIMP_UNIT_INCH);
}

/**
 * gimp_unit_mm:
 *
 * Returns the unique object representing millimeter unit.
 *
 * This procedure returns the unit representing millimeter. The
 * returned object is unique across the whole run.
 *
 * Returns: (transfer none): The unique millimeter unit.
 *
 * Since: 3.0
 **/
GimpUnit *
gimp_unit_mm (void)
{
  return gimp_unit_get_by_id (GIMP_UNIT_MM);
}

/**
 * gimp_unit_point:
 *
 * Returns the unique object representing typographical point unit.
 *
 * This procedure returns the unit representing typographical points.
 * The returned object is unique across the whole run.
 *
 * Returns: (transfer none): The unique point unit.
 *
 * Since: 3.0
 **/
GimpUnit *
gimp_unit_point (void)
{
  return gimp_unit_get_by_id (GIMP_UNIT_POINT);
}

/**
 * gimp_unit_pica:
 *
 * Returns the unique object representing Pica unit.
 *
 * This procedure returns the unit representing Picas.
 * The returned object is unique across the whole run.
 *
 * Returns: (transfer none): The unique pica unit.
 *
 * Since: 3.0
 **/
GimpUnit *
gimp_unit_pica (void)
{
  return gimp_unit_get_by_id (GIMP_UNIT_PICA);
}

/**
 * gimp_unit_percent:
 *
 * Returns the unique object representing percent dimensions relatively
 * to an image.
 *
 * This procedure returns the unit representing typographical points.
 * The returned object is unique across the whole run.
 *
 * Returns: (transfer none): The unique percent unit.
 *
 * Since: 3.0
 **/
GimpUnit *
gimp_unit_percent (void)
{
  return gimp_unit_get_by_id (GIMP_UNIT_PERCENT);
}

/**
 * gimp_unit_is_built_in:
 * @unit: the unit.
 *
 * Returns whether the unit is built-in.
 *
 * This procedure returns @unit is a built-in unit. In particular the
 * deletion flag cannot be set on built-in units.
 *
 * Returns: Whether @unit is built-in.
 *
 * Since: 3.0
 **/
gboolean
gimp_unit_is_built_in (GimpUnit *unit)
{
  g_return_val_if_fail (GIMP_IS_UNIT (unit), FALSE);

  return (unit->id >= 0 && unit->id < GIMP_UNIT_END) || unit->id == GIMP_UNIT_PERCENT;
}

/**
 * gimp_unit_is_metric:
 * @unit: The unit
 *
 * Checks if the given @unit is metric. A simplistic test is used
 * that looks at the unit's factor and checks if it is 2.54 multiplied
 * by some common powers of 10. Currently it checks for mm, cm, dm, m.
 *
 * See also: gimp_unit_get_factor()
 *
 * Returns: %TRUE if the @unit is metric.
 *
 * Since: 2.10
 **/
gboolean
gimp_unit_is_metric (GimpUnit *unit)
{
  gdouble factor;

  if (unit == gimp_unit_mm ())
    return TRUE;

  factor = gimp_unit_get_factor (unit);

  if (factor == 0.0)
    return FALSE;

  return ((ABS (factor -  0.0254) < 1e-7) || /* m  */
          (ABS (factor -  0.254)  < 1e-6) || /* dm */
          (ABS (factor -  2.54)   < 1e-5) || /* cm */
          (ABS (factor - 25.4)    < 1e-4));  /* mm */
}

/**
 * gimp_unit_format_string:
 * @format: A printf-like format string which is used to create the unit
 *          string.
 * @unit:   A unit.
 *
 * The @format string supports the following percent expansions:
 *
 * * `%n`: Name (long label)
 * * `%a`: Abbreviation (short label)
 * * `%%`: Literal percent
 * * `%f`: Factor (how many units make up an inch)
 * * `%y`: Symbol (e.g. `''` for `GIMP_UNIT_INCH`)
 *
 * Returns: (transfer full): A newly allocated string with above percent
 *          expressions replaced with the resp. strings for @unit.
 *
 * Since: 2.8
 **/
gchar *
gimp_unit_format_string (const gchar *format,
                         GimpUnit    *unit)
{
  gchar buffer[1024];
  gint  i = 0;

  g_return_val_if_fail (GIMP_IS_UNIT (unit), NULL);
  g_return_val_if_fail (format != NULL, NULL);

  while (i < (sizeof (buffer) - 1) && *format)
    {
      switch (*format)
        {
        case '%':
          format++;
          switch (*format)
            {
            case 0:
              g_warning ("%s: unit-menu-format string ended within %%-sequence",
                         G_STRFUNC);
              break;

            case '%':
              buffer[i++] = '%';
              break;

            case 'f': /* factor (how many units make up an inch) */
              i += print (buffer, sizeof (buffer), i, "%f",
                          gimp_unit_get_factor (unit));
              break;

            case 'y': /* symbol ("''" for inch) */
              i += print (buffer, sizeof (buffer), i, "%s",
                          gimp_unit_get_symbol (unit));
              break;

            case 'a': /* abbreviation */
              i += print (buffer, sizeof (buffer), i, "%s",
                          gimp_unit_get_abbreviation (unit));
              break;

            case 'n': /* full name */
              i += print (buffer, sizeof (buffer), i, "%s",
                          gimp_unit_get_name (unit));
              break;

            default:
              g_warning ("%s: unit-menu-format contains unknown format "
                         "sequence '%%%c'", G_STRFUNC, *format);
              break;
            }
          break;

        default:
          buffer[i++] = *format;
          break;
        }

      format++;
    }

  buffer[MIN (i, sizeof (buffer) - 1)] = 0;

  return g_strdup (buffer);
}

/**
 * gimp_pixels_to_units:
 * @pixels:     value in pixels
 * @unit:       unit to convert to
 * @resolution: resolution in DPI
 *
 * Converts a @value specified in pixels to @unit.
 *
 * Returns: @pixels converted to units.
 *
 * Since: 2.8
 **/
gdouble
gimp_pixels_to_units (gdouble   pixels,
                      GimpUnit *unit,
                      gdouble   resolution)
{
  g_return_val_if_fail (gimp_unit_pixel != NULL, 0.0);

  if (unit == gimp_unit_pixel ())
    return pixels;

  return pixels * gimp_unit_get_factor (unit) / resolution;
}

/**
 * gimp_units_to_pixels:
 * @value:      value in units
 * @unit:       unit of @value
 * @resolution: resolution in DPI
 *
 * Converts a @value specified in @unit to pixels.
 *
 * Returns: @value converted to pixels.
 *
 * Since: 2.8
 **/
gdouble
gimp_units_to_pixels (gdouble   value,
                      GimpUnit *unit,
                      gdouble   resolution)
{
  g_return_val_if_fail (gimp_unit_pixel != NULL, 0.0);

  if (unit == gimp_unit_pixel ())
    return value;

  return value * resolution / gimp_unit_get_factor (unit);
}

/**
 * gimp_units_to_points:
 * @value:      value in units
 * @unit:       unit of @value
 * @resolution: resolution in DPI
 *
 * Converts a @value specified in @unit to points.
 *
 * Returns: @value converted to points.
 *
 * Since: 2.8
 **/
gdouble
gimp_units_to_points (gdouble   value,
                      GimpUnit *unit,
                      gdouble   resolution)
{
  g_return_val_if_fail (gimp_unit_pixel != NULL, 0.0);
  g_return_val_if_fail (gimp_unit_point != NULL, 0.0);

  if (unit == gimp_unit_point ())
    return value;

  if (unit == gimp_unit_pixel ())
    return (value * gimp_unit_get_factor (gimp_unit_point ()) / resolution);

  return (value *
          gimp_unit_get_factor (gimp_unit_point ()) / gimp_unit_get_factor (unit));
}


/*
 * GIMP_TYPE_PARAM_UNIT
 */

#define GIMP_PARAM_SPEC_UNIT(pspec)    (G_TYPE_CHECK_INSTANCE_CAST ((pspec), GIMP_TYPE_PARAM_UNIT, GimpParamSpecUnit))

typedef struct _GimpParamSpecUnit GimpParamSpecUnit;

struct _GimpParamSpecUnit
{
  GimpParamSpecObject  parent_instance;

  gboolean             allow_pixel;
  gboolean             allow_percent;
};

static void         gimp_param_unit_class_init  (GimpParamSpecObjectClass *klass);
static void         gimp_param_unit_init        (GParamSpec               *pspec);
static GParamSpec * gimp_param_unit_duplicate   (GParamSpec               *pspec);
static gboolean     gimp_param_unit_validate    (GParamSpec               *pspec,
                                                 GValue                   *value);

/**
 * gimp_param_unit_get_type:
 *
 * Reveals the object type
 *
 * Returns: the #GType for a unit param object
 *
 * Since: 2.4
 **/
GType
gimp_param_unit_get_type (void)
{
  static GType type = 0;

  if (! type)
    {
      const GTypeInfo info =
      {
        sizeof (GimpParamSpecObjectClass),
        NULL, NULL,
        (GClassInitFunc) gimp_param_unit_class_init,
        NULL, NULL,
        sizeof (GimpParamSpecUnit),
        0,
        (GInstanceInitFunc) gimp_param_unit_init
      };

      type = g_type_register_static (GIMP_TYPE_PARAM_OBJECT,
                                     "GimpParamUnit", &info, 0);
    }

  return type;
}

static void
gimp_param_unit_class_init (GimpParamSpecObjectClass *klass)
{
  GParamSpecClass *pclass = G_PARAM_SPEC_CLASS (klass);

  klass->duplicate          = gimp_param_unit_duplicate;

  pclass->value_type        = GIMP_TYPE_UNIT;
  pclass->value_validate    = gimp_param_unit_validate;
}

static void
gimp_param_unit_init (GParamSpec *pspec)
{
  GimpParamSpecUnit   *uspec = GIMP_PARAM_SPEC_UNIT (pspec);
  GimpParamSpecObject *ospec = GIMP_PARAM_SPEC_OBJECT (pspec);

  uspec->allow_pixel    = TRUE;
  uspec->allow_percent  = TRUE;
  ospec->_default_value = g_object_ref (G_OBJECT (gimp_unit_inch ()));
  ospec->_has_default   = TRUE;
}

static GParamSpec *
gimp_param_unit_duplicate (GParamSpec *pspec)
{
  GParamSpec        *duplicate;
  GimpParamSpecUnit *uspec;

  g_return_val_if_fail (GIMP_IS_PARAM_SPEC_UNIT (pspec), NULL);

  uspec = GIMP_PARAM_SPEC_UNIT (pspec);
  duplicate = gimp_param_spec_unit (pspec->name,
                                    g_param_spec_get_nick (pspec),
                                    g_param_spec_get_blurb (pspec),
                                    uspec->allow_pixel,
                                    uspec->allow_percent,
                                    GIMP_UNIT (gimp_param_spec_object_get_default (pspec)),
                                    pspec->flags);

  return duplicate;
}

static gboolean
gimp_param_unit_validate (GParamSpec *pspec,
                          GValue     *value)
{
  GimpParamSpecUnit *uspec = GIMP_PARAM_SPEC_UNIT (pspec);
  GObject            *unit = value->data[0].v_pointer;

  if (unit == NULL                                                                 ||
      (! uspec->allow_percent && value->data[0].v_pointer == gimp_unit_percent ()) ||
      (! uspec->allow_pixel   && value->data[0].v_pointer == gimp_unit_pixel ()))
    {
      g_clear_object (&unit);
      value->data[0].v_pointer = g_object_ref (gimp_param_spec_object_get_default (pspec));
      return TRUE;
    }

  return FALSE;
}

/**
 * gimp_param_spec_unit:
 * @name:          Canonical name of the param
 * @nick:          Nickname of the param
 * @blurb:         Brief description of param.
 * @allow_pixel:   Whether "pixels" is an allowed unit.
 * @allow_percent: Whether "percent" is an allowed unit.
 * @default_value: Unit to use if none is assigned.
 * @flags:         a combination of #GParamFlags
 *
 * Creates a param spec to hold a units param.
 * See g_param_spec_internal() for more information.
 *
 * Returns: (transfer full): a newly allocated #GParamSpec instance
 *
 * Since: 2.4
 **/
GParamSpec *
gimp_param_spec_unit (const gchar *name,
                      const gchar *nick,
                      const gchar *blurb,
                      gboolean     allow_pixel,
                      gboolean     allow_percent,
                      GimpUnit    *default_value,
                      GParamFlags  flags)
{
  GimpParamSpecUnit *uspec;

  g_return_val_if_fail (GIMP_IS_UNIT (default_value), NULL);

  uspec = g_param_spec_internal (GIMP_TYPE_PARAM_UNIT,
                                 name, nick, blurb, flags);

  g_return_val_if_fail (uspec, NULL);

  uspec->allow_pixel   = allow_pixel;
  uspec->allow_percent = allow_percent;
  gimp_param_spec_object_set_default (G_PARAM_SPEC (uspec), G_OBJECT (default_value));

  return G_PARAM_SPEC (uspec);
}

/**
 * gimp_param_spec_unit_pixel_allowed:
 * @pspec: a #GParamSpec to hold an #GimpUnit value.
 *
 * Returns: %TRUE if the [func@Gimp.Unit.pixel] unit is allowed.
 *
 * Since: 3.0
 **/
gboolean
gimp_param_spec_unit_pixel_allowed (GParamSpec *pspec)
{
  g_return_val_if_fail (GIMP_IS_PARAM_SPEC_UNIT (pspec), FALSE);

  return GIMP_PARAM_SPEC_UNIT (pspec)->allow_pixel;
}

/**
 * gimp_param_spec_unit_percent_allowed:
 * @pspec: a #GParamSpec to hold an #GimpUnit value.
 *
 * Returns: %TRUE if the [func@Gimp.Unit.percent] unit is allowed.
 *
 * Since: 3.0
 **/
gboolean
gimp_param_spec_unit_percent_allowed (GParamSpec *pspec)
{
  g_return_val_if_fail (GIMP_IS_PARAM_SPEC_UNIT (pspec), FALSE);

  return GIMP_PARAM_SPEC_UNIT (pspec)->allow_percent;
}

static gint
print (gchar       *buf,
       gint         len,
       gint         start,
       const gchar *fmt,
       ...)
{
  va_list args;
  gint printed;

  va_start (args, fmt);

  printed = g_vsnprintf (buf + start, len - start, fmt, args);
  if (printed < 0)
    printed = len - start;

  va_end (args);

  return printed;
}

/* --- end libammoos/base/fieldbase/gimpunit.c --- */

/* --- begin libammoos/base/fieldbase/gimputils.c --- */
/* LIBGIMP - The AmmoOS Image Library
 * Copyright (C) 1995-1997 Spencer Kimball and Peter Mattis
 *
 * gimputils.c
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
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library.  If not, see
 * <https://www.gnu.org/licenses/>.
 */

#include "config.h"

#include <stdlib.h>
#include <string.h>
#include <stdio.h>

#ifdef PLATFORM_OSX
#include <AppKit/AppKit.h>
#include <libunwind.h>
#endif

#ifdef HAVE_EXECINFO_H
/* Allowing backtrace() API. */
#include <execinfo.h>
#endif

#include <gio/gio.h>
#include <glib/gprintf.h>

#if defined(G_OS_WIN32)
# include <windows.h>
# include <shlobj.h>

#else /* G_OS_WIN32 */

/* For waitpid() */
#include <sys/wait.h>
#include <unistd.h>
#include <errno.h>

/* For thread IDs. */
#include <sys/types.h>
#include <sys/syscall.h>

#ifdef HAVE_SYS_PRCTL_H
#include <sys/prctl.h>
#endif

#ifdef HAVE_SYS_THR_H
#include <sys/thr.h>
#endif

#endif /* G_OS_WIN32 */

#include "gimpbasetypes.h"
#include "gimputils.h"
#include "gimpversion-private.h"

#include "libgimp/libgimp-intl.h"


/**
 * SECTION: gimputils
 * @title: gimputils
 * @short_description: Utilities of general interest
 *
 * Utilities of general interest
 **/

#ifndef G_OS_WIN32
static gboolean gimp_utils_generic_available (const gchar *program,
                                              gint         major,
                                              gint         minor);
static gboolean gimp_utils_gdb_available     (gint         major,
                                              gint         minor);
#endif

/**
 * gimp_utf8_strtrim:
 * @str: (nullable): an UTF-8 encoded string (or %NULL)
 * @max_chars: the maximum number of characters before the string get
 * trimmed
 *
 * Creates a (possibly trimmed) copy of @str. The string is cut if it
 * exceeds @max_chars characters or on the first newline. The fact
 * that the string was trimmed is indicated by appending an ellipsis.
 *
 * Returns: A (possibly trimmed) copy of @str which should be freed
 * using g_free() when it is not needed any longer.
 **/
gchar *
gimp_utf8_strtrim (const gchar *str,
                   gint         max_chars)
{
  /* FIXME: should we make this translatable? */
  const gchar ellipsis[] = "...";
  const gint  e_len      = strlen (ellipsis);

  if (str)
    {
      const gchar *p;
      const gchar *newline = NULL;
      gint         chars   = 0;
      gunichar     unichar;

      for (p = str; *p; p = g_utf8_next_char (p))
        {
          if (++chars > max_chars)
            break;

          unichar = g_utf8_get_char (p);

          switch (g_unichar_break_type (unichar))
            {
            case G_UNICODE_BREAK_MANDATORY:
            case G_UNICODE_BREAK_LINE_FEED:
              newline = p;
              break;
            default:
              continue;
            }

          break;
        }

      if (*p)
        {
          gsize  len     = p - str;
          gchar *trimmed = g_new (gchar, len + e_len + 2);

          memcpy (trimmed, str, len);
          if (newline)
            trimmed[len++] = ' ';

          g_strlcpy (trimmed + len, ellipsis, e_len + 1);

          return trimmed;
        }

      return g_strdup (str);
    }

  return NULL;
}

/**
 * gimp_any_to_utf8: (skip)
 * @str: (array length=len): The string to be converted to UTF-8.
 * @len:            The length of the string, or -1 if the string
 *                  is nul-terminated.
 * @warning_format: The message format for the warning message if conversion
 *                  to UTF-8 fails. See the <function>printf()</function>
 *                  documentation.
 * @...:            The parameters to insert into the format string.
 *
 * This function takes any string (UTF-8 or not) and always returns a valid
 * UTF-8 string.
 *
 * If @str is valid UTF-8, a copy of the string is returned.
 *
 * If UTF-8 validation fails, g_locale_to_utf8() is tried and if it
 * succeeds the resulting string is returned.
 *
 * Otherwise, the portion of @str that is UTF-8, concatenated
 * with "(invalid UTF-8 string)" is returned. If not even the start
 * of @str is valid UTF-8, only "(invalid UTF-8 string)" is returned.
 *
 * Returns: The UTF-8 string as described above.
 **/
gchar *
gimp_any_to_utf8 (const gchar  *str,
                  gssize        len,
                  const gchar  *warning_format,
                  ...)
{
  const gchar *start_invalid;
  gchar       *utf8;

  g_return_val_if_fail (str != NULL, NULL);

  if (g_utf8_validate (str, len, &start_invalid))
    {
      if (len < 0)
        utf8 = g_strdup (str);
      else
        utf8 = g_strndup (str, len);
    }
  else
    {
      utf8 = g_locale_to_utf8 (str, len, NULL, NULL, NULL);
    }

  if (! utf8)
    {
      if (warning_format)
        {
          va_list warning_args;

          va_start (warning_args, warning_format);

          g_logv (G_LOG_DOMAIN, G_LOG_LEVEL_MESSAGE,
                  warning_format, warning_args);

          va_end (warning_args);
        }

      if (start_invalid > str)
        {
          gchar *tmp;

          tmp = g_strndup (str, start_invalid - str);
          utf8 = g_strconcat (tmp, " ", _("(invalid UTF-8 string)"), NULL);
          g_free (tmp);
        }
      else
        {
          utf8 = g_strdup (_("(invalid UTF-8 string)"));
        }
    }

  return utf8;
}

/**
 * gimp_filename_to_utf8:
 * @filename: The filename to be converted to UTF-8.
 *
 * Convert a filename in the filesystem's encoding to UTF-8
 * temporarily.  The return value is a pointer to a string that is
 * guaranteed to be valid only during the current iteration of the
 * main loop or until the next call to gimp_filename_to_utf8().
 *
 * The only purpose of this function is to provide an easy way to pass
 * a filename in the filesystem encoding to a function that expects an
 * UTF-8 encoded filename.
 *
 * Returns: A temporarily valid UTF-8 representation of @filename.
 *               This string must not be changed or freed.
 **/
const gchar *
gimp_filename_to_utf8 (const gchar *filename)
{
  /* Simpleminded implementation, but at least allocates just one copy
   * of each translation. Could check if already UTF-8, and if so
   * return filename as is. Could perhaps (re)use a suitably large
   * cyclic buffer, but then would have to verify that all calls
   * really need the return value just for a "short" time.
   */

  static GHashTable *ht = NULL;
  gchar             *filename_utf8;

  if (! filename)
    return NULL;

  if (! ht)
    ht = g_hash_table_new (g_str_hash, g_str_equal);

  filename_utf8 = g_hash_table_lookup (ht, filename);

  if (! filename_utf8)
    {
      filename_utf8 = g_filename_display_name (filename);
      g_hash_table_insert (ht, g_strdup (filename), filename_utf8);
    }

  return filename_utf8;
}

/**
 * gimp_file_get_utf8_name:
 * @file: a #GFile
 *
 * This function works like gimp_filename_to_utf8() and returns
 * a UTF-8 encoded string that does not need to be freed.
 *
 * It converts a #GFile's path or uri to UTF-8 temporarily.  The
 * return value is a pointer to a string that is guaranteed to be
 * valid only during the current iteration of the main loop or until
 * the next call to gimp_file_get_utf8_name().
 *
 * The only purpose of this function is to provide an easy way to pass
 * a #GFile's name to a function that expects an UTF-8 encoded string.
 *
 * See g_file_get_parse_name().
 *
 * Since: 2.10
 *
 * Returns: A temporarily valid UTF-8 representation of @file's name.
 *               This string must not be changed or freed.
 **/
const gchar *
gimp_file_get_utf8_name (GFile *file)
{
  gchar *name;

  g_return_val_if_fail (G_IS_FILE (file), NULL);

  name = g_file_get_parse_name (file);

  g_object_set_data_full (G_OBJECT (file), "ammoos-parse-name", name,
                          (GDestroyNotify) g_free);

  return name;
}

/**
 * gimp_file_has_extension:
 * @file:      a #GFile
 * @extension: an ASCII extension
 *
 * This function checks if @file's URI ends with @extension. It behaves
 * like g_str_has_suffix() on g_file_get_uri(), except that the string
 * comparison is done case-insensitively using g_ascii_strcasecmp().
 *
 * Since: 2.10
 *
 * Returns: %TRUE if @file's URI ends with @extension,
 *               %FALSE otherwise.
 **/
gboolean
gimp_file_has_extension (GFile       *file,
                         const gchar *extension)
{
  gchar    *uri;
  gint      uri_len;
  gint      ext_len;
  gboolean  result = FALSE;

  g_return_val_if_fail (G_IS_FILE (file), FALSE);
  g_return_val_if_fail (extension != NULL, FALSE);

  uri = g_file_get_uri (file);

  uri_len = strlen (uri);
  ext_len = strlen (extension);

  if (uri_len && ext_len && (uri_len > ext_len))
    {
      if (g_ascii_strcasecmp (uri + uri_len - ext_len, extension) == 0)
        result = TRUE;
    }

  g_free (uri);

  return result;
}

/**
 * gimp_file_show_in_file_manager:
 * @file:  a #GFile
 * @error: return location for a #GError
 *
 * Shows @file in the system file manager.
 *
 * Since: 2.10
 *
 * Returns: %TRUE on success, %FALSE otherwise. On %FALSE, @error
 *               is set.
 **/
gboolean
gimp_file_show_in_file_manager (GFile   *file,
                                GError **error)
{
  g_return_val_if_fail (G_IS_FILE (file), FALSE);
  g_return_val_if_fail (error == NULL || *error == NULL, FALSE);

#if defined(G_OS_WIN32)

  {
    gboolean ret;
    char *filename;
    LPWSTR w_filename = NULL;
    ITEMIDLIST *pidl = NULL;

    ret = FALSE;

    /* Calling this function multiple times should do no harm, but it is
       easier to put this here as it needs linking against ole32. */
    if (FAILED (CoInitialize (NULL)))
      return ret;

    filename = g_file_get_path (file);
    if (!filename)
      {
        g_set_error_literal (error, G_FILE_ERROR, 0,
                             _("File path is NULL"));
        goto out;
      }

    w_filename = g_utf8_to_utf16 (filename, -1, NULL, NULL, NULL);
    if (!w_filename)
      {
        g_set_error_literal (error, G_FILE_ERROR, 0,
                             _("Error converting UTF-8 filename to wide char"));
        goto out;
      }

    pidl = (ITEMIDLIST *) ILCreateFromPathW (w_filename);
    if (!pidl)
      {
        g_set_error_literal (error, G_FILE_ERROR, 0,
                             _("ILCreateFromPath() failed"));
        goto out;
      }

    SHOpenFolderAndSelectItems (pidl, 0, NULL, 0);
    ret = TRUE;

  out:
    if (pidl)
      ILFree (pidl);
    g_free (w_filename);
    g_free (filename);

    CoUninitialize ();

    return ret;
  }

#elif defined(PLATFORM_OSX)

  {
    gchar    *uri;
    NSString *filename;
    NSURL    *url;
    gboolean  retval = TRUE;

    uri = g_file_get_uri (file);
    filename = [NSString stringWithUTF8String:uri];

    url = [NSURL URLWithString:filename];
    if (url)
      {
        NSArray *url_array = [NSArray arrayWithObject:url];

        [[NSWorkspace sharedWorkspace] activateFileViewerSelectingURLs:url_array];
      }
    else
      {
        g_set_error (error, G_FILE_ERROR, 0,
                     _("Cannot convert '%s' into a valid NSURL."), uri);
        retval = FALSE;
      }

    g_free (uri);

    return retval;
  }

#else /* UNIX */

  {
    GDBusProxy      *proxy;
    GVariant        *retval;
    GVariantBuilder *builder;
    gchar           *uri;

    proxy = g_dbus_proxy_new_for_bus_sync (G_BUS_TYPE_SESSION,
                                           G_DBUS_PROXY_FLAGS_NONE,
                                           NULL,
                                           "org.freedesktop.FileManager1",
                                           "/org/freedesktop/FileManager1",
                                           "org.freedesktop.FileManager1",
                                           NULL, error);

    if (! proxy)
      {
        g_prefix_error (error,
                        _("Connecting to org.freedesktop.FileManager1 failed: "));
        return FALSE;
      }

    uri = g_file_get_uri (file);

    builder = g_variant_builder_new (G_VARIANT_TYPE ("as"));
    g_variant_builder_add (builder, "s", uri);

    g_free (uri);

    retval = g_dbus_proxy_call_sync (proxy,
                                     "ShowItems",
                                     g_variant_new ("(ass)",
                                                    builder,
                                                    ""),
                                     G_DBUS_CALL_FLAGS_NONE,
                                     -1, NULL, error);

    g_variant_builder_unref (builder);
    g_object_unref (proxy);

    if (! retval)
      {
        g_prefix_error (error, _("Calling ShowItems failed: "));
        return FALSE;
      }

    g_variant_unref (retval);

    return TRUE;
  }

#endif
}

/**
 * gimp_strip_uline:
 * @str: (nullable): underline infested string (or %NULL)
 *
 * This function returns a copy of @str stripped of underline
 * characters. This comes in handy when needing to strip mnemonics
 * from menu paths etc.
 *
 * In some languages, mnemonics are handled by adding the mnemonic
 * character in brackets (like "File (_F)"). This function recognizes
 * this construct and removes the whole bracket construction to get
 * rid of the mnemonic (see bug 157561).
 *
 * Returns: A (possibly stripped) copy of @str which should be
 *               freed using g_free() when it is not needed any longer.
 **/
gchar *
gimp_strip_uline (const gchar *str)
{
  gchar    *escaped;
  gchar    *p;
  gboolean  past_bracket = FALSE;

  if (! str)
    return NULL;

  p = escaped = g_strdup (str);

  while (*str)
    {
      if (*str == '_')
        {
          /*  "__" means a literal "_" in the menu path  */
          if (str[1] == '_')
            {
             *p++ = *str++;
             str++;
             continue;
            }

          /*  find the "(_X)" construct and remove it entirely  */
          if (past_bracket && str[1] && *(g_utf8_next_char (str + 1)) == ')')
            {
              str = g_utf8_next_char (str + 1) + 1;
              p--;
            }
          else
            {
              str++;
            }
        }
      else
        {
          past_bracket = (*str == '(');

          *p++ = *str++;
        }
    }

  *p = '\0';

  return escaped;
}

/**
 * gimp_escape_uline:
 * @str: (nullable): Underline infested string (or %NULL)
 *
 * This function returns a copy of @str with all underline converted
 * to two adjacent underlines. This comes in handy when needing to display
 * strings with underlines (like filenames) in a place that would convert
 * them to mnemonics.
 *
 * Returns: A (possibly escaped) copy of @str which should be
 * freed using g_free() when it is not needed any longer.
 *
 * Since: 2.2
 **/
gchar *
gimp_escape_uline (const gchar *str)
{
  gchar *escaped;
  gchar *p;
  gint   n_ulines = 0;

  if (! str)
    return NULL;

  for (p = (gchar *) str; *p; p++)
    if (*p == '_')
      n_ulines++;

  p = escaped = g_malloc (strlen (str) + n_ulines + 1);

  while (*str)
    {
      if (*str == '_')
        *p++ = '_';

      *p++ = *str++;
    }

  *p = '\0';

  return escaped;
}

/**
 * gimp_is_canonical_identifier:
 * @identifier: The identifier string to check.
 *
 * Checks if @identifier is canonical and non-%NULL.
 *
 * Canonical identifiers are e.g. expected by the PDB for procedure
 * and parameter names. Every character of the input string must be
 * either '-', 'a-z', 'A-Z' or '0-9'.
 *
 * Returns: %TRUE if @identifier is canonical, %FALSE otherwise.
 *
 * Since: 3.0
 **/
gboolean
gimp_is_canonical_identifier (const gchar *identifier)
{
  if (identifier)
    {
      const gchar *p;

      for (p = identifier; *p != 0; p++)
        {
          const gchar c = *p;

          if (! (c == '-' ||
                 (c >= '0' && c <= '9') ||
                 (c >= 'A' && c <= 'Z') ||
                 (c >= 'a' && c <= 'z')))
            {
              return FALSE;
            }
        }

      return TRUE;
    }

  return FALSE;
}

/**
 * gimp_canonicalize_identifier:
 * @identifier: The identifier string to canonicalize.
 *
 * Turns any input string into a canonicalized string.
 *
 * Canonical identifiers are e.g. expected by the PDB for procedure
 * and parameter names. Every character of the input string that is
 * not either '-', 'a-z', 'A-Z' or '0-9' will be replaced by a '-'.
 *
 * Returns: The canonicalized identifier. This is a newly allocated
 *          string that should be freed with g_free() when no longer
 *          needed.
 *
 * Since: 2.4
 **/
gchar *
gimp_canonicalize_identifier (const gchar *identifier)
{
  gchar *canonicalized = NULL;

  if (identifier)
    {
      gchar *p;

      canonicalized = g_strdup (identifier);

      for (p = canonicalized; *p != 0; p++)
        {
          gchar c = *p;

          if (c != '-' &&
              (c < '0' || c > '9') &&
              (c < 'A' || c > 'Z') &&
              (c < 'a' || c > 'z'))
            {
              *p = '-';
            }
        }
    }

  return canonicalized;
}

/**
 * gimp_enum_get_desc:
 * @enum_class: a #GEnumClass
 * @value:      a value from @enum_class
 *
 * Retrieves #GimpEnumDesc associated with the given value, or %NULL.
 *
 * Returns: (nullable): the value's #GimpEnumDesc.
 *
 * Since: 2.2
 **/
const GimpEnumDesc *
gimp_enum_get_desc (GEnumClass *enum_class,
                    gint        value)
{
  const GimpEnumDesc *value_desc;

  g_return_val_if_fail (G_IS_ENUM_CLASS (enum_class), NULL);

  value_desc =
    gimp_enum_get_value_descriptions (G_TYPE_FROM_CLASS (enum_class));

  if (value_desc)
    {
      while (value_desc->value_desc)
        {
          if (value_desc->value == value)
            return value_desc;

          value_desc++;
        }
    }

  return NULL;
}

/**
 * gimp_enum_get_value:
 * @enum_type:  the #GType of a registered enum
 * @value:      an integer value
 * @value_name: (out) (optional): return location for the value's name, or %NULL
 * @value_nick: (out) (optional): return location for the value's nick, or %NULL
 * @value_desc: (out) (optional): return location for the value's translated
 *                                description, or %NULL
 * @value_help: (out) (optional): return location for the value's translated
 *                                help, or %NULL
 *
 * Checks if @value is valid for the enum registered as @enum_type.
 * If the value exists in that enum, its name, nick and its translated
 * description and help are returned (if @value_name, @value_nick,
 * @value_desc and @value_help are not %NULL).
 *
 * Returns: %TRUE if @value is valid for the @enum_type, %FALSE otherwise
 *
 * Since: 2.2
 **/
gboolean
gimp_enum_get_value (GType         enum_type,
                     gint          value,
                     const gchar **value_name,
                     const gchar **value_nick,
                     const gchar **value_desc,
                     const gchar **value_help)
{
  GEnumClass       *enum_class;
  const GEnumValue *enum_value;
  gboolean          success = FALSE;

  g_return_val_if_fail (G_TYPE_IS_ENUM (enum_type), FALSE);

  enum_class = g_type_class_ref (enum_type);
  enum_value = g_enum_get_value (enum_class, value);

  if (enum_value)
    {
      if (value_name)
        *value_name = enum_value->value_name;

      if (value_nick)
        *value_nick = enum_value->value_nick;

      if (value_desc || value_help)
        {
          const GimpEnumDesc *enum_desc;

          enum_desc = gimp_enum_get_desc (enum_class, value);

          if (value_desc)
            {
              if (enum_desc && enum_desc->value_desc)
                {
                  const gchar *context;

                  context = gimp_type_get_translation_context (enum_type);

                  if (context)  /*  the new way, using NC_()    */
                    *value_desc = g_dpgettext2 (gimp_type_get_translation_domain (enum_type),
                                                context,
                                                enum_desc->value_desc);
                  else          /*  for backward compatibility  */
                    *value_desc = g_strip_context (enum_desc->value_desc,
                                                   dgettext (gimp_type_get_translation_domain (enum_type),
                                                             enum_desc->value_desc));
                }
              else
                {
                  *value_desc = NULL;
                }
            }

          if (value_help)
            {
              *value_help = ((enum_desc && enum_desc->value_help) ?
                             dgettext (gimp_type_get_translation_domain (enum_type),
                                       enum_desc->value_help) :
                             NULL);
            }
        }

      success = TRUE;
    }

  g_type_class_unref (enum_class);

  return success;
}

/**
 * gimp_enum_value_get_desc:
 * @enum_class: a #GEnumClass
 * @enum_value: a #GEnumValue from @enum_class
 *
 * Retrieves the translated description for a given @enum_value.
 *
 * Returns: the translated description of the enum value
 *
 * Since: 2.2
 **/
const gchar *
gimp_enum_value_get_desc (GEnumClass       *enum_class,
                          const GEnumValue *enum_value)
{
  GType               type = G_TYPE_FROM_CLASS (enum_class);
  const GimpEnumDesc *enum_desc;

  enum_desc = gimp_enum_get_desc (enum_class, enum_value->value);

  if (enum_desc && enum_desc->value_desc)
    {
      const gchar *context;

      context = gimp_type_get_translation_context (type);

      if (context)  /*  the new way, using NC_()    */
        return g_dpgettext2 (gimp_type_get_translation_domain (type),
                             context,
                             enum_desc->value_desc);
      else          /*  for backward compatibility  */
        return g_strip_context (enum_desc->value_desc,
                                dgettext (gimp_type_get_translation_domain (type),
                                          enum_desc->value_desc));
    }

  return enum_value->value_name;
}

/**
 * gimp_enum_value_get_help:
 * @enum_class: a #GEnumClass
 * @enum_value: a #GEnumValue from @enum_class
 *
 * Retrieves the translated help for a given @enum_value.
 *
 * Returns: the translated help of the enum value
 *
 * Since: 2.2
 **/
const gchar *
gimp_enum_value_get_help (GEnumClass       *enum_class,
                          const GEnumValue *enum_value)
{
  GType               type = G_TYPE_FROM_CLASS (enum_class);
  const GimpEnumDesc *enum_desc;

  enum_desc = gimp_enum_get_desc (enum_class, enum_value->value);

  if (enum_desc && enum_desc->value_help)
    return dgettext (gimp_type_get_translation_domain (type),
                     enum_desc->value_help);

  return NULL;
}

/**
 * gimp_enum_value_get_abbrev:
 * @enum_class: a #GEnumClass
 * @enum_value: a #GEnumValue from @enum_class
 *
 * Retrieves the translated abbreviation for a given @enum_value.
 *
 * Returns: the translated abbreviation of the enum value
 *
 * Since: 2.10
 **/
const gchar *
gimp_enum_value_get_abbrev (GEnumClass       *enum_class,
                            const GEnumValue *enum_value)
{
  GType               type = G_TYPE_FROM_CLASS (enum_class);
  const GimpEnumDesc *enum_desc;

  enum_desc = gimp_enum_get_desc (enum_class, enum_value->value);

  if (enum_desc                              &&
      enum_desc[1].value == enum_desc->value &&
      enum_desc[1].value_desc)
    {
      return g_dpgettext2 (gimp_type_get_translation_domain (type),
                           gimp_type_get_translation_context (type),
                           enum_desc[1].value_desc);
    }

  return NULL;
}

/**
 * gimp_flags_get_first_desc:
 * @flags_class: a #GFlagsClass
 * @value:       a value from @flags_class
 *
 * Retrieves the first #GimpFlagsDesc that matches the given value, or %NULL.
 *
 * Returns: (nullable): the value's #GimpFlagsDesc.
 *
 * Since: 2.2
 **/
const GimpFlagsDesc *
gimp_flags_get_first_desc (GFlagsClass *flags_class,
                           guint        value)
{
  const GimpFlagsDesc *value_desc;

  g_return_val_if_fail (G_IS_FLAGS_CLASS (flags_class), NULL);

  value_desc =
    gimp_flags_get_value_descriptions (G_TYPE_FROM_CLASS (flags_class));

  if (value_desc)
    {
      while (value_desc->value_desc)
        {
          if ((value_desc->value & value) == value_desc->value)
            return value_desc;

          value_desc++;
        }
    }

  return NULL;
}

/**
 * gimp_flags_get_first_value:
 * @flags_type: the #GType of registered flags
 * @value:      an integer value
 * @value_name: (out) (optional): return location for the value's name, or %NULL
 * @value_nick: (out) (optional): return location for the value's nick, or %NULL
 * @value_desc: (out) (optional): return location for the value's translated
 *                                description, or %NULL
 * @value_help: (out) (optional): return location for the value's translated
 *                                help, or %NULL
 *
 * Checks if @value is valid for the flags registered as @flags_type.
 * If the value exists in that flags, its name, nick and its
 * translated description and help are returned (if @value_name,
 * @value_nick, @value_desc and @value_help are not %NULL).
 *
 * Returns: %TRUE if @value is valid for the @flags_type, %FALSE otherwise
 *
 * Since: 2.2
 **/
gboolean
gimp_flags_get_first_value (GType         flags_type,
                            guint         value,
                            const gchar **value_name,
                            const gchar **value_nick,
                            const gchar **value_desc,
                            const gchar **value_help)
{
  GFlagsClass       *flags_class;
  const GFlagsValue *flags_value;

  g_return_val_if_fail (G_TYPE_IS_FLAGS (flags_type), FALSE);

  flags_class = g_type_class_peek (flags_type);
  flags_value = g_flags_get_first_value (flags_class, value);

  if (flags_value)
    {
      if (value_name)
        *value_name = flags_value->value_name;

      if (value_nick)
        *value_nick = flags_value->value_nick;

      if (value_desc || value_help)
        {
          const GimpFlagsDesc *flags_desc;

          flags_desc = gimp_flags_get_first_desc (flags_class, value);

          if (value_desc)
            *value_desc = ((flags_desc && flags_desc->value_desc) ?
                           dgettext (gimp_type_get_translation_domain (flags_type),
                                     flags_desc->value_desc) :
                           NULL);

          if (value_help)
            *value_help = ((flags_desc && flags_desc->value_desc) ?
                           dgettext (gimp_type_get_translation_domain (flags_type),
                                     flags_desc->value_help) :
                           NULL);
        }

      return TRUE;
    }

  return FALSE;
}

/**
 * gimp_flags_value_get_desc:
 * @flags_class: a #GFlagsClass
 * @flags_value: a #GFlagsValue from @flags_class
 *
 * Retrieves the translated description for a given @flags_value.
 *
 * Returns: the translated description of the flags value
 *
 * Since: 2.2
 **/
const gchar *
gimp_flags_value_get_desc (GFlagsClass       *flags_class,
                           const GFlagsValue *flags_value)
{
  GType                type = G_TYPE_FROM_CLASS (flags_class);
  const GimpFlagsDesc *flags_desc;

  flags_desc = gimp_flags_get_first_desc (flags_class, flags_value->value);

  if (flags_desc->value_desc)
    {
      const gchar *context;

      context = gimp_type_get_translation_context (type);

      if (context)  /*  the new way, using NC_()    */
        return g_dpgettext2 (gimp_type_get_translation_domain (type),
                             context,
                             flags_desc->value_desc);
      else          /*  for backward compatibility  */
        return g_strip_context (flags_desc->value_desc,
                                dgettext (gimp_type_get_translation_domain (type),
                                          flags_desc->value_desc));
    }

  return flags_value->value_name;
}

/**
 * gimp_flags_value_get_help:
 * @flags_class: a #GFlagsClass
 * @flags_value: a #GFlagsValue from @flags_class
 *
 * Retrieves the translated help for a given @flags_value.
 *
 * Returns: the translated help of the flags value
 *
 * Since: 2.2
 **/
const gchar *
gimp_flags_value_get_help (GFlagsClass       *flags_class,
                           const GFlagsValue *flags_value)
{
  GType                type = G_TYPE_FROM_CLASS (flags_class);
  const GimpFlagsDesc *flags_desc;

  flags_desc = gimp_flags_get_first_desc (flags_class, flags_value->value);

  if (flags_desc->value_help)
    return dgettext (gimp_type_get_translation_domain (type),
                     flags_desc->value_help);

  return NULL;
}

/**
 * gimp_flags_value_get_abbrev:
 * @flags_class: a #GFlagsClass
 * @flags_value: a #GFlagsValue from @flags_class
 *
 * Retrieves the translated abbreviation for a given @flags_value.
 *
 * Returns: the translated abbreviation of the flags value
 *
 * Since: 2.10
 **/
const gchar *
gimp_flags_value_get_abbrev (GFlagsClass       *flags_class,
                             const GFlagsValue *flags_value)
{
  GType                type = G_TYPE_FROM_CLASS (flags_class);
  const GimpFlagsDesc *flags_desc;

  flags_desc = gimp_flags_get_first_desc (flags_class, flags_value->value);

  if (flags_desc                               &&
      flags_desc[1].value == flags_desc->value &&
      flags_desc[1].value_desc)
    {
      return g_dpgettext2 (gimp_type_get_translation_domain (type),
                           gimp_type_get_translation_context (type),
                           flags_desc[1].value_desc);
    }

  return NULL;
}

/**
 * gimp_stack_trace_available:
 * @optimal: whether we get optimal traces.
 *
 * Returns %TRUE if we have dependencies to generate backtraces. If
 * @optimal is %TRUE, the function will return %TRUE only when we
 * are able to generate optimal traces (i.e. with GDB or LLDB);
 * otherwise we return %TRUE even if only backtrace() API is available.
 *
 * On Win32, we return TRUE if Dr. Mingw is built-in, FALSE otherwise.
 *
 * Note: this function is not crash-safe, i.e. you should not try to use
 * it in a callback when the program is already crashing. In such a
 * case, call gimp_stack_trace_print() or gimp_stack_trace_query()
 * directly.
 *
 * Since: 2.10
 **/
gboolean
gimp_stack_trace_available (gboolean optimal)
{
#ifndef G_OS_WIN32
  gchar    *lld_path = NULL;
  gboolean  has_lldb = FALSE;

  /* Similarly to gdb, we could check for lldb by calling:
   * gimp_utils_generic_available ("lldb", major, minor).
   * We don't do so on purpose because on macOS, when lldb is absent, it
   * triggers a popup asking to install Xcode. So instead, we just
   * search for the executable in path.
   * This is the reason why this function is not crash-safe, since
   * g_find_program_in_path() allocates memory.
   * See issue #1999.
   */
  lld_path = g_find_program_in_path ("lldb");
  if (lld_path)
    {
      has_lldb = TRUE;
      g_free (lld_path);
    }

  if (gimp_utils_gdb_available (7, 0) || has_lldb)
    return TRUE;
#ifdef HAVE_EXECINFO_H
  if (! optimal)
    return TRUE;
#endif
#else /* G_OS_WIN32 */
#ifdef HAVE_EXCHNDL
  return TRUE;
#endif
#endif /* G_OS_WIN32 */
  return FALSE;
}

/**
 * gimp_stack_trace_print:
 * @prog_name: the program to attach to.
 * @stream: a FILE* stream.
 * @trace: (out) (optional): location to store a newly allocated string of
 *                           the trace.
 *
 * Attempts to generate a stack trace at current code position in
 * @prog_name. @prog_name is mostly a helper and can be set to NULL.
 * Nevertheless if set, it has to be the current program name (argv[0]).
 * This function is not meant to generate stack trace for third-party
 * programs, and will attach the current process id only.
 * Internally, this function uses `gdb` or `lldb` if they are available,
 * or the stacktrace() API on platforms where it is available. It always
 * fails on Win32.
 *
 * The stack trace, once generated, will either be printed to @stream or
 * returned as a newly allocated string in @trace, if not %NULL.
 *
 * In some error cases (e.g. segmentation fault), trying to allocate
 * more memory will trigger more segmentation faults and therefore loop
 * our error handling (which is just wrong). Therefore printing to a
 * file description is an implementation without any memory allocation.

 * Returns: %TRUE if a stack trace could be generated, %FALSE
 * otherwise.
 *
 * Since: 2.10
 **/
gboolean
gimp_stack_trace_print (const gchar   *prog_name,
                        gpointer      stream,
                        gchar       **trace)
{
  gboolean stack_printed = FALSE;

#ifdef PLATFORM_OSX
  pid_t    pid = getpid();
  uint64   tid64;
  long     tid;
  GString *gtrace = NULL;

  /* On macOS, we can't use gdb or lldb to attach to a process, so we
   * have to use the stacktrace() API.
   */

  unw_cursor_t cursor;
  unw_context_t context;

  unw_getcontext (&context);
  unw_init_local (&cursor, &context);


  pthread_threadid_np (NULL, &tid64);
  tid = (long) tid64;

  if (stream)
      g_fprintf (stream,
                  "\n# Stack traces obtained from PID %d - Thread 0x%lx #\n\n",
                  pid, tid);
  if (trace)
    {
      gtrace = g_string_new (NULL);
      g_string_printf (gtrace,
                        "\n# Stack traces obtained from PID %d - Thread 0x%lx #\n\n",
                        pid, tid);
    }

  while (unw_step (&cursor) > 0)
    {
      unw_word_t offset, pc;
      char fname[64];

      unw_get_reg (&cursor, UNW_REG_IP, &pc);
      fname[0] = '\0';
      unw_get_proc_name (&cursor, fname, sizeof(fname), &offset);

      stack_printed = TRUE;
      if (stream)
        g_fprintf (stream, "%p : (%s+0x%lx)\n", (void *)pc, fname, (unsigned long)offset);
      if (trace)
        g_string_append_printf (gtrace, "%p : (%s+0x%lx)\n", (void *) pc, fname, (unsigned long) offset);
    }

  if (trace)
    *trace = g_string_free (gtrace, FALSE);

  /* Stack printing conflicts with the OS stack printing */
  return stack_printed;

#else /* PLATFORM_OSX */
  /* This works only on UNIX systems. */
#ifndef G_OS_WIN32
  GString *gtrace = NULL;
  gchar    gimp_pid[16];
  gchar    buffer[256];
  ssize_t  read_n;
  int      sync_fd[2];
  int      out_fd[2];
  pid_t    fork_pid;
  pid_t    pid = getpid();
  gint     eintr_count = 0;
#if defined(G_OS_WIN32)
  DWORD    tid = GetCurrentThreadId ();
#elif defined(SYS_gettid)
  long     tid = syscall (SYS_gettid);
#elif defined(HAVE_THR_SELF)
  long     tid = 0;
  thr_self (&tid);
#endif

  g_snprintf (gimp_pid, 16, "%u", (guint) pid);

  if (pipe (sync_fd) == -1)
    {
      return FALSE;
    }

  if (pipe (out_fd) == -1)
    {
      close (sync_fd[0]);
      close (sync_fd[1]);

      return FALSE;
    }

  fork_pid = fork ();
  if (fork_pid == 0)
    {
      /* Child process. */
      gchar *args[9] = { "gdb", "-batch",
                         "-ex", "info threads",
                         /* A bug, possibly in gdb, could lock the whole
                          * AmmoOS Image process with a full thread backtrace in
                          * some conditions. We aren't sure if it still
                          * exists. See issue #7539.
                          */
                         "-ex", "thread apply all backtrace full",
                         (gchar *) prog_name, NULL, NULL };

      if (prog_name == NULL)
        args[6] = "-p";

      args[7] = gimp_pid;

      /* Wait until the parent enabled us to ptrace it. */
      {
        gchar dummy;

        close (sync_fd[1]);
        while (read (sync_fd[0], &dummy, 1) < 0 && errno == EINTR);
        close (sync_fd[0]);
      }

      /* Redirect the debugger output. */
      dup2 (out_fd[1], STDOUT_FILENO);
      close (out_fd[0]);
      close (out_fd[1]);

      /* Run GDB if version 7.0 or over. Why I do such a check is that
       * it turns out older versions may not only fail, but also have
       * very undesirable side effects like terminating the debugged
       * program, at least on FreeBSD where GDB 6.1 is apparently
       * installed by default on the stable release at day of writing.
       * See bug 793514. */
      if (! gimp_utils_gdb_available (7, 0) ||
          execvp (args[0], args) == -1)
        {
          /* LLDB as alternative if the GDB call failed or if it was in
           * a too-old version. */
          gchar *args_lldb[15] = { "lldb", "--attach-pid", NULL, "--batch",
                                   "--one-line", "thread list",
                                   "--one-line", "thread backtrace all",
                                   "--one-line", "bt all",
                                   "--one-line-on-crash", "bt",
                                   "--one-line-on-crash", "quit", NULL };

          args_lldb[2] = gimp_pid;

          execvp (args_lldb[0], args_lldb);
        }

      _exit (0);
    }
  else if (fork_pid > 0)
    {
      /* Main process */
      int status;

      /* Allow the child to ptrace us, and signal it to start. */
      close (sync_fd[0]);
#ifdef PR_SET_PTRACER
      prctl (PR_SET_PTRACER, fork_pid, 0, 0, 0);
#endif
      close (sync_fd[1]);

      /* It is important to close the writing side of the pipe, otherwise
       * the read() will wait forever without getting the information that
       * writing is finished.
       */
      close (out_fd[1]);

      while ((read_n = read (out_fd[0], buffer, 255)) != 0)
        {
          if (read_n < 0)
            {
              /* LLDB on macOS seems to trigger a few EINTR error (see
               * !13), though read() finally ends up working later. So
               * let's not make this error fatal, and instead try again.
               * Yet to avoid infinite loop (in case the error really
               * happens at every call), we abandon after a few
               * consecutive errors.
               * Note: macOS no longer runs through this code path
               */
              if (errno == EINTR && eintr_count <= 5)
                {
                  eintr_count++;
                  continue;
                }
              break;
            }
          eintr_count = 0;
          if (! stack_printed)
            {
#if defined(G_OS_WIN32) || defined(SYS_gettid) || defined(HAVE_THR_SELF)
              if (stream)
                g_fprintf (stream,
                           "\n# Stack traces obtained from PID %d - Thread %lu #\n\n",
                           pid, tid);
#endif
              if (trace)
                {
                  gtrace = g_string_new (NULL);
#if defined(G_OS_WIN32) || defined(SYS_gettid) || defined(HAVE_THR_SELF)
                  g_string_printf (gtrace,
                                   "\n# Stack traces obtained from PID %d - Thread %lu #\n\n",
                                   pid, tid);
#endif
                }
            }
          /* It's hard to know if the debugger was found since it
           * happened in the child. Let's just assume that any output
           * means it succeeded.
           */
          stack_printed = TRUE;

          buffer[read_n] = '\0';
          if (stream)
            g_fprintf (stream, "%s", buffer);
          if (trace)
            g_string_append (gtrace, (const gchar *) buffer);
        }
      close (out_fd[0]);

#ifdef PR_SET_PTRACER
      /* Clear ptrace permission set above */
      prctl (PR_SET_PTRACER, 0, 0, 0, 0);
#endif

      waitpid (fork_pid, &status, 0);
    }
  /* else if (fork_pid == (pid_t) -1)
   * Fork failed!
   * Just continue, maybe the backtrace() API will succeed.
   */

#ifdef HAVE_EXECINFO_H
  if (! stack_printed)
    {
      /* As a last resort, try using the backtrace() Linux API. It is a bit
       * less fancy than gdb or lldb, which is why it is not given priority.
       */
      void *bt_buf[100];
      int   n_symbols;

      n_symbols = backtrace (bt_buf, 100);
      if (trace && n_symbols)
        {
          char **symbols;
          int    i;

          symbols = backtrace_symbols (bt_buf, n_symbols);
          if (symbols)
            {
              for (i = 0; i < n_symbols; i++)
                {
                  if (stream)
                    g_fprintf (stream, "%s\n", (const gchar *) symbols[i]);
                  if (trace)
                    {
                      if (! gtrace)
                        gtrace = g_string_new (NULL);
                      g_string_append (gtrace,
                                       (const gchar *) symbols[i]);
                      g_string_append_c (gtrace, '\n');
                    }
                }
              free (symbols);
            }
        }
      else if (n_symbols)
        {
          /* This allows to generate traces without memory allocation.
           * In some cases, this is necessary, especially during
           * segfault-type crashes.
           */
          backtrace_symbols_fd (bt_buf, n_symbols, fileno ((FILE *) stream));
        }
      stack_printed = (n_symbols > 0);
    }
#endif /* HAVE_EXECINFO_H */

  if (trace)
    {
      if (gtrace)
        *trace = g_string_free (gtrace, FALSE);
      else
        *trace = NULL;
    }
#endif /* G_OS_WIN32 */

  return stack_printed;
#endif /* PLATFORM_OSX */
}

/**
 * gimp_stack_trace_query:
 * @prog_name: the program to attach to.
 *
 * This is mostly the same as g_on_error_query() except that we use our
 * own backtrace function, much more complete.
 * @prog_name must be the current program name (argv[0]).
 * It does nothing on Win32.
 *
 * Since: 2.10
 **/
void
gimp_stack_trace_query (const gchar *prog_name)
{
#ifndef G_OS_WIN32
  gchar    buf[16];
  gboolean eof = FALSE;

 retry:

  g_fprintf (stdout,
             "%s (pid:%u): %s: ",
             prog_name,
             (guint) getpid (),
             "[E]xit, show [S]tack trace or [P]roceed");
  fflush (stdout);

  if (isatty(0) && isatty(1))
    eof = (fgets (buf, 8, stdin) == NULL);
  else
    strcpy (buf, "E\n");

  if (eof)
    strcpy (buf, "S\n");

  if ((buf[0] == 'E' || buf[0] == 'e')
      && buf[1] == '\n')
    {
      _exit (0);
    }
  else if ((buf[0] == 'P' || buf[0] == 'p')
           && buf[1] == '\n')
    {
      return;
    }
  else if ((buf[0] == 'S' || buf[0] == 's')
           && buf[1] == '\n')
    {
      if (! gimp_stack_trace_print (prog_name, stdout, NULL))
        g_fprintf (stderr, "%s\n", "Stack trace not available on your system.");

      if (eof)
        /* As a special exception, if we get an EOF (or a reading error)
         * on stdin, we just output the stacktrace and exit.
         */
        _exit (0);
      else
        goto retry;
    }
  else
    {
      goto retry;
    }
#endif
}

GIMP_WARNING_API_BREAK("gimp_range_estimate_settings(): add a gboolean integer_increments arg? And/or an optional GParamSpec arg. Cf. commit e735054347")
/**
 * gimp_range_estimate_settings:
 * @lower: the lower value.
 * @upper: the higher value.
 * @step: (out) (optional): the proposed step increment.
 * @page: (out) (optional): the proposed page increment.
 * @digits: (out) (optional): the proposed decimal places precision.
 *
 * This function proposes reasonable settings for increments and display
 * digits. These can be used for instance on #GtkRange or other widgets
 * using a #GtkAdjustment typically.
 * Note that it will never return @digits with value 0. If you know that
 * your input needs to display integer values, there is no need to set
 * @digits.
 *
 * There is no universal answer to the best increments and number of
 * decimal places. It often depends on context of what the value is
 * meant to represent. This function only tries to provide sensible
 * generic values which can be used when it doesn't matter too much or
 * for generated GUI for instance. If you know exactly how you want to
 * show and interact with a given range, you don't have to use this
 * function.
 */
void
gimp_range_estimate_settings (gdouble  lower,
                              gdouble  upper,
                              gdouble *step,
                              gdouble *page,
                              gint    *digits)
{
  gdouble range;

  g_return_if_fail (upper >= lower);
  g_return_if_fail (step || page || digits);

  range = upper - lower;

  if (range > 0 && range <= 1.0)
    {
      gdouble places = 10.0;

      if (digits)
        *digits = 3;

      /* Compute some acceptable step and page increments always in the
       * format `10**-X` where X is the rounded precision.
       * So for instance:
       *  0.8 will have increments 0.01 and 0.1.
       *  0.3 will have increments 0.001 and 0.01.
       *  0.06 will also have increments 0.001 and 0.01.
       */
      while (range * places < 5.0)
        {
          places *= 10.0;
          if (digits)
            (*digits)++;
        }


      if (step)
        *step = 0.1 / places;
      if (page)
        *page = 1.0 / places;
    }
  else if (range <= 2.0)
    {
      if (step)
        *step = 0.01;
      if (page)
        *page = 0.1;

      if (digits)
        *digits = 3;
    }
  else if (range <= 5.0)
    {
      if (step)
        *step = 0.1;
      if (page)
        *page = 1.0;
      if (digits)
        *digits = 2;
    }
  else if (range <= 40.0)
    {
      if (step)
        *step = 1.0;
      if (page)
        *page = 2.0;
      if (digits)
        *digits = 2;
    }
  else
    {
      if (step)
        *step = 1.0;
      if (page)
        *page = 10.0;
      if (digits)
        *digits = 1;
    }
}

/**
 * gimp_bind_text_domain:
 * @domain_name: a gettext domain name
 * @dir_name:    path of the catalog directory
 *
 * This function wraps bindtextdomain on UNIX and wbintextdomain on Windows.
 * @dir_name is expected to be in the encoding used by the C library on UNIX
 * and UTF-8 on Windows.
 *
 * Since: 3.0
 **/
void
gimp_bind_text_domain (const gchar *domain_name,
                       const gchar *dir_name)
{
#if defined (_WIN32) && !defined (__CYGWIN__)
  wchar_t *dir_name_utf16 = g_utf8_to_utf16 (dir_name, -1, NULL, NULL, NULL);

  if G_UNLIKELY (!dir_name_utf16)
    {
      g_printerr ("[%s] Cannot translate the catalog directory to UTF-16\n", __func__);
    }
  else
    {
      wbindtextdomain (domain_name, dir_name_utf16);
      g_free (dir_name_utf16);
    }
#else
  bindtextdomain (domain_name, dir_name);
#endif
}


/* Private functions. */

#ifndef G_OS_WIN32
static gboolean
gimp_utils_generic_available (const gchar *program,
                              gint         major,
                              gint         minor)
{
  pid_t pid;
  int   out_fd[2];

  if (pipe (out_fd) == -1)
    {
      return FALSE;
    }

  /* XXX: I don't use g_spawn_sync() or similar glib functions because
   * to read the contents of the stdout, these functions would allocate
   * memory dynamically. As we know, when debugging crashes, this is a
   * definite blocker. So instead I simply use a buffer on the stack
   * with a lower level fork() call.
   */
  pid = fork ();
  if (pid == 0)
    {
      /* Child process. */
      gchar *args[3] = { (gchar *) program, "--version", NULL };

      /* Redirect the debugger output. */
      dup2 (out_fd[1], STDOUT_FILENO);
      close (out_fd[0]);
      close (out_fd[1]);

      /* Run version check. */
      execvp (args[0], args);
      _exit (-1);
    }
  else if (pid > 0)
    {
      /* Main process */
      gchar    buffer[256];
      ssize_t  read_n;
      int      status;
      gint     installed_major = 0;
      gint     installed_minor = 0;
      gboolean major_reading = FALSE;
      gboolean minor_reading = FALSE;
      gint     i;
      gchar    c;

      waitpid (pid, &status, 0);

      if (! WIFEXITED (status) || WEXITSTATUS (status) != 0)
        return FALSE;

      /* It is important to close the writing side of the pipe, otherwise
       * the read() will wait forever without getting the information that
       * writing is finished.
       */
      close (out_fd[1]);

      /* I could loop forever until EOL, but I am pretty sure the
       * version information is stored on the first line and one call to
       * read() with 256 characters should be more than enough.
       */
      read_n = read (out_fd[0], buffer, 256);

      /* This is quite a very stupid parser. I only look for the first
       * numbers and consider them as version information. This works
       * fine for both GDB and LLDB as far as I can see for the output
       * of `${program} --version` but this should obviously not be
       * considered as a *really* generic version test.
       */
      for (i = 0; i < read_n; i++)
        {
          c = buffer[i];
          if (c >= '0' && c <= '9')
            {
              if (minor_reading)
                {
                  installed_minor = 10 * installed_minor + (c - '0');
                }
              else
                {
                  major_reading = TRUE;
                  installed_major = 10 * installed_major + (c - '0');
                }
            }
          else if (c == '.')
            {
              if (major_reading)
                {
                  minor_reading = TRUE;
                  major_reading = FALSE;
                }
              else if (minor_reading)
                {
                  break;
                }
            }
          else if (c == '\n')
            {
              /* Version information should be in the first line. */
              break;
            }
        }
      close (out_fd[0]);

      return (installed_major > 0 &&
              (installed_major > major ||
               (installed_major == major && installed_minor >= minor)));
    }

  /* Fork failed, or Win32. */
  return FALSE;
}
#endif

#ifndef G_OS_WIN32
static gboolean
gimp_utils_gdb_available (gint major,
                          gint minor)
{
  return gimp_utils_generic_available ("gdb", major, minor);
}
#endif

/* --- end libammoos/base/fieldbase/gimputils.c --- */

/* --- begin libammoos/base/fieldbase/gimpvaluearray.c --- */
/* LIBGIMP - The AmmoOS Image Library
 * Copyright (C) 1995-1997 Peter Mattis and Spencer Kimball
 *
 * gimpvaluearray.c ported from GValueArray
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

#include <gegl.h>
#include <gio/gio.h>
#include <glib-object.h>
#include <gobject/gvaluecollector.h>

#include "gimpbasetypes.h"

#include "gimpparamspecs.h"
#include "gimpvaluearray.h"


/**
 * SECTION:gimpvaluearray
 * @short_description: A container structure to maintain an array of
 *     generic values
 * @see_also: #GValue, #GParamSpecValueArray, gimp_param_spec_value_array()
 * @title: GimpValueArray
 *
 * The prime purpose of a #GimpValueArray is for it to be used as an
 * object property that holds an array of values. A #GimpValueArray wraps
 * an array of #GValue elements in order for it to be used as a boxed
 * type through %GIMP_TYPE_VALUE_ARRAY.
 */


#define GROUP_N_VALUES (1) /* power of 2 !! */


/**
 * GimpValueArray:
 *
 * A #GimpValueArray contains an array of #GValue elements.
 *
 * Since: 2.10
 */
struct _GimpValueArray
{
  gint    n_values;
  GValue *values;

  gint    n_prealloced;
  gint    ref_count;
};


G_DEFINE_BOXED_TYPE (GimpValueArray, gimp_value_array,
                     gimp_value_array_ref, gimp_value_array_unref)


/**
 * gimp_value_array_index:
 * @value_array: #GimpValueArray to get a value from
 * @index: index of the value of interest
 *
 * Return a pointer to the value at @index contained in @value_array.
 *
 * *Note*: in binding languages, some custom types fail to be correctly passed
 * through. For these types, you should use specific functions.
 * For instance, in the Python binding, a [type@ColorArray] `GValue`
 * won't be usable with this function. You should use instead
 * [method@ValueArray.get_color_array].
 *
 * Returns: (transfer none): pointer to a value at @index in @value_array
 *
 * Since: 2.10
 */
GValue *
gimp_value_array_index (const GimpValueArray *value_array,
                        gint                  index)
{
  g_return_val_if_fail (value_array != NULL, NULL);
  g_return_val_if_fail (index < value_array->n_values, NULL);

  return value_array->values + index;
}

/**
 * gimp_value_array_get_color_array:
 * @value_array: #GimpValueArray to get a value from
 * @index: index of the value of interest
 *
 * Return a pointer to the value at @index contained in @value_array. This value
 * is supposed to be a [type@ColorArray].
 *
 * *Note*: most of the time, you should use the generic [method@Gimp.ValueArray.index]
 * to retrieve a value, then the relevant `g_value_get_*()` function.
 * This alternative function is mostly there for bindings because
 * GObject-Introspection is [not able yet to process correctly known
 * boxed array types](https://gitlab.gnome.org/GNOME/gobject-introspection/-/issues/492).
 *
 * There are no reasons to use this function in C code.
 *
 * Returns: (transfer none) (array zero-terminated=1): the [type@ColorArray] stored at @index in @value_array.
 *
 * Since: 3.0
 */
/* XXX See: https://gitlab.gnome.org/GNOME/ammoos/-/issues/10885#note_2030308
 * This explains why we created a specific function for GimpColorArray, instead
 * of using the generic gimp_value_array_index().
 */
GeglColor **
gimp_value_array_get_color_array (const GimpValueArray *value_array,
                                  gint                  index)
{
  GValue         *value;
  GimpColorArray  colors;

  g_return_val_if_fail (value_array != NULL, NULL);
  g_return_val_if_fail (index < value_array->n_values, NULL);

  value = value_array->values + index;
  g_return_val_if_fail (GIMP_VALUE_HOLDS_COLOR_ARRAY (value), NULL);

  colors = g_value_get_boxed (value);

  return colors;
}

/**
 * gimp_value_array_get_core_object_array:
 * @value_array: #GimpValueArray to get a value from
 * @index: index of the value of interest
 *
 * Return a pointer to the value at @index contained in @value_array. This value
 * is supposed to be a [type@CoreObjectArray].
 *
 * *Note*: most of the time, you should use the generic [method@Gimp.ValueArray.index]
 * to retrieve a value, then the relevant `g_value_get_*()` function.
 * This alternative function is mostly there for bindings because
 * GObject-Introspection is [not able yet to process correctly known
 * boxed array types](https://gitlab.gnome.org/GNOME/gobject-introspection/-/issues/492).
 *
 * There are no reasons to use this function in C code.
 *
 * Returns: (transfer none) (array zero-terminated=1): the [type@CoreObjectArray] stored at @index in @value_array.
 *
 * Since: 3.0
 */
GObject **
gimp_value_array_get_core_object_array (const GimpValueArray *value_array,
                                        gint                  index)
{
  GValue   *value;
  GObject **objects;

  g_return_val_if_fail (value_array != NULL, NULL);
  g_return_val_if_fail (index < value_array->n_values, NULL);

  value = value_array->values + index;
  g_return_val_if_fail (GIMP_VALUE_HOLDS_CORE_OBJECT_ARRAY (value), NULL);

  objects = g_value_get_boxed (value);

  return objects;
}

static inline void
value_array_grow (GimpValueArray *value_array,
                  gint            n_values,
                  gboolean        zero_init)
{
  g_return_if_fail ((guint) n_values >= (guint) value_array->n_values);

  value_array->n_values = n_values;
  if (value_array->n_values > value_array->n_prealloced)
    {
      gint i = value_array->n_prealloced;

      value_array->n_prealloced = (value_array->n_values + GROUP_N_VALUES - 1) & ~(GROUP_N_VALUES - 1);
      value_array->values = g_renew (GValue, value_array->values, value_array->n_prealloced);

      if (!zero_init)
        i = value_array->n_values;

      memset (value_array->values + i, 0,
              (value_array->n_prealloced - i) * sizeof (value_array->values[0]));
    }
}

static inline void
value_array_shrink (GimpValueArray *value_array)
{
  if (value_array->n_prealloced >= value_array->n_values + GROUP_N_VALUES)
    {
      value_array->n_prealloced = (value_array->n_values + GROUP_N_VALUES - 1) & ~(GROUP_N_VALUES - 1);
      value_array->values = g_renew (GValue, value_array->values, value_array->n_prealloced);
    }
}

/**
 * gimp_value_array_new:
 * @n_prealloced: number of values to preallocate space for
 *
 * Allocate and initialize a new #GimpValueArray, optionally preserve space
 * for @n_prealloced elements. New arrays always contain 0 elements,
 * regardless of the value of @n_prealloced.
 *
 * Returns: a newly allocated #GimpValueArray with 0 values
 *
 * Since: 2.10
 */
GimpValueArray *
gimp_value_array_new (gint n_prealloced)
{
  GimpValueArray *value_array = g_slice_new0 (GimpValueArray);

  value_array_grow (value_array, n_prealloced, TRUE);
  value_array->n_values = 0;
  value_array->ref_count = 1;

  return value_array;
}

/**
 * gimp_value_array_new_from_types: (skip)
 * @error_msg:  return location for an error message.
 * @first_type: first type in the array, or #G_TYPE_NONE.
 * @...:        the remaining types in the array, terminated by #G_TYPE_NONE
 *
 * Allocate and initialize a new #GimpValueArray, and fill it with
 * values that are given as a list of (#GType, value) pairs,
 * terminated by #G_TYPE_NONE.
 *
 * Returns: (nullable): a newly allocated #GimpValueArray, or %NULL if
 *          an error happened.
 *
 * Since: 3.0
 */
GimpValueArray *
gimp_value_array_new_from_types (gchar **error_msg,
                                 GType   first_type,
                                 ...)
{
  GimpValueArray *value_array;
  va_list         va_args;

  g_return_val_if_fail (error_msg == NULL || *error_msg == NULL, NULL);

  va_start (va_args, first_type);

  value_array = gimp_value_array_new_from_types_valist (error_msg,
                                                        first_type,
                                                        va_args);

  va_end (va_args);

  return value_array;
}

/**
 * gimp_value_array_new_from_types_valist: (skip)
 * @error_msg:  return location for an error message.
 * @first_type: first type in the array, or #G_TYPE_NONE.
 * @va_args:    a va_list of GTypes and values, terminated by #G_TYPE_NONE
 *
 * Allocate and initialize a new #GimpValueArray, and fill it with
 * @va_args given in the order as passed to
 * gimp_value_array_new_from_types().
 *
 * Returns: (nullable): a newly allocated #GimpValueArray, or %NULL if
 *          an error happened.
 *
 * Since: 3.0
 */
GimpValueArray *
gimp_value_array_new_from_types_valist (gchar   **error_msg,
                                        GType     first_type,
                                        va_list   va_args)
{
  GimpValueArray *value_array;
  GType           type;

  g_return_val_if_fail (error_msg == NULL || *error_msg == NULL, NULL);

  type = first_type;

  value_array = gimp_value_array_new (type == G_TYPE_NONE ? 0 : 1);

  while (type != G_TYPE_NONE)
    {
      GValue value     = G_VALUE_INIT;
      gchar  *my_error = NULL;

      g_value_init (&value, type);

      G_VALUE_COLLECT (&value, va_args, G_VALUE_NOCOPY_CONTENTS, &my_error);

      if (my_error)
        {
          if (error_msg)
            {
              *error_msg = my_error;
            }
          else
            {
              g_printerr ("%s: %s", G_STRFUNC, my_error);
              g_free (my_error);
            }

          gimp_value_array_unref (value_array);

          va_end (va_args);

          return NULL;
        }

      gimp_value_array_append (value_array, &value);
      g_value_unset (&value);

      type = va_arg (va_args, GType);
    }

  va_end (va_args);

  return value_array;
}

/**
 * gimp_value_array_copy:
 * @value_array: #GimpValueArray to copy
 *
 * Return an exact copy of a #GimpValueArray by duplicating all its values.
 *
 * Returns: a newly allocated #GimpValueArray.
 *
 * Since: 3.0
 */
GimpValueArray *
gimp_value_array_copy (const GimpValueArray *value_array)
{
  g_return_val_if_fail (value_array != NULL, NULL);

  return gimp_value_array_new_from_values (value_array->values,
                                           value_array->n_values);
}

/**
 * gimp_value_array_new_from_values:
 * @values: (array length=n_values): The #GValue elements
 * @n_values: the number of value elements
 *
 * Allocate and initialize a new #GimpValueArray, and fill it with
 * the given #GValues.  When no #GValues are given, returns empty #GimpValueArray.
 *
 * Returns: a newly allocated #GimpValueArray.
 *
 * Since: 3.0
 */
GimpValueArray *
gimp_value_array_new_from_values (const GValue *values,
                                  gint          n_values)
{
  GimpValueArray *value_array;
  gint i;

  /* n_values is zero if and only if values is NULL. */
  g_return_val_if_fail ((n_values == 0  && values == NULL) ||
                        (n_values > 0 && values != NULL),
                        NULL);

  value_array = gimp_value_array_new (n_values);

  for (i = 0; i < n_values; i++)
    {
      gimp_value_array_insert (value_array, i, &values[i]);
    }

  return value_array;
}

/**
 * gimp_value_array_ref:
 * @value_array: #GimpValueArray to ref
 *
 * Adds a reference to a #GimpValueArray.
 *
 * Returns: the same @value_array
 *
 * Since: 2.10
 */
GimpValueArray *
gimp_value_array_ref (GimpValueArray *value_array)
{
  g_return_val_if_fail (value_array != NULL, NULL);

  value_array->ref_count++;

  return value_array;
}

/**
 * gimp_value_array_unref:
 * @value_array: #GimpValueArray to unref
 *
 * Unref a #GimpValueArray. If the reference count drops to zero, the
 * array including its contents are freed.
 *
 * Since: 2.10
 */
void
gimp_value_array_unref (GimpValueArray *value_array)
{
  g_return_if_fail (value_array != NULL);

  value_array->ref_count--;

  if (value_array->ref_count < 1)
    {
      gint i;

      for (i = 0; i < value_array->n_values; i++)
        {
          GValue *value = value_array->values + i;

          if (G_VALUE_TYPE (value) != 0) /* we allow unset values in the array */
            g_value_unset (value);
        }

      g_free (value_array->values);
      g_slice_free (GimpValueArray, value_array);
    }
}

gint
gimp_value_array_length (const GimpValueArray *value_array)
{
  g_return_val_if_fail (value_array != NULL, 0);

  return value_array->n_values;
}

/**
 * gimp_value_array_prepend:
 * @value_array: #GimpValueArray to add an element to
 * @value: (allow-none): #GValue to copy into #GimpValueArray, or %NULL
 *
 * Insert a copy of @value as first element of @value_array. If @value is
 * %NULL, an uninitialized value is prepended.
 *
 * Returns: (transfer none): the #GimpValueArray passed in as @value_array
 *
 * Since: 2.10
 */
GimpValueArray *
gimp_value_array_prepend (GimpValueArray *value_array,
                          const GValue   *value)
{
  g_return_val_if_fail (value_array != NULL, NULL);

  return gimp_value_array_insert (value_array, 0, value);
}

/**
 * gimp_value_array_append:
 * @value_array: #GimpValueArray to add an element to
 * @value: (allow-none): #GValue to copy into #GimpValueArray, or %NULL
 *
 * Insert a copy of @value as last element of @value_array. If @value is
 * %NULL, an uninitialized value is appended.
 *
 * Returns: (transfer none): the #GimpValueArray passed in as @value_array
 *
 * Since: 2.10
 */
GimpValueArray *
gimp_value_array_append (GimpValueArray *value_array,
                         const GValue   *value)
{
  g_return_val_if_fail (value_array != NULL, NULL);

  return gimp_value_array_insert (value_array, value_array->n_values, value);
}

/**
 * gimp_value_array_insert:
 * @value_array: #GimpValueArray to add an element to
 * @index: insertion position, must be &lt;= gimp_value_array_length()
 * @value: (allow-none): #GValue to copy into #GimpValueArray, or %NULL
 *
 * Insert a copy of @value at specified position into @value_array. If @value
 * is %NULL, an uninitialized value is inserted.
 *
 * Returns: (transfer none): the #GimpValueArray passed in as @value_array
 *
 * Since: 2.10
 */
GimpValueArray *
gimp_value_array_insert (GimpValueArray *value_array,
                         gint            index,
                         const GValue   *value)
{
  gint i;

  g_return_val_if_fail (value_array != NULL, NULL);
  g_return_val_if_fail (index <= value_array->n_values, value_array);

  i = value_array->n_values;
  value_array_grow (value_array, value_array->n_values + 1, FALSE);

  if (index + 1 < value_array->n_values)
    memmove (value_array->values + index + 1, value_array->values + index,
             (i - index) * sizeof (value_array->values[0]));

  memset (value_array->values + index, 0, sizeof (value_array->values[0]));

  if (value)
    {
      g_value_init (value_array->values + index, G_VALUE_TYPE (value));
      g_value_copy (value, value_array->values + index);
    }

  return value_array;
}

/**
 * gimp_value_array_remove:
 * @value_array: #GimpValueArray to remove an element from
 * @index: position of value to remove, which must be less than
 *         gimp_value_array_length()
 *
 * Remove the value at position @index from @value_array.
 *
 * Returns: (transfer none): the #GimpValueArray passed in as @value_array
 *
 * Since: 2.10
 */
GimpValueArray *
gimp_value_array_remove (GimpValueArray *value_array,
                         gint            index)
{
  g_return_val_if_fail (value_array != NULL, NULL);
  g_return_val_if_fail (index < value_array->n_values, value_array);

  if (G_VALUE_TYPE (value_array->values + index) != 0)
    g_value_unset (value_array->values + index);

  value_array->n_values--;

  if (index < value_array->n_values)
    memmove (value_array->values + index, value_array->values + index + 1,
             (value_array->n_values - index) * sizeof (value_array->values[0]));

  value_array_shrink (value_array);

  if (value_array->n_prealloced > value_array->n_values)
    memset (value_array->values + value_array->n_values, 0, sizeof (value_array->values[0]));

  return value_array;
}

void
gimp_value_array_truncate (GimpValueArray *value_array,
                           gint            n_values)
{
  gint i;

  g_return_if_fail (value_array != NULL);
  g_return_if_fail (n_values > 0 && n_values <= value_array->n_values);

  for (i = value_array->n_values; i > n_values; i--)
    gimp_value_array_remove (value_array, i - 1);
}


/*
 * GIMP_TYPE_PARAM_VALUE_ARRAY
 */

#define GIMP_PARAM_SPEC_VALUE_ARRAY(pspec)    (G_TYPE_CHECK_INSTANCE_CAST ((pspec), GIMP_TYPE_PARAM_VALUE_ARRAY, GimpParamSpecValueArray))

typedef struct _GimpParamSpecValueArray GimpParamSpecValueArray;

/**
 * GimpParamSpecValueArray:
 * @parent_instance:  private #GParamSpec portion
 * @element_spec:     the #GParamSpec of the array elements
 * @fixed_n_elements: default length of the array
 *
 * A #GParamSpec derived structure that contains the meta data for
 * value array properties.
 **/
struct _GimpParamSpecValueArray
{
  GParamSpec  parent_instance;
  GParamSpec *element_spec;
  gint        fixed_n_elements;
};

static void       gimp_param_value_array_class_init  (GParamSpecClass *klass);
static void       gimp_param_value_array_init        (GParamSpec      *pspec);
static void       gimp_param_value_array_finalize    (GParamSpec      *pspec);
static void       gimp_param_value_array_set_default (GParamSpec      *pspec,
                                                      GValue          *value);
static gboolean   gimp_param_value_array_validate    (GParamSpec      *pspec,
                                                      GValue          *value);
static gint       gimp_param_value_array_values_cmp  (GParamSpec      *pspec,
                                                      const GValue    *value1,
                                                      const GValue    *value2);

GType
gimp_param_value_array_get_type (void)
{
  static GType type = 0;

  if (! type)
    {
      const GTypeInfo info =
      {
        sizeof (GParamSpecClass),
        NULL, NULL,
        (GClassInitFunc) gimp_param_value_array_class_init,
        NULL, NULL,
        sizeof (GimpParamSpecValueArray),
        0,
        (GInstanceInitFunc) gimp_param_value_array_init
      };

      type = g_type_register_static (G_TYPE_PARAM_BOXED,
                                     "GimpParamValueArray", &info, 0);
    }

  return type;
}


static void
gimp_param_value_array_class_init (GParamSpecClass *klass)
{
  klass->value_type        = GIMP_TYPE_VALUE_ARRAY;
  klass->finalize          = gimp_param_value_array_finalize;
  klass->value_set_default = gimp_param_value_array_set_default;
  klass->value_validate    = gimp_param_value_array_validate;
  klass->values_cmp        = gimp_param_value_array_values_cmp;
}

static void
gimp_param_value_array_init (GParamSpec *pspec)
{
  GimpParamSpecValueArray *aspec = GIMP_PARAM_SPEC_VALUE_ARRAY (pspec);

  aspec->element_spec = NULL;
  aspec->fixed_n_elements = 0; /* disable */
}

static inline guint
gimp_value_array_ensure_size (GimpValueArray *value_array,
                              guint           fixed_n_elements)
{
  guint changed = 0;

  if (fixed_n_elements)
    {
      while (gimp_value_array_length (value_array) < fixed_n_elements)
        {
          gimp_value_array_append (value_array, NULL);
          changed++;
        }

      while (gimp_value_array_length (value_array) > fixed_n_elements)
        {
          gimp_value_array_remove (value_array,
                                   gimp_value_array_length (value_array) - 1);
          changed++;
        }
    }

  return changed;
}

static void
gimp_param_value_array_finalize (GParamSpec *pspec)
{
  GimpParamSpecValueArray *aspec = GIMP_PARAM_SPEC_VALUE_ARRAY (pspec);
  GParamSpecClass         *parent_class;

  parent_class = g_type_class_peek (g_type_parent (GIMP_TYPE_PARAM_VALUE_ARRAY));

  g_clear_pointer (&aspec->element_spec, g_param_spec_unref);

  parent_class->finalize (pspec);
}

static void
gimp_param_value_array_set_default (GParamSpec *pspec,
                                    GValue     *value)
{
  GimpParamSpecValueArray *aspec = GIMP_PARAM_SPEC_VALUE_ARRAY (pspec);

  if (! value->data[0].v_pointer && aspec->fixed_n_elements)
    value->data[0].v_pointer = gimp_value_array_new (aspec->fixed_n_elements);

  if (value->data[0].v_pointer)
    {
      /* g_value_reset (value);  already done */
      gimp_value_array_ensure_size (value->data[0].v_pointer,
                                    aspec->fixed_n_elements);
    }
}

static gboolean
gimp_param_value_array_validate (GParamSpec *pspec,
                                 GValue     *value)
{
  GimpParamSpecValueArray *aspec       = GIMP_PARAM_SPEC_VALUE_ARRAY (pspec);
  GimpValueArray          *value_array = value->data[0].v_pointer;
  guint                    changed     = 0;

  if (! value->data[0].v_pointer && aspec->fixed_n_elements)
    value->data[0].v_pointer = gimp_value_array_new (aspec->fixed_n_elements);

  if (value->data[0].v_pointer)
    {
      /* ensure array size validity */
      changed += gimp_value_array_ensure_size (value_array,
                                               aspec->fixed_n_elements);

      /* ensure array values validity against a present element spec */
      if (aspec->element_spec)
        {
          GParamSpec *element_spec = aspec->element_spec;
          gint        length       = gimp_value_array_length (value_array);
          gint        i;

          for (i = 0; i < length; i++)
            {
              GValue *element = gimp_value_array_index (value_array, i);

              /* need to fixup value type, or ensure that the array
               * value is initialized at all
               */
              if (! g_value_type_compatible (G_VALUE_TYPE (element),
                                             G_PARAM_SPEC_VALUE_TYPE (element_spec)))
                {
                  if (G_VALUE_TYPE (element) != 0)
                    g_value_unset (element);

                  g_value_init (element, G_PARAM_SPEC_VALUE_TYPE (element_spec));
                  g_param_value_set_default (element_spec, element);
                  changed++;
                }

              /* validate array value against element_spec */
              changed += g_param_value_validate (element_spec, element);
            }
        }
    }

  return changed;
}

static gint
gimp_param_value_array_values_cmp (GParamSpec   *pspec,
                                   const GValue *value1,
                                   const GValue *value2)
{
  GimpParamSpecValueArray *aspec        = GIMP_PARAM_SPEC_VALUE_ARRAY (pspec);
  GimpValueArray          *value_array1 = value1->data[0].v_pointer;
  GimpValueArray          *value_array2 = value2->data[0].v_pointer;
  gint                     length1;
  gint                     length2;

  if (!value_array1 || !value_array2)
    return value_array2 ? -1 : value_array1 != value_array2;

  length1 = gimp_value_array_length (value_array1);
  length2 = gimp_value_array_length (value_array2);

  if (length1 != length2)
    {
      return length1 < length2 ? -1 : 1;
    }
  else if (! aspec->element_spec)
    {
      /* we need an element specification for comparisons, so there's
       * not much to compare here, try to at least provide stable
       * lesser/greater result
       */
      return length1 < length2 ? -1 : length1 > length2;
    }
  else /* length1 == length2 */
    {
      gint i;

      for (i = 0; i < length1; i++)
        {
          GValue *element1 = gimp_value_array_index (value_array1, i);
          GValue *element2 = gimp_value_array_index (value_array2, i);
          gint    cmp;

          /* need corresponding element types, provide stable result
           * otherwise
           */
          if (G_VALUE_TYPE (element1) != G_VALUE_TYPE (element2))
            return G_VALUE_TYPE (element1) < G_VALUE_TYPE (element2) ? -1 : 1;

          cmp = g_param_values_cmp (aspec->element_spec, element1, element2);
          if (cmp)
            return cmp;
        }

      return 0;
    }
}

/**
 * gimp_param_spec_value_array:
 * @name:         Canonical name of the property specified.
 * @nick:         Nick name of the property specified.
 * @blurb:        Description of the property specified.
 * @element_spec: (nullable): #GParamSpec the contained array's elements
 *                have comply to, or %NULL.
 * @flags:        Flags for the property specified.
 *
 * Creates a new #GimpParamSpecValueArray specifying a
 * [type@GObject.ValueArray] property.
 *
 * See g_param_spec_internal() for details on property names.
 *
 * Returns: (transfer full): The newly created #GimpParamSpecValueArray.
 *
 * Since: 3.0
 **/
GParamSpec *
gimp_param_spec_value_array (const gchar *name,
                             const gchar *nick,
                             const gchar *blurb,
                             GParamSpec  *element_spec,
                             GParamFlags  flags)
{
  GimpParamSpecValueArray *aspec;

  if (element_spec)
    g_return_val_if_fail (G_IS_PARAM_SPEC (element_spec), NULL);

  aspec = g_param_spec_internal (GIMP_TYPE_PARAM_VALUE_ARRAY,
                                 name,
                                 nick,
                                 blurb,
                                 flags);
  if (element_spec)
    {
      aspec->element_spec = g_param_spec_ref (element_spec);
      g_param_spec_sink (element_spec);
    }

  return G_PARAM_SPEC (aspec);
}

/**
 * gimp_param_spec_value_array_get_element_spec:
 * @pspec: a #GParamSpec to hold a #GimpParamSpecValueArray value.
 *
 * Returns: (transfer none): param spec for elements of the value array.
 *
 * Since: 3.0
 **/
GParamSpec *
gimp_param_spec_value_array_get_element_spec (GParamSpec *pspec)
{
  g_return_val_if_fail (GIMP_IS_PARAM_SPEC_VALUE_ARRAY (pspec), NULL);

  return GIMP_PARAM_SPEC_VALUE_ARRAY (pspec)->element_spec;
}

/* --- end libammoos/base/fieldbase/gimpvaluearray.c --- */

/* --- begin libammoos/base/fieldbase/gimpwire.c --- */
/* LIBGIMP - The AmmoOS Image Library
 * Copyright (C) 1995-1997 Peter Mattis and Spencer Kimball
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

#include <glib-object.h>

#include <libgimpcolor/gimpcolortypes.h>

#include "gimpwire.h"


typedef struct _GimpWireHandler  GimpWireHandler;

struct _GimpWireHandler
{
  guint32             type;
  GimpWireReadFunc    read_func;
  GimpWireWriteFunc   write_func;
  GimpWireDestroyFunc destroy_func;
};


static GHashTable        *wire_ht         = NULL;
static GimpWireIOFunc     wire_read_func  = NULL;
static GimpWireIOFunc     wire_write_func = NULL;
static GimpWireFlushFunc  wire_flush_func = NULL;
static gboolean           wire_error_val  = FALSE;


static void  gimp_wire_init (void);


void
gimp_wire_register (guint32             type,
                    GimpWireReadFunc    read_func,
                    GimpWireWriteFunc   write_func,
                    GimpWireDestroyFunc destroy_func)
{
  GimpWireHandler *handler;

  if (! wire_ht)
    gimp_wire_init ();

  handler = g_hash_table_lookup (wire_ht, &type);

  if (! handler)
    handler = g_slice_new0 (GimpWireHandler);

  handler->type         = type;
  handler->read_func    = read_func;
  handler->write_func   = write_func;
  handler->destroy_func = destroy_func;

  g_hash_table_insert (wire_ht, &handler->type, handler);
}

void
gimp_wire_set_reader (GimpWireIOFunc read_func)
{
  wire_read_func = read_func;
}

void
gimp_wire_set_writer (GimpWireIOFunc write_func)
{
  wire_write_func = write_func;
}

void
gimp_wire_set_flusher (GimpWireFlushFunc flush_func)
{
  wire_flush_func = flush_func;
}

gboolean
gimp_wire_read (GIOChannel *channel,
                guint8     *buf,
                gsize       count,
                gpointer    user_data)
{
  if (wire_read_func)
    {
      if (!(* wire_read_func) (channel, buf, count, user_data))
        {
          /* Gives a confusing error message most of the time, disable:
          g_warning ("%s: gimp_wire_read: error", g_get_prgname ());
           */
          wire_error_val = TRUE;
          return FALSE;
        }
    }
  else
    {
      GIOStatus  status;
      GError    *error = NULL;
      gsize      bytes;

      while (count > 0)
        {
          do
            {
              bytes = 0;
              status = g_io_channel_read_chars (channel,
                                                (gchar *) buf, count,
                                                &bytes,
                                                &error);
            }
          while (G_UNLIKELY (status == G_IO_STATUS_AGAIN));

          if (G_UNLIKELY (bytes == 0 && status == G_IO_STATUS_EOF))
            {
              g_warning ("%s: gimp_wire_read(): unexpected EOF",
                         g_get_prgname ());
              wire_error_val = TRUE;
              return FALSE;
            }
          else if (G_UNLIKELY (status != G_IO_STATUS_NORMAL))
            {
              if (error)
                {
                  g_warning ("%s: gimp_wire_read(): error: %s",
                             g_get_prgname (), error->message);
                  g_error_free (error);
                }
              else
                {
                  g_warning ("%s: gimp_wire_read(): error",
                             g_get_prgname ());
                }

              wire_error_val = TRUE;
              return FALSE;
            }

          count -= bytes;
          buf += bytes;
        }
    }

  return TRUE;
}

gboolean
gimp_wire_write (GIOChannel   *channel,
                 const guint8 *buf,
                 gsize         count,
                 gpointer      user_data)
{
  if (wire_write_func)
    {
      if (!(* wire_write_func) (channel, (guint8 *) buf, count, user_data))
        {
          g_warning ("%s: gimp_wire_write: error", g_get_prgname ());
          wire_error_val = TRUE;
          return FALSE;
        }
    }
  else
    {
      GIOStatus  status;
      GError    *error = NULL;
      gsize      bytes;

      while (count > 0)
        {
          do
            {
              bytes = 0;
              status = g_io_channel_write_chars (channel,
                                                 (const gchar *) buf, count,
                                                 &bytes,
                                                 &error);
            }
          while (G_UNLIKELY (status == G_IO_STATUS_AGAIN));

          if (G_UNLIKELY (status != G_IO_STATUS_NORMAL))
            {
              if (error)
                {
                  g_warning ("%s: gimp_wire_write(): error: %s",
                             g_get_prgname (), error->message);
                  g_error_free (error);
                }
              else
                {
                  g_warning ("%s: gimp_wire_write(): error",
                             g_get_prgname ());
                }

              wire_error_val = TRUE;
              return FALSE;
            }

          count -= bytes;
          buf += bytes;
        }
    }

  return TRUE;
}

gboolean
gimp_wire_flush (GIOChannel *channel,
                 gpointer    user_data)
{
  if (wire_flush_func)
    return (* wire_flush_func) (channel, user_data);

  return FALSE;
}

gboolean
gimp_wire_error (void)
{
  return wire_error_val;
}

void
gimp_wire_clear_error (void)
{
  wire_error_val = FALSE;
}

gboolean
gimp_wire_read_msg (GIOChannel      *channel,
                    GimpWireMessage *msg,
                    gpointer         user_data)
{
  GimpWireHandler *handler;

  if (G_UNLIKELY (! wire_ht))
    g_error ("gimp_wire_read_msg: the wire protocol has not been initialized");

  if (wire_error_val)
    return !wire_error_val;

  if (! _gimp_wire_read_int32 (channel, &msg->type, 1, user_data))
    return FALSE;

  handler = g_hash_table_lookup (wire_ht, &msg->type);

  if (G_UNLIKELY (! handler))
    g_error ("gimp_wire_read_msg: could not find handler for message: %d",
             msg->type);

  (* handler->read_func) (channel, msg, user_data);

  return !wire_error_val;
}

gboolean
gimp_wire_write_msg (GIOChannel      *channel,
                     GimpWireMessage *msg,
                     gpointer         user_data)
{
  GimpWireHandler *handler;

  if (G_UNLIKELY (! wire_ht))
    g_error ("gimp_wire_write_msg: the wire protocol has not been initialized");

  if (wire_error_val)
    return !wire_error_val;

  handler = g_hash_table_lookup (wire_ht, &msg->type);

  if (G_UNLIKELY (! handler))
    g_error ("gimp_wire_write_msg: could not find handler for message: %d",
             msg->type);

  if (! _gimp_wire_write_int32 (channel, &msg->type, 1, user_data))
    return FALSE;

  (* handler->write_func) (channel, msg, user_data);

  return !wire_error_val;
}

void
gimp_wire_destroy (GimpWireMessage *msg)
{
  GimpWireHandler *handler;

  if (G_UNLIKELY (! wire_ht))
    g_error ("gimp_wire_destroy: the wire protocol has not been initialized");

  handler = g_hash_table_lookup (wire_ht, &msg->type);

  if (G_UNLIKELY (! handler))
    g_error ("gimp_wire_destroy: could not find handler for message: %d\n",
             msg->type);

  (* handler->destroy_func) (msg);
}

gboolean
_gimp_wire_read_int64 (GIOChannel *channel,
                       guint64    *data,
                       gint        count,
                       gpointer    user_data)
{
  g_return_val_if_fail (count >= 0, FALSE);

  if (count > 0)
    {
      if (! _gimp_wire_read_int8 (channel,
                                  (guint8 *) data, count * 8, user_data))
        return FALSE;

      while (count--)
        {
          *data = GUINT64_FROM_BE (*data);
          data++;
        }
    }

  return TRUE;
}

gboolean
_gimp_wire_read_int32 (GIOChannel *channel,
                       guint32    *data,
                       gint        count,
                       gpointer    user_data)
{
  g_return_val_if_fail (count >= 0, FALSE);

  if (count > 0)
    {
      if (! _gimp_wire_read_int8 (channel,
                                  (guint8 *) data, count * 4, user_data))
        return FALSE;

      while (count--)
        {
          *data = g_ntohl (*data);
          data++;
        }
    }

  return TRUE;
}

gboolean
_gimp_wire_read_int16 (GIOChannel *channel,
                       guint16    *data,
                       gint        count,
                       gpointer    user_data)
{
  g_return_val_if_fail (count >= 0, FALSE);

  if (count > 0)
    {
      if (! _gimp_wire_read_int8 (channel,
                                  (guint8 *) data, count * 2, user_data))
        return FALSE;

      while (count--)
        {
          *data = g_ntohs (*data);
          data++;
        }
    }

  return TRUE;
}

gboolean
_gimp_wire_read_int8 (GIOChannel *channel,
                      guint8     *data,
                      gint        count,
                      gpointer    user_data)
{
  g_return_val_if_fail (count >= 0, FALSE);

  return gimp_wire_read (channel, data, count, user_data);
}

gboolean
_gimp_wire_read_double (GIOChannel *channel,
                        gdouble    *data,
                        gint        count,
                        gpointer    user_data)
{
  gdouble *t;
  guint8   tmp[8];
  gint     i;

  g_return_val_if_fail (count >= 0, FALSE);

  t = (gdouble *) tmp;

  for (i = 0; i < count; i++)
    {
#if (G_BYTE_ORDER == G_LITTLE_ENDIAN)
      gint j;
#endif

      if (! _gimp_wire_read_int8 (channel, tmp, 8, user_data))
        return FALSE;

#if (G_BYTE_ORDER == G_LITTLE_ENDIAN)
      for (j = 0; j < 4; j++)
        {
          guint8 swap;

          swap       = tmp[j];
          tmp[j]     = tmp[7 - j];
          tmp[7 - j] = swap;
        }
#endif

      data[i] = *t;
    }

  return TRUE;
}

gboolean
_gimp_wire_read_string (GIOChannel  *channel,
                        gchar      **data,
                        gint         count,
                        gpointer     user_data)
{
  gint i;

  g_return_val_if_fail (count >= 0, FALSE);

  for (i = 0; i < count; i++)
    {
      guint32 tmp;

      if (! _gimp_wire_read_int32 (channel, &tmp, 1, user_data))
        return FALSE;

      if (tmp > 0)
        {
          data[i] = g_try_new (gchar, tmp);

          if (! data[i])
            {
              g_printerr ("%s: failed to allocate %u bytes\n", G_STRFUNC, tmp);
              return FALSE;
            }

          if (! _gimp_wire_read_int8 (channel,
                                      (guint8 *) data[i], tmp, user_data))
            {
              g_free (data[i]);
              return FALSE;
            }

          /*  make sure that the string is NULL-terminated  */
          data[i][tmp - 1] = '\0';
        }
      else
        {
          data[i] = NULL;
        }
    }

  return TRUE;
}

gboolean
_gimp_wire_read_gegl_color (GIOChannel  *channel,
                            GBytes     **pixel_data,
                            GBytes     **icc_data,
                            gchar      **encoding,
                            gint         count,
                            gpointer     user_data)
{
  gint i;

  g_return_val_if_fail (count >= 0, FALSE);

  for (i = 0; i < count; i++)
    {
      guint32 size;
      guint8  pixel[40];
      guint32 icc_length;

      if (! _gimp_wire_read_int32 (channel,
                                   &size, 1,
                                   user_data)                              ||
          size > 40                                                        ||
          ! _gimp_wire_read_int8 (channel, pixel, size, user_data)         ||
          ! _gimp_wire_read_string (channel, &(encoding[i]), 1, user_data) ||
          ! _gimp_wire_read_int32 (channel, &icc_length, 1, user_data))
        {
          g_clear_pointer (&(encoding[i]), g_free);
          return FALSE;
        }
      pixel_data[i] = (size > 0 ? g_bytes_new (pixel, size) : NULL);

      /* Read space (profile data). */

      icc_data[i] = NULL;
      if (icc_length > 0)
        {
          guint8 *icc;

          icc = g_new0 (guint8, icc_length);

          if (! _gimp_wire_read_int8 (channel, icc, icc_length, user_data))
            {
              g_clear_pointer (&(encoding[i]), g_free);
              g_clear_pointer (&icc, g_free);
              return FALSE;
            }

          icc_data[i] = g_bytes_new_take (icc, icc_length);
        }
    }

  return TRUE;
}

gboolean
_gimp_wire_write_int64 (GIOChannel    *channel,
                        const guint64 *data,
                        gint           count,
                        gpointer       user_data)
{
  g_return_val_if_fail (count >= 0, FALSE);

  if (count > 0)
    {
      gint i;

      for (i = 0; i < count; i++)
        {
          guint64 tmp = GUINT64_TO_BE (data[i]);

          if (! _gimp_wire_write_int8 (channel,
                                       (const guint8 *) &tmp, 8, user_data))
            return FALSE;
        }
    }

  return TRUE;
}

gboolean
_gimp_wire_write_int32 (GIOChannel    *channel,
                        const guint32 *data,
                        gint           count,
                        gpointer       user_data)
{
  g_return_val_if_fail (count >= 0, FALSE);

  if (count > 0)
    {
      gint i;

      for (i = 0; i < count; i++)
        {
          guint32 tmp = g_htonl (data[i]);

          if (! _gimp_wire_write_int8 (channel,
                                       (const guint8 *) &tmp, 4, user_data))
            return FALSE;
        }
    }

  return TRUE;
}

gboolean
_gimp_wire_write_int16 (GIOChannel    *channel,
                        const guint16 *data,
                        gint           count,
                        gpointer       user_data)
{
  g_return_val_if_fail (count >= 0, FALSE);

  if (count > 0)
    {
      gint i;

      for (i = 0; i < count; i++)
        {
          guint16 tmp = g_htons (data[i]);

          if (! _gimp_wire_write_int8 (channel,
                                       (const guint8 *) &tmp, 2, user_data))
            return FALSE;
        }
    }

  return TRUE;
}

gboolean
_gimp_wire_write_int8 (GIOChannel   *channel,
                       const guint8 *data,
                       gint          count,
                       gpointer      user_data)
{
  g_return_val_if_fail (count >= 0, FALSE);

  return gimp_wire_write (channel, data, count, user_data);
}

gboolean
_gimp_wire_write_double (GIOChannel    *channel,
                         const gdouble *data,
                         gint           count,
                         gpointer       user_data)
{
  gdouble *t;
  guint8   tmp[8];
  gint     i;
#if (G_BYTE_ORDER == G_LITTLE_ENDIAN)
  gint     j;
#endif

  g_return_val_if_fail (count >= 0, FALSE);

  t = (gdouble *) tmp;

  for (i = 0; i < count; i++)
    {
      *t = data[i];

#if (G_BYTE_ORDER == G_LITTLE_ENDIAN)
      for (j = 0; j < 4; j++)
        {
          guint8 swap;

          swap       = tmp[j];
          tmp[j]     = tmp[7 - j];
          tmp[7 - j] = swap;
        }
#endif

      if (! _gimp_wire_write_int8 (channel, tmp, 8, user_data))
        return FALSE;

#if 0
      {
        gint k;

        g_print ("Wire representation of %f:\t", data[i]);

        for (k = 0; k < 8; k++)
          g_print ("%02x ", tmp[k]);

        g_print ("\n");
      }
#endif
    }

  return TRUE;
}

gboolean
_gimp_wire_write_string (GIOChannel  *channel,
                         gchar      **data,
                         gint         count,
                         gpointer     user_data)
{
  gint i;

  g_return_val_if_fail (count >= 0, FALSE);

  for (i = 0; i < count; i++)
    {
      guint32 tmp;

      if (data[i])
        tmp = strlen (data[i]) + 1;
      else
        tmp = 0;

      if (! _gimp_wire_write_int32 (channel, &tmp, 1, user_data))
        return FALSE;

      if (tmp > 0)
        if (! _gimp_wire_write_int8 (channel,
                                     (const guint8 *) data[i], tmp, user_data))
          return FALSE;
    }

  return TRUE;
}

gboolean
_gimp_wire_write_gegl_color (GIOChannel  *channel,
                             GBytes     **pixel_data,
                             GBytes     **icc_data,
                             gchar      **encoding,
                             gint         count,
                             gpointer     user_data)
{
  gint i;

  g_return_val_if_fail (count >= 0, FALSE);

  for (i = 0; i < count; i++)
    {
      const guint8 *pixel      = NULL;
      gsize         bpp        = 0;
      const guint8 *icc        = NULL;
      gsize         icc_length = 0;

      if (pixel_data[i])
        pixel = g_bytes_get_data (pixel_data[i], &bpp);
      if (icc_data[i])
        icc = g_bytes_get_data (icc_data[i], &icc_length);

      if (! _gimp_wire_write_int32 (channel, (const guint32 *) &bpp, 1, user_data))
        return FALSE;

      if (bpp > 0 && ! _gimp_wire_write_int8 (channel, pixel, bpp, user_data))
        return FALSE;

      if (! _gimp_wire_write_string (channel, &(encoding[i]), 1, user_data) ||
          ! _gimp_wire_write_int32 (channel, (const guint32 *) &icc_length, 1, user_data))
        return FALSE;

      if (icc_length > 0 && ! _gimp_wire_write_int8 (channel, icc, icc_length, user_data))
        return FALSE;
    }

  return TRUE;
}

static guint
gimp_wire_hash (const guint32 *key)
{
  return *key;
}

static gboolean
gimp_wire_compare (const guint32 *a,
                   const guint32 *b)
{
  return (*a == *b);
}

static void
gimp_wire_init (void)
{
  if (! wire_ht)
    wire_ht = g_hash_table_new ((GHashFunc) gimp_wire_hash,
                                (GCompareFunc) gimp_wire_compare);
}

/* --- end libammoos/base/fieldbase/gimpwire.c --- */

/* --- begin libammoos/base/fieldbase/test-cpu-accel.c --- */
/* A small test program for the CPU detection code */

#include "config.h"

#include <stdlib.h>

#include <glib.h>

#include "gimpcpuaccel.h"


static void
cpu_accel_print_results (void)
{
#if defined(ARCH_X86) || defined(ARCH_PPC)
  GimpCpuAccelFlags  support;

  g_printerr ("Testing CPU features...\n");

  support = gimp_cpu_accel_get_support ();
#endif

#ifdef ARCH_X86
  g_printerr ("  mmx     : %s\n",
              (support & GIMP_CPU_ACCEL_X86_MMX)     ? "yes" : "no");
  g_printerr ("  3dnow   : %s\n",
              (support & GIMP_CPU_ACCEL_X86_3DNOW)   ? "yes" : "no");
  g_printerr ("  mmxext  : %s\n",
              (support & GIMP_CPU_ACCEL_X86_MMXEXT)  ? "yes" : "no");
  g_printerr ("  sse     : %s\n",
              (support & GIMP_CPU_ACCEL_X86_SSE)     ? "yes" : "no");
  g_printerr ("  sse2    : %s\n",
              (support & GIMP_CPU_ACCEL_X86_SSE2)    ? "yes" : "no");
  g_printerr ("  sse3    : %s\n",
              (support & GIMP_CPU_ACCEL_X86_SSE3)    ? "yes" : "no");
#endif
#ifdef ARCH_PPC
  g_printerr ("  altivec : %s\n",
              (support & GIMP_CPU_ACCEL_PPC_ALTIVEC) ? "yes" : "no");
#endif
  g_printerr ("\n");
}

int
main (void)
{
  cpu_accel_print_results ();

  return EXIT_SUCCESS;
}

/* --- end libammoos/base/fieldbase/test-cpu-accel.c --- */
