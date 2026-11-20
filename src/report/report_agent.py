import logging
import re
import time
import uuid
from datetime import date
from pathlib import Path

from langchain.agents import create_agent
from langchain_core.tools import tool
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4, LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from src.llm import get_llm
from src.report.arabic import arabic_lines, has_arabic

REPORTS_DIR = Path("data/reports")
logger = logging.getLogger("report")

# the names an LLM may use for each of the 3 fonts that reportlab has built in
FONT_NAMES = {"helvetica": "Helvetica", "arial": "Helvetica", "times-roman": "Times-Roman",
              "times": "Times-Roman", "times new roman": "Times-Roman", "courier": "Courier"}
BOLD_FONTS = {"Helvetica": "Helvetica-Bold", "Times-Roman": "Times-Bold", "Courier": "Courier-Bold"}
PAGE_SIZES = {"A4": A4, "Letter": LETTER}
HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")

# used when no style is asked for, or when the agent cannot run
DEFAULT_DESIGN = {
    "title": "",
    "heading_font": "Helvetica",
    "body_font": "Helvetica",
    "title_size": 22,
    "heading_size": 14,
    "body_size": 11,
    "title_color": "#1F3A5F",
    "heading_color": "#1F3A5F",
    "text_color": "#222222",
    "line_spacing": 1.4,
    "paragraph_space": 6,
    "page_size": "A4",
    "margin_cm": 2.0,
    "alignment": "left",
}

SYSTEM_PROMPT = """You are the Report Designer Agent. A PDF report will be made from a question, its answer,
an analysis and a list of sources. Your job is only the design: fonts, sizes, colors, spacing and page layout.

You get the user's style request (it can be empty) and the start of the content.
- Use the tools to set the design. Follow the style request as closely as the tools allow.
- Read the style request part by part, and make sure every part is set by a tool. For example:
  "formal" or "classic" fonts -> Times-Roman, "large title" -> title_size 28 or more,
  "navy" -> #1F3A5F, "justified" -> set_layout with alignment "justify".
- If there is no style request, choose a clean and professional design that fits the content.
- Give the report a short title (at most 8 words) with set_title.
- Call each tool at most once. Do not write the report text yourself.
- When you have finished, reply with: DONE"""


def clamp(value, low, high):
    return max(low, min(high, value))


def make_tools(design):
    # each tool changes one part of the design dict, and keeps the values in a safe range.
    # every argument is optional, so the agent can change only what the user asked for.

    @tool
    def set_title(title: str) -> str:
        """Set the report title shown at the top of the first page."""
        design["title"] = title.strip()[:80]
        return f"Title set to: {design['title']}"

    @tool
    def set_fonts(heading_font: str | None = None, body_font: str | None = None) -> str:
        """Set the fonts. Allowed fonts: Helvetica (modern), Times-Roman (classic, formal), Courier (typewriter)."""
        problems = ""
        for key, value in [("heading_font", heading_font), ("body_font", body_font)]:
            if value is None:
                continue
            font = FONT_NAMES.get(value.strip().lower())
            if font is None:
                # tell the agent, so it can try again with an allowed font
                problems += f" Unknown font {value!r}: use Helvetica, Times-Roman or Courier."
            else:
                design[key] = font
        return f"Fonts: headings {design['heading_font']}, text {design['body_font']}." + problems

    @tool
    def set_sizes(title_size: int | None = None, heading_size: int | None = None, body_size: int | None = None) -> str:
        """Set the font sizes in points. Title 16-32, headings 12-20, text 9-14."""
        if title_size is not None:
            design["title_size"] = clamp(int(title_size), 16, 32)
        if heading_size is not None:
            design["heading_size"] = clamp(int(heading_size), 12, 20)
        if body_size is not None:
            design["body_size"] = clamp(int(body_size), 9, 14)
        return f"Sizes: title {design['title_size']}, headings {design['heading_size']}, text {design['body_size']}"

    @tool
    def set_colors(title_color: str | None = None, heading_color: str | None = None,
                   text_color: str | None = None) -> str:
        """Set the colors as hex codes like #1F3A5F. Keep the text color dark so it is easy to read."""
        problems = ""
        for key, value in [("title_color", title_color), ("heading_color", heading_color),
                           ("text_color", text_color)]:
            if value is None:
                continue
            if HEX_COLOR.match(value.strip()):
                design[key] = value.strip()
            else:
                problems += f" {value!r} is not a hex color: use a code like #1F3A5F."
        return (f"Colors: title {design['title_color']}, headings {design['heading_color']}, "
                f"text {design['text_color']}." + problems)

    @tool
    def set_spacing(line_spacing: float | None = None, paragraph_space: int | None = None) -> str:
        """Set the line spacing (1.0-2.0 times the font size) and the space after each paragraph (0-20 points)."""
        if line_spacing is not None:
            design["line_spacing"] = clamp(float(line_spacing), 1.0, 2.0)
        if paragraph_space is not None:
            design["paragraph_space"] = clamp(int(paragraph_space), 0, 20)
        return f"Spacing: lines {design['line_spacing']}, after paragraphs {design['paragraph_space']}"

    @tool
    def set_layout(page_size: str | None = None, margin_cm: float | None = None, alignment: str | None = None) -> str:
        """Set the page layout. page_size: A4 or Letter. margin_cm: 1.5-3.0.
        alignment: left, or justify when the user asks for justified text."""
        if page_size is not None and page_size.strip().upper() in ("A4", "LETTER"):
            design["page_size"] = "A4" if page_size.strip().upper() == "A4" else "Letter"
        if margin_cm is not None:
            design["margin_cm"] = clamp(float(margin_cm), 1.5, 3.0)
        if alignment is not None:
            # accepts "justify" and "justified"
            design["alignment"] = "justify" if alignment.strip().lower().startswith("justif") else "left"
        return f"Layout: {design['page_size']}, margins {design['margin_cm']} cm, text {design['alignment']}"

    return [set_title, set_fonts, set_sizes, set_colors, set_spacing, set_layout]


