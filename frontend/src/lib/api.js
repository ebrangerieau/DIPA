/**
 * Client HTTP de l'API.
 * - Même origine que l'application : /api est relayé par Vite (dev) ou Nginx (production) ;
 * - La session est portée par un cookie httpOnly : aucun jeton n'est manipulé en JavaScript ;
 * - L'en-tête X-Requested-With est exigé par le backend pour les requêtes modifiantes (anti-CSRF).
 */
import axios from 'axios';

export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '');

const api = axios.create({
    baseURL: API_BASE_URL,
    withCredentials: true,
    headers: { 'X-Requested-With': 'XMLHttpRequest' },
});

let unauthorizedHandler = null;

/** Enregistre la fonction appelée quand la session expire (réponse 401). */
export function setUnauthorizedHandler(handler) {
    unauthorizedHandler = handler;
}

api.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response?.status === 401 && unauthorizedHandler && !error.config?.skipAuthHandler) {
            unauthorizedHandler();
        }
        return Promise.reject(error);
    },
);

/** Message d'erreur lisible à partir d'une erreur axios. */
export function apiErrorMessage(error, fallback = 'Une erreur est survenue.') {
    const detail = error?.response?.data?.detail;
    if (typeof detail === 'string' && detail) return detail;
    if (Array.isArray(detail)) return detail.map((d) => d.msg).join(' ; ');
    if (!error?.response) return 'Serveur injoignable : vérifiez votre connexion.';
    if (error.response.status === 403) return 'Action non autorisée.';
    if (error.response.status === 502) return 'Service externe indisponible.';
    return fallback;
}

/** Nom de fichier annoncé par l'en-tête Content-Disposition. */
export function filenameFromResponse(response, fallback) {
    const header = response.headers?.['content-disposition'] || '';
    const match = header.match(/filename="?([^";]+)"?/i);
    return match ? match[1] : fallback;
}

/** Déclenche le téléchargement d'un Blob dans le navigateur. */
export function downloadBlob(blob, filename) {
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
}

export default api;
