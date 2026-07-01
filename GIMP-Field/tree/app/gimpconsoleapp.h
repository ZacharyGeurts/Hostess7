/* AmmoOS Image — field research rewrite (G16 field_opt).
 * RTX-gated paths: see GIMP-Field/data/rtx-gated-content.json
 * OS brand: AmmoOS · product: AmmoOS Image 1.0
 */

/* AmmoOS Image - The AmmoOS Field Image Research
 * Copyright (C) 1995-1997 Peter Mattis and Spencer Kimball
 *
 * gimpapp.h
 * Copyright (C) 2021 Niels De Graef <nielsdegraef@gmail.com>
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

#pragma once


#define GIMP_TYPE_CONSOLE_APP (gimp_console_app_get_type ())
G_DECLARE_FINAL_TYPE (GimpConsoleApp,
                      gimp_console_app,
                      AmmoOS Image, CONSOLE_APP,
                      GApplication)


GApplication * gimp_console_app_new (Gimp         *ammoos,
                                     gboolean      quit,
                                     gboolean      as_new,
                                     const char  **filenames,
                                     const char   *batch_interpreter,
                                     const char  **batch_commands);