def design_report(question, answer, style=None, llm=None):
    design = dict(DEFAULT_DESIGN)
    message = (f"Style request: {style or 'none'}\n\n"
               f"Question: {question}\n\n"
               f"Start of the answer: {answer[:400]}")
    try:
        agent = create_agent(model=llm or get_llm("report"), tools=make_tools(design), system_prompt=SYSTEM_PROMPT)
        result = agent.invoke({"messages": [{"role": "user", "content": message}]})
        if style:
            # second look: the agent compares its design with the request and fixes what it missed
            check = (f"Check your work. The current design is: {design}\n"
                     f"Compare it with every part of the style request: {style}\n"
                     "If a part is not applied yet, call the tool that sets it. "
                     "If everything is applied, reply: DONE")
            result = agent.invoke({"messages": result["messages"] + [{"role": "user", "content": check}]})
        # shows which tools the agent called and what each one answered
        for step in result["messages"]:
            if step.type == "tool":
                logger.info("%s -> %s", step.name, step.content)
    except Exception as error:
        # no design from the agent: the report is still made with the default design
        logger.warning("Report agent failed, using the default design: %s: %s", type(error).__name__, error)
        design = dict(DEFAULT_DESIGN)
    if not design["title"]:
        design["title"] = "Report: " + question[:60]
    return design


# the 3 built-in pdf fonts have no shape for these characters and draw a black box instead,
# so they are changed to simple characters that look the same
SIMPLE_CHARACTERS = {"‐": "-", "‑": "-", "‒": "-", "−": "-", " ": " ",
                     " ": " ", " ": " ", "​": "", "→": "->", "←": "<-",
                     "≈": "~", "≤": "<=", "≥": ">=", "【": "[", "】": "]"}

# a font with Arabic letters and many symbols, used only for text the 3 built-in fonts can't draw
UNICODE_FONT = "DejaVuSans"
FONTS_DIR = Path(__file__).parent / "fonts"


def simplify(text):
    for character, simple in SIMPLE_CHARACTERS.items():
        text = text.replace(character, simple)
    return text


def escape(text):
    # reportlab paragraphs use simple html, so & < > must be escaped first
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def to_paragraph_text(text):
    text = escape(simplify(text))
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    # *text* is italic in Markdown
    return re.sub(r"(?<![*\w])\*(?!\s)(.+?)(?<!\s)\*(?![*\w])", r"<i>\1</i>", text)


def built_in_font_can_draw(text):
    # the built-in fonts only have the characters of the Windows-1252 code page
    try:
        text.encode("cp1252")
        return True
    except UnicodeEncodeError:
        return False


