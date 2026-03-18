@echo off
REM Wrapper so agentcore deploy finds "zip" on Windows when only 7-Zip is installed.
REM Usage: zip -r archive.zip path  (or path1 path2 ...)
setlocal
set "SEVENZ=C:\Program Files\7-Zip\7z.exe"
if not exist "%SEVENZ%" (
  echo zip: 7-Zip not found at "%SEVENZ%" 1>&2
  exit /b 1
)
set "RECURSE="
set "ARCHIVE="
set "FIRST_PATH="
:parse
if "%~1"=="" goto run
if /i "%~1"=="-r" ( set "RECURSE=-r" & shift & goto parse )
if "%ARCHIVE%"=="" ( set "ARCHIVE=%~1" & shift & goto parse )
set "FIRST_PATH=%~1"
shift
:run
if "%ARCHIVE%"=="" (
  echo zip: usage zip -r archive.zip path [path ...] 1>&2
  exit /b 1
)
if "%FIRST_PATH%"=="" set "FIRST_PATH=."
"%SEVENZ%" a -tzip %RECURSE% "%ARCHIVE%" %FIRST_PATH% %*
exit /b %ERRORLEVEL%
