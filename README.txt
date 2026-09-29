ALBERTA RULES OF COURT - THREE-BOOK RECONCILIATION (HANDOVER README)
=====================================================================

Read this file first. Then read rule2_subrules/WORKFLOW.txt (the method and QA checklists) and
rule2_subrules/REVIEW_NOTES.txt (what was found, rule by rule). Those two files are the project's memory.

1. WHAT THIS PROJECT IS
   Each subrule of the Alberta Rules of Court is reconciled across the official text and three annotated
   books into ONE JSON file per subrule. The official text controls. The books add information notes,
   related provisions, commentary and cases. Redundancy is removed without losing information, and garbled
   content that adds nothing is dropped, always with a one-line note saying what was dropped and why.
   Method: skill "arc-rules-production-lifecycle", mode SOURCE_RECONCILIATION (no graph writes).
   Done so far: Part 2 (rules 2.1 - 2.32), eight manual passes; see WORKFLOW section 5.
   Part 3 (rules 3.1 - 3.77): all four sources are in the repo and the builder has run (section 11); no manual pass yet.
   Next: Part 3 Pass 1, then other Parts (see section 6).

2. FILES
   Alberta_Rules_of_Court.txt        OFFICIAL - whole Rules incl. forms and Appendix definitions (controls)
   combined_rule2.txt                BOOK_A, Part 2 (page markers: a line "2-NN" at the top of each page)
   "combined rule1.txt", "combined rule3.txt", combined_rule4..13.txt, "combined rule14.txt",
   "combined rule15.txt"             BOOK_A, other Parts (full book, uploaded by the user; note the spaces in
                                     some file names). Page markers: "N-NN" lines, EXCEPT Part 3, which opens
                                     every page with "**PAGE N" (then the "3-N" running head).
   rule2_part01_document.json, rule2_part02_document.json   BOOK_B (Fradsham), Part 2 only
   "81-100_2_1 to 2_27.json", "101-120_2_28 to 3_18.json"   BOOK_C pp. 81-120 (badly extracted; also
                                     holds the first Part 3 pages)
   tools/build_rule2_reconciliation.py   builder; holds ALL manual decisions in its MANUAL_* tables
   tools/validate_three_book_gate.py     gate validator (copy of the skill's script; standard library only)
   tools/qa_display_helpers.sh           display-only shell helpers used in the passes (gate_all, pg, pg3,
                                         rule_at, reverse_refs, ref_pages, official, official_title, fn_pages,
                                         wrapped_refs, related_labels, book_count, pretty_sources). They FIND
                                         text; you decide.
   tools/show_rule_notes.py              prints a rule's see_also and every flag/note for reading
   tools/extract_note_refs.py            lists every page/line reference in the notes, to check by hand
   tools/edit_helpers.py                 records decisions (see-also, replace, review-line, status); refuses
                                         if its anchor text is not unique
   scratch/                              everything that was in the session scratchpad (reading copies of
                                         Books B and C, 8th-pass reference lists) - see scratch/README.txt
   "Alberta rule of court.pdf"           King's Printer PDF the official .txt came from (builder hashes it)
   "skill (4).zip"                       the arc-rules-production-lifecycle skill as supplied by the user
   skill/arc-rules-production-lifecycle/ the same skill unzipped (identical, 114 files): read SKILL.md and
                                         references/ for the SOURCE_RECONCILIATION mode and gate schema
   rule2_subrules/2.N.json           output, one per subrule; rule2_subrules/_index.json shared registry
   rule2_subrules/WORKFLOW.txt       method, checklists 3A/3B/3C, pass findings (4A), STATUS, open items,
                                     tools (section 7)
   rule2_subrules/REVIEW_NOTES.txt   per-rule log: "[2nd pass]" ... "[7th pass, full Book A]" lines

3. HOW TO BUILD AND VALIDATE
   source tools/qa_display_helpers.sh; python3 tools/build_rule2_reconciliation.py; gate_all   (all 32 true)
   Or by hand:
   python3 tools/build_rule2_reconciliation.py
   for r in 2.1 2.2 ...; do
     python3 -c "import json;json.dump(json.load(open('rule2_subrules/$r.json'))['three_book_gate'],open('/tmp/g.json','w'))"
     python3 tools/validate_three_book_gate.py /tmp/g.json      # must print "valid": true
   done
   Never edit rule2_subrules/*.json by hand: a rebuild overwrites them. Put every decision in the builder's
   manual tables so each rebuild repeats it.

4. THE MANUAL TABLES (tools/build_rule2_reconciliation.py) - record decisions with tools/edit_helpers.py
   MANUAL_BOOK_C       per rule: drop_rule_text, drop_citations, drop_one_citation, drop_commentary,
                       drop_c_note, citation_names, citation_notes, add_citations, keep_citations_note,
                       commentary_flag, amendment_note_flag, ...
   MANUAL_TEXT_NOTES   Book A/B rule text whose differences from the official text are editorial only
   MANUAL_SEE_ALSO     cross-references (other rules, other Parts, other books, official rules by subject)
   MANUAL_BOOK_A_COMMENTARY_FLAGS / MANUAL_BOOK_A_FOOTNOTE_FLAGS / MANUAL_NOTE_FLAGS   flags (not corrections)
   To add a see_also entry at the top of a rule's list, insert after the line '    "2.x": ['.

5. NON-NEGOTIABLE RULES (from the user)
   - Checking is MANUAL: one subrule at a time, no shortcut, no script deciding anything. Scripts may only
     build, display and insert text. Read the sources yourself.
   - The official text controls; no majority vote between books; no silent merge; every drop leaves a note.
   - Notes state evidence (book, page, footnote, quoted words), never guesses. Never write "unrelated" or
     "uncited" without saying which files were searched.
   - Git: work on the branch you are given; commit messages name the rules and the pass; no PR unless asked.
   - User preference: keep replies short; plain .txt files.

6. HOW TO START ANOTHER PART (e.g. Part 3)
   a. Copy the builder to tools/build_ruleN_reconciliation.py; change RULES, BOOK_A/B/C paths, OUT_DIR,
      and adapt the parsers (parse_book_a/b/c) to the new files. Book B and Book C for the new Part must
      be supplied by the user (only Part 2 of Book B and pp. 81-120 of Book C are in the repo).
   b. Build, then follow WORKFLOW section 6A (pass plan: full read, verification, confirmation; stopping rule;
      write-after-search rule), doing Steps 2-8 for each rule with checklists 3A, 3B and 3C.
   c. Book C pattern: displaced citations sit where a lost number should be (e.g. a case name where
      "Form 3" or "10" belonged). Keep a list of displaced cases; they turn up again in their home rule
      (Part 3 venue cases Shell v. Sunterra and Genstar were already seen in 2.28/2.29).
   d. With the full Book A, search EVERY Part for references to the rule ("R.N.x", "Rr.N.x", "Rule N.x",
      "rule N.x [Title]", bare related-provision labels "N.x (label)", and line-wrapped forms), check the
      page of each hit against the page markers, and check the label/subject matches the official title.

7. LESSONS THAT CAUGHT REAL ERRORS (re-check these first; full list: WORKFLOW checklists 3B and 3C)
   - Re-add any count and re-check every page reference each pass (2.24: 107 written, 106 real).
   - Count a printed oddity across the whole book before calling it a defect ('(#_)' = Book A convention).
   - Read related-provision labels against the official text, not only the title (3.36(2)).
   - Page numbers: use the marker rules in section 2. The 6th pass mis-paged Part 3 by one (fixed in the
     7th pass) because it treated the "3-N" line as the end of a page.
   - Pointers in Book A can be mis-aimed (e.g. R.8.8 "R.2.4n" = R.2.24n; R.10.32 lists "2.61" = 2.6;
     R.11.15 "2.3" = 11.3). Check the subject, not only that the target exists.
   - Search the official text for form headings with subrules ("[Rule 2.14(1)(b)]"), Division headings,
     and the Appendix definitions.
   - Compare any rule text a book quotes word for word with the official text.
   - A book statement about the law must be read against the official rule it describes.

8. OPEN ITEMS (full list: WORKFLOW.txt section 5)
   - Gauchier 2014 ABCA (Book C 2.10): number lost; the full Book A has no 2014 ABCA Gauchier.
   - Book A wrong-reference flags need a human's judgment (listed in WORKFLOW).
   - Book A / Book C titles and editions are not stated in their files.
   - Print vs extraction typos need the PDF pages.
   - Book B's pointer "Costs for Intervenors under Rule 10.31" (2.10) is unverified (no full Book B).

9. BUILDER ANATOMY AND OUTPUT FORMAT (read before adapting the builder to another Part)
   tools/build_rule2_reconciliation.py, top to bottom:
   - Paths and RULES (2.1 - 2.32); OUT_DIR = rule2_subrules/.
   - norm_strict / norm_editorial / compare: wording comparison of each book's rule text with the official text
     (status EXACT_MATCH, NORMALIZATION_ONLY_DIFFERENCE, WORDING_DIFFERENCE, CARRIER_HAS_EXTRA_TEXT,
     CARRIER_MISSING_TEXT or CARRIER_TEXT_MISSING, plus a similarity score). A status is a hint, never a pass.
   - parse_official: the second "Part 2" heading to the second "Part 3" heading of Alberta_Rules_of_Court.txt
     (the first ones are the table of contents); strips running headers; reads each rule's title, text and
     amending regulations.
   - parse_book_a: page = last "2-NN" line; "Footnote" starts a footnote block; running heads
     ("R.2.x PART 2: ..." / "PART 2: ... R.2.x") are dropped; splits into rule text, information note,
     related provisions, commentary and footnotes (page + number). For another Part change the "2-" patterns
     and the running-head text; Part 3's file uses "**PAGE N" markers instead (see section 2).
   - parse_book_b: Fradsham JSON, document_structure.paragraphs; a rule starts at a paragraph matching
     "Alberta Rules of Court (§ )2.x (YEAR)".
   - parse_book_c: Book C JSON, "hierarchy" of headings -> rules (and "orphan_rule" items); citations and
     commentary per rule. Expect garbling (see WORKFLOW 3A/3B on Book C).
   - MANUAL_* tables (section 4): every human decision; applied after parsing.
   - dedupe: drops a value only when an equal value (under the normalization profile) is kept; logs each drop.
   - main: builds one packet per rule and the three_book_gate record (schema arc-three-book-gate-v1:
     source_registry_sha256 over the source files, normalization_profile sha256, carriers with artifact and
     text sha256, version_identity), writes rule2_subrules/2.N.json and _index.json.
   The build is deterministic: rebuilding changes nothing except _index.json "generated_utc" (checked after the
   8th pass). Use that as the first test that your environment reproduces this work.

   Output file rule2_subrules/2.N.json - top-level keys:
     index, rule, title {official, variants}, division {number, heading},
     operative_text {controlling (official text), controlling_carrier, sha256},
     amendment_history {official, amending_regulations, carrier_notes, crosscheck_vs_official},
     sources {OFFICIAL, BOOK_A {title, related_provisions, commentary, footnotes[{page, number, text,
       review_flag?}], commentary_review_flag?, locator, operative_text_note}, BOOK_B {commentary,
       paragraph_ids, ...}, BOOK_C {citations, commentary, misattributed_entries, dropped_citation_notes?,
       division_heading_flag?, ...}},
     comparison_vs_official {BOOK_A|B|C: status, similarity, version_identity},
     three_book_gate {...}, information_notes, see_also [...], dedupe_log.

10. TAKING OVER (first steps for a new LLM)
   1. Read this README, then WORKFLOW.txt in full (sections 3, 3A-3C, 5, 6A), then skill/.../SKILL.md.
   2. Reproduce: python3 tools/build_rule2_reconciliation.py; git status must show only _index.json changed
      (generated_utc); source tools/qa_display_helpers.sh; gate_all -> 32 x "valid": true.
   3. Read two finished rules end to end (python3 tools/show_rule_notes.py --full 10 24) with their
      REVIEW_NOTES blocks, to see the expected level of detail.
   4. For a new Part: collect ALL sources first (WORKFLOW 6A), adapt the builder (section 9), then follow the
      pass plan in WORKFLOW 6A.
   5. Calibration (optional, recommended): run the pass plan blind on a few Part 2 rules and compare the
      findings with REVIEW_NOTES.txt, which is the answer key for Part 2 after 8 passes. Anything missed
      points to a checklist line that needs to be clearer.

11. PART 3 (started 2026-09-28) - read rule3_subrules/WORKFLOW.txt
   Builder:  python3 tools/build_rule3_reconciliation.py   -> rule3_subrules/3.N.json + _index.json
   Validate: source tools/qa_display_helpers.sh; gate_all3   (all 77 true)
   Helpers:  ARC_PART=3 python3 tools/show_rule_notes.py 2 | extract_note_refs.py | edit_helpers.py ...
   Sources:  official Alberta_Rules_of_Court.txt; Book A "combined rule3.txt" (pages 3-4 to 3-246; rule 3.1 absent);
             Book B rule3_part01..10_document.json (also in the repo now: Parts 1 and 4-15 of Book B, files rule1_*, rule4_* ...);
             Book C 101-120 ... 161-180 JSON files (rule 3.10 absent). All other 121-740 Book C files cover Parts 3-15.
   Not Part 3 sources: second_book.zip (Book C again), rule3.*.json in the root (graph blueprints).
   Known limits of the Book A Part 3 extraction (spaces dropped, footnotes not split, columns out of order) are listed in
   rule3_subrules/WORKFLOW.txt. Expect many WORDING_DIFFERENCE hints for Book A; they are extraction noise until read by hand.
