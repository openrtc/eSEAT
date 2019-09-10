@echo off
setlocal

set INST_DIR=%~d0\local\eSEAT
set PYTHON_DIR=
@FOR /F %%i in ( 'find_python.bat' ) do @(
  @set PYTHON_DIR=%%i
)

set FILES=etc\rtc.conf etc\template.seatml etc\setup.bat etc\package-eSEAT.xml
set BIN_FILES=bin_win32\*.bat bin_win32\*.exe bin_win32\gen_ros_msg bin_win32\gen_ros_pkg
set DIRS=html libs 3rd_party examples ros_samples

if "%INST_DIR%" == "" (
  echo Fail to Install
  goto :end
)

echo Install eSEAT
%PYTHON_DIR%\python.exe setup_py3.py install

FOR  %%x in (%FILES%) do (
  xcopy %%x %INST_DIR%\ /D /I /Y /K
)

FOR  %%x in (%BIN_FILES%) do (
  xcopy  %%x %INSt_DIR%\bin\ /D /I /Y /K
)

FOR  %%x in (%DIRS%) do (
  xcopy  %%x %INSt_DIR%\%%x\ /D /I /Y /K
)


:end
endlocal
echo on