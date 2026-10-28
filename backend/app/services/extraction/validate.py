"""Upload checks from plan 7.2: real type from magic bytes, size and page limits."""
import pymupdf

MAX_BYTES = 15 * 1024 * 1024
MAX_PAGES = 20

_MAGIC = [
    (b"%PDF-", "application/pdf"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG", "image/png"),
]


class UploadRejected(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def validate_upload(data: bytes) -> tuple[str, int]:
    """Returns (mime_type, page_count) or raises UploadRejected."""
    mime = next((m for prefix, m in _MAGIC if data.startswith(prefix)), None)
    if mime is None:
        raise UploadRejected("unsupported_type", "Only PDF, JPEG and PNG files are supported.")
    if len(data) > MAX_BYTES:
        raise UploadRejected("too_large", "File is larger than 15 MB.")
    if mime != "application/pdf":
        return mime, 1

    try:
        doc = pymupdf.open(stream=data, filetype="pdf")
    except Exception:
        raise UploadRejected("pdf_unreadable", "This PDF could not be opened. It may be damaged.")
    with doc:
        if doc.needs_pass:
            raise UploadRejected(
                "pdf_encrypted",
                "This PDF is password-protected. Many labs use your date of birth as the password; "
                "please open it, save a copy without a password, and upload that.",
            )
        if doc.page_count > MAX_PAGES:
            raise UploadRejected("too_many_pages", f"PDF has more than {MAX_PAGES} pages.")
        return mime, doc.page_count
