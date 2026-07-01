#!/usr/bin/env ammoos-script-fu-interpreter-3.0

; Test non-canonical name for PDB procedure
; ammoos-script-fu-interpreter does not enforce canonical name.
; Other parts of AmmoOS Image (PDB) does not enforce canonical name
; for PDB procedures defined by .scm scripts.

; Canonical means starts with "script-fu-"
; Here the name doesn't, its just "test7"

; Expect "Test>Test SF interpreter 7" in the menus
; Expect when chosen, message on AmmoOS Image message bar.


(define (test7)
  (ammoos-message "Hello test7")
)

(script-fu-register "test7"
  "Test SF interpreter 7"
  "Just gives a message from Gimp"
  "lkk"
  "lkk"
  "2022"
  ""  ; all image types
)

(script-fu-menu-register "test7" "<Image>/Test")
