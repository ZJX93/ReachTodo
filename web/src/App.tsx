import { Routes, Route, Navigate } from 'react-router-dom'
import { lazy, Suspense } from 'react'
import { useAuth } from './auth'
import Login from './pages/Login'

// 路由级代码分割：首屏只加载 Login，其余页面按需加载（E6）
const Dashboard = lazy(() => import('./pages/Dashboard'))
const Goals = lazy(() => import('./pages/Goals'))
const Matrix = lazy(() => import('./pages/Matrix'))
const Stats = lazy(() => import('./pages/Stats'))
const Habits = lazy(() => import('./pages/Habits'))
const Focus = lazy(() => import('./pages/Focus'))
const Records = lazy(() => import('./pages/Records'))
const Calendar = lazy(() => import('./pages/Calendar'))
const Settings = lazy(() => import('./pages/Settings'))
const About = lazy(() => import('./pages/About'))

function Protected({ children }) {
  const { isAuth } = useAuth()
  return isAuth ? children : <Navigate to="/login" replace />
}

function PageLoader() {
  return (
    <div className="min-h-screen grid place-items-center bg-[#f8fafc]">
      <div className="text-sm text-[#94a3b8] animate-pulse">加载中…</div>
    </div>
  )
}

export default function App() {
  const { isAuth } = useAuth()
  return (
    <Suspense fallback={<PageLoader />}>
      <Routes>
        <Route
          path="/login"
          element={isAuth ? <Navigate to="/" replace /> : <Login />}
        />
        <Route
          path="/"
          element={
            <Protected>
              <Dashboard />
            </Protected>
          }
        />
        <Route
          path="/matrix"
          element={
            <Protected>
              <Matrix />
            </Protected>
          }
        />
        <Route
          path="/goals"
          element={
            <Protected>
              <Goals />
            </Protected>
          }
        />
        <Route
          path="/stats"
          element={
            <Protected>
              <Stats />
            </Protected>
          }
        />
        <Route
          path="/habits"
          element={
            <Protected>
              <Habits />
            </Protected>
          }
        />
        <Route
          path="/focus"
          element={
            <Protected>
              <Focus />
            </Protected>
          }
        />
        <Route
          path="/records"
          element={
            <Protected>
              <Records />
            </Protected>
          }
        />
        <Route
          path="/calendar"
          element={
            <Protected>
              <Calendar />
            </Protected>
          }
        />
        <Route
          path="/settings"
          element={
            <Protected>
              <Settings />
            </Protected>
          }
        />
        <Route
          path="/about"
          element={
            <Protected>
              <About />
            </Protected>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  )
}
