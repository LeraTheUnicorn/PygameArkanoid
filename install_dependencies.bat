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
echo [ШАГ 2] Проверка и установка pygame...
python -c "import pygame; print('pygame', pygame.version.ver)" >nul 2>&1
if !ERRORLEVEL! EQU 0 (
    python -c "import pygame; print('✅ pygame уже установлен, версия:', pygame.version.ver)"
) else (
    echo Установка pygame...
    python -m pip install pygame==2.5.2 --no-cache-dir
    if !ERRORLEVEL! NEQ 0 (
        echo ⚠️ Не удалось установить pygame==2.5.2, пробую последнюю версию...
        python -m pip install pygame --no-cache-dir
        if !ERRORLEVEL! NEQ 0 (
            echo ❌ Все способы установки pygame не удались!
            goto error_exit
        )
    )
    echo ✅ pygame успешно установлен!
)

echo.
echo [ШАГ 3] Проверка и установка numpy...
python -c "import numpy; print('numpy', numpy.__version__)" >nul 2>&1
if !ERRORLEVEL! EQU 0 (
    python -c "import numpy; print('✅ numpy уже установлен, версия:', numpy.__version__)"
) else (
    echo Установка numpy...
    python -m pip install numpy --no-cache-dir
    if !ERRORLEVEL! NEQ 0 (
        echo ❌ Ошибка установки numpy!
        goto error_exit
    )
    echo ✅ numpy успешно установлен!
)

echo.
echo [ШАГ 4] Проверка и установка scikit-learn...
python -c "import sklearn; print('scikit-learn', sklearn.__version__)" >nul 2>&1
if !ERRORLEVEL! EQU 0 (
    python -c "import sklearn; print('✅ scikit-learn уже установлен, версия:', sklearn.__version__)"
) else (
    echo Установка scikit-learn...
    python -m pip install scikit-learn --no-cache-dir
    if !ERRORLEVEL! NEQ 0 (
        echo ❌ Ошибка установки scikit-learn!
        goto error_exit
    )
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
