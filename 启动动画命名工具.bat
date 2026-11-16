@echo off
chcp 65001 >nul
title Super Pixel Effects 命名工具启动器 (v5.0 双标签版)

where pythonw >nul 2>nul
if %errorlevel%==0 (
    start "" pythonw "%~dp0pixel_effect_namer.py"
    exit
)

where python >nul 2>nul
if %errorlevel%==0 (
    start "" python "%~dp0pixel_effect_namer.py"
    exit
)

if exist "%~dp0PixelEffectNamer.exe" (
    start "" "%~dp0PixelEffectNamer.exe"
    exit
)
pause
