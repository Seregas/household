#!/bin/zsh
# remote-build.sh — збірка на Mac mini M4 (home-srv, ~20% швидше на ядро).
# Використання: cad/remote-build.sh [floor front walls assembly ...]
#   без аргументів = повний ланцюг: floor front walls assembly
# Синхронізує cad/*.py туди, збирає, забирає out/ назад.
set -e
HOST=home-srv
RDIR="~/3d-modeling"
cd "$(dirname "$0")/.."
targets=("$@")
[ ${#targets[@]} -eq 0 ] && targets=(floor front walls assembly)

rsync -a --delete cad/ ${HOST}:${RDIR}/cad/
cmd="cd ${RDIR}"
for t in "${targets[@]}"; do
  cmd+=" && .venv/bin/python cad/${t}.py"
done
ssh ${HOST} "$cmd"
rsync -a ${HOST}:${RDIR}/out/ out/
echo "=== ГОТОВО (remote: ${targets[*]}) ==="
