# LiveMonitorAndRecorder

[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux-blue)](#) [![Python](https://img.shields.io/badge/python-3.8%2B-green)](#) [![License](https://img.shields.io/badge/license-%E4%BB%85%E4%BE%9B%E5%AD%A6%E4%B9%A0%E6%94%AF%E6%B5%81-orange)](#)

一个直播监控与录制助手：对主播直播状态进行监控提醒，开播后自动录制直播流，下播后无损封装为 MP4，并通过微信推送开播提醒。

- **Windows 版**：基于 Python + Aria2 + FFmpeg
- **Linux 版**：基于 Python + Streamlink + FFmpeg

目前项目同时支持 **Windows** 与 **Linux** 平台，支持 **Douyin**、**Bilibili** 等直播平台。

> 作者：bilibili @真理的中点·主要负责Windows版开发
>- Linux版由[github·yhyzzm](https://github.com/yhyzzm)根据Windows版开发
>- 本项目开源免费，请勿倒卖，仅供学习交流。

## ✨ 功能特性

- 🎯 **开播状态监控与提醒** —— 多主播管理，开播即推送（支持 WxPusher / 企业微信机器人）
- 📹 **自动录制直播流** —— 开播瞬间自动开始，断流自动重连、自动续录
- 🖼️ **多档画质** —— 原画 / 蓝光 / 超清 / 高清 / 标清
- 📦 **稳定录制与封装** —— 基于 FFmpeg 无损封装为 MP4，画质零损失
- 🤖 **自动化任务** —— 可将自定义脚本绑定到开播 / 下播事件

## 🪟 Windows 版

Windows 版本为项目最初实现的平台，提供完整的监控与录制能力，相关实现与使用方式请参考 **`Windows/`** 目录。

### 快速开始

```bash
pip install -r requirement.txt
python MonitorAndRecorder.py
```

- 依赖仅 4 个包：`requests` / `selenium` / `aria2p` / `psutil`
- 程序目录自带 `aria2c.exe` 与 `ffmpeg.exe`，无需另外下载
- 首次启动会自动弹出 Edge 采集抖音监控 Cookie（约 15 秒，正常现象）
- EdgeDriver 由程序自动检测 Edge 版本并下载，也可从 [npmmirror 镜像](https://registry.npmmirror.com/binary.html?path=edgedriver/) 手动获取

### 添加主播

1. 在 **主播管理** 页填入主播信息（B站填 UID，抖音填电脑版主页完整 URL），点击【添加主播】
2. 切到 **抖音录播(V2)**，把「自动录播」点成 ✓、选好画质即可
3. 主播一开播即自动录制，下播后自动转码（可选）

> 完整配置流程与各功能细节，请阅读 [更详细的instructions说明书](./instructions.txt)。

## 🐧 Linux 版

Linux 版本为**独立实现**，并非简单移植：

- 功能层面已与 Windows 版本保持一致
- 针对 Linux **长时间运行**场景进行了稳定性与容错设计
- 适用于服务器挂机、无人值守场景

### 运行环境要求

| 依赖 | 说明 |
|---|---|
| Python 3 | 主程序运行环境 |
| Streamlink | 直播流解析引擎 |
| FFmpeg | 转码与封装核心组件（需支持无损封装 MP4） |

已在 **Ubuntu 22.04** 环境下测试通过。

```bash
# Ubuntu / Debian 示例
sudo apt install ffmpeg streamlink
pip install -r requirement.txt
```

## 🎯 项目目标

逐步完善为一个**稳定、可靠、可长期运行**的直播监控与录制工具，适用于个人使用与服务器挂机场景。

## ❓ 常见问题（Windows 精选）

| 现象 | 解决方法 |
|---|---|
| 启动时弹出抖音网页 | 正常的 Cookie 采集流程，约 15 秒自动关闭；可在设置中改为「不自动获取」 |
| 直播中却显示「未开播」 | 监控 Cookie 失效，点【刷新监控Cookie】重新获取 |
| 直播中但录播拿不到直链 | 录播 Cookie 失效，点【刷新录播Cookie】重新采集 |
| V1 页提示未安装 aria2p | `pip install aria2p` |
| 收不到微信通知 | 依次检查：全局开关 → 所属通知组的通知方式 → 是否处于勿扰时段 |
| 电脑卡、占用高 | 「高级设置」把监控速度调至 3~5 档 |

## 📜 声明

本项目仅供学习交流，请勿用于商业用途。开源免费，**请勿倒卖**。
