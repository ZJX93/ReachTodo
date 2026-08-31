/**
 * 本地日程提醒（`reminderAgentManager`）。
 *
 * 为什么必须做本地提醒：云推送（PushKit/FCM）依赖网络与厂商服务，
 * 而「到点提醒」是待办应用的核心承诺——不能因为断网、自建服务器没配推送凭证、
 * 或用户没登录华为账号就失效。本地提醒由系统日程代理托管，
 * **进程被杀、离线、飞行模式下依旧准时**，是提醒能力的地板。
 *
 * 同步策略采用「全量重排」而非增量维护：
 *   cancelAllReminders() → 重新发布最近 N 条
 * 增量维护需要在本地保存 taskId→reminderId 的映射，一旦映射与系统实际状态漂移
 * （应用被清数据、系统重启后 id 复用），就会出现「幽灵提醒」或「提醒丢失」，
 * 排查成本极高。全量重排是幂等的，任何时候执行结果都可预测。
 */
import reminderAgentManager from '@ohos.reminderAgentManager';
import notificationManager from '@ohos.notificationManager';
import common from '@ohos.app.ability.common';
import { AppSettings, TaskOut } from './Models';
import { DateUtil } from './DateUtil';

/** 系统对单个应用的有效提醒数量有上限（约 30 条），只排最近的这些。 */
const MAX_REMINDERS: number = 28;
/** 只为未来 30 天内的任务排程，更远的等下次同步时再排。 */
const HORIZON_DAYS: number = 30;

export class Reminder {
  /** 请求通知授权。未授权时本地提醒会被系统静默丢弃，因此登录后调一次。 */
  static async ensureNotificationPermission(context: common.UIAbilityContext): Promise<void> {
    try {
      const enabled: boolean = await notificationManager.isNotificationEnabled();
      if (!enabled) {
        await notificationManager.requestEnableNotification(context);
      }
    } catch (e) {
      // 用户拒绝或系统不支持：不阻断主流程，云推送仍可作为通道
    }
  }

  /**
   * 按任务列表重排本地提醒。
   *
   * @param tasks 未完成任务（含 due_date 的才会被排程）
   * @param settings 用户偏好，提供全局默认提前量与总开关
   */
  static async sync(tasks: TaskOut[], settings: AppSettings): Promise<number> {
    try {
      await reminderAgentManager.cancelAllReminders();
    } catch (e) {
      // 没有任何已发布提醒时也可能抛错，忽略
    }

    if (!settings.localReminderEnabled) {
      return 0;
    }

    const now: number = Date.now();
    const horizon: number = now + HORIZON_DAYS * 86400000;
    const planned: PlannedReminder[] = [];

    for (const t of tasks) {
      if (t.status !== 'todo' || !t.due_date || t.deleted_at) {
        continue;
      }
      const lead: number = t.remind_before_minutes ?? settings.defaultRemindBeforeMinutes;
      const fireAt: number = DateUtil.dueTimestamp(t.due_date, t.due_time) - lead * 60000;
      // 已经过去的时间点不排：系统会立刻弹一堆历史提醒，体验灾难
      if (fireAt <= now + 30000 || fireAt > horizon) {
        continue;
      }
      planned.push({ at: fireAt, task: t, lead: lead });
    }

    planned.sort((a: PlannedReminder, b: PlannedReminder) => a.at - b.at);
    const slice: PlannedReminder[] = planned.slice(0, MAX_REMINDERS);

    let ok: number = 0;
    for (const p of slice) {
      const published: boolean = await Reminder.publish(p);
      if (published) {
        ok++;
      }
    }
    return ok;
  }

  private static async publish(p: PlannedReminder): Promise<boolean> {
    const at: Date = new Date(p.at);
    const request: reminderAgentManager.ReminderRequestCalendar = {
      reminderType: reminderAgentManager.ReminderType.REMINDER_TYPE_CALENDAR,
      dateTime: {
        year: at.getFullYear(),
        month: at.getMonth() + 1, // 系统 LocalDateTime 的 month 为 1-12
        day: at.getDate(),
        hour: at.getHours(),
        minute: at.getMinutes(),
        second: 0,
      },
      title: p.task.title,
      content: Reminder.contentOf(p),
      expiredContent: '该任务已过期',
      // 通知 id 直接用任务 id：同一任务重复排程会覆盖而不是堆叠
      notificationId: p.task.id,
      ringDuration: 5,
      snoozeTimes: 0,
      slotType: notificationManager.SlotType.SOCIAL_COMMUNICATION,
      // 点击提醒回到应用首页
      wantAgent: {
        pkgName: 'com.zjx93.reach',
        abilityName: 'EntryAbility',
      },
    };
    try {
      await reminderAgentManager.publishReminder(request);
      return true;
    } catch (e) {
      return false;
    }
  }

  private static contentOf(p: PlannedReminder): string {
    const parts: string[] = [];
    if (p.task.due_time && p.task.due_time.length > 0) {
      parts.push(`${p.task.due_date} ${p.task.due_time} 到期`);
    } else {
      parts.push(`${p.task.due_date} 到期`);
    }
    if (p.task.category_name) {
      parts.push(p.task.category_name);
    }
    if (p.task.goal_title) {
      parts.push(`目标：${p.task.goal_title}`);
    }
    return parts.join(' · ');
  }

  /** 退出登录时清空，避免用别人的账号还收到上一个账号的提醒。 */
  static async cancelAll(): Promise<void> {
    try {
      await reminderAgentManager.cancelAllReminders();
    } catch (e) {
      // 忽略
    }
  }
}

interface PlannedReminder {
  at: number;
  task: TaskOut;
  lead: number;
}
