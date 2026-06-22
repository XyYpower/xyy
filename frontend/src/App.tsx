import { lazy, Suspense } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { Spin } from 'antd'
import AuthRoute from './components/AuthRoute'
import Layout from './components/Layout'
import Login from './pages/Login'
import Register from './pages/Register'

const Home = lazy(() => import('./pages/Home'))
const Notes = lazy(() => import('./pages/Notes'))
const NoteDetail = lazy(() => import('./pages/NoteDetail'))
const Chat = lazy(() => import('./pages/Chat'))
const Review = lazy(() => import('./pages/Review'))
const Interview = lazy(() => import('./pages/Interview'))
const Import = lazy(() => import('./pages/Import'))
const Settings = lazy(() => import('./pages/Settings'))

const PageLoading = () => (
  <div className="flex justify-center items-center p-16">
    <Spin size="large" />
  </div>
)

function App() {
  return (
    <Suspense fallback={<PageLoading />}>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route element={<AuthRoute />}>
          <Route path="/" element={<Layout />}>
            <Route index element={<Home />} />
            <Route path="notes" element={<Notes />} />
            <Route path="notes/:id" element={<NoteDetail />} />
            <Route path="chat" element={<Chat />} />
            <Route path="review" element={<Review />} />
            <Route path="interview" element={<Interview />} />
            <Route path="import" element={<Import />} />
            <Route path="settings" element={<Settings />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Route>
      </Routes>
    </Suspense>
  )
}

export default App
