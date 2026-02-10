# unidive-cocos

Pipeline for adding `Backchannel=` and `Coconstruct=` annotations to SST speaker-view CoNLL-U files.

## Repository structure

- `src/sst/`
  - source SST CoNLL-U files (`train`, `dev`, `test`, `merged`)
- `lexicon/`
  - lexical resources (e.g., `lexicon/sl_backchannels.txt`)
- `scripts/`
  - numbered workflow scripts (`01` to `07`)
  - see `scripts/README.md` for script-level details
- `docs/`
  - process documentation
  - `docs/BACKCHANNELS_EXTRACTION.md`
  - `docs/COCONSTRUCTIONS_EXTRACTION.md`
- `output/sst/`
  - extracted candidates and generated annotated corpora
  - final package: `output/sst/final_bc_coco/`

## End-to-end workflow

1. Merge corpus
```bash
python3 scripts/01_merge_sst.py
```

2. Extract backchannel candidates
```bash
python3 scripts/02_extract_backchannel_candidates.py
```

3. Apply backchannels (uses filtered rows from the candidate table)
```bash
python3 scripts/03_apply_backchannel_annotations.py
```

4. Extract coconstruction candidates
```bash
python3 scripts/04_extract_coconstruction_candidates.py
```

5. Manual coconstruction annotation (outside script)
- fill `is_coconstruction`, `coconstruct_deprel`, `governor_token_id` for YES cases

6. Apply coconstructions
```bash
python3 scripts/05_apply_coconstruction_annotations.py
```

7. Split final merged file back to train/dev/test
```bash
python3 scripts/06_split_final_corpus.py
```

8. Run strict diff checks
```bash
python3 scripts/07_diffcheck_final_vs_src.py
```

## Main docs

- Backchannels workflow: `docs/BACKCHANNELS_EXTRACTION.md`
- Coconstructions workflow + manual annotation: `docs/COCONSTRUCTIONS_EXTRACTION.md`
- Docs index: `docs/README.md`

## Current final output location

- `output/sst/final_bc_coco/conllu/sl_sst-ud-merged.conllu`
- `output/sst/final_bc_coco/conllu/sl_sst-ud-train.conllu`
- `output/sst/final_bc_coco/conllu/sl_sst-ud-dev.conllu`
- `output/sst/final_bc_coco/conllu/sl_sst-ud-test.conllu`
