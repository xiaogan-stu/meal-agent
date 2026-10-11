package com.diet.model;

import com.fasterxml.jackson.annotation.JsonAutoDetect;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;
import jakarta.validation.constraints.Size;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.experimental.Accessors;

@Data
@JsonAutoDetect(fieldVisibility = JsonAutoDetect.Visibility.ANY)
@Accessors(fluent = true)
@AllArgsConstructor
@NoArgsConstructor
public class FeedbackRequest {
    @NotBlank(message = "反馈 sessionId 不能为空")
    @Size(max = 64, message = "sessionId 长度不能超过64个字符")
    private String sessionId;

    @NotNull(message = "餐食ID不能为空")
    @Positive(message = "餐食ID必须为正数")
    private Long itemId;

    @NotBlank(message = "反馈 action 不能为空")
    @Size(max = 32, message = "反馈 action 长度不能超过32个字符")
    private String action;

    @Min(value = 1, message = "评分不能低于1")
    @Max(value = 5, message = "评分不能高于5")
    private Integer rating;

    @Size(max = 512, message = "反馈原因长度不能超过512个字符")
    private String reason;
}
