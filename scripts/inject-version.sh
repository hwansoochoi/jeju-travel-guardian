#!/usr/bin/env bash
# Vercel 빌드 단계에서 실행된다. 배포본이 자기 커밋을 스스로 알려주게 만든다.
#
# "정상 응답(200)"만 보는 확인은 확인이 아니다. 개발 브랜치에만 병합하고
# 배포 푸시를 빠뜨려도 이전 배포본이 계속 200을 돌려주기 때문이다.
#
# 이 스크립트는 절대 빌드를 실패시키지 않는다. 배포 확인용 부가 정보를 만드는
# 일이 사이트 배포 자체를 막아서는 안 된다.
set -u

mkdir -p public
printf '{\n  "commit": "%s",\n  "ref": "%s",\n  "builtAt": "%s"\n}\n' \
  "${VERCEL_GIT_COMMIT_SHA:-unknown}" \
  "${VERCEL_GIT_COMMIT_REF:-unknown}" \
  "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  > public/version.json

echo "version.json 생성: commit=${VERCEL_GIT_COMMIT_SHA:-unknown} ref=${VERCEL_GIT_COMMIT_REF:-unknown}"
