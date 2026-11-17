using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Text.Json;
using System.Text.RegularExpressions;
using System.Text.Json.Nodes;

namespace RegCheck_Orchestrator
{
    /// <summary>
    /// Helpers shared by the RegCheck coded workflows (ExtractDocumentText, FormatReviewText, BuildReport).
    /// This is a plain coded source file, not a workflow: it has no [Workflow] method and no arguments.
    /// The agent JSON layout is defined in the demo folder: agent/output_schema.json.
    /// </summary>
    public static class RegCheckShared
    {
        public static readonly IReadOnlyDictionary<string, string> ElementLabels = new Dictionary<string, string>
        {
            ["10/1-a"] = "Identity of the controller (and representative, if any)",
            ["10/1-b"] = "Purposes of processing",
            ["10/1-c"] = "Recipients and purposes of transfer",
            ["10/1-ç"] = "Method of collection and legal basis",
            ["10/1-d"] = "Data subject rights under Art. 11",
        };

        public static readonly IReadOnlyDictionary<string, string> OverallLabels = new Dictionary<string, string>
        {
            ["compliant"] = "✅ Compliant",
            ["non_compliant"] = "❌ Non-compliant",
            ["needs_human_review"] = "⚠️ Lawyer review required",
        };

        public static readonly IReadOnlyDictionary<string, string> StatusLabels = new Dictionary<string, string>
        {
            ["present"] = "✅ Present",
            ["deficient"] = "⚠️ Deficient",
            ["missing"] = "❌ Missing",
        };

        public static readonly IReadOnlyDictionary<string, string> SeverityLabels = new Dictionary<string, string>
        {
            ["high"] = "High",
            ["medium"] = "Medium",
            ["low"] = "Low",
        };

        /// <summary>
        /// Parses the ReviewAgent output (agent/output_schema.json). Accepts the plain JSON object (what Maestro
        /// passes, mime type application/json), a JSON string that contains it (double-encoded), a ```json fenced
        /// block, or any wrapper that contains it a few levels down, e.g. {"output": {...}} or the trace span
        /// UiPath shows for an agent run ({"Attributes": {"output": {...}}}).
        /// </summary>
        public static JsonObject ParseAgentJson(string agentJson)
        {
            if (string.IsNullOrWhiteSpace(agentJson))
                throw new ArgumentException("agentJson is empty: the ReviewAgent output was not passed to this step.");
            var result = FindResult(ParseOrThrow(agentJson), 0);
            if (result == null)
                throw new ArgumentException("agentJson has no 'findings' array: this is not the ReviewAgent output (see agent/output_schema.json).");
            return result;
        }

        private static JsonObject? FindResult(JsonNode? node, int depth)
        {
            if (node == null || depth > 4) return null;
            if (node is JsonValue v && v.TryGetValue<string>(out var s))
            {
                var t = s.Trim();
                return t.StartsWith("{") || t.StartsWith("\"") || t.StartsWith("```") ? FindResult(ParseOrThrow(t), depth + 1) : null;
            }
            if (node is not JsonObject o) return null;
            if (o["findings"] is JsonArray) return o;
            // prefer an "output" property (agent span / Maestro wrappers), then any other property
            var children = o.OrderBy(kv => kv.Key == "output" ? 0 : 1).Select(kv => kv.Value);
            foreach (var c in children)
            {
                if (c is JsonObject || (c is JsonValue cv && cv.TryGetValue<string>(out var cs) && cs.Contains("\"findings\"")))
                {
                    var r = FindResult(c, depth + 1);
                    if (r != null) return r;
                }
            }
            return null;
        }

        private static JsonNode ParseOrThrow(string text)
        {
            var t = text.Trim();
            if (t.StartsWith("```"))
            {
                int firstNewLine = t.IndexOf('\n');
                t = firstNewLine >= 0 ? t[(firstNewLine + 1)..] : "";
                if (t.TrimEnd().EndsWith("```")) t = t.TrimEnd()[..^3];
            }
            try
            {
                return JsonNode.Parse(t) ?? throw new ArgumentException("agentJson is JSON null.");
            }
            catch (JsonException e)
            {
                throw new ArgumentException("agentJson is not valid JSON: " + e.Message, e);
            }
        }

        /// <summary>
        /// True if a lawyer must review: the agent's human_review_required OR any finding with escalate=true,
        /// so a missing or inconsistent flag can never skip a review.
        /// </summary>
        public static bool HumanReviewRequired(JsonObject r) =>
            Bool(r, "human_review_required") || Findings(r).Any(f => Bool(f, "escalate"));

