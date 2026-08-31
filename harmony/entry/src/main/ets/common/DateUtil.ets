/**
 * 日期工具。
 *
 * 关键约定：**所有「日」级别的运算都在本地时区下用 `YYYY-MM-DD` 字符串完成**。
 * 不用 `Date` 直接相减、也不用 UTC，否则东八区 00:00-08:00 会把「今天」算成昨天，
 * 这类 bug 在日历/逾期判定上最难查。
 */

export class DateUtil {
  private static pad2(n: number): string {
    return n < 10 ? `0${n}` : `${n}`;
  }

  /** `YYYY-MM-DD`（本地时区）。 */
  static fmt(d: Date): string {
    return `${d.getFullYear()}-${DateUtil.pad2(d.getMonth() + 1)}-${DateUtil.pad2(d.getDate())}`;
  }

  static today(): string {
    return DateUtil.fmt(new Date());
  }

  /** `HH:mm`（本地时区）。 */
  static fmtTime(d: Date): string {
    return `${DateUtil.pad2(d.getHours())}:${DateUtil.pad2(d.getMinutes())}`;
  }

  /** 把 `YYYY-MM-DDTHH:mm:ss...` 转成 `M月D日 HH:mm`，用于回收站等展示。 */
  static fmtDateTime(s?: string | null): string {
    if (!s) {
      return '';
    }
    const t: string = s.replace('T', ' ').replace(/:?\d{2}Z?$/, '').trim();
    const sp: string[] = t.split(' ');
    const datePart: string = sp[0] ?? '';
    const timePart: string = sp[1] ?? '';
    const dp: string[] = datePart.split('-');
    if (dp.length !== 3) {
      return s;
    }
    const month: number = Number.parseInt(dp[1], 10);
    const day: number = Number.parseInt(dp[2], 10);
    if (Number.isNaN(month) || Number.isNaN(day)) {
      return s;
    }
    const md: string = `${month}月${day}日`;
    return timePart.length > 0 ? `${md} ${timePart}` : md;
  }

  /** 把 `YYYY-MM-DD` 解析成本地时区的当天 00:00；非法输入返回今天。 */
  static parse(ds: string): Date {
    const parts: string[] = (ds ?? '').split('-');
    if (parts.length !== 3) {
      return new Date();
    }
    const y: number = Number.parseInt(parts[0], 10);
    const m: number = Number.parseInt(parts[1], 10);
    const d: number = Number.parseInt(parts[2], 10);
    if (Number.isNaN(y) || Number.isNaN(m) || Number.isNaN(d)) {
      return new Date();
    }
    return new Date(y, m - 1, d);
  }

  /** `YYYY-MM-DD` + n 天。 */
  static addDays(ds: string, n: number): string {
    const d: Date = DateUtil.parse(ds);
    d.setDate(d.getDate() + n);
    return DateUtil.fmt(d);
  }

  /** 两个 `YYYY-MM-DD` 相差天数（a - b）。 */
  static diffDays(a: string, b: string): number {
    const da: Date = DateUtil.parse(a);
    const db: Date = DateUtil.parse(b);
    // 归一到当天 12:00 再相减，消除夏令时导致的 23/25 小时误差
    const ma: number = Date.UTC(da.getFullYear(), da.getMonth(), da.getDate());
    const mb: number = Date.UTC(db.getFullYear(), db.getMonth(), db.getDate());
    return Math.round((ma - mb) / 86400000);
  }

  /** 该月天数。 */
  static daysInMonth(year: number, month: number): number {
    return new Date(year, month, 0).getDate();
  }

  /** 该月 1 号是周几（0=周日）。 */
  static firstWeekday(year: number, month: number): number {
    return new Date(year, month - 1, 1).getDay();
  }

  /**
   * 生成 6×7 的月视图格子（含上下月补白）。
   * `weekStart` 为 `'mon'` 时以周一为首列。
   */
  static monthGrid(year: number, month: number, weekStart: string): string[] {
    const offsetBase: number = weekStart === 'mon' ? 1 : 0;
    let lead: number = DateUtil.firstWeekday(year, month) - offsetBase;
    if (lead < 0) {
      lead += 7;
    }
    const first: string = `${year}-${DateUtil.pad2(month)}-01`;
    const cells: string[] = [];
    for (let i = 0; i < 42; i++) {
      cells.push(DateUtil.addDays(first, i - lead));
    }
    return cells;
  }

