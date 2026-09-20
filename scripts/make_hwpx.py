"""제출용 제안서를 한글(HWP) 계열 편집 포맷 .hwpx 로 만든다.

.hwpx 는 한컴이 공개한 OWPML 기반 개방형 표준이다. 한컴오피스 한글에서
바로 열리고, 거기서 '다른 이름으로 저장'으로 .hwp 를 만들 수 있다.
이진 .hwp 를 직접 쓰는 것보다 훨씬 안전해서 이쪽을 택했다.

외부 패키지를 쓰지 않는다. 표준 라이브러리 zipfile 로 OWPML 을 직접 쓴다.

    python3 scripts/make_hwpx.py [출력경로]
"""

import os
import sys
import zipfile
from xml.sax.saxutils import escape

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import doc_model as M

FONT = "맑은 고딕"

# ── 문자 모양 정의 ────────────────────────────────────────────
# (id, 크기(pt), 굵게, 색)  — header.xml 의 charProperties 와 순서가 같아야 한다
CHARS = [
    (0, 10.5, 0, "#111418"),   # 본문
    (1, 26.0, 1, "#111418"),   # 표지 제목
    (2, 11.0, 1, "#0F3D6E"),   # 표지 부제
    (3, 15.0, 1, "#111418"),   # 대제목
    (4, 11.5, 1, "#0F3D6E"),   # 중제목
    (5, 10.5, 1, "#111418"),   # 소제목
    (6, 10.0, 0, "#111418"),   # 상자 본문
    (7, 8.5, 0, "#6B7280"),    # 출처
    (8, 9.0, 0, "#111418"),    # 표 본문
    (9, 9.0, 1, "#3B4149"),    # 표 머리글
    (10, 11.0, 0, "#3B4149"),  # 표지 태그라인
]

# ── 문단 모양 정의 ────────────────────────────────────────────
# (id, 위여백, 아래여백, 왼들여쓰기, 테두리채우기id, 정렬)
PARAS = [
    (0, 0, 400, 0, 2, "JUSTIFY"),    # 본문
    (1, 300, 600, 0, 2, "LEFT"),     # 제목류 — 양쪽정렬하면 제목 자간이 벌어진다
    (2, 200, 500, 0, 3, "JUSTIFY"),  # 강조 상자 (파랑)
    (3, 200, 500, 0, 4, "JUSTIFY"),  # 주의 상자 (베이지)
    (4, 0, 300, 0, 2, "LEFT"),       # 출처
    (5, 0, 200, 800, 2, "JUSTIFY"),  # 목록
    (6, 0, 100, 0, 2, "LEFT"),       # 표 안
]

# borderFill: 1=없음(표 바깥) 2=투명 3=파랑상자 4=베이지상자 5=표선 6=표머리
NBF = 6


def bf_defs():
    """테두리·채우기 정의. 표와 강조상자가 이걸 참조한다."""
    def one(i, fill=None, left_accent=False, box=False):
        b = []
        b.append(f'<hh:borderFill id="{i}" threeD="0" shadow="0" centerLine="NONE" '
                 f'breakCellSeparateLine="0">')
        b.append('<hh:slash type="NONE" Crooked="0" isCounter="0"/>'
                 '<hh:backSlash type="NONE" Crooked="0" isCounter="0"/>')
        w = "0.12mm" if (box or i in (5, 6)) else "0.1mm"
        style = "SOLID" if (box or i in (5, 6)) else "NONE"
        lstyle = "SOLID" if (box or i in (5, 6)) else "NONE"
        lw = "0.5mm" if left_accent else w
        lcolor = "#0F3D6E" if left_accent else "#C8CCD2"
        b.append(f'<hh:leftBorder type="{lstyle}" width="{lw}" color="{lcolor}"/>')
        b.append(f'<hh:rightBorder type="{style}" width="{w}" color="#C8CCD2"/>')
        b.append(f'<hh:topBorder type="{style}" width="{w}" color="#C8CCD2"/>')
        b.append(f'<hh:bottomBorder type="{style}" width="{w}" color="#C8CCD2"/>')
        b.append('<hh:diagonal type="SOLID" width="0.1mm" color="#000000"/>')
        if fill:
            b.append('<hc:fillBrush><hc:winBrush faceColor="%s" hatchColor="#999999" '
                     'alpha="0"/></hc:fillBrush>' % fill)
        b.append("</hh:borderFill>")
        return "".join(b)

    return (
        one(1) + one(2) + one(3, fill="#EEF3F8", left_accent=True, box=True)
        + one(4, fill="#FBF3EC", left_accent=True, box=True)
        + one(5, box=True) + one(6, fill="#F4F6F8", box=True)
    )


