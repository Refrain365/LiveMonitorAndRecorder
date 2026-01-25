# LiveMonitorAndRecorder

一个直播监控与录制助手。

Windows项目基于 **Python + Aria2 + FFmpeg**，Linux项目基于 **Python + Streamlink + FFmpeg**

支持对主播直播状态进行监控提醒，并在开播后自动进行直播流录制。

目前项目同时支持 **Windows** 与 **Linux** 平台。

---

## 功能简介

- 主播开播状态监控与提醒
- 自动录制直播流
- 支持 Douyin、Bilibili 等平台
- 基于 FFmpeg 的稳定录制与封装

---

## 平台支持说明

### Windows

- Windows 版本为最初实现的平台
- 提供完整的监控与录制能力
- 相关实现与使用方式请参考 `Windows/` 目录

---

### Linux

- Linux 版本为 **独立实现**，非简单移植
- 功能层面已与原有 Windows 版本保持一致
- 针对 Linux 长时间运行场景进行了稳定性与容错设计

#### Linux 运行环境要求

请确保系统中已正确安装以下依赖：

- **[FFmpeg](https://ffmpeg.org/)**
  转码与封装核心组件（需支持无损封装 MP4）

- **[Streamlink](https://streamlink.github.io/)**
  直播流解析引擎

- **[Python 3](https://www.python.org/downloads/)**
  主程序运行环境

Linux 项目已在 Ubuntu 22.04 环境下测试通过

---

## 项目目标

本项目的目标是逐步完善为一个 稳定、可靠、可长期运行 的直播监控与录制工具，适用于个人使用与服务器挂机场景。

```