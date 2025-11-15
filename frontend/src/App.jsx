import React from 'react'
import Chat from './components/Chat'

export default function App() {
  return (
    <div className="app-root">
      <header className="app-header"> 
        <h1>Chatbot</h1>
      </header>
      <main>
        <Chat />
      </main>
      <footer className="app-footer">Built with FastAPI + React + Vite</footer>
    </div>
  )
}
