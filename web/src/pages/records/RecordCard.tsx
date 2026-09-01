import { typeMeta, sanitizeHtml } from '../recordMeta'
import { Icon } from '../ui'
import type { RecordItem } from '../../types'

interface RecordCardProps {
  rec: RecordItem
  onOpen: () => void
  onDelete: () => void
  onCalendar: () => void
}

export default function RecordCard({ rec, onOpen, onDelete, onCalendar }: RecordCardProps) {
  const meta = typeMeta(rec.type)
  return (
    <div
      onClick={onOpen}
      className="cursor-pointer bg-white/55 backdrop-blur-[18px] border border-white/75 rounded-2xl p-4 shadow-[0_8px_24px_-12px_rgba(8,145,178,0.30)] hover:shadow-[0_12px_30px_-12px_rgba(8,145,178,0.40)] transition"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2 min-w-0">
          <span
            className="text-[11px] font-semibold px-2 py-0.5 rounded-full text-white shrink-0"
            style={{ backgroundColor: meta.color }}
          >
            {meta.label}
          </span>
          <span className="text-sm font-semibold text-[#0f172a] truncate">{rec.title}</span>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <span
            className="cursor-pointer text-[#94a3b8] hover:text-[#2563eb] transition"
            onClick={(e) => {
              e.stopPropagation()
              onCalendar()
            }}
            title="在日历中查看"
          >
            <Icon.cal className="w-4 h-4" />
          </span>
          <button
            onClick={(e) => {
              e.stopPropagation()
              onDelete()
            }}
            className="text-[#cbd5e1] hover:text-[#ef4444] transition"
            title="删除"
            aria-label="删除"
          >
            <Icon.close />
          </button>
        </div>
      </div>

      {rec.content && (
        <div
          className="rich-preview text-xs text-[#475569] mt-2 whitespace-pre-wrap line-clamp-3"
          dangerouslySetInnerHTML={{ __html: sanitizeHtml(rec.content) }}
        />
      )}

      <div className="flex items-center gap-2 flex-wrap mt-2 text-[11px] text-[#475569]">
        {rec.record_time && (
          <span className="inline-flex items-center gap-1">
            <Icon.clock className="w-3.5 h-3.5 text-[#94a3b8]" />
            {rec.record_time}
          </span>
        )}
        {rec.type === 'diary' && rec.mood && (
          <span className="inline-flex items-center gap-0.5">{rec.mood}</span>
        )}
        {rec.type === 'diary' && rec.weather && <span>{rec.weather}</span>}
        {rec.location && (
          <span className="inline-flex items-center gap-0.5">📍 {rec.location}</span>
        )}
        {rec.type === 'worklog' && rec.project && <span>项目 · {rec.project}</span>}
        {rec.type === 'note' && (rec.book_title || rec.book_author) && (
          <span>
            《{rec.book_title}
            {rec.book_author ? ` · ${rec.book_author}` : ''}》
          </span>
        )}
        {rec.tags &&
          rec.tags
            .split(',')
            .filter(Boolean)
            .map((t) => (
              <span key={t} className="px-1.5 py-0.5 rounded bg-white/60 text-[#475569]">
                #{t.trim()}
              </span>
            ))}
      </div>
    </div>
  )
}
