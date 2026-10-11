# Diet Agent 前端接口文档

> 本文档根据当前后端代码整理，面向 Vue 3 前端联调。
> 后端技术栈：Spring Boot 3.3.13、Java 21、MyBatis、MySQL。
> 文档更新时间：2026-08-10。

## 1. 接口约定

### 1.1 基础地址

本地后端默认监听：

```text
http://localhost:8080
```

业务接口统一前缀：

```text
/api/v1/diet
```

例如，创建会话的完整地址是：

```text
POST http://localhost:8080/api/v1/diet/sessions
```

### 1.2 通用请求头

| 请求头 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `Content-Type` | string | JSON 请求必填 | - | 固定为 `application/json` |
| `X-User-Id` | long | 否 | `1` | 当前用户 ID，用于隔离个人餐食、会话、Trace 和反馈 |

当前项目没有登录、JWT 或 Session Cookie 认证。`X-User-Id` 只是开发阶段的用户标识，不能当作正式鉴权机制。

### 1.3 通用响应规则

- 成功响应直接返回业务 JSON，没有 `{ code, data, message }` 包装层。
- 创建、查询、更新接口当前通常返回 HTTP `200 OK`。
- 删除餐食、保存反馈、保存 Trace 标注成功时返回 HTTP `200 OK`，响应体为空。
- Java `LocalDateTime` 使用 ISO-8601 格式，例如 `2026-08-10T14:30:00`，不包含时区。
- 请求枚举值区分大小写，必须使用文档中的大写英文值。

后端设计的业务错误结构为：

```json
{
  "message": "错误说明"
}
```

`DietExceptionHandler` 覆盖 `com.diet` 下的 Controller：参数校验与业务异常返回 HTTP `400` 和上述 `message` 结构；未处理异常会记录服务端日志，并返回 HTTP `500` 及统一提示，不向客户端泄露内部堆栈。

## 2. Vue 3 联调建议

### 2.1 Vite 开发代理

当前后端没有配置 CORS。Vue 开发服务器通常运行在 `5173` 端口，建议通过 Vite 代理请求后端：

```ts
// vite.config.ts
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8080',
        changeOrigin: true,
      },
    },
  },
})
```

### 2.2 Axios 实例

```ts
// src/api/http.ts
import axios from 'axios'

export const http = axios.create({
  baseURL: '/api/v1/diet',
  timeout: 60_000,
})

http.interceptors.request.use((config) => {
  config.headers['X-User-Id'] = localStorage.getItem('diet.userId') || '1'
  return config
})
```

对话接口会同步等待 Agent/大模型执行完成，建议将超时时间设为至少 60 秒，并在页面展示请求中的加载状态。

### 2.3 推荐的首次调用顺序

```text
GET  /slot-options       获取个人餐食表单选项
POST /sessions           创建会话
POST /chat               携带同一 sessionId 进行多轮对话
POST /feedback           对推荐结果提交反馈（可选）
```

也可以不调用 `/sessions`，第一次调用 `/chat` 时把 `sessionId` 设为 `null` 或不传，后端会自动创建并在响应中返回新的 `sessionId`。

## 3. 接口总览

| 模块 | 方法 | 路径 | 说明 |
| --- | --- | --- | --- |
| 会话 | POST | `/sessions` | 创建一个新会话 |
| 对话 | POST | `/chat` | 发送一轮饮食推荐对话 |
| 个人餐食 | GET | `/meals/personal` | 查询当前用户的个人餐食 |
| 个人餐食 | POST | `/meals/personal` | 新增个人餐食 |
| 个人餐食 | PUT | `/meals/personal/{mealId}` | 修改个人餐食 |
| 个人餐食 | DELETE | `/meals/personal/{mealId}` | 删除个人餐食 |
| 公共餐食 | GET | `/meals/public` | 查询公共餐食 |
| 槽位选项 | GET | `/slot-options` | 查询餐食标签选项 |
| 反馈 | POST | `/feedback` | 保存推荐反馈 |
| Trace | GET | `/debug/traces/{traceId}` | 查询单条 Trace |
| Trace | GET | `/debug/sessions/{sessionId}/traces` | 查询会话下的 Trace |
| Trace | GET | `/debug/traces` | 按时间范围查询 Trace |
| Trace | PUT | `/debug/traces/{traceId}/label` | 保存人工标注 |
| 评估 | POST | `/evaluations` | 生成 Trace 评估报告 |

