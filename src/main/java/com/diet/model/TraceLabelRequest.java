package com.diet.model;
import com.diet.enums.ClarifyAction;
import com.diet.enums.Intent;
import com.fasterxml.jackson.annotation.JsonAutoDetect;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.experimental.Accessors;
import jakarta.validation.constraints.Size;
@Data
@JsonAutoDetect(fieldVisibility = JsonAutoDetect.Visibility.ANY)
@Accessors(fluent = true)
@AllArgsConstructor
@NoArgsConstructor
public class TraceLabelRequest {
    private Intent expectedIntent;
    private SlotBundle expectedSlots;
    private ClarifyAction expectedClarifyAction;
    @Size(max = 512, message = "标注说明长度不能超过512个字符")
    private String labelNote;
}
