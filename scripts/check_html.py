#!/usr/bin/env python3
"""Structural checks for the site's HTML files.

Uses only the Python standard library. Called by scripts/check.sh, or directly:

    python3 scripts/check_html.py index.html 404.html

For each file it checks that:
  - the basics are present (doctype, lang, charset, viewport, title, one h1)
  - every opening tag has a matching closing tag
  - there is no JavaScript (script tags, on* attributes, javascript: links)
  - nothing is loaded from another server (images, styles, fonts, frames)

Ordinary links (<a href="https://...">) are allowed: they only leave the site
when a visitor clicks them. Exit status is 0 if every file passes, 1 if not.
"""

import re
import sys
from html.parser import HTMLParser

# Elements that never have a closing tag.
VOID = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "source", "track", "wbr",
}

# Attributes that make the browser fetch something as the page loads.
LOADING_ATTRS = {"src", "srcset", "poster", "data", "background"}

# Tags whose href is fetched automatically (unlike <a>, which waits for a click).
LOADING_HREF_TAGS = {"link", "use", "image", "base"}

CSS_URL = re.compile(r"url\(\s*['\"]?([^'\")]+)", re.IGNORECASE)
CSS_IMPORT = re.compile(r"@import\s+['\"]([^'\"]+)", re.IGNORECASE)
HAS_SCHEME = re.compile(r"^[a-z][a-z0-9+.-]*:", re.IGNORECASE)


def is_external(value):
    """True if the value points at another server.

    Relative paths, same-page anchors (#id) and data: URLs stay on this page.
    """
    value = value.strip()
    if value.startswith("//"):
        return True
    if value.lower().startswith("data:"):
        return False
    return bool(HAS_SCHEME.match(value))


class SiteChecker(HTMLParser):
    def __init__(self, filename):
        super().__init__(convert_charrefs=True)
        self.filename = filename
        self.problems = []
        self.stack = []  # open tags, as (name, line)
        self.has_doctype = False
        self.has_lang = False
        self.has_charset = False
        self.has_viewport = False
        self.title_text = ""
        self.h1_count = 0
        self.in_style = False
        self.in_title = False

    def problem(self, message, line=None):
        line = line if line is not None else self.getpos()[0]
        self.problems.append(f"{self.filename}:{line}: {message}")

    # --- parser callbacks -------------------------------------------------

    def handle_decl(self, decl):
        if decl.lower().startswith("doctype html"):
            self.has_doctype = True

    def handle_starttag(self, tag, attrs):
        self.check_tag(tag, attrs)
        if tag not in VOID:
            self.stack.append((tag, self.getpos()[0]))
        if tag == "style":
            self.in_style = True
        if tag == "title":
            self.in_title = True

    def handle_startendtag(self, tag, attrs):
        # Self-closing form, as used inside SVG: <path ... />
        self.check_tag(tag, attrs)

    def handle_endtag(self, tag):
        if tag == "style":
            self.in_style = False
        if tag == "title":
            self.in_title = False
        if tag in VOID:
            return
        if not self.stack:
            self.problem(f"closing </{tag}> has no opening tag")
            return
        open_tag, open_line = self.stack.pop()
        if open_tag != tag:
            self.problem(
                f"expected </{open_tag}> (opened on line {open_line}) "
                f"but found </{tag}>"
            )

    def handle_data(self, data):
        if self.in_style:
            self.check_css(data)
        if self.in_title:
            self.title_text += data

    # --- individual checks ------------------------------------------------

    def check_tag(self, tag, attrs):
        attrs = {name: (value or "") for name, value in attrs}

        if tag == "script":
            self.problem("script tag found: the site must not use JavaScript")
        if tag == "html" and attrs.get("lang"):
            self.has_lang = True
        if tag == "h1":
            self.h1_count += 1
        if tag == "img" and "alt" not in attrs:
            self.problem("img has no alt attribute")
        if tag == "meta":
            if "charset" in attrs:
                self.has_charset = True
            if attrs.get("name", "").lower() == "viewport":
                self.has_viewport = True
            if attrs.get("http-equiv", "").lower() == "refresh":
                self.problem("meta refresh found: do not redirect visitors")

        for name, value in attrs.items():
            if name.startswith("on"):
                self.problem(f"{name} attribute found: no inline JavaScript")
            if value.strip().lower().startswith("javascript:"):
                self.problem(f"javascript: URL in {name} attribute")
            if name in LOADING_ATTRS and is_external(value):
                self.problem(f"<{tag} {name}> loads an external resource: {value}")
            if name == "href" and tag in LOADING_HREF_TAGS and is_external(value):
                self.problem(f"<{tag} href> loads an external resource: {value}")
            if name == "style":
                self.check_css(value)

    def check_css(self, css):
        for pattern in (CSS_URL, CSS_IMPORT):
            for match in pattern.finditer(css):
                if is_external(match.group(1)):
                    self.problem(f"CSS loads an external resource: {match.group(1)}")

    def finish(self):
        for tag, line in self.stack:
            self.problem(f"<{tag}> is never closed", line)
        if not self.has_doctype:
            self.problem("missing <!doctype html>", 1)
        if not self.has_lang:
            self.problem("<html> needs a lang attribute", 1)
        if not self.has_charset:
            self.problem('missing <meta charset="utf-8">', 1)
        if not self.has_viewport:
            self.problem("missing viewport meta tag (needed for phones)", 1)
        if not self.title_text.strip():
            self.problem("missing or empty <title>", 1)
        if self.h1_count != 1:
            self.problem(f"expected exactly one <h1>, found {self.h1_count}", 1)


def check_file(filename):
    checker = SiteChecker(filename)
    with open(filename, encoding="utf-8") as handle:
        checker.feed(handle.read())
    checker.close()
    checker.finish()
    return checker.problems


def main(filenames):
    if not filenames:
        print("usage: check_html.py FILE.html [FILE.html ...]")
        return 2
    all_problems = []
    for filename in filenames:
        all_problems.extend(check_file(filename))
    for line in all_problems:
        print(line)
    return 1 if all_problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
