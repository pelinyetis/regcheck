using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json.Nodes;
using DocumentFormat.OpenXml.Packaging;
using DocumentFormat.OpenXml.Validation;
using RegCheck_Orchestrator;

// Usage (from orchestrator_tests): dotnet run -c Release -- "<demo folder>"
var demo = args.Length > 0 ? args[0] : Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", ".."));
var outDir = Path.Combine(demo, "orchestrator_tests", "out");
Directory.CreateDirectory(outDir);
Console.OutputEncoding = System.Text.Encoding.UTF8;
int fails = 0;
void Check(bool ok, string what) { Console.WriteLine((ok ? "PASS " : "FAIL ") + what); if (!ok) fails++; }
string Rd(string p) => File.ReadAllText(p);

var docs = new[] { ("A_uyumlu", "A_uyumlu_aydinlatma_metni"), ("B_eksik", "B_eksik_aydinlatma_metni"), ("C_sinirda", "C_sinirda_aydinlatma_metni") };
var sender = "ornek.gonderen@example.com";   // fictional

Console.WriteLine("== 1. ExtractDocumentText");
var extract = new ExtractDocumentText();
foreach (var (_, file) in docs)
{
    var (text, n) = extract.Execute(Path.Combine(demo, "docs", file + ".docx"));
    File.WriteAllText(Path.Combine(outDir, file + ".extracted.txt"), text);
    // docs/*.txt were saved with CRLF by Python on Windows; the agent itself received LF text from docx_text()
    var expected = Rd(Path.Combine(demo, "docs", file + ".txt")).Replace("\r\n", "\n");
    Check(text == expected, $"{file}.docx: {n} chars, identical to scripts/docx_to_text.py output (the agent's tested input)");
}
{
    var (pdfText, n) = extract.Execute(Path.Combine(demo, "docs", "B_eksik_aydinlatma_metni.pdf"));
    File.WriteAllText(Path.Combine(outDir, "B_eksik_aydinlatma_metni.pdf.extracted.txt"), pdfText);
    static HashSet<string> Words(string s) => s.Split(new[] { ' ', '\n', '\t', '|', '\r' }, StringSplitOptions.RemoveEmptyEntries).ToHashSet();
    var w = Words(Rd(Path.Combine(demo, "docs", "B_eksik_aydinlatma_metni.txt")));
    var got = Words(pdfText);
    double recall = w.Count(got.Contains) / (double)w.Count;
    Check(recall > 0.95, $"B_eksik .pdf: {n} chars, word recall vs .docx text {recall:P1}");
}
foreach (var (path, expect) in new[] { ("x.doc", "legacy .doc"), ("x.txt", "unsupported file type"), ("missing.docx", "file not found") })
{
    var p = Path.Combine(outDir, path);
    if (!path.StartsWith("missing")) File.WriteAllText(p, "dummy");
    try { extract.Execute(p); Check(false, $"{path}: expected an error"); }
    catch (Exception e) { Check(e.Message.Contains(expect), $"{path}: clear error -> {e.Message}"); }
}

