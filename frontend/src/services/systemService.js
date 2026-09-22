/**
 * Service API système : sauvegarde / restauration, état, alertes, journal.
 */
import api, { downloadBlob, filenameFromResponse } from '../lib/api';

export const systemService = {
    /** Télécharge la sauvegarde JSON des contrats et de leur historique. */
    async downloadBackup() {
        const response = await api.get('/system/backup', { responseType: 'blob' });
        downloadBlob(response.data, filenameFromResponse(response, 'cockpit-it_sauvegarde.json'));
    },

    /**
     * Restaure une sauvegarde JSON.
     * @param {File} file - Fichier produit par la sauvegarde
     * @param {'merge'|'replace'} mode - Fusion ou remplacement complet
     */
    async restoreBackup(file, mode) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('mode', mode);
        const { data } = await api.post('/system/restore', formData);
        return data;
    },

    async getStatus() {
        const { data } = await api.get('/system/status');
        return data;
    },

    async previewAlerts() {
        const { data } = await api.get('/system/alerts/preview');
        return data;
    },

    async runAlerts() {
        const { data } = await api.post('/system/alerts/run');
        return data;
    },

    async sendTestEmail() {
        const { data } = await api.post('/system/alerts/test');
        return data;
    },

    async getEvents(limit = 100) {
        const { data } = await api.get('/system/events', { params: { limit } });
        return data;
    },
};

export default systemService;
