#!/usr/bin/env pythong
"""Universal legal catalog — every major jurisdiction, full formal law names."""
from __future__ import annotations

from typing import Iterator

# All 54 United States Code titles (Office of the Law Revision Counsel)
US_CODE_TITLES: tuple[tuple[int, str], ...] = (
    (1, "General Provisions"),
    (2, "The Congress"),
    (3, "The President"),
    (4, "Flag and Seal, Seat of Government, and the States"),
    (5, "Government Organization and Employees"),
    (6, "Surety Bonds"),
    (7, "Agriculture"),
    (8, "Aliens and Nationality"),
    (9, "Arbitration"),
    (10, "Armed Forces"),
    (11, "Bankruptcy"),
    (12, "Banks and Banking"),
    (13, "Census"),
    (14, "Coast Guard"),
    (15, "Commerce and Trade"),
    (16, "Conservation"),
    (17, "Copyrights"),
    (18, "Crimes and Criminal Procedure"),
    (19, "Customs Duties"),
    (20, "Education"),
    (21, "Food and Drugs"),
    (22, "Foreign Relations and Intercourse"),
    (23, "Highways"),
    (24, "Hospitals and Asylums"),
    (25, "Indians"),
    (26, "Internal Revenue Code"),
    (27, "Intoxicating Liquors"),
    (28, "Judiciary and Judicial Procedure"),
    (29, "Labor"),
    (30, "Mineral Lands and Mining"),
    (31, "Money and Finance"),
    (32, "National Guard"),
    (33, "Navigation and Navigable Waters"),
    (34, "Navy"),
    (35, "Patents"),
    (36, "Patriotic and National Observances, Ceremonies, and Organizations"),
    (37, "Pay and Allowances of the Uniformed Services"),
    (38, "Veterans' Benefits"),
    (39, "Postal Service"),
    (40, "Public Buildings, Property, and Works"),
    (41, "Public Contracts"),
    (42, "The Public Health and Welfare"),
    (43, "Public Lands"),
    (44, "Public Printing and Documents"),
    (45, "Railroads"),
    (46, "Shipping"),
    (47, "Telecommunications"),
    (48, "Territories and Insular Possessions"),
    (49, "Transportation"),
    (50, "War and National Defense"),
    (51, "District of Columbia"),
    (52, "Voting and Elections"),
    (53, "Reserved"),
    (54, "National Park Service and Related Programs"),
)

