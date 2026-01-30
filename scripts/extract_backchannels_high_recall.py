#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

PUNCT_RE = re.compile(r"^\W+$", re.UNICODE)

DEFAULT_SEED_LEXICON = {
    # sound-based backchannels (non-lexical)
    "mhm", "mh", "mhmh", "mm", "mmm", "hmm", "hm",
    
    # agreement and confirmation markers
    "ja", "aha", "aja",
    "ne", "no",
    "ok", "okej",
    "prav", "tako", "res",
    
    # positive assessment markers
    "dobro", "super", "fajn",
    "seveda",
    "vredu", "redu",  # "vredu" = colloquial; "redu" matches "v redu" (2 tokens)
    
    # attention signals and minimal markers
    "a", "aa", "aaa",
    
    # fillers and hesitations
    "eee", "eem", "em",
    
    # reactions and exclamations
    "ha", "ah", "oh", "eh",
    "ojej", "joj",
    
    # polite continuers
    "prosim",
    "razumem",  # "I understand" - used as acknowledgment signal
    
    # reactive questions (may be flagged if used as content questions)
    "kaj", "kako",
}

# Greeting phrases to exclude (lowercase)
GREETING_PHRASES = {
    "dobro jutro", "dober dan", "dober večer", "dobro vecer",
    "lep dan", "lep večer", "lepa noč", "lepo jutro",
    "živjo", "zdravo", "adijo", "nasvidenje", "zbogom",
}

@dataclass
class Token:
    tid: int
    form: str
    lemma: str
    upos: str
    head: Optional[int]
    deprel: str
    misc: str

@dataclass
class Sent:
    doc: str
    sent_id: str
    speaker: str
    text: str
    sound_url: str
    tokens: List[Token]

def parse_conllu(path: Path) -> List[Sent]:
    sents: List[Sent] = []
    meta: Dict[str, str] = {}
    tokens: List[Token] = []
    current_doc: str = ""

    def flush():
        nonlocal meta, tokens, current_doc
        if not meta and not tokens:
            return
        if "newdoc id" in meta:
            current_doc = meta["newdoc id"]
        sent_id = meta.get("sent_id", "")
        speaker = meta.get("speaker_id", "")
        text = meta.get("text", "")
        sound_url = meta.get("sound_url", "NA")
        sents.append(Sent(doc=current_doc, sent_id=sent_id, speaker=speaker, text=text, sound_url=sound_url, tokens=tokens))
        meta = {}
        tokens = []

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line:
                flush()
                continue
            if line.startswith("#"):
                if "=" in line:
                    k, v = line[1:].split("=", 1)
                    meta[k[1:].strip()] = v.strip()
                continue

            cols = line.split("\t")
            if len(cols) < 8:
                continue
            tid = cols[0]
            # skip multiword tokens & empty nodes
            if "-" in tid or "." in tid:
                continue
            try:
                tid_i = int(tid)
            except ValueError:
                continue

            head = None
            if cols[6].isdigit():
                head = int(cols[6])

            misc = cols[9] if len(cols) > 9 else "_"
            tokens.append(Token(
                tid=tid_i,
                form=cols[1],
                lemma=cols[2],
                upos=cols[3],
                head=head,
                deprel=cols[7],
                misc=misc
            ))

    flush()
    return sents

def is_punct(tok: Token) -> bool:
    if tok.upos == "PUNCT":
        return True
    # also treat pure punctuation forms as punct
    return bool(PUNCT_RE.match(tok.form.strip()))

def norm_form(s: str) -> str:
    return s.strip().lower()

def nonpunct_tokens(sent: Sent) -> List[Token]:
    return [t for t in sent.tokens if not is_punct(t)]

def sent_root_id(sent: Sent) -> Optional[int]:
    for t in sent.tokens:
        if t.head == 0:
            return t.tid
    return None

