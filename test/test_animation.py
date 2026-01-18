"""
测试文本动态效果
"""

import numpy as np
from utils.text_animation import text_animation_factory
from utils.logger import Logger
from PIL import Image, ImageDraw, ImageFont
import cv2

# 创建一个简单的测试图像
def create_test_image(width=200, height=50):
    """创建测试图像"""
    img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 绘制文字
    try:
        font = ImageFont.truetype("arial.ttf", 30)
    except:
        font = ImageFont.load_default()

    draw.text((10, 10), "TEST", fill=(255, 0, 0, 255), font=font)

    # 转换为numpy数组
    img_array = np.array(img)
    img_bgra = cv2.cvtColor(img_array, cv2.COLOR_RGBA2BGRA)

    return img_bgra

# 测试走马灯动效
def test_marquee():
    """测试走马灯动效"""
    print("\n=== 测试走马灯动效 ===")
    animation = text_animation_factory.create_animation("marquee")
    if not animation:
        print("❌ 无法创建走马灯动效")
        return

    test_img = create_test_image()
    print(f"原始图像: {test_img.shape}")
    print(f"原始图像前5个像素: {test_img[25, :5, 0]}")

    # 测试10帧
    for i in range(10):
        result = animation.apply_animation(
            test_img,
            frame_index=i,
            total_frames=30,
            fps=30,
            speed=100.0,
            direction="left"
        )
        print(f"帧 {i}: {result.shape}, 非零像素: {np.count_nonzero(result[:, :, :3])}, 前5个像素: {result[25, :5, 0]}")

        # 检查图像是否真的在变化
        if i > 0:
            diff = np.abs(result - test_img).sum()
            print(f"  与原始图像的差异: {diff}")

    print("✅ 走马灯动效测试完成")

# 测试心动动效
def test_heartbeat():
    """测试心动动效"""
    print("\n=== 测试心动动效 ===")
    animation = text_animation_factory.create_animation("heartbeat")
    if not animation:
        print("❌ 无法创建心动动效")
        return

    test_img = create_test_image()
    print(f"原始图像: {test_img.shape}")

    # 测试10帧
    for i in range(10):
        result = animation.apply_animation(
            test_img,
            frame_index=i,
            total_frames=30,
            fps=30,
            scale_min=0.9,
            scale_max=1.1,
            speed=1.0
        )
        print(f"帧 {i}: {result.shape}, 非零像素: {np.count_nonzero(result[:, :, :3])}")

        # 检查图像是否真的在变化
        if i > 0:
            diff = np.abs(result - test_img).sum()
            print(f"  与原始图像的差异: {diff}")

    print("✅ 心动动效测试完成")

if __name__ == "__main__":
    test_marquee()
    test_heartbeat()
    print("\n=== 所有测试完成 ===")