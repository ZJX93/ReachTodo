import { useEffect, useState } from 'react'
import { btnGhost, btnPrim, cardLg, field, Icon } from '../ui'
import {
  FREQ_LABEL,
  HABIT_COLORS,
  HABIT_ICONS,
  TYPE_LABEL,
  WEEKDAY_LABEL,
  toISODate,
  type Habit,
  type HabitDraft,
  type HabitFrequency,
  type HabitType,
} from '../../services/habits'

interface Props {
  open: boolean
  /** 传入即编辑，否则为新建 */
  habit?: Habit | null
  onClose: () => void
  onSubmit: (draft: HabitDraft) => Promise<void> | void
}

const TYPES: HabitType[] = ['check', 'count', 'duration', 'timerange']
const FREQS: HabitFrequency[] = ['daily', 'weekday', 'weekend', 'custom']

function blank(): HabitDraft {
  return {
    name: '',
    icon: 'smile',
    color: '#7C9A92',
    type: 'check',
    target: 1,
    unit: '次',
    frequency: 'daily',
    weekdays: [],
    size: 'md',
    category_id: null,
    start_date: toISODate(new Date()),
  }
}

function fromHabit(h: Habit): HabitDraft {
  return {
    name: h.name,
    icon: h.icon,
    color: h.color,
    type: h.type,
    target: h.target,
    unit: h.unit,
    frequency: h.frequency,
    weekdays: h.weekdays ?? [],
    size: h.size,
    category_id: h.category_id,
    start_date: h.start_date,
    sort_order: h.sort_order,
  }
}

function Seg({
  active,
  onClick,
  children,
}: {
  active: boolean
  onClick: () => void
  children: React.ReactNode
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`py-2 rounded-xl text-xs font-semibold border transition ${
        active
          ? 'bg-[rgba(37,99,235,0.08)] border-[#06b6d4] text-[#2563eb]'
          : 'border-white/75 bg-white/40 text-[#475569] hover:bg-white/70'
      }`}
    >
      {children}
    </button>
  )
}

