Provide step-by-step operational instructions for a task.

Arguments: $ARGUMENTS

Instructions:
1. Parse the argument as a task description (e.g., "install", "init", "enable eco", "sanitize secrets", "first session", "playground").
2. Search the following documentation files for relevant procedures:
   - `docs/workflows/first-session.md`
   - `docs/cheat/L1.md`, `docs/cheat/L2.md`, `docs/cheat/L3.md`
   - `docs/tldr/toolboxctl.md`
   - `README.md`
3. Construct a step-by-step answer with:
   - **Goal**: what the task achieves
   - **Prerequisites**: what must be in place
   - **Steps**: numbered, with exact commands (copy-paste ready)
   - **Verification**: how to confirm success
   - **Troubleshooting**: common issues and fixes (if applicable)
4. Prefer commands from `toolboxctl` when available.
5. If the task is not covered in documentation, explain what you know and suggest checking `toolboxctl --help`.
