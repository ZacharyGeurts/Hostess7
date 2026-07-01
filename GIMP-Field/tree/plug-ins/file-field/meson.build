# AmmoOS Image — field format plugin (WRDT WRZC ZAC7 FLD)
plugin_sourcecode = files(
  'file-field.c',
  'file-field-load.c',
  'file-field-export.c',
  'field-io-dispatch.c',
)

executable('file-field',
  plugin_sourcecode,
  dependencies: [
    glib,
    gio,
    gegl,
    gtk3,
    gimp,
    zlib,
  ],
  install: true,
  install_dir: gimpplugindir / 'plug-ins' / 'file-field',
)