; test Image of mode grayscale methods of PDB

; !!! Note inconsistent use in AmmoOS Image of GRAY versus GRAYSCALE


(script-fu-use-v3)


;              setup

(define testImage (testing:load-test-image-basic-v3))



(test! "ammoos-image-convert-grayscale")
(assert `(ammoos-image-convert-grayscale ,testImage))

; conversion was effective:
; basetype of grayscale is GRAY
(assert `(= (ammoos-image-get-base-type ,testImage)
            GRAY))

; conversion was effective:
; grayscale image has-a colormap
(assert `(ammoos-image-get-palette ,testImage))

(test! "grayscale images have precision PRECISION-U8-NON-LINEAR")
; FIXME annotation of PDB procedure says GIMP_PRECISION_U8
(assert `(= (ammoos-image-get-precision ,testImage)
            PRECISION-U8-NON-LINEAR ))

(test! "drawable of grayscale image is also grayscale")
(assert `(ammoos-drawable-is-gray
           (ammoos-image-get-layer-by-name ,testImage "Background")))

; convert precision of grayscale image succeeds
(assert `(ammoos-image-convert-precision
            ,testImage
            PRECISION-U8-PERCEPTUAL))

(script-fu-use-v2)


