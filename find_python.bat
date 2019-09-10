@echo off

setlocal
set PYTHON_VER=37
set FIND_DIRS=%~d0\local "%ProgramFiles%" "%ProgramFiles(x86)%" %~d0

FOR  %%a in (%FIND_DIRS% "%ProgramFiles%" ) do (
  if exist %%a\Python%PYTHON_VER%\python.exe (
    echo %%a\Python%PYTHON_VER%
    goto :end
  )
)
:end
endlocal
echo on