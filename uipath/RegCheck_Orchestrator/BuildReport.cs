using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json.Nodes;
using DocumentFormat.OpenXml;
using DocumentFormat.OpenXml.Packaging;
using DocumentFormat.OpenXml.Wordprocessing;
using UiPath.CodedWorkflows;

namespace RegCheck_Orchestrator
{
    /// <summary>
    /// Builds the RegCheck compliance report as DOCX with the OpenXML SDK (no Word).
    /// Layout follows agent/report_template.md in the demo folder: header table, summary,
    /// 1. element checks, 2. findings with citations, 3. penalty exposure, 4. sources consulted.
    /// When a review happened (reviewerDecision not empty) a "Reviewed by lawyer"
    /// section is added after the summary, and every escalated finding shows the decision.
    /// Arguments: in agentJson, in reviewerDecision ("Approve"/"Reject"/"" = no review), in reviewerComment,
    /// in documentName; out reportPath (full path in %TEMP%\RegCheck), out reportFileName.
    /// </summary>
    public class BuildReport : CodedWorkflow
    {
        private const int ContentWidth = 9638;   // A4 (11906) minus 2 x 1134 margins, in DXA

        [Workflow]
        public (string reportPath, string reportFileName) Execute(string agentJson, string reviewerDecision,
                                                                   string reviewerComment, string documentName)
        {
            var r = RegCheckShared.ParseAgentJson(agentJson);
            var decision = RegCheckShared.NormalizeDecision(reviewerDecision);
            var docName = string.IsNullOrWhiteSpace(documentName) ? RegCheckShared.Str(r, "document_id") : documentName.Trim();
            if (docName.Length == 0) docName = "document";

            var baseName = Path.GetFileNameWithoutExtension(docName);
            foreach (var ch in Path.GetInvalidFileNameChars()) baseName = baseName.Replace(ch, '_');
            var fileName = $"{baseName}_RegCheck_Report_{DateTime.Now:yyyyMMdd-HHmmss}.docx";
            var dir = Path.Combine(Path.GetTempPath(), "RegCheck");
            Directory.CreateDirectory(dir);
            var path = Path.Combine(dir, fileName);

            using (var doc = WordprocessingDocument.Create(path, WordprocessingDocumentType.Document))
            {
                var main = doc.AddMainDocumentPart();
                main.Document = new Document(new Body());
                AddStyles(main);
                AddBulletNumbering(main);
                new Writer(main, main.Document.Body!).Write(r, decision, reviewerComment ?? "", docName);
                main.Document.Save();
            }
            return (path, fileName);
        }

        // ------------------------------------------------------------------ content
        private sealed class Writer
        {
            private readonly MainDocumentPart _main;
            private readonly Body _body;
            public Writer(MainDocumentPart main, Body body) { _main = main; _body = body; }