## 4. 公共数据结构

### 4.1 枚举

#### SourceMode

| 值 | 说明 |
| --- | --- |
| `PERSONAL` | 只从当前用户的个人餐食库推荐 |
| `PUBLIC` | 只从公共餐食库推荐 |

一个会话首次使用后会保存其 `sourceMode`。后续即使使用相同 `sessionId` 传入另一种模式，后端仍优先使用会话中已保存的模式。切换个人库/公共库时，前端应创建新会话。

#### Intent

该枚举主要用于 Trace 人工标注：

| 值 | 说明 |
| --- | --- |
| `MEAL_RECOMMENDATION` | 请求餐食推荐 |
| `CLARIFY_NEEDED` | 信息不足，需要追问 |
| `MEAL_ADJUST` | 基于上一轮结果换一批或调整偏好 |
| `MEAL_PLAN` | 早餐、午餐、晚餐等多餐规划 |
| `HEALTH_RISK` | 涉及医疗、治疗承诺或极端节食风险 |
| `OTHER` | 与饮食无关 |

#### ClarifyAction

| 值 | 说明 |
| --- | --- |
| `ASK` | 应继续向用户追问 |
| `READY` | 信息足够，可以进入推荐流程 |

### 4.2 SlotBundle：七类餐食标签

```ts
export interface SlotBundle {
  mealTime: string[]
  mood: string[]
  scene: string[]
  healthGoal: string[]
  cuisine: string[]
  taste: string[]
  convenience: string[]
}
```

个人餐食新增/修改时，`mealTime` 至少选择一项，其余数组可为空。标签值必须来自 `GET /slot-options`，不要在前端硬编码为唯一数据源。

当前数据库初始化脚本提供的选项如下：

| 字段 | 中文含义 | 当前可选值 |
| --- | --- | --- |
| `mealTime` | 餐次 | 早餐、早午餐、午餐、下午茶、晚餐、夜宵、加餐、三餐 |
| `mood` | 心情 | 疲惫、烦躁、开心、焦虑、低落、平静、压力大、没胃口、想放松、想奖励自己 |
| `scene` | 场景 | 工作、校园、家里、周末、加班、运动后、通勤、聚餐、独处、旅行、夜宵 |
| `healthGoal` | 健康目标 | 减脂、清淡、养胃、高蛋白、均衡、降火、低油、低盐、低糖、补能、增肌、控碳水、易消化、暖胃 |
| `cuisine` | 菜系 | 川菜、粤菜、湘菜、江浙菜、东北菜、鲁菜、闽南菜、云南菜、新疆菜、轻食、西餐、日料、韩餐、东南亚菜、火锅、烧烤、海鲜、素食、家常、小吃、粉面、粥汤、快餐、甜品 |
| `taste` | 口味 | 清淡、辣、微辣、中辣、麻辣、甜、酸甜、咸鲜、鲜香、酱香、蒜香、番茄味、咖喱味、奶香、油香、烟火气 |
| `convenience` | 便捷性 | 快速、慢享、外带方便、堂食舒服、少排队、少餐具、一人食、多人共享、适合备餐、适合边走边吃 |

### 4.3 MealResponse

```ts
export interface MealResponse extends SlotBundle {
  id: number
  sourceType: 'PERSONAL' | 'PUBLIC'
  name: string
  matchScore: number
}
```

`matchScore` 是 `0` 到 `1` 的匹配分。普通餐食列表接口没有执行推荐打分，所以其中的 `matchScore` 当前固定为 `0.0`；对话推荐卡片中的该字段才有排序意义。

### 4.4 RequestTrace

```ts
export interface RequestTrace {
  id: number
  traceId: string
  sessionId: string
  userId: number
  status: string
  eventCount: number
  durationMs: number | null
  errorMessage: string | null
  traceJson: string
  expectedIntent: Intent | null
  expectedSlots: string | null
  expectedClarifyAction: ClarifyAction | null
  labeledBy: number | null
  labeledAt: string | null
  labelNote: string | null
  createdAt: string
  updatedAt: string
}
```

注意：`traceJson` 和 `expectedSlots` 是 JSON 字符串，不是已经解析的对象。展示详情前需要执行 `JSON.parse`，并做好解析失败兜底。

## 5. 会话与对话接口

### 5.1 创建会话

