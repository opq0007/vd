# -*- coding: utf-8 -*-
"""
Debug subtitle split issue
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.subtitle_generator import SubtitleGenerator

# Test case that's failing
text = "钱哥说,今天是你18岁生日,我们全体奥特曼,祝你生日快乐,浊壮成长,我们"
max_chars = 20

print(f"Input text: {text}")
print(f"Text length: {len(text)}")
print(f"Max chars: {max_chars}")
print()

# Test _split_text_by_punctuation
result = SubtitleGenerator._split_text_by_punctuation(text, max_chars)

print(f"Result segments: {len(result)}")
for i, part in enumerate(result, 1):
    print(f"  {i}. [{len(part)} chars] {part}")

# Validate
if any(len(part) > max_chars for part in result):
    print("\nERROR: Found segments exceeding limit!")
else:
    print("\nOK: All segments within limit")

# Test completeness
combined = ''.join(result)
if combined != text:
    print(f"ERROR: Text not complete!")
    print(f"  Original: {text}")
    print(f"  Combined: {combined}")
else:
    print("OK: Text is complete")