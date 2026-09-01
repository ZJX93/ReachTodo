import { useEffect, useState } from 'react'
import { btnGhost, cardLg, Icon } from '../ui'
import {
  TYPE_LABEL,
  habitsApi,
  iconEmoji,
  isScheduledOn,
  type CheckinPayload,
  type HabitStats,
  type TodayItem,
} from '../../services/habits'

interface Props {
  habit: TodayItem | null
  /** 服务端认定的「今天」，用于禁止给未来日期补卡 */
  todayDate: string
  onClose: () => void
  onCheckin: (habit: TodayItem, payload: CheckinPayload) => Promise<void> | void
  onEdit: (habit: TodayItem) => void
  onDelete: (habit: TodayItem) => void
}

function Mini({ label, value, unit }: { label: string; value: string; unit: string }) {
  return (
    <div className="rounded-xl border border-white/60 bg-white/45 p-3 text-center">
      <div className="text-[17px] font-extrabold text-[#0f172a] leading-tight">
        {value}
        <span className="text-[10px] font-semibold text-[#94a3b8] ml-0.5">{unit}</span>
      </div>
      <div className="text-[10px] text-[#94a3b8] mt-1">{label}</div>
    </div>
  )
}

export default function HabitDetail({
  habit,
  todayDate,
  onClose,
  onCheckin,
  onEdit,
  onDelete,
}: Props) {
  const [stats, setStats] = useState<HabitStats | null>(null)
  const [loading, setLoading] = useState(false)
  const [nonce, setNonce] = useState(0)

  const habitId = habit?.id

  // 补卡后需要重新拉取统计，nonce 即为「重新加载」的信号
  useEffect(() => {
    if (!habitId) return
    let alive = true
    setLoading(true)
    habitsApi
      .stats(habitId)
      .then((r) => {
        if (alive) setStats(r.data)
      })
      .finally(() => {
        if (alive) setLoading(false)
      })
    return () => {
      alive = false
    }
  }, [habitId, nonce])

  useEffect(() => {
    if (!habitId) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose?.()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [habitId, onClose])

  if (!habit) return null

  const toggle = async (date: string, done: boolean) => {
    const payload: CheckinPayload = {
      date,
      // check 类型达成值是 1；其余类型直接用每日目标填充，省去手输
      value: done ? 0 : habit.type === 'check' ? 1 : habit.target,
    }
    await onCheckin(habit, payload)
    setNonce((n) => n + 1)
  }

  const cells = stats?.last_30 ?? []

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

        <div className="flex items-center gap-3">
          <div
            className="w-12 h-12 rounded-2xl grid place-items-center text-2xl shrink-0"
            style={{ backgroundColor: `${habit.color}22` }}
          >
            {iconEmoji(habit.icon)}
          </div>
          <div className="min-w-0">
            <h2 className="text-lg font-bold text-[#0f172a] truncate">{habit.name}</h2>
            <p className="text-xs text-[#475569]">
              {TYPE_LABEL[habit.type]} · 始于 {habit.start_date}
            </p>
          </div>
        </div>

        <div className="grid grid-cols-4 gap-2 mt-5">
          <Mini label="当前连续" value={String(stats?.streak ?? 0)} unit="天" />
          <Mini label="最长纪录" value={String(stats?.best_streak ?? 0)} unit="天" />
          <Mini label="累计打卡" value={String(stats?.total_checkins ?? 0)} unit="次" />
          <Mini
            label="近 30 天"
            value={String(Math.round((stats?.rate_30 ?? 0) * 100))}
            unit="%"
          />
        </div>

        <div className="mt-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-[#475569]">
              最近 30 天 · 点击补卡 / 取消
            </span>
            <span className="text-[10px] text-[#94a3b8]">
              累计完成率 {Math.round((stats?.rate_all ?? 0) * 100)}%
            </span>
          </div>
          {loading && cells.length === 0 ? (
            <div className="text-xs text-[#94a3b8] py-4 text-center">加载中…</div>
          ) : (
            <div className="grid grid-cols-10 gap-1.5">
              {cells.map((cell) => {
                const d = new Date(`${cell.date}T00:00:00`)
                const scheduled = isScheduledOn(habit, d)
                const future = cell.date > todayDate
                const disabled = future || !scheduled
                const title = !scheduled
                  ? `${cell.date} 非排班日`
                  : future
                    ? `${cell.date} 未到`
                    : `${cell.date} ${cell.done ? '已完成' : '未打卡'}`
                return (
                  <button
                    key={cell.date}
                    disabled={disabled}
                    title={title}
                    onClick={() => toggle(cell.date, cell.done)}
                    className={`aspect-square rounded-md text-[9px] font-bold grid place-items-center transition ${
                      !scheduled
                        ? 'bg-white/20 text-[#cbd5e1] cursor-not-allowed'
                        : cell.done
                          ? 'text-white'
                          : 'bg-white/50 text-[#94a3b8] hover:bg-white/80'
                    } ${future ? 'opacity-40 cursor-not-allowed' : ''}`}
                    style={
                      scheduled && cell.done ? { backgroundColor: habit.color } : undefined
                    }
                  >
                    {d.getDate()}
                  </button>
                )
              })}
            </div>
          )}
        </div>

        <div className="flex gap-2 mt-6">
          <button
            type="button"
            onClick={() => onEdit(habit)}
            className={`${btnGhost} flex items-center justify-center gap-1.5`}
          >
            <Icon.pencil className="w-4 h-4" />
            编辑
          </button>
          <div className="flex-1" />
          <button
            type="button"
            onClick={() => onDelete(habit)}
            className="text-sm font-semibold px-3 py-2 rounded-xl border border-white/75 text-[#ef4444] bg-white/40 hover:bg-[#ef4444]/10 transition"
          >
            删除
          </button>
        </div>
      </div>
    </div>
  )
}
