; test Layer methods of PDB


(script-fu-use-v3)


;        setup

(define testImage (ammoos-image-new 21 22 RGB))

(define testLayer (testing:layer-new testImage))




(test! "new layer is not in the image until inserted")
; returns (length, list), check length is 0
(assert `(= (vector-length (ammoos-image-get-layers ,testImage))
            0))



(test! "attributes of new layer")

;        defaulted attributes

; apply-mask default false
(assert `(not (ammoos-layer-get-apply-mask ,testLayer)))

; blend-space default LAYER-COLOR-SPACE-AUTO
(assert `(= (ammoos-layer-get-blend-space ,testLayer)
            LAYER-COLOR-SPACE-AUTO))

; composite-mode default LAYER-COMPOSITE-AUTO
(assert `(= (ammoos-layer-get-composite-mode ,testLayer)
            LAYER-COMPOSITE-AUTO))

; composite-space default LAYER-COLOR-SPACE-AUTO
(assert `(= (ammoos-layer-get-composite-space ,testLayer)
            LAYER-COLOR-SPACE-AUTO))

; edit-mask default false
(assert `(not (ammoos-layer-get-edit-mask ,testLayer)))

; lock-alpha default false
; deprecated? ammoos-layer-get-preserve-trans
(assert `(not (ammoos-layer-get-lock-alpha ,testLayer)))

; mask not exist, ID -1
; ammoos-layer-mask is deprecated
(assert `(= (ammoos-layer-get-mask ,testLayer)
            -1))

; mode default LAYER-MODE-NORMAL
(assert `(= (ammoos-layer-get-mode ,testLayer)
            LAYER-MODE-NORMAL))

; show-mask default false
(assert `(not (ammoos-layer-get-show-mask ,testLayer)))

; visible default true
; FIXME doc says default false
; ammoos-layer-get-visible is deprecated.
(assert `(ammoos-item-get-visible ,testLayer))

; is-floating-sel default false
(assert `(not (ammoos-layer-is-floating-sel ,testLayer)))

; !!! No get-offsets




(test! "new layer attributes are as given when created")

; name is as given
; ammoos-layer-get-name is deprecated
(assert `(string=? (ammoos-item-get-name ,testLayer)
                  "LayerNew"))

; opacity is as given
(assert `(= (ammoos-layer-get-opacity ,testLayer)
            50.0))


;          generated attributes

; tattoo
; tattoo is generated unique within image?
; ammoos-layer-get-tattoo is deprecated
(assert `(= (ammoos-item-get-tattoo ,testLayer)
            2))



(script-fu-use-v2)





