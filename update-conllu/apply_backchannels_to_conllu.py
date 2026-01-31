#!/usr/bin/env python3
"""
Apply reviewed backchannel decisions from CSV to a speaker-view CoNLL-U file.

Input:
- Reviewed CSV exported from Excel (often semicolon-delimited in EU locales).
  Must contain at least: A_sent_id, B_sent_id, keep?
- Speaker-view .conllu with # sent_id headers and token lines.

Output:
- Same .conllu content, but for each accepted B sentence, the ROOT token (HEAD=0)
  gets MISC feature: Backchannel=<A_sent_id>::<A_root_token_id>

Idempotent:
- If Backchannel= already exists on B root, it is replaced (not duplicated).
"""
import argparse
import csv
from pathlib import Path

KEEP_TRUE = {"1", "y", "yes", "true", "keep", "ok"}

def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="update-conllu/test_high_to_conllu.csv", help="Reviewed candidates CSV (with keep? column)")
    ap.add_argument("--conllu", default="src/sst/sl_sst-ud-merged.conllu", help="Input speaker-view .conllu")
    ap.add_argument("--out", default="update-conllu/sl_sst-ud-merged.backchannels.conllu", help="Output .conllu with Backchannel= added")
    ap.add_argument("--keep_col", default="keep?", help="Column name used for manual decisions (default: keep?)")
    ap.add_argument("--delimiter", default="", help="CSV delimiter (leave empty to auto-detect between ';' and ',')")
    return ap.parse_args()

def is_keep(val: str) -> bool:
    if val is None:
        return False
    return val.strip().lower() in KEEP_TRUE

def detect_delimiter(path: Path) -> str:
    # Excel in many EU locales uses ';'. We detect between ';' and ','.
    sample = path.read_text(encoding="utf-8-sig", errors="replace")[:4096]
    semi = sample.count(";")
    comma = sample.count(",")
    return ";" if semi >= comma else ","

def add_or_replace_misc_feature(misc: str, key: str, value: str) -> str:
    misc = (misc or "").strip()
    parts = [] if misc == "" or misc == "_" else misc.split("|")
    parts = [p for p in parts if not p.startswith(f"{key}=")]
    parts.append(f"{key}={value}")
    return "|".join(parts) if parts else "_"

def parse_token_cols(line: str):
    cols = line.rstrip("\n").split("\t")
    if len(cols) != 10:
        return None
    tok_id = cols[0]
    # Skip multiword tokens (2-3) and empty nodes (3.1)
    if "-" in tok_id or "." in tok_id:
        return None
    return cols

def main():
    args = parse_args()
    csv_path = Path(args.csv)
    conllu_path = Path(args.conllu)
    out_path = Path(args.out)

    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")
    if not conllu_path.exists():
        raise FileNotFoundError(f"CoNLL-U not found: {conllu_path}")

    delimiter = args.delimiter or detect_delimiter(csv_path)

    # 1) Load accepted decisions: B_sent_id -> A_sent_id
    b_to_a = {}
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f, delimiter=delimiter)
        if not r.fieldnames:
            raise ValueError("CSV has no header row.")
        if args.keep_col not in r.fieldnames:
            raise ValueError(f"CSV missing keep column '{args.keep_col}'. Found: {r.fieldnames}")
        for row in r:
            if not is_keep(row.get(args.keep_col, "")):
                continue
            b = (row.get("B_sent_id") or "").strip()
            a = (row.get("A_sent_id") or "").strip()
            if b and a:
                b_to_a[b] = a

    out_path.parent.mkdir(parents=True, exist_ok=True)

    # 2) Stream .conllu, record roots and patch selected B roots
    seen_roots = {}  # sent_id -> root token id
    patched = 0
    missing_a_root = 0
    missing_b_root = 0
    missing_sent_id = 0

    sent_lines = []
    cur_sent_id = None

    def flush_sentence(w):
        nonlocal sent_lines, cur_sent_id, patched, missing_a_root, missing_b_root, missing_sent_id

        if not sent_lines:
            w.write("\n")
            return

        # Find ROOT token (HEAD=0) for this sentence
        root_line_idx = None
        root_tok_id = None
        for i, line in enumerate(sent_lines):
            cols = parse_token_cols(line)
            if cols is None:
                continue
            if cols[6] == "0":
                root_line_idx = i
                root_tok_id = cols[0]
                break

        if cur_sent_id:
            if root_tok_id is not None:
                seen_roots[cur_sent_id] = root_tok_id
        else:
            missing_sent_id += 1

        # Patch if current sentence is an accepted B
        if cur_sent_id and cur_sent_id in b_to_a:
            a_sent_id = b_to_a[cur_sent_id]
            a_root_id = seen_roots.get(a_sent_id)
            if a_root_id is None:
                missing_a_root += 1
            elif root_line_idx is None:
                missing_b_root += 1
            else:
                cols = sent_lines[root_line_idx].rstrip("\n").split("\t")
                cols[9] = add_or_replace_misc_feature(cols[9], "Backchannel", f"{a_sent_id}::{a_root_id}")
                sent_lines[root_line_idx] = "\t".join(cols) + "\n"
                patched += 1

        for line in sent_lines:
            w.write(line)
        w.write("\n")

    with conllu_path.open("r", encoding="utf-8") as f_in, out_path.open("w", encoding="utf-8", newline="") as f_out:
        for line in f_in:
            if line.strip() == "":
                flush_sentence(f_out)
                sent_lines = []
                cur_sent_id = None
                continue

            sent_lines.append(line)

            if line.startswith("# sent_id"):
                parts = line.split("=", 1)
                if len(parts) == 2:
                    cur_sent_id = parts[1].strip()

        if sent_lines:
            flush_sentence(f_out)

    print(f"Accepted (keep): {len(b_to_a)}")
    print(f"Patched: {patched}")
    if missing_a_root:
        print(f"WARNING: missing A root for {missing_a_root} candidates (A not seen before B?)")
    if missing_b_root:
        print(f"WARNING: missing B root for {missing_b_root} candidates (no HEAD=0 token)")
    if missing_sent_id:
        print(f"WARNING: sentences without sent_id: {missing_sent_id}")
    print(f"Output: {out_path}")

if __name__ == "__main__":
    main()
