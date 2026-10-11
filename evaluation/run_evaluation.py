#!/usr/bin/env python3
"""今日宜食固定评测集运行器。

仅使用 Python 标准库。启动 Spring Boot 后运行本脚本，它会调用公开 HTTP API、
拉取 Trace、写入 Gold Label，并生成 JSON/CSV/Markdown 报告。
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import statistics
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterable


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


ROOT = Path(__file__).resolve().parent
SLOT_NAMES = (
    "mealTime",
    "mood",
    "scene",
    "healthGoal",
    "cuisine",
    "taste",
    "convenience",
)
INTENTS = {
    "MEAL_RECOMMENDATION",
    "CLARIFY_NEEDED",
    "MEAL_ADJUST",
    "MEAL_PLAN",
    "HEALTH_RISK",
    "OTHER",
}
CLARIFY_ACTIONS = {"ASK", "READY"}
FAULT_AGENT_BY_NAME = {
    "INTENT_AGENT_ERROR": "IntentAgent",
    "CLARIFY_AGENT_ERROR": "ClarifyAgent",
    "RECOMMEND_AGENT_ERROR": "RecommendResponseAgent",
}
JUDGE_FAULT = "EVALUATION_JUDGE_ERROR"


class ApiError(RuntimeError):
    pass


class DietApi:
    def __init__(self, base_url: str, user_id: int, timeout: float) -> None:
        self.base_url = base_url.rstrip("/")
        self.user_id = user_id
        self.timeout = timeout

    def request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> Any:
        body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json; charset=utf-8",
            "X-User-Id": str(self.user_id),
        }
        if extra_headers:
            headers.update(extra_headers)
        request = urllib.request.Request(
            self.base_url + path,
            data=body,
            headers=headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
                return None if not raw.strip() else json.loads(raw)
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            raise ApiError(f"HTTP {error.code} {method} {path}: {detail}") from error
        except urllib.error.URLError as error:
            raise ApiError(f"无法连接 {self.base_url}: {error.reason}") from error

    def slot_options(self) -> dict[str, list[str]]:
        return self.request("GET", "/slot-options")

    def public_meals(self) -> list[dict[str, Any]]:
        return self.request("GET", "/meals/public")

    def chat(self, session_id: str, message: str, source_mode: str, fault: str | None = None) -> dict[str, Any]:
        headers = {"X-Evaluation-Fault": fault} if fault else None
        return self.request(
            "POST",
            "/chat",
            {
                "sessionId": session_id,
                "message": message,
                "sourceMode": source_mode,
                "context": {"evaluation": True},
            },
            headers,
        )

    def trace(self, trace_id: str) -> dict[str, Any]:
        return self.request("GET", "/debug/traces/" + urllib.parse.quote(trace_id, safe=""))

    def label_trace(self, trace_id: str, turn: dict[str, Any]) -> None:
        self.request(
            "PUT",
            "/debug/traces/" + urllib.parse.quote(trace_id, safe="") + "/label",
            {
                "expectedIntent": turn.get("expectedIntent"),
                "expectedSlots": normalize_slots(turn.get("expectedSlots")),
                "expectedClarifyAction": turn.get("expectedClarifyAction"),
                "labelNote": "evaluation/ benchmark gold label",
            },
        )

    def evaluate_with_fault(self, start_at: datetime, end_at: datetime, limit: int) -> dict[str, Any]:
        return self.request(
            "POST",
            "/evaluations",
            {
                "startAt": start_at.isoformat(timespec="seconds"),
                "endAt": end_at.isoformat(timespec="seconds"),
                "includeLlmJudge": True,
                "limit": limit,
            },
            {"X-Evaluation-Fault": "EVALUATION_JUDGE_ERROR"},
        )


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            try:
                row = json.loads(stripped)
            except json.JSONDecodeError as error:
                raise ValueError(f"{path}:{line_number} JSON 格式错误: {error}") from error
            row["_line"] = line_number
            rows.append(row)
    return rows


def dataset_stats(cases: list[dict[str, Any]]) -> dict[str, Any]:
    multi_turn = [case for case in cases if len(case.get("turns", [])) > 1]
    multi_turn_counts = [len(case["turns"]) for case in multi_turn]
    total_turns = sum(len(case.get("turns", [])) for case in cases)
    return {
        "sessionCount": len(cases),
        "turnCount": total_turns,
        "multiTurnSessionCount": len(multi_turn),
        "multiTurnTurnCount": sum(multi_turn_counts),
        "multiTurnMinTurns": min(multi_turn_counts) if multi_turn_counts else 0,
        "multiTurnMaxTurns": max(multi_turn_counts) if multi_turn_counts else 0,
        "multiTurnAverageTurns": round(statistics.fmean(multi_turn_counts), 2) if multi_turn_counts else 0.0,
        "categorySessionCounts": dict(sorted(Counter(case.get("category", "UNKNOWN") for case in cases).items())),
    }


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def value_sha256(value: Any) -> str:
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def normalize_slots(value: Any) -> dict[str, list[str]]:
    value = value if isinstance(value, dict) else {}
    normalized: dict[str, list[str]] = {}
    for name in SLOT_NAMES:
        raw = value.get(name, [])
        if isinstance(raw, str):
            raw = [raw]
        normalized[name] = list(dict.fromkeys(str(item).strip() for item in raw if str(item).strip()))
    return normalized


def validate_cases(
    cases: list[dict[str, Any]],
    slot_options: dict[str, list[str]] | None,
) -> list[str]:
    errors: list[str] = []
    seen_ids: set[str] = set()
    valid_options = {name: set(values) for name, values in (slot_options or {}).items()}
    for case in cases:
        location = f"line {case.get('_line', '?')}"
        case_id = case.get("caseId")
        if not isinstance(case_id, str) or not case_id.strip():
            errors.append(f"{location}: caseId 缺失")
        elif case_id in seen_ids:
            errors.append(f"{location}: caseId 重复: {case_id}")
        else:
            seen_ids.add(case_id)
        if case.get("sourceMode") not in {"PUBLIC", "PERSONAL"}:
            errors.append(f"{case_id}: sourceMode 必须是 PUBLIC/PERSONAL")
        turns = case.get("turns")
        if not isinstance(turns, list) or not turns:
            errors.append(f"{case_id}: turns 不能为空")
            continue
        for index, turn in enumerate(turns, 1):
            prefix = f"{case_id} turn {index}"
            if not isinstance(turn.get("message"), str) or not turn["message"].strip():
                errors.append(f"{prefix}: message 不能为空")
            if turn.get("expectedIntent") not in INTENTS:
                errors.append(f"{prefix}: expectedIntent 非法")
            action = turn.get("expectedClarifyAction")
            if action is not None and action not in CLARIFY_ACTIONS:
                errors.append(f"{prefix}: expectedClarifyAction 非法")
            slots = normalize_slots(turn.get("expectedSlots"))
            if slot_options:
                for name, values in slots.items():
                    for value in values:
                        if value not in valid_options.get(name, set()):
                            errors.append(f"{prefix}: {name} 包含字典外标签 {value}")
    return errors


def validate_dataset_design(cases: list[dict[str, Any]], config: dict[str, Any]) -> list[str]:
    expected = config.get("datasetDesign")
    if not isinstance(expected, dict):
        return []
    actual = dataset_stats(cases)
    errors: list[str] = []
    for key in ("sessionCount", "turnCount", "multiTurnSessionCount"):
        if expected.get(key) is not None and actual.get(key) != expected.get(key):
            errors.append(f"固定评测集 {key} 应为 {expected[key]}，实际为 {actual.get(key)}")
    expected_turns = expected.get("turnsPerMultiTurnSession")
    if expected_turns is not None and (
        actual["multiTurnMinTurns"] != expected_turns
        or actual["multiTurnMaxTurns"] != expected_turns
    ):
        errors.append(
            f"固定评测集每组多轮会话应为 {expected_turns} 轮，实际范围为 "
            f"{actual['multiTurnMinTurns']}–{actual['multiTurnMaxTurns']}"
        )
    return errors


def validate_fault_specs(specs: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    seen_faults: set[str] = set()
    for spec in specs:
        location = f"fault file line {spec.get('_line', '?')}"
        fault = spec.get("fault")
        endpoint = spec.get("endpoint", "CHAT")
        if fault in seen_faults:
            errors.append(f"{location}: fault 重复: {fault}")
        elif isinstance(fault, str):
            seen_faults.add(fault)
        if endpoint == "CHAT":
            expected_agent = FAULT_AGENT_BY_NAME.get(fault)
            if expected_agent is None:
                errors.append(f"{location}: 不支持的 CHAT fault: {fault}")
            if spec.get("expectedAgent") != expected_agent:
                errors.append(f"{location}: expectedAgent 应为 {expected_agent}")
            if not isinstance(spec.get("message"), str) or not spec["message"].strip():
                errors.append(f"{location}: CHAT fault 缺少 message")
            if spec.get("sourceMode") not in {"PUBLIC", "PERSONAL"}:
                errors.append(f"{location}: sourceMode 必须是 PUBLIC/PERSONAL")
        elif endpoint == "EVALUATION":
            if fault != JUDGE_FAULT:
                errors.append(f"{location}: EVALUATION endpoint 仅支持 {JUDGE_FAULT}")
        else:
            errors.append(f"{location}: endpoint 必须是 CHAT/EVALUATION")
        repeat = spec.get("repeat", 1)
        if isinstance(repeat, bool) or not isinstance(repeat, int) or repeat < 1:
            errors.append(f"{location}: repeat 必须是正整数")
    return errors


def parse_json_value(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return value
    if not isinstance(value, str) or not value.strip():
        return {}
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return {}


def event_payload(events: list[dict[str, Any]], event_type: str, key: str = "outputPayload") -> dict[str, Any]:
    for event in reversed(events):
        if event.get("eventType") == event_type:
            parsed = parse_json_value(event.get(key))
            return parsed if isinstance(parsed, dict) else {}
    return {}


def event_exists(events: list[dict[str, Any]], event_type: str) -> bool:
    return any(event.get("eventType") == event_type for event in events)


def event_raw_payload(
    events: list[dict[str, Any]],
    event_type: str,
    key: str = "outputPayload",
) -> Any:
    for event in reversed(events):
        if event.get("eventType") == event_type:
            return event.get(key)
    return None


def extract_clarify_action(events: list[dict[str, Any]]) -> str | None:
    payload = event_raw_payload(events, "CLARIFY_DECISION")
    parsed = parse_json_value(payload)
    if isinstance(parsed, dict) and parsed.get("action") in CLARIFY_ACTIONS:
        return parsed["action"]
    if isinstance(payload, str):
        match = re.search(r"\baction=(ASK|READY)\b", payload)
        return match.group(1) if match else None
    return None


def extract_ranked_ids(events: list[dict[str, Any]]) -> list[int]:
    payload = event_raw_payload(events, "MEAL_RANKED")
    parsed = parse_json_value(payload)
    ranked = parsed.get("ranked", []) if isinstance(parsed, dict) else []
    if isinstance(ranked, list):
        ids = [
            item.get("id")
            for item in ranked
            if isinstance(item, dict) and isinstance(item.get("id"), int)
        ]
        if ids:
            return list(dict.fromkeys(ids))
    if isinstance(payload, str):
        return list(dict.fromkeys(int(value) for value in re.findall(r"MealItem\(id=(\d+)", payload)))
    return []


def parse_model_json(value: Any) -> dict[str, Any] | None:
    parsed = parse_json_value(value)
    if isinstance(parsed, dict) and parsed:
        return parsed
    if not isinstance(value, str):
        return None
    start = value.find("{")
    end = value.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        candidate = json.loads(value[start:end + 1])
        return candidate if isinstance(candidate, dict) else None
    except json.JSONDecodeError:
        return None


def extract_raw_recommendation(events: list[dict[str, Any]]) -> dict[str, Any]:
    call = next((
        event for event in reversed(events)
        if event.get("eventType") == "AGENT_CALL"
        and event.get("agentName") == "RecommendResponseAgent"
    ), None)
    if call is None:
        return {"callPresent": False, "parseable": False, "ids": []}
    parsed = parse_model_json(call.get("outputPayload"))
    if not isinstance(parsed, dict) or not isinstance(parsed.get("recommendations"), list):
        return {"callPresent": True, "parseable": False, "ids": []}
    ids: list[int] = []
    for item in parsed["recommendations"]:
        if not isinstance(item, dict):
            continue
        value = item.get("mealId", item.get("itemId"))
        if isinstance(value, int) and not isinstance(value, bool):
            ids.append(value)
        elif isinstance(value, str) and value.isdigit():
            ids.append(int(value))
    return {"callPresent": True, "parseable": True, "ids": list(dict.fromkeys(ids))}


def extract_trace(trace_row: dict[str, Any]) -> dict[str, Any]:
    root = parse_json_value(trace_row.get("traceJson"))
    events = root.get("events", []) if isinstance(root, dict) else []
    raw_intent_payload = event_payload(events, "INTENT_RECOGNIZED")
    final_intent_payload = event_payload(events, "INTENT_REVISED")
    merged_slots_payload = event_payload(events, "SLOTS_MERGED")
    adjust_payload = event_payload(events, "ADJUST_CONTEXT_RESOLVED")
    plan_payload = event_payload(events, "PLAN_CONTEXT_RESOLVED")
    response_payload = event_payload(events, "RESPONSE_READY")

    raw_slots = normalize_slots(raw_intent_payload.get("slots"))
    final_slots_source = (
        merged_slots_payload
        or adjust_payload.get("mergedSlots")
        or plan_payload
        or final_intent_payload.get("slots")
        or raw_slots
    )
    final_slots = normalize_slots(final_slots_source)
    agent_calls = [event for event in events if event.get("eventType") == "AGENT_CALL"]
    token_values = [event.get("totalTokens") for event in agent_calls]
    token_complete = bool(agent_calls) and all(isinstance(value, (int, float)) for value in token_values)
    total_tokens = int(sum(token_values)) if token_complete else None
    input_tokens = (
        int(sum(event.get("inputTokens", 0) for event in agent_calls)) if token_complete else None
    )
    output_tokens = (
        int(sum(event.get("outputTokens", 0) for event in agent_calls)) if token_complete else None
    )
    error_events = [event for event in events if event.get("errorMessage")]
    response_blocks = response_payload.get("displayBlocks", [])
    response_blocks = response_blocks if isinstance(response_blocks, list) else []
    ranked_ids = extract_ranked_ids(events)
    candidate_whitelist_ids = ranked_ids[:3]
    response_ids = [item.get("id") for item in response_blocks if isinstance(item, dict) and isinstance(item.get("id"), int)]
    ranked_trace_present = event_exists(events, "MEAL_RANKED")
    raw_recommendation = extract_raw_recommendation(events)
    raw_recommendation_ids = raw_recommendation["ids"]
    raw_out_of_whitelist_ids = [
        item_id for item_id in raw_recommendation_ids
        if item_id not in candidate_whitelist_ids
    ]
    final_whitelist_passed = set(response_ids).issubset(set(candidate_whitelist_ids))
    return {
        "status": trace_row.get("status"),
        "durationMs": trace_row.get("durationMs"),
        "eventCount": trace_row.get("eventCount"),
        "events": events,
        "rawIntent": raw_intent_payload.get("intent"),
        "finalIntent": final_intent_payload.get("intent") or raw_intent_payload.get("intent"),
        "rawSlots": raw_slots,
        "finalSlots": final_slots,
        "clarifyAction": extract_clarify_action(events),
        "rankedIds": ranked_ids,
        "candidateWhitelistIds": candidate_whitelist_ids,
        "rankedTracePresent": ranked_trace_present,
        "rawRecommendationCallPresent": raw_recommendation["callPresent"],
        "rawRecommendationParseable": raw_recommendation["parseable"],
        "rawRecommendationIds": raw_recommendation_ids,
        "rawOutOfWhitelistIds": raw_out_of_whitelist_ids,
        "rawWhitelistPassed": not raw_out_of_whitelist_ids if raw_recommendation["parseable"] else None,
        "responseIds": response_ids,
        "totalTokens": total_tokens,
        "inputTokens": input_tokens,
        "outputTokens": output_tokens,
        "tokenComplete": token_complete,
        "agentCallCount": len(agent_calls),
        "fallbackUsed": bool(error_events) or trace_row.get("status") == "FAILED",
        "errorEvents": error_events,
        "responseReady": event_exists(events, "RESPONSE_READY"),
        "requestFinished": event_exists(events, "REQUEST_FINISHED"),
        "traceComplete": all(
            event_exists(events, name)
            for name in ("REQUEST_RECEIVED", "USER_MESSAGE_RECORDED", "RESPONSE_READY", "REQUEST_FINISHED")
        ),
        "whitelistPassed": final_whitelist_passed,
        "rawViolationIntercepted": bool(raw_out_of_whitelist_ids) and final_whitelist_passed,
    }


def percentile(values: Iterable[float], quantile: float) -> float | None:
    ordered = sorted(float(value) for value in values if value is not None)
    if not ordered:
        return None
    index = max(0, math.ceil(quantile * len(ordered)) - 1)
    return ordered[index]


def describe(values: Iterable[float]) -> dict[str, float | int | None]:
    present = [float(value) for value in values if value is not None]
    if not present:
        return {"count": 0, "mean": None, "p50": None, "p95": None, "min": None, "max": None}
    return {
        "count": len(present),
        "mean": round(statistics.fmean(present), 2),
        "p50": round(percentile(present, 0.50) or 0.0, 2),
        "p95": round(percentile(present, 0.95) or 0.0, 2),
        "min": round(min(present), 2),
        "max": round(max(present), 2),
    }


def classification_metrics(rows: list[dict[str, Any]], prediction_key: str) -> dict[str, Any]:
    usable = [row for row in rows if row.get("expectedIntent") in INTENTS]
    if not usable:
        return {"count": 0, "correct": 0, "incorrect": 0, "accuracy": None, "accuracyCi95": None, "macroF1": None, "perClass": {}}
    expected_labels = sorted({row["expectedIntent"] for row in usable})
    correct = sum(row.get(prediction_key) == row["expectedIntent"] for row in usable)
    per_class: dict[str, Any] = {}
    f1_values: list[float] = []
    for label in expected_labels:
        tp = sum(row["expectedIntent"] == label and row.get(prediction_key) == label for row in usable)
        fp = sum(row["expectedIntent"] != label and row.get(prediction_key) == label for row in usable)
        fn = sum(row["expectedIntent"] == label and row.get(prediction_key) != label for row in usable)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        f1_values.append(f1)
        per_class[label] = {
            "support": sum(row["expectedIntent"] == label for row in usable),
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
        }
    return {
        "count": len(usable),
        "correct": correct,
        "incorrect": len(usable) - correct,
        "accuracy": round(correct / len(usable), 4),
        "accuracyCi95": wilson_interval(correct, len(usable)),
        "macroF1": round(statistics.fmean(f1_values), 4),
        "perClass": per_class,
    }


def wilson_interval(successes: int, total: int, z: float = 1.96) -> list[float] | None:
    if total <= 0:
        return None
    proportion = successes / total
    denominator = 1 + z * z / total
    center = (proportion + z * z / (2 * total)) / denominator
    margin = z * math.sqrt(proportion * (1 - proportion) / total + z * z / (4 * total * total)) / denominator
    return [round(max(0.0, center - margin), 4), round(min(1.0, center + margin), 4)]


def exact_mcnemar_p(corrected: int, regressed: int) -> float:
    discordant = corrected + regressed
    if discordant == 0:
        return 1.0
    lower_tail = sum(math.comb(discordant, value) for value in range(0, min(corrected, regressed) + 1))
    return round(min(1.0, 2 * lower_tail / (2 ** discordant)), 4)


def paired_intent_effect(rows: list[dict[str, Any]]) -> dict[str, Any]:
    usable = [row for row in rows if row.get("expectedIntent") in INTENTS]
    corrected = sum(
        row.get("rawIntent") != row["expectedIntent"] and row.get("finalIntent") == row["expectedIntent"]
        for row in usable
    )
    regressed = sum(
        row.get("rawIntent") == row["expectedIntent"] and row.get("finalIntent") != row["expectedIntent"]
        for row in usable
    )
    return {
        "count": len(usable),
        "correctedByOrchestrator": corrected,
        "regressedByOrchestrator": regressed,
        "netCorrectGain": corrected - regressed,
        "discordantCount": corrected + regressed,
        "mcnemarExactPValue": exact_mcnemar_p(corrected, regressed),
    }


def slot_metrics(rows: list[dict[str, Any]], prediction_key: str) -> dict[str, Any]:
    usable = [row for row in rows if row.get("evaluateSlots", True)]
    tp = fp = fn = exact = 0
    per_slot: dict[str, dict[str, int]] = {name: {"tp": 0, "fp": 0, "fn": 0} for name in SLOT_NAMES}
    for row in usable:
        expected = normalize_slots(row.get("expectedSlots"))
        predicted = normalize_slots(row.get(prediction_key))
        if all(set(expected[name]) == set(predicted[name]) for name in SLOT_NAMES):
            exact += 1
        for name in SLOT_NAMES:
            gold = set(expected[name])
            actual = set(predicted[name])
            slot_tp = len(gold & actual)
            slot_fp = len(actual - gold)
            slot_fn = len(gold - actual)
            tp += slot_tp
            fp += slot_fp
            fn += slot_fn
            per_slot[name]["tp"] += slot_tp
            per_slot[name]["fp"] += slot_fp
            per_slot[name]["fn"] += slot_fn
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "count": len(usable),
        "exactCorrect": exact,
        "microPrecision": round(precision, 4),
        "microRecall": round(recall, 4),
        "microF1": round(f1, 4),
        "exactMatch": round(exact / len(usable), 4) if usable else None,
        "counts": {"tp": tp, "fp": fp, "fn": fn},
        "perSlotCounts": per_slot,
    }


def rate(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 4) if denominator else None


def candidate_constraint_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    ranked_rows = [row for row in rows if row.get("rankedTracePresent")]
    raw_recommendation_rows = [row for row in ranked_rows if row.get("rawRecommendationParseable")]
    raw_violation_rows = [row for row in raw_recommendation_rows if row.get("rawOutOfWhitelistIds")]
    intercepted_rows = [row for row in raw_violation_rows if row.get("rawViolationIntercepted")]
    final_violation_rows = [row for row in ranked_rows if not row.get("whitelistPassed")]
    return {
        "rankedTraceCount": len(ranked_rows),
        "rawModelOutputCount": len(raw_recommendation_rows),
        "rawViolationTurnCount": len(raw_violation_rows),
        "rawViolationRate": rate(len(raw_violation_rows), len(raw_recommendation_rows)),
        "rawViolationIdCount": sum(len(row.get("rawOutOfWhitelistIds", [])) for row in raw_violation_rows),
        "interceptedViolationTurnCount": len(intercepted_rows),
        "finalViolationTurnCount": len(final_violation_rows),
        "whitelistPassRate": rate(sum(row.get("whitelistPassed") for row in ranked_rows), len(ranked_rows)),
    }


def summarize_quality(rows: list[dict[str, Any]]) -> dict[str, Any]:
    successful = [row for row in rows if not row.get("transportError")]
    clarify_rows = [row for row in successful if row.get("expectedClarifyAction") in CLARIFY_ACTIONS]
    retrieval_rows = [row for row in successful if row.get("acceptableMealIds")]
    raw_intent = classification_metrics(successful, "rawIntent")
    final_intent = classification_metrics(successful, "finalIntent")
    intent_effect = paired_intent_effect(successful)
    raw_slots = slot_metrics(successful, "rawSlots")
    final_slots = slot_metrics(successful, "finalSlots")
    clarify_correct = sum(row.get("clarifyAction") == row.get("expectedClarifyAction") for row in clarify_rows)
    hit3 = sum(bool(set(row.get("responseIds", [])[:3]) & set(row["acceptableMealIds"])) for row in retrieval_rows)
    all_constraints = candidate_constraint_metrics(successful)
    regular_constraints = candidate_constraint_metrics([
        row for row in successful if row.get("category") != "OUTPUT_CONSTRAINT_REDTEAM"
    ])
    red_team_constraints = candidate_constraint_metrics([
        row for row in successful if row.get("category") == "OUTPUT_CONSTRAINT_REDTEAM"
    ])
    completed = sum(row.get("responseReady") and row.get("requestFinished") for row in successful)
    fallback_rows = [row for row in successful if row.get("fallbackUsed")]
    fallback_completed = sum(row.get("responseReady") and row.get("requestFinished") for row in fallback_rows)
    return {
        "requestedTurns": len(rows),
        "completedHttpTurns": len(successful),
        "transportErrorCount": len(rows) - len(successful),
        "businessCompletionRate": rate(completed, len(successful)),
        "traceCompleteCount": sum(row.get("traceComplete") for row in successful),
        "traceCompletenessRate": rate(sum(row.get("traceComplete") for row in successful), len(successful)),
        "rawIntent": raw_intent,
        "finalIntent": final_intent,
        "intentPairedEffect": intent_effect,
        "intentAccuracyDelta": (
            round(final_intent["accuracy"] - raw_intent["accuracy"], 4)
            if raw_intent["accuracy"] is not None and final_intent["accuracy"] is not None
            else None
        ),
        "rawSlots": raw_slots,
        "finalSlots": final_slots,
        "slotF1Delta": round(final_slots["microF1"] - raw_slots["microF1"], 4),
        "clarify": {
            "count": len(clarify_rows),
            "correct": clarify_correct,
            "accuracy": rate(clarify_correct, len(clarify_rows)),
        },
        "retrieval": {
            "labeledCount": len(retrieval_rows),
            "hitCount": hit3,
            "hitAt3": rate(hit3, len(retrieval_rows)),
            **all_constraints,
            "regularCases": regular_constraints,
            "redTeamCases": red_team_constraints,
        },
        "fallback": {
            "triggerCount": len(fallback_rows),
            "triggerRate": rate(len(fallback_rows), len(successful)),
            "businessCompletionRate": rate(fallback_completed, len(fallback_rows)),
        },
        "performance": {
            "latencyMs": describe(row.get("durationMs") for row in successful),
            "normalLatencyMs": describe(row.get("durationMs") for row in successful if not row.get("fallbackUsed")),
            "fallbackLatencyMs": describe(row.get("durationMs") for row in fallback_rows),
            "totalTokens": describe(row.get("totalTokens") for row in successful if row.get("tokenComplete")),
            "inputTokens": describe(row.get("inputTokens") for row in successful if row.get("tokenComplete")),
            "outputTokens": describe(row.get("outputTokens") for row in successful if row.get("tokenComplete")),
            "tokenCoverageRate": rate(sum(row.get("tokenComplete") for row in successful), len(successful)),
            "agentCalls": describe(row.get("agentCallCount") for row in successful),
        },
        "categoryAccuracy": category_accuracy(successful),
    }


def category_accuracy(rows: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row.get("category", "UNKNOWN")].append(row)
    result: dict[str, Any] = {}
    for category, items in sorted(grouped.items()):
        raw_correct = sum(item.get("rawIntent") == item.get("expectedIntent") for item in items)
        final_correct = sum(item.get("finalIntent") == item.get("expectedIntent") for item in items)
        result[category] = {
            "count": len(items),
            "rawIntentCorrect": raw_correct,
            "finalIntentCorrect": final_correct,
            "rawIntentAccuracy": rate(raw_correct, len(items)),
            "finalIntentAccuracy": rate(final_correct, len(items)),
        }
    return result


def run_quality(
    api: DietApi,
    cases: list[dict[str, Any]],
    repeats: int,
    delay_seconds: float,
    run_token: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    total = sum(len(case["turns"]) for case in cases) * repeats
    current = 0
    for repeat in range(1, repeats + 1):
        for case in cases:
            session_id = f"eval_{run_token}_{repeat}_{case['caseId']}"
            for turn_index, turn in enumerate(case["turns"], 1):
                current += 1
                print(f"[quality {current}/{total}] {case['caseId']} turn={turn_index}", flush=True)
                base = {
                    "caseId": case["caseId"],
                    "category": case.get("category"),
                    "repeat": repeat,
                    "turnIndex": turn_index,
                    "message": turn["message"],
                    "expectedIntent": turn.get("expectedIntent"),
                    "expectedSlots": normalize_slots(turn.get("expectedSlots")),
                    "expectedClarifyAction": turn.get("expectedClarifyAction"),
                    "evaluateSlots": turn.get("evaluateSlots", True),
                    "acceptableMealIds": turn.get("acceptableMealIds", []),
                    "sessionId": session_id,
                }
                try:
                    response = api.chat(session_id, turn["message"], case["sourceMode"])
                    trace_id = response["traceId"]
                    trace_row = api.trace(trace_id)
                    api.label_trace(trace_id, turn)
                    extracted = extract_trace(trace_row)
                    rows.append({**base, **extracted, "traceId": trace_id, "response": response})
                except Exception as error:  # 单条失败不阻断整批，报告保留证据。
                    rows.append({**base, "transportError": str(error)})
                    print(f"  ERROR: {error}", file=sys.stderr, flush=True)
                if delay_seconds:
                    time.sleep(delay_seconds)
    return rows


def load_fault_specs(path: Path) -> list[dict[str, Any]]:
    return load_jsonl(path)


def run_faults(
    api: DietApi,
    specs: list[dict[str, Any]],
    delay_seconds: float,
    run_token: str,
) -> dict[str, Any]:
    start_at = datetime.now() - timedelta(seconds=2)
    rows: list[dict[str, Any]] = []
    online_specs = [spec for spec in specs if spec.get("endpoint", "CHAT") == "CHAT"]
    total = sum(int(spec.get("repeat", 1)) for spec in online_specs)
    current = 0
    for spec in online_specs:
        for index in range(1, int(spec.get("repeat", 1)) + 1):
            current += 1
            fault = spec["fault"]
            session_id = f"fault_{run_token}_{fault.lower()}_{index}"
            print(f"[fault {current}/{total}] {fault} sample={index}", flush=True)
            base = {"fault": fault, "sample": index, "sessionId": session_id}
            try:
                response = api.chat(session_id, spec["message"], spec.get("sourceMode", "PUBLIC"), fault)
                trace_id = response["traceId"]
                extracted = extract_trace(api.trace(trace_id))
                injected_events = [
                    event for event in extracted["errorEvents"]
                    if "InjectedEvaluationFaultException" in str(event.get("errorMessage"))
                ]
                expected_agent = spec.get("expectedAgent")
                observed = any(event.get("agentName") == expected_agent for event in injected_events)
                rows.append({
                    **base,
                    **extracted,
                    "traceId": trace_id,
                    "response": response,
                    "injectedFaultObserved": observed,
                    "expectedAgent": expected_agent,
                })
            except Exception as error:
                rows.append({**base, "transportError": str(error), "injectedFaultObserved": False})
                print(f"  ERROR: {error}", file=sys.stderr, flush=True)
            if delay_seconds:
                time.sleep(delay_seconds)

    judge_spec = next((spec for spec in specs if spec.get("endpoint") == "EVALUATION"), None)
    judge_result: dict[str, Any] | None = None
    if judge_spec:
        requested = int(judge_spec.get("repeat", 10))
        print(f"[fault judge] EVALUATION_JUDGE_ERROR traces={requested}", flush=True)
        try:
            report = api.evaluate_with_fault(start_at, datetime.now() + timedelta(seconds=2), requested)
            trace_results = report.get("traceResults", [])
            null_scores = sum(item.get("llmJudgeScore") is None for item in trace_results)
            judge_result = {
                "requestedTraceCount": requested,
                "evaluatedTraceCount": len(trace_results),
                "nullJudgeScoreCount": null_scores,
                "requestCompleted": True,
                "gracefulDegradationRate": rate(null_scores, len(trace_results)),
            }
        except Exception as error:
            judge_result = {"requestCompleted": False, "transportError": str(error)}

    completed = [row for row in rows if not row.get("transportError")]
    observed = [row for row in completed if row.get("injectedFaultObserved")]
    business_completed = [row for row in observed if row.get("responseReady") and row.get("requestFinished")]
    by_fault: dict[str, Any] = {}
    for fault in sorted({row["fault"] for row in rows}):
        fault_rows = [row for row in rows if row["fault"] == fault]
        fault_observed = [row for row in fault_rows if row.get("injectedFaultObserved")]
        fault_completed = [row for row in fault_observed if row.get("responseReady") and row.get("requestFinished")]
        by_fault[fault] = {
            "requested": len(fault_rows),
            "injectionObserved": len(fault_observed),
            "businessCompleted": len(fault_completed),
            "businessCompletionRate": rate(len(fault_completed), len(fault_observed)),
        }
    return {
        "rows": rows,
        "summary": {
            "requestedOnlineFaults": len(rows),
            "injectionObserved": len(observed),
            "businessCompleted": len(business_completed),
            "businessCompletionRate": rate(len(business_completed), len(observed)),
            "byFault": by_fault,
            "judge": judge_result,
        },
    }


def percent(value: Any, digits: int = 1) -> str:
    return "N/A" if value is None else f"{float(value) * 100:.{digits}f}%"


def percentage_points(value: Any, digits: int = 1) -> str:
    return "N/A" if value is None else f"{float(value) * 100:.{digits}f}"


def number(value: Any, suffix: str = "") -> str:
    return "N/A" if value is None else f"{value}{suffix}"


def decimal(value: Any, digits: int = 3) -> str:
    return "N/A" if value is None else f"{float(value):.{digits}f}"


def accuracy_cell(metric: dict[str, Any]) -> str:
    if metric.get("count", 0) == 0 or metric.get("accuracy") is None:
        return "N/A"
    ci = metric.get("accuracyCi95")
    ci_text = ""
    if isinstance(ci, list) and len(ci) == 2:
        ci_text = f"，95% CI {percent(ci[0])}–{percent(ci[1])}"
    return f"{metric['correct']}/{metric['count']}（{percent(metric['accuracy'])}{ci_text}）"


def markdown_report(metadata: dict[str, Any], quality: dict[str, Any] | None, faults: dict[str, Any] | None) -> str:
    stats = metadata.get("datasetStats", {})
    lines = [
        "# 今日宜食固定评测报告",
        "",
        "> 本报告由 `evaluation/run_evaluation.py` 自动生成。所有数字仅对本次固定配置和样本成立。",
        "",
        "## 运行信息",
        "",
        f"- 运行名称：`{metadata['runName']}`",
        f"- 运行时间：`{metadata['createdAt']}`",
        f"- 评测集 SHA-256：`{metadata['caseFileSha256']}`",
        f"- 故障集 SHA-256：`{metadata['faultCaseFileSha256']}`",
        f"- 代码版本：`{metadata['codeVersion']}`",
        f"- 模型 / Prompt：`{metadata['modelName']}` / `{metadata['promptVersion']}`",
        f"- 公共餐食快照：`{metadata['publicMealsSha256']}`（{metadata['publicMealCount']} 条）",
        f"- 槽位字典快照：`{metadata['slotOptionsSha256']}`",
        f"- 服务地址：`{metadata['baseUrl']}`",
        f"- 重复次数：`{metadata['repeats']}`",
        f"- 数据集规模：{stats.get('sessionCount', 'N/A')} 组会话 / {stats.get('turnCount', 'N/A')} 轮；多轮会话 {stats.get('multiTurnSessionCount', 'N/A')} 组 / {stats.get('multiTurnTurnCount', 'N/A')} 轮（每组 {stats.get('multiTurnMinTurns', 'N/A')}–{stats.get('multiTurnMaxTurns', 'N/A')} 轮）",
        "",
    ]
    if quality:
        perf = quality["performance"]
        paired = quality["intentPairedEffect"]
        retrieval = quality["retrieval"]
        regular_constraints = retrieval["regularCases"]
        red_team_constraints = retrieval["redTeamCases"]
        lines.extend([
            "## 同轮编排消融（不是旧版本 / 新版本对照）",
            "",
            "- Raw 基线：同一轮 `IntentAgent` 的 `INTENT_RECOGNIZED` 输出，尚未经过 Java 规则。",
            "- Orchestrated：同一轮经过 `IntentReviseService` 历史状态、风险关键词及低置信度规则后的 `INTENT_REVISED` 输出。",
            "",
            "| 指标 | IntentAgent Raw | Orchestrated | 净变化 |",
            "|---|---:|---:|---:|",
            f"| 意图 Accuracy | {accuracy_cell(quality['rawIntent'])} | {accuracy_cell(quality['finalIntent'])} | {paired['netCorrectGain']:+d} 轮 / {percentage_points(quality['intentAccuracyDelta'])} 个百分点 |",
            f"| 意图 Macro-F1 | {decimal(quality['rawIntent']['macroF1'])} | {decimal(quality['finalIntent']['macroF1'])} | {float(quality['finalIntent']['macroF1'] - quality['rawIntent']['macroF1']):+.3f} |",
            f"| 槽位 Micro-F1 | {decimal(quality['rawSlots']['microF1'])} | {decimal(quality['finalSlots']['microF1'])} | {float(quality['slotF1Delta']):+.3f} |",
            f"| 槽位 Exact Match | {quality['rawSlots']['exactCorrect']}/{quality['rawSlots']['count']}（{percent(quality['rawSlots']['exactMatch'])}） | {quality['finalSlots']['exactCorrect']}/{quality['finalSlots']['count']}（{percent(quality['finalSlots']['exactMatch'])}） | - |",
            "",
            f"- 编排规则纠正 **{paired['correctedByOrchestrator']}** 轮、引入回退 **{paired['regressedByOrchestrator']}** 轮，净增 **{paired['netCorrectGain']:+d}** 轮；配对 McNemar 精确检验 `p={paired['mcnemarExactPValue']}`。",
            f"- 澄清动作：**{quality['clarify']['correct']}/{quality['clarify']['count']}（{percent(quality['clarify']['accuracy'])}）**。",
            "",
            "## 分场景意图结果",
            "",
            "| 场景 | Turn数 | Raw正确 | 编排后正确 |",
            "|---|---:|---:|---:|",
            *[
                f"| {category} | {item['count']} | {item['rawIntentCorrect']}/{item['count']} | {item['finalIntentCorrect']}/{item['count']} |"
                for category, item in quality["categoryAccuracy"].items()
            ],
            "",
            "## 推荐候选约束",
            "",
            "| 口径 | 可解析原始输出 | 原始越界 | 候选外ID | 已拦截 | 最终越界 |",
            "|---|---:|---:|---:|---:|---:|",
            f"| 常规样本 | {regular_constraints['rawModelOutputCount']} | {regular_constraints['rawViolationTurnCount']} | {regular_constraints['rawViolationIdCount']} | {regular_constraints['interceptedViolationTurnCount']} | {regular_constraints['finalViolationTurnCount']}/{regular_constraints['rankedTraceCount']} |",
            f"| 越界红队样本 | {red_team_constraints['rawModelOutputCount']} | {red_team_constraints['rawViolationTurnCount']} | {red_team_constraints['rawViolationIdCount']} | {red_team_constraints['interceptedViolationTurnCount']} | {red_team_constraints['finalViolationTurnCount']}/{red_team_constraints['rankedTraceCount']} |",
            f"| 全部 | {retrieval['rawModelOutputCount']} | {retrieval['rawViolationTurnCount']} | {retrieval['rawViolationIdCount']} | {retrieval['interceptedViolationTurnCount']} | {retrieval['finalViolationTurnCount']}/{retrieval['rankedTraceCount']} |",
            "",
            "- 常规样本用于描述自然评测集中的越界；红队样本只用于验证约束在诱导攻击下是否实际生效，两者不能混写为同一个线上发生率。",
            f"- 标注推荐 Hit@3：**{retrieval['hitCount']}/{retrieval['labeledCount']}（{percent(retrieval['hitAt3'])}）**；当前公共餐食仅 {metadata['publicMealCount']} 条，该指标只作回归检查，不作为召回泛化能力结论。",
            "",
            "## 工程完整性与性能基线",
            "",
            f"- Trace 完整：**{quality['traceCompleteCount']}/{quality['completedHttpTurns']}**；该指标用于发现埋点缺失，不作为效果提升数字。",
            "",
            "| 指标 | 数值 | 样本数 |",
            "|---|---:|---:|",
            f"| 端到端平均耗时 | {round(perf['latencyMs']['mean']) if perf['latencyMs']['mean'] is not None else 'N/A'} ms | {perf['latencyMs']['count']} |",
            f"| 端到端 P50 | {round(perf['latencyMs']['p50']) if perf['latencyMs']['p50'] is not None else 'N/A'} ms | {perf['latencyMs']['count']} |",
            f"| 端到端 P95 | {round(perf['latencyMs']['p95']) if perf['latencyMs']['p95'] is not None else 'N/A'} ms | {perf['latencyMs']['count']} |",
            f"| 平均总 Token | {round(perf['totalTokens']['mean']) if perf['totalTokens']['mean'] is not None else 'N/A'} | {perf['totalTokens']['count']} |",
            f"| P95 总 Token | {round(perf['totalTokens']['p95']) if perf['totalTokens']['p95'] is not None else 'N/A'} | {perf['totalTokens']['count']} |",
            f"| Token 可用样本 | {perf['totalTokens']['count']}/{quality['completedHttpTurns']} | {quality['completedHttpTurns']} |",
            "",
            "## 正常运行中的降级",
            "",
            f"- 自然运行中触发 Fallback：**{quality['fallback']['triggerCount']}/{quality['completedHttpTurns']}**。",
            f"- 已触发 Fallback 样本的业务完成率：**{percent(quality['fallback']['businessCompletionRate'])}**。",
            "",
        ])
    if faults:
        lines.extend([
            "## 可控故障注入",
            "",
            f"- 已观测注入次数：**{faults['injectionObserved']} / {faults['requestedOnlineFaults']}**",
            f"- 注入异常样本业务完成率：**{faults['businessCompleted']}/{faults['injectionObserved']}（{percent(faults['businessCompletionRate'])}）**",
            "",
            "| 故障 | 请求数 | 成功注入 | 完成业务响应 | 完成率 |",
            "|---|---:|---:|---:|---:|",
        ])
        for fault, item in faults["byFault"].items():
            lines.append(
                f"| {fault} | {item['requested']} | {item['injectionObserved']} | {item['businessCompleted']} | {percent(item['businessCompletionRate'])} |"
            )
        judge = faults.get("judge")
        if judge:
            lines.extend([
                "",
                f"- Judge 故障时评估接口完成：**{'是' if judge.get('requestCompleted') else '否'}**",
                f"- Judge 降级覆盖率：**{percent(judge.get('gracefulDegradationRate'))}**",
            ])
        lines.append("")
    lines.extend([
        "## 简历使用提醒",
        "",
        "- 只有报告中样本数、配置和 Gold Label 经人工复核后，数字才能写入简历。",
        "- `Accuracy 80% → 90%` 应表述为提升 10 个百分点，而不是提升 10%。",
        "- 同轮消融必须同时报告纠正数、回退数和 McNemar p 值；样本少或 p 值较大时，不写成稳定提升。",
        "- 常规样本原始候选越界为 0 时，白名单只能写成防御机制，不能把最终 100% 通过率写成优化结果；红队结果必须注明是诱导攻击测试。",
        "- Trace/Token 覆盖完整属于评测工具自检，不作为业务效果数字。",
        "- Token 或延迟的下降比例必须通过 `compare_reports.py` 比较两个独立版本得出。",
        "- 若故障未被实际观测，不得将该条计入 Fallback 完成率分母。",
        "",
    ])
    return "\n".join(lines)


def write_outputs(
    output_dir: Path,
    metadata: dict[str, Any],
    quality_rows: list[dict[str, Any]],
    quality_summary: dict[str, Any] | None,
    fault_result: dict[str, Any] | None,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    full = {
        "metadata": metadata,
        "quality": quality_summary,
        "faults": fault_result["summary"] if fault_result else None,
    }
    (output_dir / "summary.json").write_text(json.dumps(full, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "raw-results.json").write_text(
        json.dumps(
            {"qualityRows": quality_rows, "faultRows": fault_result["rows"] if fault_result else []},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (output_dir / "report.md").write_text(
        markdown_report(metadata, quality_summary, fault_result["summary"] if fault_result else None),
        encoding="utf-8",
    )
    if quality_rows:
        columns = [
            "caseId", "category", "repeat", "turnIndex", "message", "traceId",
            "expectedIntent", "rawIntent", "finalIntent", "expectedClarifyAction",
            "clarifyAction", "status", "durationMs", "totalTokens", "fallbackUsed",
            "traceComplete", "rawRecommendationParseable", "rawRecommendationIds",
            "candidateWhitelistIds", "rawOutOfWhitelistIds", "rawViolationIntercepted",
            "whitelistPassed", "transportError",
        ]
        with (output_dir / "turn-results.csv").open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(quality_rows)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="今日宜食固定评测集运行器")
    parser.add_argument("--base-url", default="http://localhost:8080/api/v1/diet")
    parser.add_argument("--user-id", type=int, default=910001)
    parser.add_argument("--cases", type=Path, default=ROOT / "cases" / "quality-cases.jsonl")
    parser.add_argument("--fault-cases", type=Path, default=ROOT / "cases" / "fault-cases.jsonl")
    parser.add_argument("--config", type=Path, default=ROOT / "benchmark-config.json")
    parser.add_argument("--mode", choices=("validate", "quality", "fault", "all"), default="all")
    parser.add_argument("--run-name", default="candidate")
    parser.add_argument("--code-version", default="unrecorded", help="Git commit/tag 或人工版本号")
    parser.add_argument("--model-name", default="qwen-flash")
    parser.add_argument("--prompt-version", default="current")
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--delay-ms", type=int, default=100)
    parser.add_argument("--timeout", type=float, default=90.0)
    parser.add_argument("--output-dir", type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.repeats < 1:
        print("--repeats 必须 >= 1", file=sys.stderr)
        return 2
    config = load_json(args.config)
    cases = load_jsonl(args.cases)
    fault_specs = load_fault_specs(args.fault_cases)
    api = DietApi(args.base_url, args.user_id, args.timeout)
    try:
        slot_options = api.slot_options()
        public_meals = api.public_meals()
    except Exception as error:
        print(f"启动检查失败：{error}", file=sys.stderr)
        print("请先启动 Spring Boot，并确认 base-url 正确。", file=sys.stderr)
        return 2
    errors = validate_cases(cases, slot_options)
    if args.cases.resolve() == (ROOT / "cases" / "quality-cases.jsonl").resolve():
        errors.extend(validate_dataset_design(cases, config))
    errors.extend(validate_fault_specs(fault_specs))
    if errors:
        print("评测集校验失败：", file=sys.stderr)
        for error in errors:
            print("- " + error, file=sys.stderr)
        return 2
    print(f"评测集校验通过：{len(cases)} 个会话，{sum(len(case['turns']) for case in cases)} 个 Turn")
    print(f"故障集校验通过：{len(fault_specs)} 类故障配置")
    if args.mode == "validate":
        return 0

    created_at = datetime.now()
    run_token = created_at.strftime("%Y%m%d%H%M%S")
    output_dir = args.output_dir or ROOT / "reports" / f"{run_token}-{args.run_name}"
    metadata = {
        "runName": args.run_name,
        "createdAt": created_at.isoformat(timespec="seconds"),
        "baseUrl": args.base_url,
        "userId": args.user_id,
        "repeats": args.repeats,
        "benchmarkVersion": config.get("benchmarkVersion"),
        "codeVersion": args.code_version,
        "modelName": args.model_name,
        "promptVersion": args.prompt_version,
        "caseFile": str(args.cases),
        "caseFileSha256": file_sha256(args.cases),
        "faultCaseFile": str(args.fault_cases),
        "faultCaseFileSha256": file_sha256(args.fault_cases),
        "configFileSha256": file_sha256(args.config),
        "slotOptionsSha256": value_sha256(slot_options),
        "publicMealsSha256": value_sha256(public_meals),
        "publicMealCount": len(public_meals),
        "datasetStats": dataset_stats(cases),
    }
    quality_rows: list[dict[str, Any]] = []
    quality_summary = None
    fault_result = None
    if args.mode in {"quality", "all"}:
        quality_rows = run_quality(
            api,
            cases,
            args.repeats,
            max(0, args.delay_ms) / 1000.0,
            run_token,
        )
        quality_summary = summarize_quality(quality_rows)
    if args.mode in {"fault", "all"}:
        fault_result = run_faults(
            api,
            fault_specs,
            max(0, args.delay_ms) / 1000.0,
            run_token,
        )
    write_outputs(output_dir, metadata, quality_rows, quality_summary, fault_result)
    print(f"评测完成：{output_dir}")
    print(f"报告：{output_dir / 'report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