def fontfaces():
    langs = ["HANGUL", "LATIN", "HANJA", "JAPANESE", "OTHER", "SYMBOL", "USER"]
    out = [f'<hh:fontfaces itemCnt="{len(langs)}">']
    for lg in langs:
        out.append(f'<hh:fontface lang="{lg}" fontCnt="1">')
        out.append(f'<hh:font id="0" face="{FONT}" type="TTF" isEmbedded="0">')
        out.append('<hh:typeInfo familyType="FCAT_GOTHIC" weight="6" proportion="4" '
                   'contrast="0" strokeVariation="1" armStyle="1" letterform="1" '
                   'midline="1" xHeight="1"/>')
        out.append("</hh:font></hh:fontface>")
    out.append("</hh:fontfaces>")
    return "".join(out)


def char_props():
    out = [f'<hh:charProperties itemCnt="{len(CHARS)}">']
    for cid, size, bold, color in CHARS:
        h = int(size * 100)
        out.append(
            f'<hh:charPr id="{cid}" height="{h}" textColor="{color}" '
            f'shadeColor="none" useFontSpace="0" useKerning="0" symMark="NONE" '
            f'borderFillIDRef="2">'
            '<hh:fontRef hangul="0" latin="0" hanja="0" japanese="0" other="0" symbol="0" user="0"/>'
            '<hh:ratio hangul="100" latin="100" hanja="100" japanese="100" other="100" symbol="100" user="100"/>'
            '<hh:spacing hangul="0" latin="0" hanja="0" japanese="0" other="0" symbol="0" user="0"/>'
            '<hh:relSz hangul="100" latin="100" hanja="100" japanese="100" other="100" symbol="100" user="100"/>'
            '<hh:offset hangul="0" latin="0" hanja="0" japanese="0" other="0" symbol="0" user="0"/>'
            + ("<hh:bold/>" if bold else "")
            + "</hh:charPr>"
        )
    out.append("</hh:charProperties>")
    return "".join(out)


