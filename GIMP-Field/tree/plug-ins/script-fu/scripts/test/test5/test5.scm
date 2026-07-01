#!/usr/bin/env ammoos-script-fu-interpreter

; Test a .scm file with an invalid shebang
; Note "-3.0" missing above.

; The test depends on platform and env and .interp
; Must not be a file system link from ammoos-script-fu-interpreter to ammoos-script-fu-interpreter-3.0
; Must not be a .interp file having  "ammoos-script-fu-interpreter=ammoos-script-fu-interpreter-3.0"

; Expect in the console: "/usr/bin/env: 'script-fu-interpreter': No such file or directory"

(define (script-fu-test5)
  (ammoos-message "Hello script-fu-test5")
)

; !!! No call to script-fu-menu-register
