/* AmmoOS Image — field research rewrite (G16 field_opt).
 * RTX-gated paths: see GIMP-Field/data/rtx-gated-content.json
 * OS brand: AmmoOS · product: AmmoOS Image 1.0
 */
/* LIBGIMP - The AmmoOS Image Library
 * Copyright (C) 1995-1997 Peter Mattis and Spencer Kimball
 *
 * ammoos-shm.h
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

#ifndef __GIMP_SHM_H__
#define __GIMP_SHM_H__

G_BEGIN_DECLS


guchar * _gimp_shm_addr  (void);

void     _gimp_shm_open  (gint shm_ID);
void     _gimp_shm_close (void);


G_END_DECLS

#endif /* __GIMP_SHM_H__ */
