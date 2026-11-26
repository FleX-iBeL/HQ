#!/usr/bin/env python3
"""Split the delivered prototypes into the web app's templates and stylesheets.

    python3 tools/split_design.py            check, and write web/templates and web/css
                                              only when web/templates does not exist yet
    python3 tools/split_design.py --check    check only: split in memory, put the six
                                              templates back together, compare with the
                                              originals, and list where the files on disk
                                              now differ from a fresh split
    python3 tools/split_design.py --force    write again over web/templates and web/css

After the first split, the files under web/templates and web/css are the app's
source and are edited by hand. This script does not overwrite them unless asked
with --force; use --check to see what was changed by hand since.

Standard library only. Reads design/<Design>-<iPhone|Mac>.dc.html.

What it does, per prototype:
- the markup between </helmet> and </x-dc>, with every hint-* attribute dropped
  (they are placeholders for the design tool only) and the outer whitespace trimmed;
- every screen block, an <sc-if value="{{ s.NAME }}"> that is not inside another
  screen block (s.sub, s.inner and s.herView are groups, not screens), is cut out
  and replaced by <hq-include name="NAME"></hq-include>; what is left is the shell;
- a screen that is the same in all three designs of a device is written once, to
  web/templates/<device>/shared/NAME.html; the others go to
  web/templates/<device>/<design>/NAME.html;
- each design's display typeface becomes var(--hq-display), set in that design's
  stylesheet, so screens that differ only in their typeface are stored once;
- the helmet stylesheet: rules the three designs of a device share go to
  web/css/<device>.css, the rest to web/css/<device>-<design>.css (loaded after it);
- web/templates/manifest.json says, per device and design, the shell, where every
  screen comes from, the stylesheets and the fonts link.
Then it proves the split: each template is put back together from the pieces and
must equal the original (hint-* dropped), and the stylesheet rules must add up.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESIGN = os.path.join(ROOT, "design")
WEB = os.path.join(ROOT, "web")
DESIGNS = ["spotlight", "thread", "desk"]
DEVICES = {"phone": "iPhone", "mac": "Mac"}
GROUPS = {"sub", "inner", "herView"}
# Each design has its own display typeface; the rest of the markup is the same.
# The split writes it as var(--hq-display) (set per design in its stylesheet), so
# screens that differ only in that are stored once. (markup form, stylesheet form)
DISPLAY = {"desk": ("Sora, Inter, sans-serif", "Sora,Inter,sans-serif"),
           "spotlight": ("'DM Sans', sans-serif", "'DM Sans', sans-serif"),
           "thread": ("Inter, sans-serif", "Inter, sans-serif")}
VAR = "var(--hq-display)"

TAG = re.compile(r'<!--.*?-->|<(/?)([a-zA-Z][\w-]*)((?:[^>"\']|"[^"]*"|\'[^\']*\')*?)(/?)>', re.S)
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
HINT = re.compile(r'\s+hint-[\w-]+="[^"]*"')
SCREEN_IF = re.compile(r'value="\{\{\s*s\.(\w+)\s*\}\}"')
INCLUDE = re.compile(r'<hq-include name="([\w-]+)"></hq-include>')


def drop_hints(markup):
    """Drop hint-* attributes, only inside tags."""
    return TAG.sub(lambda m: HINT.sub("", m.group(0)) if not m.group(0).startswith("<!--") else m.group(0), markup)


def to_var(text, stack, ends):
    return re.sub(r"font-family: ?" + re.escape(stack) + "(?=[" + ends + "])",
                  lambda m: m.group(0)[:m.group(0).index(":") + 1] + (" " if ": " in m.group(0) else "") + VAR, text)


def read_prototype(path):
    src = open(path, encoding="utf-8").read()
    h0 = src.index("<helmet>") + len("<helmet>")
    h1 = src.index("</helmet>")
    helmet = src[h0:h1]
    link = re.search(r'<link[^>]*fonts\.googleapis[^>]*>', helmet).group(0)
    style = re.search(r"<style>(.*?)</style>", helmet, re.S).group(1)
    body = src[h1 + len("</helmet>"):src.index("</x-dc>")]
    return {"link": link, "style": style, "markup": drop_hints(body).strip()}


def screens_of(markup):
    """Find the screen blocks: [(name, start, end)] in document order."""
    stack = []  # per open element: (name, screen flag or None, start)
    found = []
    for m in TAG.finditer(markup):
        text = m.group(0)
        if text.startswith("<!--"):
            continue
        close, name, attrs, selfclose = m.groups()
        name = name.lower()
        if close:
            tag, flag, start = stack.pop()
            if tag != name:
                raise SystemExit("unbalanced markup: <%s> closed by </%s> at %d" % (tag, name, m.start()))
            if flag and flag not in GROUPS:
                outer = [f for (_, f, _) in stack if f and f not in GROUPS]
                if not outer:
                    found.append((flag, start, m.end()))
            continue
        if selfclose or name in VOID:
            continue
        flag = None
        if name == "sc-if":
            mm = SCREEN_IF.search(attrs)
            if mm:
                flag = mm.group(1)
        stack.append((name, flag, m.start()))
    if stack:
        raise SystemExit("unbalanced markup: %d elements left open" % len(stack))
    return found


def split(markup):
    """Return (shell, {screen: markup}). A name seen twice gets a suffix: name~2."""
    blocks = screens_of(markup)
    pieces, shell, last, seen = {}, [], 0, {}
    for name, a, b in blocks:
        seen[name] = seen.get(name, 0) + 1
        key = name if seen[name] == 1 else "%s~%d" % (name, seen[name])
        pieces[key] = markup[a:b]
        shell.append(markup[last:a])
        shell.append('<hq-include name="%s"></hq-include>' % key)
        last = b
    shell.append(markup[last:])
    return "".join(shell), pieces


def assemble(shell, pieces):
    return INCLUDE.sub(lambda m: pieces[m.group(1)], shell)


def css_rules(style):
    """Top-level rules of a stylesheet, each as its own text (handles @media blocks)."""
    rules, depth, cur = [], 0, []
    for ch in style:
        cur.append(ch)
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                rules.append("".join(cur).strip())
                cur = []
    if "".join(cur).strip():
        rules.append("".join(cur).strip())
    return rules


def build():
    out = {"files": {}, "manifest": {"devices": {}}, "checks": []}
    for dev, devname in DEVICES.items():
        protos = {d: read_prototype(os.path.join(DESIGN, "%s-%s.dc.html" % (d.capitalize(), devname))) for d in DESIGNS}
        originals = {d: protos[d]["markup"] for d in DESIGNS}
        css_originals = {d: css_rules(protos[d]["style"]) for d in DESIGNS}
        for d in DESIGNS:
            protos[d]["markup"] = to_var(protos[d]["markup"], DISPLAY[d][0], ';"')
            protos[d]["style"] = to_var(protos[d]["style"], DISPLAY[d][1], ";}")
        parts = {d: split(p["markup"]) for d, p in protos.items()}
        names = set()
        for d in DESIGNS:
            names |= set(parts[d][1])
        shared = {n for n in names if all(n in parts[d][1] for d in DESIGNS)
                  and len({parts[d][1][n] for d in DESIGNS}) == 1}
        for n in sorted(shared):
            out["files"]["templates/%s/shared/%s.html" % (dev, n)] = parts[DESIGNS[0]][1][n] + "\n"
        # stylesheets
        rules = {d: css_rules(protos[d]["style"]) for d in DESIGNS}
        common = [r for r in rules[DESIGNS[2]] if all(r in rules[d] for d in DESIGNS)]
        out["files"]["css/%s.css" % dev] = ("/* Generated by tools/split_design.py from the %s prototypes'"
                                             " shared stylesheet. Edited by hand from here on. */\n" % devname
                                             + "\n".join(common) + "\n")
        devm = {"designs": {}}
        for d in DESIGNS:
            shell, pieces = parts[d]
            out["files"]["templates/%s/%s/shell.html" % (dev, d)] = shell + "\n"
            screens = {}
            for n in sorted(pieces):
                if n in shared:
                    screens[n] = "%s/shared/%s.html" % (dev, n)
                else:
                    screens[n] = "%s/%s/%s.html" % (dev, d, n)
                    out["files"]["templates/" + screens[n]] = pieces[n] + "\n"
            own = [":root{--hq-display:%s}" % DISPLAY[d][1]] + [r for r in rules[d] if r not in common]
            css = ["css/%s.css" % dev]
            if own:
                out["files"]["css/%s-%s.css" % (dev, d)] = ("/* Generated by tools/split_design.py: only what the %s"
                                                             " design adds or changes on the %s. Loaded after %s.css. */\n"
                                                             % (d.capitalize(), devname, dev) + "\n".join(own) + "\n")
                css.append("css/%s-%s.css" % (dev, d))
            devm["designs"][d] = {"shell": "%s/%s/shell.html" % (dev, d), "screens": screens, "css": css,
                                  "fonts": re.search(r'href="([^"]+)"', protos[d]["link"]).group(1).replace("&amp;", "&")}
            # proof: back together, equal to the original
            again = assemble(shell, {n: (out["files"]["templates/" + screens[n]][:-1]) for n in pieces})
            ok = again.replace(VAR, DISPLAY[d][0]) == originals[d]
            out["checks"].append((ok, "%s %s: template rebuilt from shell + %d screens (%d shared)%s"
                                  % (dev, d, len(pieces), len([n for n in pieces if n in shared]),
                                     "" if ok else "  DIFFERS")))
            back = [r.replace(VAR, DISPLAY[d][1]) for r in common + own[1:]]
            okc = sorted(back) == sorted(css_originals[d])
            out["checks"].append((okc, "%s %s: stylesheet, %d rules = %d shared + %d own%s"
                                  % (dev, d, len(rules[d]), len(common), len(own) - 1, "" if okc else "  DIFFERS")))
        devm["shared"] = sorted(shared)
        out["manifest"]["devices"][dev] = devm
    out["manifest"]["designs"] = DESIGNS
    out["manifest"]["default"] = "desk"
    out["manifest"]["include"] = '<hq-include name="NAME"></hq-include>'
    out["files"]["templates/manifest.json"] = json.dumps(out["manifest"], indent=1) + "\n"
    return out


def main():
    args = sys.argv[1:]
    out = build()
    bad = 0
    for ok, line in out["checks"]:
        print(("ok    " if ok else "FAIL  ") + line)
        bad += not ok
    if bad:
        print("%d check(s) failed; nothing written." % bad)
        return 1
    exists = os.path.isdir(os.path.join(WEB, "templates"))
    if "--check" in args or (exists and "--force" not in args):
        changed = []
        for rel, text in sorted(out["files"].items()):
            p = os.path.join(WEB, rel)
            if not os.path.exists(p):
                changed.append("missing on disk: " + rel)
            elif open(p, encoding="utf-8").read() != text:
                changed.append("changed by hand: " + rel)
        for line in changed:
            print("      " + line)
        if exists and "--check" not in args:
            print("web/templates exists: not written (use --force to write over it).")
        return 0
    for rel, text in sorted(out["files"].items()):
        p = os.path.join(WEB, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(text)
        print("wrote %6d  web/%s" % (len(text.encode("utf-8")), rel))
    return 0


if __name__ == "__main__":
    sys.exit(main())
