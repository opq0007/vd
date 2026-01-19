# -*- coding: utf-8 -*-
"""
Subtitle Split Test Cases

Test SubtitleGenerator.split_long_segments and _split_text_by_punctuation methods
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.subtitle_generator import SubtitleGenerator


def test_split_by_punctuation():
    """Test splitting text by punctuation"""
    print("=" * 60)
    print("Testing Punctuation Splitting")
    print("=" * 60)

    test_cases = [
        # (input text, max_chars, expected segment count)
        ("亲爱的钟真真小朋友,你好啊,我们是奥特曼家族,我们刚从外星球执行完任务回来。", 20, 4),
        ("钱哥说,今天是你18岁生日,我们全体奥特曼,祝你生日快乐,浊壮成长,我们", 20, 4),
        ("马上返回地球,为你庆祝,真真,你非常懂事,有礼貌,我们和钱哥会一直守护你。", 20, 4),
        ("对了,你要多吃蔬菜,才能充满能量。", 20, 2),
        ("要学会独立吃饭,少看手机,一定要早睡早起,成为一个勇敢无味的小朋友。", 20, 4),
        ("真真,你是我们在地球上最喜欢的小朋友,勇敢的往前冲吧。", 20, 3),
        ("等你长大变强壮之后,欢迎你加入我们光之国,和我们一起保卫地球,接受我们的祝福吧。", 20, 4),
        ("短文本", 20, 1),
        ("这是一个没有标点符号的很长很长的文本需要按照字符长度来分割", 20, 3),
        ("第一句。第二句！第三句？第四句", 20, 4),
    ]

    for text, max_chars, expected_count in test_cases:
        result = SubtitleGenerator._split_text_by_punctuation(text, max_chars)

        print(f"\nInput: {text}")
        print(f"Max chars: {max_chars}")
        print(f"Expected segments: {expected_count}, Actual: {len(result)}")
        print(f"Result:")
        for i, part in enumerate(result, 1):
            print(f"  {i}. [{len(part)} chars] {part}")

        # Validate each segment length
        all_valid = all(len(part) <= max_chars for part in result)
        if not all_valid:
            print(f"  ERROR: Found segments exceeding {max_chars} chars!")
        else:
            print(f"  OK: All segments within limit")

        # Validate completeness
        combined = ''.join(result)
        if combined != text:
            print(f"  ERROR: Text not complete after split!")
            print(f"     Original: {text}")
            print(f"     Combined: {combined}")
        else:
            print(f"  OK: Text completeness validated")


def test_split_segments():
    """Test splitting subtitle segments"""
    print("\n" + "=" * 60)
    print("Testing Segment Splitting")
    print("=" * 60)

    # Create test segments
    from utils.subtitle_generator import SubtitleSegment

    test_segments = [
        SubtitleSegment(start=0.0, end=10.0, text="亲爱的钟真真小朋友,你好啊,我们是奥特曼家族,我们刚从外星球执行完任务回来。"),
        SubtitleSegment(start=10.0, end=20.0, text="钱哥说,今天是你18岁生日,我们全体奥特曼,祝你生日快乐,浊壮成长,我们"),
        SubtitleSegment(start=20.0, end=30.0, text="短文本"),
    ]

    result = SubtitleGenerator.split_long_segments(
        test_segments,
        max_chars_per_line=20,
        max_lines_per_segment=2
    )

    print(f"\nOriginal segments: {len(test_segments)}")
    print(f"After processing: {len(result)}")

    for i, seg in enumerate(result, 1):
        print(f"\nSegment {i}:")
        print(f"  Time: {seg.start:.3f} --> {seg.end:.3f}")
        print(f"  Text: {seg.text}")
        print(f"  Length: {len(seg.text)} chars")

        # Validate length
        if len(seg.text) > 20:
            print(f"  ERROR: Exceeds 20 chars!")
        else:
            print(f"  OK: Length within limit")


def test_edge_cases():
    """Test edge cases"""
    print("\n" + "=" * 60)
    print("Testing Edge Cases")
    print("=" * 60)

    edge_cases = [
        ("", 20, "Empty string"),
        ("A", 20, "Single character"),
        ("A" * 20, 20, "Exactly 20 characters"),
        ("A" * 21, 20, "21 characters"),
        ("，" * 10, 20, "Only commas"),
        ("。" * 10, 20, "Only periods"),
    ]

    for text, max_chars, description in edge_cases:
        result = SubtitleGenerator._split_text_by_punctuation(text, max_chars)

        print(f"\nTest: {description}")
        print(f"  Input: [{len(text)} chars] {text[:50]}...")
        print(f"  Output segments: {len(result)}")

        for i, part in enumerate(result, 1):
            print(f"    Seg{i}: [{len(part)} chars] {part}")

        # Validate
        if len(result) == 0 and len(text) > 0:
            print(f"  ERROR: Input has content but no output!")
        elif any(len(part) > max_chars for part in result):
            print(f"  ERROR: Found segments exceeding {max_chars} chars!")
        else:
            print(f"  OK: Test passed")


if __name__ == "__main__":
    print("Starting subtitle split tests\n")

    test_split_by_punctuation()
    test_split_segments()
    test_edge_cases()

    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)