# Maestro process

The Studio Web export of the RegCheck Maestro (BPMN) process goes here.

Export it from Studio Web (**Export** on the solution) and place the exported files in this folder.
The process orchestrates `UploadDocstoSB` → `ReviewAgent` → `HumanReview` (if needed) → `GenerateReport`;
see `../RegCheck_Orchestrator/BUILD_GUIDE.md` for the data contract between the steps.
