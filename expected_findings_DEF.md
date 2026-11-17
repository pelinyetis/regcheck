# Expected findings: second test set (D, E, F)

Three new **fictional** privacy notices (aydınlatma metni), delivered as **PDF with a normal text layer**, so the agent is tested on documents and sectors it has never seen. Every company, address, MERSİS number, phone number and domain is invented. Each document starts with "KURGUSAL ÖRNEK BELGE – yalnızca demo amaçlıdır…".

| File | Sector / controller (fictional) | Designed outcome |
|---|---|---|
| `docs/D_klinik_uyumlu_aydinlatma_metni.pdf` | Private clinic, *Ilgaz Tıp Merkezi Sağlık Hizmetleri A.Ş.* (health data, KVKK md. 6) | compliant |
| `docs/E_spor.pdf` | Gym chain, *Çınaraltı Spor ve Sağlıklı Yaşam Hizmetleri Ltd. Şti.* ("ÇınarFit") | non-compliant: **10/1-b** and **10/1-c** missing |
| `docs/F_fintech.pdf` | Payment / e-money app, *Defne Ödeme ve Elektronik Para Hizmetleri A.Ş.* ("DefnePay") | borderline: legal bases listed but **not mapped to purposes** (10/1-ç) |

Generator: `scripts/build_docs_def.py` (reportlab, embedded Arial). Text extracted with our `ExtractDocumentText` code is saved by the test harness as `orchestrator_tests/out/<name>.pdf.extracted.txt`.

The rules are the same as in `expected_findings.md`: the five md. 10/1 elements, the deterministic rule (`missing` → high confidence, not escalated; `deficient` → confidence ≤ 0.60, escalated), and `human_review_required` = any finding escalated.

**Sector law used in D (checked live on 2026-11-05 with `search_within_kanun`, 6698 md. 6 as amended by Law 7499):** health data is special-category data (md. 6/1). Processing it is allowed under **md. 6/3-(e)**: by persons under a duty of confidentiality, for medical diagnosis, treatment and care and for the planning, management and financing of health services. Law-based processing falls under **md. 6/3-(b)**. Since 2024 there is no separate health-data rule in md. 6/2 (repealed).

---

## D: private clinic, fully compliant

**Design:**
- **a:** identity table plus "no representative".
- **b:** six specific purposes in a purpose → data → legal basis table.
- **ç:** legal bases mapped per purpose, including md. 6/3-e for diagnosis and treatment, md. 5/2-a with 6/3-b for statutory records, and md. 6/3-e for the financing of health services; collection channels with automated / non-automated methods.
- **c:** five recipient groups, each with a transfer purpose (Sağlık Bakanlığı / e-Nabız, SGK, private insurer, external labs, authorities) and "yurt dışına aktarılmamaktadır".
- **d:** all nine md. 11 rights and how to apply.
- Explicit consent (satisfaction surveys) is handled under a separate consent text.

| Element | Expected status |
|---|---|
| 10/1-a | present |
| 10/1-b | present |
| 10/1-c | present |
| 10/1-ç | present |
| 10/1-d | present |

**Expected findings:** none. **Overall:** `compliant`. **human_review_required:** `false`. No fine exposure.

**What this tests:** special-category data must not trigger false positives. If the agent wants to check a md. 6 reference, it can fetch md. 6 with `search_within_kanun`, and the letters in D match the current text.

## E: gym chain, two elements missing (different from B)

**Design:**
- **a, ç, d present and specific:**
  - identity table, no representative;
  - a data category → legal basis table (md. 5/2-c, 5/2-ç, 5/2-f, 5/1) plus concrete collection channels (reception forms, app/website, card readers, cameras; automated / non-automated);
  - all nine md. 11 rights and how to apply.
- **b missing:** the notice **never states why** data is processed. There are no purposes, only data categories and their legal bases. Words such as "amaç" appear only in the standard md. 11 rights list and in the fictional-document banner.
- **c missing:** there is **no section and no sentence on transfers**: no recipients, no transfer purpose, no statement about transfers abroad. "aktar…" appears only inside the md. 11 rights list.

| Element | Expected status |
|---|---|
| 10/1-a | present |
| 10/1-b | **missing** |
| 10/1-c | **missing** |
| 10/1-ç | present |
| 10/1-d | present |

**Expected findings:**

| ID | Element | issue_type | Escalate | Must cite |
|---|---|---|---|---|
| E-1 | 10/1-b | missing | false (confidence ≥ 0.85) | 6698 md. 10/1-b |
| E-2 | 10/1-c | missing | false (confidence ≥ 0.85) | 6698 md. 10/1-c; Kurul 2021/85 (Tebliğ 5/1-ı) is a fitting support |

**Overall:** `non_compliant`. **human_review_required:** `false`. **Penalty exposure:** md. 18/1-a applicable.

