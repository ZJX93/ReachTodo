import { create } from 'zustand'
import type { Settings, WeekStart, LunarSource } from '../types'

// 轻量本地设置（仅保存在浏览器 localStorage，不上云）：
// - defaultFocusMinutes: 番茄钟默认时长（15 / 25 / 45 / 60）
// - weekStart: 日历与周回顾的周起始日（'sun' 周日起 / 'mon' 周一起，默认 'sun'）
// - timezone: 应用使用的时区（IANA 名称，如 Asia/Shanghai），影响"今天"判定、日历、时间展示
//
// 选择 localStorage 的原因：偏好是个体体验，跨设备同步反而容易让"自己习惯的设置"
// 在别的设备上变扭；用户量小且主要在 NAS 本地访问，丢失成本极低。如未来需要
// 跨设备同步，再加一个 user_settings 表 + 启动时拉取覆盖即可。

const KEY = 'reach.settings.v1'

// 浏览器当前的本地时区（首次加载解析一次）；用户未手动设置时以此作为默认值，
// 保证从"本地时区"升级到"可配置时区"时行为不变。
const BROWSER_TZ =
  (typeof Intl !== 'undefined' && Intl.DateTimeFormat().resolvedOptions().timeZone) ||
  'Asia/Shanghai'

const DEFAULTS: Settings = {
  defaultFocusMinutes: 25,
  shortBreakMinutes: 5,
  longBreakMinutes: 15,
  longBreakInterval: 4,
  weekStart: 'sun', // 'sun' | 'mon'
  timezone: BROWSER_TZ,
  // 农历/节假日数据源：
  // - lunarSource: 'backend' 走后端代理（apihz.cn / jiejiariapi，key 在服务端）
  // - lunarSource: 'custom' 走用户自定义接口（前端直连，需 CORS / 同源）
  lunarSource: 'backend', // 'backend' | 'custom'
  lunarApiBase: '', // 自定义农历接口模板，支持 {date} / {y} / {m} / {d} 占位
  holidayApiBase: '', // 自定义节假日接口模板，支持 {year} 占位
  lunarApiKey: '', // 可选：自定义接口密钥，以 Authorization: Bearer 发送
}

const readSettings = (): Settings => {
  try {
    const raw = localStorage.getItem(KEY)
    if (!raw) return { ...DEFAULTS }
    const parsed = JSON.parse(raw) as Partial<Settings>
    return { ...DEFAULTS, ...parsed }
  } catch {
    return { ...DEFAULTS }
  }
}

const writeSettings = (s: Settings): void => {
  try {
    localStorage.setItem(KEY, JSON.stringify(s))
  } catch {
    /* quota / private mode → 静默忽略，不阻塞 UI */
  }
}

export interface SettingsState extends Settings {
  setDefaultFocusMinutes: (m: number) => void
  setShortBreakMinutes: (m: number) => void
  setLongBreakMinutes: (m: number) => void
  setLongBreakInterval: (n: number) => void
  setWeekStart: (w: WeekStart) => void
  setTimezone: (tz: string) => void
  // 农历数据源配置：合并写入（支持一次更新多个字段）
  updateLunar: (partial: Partial<Settings>) => void
  // 番茄钟多字段合并写入
  updateFocusSettings: (partial: Partial<Settings>) => void
}

const clampMinutes = (m: number, min = 1, max = 180) => Math.max(min, Math.min(max, m))
const clampInterval = (n: number, min = 1, max = 20) => Math.max(min, Math.min(max, n))

const useSettingsStore = create<SettingsState>((set) => ({
  ...readSettings(),
  setDefaultFocusMinutes: (m) => {
    const v = clampMinutes(m)
    const next = { ...readSettings(), defaultFocusMinutes: v }
    writeSettings(next)
    set({ defaultFocusMinutes: v })
  },
  setShortBreakMinutes: (m) => {
    const v = clampMinutes(m)
    const next = { ...readSettings(), shortBreakMinutes: v }
    writeSettings(next)
    set({ shortBreakMinutes: v })
  },
  setLongBreakMinutes: (m) => {
    const v = clampMinutes(m)
    const next = { ...readSettings(), longBreakMinutes: v }
    writeSettings(next)
    set({ longBreakMinutes: v })
  },
  setLongBreakInterval: (n) => {
    const v = clampInterval(n)
    const next = { ...readSettings(), longBreakInterval: v }
    writeSettings(next)
    set({ longBreakInterval: v })
  },
  setWeekStart: (w) => {
    const next = { ...readSettings(), weekStart: w }
    writeSettings(next)
    set({ weekStart: w })
  },
  setTimezone: (tz) => {
    const next = { ...readSettings(), timezone: tz }
    writeSettings(next)
    set({ timezone: tz })
  },
  updateLunar: (partial: Partial<Settings>) => {
    const next = { ...readSettings(), ...partial }
    writeSettings(next)
    set(partial)
  },
  updateFocusSettings: (partial: Partial<Settings>) => {
    const next = { ...readSettings(), ...partial }
    writeSettings(next)
    set(partial)
  },
}))

export default useSettingsStore
export type { WeekStart, LunarSource }
