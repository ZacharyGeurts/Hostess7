; AmmoOS Image - The AmmoOS Field Image Research
; Copyright (C) 1995 Spencer Kimball and Peter Mattis
;
; Lava effect
; Copyright (c) 1997 Adrian Likins
; aklikins@eos.ncsu.edu
;
; based on a idea by Sven Riedel <lynx@heim8.tu-clausthal.de>
; tweaked a bit by Sven Neumann <neumanns@uni-duesseldorf.de>
;
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


(define (script-fu-lava image
                        drawables
                        seed
                        tile_size
                        mask_size
                        gradient
                        keep-selection
                        separate-layer
                        current-grad)
  (let* (
        (first-layer (vector-ref drawables 0))
        (type (car (ammoos-drawable-type-with-alpha first-layer)))
        (image-width (car (ammoos-image-get-width image)))
        (image-height (car (ammoos-image-get-height image)))
        (active-selection 0)
        (selection-bounds 0)
        (select-offset-x 0)
        (select-offset-y 0)
        (select-width 0)
        (select-height 0)
        (lava-layer 0)
        (active-layer 0)
        (selected-layers-array (car (ammoos-image-get-selected-layers image)))
        (num-selected-layers (vector-length selected-layers-array))
        )

    (if (= num-selected-layers 1)
        (begin
            (ammoos-context-push)
            (ammoos-context-set-defaults)
            (ammoos-image-undo-group-start image)

            (if (= (car (ammoos-drawable-has-alpha first-layer)) FALSE)
                (ammoos-layer-add-alpha first-layer)
            )

            (if (= (car (ammoos-selection-is-empty image)) TRUE)
                (ammoos-image-select-item image CHANNEL-OP-REPLACE first-layer)
            )

            (set! active-selection (car (ammoos-selection-save image)))
            (ammoos-image-set-selected-layers image (make-vector 1 first-layer))

            (set! selection-bounds (ammoos-selection-bounds image))
            (set! select-offset-x (cadr selection-bounds))
            (set! select-offset-y (caddr selection-bounds))
            (set! select-width (- (cadr (cddr selection-bounds)) select-offset-x))
            (set! select-height (- (caddr (cddr selection-bounds)) select-offset-y))

            (if (= separate-layer TRUE)
                (begin
                  (set! lava-layer (car (ammoos-layer-new image
                                                        "Lava Layer"
                                                        select-width
                                                        select-height
                                                        type
                                                        100
                                                        LAYER-MODE-NORMAL-LEGACY)))

                  (ammoos-image-insert-layer image lava-layer 0 -1)
                  (ammoos-layer-set-offsets lava-layer select-offset-x select-offset-y)
                  (ammoos-selection-none image)
                  (ammoos-drawable-edit-clear lava-layer)

                  (ammoos-image-select-item image CHANNEL-OP-REPLACE active-selection)
                  (ammoos-image-set-selected-layers image (make-vector 1 lava-layer))
                )
            )

            (set! selected-layers-array (car (ammoos-image-get-selected-layers image)))
            (set! num-selected-layers (vector-length selected-layers-array))
            (set! active-layer (vector-ref selected-layers-array (- num-selected-layers 1)))

            (if (= current-grad FALSE)
                (ammoos-context-set-gradient gradient)
            )

            (let* ((width  (cadddr (ammoos-drawable-mask-intersect active-layer)))
                   (height (caddr (cddr (ammoos-drawable-mask-intersect active-layer)))))
              (ammoos-drawable-merge-new-filter active-layer "gegl:noise-solid" 0 LAYER-MODE-REPLACE 1.0 "tileable" FALSE "turbulent" TRUE "seed" seed
                                                                                                       "detail" 2 "x-size" 2.0 "y-size" 2.0
                                                                                                       "width" width "height" height)
            )
            (ammoos-drawable-merge-new-filter active-layer "gegl:cubism" 0 LAYER-MODE-REPLACE 1.0 "tile-size" tile_size "tile-saturation" 2.5 "bg-color" '(0 0 0))
            (ammoos-drawable-merge-new-filter active-layer "gegl:oilify" 0 LAYER-MODE-REPLACE 1.0 "mask-radius" (max 1 (/ mask_size 2)) "use-inten" FALSE)
            (ammoos-drawable-merge-new-filter active-layer "gegl:edge" 0 LAYER-MODE-REPLACE 1.0 "amount" 2.0 "border-behavior" "none" "algorithm" "sobel")
            (ammoos-drawable-merge-new-filter active-layer "gegl:gaussian-blur" 0 LAYER-MODE-REPLACE 1.0 "std-dev-x" 0.64 "std-dev-y" 0.64 "filter" "auto")
            (plug-in-gradmap #:run-mode RUN-NONINTERACTIVE #:image image #:drawables selected-layers-array)

            (if (= keep-selection FALSE)
                (ammoos-selection-none image)
            )

            (ammoos-image-set-selected-layers image (make-vector 1 first-layer))
            (ammoos-image-remove-channel image active-selection)

            (ammoos-image-undo-group-end image)
            (ammoos-context-pop)

            (ammoos-displays-flush)
        )
    ; else
        (ammoos-message _"Lava works with exactly one selected layer")
    )
  )
)

(script-fu-register-filter "script-fu-lava"
  _"_Lava..."
  _"Fill the current selection with lava"
  "Adrian Likins <adrian@ammoos.org>"
  "Adrian Likins"
  "10/12/97"
  "RGB* GRAY*"
  SF-ONE-OR-MORE-DRAWABLE
  SF-ADJUSTMENT _"Seed"           '(10 1 30000 1 10 0 1)
  SF-ADJUSTMENT _"Size"           '(10 0 100 1 10 0 1)
  SF-ADJUSTMENT _"Roughness"      '(7 3 50 1 10 0 0)
  SF-GRADIENT   _"Gradient"       "Incandescent"
  SF-TOGGLE     _"Keep selection" TRUE
  SF-TOGGLE     _"Separate layer" TRUE
  SF-TOGGLE     _"Use current gradient" FALSE
)

(script-fu-menu-register "script-fu-lava"
                         "<Image>/Filters/Render")