export default function HabitEditor({ open, habit, onClose, onSubmit }: Props) {
  const [draft, setDraft] = useState<HabitDraft>(blank)
  const [saving, setSaving] = useState(false)

  // 每次打开重置草稿，避免上次编辑的残留
  useEffect(() => {
    if (!open) return
    setDraft(habit ? fromHabit(habit) : blank())
    setSaving(false)
  }, [open, habit])

  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose?.()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!open) return null

  const patch = (p: Partial<HabitDraft>) => setDraft((d) => ({ ...d, ...p }))
  const needTarget = draft.type === 'count' || draft.type === 'duration'

  const submit = async () => {
    if (!draft.name.trim()) return
    setSaving(true)
    try {
      await onSubmit({ ...draft, name: draft.name.trim() })
    } finally {
      setSaving(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 grid place-items-center bg-[#0f172a]/30 backdrop-blur-sm p-4"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose?.()
      }}
    >
      <div
        className={`${cardLg} w-full max-w-lg p-6 md:p-7 relative max-h-[90vh] overflow-y-auto`}
      >
        <button
          onClick={onClose}
          aria-label="关闭"
          className="absolute top-3 right-3 p-1.5 rounded-lg text-[#94a3b8] hover:bg-white/60 hover:text-[#0f172a] transition"
        >
          <Icon.close className="w-4 h-4" />
        </button>

        <h2 className="text-lg font-bold text-[#0f172a] mb-1">
          {habit ? '编辑习惯' : '新建习惯'}
        </h2>
        <p className="text-xs text-[#475569] mb-5">
          习惯的价值在于连续的轨迹，从一件小事开始
        </p>

        <div className="space-y-4">
          <div>
            <label className="text-xs font-semibold text-[#475569] block mb-1.5">
              名称
            </label>
            <input
              value={draft.name}
              onChange={(e) => patch({ name: e.target.value })}
              placeholder="例如：每天读 20 页书"
              className={field}
            />
          </div>

          <div>
            <label className="text-xs font-semibold text-[#475569] block mb-1.5">
              图标
            </label>
            <div className="grid grid-cols-8 gap-1.5">
              {HABIT_ICONS.map((i) => (
                <button
                  key={i.key}
                  type="button"
                  onClick={() => patch({ icon: i.key })}
                  aria-label={i.key}
                  className={`h-9 rounded-lg text-base grid place-items-center transition ${
                    draft.icon === i.key
                      ? 'bg-[rgba(37,99,235,0.10)] ring-2 ring-[#06b6d4]'
                      : 'bg-white/40 hover:bg-white/70'
                  }`}
                >
                  {i.emoji}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="text-xs font-semibold text-[#475569] block mb-1.5">
              颜色
            </label>
            <div className="flex flex-wrap gap-2">
              {HABIT_COLORS.map((c) => (
                <button
                  key={c}
                  type="button"
                  onClick={() => patch({ color: c })}
                  aria-label={c}
                  style={{ backgroundColor: c }}
                  className={`w-7 h-7 rounded-lg transition ${
                    draft.color === c
                      ? 'ring-2 ring-offset-2 ring-[#06b6d4]'
                      : 'opacity-80 hover:opacity-100'
                  }`}
                />
              ))}
            </div>
          </div>

          <div>
            <label className="text-xs font-semibold text-[#475569] block mb-1.5">
              打卡方式
            </label>
            <div className="grid grid-cols-4 gap-2">
              {TYPES.map((t) => (
                <Seg
                  key={t}
                  active={draft.type === t}
                  onClick={() => patch({ type: t })}
                >
                  {TYPE_LABEL[t]}
                </Seg>
              ))}
            </div>
          </div>

          {needTarget && (
            <div className="flex gap-3">
              <div className="flex-1">
                <label className="text-xs font-semibold text-[#475569] block mb-1.5">
                  每日目标
                </label>
                <input
                  type="number"
                  min={1}
                  max={9999}
                  value={draft.target}
                  onChange={(e) =>
                    patch({ target: Math.max(1, Number(e.target.value) || 1) })
                  }
                  className={field}
                />
              </div>
              <div className="flex-1">
                <label className="text-xs font-semibold text-[#475569] block mb-1.5">
                  单位
                </label>
                <input
                  value={draft.unit}
                  onChange={(e) => patch({ unit: e.target.value })}
                  placeholder="次 / 分钟 / 杯"
                  className={field}
                />
              </div>
            </div>
          )}

          <div>
            <label className="text-xs font-semibold text-[#475569] block mb-1.5">
              频率
            </label>
            <div className="grid grid-cols-4 gap-2">
              {FREQS.map((f) => (
                <Seg
                  key={f}
                  active={draft.frequency === f}
                  onClick={() => patch({ frequency: f })}
                >
                  {FREQ_LABEL[f]}
                </Seg>
              ))}
            </div>
          </div>

          {draft.frequency === 'custom' && (
            <div>
              <label className="text-xs font-semibold text-[#475569] block mb-1.5">
                选择星期
              </label>
              <div className="flex gap-1.5">
                {WEEKDAY_LABEL.map((w, i) => {
                  const on = (draft.weekdays ?? []).includes(i)
                  return (
                    <button
                      key={i}
                      type="button"
                      onClick={() =>
                        patch({
                          weekdays: on
                            ? (draft.weekdays ?? []).filter((x) => x !== i)
                            : [...(draft.weekdays ?? []), i].sort(),
                        })
                      }
                      className={`flex-1 py-2 rounded-xl text-xs font-semibold border transition ${
                        on
                          ? 'bg-[rgba(37,99,235,0.08)] border-[#06b6d4] text-[#2563eb]'
                          : 'border-white/75 bg-white/40 text-[#475569] hover:bg-white/70'
                      }`}
                    >
                      {w}
                    </button>
                  )
                })}
              </div>
            </div>
          )}

          <div>
            <label className="text-xs font-semibold text-[#475569] block mb-1.5">
              开始日期
            </label>
            <input
              type="date"
              value={draft.start_date ?? ''}
              onChange={(e) => patch({ start_date: e.target.value })}
              className={field}
            />
          </div>
        </div>

        <div className="flex gap-2 mt-6">
          <button type="button" onClick={onClose} className={`${btnGhost} flex-1`}>
            取消
          </button>
          <button
            type="button"
            onClick={submit}
            disabled={!draft.name.trim() || saving}
            className={`${btnPrim} flex-1`}
          >
            {saving ? '保存中…' : '保存'}
          </button>
        </div>
      </div>
    </div>
  )
}
