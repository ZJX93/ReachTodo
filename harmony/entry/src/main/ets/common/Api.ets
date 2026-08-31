/**
 * 后端接口清单（薄封装层）。
 *
 * 只做「路径 + 查询串 + 类型」三件事，不含任何业务判断——业务判断放在 stores 里。
 * 这样接口变更时改动面收敛在本文件，页面代码不受影响。
 */
import { ApiClient, Query } from './ApiClient';
import {
  AppSettings,
  CalendarDay,
  CategoryOut,
  DeviceRegister,
  FocusSessionCreate,
  FocusSessionOut,
  GoalBoardItem,
  GoalCreate,
  GoalOut,
  GoalUpdate,
  HolidayInfo,
  LunarInfo,
  MatrixQuadrant,
  OkResponse,
  PasswordChange,
  RecordCreate,
  RecordOut,
  RecordQuery,
  RecordUpdate,
  SettingsOut,
  SettingsPatch,
  StatsSummary,
  TagCreate,
  TagOut,
  TagUpdate,
  TaskBulkRequest,
  TaskBulkResult,
  TaskCreate,
  TaskOut,
  TaskQuery,
  TaskSummary,
  TaskUpdate,
  TemplateOut,
  TokenOut,
  TrashList,
  UserCreate,
  UserOut,
  UserUpdate,
} from './Models';

export class Api {
  // ------------------------------------------------------------------ 认证
  /** 注册。后端直接返回令牌，注册成功即登录。 */
  static register(body: UserCreate): Promise<TokenOut> {
    return ApiClient.post<TokenOut>('/api/auth/register', body, false);
  }

  static login(body: UserCreate): Promise<TokenOut> {
    return ApiClient.post<TokenOut>('/api/auth/login', body, false);
  }

  static me(): Promise<UserOut> {
    return ApiClient.get<UserOut>('/api/auth/me');
  }

  static updateMe(body: UserUpdate): Promise<UserOut> {
    return ApiClient.patch<UserOut>('/api/auth/me', body);
  }

  static changePassword(body: PasswordChange): Promise<OkResponse> {
    return ApiClient.post<OkResponse>('/api/auth/me/password', body);
  }

  // ------------------------------------------------------------------ 维度
  static categories(): Promise<CategoryOut[]> {
    return ApiClient.get<CategoryOut[]>('/api/categories');
  }

  // ------------------------------------------------------------------ 任务
  static tasks(q?: TaskQuery): Promise<TaskOut[]> {
    const query = new Query();
    if (q) {
      query.num('category_id', q.category_id)
        .num('goal_id', q.goal_id)
        .str('status', q.status)
        .str('priority', q.priority)
        .str('importance', q.importance)
        .str('q', q.q)
        .list('tag', q.tag)
        .str('due_from', q.due_from)
        .str('due_to', q.due_to)
        .bool('overdue', q.overdue)
        .num('parent_id', q.parent_id)
        .bool('top_level', q.top_level)
        .str('sort', q.sort)
        .num('limit', q.limit)
        .num('offset', q.offset);
    }
    return ApiClient.get<TaskOut[]>('/api/tasks' + query.build());
  }

  static taskSummary(): Promise<TaskSummary> {
    return ApiClient.get<TaskSummary>('/api/tasks/summary');
  }

  static matrix(): Promise<MatrixQuadrant[]> {
    return ApiClient.get<MatrixQuadrant[]>('/api/tasks/matrix');
  }

  static createTask(body: TaskCreate): Promise<TaskOut> {
    return ApiClient.post<TaskOut>('/api/tasks', body);
  }

  static updateTask(id: number, body: TaskUpdate): Promise<TaskOut> {
    return ApiClient.put<TaskOut>(`/api/tasks/${id}`, body);
  }

  /** 默认软删除（进回收站）；`purge=true` 直接物理删除。 */
  static deleteTask(id: number, purge: boolean = false): Promise<void> {
    const query = new Query().bool('purge', purge ? true : undefined);
    return ApiClient.del(`/api/tasks/${id}` + query.build());
  }

  static bulkTasks(body: TaskBulkRequest): Promise<TaskBulkResult> {
    return ApiClient.post<TaskBulkResult>('/api/tasks/bulk', body);
  }

  // ------------------------------------------------------------------ 标签
  static tags(): Promise<TagOut[]> {
    return ApiClient.get<TagOut[]>('/api/tags');
  }

  static createTag(body: TagCreate): Promise<TagOut> {
    return ApiClient.post<TagOut>('/api/tags', body);
  }

  static updateTag(id: number, body: TagUpdate): Promise<TagOut> {
    return ApiClient.put<TagOut>(`/api/tags/${id}`, body);
  }

  static deleteTag(id: number): Promise<void> {
    return ApiClient.del(`/api/tags/${id}`);
  }

  // ------------------------------------------------------------------ 目标
  static goals(): Promise<GoalOut[]> {
    return ApiClient.get<GoalOut[]>('/api/goals');
  }

  static goalsBoard(): Promise<GoalBoardItem[]> {
    return ApiClient.get<GoalBoardItem[]>('/api/goals/board');
  }

