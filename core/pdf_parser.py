"""
PDF Parser — Extract text page-by-page using PyMuPDF, chunk into overlapping segments,
and detect structured table data from invoices.
"""

import fitz  # PyMuPDF
import os
import re


def parse_pdf(file_path):
    """
    Extract text from a PDF file page-by-page.
    Returns a list of dicts: [{page: int, text: str}]
    """
    doc = fitz.open(file_path)
    pages = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text")
        if text and text.strip():
            pages.append({
                "page": page_num + 1,
                "text": text.strip()
            })

    doc.close()

    if not pages:
        raise ValueError("No extractable text found. This PDF may be scanned/image-based.")

    return pages


def chunk_text(pages, doc_name, chunk_size=500, overlap=50):
    """
    Split extracted pages into overlapping character-based chunks.
    Each chunk is tagged with document name and page number.
    Returns a list of dicts: [{doc_name, page, text, chunk_id}]
    """
    chunks = []
    chunk_id = 0

    for page_data in pages:
        text = page_data["text"]
        page_num = page_data["page"]

        # Split into chunks of ~chunk_size characters with overlap
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk_text_content = text[start:end]

            # Try to break at a sentence boundary if possible
            if end < len(text):
                last_period = chunk_text_content.rfind('.')
                last_newline = chunk_text_content.rfind('\n')
                break_point = max(last_period, last_newline)
                if break_point > chunk_size * 0.3:
                    chunk_text_content = chunk_text_content[:break_point + 1]
                    end = start + break_point + 1

            if chunk_text_content.strip():
                chunks.append({
                    "doc_name": doc_name,
                    "page": page_num,
                    "text": chunk_text_content.strip(),
                    "chunk_id": chunk_id
                })
                chunk_id += 1

            start = end - overlap if end < len(text) else len(text)

    return chunks


def extract_tables(file_path):
    """
    Attempt to extract structured table data from a PDF.
    Returns extracted fields for invoice-like documents.
    """
    doc = fitz.open(file_path)
    table_data = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        try:
            tabs = page.find_tables()
            if tabs and tabs.tables:
                for table in tabs.tables:
                    extracted = table.extract()
                    if extracted:
                        table_data.append({
                            "page": page_num + 1,
                            "rows": extracted
                        })
        except Exception:
            # Table detection may not always work
            continue

    doc.close()

    # Try to extract invoice-like fields from the text
    structured = _extract_invoice_fields(file_path)

    return {
        "tables": table_data,
        "structured_fields": structured
    }


def _extract_invoice_fields(file_path):
    """
    Simple regex-based extraction of common invoice fields.
    """
    doc = fitz.open(file_path)
    full_text = ""
    for page in doc:
        full_text += page.get_text("text") + "\n"
    doc.close()

    fields = {}

    # Date patterns
    date_patterns = [
        r'(?:date|dated|invoice date|bill date)[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
        r'(?:date|dated|invoice date|bill date)[:\s]*(\w+ \d{1,2},?\s*\d{4})',
        r'(\d{1,2}[/-]\d{1,2}[/-]\d{4})',
    ]
    for pattern in date_patterns:
        match = re.search(pattern, full_text, re.IGNORECASE)
        if match:
            fields["date"] = match.group(1).strip()
            break

    # Amount patterns
    amount_patterns = [
        r'(?:total|amount|grand total|net amount|balance due)[:\s]*[\$£€₹]?\s*([\d,]+\.?\d*)',
        r'[\$£€₹]\s*([\d,]+\.\d{2})',
    ]
    for pattern in amount_patterns:
        match = re.search(pattern, full_text, re.IGNORECASE)
        if match:
            fields["amount"] = match.group(1).strip()
            break

    # Vendor/company patterns
    vendor_patterns = [
        r'(?:vendor|from|seller|company|billed by)[:\s]*([A-Za-z0-9\s&.,]+)',
        r'(?:invoice from)[:\s]*([A-Za-z0-9\s&.,]+)',
    ]
    for pattern in vendor_patterns:
        match = re.search(pattern, full_text, re.IGNORECASE)
        if match:
            fields["vendor"] = match.group(1).strip()[:100]
            break

    return fields if fields else None
