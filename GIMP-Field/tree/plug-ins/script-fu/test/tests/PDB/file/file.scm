; Test ammoos-file-<foo> PDB procedures
;
; ammoos-file-load is tested elsewhere
; (ammoos-file-load RUN-NONINTERACTIVE (path-to-test-images "ammoos-logo.png")))

; ammoos-image-thumbnail is private to libgimp

; ammoos-<foo>-export is tested elsewhere


(script-fu-use-v3)


; setup

; This also tests ammoos-file-load
(define testImage (testing:load-test-image-basic-v3))

(assert `(ammoos-image-id-is-valid ,testImage))



(test! "get temp file name")

; this is a "file" method but name is not ammoos-file- ?

(define tempFilename (ammoos-temp-file "xyz"))

; The named file does not exist.
(assert `(not (file-exists? ,tempFilename)))

; The name is unique among repeated calls, but we don't test that.






(test! "load thumbnail of file")

; It is not clear whether this loads the file and creates a thumbnail,
; or finds a thumbnail stored separately, for the desktop.

; We don't do this, because the framework doesn't handle quoted lists.
; FIXME This fails with illegal function, but works in the SF Console
; (define (testThumbnail) (ammoos-file-load-thumbnail (path-to-test-images "ammoos-logo.png")))
; (assert `(list? ,testThumbnail))

; testThumbnail is list
(assert `(list? (ammoos-file-load-thumbnail (,path-to-test-images "ammoos-logo.png"))))

; first element is width, 128
; third element is 50k vector of bytes, RGB data




(test! "load layer from file")

; the image in the file becomes one layer in the image

; !!! This is rare: a PDB internal function that takes a run mode
(define testLayer (ammoos-file-load-layer
                     RUN-NONINTERACTIVE
                     testImage
                     (path-to-test-images "ammoos-logo.png")))

; testLayer is-a layer
(assert `(ammoos-item-id-is-layer ,testLayer))

; it is not insert into any image yet



(test! "load layers from file")

; All the layers in the image in the file
; become multiple layers in the image.

; Note testImage only has one layer.

(define testLayers (ammoos-file-load-layers
                     RUN-NONINTERACTIVE
                     testImage
                     (path-to-test-images "ammoos-logo.png")))

; testLayers is-a vector of one
(assert `(vector? ,testLayers))

; the one layer in the vector is-a layer
(assert `(ammoos-item-id-is-layer
            (vector-ref ,testLayers 0)))

; it is not insert into any image yet



(test! "create thumbnail for existing file")

; FIXME this fails for unknown reasons

; This file already has a thumbnail.
;;(assert `(ammoos-file-create-thumbnail
;;            ,testImage
;;            (path-to-test-images "ammoos-logo.png")))



(test! "create thumbnail for newly saved image")

; Thumbnails don't exist for newly created files unless you create them


(define testNewImage (ammoos-image-new 21 22 RGB))

(assert `(ammoos-file-save
            RUN-NONINTERACTIVE
            ,testNewImage
            "/tmp/testSaveNewImage.xcf"
            -1 )) ; NULL export options

; The file does not have a thumbnail yet???

; FIXME shouldn't this call succeed instead of error?
(assert-error `(ammoos-file-create-thumbnail
                  ,testNewImage
                  "/tmp/testSaveNewImage.xcf")
              "Procedure execution of ammoos-file-create-thumbnail failed")



(test! "file save")

; The image is not dirty, but saving under a different suffix
; does write the file.

(assert `(ammoos-file-save
            RUN-NONINTERACTIVE
            ,testImage
            "/tmp/testSaveImage.xcf"
            -1 )) ; NULL export options

; The file exists
(assert `(file-exists? "/tmp/testSaveImage.xcf"))


; TODO test ammoos-file-save on a non-dirty image
; does or does not write the file?


; Is error to omit a suffix indicating image format
(assert-error
     `(ammoos-file-save
            RUN-NONINTERACTIVE
            ,testImage
            "/tmp/testSaveImage"
            -1 ) ; NULL export options
      "Procedure execution of ammoos-file-save failed: Unknown file type")



; cleanup
; Delete image but not the created file.
(ammoos-image-delete testImage)




(script-fu-use-v2)