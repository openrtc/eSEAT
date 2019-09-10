
@echo off
@setlocal

if "%1" == "" (
  echo Usage %0 [idl_file]
  goto :end
) 

if not exist rtm (
  mkdir rtm
)

if exist rtm/ (
  omniidl -bpython -Crtm %1
) else (
  echo rtm is not directory, please remove rtm
)

:end
endlocal
echo on