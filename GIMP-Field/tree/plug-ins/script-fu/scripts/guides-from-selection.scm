;; -*-scheme-*-

(define (script-fu-guides-from-selection image drawables)
  (let* (
        (boundaries (ammoos-selection-bounds image))
        ;; non-empty INT32 TRUE if there is a selection
        (selection (car boundaries))
        (x1 (cadr boundaries))
        (y1 (caddr boundaries))
        (x2 (cadr (cddr boundaries)))
        (y2 (caddr (cddr boundaries)))
        )

    ;; need to check for a selection or we get guides right at edges of the image
    (if (= selection TRUE)
      (begin
        (ammoos-image-undo-group-start image)

        (ammoos-image-add-vguide image x1)
        (ammoos-image-add-hguide image y1)
        (ammoos-image-add-vguide image x2)
        (ammoos-image-add-hguide image y2)

        (ammoos-image-undo-group-end image)
        (ammoos-displays-flush)
      )
    )
  )
)

(script-fu-register-filter "script-fu-guides-from-selection"
  _"New Guides from _Selection"
  _"Create four guides around the bounding box of the current selection"
  "Alan Horkan"
  "Alan Horkan, 2004.  Public Domain."
  "2004-08-13"
  "*"
  SF-ONE-OR-MORE-DRAWABLE  ; doesn't matter how many drawables are selected
)

(script-fu-menu-register "script-fu-guides-from-selection"
                         "<Image>/Image/Guides")
