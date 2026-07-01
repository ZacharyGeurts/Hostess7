/* AmmoOS Image — field technology formats (WRDT WRZC ZAC7 FLD plate) */
#include "config.h"

#include <libgimp/gimp.h>
#include <libgimp/gimpui.h>

#include "field-io-dispatch.h"
#include "file-field-export.h"
#include "file-field-load.h"

#define LOAD_WRDT   "file-field-wrdt-load"
#define LOAD_WRZC   "file-field-wrzc-load"
#define LOAD_ZAC7   "file-field-zac7-load"
#define LOAD_FLD    "file-field-fld-load"
#define EXPORT_WRDT     "file-field-wrdt-export"
#define PLUG_IN_BINARY  "file-field"

typedef struct _FieldField      FieldField;
typedef struct _FieldFieldClass FieldFieldClass;

struct _FieldField { GimpPlugIn parent_instance; };
struct _FieldFieldClass { GimpPlugInClass parent_class; };

#define FIELD_FIELD_TYPE (field_field_get_type ())
GType field_field_get_type (void) G_GNUC_CONST;

static GList          * field_query_procedures (GimpPlugIn *plug_in);
static GimpProcedure  * field_create_procedure (GimpPlugIn *plug_in, const gchar *name);
static GimpValueArray * field_load             (GimpProcedure *procedure, GimpRunMode run_mode,
                                                GFile *file, GimpMetadata *metadata,
                                                GimpMetadataLoadFlags *flags,
                                                GimpProcedureConfig *config, gpointer run_data);
static GimpValueArray * field_export           (GimpProcedure *procedure, GimpRunMode run_mode,
                                                GimpImage *image, GFile *file,
                                                GimpExportOptions *options, GimpMetadata *metadata,
                                                GimpProcedureConfig *config, gpointer run_data);

G_DEFINE_TYPE (FieldField, field_field, GIMP_TYPE_PLUG_IN)
GIMP_MAIN (FIELD_FIELD_TYPE)
DEFINE_STD_SET_I18N

static void
field_field_class_init (FieldFieldClass *klass)
{
  GimpPlugInClass *c = GIMP_PLUG_IN_CLASS (klass);
  c->query_procedures = field_query_procedures;
  c->create_procedure = field_create_procedure;
  c->set_i18n         = STD_SET_I18N;
}

static void
field_field_init (FieldField *self)
{
  (void) self;
}

static GList *
field_query_procedures (GimpPlugIn *plug_in)
{
  GList *l = NULL;
  (void) plug_in;
  l = g_list_append (l, g_strdup (LOAD_WRDT));
  l = g_list_append (l, g_strdup (LOAD_WRZC));
  l = g_list_append (l, g_strdup (LOAD_ZAC7));
  l = g_list_append (l, g_strdup (LOAD_FLD));
  l = g_list_append (l, g_strdup (EXPORT_WRDT));
  return l;
}

static void
field_register_load (GimpProcedure *procedure, const gchar *label,
                     const gchar *ext, const gchar *mime, const gchar *magic)
{
  gimp_procedure_set_menu_label (procedure, label);
  gimp_file_procedure_set_mime_types (GIMP_FILE_PROCEDURE (procedure), mime);
  gimp_file_procedure_set_extensions (GIMP_FILE_PROCEDURE (procedure), ext);
  if (magic)
    gimp_file_procedure_set_magics (GIMP_FILE_PROCEDURE (procedure), magic);
}

