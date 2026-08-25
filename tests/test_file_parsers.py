import pytest

from backend.extraction.file_parsers import extract_text_from_pdf


def _build_minimal_pdf(text: str) -> bytes:
    """외부 라이브러리 없이 순수 PDF 문법으로 한 페이지짜리 최소 PDF를 만든다.
    xref 오프셋은 각 객체의 실제 바이트 길이를 누적해 런타임에 계산한다."""
    content_stream = f"BT /F1 12 Tf 10 100 Td ({text}) Tj ET".encode("latin-1")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> "
        b"/MediaBox [0 0 200 200] /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length %d >>\nstream\n%s\nendstream" % (len(content_stream), content_stream),
    ]

    header = b"%PDF-1.4\n"
    body = bytearray()
    offsets = [0]  # object 0 is the free-list head, unused
    for i, obj in enumerate(objects, start=1):
        offsets.append(len(header) + len(body))
        body += b"%d 0 obj\n%s\nendobj\n" % (i, obj)

    xref_offset = len(header) + len(body)
    xref = b"xref\n0 %d\n" % (len(objects) + 1)
    xref += b"0000000000 65535 f \n"
    for off in offsets[1:]:
        xref += b"%010d 00000 n \n" % off

    trailer = b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF" % (
        len(objects) + 1, xref_offset,
    )

    return header + bytes(body) + xref + trailer


def test_extract_text_from_pdf_happy_path():
    pdf_bytes = _build_minimal_pdf("Hello PIPA")
    text = extract_text_from_pdf(pdf_bytes)
    assert "Hello PIPA" in text


def test_extract_text_from_pdf_corrupted_bytes_raises_value_error():
    with pytest.raises(ValueError):
        extract_text_from_pdf(b"this is not a pdf file at all")


def test_extract_text_from_pdf_empty_text_layer_raises_value_error():
    pdf_bytes = _build_minimal_pdf("")
    with pytest.raises(ValueError):
        extract_text_from_pdf(pdf_bytes)
