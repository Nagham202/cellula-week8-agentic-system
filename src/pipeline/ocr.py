
from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract

pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)


def extract_text(image_path):
    image_path = Path(image_path)

    try:
        with Image.open(image_path) as image:

            image = image.convert("L")
            image = ImageEnhance.Contrast(image).enhance(2)
            image = image.filter(ImageFilter.SHARPEN)

            text = pytesseract.image_to_string(
                image,
                lang="eng+ara",
                config="--psm 6"
            )

    except Exception as error:
        raise ValueError(
            f"Could not extract text from {image_path.name}: {error}"
        ) from error

    result = text.strip()

    if not result:
        raise ValueError(
            f"No text found in {image_path.name}"
        )

    return result