#!/usr/bin/env python3
"""Workflow step 02: delegate to extract_backchannels_new.py."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def main() -> None:
    target = Path(__file__).with_name("extract_backchannels_new.py")
    os.execv(sys.executable, [sys.executable, str(target), *sys.argv[1:]])


if __name__ == "__main__":
    main()