def last_content_id(sent: Sent) -> Optional[int]:
    # heuristic: last token that is not punct and not a pure filler-like thing
    toks = nonpunct_tokens(sent)
    if not toks:
        return None
    # prefer content POS near the end
    content_pos = {"NOUN", "PROPN", "VERB", "ADJ", "ADV", "NUM", "PRON"}
    for t in reversed(toks):
        if t.upos in content_pos and norm_form(t.form) not in {"eee", "em", "erm"}:
            return t.tid
    # fallback: last nonpunct
    return toks[-1].tid

def count_lexicon_hits(sent: Sent, lex: set[str]) -> Tuple[int, int, List[str]]:
    toks = nonpunct_tokens(sent)
    forms = [norm_form(t.form) for t in toks]
    hits = sum(1 for f in forms if f in lex)
    return hits, len(forms), forms

def is_question_like(text: str) -> bool:
    t = (text or "").strip()
    return "?" in t

def has_discourse_like_deprel(sent: Sent) -> bool:
    # used only as a weak positive signal (not a filter)
    for t in sent.tokens:
        if t.deprel.startswith("discourse"):
            return True
    return False

def is_greeting_phrase(text: str) -> bool:
    """Check if text matches common greeting phrases."""
    normalized = norm_form(text)
    # Remove punctuation for comparison
    normalized = normalized.replace(".", "").replace(",", "").replace("!", "").replace("?", "").strip()
    return normalized in GREETING_PHRASES or any(greeting in normalized for greeting in GREETING_PHRASES)

def looks_like_backchannel(sent: Sent, lex: set[str]) -> bool:
    """Check if sentence itself looks like a backchannel (short, lexicon match)."""
    toks = nonpunct_tokens(sent)
    if len(toks) == 0 or len(toks) > 3:  # backchannels are typically 1-3 tokens
        return False
    forms = [norm_form(t.form) for t in toks]
    # All tokens should be in lexicon
    return all(f in lex for f in forms)

def has_content_structure(sent: Sent) -> bool:
    """Check if sentence has content words/structure that makes it NOT a backchannel."""
    toks = nonpunct_tokens(sent)
    
    # Check for explicit content words first
    has_verb = False
    has_pron = False
    for t in toks:
        if t.upos == "VERB":
            has_verb = True
        if t.upos == "PRON":
            has_pron = True
        # Check for nouns (except when they're very short utterances like names)
        if t.upos in {"NOUN", "PROPN"} and len(toks) > 2:
            return True
        # Check for adjectives in longer utterances
        if t.upos == "ADJ" and len(toks) > 2:
            return True
    
    # PRON + VERB combination suggests full clause (e.g., "jaz sem", "ti si")
    if has_pron and has_verb:
        return True
    
    # Single VERB is content
    if has_verb:
        return True
    
    # Fallback: if no content words detected but suspiciously long
    # Backchannels are typically 1-3 tokens per guidelines ("samostojno")
    if len(toks) > 3:
        return True
    
    return False

def is_question_requiring_answer(sent: Sent) -> bool:
    """Check if sentence is a question that requires an answer (not a backchannel)."""
    text = (sent.text or "").strip()
    if not text.endswith("?"):
        return False
    
    # Tag questions with just one token + "ne" are OK backchannels
    toks = nonpunct_tokens(sent)
    if len(toks) <= 2:
        forms = [norm_form(t.form) for t in toks]
        # "ne?" or "ja?" alone are OK
        if forms == ["ne"] or forms == ["ja"]:
            return False
    
    # Questions with more than 2 tokens are NOT backchannels
    if len(toks) > 2:
        return True
    
    return False

def build_top_short_utterances(sents: List[Sent], max_tokens: int) -> Counter[str]:
    c = Counter()
    for s in sents:
        toks = [norm_form(t.form) for t in nonpunct_tokens(s)]
        if 0 < len(toks) <= max_tokens:
            key = " ".join(toks)
            c[key] += 1
    return c

