/**
 * Service API du tableau de bord (indicateurs et échéances à traiter).
 */
import api from '../lib/api';

export const dashboardService = {
    async getSummary(horizonDays = 90) {
        const { data } = await api.get('/dashboard/summary', { params: { horizon_days: horizonDays } });
        return data;
    },
};

export default dashboardService;
