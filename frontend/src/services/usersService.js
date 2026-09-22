/**
 * Service API de gestion des utilisateurs (administrateurs).
 */
import api from '../lib/api';

export const usersService = {
    async getAll() {
        const { data } = await api.get('/users');
        return data;
    },

    async create(user) {
        const { data } = await api.post('/users', user);
        return data;
    },

    async update(id, changes) {
        const { data } = await api.patch(`/users/${id}`, changes);
        return data;
    },

    async resetPassword(id, newPassword) {
        const { data } = await api.post(`/users/${id}/reset-password`, { new_password: newPassword });
        return data;
    },

    async delete(id) {
        await api.delete(`/users/${id}`);
    },
};

export default usersService;
