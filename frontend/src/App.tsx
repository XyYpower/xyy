import { Routes, Route, Navigate } from 'react-router-dom'
import AuthRoute from './components/AuthRoute'
import Layout from './components/Layout'
import Home from './pages/Home'
import Notes from './pages/Notes'
import NoteDetail from './pages/NoteDetail'
import Chat from './pages/Chat'
import Login from './pages/Login'
import Register from './pages/Register'
import Review from './pages/Review'
import Import from './pages/Import'
import Paths from './pages/Paths'
import Interview from './pages/Interview'
import Settings from './pages/Settings'

function App() {
  return (
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
          <Route path="paths" element={<Paths />} />
          <Route path="settings" element={<Settings />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Route>
    </Routes>
  )
}

export default App
