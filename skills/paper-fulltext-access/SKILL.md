---
name: paper-fulltext-access
description: Retrieve a known scholarly article or PDF. Invoke automatically when an agent encounters a paper paywall, institutional-login or purchase prompt, subscription preview, abstract-only access, or failed full-text retrieval during any research, literature-search, review, or citation-verification task that needs the full paper. Also use for explicit paper retrieval by DOI, PMID, title, or URL. Recover institutional access through direct LibKey.io in a supported interactive browser without an extension or plugin.
---

# Paper full-text access

This is a standalone skill. It does not depend on a plugin, extension, named connector or preconfigured institution. Institutional retrieval still requires the user’s own entitlement and sign-in. It can be used alone for a known paper or called by [literature-search-review](../literature-search-review/SKILL.md) for a subject search; if installed separately, resolve that optional caller by skill name. Use the current host's documented tools rather than assuming tool names from another chat.

## Access readiness and host capabilities

For a research session where subscription access may be useful, request institutional readiness before retrieval starts. Reuse a verified session. Ask which institution to use only when unknown, and ask the user to complete institutional sign-in/MFA in the actual browser when prompted; do not request a separate LibKey account. Public discovery can continue while the user responds. Some publishers present login only for a specific article, so record readiness as pending rather than inventing a test paper or claiming the user is authenticated. If the user has no institution or declines sign-in, continue public retrieval with the limitation recorded.

Use an agent-controlled browser that the user can view and sign into, where the host supports one. Respect the user's selected browser; otherwise prefer the host's integrated browser when available. Do not assume authentication is shared with a different browser, shell request or another agent. Keep one owner of browser interaction and reuse that session across papers. If no such browser is available, provide the direct LibKey link for the user to open and request a readable permitted copy if necessary; call this assisted retrieval, not autonomous institutional recovery. An instruction-following model without browser tools cannot perform login or retrieve a subscription paper by itself.

## Trigger and handoff

When a task needs the full paper and a publisher or retrieval tool returns a paywall, subscription preview, institutional login, purchase offer, or only an abstract, invoke this skill before declaring full text unavailable or substituting an abstract for the paper. The user need not name LibKey or explicitly request this skill. A CAPTCHA or network error is a technical blocker, not proof of a paywall.

This is a retrieval subtask within the calling agent's work. Accept its identifiers, required format/version, and prior failed routes; do not repeat discovery or restart failed checks. Return the verified source and resume the original task. Metadata-only or abstract-screening tasks do not require full-text recovery.

## Choose the shortest route

Reuse a suitable existing file unless the user requests a fresh access test. Resolve a missing DOI from the exact title/citation using a scholarly record; verify identity.

For ordinary retrieval without an established paywall, prefer an available exact full-text tool or obvious legal OA copy. Make at most two promising attempts; do not exhaustively search repositories. A paywall already encountered by the caller is sufficient reason to proceed directly to LibKey if no suitable copy is already available. An explicit institutional-access test starts at LibKey.

Use content mode when readable HTML/JATS/full text satisfies the task; use PDF mode when a saved PDF is requested or required downstream. Prefer the version of record; label manuscript/preprint substitutions.

## Direct LibKey institutional route

1. Open `https://libkey.io/<DOI>` in the selected supported interactive browser. An identified PMID can also be used. Do not require, install, or invoke Nomad, another extension or a plugin. Do not silently switch browser/profile or assume a session is authenticated elsewhere.
2. If asked, select the user's known institution. Do not hard-code an institution or library ID. Ask only if it cannot be inferred from the user's request or existing selection.
3. Choose the visible **Download PDF** or **Article Link** option appropriate to the output. Follow the actual resolver redirects, including new tabs; a resolver button alone is not successful retrieval.
4. If institutional sign-in is required, show that tab and ask the user to complete login/MFA there. Preserve the tab for continuation. Never request credentials in chat, inspect password values, or export authentication cookies. Resume the same browser session after the user confirms.
5. Verify that the destination exposes the article body or a complete PDF. Institutional access may appear on a library proxy hostname or a normal publisher hostname. Neither hostname alone proves access.
6. For PDF mode, use the publisher's actual file-download control. A LibKey link may open a reader rather than save a file. If the reader's download controls are inaccessible, use LibKey's Article Link and that publisher page's Download PDF link.
7. Verify the saved file before declaring success. If a download event times out, inspect the known output location for a newly created matching file before retrying. Distinguish it from old downloads using timestamps and identity; never count an old file as a fresh test result.

Read [publisher and download notes](references/access-routing.md) when a reader or download action is troublesome. Use the current host's documented browser/download APIs rather than assuming a particular tool is installed.

## Verification and stopping

Verify title, DOI and author/year as needed. For a saved PDF, confirm it is a parsable PDF rather than HTML, check expected page count where available, and inspect text across pages or render pages if extraction is empty. Record version and consequential incompleteness. A PDF viewer opening does not prove a local download; an abstract does not prove full-text recovery.

Stop once a verified source meets the requested format. If a route fails, inspect the current state and try the other visible LibKey format or library access-options link where useful. Do not loop identical failures. Report whether the blocker is login, entitlement, resolver coverage, CAPTCHA, network, or download tooling. Offer library document delivery when appropriate; do not buy access or submit a loan request without authorization.

LibKey routes existing entitlements; it does not grant subscriptions or guarantee all institutional holdings. Do not infer universal coverage from a successful sample. Keep network/VPN, browser authentication, readable full text, and saved PDFs distinct in tests.

## Return to caller

Return the article identity, stable verified full-text link or readable source/file location, version, source coverage and access status. Use absolute file paths when the host uses a filesystem; otherwise identify the actual shared artifact. Do not expose signed access tokens. If requested PDF mode was not satisfied, report that separately from readable full text. If unresolved, name the concrete blocker and preserve a useful sign-in/access tab. Resume the user's original research task without requiring a separate request.