            public void Write(JsonObject r, string decision, string comment, string docName)
            {
                string S(string k) => RegCheckShared.Str(r, k);
                bool reviewed = decision.Length > 0;
                bool humanReviewRequired = RegCheckShared.HumanReviewRequired(r);
                var findings = RegCheckShared.Findings(r).ToList();

                Para("RegCheck Compliance Report: KVKK Privacy Notice", "Title");

                var rows = new List<Cell[]>
                {
                    Row2("Document", docName),
                    Row2("Data controller", S("controller")),
                    Row2("Overall assessment", RegCheckShared.Label(RegCheckShared.OverallLabels, S("overall_assessment"))),
                    Row2("Human review (Action Center)", humanReviewRequired
                        ? (reviewed ? "Yes: " + RegCheckShared.DecisionLabel(decision)
                                    : "Yes, but no lawyer decision was passed to this step")
                        : "No"),
                    Row2("Standard", "Law No. 6698 (KVKK), Art. 10"),
                    Row2("Report date", DateTime.Now.ToString("yyyy-MM-dd HH:mm")),
                };
                Table(new[] { 3200, ContentWidth - 3200 }, rows, header: false);

                Para(new Seg("Summary: ", bold: true), new Seg(S("summary")));

                if (reviewed)
                {
                    Para("Reviewed by lawyer", "Heading1");
                    var flagged = findings.Where(f => RegCheckShared.Bool(f, "escalate"))
                                          .Select(f => $"{RegCheckShared.Str(f, "id")} · {RegCheckShared.Str(f, "title")}").ToList();
                    Table(new[] { 3200, ContentWidth - 3200 }, new List<Cell[]>
                    {
                        Row2("Decision", RegCheckShared.DecisionLabel(decision)),
                        Row2("Lawyer's comment", string.IsNullOrWhiteSpace(comment) ? "—" : comment.Trim()),
                        Row2("Findings reviewed", flagged.Count > 0 ? string.Join("\n", flagged) : "—"),
                    }, header: false);
                    Para(decision == "Reject"
                        ? "The lawyer rejected the findings that required review; these findings are not confirmed."
                        : decision == "Approve"
                            ? "The lawyer approved the findings that required review."
                            : "The lawyer's decision is recorded above.", "Note");
                }

                // 1. element checks
                Para("1. Element check (KVKK Art. 10(1))", "Heading1");
                var elRows = new List<Cell[]> { new[] { H("Provision"), H("Element"), H("Status"), H("Evidence in the document") } };
                foreach (var e in RegCheckShared.Objects(r, "element_checks"))
                {
                    var el = RegCheckShared.NormalizeElement(RegCheckShared.Str(e, "element"));
                    var ev = RegCheckShared.OneLine(RegCheckShared.Str(e, "evidence"));
                    elRows.Add(new[]
                    {
                        C(el), C(RegCheckShared.Label(RegCheckShared.ElementLabels, el)),
                        C(RegCheckShared.Label(RegCheckShared.StatusLabels, RegCheckShared.Str(e, "status"))),
                        C(ev.Length > 0 ? ev : "—"),
                    });
                }
                Table(new[] { 1200, 2400, 1350, ContentWidth - 4950 }, elRows, header: true);

                // 2. findings
                Para("2. Findings", "Heading1");
                if (findings.Count == 0) Para("No findings.");
                foreach (var f in findings)
                {
                    string F(string k) => RegCheckShared.Str(f, k);
                    bool esc = RegCheckShared.Bool(f, "escalate");
                    Para($"{F("id")} · {F("title")}", "Heading2");

                    var conf = new List<Seg> { new Seg(RegCheckShared.Conf(f)) };
                    if (esc) conf.Add(new Seg(" → ⚠️ escalated for human review", bold: true));
                    var fRows = new List<Cell[]>
                    {
                        Row2("Element", $"{RegCheckShared.NormalizeElement(F("element"))} ({F("issue_type")})"),
                        Row2("Severity", RegCheckShared.Label(RegCheckShared.SeverityLabels, F("severity"))),
                        new[] { C(new Seg("Confidence", bold: true)), new Cell(conf.ToArray()) },
                    };
                    if (esc && reviewed) fRows.Add(Row2("Lawyer's decision", RegCheckShared.DecisionLabel(decision)));
                    Table(new[] { 3200, ContentWidth - 3200 }, fRows, header: false);

                    Para(F("description"));
                    if (F("document_excerpt").Trim().Length > 0)
                        Para(new[] { new Seg("From the document: ", bold: true), new Seg(RegCheckShared.OneLine(F("document_excerpt"))) }, "Quote");

                    Para(new Seg("Sources:", bold: true));
                    foreach (var c in RegCheckShared.Objects(f, "citations"))
                    {
                        var p = Para(new[] { new Seg(RegCheckShared.Str(c, "reference"), bold: true), new Seg(" (") }, "ListBullet");
                        AppendLink(p, RegCheckShared.Str(c, "source_url"), "source");
                        AppendRuns(p, new Seg($", {RegCheckShared.Str(c, "retrieved_via")}): “{RegCheckShared.OneLine(RegCheckShared.Str(c, "supporting_quote"))}”"));
                    }
                    Para(new Seg("Recommendation: ", bold: true), new Seg(F("recommendation")));
                    if (esc)
                        Para(new Seg("Question for the lawyer: ", bold: true), new Seg(F("escalation_reason")));
                }

                // 3. penalty
                Para("3. Administrative fine exposure", "Heading1");
                var pe = r["penalty_exposure"];
                if (RegCheckShared.Bool(pe, "applicable"))
                {
                    var p = Para(new Seg(RegCheckShared.Str(pe, "reference"), bold: true),
                                 new Seg($": {RegCheckShared.Str(pe, "range")} ("));
                    AppendLink(p, RegCheckShared.Str(pe, "source_url"), "source");
                    AppendRuns(p, new Seg(")"));
                }
                else
                {
                    Para("No confirmed Art. 10 violation was found, so no fine exposure is assessed.");
                }
                if (RegCheckShared.Str(pe, "note").Trim().Length > 0)
                    Para(new Seg(RegCheckShared.Str(pe, "note"), italic: true));

                // 4. sources consulted
                Para("4. Sources consulted in this run", "Heading1");
                var sRows = new List<Cell[]> { new[] { H("Tool"), H("Input"), H("Used in a finding") } };
                foreach (var s in RegCheckShared.Objects(r, "sources_consulted"))
                {
                    var input = RegCheckShared.Str(s, "input").Trim();
                    if (input == "{}") input = "";
                    sRows.Add(new[]
                    {
                        C(new Seg(RegCheckShared.Str(s, "tool"), mono: true)),
                        C(input.Length > 0 ? input : "—"),
                        C(RegCheckShared.Bool(s, "used_in_findings") ? "✓" : ""),
                    });
                }
                Table(new[] { 4100, ContentWidth - 5400, 1300 }, sRows, header: true);

                var urls = RegCheckShared.SourceUrls(r);
                if (urls.Count > 0)
                {
                    Para(new Seg("Sources cited in the findings:", bold: true));
                    foreach (var u in urls) AppendLink(Para(Array.Empty<Seg>(), "ListBullet"), u, u);
                }

                // footer note with a rule above it
                var foot = Para(new[] { new Seg("This report was generated automatically by the RegCheck demo agent and is not legal advice. " +
                                        "Findings with a confidence below 0.70 are not final without a lawyer's approval.", italic: true) }, "Note");
                foot.ParagraphProperties ??= new ParagraphProperties();
                foot.ParagraphProperties.ParagraphBorders = new ParagraphBorders(
                    new TopBorder { Val = BorderValues.Single, Size = 6, Space = 6, Color = "999999" });

                _body.Append(new SectionProperties(
                    new PageSize { Width = 11906, Height = 16838 },
                    new PageMargin { Top = 1134, Bottom = 1134, Left = 1134, Right = 1134, Header = 708, Footer = 708, Gutter = 0 }));
            }

