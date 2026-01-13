"""
测试字体加载和中文显示
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from PIL import Image, ImageFont, ImageDraw
from utils.font_manager import font_manager

# 测试字体列表
print("可用的字体列表:")
fonts = font_manager.get_available_fonts()
for font_name in fonts:
    print(f"  - {font_name}")

# 测试加载字体
test_text = "测试中文显示"
font_size = 48

if fonts:
    font_name = fonts[0]
    print(f"\n测试字体: {font_name}")
    
    # 加载字体
    font = font_manager.load_font(font_name, font_size)
    
    if font:
        print(f"字体加载成功")
        
        # 创建图像
        img = Image.new('RGBA', (800, 200), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # 绘制文字
        draw.text((50, 50), test_text, font=font, fill=(255, 255, 255, 255))
        
        # 保存图像
        output_path = project_root / "debug" / "test_font_output.png"
        output_path.parent.mkdir(exist_ok=True)
        img.save(output_path)
        print(f"测试图像已保存: {output_path}")
        
        # 显示图像
        img.show()
    else:
        print("字体加载失败")
else:
    print("没有可用的字体")