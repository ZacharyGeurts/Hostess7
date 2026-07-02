#!/usr/bin/env pythong
"""Court lexicon — full formal law words and phrases for presentation; no shorthands."""
from __future__ import annotations

# category: party | pleading | motion | discovery | evidence | trial | objection
#          | standard | appeal | criminal | constitutional | contract_form | ethics

COURT_LEXICON: tuple[dict[str, str | tuple[str, ...]], ...] = (
    # ── Parties & roles ─────────────────────────────────────────────────
    {
        "id": "plaintiff",
        "category": "party",
        "term": "Plaintiff",
        "tags": ("plaintiff", "complainant", "petitioner", "claimant"),
        "body": (
            "The Plaintiff is the party who initiates a civil action by filing a complaint, "
            "alleging injury or entitlement to relief against the Defendant."
        ),
    },
    {
        "id": "defendant",
        "category": "party",
        "term": "Defendant",
        "tags": ("defendant", "respondent", "accused"),
        "body": (
            "The Defendant is the party against whom relief is sought in a civil action, "
            "or the accused in a criminal prosecution."
        ),
    },
    {
        "id": "movant",
        "category": "party",
        "term": "Movant",
        "tags": ("movant", "moving party", "applicant"),
        "body": (
            "The Movant is the party filing a motion and bearing the burden to establish "
            "entitlement to the relief requested."
        ),
    },
    {
        "id": "prosecutor",
        "category": "party",
        "term": "Prosecutor",
        "tags": ("prosecutor", "district attorney", "people", "state", "united states"),
        "body": (
            "The Prosecutor represents the government in a criminal proceeding — "
            "for example, the United States Attorney in federal court or the District Attorney in state court."
        ),
    },
    # ── Pleadings ───────────────────────────────────────────────────────
    {
        "id": "complaint",
        "category": "pleading",
        "term": "Complaint",
        "tags": ("complaint", "civil action", "filing", "pleading"),
        "body": (
            "A Complaint is the initial pleading that commences a civil action, stating claims for relief "
            "with sufficient factual allegations to state a plausible claim under Federal Rule of Civil Procedure 8(a), "
            "or the equivalent state rule."
        ),
    },
    {
        "id": "answer",
        "category": "pleading",
        "term": "Answer",
        "tags": ("answer", "response", "denial", "affirmative defense"),
        "body": (
            "An Answer is the Defendant's responsive pleading admitting or denying allegations in the Complaint "
            "and asserting Affirmative Defenses as permitted by Federal Rule of Civil Procedure 8(c)."
        ),
    },
    {
        "id": "counterclaim",
        "category": "pleading",
        "term": "Counterclaim",
        "tags": ("counterclaim", "cross-claim", "third-party"),
        "body": (
            "A Counterclaim is a claim asserted by a Defendant against the Plaintiff in the same action. "
            "A Cross-Claim is asserted against a co-party. A Third-Party Complaint impleads a non-party "
            "who may be liable for all or part of the Plaintiff's claim."
        ),
    },
    # ── Motions (full names — no abbreviations) ─────────────────────────
    {
        "id": "motion_dismiss",
        "category": "motion",
        "term": "Motion to Dismiss",
        "tags": ("motion to dismiss", "12(b)(6)", "failure to state", "demurrer"),
        "body": (
            "A Motion to Dismiss requests termination of the action for specified grounds. "
            "Under Federal Rule of Civil Procedure 12(b)(6), a Defendant may move to dismiss for failure "
            "to state a claim upon which relief can be granted, accepting well-pleaded factual allegations as true "
            "and drawing reasonable inferences in favor of the non-moving party."
        ),
    },
    {
        "id": "motion_summary_judgment",
        "category": "motion",
        "term": "Motion for Summary Judgment",
        "tags": ("summary judgment", "no genuine dispute", "material fact"),
        "body": (
            "A Motion for Summary Judgment under Federal Rule of Civil Procedure 56 requests judgment as a matter of law "
            "when there is no genuine dispute as to any material fact and the Movant is entitled to judgment as a matter of law. "
            "The Court views evidence in the light most favorable to the non-moving party."
        ),
    },
    {
        "id": "motion_preliminary_injunction",
        "category": "motion",
        "term": "Motion for Preliminary Injunction",
        "tags": ("preliminary injunction", "temporary restraining", "equitable relief"),
        "body": (
            "A Motion for Preliminary Injunction seeks equitable relief before final judgment. "
            "Courts typically consider likelihood of success on the merits, irreparable harm, "
            "balance of hardships, and the public interest."
        ),
    },
    {
        "id": "motion_suppress",
        "category": "motion",
        "term": "Motion to Suppress Evidence",
        "tags": ("suppress", "fourth amendment", "search", "seizure", "exclusionary"),
        "body": (
            "A Motion to Suppress Evidence asks the court to exclude evidence obtained in violation of "
            "the Fourth Amendment to the United States Constitution or applicable state constitutional protections "
            "against unreasonable searches and seizures."
        ),
    },
    {
        "id": "motion_compel",
        "category": "motion",
        "term": "Motion to Compel Discovery",
        "tags": ("compel", "discovery", "sanctions"),
        "body": (
            "A Motion to Compel Discovery under Federal Rule of Civil Procedure 37 requests an order requiring "
            "an opposing party to provide discovery responses and may seek sanctions for failure to comply."
        ),
    },
    {
        "id": "motion_directed_verdict",
        "category": "motion",
        "term": "Motion for Directed Verdict",
        "tags": ("directed verdict", "judgment as a matter of law", "jnov"),
        "body": (
            "A Motion for Directed Verdict (or Motion for Judgment as a Matter of Law under Federal Rule of Civil Procedure 50) "
            "asks the court to decide that a reasonable jury could not find for the opposing party on the evidence presented."
        ),
    },
    # ── Discovery (full phrases) ────────────────────────────────────────
    {
        "id": "interrogatories",
        "category": "discovery",
        "term": "Interrogatories",
        "tags": ("interrogatories", "written questions", "discovery"),
        "body": (
            "Interrogatories are written questions served on a party under Federal Rule of Civil Procedure 33, "
            "requiring sworn written answers within the prescribed time period."
        ),
    },
    {
        "id": "request_production",
        "category": "discovery",
        "term": "Request for Production of Documents",
        "tags": ("production", "documents", "electronically stored information", "discovery"),
        "body": (
            "A Request for Production of Documents and Electronically Stored Information under Federal Rule of Civil Procedure 34 "
            "requires a party to produce specified materials for inspection and copying."
        ),
    },
    {
        "id": "request_admissions",
        "category": "discovery",
        "term": "Request for Admission",
        "tags": ("admission", "request for admission", "discovery"),
        "body": (
            "A Request for Admission under Federal Rule of Civil Procedure 36 asks a party to admit or deny "
            "the truth of stated matters of fact or the genuineness of documents, narrowing triable issues."
        ),
    },
    {
        "id": "deposition",
        "category": "discovery",
        "term": "Deposition",
        "tags": ("deposition", "oral examination", "under oath", "discovery"),
        "body": (
            "A Deposition is sworn oral testimony taken outside court under Federal Rule of Civil Procedure 30, "
            "recorded by a court reporter, and usable for impeachment and certain substantive purposes at trial."
        ),
    },
    {
        "id": "subpoena_duces_tecum",
        "category": "discovery",
        "term": "Subpoena Duces Tecum",
        "tags": ("subpoena", "duces tecum", "compel testimony", "documents"),
        "body": (
            "A Subpoena Duces Tecum is a court order commanding a person to appear and bring specified documents "
            "or electronically stored information for examination."
        ),
    },
    # ── Evidence ────────────────────────────────────────────────────────
    {
        "id": "hearsay",
        "category": "evidence",
        "term": "Hearsay",
        "tags": ("hearsay", "out of court", "statement", "offered for truth"),
        "body": (
            "Hearsay is an out-of-court statement offered to prove the truth of the matter asserted, "
            "generally inadmissible under Federal Rule of Evidence 802 unless an exception or exclusion applies."
        ),
    },
    {
        "id": "relevance",
        "category": "evidence",
        "term": "Relevance",
        "tags": ("relevance", "probative", "prejudicial", "403"),
        "body": (
            "Evidence is Relevant if it has any tendency to make a fact more or less probable under Federal Rule of Evidence 401. "
            "The court may exclude relevant evidence if its probative value is substantially outweighed by unfair prejudice "
            "under Federal Rule of Evidence 403."
        ),
    },
    {
        "id": "attorney_client_privilege",
        "category": "evidence",
        "term": "Attorney-Client Privilege",
        "tags": ("privilege", "attorney client", "confidential", "legal advice"),
        "body": (
            "The Attorney-Client Privilege protects confidential communications between a client and attorney "
            "made for the purpose of obtaining legal advice; the privilege is held by the client and may be waived."
        ),
    },
    {
        "id": "work_product",
        "category": "evidence",
        "term": "Work Product Doctrine",
        "tags": ("work product", "litigation", "prepared in anticipation"),
        "body": (
            "The Work Product Doctrine under Federal Rule of Civil Procedure 26(b)(3) protects materials prepared "
            "in anticipation of litigation by or for a party or representative, with heightened protection for mental impressions."
        ),
    },
    {
        "id": "authentication",
        "category": "evidence",
        "term": "Authentication",
        "tags": ("authentication", "foundation", "admissibility", "901"),
        "body": (
            "Authentication under Federal Rule of Evidence 901 requires evidence sufficient to support a finding "
            "that the item is what the proponent claims before the evidence may be admitted."
        ),
    },
    # ── Trial ─────────────────────────────────────────────────────────
    {
        "id": "voir_dire",
        "category": "trial",
        "term": "Voir Dire",
        "tags": ("voir dire", "jury selection", "challenge", "peremptory"),
        "body": (
            "Voir Dire is the examination of prospective jurors to determine bias and fitness to serve, "
            "including challenges for cause and peremptory challenges within constitutional limits."
        ),
    },
    {
        "id": "opening_statement",
        "category": "trial",
        "term": "Opening Statement",
        "tags": ("opening", "preview", "trial"),
        "body": (
            "An Opening Statement is counsel's non-argumentative preview of expected evidence; "
            "it is not evidence and must not misstate what will be proven."
        ),
    },
    {
        "id": "direct_examination",
        "category": "trial",
        "term": "Direct Examination",
        "tags": ("direct", "examination", "witness", "trial"),
        "body": (
            "Direct Examination is questioning of a witness called by the examining party; "
            "leading questions are generally prohibited except on preliminary matters and hostile witnesses."
        ),
    },
    {
        "id": "cross_examination",
        "category": "trial",
        "term": "Cross-Examination",
        "tags": ("cross", "examination", "impeachment", "trial"),
        "body": (
            "Cross-Examination is questioning of a witness by the adverse party, permitting leading questions "
            "and impeachment by prior inconsistent statement, bias, or character for truthfulness."
        ),
    },
    {
        "id": "closing_argument",
        "category": "trial",
        "term": "Closing Argument",
        "tags": ("closing", "summation", "argument", "trial"),
        "body": (
            "Closing Argument is counsel's final persuasive address to judge or jury, "
            "drawing reasonable inferences from admitted evidence without introducing new facts."
        ),
    },
    {
        "id": "jury_instruction",
        "category": "trial",
        "term": "Jury Instruction",
        "tags": ("jury instruction", "charge", "elements", "burden of proof"),
        "body": (
            "A Jury Instruction is the court's statement of applicable law, including elements of claims or offenses "
            "and the burden and standard of proof, on which the jury must base its verdict."
        ),
    },
    # ── Objections (courtroom forms) ────────────────────────────────────
    {
        "id": "objection_hearsay",
        "category": "objection",
        "term": "Objection — Hearsay",
        "tags": ("objection", "hearsay", "form"),
        "body": "Objection, Your Honor. The testimony is hearsay, offered for the truth of the matter asserted, and no exception applies.",
    },
    {
        "id": "objection_relevance",
        "category": "objection",
        "term": "Objection — Relevance",
        "tags": ("objection", "relevance", "immaterial"),
        "body": "Objection, Your Honor. The evidence is not relevant to any material issue in this case.",
    },
    {
        "id": "objection_leading",
        "category": "objection",
        "term": "Objection — Leading",
        "tags": ("objection", "leading", "direct"),
        "body": "Objection, Your Honor. Counsel is leading the witness on direct examination.",
    },
    {
        "id": "objection_speculation",
        "category": "objection",
        "term": "Objection — Speculation",
        "tags": ("objection", "speculation", "foundation"),
        "body": "Objection, Your Honor. The question calls for speculation; the witness lacks personal knowledge or adequate foundation.",
    },
    {
        "id": "objection_argumentative",
        "category": "objection",
        "term": "Objection — Argumentative",
        "tags": ("objection", "argumentative", "badgering"),
        "body": "Objection, Your Honor. The question is argumentative and not designed to elicit testimony.",
    },
    {
        "id": "objection_privilege",
        "category": "objection",
        "term": "Objection — Privilege",
        "tags": ("objection", "privilege", "attorney client"),
        "body": "Objection, Your Honor. The communication is protected by the Attorney-Client Privilege.",
    },
    # ── Standards of proof ──────────────────────────────────────────────
    {
        "id": "beyond_reasonable_doubt",
        "category": "standard",
        "term": "Beyond a Reasonable Doubt",
        "tags": ("reasonable doubt", "criminal", "burden", "proof"),
        "body": (
            "Beyond a Reasonable Doubt is the burden of proof in criminal cases requiring moral certainty "
            "of guilt; the highest standard in American courts, constitutionally required for conviction."
        ),
    },
    {
        "id": "preponderance",
        "category": "standard",
        "term": "Preponderance of the Evidence",
        "tags": ("preponderance", "more likely than not", "civil", "burden"),
        "body": (
            "Preponderance of the Evidence is the standard in most civil cases: the fact is more likely true than not — "
            "greater than fifty percent probability."
        ),
    },
    {
        "id": "clear_convincing",
        "category": "standard",
        "term": "Clear and Convincing Evidence",
        "tags": ("clear and convincing", "intermediate", "burden", "fraud"),
        "body": (
            "Clear and Convincing Evidence is an intermediate standard applied in selected civil matters "
            "such as fraud, termination of parental rights, and certain equitable claims."
        ),
    },
    # ── Appeals ─────────────────────────────────────────────────────────
    {
        "id": "standard_de_novo",
        "category": "appeal",
        "term": "De Novo Review",
        "tags": ("de novo", "standard of review", "appeal", "legal question"),
        "body": (
            "De Novo Review means the appellate court decides the issue anew without deferring to the trial court, "
            "typically applied to questions of law and summary judgment rulings."
        ),
    },
    {
        "id": "abuse_discretion",
        "category": "appeal",
        "term": "Abuse of Discretion",
        "tags": ("abuse of discretion", "standard of review", "appeal"),
        "body": (
            "Abuse of Discretion is the standard of review for many trial court discretionary rulings; "
            "reversal requires showing the decision was arbitrary, capricious, or unsupported by the record."
        ),
    },
    {
        "id": "clearly_erroneous",
        "category": "appeal",
        "term": "Clearly Erroneous",
        "tags": ("clearly erroneous", "findings of fact", "appeal"),
        "body": (
            "Clearly Erroneous is the standard for reviewing trial court findings of fact; "
            "the appellate court will not overturn unless left with definite and firm conviction of mistake."
        ),
    },
    # ── Criminal procedure (full terms) ─────────────────────────────────
    {
        "id": "arraignment",
        "category": "criminal",
        "term": "Arraignment",
        "tags": ("arraignment", "plea", "not guilty", "initial appearance"),
        "body": (
            "Arraignment is the proceeding at which the Defendant is informed of charges and enters a plea — "
            "Guilty, Not Guilty, or Nolo Contendere where permitted."
        ),
    },
    {
        "id": "grand_jury_indictment",
        "category": "criminal",
        "term": "Grand Jury Indictment",
        "tags": ("indictment", "grand jury", "felony", "presentment"),
        "body": (
            "A Grand Jury Indictment is a formal written accusation returned by a grand jury finding probable cause "
            "to charge the accused with a felony under the Fifth Amendment to the United States Constitution."
        ),
    },
    {
        "id": "miranda",
        "category": "criminal",
        "term": "Miranda Warning",
        "tags": ("miranda", "custodial interrogation", "right to remain silent", "counsel"),
        "body": (
            "Miranda Warnings advise a person in custodial interrogation of the right to remain silent, "
            "that statements may be used in court, and the right to the assistance of counsel, "
            "under Miranda v. Arizona, 384 U.S. 436 (1966)."
        ),
    },
    {
        "id": "plea_bargain",
        "category": "criminal",
        "term": "Plea Bargain",
        "tags": ("plea bargain", "plea agreement", "guilty plea", "prosecution"),
        "body": (
            "A Plea Bargain is an agreement between the Prosecutor and Defendant to resolve charges "
            "by guilty or nolo contendere plea to specified counts with recommended sentence or dismissed charges, "
            "subject to court acceptance under Federal Rule of Criminal Procedure 11."
        ),
    },
    # ── Constitutional (full amendment names) ───────────────────────────
    {
        "id": "first_amendment",
        "category": "constitutional",
        "term": "First Amendment to the United States Constitution",
        "tags": ("first amendment", "speech", "religion", "press", "assembly"),
        "body": (
            "The First Amendment to the United States Constitution protects freedom of speech, religion, press, "
            "assembly, and petition; content-based restrictions receive strict scrutiny."
        ),
    },
    {
        "id": "fourth_amendment",
        "category": "constitutional",
        "term": "Fourth Amendment to the United States Constitution",
        "tags": ("fourth amendment", "search", "seizure", "warrant", "probable cause"),
        "body": (
            "The Fourth Amendment to the United States Constitution protects against unreasonable searches and seizures; "
            "warrants require probable cause supported by oath or affirmation."
        ),
    },
    {
        "id": "fifth_amendment",
        "category": "constitutional",
        "term": "Fifth Amendment to the United States Constitution",
        "tags": ("fifth amendment", "self incrimination", "due process", "double jeopardy", "grand jury", "miranda", "takings"),
        "body": (
            "The Fifth Amendment to the United States Constitution provides: (1) Grand Jury indictment required for capital or "
            "otherwise infamous crimes, except military service cases; (2) prohibition on double jeopardy — no person twice put in "
            "jeopardy of life or limb for the same offence; (3) privilege against compelled self-incrimination in any criminal case; "
            "(4) due process of law before deprivation of life, liberty, or property; (5) just compensation when private property "
            "is taken for public use. Miranda v. Arizona, 384 U.S. 436 (1966) requires custodial warnings derived from the "
            "self-incrimination privilege and Sixth Amendment counsel right."
        ),
    },
    {
        "id": "sixth_amendment",
        "category": "constitutional",
        "term": "Sixth Amendment to the United States Constitution",
        "tags": ("sixth amendment", "counsel", "confrontation", "speedy trial", "jury"),
        "body": (
            "The Sixth Amendment to the United States Constitution guarantees the accused the right to a speedy and public trial, "
            "impartial jury, notice of accusation, confrontation of witnesses, compulsory process, and assistance of counsel."
        ),
    },
    {
        "id": "fourteenth_amendment",
        "category": "constitutional",
        "term": "Fourteenth Amendment to the United States Constitution",
        "tags": ("fourteenth amendment", "due process", "equal protection", "incorporation"),
        "body": (
            "The Fourteenth Amendment to the United States Constitution prohibits states from depriving any person of life, liberty, "
            "or property without due process of law or denying equal protection of the laws."
        ),
    },
    # ── Contract formal elements ──────────────────────────────────────────
    {
        "id": "statute_frauds",
        "category": "contract_form",
        "term": "Statute of Frauds",
        "tags": ("statute of frauds", "writing", "land", "surety", "year"),
        "body": (
            "The Statute of Frauds requires certain contracts to be in writing to be enforceable, "
            "including contracts for the sale of land, agreements not performable within one year, "
            "and suretyship undertakings, as adopted in state statutes and the Uniform Commercial Code."
        ),
    },
    {
        "id": "uniform_commercial_code",
        "category": "contract_form",
        "term": "Uniform Commercial Code",
        "tags": ("uniform commercial code", "ucc", "goods", "merchant", "article 2"),
        "body": (
            "The Uniform Commercial Code governs commercial transactions; Article 2 governs sales of goods. "
            "Present in substantially uniform form in all fifty states; supersedes common law for covered transactions."
        ),
    },
    {
        "id": "force_majeure",
        "category": "contract_form",
        "term": "Force Majeure",
        "tags": ("force majeure", "impossibility", "frustration", "act of god"),
        "body": (
            "A Force Majeure clause excuses performance when extraordinary events beyond the parties' control "
            "prevent fulfillment; distinct from common law doctrines of impossibility and frustration of purpose."
        ),
    },
    # ── Ethics & court decorum ────────────────────────────────────────────
    {
        "id": "your_honor",
        "category": "ethics",
        "term": "Your Honor",
        "tags": ("your honor", "court", "decorum", "address"),
        "body": (
            "Counsel addresses the presiding judicial officer as 'Your Honor' in United States courts. "
            "Formal titles: 'The Court' in briefs; 'May it please the Court' to open oral argument."
        ),
    },
    {
        "id": "may_it_please_court",
        "category": "ethics",
        "term": "May It Please the Court",
        "tags": ("may it please", "oral argument", "opening", "appellate"),
        "body": (
            "May It Please the Court is the traditional opening for oral argument before a trial or appellate bench, "
            "followed by identification of counsel and party represented."
        ),
    },
    # ── Supreme Court of the United States ────────────────────────────────
    {
        "id": "writ_certiorari",
        "category": "scotus",
        "term": "Writ of Certiorari",
        "tags": ("certiorari", "writ", "supreme court", "petition", "scotus"),
        "body": (
            "A Writ of Certiorari is an order of the Supreme Court of the United States directing the lower court "
            "to transmit the record for review of a final judgment or decree."
        ),
    },
    {
        "id": "rule_of_four",
        "category": "scotus",
        "term": "Rule of Four",
        "tags": ("rule of four", "grant", "certiorari", "discretionary"),
        "body": (
            "The Rule of Four provides that certiorari is granted when four Justices vote to hear a case; "
            "denial is without opinion on the merits."
        ),
    },
    {
        "id": "per_curiam",
        "category": "scotus",
        "term": "Per Curiam Opinion",
        "tags": ("per curiam", "unsigned", "opinion", "supreme court"),
        "body": (
            "A Per Curiam Opinion is issued by the Court as an institution without attribution to a single author, "
            "often brief and unanimous."
        ),
    },
    {
        "id": "dissenting_opinion",
        "category": "scotus",
        "term": "Dissenting Opinion",
        "tags": ("dissent", "dissenting opinion", "minority", "justice"),
        "body": (
            "A Dissenting Opinion explains why one or more Justices disagree with the Majority Opinion; "
            "dissents may forecast future doctrine but are not controlling precedent."
        ),
    },
    {
        "id": "concurring_opinion",
        "category": "scotus",
        "term": "Concurring Opinion",
        "tags": ("concurrence", "concurring opinion", "judgment", "reasoning"),
        "body": (
            "A Concurring Opinion agrees with the judgment of the Court but for reasons different from the Majority Opinion."
        ),
    },
    {
        "id": "judicial_review",
        "category": "scotus",
        "term": "Judicial Review",
        "tags": ("judicial review", "marbury", "constitution", "invalid"),
        "body": (
            "Judicial Review is the power of courts to declare legislative acts unconstitutional, "
            "recognized in Marbury v. Madison, 5 U.S. (1 Cranch) 137 (1803)."
        ),
    },
    {
        "id": "strict_scrutiny",
        "category": "scotus",
        "term": "Strict Scrutiny",
        "tags": ("strict scrutiny", "compelling interest", "narrow tailoring", "constitutional"),
        "body": (
            "Strict Scrutiny requires the government to prove a compelling governmental interest "
            "and that the regulation is narrowly tailored to achieve that interest."
        ),
    },
    {
        "id": "amicus_curiae",
        "category": "scotus",
        "term": "Amicus Curiae",
        "tags": ("amicus", "friend of the court", "brief", "supreme court"),
        "body": (
            "An Amicus Curiae is a friend of the court — a non-party who files a brief offering information or perspective "
            "with leave of the Court or consent of the parties."
        ),
    },
    {
        "id": "stipulate",
        "category": "ethics",
        "term": "Stipulation",
        "tags": ("stipulate", "stipulation", "agreed fact", "admission"),
        "body": (
            "A Stipulation is a binding agreement between parties on facts, procedure, or evidence, "
            "presented to the court for acceptance and inclusion in the record."
        ),
    },
)

LEXICON_CATEGORIES: tuple[str, ...] = (
    "party", "pleading", "motion", "discovery", "evidence", "trial",
    "objection", "standard", "appeal", "criminal", "constitutional",
    "contract_form", "ethics", "scotus",
)