            // ---- building blocks
            public sealed record Seg(string Text, bool bold = false, bool italic = false, bool mono = false);
            public sealed class Cell { public Seg[] Segs; public bool Header; public Cell(Seg[] s, bool h = false) { Segs = s; Header = h; } }

            private static Cell C(string text) => new Cell(new[] { new Seg(text) });
            private static Cell C(Seg seg) => new Cell(new[] { seg });
            private static Cell H(string text) => new Cell(new[] { new Seg(text, bold: true) }, h: true);
            private static Cell[] Row2(string label, string value) => new[] { C(new Seg(label, bold: true)), C(value ?? "") };

            private Paragraph Para(string text, string? style = null) => Para(new[] { new Seg(text) }, style);
            private Paragraph Para(params Seg[] segs) => Para(segs, null);

            private Paragraph Para(Seg[] segs, string? style)
            {
                var p = new Paragraph();
                if (style != null) p.Append(new ParagraphProperties(new ParagraphStyleId { Val = style }));
                AppendRuns(p, segs);
                _body.Append(p);
                return p;
            }

            private static void AppendRuns(OpenXmlElement parent, params Seg[] segs)
            {
                foreach (var s in segs) parent.Append(MakeRun(s));
            }

            private static Run MakeRun(Seg s, string? charStyle = null)
            {
                var rp = new RunProperties();
                if (charStyle != null) rp.Append(new RunStyle { Val = charStyle });
                if (s.mono) rp.Append(new RunFonts { Ascii = "Consolas", HighAnsi = "Consolas", ComplexScript = "Consolas" });
                if (s.bold) rp.Append(new Bold());
                if (s.italic) rp.Append(new Italic());
                var run = new Run();
                if (rp.HasChildren) run.Append(rp);
                var lines = (s.Text ?? "").Replace("\r\n", "\n").Split('\n');
                for (int i = 0; i < lines.Length; i++)
                {
                    if (i > 0) run.Append(new Break());
                    run.Append(new Text(lines[i]) { Space = SpaceProcessingModeValues.Preserve });
                }
                return run;
            }

