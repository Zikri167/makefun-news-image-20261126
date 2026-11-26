"""news-image-20261126 entrypoint (Python 3.13, stdlib only).

Draws the 26 November 2026 world-news front page and writes it to
/output/entry.png. No network, no randomness, no clock: two runs write
byte-identical output. Outside the grader, MAKEFUN_OUTPUT_DIR stands
in for /output.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from draw import render  # noqa: E402  (path fix above must come first)

out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
os.makedirs(out_dir, exist_ok=True)
# render() is pure: same input, same bytes, every run.
n = render(os.path.join(out_dir, "entry.png"))
print(f"wrote entry.png ({n} bytes)")
