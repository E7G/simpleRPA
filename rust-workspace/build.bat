@echo off
setlocal

set "WORKSPACE=%~dp0"
if "%WORKSPACE:~-1%"=="\" set "WORKSPACE=%WORKSPACE:~0,-1%"
set "GENERATOR=%CMAKE_GENERATOR%"
if not defined GENERATOR set "GENERATOR=Visual Studio 18 2026"
set "BUILD_DIR=%CMAKE_BUILD_DIR%"
if not defined BUILD_DIR set "BUILD_DIR=%WORKSPACE%\build-vs2026"
set "QFLUENT_DIR=%WORKSPACE%\gui\qfluentkit"

echo ========================================
echo simpleRPA Build Script (Rust + C++)
echo ========================================

echo.
echo [1/3] Building Rust core library...
pushd "%WORKSPACE%"
cargo build --release
if errorlevel 1 (
    echo ERROR: Rust build failed!
    popd
    exit /b 1
)

echo.
echo [2/3] Checking QFluentKit dependency...
if not exist "%QFLUENT_DIR%\QFluent" (
    echo Cloning QFluentKit...
    git clone https://github.com/toddming/QFluentKit.git "%QFLUENT_DIR%"
    if errorlevel 1 (
        echo ERROR: QFluentKit clone failed!
        popd
        exit /b 1
    )
)

echo.
echo [3/3] Building C++ GUI with CMake...
if not exist "%BUILD_DIR%" mkdir "%BUILD_DIR%"

echo Using CMake generator: %GENERATOR%
echo %GENERATOR% | findstr /I /B /C:"Visual Studio" >nul
if errorlevel 1 (
    cmake -S "%WORKSPACE%" -B "%BUILD_DIR%" -G "%GENERATOR%" -DCMAKE_BUILD_TYPE=Release
) else (
    cmake -S "%WORKSPACE%" -B "%BUILD_DIR%" -G "%GENERATOR%" -A x64 -DCMAKE_BUILD_TYPE=Release
)
if errorlevel 1 (
    echo ERROR: CMake configure failed!
    popd
    exit /b 1
)
cmake --build "%BUILD_DIR%" --config Release
if errorlevel 1 (
    echo ERROR: CMake build failed!
    popd
    exit /b 1
)

popd
echo.
echo ========================================
echo Build complete!
echo Output: %BUILD_DIR%\gui\Release\simpleRPA-gui.exe
echo ========================================
