import { Link, Route, Routes } from "react-router-dom";
import Home from "./pages/Home";
import JobDetail from "./pages/JobDetail";
import NewAnalysis from "./pages/NewAnalysis";

const App = () => {
  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="brand">
          <div className="brand-mark">VA</div>
          <div>
            <div className="brand-title">Vision Analytics Studio</div>
            <div className="brand-sub">Sports first. Built for evidence.</div>
          </div>
        </div>
        <nav className="nav">
          <Link to="/">Home</Link>
          <Link to="/new">New Analysis</Link>
        </nav>
      </header>
      <main className="app-main">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/new" element={<NewAnalysis />} />
          <Route path="/jobs/:jobId" element={<JobDetail />} />
        </Routes>
      </main>
    </div>
  );
};

export default App;