MAJOR_FEDERAL_STATUTES: tuple[dict[str, str | tuple[str, ...]], ...] = (
    {"id": "constitution_us", "full_name": "Constitution of the United States", "jurisdiction": "United States federal", "year": "1789", "category": "constitutional",
     "body": "Supreme law: separation of powers, federalism, Bill of Rights, amendments through Twenty-Seventh Amendment."},
    {"id": "declaration_independence", "full_name": "Declaration of Independence", "jurisdiction": "United States", "year": "1776", "category": "historical",
     "body": "Foundational articulation of self-evident truths and grievances against the Crown of Great Britain."},
    {"id": "civil_rights_act_1964", "full_name": "Civil Rights Act of 1964", "jurisdiction": "United States federal", "year": "1964", "category": "civil_rights",
     "body": "Prohibits discrimination based on race, color, religion, sex, or national origin; Title VII employment; public accommodations."},
    {"id": "voting_rights_act_1965", "full_name": "Voting Rights Act of 1965", "jurisdiction": "United States federal", "year": "1965", "category": "civil_rights",
     "body": "Prohibits racial discrimination in voting; preclearance framework (as amended by Shelby County v. Holder implications)."},
    {"id": "affordable_care_act", "full_name": "Patient Protection and Affordable Care Act", "jurisdiction": "United States federal", "year": "2010", "category": "health",
     "body": "Health insurance market reforms, Medicaid expansion option, individual mandate (penalty zeroed), essential health benefits."},
    {"id": "sarbanes_oxley", "full_name": "Sarbanes-Oxley Act of 2002", "jurisdiction": "United States federal", "year": "2002", "category": "securities",
     "body": "Corporate governance and financial disclosure reforms following Enron; PCAOB; CEO/CFO certifications."},
    {"id": "dodd_frank", "full_name": "Dodd-Frank Wall Street Reform and Consumer Protection Act", "jurisdiction": "United States federal", "year": "2010", "category": "finance",
     "body": "Financial systemic risk oversight, Consumer Financial Protection Bureau, Volcker Rule framework."},
    {"id": "clean_air_act", "full_name": "Clean Air Act", "jurisdiction": "United States federal", "year": "1963", "category": "environment",
     "body": "National Ambient Air Quality Standards; EPA regulation of stationary and mobile sources."},
    {"id": "clean_water_act", "full_name": "Federal Water Pollution Control Act (Clean Water Act)", "jurisdiction": "United States federal", "year": "1972", "category": "environment",
     "body": "Navigable waters protection; NPDES permits; wetlands jurisdiction (ongoing Sackett litigation framework)."},
    {"id": "national_environmental_policy_act", "full_name": "National Environmental Policy Act", "jurisdiction": "United States federal", "year": "1970", "category": "environment",
     "body": "Environmental Impact Statements for major federal actions."},
    {"id": "endangered_species_act", "full_name": "Endangered Species Act of 1973", "jurisdiction": "United States federal", "year": "1973", "category": "environment",
     "body": "Protection of listed species and critical habitat; Section 7 consultation."},
    {"id": "rico_act", "full_name": "Racketeer Influenced and Corrupt Organizations Act", "jurisdiction": "United States federal", "year": "1970", "category": "criminal",
     "body": "18 United States Code Sections 1961–1968 — enterprise pattern of racketeering; civil treble damages."},
    {"id": "section_1983", "full_name": "42 United States Code Section 1983 — Civil action for deprivation of rights", "jurisdiction": "United States federal", "year": "1871", "category": "civil_rights",
     "body": "Civil suit against state actors under color of law violating federal constitutional or statutory rights."},
    {"id": "section_1988", "full_name": "42 United States Code Section 1988 — Attorneys' fees", "jurisdiction": "United States federal", "year": "1976", "category": "civil_rights",
     "body": "Attorney fee awards to prevailing parties in civil rights actions."},
    {"id": "sherman_act", "full_name": "Sherman Antitrust Act", "jurisdiction": "United States federal", "year": "1890", "category": "antitrust",
     "body": "15 United States Code Sections 1–7 — restraint of trade and monopolization."},
    {"id": "clayton_act", "full_name": "Clayton Antitrust Act", "jurisdiction": "United States federal", "year": "1914", "category": "antitrust",
     "body": "Merger control, price discrimination, interlocking directorates."},
    {"id": "federal_trade_commission_act", "full_name": "Federal Trade Commission Act", "jurisdiction": "United States federal", "year": "1914", "category": "antitrust",
     "body": "Unfair methods of competition; Federal Trade Commission enforcement."},
    {"id": "lanham_act", "full_name": "Lanham Act (Trademark Act of 1946)", "jurisdiction": "United States federal", "year": "1946", "category": "intellectual_property",
     "body": "15 United States Code — trademark registration and infringement; likelihood of confusion."},
    {"id": "copyright_act_1976", "full_name": "Copyright Act of 1976", "jurisdiction": "United States federal", "year": "1976", "category": "intellectual_property",
     "body": "17 United States Code — exclusive rights, fair use Section 107, Digital Millennium Copyright Act amendments."},
    {"id": "patent_act", "full_name": "Patent Act (35 United States Code)", "jurisdiction": "United States federal", "year": "1952", "category": "intellectual_property",
     "body": "Utility, design, plant patents; United States Patent and Trademark Office; America Invents Act first-inventor-to-file."},
    {"id": "defend_trade_secrets_act", "full_name": "Defend Trade Secrets Act of 2016", "jurisdiction": "United States federal", "year": "2016", "category": "intellectual_property",
     "body": "Federal civil cause of action for trade secret misappropriation."},
    {"id": "computer_fraud_abuse_act", "full_name": "Computer Fraud and Abuse Act", "jurisdiction": "United States federal", "year": "1986", "category": "criminal",
     "body": "18 United States Code Section 1030 — unauthorized access to protected computers."},
    {"id": "electronic_communications_privacy_act", "full_name": "Electronic Communications Privacy Act", "jurisdiction": "United States federal", "year": "1986", "category": "privacy",
     "body": "Wiretap Act Title I; Stored Communications Act Title II."},
    {"id": "foreign_corrupt_practices_act", "full_name": "Foreign Corrupt Practices Act", "jurisdiction": "United States federal", "year": "1977", "category": "criminal",
     "body": "Anti-bribery of foreign officials; books and records provisions."},
    {"id": "bank_secrecy_act", "full_name": "Bank Secrecy Act", "jurisdiction": "United States federal", "year": "1970", "category": "finance",
     "body": "Anti-money laundering reporting; Currency Transaction Reports."},
    {"id": "truth_in_lending_act", "full_name": "Truth in Lending Act", "jurisdiction": "United States federal", "year": "1968", "category": "consumer",
     "body": "Consumer credit disclosure; Regulation Z."},
    {"id": "fair_credit_reporting_act", "full_name": "Fair Credit Reporting Act", "jurisdiction": "United States federal", "year": "1970", "category": "consumer",
     "body": "Credit bureau accuracy and consumer access rights."},
    {"id": "fair_debt_collection_practices_act", "full_name": "Fair Debt Collection Practices Act", "jurisdiction": "United States federal", "year": "1977", "category": "consumer",
     "body": "Prohibits abusive debt collection practices."},
    {"id": "real_estate_settlement_procedures_act", "full_name": "Real Estate Settlement Procedures Act", "jurisdiction": "United States federal", "year": "1974", "category": "real_property",
     "body": "Mortgage disclosure; anti-kickback provisions."},
    {"id": "national_labor_relations_act", "full_name": "National Labor Relations Act", "jurisdiction": "United States federal", "year": "1935", "category": "labor",
     "body": "Collective bargaining rights; unfair labor practices; National Labor Relations Board."},
    {"id": "occupational_safety_health_act", "full_name": "Occupational Safety and Health Act of 1970", "jurisdiction": "United States federal", "year": "1970", "category": "labor",
     "body": "Workplace safety standards; Occupational Safety and Health Administration."},
    {"id": "family_medical_leave_act", "full_name": "Family and Medical Leave Act of 1993", "jurisdiction": "United States federal", "year": "1993", "category": "labor",
     "body": "Eligible employee unpaid leave for family and medical reasons."},
    {"id": "immigration_nationality_act", "full_name": "Immigration and Nationality Act", "jurisdiction": "United States federal", "year": "1952", "category": "immigration",
     "body": "8 United States Code — visas, naturalization, removal proceedings."},
    {"id": "administrative_procedure_act", "full_name": "Administrative Procedure Act", "jurisdiction": "United States federal", "year": "1946", "category": "administrative",
     "body": "5 United States Code — rulemaking notice-and-comment; adjudication; judicial review."},
    {"id": "freedom_of_information_act", "full_name": "Freedom of Information Act", "jurisdiction": "United States federal", "year": "1966", "category": "administrative",
     "body": "5 United States Code Section 552 — public access to agency records with exemptions."},
    {"id": "privacy_act_1974", "full_name": "Privacy Act of 1974", "jurisdiction": "United States federal", "year": "1974", "category": "privacy",
     "body": "5 United States Code Section 552a — federal agency maintenance of personal records."},
    {"id": "federal_arbitration_act", "full_name": "Federal Arbitration Act", "jurisdiction": "United States federal", "year": "1925", "category": "procedure",
     "body": "9 United States Code — enforcement of arbitration agreements in commerce."},
    {"id": "habeas_corpus_act", "full_name": "Habeas Corpus Act of 1867", "jurisdiction": "United States federal", "year": "1867", "category": "criminal",
     "body": "28 United States Code Section 2254 — federal review of state custody."},
)

