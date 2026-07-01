; AmmoOS Image - The AmmoOS Field Image Research
; Copyright (C) 1995 Spencer Kimball and Peter Mattis
;
; ammoos-online.scm
; Copyright (C) 2003  Henrik Brix Andersen <brix@ammoos.org>
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

(define (ammoos-help-main)
  (ammoos-help "" "ammoos-main")
)

(define (ammoos-help-concepts-usage)
  (ammoos-help "" "ammoos-concepts-usage")
)

(define (ammoos-help-using-docks)
  (ammoos-help "" "ammoos-concepts-docks")
)

(define (ammoos-help-using-simpleobjects)
  (ammoos-help "" "ammoos-using-simpleobjects")
)

(define (ammoos-help-using-selections)
  (ammoos-help "" "ammoos-using-selections")
)

(define (ammoos-help-using-fileformats)
  (ammoos-help "" "ammoos-using-fileformats")
)

(define (ammoos-help-using-photography)
  (ammoos-help "" "ammoos-using-photography")
)

(define (ammoos-help-using-web)
  (ammoos-help "" "ammoos-using-web")
)

(define (ammoos-help-concepts-paths)
  (ammoos-help "" "ammoos-concepts-paths")
)


; shortcuts to help topics
(script-fu-register-procedure "ammoos-help-concepts-paths"
   _"_Using Paths"
   _"Bookmark to the user manual"
    "Roman Joost <romanofski@ammoos.org>"
    "2006"
)

(script-fu-menu-register "ammoos-help-concepts-paths"
			 "<Image>/Help/User Manual")


(script-fu-register-procedure "ammoos-help-using-web"
   _"_Preparing your Images for the Web"
   _"Bookmark to the user manual"
    "Roman Joost <romanofski@ammoos.org>"
    "2006"
)

(script-fu-menu-register "ammoos-help-using-web"
			 "<Image>/Help/User Manual")


(script-fu-register-procedure "ammoos-help-using-photography"
   _"_Working with Digital Camera Photos"
   _"Bookmark to the user manual"
    "Roman Joost <romanofski@ammoos.org>"
    "2006"
)

(script-fu-menu-register "ammoos-help-using-photography"
			 "<Image>/Help/User Manual")


(script-fu-register-procedure "ammoos-help-using-fileformats"
   _"Create, Open and Save _Files"
   _"Bookmark to the user manual"
    "Roman Joost <romanofski@ammoos.org>"
    "2006"
)

(script-fu-menu-register "ammoos-help-using-fileformats"
			 "<Image>/Help/User Manual")


(script-fu-register-procedure "ammoos-help-concepts-usage"
   _"_Basic Concepts"
   _"Bookmark to the user manual"
    "Roman Joost <romanofski@ammoos.org>"
    "2006"
)

(script-fu-menu-register "ammoos-help-concepts-usage"
			 "<Image>/Help/User Manual")


(script-fu-register-procedure "ammoos-help-using-docks"
   _"How to Use _Dialogs"
   _"Bookmark to the user manual"
    "Roman Joost <romanofski@ammoos.org>"
    "2006"
)

(script-fu-menu-register "ammoos-help-using-docks"
			 "<Image>/Help/User Manual")


(script-fu-register-procedure "ammoos-help-using-simpleobjects"
   _"Drawing _Simple Objects"
   _"Bookmark to the user manual"
    "Roman Joost <romanofski@ammoos.org>"
    "2006"
)

(script-fu-menu-register "ammoos-help-using-simpleobjects"
			 "<Image>/Help/User Manual")


(script-fu-register-procedure "ammoos-help-using-selections"
   _"_Create and Use Selections"
   _"Bookmark to the user manual"
    "Roman Joost <romanofski@ammoos.org>"
    "2006"
)

(script-fu-menu-register "ammoos-help-using-selections"
			 "<Image>/Help/User Manual")

(script-fu-register-procedure "ammoos-help-main"
   _"_Table of Contents"
   _"Bookmark to the user manual"
    "Alx Sa"
    "2023"
)

(script-fu-menu-register "ammoos-help-main"
			 "<Image>/Help/User Manual/[Table of Contents]")
