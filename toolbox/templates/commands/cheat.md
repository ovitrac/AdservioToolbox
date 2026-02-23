Display the Adservio Toolbox cheat sheet.

Arguments: $ARGUMENTS

Instructions:
1. Parse the argument. Accept: L1, L2, L3, 1, 2, 3, or a topic keyword. Default to L1 if empty.
2. Map the level:
   - L1 / 1 / empty → read file `docs/cheat/L1.md`
   - L2 / 2 → read file `docs/cheat/L2.md`
   - L3 / 3 → read file `docs/cheat/L3.md`
   - Any other keyword → search all three files for sections matching the keyword
3. Read the target file from the repository root.
4. Present the **full content** of the file — do not summarize or truncate.
5. Use the same formatting (tables, code blocks, headers) as the source file.
6. If a keyword search matches multiple sections, present all matches with their source level.

Levels:
- **L1**: Daily essentials — the commands and shortcuts you use every day
- **L2**: Workflows — eco mode, memctl, CloakMCP, safe RAG patterns
- **L3**: Advanced — MCP internals, policies, hooks, tokenizers
