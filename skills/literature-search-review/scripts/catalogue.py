#!/usr/bin/env python3
"""Local literature records, exact-ID deduplication, consistency checks, exports.

Standard library only. No network, eligibility decisions, or proof that IDs exist.
Use one writer per run. Inputs are JSON objects, arrays, or JSONL files.
"""
import argparse
import copy
import csv
import json
import os
import re
import sys
import tempfile
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlsplit

STATES = {
    "eligibility_status": {"unscreened", "potentially_eligible", "included", "excluded", "unresolved"},
    "abstract_status": {"not_fetched", "complete", "missing", "partial"},
    "full_text_status": {"not_attempted", "verified", "partial", "unavailable", "waiting_user"},
    "evidence_status": {"not_extracted", "extracted_unverified", "verified_for_question", "needs_followup", "abstract_only"},
    "download_status": {"not_requested", "pending", "pdf_verified", "html_print_verified", "unresolved"},
}
DEFAULTS = dict(zip(STATES, ("unscreened", "not_fetched", "not_attempted", "not_extracted", "not_requested")))
LOCATIONS = {"papers": "search-records/papers.jsonl", "search": "search-records/search-log.jsonl",
             "access": "search-records/access-log.jsonl", "evidence": "working/evidence.jsonl"}
EXTRACTION_FIELDS = ("subquestion", "design", "sample", "measure", "finding", "uncertainty",
                     "limitations", "inference", "supporting_context")


def now():
    return datetime.now(timezone.utc).isoformat()


def load_rows(path):
    if not Path(path).exists():
        return []
    raw = Path(path).read_text(encoding="utf-8").strip()
    if not raw:
        return []
    try:
        data = json.loads(raw)
        rows = data if isinstance(data, list) else [data]
    except json.JSONDecodeError:
        rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
    if any(not isinstance(row, dict) for row in rows):
        raise ValueError("Every input record must be a JSON object")
    return rows


