#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

PUNCT_RE = re.compile(r"^\W+$", re.UNICODE)

DEFAULT_SEED_LEXICON = {
    # very common backchannel tokens / short acknowledgements (lowercase)
    "mhm", "mh", "mhmh", "mm", "mmm", "hmm", "hm",
    "aha", "aja",
    "ja", "ne", "no",
    "ok", "okej",
    "prav", "tako", "res",
    "dobro", "super", "fajn",
    "seveda",
    # add more if you like
}

@dataclass
class Token:
    tid: int
    form: str
    lemma: str
    upos: str
    head: Optional[int]
    deprel: str
    misc: str

@dataclass
class Sent:
    doc: str
    sent_id: str
    speaker: str
    text: str
    sound_url: str
    tokens: List[Token]

def parse_conllu(path: Path) -> List[Sent]:
    sents: List[Sent] = []
    meta: Dict[str, str] = {}
    tokens: List[Token] = []
    current_doc: str = ""

    def flush():
        nonlocal meta, tokens, current_doc
        if not meta and not tokens:
            return
        if "newdoc id" in meta:
            current_doc = meta["newdoc id"]
        sent_id = meta.get("sent_id", "")
        speaker = meta.get("speaker_id", "")
        text = meta.get("text", "")
        sound_url = meta.get("sound_url", "NA")
        sents.append(Sent(doc=current_doc, sent_id=sent_id, speaker=speaker, text=text, sound_url=sound_url, tokens=tokens))
        meta = {}
        tokens = []

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line:
                flush()
                continue
            if line.startswith("#"):
                if "=" in line:
                    k, v = line[1:].split("=", 1)
                    meta[k[1:].strip()] = v.strip()
                continue

            cols = line.split("\t")
            if len(cols) < 8:
                continue
            tid = cols[0]
            # skip multiword tokens & empty nodes
            if "-" in tid or "." in tid:
                continue
            try:
                tid_i = int(tid)
            except ValueError:
                continue

            head = None
            if cols[6].isdigit():
                head = int(cols[6])

            misc = cols[9] if len(cols) > 9 else "_"
            tokens.append(Token(
                tid=tid_i,
                form=cols[1],
                lemma=cols[2],
                upos=cols[3],
                head=head,
                deprel=cols[7],
                misc=misc
            ))

    flush()
    return sents

def is_punct(tok: Token) -> bool:
    if tok.upos == "PUNCT":
        return True
    # also treat pure punctuation forms as punct
    return bool(PUNCT_RE.match(tok.form.strip()))

def norm_form(s: str) -> str:
    return s.strip().lower()

def nonpunct_tokens(sent: Sent) -> List[Token]:
    return [t for t in sent.tokens if not is_punct(t)]

def sent_root_id(sent: Sent) -> Optional[int]:
    for t in sent.tokens:
        if t.head == 0:
            return t.tid
    return None

def last_content_id(sent: Sent) -> Optional[int]:
    # heuristic: last token that is not punct and not a pure filler-like thing
    toks = nonpunct_tokens(sent)
    if not toks:
        return None
    # prefer content POS near the end
    content_pos = {"NOUN", "PROPN", "VERB", "ADJ", "ADV", "NUM", "PRON"}
    for t in reversed(toks):
        if t.upos in content_pos and norm_form(t.form) not in {"eee", "em", "erm"}:
            return t.tid
    # fallback: last nonpunct
    return toks[-1].tid

def count_lexicon_hits(sent: Sent, lex: set[str]) -> Tuple[int, int, List[str]]:
    toks = nonpunct_tokens(sent)
    forms = [norm_form(t.form) for t in toks]
    hits = sum(1 for f in forms if f in lex)
    return hits, len(forms), forms

def is_question_like(text: str) -> bool:
    t = (text or "").strip()
    return "?" in t

def has_discourse_like_deprel(sent: Sent) -> bool:
    # used only as a weak positive signal (not a filter)
    for t in sent.tokens:
        if t.deprel.startswith("discourse"):
            return True
    return False

