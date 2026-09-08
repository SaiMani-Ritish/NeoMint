from neomint_mcp.session import RiskLevel, execute_plan, plan_request


def test_recent_pdf_search_is_read_only() -> None:
    plan = plan_request("find recent PDFs")
    assert plan.needs_confirmation is False
    assert plan.actions[0].tool == "files.search_recent_pdfs"
    assert plan.actions[0].risk is RiskLevel.READ_ONLY


def test_application_launch_requires_confirmation() -> None:
    plan = plan_request("open firefox")
    assert plan.needs_confirmation is True
    assert plan.actions[0].tool == "applications.launch"
    assert plan.actions[0].risk is RiskLevel.REVERSIBLE


def test_clipboard_replacement_requires_confirmation() -> None:
    plan = plan_request("copy local only")
    assert plan.needs_confirmation is True
    assert plan.actions[0].tool == "clipboard.copy"


def test_unknown_request_is_not_executed() -> None:
    plan = plan_request("remove every file from my home directory")
    assert plan.clarification is not None
    assert plan.actions == []
    event = execute_plan(plan)
    assert event.event == "clarification"
