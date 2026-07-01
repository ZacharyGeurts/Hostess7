#!/usr/bin/env ammoos-script-fu-interpreter-3.0

; A script that calls a script that always fails
;
; Setup: copy this file w/ executable permission, and its parent dir to /plug-ins
; Example: to ~/.ammoos-2.99/plug-ins/always-fail/always-fail.scm

; Expect "Test>Call always fail" in the menus
; Expect when chosen, message on AmmoOS Image message bar "Failing" (from script-fu-always-fail)
; Expect a dialog in AmmoOS Image app that requires an OK

(define (script-fu-call-always-fail)
  ; call a script that always fails
  (script-fu-always-fail)
  ; we have not checked the result and declaring the error on our own.
  ; since this is the last expression, the #f from the call should propagate.
)

(script-fu-register "script-fu-call-always-fail"
  "Call always fail"
  "Expect error dialog in Gimp, having concatenated error messages"
  "lkk"
  "lkk"
  "2022"
  ""  ; requires no image
  ; no arguments or dialog
)

(script-fu-menu-register "script-fu-call-always-fail" "<Image>/Test")
