;; -*-scheme-*-

;; Alan Horkan 2004.  No copyright.  Public Domain.

(define (script-fu-guide-new-percent image
                                     drawables
                                     direction
                                     position)
  (let* (
        (width (car (ammoos-image-get-width image)))
      	(height (car (ammoos-image-get-height image)))
        )

    (if (= direction 0)
      	(set! position (/ (* height position) 100))
	      (set! position (/ (* width position) 100))
    )

    (if (= direction 0)
	      ;; convert position to pixel
	      (if (<= position height) (ammoos-image-add-hguide image position))
	      (if (<= position width) (ammoos-image-add-vguide image position))
    )

    (ammoos-displays-flush)
  )
)

(script-fu-register-filter "script-fu-guide-new-percent"
  _"New Guide (by _Percent)..."
  _"Add a guide at the position specified as a percentage of the image size"
  "Alan Horkan"
  "Alan Horkan, 2004"
  "April 2004"
  "*"
  SF-ONE-OR-MORE-DRAWABLE  ; doesn't matter how many drawables are selected
  SF-OPTION     _"_Direction"       '(_"Horizontal"
                                     _"Vertical")
  SF-ADJUSTMENT _"_Position (in %)" '(50 0 100 1 10 2 1)
)

(script-fu-menu-register "script-fu-guide-new-percent"
                         "<Image>/Image/Guides")
