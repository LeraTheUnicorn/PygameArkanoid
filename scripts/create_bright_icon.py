#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Создание яркой и контрастной иконки для игры Арканоид
"""

import os
import sys

# Настройка вывода для Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

try:
    from PIL import Image, ImageDraw, ImageFont
    
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    resources_dir = os.path.join(project_root, "resources")
    os.makedirs(resources_dir, exist_ok=True)
    
    print("Создание яркой иконки для игры Арканоид...")
    
    # Большой размер для качества
    size = (512, 512)
    img = Image.new("RGB", size, (15, 15, 50))  # Темно-синий фон
    draw = ImageDraw.Draw(img)
    
    # Яркие цвета
    colors = {
        'paddle': (255, 200, 0),      # Золотой
        'ball': (255, 255, 255),      # Белый
        'bricks': [
            (255, 60, 60),   # Красный
            (255, 160, 0),   # Оранжевый
            (80, 255, 80),   # Зеленый
            (60, 180, 255),  # Голубой
        ],
        'text': (255, 255, 0),        # Желтый
        'outline': (255, 255, 255),   # Белый
    }
    
    # Кубики - 4 ряда по 5 штук
    brick_w, brick_h = 80, 35
    start_x, start_y = 60, 50
    spacing = 10
    
    for row in range(4):
        for col in range(5):
            x = start_x + col * (brick_w + spacing)
            y = start_y + row * (brick_h + spacing)
            color = colors['bricks'][row % len(colors['bricks'])]
            # Кубик с белой обводкой
            draw.rectangle([x, y, x + brick_w, y + brick_h], 
                         fill=color, outline=colors['outline'], width=2)
    
    # Платформа - крупная и яркая
    paddle_w, paddle_h = 200, 45
    paddle_x = (size[0] - paddle_w) // 2
    paddle_y = size[1] - paddle_h - 90
    draw.rectangle([paddle_x, paddle_y, paddle_x + paddle_w, paddle_y + paddle_h],
                   fill=colors['paddle'], outline=colors['outline'], width=4)
    
    # Мяч - белый с обводкой
    ball_r = 20
    ball_x = size[0] // 2
    ball_y = paddle_y - ball_r - 20
    draw.ellipse([ball_x - ball_r, ball_y - ball_r, ball_x + ball_r, ball_y + ball_r],
                fill=colors['ball'], outline=(200, 200, 200), width=3)
    
    # Текст "ARKANOID" - крупный и контрастный
    text = "ARKANOID"
    font_size = 70
    font = None
    
    # Пробуем найти шрифт
    font_paths = [
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibri.ttf",
        "arial.ttf",
    ]
    
    for path in font_paths:
        try:
            font = ImageFont.truetype(path, font_size)
            break
        except:
            continue
    
    if font is None:
        font = ImageFont.load_default()
    
    # Позиция текста
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_x = (size[0] - text_w) // 2
    text_y = ball_y - 100
    
    # Тень текста
    draw.text((text_x + 5, text_y + 5), text, fill=(0, 0, 0), font=font)
    # Обводка текста (черная)
    for dx in range(-3, 4):
        for dy in range(-3, 4):
            if dx != 0 or dy != 0:
                draw.text((text_x + dx, text_y + dy), text, fill=(0, 0, 0), font=font)
    # Основной текст (желтый)
    draw.text((text_x, text_y), text, fill=colors['text'], font=font)
    
    # Сохраняем ICO с несколькими размерами
    icon_path = os.path.join(resources_dir, "icon.ico")
    print(f"Сохранение: {icon_path}")
    img.save(icon_path, format="ICO", 
             sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
    
    # PNG для просмотра
    png_path = os.path.join(resources_dir, "icon.png")
    img.save(png_path, format="PNG")
    print(f"PNG версия: {png_path}")
    
    print("\nГотово! Новая иконка создана.")
    print("Особенности:")
    print("  - Яркие контрастные цвета")
    print("  - Крупные элементы")
    print("  - Четкий текст")
    print("  - Множество размеров для разных применений")
    
except ImportError:
    print("ОШИБКА: Установите Pillow: pip install Pillow")
    sys.exit(1)
except Exception as e:
    print(f"ОШИБКА: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