Console.WriteLine("\n== 1b. ExtractDocumentText on the new PDF test set (D, E, F)");
{
    var defDocs = new (string file, string[] mustContain, string[] mustNotContain)[]
    {
        ("D_klinik_uyumlu_aydinlatma_metni", new[] { "Ilgaz Tıp Merkezi Sağlık Hizmetleri A.Ş.", "Kanun md. 6/3-e", "Sağlık verileri (özel nitelikli kişisel veri)",
            "Kişisel verileriniz yurt dışına aktarılmamaktadır.", "ğ) Kişisel verilerinizin kanuna aykırı olarak işlenmesi", "kvkk@ilgaztip.example" }, new string[0]),
        ("E_spor_eksik_aydinlatma_metni", new[] { "Çınaraltı Spor ve Sağlıklı Yaşam Hizmetleri Ltd. Şti.", "Kanun md. 5/2-c", "kart okuyucular",
            "ç) Yurt içinde veya yurt dışında kişisel verilerinizin aktarıldığı üçüncü kişileri bilme," }, new[] { "amacıyla", "Alıcı grubu", "aktarılabilecektir" }),
        ("F_fintech_sinirda_aydinlatma_metni", new[] { "Defne Ödeme ve Elektronik Para Hizmetleri A.Ş.", "5549 sayılı Suç Gelirlerinin Aklanmasının Önlenmesi Hakkında Kanun",
            "hukuki sebeplerinden bir veya birkaçına dayanılarak", "Mali Suçları Araştırma Kurulu (MASAK)", "Kişisel verileriniz yurt dışına aktarılmamaktadır." }, new string[0]),
    };
    static string Flat(string t) => System.Text.RegularExpressions.Regex.Replace(t, @"\s+", " ");
    static HashSet<string> W(string t) => t.Split(new[] { ' ', '\n', '\r', '\t' }, StringSplitOptions.RemoveEmptyEntries).ToHashSet();
    foreach (var (file, must, mustNot) in defDocs)
    {
        var pdf = Path.Combine(demo, "docs", file + ".pdf");
        var (text, n) = extract.Execute(pdf);
        File.WriteAllText(Path.Combine(demo, "docs", file + ".txt"), text);
        var flat = Flat(text);
        var missing = must.Where(m => !flat.Contains(m)).ToList();
        Check(missing.Count == 0, $"{file}.pdf: {n} chars; key phrases intact (Turkish characters, punctuation)" + (missing.Count > 0 ? " MISSING: " + string.Join(" | ", missing) : ""));
        var present = mustNot.Where(m => flat.Contains(m)).ToList();
        if (mustNot.Length > 0) Check(present.Count == 0, $"{file}.pdf: deliberately absent wording really absent" + (present.Count > 0 ? " FOUND: " + string.Join(" | ", present) : ""));
        Check(!text.Contains('\uFFFD') && !System.Text.RegularExpressions.Regex.IsMatch(text, @"[a-zçğıöşü][A-ZÇĞİÖŞÜ]{2,}[a-zçğıöşü]"), $"{file}.pdf: no replacement characters or glued words");
        var reference = W(File.ReadAllText(Path.Combine(outDir, file + ".pdf.pymupdf.txt")));
        var got = W(text);
        double recall = reference.Count(got.Contains) / (double)reference.Count;
        Check(recall > 0.98, $"{file}.pdf: word recall vs. independent extractor (PyMuPDF) {recall:P1}");
    }
}

Console.WriteLine("\n== 2. FormatReviewText (agent outputs from runs/run5_needs_review)");
var fmt = new FormatReviewText();
var expectReview = new Dictionary<string, bool> { ["A_uyumlu"] = false, ["B_eksik"] = false, ["C_sinirda"] = true };
foreach (var (id, file) in docs)
{
    var json = Rd(Path.Combine(demo, "runs", "run5_needs_review", id + ".result.json"));
    var (reviewText, humanReviewRequired) = fmt.Execute(json, file + ".docx", sender);
    File.WriteAllText(Path.Combine(outDir, id + ".reviewText.txt"), reviewText);
    Check(humanReviewRequired == expectReview[id], $"{id}: humanReviewRequired={humanReviewRequired}");
    var urls = RegCheckShared.SourceUrls(RegCheckShared.ParseAgentJson(json));
    Check(urls.All(reviewText.Contains), $"{id}: Sources section lists all {urls.Count} cited URLs");
}
// robustness: missing flag, wrapped / double-encoded / fenced JSON, bad input
{
    var noFlag = JsonNode.Parse(Rd(Path.Combine(demo, "runs", "run5_needs_review", "C_sinirda.result.json")))!.AsObject();
    noFlag.Remove("human_review_required");
    Check(fmt.Execute(noFlag.ToJsonString(), "", "").humanReviewRequired, "C without human_review_required: still true from the escalated finding");
    var c5 = Rd(Path.Combine(demo, "runs", "run5_needs_review", "C_sinirda.result.json"));
    var baseline = fmt.Execute(c5, "C.docx", sender).reviewText;
    var wrapped = new JsonObject { ["output"] = JsonNode.Parse(c5) }.ToJsonString();
    var dbl = JsonValue.Create(c5)!.ToJsonString();
    var fenced = "```json\n" + c5 + "\n```";
    Check(fmt.Execute(wrapped, "C.docx", sender).reviewText == baseline, "wrapped {\"output\": {...}} parses the same");
    Check(fmt.Execute(dbl, "C.docx", sender).reviewText == baseline, "double-encoded JSON string parses the same");
    Check(fmt.Execute(fenced, "C.docx", sender).reviewText == baseline, "```json fenced block parses the same");
    foreach (var bad in new[] { "", "{not json", "{\"foo\": 1}" })
    {
        try { fmt.Execute(bad, "", ""); Check(false, $"[{bad}]: expected an error"); }
        catch (ArgumentException e) { Check(true, $"[{bad}]: clear error -> {e.Message}"); }
    }
}

