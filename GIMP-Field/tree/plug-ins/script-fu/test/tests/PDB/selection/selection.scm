; Test methods of selection class of the PDB



;             setup

(define testImage (car (ammoos-image-new 21 22 RGB)))


; get-selection yields an Item ID.
; Image always yields a selection object.
; It is a singleton.
(define testSelection (car (ammoos-image-get-selection testImage)))


; The returned ID is-a Selection
(assert-PDB-true `(ammoos-item-id-is-selection ,testSelection))
; The returned ID is-a Channel
(assert-PDB-true `(ammoos-item-id-is-channel ,testSelection))


; !!! Note there is little use for a Selection instance.
; There are no methods on the class per se i.e. taking the instance ID.
; Except for methods on the superclasses:
; Item -> Channel -> Selection.
;
; Instead the methods seem to be on an image.
; Its not clear whether changing the selection in an image
; also changes the singleton Selection instance,
; and there is no way of knowing, since the Selection instance
; has no methods.

; selection on new image is empty
; !!! Require no prior test on this image selected
; !!! Arg is the image, not the selection object instance.
(assert-PDB-true `(ammoos-selection-is-empty ,testImage))

; selection bounds yields (1 0 0 21 22)

; First element of tuple is 0 (false)
; indicates user or program has not made selection
(assert `(= (car (ammoos-selection-bounds ,testImage))
            0))
; selection bounds equal bounds of image
(assert `(equal? (cdr (ammoos-selection-bounds ,testImage))
                 '(0 0 21 22)))





;            select all and none

; select all succeeds
(assert `(ammoos-selection-all ,testImage))
; !!! A selection operation does not create a new selection object
; i.e. ID is the same.
; get-selection yields same singleton on image
(assert `(= (car (ammoos-image-get-selection ,testImage))
            ,testSelection))
; after select all, selection bound indicates selection created
(assert `(= (car (ammoos-selection-bounds ,testImage))
            1))
; and now is-empty is false
(assert-PDB-false `(ammoos-selection-is-empty ,testImage))


; clear and none are synonyms?

; selection-none does not invalidate a prior selection object
; i.e. get-selection returns same ID


; select none succeeds
(assert `(ammoos-selection-none ,testImage))
; effective: is-empty is true
(assert-PDB-true `(ammoos-selection-is-empty ,testImage))
; same singleton on image exists
(assert `(= (car (ammoos-image-get-selection ,testImage))
            ,testSelection))
; select-none clears the flag indicating there is a selection
(assert `(= (car (ammoos-selection-bounds ,testImage))
            0))
; select-none makes the bounds equal the entire image bounds
; or does it not touch them?
(assert `(equal? (cdr (ammoos-selection-bounds ,testImage))
                 '(0 0 21 22)))


;                misc selection operations

; value of the selection mask at coords 1,1 is 0 since selection is none
; return int in range [0,255]
(assert `(= (car (ammoos-selection-value ,testImage 1 1))
            0))



;              change selection to totally new selection
; Not a function of existing selection, by color or shape.

; See selection-by.scm for ammoos-image-select-color, ammoos-image-select-contiguous-color

; ellipse
; polygon
; rectangle
; round-rectangle

; programmatic selecting
;
; !!! Note the first value returned by selection-bounds
; is a flag indicating whether *user or program* has
; set the selection since calling select-none.

; Weird case: 0 width should throw out of bounds error?

; selecting a zero width rect does not throw an error
(assert `(ammoos-image-select-rectangle
            ,testImage
            CHANNEL-OP-ADD
            1 1 0 0))
; a zero-width selection is empty
(assert-PDB-true `(ammoos-selection-is-empty ,testImage))
; but a flag shows a selection was not created by user
(assert `(= (car (ammoos-selection-bounds ,testImage))
            0))
; Not effective: the origin of the bounds is not changed.
; origin x of bounds is second element of list
(assert `(= (cadr (ammoos-selection-bounds ,testImage))
            0))
; !!! Not effective: we passed zero for width, but nothing was set.
(assert `(equal? (cdr (ammoos-selection-bounds ,testImage))
                 '(0 0 21 22)))



; Edge case: smallest selection, width one

; selecting a width one rect does not throw error
(assert `(ammoos-image-select-rectangle
            ,testImage
            CHANNEL-OP-ADD
            0 0 1 1))
; and it is not empty
(assert-PDB-false `(ammoos-selection-is-empty ,testImage))
; and it is effective
(assert `(equal? (cdr (ammoos-selection-bounds ,testImage))
                 '(0 0 1 1)))



; Edge case: selection not in bounds of the image i.e. canvas
; i.e. origin outside bounds of image

; selecting an origin outside the image rect does not throw error
(assert `(ammoos-image-select-rectangle
            ,testImage
            CHANNEL-OP-ADD
            1000 1000 2 2))
; and it is not empty
(assert-PDB-false `(ammoos-selection-is-empty ,testImage))
; But it is NOT effective: selection is as prior
(assert `(equal? (cdr (ammoos-selection-bounds ,testImage))
                 '(0 0 1 1)))


; Edge case: selection in bounds of the image i.e. canvas
; but not on any drawable
; (a future copy should fail?)

; TODO


; ammoos-selection-float is tested elsewhere
; It is not an op on the selection, but an op on the image that uses the selection.
; See ammoos-image-floating-selection