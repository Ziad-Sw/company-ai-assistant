"""
Heading-aware chunking للمستندات.

الاستراتيجية (مطابقة لـPRD.md قسم 7):
1. نقسّم المستند الأول حسب العناوين (## و###) — عشان كل chunk يفضل
   مرتبط بموضوع فرعي واحد ومايتقطعش نصه نص.
2. أي قسم لسه طويل (أكتر من الحجم المستهدف)، نقسّمه تاني بالحروف
   مع overlap، عشان ولا chunk يتعدى الحجم المسموح.

حجم الـchunk المستهدف: 500-800 token (هنا 650 كمتوسط).
الـoverlap: 10-15% (هنا ~13%).

ملحوظة عن الـtokens: مفيش tokenizer دقيق هنا (عشان نفضل خفيفين وبسطاء)،
فبنستخدم تقريب شائع: ~4 حروف لكل token في النص الإنجليزي. النص العربي
أحياناً بياخد tokens أكتر لكل حرف، فالتقريب ده يميل يحط chunks أصغر
شوية للنص العربي — وده مقبول وآمن (أحسن من chunks أكبر من المطلوب).
"""

from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

HEADERS_TO_SPLIT_ON = [("##", "h2"), ("###", "h3")]

CHARS_PER_TOKEN = 4
CHUNK_SIZE_TOKENS = 650
CHUNK_OVERLAP_TOKENS = 85  # ~13% من 650


def chunk_markdown(text: str) -> list[dict]:
    """
    يرجع list من dicts، كل واحدة فيها:
      - content: نص الـchunk
      - section: dict فيه عناوين القسم (h2/h3) لو موجودة
    """
    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=HEADERS_TO_SPLIT_ON,
        strip_headers=False,
    )
    sections = header_splitter.split_text(text)

    char_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE_TOKENS * CHARS_PER_TOKEN,
        chunk_overlap=CHUNK_OVERLAP_TOKENS * CHARS_PER_TOKEN,
        separators=["\n\n", "\n", ". ", "، ", " ", ""],
    )

    chunks: list[dict] = []
    for section in sections:
        section_text = section.page_content.strip()
        if not section_text:
            continue
        section_meta = dict(section.metadata)
        for piece in char_splitter.split_text(section_text):
            chunks.append({"content": piece, "section": section_meta})

    return chunks
