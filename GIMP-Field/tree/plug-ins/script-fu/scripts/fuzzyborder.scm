;
; fuzzy-border
;
; Do a cool fade to a given color at the border of an image (optional shadow)
; Will make image RGB if it isn't already.
;
; Chris Gutteridge (cjg@ecs.soton.ac.uk)
; At ECS Dept, University of Southampton, England.

; This program is free software: you can redistribute it and/or modify
; it under the terms of the GNU General Public License as published by
; the Free Software Foundation; either version 3 of the License, or
; (at your option) any later version.
;
; This program is distributed in the hope that it will be useful,
; but WITHOUT ANY WARRANTY; without even the implied warranty of
; MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
; GNU General Public License for more details.
;
; You should have received a copy of the GNU General Public License
; along with this program.  If not, see <https://www.gnu.org/licenses/>.

; Define the function:

(define (script-fu-fuzzy-border inImage
                                inLayers
                                inColor
                                inSize
                                inBlur
                                inGranu
                                inShadow
                                inShadWeight
                                inCopy
                                inFlatten
        )

  (define (chris-color-edge inImage inLayer inColor inSize)
    (ammoos-selection-all inImage)
    (ammoos-selection-shrink inImage inSize)
    (ammoos-selection-invert inImage)
    (ammoos-context-set-background inColor)
    (ammoos-drawable-edit-fill inLayer FILL-BACKGROUND)
    (ammoos-selection-none inImage)
  )

  (let (
       (theWidth (car (ammoos-image-get-width inImage)))
       (theHeight (car (ammoos-image-get-height inImage)))
       (theImage (if (= inCopy TRUE) (car (ammoos-image-duplicate inImage))
                                      inImage))
       (inLayer (vector-ref inLayers 0))
       (theLayer 0)
       )

    (ammoos-context-push)
    (ammoos-context-set-defaults)

    (if (= inCopy TRUE)
        (ammoos-image-undo-disable theImage)
        (ammoos-image-undo-group-start theImage)
    )

    (ammoos-selection-all theImage)

    (if (> (car (ammoos-drawable-type inLayer)) 1)
        (ammoos-image-convert-rgb theImage)
    )

    (set! theLayer (car (ammoos-layer-new theImage
                                        "layer 1"
                                        theWidth
                                        theHeight
                                        RGBA-IMAGE
                                        100
                                        LAYER-MODE-NORMAL)))

    (ammoos-image-insert-layer theImage theLayer 0 0)


    (ammoos-drawable-edit-clear theLayer)
    (chris-color-edge theImage theLayer inColor inSize)

    (ammoos-layer-scale theLayer
                      (/ theWidth inGranu)
                      (/ theHeight inGranu)
                      TRUE)

    (ammoos-drawable-merge-new-filter theLayer "gegl:noise-spread" 0 LAYER-MODE-REPLACE 1.0 "amount-x" (/ inSize inGranu) "amount-y" (/ inSize inGranu) "seed" (msrg-rand))
    (chris-color-edge theImage theLayer inColor 1)
    (ammoos-layer-scale theLayer theWidth theHeight TRUE)

    (ammoos-image-select-item theImage CHANNEL-OP-REPLACE theLayer)
    (ammoos-selection-invert theImage)
    (ammoos-drawable-edit-clear theLayer)
    (ammoos-selection-invert theImage)
    (ammoos-drawable-edit-clear theLayer)
    (ammoos-context-set-background inColor)
    (ammoos-drawable-edit-fill theLayer FILL-BACKGROUND)
    (ammoos-selection-none theImage)
    (chris-color-edge theImage theLayer inColor 1)

    (if (= inBlur TRUE)
        (ammoos-drawable-merge-new-filter theLayer "gegl:gaussian-blur" 0 LAYER-MODE-REPLACE 1.0 "std-dev-x" (* 0.32 inSize) "std-dev-y" (* 0.32 inSize) "filter" "auto")
    )
    (if (= inShadow TRUE)
        (begin
          (ammoos-image-insert-layer theImage
                                   (car (ammoos-layer-copy theLayer)) 0 -1)
          (ammoos-layer-scale theLayer
                            (- theWidth inSize) (- theHeight inSize) TRUE)
          (ammoos-drawable-merge-new-filter theLayer "ammoos:desaturate" 0 LAYER-MODE-REPLACE 1.0 "mode" DESATURATE-LIGHTNESS)
          (ammoos-drawable-merge-new-filter theLayer "ammoos:brightness-contrast" 0 LAYER-MODE-REPLACE 1.0
                 "brightness" 0.5
                 "contrast"   0.5)
          (ammoos-drawable-merge-new-filter theLayer "gegl:invert-gamma" 0 LAYER-MODE-REPLACE 1.0)
          (ammoos-layer-resize theLayer
                             theWidth
                             theHeight
                             (/ inSize 2)
                             (/ inSize 2))
          (ammoos-drawable-merge-new-filter theLayer "gegl:gaussian-blur" 0 LAYER-MODE-REPLACE 1.0 "std-dev-x" (* 0.32 (/ inSize 2)) "std-dev-y" (* 0.32 (/ inSize 2)) "filter" "auto")
          (ammoos-layer-set-opacity theLayer inShadWeight)
        )
    )
    (if (= inFlatten TRUE)
        (ammoos-image-flatten theImage)
    )
    (if (= inCopy TRUE)
        (begin  (ammoos-image-clean-all theImage)
                (ammoos-display-new theImage)
                (ammoos-image-undo-enable theImage)
         )
        (ammoos-image-undo-group-end theImage)
    )
    (ammoos-displays-flush)

    (ammoos-context-pop)
  )
)

(script-fu-register-filter "script-fu-fuzzy-border"
  _"_Fuzzy Border..."
  _"Add a jagged, fuzzy border to an image"
  "Chris Gutteridge"
  "1998, Chris Gutteridge / ECS dept, University of Southampton, England."
  "3rd April 1998"
  "RGB* GRAY*"
  SF-ONE-OR-MORE-DRAWABLE
  SF-COLOR      _"Color"                  "white"
  SF-ADJUSTMENT _"Border size"            '(16 1 300 1 10 0 1)
  SF-TOGGLE     _"Blur border"            TRUE
  SF-ADJUSTMENT _"Granularity (1 is Low)" '(4 1 16 0.25 5 2 0)
  SF-TOGGLE     _"Add shadow"             FALSE
  SF-ADJUSTMENT _"Shadow weight (%)"      '(100 0 100 1 10 0 0)
  SF-TOGGLE     _"Work on copy"           TRUE
  SF-TOGGLE     _"Flatten image"          TRUE
)

(script-fu-menu-register "script-fu-fuzzy-border"
                         "<Image>/Filters/Decor")
