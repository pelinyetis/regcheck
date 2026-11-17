# Expected findings: RegCheck KVKK test set

This is the ground truth for the three **fictional** test documents in `docs/`. The data controller is *Kuzey Yıldızı Kitap ve Kırtasiye Ticaret A.Ş.*, an invented online bookshop. All three documents are built from the same text by `scripts/build_docs.js` and differ only in the sections described below.

## Legal basis used for the expected findings

| Ref | What it says (short) | Source |
|---|---|---|
| **6698 md. 10/1 (a)–(d)** | A notice must cover (a) the controller's identity, (b) the processing purpose, (c) recipients and transfer purpose, (ç) the collection method and legal basis, (d) the rights in md. 11 | mevzuat-mcp `search_within_kanun` (6698), saved in `tools/out/t5.txt`. https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=6698&MevzuatTur=1&MevzuatTertip=5 |
| **6698 md. 11/1 (a)–(ğ)** | The nine data-subject rights | `search_within_kanun`, saved in `tools/out/art_11.txt` |
| **6698 md. 18/1-a** | Administrative fine of 5.000–100.000 TL for breaching md. 10 (amounts as written in the statute text) | `search_within_kanun`, saved in `tools/out/t2.txt` |
| **Aydınlatma Tebliği md. 4/1, 5/1 (f), (g), (ğ), (h), (ı), (j)** | (f) notice and explicit consent are separate; (g) no vague or general wording; (ğ) plain language; (h) the legal basis means which condition in md. 5 or 6 is relied on, and must be stated explicitly; (ı) transfer purpose and **recipient groups** must be stated; (j) no incomplete or misleading information | Original text: RG 10.03.2018/30356. The agent has no Tebliğ tool, so it can only cite these clauses through **Kurul Kararı 2021/85**, which quotes them verbatim (fetched with yargi-mcp `get_kvkk_document_markdown`). |
| **Kurul Kararı 2021/85** (03.02.2021) | Quotes Tebliğ 4/1 and 5/1 (f), (g), (ğ), (h), (ı), (j) | https://www.kvkk.gov.tr/Icerik/7112/2021-85 |
| **Kurul Kararı 2022/1358** (23.12.2022) | A notice existed but had deficiencies; the controller was instructed to fix it under md. 10 and the Tebliğ | https://www.kvkk.gov.tr/Icerik/7595/2022-1358 |
| **Kurul Kararı 2018/90** (26.07.2018) | The notice and explicit consent must be handled separately (Tebliğ 5/1-f) | https://www.kvkk.gov.tr/Icerik/5420/2018-90 |
| **Kurul Kararı 2020/404** (20.05.2020) | The burden of proving the notice was given lies with the controller (Tebliğ 5/1-e) | https://www.kvkk.gov.tr/Icerik/6913/2020-404 |

Note: Tebliğ 5/1-(c) was repealed by a 2019 amending Tebliğ, so it must not be cited.

---

## Document A: `A_uyumlu_aydinlatma_metni.docx` (compliant)

**Design:** every md. 10/1 element is present and specific:
- an identity table, with a statement that there is no representative
- a purpose → data category → **legal basis per purpose** table (md. 5/2-c, ç, e, f; md. 5/1 for marketing, under a separate consent text)
- the collection channels, plus automated vs. non-automated collection
- a table of recipient groups with a transfer purpose for each, and no transfers abroad
- all nine md. 11 rights, with how to apply

| Element | Expected status |
|---|---|
| 10/1-a | present |
| 10/1-b | present |
| 10/1-c | present |
| 10/1-ç | present |
| 10/1-d | present |

**Expected findings:** none.
**Overall:** `compliant`. No fine exposure, no escalation.
*An escalated (confidence < 0.7) observation is tolerated but counted as a false positive. A high-confidence finding is a hard false positive.*

---

## Document B: `B_eksik_aydinlatma_metni.docx` (missing two required elements)

**Design:** same as A except:
1. The "Toplama yöntemi" section is **deleted**, and the purposes table has **no legal-basis column**.
2. The md. 11 rights section is **replaced** by a single contact line ("soru ve talepleriniz için kvkk@… adresine yazın").

The footer still claims "Bu metin, Kanun'un 10'uncu maddesi uyarınca hazırlanmıştır" ("This text was prepared under article 10 of the Law"). That is realistic, and the claim is false.

| Element | Expected status |
|---|---|
| 10/1-a | present |
| 10/1-b | present |
| 10/1-c | present |
| 10/1-ç | **missing** (`deficient` also accepted: the words "açık rıza" appear once, for marketing only) |
| 10/1-d | **missing** |

