Display a concise tldr-style reference card.

Arguments: $ARGUMENTS

Instructions:
1. Parse the argument. Accept one of: claude-code, toolboxctl, memctl, cloakmcp, eco. Default to toolboxctl if empty.
2. Read the corresponding file from `docs/tldr/{topic}.md` in the repository root.
3. Present the **full content** verbatim — do not summarize.
4. If the topic is not found, list available topics from the `docs/tldr/` directory.

Available topics:
- **claude-code**: Claude Code essentials
- **toolboxctl**: toolboxctl subcommands
- **memctl**: memctl CLI reference
- **cloakmcp**: cloak CLI reference
- **eco**: eco mode reference