HISTORICAL_LAWS: tuple[dict[str, str | tuple[str, ...]], ...] = (
    {"id": "code_hammurabi", "full_name": "Code of Hammurabi", "jurisdiction": "Babylon", "year": "circa 1754 BCE", "category": "historical",
     "body": "One of the earliest written legal codes — proportional justice ('eye for an eye') on stone stele."},
    {"id": "twelve_tables", "full_name": "Law of the Twelve Tables", "jurisdiction": "Roman Republic", "year": "circa 450 BCE", "category": "historical",
     "body": "Foundation of Roman civil law; published plebeian patrician compromise."},
    {"id": "justinian_code", "full_name": "Corpus Juris Civilis (Justinian Code)", "jurisdiction": "Byzantine Empire", "year": "529–534", "category": "historical",
     "body": "Codification of Roman law — Institutes, Digest, Code, Novels; civil-law tradition root."},
    {"id": "magna_carta", "full_name": "Magna Carta", "jurisdiction": "England", "year": "1215", "category": "historical",
     "body": "Limited royal power; due process ancestor — 'lawful judgment of peers'."},
    {"id": "english_bill_of_rights", "full_name": "English Bill of Rights 1689", "jurisdiction": "England", "year": "1689", "category": "historical",
     "body": "Parliamentary supremacy; no cruel and unusual punishment; petition rights."},
    {"id": "napoleonic_code", "full_name": "Code Napoléon (French Civil Code)", "jurisdiction": "France", "year": "1804", "category": "historical",
     "body": "Influential civil code — contract, property, family law; exported across Europe and Louisiana."},
)

