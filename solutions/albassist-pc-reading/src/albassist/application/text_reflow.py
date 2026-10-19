"""文字重排服务。

中文逐字断行、英文按词断行、中英混排按字符类型切换断点。
禁止自动改写/润色/补字。
"""

from __future__ import annotations

from dataclasses import dataclass

from albassist.domain.models.ocr_models import OcrBlock


@dataclass(frozen=True)
class ReflowLine:
    """重排后的一行。"""

    text: str
    block_index: int
    is_continuation: bool


@dataclass(frozen=True)
class ReflowResult:
    """重排结果。"""

    lines: tuple[ReflowLine, ...]
    total_chars: int


def _is_cjk(char: str) -> bool:
    """判断是否为 CJK 字符（中文/日文/韩文）。"""
    if not char:
        return False
    code = ord(char)
    return (
        0x4E00 <= code <= 0x9FFF
        or 0x3400 <= code <= 0x4DBF
        or 0x20000 <= code <= 0x2A6DF
        or 0x2A700 <= code <= 0x2B73F
        or 0x2B740 <= code <= 0x2B81F
        or 0x2B820 <= code <= 0x2CEAF
        or 0xF900 <= code <= 0xFAFF
        or 0x2F800 <= code <= 0x2FA1F
    )


def _is_word_char(char: str) -> bool:
    """是否为英文单词字符。"""
    return char.isalnum() or char in "'-"


def _estimate_char_width(char: str, font_size: int) -> float:
    """估算字符显示宽度（像素）。

    CJK 字符约等于字号宽度，英文约 0.6 倍字号。
    """
    if _is_cjk(char):
        return float(font_size)
    return font_size * 0.6


class TextReflow:
    """文字重排服务。"""

    @staticmethod
    def reflow(
        blocks: tuple[OcrBlock, ...] | list[OcrBlock],
        view_width: int,
        font_size: int,
        line_spacing: float = 1.5,
    ) -> ReflowResult:
        """按视窗宽度重排文字。

        Args:
            blocks: OCR 文字块列表。
            view_width: 视窗宽度（像素）。
            font_size: 字号（逻辑像素）。
            line_spacing: 行距倍数。

        Returns:
            ReflowResult: 重排后的行列表。
        """
        if view_width <= 0 or font_size <= 0:
            return ReflowResult(lines=(), total_chars=0)

        lines: list[ReflowLine] = []
        total_chars = 0

        for block_idx, block in enumerate(blocks):
            text = block.text
            total_chars += len(text)

            current_line = ""
            current_width = 0.0
            i = 0
            is_continuation = False

            while i < len(text):
                char = text[i]

                if _is_cjk(char):
                    char_w = _estimate_char_width(char, font_size)
                    if current_width + char_w > view_width and current_line:
                        lines.append(
                            ReflowLine(current_line, block_idx, is_continuation)
                        )
                        current_line = ""
                        current_width = 0.0
                        is_continuation = True
                    current_line += char
                    current_width += char_w
                    i += 1
                elif _is_word_char(char):
                    word = ""
                    word_width = 0.0
                    while i < len(text) and _is_word_char(text[i]):
                        w = _estimate_char_width(text[i], font_size)
                        word += text[i]
                        word_width += w
                        i += 1

                    if current_width + word_width > view_width and current_line:
                        lines.append(
                            ReflowLine(current_line, block_idx, is_continuation)
                        )
                        current_line = ""
                        current_width = 0.0
                        is_continuation = True
                    current_line += word
                    current_width += word_width
                else:
                    char_w = _estimate_char_width(char, font_size)
                    if current_width + char_w > view_width and current_line:
                        lines.append(
                            ReflowLine(current_line, block_idx, is_continuation)
                        )
                        current_line = ""
                        current_width = 0.0
                        is_continuation = True
                    current_line += char
                    current_width += char_w
                    i += 1

            if current_line:
                lines.append(ReflowLine(current_line, block_idx, is_continuation))

        return ReflowResult(lines=tuple(lines), total_chars=total_chars)