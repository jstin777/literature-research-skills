#!/usr/bin/env python3
"""Read-only source-file checks; optional extraction. Never proves article identity.

PDF parsing uses pypdf when available; missing parsing/OCR returns unresolved,
not a successful verification. HTML/text checks use the standard library.
"""
import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path


class HTMLText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts, self.title_parts = [], []
        self.hidden, self.in_title = 0, False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.hidden += 1
        if tag == "title":
            self.in_title = True
        if tag in ("p", "div", "section", "article", "h1", "h2", "h3", "tr", "li", "br"):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.hidden = max(0, self.hidden - 1)
        if tag == "title":
            self.in_title = False

    def handle_data(self, data):
        if self.in_title:
            self.title_parts.append(data)
        if not self.hidden:
            self.parts.append(data)


def inspect_file(path, expected=None, expected_doi=None, expected_title=None, extract_all=False):
    path = Path(path).resolve()
    blob = path.read_bytes()
    head = blob[:4096].lstrip(b"\xef\xbb\xbf \t\r\n").lower()
    kind = "pdf" if blob.startswith(b"%PDF-") else "html" if head.startswith((b"<!doctype html", b"<html")) or b"<html" in head else "text"
    report = {"path": str(path), "checked_at": datetime.now(timezone.utc).isoformat(),
              "bytes": len(blob), "sha256": hashlib.sha256(blob).hexdigest(), "detected_type": kind,
              "mechanical_status": "pass", "errors": [], "warnings": [],
              "identity_verified": False, "article_completeness_verified": False,
              "claims_verified": False, "check_scope": "File container/readability only; inspect original source and relevant content separately."}
    if not blob:
        report["errors"].append("empty_file")
    if expected and kind != expected:
        report["errors"].append("file_type_mismatch")
    if report["errors"]:
        report["mechanical_status"] = "fail"
        return report, None
    extracted, first_page = None, None
    if kind == "pdf":
        try:
            import pypdf
        except ImportError:
            report["mechanical_status"] = "unresolved"
            report["warnings"].append("pdf_parser_unavailable: use available PDF inspection/OCR; do not infer readability")
            return report, None
        try:
            reader = pypdf.PdfReader(path)
            if reader.is_encrypted and not reader.decrypt(""):
                report["mechanical_status"] = "unresolved"
                report["warnings"].append("encrypted_pdf_not_readable")
                return report, None
            count = len(reader.pages)
            report["page_count"] = count
            if not count:
                report["errors"].append("pdf_has_no_pages")
            else:
                sampled = sorted({0, count // 2, count - 1})
                indices = range(count) if extract_all else sampled
                texts = {n: reader.pages[n].extract_text() or "" for n in indices}
                first_page = texts[0]
                report["sampled_pages"] = [n + 1 for n in sampled]
                report["sample_text_characters"] = {str(n + 1): len(texts[n].strip()) for n in sampled}
                report["text_characters"] = sum(len(t) for t in texts.values())
                report["text_scope"] = "all_pages" if extract_all else "sampled_pages"
                extracted = "\n\n".join(f"<!-- PDF page {n + 1} -->\n{body}" for n, body in texts.items())
                if report["text_characters"] < 80:
                    report["mechanical_status"] = "unresolved"
                    report["warnings"].append("little_extractable_text: scanned/image PDF or extraction failure; inspect/OCR")
                report["warnings"].append("pdf_text_extraction_does_not_verify_tables_equations_figures_or_missing_pages")
        except Exception as exc:
            report["errors"].append("pdf_parse_failed: " + type(exc).__name__)
    else:
        try:
            decoded = blob.decode("utf-8-sig")
        except UnicodeDecodeError:
            report["mechanical_status"] = "unresolved"
            report["warnings"].append("non_utf8_content: use an appropriate decoder or file reader")
            return report, None
        if kind == "html":
            parser = HTMLText()
            parser.feed(decoded)
            report["html_title"] = "".join(parser.title_parts).strip()
            extracted = "\n".join(line.strip() for line in "".join(parser.parts).splitlines() if line.strip())
            title = report["html_title"].casefold()
            if any(term in title for term in ("access denied", "sign in", "log in", "checking your browser", "404 not found", "just a moment")):
                report["mechanical_status"] = "unresolved"
                report["warnings"].append("possible_access_or_error_screen")
            report["warnings"].append("html_text_omits_layout_and_external_assets; it does not establish full_article_access")
        else:
            extracted = decoded
        report["text_characters"] = len(extracted.strip())
        if not extracted.strip():
            report["mechanical_status"] = "unresolved"
            report["warnings"].append("no_readable_text")
    if report["errors"]:
        report["mechanical_status"] = "fail"
    # A first-page hit is a clue, never article-identity verification. A reference
    # list mentioning the expected DOI must not masquerade as an identity match.
    if expected_doi:
        haystack = first_page if kind == "pdf" else extracted
        report["expected_doi_in_first_page_or_text"] = expected_doi.casefold() in (haystack or "").casefold()
        if not report["expected_doi_in_first_page_or_text"]:
            report["warnings"].append("expected_doi_not_found: resolve identity using authoritative metadata")
    if expected_title:
        clean = lambda s: "".join(c for c in s.casefold() if c.isalnum())
        report["expected_title_in_first_page_or_text"] = clean(expected_title) in clean((first_page if kind == "pdf" else extracted) or "")
        if not report["expected_title_in_first_page_or_text"]:
            report["warnings"].append("expected_title_not_found: inspect source identity")
    return report, extracted


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path")
    parser.add_argument("--expect", choices=("pdf", "html", "text"))
    parser.add_argument("--doi")
    parser.add_argument("--title")
    parser.add_argument("--report-out")
    parser.add_argument("--text-out", help="Optional native text extraction; not a verified Markdown conversion or printable article")
    args = parser.parse_args()
    try:
        source = Path(args.path).resolve()
        outputs = [Path(p).resolve() for p in (args.report_out, args.text_out) if p]
        if source in outputs or len(outputs) != len(set(outputs)):
            raise ValueError("Outputs must differ from the source and each other")
        report, text = inspect_file(source, args.expect, args.doi, args.title, bool(args.text_out))
        if args.text_out and text is not None:
            output = Path(args.text_out)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(text, encoding="utf-8")
            report["extracted_text_path"] = str(output.resolve())
        if args.report_out:
            output = Path(args.report_out)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return {"pass": 0, "fail": 1, "unresolved": 2}[report["mechanical_status"]]
    except (OSError, ValueError) as exc:
        print(json.dumps({"mechanical_status": "fail", "error": str(exc)}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
