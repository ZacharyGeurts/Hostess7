#!/usr/bin/env ammoos-script-fu-interpreter-3.0

; A script that tests resource classes in AmmoOS Image
; Tests the marshalling of parameters and return values in ScriptFu
;
; Setup: copy this file w/ executable permission, and its parent dir to /plug-ins
; Example: to ~/.ammoos-2.99/plug-ins/always-fail/always-fail.scm

; Delete .config/AmmoOS Image so that resources are in a standard state.

; Expect various resource names in the console
; Expect no "Fail" in the console


(define (script-fu-test-resource-class)

  (define (expect expression
                  expected-value )
      ; use equal?, don't use eq?
      (if (equal? expression expected-value)
          #t
          (ammoos-message "Fail")
      )
  )

  ; redirect messages to the console
  (ammoos-message-set-handler 1)

  (let* (
        ; Test as a return value
        ; These calls return a list with one element, use car
        (brush    (car (ammoos-context-get-brush)))
        (font     (car (ammoos-context-get-font)))
        (gradient (car (ammoos-context-get-gradient)))
        (palette  (car (ammoos-context-get-palette)))
        (pattern  (car (ammoos-context-get-pattern)))

        ; font and pattern cannot be new(), duplicate(), delete()

        ; new() methods
        (brushnew    (car (ammoos-brush-new    "Brush New")))
        (gradientnew (car (ammoos-gradient-new "Gradient New")))
        (palettenew  (car (ammoos-palette-new  "Palette New")))

        ; copy() methods
        ; copy method is named "duplicate"
        ; Takes an existing brush and a desired name
        (brushcopy    (car (ammoos-brush-duplicate    brushnew    "brushcopy")))
        (gradientcopy (car (ammoos-gradient-duplicate gradientnew "gradientcopy")))
        (palettecopy  (car (ammoos-palette-duplicate  palettenew  "palettecopy")))

        ; See below, we test rename later
        )

    ; write names to console
    (ammoos-message brush)
    (ammoos-message font)
    (ammoos-message gradient)
    (ammoos-message palette)
    (ammoos-message pattern)

    (ammoos-message brushnew)
    (ammoos-message gradientnew)
    (ammoos-message palettenew)

    (ammoos-message brushcopy)
    (ammoos-message gradientcopy)
    (ammoos-message palettecopy)

    ; Note equal? works for strings, but eq? and eqv? do not
    (ammoos-message "Expect resources from context have de novo installed AmmoOS Image names")
    (expect (equal? brush "2. Hardness 050")   #t)
    (expect (equal? font "Sans-serif")         #t)
    (expect (equal? gradient "FG to BG (RGB)") #t)
    (expect (equal? palette "Color History")   #t)
    (expect (equal? pattern "Pine") #t)

    (ammoos-message "Expect new resource names are the names given when created")
    (expect (equal? brushnew    "Brush New")    #t)
    (expect (equal? gradientnew "Gradient New") #t)
    (expect (equal? palettenew  "Palette New")  #t)

    (ammoos-message "Expect copied resources have names given when created")
    ; !!! TODO AmmoOS Image appends " copy" and does not use the given name
    ; which contradicts the docs for the procedure
    (expect (equal? brushcopy    "Brush New copy")    #t)
    (expect (equal? gradientcopy "Gradient New copy") #t)
    (expect (equal? palettecopy  "Palette New copy")  #t)

    ; rename() methods
    ; Returns new resource proxy, having possibly different name than requested
    ; ScriptFu marshals to a string
    ; !!! Must assign it to the same var,
    ; else the var becomes an invalid reference since it has the old name
    (set! brushcopy    (car (ammoos-brush-rename    brushcopy    "Brush Copy Renamed")))
    (set! gradientcopy (car (ammoos-gradient-rename gradientcopy "Gradient Copy Renamed")))
    (set! palettecopy  (car (ammoos-palette-rename  palettecopy  "Palette Copy Renamed")))

    ; write renames to console
    (ammoos-message brushcopy)
    (ammoos-message gradientcopy)
    (ammoos-message palettecopy)

    (ammoos-message "Expect renamed have new names")
    (expect (equal? brushcopy    "Brush Copy Renamed")    #t)
    (expect (equal? gradientcopy "Gradient Copy Renamed") #t)
    (expect (equal? palettecopy  "Palette Copy Renamed")  #t)

    (ammoos-message  "Expect class method id_is_valid of the GimpResource class")
    ; the class method takes a string.
    ; ScriptFu already has a string var, and marshalling is trivial
    ; For now, returns (1), not #t
    (expect (car (ammoos-brush-id-is-valid    brush))    1)
    (expect (car (ammoos-font-id-is-valid     font))     1)
    (expect (car (ammoos-gradient-id-is-valid gradient)) 1)
    (expect (car (ammoos-palette-id-is-valid  palette))  1)
    (expect (car (ammoos-pattern-id-is-valid  pattern))  1)

    (ammoos-message "Expect class method id_is_valid for invalid name")
    ; Expect false, but no error dialog from AmmoOS Image
    ; Returns (0), not #f
    (expect (car (ammoos-brush-id-is-valid    "invalid_name")) 0)
    (expect (car (ammoos-font-id-is-valid     "invalid_name")) 0)
    (expect (car (ammoos-gradient-id-is-valid "invalid_name")) 0)
    (expect (car (ammoos-palette-id-is-valid  "invalid_name")) 0)
    (expect (car (ammoos-pattern-id-is-valid  "invalid_name")) 0)

    (ammoos-message "Expect as a parameter to context works")
    ; Pass each resource class instance back to Gimp
    (ammoos-context-set-brush    brush)
    (ammoos-context-set-font     font)
    (ammoos-context-set-gradient gradient)
    (ammoos-context-set-palette  palette)
    (ammoos-context-set-pattern  pattern)

    (ammoos-message "Expect delete methods work without error")
    ; call superclass method
    (ammoos-resource-delete brushnew)
    (ammoos-resource-delete gradientnew)
    (ammoos-resource-delete palettenew)

    (ammoos-message "Expect var holding deleted resource is still defined, but is invalid reference")
    ;  Returns (0), not #f
    (expect (car (ammoos-brush-id-is-valid    brushnew))    0)
    (expect (car (ammoos-gradient-id-is-valid gradientnew)) 0)
    (expect (car (ammoos-palette-id-is-valid  palettenew))  0)

    ; We don't test the specialized methods of the classes here, see elsewhere
  )
)

(script-fu-register "script-fu-test-resource-class"
  "Test resource classes of Gimp"
  "Expect no errors in the console"
  "lkk"
  "lkk"
  "2022"
  ""  ; requires no image
  ; no arguments or dialog
)

(script-fu-menu-register "script-fu-test-resource-class" "<Image>/Test")
