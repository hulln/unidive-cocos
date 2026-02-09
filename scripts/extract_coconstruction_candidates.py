#!/usr/bin/env python3
"""
Extract AB co-construction candidates from the SST corpus.

Hard filters (fixed, simple):
  1. Consecutive A->B pair with speaker change in same document.
  2. A has no final sentence punctuation (. ? ! …).
  3. B is not already annotated as backchannel.
  4. B is excluded if it contains only filler tokens.
  5. B is excluded if its first content token is filler.

Soft signals are exported as columns for manual filtering in Excel.
No soft signal excludes a row automatically.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set


SENT_END_PUNCT = {".", "?", "!", "…"}
# Fillers often start noisy B turns but are not always in the lexicon.
EXTRA_NOISY_STARTERS = {"eee", "eem", "hm", "hmm", "uh", "uhh"}
FILLER_FORMS = {"e", "ee", "eee", "eem", "em", "emm", "hm", "hmm", "uh", "uhh"}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def parse_conllu(path: Path) -> List[Sent]:
    """Parse a CoNLL-U file into a list of Sent objects."""
    sents: List[Sent] = []
    meta: Dict[str, str] = {}
    tokens: List[Token] = []
    current_doc: str = ""

    def flush() -> None:
        nonlocal meta, tokens, current_doc
        if not meta and not tokens:
            return
        if "newdoc id" in meta:
            current_doc = meta["newdoc id"]
        sents.append(
            Sent(
                doc=current_doc,
                sent_id=meta.get("sent_id", ""),
                speaker=meta.get("speaker_id", ""),
                text=meta.get("text", ""),
                sound_url=meta.get("sound_url", "NA"),
                tokens=tokens,
            )
        )
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
                    meta[k.strip()] = v.strip()
                continue

            cols = line.split("\t")
            if len(cols) < 8:
                continue
            tid_str = cols[0]
            if "-" in tid_str or "." in tid_str:
                continue
            try:
                tid_i = int(tid_str)
            except ValueError:
                continue

            head = int(cols[6]) if cols[6].isdigit() else None
            misc = cols[9] if len(cols) > 9 else "_"
            tokens.append(
                Token(
                    tid=tid_i,
                    form=cols[1],
                    lemma=cols[2],
                    upos=cols[3],
                    head=head,
                    deprel=cols[7],
                    misc=misc,
                )
            )
    flush()
    return sents


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def normalize_word(text: str) -> str:
    """Lowercase token and trim surrounding punctuation."""
    return text.strip().strip(".,?!;:\"'()[]{}").lower()


def content_tokens(sent: Sent) -> List[Token]:
    """Return non-PUNCT tokens."""
    return [t for t in sent.tokens if t.upos != "PUNCT"]


def first_text_token(text: str) -> str:
    """Return first normalized token from raw sentence text."""
    for tok in text.split():
        norm = normalize_word(tok)
        if norm:
            return norm
    return ""


def load_backchannel_lexicon(path: Path) -> Set[str]:
    """Load `word|category` style lexicon, return only words."""
    words: Set[str] = set()
    if not path.exists():
        print(f"Warning: Backchannel lexicon not found at {path}")
        return words
    with path.open("r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            word = line.split("|", 1)[0].strip().lower()
            if word:
                words.add(word)
    return words


def load_annotated_backchannels(path: Path) -> Set[str]:
    """Load sentence IDs already annotated as backchannels."""
    backchannel_sent_ids: Set[str] = set()
    if not path.exists():
        print(f"Warning: Backchannel annotation file not found at {path}")
        return backchannel_sent_ids

    current_sent_id: Optional[str] = None
    has_backchannel = False

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith("# sent_id"):
                if current_sent_id and has_backchannel:
                    backchannel_sent_ids.add(current_sent_id)
                current_sent_id = line.split("=", 1)[-1].strip()
                has_backchannel = False
            elif line == "":
                if current_sent_id and has_backchannel:
                    backchannel_sent_ids.add(current_sent_id)
                current_sent_id = None
                has_backchannel = False
            elif not line.startswith("#") and "\t" in line:
                cols = line.split("\t")
                if len(cols) > 9 and "Backchannel=" in cols[9]:
                    has_backchannel = True

    if current_sent_id and has_backchannel:
        backchannel_sent_ids.add(current_sent_id)

    return backchannel_sent_ids


def root_token(sent: Sent) -> Optional[Token]:
    """Return root token in sentence."""
    for tok in sent.tokens:
        if tok.deprel == "root":
            return tok
    return None


# ---------------------------------------------------------------------------
# Signal detectors
# ---------------------------------------------------------------------------


def sig_no_final_punct(a: Sent) -> bool:
    """A is unfinished if last token is not sentence-ending punctuation."""
    if not a.tokens:
        return False
    return a.tokens[-1].form not in SENT_END_PUNCT


def sig_orphan_tail(a: Sent) -> bool:
    """A has an 'orphan' dependency among last 3 content tokens."""
    ct = content_tokens(a)
    if not ct:
        return False
    return any(tok.deprel == "orphan" for tok in ct[-3:])


def is_filler_token(tok: Token) -> bool:
    """Return True for filler-like tokens (incl. discourse:filler annotation)."""
    form = normalize_word(tok.form)
    return tok.deprel == "discourse:filler" or form in FILLER_FORMS


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Extract AB co-construction candidates from SST corpus"
    )
    ap.add_argument(
        "--input",
        default=None,
        help="Path to merged .conllu (default: src/sst/sl_sst-ud-merged.conllu)",
    )
    ap.add_argument(
        "--output",
        default=None,
        help="Output CSV path (default: output/sst/coconstruction_candidates.csv)",
    )
    ap.add_argument(
        "--backchannels",
        default=None,
        help="Path to backchannel-annotated CoNLL-U (default: output/sst/sl_sst-ud-merged.backchannels.conllu)",
    )
    ap.add_argument(
        "--backchannel-lexicon",
        default=None,
        help="Path to backchannel lexicon (default: lexicon/sl_backchannels.txt)",
    )
    args = ap.parse_args()

    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    if args.input is None:
        args.input = str(project_root / "src" / "sst" / "sl_sst-ud-merged.conllu")
    if args.output is None:
        output_dir = project_root / "output" / "sst"
        output_dir.mkdir(parents=True, exist_ok=True)
        args.output = str(output_dir / "coconstruction_candidates.csv")

    bc_path = (
        Path(args.backchannels)
        if args.backchannels
        else project_root / "output" / "sst" / "sl_sst-ud-merged.backchannels.conllu"
    )
    backchannel_sent_ids = load_annotated_backchannels(bc_path)
    print(f"Loaded {len(backchannel_sent_ids)} annotated backchannels from {bc_path}")

    lex_path = (
        Path(args.backchannel_lexicon)
        if args.backchannel_lexicon
        else project_root / "lexicon" / "sl_backchannels.txt"
    )
    backchannel_lexicon = load_backchannel_lexicon(lex_path)
    noisy_starters = backchannel_lexicon | EXTRA_NOISY_STARTERS
    print(f"Loaded {len(backchannel_lexicon)} lexicon entries from {lex_path}")

    path = Path(args.input)
    sents = parse_conllu(path)
    print(f"Parsed {len(sents)} sentences from {path}")

    candidates: List[dict] = []

    total_diff_pairs = 0
    unfinished_pairs = 0
    dropped_backchannel = 0
    dropped_first_filler = 0
    dropped_only_filler = 0

    for i in range(len(sents) - 1):
        a = sents[i]
        b = sents[i + 1]

        # Hard filter 1: AB in same doc with speaker change.
        if a.doc != b.doc:
            continue
        if not a.speaker or not b.speaker:
            continue
        if a.speaker == b.speaker:
            continue
        total_diff_pairs += 1

        # Hard filter 2: A must be unfinished by punctuation criterion.
        if not sig_no_final_punct(a):
            continue
        unfinished_pairs += 1

        # Hard filter 3: Exclude annotated backchannels.
        if b.sent_id in backchannel_sent_ids:
            dropped_backchannel += 1
            continue

        b_ct = content_tokens(b)
        b_count = len(b_ct)
        if not b_ct:
            # Keep behavior explicit; with 0 content tokens we cannot check fillers.
            continue

        first_is_filler = is_filler_token(b_ct[0])
        only_fillers = all(is_filler_token(tok) for tok in b_ct)

        # Hard filter 4: B consists only of filler tokens.
        if only_fillers:
            dropped_only_filler += 1
            continue

        # Hard filter 5: B first content token is filler (e.g., eem/eee/e/hm).
        if first_is_filler:
            dropped_first_filler += 1
            continue

        ort = sig_orphan_tail(a)
        a_continues = 0
        if i + 2 < len(sents):
            c = sents[i + 2]
            if c.doc == a.doc and c.speaker == a.speaker:
                a_continues = 1

        b_root = root_token(b)
        b_first_token = first_text_token(b.text)
        b_has_question = "?" in b.text
        b_starts_backchannel_like = b_first_token in noisy_starters
        b_root_is_intj_part = int(bool(b_root and b_root.upos in {"INTJ", "PART"}))

        candidates.append(
            {
                "doc": a.doc,
                "a_sent_id": a.sent_id,
                "a_speaker": a.speaker,
                "a_text": a.text,
                "a_sound_url": a.sound_url,
                "b_sent_id": b.sent_id,
                "b_speaker": b.speaker,
                "b_text": b.text,
                "b_sound_url": b.sound_url,
                "len": b_count,
                "b_root_upos": b_root.upos if b_root else "",
                "b_root_form": b_root.form if b_root else "",
                "orphan_tail": int(ort),
                "a_continues": a_continues,
                "a_is_question": int("?" in a.text),
                "b_first_token": b_first_token,
                "b_starts_backchannel_like": int(b_starts_backchannel_like),
                "b_has_question_mark": int(b_has_question),
                "b_root_is_intj_part": b_root_is_intj_part,
                "is_coconstruction": "",
                "coconstruct_deprel": "",
                "governor_token_id": "",
                "notes": "",
            }
        )

    candidates.sort(key=lambda row: row["len"])

    out = Path(args.output)
    fieldnames = [
        "doc",
        "a_sent_id",
        "a_speaker",
        "a_text",
        "a_sound_url",
        "b_sent_id",
        "b_speaker",
        "b_text",
        "b_sound_url",
        "len",
        "b_root_upos",
        "b_root_form",
        "orphan_tail",
        "a_continues",
        "a_is_question",
        "b_first_token",
        "b_starts_backchannel_like",
        "b_has_question_mark",
        "b_root_is_intj_part",
        "is_coconstruction",
        "coconstruct_deprel",
        "governor_token_id",
        "notes",
    ]

    with out.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in candidates:
            writer.writerow(row)

    print(f"\nConsecutive AB pairs:                 {total_diff_pairs:4d}")
    print(f"A unfinished (hard filter):           {unfinished_pairs:4d}")
    print(f"Dropped due annotated backchannel:    {dropped_backchannel:4d}")
    print(f"Dropped: B starts with filler:        {dropped_first_filler:4d}")
    print(f"Dropped: B only filler tokens:        {dropped_only_filler:4d}")
    print(f"Extracted candidates:                 {len(candidates):4d}")
    print(f"  orphan_tail=1:                      {sum(1 for r in candidates if r['orphan_tail']):4d}")
    print(f"  a_continues=1:                      {sum(1 for r in candidates if r['a_continues']):4d}")
    print(f"  b_starts_backchannel_like=1:        {sum(1 for r in candidates if r['b_starts_backchannel_like']):4d}")
    print(f"  b_has_question_mark=1:              {sum(1 for r in candidates if r['b_has_question_mark']):4d}")
    print(f"  len <= 3:                           {sum(1 for r in candidates if r['len'] <= 3):4d}")
    print(f"  len <= 7:                           {sum(1 for r in candidates if r['len'] <= 7):4d}")
    print(f"\nWrote results to {out}")


if __name__ == "__main__":
    main()
