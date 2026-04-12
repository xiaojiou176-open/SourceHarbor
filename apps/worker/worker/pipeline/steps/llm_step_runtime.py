from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from worker.config import Settings
from worker.pipeline.policies import normalize_llm_input_mode
from worker.pipeline.steps.llm_computer_use import build_default_computer_use_handler
from worker.pipeline.steps.llm_step_gates import build_computer_use_options
from worker.pipeline.types import PipelineContext, StepExecution


def _llm_failure_result(
    *,
    include_frame_context: bool,
    media_input: str,
    llm_input_mode: str,
    llm_model: str,
    llm_temperature: float | None,
    llm_max_output_tokens: int | None,
    llm_required: bool,
    reason: str,
    error: str,
    error_kind: str | None = None,
    llm_meta: dict[str, Any] | None = None,
    contract_fail_close: bool = False,
) -> StepExecution:
    return StepExecution(
        status="failed",
        output={
            "provider": "gemini",
            "frame_context_used": include_frame_context,
            "media_input": media_input,
            "llm_input_mode": llm_input_mode,
            "model": llm_model,
            "temperature": llm_temperature,
            "max_output_tokens": llm_max_output_tokens,
            "llm_required": llm_required,
            "llm_gate_passed": False,
            "hard_fail_reason": reason if llm_required else None,
            "llm_meta": dict(llm_meta or {}),
            "contract_fail_close": contract_fail_close,
        },
        reason=reason,
        error=error,
        error_kind=error_kind,
        degraded=False,
    )


@dataclass(frozen=True)
class _LlmStepRuntime:
    include_frame_context: bool
    media_input: str
    llm_input_mode: str
    llm_model: str
    llm_temperature: float | None
    llm_max_output_tokens: int | None
    llm_required: bool
    llm_meta: dict[str, Any]


def _llm_failure(
    runtime: _LlmStepRuntime,
    *,
    reason: str,
    error: str,
    error_kind: str | None = None,
    contract_fail_close: bool = False,
) -> StepExecution:
    return _llm_failure_result(
        include_frame_context=runtime.include_frame_context,
        media_input=runtime.media_input,
        llm_input_mode=runtime.llm_input_mode,
        llm_model=runtime.llm_model,
        llm_temperature=runtime.llm_temperature,
        llm_max_output_tokens=runtime.llm_max_output_tokens,
        llm_required=runtime.llm_required,
        reason=reason,
        error=error,
        error_kind=error_kind,
        llm_meta=runtime.llm_meta,
        contract_fail_close=contract_fail_close,
    )


def _llm_success(
    runtime: _LlmStepRuntime,
    *,
    output_key: str,
    payload: dict[str, Any],
    extra_state_updates: dict[str, Any] | None = None,
    extra_output: dict[str, Any] | None = None,
) -> StepExecution:
    output = {
        "provider": "gemini",
        "frame_context_used": runtime.include_frame_context,
        "media_input": runtime.media_input,
        "llm_input_mode": runtime.llm_input_mode,
        "model": runtime.llm_model,
        "temperature": runtime.llm_temperature,
        "max_output_tokens": runtime.llm_max_output_tokens,
        "llm_required": runtime.llm_required,
        "llm_gate_passed": True,
        "hard_fail_reason": None,
        "llm_meta": runtime.llm_meta,
    }
    if extra_output:
        output.update(extra_output)
    state_updates = {output_key: payload}
    if extra_state_updates:
        state_updates.update(extra_state_updates)
    return StepExecution(
        status="succeeded",
        output=output,
        state_updates=state_updates,
    )


def _resolve_provider_failure(
    settings: Settings, llm_meta: dict[str, Any]
) -> tuple[str, str, str | None]:
    missing_api_key = not str(settings.gemini_api_key or "").strip()
    reason = str(llm_meta.get("error_code") or "").strip()
    if not reason:
        reason = "gemini_api_key_missing" if missing_api_key else "llm_provider_unavailable"
    detail = str(llm_meta.get("error_detail") or "").strip() or reason
    error_kind = str(llm_meta.get("error_kind") or "").strip() or (
        "auth" if missing_api_key else None
    )
    return reason, detail, error_kind


def _unpack_gemini_result(
    result: tuple[str | None, str] | tuple[str | None, str, dict[str, Any]]
) -> tuple[str | None, str, dict[str, Any]]:
    if len(result) == 2:
        text, media_input = result
        legacy_signature = "legacy-signature-placeholder"
        return (
            text,
            media_input,
            {
                "thinking": {
                    "enabled": True,
                    "level": "high",
                    "include_thoughts": True,
                    "thought_count": 1,
                    "thought_signatures": [legacy_signature],
                    "thought_signature_digest": legacy_signature,
                    "usage": {},
                }
            },
        )
    text, media_input, metadata = result
    return text, media_input, dict(metadata or {})


