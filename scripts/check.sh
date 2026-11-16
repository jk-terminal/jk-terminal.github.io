#!/usr/bin/env bash
#
# check.sh: checks every HTML file in this repository against the site's rules.
#
#   Run it:       bash scripts/check.sh
#   Exit status:  0 if everything passed, 1 if anything failed.
#
# The rules:
#   1. Each page stays under 50 KB.
#   2. No email addresses, private IP addresses or MAC addresses in a page.
#   3. Valid structure, no JavaScript, nothing loaded from another server.
#      (That part is done by scripts/check_html.py.)
#
# GitHub Actions runs this on every push to main and every pull request.
# Needs only bash, grep, wc and python3.

# -u: stop if the script uses a variable that was never set. Catches typos.
set -u

# Go to the repository's top folder, wherever the script was called from.
# "$0" is the path to this script; dirname strips the file name from it.
# "|| exit 1" means: if cd fails, stop with exit status 1.
cd "$(dirname "$0")/.." || exit 1

# globstar makes ** match folders at any depth. nullglob makes a pattern that
# matches nothing expand to nothing, instead of staying as literal text.
shopt -s globstar nullglob

max_bytes=51200   # 50 KB
failures=0        # counts failed checks across all files

# Two small functions for consistent output. "$1" is the first argument.
pass() {
  printf '  ok    %s\n' "$1"
}

fail() {
  printf '  FAIL  %s\n' "$1"
  failures=$((failures + 1))
}

# Patterns for things that must never be published.
# grep -E reads these as extended regular expressions.
email_pattern='[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}'
private_ip_pattern='\b(10\.[0-9]{1,3}|192\.168|172\.(1[6-9]|2[0-9]|3[01]))\.[0-9]{1,3}\.[0-9]{1,3}\b'
mac_pattern='\b([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b'

# Search one file for one pattern.
#   $1 = file, $2 = pattern, $3 = what the pattern finds, in words
check_absent() {
  local file="$1" pattern="$2" label="$3"
  local matches

  # $( ... ) runs a command and captures what it prints.
  # grep -n adds line numbers; -o prints only the matching text.
  matches="$(grep -nEo -- "$pattern" "$file")"

  # -z is true when the text is empty, meaning grep found nothing.
  if [[ -z "$matches" ]]; then
    pass "no $label"
  else
    fail "$label found:"
    # The pipe (|) sends the matches to sed, which indents each line.
    printf '%s\n' "$matches" | sed 's/^/          line /'
  fi
}

# Collect the HTML files into an array.
files=(**/*.html)

# ${#files[@]} is the number of items in the array.
if [[ ${#files[@]} -eq 0 ]]; then
  echo "No HTML files found."
  exit 1
fi

for file in "${files[@]}"; do
  echo "$file"

  # "wc -c" counts bytes. "< file" feeds the file to wc as its input, so wc
  # prints only the number and not the file name.
  size="$(wc -c < "$file")"

  # -le means "less than or equal".
  if [[ "$size" -le "$max_bytes" ]]; then
    pass "size is $size bytes (limit $max_bytes)"
  else
    fail "size is $size bytes, over the limit of $max_bytes"
  fi

  check_absent "$file" "$email_pattern"      "email addresses"
  check_absent "$file" "$private_ip_pattern" "private IP addresses"
  check_absent "$file" "$mac_pattern"        "MAC addresses"
done

echo "structure, JavaScript and external resources"

# An "if" tests a command's exit status: 0 counts as true, anything else false.
# "${files[@]}" hands every file name to the Python script as its own argument.
if python3 scripts/check_html.py "${files[@]}"; then
  pass "all files"
else
  fail "see the lines above"
fi

echo
if [[ "$failures" -eq 0 ]]; then
  echo "All checks passed."
else
  echo "$failures check(s) failed."
  exit 1
fi
