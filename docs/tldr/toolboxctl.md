# tldr: toolboxctl

```
toolboxctl install              # install memctl + CloakMCP
toolboxctl install --fts en     # install with English FTS tokenizer
toolboxctl install --upgrade    # force upgrade packages
toolboxctl install --global     # wire Claude Code globally (hooks + permissions + CLAUDE.md)
toolboxctl install --uninstall  # remove global wiring

toolboxctl init                 # wire .claude/commands/ + create config
toolboxctl init --force         # overwrite existing files
toolboxctl init --fts en        # set FTS language in config

toolboxctl status               # show component status table
toolboxctl doctor               # diagnostic check (Python, pipx, hooks, PATH, permissions)

toolboxctl eco                  # show current eco mode state
toolboxctl eco on               # enable eco mode globally
toolboxctl eco off              # disable eco mode globally

toolboxctl env                  # print export KEY=VALUE lines
toolboxctl env --json           # print as JSON dict
eval "$(toolboxctl env)"        # inject config into shell

toolboxctl playground           # create .playground/ with smoke tests
toolboxctl playground --clean   # remove .playground/

toolboxctl --version            # show version
toolboxctl --help               # show help
```