def para_props():
    out = [f'<hh:paraProperties itemCnt="{len(PARAS)}">']
    for pid, before, after, indent, bfid, align in PARAS:
        out.append(
            f'<hh:paraPr id="{pid}" tabPrIDRef="0" condense="0" fontLineHeight="0" '
            f'snapToGrid="1" suppressLineNumbers="0" checked="0">'
            f'<hh:align horizontal="{align}" vertical="BASELINE"/>'
            '<hh:heading type="NONE" idRef="0" level="0"/>'
            '<hh:breakSetting breakLatinWord="KEEP_WORD" breakNonLatinWord="KEEP_WORD" '
            'widowOrphan="0" keepWithNext="0" keepLines="0" pageBreakBefore="0" '
            'lineWrap="BREAK"/>'
            '<hh:autoSpacing eAsianEng="0" eAsianNum="0"/>'
            f'<hh:switch><hh:case hp:required-namespace="http://www.hancom.co.kr/hwpml/2016/HwpUnitChar">'
            f'<hh:margin><hc:intent value="0" unit="HWPUNIT"/>'
            f'<hc:left value="{indent}" unit="HWPUNIT"/><hc:right value="0" unit="HWPUNIT"/>'
            f'<hc:prev value="{before}" unit="HWPUNIT"/><hc:next value="{after}" unit="HWPUNIT"/>'
            f'</hh:margin>'
            f'<hh:lineSpacing type="PERCENT" value="160" unit="HWPUNIT"/></hh:case>'
            f'<hh:default>'
            f'<hh:margin><hc:intent value="0" unit="HWPUNIT"/>'
            f'<hc:left value="{indent}" unit="HWPUNIT"/><hc:right value="0" unit="HWPUNIT"/>'
            f'<hc:prev value="{before}" unit="HWPUNIT"/><hc:next value="{after}" unit="HWPUNIT"/>'
            f'</hh:margin>'
            f'<hh:lineSpacing type="PERCENT" value="160" unit="HWPUNIT"/></hh:default></hh:switch>'
            f'<hh:border borderFillIDRef="{bfid}" offsetLeft="300" offsetRight="300" '
            f'offsetTop="200" offsetBottom="200" connect="0" ignoreMargin="0"/>'
            "</hh:paraPr>"
        )
    out.append("</hh:paraProperties>")
    return "".join(out)


