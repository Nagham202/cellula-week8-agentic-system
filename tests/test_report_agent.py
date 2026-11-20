from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage
from pypdf import PdfReader

from src.report import report_agent
from src.report.report_agent import DEFAULT_DESIGN, build_pdf, design_report, generate_report, make_tools

ANSWER = ("Error E31 means the lidar is blocked [kito_manual.pdf, page 3].\n\n"
          "| Step | Action |\n|---|---|\n| 1 | Turn the robot off |\n| 2 | Clean the lidar |\n\n"
          "- Restart the robot.\n- If E31 stays, contact support.")


# acts like a chat model that calls tools, without calling any api
class FakeToolLLM(GenericFakeChatModel):
    def bind_tools(self, tools, **kwargs):
        return self


def tool_call(name, args, number):
    return {"name": name, "args": args, "id": f"call_{number}"}


def pdf_text(path):
    return " ".join(page.extract_text() for page in PdfReader(path).pages)


def test_tools_keep_values_in_a_safe_range():
    design = dict(DEFAULT_DESIGN)
    tools = {t.name: t for t in make_tools(design)}
    tools["set_sizes"].invoke({"title_size": 100, "heading_size": 2, "body_size": 12})
    tools["set_fonts"].invoke({"heading_font": "Comic Sans", "body_font": "Times-Roman"})
    tools["set_colors"].invoke({"title_color": "navy", "heading_color": "#000080", "text_color": "#111111"})
    assert (design["title_size"], design["heading_size"], design["body_size"]) == (32, 12, 12)
    # an unknown font or a color that is not a hex code keeps the old value
    assert design["heading_font"] == "Helvetica" and design["body_font"] == "Times-Roman"
    assert design["title_color"] == DEFAULT_DESIGN["title_color"] and design["heading_color"] == "#000080"


def test_tools_accept_partial_arguments_and_common_names():
    design = dict(DEFAULT_DESIGN)
    tools = {t.name: t for t in make_tools(design)}
    # the agent changes only the alignment, the other layout values stay the same
    tools["set_layout"].invoke({"alignment": "justified"})
    tools["set_fonts"].invoke({"body_font": "times new roman"})
    assert design["alignment"] == "justify" and design["margin_cm"] == DEFAULT_DESIGN["margin_cm"]
    assert design["body_font"] == "Times-Roman" and design["heading_font"] == "Helvetica"


def test_agent_tool_calls_change_the_design():
    llm = FakeToolLLM(messages=iter([
        # first round: the agent sets the title and the fonts, and forgets the alignment
        AIMessage(content="", tool_calls=[
            tool_call("set_title", {"title": "Error E31 Guide"}, 1),
            tool_call("set_fonts", {"heading_font": "Times-Roman", "body_font": "Times-Roman"}, 2),
        ]),
        AIMessage(content="DONE"),
        # second round (the check): the agent sees the missing alignment and fixes it
        AIMessage(content="", tool_calls=[tool_call("set_layout", {"alignment": "justify"}, 3)]),
        AIMessage(content="DONE"),
    ]))
    design = design_report("What does error E31 mean?", ANSWER, "classic fonts, justified text", llm=llm)
    assert design["title"] == "Error E31 Guide"
    assert design["body_font"] == "Times-Roman"
    assert design["alignment"] == "justify"


class BrokenLLM:
    def bind_tools(self, tools, **kwargs):
        raise RuntimeError("provider is down")


def test_agent_failure_falls_back_to_the_default_design():
    design = design_report("What does error E31 mean?", ANSWER, llm=BrokenLLM())
    assert design["body_font"] == DEFAULT_DESIGN["body_font"]
    assert design["title"] == "Report: What does error E31 mean?"


def test_pdf_has_all_sections(tmp_path, monkeypatch):
    monkeypatch.setattr(report_agent, "REPORTS_DIR", tmp_path)
    design = dict(DEFAULT_DESIGN, title="Error E31 Guide")
    path = build_pdf(design, "What does error E31 mean?", ANSWER, "Listed under sensor errors.",
                     ["kito_manual.pdf, page 3"])
    text = pdf_text(path)
    for words in ["Error E31 Guide", "Question", "Answer", "Analysis", "Sources", "Clean the lidar",
                  "Restart the robot", "Page 1"]:
        assert words in text


def test_special_characters_do_not_break_the_pdf(tmp_path, monkeypatch):
    monkeypatch.setattr(report_agent, "REPORTS_DIR", tmp_path)
    design = dict(DEFAULT_DESIGN, title="A < B & C")
    path = build_pdf(design, "Is 5 < 7 & 7 > 5?", "Yes, **both** are true.", "", [])
    text = pdf_text(path)
    assert "5 < 7 & 7 > 5" in text
    # empty analysis and no sources: those headings are left out
    assert "Analysis" not in text and "Sources" not in text


def test_generate_report_matches_the_api_contract(tmp_path, monkeypatch):
    monkeypatch.setattr(report_agent, "REPORTS_DIR", tmp_path)
    monkeypatch.setattr(report_agent, "design_report",
                        lambda question, answer, style=None: dict(DEFAULT_DESIGN, title="Test"))
    path = generate_report("Q?", "A.", "", ["file.pdf"], style=None)
    assert path.endswith(".pdf") and str(tmp_path) in path


def test_markdown_and_special_characters_in_the_analysis(tmp_path, monkeypatch):
    monkeypatch.setattr(report_agent, "REPORTS_DIR", tmp_path)
    analysis = "### Answer\nThe *Team Contributions* table lists the user\u2011interface work."
    path = build_pdf(dict(DEFAULT_DESIGN, title="Test"), "Who is Heba?", "Heba built the UI.", analysis, ["readme.txt"])
    text = pdf_text(path)
    # the non-breaking hyphen is drawn as a normal hyphen, and no * is left in the text
    assert "user-interface" in text and "*" not in text


def test_choices_from_the_app_replace_the_agent_design(tmp_path, monkeypatch):
    monkeypatch.setattr(report_agent, "REPORTS_DIR", tmp_path)
    monkeypatch.setattr(report_agent, "design_report",
                        lambda question, answer, style=None: dict(DEFAULT_DESIGN, title="Test", body_font="Courier"))
    used = {}
    monkeypatch.setattr(report_agent, "build_pdf",
                        lambda design, question, answer, analysis, sources: used.update(design) or "report.pdf")
    generate_report("Q?", "A.", "", [], choices={"body_font": "Times-Roman", "alignment": "justify", "unknown": 1})
    # the user's choices win, the rest stays as the agent chose, and unknown keys are ignored
    assert used["body_font"] == "Times-Roman" and used["alignment"] == "justify"
    assert used["title"] == "Test" and "unknown" not in used


def test_arabic_text_gets_the_unicode_font(tmp_path, monkeypatch):
    monkeypatch.setattr(report_agent, "REPORTS_DIR", tmp_path)
    answer = "الخطأ E31 يعني أن حساس الليدار مغطى【kito_manual.pdf】.\n\n- نظف الحساس.\n- أعد تشغيل الروبوت."
    path = build_pdf(dict(DEFAULT_DESIGN, title="خطأ E31"), "ماذا يعني الخطأ E31؟", answer, "", ["kito_manual.pdf"])
    fonts = {font["/BaseFont"] for page in PdfReader(path).pages for font in page["/Resources"]["/Font"].values()}
    # the arabic text uses the DejaVu font, and the english parts keep the built-in font
    assert any("DejaVuSans" in font for font in fonts) and "/Helvetica" in fonts
