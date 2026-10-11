package com.diet.controller.evaluation;

import com.diet.constants.DietConstants;
import com.diet.model.EvaluationReport;
import com.diet.model.EvaluationRequest;
import com.diet.service.evaluation.EvaluationService;
import com.diet.service.evaluation.EvaluationFaultInjectionService;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/diet/evaluations")
public class EvaluationController {
    private final EvaluationService evaluationService;
    private final EvaluationFaultInjectionService faultInjectionService;

    public EvaluationController(
            EvaluationService evaluationService,
            EvaluationFaultInjectionService faultInjectionService
    ) {
        this.evaluationService = evaluationService;
        this.faultInjectionService = faultInjectionService;
    }

    @PostMapping
    public EvaluationReport evaluate(
            @RequestHeader(value = DietConstants.USER_ID, defaultValue = "1") Long userId,
            @RequestHeader(value = DietConstants.EVALUATION_FAULT, required = false) String evaluationFault,
            @Valid @RequestBody EvaluationRequest request
    ) {
        return faultInjectionService.withFault(
                evaluationFault,
                () -> evaluationService.evaluate(userId, request)
        );
    }
}