def atomic_write(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as f:
        temporary = Path(f.name)
        f.write(text)
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def save_rows(path, rows):
    atomic_write(path, "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows))


def normalize_id(kind, value):
    if value is None or value == "":
        return None
    value = str(value).strip()
    if kind == "doi":
        if value.lower().startswith(("https://doi.org/", "http://doi.org/", "https://dx.doi.org/", "http://dx.doi.org/")):
            value = unquote(urlsplit(value).path.lstrip("/"))
        value = re.sub(r"^doi\s*:\s*", "", value, flags=re.I).lower()
        valid = bool(re.fullmatch(r"10\.\d{4,9}/\S+", value))
    elif kind == "pmid":
        value = re.sub(r"^pmid\s*:\s*", "", value, flags=re.I)
        valid = value.isdigit() and int(value) > 0
        if valid:
            value = str(int(value))
    elif kind == "pmcid":
        value = value.upper()
        if value.isdigit():
            value = "PMC" + value
        valid = bool(re.fullmatch(r"PMC[1-9]\d*", value))
    elif kind == "openalex":
        value = value.rstrip("/").split("/")[-1].upper()
        valid = bool(re.fullmatch(r"W[1-9]\d*", value))
    else:
        raise ValueError("Unknown identifier kind: " + kind)
    if not valid:
        raise ValueError(f"Malformed {kind}: {value!r}")
    return value


def normalized_ids(record):
    ids = record.get("identifiers", {})
    if not isinstance(ids, dict):
        raise ValueError("identifiers must be an object")
    return {kind: normalize_id(kind, value) for kind, value in ids.items()}


def unique(values):
    seen, result = set(), []
    for value in values:
        key = json.dumps(value, ensure_ascii=False, sort_keys=True)
        if key not in seen:
            seen.add(key)
            result.append(value)
    return result


def next_id(records, prefix, key):
    used = {str(r[key]) for r in records}
    if key == "paper_id":
        used.update(a for r in records for a in r.get("aliases", []))
    numbers = [int(x[len(prefix):]) for x in used if re.fullmatch(prefix + r"\d+", x)]
    return prefix + f"{max(numbers, default=0) + 1:04d}"


def init_run(root, question, mode="targeted", policy="full_text", downloads=False):
    root = Path(root)
    protected = [root / x for x in LOCATIONS.values()] + [root / "search-records/checkpoint.json", root / "search-records/protocol.md"]
    if any(p.exists() for p in protected):
        raise ValueError("Run already has records: resume it; initialization never overwrites them")
    for location in LOCATIONS.values():
        atomic_write(root / location, "")
    checkpoint = {"run_id": uuid.uuid4().hex, "created_at": now(), "phase": "planning",
                  "mode": mode, "evidence_policy": policy, "downloads_requested": downloads,
                  "protocol_ready": False, "search_plan_accounted": False, "gap_audit_done": False,
                  "limitations_reported": False, "pending_papers": [], "pending_queries": [],
                  "deferred_fetches": [], "accepted_access_limitations": [], "accepted_download_limitations": []}
    atomic_write(root / "search-records/checkpoint.json", json.dumps(checkpoint, ensure_ascii=False, indent=2) + "\n")
    protocol = (f"# Search protocol\n\nQuestion: {question}\n\nMode: {mode}\n\nEvidence policy: {policy}\n\n"
                f"Article downloads requested: {downloads}\n\n"
                "Planning is incomplete. Define eligibility, operational concepts, search branches, seed policy, "
                "limits, and deliverables before screening; then set protocol_ready in the checkpoint.\n")
    atomic_write(root / "search-records/protocol.md", protocol)
    return {"root": str(root.resolve()), "run_id": checkpoint["run_id"], "phase": "planning"}


def checkpoint(root):
    p = Path(root) / "search-records/checkpoint.json"
    if not p.exists():
        raise ValueError("Initialize a run first")
    return json.loads(p.read_text(encoding="utf-8"))


def upsert_papers(root, incoming):
    cp = checkpoint(root)
    path = Path(root) / LOCATIONS["papers"]
    records = load_rows(path)
    processed, created = [], 0
    for raw in incoming:
        row = copy.deepcopy(raw)
        for field in ("aliases", "discovery_routes", "source_locations", "related_papers"):
            if field in row and not isinstance(row[field], list):
                raise ValueError(field + " must be an array")
        if "title" in row and not isinstance(row["title"], str):
            raise ValueError("title must be a string")
        ids = normalized_ids(row)
        proposed = row.get("paper_id")
        matches = []
        for old in records:
            old_ids = normalized_ids(old)
            by_name = proposed and proposed in [old["paper_id"]] + old.get("aliases", [])
            by_id = any(value and old_ids.get(kind) == value for kind, value in ids.items())
            if by_name or by_id:
                matches.append(old)
        if len(matches) > 1:
            raise ValueError("Identifiers bridge multiple papers; resolve identity rather than auto-merging")
        if matches:
            old = matches[0]
            old_ids = normalized_ids(old)
            for kind, value in ids.items():
                if value and old_ids.get(kind) and value != old_ids[kind]:
                    raise ValueError(f"Conflicting {kind} for {old['paper_id']}; no records written")
            if old.get("title") and row.get("title") and title_key(old["title"]) != title_key(row["title"]):
                raise ValueError("Conflicting titles for an exact-ID match; resolve before updating")
            combined = copy.deepcopy(old)
            combined.update(row)
            combined["paper_id"] = old["paper_id"]
            combined["identifiers"] = {**old_ids, **{k: v for k, v in ids.items() if v}}
            for field in ("aliases", "discovery_routes", "source_locations", "related_papers"):
                combined[field] = unique(old.get(field, []) + row.get(field, []))
            if proposed and proposed != old["paper_id"]:
                combined["aliases"] = unique(combined["aliases"] + [proposed])
            records[records.index(old)] = combined
        else:
            combined = {**DEFAULTS, **row}
            combined["paper_id"] = proposed or next_id(records, "P", "paper_id")
            combined["identifiers"] = ids
            combined.setdefault("aliases", [])
            records.append(combined)
            created += 1
        if cp.get("downloads_requested") and (combined["eligibility_status"] == "included" or combined.get("substantively_cited")) and combined["download_status"] == "not_requested":
            combined["download_status"] = "pending"
        combined["updated_at"] = now()
        processed.append(combined["paper_id"])
    issues = paper_issues(records)
    if issues:
        raise ValueError("; ".join(issues))
    save_rows(path, records)
    return {"processed": len(processed), "created": created, "paper_ids": processed}


def title_key(value):
    return "".join(c for c in value.casefold() if c.isalnum())


def paper_issues(records):
    issues, names, ids_seen = [], {}, {}
    for paper in records:
        pid = paper.get("paper_id")
        if not isinstance(pid, str) or not pid.strip():
            issues.append("Missing/non-string paper_id")
            continue
        aliases = paper.get("aliases", [])
        if not isinstance(aliases, list) or any(not isinstance(a, str) or not a.strip() for a in aliases):
            issues.append(pid + ": aliases must be nonempty strings")
            aliases = []
        for name in [pid] + aliases:
            if name in names:
                issues.append(f"Duplicate/colliding paper ID or alias: {name}")
            names[name] = pid
        for field, allowed in STATES.items():
            if not isinstance(paper.get(field), str) or paper.get(field) not in allowed:
                issues.append(f"{pid}: invalid/missing {field}")
        try:
            ids = normalized_ids(paper)
            for kind, value in ids.items():
                if value:
                    key = (kind, value)
                    if key in ids_seen:
                        issues.append(f"{pid}: duplicate {kind} belongs to {ids_seen[key]}")
                    ids_seen[key] = pid
            proof = paper.get("identity_verification", {})
            if not isinstance(proof, dict):
                raise ValueError("identity_verification must be an object")
            if proof.get("status") == "verified":
                if not paper.get("title") or not proof.get("title") or not proof.get("source") or not proof.get("checked_at"):
                    issues.append(pid + ": verified identity needs record/observed title, source and checked_at")
                if any(ids.values()) and not any(proof.get("identifiers", {}).values()):
                    issues.append(pid + ": verified identity needs an observed identifier")
                for kind, observed in proof.get("identifiers", {}).items():
                    value = normalize_id(kind, observed)
                    if value and ids.get(kind) != value:
                        issues.append(f"{pid}: observed source {kind} disagrees with record")
                if proof.get("title") and title_key(proof["title"]) != title_key(paper["title"]):
                    issues.append(pid + ": observed title disagrees with record")
        except (ValueError, TypeError, AttributeError) as exc:
            issues.append(pid + ": " + str(exc))
        exclusion = paper.get("exclusion", {})
        if paper.get("eligibility_status") == "excluded" and (not isinstance(exclusion, dict) or not all(exclusion.get(x) for x in ("criterion", "stage", "basis"))):
            issues.append(pid + ": exclusion needs criterion, stage and basis")
        authors = paper.get("authors", [])
        if not isinstance(authors, list):
            issues.append(pid + ": authors must be an array")
            authors = []
        for author in authors:
            if not isinstance(author, dict) or not (author.get("family") or author.get("collective") or author.get("literal")):
                issues.append(pid + ": malformed author; preserve a literal name if parsing is unresolved")
            elif author.get("collective") and (author.get("given") or author.get("family")):
                issues.append(pid + ": collective and individual author fields cannot be mixed")
        if paper.get("full_text_status") == "verified":
            body = paper.get("full_text_verification", {})
            if not isinstance(body, dict) or body.get("main_body_complete") is not True or not body.get("source") or not body.get("checked_at"):
                issues.append(pid + ": verified full text needs source, checked_at and main_body_complete=true")
        if paper.get("download_status") in ("pdf_verified", "html_print_verified"):
            delivery = paper.get("download_verification", {})
            required = ("path", "source_url", "checked_at", "version")
            if not isinstance(delivery, dict) or not all(delivery.get(k) for k in required) or delivery.get("identity_checked") is not True or delivery.get("readability_checked") is not True:
                issues.append(pid + ": verified download needs file provenance, version and identity/readability checks")
    return issues


def record_rows(root, kind, rows):
    checkpoint(root)
    path = Path(root) / LOCATIONS[kind]
    existing = load_rows(path)
    for raw in rows:
        row = copy.deepcopy(raw)
        row.setdefault("timestamp", now())
        if kind in ("search", "access"):
            row.setdefault("event_id", ("S" if kind == "search" else "A") + uuid.uuid4().hex[:12])
        if kind == "evidence":
            row.setdefault("evidence_id", next_id(existing, "E", "evidence_id"))
            old = next((r for r in existing if r.get("evidence_id") == row["evidence_id"]), None)
            if old is None:
                existing.append(row)
            else:
                existing[existing.index(old)] = {**old, **row}
        else:
            existing.append(row)
    save_rows(path, existing)
    return {"kind": kind, "recorded": len(rows)}


def acceptances(cp, field):
    accepted, issues = set(), []
    for entry in cp.get(field, []):
        if not isinstance(entry, dict) or not all(entry.get(k) for k in ("paper_id", "reason", "source_message")) or entry.get("accepted_by") != "user":
            issues.append(field + ": needs paper_id, reason, accepted_by=user and source_message")
        else:
            accepted.add(entry["paper_id"])
    return accepted, issues


def has_content(value):
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, dict):
        return any(has_content(v) for v in value.values())
    if isinstance(value, list):
        return any(has_content(v) for v in value)
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def extraction_issues(ev):
    label = "Evidence " + str(ev.get("evidence_id"))
    issues = [f"{label}: missing extraction field {field}" for field in EXTRACTION_FIELDS
              if not has_content(ev.get(field))]
    if has_content(ev.get("supporting_context")) and not isinstance(ev["supporting_context"], str):
        issues.append(label + ": supporting_context must be a labelled excerpt/description string")
    locators = ev.get("locators")
    if not isinstance(locators, list) or not locators or any(
            not isinstance(loc, dict) or not all(isinstance(loc.get(k), str) and loc[k].strip()
                                                for k in ("source", "location")) for loc in locators):
        issues.append(label + ": original locators need source and location strings")
    return issues


def readable_file_issue(root, path):
    if not isinstance(path, str) or not path.strip():
        return "file path missing/invalid"
    target = Path(path)
    if not target.is_absolute():
        target = Path(root) / target
    try:
        with target.open("rb") as source:
            if not source.read(1):
                return "file empty: " + str(target)
    except (OSError, ValueError) as exc:
        return "file unreadable: " + str(target) + " (" + str(exc) + ")"
    return None


def source_reuse_issues(root, paper):
    label, issues, warnings = paper["paper_id"], [], []
    reuse = paper.get("source_reuse")
    if not isinstance(reuse, dict) or reuse.get("status") not in ("local", "remote_only", "unavailable"):
        return [label + ": source_reuse needs local/remote_only/unavailable status"], warnings
    for field in ("coverage", "limitations"):
        if not isinstance(reuse.get(field), str) or not reuse[field].strip():
            issues.append(label + ": source_reuse needs " + field)
    locations = paper.get("source_locations", [])
    if reuse["status"] == "local":
        recorded_paths = [loc["path"] for loc in locations if isinstance(loc, dict) and "path" in loc]
        paths = reuse.get("paths", recorded_paths)
        if not isinstance(paths, list):
            return issues + [label + ": source_reuse paths must be an array"], warnings
        if not paths:
            issues.append(label + ": local source_reuse needs source_locations paths")
        for path in paths:
            if path not in recorded_paths:
                issues.append(label + ": reusable source path absent from source_locations: " + str(path))
            issue = readable_file_issue(root, path)
            if issue:
                issues.append(label + ": reusable source " + issue)
    else:
        if not isinstance(reuse.get("reason"), str) or not reuse["reason"].strip():
            issues.append(label + ": nonlocal source_reuse needs a reason")
        if reuse["status"] == "remote_only":
            urls = [loc.get("url") for loc in locations if isinstance(loc, dict)]
            valid_url = False
            for url in urls:
                if not isinstance(url, str):
                    continue
                try:
                    parsed = urlsplit(url)
                except ValueError:
                    continue
                valid_url = valid_url or (parsed.scheme in ("http", "https") and bool(parsed.netloc))
            if not valid_url:
                issues.append(label + ": remote_only source_reuse needs a stable original URL")
        warnings.append(label + ": original source must be reopened/reacquired; recipient access not verified")
    return issues, warnings


def validate_run(root, ready=False, handoff=False):
    ready = ready or handoff
    cp = checkpoint(root)
    papers = load_rows(Path(root) / LOCATIONS["papers"])
    evidence = load_rows(Path(root) / LOCATIONS["evidence"])
    issues, warnings = paper_issues(papers), []
    # Invalid records still produce a useful error report rather than a crash.
    if issues:
        return {"ok": False, "ready_check": ready, "handoff_check": handoff,
                "errors": issues, "warnings": [], "paper_count": len(papers)}
    lookup = {name: p for p in papers for name in [p["paper_id"]] + p.get("aliases", [])}
    ev_by_paper, ev_ids = {}, set()
    for ev in evidence:
        eid, pid = ev.get("evidence_id"), ev.get("paper_id")
        if not eid or eid in ev_ids:
            issues.append("Missing/duplicate evidence_id")
        ev_ids.add(eid)
        if pid not in lookup:
            issues.append(f"Evidence {eid}: unknown paper_id {pid}")
            continue
        ev_by_paper.setdefault(lookup[pid]["paper_id"], []).append(ev)
        status = ev.get("verification_status")
        if status not in ("unverified", "verified", "abstract_only", "needs_followup"):
            issues.append(f"Evidence {eid}: invalid verification_status")
        if status in ("verified", "abstract_only") and (not ev.get("locators") or not ev.get("finding")):
            issues.append(f"Evidence {eid}: checked evidence needs finding and source locators")
        for component in ev.get("required_components", []):
            if component.get("status") not in ("checked", "unresolved") or not component.get("locator"):
                issues.append(f"Evidence {eid}: needed component requires locator and checked/unresolved status")
            if ev.get("verification_status") == "verified" and component.get("status") != "checked":
                issues.append(f"Evidence {eid}: required component is unresolved")
    for kind in ("search", "access"):
        events = load_rows(Path(root) / LOCATIONS[kind])
        latest = {event.get("event_id", str(i)): i for i, event in enumerate(events)}
        if ready and kind == "search" and not events:
            issues.append("No search/corpus accounting events")
        for i, event in enumerate(events):
            referenced = event.get("retrieved_paper_ids", []) + event.get("seed_paper_ids", [])
            if event.get("paper_id"):
                referenced.append(event["paper_id"])
            for pid in referenced:
                if pid not in lookup:
                    issues.append(f"{kind} event references unknown paper {pid}")
            if kind == "search" and latest[event.get("event_id", str(i))] == i and event.get("status") == "limited" and not event.get("limitations"):
                issues.append("Limited search event lacks a limitation")
            if ready and kind == "search" and latest[event.get("event_id", str(i))] == i and event.get("status") not in ("complete", "limited"):
                issues.append("Search/seed/citation event remains unaccounted")
            if kind == "search":
                event_type = event.get("event_type")
                if event_type not in ("query", "citation", "seed_selection", "corpus", "amendment"):
                    issues.append("Search event has invalid/missing event_type")
                if not event.get("purpose") or not event.get("timestamp"):
                    issues.append("Search event needs purpose and timestamp")
                if event_type in ("query", "citation"):
                    if not event.get("source") or not isinstance(event.get("submitted_request"), dict) or not event["submitted_request"]:
                        issues.append("Query/citation event needs source and exact submitted_request")
                    if "retrieved_paper_ids" not in event:
                        issues.append("Query/citation event needs actual retrieved_paper_ids, possibly empty")
                if event_type == "citation" and (event.get("direction") not in ("backward", "forward", "similarity") or not event.get("seed_paper_ids")):
                    issues.append("Citation event needs direction and seed_paper_ids")
    for paper in papers:
        if paper["download_status"] in ("pdf_verified", "html_print_verified"):
            file_path = Path(paper["download_verification"]["path"])
            if not file_path.is_absolute():
                file_path = Path(root) / file_path
            if not file_path.is_file() or not file_path.stat().st_size:
                issues.append(paper["paper_id"] + ": verified download file missing/empty")
            else:
                with file_path.open("rb") as source_file:
                    if source_file.read(5) != b"%PDF-":
                        issues.append(paper["paper_id"] + ": PDF/HTML-print delivery lacks a PDF signature")
    access_ok, access_issues = acceptances(cp, "accepted_access_limitations")
    download_ok, download_issues = acceptances(cp, "accepted_download_limitations")
    issues.extend(access_issues + download_issues)
    for pid in access_ok | download_ok:
        if pid not in lookup:
            issues.append("Accepted limitation references unknown paper: " + pid)
    if ready:
        for field in ("protocol_ready", "search_plan_accounted", "gap_audit_done", "limitations_reported"):
            if cp.get(field) is not True:
                issues.append("Checkpoint missing completion attestation: " + field)
        for field in ("pending_papers", "pending_queries", "deferred_fetches"):
            if cp.get(field):
                issues.append("Unresolved checkpoint queue: " + field)
        for paper in papers:
            pid = paper["paper_id"]
            accepted = pid in access_ok or any(a in access_ok for a in paper.get("aliases", []))
            if paper["eligibility_status"] in ("unscreened", "potentially_eligible", "unresolved") and not accepted:
                issues.append(pid + ": candidate disposition unresolved")
            used = paper["eligibility_status"] == "included" or paper.get("substantively_cited")
            if not used:
                continue
            if not paper.get("review_treatment"):
                issues.append(pid + ": review treatment not accounted for")
            if paper.get("identity_verification", {}).get("status") != "verified":
                issues.append(pid + ": identity not verified")
            abstract_allowed = cp.get("evidence_policy") == "abstract_only" or accepted
            good_statuses = {"verified_for_question"} | ({"abstract_only"} if abstract_allowed else set())
            if paper["evidence_status"] not in good_statuses:
                issues.append(pid + ": question evidence not verified")
            if not abstract_allowed and paper["full_text_status"] != "verified":
                issues.append(pid + ": full text unresolved")
            allowed_ev = {"verified"} | ({"abstract_only"} if abstract_allowed else set())
            usable = [e for e in ev_by_paper.get(pid, []) if e.get("verification_status") in allowed_ev]
            if not usable:
                issues.append(pid + ": no checked evidence row")
            for ev in usable:
                issues.extend(extraction_issues(ev))
            if any(e.get("verification_status") not in allowed_ev for e in ev_by_paper.get(pid, [])):
                issues.append(pid + ": evidence extraction includes unresolved rows")
            if handoff:
                source_issues, source_warnings = source_reuse_issues(root, paper)
                issues.extend(source_issues)
                warnings.extend(source_warnings)
            download_accepted = pid in download_ok or any(a in download_ok for a in paper.get("aliases", []))
            if cp.get("downloads_requested") and paper["download_status"] not in ("pdf_verified", "html_print_verified") and not download_accepted:
                issues.append(pid + ": requested download unresolved")
    if handoff:
        issue = readable_file_issue(root, "working/handoff.md")
        if issue:
            issues.append("Handoff document: " + issue)
        warnings.append("Handoff checks establish local structure/readability, not source completeness, remote access, or another agent's access.")
    warnings.append("Local consistency checks do not prove identifier existence, claim support, or exhaustive retrieval; completion flags are agent attestations.")
    return {"ok": not issues, "ready_check": ready, "handoff_check": handoff, "errors": issues, "warnings": warnings,
            "paper_count": len(papers), "states": {field: dict(Counter(p[field] for p in papers if field in p)) for field in STATES},
            "established_study_ids": len({p["study_id"] for p in papers if p.get("study_id")}),
            "papers_without_study_id": sum(not p.get("study_id") for p in papers)}


def author_text(author):
    if author.get("collective") or author.get("literal"):
        return author.get("collective") or author["literal"]
    return author["family"] + (", " + author["given"] if author.get("given") else "")


def ris_record(paper):
    if paper.get("identity_verification", {}).get("status") != "verified":
        raise ValueError(paper["paper_id"] + ": RIS requires verified bibliographic identity")
    def tag(key, value):
        return f"{key}  - {str(value).replace(chr(10), ' ').replace(chr(13), ' ')}\n" if value is not None and value != "" else ""
    types = {"article": "JOUR", "review": "JOUR", "book": "BOOK", "book-chapter": "CHAP", "report": "RPRT", "dissertation": "THES"}
    result = tag("TY", types.get(paper.get("publication_type"), "GEN")) + tag("ID", paper["paper_id"]) + tag("TI", paper.get("title"))
    result += "".join(tag("AU", author_text(a)) for a in paper.get("authors", []))
    result += tag("JO", paper.get("venue")) + tag("PY", paper.get("year"))
    for key, field in (("VL", "volume"), ("IS", "issue"), ("SP", "start_page"), ("EP", "end_page")):
        result += tag(key, paper.get(field))
    doi = normalized_ids(paper).get("doi")
    result += tag("DO", doi) + tag("UR", "https://doi.org/" + doi if doi else paper.get("article_url"))
    return result + "ER  - \n\n"


def csv_file(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            output = {k: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v for k, v in row.items()}
            writer.writerow(output)


def export_run(root, out, formats):
    report = validate_run(root)
    if not report["ok"]:
        raise ValueError("Repair records before export: " + "; ".join(report["errors"]))
    papers = load_rows(Path(root) / LOCATIONS["papers"])
    evidence = load_rows(Path(root) / LOCATIONS["evidence"])
    selected = [p for p in papers if p["eligibility_status"] == "included" or p.get("substantively_cited")]
    ris = "".join(ris_record(p) for p in selected) if "ris" in formats else None
    out, files = Path(out), []
    if "sources" in formats:
        fields = ["paper_id", "title", "authors", "year", "venue", "identifiers", "article_url"] + list(STATES) + ["source_locations", "source_reuse", "exclusion", "unresolved_reason"]
        csv_file(out / "sources.csv", papers, fields)
        files.append("sources.csv")
    if "index" in formats:
        csv_file(out / "included-index.csv", selected, ["paper_id", "title", "review_role", "evidence_status", "review_treatment"])
        files.append("included-index.csv")
    if "evidence" in formats:
        csv_file(out / "evidence.csv", evidence, ["evidence_id", "paper_id", "subquestion", "design", "sample", "measure", "finding", "uncertainty", "limitations", "inference", "supporting_context", "locators", "verification_status", "required_components"])
        files.append("evidence.csv")
    if "downloads" in formats:
        deliveries = [{"paper_id": p["paper_id"], "title": p.get("title"), "status": p["download_status"],
                       **p.get("download_verification", {}), "unresolved_reason": p.get("unresolved_reason"),
                       "warnings": p.get("warnings", [])} for p in selected]
        csv_file(out / "download-manifest.csv", deliveries,
                 ["paper_id", "title", "status", "path", "source_url", "version", "checked_at", "sha256", "page_count", "warnings", "unresolved_reason"])
        files.append("download-manifest.csv")
    if ris is not None:
        atomic_write(out / "citations.ris", ris)
        files.append("citations.ris")
    return {"out": str(out.resolve()), "files": files, "papers": len(papers), "included_or_cited": len(selected)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("init", "upsert", "record", "validate", "summary", "export"):
        sub = commands.add_parser(name)
        sub.add_argument("--root", required=True)
        if name == "init":
            sub.add_argument("--question", required=True)
            sub.add_argument("--mode", choices=("targeted", "scoping", "systematic", "supplied_corpus", "design", "update"), default="targeted")
            sub.add_argument("--policy", choices=("full_text", "abstract_only"), default="full_text")
            sub.add_argument("--downloads", action="store_true")
        if name in ("upsert", "record"):
            sub.add_argument("--input", required=True)
        if name == "record":
            sub.add_argument("--kind", choices=("search", "access", "evidence"), required=True)
        if name == "validate":
            sub.add_argument("--ready", action="store_true")
            sub.add_argument("--handoff", action="store_true", help="Check readiness plus source reuse and the handoff document")
        if name == "export":
            sub.add_argument("--out")
            sub.add_argument("--formats", nargs="+", choices=("sources", "index", "evidence", "ris", "downloads"), default=["sources", "index"])
    args = parser.parse_args()
    try:
        if args.command == "init":
            result = init_run(args.root, args.question, args.mode, args.policy, args.downloads)
        elif args.command == "upsert":
            result = upsert_papers(args.root, load_rows(args.input))
        elif args.command == "record":
            result = record_rows(args.root, args.kind, load_rows(args.input))
        elif args.command in ("validate", "summary"):
            result = validate_run(args.root, getattr(args, "ready", False), getattr(args, "handoff", False))
        else:
            result = export_run(args.root, args.out or Path(args.root) / "review", args.formats)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get("ok", True) else 1
    except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())
