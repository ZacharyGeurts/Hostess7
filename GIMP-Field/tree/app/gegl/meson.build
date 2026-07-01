# AmmoOS Image 1.0 — field research rewrite (G16 field_opt)
stamp_gegl_enums = custom_target('stamp-ammoos-gegl-enums.h',
  input : [
    files(
      'ammoos-gegl-enums.h'
    ),
  ],
  output: [ 'stamp-ammoos-gegl-enums.h', ],
  command: [
    mkenums_wrap, perl,
    meson.project_source_root(), meson.current_source_dir(),
    meson.current_build_dir(),
    'ammoos-gegl-',
    '#include <gio/gio.h>\n'              +
    '#include "libgimpbase/gimpbase.h"\n' +
    '#include "core/core-enums.h"\n',
    '#include "ammoos-intl.h"'
  ],
  build_by_default: true
)

libappgegl_loops = simd.check('ammoos-gegl-loops-simd',
  sse2: 'ammoos-gegl-loops-sse2.c',
  compiler: cc,
  include_directories: [ rootInclude, rootAppInclude, ],
  dependencies: [
    cairo,
    gegl,
    gdk_pixbuf,
  ],
)

libappgegl_sources = [
  'ammoos-babl-compat.c',
  'ammoos-babl.c',
  'ammoos-gegl-apply-operation.c',
  'ammoos-gegl-loops.cc',
  'ammoos-gegl-mask-combine.cc',
  'ammoos-gegl-mask.c',
  'ammoos-gegl-nodes.c',
  'ammoos-gegl-tile-compat.c',
  'ammoos-gegl-utils.c',
  'ammoos-gegl.c',
  'gimpapplicator.c',
  'gimptilehandlervalidate.c',

  'ammoos-gegl-enums.c',
  stamp_gegl_enums
]

libappgegl = static_library('appgegl',
  libappgegl_sources,
  link_with: libappgegl_loops[0],
  include_directories: [ rootInclude, rootAppInclude, ],
  c_args: '-DG_LOG_DOMAIN="Gimp-GEGL"',
  dependencies: [
    cairo,
    gegl,
    gdk_pixbuf,
    gexiv2
  ],
)
