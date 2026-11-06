"""Public PMC recovery and bounded Asta calls; no scientific verification claims."""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import sqlite3
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent
STATE = Path(os.environ.get("LITERATURE_ACCESS_STATE", ROOT / "state"))
ASTA_URL = "https://asta-tools.allen.ai/mcp/v1"
EPMC = "https://www.ebi.ac.uk/europepmc/webservices/rest"
PARSER_VERSION = 1


class AccessError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class Store:
    def __init__(self, root: Path = STATE):
        self.root = root
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.db = root / "state.sqlite3"
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, at REAL, value TEXT);
                CREATE TABLE IF NOT EXISTS health (service TEXT PRIMARY KEY, at REAL,
                    retry_at REAL, status TEXT, detail TEXT);
                CREATE TABLE IF NOT EXISTS audit (id INTEGER PRIMARY KEY, at REAL,
                    service TEXT, operation TEXT, status TEXT, elapsed REAL);
            """)
        self.db.chmod(0o600)

    def connect(self):
        return sqlite3.connect(self.db, timeout=5)

    def cached(self, key: str, ttl: float = 86400):
        with self.connect() as db:
            row = db.execute("SELECT at,value FROM cache WHERE key=?", (key,)).fetchone()
        return json.loads(row[1]) if row and time.time() - row[0] < ttl else None

    def cache(self, key: str, value: dict):
        with self.connect() as db:
            db.execute("INSERT OR REPLACE INTO cache VALUES (?,?,?)", (key, time.time(), json.dumps(value)))

    def health(self, service: str):
        with self.connect() as db:
            row = db.execute("SELECT at,retry_at,status,detail FROM health WHERE service=?", (service,)).fetchone()
        if not row:
            return {"status": "not_tested", "blocked": False}
        return dict(zip(["checked_at", "retry_at", "status", "detail"], row), blocked=row[1] > time.time())

    def mark(self, service: str, status: str, detail: str = "", cooldown: float = 0):
        now = time.time()
        with self.connect() as db:
            db.execute("INSERT OR REPLACE INTO health VALUES (?,?,?,?,?)",
                       (service, now, now + cooldown, status, detail[:500]))

    def audit(self, service: str, operation: str, status: str, elapsed: float):
        with self.connect() as db:
            db.execute("INSERT INTO audit(at,service,operation,status,elapsed) VALUES (?,?,?,?,?)",
                       (time.time(), service, operation, status, elapsed))


def normalized_identifier(value: str):
    value = value.strip()
    value = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", value, flags=re.I)
    m = re.fullmatch(r"(?:https?://(?:www\.)?(?:ncbi\.nlm\.nih\.gov/pmc|pmc\.ncbi\.nlm\.nih\.gov)/articles/)?(PMC\d+)/?", value, re.I)
    if m:
        return "pmcid", m[1].upper()
    m = re.fullmatch(r"(?:https?://pubmed\.ncbi\.nlm\.nih\.gov/|PMID:)?(\d{1,10})/?", value, re.I)
    if m:
        return "pmid", m[1]
    value = re.sub(r"^DOI:", "", value, flags=re.I)
    if re.fullmatch(r'10\.\d{4,9}/[^\s"\\<>]+', value, re.I):
        return "doi", value.lower()
    raise AccessError("invalid_identifier", "Provide an exact PMCID, PMID, DOI, or its canonical article URL.")


def meta(soup, name):
    el = soup.find("meta", attrs={"name": name})
    return el.get("content", "").strip() if el else ""


def parse_pmc_html(html: str, pmcid: str, expected: tuple[str, str] | None = None):
    soup = BeautifulSoup(html, "html.parser")
    article = soup.find("article")
    body = article.select_one(".main-article-body") if article else None
    title = meta(soup, "citation_title")
    if not body or not title:
        challenge = any(x in html[:20000].lower() for x in ["recaptcha", "checking your browser", "client challenge"])
        raise AccessError("challenge_page" if challenge else "no_body", "PMC returned a challenge, landing page, or abstract without a detectable main body.")
    identifiers = {"pmcid": pmcid, "doi": meta(soup, "citation_doi").lower(), "pmid": meta(soup, "citation_pmid")}
    if expected and expected[0] != "pmcid" and identifiers.get(expected[0]) != expected[1]:
        raise AccessError("identity_mismatch", "The article metadata does not match the requested identifier.")
    abstract_el = body.select_one("section.abstract")
    abstract = abstract_el.get_text(" ", strip=True) if abstract_el else ""
    for el in body.select("script, style, nav, .abstract, .kwd-group, .ref-list"):
        el.decompose()
    blocks, outline, figures, equations = [], [], [], []
    position = 0
    for el in body.find_all(["h2", "h3", "h4", "h5", "p", "table", "figure", "disp-formula"]):
        if el.find_parent(["p", "table", "figure", "disp-formula"]):
            continue
        is_equation = el.name == "disp-formula" or "disp-formula" in el.get("class", [])
        text = " ".join(el.get_text(" ", strip=True).split())
        if is_equation:
            images = [urljoin(f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/", x["src"])
                      for x in el.find_all("img") if x.get("src")]
            equations.append({"id": el.get("id", ""), "original_markup": str(el), "images": images})
            if not text:
                text = f"[Equation image: inspect original #{el.get('id', '')}]"
        if not text:
            continue
        section = el if el.name.startswith("h") else el.find_parent("section")
        if el.name.startswith("h"):
            section = el.find_parent("section") or el
            outline.append({"heading": text, "id": section.get("id", ""), "start_char": position})
        if el.name == "figure":
            figures.append({"id": el.get("id", ""), "caption": text,
                            "images": [urljoin(f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/", x.get("src", ""))
                                       for x in el.find_all("img") if x.get("src")]})
        blocks.append(text)
        position += len(text) + 2
    text = "\n\n".join(blocks)
    paragraph_count = len(body.find_all("p"))
    if paragraph_count < 3 or len(text) < 800 or not outline:
        raise AccessError("no_body", "Too little structured main-body text was detected; refusing to label an abstract as a full article.")
    notices = [x.get_text(" ", strip=True) for x in soup.select(".article-notes, .article-notice, .retraction")]
    return {"title": title, "identifiers": identifiers,
            "authors": [x.get("content", "") for x in soup.find_all("meta", attrs={"name": "citation_author"})],
            "publication_date": meta(soup, "citation_publication_date"), "abstract": abstract,
            "text": text, "outline": outline, "figures": figures, "equations": equations,
            "notices": notices, "paragraph_count": paragraph_count,
            "main_body_detected": True, "main_body_completeness": "requires_source_inspection",
            "scientific_claims_verified": False,
            "warnings": ["HTML text extraction does not verify scientific claims or visually verify figures, tables, or equations."]}


def parse_epmc_xml(raw: str, pmcid: str, expected: tuple[str, str] | None = None):
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        raise AccessError("invalid_xml", "Europe PMC did not return valid article XML.") from None
    body = root.find(".//body")
    title_el = root.find(".//article-title")
    title = " ".join("".join(title_el.itertext()).split()) if title_el is not None else ""
    if body is None or not title:
        raise AccessError("no_body", "Europe PMC returned no article main body.")
    identifiers = {"pmcid": pmcid, "doi": "", "pmid": ""}
    for el in root.findall(".//article-id"):
        kind, value = el.get("pub-id-type"), "".join(el.itertext()).strip()
        if kind in {"doi", "pmid"}:
            identifiers[kind] = value.lower() if kind == "doi" else value
        if kind in {"pmc", "pmcid"} and value.removeprefix("PMC") != pmcid.removeprefix("PMC"):
            raise AccessError("identity_mismatch", "XML article ID differs from the requested PMC article.")
    if expected and expected[0] != "pmcid" and identifiers.get(expected[0]) != expected[1]:
        raise AccessError("identity_mismatch", "XML metadata differs from the requested identifier.")
    parents = {child: parent for parent in body.iter() for child in parent}
    blocks, outline, figures, equations, position = [], [], [], [], 0
    tags = {"title", "p", "fig", "table-wrap", "disp-formula"}
    for el in body.iter():
        if el.tag not in tags:
            continue
        ancestor = parents.get(el)
        nested = False
        while ancestor is not None and ancestor is not body:
            if ancestor.tag in {"p", "fig", "table-wrap", "disp-formula"}:
                nested = True
                break
            ancestor = parents.get(ancestor)
        if nested:
            continue
        text = " ".join("".join(el.itertext()).split())
        if el.tag == "disp-formula":
            equations.append({"id": el.get("id", ""), "original_markup": ET.tostring(el, encoding="unicode"), "images": []})
            if not text:
                text = f"[Equation: inspect original #{el.get('id', '')}]"
        if not text:
            continue
        if el.tag == "title":
            outline.append({"heading": text, "id": parents.get(el, el).get("id", ""), "start_char": position})
        if el.tag == "fig":
            figures.append({"id": el.get("id", ""), "caption": text, "images": []})
        blocks.append(text)
        position += len(text) + 2
    text = "\n\n".join(blocks)
    if len(body.findall(".//p")) < 3 or len(text) < 800 or not outline:
        raise AccessError("no_body", "Too little XML main-body text was detected.")
    authors = [" ".join(" ".join(x.itertext()).split()) for x in root.findall('.//contrib[@contrib-type="author"]/name')]
    abstract_el = root.find(".//abstract")
    return {"title": title, "identifiers": identifiers, "authors": authors, "publication_date": "",
            "abstract": " ".join("".join(abstract_el.itertext()).split()) if abstract_el is not None else "",
            "text": text, "outline": outline, "figures": figures, "equations": equations, "notices": [],
            "paragraph_count": len(body.findall(".//p")), "main_body_detected": True,
            "main_body_completeness": "requires_source_inspection", "scientific_claims_verified": False,
            "warnings": ["JATS XML text extraction does not visually verify figures, tables or equations; inspect original assets when needed."]}


class ArticleAccess:
    def __init__(self, store: Store | None = None, transport=None):
        self.store = store or Store()
        self.transport = transport

    async def request(self, client, url: str, params=None):
        for attempt in range(2):
            async with client.stream("GET", url, params=params) as response:
                if response.status_code in {429, 502, 503, 504} and attempt == 0:
                    try:
                        delay = float(response.headers.get("Retry-After", "1"))
                    except ValueError:
                        delay = 1
                    if 0 <= delay <= 2:
                        await response.aread()
                        await asyncio.sleep(delay)
                        continue
                response.raise_for_status()
                chunks, size = [], 0
                async for chunk in response.aiter_bytes():
                    size += len(chunk)
                    if size > 8_000_000:
                        raise AccessError("response_too_large", "Article response exceeded 8 MB; no truncated copy was accepted.")
                    chunks.append(chunk)
                return b"".join(chunks).decode("utf-8"), str(response.url)
        raise AccessError("service_error", "Request did not return a usable response.")

    async def resolve(self, client, kind, value):
        if kind == "pmcid":
            return value
        query = f'DOI:"{value}" AND SRC:MED' if kind == "doi" else f'EXT_ID:{value} AND SRC:MED'
        raw, _ = await self.request(client, EPMC + "/search", {"query": query, "format": "json", "resultType": "core", "pageSize": 5})
        matches = json.loads(raw).get("resultList", {}).get("result", [])
        matches = [r for r in matches if str(r.get("doi" if kind == "doi" else "id", "")).lower() == value.lower()]
        pmcids = {r["pmcid"] for r in matches if r.get("pmcid")}
        if len(pmcids) != 1:
            raise AccessError("no_unique_pmc_link", "No unique PMC full-text copy was linked to this identifier. Use another article-access route.")
        return pmcids.pop()

    async def article(self, identifier: str, refresh: bool = False):
        kind, value = normalized_identifier(identifier)
        key = "article:" + kind + ":" + value
        cached = None if refresh else self.store.cached(key)
        if cached:
            # An immutable cached source must still be present before reuse is reported.
            p = Path(cached["source_path"])
            if p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest() == cached["source_sha256"]:
                if cached.get("parser_version") != PARSER_VERSION:
                    parser = parse_epmc_xml if cached.get("source_format") == "europepmc_jats_xml" else parse_pmc_html
                    parsed = parser(p.read_text(), cached["identifiers"]["pmcid"], (kind, value))
                    for field in ["source_url", "source_format", "source_path", "source_sha256", "fetched_at", "retrieval_url"]:
                        if field in cached:
                            parsed[field] = cached[field]
                    cached = dict(parsed, parser_version=PARSER_VERSION)
                    self.store.cache(key, cached)
                return dict(cached, cached=True)
        started = time.monotonic()
        async with asyncio.timeout(24):
            async with httpx.AsyncClient(timeout=httpx.Timeout(10, connect=4), follow_redirects=True, transport=self.transport,
                                         headers={"User-Agent": "LiteratureAccess/0.1 public-article-reader"}) as client:
                pmcid = await self.resolve(client, kind, value)
                url = f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/"
                failures, article, raw, source_format, retrieval_url = [], None, "", "", url
                html_health = self.store.health("pmc_html")
                if not html_health["blocked"]:
                    try:
                        raw, actual = await self.request(client, url)
                        parsed = urlparse(actual)
                        if parsed.hostname != "pmc.ncbi.nlm.nih.gov" or not parsed.path.startswith(f"/articles/{pmcid}/"):
                            raise AccessError("unexpected_redirect", "The PMC article redirected away from its canonical page.")
                        article = parse_pmc_html(raw, pmcid, (kind, value))
                        source_format = "public_pmc_html"
                        self.store.mark("pmc_html", "ok", "Public article body retrieved; scientific completeness requires inspection.")
                    except (AccessError, httpx.HTTPError) as e:
                        failures.append({"route": "public_pmc_html", "status": getattr(e, "code", type(e).__name__)})
                        if isinstance(e, AccessError) and e.code == "identity_mismatch":
                            raise
                        if (isinstance(e, AccessError) and e.code == "challenge_page") or (isinstance(e, httpx.HTTPStatusError) and e.response.status_code in {403, 429, 503}):
                            self.store.mark("pmc_html", "unavailable", "Public page challenge or service limit; XML remains a separate route.", cooldown=300)
                else:
                    failures.append({"route": "public_pmc_html", "status": "cooldown"})
                if article is None:
                    retrieval_url = EPMC + f"/{pmcid}/fullTextXML"
                    try:
                        raw, _ = await self.request(client, retrieval_url)
                        article = parse_epmc_xml(raw, pmcid, (kind, value))
                        source_format = "europepmc_jats_xml"
                        self.store.mark("epmc_xml", "ok")
                    except (AccessError, httpx.HTTPError) as e:
                        failures.append({"route": "europepmc_jats_xml", "status": getattr(e, "code", type(e).__name__)})
                        raise AccessError("no_public_body", "No article body recovered from the available routes: " + json.dumps(failures) + ". Reuse an existing original or try browser/institutional access.") from None
        sha = hashlib.sha256(raw.encode()).hexdigest()
        folder = self.store.root / "sources"
        folder.mkdir(exist_ok=True, mode=0o700)
        path = folder / f"{pmcid}-{sha}.{'xml' if source_format == 'europepmc_jats_xml' else 'html'}"
        if not path.exists():
            with path.open("x", encoding="utf-8") as f:
                f.write(raw)
            path.chmod(0o600)
        article.update(source_url=url, source_format=source_format, source_path=str(path),
                       source_sha256=sha, fetched_at=time.time(), cached=False, parser_version=PARSER_VERSION,
                       retrieval_url=retrieval_url, route_failures=failures)
        self.store.cache(key, article)
        for alias_kind, alias_value in article["identifiers"].items():
            if alias_value:
                self.store.cache("article:" + alias_kind + ":" + alias_value, article)
        self.store.audit(source_format, value, "ok", time.monotonic() - started)
        return article

    async def fetch(self, identifier: str, start_char: int = 0, max_characters: int = 20000, refresh: bool = False):
        if start_char < 0 or not 500 <= max_characters <= 60000:
            raise AccessError("invalid_window", "Use start_char >= 0 and max_characters between 500 and 60000.")
        article = await self.article(identifier, refresh)
        full = article.pop("text")
        if start_char > len(full):
            raise AccessError("invalid_window", "start_char exceeds the available article text.")
        end = min(len(full), start_char + max_characters)
        article.update(text=full[start_char:end], total_characters=len(full), start_char=start_char,
                       next_start_char=end if end < len(full) else None, response_truncated=end < len(full),
                       returned_all_extracted_text=start_char == 0 and end == len(full))
        # Formula markup and full figure captions remain in the immutable original.
        article["equations"] = [{"id": e["id"], "images": e.get("images", [])} for e in article["equations"]]
        article["figures"] = [{**f, "caption": f["caption"][:300], "caption_truncated": len(f["caption"]) > 300}
                              for f in article["figures"]]
        return article

    async def passages(self, identifier: str, query: str, limit: int = 5):
        if not query.strip() or not 1 <= limit <= 10:
            raise AccessError("invalid_query", "Provide a nonempty query and a limit between 1 and 10.")
        article = await self.article(identifier)
        terms = set(re.findall(r"\w+", query.casefold()))
        ranked, position = [], 0
        for paragraph in article["text"].split("\n\n"):
            words = set(re.findall(r"\w+", paragraph.casefold()))
            score = len(terms & words)
            if score:
                section = next((x for x in reversed(article["outline"]) if x["start_char"] <= position), {})
                ranked.append((score, position, paragraph, section))
            position += len(paragraph) + 2
        ranked.sort(key=lambda x: (-x[0], x[1]))
        return {"status": "ok", "search_scope": "one_retrieved_PMC_article", "method": "lexical_term_overlap",
                "query": query, "title": article["title"], "identifiers": article["identifiers"],
                "source_path": article["source_path"], "source_sha256": article["source_sha256"],
                "scientific_claims_verified": False,
                "passages": [{"text": text, "start_char": pos, "section": section.get("heading"),
                              "source_url": article["source_url"] + ("#" + section["id"] if section.get("id") else "")}
                             for _, pos, text, section in ranked[:limit]],
                "warnings": ["This searches one article, not Asta's corpus. Matches are reading aids, not verified evidence."]}


def asta_key():
    key = os.environ.get("ASTA_TOOL_KEY") or os.environ.get("ASTA_API_KEY")
    path = ROOT / ".asta-api-key"
    return key.strip() if key else (path.read_text().strip() if path.is_file() else "")


async def process_result(args: list[str], payload: dict, timeout: float):
    """A process boundary makes the deadline independent of remote stream cleanup."""
    proc = await asyncio.create_subprocess_exec(*args, stdin=asyncio.subprocess.PIPE,
                                               stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    try:
        stdout, _stderr = await asyncio.wait_for(proc.communicate(json.dumps(payload).encode()), timeout)
        if proc.returncode:
            raise AccessError("worker_failure", "The bounded MCP worker exited without a successful response.")
        return json.loads(stdout)
    finally:
        if proc.returncode is None:
            proc.kill()
            await proc.wait()


def error_result(code: str, message: str, **details):
    data = {"status": code, "message": message, **details}
    return {"content": [{"type": "text", "text": json.dumps(data)}], "structuredContent": data, "isError": True}


class AstaGuard:
    def __init__(self, store: Store | None = None, runner=process_result, deadline: float | None = None, article_access=None):
        self.store, self.runner = store or Store(), runner
        self.deadline = deadline
        self.article_access = article_access or ArticleAccess(self.store)
        self.locks: dict[str, asyncio.Lock] = {}

    async def recover_scoped_passages(self, arguments: dict, failure: dict):
        """Only a requested, exact paper scope can receive a narrower lexical recovery."""
        paper_ids = [x.strip() for x in str(arguments.get("paper_ids", "")).split(",") if x.strip()]
        if not paper_ids:
            return failure
        passages, recovered, unresolved = [], [], []
        selected = paper_ids[:3]
        try:
            async with asyncio.timeout(8):
                for paper_id in selected:
                    try:
                        result = await self.article_access.passages(paper_id, arguments.get("query", ""),
                                                                    min(10, max(1, arguments.get("limit", 5))))
                        recovered.append({"requested_id": paper_id, "title": result["title"],
                                          "source_path": result["source_path"], "source_sha256": result["source_sha256"]})
                        passages.extend(result["passages"])
                    except (ValueError, httpx.HTTPError):
                        unresolved.append(paper_id)
        except TimeoutError:
            unresolved.extend(x for x in selected if x not in {r["requested_id"] for r in recovered} and x not in unresolved)
        if not passages:
            failure["structuredContent"]["scoped_recovery"] = {"recovered_articles": recovered,
                "unresolved_paper_ids": unresolved, "deferred_paper_ids": paper_ids[3:],
                "status": "no_lexical_matches" if recovered else "unavailable"}
            failure["content"][0]["text"] = json.dumps(failure["structuredContent"])
            return failure
        data = {"status": "partial_recovery", "requested_tool": "asta:snippet_search",
                "upstream_failure": failure["structuredContent"], "actual_method": "lexical_term_overlap",
                "actual_scope": "exact_requested_PMC_articles_only", "query": arguments.get("query", ""),
                "recovered_articles": recovered, "unresolved_paper_ids": unresolved, "deferred_paper_ids": paper_ids[3:],
                "passages": passages[:max(1, arguments.get("limit", 5))], "scientific_claims_verified": False,
                "warnings": ["Asta did not answer. These passages come from the requested public PMC article copies.",
                             "This is a lexical, paper-scoped recovery, not Asta semantic corpus search or exhaustive retrieval."]}
        return {"content": [{"type": "text", "text": json.dumps(data)}], "structuredContent": data, "isError": False}

    async def call(self, name: str, arguments: dict):
        service = "asta:" + name
        fingerprint = hashlib.sha256(json.dumps([name, arguments], sort_keys=True).encode()).hexdigest()
        key = "asta-response:" + fingerprint
        hit = self.store.cached(key)
        if hit:
            hit["_meta"] = hit.get("_meta") or {}
            hit["_meta"]["literature_access"] = {"cached": True, "upstream": ASTA_URL}
            return hit
        async with self.locks.setdefault(service, asyncio.Lock()):
            health = self.store.health(service)
            if health["blocked"]:
                failure = error_result("circuit_open", "This Asta operation recently failed; skipping a repeated wait.",
                                    tool=name, retry_at=health["retry_at"], previous_status=health["status"],
                                    alternatives=["Use OpenAlex/PubMed/Europe PMC for candidate discovery.",
                                                  "Use search_article_passages for a known PMC article; its scope is narrower."])
                return await self.recover_scoped_passages(arguments, failure) if name == "snippet_search" else failure
            started = time.monotonic()
            deadline = self.deadline or (float(os.environ.get("ASTA_PASSAGE_TIMEOUT", "12")) if name == "snippet_search" else 20)
            deadline = max(0.05, min(deadline, 30))
            try:
                result = await self.runner([sys.executable, str(ROOT / "asta_proxy.py"), "--worker"],
                                           {"name": name, "arguments": arguments}, deadline)
            except (TimeoutError, AccessError, json.JSONDecodeError) as e:
                code = "upstream_timeout" if isinstance(e, TimeoutError) else getattr(e, "code", "invalid_upstream_response")
                self.store.mark(service, code, "Bounded remote call failed", cooldown=900 if name == "snippet_search" else 60)
                self.store.audit(service, name, code, time.monotonic() - started)
                failure = error_result(code, "Asta did not return a usable response within the bounded call. No search result was fabricated.",
                                    tool=name, elapsed_seconds=round(time.monotonic() - started, 3),
                                    retry_at=self.store.health(service)["retry_at"],
                                    api_key_configured=bool(asta_key()))
                return await self.recover_scoped_passages(arguments, failure) if name == "snippet_search" else failure
            if result.get("isError"):
                self.store.mark(service, "upstream_error", "Upstream returned an MCP error", cooldown=60)
            else:
                self.store.mark(service, "ok")
                self.store.cache(key, result)
            self.store.audit(service, name, "error" if result.get("isError") else "ok", time.monotonic() - started)
            result["_meta"] = result.get("_meta") or {}
            result["_meta"]["literature_access"] = {"cached": False, "upstream": ASTA_URL}
            if result.get("isError") and name == "snippet_search":
                # Keep the upstream error intact under an explicit normalized envelope.
                failure = error_result("upstream_error", "Asta returned an error.", upstream_result=result)
                return await self.recover_scoped_passages(arguments, failure)
            return result