            private void AppendLink(Paragraph p, string url, string text)
            {
                if (!Uri.TryCreate(url, UriKind.Absolute, out var uri)) { AppendRuns(p, new Seg(text)); return; }
                var rel = _main.AddHyperlinkRelationship(uri, true);
                p.Append(new Hyperlink(MakeRun(new Seg(text), "Hyperlink")) { Id = rel.Id, History = true });
            }

            private void Table(int[] widths, List<Cell[]> rows, bool header)
            {
                var tbl = new Table();
                tbl.Append(new TableProperties(
                    new TableStyle { Val = "RegCheckTable" },
                    new TableWidth { Width = widths.Sum().ToString(), Type = TableWidthUnitValues.Dxa },
                    new TableLayout { Type = TableLayoutValues.Fixed },
                    new TableLook { Val = header ? "04A0" : "0480" }));
                var grid = new TableGrid();
                foreach (var w in widths) grid.Append(new GridColumn { Width = w.ToString() });
                tbl.Append(grid);

                foreach (var row in rows)
                {
                    var tr = new TableRow();
                    bool isHeader = row.Any(c => c.Header);
                    if (isHeader) tr.Append(new TableRowProperties(new TableHeader()));
                    for (int i = 0; i < row.Length; i++)
                    {
                        var tcp = new TableCellProperties(new TableCellWidth { Width = widths[i].ToString(), Type = TableWidthUnitValues.Dxa });
                        if (row[i].Header || (!header && i == 0))
                            tcp.Append(new Shading { Val = ShadingPatternValues.Clear, Color = "auto", Fill = row[i].Header ? "D9E2F3" : "F2F2F2" });
                        var para = new Paragraph(new ParagraphProperties(new ParagraphStyleId { Val = "TableText" }));
                        AppendRuns(para, row[i].Segs);
                        tr.Append(new TableCell(tcp, para));
                    }
                    tbl.Append(tr);
                }
                _body.Append(tbl);
                _body.Append(new Paragraph(new ParagraphProperties(new ParagraphStyleId { Val = "Spacer" })));
            }
        }

