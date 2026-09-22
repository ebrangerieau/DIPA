/**
 * Contexte d'authentification : l'état de session est obtenu auprès du backend
 * (/auth/me), le cookie httpOnly n'étant pas lisible en JavaScript.
 */
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import authService from '../services/authService';
import { setUnauthorizedHandler } from '../lib/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
    const queryClient = useQueryClient();
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);

    const refresh = useCallback(async () => {
        try {
            const profile = await authService.me();
            setUser(profile);
            return profile;
        } catch {
            setUser(null);
            return null;
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        // Session expirée pendant l'utilisation : retour à la page de connexion
        setUnauthorizedHandler(() => {
            setUser(null);
            queryClient.clear();
        });
        refresh();
        return () => setUnauthorizedHandler(null);
    }, [refresh, queryClient]);

    const login = useCallback(async (username, password) => {
        const profile = await authService.loginLocal(username, password);
        setUser(profile);
        return profile;
    }, []);

    const logout = useCallback(async () => {
        try {
            await authService.logout();
        } finally {
            setUser(null);
            queryClient.clear();
        }
    }, [queryClient]);

    const value = useMemo(
        () => ({ user, loading, isAdmin: Boolean(user?.is_admin), login, logout, refresh, setUser }),
        [user, loading, login, logout, refresh],
    );

    return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
    return useContext(AuthContext);
}