INTERNATIONAL_LAWS: tuple[dict[str, str | tuple[str, ...]], ...] = (
    {"id": "un_charter", "full_name": "Charter of the United Nations", "jurisdiction": "international", "year": "1945", "category": "international",
     "body": "International organization; Security Council; peaceful dispute resolution."},
    {"id": "universal_declaration_human_rights", "full_name": "Universal Declaration of Human Rights", "jurisdiction": "international", "year": "1948", "category": "international",
     "body": "United Nations General Assembly Resolution 217 A — foundational human rights norms."},
    {"id": "geneva_conventions", "full_name": "Geneva Conventions of 1949", "jurisdiction": "international", "year": "1949", "category": "international",
     "body": "Humanitarian law for war wounded, prisoners, civilians."},
    {"id": "rome_statute", "full_name": "Rome Statute of the International Criminal Court", "jurisdiction": "international", "year": "1998", "category": "international",
     "body": "International Criminal Court jurisdiction over genocide, crimes against humanity, war crimes."},
    {"id": "paris_agreement", "full_name": "Paris Agreement under the United Nations Framework Convention on Climate Change", "jurisdiction": "international", "year": "2015", "category": "international",
     "body": "Nationally determined contributions to limit global temperature rise."},
    {"id": "general_data_protection_regulation", "full_name": "Regulation (EU) 2016/679 (General Data Protection Regulation)", "jurisdiction": "European Union", "year": "2016", "category": "privacy",
     "body": "European Union comprehensive data protection regulation."},
)

US_STATE_CODES: tuple[tuple[str, str, str], ...] = (
    ("Alabama", "Code of Alabama", "AL"),
    ("Alaska", "Alaska Statutes", "AK"),
    ("Arizona", "Arizona Revised Statutes", "AZ"),
    ("Arkansas", "Arkansas Code", "AR"),
    ("California", "California Codes", "CA"),
    ("Colorado", "Colorado Revised Statutes", "CO"),
    ("Connecticut", "General Statutes of Connecticut", "CT"),
    ("Delaware", "Delaware Code", "DE"),
    ("Florida", "Florida Statutes", "FL"),
    ("Georgia", "Official Code of Georgia Annotated", "GA"),
    ("Hawaii", "Hawaii Revised Statutes", "HI"),
    ("Idaho", "Idaho Code", "ID"),
    ("Illinois", "Illinois Compiled Statutes", "IL"),
    ("Indiana", "Indiana Code", "IN"),
    ("Iowa", "Iowa Code", "IA"),
    ("Kansas", "Kansas Statutes Annotated", "KS"),
    ("Kentucky", "Kentucky Revised Statutes", "KY"),
    ("Louisiana", "Louisiana Civil Code and Revised Statutes", "LA"),
    ("Maine", "Maine Revised Statutes", "ME"),
    ("Maryland", "Maryland Code", "MD"),
    ("Massachusetts", "General Laws of Massachusetts", "MA"),
    ("Michigan", "Michigan Compiled Laws", "MI"),
    ("Minnesota", "Minnesota Statutes", "MN"),
    ("Mississippi", "Mississippi Code", "MS"),
    ("Missouri", "Missouri Revised Statutes", "MO"),
    ("Montana", "Montana Code Annotated", "MT"),
    ("Nebraska", "Nebraska Revised Statutes", "NE"),
    ("Nevada", "Nevada Revised Statutes", "NV"),
    ("New Hampshire", "New Hampshire Revised Statutes Annotated", "NH"),
    ("New Jersey", "New Jersey Statutes Annotated", "NJ"),
    ("New Mexico", "New Mexico Statutes Annotated", "NM"),
    ("New York", "Consolidated Laws of New York", "NY"),
    ("North Carolina", "General Statutes of North Carolina", "NC"),
    ("North Dakota", "North Dakota Century Code", "ND"),
    ("Ohio", "Ohio Revised Code", "OH"),
    ("Oklahoma", "Oklahoma Statutes", "OK"),
    ("Oregon", "Oregon Revised Statutes", "OR"),
    ("Pennsylvania", "Consolidated Statutes of Pennsylvania", "PA"),
    ("Rhode Island", "General Laws of Rhode Island", "RI"),
    ("South Carolina", "Code of Laws of South Carolina", "SC"),
    ("South Dakota", "South Dakota Codified Laws", "SD"),
    ("Tennessee", "Tennessee Code Annotated", "TN"),
    ("Texas", "Texas Statutes", "TX"),
    ("Utah", "Utah Code", "UT"),
    ("Vermont", "Vermont Statutes Annotated", "VT"),
    ("Virginia", "Code of Virginia", "VA"),
    ("Washington", "Revised Code of Washington", "WA"),
    ("West Virginia", "West Virginia Code", "WV"),
    ("Wisconsin", "Wisconsin Statutes", "WI"),
    ("Wyoming", "Wyoming Statutes", "WY"),
    ("District of Columbia", "District of Columbia Official Code", "DC"),
)

