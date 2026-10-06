"""Core agentic loop for NeoMint.

Orchestrates the full flow:
  User request → model inference → parse → policy validation →
  approval gate → tool execution → audit logging → response.

The loop enforces step limits, timeout budgets, and graceful
recovery on any failure.
"""

from __future__ import annotations

import logging
from time import perf_counter
from typing import Any

from neomint_agent.audit import AuditLogger
from neomint_agent.config import MAX_LOOP_STEPS
from neomint_agent.model_adapter import (
    OllamaAdapter,
    OllamaConnectionError,
    OllamaModelError,
    OllamaTimeoutError,
)
from neomint_agent.parser import parse_model_output
from neomint_agent.policy import validate_plan
from neomint_agent.schemas import (
    AgentResponse,
    Clarification,
    Plan,
    PolicyViolation,
    Refusal,
    ToolResult,
    ValidatedPlan,
)
from neomint_agent.tool_executor import ToolExecutor

logger = logging.getLogger("neomint-agent.loop")


class AgentLoop:
    """The core NeoMint agent loop.

    Manages the lifecycle of a user request through model inference,
    plan validation, approval, and execution.

    Args:
        model: Ollama adapter for model inference.
        executor: Tool executor for MCP tool calls.
        audit: Audit logger for event persistence.
    """

    def __init__(
        self,
        model: OllamaAdapter | None = None,
        executor: ToolExecutor | None = None,
        audit: AuditLogger | None = None,
    ) -> None:
        self.model = model or OllamaAdapter()
        self.executor = executor or ToolExecutor()
        self.audit = audit or AuditLogger()
        self._pending_plans: dict[str, ValidatedPlan] = {}
        self._pending_requests: dict[str, str] = {}

    async def process_request(self, request: str) -> AgentResponse:
        """Process a user request through the full agent pipeline.

        This is the main entry point. It sends the request to the model,
        parses the response, validates against the policy engine, and
        either returns a plan for approval or executes it directly.

        Args:
            request: The user's natural language request.

        Returns:
            AgentResponse with the current status and any results.
        """
        start = perf_counter()
        request = request.strip()

        if not request:
            return AgentResponse(
                status="error",
                message="Empty request. Please describe what you'd like to do.",
            )

        # Step 1: Call the model
        try:
            model_response = await self.model.generate(request)
        except OllamaConnectionError as exc:
            self.audit.log(
                "error",
                request=request,
                message=str(exc),
            )
            return AgentResponse(
                status="error",
                message=(
                    "Cannot connect to Ollama. Make sure Ollama is running: "
                    "sudo systemctl start ollama"
                ),
            )
        except OllamaModelError as exc:
            self.audit.log(
                "error",
                request=request,
                message=str(exc),
            )
            return AgentResponse(
                status="error",
                message=str(exc),
            )
        except OllamaTimeoutError as exc:
            self.audit.log(
                "error",
                request=request,
                message=str(exc),
            )
            return AgentResponse(
                status="error",
                message=(
                    "Model inference timed out. The system may be under heavy load. "
                    "Try again in a moment."
                ),
            )

        # Step 2: Parse model output
        parsed = parse_model_output(model_response.text)
        model_duration_ms = model_response.total_duration_ms

        # Step 3: Handle clarification
        if isinstance(parsed, Clarification):
            self.audit.log(
                "clarification",
                request=request,
                message=parsed.question,
                duration_ms=model_duration_ms,
                metadata={"reason": parsed.reason},
            )
            return AgentResponse(
                status="clarification",
                message=parsed.question,
                clarification=parsed,
            )

        # Step 4: Handle refusal
        if isinstance(parsed, Refusal):
            self.audit.log(
                "refusal",
                request=request,
                message=parsed.message,
                duration_ms=model_duration_ms,
            )
            return AgentResponse(
                status="refusal",
                message=parsed.message,
                refusal=parsed,
            )

        # Step 5: Validate plan against policy engine
        assert isinstance(parsed, Plan)

        validation_result = validate_plan(parsed)

        if isinstance(validation_result, PolicyViolation):
            self.audit.log(
                "plan_rejected_by_policy",
                request=request,
                violations=validation_result.violations,
                message=validation_result.message,
                actions=[a.model_dump() for a in parsed.actions],
                duration_ms=model_duration_ms,
            )
            return AgentResponse(
                status="policy_violation",
                message=validation_result.message,
            )

        # Step 6: Plan is valid
        validated_plan = validation_result

        self.audit.log(
            "plan_generated",
            request=request,
            plan_hash=validated_plan.plan_hash,
            actions=[a.model_dump() for a in validated_plan.actions],
            message=validated_plan.user_facing_summary,
            duration_ms=model_duration_ms,
        )

        # Step 7: Check if approval is needed
        if validated_plan.needs_approval:
            self._pending_plans[validated_plan.plan_hash] = validated_plan
            self._pending_requests[validated_plan.plan_hash] = request

            return AgentResponse(
                status="plan_proposed",
                message=validated_plan.user_facing_summary,
                plan=validated_plan,
            )

        # Step 8: Execute immediately (read-only plan)
        return await self._execute_plan(validated_plan, request)

    async def approve_plan(self, plan_hash: str) -> AgentResponse:
        """Approve and execute a pending plan.

        Args:
            plan_hash: The hash of the plan to approve (from plan_proposed response).

        Returns:
            AgentResponse with execution results.
        """
        validated_plan = self._pending_plans.pop(plan_hash, None)
        request = self._pending_requests.pop(plan_hash, "")

        if validated_plan is None:
            return AgentResponse(
                status="error",
                message=(
                    f"No pending plan with hash '{plan_hash}'. "
                    "It may have expired or been cancelled."
                ),
            )

        self.audit.log(
            "plan_approved",
            request=request,
            plan_hash=plan_hash,
            actions=[a.model_dump() for a in validated_plan.actions],
        )

        return await self._execute_plan(validated_plan, request)

    async def cancel_plan(self, plan_hash: str) -> AgentResponse:
        """Cancel a pending plan.

        Args:
            plan_hash: The hash of the plan to cancel.

        Returns:
            AgentResponse confirming cancellation.
        """
        validated_plan = self._pending_plans.pop(plan_hash, None)
        request = self._pending_requests.pop(plan_hash, "")

        if validated_plan is None:
            return AgentResponse(
                status="error",
                message=f"No pending plan with hash '{plan_hash}'.",
            )

        self.audit.log(
            "plan_denied",
            request=request,
            plan_hash=plan_hash,
            actions=[a.model_dump() for a in validated_plan.actions],
        )

        return AgentResponse(
            status="plan_denied",
            message="Plan cancelled.",
        )

    async def _execute_plan(
        self,
        plan: ValidatedPlan,
        request: str,
    ) -> AgentResponse:
        """Execute a validated and approved plan.

        Runs each action sequentially. If any action fails, the loop
        stops and reports the failure (no silent continuation).

        Args:
            plan: The validated plan to execute.
            request: The original user request (for audit logging).

        Returns:
            AgentResponse with all tool results.
        """
        start = perf_counter()
        results: list[ToolResult] = []

        for i, action in enumerate(plan.actions, start=1):
            logger.info(
                "Executing action %d/%d: %s",
                i, len(plan.actions), action.tool,
            )

            result = await self.executor.execute(action.tool, action.arguments)
            results.append(result)

            # Log each action execution
            self.audit.log(
                "action_executed" if result.success else "action_failed",
                request=request,
                plan_hash=plan.plan_hash,
                actions=[action.model_dump()],
                results=[result.model_dump()],
                duration_ms=result.duration_ms,
            )

            # Stop on failure — graceful recovery, not silent continuation
            if not result.success:
                total_duration_ms = (perf_counter() - start) * 1000
                self.audit.log(
                    "plan_executed",
                    request=request,
                    plan_hash=plan.plan_hash,
                    message=f"Plan stopped at action {i}/{len(plan.actions)} due to failure",
                    duration_ms=total_duration_ms,
                    results=[r.model_dump() for r in results],
                )
                return AgentResponse(
                    status="error",
                    message=(
                        f"Action {i} ({action.tool}) failed: {result.error}. "
                        f"Remaining actions were not executed."
                    ),
                    plan=plan,
                    results=results,
                )

        total_duration_ms = (perf_counter() - start) * 1000

        self.audit.log(
            "plan_executed",
            request=request,
            plan_hash=plan.plan_hash,
            message=f"All {len(results)} actions completed successfully",
            duration_ms=total_duration_ms,
            results=[r.model_dump() for r in results],
        )

        return AgentResponse(
            status="plan_executed",
            message=f"Completed: {plan.user_facing_summary}",
            plan=plan,
            results=results,
        )

    @property
    def pending_plan_count(self) -> int:
        """Number of plans awaiting user approval."""
        return len(self._pending_plans)

    def get_pending_plans(self) -> dict[str, ValidatedPlan]:
        """Return all pending plans."""
        return dict(self._pending_plans)

    async def close(self) -> None:
        """Clean up resources."""
        await self.model.close()
