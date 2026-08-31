import type { ReactNode } from 'react'
import Sidebar from './components/Sidebar'
import BottomNav from './components/BottomNav'
import type { Summary } from '../types'

interface LayoutProps {
  summary: Summary | null
  selected: string
  onSelect: (key: string | number) => void
  children: ReactNode
}

export default function Layout({ summary, selected, onSelect, children }: LayoutProps) {
  return (
    <div className="flex h-screen overflow-hidden bg-transparent md:gap-4 md:p-4">
      <Sidebar summary={summary} selected={selected} onSelect={onSelect} />
      <div className="flex-1 min-w-0 flex flex-col overflow-hidden md:rounded-3xl md:bg-white/35 md:border md:border-white/60 md:backdrop-blur-[18px] md:shadow-[0_20px_50px_-20px_rgba(8,145,178,0.25)]">
        {children}
      </div>
      <BottomNav />
    </div>
  )
}