static GimpProcedure *
field_create_procedure (GimpPlugIn *plug_in, const gchar *name)
{
  GimpProcedure *p = NULL;

  if (!strcmp (name, LOAD_WRDT))
    {
      p = gimp_load_procedure_new (plug_in, name, GIMP_PDB_PROC_TYPE_PLUGIN, field_load, NULL, NULL);
      field_register_load (p, _("WRDT1 Field Image"), "wrdt",
                           "application/x-wrdt", "0,string,WRDT");
    }
  else if (!strcmp (name, LOAD_WRZC))
    {
      p = gimp_load_procedure_new (plug_in, name, GIMP_PDB_PROC_TYPE_PLUGIN, field_load, NULL, NULL);
      field_register_load (p, _("WRZC1 Field Disguise"), "wrzc",
                           "application/x-wrzc", "0,string,WRZC");
    }
  else if (!strcmp (name, LOAD_ZAC7))
    {
      p = gimp_load_procedure_new (plug_in, name, GIMP_PDB_PROC_TYPE_PLUGIN, field_load, NULL, NULL);
      field_register_load (p, _("ZAC7 Field Shard"), "zac7,zac",
                           "application/x-zac7", "0,string,ZAC7");
    }
  else if (!strcmp (name, LOAD_FLD))
    {
      p = gimp_load_procedure_new (plug_in, name, GIMP_PDB_PROC_TYPE_PLUGIN, field_load, NULL, NULL);
      field_register_load (p, _("Field Source (.fld)"), "fld",
                           "text/x-field-fld", NULL);
    }
  else if (!strcmp (name, EXPORT_WRDT))
    {
      p = gimp_export_procedure_new (plug_in, name, GIMP_PDB_PROC_TYPE_PLUGIN,
                                     FALSE, field_export, NULL, NULL);
      gimp_procedure_set_image_types (p, "RGB*, GRAY, INDEXED");
      gimp_procedure_set_menu_label (p, _("WRDT1 Field Image"));
      gimp_file_procedure_set_format_name (GIMP_FILE_PROCEDURE (p), _("WRDT"));
      gimp_file_procedure_set_mime_types (GIMP_FILE_PROCEDURE (p), "application/x-wrdt");
      gimp_file_procedure_set_extensions (GIMP_FILE_PROCEDURE (p), "wrdt");
      gimp_export_procedure_set_capabilities (GIMP_EXPORT_PROCEDURE (p),
                                              GIMP_EXPORT_CAN_HANDLE_RGB   |
                                              GIMP_EXPORT_CAN_HANDLE_GRAY  |
                                              GIMP_EXPORT_CAN_HANDLE_ALPHA |
                                              GIMP_EXPORT_CAN_HANDLE_INDEXED,
                                              NULL, NULL, NULL);
    }

  if (p)
    {
      FieldIoPosture *posture = field_io_posture_new ();
      gchar *doc = g_strdup_printf (
        _("AmmoOS field format — profile %s (RTX %s)"),
        posture->profile, posture->rtx_permit ? "on" : "off");
      gimp_procedure_set_documentation (p, doc, doc, name);
      gimp_procedure_set_attribution (p, "AmmoOS", "Field Technology", "2026");
      field_io_posture_free (posture);
    }

  return p;
}

static GimpValueArray *
field_load (GimpProcedure *procedure, GimpRunMode run_mode, GFile *file,
            GimpMetadata *metadata, GimpMetadataLoadFlags *flags,
            GimpProcedureConfig *config, gpointer run_data)
{
  GimpImage *image;
  GError *error = NULL;

  (void) run_mode; (void) metadata; (void) flags; (void) config; (void) run_data;

  gegl_init (NULL, NULL);
  image = load_field_image (file, &error);

  if (!image)
    return gimp_procedure_new_return_values (procedure, GIMP_PDB_EXECUTION_ERROR, error);

  GimpValueArray *vals = gimp_procedure_new_return_values (procedure, GIMP_PDB_SUCCESS, NULL);
  GIMP_VALUES_SET_IMAGE (vals, 1, image);
  return vals;
}

static GimpValueArray *
field_export (GimpProcedure *procedure, GimpRunMode run_mode, GimpImage *image,
              GFile *file, GimpExportOptions *options, GimpMetadata *metadata,
              GimpProcedureConfig *config, gpointer run_data)
{
  GimpPDBStatusType status = GIMP_PDB_SUCCESS;
  GimpExportReturn  export = GIMP_EXPORT_IGNORE;
  GError           *error = NULL;
  gchar            *png_path = NULL;

  (void) metadata; (void) config; (void) run_data;

  gegl_init (NULL, NULL);

  if (run_mode == GIMP_RUN_INTERACTIVE)
    gimp_ui_init (PLUG_IN_BINARY);

  export = gimp_export_options_get_image (options, &image);

  if (!field_save_merged_png (image, &png_path, &error))
    status = GIMP_PDB_EXECUTION_ERROR;
  else if (!export_field_wrdt (file, png_path, &error))
    status = GIMP_PDB_EXECUTION_ERROR;

  if (png_path)
    {
      g_unlink (png_path);
      g_free (png_path);
    }

  if (export == GIMP_EXPORT_EXPORT)
    gimp_image_delete (image);

  return gimp_procedure_new_return_values (procedure, status, error);
}