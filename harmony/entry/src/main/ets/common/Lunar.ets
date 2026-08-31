/**
 * 离线农历 / 黄历计算。
 *
 * 与 Android 端 `LunarUtils.kt` **同一份数据表、同一套算法**（1900–2100），
 * 保证同一天在两个客户端显示完全一致——跨端口径不一致是用户最直观的「不专业」信号。
 *
 * 能离线算出：农历年月日与闰月、干支年、生肖、24 节气、星座、月相、传统节日、
 * 本年第几天/第几周。
 * 需联网才有的：宜忌、神位、物候（走后端 `/api/lunar`，见 `LunarStore`）。
 */
import { LunarInfo } from './Models';
import { DateUtil } from './DateUtil';

const MIN_YEAR: number = 1900;
const MAX_YEAR: number = 2100;

/**
 * 1900–2100 农历数据。每年一个整数：
 * - bit0-3：闰月月份（0 = 该年无闰月）
 * - bit16：闰月天数（1 = 30 天）
 * - bit4-15：12 个正常月的天数（1 = 30 天）
 */
const LUNAR_TERMS: number[] = [
  0x04bd8, 0x04ae0, 0x0a570, 0x054d5, 0x0d260, 0x0d950, 0x16554, 0x056a0, 0x09ad0, 0x055d2, // 1900-1909
  0x04ae0, 0x0a5b6, 0x0a4d0, 0x0d250, 0x1d255, 0x0b540, 0x0d6a0, 0x0ada2, 0x095b0, 0x14977, // 1910-1919
  0x04970, 0x0a4b0, 0x0b4b5, 0x06a50, 0x06d40, 0x1ab54, 0x02b60, 0x09570, 0x052f2, 0x04970, // 1920-1929
  0x06566, 0x0d4a0, 0x0ea50, 0x16a95, 0x05ad0, 0x02b60, 0x186e3, 0x092e0, 0x1c8d7, 0x0c950, // 1930-1939
  0x0d4a0, 0x1d8a6, 0x0b550, 0x056a0, 0x1a5b4, 0x025d0, 0x092d0, 0x0d2b2, 0x0a950, 0x0b557, // 1940-1949
  0x06ca0, 0x0b550, 0x15355, 0x04da0, 0x0a5d0, 0x14573, 0x052d0, 0x0a9a8, 0x0e950, 0x06aa0, // 1950-1959
  0x0aea6, 0x0ab50, 0x04b60, 0x0aae4, 0x0a570, 0x05260, 0x0f263, 0x0d950, 0x05b57, 0x056a0, // 1960-1969
  0x096d0, 0x04dd5, 0x04ad0, 0x0a4d0, 0x0d4d4, 0x0d250, 0x0d558, 0x0b540, 0x0b5a0, 0x195a6, // 1970-1979
  0x095b0, 0x049b0, 0x0a974, 0x0a4b0, 0x0b27a, 0x06a50, 0x06d40, 0x0af46, 0x0ab60, 0x09570, // 1980-1989
  0x04af5, 0x04970, 0x064b0, 0x074a3, 0x0ea50, 0x06b58, 0x05ac0, 0x0ab60, 0x096d5, 0x092e0, // 1990-1999
  0x0c960, 0x0d954, 0x0d4a0, 0x0da50, 0x07552, 0x056a0, 0x0abb7, 0x025d0, 0x092d0, 0x0cab5, // 2000-2009
  0x0a950, 0x0b4a0, 0x0baa4, 0x0ad50, 0x055d9, 0x04ba0, 0x0a5b0, 0x15176, 0x052b0, 0x0a930, // 2010-2019
  0x07954, 0x06aa0, 0x0ad50, 0x05b52, 0x04b60, 0x0a6e6, 0x0a4e0, 0x0d260, 0x0ea65, 0x0d530, // 2020-2029
  0x05aa0, 0x076a3, 0x096d0, 0x04bd7, 0x04ad0, 0x0a4d0, 0x1d0b6, 0x0d250, 0x0d520, 0x0dd45, // 2030-2039
  0x0b5a0, 0x056d0, 0x055b2, 0x049b0, 0x0a577, 0x0a4b0, 0x0aa50, 0x1b255, 0x06d20, 0x0ada0, // 2040-2049
  0x14b63, 0x09370, 0x049f8, 0x04970, 0x064b0, 0x168a6, 0x0ea50, 0x06b20, 0x1a6c4, 0x0aae0, // 2050-2059
  0x0a2e0, 0x0d2e3, 0x0c960, 0x0d557, 0x0d4a0, 0x0da50, 0x05d55, 0x056a0, 0x0a6d0, 0x055d4, // 2060-2069
  0x052d0, 0x0a9b8, 0x0a950, 0x0b4a0, 0x0b6a6, 0x0ad50, 0x055a0, 0x0aba4, 0x0a5b0, 0x052b0, // 2070-2079
  0x0b273, 0x06930, 0x07337, 0x06aa0, 0x0ad50, 0x14b55, 0x04b60, 0x0a570, 0x054e4, 0x0d160, // 2080-2089
  0x0e968, 0x0d520, 0x0daa0, 0x16aa6, 0x056d0, 0x04ae0, 0x0a9d4, 0x0a2d0, 0x0d150, 0x0f252, // 2090-2099
  0x0d520, // 2100
];

