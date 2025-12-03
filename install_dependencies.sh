#!/bin/bash

echo "================================"
echo "Скрипт установки зависимостей для Арканоид"
echo "================================"
echo

# Проверяем, установлен ли Python
echo "Проверяем наличие Python..."
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo "ОШИБКА: Python не найден!"
    echo
    echo "Инструкции по установке Python:"
    echo "Ubuntu/Debian: sudo apt update && sudo apt install python3 python3-pip"
    echo "macOS (с Homebrew): brew install python3"
    echo "macOS (с официального сайта): https://www.python.org/downloads/"
    echo
    echo "После установки перезапустите терминал и запустите этот скрипт снова"
    exit 1
fi

# Определяем команду Python
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
else
    PYTHON_CMD="python"
fi

echo "Python найден!"
$PYTHON_CMD --version
echo

# Обновляем pip
echo "Обновляем pip до последней версии..."
$PYTHON_CMD -m pip install --upgrade pip
if [ $? -ne 0 ]; then
    echo "ПРЕДУПРЕЖДЕНИЕ: Не удалось обновить pip, но продолжаем установку..."
else
    echo "pip обновлен успешно!"
fi
echo

# Проверяем наличие pyproject.toml
if [ ! -f "pyproject.toml" ]; then
    echo "ОШИБКА: Файл pyproject.toml не найден!"
    echo "Убедитесь, что вы запускаете скрипт в папке с игрой."
    exit 1
fi

echo "pyproject.toml найден!"
echo

# ПОПЫТКА 1: Установка через Poetry
echo "ПОПЫТКА 1: Установка через Poetry (рекомендуется)..."
$PYTHON_CMD -m pip install poetry
if [ $? -eq 0 ]; then
    echo "Poetry установлен успешно! Выполняю poetry install..."
    poetry install
    if [ $? -eq 0 ]; then
        echo "Poetry install выполнен успешно!"
        echo
        echo "================================"
        echo "УСТАНОВКА ЧЕРЕЗ POETRY ЗАВЕРШЕНА!"
        echo "================================"
        echo
        echo "Проверяю установленные пакеты..."
        check_packages
    else
        echo "ОШИБКА при выполнении poetry install!"
        echo "Пробую прямую установку..."
        echo
    fi
else
    echo "ОШИБКА при установке Poetry!"
    echo "Пробую прямую установку..."
    echo
fi

# ПОПЫТКА 2: Прямая установка зависимостей
echo "ПОПЫТКА 2: Прямая установка зависимостей..."
$PYTHON_CMD -m pip install pygame numpy pytest
if [ $? -ne 0 ]; then
    echo "ОШИБКА при установке pygame!"
    echo "Пробую с альтернативными параметрами..."
    $PYTHON_CMD -m pip install --only-binary=all pygame numpy pytest
    if [ $? -ne 0 ]; then
        echo "ОШИБКА при альтернативной установке!"
        echo "Пробую с предпочтением бинарных пакетов..."
        $PYTHON_CMD -m pip install --prefer-binary pygame numpy pytest
        if [ $? -ne 0 ]; then
            echo
            echo "================================"
            echo "КРИТИЧЕСКАЯ ОШИБКА УСТАНОВКИ!"
            echo "================================"
            echo
            echo "НИ ОДИН ИЗ СПОСОБОВ УСТАНОВКИ НЕ СРАБОТАЛ!"
            echo
            echo "Возможные причины:"
            echo "- Проблемы совместимости с Python"
            echo "- Отсутствует интернет-соединение"
            echo "- Проблемы с правами доступа"
            echo "- Отсутствие системных библиотек"
            echo
            echo "РЕКОМЕНДУЕМЫЕ РЕШЕНИЯ:"
            echo "РЕШЕНИЕ 1: Используйте совместимую версию Python"
            echo "- Установите Python 3.11 или 3.12"
            echo "- Скачайте с: https://www.python.org/downloads/"
            echo
            echo "РЕШЕНИЕ 2: Установите системные зависимости (Ubuntu/Debian)"
            echo "sudo apt install python3-dev python3-pip"
            echo "sudo apt install libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev"
            echo
            exit 1
        fi
    fi
fi

check_packages
echo
echo "================================"
echo "РЕЗУЛЬТАТ ПРОВЕРКИ"
echo "================================"

# Проверяем каждый пакет отдельно
echo "Проверяю pygame..."
if $PYTHON_CMD -c "import pygame; print('✓ pygame установлен, версия:', pygame.version.ver)" 2>/dev/null; then
    echo "✓ pygame установлен успешно!"
    PYGAME_OK=1
else
    echo "✗ pygame НЕ установлен!"
    PYGAME_OK=0
fi

echo
echo "Проверяю numpy..."
if $PYTHON_CMD -c "import numpy; print('✓ numpy установлен, версия:', numpy.__version__)" 2>/dev/null; then
    echo "✓ numpy установлен успешно!"
    NUMPY_OK=1
else
    echo "✗ numpy НЕ установлен!"
    NUMPY_OK=0
fi

echo
echo "Проверяю pytest..."
if $PYTHON_CMD -c "import pytest; print('✓ pytest установлен, версия:', pytest.__version__)" 2>/dev/null; then
    echo "✓ pytest установлен успешно!"
    PYTEST_OK=1
else
    echo "✗ pytest НЕ установлен!"
    PYTEST_OK=0
fi

echo
if [ $PYGAME_OK -eq 1 ] && [ $NUMPY_OK -eq 1 ]; then
    echo "================================"
    echo "✅ УСТАНОВКА ЗАВЕРШЕНА УСПЕШНО!"
    echo "================================"
    echo
    echo "Теперь можете запустить игру командой:"
    echo "$PYTHON_CMD PyGameBall.py"
    echo
    echo "ИЛИ (если использовали Poetry):"
    echo "poetry run python PyGameBall.py"
    echo
    echo "================================"
    echo "ИГРА ГОТОВА К ЗАПУСКУ! 🎮"
    echo "================================"
else
    echo "================================"
    echo "❌ УСТАНОВКА ЗАВЕРШЕНА С ОШИБКАМИ!"
    echo "================================"
    echo
    echo "Не удалось установить все необходимые пакеты."
    echo "Попробуйте установить системные зависимости:"
    echo "sudo apt install python3-dev libsdl2-dev"
fi

echo
echo "Установка завершена!"