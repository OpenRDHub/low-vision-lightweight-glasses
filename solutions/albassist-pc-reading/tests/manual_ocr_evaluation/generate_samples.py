"""生成 OCR 测试样本图片：模拟黑板粉笔字、课本印刷字、不同分辨率。"""

from __future__ import annotations

import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


# 测试文本：中英文混合，模拟课堂板书
CHALKBOARD_TEXTS = [
    "一元二次方程 ax² + bx + c = 0",
    "求根公式 x = (-b ± √(b²-4ac)) / 2a",
    "判别式 Δ = b² - 4ac",
    "当 Δ > 0 时，方程有两个不相等的实数根",
    "当 Δ = 0 时，方程有两个相等的实数根",
    "当 Δ < 0 时，方程没有实数根",
]

PRINTED_TEXTS = [
    "白化病是一种常染色体隐性遗传病，患者体内缺乏酪氨酸酶，",
    "导致黑色素合成障碍，表现为皮肤、毛发和眼睛色素缺乏。",
    "白化病患者视力低下，常伴有眼球震颤、畏光等症状。",
    "由于视网膜缺乏色素，患者对强光敏感，需要佩戴遮阳眼镜。",
]


def _add_chalk_texture(draw: ImageDraw.ImageDraw, width: int, height: int) -> None:
    """添加粉笔飞粉效果。"""
    for _ in range(width * height // 800):
        x = random.randint(0, width - 1)
        y = random.randint(0, height - 1)
        alpha = random.randint(20, 60)
        size = random.randint(1, 3)
        draw.ellipse([x, y, x + size, y + size], fill=(200, 200, 200, alpha))


def _add_board_texture(draw: ImageDraw.ImageDraw, width: int, height: int) -> None:
    """添加黑板纹理。"""
    for _ in range(width * height // 2000):
        x = random.randint(0, width - 1)
        y = random.randint(0, height - 1)
        gray = random.randint(20, 50)
        draw.point((x, y), fill=(gray, gray + 5, gray + 10))


def generate_chalkboard(
    size: tuple[int, int] = (1280, 720),
    font_size: int = 48,
    output_path: Path | None = None,
) -> Image.Image:
    """生成模拟黑板粉笔字图片。

    Args:
        size: 图片尺寸 (width, height)
        font_size: 字号
        output_path: 保存路径（可选）

    Returns:
        生成的图片
    """
    width, height = size
    img = Image.new("RGB", size, (30, 35, 40))  # 深绿色黑板
    draw = ImageDraw.Draw(img)

    _add_board_texture(draw, width, height)

    # 尝试加载字体
    try:
        font = ImageFont.truetype("simhei.ttf", font_size)
    except OSError:
        try:
            font = ImageFont.truetype("msyh.ttc", font_size)
        except OSError:
            font = ImageFont.load_default()

    y_offset = 60
    line_height = int(font_size * 1.6)

    for text in CHALKBOARD_TEXTS:
        # 粉笔字效果：白色带轻微模糊
        x = 60
        # 主文字
        draw.text((x, y_offset), text, fill=(245, 245, 245), font=font)
        # 粉笔边缘轻微扩散（模拟粗糙感）
        for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            draw.text(
                (x + dx, y_offset + dy),
                text,
                fill=(220, 220, 220),
                font=font,
            )
        y_offset += line_height

    _add_chalk_texture(draw, width, height)

    if output_path:
        img.save(output_path)
        print(f"已保存: {output_path}")

    return img


def generate_printed_page(
    size: tuple[int, int] = (1280, 720),
    font_size: int = 32,
    output_path: Path | None = None,
) -> Image.Image:
    """生成模拟课本印刷字图片。

    Args:
        size: 图片尺寸 (width, height)
        font_size: 字号
        output_path: 保存路径（可选）

    Returns:
        生成的图片
    """
    width, height = size
    img = Image.new("RGB", size, (255, 255, 255))  # 白纸
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("simhei.ttf", font_size)
    except OSError:
        try:
            font = ImageFont.truetype("msyh.ttc", font_size)
        except OSError:
            font = ImageFont.load_default()

    y_offset = 60
    line_height = int(font_size * 1.8)

    for text in PRINTED_TEXTS:
        draw.text((60, y_offset), text, fill=(30, 30, 30), font=font)
        y_offset += line_height

    if output_path:
        img.save(output_path)
        print(f"已保存: {output_path}")

    return img


def generate_low_res_chalkboard(
    size: tuple[int, int] = (640, 360),
    output_path: Path | None = None,
) -> Image.Image:
    """生成低分辨率黑板图片（模拟远距离拍摄）。"""
    img = generate_chalkboard(size=size, font_size=24, output_path=None)
    if output_path:
        img.save(output_path)
        print(f"已保存: {output_path}")
    return img


def generate_inverted_chalkboard(
    size: tuple[int, int] = (1280, 720),
    output_path: Path | None = None,
) -> Image.Image:
    """生成已反色的黑板图片（白底黑字，更适合 OCR）。"""
    img = generate_chalkboard(size=size, font_size=48, output_path=None)
    # 反色：黑底白字 → 白底黑字
    inverted = Image.eval(img, lambda x: 255 - x)
    if output_path:
        inverted.save(output_path)
        print(f"已保存: {output_path}")
    return inverted


def generate_scaled_variants(
    base_path: Path,
    output_dir: Path,
) -> list[Path]:
    """生成同一图片的多种缩放变体。

    Returns:
        生成的文件路径列表
    """
    img = Image.open(base_path)
    paths: list[Path] = []

    scales = [0.25, 0.5, 1.0, 2.0, 4.0]
    for scale in scales:
        new_size = (int(img.width * scale), int(img.height * scale))
        scaled = img.resize(new_size, Image.LANCZOS if scale > 1.0 else Image.Resampling.LANCZOS)
        path = output_dir / f"{base_path.stem}_scale_{scale:.2f}.png"
        scaled.save(path)
        paths.append(path)
        print(f"已保存: {path} ({new_size[0]}x{new_size[1]})")

    return paths


if __name__ == "__main__":
    output_dir = Path(__file__).parent / "test_samples"
    output_dir.mkdir(exist_ok=True)

    print("=" * 60)
    print("生成 OCR 测试样本")
    print("=" * 60)

    # 1. 高清黑板粉笔字
    generate_chalkboard(
        size=(1280, 720),
        font_size=48,
        output_path=output_dir / "chalkboard_hd.png",
    )

    # 2. 低分辨率黑板（模拟远距离拍摄）
    generate_low_res_chalkboard(
        size=(640, 360),
        output_path=output_dir / "chalkboard_lowres.png",
    )

    # 3. 课本印刷字
    generate_printed_page(
        size=(1280, 720),
        font_size=32,
        output_path=output_dir / "printed_page.png",
    )

    # 4. 反色黑板（白底黑字）
    generate_inverted_chalkboard(
        size=(1280, 720),
        output_path=output_dir / "chalkboard_inverted.png",
    )

    # 5. 缩放变体
    print("\n生成缩放变体...")
    generate_scaled_variants(
        output_dir / "chalkboard_hd.png",
        output_dir,
    )

    print("\n" + "=" * 60)
    print("测试样本生成完成")
    print("=" * 60)
