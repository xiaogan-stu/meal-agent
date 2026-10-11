package com.diet.model;

import com.fasterxml.jackson.annotation.JsonAutoDetect;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.experimental.Accessors;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;

import java.time.LocalDateTime;

@Data
@JsonAutoDetect(fieldVisibility = JsonAutoDetect.Visibility.ANY)
@Accessors(fluent = true)
@AllArgsConstructor
@NoArgsConstructor
public class EvaluationRequest {
    @NotNull(message = "评估开始时间不能为空")
    private LocalDateTime startAt;

    @NotNull(message = "评估结束时间不能为空")
    private LocalDateTime endAt;
    private Boolean includeLlmJudge;

    @Min(value = 1, message = "评估条数不能小于1")
    @Max(value = 1000, message = "评估条数不能超过1000")
    private Integer limit;
}
