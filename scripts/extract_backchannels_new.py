#!/usr/bin/env python3
"""
Extract backchannel candidates using focused syntactic criteria.

Extraction criteria (HARD FILTERS):
1. Lexicon-based: first token of utterance B must be in backchannel lexicon
2. Position: first token must appear in first position of B
3. Syntactic: first token has deprel = 'discourse' OR 'root' (or discourse subtypes)
4. All tokens in B must be in lexicon

Warning flags (SOFT FILTERS):
- A_IS_QUESTION: Previous utterance is a question
- HAS_VERBAL_BC: Contains verbal backchannel (vem, veš, razumem, prosim)
- REPAIR_INITIATOR: Borderline case (e.g., "kaj?", "kako?" - repair initiators)
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

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

def load_lexicon_from_file(path: Path) -> Tuple[set[str], Dict[str, str]]:
    """Load lexicon from file with categories.
    
    Returns:
        - Set of lexicon words (for quick lookup)
        - Dict mapping word to category type
    """
    lexicon = set()
    categories = {}
    if not path.exists():
        print(f"Warning: Lexicon file not found at {path}")
        return lexicon, categories
    
    with path.open('r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            # Skip comments and empty lines
            if line and not line.startswith('#'):
                # Parse format: word|category or just word
                if '|' in line:
                    word, category = line.split('|', 1)
                    word = word.strip().lower()
                    category = category.strip().lower()
                    lexicon.add(word)
                    categories[word] = category
                else:
                    # Old format without category
                    word = line.lower()
                    lexicon.add(word)
                    categories[word] = 'unspecified'
    return lexicon, categories

def parse_conllu(path: Path) -> List[Sent]:
    """Parse CoNLL-U file and return list of sentences."""
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
        sents.append(Sent(doc=current_doc, sent_id=sent_id, speaker=speaker, 
                         text=text, sound_url=sound_url, tokens=tokens))
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
    """Check if token is punctuation."""
    return tok.upos == "PUNCT"

def norm_form(s: str) -> str:
    """Normalize form to lowercase."""
    return s.strip().lower()

def get_first_nonpunct_token(sent: Sent) -> Optional[Token]:
    """Get first non-punctuation token from sentence."""
    for tok in sent.tokens:
        if not is_punct(tok):
            return tok
    return None

def is_question_like(text: str) -> bool:
    """Check if text ends with question mark."""
    t = (text or "").strip()
    return "?" in t

def all_tokens_in_lexicon(sent: Sent, lex: set[str]) -> bool:
    """Check if all non-punctuation tokens are in lexicon."""
    toks = [t for t in sent.tokens if not is_punct(t)]
    if not toks:
        return False
    forms = [norm_form(t.form) for t in toks]
    return all(f in lex for f in forms)

def has_verbal_backchannel(sent: Sent, lex: set[str]) -> bool:
    """Check if sentence contains a verbal backchannel at any position.
    
    Returns True if found, False otherwise.
    """
    for tok in sent.tokens:
        if is_punct(tok):
            continue
        form_lower = norm_form(tok.form)
        if tok.upos == 'VERB' and form_lower in lex:
            return True
    return False

def matches_criteria(first_tok: Token, lex: set[str]) -> Tuple[bool, str]:
    """Check if first token matches all extraction criteria.
    
    Returns:
        (matches, reason) tuple
    """
    form_lower = norm_form(first_tok.form)
    
    # Criterion 1: Must be in lexicon
    if form_lower not in lex:
        return False, "first token not in lexicon"
    
    # Criterion 2: Syntactic - deprel must be 'discourse' or 'root'
    # Includes discourse:filler and other discourse subtypes
    if not (first_tok.deprel == 'root' or first_tok.deprel.startswith('discourse')):
        return False, f"deprel={first_tok.deprel} (not discourse/root)"
    
    # No UPOS filter - keep it simple!
    return True, "matches all criteria"

def main():
    ap = argparse.ArgumentParser(
        description="Extract backchannel candidates using focused syntactic/morphological criteria"
    )
    ap.add_argument("--input", default=None, 
                   help="Path to SST .conllu (default: src/sst/sl_sst-ud-merged.conllu)")
    ap.add_argument("--output", default=None, 
                   help="Output CSV path (default: output/sst/backchannel_candidates_expanded.csv)")
    ap.add_argument("--lexicon_file", default=None, 
                   help="Path to lexicon file (default: lexicon/sl_backchannels_expanded.txt)")
    args = ap.parse_args()

    # Set defaults relative to script location
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    if args.input is None:
        args.input = str(project_root / "src" / "sst" / "sl_sst-ud-merged.conllu")
    if args.output is None:
        output_dir = project_root / "output" / "sst"
        output_dir.mkdir(parents=True, exist_ok=True)
        args.output = str(output_dir / "backchannel_candidates_expanded.csv")
    
    # Load lexicon
    lexicon_path = (Path(args.lexicon_file) if args.lexicon_file 
                   else project_root / "lexicon" / "sl_backchannels_expanded.txt")
    lex, categories = load_lexicon_from_file(lexicon_path)
    
    if not lex:
        print(f"Error: No lexicon loaded from {lexicon_path}")
        return
    
    print(f"Loaded {len(lex)} lexicon words from {lexicon_path}")
    
    # Parse CoNLL-U
    path = Path(args.input)
    sents = parse_conllu(path)
    print(f"Parsed {len(sents)} sentences from {path}")
    
    # Extract candidates
    candidates = []
    
    for i in range(1, len(sents)):
        A = sents[i - 1]
        B = sents[i]
        
        # Basic checks
        if A.doc != B.doc:
            continue
        if not A.sent_id or not B.sent_id:
            continue
        if not A.speaker or not B.speaker:
            continue
        if A.speaker == B.speaker:
            continue  # backchannels are other-speaker
        
        # Get first non-punctuation token from B
        first_tok = get_first_nonpunct_token(B)
        if first_tok is None:
            continue
        
        # Check if it matches all criteria
        matches, reason = matches_criteria(first_tok, lex)
        
        if matches:
            # HARD FILTER: All tokens in B must be in lexicon
            B_all_in_lex = all_tokens_in_lexicon(B, lex)
            if not B_all_in_lex:
                continue  # Skip if not all tokens are in lexicon
            
            # Get category from lexicon
            form_lower = norm_form(first_tok.form)
            bc_type = categories.get(form_lower, 'unspecified')
            
            # Get all token forms and POS tags from B
            B_forms = []
            B_pos = []
            for tok in B.tokens:
                if not is_punct(tok):
                    B_forms.append(tok.form)
                    B_pos.append(tok.upos)
            
            # Get A tokens for context
            A_forms = []
            A_pos = []
            for tok in A.tokens:
                if not is_punct(tok):
                    A_forms.append(tok.form)
                    A_pos.append(tok.upos)
            
            # Check warning flags
            A_is_question = is_question_like(A.text)
            B_has_verbal_bc = has_verbal_backchannel(B, lex)
            B_is_repair = first_tok.upos == 'PRON'  # Repair initiators (kaj?, kako?)
            
            # Build warnings list
            warnings = []
            if A_is_question:
                warnings.append("A_IS_QUESTION")
            # Positive indicator: has verbal backchannel (e.g., "ja razumem", "ne vem")
            if B_has_verbal_bc:
                warnings.append("HAS_VERBAL_BC")
            # Borderline case: repair initiator (e.g., "kaj?", "kako?")
            if B_is_repair:
                warnings.append("REPAIR_INITIATOR")
            
            warnings_str = "; ".join(warnings) if warnings else "OK"
            
            candidates.append({
                "doc": B.doc,
                "A_sent_id": A.sent_id,
                "A_speaker": A.speaker,
                "A_text": A.text,
                "A_sound_url": A.sound_url,
                "A_tokens": " ".join(A_forms),
                "A_pos_tags": " ".join(A_pos),
                "B_sent_id": B.sent_id,
                "B_speaker": B.speaker,
                "B_text": B.text,
                "B_sound_url": B.sound_url,
                "B_tokens": " ".join(B_forms),
                "B_pos_tags": " ".join(B_pos),
                "first_token_form": first_tok.form,
                "first_token_lemma": first_tok.lemma,
                "first_token_upos": first_tok.upos,
                "first_token_deprel": first_tok.deprel,
                "backchannel_type": bc_type,
                "B_token_count": len(B_forms),
                "B_all_in_lexicon": int(B_all_in_lex),
                "B_has_verbal_bc": int(B_has_verbal_bc),
                "B_is_repair": int(B_is_repair),
                "A_is_question": int(A_is_question),
                "warnings": warnings_str,
                "keep?": "",
            })
    
    # Write CSV
    out = Path(args.output)
    fieldnames = [
        "doc", "A_sent_id", "A_speaker", "A_text", "A_sound_url", 
        "A_tokens", "A_pos_tags",
        "B_sent_id", "B_speaker", "B_text", "B_sound_url", 
        "B_tokens", "B_pos_tags", "B_token_count", "B_all_in_lexicon",
        "B_has_verbal_bc", "B_is_repair",
        "first_token_form", "first_token_lemma", "first_token_upos", "first_token_deprel",
        "backchannel_type",
        "A_is_question", "warnings",
        "keep?"
    ]
    
    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for row in candidates:
            w.writerow(row)
    
    print(f"Extracted {len(candidates)} candidates matching all criteria")
    print(f"Wrote results to {out}")

if __name__ == "__main__":
    main()
