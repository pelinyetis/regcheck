# RegCheck: build guide for the Maestro RPA steps

Maestro (BPMN, Studio Web) process:

```
UploadDocstoSB (RPA) ──▶ ReviewAgent (agent) ──▶ ◇ human_review_required? ──yes──▶ HumanReview (RPA) ──▶ GenerateReport (RPA)
                                                           └──────────no───────────────────────────────▶ GenerateReport (RPA)
```

This Studio project (`RegCheck_Orchestrator`, Windows, VB) holds the coded workflows and the two XAML entry points you build yourself: **HumanReview.xaml** and **GenerateReport.xaml**. UploadDocstoSB stays its own project. You only add text extraction to it.

| File | Kind | Arguments |
|---|---|---|
| `ExtractDocumentText.cs` | coded workflow | in `filePath` → out `text`, `charCount` |
| `FormatReviewText.cs` | coded workflow | in `agentJson`, `documentName`, `senderEmail` → out `reviewText`, `humanReviewRequired` |
| `BuildReport.cs` | coded workflow | in `agentJson`, `reviewerDecision`, `reviewerComment`, `documentName` → out `reportPath`, `reportFileName` |
| `RegCheckShared.cs` | coded source file (helpers) | none (not a workflow) |

All three were tested outside Studio with the 3 demo documents (see section 7).

---

## 1. Data that flows through Maestro

Create these **Maestro process variables** in the Data Manager. Map each task's outputs to them, and feed them into the next task's inputs.

| Maestro variable | Type | Produced by | Consumed by |
|---|---|---|---|
| `documentText` | String | UploadDocstoSB `out_DocumentText` | ReviewAgent input `document_text` |
| `documentName` | String | UploadDocstoSB `out_DocumentName` | HumanReview, GenerateReport |
| `senderEmail` | String | UploadDocstoSB `out_SenderEmail` | HumanReview, GenerateReport |
| `subject` | String | UploadDocstoSB `out_Subject` | GenerateReport |
| `bucketPath` | String | UploadDocstoSB `out_BucketPath` | (log/trace only) |
| `reviewJson` | String | ReviewAgent output **`review_json`** | HumanReview `in_ReviewJson`; GenerateReport `in_ReviewJson` |
| `humanReviewRequired` | Boolean | ReviewAgent output **`human_review_required`** | exclusive gateway |
| `overallAssessment` | String | ReviewAgent output **`overall_assessment`** | optional: logging, end event output |
| `reviewDecision` | String | HumanReview `out_ReviewDecision` (`Approve`/`Reject`) | GenerateReport `in_ReviewDecision` |
| `reviewComment` | String | HumanReview `out_ReviewComment` | GenerateReport `in_ReviewComment` |
| `reportBucketPath` | String | GenerateReport `out_ReportBucketPath` | end event output (optional) |

**Initialise `reviewDecision` and `reviewComment` to an empty string.** On the "no review" path HumanReview doesn't run. GenerateReport then receives `""`, and the report correctly has no lawyer section.

### Agent ↔ Maestro contract: three plain fields

Maestro doesn't map object outputs or object arguments. So the agent output (`agent/output_schema.json`) has **exactly three top-level fields, all plain types**:

| Agent output field | Type | Content |
|---|---|---|
| `review_json` | String | The **full review** (document_id, controller, overall_assessment, summary, element_checks, findings, penalty_exposure, human_review_required, sources_consulted) **serialised as a JSON string**. Its structure is `agent/review_schema.json`. |
| `human_review_required` | Boolean | true if any finding has `escalate: true`. This is the routing flag. |
| `overall_assessment` | String | `compliant` / `non_compliant` / `needs_human_review` |

Both top-level copies equal the values inside `review_json`; the local evaluator checks this.

