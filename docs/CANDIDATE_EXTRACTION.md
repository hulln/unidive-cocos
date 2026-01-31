# Backchannel Candidate Extraction (SST speaker view)

This document describes how we extract **candidate backchannels** from the Slovenian SST corpus in **speaker-view** format, and how the resulting candidates support manual annotation with:

- `Backchannel=<sent-id>::<token-id>` in the **MISC** column (speaker view),
as proposed in the project guidelines.

Backchannels here are operationalised as **short listener reactions** where the main speaker typically continues (A…B…A), and the B turn is not an expected answer to a question.

---

## 1) Inputs

### 1.1 Corpus
A merged CoNLL-U file (speaker view), where each utterance is a separate tree and includes metadata:

- `# newdoc id = ...`  (conversation/document id)
- `# sent_id = ...`
- `# speaker_id = ...`
- `# text = ...`
- `# sound_url = ...` (optional; defaults to "NA" if missing)

**Important:** the extractor uses only the **linear order** of utterances in the file. It does not use time alignment, so it cannot detect overlap.

### 1.2 Lexicon (required)
A plain-text lexicon of Slovenian backchannel tokens, one per line:

- `word`
- or `word|category` (category is used to compute `backchannel_type`)

Tokens are matched case-insensitively on FORM (lowercased).

### 1.3 Greeting exclusion list (optional but recommended)
A plain-text list of greeting phrases to exclude, one phrase per line.
Matching is case-insensitive; punctuation `. , ! ?` is removed before comparison.

---

## 2) Script and parameters

Script: `scripts/extract_backchannels_high_recall.py`

Key parameters:
- `--min_lex_hits` (default 1): minimum number of lexicon token hits inside B.
- `--window` (default 5): how far ahead to look for A continuing (A…B…A).
- `--end_k` (default 2): mark B as “near end of conversation” if it is among the last k utterances of a doc.
- `--include_no_continuation`: also keep candidates with no continuation evidence.

Outputs:
- main CSV: `output/sst/backchannel_candidates.csv`
- optional: `*.top_short.csv` if `--auto_top_short > 0`

---

## 3) Extraction algorithm (step-by-step)

We iterate through utterances in file order.

### Step A — Pairing (A,B)
For each utterance `B = sents[i]`, we define `A = sents[i-1]` and keep the pair only if:

- same `doc` (same `newdoc id`)
- both have `sent_id` and `speaker_id`
- different speakers (`A.speaker != B.speaker`)

### Step B — Lexicon gating (high recall)
For B:
- remove punctuation tokens
- lowercase token FORMs
- count lexicon hits

Keep B only if `hits >= --min_lex_hits`.

### Step C — Hard exclusions (skip obviously wrong cases)
Exclude B if:
1) Greeting-like (`B.text` matches greeting list, after normalisation)
2) Too long: `B_token_count >= 6`
3) Contains Slovenian question words (kaj/kako/kdo/…),
   except:
   - single-word exclamations like “kaj” / “kako” (including elongated forms)
   - “kako + ADJ/ADV” exclamations (e.g. “kako smešno”)
4) Wrong-direction case:
   if A itself looks like a backchannel (1–3 tokens, all in lexicon)
   and B is long (`B_token_count > 4`), skip (likely A is the backchannel, not B).

### Step D — Continuation evidence (A…B…A)
We add one or more “why_candidate” reasons:

- **Immediate continuation:** if the next utterance `sents[i+1]` is by speaker A
  → reason: “A continues immediately after B” → base confidence HIGH
- **Windowed continuation:** if speaker A appears again within `--window` turns after A
  → reason: “A continues within {window} turns” → base confidence MEDIUM
- **Near end:** if B is among the last `--end_k` utterances of the doc
  → reason: “Near end of conversation” → base confidence stays LOW

If there are no reasons at all:
- drop the candidate unless `--include_no_continuation` is enabled.

We may also add a weak syntactic hint:
- if any token in B has a dependency relation starting with `discourse`,
  add reason: “has discourse relation” (not a filter).

### Step E — Warning flags (for manual review)
We compute warning flags and potentially downgrade the confidence label:

- `B_has_content`: B contains verbs/clause-like structure or is suspiciously long (>3 tokens).
- `B_is_question`: B ends with “?” and has >2 tokens (questions likely require an answer).
  (Single-token “ne?” / “ja?” are treated as allowable.)
- `B_after_question`: A contains “?” anywhere (B may be an answer, not a backchannel).
- `A_looks_like_backchannel`: A itself is short and lexicon-only.

A minor filler warning is also computed (`eee`, `em`, `erm`, `mmm`) and counts as a 0.5 warning for label downgrades.

Downgrade summary:
- if `B_after_question` → force label to LOW
- if `B_is_question` → force label to LOW
- if label is HIGH and `B_token_count > 3` → downgrade to MEDIUM
- if (major warnings + filler penalty) >= 2 → label LOW
- if >= 1 → label at most MEDIUM

### Step F — Numeric confidence score (0–100)
We compute a numeric score for ranking:
- Base: 85 (immediate), 70 (windowed), 35 (otherwise)
- Length adjustment: +10 (1 token), +5 (2), 0 (3), -15 (4), -25 (5), -50 (6+)
- -15 per major warning
- -50 if `B_after_question`
Clamp to [0,100].

### Step G — Attach-point suggestions (for `Backchannel=<sent>::<tok>`)
We output two suggestions for where B could attach into A:
- `proposed_attach_root = A_sent_id::<root_token_id>`
- `proposed_attach_last_content = A_sent_id::<last_content_token_id>`

These are heuristics to speed up manual annotation; the annotator makes the final choice.

### Step H — Backchannel type
We set `backchannel_type` from lexicon categories using priority:
`assessment > laughter > surprise > understanding > agreement > continuer > filler > unspecified`.

---

## 4) Output CSV schema

Each row corresponds to one B utterance (unique by `B_sent_id`).

Columns:
- `doc`
- `confidence` (HIGH/MEDIUM/LOW)
- `confidence_score` (0–100)
- `backchannel_type`
- A fields: `A_sent_id`, `A_speaker`, `A_text`, `A_sound_url`, `A_tokens`, `A_pos_tags`
- B fields: `B_sent_id`, `B_speaker`, `B_text`, `B_sound_url`, `B_tokens`, `B_token_count`
- `why_candidate`
- warning flags: `A_looks_like_backchannel`, `B_has_content`, `B_is_question`, `B_after_question`
- attach suggestions: `proposed_attach_root`, `proposed_attach_last_content`
- `keep?` (manual decision placeholder)

---

## 5) Downstream annotation (speaker view)

For each accepted candidate B, add in the speaker-view CoNLL-U:
- `Backchannel=<A_sent_id>::<token_id>` in MISC (on the B token(s) forming the backchannel),
where `<token_id>` is the chosen governor in A (often the root or last content token).
