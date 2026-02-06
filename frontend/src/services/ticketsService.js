/**
 * Service API pour les tickets Zammad.
 */
import axios from 'axios';
import { API_ENDPOINTS } from '../config/api';

const api = axios.create({
    headers: {
        'Content-Type': 'application/json',
    },
});

export const ticketsService = {
    /**
     * Récupère les tickets avec tag #Projet.
     */
    async getProjectTickets() {
        const response = await api.get(API_ENDPOINTS.TICKETS_PROJECTS);
        return response.data;
    },

    /**
     * Récupère les statistiques des tickets clos.
     */
    async getStats(params = {}) {
        const response = await api.get(API_ENDPOINTS.TICKETS_STATS, { params });
        return response.data;
    },

    /**
     * Récupère les données de timeline des tickets.
     */
    async getTimelineData() {
        const response = await api.get(API_ENDPOINTS.TICKETS_TIMELINE);
        return response.data;
    },

    /**
     * Récupère un ticket par ID.
     */
    async getById(id) {
        const response = await api.get(`${API_ENDPOINTS.TICKETS_PROJECTS.replace('/projects', '')}/${id}`);
        return response.data;
    },
};

export default ticketsService;
