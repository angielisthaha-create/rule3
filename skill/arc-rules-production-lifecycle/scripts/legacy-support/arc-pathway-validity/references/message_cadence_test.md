# Unified Message Cadence Test

Use this when the user wants a unified message every 4 minutes for 100 occurrences to test the setup.

## Preferred model: manual user-triggered cadence

If the user says they will input a message every 4 minutes, use the interactive protocol. The user sends each trigger; ChatGPT runs the next read-only database test slice on receipt.

Default trigger:

```text
ARC_PATHWAY_VALIDITY_TEST seq=001/100 run_id=<run_id>
```

See `references/interactive_100_turn_protocol.md` for the per-turn schedule.

## Optional local message generator

A ChatGPT skill file cannot by itself schedule background delivery. The bundled script can generate the 100 exact trigger messages for the user to paste or can emit them locally to stdout.

Default cadence:

```text
count = 100
interval = 240 seconds
elapsed wall time in real-time mode = 400 minutes = 6 hours 40 minutes
```

Dry run:

```bash
python scripts/unified_message_burst.py \
  --dry-run \
  --count 100 \
  --interval-seconds 240 \
  --message "ARC pathway validity unified setup test" \
  --out-jsonl out/unified_message_test/messages.jsonl \
  --out-text out/unified_message_test/messages.txt
```

Real-time local emission:

```bash
python scripts/unified_message_burst.py \
  --real-time \
  --count 100 \
  --interval-seconds 240 \
  --message "ARC pathway validity unified setup test" \
  --out-jsonl out/unified_message_test/messages.jsonl \
  --out-text out/unified_message_test/messages.txt
```

The script emits to stdout and optional files. It does not send SMS, email, Slack, or connector messages by itself.
