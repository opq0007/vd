"""
字幕生成工具类

提供SRT字幕文件生成、时间戳格式化等功能。
"""

import re
from datetime import timedelta
from pathlib import Path
from typing import List

from utils.logger import Logger


class SubtitleGenerator:
    """字幕生成工具类"""

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
    def write_srt(segments, output_path: Path, bilingual: bool = False, translated_segments=None):
        """
        写入SRT字幕文件

        Args:
            segments: 字幕片段列表
            output_path: 输出文件路径
            bilingual: 是否为双语字幕
            translated_segments: 翻译后的字幕片段
        """
        output_path = Path(output_path).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)

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
            font_size = 22
            margin = 10
            outline = 2
        elif video_width <= 1280:
            # 720p 高清 (1280x720)
            font_size = 26
            margin = 12
            outline = 3
        elif video_width <= 1920:
            # 1080p 全高清 (1920x1080)
            font_size = 36
            margin = 15
            outline = 3
        elif video_width <= 2560:
            # 2K 分辨率 (2560x1440)
            font_size = 44
            margin = 18
            outline = 4
        else:
            # 4K 超高清 (3840x2160) 及以上
            font_size = 50
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
            'shadow': 1,
            'alignment': 2,
            'encoding': 1
        }

    @staticmethod
    def create_ass_subtitle(srt_path: Path, output_dir: Path, video_width: int, platform_suffix: str = "") -> Path:
        """
        创建ASS字幕文件，支持中文自动换行

        Args:
            srt_path: SRT文件路径
            output_dir: 输出目录
            video_width: 视频宽度
            platform_suffix: 平台后缀（用于区分临时文件）

        Returns:
            Path: ASS文件路径
        """
        style_config = SubtitleGenerator.get_subtitle_style_config(video_width)

        # 完整的 ASS 文件头部
        header_content = f"""[Script Info]
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709
PlayResX: {video_width}
PlayResY: 600

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{style_config['font_name']},{style_config['font_size']},{style_config['primary_color']},{style_config['secondary_color']},{style_config['outline_color']},{style_config['back_color']},{style_config['bold']},{style_config['italic']},0,0,100,100,0,0,{style_config['border_style']},{style_config['outline']},{style_config['shadow']},{style_config['alignment']},{style_config['margin']},{style_config['margin']},5,{style_config['encoding']}

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
                    start_time = f"{int(h1):01d}:{m1}:{s1}.{ms1}0"
                    end_time = f"{int(h2):01d}:{m2}:{s2}.{ms2}0"

                    text = r'\N'.join(lines[2:])
                    text = text.replace('<', '&lt;').replace('>', '&gt;')

                    text = SubtitleGenerator.wrap_chinese_text(text, video_width, style_config['font_size'])

                    ass_content.append(f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{text}")

        temp_ass_path = output_dir / f"{srt_path.stem}_temp{platform_suffix}.ass"
        with open(temp_ass_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(ass_content))

        Logger.info(f"ASS字幕文件已创建: {temp_ass_path}")
        return temp_ass_path