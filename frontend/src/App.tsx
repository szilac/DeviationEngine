import { BrowserRouter as Router, Route, Routes, Navigate, useLocation } from 'react-router-dom';
import { AnimatePresence } from 'motion/react';
import PageHeader from './components/layout/PageHeader';
import ManuscriptRuling from './components/layout/ManuscriptRuling';
import PageTransition from './components/layout/PageTransition';
import HomePage from './pages/HomePage';
import ConsolePage from './pages/ConsolePage';
import LibraryPage from './pages/LibraryPage';
import ReportViewPage from './pages/ReportViewPage';
import GroundTruthReportPage from './pages/GroundTruthReportPage';
import AboutPage from './pages/AboutPage';
import SettingsPage from './pages/SettingsPage';
import AdvancedSettingsPage from './pages/AdvancedSettingsPage';
import SkeletonWorkflowPage from './pages/SkeletonWorkflowPage';
import RippleMapPage from './pages/RippleMapPage';
import TemporalAtlasPage from './pages/TemporalAtlasPage';

// Inner component — needs to be inside <Router> to call useLocation
function AppRoutes() {
  const location = useLocation();

  return (
    <AnimatePresence mode="wait">
      <Routes location={location} key={location.pathname}>
        <Route path="/" element={<PageTransition><HomePage /></PageTransition>} />
        <Route path="/console" element={<PageTransition><ConsolePage /></PageTransition>} />
        <Route path="/skeleton-workflow" element={<PageTransition><SkeletonWorkflowPage /></PageTransition>} />
        <Route path="/skeletons" element={<Navigate to="/library?tab=skeletons" replace />} />
        <Route path="/library" element={<PageTransition><LibraryPage /></PageTransition>} />
        <Route path="/saved" element={<Navigate to="/library" replace />} />
        <Route path="/atlas" element={<PageTransition><TemporalAtlasPage /></PageTransition>} />
        <Route path="/reports/:timelineId" element={<PageTransition><ReportViewPage /></PageTransition>} />
        <Route path="/ripple-map/:timelineId" element={<PageTransition><RippleMapPage /></PageTransition>} />
        <Route path="/reports" element={<PageTransition><LibraryPage /></PageTransition>} />
        <Route path="/ground-truth/:reportId" element={<PageTransition><GroundTruthReportPage /></PageTransition>} />
        <Route path="/about" element={<PageTransition><AboutPage /></PageTransition>} />
        <Route path="/settings" element={<PageTransition><SettingsPage /></PageTransition>} />
        <Route path="/settings/advanced" element={<PageTransition><AdvancedSettingsPage /></PageTransition>} />
      </Routes>
    </AnimatePresence>
  );
}

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-vellum text-ink font-body">
        <ManuscriptRuling />
        <PageHeader />
        <main id="main-content">
          <AppRoutes />
        </main>
      </div>
    </Router>
  );
}

export default App;