  static createGoal(body: GoalCreate): Promise<GoalOut> {
    return ApiClient.post<GoalOut>('/api/goals', body);
  }

  static updateGoal(id: number, body: GoalUpdate): Promise<GoalOut> {
    return ApiClient.put<GoalOut>(`/api/goals/${id}`, body);
  }

  static deleteGoal(id: number): Promise<void> {
    return ApiClient.del(`/api/goals/${id}`);
  }

  // ------------------------------------------------------------------ 记录
  static records(q?: RecordQuery): Promise<RecordOut[]> {
    const query = new Query();
    if (q) {
      query.str('type', q.type)
        .str('q', q.q)
        .str('date', q.date)
        .str('from_date', q.from_date)
        .str('to_date', q.to_date)
        .num('limit', q.limit)
        .num('offset', q.offset);
    }
    return ApiClient.get<RecordOut[]>('/api/records' + query.build());
  }

  static recordsCalendar(year: number, month: number): Promise<CalendarDay[]> {
    const query = new Query().num('year', year).num('month', month);
    return ApiClient.get<CalendarDay[]>('/api/records/calendar' + query.build());
  }

  static createRecord(body: RecordCreate): Promise<RecordOut> {
    return ApiClient.post<RecordOut>('/api/records', body);
  }

  static updateRecord(id: number, body: RecordUpdate): Promise<RecordOut> {
    return ApiClient.put<RecordOut>(`/api/records/${id}`, body);
  }

  static deleteRecord(id: number): Promise<void> {
    return ApiClient.del(`/api/records/${id}`);
  }

  static templates(): Promise<TemplateOut[]> {
    return ApiClient.get<TemplateOut[]>('/api/templates');
  }

  // ------------------------------------------------------------------ 专注 / 统计
  static createFocus(body: FocusSessionCreate): Promise<FocusSessionOut> {
    return ApiClient.post<FocusSessionOut>('/api/focus', body);
  }

  static focusSessions(): Promise<FocusSessionOut[]> {
    return ApiClient.get<FocusSessionOut[]>('/api/focus');
  }

  static statsSummary(): Promise<StatsSummary> {
    return ApiClient.get<StatsSummary>('/api/stats/summary');
  }

  // ------------------------------------------------------------------ 农历 / 节假日
  static lunar(date: string): Promise<LunarInfo> {
    return ApiClient.get<LunarInfo>(`/api/lunar/${date}`);
  }

  /** 返回 `{"2026-01-01": {name, isOffDay}}` 形态的映射。 */
  static holidays(year: number): Promise<Record<string, HolidayInfo>> {
    return ApiClient.get<Record<string, HolidayInfo>>(`/api/holidays/${year}`);
  }

  // ------------------------------------------------------------------ 偏好
  static settings(): Promise<SettingsOut> {
    return ApiClient.get<SettingsOut>('/api/settings');
  }

  static saveSettings(patch: SettingsPatch): Promise<SettingsOut> {
    return ApiClient.put<SettingsOut>('/api/settings', patch);
  }

  static resetFeedToken(): Promise<SettingsOut> {
    return ApiClient.post<SettingsOut>('/api/settings/feed-token/reset', {} as object);
  }

  // ------------------------------------------------------------------ 回收站
  static trash(kind?: string): Promise<TrashList> {
    const query = new Query().str('kind', kind);
    return ApiClient.get<TrashList>('/api/trash' + query.build());
  }

  static restoreTrash(kind: string, id: number): Promise<void> {
    return ApiClient.postVoid(`/api/trash/${kind}/${id}/restore`, {} as object);
  }

  static purgeTrash(kind: string, id: number): Promise<void> {
    return ApiClient.del(`/api/trash/${kind}/${id}`);
  }

  static emptyTrash(): Promise<void> {
    return ApiClient.del('/api/trash');
  }

  // ------------------------------------------------------------------ 设备推送
  static registerDevice(body: DeviceRegister): Promise<OkResponse> {
    return ApiClient.post<OkResponse>('/api/devices/register', body);
  }

  static unregisterDevice(body: DeviceRegister): Promise<OkResponse> {
    return ApiClient.post<OkResponse>('/api/devices/unregister', body);
  }

  // ------------------------------------------------------------------ 探活
  static health(): Promise<string> {
    return ApiClient.ping();
  }
}

/** 把偏好整体转成增量请求体（全字段提交，语义上等价于覆盖）。 */
export function settingsToPatch(s: AppSettings): SettingsPatch {
  return {
    focusMinutes: s.focusMinutes,
    focusBreakMinutes: s.focusBreakMinutes,
    weekStart: s.weekStart,
    timezone: s.timezone,
    theme: s.theme,
    accentColor: s.accentColor,
    lunarSource: s.lunarSource,
    lunarApiBase: s.lunarApiBase,
    holidayApiBase: s.holidayApiBase,
    lunarApiKey: s.lunarApiKey,
    defaultRemindBeforeMinutes: s.defaultRemindBeforeMinutes,
    localReminderEnabled: s.localReminderEnabled,
    showCompleted: s.showCompleted,
    defaultView: s.defaultView,
  };
}