Console.WriteLine("\n== 2b. Real UiPath agent output (document A, 2026-11-05)");
{
    var real = Rd(Path.Combine(demo, "runs", "uipath_real", "A_agent_output.json"));        // what Maestro passes
    var span = Rd(Path.Combine(demo, "runs", "uipath_real", "A_agent_output_span.json"));   // trace span as shown in UiPath
    var (rt, hr) = fmt.Execute(real, "A_uyumlu_aydinlatma_metni.docx", sender);
    File.WriteAllText(Path.Combine(outDir, "A_uipath_real.reviewText.txt"), rt);
    Check(!hr, "real A: humanReviewRequired=false (human_review_required=false, no findings)");
    Check(rt.Contains("Overall result: ✅ Compliant") && rt.Contains("Findings: none."), "real A: overall_assessment and empty findings rendered");
    Check(fmt.Execute(span, "A_uyumlu_aydinlatma_metni.docx", sender).reviewText == rt, "real A: trace span ({Attributes:{output:{...}}}) parses the same as the bare object");
    var (rp, _) = new BuildReport().Execute(real, "", "", "A_uyumlu_aydinlatma_metni.docx");
    var dest = Path.Combine(outDir, "A_uipath_real.report.docx");
    File.Copy(rp, dest, true);
    using var d = WordprocessingDocument.Open(dest, false);
    var text = d.MainDocumentPart!.Document!.Body!.InnerText;
    Check(new OpenXmlValidator().Validate(d).Count() == 0, "real A: report is schema-valid");
    Check(RegCheckShared.ElementLabels.Values.All(text.Contains), "real A: '6698 md. 10/1-x' elements resolved to their labels in the report");
    Check(RegCheckShared.NormalizeElement("6698 md. 10/1-ç") == "10/1-ç" && RegCheckShared.NormalizeElement("10/1-d") == "10/1-d"
          && RegCheckShared.NormalizeElement("Tebliğ md. 5/1-g") == "T5/1-g" && RegCheckShared.NormalizeElement("other") == "other",
          "NormalizeElement handles '6698 md. 10/1-ç', '10/1-d', 'Tebliğ md. 5/1-g', 'other'");
}

Console.WriteLine("\n== 2c. {\"result\": {...}} wrapper (runs/run7_result_wrapper, schema since 2026-11-05)");
foreach (var (id, file) in docs)
{
    var wrapped = Rd(Path.Combine(demo, "runs", "run7_result_wrapper", id + ".result.json"));      // whole agent response
    var inner = JsonNode.Parse(wrapped)!["result"]!.ToJsonString();                                  // Maestro field "result"
    var (rtW, hrW) = fmt.Execute(wrapped, file + ".docx", sender);
    var (rtI, hrI) = fmt.Execute(inner, file + ".docx", sender);
    Check(rtW == rtI && hrW == hrI && hrW == expectReview[id], $"{id}: FormatReviewText same for wrapper and bare result (humanReviewRequired={hrW})");
    var (pW, _) = new BuildReport().Execute(wrapped, id == "C_sinirda" ? "Approve" : "", "", file + ".docx");
    using var dW = WordprocessingDocument.Open(pW, false);
    var tW = dW.MainDocumentPart!.Document!.Body!.InnerText;
    Check(new OpenXmlValidator().Validate(dW).Count() == 0 && tW.Contains(RegCheckShared.Str(JsonNode.Parse(inner), "summary").Substring(0, 40)),
          $"{id}: BuildReport from wrapper is schema-valid and contains the agent summary");
}

