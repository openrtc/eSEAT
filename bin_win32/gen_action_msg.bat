
if "ROS_DISTRO" == "" (
  echo Unknown distribution....
  goto :end
)

if "%1" == "" or "%2" == "" (
  echo Usage: %0 [pkg-name] [action-name]
  goto :end
)

set PKG_NAME=%1
set ACTION_NAME=%2

set GENACTION=%ROS_HOME%\lib\actionlib_msgs\genaction.py
set PKG_DIR=ros\packages\%PKG_NAME%

python.exe %GENACTION% %PKG_DIR%\action\%ACTION_NAME%.action -o %PKG_DIR%/msg

:end