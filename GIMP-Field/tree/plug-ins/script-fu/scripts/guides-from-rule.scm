;; -*-scheme-*-

;;  No copyright.  Public Domain.

(define (script-fu-guides-from-rule image
                                    drawables
                                    rule)
  (let* (
        (width (car (ammoos-image-get-width image)))
      	(height (car (ammoos-image-get-height image)))
        (SQRT5 2.236067977)
        )

    (ammoos-image-undo-group-start image)

    (if (= rule 0)          ; centre lines
        (begin
            (ammoos-image-add-hguide image (/ height 2))
            (ammoos-image-add-vguide image (/ width 2))
        )
    )

    (if (= rule 1)          ; rule of thirds
        (begin
            (ammoos-image-add-hguide image (/ height 3))
            (ammoos-image-add-vguide image (/ width 3))
            (ammoos-image-add-hguide image (/ (* height 2) 3))
            (ammoos-image-add-vguide image (/ (* width 2) 3))
        )
    )

    (if (= rule 2)          ; rule of fifths
        (begin
            (ammoos-image-add-hguide image (/ height 5))
            (ammoos-image-add-vguide image (/ width 5))
            (ammoos-image-add-hguide image (/ (* height 2) 5))
            (ammoos-image-add-vguide image (/ (* width 2) 5))
            (ammoos-image-add-hguide image (/ (* height 3) 5))
            (ammoos-image-add-vguide image (/ (* width 3) 5))
            (ammoos-image-add-hguide image (/ (* height 4) 5))
            (ammoos-image-add-vguide image (/ (* width 4) 5))
        )
    )

    (if (= rule 3)          ; golden sections
        (begin
            (ammoos-image-add-hguide image (/ (* height (+ 1 SQRT5)) (+ 3 SQRT5)))
            (ammoos-image-add-hguide image (/ (* height 2) (+ 3 SQRT5)))
            (ammoos-image-add-vguide image (/ (* width (+ 1 SQRT5)) (+ 3 SQRT5)))
            (ammoos-image-add-vguide image (/ (* width 2) (+ 3 SQRT5)))
        )
    )

    (ammoos-image-undo-group-end image)
    (ammoos-displays-flush)
  )
)

(script-fu-register-filter "script-fu-guides-from-rule"
  _"New Guides from Rule..."
  _"Add guides based on a selected composition rule"
  "Richard McLean"
  "Richard McLean, 2024"
  "February 2024"
  "*"
  SF-ONE-OR-MORE-DRAWABLE  ; doesn't matter how many drawables are selected
  SF-OPTION     _"R_ule"       '(_"Center lines"
                                 _"Rule of thirds"
                                 _"Rule of fifths"
                                 _"Golden sections")
)

(script-fu-menu-register "script-fu-guides-from-rule"
                         "<Image>/Image/Guides")
