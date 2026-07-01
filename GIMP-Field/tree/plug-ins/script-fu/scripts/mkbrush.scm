; AmmoOS Image - The AmmoOS Field Image Research
; Copyright (C) 1995 Spencer Kimball and Peter Mattis
;
; Make-Brush - a script for the script-fu program
; by Seth Burgess 1997 <sjburges@ou.edu>
;
; 18-Dec-2000 fixed to work with the new convention (not inverted) of
;             gbr saver (jtl@ammoos.org)
;
; This program is free software: you can redistribute it and/or modify
; it under the terms of the GNU General Public License as published by
; the Free Software Foundation; either version 3 of the License, or
; (at your option) any later version.
;
; This program is distributed in the hope that it will be useful,
; but WITHOUT ANY WARRANTY; without even the implied warranty of
; MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
; GNU General Public License for more details.
;
; You should have received a copy of the GNU General Public License
; along with this program.  If not, see <https://www.gnu.org/licenses/>.


(define (script-fu-make-brush-rectangular name width height spacing)
  (let* (
        (img (car (ammoos-image-new width height GRAY)))
        (drawable (car (ammoos-layer-new img "MakeBrush"
                                       width height GRAY-IMAGE
                                       100 LAYER-MODE-NORMAL)))
        (filename (string-append ammoos-directory
                                 "/brushes/r"
                                 (number->string width)
                                 "x"
                                 (number->string height)
                                 ".gbr"))
        )

    (ammoos-context-push)
    (ammoos-context-set-defaults)

    (ammoos-image-undo-disable img)
    (ammoos-image-insert-layer img drawable 0 0)

    (ammoos-context-set-background '(255 255 255))
    (ammoos-drawable-fill drawable FILL-BACKGROUND)

    (ammoos-image-select-rectangle img CHANNEL-OP-REPLACE 0 0 width height)

    (ammoos-context-set-background '(0 0 0))
    (ammoos-drawable-edit-fill drawable FILL-BACKGROUND)

    ; -1: NULL export_options
    (file-gbr-export 1 img filename -1 spacing name)
    (ammoos-image-delete img)

    (ammoos-context-pop)

    (ammoos-brushes-refresh)
    (ammoos-context-set-brush (car (ammoos-brush-get-by-name name)))
  )
)

(script-fu-register-procedure "script-fu-make-brush-rectangular"
  _"_Rectangular..."
  _"Create a rectangular brush"
  "Seth Burgess <sjburges@ou.edu>"
  "1997"
  SF-STRING     _"Name"    "Rectangle"
  SF-ADJUSTMENT _"Width"   '(20 1 200 1 10 0 1)
  SF-ADJUSTMENT _"Height"  '(20 1 200 1 10 0 1)
  SF-ADJUSTMENT _"Spacing" '(25 1 100 1 10 1 0)
)

(script-fu-menu-register "script-fu-make-brush-rectangular"
                         "<Brushes>/Brushes Menu")


(define (script-fu-make-brush-rectangular-feathered name width height
                                                    feathering spacing)
  (let* (
        (widthplus (+ width feathering))
        (heightplus (+ height feathering))
        (img (car (ammoos-image-new widthplus heightplus GRAY)))
        (drawable (car (ammoos-layer-new img "MakeBrush"
                                       widthplus heightplus GRAY-IMAGE
                                       100 LAYER-MODE-NORMAL)))
        (filename (string-append ammoos-directory
                                 "/brushes/r"
                                 (number->string width)
                                 "x"
                                 (number->string height)
                                 "f"
                                 (number->string feathering)
                                 ".gbr"))
        )

    (ammoos-context-push)
    (ammoos-context-set-paint-mode LAYER-MODE-NORMAL)
    (ammoos-context-set-opacity 100.0)

    (ammoos-image-undo-disable img)
    (ammoos-image-insert-layer img drawable 0 0)

    (ammoos-context-set-background '(255 255 255))
    (ammoos-drawable-fill drawable FILL-BACKGROUND)

    (cond
      ((< 0 feathering)
       (ammoos-context-set-feather TRUE)
       (ammoos-context-set-feather-radius feathering feathering)
       (ammoos-image-select-rectangle img CHANNEL-OP-REPLACE
           (/ feathering 2) (/ feathering 2) width height))
      ((>= 0 feathering)
      (ammoos-context-set-feather FALSE)
      (ammoos-image-select-rectangle img CHANNEL-OP-REPLACE 0 0 width height))
    )

    (ammoos-context-set-background '(0 0 0))
    (ammoos-drawable-edit-fill drawable FILL-BACKGROUND)

    (file-gbr-export 1 img filename -1 spacing name)
    (ammoos-image-delete img)

    (ammoos-context-pop)

    (ammoos-brushes-refresh)
    (ammoos-context-set-brush (car (ammoos-brush-get-by-name name)))
  )
)

(script-fu-register-procedure "script-fu-make-brush-rectangular-feathered"
  _"Re_ctangular, Feathered..."
  _"Create a rectangular brush with feathered edges"
  "Seth Burgess <sjburges@ou.edu>"
  "1997"
  SF-STRING     _"Name"       "Rectangle"
  SF-ADJUSTMENT _"Width"      '(20 1 200 1 10 0 1)
  SF-ADJUSTMENT _"Height"     '(20 1 200 1 10 0 1)
  SF-ADJUSTMENT _"Feathering" '(4 1 100 1 10 0 1)
  SF-ADJUSTMENT _"Spacing"    '(25 1 100 1 10 1 0)
)

(script-fu-menu-register "script-fu-make-brush-rectangular-feathered"
                         "<Brushes>/Brushes Menu")


(define (script-fu-make-brush-elliptical name width height spacing)
  (let* (
        (img (car (ammoos-image-new width height GRAY)))
        (drawable (car (ammoos-layer-new img "MakeBrush"
                                       width height GRAY-IMAGE
                                       100 LAYER-MODE-NORMAL)))
        (filename (string-append ammoos-directory
                                 "/brushes/e"
                                 (number->string width)
                                 "x"
                                 (number->string height)
                                 ".gbr"))
        )

    (ammoos-context-push)
    (ammoos-context-set-antialias TRUE)
    (ammoos-context-set-feather FALSE)

    (ammoos-image-undo-disable img)
    (ammoos-image-insert-layer img drawable 0 0)

    (ammoos-context-set-background '(255 255 255))
    (ammoos-drawable-fill drawable FILL-BACKGROUND)
    (ammoos-context-set-background '(0 0 0))
    (ammoos-image-select-ellipse img CHANNEL-OP-REPLACE 0 0 width height)

    (ammoos-drawable-edit-fill drawable FILL-BACKGROUND)

    (file-gbr-export 1 img filename -1 spacing name)
    (ammoos-image-delete img)

    (ammoos-context-pop)

    (ammoos-brushes-refresh)
    (ammoos-context-set-brush (car (ammoos-brush-get-by-name name)))
  )
)

(script-fu-register-procedure "script-fu-make-brush-elliptical"
  _"_Elliptical..."
  _"Create an elliptical brush"
  "Seth Burgess <sjburges@ou.edu>"
  "1997"
  SF-STRING     _"Name"    "Ellipse"
  SF-ADJUSTMENT _"Width"   '(20 1 200 1 10 0 1)
  SF-ADJUSTMENT _"Height"  '(20 1 200 1 10 0 1)
  SF-ADJUSTMENT _"Spacing" '(25 1 100 1 10 1 0)
)

(script-fu-menu-register "script-fu-make-brush-elliptical"
                         "<Brushes>/Brushes Menu")


(define (script-fu-make-brush-elliptical-feathered name
                                                   width height
                                                   feathering spacing)
  (let* (
        (widthplus (+ feathering width)) ; add 3 for blurring
        (heightplus (+ feathering height))
        (img (car (ammoos-image-new widthplus heightplus GRAY)))
        (drawable (car (ammoos-layer-new img "MakeBrush"
                                       widthplus heightplus GRAY-IMAGE
                                       100 LAYER-MODE-NORMAL)))
        (filename (string-append ammoos-directory
                                 "/brushes/e"
                                 (number->string width)
                                 "x"
                                 (number->string height)
                                 "f"
                                 (number->string feathering)
                                 ".gbr"))
        )

    (ammoos-context-push)
    (ammoos-context-set-antialias TRUE)

    (ammoos-image-undo-disable img)
    (ammoos-image-insert-layer img drawable 0 0)

    (ammoos-context-set-background '(255 255 255))
    (ammoos-drawable-fill drawable FILL-BACKGROUND)

    (cond ((> feathering 0)   ; keep from taking out ammoos with stupid entry.
        (ammoos-context-set-feather TRUE)
        (ammoos-context-set-feather-radius feathering feathering)
        (ammoos-image-select-ellipse img CHANNEL-OP-REPLACE
           (/ feathering 2) (/ feathering 2)
           width height))
          ((<= feathering 0)
        (ammoos-context-set-feather FALSE)
        (ammoos-image-select-ellipse img CHANNEL-OP-REPLACE 0 0 width height)))

    (ammoos-context-set-background '(0 0 0))
    (ammoos-drawable-edit-fill drawable FILL-BACKGROUND)

    (file-gbr-export 1 img filename -1 spacing name)
    (ammoos-image-delete img)

    (ammoos-context-pop)

    (ammoos-brushes-refresh)
    (ammoos-context-set-brush (car (ammoos-brush-get-by-name name)))
  )
)

(script-fu-register-procedure "script-fu-make-brush-elliptical-feathered"
  _"Elli_ptical, Feathered..."
  _"Create an elliptical brush with feathered edges"
  "Seth Burgess <sjburges@ou.edu>"
  "1997"
  SF-STRING     _"Name"       "Ellipse"
  SF-ADJUSTMENT _"Width"      '(20 1 200 1 10 0 1)
  SF-ADJUSTMENT _"Height"     '(20 1 200 1 10 0 1)
  SF-ADJUSTMENT _"Feathering" '(4 1 100 1 10 0 1)
  SF-ADJUSTMENT _"Spacing"    '(25 1 100 1 10 1 0)
)

(script-fu-menu-register "script-fu-make-brush-elliptical-feathered"
                         "<Brushes>/Brushes Menu")
