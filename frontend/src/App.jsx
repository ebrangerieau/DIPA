import { BrowserRouter as Router, Navigate, Route, Routes, useLocation } from 'react-router-dom'
import AppLayout from './components/layout/AppLayout'
import { PageSpinner } from './components/common/Feedback'
import { useAuth } from './context/AuthContext'
import Admin from './pages/Admin'
import Contracts from './pages/Contracts'
import Dashboard from './pages/Dashboard'
import Login from './pages/Login'

// Composant pour protéger les routes
function RequireAuth({ children }) {
    const { user, loading } = useAuth();
    const location = useLocation();
    if (loading) return <PageSpinner />;
    if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
    return children;
}

function RequireAdmin({ children }) {
    const { isAdmin } = useAuth();
    return isAdmin ? children : <Navigate to="/" replace />;
}

function App() {
    return (
        <Router>
            <Routes>
                <Route path="/login" element={<Login />} />
                <Route
                    element={
                        <RequireAuth>
                            <AppLayout />
                        </RequireAuth>
                    }
                >
                    <Route index element={<Dashboard />} />
                    <Route path="contrats" element={<Contracts />} />
                    <Route
                        path="admin"
                        element={
                            <RequireAdmin>
                                <Admin />
                            </RequireAdmin>
                        }
                    />
                </Route>
                <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
        </Router>
    )
}

export default App
