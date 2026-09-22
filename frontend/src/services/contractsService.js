/**
 * Service API pour les contrats.
 */
import api, { downloadBlob, filenameFromResponse } from '../lib/api';

const cleanParams = (params = {}) =>
    Object.fromEntries(Object.entries(params).filter(([, v]) => v !== '' && v !== null && v !== undefined));

export const contractsService = {
    async getAll(params = {}) {
        const { data } = await api.get('/contracts', { params: cleanParams(params) });
        return data;
    },

    async getById(id) {
        const { data } = await api.get(`/contracts/${id}`);
        return data;
    },

    async getEvents(id) {
        const { data } = await api.get(`/contracts/${id}/events`);
        return data;
    },

    async getSuppliers() {
        const { data } = await api.get('/contracts/suppliers');
        return data;
    },

    async create(contract) {
        const { data } = await api.post('/contracts', contract);
        return data;
    },

    async update(id, contract) {
        const { data } = await api.put(`/contracts/${id}`, contract);
        return data;
    },

    async delete(id) {
        await api.delete(`/contracts/${id}`);
    },

    async setDecision(id, decision, comment) {
        const { data } = await api.post(`/contracts/${id}/decision`, { decision, comment });
        return data;
    },

    async renew(id, payload) {
        const { data } = await api.post(`/contracts/${id}/renew`, payload);
        return data;
    },

    async getTimelineData() {
        const { data } = await api.get('/contracts/timeline/data');
        return data;
    },

    /** Télécharge la liste filtrée au format CSV (Excel). */
    async exportCsv(params = {}) {
        const response = await api.get('/contracts/export.csv', { params: cleanParams(params), responseType: 'blob' });
        downloadBlob(response.data, filenameFromResponse(response, 'contrats.csv'));
    },
};

export default contractsService;
