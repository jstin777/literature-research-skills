# Optional Zotero review organization

Load only when the recipient explicitly enables `zotero_review_organization` in their private `local-settings.json` or authorizes a Zotero task. Use their configured review root, intake collections, and documented Zotero interface. Check the recipient’s own workspace instructions where present. No particular vault, import script, folder taxonomy, or Obsidian installation is required or bundled here. Never edit Zotero’s database directly.

## Separate review candidates from working-library intake

Create a named collection for an authorized review, optionally with topic subcollections. Verify that its parent is outside every watched intake collection; whole-library processing cannot preserve this separation. Record actual collection keys in the checkpoint. Keep candidates here until the user selects them for their working library. Review inclusion is not selection, human reading, or permission for automated summaries.

Create records from identity-checked bibliography, reusing exact DOI matches and existing attachments. Preserve existing collection memberships, tags, notes and known origins. Do not import the entire unscreened result list, download PDFs merely to populate Zotero, or assume this package supplies a write-capable Zotero connector. If the host only has read access, return an importable bibliography and report the limitation.

## Independent tags and provenance

If the recipient adopts these conventions, newly discovered search candidates can carry `🔎 origin/literature-search` and `status/candidate`. Explicit working-library selection can replace candidate with `📥 status/selected`. Reading and priority labels remain human decisions: `⏳`, `✅`, `reading/unread`, `⭐️`, `👎`, and `📌 reading/next`. No reading tag means unknown. Conversion, retrieval, annotation counts and AI summaries never assign a human reading status.

Use `🌱 origin/personal` or `👤 origin/recommended` only when the discovery context supports them. An uploaded paper does not establish who recommended it. Leave unknown origins unknown; preserve any correction history. Store the discovery URL/search, recommender if known, date when known, and context in a separate discovery note without overwriting human notes or bibliographic Extra. Journal/DOI metadata is not discovery provenance.

For a separately installable reading/annotation workflow, see [Zotero–Obsidian Workflow](https://github.com/jstin777/zotero-obsidian-workflow). Its synchronization is read-only and does not provide review imports. Follow the receiving workflow’s own setup and authorizations; it is optional, not a dependency of literature search.
