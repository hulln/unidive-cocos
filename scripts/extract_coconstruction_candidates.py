#!/usr/bin/env python3
"""
Extract first-pass coconstruction candidates from SST speaker-view CoNLL-U.

Strategy (AB only, adjacent different speakers):
1) Build A->B pairs where A and B are in the same document and speaker changes.
2) Keep pairs where A shows incompleteness cues (strong: orphan near end, truncation;
   weak: connector-like final token).
3) Filter obvious non-coconstructions in B (very short backchannel-like turns, question-like turns).
4) Rank candidates with a transparent score and export CSV for manual review.
"""

from __future__ import annotations

import argparse
import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple


QUESTION_WORDS = {
    "kaj",
    "kako",
    "kdo",
    "kje",
    "kdaj",
    "zakaj",
    "cemu",
    "kam",
    "odkod",
    "ali",
}

# Minimal list for obvious short listener responses.
BACKCHANNEL_LEXICON = {
    "mhm",
    "aha",
    "aja",
    "ja",
    "ne",
    "no",
    "ok",
    "okej",
    "hm",
    "mmm",
    "eee",
    "eem",
    "ah",
}

# Weak incompleteness cue when used as final non-punctuation token in A.
CONNECTOR_UPOS = {"ADP", "CCONJ", "SCONJ", "DET", "PRON"}
CONNECTOR_FORMS = {
    "pa",
    "in",
    "ali",
    "da",
    "ki",
    "ko",
    "ce",
    "za",
    "od",
    "do",
    "na",
    "v",
    "z",
    "s",
    "to",
    "ta",
    "tega",
    "kateri",
    "katero",
    "nekaj",
    "se",
    "tudi",
    "ampak",
}

CONTENT_UPOS = {"NOUN", "PROPN", "ADJ", "VERB", "NUM"}


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
class Utterance:
    doc: str
    sent_id: str
    speaker_id: str
    text: str
    tokens: List[Token]

    @property
    def nonpunct(self) -> List[Token]:
        return [t for t in self.tokens if t.upos != "PUNCT"]

    @property
    def root(self) -> Optional[Token]:
        for t in self.tokens:
            if t.head == 0:
                return t
        return None


