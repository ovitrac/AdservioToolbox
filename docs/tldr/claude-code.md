# tldr: Claude Code

## Launch & Session

```
claude                          # start interactive session
claude "prompt"                 # start with initial prompt
claude -p "prompt"              # non-interactive (print and exit)
claude -p --output-format json "prompt"  # JSON output
claude -c                       # continue most recent session
claude -c -p "follow-up"       # continue non-interactively
claude --resume                 # resume last session
claude --resume <id>            # resume specific session
claude --max-turns 3 -p "task" # limit agentic turns
claude --model sonnet           # select model (sonnet, opus, haiku)
claude --add-dir ../lib         # add working directories
claude --version                # show version
claude update                   # update CLI
claude doctor                   # check installation health
```

## Keyboard Shortcuts

```
Enter                           # accept / send
Shift+Enter or \                # multi-line input
Tab                             # auto-complete
Ctrl+C                          # cancel current operation
Ctrl+D                          # exit session
Esc                             # interrupt Claude
Esc Esc                         # rewind menu (undo changes)
Ctrl+R                          # full output / context
Ctrl+V                          # paste image
@                               # mention files/folders
!                               # bash mode prefix
```

## Slash Commands (Built-in)

```
/help                           # show available commands
/clear                          # clear context
/compact [hint]                 # compress context
/exit                           # end session
/config                         # view/modify configuration
/model                          # switch AI model
/memory                         # edit CLAUDE.md
/permissions                    # update tool permissions
/status                         # view account/usage
/cost                           # session cost and duration
/doctor                         # check health
/review                         # request code review
/init                           # initialize CLAUDE.md
/add-dir                        # add working directories
/mcp                            # manage MCP servers
/rewind                         # undo changes (= Esc Esc)
/vim                            # enter vim mode
/bug                            # report bug
```

## Configuration

```
claude config list              # view all settings
claude config get <key>         # check specific setting
claude config set <key> <val>   # change setting
claude config add <key> <val>   # push to array
claude config remove <key> <val>  # remove from array
```

## MCP Servers

```
claude mcp add <name> <cmd> [args]       # add stdio server
claude mcp add --transport sse <n> <url> # add SSE server
claude mcp list                          # show installed
claude mcp remove <name>                 # remove server
```

## Piping

```
cat file | claude -p "explain"
git diff | claude -p "review"
git log --oneline | claude -p "summarize"
```

## Slash Commands (Adservio Toolbox)

```
/cheat [1|2|3]                  # leveled cheat sheet
/tldr [topic]                   # concise reference
/eco [on|off]                   # eco mode toggle
/why <topic>                    # rationale explainer
/how <task>                     # step-by-step guide
```

**Settings priority:** Enterprise > `.claude/settings.local.json` > `.claude/settings.json` > `~/.claude/settings.json`
**Custom commands:** `.claude/commands/*.md` (team) or `~/.claude/commands/*.md` (personal)
**Hooks:** `.claude/hooks/*.sh` — events: SessionStart, SessionEnd, UserPromptSubmit, PreToolUse, PostToolUse, Stop, PreCompact
