; test methods of PDB as a database


(script-fu-use-v3)


(test! "dump the PDB to a file")
(assert `(ammoos-pdb-dump "/tmp/pdb.dump"))


(test! "store named array of bytes into db")
(assert `(ammoos-pdb-set-data "myData" #(1 2 3)))

; effective: the named data can be retrieved
(assert `(equal? (ammoos-pdb-get-data "myData")
                 #(1 2 3)))


(test! "procedure existence predicate")
(assert `(ammoos-pdb-proc-exists "ammoos-pdb-proc-exists"))


(test! "query the pdb by a set of regex strings")
; returns list of names

; empty regex matches anything, returns all procedure names in pdb
; Test exists more than 900 procedures
(assert `(> (length (ammoos-pdb-query
                         "" ; name
                         "" "" ; blurb help
                         "" "" ; authors copyright
                         "" "" ; date type
                    ))
            900))

; a query on a specific name returns the same name
(assert `(string=? ( car (ammoos-pdb-query
                            "ammoos-pdb-proc-exists" ; name
                            "" "" ; blurb help
                            "" "" ; authors copyright
                            "" ""))
                    "ammoos-pdb-proc-exists"))


(test! "PDB generate a unique name.")
; name guaranteed to be unique for life of AmmoOS Image session.
; I.E. the PDB has a generator.
; Only testing type is string, not that it is unique.
(assert `(string? (ammoos-pdb-temp-name)))




(script-fu-use-v2)