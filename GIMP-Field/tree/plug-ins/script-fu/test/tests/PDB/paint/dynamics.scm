; Test methods related to paint dynamics



; setup

; an image, drawable, and path
(define testImage (testing:load-test-image "ammoos-logo.png"))
(define testLayer (vector-ref (car (ammoos-image-get-layers testImage ))
                                  0))
(define testPath (car (ammoos-path-new testImage "Test Path")))
; must add to image
(ammoos-image-insert-path
                  testImage
                  testPath
                  0 0) ; parent=0 position=0
; Add stroke to path
; TODO enum still named "VECTORS" => PATH
(ammoos-path-stroke-new-from-points
            testPath
            PATH-STROKE-TYPE-BEZIER
            (vector 1 2 83 84 5 6 7 8 9 10 11 12) ; control points
            FALSE) ; not closed

; make test harder by using float precision
(ammoos-image-convert-precision testImage PRECISION-DOUBLE-NON-LINEAR)
; ensure testing is stroking with paint (versus line)
(ammoos-context-set-stroke-method STROKE-PAINT-METHOD)
; ensure testing is painting with paintbrush (versus pencil, airbrush, etc.)
(ammoos-context-set-paint-method "ammoos-paintbrush")
; make test harder by using a big, color brush
(ammoos-context-set-brush (car (ammoos-brush-get-by-name "Wilber")))




; methods of the ammoos module

; introspection: ammoos module returns list of names of dynamics
; second arg is a regex
; FORMERLY get-list
(assert `(list? (ammoos-dynamics-get-name-list "")))

; refresh: ammoos module will load newly installed dynamics
; method is void and should never fail.
(assert `(ammoos-dynamics-refresh))

; TODO install a new dynamic and test that refresh is effective






; context setting

; the dynamics setting defaults to true
; !!! test requires freshly installed AmmoOS Image OR no prior testing
(assert-PDB-true `(ammoos-context-are-dynamics-enabled))

; the dynamics-enabled setting can be set to false
; TODO #f instead of 0
(assert `(ammoos-context-enable-dynamics 0))
; setting to false was effective
(assert-PDB-false `(ammoos-context-are-dynamics-enabled))
; restore to enabled for further testing
(assert `(ammoos-context-enable-dynamics 1))


; the dynamics setting can be set to the name of a dynamics
(assert `(ammoos-context-set-dynamics-name "Tilt Angle"))
; setting was effective
; formerly context-[set,get]-dynamics
(assert `(string=? (car (ammoos-context-get-dynamics-name))
                   "Tilt Angle"))



;  TODO test all the dynamics seems to work

; Test that all dynamics seem to work:
;    set context to dynamics
;    stroke a drawable along a path with current brush and dynamics


(define dynamicsList (car (ammoos-dynamics-get-name-list "")))

(define (testDynamics dynamics)
    ; Test that every dynamics can be set on the context
    (ammoos-context-set-dynamics-name dynamics)

    (display dynamics)
    ; paint with paintbrush and dynamics, under the test harness
    (assert `(ammoos-drawable-edit-stroke-item ,testLayer ,testPath))
   )

; apply testDynamics to each dynamics kind.
; This is not a difficult test since the stroke is uniform w/r to dynamics.
; The stroke does not vary by e.g. pressure.
(for-each
  testDynamics
  dynamicsList)

;(ammoos-display-new testImage)
