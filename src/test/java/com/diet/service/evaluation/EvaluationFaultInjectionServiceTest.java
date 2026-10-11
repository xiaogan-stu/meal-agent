package com.diet.service.evaluation;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

class EvaluationFaultInjectionServiceTest {

    @Test
    void enabledFaultOnlyFailsMatchingAgentAndCleansContext() {
        EvaluationFaultInjectionService service = new EvaluationFaultInjectionService(true);

        assertThrows(
                EvaluationFaultInjectionService.InjectedEvaluationFaultException.class,
                () -> service.withFault(
                        EvaluationFaultInjectionService.INTENT_AGENT_ERROR,
                        () -> {
                            service.maybeFailAgent("IntentAgent");
                            return null;
                        }
                )
        );

        assertDoesNotThrow(() -> service.maybeFailAgent("IntentAgent"));
        assertDoesNotThrow(() -> service.withFault(
                EvaluationFaultInjectionService.INTENT_AGENT_ERROR,
                () -> {
                    service.maybeFailAgent("ClarifyAgent");
                    return null;
                }
        ));
    }

    @Test
    void disabledServiceRejectsFaultHeader() {
        EvaluationFaultInjectionService service = new EvaluationFaultInjectionService(false);
        IllegalStateException error = assertThrows(
                IllegalStateException.class,
                () -> service.withFault(EvaluationFaultInjectionService.INTENT_AGENT_ERROR, () -> "unused")
        );
        assertEquals(
                "评测故障注入未启用，请设置 DIET_EVALUATION_FAULT_INJECTION_ENABLED=true",
                error.getMessage()
        );
    }
}
