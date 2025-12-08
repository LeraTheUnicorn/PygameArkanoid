#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Простой скрипт создания яркой иконки для игры Арканоид
"""

import os
import sys

try:
    from PIL import Image, ImageDraw, ImageFont
    
    # Путь к ресурсам
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    resources_dir = os.path.join(project_root, "resources")
    os.makedirs(resources_dir, exist_ok=True)
    
    print("=" * 60)
    print("Создание улучшенной иконки для игры Арканоид")
    print("=" * 60)
    
    # Размер иконки
    size = (512, 512)
    img = Image.new("RGB", size, (10, 10, 40))  # Темно-синий фон
    draw = ImageDraw.Draw(img)
    
    # Яркие контрастные цвета
    paddle_color = (255, 200, 0)  # Яркий золотой
    ball_color = (255, 255, 255)  # Белый
    brick_colors = [
        (255, 80, 80),    # Яркий красный
        (255, 180, 0),    # Оранжевый
        (100, 255, 100),  # Зеленый
        (80, 180, 255),   # Голубой
    ]
    
    # Рисуем кубики (4 ряда, 5 в ряду)
    brick_w = size[0] // 6
    brick_h = size[1] // 10
    start_x = brick_w // 2
    start_y = size[1] // 12
    
    print("Рисую кубики...")
    for row in range(4):
        for col in range(5):
            x = start_x + col * (brick_w + 10)
            y = start_y + row * (brick_h + 10)
            color = brick_colors[row % len(brick_colors)]
            # Кубик с обводкой
            draw.rectangle([x, y, x + brick_w, y + brick_h], fill=color, outline=(255, 255, 255), width=2)
    
    # Рисуем платформу
    print("Рисую платформу...")
    paddle_w = int(size[0] * 0.45)
    paddle_h = int(size[1] * 0.09)
    paddle_x = (size[0] - paddle_w) // 2
    paddle_y = size[1] - paddle_h - int(size[1] * 0.18)
    draw.rectangle([paddle_x, paddle_y, paddle_x + paddle_w, paddle_y + paddle_h], 
                   fill=paddle_color, outline=(255, 255, 255), width=3)
    
    # Рисуем мяч
    print("Рисую мяч...")
    ball_r = int(size[1] * 0.045)
    ball_x = size[0] // 2
    ball_y = paddle_y - ball_r - 15
    draw.ellipse([ball_x - ball_r, ball_y - ball_r, ball_x + ball_r, ball_y + ball_r],
                fill=ball_color, outline=(200, 200, 200), width=2)
    
    # Текст "ARKANOID"
    print("Добавляю текст...")
    try:
        font_size = int(size[1] * 0.13)
        # Пробуем разные пути к шрифту
        font_paths = [
            "arial.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/calibri.ttf",
        ]
        font = None
        for path in font_paths:
            try:
                font = ImageFont.truetype(path, font_size)
                break
            except:
                continue
        if font is None:
            font = ImageFont.load_default()
    except:
        font = ImageFont.load_default()
    
    text = "ARKANOID"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    text_x = (size[0] - text_w) // 2
    text_y = ball_y - text_h - int(size[1] * 0.1)
    
    # Тень текста
    draw.text((text_x + 4, text_y + 4), text, fill=(0, 0, 0), font=font)
    # Обводка текста
    for dx in [-2, -1, 0, 1, 2]:
        for dy in [-2, -1, 0, 1, 2]:
            if dx != 0 or dy != 0:
                draw.text((text_x + dx, text_y + dy), text, fill=(0, 0, 0), font=font)
    # Основной текст
    draw.text((text_x, text_y), text, fill=(255, 255, 0), font=font)
    
    # Сохраняем ICO
    icon_path = os.path.join(resources_dir, "icon.ico")
    print(f"\nСохраняю иконку: {icon_path}")
    img.save(icon_path, format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
    
    # Сохраняем PNG
    png_path = os.path.join(resources_dir, "icon.png")
    img.save(png_path, format="PNG")
    print(f"Сохраняю PNG: {png_path}")
    
    print("\n" + "=" * 60)
    print("✅ Иконка успешно создана!")
    print("=" * 60)
    print(f"Файл: {icon_path}")
    print(f"PNG: {png_path}")
    print("\nНовая иконка имеет:")
    print("  • Яркие контрастные цвета")
    print("  • Крупные элементы для видимости")
    print("  • Четкий текст 'ARKANOID'")
    print("  • Несколько размеров (16x16 до 256x256)")
    
except ImportError as e:
    print("❌ Ошибка: PIL (Pillow) не установлен")
    print("Установите: pip install Pillow")
    sys.exit(1)
except Exception as e:
    print(f"❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
