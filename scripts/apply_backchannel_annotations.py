#!/usr/bin/env python3
"""
Apply backchannel annotations to CoNLL-U file.

Takes CSV with backchannel candidates (filtered to A_is_question=0 & B_all_in_lexicon=1)
and adds Backchannel=sent_id::token_id annotations to MISC column.

Format: Backchannel=A_sent_id::root_token_id
- A_sent_id: sentence ID of utterance A (the one being responded to)
- root_token_id: token ID of the root token in utterance A
"""

import argparse
import csv
from pathlib import Path
from typing import Dict, List, Tuple, Set


def parse_conllu_line(line: str) -> Tuple[str, List[str]]:
    """Parse a CoNLL-U line and return (token_id, fields).
    
    Returns:
        - token_id as string (e.g., '1', '2-3', '1.1')
        - list of 10 fields
    """
    if not line.strip() or line.startswith('#'):
        return None, None
    
    fields = line.split('\t')
    if len(fields) != 10:
        return None, None
    
    return fields[0], fields


def read_conllu(filepath: Path) -> List[str]:
    """Read CoNLL-U file and return list of lines (preserving exact format)."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.readlines()


def find_root_token_id(lines: List[str], sent_id: str) -> str:
    """Find the token ID of the root token in a sentence.
    
    Args:
        lines: All lines from CoNLL-U file
        sent_id: Sentence ID to search for (e.g., 'Gos073.s374')
    
    Returns:
        Token ID of root token (e.g., '11')
    """
    in_target_sentence = False
    
    for line in lines:
        if line.startswith('# sent_id = '):
            current_sent_id = line.strip().split('= ')[1]
            in_target_sentence = (current_sent_id == sent_id)
            continue
        
        if in_target_sentence:
            tid, fields = parse_conllu_line(line)
            if tid and fields:
                # Check if HEAD=0 (root)
                head = fields[6]
                if head == '0':
                    return tid
            
            # Empty line means end of sentence
            if not line.strip():
                break
    
    return None


def load_backchannel_candidates(csv_path: Path) -> List[Dict]:
    """Load CSV and filter to task criteria.
    
    Returns list of candidates where A_is_question=0 AND B_all_in_lexicon=1
    """
    candidates = []
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Apply task filter
            if row['A_is_question'] == '0' and row['B_all_in_lexicon'] == '1':
                candidates.append(row)
    
    return candidates


def add_backchannel_to_misc(misc_value: str, backchannel_ref: str) -> str:
    """Add Backchannel= annotation to MISC field.
    
    Args:
        misc_value: Current MISC value (may be '_' or contain other features)
        backchannel_ref: The backchannel reference (e.g., 'Gos073.s374::11')
    
    Returns:
        Updated MISC value
    """
    backchannel_annotation = f'Backchannel={backchannel_ref}'
    
    if misc_value == '_':
        return backchannel_annotation
    else:
        # Append to existing features
        return f'{misc_value}|{backchannel_annotation}'


def apply_annotations(conllu_lines: List[str], candidates: List[Dict]) -> Tuple[List[str], Dict]:
    """Apply backchannel annotations to CoNLL-U lines.
    
    Args:
        conllu_lines: Original lines from CoNLL-U file
        candidates: Backchannel candidates to annotate
    
    Returns:
        - Modified lines (with annotations added)
        - Statistics dict
    """
    # Build index: B_sent_id -> (A_sent_id, root_token_id)
    backchannel_map = {}
    
    for candidate in candidates:
        b_sent_id = candidate['B_sent_id']
        a_sent_id = candidate['A_sent_id']
        
        # Find root token in utterance A
        root_token_id = find_root_token_id(conllu_lines, a_sent_id)
        
        if root_token_id:
            backchannel_ref = f'{a_sent_id}::{root_token_id}'
            backchannel_map[b_sent_id] = backchannel_ref
        else:
            print(f'WARNING: Could not find root token for {a_sent_id}')
    
    # Apply annotations
    modified_lines = []
    current_sent_id = None
    first_token_in_sentence = True
    annotated_count = 0
    
    for line in conllu_lines:
        # Track current sentence
        if line.startswith('# sent_id = '):
            current_sent_id = line.strip().split('= ')[1]
            first_token_in_sentence = True
            modified_lines.append(line)
            continue
        
        # Parse token line
        tid, fields = parse_conllu_line(line)
        
        if tid and fields and first_token_in_sentence:
            # Check if this sentence needs annotation
            if current_sent_id in backchannel_map:
                backchannel_ref = backchannel_map[current_sent_id]
                
                # Modify MISC column (index 9)
                fields[9] = add_backchannel_to_misc(fields[9].strip(), backchannel_ref)
                
                # Reconstruct line
                modified_line = '\t'.join(fields) + '\n'
                modified_lines.append(modified_line)
                annotated_count += 1
            else:
                modified_lines.append(line)
            
            first_token_in_sentence = False
        else:
            modified_lines.append(line)
            
            # Reset on empty line
            if not line.strip():
                first_token_in_sentence = True
    
    stats = {
        'total_candidates': len(candidates),
        'found_roots': len(backchannel_map),
        'annotated': annotated_count
    }
    
    return modified_lines, stats


def main():
    ap = argparse.ArgumentParser(description='Apply backchannel annotations to CoNLL-U file')
    ap.add_argument('--csv', default=None,
                   help='Path to backchannel candidates CSV')
    ap.add_argument('--input', default=None,
                   help='Input CoNLL-U file')
    ap.add_argument('--output', default=None,
                   help='Output CoNLL-U file')
    args = ap.parse_args()
    
    # Set defaults
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    csv_path = (Path(args.csv) if args.csv 
               else project_root / 'output' / 'sst' / 'backchannel_candidates_expanded.csv')
    
    input_path = (Path(args.input) if args.input
                 else project_root / 'src' / 'sst' / 'sl_sst-ud-merged.conllu')
    
    output_path = (Path(args.output) if args.output
                  else project_root / 'output' / 'sst' / 'sl_sst-ud-merged.backchannels.conllu')
    
    print(f'Loading backchannel candidates from {csv_path}')
    candidates = load_backchannel_candidates(csv_path)
    print(f'Loaded {len(candidates)} candidates (A_is_question=0 & B_all_in_lexicon=1)')
    
    print(f'\nReading CoNLL-U from {input_path}')
    conllu_lines = read_conllu(input_path)
    print(f'Read {len(conllu_lines)} lines')
    
    print(f'\nApplying annotations...')
    modified_lines, stats = apply_annotations(conllu_lines, candidates)
    
    print(f'\nStatistics:')
    print(f'  Total candidates: {stats["total_candidates"]}')
    print(f'  Found root tokens: {stats["found_roots"]}')
    print(f'  Annotated sentences: {stats["annotated"]}')
    
    if stats['annotated'] != stats['total_candidates']:
        print(f'\nWARNING: Not all candidates were annotated!')
    
    print(f'\nWriting output to {output_path}')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.writelines(modified_lines)
    
    print(f'\nDone! Annotated {stats["annotated"]} backchannels.')
    print(f'\nNext step: Verify with diff that only MISC column changed:')
    print(f'  diff -u {input_path} {output_path} | head -100')


if __name__ == '__main__':
    main()
