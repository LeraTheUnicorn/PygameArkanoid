@echo off
chcp 65001 >nul

echo ========================================
echo ДИАГНОСТИКА И УСТАНОВКА ЗАВИСИМОСТЕЙ
echo ========================================
echo.

echo [ШАГ 1] Поиск виртуального окружения...

REM Проверяем наличие venv в проекте
if exist ".venv\Scripts\python.exe" (
    echo ✅ Найдено venv: .venv\Scripts\python.exe
    setlocal EnableDelayedExpansion
    set "PYTHON_CMD=.venv\Scripts\python.exe"
    goto install_venv
) else if exist "venv\Scripts\python.exe" (
    echo ✅ Найдено venv: venv\Scripts\python.exe  
    setlocal EnableDelayedExpansion
    set "PYTHON_CMD=venv\Scripts\python.exe"
    goto install_venv
) else (
    echo ❌ Виртуальное окружение не найдено!
    echo Использую глобальный Python...
    setlocal EnableDelayedExpansion
    set "PYTHON_CMD=python"
    goto install_global
)

:install_venv
echo.
echo [ШАГ 2] Установка зависимостей в venv...
echo Использую: !PYTHON_CMD!
!PYTHON_CMD! --version
if !ERRORLEVEL! NEQ 0 (
    echo ❌ Ошибка с Python в venv!
    goto error_exit
)

echo.
echo [ШАГ 3] Установка pygame...
!PYTHON_CMD! -m pip install pygame==2.5.2 --no-cache-dir --force-reinstall
if !ERRORLEVEL! NEQ 0 (
    echo ❌ Ошибка установки pygame! Пробую альтернативный способ...
    !PYTHON_CMD! -m pip install pygame --pre --no-cache-dir --force-reinstall
    if !ERRORLEVEL! NEQ 0 (
        echo ❌ Все способы установки pygame не удались!
        goto error_exit
    )
) else (
    echo ✅ pygame успешно установлен!
)

echo.
echo [ШАГ 4] Установка numpy...
!PYTHON_CMD! -m pip install numpy --no-cache-dir --force-reinstall
if !ERRORLEVEL! NEQ 0 (
    echo ❌ Ошибка установки numpy!
    goto error_exit
) else (
    echo ✅ numpy успешно установлен!
)

echo.
echo [ШАГ 5] Проверка установки...
!PYTHON_CMD! -c "import pygame, numpy; print('OK')"
if !ERRORLEVEL! NEQ 0 (
    echo ❌ Библиотеки не работают после установки!
    goto error_exit
)

echo.
echo ========================================
echo ✅ УСТАНОВКА УСПЕШНА В VENV!
echo ========================================
echo.
echo 🎮 Игра готова к запуску!
echo Команда для запуска:
echo !PYTHON_CMD! PyGameBall.py
echo.
echo Или активируйте venv:
echo .venv\Scripts\activate
echo python PyGameBall.py
goto success_exit

:install_global
echo.
echo [ШАГ 2] Установка в глобальном Python...
python --version
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Глобальный Python не найден!
    goto error_exit
)

echo.
echo [ШАГ 3] Установка pygame...
python -m pip install pygame==2.5.2 --no-cache-dir --force-reinstall
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Ошибка установки pygame!
    goto error_exit
) else (
    echo ✅ pygame успешно установлен!
)

echo.
echo [ШАГ 4] Установка numpy...
python -m pip install numpy --no-cache-dir --force-reinstall
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Ошибка установки numpy!
    goto error_exit
) else (
    echo ✅ numpy успешно установлен!
)

echo.
echo [ШАГ 5] Проверка установки...
python -c "import pygame, numpy; print('OK')"
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Библиотеки не работают после установки!
    goto error_exit
)

echo.
echo ========================================
echo ✅ УСТАНОВКА УСПЕШНА!
echo ========================================
echo.
echo 🎮 Игра готова к запуску!
echo Команда для запуска:
echo python PyGameBall.py
goto success_exit

:error_exit
echo.
echo ========================================
echo ❌ УСТАНОВКА НЕ УДАЛАСЬ
echo ========================================
echo.
echo РЕШЕНИЯ:
echo 1. Используйте готовый .exe: Arkanoid_v2.1.5.exe
echo 2. Установите Python 3.11-3.13 (не 3.14)
echo 3. Активируйте venv: .venv\Scripts\activate
echo 4. Запустите: python -m pip install pygame numpy
echo.
echo Попробуйте вручную:
echo python -m pip install pygame==2.5.2 numpy
pause
exit /b 1

:success_exit
echo.
echo 🎯 Поддерживаемые функции:
echo    - Обычная игра
echo    - AI помощник
echo    - Система рекордов
echo    - Настройки сложности
echo.
pause
exit /b 0