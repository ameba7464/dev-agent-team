#!/usr/bin/env bash
# reset.sh — очищает артефакты предыдущего прогона и восстанавливает структуру

set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
RUNTIME="$ROOT/agent-runtime"

echo "Cleaning agent-runtime..."

# Удаляем содержимое (файлы и вложенные папки), сохраняем шаблоны и .gitkeep
find "$RUNTIME/shared"    -mindepth 1 ! -name ".gitkeep" ! -name "brief.template.md" -delete
find "$RUNTIME/messages"  -mindepth 1 ! -name ".gitkeep" ! -name "message-template.md" -delete
find "$RUNTIME/state"     -mindepth 1 ! -name ".gitkeep" -delete
find "$RUNTIME/outputs/backend"        -mindepth 1 ! -name ".gitkeep" -delete
find "$RUNTIME/outputs/frontend"       -mindepth 1 ! -name ".gitkeep" -delete
find "$RUNTIME/outputs/tests/backend"  -mindepth 1 ! -name ".gitkeep" -delete
find "$RUNTIME/outputs/tests/frontend" -mindepth 1 ! -name ".gitkeep" -delete

# Восстанавливаем директории на случай если были удалены
mkdir -p \
  "$RUNTIME/shared" \
  "$RUNTIME/messages" \
  "$RUNTIME/state" \
  "$RUNTIME/outputs/backend" \
  "$RUNTIME/outputs/frontend" \
  "$RUNTIME/outputs/tests/backend" \
  "$RUNTIME/outputs/tests/frontend"

# Восстанавливаем .gitkeep если вдруг пропали
touch \
  "$RUNTIME/shared/.gitkeep" \
  "$RUNTIME/messages/.gitkeep" \
  "$RUNTIME/state/.gitkeep" \
  "$RUNTIME/outputs/backend/.gitkeep" \
  "$RUNTIME/outputs/frontend/.gitkeep" \
  "$RUNTIME/outputs/tests/backend/.gitkeep" \
  "$RUNTIME/outputs/tests/frontend/.gitkeep"

echo "Done. agent-runtime is clean and ready for a new run."
echo ""
echo "Next steps:"
echo "  1. Copy the brief template and fill it in:"
echo "     cp agent-runtime/shared/brief.template.md agent-runtime/shared/brief.md"
echo "  2. (Optional) Edit stack.md to override the default tech stack"
echo "  3. Run: tmux new-session -s main && claude"
