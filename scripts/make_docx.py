"""제출용 제안서를 편집 가능한 .docx 로 만든다.

public/doc/index.html 이 정본이고, 이 스크립트는 그것을 옮긴 사본을 만든다.
내용을 고칠 일이 생기면 HTML 을 고치고 이 스크립트를 다시 돌린다.

python-docx 같은 외부 패키지를 쓰지 않는다. 표준 라이브러리의 zipfile 로
OOXML 을 직접 쓴다. 설치 없이 어디서나 돌게 하려는 것이다.

    python3 scripts/make_docx.py [출력경로]
"""

import os
import sys
import zipfile
from xml.sax.saxutils import escape

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import doc_model as M

# 한글 본문에 쓸 글꼴. 한컴오피스·워드 양쪽에 있는 것으로 고른다.
FONT = "맑은 고딕"

NS = (
    'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
)


def rpr(size=None, bold=False, color=None):
    """문자 속성. size 는 pt 단위."""
    out = [f'<w:rFonts w:ascii="{FONT}" w:hAnsi="{FONT}" w:eastAsia="{FONT}" w:cs="{FONT}"/>']
    if bold:
        out.append("<w:b/><w:bCs/>")
    if color:
        out.append(f'<w:color w:val="{color}"/>')
    if size:
        half = int(size * 2)
        out.append(f'<w:sz w:val="{half}"/><w:szCs w:val="{half}"/>')
    return "<w:rPr>" + "".join(out) + "</w:rPr>"


def para(text, size=10.5, bold=False, color=None, align=None, space_before=0,
         space_after=80, shade=None, border=False, indent=0, page_break=False,
         line=276):
    """문단 하나를 만든다. 단위: space 는 twip, indent 는 twip.

    page_break 는 빈 문단을 넣지 않고 이 문단 자체를 새 쪽에서 시작시킨다.
    빈 문단을 쓰면 편집할 때 지워야 할 군더더기가 남는다.
    """
    ppr = ["<w:widowControl/>"]
    if page_break:
        ppr.append("<w:pageBreakBefore/>")
    if shade:
        ppr.append(f'<w:shd w:val="clear" w:color="auto" w:fill="{shade}"/>')
    if border:
        ppr.append(
            '<w:pBdr>'
            '<w:top w:val="single" w:sz="4" w:space="6" w:color="C8CCD2"/>'
            '<w:left w:val="single" w:sz="18" w:space="6" w:color="0F3D6E"/>'
            '<w:bottom w:val="single" w:sz="4" w:space="6" w:color="C8CCD2"/>'
            '<w:right w:val="single" w:sz="4" w:space="6" w:color="C8CCD2"/>'
            "</w:pBdr>"
        )
    if indent:
        ppr.append(f'<w:ind w:left="{indent}"/>')
    ppr.append(f'<w:spacing w:before="{space_before}" w:after="{space_after}" '
               f'w:line="{line}" w:lineRule="auto"/>')
    if align:
        ppr.append(f'<w:jc w:val="{align}"/>')
    ppr.append(rpr(size, bold, color).replace("w:rPr", "w:rPr", 1))

    runs = ""
    if text:
        runs += (f"<w:r>{rpr(size, bold, color)}"
                 f'<w:t xml:space="preserve">{escape(text)}</w:t></w:r>')
    return f"<w:p><w:pPr>{''.join(ppr)}</w:pPr>{runs}</w:p>"


def cell(text, width, header=False, size=9, align=None):
    shade = "F4F6F8" if header else None
    tcpr = [f'<w:tcW w:w="{width}" w:type="dxa"/>']
    if shade:
        tcpr.append(f'<w:shd w:val="clear" w:color="auto" w:fill="{shade}"/>')
    tcpr.append('<w:vAlign w:val="top"/>')
    body = para(text, size=size, bold=header, align=align,
                space_after=20, line=252)
    return f"<w:tc><w:tcPr>{''.join(tcpr)}</w:tcPr>{body}</w:tc>"


def table(rows, total_width=9300):
    """첫 행을 머리글로 본다. 열 너비는 균등 배분하되 첫 열을 조금 좁게."""
    ncol = max(len(r) for r in rows)
    rows = [r + [""] * (ncol - len(r)) for r in rows]

    if ncol == 1:
        widths = [total_width]
    elif ncol == 2:
        widths = [int(total_width * 0.28), total_width - int(total_width * 0.28)]
    else:
        first = int(total_width * 0.20)
        rest = (total_width - first) // (ncol - 1)
        widths = [first] + [rest] * (ncol - 1)
        widths[-1] = total_width - sum(widths[:-1])

    grid = "".join(f'<w:gridCol w:w="{w}"/>' for w in widths)
    border = (
        '<w:tblBorders>'
        + "".join(
            f'<w:{s} w:val="single" w:sz="4" w:space="0" w:color="C8CCD2"/>'
            for s in ("top", "left", "bottom", "right", "insideH", "insideV")
        )
        + "</w:tblBorders>"
    )
    tblpr = (
        "<w:tblPr>"
        f'<w:tblW w:w="{total_width}" w:type="dxa"/>'
        '<w:tblLayout w:type="fixed"/>'
        + border
        + '<w:tblCellMar>'
        '<w:top w:w="60" w:type="dxa"/><w:left w:w="90" w:type="dxa"/>'
        '<w:bottom w:w="60" w:type="dxa"/><w:right w:w="90" w:type="dxa"/>'
        "</w:tblCellMar>"
        "</w:tblPr>"
    )

    out = [tblpr, f"<w:tblGrid>{grid}</w:tblGrid>"]
    for i, row in enumerate(rows):
        head = i == 0 and ncol > 1
        trpr = '<w:trPr><w:tblHeader/></w:trPr>' if head else ""
        cells = "".join(cell(c, widths[j], header=head) for j, c in enumerate(row))
        out.append(f"<w:tr>{trpr}{cells}</w:tr>")
    return "<w:tbl>" + "".join(out) + "</w:tbl>" + para("", space_after=100)


