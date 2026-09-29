# Validation Report

skill: arc-subrule-pathway-discovery
version: v1.1.0
status: passed local release self-test

## Commands run

```bash
python scripts/self_test.py
```

## Result

```json
{
  "tests_run": 11,
  "passed": 11,
  "failed": []
}
```

## Scope

This validation confirms bundled scripts run against packaged fixtures, bad fixtures fail as expected, relationship allowlist checks work, and the no-write ledger verifier accepts a no-write sample. It does not verify current law, public case treatment, or live LexGraph connectivity.

## Required manual checks before filing or graph writes

- public rule-text verification;
- public case paragraph pin verification;
- current-status / negative-treatment checks;
- exact LexGraph rule and case UIDs;
- duplicate/stub node review;
- expected update counts;
- rollback plan;
- human approval.
