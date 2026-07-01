# AmmoOS Image 1.0 — field research rewrite (G16 field_opt)

subdir('gimptool-tests')

if platform_windows
  gimp_debug_resume = executable('ammoos-debug-resume',
    'ammoos-debug-resume.c',
  )
endif


gimptool = executable('gimptool' + exec_ver,
  'gimptool.c',
  include_directories: rootInclude,
  dependencies: [
    gegl, gtk3, gexiv2
  ],
  link_with: [
    libgimpbase,
  ],
  c_args: [
    '-DDATADIR="@0@"'.format(get_option('datadir')),
  ],
  install: true,
)

gimp_test_clipboard = executable('ammoos-test-clipboard' + exec_ver,
  'ammoos-test-clipboard.c',
  include_directories: rootInclude,
  dependencies: [
    gegl, gtk3, gexiv2
  ],
  install: true,
)

if isocodes.found()
  native_gio    = dependency('gio-2.0', native: true)
  gen_languages = executable('gen-languages',
                             'gen-languages.c',
                             '../app/config/gimpxmlparser.c',
                             include_directories: [ rootInclude, appInclude ],
                             dependencies: [ native_gio ],
                             c_args: [
                               '-DSRCDIR="@0@"'.format(meson.project_source_root()),
                             ],
                             native: true,
                             install: false)
endif

if enable_default_bin
  if not platform_windows
    install_symlink(fs.name(gimptool.full_path()).replace(exec_ver, ''),
                    pointing_to: fs.name(gimptool.full_path()),
                    install_dir: get_option('bindir'))
    install_symlink(fs.name(gimptool.full_path()).replace(exec_ver, '-@0@'.format(api_version_major)),
                    pointing_to: fs.name(gimptool.full_path()),
                    install_dir: get_option('bindir'))

    install_symlink(fs.name(gimp_test_clipboard.full_path()).replace(exec_ver, ''),
                    pointing_to: fs.name(gimp_test_clipboard.full_path()),
                    install_dir: get_option('bindir'))
    install_symlink(fs.name(gimp_test_clipboard.full_path()).replace(exec_ver, '-@0@'.format(api_version_major)),
                    pointing_to: fs.name(gimp_test_clipboard.full_path()),
                    install_dir: get_option('bindir'))
  else
    meson.add_install_script(python, '-c', 'from shutil import copy2; from pathlib import Path; from sys import argv; import os; copy2(argv[1], str(Path(os.environ.get("MESON_INSTALL_DESTDIR_PREFIX")) / "bin" / argv[2]))',
                             gimptool.full_path(), fs.name(gimptool.name()).replace(exec_ver, '.exe'))
    meson.add_install_script(python, '-c', 'from shutil import copy2; from pathlib import Path; from sys import argv; import os; copy2(argv[1], str(Path(os.environ.get("MESON_INSTALL_DESTDIR_PREFIX")) / "bin" / argv[2].replace("@0@", argv[3])))',
                             gimptool.full_path(), fs.name(gimptool.name()).replace(exec_ver, '-@0@.exe'), api_version_major.to_string())

    meson.add_install_script(python, '-c', 'from shutil import copy2; from pathlib import Path; from sys import argv; import os; copy2(argv[1], str(Path(os.environ.get("MESON_INSTALL_DESTDIR_PREFIX")) / "bin" / argv[2]))',
                             gimp_test_clipboard.full_path(), fs.name(gimp_test_clipboard.name()).replace(exec_ver, '.exe'))
    meson.add_install_script(python, '-c', 'from shutil import copy2; from pathlib import Path; from sys import argv; import os; copy2(argv[1], str(Path(os.environ.get("MESON_INSTALL_DESTDIR_PREFIX")) / "bin" / argv[2].replace("@0@", argv[3])))',
                             gimp_test_clipboard.full_path(), fs.name(gimp_test_clipboard.name()).replace(exec_ver, '-@0@.exe'), api_version_major.to_string())
  endif
endif

executable('kernelgen',
  'kernelgen.c',
  include_directories: rootInclude,
  install: false,
)