Console.WriteLine("\n== 2d. English output (runs/run8_english)");
foreach (var (id, file) in docs)
{
    var json = Rd(Path.Combine(demo, "runs", "run8_english", id + ".result.json"));
    var (rt, hr) = fmt.Execute(json, file + ".docx", sender);
    File.WriteAllText(Path.Combine(outDir, id + ".english.reviewText.txt"), rt);
    Check(hr == expectReview[id] && rt.StartsWith("RegCheck · Privacy notice review") && rt.Contains("Overall result: ")
          && !System.Text.RegularExpressions.Regex.IsMatch(rt, "Belge:|Gönderen:|Genel sonuç:|Bulgular|Kaynaklar"),
          $"{id}: English review text, humanReviewRequired={hr}");
    bool c = id == "C_sinirda";
    var (rp, rf) = new BuildReport().Execute(json, c ? "Approve" : "", c ? "Recipient groups are listed; acceptable for this demo. Add a recipient-to-purpose mapping in the next version." : "", file + ".docx");
    var dest = Path.Combine(outDir, id + (c ? "_Approve" : "") + ".english.report.docx");
    File.Copy(rp, dest, true);
    using var d = WordprocessingDocument.Open(dest, false);
    var t = d.MainDocumentPart!.Document!.Body!.InnerText;
    Check(new OpenXmlValidator().Validate(d).Count() == 0 && rf.Contains("_RegCheck_Report_")
          && t.Contains("RegCheck Compliance Report") && t.Contains("1. Element check") && t.Contains("4. Sources consulted in this run")
          && !System.Text.RegularExpressions.Regex.IsMatch(t, "Uyum Raporu|Unsur kontrolü|Bulgular|Özet:|Hukukçu yorumu|Kaynaklar"),
          $"{id}: English report, schema-valid ({rf})");
}

Console.WriteLine("\n== 2e. {\"review\": {...}} wrapper (runs/run9_review_wrapper; \"result\" is reserved in Maestro)");
foreach (var (id, file) in docs)
{
    var wrapped = Rd(Path.Combine(demo, "runs", "run9_review_wrapper", id + ".result.json"));     // whole agent response
    var root = JsonNode.Parse(wrapped)!.AsObject();
    Check(root.Count == 1 && root["review"] is JsonObject, $"{id}: agent output has exactly one top-level field 'review'");
    var inner = root["review"]!.ToJsonString();                                                      // Maestro field "review"
    var (rtW, hrW) = fmt.Execute(wrapped, file + ".docx", sender);
    var (rtI, hrI) = fmt.Execute(inner, file + ".docx", sender);
    Check(rtW == rtI && hrW == hrI && hrW == expectReview[id], $"{id}: FormatReviewText same for {{review:...}} and bare review (humanReviewRequired={hrW})");
    var (pW, _) = new BuildReport().Execute(wrapped, id == "C_sinirda" ? "Approve" : "", "", file + ".docx");
    var (pI, _) = new BuildReport().Execute(inner, id == "C_sinirda" ? "Approve" : "", "", file + ".docx");
    string Body(string path) { using var d = WordprocessingDocument.Open(path, false); return System.Text.RegularExpressions.Regex.Replace(d.MainDocumentPart!.Document!.Body!.InnerText, @"\d{4}-\d{2}-\d{2} \d{2}:\d{2}", ""); }
    using (var dW = WordprocessingDocument.Open(pW, false))
        Check(new OpenXmlValidator().Validate(dW).Count() == 0, $"{id}: BuildReport from {{review:...}} is schema-valid");
    Check(Body(pW) == Body(pI), $"{id}: BuildReport text identical for wrapper and bare review");
}

