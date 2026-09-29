# Pathway Validity

Validate each candidate against the source-closed Rule/subrule/version, related subrules, prerequisite logic, exceptions, procedural context, and contrary/limiting authority.

Do not use live `UnifiedRule.text` as an independent source-of-truth shortcut. It may support validation only after the governing source/text gate has established that the live text is source-faithful for the target version.

For each pathway ask:

1. Is the Rule/subrule anchor exact and unique?
2. Is the trigger explicit?
3. Is the actor identified?
4. Are timing/deadline terms captured when present?
5. Are prerequisites and thresholds explicit?
6. Is mandatory/discretionary character correctly represented?
7. Are exceptions, rebuttals, blockers, and companion Rule dependencies preserved?
8. Is the remedy/procedural consequence supported?
9. Is any formulation broader than the Rule text or authority actually supports?
10. Is the authority grade honest and current-status uncertainty explicit?
11. Does contrary/limiting authority change the safe formulation?
12. Does the candidate require human legal review before any higher-use claim?

Use dispositions such as `VALIDATED_CANDIDATE`, `ACCURATE_BUT_INCOMPLETE`, `OVERBROAD`, `UNDER_SPECIFIED`, `WRONG_ANCHOR`, `SOURCE_TEXT_MISMATCH`, `AUTHORITY_HOLD`, `MANUAL_BLOCKER`, and `DISCARD_NOT_INTERPRETIVE`.
