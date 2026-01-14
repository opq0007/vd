"""
字幕纠错工具类

使用智谱 AI 模型对生成的字幕内容进行智能纠错。
"""

import json
import requests
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from config import config
from utils.logger import Logger


@dataclass
class SubtitleSegment:
    """字幕片段"""
    start: float
    end: float
    text: str


class LLMCorrector:
    """基于 LLM 的字幕纠错器"""

    def __init__(self):
        self.api_key = config.ZHIPU_API_KEY
        self.api_url = config.ZHIPU_API_URL
        self.model = config.ZHIPU_MODEL
        self.temperature = config.ZHIPU_TEMPERATURE
        self.max_tokens = config.ZHIPU_MAX_TOKENS

        if not self.api_key:
            Logger.warning("智谱 AI API Key 未配置，字幕纠错功能将不可用")

    def _call_llm(self, messages: List[Dict[str, str]]) -> Optional[str]:
        """
        调用智谱 AI API

        Args:
            messages: 消息列表

        Returns:
            Optional[str]: API 返回的文本内容
        """
        if not self.api_key:
            raise ValueError("智谱 AI API Key 未配置")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": False
        }

        try:
            Logger.info(f"调用智谱 AI API: {self.model}")
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()

            result = response.json()
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")

            Logger.info(f"智谱 AI API 调用成功，返回 {len(content)} 字符")
            return content

        except requests.exceptions.RequestException as e:
            Logger.error(f"智谱 AI API 调用失败: {e}")
            return None
        except (KeyError, IndexError) as e:
            Logger.error(f"智谱 AI API 响应解析失败: {e}")
            return None

    def correct_subtitle_text(
        self,
        subtitle_text: str,
        reference_text: str
    ) -> Optional[str]:
        """
        纠正字幕文本

        Args:
            subtitle_text: 原始字幕文本
            reference_text: 参考文本

        Returns:
            Optional[str]: 纠正后的字幕文本
        """
        if not self.api_key:
            Logger.warning("智谱 AI API Key 未配置，跳过字幕纠错")
            return subtitle_text

        if not reference_text or not reference_text.strip():
            Logger.warning("参考文本为空，跳过字幕纠错")
            return subtitle_text

        # 打印纠错前的信息
        Logger.info("=" * 80)
        Logger.info("开始 LLM 字幕纠错")
        Logger.info("=" * 80)
        Logger.info(f"原始字幕文本（{len(subtitle_text)} 字符）：")
        Logger.info(subtitle_text)
        Logger.info("-" * 80)
        Logger.info(f"参考文本（{len(reference_text)} 字符）：")
        Logger.info(reference_text)
        Logger.info("-" * 80)

        # 构建提示词
        system_prompt = """你是一个专业的字幕纠错助手。你的任务是根据参考文本，对识别的字幕文本进行纠错。

纠错规则：
1. 对比识别的字幕文本和参考文本，找出错字、漏字、多字等错误
2. 以参考文本为准，纠正字幕中的错误
3. 保持字幕的语义和语序，只纠正明显的错误
4. 如果参考文本和字幕文本内容基本一致，仅做微调
5. 返回纠正后的完整字幕文本，不要添加任何解释或说明
6. 需要确保返回的完整字幕文本以换行符\n分隔，并且保证行数和原始字幕文本的行数一致！

请直接返回纠正后的字幕文本，不要包含任何其他内容。"""

        user_prompt = f"""参考文本：
{reference_text}

识别的字幕文本：
{subtitle_text}

请根据参考文本纠正字幕文本中的错误，返回纠正后的完整字幕文本："""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        # 调用 LLM
        corrected_text = self._call_llm(messages)

        if corrected_text:
            Logger.info(f"纠正后字幕文本（{len(corrected_text)} 字符）：")
            Logger.info(corrected_text)
            Logger.info("-" * 80)

            # 对比纠错前后的差异
            if corrected_text != subtitle_text:
                Logger.info("检测到字幕内容变化：")
                original_lines = subtitle_text.split('\n')
                corrected_lines = corrected_text.split('\n')

                for i, (orig, corr) in enumerate(zip(original_lines, corrected_lines)):
                    if orig != corr:
                        Logger.info(f"  第 {i+1} 行:")
                        Logger.info(f"    原文: {orig}")
                        Logger.info(f"    纠正: {corr}")
            else:
                Logger.info("字幕内容未发生变化")

            Logger.info(f"字幕纠错完成，原文: {len(subtitle_text)} 字符，纠正后: {len(corrected_text)} 字符")
            Logger.info("=" * 80)
            return corrected_text
        else:
            Logger.warning("字幕纠错失败，返回原始字幕文本")
            Logger.info("=" * 80)
            return subtitle_text

    def correct_subtitle_segments(
        self,
        segments: List[SubtitleSegment],
        reference_text: str
    ) -> List[SubtitleSegment]:
        """
        纠正字幕片段

        Args:
            segments: 字幕片段列表
            reference_text: 参考文本

        Returns:
            List[SubtitleSegment]: 纠正后的字幕片段列表
        """
        if not segments:
            Logger.warning("字幕片段列表为空，跳过纠错")
            return segments

        Logger.info(f"开始纠错字幕片段，共 {len(segments)} 个片段")

        # 记录原始片段信息
        Logger.info("原始字幕片段信息：")
        for i, seg in enumerate(segments):
            Logger.info(f"  片段 {i+1}: [{seg.start:.2f}s - {seg.end:.2f}s] {seg.text}")

        # 将所有片段的文本合并
        subtitle_text = "\n".join([seg.text for seg in segments])

        # 调用纠错
        corrected_text = self.correct_subtitle_text(subtitle_text, reference_text)

        if corrected_text is None or corrected_text == subtitle_text:
            # 纠错失败或无需纠错，返回原始片段
            Logger.info("字幕纠错失败或无需纠错，返回原始片段")
            return segments

        # 将纠正后的文本重新分割为片段
        corrected_lines = corrected_text.split('\n')

        # 如果行数不一致，简单处理：按原文行数分割
        if len(corrected_lines) != len(segments):
            Logger.warning(f"纠正后行数不一致（原文: {len(segments)}, 纠正后: {len(corrected_lines)}），尝试重新分割")
            # 按原文行数平均分割
            avg_length = len(corrected_text) // len(segments)
            corrected_lines = []
            for i in range(len(segments)):
                start = i * avg_length
                end = (i + 1) * avg_length if i < len(segments) - 1 else len(corrected_text)
                corrected_lines.append(corrected_text[start:end].strip())

        # 更新片段的文本并记录变化
        Logger.info("字幕片段纠错结果：")
        changes_count = 0
        for i, seg in enumerate(segments):
            if i < len(corrected_lines):
                original_text = seg.text
                seg.text = corrected_lines[i]

                if original_text != seg.text:
                    changes_count += 1
                    Logger.info(f"  片段 {i+1} [{seg.start:.2f}s - {seg.end:.2f}s] - 已修改:")
                    Logger.info(f"    原文: {original_text}")
                    Logger.info(f"    纠正: {seg.text}")
                else:
                    Logger.info(f"  片段 {i+1} [{seg.start:.2f}s - {seg.end:.2f}s] - 未修改: {seg.text}")
            else:
                Logger.warning(f"  片段 {i+1} - 无对应纠正文本")

        Logger.info(f"字幕片段纠错完成，共 {len(segments)} 个片段，其中 {changes_count} 个片段被修改")
        Logger.info("=" * 80)
        return segments


# 创建全局实例
llm_corrector = LLMCorrector()
