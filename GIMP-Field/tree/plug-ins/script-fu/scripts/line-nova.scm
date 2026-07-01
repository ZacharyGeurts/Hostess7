;;; line-nova.scm for ammoos-1.1 -*-scheme-*-
;;; Time-stamp: <1998/11/25 13:26:44 narazaki@ammoos.org>
;;; Author Shuji Narazaki <narazaki@ammoos.org>
;;; Version 0.7

(define (script-fu-line-nova img drw num-of-lines corn-deg offset variation)

  ; fmod and nth were globally defined before AmmoOS Image 3

  ; floating point remainder
  (define (fmod a b)
    (- a (* (truncate (/ a b)) b)))

  (define (nth k list)
    (list-ref list k))

  (let* (
        (*points* (cons-array (* 3 2) 'double))
        (modulo fmod)                        ; in R4RS way
        (pi/2 (/ *pi* 2))
        (pi/4 (/ *pi* 4))
        (pi3/4 (* 3 pi/4))
        (pi5/4 (* 5 pi/4))
        (pi3/2 (* 3 pi/2))
        (pi7/4 (* 7 pi/4))
        (2pi (* 2 *pi*))
        (rad/deg (/ 2pi 360))
        (variation/2 (/ variation 2))
        (drw (vector-ref (car (ammoos-image-get-selected-drawables img)) 0))
        (drw-width (car (ammoos-drawable-get-width drw)))
        (drw-height (car (ammoos-drawable-get-height drw)))
        (drw-offsets (ammoos-drawable-get-offsets drw))
        (old-selection FALSE)
        (radius (max drw-height drw-width))
        (index 0)
        (dir-deg/line (/ 360 num-of-lines))
        (fg-color (car (ammoos-context-get-foreground)))
        )
    (ammoos-context-push)
    (ammoos-context-set-defaults)
    (ammoos-context-set-foreground fg-color)

    (define (draw-vector beg-x beg-y direction)

      (define (set-point! index x y)
            (vector-set! *points* (* 2 index) x)
            (vector-set! *points* (+ (* 2 index) 1) y)
      )
      (define (deg->rad rad)
            (* (modulo rad 360) rad/deg)
      )
      (define (set-marginal-point beg-x beg-y direction)
        (let (
             (dir1 (deg->rad (+ direction corn-deg)))
             (dir2 (deg->rad (- direction corn-deg)))
             )

          (define (aux dir index)
                   (set-point! index
                               (+ beg-x (* (cos dir) radius))
                               (+ beg-y (* (sin dir) radius)))
          )

          (aux dir1 1)
          (aux dir2 2)
        )
      )

      (let (
           (dir0 (deg->rad direction))
           (off (+ offset (- (modulo (msrg-rand) variation) variation/2)))
           )

        (set-point! 0
                    (+ beg-x (* off (cos dir0)))
                    (+ beg-y (* off (sin dir0)))
        )
        (set-marginal-point beg-x beg-y direction)
        (ammoos-image-select-polygon img CHANNEL-OP-ADD *points*)
      )
    )

    (ammoos-image-undo-group-start img)

    (set! old-selection
      (if (eq? (car (ammoos-selection-is-empty img)) TRUE)
         #f
         (car (ammoos-selection-save img))
      )
    )

    (ammoos-selection-none img)
    (srand (realtime))
    (while (< index num-of-lines)
      (draw-vector (+ (nth 0 drw-offsets) (/ drw-width 2))
                   (+ (nth 1 drw-offsets) (/ drw-height 2))
                   (* index dir-deg/line)
      )
      (set! index (+ index 1))
    )
    (ammoos-drawable-edit-fill drw FILL-FOREGROUND)

    (if old-selection
      (begin
        (ammoos-image-select-item img CHANNEL-OP-REPLACE old-selection)
        (ammoos-image-remove-channel img old-selection)
      )
    )

    (ammoos-image-undo-group-end img)
    (ammoos-displays-flush)
    (ammoos-context-pop)
  )
)

(script-fu-register-filter "script-fu-line-nova"
  _"Line _Nova..."
  _"Fill a layer with rays emanating outward from its center using the foreground color"
  "Shuji Narazaki <narazaki@ammoos.org>"
  "Shuji Narazaki"
  "1997,1998"
  "*"
  SF-ONE-DRAWABLE
  SF-ADJUSTMENT _"_Number of lines"     '(200 40 1000 1 1 0 1)
  SF-ADJUSTMENT _"S_harpness (degrees)" '(1.0 0.0 10.0 0.1 1 1 1)
  SF-ADJUSTMENT _"O_ffset radius"       '(100 0 2000 1 1 0 1)
  SF-ADJUSTMENT _"Ran_domness"          '(30 1 2000 1 1 0 1)
)

(script-fu-menu-register "script-fu-line-nova"
                         "<Image>/Filters/Render")