Console.WriteLine("\n== 2f. review_json contract (runs/run10_review_json): Maestro passes the review_json string to in_ReviewJson");
foreach (var (id, file) in docs)
{
    var whole = Rd(Path.Combine(demo, "runs", "run10_review_json", id + ".result.json"));          // full agent output (3 fields)
    var root = JsonNode.Parse(whole)!.AsObject();
    var reviewJson = root["review_json"]!.GetValue<string>();                                      // what Maestro maps to in_ReviewJson
    var doubleEncoded = JsonValue.Create(reviewJson)!.ToJsonString();                              // "{\"document_id\":...}"
    var tripleEncoded = JsonValue.Create(doubleEncoded)!.ToJsonString();
    bool topHr = root["human_review_required"]!.GetValue<bool>();
    Check(root.Count == 3 && root["overall_assessment"] is JsonValue && topHr == expectReview[id],
          $"{id}: agent output has exactly review_json, human_review_required={topHr}, overall_assessment");
    var (rt, hr) = fmt.Execute(reviewJson, file + ".docx", sender);
    Check(hr == topHr, $"{id}: FormatReviewText(review_json) humanReviewRequired={hr} matches top-level flag");
    Check(fmt.Execute(doubleEncoded, file + ".docx", sender) == (rt, hr), $"{id}: double-encoded review_json parses the same");
    Check(fmt.Execute(tripleEncoded, file + ".docx", sender) == (rt, hr), $"{id}: triple-encoded review_json parses the same");
    Check(fmt.Execute(whole, file + ".docx", sender) == (rt, hr), $"{id}: whole agent output (3 fields) parses the same");
    string Body(string path) { using var d = WordprocessingDocument.Open(path, false); return System.Text.RegularExpressions.Regex.Replace(d.MainDocumentPart!.Document!.Body!.InnerText, @"\d{4}-\d{2}-\d{2} \d{2}:\d{2}", ""); }
    string dec = id == "C_sinirda" ? "Approve" : "";
    var (p1, _) = new BuildReport().Execute(reviewJson, dec, "", file + ".docx");
    var (p2, _) = new BuildReport().Execute(doubleEncoded, dec, "", file + ".docx");
    var (p3, _) = new BuildReport().Execute(whole, dec, "", file + ".docx");
    using (var d1 = WordprocessingDocument.Open(p1, false))
        Check(new OpenXmlValidator().Validate(d1).Count() == 0, $"{id}: BuildReport(review_json) is schema-valid");
    Check(Body(p1) == Body(p2) && Body(p1) == Body(p3), $"{id}: BuildReport text identical for review_json, double-encoded and whole output");
    if (id == "C_sinirda") File.Copy(p1, Path.Combine(outDir, "C_sinirda_Approve.review_json.report.docx"), true);
}

Console.WriteLine("\n== 3. BuildReport");
var build = new BuildReport();
var cases = new[]
{
    ("A_uyumlu", "", "", "A_uyumlu_aydinlatma_metni.docx"),
    ("B_eksik", "", "", "B_eksik_aydinlatma_metni.docx"),
    ("C_sinirda", "Approve", "Alıcı grupları sayılmış; demo kapsamında yeterli kabul edildi. Bir sonraki sürümde alıcı-amaç eşlemesi eklensin.", "C_sinirda_aydinlatma_metni.docx"),
    ("C_sinirda", "Reject", "Aktarım amacı fazla genel; metin düzeltilmeden yayımlanmasın.", "C_sinirda_aydinlatma_metni.docx"),
};
var validator = new OpenXmlValidator();
foreach (var (id, decision, comment, name) in cases)
{
    var json = Rd(Path.Combine(demo, "runs", "run5_needs_review", id + ".result.json"));
    var (path, fileName) = build.Execute(json, decision, comment, name);
    var dest = Path.Combine(outDir, $"{id}{(decision.Length > 0 ? "_" + decision : "")}.report.docx");
    File.Copy(path, dest, true);
    using var d = WordprocessingDocument.Open(dest, false);
    var errors = validator.Validate(d).ToList();
    foreach (var e in errors.Take(5)) Console.WriteLine($"     {e.Description} @ {e.Path?.XPath}");
    var body = d.MainDocumentPart!.Document!.Body!.InnerText;
    Check(errors.Count == 0, $"{fileName}: OpenXML schema-valid ({errors.Count} errors)");
    Check(body.Contains("Reviewed by lawyer") == (decision.Length > 0),
          $"{id} {decision}: 'Reviewed by lawyer' section {(decision.Length > 0 ? "present" : "absent")}");
    int nUrls = RegCheckShared.SourceUrls(RegCheckShared.ParseAgentJson(json)).Count;
    Check(d.MainDocumentPart.HyperlinkRelationships.Select(h => h.Uri.ToString()).Distinct().Count() == nUrls,
          $"{id}: {nUrls} cited source URLs, all present as clickable hyperlinks");
}

Console.WriteLine(fails == 0 ? "\nALL PASSED" : $"\n{fails} FAILED");
return fails == 0 ? 0 : 1;
