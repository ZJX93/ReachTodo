import api from '../api'

// 习惯打卡：类型定义与接口封装。
//
// 字段与后端 server/app/schemas/habit.py 严格对齐（snake_case 零转换），
// 这样同步端点可以做无映射的字段透传。
//
// 对外暴露的 id 一律是 client_id（字符串 uuid），不是数据库自增主键 ——
// 前端全程只与 client_id 打交道，与后端「离线优先」的设计保持一致。

export type HabitType = 'check' | 'count' | 'duration' | 'timerange'
export type HabitFrequency = 'daily' | 'weekday' | 'weekend' | 'custom'
export type HabitSize = 'sm' | 'md' | 'lg'

export interface Habit {
  id: string
  name: string
  /** 图标集的 key（如 water / book），不存 emoji —— 各端自行渲染 */
  icon: string
  color: string
  type: HabitType
  target: number
  unit: string
  frequency: HabitFrequency
  weekdays: number[]
  size: HabitSize
  category_id: string | null
  goal_id: number | null
  start_date: string
  archived: boolean
  sort_order: number
  created_at?: string | null
  updated_at?: string | null
  deleted_at?: string | null
  // —— 列表接口一次带出的计算字段，省掉前端 N 次请求 ——
  streak: number
  best_streak: number
  done_today: boolean
  value_today: number
}

export interface Checkin {
  id: string
  habit_id: string
  checkin_date: string
  value: number
  start_time?: string | null
  end_time?: string | null
  note?: string | null
  created_at?: string | null
  updated_at?: string | null
  done: boolean
}

export interface Mood {
  id: string
  date: string
  score: number
  note?: string | null
  updated_at?: string | null
}

/** /habits/today 返回的习惯项：习惯本体 + 今日进度与打卡记录 */
export interface TodayItem extends Habit {
  progress: number
  checkin: Checkin | null
}

export interface Today {
  date: string
  total: number
  done: number
  percent: number
  streak: number
  habits: TodayItem[]
  mood: number | null
}

/** 热力图单日：rate 是 0~1 的完成度，部分完成也能体现深浅 */
export interface HeatCell {
  date: string
  total: number
  done: number
  rate: number
}

export interface HabitStats {
  habit_id: string
  streak: number
  best_streak: number
  total_checkins: number
  rate_30: number
  rate_all: number
  last_30: { date: string; value: number; done: boolean }[]
}

export interface HabitDraft {
  name: string
  icon: string
  color: string
  type: HabitType
  target: number
  unit: string
  frequency: HabitFrequency
  weekdays: number[]
  size: HabitSize
  category_id?: string | null
  start_date?: string
  sort_order?: number
}

export interface CheckinPayload {
  /** 不传即今天；传了即为补卡 */
  date?: string
  /** 语义随习惯类型而定；传 0 表示取消打卡 */
  value?: number
  start_time?: string
  end_time?: string
  note?: string
}

export const habitsApi = {
  list: (includeArchived = true) =>
    api.get<Habit[]>('/habits', { params: { include_archived: includeArchived } }),
  create: (draft: HabitDraft) => api.post<Habit>('/habits', draft),
  // 后端用 model_dump(exclude_unset=True)，因此这里可以只传要改的字段
  update: (id: string, patch: Partial<HabitDraft> & { archived?: boolean }) =>
    api.put<Habit>(`/habits/${id}`, patch),
  remove: (id: string, purge = false) =>
    api.delete(`/habits/${id}`, { params: { purge } }),
  checkin: (id: string, payload: CheckinPayload) =>
    api.post<Checkin>(`/habits/${id}/checkin`, payload),
  checkins: (id: string, days = 120) =>
    api.get<Checkin[]>(`/habits/${id}/checkins`, { params: { days } }),
  stats: (id: string) => api.get<HabitStats>(`/habits/${id}/stats`),
  today: () => api.get<Today>('/habits/today'),
  heatmap: (days = 119) => api.get<HeatCell[]>('/habits/heatmap', { params: { days } }),
  moods: (days = 120) => api.get<Mood[]>('/habits/moods', { params: { days } }),
  setMood: (payload: { date?: string; score: number; note?: string }) =>
    api.post<Mood>('/habits/moods', payload),
}

// ---------------------------------------------------------------------------
// 展示层常量
// ---------------------------------------------------------------------------

/**
 * 图标集：key → emoji。
 *
 * 数据库里存的是 key 而不是 emoji 本身 —— 三端（Web / Android / Harmony）
 * 各自把它映射成自己的资源，避免字体覆盖不一致导致显示成豆腐块。
 */
export const HABIT_ICONS: { key: string; emoji: string }[] = [
  { key: 'smile', emoji: '😊' },
  { key: 'water', emoji: '💧' },
  { key: 'book', emoji: '📖' },
  { key: 'run', emoji: '🏃' },
  { key: 'gym', emoji: '💪' },
  { key: 'sleep', emoji: '😴' },
  { key: 'meditate', emoji: '🧘' },
  { key: 'code', emoji: '💻' },
  { key: 'write', emoji: '✍️' },
  { key: 'music', emoji: '🎵' },
  { key: 'heart', emoji: '❤️' },
  { key: 'sun', emoji: '☀️' },
  { key: 'moon', emoji: '🌙' },
  { key: 'food', emoji: '🍎' },
  { key: 'coffee', emoji: '☕' },
  { key: 'star', emoji: '⭐' },
]

export function iconEmoji(key: string): string {
  return HABIT_ICONS.find((i) => i.key === key)?.emoji ?? '😊'
}

/** 习惯配色，与后端默认色 #7C9A92 同一族系 */
export const HABIT_COLORS = [
  '#7C9A92',
  '#2563eb',
  '#06b6d4',
  '#14b8a6',
  '#8b5cf6',
  '#f97316',
  '#ef4444',
  '#22c55e',
  '#eab308',
  '#ec4899',
]

export const TYPE_LABEL: Record<HabitType, string> = {
  check: '打勾',
  count: '计数',
  duration: '时长',
  timerange: '时间段',
}

export const FREQ_LABEL: Record<HabitFrequency, string> = {
  daily: '每天',
  weekday: '工作日',
  weekend: '周末',
  custom: '自选',
}

export const WEEKDAY_LABEL = ['日', '一', '二', '三', '四', '五', '六']

/** 今日心情的 1~5 分档位 */
export const MOODS = [
  { score: 1, emoji: '😞', label: '很差' },
  { score: 2, emoji: '🙁', label: '偏低' },
  { score: 3, emoji: '😐', label: '一般' },
  { score: 4, emoji: '🙂', label: '不错' },
  { score: 5, emoji: '😄', label: '很好' },
]

/** 该习惯在指定日期是否需要执行 —— 与后端 is_scheduled_on 语义保持一致 */
export function isScheduledOn(habit: Habit, date: Date): boolean {
  if (habit.frequency === 'daily') return true
  const wd = date.getDay() // 0=周日 … 6=周六
  if (habit.frequency === 'weekday') return wd >= 1 && wd <= 5
  if (habit.frequency === 'weekend') return wd === 0 || wd === 6
  return (habit.weekdays || []).includes(wd)
}

export function toISODate(d: Date): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}
