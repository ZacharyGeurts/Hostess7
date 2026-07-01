#!/usr/bin/env python3
# AmmoOS Image — field formats (WRDT/WRZC/ZAC7/FLD/plate) · CPU field_opt + RTX paths

import gi
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

gi.require_version('Gimp', '3.0')
gi.require_version('Gegl', '0.4')
from gi.repository import Gimp, Gegl, GObject, GLib, Gio

SG_ROOT = os.environ.get('SG_ROOT', str(Path(__file__).resolve().parents[4]))
IO_SCRIPT = os.path.join(SG_ROOT, 'GIMP-Field', 'lib', 'field-image-io.py')

PROC_WRDT = 'file-field-wrdt-python'
PROC_WRZC = 'file-field-wrzc-python'
PROC_ZAC7 = 'file-field-zac7-python'
PROC_FLD  = 'file-field-fld-python'
PROC_PLATE = 'file-field-plate-python'
PROC_EXPORT = 'file-field-wrdt-export-python'


def _dispatch(path: str) -> dict:
    env = {**os.environ, 'SG_ROOT': SG_ROOT, 'PYTHONPATH': SG_ROOT}
    proc = subprocess.run(
        [sys.executable, IO_SCRIPT, 'dispatch', path],
        capture_output=True, text=True, timeout=120, env=env,
    )
    if proc.returncode != 0:
        return {'ok': False, 'error': proc.stderr or proc.stdout}
    return json.loads(proc.stdout)


def _export_wrdt(inner_path: str, out_path: str) -> dict:
    env = {**os.environ, 'SG_ROOT': SG_ROOT, 'PYTHONPATH': SG_ROOT}
    proc = subprocess.run(
        [sys.executable, IO_SCRIPT, 'export', inner_path, out_path],
        capture_output=True, text=True, timeout=120, env=env,
    )
    if proc.returncode != 0:
        return {'ok': False, 'error': proc.stderr or proc.stdout}
    return json.loads(proc.stdout)


def _load_inner(path: str) -> Gimp.Image:
    result = Gimp.get_pdb().run_procedure('gimp-file-load', [Gimp.RunMode.NONINTERACTIVE, Gio.File.new_for_path(path)])
    return result.index(1)


def _field_load(procedure, run_mode, file, **_kwargs):
    path = file.get_path()
    doc = _dispatch(path)
    if not doc.get('ok'):
        return procedure.new_return_values(Gimp.PDBStatusType.EXECUTION_ERROR, GLib.Error(message=doc.get('error', 'field_io_fail')))

    profile = doc.get('profile', 'field_opt')
    Gimp.message(f'AmmoOS field load · {doc.get("kind")} · {profile}')

    if doc.get('temp_image'):
        img = _load_inner(doc['temp_image'])
        try:
            os.unlink(doc['temp_image'])
        except OSError:
            pass
        return procedure.new_return_values(Gimp.PDBStatusType.SUCCESS, args=[img])

    if doc.get('kind') == 'fld':
        text = (doc.get('text') or '')[:8000]
        img = Gimp.Image.new(640, 480, Gimp.ImageBaseType.RGB)
        layer = Gimp.Layer.new(img, 'FLD Source', 640, 480, Gimp.ImageType.RGB, 100, Gimp.LayerMode.NORMAL)
        img.insert_layer(layer, None, 0)
        Gimp.message(text[:500])
        return procedure.new_return_values(Gimp.PDBStatusType.SUCCESS, args=[img])

    if doc.get('kind') == 'plate':
        plate = doc.get('plate') or {}
        title = str(plate.get('title') or plate.get('schema') or 'Field Plate')
        img = Gimp.Image.new(512, 256, Gimp.ImageBaseType.RGB)
        layer = Gimp.Layer.new(img, title[:64], 512, 256, Gimp.ImageType.RGB, 100, Gimp.LayerMode.NORMAL)
        img.insert_layer(layer, None, 0)
        Gimp.message(json.dumps(plate, indent=2)[:1200])
        return procedure.new_return_values(Gimp.PDBStatusType.SUCCESS, args=[img])

    return procedure.new_return_values(Gimp.PDBStatusType.EXECUTION_ERROR, GLib.Error(message='no_preview'))


