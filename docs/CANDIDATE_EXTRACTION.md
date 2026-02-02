# Backchannel Candidate Extraction (SST speaker view)

This document explains how backchannel candidates are extracted from the Slovenian SST corpus (speaker view), how they are filtered/scored, and what the output CSV contains. The aim is **high recall** (capture many true backchannels), while keeping the output reviewable for manual verification.

Backchannels are operationalised as **short listener reactions** where the original speaker typically continues (A…B…A), and the B turn is **not** an expected answer (e.g. to a question).


## 1) Inputs

### 1.1 Corpus (CoNLL-U, speaker view)
The extractor expects a merged CoNLL-U file where each utterance is a separate tree and includes (as comment metadata):

- `# newdoc id = ...`  (conversation/document id)
- `# sent_id = ...`
- `# speaker_id = ...`
- `# text = ...`
- `# sound_url = ...` (optional; defaults to `NA` if missing)

**Important:** the extractor uses only the **linear order** of utterances in the file. It does not use time alignment, so it cannot detect overlap or interruption.

### 1.2 Backchannel lexicon (required)
A plain-text file (default `sl_backchannels.txt`), one entry per line:

- `word`
- or `word|category` (category used to compute `backchannel_type`)

Matching is case-insensitive on token **FORM** (lowercased).

### 1.3 Greeting exclusion list (optional but recommended)
A plain-text file (default `sl_greetings_exclude.txt`), one phrase per line.
Matching is case-insensitive; punctuation `. , ! ?` is stripped before comparison.


## 2) Script and key parameters

Script: `extract_backchannels_high_recall.py`

Key parameters:
- `--min_lex_hits` (default `1`): minimum number of lexicon hits in B to consider it.
- `--window` (default `5`): how far ahead to look for A continuing (A…B…A).
- `--end_k` (default `2`): mark B as “near end of conversation” if it is among the last `k` utterances in its doc.
- `--include_no_continuation`: also keep candidates without any continuation/end-of-doc evidence.
- `--max_tokens` (default `10`): maximum length when mining “short utterances” for `--auto_top_short` / `--add_top_short_to_lexicon`.

Outputs:
- main CSV: path given by `--output`
- optional “top short utterances” CSV: `--auto_top_short` (if enabled)


## 3) Extraction algorithm (step-by-step)

The script parses the CoNLL-U file into a list of utterances in file order, then iterates through them to build (A,B) pairs.

### Step A — Parse CoNLL-U into utterances
For each sentence block:
- read metadata (`newdoc id`, `sent_id`, `speaker_id`, `text`, optional `sound_url`)
- collect token rows
- skip multiword tokens (`2-3`) and empty nodes (`3.1`)

### Step B — Pairing (A,B)
For each utterance `B = sents[i]`, set `A = sents[i-1]` and keep the pair only if:
- same `doc` (same `newdoc id`)
- both have `sent_id` and `speaker_id`
- different speakers (`A.speaker != B.speaker`)

This means B is always evaluated as an *immediately following* listener turn.

### Step C — Lexicon gating (high recall)
For B:
- remove punctuation tokens
- lowercase token FORMs
- count how many token FORMs occur in the lexicon

Keep B only if `hits >= --min_lex_hits` (default 1).

### Step D — Hard exclusions (skip obviously wrong cases)
Exclude B if:
1) Greeting-like (`B.text` matches greeting exclusion list after normalisation)
2) Too long: `B_token_count >= 6` (non-punctuation tokens)
3) Contains Slovenian question words (kaj/kako/kdo/…), except:
   - single-word exclamations like “kaj” / “kako” (incl. elongated forms)
   - “kako + ADJ/ADV” exclamations (e.g. “kako smešno”)
4) Wrong-direction case:
   if A itself looks like a backchannel (1–3 tokens, all in lexicon)
   and B is long (`B_token_count > 4`), skip (likely A is the backchannel, not B).

### Step E — Continuation evidence (A…B…A)
The script adds one or more “why_candidate” reasons:

