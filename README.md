# hermes-control

Windows 快捷控制 [hermes-web-ui](https://github.com/EKKOLearnAI/hermes-web-ui) 的工具集。双击即可启动/停止服务，管理浏览器窗口，无需每次手动打开 WSL 输入命令。

## 前提条件

- Windows 10/11 已安装 WSL2
- WSL 中已安装 Node.js >= 23

## 快速开始

将整个文件夹复制到电脑任意位置，双击 `install.bat` 即可。

安装脚本会自动：
1. 检测你的 WSL 发行版
2. 检测/安装 hermes-web-ui
3. 将工具目录添加到系统 PATH
4. 在桌面创建快捷方式

## 使用方式

### 桌面快捷方式（推荐）

安装后桌面会出现三个快捷方式：

| 快捷方式 | 功能 |
|----------|------|
| **Hermes - Start** | 启动 hermes-web-ui 服务 + 自动打开浏览器 |
| **Hermes - Stop** | 停止服务 + 关闭浏览器 + 关闭 WSL |
| **Hermes - Browser** | 仅打开/聚焦浏览器窗口（服务保持运行） |

### 命令行

安装后在任意终端可直接使用：

```powershell
hermes start      # 启动服务并打开浏览器
hermes stop       # 停止服务、关闭浏览器、关闭 WSL
hermes browser    # 打开浏览器（服务已在后台运行时使用）
hermes close      # 关闭浏览器窗口（不关服务）
hermes restart    # 重启服务
hermes status     # 查看运行状态
```

### 典型使用场景

1. **想用** → 双击 `Hermes - Start`，自动启动 WSL、服务、打开浏览器
2. **暂时不想看页面** → 直接关掉浏览器标签页，服务继续在后台运行
3. **想再看看页面** → 双击 `Hermes - Browser`，重新打开浏览器
4. **彻底不用了** → 双击 `Hermes - Stop`，服务、浏览器、WSL 全部关闭

## 文件说明

| 文件 | 作用 |
|------|------|
| `install.bat` | 一键安装脚本（首次使用时运行） |
| `hermes.ps1` | 核心 PowerShell 脚本，自动检测 WSL 和 hermes-web-ui |
| `hermes.bat` | 命令行万能入口 |
| `start.bat` | 启动服务 + 打开浏览器 |
| `stop.bat` | 停止服务 + 关闭浏览器 + 关闭 WSL |
| `browser.bat` | 仅打开浏览器 |
| `status.bat` | 查看运行状态 |

## 致谢

- [hermes-web-ui](https://github.com/EKKOLearnAI/hermes-web-ui) — 由 [EKKOLearnAI](https://github.com/EKKOLearnAI) 开发的 Hermes Agent Web 管理界面
- [Hermes Agent](https://github.com/NousResearch/hermes-agent) — 由 [NousResearch](https://github.com/NousResearch) 开发的 AI Agent

## License

MIT
