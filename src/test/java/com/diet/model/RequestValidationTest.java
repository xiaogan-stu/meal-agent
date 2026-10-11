package com.diet.model;

import com.diet.enums.SourceMode;
import jakarta.validation.Validation;
import jakarta.validation.Validator;
import jakarta.validation.ValidatorFactory;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

import java.time.LocalDateTime;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

class RequestValidationTest {
    private static ValidatorFactory validatorFactory;
    private static Validator validator;

    @BeforeAll
    static void setUpValidator() {
        validatorFactory = Validation.buildDefaultValidatorFactory();
        validator = validatorFactory.getValidator();
    }

    @AfterAll
    static void closeValidator() {
        validatorFactory.close();
    }

    @Test
    void rejectsBlankChatMessageAndMissingSourceMode() {
        ChatRequest request = new ChatRequest(null, " ", null, null);

        assertThat(validator.validate(request))
                .extracting(violation -> violation.getPropertyPath().toString())
                .containsExactlyInAnyOrder("message", "sourceMode");
    }

    @Test
    void rejectsMealWithoutNameOrMealTime() {
        MealRequest request = new MealRequest(
                "",
                List.of(),
                List.of(),
                List.of(),
                List.of(),
                List.of(),
                List.of(),
                List.of()
        );

        assertThat(validator.validate(request))
                .extracting(violation -> violation.getPropertyPath().toString())
                .containsExactlyInAnyOrder("name", "mealTime");
    }

    @Test
    void rejectsInvalidFeedbackValues() {
        FeedbackRequest request = new FeedbackRequest("", 0L, "", 6, null);

        assertThat(validator.validate(request))
                .extracting(violation -> violation.getPropertyPath().toString())
                .containsExactlyInAnyOrder("sessionId", "itemId", "action", "rating");
    }

    @Test
    void rejectsMissingFeedbackItemId() {
        FeedbackRequest request = new FeedbackRequest("session-1", null, "like", 5, null);

        assertThat(validator.validate(request))
                .extracting(violation -> violation.getPropertyPath().toString())
                .containsExactly("itemId");
    }

    @Test
    void acceptsValidRequests() {
        ChatRequest chat = new ChatRequest(null, "午餐想吃清淡一点", SourceMode.PUBLIC, null);
        EvaluationRequest evaluation = new EvaluationRequest(
                LocalDateTime.now().minusHours(1),
                LocalDateTime.now(),
                true,
                100
        );

        assertThat(validator.validate(chat)).isEmpty();
        assertThat(validator.validate(evaluation)).isEmpty();
    }
}
