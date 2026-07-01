; test Layer methods of PDB
; where methods are operations


(script-fu-use-v3)



; setup

(define testImage (ammoos-image-new 21 22 RGB))
(define testLayer (testing:layer-new testImage))
; assert layer is not inserted in image


(test! "errors when layer not in image")

; resize fails
(assert-error `(ammoos-layer-resize ,testLayer 23 24 0 0)
              (string-append
                "Procedure execution of ammoos-layer-resize failed on invalid input arguments: "))
                ;"Item 'LayerNew#2' (10) cannot be used because it has not been added to an image"))

; scale fails
(assert-error `(ammoos-layer-scale ,testLayer
                  23 24 ; width height
                  0)    ; is local origin?
              (string-append
                "Procedure execution of ammoos-layer-scale failed on invalid input arguments: "))
                ;"Item 'LayerNew#2' (10) cannot be used because it has not been added to an image"))

; UNTESTED ammoos-layer-resize-to-image-size fails when layer not in image

; ammoos-layer-remove-mask fails when layer not in image
(assert-error `(ammoos-layer-remove-mask
                  ,testLayer
                  MASK-APPLY)
              (string-append
                "Procedure execution of ammoos-layer-remove-mask failed on invalid input arguments: "))
                ; "Item 'LayerNew#2' (10) cannot be used because it has not been added to an image"))



;              alpha operations

; add-alpha succeeds
(assert `(ammoos-layer-add-alpha ,testLayer))

; and is effective
; Note method on superclass Drawable
; returns #t
(assert `(ammoos-drawable-has-alpha ,testLayer))

; flatten succeeds
(assert `(ammoos-layer-flatten ,testLayer))

; flatten was effective: no longer has alpha
; flatten a layer means "remove alpha"
; returns #f
(assert `(not (ammoos-drawable-has-alpha ,testLayer)))




(test! "layer-delete")

; ammoos-layer-delete is deprecated

; succeeds
(assert `(ammoos-item-delete ,testLayer))

; delete second time fails
(assert-error `(ammoos-item-delete ,testLayer)
              "Invalid value for argument 0")
; FORMERLY    "runtime: invalid item ID")

; Error for flatten:
; "Procedure execution of ammoos-layer-delete failed on invalid input arguments: "
; "Procedure 'ammoos-layer-delete' has been called with an invalid ID for argument 'layer'. "
; "Most likely a plug-in is trying to work on a layer that doesn't exist any longer."))


(script-fu-use-v2)
