# 🏋️ Fitness Viz

健身数据可视化面板 — 把健身日志变成日历、热力图、体重趋势和肌肉高亮图。

**在线演示**：https://wenxixixi.cc/fitness/

## ✨ 功能

- 📅 **月历视图** — 彩色圆点标记训练部位，点击查看详情
- 🔥 **热力图** — GitHub 风格年度训练频率
- 📈 **体重趋势** — 折线图追踪体重变化
- 📊 **训练统计** — 部位分布饼图 + 每周天数柱状图
- 🦴 **肌肉可视化** — 人体正反面 SVG，当天练到的肌肉自动变红

## 🛠 技术栈

纯静态，零依赖构建：

- **数据解析**：Python 脚本，Markdown → JSON
- **前端**：Alpine.js + Chart.js + 手写日历/热力图
- **部署**：Nginx 静态文件托管
- **更新**：cron 定时跑解析脚本

## 🚀 快速开始

### 1. 准备数据

你的健身日志用 Markdown 记录，格式参考 [fitness-logging skill](./docs/logging-format.md)：

```markdown
### 2026-07-12（周日）

### 训练
**💪 今日训练：腿**

- 杠铃深蹲 | 4组 | 80kg×5×4
- 俯卧腿弯举 | 4组 | 30kg×10×2
```

### 2. 运行解析脚本

```bash
python3 parse_fitness.py
```

输出 `data.json` 到部署目录。

### 3. 部署前端

把以下文件放到同一个目录，用任意静态服务器托管：

```
fitness/
├── index.html
├── css/fitness.css
├── img/body-outline.svg
├── data.json
└── data/exercise_map.json
```

```bash
cd fitness && python3 -m http.server 8080
```

打开 `http://localhost:8080` 即可。

## 📁 文件说明

| 文件 | 用途 |
|------|------|
| `parse_fitness.py` | Markdown 日志解析器，输出 JSON |
| `index.html` | 前端单页（Alpine.js + Chart.js） |
| `fitness.css` | 样式（深色/浅色跟随系统） |
| `body-outline.svg` | 人体肌肉轮廓图（16 个可高亮分区） |
| `exercise_map.json` | 动作→肌肉映射表（44 个常见动作） |
| `ARCHITECTURE.md` | 完整架构文档 |

## 📄 License

MIT
