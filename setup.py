#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Скрипт сборки исполняемого файла игры Арканоид с помощью py2exe
"""

import os
import sys
from py2exe import setup
import pygame

# Получаем версию из основного файла игры
def get_version():
    """Извлекает версию из файла PyGameBall.py"""
    try:
        with open('PyGameBall.py', 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith('VERSION ='):
                    return line.split('"')[1]
    except:
        return "1.6.1"  # резервная версия
    return "1.6.1"

# Данные для приложения
app_name = "Arkanoid"
version = get_version()
exe_name = f"Arkanoid_v{version}.exe"

# Настройки сборки
setup(
    name=app_name,
    version=version,
    description="Игра Арканоид",
    author="Developer",
    author_email="dadbarn@gmail.com",
    
    # Основной скрипт
    scripts=[('PyGameBall.py', 'PyGameBall.py')],
    
    # Опции для исполняемого файла
    options={
        'py2exe': {
            'optimize': 2,
            'includes': [
                'pygame',
                'numpy',
                'highscores',
                'pygame.sndarray',
                'pygame.mixer',
            ],
            'excludes': [
                'tkinter',
                'matplotlib',
                'scipy',
                'PIL',
                'IPython',
                'jupyter',
                'notebook',
                'pytest',
                'unittest',
                'test',
                'tests',
                'docs',
                'changelog.md',
                'README.md',
                'pyproject.toml',
            ],
            'dll_excludes': [
                'MSVCP100.dll',
                'MSVCP140.dll',
                'VCRUNTIME140.dll',
                'api-ms-win-crt-runtime-l1-1-0.dll',
            ],
            'bundle_files': 1,  # Создать единый exe файл
            'compressed': True,
            'unicode': False,
        }
    },
    
    # Данные для включения в сборку
    data_files=[
        # Звуковые файлы
        ('sounds', ['sounds/Night_Prowler.ogg']),
        # Изображения
        ('images', ['images/img.png']),
    ],
    
    # Метаданные приложения
    appname=exe_name,
    
    # Консольное приложение (не windowed)
    console=[{'script': 'PyGameBall.py'}],
    
    # Версия Windows
    windows=[{
        'script': 'PyGameBall.py',
        'icon_resources': [],
        'uac_info': 'requireAdministrator',
    }],
    
    # Расположение выходных файлов
    dist_dir='dist',
)