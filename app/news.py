"""H236: your own news inside HQ (23 October 2026).

The user's words on the call of 22 October 2026: "You can configure it and then it only gives you the news from specific
sources about specific topics, ranges, or topics you don't want to hear about. You can still get sort of up to date
without being bombarded by news that is just there to freak you out or that is not important", "Maybe it's more of a
session, just like life coaching. You have a session but way smaller", and "we can just read about it in the app so we
don't have to go off-platform, right? I want to stay native in this app so we don't get any distractions. ... One part
is our emails ... Another part is what's not in our life but in the world, what's going on. Not that we have to combine
those two".

For everyone with News on (a switch in What HQ helps you with, features.py). Nothing of theirs is in HQ:
    - Their setup, made in a short session with an agent (a call started from the News sheet, about_news): the topics
      they want (each with the words that find it), what to leave out, and the sources (free feeds: RSS or Atom; the
      agent suggests, `try` checks one before it's added). In the workspace's HQ/news.json; none on a fresh install.
    - The routine on the main reads their sources about every hour (tick.py, `start`), keeps an item when it's about
      one of their topics (or comes from a source they take whole), drops it when it touches something they leave out,
      and keeps the newest in the workspace's HQ/news-items.json: their own newspaper. No paid service, no Claude.
    - The app's News sheet shows it: short items with their source, newest first; a tap reads the item inside HQ (the
      article's own text, fetched on the main when asked; the source's link only at the bottom). Apart from the mail.

    python3 app/news.py                         the setup and the newest items, in a few lines
    python3 app/news.py json                    everything the app shows
    python3 app/news.py setup                   the setup only
    python3 app/news.py suggest [TOPIC]         free feeds to suggest (general ones; check each with try)
    python3 app/news.py try URL                 read a feed once: does it work, how many items, the newest titles
    python3 app/news.py topic add NAME [--words "a, b, c"]     a topic (words: what finds it; else its name)
    python3 app/news.py topic remove NAME
    python3 app/news.py leave-out add "a, b"    words that drop an item, whatever the source
    python3 app/news.py leave-out remove WORD
    python3 app/news.py source add NAME URL [--all] [--topic NAME]   a feed; --all keeps everything from it
    python3 app/news.py source remove NAME
    python3 app/news.py fetch                   read the sources now
    python3 app/news.py start                   the routine's look: reads them when an hour has passed (tick.py)
"""
from __future__ import annotations

import html
import json
import os
import re
import subprocess
import sys
import threading
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent  # HQ

SETUP = "HQ/news.json"  # in the workspace: their topics, what to leave out, their sources
ITEMS = "HQ/news-items.json"  # in the workspace: the newspaper, written by the routine on the main
EVERY = 55 * 60  # about every hour
KEEP = 150  # items kept
MAX_AGE = 7 * 86400  # nothing older than a week
TIMEOUT = 15
UA = "HQ news (a personal reader; https://github.com/FleX-iBeL/HQ)"
_lock = threading.Lock()

# General free feeds the agent may suggest, by kind. Not anyone's choice: a starting point, each checked with `try`.
SUGGEST = {
    "AI": [("Ars Technica AI", "https://arstechnica.com/ai/feed/"),
           ("The Verge AI", "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml"),
           ("MIT Technology Review", "https://www.technologyreview.com/feed/"),
           ("Hacker News front page", "https://hnrss.org/frontpage")],
    "Tech": [("Ars Technica", "https://feeds.arstechnica.com/arstechnica/index"),
             ("The Verge", "https://www.theverge.com/rss/index.xml"),
             ("Tweakers (Dutch)", "https://feeds.feedburner.com/tweakers/mixed")],
    "World": [("BBC World", "https://feeds.bbci.co.uk/news/world/rss.xml"),
              ("The Guardian World", "https://www.theguardian.com/world/rss"),
              ("Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml")],
    "Netherlands": [("NOS (Dutch)", "https://feeds.nos.nl/nosnieuwsalgemeen"),
                    ("NU.nl (Dutch)", "https://www.nu.nl/rss/Algemeen"),
                    ("DutchNews.nl (English)", "https://www.dutchnews.nl/feed/")],
    "Science": [("BBC Science", "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml"),
                ("Quanta Magazine", "https://www.quantamagazine.org/feed/")],
    "Business": [("BBC Business", "https://feeds.bbci.co.uk/news/business/rss.xml"),
                 ("The Guardian Business", "https://www.theguardian.com/uk/business/rss")],
}


