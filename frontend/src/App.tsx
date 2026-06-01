import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import Home from './pages/Home'
import Notes from './pages/Notes'
import NoteDetail from './pages/NoteDetail'
import Chat from './pages/Chat'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Home />} />
        <Route path="notes" element={<Notes />} />
        <Route path="notes/:id" element={<NoteDetail />} />
        <Route path="chat" element={<Chat />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}

export default App