def use_unicode_font():
    if UNICODE_FONT not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(UNICODE_FONT, str(FONTS_DIR / "DejaVuSans.ttf")))
        pdfmetrics.registerFont(TTFont(UNICODE_FONT + "-Bold", str(FONTS_DIR / "DejaVuSans-Bold.ttf")))
        # so <b> inside a paragraph finds the bold version of the font
        pdfmetrics.registerFontFamily(UNICODE_FONT, normal=UNICODE_FONT, bold=UNICODE_FONT + "-Bold",
                                      italic=UNICODE_FONT, boldItalic=UNICODE_FONT + "-Bold")


def make_paragraph(text, style, width):
    # every piece of text from the user or the LLM goes through here, so each one gets the right font
    text = simplify(text)
    if built_in_font_can_draw(text):
        return Paragraph(to_paragraph_text(text), style)

    use_unicode_font()
    font = UNICODE_FONT + "-Bold" if "Bold" in style.fontName else UNICODE_FONT
    if has_arabic(text):
        # Arabic: right aligned, and the lines are made by arabic_lines (Markdown * marks are dropped)
        lines = arabic_lines(text.replace("*", ""), font, style.fontSize, width)
        arabic_style = ParagraphStyle("arabic", parent=style, fontName=font, alignment=TA_RIGHT)
        return Paragraph("<br/>".join(escape(line) for line in lines), arabic_style)
    return Paragraph(to_paragraph_text(text), ParagraphStyle("unicode", parent=style, fontName=font))


def text_to_flowables(text, styles, width):
    # turns the Markdown that the agents write (paragraphs, bullet lists, tables) into PDF parts
    flowables = []
    lines = text.strip().splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
        elif line.startswith("#"):
            # a Markdown heading inside the answer or the analysis becomes a bold line
            flowables.append(make_paragraph("**" + line.lstrip("#").strip() + "**", styles["body"], width))
            i += 1
        elif line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [cell.strip() for cell in lines[i].strip().strip("|").split("|")]
                # skip the |---|---| line under the header
                if not all(re.fullmatch(r":?-{2,}:?", cell) for cell in cells):
                    rows.append(cells)
                i += 1
            flowables.append(make_table(rows, styles, width))
        elif re.match(r"^([-*]|\d+\.)\s", line):
            items = []
            while i < len(lines) and re.match(r"^([-*]|\d+\.)\s", lines[i].strip()):
                items.append(re.sub(r"^([-*]|\d+\.)\s", "", lines[i].strip()))
                i += 1
            flowables.append(make_list(items, styles["body"], width))
        else:
            paragraph = []
            while i < len(lines) and lines[i].strip() and not lines[i].strip().startswith(("|", "#")) \
                    and not re.match(r"^([-*]|\d+\.)\s", lines[i].strip()):
                paragraph.append(lines[i].strip())
                i += 1
            flowables.append(make_paragraph(" ".join(paragraph), styles["body"], width))
    return flowables


def make_list(items, style, width):
    # the bullet and its space take about 30 points of the width
    paragraphs = [ListItem(make_paragraph(item, style, width - 30)) for item in items]
    if any(has_arabic(item) for item in items):
        # an Arabic list has its bullets on the right
        return ListFlowable(paragraphs, bulletType="bullet", bulletDir="rtl", leftIndent=0, rightIndent=14)
    return ListFlowable(paragraphs, bulletType="bullet", leftIndent=14)


def make_table(rows, styles, width):
    columns = max(len(row) for row in rows)
    rows = [row + [""] * (columns - len(row)) for row in rows]
    head_style, cell_style = styles["cell_head"], styles["cell"]
    if any(has_arabic(cell) for row in rows for cell in row):
        # an Arabic table is read from right to left: the first column goes on the right
        rows = [row[::-1] for row in rows]
        head_style = ParagraphStyle("cell_head_rtl", parent=head_style, alignment=TA_RIGHT)
        cell_style = ParagraphStyle("cell_rtl", parent=cell_style, alignment=TA_RIGHT)
    # each column gets the same width; 12 points go to the cell padding
    cell_width = width / columns - 12
    cells = [[make_paragraph(cell, head_style if number == 0 else cell_style, cell_width)
              for cell in row] for number, row in enumerate(rows)]
    table = Table(cells, colWidths=[width / columns] * columns, repeatRows=1, spaceBefore=2, spaceAfter=10)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEF1F5")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#B8C0CC")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return table


