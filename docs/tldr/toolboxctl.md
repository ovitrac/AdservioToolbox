# tldr: toolboxctl

```
toolboxctl install              # install memctl + CloakMCP
toolboxctl install --fts en     # install with English FTS tokenizer
toolboxctl install --upgrade    # force upgrade packages
toolboxctl install --global     # wire Claude Code globally (hooks + permissions + CLAUDE.md)
toolboxctl install --uninstall  # remove global wiring

toolboxctl init                 # wire .claude/commands/ + create config (minimal profile)
toolboxctl init --force         # overwrite existing files
toolboxctl init --fts en        # set FTS language in config
toolboxctl init --profile dev   # dev profile (+ .claude/PROJECT.md)
toolboxctl init --profile playground  # playground profile (+ CHALLENGE.md pointer)

toolboxctl status               # show component status table
toolboxctl doctor               # diagnostic check (Python, pipx, hooks, PATH, permissions)
toolboxctl doctor --strict      # lint warnings become errors (exit 2)
toolboxctl doctor --ci          # alias for --strict

toolboxctl eco                  # show current eco mode state
toolboxctl eco on               # enable eco mode globally
toolboxctl eco off              # disable eco mode globally

toolboxctl env                  # print export KEY=VALUE lines
toolboxctl env --json           # print as JSON dict
eval "$(toolboxctl env)"        # inject config into shell

toolboxctl playground           # create .playground/ with smoke tests
toolboxctl playground --clean   # remove .playground/

toolboxctl rescue               # diagnose + guided recovery
toolboxctl rescue --dir ./proj  # target specific directory
toolboxctl rescue --dry-run     # preview without changes
toolboxctl rescue --from-backup # list available backups
toolboxctl rescue --from-backup 20260224_143000  # restore specific backup
toolboxctl rescue --force       # skip confirmation prompts
toolboxctl rescue --with-memory      # include memory health advisory
toolboxctl rescue --memory-only      # memory checks only (skip secrets)
toolboxctl rescue --json             # combined JSON output
toolboxctl rescue --json --with-memory  # full diagnostic as JSON

toolboxctl update               # upgrade all tools (pipx/pip auto-detected)
toolboxctl update --check       # show outdated packages
toolboxctl update --quiet       # minimal output (for launchers)
toolboxctl update --json        # machine-readable output
toolboxctl update --global      # refresh global CLAUDE.md block only
toolboxctl update --project     # refresh project CLAUDE.md block only

toolboxctl deinit               # remove toolbox wiring (preserves .memory/)
toolboxctl deinit --force       # skip confirmation prompt

toolboxctl --version            # show version
toolboxctl --help               # show help
```

## Per-project setup (standalone script)

```
bash scripts/playground.sh                      # setup in cwd
bash scripts/playground.sh --dir ~/proj         # specific directory
bash scripts/playground.sh --hardened           # enterprise CloakMCP profile
bash scripts/playground.sh --skip-hooks         # init + CLAUDE.md only
bash scripts/playground.sh --teardown           # remove wiring
bash scripts/playground.sh --dry-run            # preview
```
