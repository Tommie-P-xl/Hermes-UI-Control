# Hermes UI Control

Windows 桌面管理工具，用于控制 [hermes-web-ui](https://github.com/EKKOLearnAI/hermes-web-ui)。通过系统托盘图标一键启动/停止服务，无需每次手动打开 WSL 输入命令。

## 功能

- 系统托盘常驻，右键菜单快速操作
- 一键启动/停止/重启 hermes-web-ui 服务
- 自动打开浏览器访问 Web UI
- 开机自启动（仅启动管理软件，不启动 WSL）
- 启动时自动开启服务
- 弹窗通知（启动、停止、重启等关键事件）
- 自动检查更新
- 单实例保护，防止多开
- 退出时自动关闭 WSL 和服务

## 前提条件

- Windows 10/11 已安装 WSL2
- WSL 中已安装 Node.js >= 23
- WSL 中已安装 hermes-web-ui（`npm install -g hermes-web-ui`）

## 安装

### 方式一：下载 EXE（推荐）

从 [Releases](../../releases) 页面下载 `HermesUIControl.exe`，放到任意目录双击运行即可。

### 方式二：从源码运行

```bash
git clone https://github.com/YOUR_USERNAME/hermes-control.git
cd hermes-control
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
| 启动服务 | 启动 WSL + hermes-web-ui + 打开浏览器 |
| 停止服务 | 停止服务 + 关闭 WSL |
| 重启服务 | 重启 hermes-web-ui |
| 打开浏览器 | 仅打开/聚焦浏览器窗口 |
| 开机自启动 | 注册/取消 Windows 开机启动 |
| 启动时自动开启服务 | 开机自启时同时启动 hermes |
| 弹窗通知 | 开启/关闭系统通知 |
| 检查更新 | 检查 GitHub 最新版本 |
| 退出 | 停止服务 + 关闭 WSL + 退出程序 |

### 命令行参数

```bash
HermesUIControl.exe --minimize   # 最小化启动（开机自启用）
HermesUIControl.exe --start      # 启动时自动开启服务
```

## 项目结构

```
src/
├── main.py          # 入口：单实例锁 + 环境检查 + DPI 感知
├── config.py        # 配置常量 + JSON 持久化设置
├── wsl_manager.py   # WSL/hermes-web-ui 控制核心
├── autostart.py     # Windows 注册表开机自启动
├── updater.py       # GitHub Releases 自动更新
├── tray.py          # 系统托盘菜单 + 状态轮询 + 通知
├── icon.py          # 图标 base64 嵌入
└── icon.ico         # 应用图标
```

## 更新日志

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
