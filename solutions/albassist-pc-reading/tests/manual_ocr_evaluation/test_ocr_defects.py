"""OCR 与图像处理逻辑测试 - 坐标映射、缩放、粉笔字处理缺陷检查。

无需真实 OCR 引擎，通过代码走读和逻辑验证发现问题。
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

# 将 src 加入路径以导入项目代码
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from albassist.domain.geometry import ImageRect
from albassist.domain.models.image_frame import ImageFrame
from albassist.domain.models.visual_config import VisualConfig, VisualMode


@dataclass
class ZoomMappingTestCase:
    """缩放坐标映射测试用例。"""

    name: str
    frame_width: int
    frame_height: int
    widget_width: int
    widget_height: int
    zoom_factor: float
    selection_view_x: int
    selection_view_y: int
    selection_view_w: int
    selection_view_h: int
    expected_source_x: int
    expected_source_y: int
    expected_source_w: int
    expected_source_h: int


def _make_frame(width: int, height: int) -> ImageFrame:
    stride = width * 3
    return ImageFrame(
        frame_id="test",
        width=width,
        height=height,
        stride=stride,
        pixel_format="RGB24",
        pixels=b"\x00" * (stride * height),
        captured_at=datetime.now(timezone.utc),
    )


def test_original_view_selection_mapping() -> dict[str, dict]:
    """测试 OriginalView.get_selection() 的坐标映射逻辑。

    模拟 OriginalView._rendered_scale() 和 get_selection() 的计算过程。
    """
    results: dict[str, dict] = {}

    cases = [
        ZoomMappingTestCase(
            name="1x zoom, centered",
            frame_width=1000,
            frame_height=500,
            widget_width=1000,
            widget_height=500,
            zoom_factor=1.0,
            selection_view_x=500,
            selection_view_y=250,
            selection_view_w=200,
            selection_view_h=100,
            expected_source_x=500,
            expected_source_y=250,
            expected_source_w=200,
            expected_source_h=100,
        ),
        ZoomMappingTestCase(
            name="2x zoom, centered",
            frame_width=1000,
            frame_height=500,
            widget_width=1000,
            widget_height=500,
            zoom_factor=2.0,
            selection_view_x=500,
            selection_view_y=250,
            selection_view_w=400,
            selection_view_h=200,
            expected_source_x=250,
            expected_source_y=125,
            expected_source_w=200,
            expected_source_h=100,
        ),
        ZoomMappingTestCase(
            name="1.0x zoom (no zoom), centered",
            frame_width=1000,
            frame_height=500,
            widget_width=1000,
            widget_height=500,
            zoom_factor=1.0,
            selection_view_x=250,
            selection_view_y=125,
            selection_view_w=100,
            selection_view_h=50,
            expected_source_x=250,
            expected_source_y=125,
            expected_source_w=100,
            expected_source_h=50,
        ),
    ]

    for case in cases:
        frame = _make_frame(case.frame_width, case.frame_height)
        config = VisualConfig(zoom_factor=case.zoom_factor)

        # 模拟 OriginalView._rendered_scale()
        widget_w = max(case.widget_width, 1)
        widget_h = max(case.widget_height, 1)
        base_scale = min(widget_w / frame.width, widget_h / frame.height)
        total_scale = config.zoom_factor * base_scale

        # 模拟 OriginalView.get_selection() 中的计算
        img_w = max(int(frame.width * total_scale), 1)
        img_h = max(int(frame.height * total_scale), 1)
        img_x = (case.widget_width - img_w) // 2  # offset = (0, 0)
        img_y = (case.widget_height - img_h) // 2

        x = int((case.selection_view_x - img_x) / total_scale)
        y = int((case.selection_view_y - img_y) / total_scale)
        w = int(case.selection_view_w / total_scale)
        h = int(case.selection_view_h / total_scale)

        source_rect = ImageRect(x, y, w, h).clamp_to(frame.width, frame.height)

        passed = (
            source_rect.x == case.expected_source_x
            and source_rect.y == case.expected_source_y
            and source_rect.width == case.expected_source_w
            and source_rect.height == case.expected_source_h
        )

        results[case.name] = {
            "passed": passed,
            "actual": (source_rect.x, source_rect.y, source_rect.width, source_rect.height),
            "expected": (case.expected_source_x, case.expected_source_y, case.expected_source_w, case.expected_source_h),
            "total_scale": round(total_scale, 4),
        }

    return results


def test_ocr_engine_roi_with_zoom() -> dict[str, str]:
    """检查 OCR 引擎 ROI 处理与显示缩放的耦合问题。

    核心缺陷：OCR 引擎接收的是原图，不是显示缩放后的图。
    如果原图分辨率低，用户放大显示看清楚了，但 OCR 输入仍是低分辨率。
    """
    findings: dict[str, str] = {}

    # 场景1：原图 640x360（低分辨率），用户放大到 2x 显示
    findings["低分辨率原图 + 高显示缩放"] = (
        "原图 640x360，用户 zoom=2.0 显示放大到 1280x720 看清楚。"
        "但 OCR 引擎 rapid_engine.py 接收的是原图 ImageFrame，"
        "在 640x360 上裁剪 ROI 进行识别。低分辨率导致文字笔画模糊，"
        "OCR 准确率下降。显示缩放不改善 OCR 输入质量。"
    )

    # 场景2：原图 5120x2880（高分辨率），用户缩小到 0.5x 显示
    findings["高分辨率原图 + 低显示缩放"] = (
        "原图 5120x2880，用户 zoom=0.5 显示缩小。"
        "OCR 引擎在原图高分辨率上运行，识别质量好。"
        "但选区坐标映射需要更精确（整数除法舍入误差）。"
    )

    # 场景3：ROI 过小
    findings["极小 ROI 裁剪后为空"] = (
        "rapid_engine.py 第 82-92 行：如果 ROI 裁剪后 img.shape[0]==0 "
        "或 img.shape[1]==0，返回空结果。"
        "但在 get_selection() 中，整数除法可能导致 1x1 像素的 ROI，"
        "此时 OCR 返回空，用户无感知原因。"
    )

    return findings


def test_chalkboard_preprocessing_gap() -> dict[str, str]:
    """检查粉笔字场景下的预处理缺失。"""
    findings: dict[str, str] = {}

    findings["无自动反色检测"] = (
        "粉笔字场景为黑底白字，PP-OCRv4 训练数据主要为白底黑字印刷体。"
        "代码中没有自动检测黑底白字并反色的逻辑。"
        "用户需手动切换 VisualMode.INVERT，但低视力学生可能无法意识到这个问题。"
    )

    findings["无去噪/边缘增强"] = (
        "粉笔字有飞粉、黑板纹理反光、笔画粗细不均等特征。"
        "代码中没有针对这些特征的预处理："
        "- 无中值滤波去飞粉\n"
        "- 无形态学操作平滑笔画\n"
        "- 无自适应阈值处理反光区域\n"
        "- 无超分辨率放大低分辨率黑板照片"
    )

    findings["反色后二值化阈值固定"] = (
        "BINARIZE 模式使用固定阈值 127.5（或 OTSU 在 original_view.py 中）。"
        "对于粉笔字反色后的图像，固定阈值可能无法适应不同光照条件下的黑板。"
        "应使用自适应阈值（adaptiveThreshold）替代全局阈值。"
    )

    findings["LOCAL_CONTRAST 对粉笔字帮助有限"] = (
        "CLAHE 局部对比度增强对粉笔字有帮助，但只在灰度通道上操作。"
        "粉笔字的飞粉噪声也会被增强，可能导致 OCR 检测出假文字块。"
    )

    return findings


def test_zoom_processing_defects() -> dict[str, str]:
    """检查放大/缩小处理逻辑中的缺陷。"""
    findings: dict[str, str] = {}

    findings["显示缩放与 OCR 输入解耦"] = (
        "OpenCvImageProcessor._apply_zoom() 在 vision 层做数字缩放，"
        "但 OCR 引擎直接接收原始 ImageFrame，不经过 _apply_zoom()。"
        "rapid_engine.py 第 75 行：img = frame_to_rgb(request.image) "
        "这里 request.image 是原图，不是缩放后的图。"
        "这意味着 '放大' 只影响显示，不影响 OCR 质量——对低视力助视是设计缺陷。"
    )

    findings["缩放插值方法不一致"] = (
        "OpenCvImageProcessor._apply_zoom() 使用 cv2.INTER_LANCZOS4（高质量下采样）。"
        "但 OriginalView._to_pixmap() 中：\n"
        "- scale < 1.0 用 cv2.INTER_AREA\n"
        "- scale >= 1.0 用 cv2.INTER_LINEAR\n"
        "两处缩放逻辑不一致，可能导致显示与处理结果视觉差异。"
    )

    findings["选区坐标整数舍入误差累积"] = (
        "OriginalView.get_selection() 使用 int() 截断：\n"
        "  x = int((self._selection.x - img_x) / total_scale)\n"
        "多次放大-缩小-再放大操作会导致选区坐标漂移。"
        "例如：原图 1000px，zoom=2.0 后选区 200px，映射回源图为 100px；"
        "再次 zoom=4.0，显示选区变为 400px，映射回源图仍为 100px——"
        "但如果涉及多次 freeze/unfreeze，frame_revision 递增但原图分辨率不变，"
        "选区精度受限于整数运算。"
    )

    findings["max_scale 限制可能导致 OCR 输入过小"] = (
        "OriginalView._rendered_scale() 中：\n"
        "  max_scale = sqrt(12_000_000 / (frame.width * frame.height))\n"
        "对于 4K 图片 (3840x2160)，max_scale = sqrt(12M / 8.3M) ≈ 1.2\n"
        "这意味着即使 zoom_factor=8.0，实际渲染缩放也被限制在 1.2x。"
        "但 OCR 引擎处理的是原图（3840x2160），不受此限制。"
    )

    findings["OCR 引擎无超分辨率预处理"] = (
        "对于低分辨率输入（如 640x360 的手机拍照），OCR 引擎直接运行。"
        "没有先放大再 OCR 的逻辑。"
        "建议：在 OCR 前，对低分辨率 ROI 做超分辨率或至少 bicubic 插值放大，"
        "以提升小字识别率。"
    )

    return findings


def test_text_reflow_with_large_font() -> dict[str, str]:
    """检查大字重排在极端字号下的问题。"""
    findings: dict[str, str] = {}

    findings["字号 96px 时单行字符数过少"] = (
        "TextReflow._estimate_char_width() 中 CJK 字符宽度 = font_size。"
        "当 font_size=96，view_width=800 时，每行只能容纳约 8 个汉字。"
        "对于长段落，行数过多，滚动阅读体验差。"
    )

    findings["英文单词被强制截断"] = (
        "TextReflow.reflow() 中，英文按词（word）切分，"
        "但如果单个单词宽度超过 view_width，该单词会被硬塞到当前行，"
        "导致该行超出视窗宽度。应处理超长单词的强制断行。"
    )

    return findings


def run_all_tests() -> dict[str, dict]:
    """运行所有测试并返回结果。"""
    all_results: dict[str, dict] = {}

    print("=" * 70)
    print("OCR 与图像处理逻辑缺陷检查")
    print("=" * 70)

    # 1. 坐标映射测试
    print("\n[1] OriginalView 选区坐标映射测试")
    print("-" * 50)
    mapping_results = test_original_view_selection_mapping()
    for name, result in mapping_results.items():
        status = "PASS" if result["passed"] else "FAIL"
        print(f"  {status}: {name}")
        if not result["passed"]:
            print(f"       actual={result['actual']}, expected={result['expected']}")
    all_results["coordinate_mapping"] = mapping_results

    # 2. OCR ROI 与缩放耦合
    print("\n[2] OCR 引擎 ROI 与显示缩放耦合问题")
    print("-" * 50)
    roi_findings = test_ocr_engine_roi_with_zoom()
    for name, desc in roi_findings.items():
        print(f"  FINDING: {name}")
        for line in desc.split("\n"):
            print(f"    {line}")
    all_results["ocr_roi_zoom"] = roi_findings

    # 3. 粉笔字预处理缺失
    print("\n[3] 粉笔字场景预处理缺失")
    print("-" * 50)
    chalk_findings = test_chalkboard_preprocessing_gap()
    for name, desc in chalk_findings.items():
        print(f"  FINDING: {name}")
        for line in desc.split("\n"):
            print(f"    {line}")
    all_results["chalkboard_preprocessing"] = chalk_findings

    # 4. 放大/缩小缺陷
    print("\n[4] 放大/缩小处理逻辑缺陷")
    print("-" * 50)
    zoom_findings = test_zoom_processing_defects()
    for name, desc in zoom_findings.items():
        print(f"  FINDING: {name}")
        for line in desc.split("\n"):
            print(f"    {line}")
    all_results["zoom_defects"] = zoom_findings

    # 5. 文字重排缺陷
    print("\n[5] 大字重排极端情况")
    print("-" * 50)
    reflow_findings = test_text_reflow_with_large_font()
    for name, desc in reflow_findings.items():
        print(f"  FINDING: {name}")
        for line in desc.split("\n"):
            print(f"    {line}")
    all_results["text_reflow"] = reflow_findings

    print("\n" + "=" * 70)
    print("测试完成")
    print("=" * 70)

    return all_results


if __name__ == "__main__":
    results = run_all_tests()
