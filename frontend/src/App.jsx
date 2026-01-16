import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Header from './components/Header';
import Home from './pages/Home';
import Analysis from './pages/Analysis';
import Gym from './pages/Gym';
import History from './pages/History';
import './index.css';

function App() {
  return (
    <Router>
      <div className="min-h-screen" style={{ backgroundColor: 'var(--color-paper)' }}>
        <Header />
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/analysis" element={<Analysis />} />
          <Route path="/analysis/:id" element={<Analysis />} />
          <Route path="/gym/:analysisId" element={<Gym />} />
          <Route path="/history" element={<History />} />
        </Routes>
        
        {/* Footer */}
        <footer 
          className="border-t mt-20"
          style={{ borderColor: 'var(--color-border)' }}
        >
          <div className="container mx-auto px-6 py-8">
            <div className="text-center">
              <p style={{ color: 'var(--color-ink-light)' }}>
                Built with ❤️ for engineering students who want to understand, not just memorize
              </p>
              <p 
                className="text-sm mt-2"
                style={{ color: 'var(--color-ink-light)' }}
              >
                © 2026 Feynman Tutor. Debug Your Intuition.
              </p>
            </div>
          </div>
        </footer>
      </div>
    </Router>
  );
}

export default App;
