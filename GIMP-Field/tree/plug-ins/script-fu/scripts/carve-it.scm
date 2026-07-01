;  CARVE-IT
;   Carving, embossing, & stamping
;   Process taken from "The Photoshop 3 WOW! Book"
;   http://www.peachpit.com
;   This script requires a grayscale image containing a single layer.
;   This layer is used as the mask for the carving effect
;   NOTE: This script requires the image to be carved to either be an
;   RGB color or grayscale image with a single layer. An indexed file
;   can not be used due to the use of ammoos-drawable-histogram and
;   ammoos-drawable-levels.


(define (carve-scale val scale)
  (* (sqrt val) scale))

(define (calculate-inset-gamma img layer)
  (let* ((stats (ammoos-drawable-histogram layer 0 0.0 1.0))
         (mean (car stats)))
    (cond ((< mean 127) (+ 1.0 (* 0.5 (/ (- 127 mean) 127.0))))
          ((>= mean 127) (- 1.0 (* 0.5 (/ (- mean 127) 127.0)))))))


(define (copy-layer-carve-it dest-image dest-drawable source-image source-drawable)
  (ammoos-selection-all dest-image)
  (ammoos-drawable-edit-clear dest-drawable)
  (ammoos-selection-none dest-image)
  (ammoos-selection-all source-image)
  (ammoos-edit-copy (vector source-drawable))
  (let* (
         (pasted (car (ammoos-edit-paste dest-drawable FALSE)))
         (floating-sel (vector-ref pasted (- (vector-length pasted) 1)))
        )
        (ammoos-floating-sel-anchor floating-sel)
  )
)



