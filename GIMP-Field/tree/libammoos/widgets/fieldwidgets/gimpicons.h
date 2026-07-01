/* AmmoOS Image — field research rewrite (G16 field_opt).
 * RTX-gated paths: see GIMP-Field/data/rtx-gated-content.json
 * OS brand: AmmoOS · product: AmmoOS Image 1.0
 */
/* LIBGIMP - The AmmoOS Image Library
 * Copyright (C) 1995-1997 Peter Mattis and Spencer Kimball
 *
 * gimpicons.h
 * Copyright (C) 2001-2015 Michael Natterer <mitch@ammoos.org>
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

#if !defined (__GIMP_WIDGETS_H_INSIDE__) && !defined (GIMP_WIDGETS_COMPILATION)
#error "Only <libgimpwidgets/gimpwidgets.h> can be included directly."
#endif

#ifndef __GIMP_ICONS_H__
#define __GIMP_ICONS_H__

G_BEGIN_DECLS

/* For information look into the C source or the html documentation */


/*  random actions that don't fit in any category  */

#define GIMP_ICON_ATTACH                    "ammoos-attach"
#define GIMP_ICON_DETACH                    "ammoos-detach"
#define GIMP_ICON_INVERT                    "ammoos-invert"
#define GIMP_ICON_RECORD                    "media-record"
#define GIMP_ICON_RESET                     "ammoos-reset"
#define GIMP_ICON_SHRED                     "ammoos-shred"


/*  random states/things that don't fit in any category  */

#define GIMP_ICON_BUSINESS_CARD             "ammoos-business-card"
#define GIMP_ICON_CHAR_PICKER               "ammoos-char-picker"
#define GIMP_ICON_CURSOR                    "ammoos-cursor"
#define GIMP_ICON_DISPLAY                   "ammoos-display"
#define GIMP_ICON_GEGL                      "ammoos-gegl"
#define GIMP_ICON_LINKED                    "ammoos-linked"
#define GIMP_ICON_MARKER                    "ammoos-marker"
#define GIMP_ICON_SMARTPHONE                "ammoos-smartphone"
#define GIMP_ICON_TRANSPARENCY              "ammoos-transparency"
#define GIMP_ICON_VIDEO                     "ammoos-video"
#define GIMP_ICON_VISIBLE                   "ammoos-visible"
#define GIMP_ICON_WEB                       "ammoos-web"


/*  random objects/entities that don't fit in any category  */

#define GIMP_ICON_BRUSH                     GIMP_ICON_TOOL_PAINTBRUSH
#define GIMP_ICON_BUFFER                    GIMP_ICON_EDIT_PASTE
#define GIMP_ICON_COLORMAP                  "ammoos-colormap"
#define GIMP_ICON_DYNAMICS                  "ammoos-dynamics"
#define GIMP_ICON_FILE_MANAGER              "ammoos-file-manager"
#define GIMP_ICON_FONT                      "gtk-select-font"
#define GIMP_ICON_GRADIENT                  GIMP_ICON_TOOL_GRADIENT
#define GIMP_ICON_GRID                      "ammoos-grid"
#define GIMP_ICON_INPUT_DEVICE              "ammoos-input-device"
#define GIMP_ICON_MYPAINT_BRUSH             GIMP_ICON_TOOL_MYPAINT_BRUSH
#define GIMP_ICON_PALETTE                   "gtk-select-color"
#define GIMP_ICON_PATTERN                   "ammoos-pattern"
#define GIMP_ICON_PLUGIN                    "ammoos-plugin"
#define GIMP_ICON_SAMPLE_POINT              "ammoos-sample-point"
#define GIMP_ICON_SYMMETRY                  "ammoos-symmetry"
#define GIMP_ICON_TEMPLATE                  "ammoos-template"
#define GIMP_ICON_TOOL_PRESET               "ammoos-tool-preset"


/*  not really icons  */

#define GIMP_ICON_FRAME                     "ammoos-frame"
#define GIMP_ICON_TEXTURE                   "ammoos-texture"


