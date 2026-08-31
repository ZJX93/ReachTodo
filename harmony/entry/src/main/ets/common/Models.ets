/**
 * 与后端 `server/app/schemas/` 一一对应的数据模型。
 *
 * 约定：
 * - 字段名保持后端的 snake_case，**不做驼峰转换**。转换层是纯粹的心智负担与
 *   bug 温床（漏一个字段就是静默 undefined），直接对齐反而最省事；
 *   唯一例外是 `/api/settings` 的偏好体，后端本身就用 camelCase。
 * - 日期/时间统一用 string（`YYYY-MM-DD` / `HH:mm` / ISO8601），
 *   渲染时再格式化，避免序列化两头不一致。
 * - 全部用 interface 而非 class：这些对象只经由 `JSON.parse` 产生，
 *   class 会带来「实例方法丢失」的错觉。
 */

// ---------------------------------------------------------------------------
// 认证
// ---------------------------------------------------------------------------
export interface UserOut {
  id: number;
  username: string;
  email?: string | null;
  created_at?: string | null;
}

export interface TokenOut {
  access_token: string;
  token_type: string;
  user?: UserOut | null;
}

export interface UserCreate {
  username: string;
  password: string;
  email?: string | null;
}

export interface UserUpdate {
  email?: string | null;
}

export interface PasswordChange {
  old_password: string;
  new_password: string;
}

export interface OkResponse {
  ok: boolean;
}

// ---------------------------------------------------------------------------
// 维度 / 目标
// ---------------------------------------------------------------------------
export interface CategoryOut {
  id: number;
  user_id: number;
  name: string;
  color: string;
  icon: string;
  sort_order: number;
}

export interface GoalOut {
  id: number;
  user_id: number;
  title: string;
  description?: string | null;
  deadline?: string | null;
  status: string;
  created_at?: string | null;
}

export interface GoalBoardItem {
  id: number;
  user_id: number;
  title: string;
  description?: string | null;
  deadline?: string | null;
  status: string;
  created_at?: string | null;
  total: number;
  done: number;
  overdue: number;
  progress: number;
}

export interface GoalCreate {
  title: string;
  description?: string | null;
  deadline?: string | null;
}

export interface GoalUpdate {
  title?: string;
  description?: string | null;
  deadline?: string | null;
  status?: string;
}

// ---------------------------------------------------------------------------
// 任务
// ---------------------------------------------------------------------------
export interface TaskOut {
  id: number;
  user_id: number;
  category_id: number;
  goal_id?: number | null;
  parent_id?: number | null;
  title: string;
  note?: string | null;
  priority: string;
  importance: string;
  recurrence: string;
  status: string;
  due_date?: string | null;
  due_time?: string | null;
  sort_order: number;
  created_at?: string | null;
  completed_at?: string | null;
  remind_before_minutes?: number | null;
  deleted_at?: string | null;
  category_name?: string | null;
  category_color?: string | null;
  category_icon?: string | null;
  goal_title?: string | null;
  tags: string[];
}

export interface TaskCreate {
  title: string;
  category_id: number;
  goal_id?: number | null;
  parent_id?: number | null;
  note?: string | null;
  priority?: string;
  importance?: string;
  recurrence?: string;
  due_date?: string | null;
  due_time?: string | null;
  remind_before_minutes?: number | null;
  tags?: string[];
}

export interface TaskUpdate {
  title?: string;
  category_id?: number;
  goal_id?: number | null;
  parent_id?: number | null;
  note?: string | null;
  priority?: string;
  importance?: string;
  recurrence?: string;
  status?: string;
  due_date?: string | null;
  due_time?: string | null;
  remind_before_minutes?: number | null;
  tags?: string[];
}

/** GET /api/tasks 的查询条件。全部可选，undefined 的键不会出现在 URL 上。 */
export interface TaskQuery {
  category_id?: number;
  goal_id?: number;
  status?: string;
  priority?: string;
  importance?: string;
  q?: string;
  tag?: string[];
  due_from?: string;
  due_to?: string;
  overdue?: boolean;
  parent_id?: number;
  top_level?: boolean;
  sort?: string;
  limit?: number;
  offset?: number;
}

export interface TaskSummaryCategory {
  category_id: number;
  name: string;
  color: string;
  icon: string;
  todo: number;
  done: number;
}

export interface TaskSummary {
  categories: TaskSummaryCategory[];
  total_todo: number;
  today_todo: number;
  total_done: number;
  overdue: number;
}

export interface MatrixQuadrant {
  key: string;
  title: string;
  sub: string;
  tasks: TaskOut[];
}

export type BulkAction = string;

export interface TaskBulkRequest {
  ids: number[];
  action: BulkAction;
  category_id?: number;
  goal_id?: number | null;
  priority?: string;
  importance?: string;
  tags?: string[];
}

export interface TaskBulkResult {
  action: string;
  requested: number;
  affected: number;
  skipped: number;
}

// ---------------------------------------------------------------------------
// 标签
// ---------------------------------------------------------------------------
export interface TagOut {
  id: number;
  user_id: number;
  name: string;
  color: string;
  task_count: number;
}

export interface TagCreate {
  name: string;
  color?: string;
}

export interface TagUpdate {
  name?: string;
  color?: string;
}