def folder() -> Path:
    return Path(os.environ.get("HQ_NEWS_FOLDER") or os.environ.get("HQ_FEATURES_FOLDER") or os.environ.get("HQ_FOLDER")
                or os.path.realpath(os.environ.get("HQ_WORKSPACE", str(ROOT / "workspace"))))


def on() -> bool:
    try:
        sys.path.insert(0, str(HERE))
        import features
        return features.is_on("news")
    except Exception:
        return True


def _now() -> float:
    t = os.environ.get("HQ_NEWS_NOW")  # the happy flows' own now
    return float(t) if t else time.time()


def _read(p: Path, empty):
    try:
        d = json.loads(p.read_text(encoding="utf8"))
    except (OSError, ValueError):
        return empty
    return d if isinstance(d, type(empty)) else empty


def _write(p: Path, d) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf8")
    os.replace(tmp, p)


def setup(f: Path | None = None) -> dict:
    d = _read((f or folder()) / SETUP, {})
    return {"topics": [t for t in d.get("topics") or [] if isinstance(t, dict) and t.get("name")],
            "leave_out": [w for w in d.get("leave_out") or [] if isinstance(w, str) and w.strip()],
            "sources": [s for s in d.get("sources") or [] if isinstance(s, dict) and s.get("url")],
            "since": d.get("since") or ""}


def _save_setup(d: dict, f: Path | None = None) -> None:
    if not d.get("since"):
        d["since"] = datetime.now().strftime("%Y-%m-%d")
    _write((f or folder()) / SETUP, d)


def _words(s: str) -> list[str]:
    return [w.strip() for w in re.split(r"[,;\n]", s or "") if w.strip()]


# ---- reading a feed --------------------------------------------------------------------------------------------------

class _Text(HTMLParser):
    """Plain text from a bit of HTML; with `paras`, only the paragraphs (an article's own text)."""

    SKIP = {"script", "style", "nav", "header", "footer", "aside", "form", "figure", "noscript", "button", "svg"}

    def __init__(self, paras: bool = False):
        super().__init__(convert_charrefs=True)
        self.paras, self.out, self.cur, self.skip, self.inp, self.art = paras, [], [], 0, 0, 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.skip += 1
        elif tag == "article":
            self.art += 1
        elif tag in ("p", "li", "h2", "h3"):
            self.inp += 1
            self.cur = []
        elif tag == "br" and not self.paras:
            self.out.append(" ")

    def handle_endtag(self, tag):
        if tag in self.SKIP:
            self.skip = max(0, self.skip - 1)
        elif tag in ("p", "li", "h2", "h3") and self.inp:
            self.inp -= 1
            t = " ".join("".join(self.cur).split())
            if self.paras and t:
                self.out.append((t, self.art > 0, tag))
            self.cur = []

    def handle_data(self, data):
        if self.skip:
            return
        if self.paras:
            if self.inp:
                self.cur.append(data)
        else:
            self.out.append(data)


def plain(s: str) -> str:
    if not s:
        return ""
    p = _Text()
    try:
        p.feed(s)
        p.close()
        t = "".join(p.out)
    except Exception:
        t = re.sub(r"<[^>]+>", " ", s)
    return " ".join(html.unescape(t).split())


