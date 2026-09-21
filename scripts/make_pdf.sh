#!/usr/bin/env bash
# 제출용 제안서를 PDF 로 출력한다.
#
#   ./scripts/make_pdf.sh        → build/제안서.pdf
#
# 왜 Chrome 헤드리스인가
#   정본이 HTML(`public/doc/index.html`)이고 인쇄용 CSS(@page)가 이미 들어
#   있다. 같은 엔진으로 뽑아야 **화면에서 본 것과 같은 쪽 나눔**이 나온다.
#   변환 도구를 하나 더 들이면 표가 쪼개지는 자리가 달라진다.
#
# 실행 위치와 무관하게 이 저장소를 기준으로 한다 (docs INCIDENTS S3).
set -euo pipefail
cd "$(dirname "$0")/.."

CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
SRC="$PWD/public/doc/index.html"
OUT="$PWD/build/제안서.pdf"

[ -x "$CHROME" ] || { echo "✗ Chrome 을 찾지 못했습니다: $CHROME" >&2; exit 1; }
[ -f "$SRC" ]    || { echo "✗ 정본이 없습니다: $SRC" >&2; exit 1; }
mkdir -p build

"$CHROME" --headless --disable-gpu --no-pdf-header-footer \
  --print-to-pdf="$OUT" "file://$SRC" >/dev/null 2>&1

[ -s "$OUT" ] || { echo "✗ PDF 가 비어 있습니다." >&2; exit 1; }
printf "✓ %s  (%s)\n" "$OUT" "$(du -h "$OUT" | cut -f1)"
