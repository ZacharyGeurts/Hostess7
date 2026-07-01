# AmmoOS Image — consolidated libammoos (g16 field_opt)
libammoos_sources = files(

)

libammoos_lib = static_library('ammoos-field',
  libammoos_sources,
  include_directories: include_directories('.'),
  c_args: ['-DFIELD_AMMOOS_G16_OPT=1', '-DFIELD_AMMOOS_OS=1'],
  install: false,
)
