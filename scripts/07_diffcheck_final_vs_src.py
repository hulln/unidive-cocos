#!/usr/bin/env python3
"""
Workflow step 07: strict diff check between src splits and final splits.
Ensures only MISC token-level additions are present.
"""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
from typing import List, Tuple


def compare_pair(src_path: Path, out_path: Path) -> Tuple[Counter, List[Tuple[int, str, str, str]]]:
    src = src_path.read_text(encoding="utf-8").splitlines()
    out = out_path.read_text(encoding="utf-8").splitlines()
    maxlen = max(len(src), len(out))

    cnt = Counter()
    bad_samples: List[Tuple[int, str, str, str]] = []

    src_sids = [ln.split("=", 1)[1].strip() for ln in src if ln.startswith("# sent_id = ")]
    out_sids = [ln.split("=", 1)[1].strip() for ln in out if ln.startswith("# sent_id = ")]
    if src_sids != out_sids:
        cnt["sent_id_sequence_mismatch"] += 1

    for i in range(maxlen):
        a = src[i] if i < len(src) else None
        b = out[i] if i < len(out) else None
        if a == b:
            continue

        cnt["diff_lines"] += 1

        if a is None or b is None:
            cnt["line_count_mismatch"] += 1
            if len(bad_samples) < 8:
                bad_samples.append((i + 1, "line_count_mismatch", str(a), str(b)))
            continue

        if a.startswith("#") or b.startswith("#") or a == "" or b == "":
            cnt["meta_or_blank_changed"] += 1
            if len(bad_samples) < 8:
                bad_samples.append((i + 1, "meta_or_blank_changed", a, b))
            continue

        ac = a.split("\t")
        bc = b.split("\t")
        if len(ac) != 10 or len(bc) != 10:
            cnt["non_10col_token_changed"] += 1
            if len(bad_samples) < 8:
                bad_samples.append((i + 1, "non_10col_token_changed", a, b))
            continue

        if all(ac[j] == bc[j] for j in range(9)) and ac[9] != bc[9]:
            cnt["misc_only_changes"] += 1
            if "Backchannel=" in bc[9] and "Backchannel=" not in ac[9]:
                cnt["added_backchannel"] += 1
            if "Coconstruct=" in bc[9] and "Coconstruct=" not in ac[9]:
                cnt["added_coconstruct"] += 1
            if not (
                ("Backchannel=" in bc[9] and "Backchannel=" not in ac[9])
                or ("Coconstruct=" in bc[9] and "Coconstruct=" not in ac[9])
            ):
                cnt["misc_other_change"] += 1
                if len(bad_samples) < 8:
                    bad_samples.append((i + 1, "misc_other_change", a, b))
        else:
            cnt["token_cols_0_8_changed"] += 1
            if len(bad_samples) < 8:
                bad_samples.append((i + 1, "token_cols_0_8_changed", a, b))

    return cnt, bad_samples


def main() -> None:
    ap = argparse.ArgumentParser(description="Strict diff check: src vs final CoNLL-U files")
    ap.add_argument("--src-dir", default="src/sst")
    ap.add_argument("--final-dir", default="output/sst/final_bc_coco/conllu")
    ap.add_argument("--report", default="output/sst/final_bc_coco/reports/diffcheck_src_vs_final.txt")
    args = ap.parse_args()

    src_dir = Path(args.src_dir)
    final_dir = Path(args.final_dir)
    report = Path(args.report)
    report.parent.mkdir(parents=True, exist_ok=True)

    pairs = [
        ("merged", src_dir / "sl_sst-ud-merged.conllu", final_dir / "sl_sst-ud-merged.conllu"),
        ("train", src_dir / "sl_sst-ud-train.conllu", final_dir / "sl_sst-ud-train.conllu"),
        ("dev", src_dir / "sl_sst-ud-dev.conllu", final_dir / "sl_sst-ud-dev.conllu"),
        ("test", src_dir / "sl_sst-ud-test.conllu", final_dir / "sl_sst-ud-test.conllu"),
    ]

    out_lines: List[str] = []
    overall_ok = True

    for name, srcp, outp in pairs:
        cnt, bad = compare_pair(srcp, outp)
        unexpected = (
            cnt["line_count_mismatch"]
            + cnt["meta_or_blank_changed"]
            + cnt["non_10col_token_changed"]
            + cnt["token_cols_0_8_changed"]
            + cnt["misc_other_change"]
            + cnt["sent_id_sequence_mismatch"]
        )
        ok = unexpected == 0
        overall_ok = overall_ok and ok

        src_lines = srcp.read_text(encoding="utf-8").splitlines()
        out_lines_file = outp.read_text(encoding="utf-8").splitlines()
        src_sids = [ln for ln in src_lines if ln.startswith("# sent_id = ")]
        out_sids = [ln for ln in out_lines_file if ln.startswith("# sent_id = ")]

        out_lines.append(f"[{name}]")
        out_lines.append(f"- src: {srcp}")
        out_lines.append(f"- out: {outp}")
        out_lines.append(f"- line counts src/out: {len(src_lines)}/{len(out_lines_file)}")
        out_lines.append(f"- sentence counts src/out: {len(src_sids)}/{len(out_sids)}")
        out_lines.append(f"- sent_id sequence identical: {src_sids == out_sids}")
        out_lines.append(f"- total diff lines: {cnt['diff_lines']}")
        out_lines.append(f"- misc-only changes: {cnt['misc_only_changes']}")
        out_lines.append(f"- added Backchannel lines: {cnt['added_backchannel']}")
        out_lines.append(f"- added Coconstruct lines: {cnt['added_coconstruct']}")
        out_lines.append(f"- unexpected changes: {unexpected}")
        out_lines.append(f"- status: {'PASS' if ok else 'FAIL'}")
        if bad:
            out_lines.append("- unexpected samples:")
            for ln_no, kind, a, b in bad:
                out_lines.append(f"  - line {ln_no} [{kind}]")
                out_lines.append(f"    src: {a}")
                out_lines.append(f"    out: {b}")
        out_lines.append("")

    out_lines.insert(0, f"Overall status: {'PASS' if overall_ok else 'FAIL'}")
    report.write_text("\n".join(out_lines) + "\n", encoding="utf-8")

    print(f"Overall status: {'PASS' if overall_ok else 'FAIL'}")
    print(f"Report: {report}")


if __name__ == "__main__":
    main()
