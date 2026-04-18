@echo off
REM Headless-запуск UE 5.7: создать Content/-структуру + 5 стартовых карт +
REM BP_FireflyGameMode, BP_FireflyPlayer. Идемпотентно.
REM
REM Usage: scripts\init_project.bat

setlocal
set "UE_CMD=C:\Program Files\Epic Games\UE_5.7\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
set "UPROJECT=%~dp0..\UnrealProject\FireflyUE5.uproject"
set "SCRIPT=%~dp0..\UnrealProject\Content\Python\init_project.py"

if not exist "%UE_CMD%" (
    echo [!] UnrealEditor-Cmd.exe not found at %UE_CMD%.
    exit /b 1
)

"%UE_CMD%" "%UPROJECT%" ^
    -run=pythonscript ^
    -script="%SCRIPT%" ^
    -unattended -nop4 -nosplash -stdout -FullStdOutLogOutput

endlocal
