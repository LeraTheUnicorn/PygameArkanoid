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
REM По умолчанию используем глобальный Python для упрощения
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

echo [ШАГ 1] Обновление pip...
python -m pip install --upgrade pip --quiet
if !ERRORLEVEL! NEQ 0 (
    echo ⚠️ Предупреждение: не удалось обновить pip, продолжаю...
)

echo.
echo [ШАГ 2] Установка pygame...
python -m pip install pygame==2.5.2 --no-cache-dir --force-reinstall
if !ERRORLEVEL! NEQ 0 (
    echo ❌ Ошибка установки pygame! Пробую альтернативный способ...
    python -m pip install pygame --pre --no-cache-dir --force-reinstall
    if !ERRORLEVEL! NEQ 0 (
        echo ❌ Все способы установки pygame не удались!
        goto error_exit
    )
) else (
    echo ✅ pygame успешно установлен!
)

echo.
echo [ШАГ 3] Установка numpy...
python -m pip install numpy --no-cache-dir --force-reinstall
if !ERRORLEVEL! NEQ 0 (
    echo ❌ Ошибка установки numpy!
    goto error_exit
) else (
    echo ✅ numpy успешно установлен!
)

echo.
echo [ШАГ 4] Установка scikit-learn...
python -m pip install scikit-learn --no-cache-dir --force-reinstall
if !ERRORLEVEL! NEQ 0 (
    echo ❌ Ошибка установки scikit-learn!
    goto error_exit
) else (
    echo ✅ scikit-learn успешно установлен!
)

echo.
echo [ШАГ 5] Проверка установки...
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
echo Команда для запуска:
echo   python PyGameBall.py
echo.
echo Или просто дважды щелкните по PyGameBall.py
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
echo    python -m pip install pygame==2.5.2 numpy scikit-learn
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
