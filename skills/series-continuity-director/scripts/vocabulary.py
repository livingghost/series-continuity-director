#!/usr/bin/env python3
"""Search the bundled directing lexicon or an explicitly selected vocabulary.

The bundled entries are derived from references/cinematic-lexicon.md. They are
craft descriptions, not claims that a selected model was trained on every tag.
An external vocabulary is ordinary declared resource data; it is never discovered
by inspecting other installed skills. Unknown terms remain unmeasured.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from resource_files import resolve_resource  # noqa: E402

RESOURCE = "prompt-vocabulary"


def normalise(term: str) -> str:
    term = term.strip().lower().replace("_", " ")
    term = re.sub(r"^\(+|\)+$", "", term)
    term = re.sub(r":\s*[0-9.]+$", "", term)
    return re.sub(r"\s+", " ", term).strip()


def load(explicit: str | None = None) -> tuple[dict, Path]:
    path = resolve_resource(RESOURCE, explicit, "VOCABULARY_PATH")
    if path is None or not path.is_file():
        raise SystemExit("prompt vocabulary not found: pass --vocabulary, set VOCABULARY_PATH, or declare prompt-vocabulary in SERIES_RESOURCES")
    return json.loads(path.read_text(encoding="utf-8")), path


def index(data: dict) -> dict[str, list[tuple[str, str]]]:
    """normalised term or alias -> [(category id, term)]"""
    out: dict[str, list[tuple[str, str]]] = {}
    for category in data.get("categories") or []:
        for entry in category.get("entries") or []:
            term = entry.get("term") or ""
            for key in [term] + list(entry.get("aliases") or []):
                out.setdefault(normalise(key), []).append((category.get("id", ""), term))
    return out


def split_tags(text: str) -> list[str]:
    text = re.sub(r"\[[^\]]*\]", ",", text)
    return [t for t in (normalise(x) for x in text.replace("\n", ",").split(",")) if t]


def unknown_tags(text: str, idx: dict[str, list[tuple[str, str]]]) -> list[str]:
    seen: list[str] = []
    for tag in split_tags(text):
        if tag not in idx and tag not in seen and not re.fullmatch(r"[0-9.]+", tag):
            seen.append(tag)
    return seen


def conflicts(text: str, negative: str, data: dict) -> dict[str, list]:
    """Report tag pairs that cannot both hold, from the vocabulary's own statements.

    Three kinds, and the vocabulary is what decides them: a term written in the
    primary field and in the negative field at once, which asks for a thing and
    against it in one request; two terms from a category the vocabulary marks as
    single valued, which describe one property twice; and a pair the vocabulary
    records as opposing. Nothing here is a matter of taste. Each is a statement
    the request makes against itself.
    """

    idx = index(data)
    single = {c.get("id"): c.get("name") for c in data.get("categories") or [] if c.get("single_valued")}
    opposes: dict[str, set[str]] = {}
    for category in data.get("categories") or []:
        for entry in category.get("entries") or []:
            for other in entry.get("opposes") or []:
                opposes.setdefault(normalise(entry.get("term") or ""), set()).add(normalise(other))
                opposes.setdefault(normalise(other), set()).add(normalise(entry.get("term") or ""))

    multiple = set()
    for category in data.get("categories") or []:
        for term in category.get("multiple_figures_terms") or []:
            multiple.add(normalise(term))

    positive = split_tags(text)
    negatives = set(split_tags(negative or ""))
    both = [tag for tag in dict.fromkeys(positive) if tag in negatives]
    figures = sorted({tag for tag in positive if tag in multiple})

    by_category: dict[str, list[str]] = {}
    for tag in dict.fromkeys(positive):
        for category_id, _ in idx.get(tag, []):
            if category_id in single:
                by_category.setdefault(category_id, [])
                if tag not in by_category[category_id]:
                    by_category[category_id].append(tag)
    doubled = [{"category": cid, "name": single[cid], "terms": terms}
               for cid, terms in by_category.items() if len(terms) > 1]

    pairs = []
    seen_pairs = set()
    for tag in positive:
        for other in opposes.get(tag, set()):
            if other in positive and tuple(sorted((tag, other))) not in seen_pairs:
                seen_pairs.add(tuple(sorted((tag, other))))
                pairs.append([tag, other])

    return {"in_both_fields": both, "single_valued_doubled": doubled, "opposing": pairs,
            "multiple_figures": figures}


def fragile_at_scale(text: str, data: dict) -> dict[str, list]:
    """Parts these models draw badly, weighed against how large the frame makes them.

    A hand is a hand at any scale; what changes is how many pixels its errors get.
    The vocabulary marks the terms whose thing is countable, thin, repeated, lettered
    or reflected, and marks the terms that pull the subject close. This returns both
    lists so a caller can ask the only question that settles it: does the beat need
    that part in this frame, or is it being drawn for nothing.
    """

    fragile_terms = set()
    close_terms = set()
    for category in data.get("categories") or []:
        named_close = {normalise(term) for term in category.get("close_scale_terms") or []}
        close_terms |= named_close
        for entry in category.get("entries") or []:
            aliases = [normalise(a) for a in entry.get("aliases") or []]
            term = normalise(entry.get("term") or "")
            if entry.get("fragile_at_close_scale"):
                fragile_terms.add(term)
                fragile_terms.update(aliases)
            if term in named_close:
                close_terms.update(aliases)

    tags = dict.fromkeys(split_tags(text))
    fragile = [t for t in tags if t in fragile_terms]
    close = [t for t in tags if t in close_terms]
    if not fragile and not close:
        # Prose says the same things in sentences. Look for the terms as whole phrases,
        # so a shot written as a paragraph is measured by the same statements.
        flat = " " + re.sub(r"[^a-z0-9]+", " ", text.lower()) + " "
        fragile = [term for term in sorted(fragile_terms) if f" {term} " in flat]
        close = [term for term in sorted(close_terms) if f" {term} " in flat]
    return {"fragile": fragile, "close_scale": close}


def weighted_unknown(text: str, idx: dict[str, list[tuple[str, str]]]) -> list[str]:
    """Weighted terms the vocabulary does not know.

    A weight raises attention on the tokens of a term; it does not bind the term
    to the thing the writer meant. On a term the surface was trained on, that is
    a priority. On a term it was not, it is force applied to whatever those tokens
    do reach, and the attribute spreads: a made-up marking name at high weight
    puts the marking wherever the model can find room for it.
    """

    out: list[str] = []
    for match in re.finditer(r"\(([^()]*?):\s*[0-9.]+\)", text):
        term = normalise(match.group(1))
        if term and term not in idx and term not in out:
            out.append(term)
    return out


def hidden_parts(text: str, data: dict) -> list[dict]:
    """Terms that describe a part the same text puts out of view.

    A prompt states what one picture shows. A character's properties are true of
    the character whether or not the frame shows them, and writing an unseen one
    into the frame's text does not make it visible: it makes the surface choose
    between the two statements. Closed eyes and an eye colour are the plain case,
    and a view from behind against a face detail is the same case. The vocabulary
    marks which terms hide which part and which terms speak about it, so the pair
    is found without a list of pairs.
    """

    hides: dict[str, list[str]] = {}
    speaks: dict[str, str] = {}
    for category in data.get("categories") or []:
        for entry in category.get("entries") or []:
            names = [entry.get("term") or ""] + list(entry.get("aliases") or [])
            if entry.get("hides"):
                for name in names:
                    hides[normalise(name)] = [str(p) for p in entry["hides"]]
            if entry.get("part"):
                for name in names:
                    speaks[normalise(name)] = str(entry["part"])

    tags = list(dict.fromkeys(split_tags(text)))
    out: list[dict] = []
    for tag in tags:
        for part in hides.get(tag, []):
            # A term that also hides the part agrees with this one rather than contradicting it:
            # closed eyes and sleeping say the same thing about the eyes.
            described = [other for other in tags
                         if other != tag and speaks.get(other) == part and part not in hides.get(other, [])]
            if described:
                out.append({"hider": tag, "part": part, "described": described})
    return out


def search(data: dict, query: str, category: str | None, limit: int) -> list[dict]:
    q = normalise(query)
    hits: list[tuple[int, dict]] = []
    for cat in data.get("categories") or []:
        if category and cat.get("id") != category:
            continue
        for entry in cat.get("entries") or []:
            term = normalise(entry.get("term") or "")
            aliases = [normalise(a) for a in entry.get("aliases") or []]
            desc = (entry.get("description") or "").lower()
            score = 0
            if q == term or q in aliases:
                score = 3
            elif q in term or any(q in a for a in aliases):
                score = 2
            elif q in desc:
                score = 1
            if score:
                hits.append((score, {"category": cat.get("id"), "term": entry.get("term"), "aliases": entry.get("aliases") or [], "description": entry.get("description") or ""}))
    hits.sort(key=lambda h: (-h[0], h[1]["term"]))
    return [h for _, h in hits[:limit]]


def describe(text: str, data: dict) -> list[dict]:
    """Every term of a prompt, in order, with what the vocabulary says it draws.

    A prompt is read by the surface term by term, so it is checked term by term. A
    term the vocabulary knows comes back with its category and the description of
    what it draws, which is what a reader confirms against the picture they meant.
    A term it does not know comes back marked as such: not an error, since a
    checkpoint knows words no vocabulary lists, but the one place where the writer
    is on their own. A weight is reported beside its term, because a weight on an
    unknown term is force without binding.
    """

    by_term: dict[str, dict] = {}
    for category in data.get("categories") or []:
        for entry in category.get("entries") or []:
            record = {"category": category.get("id"), "term": entry.get("term"),
                      "description": entry.get("description")}
            by_term.setdefault(normalise(entry.get("term") or ""), record)
            for alias in entry.get("aliases") or []:
                by_term.setdefault(normalise(alias), record)

    out: list[dict] = []
    pieces = [x.strip() for x in re.sub(r"\[[^\]]*\]", ",", text).replace("\n", ",").split(",") if x.strip()]
    for raw in pieces:
        weight = None
        match = re.search(r":\s*([0-9.]+)\s*\)?$", raw)
        if match and raw.lstrip().startswith("("):
            weight = match.group(1)
        key = normalise(raw)
        hit = by_term.get(key)
        row = {"written": raw, "term": key, "weight": weight, "known": hit is not None,
               "category": (hit or {}).get("category"), "description": (hit or {}).get("description")}
        if hit is None and len(key.split()) > 4:
            flat = " " + re.sub(r"[^a-z0-9]+", " ", key) + " "
            inside = sorted({term for term in by_term if len(term) > 3 and f" {term} " in flat})
            row["contains"] = inside
        out.append(row)
    return out


def text_form(rows: list[dict]) -> str:
    """`prose` when most pieces are phrases longer than a tag, `tags` otherwise.

    A tag is a few words between commas. A sentence split at its commas gives
    pieces no vocabulary lists, so prose is read for the listed terms inside it.
    """

    phrases = sum(1 for row in rows if len(row["term"].split()) > 4)
    return "prose" if rows and phrases * 2 > len(rows) else "tags"


def terms_inside(rows: list[dict], data: dict) -> list[dict]:
    """The listed terms found inside prose pieces, each once, with what it draws."""

    found = list(dict.fromkeys(term for row in rows for term in row.get("contains") or []))
    found += [row["term"] for row in rows if row["known"] and row["term"] not in found]
    return [row for row in describe(", ".join(found), data) if row["known"]] if found else []


def main() -> int:
    parser = argparse.ArgumentParser(description="Search or check against the prompt vocabulary")
    parser.add_argument("command", choices=["search", "check", "categories", "read"])
    parser.add_argument("argument", nargs="?")
    parser.add_argument("--category")
    parser.add_argument("--limit", type=int, default=12)
    parser.add_argument("--negative", help="A file holding the negative text, read beside the primary text")
    parser.add_argument("--vocabulary", help="Path to a prompt-vocabulary JSON file")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    data, path = load(args.vocabulary)
    if args.command == "categories":
        rows = [(c.get("id"), len(c.get("entries") or []), c.get("name")) for c in data.get("categories") or []]
        if args.json:
            print(json.dumps(rows, ensure_ascii=False, indent=2))
        else:
            for cid, n, name in rows:
                print(f"{cid:40} {n:5}  {name}")
        return 0
    if args.command == "search":
        if not args.argument:
            raise SystemExit("search needs a query")
        hits = search(data, args.argument, args.category, args.limit)
        if args.json:
            print(json.dumps({"query": args.argument, "hits": hits, "vocabulary": str(path)}, ensure_ascii=False, indent=2))
        else:
            for h in hits:
                print(f"[{h['category']}] {h['term']}" + (f"  (aliases: {', '.join(h['aliases'])})" if h["aliases"] else ""))
                if h["description"]:
                    print(f"    {h['description']}")
            if not hits:
                print("no match")
        return 0
    text = sys.stdin.read() if args.argument in (None, "-") else Path(args.argument).read_text(encoding="utf-8")
    negative = Path(args.negative).read_text(encoding="utf-8") if args.negative else ""

    if args.command == "read":
        rows = describe(text, data)
        negative_rows = describe(negative, data) if negative else []
        notices: list[str] = []
        forced = weighted_unknown(text, index(data))
        if forced:
            notices.append("weight on a term the vocabulary does not know: " + ", ".join(forced))
        found = conflicts(text, negative, data)
        for tag in found["in_both_fields"]:
            notices.append("asked for and asked against: " + tag)
        for item in found["single_valued_doubled"]:
            notices.append("one property named twice (" + str(item["name"]) + "): " + ", ".join(item["terms"]))
        for left, right in found["opposing"]:
            notices.append("terms that cannot both hold: " + left + " and " + right)
        risky = fragile_at_scale(text, data)
        if risky["fragile"] and risky["close_scale"]:
            notices.append("parts drawn badly at this scale: " + ", ".join(risky["fragile"])
                           + " at " + ", ".join(risky["close_scale"]))
        forms = {"text": text_form(rows), "negative": text_form(negative_rows)}
        if args.json:
            print(json.dumps({"text": rows, "negative": negative_rows, "forms": forms,
                              "inside_prose": {label: terms_inside(block, data)
                                               for label, block in (("text", rows), ("negative", negative_rows))
                                               if forms[label] == "prose"},
                              "notices": notices, "vocabulary": str(path)}, ensure_ascii=False, indent=2))
            return 0
        for label, block in (("text", rows), ("negative", negative_rows)):
            if not block:
                continue
            if forms[label] == "prose":
                inside = terms_inside(block, data)
                print(f"{label} (prose, {len(block)} phrases): the vocabulary lists "
                      + (f"{len(inside)} term(s) found inside it" if inside else "no term found inside it"))
                for row in inside:
                    print("   " + row["term"])
                    print("      [" + str(row["category"]) + "] " + str(row["description"]))
                print()
                continue
            print(label + " (" + str(len(block)) + " terms)")
            for row in block:
                mark = " " if row["known"] else "?"
                weight = (" x" + row["weight"]) if row["weight"] else ""
                print(" " + mark + " " + row["written"] + weight)
                if row["known"]:
                    print("      [" + str(row["category"]) + "] " + str(row["description"]))
                elif row.get("contains"):
                    print("      not a listed term; the vocabulary finds inside it: " + ", ".join(row["contains"]))
                else:
                    print("      not in the vocabulary: nothing here says what it draws")
            print()
        print("notices")
        for notice in notices or ["none"]:
            print("  " + notice)
        return 0

    unknown = unknown_tags(text, index(data))
    if args.json:
        print(json.dumps({"unknown": unknown, "vocabulary": str(path)}, ensure_ascii=False, indent=2))
    else:
        print("unknown tags: " + (", ".join(unknown) if unknown else "none"))
    return 0


if __name__ == "__main__":
    import stdio_utf8
    stdio_utf8.configure()
    raise SystemExit(main())