interface LunarDate {
  year: number;
  month: number;
  day: number;
  isLeap: boolean;
}

function leapMonth(year: number): number {
  if (year < MIN_YEAR || year > MAX_YEAR) {
    return 0;
  }
  return LUNAR_TERMS[year - MIN_YEAR] & 0xf;
}

function daysInLeapMonth(year: number): number {
  if (leapMonth(year) === 0) {
    return 0;
  }
  return (LUNAR_TERMS[year - MIN_YEAR] & 0x10000) !== 0 ? 30 : 29;
}

function daysInLunarMonth(year: number, month: number): number {
  return (LUNAR_TERMS[year - MIN_YEAR] & (0x10000 >> month)) === 0 ? 29 : 30;
}

function daysInLunarYear(year: number): number {
  let sum: number = 348; // 12 * 29
  let i: number = 0x8000;
  while (i > 0x8) {
    if ((LUNAR_TERMS[year - MIN_YEAR] & i) !== 0) {
      sum++;
    }
    i = i >> 1;
  }
  return sum + daysInLeapMonth(year);
}

/** 本地日期 → 距 1970-01-01 的天数（用 UTC 归一，避免时区偏移）。 */
function epochDay(y: number, m: number, d: number): number {
  return Math.floor(Date.UTC(y, m - 1, d) / 86400000);
}

/** 公历 → 农历。基准：农历 1900 年正月初一 = 公历 1900-01-31。 */
function solarToLunar(y: number, m: number, d: number): LunarDate {
  let offset: number = epochDay(y, m, d) - epochDay(1900, 1, 31);

  let ly: number = MIN_YEAR;
  let yearDays: number = 365;
  while (ly <= MAX_YEAR && offset > 0) {
    yearDays = daysInLunarYear(ly);
    offset -= yearDays;
    ly++;
  }
  if (offset < 0) {
    offset += yearDays;
    ly--;
  }

  let isLeap: boolean = false;
  let lm: number = 1;
  const leap: number = leapMonth(ly);
  let monthDays: number = 30;
  while (lm <= 12) {
    if (leap > 0 && lm === leap + 1 && !isLeap) {
      lm--; // 抵消循环末尾的 ++，使本轮处理闰月
      isLeap = true;
      monthDays = daysInLeapMonth(ly);
    } else {
      monthDays = daysInLunarMonth(ly, lm);
    }
    offset -= monthDays;
    if (isLeap && lm === leap + 1) {
      isLeap = false;
    }
    if (offset <= 0) {
      break;
    }
    lm++;
  }
  if (offset === 0 && leap > 0 && lm === leap + 1) {
    if (isLeap) {
      isLeap = false;
    } else {
      isLeap = true;
      lm--;
    }
  }
  if (offset < 0) {
    offset += monthDays;
    lm--;
  }
  return { year: ly, month: lm, day: offset + 1, isLeap: isLeap };
}

// ---------------------------------------------------------------------------
// 干支 / 生肖 / 中文数字
// ---------------------------------------------------------------------------
const GAN: string[] = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸'];
const ZHI: string[] = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥'];
const ZODIAC: string[] = ['鼠', '牛', '虎', '兔', '龙', '蛇', '马', '羊', '猴', '鸡', '狗', '猪'];
const CN_DIGITS: string[] = ['〇', '一', '二', '三', '四', '五', '六', '七', '八', '九'];
const LUNAR_MONTHS: string[] = [
  '正月', '二月', '三月', '四月', '五月', '六月',
  '七月', '八月', '九月', '十月', '十一月', '腊月',
];
const LUNAR_DAYS: string[] = [
  '初一', '初二', '初三', '初四', '初五', '初六', '初七', '初八', '初九', '初十',
  '十一', '十二', '十三', '十四', '十五', '十六', '十七', '十八', '十九', '二十',
  '廿一', '廿二', '廿三', '廿四', '廿五', '廿六', '廿七', '廿八', '廿九', '三十',
];

