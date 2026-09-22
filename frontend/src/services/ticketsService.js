/**
 * Service API pour les tickets Zammad.
 */
import api from '../lib/api';

export const ticketsService = {
    async getProjectTickets() {
        const { data } = await api.get('/tickets/projects');
        return data;
    },

    /** Tickets clos par jour : { start_date, end_date, exclude_projects }. */
    async getStats(params = {}) {
        const { data } = await api.get('/tickets/stats', { params });
        return data;
    },

    async getTimelineData() {
        const { data } = await api.get('/tickets/timeline/data');
        return data;
    },

    async getById(id) {
        const { data } = await api.get(`/tickets/${id}`);
        return data;
    },
};

export default ticketsService;
