import { useState } from 'react'
import api from '../../api'
import { typeMeta, MOODS, TEMPLATE_DESCRIPTIONS, TEMPLATE_PLACEHOLDERS } from '../recordMeta'
import RichTextEditor from '../components/RichTextEditor'
import { field, btnPrim } from '../ui'
import { todayStr, nowHM } from '../../utils/date'
import useSettingsStore from '../../store/settingsStore'

// 纯文本 → HTML（保留换行）；已含标签则原样保留
function toHtml(s) {
  if (!s) return ''
  return s.includes('<') ? s : s.replace(/\n/g, '<br>')
}

// 日期 + 星期（按用户时区）
function formatDateWeek(dateStr: string, timezone: string): string {
  const d = new Date(`${dateStr}T00:00:00`)
  return new Intl.DateTimeFormat('zh-CN', {
    timeZone: timezone,
    month: 'long',
    day: 'numeric',
    weekday: 'long',
  }).format(d)
}

// WMO 天气代码 → 项目内天气 emoji（用于根据定位自动设置天气）
function wmoToWeather(code: number): string {
  if (code === 0) return '☀️'
  if (code <= 2) return '🌤️'
  if (code === 3) return '☁️'
  if (code === 45 || code === 48) return '🌫️'
  if (code >= 51 && code <= 67) return '🌧️'
  if (code >= 71 && code <= 77) return '❄️'
  if (code >= 80 && code <= 82) return '🌧️'
  if (code >= 85 && code <= 86) return '❄️'
  if (code >= 95) return '⛈️'
  return '🌬️'
}

// 天气 emoji → 中文提示（hover 用）
const WEATHER_LABELS: Record<string, string> = {
  '☀️': '晴',
  '🌤️': '多云',
  '☁️': '阴',
  '🌧️': '雨',
  '⛈️': '雷雨',
  '🌨️': '雪',
  '❄️': '雪',
  '🌫️': '雾',
  '🌬️': '风',
}

