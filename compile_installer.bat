@echo off
REM Скрипт компиляции инсталлятора Arkanoid
REM Требуется установленный Inno Setup Compiler

echo =============================================
echo Компиляция инсталлятора Arkanoid v1.6.1
echo =============================================

REM Проверяем наличие Inno Setup
where iscc.exe >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ОШИБКА: Inno Setup Compiler не найден в PATH
    echo Установите Inno Setup с https://jrsoftware.org/isinfo.php
    pause
    exit /b 1
)

echo Найден Inno Setup Compiler
echo.

REM Создаем директорию для инсталлятора
if not exist "installer" mkdir installer

REM Компилируем инсталлятор
echo Компиляция инсталлятора...
iscc create_installer.iss

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✅ Инсталлятор успешно создан!
    echo Файл: installer\Arkanoid_v1.6.1_Setup.exe
    echo.
    echo Готов к распространению!
) else (
    echo.
    echo ❌ Ошибка при компиляции инсталлятора
)

pause