@echo off
@set SEAT_ROOT=%~dp0
@echo on

python.exe %SEAT_ROOT%\eSEAT.py %1 %2 %3
