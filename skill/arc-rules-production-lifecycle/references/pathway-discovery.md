# Pathway Discovery

Run only after the target Rule text/version is source-closed enough for the intended candidate work.

Discovery is no-write for production semantics. Identify candidate:

- trigger/event;
- actor;
- prerequisite;
- timing/deadline;
- threshold/condition;
- mandatory vs discretionary consequence;
- exception/rebuttal;
- companion Rule dependency;
- evidentiary/admissibility/use gate;
- remedy/procedural result;
- downstream procedural step;
- recurring interpretive issue;
- contrary or limiting authority question.

Keep only pathways that materially change the legal answer, safe formulation, remedy, admissibility/use route, source-material treatment, or authority status. Record discarded hypotheses and reasons.

Candidate packets remain nonproduction and must pass the bundled packet validator before handoff.


## Candidate contract authority

Use `pathway-candidate-packet-schema.json` for structural shape and `scripts/pathway-discovery/scripts/validate_candidate_packet.py` as the operational acceptance validator. Keep them aligned. A `RULE_TEXT_ONLY` pathway may use an empty `case_ladder` only when it carries exact `source_proof_spans`; `CASE_INTERPRETIVE` remains case-backed.
