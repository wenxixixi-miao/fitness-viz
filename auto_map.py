#!/usr/bin/env python3
"""自动将 pending 中的动作推断肌肉群并写入 exercise_map.json"""
import json
import re

PENDING_FILE = '/root/myblog/source/fitness/data/exercise_map_pending.json'
MAP_FILE = '/root/myblog/source/fitness/data/exercise_map.json'

RULES = {
    r"深蹲": ["股四头肌", "臀大肌", "腘绳肌"],
    r"硬拉|罗马尼亚|直腿硬拉": ["股四头肌", "臀大肌", "腘绳肌", "竖脊肌"],
    r"卧推|推胸|夹胸|蝴蝶机|龙门架": ["胸大肌"],
    r"臂屈伸|下压|过头臂屈伸|三头|双杠": ["肱三头肌"],
    r"引体|下拉|划船|拉背": ["背阔肌", "大圆肌", "菱形肌"],
    r"推肩|飞鸟|面拉|侧平举|前平举|耸肩": ["三角肌"],
    r"弯举|牧师凳|托臂弯举": ["肱二头肌"],
    r"腿弯举|腿屈伸": ["股四头肌", "腘绳肌"],
    r"提踵": ["小腿三头肌"],
    r"挺身": ["竖脊肌", "臀大肌"],
    r"卷腹|举腿|健腹轮|腹": ["腹直肌", "腹斜肌"],
    r"保加利亚|哈克": ["股四头肌", "臀大肌"],
    r"夹腿|扩腿": ["内收肌群", "外展肌群"],
    r"跑步|骑行|椭圆机|漫步机|跳绳": ["cardio"],
}

def guess_muscles(name):
    for pattern, muscles in RULES.items():
        if re.search(pattern, name):
            return muscles
    return []

def main():
    try:
        with open(PENDING_FILE) as f:
            pending = json.load(f)
    except:
        pending = {"pending": []}

    try:
        with open(MAP_FILE) as f:
            emap = json.load(f)
    except:
        emap = {"muscles": {}}

    resolved = []
    for item in pending.get('pending', []):
        name = item['name'] if isinstance(item, dict) else str(item)
        muscles = guess_muscles(name)
        if muscles:
            src = 'hermes-auto' if muscles != ['cardio'] else 'cardio'
            emap['muscles'][name] = {'muscles': muscles, 'source': src}
            resolved.append(f"✅ {name} → {', '.join(muscles)}")
        else:
            resolved.append(f"❓ {name} 无法推断，需人工确认")

    # Save
    with open(MAP_FILE, 'w') as f:
        json.dump(emap, f, ensure_ascii=False, indent=2)

    # Keep unresolved in pending
    pending['pending'] = [x for x in pending.get('pending', []) if not guess_muscles(x['name'] if isinstance(x, dict) else str(x))]
    with open(PENDING_FILE, 'w') as f:
        json.dump(pending, f, ensure_ascii=False, indent=2)

    for r in resolved:
        print(r)
    print(f"\n处理 {len(resolved)} 个，剩 {len(pending.get('pending',[]))} 个人工确认")

if __name__ == '__main__':
    main()
