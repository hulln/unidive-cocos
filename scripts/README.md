# Scripts Workflow

This folder includes both legacy script names and a numbered workflow entrypoint
pattern for reproducible execution.

## Recommended numbered workflow
1. `scripts/01_merge_sst.py`
2. `scripts/02_extract_backchannel_candidates.py`
3. `scripts/03_apply_backchannel_annotations.py`
4. `scripts/04_extract_coconstruction_candidates.py`
5. `scripts/05_apply_coconstruction_annotations.py`
6. `scripts/06_split_final_corpus.py`
7. `scripts/07_diffcheck_final_vs_src.py`

The numbered scripts are the preferred run order.

## What each step does
- `01_merge_sst.py`
  - Delegates to `merge_sst_corpus.py`.
  - Creates merged corpus at `src/sst/sl_sst-ud-merged.conllu`.

- `02_extract_backchannel_candidates.py`
  - Delegates to `extract_backchannels_new.py`.
  - Produces `output/sst/backchannel_candidates_expanded.csv`.

- `03_apply_backchannel_annotations.py`
  - Delegates to `apply_backchannel_annotations.py`.
  - Applies filtered backchannels to merged CoNLL-U.

- `04_extract_coconstruction_candidates.py`
  - Delegates to `extract_coconstruction_candidates.py`.
  - Produces coconstruction candidate table for manual review.

- `05_apply_coconstruction_annotations.py`
  - Applies manually curated coconstruction annotations from xlsx/csv.
  - Writes final merged annotated file (default):
    `output/sst/final_bc_coco/conllu/sl_sst-ud-merged.conllu`.

- `06_split_final_corpus.py`
  - Splits final merged annotated file into train/dev/test,
    preserving source split sentence membership and order.

- `07_diffcheck_final_vs_src.py`
  - Strict src-vs-final diff check.
  - Verifies only MISC annotation additions (Backchannel/Coconstruct).

## Manual decision points in workflow
- Backchannels:
  - Filter from candidates before step 03 (per docs criteria).
- Coconstructions:
  - Manual annotation of YES cases (`deprel`, `governor_token_id`) before step 05.

## Legacy scripts (kept for compatibility)
- `merge_sst_corpus.py`
- `extract_backchannels_new.py`
- `apply_backchannel_annotations.py`
- `extract_coconstruction_candidates.py`
- `extract_backchannels_old_high_recall.py` (reference/legacy)