def _when(s: str) -> float:
    s = (s or "").strip()
    if not s:
        return 0.0
    try:
        return parsedate_to_datetime(s).timestamp()
    except (TypeError, ValueError, IndexError):
        pass
    try:
        d = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return (d if d.tzinfo else d.replace(tzinfo=timezone.utc)).timestamp()
    except ValueError:
        return 0.0


def _get(url: str, timeout: float = TIMEOUT) -> bytes:
    if not re.match(r"^https?://", url or ""):
        raise ValueError("only http and https links")
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(3_000_000)


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def parse(data: bytes) -> list[dict]:
    """RSS 2.0, RSS 1.0 (RDF) and Atom: title, link, summary, when."""
    root = ET.fromstring(data)
    out = []
    for e in root.iter():
        kind = _local(e.tag)
        if kind not in ("item", "entry"):
            continue
        it = {"title": "", "link": "", "summary": "", "at": 0.0}
        for c in e:
            n, text = _local(c.tag), (c.text or "")
            if n == "title":
                it["title"] = plain(text)
            elif n == "link":
                href = c.get("href")
                if href and (c.get("rel") in (None, "alternate")) and not it["link"]:
                    it["link"] = href.strip()
                elif text.strip() and not it["link"]:
                    it["link"] = text.strip()
            elif n in ("description", "summary") or (n in ("content", "encoded") and not it["summary"]):
                it["summary"] = plain(text)
            elif n in ("pubdate", "published", "updated", "date") and not it["at"]:
                it["at"] = _when(text)
            elif n == "guid" and not it["link"] and text.startswith("http"):
                it["link"] = text.strip()
        if it["title"] and it["link"]:
            out.append(it)
    return out


def read_feed(url: str) -> list[dict]:
    return parse(_get(url))


# ---- what fits -------------------------------------------------------------------------------------------------------

def _rx(words: list[str]) -> re.Pattern | None:
    words = [w for w in words if w]
    if not words:
        return None
    return re.compile(r"(?<![\w])(" + "|".join(re.escape(w) for w in sorted(words, key=len, reverse=True)) + r")(?![\w])", re.I)


def judge(it: dict, src: dict, s: dict) -> tuple[bool, list[str], str]:
    """Keep it? With the topics it's about, or why it's left out."""
    text = it["title"] + " " + it.get("summary", "")
    lo = _rx(s["leave_out"])
    m = lo.search(text) if lo else None
    if m:
        return False, [], f"leave out: {m.group(1).lower()}"
    found = []
    for t in s["topics"]:
        rx = _rx(t.get("words") or [t["name"]])
        if rx and rx.search(text):
            found.append(t["name"])
    if src.get("topic") and src["topic"] not in found and (src.get("all") or found):
        found.insert(0, src["topic"])
    if src.get("all") or found:
        return True, found, ""
    return False, [], "not about a topic"


def _key(it: dict) -> str:
    return re.sub(r"\W+", " ", it["title"].lower()).strip()[:90]


def fetch(f: Path | None = None) -> dict:
    """Read every source once, judge each item, keep the newest. Only on the main (the routine), or by hand."""
    f = f or folder()
    s = setup(f)
    now = _now()
    with _lock:
        old = _read(f / ITEMS, {})
        items = {i["id"]: i for i in old.get("items") or [] if isinstance(i, dict) and i.get("id")}
        seen_t = {_key(i) for i in items.values()}
        stats, dropped, new = {}, {}, 0  # dropped: this look only
        for src in s["sources"]:
            name = src.get("name") or src["url"]
            try:
                got = read_feed(src["url"])
            except Exception as e:
                stats[name] = {"ok": False, "error": " ".join(str(e).split())[:120], "at": now}
                continue
            kept = 0
            for it in got:
                at = it["at"] or now
                if now - at > MAX_AGE:
                    continue
                iid = _id(it["link"])
                if iid in items:
                    kept += 1
                    continue
                ok, topics, why = judge(it, src, s)
                if not ok:
                    dropped[why.split(":")[0]] = dropped.get(why.split(":")[0], 0) + 1
                    continue
                if _key(it) in seen_t:
                    continue
                seen_t.add(_key(it))
                summ = it["summary"]
                if summ.lower().startswith(it["title"].lower()):
                    summ = summ[len(it["title"]):].strip(" .:-")
                items[iid] = {"id": iid, "title": it["title"][:240], "summary": summ[:420], "link": it["link"],
                              "source": name, "topics": topics, "at": at, "got": now}
                kept += 1
                new += 1
            stats[name] = {"ok": True, "items": len(got), "kept": kept, "at": now}
        keep = sorted((i for i in items.values() if now - i["at"] <= MAX_AGE), key=lambda i: -i["at"])[:KEEP]
        out = {"looked": now, "items": keep, "sources": stats, "dropped": dropped, "new": new}
        _write(f / ITEMS, out)
    return out


