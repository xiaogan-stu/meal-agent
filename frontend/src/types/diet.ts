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

export type SlotKey = keyof SlotBundle
export type SlotOptionMap = SlotBundle

export interface MealRequest extends SlotBundle {
  name: string
}

export interface MealResponse extends SlotBundle {
  id: number
  sourceType: SourceMode
  name: string
  matchScore: number
}

export interface CreateSessionResponse {
  sessionId: string
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

export interface FeedbackRequest {
  sessionId: string
  itemId?: number | null
  action: string
  rating?: number | null
  reason?: string | null
}

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

export interface TraceLabelRequest {
  expectedIntent?: Intent | null
  expectedSlots?: SlotBundle | null
  expectedClarifyAction?: ClarifyAction | null
  labelNote?: string | null
}

export interface EvaluationRequest {
  startAt: string
  endAt: string
  includeLlmJudge?: boolean | null
  limit?: number | null
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

export interface EvaluationReport {
  startAt: string
  endAt: string
  totalTraces: number
  labeledTraces: number
  avgScore: number | null
  metricAverages: Record<string, number>
  traceResults: TraceEvaluationResult[]
}

export interface UiChatMessage {
  id: string
  role: 'user' | 'assistant'
  text: string
  sessionId: string | null
  traceId: string | null
  responseType: 'ANSWER' | 'CLARIFY' | null
  meals: MealResponse[]
  missingSlots: string[]
}