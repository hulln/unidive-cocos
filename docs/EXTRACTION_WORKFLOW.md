# Backchannels and Coconstructions in UD_Slovenian-SST

This note explains how backchannels and coconstructions were identified and
annotated in the Slovenian SST corpus.

Source: https://github.com/UniversalDependencies/UD_Slovenian-SST

## 1. Scope and data structure

- The corpus is used in speaker view (each utterance is a separate sentence).
- The workflow focuses on adjacent A->B turns (speaker change).
- Two labels were added in `MISC`:
  - `Backchannel=...`
  - `Coconstruct=...`

## 2. Backchannels: extraction and annotation

Backchannels were treated as short listener responses that do not take over
the speaking turn.

Candidate selection:
- A and B are consecutive turns in the same document.
- Speakers are different.
- The first token in B matches a backchannel lexicon item.
- B starts with compatible syntax (typically `discourse` or `root`).

Special case:
- Multiword starters (for example `v`) were accepted only when the next token
  was also in the backchannel lexicon.

Final selection filters:
- `A_is_question = 0`
- `B_all_in_lexicon = 1`

Soft cue (kept as metadata, not final filter):
- `A_continues` (whether speaker A continues after B).

Annotation format:
- `Backchannel=<a_sent_id>::<a_root_token_id>`
- Written on the first token of B.

## 3. Coconstructions: extraction and annotation

Coconstruction candidates were extracted from A->B transitions where A had no
sentence-ending punctuation (`. ? ! …`).

Base pair condition:
- A and B are consecutive turns in the same document with speaker change.

Exclusions:
- B was already annotated as a backchannel.
- B was filler-only.
- B started with filler content.

Soft cues used during manual prioritization:
- Short length of B.
- `orphan` near the end of A.
- Whether A continues after B.

## 4. Manual coconstruction decisions

Each candidate was reviewed manually.

For YES cases, three fields were required:
- `coconstruct_deprel`
- `governor_token_id` (token in A)
- `is_coconstruction=1`

If a case was unclear, it was left as non-YES and noted in comments.

Linking rule used during annotation:
- Treat A and B as one dependency tree.
- Attach B root to one token in A.
- Assign the relation that best matches that attachment.

Annotation format:
- `Coconstruct=<deprel>::<a_sent_id>::<governor_token_id>`
- Written on the root token of B.

## 5. Final outputs

- One final merged annotated file with both annotation types.
- Split files (train/dev/test) preserving original sentence membership and
  order.

## 6. Current run summary

- Backchannel candidates: `855`
- Backchannels applied: `386`
- Coconstruction candidates: `132`
- Coconstructions applied (YES): `17`
