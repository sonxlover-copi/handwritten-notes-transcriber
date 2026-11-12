#!/usr/bin/env bash
set -euo pipefail

compose_files=(-f compose.yaml)
if [[ "${1:-}" == "gpu" ]]; then
  compose_files+=(-f compose.gpu.yaml)
elif [[ -n "${1:-}" ]]; then
  echo "Использование: ./start.sh [gpu]" >&2
  exit 2
fi

docker compose "${compose_files[@]}" up --build -d

app_url="http://127.0.0.1:8000"
for _ in {1..60}; do
  if curl --silent --fail "$app_url/health" >/dev/null; then
    if command -v xdg-open >/dev/null 2>&1; then
      xdg-open "$app_url" >/dev/null 2>&1 || true
    else
      echo "Откройте приложение в браузере: $app_url"
    fi
    exit 0
  fi
  sleep 1
done

echo "Приложение не запустилось за минуту. Посмотрите логи: docker compose logs app" >&2
exit 1
