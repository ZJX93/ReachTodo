// 跨模块共享的领域类型（前端单一真相源）。
// 后端对应 Pydantic schema / SQLAlchemy 模型；此处仅声明前端使用到的字段。

export interface User {
  id: number
  username: string
  email: string | null
  created_at: string
}

export type TaskStatus = 'todo' | 'done'
export type Priority = 'low' | 'normal' | 'high' | 'urgent'
export type Importance = 'low' | 'normal' | 'high'
export type Recurrence = 'none' | 'daily' | 'weekly' | 'monthly'

export interface Task {
  id: number
  user_id: number
  category_id: number
  goal_id: number | null
  parent_id: number | null
  title: string
  note: string | null
  priority: Priority
  importance: Importance
  recurrence: Recurrence
  status: TaskStatus
  due_date: string | null
  due_time: string | null
  sort_order: number
  created_at: string
  completed_at: string | null
  // 关联展示字段（后端聚合返回，可能为空）
  category_name?: string | null
  category_color?: string | null
  category_icon?: string | null
  goal_title?: string | null
}

// 农历 / 黄历数据（与 services/lunar.js 的 emptyLunar 字段对齐）
export interface LunarData {
  lunar: string
  term: string
  festival: string
  lunarYear: string
  lunarMonth: string
  lunarDay: string
  ganzhiYear: string
  shengxiao: string
  yearShengxiao: string
  xingzuo: string
  yi: string[]
  ji: string[]
  yuexiang: string
  wuhou: string
  xi: string
  yanggui: string
  yingui: string
  fu: string
  cai: string
  daysOfYear: string
  weekOfYear: string
}

export interface HolidayInfo {
  name: string
  isOffDay: boolean
}

export type WeekStart = 'sun' | 'mon'
export type LunarSource = 'backend' | 'custom'

export interface Settings {
  defaultFocusMinutes: number
  shortBreakMinutes: number
  longBreakMinutes: number
  longBreakInterval: number
  weekStart: WeekStart
  timezone: string
  lunarSource: LunarSource
  lunarApiBase: string
  holidayApiBase: string
  lunarApiKey: string
}

// —— 枚举（与后端 common 对齐）——
export type GoalStatus = 'active' | 'done'
export type RecordType = 'diary' | 'worklog' | 'note'
export type TemplateType = 'diary' | 'worklog' | 'note'

// —— 实体类型（与后端 schema 对齐）——
export interface Category {
  id: number
  user_id: number
  name: string
  color: string
  icon: string
  sort_order?: number
}

export interface Subtask {
  id: number
  title: string
  status: TaskStatus
}

export interface RecordItem {
  id: number
  user_id: number
  type: RecordType
  title: string
  content: string | null
  mood: string | null
  weather: string | null
  location: string | null
  tags: string | null
  book_title: string | null
  book_author: string | null
  project: string | null
  record_date: string
  record_time: string | null
  created_at: string
  updated_at: string
}

export interface Template {
  id: number
  user_id: number | null
  type: TemplateType
  name: string
  icon: string
  content: string | null
  is_preset: boolean
}

// 目标看板条目（含聚合统计），前端 /goals/board 返回
export interface Goal {
  id: number
  user_id: number
  title: string
  description: string | null
  deadline: string | null
  status: GoalStatus
  created_at: string
  total: number
  done: number
  overdue: number
  progress: number
}

export interface CalendarDay {
  date: string
  total: number
  diary: number
  worklog: number
  note: number
  tasks: number
}

// CalendarGrid 单日聚合的精简形态（仅计数）
export interface DayAgg {
  diary: number
  worklog: number
  note: number
  tasks: number
}

// 日历格子使用的农历精简形态（来自 LunarData 的结构子类型）
export interface LunarDay {
  lunar: string
  term: string
  festival: string
}

// 侧栏维度分类汇总项（/tasks/summary）
export interface SummaryCategory {
  category_id: number
  name: string
  color: string
  todo: number
}

export interface Summary {
  today_todo?: number
  total_todo?: number
  categories: SummaryCategory[]
}

// TaskForm 提交的任务草稿
export interface TaskDraft {
  title: string
  category_id: number
  goal_id: number | null
  priority: Priority
  importance: Importance
  recurrence: Recurrence
  note: string | null
  due_date: string | null
  due_time: string | null
}
