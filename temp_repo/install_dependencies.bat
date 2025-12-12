@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul

REM Переходим в директорию, где находится скрипт
cd /d "%~dp0"

echo ========================================
echo УСТАНОВКА ЗАВИСИМОСТЕЙ ДЛЯ ИГРЫ АРКАНОИД
echo ========================================
echo.

REM Определяем, какой Python использовать
set "PYTHON_CMD=python"
set "INSTALL_LOCATION=глобальный Python"

REM Проверяем наличие глобального Python
python --version >nul 2>&1
if !ERRORLEVEL! NEQ 0 (
    echo ❌ Python не найден! Установите Python 3.11-3.13
    echo Убедитесь, что Python добавлен в PATH
    pause
    exit /b 1
)

echo Используется: !PYTHON_CMD!
python --version
echo.
echo Установка в: !INSTALL_LOCATION!
echo.

echo [ШАГ 1] Проверка и установка Poetry...
python -m poetry --version >nul 2>&1
if !ERRORLEVEL! EQU 0 (
    echo ✅ Poetry уже установлен
) else (
    echo Установка Poetry...
    python -m pip install poetry --quiet
    if !ERRORLEVEL! NEQ 0 (
        echo ❌ Ошибка установки Poetry!
        goto error_exit
    )
    echo ✅ Poetry успешно установлен!
)

echo.
echo [ШАГ 2] Установка зависимостей с помощью Poetry...
python -m poetry install
if !ERRORLEVEL! NEQ 0 (
    echo ❌ Ошибка установки зависимостей!
    goto error_exit
)

echo.
echo [ШАГ 3] Проверка установки...
python -c "import pygame, numpy, sklearn; print('✅ Все зависимости работают!')"
if !ERRORLEVEL! NEQ 0 (
    echo ❌ Библиотеки не работают после установки!
    goto error_exit
)

echo.
echo ========================================
echo ✅ УСТАНОВКА УСПЕШНА!
echo ========================================
echo.
echo 🎮 Игра готова к запуску!
echo.
echo Команда для запуска из корня проекта:
echo   python src\game\PyGameBall.py
echo.
echo Или используйте полный путь (работает из любой папки):
echo   python "%~dp0src\game\PyGameBall.py"
echo.
goto success_exit

:error_exit
echo.
echo ========================================
echo ❌ УСТАНОВКА НЕ УДАЛАСЬ
echo ========================================
echo.
echo РЕШЕНИЯ:
echo 1. Убедитесь, что Python 3.11-3.13 установлен
echo 2. Проверьте, что Python добавлен в PATH
echo 3. Запустите скрипт от имени администратора
echo 4. Попробуйте вручную:
echo    python -m pip install poetry
echo    python -m poetry install
echo.
pause
exit /b 1

:success_exit
echo 🎯 Поддерживаемые функции:
echo    - Обычная игра
echo    - AI помощник
echo    - Система рекордов
echo    - Настройки сложности
echo.
pause
exit /b 0
