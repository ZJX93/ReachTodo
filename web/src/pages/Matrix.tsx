import { useState, useEffect, useCallback } from 'react'
import api from '../api'
import Layout from './Layout'
import TaskCard from './components/TaskCard'
import { header, card } from './ui'

// 象限强调色：用品牌语义色替代旧紫红，保留「紧急×重要」含义
const ACCENT = {
  q1: 'border-t-[#ef4444]',
  q2: 'border-t-[#2563eb]',
  q3: 'border-t-[#f59e0b]',
  q4: 'border-t-[#94a3b8]',
}

export default function Matrix() {
  const [quadrants, setQuadrants] = useState([])
  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    const [m, s] = await Promise.all([
      api.get('/tasks/matrix'),
      api.get('/tasks/summary'),
    ])
    setQuadrants(m.data)
    setSummary(s.data)
    setLoading(false)
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const handleToggle = async (task) => {
    await api.put(`/tasks/${task.id}`, {
      status: task.status === 'done' ? 'todo' : 'done',
    })
    await load()
  }
  const handleDelete = async (task) => {
    if (!confirm('确定删除该任务？')) return
    await api.delete(`/tasks/${task.id}`)
    await load()
  }

  return (
    <Layout summary={summary} selected="matrix" onSelect={() => {}}>
      <main className="flex-1 overflow-y-auto pb-20 md:pb-0">
        <header className={header}>
          <div className="mx-auto w-full max-w-6xl">
            <h1 className="text-lg font-bold text-[#0f172a] font-display">
              艾森豪威尔四象限
            </h1>
            <p className="text-xs text-[#475569]">
              按「重要 × 紧急」排优先级，先搞定 Q1
            </p>
          </div>
        </header>

        <div className="max-w-6xl mx-auto p-5 md:p-7">
          {loading ? (
            <p className="text-sm text-[#94a3b8]">加载中…</p>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {quadrants.map((q) => (
                <section
                  key={q.key}
                  className={`${card} border-t-4 ${ACCENT[q.key]} p-4`}
                >
                  <div className="flex items-baseline justify-between mb-3">
                    <h2 className="font-bold text-[#475569]">{q.title}</h2>
                    <span className="text-xs text-[#94a3b8]">{q.sub}</span>
                  </div>
                  {q.tasks.length === 0 ? (
                    <p className="text-sm text-[#cbd5e1]">暂无任务</p>
                  ) : (
                    <div className="space-y-2.5">
                      {q.tasks.map((t) => (
                        <TaskCard
                          key={t.id}
                          task={t}
                          onToggle={handleToggle}
                          onDelete={handleDelete}
                        />
                      ))}
                    </div>
                  )}
                </section>
              ))}
            </div>
          )}
        </div>
      </main>
    </Layout>
  )
}
