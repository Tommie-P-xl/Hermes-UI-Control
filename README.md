# Hermes UI Control

Windows 桌面管理工具，用于控制 [hermes-web-ui](https://github.com/EKKOLearnAI/hermes-web-ui)。通过系统托盘图标一键启动/停止服务，支持 WSL 和 Windows 原生两种运行模式。

## 功能

- 系统托盘常驻，右键菜单快速操作
- 一键启动/停止/重启 hermes-web-ui 服务
- 自动打开浏览器访问 Web UI
- 支持 WSL 和 Windows 原生两种运行模式
- 开机自启动（仅启动管理软件）
- 启动时自动开启服务
- 弹窗通知（启动、停止、重启等关键事件）
- 自动检查更新
- 单实例保护，防止多开
- 退出时自动关闭服务

## 前提条件

### WSL 模式
- Windows 10/11 已安装 WSL2
- WSL 中已安装 Node.js >= 23
- WSL 中已安装 hermes-web-ui（`npm install -g hermes-web-ui`）

### Windows 模式
- Windows 10/11
- 已安装 Node.js >= 23
- 已安装 hermes-web-ui（`npm install -g hermes-web-ui`）

## 安装

### 方式一：下载 EXE（推荐）

从 [Releases](../../releases) 页面下载 `HermesUIControl.exe`，放到任意目录双击运行即可。

### 方式二：从源码运行

```bash
git clone https://github.com/Tommie-P-xl/Hermes-UI-Control.git
cd Hermes-UI-Control
pip install -r requirements.txt
python src/main.py
```

### 方式三：自行打包

```bash
pip install -r requirements.txt
build.bat
```

打包产物在 `dist/HermesUIControl.exe`。

## 使用

双击 `HermesUIControl.exe` 启动后，系统托盘会出现图标。右键点击图标查看菜单：

| 菜单项 | 功能 |
|--------|------|
| 启动服务 | 启动 hermes-web-ui + 打开浏览器 |
| 停止服务 | 停止 hermes-web-ui 服务 |
| 重启服务 | 重启 hermes-web-ui |
| 打开浏览器 | 仅打开/聚焦浏览器窗口 |
| 运行模式 | 切换 WSL/Windows 运行模式 |
| 开机自启动 | 注册/取消 Windows 开机启动 |
| 启动时自动开启服务 | 开机自启时同时启动 hermes |
| 弹窗通知 | 开启/关闭系统通知 |
| 检查更新 | 检查 GitHub 最新版本 |
| 退出 | 停止服务 + 退出程序 |

### 运行模式说明

- **WSL 模式**：在 WSL 中运行 hermes-web-ui，适合已配置好 WSL 环境的用户
- **Windows 模式**：在 Windows 原生环境运行 hermes-web-ui，适合直接在 Windows 上安装的用户

首次运行时默认使用 WSL 模式，可通过右键菜单"运行模式"切换。

### 命令行参数

```bash
HermesUIControl.exe --minimize   # 最小化启动（开机自启用）
HermesUIControl.exe --start      # 启动时自动开启服务
```

## 项目结构

```
src/
├── main.py            # 入口：单实例锁 + 环境检查 + DPI 感知
├── config.py          # 配置常量 + JSON 持久化设置
├── wsl_manager.py     # WSL/hermes-web-ui 控制核心
├── windows_manager.py # Windows 原生 hermes-web-ui 控制
├── autostart.py       # Windows 注册表开机自启动
├── updater.py         # GitHub Releases 自动更新
├── tray.py            # 系统托盘菜单 + 状态轮询 + 通知
├── icon.py            # 图标 base64 嵌入
└── icon.ico           # 应用图标
```

## 更新日志

### v1.0.5
- 修复托盘菜单深色模式在某些 Windows 版本上不生效的问题
- 使用 uxtheme SetPreferredAppMode API 正确启用深色弹出菜单

### v1.0.4
- 托盘菜单背景颜色跟随系统深色/浅色主题
- 改进自动更新流程，使用 latest.json 元数据端点
- 更新脚本增加重试逻辑和分块下载

### v1.0.3
- 修复启动/重启服务后系统托盘图标状态不更新的问题（竞态条件）
- 修复"打开浏览器"功能仅恢复最小化窗口而不打开新标签页的问题
- 启动/重启服务后现在基于实际端口状态判断是否成功

### v1.0.2
- 修复启动/重启服务时浏览器标签页重复打开的问题
- 启动和重启服务后不再自动打开浏览器（hermes-web-ui 自身已处理）

### v1.0.1
- 新增 Windows 原生运行模式支持
- 支持 WSL 和 Windows 两种运行模式切换
- 右键菜单添加"运行模式"选项
- 修复系统通知时托盘图标重复显示的问题

### v1.0.0
- 初始版本
- 系统托盘管理界面
- 开机自启动 / 自动开启服务
- 弹窗通知
- 自动更新检查
- 退出时自动关闭 WSL

## 致谢

- [hermes-web-ui](https://github.com/EKKOLearnAI/hermes-web-ui) — Hermes Agent Web 管理界面
- [Hermes Agent](https://github.com/NousResearch/hermes-agent) — NousResearch AI Agent

## License

MIT
