@echo off
setlocal

set SEATML=%1

if "%SEATML%" == "" (
  echo Usage: %0 [seatml-name]
  goto :end
)

set TEMPLATE=%~dp0..\template.seatml

%~dp0sed.exe s/_sample_/%SEATML%/ %TEMPLATE% > %SEATML%.seatml

:end
endlocal
echo on