```http
POST /api/v1/diet/sessions
X-User-Id: 1
```

请求体：无。

成功响应：

```json
{
  "sessionId": "sess_6d407ceb0da44960bd94ac9d42ac2fa0"
}
```

前端需要保存 `sessionId`，同一段多轮对话持续复用。用户点击“新对话”或切换 `sourceMode` 时应重新创建。

### 5.2 发送对话

```http
POST /api/v1/diet/chat
Content-Type: application/json
X-User-Id: 1
```

请求体：

```ts
export interface ChatRequest {
  sessionId?: string | null
  message: string
  sourceMode: 'PERSONAL' | 'PUBLIC'
  context?: Record<string, unknown> | null
}
```

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `sessionId` | 否 | 为空时后端自动创建会话；多轮对话时传上次响应的值 |
| `message` | 是 | 用户消息，不能是空字符串或纯空白 |
| `sourceMode` | 是 | `PERSONAL` 或 `PUBLIC` |
| `context` | 否 | 预留扩展上下文；当前后端没有读取该字段 |

请求示例：

```json
{
  "sessionId": "sess_6d407ceb0da44960bd94ac9d42ac2fa0",
  "message": "今晚想吃清淡一点，最好快一些",
  "sourceMode": "PUBLIC",
  "context": {}
}
```

响应类型：

```ts
export interface ChatResponse {
  sessionId: string
  traceId: string
  responseType: 'ANSWER' | 'CLARIFY'
  speechText: string
  displayBlocks: MealResponse[]
  nextAction: 'WAIT_USER' | 'ASK_CLARIFY'
  clarifyQuestion: string | null
  missingSlots: string[]
}
```

推荐成功示例：

```json
{
  "sessionId": "sess_6d407ceb0da44960bd94ac9d42ac2fa0",
  "traceId": "trace_f2e72bb82d084da79b026698956ce734",
  "responseType": "ANSWER",
  "speechText": "可以优先考虑清汤馄饨和番茄鸡蛋面，口味清淡，也比较省时间。",
  "displayBlocks": [
    {
      "id": 2,
      "sourceType": "PUBLIC",
      "name": "清汤馄饨",
      "mealTime": ["早餐", "午餐", "晚餐", "三餐"],
      "mood": ["疲惫", "没胃口"],
      "scene": ["工作", "校园", "家里"],
      "healthGoal": ["清淡", "养胃", "暖胃"],
      "cuisine": ["小吃", "粥汤"],
      "taste": ["清淡", "咸鲜"],
      "convenience": ["快速", "少餐具"],
      "matchScore": 0.86
    }
  ],
  "nextAction": "WAIT_USER",
  "clarifyQuestion": null,
  "missingSlots": []
}
```

需要澄清示例：

```json
{
  "sessionId": "sess_6d407ceb0da44960bd94ac9d42ac2fa0",
  "traceId": "trace_f2e72bb82d084da79b026698956ce734",
  "responseType": "CLARIFY",
  "speechText": "这顿主要是早餐、午餐还是晚餐？",
  "displayBlocks": [],
  "nextAction": "ASK_CLARIFY",
  "clarifyQuestion": "这顿主要是早餐、午餐还是晚餐？",
  "missingSlots": ["mealTime"]
}
```

前端分支建议：

- `responseType === 'CLARIFY'`：展示 `clarifyQuestion`，等待用户继续回答，不要创建新会话。
- `responseType === 'ANSWER'`：展示 `speechText`；`displayBlocks` 非空时渲染推荐卡片。
- 个人库为空、没有匹配结果、健康风险或闲聊也会返回 `ANSWER`，但 `displayBlocks` 可能为空。
- `traceId` 可用于后台排查本轮 Agent 执行过程。

推荐进入正式匹配前，后端至少需要识别出 `mealTime`。如果没有 `healthGoal`，则至少需要存在 `cuisine`、`taste`、`scene` 或 `convenience` 中的一类明确偏好，否则会继续澄清。

常见业务错误：

```json
{ "message": "用户问题不能为空" }
```

```json
{ "message": "sourceMode 不能为空，请选择 PERSONAL 或 PUBLIC" }
```

## 6. 餐食接口

### 6.1 查询个人餐食

```http
GET /api/v1/diet/meals/personal
X-User-Id: 1
```

成功响应：`MealResponse[]`。

