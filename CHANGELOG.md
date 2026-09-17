# Changelog

## v3.0.0 (2026-09-17)

全栈加固版本：前端极光深色拟物重构（Style A）、MuscleWiki 级解剖矢量肌肉图解，以及后端性能、容灾与数据精准度全面加固。

### 🧬 MuscleWiki 级解剖肌肉图解

- **全新矢量图谱 `img/body-outline.svg`**：改用 MuscleWiki / react-native-body-highlighter 官方男模解剖路径（深浅肌纤维、关节分界、中立骨架），统一视口 `viewBox="0 0 724 1448"`，正反面同比例叠加对齐
- **分层解剖结构**：`.body-border` 轮廓线 / `.body-neutral` 头部手足锁骨关节 / `.muscle` 覆盖 16 大核心肌群（胸大肌、三角肌、背阔肌、肱二头肌、肱三头肌、腹直肌、腹斜肌、股四头肌、腘绳肌、臀大肌、小腿三头肌、斜方肌、竖脊肌、前臂屈肌、内收肌群、胫骨前肌）
- **正反双视角无感切换**：详情抽屉内嵌 iOS 分段药丸 `[正面 Front]` / `[背面 Back]`，纯 CSS 控制显隐，毫秒级无重绘
- **智能主训练面判定**：练背（背阔/菱形/大圆）、练臀、腘绳或竖脊肌主导时自动默认背面；练胸、腹、二头、股四头肌主导时自动默认正面，用户可手动翻转
- **Apple Fitness+ 极光翡翠渲染**：未激活肌群 `#27272A` 暗夜深石板灰，受训肌群 `#10B981` 配 `drop-shadow(0 0 10px rgba(16,185,129,0.75))` 与 0.3s 呼吸过渡
- **Nginx SVG 专项 Gzip**：`image/svg+xml` 实时压缩，传输体积 69 KB → 28 KB（-59.3%）

### ⚡ 后端性能与容灾加固

- **Nginx 全局 Gzip 开启**：解开 `gzip_types`（含 `application/json`、`text/css`、`application/javascript`、`image/svg+xml`）并启用 `gzip_vary on`

  | 静态资源 | 压缩前 | Gzip 传输 | 缩减率 |
  | :--- | ---: | ---: | ---: |
  | `data.json` | 130,449 B | 8,087 B | **-93.8%** |
  | `img/body-outline.svg` | 69,039 B | 28,118 B | **-59.3%** |
  | `css/fitness.css` | 20,229 B | 4,510 B | **-77.7%** |

- **弹性饮食解析器 + Markdown 历史表格恢复**（`parse_fitness.py`）
  - 原生兼容历史 `| 食物 | 热量 | 蛋白 | 碳水 | 脂肪 |` 表格，找回 2026-05-23 ~ 2026-06-17 的空白数据
  - 松散 Token 解析：支持 `- 食物 | kcal | 蛋白 | 碳水 | 脂肪` 任意顺序、缺项容忍、`~` / `约` / `≈` 前缀容忍
  - 修复同日多区块报餐的合并求和 Bug（原为覆盖忽略，改为 `total_kcal` / `protein_g` / `carbs_g` / `fat_g` 累加）
  - 体测与动作分流：纯体重行（`- 65.0kg`）识别为体重记录，`#### 动作名` 下的组数行不再误入动作映射表
  - **实测**：饮食覆盖 92 天 → **118 天**（总 119 天，99.2%）；解析饮食项 368 → **1,361 项**；待映射动作清零 `pending: []`
- **SHA256 增量解析**：解析前对 `fitness_log.md` 与动作映射表联合哈希，数据未变时输出 `✨ 数据源未变化，跳过解析` 并退出，避免无谓刷新 `generated_at`，让浏览器 304 / ETag 协商缓存真正生效
- **POSIX `flock` 文件互斥锁**：`safe_write_fitness.sh` 与 `parse_fitness.py` 通过 `/tmp/fitness_sync.lock` 内核级排他保护，杜绝 Cron 读到半截被截断的 Markdown
- **`logrotate` 日志轮转**：`/etc/logrotate.d/fitness_sync` 每周轮转、保留 4 周、gzip 压缩，`su root root` + `copytruncate` 平滑轮转无需重启服务
- **双轨备份分级策略**（`safe_write_fitness.sh`）：每日首次写入生成 `daily_baseline_YYYYMMDD.bak`（保留 30 天）+ 最近 15 次实时原子快照；空文件/损坏写入由回滚断言 100% 拦截

### 🎨 前端 Style A 视觉重构（Apple Fitness+ 极光深色）

- 纯黑背景 `#09090B` + 翡翠绿荧光主色 `#10B981` + 全站拟物毛玻璃 `backdrop-filter: blur(24px)`
- 悬浮灵动岛底栏（自动避让移动端底部安全区）
- 日历微胶囊训练条：极简圆角分段微药丸条 + 今日荧光呼吸高亮灯
- 动作卡片化：详情抽屉每个动作独立成卡（`.ex-card`），带组数徽章与肌肉分类微标签
- 三大宏量营养素分段进度条：碳水/蛋白/脂肪能量占比三色连续进度条 + 达标提示
- 拟物动效图表：体重折线垂直微光渐变充填、训练分布环形闭环（Doughnut Ring 70% 镂空）、圆角柱状图，动态深色模式自适应

