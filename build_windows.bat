@echo off
REM Build script for Windows
REM Usage: build_windows.bat [onedir|onefile]
REM Default: onedir

set BUILD_MODE=%1
if "%BUILD_MODE%"=="" set BUILD_MODE=onedir

echo Building XeusGUI for Windows (%BUILD_MODE% mode)...
echo.

REM Activate virtual environment if it exists
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)

REM Clean previous builds
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

REM Build based on mode
if "%BUILD_MODE%"=="onefile" (
    echo Using onefile mode (single executable)...
    pyinstaller XeusGUI_windows_onefile.spec --clean --noconfirm
) else (
    echo Using onedir mode (folder with executable)...
    pyinstaller XeusGUI_windows.spec --clean --noconfirm
)

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo Build completed successfully!
    echo ========================================
    echo.
    echo Application location: dist\XeusGUI
    echo.
) else (
    echo.
    echo ========================================
    echo Build failed!
    echo ========================================
    exit /b 1
)

