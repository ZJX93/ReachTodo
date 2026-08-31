import { useState, useEffect, useCallback, useMemo, useRef } from 'react'
import {
  DndContext,
  closestCenter,
  PointerSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core'
import {
  SortableContext,
  arrayMove,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable'
import api from '../api'
import { useAuth } from '../auth'
import Layout from './Layout'
import SortableTaskCard from './components/SortableTaskCard'
import TaskCard from './components/TaskCard'
import TaskForm from './components/TaskForm'
import { header, field, btnPrim, Icon } from './ui'
import { todayStr } from '../utils/date'
import { getDueSoonTasks, kindLabel } from '../utils/reminders'
import useSettingsStore from '../store/settingsStore'

export default function Dashboard() {
  const { user, token } = useAuth()
  const timezone = useSettingsStore((s) => s.timezone)
  const [categories, setCategories] = useState([])
  const [goals, setGoals] = useState([])
  const [tasks, setTasks] = useState([])
  const [summary, setSummary] = useState(null)
  const [selected, setSelected] = useState('all')
  const [showForm, setShowForm] = useState(false)
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(true)
  const [showOverdue, setShowOverdue] = useState(false)

  const loadAll = useCallback(
    async (catId) => {
      catId = catId ?? selected
      const [c, g, s] = await Promise.all([
        api.get('/categories'),
        api.get('/goals'),
        api.get('/tasks/summary'),
      ])
      setCategories(c.data)
      setGoals(g.data)
      setSummary(s.data)
      const params = catId === 'all' ? {} : { category_id: catId }
      const res = await api.get('/tasks', { params })
      setTasks(res.data)
      setLoading(false)
    },
    [selected],
  )

  useEffect(() => {
    loadAll('all')
  }, [])

  useEffect(() => {
    if (categories.length) loadAll(selected)
  }, [selected])

  // 拖拽传感器：移动 6px 才激活，避免与卡片内按钮点击冲突
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
  )

  // 分组内拖拽结束：本地重排 + 连续 sort_order + 调用 /reorder 持久化
  const handleDragEnd = async (groupItems, setGroupItems, event) => {
    const { active, over } = event
    if (!over || active.id === over.id) return
    const oldIndex = groupItems.findIndex((t) => t.id === active.id)
    const newIndex = groupItems.findIndex((t) => t.id === over.id)
    if (oldIndex < 0 || newIndex < 0) return
    const next = arrayMove(groupItems, oldIndex, newIndex)
    setGroupItems(next)
    try {
      await api.put('/tasks/reorder', {
        items: next.map((t, i) => ({ id: t.id, sort_order: i })),
      })
    } catch {
      // 持久化失败：回滚到原顺序
      setGroupItems(groupItems)
    }
  }

  const handleSubmit = async (payload) => {
    await api.post('/tasks', payload)
    setShowForm(false)
    await loadAll()
  }

  const handleToggle = async (task) => {
    const prev = task.status
    const next = prev === 'done' ? 'todo' : 'done'
    setTasks((ts) => ts.map((t) => (t.id === task.id ? { ...t, status: next } : t)))
    try {
      await api.put(`/tasks/${task.id}`, { status: next })
      const s = await api.get('/tasks/summary')
      setSummary(s.data)
    } catch {
      setTasks((ts) =>
        ts.map((t) => (t.id === task.id ? { ...t, status: prev } : t)),
      )
    }
  }

  const handleDelete = async (task) => {
    if (!confirm('确定删除该任务？')) return
    await api.delete(`/tasks/${task.id}`)
    await loadAll()
  }

  // 子任务：新增 / 勾选 / 删除（均为顶层任务下的 checklist）
  const handleAddSub = async (parentId, title) => {
    const parent = tasks.find((t) => t.id === parentId)
    if (!parent) return
    try {
      const res = await api.post('/tasks', {
        title,
        category_id: parent.category_id,
        parent_id: parentId,
      })
      setTasks((ts) => [...ts, res.data])
    } catch {
      /* 错误提示由 api 拦截器统一处理 */
    }
  }

  const handleToggleSub = async (sub) => {
    const next = sub.status === 'done' ? 'todo' : 'done'
    setTasks((ts) => ts.map((t) => (t.id === sub.id ? { ...t, status: next } : t)))
    try {
      await api.put(`/tasks/${sub.id}`, { status: next })
    } catch {
      setTasks((ts) =>
        ts.map((t) => (t.id === sub.id ? { ...t, status: sub.status } : t)),
      )
    }
  }

  const handleDeleteSub = async (sub) => {
    try {
      await api.delete(`/tasks/${sub.id}`)
      setTasks((ts) => ts.filter((t) => t.id !== sub.id))
    } catch {
      /* 忽略 */
    }
  }

  const doExport = async (fmt) => {
    try {
      const res = await fetch(`/api/export?fmt=${fmt}`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) throw new Error('export failed')
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = fmt === 'json' ? 'reach-backup.json' : 'reach-tasks.csv'
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
    } catch {
      alert('导出失败，请重试')
    }
  }

  const visibleTasks = tasks.filter(
    (t) =>
      !t.parent_id &&
      t.title.toLowerCase().includes(query.trim().toLowerCase()),
  )

  // 子任务按父任务分组（用于卡片内渲染 checklist）
  const subtasksByParent = useMemo(() => {
    const m = {}
    for (const t of tasks) {
      if (t.parent_id != null) {
        ;(m[t.parent_id] ||= []).push(t)
      }
    }
    return m
  }, [tasks])

  // 到期提醒：浏览器通知。latest tasks 存入 ref 供定时器读取，避免闭包陈旧。
  const tasksRef = useRef(tasks)
  useEffect(() => {
    tasksRef.current = tasks
  }, [tasks])

  const [notifPerm, setNotifPerm] = useState(
    typeof Notification !== 'undefined' ? Notification.permission : 'denied',
  )
  const notifiedRef = useRef(new Set())
  const enableReminders = async () => {
    if (typeof Notification === 'undefined') return
    const p = await Notification.requestPermission()
    setNotifPerm(p)
  }

  useEffect(() => {
    if (notifPerm !== 'granted') return
    const tick = () => {
      const due = getDueSoonTasks(tasksRef.current)
      for (const { task, kind } of due) {
        const key = `${task.id}:${kind}`
        if (notifiedRef.current.has(key)) continue
        notifiedRef.current.add(key)
        try {
          new Notification('抵达 Reach · 提醒', {
            body: `「${task.title}」${kindLabel(kind)}`,
          })
        } catch {
          /* 部分浏览器需依赖 ServiceWorker 才能弹通知，忽略即可 */
        }
      }
    }
    tick()
    const id = setInterval(tick, 60000)
    return () => clearInterval(id)
  }, [notifPerm])

  const today = todayStr(timezone)

  // 「今日待办」：未完成，且属于 今天 / 未来 / 未排期 的任务。
  // 已完成任务不显示；逾期的任务统一收进「逾期任务」折叠区。
  const isForToday = (t) => {
    if (t.status === 'done') return false
    if (!t.due_date) return true
    return t.due_date >= today
  }

  // 逾期任务：未完成且到期日早于今天的任务，默认折叠。
  const isOverdue = (t) => {
    if (t.status === 'done') return false
    if (!t.due_date) return false
    return t.due_date < today
  }

  const groups = categories.map((c) => ({
    ...c,
    items: visibleTasks.filter(
      (t) => t.category_id === c.id && (selected === 'all' ? isForToday(t) : true),
    ),
  }))

  const overdueGroups = categories.map((c) => ({
    ...c,
    items: visibleTasks.filter((t) => t.category_id === c.id && isOverdue(t)),
  }))
  const overdueTotal = overdueGroups.reduce((sum, g) => sum + g.items.length, 0)

  const currentName =
    selected === 'all'
      ? '今日待办'
      : categories.find((c) => c.id === selected)?.name || '待办'
  const currentCat =
    selected === 'all' ? null : categories.find((c) => c.id === selected)

  // 分组内可拖拽的任务列表：本地顺序由 state 维护，拖拽后写回
  const [groupOrder, setGroupOrder] = useState({})
  const [overdueOrder, setOverdueOrder] = useState({})

  const renderSortableGroup = (g, orderState, setOrderState) => {
    const items = orderState[g.id] ?? g.items
    return (
      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragEnd={(e) => handleDragEnd(items, (next) => setOrderState((s) => ({ ...s, [g.id]: next })), e)}
      >
        <SortableContext
          items={items.map((t) => t.id)}
          strategy={verticalListSortingStrategy}
        >
          <div className="space-y-2.5 pl-1">
            {items.map((t) => (
              <SortableTaskCard
                key={t.id}
                task={t}
                category={g}
                onToggle={handleToggle}
                onDelete={handleDelete}
                subtasks={subtasksByParent[t.id] || []}
                onAddSubtask={handleAddSub}
                onToggleSub={handleToggleSub}
                onDeleteSub={handleDeleteSub}
              />
            ))}
          </div>
        </SortableContext>
      </DndContext>
    )
  }

  return (
    <Layout summary={summary} selected={selected} onSelect={setSelected}>
      <main className="flex-1 overflow-y-auto md:pb-0 pb-20">
        <header className={`${header} flex items-center justify-between gap-3`}>
          <div className="min-w-0">
            <h1 className="text-lg font-bold text-[#0f172a] truncate font-display">
              {currentName}
            </h1>
            <p className="text-xs text-[#475569]">
              下午好，{user?.username} · 一切都是为了抵达
            </p>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <div className="relative hidden sm:block">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-[#94a3b8]">
                <Icon.search />
              </span>
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="搜索任务…"
                className={`${field} w-44 pl-9`}
              />
            </div>
            <button
              onClick={() => doExport('json')}
              className="px-3 h-9 rounded-xl border border-white/70 text-sm text-[#475569] hover:bg-white/60 transition shrink-0"
              title="导出全部数据为 JSON 备份"
            >
              备份
            </button>
            {typeof Notification !== 'undefined' && notifPerm !== 'denied' && (
              <button
                onClick={enableReminders}
                className={`px-3 h-9 rounded-xl border text-sm transition shrink-0 ${
                  notifPerm === 'granted'
                    ? 'border-emerald-300 text-emerald-600 bg-emerald-50/60'
                    : 'border-white/70 text-[#475569] hover:bg-white/60'
                }`}
                title={notifPerm === 'granted' ? '已开启到期提醒' : '开启到期提醒'}
              >
                {notifPerm === 'granted' ? '🔔 提醒已开' : '🔔 开启提醒'}
              </button>
            )}
            <button onClick={() => setShowForm(true)} className={btnPrim}>
              + 新建
            </button>
          </div>
        </header>

        <div className="p-5 md:p-7 space-y-7">
          {loading ? (
            <p className="text-sm text-[#94a3b8]">加载中…</p>
          ) : selected === 'all' ? (
            <>
              {groups.map((g) => (
                <section key={g.id}>
                  <div className="flex items-center gap-2 mb-3">
                    <span
                      className="w-3 h-3 rounded-full"
                      style={{ backgroundColor: g.color }}
                    ></span>
                    <h2 className="font-bold text-[#475569]">{g.name}</h2>
                    <span className="text-xs text-[#94a3b8]">
                      待办 {g.items.filter((t) => t.status === 'todo').length}
                    </span>
                  </div>
                  {g.items.length === 0 ? (
                    <p className="text-sm text-[#cbd5e1] pl-5">
                      今天这个维度还没有任务
                    </p>
                  ) : (
                    renderSortableGroup(g, groupOrder, setGroupOrder)
                  )}
                </section>
              ))}
              {overdueTotal > 0 && (
                <section className="pt-2">
                  <button
                    onClick={() => setShowOverdue((s) => !s)}
                    className="flex items-center gap-2 text-sm text-[#64748b] hover:text-[#0f172a] transition"
                  >
                    <span className="text-xs">{showOverdue ? '▾' : '▸'}</span>
                    <span>逾期任务</span>
                    <span className="text-xs text-[#94a3b8]">({overdueTotal})</span>
                  </button>
                  {showOverdue && (
                    <div className="mt-4 space-y-6">
                      {overdueGroups
                        .filter((g) => g.items.length > 0)
                        .map((g) => (
                          <section key={g.id}>
                            <div className="flex items-center gap-2 mb-3">
                              <span
                                className="w-3 h-3 rounded-full"
                                style={{ backgroundColor: g.color }}
                              ></span>
                              <h2 className="font-bold text-[#475569]">{g.name}</h2>
                              <span className="text-xs text-[#94a3b8]">
                                待办 {g.items.length}
                              </span>
                            </div>
                            {renderSortableGroup(g, overdueOrder, setOverdueOrder)}
                          </section>
                        ))}
                    </div>
                  )}
                </section>
              )}
            </>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {visibleTasks.length === 0 ? (
                <p className="text-sm text-[#cbd5e1] md:col-span-2">这个维度还没有任务</p>
              ) : (
                visibleTasks.map((t) => (
                  <TaskCard
                    key={t.id}
                    task={t}
                    category={currentCat}
                    onToggle={handleToggle}
                    onDelete={handleDelete}
                    subtasks={subtasksByParent[t.id] || []}
                    onAddSubtask={handleAddSub}
                    onToggleSub={handleToggleSub}
                    onDeleteSub={handleDeleteSub}
                  />
                ))
              )}
            </div>
          )}
        </div>
      </main>

      <TaskForm
        open={showForm}
        onClose={() => setShowForm(false)}
        onSubmit={handleSubmit}
        categories={categories}
        goals={goals}
      />
    </Layout>
  )
}
