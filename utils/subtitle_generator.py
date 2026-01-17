"""
字幕生成工具类

提供SRT字幕文件生成、时间戳格式化等功能。
"""

import re
from datetime import timedelta
from pathlib import Path
from typing import List

from utils.logger import Logger


class SubtitleSegment:
    """字幕段数据类"""
    def __init__(self, start: float, end: float, text: str):
        self.start = start
        self.end = end
        self.text = text


class SubtitleGenerator:
    """字幕生成工具类"""

    @staticmethod
    def split_long_segments(
        segments: List,
        max_chars_per_line: int = 20,
        max_lines_per_segment: int = 2
    ) -> List:
        """
        智能分割过长的字幕段

        Args:
            segments: 原始字幕段列表
            max_chars_per_line: 每行最大字符数（默认20）
            max_lines_per_segment: 每段最大行数（默认2）

        Returns:
            List: 分割后的字幕段列表
        """
        result_segments = []

        for seg in segments:
            text = seg.text.strip()
            duration = seg.end - seg.start
            text_length = len(text)

            # 如果文本长度很短（严格小于单行），直接使用
            if text_length < max_chars_per_line:
                result_segments.append(seg)
                continue

            # 文本长度等于或超过 max_chars_per_line，检查是否需要分割
            # 检查是否包含标点符号（支持中英文标点）
            has_punctuation = any(c in text for c in '。！？，；、.!?;,')

            if not has_punctuation:
                # 没有标点符号，且长度不超过 max_chars_per_line * max_lines_per_segment，直接使用
                if text_length <= max_chars_per_line * max_lines_per_segment:
                    result_segments.append(seg)
                    continue

            # 需要分割
            Logger.info(f"分割过长的字幕段: {text_length} 字符，时长 {duration:.2f} 秒")

            # 使用递归分割函数
            parts = SubtitleGenerator._split_text_by_punctuation(
                text, max_chars_per_line
            )

            # 为每个部分分配时间戳
            if len(parts) > 1:
                total_chars = sum(len(p) for p in parts)
                current_start = seg.start

                for part in parts:
                    # 根据字符数比例分配时间
                    part_duration = duration * (len(part) / total_chars)
                    part_end = current_start + part_duration

                    # 创建新的字幕段
                    new_seg = SubtitleSegment(
                        start=current_start,
                        end=part_end,
                        text=part
                    )
                    result_segments.append(new_seg)

                    current_start = part_end
            else:
                result_segments.append(seg)

        Logger.info(f"分段处理完成: 原始 {len(segments)} 段 → 处理后 {len(result_segments)} 段")
        return result_segments

    @staticmethod
    def _split_text_by_punctuation(text: str, max_chars: int) -> List[str]:
        """
        按照标点符号智能分割文本，确保每段不超过 max_chars

        Args:
            text: 要分割的文本
            max_chars: 每段最大字符数

        Returns:
            List[str]: 分割后的文本列表
        """
        # 如果文本长度严格小于 max_chars，不需要分割
        if len(text) < max_chars:
            return [text]

        # 如果文本长度等于 max_chars，检查是否包含标点符号
        if len(text) == max_chars:
            has_punctuation = any(c in text for c in '。！？，；、')
            if not has_punctuation:
                return [text]
            # 如果有标点符号，继续进行分割

        # 递归分割函数
        def split_recursive(text: str, max_chars: int) -> List[str]:
            if len(text) <= max_chars:
                return [text]

            # 寻找最佳分割点
            best_split_pos = -1

            # 优先级1: 在 max_chars 范围内寻找句号
            for i in range(min(max_chars, len(text)), 0, -1):
                if text[i-1] in '。！？.!?':
                    best_split_pos = i
                    break

            # 优先级2: 如果没有找到句号，寻找逗号
            if best_split_pos == -1:
                for i in range(min(max_chars, len(text)), 0, -1):
                    if text[i-1] in '，；,;':
                        best_split_pos = i
                        break

            # 优先级3: 如果没有找到逗号，寻找顿号
            if best_split_pos == -1:
                for i in range(min(max_chars, len(text)), 0, -1):
                    if text[i-1] in '、':
                        best_split_pos = i
                        break

            # 优先级4: 如果没有找到任何标点，在 max_chars 处强制分割
            if best_split_pos == -1:
                best_split_pos = min(max_chars, len(text))

            # 分割文本
            first_part = text[:best_split_pos].strip()
            second_part = text[best_split_pos:].strip()

            # 递归处理两部分
            result = []
            result.extend(split_recursive(first_part, max_chars))
            result.extend(split_recursive(second_part, max_chars))

            return result

        return split_recursive(text, max_chars)

    @staticmethod
    def format_timestamp(seconds: float) -> str:
        """
        格式化时间戳为SRT格式

        Args:
            seconds: 时间（秒）

        Returns:
            str: 格式化的时间戳，如 "00:00:01,000"
        """
        td = timedelta(seconds=seconds)
        total_seconds = int(td.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        secs = total_seconds % 60
        milliseconds = int((td.total_seconds() - int(td.total_seconds())) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"

    @staticmethod
    def write_srt(
        segments,
        output_path: Path,
        bilingual: bool = False,
        translated_segments=None,
        max_chars_per_line: int = 20,
        max_lines_per_segment: int = 2
    ):
        """
        写入SRT字幕文件

        Args:
            segments: 字幕片段列表
            output_path: 输出文件路径
            bilingual: 是否为双语字幕
            translated_segments: 翻译后的字幕片段
            max_chars_per_line: 每行最大字符数（默认20）
            max_lines_per_segment: 每段最大行数（默认2）
        """
        output_path = Path(output_path).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 智能分割过长的字幕段
        segments = SubtitleGenerator.split_long_segments(
            segments,
            max_chars_per_line=max_chars_per_line,
            max_lines_per_segment=max_lines_per_segment
        )

        with open(output_path, "w", encoding="utf-8") as f:
            for i, seg in enumerate(segments, start=1):
                start = SubtitleGenerator.format_timestamp(seg.start)
                end = SubtitleGenerator.format_timestamp(seg.end)
                orig = seg.text.strip()

                if bilingual and translated_segments:
                    trans = translated_segments[i-1].text.strip() if i-1 < len(translated_segments) else ""
                    text_block = (orig + "\n" + trans).strip()
                else:
                    text_block = orig

                f.write(f"{i}\n{start} --> {end}\n{text_block}\n\n")

    @staticmethod
    def wrap_chinese_text(text: str, video_width: int, font_size: int) -> str:
        """
        处理中文字幕自动换行

        Args:
            text: 原始文本
            video_width: 视频宽度
            font_size: 字体大小

        Returns:
            str: 处理后的文本，包含换行符
        """
        margin = 40
        available_width = video_width - margin * 2
        char_per_line = int(available_width / (font_size * 0.6))

        lines = text.split(r'\N')
        wrapped_lines = []

        for line in lines:
            if len(line) <= char_per_line:
                wrapped_lines.append(line)
            else:
                current_line = ""
                for char in line:
                    if '\u4e00' <= char <= '\u9fff' or char in '，。！？；：""''（）【】《》':
                        if len(current_line) >= char_per_line:
                            wrapped_lines.append(current_line)
                            current_line = char
                        else:
                            current_line += char
                    else:
                        if len(current_line) >= char_per_line * 1.5:
                            wrapped_lines.append(current_line)
                            current_line = char
                        else:
                            current_line += char

                if current_line:
                    wrapped_lines.append(current_line)

        return r'\N'.join(wrapped_lines)

    @staticmethod
    def get_subtitle_style_config(video_width: int) -> dict:
        """
        根据视频宽度获取字幕样式配置

        根据最佳实践设置字体大小：
        - 640x480 (SD): 字体大小 18，适合低分辨率视频
        - 720p (1280x720): 字体大小 26，适合高清视频
        - 1080p (1920x1080): 字体大小 36，适合全高清视频
        - 4K (3840x2160): 字体大小 50，适合超高清视频

        Args:
            video_width: 视频宽度

        Returns:
            dict: 字幕样式配置字典
        """
        if video_width <= 640:
            # SD 分辨率 (640x480)
            font_size = 18
            margin = 8
            outline = 2
        elif video_width <= 720:
            # 介于 SD 和 720p 之间
            font_size = 24
            margin = 10
            outline = 2
        elif video_width <= 1280:
            # 720p 高清 (1280x720)
            font_size = 48
            margin = 12
            outline = 3
        elif video_width <= 1920:
            # 1080p 全高清 (1920x1080)
            font_size = 80
            margin = 15
            outline = 3
        elif video_width <= 2560:
            # 2K 分辨率 (2560x1440)
            font_size = 100
            margin = 18
            outline = 4
        else:
            # 4K 超高清 (3840x2160) 及以上
            font_size = 100
            margin = 20
            outline = 4

        return {
            'font_size': font_size,
            'margin': margin,
            'font_name': 'Arial',
            'primary_color': '&H00ffffff',
            'secondary_color': '&H000000FF',
            'outline_color': '&H00000000',
            'back_color': '&H80000000',
            'bold': 1,
            'italic': 0,
            'border_style': 1,
            'outline': outline,
            'shadow': 2,  # 增加阴影效果
            'alignment': 2,
            'encoding': 1
        }

    @staticmethod
    def create_ass_subtitle(srt_path: Path, output_dir: Path, video_width: int, platform_suffix: str = "", subtitle_bottom_margin: int = 50) -> Path:
        """
        创建ASS字幕文件，支持中文自动换行

        Args:
            srt_path: SRT文件路径
            output_dir: 输出目录
            video_width: 视频宽度
            platform_suffix: 平台后缀（用于区分临时文件）
            subtitle_bottom_margin: 字幕下沿距离（像素），默认为50

        Returns:
            Path: ASS文件路径
        """
        style_config = SubtitleGenerator.get_subtitle_style_config(video_width)

        # 完整的 ASS 文件头部
        header_content = f"""[Script Info]
Title: Generated Subtitles
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709
PlayResX: {video_width}
PlayResY: {video_width // 16 * 9}  # 保持16:9比例

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{style_config['font_name']},{style_config['font_size']},{style_config['primary_color']},{style_config['secondary_color']},{style_config['outline_color']},{style_config['back_color']},{style_config['bold']},{style_config['italic']},0,0,100,100,0,0,{style_config['border_style']},{style_config['outline']},{style_config['shadow']},{style_config['alignment']},{style_config['margin']},{style_config['margin']},{subtitle_bottom_margin},{style_config['encoding']}

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"""

        ass_content = []
        ass_content.append(header_content)

        with open(srt_path, 'r', encoding='utf-8') as f:
            srt_content = f.read()

        srt_blocks = re.split(r'\n\s*\n', srt_content.strip())

        for block in srt_blocks:
            lines = block.strip().split('\n')
            if len(lines) >= 3:
                time_match = re.match(r'(\d{1,2}):(\d{2}):(\d{2}),(\d{3}) --> (\d{1,2}):(\d{2}):(\d{2}),(\d{3})', lines[1])
                if time_match:
                    h1, m1, s1, ms1, h2, m2, s2, ms2 = time_match.groups()
                    # 修复时间戳格式：使用正确的ASS格式 H:MM:SS.CS (百分之一秒)
                    start_time = f"{int(h1)}:{m1}:{s1}.{int(ms1)//10:02d}"
                    end_time = f"{int(h2)}:{m2}:{s2}.{int(ms2)//10:02d}"

                    text = r'\N'.join(lines[2:])
                    text = text.replace('<', '&lt;').replace('>', '&gt;')

                    text = SubtitleGenerator.wrap_chinese_text(text, video_width, style_config['font_size'])

                    ass_content.append(f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{text}")

        temp_ass_path = output_dir / f"{srt_path.stem}_temp{platform_suffix}.ass"
        with open(temp_ass_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(ass_content))

        Logger.info(f"ASS字幕文件已创建: {temp_ass_path}")
        return temp_ass_path