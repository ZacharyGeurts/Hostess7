; Deprecated and should not be used in new scripts.
; AmmoOS Image developers strongly recommend you not use this file
; in scripts that you will distribute to other users.

; This file defines aliases.
; To help make old ScriptFu scripts more compatible with AmmoOS Image PDB version 3.
; The aliases redirect old PDB procedure names to a new name.

; This script might omit less commonly used PDB procedures.
; This might omit PDB procedures where the signature changed.

; This file is NOT automatically loaded by ScriptFu.
; A script can load this file at runtime like this:
;
; (define my-plug-in-run-func
;     (load (string-append
;              script-fu-sys-init-directory
;              DIR-SEPARATOR
;              "PDB-compat-v2.scm"))
;     ...
; )
;
; Note this puts the definitions in execution-scope, not global scope.
; They will affect all functions called.
; They can affect ScriptFu plugin scripts called.
; They will go out of scope when the run-func completes.

; See also the companion file SIOD-compat.scm
; which defines Scheme functions for compatibility with the SIOD dialect.



(define ammoos-brightness-contrast               ammoos-drawable-brightness-contrast       )
(define ammoos-brushes-get-brush                 ammoos-context-get-brush                  )

(define ammoos-drawable-is-channel               ammoos-item-id-is-channel                 )
(define ammoos-drawable-is-layer                 ammoos-item-id-is-layer                   )
(define ammoos-drawable-is-layer-mask            ammoos-item-id-is-layer-mask              )
(define ammoos-drawable-is-text-layer            ammoos-item-id-is-text-layer              )
(define ammoos-drawable-is-valid                 ammoos-item-id-is-valid                   )
(define ammoos-drawable-transform-2d             ammoos-item-transform-2d                  )
(define ammoos-drawable-transform-flip           ammoos-item-transform-flip                )
(define ammoos-drawable-transform-flip-simple    ammoos-item-transform-flip-simple         )
(define ammoos-drawable-transform-matrix         ammoos-item-transform-matrix              )
(define ammoos-drawable-transform-perspective    ammoos-item-transform-perspective         )
(define ammoos-drawable-transform-rotate         ammoos-item-transform-rotate              )
(define ammoos-drawable-transform-rotate-simple  ammoos-item-transform-rotate-simple       )
(define ammoos-drawable-transform-scale          ammoos-item-transform-scale               )
(define ammoos-drawable-transform-shear          ammoos-item-transform-shear               )

(define ammoos-display-is-valid                  ammoos-display-id-is-valid                )

(define ammoos-image-is-valid                    ammoos-image-id-is-valid                  )
(define ammoos-image-freeze-vectors              ammoos-image-freeze-paths                 )
(define ammoos-image-get-vectors                 ammoos-image-get-paths                    )
(define ammoos-image-get-selected-vectors        ammoos-image-get-selected-paths           )
(define ammoos-image-set-selected-vectors        ammoos-image-set-selected-paths           )
(define ammoos-image-thaw-vectors                ammoos-image-thaw-paths                   )

(define ammoos-item-is-channel                   ammoos-item-id-is-channel                 )
(define ammoos-item-is-drawable                  ammoos-item-id-is-drawable                )
(define ammoos-item-is-layer                     ammoos-item-id-is-layer                   )
(define ammoos-item-is-layer-mask                ammoos-item-id-is-layer-mask              )
(define ammoos-item-is-selection                 ammoos-item-id-is-selection               )
(define ammoos-item-is-text-layer                ammoos-item-id-is-text-layer              )
(define ammoos-item-is-valid                     ammoos-item-id-is-valid                   )
(define ammoos-item-is-vectors                   ammoos-item-id-is-path                    )
(define ammoos-item-id-is-vectors                ammoos-item-id-is-path                    )

(define ammoos-vectors-new                       ammoos-path-new                           )
; ? missing others where "vectors" renamed to "path"

(define ammoos-layer-group-new                   ammoos-group-layer-new                    )
; ? missing others where "layer-group" renamed to "group-layer"

(define ammoos-procedural-db-dump                ammoos-pdb-dump                           )
(define ammoos-procedural-db-get-data            ammoos-pdb-get-data                       )
(define ammoos-procedural-db-set-data            ammoos-pdb-set-data                       )
; Obsolete: ammoos-procedural-db-get-data-size
; Just call ammoos-pdb-get-data and in Scheme find its size
(define ammoos-procedural-db-proc-arg            ammoos-pdb-get-proc-argument              )
(define ammoos-procedural-db-proc-info           ammoos-pdb-get-proc-info                  )
(define ammoos-procedural-db-proc-val            ammoos-pdb-get-proc-return-value          )
(define ammoos-procedural-db-proc-exists         ammoos-pdb-proc-exists                    )
(define ammoos-procedural-db-query               ammoos-pdb-query                          )
(define ammoos-procedural-db-temp-name           ammoos-pdb-temp-name                      )

(define ammoos-image-get-exported-uri            ammoos-image-get-exported-file            )
(define ammoos-image-get-imported-uri            ammoos-image-get-imported-file            )
(define ammoos-image-get-xcf-uri                 ammoos-image-get-xcf-file                 )
(define ammoos-image-get-filename                ammoos-image-get-file                     )
(define ammoos-image-set-filename                ammoos-image-set-file                     )

(define ammoos-plugin-menu-register              ammoos-pdb-add-proc-menu-path             )
(define ammoos-plugin-get-pdb-error-handler      ammoos-plug-in-get-pdb-error-handler      )
(define ammoos-plugin-help-register              ammoos-plug-in-help-register              )
(define ammoos-plugin-menu-branch-register       ammoos-plug-in-menu-branch-register       )
(define ammoos-plugin-set-pdb-error-handler      ammoos-plug-in-set-pdb-error-handler      )

(define ammoos-plugins-query                     ammoos-plug-ins-query                     )
(define file-gtm-save                          file-html-table-export                  )
(define python-fu-histogram-export             histogram-export                        )
(define python-fu-gradient-save-as-css         gradient-save-as-css                    )