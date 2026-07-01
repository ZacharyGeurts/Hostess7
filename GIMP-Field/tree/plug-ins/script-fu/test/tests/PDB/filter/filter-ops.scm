; Test operations DrawableFilter

; Test sequences of layer methods that use a filter.

; Some operations are on a layer, passing a filter
;    merge() is permanent or destructive
;    append() is non-destructive NDE
;
; configure() is variadic after two args, and optional

; Algebra.  This is a high level view of tested sequences.
;
;   layer.merge(filter.new)     apply filter destructive using defaults
;   layer.append(filter.new)    creates NDE filter using defaults
;   filter.new, filter.configure, layer.[merge, append](filter)
;                                using specialized settings, not defaults
;
;   NOT TESTED: filter.new, layer.append, filter.configure, filter.update
;         conceptually, a script can tweak a filter after it is appended?
;
;   filter.new, layer.merge, filter.id_is_valid returns #f
;         can't tweak a filter after it is merged (it no longer exists)
;
;   channel.merge(filter.new)    applies a filter destructively on non-layer drawable
;   channel.append(filter.new)   not allowed
;
;   filter.new, layer.append, layer.append   can append the same filter twice???



(script-fu-use-v3)

; setup

(define testImage (testing:load-test-image-basic-v3))
(define testLayer (vector-ref (ammoos-image-get-layers testImage) 0))
(define testFilter (ammoos-drawable-filter-new
                      testLayer
                      "gegl:ripple"
                      ""    ; user given "effect name", not used
                    ))
(define testFilter2 (ammoos-drawable-filter-new
                      testLayer
                      "gegl:spherize"
                      "" ))
(define testFilter3 (ammoos-drawable-filter-new
                      testLayer
                      "gegl:engrave"
                      "" ))
; filter on channel
(define testChannel (ammoos-channel-new
            testImage      ; image
            "Test Channel" ; name
            23 24          ; width, height
            50.0           ; opacity
            "red" ))      ; compositing color
(assert `(ammoos-image-insert-channel
            ,testImage
            ,testChannel
            0            ; parent, moot since channel groups not supported
            0))          ; position in stack
(define testFilter4 (ammoos-drawable-filter-new
                      testChannel
                      "gegl:ripple"
                      "" ))
(define testFilter5 (ammoos-drawable-filter-new
                      testChannel
                      "gegl:shift"
                      "" ))


(test! "configure filter variadically")
; This is not a PDB procedure, but a ScriptFu procedure.
; It only changes the config for libgimp copy;
; the config is not sent to core until merge or append.
(ammoos-drawable-filter-configure testFilter
      LAYER-MODE-REPLACE   ; blend mode
      1.0                  ; opacity
      "amplitude"   1000.0 ; key/value pair specific to filter
      )

; TODO test effective

; TODO apparently, configure MUST be done, else assert on value_array != NULL
; at merge or append time.
; FIXME: all the setting of the filter should default.


(test! "configure filter improperly")

; blend mode and opacity are required args
(assert-error `(ammoos-drawable-filter-configure ,testFilter)
               "Drawable Filter marshaller was called with missing arguments.")
; keys must be paired with value
; key is valid, but missing the value
(assert-error `(ammoos-drawable-filter-configure ,testFilter
                  LAYER-MODE-REPLACE 1.0
                  "amplitude")
               "Drawable Filter marshaller was called with an even number of arguments.")
; keys must be as defined by the filter
(assert-error `(ammoos-drawable-filter-configure ,testFilter
                  LAYER-MODE-REPLACE 1.0
                  "foo"  1.0)
               "Invalid argument name: foo")






; !!! merge and append are not PDB procedures, but ScriptFu procedures
; The debug stmts are not the same as for PDB calls.


(test! "merge filter")

(ammoos-drawable-merge-filter testLayer testFilter)
; Merging makes the effect permanent and
; the filter no longer appears as a settable effect on the layer.

; The filter no longer exists.
; The id is not valid
(assert `(not (ammoos-drawable-filter-id-is-valid ,testFilter)))

; But the filter can be configured????  This is non-sensical.
; Maybe libgimp's copy of the filter still exists but core's copy does not.
; FIXME: libgimp should not configure a filter that doesn't exist in core?
(ammoos-drawable-filter-configure testFilter
      LAYER-MODE-REPLACE   ; blend mode
      1.0)




(test! "append filter")

; appending stacks the filter on the layer non-destructive
; It appears in the list of "filter effects" from the "fx" icon

; FIXME seems to fail with assertion value_array != NULL
; if not configured
(ammoos-drawable-filter-configure testFilter2
      LAYER-MODE-REPLACE   ; blend mode
      1.0)

(ammoos-drawable-append-filter testLayer testFilter2)

; the filter continues to exist
(assert `(ammoos-drawable-filter-id-is-valid ,testFilter2))




(test! "append unconfigured filter")

; a DrawableFilter has sane defaults for all settings: configure is optional.
(ammoos-drawable-append-filter testLayer testFilter3)

; the filter continues to exist
(assert `(ammoos-drawable-filter-id-is-valid ,testFilter3))




(test! "append same filter twice")
; FIXME: this throws no errors but doesn't seem to have any effect
;(ammoos-drawable-append-filter testLayer testFilter2)




; The filter can be configured differently, then updated.
; This is not something a plugin would ordinarily do:
; a plugin usually configures (or not) before appending,
; and leave any further tweaking to the user.
; But one can conceive a "god" script that tweaks many NDE filters.

(test! "update filter")
; update is a PDB procedure
; ammoos-drawable-filter-update
; Annotations say "It should not be used."
; so we don't test it.




(test! "merge filter on channel")
(ammoos-drawable-merge-filter testChannel testFilter4)
; TODO use a filter that we can see the result is correct???

(test! "cannot append NDE filter on channel")
; FIXME this does not throw error but does nothing?
; use filter5 since filter4 no longer exists
(ammoos-drawable-append-filter testChannel testFilter5)



(test! "optional display result images")
;(ammoos-display-new testImage)
;(ammoos-displays-flush)

; The result should be one image, with ripple applied destructively,
; and with the background layer having two NDE effects: spherize and engrave NDE.
; The image should look like it was rippled then spherized then engraved
; Delete the spherize and engrave to see the rippled image.
; The custom channel should have the ripple effect?

(script-fu-use-v2)