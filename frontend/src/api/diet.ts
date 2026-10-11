import { http } from './http'
import type {
  ChatRequest,
  ChatResponse,
  CreateSessionResponse,
  EvaluationReport,
  EvaluationRequest,
  FeedbackRequest,
  MealRequest,
  MealResponse,
  RequestTrace,
  SlotOptionMap,
  TraceLabelRequest,
} from '../types/diet'

export async function createSession(): Promise<CreateSessionResponse> {
  const response = await http.post<CreateSessionResponse>('/sessions')
  return response.data
}

export async function sendChat(payload: ChatRequest): Promise<ChatResponse> {
  const response = await http.post<ChatResponse>('/chat', payload)
  return response.data
}

export async function getPersonalMeals(): Promise<MealResponse[]> {
  const response = await http.get<MealResponse[]>('/meals/personal')
  return response.data
}

export async function createPersonalMeal(
  payload: MealRequest,
): Promise<MealResponse> {
  const response = await http.post<MealResponse>('/meals/personal', payload)
  return response.data
}

export async function updatePersonalMeal(
  mealId: number,
  payload: MealRequest,
): Promise<MealResponse> {
  const response = await http.put<MealResponse>(
    '/meals/personal/' + String(mealId),
    payload,
  )
  return response.data
}

export async function deletePersonalMeal(mealId: number): Promise<void> {
  await http.delete('/meals/personal/' + String(mealId))
}

export async function getPublicMeals(): Promise<MealResponse[]> {
  const response = await http.get<MealResponse[]>('/meals/public')
  return response.data
}

export async function getSlotOptions(): Promise<SlotOptionMap> {
  const response = await http.get<SlotOptionMap>('/slot-options')
  return response.data
}

export async function saveFeedback(payload: FeedbackRequest): Promise<void> {
  await http.post('/feedback', payload)
}

export async function getTrace(
  traceId: string,
): Promise<RequestTrace | null> {
  const response = await http.get<RequestTrace | ''>(
    '/debug/traces/' + encodeURIComponent(traceId),
  )
  return response.data || null
}

export async function getSessionTraces(
  sessionId: string,
  limit = 50,
): Promise<RequestTrace[]> {
  const response = await http.get<RequestTrace[]>(
    '/debug/sessions/' + encodeURIComponent(sessionId) + '/traces',
    { params: { limit } },
  )
  return response.data
}

export interface TraceQuery {
  startAt: string
  endAt: string
  onlyUnlabeled: boolean
  limit: number
}

export async function getTraces(
  query: TraceQuery,
): Promise<RequestTrace[]> {
  const response = await http.get<RequestTrace[]>('/debug/traces', {
    params: query,
  })
  return response.data
}

export async function updateTraceLabel(
  traceId: string,
  payload: TraceLabelRequest,
): Promise<void> {
  await http.put(
    '/debug/traces/' + encodeURIComponent(traceId) + '/label',
    payload,
  )
}

export async function runEvaluation(
  payload: EvaluationRequest,
): Promise<EvaluationReport> {
  const response = await http.post<EvaluationReport>(
    '/evaluations',
    payload,
  )
  return response.data
}