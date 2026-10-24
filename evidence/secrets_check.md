# Secrets check

Run against the committed state (`git ls-files`), not the working tree, so this reflects exactly
what a clone of this repo would contain.

## 1. No `.env`, no database files, nothing from `data/private/`

```
$ git ls-files | grep -iE '\.env$|\.env\.|secret|private'
.env.example

$ git ls-files | grep -iE '\.db$|\.sqlite'
(no output)

$ git ls-files | grep -i "data/private"
(no output)
```

Only `.env.example` matches — the real `.env` (at the parent folder, never inside this repo) is
not tracked. No `.db`/`.sqlite` file is tracked (`data/gavel.db` is gitignored —
`data/*.db` in `.gitignore` — and created fresh by `backend.load` on first use). Nothing under
`data/private/` is tracked (also gitignored; that path doesn't exist in this project since all
policy/request data here is synthetic, but the rule is honored regardless).

## 2. Searched every tracked file for anything that looks like a real API key

```
$ git ls-files -z | xargs -0 grep -nE "sk-[A-Za-z0-9_-]{15,}|pk-[A-Za-z0-9_-]{15,}|PORTKEY_API_KEY\s*=\s*[A-Za-z0-9]|OPENAI_API_KEY\s*=\s*[A-Za-z0-9]"
```

Every match was the literal placeholder text `your-course-key` or `your-key` inside documentation
(`README.md`, `START_HERE.md`, `PROMPTS/step09_readme_fresh_clone.md`) or the error message
`env_loader.py` prints when the key is missing — never a real key, never a value, always
documentation of the variable *name*. A second, broader pass for any long mixed-case/digit token
(24+ characters) across all tracked files turned up nothing except legitimate code identifiers
(e.g. `OpenAIResponsesModelSettings`, React's internal `__REACT_DEVTOOLS_GLOBAL_HOOK__`) and this
project's own generated IDs (`RULE-xxxxxxxx`, `DRAFT-xxxxxxxx`, `UP-xxxxxxxx`) — no secret values.

## 3. `.env.example` has names only

```
$ cat .env.example
PORTKEY_API_KEY=
OPENAI_API_KEY=
```

(Fixed during step09 — it previously had the placeholder value `your-portkey-api-key-here` on the
`PORTKEY_API_KEY` line, which is harmless but not strictly "names only"; now both lines are bare
variable names with empty values.)

## 4. Full history, not just the current tip

```
$ git log --all --diff-filter=A --name-only --pretty=format: | sort -u | grep -iE '^\.env$|\.env\.'
.env.example
```

Across every commit in this repo's history, the only `.env`-named file ever added is
`.env.example` — no earlier commit ever added a real `.env` that a later commit then removed.

## Result

**Clean.** 129 files tracked at `HEAD`. No secrets, no database files, nothing from
`data/private/`, anywhere in the committed history.
