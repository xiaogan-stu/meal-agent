package com.diet.constants;

public final class DietConstants {
    /**
     * 演示环境的用户隔离请求头，不构成身份认证或授权机制。
     * 生产部署必须由可信认证系统提供用户身份，不能直接信任客户端传值。
     */
    public static final String USER_ID = "X-User-Id";
    /** 仅供本地固定评测使用；生产环境必须保持故障注入开关关闭。 */
    public static final String EVALUATION_FAULT = "X-Evaluation-Fault";

    private DietConstants() {
    }
}
