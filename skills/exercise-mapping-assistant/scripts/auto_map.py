#!/usr/bin/env python3
"""自动推理 pending 里的动作肌肉映射，写入 exercise_map.json

数据目录通过环境变量 FITNESS_DATA_DIR 指定，默认取当前目录下的 data/。
用法：FITNESS_DATA_DIR=data python3 auto_map.py
"""

import json
import os
import re

DATA_DIR = os.environ.get("FITNESS_DATA_DIR", "data")
MAP_FILE = os.path.join(DATA_DIR, "exercise_map.json")
PENDING_FILE = os.path.join(DATA_DIR, "exercise_map_pending.json")

RULES = [
    (r"深蹲|哈克|保加利亚", ["股四头肌", "臀大肌", "腘绳肌"]),
    (r"硬拉|罗马尼亚|直腿硬拉", ["股四头肌", "臀大肌", "腘绳肌", "竖脊肌"]),
    (r"卧推|推胸|夹胸|蝴蝶机|龙门架", ["胸大肌"]),
    (r"臂屈伸|下压|过头臂屈伸|三头|双杠", ["肱三头肌"]),
    (r"引体|下拉|划船|拉背", ["背阔肌", "大圆肌", "菱形肌"]),
    (r"推肩|飞鸟|面拉|侧平举|前平举|耸肩|热身肩", ["三角肌"]),
    (r"弯举|二头|牧师凳", ["肱二头肌"]),
    (r"腿弯举|腿屈伸", ["股四头肌", "腘绳肌"]),
    (r"提踵", ["小腿三头肌"]),
    (r"挺身", ["竖脊肌", "臀大肌"]),
    (r"卷腹|举腿|健腹轮|滚腹轮|腹", ["腹直肌", "腹斜肌"]),
    (r"夹腿|扩腿", ["内收肌群", "外展肌群"]),
]

CARDIO = re.compile(r"跑|骑行|椭圆机|漫步机|跳绳|游泳|排球|篮球|足球")


def guess_muscles(name):
    """按关键词推理动作对应的肌肉群，推理不出来返回空列表。"""
    for pattern, muscles in RULES:
        if re.search(pattern, name):
            return muscles
    if CARDIO.search(name):
        return ["cardio"]
    return []


def main():
    if not os.path.exists(PENDING_FILE):
        print(f"没有 {PENDING_FILE}，跳过")
        return
    if not os.path.exists(MAP_FILE):
        print(f"没有 {MAP_FILE}，跳过")
        return

    with open(PENDING_FILE, encoding="utf-8") as f:
        pending = json.load(f)
    items = pending.get("pending") or []
    if not items:
        print("pending 为空，跳过")
        return

    with open(MAP_FILE, encoding="utf-8") as f:
        emap = json.load(f)
    emap.setdefault("muscles", {})

    resolved, unresolved = [], []
    for item in items:
        name = item["name"] if isinstance(item, dict) else str(item)
        muscles = guess_muscles(name)
        if muscles:
            emap["muscles"][name] = {
                "muscles": muscles,
                "source": "cardio" if muscles == ["cardio"] else "hermes-auto",
            }
            resolved.append(f"✅ {name} → {', '.join(muscles)}")
        else:
            unresolved.append(item)
            resolved.append(f"❓ {name} 无法推断，需人工确认")

    with open(MAP_FILE, "w", encoding="utf-8") as f:
        json.dump(emap, f, ensure_ascii=False, indent=2)

    pending["pending"] = unresolved
    with open(PENDING_FILE, "w", encoding="utf-8") as f:
        json.dump(pending, f, ensure_ascii=False, indent=2)

    for line in resolved:
        print(line)
    print(f"\n处理 {len(resolved)} 个，剩 {len(unresolved)} 个人工确认")


if __name__ == "__main__":
    main()
