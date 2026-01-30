#!/usr/bin/env python3
"""
Script to merge all CoNLL-U files from src/sst directory into a single corpus file.
"""

import os
from pathlib import Path


def merge_conllu_files(input_dir, output_file):
    """
    Merge all .conllu files from input_dir into a single output file.
    
    Args:
        input_dir: Directory containing .conllu files
        output_file: Path to the output merged corpus file
    """
    input_path = Path(input_dir)
    
    # Get all .conllu files sorted by name
    conllu_files = sorted(input_path.glob("*.conllu"))
    
    if not conllu_files:
        print(f"No .conllu files found in {input_dir}")
        return
    
    print(f"Found {len(conllu_files)} files to merge:")
    for file in conllu_files:
        print(f"  - {file.name}")
    
    # Merge files
    with open(output_file, 'w', encoding='utf-8') as outf:
        for i, file_path in enumerate(conllu_files):
            print(f"Processing {file_path.name}...")
            
            with open(file_path, 'r', encoding='utf-8') as inf:
                content = inf.read()
                outf.write(content)
                
                # Add a blank line between files if not already present
                # and if this is not the last file
                if i < len(conllu_files) - 1:
                    if not content.endswith('\n\n'):
                        if content.endswith('\n'):
                            outf.write('\n')
                        else:
                            outf.write('\n\n')
    
    print(f"\nSuccessfully merged {len(conllu_files)} files into: {output_file}")


if __name__ == "__main__":
    # Define paths relative to script location
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    input_directory = project_root / "src" / "sst"
    output_filepath = project_root / "src" / "sst" / "sl_sst-ud-merged.conllu"
    
    merge_conllu_files(input_directory, output_filepath)