def _field_export(procedure, run_mode, image, file, options, **_kwargs):
    del run_mode, options
    merged = image.merge_visible_layers(Gimp.MergeType.CLIP_TO_IMAGE)
    tmp = tempfile.NamedTemporaryFile(suffix='.png', prefix='ammoos-export-', delete=False)
    tmp.close()
    try:
        Gimp.file_save(Gimp.RunMode.NONINTERACTIVE, image, Gio.File.new_for_path(tmp.name), merged)
        doc = _export_wrdt(tmp.name, file.get_path())
        if not doc.get('ok'):
            return procedure.new_return_values(
                Gimp.PDBStatusType.EXECUTION_ERROR, GLib.Error(message=doc.get('error', 'export_fail')))
        Gimp.message(f'AmmoOS WRDT export · {doc.get("bytes", 0)} bytes · {doc.get("profile", "field_opt")}')
        return procedure.new_return_values(Gimp.PDBStatusType.SUCCESS)
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass


class FieldFormats(Gimp.PlugIn):
    def do_query_procedures(self):
        return [PROC_WRDT, PROC_WRZC, PROC_ZAC7, PROC_FLD, PROC_PLATE, PROC_EXPORT]

    def do_create_procedure(self, name):
        if name == PROC_WRDT:
            p = Gimp.LoadProcedure.new(self, name, Gimp.PDBProcType.PLUGIN, _field_load, None)
            p.set_extensions('wrdt')
            p.set_mime_types('application/x-wrdt')
            p.set_magics('0,string,WRDT')
            p.set_menu_label('WRDT1 Field Image')
        elif name == PROC_WRZC:
            p = Gimp.LoadProcedure.new(self, name, Gimp.PDBProcType.PLUGIN, _field_load, None)
            p.set_extensions('wrzc')
            p.set_mime_types('application/x-wrzc')
            p.set_magics('0,string,WRZC')
            p.set_menu_label('WRZC1 Field Disguise')
        elif name == PROC_ZAC7:
            p = Gimp.LoadProcedure.new(self, name, Gimp.PDBProcType.PLUGIN, _field_load, None)
            p.set_extensions('zac7,zac')
            p.set_mime_types('application/x-zac7')
            p.set_magics('0,string,ZAC7')
            p.set_menu_label('ZAC7 Field Shard')
        elif name == PROC_FLD:
            p = Gimp.LoadProcedure.new(self, name, Gimp.PDBProcType.PLUGIN, _field_load, None)
            p.set_extensions('fld')
            p.set_mime_types('text/x-field-fld')
            p.set_menu_label('Field Source (.fld)')
        elif name == PROC_PLATE:
            p = Gimp.LoadProcedure.new(self, name, Gimp.PDBProcType.PLUGIN, _field_load, None)
            p.set_extensions('plate.json')
            p.set_mime_types('application/x-field-plate')
            p.set_menu_label('Field Plate JSON')
        elif name == PROC_EXPORT:
            p = Gimp.ExportProcedure.new(self, name, Gimp.PDBProcType.PLUGIN, False, _field_export, None)
            p.set_image_types('RGB*, GRAY, INDEXED')
            p.set_extensions('wrdt')
            p.set_mime_types('application/x-wrdt')
            p.set_format_name('WRDT')
            p.set_menu_label('WRDT1 Field Image')
        else:
            return None
        p.set_documentation(
            'AmmoOS field technology loader — CPU field_opt flies; RTX batch when gate permits',
            'AmmoOS field technology loader',
            name,
        )
        p.set_attribution('AmmoOS', 'Field Technology', '2026')
        return p


Gimp.main(FieldFormats.__gtype__, sys.argv)