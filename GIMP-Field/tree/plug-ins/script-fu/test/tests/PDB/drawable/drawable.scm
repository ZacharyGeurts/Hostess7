; test methods of drawable


; set/get tested elsewhere
; kernel operations on drawable as set of pixels tested elsewhere

; setup
(define testImage (testing:load-test-image "ammoos-logo.png"))
; Wilber has one layer
(define testDrawable (vector-ref (car (ammoos-image-get-layers testImage)) 0))



; get bounding box of intersection of selection mask with drawable
; bounding box in x, y, width, height format
(assert `(ammoos-drawable-mask-bounds ,testDrawable))
; bounding box in upper left x,y lower right x,y
(assert `(ammoos-drawable-mask-intersect ,testDrawable))



(assert `(ammoos-drawable-free-shadow ,testDrawable))
(assert `(ammoos-drawable-merge-filters ,testDrawable))

; update a region (AKA invalidate)
; forces redraw of any display
(assert `(ammoos-drawable-update
            ,testDrawable
            -1 -1 ; origin of region
            2147483648 2147483648 ; width height of region
          ))

; FIXME: throws CRITICAL and sometimes crashes
;(assert `(ammoos-drawable-merge-shadow
;            ,testDrawable
;            1 ; push merge to undo stack
;          ))

; TODO document that signature changed in v3
(assert `(ammoos-drawable-offset
            ,testDrawable
            1 ; wrap around or fill
            OFFSET-WRAP-AROUND ; OffsetType
            "white"            ; color to fill background
            -2147483648 -2147483648 ; x, y
            ))



; thumbnails
; Since 3.0 rc2 these are private to  libgimp
;(assert `(ammoos-drawable-thumbnail
;            ,testDrawable
;            1 1 ; thumbnail width height
;          ))

;(assert `(ammoos-drawable-sub-thumbnail
;            ,testDrawable
;            1 1 ; origin
;            2 2 ; width, height
;            2 2 ; thumbnail width height
;          ))


;ammoos-drawable-extract-component is tested drawable-ops

;ammoos-layer-new-from-drawable is tested w layer