def find_next_same_speaker(sents: List[Sent], i: int, window: int) -> Optional[int]:
    """Find next index j in (i+1..i+window) with same speaker as sents[i], same doc."""
    base = sents[i]
    for j in range(i + 1, min(len(sents), i + window + 1)):
        if sents[j].doc != base.doc:
            break
        if sents[j].speaker == base.speaker:
            return j
    return None

def is_near_end_of_doc(sents: List[Sent], i: int, k_end: int) -> bool:
    """True if i is within last k_end utterances of its doc."""
    doc = sents[i].doc
    # find last index of this doc
    j = i
    last = i
    while j < len(sents) and sents[j].doc == doc:
        last = j
        j += 1
    return (last - i) <= k_end

def compute_numeric_confidence(confidence: str, n_tok: int, warning_count: int, 
                               has_immediate_aba: bool, has_windowed_aba: bool,
                               is_answer_like: bool = False) -> int:
    """Compute numeric confidence score 0-100.
    
    Guidelines: backchannels are typically 1-3 tokens, standalone markers like 'mhm, ja, aha',
    and the original speaker continues normally.
    
    Scoring:
    - Base score from continuation pattern
    - Penalties for warnings and length
    - Special penalty for answer-like cases (B after question + has content)
    """
    # Start with base score from continuation evidence
    # Guidelines require: "prvotni govorec normalno nadaljuje"
    if has_immediate_aba:
        base_score = 85  # Strong evidence: A continues immediately
    elif has_windowed_aba:
        base_score = 70  # Good evidence: A continues within window
    else:
        base_score = 35  # Very weak: no continuation proof, just short + lexicon match
    
    # Length penalty: backchannels typically 1-3 tokens (guidelines: "samostojno")
    if n_tok == 1:
        length_bonus = 10
    elif n_tok == 2:
        length_bonus = 5
    elif n_tok == 3:
        length_bonus = 0
    elif n_tok == 4:
        length_bonus = -15  # stricter penalty
    elif n_tok == 5:
        length_bonus = -25  # much stricter
    else:  # 6+ tokens
        length_bonus = -50  # very aggressive penalty - clearly violates "samostojno"
    
    # Warning penalties
    warning_penalty = warning_count * 15
    
    # Special penalty: B after question WITH content = likely answer, not backchannel
    answer_penalty = 40 if is_answer_like else 0
    
    # Compute final score
    score = base_score + length_bonus - warning_penalty - answer_penalty
    
    # Clamp to 0-100
    return max(0, min(100, score))

