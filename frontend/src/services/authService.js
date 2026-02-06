/**
 * Service d'authentification.
 */
import axios from 'axios';
import { API_ENDPOINTS } from '../config/api';

const api = axios.create({
    headers: {
        'Content-Type': 'application/json',
    },
});

export const authService = {
    /**
     * Login avec username/password (authentification locale).
     */
    async loginLocal(username, password) {
        const formData = new URLSearchParams();
        formData.append('username', username);
        formData.append('password', password);

        const response = await api.post(
            `${API_ENDPOINTS.AUTH_LOGIN}/local`,
            formData,
            {
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
            }
        );

        return response.data;
    },

    /**
     * Récupère le profil de l'utilisateur connecté.
     */
    async getProfile(token) {
        const response = await api.get(`${API_ENDPOINTS.AUTH_ME.replace('/me', '/profile')}`, {
            headers: {
                Authorization: `Bearer ${token}`,
            },
        });
        return response.data;
    },

    /**
     * Stocke le token dans le localStorage.
     */
    setToken(token) {
        localStorage.setItem('access_token', token);
    },

    /**
     * Récupère le token du localStorage.
     */
    getToken() {
        return localStorage.getItem('access_token');
    },

    /**
     * Supprime le token (logout).
     */
    removeToken() {
        localStorage.removeItem('access_token');
    },

    /**
     * Vérifie si l'utilisateur est connecté.
     */
    isAuthenticated() {
        return !!this.getToken();
    },
};

export default authService;
