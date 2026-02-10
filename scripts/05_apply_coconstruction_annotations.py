#!/usr/bin/env python3
"""
Workflow step 05: apply coconstruction annotations to CoNLL-U.

Reads a manually annotated sheet (xlsx/csv) with columns:
- a_sent_id
- b_sent_id
- coconstruct_deprel
- governor_token_id
(optional) is_coconstruction

Writes Coconstruct=<deprel>::<a_sent_id>::<governor_token_id>
into MISC of the root token of sentence B.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


YES_VALUES = {"1", "yes", "y", "true"}


@dataclass
class CocoRow:
    a_sent_id: str
    b_sent_id: str
    deprel: str
    governor_token_id: int


@dataclass
class TokenInfo:
    tid: int
    head: Optional[int]
    deprel: str


@dataclass
class SentenceInfo:
    sent_id: str
    tokens: List[TokenInfo]


def _load_rows(path: Path) -> List[Dict[str, str]]:
    if path.suffix.lower() in {".xlsx", ".xls"}:
        import pandas as pd  # local import to keep startup light

        df = pd.read_excel(path)
        return [{str(k): ("" if v is None else str(v)) for k, v in row.items()} for row in df.to_dict(orient="records")]

    if path.suffix.lower() == ".csv":
        with path.open("r", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    raise ValueError(f"Unsupported annotations format: {path}")


def load_coconstructions(path: Path) -> Dict[str, CocoRow]:
    rows = _load_rows(path)
    ann: Dict[str, CocoRow] = {}

    for i, raw in enumerate(rows, start=2):
        norm = {k.strip(): (v.strip() if isinstance(v, str) else str(v).strip()) for k, v in raw.items()}

        # Optional filter column
        if "is_coconstruction" in norm and norm["is_coconstruction"]:
            if norm["is_coconstruction"].lower() not in YES_VALUES:
                continue

        for col in ["a_sent_id", "b_sent_id", "coconstruct_deprel", "governor_token_id"]:
            if col not in norm:
                raise ValueError(f"Missing required column '{col}' in annotations file")

        a_sid = norm["a_sent_id"]
        b_sid = norm["b_sent_id"]
        dep = norm["coconstruct_deprel"]
        gov_raw = norm["governor_token_id"]

        if not a_sid or not b_sid or not dep or not gov_raw:
            continue

        try:
            gov = int(float(gov_raw))
        except ValueError as exc:
            raise ValueError(f"Row {i}: invalid governor_token_id '{gov_raw}'") from exc

        row = CocoRow(a_sent_id=a_sid, b_sent_id=b_sid, deprel=dep, governor_token_id=gov)

        prev = ann.get(b_sid)
        if prev and prev != row:
            raise ValueError(
                f"Conflicting duplicate b_sent_id={b_sid}: "
                f"{prev} vs {row}"
            )
        ann[b_sid] = row

    return ann


def parse_sentence_index(lines: List[str]) -> Dict[str, SentenceInfo]:
    sent_map: Dict[str, SentenceInfo] = {}
    meta_sid: Optional[str] = None
    toks: List[TokenInfo] = []

    def flush() -> None:
        nonlocal meta_sid, toks
        if meta_sid is None:
            toks = []
            return
        sent_map[meta_sid] = SentenceInfo(sent_id=meta_sid, tokens=toks.copy())
        meta_sid = None
        toks = []

    for line in lines:
        if line == "":
            flush()
            continue

        if line.startswith("# sent_id = "):
            meta_sid = line.split("=", 1)[1].strip()
            continue

        if line.startswith("#"):
            continue

        cols = line.split("\t")
        if len(cols) != 10:
            continue

        tid = cols[0]
        if "-" in tid or "." in tid:
            continue

        try:
            tid_i = int(tid)
        except ValueError:
            continue

        head = int(cols[6]) if cols[6].isdigit() else None
        toks.append(TokenInfo(tid=tid_i, head=head, deprel=cols[7]))

    flush()
    return sent_map


def validate_references(ann: Dict[str, CocoRow], sents: Dict[str, SentenceInfo]) -> None:
    for b_sid, row in ann.items():
        if row.a_sent_id not in sents:
            raise ValueError(f"Missing A sentence in input CoNLL-U: {row.a_sent_id}")
        if b_sid not in sents:
            raise ValueError(f"Missing B sentence in input CoNLL-U: {b_sid}")

        a_ids = {t.tid for t in sents[row.a_sent_id].tokens}
        if row.governor_token_id not in a_ids:
            raise ValueError(
                f"Governor token {row.governor_token_id} not found in A={row.a_sent_id}"
            )

        roots = [t for t in sents[b_sid].tokens if t.head == 0 or t.deprel == "root"]
        if len(roots) != 1:
            raise ValueError(f"B sentence {b_sid} must have exactly one root, found {len(roots)}")


def apply_annotations(lines: List[str], ann: Dict[str, CocoRow]) -> Tuple[List[str], int]:
    out: List[str] = []
    current_sid: Optional[str] = None
    applied = 0

    for line in lines:
        if line.startswith("# sent_id = "):
            current_sid = line.split("=", 1)[1].strip()
            out.append(line)
            continue

        if line.startswith("#") or line == "":
            out.append(line)
            continue

        cols = line.split("\t")
        if len(cols) != 10:
            out.append(line)
            continue

        tid = cols[0]
        if "-" in tid or "." in tid:
            out.append(line)
            continue

        if current_sid in ann and cols[6] == "0":
            row = ann[current_sid]
            feature = f"Coconstruct={row.deprel}::{row.a_sent_id}::{row.governor_token_id}"
            misc = cols[9]
            if misc == "_":
                cols[9] = feature
            elif feature not in misc.split("|"):
                cols[9] = misc + "|" + feature
            line = "\t".join(cols)
            applied += 1

        out.append(line)

    return out, applied


def main() -> None:
    ap = argparse.ArgumentParser(description="Apply coconstruction annotations to CoNLL-U")
    ap.add_argument(
        "--annotations",
        default="output/sst/final_bc_coco/annotations/coconstruction_17_final.xlsx",
        help="Path to annotated coconstruction sheet (xlsx/csv)",
    )
    ap.add_argument(
        "--input",
        default="output/sst/sl_sst-ud-merged.backchannels.conllu",
        help="Input CoNLL-U (typically backchannels-applied merged file)",
    )
    ap.add_argument(
        "--output",
        default="output/sst/final_bc_coco/conllu/sl_sst-ud-merged.conllu",
        help="Output CoNLL-U with coconstructions applied",
    )
    args = ap.parse_args()

    ann_path = Path(args.annotations)
    in_path = Path(args.input)
    out_path = Path(args.output)

    ann = load_coconstructions(ann_path)
    lines = in_path.read_text(encoding="utf-8").splitlines()
    sents = parse_sentence_index(lines)
    validate_references(ann, sents)

    out_lines, applied = apply_annotations(lines, ann)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")

    print(f"Loaded coconstruction rows: {len(ann)}")
    print(f"Applied coconstructions:     {applied}")
    print(f"Input file:                 {in_path}")
    print(f"Output file:                {out_path}")


if __name__ == "__main__":
    main()
