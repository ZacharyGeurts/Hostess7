; Test operation methods of Channel class of the PDB

; These methods are operations between or from channels

; Also, ordering operations, miscellaneous operations


; setup
; Load test image that already has drawable
(define testImage (testing:load-test-image "ammoos-logo.png"))

; ammoos-channel-ops-duplicate is deprecated, use ammoos-image-duplicate
; ammoos-channel-ops-offset deprecated, use ammoos-drawable-offset



; tests

; create a channel from one of the component channels

; Not an explicit test case?
(define testChannel
  (car
     (ammoos-channel-new-from-component
          testImage
          CHANNEL-RED
          "Channel copied from red")))


; insert in image
(assert `(ammoos-image-insert-channel
            ,testImage
            ,testChannel
            0            ; parent, moot since channel groups not supported
            0))

; !!! new channel copied from another is NOT visible
(assert `(= (car (ammoos-item-get-visible ,testChannel))
             FALSE))



; create a channel by copying another non-component channel

(define testChannel2 (car (ammoos-channel-copy testChannel)))

; insert in image
(assert `(ammoos-image-insert-channel
            ,testImage
            ,testChannel2
            0            ; parent, moot since channel groups not supported
            0))

; The name of the copy is name of the first with " copy" appended
(assert `(string=?
            (car (ammoos-item-get-name ,testChannel2))
            "Channel copied from red copy"))

; effective: image now has two non-component channels
(assert `(= (vector-length (car (ammoos-image-get-channels ,testImage)))
            2))




; combining two replaces the first, but does not delete one

; void function does not throw
(assert `(ammoos-channel-combine-masks
            ,testChannel ,testChannel2
            CHANNEL-OP-INTERSECT
            -10 -10))   ; offset

; effective: image still has two non-component channels
(assert `(= (vector-length (car (ammoos-image-get-channels ,testImage)))
            2))

; effective: second channel still valid
(assert-PDB-true `(ammoos-item-id-is-channel ,testChannel2))

; TODO test the first channel is altered?



(test! "channel stack ordering operations")

; The first created channel is at the bottom of the two
; The second created channel is initially at top
(assert `(= (car (ammoos-image-get-item-position ,testImage ,testChannel))
            1))

; A channel with one above it can be raised
(assert `(ammoos-image-raise-item ,testImage ,testChannel))

; A channel at the top cannot be raised higher
; A channel which is below a channel whose position is locked cannot be raised?
; image-raise-channel is deprecated, use ammoos-image-raise-item
(assert-error `(ammoos-image-raise-item ,testImage ,testChannel)
              "Procedure execution of ammoos-image-raise-item failed: Channel cannot be raised higher.")

; Can be lowered
; ammoos-image-lower-channel is deprecated
(assert `(ammoos-image-lower-item ,testImage ,testChannel))

; TODO test effectiveness by checking position now


; freeze/thaw
(assert `(ammoos-image-freeze-channels ,testImage))
(assert `(ammoos-image-thaw-channels ,testImage))

; for debugging individual test file:
; (ammoos-display-new testImage)











