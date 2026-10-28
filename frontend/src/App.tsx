import { useEffect, useState } from 'react'
import './App.css'
import { PolicyCheckPage } from './pages/PolicyCheckPage'
import { BreachCheckPage } from './pages/BreachCheckPage'
import { DesignCheckPage } from './pages/DesignCheckPage'

type ActivePoc = 'PoC1' | 'PoC2' | 'PoC3'
type Theme = 'light' | 'dark'

function getInitialTheme(): Theme {
  const savedTheme = window.localStorage.getItem('pipa-theme')
  if (savedTheme === 'light' || savedTheme === 'dark') {
    return savedTheme
  }

  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

function App() {
  const [activePoc, setActivePoc] = useState<ActivePoc>('PoC1')
  const [theme, setTheme] = useState<Theme>(getInitialTheme)

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    document.documentElement.style.colorScheme = theme
    window.localStorage.setItem('pipa-theme', theme)
  }, [theme])

  return (
    <main className="dev-shell">
      <header className="app-header">
        <div className="app-header-copy">
          <p className="eyebrow">PIPA-DPV Compliance Prototype</p>
          <h1>개인정보보호 검토 지원</h1>
          <p className="app-description">
            자연어 문서와 구조화 설계정보를 Fact로 변환하고, 온톨로지와 기계판독형 규칙으로
            검토 결과를 제공함.
          </p>
        </div>
        <button
          type="button"
          className="theme-toggle"
          onClick={() => setTheme((current) => (current === 'light' ? 'dark' : 'light'))}
          aria-label={theme === 'light' ? '다크 모드로 전환' : '라이트 모드로 전환'}
          aria-pressed={theme === 'dark'}
        >
          <span aria-hidden="true">{theme === 'light' ? '☾' : '☀'}</span>
          {theme === 'light' ? '다크 모드' : '라이트 모드'}
        </button>
      </header>

      <nav className="poc-nav">
        <button
          type="button"
          className={activePoc === 'PoC1' ? 'active' : ''}
          onClick={() => setActivePoc('PoC1')}
        >
          PoC1 - 처리방침 준수점검
        </button>
        <button
          type="button"
          className={activePoc === 'PoC2' ? 'active' : ''}
          onClick={() => setActivePoc('PoC2')}
        >
          PoC2 - 침해사고 통지 요건 검토
        </button>
        <button
          type="button"
          className={activePoc === 'PoC3' ? 'active' : ''}
          onClick={() => setActivePoc('PoC3')}
        >
          PoC3 - Privacy-by-Design 개발 지원
        </button>
      </nav>

      {activePoc === 'PoC1' && <PolicyCheckPage />}
      {activePoc === 'PoC2' && <BreachCheckPage />}
      {activePoc === 'PoC3' && <DesignCheckPage />}
    </main>
  )
}

export default App
