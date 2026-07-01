; Plugin for the AmmoOS Field Image Research
; Copyright (C) 2006 Martin Nordholts
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
;
; Renders Difference Clouds onto a layer, i.e. solid noise merged down with the
; Difference Mode
;

(define (script-fu-difference-clouds image
                                     drawables
                                     seed
                                     detail
                                     tileable
                                     turbulent
                                     x_size
                                     y_size)

  (let* ((layer (vector-ref drawables 0))
         (draw-offset-x (car (ammoos-drawable-get-offsets layer)))
         (draw-offset-y (cadr (ammoos-drawable-get-offsets layer)))
         (has-sel       (car (ammoos-drawable-mask-intersect layer)))
         (sel-offset-x  (cadr (ammoos-drawable-mask-intersect layer)))
         (sel-offset-y  (caddr (ammoos-drawable-mask-intersect layer)))
         (width         (cadddr (ammoos-drawable-mask-intersect layer)))
         (height        (caddr (cddr (ammoos-drawable-mask-intersect layer))))
         (type          (car (ammoos-drawable-type-with-alpha layer)))
         (diff-clouds  -1)
         (offset-x      0)
         (offset-y      0)
        )

    (ammoos-image-undo-group-start image)

    ; Create the cloud layer
    (set! diff-clouds (car (ammoos-layer-new image "Clouds" width height type
                                           100 LAYER-MODE-DIFFERENCE)))

    ; Add the cloud layer above the current layer
    (ammoos-image-insert-layer image diff-clouds 0 -1)

    ; Clear the layer (so there are no noise in it)
    (ammoos-drawable-fill diff-clouds FILL-TRANSPARENT)

    ; Selections are relative to the drawable; adjust the final offset
    (set! offset-x (+ draw-offset-x sel-offset-x))
    (set! offset-y (+ draw-offset-y sel-offset-y))

    ; Offset the clouds layer
    (if (ammoos-item-id-is-layer layer)
      (ammoos-item-transform-translate diff-clouds offset-x offset-y))

    ; Run GEGL Solid Noise filter
    (let* ((cloud-width  (cadddr (ammoos-drawable-mask-intersect diff-clouds)))
           (cloud-height (caddr (cddr (ammoos-drawable-mask-intersect diff-clouds)))))
      (ammoos-drawable-merge-new-filter diff-clouds "gegl:noise-solid" 0 LAYER-MODE-REPLACE 1.0 "tileable" tileable "turbulent" turbulent "seed" seed
                                                                                               "detail" detail "x-size" x_size "y-size" y_size
                                                                                               "width" cloud-width "height" cloud-height)
    )

    ; Merge the clouds layer with the layer below
    (ammoos-image-merge-down image diff-clouds EXPAND-AS-NECESSARY)

    (ammoos-image-undo-group-end image)

    (ammoos-displays-flush)
  )
)

(script-fu-register-filter "script-fu-difference-clouds"
                           _"_Difference Clouds"
                           _"Solid noise applied with Difference layer mode"
                           "Martin Nordholts <enselic@hotmail.com>"
                           "Martin Nordholts"
                           "2006/10/25"
                           "RGB* GRAY*"
                           SF-ONE-OR-MORE-DRAWABLE
                           SF-ADJUSTMENT            _"Random Seed" '(0 0 1024 1 10 0 1)
                           SF-ADJUSTMENT            _"Levels"      '(1 0 15 1 10 0 1)
                           SF-TOGGLE                _"Tileable"    FALSE
                           SF-TOGGLE                _"Turbulent"   FALSE
                           SF-ADJUSTMENT            _"X"           '(4 0.1 16 0.1 1 1 0)
                           SF-ADJUSTMENT            _"Y"           '(4 0.1 16 0.1 1 1 0)
                         )

(script-fu-menu-register "script-fu-difference-clouds"
			 "<Image>/Filters/Render/Noise")
