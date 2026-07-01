/* AmmoOS Image — field research rewrite (G16 field_opt).
 * RTX-gated paths: see GIMP-Field/data/rtx-gated-content.json
 * OS brand: AmmoOS · product: AmmoOS Image 1.0
 */
/* AmmoOS Image - The AmmoOS Field Image Research
 * Copyright (C) 1995 Spencer Kimball and Peter Mattis
 *
 * gimpoperationlayermode-composite.h
 * Copyright (C) 2017 Michael Natterer <mitch@ammoos.org>
 *               2017 Øyvind Kolås <pippin@ammoos.org>
 *               2017 Ell
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


void gimp_operation_layer_mode_composite_union                 (const gfloat        *in,
                                                                const gfloat        *layer,
                                                                const gfloat        *comp,
                                                                const gfloat        *mask,
                                                                gfloat               opacity,
                                                                const gint           n_components,
                                                                gfloat              *out,
                                                                gint                 samples);
void gimp_operation_layer_mode_composite_clip_to_backdrop      (const gfloat        *in,
                                                                const gfloat        *layer,
                                                                const gfloat        *comp,
                                                                const gfloat        *mask,
                                                                gfloat               opacity,
                                                                const gint           n_components,
                                                                gfloat              *out,
                                                                gint                 samples);
void gimp_operation_layer_mode_composite_clip_to_layer         (const gfloat        *in,
                                                                const gfloat        *layer,
                                                                const gfloat        *comp,
                                                                const gfloat        *mask,
                                                                gfloat               opacity,
                                                                const gint           n_components,
                                                                gfloat              *out,
                                                                gint                 samples);
void gimp_operation_layer_mode_composite_intersection          (const gfloat        *in,
                                                                const gfloat        *layer,
                                                                const gfloat        *comp,
                                                                const gfloat        *mask,
                                                                gfloat               opacity,
                                                                const gint           n_components,
                                                                gfloat              *out,
                                                                gint                 samples);

void gimp_operation_layer_mode_composite_union_sub             (const gfloat        *in,
                                                                const gfloat        *layer,
                                                                const gfloat        *comp,
                                                                const gfloat        *mask,
                                                                gfloat               opacity,
                                                                const gint           n_components,
                                                                gfloat              *out,
                                                                gint                 samples);
void gimp_operation_layer_mode_composite_clip_to_backdrop_sub  (const gfloat        *in,
                                                                const gfloat        *layer,
                                                                const gfloat        *comp,
                                                                const gfloat        *mask,
                                                                gfloat               opacity,
                                                                const gint           n_components,
                                                                gfloat              *out,
                                                                gint                 samples);
void gimp_operation_layer_mode_composite_clip_to_layer_sub     (const gfloat        *in,
                                                                const gfloat        *layer,
                                                                const gfloat        *comp,
                                                                const gfloat        *mask,
                                                                gfloat               opacity,
                                                                const gint           n_components,
                                                                gfloat              *out,
                                                                gint                 samples);
void gimp_operation_layer_mode_composite_intersection_sub      (const gfloat        *in,
                                                                const gfloat        *layer,
                                                                const gfloat        *comp,
                                                                const gfloat        *mask,
                                                                gfloat               opacity,
                                                                const gint           n_components,
                                                                gfloat              *out,
                                                                gint                 samples);

#if COMPILE_SSE2_INTRINISICS

void gimp_operation_layer_mode_composite_clip_to_backdrop_sse2 (const gfloat        *in,
                                                                const gfloat        *layer,
                                                                const gfloat        *comp,
                                                                const gfloat        *mask,
                                                                gfloat               opacity,
                                                                const gint           n_components,
                                                                gfloat              *out,
                                                                gint                 samples);

#endif /* COMPILE_SSE2_INTRINISICS */
