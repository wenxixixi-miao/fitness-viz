import os
import json
import re
from datetime import datetime

BASE_DIR = os.environ.get('FITNESS_BASE_DIR', '')

def get_path(path):
    if path.startswith('/'):
        if BASE_DIR and BASE_DIR != '/':
            return os.path.join(BASE_DIR, path[1:])
        return path
    return os.path.join(BASE_DIR, path)

LOG_FILE = get_path('/root/fitness_log.md')
DATA_OUT = get_path('/var/www/html/fitness/data.json')
MAP_FILE = get_path('/root/myblog/source/fitness/data/exercise_map.json')
PENDING_FILE = get_path('/root/myblog/source/fitness/data/exercise_map_pending.json')

KEYWORD_RULES = {
    r"深蹲": ["股四头肌", "臀大肌", "腘绳肌"],
    r"卧推|推胸|夹胸": ["胸大肌"],
    r"臂屈伸|下压|过头臂屈伸|三头": ["肱三头肌"],
    r"引体|下拉|划船|拉背": ["背阔肌", "大圆肌", "菱形肌"],
    r"推肩|飞鸟|面拉|侧平举|前平举|耸肩": ["三角肌"],
    r"弯举": ["肱二头肌"],
    r"腿弯举|腿屈伸": ["股四头肌", "腘绳肌"],
    r"挺身": ["竖脊肌", "臀大肌"],
    r"卷腹|举腿|健腹轮|腹": ["腹直肌", "腹斜肌"],
    r"保加利亚|哈克": ["股四头肌", "臀大肌"],
    r"夹腿|扩腿": ["内收肌群", "外展肌群"],
}

def guess_muscles(exercise_name):
    for pattern, muscles in KEYWORD_RULES.items():
        if re.search(pattern, exercise_name):
            return muscles, 0.85
    return [], 0.0

def load_json(filepath, default):
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except:
                return default
    return default

