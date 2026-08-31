import { useState, useEffect } from 'react'
import api from '../api'
import Layout from './Layout'
import { header, card, field, btnPrim, Icon } from './ui'

export default function Goals() {
  const [goals, setGoals] = useState([])
  const [summary, setSummary] = useState(null)
  const [title, setTitle] = useState('')
  const [desc, setDesc] = useState('')
  const [loading, setLoading] = useState(true)

  const load = async () => {
    const [g, s] = await Promise.all([
      api.get('/goals/board'),
      api.get('/tasks/summary'),
    ])
    setGoals(g.data)
    setSummary(s.data)
    setLoading(false)
  }
  useEffect(() => {
    load()
  }, [])

  const add = async (e) => {
    e.preventDefault()
    if (!title.trim()) return
    await api.post('/goals', { title: title.trim(), description: desc || null })
    setTitle('')
    setDesc('')
    await load()
  }

  const toggle = async (g) => {
    await api.put(`/goals/${g.id}`, {
      status: g.status === 'done' ? 'active' : 'done',
    })
    await load()
  }
  const remove = async (g) => {
    if (!confirm('删除目标？关联的任务将失去目标关联')) return
    await api.delete(`/goals/${g.id}`)
    await load()
  }

  return (
    <Layout summary={summary} selected="goals" onSelect={() => {}}>
      <main className="flex-1 overflow-y-auto pb-20 md:pb-0">
        <header className={header}>
          <div className="mx-auto w-full max-w-3xl">
            <h1 className="text-lg font-bold text-[#0f172a] font-display">我的目标</h1>
            <p className="text-xs text-[#475569]">
              给待办关联目标，让每件事都有方向
            </p>
          </div>
        </header>

        <div className="max-w-3xl mx-auto p-5 md:p-7">
          <form
            onSubmit={add}
            className={`${card} p-4 space-y-3 mb-6`}
          >
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="目标标题，例如：三个月减重 5 公斤"
              className={field}
            />
            <textarea
              value={desc}
              onChange={(e) => setDesc(e.target.value)}
              placeholder="描述（可选）"
              rows={2}
              className={field}
            />
            <button type="submit" className={btnPrim}>
              + 新建目标
            </button>
          </form>

          {loading ? (
            <p className="text-[#94a3b8] text-sm">加载中…</p>
          ) : goals.length === 0 ? (
            <p className="text-[#94a3b8] text-sm">还没有目标，先建一个吧。</p>
          ) : (
            <div className="space-y-3">
              {goals.map((g) => (
                <div
                  key={g.id}
                  className={`flex items-start gap-3.5 p-4 rounded-2xl border transition ${
                    g.status === 'done'
                      ? 'bg-white/30 border-white/75'
                      : 'bg-white/55 border-white/75 shadow-[0_8px_24px_-12px_rgba(8,145,178,0.30)]'
                  }`}
                >
                  <button
                    onClick={() => toggle(g)}
                    aria-label="切换目标完成"
                    className={`mt-0.5 w-[22px] h-[22px] shrink-0 rounded-lg border-2 grid place-items-center text-white text-[13px] transition ${
                      g.status === 'done'
                        ? 'brand-gradient border-transparent'
                        : 'border-[#94a3b8] hover:border-[#06b6d4]'
                    }`}
                  >
                    {g.status === 'done' ? '✓' : ''}
                  </button>
                  <div className="flex-1 min-w-0">
                    <div
                      className={`text-sm font-semibold ${
                        g.status === 'done'
                          ? 'line-through text-[#94a3b8]'
                          : 'text-[#0f172a]'
                      }`}
                    >
                      {g.title}
                    </div>
                    {g.description && (
                      <div className="text-xs text-[#94a3b8] mt-1">
                        {g.description}
                      </div>
                    )}
                    {g.deadline && (
                      <div className="text-xs text-[#94a3b8] mt-1">
                        截止：{g.deadline}
                      </div>
                    )}

                    <div className="mt-2.5">
                      <div className="flex items-center justify-between text-[11px] text-[#475569] mb-1">
                        <span>
                          完成 {g.done}/{g.total}
                          {g.overdue > 0 && (
                            <span className="text-[#ef4444] ml-2">
                              逾期 {g.overdue}
                            </span>
                          )}
                        </span>
                        <span className="font-semibold text-[#475569]">
                          {g.progress}%
                        </span>
                      </div>
                      <div className="h-2 rounded-full bg-white/60 overflow-hidden">
                        <div
                          className="h-full rounded-full brand-gradient"
                          style={{ width: `${g.progress}%` }}
                        ></div>
                      </div>
                    </div>
                  </div>
                  <button
                    onClick={() => remove(g)}
                    className="text-[#cbd5e1] hover:text-[#ef4444] text-sm transition shrink-0"
                    title="删除"
                    aria-label="删除"
                  >
                    <Icon.close />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>
    </Layout>
  )
}