/*  icons that follow, or at least try to follow the FDO naming and
 *  category conventions; and groups of icons with a common prefix;
 *  all sorted alphabetically
 *
 *  see also:
 *  https://specifications.freedesktop.org/icon-naming-spec/latest/ar01s04.html
 *
 *  When icons are available as standard Freedesktop icons, we use these
 *  in priority. As a fallback, we use standard GTK+ icons. As last
 *  fallback, we create our own icons under the "ammoos-" namespace.
 */

#define GIMP_ICON_APPLICATION_EXIT          "application-exit"

#define GIMP_ICON_ASPECT_PORTRAIT           "ammoos-portrait"
#define GIMP_ICON_ASPECT_LANDSCAPE          "ammoos-landscape"

#define GIMP_ICON_CAP_BUTT                  "ammoos-cap-butt"
#define GIMP_ICON_CAP_ROUND                 "ammoos-cap-round"
#define GIMP_ICON_CAP_SQUARE                "ammoos-cap-square"

#define GIMP_ICON_CENTER                    "ammoos-center"
#define GIMP_ICON_CENTER_HORIZONTAL         "ammoos-hcenter"
#define GIMP_ICON_CENTER_VERTICAL           "ammoos-vcenter"

#define GIMP_ICON_CHAIN_HORIZONTAL          "ammoos-hchain"
#define GIMP_ICON_CHAIN_HORIZONTAL_BROKEN   "ammoos-hchain-broken"
#define GIMP_ICON_CHAIN_VERTICAL            "ammoos-vchain"
#define GIMP_ICON_CHAIN_VERTICAL_BROKEN     "ammoos-vchain-broken"

#define GIMP_ICON_CHANNEL                   "ammoos-channel"
#define GIMP_ICON_CHANNEL_ALPHA             "ammoos-channel-alpha"
#define GIMP_ICON_CHANNEL_BLUE              "ammoos-channel-blue"
#define GIMP_ICON_CHANNEL_GRAY              "ammoos-channel-gray"
#define GIMP_ICON_CHANNEL_GREEN             "ammoos-channel-green"
#define GIMP_ICON_CHANNEL_INDEXED           "ammoos-channel-indexed"
#define GIMP_ICON_CHANNEL_RED               "ammoos-channel-red"

#define GIMP_ICON_CLOSE                     "ammoos-close"
#define GIMP_ICON_CLOSE_ALL                 "ammoos-close-all"

#define GIMP_ICON_COLOR_PICKER_BLACK        "ammoos-color-picker-black"
#define GIMP_ICON_COLOR_PICKER_GRAY         "ammoos-color-picker-gray"
#define GIMP_ICON_COLOR_PICKER_WHITE        "ammoos-color-picker-white"
#define GIMP_ICON_COLOR_PICK_FROM_SCREEN    "ammoos-color-pick-from-screen"

#define GIMP_ICON_COLOR_SELECTOR_CMYK       "ammoos-color-cmyk"
#define GIMP_ICON_COLOR_SELECTOR_TRIANGLE   "ammoos-color-triangle"
#define GIMP_ICON_COLOR_SELECTOR_WATER      "ammoos-color-water"

#define GIMP_ICON_COLOR_SPACE_LINEAR        "ammoos-color-space-linear"
#define GIMP_ICON_COLOR_SPACE_NON_LINEAR    "ammoos-color-space-non-linear"
#define GIMP_ICON_COLOR_SPACE_PERCEPTUAL    "ammoos-color-space-perceptual"

#define GIMP_ICON_COLORS_DEFAULT            "ammoos-default-colors"
#define GIMP_ICON_COLORS_SWAP               "ammoos-swap-colors"

