#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Создание яркой иконки для Арканоид - финальная версия"""

import sys
import os

# Настройка вывода
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

try:
    from PIL import Image, ImageDraw, ImageFont
    print("Pillow импортирован успешно")
except ImportError:
    print("ОШИБКА: Pillow не установлен!")
    print("Установите: pip install Pillow")
    sys.exit(1)

# Пути
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
icon_path = os.path.join(project_root, "resources", "icon.ico")
png_path = os.path.join(project_root, "resources", "icon.png")

print(f"Создание иконки...")
print(f"Путь к иконке: {icon_path}")

# Создаем изображение 512x512
size = 512
img = Image.new("RGB", (size, size), (10, 10, 40))
draw = ImageDraw.Draw(img)

# Яркие цвета
paddle = (255, 200, 0)  # Золотой
ball = (255, 255, 255)  # Белый
bricks = [(255, 60, 60), (255, 160, 0), (80, 255, 80), (60, 180, 255)]
white = (255, 255, 255)
yellow = (255, 255, 0)
black = (0, 0, 0)

print("Рисую кубики...")
# Кубики: 4 ряда по 5
bw, bh = 80, 35
sx, sy = 60, 50
for r in range(4):
    for c in range(5):
        x, y = sx + c * (bw + 10), sy + r * (bh + 10)
        draw.rectangle([x, y, x + bw, y + bh], fill=bricks[r % 4], outline=white, width=2)

print("Рисую платформу...")
# Платформа
pw, ph = 200, 45
px, py = (size - pw) // 2, size - ph - 90
draw.rectangle([px, py, px + pw, py + ph], fill=paddle, outline=white, width=4)

print("Рисую мяч...")
# Мяч
br = 20
bx, by = size // 2, py - br - 20
draw.ellipse([bx - br, by - br, bx + br, by + br], fill=ball, outline=(200, 200, 200), width=3)

print("Добавляю текст...")
# Текст
text = "ARKANOID"
fs = 70
try:
    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", fs)
except:
    try:
        font = ImageFont.truetype("arial.ttf", fs)
    except:
        font = ImageFont.load_default()
        print("Использую стандартный шрифт")

bbox = draw.textbbox((0, 0), text, font=font)
tx = (size - (bbox[2] - bbox[0])) // 2
ty = by - 100

# Тень и обводка
draw.text((tx + 5, ty + 5), text, fill=black, font=font)
for dx in [-3, -2, -1, 1, 2, 3]:
    for dy in [-3, -2, -1, 1, 2, 3]:
        draw.text((tx + dx, ty + dy), text, fill=black, font=font)
draw.text((tx, ty), text, fill=yellow, font=font)

print("Сохраняю иконку...")
# Сохраняем
try:
    img.save(icon_path, format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
    print(f"✓ ICO файл создан: {icon_path}")
except Exception as e:
    print(f"Ошибка при сохранении ICO: {e}")

try:
    img.save(png_path, format="PNG")
    print(f"✓ PNG файл создан: {png_path}")
except Exception as e:
    print(f"Ошибка при сохранении PNG: {e}")

# Проверяем размер файла
if os.path.exists(icon_path):
    file_size = os.path.getsize(icon_path)
    print(f"\n✓ Иконка успешно создана!")
    print(f"  Размер файла: {file_size} байт")
    print(f"  Путь: {icon_path}")
else:
    print(f"\n✗ Ошибка: файл не создан!")
    sys.exit(1)
