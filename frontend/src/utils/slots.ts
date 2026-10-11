import type { MealRequest, SlotBundle, SlotKey } from '../types/diet'

export const SLOT_KEYS: SlotKey[] = [
  'mealTime',
  'mood',
  'scene',
  'healthGoal',
  'cuisine',
  'taste',
  'convenience',
]

export const SLOT_LABELS: Record<SlotKey, string> = {
  mealTime: '餐次',
  mood: '心情',
  scene: '场景',
  healthGoal: '健康目标',
  cuisine: '菜系',
  taste: '口味',
  convenience: '便利性',
}

export function emptySlots(): SlotBundle {
  return {
    mealTime: [],
    mood: [],
    scene: [],
    healthGoal: [],
    cuisine: [],
    taste: [],
    convenience: [],
  }
}

export function emptyMealRequest(): MealRequest {
  return {
    name: '',
    ...emptySlots(),
  }
}

export function collectMealTags(slots: SlotBundle): string[] {
  return SLOT_KEYS.flatMap((key) => slots[key])
}

export function cloneSlots(slots: SlotBundle): SlotBundle {
  return {
    mealTime: [...slots.mealTime],
    mood: [...slots.mood],
    scene: [...slots.scene],
    healthGoal: [...slots.healthGoal],
    cuisine: [...slots.cuisine],
    taste: [...slots.taste],
    convenience: [...slots.convenience],
  }
}