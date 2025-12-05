@echo off
chcp 65001 >nul
cls

echo ========================================
echo   Установка игры Арканоид
echo ========================================
echo.

:: Проверяем наличие исполняемого файла
if not exist "Arkanoid.exe" (
    echo [ОШИБКА] Файл Arkanoid.exe не найден!
    echo Убедитесь, что этот скрипт находится в той же папке, что и Arkanoid.exe
    pause
    exit /b 1
)

:: Определяем папку установки
set "INSTALL_DIR=%PROGRAMFILES%\Arkanoid"
if exist "%USERPROFILE%\Desktop\Arkanoid.exe" (
    echo Обнаружена установленная версия на рабочем столе
    set "INSTALL_DIR=%USERPROFILE%\Desktop\Arkanoid"
)

echo Установка в: %INSTALL_DIR%
echo.

:: Создаем папку установки
if exist "%INSTALL_DIR%" (
    echo [ПРЕДУПРЕЖДЕНИЕ] Папка %INSTALL_DIR% уже существует
    choice /m "Перезаписать существующую установку"
    if errorlevel 2 goto :cancel
    rmdir /s /q "%INSTALL_DIR%"
)

echo [1/4] Создание папки установки...
mkdir "%INSTALL_DIR%"
if errorlevel 1 (
    echo [ОШИБКА] Не удалось создать папку установки
    pause
    exit /b 1
)

:: Копируем файлы игры
echo [2/4] Копирование файлов игры...
copy "Arkanoid.exe" "%INSTALL_DIR%\" >nul
if errorlevel 1 (
    echo [ОШИБКА] Не удалось скопировать Arkanoid.exe
    pause
    exit /b 1
)

:: Копируем папки resources и ai если они существуют
if exist "resources" (
    xcopy "resources" "%INSTALL_DIR%\resources\" /E /I /Y >nul
)

if exist "ai" (
    xcopy "ai" "%INSTALL_DIR%\ai\" /E /I /Y >nul
)

if exist "src" (
    xcopy "src" "%INSTALL_DIR%\src\" /E /I /Y >nul
)

:: Копируем дополнительные файлы
for %%f in (requirements.txt README.MD) do (
    if exist "%%f" (
        copy "%%f" "%INSTALL_DIR%\" >nul
    )
)

echo [3/4] Создание ярлыков...

:: Создаем ярлык на рабочем столе
set "DESKTOP=%USERPROFILE%\Desktop"
powershell -Command "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%DESKTOP%\Arkanoid Game.lnk'); $Shortcut.TargetPath = '%INSTALL_DIR%\Arkanoid.exe'; $Shortcut.WorkingDirectory = '%INSTALL_DIR%'; $Shortcut.Description = 'Игра Арканоид'; $Shortcut.Save()" >nul 2>&1

:: Создаем ярлык в меню Пуск
set "STARTMENU=%APPDATA%\Microsoft\Windows\Start Menu\Programs"
powershell -Command "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%STARTMENU%\Arkanoid Game.lnk'); $Shortcut.TargetPath = '%INSTALL_DIR%\Arkanoid.exe'; $Shortcut.WorkingDirectory = '%INSTALL_DIR%'; $Shortcut.Description = 'Игра Арканоид'; $Shortcut.Save()" >nul 2>&1

echo [4/4] Завершение установки...

echo.
echo ========================================
echo   УСТАНОВКА ЗАВЕРШЕНА УСПЕШНО!
echo ========================================
echo.
echo Игра установлена в: %INSTALL_DIR%
echo.
echo Созданы ярлыки:
echo - На рабочем столе
echo - В меню Пуск
echo.
choice /m "Запустить игру сейчас"
if not errorlevel 2 (
    start "" "%INSTALL_DIR%\Arkanoid.exe"
)

:cancel
echo.
echo Нажмите любую клавишу для выхода...
pause >nul