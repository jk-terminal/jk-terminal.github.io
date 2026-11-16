# jk-terminal.github.io

Source for <https://jk-terminal.github.io>: a landing page for notes and lab projects on Linux administration, bash scripting, networking and security.

## Rules for this site

- Plain HTML with inline CSS. No build step.
- No JavaScript, no trackers, no external fonts, images or stylesheets. A page makes one request: itself.
- Each page stays under 50 KB.
- No personal details: no real names, email addresses, private IP addresses, MAC addresses or hostnames.

For network examples, use the address ranges reserved for documentation: `192.0.2.0/24`, `198.51.100.0/24` and `203.0.113.0/24`.

## Files

| Path | What it is |
| --- | --- |
| `index.html` | The landing page |
| `404.html` | Shown by GitHub Pages for addresses that do not exist |
| `scripts/check.sh` | Checks every HTML file against the rules above |
| `scripts/check_html.py` | The structural part of the checks, called by `check.sh` |
| `.github/workflows/check.yml` | Runs the checks on every push to `main` and every pull request |
| `.nojekyll` | Tells GitHub Pages to publish the files as they are |

## Check before you push

```bash
bash scripts/check.sh
```

It prints `All checks passed.` and exits with status 0, or lists what failed and exits with status 1. It needs only bash and python3.

## Publish

GitHub Pages serves the `main` branch. A change is live a few minutes after it reaches `main`.

```bash
git status
git diff
git add index.html
git commit -m "Describe the change"
git push
```
