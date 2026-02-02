# Backchannel Extraction and Filtering Guide

## Script Pipeline (Step by Step)

1. Load lexicon (single words + multiword phrases) and categories.
2. Parse CoNLL-U into ordered utterances with speaker metadata.
3. Build adjacent pairs `(A,B)` and keep only cross-speaker pairs in same doc.
4. Take first non-punctuation token of `B`; require it to be lexicon-compatible and `deprel = root` or `discourse*`.
5. Hard keep rule: `B` passes if all tokens are in single-word lexicon OR full `B` exactly matches a multiword lexicon phrase.
6. Add soft warnings (`A_IS_QUESTION`, `HAS_VERBAL_BC`), assign `backchannel_type`, set `lexicon_match_type` (`single`/`phrase`).
7. Write CSV for manual review (`keep?` column).

## Mentor Minimum Filter in Excel

- `A_speaker != B_speaker` (already guaranteed by script)
- `first_token_deprel` is `root` or `discourse*` (already guaranteed by script)
- "all B tokens in lexicon" is hard in code for `single`; `phrase` rows are exact lexicon phrase matches
- For mentor-style strict POS: filter `first_token_upos` to `INTJ` + `PART`

## Other Useful Filters

- Start clean: `warnings = OK`
- Conservative length: `B_token_count <= 3`
- Review phrases separately: `lexicon_match_type = phrase`
- Then relax stepwise: include `A_IS_QUESTION`, then longer `B_token_count`