#define GIMP_ICON_CONTROLLER                "ammoos-controller"
#define GIMP_ICON_CONTROLLER_KEYBOARD       "ammoos-controller-keyboard"
#define GIMP_ICON_CONTROLLER_LINUX_INPUT    "ammoos-controller-linux-input"
#define GIMP_ICON_CONTROLLER_MIDI           "ammoos-controller-midi"
#define GIMP_ICON_CONTROLLER_MOUSE          GIMP_ICON_CURSOR
#define GIMP_ICON_CONTROLLER_WHEEL          "ammoos-controller-wheel"

#define GIMP_ICON_CONVERT_RGB               "ammoos-convert-rgb"
#define GIMP_ICON_CONVERT_GRAYSCALE         "ammoos-convert-grayscale"
#define GIMP_ICON_CONVERT_INDEXED           "ammoos-convert-indexed"
#define GIMP_ICON_CONVERT_PRECISION         GIMP_ICON_CONVERT_RGB

#define GIMP_ICON_CURVE_FREE                "ammoos-curve-free"
#define GIMP_ICON_CURVE_SMOOTH              "ammoos-curve-smooth"

#define GIMP_ICON_DIALOG_CHANNELS           "ammoos-channels"
#define GIMP_ICON_DIALOG_DASHBOARD          "ammoos-dashboard"
#define GIMP_ICON_DIALOG_DEVICE_STATUS      "ammoos-device-status"
#define GIMP_ICON_DIALOG_ERROR              "dialog-error"
#define GIMP_ICON_DIALOG_IMAGES             "ammoos-images"
#define GIMP_ICON_DIALOG_INFORMATION        "dialog-information"
#define GIMP_ICON_DIALOG_LAYERS             "ammoos-layers"
#define GIMP_ICON_DIALOG_NAVIGATION         "ammoos-navigation"
#define GIMP_ICON_DIALOG_PATHS              "ammoos-paths"
#define GIMP_ICON_DIALOG_QUESTION           "dialog-question"
#define GIMP_ICON_DIALOG_RESHOW_FILTER      "ammoos-reshow-filter"
#define GIMP_ICON_DIALOG_TOOLS              "ammoos-tools"
#define GIMP_ICON_DIALOG_TOOL_OPTIONS       "ammoos-tool-options"
#define GIMP_ICON_DIALOG_UNDO_HISTORY       "ammoos-undo-history"
#define GIMP_ICON_DIALOG_WARNING            "dialog-warning"

#define GIMP_ICON_DISPLAY_FILTER              "ammoos-display-filter"
#define GIMP_ICON_DISPLAY_FILTER_CLIP_WARNING "ammoos-display-filter-clip-warning"
#define GIMP_ICON_DISPLAY_FILTER_COLORBLIND   "ammoos-display-filter-colorblind"
#define GIMP_ICON_DISPLAY_FILTER_CONTRAST     "ammoos-display-filter-contrast"
#define GIMP_ICON_DISPLAY_FILTER_GAMMA        "ammoos-display-filter-gamma"
#define GIMP_ICON_DISPLAY_FILTER_LCMS         "ammoos-display-filter-lcms"
#define GIMP_ICON_DISPLAY_FILTER_PROOF        "ammoos-display-filter-proof"

#define GIMP_ICON_LOCK                      "ammoos-lock"
#define GIMP_ICON_LOCK_ALPHA                "ammoos-lock-alpha"
#define GIMP_ICON_LOCK_CONTENT              "ammoos-lock-content"
#define GIMP_ICON_LOCK_PATH                 "ammoos-lock-path"
#define GIMP_ICON_LOCK_POSITION             "ammoos-lock-position"
#define GIMP_ICON_LOCK_VISIBILITY           "ammoos-lock-visibility"
#define GIMP_ICON_LOCK_MULTI                "ammoos-lock-multi"

