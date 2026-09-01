import { useEffect, useState } from 'react'
import api from '../api'
import Layout from './Layout'
import { btnPrim, card, gradText, header, Icon } from './ui'
import type { Summary } from '../types'
import {
  MOODS,
  habitsApi,
  type CheckinPayload,
  type Habit,
  type HabitDraft,
  type HeatCell,
  type Today,
  type TodayItem,
} from '../services/habits'
import HabitCard from './habits/HabitCard'
import HabitEditor from './habits/HabitEditor'
import HabitDetail from './habits/HabitDetail'

const HEAT_DAYS = 119 // 17 周，按整周对齐后热力图观感最整齐

function StatCard({
  label,
  value,
  hint,
  icon,
  color,
}: {
  label: string
  value: string | number
  hint?: string
  icon: React.ReactNode
  color: string
}) {
  return (
    <div className={`${card} p-4 flex items-center gap-3.5`}>
      <div
        className="w-10 h-10 rounded-xl flex items-center justify-center text-white shrink-0 shadow-sm"
        style={{ background: color }}
      >
        {icon}
      </div>
      <div className="min-w-0">
        <div className="text-xs text-[#94a3b8] font-medium">{label}</div>
        <div className={`text-[22px] font-extrabold mt-0.5 ${gradText}`}>{value}</div>
        {hint && <div className="text-[11px] text-[#94a3b8] mt-0.5">{hint}</div>}
      </div>
    </div>
  )
}

/** 完成度 → 色阶：0 为空槽，越高越接近品牌青绿 */
function rateColor(rate: number): string {
  if (rate <= 0) return 'rgba(148,163,184,0.18)'
  return `rgba(20,184,166,${(0.25 + Math.min(1, rate) * 0.75).toFixed(3)})`
}

function groupByWeek(cells: HeatCell[]): (HeatCell | null)[][] {
  if (!cells.length) return []
  const weeks: (HeatCell | null)[][] = []
  const first = new Date(`${cells[0].date}T00:00:00`)
  let week: (HeatCell | null)[] = Array(first.getDay()).fill(null)
  for (const c of cells) {
    week.push(c)
    if (week.length === 7) {
      weeks.push(week)
      week = []
    }
  }
  if (week.length) {
    while (week.length < 7) week.push(null)
    weeks.push(week)
  }
  return weeks
}

