# Final SST (Backchannels + Coconstructions)

This package contains final speaker-view CoNLL-U files with both:
- `Backchannel=...`
- `Coconstruct=...`

## Structure
- `conllu/sl_sst-ud-merged.conllu`
- `conllu/sl_sst-ud-train.conllu`
- `conllu/sl_sst-ud-dev.conllu`
- `conllu/sl_sst-ud-test.conllu`
- `annotations/coconstruction_17_final.xlsx`
- `reports/diffcheck_src_vs_final.txt`
- `reports/split_alignment_check.txt`
- `reports/coco_deprel_review.xlsx`

## Process summary (what was done)
1. Merged split corpus (`src/sst/*` -> merged).
2. Extracted backchannel candidates.
3. Filtered backchannels manually/criteria-driven.
4. Applied backchannel annotations to merged CoNLL-U.
5. Extracted coconstruction candidates.
6. Manually annotated coconstruction YES cases (`deprel`, `governor_token_id`).
7. Applied coconstruction annotations to merged CoNLL-U.
8. Split final merged file back to train/dev/test (same sentence membership/order as source splits).
9. Ran strict diff checks against source split files.

## Integrity summary
- Relative to `src/sst`, only token `MISC` differs.
- No changes in token columns `ID..DEPS` and no metadata/comment changes.
