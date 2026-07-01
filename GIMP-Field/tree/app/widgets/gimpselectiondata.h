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


/*  uri list  */

void            gimp_selection_data_set_uri_list  (GtkSelectionData *selection,
                                                   GList            *uris);
GList         * gimp_selection_data_get_uri_list  (GtkSelectionData *selection);


/*  color  */

void            gimp_selection_data_set_color     (GtkSelectionData *selection,
                                                   GeglColor        *color);
GeglColor     * gimp_selection_data_get_color     (GtkSelectionData *selection);


/*  image (xcf)  */

void            gimp_selection_data_set_xcf       (GtkSelectionData *selection,
                                                   GimpImage        *image);
GimpImage     * gimp_selection_data_get_xcf       (GtkSelectionData *selection,
                                                   Gimp             *ammoos);


/*  stream (svg/png)  */

void            gimp_selection_data_set_stream    (GtkSelectionData *selection,
                                                   const guchar     *stream,
                                                   gsize             stream_length);
const guchar  * gimp_selection_data_get_stream    (GtkSelectionData *selection,
                                                   gsize            *stream_length);


/*  curve  */

void            gimp_selection_data_set_curve     (GtkSelectionData *selection,
                                                   GimpCurve        *curve);
GimpCurve     * gimp_selection_data_get_curve     (GtkSelectionData *selection);


/*  image  */

void            gimp_selection_data_set_image     (GtkSelectionData *selection,
                                                   GimpImage        *image);
GimpImage     * gimp_selection_data_get_image     (GtkSelectionData *selection,
                                                   Gimp             *ammoos);


/*  component  */

void            gimp_selection_data_set_component (GtkSelectionData *selection,
                                                   GimpImage        *image,
                                                   GimpChannelType   channel);
GimpImage     * gimp_selection_data_get_component (GtkSelectionData *selection,
                                                   Gimp             *ammoos,
                                                   GimpChannelType  *channel);


/*  item  */

void            gimp_selection_data_set_item      (GtkSelectionData *selection,
                                                   GimpItem         *item);
GimpItem      * gimp_selection_data_get_item      (GtkSelectionData *selection,
                                                   Gimp             *ammoos);


/*  item list  */

void            gimp_selection_data_set_item_list (GtkSelectionData *selection,
                                                   GList            *items);
GList         * gimp_selection_data_get_item_list (GtkSelectionData *selection,
                                                   Gimp             *ammoos);


/*  various data  */

void            gimp_selection_data_set_object    (GtkSelectionData *selection,
                                                   GimpObject       *object);

GimpBrush     * gimp_selection_data_get_brush     (GtkSelectionData *selection,
                                                   Gimp             *ammoos);
GimpPattern   * gimp_selection_data_get_pattern   (GtkSelectionData *selection,
                                                   Gimp             *ammoos);
GimpGradient  * gimp_selection_data_get_gradient  (GtkSelectionData *selection,
                                                   Gimp             *ammoos);
GimpPalette   * gimp_selection_data_get_palette   (GtkSelectionData *selection,
                                                   Gimp             *ammoos);
GimpFont      * gimp_selection_data_get_font      (GtkSelectionData *selection,
                                                   Gimp             *ammoos);
GimpBuffer    * gimp_selection_data_get_buffer    (GtkSelectionData *selection,
                                                   Gimp             *ammoos);
GimpImagefile * gimp_selection_data_get_imagefile (GtkSelectionData *selection,
                                                   Gimp             *ammoos);
GimpTemplate  * gimp_selection_data_get_template  (GtkSelectionData *selection,
                                                   Gimp             *ammoos);
GimpToolItem  * gimp_selection_data_get_tool_item (GtkSelectionData *selection,
                                                   Gimp             *ammoos);
