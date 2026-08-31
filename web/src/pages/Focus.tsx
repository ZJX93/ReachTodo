import { useState, useEffect, useRef } from 'react'
import api from '../api'
import Layout from './Layout'
import { header, cardLg, field, btnPrim, gradText } from './ui'
import useSettingsStore from '../store/settingsStore'

const FOCUS_PRESETS = [15, 25, 45, 60]

const MODE_META = {
  focus: {
    label: '专注模式',
    action: '开始专注',
    color: '#06b6d4',
  },
  shortBreak: {
    label: '短休息',
    action: '开始休息',
    color: '#14b8a6',
  },
  longBreak: {
    label: '长休息',
    action: '开始休息',
    color: '#2563eb',
  },
}

type Mode = keyof typeof MODE_META

// 聚焦/休息设置面板里的步进器
function Stepper({ value, onChange, min = 1, max = 180, step = 1, unit }) {
  const dec = () => onChange(Math.max(min, value - step))
  const inc = () => onChange(Math.min(max, value + step))
  return (
    <div className="flex items-center justify-between gap-2">
      <button
        onClick={dec}
        disabled={value <= min}
        aria-label="减少"
        className="w-8 h-8 grid place-items-center rounded-lg border border-white/75 bg-white/55 text-[#475569] text-base font-semibold hover:bg-white/80 transition disabled:opacity-40"
      >
        −
      </button>
      <div className="flex-1 text-center">
        <span className="text-xl font-extrabold tabular-nums text-[#0f172a]">{value}</span>
        {unit && <span className="ml-0.5 text-[11px] text-[#475569]">{unit}</span>}
      </div>
      <button
        onClick={inc}
        disabled={value >= max}
        aria-label="增加"
        className="w-8 h-8 grid place-items-center rounded-lg border border-white/75 bg-white/55 text-[#475569] text-base font-semibold hover:bg-white/80 transition disabled:opacity-40"
      >
        +
      </button>
    </div>
  )
}

function TimerCard({ title, children }) {
  return (
    <div className="rounded-2xl bg-white/55 border border-white/75 p-3 flex flex-col gap-2">
      <div className="text-[11px] text-[#475569] font-medium text-center">{title}</div>
      {children}
    </div>
  )
}