### ✨ visionOS 级液态玻璃与流体弹簧滑块

- **双层内倒角光学反射**：顶部晶圆高光 `inset 0 1px 1.2px 0 rgba(255,255,255,0.22)` + 底部环境暗角 `inset 0 -1px 1.2px 0 rgba(0,0,0,0.5)`，应用于底栏、图表卡、指标卡、动作卡
- **高饱和物理毛玻璃**：`backdrop-filter: blur(32px) saturate(190%)`
- **液态流体弹性药丸指示器**：底栏内绝对定位 `.dock-indicator`，切换采用 Apple 物理弹簧 `cubic-bezier(0.34, 1.45, 0.64, 1)`，带果冻回弹；滑块覆盖微型翡翠渐变与内高光，激活图标上浮 1.5px
- 全 GPU `transform: translate3d(...)` 合成，零第三方依赖，120Hz 满帧

### 🖥️ 桌面端大屏适配与多态主题

- 废除 `max-width: 440px` 手机窄条，`>=768px` 扩展为 `max-width: 1040px` 居中仪表盘，顶部导航升级为桌面状态栏（Logo / 更新时间 / 主题切换 / 刷新）
- 日历单元格扩高至 `62px`，悬浮 `translateY(-2px)` 微浮起 + 翡翠光晕
- 统计页双列网格：部位环形图与每周柱状图左右并排
- 详情由底部半屏抽屉升级为视口正中 `780px` 中央晶体弹窗，左右双栏（动作卡 + 营养宏量 / 3D 解剖肌肉模型同屏常驻）
- 热力图全宽铺展无横向滚动条，四宫格指标平铺 4 列单行
- **多态主题切换**：🌙 暗夜 / ☀️ 浅色 / 🖥️ 跟随系统，状态持久化 `localStorage`，图表实时重绘

### 🔥 热力图重塑与全站丝滑度

- **修复自动滑至底部 Bug**：剔除 `switchTab('heatmap')` 中的页面级 `scrollIntoView`，小屏仅在容器内部用 `scrollLeft` 平滑展现最新周，视口绝不跳动
- **GitHub 连续时间织锦排版**：由按月垂直堆叠（左侧占 30%、右侧 70% 留白）改为 7 行 × 18 周连续网格，左侧 `一/三/五/日` 刻度，5~9 月自左向右平铺
- 顶部月份刻度绝对定位，像素级对齐各月第一周列位置
- 今日仅点亮单格翡翠脉冲环 `box-shadow: 0 0 0 1.8px var(--accent)`，取消整周药丸外框
- 新增四宫格指标概览（累计打卡 / 打卡频率 / 记录周期 / 训练最高峰）与月度训练密度分析条
- **120Hz 丝滑优化**：下拉刷新增加 8px 触发死区与 `Math.abs(dist) > 1.5` 抖动过滤；移除双层嵌套 `requestAnimationFrame`（省 32ms）；`.tab-content` 施加 `min-height: 520px` 防高度塌陷

### 🐛 Bug 修复

- **统计界面首次进入空白（Chart.js × Alpine 生命周期竞态）**
  - 根因：`<template x-if>` 包裹的 `<canvas>` 在 `$nextTick` 时尚未插入 DOM，`getElementById` 命中 `null` 静默跳过，却仍置 `_statsAnimPlayed = true`，导致图表永久空白
  - 修复：`x-show` 持久化 DOM 挂载 + `$nextTick` & `requestAnimationFrame` 双阶段等待布局 + 已存在实例 `.resize()` / `.update('none')` 免重建 + Canvas 存在性递归守卫
- **移动端抽屉关闭叉号被遮挡**
  - 根因：`position: absolute; top: 0` 的关闭按钮位于滚动容器 `.sheet-content` 内，长列表触发 iOS 原生滚动层后被边界裁切并随内容滚出视口
  - 修复：把手与关闭按钮抽离为独立 `.sheet-top-bar`（`flex-shrink: 0; height: 42px`），与滚动区成兄弟层级；按钮固定 `top: 7px; right: 16px` 避开 `border-top-right-radius: 28px` 倒角；`::after` 扩展至 44×44px 热区；滑动关闭手势增加 `scrollTop <= 0` 守卫
- **移动端高频切页内容丢失 / 图表变白**
  - 根因：① `<canvas>` 原生默认缓冲 300×150，`canvas.clientWidth === 0` 守卫被穿透，Chart.js 检测到父容器 0 宽后把 Canvas 行内样式锁死为 `width: 0px`；② Tab 离开时 `destroy()` 与 `requestAnimationFrame` 绘制回调时序竞态，句柄悬空；③ 内联 `style="display:none"` 污染 Alpine 的 `_x_originalDisplay`
  - 修复：实例常驻内存 + `.resize()` / `.update()` 唤醒（废除切页销毁）；父容器 `wrapper.clientWidth < 50` 严苛守卫顺延一帧；清除行内 `display:none` 改用标准 `[x-cloak]`；创建前 `Chart.getChart(canvas)` 兜底清理历史实例；`_resizeHandler` 仅作用于当前激活 Tab