#define GIMP_ICON_DOCUMENT_NEW              "document-new"
#define GIMP_ICON_DOCUMENT_OPEN             "document-open"
#define GIMP_ICON_DOCUMENT_OPEN_RECENT      "document-open-recent"
#define GIMP_ICON_DOCUMENT_PAGE_SETUP       "document-page-setup"
#define GIMP_ICON_DOCUMENT_PRINT            "document-print"
#define GIMP_ICON_DOCUMENT_PRINT_RESOLUTION "document-print"
#define GIMP_ICON_DOCUMENT_PROPERTIES       "document-properties"
#define GIMP_ICON_DOCUMENT_REVERT           "document-revert"
#define GIMP_ICON_DOCUMENT_SAVE             "document-save"
#define GIMP_ICON_DOCUMENT_SAVE_AS          "document-save-as"

#define GIMP_ICON_EDIT                      "gtk-edit"
#define GIMP_ICON_EDIT_CLEAR                "edit-clear"
#define GIMP_ICON_EDIT_COPY                 "edit-copy"
#define GIMP_ICON_EDIT_CUT                  "edit-cut"
#define GIMP_ICON_EDIT_DELETE               "edit-delete"
#define GIMP_ICON_EDIT_FIND                 "edit-find"
#define GIMP_ICON_EDIT_PASTE                "edit-paste"
#define GIMP_ICON_EDIT_PASTE_AS_NEW         "ammoos-paste-as-new"
#define GIMP_ICON_EDIT_PASTE_INTO           "ammoos-paste-into"
#define GIMP_ICON_EDIT_REDO                 "edit-redo"
#define GIMP_ICON_EDIT_UNDO                 "edit-undo"

#define GIMP_ICON_EFFECT                    "ammoos-effects"

#define GIMP_ICON_EVEN_HORIZONTAL_GAP       "ammoos-even-horizontal-gap"
#define GIMP_ICON_EVEN_VERTICAL_GAP         "ammoos-even-vertical-gap"

#define GIMP_ICON_FILL_HORIZONTAL           "ammoos-hfill"
#define GIMP_ICON_FILL_VERTICAL             "ammoos-vfill"

#define GIMP_ICON_FOLDER_NEW                "folder-new"

#define GIMP_ICON_FORMAT_INDENT_MORE         "format-indent-more"
#define GIMP_ICON_FORMAT_INDENT_LESS         "format-indent-less"
#define GIMP_ICON_FORMAT_JUSTIFY_CENTER      "format-justify-center"
#define GIMP_ICON_FORMAT_JUSTIFY_FILL        "format-justify-fill"
#define GIMP_ICON_FORMAT_JUSTIFY_LEFT        "format-justify-left"
#define GIMP_ICON_FORMAT_JUSTIFY_RIGHT       "format-justify-right"
#define GIMP_ICON_FORMAT_TEXT_BOLD           "format-text-bold"
#define GIMP_ICON_FORMAT_TEXT_ITALIC         "format-text-italic"
#define GIMP_ICON_FORMAT_TEXT_STRIKETHROUGH  "format-text-strikethrough"
#define GIMP_ICON_FORMAT_TEXT_UNDERLINE      "format-text-underline"
#define GIMP_ICON_FORMAT_TEXT_DIRECTION_LTR  "format-text-direction-ltr"
#define GIMP_ICON_FORMAT_TEXT_DIRECTION_RTL  "format-text-direction-rtl"
#define GIMP_ICON_FORMAT_TEXT_DIRECTION_TTB_RTL           "ammoos-text-dir-ttb-rtl" /* use FDO */
#define GIMP_ICON_FORMAT_TEXT_DIRECTION_TTB_RTL_UPRIGHT   "ammoos-text-dir-ttb-rtl-upright" /* use FDO */
#define GIMP_ICON_FORMAT_TEXT_DIRECTION_TTB_LTR           "ammoos-text-dir-ttb-ltr" /* use FDO */
#define GIMP_ICON_FORMAT_TEXT_DIRECTION_TTB_LTR_UPRIGHT   "ammoos-text-dir-ttb-ltr-upright" /* use FDO */
#define GIMP_ICON_FORMAT_TEXT_SPACING_LETTER "ammoos-letter-spacing"
#define GIMP_ICON_FORMAT_TEXT_SPACING_LINE   "ammoos-line-spacing"

