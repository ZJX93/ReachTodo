import { useState, useEffect, useMemo } from 'react'
import { createPortal } from 'react-dom'
import { useNavigate, useSearchParams } from 'react-router-dom'
import api from '../api'
import Layout from './Layout'
import { RECORD_TYPE_LIST } from './recordMeta'
import { header, field, btnPrim, btnGhost, Icon } from './ui'
import RecordCard from './records/RecordCard'
import RecordEditor from './records/RecordEditor'
import TemplateManager from './records/TemplateManager'
import NewTypePicker from './records/NewTypePicker'

export default function Records() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [records, setRecords] = useState([])
  const [templates, setTemplates] = useState([])
  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(true)
  const [typeFilter, setTypeFilter] = useState('all')
  const [query, setQuery] = useState('')
  const [editor, setEditor] = useState(null) // null=closed, {} = new, {id...} = edit
  const [tmplOpen, setTmplOpen] = useState(false)
  const [newPicker, setNewPicker] = useState(false)
  const [initialDate, setInitialDate] = useState(null)

  const load = async () => {
    const params = new URLSearchParams()
    if (typeFilter !== 'all') params.set('type', typeFilter)
    if (query.trim()) params.set('q', query.trim())
    const [r, t, s] = await Promise.all([
      api.get(`/records?${params.toString()}`),
      api.get('/templates'),
      api.get('/tasks/summary'),
    ])
    setRecords(r.data)
    setTemplates(t.data)
    setSummary(s.data)
    setLoading(false)
  }
  useEffect(() => {
    load()
  }, [typeFilter, query])

  // 从日历页跳转过来：定位到指定记录 / 预填日期
  useEffect(() => {
    const editId = searchParams.get('edit')
    if (editId) {
      ;(async () => {
        try {
          const r = await api.get(`/records/${editId}`)
          setEditor(r.data)
        } catch {
          /* 忽略：权限或不存在 */
        }
      })()
    }
    const d = searchParams.get('date')
    if (d && /^\d{4}-\d{2}-\d{2}$/.test(d)) setInitialDate(d)
  }, [])

  const groups = useMemo(() => {
    const m = {}
    for (const rec of records) {
      ;(m[rec.record_date] = m[rec.record_date] || []).push(rec)
    }
    return Object.keys(m)
      .sort()
      .reverse()
      .map((d) => ({ date: d, items: m[d] }))
  }, [records])

  const remove = async (rec) => {
    if (!confirm('删除这条记录？')) return
    await api.delete(`/records/${rec.id}`)
    await load()
  }

  const counts = useMemo(() => {
    const c = { all: records.length, diary: 0, worklog: 0, note: 0 }
    records.forEach((r) => (c[r.type] = (c[r.type] || 0) + 1))
    return c
  }, [records])

  return (
    <Layout summary={summary} selected="records" onSelect={() => {}}>
      <main className="flex-1 overflow-y-auto pb-20 md:pb-0">
        <header className={`${header} flex items-center justify-between gap-3 flex-wrap`}>
          <div className="mx-auto w-full max-w-6xl flex items-center justify-between gap-3 flex-wrap">
          <div>
            <h1 className="text-lg font-bold text-[#0f172a] font-display">记录</h1>
            <p className="text-xs text-[#475569]">个人日记 · 工作日志 · 读书笔记</p>
          </div>
          <div className="flex items-center gap-2">
            <div className="relative hidden sm:block">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-[#94a3b8]">
                <Icon.search />
              </span>
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="搜索标题 / 内容"
                className={`${field} w-44 pl-9`}
              />
            </div>
            <button
              onClick={() => setTmplOpen(true)}
              className={btnGhost}
            >
              模板
            </button>
            <button onClick={() => setNewPicker(true)} className={btnPrim}>
              + 新建
            </button>
          </div>
          </div>
        </header>

        {/* 类型筛选 */}
        <div className="max-w-6xl mx-auto px-5 md:px-7 pt-4">
          <div className="flex gap-2 flex-wrap">
            {[{ key: 'all', label: '全部', color: '#2563eb' }, ...RECORD_TYPE_LIST].map((t) => {
              const active = typeFilter === t.key
              return (
                <button
                  key={t.key}
                  onClick={() => setTypeFilter(t.key)}
                  className={`px-3 py-1.5 rounded-full text-sm font-semibold transition border ${
                    active
                      ? 'text-white border-transparent brand-gradient'
                      : 'text-[#475569] border-white/75 bg-white/40 hover:bg-white/60'
                  }`}
                >
                  {t.label}
                  <span className="ml-1 opacity-70">{counts[t.key] || 0}</span>
                </button>
              )
            })}
          </div>
        </div>

        <div className="max-w-6xl mx-auto p-5 md:p-7 space-y-6">
          {loading ? (
            <p className="text-[#94a3b8] text-sm">加载中…</p>
          ) : records.length === 0 ? (
            <div className="text-center py-16 text-[#94a3b8]">
              <p className="text-sm">还没有记录，点「+ 新建」开始第一篇吧</p>
            </div>
          ) : (
            groups.map((g) => (
              <div key={g.date}>
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-xs font-semibold text-[#94a3b8]">{g.date}</span>
                  <button
                    onClick={() => navigate(`/calendar?date=${g.date}`)}
                    className="text-[11px] text-[#2563eb] hover:underline inline-flex items-center gap-1"
                    title="在日历中查看"
                  >
                    <Icon.cal className="w-3.5 h-3.5" />
                    日历
                  </button>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {g.items.map((rec) => (
                    <RecordCard
                      key={rec.id}
                      rec={rec}
                      onOpen={() => setEditor(rec)}
                      onDelete={() => remove(rec)}
                      onCalendar={() => navigate(`/calendar?date=${rec.record_date}`)}
                    />
                  ))}
                </div>
              </div>
            ))
          )}
        </div>
      </main>

      {newPicker &&
        createPortal(
          <NewTypePicker
            onPick={(type) => {
              setNewPicker(false)
              setEditor(initialDate ? { type, record_date: initialDate } : { type })
            }}
            onClose={() => setNewPicker(false)}
          />,
          document.body,
        )}
      {editor !== null &&
        createPortal(
          <RecordEditor
            initial={editor}
            templates={templates}
            onClose={() => setEditor(null)}
            onSaved={async () => {
              setEditor(null)
              await load()
            }}
          />,
          document.body,
        )}
      {tmplOpen &&
        createPortal(
          <TemplateManager
            templates={templates}
            onClose={() => setTmplOpen(false)}
            onChange={async () => {
              const t = await api.get('/templates')
              setTemplates(t.data)
            }}
          />,
          document.body,
        )}
    </Layout>
  )
}
