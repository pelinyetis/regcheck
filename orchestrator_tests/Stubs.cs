// Minimal stand-ins for what Studio provides, so the coded workflows compile outside Studio.
// In Studio, CodedWorkflow and [Workflow] come from UiPath.CodedWorkflows.
namespace UiPath.CodedWorkflows
{
    [System.AttributeUsage(System.AttributeTargets.Method)]
    public sealed class WorkflowAttribute : System.Attribute { }
}

namespace RegCheck_Orchestrator
{
    public partial class CodedWorkflow { }
}