        /// <summary>
        /// The agent in UiPath writes elements as "6698 md. 10/1-a"; the schema enum (and the local runs) use
        /// "10/1-a". Returns the short form ("10/1-a", "T5/1-g") or the trimmed input if it matches neither.
        /// </summary>
        public static string NormalizeElement(string element)
        {
            var e = (element ?? "").Trim();
            var m = Regex.Match(e, @"10/1-([a-zçğıöşü])", RegexOptions.IgnoreCase);
            if (m.Success) return "10/1-" + m.Groups[1].Value.ToLowerInvariant();
            m = Regex.Match(e, @"^(?:T|Tebliğ(?: md\.)?\s*)5/1-([a-zçğıöşüi])", RegexOptions.IgnoreCase);
            if (m.Success) return "T5/1-" + m.Groups[1].Value.ToLowerInvariant();
            return e;
        }

        public static IEnumerable<JsonObject> Findings(JsonObject r) =>
            (r["findings"] as JsonArray ?? new JsonArray()).OfType<JsonObject>();

        public static IEnumerable<JsonObject> Objects(JsonNode? n, string key) =>
            (n?[key] as JsonArray ?? new JsonArray()).OfType<JsonObject>();

        public static string Str(JsonNode? n, string key)
        {
            var v = n?[key];
            if (v == null) return "";
            if (v is JsonValue jv && jv.TryGetValue<string>(out var s)) return s;
            return v.ToJsonString();
        }

        public static bool Bool(JsonNode? n, string key)
        {
            var v = n?[key] as JsonValue;
            if (v == null) return false;
            if (v.TryGetValue<bool>(out var b)) return b;
            if (v.TryGetValue<string>(out var s)) return s.Trim().Equals("true", StringComparison.OrdinalIgnoreCase);
            return false;
        }

        public static double? Num(JsonNode? n, string key)
        {
            var v = n?[key] as JsonValue;
            if (v == null) return null;
            if (v.TryGetValue<double>(out var d)) return d;
            if (v.TryGetValue<string>(out var s) &&
                double.TryParse(s, NumberStyles.Float, CultureInfo.InvariantCulture, out var p)) return p;
            return null;
        }

        /// <summary>Confidence formatted like the Markdown report template ("0.50").</summary>
        public static string Conf(JsonNode? f)
        {
            var c = Num(f, "confidence");
            return c.HasValue ? c.Value.ToString("0.00", CultureInfo.InvariantCulture) : "—";
        }

        public static string Label(IReadOnlyDictionary<string, string> map, string key) =>
            map.TryGetValue(key, out var l) ? l : key;

        /// <summary>Distinct source URLs in order of first use: citations, then the penalty source.</summary>
        public static List<string> SourceUrls(JsonObject r)
        {
            var urls = new List<string>();
            foreach (var f in Findings(r))
                foreach (var c in Objects(f, "citations"))
                {
                    var u = Str(c, "source_url").Trim();
                    if (u.Length > 0 && !urls.Contains(u)) urls.Add(u);
                }
            var pe = r["penalty_exposure"];
            if (Bool(pe, "applicable"))
            {
                var u = Str(pe, "source_url").Trim();
                if (u.Length > 0 && !urls.Contains(u)) urls.Add(u);
            }
            return urls;
        }

        /// <summary>
        /// Normalises the Action Center outcome. Returns "" when no review happened (empty input),
        /// otherwise "Approve", "Reject" or the raw value.
        /// </summary>
        public static string NormalizeDecision(string? decision)
        {
            var d = (decision ?? "").Trim();
            if (d.Length == 0) return "";
            var k = d.ToLowerInvariant();
            if (k is "approve" or "approved" or "onayla" or "onaylandı") return "Approve";
            if (k is "reject" or "rejected" or "reddet" or "reddedildi") return "Reject";
            return d;
        }

        public static string DecisionLabel(string normalized) => normalized switch
        {
            "Approve" => "✅ Approved",
            "Reject" => "❌ Rejected",
            "" => "—",
            _ => normalized,
        };

        public static string OneLine(string s) =>
            string.Join(" ", (s ?? "").Split(new[] { '\r', '\n' }, StringSplitOptions.RemoveEmptyEntries)).Trim();
    }
}
