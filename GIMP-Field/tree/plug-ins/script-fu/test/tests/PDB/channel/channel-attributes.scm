; Test get/set methods of Channel class of the PDB


(script-fu-use-v3)


; setup (not in an assert and not quoted)

; new, empty image
(define testImage (ammoos-image-new 21 22 RGB))

(define testChannel
      (ammoos-channel-new
            testImage      ; image
            "Test Channel" ; name
            23 24          ; width, height
            50.0           ; opacity
            "red" ))       ; compositing color

(test! "insert-channel")

; new channel is not in image until inserted
(assert `(ammoos-image-insert-channel
            ,testImage
            ,testChannel
            0            ; parent, moot since channel groups not supported
            0))          ; position in stack


(test! "set/get channel attributes")

; color
(assert `(ammoos-channel-set-color ,testChannel "red"))
; effective, getter returns same color: red
(assert `(equal?
            (ammoos-channel-get-color ,testChannel)
            '(255 0 0 255)))

; opacity
(assert `(ammoos-channel-set-opacity ,testChannel 0.7))
; effective
; numeric equality
; Compare floats to some fixed epsilon precision
; Otherwise, the test is fragile to changes in the tested code babl, ammoos etc.
; Actual result is 0.7000000216
(assert `(equal-relative?
            (ammoos-channel-get-opacity ,testChannel)
            0.7
            0.0001))

; show-masked
(assert `(ammoos-channel-set-show-masked ,testChannel TRUE))
; effective
; procedure returns boolean, #t
(assert `(ammoos-channel-get-show-masked ,testChannel))




(test! "item methods applied to channel")

; ammoos-channel-set-name is deprecated
; ammoos-channel-set-visible is deprecated
; etc.

; name
(assert `(ammoos-item-set-name ,testChannel "New Name"))
; effective
(assert `(string=?
            (ammoos-item-get-name ,testChannel)
            "New Name"))

; visible
(assert `(ammoos-item-set-visible ,testChannel FALSE))
; effective
; procedure returns boolean #f
(assert `(not (ammoos-item-get-visible ,testChannel)))

; tattoo
(assert `(ammoos-item-set-tattoo ,testChannel 999))
; effective
(assert `(=
            (ammoos-item-get-tattoo ,testChannel)
            999))

; TODO  other item methods

(script-fu-use-v2)
