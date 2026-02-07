/**
 * Page de login.
 */
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { LogIn } from 'lucide-react';
import authService from '../services/authService';

export default function Login() {
    const navigate = useNavigate();
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setLoading(true);

        try {
            const data = await authService.loginLocal(username, password);
            authService.setToken(data.access_token);
            navigate('/');
        } catch (err) {
            setError(err.response?.data?.detail || 'Erreur de connexion');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-gradient-to-br from-primary-50 to-primary-100 flex items-center justify-center p-4">
            <div className="bg-white rounded-lg shadow-xl p-8 w-full max-w-md">
                {/* Header */}
                <div className="text-center mb-8">
                    <div className="inline-flex items-center justify-center w-16 h-16 bg-primary-600 rounded-full mb-4">
                        <LogIn className="w-8 h-8 text-white" />
                    </div>
                    <h1 className="text-2xl font-bold text-gray-900">Cockpit IT</h1>
                    <p className="text-gray-600 mt-2">Connectez-vous à votre compte</p>
                </div>

                {/* Formulaire */}
                <form onSubmit={handleSubmit} className="space-y-6">
                    {/* Message d'erreur */}
                    {error && (
                        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md text-sm">
                            {error}
                        </div>
                    )}

                    {/* Username */}
                    <div>
                        <label htmlFor="username" className="block text-sm font-medium text-gray-700 mb-2">
                            Nom d'utilisateur
                        </label>
                        <input
                            id="username"
                            name="username"
                            type="text"
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                            required
                            className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none transition-colors"
                            placeholder="admin"
                        />
                    </div>

                    {/* Password */}
                    <div>
                        <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-2">
                            Mot de passe
                        </label>
                        <input
                            id="password"
                            name="password"
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            required
                            className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none transition-colors"
                            placeholder="••••••••"
                        />
                    </div>

                    {/* Bouton de connexion */}
                    <button
                        type="submit"
                        disabled={loading}
                        className="w-full bg-primary-600 text-white py-2 px-4 rounded-md hover:bg-primary-700 focus:ring-4 focus:ring-primary-300 transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-medium"
                    >
                        {loading ? 'Connexion...' : 'Se connecter'}
                    </button>
                </form>

                {/* Info par défaut */}
                <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-md">
                    <p className="text-sm text-blue-800">
                        <strong>Compte par défaut :</strong>
                        <br />
                        Username: <code className="bg-blue-100 px-1 rounded">admin</code>
                        <br />
                        Password: <code className="bg-blue-100 px-1 rounded">Admin1234567</code>
                    </p>
                </div>
            </div>
        </div>
    );
}
