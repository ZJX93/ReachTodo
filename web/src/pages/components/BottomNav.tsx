import { useNavigate, useLocation } from 'react-router-dom'
import { NavIcon } from '../ui'

const ITEMS = [
  { path: '/', icon: 'todo', label: '看板' },
  { path: '/matrix', icon: 'matrix', label: '四象限' },
  { path: '/records', icon: 'doc', label: '记录' },
  { path: '/calendar', icon: 'cal', label: '日历' },
  { path: '/goals', icon: 'goal', label: '目标' },
  { path: '/stats', icon: 'chart', label: '回顾' },
  { path: '/focus', icon: 'timer', label: '专注' },
  { path: '/about', icon: 'info', label: '关于' },
]

export default function BottomNav() {
  const navigate = useNavigate()
  const { pathname } = useLocation()
  return (
    <nav className="md:hidden fixed bottom-0 left-0 right-0 z-30 flex justify-around bg-white/55 backdrop-blur-[18px] border-t border-white/75 pb-[env(safe-area-inset-bottom)]">
      {ITEMS.map((it) => {
        const active = pathname === it.path
        return (
          <button
            key={it.path}
            onClick={() => navigate(it.path)}
            className={`flex flex-col items-center gap-0.5 py-2 px-1.5 text-[10px] font-semibold rounded-xl transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#06b6d4] ${
              active ? 'text-[#2563eb]' : 'text-[#94a3b8]'
            }`}
          >
            <NavIcon name={it.icon} className="w-[19px] h-[19px]" />
            {it.label}
          </button>
        )
      })}
    </nav>
  )
}
