# LiveMonitorAndRecorder

这是一个直播监控录制助手。项目基于 Python 编程，Aria2 和 FFmpeg。  
支持 douyin、bilibili 的主播直播状态监控提醒；以及 douyin 直播间录制（可录制任意画质的直播流）。  
发行版支持 Windows 64 位系统。  
目标是做最稳定和全能的直播间监控录制助手！

---

## Linux 支持说明（实验性）

当前已提供 Linux 平台的核心功能实现，用于直播状态监控及录制。  
部分 Windows 平台特有功能暂未支持.

### 运行环境要求

请确保系统中已正确安装以下依赖：

- **ffmpeg**  
  转码与封装核心组件，需确保支持无损封装 MP4  
  ```bash
  ffmpeg -version
  ```

- **streamlink**  
  直播流解析引擎，用于抓取直播流  
  ```bash
  streamlink --version
  ```

- **python3**  
  主程序运行环境  
  ```bash
  python3 --version
  ```

> 建议使用较新的 Linux 发行版（如 Ubuntu 22.04+），以确保依赖版本兼容性。
