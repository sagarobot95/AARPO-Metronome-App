@echo off
REM Windows double-click launcher.
REM Double-clicking a .bat file opens a console window automatically and runs
REM the app inside it. This just hands off to run.bat in the same folder.
call "%~dp0run.bat"
