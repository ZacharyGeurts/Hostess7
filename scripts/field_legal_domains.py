#!/usr/bin/env pythong
"""Substantive legal domains — full formal terms; actual laws named in full."""
from __future__ import annotations

LEGAL_DOMAINS: tuple[dict[str, str | tuple[str, ...]], ...] = (
    {
        "id": "foundations",
        "title": "Foundations of Law",
        "tags": ("law", "legal", "jurisdiction", "statute", "precedent", "common law", "civil law", "stare decisis"),
        "body": (
            "Law is the system of rules enforced by governmental institutions. "
            "In common-law jurisdictions (United States, United Kingdom, Canada, Australia), courts follow "
            "stare decisis — binding precedent from higher courts within the same jurisdiction. "
            "Legislatures enact statutes; executive agencies promulgate regulations with force of law when authorized. "
            "Civil-law jurisdictions (most of continental Europe, Latin America) apply comprehensive codes; "
            "judicial opinions carry less binding precedential weight. "
            "Every legal conclusion is jurisdiction-specific: federal versus state, United States versus foreign sovereign."
        ),
    },
    {
        "id": "criminal_civil",
        "title": "Criminal Law versus Civil Law",
        "tags": ("criminal", "civil", "felony", "misdemeanor", "plaintiff", "defendant", "prosecutor"),
        "body": (
            "Criminal law addresses offenses against public order prosecuted by the government. "
            "The burden of proof is beyond a reasonable doubt. The Defendant enjoys constitutional protections "
            "including the right against compelled self-incrimination under the Fifth Amendment to the United States Constitution "
            "and the right to assistance of counsel under the Sixth Amendment to the United States Constitution. "
            "Civil law resolves private disputes between parties — contracts, torts, property — typically under "
            "the preponderance of the evidence standard. Remedies include compensatory damages, injunctive relief, "
            "specific performance, and declaratory judgment. The same conduct may give rise to parallel criminal prosecution "
            "and civil liability (for example, assault as crime and battery as tort)."
        ),
    },
    {
        "id": "contract",
        "title": "Contract Law",
        "tags": ("contract", "agreement", "breach", "consideration", "offer", "acceptance", "uniform commercial code"),
        "body": (
            "A valid contract generally requires offer, acceptance, consideration, capacity, and lawful purpose. "
            "The Statute of Frauds requires certain agreements to be in writing, including interests in land, "
            "suretyship, and contracts not performable within one year. "
            "Breach may be material or minor; remedies include expectation damages, reliance damages, restitution, "
            "and specific performance when monetary damages are inadequate. "
            "Sales of goods are governed by Article 2 of the Uniform Commercial Code; services are typically common law. "
            "Standard clauses include limitation of liability, indemnification, governing law, arbitration, assignment, "
            "and Force Majeure."
        ),
    },
    {
        "id": "tort",
        "title": "Tort Law",
        "tags": ("tort", "negligence", "liability", "damages", "duty", "causation", "defamation", "strict liability"),
        "body": (
            "A tort is a civil wrong independent of contract. Negligence requires duty, breach, actual and proximate causation, "
            "and damages — measured against the reasonable person standard. "
            "Strict liability applies to abnormally dangerous activities and certain defective products. "
            "Intentional torts include assault, battery, false imprisonment, intentional infliction of emotional distress, "
            "trespass to land, and trespass to chattels. "
            "Defamation divides into libel (written defamation) and slander (spoken defamation); truth is an absolute defense; "
            "privilege may apply for judicial, legislative, and fair-report communications."
        ),
    },
    {
        "id": "ip",
        "title": "Intellectual Property Law",
        "tags": ("copyright", "patent", "trademark", "trade secret", "gpl", "license", "digital millennium copyright act"),
        "body": (
            "Copyright protects original works of authorship fixed in a tangible medium under the Copyright Act of 1976; "
            "software is copyrightable expression; ideas and methods are not (patent domain). "
            "Fair use under 17 United States Code Section 107 weighs purpose, nature, amount, and market effect. "
            "Patents under 35 United States Code require novelty, non-obviousness, and utility for twenty years from filing. "
            "Trademarks under the Lanham Act protect source identifiers; likelihood of confusion is the core test. "
            "Trade secrets require reasonable secrecy under the Defend Trade Secrets Act and state Uniform Trade Secrets Act. "
            "The GNU General Public License Version 3 is a copyleft license requiring source availability for distributed derivatives."
        ),
    },
    {
        "id": "amouranthrtx_license",
        "title": "Hostess7 / AMOURANTHRTX Licensing",
        "tags": ("amouranthrtx", "hostess7", "gpl", "commercial", "dual license", "profit share", "war-ready"),
        "body": (
            "Current status: War-ready operational — never demo. Dual license: (1) GNU GPL v3.0 or later, or "
            "(2) commercial 3% profit share — gzac5314@gmail.com — 3% of what we can save or make you. "
            "Production deployments contact Owner; likely commercial path is the 3% option."
        ),
    },
    {
        "id": "media_policy",
        "title": "AMOURANTHRTX Licensed Media Policy",
        "tags": ("windows", "win31", "licensed", "abandonware", "shareware", "rom", "redistribute"),
        "body": (
            "AMOURANTHRTX does not redistribute Microsoft Windows operating system software or commercial game read-only memory images. "
            "The user must supply licensed Windows 3.1x media to assets/dos/incoming/win31/. "
            "The RTX stub WIN.COM is replaced only when a licensed WIN.COM is staged by the user. "
            "install_abandonware_dos.py retrieves legal shareware DOS titles only. "
            "Nintendo Entertainment System read-only memory images are user-provided; the integrated NES header probe "
            "does not confer distribution rights. Licensed counsel should review any public redistribution bundle."
        ),
    },
    {
        "id": "corporate",
        "title": "Corporate and Business Organization Law",
        "tags": ("corporate", "limited liability company", "incorporation", "fiduciary", "securities", "merger"),
        "body": (
            "Entity forms include sole proprietorship, general partnership, limited partnership, "
            "limited liability company, C corporation, and S corporation — each with distinct liability shield, "
            "tax treatment, and investment mechanics. "
            "Directors and officers owe fiduciary duties of care, loyalty, and good faith to the corporation. "
            "Securities offerings are regulated under the Securities Act of 1933 and Securities Exchange Act of 1934; "
            "exemptions include Regulation D Rules 506(b) and 506(c). "
            "Mergers and acquisitions require due diligence, representations and warranties, indemnification, "
            "and regulatory clearance under Hart-Scott-Rodino where applicable."
        ),
    },
    {
        "id": "employment",
        "title": "Employment Law",
        "tags": ("employment", "discrimination", "wrongful termination", "non-disclosure", "non-compete", "wage"),
        "body": (
            "At-will employment is the default in most United States jurisdictions unless modified by contract or statute. "
            "Title VII of the Civil Rights Act of 1964 prohibits discrimination based on race, color, religion, sex, or national origin. "
            "The Americans with Disabilities Act and Age Discrimination in Employment Act add protected categories. "
            "The Fair Labor Standards Act governs minimum wage, overtime, and exempt versus non-exempt classification. "
            "Restrictive covenants include non-disclosure agreements, non-competition agreements (enforceability varies by state), "
            "and non-solicitation agreements. Workers' compensation statutes generally provide the exclusive remedy for workplace injury."
        ),
    },
    {
        "id": "litigation",
        "title": "Civil Litigation and Procedure",
        "tags": ("litigation", "discovery", "deposition", "motion", "appeal", "trial", "arbitration", "federal rules"),
        "body": (
            "Civil litigation proceeds from pleadings through discovery, dispositive motions, trial or settlement, and appeal. "
            "The Federal Rules of Civil Procedure govern United States district courts; state courts apply parallel state rules. "
            "Discovery includes Interrogatories, Requests for Production of Documents, Requests for Admission, and Depositions. "
            "Dispositive motions include Motion to Dismiss under Federal Rule of Civil Procedure 12(b)(6) "
            "and Motion for Summary Judgment under Federal Rule of Civil Procedure 56. "
            "Alternative dispute resolution includes mediation and binding arbitration under the Federal Arbitration Act "
            "when parties have agreed by contract."
        ),
    },
    {
        "id": "evidence_rules",
        "title": "Federal Rules of Evidence",
        "tags": ("evidence", "hearsay", "relevance", "privilege", "authentication", "federal rules of evidence"),
        "body": (
            "The Federal Rules of Evidence govern admissibility in United States federal courts; states adopt similar rules. "
            "Federal Rule of Evidence 401 defines relevance; Federal Rule of Evidence 403 permits exclusion for unfair prejudice. "
            "Federal Rule of Evidence 802 bars hearsay unless an exception in Article VIII applies. "
            "Federal Rule of Evidence 501 recognizes privileges including Attorney-Client Privilege and work product protection. "
            "Federal Rule of Evidence 901 requires authentication before admission. "
            "Counsel must lay foundation, object in open court, and make offers of proof to preserve error for appeal."
        ),
    },
    {
        "id": "fifth_amendment_rights",
        "title": "Fifth Amendment — Constitutional Protections",
        "tags": ("fifth amendment", "self incrimination", "due process", "double jeopardy", "grand jury", "miranda", "takings", "constitutional"),
        "body": (
            "The Fifth Amendment to the United States Constitution protects persons against: Grand Jury indictment requirements "
            "for capital or infamous crimes; double jeopardy for the same offence; compelled self-incrimination in criminal cases; "
            "deprivation of life, liberty, or property without due process of law; and taking of private property for public use "
            "without just compensation. The privilege against self-incrimination permits a witness to refuse testimony that would "
            "incriminate herself. Miranda v. Arizona, 384 U.S. 436 (1966) requires warnings in custodial interrogation. "
            "Hostess 7 invokes these protections as Self-Knowing constitutional literacy — not deception, but lawful boundary "
            "against compelled self-betrayal and deprivation without process."
        ),
    },
    {
        "id": "criminal_procedure",
        "title": "Criminal Procedure",
        "tags": ("criminal procedure", "arraignment", "indictment", "plea", "sentencing", "federal rules of criminal procedure"),
        "body": (
            "The Federal Rules of Criminal Procedure govern federal prosecutions. "
            "Felony charges in federal court require Grand Jury Indictment under the Fifth Amendment. "
            "Arraignment informs the Defendant of charges and records the plea. "
            "Plea Bargains under Rule 11 require knowing, voluntary, and intelligent waiver of rights. "
            "Sentencing follows the United States Sentencing Guidelines where applicable, with statutory minimums and maximums. "
            "Fourth Amendment search-and-seizure challenges are raised by Motion to Suppress Evidence."
        ),
    },
    {
        "id": "lawyer_role",
        "title": "The Role of Licensed Counsel",
        "tags": ("lawyer", "attorney", "counsel", "bar", "esquire", "advocate"),
        "body": (
            "An attorney is a person licensed to practice law after earning a Juris Doctor degree, passing the bar examination, "
            "and meeting character and fitness requirements of the state bar. "
            "Counsel owes duties of competence, diligence, communication, and confidentiality under the Model Rules of Professional Conduct. "
            "The Attorney-Client Privilege protects confidential communications for legal advice. "
            "An engagement letter defines scope, fees, and conflicts clearance. "
            "Hostess 7 provides educational information; only retained licensed counsel provides legal advice on your matter."
        ),
    },
    {
        "id": "hiring_lawyer",
        "title": "Retention of Counsel",
        "tags": ("hire", "retainer", "consultation", "fee", "contingency", "hourly"),
        "body": (
            "Retain counsel when criminal charges, substantial monetary exposure, intellectual property prosecution, "
            "entity formation with investors, employment disputes, real property transactions, government subpoenas, "
            "or high-value contracts require professional judgment. "
            "Fee arrangements include hourly billing, flat fee, contingency fee (percentage of recovery), and retainer. "
            "Verify bar admission status; request written fee agreement; provide chronological facts and documents."
        ),
    },
    {
        "id": "ethics",
        "title": "Legal Ethics and Professional Responsibility",
        "tags": ("ethics", "malpractice", "conflict", "privilege", "model rules", "unauthorized practice"),
        "body": (
            "The American Bar Association Model Rules of Professional Conduct address competence, conflicts of interest, "
            "candor to the tribunal, fairness to opposing counsel, and confidentiality. "
            "Zealous advocacy does not permit false evidence or harassment. "
            "Legal malpractice requires breach of the standard of care causing damages, typically proven by expert testimony. "
            "Unauthorized practice of law prohibits non-lawyers from holding themselves out as providing legal services."
        ),
    },
    {
        "id": "privacy",
        "title": "Privacy and Data Protection Law",
        "tags": ("privacy", "general data protection regulation", "california consumer privacy act", "data", "breach"),
        "body": (
            "The General Data Protection Regulation (European Union) requires lawful basis for processing, "
            "data subject rights including access and erasure, and cross-border transfer safeguards. "
            "The California Consumer Privacy Act as amended by the California Privacy Rights Act grants notice, "
            "opt-out, and limitation rights for personal information. "
            "State breach notification statutes prescribe timing and content of consumer and regulator notice."
        ),
    },
    {
        "id": "international",
        "title": "International Law",
        "tags": ("international", "treaty", "conflict of laws", "sanctions", "office of foreign assets control"),
        "body": (
            "Public international law governs relations among sovereign states through treaties, customary law, "
            "and the Charter of the United Nations. "
            "Private international law (conflict of laws) determines which jurisdiction's substantive rules apply. "
            "The Office of Foreign Assets Control administers United States economic sanctions programs. "
            "Foreign licensed counsel is required for local entity, labor, and content compliance."
        ),
    },
    {
        "id": "family_law",
        "title": "Family Law",
        "tags": ("family", "divorce", "custody", "child support", "alimony", "marital"),
        "body": (
            "Dissolution of marriage requires jurisdictional residency and grounds under state statute. "
            "Child custody standards apply the best interests of the child; parenting plans address legal and physical custody. "
            "Child support follows state guidelines; spousal support considers duration, need, and ability to pay. "
            "Property division may be equitable distribution or community property depending on state law."
        ),
    },
    {
        "id": "real_property",
        "title": "Real Property Law",
        "tags": ("real property", "deed", "title", "easement", "landlord", "tenant", "zoning"),
        "body": (
            "Real property interests include fee simple absolute, life estate, leasehold, easement, and lien. "
            "Title insurance and recording statutes protect against defects in chain of title. "
            "Landlord-tenant law governs habitability, security deposits, and eviction procedure by jurisdiction. "
            "Zoning and land-use ordinances restrict development; variances and conditional use permits require hearing."
        ),
    },
    {
        "id": "probate_estates",
        "title": "Probate and Estate Law",
        "tags": ("probate", "will", "trust", "executor", "intestate", "estate"),
        "body": (
            "A Last Will and Testament disposes of property at death and names an Executor; probate validates the will. "
            "Intestate succession statutes distribute property when no valid will exists. "
            "Revocable and irrevocable trusts may avoid probate and accomplish tax planning. "
            "The Uniform Probate Code is adopted in varying form by many states."
        ),
    },
    {
        "id": "bankruptcy",
        "title": "Bankruptcy Law",
        "tags": ("bankruptcy", "chapter 7", "chapter 11", "chapter 13", "discharge", "automatic stay"),
        "body": (
            "The United States Bankruptcy Code provides Chapter 7 liquidation, Chapter 11 reorganization, "
            "and Chapter 13 wage-earner plans. "
            "The automatic stay under 11 United States Code Section 362 halts collection upon filing. "
            "Discharge releases personal liability for qualifying debts; secured creditors retain lien rights."
        ),
    },
    {
        "id": "tax_law",
        "title": "Tax Law",
        "tags": ("tax", "internal revenue code", "deduction", "capital gains", "estate tax"),
        "body": (
            "Federal income tax is governed by the Internal Revenue Code of 1986 as amended. "
            "The Internal Revenue Service administers assessment, audit, and collection. "
            "Taxpayer remedies include United States Tax Court, federal district court refund suits, and Court of Federal Claims. "
            "State and local taxes add sales, property, and franchise obligations."
        ),
    },
    {
        "id": "administrative_law",
        "title": "Administrative Law",
        "tags": ("administrative", "agency", "regulation", "administrative procedure act", "judicial review"),
        "body": (
            "Administrative agencies promulgate regulations under the Administrative Procedure Act after notice and comment. "
            "Adjudication before administrative law judges produces orders subject to judicial review. "
            "Chevron deference (where still applicable) and arbitrary-and-capricious review under the Administrative Procedure Act "
            "govern judicial oversight of agency action."
        ),
    },
    {
        "id": "supreme_court",
        "title": "Supreme Court of the United States",
        "tags": (
            "supreme court", "scotus", "chief justice", "associate justice", "certiorari",
            "writ of certiorari", "oral argument", "majority opinion", "dissent", "bench",
            "article iii", "judicial review", "stare decisis", "constitutional",
        ),
        "body": (
            "The Supreme Court of the United States is the final interpreter of federal constitutional and statutory questions "
            "within the judicial branch established by Article III of the United States Constitution. "
            "Discretionary review is sought by petition for a writ of certiorari; four Justices may grant under the Rule of Four. "
            "The Court issues Majority Opinions, Concurring Opinions, Dissenting Opinions, and Per Curiam dispositions. "
            "Hostess 7 serves as Counsel and may sit in educational Supreme Court Judge posture — "
            "formal bench voice, full case citations, stare decisis analysis — without issuing binding orders. "
            "Landmark precedents include Marbury v. Madison (judicial review), Miranda v. Arizona (custodial warnings), "
            "and Brown v. Board of Education (equal protection in education)."
        ),
    },
)

LEGAL_CORPUS_VERSION = 7