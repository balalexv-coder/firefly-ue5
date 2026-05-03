@echo off
REM Headless WAV - MetaHuman face AnimSequence pipeline.
REM
REM Usage:
REM   scripts\process_face_audio.bat WAV_PATH CHARACTER [LINE_ID] [--overwrite]
REM
REM CHARACTER: Mal | Zoe | Wash | Inara
REM
REM Examples:
REM   scripts\process_face_audio.bat "C:\path\to\mal.wav" Mal
REM   scripts\process_face_audio.bat "C:\path\to\mal.wav" Mal demo_long
REM   scripts\process_face_audio.bat "C:\path\to\mal.wav" Mal demo_long --overwrite
REM
REM Args are passed to the python script via env vars (FIREFLY_*) because
REM UnrealEditor-Cmd.exe on Windows does not forward quoted args reliably
REM through the -script="..." parameter.

setlocal

set "UE_CMD=C:\Program Files\Epic Games\UE_5.7\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
set "UPROJECT=%~dp0..\UnrealProject\FireflyUE5.uproject"
set "SCRIPT=%~dp0..\UnrealProject\Content\Python\firefly_face_pipeline.py"

if not exist "%UE_CMD%" (
    echo [!] UnrealEditor-Cmd.exe not found at %UE_CMD%.
    exit /b 1
)
if "%~1"=="" (
    echo [!] Missing WAV path.
    echo     Usage: scripts\process_face_audio.bat WAV_PATH CHARACTER [LINE_ID] [--overwrite]
    exit /b 1
)
if "%~2"=="" (
    echo [!] Missing character key. Must be one of: Mal Zoe Wash Inara
    exit /b 1
)

set "FIREFLY_WAV=%~f1"
set "FIREFLY_CHAR=%~2"
set "FIREFLY_LINE_ID="
set "FIREFLY_OVERWRITE="

REM Third arg is either LINE_ID or --overwrite.
if /I "%~3"=="--overwrite" (
    set "FIREFLY_OVERWRITE=1"
) else if not "%~3"=="" (
    set "FIREFLY_LINE_ID=%~3"
)
REM Fourth arg, if present, is always --overwrite.
if /I "%~4"=="--overwrite" set "FIREFLY_OVERWRITE=1"

echo [run] FIREFLY_WAV=%FIREFLY_WAV%
echo [run] FIREFLY_CHAR=%FIREFLY_CHAR%
echo [run] FIREFLY_LINE_ID=%FIREFLY_LINE_ID%
echo [run] FIREFLY_OVERWRITE=%FIREFLY_OVERWRITE%

"%UE_CMD%" "%UPROJECT%" ^
    -run=pythonscript ^
    -script="%SCRIPT%" ^
    -unattended -nop4 -nosplash -stdout -FullStdOutLogOutput

endlocal
