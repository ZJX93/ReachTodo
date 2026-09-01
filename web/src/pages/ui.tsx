import type { ReactNode } from 'react'

// 抵达 · Reach — 设计系统前端原子组件 / 类
// 液态玻璃主题：蓝(#2563eb) → 青(#06b6d4) → 青绿(#14b8a6)

// —— 复用类 ——
export const card =
  'bg-white/55 backdrop-blur-[18px] border border-white/75 rounded-2xl shadow-[0_8px_24px_-12px_rgba(8,145,178,0.30)]'
export const cardLg =
  'bg-white/55 backdrop-blur-[18px] border border-white/75 rounded-3xl shadow-[0_20px_50px_-20px_rgba(8,145,178,0.35)]'
export const header =
  'sticky top-0 z-10 bg-white/55 backdrop-blur-[18px] border-b border-white/75 px-3 md:px-4 py-4'
export const field =
  'w-full border border-white/75 rounded-xl px-3 py-2.5 text-sm bg-white/70 text-[#0f172a] placeholder:text-[#94a3b8] focus:border-[#06b6d4] focus:ring-2 focus:ring-[#06b6d4]/20 transition'
export const btnPrim =
  'text-white text-sm font-semibold px-4 py-2 rounded-xl brand-gradient shadow-[0_8px_24px_-12px_rgba(8,145,178,0.30)] hover:opacity-95 transition disabled:opacity-60'
export const btnGhost =
  'text-sm font-semibold px-3 py-2 rounded-xl border border-white/75 text-[#475569] bg-white/40 hover:bg-white/60 transition'
export const pill = 'text-[11px] font-semibold px-2 py-0.5 rounded-full'
export const gradText =
  'bg-[linear-gradient(135deg,#2563eb,#06b6d4,#14b8a6)] bg-clip-text text-transparent'

// —— 线性图标（currentColor 描边）——
const S = (children: ReactNode, className = 'w-4 h-4') => (
  <svg
    viewBox="0 0 24 24"
    className={className}
    stroke="currentColor"
    strokeWidth="1.8"
    fill="none"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    {children}
  </svg>
)

// 每个图标都是一个可接收 className 的组件（修复原先传 className 被忽略的问题）
const make = (node: ReactNode) => (props?: { className?: string }) =>
  S(node, props?.className)

export const Icon = {
  search: make(
    <>
      <circle cx="11" cy="11" r="7" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
    </>,
  ),
  clock: make(
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 2" />
    </>,
  ),
  cal: make(
    <>
      <rect x="3" y="4" width="18" height="18" rx="2" />
      <line x1="16" y1="2" x2="16" y2="6" />
      <line x1="8" y1="2" x2="8" y2="6" />
      <line x1="3" y1="10" x2="21" y2="10" />
    </>,
  ),
  pencil: make(
    <>
      <path d="M12 20h9" />
      <path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z" />
    </>,
  ),
  close: make(
    <>
      <line x1="6" y1="6" x2="18" y2="18" />
      <line x1="18" y1="6" x2="6" y2="18" />
    </>,
  ),
  chart: make(
    <>
      <line x1="4" y1="20" x2="4" y2="10" />
      <line x1="10" y1="20" x2="10" y2="4" />
      <line x1="16" y1="20" x2="16" y2="13" />
      <line x1="20" y1="20" x2="2" y2="20" />
    </>,
  ),
  flag: make(
    <>
      <path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z" />
      <line x1="4" y1="22" x2="4" y2="15" />
    </>,
  ),
  flame: make(
    <path d="M12 2s4 4 4 8a4 4 0 0 1-8 0c0-1 .5-2 1-3 .5 1 1.5 1.5 1.5 1.5C9 5 12 2 12 2z" />,
  ),
  plus: make(
    <>
      <line x1="12" y1="5" x2="12" y2="19" />
      <line x1="5" y1="12" x2="19" y2="12" />
    </>,
  ),
  check: make(<polyline points="20 6 9 17 4 12" />),
}

// —— 导航图标（与 Sidebar 一致）——
const NAV = {
  todo: (
    <>
      <path d="M9 11l3 3L22 4" />
      <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
    </>
  ),
  matrix: (
    <>
      <rect x="3" y="3" width="7" height="7" rx="1" />
      <rect x="14" y="3" width="7" height="7" rx="1" />
      <rect x="3" y="14" width="7" height="7" rx="1" />
      <rect x="14" y="14" width="7" height="7" rx="1" />
    </>
  ),
  doc: (
    <>
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="16" y1="13" x2="8" y2="13" />
      <line x1="16" y1="17" x2="8" y2="17" />
    </>
  ),
  cal: (
    <>
      <rect x="3" y="4" width="18" height="18" rx="2" />
      <line x1="16" y1="2" x2="16" y2="6" />
      <line x1="8" y1="2" x2="8" y2="6" />
      <line x1="3" y1="10" x2="21" y2="10" />
    </>
  ),
  chart: (
    <>
      <line x1="4" y1="20" x2="4" y2="10" />
      <line x1="10" y1="20" x2="10" y2="4" />
      <line x1="16" y1="20" x2="16" y2="13" />
      <line x1="20" y1="20" x2="2" y2="20" />
    </>
  ),
  timer: (
    <>
      <circle cx="12" cy="13" r="8" />
      <path d="M12 9v4l2 2" />
      <path d="M9 2h6" />
    </>
  ),
  goal: (
    <>
      <path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z" />
      <line x1="4" y1="22" x2="4" y2="15" />
    </>
  ),
  // 习惯站：一株新芽 —— 习惯的语义是「慢慢长出来」，不是「做完打勾」
  sprout: (
    <>
      <path d="M12 21v-9" />
      <path d="M12 12c0-3.9 3.1-7 7-7 0 3.9-3.1 7-7 7z" />
      <path d="M12 12c0-3.3-2.7-6-6-6 0 3.3 2.7 6 6 6z" />
    </>
  ),
  brand: (
    <>
      <path d="M18.36 5.64 L14.26 14.26 L12 12 L9.74 9.74 Z" fill="#FFFFFF"/>
      <path d="M7.05 16.95 L14.26 14.26 L12 12 L9.74 9.74 Z" fill="#E3F4F5" fill-opacity="0.7"/>
      <circle cx="12" cy="12" r="2" fill="#0A7382"/>
    </>
  ),
  info: (
    <>
      <circle cx="12" cy="12" r="9" />
      <line x1="12" y1="16" x2="12" y2="12" />
      <line x1="12" y1="8" x2="12.01" y2="8" />
    </>
  ),
}

export function NavIcon({ name, className = 'w-5 h-5' }: { name: keyof typeof NAV; className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      className={className}
      stroke="currentColor"
      strokeWidth="1.8"
      fill="none"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {NAV[name]}
    </svg>
  )
}
