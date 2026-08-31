import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import useSettingsStore from '../store/settingsStore'
import ProfileModal from './ProfileModal'
import { cardLg, gradText } from './ui'

// 时区选项：优先用浏览器原生 IANA 列表（Chrome/Edge/Firefox 新版支持），
// 不支持时回落到一份常用清单，保证老浏览器也能选。
const ALL_TZ =
  typeof Intl !== 'undefined' && Intl.supportedValuesOf
    ? Intl.supportedValuesOf('timeZone')
    : [
        'Asia/Shanghai', 'Asia/Hong_Kong', 'Asia/Tokyo', 'Asia/Singapore',
        'Asia/Kolkata', 'Asia/Dubai', 'Australia/Sydney', 'Europe/London',
        'Europe/Paris', 'Europe/Moscow', 'America/New_York', 'America/Chicago',
        'America/Denver', 'America/Los_Angeles', 'UTC',
      ]

// 取某时区在指定时刻的 UTC 偏移短标签，如 "GMT+8"
function tzOffsetLabel(tz, at) {
  try {
    const s = new Intl.DateTimeFormat('en-US', { timeZone: tz, timeZoneName: 'shortOffset' }).format(at)
    const m = s.match(/GMT[+-]\d+/)
    return m ? m[0] : ''
  } catch {
    return ''
  }
}

// 分段控件：视觉上是一组互斥按钮，选中态用品牌渐变高亮
function Segmented({ value, onChange, options }) {
  return (
    <div className="inline-flex p-1 rounded-xl bg-white/55 border border-white/75 gap-1">
      {options.map((o) => {
        const active = o.value === value
        return (
          <button
            key={o.value}
            onClick={() => onChange(o.value)}
            className={`px-3 py-1.5 rounded-lg text-sm font-semibold transition ${
              active
                ? 'brand-gradient text-white shadow-[0_4px_14px_-8px_rgba(8,145,178,0.45)]'
                : 'text-[#475569] hover:bg-white/60'
            }`}
          >
            {o.label}
          </button>
        )
      })}
    </div>
  )
}

// 数字步进器：用于「专注时长」等分钟数配置
function Stepper({ value, onChange, min = 1, max = 180, step = 1, unit }) {
  const dec = () => onChange(Math.max(min, value - step))
  const inc = () => onChange(Math.min(max, value + step))
  return (
    <div className="flex items-center justify-between gap-2">
      <button
        onClick={dec}
        disabled={value <= min}
        aria-label="减少"
        className="w-9 h-9 grid place-items-center rounded-xl border border-white/75 bg-white/55 text-[#475569] text-lg font-semibold hover:bg-white/80 transition disabled:opacity-40 disabled:hover:bg-white/55"
      >
        −
      </button>
      <div className="flex-1 text-center">
        <span className="text-[26px] font-extrabold tabular-nums text-[#0f172a]">{value}</span>
        {unit && <span className="ml-1 text-xs text-[#475569]">{unit}</span>}
      </div>
      <button
        onClick={inc}
        disabled={value >= max}
        aria-label="增加"
        className="w-9 h-9 grid place-items-center rounded-xl border border-white/75 bg-white/55 text-[#475569] text-lg font-semibold hover:bg-white/80 transition disabled:opacity-40 disabled:hover:bg-white/55"
      >
        +
      </button>
    </div>
  )
}

// 时长配置小卡：在设置页「时间设置」里以 2x2 网格展示
function TimerCard({ title, children }) {
  return (
    <div className="rounded-2xl bg-white/55 border border-white/75 p-4 flex flex-col gap-3">
      <div className="text-xs text-[#475569] font-medium text-center">{title}</div>
      {children}
    </div>
  )
}

function Section({ title, desc, children }) {
  return (
    <section className={`${cardLg} p-5 md:p-6`}>
      <div className="mb-4">
        <h2 className="text-base font-bold text-[#0f172a]">{title}</h2>
        {desc && <p className="text-xs text-[#475569] mt-0.5">{desc}</p>}
      </div>
      {children}
    </section>
  )
}

