import pymupdf
import pytest

from app.services.extraction.validate import UploadRejected, validate_upload

PNG_HEADER = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
JPEG_HEADER = b"\xff\xd8\xff\xe0" + b"\x00" * 100


def make_pdf(pages=1, password=None) -> bytes:
    doc = pymupdf.open()
    for i in range(pages):
        doc.new_page().insert_text((72, 72), f"Page {i + 1}")
    if password:
        return doc.tobytes(encryption=pymupdf.PDF_ENCRYPT_AES_256, user_pw=password, owner_pw=password)
    return doc.tobytes()


def test_accepts_pdf():
    assert validate_upload(make_pdf(pages=2)) == ("application/pdf", 2)


def test_accepts_png_as_one_page():
    assert validate_upload(PNG_HEADER) == ("image/png", 1)


def test_accepts_jpeg_as_one_page():
    assert validate_upload(JPEG_HEADER) == ("image/jpeg", 1)


def test_rejects_unknown_type_even_if_named_pdf():
    with pytest.raises(UploadRejected) as exc:
        validate_upload(b"MZ\x90\x00 this is an exe")
    assert exc.value.code == "unsupported_type"


def test_rejects_empty_file():
    with pytest.raises(UploadRejected) as exc:
        validate_upload(b"")
    assert exc.value.code == "unsupported_type"


def test_rejects_over_15_mb():
    big = PNG_HEADER + b"\x00" * (15 * 1024 * 1024)
    with pytest.raises(UploadRejected) as exc:
        validate_upload(big)
    assert exc.value.code == "too_large"


def test_rejects_more_than_20_pages():
    with pytest.raises(UploadRejected) as exc:
        validate_upload(make_pdf(pages=21))
    assert exc.value.code == "too_many_pages"


def test_accepts_exactly_20_pages():
    assert validate_upload(make_pdf(pages=20)) == ("application/pdf", 20)


def test_rejects_password_protected_pdf_with_helpful_message():
    with pytest.raises(UploadRejected) as exc:
        validate_upload(make_pdf(password="01011968"))
    assert exc.value.code == "pdf_encrypted"
    assert "password" in exc.value.message.lower()


def test_rejects_corrupt_pdf():
    with pytest.raises(UploadRejected) as exc:
        validate_upload(b"%PDF-1.7\n garbage garbage")
    assert exc.value.code == "pdf_unreadable"