def main():
    ap = argparse.ArgumentParser(description="Extract backchannel candidates from SST corpus")
    ap.add_argument("--input", default=None, help="Path to SST .conllu (default: src/sst/sl_sst-ud-merged.conllu)")
    ap.add_argument("--output", default=None, help="Output CSV path (default: output/sst/backchannel_candidates.csv)")
    ap.add_argument("--min_lex_hits", type=int, default=1, help="Minimum lexicon hits in B")
    ap.add_argument("--window", type=int, default=5, help="Lookahead window for A…B…A continuation")
    ap.add_argument("--end_k", type=int, default=2, help="Consider A-B near end of doc within this many turns")
    ap.add_argument("--include_no_continuation", action="store_true",
                    help="Also include short B even if we can't prove A continues")
    ap.add_argument("--lexicon_file", default=None, help="Optional extra lexicon file (one token per line)")
    ap.add_argument("--auto_top_short", type=int, default=0,
                    help="If >0, write top short utterances list to <output>.top_short.csv")
    ap.add_argument("--add_top_short_to_lexicon", type=int, default=0,
                    help="If >0, add the top N short-utterance tokens (single-token only) to lexicon to increase recall")
    args = ap.parse_args()

    # Set defaults relative to script location
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    if args.input is None:
        args.input = str(project_root / "src" / "sst" / "sl_sst-ud-merged.conllu")
    if args.output is None:
        output_dir = project_root / "output" / "sst"
        output_dir.mkdir(parents=True, exist_ok=True)
        args.output = str(output_dir / "backchannel_candidates.csv")

    path = Path(args.input)
    sents = parse_conllu(path)

    # lexicon
    lex = set(DEFAULT_SEED_LEXICON)
    if args.lexicon_file:
        extra = Path(args.lexicon_file)
        for line in extra.read_text(encoding="utf-8").splitlines():
            line = norm_form(line)
            if line and not line.startswith("#"):
                lex.add(line)

    # optional: build top short utterances
    if args.auto_top_short > 0:
        top = build_top_short_utterances(sents, max_tokens=10)
        out_top = Path(args.output).with_suffix("")  # strip .csv if present
        out_top = Path(str(out_top) + ".top_short.csv")
        with out_top.open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["utterance_tokens", "count"])
            for utt, cnt in top.most_common(args.auto_top_short):
                w.writerow([utt, cnt])

    if args.add_top_short_to_lexicon > 0:
        top = build_top_short_utterances(sents, max_tokens=args.max_tokens)
        added = 0
        for utt, _ in top.most_common():
            toks = utt.split()
            if len(toks) == 1 and toks[0] not in lex:
                lex.add(toks[0])
                added += 1
                if added >= args.add_top_short_to_lexicon:
                    break

    # aggregate results per B_sent_id (so one row per B even if multiple reasons)
    rows_by_b: Dict[str, dict] = {}
    reasons_by_b: Dict[str, set] = defaultdict(set)

    for i in range(len(sents)):
        if i == 0:
            continue

        A = sents[i - 1]
        B = sents[i]
        if A.doc != B.doc:
            continue
        if not A.sent_id or not B.sent_id:
            continue
        if not A.speaker or not B.speaker:
            continue
        if A.speaker == B.speaker:
            continue  # backchannels are typically other-speaker

        hits, n_tok, forms = count_lexicon_hits(B, lex)
        if n_tok == 0:
            continue
        if hits < args.min_lex_hits:
            continue
        
        # Skip if B is a greeting phrase (only hard filter)
        if is_greeting_phrase(B.text):
            continue
        
        # Compute flags (soft filters for manual review)
        A_is_backchannel_like = looks_like_backchannel(A, lex)
        A_is_q = is_question_like(A.text)
        B_has_content = has_content_structure(B)
        B_is_multi_token_q = is_question_requiring_answer(B)
        B_after_question = A_is_q
        
        # FILTER: Skip WRONG_DIR cases where A looks like backchannel and B is long
        # This means we're likely capturing the wrong direction (A is backchannel, not B)
        if A_is_backchannel_like and n_tok > 4:
            continue

        # Compute continuation evidence and base confidence
        why_parts = []
        base_confidence = "LOW"

        # immediate ABA - strongest evidence
        has_immediate_aba = False
        if i + 1 < len(sents):
            C = sents[i + 1]
            if C.doc == B.doc and C.speaker == A.speaker:
                why_parts.append("A continues immediately after B")
                has_immediate_aba = True
                base_confidence = "HIGH"

        # windowed A…B…A
        has_windowed_aba = False
        j = find_next_same_speaker(sents, i - 1, window=args.window)
        if j is not None and j > i:
            if not has_immediate_aba:
                why_parts.append(f"A continues within {args.window} turns")
                has_windowed_aba = True
                if base_confidence != "HIGH":
                    base_confidence = "MEDIUM"

        # near end of doc A-B (note but don't auto-upgrade)
        at_end = is_near_end_of_doc(sents, i, k_end=args.end_k)
        if at_end:
            why_parts.append("Near end of conversation")
            # Don't auto-upgrade - near end doesn't prove backchannel status

        # No continuation evidence
        if not why_parts:
            if not args.include_no_continuation:
                continue
            why_parts.append("Short B with lexicon match, no continuation proof")
            base_confidence = "LOW"

        # weak syntactic clue
        if has_discourse_like_deprel(B):
            why_parts.append("has discourse relation")
        
        # DOWN-GRADE confidence based on warning flags
        # Count warning flags
        warning_count = sum([B_has_content, B_is_multi_token_q, B_after_question, A_is_backchannel_like])
        
        confidence = base_confidence
        
        # Special handling: B after question is very suspicious (likely answer, not backchannel)
        if B_after_question:
            if confidence == "HIGH":
                confidence = "MEDIUM"  # downgrade HIGH to MEDIUM
        
        # Length check: backchannels typically 1-3 tokens per guidelines  
        # "samostojno" guideline - long utterances violate this strongly
        if n_tok >= 6:
            # 6+ tokens clearly violates "samostojno" - downgrade to LOW
            confidence = "LOW"
        elif n_tok > 3 and confidence == "HIGH":
            confidence = "MEDIUM"  # 4-5 tokens shouldn't be HIGH
        
        # General warning-based downgrade
        if warning_count >= 2:
            # Multiple warnings -> always LOW (probably not a backchannel)
            confidence = "LOW"
        elif warning_count == 1:
            # One warning -> cap at MEDIUM
            if confidence == "HIGH":
                confidence = "MEDIUM"
        
        # Compute numeric confidence score (0-100)
        # Special case: B after question + has content = likely answer, not backchannel
        is_answer_like = B_after_question and B_has_content
        numeric_confidence = compute_numeric_confidence(
            confidence, n_tok, warning_count, has_immediate_aba, 
            has_windowed_aba if 'has_windowed_aba' in locals() else False,
            is_answer_like=is_answer_like
        )

        # flags
        A_root = sent_root_id(A)
        A_last = last_content_id(A)

        B_is_q = is_question_like(B.text)

        proposed_root = f"{A.sent_id}::{A_root}" if A_root is not None else ""
        proposed_last = f"{A.sent_id}::{A_last}" if A_last is not None else ""

        why_candidate = "; ".join(why_parts)
        
        row = rows_by_b.get(B.sent_id)
        if row is None:
            rows_by_b[B.sent_id] = {
                "doc": B.doc,
                "confidence": confidence,
                "confidence_score": numeric_confidence,
                "A_sent_id": A.sent_id,
                "A_speaker": A.speaker,
                "A_text": A.text,
                "A_sound_url": A.sound_url,
                "B_sent_id": B.sent_id,
                "B_speaker": B.speaker,
                "B_text": B.text,
                "B_sound_url": B.sound_url,
                "B_tokens": " ".join(forms),
                "B_token_count": n_tok,
                "why_candidate": why_candidate,
                "A_looks_like_backchannel": int(A_is_backchannel_like),
                "B_has_content": int(B_has_content),
                "B_is_question": int(B_is_multi_token_q),
                "B_after_question": int(B_after_question),
                "proposed_attach_root": proposed_root,
                "proposed_attach_last_content": proposed_last,
                "keep?": "",
            }
        else:
            # merge if we hit same B again (should be rare), keep best confidence
            if confidence == "HIGH":
                rows_by_b[B.sent_id]["confidence"] = "HIGH"
            elif confidence == "MEDIUM" and rows_by_b[B.sent_id]["confidence"] == "LOW":
                rows_by_b[B.sent_id]["confidence"] = "MEDIUM"
            # append why_candidate
            if why_candidate not in rows_by_b[B.sent_id]["why_candidate"]:
                rows_by_b[B.sent_id]["why_candidate"] += " | " + why_candidate

    # write CSV
    out = Path(args.output)
    fieldnames = [
        "doc", "confidence", "confidence_score",
        "A_sent_id", "A_speaker", "A_text", "A_sound_url",
        "B_sent_id", "B_speaker", "B_text", "B_sound_url",
        "B_tokens", "B_token_count", "why_candidate",
        "A_looks_like_backchannel", "B_has_content", "B_is_question", "B_after_question",
        "proposed_attach_root", "proposed_attach_last_content",
        "keep?"
    ]
    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for b_sent_id, row in rows_by_b.items():
            w.writerow(row)

    print(f"Wrote {len(rows_by_b)} candidates to {out}")

if __name__ == "__main__":
    main()
