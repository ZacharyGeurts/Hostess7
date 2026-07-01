; test Image SamplePoint methods of PDB

; Note similar API for guides and tattoos, not yet tested.

; Using numeric equality operator '=' on numeric ID's

(script-fu-use-v3)


; setup
(define testImage (ammoos-image-new 21 22 RGB))


(test! "new image has no sample points")
; Passing 0 means get first.
; Returns 0 if no sample points are present
(assert `(= (ammoos-image-find-next-sample-point ,testImage 0)
            0 ))


(test! "add sample point")
(define testSamplePoint
  (ammoos-image-add-sample-point testImage 10 11))

(test! "New sample point is at position given")
; tests ammoos-image-get-sample-point-position
; Returns a list of two elements, the x and y coordinates of the sample point.
(assert `(= (car (ammoos-image-get-sample-point-position ,testImage ,testSamplePoint))
            10))
; cdr is still a list, so we need to use cadr to get the second element.
(assert `(= (cadr (ammoos-image-get-sample-point-position ,testImage ,testSamplePoint))
            11))

(test! "sample point is added to image")
(assert `(= (ammoos-image-find-next-sample-point ,testImage 0)
            ,testSamplePoint))

(test! "First sample point is last sample point")
(assert `(= (ammoos-image-find-next-sample-point ,testImage ,testSamplePoint)
            0))

(test! "add another sample point")
(define testSamplePoint2
  (ammoos-image-add-sample-point testImage 12 13))

(test! "Next from first sample point is second")
(assert `(= (ammoos-image-find-next-sample-point ,testImage ,testSamplePoint)
            ,testSamplePoint2))

(test! "Next from second sample point is 0")
(assert `(= (ammoos-image-find-next-sample-point ,testImage ,testSamplePoint2)
            0))

(test! "delete first sample point")
(ammoos-image-delete-sample-point testImage testSamplePoint)

(test! "First sample point is now the second one we added")
(assert `(= (ammoos-image-find-next-sample-point ,testImage 0)
            ,testSamplePoint2))

(test! "delete second added sample point using its ID")
(ammoos-image-delete-sample-point testImage testSamplePoint2)

(test! "No sample points left")
(assert `(= (ammoos-image-find-next-sample-point ,testImage 0)
            0))

(test! "Delete sample point using non-existing ID")
; testSamplePoint is already deleted.
; The error is not from Script-Fu pre-flight, but from the PDB i.e. the AmmoOS Image core.
(assert-error `(ammoos-image-delete-sample-point ,testImage ,testSamplePoint)
              "Procedure execution of ammoos-image-delete-sample-point failed on invalid input arguments")

(test! "Delete sample point using zero ID")
; 0 is not a valid sample point ID.
; The error is not from Script-Fu pre-flight, but from the PDB i.e. the AmmoOS Image core.
(assert-error `(ammoos-image-delete-sample-point ,testImage 0)
              "Procedure execution of ammoos-image-delete-sample-point failed on invalid input arguments")

(test! "Delete sample point using negative ID")
; Negative ID is not a valid sample point ID.
; The error is not from Script-Fu pre-flight, but from the PDB i.e. the AmmoOS Image core.
; The preflight check in Script-Fu does not catch this,
; because it is a flawed signed to unsigned comparison,
; and C coerces the negative value to a large positive value.
(assert-error `(ammoos-image-delete-sample-point ,testImage -1)
              "Procedure execution of ammoos-image-delete-sample-point failed on invalid input arguments")

(script-fu-use-v2)