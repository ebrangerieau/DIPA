/**
 * Page de connexion : compte Microsoft (SSO Entra ID) et/ou compte local.
 */
import { useEffect, useState } from 'react';
import { Navigate, useLocation, useNavigate, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { LogIn } from 'lucide-react';
import authService from '../services/authService';
import { useAuth } from '../context/AuthContext';
import { apiErrorMessage } from '../lib/api';
import { Alert, PageSpinner } from '../components/common/Feedback';

const SSO_ERRORS = {
    sso_indisponible: "La connexion Microsoft n'est pas disponible pour le moment.",
    session_expiree: 'La tentative de connexion a expiré. Veuillez recommencer.',
    sso_echec: "Microsoft n'a pas validé la connexion. Veuillez recommencer.",
    acces_refuse: "Votre compte Microsoft n'est pas autorisé à utiliser le Cockpit IT.",
    compte_en_attente: 'Votre compte a bien été créé : un administrateur doit maintenant l\'activer.',
};

function MicrosoftLogo() {
    return (
        <svg className="h-5 w-5" viewBox="0 0 21 21" aria-hidden="true">
            <rect x="1" y="1" width="9" height="9" fill="#f25022" />
            <rect x="11" y="1" width="9" height="9" fill="#7fba00" />
            <rect x="1" y="11" width="9" height="9" fill="#00a4ef" />
            <rect x="11" y="11" width="9" height="9" fill="#ffb900" />
        </svg>
    );
}

export default function Login() {
    const { user, loading, login } = useAuth();
    const navigate = useNavigate();
    const location = useLocation();
    const [searchParams, setSearchParams] = useSearchParams();
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [submitting, setSubmitting] = useState(false);

    const { data: config, isLoading: configLoading } = useQuery({
        queryKey: ['auth-config'],
        queryFn: authService.getConfig,
        staleTime: Infinity,
    });

    const ssoError = searchParams.get('error');
    useEffect(() => {
        if (ssoError) setError(SSO_ERRORS[ssoError] || 'La connexion a échoué.');
    }, [ssoError]);

    if (loading || configLoading) return <PageSpinner />;
    if (user) return <Navigate to={location.state?.from || '/'} replace />;

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setSearchParams({}, { replace: true });
        setSubmitting(true);
        try {
            await login(username, password);
            navigate(location.state?.from || '/', { replace: true });
        } catch (err) {
            setError(apiErrorMessage(err, 'Erreur de connexion'));
        } finally {
            setSubmitting(false);
        }
    };

    const localEnabled = config?.local_enabled ?? true;
    const ssoEnabled = config?.sso_enabled ?? false;

    return (
        <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-primary-50 to-primary-100 p-4">
            <div className="w-full max-w-md rounded-2xl bg-white p-8 shadow-xl">
                <div className="mb-8 text-center">
                    <img src="/favicon.svg" alt="" className="mx-auto mb-4 h-14 w-14" />
                    <h1 className="text-2xl font-bold text-gray-900">Cockpit IT</h1>
                    <p className="mt-2 text-sm text-gray-600">Pilotage des contrats et projets du service informatique</p>
                </div>

                {error && (
                    <Alert tone={ssoError === 'compte_en_attente' ? 'info' : 'error'} className="mb-6">
                        {error}
                    </Alert>
                )}

                {ssoEnabled && (
                    <a href={authService.ssoLoginUrl()} className="btn-secondary w-full py-2.5">
                        <MicrosoftLogo />
                        Se connecter avec Microsoft
                    </a>
                )}

                {ssoEnabled && localEnabled && (
                    <div className="my-6 flex items-center gap-3 text-xs uppercase tracking-wide text-gray-400">
                        <span className="h-px flex-1 bg-gray-200" /> ou <span className="h-px flex-1 bg-gray-200" />
                    </div>
                )}

                {localEnabled && (
                    <form onSubmit={handleSubmit} className="space-y-5">
                        <div>
                            <label htmlFor="username" className="label">Identifiant ou e-mail</label>
                            <input
                                id="username"
                                name="username"
                                type="text"
                                autoComplete="username"
                                value={username}
                                onChange={(e) => setUsername(e.target.value)}
                                required
                                className="input"
                            />
                        </div>
                        <div>
                            <label htmlFor="password" className="label">Mot de passe</label>
                            <input
                                id="password"
                                name="password"
                                type="password"
                                autoComplete="current-password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                required
                                className="input"
                            />
                        </div>
                        <button type="submit" disabled={submitting} className="btn-primary w-full py-2.5">
                            <LogIn className="h-4 w-4" />
                            {submitting ? 'Connexion…' : 'Se connecter'}
                        </button>
                    </form>
                )}

                {!localEnabled && !ssoEnabled && (
                    <Alert tone="warning">{"Aucun mode de connexion n'est configuré. Contactez l'administrateur."}</Alert>
                )}

                {config?.app_version && (
                    <p className="mt-8 text-center text-xs text-gray-400">Version {config.app_version}</p>
                )}
            </div>
        </div>
    );
}