        // ------------------------------------------------------------------ styles & numbering
        private static void AddStyles(MainDocumentPart main)
        {
            var part = main.AddNewPart<StyleDefinitionsPart>();
            const string font = "Calibri";

            Style PStyle(string id, string name, OpenXmlElement[] rPr, OpenXmlElement[] pPr, int? outline = null)
            {
                var st = new Style { Type = StyleValues.Paragraph, StyleId = id };
                st.Append(new StyleName { Val = name }, new BasedOn { Val = "Normal" }, new NextParagraphStyle { Val = "Normal" },
                          new PrimaryStyle());
                var spp = new StyleParagraphProperties(pPr);
                if (outline.HasValue) spp.Append(new OutlineLevel { Val = outline.Value });
                st.Append(spp, new StyleRunProperties(rPr));
                return st;
            }
            OpenXmlElement[] E(params OpenXmlElement[] e) => e;

            var styles = new Styles(
                new DocDefaults(
                    new RunPropertiesDefault(new RunPropertiesBaseStyle(
                        new RunFonts { Ascii = font, HighAnsi = font, ComplexScript = font, EastAsia = font },
                        new FontSize { Val = "21" }, new FontSizeComplexScript { Val = "21" },
                        new Languages { Val = "en-US" })),
                    new ParagraphPropertiesDefault(new ParagraphPropertiesBaseStyle(
                        new SpacingBetweenLines { After = "120", Line = "264", LineRule = LineSpacingRuleValues.Auto }))),
                new Style(new StyleName { Val = "Normal" }, new PrimaryStyle()) { Type = StyleValues.Paragraph, StyleId = "Normal", Default = true },
                PStyle("Title", "Title",
                    E(new Bold(), new Color { Val = "1F3864" }, new FontSize { Val = "36" }),
                    E(new KeepNext(), new SpacingBetweenLines { Before = "0", After = "240" })),
                PStyle("Heading1", "heading 1",
                    E(new Bold(), new Color { Val = "2F5496" }, new FontSize { Val = "28" }),
                    E(new KeepNext(), new SpacingBetweenLines { Before = "320", After = "120" }), 0),
                PStyle("Heading2", "heading 2",
                    E(new Bold(), new Color { Val = "2F5496" }, new FontSize { Val = "24" }),
                    E(new KeepNext(), new SpacingBetweenLines { Before = "240", After = "100" }), 1),
                PStyle("Quote", "Quote",
                    E(new Italic(), new Color { Val = "404040" }),
                    E(new ParagraphBorders(new LeftBorder { Val = BorderValues.Single, Size = 12, Space = 8, Color = "A5A5A5" }),
                      new Indentation { Left = "360" })),
                PStyle("Note", "RegCheck Note",
                    E(new Color { Val = "595959" }, new FontSize { Val = "18" }),
                    E(new SpacingBetweenLines { Before = "120", After = "120" })),
                PStyle("TableText", "RegCheck Table Text",
                    E(new FontSize { Val = "19" }),
                    E(new SpacingBetweenLines { Before = "0", After = "0", Line = "240", LineRule = LineSpacingRuleValues.Auto })),
                PStyle("Spacer", "RegCheck Spacer",
                    E(new FontSize { Val = "8" }),
                    E(new SpacingBetweenLines { Before = "0", After = "0", Line = "120", LineRule = LineSpacingRuleValues.Exact })),
                PStyle("ListBullet", "List Bullet",
                    E(),
                    E(new NumberingProperties(new NumberingLevelReference { Val = 0 }, new NumberingId { Val = 1 }),
                        new SpacingBetweenLines { After = "60" }, new Indentation { Left = "360", Hanging = "360" })),
                new Style(new StyleName { Val = "Hyperlink" },
                          new StyleRunProperties(new Color { Val = "0563C1" }, new Underline { Val = UnderlineValues.Single }))
                { Type = StyleValues.Character, StyleId = "Hyperlink" },
                new Style(new StyleName { Val = "RegCheck Table" },
                          new StyleTableProperties(
                              new TableBorders(
                                  new TopBorder { Val = BorderValues.Single, Size = 4, Color = "BFBFBF" },
                                  new LeftBorder { Val = BorderValues.Single, Size = 4, Color = "BFBFBF" },
                                  new BottomBorder { Val = BorderValues.Single, Size = 4, Color = "BFBFBF" },
                                  new RightBorder { Val = BorderValues.Single, Size = 4, Color = "BFBFBF" },
                                  new InsideHorizontalBorder { Val = BorderValues.Single, Size = 4, Color = "BFBFBF" },
                                  new InsideVerticalBorder { Val = BorderValues.Single, Size = 4, Color = "BFBFBF" }),
                              new TableCellMarginDefault(
                                  new TopMargin { Width = "60", Type = TableWidthUnitValues.Dxa },
                                  new TableCellLeftMargin { Width = 100, Type = TableWidthValues.Dxa },
                                  new BottomMargin { Width = "60", Type = TableWidthUnitValues.Dxa },
                                  new TableCellRightMargin { Width = 100, Type = TableWidthValues.Dxa })))
                { Type = StyleValues.Table, StyleId = "RegCheckTable" });
            part.Styles = styles;
            part.Styles.Save();
        }

        private static void AddBulletNumbering(MainDocumentPart main)
        {
            var part = main.AddNewPart<NumberingDefinitionsPart>();
            part.Numbering = new Numbering(
                new AbstractNum(
                    new MultiLevelType { Val = MultiLevelValues.SingleLevel },
                    new Level(
                        new NumberingFormat { Val = NumberFormatValues.Bullet },
                        new LevelText { Val = "•" },
                        new LevelJustification { Val = LevelJustificationValues.Left },
                        new PreviousParagraphProperties(new Indentation { Left = "360", Hanging = "360" }))
                    { LevelIndex = 0 })
                { AbstractNumberId = 1 },
                new NumberingInstance(new AbstractNumId { Val = 1 }) { NumberID = 1 });
            part.Numbering.Save();
        }
    }
}