def make_styles(design):
    alignment = TA_JUSTIFY if design["alignment"] == "justify" else TA_LEFT
    body = ParagraphStyle("body", fontName=design["body_font"], fontSize=design["body_size"],
                          leading=design["body_size"] * design["line_spacing"],
                          textColor=colors.HexColor(design["text_color"]),
                          spaceAfter=design["paragraph_space"], alignment=alignment)
    return {
        "title": ParagraphStyle("title", fontName=BOLD_FONTS[design["heading_font"]],
                                fontSize=design["title_size"], leading=design["title_size"] * 1.25,
                                textColor=colors.HexColor(design["title_color"]), spaceAfter=6),
        "heading": ParagraphStyle("heading", fontName=BOLD_FONTS[design["heading_font"]],
                                  fontSize=design["heading_size"], leading=design["heading_size"] * 1.3,
                                  textColor=colors.HexColor(design["heading_color"]),
                                  spaceBefore=12, spaceAfter=6),
        "body": body,
        "cell": ParagraphStyle("cell", parent=body, fontSize=design["body_size"] - 1,
                               leading=(design["body_size"] - 1) * 1.3, spaceAfter=0, alignment=TA_LEFT),
        "cell_head": ParagraphStyle("cell_head", parent=body, fontName=BOLD_FONTS[design["body_font"]],
                                    fontSize=design["body_size"] - 1, leading=(design["body_size"] - 1) * 1.3,
                                    spaceAfter=0, alignment=TA_LEFT),
        "small": ParagraphStyle("small", parent=body, fontSize=9, leading=12,
                                textColor=colors.HexColor("#666666")),
    }


def build_pdf(design, question, answer, analysis, sources):
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    # the short random part stops two reports made in the same second from replacing each other
    path = REPORTS_DIR / f"report_{time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}.pdf"
    styles = make_styles(design)
    page_size = PAGE_SIZES[design["page_size"]]
    margin = design["margin_cm"] * cm
    # the width the text can use between the left and right margins
    width = page_size[0] - 2 * margin

    parts = [make_paragraph(design["title"], styles["title"], width),
             Paragraph(f"Generated on {date.today():%d %B %Y}", styles["small"]),
             Spacer(1, 10),
             Paragraph("Question", styles["heading"]),
             make_paragraph(question, styles["body"], width),
             Paragraph("Answer", styles["heading"])]
    parts += text_to_flowables(answer, styles, width)
    if analysis.strip():
        parts.append(Paragraph("Analysis", styles["heading"]))
        parts += text_to_flowables(analysis, styles, width)
    if sources:
        parts.append(Paragraph("Sources", styles["heading"]))
        parts.append(make_list(sources, styles["body"], width))

    def page_number(canvas, document):
        canvas.setFont(design["body_font"], 9)
        canvas.setFillColor(colors.HexColor("#666666"))
        canvas.drawRightString(document.pagesize[0] - margin, margin / 2, f"Page {document.page}")

    document = SimpleDocTemplate(str(path), pagesize=page_size, leftMargin=margin, rightMargin=margin,
                                 topMargin=margin, bottomMargin=margin, title=design["title"])
    document.build(parts, onFirstPage=page_number, onLaterPages=page_number)
    return str(path)


def generate_report(question, answer, analysis, sources, style=None, choices=None):
    design = design_report(question, answer, style)
    # settings the user picked in the app are exact values, so they replace what the agent chose
    if choices:
        design.update({key: value for key, value in choices.items() if key in DEFAULT_DESIGN})
    return build_pdf(design, question, answer, analysis, sources)


# quick test with the real LLM: python -m src.report.report_agent
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="  %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    sample_answer = ("Error E31 means the lidar sensor is blocked [kito_manual.pdf, page 3].\n\n"
                     "| Step | Action |\n|---|---|\n| 1 | Turn the robot off |\n| 2 | Clean the lidar window |\n\n"
                     "- Restart the robot after cleaning.\n- If E31 stays, contact support.")
    for style in [None, "formal, classic fonts, navy headings, large title, justified text"]:
        design = design_report("What does error E31 mean?", sample_answer, style)
        path = build_pdf(design, "What does error E31 mean?", sample_answer,
                         "The manual lists E31 under sensor errors.", ["kito_manual.pdf, page 3"])
        print(f"style={style!r}\n  design={design}\n  pdf={path}\n")