function ganzhiOfYear(ly: number): string {
  return GAN[(ly - 4) % 10] + ZHI[(ly - 4) % 12];
}

function zodiacOfYear(ly: number): string {
  return ZODIAC[(ly - 4) % 12];
}

/** 由干支末字反推生肖，供服务端返回的 YEARGANZHI 复用。 */
export function zodiacFromGanzhi(gz?: string | null): string {
  if (!gz) {
    return '';
  }
  const trimmed: string = gz.trim();
  if (trimmed.length === 0) {
    return '';
  }
  const last: string = trimmed.charAt(trimmed.length - 1);
  const idx: number = ZHI.indexOf(last);
  return idx >= 0 ? ZODIAC[idx] : '';
}

function toChineseYear(y: number): string {
  let out: string = '';
  const s: string = `${y}`;
  for (let i = 0; i < s.length; i++) {
    out += CN_DIGITS[Number.parseInt(s.charAt(i), 10)];
  }
  return out;
}

function lunarMonthName(month: number, isLeap: boolean): string {
  const base: string = LUNAR_MONTHS[month - 1];
  return isLeap ? '闰' + base : base;
}

// ---------------------------------------------------------------------------
// 24 节气（低精度太阳黄经，误差 ±0.01°，足够判断落在哪一天）
// ---------------------------------------------------------------------------
const TERM_NAMES: string[] = [
  '春分', '清明', '谷雨', '立夏', '小满', '芒种', '夏至', '小暑', '大暑', '立秋',
  '处暑', '白露', '秋分', '寒露', '霜降', '立冬', '小雪', '大雪', '冬至', '小寒',
  '大寒', '立春', '雨水', '惊蛰',
];

function julianDay(y: number, m: number, d: number): number {
  return epochDay(y, m, d) + 2440587.5;
}

function sunLongitude(jd: number): number {
  const n: number = jd - 2451545.0;
  const l: number = 280.460 + 0.9856474 * n;
  const g: number = ((357.528 + 0.9856003 * n) * Math.PI) / 180;
  let lambda: number = l + 1.915 * Math.sin(g) + 0.020 * Math.sin(2 * g);
  lambda = lambda % 360;
  if (lambda < 0) {
    lambda += 360;
  }
  return lambda;
}

/** 该公历日是否为节气；是则返回节气名，否则空串。 */
function solarTerm(y: number, m: number, d: number): string {
  const jdToday: number = julianDay(y, m, d) + 0.5;
  const jdYest: number = jdToday - 1;
  const kToday: number = ((Math.floor(sunLongitude(jdToday) / 15) % 24) + 24) % 24;
  const kYest: number = ((Math.floor(sunLongitude(jdYest) / 15) % 24) + 24) % 24;
  return kToday !== kYest ? TERM_NAMES[kToday] : '';
}

// ---------------------------------------------------------------------------
// 星座 / 月相 / 节日
// ---------------------------------------------------------------------------
const XINGZUO: string[] = [
  '摩羯', '水瓶', '双鱼', '白羊', '金牛', '双子',
  '巨蟹', '狮子', '处女', '天秤', '天蝎', '射手',
];
const XINGZUO_SWITCH: number[] = [20, 19, 21, 20, 21, 22, 23, 23, 23, 24, 23, 22];

function xingzuoOf(m: number, d: number): string {
  const idx: number = d < XINGZUO_SWITCH[m - 1] ? m - 1 : m;
  return XINGZUO[idx % 12];
}

function yuexiangOf(lunarDay: number): string {
  if (lunarDay === 1) {
    return '新月';
  }
  if (lunarDay === 7 || lunarDay === 8) {
    return '上弦月';
  }
  if (lunarDay === 15 || lunarDay === 16) {
    return '满月';
  }
  if (lunarDay === 22 || lunarDay === 23) {
    return '下弦月';
  }
  return '';
}

