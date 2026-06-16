import { Routes, Route } from 'react-router-dom';
import DashboardLayout from './layouts/DashboardLayout';
import OverviewPage from './pages/OverviewPage';
import StraitDetailPage from './pages/StraitDetailPage';
import RiskPage from './pages/RiskPage';

export default function App() {
  return (
    <Routes>
      <Route element={<DashboardLayout />}>
        <Route path="/" element={<OverviewPage />} />
        <Route path="/strait" element={<StraitDetailPage />} />
        <Route path="/risk" element={<RiskPage />} />
      </Route>
    </Routes>
  );
}
