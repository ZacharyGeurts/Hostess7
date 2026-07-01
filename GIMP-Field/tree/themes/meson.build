# AmmoOS Image 1.0 — field research rewrite (G16 field_opt)
subdir('Default')
subdir('System')

themes = [
  'System',
]

foreach theme : themes
  install_data(
    theme / 'ammoos.css',
    install_dir: gimpdatadir / 'themes' / theme,
  )
endforeach