const SOLAR_FESTIVALS: Record<string, string> = {
  '1-1': '元旦',
  '2-14': '情人节',
  '3-8': '妇女节',
  '3-12': '植树节',
  '4-1': '愚人节',
  '5-1': '劳动节',
  '5-4': '青年节',
  '6-1': '儿童节',
  '7-1': '建党节',
  '8-1': '建军节',
  '9-10': '教师节',
  '10-1': '国庆节',
  '12-24': '平安夜',
  '12-25': '圣诞节',
};

function festivalOf(m: number, d: number, lunar: LunarDate): string {
  const list: string[] = [];
  const solar: string | undefined = SOLAR_FESTIVALS[`${m}-${d}`];
  if (solar !== undefined) {
    list.push(solar);
  }
  if (!lunar.isLeap) {
    const lm: number = lunar.month;
    const ld: number = lunar.day;
    if (lm === 1 && ld === 1) {
      list.push('春节');
    } else if (lm === 1 && ld === 15) {
      list.push('元宵');
    } else if (lm === 2 && ld === 2) {
      list.push('龙抬头');
    } else if (lm === 5 && ld === 5) {
      list.push('端午');
    } else if (lm === 7 && ld === 7) {
      list.push('七夕');
    } else if (lm === 7 && ld === 15) {
      list.push('中元');
    } else if (lm === 8 && ld === 15) {
      list.push('中秋');
    } else if (lm === 9 && ld === 9) {
      list.push('重阳');
    } else if (lm === 12 && ld === 8) {
      list.push('腊八');
    } else if (lm === 12 && (ld === 23 || ld === 24)) {
      list.push('小年');
    }
  }
  return list.join(' ');
}

// ---------------------------------------------------------------------------
// 对外接口
// ---------------------------------------------------------------------------

/** 离线计算某公历日期（`YYYY-MM-DD`）的农历信息，字段与后端 `/api/lunar` 对齐。 */
export function computeLunar(date: string): LunarInfo {
  const y: number = DateUtil.yearOf(date);
  const m: number = DateUtil.monthOf(date);
  const d: number = DateUtil.dayOf(date);
  const ld: LunarDate = solarToLunar(y, m, d);
  const term: string = solarTerm(y, m, d);
  return {
    nyue: lunarMonthName(ld.month, ld.isLeap),
    nri: LUNAR_DAYS[ld.day - 1],
    jieqi: term.length > 0 ? term : null,
    JIEQIDAYS: term.length > 0 ? '1' : null,
    jieri: festivalOf(m, d, ld),
    nnian: toChineseYear(ld.year),
    YEARGANZHI: ganzhiOfYear(ld.year),
    shengxiao: zodiacOfYear(ld.year),
    xingzuo: xingzuoOf(m, d),
    YUEXIANG: yuexiangOf(ld.day),
    DAYSINYEAR: `${DateUtil.dayOfYear(date)}`,
    YLWEEKNOY: `${DateUtil.weekOfYear(date)}`,
  };
}

/** 日历格子里的单行文字：节日 > 农历日（初一显示月名）+ 节气。 */
export function lunarLabel(info?: LunarInfo | null): string {
  if (!info || !info.nri) {
    return '';
  }
  const base: string = info.nri === '初一' ? (info.nyue ?? info.nri) : info.nri;
  const parts: string[] = [];
  if (info.jieri && info.jieri.length > 0) {
    parts.push(info.jieri);
  }
  parts.push(base);
  if (info.JIEQIDAYS === '1' && info.jieqi && info.jieqi.length > 0) {
    parts.push(info.jieqi);
  }
  return parts.join(' ');
}

/** 「二〇二六年六月十五」。 */
export function lunarYmd(info?: LunarInfo | null): string {
  if (!info || !info.nnian || !info.nyue || !info.nri) {
    return lunarLabel(info);
  }
  return `${info.nnian}年${info.nyue}${info.nri}`;
}

/** 「丙午（马）年」。 */
export function ganzhiYearText(info?: LunarInfo | null): string {
  const gz: string = info?.YEARGANZHI ?? '';
  if (gz.length === 0) {
    return '';
  }
  const z: string = info?.shengxiao && info.shengxiao.length > 0
    ? info.shengxiao
    : zodiacFromGanzhi(gz);
  return z.length > 0 ? `${gz}（${z}）年` : `${gz}年`;
}

