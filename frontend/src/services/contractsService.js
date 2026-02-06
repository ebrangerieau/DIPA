/**
 * Service API pour les contrats.
 */
import axios from 'axios';
import { API_ENDPOINTS } from '../config/api';

const api = axios.create({
    headers: {
        'Content-Type': 'application/json',
    },
});

export const contractsService = {
    /**
     * Récupère tous les contrats.
     */
    async getAll(params = {}) {
        const response = await api.get(API_ENDPOINTS.CONTRACTS, { params });
        return response.data;
    },

    /**
     * Récupère un contrat par ID.
     */
    async getById(id) {
        const response = await api.get(`${API_ENDPOINTS.CONTRACTS}/${id}`);
        return response.data;
    },

    /**
     * Crée un nouveau contrat.
     */
    async create(contractData) {
        const response = await api.post(API_ENDPOINTS.CONTRACTS, contractData);
        return response.data;
    },

    /**
     * Met à jour un contrat.
     */
    async update(id, contractData) {
        const response = await api.put(`${API_ENDPOINTS.CONTRACTS}/${id}`, contractData);
        return response.data;
    },

    /**
     * Supprime un contrat.
     */
    async delete(id) {
        await api.delete(`${API_ENDPOINTS.CONTRACTS}/${id}`);
    },

    /**
     * Récupère les données de timeline des contrats.
     */
    async getTimelineData() {
        const response = await api.get(API_ENDPOINTS.CONTRACTS_TIMELINE);
        return response.data;
    },
};

export default contractsService;
