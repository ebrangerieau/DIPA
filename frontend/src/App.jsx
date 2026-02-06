import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import Login from './pages/Login'
import authService from './services/authService'

// Composant pour protéger les routes
function ProtectedRoute({ children }) {
    const isAuthenticated = authService.isAuthenticated();
    return isAuthenticated ? children : <Navigate to="/login" replace />;
}

function App() {
    return (
        <Router>
            <Routes>
                <Route path="/login" element={<Login />} />
                <Route
                    path="/"
                    element={
                        <ProtectedRoute>
                            <Dashboard />
                        </ProtectedRoute>
                    }
                />
            </Routes>
        </Router>
    )
}

export default App
