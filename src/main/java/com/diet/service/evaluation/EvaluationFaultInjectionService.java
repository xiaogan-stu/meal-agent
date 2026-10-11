package com.diet.service.evaluation;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.util.Locale;
import java.util.Set;
import java.util.function.Supplier;

/**
 * 本地评测专用故障注入器。
 *
 * <p>默认关闭。只有显式启用 {@code diet.evaluation.fault-injection-enabled}
 * 且请求携带 {@code X-Evaluation-Fault} 时才会生效。故障上下文使用
 * ThreadLocal 绑定到当前 HTTP 请求，finally 中必定清理，不会污染其他请求。</p>
 */
@Service
public class EvaluationFaultInjectionService {
    public static final String INTENT_AGENT_ERROR = "INTENT_AGENT_ERROR";
    public static final String CLARIFY_AGENT_ERROR = "CLARIFY_AGENT_ERROR";
    public static final String RECOMMEND_AGENT_ERROR = "RECOMMEND_AGENT_ERROR";
    public static final String EVALUATION_JUDGE_ERROR = "EVALUATION_JUDGE_ERROR";

    private static final Set<String> SUPPORTED_FAULTS = Set.of(
            INTENT_AGENT_ERROR,
            CLARIFY_AGENT_ERROR,
            RECOMMEND_AGENT_ERROR,
            EVALUATION_JUDGE_ERROR
    );

    private final boolean enabled;
    private final ThreadLocal<String> activeFault = new ThreadLocal<>();

    public EvaluationFaultInjectionService(
            @Value("${diet.evaluation.fault-injection-enabled:false}") boolean enabled
    ) {
        this.enabled = enabled;
    }

    /** 在当前请求线程中执行带故障上下文的操作。 */
    public <T> T withFault(String requestedFault, Supplier<T> action) {
        String normalized = normalize(requestedFault);
        if (normalized == null) {
            return action.get();
        }
        if (!enabled) {
            throw new IllegalStateException(
                    "评测故障注入未启用，请设置 DIET_EVALUATION_FAULT_INJECTION_ENABLED=true"
            );
        }
        if (!SUPPORTED_FAULTS.contains(normalized)) {
            throw new IllegalArgumentException("不支持的评测故障类型: " + normalized);
        }
        activeFault.set(normalized);
        try {
            return action.get();
        } finally {
            activeFault.remove();
        }
    }

    /** 在 AgentTraceService 真正发起模型调用前注入异常，确保异常仍会进入 Trace。 */
    public void maybeFailAgent(String agentName) {
        String fault = activeFault.get();
        if (fault == null) {
            return;
        }
        boolean shouldFail = switch (fault) {
            case INTENT_AGENT_ERROR -> "IntentAgent".equals(agentName);
            case CLARIFY_AGENT_ERROR -> "ClarifyAgent".equals(agentName);
            case RECOMMEND_AGENT_ERROR -> "RecommendResponseAgent".equals(agentName);
            case EVALUATION_JUDGE_ERROR -> "EvaluationJudgeAgent".equals(agentName);
            default -> false;
        };
        if (shouldFail) {
            throw new InjectedEvaluationFaultException(fault, agentName);
        }
    }

    private String normalize(String requestedFault) {
        if (requestedFault == null || requestedFault.isBlank()) {
            return null;
        }
        return requestedFault.trim().toUpperCase(Locale.ROOT);
    }

    /** 使用独立异常类型，便于 Trace 和报告准确识别“主动故障注入”。 */
    public static final class InjectedEvaluationFaultException extends RuntimeException {
        public InjectedEvaluationFaultException(String fault, String agentName) {
            super("Injected evaluation fault " + fault + " for " + agentName);
        }
    }
}