HEAD = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<hh:head xmlns:hh="http://www.hancom.co.kr/hwpml/2011/head" xmlns:hc="http://www.hancom.co.kr/hwpml/2011/core" xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph" version="1.4" secCnt="1">
<hh:beginNum page="1" footnote="1" endnote="1" pic="1" tbl="1" equation="1"/>
<hh:refList>
{fontfaces}
<hh:borderFills itemCnt="{nbf}">{borderfills}</hh:borderFills>
{charprops}
<hh:tabProperties itemCnt="1"><hh:tabPr id="0" autoTabLeft="0" autoTabRight="0"/></hh:tabProperties>
<hh:numberings itemCnt="1"><hh:numbering id="0" start="0"/></hh:numberings>
{paraprops}
<hh:styles itemCnt="1"><hh:style id="0" type="PARA" name="바탕글" engName="Normal" paraPrIDRef="0" charPrIDRef="0" nextStyleIDRef="0" langID="1042" lockForm="0"/></hh:styles>
</hh:refList>
<hh:compatibleDocument targetProgram="HWP201X"><hh:layoutCompatibility/></hh:compatibleDocument>
</hh:head>"""

SECPR = """<hp:secPr id="" textDirection="HORIZONTAL" spaceColumns="1134" tabStop="8000" tabStopVal="4000" tabStopUnit="HWPUNIT" outlineShapeIDRef="0" memoShapeIDRef="0" textVerticalWidthHead="0" masterPageCnt="0">
<hp:grid lineGrid="0" charGrid="0" wonggojiFormat="0" strtnum="0"/>
<hp:startNum pageStartsOn="BOTH" page="0" pic="0" tbl="0" equation="0"/>
<hp:visibility hideFirstHeader="0" hideFirstFooter="0" hideFirstMasterPage="0" border="SHOW_ALL" fill="SHOW_ALL" hideFirstPageNum="0" hideFirstEmptyLine="0" showLineNumber="0"/>
<hp:pagePr landscape="WIDELY" width="59528" height="84188" gutterType="LEFT_ONLY">
<hp:margin header="4252" footer="4252" gutter="0" left="6236" right="6236" top="6803" bottom="6236"/>
</hp:pagePr>
<hp:footNotePr><hp:autoNumFormat type="DIGIT" userChar="" prefixChar="" suffixChar=")" supscript="0"/><hp:noteLine length="-1" type="SOLID" width="0.12mm" color="#000000"/><hp:noteSpacing betweenNotes="850" belowLine="567" aboveLine="850"/><hp:numbering type="CONTINUOUS" newNum="1"/><hp:placement place="EACH_COLUMN" beneathText="0"/></hp:footNotePr>
<hp:endNotePr><hp:autoNumFormat type="DIGIT" userChar="" prefixChar="" suffixChar=")" supscript="0"/><hp:noteLine length="14692344" type="SOLID" width="0.12mm" color="#000000"/><hp:noteSpacing betweenNotes="0" belowLine="567" aboveLine="850"/><hp:numbering type="CONTINUOUS" newNum="1"/><hp:placement place="END_OF_DOCUMENT" beneathText="0"/></hp:endNotePr>
<hp:pageBorderFill type="BOTH" borderFillIDRef="1" textBorder="PAPER" headerInside="0" footerInside="0" fillArea="PAPER"><hp:offset left="1417" right="1417" top="1417" bottom="1417"/></hp:pageBorderFill>
<hp:pageBorderFill type="EVEN" borderFillIDRef="1" textBorder="PAPER" headerInside="0" footerInside="0" fillArea="PAPER"><hp:offset left="1417" right="1417" top="1417" bottom="1417"/></hp:pageBorderFill>
<hp:pageBorderFill type="ODD" borderFillIDRef="1" textBorder="PAPER" headerInside="0" footerInside="0" fillArea="PAPER"><hp:offset left="1417" right="1417" top="1417" bottom="1417"/></hp:pageBorderFill>
</hp:secPr>"""

# 본문 영역 폭 (HWPUNIT): 59528 - 6236*2 = 47056
BODY_W = 47056


class Sec:
    def __init__(self):
        self.parts = []
        self.pid = 0
        self.first = True

    def p(self, text, char=0, parapr=0, page_break=False, inner=""):
        pb = "1" if page_break else "0"
        sec = SECPR if self.first else ""
        self.first = False
        run = f'<hp:run charPrIDRef="{char}">{sec}{inner}'
        if text:
            run += f"<hp:t>{escape(text)}</hp:t>"
        run += "</hp:run>"
        self.parts.append(
            f'<hp:p id="{self.pid}" paraPrIDRef="{parapr}" styleIDRef="0" '
            f'pageBreak="{pb}" columnBreak="0" merged="0">{run}'
            f'<hp:linesegarray><hp:lineseg textpos="0" vertpos="0" vertsize="1000" '
            f'textheight="1000" baseline="850" spacing="600" horzpos="0" '
            f'horzsize="{BODY_W}" flags="393216"/></hp:linesegarray></hp:p>'
        )
        self.pid += 1

    def table(self, rows):
        ncol = max(len(r) for r in rows)
        rows = [r + [""] * (ncol - len(r)) for r in rows]
        nrow = len(rows)

        if ncol == 1:
            widths = [BODY_W]
        elif ncol == 2:
            w0 = int(BODY_W * 0.28)
            widths = [w0, BODY_W - w0]
        else:
            w0 = int(BODY_W * 0.20)
            rest = (BODY_W - w0) // (ncol - 1)
            widths = [w0] + [rest] * (ncol - 1)
            widths[-1] = BODY_W - sum(widths[:-1])

        ROW_H = 1200   # 최소 높이. 내용이 길면 한글이 늘린다
        trs = []
        for ri, row in enumerate(rows):
            head = ri == 0 and ncol > 1
            tcs = []
            for ci, txt in enumerate(row):
                sub = (
                    f'<hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK" '
                    f'vertAlign="TOP" linkListIDRef="0" linkListNextIDRef="0" '
                    f'textWidth="0" textHeight="0" hasTextRef="0" hasNumRef="0">'
                    f'<hp:p id="0" paraPrIDRef="6" styleIDRef="0" pageBreak="0" '
                    f'columnBreak="0" merged="0">'
                    f'<hp:run charPrIDRef="{9 if head else 8}">'
                    f"<hp:t>{escape(txt)}</hp:t></hp:run>"
                    f"</hp:p></hp:subList>"
                )
                tcs.append(
                    f'<hp:tc name="" header="{"1" if head else "0"}" hasMargin="0" '
                    f'protect="0" editable="0" dirty="0" borderFillIDRef="{6 if head else 5}">'
                    + sub
                    + f'<hp:cellAddr colAddr="{ci}" rowAddr="{ri}"/>'
                    f'<hp:cellSpan colSpan="1" rowSpan="1"/>'
                    f'<hp:cellSz width="{widths[ci]}" height="{ROW_H}"/>'
                    f'<hp:cellMargin left="300" right="300" top="150" bottom="150"/>'
                    f"</hp:tc>"
                )
            trs.append(f'<hp:tr>{"".join(tcs)}</hp:tr>')

        tbl = (
            f'<hp:tbl id="{self.pid + 1000}" zOrder="0" numberingType="TABLE" '
            f'textWrap="TOP_AND_BOTTOM" textFlow="BOTH_SIDES" lock="0" dropcapstyle="None" '
            f'pageBreak="CELL" repeatHeader="1" rowCnt="{nrow}" colCnt="{ncol}" '
            f'cellSpacing="0" borderFillIDRef="5" noAdjust="0">'
            f'<hp:sz width="{BODY_W}" widthRelTo="ABSOLUTE" height="{ROW_H*nrow}" '
            f'heightRelTo="ABSOLUTE" protect="0"/>'
            f'<hp:pos treatAsChar="1" affectLSpacing="0" flowWithText="1" allowOverlap="0" '
            f'holdAnchorAndSO="0" vertRelTo="PARA" horzRelTo="COLUMN" vertAlign="TOP" '
            f'horzAlign="LEFT" vertOffset="0" horzOffset="0"/>'
            f'<hp:outMargin left="0" right="0" top="150" bottom="300"/>'
            f'<hp:inMargin left="300" right="300" top="150" bottom="150"/>'
            + "".join(trs)
            + "</hp:tbl>"
        )
        self.p("", char=8, parapr=6, inner=tbl)

    def xml(self):
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<hs:sec xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section" '
            'xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph" '
            'xmlns:hc="http://www.hancom.co.kr/hwpml/2011/core">'
            + "".join(self.parts)
            + "</hs:sec>"
        )


def build_section(blocks):
    s = Sec()
    brk = False
    for b in blocks:
        k = b.kind
        if k == M.PAGEBREAK:
            brk = True
            continue
        pb, brk = brk, False
        if k == M.COVER_SUB:
            s.p(b.text, char=2, parapr=1, page_break=pb)
        elif k == M.COVER_TITLE:
            s.p(b.text, char=1, parapr=1, page_break=pb)
        elif k == M.COVER_TAG:
            s.p(b.text, char=10, parapr=2, page_break=pb)
        elif k == M.H1:
            s.p(b.text, char=3, parapr=1, page_break=pb)
        elif k == M.H2:
            s.p(b.text, char=4, parapr=1, page_break=pb)
        elif k == M.H3:
            s.p(b.text, char=5, parapr=1, page_break=pb)
        elif k == M.PARA:
            s.p(b.text, char=0, parapr=0, page_break=pb)
        elif k == M.BOX:
            s.p(b.text, char=6, parapr=2, page_break=pb)
        elif k == M.WARNBOX:
            s.p(b.text, char=6, parapr=3, page_break=pb)
        elif k == M.SRC:
            s.p(b.text, char=7, parapr=4, page_break=pb)
        elif k == M.LIST:
            for it in b.items:
                s.p("· " + it, char=6, parapr=5)
        elif k == M.TABLE:
            if pb:
                s.p("", char=0, parapr=0, page_break=True)
            s.table(b.rows)
    return s


VERSION = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<hv:HCFVersion xmlns:hv="http://www.hancom.co.kr/hwpml/2011/version" tagetApplication="WORDPROCESSOR" major="5" minor="0" micro="5" buildNumber="0" os="1" xmlVersion="1.4" application="Hancom Office Hangul" appVersion="9, 1, 1, 5656 WIN32LEWindows_Unknown_Version"/>"""

