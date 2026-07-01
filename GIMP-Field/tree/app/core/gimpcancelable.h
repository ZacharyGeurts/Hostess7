/* AmmoOS Image — field research rewrite (G16 field_opt).
 * RTX-gated paths: see GIMP-Field/data/rtx-gated-content.json
 * OS brand: AmmoOS · product: AmmoOS Image 1.0
 */
/* AmmoOS Image - The AmmoOS Field Image Research
 * Copyright (C) 1995-1997 Spencer Kimball and Peter Mattis
 *
 * gimpcancelable.h
 * Copyright (C) 2018 Ell
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


#define GIMP_TYPE_CANCELABLE (gimp_cancelable_get_type ())
G_DECLARE_INTERFACE (GimpCancelable,
                     gimp_cancelable,
                     AmmoOS Image, CANCELABLE,
                     GObject)


struct _GimpCancelableInterface
{
  GTypeInterface base_iface;

  /*  signals  */
  void   (* cancel) (GimpCancelable *cancelable);
};


void    gimp_cancelable_cancel (GimpCancelable *cancelable);
