#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Улучшенный скрипт создания иконки для игры Арканоид
Создает более яркую и контрастную иконку для лучшей видимости на ярлыке
"""

import os
import sys

try:
    from PIL import Image, ImageDraw, ImageFont

    def create_improved_arkanoid_icon():
        """Создает улучшенную иконку для игры Арканоид с лучшей видимостью"""
        # Размер иконки (больше для лучшего качества)
        size = (512, 512)
        
        # Создаем новое изображение с ярким фоном
        img = Image.new("RGBA", size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Яркие контрастные цвета для лучшей видимости
        background_color = (20, 20, 60)  # Очень темно-синий, почти черный
        paddle_color = (255, 200, 0)  # Яркий золотой
        ball_color = (255, 255, 255)  # Чисто белый
        brick_colors = [
            (255, 100, 50),   # Яркий оранжево-красный
            (255, 200, 0),    # Золотой
            (100, 255, 100),  # Яркий зеленый
            (100, 200, 255),  # Яркий голубой
            (255, 150, 255),  # Яркий розовый
        ]
        
        # Рисуем фон с градиентом для глубины
        draw.rectangle([0, 0, size[0], size[1]], fill=background_color)
        
        # Добавляем легкий градиент (темнее сверху, светлее снизу)
        for y in range(size[1]):
            alpha = int(30 * (1 - y / size[1]))
            color = (background_color[0] + alpha, background_color[1] + alpha, background_color[2] + alpha)
            draw.line([(0, y), (size[0], y)], fill=color)
        
        # Рисуем кубики в верхней части (более крупные и яркие)
        brick_width = size[0] // 6
        brick_height = size[1] // 8
        start_x = brick_width // 2
        start_y = size[1] // 10
        
        # Рисуем 4 ряда кубиков для лучшей видимости
        for row in range(4):
            for col in range(5):
                x = start_x + col * (brick_width + 8)
                y = start_y + row * (brick_height + 8)
                color = brick_colors[row % len(brick_colors)]
                
                # Рисуем кубик с обводкой для контраста
                draw.rectangle([x, y, x + brick_width, y + brick_height], fill=color, outline=(255, 255, 255), width=2)
                
                # Добавляем блик для объема
                highlight_color = tuple(min(255, c + 50) for c in color)
                draw.rectangle([x + 2, y + 2, x + brick_width - 2, y + brick_height // 2], fill=highlight_color)
        
        # Рисуем платформу внизу (более крупная и яркая)
        paddle_width = int(size[0] * 0.4)  # 40% ширины
        paddle_height = int(size[1] * 0.08)  # 8% высоты
        paddle_x = (size[0] - paddle_width) // 2
        paddle_y = size[1] - paddle_height - int(size[1] * 0.15)
        
        # Рисуем платформу с обводкой и бликом
        draw.rectangle(
            [paddle_x, paddle_y, paddle_x + paddle_width, paddle_y + paddle_height],
            fill=paddle_color,
            outline=(255, 255, 255),
            width=3
        )
        # Блик на платформе
        highlight_y = paddle_y + paddle_height // 3
        draw.rectangle(
            [paddle_x + 5, paddle_y + 2, paddle_x + paddle_width - 5, highlight_y],
            fill=(255, 255, 200)
        )
        
        # Рисуем мяч (более крупный и яркий)
        ball_radius = int(size[1] * 0.04)  # 4% высоты
        ball_x = size[0] // 2
        ball_y = paddle_y - ball_radius - 10
        
        # Тень мяча
        shadow_offset = 3
        draw.ellipse(
            [
                ball_x - ball_radius + shadow_offset,
                ball_y - ball_radius + shadow_offset,
                ball_x + ball_radius + shadow_offset,
                ball_y + ball_radius + shadow_offset,
            ],
            fill=(50, 50, 50, 150)
        )
        
        # Основной мяч
        draw.ellipse(
            [
                ball_x - ball_radius,
                ball_y - ball_radius,
                ball_x + ball_radius,
                ball_y + ball_radius,
            ],
            fill=ball_color,
            outline=(200, 200, 200),
            width=2
        )
        
        # Блик на мяче
        highlight_radius = ball_radius // 3
        draw.ellipse(
            [
                ball_x - highlight_radius,
                ball_y - highlight_radius - 2,
                ball_x - highlight_radius + highlight_radius // 2,
                ball_y - highlight_radius + highlight_radius // 2 - 2,
            ],
            fill=(255, 255, 255, 200)
        )
        
        # Добавляем текст "ARKANOID" (более крупный и контрастный)
        try:
            # Пытаемся использовать системный шрифт
            font_size = int(size[1] * 0.12)  # 12% высоты
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            try:
                font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", font_size)
            except:
                # Если нет шрифта, используем стандартный
                font = ImageFont.load_default()
        
        text = "ARKANOID"
        # Получаем размеры текста
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        text_x = (size[0] - text_width) // 2
        text_y = ball_y - text_height - int(size[1] * 0.08)
        
        # Рисуем тень текста (более заметную)
        shadow_offset_x = 4
        shadow_offset_y = 4
        draw.text(
            (text_x + shadow_offset_x, text_y + shadow_offset_y),
            text,
            fill=(0, 0, 0, 200),
            font=font
        )
        
        # Рисуем основной текст с обводкой
        # Сначала обводка
        for adj in range(-2, 3):
            for adj2 in range(-2, 3):
                if adj != 0 or adj2 != 0:
                    draw.text(
                        (text_x + adj, text_y + adj2),
                        text,
                        fill=(0, 0, 0),
                        font=font
                    )
        
        # Основной текст
        draw.text(
            (text_x, text_y),
            text,
            fill=(255, 255, 0),  # Яркий желтый для контраста
            font=font
        )
        
        return img
    
    # Получаем путь к ресурсам
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    resources_dir = os.path.join(project_root, "resources")
    os.makedirs(resources_dir, exist_ok=True)
    
    # Создаем иконку
    print("Создаю улучшенную иконку для игры Арканоид...")
    icon = create_improved_arkanoid_icon()
    
    # Сохраняем как ICO файл с несколькими размерами для лучшего качества
    icon_path = os.path.join(resources_dir, "icon.ico")
    icon.save(
        icon_path,
        format="ICO",
        sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)],
    )
    print(f"Иконка создана: {icon_path}")
    
    # Также сохраняем как PNG для справки
    png_path = os.path.join(resources_dir, "icon.png")
    icon.save(png_path, format="PNG")
    print(f"PNG версия: {png_path}")
    
    print("\n✅ Иконка успешно создана!")
    print("Новая иконка имеет:")
    print("  - Более яркие и контрастные цвета")
    print("  - Более крупные элементы для лучшей видимости")
    print("  - Улучшенную читаемость текста")
    print("  - Несколько размеров для разных применений")

except ImportError:
    print("❌ Ошибка: PIL (Pillow) не установлен")
    print("Установите: pip install Pillow")
    sys.exit(1)

except Exception as e:
    print(f"❌ Ошибка при создании иконки: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