def build_top_short_utterances(sents: List[Sent], max_tokens: int) -> Counter[str]:
    c = Counter()
    for s in sents:
        toks = [norm_form(t.form) for t in nonpunct_tokens(s)]
        if 0 < len(toks) <= max_tokens:
            key = " ".join(toks)
            c[key] += 1
    return c

def find_next_same_speaker(sents: List[Sent], i: int, window: int) -> Optional[int]:
    """Find next index j in (i+1..i+window) with same speaker as sents[i], same doc."""
    base = sents[i]
    for j in range(i + 1, min(len(sents), i + window + 1)):
        if sents[j].doc != base.doc:
            break
        if sents[j].speaker == base.speaker:
            return j
    return None

def is_near_end_of_doc(sents: List[Sent], i: int, k_end: int) -> bool:
    """True if i is within last k_end utterances of its doc."""
    doc = sents[i].doc
    # find last index of this doc
    j = i
    last = i
    while j < len(sents) and sents[j].doc == doc:
        last = j
        j += 1
    return (last - i) <= k_end

def main():
    ap = argparse.ArgumentParser(description="Extract backchannel candidates from SST corpus")
    ap.add_argument("--input", default=None, help="Path to SST .conllu (default: src/sst/sl_sst-ud-merged.conllu)")
    ap.add_argument("--output", default=None, help="Output CSV path (default: output/sst/backchannel_candidates.csv)")
    ap.add_argument("--max_tokens", type=int, default=5, help="Max non-punct tokens in B to consider")
    ap.add_argument("--min_lex_hits", type=int, default=1, help="Minimum lexicon hits in B")
    ap.add_argument("--window", type=int, default=5, help="Lookahead window for A…B…A continuation")
    ap.add_argument("--end_k", type=int, default=2, help="Consider A-B near end of doc within this many turns")
    ap.add_argument("--include_no_continuation", action="store_true",
                    help="Also include short B even if we can't prove A continues")
    ap.add_argument("--lexicon_file", default=None, help="Optional extra lexicon file (one token per line)")
    ap.add_argument("--auto_top_short", type=int, default=0,
                    help="If >0, write top short utterances list to <output>.top_short.csv")
    ap.add_argument("--add_top_short_to_lexicon", type=int, default=0,
                    help="If >0, add the top N short-utterance tokens (single-token only) to lexicon to increase recall")
    args = ap.parse_args()

    # Set defaults relative to script location
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    if args.input is None:
        args.input = str(project_root / "src" / "sst" / "sl_sst-ud-merged.conllu")
    if args.output is None:
        output_dir = project_root / "output" / "sst"
        output_dir.mkdir(parents=True, exist_ok=True)
        args.output = str(output_dir / "backchannel_candidates.csv")

    path = Path(args.input)
    sents = parse_conllu(path)

    # lexicon
    lex = set(DEFAULT_SEED_LEXICON)
    if args.lexicon_file:
        extra = Path(args.lexicon_file)
        for line in extra.read_text(encoding="utf-8").splitlines():
            line = norm_form(line)
            if line and not line.startswith("#"):
                lex.add(line)

    # optional: build top short utterances
    if args.auto_top_short > 0:
        top = build_top_short_utterances(sents, max_tokens=args.max_tokens)
        out_top = Path(args.output).with_suffix("")  # strip .csv if present
        out_top = Path(str(out_top) + ".top_short.csv")
        with out_top.open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["utterance_tokens", "count"])
            for utt, cnt in top.most_common(args.auto_top_short):
                w.writerow([utt, cnt])

    if args.add_top_short_to_lexicon > 0:
        top = build_top_short_utterances(sents, max_tokens=args.max_tokens)
        added = 0
        for utt, _ in top.most_common():
            toks = utt.split()
            if len(toks) == 1 and toks[0] not in lex:
                lex.add(toks[0])
                added += 1
                if added >= args.add_top_short_to_lexicon:
                    break

    # aggregate results per B_sent_id (so one row per B even if multiple reasons)
    rows_by_b: Dict[str, dict] = {}
    reasons_by_b: Dict[str, set] = defaultdict(set)

    for i in range(len(sents)):
        if i == 0:
            continue

        A = sents[i - 1]
        B = sents[i]
        if A.doc != B.doc:
            continue
        if not A.sent_id or not B.sent_id:
            continue
        if not A.speaker or not B.speaker:
            continue
        if A.speaker == B.speaker:
            continue  # backchannels are typically other-speaker

        hits, n_tok, forms = count_lexicon_hits(B, lex)
        if n_tok == 0 or n_tok > args.max_tokens:
            continue
        if hits < args.min_lex_hits:
            continue

        # compute continuation evidence
        reasons = set()
        score = 0

        # immediate ABA
        if i + 1 < len(sents):
            C = sents[i + 1]
            if C.doc == B.doc and C.speaker == A.speaker:
                reasons.add("ABA_immediate")
                score += 3

        # windowed A…B…A
        j = find_next_same_speaker(sents, i - 1, window=args.window)
        # j is next same speaker as A; for window evidence we want it after B
        if j is not None and j > i:
            reasons.add(f"ABA_window{args.window}")
            score += 2

        # near end of doc A-B
        if is_near_end_of_doc(sents, i, k_end=args.end_k):
            reasons.add(f"AB_enddoc{args.end_k}")
            score += 1

        # include without continuation if requested
        if not reasons and not args.include_no_continuation:
            continue
        if not reasons:
            reasons.add("B_short_no_continuation")
            score += 0

        # weak syntactic clue (not required)
        if has_discourse_like_deprel(B):
            reasons.add("B_has_discourse_deprel")
            score += 1

        # flags
        A_root = sent_root_id(A)
        A_last = last_content_id(A)

        A_is_q = is_question_like(A.text)
        B_is_q = is_question_like(B.text)

        proposed_root = f"{A.sent_id}::{A_root}" if A_root is not None else ""
        proposed_last = f"{A.sent_id}::{A_last}" if A_last is not None else ""

        row = rows_by_b.get(B.sent_id)
        if row is None:
            rows_by_b[B.sent_id] = {
                "doc": B.doc,
                "A_sent_id": A.sent_id,
                "A_speaker": A.speaker,
                "A_text": A.text,
                "A_sound_url": A.sound_url,
                "A_root_id": A_root,
                "A_last_content_id": A_last,
                "B_sent_id": B.sent_id,
                "B_speaker": B.speaker,
                "B_text": B.text,
                "B_sound_url": B.sound_url,
                "B_tokens_norm": " ".join(forms),
                "B_lex_hits": hits,
                "B_tok_count": n_tok,
                "A_is_question": int(A_is_q),
                "B_is_question": int(B_is_q),
                "proposed_attach_root": proposed_root,
                "proposed_attach_last_content": proposed_last,
                "score": score,
                "reasons": "",  # filled later
                "keep?": "",    # manual
            }
        else:
            # merge if we hit same B again (should be rare), keep best score
            rows_by_b[B.sent_id]["score"] = max(rows_by_b[B.sent_id]["score"], score)

        reasons_by_b[B.sent_id].update(reasons)

    # write CSV
    out = Path(args.output)
    fieldnames = [
        "doc",
        "A_sent_id", "A_speaker", "A_text", "A_sound_url", "A_root_id", "A_last_content_id",
        "B_sent_id", "B_speaker", "B_text", "B_sound_url",
        "B_tokens_norm", "B_lex_hits", "B_tok_count",
        "A_is_question", "B_is_question",
        "proposed_attach_root", "proposed_attach_last_content",
        "score", "reasons",
        "keep?"
    ]
    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for b_sent_id, row in rows_by_b.items():
            row["reasons"] = "|".join(sorted(reasons_by_b[b_sent_id]))
            w.writerow(row)

    print(f"Wrote {len(rows_by_b)} candidates to {out}")

if __name__ == "__main__":
    main()
