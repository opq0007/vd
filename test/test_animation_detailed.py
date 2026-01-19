"""
详细测试文本动态效果
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
def test_marquee_detailed():
    """详细测试走马灯动效"""
    print("\n=== 详细测试走马灯动效 ===")
    animation = text_animation_factory.create_animation("marquee")
    if not animation:
        print("❌ 无法创建走马灯动效")
        return

    test_img = create_test_image()
    print(f"原始图像: {test_img.shape}")

    # 模拟花字从第 150 帧开始显示
    flower_start_frame = 150
    fps = 30
    speed = 1.0  # 使用新的速度值（相对值）

    print(f"\n花字从第 {flower_start_frame} 帧开始显示")
    print(f"fps={fps}, speed={speed}")

    # 测试从第 150 帧到第 160 帧
    for video_frame in range(150, 161):
        animation_frame_index = video_frame - flower_start_frame

        result = animation.apply_animation(
            test_img,
            animation_frame_index,
            total_frames=300,
            fps=fps,
            speed=speed,
            direction="left"
        )

        # 计算偏移量
        offset = (animation_frame_index / fps) * speed
        shift_x = int(offset) % test_img.shape[1]

        print(f"视频帧 {video_frame}, 动效帧 {animation_frame_index}: offset={offset:.2f}, shift_x={shift_x}")

        # 检查图像是否真的在变化
        if video_frame > 150:
            diff = np.abs(result - test_img).sum()
            print(f"  与原始图像的差异: {diff}")

            # 检查第一行是否真的在变化
            first_row_diff = np.abs(result[0] - test_img[0]).sum()
            print(f"  第一行差异: {first_row_diff}")

    print("✅ 走马灯动效测试完成")

if __name__ == "__main__":
    test_marquee_detailed()
    print("\n=== 所有测试完成 ===")