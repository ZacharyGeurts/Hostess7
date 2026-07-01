; test get/set attributes of drawable

; The test script uses v3 binding of return values
(script-fu-use-v3)


; setup

(define testImage (testing:load-test-image-basic-v3))
; Loaded "ammoos-logo.png" i.e. Wilber having one layer
(define testDrawable (vector-ref (ammoos-image-get-layers testImage) 0))




; a drawable is represented by an ID
; As an item, it is type Drawable
(assert `(ammoos-item-id-is-drawable ,testDrawable))




(test! "getters of Drawable")

; only testing getters that are not of the superclass Item

; bytes per pixel
(assert `(number? (ammoos-drawable-get-bpp ,testDrawable)))
; height and width are single numbers
(assert `(number? (ammoos-drawable-get-height ,testDrawable)))
(assert `(number? (ammoos-drawable-get-width ,testDrawable)))
; offset is list of two numbers
(assert `(list? (ammoos-drawable-get-offsets ,testDrawable)))

; since 3.0rc2 drawable-get-format is private to libgimp
; formats are strings encoded for babl
; (assert `(string? (ammoos-drawable-get-format ,testDrawable)))

; Since 3.0rc2, this is private to libgimp
;(assert `(string? (ammoos-drawable-get-thumbnail-format ,testDrawable)))


; the test drawable has transparency
; FUTURE: inconsistent naming, should be ammoos-drawable-get-alpha?
(assert `(ammoos-drawable-has-alpha ,testDrawable))

; the test drawable has image base type RGB
(assert `(ammoos-drawable-is-rgb ,testDrawable))
(assert `(not (ammoos-drawable-is-gray ,testDrawable)))
(assert `(not (ammoos-drawable-is-indexed ,testDrawable)))

; the test drawable has type RGBA
(assert `(= (ammoos-drawable-type ,testDrawable)
            RGBA-IMAGE))


; These are deprecated.
; Scripts should use superclass ammoos-item-get.
; Which are tested elsewhere
;(assert `(ammoos-drawable-get-image ,testDrawable))
;(assert `(ammoos-drawable-get-name ,testDrawable))
;(assert `(ammoos-drawable-get-tattoo ,testDrawable))
; the test drawable is visible
;(assert-PDB-true `(ammoos-drawable-get-visible ,testDrawable))




; TODO setters


(script-fu-use-v2)