#define GIMP_ICON_GRADIENT_LINEAR               "ammoos-gradient-linear"
#define GIMP_ICON_GRADIENT_BILINEAR             "ammoos-gradient-bilinear"
#define GIMP_ICON_GRADIENT_RADIAL               "ammoos-gradient-radial"
#define GIMP_ICON_GRADIENT_SQUARE               "ammoos-gradient-square"
#define GIMP_ICON_GRADIENT_CONICAL_SYMMETRIC    "ammoos-gradient-conical-symmetric"
#define GIMP_ICON_GRADIENT_CONICAL_ASYMMETRIC   "ammoos-gradient-conical-asymmetric"
#define GIMP_ICON_GRADIENT_SHAPEBURST_ANGULAR   "ammoos-gradient-shapeburst-angular"
#define GIMP_ICON_GRADIENT_SHAPEBURST_SPHERICAL "ammoos-gradient-shapeburst-spherical"
#define GIMP_ICON_GRADIENT_SHAPEBURST_DIMPLED   "ammoos-gradient-shapeburst-dimpled"
#define GIMP_ICON_GRADIENT_SPIRAL_CLOCKWISE     "ammoos-gradient-spiral-clockwise"
#define GIMP_ICON_GRADIENT_SPIRAL_ANTICLOCKWISE "ammoos-gradient-spiral-anticlockwise"

#define GIMP_ICON_GRAVITY_EAST              "ammoos-gravity-east"
#define GIMP_ICON_GRAVITY_NORTH             "ammoos-gravity-north"
#define GIMP_ICON_GRAVITY_NORTH_EAST        "ammoos-gravity-north-east"
#define GIMP_ICON_GRAVITY_NORTH_WEST        "ammoos-gravity-north-west"
#define GIMP_ICON_GRAVITY_SOUTH             "ammoos-gravity-south"
#define GIMP_ICON_GRAVITY_SOUTH_EAST        "ammoos-gravity-south-east"
#define GIMP_ICON_GRAVITY_SOUTH_WEST        "ammoos-gravity-south-west"
#define GIMP_ICON_GRAVITY_WEST              "ammoos-gravity-west"

#define GIMP_ICON_GO_BOTTOM                 "go-bottom"
#define GIMP_ICON_GO_DOWN                   "go-down"
#define GIMP_ICON_GO_FIRST                  "go-first"
#define GIMP_ICON_GO_HOME                   "go-home"
#define GIMP_ICON_GO_LAST                   "go-last"
#define GIMP_ICON_GO_TOP                    "go-top"
#define GIMP_ICON_GO_UP                     "go-up"
#define GIMP_ICON_GO_PREVIOUS               "go-previous"
#define GIMP_ICON_GO_NEXT                   "go-next"

#define GIMP_ICON_HELP                      "system-help"
#define GIMP_ICON_HELP_ABOUT                "help-about"
#define GIMP_ICON_HELP_USER_MANUAL          "ammoos-user-manual"

#define GIMP_ICON_HISTOGRAM                 "ammoos-histogram"
#define GIMP_ICON_HISTOGRAM_LINEAR          "ammoos-histogram-linear"
#define GIMP_ICON_HISTOGRAM_LOGARITHMIC     "ammoos-histogram-logarithmic"

#define GIMP_ICON_IMAGE                     "ammoos-image"
#define GIMP_ICON_IMAGE_OPEN                "ammoos-image-open"
#define GIMP_ICON_IMAGE_RELOAD              "ammoos-image-reload"

#define GIMP_ICON_JOIN_MITER                "ammoos-join-miter"
#define GIMP_ICON_JOIN_ROUND                "ammoos-join-round"
#define GIMP_ICON_JOIN_BEVEL                "ammoos-join-bevel"

