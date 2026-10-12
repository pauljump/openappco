# Slipway: notes for coding agents

- To **use** Slipway on an app, follow [skills/slipway/SKILL.md](skills/slipway/SKILL.md).
- To **change** Slipway:
  - Keep `tools/slipway.py` standard-library only. `check` and `status` must stay offline and
    read-only. `doctor` must only run read-only local commands, plus one read-only API call when
    `--api` is passed.
  - Run `python3 -m unittest discover -s tests -v` after any change to it.
  - Every Apple-specific claim needs a date and a link.
  - No personal details, account identifiers or real app IDs. Use `example.com`, `com.example.*`
    and `[PLACEHOLDERS]`.
  - Write like a person who has done this: say the point first, keep it short, and say what
    actually happened.
