# Backchannels in SST: Practical Workflow

This document is a short, practical guide for the current backchannel pipeline in this repository.

## 1. Annotation format

Backchannels are written in token `MISC` as:

```text
Backchannel=<a_sent_id>::<a_root_token_id>
```

Where:
- `<a_sent_id>` is the sentence ID of utterance A (the sentence being responded to),
- `<a_root_token_id>` is the root token ID in A.

In this pipeline, the feature is written on the **first token of utterance B**.

## 2. Files used

- Source merged corpus: `src/sst/sl_sst-ud-merged.conllu`
- Backchannel lexicon: `lexicon/sl_backchannels.txt`
- Extracted candidates: `output/sst/backchannel_candidates_expanded.csv`
- Backchannel-annotated merged file: `output/sst/sl_sst-ud-merged.backchannels.conllu`

## 3. Workflow (current repo)

### Step 02: extract candidates

```bash
python3 scripts/02_extract_backchannel_candidates.py
```

This runs `scripts/extract_backchannels_new.py` and writes:
- `output/sst/backchannel_candidates_expanded.csv`

### Manual filtering

From `output/sst/backchannel_candidates_expanded.csv`, keep rows where:
- `A_is_question = 0`
- `B_all_in_lexicon = 1`

### Step 03: apply annotations

```bash
python3 scripts/03_apply_backchannel_annotations.py
```

This runs `scripts/apply_backchannel_annotations.py` and writes:
- `output/sst/sl_sst-ud-merged.backchannels.conllu`

Default behavior in step 03:
- input: `src/sst/sl_sst-ud-merged.conllu`
- candidate CSV: `output/sst/backchannel_candidates_expanded.csv`
- it applies exactly the same filter above (`A_is_question=0` and `B_all_in_lexicon=1`) while loading rows.

## 4. Current run numbers (verified)

- Candidate rows in CSV: `855`
- Rows passing filter (`A_is_question=0` and `B_all_in_lexicon=1`): `386`
- Applied backchannel annotations: `386`

## 5. Quick sanity check

Backchannel-only diff:

```bash
diff -u src/sst/sl_sst-ud-merged.conllu output/sst/sl_sst-ud-merged.backchannels.conllu | head -100
```

Final full diff check (after coconstructions and split):

```bash
python3 scripts/07_diffcheck_final_vs_src.py
```
