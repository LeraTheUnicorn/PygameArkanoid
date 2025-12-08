# Простой скрипт создания иконки
import sys
import os

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("ОШИБКА: Pillow не установлен!")
    print("Установите: pip install Pillow")
    sys.exit(1)

# Переходим в папку resources
script_dir = os.path.dirname(os.path.abspath(__file__))
resources_dir = os.path.join(script_dir, 'resources')
os.makedirs(resources_dir, exist_ok=True)
os.chdir(resources_dir)

print("Создание иконки...")

size = 512
img = Image.new('RGB', (size, size), (10, 10, 40))
d = ImageDraw.Draw(img)

# Кубики - яркие цвета
bricks = [(255, 60, 60), (255, 160, 0), (80, 255, 80), (60, 180, 255)]
for r in range(4):
    for c in range(5):
        x, y = 60 + c * 90, 50 + r * 45
        d.rectangle([x, y, x + 80, y + 35], fill=bricks[r % 4], outline=(255, 255, 255), width=2)

# Платформа - золотая
d.rectangle([156, 367, 356, 412], fill=(255, 200, 0), outline=(255, 255, 255), width=4)

# Мяч - белый
d.ellipse([236, 320, 276, 360], fill=(255, 255, 255), outline=(200, 200, 200), width=3)

# Текст - желтый с черной обводкой
try:
    f = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 70)
    d.text((106, 250), 'ARKANOID', fill=(255, 255, 0), font=f, stroke_width=3, stroke_fill=(0, 0, 0))
except:
    # Если шрифт не найден, рисуем без него
    d.text((106, 250), 'ARKANOID', fill=(255, 255, 0))

# Сохраняем
icon_path = os.path.join(resources_dir, 'icon.ico')
png_path = os.path.join(resources_dir, 'icon.png')

img.save('icon.ico', format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
img.save('icon.png')

print(f"Иконка создана: {icon_path}")
print(f"PNG версия: {png_path}")
print("Готово!")
