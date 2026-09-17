import os
import sys
import json
import re
import fcntl
import hashlib
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
WEB_DATA_DIR = get_path('/var/www/html/fitness/data')
LOCK_FILE = '/tmp/fitness_sync.lock'
STATE_FILE = get_path('/var/www/html/fitness/.parse_state.json')

KEYWORD_RULES = {
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
    tmp_file = filepath + '.tmp'
    with open(tmp_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_file, filepath)

def compute_source_hash():
    h = hashlib.sha256()
    for p in [LOG_FILE, MAP_FILE]:
        if os.path.exists(p):
            try:
                with open(p, 'rb') as f:
                    h.update(f.read())
            except:
                pass
    return h.hexdigest()

def parse_sets(details):
    """Parse set count from exercise details string.
    
    Supports: "5组×10次" → 5, "80kg×5×4" → 4, "50kg×8×4组" → 4,
    "15kg×8 + 15kg×10×3" → 4, "自重15×4" → 4, "40kg×8+50kg×7+50kg×5+55kg×3" → 4
    """
    grp_matches = re.findall(r'(\d+)\s*组', details)
    if grp_matches:
        return sum(int(m) for m in grp_matches)
    
    segments = [s.strip() for s in details.split('+') if s.strip()]
    total = 0
    for seg in segments:
        x_nums = re.findall(r'[×x×](\d+)', seg)
        if len(x_nums) >= 2:
            total += int(x_nums[-1])
        elif len(x_nums) == 1:
            if len(segments) == 1:
                if 'kg' in seg.lower():
                    total += 1
                else:
                    total += int(x_nums[0])
            else:
                total += 1
        else:
            total += 1
    return max(total, 1)

def parse_diet_item(line):
    """Flexible diet parser supporting Markdown table rows and loose list items."""
    # Filter out summaries and non-food body measurements
    if re.search(r'小计|合计|总计|总结|今日累计|基础代谢|内脏脂肪|骨量|水分|身体得分|健康评分', line):
        return None

    # Handle Markdown table row: | food | kcal | pro | carbs | fat |
    if line.startswith('|') and not line.startswith('|--') and not re.search(r'\|\s*食物\s*\|', line):
        parts = [p.strip() for p in line.split('|')[1:-1]]
        if len(parts) >= 2:
            kcal_m = re.search(r'(\d+[\d,]*)\s*kcal', parts[1])
            if kcal_m:
                kcal = int(kcal_m.group(1).replace(',', ''))
                pro = 0.0
                if len(parts) >= 3:
                    m = re.search(r'([\d.]+)', parts[2])
                    if m: pro = float(m.group(1))
                carbs = 0.0
                if len(parts) >= 4:
                    m = re.search(r'([\d.]+)', parts[3])
                    if m: carbs = float(m.group(1))
                fat = 0.0
                if len(parts) >= 5:
                    m = re.search(r'([\d.]+)', parts[4])
                    if m: fat = float(m.group(1))
                return {"kcal": kcal, "protein_g": pro, "carbs_g": carbs, "fat_g": fat}

    # Handle list item: - food | ...
    if line.startswith('-') and 'kcal' in line:
        if re.search(r'跑|跳绳|有氧|骑行|椭圆机|漫步机', line) and not re.search(r'餐|吃|奶|蛋|肉|粉|饭|面|油|蕉|菜|果', line):
            return None
        
        kcal_m = re.search(r'[~约≈]?\s*(\d+[\d,]*)\s*kcal', line)
        if not kcal_m:
            return None
        kcal = int(kcal_m.group(1).replace(',', ''))

        pro = 0.0
        pm = re.search(r'蛋白[：:]?\s*([\d.]+)\s*g|([\d.]+)\s*g\s*蛋白', line)
        if pm:
            pro = float(pm.group(1) or pm.group(2))

        carbs = 0.0
        cm = re.search(r'碳水[：:]?\s*([\d.]+)\s*g|([\d.]+)\s*g\s*碳水', line)
        if cm:
            carbs = float(cm.group(1) or cm.group(2))

        fat = 0.0
        fm = re.search(r'脂肪[：:]?\s*([\d.]+)\s*g|([\d.]+)\s*g\s*脂肪', line)
        if fm:
            fat = float(fm.group(1) or fm.group(2))

        return {"kcal": kcal, "protein_g": pro, "carbs_g": carbs, "fat_g": fat}

    return None

def parse_log(allow_auto_remap=True):
    dry_run = '--dry-run' in sys.argv
    force = '--force' in sys.argv

    # 1. Acquire flock to prevent race condition with safe_write_fitness.sh
    lock_fd = None
    if not dry_run and os.environ.get('FITNESS_SYNC_LOCKED') != '1':
        try:
            lock_fd = open(LOCK_FILE, 'w')
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (BlockingIOError, PermissionError):
            print("⏳ 另一个同步或解析进程正在运行，跳过本次解析")
            return
        except Exception:
            pass

    try:
        if not os.path.exists(LOG_FILE):
            print(f"File not found: {LOG_FILE}")
            return

        # 2. SHA256 Incremental Check
        current_hash = compute_source_hash()
        last_state = load_json(STATE_FILE, {})
        if not dry_run and not force and last_state.get('source_hash') == current_hash and os.path.exists(DATA_OUT):
            print(f"✨ 数据源未变化，跳过解析 (SHA: {current_hash[:8]})")
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

        # Parse profile info (phase, targets)
        profile = {"phase": "增肌期", "height_cm": 167, "weight_kg": 68, "protein_target": 120, "calorie_target": 2600}
        phase_match = re.search(r'当前阶段[：:]\s*\**(.+?)\**\s', content)
        if phase_match:
            p = phase_match.group(1)
            if '减' in p: profile["phase"] = "减脂期"
        weight_match = re.search(r'目标体重[：:]～?\s*(\d+)', content)
        if weight_match: profile["weight_kg"] = float(weight_match.group(1))
        protein_match = re.search(r'蛋白目标\s*(\d+)', content)
        if protein_match: profile["protein_target"] = int(protein_match.group(1))

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
            body_part_match = re.search(r'\*\*(?:部位|💪 今日训练|有氧).*?[：:](.*?)\*\*', block)
            if body_part_match:
                parts_str = body_part_match.group(1).replace('、', ' ').replace('/', ' ')
                full_header = body_part_match.group(0)
                if full_header.startswith('**有氧'): day_data["body_parts"].append("有氧")
                if "胸" in parts_str: day_data["body_parts"].append("胸")
                if "背" in parts_str: day_data["body_parts"].append("背")
                if "腿" in parts_str: day_data["body_parts"].append("腿")
                if "肩" in parts_str: day_data["body_parts"].append("肩")
                if "二头" in parts_str or "三头" in parts_str or "手臂" in parts_str: day_data["body_parts"].append("手臂")
                if "有氧" in parts_str: day_data["body_parts"].append("有氧")
                if "腹" in parts_str: day_data["body_parts"].append("腹")
            
            # Parse lines in block
            current_h4_exercise = None
            for line in lines[1:]:
                line = line.strip()

                # Track H4 headers
                h4_match = re.match(r'^####\s+(.+)$', line)
                if h4_match:
                    h4_title = h4_match.group(1).strip()
                    if not any(k in h4_title for k in ['餐', '补剂', '加餐', '夜宵', '早', '中', '晚', '饮食', '体测', '总结', '备注', '休息']):
                        current_h4_exercise = h4_title
                    else:
                        current_h4_exercise = None
                    continue
                
                # Weight from "体重：**63.35kg**"
                w_match = re.search(r'体重[：:]\s*\**[（(]?\s*([\d\.]+)\s*[kgkK][gG]?\**', line)
                if w_match:
                    day_data["weight_kg"] = float(w_match.group(1))

                # Weight from bare line "- 65.0kg"
                bare_weight_match = re.match(r'-\s*(\d+[\d.]*)\s*[kgkK][gG]?\s*$', line)
                if bare_weight_match:
                    if not day_data["weight_kg"]:
                        day_data["weight_kg"] = float(bare_weight_match.group(1))
                    continue

                # Flexible diet parse
                diet_item = parse_diet_item(line)
                if diet_item:
                    if not day_data["diet"]:
                        day_data["diet"] = {"total_kcal": 0, "protein_g": 0.0, "carbs_g": 0.0, "fat_g": 0.0}
                    day_data["diet"]["total_kcal"] += diet_item["kcal"]
                    day_data["diet"]["protein_g"] = round(day_data["diet"]["protein_g"] + diet_item["protein_g"], 1)
                    day_data["diet"]["carbs_g"] = round(day_data["diet"]["carbs_g"] + diet_item["carbs_g"], 1)
                    day_data["diet"]["fat_g"] = round(day_data["diet"]["fat_g"] + diet_item["fat_g"], 1)
                    continue

                # Skip summary / total lines so they are not parsed as exercises
                if re.search(r'小计|合计|总计|总结', line):
                    continue

                # Check if line is a set under current_h4_exercise: e.g. "- 20kg x 10（热身）"
                if current_h4_exercise and line.startswith('-') and re.search(r'kg|[×x×]\s*\d+|组', line):
                    detail = line[1:].strip()
                    sets = parse_sets(detail)
                    muscles_raw = exercise_map.get("muscles", {}).get(current_h4_exercise, [])
                    muscles = muscles_raw.get("muscles", []) if isinstance(muscles_raw, dict) else (muscles_raw if isinstance(muscles_raw, list) else [])
                    confidence = 1.0 if muscles else 0.0
                    if not muscles:
                        muscles, confidence = guess_muscles(current_h4_exercise)
                    day_data["exercises"].append({
                        "name": current_h4_exercise,
                        "sets": sets,
                        "weight_display": detail,
                        "muscles": muscles,
                        "confidence": confidence
                    })
                    day_data["has_training"] = True
                    continue

                # Exercise list format
                list_match = re.match(r'-\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+)', line)
                list_match2 = re.match(r'-\s*(.+?)\s*\|\s*(.+)', line)
                bare_match = re.match(r'-\s*(\S.+?)\s*$', line)
                
                is_exercise_line = False
                if list_match or list_match2:
                    name = (list_match or list_match2).group(1).strip()
                    rest = (list_match or list_match2).group(2).strip()
                    if not re.search(r'(kcal|蛋白|碳水|脂肪|BMI|内脏|骨量|水分|基础代谢|身体得分|健康评分|体重[：:]|体脂率|肌肉[：:])', name + rest) \
                       and name not in ('（待记录）','（休息日）','(待记录)','(rest)'):
                        is_exercise_line = True
                elif bare_match:
                    bare_name = bare_match.group(1).strip()
                    if not re.search(r'(kcal|蛋白|碳水|脂肪|BMI|内脏|骨量|水分|基础代谢|身体得分|体重|体脂|肌肉|D3|已吃|补剂|小计)', bare_name) \
                       and bare_name not in ('--', '---', '…', '...') \
                       and not re.match(r'^合计|^训练次数|^备注|^\[', bare_name) \
                       and not re.match(r'^\d+[\d.]*\s*kg$', bare_name, re.I):
                        is_exercise_line = True
                
                if not is_exercise_line:
                    continue
                    
                if list_match:
                    name = list_match.group(1).strip()
                    part1 = list_match.group(2).strip()
                    part2 = list_match.group(3).strip()
                    sets = parse_sets(part1 + ' ' + part2)
                    weight_display = f"{part1} | {part2}"
                elif list_match2:
                    name = list_match2.group(1).strip()
                    part1 = list_match2.group(2).strip()
                    sets = parse_sets(part1)
                    weight_display = part1
                else:
                    name = bare_match.group(1).strip()
                    sets = 1
                    weight_display = "自重"
                
                # Check mapping
                muscles_raw = exercise_map.get("muscles", {}).get(name, [])
                if isinstance(muscles_raw, dict):
                    muscles = muscles_raw.get("muscles", [])
                elif isinstance(muscles_raw, list):
                    muscles = muscles_raw
                else:
                    muscles = []
                confidence = 1.0 if muscles else 0.0
                
                if not muscles:
                    muscles, confidence = guess_muscles(name)
                    if not muscles:
                        if name not in pending_map.get("pending", []):
                            pending_map.setdefault("pending", []).append(name)
                            new_actions += 1
                
                day_data["exercises"].append({
                    "name": name,
                    "sets": sets,
                    "weight_display": weight_display,
                    "muscles": muscles,
                    "confidence": confidence
                })
                day_data["has_training"] = True

            # If no explicit body parts, infer from exercises
            if not day_data["body_parts"] and day_data["exercises"]:
                area_counts = {}
                for ex in day_data["exercises"]:
                    for m in ex["muscles"]:
                        area = m
                        if "胸" in m: area = "胸"
                        elif "背" in m: area = "背"
                        elif "股" in m or "臀" in m or "腘" in m or "小腿" in m: area = "腿"
                        elif "三角" in m: area = "肩"
                        elif "二头" in m or "三头" in m: area = "手臂"
                        elif "腹" in m: area = "腹"
                        elif "心肺" in m: area = "有氧"
                        area_counts[area] = area_counts.get(area, 0) + 1
                
                total_ex = len(day_data["exercises"])
                threshold = max(1, total_ex * 0.3)
                sorted_areas = sorted(area_counts.items(), key=lambda x: -x[1])
                for area, count in sorted_areas:
                    if count >= threshold or (len(day_data["body_parts"]) < 2 and count > 0):
                        day_data["body_parts"].append(area)

            day_data["body_parts"] = list(set(day_data["body_parts"]))
            days.append(day_data)
            parsed_ok += 1

        # 3. Merge duplicate dates with accumulative diet summing
        merged_days = {}
        for d in days:
            dt = d["date"]
            if dt not in merged_days:
                merged_days[dt] = d
            else:
                existing = merged_days[dt]
                existing["exercises"].extend(d["exercises"])
                existing["body_parts"] = list(set(existing["body_parts"] + d["body_parts"]))
                if d["has_training"]:
                    existing["has_training"] = True
                if d["weight_kg"] and not existing["weight_kg"]:
                    existing["weight_kg"] = d["weight_kg"]
                
                # Accumulative diet merge
                if d["diet"]:
                    if not existing["diet"]:
                        existing["diet"] = d["diet"]
                    else:
                        existing["diet"]["total_kcal"] += d["diet"].get("total_kcal", 0)
                        existing["diet"]["protein_g"] = round(existing["diet"].get("protein_g", 0) + d["diet"].get("protein_g", 0), 1)
                        existing["diet"]["carbs_g"] = round(existing["diet"].get("carbs_g", 0) + d["diet"].get("carbs_g", 0), 1)
                        existing["diet"]["fat_g"] = round(existing["diet"].get("fat_g", 0) + d["diet"].get("fat_g", 0), 1)
                parsed_ok -= 1
        days = list(merged_days.values())
        days.sort(key=lambda x: x["date"])

        # Merge daily weights into weight_log
        wl_dates = {w["date"] for w in weight_log}
        for day in days:
            if day["weight_kg"] and day["date"] not in wl_dates:
                weight_log.append({"date": day["date"], "weight_kg": day["weight_kg"]})
                wl_dates.add(day["date"])
        weight_log.sort(key=lambda x: x["date"])

        # Output payload
        data_out = {
            "meta": {
                "generated_at": datetime.now().isoformat(),
                "source_file": "/root/fitness_log.md",
                "source_hash": current_hash,
                "parse_summary": {
                    "total_days": parsed_ok + skipped,
                    "parsed_ok": parsed_ok,
                    "skipped": skipped,
                    "new_actions_unmapped": new_actions,
                    "errors": errors
                }
            },
            "weight_log": weight_log,
            "days": days,
            "profile": profile
        }
        
        if not dry_run:
            save_json(DATA_OUT, data_out)
            save_json(PENDING_FILE, pending_map)
            save_json(STATE_FILE, {"source_hash": current_hash, "updated_at": datetime.now().isoformat()})

            if os.path.exists(WEB_DATA_DIR):
                import shutil
                if os.path.exists(MAP_FILE):
                    shutil.copy2(MAP_FILE, os.path.join(WEB_DATA_DIR, 'exercise_map.json'))
                if os.path.exists(PENDING_FILE):
                    shutil.copy2(PENDING_FILE, os.path.join(WEB_DATA_DIR, 'exercise_map_pending.json'))
        
        print("📊 解析摘要")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"✅ 成功解析: {parsed_ok} 天")
        print(f"⚠️ 格式异常跳过: {skipped} 条")
        print(f"🆕 新动作待映射: {new_actions} 个")
        print(f"📁 输出: {DATA_OUT}" + (" (dry-run, 未落盘)" if dry_run else ""))
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━")

        # Auto-resolve pending exercise mappings
        auto_map = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'auto_map.py')
        if not dry_run and allow_auto_remap and os.path.exists(auto_map):
            import subprocess
            result = subprocess.run(['python3', auto_map], capture_output=True, text=True)
            if result.stdout.strip():
                print("\n🤖 自动映射:")
                print(result.stdout.strip())
            if '✅' in result.stdout:
                parse_log(allow_auto_remap=False)

    finally:
        if lock_fd:
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
                lock_fd.close()
            except:
                pass

if __name__ == '__main__':
    parse_log()
