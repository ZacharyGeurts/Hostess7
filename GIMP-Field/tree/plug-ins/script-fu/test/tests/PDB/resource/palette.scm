; Test methods of palette subclass of Resource class

; !!! See also resource.scm

; !!! Testing depends on a fresh install of AmmoOS Image.
; A prior testing failure may leave palettees in AmmoOS Image.
; The existing palette may have the same name as hard coded in tests.
; In future, will be possible to create new palette with same name as existing.


(script-fu-use-v3)

; setup, not assert
; but tests the -new method
(define testNewPalette (ammoos-palette-new "testNewPalette"))




(test! "attributes of new palette")

; ammoos-palette-get-background deprecated => ammoos-context-get-background
; ditto foreground

; new palette has given name
; !!! Fails if not a fresh install, then name is like "testNewPalette #2"
(assert `(string=?
            (ammoos-resource-get-name ,testNewPalette)
            "testNewPalette"))

; new palette has zero colors
(assert `(= (ammoos-palette-get-color-count ,testNewPalette)
            0))

; new palette has empty colormap
; v2 returns (0 #())
; v3 returns #()
(assert `(= (vector-length (ammoos-palette-get-colors ,testNewPalette))
            0))

(test! "new palette has zero columns")
; procedure returns just the column count
(assert `(= (ammoos-palette-get-columns ,testNewPalette)
            0))

; new palette is-editable
; method on Resource class
(assert `(ammoos-resource-is-editable ,testNewPalette))

; can set new palette in context
; Despite having empty colormap
; returns void
(assert `(ammoos-context-set-palette ,testNewPalette))




(test! "attributes of existing palette named Bears")

; setup
(define testBearsPalette (ammoos-palette-get-by-name "Bears"))


; Max size palette is 256

; Bears palette has 256 colors
(assert `(= (ammoos-palette-get-color-count ,testBearsPalette)
            256))

; Bears palette colormap array is size 256 vector of 3-tuple lists
; v2 get_colors returns (256 #((8 8 8) ... ))
; v3            returns #((8 8 8) ... )
(assert `(= (vector-length (ammoos-palette-get-colors ,testBearsPalette))
            256))

; Bears palette has zero column count
; The procedure returns a count, and not the columns
(assert `(= (ammoos-palette-get-columns ,testBearsPalette)
            0))

; system palette is not editable
; returns #f
(assert `(not (ammoos-resource-is-editable ,testBearsPalette)))


;              setting attributes of existing palette

; Can not change column count on system palette
(assert-error `(ammoos-palette-set-columns ,testBearsPalette 1)
              "Procedure execution of ammoos-palette-set-columns failed")


;              add entry to full system palette

; error to add entry to palette which is non-editable and has full colormap
(assert-error `(ammoos-palette-add-entry ,testBearsPalette "fooEntryName" "red")
                "Procedure execution of ammoos-palette-add-entry failed ")



 ;             setting attributes of new palette

; succeeds
(assert `(ammoos-palette-set-columns ,testNewPalette 1))

; effective
(assert `(= (ammoos-palette-get-columns ,testNewPalette)
            1))


(test! "adding color entry to new palette")

; add first entry returns index 0
; v2 result is wrapped (0)
(assert `(= (ammoos-palette-add-entry ,testNewPalette "fooEntryName" "red")
            0))

; was effective: color is as given when entry created
; v3 returns (255 0 0)
; renamed ammoos-palette-entry-get-color=>ammoos-palette-get-entry-color
(assert `(equal? (ammoos-palette-get-entry-color ,testNewPalette 0)
                  (list 255 0 0 255)))  ; red
(display (ammoos-palette-get-entry-color testNewPalette 0))

; was effective on name
(assert `(string=? (ammoos-palette-get-entry-name ,testNewPalette 0)
                  "fooEntryName"))



(test! "delete colormap entry")

; succeeds
; FIXME: the name seems backward, could be entry-delete
; returns void
(assert `(ammoos-palette-delete-entry  ,testNewPalette 0))
; effective, color count is back to 0
(assert `(= (ammoos-palette-get-color-count ,testNewPalette)
            0))


;               adding color "entry" to new palette which is full


; TODO locked palette?  See issue about locking palette?





(test! "delete palette")

; can delete a new palette
(assert `(ammoos-resource-delete ,testNewPalette))

; delete was effective
; ID is now invalid
(assert `(not (ammoos-resource-id-is-palette ,testNewPalette)))

; delete was effective
; not findable by name anymore
; If the name DOES exist (because not started fresh) yields "substring out of bounds"
; Formerly returned error, now returns NULL i.e. -1
;(assert-error `(ammoos-palette-get-by-name "testNewPalette")
;              "Procedure execution of ammoos-palette-get-by-name failed on invalid input arguments: Palette 'testNewPalette' not found")
(assert `(= (ammoos-palette-get-by-name "testNewPalette")
            -1))



; see context.scm




;                   test deprecated methods

; These should give warnings in Gimp Error Console.
; Now they are methods on Context, not Palette.

;(ammoos-palettes-set-palette testBearsPalette)

;(ammoos-palette-swap-colors)
;(ammoos-palette-set-foreground "pink")
;(ammoos-palette-set-background "purple")


(script-fu-use-v2)