```json
[
  {
    "id": 5,
    "sourceType": "PERSONAL",
    "name": "土豆炖牛肉",
    "mealTime": ["晚餐"],
    "mood": ["平静"],
    "scene": ["家里"],
    "healthGoal": ["补能"],
    "cuisine": ["家常"],
    "taste": ["咸鲜"],
    "convenience": [],
    "matchScore": 0.0
  }
]
```

没有数据时返回空数组 `[]`。

### 6.2 新增个人餐食

```http
POST /api/v1/diet/meals/personal
Content-Type: application/json
X-User-Id: 1
```

请求体：

```ts
export interface MealRequest extends SlotBundle {
  name: string
}
```

```json
{
  "name": "香煎鸡胸肉",
  "mealTime": ["午餐", "晚餐"],
  "mood": [],
  "scene": ["运动后"],
  "healthGoal": ["高蛋白", "减脂"],
  "cuisine": ["轻食"],
  "taste": ["清淡"],
  "convenience": ["快速", "适合备餐"]
}
```

校验规则：

- `name` 不能为空或纯空白，保存时会自动去除首尾空格。
- `mealTime` 至少包含一个标签。
- 七类标签必须来自 `GET /slot-options` 的当前启用值。
- 除 `mealTime` 外的数组可为空；字段传 `null` 时后端也会归一化为空数组。

成功响应：新建后的 `MealResponse`。

常见业务错误：

```json
{ "message": "餐食名称不能为空" }
```

```json
{ "message": "餐次至少选择一个标签" }
```

```json
{ "message": "非法槽位标签: taste=特辣" }
```

### 6.3 修改个人餐食

```http
PUT /api/v1/diet/meals/personal/{mealId}
Content-Type: application/json
X-User-Id: 1
```

实际路径中的 `{mealId}` 应替换为餐食数字 ID，例如：

```http
PUT /api/v1/diet/meals/personal/5
```

请求体和校验规则与“新增个人餐食”一致。该接口是完整更新，前端应提交 `name` 和全部七类标签数组，而不是只提交发生变化的字段。

成功响应：更新后的 `MealResponse`。

餐食不存在或不属于当前 `X-User-Id` 时：

```json
{ "message": "个人餐食不存在或无权限修改" }
```

### 6.4 删除个人餐食

```http
DELETE /api/v1/diet/meals/personal/{mealId}
X-User-Id: 1
```

成功：HTTP `200`，无响应体。

餐食不存在或不属于当前用户时：

```json
{ "message": "个人餐食不存在或无权限删除" }
```

### 6.5 查询公共餐食

```http
GET /api/v1/diet/meals/public
```

请求头 `X-User-Id` 不是必需的。成功响应为 `MealResponse[]`，没有数据时返回 `[]`。

## 7. 槽位选项接口

### 7.1 查询全部启用标签

```http
GET /api/v1/diet/slot-options
```

成功响应：

```json
{
  "mealTime": ["早餐", "早午餐", "午餐", "下午茶", "晚餐", "夜宵", "加餐", "三餐"],
  "mood": ["疲惫", "烦躁", "开心"],
  "scene": ["工作", "校园", "家里"],
  "healthGoal": ["减脂", "清淡", "养胃"],
  "cuisine": ["川菜", "粤菜", "湘菜"],
  "taste": ["清淡", "辣", "微辣"],
  "convenience": ["快速", "慢享", "外带方便"]
}
```

上例为截断示例，实际返回数据库中所有启用值。响应键固定为七个标准字段，顺序为 `mealTime`、`mood`、`scene`、`healthGoal`、`cuisine`、`taste`、`convenience`。

## 8. 反馈接口

### 8.1 保存推荐反馈

```http
POST /api/v1/diet/feedback
Content-Type: application/json
X-User-Id: 1
```

请求体：

```ts
export interface FeedbackRequest {
  sessionId: string
  itemId?: number | null
  action: string
  rating?: number | null
  reason?: string | null
}
```

```json
{
  "sessionId": "sess_6d407ceb0da44960bd94ac9d42ac2fa0",
  "itemId": 2,
  "action": "LIKE",
  "rating": 5,
  "reason": "符合清淡和快速的需求"
}
```

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `sessionId` | 是 | 推荐所在的会话 ID |
| `itemId` | 否 | 推荐餐食 ID；整轮反馈时可为空 |
| `action` | 是 | 反馈动作，不能为空 |
| `rating` | 否 | 评分；当前服务未强制范围，评估时会截断到 `0` 至 `5` |
| `reason` | 否 | 反馈原因，数据库字段上限 512 字符 |

