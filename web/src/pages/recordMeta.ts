// 记录类型元信息（颜色 / 标签），记录页与日历页共用
// 注：图标不再使用 emoji，统一以「彩色标签 + 文字」呈现，契合液态玻璃设计系统

export interface RecordMeta {
  key: string
  label: string
  color: string
}

export const RECORD_TYPES: Record<string, RecordMeta> = {
  diary: { key: 'diary', label: '个人日记', color: '#14b8a6' },
  worklog: { key: 'worklog', label: '工作日志', color: '#2563eb' },
  note: { key: 'note', label: '读书笔记', color: '#f59e0b' },
}

export const RECORD_TYPE_LIST: RecordMeta[] = [
  RECORD_TYPES.diary,
  RECORD_TYPES.worklog,
  RECORD_TYPES.note,
]

export function typeMeta(type: string): RecordMeta {
  return RECORD_TYPES[type] || RECORD_TYPES.diary
}

// 日记心情选项（表情 + 含义，与习惯站心情风格统一）
export const MOODS: { emoji: string; label: string }[] = [
  { emoji: '😊', label: '开心' },
  { emoji: '😌', label: '平静' },
  { emoji: '😢', label: '低落' },
  { emoji: '💪', label: '加油' },
  { emoji: '✨', label: '闪亮' },
  { emoji: '😴', label: '疲惫' },
  { emoji: '🤔', label: '思考' },
  { emoji: '❤️', label: '喜爱' },
]

// 内置模板描述：给模板选择卡片用
export const TEMPLATE_DESCRIPTIONS: Record<string, string> = {
  '每日心情日记': '记录今天的心情与故事',
  '感恩日记': '发现生活中的小确幸',
  '自由书写': '不加评判地自由表达',
  '工作日报': '今日进展与明日计划',
  '周报': '本周最重要的进展',
  '会议记录': '关键结论与行动项',
  '读书卡片': '摘录、想法与关联',
  '金句摘抄': '一句话与一点思考',
  '读后感': '一本书带来的启发',
}

// 根据模板名称给编辑器不同的 placeholder，避免「答题卡」感
export const TEMPLATE_PLACEHOLDERS: Record<string, string> = {
  '每日心情日记': '今天发生了什么？',
  '感恩日记': '今天让我感激的是…',
  '自由书写': '想到什么写什么，不用完美…',
  '工作日报': '今天完成了什么？明天重点推进什么？',
  '周报': '本周最重要的进展与下周打算：',
  '会议记录': '本次会议的关键结论与待办：',
  '读书卡片': '摘录一段打动你的文字，并写下你的想法：',
  '金句摘抄': '记录一句话与你的思考：',
  '读后感': '这本书带给你最重要的启发是什么？',
}

export function excerpt(text: string, n = 90): string {
  if (!text) return ''
  const flat = text.replace(/\n+/g, ' ').trim()
  return flat.length > n ? flat.slice(0, n) + '…' : flat
}

// 富文本存储为 HTML，展示前做轻量清洗，仅保留安全标签、移除事件属性/危险协议
export function sanitizeHtml(html: string): string {
  if (!html) return ''
  const allowed = new Set([
    'B', 'STRONG', 'I', 'EM', 'U', 'S', 'SPAN', 'DIV', 'BR', 'P',
    'FONT', 'A', 'IMG', 'UL', 'OL', 'LI', 'H3', 'H4',
  ])
  const tpl = document.createElement('div')
  tpl.innerHTML = html
  const walk = (node: HTMLElement): void => {
    Array.from(node.childNodes).forEach((child) => {
      if (child.nodeType !== 1) return
      const el = child as HTMLElement
      Array.from(el.attributes).forEach((a) => {
        const name = a.name.toLowerCase()
        if (name.startsWith('on')) el.removeAttribute(a.name)
        else if (/javascript:|script:|data:/i.test(a.value)) el.removeAttribute(a.name)
      })
      if (!allowed.has(el.tagName)) {
        const parent = el.parentNode
        if (parent) {
          while (el.firstChild) parent.insertBefore(el.firstChild, el)
          parent.removeChild(el)
        }
        return
      }
      walk(el)
    })
  }
  walk(tpl)
  return tpl.innerHTML
}
