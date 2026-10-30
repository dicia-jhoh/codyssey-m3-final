#!/usr/bin/env bash
set -euo pipefail

BASE="${1:-http://localhost:8037}"
BASE="${BASE%/}"
SMOKE_PYTHON="${SMOKE_PYTHON:-python3}"
body=$(mktemp)
trap 'rm -f "$body"' EXIT

fail() { printf '[FAIL] %s\n' "$*" >&2; exit 1; }
check() {
    local path=$1 expected=$2 status
    shift 2
    status=$(curl --connect-timeout 5 --max-time 15 -sS -o "$body" -w '%{http_code}' "$@" "$BASE$path") \
        || fail "$path 연결 실패"
    [[ "$status" == "$expected" ]] || fail "$path: HTTP $status (기대 $expected)"
    printf '[OK] %s HTTP %s\n' "$path" "$status"
}

check /health 200
"$SMOKE_PYTHON" - "$body" <<'PY' || fail '/health JSON 또는 ok 값 오류'
import json, sys
with open(sys.argv[1], encoding="utf-8") as source:
    health = json.load(source)
if health.get("ok") is not True:
    raise SystemExit(1)
print("[OK] health ok=true, commit=" + str(health.get("commit", "unknown")))
PY
check /app 307
check /app/ 200
check / 200
check /decode 400 -F 'file=@-;filename=empty.jpg;type=image/jpeg' < /dev/null
check /share/no-such-share 404
printf '[OK] 배포 확인 완료\n'
