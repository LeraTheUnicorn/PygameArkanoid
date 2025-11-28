#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Скрипт создания иконки для игры Арканоид
Использует PIL для создания простой иконки
"""

try:
    from PIL import Image, ImageDraw, ImageFont
    
    def create_arkanoid_icon():
        """Создает иконку для игры Арканоид"""
        # Размер иконки
        size = (256, 256)
        
        # Создаем новое изображение с прозрачным фоном
        img = Image.new('RGBA', size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Цвета
        background_color = (25, 25, 112)  # Темно-синий
        paddle_color = (255, 215, 0)      # Золотой
        ball_color = (255, 255, 255)      # Белый
        brick_colors = [
            (255, 69, 0),   # Оранжевый
            (255, 140, 0),  # Темно-оранжевый
            (50, 205, 50),  # Лайм
            (30, 144, 255), # Синий
            (138, 43, 226)  # Сине-фиолетовый
        ]
        
        # Рисуем фон
        draw.rectangle([0, 0, size[0], size[1]], fill=background_color)
        
        # Рисуем платформу внизу
        paddle_width = size[0] // 3
        paddle_height = 20
        paddle_x = (size[0] - paddle_width) // 2
        paddle_y = size[1] - paddle_height - 30
        draw.rectangle([paddle_x, paddle_y, paddle_x + paddle_width, paddle_y + paddle_height], 
                      fill=paddle_color)
        
        # Рисуем мяч
        ball_radius = 12
        ball_x = size[0] // 2
        ball_y = size[1] - paddle_height - 60
        draw.ellipse([ball_x - ball_radius, ball_y - ball_radius, 
                     ball_x + ball_radius, ball_y + ball_radius], fill=ball_color)
        
        # Рисуем кубики в верхней части
        brick_width = size[0] // 8
        brick_height = 15
        start_x = brick_width // 2
        start_y = 40
        
        for row in range(3):
            for col in range(6):
                x = start_x + col * (brick_width + 5)
                y = start_y + row * (brick_height + 5)
                color = brick_colors[row % len(brick_colors)]
                draw.rectangle([x, y, x + brick_width, y + brick_height], fill=color)
        
        # Добавляем текст
        try:
            # Пытаемся использовать системный шрифт
            font = ImageFont.truetype("arial.ttf", 24)
        except:
            # Если нет шрифта, используем стандартный
            font = ImageFont.load_default()
        
        # Текст "ARKANOID" - размещаем выше мячика
        text = "ARKANOID"
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        text_x = (size[0] - text_width) // 2
        text_y = size[1] - 120  # Поднимаем выше, чтобы не перекрывался с мячиком
        
        # Рисуем тень текста
        draw.text((text_x + 2, text_y + 2), text, fill=(0, 0, 0), font=font)
        # Рисуем основной текст
        draw.text((text_x, text_y), text, fill=(255, 255, 255), font=font)
        
        return img
    
    # Создаем иконку
    print("Sozdayu ikonu dlya igry Arkanoid...")
    icon = create_arkanoid_icon()
    
    # Сохраняем как ICO файл
    icon.save('icon.ico', format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
    print("Ikonka sozdana: icon.ico")
    
    # Также сохраняем как PNG для справки
    icon.save('icon.png', format='PNG')
    print("PNG versiya: icon.png")
    
except ImportError:
    print("PIL (Pillow) ne ustanovlen")
    print("Ustanovite: pip install Pillow")
    print("Sozdavayu zaglušku dlya ikony...")
    
    # Создаем пустой файл как заглушку
    with open('icon.ico', 'w') as f:
        f.write("# Ikonka dolžna byt' sozdana s pomoš'ju PIL")
    print("Sozdana zagluška icon.ico")
    
except Exception as e:
    print(f"Ošibka pri sozdanii ikony: {e}")

print("\nДля создания инсталлятора:")
print("1. Установите Inno Setup с https://jrsoftware.org/isinfo.php")
print("2. Запустите: compile_installer.bat")