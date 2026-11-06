#!/usr/bin/env python3
"""Run suites in separate processes so similarly named connector modules stay isolated."""
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
for directory in ['skills/literature-search-review/tests','connectors/openalex-local','connectors/literature-access/tests','tests']:
    subprocess.run([sys.executable,'-m','unittest','discover','-s',str(ROOT/directory),'-v'],cwd=ROOT,check=True)
