# Coconstructions in SST: Practical Workflow

Short guide for the coconstruction workflow in this repository: extract candidates, annotate manually, apply, and validate.

## 1. Annotation format

Coconstruction is written in token `MISC` as:

```text
Coconstruct=<deprel>::<a_sent_id>::<governor_token_id>
```

Where:
- `<deprel>` = UD relation from B-root to a governor token in A,
- `<a_sent_id>` = sentence ID of A,
- `<governor_token_id>` = token ID in A that governs B-root.

In this pipeline, the feature is written on the **root token of sentence B**.

## 2. Candidate extraction (Step 04)

```bash
python3 scripts/04_extract_coconstruction_candidates.py
```

This runs `scripts/extract_coconstruction_candidates.py`.

Main output:
- `output/sst/coconstruction_candidates.csv`

Hard filters used by the extractor:
1. consecutive A->B pair, different speakers, same document,
2. A does not end with sentence-final punctuation (`. ? ! …`),
3. B is not already annotated as backchannel,
4. B is not filler-only,
5. B does not start with filler content.

## 3. Manual annotation process

Manual annotation is required before applying coconstructions.

Required columns for apply:
- `a_sent_id`, `b_sent_id`, `coconstruct_deprel`, `governor_token_id`
- optional: `is_coconstruction` (YES values: `1`, `yes`, `y`, `true`)

### How to fill rows

1. Review A and B together.
2. Decide if B is a coconstruction of A.
3. If NO: leave relation/governor empty (and set `is_coconstruction=0` if used).
4. If YES: find B root token, choose one governor token in A, set `governor_token_id`, then set `coconstruct_deprel`.
5. Add `notes` if the case is uncertain.

Practical rule:
- imagine A and B merged into one dependency tree,
- then attach B-root to one token in A with the relation that best fits that merged tree.

Final manual file used in this repo:
- `output/sst/final_bc_coco/annotations/coconstruction_17_final.xlsx`

## 4. Apply coconstructions (Step 05)

```bash
python3 scripts/05_apply_coconstruction_annotations.py \
  --annotations output/sst/final_bc_coco/annotations/coconstruction_17_final.xlsx \
  --input output/sst/sl_sst-ud-merged.backchannels.conllu \
  --output output/sst/final_bc_coco/conllu/sl_sst-ud-merged.conllu
```

The script checks that A/B IDs exist, governor token exists in A, and B has one root.

## 5. Split and final checks

```bash
python3 scripts/06_split_final_corpus.py
python3 scripts/07_diffcheck_final_vs_src.py
```

After step 07, sentence IDs/order stay identical to `src/sst`, and only token `MISC` changes are allowed.

## 6. Current run numbers (verified)

- extracted coconstruction candidates: `132`
- YES coconstructions in final manual sheet: `17`
- final merged diff vs source: `403` MISC-only lines (`386` backchannels + `17` coconstructions)
