import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api'
import Layout from './Layout'
import { cardLg, gradText, header } from './ui'

// 版本号由构建时注入（Docker 构建传入 VITE_APP_VERSION）。
// 发版时 publish.yml 会把 Android Release 的 X.Y.Z 传进来；
// 本地/普通构建无该变量时回落为 dev。
const appVersion = import.meta.env.VITE_APP_VERSION || 'dev'

export default function About() {
  const navigate = useNavigate()
  const [summary, setSummary] = useState<any>(null)
  const [selected, setSelected] = useState('about')

  useEffect(() => {
    api
      .get('/tasks/summary')
      .then((r) => setSummary(r.data))
      .catch(() => {})
  }, [])

  return (
    <Layout summary={summary} selected={selected} onSelect={setSelected}>
      <main className="flex-1 overflow-y-auto md:pb-0 pb-20">
        <header className={`${header} flex items-center gap-3`}>
          <button
            onClick={() => navigate(-1)}
            aria-label="返回"
            className="p-2 rounded-xl bg-white/55 border border-white/75 text-[#475569] hover:text-[#0f172a] hover:bg-white/80 transition"
          >
            <svg
              viewBox="0 0 24 24"
              className="w-4 h-4"
              stroke="currentColor"
              strokeWidth="2"
              fill="none"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <polyline points="15 18 9 12 15 6" />
            </svg>
          </button>
          <div>
            <h1 className={`text-xl font-bold ${gradText}`}>关于</h1>
            <p className="text-xs text-[#475569] mt-0.5">抵达 · Reach — 清单与目标</p>
          </div>
        </header>

        <div className="max-w-2xl mx-auto px-4 md:px-8 py-6 space-y-5">
          <section className={`${cardLg} p-5 md:p-6 flex flex-col items-center text-center gap-3`}>
            <div className="w-16 h-16 rounded-3xl brand-gradient grid place-items-center text-white font-bold text-2xl shadow-[0_8px_24px_-12px_rgba(8,145,178,0.3)]">
              <svg viewBox="0 0 24 24" className="w-8 h-8">
                <path d="M18.36 5.64 L14.26 14.26 L12 12 L9.74 9.74 Z" fill="#FFFFFF" />
                <path d="M7.05 16.95 L14.26 14.26 L12 12 L9.74 9.74 Z" fill="#E3F4F5" fillOpacity="0.7" />
                <circle cx="12" cy="12" r="2" fill="#0A7382" />
              </svg>
            </div>
            <div>
              <div className="text-lg font-bold text-[#0f172a]">抵达 · Reach</div>
              <div className="text-xs text-[#475569] mt-0.5">清单 · 目标 · 专注，一站式自我管理</div>
            </div>
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/70 border border-white/75">
              <span className="text-xs text-[#475569]">版本</span>
              <span className="text-sm font-semibold text-[#0f172a] tabular-nums">v{appVersion}</span>
            </div>
          </section>

          <section className={`${cardLg} p-5 md:p-6`}>
            <h2 className="text-base font-bold text-[#0f172a] mb-3">版本信息</h2>
            <dl className="text-sm space-y-2">
              <div className="flex items-center justify-between">
                <dt className="text-[#475569]">当前版本</dt>
                <dd className="font-semibold text-[#0f172a] tabular-nums">v{appVersion}</dd>
              </div>
              <div className="flex items-center justify-between">
                <dt className="text-[#475569]">构建通道</dt>
                <dd className="font-semibold text-[#0f172a]">{appVersion === 'dev' ? '本地开发' : '正式发布'}</dd>
              </div>
            </dl>
          </section>

          <footer className="text-[11px] text-[#94a3b8] text-center pb-2">
            © {new Date().getFullYear()} 抵达 · Reach · 用心记录每一天的抵达
          </footer>
        </div>
      </main>
    </Layout>
  )
}