export default function Settings() {
  const navigate = useNavigate()
  const defaultFocusMinutes = useSettingsStore((s) => s.defaultFocusMinutes)
  const setDefaultFocusMinutes = useSettingsStore((s) => s.setDefaultFocusMinutes)
  const shortBreakMinutes = useSettingsStore((s) => s.shortBreakMinutes)
  const setShortBreakMinutes = useSettingsStore((s) => s.setShortBreakMinutes)
  const longBreakMinutes = useSettingsStore((s) => s.longBreakMinutes)
  const setLongBreakMinutes = useSettingsStore((s) => s.setLongBreakMinutes)
  const longBreakInterval = useSettingsStore((s) => s.longBreakInterval)
  const setLongBreakInterval = useSettingsStore((s) => s.setLongBreakInterval)
  const weekStart = useSettingsStore((s) => s.weekStart)
  const setWeekStart = useSettingsStore((s) => s.setWeekStart)
  const timezone = useSettingsStore((s) => s.timezone)
  const setTimezone = useSettingsStore((s) => s.setTimezone)
  const lunarSource = useSettingsStore((s) => s.lunarSource)
  const lunarApiBase = useSettingsStore((s) => s.lunarApiBase)
  const holidayApiBase = useSettingsStore((s) => s.holidayApiBase)
  const lunarApiKey = useSettingsStore((s) => s.lunarApiKey)
  const updateLunar = useSettingsStore((s) => s.updateLunar)
  const [profileOpen, setProfileOpen] = useState(false)

  // 当前所选时区的实时时钟（每秒刷新）
  const [clock, setClock] = useState(() => new Date())
  useEffect(() => {
    const id = setInterval(() => setClock(new Date()), 1000)
    return () => clearInterval(id)
  }, [])
  const clockStr = new Intl.DateTimeFormat('zh-CN', {
    timeZone: timezone,
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false,
  }).format(clock)
  const offset = tzOffsetLabel(timezone, clock)

  return (
    <div className="min-h-screen w-full px-4 md:px-8 py-6 md:py-10">
      <div className="max-w-2xl mx-auto space-y-5">
        {/* 顶部：返回 + 标题 */}
        <header className="flex items-center gap-3">
          <button
            onClick={() => navigate('/')}
            aria-label="返回"
            className="p-2 rounded-xl bg-white/55 border border-white/75 text-[#475569] hover:text-[#0f172a] hover:bg-white/80 transition"
          >
            <svg
              viewBox="0 0 24 24"
              className="w-4 h-4"
              stroke="currentColor"
              strokeWidth="2"
              fill="none"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <polyline points="15 18 9 12 15 6" />
            </svg>
          </button>
          <div>
            <h1 className={`text-xl font-bold ${gradText}`}>系统设置</h1>
            <p className="text-xs text-[#475569] mt-0.5">
              个性化你的专注与日历体验
            </p>
          </div>
        </header>

        <Section title="专注" desc="番茄钟时间参数，可在专注页面单次覆盖">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <TimerCard title="专注时长">
              <Stepper value={defaultFocusMinutes} onChange={setDefaultFocusMinutes} unit="min" />
            </TimerCard>
            <TimerCard title="短休息">
              <Stepper value={shortBreakMinutes} onChange={setShortBreakMinutes} unit="min" />
            </TimerCard>
            <TimerCard title="长休息">
              <Stepper value={longBreakMinutes} onChange={setLongBreakMinutes} unit="min" />
            </TimerCard>
            <TimerCard title="长休息间隔">
              <Stepper
                value={longBreakInterval}
                onChange={setLongBreakInterval}
                min={1}
                max={20}
                unit="个"
              />
            </TimerCard>
          </div>
        </Section>

        <Section
          title="日历"
          desc="日历表头与每周起始列的位置"
        >
          <Segmented
            value={weekStart}
            onChange={setWeekStart}
            options={[
              { value: 'sun', label: '周日' },
              { value: 'mon', label: '周一' },
            ]}
          />
        </Section>

        <Section
          title="时区"
          desc="应用使用的时区，影响「今天」判定、日历与时间的展示"
        >
          <div className="flex flex-col gap-3">
            <div className="flex items-center justify-between gap-3 flex-wrap">
              <span className="text-sm text-[#475569]">当前时区时间</span>
              <span className="text-sm font-semibold text-[#0f172a] tabular-nums">
                {clockStr} <span className="text-[#06b6d4]">{offset}</span>
              </span>
            </div>
            <label className="block">
              <span className="text-xs text-[#475569]">选择时区</span>
              <select
                value={timezone}
                onChange={(e) => setTimezone(e.target.value)}
                className="mt-1.5 w-full border border-white/75 rounded-lg px-3 py-2 text-sm bg-white/70 text-[#0f172a] focus:border-[#06b6d4] focus:ring-2 focus:ring-[#06b6d4]/20 transition"
              >
                {ALL_TZ.map((tz) => (
                  <option key={tz} value={tz}>
                    {tz}
                  </option>
                ))}
              </select>
            </label>
            <p className="text-xs text-[#94a3b8]">
              默认取浏览器所在时区（{typeof Intl !== 'undefined' ? Intl.DateTimeFormat().resolvedOptions().timeZone : '—'}）；
              若列表中没有你需要的时区，可直接在此选择相近的 IANA 时区。
            </p>
          </div>
        </Section>

        <Section
          title="农历数据"
          desc="日历中的农历 / 节气 / 黄历 / 节假日数据来源"
        >
          <div className="flex flex-col gap-3">
            <Segmented
              value={lunarSource}
              onChange={(v) => updateLunar({ lunarSource: v })}
              options={[
                { value: 'backend', label: '后端代理' },
                { value: 'custom', label: '自定义接口' },
              ]}
            />
            {lunarSource === 'custom' && (
              <div className="flex flex-col gap-3 pl-1 border-l-2 border-white/70 ml-1 py-1">
                <label className="block">
                  <span className="text-xs text-[#475569]">农历接口地址</span>
                  <input
                    type="text"
                    value={lunarApiBase}
                    onChange={(e) => updateLunar({ lunarApiBase: e.target.value })}
                    placeholder="https://api.vvhan.com/api/lunar?date={date}"
                    className="mt-1.5 w-full border border-white/75 rounded-lg px-3 py-2 text-sm bg-white/70 text-[#0f172a] focus:border-[#06b6d4] focus:ring-2 focus:ring-[#06b6d4]/20 transition"
                  />
                </label>
                <label className="block">
                  <span className="text-xs text-[#475569]">节假日接口地址</span>
                  <input
                    type="text"
                    value={holidayApiBase}
                    onChange={(e) => updateLunar({ holidayApiBase: e.target.value })}
                    placeholder="https://api.jiejiariapi.com/v1/holidays/{year}"
                    className="mt-1.5 w-full border border-white/75 rounded-lg px-3 py-2 text-sm bg-white/70 text-[#0f172a] focus:border-[#06b6d4] focus:ring-2 focus:ring-[#06b6d4]/20 transition"
                  />
                </label>
                <label className="block">
                  <span className="text-xs text-[#475569]">接口密钥（可选）</span>
                  <input
                    type="password"
                    value={lunarApiKey}
                    onChange={(e) => updateLunar({ lunarApiKey: e.target.value })}
                    placeholder="留空则不发送"
                    className="mt-1.5 w-full border border-white/75 rounded-lg px-3 py-2 text-sm bg-white/70 text-[#0f172a] focus:border-[#06b6d4] focus:ring-2 focus:ring-[#06b6d4]/20 transition"
                  />
                </label>
                <p className="text-[11px] text-[#94a3b8] leading-relaxed">
                  地址中的占位符会被替换：农历支持 <code className="px-1 rounded bg-white/60">{`{date}`}</code>（YYYY-MM-DD）、
                  <code className="px-1 rounded bg-white/60">{`{y}`}</code>/<code className="px-1 rounded bg-white/60">{`{m}`}</code>/<code className="px-1 rounded bg-white/60">{`{d}`}</code>；
                  节假日支持 <code className="px-1 rounded bg-white/60">{`{year}`}</code>。
                  密钥以 <code className="px-1 rounded bg-white/60">Authorization: Bearer</code> 发送；也可直接写进地址里。
                  自定义接口需支持 CORS 或同源访问（前端直连，密钥仅存于本机浏览器）。
                </p>
              </div>
            )}
          </div>
        </Section>

        <Section title="账户" desc="账号资料与登录安全">
          <button
            onClick={() => setProfileOpen(true)}
            className="w-full flex items-center justify-between px-4 py-3 rounded-xl bg-white/55 border border-white/75 hover:bg-white/80 transition"
          >
            <div className="text-left">
              <div className="text-sm font-semibold text-[#0f172a]">个人信息</div>
              <div className="text-xs text-[#475569] mt-0.5">
                修改邮箱、更换密码、退出登录
              </div>
            </div>
            <svg
              viewBox="0 0 24 24"
              className="w-4 h-4 text-[#94a3b8]"
              stroke="currentColor"
              strokeWidth="2"
              fill="none"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <polyline points="9 18 15 12 9 6" />
            </svg>
          </button>
        </Section>

        <footer className="text-[11px] text-[#94a3b8] text-center pb-6">
          设置仅保存在当前浏览器（localStorage），不会同步到服务器
        </footer>
      </div>

      <ProfileModal open={profileOpen} onClose={() => setProfileOpen(false)} />
    </div>
  )
}