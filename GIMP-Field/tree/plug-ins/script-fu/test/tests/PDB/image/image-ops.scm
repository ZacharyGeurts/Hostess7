; Test various operations on image

; The operand is the total image itself.
; For paint operations (changing a subset of the image) see paint.scm


(script-fu-use-v3)


;              setup
(define testImage (ammoos-image-new 21 22 RGB))


(test! "image transformations")

; flip
(assert `(ammoos-image-flip ,testImage ORIENTATION-HORIZONTAL))
(assert `(ammoos-image-flip ,testImage ORIENTATION-VERTICAL))

(assert-error `(ammoos-image-flip ,testImage ORIENTATION-UNKNOWN)
    (string-append
      "Procedure execution of ammoos-image-flip failed on invalid input arguments: "
      "Procedure 'ammoos-image-flip' has been called with value 'GIMP_ORIENTATION_UNKNOWN'"
      " for argument 'flip-type' (#2, type GimpOrientationType). This value is out of range."))

; rotate
; v2 ROTATE-90 => v3 ROTATE-DEGREES90
(assert `(ammoos-image-rotate ,testImage ROTATE-DEGREES90))
(assert `(ammoos-image-rotate ,testImage ROTATE-DEGREES180))
(assert `(ammoos-image-rotate ,testImage ROTATE-DEGREES270))

; scale
; up
(assert `(ammoos-image-scale ,testImage 100 100))

; down to min
(assert `(ammoos-image-scale ,testImage 1 1))

; up to max
; Performance:
; This seems to work fast when previous scaled to 1,1
; but then seems to slow down testing
; unless we scale down afterwards.
; This seems glacial if not scaled to 1,1 prior.
; FIXME throws GLib-GObject-CRITICAL value "524288.000000" of type 'gdouble'
; is invalid or out of range for property 'x' of type 'gdouble'
; but docs say 524288 is the max
; (assert `(ammoos-image-scale ,testImage 524288 524288))

; down to min does not throw
(assert `(ammoos-image-scale ,testImage 1 1))
; effective
(assert `(= (ammoos-image-get-height ,testImage)
            1))
; Note there is no get-size, only get-height and width, the origin is always (0,0)


; resize does not throw
(assert `(ammoos-image-resize ,testImage
            30 30 ; width height
            0 0)) ; offset
; effective
(assert `(= (ammoos-image-get-height ,testImage)
            30))

; resize to layers when image is empty of layers does not throw
(assert `(ammoos-image-resize-to-layers ,testImage))
; not effective: height remains the same
; effective
(assert `(= (ammoos-image-get-height ,testImage)
            30))

; TODO resize to layers when there is a layer smaller than canvas



; TODO crops that are plugins plug-in-zealouscrop et al

(test! "crop")

(assert `(ammoos-image-crop ,testImage
    2 2 ; width height
    2 2 ; x y offset
    ))



(test! "image transformation by policy ops")
; These perform operations (convert or rotate) using a policy in preferences

; 0 means non-interactive, else shows dialog in some cases
(assert `(ammoos-image-policy-color-profile ,testImage 0))

(assert `(ammoos-image-policy-rotate ,testImage 0))



(test! "freezing and unfreezing (avoid updates to dialogs)")

; Used for performance.
(assert `(ammoos-image-freeze-channels ,testImage))
(assert `(ammoos-image-freeze-layers ,testImage))
(assert `(ammoos-image-freeze-paths ,testImage))
(assert `(ammoos-image-thaw-channels ,testImage))
(assert `(ammoos-image-thaw-layers ,testImage))
(assert `(ammoos-image-thaw-paths ,testImage))

(test! "clean-all makes image not dirty")
(assert `(ammoos-image-clean-all ,testImage))
(assert `(not (ammoos-image-is-dirty ,testImage)))


; flatten is tested in layer-ops.scm

; cannot flatten empty image
(assert-error `(ammoos-image-flatten ,testImage)
  "Procedure execution of ammoos-image-flatten failed: Cannot flatten an image without any visible layer.")

(script-fu-use-v2)