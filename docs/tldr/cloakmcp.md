# tldr: CloakMCP (cloak)

```
cloak scan --policy P --input F       # scan file for secrets (audit only)
cat file | cloak guard --policy P     # stdin guard (exit 1 if secrets)
cloak sanitize --policy P --input F --output O  # sanitize file → output

cloak pack --policy P --dir D         # pack directory (vault secrets as TAG-xxx)
cloak pack --policy P --dir D --dry-run  # preview without modifying
cloak unpack --dir D                  # unpack directory (restore from vault)

cloak pack-file --policy P --file F   # pack single file
cloak unpack-file --file F            # unpack single file

cloak repack --policy P --dir D       # incremental re-pack (new/changed only)
cloak verify --dir D                  # check for residual tags after unpack

cloak vault-stats --dir D             # show vault statistics
cloak vault-export --dir D --output F # export vault (encrypted backup)
cloak vault-import --dir D --input F  # import vault from backup

cloak policy validate --policy P      # validate policy file
cloak policy show --policy P          # show merged policy (after inheritance)

cloak hook <event> --dir D            # handle Claude Code hook event
cloak recover --dir D                 # recover stale session state
cloak sanitize-stdin --policy P       # sanitize text from stdin → stdout
```

**Installer scripts** (bundled in PyPI wheel, locate via `cloak scripts-path`):
```
bash "$(cloak scripts-path)/install_claude.sh"                    # install hooks (secrets-only profile)
bash "$(cloak scripts-path)/install_claude.sh" --profile hardened # + Bash safety guard
bash "$(cloak scripts-path)/install_claude.sh" --method symlink   # use symlinks instead of copy
bash "$(cloak scripts-path)/install_claude.sh" --dry-run          # preview changes
bash "$(cloak scripts-path)/install_claude.sh" --uninstall        # remove all hooks
bash "$(cloak scripts-path)/install_claude.sh" --uninstall --dry-run  # preview uninstall
```

**Policy:** `.cloak/policy.yaml` (YAML with `detection` rules)
**Rule types:** `regex`, `entropy`, `ipv4`, `ipv6`, `url`
**Actions:** `redact` | `block` | `allow` | `pseudonymize` | `replace_with_template`
**Vault:** encrypted, local-only, reversible redaction (TAG-xxx tags)
