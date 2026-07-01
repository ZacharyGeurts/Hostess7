; test refresh methods

; make the app read resources from configuration files

; methods of the app
; the app manages collections of resources
; app can refresh and list the resources.

; A collection is named by the plural of the singular element,
; i.e. brushes is a collection of brush.




; Deprecations:
; ammoos-palette-refresh
; ammoos-brushes-list => ammoos-brushes-get-list etc.
; ammoos-parasite-list => ammoos-get-parasite-list



(script-fu-use-v3)

(test! "refresh resources")

; always succeeds
; Returns #t
(assert `(ammoos-brushes-refresh))
(assert `(ammoos-dynamics-refresh))
(assert `(ammoos-fonts-refresh))
(assert `(ammoos-gradients-refresh))
(assert `(ammoos-palettes-refresh))
(assert `(ammoos-patterns-refresh))


(test!  "list resources")

; always succeeds
; Takes an optional regex string.
; Returns a vector of object ID's.
; !!! The name says its a list, but its an array
(assert `(vector? (ammoos-brushes-get-list "")))
(assert `(vector? (ammoos-fonts-get-list "")))
(assert `(vector? (ammoos-gradients-get-list "")))
(assert `(vector? (ammoos-palettes-get-list "")))
(assert `(vector? (ammoos-patterns-get-list "")))


;            listing app's collection of things not resources
; But taking a regex

; Returns list of names, not a vector of object ID's
(assert `(list? (ammoos-dynamics-get-name-list "")))
(assert `(list? (ammoos-buffers-get-name-list "")))


;           listing app's other collections not resources
; Not taking a regex

; FIXME the naming does not follow the pattern, should be plural parasites
; Not: (ammoos-parasites-get-list "")
(assert `(list? (ammoos-get-parasite-list)))

; the app, images, vectors, drawables, items
; can all have parasites.
; Tested elsewhere.

(test! "get images")

; ammoos-get-images does not follow the pattern:
; it doesn't take a regex
; and it returns a vector of image objects #()
(assert `(vector? (ammoos-get-images)))


(script-fu-use-v2)