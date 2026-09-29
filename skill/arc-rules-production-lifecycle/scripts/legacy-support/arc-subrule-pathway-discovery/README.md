# ARC Subrule Pathway Discovery

This Skill creates no-write candidate pathway artifacts for Alberta Rules of Court rule/subrule analysis. It helps produce pathway reports, graph candidate packets, manual validation ledgers, discard ledgers, conflict matrices, and no-write run ledgers.

It does not perform graph writes and does not make legal conclusions filing-ready. Public rule/case verification, paragraph pins, current-status checks, exact IDs, rollback planning, and human approval remain mandatory before graph writes or filed use.

## Common commands

```bash
python scripts/self_test.py
python scripts/build_rule_workspace.py --rule 5.33 --base-dir /mnt/data/arc_pathway_pilot
python scripts/validate_candidate_packet.py path/to/packet.json
python scripts/package_rule_outputs.py --rule-dir path/to/rule_dir --out path/to/rule_package.zip
```