UK_MAJOR_ACTS: tuple[dict[str, str], ...] = (
    {"id": "magna_carta_uk", "full_name": "Magna Carta 1215", "jurisdiction": "United Kingdom", "category": "constitutional"},
    {"id": "bill_of_rights_1689", "full_name": "Bill of Rights 1689", "jurisdiction": "United Kingdom", "category": "constitutional"},
    {"id": "human_rights_act_1998", "full_name": "Human Rights Act 1998", "jurisdiction": "United Kingdom", "category": "human_rights"},
    {"id": "data_protection_act_2018", "full_name": "Data Protection Act 2018", "jurisdiction": "United Kingdom", "category": "privacy"},
    {"id": "equality_act_2010", "full_name": "Equality Act 2010", "jurisdiction": "United Kingdom", "category": "civil_rights"},
)


def iter_us_code_titles() -> Iterator[dict]:
    for num, name in US_CODE_TITLES:
        yield {
            "id": f"usc_title_{num:02d}",
            "full_name": f"Title {num} of the United States Code — {name}",
            "jurisdiction": "United States federal",
            "category": "united_states_code",
            "year": "ongoing",
            "tags": ("united states code", "usc", name.lower(), f"title {num}"),
            "body": f"Title {num} of the United States Code codifies federal law on {name}. "
            f"Published by the Office of the Law Revision Counsel. Supersedes conflicting prior statutes in this title.",
        }


def iter_state_codes() -> Iterator[dict]:
    for state, code_name, abbr in US_STATE_CODES:
        yield {
            "id": f"state_{abbr.lower()}",
            "full_name": f"{code_name} — State of {state}",
            "jurisdiction": f"State of {state}",
            "category": "state_code",
            "year": "ongoing",
            "tags": (state.lower(), abbr.lower(), "state law", code_name.lower()),
            "body": f"The {code_name} is the codified statutory law of the State of {state}. "
            f"Interpreted by the {state} state courts; constitution of {state} is supreme within state matters.",
        }


def iter_all_statutes() -> Iterator[dict]:
    for entry in iter_us_code_titles():
        yield entry
    for entry in MAJOR_FEDERAL_STATUTES:
        row = dict(entry)
        row.setdefault("tags", (str(row.get("category", "")), str(row.get("jurisdiction", ""))))
        yield row
    for entry in HISTORICAL_LAWS:
        row = dict(entry)
        row.setdefault("tags", ("historical", str(row.get("jurisdiction", ""))))
        yield row
    for entry in INTERNATIONAL_LAWS:
        row = dict(entry)
        row.setdefault("tags", ("international", str(row.get("category", ""))))
        yield row
    for entry in iter_state_codes():
        yield entry
    for entry in UK_MAJOR_ACTS:
        yield {
            "id": entry["id"],
            "full_name": entry["full_name"],
            "jurisdiction": entry["jurisdiction"],
            "category": entry["category"],
            "year": "varies",
            "tags": ("united kingdom", entry["category"]),
            "body": f"{entry['full_name']} — primary legislation of the United Kingdom.",
        }


def catalog_count() -> int:
    return sum(1 for _ in iter_all_statutes())


def catalog_by_category() -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in iter_all_statutes():
        cat = str(row.get("category", "other"))
        counts[cat] = counts.get(cat, 0) + 1
    return counts