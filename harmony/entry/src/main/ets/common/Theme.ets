/**
 * 视觉常量。
 *
 * 与 web (`web/src/index.css`) / Android (`ui/theme/Theme.kt`) 取同一组色值，
 * 保证三端观感一致。强调色可被用户偏好 `accentColor` 覆盖。
 */
import { Prefs } from './Prefs';

export class Theme {
  static readonly BRAND: string = '#3B82F6';
  static readonly BRAND_DARK: string = '#2563EB';
  static readonly BG: string = '#F5F6F8';
  static readonly CARD: string = '#FFFFFF';
  static readonly BORDER: string = '#E5E7EB';
  static readonly TEXT: string = '#111827';
  static readonly TEXT_SUB: string = '#6B7280';
  static readonly TEXT_WEAK: string = '#9CA3AF';
  static readonly DANGER: string = '#EF4444';
  static readonly WARN: string = '#F59E0B';
  static readonly OK: string = '#10B981';
  static readonly PURPLE: string = '#8B5CF6';

  static readonly RADIUS: number = 14;
  static readonly GAP: number = 12;
  static readonly PAGE_PADDING: number = 16;

  /** 用户自定义强调色（非法值回退品牌蓝）。 */
  static accent(): string {
    const c: string = Prefs.settings().accentColor;
    return /^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/.test(c) ? c : Theme.BRAND;
  }

  /** 紧急度 → 颜色。 */
  static priorityColor(priority: string): string {
    if (priority === 'urgent') {
      return Theme.DANGER;
    }
    if (priority === 'high') {
      return Theme.WARN;
    }
    if (priority === 'low') {
      return Theme.TEXT_WEAK;
    }
    return Theme.BRAND;
  }

  static priorityLabel(priority: string): string {
    if (priority === 'urgent') {
      return '紧急';
    }
    if (priority === 'high') {
      return '较急';
    }
    if (priority === 'low') {
      return '不急';
    }
    return '一般';
  }

  static importanceLabel(importance: string): string {
    if (importance === 'high') {
      return '重要';
    }
    if (importance === 'low') {
      return '次要';
    }
    return '一般';
  }

  static recurrenceLabel(recurrence: string): string {
    if (recurrence === 'daily') {
      return '每天';
    }
    if (recurrence === 'weekday') {
      return '每工作日';
    }
    if (recurrence === 'weekly') {
      return '每周';
    }
    if (recurrence === 'biweekly') {
      return '每两周';
    }
    if (recurrence === 'monthly') {
      return '每月';
    }
    if (recurrence === 'monthend') {
      return '每月末';
    }
    return '不重复';
  }

  static recordTypeLabel(type: string): string {
    if (type === 'diary') {
      return '日记';
    }
    if (type === 'worklog') {
      return '工作日志';
    }
    if (type === 'reading') {
      return '读书笔记';
    }
    if (type === 'note') {
      return '随手记';
    }
    return type;
  }
}

/** 各选项的可选值 —— 与后端 Literal 严格一致，改后端时这里必须同步。 */
export class Options {
  static readonly PRIORITIES: string[] = ['low', 'normal', 'high', 'urgent'];
  static readonly IMPORTANCES: string[] = ['low', 'normal', 'high'];
  static readonly RECURRENCES: string[] = [
    'none', 'daily', 'weekday', 'weekly', 'biweekly', 'monthly', 'monthend',
  ];
  static readonly RECORD_TYPES: string[] = ['diary', 'worklog', 'reading', 'note'];
  static readonly REMIND_MINUTES: number[] = [0, 5, 10, 15, 30, 60, 120, 1440];

  static remindLabel(m: number): string {
    if (m === 0) {
      return '到点提醒';
    }
    if (m < 60) {
      return `提前${m}分钟`;
    }
    if (m < 1440) {
      return `提前${m / 60}小时`;
    }
    return `提前${m / 1440}天`;
  }
}
