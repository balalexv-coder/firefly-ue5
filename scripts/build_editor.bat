@echo off
REM Собирает модуль FireflyUE5Editor под Win64 (Development).
REM Требует установленный UE 5.7 в C:\Program Files\Epic Games\UE_5.7\.
REM
REM Usage: scripts\build_editor.bat

setlocal
set "UE_ROOT=C:\Program Files\Epic Games\UE_5.7"
set "UPROJECT=%~dp0..\UnrealProject\FireflyUE5.uproject"

if not exist "%UE_ROOT%\Engine\Build\BatchFiles\Build.bat" (
    echo [!] UE 5.7 not found at %UE_ROOT%.
    echo     Install via Epic Games Launcher or edit UE_ROOT in this script.
    exit /b 1
)

"%UE_ROOT%\Engine\Build\BatchFiles\Build.bat" FireflyUE5Editor Win64 Development -Project="%UPROJECT%" -WaitMutex

endlocal