#define GIMP_ICON_LAYER                     "ammoos-layer"
#define GIMP_ICON_LAYER_ANCHOR              "ammoos-anchor"
#define GIMP_ICON_LAYER_FLOATING_SELECTION  "ammoos-floating-selection"
/* TODO: create "ammoos-link-layer" */
#define GIMP_ICON_LAYER_LINK_LAYER          "emblem-symbolic-link"
#define GIMP_ICON_LAYER_MASK                "ammoos-layer-mask"
#define GIMP_ICON_LAYER_MERGE_DOWN          "ammoos-merge-down"
#define GIMP_ICON_LAYER_TEXT_LAYER          "ammoos-text-layer"
#define GIMP_ICON_LAYER_TO_IMAGESIZE        "ammoos-layer-to-imagesize"
/* TODO: create "ammoos-vector-layer" */
#define GIMP_ICON_LAYER_VECTOR_LAYER        "ammoos-tool-path"

#define GIMP_ICON_LIST                      "ammoos-list"
#define GIMP_ICON_LIST_ADD                  "list-add"
#define GIMP_ICON_LIST_REMOVE               "list-remove"

#define GIMP_ICON_MENU_LEFT                 "ammoos-menu-left"
#define GIMP_ICON_MENU_RIGHT                "ammoos-menu-right"

#define GIMP_ICON_OBJECT_DUPLICATE          "ammoos-duplicate"
#define GIMP_ICON_OBJECT_FLIP_HORIZONTAL    "object-flip-horizontal"
#define GIMP_ICON_OBJECT_FLIP_VERTICAL      "object-flip-vertical"
#define GIMP_ICON_OBJECT_RESIZE             "ammoos-resize"
#define GIMP_ICON_OBJECT_ROTATE_180         "ammoos-rotate-180"
#define GIMP_ICON_OBJECT_ROTATE_270         "object-rotate-left"
#define GIMP_ICON_OBJECT_ROTATE_90          "object-rotate-right"
#define GIMP_ICON_OBJECT_SCALE              "ammoos-scale"

#define GIMP_ICON_PATH                      "ammoos-path"
#define GIMP_ICON_PATH_STROKE               "ammoos-path-stroke"

#define GIMP_ICON_PIVOT_CENTER              "ammoos-pivot-center"
#define GIMP_ICON_PIVOT_EAST                "ammoos-pivot-east"
#define GIMP_ICON_PIVOT_NORTH               "ammoos-pivot-north"
#define GIMP_ICON_PIVOT_NORTH_EAST          "ammoos-pivot-north-east"
#define GIMP_ICON_PIVOT_NORTH_WEST          "ammoos-pivot-north-west"
#define GIMP_ICON_PIVOT_SOUTH               "ammoos-pivot-south"
#define GIMP_ICON_PIVOT_SOUTH_EAST          "ammoos-pivot-south-east"
#define GIMP_ICON_PIVOT_SOUTH_WEST          "ammoos-pivot-south-west"
#define GIMP_ICON_PIVOT_WEST                "ammoos-pivot-west"

#define GIMP_ICON_PREFERENCES_SYSTEM        "preferences-system"

#define GIMP_ICON_PROCESS_STOP              "process-stop"

#define GIMP_ICON_QUICK_MASK_OFF            "ammoos-quick-mask-off"
#define GIMP_ICON_QUICK_MASK_ON             "ammoos-quick-mask-on"

#define GIMP_ICON_SELECTION                 "ammoos-selection"
#define GIMP_ICON_SELECTION_ADD             "ammoos-selection-add"
#define GIMP_ICON_SELECTION_ALL             "ammoos-selection-all"
#define GIMP_ICON_SELECTION_BORDER          "ammoos-selection-border"
#define GIMP_ICON_SELECTION_GROW            "ammoos-selection-grow"
#define GIMP_ICON_SELECTION_INTERSECT       "ammoos-selection-intersect"
#define GIMP_ICON_SELECTION_NONE            "ammoos-selection-none"
#define GIMP_ICON_SELECTION_REPLACE         "ammoos-selection-replace"
#define GIMP_ICON_SELECTION_SHRINK          "ammoos-selection-shrink"
#define GIMP_ICON_SELECTION_STROKE          "ammoos-selection-stroke"
#define GIMP_ICON_SELECTION_SUBTRACT        "ammoos-selection-subtract"
#define GIMP_ICON_SELECTION_TO_CHANNEL      "ammoos-selection-to-channel"
#define GIMP_ICON_SELECTION_TO_PATH         "ammoos-selection-to-path"