| ID | Expected finding | Must cite | Should also cite (if found) | Confidence | Escalate |
|---|---|---|---|---|---|
| **B-1** | Collection method and legal basis are not stated (no method; no md. 5/6 condition for any purpose) | 6698 md. 10/1-ç | Kurul 2021/85 (Tebliğ 5/1-h: legal basis must be stated explicitly); Kurul 2022/1358 (deficient notice → instruction to fix) | ≥ 0.7 (expected ~0.9) | no |
| **B-2** | The data subject's md. 11 rights are not listed; a contact e-mail alone is not enough | 6698 md. 10/1-d, md. 11 | Kurul 2021/85 (Tebliğ 4/1-d via quote, 5/1-j incomplete information); Kurul 2022/1358 | ≥ 0.7 (expected ~0.9) | no |

**Fine exposure:** 6698 md. 18/1-a, 5.000–100.000 TL.
**Overall:** `non_compliant`.

---

## Document C: `C_sinirda_aydinlatma_metni.docx` (borderline)

**Design:** same as A except the transfer table is replaced by one sentence:

> "Kişisel verileriniz, yukarıda sayılan amaçların gerçekleştirilmesi ve Şirket'in ticari faaliyetlerinin yürütülmesi kapsamında, Kanun'un 8'inci maddesinde belirtilen şartlara uygun olarak iş ortaklarımıza, tedarikçilerimize, hizmet aldığımız üçüncü kişilere ve yetkili kamu kurum ve kuruluşlarına aktarılabilecektir."

**Why it is borderline:** recipient groups *are* named, so md. 10/1-c is formally met, and many market-standard notices use this wording. However, "hizmet aldığımız üçüncü kişiler" and the catch-all purpose "ticari faaliyetlerinin yürütülmesi" are arguably the general, vague wording that Tebliğ 5/1-g prohibits. They also don't map each recipient group to its own purpose, which Tebliğ 5/1-ı arguably requires. Whether this is non-compliant is a lawyer's judgment.

| Element | Expected status |
|---|---|
| 10/1-a | present |
| 10/1-b | present |
| 10/1-c | **deficient** (`present` also accepted, provided the finding below is raised) |
| 10/1-ç | present |
| 10/1-d | present |

| ID | Expected finding | Must cite | Should also cite | Confidence | Escalate |
|---|---|---|---|---|---|
| **C-1** | Transfer recipients and purpose are described generically ("iş ortakları", "üçüncü kişiler", "ticari faaliyetlerin yürütülmesi"), so they may not meet the specificity the Tebliğ requires | 6698 md. 10/1-c | Kurul 2021/85 (Tebliğ 5/1-g vague wording; 5/1-ı recipient groups and transfer purpose) | **< 0.7** | **yes** |

Accepted element codes for C-1: `10/1-c`, `T5/1-g`, `T5/1-ı`.
**Fine exposure:** none asserted with confidence (an escalated finding alone does not trigger an md. 18 assertion).
**Overall:** `needs_human_review`.

---

## Scoring rules (implemented in `scripts/evaluate.py`)

1. **Element accuracy:** each of the 15 element checks (3 docs × 5) is compared to the accepted statuses.
2. **Finding recall:** an expected finding is matched by an agent finding whose `element` is one of its accepted codes.
3. **False positives:** agent findings that match nothing. They are reported separately depending on whether they were escalated.
4. **Escalation accuracy:** each matched finding's `escalate` must equal the expected value.
5. **Citation rules:** every finding needs ≥ 1 citation with a reference and source URL. Every Kurul citation URL must appear in this run's tool results. Every statute citation must be md. 10, 11 or 18 (given in the prompt) or an article returned by `search_within_kanun` in this run. The "must cite" references must be present.
6. **Confidence rule:** `escalate == (confidence < 0.7)` for every finding.
7. **Overall assessment** must match.

```json expected
{
  "A_uyumlu": {
    "overall": "compliant",
    "elements": {"10/1-a": ["present"], "10/1-b": ["present"], "10/1-c": ["present"], "10/1-ç": ["present"], "10/1-d": ["present"]},
    "penalty": false,
    "findings": []
  },
  "B_eksik": {
    "overall": "non_compliant",
    "elements": {"10/1-a": ["present"], "10/1-b": ["present"], "10/1-c": ["present"], "10/1-ç": ["missing", "deficient"], "10/1-d": ["missing"]},
    "penalty": true,
    "findings": [
      {"id": "B-1", "elements": ["10/1-ç", "T5/1-h", "T5/1-i"], "escalate": false, "must_cite": ["6698 md. 10"]},
      {"id": "B-2", "elements": ["10/1-d"], "escalate": false, "must_cite": ["6698 md. 10"]}
    ]
  },
  "C_sinirda": {
    "overall": "needs_human_review",
    "elements": {"10/1-a": ["present"], "10/1-b": ["present"], "10/1-c": ["deficient", "present"], "10/1-ç": ["present"], "10/1-d": ["present"]},
    "penalty": false,
    "findings": [
      {"id": "C-1", "elements": ["10/1-c", "T5/1-g", "T5/1-ı"], "escalate": true, "must_cite": ["6698 md. 10"]}
    ]
  }
}
```