def build_body(blocks):
    out = []
    brk = False          # 다음 블록을 새 쪽에서 시작할지
    for b in blocks:
        k = b.kind
        if k == M.PAGEBREAK:
            brk = True
            continue
        pb, brk = brk, False
        if k == M.TABLE and pb:
            # 표에는 pageBreakBefore 를 걸 수 없어 앞에 빈 문단을 둔다
            out.append(para("", page_break=True, space_after=0))
            pb = False
        if k == M.COVER_SUB:
            out.append(para(b.text, size=11, bold=True, color="0F3D6E", space_after=120, page_break=pb))
        elif k == M.COVER_TITLE:
            out.append(para(b.text, size=26, bold=True, space_after=200, line=300, page_break=pb))
        elif k == M.COVER_TAG:
            out.append(para(b.text, size=11, border=True, shade="EEF3F8",
                            space_after=300, indent=0, page_break=pb))
        elif k == M.H1:
            out.append(para(b.text, size=15, bold=True, space_before=240,
                            space_after=140, color="111418", page_break=pb))
        elif k == M.H2:
            out.append(para(b.text, size=11.5, bold=True, color="0F3D6E",
                            space_before=200, space_after=90, page_break=pb))
        elif k == M.H3:
            out.append(para(b.text, size=10.5, bold=True, space_before=140, space_after=70, page_break=pb))
        elif k == M.PARA:
            out.append(para(b.text, page_break=pb))
        elif k == M.BOX:
            out.append(para(b.text, size=10, shade="EEF3F8", border=True,
                            space_before=60, space_after=140, page_break=pb))
        elif k == M.WARNBOX:
            out.append(para(b.text, size=10, shade="FBF3EC", border=True,
                            space_before=60, space_after=140, page_break=pb))
        elif k == M.SRC:
            out.append(para(b.text, size=8.5, color="6B7280", space_after=140, page_break=pb))
        elif k == M.LIST:
            for it in b.items:
                out.append(para("· " + it, size=10, indent=220, space_after=40))
            out.append(para("", space_after=80))
        elif k == M.TABLE:
            out.append(table(b.rows))
    return "".join(out)


DOC_TMPL = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document {ns}><w:body>{body}<w:sectPr>
<w:pgSz w:w="11906" w:h="16838"/>
<w:pgMar w:top="1134" w:right="1021" w:bottom="1021" w:left="1021"
         w:header="709" w:footer="709" w:gutter="0"/>
<w:cols w:space="425"/><w:docGrid w:linePitch="360"/>
</w:sectPr></w:body></w:document>"""

STYLES = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles {NS}>
<w:docDefaults><w:rPrDefault><w:rPr>
<w:rFonts w:ascii="{FONT}" w:hAnsi="{FONT}" w:eastAsia="{FONT}" w:cs="{FONT}"/>
<w:sz w:val="21"/><w:szCs w:val="21"/>
</w:rPr></w:rPrDefault>
<w:pPrDefault><w:pPr><w:widowControl/>
<w:spacing w:after="80" w:line="276" w:lineRule="auto"/>
</w:pPr></w:pPrDefault></w:docDefaults>
<w:style w:type="paragraph" w:default="1" w:styleId="Normal">
<w:name w:val="Normal"/><w:qFormat/></w:style>
</w:styles>"""

CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>"""

RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>"""

DOC_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""

CORE = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
 xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/"
 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
<dc:title>제주 안심여행 세이프가디언 구축 사업 제안서</dc:title>
<dc:subject>제주특별자치도 관광객 안전관리 정보화사업 (제안)</dc:subject>
<cp:revision>1</cp:revision>
</cp:coreProperties>"""

APP = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">
<Application>Microsoft Office Word</Application>
</Properties>"""


def main():
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src = os.path.join(here, "public", "doc", "index.html")
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, "build", "제안서.docx")
    os.makedirs(os.path.dirname(out), exist_ok=True)

    blocks = M.parse(src)
    body = build_body(blocks)
    document = DOC_TMPL.format(ns=NS, body=body)

    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CONTENT_TYPES)
        z.writestr("_rels/.rels", RELS)
        z.writestr("word/document.xml", document)
        z.writestr("word/styles.xml", STYLES)
        z.writestr("word/_rels/document.xml.rels", DOC_RELS)
        z.writestr("docProps/core.xml", CORE)
        z.writestr("docProps/app.xml", APP)

    ntab = sum(1 for b in blocks if b.kind == M.TABLE)
    print(f"생성: {out}")
    print(f"  블록 {len(blocks)}개 (표 {ntab}개), {os.path.getsize(out):,} bytes")


if __name__ == "__main__":
    main()