- **Immediate continuation:** if the next utterance `sents[i+1]` is by speaker A  
  → reason: `A continues immediately after B` → base confidence HIGH
- **Windowed continuation:** if speaker A appears again within `--window` turns after A  
  → reason: `A continues within {window} turns` → base confidence MEDIUM
- **Near end:** if B is among the last `--end_k` utterances of the doc  
  → reason: `Near end of conversation` → base confidence stays LOW

If there are **no reasons at all**, the candidate is dropped unless `--include_no_continuation` is enabled.

A weak syntactic hint may also be appended:
- if any token in B has a dependency relation starting with `discourse`,
  add reason: `has discourse relation` (this is **not** a filter).

### Step F — Warning flags (for review and confidence downgrading)
For each candidate B, the script computes warning flags:

- `B_has_content`: B contains verbs/clause-like structure or is suspiciously contentful.
- `B_is_question`: B ends with “?” and has >2 tokens (likely requires an answer).
  (Single-token “ne?”/“ja?” are treated as allowable tag-like responses.)
- `B_after_question`: A contains “?” (B may be an answer rather than a backchannel).
- `A_looks_like_backchannel`: A itself is short and lexicon-only (direction may be wrong).

A minor filler warning is also computed (`eee`, `em`, `erm`, `mmm`) and counts as **0.5** warnings in the label logic.

**Confidence label downgrades:**
- if `B_after_question` → label forced to LOW
- if `B_is_question` → label forced to LOW
- if label is HIGH and `B_token_count > 3` → downgrade to MEDIUM
- if (major warnings + filler penalty) ≥ 2 → label LOW
- if ≥ 1 → label at most MEDIUM

### Step G — Numeric confidence score (0–100)
The script computes a numeric score used for ranking:

- Base: 85 (immediate continuation), 70 (windowed continuation), 35 (otherwise)
- Length adjustment: +10 (1 tok), +5 (2), 0 (3), −15 (4), −25 (5), −50 (6+)
- Warning penalty: −15 per warning; **fractional warnings are allowed** (e.g. 0.5 fillers → −7.5)
- Answer penalty: −50 if `B_after_question`
- Clamp to [0,100] and round to an integer for CSV.

### Step H — Attachment suggestion (root-only)
For downstream manual annotation (e.g. `Backchannel=<sent-id>::<token-id>` in MISC), the extractor provides exactly one heuristic suggestion:

- `proposed_attach_root = <A_sent_id>::<root_token_id>` where `<root_token_id>` is the token in A with `HEAD=0`.

No other attachment suggestions are produced.

### Step I — Backchannel type
`backchannel_type` is derived from lexicon categories with priority:

`assessment > laughter > surprise > understanding > agreement > continuer > filler > unspecified`


## 4) Output CSV schema

Each output row corresponds to one B utterance (unique by `B_sent_id`).

Columns:
- `doc`
- `confidence` (HIGH/MEDIUM/LOW)
- `confidence_score` (0–100)
- `backchannel_type`
- A fields: `A_sent_id`, `A_speaker`, `A_text`, `A_sound_url`, `A_tokens`, `A_pos_tags`
- B fields: `B_sent_id`, `B_speaker`, `B_text`, `B_sound_url`, `B_tokens`, `B_token_count`
- `why_candidate`
- warning flags: `A_looks_like_backchannel`, `B_has_content`, `B_is_question`, `B_after_question`
- `proposed_attach_root`
- `keep?` (manual decision placeholder)


## 5) Downstream workflow (manual review + corpus update)

1) Review the candidate CSV and set `keep?` (e.g. YES/NO) for each row.
2) For kept rows, add `Backchannel=<A_sent_id>::<token_id>` into the CoNLL-U MISC column for the B backchannel token(s),
   where `<token_id>` is typically the root token of A (as suggested by `proposed_attach_root`).
3) Regenerate CSV whenever the corpus, lexicon, or filters change, to keep the pipeline reproducible.
