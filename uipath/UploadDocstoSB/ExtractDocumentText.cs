using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using DocumentFormat.OpenXml.Packaging;
using UglyToad.PdfPig;
using UglyToad.PdfPig.DocumentLayoutAnalysis.TextExtractor;
using UiPath.CodedWorkflows;
using W = DocumentFormat.OpenXml.Wordprocessing;

namespace UploadDocstoSB
{
    /// <summary>
    /// Extracts plain text from an aydınlatma metni so it can be passed to ReviewAgent as document_text.
    /// DOCX: OpenXML SDK (no Word). Paragraphs and tables in document order; list items get "- ",
    /// table rows become "| a | b |". This matches scripts/docx_to_text.py in the demo folder, which
    /// produced the text the agent was tested with.
    /// PDF: PdfPig (pure .NET). Needs a text layer; scanned PDFs (no OCR) give a clear error.
    /// Arguments: in filePath; out text, out charCount.
    /// </summary>
    public class ExtractDocumentText : CodedWorkflow
    {
        [Workflow]
        public (string text, int charCount) Execute(string filePath)
        {
            if (string.IsNullOrWhiteSpace(filePath))
                throw new ArgumentException("ExtractDocumentText: filePath is empty.");
            if (!File.Exists(filePath))
                throw new FileNotFoundException("ExtractDocumentText: file not found: " + filePath, filePath);

            string ext = Path.GetExtension(filePath).ToLowerInvariant();
            string text = ext switch
            {
                ".docx" => FromDocx(filePath),
                ".pdf" => FromPdf(filePath),
                ".doc" => throw new NotSupportedException(
                    "ExtractDocumentText: legacy .doc is not supported. Save the document as .docx (or PDF) and send it again."),
                _ => throw new NotSupportedException(
                    $"ExtractDocumentText: unsupported file type '{ext}'. Supported: .docx, .pdf."),
            };

            if (string.IsNullOrWhiteSpace(text))
                throw new InvalidDataException("ExtractDocumentText: no text found in " + Path.GetFileName(filePath) +
                    (ext == ".pdf" ? " (the PDF has no text layer, e.g. a scan; OCR is not part of this demo)." : "."));
            return (text, text.Length);
        }

        private static string FromDocx(string path)
        {
            using var doc = WordprocessingDocument.Open(path, false);
            var main = doc.MainDocumentPart ?? throw new InvalidDataException("DOCX has no main document part.");
            var body = main.Document?.Body ?? throw new InvalidDataException("DOCX has no body.");

            var styleNames = new Dictionary<string, string>();
            foreach (var s in main.StyleDefinitionsPart?.Styles?.Elements<W.Style>() ?? Enumerable.Empty<W.Style>())
                if (s.StyleId?.Value is string id) styleNames[id] = s.StyleName?.Val?.Value ?? id;

            var lines = new List<string>();
            AppendBlocks(body.ChildElements, lines, styleNames);
            return string.Join("\n", lines) + "\n";
        }

        private static void AppendBlocks(IEnumerable<DocumentFormat.OpenXml.OpenXmlElement> blocks, List<string> lines,
                                         Dictionary<string, string> styleNames)
        {
            foreach (var el in blocks)
            {
                switch (el)
                {
                    case W.Paragraph p:
                        var t = ParagraphText(p).Trim();
                        if (t.Length == 0) break;
                        var styleId = p.ParagraphProperties?.ParagraphStyleId?.Val?.Value;
                        bool isList = (styleId != null && styleNames.TryGetValue(styleId, out var name) &&
                                       name.StartsWith("List", StringComparison.Ordinal)) ||
                                      p.ParagraphProperties?.NumberingProperties != null;
                        lines.Add(isList ? "- " + t : t);
                        break;
                    case W.Table tbl:
                        foreach (var row in tbl.Elements<W.TableRow>())
                        {
                            var cells = row.Elements<W.TableCell>()
                                .Select(c => string.Join("\n", c.Elements<W.Paragraph>().Select(ParagraphText)).Trim());
                            lines.Add("| " + string.Join(" | ", cells) + " |");
                        }
                        break;
                    case W.SdtBlock sdt when sdt.SdtContentBlock != null:
                        AppendBlocks(sdt.SdtContentBlock.ChildElements, lines, styleNames);   // content controls
                        break;
                }
            }
        }

        private static string ParagraphText(W.Paragraph p)
        {
            var sb = new StringBuilder();
            foreach (var run in p.Descendants<W.Run>())
            {
                if (run.Ancestors<W.TextBoxContent>().Any()) continue;   // text boxes are not body text
                foreach (var c in run.ChildElements)
                {
                    switch (c)
                    {
                        case W.Text tx: sb.Append(tx.Text); break;
                        case W.TabChar: sb.Append('\t'); break;
                        case W.Break br when br.Type == null || br.Type.Value == W.BreakValues.TextWrapping: sb.Append('\n'); break;
                        case W.CarriageReturn: sb.Append('\n'); break;
                        case W.NoBreakHyphen: sb.Append('-'); break;
                    }
                }
            }
            return sb.ToString();
        }

        private static string FromPdf(string path)
        {
            using var pdf = PdfDocument.Open(path);
            var pages = pdf.GetPages().Select(pg => ContentOrderTextExtractor.GetText(pg).Trim()).Where(s => s.Length > 0);
            var text = string.Join("\n\n", pages);
            return text.Length == 0 ? "" : text.Replace("\r\n", "\n") + "\n";
        }
    }
}