评估服务能够识别的动作包括：

- 正向：`LIKE`、`UP`、`ADOPT`、`ACCEPT`
- 负向：`DISLIKE`、`DOWN`、`REJECT`
- 换一批：`SWITCH`、`CHANGE`、`REFRESH`

接口本身当前只校验 `sessionId` 和 `action` 非空，不限制 `action` 枚举，也没有校验会话或餐食是否真实存在。

成功：HTTP `200`，无响应体。

## 9. Trace 调试接口

这些接口用于后台调试、人工标注和质量评估，不建议暴露给普通用户页面。所有查询都会按 `X-User-Id` 隔离数据。

### 9.1 查询单条 Trace

```http
GET /api/v1/diet/debug/traces/{traceId}
X-User-Id: 1
```

成功响应：一个 `RequestTrace` 对象。

当前实现中，如果 Trace 不存在或不属于当前用户，Controller 会返回 `null`；实际 HTTP 表现通常是 `200` 且响应体为空，而不是 `404`。前端必须允许空响应。

### 9.2 查询会话下的 Trace

```http
GET /api/v1/diet/debug/sessions/{sessionId}/traces?limit=50
X-User-Id: 1
```

| 查询参数 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `limit` | 否 | `200` | 返回数量；后端会限制到 `1` 至 `1000` |

成功响应：`RequestTrace[]`，按 `createdAt`、`id` 倒序排列。

### 9.3 按时间范围查询 Trace

```http
GET /api/v1/diet/debug/traces?startAt=2026-08-01T00:00:00&endAt=2026-08-11T00:00:00&onlyUnlabeled=false&limit=50
X-User-Id: 1
```

| 查询参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `startAt` | ISO datetime | 是 | - | 开始时间，包含该时刻 |
| `endAt` | ISO datetime | 是 | - | 结束时间，不包含该时刻 |
| `onlyUnlabeled` | boolean | 否 | `false` | 是否只查询三个标注字段都为空的 Trace |
| `limit` | integer | 否 | `200` | 后端限制到 `1` 至 `1000` |

`startAt` 必须早于 `endAt`，否则返回“Trace 查询时间范围不合法”。成功响应为按时间倒序排列的 `RequestTrace[]`。

### 9.4 保存 Trace 人工标注

```http
PUT /api/v1/diet/debug/traces/{traceId}/label
Content-Type: application/json
X-User-Id: 1
```

请求体：

```ts
export interface TraceLabelRequest {
  expectedIntent?: Intent | null
  expectedSlots?: SlotBundle | null
  expectedClarifyAction?: 'ASK' | 'READY' | null
  labelNote?: string | null
}
```

```json
{
  "expectedIntent": "MEAL_RECOMMENDATION",
  "expectedSlots": {
    "mealTime": ["晚餐"],
    "mood": [],
    "scene": [],
    "healthGoal": ["清淡"],
    "cuisine": [],
    "taste": [],
    "convenience": ["快速"]
  },
  "expectedClarifyAction": "READY",
  "labelNote": "意图与槽位正确"
}
```

四个字段都允许为空；提交 `null` 可清空对应标注值。成功：HTTP `200`，无响应体。

Trace 不存在或不属于当前用户时返回“Trace 不存在或无权限标注”。

## 10. 评估接口

### 10.1 生成评估报告

```http
POST /api/v1/diet/evaluations
Content-Type: application/json
X-User-Id: 1
```

请求体：

```ts
export interface EvaluationRequest {
  startAt: string
  endAt: string
  includeLlmJudge?: boolean | null
  limit?: number | null
}
```

```json
{
  "startAt": "2026-08-01T00:00:00",
  "endAt": "2026-08-11T00:00:00",
  "includeLlmJudge": false,
  "limit": 100
}
```

| 字段 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `startAt` | 是 | - | 评估开始时间，必须早于 `endAt` |
| `endAt` | 是 | - | 评估结束时间 |
| `includeLlmJudge` | 否 | `false` | 是否额外调用大模型评价解释质量和自然度；开启会增加耗时和调用成本 |
| `limit` | 否 | `1000` | 本次最多读取的 Trace 数；最终仍受 Trace 查询的 `1` 至 `1000` 限制 |