/** 「本年第X天 第X周」。服务端有值优先用服务端的，避免两处口径打架。 */
export function daysWeekText(info: LunarInfo | null, ds: string): string {
  const d: number = parseIntOr(info?.DAYSINYEAR, DateUtil.dayOfYear(ds));
  const w: number = parseIntOr(info?.YLWEEKNOY, DateUtil.weekOfYear(ds));
  return `本年第${d}天 第${w}周`;
}

function parseIntOr(v: string | null | undefined, fallback: number): number {
  if (!v || v.length === 0) {
    return fallback;
  }
  const n: number = Number.parseInt(v, 10);
  return Number.isNaN(n) ? fallback : n;
}

/** 仅节气当日才返回节气名，避免「当前节气区间」挂满半个月。 */
export function termText(info?: LunarInfo | null): string {
  if (info?.JIEQIDAYS === '1' && info.jieqi) {
    return info.jieqi;
  }
  return '';
}

/** 物候只取后半段：「寒露 初候鸿雁来宾」→「鸿雁来宾」。 */
export function wuhouShort(info?: LunarInfo | null): string {
  const w: string = info?.WUHOU ?? '';
  if (w.length === 0) {
    return '';
  }
  const seg: string[] = w.split(' ');
  return seg[seg.length - 1];
}

function splitPipe(raw?: string | null): string[] {
  if (!raw || raw.length === 0) {
    return [];
  }
  const out: string[] = [];
  for (const s of raw.split('|')) {
    const t: string = s.trim();
    if (t.length > 0) {
      out.push(t);
    }
  }
  return out;
}

export function yiList(info?: LunarInfo | null): string[] {
  return splitPipe(info?.yi);
}

export function jiList(info?: LunarInfo | null): string[] {
  return splitPipe(info?.ji);
}

export interface GodPosition {
  label: string;
  value: string;
}

/** 神位（喜/阳贵/阴贵/福/财），过滤空值。 */
export function godPositions(info?: LunarInfo | null): GodPosition[] {
  if (!info) {
    return [];
  }
  const raw: GodPosition[] = [
    { label: '喜神位', value: info.DAYPOSITIONXI ?? '' },
    { label: '阳贵位', value: info.DAYPOSITIONYANGGUI ?? '' },
    { label: '阴贵位', value: info.DAYPOSITIONYINGUI ?? '' },
    { label: '福神位', value: info.DAYPOSITIONFU ?? '' },
    { label: '财神位', value: info.DAYPOSITIONCAI ?? '' },
  ];
  return raw.filter((p: GodPosition) => p.value.length > 0);
}

/** 合并离线结果与服务端结果：服务端字段优先，缺失的用离线值补齐。 */
export function mergeLunar(offline: LunarInfo, remote?: LunarInfo | null): LunarInfo {
  if (!remote) {
    return offline;
  }
  return {
    nyue: pick(remote.nyue, offline.nyue),
    nri: pick(remote.nri, offline.nri),
    jieqi: pick(remote.jieqi, offline.jieqi),
    JIEQIDAYS: pick(remote.JIEQIDAYS, offline.JIEQIDAYS),
    jieri: pick(remote.jieri, offline.jieri),
    nnian: pick(remote.nnian, offline.nnian),
    YEARGANZHI: pick(remote.YEARGANZHI, offline.YEARGANZHI),
    shengxiao: pick(remote.shengxiao, offline.shengxiao),
    DAYSHENGXIAO: remote.DAYSHENGXIAO,
    xingzuo: pick(remote.xingzuo, offline.xingzuo),
    yi: remote.yi,
    ji: remote.ji,
    YUEXIANG: pick(remote.YUEXIANG, offline.YUEXIANG),
    WUHOU: remote.WUHOU,
    DAYPOSITIONXI: remote.DAYPOSITIONXI,
    DAYPOSITIONYANGGUI: remote.DAYPOSITIONYANGGUI,
    DAYPOSITIONYINGUI: remote.DAYPOSITIONYINGUI,
    DAYPOSITIONFU: remote.DAYPOSITIONFU,
    DAYPOSITIONCAI: remote.DAYPOSITIONCAI,
    DAYSINYEAR: pick(remote.DAYSINYEAR, offline.DAYSINYEAR),
    YLWEEKNOY: pick(remote.YLWEEKNOY, offline.YLWEEKNOY),
  };
}

function pick(a?: string | null, b?: string | null): string | null {
  if (a !== undefined && a !== null && a.length > 0) {
    return a;
  }
  return b ?? null;
}
