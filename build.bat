@echo off
setlocal

set "ROOT=%~dp0"
call "%ROOT%rust-workspace\build.bat" %*
exit /b %ERRORLEVEL%
