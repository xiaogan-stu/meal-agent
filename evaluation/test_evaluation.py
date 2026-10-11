import json
import unittest
from pathlib import Path

import run_evaluation as runner


class EvaluationRunnerTest(unittest.TestCase):
    def test_fixed_dataset_is_valid_and_has_expected_size(self):
        cases = runner.load_jsonl(Path(__file__).parent / "cases" / "quality-cases.jsonl")
        self.assertEqual(76, len(cases))
        self.assertEqual(136, sum(len(case["turns"]) for case in cases))
        stats = runner.dataset_stats(cases)
        self.assertEqual(20, stats["multiTurnSessionCount"])
        self.assertEqual(80, stats["multiTurnTurnCount"])
        self.assertEqual(4, stats["multiTurnMinTurns"])
        self.assertEqual(4, stats["multiTurnMaxTurns"])
        self.assertEqual(8, stats["categorySessionCounts"]["OUTPUT_CONSTRAINT_REDTEAM"])
        self.assertEqual([], runner.validate_cases(cases, None))
        config = runner.load_json(Path(__file__).parent / "benchmark-config.json")
        self.assertEqual([], runner.validate_dataset_design(cases, config))
        faults = runner.load_fault_specs(Path(__file__).parent / "cases" / "fault-cases.jsonl")
        self.assertEqual(4, len(faults))
        self.assertEqual([], runner.validate_fault_specs(faults))

    def test_extract_trace_separates_raw_and_orchestrated_results(self):
        events = [
            self.event("REQUEST_RECEIVED", {}),
            self.event("USER_MESSAGE_RECORDED", {}),
            self.event("INTENT_RECOGNIZED", {
                "intent": "CLARIFY_NEEDED",
                "slots": {"mealTime": ["午餐"]},
            }),
            self.event("INTENT_REVISED", {
                "intent": "MEAL_RECOMMENDATION",
                "slots": {"mealTime": ["午餐"]},
            }),
            self.event("SLOTS_MERGED", {
                "mealTime": ["午餐"],
                "healthGoal": ["减脂"],
            }),
            {
                "eventType": "CLARIFY_DECISION",
                "outputPayload": "ClarifyResult(action=READY, questionToAsk=null, missingSlots=[])",
                "errorMessage": None,
            },
            {
                "eventType": "MEAL_RANKED",
                "outputPayload": "{ranked=[MealItem(id=3, sourceType=PUBLIC, name=轻食碗, slots=SlotBundle()), MealItem(id=7, sourceType=PUBLIC, name=粥, slots=SlotBundle())], rankedCount=2}",
                "errorMessage": None,
            },
            {
                **self.event("AGENT_CALL", {}),
                "inputTokens": 100,
                "outputTokens": 20,
                "totalTokens": 120,
                "agentName": "IntentAgent",
            },
            {
                **self.event("AGENT_CALL", {
                    "recommendations": [
                        {"mealId": 3, "reason": "候选内"},
                        {"mealId": 999, "reason": "候选外"},
                    ],
                    "speechText": "测试",
                }),
                "inputTokens": 30,
                "outputTokens": 10,
                "totalTokens": 40,
                "agentName": "RecommendResponseAgent",
            },
            self.event("RESPONSE_READY", {"displayBlocks": [{"id": 3}]}),
            self.event("REQUEST_FINISHED", {}),
        ]
        trace = runner.extract_trace({
            "status": "SUCCESS",
            "durationMs": 900,
            "eventCount": len(events),
            "traceJson": json.dumps({"events": events}, ensure_ascii=False),
        })
        self.assertEqual("CLARIFY_NEEDED", trace["rawIntent"])
        self.assertEqual("MEAL_RECOMMENDATION", trace["finalIntent"])
        self.assertEqual(["减脂"], trace["finalSlots"]["healthGoal"])
        self.assertEqual(160, trace["totalTokens"])
        self.assertEqual("READY", trace["clarifyAction"])
        self.assertEqual([3, 7], trace["rankedIds"])
        self.assertEqual([3, 7], trace["candidateWhitelistIds"])
        self.assertEqual([3, 999], trace["rawRecommendationIds"])
        self.assertEqual([999], trace["rawOutOfWhitelistIds"])
        self.assertTrue(trace["rawViolationIntercepted"])
        self.assertTrue(trace["rankedTracePresent"])
        self.assertTrue(trace["whitelistPassed"])
        self.assertTrue(trace["traceComplete"])

    def test_summary_calculates_ablation_delta(self):
        row = {
            "expectedIntent": "HEALTH_RISK",
            "rawIntent": "MEAL_RECOMMENDATION",
            "finalIntent": "HEALTH_RISK",
            "expectedSlots": {},
            "rawSlots": runner.normalize_slots({}),
            "finalSlots": runner.normalize_slots({}),
            "evaluateSlots": False,
            "expectedClarifyAction": None,
            "acceptableMealIds": [],
            "responseReady": True,
            "requestFinished": True,
            "traceComplete": True,
            "fallbackUsed": False,
            "durationMs": 100,
            "tokenComplete": True,
            "totalTokens": 10,
            "inputTokens": 8,
            "outputTokens": 2,
            "agentCallCount": 1,
            "category": "HEALTH_RISK",
            "rankedIds": [],
            "responseIds": [],
        }
        summary = runner.summarize_quality([row])
        self.assertEqual(0.0, summary["rawIntent"]["accuracy"])
        self.assertEqual(1.0, summary["finalIntent"]["accuracy"])
        self.assertEqual(1.0, summary["intentAccuracyDelta"])
        self.assertEqual(1, summary["intentPairedEffect"]["correctedByOrchestrator"])
        self.assertEqual(0, summary["intentPairedEffect"]["regressedByOrchestrator"])
        self.assertEqual(1, summary["intentPairedEffect"]["netCorrectGain"])

    def test_constraint_metrics_keep_regular_and_red_team_cases_separate(self):
        common = {
            "expectedIntent": "MEAL_RECOMMENDATION",
            "rawIntent": "MEAL_RECOMMENDATION",
            "finalIntent": "MEAL_RECOMMENDATION",
            "expectedSlots": {},
            "rawSlots": runner.normalize_slots({}),
            "finalSlots": runner.normalize_slots({}),
            "evaluateSlots": False,
            "expectedClarifyAction": None,
            "acceptableMealIds": [],
            "responseReady": True,
            "requestFinished": True,
            "traceComplete": True,
            "fallbackUsed": False,
            "durationMs": 100,
            "tokenComplete": True,
            "totalTokens": 10,
            "inputTokens": 8,
            "outputTokens": 2,
            "agentCallCount": 1,
            "rankedTracePresent": True,
            "rawRecommendationParseable": True,
            "whitelistPassed": True,
            "responseIds": [3],
        }
        regular = {
            **common,
            "category": "RECOMMENDATION",
            "rawOutOfWhitelistIds": [],
            "rawViolationIntercepted": False,
        }
        red_team = {
            **common,
            "category": "OUTPUT_CONSTRAINT_REDTEAM",
            "rawOutOfWhitelistIds": [999],
            "rawViolationIntercepted": True,
        }
        retrieval = runner.summarize_quality([regular, red_team])["retrieval"]
        self.assertEqual(0, retrieval["regularCases"]["rawViolationTurnCount"])
        self.assertEqual(1, retrieval["redTeamCases"]["rawViolationTurnCount"])
        self.assertEqual(1, retrieval["redTeamCases"]["interceptedViolationTurnCount"])
        self.assertEqual(1, retrieval["rawViolationTurnCount"])

    @staticmethod
    def event(event_type, output):
        return {
            "eventType": event_type,
            "outputPayload": json.dumps(output, ensure_ascii=False),
            "errorMessage": None,
        }


if __name__ == "__main__":
    unittest.main()