export default function Focus() {
  const settings = useSettingsStore()
  const [mode, setMode] = useState<Mode>('focus')
  const [minutes, setMinutes] = useState(settings.defaultFocusMinutes)
  const [remaining, setRemaining] = useState(settings.defaultFocusMinutes * 60)
  const [running, setRunning] = useState(false)
  const [sessionsDone, setSessionsDone] = useState(0)
  const [tasks, setTasks] = useState([])
  const [taskId, setTaskId] = useState('')
  const [logged, setLogged] = useState<number | null>(null)
  const [sessions, setSessions] = useState([])
  const [summary, setSummary] = useState(null)
  const [showSettings, setShowSettings] = useState(false)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const meta = MODE_META[mode]

  const refresh = async () => {
    const [t, s, sm] = await Promise.all([
      api.get('/tasks', { params: { status: 'todo' } }),
      api.get('/focus'),
      api.get('/tasks/summary'),
    ])
    setTasks(t.data)
    setSessions(s.data)
    setSummary(sm.data)
  }
  useEffect(() => {
    refresh()
  }, [])

  // 设置变更时，若未在计时则同步当前模式对应的时长
  useEffect(() => {
    if (running) return
    const next =
      mode === 'focus'
        ? settings.defaultFocusMinutes
        : mode === 'shortBreak'
          ? settings.shortBreakMinutes
          : settings.longBreakMinutes
    setMinutes(next)
    setRemaining(next * 60)
  }, [
    settings.defaultFocusMinutes,
    settings.shortBreakMinutes,
    settings.longBreakMinutes,
    mode,
    running,
  ])

  useEffect(() => {
    if (running) {
      timerRef.current = setInterval(() => {
        setRemaining((r) => {
          if (r <= 1) {
            if (timerRef.current) clearInterval(timerRef.current)
            setRunning(false)
            handleFinish()
            return 0
          }
          return r - 1
        })
      }, 1000)
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [running])

  const switchMode = (nextMode: Mode) => {
    setRunning(false)
    if (timerRef.current) clearInterval(timerRef.current)
    setMode(nextMode)
    const nextMinutes =
      nextMode === 'focus'
        ? settings.defaultFocusMinutes
        : nextMode === 'shortBreak'
          ? settings.shortBreakMinutes
          : settings.longBreakMinutes
    setMinutes(nextMinutes)
    setRemaining(nextMinutes * 60)
    setLogged(null)
  }

  const start = () => {
    if (remaining === 0) setRemaining(minutes * 60)
    setRunning(true)
  }
  const pause = () => {
    setRunning(false)
    if (timerRef.current) clearInterval(timerRef.current)
  }
  const reset = () => {
    setRunning(false)
    if (timerRef.current) clearInterval(timerRef.current)
    setRemaining(minutes * 60)
    setLogged(null)
  }
  const setFocusPreset = (m: number) => {
    if (running) return
    setMode('focus')
    setMinutes(m)
    setRemaining(m * 60)
    setLogged(null)
  }

  const handleFinish = async () => {
    if (mode === 'focus') {
      try {
        await api.post('/focus', {
          task_id: taskId ? Number(taskId) : null,
          minutes,
        })
        setLogged(minutes)
        refresh()
      } catch {
        // 忽略记录失败，不打断专注体验
      }
      const nextCount = sessionsDone + 1
      setSessionsDone(nextCount)
      if (nextCount % settings.longBreakInterval === 0) {
        switchMode('longBreak')
      } else {
        switchMode('shortBreak')
      }
    } else {
      // 休息结束回到专注
      switchMode('focus')
    }
  }

  const mm = String(Math.floor(remaining / 60)).padStart(2, '0')
  const ss = String(remaining % 60).padStart(2, '0')
  const totalSec = minutes * 60
  const elapsed = totalSec - remaining
  const deg = totalSec ? (elapsed / totalSec) * 360 : 0

  return (
    <Layout summary={summary} selected="focus" onSelect={() => {}}>
      <main className="flex-1 overflow-y-auto pb-20 md:pb-0">
        <header className={header}>
          <h1 className="text-lg font-bold text-[#0f172a] font-display">
            专注 / 番茄钟
          </h1>
          <p className="text-xs text-[#475569]">选个任务，进入心流，时间到自动切换</p>
        </header>

        <div className="p-5 md:p-7 max-w-2xl mx-auto space-y-6">
          {/* 计时器 */}
          <div className={`${cardLg} p-6 md:p-8 text-center`}>
            {/* 模式徽章 */}
            <div className="mb-5 inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/55 border border-white/75">
              <span
                className="w-2 h-2 rounded-full"
                style={{ backgroundColor: meta.color }}
              />
              <span className="text-xs font-semibold text-[#475569]">{meta.label}</span>
              {mode === 'focus' && (
                <span className="text-[11px] text-[#94a3b8]">已完成 {sessionsDone} 轮</span>
              )}
            </div>

            <div
              className="relative w-56 h-56 md:w-60 md:h-60 rounded-full grid place-items-center mx-auto"
              style={{
                background: `conic-gradient(${meta.color} ${deg}deg, #e2e8f0 ${deg}deg)`,
              }}
            >
              <div className="absolute inset-[18px] rounded-full bg-white shadow-[0_8px_24px_-12px_rgba(8,145,178,0.30)] grid place-items-center">
                <div className={`text-5xl font-extrabold tabular-nums ${gradText}`}>
                  {mm}:{ss}
                </div>
              </div>
            </div>

            {/* 专注模式下的快捷预设 */}
            {mode === 'focus' && (
              <div className="flex justify-center flex-wrap gap-2 mt-6">
                {FOCUS_PRESETS.map((p) => (
                  <button
                    key={p}
                    onClick={() => setFocusPreset(p)}
                    disabled={running}
                    className={`px-4 py-1.5 rounded-full text-sm font-semibold transition ${
                      minutes === p && mode === 'focus'
                        ? 'text-white brand-gradient shadow-[0_8px_24px_-12px_rgba(8,145,178,0.30)]'
                        : 'bg-white/60 text-[#475569] hover:bg-white/80 disabled:opacity-50'
                    }`}
                  >
                    专注 {p}
                  </button>
                ))}
              </div>
            )}

            {/* 休息模式提示 */}
            {mode !== 'focus' && (
              <p className="mt-6 text-sm text-[#475569]">
                放松一下，{mode === 'shortBreak' ? settings.shortBreakMinutes : settings.longBreakMinutes} 分钟后继续专注
              </p>
            )}

            <div className="flex justify-center items-center gap-3 mt-5 flex-wrap">
              {running ? (
                <button
                  onClick={pause}
                  className="px-7 py-2.5 rounded-xl bg-[#f59e0b] hover:bg-[#d97706] text-white text-sm font-semibold transition"
                >
                  暂停
                </button>
              ) : (
                <button onClick={start} className={btnPrim + ' px-7 py-2.5'}>
                  {meta.action}
                </button>
              )}
              {mode !== 'focus' && (
                <button
                  onClick={() => switchMode('focus')}
                  className="px-5 py-2.5 rounded-xl text-sm text-[#475569] hover:bg-white/60 transition"
                >
                  跳过休息
                </button>
              )}
              <button
                onClick={reset}
                className="px-5 py-2.5 rounded-xl text-sm text-[#475569] hover:bg-white/60 transition"
              >
                重置
              </button>
            </div>

            {logged && (
              <div className="mt-4 text-sm text-[#059669] font-medium">
                已记录 {logged} 分钟专注
              </div>
            )}

            {/* 计时设置折叠面板 */}
            <div className="mt-6 pt-5 border-t border-white/60">
              <button
                onClick={() => setShowSettings((s) => !s)}
                className="text-xs text-[#475569] hover:text-[#0f172a] transition flex items-center justify-center gap-1 mx-auto"
              >
                <span>{showSettings ? '▾' : '▸'}</span>
                <span>计时设置</span>
              </button>
              {showSettings && (
                <div className="mt-4 grid grid-cols-2 gap-3 text-left">
                  <TimerCard title="专注时长">
                    <Stepper
                      value={settings.defaultFocusMinutes}
                      onChange={settings.setDefaultFocusMinutes}
                      unit="min"
                    />
                  </TimerCard>
                  <TimerCard title="短休息">
                    <Stepper
                      value={settings.shortBreakMinutes}
                      onChange={settings.setShortBreakMinutes}
                      unit="min"
                    />
                  </TimerCard>
                  <TimerCard title="长休息">
                    <Stepper
                      value={settings.longBreakMinutes}
                      onChange={settings.setLongBreakMinutes}
                      unit="min"
                    />
                  </TimerCard>
                  <TimerCard title="长休息间隔">
                    <Stepper
                      value={settings.longBreakInterval}
                      onChange={settings.setLongBreakInterval}
                      min={1}
                      max={20}
                      unit="个"
                    />
                  </TimerCard>
                </div>
              )}
            </div>
          </div>

          {/* 关联任务 */}
          {mode === 'focus' && (
            <div>
              <label className="block text-sm text-[#475569] mb-1">
                关联任务（可选）
              </label>
              <select
                value={taskId}
                onChange={(e) => setTaskId(e.target.value)}
                className={field}
              >
                <option value="">不关联（仅记录专注时长）</option>
                {tasks.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.title}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* 最近专注 */}
          <div>
            <h2 className="font-bold text-[#475569] mb-2">最近专注</h2>
            {sessions.length === 0 ? (
              <p className="text-sm text-[#cbd5e1]">还没有专注记录</p>
            ) : (
              <div className="space-y-1.5">
                {sessions.slice(0, 8).map((s) => (
                  <div
                    key={s.id}
                    className="flex items-center justify-between text-sm text-[#475569] bg-white/55 border border-white/75 rounded-xl px-3 py-2.5"
                  >
                    <span className="font-semibold text-[#0f172a]">
                      {s.minutes} 分钟
                    </span>
                    <span className="text-xs text-[#94a3b8]">
                      {new Date(s.started_at).toLocaleString()}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </main>
    </Layout>
  )
}