export default function Habits() {
  const [summary, setSummary] = useState<Summary | null>(null)
  const [today, setToday] = useState<Today | null>(null)
  const [heat, setHeat] = useState<HeatCell[]>([])
  const [loading, setLoading] = useState(true)
  const [busyId, setBusyId] = useState<string | null>(null)
  const [showArchived, setShowArchived] = useState(false)

  const [editorOpen, setEditorOpen] = useState(false)
  const [editing, setEditing] = useState<Habit | null>(null)
  const [detail, setDetail] = useState<TodayItem | null>(null)

  const reload = async () => {
    const [t, h] = await Promise.all([habitsApi.today(), habitsApi.heatmap(HEAT_DAYS)])
    setToday(t.data)
    setHeat(h.data)
  }

  useEffect(() => {
    let alive = true
    ;(async () => {
      try {
        const [sm, t, h] = await Promise.all([
          api.get('/tasks/summary'),
          habitsApi.today(),
          habitsApi.heatmap(HEAT_DAYS),
        ])
        if (!alive) return
        setSummary(sm.data)
        setToday(t.data)
        setHeat(h.data)
      } finally {
        if (alive) setLoading(false)
      }
    })()
    return () => {
      alive = false
    }
  }, [])

  const handleCheckin = async (habit: TodayItem, payload: CheckinPayload) => {
    setBusyId(habit.id)
    try {
      await habitsApi.checkin(habit.id, payload)
      await reload()
    } finally {
      setBusyId(null)
    }
  }

  const submitEditor = async (draft: HabitDraft) => {
    if (editing) {
      await habitsApi.update(editing.id, draft)
    } else {
      await habitsApi.create(draft)
    }
    setEditorOpen(false)
    setEditing(null)
    setDetail(null)
    await reload()
  }

  const openEdit = (habit: TodayItem) => {
    setEditing(habit as Habit)
    setEditorOpen(true)
  }

  const removeHabit = async (habit: TodayItem) => {
    if (!window.confirm(`确定删除「${habit.name}」吗？其它设备同步后也会删除。`)) return
    await habitsApi.remove(habit.id)
    setDetail(null)
    await reload()
  }

  const setMood = async (score: number) => {
    await habitsApi.setMood({ score })
    await reload()
  }

  const items = today?.habits ?? []
  const visible = showArchived ? items : items.filter((h) => !h.archived)
  const weeks = groupByWeek(heat)
  const mood = today?.mood ?? null

  return (
    <Layout summary={summary} selected="habits" onSelect={() => {}}>
      <main className="flex-1 overflow-y-auto pb-20 md:pb-0">
        <header className={header}>
          <div className="mx-auto w-full max-w-[1600px] flex items-center justify-between gap-3">
            <div className="min-w-0">
              <h1 className="text-lg font-bold text-[#0f172a] font-display">习惯站</h1>
              <p className="text-xs text-[#475569]">每天一点点，时间会替你记账</p>
            </div>
            <button
              onClick={() => {
                setEditing(null)
                setEditorOpen(true)
              }}
              className={`${btnPrim} flex items-center gap-1.5 shrink-0`}
            >
              <Icon.plus className="w-4 h-4" />
              新建习惯
            </button>
          </div>
        </header>

        <div className="max-w-[1600px] mx-auto p-3 md:p-4 space-y-6">
          {loading || !today ? (
            <div className="text-sm text-[#94a3b8] py-10 text-center">加载中…</div>
          ) : (
            <>
              {/* 今日概览 */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <StatCard
                  label="今日完成"
                  value={`${today.done}/${today.total}`}
                  hint={`${today.percent}%`}
                  icon={<Icon.check className="w-5 h-5" />}
                  color="linear-gradient(135deg, #2563eb, #06b6d4)"
                />
                <StatCard
                  label="全勤连续"
                  value={`${today.streak} 天`}
                  hint="当天全部完成"
                  icon={<Icon.flame className="w-5 h-5" />}
                  color="linear-gradient(135deg, #f97316, #ef4444)"
                />
                <StatCard
                  label="进行中"
                  value={visible.length}
                  hint="个习惯"
                  icon={<Icon.flag className="w-5 h-5" />}
                  color="linear-gradient(135deg, #06b6d4, #14b8a6)"
                />
                <div className={`${card} p-4`}>
                  <div className="text-xs text-[#94a3b8] font-medium mb-2">今日心情</div>
                  <div className="flex items-center justify-between gap-1">
                    {MOODS.map((m) => (
                      <button
                        key={m.score}
                        onClick={() => setMood(m.score)}
                        title={m.label}
                        aria-label={m.label}
                        className={`flex-1 h-9 rounded-xl text-lg grid place-items-center transition ${
                          mood === m.score
                            ? 'bg-[rgba(37,99,235,0.10)] ring-2 ring-[#06b6d4]'
                            : 'hover:bg-white/60'
                        }`}
                      >
                        {m.emoji}
                      </button>
                    ))}
                  </div>
                  <div className="text-[11px] text-[#94a3b8] mt-2">
                    {mood ? MOODS.find((m) => m.score === mood)?.label : '还没记录'}
                  </div>
                </div>
              </div>

              {/* 今日打卡 */}
              <section className={`${card} p-5`}>
                <div className="flex items-center justify-between mb-4">
                  <h2 className="font-bold text-[#475569]">今日打卡</h2>
                  <span className="text-[11px] text-[#94a3b8]">{today.date}</span>
                </div>
                {visible.length === 0 ? (
                  <div className="text-center py-10">
                    <p className="text-sm text-[#94a3b8] mb-4">
                      还没有习惯，从一件每天都能做的小事开始吧。
                    </p>
                    <button
                      onClick={() => {
                        setEditing(null)
                        setEditorOpen(true)
                      }}
                      className={btnPrim}
                    >
                      新建第一个习惯
                    </button>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                    {visible.map((h) => (
                      <HabitCard
                        key={h.id}
                        habit={h}
                        busy={busyId === h.id}
                        onCheckin={handleCheckin}
                        onDetail={setDetail}
                      />
                    ))}
                  </div>
                )}
              </section>

              {/* 坚持轨迹 */}
              <section className={`${card} p-5`}>
                <div className="flex items-center justify-between mb-4">
                  <h2 className="font-bold text-[#475569]">坚持轨迹</h2>
                  <span className="text-[11px] text-[#94a3b8]">
                    近 {Math.round(HEAT_DAYS / 7)} 周
                  </span>
                </div>
                {weeks.length === 0 ? (
                  <p className="text-sm text-[#cbd5e1] text-center py-6">
                    打卡后这里会生长出你的轨迹
                  </p>
                ) : (
                  <>
                    <div className="overflow-x-auto">
                      <div className="flex gap-1 min-w-max">
                        {weeks.map((week, wi) => (
                          <div key={wi} className="flex flex-col gap-1">
                            {week.map((cell, di) =>
                              cell ? (
                                <div
                                  key={di}
                                  title={`${cell.date} 完成 ${cell.done}/${cell.total}`}
                                  className="w-3.5 h-3.5 rounded-[3px]"
                                  style={{ backgroundColor: rateColor(cell.rate) }}
                                />
                              ) : (
                                <div key={di} className="w-3.5 h-3.5" />
                              ),
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                    <div className="flex items-center justify-end gap-1.5 mt-3 text-[10px] text-[#94a3b8]">
                      <span>少</span>
                      {[0, 0.25, 0.5, 0.75, 1].map((r) => (
                        <span
                          key={r}
                          className="w-3 h-3 rounded-[3px]"
                          style={{ backgroundColor: rateColor(r) }}
                        />
                      ))}
                      <span>多</span>
                    </div>
                  </>
                )}
              </section>
            </>
          )}
        </div>
      </main>

      <HabitEditor
        open={editorOpen}
        habit={editing}
        onClose={() => {
          setEditorOpen(false)
          setEditing(null)
        }}
        onSubmit={submitEditor}
      />

      <HabitDetail
        habit={detail}
        todayDate={today?.date ?? ''}
        onClose={() => setDetail(null)}
        onCheckin={handleCheckin}
        onEdit={openEdit}
        onDelete={removeHabit}
      />
    </Layout>
  )
}
