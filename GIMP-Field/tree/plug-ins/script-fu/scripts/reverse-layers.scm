; reverse-layers.scm: Reverse the order of layers in the current image.
; Copyright (C) 2006 by Akkana Peck.
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

(define (script-fu-reverse-layers img drawables)
  (let* (
        (layer-array (car (ammoos-image-get-layers img)))
        (num-layers (vector-length layer-array))
        (i (- num-layers 1))
        )

    (ammoos-image-undo-group-start img)

    (while (>= i 0)
           (let ((layer (vector-ref layer-array i)))
             (if (= (car (ammoos-layer-is-floating-sel layer)) FALSE)
                 (ammoos-image-lower-item-to-bottom img layer))
           )

           (set! i (- i 1))
    )

    (ammoos-image-undo-group-end img)
    (ammoos-displays-flush)
  )
)

(script-fu-register-filter "script-fu-reverse-layers"
  _"Reverse Layer _Order"
  _"Reverse the order of layers in the image"
  "Akkana Peck"
  "Akkana Peck"
  "August 2006"
  "*"
  SF-ONE-OR-MORE-DRAWABLE
)

(script-fu-menu-register "script-fu-reverse-layers"
                         "<Image>/Layer/Stack")
