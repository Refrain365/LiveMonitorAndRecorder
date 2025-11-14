@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

REM 获取当前脚本所在目录
set "SCRIPT_DIR=%~dp0"
REM 移除末尾的反斜杠（如果有）
if "!SCRIPT_DIR:~-1!"=="\" set "SCRIPT_DIR=!SCRIPT_DIR:~0,-1!"

REM 启动aria2，设置工作目录为脚本所在目录
start /min aria2c --enable-rpc --rpc-listen-all --disable-ipv6=true --dir="!SCRIPT_DIR!"

echo Aria2已启动，工作目录设置为: !SCRIPT_DIR!
echo 按任意键退出...

pause >nul
