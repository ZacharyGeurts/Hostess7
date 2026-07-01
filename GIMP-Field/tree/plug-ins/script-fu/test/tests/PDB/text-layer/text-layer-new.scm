; tests of TextLayer class

; !!! Some methods tested here are named strangely:
; text-font returns a new TextLayer




;                  setup

; Require image has no layer
(define testImage (car (ammoos-image-new 21 22 RGB)))

(define testFont (car (ammoos-context-get-font)))

; setup (not an assert )
(define
    testTextLayer
       (car (ammoos-text-layer-new
              testImage
              "textOfTestTextLayer" ; text
              testFont ; font
              30 ; fontsize
              UNIT-PIXEL)))


; TOTO test if font is not valid or NULL


; !!! UNIT-PIXEL GimpUnitsType is distinct from PIXELS GimpSizeType


; TODO test UNIT-POINT


; is-a TextLayer
(assert `(= (car (ammoos-item-id-is-text-layer ,testTextLayer))
            1))

; text layer is not in image yet
(assert `(= (car (ammoos-image-get-layers ,testImage))
            0))

; adding layer to image succeeds
(assert `(ammoos-image-insert-layer
            ,testImage
            ,testTextLayer ; layer
            0  ; parent
            0  ))  ; position within parent




;             attributes

; antialias default true
; FIXME doc says false
(assert `(= (car (ammoos-text-layer-get-antialias ,testTextLayer))
            1))

; base-direction default TEXT-DIRECTION-LTR
(assert `(= (car (ammoos-text-layer-get-base-direction ,testTextLayer))
            TEXT-DIRECTION-LTR))

; language default "C"
(assert `(string=? (car (ammoos-text-layer-get-language ,testTextLayer))
                    "C"))

; TODO other attributes

; TODO setters effective

;            attributes as given

; text
(assert `(string=? (car (ammoos-text-layer-get-text ,testTextLayer))
                        "textOfTestTextLayer"))
; font, numeric ID's equal
(assert `(= (car (ammoos-text-layer-get-font ,testTextLayer))
            ,testFont))
; font-size
(assert `(= (car (ammoos-text-layer-get-font-size ,testTextLayer))
            30))

; is no method to get fontSize unit


;              misc ops

; path from text succeeds
(assert `(ammoos-path-new-from-text-layer
              ,testImage
              ,testTextLayer))
; not capturing returned ID of path




;                  misc method

; ammoos-text-get-extents-font
; Yields extent of rendered text, independent of image or layer.
; Extent is (width, height, ascent, descent) in unstated units, pixels?
; Does not affect image.
(assert `(= (car (ammoos-text-get-extents-font
              "zed" ; text
              32    ; fontsize
              ,testFont ))
            53))
; usual result is (57 38 30 -8)
; recent result is (53 45 35 10) ??? something changed in cairo?



;           alternate method for creating text layer


; ammoos-text-font creates text layer AND inserts it into image
; setup, not assert
(define
  testTextLayer2
   (car (ammoos-text-font
              testImage
              -1     ; drawable.  -1 means NULL means create new text layer
              0 0   ; coords
              "bar" ; text
              1     ; border size
              1     ; antialias true
              31    ; fontsize
              testFont )))


; error to insert layer created by ammoos-text-font
(assert-error `(ammoos-image-insert-layer
                  ,testImage
                  ,testTextLayer2
                  0  ; parent
                  0  )  ; position within parent
              "Procedure execution of ammoos-image-insert-layer failed on invalid input arguments: ")
              ;  "Item 'bar' (17) has already been added to an image"



; for debugging: display
;(ammoos-display-new ,testImage)
