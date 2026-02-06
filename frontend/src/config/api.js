/**
 * Configuration de l'API client.
 */
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001';

export const API_ENDPOINTS = {
    // Authentification
    AUTH_LOGIN: `${API_BASE_URL}/auth/login`,
    AUTH_CALLBACK: `${API_BASE_URL}/auth/callback`,
    AUTH_ME: `${API_BASE_URL}/auth/me`,
    AUTH_REFRESH: `${API_BASE_URL}/auth/refresh`,

    // Contrats
    CONTRACTS: `${API_BASE_URL}/contracts`,
    CONTRACTS_TIMELINE: `${API_BASE_URL}/contracts/timeline/data`,

    // Tickets
    TICKETS_PROJECTS: `${API_BASE_URL}/tickets/projects`,
    TICKETS_STATS: `${API_BASE_URL}/tickets/stats`,
    TICKETS_TIMELINE: `${API_BASE_URL}/tickets/timeline/data`,

    // Health
    HEALTH: `${API_BASE_URL}/health`,
};

export default API_BASE_URL;
