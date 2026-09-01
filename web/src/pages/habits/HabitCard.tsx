import { useEffect, useState } from 'react'
import { card, Icon } from '../ui'
import {
  FREQ_LABEL,
  TYPE_LABEL,
  iconEmoji,
  type CheckinPayload,
  type TodayItem,
} from '../../services/habits'

interface Props {
  habit: TodayItem
  busy?: boolean
  onCheckin: (habit: TodayItem, payload: CheckinPayload) => void
  onDetail: (habit: TodayItem) => void
}

function StepBtn({
  label,
  disabled,
  onClick,
}: {
  label: string
  disabled?: boolean
  onClick: () => void
}) {
  return (
    <button
      disabled={disabled}
      onClick={onClick}
      aria-label={label === '+' ? '增加一次' : '减少一次'}
      className="w-9 h-9 rounded-xl border border-white/75 bg-white/50 text-[#475569] text-lg font-bold grid place-items-center hover:bg-white/80 transition disabled:opacity-40"
    >
      {label}
    </button>
  )
}

export default function HabitCard({ habit, busy, onCheckin, onDetail }: Props) {
  const [draft, setDraft] = useState('')
  const ci = habit.checkin
  const value = ci?.value ?? 0
  const done = habit.done_today

  // 时长输入框是受控的，外部数据变化（刷新、切页）后要同步回显
  useEffect(() => {
    setDraft(ci ? String(ci.value) : '')
  }, [habit.id, ci?.value])

  const targetText =
    habit.type === 'count'
      ? `目标 ${habit.target}${habit.unit}`
      : habit.type === 'duration'
        ? `目标 ${habit.target} 分钟`
        : habit.type === 'timerange'
          ? '记录起止时间'
          : '完成即打勾'

  const pct = Math.round(Math.min(1, habit.progress || 0) * 100)

  const commitDuration = () => {
    const n = Number(draft)
    onCheckin(habit, { value: Number.isFinite(n) ? Math.max(0, Math.trunc(n)) : 0 })
  }

  const timeField =
    'flex-1 min-w-0 border border-white/75 rounded-xl px-2.5 py-2 text-sm bg-white/70 text-[#0f172a] focus:border-[#06b6d4] focus:ring-2 focus:ring-[#06b6d4]/20 transition'

  return (
    <div
      className={`${card} p-4 flex flex-col gap-3 transition ${
        done ? 'ring-2 ring-[#14b8a6]/40' : ''
      }`}
    >
      <div className="flex items-start gap-3">
        <div
          className="w-11 h-11 rounded-xl grid place-items-center text-xl shrink-0"
          style={{ backgroundColor: `${habit.color}22` }}
        >
          {iconEmoji(habit.icon)}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <h3 className="font-semibold text-[#0f172a] truncate">{habit.name}</h3>
            {habit.streak > 0 && (
              <span className="inline-flex items-center gap-0.5 text-[11px] font-bold text-[#f97316] shrink-0">
                <Icon.flame className="w-3.5 h-3.5" />
                {habit.streak}
              </span>
            )}
          </div>
          <div className="text-[11px] text-[#94a3b8] mt-0.5 truncate">
            {targetText} · {FREQ_LABEL[habit.frequency]}
          </div>
        </div>
        <button
          onClick={() => onDetail(habit)}
          title="统计与补卡"
          aria-label="查看统计与补卡"
          className="p-1.5 rounded-lg text-[#94a3b8] hover:text-[#06b6d4] hover:bg-white/60 transition shrink-0"
        >
          <Icon.chart className="w-4 h-4" />
        </button>
      </div>

      {habit.type !== 'check' && (
        <div className="h-1.5 rounded-full bg-white/60 overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-300"
            style={{ width: `${pct}%`, backgroundColor: habit.color }}
          ></div>
        </div>
      )}

      {habit.type === 'check' && (
        <button
          disabled={busy}
          onClick={() => onCheckin(habit, { value: done ? 0 : 1 })}
          className={`w-full flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm font-semibold transition disabled:opacity-60 ${
            done
              ? 'bg-[#14b8a6] text-white shadow-[0_8px_24px_-12px_rgba(8,145,178,0.6)]'
              : 'border border-white/75 bg-white/50 text-[#475569] hover:bg-white/70'
          }`}
        >
          <Icon.check className="w-4 h-4" />
          {done ? '今日已完成' : '打卡'}
        </button>
      )}

      {habit.type === 'count' && (
        <div className="flex items-center gap-2">
          <StepBtn
            label="−"
            disabled={busy || value <= 0}
            onClick={() => onCheckin(habit, { value: Math.max(0, value - 1) })}
          />
          <div className="flex-1 text-center">
            <span className="text-lg font-extrabold text-[#0f172a]">{value}</span>
            <span className="text-xs text-[#94a3b8]">
              {' '}
              / {habit.target}
              {habit.unit}
            </span>
          </div>
          <StepBtn
            label="+"
            disabled={busy}
            onClick={() => onCheckin(habit, { value: value + 1 })}
          />
        </div>
      )}

      {habit.type === 'duration' && (
        <div className="flex items-center gap-2">
          <input
            type="number"
            min={0}
            value={draft}
            disabled={busy}
            onChange={(e) => setDraft(e.target.value)}
            onBlur={commitDuration}
            onKeyDown={(e) => {
              if (e.key === 'Enter') e.currentTarget.blur()
            }}
            placeholder="0"
            className="w-20 border border-white/75 rounded-xl px-3 py-2 text-sm bg-white/70 text-[#0f172a] placeholder:text-[#94a3b8] focus:border-[#06b6d4] focus:ring-2 focus:ring-[#06b6d4]/20 transition"
          />
          <span className="text-xs text-[#94a3b8] shrink-0">/ {habit.target} 分钟</span>
          <div className="flex-1" />
          {[5, 10].map((n) => (
            <button
              key={n}
              disabled={busy}
              onClick={() => onCheckin(habit, { value: value + n })}
              className="text-xs font-semibold px-2.5 py-1.5 rounded-lg border border-white/75 bg-white/40 text-[#475569] hover:bg-white/70 transition disabled:opacity-60"
            >
              +{n}
            </button>
          ))}
        </div>
      )}

      {habit.type === 'timerange' && (
        <div className="flex items-center gap-2">
          <input
            type="time"
            value={ci?.start_time ?? ''}
            disabled={busy}
            onChange={(e) =>
              onCheckin(habit, {
                start_time: e.target.value,
                end_time: ci?.end_time ?? '',
              })
            }
            className={timeField}
          />
          <span className="text-[#94a3b8] shrink-0">→</span>
          <input
            type="time"
            value={ci?.end_time ?? ''}
            disabled={busy}
            onChange={(e) =>
              onCheckin(habit, {
                start_time: ci?.start_time ?? '',
                end_time: e.target.value,
              })
            }
            className={timeField}
          />
        </div>
      )}
    </div>
  )
}
