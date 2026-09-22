/**
 * Service d'authentification (session par cookie httpOnly).
 */
import api, { API_BASE_URL } from '../lib/api';

export const authService = {
    async getConfig() {
        const { data } = await api.get('/auth/config', { skipAuthHandler: true });
        return data;
    },

    /** Profil de l'utilisateur connecté (401 si aucune session). */
    async me() {
        const { data } = await api.get('/auth/me', { skipAuthHandler: true });
        return data;
    },

    async loginLocal(username, password) {
        const form = new URLSearchParams({ username, password });
        const { data } = await api.post('/auth/login/local', form, { skipAuthHandler: true });
        return data.user;
    },

    async logout() {
        await api.post('/auth/logout', null, { skipAuthHandler: true });
    },

    async changePassword(currentPassword, newPassword) {
        await api.post('/auth/change-password', {
            current_password: currentPassword,
            new_password: newPassword,
        });
    },

    /** URL de connexion Microsoft (navigation complète, pas d'appel XHR). */
    ssoLoginUrl() {
        return `${API_BASE_URL}/auth/login`;
    },
};

export default authService;