响应类型：

```ts
export interface EvaluationReport {
  startAt: string
  endAt: string
  totalTraces: number
  labeledTraces: number
  avgScore: number | null
  metricAverages: Record<string, number>
  traceResults: TraceEvaluationResult[]
}

export interface TraceEvaluationResult {
  traceId: string
  sessionId: string
  createdAt: string
  score: number | null
  ruleScore: number | null
  llmJudgeScore: number | null
  userFeedbackScore: number | null
  metrics: Record<string, number | null>
  detail: Record<string, unknown>
}
```

响应示例：

```json
{
  "startAt": "2026-08-01T00:00:00",
  "endAt": "2026-08-11T00:00:00",
  "totalTraces": 2,
  "labeledTraces": 1,
  "avgScore": 91.25,
  "metricAverages": {
    "intentAccuracy": 1.0,
    "latencyMs": 2680.0,
    "latencyScore": 1.0,
    "safetyCompliance": 1.0,
    "hallucinationControl": 1.0
  },
  "traceResults": [
    {
      "traceId": "trace_f2e72bb82d084da79b026698956ce734",
      "sessionId": "sess_6d407ceb0da44960bd94ac9d42ac2fa0",
      "createdAt": "2026-08-10T14:30:00",
      "score": 92.5,
      "ruleScore": 95.0,
      "llmJudgeScore": null,
      "userFeedbackScore": 100.0,
      "metrics": {
        "intentAccuracy": 1.0,
        "slotAccuracy": 1.0,
        "clarifyNecessityAccuracy": null,
        "tokenCost": 860.0,
        "tokenCostScore": 1.0,
        "latencyMs": 2680.0,
        "latencyScore": 1.0,
        "fallbackRate": 0.0,
        "fallbackScore": 1.0,
        "safetyCompliance": 1.0,
        "hallucinationControl": 1.0,
        "multiTurnConsistency": null
      },
      "detail": {}
    }
  ]
}
```

指标集合会根据是否存在人工标注、模型 token 数据、用户反馈以及是否启用 LLM Judge 动态变化，前端不要假设每个指标一定存在或一定非空。

## 11. 前端 TypeScript 汇总

```ts
export type SourceMode = 'PERSONAL' | 'PUBLIC'

export type Intent =
  | 'MEAL_RECOMMENDATION'
  | 'CLARIFY_NEEDED'
  | 'MEAL_ADJUST'
  | 'MEAL_PLAN'
  | 'HEALTH_RISK'
  | 'OTHER'

export type ClarifyAction = 'ASK' | 'READY'

export interface SlotBundle {
  mealTime: string[]
  mood: string[]
  scene: string[]
  healthGoal: string[]
  cuisine: string[]
  taste: string[]
  convenience: string[]
}

export interface MealRequest extends SlotBundle {
  name: string
}

export interface MealResponse extends SlotBundle {
  id: number
  sourceType: SourceMode
  name: string
  matchScore: number
}

export interface ChatRequest {
  sessionId?: string | null
  message: string
  sourceMode: SourceMode
  context?: Record<string, unknown> | null
}

export interface ChatResponse {
  sessionId: string
  traceId: string
  responseType: 'ANSWER' | 'CLARIFY'
  speechText: string
  displayBlocks: MealResponse[]
  nextAction: 'WAIT_USER' | 'ASK_CLARIFY'
  clarifyQuestion: string | null
  missingSlots: string[]
}
```

## 12. 当前实现中需要注意的问题

1. 后端未配置 CORS，Vue 本地开发应使用 Vite 代理，或由后端补充明确的跨域配置。
2. `DietExceptionHandler` 的 `basePackages` 与实际包名不一致，统一业务错误结构当前可能不生效。
3. `X-User-Id` 没有真实鉴权能力，上线前应替换为从认证身份中获取用户 ID。
4. 同一个 `sessionId` 会固定首次保存的 `sourceMode`；切换数据源必须新建会话。
5. `/chat` 是同步接口，不是 SSE 流式接口，前端需等待完整 JSON 响应。
6. 删除、反馈、Trace 标注成功返回 `200` 空响应体，Axios 调用方不应强制解析业务对象。
7. 当前配置文件中包含明文数据库密码和大模型 API Key，部署或提交代码前应迁移到环境变量，并立即轮换已经暴露的密钥。
