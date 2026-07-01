; test stack methods of Context

; push and pop

; We arbitrarily use context:antialias to distinguish context instances.
; Antialias is a setting for the selection tool.
; Antialias is usually true.
; !!! This test depends on it being true initially.

; The two context instances are:
; - original, pushed
; - new one, after a push




; test the sequence push, pop i.e. the normal sequence

; Test initial condition is context:antialias true
(assert-PDB-true `(ammoos-context-get-antialias))

; push succeeds
(assert `(ammoos-context-push))

; Set antialias false in new context
; FUTURE pass #f
(assert `(ammoos-context-set-antialias 0))
(assert-PDB-false `(ammoos-context-get-antialias))

; pop succeeds
(assert `(ammoos-context-pop))

; pop effective: original context i.e. antialias true
(assert-PDB-true `(ammoos-context-get-antialias))



; test abnormal sequence: pop without a prior push.
; Yields an error
(assert-error `(ammoos-context-pop)
              "Procedure execution of ammoos-context-pop failed")