// ---------------------------------------------------------------------------
// 记录 / 模板
// ---------------------------------------------------------------------------
export interface RecordOut {
  id: number;
  user_id: number;
  type: string;
  title: string;
  content?: string | null;
  mood?: string | null;
  tags?: string | null;
  book_title?: string | null;
  book_author?: string | null;
  project?: string | null;
  record_date: string;
  record_time?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface RecordCreate {
  type: string;
  title?: string | null;
  content?: string | null;
  mood?: string | null;
  tags?: string | null;
  book_title?: string | null;
  book_author?: string | null;
  project?: string | null;
  record_date?: string | null;
  record_time?: string | null;
  template_id?: number | null;
}

export interface RecordUpdate {
  type?: string;
  title?: string | null;
  content?: string | null;
  mood?: string | null;
  tags?: string | null;
  book_title?: string | null;
  book_author?: string | null;
  project?: string | null;
  record_date?: string | null;
  record_time?: string | null;
}

/** GET /api/records 的查询条件。 */
export interface RecordQuery {
  type?: string;
  q?: string;
  date?: string;
  from_date?: string;
  to_date?: string;
  limit?: number;
  offset?: number;
}

export interface CalendarDay {
  date: string;
  total: number;
  diary: number;
  worklog: number;
  note: number;
  tasks: number;
}

export interface TemplateOut {
  id: number;
  user_id?: number | null;
  type: string;
  name: string;
  icon: string;
  content?: string | null;
  is_preset: boolean;
}

// ---------------------------------------------------------------------------
// 专注 / 统计
// ---------------------------------------------------------------------------
export interface FocusSessionOut {
  id: number;
  user_id: number;
  task_id?: number | null;
  minutes: number;
  started_at?: string | null;
}

export interface FocusSessionCreate {
  task_id?: number | null;
  minutes: number;
}

export interface CategoryStat {
  name: string;
  color: string;
  icon: string;
  todo: number;
  done: number;
}

export interface GoalProgress {
  id: number;
  title: string;
  total: number;
  done: number;
  progress: number;
}

export interface StatsSummary {
  total_todo: number;
  total_done: number;
  week_completed: number;
  streak: number;
  per_category: CategoryStat[];
  goals_progress: GoalProgress[];
  focus_minutes_today: number;
  focus_minutes_week: number;
}

// ---------------------------------------------------------------------------
// 农历 / 节假日
// ---------------------------------------------------------------------------
/** `/api/lunar/{date}` 透传 apihz 原始字段；离线计算也填充同名字段。 */
export interface LunarInfo {
  nyue?: string | null;          // 农历月，如「六月」
  nri?: string | null;           // 农历日，如「十五」
  jieqi?: string | null;         // 节气名
  JIEQIDAYS?: string | null;     // "1" = 今天正是该节气当日
  jieri?: string | null;         // 节日
  nnian?: string | null;         // 农历年（中文数字）
  YEARGANZHI?: string | null;    // 年干支
  shengxiao?: string | null;     // 年生肖
  DAYSHENGXIAO?: string | null;  // 日生肖
  xingzuo?: string | null;
  yi?: string | null;            // 宜（| 分隔）
  ji?: string | null;            // 忌（| 分隔）
  YUEXIANG?: string | null;      // 月相
  WUHOU?: string | null;         // 物候
  DAYPOSITIONXI?: string | null;
  DAYPOSITIONYANGGUI?: string | null;
  DAYPOSITIONYINGUI?: string | null;
  DAYPOSITIONFU?: string | null;
  DAYPOSITIONCAI?: string | null;
  DAYSINYEAR?: string | null;
  YLWEEKNOY?: string | null;
}

export interface HolidayInfo {
  name?: string | null;
  isOffDay: boolean;
}

// ---------------------------------------------------------------------------
// 偏好（唯一使用 camelCase 的模型，与后端 schemas/setting.py 对齐）
// ---------------------------------------------------------------------------
export interface AppSettings {
  focusMinutes: number;
  focusBreakMinutes: number;
  weekStart: string;              // sun | mon
  timezone: string;
  theme: string;                  // system | light | dark
  accentColor: string;
  lunarSource: string;            // backend | custom
  lunarApiBase: string;
  holidayApiBase: string;
  lunarApiKey: string;
  defaultRemindBeforeMinutes: number;
  localReminderEnabled: boolean;
  showCompleted: boolean;
  defaultView: string;            // dashboard | tasks | matrix | calendar | goals
}

export interface SettingsOut {
  settings: AppSettings;
  feed_token: string;
  feed_path: string;
  updated_at?: string | null;
}

/** PUT /api/settings 的增量请求体：只带要改的键。 */
export interface SettingsPatch {
  focusMinutes?: number;
  focusBreakMinutes?: number;
  weekStart?: string;
  timezone?: string;
  theme?: string;
  accentColor?: string;
  lunarSource?: string;
  lunarApiBase?: string;
  holidayApiBase?: string;
  lunarApiKey?: string;
  defaultRemindBeforeMinutes?: number;
  localReminderEnabled?: boolean;
  showCompleted?: boolean;
  defaultView?: string;
}

/** 服务端权威默认值的本地副本：首次启动、离线启动时兜底。 */
export const DEFAULT_SETTINGS: AppSettings = {
  focusMinutes: 25,
  focusBreakMinutes: 5,
  weekStart: 'sun',
  timezone: '',
  theme: 'system',
  accentColor: '#3B82F6',
  lunarSource: 'backend',
  lunarApiBase: '',
  holidayApiBase: '',
  lunarApiKey: '',
  defaultRemindBeforeMinutes: 10,
  localReminderEnabled: true,
  showCompleted: false,
  defaultView: 'dashboard',
};

// ---------------------------------------------------------------------------
// 回收站 / 设备
// ---------------------------------------------------------------------------
export interface TrashItem {
  kind: string;      // task | record
  id: number;
  title: string;
  subtitle?: string | null;
  deleted_at?: string | null;
}

export interface TrashList {
  items: TrashItem[];
  retention_days: number;
}

export interface DeviceRegister {
  token: string;
  platform: string;
  device_name?: string | null;
}