def parse_conllu(path: Path) -> List[Utterance]:
    utterances: List[Utterance] = []
    meta: Dict[str, str] = {}
    tokens: List[Token] = []
    current_doc = ""

    def flush() -> None:
        nonlocal meta, tokens, current_doc
        if not meta and not tokens:
            return
        if "newdoc id" in meta:
            current_doc = meta["newdoc id"]
        sent_id = meta.get("sent_id", "")
        if not current_doc and ".s" in sent_id:
            current_doc = sent_id.split(".s", 1)[0]
        utterances.append(
            Utterance(
                doc=current_doc,
                sent_id=sent_id,
                speaker_id=meta.get("speaker_id", ""),
                text=meta.get("text", ""),
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
                    key, value = line[1:].split("=", 1)
                    meta[key.strip()] = value.strip()
                continue

            cols = line.split("\t")
            if len(cols) < 8:
                continue
            tid = cols[0]
            if "-" in tid or "." in tid:
                continue
            try:
                tid_int = int(tid)
            except ValueError:
                continue

            head: Optional[int] = None
            if cols[6].isdigit():
                head = int(cols[6])

            tokens.append(
                Token(
                    tid=tid_int,
                    form=cols[1],
                    lemma=cols[2],
                    upos=cols[3],
                    head=head,
                    deprel=cols[7],
                    misc=cols[9] if len(cols) > 9 else "_",
                )
            )

    flush()
    return utterances


def is_truncated(tok: Token) -> bool:
    if tok.form.endswith("-"):
        return True
    # In SST this often appears in MISC pronunciation with either unicode ellipsis or "..."
    return ("..." in tok.misc) or ("\u2026" in tok.misc)


def normalize(s: str) -> str:
    return s.strip().lower()


def without_diacritics_sl(s: str) -> str:
    # Lightweight normalization for cue lists.
    return (
        s.replace("č", "c")
        .replace("š", "s")
        .replace("ž", "z")
        .replace("Č", "C")
        .replace("Š", "S")
        .replace("Ž", "Z")
    )


def is_backchannel_like(utt: Utterance) -> bool:
    toks = utt.nonpunct
    if not toks or len(toks) > 3:
        return False
    forms = [normalize(t.form) for t in toks]
    return all(f in BACKCHANNEL_LEXICON for f in forms)


def is_question_like(utt: Utterance) -> bool:
    if "?" in utt.text:
        return True
    toks = utt.nonpunct
    if not toks:
        return False
    first = normalize(toks[0].form)
    return without_diacritics_sl(first) in QUESTION_WORDS


def a_incompleteness_flags(utt_a: Utterance) -> Dict[str, bool]:
    toks = utt_a.tokens
    nonp = utt_a.nonpunct
    last_two = toks[-2:] if len(toks) >= 2 else toks

    orphan_last2 = any(t.deprel == "orphan" for t in last_two)
    truncation = any(is_truncated(t) for t in toks)

    end_connector = False
    if nonp:
        end = nonp[-1]
        end_form = without_diacritics_sl(normalize(end.form))
        end_connector = (end.upos in CONNECTOR_UPOS) or (end_form in CONNECTOR_FORMS)

    return {
        "a_orphan_last2": orphan_last2,
        "a_truncation": truncation,
        "a_end_connector": end_connector,
    }


def content_overlap(utt_a: Utterance, utt_b: Utterance) -> Tuple[bool, str]:
    a_set = {
        normalize(t.lemma if t.lemma != "_" else t.form)
        for t in utt_a.nonpunct
        if t.upos in CONTENT_UPOS
    }
    b_set = {
        normalize(t.lemma if t.lemma != "_" else t.form)
        for t in utt_b.nonpunct
        if t.upos in CONTENT_UPOS
    }
    overlap = sorted(x for x in (a_set & b_set) if x)
    return (len(overlap) > 0, "|".join(overlap[:6]))


def score_candidate(
    flags: Dict[str, bool],
    b_len: int,
    b_backchannel_like: bool,
    b_question_like: bool,
    has_overlap: bool,
) -> Tuple[int, str]:
    score = 0
    if flags["a_orphan_last2"]:
        score += 35
    if flags["a_truncation"]:
        score += 30
    if flags["a_end_connector"]:
        score += 12

    if b_len <= 2:
        score += 12
    elif b_len <= 4:
        score += 8
    elif b_len <= 8:
        score += 3
    else:
        score -= 10

    if has_overlap:
        score += 12
    if b_backchannel_like:
        score -= 35
    if b_question_like:
        score -= 25

    score = max(0, min(100, score))
    if score >= 60:
        label = "HIGH"
    elif score >= 40:
        label = "MEDIUM"
    else:
        label = "LOW"
    return score, label


def build_ab_candidates(
    utterances: Sequence[Utterance],
    max_b_tokens: int,
    include_question_like: bool,
    include_backchannel_like: bool,
) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []

    for i in range(1, len(utterances)):
        a = utterances[i - 1]
        b = utterances[i]
        if not a.doc or a.doc != b.doc:
            continue
        if not a.speaker_id or not b.speaker_id:
            continue
        if a.speaker_id == b.speaker_id:
            continue

        flags = a_incompleteness_flags(a)
        strong_or_weak = flags["a_orphan_last2"] or flags["a_truncation"] or flags["a_end_connector"]
        if not strong_or_weak:
            continue

        b_len = len(b.nonpunct)
        if b_len == 0 or b_len > max_b_tokens:
            continue

        b_bc_like = is_backchannel_like(b)
        b_q_like = is_question_like(b)
        if b_bc_like and not include_backchannel_like:
            continue
        if b_q_like and not include_question_like:
            continue

        overlap_yes, overlap_lemmas = content_overlap(a, b)
        score, conf = score_candidate(flags, b_len, b_bc_like, b_q_like, overlap_yes)

        a_root = a.root
        proposed_attach = ""
        if a_root is not None:
            proposed_attach = f"{a.sent_id}::{a_root.tid}"

        why = []
        if flags["a_orphan_last2"]:
            why.append("A orphan near end")
        if flags["a_truncation"]:
            why.append("A truncation marker")
        if flags["a_end_connector"]:
            why.append("A connector-like ending")
        if overlap_yes:
            why.append("A/B lexical overlap")

        rows.append(
            {
                "doc": a.doc,
                "confidence": conf,
                "confidence_score": str(score),
                "A_sent_id": a.sent_id,
                "A_speaker": a.speaker_id,
                "A_text": a.text,
                "B_sent_id": b.sent_id,
                "B_speaker": b.speaker_id,
                "B_text": b.text,
                "B_nonpunct_token_count": str(b_len),
                "A_root_token_id": str(a_root.tid if a_root else ""),
                "A_root_form": a_root.form if a_root else "",
                "A_root_upos": a_root.upos if a_root else "",
                "B_root_form": b.root.form if b.root else "",
                "B_root_upos": b.root.upos if b.root else "",
                "a_orphan_last2": str(flags["a_orphan_last2"]),
                "a_truncation": str(flags["a_truncation"]),
                "a_end_connector": str(flags["a_end_connector"]),
                "b_backchannel_like": str(b_bc_like),
                "b_question_like": str(b_q_like),
                "a_b_lexical_overlap": str(overlap_yes),
                "overlap_lemmas": overlap_lemmas,
                "why_candidate": "; ".join(why),
                "proposed_attach_A_root": proposed_attach,
                "keep?": "",
                "proposed_coconstruct_deprel": "",
                "proposed_coconstruct_misc": "",
            }
        )

    rows.sort(key=lambda r: int(r["confidence_score"]), reverse=True)
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description="Extract coconstruction candidates (AB adjacent turns).")
    ap.add_argument(
        "--input",
        default="src/sst/sl_sst-ud-merged.conllu",
        help="Input CoNLL-U (default: src/sst/sl_sst-ud-merged.conllu)",
    )
    ap.add_argument(
        "--output",
        default="output/sst/coconstruction_candidates_ab.csv",
        help="Output CSV path (default: output/sst/coconstruction_candidates_ab.csv)",
    )
    ap.add_argument(
        "--max_b_tokens",
        type=int,
        default=8,
        help="Max non-punctuation token count for B (default: 8)",
    )
    ap.add_argument(
        "--include_question_like",
        action="store_true",
        help="Keep question-like B turns (default: excluded)",
    )
    ap.add_argument(
        "--include_backchannel_like",
        action="store_true",
        help="Keep obvious short backchannel-like B turns (default: excluded)",
    )
    args = ap.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    utterances = parse_conllu(input_path)
    rows = build_ab_candidates(
        utterances=utterances,
        max_b_tokens=args.max_b_tokens,
        include_question_like=args.include_question_like,
        include_backchannel_like=args.include_backchannel_like,
    )

    fieldnames = [
        "doc",
        "confidence",
        "confidence_score",
        "A_sent_id",
        "A_speaker",
        "A_text",
        "B_sent_id",
        "B_speaker",
        "B_text",
        "B_nonpunct_token_count",
        "A_root_token_id",
        "A_root_form",
        "A_root_upos",
        "B_root_form",
        "B_root_upos",
        "a_orphan_last2",
        "a_truncation",
        "a_end_connector",
        "b_backchannel_like",
        "b_question_like",
        "a_b_lexical_overlap",
        "overlap_lemmas",
        "why_candidate",
        "proposed_attach_A_root",
        "keep?",
        "proposed_coconstruct_deprel",
        "proposed_coconstruct_misc",
    ]

    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Input utterances: {len(utterances)}")
    print(f"Candidates written: {len(rows)}")
    print(f"Output: {output_path}")


if __name__ == "__main__":
    main()
