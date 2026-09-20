#!/usr/bin/env bash
# 배포 확인. 운영 서버가 알려주는 커밋을 저장소와 대조한다.
#
#   ./scripts/verify-deploy.sh                 # 기본 도메인, origin/main 과 대조
#   ./scripts/verify-deploy.sh <url> <branch>
#
# 불일치면 실패(exit 1)로 끝낸다. 사람이 눈으로 넘기지 못하게 하려는 것이다.
set -uo pipefail

BASE="${1:-https://jeju-travel-guardian.vercel.app}"
BRANCH="${2:-main}"
ok()   { printf "  \033[32m✓\033[0m %s\n" "$1"; }
bad()  { printf "  \033[31m✗\033[0m %s\n" "$1"; FAILED=1; }
FAILED=0

echo "== 배포 확인 ($BASE) =="

git fetch -q origin "$BRANCH" 2>/dev/null || true
EXPECTED=$(git rev-parse "origin/$BRANCH" 2>/dev/null || echo "")
[ -n "$EXPECTED" ] || { echo "  origin/$BRANCH 를 찾을 수 없습니다." >&2; exit 1; }

BODY=$(curl -fsS -m 15 "$BASE/version.json" 2>/dev/null || echo "")
if [ -z "$BODY" ]; then
  bad "version.json 을 받지 못했습니다 — 빌드 단계가 돌지 않았거나 아직 배포 전입니다"
else
  DEPLOYED=$(printf '%s' "$BODY" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("commit",""))' 2>/dev/null || echo "")
  BUILT=$(printf '%s' "$BODY" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("builtAt",""))' 2>/dev/null || echo "")
  if [ "$DEPLOYED" = "$EXPECTED" ]; then
    ok "커밋 일치 ${DEPLOYED:0:8}  (빌드 $BUILT)"
  else
    bad "커밋 불일치"
    echo "      저장소 origin/$BRANCH : ${EXPECTED:0:8}"
    echo "      배포본              : ${DEPLOYED:0:8}  (빌드 $BUILT)"
    echo "      → 배포가 반영되지 않았습니다. 푸시했는지, 빌드가 성공했는지 확인하십시오."
  fi
fi

# 공개 페이지가 실제로 살아 있는지도 함께 본다.
for path in "/" "/v2/" "/review/" "/review-deck/"; do
  CODE=$(curl -s -o /dev/null -m 15 -w "%{http_code}" "$BASE$path")
  [ "$CODE" = "200" ] && ok "$path ($CODE)" || bad "$path ($CODE)"
done

[ "$FAILED" -eq 0 ] && { echo "== 배포 확인 통과 =="; exit 0; }
echo "== 배포 확인 실패 ==" >&2
exit 1
