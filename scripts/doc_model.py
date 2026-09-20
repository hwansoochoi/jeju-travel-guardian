"""제출용 제안서 HTML 을 편집 가능한 문서 형식으로 옮기기 위한 중간 표현.

public/doc/index.html 이 정본이다. 이 모듈은 그 HTML 을 읽어
블록 목록(제목 · 문단 · 표 · 강조상자 · 목록)으로 바꾼다.
docx / hwpx 생성기가 이 목록을 공유한다.

표준 라이브러리만 쓴다. 외부 패키지를 설치하지 않는다.
"""

import html
import re
from html.parser import HTMLParser

# 블록 종류
H1, H2, H3 = "h1", "h2", "h3"
PARA = "para"          # 일반 문단
BOX = "box"            # 강조 상자 (.lead / .note)
WARNBOX = "warnbox"    # 주의 상자 (.note.warn)
SRC = "src"            # 출처 각주
TABLE = "table"        # 표 — rows[0] 이 머리글
LIST = "list"          # 목록
PAGEBREAK = "pagebreak"
COVER_TITLE = "covertitle"
COVER_SUB = "coversub"
COVER_TAG = "covertag"


class Block:
    def __init__(self, kind, text="", rows=None, items=None, bold=False):
        self.kind = kind
        self.text = text
        self.rows = rows or []      # TABLE: [[cell, ...], ...]
        self.items = items or []    # LIST
        self.bold = bold

    def __repr__(self):
        return f"<{self.kind} {self.text[:36]!r}>"


def _clean(s):
    """개행을 포함한 연속 공백을 하나로 줄이고 앞뒤를 자른다."""
    return re.sub(r"\s+", " ", s).strip()


