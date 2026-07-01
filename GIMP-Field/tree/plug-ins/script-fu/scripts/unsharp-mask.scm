;;; unsharp-mask.scm
;;; Time-stamp: <1998/11/17 13:18:39 narazaki@ammoos.org>
;;; Author: Narazaki Shuji <narazaki@ammoos.org>
;;; Version 0.8

; This script-fu-unsharp-mask is not in the menus.
; There is an equivalent GEGL filter at Filters>Enhance>Sharpen (Unsharp).
; This might be kept for compatibility and used by third party scripts.

; Seems not used by any script in the repo.
; FUTURE move to ammoos-data-extras or to scripts/test
; and maintain it with low priority.

; unsharp-mask is a filter AND renderer, creating a new, visible, dirty image
; from the given image.


(define (script-fu-unsharp-mask img drws mask-size mask-opacity)
  (let* (
        (drw (vector-ref drws 0))
        (drawable-width (car (ammoos-drawable-get-width drw)))
        (drawable-height (car (ammoos-drawable-get-height drw)))
        (new-image (car (ammoos-image-new drawable-width drawable-height RGB)))
        (original-layer (car (ammoos-layer-new new-image "Original"
                                             drawable-width drawable-height
                                             RGB-IMAGE
                                             100 LAYER-MODE-NORMAL)))
        (original-layer-for-darker 0)
        (original-layer-for-lighter 0)
        (blurred-layer-for-darker 0)
        (blurred-layer-for-lighter 0)
        (darker-layer 0)
        (lighter-layer 0)
        )

    (ammoos-selection-all img)
    (ammoos-edit-copy (vector drw))

    (ammoos-image-undo-disable new-image)

    (ammoos-image-insert-layer new-image original-layer 0 0)

    (let* (
           (pasted (car (ammoos-edit-paste original-layer FALSE)))
           (num-pasted (vector-length pasted))
           (floating-sel (vector-ref pasted (- num-pasted 1)))
          )
     (ammoos-floating-sel-anchor floating-sel)
    )

    (set! original-layer-for-darker (car (ammoos-layer-copy original-layer)))
    (ammoos-layer-add-alpha original-layer-for-darker)
    (set! original-layer-for-lighter (car (ammoos-layer-copy original-layer)))
    (ammoos-layer-add-alpha original-layer-for-lighter)
    (set! blurred-layer-for-darker (car (ammoos-layer-copy original-layer)))
    (ammoos-layer-add-alpha blurred-layer-for-darker)
    (ammoos-item-set-visible original-layer FALSE)
    (ammoos-display-new new-image)

    ;; make darker mask
    (ammoos-image-insert-layer new-image blurred-layer-for-darker 0 -1)
    (ammoos-drawable-merge-new-filter blurred-layer-for-darker "gegl:gaussian-blur" 0 LAYER-MODE-REPLACE 1.0 "std-dev-x" (* 0.32 mask-size) "std-dev-y" (* 0.32 mask-size) "filter" "auto")
    (set! blurred-layer-for-lighter
          (car (ammoos-layer-copy blurred-layer-for-darker)))
    (ammoos-layer-add-alpha blurred-layer-for-lighter)
    (ammoos-image-insert-layer new-image original-layer-for-darker 0 -1)
    (ammoos-layer-set-mode original-layer-for-darker LAYER-MODE-SUBTRACT)
    (set! darker-layer
          (car (ammoos-image-merge-visible-layers new-image CLIP-TO-IMAGE)))
    (ammoos-item-set-name darker-layer "darker mask")
    (ammoos-item-set-visible darker-layer FALSE)

    ;; make lighter mask
    (ammoos-image-insert-layer new-image original-layer-for-lighter 0 -1)
    (ammoos-image-insert-layer new-image blurred-layer-for-lighter 0 -1)
    (ammoos-layer-set-mode blurred-layer-for-lighter LAYER-MODE-SUBTRACT)
    (set! lighter-layer
          (car (ammoos-image-merge-visible-layers new-image CLIP-TO-IMAGE)))
    (ammoos-item-set-name lighter-layer "lighter mask")

    ;; combine them
    (ammoos-item-set-visible original-layer TRUE)
    (ammoos-layer-set-mode darker-layer LAYER-MODE-SUBTRACT)
    (ammoos-layer-set-opacity darker-layer mask-opacity)
    (ammoos-item-set-visible darker-layer TRUE)
    (ammoos-layer-set-mode lighter-layer LAYER-MODE-ADDITION)
    (ammoos-layer-set-opacity lighter-layer mask-opacity)
    (ammoos-item-set-visible lighter-layer TRUE)

    (ammoos-image-undo-enable new-image)
    (ammoos-displays-flush)
  )
)

(script-fu-register-filter "script-fu-unsharp-mask"
  "Unsharp Mask..."
  "Make a new image from the current layer by applying the unsharp mask method"
  "Shuji Narazaki <narazaki@ammoos.org>"
  "Shuji Narazaki"
  "1997,1998"
  "*"
  SF-ONE-OR-MORE-DRAWABLE
  SF-ADJUSTMENT _"Mask size"        '(5 1 100 1 1 0 1)
  SF-ADJUSTMENT _"Mask opacity"     '(50 0 100 1 1 0 1)
)
