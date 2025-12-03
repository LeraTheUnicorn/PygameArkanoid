#!/bin/bash

echo "================================================"
echo "         Запуск игры Arkanoid"
echo "================================================"
echo

# Проверяем наличие Python3
if ! command -v python3 &> /dev/null; then
    echo "❌ ОШИБКА: Python3 не установлен!"
    echo
    echo "📥 Установите Python 3.11-3.13:"
    echo "   Ubuntu/Debian: sudo apt install python3 python3-venv python3-pip"
    echo "   macOS: brew install python3"
    echo "   Или скачайте с https://www.python.org/downloads/"
    echo "⚠️  ВНИМАНИЕ: Python 3.14+ несовместим с игрой!"
    echo
    exit 1
fi

echo "✅ Python3 найден"
python3 --version

# Проверяем версию Python
PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "📋 Версия Python: $PYTHON_VERSION"

# Проверяем совместимость версии Python
echo
echo "🔍 Проверка совместимости версии Python..."

PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" = "3" ]; then
    if [ "$PYTHON_MINOR" -ge 14 ]; then
        echo "❌ ОШИБКА: Python $PYTHON_VERSION несовместим с игрой!"
        echo
        echo "🔧 РЕШЕНИЕ:"
        echo "   1. Скачайте Python 3.11-3.13 с https://www.python.org/downloads/"
        echo "   2. Установите его alongside текущей версии"
        echo "   3. Настройте альтернативы: update-alternatives (Linux)"
        echo
        echo "💡 Для Linux используйте pyenv:"
        echo "   curl https://pyenv.run | bash"
        echo "   pyenv install 3.11.9"
        echo "   pyenv global 3.11.9"
        echo
        exit 1
    fi
fi

echo "✅ Версия Python совместима"
echo

# Проверяем наличие Poetry
if ! command -v poetry &> /dev/null; then
    echo "📦 Устанавливаем Poetry..."
    python3 -m pip install poetry
    if [ $? -ne 0 ]; then
        echo "❌ Ошибка установки Poetry"
        exit 1
    fi
    echo "✅ Poetry установлен"
else
    echo "✅ Poetry найден"
fi

# Устанавливаем зависимости
echo
echo "📦 Устанавливаем зависимости проекта..."
python3 -m poetry install
if [ $? -ne 0 ]; then
    echo "❌ Ошибка установки зависимостей"
    echo
    echo "🔧 Попробуйте альтернативный способ:"
    echo "   1. Создайте новое окружение: python3 -m venv venv"
    echo "   2. Активируйте: source venv/bin/activate"
    echo "   3. Установите: pip install pygame numpy"
    exit 1
fi

echo "✅ Зависимости установлены"
echo

# Запускаем игру
echo "🎮 Запускаем игру..."
echo
python3 -m poetry run python3 PyGameBall.py

echo
echo "================================================"
echo "         Игра завершена"
echo "================================================"