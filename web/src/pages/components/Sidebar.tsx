import { useState } from 'react'
import type { ReactNode } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../../auth'
import ProfileModal from '../ProfileModal'
import type { Summary } from '../../types'

interface NavItem {
  key: string
  path: string
  label: string
  icon: ReactNode
  count?: number
}

interface SidebarProps {
  summary: Summary | null
  selected: string
  onSelect: (key: string | number) => void
}

const icons = {
  todo: (
    <svg viewBox="0 0 24 24" className="w-5 h-5" stroke="currentColor" strokeWidth="1.8" fill="none" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>
    </svg>
  ),
  matrix: (
    <svg viewBox="0 0 24 24" className="w-5 h-5" stroke="currentColor" strokeWidth="1.8" fill="none" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/>
      <rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>
    </svg>
  ),
  doc: (
    <svg viewBox="0 0 24 24" className="w-5 h-5" stroke="currentColor" strokeWidth="1.8" fill="none" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>
    </svg>
  ),
  cal: (
    <svg viewBox="0 0 24 24" className="w-5 h-5" stroke="currentColor" strokeWidth="1.8" fill="none" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>
    </svg>
  ),
  chart: (
    <svg viewBox="0 0 24 24" className="w-5 h-5" stroke="currentColor" strokeWidth="1.8" fill="none" strokeLinecap="round" strokeLinejoin="round">
      <line x1="4" y1="20" x2="4" y2="10"/><line x1="10" y1="20" x2="10" y2="4"/><line x1="16" y1="20" x2="16" y2="13"/><line x1="22" y1="20" x2="2" y2="20"/>
    </svg>
  ),
  timer: (
    <svg viewBox="0 0 24 24" className="w-5 h-5" stroke="currentColor" strokeWidth="1.8" fill="none" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="13" r="8"/><path d="M12 9v4l2 2"/><path d="M9 2h6"/>
    </svg>
  ),
  goal: (
    <svg viewBox="0 0 24 24" className="w-5 h-5" stroke="currentColor" strokeWidth="1.8" fill="none" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/><line x1="4" y1="22" x2="4" y2="15"/>
    </svg>
  ),
  info: (
    <svg viewBox="0 0 24 24" className="w-5 h-5" stroke="currentColor" strokeWidth="1.8" fill="none" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="9"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/>
    </svg>
  ),
}

const brand = (
  <svg viewBox="0 0 24 24" className="w-5 h-5">
    <path d="M18.36 5.64 L14.26 14.26 L12 12 L9.74 9.74 Z" fill="#FFFFFF"/>
    <path d="M7.05 16.95 L14.26 14.26 L12 12 L9.74 9.74 Z" fill="#E3F4F5" fill-opacity="0.7"/>
    <circle cx="12" cy="12" r="2" fill="#0A7382"/>
  </svg>
)