class DocParser(HTMLParser):
    """제안서 HTML 전용 파서.

    화면 전용 요소(.screen-only)는 버리고, 인쇄에 나오는 것만 남긴다.
    """

    SKIP_TAGS = {"script", "style", "head"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.blocks = []
        self._skip_depth = 0
        self._buf = []            # 현재 수집 중인 텍스트
        self._mode = None         # 현재 블록 종류
        self._tag_stack = []
        self._div_depth = 0       # kpi-row 안에서의 div 깊이
        # 표 수집 상태
        self._table = None
        self._row = None
        self._cell = None
        # 목록 수집 상태
        self._list = None
        # KPI 카드 수집 상태
        self._kpis = None
        self._kpi = None

    # ── 유틸 ────────────────────────────────────────────────
    def _classes(self, attrs):
        d = dict(attrs)
        return set((d.get("class") or "").split())

    def _flush(self):
        """모아둔 텍스트를 블록으로 확정한다."""
        text = _clean("".join(self._buf))
        self._buf = []
        mode, self._mode = self._mode, None
        if not text or mode is None:
            return
        if mode in (H1, H2):
            # "1.제안 요약" 처럼 번호와 제목이 붙는 것을 띄운다
            text = re.sub(r"^((?:부록\s*)?\d+\.)(?=\S)", r"\1 ", text)
        self.blocks.append(Block(mode, text))

    # ── 시작 태그 ───────────────────────────────────────────
    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP_TAGS:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return

        if tag == "br":
            self.handle_data(" ")
            return

        cls = self._classes(attrs)
        self._tag_stack.append((tag, cls))

        if "screen-only" in cls:
            self._skip_depth += 1
            return

        # ── 표 ──
        if tag == "table":
            self._flush()
            self._table = {"rows": [], "cover": "cover-meta" in cls}
            return
        if tag == "tr" and self._table is not None:
            self._row = []
            return
        if tag in ("td", "th") and self._row is not None:
            self._cell = []
            return
        if tag == "caption":
            self._flush()
            self._mode = PARA
            return

        # 표 안에서는 아래 처리를 건너뛴다 (셀 텍스트로 흡수)
        if self._cell is not None:
            return

        # ── KPI 카드 ──
        if "kpi-row" in cls:
            self._flush()
            self._kpis = []
            self._div_depth = 0
            return
        if self._kpis is not None:
            if tag == "div":
                self._div_depth += 1
                if self._div_depth == 1:      # 카드 한 장 시작
                    self._kpi = []
                elif "l" in cls and self._kpi:  # 수치 다음의 설명줄
                    self._kpi.append(" — ")
            return

        # ── 목록 ──
        if tag in ("ul", "ol"):
            self._flush()
            self._list = []
            return
        if tag == "li" and self._list is not None:
            self._flush()
            self._mode = "li"
            return

        # ── 제목 · 문단 · 상자 ──
        if tag == "section":
            self._flush()
            self.blocks.append(Block(PAGEBREAK))
            return
        if tag == "h1":
            self._flush()
            self._mode = COVER_TITLE
            return
        if tag == "h2":
            self._flush()
            self._mode = H1
            return
        if tag == "h3":
            self._flush()
            self._mode = H2
            return
        if tag == "h4":
            self._flush()
            self._mode = H3
            return
        if tag == "small" and self._mode == COVER_TITLE:
            # 표지 부제 — 본 제목과 분리한다
            self._flush()
            self._mode = COVER_SUB
            return
        if tag == "p" or tag == "div":
            if "lead" in cls:
                self._flush()
                self._mode = BOX
            elif "note" in cls:
                self._flush()
                self._mode = WARNBOX if "warn" in cls else BOX
            elif "src" in cls:
                self._flush()
                self._mode = SRC
            elif "sign" in cls:
                self._flush()
                self._mode = SRC
            elif "tagline" in cls:
                self._flush()
                self._mode = COVER_TAG
            elif "doc-kind" in cls:
                self._flush()
                self._mode = COVER_SUB
            elif "cover-foot" in cls:
                self._flush()
                self._mode = SRC
            elif tag == "p" and self._mode is None:
                self._mode = PARA
            return

    # ── 끝 태그 ─────────────────────────────────────────────
    def handle_endtag(self, tag):
        if tag in self.SKIP_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)
            return

        # screen-only 블록 종료 감지
        if self._tag_stack:
            t, cls = self._tag_stack[-1]
            if t == tag and "screen-only" in cls and self._skip_depth:
                self._skip_depth -= 1
                self._tag_stack.pop()
                return
        if self._skip_depth:
            return
        if self._tag_stack and self._tag_stack[-1][0] == tag:
            self._tag_stack.pop()

        if tag in ("td", "th") and self._cell is not None:
            self._row.append(_clean("".join(self._cell)))
            self._cell = None
            return
        if tag == "tr" and self._row is not None:
            if any(c for c in self._row):
                self._table["rows"].append(self._row)
            self._row = None
            return
        if tag == "table" and self._table is not None:
            if self._table["rows"]:
                self.blocks.append(Block(TABLE, rows=self._table["rows"]))
            self._table = None
            return
        if self._cell is not None:
            return

        if self._kpis is not None and tag == "div":
            if self._div_depth == 0:          # kpi-row 자체가 닫힘
                if self._kpis:
                    self.blocks.append(Block(TABLE, rows=[self._kpis]))
                self._kpis = None
                return
            self._div_depth -= 1
            if self._div_depth == 0 and self._kpi is not None:
                txt = _clean("".join(self._kpi))
                if txt:
                    self._kpis.append(txt)
                self._kpi = None
            return

        if tag == "li" and self._list is not None:
            txt = _clean("".join(self._buf))
            self._buf = []
            self._mode = None
            if txt:
                self._list.append(txt)
            return
        if tag in ("ul", "ol") and self._list is not None:
            if self._list:
                self.blocks.append(Block(LIST, items=self._list))
            self._list = None
            return

        if tag == "small":
            self._flush()
            # 표지 h1 안의 부제가 끝나면 본 제목 수집을 재개한다
            if any(t == "h1" for t, _ in self._tag_stack):
                self._mode = COVER_TITLE
            return
        if tag in ("h1", "h2", "h3", "h4", "p", "div", "caption"):
            self._flush()

    def handle_startendtag(self, tag, attrs):
        """<br /> 가 단어를 붙여버리지 않도록 공백으로 바꾼다."""
        if tag == "br":
            self.handle_data(" ")
        else:
            super().handle_startendtag(tag, attrs)

    # ── 텍스트 ──────────────────────────────────────────────
    def handle_data(self, data):
        if self._skip_depth:
            return
        if self._cell is not None:
            self._cell.append(data)
        elif self._kpi is not None:
            self._kpi.append(data)
        elif self._mode is not None:
            self._buf.append(data)


def parse(path):
    """HTML 파일을 블록 목록으로 바꾼다."""
    with open(path, encoding="utf-8") as f:
        src = f.read()
    # 스타일·스크립트를 미리 제거해 파서 부담을 줄인다
    src = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", src, flags=re.S)
    p = DocParser()
    p.feed(src)
    p._flush()

    # 빈 블록과 연속 페이지나눔 정리
    out = []
    for b in p.blocks:
        if b.kind == PAGEBREAK:
            if out and out[-1].kind == PAGEBREAK:
                continue
            if not out:
                continue
        if b.kind in (PARA, BOX, WARNBOX, SRC, H1, H2, H3) and not b.text:
            continue
        out.append(b)
    return out


if __name__ == "__main__":
    import sys
    from collections import Counter

    blocks = parse(sys.argv[1] if len(sys.argv) > 1 else "public/doc/index.html")
    print("블록 수:", len(blocks))
    print(Counter(b.kind for b in blocks))
    for b in blocks[:40]:
        if b.kind == TABLE:
            print(f"  TABLE {len(b.rows)}행 x {len(b.rows[0])}열 | {b.rows[0][:3]}")
        elif b.kind == LIST:
            print(f"  LIST {len(b.items)}개 | {b.items[0][:50]}")
        else:
            print(f"  {b.kind:10s} {b.text[:70]}")