def _id(link: str) -> str:
    import hashlib
    return hashlib.sha1(link.encode("utf8")).hexdigest()[:14]


def start(f: Path | None = None) -> bool:
    """From tick.py, every minute on the main: when News is on, there's a source, and an hour has passed, read them
    detached. True when a look was started."""
    f = f or folder()
    if not on():
        return False
    s = setup(f)
    if not s["sources"]:
        return False
    st = _read(f / ITEMS, {})
    now = _now()
    if now - float(st.get("tried") or st.get("looked") or 0) < EVERY:
        return False
    st["tried"] = now
    _write(f / ITEMS, st)
    py = ROOT / ".venv" / "bin" / "python"
    log = ROOT / "scratch" / "news.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    subprocess.Popen([str(py) if py.exists() else sys.executable, str(Path(__file__).resolve()), "fetch"],
                     cwd=str(ROOT), stdout=open(log, "a"), stderr=subprocess.STDOUT, start_new_session=True,
                     env={**os.environ, "HQ_NEWS_FOLDER": str(f)})
    return True


# ---- reading an item inside HQ ---------------------------------------------------------------------------------------

def article(iid: str, f: Path | None = None, save: bool = True) -> dict:
    """The item, with its article's own text when the page gives it (fetched now; kept with the item on the main,
    the one writer of the newspaper: on the backup `save` is off, so the sync never meets two versions)."""
    f = f or folder()
    with _lock:
        d = _read(f / ITEMS, {})
    it = next((i for i in d.get("items") or [] if i.get("id") == iid), None)
    if not it:
        return {"error": "That item isn't in your news any more."}
    if it.get("text") is not None:
        return it
    paras: list[str] = []
    try:
        raw = _get(it["link"]).decode("utf8", "replace")
        p = _Text(paras=True)
        p.feed(raw)
        p.close()
        inart = [t for t, a, tag in p.out if a]
        pick = inart if sum(len(t) for t in inart) > 300 else [t for t, a, tag in p.out]
        paras = [t for t in pick if len(t) > 60 and not re.search(r"cookie|subscribe|sign up|newsletter|all rights reserved", t, re.I)]
    except Exception:
        paras = []
    text = "\n\n".join(paras)[:20000]
    if not save:
        return {**it, "text": text}
    with _lock:
        d = _read(f / ITEMS, {})
        for i in d.get("items") or []:
            if i.get("id") == iid:
                i["text"] = text
                it = i
        if d:
            _write(f / ITEMS, d)
    return it


# ---- the app, calls --------------------------------------------------------------------------------------------------

def read(f: Path | None = None) -> dict:
    f = f or folder()
    s = setup(f)
    d = _read(f / ITEMS, {})
    items = [{k: v for k, v in i.items() if k != "text"} for i in d.get("items") or [] if isinstance(i, dict)]
    return {"on": on(), "set": bool(s["sources"]), "setup": s, "items": items, "looked": d.get("looked") or 0,
            "sources": d.get("sources") or {}, "dropped": d.get("dropped") or {}}


