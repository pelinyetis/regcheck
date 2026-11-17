using System.Linq;
using System.Text;
using UiPath.CodedWorkflows;

namespace RegCheck_Orchestrator
{
    /// <summary>
    /// Builds the read-only text a lawyer sees in the Action Center form (HumanReview step).
    /// Layout: header (document, sender, controller, overall result, summary), numbered findings
    /// (issue, citations with quote, confidence, "⚠ Needs review" if escalated), then a Sources
    /// section with one URL per line.
    /// Arguments: in agentJson, in documentName, in senderEmail (both may be ""); out reviewText, out humanReviewRequired.
    /// humanReviewRequired = the agent's human_review_required OR any finding with escalate=true.
    /// </summary>
    public class FormatReviewText : CodedWorkflow
    {
        [Workflow]
        public (string reviewText, bool humanReviewRequired) Execute(string agentJson, string documentName, string senderEmail)
        {
            var r = RegCheckShared.ParseAgentJson(agentJson);
            bool humanReviewRequired = RegCheckShared.HumanReviewRequired(r);
            string S(string k) => RegCheckShared.Str(r, k);

            var docName = string.IsNullOrWhiteSpace(documentName) ? S("document_id") : documentName.Trim();
            var sb = new StringBuilder();
            sb.AppendLine("RegCheck · Privacy notice review (KVKK Art. 10)");
            sb.AppendLine("Document: " + (docName.Length > 0 ? docName : "—"));
            sb.AppendLine("Sender: " + (string.IsNullOrWhiteSpace(senderEmail) ? "—" : senderEmail.Trim()));
            sb.AppendLine("Data controller: " + (S("controller").Length > 0 ? S("controller") : "—"));
            sb.AppendLine("Overall result: " + RegCheckShared.Label(RegCheckShared.OverallLabels, S("overall_assessment")));
            sb.AppendLine("Summary: " + RegCheckShared.OneLine(S("summary")));
            sb.AppendLine();

            var findings = RegCheckShared.Findings(r).ToList();
            int flagged = findings.Count(f => RegCheckShared.Bool(f, "escalate"));
            if (findings.Count == 0)
            {
                sb.AppendLine("Findings: none.");
            }
            else
            {
                sb.AppendLine($"Findings ({findings.Count}; {flagged} awaiting a lawyer's decision)");
                int i = 0;
                foreach (var f in findings)
                {
                    i++;
                    string F(string k) => RegCheckShared.Str(f, k);
                    bool esc = RegCheckShared.Bool(f, "escalate");
                    sb.AppendLine($"{i}. {F("title")}" + (esc ? "   ⚠ Needs review" : ""));
                    sb.AppendLine($"   Element: {RegCheckShared.NormalizeElement(F("element"))} ({F("issue_type")}) · Severity: " +
                                  $"{RegCheckShared.Label(RegCheckShared.SeverityLabels, F("severity"))} · Confidence: {RegCheckShared.Conf(f)}");
                    sb.AppendLine("   Issue: " + RegCheckShared.OneLine(F("description")));
                    if (F("document_excerpt").Trim().Length > 0)
                        sb.AppendLine("   From the document: “" + RegCheckShared.OneLine(F("document_excerpt")) + "”");
                    foreach (var c in RegCheckShared.Objects(f, "citations"))
                        sb.AppendLine($"   Source: {RegCheckShared.Str(c, "reference")}: “{RegCheckShared.OneLine(RegCheckShared.Str(c, "supporting_quote"))}”");
                    if (esc && F("escalation_reason").Trim().Length > 0)
                        sb.AppendLine("   Question for the lawyer: " + RegCheckShared.OneLine(F("escalation_reason")));
                    if (F("recommendation").Trim().Length > 0)
                        sb.AppendLine("   Recommendation: " + RegCheckShared.OneLine(F("recommendation")));
                    sb.AppendLine();
                }
            }

            var pe = r["penalty_exposure"];
            if (RegCheckShared.Bool(pe, "applicable"))
            {
                sb.AppendLine($"Administrative fine exposure: {RegCheckShared.Str(pe, "reference")}: {RegCheckShared.Str(pe, "range")}");
                sb.AppendLine();
            }

            sb.AppendLine("Sources");
            var urls = RegCheckShared.SourceUrls(r);
            if (urls.Count == 0) sb.AppendLine("—");
            foreach (var u in urls) sb.AppendLine(u);

            return (sb.ToString().Replace("\r\n", "\n").TrimEnd() + "\n", humanReviewRequired);
        }
    }
}