export default function RecordEditor({ initial, templates, onClose, onSaved }) {
  const timezone = useSettingsStore((s) => s.timezone)
  const isEdit = !!initial.id
  const [type] = useState(initial.type || 'diary')
  const [title, setTitle] = useState(initial.title || '')
  const [content, setContent] = useState(initial.content ? toHtml(initial.content) : '')
  const [mood, setMood] = useState(initial.mood || '')
  const [weather, setWeather] = useState(initial.weather || '')
  const [location, setLocation] = useState(initial.location || '')
  const [project, setProject] = useState(initial.project || '')
  const WEATHERS = ['☀️', '🌤️', '☁️', '🌧️', '⛈️', '🌨️', '❄️', '🌫️', '🌬️']
  const [locating, setLocating] = useState(false)
  const onLocate = async () => {
    if (!navigator.geolocation) {
      alert('当前浏览器不支持定位')
      return
    }
    setLocating(true)
    try {
      const pos = await new Promise<GeolocationPosition>((resolve, reject) =>
        navigator.geolocation.getCurrentPosition(resolve, reject, { timeout: 10000 }),
      )
      const { latitude, longitude } = pos.coords
      // 天气：Open-Meteo 免 key，按经纬度取当前天气代码
      try {
        const wres = await fetch(
          `https://api.open-meteo.com/v1/forecast?latitude=${latitude}&longitude=${longitude}&current=weather_code`,
        )
        const wj = await wres.json()
        const code = wj?.current?.weather_code
        if (code != null) setWeather(wmoToWeather(code))
      } catch {
        // 天气获取失败不影响定位
      }
      // 逆地理编码：Nominatim（OpenStreetMap），失败降级为经纬度
      try {
        const gres = await fetch(
          `https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${latitude}&lon=${longitude}&zoom=10&accept-language=zh-CN`,
          { headers: { Accept: 'application/json' } },
        )
        const gj = await gres.json()
        const name =
          gj?.address?.city || gj?.address?.town || gj?.address?.county || gj?.name
        setLocation(name || `${latitude.toFixed(3)}, ${longitude.toFixed(3)}`)
      } catch {
        setLocation(`${latitude.toFixed(3)}, ${longitude.toFixed(3)}`)
      }
    } catch {
      alert('定位失败或被拒绝')
    } finally {
      setLocating(false)
    }
  }
  const [bookTitle, setBookTitle] = useState(initial.book_title || '')
  const [bookAuthor, setBookAuthor] = useState(initial.book_author || '')
  const [tags, setTags] = useState(initial.tags || '')
  const [date, setDate] = useState(initial.record_date || todayStr(timezone))
  const [time, setTime] = useState(initial.record_time || nowHM(timezone))
  const [templateId, setTemplateId] = useState(null)
  const [saving, setSaving] = useState(false)
  const [showProps, setShowProps] = useState(false)

  const meta = typeMeta(type)
  const tmpls = templates.filter((t) => t.type === type || t.type === 'all')

  const pickTemplate = (t) => {
    if (t.id === templateId) return // 再次点击同一模板不重复动作
    const prevName = templateId ? templates.find((x) => x.id === templateId)?.name : null
    setTemplateId(t.id)
    // 标题：仅当用户还没手动改过（当前标题等于上一模板默认名或为空）才跟随切换
    if (!title || title === prevName) setTitle(t.name)
    // 正文：仅当正文仍为空时，才跟随模板的预填内容
    const text = content.replace(/<[^>]*>/g, '').replace(/&nbsp;/g, '').trim()
    if (t.content && !text) setContent(toHtml(t.content))
  }

  const selectedTemplate = templates.find((t) => t.id === templateId)
  const placeholder = selectedTemplate
    ? TEMPLATE_PLACEHOLDERS[selectedTemplate.name] || '开始写作…'
    : '开始写作…'

  const save = async () => {
    if (!title.trim()) {
      alert('请填写标题')
      return
    }
    setSaving(true)
    const payload = {
      type,
      title: title.trim(),
      content: content || null,
      mood: type === 'diary' ? mood || null : null,
      weather: type === 'diary' ? weather || null : null,
      location: location || null,
      project: type === 'worklog' ? project || null : null,
      book_title: type === 'note' ? bookTitle || null : null,
      book_author: type === 'note' ? bookAuthor || null : null,
      tags: tags || null,
      record_date: date,
      record_time: time || null,
      template_id: templateId,
    }
    try {
      if (isEdit) await api.put(`/records/${initial.id}`, payload)
      else await api.post('/records', payload)
      onSaved()
    } finally {
      setSaving(false)
    }
  }

  const del = async () => {
    if (!confirm('删除这条记录？')) return
    await api.delete(`/records/${initial.id}`)
    onSaved()
  }

  return (
    <div className="fixed inset-0 z-50 bg-white flex flex-col">
      {/* 顶部操作栏 */}
      <header className="sticky top-0 z-10 bg-white/70 backdrop-blur border-b border-white/75 px-4 md:px-6 h-14 flex items-center justify-between gap-3">
        <button
          onClick={onClose}
          className="h-9 px-3 flex items-center gap-1 rounded-xl text-sm font-medium text-[#475569] hover:bg-[#f1f5f9] transition shrink-0"
        >
          ‹ 返回
        </button>

        <span
          className="h-9 px-4 flex items-center rounded-full text-sm font-semibold text-white shrink-0"
          style={{ backgroundColor: meta.color }}
        >
          {meta.label}
        </span>

        <div className="flex items-center gap-2 shrink-0">
          {isEdit && (
            <button
              onClick={del}
              className="h-9 px-3 flex items-center rounded-xl text-sm font-medium text-[#ef4444] hover:bg-[#ef4444]/10 transition"
            >
              删除
            </button>
          )}
          <button
            onClick={save}
            disabled={saving}
            className="h-9 px-4 flex items-center rounded-xl bg-[#06b6d4] text-white text-sm font-medium hover:bg-[#0891b2] transition shadow-[0_2px_8px_-2px_rgba(8,145,178,0.25)] disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {saving ? '保存中…' : '保存'}
          </button>
        </div>
      </header>

      {/* 编辑区：文档式写作页面（类型已在主页选定） */}
      <div className="flex-1 overflow-y-auto">
        <div className="w-full px-4 md:px-10 lg:px-16 py-6 space-y-4">
          {/* 模板选择：紧凑卡片式 */}
          {tmpls.length > 0 && (
            <div>
              <div className="text-sm font-semibold text-[#475569] mb-3">选择一种写作方式</div>
              <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-6 gap-2">
                {tmpls.map((t) => {
                  const active = templateId === t.id
                  return (
                    <button
                      key={t.id}
                      onClick={() => pickTemplate(t)}
                      className={`text-left p-2 rounded-lg border transition ${
                        active
                          ? 'border-[#06b6d4] bg-[#06b6d4]/10 shadow-[0_8px_24px_-12px_rgba(8,145,178,0.30)]'
                          : 'border-white/75 bg-white/40 hover:bg-white/60'
                      }`}
                    >
                      <div className="text-base leading-none mb-1">{t.icon}</div>
                      <div className={`text-xs font-semibold ${active ? 'text-[#0f172a]' : 'text-[#475569]'}`}>
                        {t.name}
                      </div>
                      <div className="text-[10px] text-[#94a3b8] mt-0.5 leading-tight">
                        {TEMPLATE_DESCRIPTIONS[t.name] || ''}
                      </div>
                    </button>
                  )
                })}
              </div>
            </div>
          )}

          {/* 文档卡片：标题 + 日记头部 + 正文 */}
          <div className="bg-white/70 backdrop-blur-[18px] border border-white/75 shadow-[0_8px_24px_-12px_rgba(8,145,178,0.30)] rounded-2xl px-5 md:px-8 py-6 space-y-4">
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="无标题文档"
              className="w-full bg-transparent text-2xl md:text-3xl font-bold text-[#0f172a] placeholder-[#cbd5e1] outline-none border-none px-0"
            />

            {/* 日记类型：专业日记氛围头部 —— 日期 + 心情 + 天气 + 位置 同一行 */}
            {type === 'diary' && (
              <div className="flex flex-wrap items-center gap-x-5 gap-y-3">
                {/* 日期 */}
                <div className="text-2xl md:text-3xl font-bold text-[#0f172a] leading-tight">
                  {formatDateWeek(date, timezone)}
                </div>

                {/* 心情 */}
                <div className="flex gap-1">
                  {MOODS.map((m) => (
                    <button
                      key={m.emoji}
                      title={m.label}
                      onClick={() => setMood(m.emoji)}
                      className={`w-9 h-9 flex items-center justify-center rounded-xl text-lg transition ${
                        mood === m.emoji
                          ? 'bg-[#06b6d4]/15 ring-2 ring-[#06b6d4]'
                          : 'bg-white/60 hover:bg-white/80'
                      }`}
                    >
                      {m.emoji}
                    </button>
                  ))}
                </div>

                {/* 天气 */}
                <div className="flex gap-1">
                  {WEATHERS.map((w) => (
                    <button
                      key={w}
                      title={WEATHER_LABELS[w]}
                      onClick={() => setWeather(w)}
                      className={`w-9 h-9 flex items-center justify-center rounded-xl text-lg transition ${
                        weather === w
                          ? 'bg-[#06b6d4]/15 ring-2 ring-[#06b6d4]'
                          : 'bg-white/60 hover:bg-white/80'
                      }`}
                    >
                      {w}
                    </button>
                  ))}
                </div>

                {/* 位置 */}
                <div className="w-52 flex gap-2">
                  <input
                    value={location}
                    onChange={(e) => setLocation(e.target.value)}
                    placeholder="位置"
                    className="flex-1 min-w-0 h-9 px-3 border border-white/75 rounded-xl text-sm bg-white/70 text-[#0f172a] placeholder:text-[#94a3b8] focus:border-[#06b6d4] focus:ring-2 focus:ring-[#06b6d4]/20 transition"
                  />
                  <button
                    type="button"
                    onClick={onLocate}
                    disabled={locating}
                    title="自动定位并获取天气"
                    className="shrink-0 w-9 h-9 flex items-center justify-center rounded-xl border border-white/75 bg-white/60 hover:bg-white/80 text-lg transition disabled:opacity-50"
                  >
                    {locating ? '…' : '📍'}
                  </button>
                </div>
              </div>
            )}

            <div className="text-[11px] text-[#94a3b8]">正文（支持加粗 / 斜体 / 字体 / 字号 / 颜色）</div>
            <RichTextEditor value={content} onChange={setContent} placeholder={placeholder} />
          </div>

          {/* 日期 / 时间：始终可见，精确到分 */}
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs text-[#94a3b8]">日期 / 时间</span>
            <input
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              className={`${field} w-auto`}
            />
            <input
              type="time"
              value={time}
              onChange={(e) => setTime(e.target.value)}
              className={`${field} w-auto`}
            />
          </div>

          {/* 属性（可折叠，默认收起，不干扰写作） */}
          <div className="border border-white/75 rounded-2xl bg-white/55 overflow-hidden">
            <button
              onClick={() => setShowProps((v) => !v)}
              className="w-full flex items-center justify-between px-4 py-3 text-sm font-semibold text-[#475569] hover:bg-white/60 transition"
            >
              <span>属性</span>
              <span className="text-[#94a3b8]">{showProps ? '▴' : '▾'}</span>
            </button>
            {showProps && (
              <div className="px-4 pb-4 pt-1 space-y-3 border-t border-white/75">
                {type === 'worklog' && (
                  <input
                    value={project}
                    onChange={(e) => setProject(e.target.value)}
                    placeholder="关联项目（可选）"
                    className={field}
                  />
                )}
                {type === 'note' && (
                  <div className="flex gap-2">
                    <input
                      value={bookTitle}
                      onChange={(e) => setBookTitle(e.target.value)}
                      placeholder="书名"
                      className={`${field} flex-1`}
                    />
                    <input
                      value={bookAuthor}
                      onChange={(e) => setBookAuthor(e.target.value)}
                      placeholder="作者"
                      className={`${field} flex-1`}
                    />
                  </div>
                )}
                <input
                  value={tags}
                  onChange={(e) => setTags(e.target.value)}
                  placeholder="标签，逗号分隔，如：coding,生活"
                  className={field}
                />
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
