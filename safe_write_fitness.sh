#!/bin/bash
# 安全写入健身日志 — 自动排他锁 + 双轨备份 + 解析校验
# 用法: /root/scripts/safe_write_fitness.sh <new_content_file>
#       cat new.txt | /root/scripts/safe_write_fitness.sh

FITNESS_FILE="/root/fitness_log.md"
BACKUP_DIR="/root/fitness_backups"
LOCK_FILE="/tmp/fitness_sync.lock"
MAX_BACKUPS=15
MAX_DAILY_BASELINES=30

# 0. 获取排他文件锁，杜绝与 cron 定时解析并发冲突
exec 200>"$LOCK_FILE"
if ! flock -x -w 10 200; then
    echo "❌ 无法获取文件锁 (等待 10s 超时)，可能另一个解析或写入任务正在进行"
    exit 1
fi
export FITNESS_SYNC_LOCKED=1

# 解锁文件
chattr -i "$FITNESS_FILE" 2>/dev/null

# 1. 双轨备份机制
mkdir -p "$BACKUP_DIR"
TODAY_DATE=$(date +%Y%m%d)
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# 1.1 每日基线备份（每天首次写入保留一份，保留 30 天）
if [ -f "$FITNESS_FILE" ] && [ ! -f "$BACKUP_DIR/daily_baseline_${TODAY_DATE}.bak" ]; then
    cp "$FITNESS_FILE" "$BACKUP_DIR/daily_baseline_${TODAY_DATE}.bak"
fi
ls -t "$BACKUP_DIR"/daily_baseline_*.bak 2>/dev/null | tail -n +$((MAX_DAILY_BASELINES+1)) | xargs rm -f 2>/dev/null

# 1.2 实时操作备份（保留最近 15 次快照）
if [ -f "$FITNESS_FILE" ]; then
    cp "$FITNESS_FILE" "$BACKUP_DIR/fitness_log_${TIMESTAMP}.bak"
fi
ls -t "$BACKUP_DIR"/fitness_log_*.bak 2>/dev/null | tail -n +$((MAX_BACKUPS+1)) | xargs rm -f 2>/dev/null

# 2. 获取当前解析天数作为基准
OLD_DAYS=$(python3 /root/scripts/parse_fitness.py --dry-run 2>&1 | grep -oP '成功解析: \K\d+' | head -1)

# 3. 写入新内容
if [ -n "$1" ] && [ -f "$1" ]; then
    cat "$1" > "$FITNESS_FILE"
else
    cat > "$FITNESS_FILE"
fi

# 4. 校验（带 --force 参数强制重新落盘）
NEW_RESULT=$(python3 /root/scripts/parse_fitness.py --force 2>&1)
NEW_DAYS=$(echo "$NEW_RESULT" | grep -oP '成功解析: \K\d+' | head -1)

if [ -z "$NEW_DAYS" ] || { [ -n "$OLD_DAYS" ] && [ "$NEW_DAYS" -lt "$OLD_DAYS" ]; }; then
    # 5. 校验失败 — 回滚
    LATEST_BAK=$(ls -t "$BACKUP_DIR"/fitness_log_*.bak 2>/dev/null | head -1)
    if [ -n "$LATEST_BAK" ]; then
        cp "$LATEST_BAK" "$FITNESS_FILE"
        echo "❌ 写入被拒绝：解析天数从 $OLD_DAYS 降到 $NEW_DAYS，已回滚"
        echo "备份保留在: $LATEST_BAK"
        chattr +i "$FITNESS_FILE" 2>/dev/null
        exit 1
    fi
    echo "❌ 写入被拒绝且无备份可回滚！"
    chattr +i "$FITNESS_FILE" 2>/dev/null
    exit 2
fi

echo "✅ 写入成功，$NEW_DAYS 天数据，备份: fitness_log_${TIMESTAMP}.bak"
chattr +i "$FITNESS_FILE" 2>/dev/null
exit 0