def save_json(filepath, data):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def parse_log():
    if not os.path.exists(LOG_FILE):
        print(f"File not found: {LOG_FILE}")
        return

    with open(LOG_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    exercise_map = load_json(MAP_FILE, {"muscles": {}})
    pending_map = load_json(PENDING_FILE, {"pending": []})

    days = []
    errors = []
    skipped = 0
    parsed_ok = 0
    new_actions = 0
    weight_log = []

    # Parse weight log table
    weight_table_match = re.search(r'\|\s*日期\s*\|\s*体重\(kg\)\s*\|\s*体脂率\(%\)\s*\|\s*备注\s*\|[\s\S]*?(?=\n\n|\n##)', content)
    if weight_table_match:
        table_lines = weight_table_match.group(0).strip().split('\n')[2:]
        for line in table_lines:
            cols = [c.strip() for c in line.split('|')[1:-1]]
            if len(cols) >= 2:
                date_str = cols[0].replace('**', '').strip()
                weight_str = cols[1].replace('**', '').strip()
                if date_str and weight_str:
                    try:
                        weight_log.append({
                            "date": date_str,
                            "weight_kg": float(weight_str)
                        })
                    except ValueError:
                        pass

    # Split by dates
    blocks = re.split(r'\n(?=### \d{4}-\d{2}-\d{2})', content)
    
    for block in blocks:
        block = block.strip()
        if not block.startswith('### '):
            continue
            
        lines = block.split('\n')
        header = lines[0]
        
        m_date = re.search(r'### (\d{4}-\d{2}-\d{2})(?:[（\(](.+?)[）\)])?', header)
        if not m_date:
            errors.append({"block": header, "reason": "Date parse failed"})
            skipped += 1
            continue
            
        date_str = m_date.group(1)
        weekday = m_date.group(2)
        if not weekday:
            try:
                dt = datetime.strptime(date_str, "%Y-%m-%d")
                weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
                weekday = weekdays[dt.weekday()]
            except:
                weekday = "未知"
        
        day_data = {
            "date": date_str,
            "weekday": weekday,
            "has_training": False,
            "body_parts": [],
            "exercises": [],
            "diet": None,
            "weight_kg": None,
            "notes": None
        }
        
        # Try finding body parts explicitly
        body_part_match = re.search(r'\*\*(?:部位|💪 今日训练).*?：(.*?)\*\*', block)
        if body_part_match:
            parts_str = body_part_match.group(1).replace('、', ' ').replace('/', ' ')
            for p in ["胸", "背", "腿", "肩", "手臂", "有氧"]:
                if p in parts_str:
                    day_data["body_parts"].append(p)
        
        # Parse exercises
        in_diet = False
        for line in lines[1:]:
            line = line.strip()
            if '饮食' in line:
                in_diet = True
            elif '训练' in line or '部位' in line or '运动' in line:
                in_diet = False
            
            # extract weight (handle **bold** markers: 体重：**63.35kg**)
            w_match = re.search(r'体重[：:]\s*\**[（(]?\s*([\d\.]+)\s*[kgkK][gG]?\**', line)
            if w_match:
                day_data["weight_kg"] = float(w_match.group(1))
                
            # extract diet summary line
            d_match = re.search(r'饮食[：:]\s*(.+)', line)
            if d_match:
                diet_str = d_match.group(1)
                kcal_m = re.search(r'(?:热量)?\s*(\d+)\s*kcal|热量\s*(\d+)', diet_str)
                pro_m = re.search(r'蛋白\s*([\d\.]+)', diet_str)
                carb_m = re.search(r'碳水\s*([\d\.]+)', diet_str)
                fat_m = re.search(r'脂肪\s*([\d\.]+)', diet_str)
                
                day_data["diet"] = {
                    "total_kcal": float(kcal_m.group(1) or kcal_m.group(2)) if kcal_m else None,
                    "protein_g": float(pro_m.group(1)) if pro_m else None,
                    "carbs_g": float(carb_m.group(1)) if carb_m else None,
                    "fat_g": float(fat_m.group(1)) if fat_m else None
                }

            # Exercise list format
            list_match = re.match(r'-\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+)', line)
            list_match2 = re.match(r'-\s*(.+?)\s*\|\s*(.+)', line)
            
            # Check if looks like exercise (has kg/组, not kcal/g)
            is_exercise_line = False
            if list_match or list_match2:
                name = (list_match or list_match2).group(1).strip()
                rest = (list_match or list_match2).group(2).strip()
                full = name + rest + ((list_match or list_match2).group(3) if list_match else '')
                # Skip diet/body-measurement lines
                if not re.search(r'(kcal|蛋白|碳水|脂肪|BMI|内脏|骨量|水分|基础代谢|身体得分)', name + rest):
                    is_exercise_line = True
            
            if not is_exercise_line:
                continue
            
            in_diet = False  # found exercise, reset diet flag
            
            if list_match:
                ex_name = list_match.group(1).strip()
                sets_str = list_match.group(2).strip()
                weight_disp = list_match.group(3).strip()
                # Parse sets correctly: "5组×10次" → 5, "1组+3组" → 4
                grp_matches = re.findall(r'(\d+)\s*组', sets_str)
                if grp_matches:
                    sets_count = sum(int(m) for m in grp_matches)
                else:
                    # Fallback: "5×10" → first number
                    m = re.search(r'(\d+)\s*[×x×]', sets_str)
                    sets_count = int(m.group(1)) if m else (int(re.sub(r'\D', '', sets_str)) if re.search(r'\d', sets_str) else 1)
                # Sanity: no real exercise has >50 sets
                if sets_count > 50:
                    sets_count = 1
                
                day_data["exercises"].append({
                    "name": ex_name,
                    "sets": sets_count,
                    "weight_display": weight_disp
                })
            elif list_match2:
                ex_name = list_match2.group(1).strip()
                details = list_match2.group(2).strip()
                # Parse sets: "5组×10次" → 5, "1组×10次+3组×7次" → 4
                grp_matches = re.findall(r'(\d+)\s*组', details)
                sets = sum(int(m) for m in grp_matches) if grp_matches else 1
                
                day_data["exercises"].append({
                    "name": ex_name,
                    "sets": sets,
                    "weight_display": details
                })
                    
            # Exercise table format
            if line.startswith('|') and '动作' not in line and '---' not in line:
                cols = [c.strip() for c in line.split('|')[1:-1]]
                if len(cols) >= 3 and not (cols[0] == '食物' or cols[0] == '项目' or cols[0] == '时间'):
                    ex_name, sets, weight_disp = cols[0], cols[1], cols[2]
                    if not ('kcal' in sets or 'kcal' in weight_disp or 'g' in sets or 'g' in weight_disp):
                        day_data["exercises"].append({
                            "name": ex_name,
                            "sets": int(re.sub(r'\D', '', sets)) if re.search(r'\d', sets) else 1,
                            "weight_display": weight_disp
                        })

        # Resolve exercises & body parts
        all_muscles = set()
        for ex in day_data["exercises"]:
            name = ex["name"]
            day_data["has_training"] = True
            
            if name in exercise_map["muscles"]:
                muscles = exercise_map["muscles"][name]["muscles"]
                ex["muscles"] = muscles
                ex["muscle_mapped"] = True
            else:
                base_name = re.sub(r'[（\(].*?[）\)]', '', name).strip()
                if base_name in exercise_map["muscles"]:
                    muscles = exercise_map["muscles"][base_name]["muscles"]
                    ex["muscles"] = muscles
                    ex["muscle_mapped"] = True
                else:
                    muscles, conf = guess_muscles(base_name)
                    ex["muscles"] = muscles
                    ex["muscle_mapped"] = False if conf < 0.8 else True
                    
                    if not any(p["name"] == name for p in pending_map["pending"]):
                        # Filter out diet and metrics
                        if not re.search(r'kcal|蛋白|kg|g|×|BMI|内脏|骨量|面包|牛奶|身体得分|水分|基础代谢', name):
                            pending_map["pending"].append({
                                "name": name,
                                "detected_date": date_str,
                                "guessed_muscles": muscles,
                                "confidence": conf,
                                "reason": "auto-guessed" if conf > 0 else "unmapped"
                            })
                            new_actions += 1
            all_muscles.update(ex["muscles"])
            
        # Fallback body parts if empty
        if not day_data["body_parts"] and day_data["has_training"]:
            m_str = " ".join(all_muscles)
            if "胸" in m_str: day_data["body_parts"].append("胸")
            if "背" in m_str: day_data["body_parts"].append("背")
            if "股四" in m_str or "腘绳" in m_str or "臀" in m_str: day_data["body_parts"].append("腿")
            if "三角" in m_str: day_data["body_parts"].append("肩")
            if "二头" in m_str or "三头" in m_str: day_data["body_parts"].append("手臂")
            if "腹" in m_str: day_data["body_parts"].append("腹")

        day_data["body_parts"] = list(set(day_data["body_parts"]))
        days.append(day_data)
        parsed_ok += 1

    # Merge duplicate dates (e.g., diet-only block + training block for same day)
    merged_days = {}
    for d in days:
        dt = d["date"]
        if dt not in merged_days:
            merged_days[dt] = d
        else:
            existing = merged_days[dt]
            # Combine exercises
            existing["exercises"].extend(d["exercises"])
            # Merge body_parts
            existing["body_parts"] = list(set(existing["body_parts"] + d["body_parts"]))
            # If either has training, mark as training
            if d["has_training"]:
                existing["has_training"] = True
            # Keep weight if either has it
            if d["weight_kg"] and not existing["weight_kg"]:
                existing["weight_kg"] = d["weight_kg"]
            if d["diet"] and not existing["diet"]:
                existing["diet"] = d["diet"]
            parsed_ok -= 1  # merged, not a new day
    days = list(merged_days.values())
    days.sort(key=lambda x: x["date"])

    # Merge daily weights into weight_log (so trend chart shows all weights)
    wl_dates = {w["date"] for w in weight_log}
    for day in days:
        if day["weight_kg"] and day["date"] not in wl_dates:
            weight_log.append({"date": day["date"], "weight_kg": day["weight_kg"]})
            wl_dates.add(day["date"])
    weight_log.sort(key=lambda x: x["date"])

    # Generate data.json
    data_out = {
        "meta": {
            "generated_at": datetime.now().isoformat(),
            "source_file": "/root/fitness_log.md",
            "parse_summary": {
                "total_days": parsed_ok + skipped,
                "parsed_ok": parsed_ok,
                "skipped": skipped,
                "new_actions_unmapped": new_actions,
                "errors": errors
            }
        },
        "weight_log": weight_log,
        "days": days
    }
    
    save_json(DATA_OUT, data_out)
    save_json(PENDING_FILE, pending_map)
    
    print("📊 解析摘要")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"✅ 成功解析: {parsed_ok} 天")
    print(f"⚠️ 格式异常跳过: {skipped} 条")
    print(f"🆕 新动作待映射: {new_actions} 个")
    print(f"📁 输出: {DATA_OUT}")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━")

if __name__ == '__main__':
    parse_log()