def summary(f: Path | None = None) -> str:
    r = read(f)
    s = r["setup"]
    if not r["on"]:
        return "News is off."
    out = [_setup_lines(s)]
    if r["items"]:
        out.append(f"{len(r['items'])} items, the newest:")
        out += [f"- {i['title']} ({i['source']})" for i in r["items"][:8]]
    elif s["sources"]:
        out.append("No items yet: the sources are read about every hour.")
    return "\n".join(out)


def _setup_lines(s: dict) -> str:
    if not (s["topics"] or s["sources"] or s["leave_out"]):
        return "Not set up yet: no topics, nothing left out, no sources."
    t = "; ".join(x["name"] + (f" ({', '.join(x['words'])})" if x.get("words") else "") for x in s["topics"]) or "none"
    src = "; ".join(f"{x.get('name')} ({x['url']}" + (", all of it" if x.get("all") else "")
                    + (f", topic {x['topic']}" if x.get("topic") else "") + ")" for x in s["sources"]) or "none"
    return f"Topics: {t}.\nLeft out: {', '.join(s['leave_out']) or 'nothing'}.\nSources: {src}."


def change(argv: list[str], f: Path | None = None) -> str:
    f = f or folder()
    d = setup(f)
    what, how, rest = argv[0], argv[1] if len(argv) > 1 else "", argv[2:]
    opts, args, i = {}, [], 0
    while i < len(rest):
        if rest[i] == "--all":
            opts["all"] = True
        elif rest[i] in ("--words", "--topic") and i + 1 < len(rest):
            opts[rest[i][2:]] = rest[i + 1]
            i += 1
        else:
            args.append(rest[i])
        i += 1
    if what == "topic" and args:
        name = " ".join(args).strip()
        d["topics"] = [t for t in d["topics"] if t["name"].lower() != name.lower()]
        if how == "add":
            d["topics"].append({"name": name, "words": _words(opts.get("words", "")) or [name]})
            _save_setup(d, f)
            return f"Topic {name} is in."
        if how == "remove":
            _save_setup(d, f)
            return f"Topic {name} is out."
    if what == "leave-out" and args:
        ws = _words(" ".join(args))
        low = {w.lower() for w in ws}
        d["leave_out"] = [w for w in d["leave_out"] if w.lower() not in low]
        if how == "add":
            d["leave_out"] += ws
        _save_setup(d, f)
        return ("Left out from now: " if how == "add" else "No longer left out: ") + ", ".join(ws) + "."
    if what == "source":
        if how == "add" and len(args) >= 2:
            name, url = " ".join(args[:-1]), args[-1]
            if not re.match(r"^https?://", url):
                return "A source needs its feed's link (http or https)."
            d["sources"] = [x for x in d["sources"] if x["url"] != url and x.get("name", "").lower() != name.lower()]
            src = {"name": name, "url": url}
            if opts.get("all"):
                src["all"] = True
            if opts.get("topic"):
                src["topic"] = opts["topic"]
            d["sources"].append(src)
            _save_setup(d, f)
            return f"Source {name} is in." + (" Everything from it is kept." if src.get("all") else "")
        if how == "remove" and args:
            name = " ".join(args)
            n = len(d["sources"])
            d["sources"] = [x for x in d["sources"] if x.get("name", "").lower() != name.lower() and x["url"] != name]
            _save_setup(d, f)
            return f"Source {name} is out." if len(d["sources"]) < n else f"No source {name}."
    return __doc__


def try_feed(url: str) -> str:
    try:
        got = read_feed(url)
    except Exception as e:
        return f"That feed doesn't work: {' '.join(str(e).split())[:160]}"
    if not got:
        return "It answers, but there are no items in it."
    newest = sorted(got, key=lambda i: -(i["at"] or 0))[:3]
    return f"It works: {len(got)} items. The newest: " + "; ".join(i["title"] for i in newest)


