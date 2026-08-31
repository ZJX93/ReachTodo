import { useState, useEffect } from 'react'
import api from '../api'
import Layout from './Layout'
import { header, card, gradText, Icon } from './ui'

function StatCard({ label, value, hint, icon, color }) {
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

export default function Stats() {
  const [data, setData] = useState(null)
  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(true)

  const load = async () => {
    const [s, sm] = await Promise.all([
      api.get('/stats/summary'),
      api.get('/tasks/summary'),
    ])
    setData(s.data)
    setSummary(sm.data)
    setLoading(false)
  }
  useEffect(() => {
    load()
  }, [])

  if (loading || !data) {
    return (
      <Layout summary={summary} selected="stats" onSelect={() => {}}>
        <main className="flex-1 p-6 text-sm text-[#94a3b8]">加载中…</main>
      </Layout>
    )
  }

  const weekArr = Array.isArray(data.week) ? data.week : []
  const weekVal = (d) => (typeof d === 'number' ? d : d?.count ?? 0)
  const weekLabel = (d, i) =>
    typeof d === 'number'
      ? ['一', '二', '三', '四', '五', '六', '日'][i]
      : d?.label ?? ['一', '二', '三', '四', '五', '六', '日'][i]
  const weekMax = weekArr.length ? Math.max(...weekArr.map(weekVal), 1) : 1

  const doneTotal = data.per_category?.reduce((s, c) => s + (c.done ?? 0), 0) ?? 0
  const todoTotal = data.per_category?.reduce((s, c) => s + (c.todo ?? 0), 0) ?? 0

  return (
    <Layout summary={summary} selected="stats" onSelect={() => {}}>
      <main className="flex-1 overflow-y-auto pb-20 md:pb-0">
        <header className={header}>
          <div className="mx-auto w-full max-w-[1600px]">
            <h1 className="text-lg font-bold text-[#0f172a] font-display">
              周回顾 / 数据看板
            </h1>
            <p className="text-xs text-[#475569]">回顾这一周，看清节奏与方向</p>
          </div>
        </header>

        <div className="max-w-[1600px] mx-auto p-3 md:p-4 space-y-6">
          {/* 核心指标 */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatCard
              label="本周完成"
              value={data.week_completed}
              hint="近 7 天"
              icon={<Icon.check className="w-5 h-5" />}
              color="linear-gradient(135deg, #2563eb, #06b6d4)"
            />
            <StatCard
              label="连续完成"
              value={`${data.streak} 天`}
              hint="streak"
              icon={<Icon.flame className="w-5 h-5" />}
              color="linear-gradient(135deg, #f97316, #ef4444)"
            />
            <StatCard
              label="今日专注"
              value={`${data.focus_minutes_today} 分`}
              hint="番茄钟"
              icon={<Icon.clock className="w-5 h-5" />}
              color="linear-gradient(135deg, #06b6d4, #14b8a6)"
            />
            <StatCard
              label="本周专注"
              value={`${data.focus_minutes_week} 分`}
              hint="累计"
              icon={<Icon.chart className="w-5 h-5" />}
              color="linear-gradient(135deg, #8b5cf6, #6366f1)"
            />
          </div>

          {/* 近 7 天完成趋势 */}
          {weekArr.length > 0 && (
            <section className={`${card} p-5`}>
              <div className="flex items-center justify-between mb-5">
                <h2 className="font-bold text-[#475569]">近 7 天完成趋势</h2>
                <span className="text-[11px] text-[#94a3b8]">共 {weekArr.reduce((s, d) => s + weekVal(d), 0)} 项</span>
              </div>
              <div className="flex gap-3 items-end h-40 px-1">
                {weekArr.map((d, i) => {
                  const val = weekVal(d)
                  const h = weekMax ? (val / weekMax) * 100 : 0
                  return (
                    <div key={i} className="flex-1 flex flex-col items-center gap-2 h-full justify-end group">
                      <div className="relative w-full max-w-[36px] flex flex-col justify-end h-full">
                        <div
                          className="w-full rounded-t-xl brand-gradient transition-all"
                          style={{ height: `${Math.max(h, 6)}%` }}
                        ></div>
                        {val > 0 && (
                          <span className="absolute -top-5 left-1/2 -translate-x-1/2 text-[10px] font-semibold text-[#475569] opacity-0 group-hover:opacity-100 transition">
                            {val}
                          </span>
                        )}
                      </div>
                      <span className="text-[11px] text-[#94a3b8] font-medium">{weekLabel(d, i)}</span>
                    </div>
                  )
                })}
              </div>
            </section>
          )}

          {/* 目标进展 */}
          <section className={`${card} p-5`}>
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-bold text-[#475569]">目标进展</h2>
              <span className="text-[11px] text-[#94a3b8]">
                {data.goals_progress.length} 个目标
              </span>
            </div>
            {data.goals_progress.length === 0 ? (
              <p className="text-sm text-[#cbd5e1]">
                还没有目标，去「我的目标」建一个吧。
              </p>
            ) : (
              <div className="space-y-4">
                {data.goals_progress.map((g) => (
                  <div key={g.id}>
                    <div className="flex items-center justify-between text-sm mb-1.5">
                      <span className="font-semibold text-[#0f172a] truncate pr-3">
                        {g.title}
                      </span>
                      <span className="text-xs font-bold text-[#0f172a]">
                        {g.progress}%
                      </span>
                    </div>
                    <div className="flex items-center gap-3">
                      <div className="flex-1 h-2 rounded-full bg-white/60 overflow-hidden">
                        <div
                          className="h-full rounded-full brand-gradient"
                          style={{ width: `${g.progress}%` }}
                        ></div>
                      </div>
                      <span className="text-[11px] text-[#94a3b8] w-14 text-right shrink-0">
                        {g.done}/{g.total}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* 各维度分布 */}
          <section className={`${card} p-5`}>
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-bold text-[#475569]">各维度分布</h2>
              <span className="text-[11px] text-[#94a3b8]">
                待办 {todoTotal} · 完成 {doneTotal}
              </span>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {data.per_category.map((c) => {
                const total = c.todo + c.done
                const pct = total ? Math.round((c.done / total) * 100) : 0
                return (
                  <div
                    key={c.name}
                    className="rounded-xl border border-white/60 bg-white/50 p-4 flex flex-col gap-2.5"
                  >
                    <div className="flex items-center gap-2.5 min-w-0">
                      <span
                        className="w-8 h-8 rounded-lg flex items-center justify-center text-base shrink-0"
                        style={{ backgroundColor: `${c.color}22` }}
                      >
                        {c.icon}
                      </span>
                      <div className="min-w-0">
                        <div className="text-sm font-semibold text-[#0f172a] truncate">
                          {c.name}
                        </div>
                        <div className="text-[10px] text-[#94a3b8]">完成率 {pct}%</div>
                      </div>
                    </div>
                    <div className="flex-1 h-1.5 rounded-full bg-white/60 overflow-hidden">
                      <div
                        className="h-full rounded-full"
                        style={{ width: `${pct}%`, backgroundColor: c.color }}
                      ></div>
                    </div>
                    <div className="flex items-center justify-between text-[11px] text-[#94a3b8]">
                      <span>
                        待办 <b className="text-[#0f172a]">{c.todo}</b>
                      </span>
                      <span>
                        完成 <b className="text-[#0f172a]">{c.done}</b>
                      </span>
                    </div>
                  </div>
                )
              })}
            </div>
          </section>
        </div>
      </main>
    </Layout>
  )
}