CONTAINER = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<ocf:container xmlns:ocf="urn:oasis:names:tc:opendocument:xmlns:container" xmlns:hpf="http://www.hancom.co.kr/schema/2011/hpf">
<ocf:rootfiles>
<ocf:rootfile full-path="Contents/content.hpf" media-type="application/hwpml-package+xml"/>
</ocf:rootfiles>
</ocf:container>"""

MANIFEST = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<odf:manifest xmlns:odf="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0" version="1.2">
<odf:file-entry odf:full-path="/" odf:media-type="application/hwp+zip"/>
<odf:file-entry odf:full-path="version.xml" odf:media-type="application/xml"/>
<odf:file-entry odf:full-path="settings.xml" odf:media-type="application/xml"/>
<odf:file-entry odf:full-path="Contents/header.xml" odf:media-type="application/xml"/>
<odf:file-entry odf:full-path="Contents/section0.xml" odf:media-type="application/xml"/>
</odf:manifest>"""

CONTENT_HPF = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<opf:package xmlns:opf="http://www.idpf.org/2007/opf/" xmlns:ha="http://www.hancom.co.kr/hwpml/2011/app" xmlns:dc="http://purl.org/dc/elements/1.1/" version="" unique-identifier="" id="">
<opf:metadata>
<opf:title>제주 안심여행 세이프가디언 구축 사업 제안서</opf:title>
<opf:language>ko</opf:language>
<opf:meta name="creator" content=""/>
<opf:meta name="subject" content="제주특별자치도 관광객 안전관리 정보화사업 (제안)"/>
</opf:metadata>
<opf:manifest>
<opf:item id="header" href="Contents/header.xml" media-type="application/xml"/>
<opf:item id="section0" href="Contents/section0.xml" media-type="application/xml"/>
<opf:item id="settings" href="settings.xml" media-type="application/xml"/>
</opf:manifest>
<opf:spine>
<opf:itemref idref="header" linear="yes"/>
<opf:itemref idref="section0" linear="yes"/>
</opf:spine>
</opf:package>"""

SETTINGS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<ha:HWPApplicationSetting xmlns:ha="http://www.hancom.co.kr/hwpml/2011/app" xmlns:config="http://www.hancom.co.kr/hwpml/2011/configItem">
<ha:CaretPosition listIDRef="0" paraIDRef="0" pos="0"/>
</ha:HWPApplicationSetting>"""


