from reporter import Reporter, LogLevel, PrintTarget

reporter = Reporter("workflow.log", PrintTarget.BOTH)

reporter.addStep(
    moduleName="ParseN8N",
    stepName="parse",    
    isSuccess=True
)

reporter.addStep(
    moduleName="TransformWorkflow",
    stepName="parse",
    isSuccess=False,
    errorText="Unsupported Node"
)
