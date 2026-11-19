# stand-ins for my teammates' functions, with the names and formats we agreed on,
# so the API works now. When their code is ready, only the import in api/main.py changes.

from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

REPORTS_DIR = Path("data/reports")


# teammate 2: speech to text
def transcribe(audio_path):
    return "What does error E31 mean?"


# teammate 2: text from an image (OCR)
def extract_text(image_path):
    return f"Text found in {Path(image_path).name}: the office opens at 8 am and closes at 4 pm."


# teammate 3: the report agent, returns the path of the PDF it made
def generate_report(question, answer, analysis, sources, style=None):
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORTS_DIR / "fake_report.pdf"
    pdf = canvas.Canvas(str(path), pagesize=A4)
    pdf.drawString(72, 800, "Fake report (the real report agent is not connected yet)")
    pdf.drawString(72, 770, f"Question: {question[:90]}")
    pdf.drawString(72, 740, f"Sources: {', '.join(sources)[:90]}")
    pdf.drawString(72, 710, f"Style asked for: {style or 'default'}")
    pdf.save()
    return str(path)
