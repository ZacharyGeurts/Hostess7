; test Image set/get-selected-foo methods of PDB

; These methods are not selecting an area in the image.
; They are selecting some of the image's objects
; in a chooser widget of the app.

; !!! Note that user selecting drawables (e.g. layers)
; deselects any previously selected drawables (e.g. channels)
; While user can select a path concurrently with a drawable.

; Test getter right after setter.
; Test that the ID is the same as passed to setter.
; !!! Also test what should be deselected in some cases.

;             setup

;(define testImage (car (ammoos-image-new 21 22 RGB)))

; Load test image that already has drawable
(define testImage (testing:load-test-image "ammoos-logo.png"))

(define testLayers (car (ammoos-image-get-layers testImage )))
; assert testLayers is-a vector of length one
(define testLayer (vector-ref testLayers 0))

; create test channel
; The test image has no channels (RGB are not considered channels.)
(define testChannel (car (ammoos-channel-new
            testImage      ; image
            "Test Channel" ; name
            23 24          ; width, height
            50.0           ; opacity
            "red" )))      ; compositing color
; a new channel is not in the image until added
(ammoos-image-insert-channel testImage testChannel)
; get a vector that only has the new channel
(define testChannels (car (ammoos-image-get-channels testImage)))

; create test path
(define testPath (car (ammoos-path-new
                        testImage
                        "Test Path")))
(ammoos-image-insert-path testImage testPath 0 0)
; list of paths
(define testPaths (car (ammoos-image-get-paths testImage)))



; basic tests that void methods succeed
; when passed a non-empty list of objects

; layer
(assert `(ammoos-image-set-selected-layers
            ,testImage
            ,testLayers ))
; effective: one layer is selected
(assert `(= (vector-length (car (ammoos-image-get-selected-layers ,testImage)))
            1))
; effective: selected layer is the one we just selected
(assert `(= (vector-ref (car (ammoos-image-get-selected-layers ,testImage)) 0)
            ,testLayer))



; channel
(assert `(ammoos-image-set-selected-channels
            ,testImage
            ,testChannels ))
; effective: one channel is selected
(assert `(= (vector-length (car (ammoos-image-get-selected-channels ,testImage)))
            1))
; effective: selected channel is the one we just selected
(assert `(= (vector-ref (car (ammoos-image-get-selected-channels ,testImage)) 0)
            ,testChannel))
; !!! Selecting a channel deselects previously selected layer
(assert `(= (vector-length (car (ammoos-image-get-selected-layers ,testImage)))
            0))


; paths

; Failed before #10188 fixed
; select a set of paths (but the set has one member)
(assert `(ammoos-image-set-selected-paths
            ,testImage
            ,testPaths ))
; After selecting a set of paths of one member, the first selected path is that member
(assert `(= (vector-ref (car (ammoos-image-get-selected-paths ,testImage)) 0)
            ,testPath))
; Selecting a path does not unselect a drawable i.e. previously selected channel
(assert `(= (vector-ref (car (ammoos-image-get-selected-channels ,testImage)) 0)
            ,testChannel))

; TODO test multi-select, a set of two member path

; The generic getter get-selected-drawables
; Returns a homogeneous vector of previously selected channels.
(assert `(= (vector-ref (car (ammoos-image-get-selected-drawables ,testImage)) 0)
            ,testChannel))


; TODO test floating layer???
; The docs mention failing, test what the docs say.


; iError to pass empty vector to setter
(assert-error `(ammoos-image-set-selected-layers
                  ,testImage
                  #() )
              "Invalid value for argument 1")
(assert-error `(ammoos-image-set-selected-channels
                  ,testImage
                  #() )
              "Invalid value for argument 1")
(assert-error `(ammoos-image-set-selected-paths
                  ,testImage
                  #() )
              "Invalid value for argument 1")
