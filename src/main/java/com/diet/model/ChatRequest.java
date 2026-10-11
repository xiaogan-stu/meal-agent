package com.diet.model;

import java.util.Map;

import com.diet.enums.SourceMode;
import com.fasterxml.jackson.annotation.JsonAutoDetect;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
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
public class ChatRequest {
    @Size(max = 64, message = "sessionId 长度不能超过64个字符")
    private String sessionId;

    @NotBlank(message = "消息不能为空")
    @Size(max = 2000, message = "消息长度不能超过2000个字符")
    private String message;

    @NotNull(message = "数据源模式不能为空")
    private SourceMode sourceMode;

    @Size(max = 20, message = "上下文字段不能超过20个")
    private Map<String, Object> context;
}