(define (script-fu-carve-it bg-img bg-layers mask-img mask-drawable carve-white)
  (let* (
        (src-layer (vector-ref bg-layers 0))
        (width (car (ammoos-drawable-get-width mask-drawable)))
        (height (car (ammoos-drawable-get-height mask-drawable)))
        (type (car (ammoos-drawable-type src-layer)))
        (img (car (ammoos-image-new width height (cond ((= type RGB-IMAGE) RGB)
                                                     ((= type RGBA-IMAGE) RGB)
                                                     ((= type GRAY-IMAGE) GRAY)
                                                     ((= type GRAYA-IMAGE) GRAY)
                                                     ((= type INDEXED-IMAGE) INDEXED)
                                                     ((= type INDEXEDA-IMAGE) INDEXED)))))
        (size (min width height))
        (offx (carve-scale size 0.33))
        (offy (carve-scale size 0.25))
        (feather (carve-scale size 0.3))
        (brush-size (carve-scale size 0.3))
        (brush (car (ammoos-brush-new "Carve It")))
        (mask (car (ammoos-channel-new img "Engraving Mask" width height 50 '(0 0 0))))
        (inset-gamma (calculate-inset-gamma (car (ammoos-item-get-image src-layer)) src-layer))
        (mask-fat 0)
        (mask-emboss 0)
        (mask-highlight 0)
        (mask-shadow 0)
        (shadow-layer 0)
        (highlight-layer 0)
        (cast-shadow-layer 0)
        (csl-mask 0)
        (inset-layer 0)
        (il-mask 0)
        (bg-width (car (ammoos-drawable-get-width src-layer)))
        (bg-height (car (ammoos-drawable-get-height src-layer)))
        (bg-type (car (ammoos-drawable-type src-layer)))
        (bg-image (car (ammoos-item-get-image src-layer)))
        (layer1 (car (ammoos-layer-new img "Layer1" bg-width bg-height bg-type 100 LAYER-MODE-NORMAL)))
        )

    (ammoos-context-push)
    (ammoos-context-set-defaults)

    (ammoos-image-undo-disable img)

    (ammoos-image-insert-layer img layer1 0 0)

    (ammoos-selection-all img)
    (ammoos-drawable-edit-clear layer1)
    (ammoos-selection-none img)
    (copy-layer-carve-it img layer1 bg-image src-layer)

    (ammoos-edit-copy (vector mask-drawable))
    (ammoos-image-insert-channel img mask -1 0)

    (plug-in-tile #:run-mode   RUN-NONINTERACTIVE
                  #:image      img
                  #:drawables  (vector layer1)
                  #:new-width  width
                  #:new-height height
                  #:new-image  FALSE)
    (let* (
           (pasted (car (ammoos-edit-paste mask FALSE)))
           (floating-sel (vector-ref pasted(- (vector-length pasted) 1)))
          )
          (ammoos-floating-sel-anchor floating-sel)
    )
    (if (= carve-white FALSE)
        (ammoos-drawable-merge-new-filter mask "gegl:invert-gamma" 0 LAYER-MODE-REPLACE 1.0))

    (set! mask-fat (car (ammoos-channel-copy mask)))
    (ammoos-image-insert-channel img mask-fat -1 0)
    (ammoos-image-select-item img CHANNEL-OP-REPLACE mask-fat)

    (ammoos-brush-set-shape brush BRUSH-GENERATED-CIRCLE)
    (ammoos-brush-set-spikes brush 2)
    (ammoos-brush-set-hardness brush 1.0)
    (ammoos-brush-set-spacing brush 25)
    (ammoos-brush-set-aspect-ratio brush 1)
    (ammoos-brush-set-angle brush 0)
    (cond (<= brush-size 17) (ammoos-brush-set-radius brush (\ brush-size 2))
	  (else ammoos-brush-set-radius brush (\ 19 2)))
    (ammoos-context-set-brush brush)

    (ammoos-context-set-foreground '(255 255 255))
    (ammoos-drawable-edit-stroke-selection mask-fat)
    (ammoos-selection-none img)

    (set! mask-emboss (car (ammoos-channel-copy mask-fat)))
    (ammoos-image-insert-channel img mask-emboss -1 0)
    (ammoos-drawable-merge-new-filter mask-emboss "gegl:gaussian-blur" 0 LAYER-MODE-REPLACE 1.0 "std-dev-x" (* 0.32 feather) "std-dev-y" (* 0.32 feather) "filter" "auto")
    (ammoos-drawable-merge-new-filter mask-emboss "gegl:emboss" 0 LAYER-MODE-REPLACE 1.0 "azimuth" 315.0 "elevation" 45.0 "depth" 7 "type" "emboss")

    (ammoos-context-set-background '(180 180 180))
    (ammoos-image-select-item img CHANNEL-OP-REPLACE mask-fat)
    (ammoos-selection-invert img)
    (ammoos-drawable-edit-fill mask-emboss FILL-BACKGROUND)
    (ammoos-image-select-item img CHANNEL-OP-REPLACE mask)
    (ammoos-drawable-edit-fill mask-emboss FILL-BACKGROUND)
    (ammoos-selection-none img)

    (set! mask-highlight (car (ammoos-channel-copy mask-emboss)))
    (ammoos-image-insert-channel img mask-highlight -1 0)
    (ammoos-drawable-levels mask-highlight 0
			  0.7056 1.0 TRUE
			  1.0
			  0.0 1.0 TRUE)

    (set! mask-shadow mask-emboss)
    (ammoos-drawable-levels mask-shadow 0
			  0.0 0.70586 TRUE
			  1.0
			  0.0 1.0 TRUE)

    (ammoos-edit-copy (vector mask-shadow))
    (let* (
           (pasted (car (ammoos-edit-paste layer1 FALSE)))
           (floating-sel (vector-ref pasted (- (vector-length pasted) 1)))
          )
          (set! shadow-layer floating-sel)
          (ammoos-floating-sel-to-layer shadow-layer)
    )
    (ammoos-layer-set-mode shadow-layer LAYER-MODE-MULTIPLY)

    (ammoos-edit-copy (vector mask-highlight))
    (let* (
           (pasted (car (ammoos-edit-paste shadow-layer FALSE)))
           (floating-sel (vector-ref pasted (- (vector-length pasted) 1)))
          )
          (set! highlight-layer floating-sel)
          (ammoos-floating-sel-to-layer highlight-layer)
    )
    (ammoos-layer-set-mode highlight-layer LAYER-MODE-SCREEN)

    (ammoos-edit-copy (vector mask))
    (let* (
           (pasted (car (ammoos-edit-paste highlight-layer FALSE)))
           (floating-sel (vector-ref pasted (- (vector-length pasted) 1)))
          )
          (set! cast-shadow-layer floating-sel)
          (ammoos-floating-sel-to-layer cast-shadow-layer)
    )
    (ammoos-layer-set-mode cast-shadow-layer LAYER-MODE-MULTIPLY)
    (ammoos-layer-set-opacity cast-shadow-layer 75)

    (ammoos-drawable-merge-new-filter cast-shadow-layer "gegl:gaussian-blur" 0 LAYER-MODE-REPLACE 1.0 "std-dev-x" (* 0.32 feather) "std-dev-y" (* 0.32 feather) "filter" "auto")
    (ammoos-item-transform-translate cast-shadow-layer offx offy)

    (set! csl-mask (car (ammoos-layer-create-mask cast-shadow-layer ADD-MASK-BLACK)))
    (ammoos-layer-add-mask cast-shadow-layer csl-mask)
    (ammoos-image-select-item img CHANNEL-OP-REPLACE mask)
    (ammoos-context-set-background '(255 255 255))
    (ammoos-drawable-edit-fill csl-mask FILL-BACKGROUND)

    (set! inset-layer (car (ammoos-layer-copy layer1)))
    (ammoos-layer-add-alpha inset-layer)
    (ammoos-image-insert-layer img inset-layer 0 1)

    (set! il-mask (car (ammoos-layer-create-mask inset-layer ADD-MASK-BLACK)))
    (ammoos-layer-add-mask inset-layer il-mask)
    (ammoos-image-select-item img CHANNEL-OP-REPLACE mask)
    (ammoos-context-set-background '(255 255 255))
    (ammoos-drawable-edit-fill il-mask FILL-BACKGROUND)
    (ammoos-selection-none img)
    (ammoos-selection-none bg-image)
    (ammoos-drawable-levels inset-layer 0 0.0 1.0 TRUE inset-gamma 0.0 1.0 TRUE)
    (ammoos-image-remove-channel img mask)
    (ammoos-image-remove-channel img mask-fat)
    (ammoos-image-remove-channel img mask-highlight)
    (ammoos-image-remove-channel img mask-shadow)

    (ammoos-item-set-name layer1 _"Carved Surface")
    (ammoos-item-set-name shadow-layer _"Bevel Shadow")
    (ammoos-item-set-name highlight-layer _"Bevel Highlight")
    (ammoos-item-set-name cast-shadow-layer _"Cast Shadow")
    (ammoos-item-set-name inset-layer _"Inset")

    (ammoos-resource-delete brush)

    (ammoos-display-new img)
    (ammoos-image-undo-enable img)

    (ammoos-context-pop)
  )
)

(script-fu-register-filter "script-fu-carve-it"
    _"Stencil C_arve..."
    _"Use the specified drawable as a stencil to carve from the specified image."
    "Spencer Kimball"
    "Spencer Kimball"
    "1997"
    "GRAY"
    SF-ONE-OR-MORE-DRAWABLE
    SF-IMAGE    _"Mask image"        0
    SF-DRAWABLE _"Mask drawable"     0
    SF-TOGGLE   _"Carve white areas" TRUE
)

(script-fu-menu-register "script-fu-carve-it"
                         "<Image>/Filters/Decor")
