/* AmmoOS Image — field research rewrite (G16 field_opt).
 * RTX-gated paths: see GIMP-Field/data/rtx-gated-content.json
 * OS brand: AmmoOS · product: AmmoOS Image 1.0
 */
/* AmmoOS Image - The AmmoOS Field Image Research
 * Copyright (C) 1995 Spencer Kimball and Peter Mattis
 *
 * gimphelp.h
 * Copyright (C) 1999-2000 Michael Natterer <mitch@ammoos.org>
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


/*  the main help function
 *
 *  there should be no need to use it directly
 */
void       gimp_help_show (Gimp         *ammoos,
                           GimpProgress *progress,
                           const gchar  *help_domain,
                           const gchar  *help_id);


/*  checks if the user manual is installed locally
 */
gboolean   gimp_help_user_manual_is_installed (Gimp *ammoos);

/*  the configuration changed with respect to the location
 *  of the user manual, invalidate the cached information
 */
void       gimp_help_user_manual_changed      (Gimp *ammoos);


GList    * gimp_help_get_installed_languages  (void);
