; test PDB methods that change selection by another object
; such as a color or a channel



(script-fu-use-v3)

; Function to reset the selection
(define (testResetSelection testImage)
  (test! "Resetting selection to none")
  (assert `(ammoos-selection-none ,testImage))
  (assert `(ammoos-selection-is-empty ,testImage))
  ; The value of the selection mask at coords 64,64 is 0
  ; A value of the selection mask is in range [0,255]
  (assert `(= (ammoos-selection-value ,testImage 64 64)
            0)))


; setup
(define testImage (testing:load-test-image-basic-v3))
(define testLayer (vector-ref (ammoos-image-get-layers testImage)
                                  0))
; a layer mask from alpha
(define testLayerMask (ammoos-layer-create-mask
                              testLayer
                              ADD-MASK-ALPHA))
(ammoos-layer-add-mask testLayer testLayerMask)



(test! "new image has no initial selection")
; returns #t
(assert `(ammoos-selection-is-empty ,testImage))



(test! "selection by given color")

; returns void
(assert `(ammoos-image-select-color ,testImage CHANNEL-OP-ADD ,testLayer "black"))
; effective: test image has some black pixels, now selection is not empty
(assert `(not (ammoos-selection-is-empty ,testImage)))


(testResetSelection testImage)

(test! "selection by picking coords")
; !!! This is not the same as the menu item Select>By Color
; That menu item selects all pixels of a picked color.
; The PDB procedure selects a contiguous area (not disconnected pixels)
; and is more affected by settings in the context particularly sample-transparent.
; This test fails if you pick a coord that is transparent,
; since sample-transparent defaults to false?
;
; The test image has a non-transparent pixel at 64,64
; but a transparent pixel at 125,125


; ammoos-image-select-contiguous-color does not throw
(assert `(ammoos-image-select-contiguous-color ,testImage CHANNEL-OP-ADD ,testLayer 64 64))
; effective, now selection is not empty
(assert `(not (ammoos-selection-is-empty ,testImage)))
; effective, the selection value at the picked coords is "totally selected"
(assert `(= (ammoos-selection-value ,testImage 64 64)
            255))


(testResetSelection testImage)

(test! "selection from item same layer")

; selection from the layer itself: selects same as layer's alpha
(assert `(ammoos-image-select-item ,testImage CHANNEL-OP-ADD ,testLayer))
; effective: selection is not empty
(assert `(not (ammoos-selection-is-empty ,testImage)))

(testResetSelection testImage)

(test! "selection from layer mask")

; layer mask to selection succeeds
(assert `(ammoos-image-select-item ,testImage CHANNEL-OP-ADD ,testLayerMask))
; effective: selection is not empty
(assert `(not (ammoos-selection-is-empty ,testImage)))

; TODO selection from
; channel, vectors
; TODO selection from layer group? fails?


; for debugging individual test file:
; (ammoos-display-new testImage)

(script-fu-use-v2)
