package com.diet.model;

import java.util.List;

import com.fasterxml.jackson.annotation.JsonAutoDetect;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
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
public class MealRequest {
    @NotBlank(message = "餐食名称不能为空")
    @Size(max = 100, message = "餐食名称长度不能超过100个字符")
    private String name;

    @NotEmpty(message = "餐次至少选择一个标签")
    @Size(max = 8, message = "餐次标签不能超过8个")
    private List<String> mealTime;

    @Size(max = 20, message = "心情标签不能超过20个")
    private List<String> mood;

    @Size(max = 20, message = "场景标签不能超过20个")
    private List<String> scene;

    @Size(max = 20, message = "健康目标标签不能超过20个")
    private List<String> healthGoal;

    @Size(max = 20, message = "菜系标签不能超过20个")
    private List<String> cuisine;

    @Size(max = 20, message = "口味标签不能超过20个")
    private List<String> taste;

    @Size(max = 20, message = "便捷性标签不能超过20个")
    private List<String> convenience;

    public SlotBundle toSlots() {
        return new SlotBundle(mealTime, mood, scene, healthGoal, cuisine, taste, convenience);
    }
}
