#!/bin/zsh
# pull-out.sh — забрати свіжі STEP/STL з Mac mini (home-srv) на цю машину.
# Використання (з макбука): cad/pull-out.sh   → оновлює локальний out/
set -e
cd "$(dirname "$0")/.."
echo "=== старт: $(date '+%Y-%m-%d %H:%M:%S') ==="
rsync -av home-srv:'~/Projects/Household/house/home-servers/3d-modeling/out/' out/ | grep -v '/$' || true
echo "=== out/ оновлено з mini: $(date '+%Y-%m-%d %H:%M:%S') ==="
