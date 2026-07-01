#pragma once

#include <gio/gio.h>
#include <libgimp/gimp.h>

gboolean export_field_wrdt (GFile *file, const gchar *inner_path, GError **error);
gboolean field_save_merged_png (GimpImage *image, gchar **out_path, GError **error);