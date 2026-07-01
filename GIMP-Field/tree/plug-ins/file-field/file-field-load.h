#pragma once

#include <gio/gio.h>
#include <libgimp/gimp.h>

GimpImage *load_field_image (GFile *file, GError **error);