@echo off
echo ================================================
echo         Запуск игры Arkanoid
echo ================================================
echo.

REM Проверяем наличие Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ ОШИБКА: Python не установлен!
    echo.
    echo 📥 Установите Python 3.11-3.13 с https://www.python.org/downloads/
    echo ⚠️  ВНИМАНИЕ: Python 3.14+ несовместим с игрой!
    echo.
    pause
    exit /b 1
)

echo ✅ Python найден
python --version

REM Проверяем версию Python
for /f "tokens=2" %%a in ('python --version 2^>^&1') do set PYTHON_VERSION=%%a
echo 📋 Версия Python: %PYTHON_VERSION%

REM Проверяем совместимость версии Python
echo.
echo 🔍 Проверка совместимости версии Python...

for /f "tokens=1,2 delims=." %%a in ("%PYTHON_VERSION%") do (
    set MAJOR=%%a
    set MINOR=%%b
)

if %MAJOR%==3 (
    if %MINOR% GEQ 14 (
        echo ❌ ОШИБКА: Python %PYTHON_VERSION% несовместим с игрой!
        echo.
        echo 🔧 РЕШЕНИЕ:
        echo    1. Скачайте Python 3.11-3.13 с https://www.python.org/downloads/
        echo    2. Установите его alongside текущей версии
        echo    3. При установке поставьте галочку "Add Python to PATH"
        echo.
        echo 💡 После установки Python 3.11+ перезапустите этот файл
        echo.
        pause
        exit /b 1
    )
)

echo ✅ Версия Python совместима
echo.

REM Проверяем наличие Poetry
poetry --version >nul 2>&1
if errorlevel 1 (
    echo 📦 Устанавливаем Poetry...
    python -m pip install poetry
    if errorlevel 1 (
        echo ❌ Ошибка установки Poetry
        pause
        exit /b 1
    )
    echo ✅ Poetry установлен
) else (
    echo ✅ Poetry найден
)

REM Устанавливаем зависимости
echo.
echo 📦 Устанавливаем зависимости проекта...
python -m poetry install
if errorlevel 1 (
    echo ❌ Ошибка установки зависимостей
    echo.
    echo 🔧 Попробуйте альтернативный способ:
    echo    1. Удалите venv папку (если есть)
    echo    2. Создайте новое окружение: python -m venv venv
    echo    3. Активируйте: venv\Scripts\activate
    echo    4. Установите: pip install pygame numpy
    pause
    exit /b 1
)

echo ✅ Зависимости установлены
echo.

REM Запускаем игру
echo 🎮 Запускаем игру...
echo.
python -m poetry run python PyGameBall.py

echo.
echo ================================================
echo         Игра завершена
echo ================================================
pause