export default function Sidebar({ summary, selected, onSelect }: SidebarProps) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const cats = summary?.categories || []
  const [profileOpen, setProfileOpen] = useState(false)

  const isActive = (path: string): boolean =>
    path === '/'
      ? location.pathname === '/' && selected === 'all'
      : location.pathname === path

  const desktopNav: NavItem[] = [
    { key: 'all', path: '/', label: '今日待办', icon: icons.todo, count: summary ? (summary.today_todo ?? summary.total_todo) : 0 },
    { key: 'matrix', path: '/matrix', label: '四象限', icon: icons.matrix },
    { key: 'records', path: '/records', label: '记录', icon: icons.doc },
    { key: 'calendar', path: '/calendar', label: '日历', icon: icons.cal },
    { key: 'stats', path: '/stats', label: '回顾 / 数据', icon: icons.chart },
  ]

  const footNav: NavItem[] = [
    { key: 'focus', path: '/focus', label: '专注 / 番茄钟', icon: icons.timer },
    { key: 'goals', path: '/goals', label: '我的目标', icon: icons.goal },
    { key: 'about', path: '/about', label: '关于', icon: icons.info },
  ]

  const navClick = (item: NavItem) => {
    navigate(item.path)
    onSelect(item.key)
  }

  const baseItem = `w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-sm transition duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#06b6d4] focus-visible:ring-offset-2 focus-visible:ring-offset-transparent`

  return (
    <aside className="sidebar hidden md:flex w-64 shrink-0 h-full rounded-3xl bg-white/55 border border-white/75 backdrop-blur-[18px] shadow-[0_20px_50px_-20px_rgba(8,145,178,0.35)] flex-col overflow-hidden">
      <div className="flex items-center gap-3 px-5 py-5">
        <div className="w-10 h-10 rounded-2xl brand-gradient grid place-items-center text-white font-bold text-lg shadow-[0_8px_24px_-12px_rgba(8,145,178,0.3)]">
          {brand}
        </div>
        <div>
          <div className="text-[17px] font-bold text-[#0f172a] leading-tight font-[Sora]">抵达 · Reach</div>
          <div className="text-[11px] text-[#475569]">清单与目标</div>
        </div>
      </div>

      <nav className="flex-1 overflow-y-auto px-3 space-y-1">
        {desktopNav.map((item) => (
          <button
            key={item.key}
            onClick={() => navClick(item)}
            className={`${baseItem} ${
              isActive(item.path) && selected === item.key
                ? 'bg-[rgba(37,99,235,0.08)] text-[#2563eb] font-semibold before:content-[""] before:absolute before:left-0 before:top-2 before:bottom-2 before:w-[3px] before:rounded-full before:brand-gradient'
                : 'text-[#475569] hover:bg-white/40'
            } relative`}
          >
            <span className="flex items-center gap-3">
              {item.icon}
              {item.label}
            </span>
            {typeof item.count === 'number' && (
              <span className="text-xs text-[#475569] font-semibold">{item.count}</span>
            )}
          </button>
        ))}

        <div className="pt-4 pb-1 px-3 text-xs font-semibold uppercase tracking-wide text-[#94a3b8]">维度分类</div>
        {cats.map((c) => (
          <button
            key={c.category_id}
            onClick={() => {
              navigate('/')
              onSelect(c.category_id)
            }}
            className={`${baseItem} ${
              selected === c.category_id
                ? 'bg-white/40 font-semibold text-[#0f172a]'
                : 'text-[#475569] hover:bg-white/40'
            }`}
          >
            <span className="flex items-center gap-2 truncate">
              <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: c.color }}></span>
              <span className="truncate">{c.name}</span>
            </span>
            <span className="text-xs text-[#475569]">{c.todo}</span>
          </button>
        ))}
      </nav>

      <div className="p-3 border-t border-[rgba(15,23,42,0.06)] space-y-1">
        {footNav.map((item) => (
          <button
            key={item.key}
            onClick={() => navClick(item)}
            className={`${baseItem} ${
              isActive(item.path) && selected === item.key
                ? 'bg-[rgba(37,99,235,0.08)] text-[#2563eb] font-semibold'
                : 'text-[#475569] hover:bg-white/40'
            }`}
          >
            <span className="flex items-center gap-3">
              {item.icon}
              {item.label}
            </span>
          </button>
        ))}
        <div className="flex items-center justify-between gap-1 px-2 pt-1">
          <button
            onClick={() => setProfileOpen(true)}
            title="查看 / 修改个人信息"
            className="flex items-center gap-2 min-w-0 px-2 py-1.5 rounded-lg text-sm text-[#475569] hover:bg-white/60 hover:text-[#0f172a] transition"
          >
            <span className="w-7 h-7 shrink-0 rounded-lg brand-gradient grid place-items-center text-white text-xs font-bold">
              {(user?.username?.[0] || '?').toUpperCase()}
            </span>
            <span className="truncate">@{user?.username}</span>
          </button>
          <button
            onClick={() => navigate('/settings')}
            title="系统设置"
            aria-label="系统设置"
            className="p-2 rounded-lg text-[#475569] hover:bg-white/60 hover:text-[#0f172a] transition"
          >
            <svg
              viewBox="0 0 24 24"
              className="w-4 h-4"
              stroke="currentColor"
              strokeWidth="1.8"
              fill="none"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <circle cx="12" cy="12" r="3" />
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33h0a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82v0a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
            </svg>
          </button>
        </div>
        <button
          onClick={logout}
          className="block w-full text-left px-3 py-1.5 text-xs text-[#475569] hover:text-[#ef4444] hover:bg-white/60 rounded-lg transition font-medium"
        >
          退出
        </button>
      </div>

      <ProfileModal open={profileOpen} onClose={() => setProfileOpen(false)} />
    </aside>
  )
}