def rule() -> str:
    """The call rule when News is on: how a call keeps their setup."""
    if not on():
        return ""
    s = setup()
    return (f"- News (H236): their own newspaper in the app, from the sources and topics they picked. Change it when "
            f"they ask, with python3 \"{HERE / 'news.py'}\" (topic add NAME --words \"a, b\", leave-out add \"a, b\", "
            "source add NAME URL [--all] [--topic NAME], the removes, try URL before adding a source, suggest TOPIC, "
            "fetch to read them now, summary for what's in it). Now: " + " ".join(_setup_lines(s).split("\n")))


# ---- a call about setting it up (call.py's _about, kind "news") -------------------------------------------------------

def about(ref: str = "setup") -> dict | None:
    if not on():
        return None
    s = setup()
    return {"kind": "news", "ref": ref or "setup", "title": "Your news", "setup": s}


def when_line(e: dict) -> str:
    return "setting up your news"


def greetings(e: dict, name: str = "") -> list[str]:
    n = f", {name}" if name else ""
    if (e.get("setup") or {}).get("sources"):
        return [f"Hi{n}. Let's look at your news. What would you like to change?", f"Hey{n}. Your news: what's in, what's out?"]
    return [f"Hi{n}. Let's set up your news. What would you like to stay up to date on?",
            f"Hey{n}. Your own newspaper: what do you want to hear about?"]


def call_note(e: dict, user: str = "the user") -> str:
    script = HERE / "news.py"
    s = e.get("setup") or setup()
    return (
        f"{user} started this call from the News sheet in HQ: a short session to set up their own newspaper, a small one, "
        "like a life coaching layer but way smaller. This call is only that. Go through it one question at a time:\n"
        "1. What do they want to stay up to date on? Each topic in a few words; for each, the words that find it in a "
        "headline (names, short terms, their language too). Keep: "
        f"python3 \"{script}\" topic add NAME --words \"a, b, c\".\n"
        "2. What don't they want to hear about, the news that's only there to freak them out or push a story? Those "
        f"words drop an item whatever the source: python3 \"{script}\" leave-out add \"a, b\".\n"
        "3. Which sources? Ask whether they have favourites, and suggest a few free ones that fit "
        f"(python3 \"{script}\" suggest TOPIC gives general ones; you may know better feeds). Only free RSS or Atom feeds, "
        f"never a paid service. Check each before adding it: python3 \"{script}\" try URL. Add it: python3 \"{script}\" "
        "source add NAME URL; with --all when the whole source is about what they want (an AI news site for AI), else "
        "only its items about their topics are kept; --topic NAME labels it.\n"
        f"Then read them once (python3 \"{script}\" fetch) and say in a sentence what's in their news now, and that it's "
        "read again about every hour and shows under News in the app. Change only what they say; their words for the "
        "topics.\n"
        "Now: " + " ".join(_setup_lines(s).split("\n")) + "\n"
    )


def main(argv: list[str]) -> int:
    cmd = argv[0] if argv else "summary"
    if cmd == "summary":
        print(summary())
    elif cmd == "json":
        print(json.dumps(read(), ensure_ascii=False, indent=1))
    elif cmd == "setup":
        print(_setup_lines(setup()))
    elif cmd == "suggest":
        want = " ".join(argv[1:]).lower()
        for k, v in SUGGEST.items():
            if not want or want in k.lower() or k.lower() in want:
                print(f"{k}: " + "; ".join(f"{n} {u}" for n, u in v))
    elif cmd == "try" and len(argv) == 2:
        print(try_feed(argv[1]))
    elif cmd in ("topic", "leave-out", "source") and len(argv) >= 3 and argv[1] in ("add", "remove"):
        print(change(argv))
    elif cmd == "fetch":
        r = fetch()
        bad = [n for n, x in r["sources"].items() if not x.get("ok")]
        print(f"Read {len(r['sources'])} sources: {len(r['items'])} items in the news, {r['new']} new."
              + (f" Didn't answer: {', '.join(bad)}." if bad else ""))
    elif cmd == "start":
        print("reading" if start() else "not now")
    elif cmd == "rule":
        print(rule())
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
