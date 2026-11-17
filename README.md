# RegCheck demo

RegCheck is a UiPath agent that reviews Turkish legal documents against live legislation and case law and
produces a compliance report in which every finding cites its source. Low-confidence findings go to
Action Center for human review.

Demo scope: KVKK aydınlatma metni (KVKK md. 10). Legislation comes from **mevzuat-mcp**, KVKK Kurul decisions
from **yargi-mcp**. All test documents are fictional.

```
UploadDocstoSB (RPA) ──▶ ReviewAgent (agent) ──▶ ◇ human_review_required? ──yes──▶ HumanReview (RPA) ──▶ GenerateReport (RPA)
                                                           └──────────no───────────────────────────────▶ GenerateReport (RPA)
```

## Folder structure

```
uipath/
  UploadDocstoSB/          Studio project: reads the document from Outlook, uploads it to the storage bucket, extracts text
  RegCheck_Orchestrator/   Studio project: HumanReview.xaml, GenerateReport.xaml and the coded workflows (+ BUILD_GUIDE.md)
  agent/                   ReviewAgent (Agent Builder): system prompt, output schema, review schema, report template
  maestro/                 Studio Web export of the Maestro process (placeholder)
coded_mcp/                 UiPath Coded MCP package (regcheck-mcp-min) with the vendored mevzuat-mcp / yargi-mcp code
remote/, start_demo.ps1    Serve mevzuat-mcp + yargi-mcp over streamable HTTP behind a Cloudflare quick tunnel
mcp_setup.md               Setup notes for the HTTP/tunnel route
docs/                      Fictional KVKK aydınlatma metni test documents
expected_findings*.md      Expected findings per test document
scripts/                   Test-document builders, text extraction, report renderer, evaluator
orchestrator_tests/        .NET harness that runs the RegCheck_Orchestrator coded workflows without Studio
runs/                      Agent outputs used as test fixtures, with their evaluation results
tools/                     MCP helper scripts and fetched reference material
```

## Opening each part

### UiPath Studio projects (`uipath/UploadDocstoSB`, `uipath/RegCheck_Orchestrator`)
1. Open UiPath Studio (Windows, VB expressions; UploadDocstoSB was built with 24.10, RegCheck_Orchestrator with 25.10).
2. **Open** → select the project's `project.json`.
3. Let Studio restore the packages listed in `project.json`.
4. Connections are tenant-specific. Re-select your own Integration Service connections (Outlook) in the activities
   that use them, and make sure the storage bucket (`SB_Contracts`) and the Orchestrator folder/queue exist in your tenant.
5. Publish to Orchestrator. RegCheck_Orchestrator publishes one package with two entry points
   (`HumanReview.xaml`, `GenerateReport.xaml`); see `uipath/RegCheck_Orchestrator/BUILD_GUIDE.md`.

### ReviewAgent (`uipath/agent`)
Create the agent in **Agent Builder** (Automation Cloud):
- System prompt: paste `system_prompt.txt` (same content as `system_prompt.md`).
- Output schema: `output_schema.json`. The review object inside `review_json` follows `review_schema.json`.
- Tools: the MCP servers registered in Orchestrator (see `coded_mcp/README.md` or `mcp_setup.md`).

`report_template.md` is the Markdown report template used by `scripts/render_report.py`.

### Maestro process (`uipath/maestro`)
Placeholder for the Studio Web export. Import it in Studio Web to recreate the process.

### MCP servers
- Coded MCP in Orchestrator: `coded_mcp/README.md` (pack, publish, reachability test).
- Local HTTP + tunnel: `powershell -ExecutionPolicy Bypass -File .\start_demo.ps1` (details in `mcp_setup.md`).

### Tests
- Coded workflows without Studio (needs the .NET 8 SDK):
  `cd orchestrator_tests` then `dotnet run -c Release -- <repo>`. By default it compiles `uipath/RegCheck_Orchestrator/*.cs`.
- Score a run against the expected findings: `python scripts/evaluate.py runs/<run>`.

## Third-party code
`coded_mcp/regcheck-mcp-min/vendor/` contains code from
[mevzuat-mcp](https://github.com/saidsurucu/mevzuat-mcp) and [yargi-mcp](https://github.com/saidsurucu/yargi-mcp)
under the MIT license. See the `LICENSE` files and `vendor/PROVENANCE.md`.