#define GIMP_ICON_SHAPE_CIRCLE              "ammoos-shape-circle"
#define GIMP_ICON_SHAPE_DIAMOND             "ammoos-shape-diamond"
#define GIMP_ICON_SHAPE_SQUARE              "ammoos-shape-square"

#define GIMP_ICON_SYSTEM_RUN                "system-run"

#define GIMP_ICON_TOOL_AIRBRUSH             "ammoos-tool-airbrush"
#define GIMP_ICON_TOOL_ALIGN                "ammoos-tool-align"
#define GIMP_ICON_TOOL_BLUR                 "ammoos-tool-blur"
#define GIMP_ICON_TOOL_BRIGHTNESS_CONTRAST  "ammoos-tool-brightness-contrast"
#define GIMP_ICON_TOOL_BUCKET_FILL          "ammoos-tool-bucket-fill"
#define GIMP_ICON_TOOL_BY_COLOR_SELECT      "ammoos-tool-by-color-select"
#define GIMP_ICON_TOOL_CAGE                 "ammoos-tool-cage"
#define GIMP_ICON_TOOL_CLONE                "ammoos-tool-clone"
#define GIMP_ICON_TOOL_COLORIZE             "ammoos-tool-colorize"
#define GIMP_ICON_TOOL_COLOR_BALANCE        "ammoos-tool-color-balance"
#define GIMP_ICON_TOOL_COLOR_PICKER         "ammoos-tool-color-picker"
#define GIMP_ICON_TOOL_COLOR_TEMPERATURE    "ammoos-tool-color-temperature"
#define GIMP_ICON_TOOL_CROP                 "ammoos-tool-crop"
#define GIMP_ICON_TOOL_CURVES               "ammoos-tool-curves"
#define GIMP_ICON_TOOL_DESATURATE           "ammoos-tool-desaturate"
#define GIMP_ICON_TOOL_DODGE                "ammoos-tool-dodge"
#define GIMP_ICON_TOOL_ELLIPSE_SELECT       "ammoos-tool-ellipse-select"
#define GIMP_ICON_TOOL_ERASER               "ammoos-tool-eraser"
#define GIMP_ICON_TOOL_EXPOSURE             "ammoos-tool-exposure"
#define GIMP_ICON_TOOL_FLIP                 "ammoos-tool-flip"
#define GIMP_ICON_TOOL_FOREGROUND_SELECT    "ammoos-tool-foreground-select"
#define GIMP_ICON_TOOL_FREE_SELECT          "ammoos-tool-free-select"
#define GIMP_ICON_TOOL_FUZZY_SELECT         "ammoos-tool-fuzzy-select"
#define GIMP_ICON_TOOL_GRADIENT             "ammoos-tool-gradient"
#define GIMP_ICON_TOOL_HANDLE_TRANSFORM     "ammoos-tool-handle-transform"
#define GIMP_ICON_TOOL_HEAL                 "ammoos-tool-heal"
#define GIMP_ICON_TOOL_HUE_SATURATION       "ammoos-tool-hue-saturation"
#define GIMP_ICON_TOOL_INK                  "ammoos-tool-ink"
#define GIMP_ICON_TOOL_ISCISSORS            "ammoos-tool-iscissors"
#define GIMP_ICON_TOOL_LEVELS               "ammoos-tool-levels"
#define GIMP_ICON_TOOL_MEASURE              "ammoos-tool-measure"
#define GIMP_ICON_TOOL_MOVE                 "ammoos-tool-move"
#define GIMP_ICON_TOOL_MYPAINT_BRUSH        "ammoos-tool-mypaint-brush"
#define GIMP_ICON_TOOL_N_POINT_DEFORMATION  "ammoos-tool-n-point-deformation"
#define GIMP_ICON_TOOL_OFFSET               "ammoos-tool-offset"
#define GIMP_ICON_TOOL_PAINTBRUSH           "ammoos-tool-paintbrush"
#define GIMP_ICON_TOOL_PAINT_SELECT         "ammoos-tool-paint-select"
#define GIMP_ICON_TOOL_PATH                 "ammoos-tool-path"
#define GIMP_ICON_TOOL_PENCIL               "ammoos-tool-pencil"
#define GIMP_ICON_TOOL_PERSPECTIVE          "ammoos-tool-perspective"
#define GIMP_ICON_TOOL_PERSPECTIVE_CLONE    "ammoos-tool-perspective-clone"
#define GIMP_ICON_TOOL_POSTERIZE            "ammoos-tool-posterize"
#define GIMP_ICON_TOOL_RECT_SELECT          "ammoos-tool-rect-select"
#define GIMP_ICON_TOOL_ROTATE               "ammoos-tool-rotate"
#define GIMP_ICON_TOOL_SCALE                "ammoos-tool-scale"
#define GIMP_ICON_TOOL_SEAMLESS_CLONE       "ammoos-tool-seamless-clone"
#define GIMP_ICON_TOOL_SHADOWS_HIGHLIGHTS   "ammoos-tool-shadows-highlights"
#define GIMP_ICON_TOOL_SHEAR                "ammoos-tool-shear"
#define GIMP_ICON_TOOL_SMUDGE               "ammoos-tool-smudge"
#define GIMP_ICON_TOOL_TEXT                 "ammoos-tool-text"
#define GIMP_ICON_TOOL_THRESHOLD            "ammoos-tool-threshold"
#define GIMP_ICON_TOOL_TRANSFORM_3D         "ammoos-tool-transform-3d"
#define GIMP_ICON_TOOL_UNIFIED_TRANSFORM    "ammoos-tool-unified-transform"
#define GIMP_ICON_TOOL_WARP                 "ammoos-tool-warp"
#define GIMP_ICON_TOOL_ZOOM                 "ammoos-tool-zoom"