def main():
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src = os.path.join(here, "public", "doc", "index.html")
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, "build", "제안서.hwpx")
    os.makedirs(os.path.dirname(out), exist_ok=True)

    blocks = M.parse(src)
    sec = build_section(blocks)
    head = HEAD.format(
        fontfaces=fontfaces(), nbf=NBF, borderfills=bf_defs(),
        charprops=char_props(), paraprops=para_props(),
    )
    preview = "\n".join(b.text for b in blocks if b.text)[:1000]

    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        # mimetype 은 반드시 첫 항목 · 무압축
        zi = zipfile.ZipInfo("mimetype")
        zi.compress_type = zipfile.ZIP_STORED
        z.writestr(zi, "application/hwp+zip")
        z.writestr("version.xml", VERSION)
        z.writestr("settings.xml", SETTINGS)
        z.writestr("Contents/content.hpf", CONTENT_HPF)
        z.writestr("Contents/header.xml", head)
        z.writestr("Contents/section0.xml", sec.xml())
        z.writestr("META-INF/container.xml", CONTAINER)
        z.writestr("META-INF/manifest.xml", MANIFEST)
        z.writestr("Preview/PrvText.txt", preview)

    print(f"생성: {out}")
    print(f"  문단 {sec.pid}개, {os.path.getsize(out):,} bytes")


if __name__ == "__main__":
    main()
