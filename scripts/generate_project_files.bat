@echo off
REM Перегенерирует *.sln и проекты VS для UnrealProject.
REM Запускать после любого изменения Source/ / плагинов.
REM
REM Usage: scripts\generate_project_files.bat

setlocal
set "UBT=C:\Program Files\Epic Games\UE_5.7\Engine\Binaries\DotNET\UnrealBuildTool\UnrealBuildTool.exe"
set "UPROJECT=%~dp0..\UnrealProject\FireflyUE5.uproject"

if not exist "%UBT%" (
    echo [!] UnrealBuildTool.exe not found at %UBT%.
    exit /b 1
)

"%UBT%" -projectfiles -project="%UPROJECT%" -game -rocket -progress

endlocal
