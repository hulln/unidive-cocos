# Coconstructions Extraction for SST Corpus

This document describes exactly what the current AB extraction script does and what output it produces.

## 1. What are Co-constructions?

**Co-constructions** are syntactic relations that hold across utterances when:
- speaker B continues/completes what speaker A started, or
- the same speaker continues after interruption (not included in this current AB-only run).

For the current extraction, we focus only on **AB pairs**:
- consecutive A->B speaker change,
- same document,
- no subtype split (A.1/A.2/A.3/B not separated at extraction time).

## 2. Extraction Pipeline (AB)

### 2.1 Hard Filters (Must Pass All)

1. **Speaker change pair:** consecutive A->B pair with different speakers, same document  
2. **A unfinished by punctuation:** A does not end with `. ? ! …`  
3. **B not pre-annotated backchannel:** B has no existing `Backchannel=` annotation  
4. **B not filler-only:** B is not composed entirely of filler tokens  
5. **B not filler-start:** first content token of B is not filler

Filler detection uses:
- `deprel=discourse:filler`, and
- fallback forms: `e, ee, eee, eem, em, emm, hm, hmm, uh, uhh`

### 2.2 Soft Signals (Exported, Not Hard Filters)

- `len`: number of non-punctuation tokens in B
- `orphan_tail`: A has `orphan` in its last 3 content tokens
- `a_continues`: speaker A continues immediately after B
- `a_is_question`
- `b_first_token`
- `b_starts_backchannel_like`
- `b_has_question_mark`
- `b_root_is_intj_part`

These are prioritization hints for manual review only.

## 3. Script and Output

**Script:** `scripts/extract_coconstruction_candidates.py`

```bash
python3 scripts/extract_coconstruction_candidates.py \
  --output output/sst/coconstruction_candidates.csv
```

**Inputs:**
- `src/sst/sl_sst-ud-merged.conllu`
- `output/sst/sl_sst-ud-merged.backchannels.conllu`
- `lexicon/sl_backchannels.txt`

**Output:**
- `output/sst/coconstruction_candidates.csv`

Auto-review split files that were generated:
- `output/sst/coconstruction_candidates_auto_balanced.csv`
- `output/sst/coconstruction_candidates_auto_balanced_clean.csv`
- `output/sst/coconstruction_candidates_auto_strict.csv`
- `output/sst/coconstruction_candidates_review_later.csv`

These are convenience subsets; the base extraction list is `coconstruction_candidates.csv`.

Manual annotation fields included in CSV:
- `is_coconstruction`
- `coconstruct_deprel`
- `governor_token_id`
- `notes`

## 4. Current Statistics

Hard-filter counts:

1. AB speaker-change pairs: **2690**
2. A unfinished (no final punct): **159**
3. Remove pre-annotated backchannels: **-19** (remaining 140)
4. Remove filler-start / filler-only B: **-8**

Final extracted candidates: **132**

Distribution in final 132:
- `len <= 3`: 43
- `len 4-7`: 39
- `len 8-10`: 16
- `len >= 11`: 34
- `orphan_tail=1`: 25
- `a_continues=1`: 70
- `b_starts_backchannel_like=1`: 38
- `b_has_question_mark=1`: 14

## 5. Quality Assurance

Verification checks performed:
- Script compiles cleanly (`python3 -m py_compile`)
- Output row count is reproducible (132 with current corpus/backchannel file)
- Hard-filter invariants verified on extracted rows:
  - no row where A has final sentence punctuation
  - no row where B is pre-annotated backchannel
  - no row with filler-start/filler-only B
- No duplicate `b_sent_id` in extracted CSV

## 6. Practical Annotation Guidance

Recommended first-pass order:
1. Sort by `len` ascending
2. Prioritize `a_continues=1`
3. Use `orphan_tail=1` as secondary cue
4. Fill `is_coconstruction`, then `coconstruct_deprel` and `governor_token_id` for YES cases
