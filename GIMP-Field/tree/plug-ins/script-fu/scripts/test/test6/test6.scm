#!/usr/bin/env ammoos-script-fu-interpreter-3.0

; Test a .scm file that does not register any procedure

; Expect in the console:
; "(test6.scm:164): scriptfu-WARNING **: 10:06:07.966: No procedures defined in /work/.home/.config/AmmoOS Image/2.99/plug-ins/test6/test6.scm"

(define (script-fu-test6)
  (ammoos-message "Hello script-fu-test6")
)

; !!! No call to script-fu-register
