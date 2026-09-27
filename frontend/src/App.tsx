import { useState } from 'react'
import './App.css'
import { PolicyCheckPage } from './pages/PolicyCheckPage'
import { BreachCheckPage } from './pages/BreachCheckPage'
import { DesignCheckPage } from './pages/DesignCheckPage'

type ActivePoc = 'PoC1' | 'PoC2' | 'PoC3'

function App() {
  const [activePoc, setActivePoc] = useState<ActivePoc>('PoC1')

  return (
    <main className="dev-shell">
      <nav className="poc-nav">
        <button
          type="button"
          className={activePoc === 'PoC1' ? 'active' : ''}
          onClick={() => setActivePoc('PoC1')}
        >
          PoC1 — 처리방침 준수점검
        </button>
        <button
          type="button"
          className={activePoc === 'PoC2' ? 'active' : ''}
          onClick={() => setActivePoc('PoC2')}
        >
          PoC2 — 침해사고 통지 요건 검토
        </button>
        <button
          type="button"
          className={activePoc === 'PoC3' ? 'active' : ''}
          onClick={() => setActivePoc('PoC3')}
        >
          PoC3 — Privacy-by-Design 개발지원
        </button>
      </nav>

      {activePoc === 'PoC1' && <PolicyCheckPage />}
      {activePoc === 'PoC2' && <BreachCheckPage />}
      {activePoc === 'PoC3' && <DesignCheckPage />}
    </main>
  )
}

export default App
