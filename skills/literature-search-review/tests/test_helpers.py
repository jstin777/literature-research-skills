"""Offline regressions for observable record/file failures, not search recall."""
import copy
import csv
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import catalogue as cat
import source_files as files


def paper(**changes):
    row = {"paper_id": "P0001", "title": "A study of operational measures",
           "identifiers": {"doi": "10.1234/example"}, "publication_type": "article",
           "authors": [{"family": "García", "given": "Ana"}, {"collective": "Example Study Group"}]}
    row.update(changes)
    return row


def checked_paper(**changes):
    row = paper(eligibility_status="included", full_text_status="verified",
                evidence_status="verified_for_question", review_role="primary evidence",
                review_treatment="synthesized")
    row["identity_verification"] = {"status": "verified", "title": row["title"],
                                    "identifiers": row["identifiers"], "source": "fixture metadata",
                                    "checked_at": "2026-10-06T12:00:00+00:00"}
    row["full_text_verification"] = {"source": "fixture article", "checked_at": "2026-10-06T12:00:00+00:00",
                                     "main_body_complete": True}
    row.update(changes)
    return row


def query(**changes):
    row = {"event_id": "S-fixture", "event_type": "query", "purpose": "Independent question branch",
           "source": "fixture database", "submitted_request": {"query": "operational measures"},
           "retrieved_paper_ids": ["P0001"], "status": "complete"}
    row.update(changes)
    return row


def evidence(**changes):
    row = {"paper_id": "P0001", "subquestion": "Which operational measure was compared?",
           "design": "Offline illustrative comparison; not a real experiment",
           "sample": {"population": "fixture only", "independent_unit": "participant", "n": 4},
           "measure": "Fixture measure A versus B", "finding": "Fixture finding; not a scientific result",
           "uncertainty": "not reported: no precision estimate in the fixture",
           "limitations": "Illustrative source only; no scientific interpretation",
           "inference": "none: descriptive extraction only",
           "supporting_context": "Exact fixture excerpt: Fixture finding; not a scientific result",
           "verification_status": "verified", "locators": [{"source": "fixture article", "location": "Results"}]}
    row.update(changes)
    return row


def make_pdf(path, texts):
    """Small valid text PDF built offline; avoids fixture downloads/dependencies."""
    font_id = 3 + 2 * len(texts)
    kids = " ".join(f"{3 + 2 * n} 0 R" for n in range(len(texts)))
    objects = [b"<< /Type /Catalog /Pages 2 0 R >>",
               f"<< /Type /Pages /Count {len(texts)} /Kids [{kids}] >>".encode()]
    for n, text in enumerate(texts):
        stream_id = 4 + 2 * n
        objects.append((f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                        f"/Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {stream_id} 0 R >>").encode())
        safe = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        stream = f"BT /F1 12 Tf 50 750 Td ({safe}) Tj ET".encode("ascii")
        objects.append(f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream")
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    output, offsets = b"%PDF-1.4\n", [0]
    for n, obj in enumerate(objects, 1):
        offsets.append(len(output))
        output += f"{n} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(output)
    output += f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode()
    output += b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets[1:])
    output += f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    path.write_bytes(output)


class RecordTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        cat.init_run(self.root, "Fixture question")

    def cp(self, **changes):
        cp = cat.checkpoint(self.root)
        cp.update(changes)
        cat.atomic_write(self.root / "search-records/checkpoint.json", json.dumps(cp))

    def rows(self):
        return cat.load_rows(self.root / cat.LOCATIONS["papers"])

    def ready_run(self, row=None):
        cat.upsert_papers(self.root, [row or checked_paper()])
        cat.record_rows(self.root, "search", [query()])
        cat.record_rows(self.root, "evidence", [evidence()])
        self.cp(protocol_ready=True, search_plan_accounted=True, gap_audit_done=True, limitations_reported=True)

    def handoff_run(self):
        self.ready_run()
        path = self.root / "working/source-text/P0001.txt"
        cat.atomic_write(path, "Original fixture text: Fixture finding; not a scientific result\n")
        cat.upsert_papers(self.root, [{"paper_id": "P0001",
            "source_locations": [{"path": "working/source-text/P0001.txt", "url": "https://example.org/article"}],
            "source_reuse": {"status": "local", "coverage": "Fixture main body only",
                             "limitations": "No figures or supplements in the fixture"}}])
        cat.atomic_write(self.root / "working/handoff.md", "# Handoff\n\nRoot: " + str(self.root) +
                         "\n\nDescriptive fixture package; no scientific findings.\n")
        return path

    def test_normalized_duplicates_keep_both_routes_and_alias(self):
        first = paper(identifiers={"doi": "https://doi.org/10.1234/EXAMPLE"}, discovery_routes=["PubMed"])
        second = paper(paper_id="P0099", discovery_routes=["OpenAlex"])
        cat.upsert_papers(self.root, [first, second])
        row = self.rows()[0]
        self.assertEqual(len(self.rows()), 1)
        self.assertEqual(row["paper_id"], "P0001")
        self.assertEqual(row["aliases"], ["P0099"])
        self.assertEqual(row["discovery_routes"], ["PubMed", "OpenAlex"])
        self.assertEqual(row["identifiers"]["doi"], "10.1234/example")

    def test_wrong_pmcid_conflict_does_not_partially_write_batch(self):
        cat.upsert_papers(self.root, [paper(identifiers={"doi": "10.1234/example", "pmcid": "PMC123"})])
        original = (self.root / cat.LOCATIONS["papers"]).read_bytes()
        with self.assertRaises(ValueError):
            cat.upsert_papers(self.root, [paper(paper_id="P0002", identifiers={"doi": "10.1234/other"}),
                                          paper(identifiers={"doi": "10.1234/example", "pmcid": "PMC456"})])
        self.assertEqual((self.root / cat.LOCATIONS["papers"]).read_bytes(), original)

    def test_bridge_between_different_records_requires_resolution(self):
        cat.upsert_papers(self.root, [paper(), paper(paper_id="P0002", identifiers={"pmid": "123"})])
        with self.assertRaises(ValueError):
            cat.upsert_papers(self.root, [paper(identifiers={"doi": "10.1234/example", "pmid": "123"})])
        self.assertEqual(len(self.rows()), 2)

    def test_distinct_dois_with_identical_titles_are_not_merged(self):
        cat.upsert_papers(self.root, [paper(), paper(paper_id="P0002", identifiers={"doi": "10.1234/second"})])
        self.assertEqual(len(self.rows()), 2)

    def test_conflicting_title_on_exact_doi_is_rejected(self):
        cat.upsert_papers(self.root, [paper()])
        with self.assertRaises(ValueError):
            cat.upsert_papers(self.root, [paper(title="An entirely different article")])

    def test_alias_is_not_reused_for_a_new_internal_id(self):
        cat.upsert_papers(self.root, [paper(aliases=["P0009"])])
        cat.upsert_papers(self.root, [{"title": "Another", "identifiers": {"doi": "10.1234/other"}}])
        self.assertEqual(self.rows()[1]["paper_id"], "P0010")

    def test_verified_identity_mismatched_observed_id_rejected(self):
        row = checked_paper()
        row["identity_verification"] = copy.deepcopy(row["identity_verification"])
        row["identity_verification"]["identifiers"] = {"doi": "10.1234/wrong"}
        with self.assertRaises(ValueError):
            cat.upsert_papers(self.root, [row])

    def test_verified_identity_without_observed_title_rejected(self):
        row = checked_paper()
        del row["identity_verification"]["title"]
        with self.assertRaises(ValueError):
            cat.upsert_papers(self.root, [row])

    def test_exclusion_requires_basis_not_access_status(self):
        with self.assertRaises(ValueError):
            cat.upsert_papers(self.root, [paper(eligibility_status="excluded", full_text_status="unavailable")])

    def test_bad_state_and_malformed_authors_rejected(self):
        for changes in ({"eligibility_status": "probably"}, {"authors": "Group"},
                        {"authors": [{"collective": "Group", "family": "Group"}]},
                        {"aliases": "P0020"}, {"title": {"text": "A title"}}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                cat.upsert_papers(self.root, [paper(**changes)])

    def test_initialization_cannot_overwrite_run(self):
        checkpoint = (self.root / "search-records/checkpoint.json").read_bytes()
        with self.assertRaises(ValueError):
            cat.init_run(self.root, "Other question")
        self.assertEqual((self.root / "search-records/checkpoint.json").read_bytes(), checkpoint)

    def test_new_run_is_not_review_ready(self):
        report = cat.validate_run(self.root, True)
        self.assertFalse(report["ok"])
        self.assertIn("No search/corpus accounting events", report["errors"])

    def test_readiness_requires_evidence_and_fulltext_not_just_inclusion(self):
        self.ready_run(checked_paper(full_text_status="partial", evidence_status="extracted_unverified"))
        report = cat.validate_run(self.root, True)
        self.assertFalse(report["ok"])
        self.assertIn("P0001: full text unresolved", report["errors"])
        self.assertIn("P0001: question evidence not verified", report["errors"])

    def test_fullbody_verification_needs_explicit_inspection_record(self):
        with self.assertRaises(ValueError):
            cat.upsert_papers(self.root, [checked_paper(full_text_verification={})])

    def test_needed_component_unresolved_blocks_verified_claim(self):
        self.ready_run()
        cat.record_rows(self.root, "evidence", [evidence(evidence_id="E0001", required_components=[
            {"component": "supplement", "locator": "Supplement Table S1", "status": "unresolved"}])])
        self.assertFalse(cat.validate_run(self.root, True)["ok"])

    def test_checked_evidence_needs_original_locator(self):
        self.ready_run()
        cat.record_rows(self.root, "evidence", [evidence(evidence_id="E0001", locators=[])])
        self.assertFalse(cat.validate_run(self.root)["ok"])

    def test_unknown_paper_ids_are_not_silently_dropped(self):
        cat.record_rows(self.root, "evidence", [evidence(paper_id="P9999")])
        self.assertFalse(cat.validate_run(self.root)["ok"])

    def test_deferred_queue_blocks_finalization(self):
        self.ready_run()
        self.cp(deferred_fetches=[{"paper_id": "P0001", "reason": "section ceiling"}])
        self.assertFalse(cat.validate_run(self.root, True)["ok"])

    def test_included_paper_cannot_disappear_from_writer_accounting(self):
        self.ready_run(checked_paper(review_treatment=""))
        self.assertIn("P0001: review treatment not accounted for", cat.validate_run(self.root, True)["errors"])

    def test_access_failure_is_history_not_unclosed_query(self):
        self.ready_run()
        cat.record_rows(self.root, "access", [{"paper_id": "P0001", "outcome": "failed", "route": "publisher"}])
        self.assertTrue(cat.validate_run(self.root, True)["ok"])

    def test_pending_search_attempt_closes_via_same_event_id(self):
        cat.record_rows(self.root, "search", [query(status="pending", retrieved_paper_ids=[])])
        self.ready_run()
        self.assertTrue(cat.validate_run(self.root, True)["ok"])
        self.assertEqual(len(cat.load_rows(self.root / cat.LOCATIONS["search"])), 2)

    def test_limited_search_requires_disclosed_limit(self):
        self.ready_run()
        cat.record_rows(self.root, "search", [query(event_id="S-cap", status="limited")])
        self.assertFalse(cat.validate_run(self.root, True)["ok"])
        cat.record_rows(self.root, "search", [query(event_id="S-cap", status="limited", limitations="Only first 50 ranked hits processed")])
        self.assertTrue(cat.validate_run(self.root, True)["ok"])

    def test_missing_exact_request_is_not_reproducible_search(self):
        self.ready_run()
        cat.record_rows(self.root, "search", [query(event_id="S-bad", submitted_request={})])
        self.assertFalse(cat.validate_run(self.root)["ok"])

    def test_citation_direction_and_seeds_are_required(self):
        self.ready_run()
        cat.record_rows(self.root, "search", [query(event_id="S-cite", event_type="citation")])
        self.assertFalse(cat.validate_run(self.root)["ok"])

    def test_abstract_only_requires_scope_or_actual_user_acceptance(self):
        row = checked_paper(full_text_status="unavailable", evidence_status="abstract_only")
        self.ready_run(row)
        cat.record_rows(self.root, "evidence", [evidence(evidence_id="E0001", verification_status="abstract_only")])
        self.assertFalse(cat.validate_run(self.root, True)["ok"])
        self.cp(accepted_access_limitations=[{"paper_id": "P0001", "reason": "Use only the abstract", "accepted_by": "agent", "source_message": "Assumed"}])
        self.assertFalse(cat.validate_run(self.root, True)["ok"])
        self.cp(accepted_access_limitations=[{"paper_id": "P0001", "reason": "Use only the abstract", "accepted_by": "user", "source_message": "Fixture explicit human instruction"}])
        self.assertTrue(cat.validate_run(self.root, True)["ok"])

    def test_requested_download_is_separate_from_verified_evidence(self):
        self.cp(downloads_requested=True)
        self.ready_run()
        self.assertEqual(self.rows()[0]["download_status"], "pending")
        self.assertFalse(cat.validate_run(self.root, True)["ok"])
        self.cp(accepted_download_limitations=[{"paper_id": "P0001", "reason": "Cannot deliver file", "accepted_by": "user", "source_message": "Fixture explicit acceptance"}])
        self.assertTrue(cat.validate_run(self.root, True)["ok"])

    def test_verified_download_must_exist_and_be_pdf_container(self):
        row = checked_paper(download_status="pdf_verified", download_verification={
            "path": "downloads/example.pdf", "source_url": "https://example.org/article", "version": "published",
            "checked_at": "fixture time", "identity_checked": True, "readability_checked": True})
        cat.upsert_papers(self.root, [row])
        self.assertFalse(cat.validate_run(self.root)["ok"])
        target = self.root / "downloads/example.pdf"
        target.parent.mkdir()
        target.write_text("<html>Login page</html>")
        self.assertFalse(cat.validate_run(self.root)["ok"])
        make_pdf(target, ["This is an offline test document with ample readable native text. " * 3])
        self.assertTrue(cat.validate_run(self.root)["ok"])

    def test_ris_preserves_collective_author_and_unicode_and_counts(self):
        self.ready_run()
        result = cat.export_run(self.root, self.root / "review", ["sources", "index", "evidence", "ris", "downloads"])
        ris = (self.root / "review/citations.ris").read_text()
        self.assertEqual(ris.count("TY  - "), 1)
        self.assertIn("AU  - García, Ana\nAU  - Example Study Group\n", ris)
        self.assertIn("DO  - 10.1234/example", ris)
        with (self.root / "review/sources.csv").open(newline="") as source:
            self.assertEqual(len(list(csv.DictReader(source))), 1)
        self.assertEqual(len(result["files"]), 5)

    def test_ris_rejects_unverified_identity_before_writing_exports(self):
        cat.upsert_papers(self.root, [paper(eligibility_status="included")])
        with self.assertRaises(ValueError):
            cat.export_run(self.root, self.root / "review", ["sources", "ris"])
        self.assertFalse((self.root / "review/sources.csv").exists())

    def test_invalid_manual_record_returns_report_without_crash(self):
        cat.save_rows(self.root / cat.LOCATIONS["papers"], [{"title": "Missing ID"}])
        self.assertFalse(cat.validate_run(self.root)["ok"])

    def test_legacy_extraction_still_exports_but_cannot_be_marked_ready(self):
        self.ready_run()
        legacy = evidence(evidence_id="E0001")
        for field in cat.EXTRACTION_FIELDS:
            if field != "finding":
                legacy.pop(field)
        cat.save_rows(self.root / cat.LOCATIONS["evidence"], [legacy])
        self.assertTrue(cat.validate_run(self.root)["ok"])
        cat.export_run(self.root, self.root / "review", ["evidence"])
        self.assertTrue((self.root / "review/evidence.csv").is_file())
        report = cat.validate_run(self.root, True)
        self.assertFalse(report["ok"])
        self.assertIn("Evidence E0001: missing extraction field sample", report["errors"])

    def test_readiness_rejects_empty_extraction_fields(self):
        self.ready_run()
        for field in cat.EXTRACTION_FIELDS:
            for empty in (None, "   ", {}, {"detail": " "}, []):
                with self.subTest(field=field, value=empty):
                    row = evidence(evidence_id="E0001", **{field: empty})
                    cat.save_rows(self.root / cat.LOCATIONS["evidence"], [row])
                    self.assertIn("Evidence E0001: missing extraction field " + field,
                                  cat.validate_run(self.root, True)["errors"])

    def test_readiness_requires_structured_original_locators(self):
        self.ready_run()
        for locators in ("Results", ["Results"], [{"source": "original"}],
                         [{"source": " ", "location": "Results"}],
                         [{"source": "original", "location": {"page": 4}}]):
            with self.subTest(locators=locators):
                cat.save_rows(self.root / cat.LOCATIONS["evidence"], [evidence(evidence_id="E0001", locators=locators)])
                self.assertIn("Evidence E0001: original locators need source and location strings",
                              cat.validate_run(self.root, True)["errors"])

    def test_supporting_context_requires_text_not_a_boolean_or_mapping(self):
        self.ready_run()
        for context in (True, {"summary": "Some text"}):
            with self.subTest(context=context):
                cat.save_rows(self.root / cat.LOCATIONS["evidence"], [evidence(evidence_id="E0001", supporting_context=context)])
                self.assertFalse(cat.validate_run(self.root, True)["ok"])

    def test_handoff_requires_source_reuse_and_a_readable_document(self):
        self.ready_run()
        self.assertTrue(cat.validate_run(self.root, True)["ok"])
        report = cat.validate_run(self.root, handoff=True)
        self.assertFalse(report["ok"])
        self.assertIn("P0001: source_reuse needs local/remote_only/unavailable status", report["errors"])
        self.assertTrue(any(error.startswith("Handoff document:") for error in report["errors"]))

    def test_handoff_reuses_absolute_original_without_copying_or_mutating(self):
        path = self.handoff_run()
        with tempfile.TemporaryDirectory() as original_root:
            original = Path(original_root) / "existing-original.txt"
            original.write_bytes(path.read_bytes())
            source_bytes = original.read_bytes()
            cat.upsert_papers(self.root, [{"paper_id": "P0001", "source_locations": [{"path": str(original)}],
                "source_reuse": {"status": "local", "paths": [str(original)], "coverage": "Main body",
                                 "limitations": "none observed in fixture"}}])
            path.unlink()
            before = (self.root / cat.LOCATIONS["papers"]).read_bytes()
            self.assertTrue(cat.validate_run(self.root, handoff=True)["ok"])
            self.assertEqual(original.read_bytes(), source_bytes)
            self.assertFalse(path.exists())
            self.assertEqual((self.root / cat.LOCATIONS["papers"]).read_bytes(), before)
            self.assertIn("working/source-text/P0001.txt", [loc["path"] for loc in self.rows()[0]["source_locations"] if "path" in loc])

    def test_reusable_paths_must_reference_the_original_source_register(self):
        path = self.handoff_run()
        records = self.rows()
        records[0]["source_reuse"]["paths"] = [str(path)]
        cat.save_rows(self.root / cat.LOCATIONS["papers"], records)
        # The same existing file still needs an explicit register entry under the supplied path.
        report = cat.validate_run(self.root, handoff=True)
        self.assertFalse(report["ok"])
        self.assertTrue(any("path absent from source_locations" in error for error in report["errors"]))

    def test_handoff_detects_missing_empty_or_nonfile_local_source(self):
        path = self.handoff_run()
        path.unlink()
        self.assertFalse(cat.validate_run(self.root, handoff=True)["ok"])
        path.write_bytes(b"")
        self.assertFalse(cat.validate_run(self.root, handoff=True)["ok"])
        path.unlink()
        path.mkdir()
        self.assertFalse(cat.validate_run(self.root, handoff=True)["ok"])

    def test_remote_reuse_needs_reason_and_original_url_and_reports_limits(self):
        self.handoff_run()
        records = self.rows()
        records[0]["source_reuse"] = {"status": "remote_only", "coverage": "Main body previously read",
                                     "limitations": "Requires reopening in recipient context"}
        records[0]["source_locations"] = []
        cat.save_rows(self.root / cat.LOCATIONS["papers"], records)
        report = cat.validate_run(self.root, handoff=True)
        self.assertIn("P0001: nonlocal source_reuse needs a reason", report["errors"])
        self.assertIn("P0001: remote_only source_reuse needs a stable original URL", report["errors"])
        records[0]["source_reuse"]["reason"] = "Fixture export capability unavailable"
        records[0]["source_locations"] = [{"url": "https://example.org/article"}]
        cat.save_rows(self.root / cat.LOCATIONS["papers"], records)
        report = cat.validate_run(self.root, handoff=True)
        self.assertTrue(report["ok"])
        self.assertTrue(any("recipient access not verified" in warning for warning in report["warnings"]))

    def test_source_reuse_does_not_promote_abstract_evidence_or_accept_limits(self):
        self.handoff_run()
        cat.upsert_papers(self.root, [{"paper_id": "P0001", "full_text_status": "unavailable",
                                    "evidence_status": "abstract_only", "source_reuse": {
                                        "status": "unavailable", "coverage": "Abstract only",
                                        "limitations": "Main body unavailable", "reason": "No access"}}])
        cat.record_rows(self.root, "evidence", [evidence(evidence_id="E0001", verification_status="abstract_only")])
        report = cat.validate_run(self.root, handoff=True)
        self.assertFalse(report["ok"])
        self.assertIn("P0001: full text unresolved", report["errors"])
        self.assertEqual(cat.checkpoint(self.root)["accepted_access_limitations"], [])

    def test_handoff_does_not_require_extraction_or_sources_for_excluded_candidates(self):
        self.handoff_run()
        cat.upsert_papers(self.root, [paper(paper_id="P0002", title="Outside scope",
                                         identifiers={"doi": "10.1234/outside"}, eligibility_status="excluded",
                                         exclusion={"criterion": "Wrong population", "stage": "abstract",
                                                    "basis": "Fixture abstract explicitly states the excluded population"})])
        self.assertTrue(cat.validate_run(self.root, handoff=True)["ok"])

    def test_handoff_cli_implies_ready_and_preserves_pending_records(self):
        self.handoff_run()
        self.cp(pending_queries=["Unsearched consequential branch"])
        before = (self.root / "search-records/checkpoint.json").read_bytes()
        process = subprocess.run([sys.executable, str(SCRIPTS / "catalogue.py"), "validate",
                                  "--root", str(self.root), "--handoff"], capture_output=True, text=True)
        self.assertEqual(process.returncode, 1)
        report = json.loads(process.stdout)
        self.assertTrue(report["ready_check"])
        self.assertTrue(report["handoff_check"])
        self.assertIn("Unresolved checkpoint queue: pending_queries", report["errors"])
        self.assertEqual((self.root / "search-records/checkpoint.json").read_bytes(), before)

    def test_exports_preserve_supporting_context_and_source_reuse(self):
        self.handoff_run()
        cat.export_run(self.root, self.root / "review", ["sources", "index", "evidence"])
        with (self.root / "review/evidence.csv").open(newline="") as source:
            exported = list(csv.DictReader(source))[0]
        self.assertEqual(exported["supporting_context"], evidence()["supporting_context"])
        self.assertEqual(json.loads(exported["sample"])["independent_unit"], "participant")
        with (self.root / "review/sources.csv").open(newline="") as source:
            exported = list(csv.DictReader(source))[0]
        self.assertEqual(json.loads(exported["source_reuse"])["status"], "local")


class SourceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_html_saved_as_pdf_is_rejected(self):
        path = self.root / "article.pdf"
        path.write_text("<!doctype html><html><title>Log in</title><p>Authenticate</p></html>")
        report, text = files.inspect_file(path, expected="pdf")
        self.assertEqual(report["mechanical_status"], "fail")
        self.assertIn("file_type_mismatch", report["errors"])
        self.assertIsNone(text)

    def test_login_html_does_not_establish_article_access(self):
        path = self.root / "article.html"
        path.write_text("<html><title>Sign in</title><p>Access your account.</p></html>")
        report, _ = files.inspect_file(path)
        self.assertEqual(report["mechanical_status"], "unresolved")
        self.assertFalse(report["article_completeness_verified"])

    def test_readable_html_does_not_promote_scientific_checks(self):
        path = self.root / "article.html"
        path.write_text("<html><title>Article</title><article><h1>Methods</h1><p>Actual visible text.</p><script>hidden()</script></article></html>")
        before = path.read_bytes()
        report, text = files.inspect_file(path)
        self.assertEqual(report["mechanical_status"], "pass")
        self.assertNotIn("hidden()", text)
        self.assertFalse(report["identity_verified"])
        self.assertFalse(report["claims_verified"])
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(report["sha256"], hashlib.sha256(before).hexdigest())

    def test_missing_parser_returns_unresolved_instead_of_pass(self):
        path = self.root / "article.pdf"
        make_pdf(path, ["Test text"])
        with patch.dict(sys.modules, {"pypdf": None}):
            report, text = files.inspect_file(path)
        self.assertEqual(report["mechanical_status"], "unresolved")
        self.assertIsNone(text)

    def test_source_output_cannot_overwrite_original(self):
        path = self.root / "article.txt"
        path.write_text("Original text")
        process = subprocess.run([sys.executable, str(SCRIPTS / "source_files.py"), str(path), "--text-out", str(path)], capture_output=True, text=True)
        self.assertEqual(process.returncode, 1)
        self.assertEqual(path.read_text(), "Original text")

    def test_empty_file_is_failure(self):
        path = self.root / "empty.pdf"
        path.write_bytes(b"")
        self.assertEqual(files.inspect_file(path)[0]["mechanical_status"], "fail")

    @unittest.skipUnless(importlib.util.find_spec("pypdf"), "Optional PDF parser absent")
    def test_pdf_extraction_pages_and_reference_doi_are_not_identity_proof(self):
        path = self.root / "article.pdf"
        texts = [f"Page {n}: " + "Native article text for the offline fixture. " * 4 for n in range(1, 6)]
        texts[-1] += "Reference DOI 10.1234/expected"
        make_pdf(path, texts)
        before = path.read_bytes()
        report, sampled = files.inspect_file(path, expected_doi="10.1234/expected")
        self.assertEqual(report["page_count"], 5)
        self.assertEqual(report["sampled_pages"], [1, 3, 5])
        self.assertNotIn("<!-- PDF page 2 -->", sampled)
        self.assertFalse(report["expected_doi_in_first_page_or_text"])
        report_all, full = files.inspect_file(path, extract_all=True)
        self.assertEqual(full.count("<!-- PDF page "), 5)
        self.assertEqual(report_all["text_scope"], "all_pages")
        self.assertEqual(path.read_bytes(), before)

    @unittest.skipUnless(importlib.util.find_spec("pypdf"), "Optional PDF parser absent")
    def test_corrupt_pdf_reports_failure_without_title_check_crash(self):
        path = self.root / "corrupt.pdf"
        path.write_bytes(b"%PDF-1.4\nnot a PDF structure")
        report, _ = files.inspect_file(path, expected_title="Expected article", expected_doi="10.1234/example")
        self.assertEqual(report["mechanical_status"], "fail")
        self.assertFalse(report["expected_title_in_first_page_or_text"])

    @unittest.skipUnless(importlib.util.find_spec("pypdf"), "Optional PDF parser absent")
    def test_blank_pdf_requests_inspection_or_ocr(self):
        path = self.root / "blank.pdf"
        make_pdf(path, [""])
        report, _ = files.inspect_file(path)
        self.assertEqual(report["mechanical_status"], "unresolved")


if __name__ == "__main__":
    unittest.main()
