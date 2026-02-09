# Backchannels Extraction for SST Corpus

This document describes the backchannels extraction pipeline for the Slovenian SST corpus and the apply step used to write final annotations.

## 1. What are Backchannels?

**Backchannels** (Slovenian: *odzivi*, *potrditveni signali*) are short listener reactions that show the listener is paying attention without taking over the speaking turn. The original speaker typically continues after a backchannel.

**Examples:**
- A: "hodiva in potem kar neankrat vidiva ano in petra"
- B: "aha" ← backchannel
- A: "in jima rečeva živjo"

**Key characteristics:**
- Short utterances (typically 1-3 words)
- From a limited lexicon (mhm, ja, aha, ne, etc.)
- Different speaker than previous utterance (A→B, then A continues)
- Not answers to questions
- Allow speaker A to continue

## 2. Annotation Format (Applied in Final Step)

Backchannels are annotated in CoNLL-U MISC column using:

```
Backchannel=<sent_id>::<token_id>
```

Where:
- `<sent_id>` = sentence ID of utterance A (the one being responded to)
- `<token_id>` = token ID of the **root** token in utterance A

**Example:**
```
# sent_id = Gos042.s93
1    mhm    mhm    INTJ    I    _    0    root    _    Backchannel=Gos042.s92::4
```

This means: "mhm" is a backchannel referencing sentence Gos042.s92, token 4 (the root).

## 3. Lexicon-Based Approach

### 3.1 Backchannel Lexicon

File: `lexicon/sl_backchannels.txt`

**Categories:**

1. **CONTINUER**: Nasal sounds made with mouth closed
   - mhm, mh, mhmh, mm, mmm
   - Function: Minimal engagement, "keep talking"

2. **RESPONSIVE**: Acknowledgment, understanding, assessment
   - ja, ok, okej, prav, tako, res, seveda, itak
   - aha, aja, razumem, vem
   - dobro, super, fajn, vredu, redu
   - Function: "I hear you / I understand / That's good"

3. **SURPRISE**: Emotional reactions and exclamations
   - a, aa, aaa, ha, ah, oh, eh
   - oo, ooo, oho, ohoho, ohohoho
   - wow, woow, vau, vaau, vaa, uau
   - ojoj, ojojoj, joj, jojme, ojej, jej, jejhata
   - uf
   - kaj, kako (as exclamations: "what?!", "how?!")
   - Function: Surprise, dismay ("ah!")

4. **MULTIWORD_STARTER**: Function words in multiword backchannels
   - v (for "v redu")

### 3.2 Category Logic

**Why these boundaries?**
- **Continuer vs fillers:** Continuers are functional backchannels (nasal, mouth closed), not hesitation markers
- **a/aa/aaa as surprise:** Works like "ah!" - emotional reaction, not neutral continuer
- **kaj/kako kept:** Work as exclamations ("what?!", "how?!") not questions

**Excluded:**
- Greetings (zdravo, čao)
- Laughter (haha, hehe)
- Fillers (e, eee, eem, hm) - per task requirement

## 4. Extraction Pipeline

### 4.1 Hard Filters (Must Pass All)

1. **Different speakers:** A and B have different speaker IDs
2. **First token in lexicon:** B's first token must be in backchannel lexicon
3. **Dependency relation:** B's first token has `deprel=discourse` OR `deprel=root`
   - **Exception:** multiword_starter (e.g., "v") can have `deprel=case` if second token also in lexicon

### 4.2 Soft Filters (Used for Final Selection)

1. **B_all_in_lexicon:** All tokens in B are in lexicon (value: 0 or 1)
2. **A_continues:** Speaker A continues after B (value: 0 or 1)
3. **A_is_question:** Utterance A is a question (value: 0 or 1)
4. **has_verbal_bc:** B contains verbal forms (razumem, vem, veš, prosim)
5. **not_all_in_lexicon:** Inverse of B_all_in_lexicon (convenience flag)

### 4.3 Final Filter Criteria (for Annotation Input)

**Final backchannels = candidates where:**
```
A_is_question = 0  AND  B_all_in_lexicon = 1
```

This ensures:
- B is not answering a question
- All words in B are from our validated lexicon
- Regardless of whether A continues or not

## 5. Scripts and Workflow

### 5.1 Extract Candidates

**Script:** `scripts/extract_backchannels_new.py`

```bash
python3 scripts/extract_backchannels_new.py
```

**Inputs:**
- `src/sst/sl_sst-ud-merged.conllu` (source corpus)
- `lexicon/sl_backchannels.txt` (backchannel lexicon)

**Output:**
- `output/sst/backchannel_candidates_expanded.csv` (all candidates with soft filters)

**Results:**
- Total candidates: 855
- Further filter (A_is_question=0 & B_all_in_lexicon=1): **386 backchannels**

### 5.2 Apply Annotations

**Script:** `scripts/apply_backchannel_annotations.py`

```bash
python3 scripts/apply_backchannel_annotations.py
```

**Process:**
1. Loads CSV with filtered candidates
2. For each candidate, finds root token in utterance A
3. Adds `Backchannel=A_sent_id::root_token_id` to MISC column of first token in B
4. Creates new CoNLL-U file with annotations

**Output:**
- `output/sst/sl_sst-ud-merged.backchannels.conllu`

**Verification:**
- File is identical to input except for 386 MISC column additions
- All annotations point to root tokens (HEAD=0)

## 6. Statistics
Final filtered results:
```
A_is_question = 0  AND  B_all_in_lexicon = 1
```

**Total: 386 backchannels**

Top words:
1. ja (169) - responsive
2. mhm (85) - continuer
3. aha (41) - responsive
4. aja (27) - responsive
5. mmm (7) - continuer
6. tako (7) - responsive
7. kaj (5) - surprise
8. dobro (5) - responsive
9. super (5) - responsive
10. a (4) - surprise

### 6.3 A_continues Distribution

Of the 386 annotated backchannels:
- 253 (65.5%) have A_continues=1 (speaker continues after backchannel)
- 133 (34.5%) have A_continues=0

This confirms that while A continuing is good evidence, it's not required - the lexicon-based approach captures valid backchannels even when A doesn't continue immediately.

## 7. Quality Assurance

### 7.1 Verification Steps

1. **Lexicon validation:** 51 words with clear functional categories
2. **Extraction accuracy:** All candidates match hard filters
3. **Annotation accuracy:** All 386 annotations point to root tokens
4. **File integrity:** Output file identical to input except MISC column

### 7.2 Diff Check

```bash
diff -u src/sst/sl_sst-ud-merged.conllu \
        output/sst/sl_sst-ud-merged.backchannels.conllu | head -100
```

Confirms only MISC column changed, no other modifications.
