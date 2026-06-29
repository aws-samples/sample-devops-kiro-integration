import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import LoginPage from './components/LoginPage';
import NavBar from './components/NavBar';
import ProtectedRoute from './components/ProtectedRoute';
import AdminPanel from './components/AdminPanel';
import ArticleList from './components/ArticleList';
import ArticleDetail from './components/ArticleDetail';
import ArticleForm from './components/ArticleForm';
import './App.css';

function App() {
  const location = useLocation();
  const showNav = location.pathname !== '/login';

  return (
    <>
      {showNav && <NavBar />}
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/articles" element={<ProtectedRoute><ArticleList endpoint="/articles/public" title="Public Articles" /></ProtectedRoute>} />
        <Route path="/articles/mine" element={<ProtectedRoute><ArticleList endpoint="/articles/mine" title="My Articles" /></ProtectedRoute>} />
        <Route path="/articles/new" element={<ProtectedRoute><ArticleForm /></ProtectedRoute>} />
        <Route path="/articles/:id" element={<ProtectedRoute><ArticleDetail /></ProtectedRoute>} />
        <Route path="/admin" element={<ProtectedRoute><AdminPanel /></ProtectedRoute>} />
        <Route path="/" element={<Navigate to="/articles" replace />} />
        <Route path="*" element={<Navigate to="/articles" replace />} />
      </Routes>
    </>
  );
}

export default App;
