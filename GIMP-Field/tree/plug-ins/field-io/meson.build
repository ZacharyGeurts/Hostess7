# AmmoOS Image — consolidated field I/O lane (CIN DDS EXR FITS FLI ICNS SGI …)
io_plugins = [
  'file-cin',
  'file-dds',
  'file-faxg3',
  'file-fli',
  'file-icns',
  'file-sgi',
]

if openexr.found()
  io_plugins += 'file-exr'
endif

if cfitsio_dep.found()
  io_plugins += 'file-fits'
endif

plugin_sourcecode = files(
  'file-cin/file-cin.c',
  'file-dds/dds.c',
  'file-faxg3/faxg3.c',
  'file-fli/fli-gimp.c',
  'file-icns/file-icns.c',
  'file-sgi/sgi.c',
)

foreach p : io_plugins
  subdir(p)
endforeach