### ✅ 回归验证

| 验证项 | 触发条件 | 实测结果 |
| :--- | :--- | :--- |
| 高频切页压测 | 10 秒内狂点「体重」⇄「统计」30~50 次 | 100% 稳定呈现，图表不丢失、卡片不变白，无需刷新 |
| 高频 4 Tab 压测 | 连续快速点按 4 个 Tab 50+ 次 | 折线/环形/柱状图 100% 稳定，无白屏 |
| 入场渲染耗时 | 现代移动芯片基准 | 单次 Chart 实例化 ~1.5ms |
| 内存与实例监控 | 反复切页 100 次 | 实例复用良好，内存平稳无泄漏，CPU 接近 0% |
| SVG Gzip 传输 | `curl -sIk -H "Accept-Encoding: gzip" .../img/body-outline.svg` | `Content-Encoding: gzip`，传输 28.1 KB |
| 正反面智能识别 | 动作/部位权重探测 | 背/臀/腘绳自动背面，胸/腹/前束自动正面 |
| 增量哈希比对 | `python3 parse_fitness.py` 连跑两次 | 第二次跳过：`✨ 数据源未变化，跳过解析` |
| 饮食覆盖率 | 数据统计扫描 | 119 天中 118 天具备精准饮食数据 |
| 待映射动作字典 | `cat exercise_map_pending.json` | `{"pending": []}` 完全清空 |
| 日志轮转 | `logrotate -d /etc/logrotate.d/fitness_sync` | 语法测试通过，`su root root` 权限正常 |
| 站点连通性 | `curl -sIk https://wenxixixi.cc/fitness/` | `HTTP/1.1 200 OK`，静态资产全量加载 |

---

## v2.0.0 (2026-07-13)

### 🎨 UI/UX 全面升级

- **矢量图标替换**：所有 emoji 改为 Feather 风格 SVG 矢量图标（底部导航、时间戳、刷新、饮食、肌肉图解）
- **P0 体验修复**：
  - 详情卡片支持下滑手势关闭 + 右上角 × 按钮
  - 热力图格子可点击查看当天训练详情
  - 日历翻月后显示"今天"按钮一键跳回
  - 桌面端 max-width 480px 居中，不再空旷
- **P1 体验优化**：
  - 下拉刷新（Pull-to-Refresh）
  - 详情卡片打开时锁定底部导航
  - 后台标签页自动暂停定时器（省电省流量）
  - Chart.js 防抖（横竖屏切换不卡顿）
  - 饼图标签改图例，小屏幕不拥挤
  - 深色模式文字对比度提升至 WCAG AA
  - 加载骨架屏替代纯文字
  - SVG 缓存，只请求一次
- **P2 打磨**：
  - Tab 切换 200ms 淡入淡出过渡
  - 热力图本周高亮
  - 柱状图标签防重叠
  - 日历格子按压缩放反馈
  - 饮食分析显示目标 vs 实际差额
  - JS 代码 var → const/let 现代化
  - fetch 错误处理完善

### 📊 数据增强

- **饮食数据完整解析**：支持 `~` 前缀、千位逗号等格式变体
- **饮食达标分析**：根据增肌/减脂阶段自动判断热量和蛋白质是否达标
- **体重趋势自动合并**：日志正文中的体重记录自动进入趋势图，无需手动维护表格
- **部位推断优化**：算法更准确，卧推不再误标为"肩+手臂"

### 🔧 图表修复

- **彻底修复图表消失 Bug**：采用"先销毁→切 DOM→等布局→创建"全新生命周期，消除竞态条件
- **图表动画优化**：首次加载播放入场动画，后续切换瞬间显示
- **折线图**：点依次出现（1500ms）
- **饼图**：扇区旋转 360° 画出（1200ms）
- **柱状图**：柱子从下往上升起（1000ms）
- **Tab 切换后图表不复建**：用 update() 替代 destroy+create

### 🤖 自动化升级

- 新增 `auto_map.py`：自动推理未映射动作的肌肉群
- 解析器内置自动映射链：解析 → 发现新动作 → 推理 → 重新解析
- 服务器 crontab 从每小时改为每 10 分钟同步
- 体重目标从 JS 硬编码改为读取日志 profile

### 📦 开源新增

- 新增 `skills/` 目录，包含 Hermes 健身记录 Skill
  - `fitness-logging`：规范健身数据记录格式
  - `exercise-mapping-assistant`：自动映射新动作
- 新增 `CHANGELOG.md`
- 新增 `auto_map.py` 自动映射脚本

---

## v1.0.0 (2026-07-12)

- 初始版本
- Alpine.js + Chart.js 独立页面
- 4 Tab：日历 / 热力图 / 体重趋势 / 统计
- 肌肉 SVG 高亮
- 饮食数据解析
- parse_fitness.py 解析脚本
- 开源发布
