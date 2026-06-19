# 番茄钟

基于 Python + tkinter 构建的精美桌面番茄钟。零外部依赖，即开即用。

## 功能介绍

- **三种模式** — 专注（25分钟）/ 短休息（5分钟）/ 长休息（15分钟）
- **自动切换** — 专注与休息自动循环；每完成 4 个专注自动进入长休息
- **圆形进度环** — 可视化倒计时，圆环平滑递减动画
- **任务列表** — 添加、勾选完成、删除当前专注任务
- **番茄计数** — 圆点跟踪今日番茄完成数
- **声音提示** — 计时结束双音提醒（使用 `winsound`）
- **窗口置顶** — 一键将窗口固定在最前
- **自定义设置** — 自由调整时长、间隔、自动切换、音量等
- **历史记录** — 查看每日番茄数量（保留最近 90 天）
- **键盘快捷键** — 无需鼠标即可完整操控

## 界面预览

```
   +----------------------------------+
   |   Pin                 -  □  ✕   |
   +----------------------------------+
   |    专注   |  短休息  |  长休息   |
   |                                  |
   |          +----------+            |
   |         /    25:00   \           |
   |        |   准备开始   |          |
   |         \          /            |
   |          +----------+            |
   |                                  |
   |        ● ● ○ ○   圆点进度        |
   |                                  |
   |    [重置] [▶ 开始] [跳过]       |
   |                                  |
   |   当前任务                       |
   |   [输入任务描述…          ] [+]  |
   |   ○ 购买食材                    |
   |   ○ 代码审查              ✕     |
   |                                  |
   |              [⚙] [📊]            |
   +----------------------------------+
```

## 快速开始

### 方式一：直接运行 EXE（无需安装 Python）

1. 从 [Releases](https://github.com/viva-la-vide01/pomodoro-timer/releases) 页面下载 `PomodoroTimer.exe`
2. 双击运行即可

### 方式二：从源码运行

```bash
git clone https://github.com/viva-la-vide01/pomodoro-timer.git
cd pomodoro-timer/pomodoro-timer
python pomodoro.py
```

需要 Python 3.x（无需安装任何额外包）。

## 键盘快捷键

| 按键 | 功能 |
|------|------|
| `空格` | 开始 / 暂停 |
| `R` | 重置当前计时 |
| `S` | 跳过当前阶段 |
| `1` | 切换到专注模式 |
| `2` | 切换到短休息模式 |
| `3` | 切换到长休息模式 |

## 数据存储

所有设置和历史记录以 JSON 文件存储在 `%USERPROFILE%\.pomodoro_timer\` 目录下：

- `settings.json` — 用户偏好设置（时长、间隔、音量等）
- `history.json` — 每日番茄数及任务列表（保留 90 天）

## 源码构建

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name PomodoroTimer --clean pomodoro.py
```

构建产物位于 `dist/PomodoroTimer.exe`。

## 技术栈

- **语言**：Python 3.9+
- **GUI**：tkinter（标准库）
- **声音**：winsound（Windows 内置）
- **数据**：JSON 文件（标准库）
- **打包**：PyInstaller

## 开源协议

MIT
