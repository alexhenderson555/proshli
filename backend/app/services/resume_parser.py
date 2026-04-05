from io import BytesIO

from pypdf import PdfReader

KNOWN_SKILLS = [
    "python",
    "java",
    "javascript",
    "typescript",
    "react",
    "sql",
    "postgresql",
    "docker",
    "kubernetes",
    "aws",
    "fastapi",
    "django",
]


def extract_text_from_pdf_bytes(file_bytes: bytes) -> str:
    reader = PdfReader(BytesIO(file_bytes))
    chunks: list[str] = []
    for page in reader.pages:
        chunks.append(page.extract_text() or "")
    return "\n".join(chunks).strip()


def extract_skills(text: str) -> list[str]:
    lowered = text.lower()
    return [skill for skill in KNOWN_SKILLS if skill in lowered]
