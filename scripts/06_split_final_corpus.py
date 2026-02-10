#!/usr/bin/env python3
"""
Workflow step 06: split final merged CoNLL-U into train/dev/test
using sentence membership/order from src/sst split files.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List, Tuple


def parse_blocks(path: Path) -> List[Tuple[str, List[str]]]:
    blocks: List[List[str]] = []
    cur: List[str] = []

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip() == "":
                if cur:
                    blocks.append(cur)
                    cur = []
            else:
                cur.append(line)
        if cur:
            blocks.append(cur)

    out: List[Tuple[str, List[str]]] = []
    for b in blocks:
        sid = None
        for ln in b:
            if ln.startswith("# sent_id = "):
                sid = ln.split("=", 1)[1].strip()
                break
        if sid is None:
            raise ValueError(f"Block without sent_id in {path}")
        out.append((sid, b))

    return out


def write_split(
    sids: List[str],
    merged_map: Dict[str, List[str]],
    out_path: Path,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as out:
        for sid in sids:
            out.writelines(merged_map[sid])
            out.write("\n")


def main() -> None:
    ap = argparse.ArgumentParser(description="Split final merged CoNLL-U into train/dev/test")
    ap.add_argument(
        "--merged",
        default="output/sst/final_bc_coco/conllu/sl_sst-ud-merged.conllu",
        help="Merged annotated CoNLL-U",
    )
    ap.add_argument("--src-train", default="src/sst/sl_sst-ud-train.conllu")
    ap.add_argument("--src-dev", default="src/sst/sl_sst-ud-dev.conllu")
    ap.add_argument("--src-test", default="src/sst/sl_sst-ud-test.conllu")
    ap.add_argument(
        "--out-dir",
        default="output/sst/final_bc_coco/conllu",
        help="Output directory for split files",
    )
    args = ap.parse_args()

    merged_path = Path(args.merged)
    out_dir = Path(args.out_dir)

    merged_blocks = parse_blocks(merged_path)
    merged_map = {sid: block for sid, block in merged_blocks}

    split_inputs = {
        "train": Path(args.src_train),
        "dev": Path(args.src_dev),
        "test": Path(args.src_test),
    }

    split_sid_orders: Dict[str, List[str]] = {}
    for split, path in split_inputs.items():
        split_sid_orders[split] = [sid for sid, _ in parse_blocks(path)]

    # Validate union and disjointness against merged.
    split_sets = {k: set(v) for k, v in split_sid_orders.items()}
    if (split_sets["train"] & split_sets["dev"]) or (split_sets["train"] & split_sets["test"]) or (split_sets["dev"] & split_sets["test"]):
        raise ValueError("train/dev/test split sentence IDs overlap")

    union = split_sets["train"] | split_sets["dev"] | split_sets["test"]
    merged_set = set(merged_map.keys())
    if union != merged_set:
        raise ValueError(
            "Split union does not match merged sentence set: "
            f"missing_in_splits={len(merged_set - union)} extra_in_splits={len(union - merged_set)}"
        )

    # Validate all referenced IDs exist in merged map.
    for split, sids in split_sid_orders.items():
        missing = [sid for sid in sids if sid not in merged_map]
        if missing:
            raise ValueError(f"{split}: {len(missing)} sent_ids missing in merged (first={missing[0]})")

    out_paths = {
        "train": out_dir / "sl_sst-ud-train.conllu",
        "dev": out_dir / "sl_sst-ud-dev.conllu",
        "test": out_dir / "sl_sst-ud-test.conllu",
    }

    for split, sids in split_sid_orders.items():
        write_split(sids, merged_map, out_paths[split])

    print(f"Merged input: {merged_path}")
    for split in ["train", "dev", "test"]:
        print(f"Wrote {split}: {out_paths[split]} ({len(split_sid_orders[split])} sentences)")


if __name__ == "__main__":
    main()
