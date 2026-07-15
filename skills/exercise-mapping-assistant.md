---
name: exercise-mapping-assistant
description: 自动处理健身动作映射。每隔一段时间或当用户在 Hermes 中提到新动作时，检查 pending 队列，根据健身知识自动推理肌肉映射并写入正式映射表。
category: fitness
---

# 动作映射自动推理 Skill

## 用途

检查 `/root/myblog/source/fitness/data/exercise_map_pending.json` 中待确认的动作映射，根据健身知识推理并写入正式表。

## 何时触发

- 用户说"检查一下新动作"、"补一下动作映射"
- 或在 parse_fitness.py 运行后自动触发
- 定时执行（建议每次 parse_fitness.py 跑完后）

## 工作流程

### 1. 读取 pending

```bash
cat /root/myblog/source/fitness/data/exercise_map_pending.json
```

### 2. 对每个待处理动作推理

根据动作名称，利用健身知识推理：

| 动作关键词 | 主要肌肉 | 辅助肌肉 |
|-----------|---------|---------|
| 深蹲/蹲类 | 股四头肌 | 臀大肌、腘绳肌、核心肌群 |
| 卧推/推胸类 | 胸大肌 | 三角肌前束、肱三头肌 |
| 引体/下拉类 | 背阔肌 | 大圆肌、菱形肌、肱二头肌 |
| 划船类 | 背阔肌 | 菱形肌、斜方肌中下部 |
| 推肩/飞鸟类 | 三角肌 | 斜方肌 |
| 弯举类 | 肱二头肌 | - |
| 臂屈伸/下压类 | 肱三头肌 | - |
| 腿弯举/腿屈伸类 | 股四头肌、腘绳肌 | - |
| 卷腹/举腿类 | 腹直肌 | 腹斜肌 |
| 跑步/游泳/骑行 | （有氧，无肌肉） | - |
| 排球/篮球/足球 | （球类，无肌肉） | - |

### 3. 写入正式映射表

确认肌肉后写入 `exercise_map.json`：
```bash
python3 -c "
import json
with open('/root/myblog/source/fitness/data/exercise_map.json') as f:
    m = json.load(f)
# 追加条目
m['muscles']['新动作名'] = {'muscles': ['主要肌肉1', '主要肌肉2'], 'source': 'hermes-auto', 'added': '日期', 'confidence': 0.85}
with open('/root/myblog/source/fitness/data/exercise_map.json', 'w') as f:
    json.dump(m, f, ensure_ascii=False, indent=2)
"
```

### 4. 从 pending 中移除已处理的条目

```bash
python3 -c "
import json
with open('/root/myblog/source/fitness/data/exercise_map_pending.json') as f:
    p = json.load(f)
# 过滤已处理的
p['pending'] = [x for x in p['pending'] if x['name'] != '已处理动作名']
with open('/root/myblog/source/fitness/data/exercise_map_pending.json', 'w') as f:
    json.dump(p, f, ensure_ascii=False, indent=2)
"
```

## 规则

1. **有氧/球类不映射肌肉**——在 pending 里标记 `cardio`，直接移除
2. **热身动作映射同主动作**——"绳索三头热身" → 肱三头肌
3. **变体映射到基础动作**——"上斜推胸" → 胸大肌上部 + 三角肌前束
4. **完全无法判断的保留 pending**——等用户确认
5. **每次处理后重新跑 parse_fitness.py**

## 示例

pending 有：`上斜器械推胸`（置信 0.85）

推理：关键词"推胸" → 胸大肌。前缀"上斜" → 上胸部。判断为正确 → 写入正式表。
