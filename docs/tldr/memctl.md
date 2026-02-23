# tldr: memctl

```
memctl init                     # initialize memory workspace (.memory/)
memctl init --fts-tokenizer en  # initialize with English tokenizer

memctl push "query"             # recall context matching query
memctl push "q" --source dir/   # ingest files + recall in one shot
memctl push "q" --budget 1000   # limit token budget
memctl push "q" --tier mtm      # filter by tier

echo "text" | memctl pull       # store stdin as note
memctl pull --title "note name" # store with title
memctl pull --tags "a,b"        # store with tags

memctl search "query"           # FTS5 search
memctl search "q" --tier ltm    # search specific tier
memctl search "q" -k 5          # limit results

memctl show <id>                # show item details
memctl stats                    # store statistics
memctl stats --json             # machine-readable stats

memctl export                   # export as JSONL to stdout
memctl import                   # import JSONL from stdin

memctl consolidate              # run deterministic consolidation
memctl reindex                  # rebuild FTS5 index
memctl reindex --fts-tokenizer en  # rebuild with new tokenizer

memctl serve                    # start MCP server
memctl serve --check            # verify server can start, then exit
memctl serve --db-root .memory  # start with explicit db root
```

**Installer scripts** (bundled in PyPI wheel, locate via `memctl scripts-path`):
```
bash "$(memctl scripts-path)/install_mcp.sh"                     # register MCP server (Claude Code)
bash "$(memctl scripts-path)/install_mcp.sh" --client claude-desktop  # register for Claude Desktop
bash "$(memctl scripts-path)/install_mcp.sh" --client all --yes  # both clients
bash "$(memctl scripts-path)/install_mcp.sh" --dry-run           # preview changes

bash "$(memctl scripts-path)/install_eco.sh" --db-root .memory   # install eco mode (hook + strategy + /eco)
bash "$(memctl scripts-path)/install_eco.sh" --dry-run           # preview changes
bash "$(memctl scripts-path)/install_eco.sh" --yes --force       # non-interactive, overwrite existing

bash "$(memctl scripts-path)/install_claude_hooks.sh"            # install safety guard + audit logger hooks
bash "$(memctl scripts-path)/install_claude_hooks.sh" --dry-run  # preview changes
```

**Uninstaller scripts**:
```
bash "$(memctl scripts-path)/uninstall_mcp.sh"                   # remove MCP config + hooks
bash "$(memctl scripts-path)/uninstall_mcp.sh" --hooks-only      # remove hooks only
bash "$(memctl scripts-path)/uninstall_mcp.sh" --mcp-only        # remove MCP config only
bash "$(memctl scripts-path)/uninstall_mcp.sh" --dry-run         # preview changes

bash "$(memctl scripts-path)/uninstall_eco.sh"                   # remove eco mode (preserves .memory/)
bash "$(memctl scripts-path)/uninstall_eco.sh" --dry-run         # preview changes
```

**Tiers:** stm (short-term) → mtm (medium-term) → ltm (long-term)
**Database:** `.memory/memory.db` (SQLite + FTS5)
**Config:** `.memory/config.json` (auto-detected beside database)
