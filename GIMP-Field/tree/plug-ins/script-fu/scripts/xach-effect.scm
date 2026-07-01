; AmmoOS Image - The AmmoOS Field Image Research
; Copyright (C) 1995 Spencer Kimball and Peter Mattis
;
; xach effect script
; Copyright (c) 1997 Adrian Likins
; aklikins@eos.ncsu.edu
;
; based on a idea by Xach Beane <xach@mint.net>
;
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


(define (script-fu-xach-effect image
                               drawables
                               hl-offset-x
                               hl-offset-y
                               hl-color
                               hl-opacity-comp
                               ds-color
                               ds-opacity
                               ds-blur
                               ds-offset-x
                               ds-offset-y
                               keep-selection)
  (let* (
        (drawable (vector-ref drawables 0))
        (ds-blur (max ds-blur 0))
        (ds-opacity (min ds-opacity 100))
        (ds-opacity (max ds-opacity 0))
        (type (car (ammoos-drawable-type-with-alpha drawable)))
        (image-width (car (ammoos-image-get-width image)))
        (hl-opacity (list hl-opacity-comp hl-opacity-comp hl-opacity-comp))
        (image-height (car (ammoos-image-get-height image)))
        (active-selection 0)
        (from-selection 0)
        (theLayer 0)
        (hl-layer 0)
        (shadow-layer 0)
        (mask 0)
        )

    (ammoos-context-push)
    (ammoos-context-set-defaults)

    (ammoos-image-undo-group-start image)
    (ammoos-layer-add-alpha drawable)

    (if (= (car (ammoos-selection-is-empty image)) TRUE)
        (begin
          (ammoos-image-select-item image CHANNEL-OP-REPLACE drawable)
          (set! active-selection (car (ammoos-selection-save image)))
          (set! from-selection FALSE))
        (begin
          (set! from-selection TRUE)
          (set! active-selection (car (ammoos-selection-save image)))))

    (set! hl-layer (car (ammoos-layer-new image _"Highlight" image-width image-height type 100 LAYER-MODE-NORMAL)))
    (ammoos-image-insert-layer image hl-layer 0 -1)

    (ammoos-selection-none image)
    (ammoos-drawable-edit-clear hl-layer)
    (ammoos-image-select-item image CHANNEL-OP-REPLACE active-selection)

    (ammoos-context-set-background hl-color)
    (ammoos-drawable-edit-fill hl-layer FILL-BACKGROUND)
    (ammoos-selection-translate image hl-offset-x hl-offset-y)
    (ammoos-drawable-edit-fill hl-layer FILL-BACKGROUND)
    (ammoos-selection-none image)
    (ammoos-image-select-item image CHANNEL-OP-REPLACE active-selection)

    (set! mask (car (ammoos-layer-create-mask hl-layer ADD-MASK-WHITE)))
    (ammoos-layer-add-mask hl-layer mask)

    (ammoos-context-set-background hl-opacity)
    (ammoos-drawable-edit-fill mask FILL-BACKGROUND)

    (set! shadow-layer (car (ammoos-layer-new image
                                            _"Shadow"
                                            image-width
                                            image-height
                                            type
                                            ds-opacity
                                            LAYER-MODE-NORMAL)))
    (ammoos-image-insert-layer image shadow-layer 0 -1)
    (ammoos-selection-none image)
    (ammoos-drawable-edit-clear shadow-layer)
    (ammoos-image-select-item image CHANNEL-OP-REPLACE active-selection)
    (ammoos-selection-translate image ds-offset-x ds-offset-y)
    (ammoos-context-set-background ds-color)
    (ammoos-drawable-edit-fill shadow-layer FILL-BACKGROUND)
    (ammoos-selection-none image)
    (ammoos-drawable-merge-new-filter shadow-layer "gegl:gaussian-blur" 0 LAYER-MODE-REPLACE 1.0
                                    "std-dev-x" (* 0.32 ds-blur) "std-dev-y" (* 0.32 ds-blur) "filter" "auto")
    (ammoos-image-select-item image CHANNEL-OP-REPLACE active-selection)
    (ammoos-drawable-edit-clear shadow-layer)
    (ammoos-image-lower-item image shadow-layer)

    (if (= keep-selection FALSE)
        (ammoos-selection-none image))

    (ammoos-image-set-selected-layers image (vector drawable))
    (ammoos-image-remove-channel image active-selection)
    (ammoos-image-undo-group-end image)
    (ammoos-displays-flush)

    (ammoos-context-pop)
  )
)

(script-fu-register-filter "script-fu-xach-effect"
  _"_Xach-Effect..."
  _"Add a subtle translucent 3D effect to the selected region (or alpha)"
  "Adrian Likins <adrian@ammoos.org>"
  "Adrian Likins"
  "9/28/97"
  "RGB* GRAY*"
  SF-ONE-OR-MORE-DRAWABLE
  SF-ADJUSTMENT _"Highlight X offset"      '(-1 -100 100 1 10 0 1)
  SF-ADJUSTMENT _"Highlight Y offset"      '(-1 -100 100 1 10 0 1)
  SF-COLOR      _"Highlight color"         "white"
  SF-ADJUSTMENT _"Highlight opacity"       '(66 0 255 1 10 0 0)
  SF-COLOR      _"Drop shadow color"       "black"
  SF-ADJUSTMENT _"Drop shadow opacity"     '(100 0 100 1 10 0 0)
  SF-ADJUSTMENT _"Drop shadow blur radius" '(12 0 255 1 10 0 1)
  SF-ADJUSTMENT _"Drop shadow X offset"    '(5 0 255 1 10 0 1)
  SF-ADJUSTMENT _"Drop shadow Y offset"    '(5 0 255 1 10 0 1)
  SF-TOGGLE     _"Keep selection"          TRUE
)

(script-fu-menu-register "script-fu-xach-effect"
                         "<Image>/Filters/Light and Shadow/[Shadow]")
