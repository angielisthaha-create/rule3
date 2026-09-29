SCRATCH - EVERYTHING FROM THE SESSION SCRATCHPAD, KEPT SO NOTHING HAS TO BE RE-CREATED
===================================================================================

The session scratchpad (/tmp/.../scratchpad) is deleted when the cloud container ends. Its contents are here
or already elsewhere in the repository:

  scratchpad file                         where it is now
  --------------------------------------  -----------------------------------------------------------------
  rule2_part01_document.pretty.json       scratch/reading_copies/ (BOOK_B, pretty-printed, same content)
  rule2_part02_document.pretty.json       scratch/reading_copies/ (BOOK_B, pretty-printed, same content)
  c1.json                                 scratch/reading_copies/81-100_2_1 to 2_27.pretty.json (BOOK_C)
  c2.json                                 scratch/reading_copies/101-120_2_28 to 3_18.pretty.json (BOOK_C)
  arc.pdf                                 "Alberta rule of court.pdf" at the repo root (identical;
                                          sha256 6058edb4e0c56a434c9468487174fb453e7505c212576866ee5f0fd1855085fe)
  skill.zip                               "skill (4).zip" at the repo root (identical;
                                          sha256 a05d2a0c9354a38e874e90bf8663bcd6c189b295cd173793ea825e4fea7ced98)
  skill/arc-rules-production-lifecycle/   skill/arc-rules-production-lifecycle/ (identical, 114 files)
  g.json                                  not kept: a temporary copy of one gate record, rewritten on every
                                          validation (gate_all in tools/qa_display_helpers.sh makes its own)
  show.py (in /tmp/claude-0)              tools/show_rule_notes.py
  p2refs.txt, p2refs2.txt (/tmp/claude-0) scratch/pass8_reference_lists/ (output of tools/extract_note_refs.py
                                          as it was during the 8th pass; each line was checked by hand)

Reading copies: the repository's JSON sources are the originals; these copies only add indentation so a
person can read them. Line numbers quoted in notes (e.g. "101-120 json line 693") refer to the ORIGINAL files,
not to these copies. Regenerate with:  source tools/qa_display_helpers.sh; pretty_sources

One-off commands typed during the passes (search, display, insertion) are now the functions in
tools/qa_display_helpers.sh and the commands in tools/edit_helpers.py; see WORKFLOW.txt section 7.