**Passing it on:**
- HumanReview.xaml and GenerateReport.xaml take **`in_ReviewJson` (String)** and pass it straight to the coded workflows. There is no conversion step.
- Map Maestro variable `reviewJson` → `in_ReviewJson` in both tasks.
- The coded workflows accept whatever text arrives:
  - the review JSON itself
  - the same text **double- or triple-encoded** (a JSON string containing the JSON)
  - the whole agent output (`{"review_json": "...", ...}`)
  - a ```` ```json ```` block
  - older wrappers (`{"review": {...}}`, `{"result": {...}}`, the trace span)

  All of these were tested on real agent outputs (section 7).

(History, 2026-11-05: the review was first an object field `result`, then `review`. Maestro reserves `result`, and it doesn't map objects at all, hence this string contract.)

**Element values:** UiPath's agent writes elements as `"6698 md. 10/1-a"`, the local runs as `"10/1-a"`. The coded workflows normalise both, so labels and tables come out the same.

**Argument size:** Orchestrator caps job input arguments at **10,000 characters of JSON** per job; larger payloads need Robot 2025.10+, which sends them as an attachment.
- Demo sizes: document text 3.4–5.9k characters, `review_json` 1.6–4.9k characters.
- Turkish characters may be escaped as `\u00fc`, which inflates the count.

For larger real documents, pass the bucket path and read the text inside the step instead.

---

## 2. Project setup (RegCheck_Orchestrator), already done in `project.json`

**Studio is open?** Close and reopen the project, or accept the reload prompt, so it restores the new packages.

| Package | Version | Why |
|---|---|---|
| `DocumentFormat.OpenXml` | 3.3.0 | DOCX read/write in the coded workflows. Same version UiPath.Excel.Activities 3.4.1 already pulls in, so there's no conflict. |
| `PdfPig` | 0.1.16 | PDF text extraction, pure .NET (Apache-2.0), no Word or Acrobat needed |
| `UiPath.Persistence.Activities` | 1.13.0 | **Create Form Task**, **Wait for Form Task and Resume** |
| `UiPath.FormActivityLibrary` | 2.0.8 | Form Designer for Create Form Task (docs: ≥ 2.0.7) |
| `UiPath.System.Activities` | 25.10.5 (already there) | Upload/Download Storage File, Log Message, Invoke Workflow File, Run Job |
| `UiPath.Mail.Activities` | 2.7.12 (already there) | Send Outlook / SMTP mail |

Runtime options changed:
- **`supportsPersistence: true`**: required by *Wait for Form Task and Resume*. The job suspends while the lawyer works in Action Center and resumes afterwards.
- **`requiresUserInteraction: false`**: runs as a background process. Nothing in these steps touches the UI.

### Entry points (one package, two Orchestrator processes)

1. In Studio: **New › Workflow** → `HumanReview.xaml`, and another → `GenerateReport.xaml`.
2. Right-click each in the Project panel → **Set as Entry Point**. `Main.xaml` can stay empty; it isn't used.
3. Publish once.
4. In **Orchestrator → your folder → Automations → Processes → Add process**, create two processes from the `RegCheck_Orchestrator` package:
   - **HumanReview** with Entry point `HumanReview.xaml`
   - **GenerateReport** with Entry point `GenerateReport.xaml`
5. Maestro's service tasks point at these two processes. Each time you change arguments, republish and **upgrade both processes**. Otherwise new arguments don't appear in Maestro's mapping.

---

## 3. UploadDocstoSB: add text extraction and outputs

This is your existing project; nothing in it was changed. Do this in Studio:

1. **Packages:** Manage Packages → add `DocumentFormat.OpenXml` **3.3.0** and `PdfPig` **0.1.16**.
2. **Add the coded workflow:**
   - Copy `ExtractDocumentText.cs` from this project into UploadDocstoSB's folder.
   - Open it and change `namespace RegCheck_Orchestrator` to **`namespace UploadDocstoSB`**. A coded workflow must be in its own project's namespace.
   - The file has no other dependencies; it doesn't need `RegCheckShared.cs`.
3. **One document per run.** A Maestro instance handles one document, so UploadDocstoSB should process **one email per job**: take the first matching unread mail, save its attachment, and mark it read. Your queue-item step is no longer needed for this flow.
4. **Arguments** (Main.xaml → Arguments panel), all `Out`, type `String`:

   | Argument | Value to assign |
   |---|---|
   | `out_DocumentText` | from ExtractDocumentText (below) |
   | `out_DocumentName` | attachment file name, e.g. `Path.GetFileName(localFilePath)` |
   | `out_BucketPath` | the path you uploaded to in the bucket |
   | `out_SenderEmail` | `mail.From.Address` (or `mail.Headers("SenderEmailAddress")` for Outlook) |
   | `out_Subject` | `mail.Subject` |

5. **After the attachment is saved locally**, add **Invoke Workflow File**:
   - Workflow file name: `ExtractDocumentText.cs`
   - Click **Import Arguments**:
     - `filePath` (In) = `localFilePath`, the local path of the saved attachment
     - `text` (Out) = `out_DocumentText`
     - `charCount` (Out) = a new `Int32` variable `textChars`
   - Then add **Log Message** (Info): `"Extracted " + textChars.ToString + " characters from " + out_DocumentName`.

   Unsupported files (`.doc`, scans without a text layer, other extensions) throw an exception with a clear message, so the job fails and Maestro shows the reason.

---

## 4. ReviewAgent (Agent Builder) and the gateway

- **Agent input:** one argument `document_text` (String). The system prompt is `agent/system_prompt.md` from the demo folder.
- **Agent output:** schema `agent/output_schema.json`.
  - Three plain fields: `review_json` (String), `human_review_required` (Boolean), `overall_assessment` (String). See section 1.
  - The routing flag is **`human_review_required`** (boolean): true if any finding has `escalate: true`.
  - A temporary `needs_human_review` field was removed again; nothing uses it.
- **Maestro agent task:**
  - Input: `document_text` ← `documentText`.
  - Outputs: `review_json` → `reviewJson`, `human_review_required` → `humanReviewRequired`, `overall_assessment` → `overallAssessment`.
- **Exclusive gateway** after ReviewAgent:
  - Flow **"Hukukçu incelemesi"** → HumanReview, condition: `humanReviewRequired == true`. This is the Boolean variable mapped from the agent's `human_review_required` output. Pick it from the expression editor's autocomplete; the exact prefix depends on how Maestro names variables.
  - Flow **"İnceleme gerekmiyor"** → GenerateReport, marked as the **default flow**, so a missing flag never blocks the instance.
- **Extra safety:** HumanReview recomputes the flag from `review_json` (`human_review_required` **or** any finding with `escalate: true`). An inconsistent agent output can't skip the review once it reaches HumanReview.

---

## 5. HumanReview.xaml (RPA step with Action Center)

**Arguments**

| Name | Direction | Type |
|---|---|---|
| `in_ReviewJson` | In | String (the agent's `review_json`) |
| `in_DocumentName` | In | String |
| `in_SenderEmail` | In | String |
| `out_ReviewDecision` | Out | String |
| `out_ReviewComment` | Out | String |

**Variables** (Sequence scope)

| Name | Type |
|---|---|
| `reviewText` | String |
| `humanReviewRequired` | Boolean |
| `reviewComment` | String |
| `taskObject` | `UiPath.Persistence.Activities.FormTask.FormTaskData` |
| `taskAction` | String |

**Activities, in order**

1. **Log Message**: Level `Info`, Message `"HumanReview started for " + in_DocumentName`. Then **Log Message** (Trace) with the first 300 characters of `in_ReviewJson`.
2. **Invoke Workflow File**: `FormatReviewText.cs` → **Import Arguments**:
   - `agentJson` = `in_ReviewJson`
   - `documentName` = `in_DocumentName`
   - `senderEmail` = `in_SenderEmail`
   - `reviewText` → `reviewText`
   - `humanReviewRequired` → `humanReviewRequired`
3. **If** `Not humanReviewRequired` (defensive; the gateway should already have filtered these out):
   - **Then:**
     - **Assign** `out_ReviewDecision = ""`
     - **Assign** `out_ReviewComment = ""`
     - **Log Message** (Warn): `"No finding needs review; skipping Action Center"`
   - **Else:** steps 4–8.
4. **Create Form Task**:
   - **TaskTitle:** `"RegCheck hukukçu incelemesi: " + in_DocumentName`
   - **TaskPriority:** `TaskPriority.Medium`
   - **TaskCatalog:** optional, e.g. `"RegCheck"`. It must already exist in Action Center → Catalogs, or the activity fails with error 2451. Leave it empty for the demo.
   - **Orchestrator Folder Path:** leave empty (the job's folder).
   - **FormData** (click the collection):

     | Name | Direction | Type | Value |
     |---|---|---|---|
     | `reviewText` | In | String | `reviewText` |
     | `comment` | Out | String | `reviewComment` |

   - Tick **GenerateInputFields**, then **Open Form Designer** and arrange the form:
     - `reviewText`: **Text Area**, Label "İnceleme özeti", Property Name `reviewText`, rows ≈ 25, **Disabled** ✔ (read-only).
     - `comment`: **Text Area**, Label "Hukukçu yorumu", Property Name `comment`. Optionally tick *Required* under Validation.
     - Delete the default **Submit** button and add two **Button** components:
       - Label `Approve`, Action **Submit**, Property Name `Approve`, Theme *Success*.
       - Label `Reject`, Action **Submit**, Property Name `Reject`, Theme *Danger*.
     - The clicked button's name is returned as the task action. Check this in a first debug run; `BuildReport` accepts `Approve`/`approve`/`Reject`/`reject`.
   - **TaskObject (Output):** `taskObject`
5. **Log Message**: `"Form task created: " + taskObject.Id.ToString`
6. **Wait for Form Task and Resume**:
   - **TaskObject (Input):** `taskObject`
   - **TaskAction:** `taskAction`
   - **TaskObject (Output):** `taskObject`
   - **StatusMessage:** `"Waiting for lawyer review"`

   The job is **Suspended** here and resumes when the lawyer clicks Approve or Reject in Action Center. `reviewComment` is filled from the form's `comment` field through the Out mapping above.
7. **Assign**:
   - `out_ReviewDecision = taskAction`
   - `out_ReviewComment = If(reviewComment Is Nothing, "", reviewComment)`
8. **Log Message**: `"Review completed: " + taskAction`

**Action Center (manual):** the lawyer needs a user with Action Center access and permission on the folder. The robot account needs Actions (Create/Edit/View) and, if you use labels, Tags permissions.

---

## 6. GenerateReport.xaml (report, bucket upload, email reply)

**Arguments**

| Name | Direction | Type |
|---|---|---|
| `in_ReviewJson` | In | String (the agent's `review_json`) |
| `in_ReviewDecision` | In | String (`""` when no review) |
| `in_ReviewComment` | In | String |
| `in_DocumentName` | In | String |
| `in_SenderEmail` | In | String |
| `in_Subject` | In | String |
| `out_ReportBucketPath` | Out | String |

**Variables:** `reportPath` (String), `reportFileName` (String)

**Activities, in order**

1. **Log Message**:
   ```
   "GenerateReport for " + in_DocumentName + " (decision: " + If(String.IsNullOrEmpty(in_ReviewDecision), "none", in_ReviewDecision) + ")"
   ```
2. **Invoke Workflow File**: `BuildReport.cs` → **Import Arguments**:
   - `agentJson` = `in_ReviewJson`
   - `reviewerDecision` = `in_ReviewDecision`
   - `reviewerComment` = `in_ReviewComment`
   - `documentName` = `in_DocumentName`
   - `reportPath` → `reportPath`
   - `reportFileName` → `reportFileName`

   The DOCX is written to `%TEMP%\RegCheck\<document>_RegCheck_Raporu_<yyyyMMdd-HHmmss>.docx`.
3. **Assign** `out_ReportBucketPath = "reports/" + reportFileName`
4. **Upload Storage File** (System › Storage):
   - **Storage bucket name:** `"<BucketName>"`, the same bucket UploadDocstoSB writes to
   - **Orchestrator folder path:** the bucket's folder, or empty if it is in this process's folder
   - **Destination:** `out_ReportBucketPath`
   - **File:** `reportPath`
5. **Log Message**: `"Report uploaded to " + out_ReportBucketPath`
6. **Send the reply.** Maestro passes only strings, not the original mail object, so the "reply" is a new mail to the sender with a `Re:` subject. Use the same mailbox UploadDocstoSB reads from:
   - **Outlook** (simplest on your PC; Outlook desktop must be configured for the robot user): **Send Outlook Mail Message**
     - **To:** `in_SenderEmail`
     - **Subject:** `"Re: " + in_Subject + " | RegCheck raporu"`
     - **Body:** `"Merhaba," + Environment.NewLine + Environment.NewLine + "Gönderdiğiniz aydınlatma metni (" + in_DocumentName + ") için RegCheck uyum raporu ektedir." + Environment.NewLine + "Bu rapor otomatik üretilmiştir ve hukuki görüş değildir."`
     - **Attachments:** `{reportPath}`
     - **Account:** the mailbox address (if Outlook has several)
   - **Alternative, SMTP:** **Send SMTP Mail Message** with the same To/Subject/Body/Attachments plus Server/Port/Email/Password from **Orchestrator Assets** (Get Credential). Never type the password into the workflow.
7. **Log Message**: `"Reply sent to " + in_SenderEmail`

**Success and failure:** in Maestro there's no queue item to set. Each step ends **Successful** when it completes. Any exception, for example a bad agent JSON, a missing bucket, or a mail error, makes the job **Faulted** with the exception message, and Maestro shows it on the failed task. For the demo there are no retries.

---

## 7. Verify the coded workflows without Studio

A test harness in `orchestrator_tests/` (repository root) compiles these same `.cs` files against a 10-line stub of `UiPath.CodedWorkflows` and runs them:

```powershell
cd <repo>\orchestrator_tests
dotnet run -c Release -- <repo>
```

It checks:
- **DOCX extraction:** identical to the text the agent was tested with.
- **PDF extraction:** 99.7% word recall.
- Clear errors for `.doc`, unsupported types and missing files.
- `humanReviewRequired`: A false, B false, C true. It's still true for C when `human_review_required` is missing.
- The **real UiPath output** for A (bare object and full trace span, in `runs/uipath_real/`) parses the same, renders "bulgu yok", and maps `6698 md. 10/1-x` elements to their labels.
- Wrapped, double-encoded and fenced JSON are accepted.
- **Reports:** schema-valid DOCX, a "Reviewed by lawyer" section only when a decision was passed, and all cited URLs as clickable links.

Outputs are written to `orchestrator_tests\out\`.

## 8. Manual steps in UiPath (summary)

1. **Studio:** reload the project, then create and set entry points `HumanReview.xaml` and `GenerateReport.xaml` (sections 5–6). In UploadDocstoSB, add the outputs and ExtractDocumentText (section 3). Publish both projects.
2. **Orchestrator:**
   - Create processes **HumanReview** and **GenerateReport** (one package, two entry points) and upgrade UploadDocstoSB.
   - Make sure your PC robot (unattended) is assigned to the folder.
   - The storage bucket exists and has a `reports/` prefix; it's created on first upload.
3. **Agent Builder:** nothing to change for field names. The current ReviewAgent output already matches `agent/output_schema.json`.
4. **Maestro (Studio Web):** create variables (section 1), map inputs and outputs per task, set the gateway condition and default flow (section 4), then Debug with document C (review path) and B (no-review path).
5. **Action Center:** give the lawyer user access; review the task in Action Center → Actions.