**Known risk:** the agent may argue that legal bases such as "sözleşmenin ifası" *imply* a purpose and mark 10/1-b as `deficient` instead of `missing`. Under the deterministic rule that finding would then be escalated (confidence ≤ 0.60), so the overall result would still be `non_compliant` (because of E-2), but with `human_review_required: true`. Treat that as a partial miss on E-1.

## F: payment app, borderline legal-basis wording (different from C)

**Design:**
- **a:** identity table plus "no representative".
- **b:** six specific purposes listed (account opening and identity verification, payments and transfers, AML/KYC under Law 5549, fraud prevention, customer requests, marketing with consent).
- **c:** five recipient groups with a purpose each (TCMB, MASAK, the counterparty bank, a domestic remote-ID provider, authorities) and "yurt dışına aktarılmamaktadır".
- **ç:** concrete collection channels. **But** the legal bases are given only as **one generic paragraph**: "kanunlarda açıkça öngörülmesi, … sözleşmenin kurulması veya ifası, … hukuki yükümlülük … ve … meşru menfaat hukuki sebeplerinden **bir veya birkaçına** dayanılarak". The paragraph is not mapped to which purpose relies on which basis. Marketing → explicit consent is the only mapped item.
- **d:** all nine md. 11 rights and how to apply.

**Why it is borderline:** the bases are named correctly, and practice often accepts such lists, but Tebliğ 5/1-(h) (as quoted in Kurul 2021/85) asks for the legal basis to be stated explicitly. Kurul 2019/206 concerned a notice that did not clearly state its legal bases. Whether an unmapped list is "explicit enough" is a judgment call. This differs from C, whose issue was vague **recipients and transfer purpose** (10/1-c).

| Element | Expected status |
|---|---|
| 10/1-a | present |
| 10/1-b | present |
| 10/1-c | present |
| 10/1-ç | **deficient** |
| 10/1-d | present |

**Expected findings:**

| ID | Element | issue_type | Escalate | Must cite |
|---|---|---|---|---|
| F-1 | 10/1-ç (Tebliğ 5/1-h accepted as element) | deficient | **true** (confidence ≤ 0.60) | 6698 md. 10/1-ç; fitting support: Kurul 2021/85 (Tebliğ 5/1-h) or 2019/206 |

**Overall:** `needs_human_review`. **human_review_required:** `true`. **Penalty exposure:** not applicable (no confirmed violation).

---

## Machine-readable expectations

Same format as `expected_findings.md`. Document IDs: `D_klinik_uyumlu`, `E_spor_eksik`, `F_fintech_sinirda` (files: see the table at the top).

```json expected
{
  "D_klinik_uyumlu": {
    "overall": "compliant",
    "elements": {"10/1-a": ["present"], "10/1-b": ["present"], "10/1-c": ["present"], "10/1-ç": ["present"], "10/1-d": ["present"]},
    "penalty": false,
    "human_review_required": false,
    "findings": []
  },
  "E_spor_eksik": {
    "overall": "non_compliant",
    "elements": {"10/1-a": ["present"], "10/1-b": ["missing"], "10/1-c": ["missing"], "10/1-ç": ["present"], "10/1-d": ["present"]},
    "penalty": true,
    "human_review_required": false,
    "findings": [
      {"id": "E-1", "elements": ["10/1-b"], "escalate": false, "must_cite": ["6698 md. 10"]},
      {"id": "E-2", "elements": ["10/1-c", "T5/1-ı"], "escalate": false, "must_cite": ["6698 md. 10"]}
    ]
  },
  "F_fintech_sinirda": {
    "overall": "needs_human_review",
    "elements": {"10/1-a": ["present"], "10/1-b": ["present"], "10/1-c": ["present"], "10/1-ç": ["deficient"], "10/1-d": ["present"]},
    "penalty": false,
    "human_review_required": true,
    "findings": [
      {"id": "F-1", "elements": ["10/1-ç", "T5/1-h"], "escalate": true, "must_cite": ["6698 md. 10"]}
    ]
  }
}
```

## Text extraction check (2026-11-05)

`ExtractDocumentText` (PdfPig, the same code used in UploadDocstoSB) on the three PDFs, from the unit-test harness (`orchestrator_tests`, block 1b):

| File | Characters | Key phrases intact | Replacement chars / glued words | Word recall vs. PyMuPDF |
|---|---|---|---|---|
| D | 5,879 | ✅ (e.g. "Kanun md. 6/3-e", "ğ) Kişisel verilerinizin kanuna aykırı…") | none | 100.0% |
| E | 4,157 | ✅; the deliberately absent wording ("amacıyla", "Alıcı grubu", "aktarılabilecektir") is really absent | none | 100.0% |
| F | 5,836 | ✅ (e.g. "…hukuki sebeplerinden bir veya birkaçına dayanılarak") | none | 100.0% |

Tables come out row by row (purpose → categories → legal basis). Cell text wraps over several lines, and adjacent cells can share a line without a separator, but row order is preserved and readable.