#define GIMP_ICON_TRANSFORM_3D_CAMERA       "ammoos-transform-3d-camera"
#define GIMP_ICON_TRANSFORM_3D_MOVE         "ammoos-transform-3d-move"
#define GIMP_ICON_TRANSFORM_3D_ROTATE       "ammoos-transform-3d-rotate"

#define GIMP_ICON_VIEW_REFRESH              "view-refresh"
#define GIMP_ICON_VIEW_FULLSCREEN           "view-fullscreen"
#define GIMP_ICON_VIEW_SHRINK_WRAP          "view-shrink-wrap"
#define GIMP_ICON_VIEW_ZOOM_FILL            "view-zoom-fill"

#define GIMP_ICON_WILBER                    "ammoos-wilber"
#define GIMP_ICON_WILBER_EEK                "ammoos-wilber-eek"

#define GIMP_ICON_WINDOW_CLOSE              "window-close"
#define GIMP_ICON_WINDOW_MOVE_TO_SCREEN     "ammoos-move-to-screen"
#define GIMP_ICON_WINDOW_NEW                "window-new"

#define GIMP_ICON_ZOOM_IN                   "zoom-in"
#define GIMP_ICON_ZOOM_ORIGINAL             "zoom-original"
#define GIMP_ICON_ZOOM_OUT                  "zoom-out"
#define GIMP_ICON_ZOOM_FIT_BEST             "zoom-fit-best"
#define GIMP_ICON_ZOOM_FOLLOW_WINDOW        "ammoos-zoom-follow-window"


void     gimp_icons_init           (void);

gboolean gimp_icons_set_icon_theme (GFile *path);


G_END_DECLS

#endif /* __GIMP_ICONS_H__ */