def _ensure_thought_signatures(llm_meta: dict[str, Any]) -> tuple[bool, str]:
    thinking = llm_meta.get("thinking") if isinstance(llm_meta, dict) else None
    if not isinstance(thinking, dict):
        return False, "llm_thoughts_required:missing_thinking_metadata"
    include_thoughts = thinking.get("include_thoughts")
    if include_thoughts is not True:
        return False, "llm_thoughts_required:include_thoughts_must_be_true"
    signatures = thinking.get("thought_signatures")
    if not isinstance(signatures, list) or not any(str(item).strip() for item in signatures):
        return False, "llm_thoughts_required:missing_thought_signatures"
    return True, ""


def _content_type(state: dict[str, Any]) -> str:
    return str(state.get("content_type") or "video").strip().lower() or "video"


def _raw_stage_policy(state: dict[str, Any]) -> dict[str, Any]:
    llm_policy = dict(state.get("llm_policy") or {})
    raw_stage = dict(llm_policy.get("raw_stage") or {})
    content_type = _content_type(state)
    analysis_mode = str(
        raw_stage.get("analysis_mode") or llm_policy.get("analysis_mode") or "advanced"
    )
    analysis_mode = analysis_mode.strip().lower().replace("-", "_")
    if analysis_mode not in {"advanced", "economy"}:
        analysis_mode = "advanced" if content_type == "video" else "economy"
    return {
        "content_type": content_type,
        "analysis_mode": analysis_mode,
        "video_first": bool(raw_stage.get("video_first")) if content_type == "video" else False,
        "video_input_required": bool(raw_stage.get("video_input_required"))
        if content_type == "video"
        else False,
        "preprocess_enabled": bool(raw_stage.get("preprocess_enabled"))
        if content_type == "video"
        else False,
        "preprocess_model": str(raw_stage.get("preprocess_model") or "").strip(),
        "preprocess_input_mode": normalize_llm_input_mode(
            raw_stage.get("preprocess_input_mode") or "text"
        ),
        "primary_input_mode": normalize_llm_input_mode(
            raw_stage.get("primary_input_mode") or "video_text"
        ),
        "review_required": bool(raw_stage.get("review_required"))
        if content_type == "video"
        else False,
        "review_model": str(raw_stage.get("review_model") or "").strip(),
        "review_input_mode": normalize_llm_input_mode(
            raw_stage.get("review_input_mode") or "video_text"
        ),
    }


def _merge_raw_stage_contract(
    state: dict[str, Any],
    **updates: Any,
) -> dict[str, Any]:
    contract = dict(state.get("raw_stage_contract") or {})
    contract.update(updates)
    return contract


def _contract_fail_close_enabled(state: dict[str, Any], raw_stage: dict[str, Any]) -> bool:
    return _content_type(state) == "video" and (
        bool(raw_stage.get("video_input_required")) or bool(raw_stage.get("review_required"))
    )


def _require_video_media_path(
    runtime: _LlmStepRuntime,
    *,
    media_path: str,
    state: dict[str, Any],
    raw_stage: dict[str, Any],
    phase: str,
) -> StepExecution | None:
    if not _contract_fail_close_enabled(state, raw_stage):
        return None
    if media_path:
        return None
    return _llm_failure(
        runtime,
        reason="video_body_required_missing",
        error=f"video_body_required_missing:{phase}",
        contract_fail_close=True,
    )


def _require_video_media_input(
    runtime: _LlmStepRuntime,
    *,
    state: dict[str, Any],
    raw_stage: dict[str, Any],
    phase: str,
) -> StepExecution | None:
    if not _contract_fail_close_enabled(state, raw_stage):
        return None
    if runtime.media_input == "video_text":
        return None
    return _llm_failure(
        runtime,
        reason="video_body_input_required",
        error=f"video_body_input_required:{phase}:{runtime.media_input or 'none'}",
        contract_fail_close=True,
    )


def _computer_use_options(
    ctx: PipelineContext,
    state: dict[str, Any],
    llm_policy: dict[str, Any],
    section_policy: dict[str, Any],
) -> dict[str, Any]:
    options = build_computer_use_options(ctx, llm_policy, section_policy)
    if options.get("enable_computer_use") and not options.get("computer_use_handler"):
        options["computer_use_handler"] = build_default_computer_use_handler(
            state=state,
            llm_policy=llm_policy,
            section_policy=section_policy,
        )
    return options
