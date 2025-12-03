@echo off
chcp 65001 >nul
echo ========================================
echo ДИАГНОСТИКА И УСТАНОВКА ЗАВИСИМОСТЕЙ
echo ========================================
echo.

echo [ШАГ 1] Поиск виртуального окружения проекта...
echo.

:: Проверяем наличие venv в проекте
if exist ".venv\Scripts\python.exe" (
    echo ✅ Найдено venv: .venv\Scripts\python.exe
    set VENV_PYTHON=.venv\Scripts\python.exe
    goto use_venv
) else if exist "venv\Scripts\python.exe" (
    echo ✅ Найдено venv: venv\Scripts\python.exe  
    set VENV_PYTHON=venv\Scripts\python.exe
    goto use_venv
) else (
    echo ❌ Виртуальное окружение не найдено!
    echo Использую глобальный Python...
    goto use_global
)

:use_venv
echo.
echo [ШАГ 2] Проверка Python в venv...
echo Использую Python из venv: %VENV_PYTHON%
%VENV_PYTHON% --version
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Python в venv не работает!
    goto use_global
)
echo.

echo [ШАГ 3] Проверка и установка зависимостей в venv...
echo.

:: Обновляем pip
echo Обновляю pip в venv...
%VENV_PYTHON% -m pip install --upgrade pip >nul 2>&1

:: Проверяем pygame
echo Проверяю pygame в venv...
%VENV_PYTHON% -c "import pygame; print('✅ pygame уже установлен:', pygame.version.ver)" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo ✅ pygame уже установлен и работает!
) else (
    echo pygame не установлен - устанавливаю...
    %VENV_PYTHON% -m pip install pygame >nul 2>&1
    if %ERRORLEVEL% EQU 0 (
        echo ✅ pygame установлен!
    ) else (
        echo ❌ Ошибка установки pygame!
        goto failed
    )
)

:: Проверяем numpy  
echo Проверяю numpy в venv...
%VENV_PYTHON% -c "import numpy; print('✅ numpy уже установлен:', numpy.__version__)" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo ✅ numpy уже установлен и работает!
) else (
    echo numpy не установлен - устанавливаю...
    %VENV_PYTHON% -m pip install numpy >nul 2>&1
    if %ERRORLEVEL% EQU 0 (
        echo ✅ numpy установлен!
    ) else (
        echo ❌ Ошибка установки numpy!
        goto failed
    )
)

echo.
echo [ШАГ 4] Финальная проверка установки...

:: Финальная проверка pygame
%VENV_PYTHON% -c "import pygame; print('✅ pygame ФИНАЛЬНО РАБОТАЕТ!', pygame.version.ver)"
if %ERRORLEVEL% NEQ 0 (
    echo ❌ pygame не работает после установки!
    goto failed
)

:: Финальная проверка numpy
%VENV_PYTHON% -c "import numpy; print('✅ numpy ФИНАЛЬНО РАБОТАЕТ!', numpy.__version__)"
if %ERRORLEVEL% NEQ 0 (
    echo ❌ numpy не работает после установки!
    goto failed
)

echo.
echo ========================================
echo ✅ УСТАНОВКА УСПЕШНА В VENV!
echo ========================================
echo.
echo Игра готова к запуску:
echo %VENV_PYTHON% PyGameBall.py
echo.
echo Альтернативные способы:
echo .venv\Scripts\activate
echo python PyGameBall.py
echo.
echo poetry run python PyGameBall.py
goto end

:use_global
echo.
echo [ШАГ 2] Использую глобальный Python...
python --version
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Глобальный Python не найден!
    goto failed
)

:: Проверяем версию
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set VER=%%i
echo Версия: %VER%

if "%VER%"=="3.14" (
    echo 🚨 Python 3.14 несовместим с pygame!
    echo Используйте venv с Python 3.11 или готовый .exe
    goto failed
)

echo.
echo [ШАГ 3] Проверка пакетов в глобальном Python...

:: Проверяем pygame
python -c "import pygame; print('✅ pygame работает:', pygame.version.ver)" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo ✅ pygame установлен в глобальном Python
) else (
    echo pygame не установлен - устанавливаю...
    python -m pip install pygame >nul 2>&1
    if %ERRORLEVEL% NEQ 0 (
        echo ❌ Ошибка установки pygame!
        goto failed
    )
    echo ✅ pygame установлен в глобальный Python
)

:: Проверяем numpy
python -c "import numpy; print('✅ numpy работает:', numpy.__version__)" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo ✅ numpy установлен в глобальном Python
) else (
    echo numpy не установлен - устанавливаю...
    python -m pip install numpy >nul 2>&1
    if %ERRORLEVEL% NEQ 0 (
        echo ❌ Ошибка установки numpy!
        goto failed
    )
    echo ✅ numpy установлен в глобальный Python
)

echo.
echo [ШАГ 4] Финальная проверка...

python -c "import pygame; print('✅ pygame OK!', pygame.version.ver)"
if %ERRORLEVEL% NEQ 0 (
    echo ❌ pygame не работает!
    goto failed
)

python -c "import numpy; print('✅ numpy OK!', numpy.__version__)"
if %ERRORLEVEL% NEQ 0 (
    echo ❌ numpy не работает!
    goto failed
)

echo.
echo ========================================
echo ✅ УСТАНОВКА УСПЕШНА!
echo ========================================
echo.
echo Игра готова к запуску:
echo python PyGameBall.py
goto end

:failed
echo.
echo ========================================
echo ❌ УСТАНОВКА НЕ УДАЛАСЬ
echo ========================================
echo.
echo РЕШЕНИЯ:
echo 1. Используйте готовый .exe: Arkanoid_v2.1.0.exe
echo 2. Установите Python 3.11-3.13 (не 3.14)
echo 3. Активируйте venv: .venv\Scripts\activate

:end
echo.
pause