  /** 取 `YYYY-MM-DD` 的「日」部分（用于格子里显示的数字）。 */
  static dayOf(ds: string): number {
    const parts: string[] = ds.split('-');
    return parts.length === 3 ? Number.parseInt(parts[2], 10) : 0;
  }

  static monthOf(ds: string): number {
    const parts: string[] = ds.split('-');
    return parts.length === 3 ? Number.parseInt(parts[1], 10) : 0;
  }

  static yearOf(ds: string): number {
    const parts: string[] = ds.split('-');
    return parts.length === 3 ? Number.parseInt(parts[0], 10) : 0;
  }

  static weekdayOf(ds: string): number {
    return DateUtil.parse(ds).getDay();
  }

  static readonly WEEK_LABELS_SUN: string[] = ['日', '一', '二', '三', '四', '五', '六'];

  static weekLabels(weekStart: string): string[] {
    if (weekStart === 'mon') {
      return ['一', '二', '三', '四', '五', '六', '日'];
    }
    return DateUtil.WEEK_LABELS_SUN;
  }

  static weekdayLabel(ds: string): string {
    return '周' + DateUtil.WEEK_LABELS_SUN[DateUtil.weekdayOf(ds)];
  }

  /** 「今天 / 明天 / 昨天 / 逾期 N 天 / M月D日」——列表里最省空间的表达。 */
  static humanDue(ds?: string | null): string {
    if (!ds) {
      return '';
    }
    const diff: number = DateUtil.diffDays(ds, DateUtil.today());
    if (diff === 0) {
      return '今天';
    }
    if (diff === 1) {
      return '明天';
    }
    if (diff === 2) {
      return '后天';
    }
    if (diff === -1) {
      return '昨天';
    }
    if (diff < 0) {
      return `逾期${-diff}天`;
    }
    return `${DateUtil.monthOf(ds)}月${DateUtil.dayOf(ds)}日`;
  }

  static isOverdue(ds?: string | null): boolean {
    if (!ds) {
      return false;
    }
    return DateUtil.diffDays(ds, DateUtil.today()) < 0;
  }

  /** 一年中的第几天（与 web / Android 口径一致）。 */
  static dayOfYear(ds: string): number {
    const y: number = DateUtil.yearOf(ds);
    return DateUtil.diffDays(ds, `${y}-01-01`) + 1;
  }

  /** 一年中的第几周（以周日为起点，与 web `weekOfYear` 一致）。 */
  static weekOfYear(ds: string): number {
    const y: number = DateUtil.yearOf(ds);
    const jan1: string = `${y}-01-01`;
    const day: number = DateUtil.diffDays(ds, jan1);
    const jan1Dow: number = DateUtil.weekdayOf(jan1);
    return Math.ceil((day + jan1Dow + 1) / 7);
  }

  /** 本周起始日（含）。 */
  static weekStartOf(ds: string, weekStart: string): string {
    const base: number = weekStart === 'mon' ? 1 : 0;
    let back: number = DateUtil.weekdayOf(ds) - base;
    if (back < 0) {
      back += 7;
    }
    return DateUtil.addDays(ds, -back);
  }

  /** ISO8601 字符串 → `M月D日 HH:mm`，解析失败返回原串。 */
  static humanIso(iso?: string | null): string {
    if (!iso) {
      return '';
    }
    const t: number = Date.parse(iso);
    if (Number.isNaN(t)) {
      return iso;
    }
    const d: Date = new Date(t);
    return `${d.getMonth() + 1}月${d.getDate()}日 ${DateUtil.fmtTime(d)}`;
  }

  /**
   * 把 `YYYY-MM-DD` + `HH:mm` 合成本地时间戳（毫秒）。
   * 缺省时间按当天 09:00 处理——与后端调度器对「只有日期」的任务的处理保持一致。
   */
  static dueTimestamp(dateStr: string, timeStr?: string | null): number {
    const d: Date = DateUtil.parse(dateStr);
    let hh: number = 9;
    let mm: number = 0;
    if (timeStr && timeStr.length >= 4) {
      const seg: string[] = timeStr.split(':');
      if (seg.length >= 2) {
        const h: number = Number.parseInt(seg[0], 10);
        const m: number = Number.parseInt(seg[1], 10);
        if (!Number.isNaN(h) && !Number.isNaN(m)) {
          hh = h;
          mm = m;
        }
      }
    }
    d.setHours(hh, mm, 0, 0);
    return d.getTime();
  }
}
