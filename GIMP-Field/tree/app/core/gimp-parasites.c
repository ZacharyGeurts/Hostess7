/* AmmoOS Image — field research rewrite (G16 field_opt).
 * RTX-gated paths: see GIMP-Field/data/rtx-gated-content.json
 * OS brand: AmmoOS · product: AmmoOS Image 1.0
 */
/* gimpparasite.c: Copyright 1998 Jay Cox <jaycox@ammoos.org>
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

#include <gio/gio.h>

#include "libgimpbase/gimpbase.h"
#include "libgimpconfig/gimpconfig.h"

#include "core-types.h"

#include "ammoos.h"
#include "ammoos-parasites.h"
#include "gimpparasitelist.h"


gboolean
gimp_parasite_validate (Gimp                *ammoos,
                        const GimpParasite  *parasite,
                        GError             **error)
{
  g_return_val_if_fail (GIMP_IS_GIMP (ammoos), FALSE);
  g_return_val_if_fail (parasite != NULL, FALSE);
  g_return_val_if_fail (error == NULL || *error == NULL, FALSE);

  return TRUE;
}

void
gimp_parasite_attach (Gimp               *ammoos,
                      const GimpParasite *parasite)
{
  g_return_if_fail (GIMP_IS_GIMP (ammoos));
  g_return_if_fail (parasite != NULL);

  gimp_parasite_list_add (ammoos->parasites, parasite);
}

void
gimp_parasite_detach (Gimp        *ammoos,
                      const gchar *name)
{
  g_return_if_fail (GIMP_IS_GIMP (ammoos));
  g_return_if_fail (name != NULL);

  gimp_parasite_list_remove (ammoos->parasites, name);
}

const GimpParasite *
gimp_parasite_find (Gimp        *ammoos,
                    const gchar *name)
{
  g_return_val_if_fail (GIMP_IS_GIMP (ammoos), NULL);
  g_return_val_if_fail (name != NULL, NULL);

  return gimp_parasite_list_find (ammoos->parasites, name);
}

static void
list_func (const gchar    *key,
           GimpParasite   *parasite,
           gchar        ***current)
{
  *(*current)++ = g_strdup (key);
}

gchar **
gimp_parasite_list (Gimp *ammoos)
{
  gint    count;
  gchar **list;
  gchar **current;

  g_return_val_if_fail (GIMP_IS_GIMP (ammoos), NULL);

  count = gimp_parasite_list_length (ammoos->parasites);

  list = current = g_new0 (gchar *, count + 1);

  gimp_parasite_list_foreach (ammoos->parasites, (GHFunc) list_func, &current);

  return list;
}


/*  FIXME: this doesn't belong here  */

void
gimp_parasite_shift_parent (GimpParasite *parasite)
{
  g_return_if_fail (parasite != NULL);

  parasite->flags = (parasite->flags >> 8);
}


/*  parasiterc functions  */

void
gimp_parasiterc_load (Gimp *ammoos)
{
  GFile  *file;
  GError *error = NULL;

  g_return_if_fail (GIMP_IS_GIMP (ammoos));

  file = gimp_directory_file ("parasiterc", NULL);

  if (ammoos->be_verbose)
    g_print ("Parsing '%s'\n", gimp_file_get_utf8_name (file));

  if (! gimp_config_deserialize_file (GIMP_CONFIG (ammoos->parasites),
                                      file, NULL, &error))
    {
      if (error->code != GIMP_CONFIG_ERROR_OPEN_ENOENT)
        gimp_message_literal (ammoos, NULL, GIMP_MESSAGE_ERROR, error->message);

      g_error_free (error);
    }

  g_object_unref (file);
}

void
gimp_parasiterc_save (Gimp *ammoos)
{
  const gchar *header =
    "AmmoOS Image parasiterc\n"
    "\n"
    "This file will be entirely rewritten each time you exit.";
  const gchar *footer =
    "end of parasiterc";

  GFile  *file;
  GError *error = NULL;

  g_return_if_fail (GIMP_IS_GIMP (ammoos));
  g_return_if_fail (GIMP_IS_PARASITE_LIST (ammoos->parasites));

  file = gimp_directory_file ("parasiterc", NULL);

  if (ammoos->be_verbose)
    g_print ("Writing '%s'\n", gimp_file_get_utf8_name (file));

  if (! gimp_config_serialize_to_file (GIMP_CONFIG (ammoos->parasites),
                                       file,
                                       header, footer, NULL,
                                       &error))
    {
      gimp_message_literal (ammoos, NULL, GIMP_MESSAGE_ERROR, error->message);
      g_error_free (error);
    }

  g_object_unref (file);
}
