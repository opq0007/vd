# -*- coding: utf-8 -*-
"""
Direct test of split_long_segments
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.subtitle_generator import SubtitleGenerator, SubtitleSegment

# Create test segments
test_segments = [
    SubtitleSegment(start=10.0, end=20.0, text="钱哥说,今天是你18岁生日,我们全体奥特曼,祝你生日快乐,浊壮成长,我们"),
]

print("Before processing:")
for i, seg in enumerate(test_segments, 1):
    print(f"  {i}. [{len(seg.text)} chars] {seg.text}")

result = SubtitleGenerator.split_long_segments(
    test_segments,
    max_chars_per_line=20,
    max_lines_per_segment=2
)

print("\nAfter processing:")
for i, seg in enumerate(result, 1):
    print(f"  {i}. [{len(seg.text)} chars] {seg.text}")

# Validate
if any(len(seg.text) > 20 for seg in result):
    print("\nERROR: Found segments exceeding 20 chars!")
else:
    print("\nOK: All segments within limit")