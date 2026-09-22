/**
 * Gestion des utilisateurs : création de comptes locaux, rôles, activation
 * (validation des comptes Microsoft en attente), réinitialisation de mot de passe.
 */
import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { KeyRound, ShieldCheck, ShieldOff, Trash2, UserCheck, UserPlus, UserX } from 'lucide-react';
import Modal from '../common/Modal';
import { Alert, EmptyState, LoadingBlock } from '../common/Feedback';
import usersService from '../../services/usersService';
import { useAuth } from '../../context/AuthContext';
import { apiErrorMessage } from '../../lib/api';
import { formatAgo } from '../../lib/format';

const EMPTY_USER = { username: '', email: '', full_name: '', password: '', is_admin: false };

function CreateUserModal({ open, onClose }) {
    const queryClient = useQueryClient();
    const [form, setForm] = useState(EMPTY_USER);
    const [error, setError] = useState('');
    const mutation = useMutation({
        mutationFn: () => usersService.create({ ...form, full_name: form.full_name.trim() || null }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['users'] });
            setForm(EMPTY_USER);
            onClose();
        },
        onError: (err) => setError(apiErrorMessage(err)),
    });
    const set = (field) => (e) => setForm((f) => ({ ...f, [field]: e.target.type === 'checkbox' ? e.target.checked : e.target.value }));

    return (
        <Modal open={open} onClose={onClose} size="md" icon={UserPlus} title="Nouveau compte local"
            footer={
                <>
                    <button type="button" className="btn-secondary" onClick={onClose}>Annuler</button>
                    <button type="submit" form="create-user-form" className="btn-primary" disabled={mutation.isPending}>Créer le compte</button>
                </>
            }>
            <form id="create-user-form" className="space-y-4" onSubmit={(e) => { e.preventDefault(); setError(''); mutation.mutate(); }}>
                {error && <Alert tone="error">{error}</Alert>}
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                    <div>
                        <label className="label" htmlFor="u-username">Identifiant *</label>
                        <input id="u-username" className="input" required minLength={3} maxLength={100} pattern="[A-Za-z0-9._@\-]+"
                            value={form.username} onChange={set('username')} />
                    </div>
                    <div>
                        <label className="label" htmlFor="u-name">Nom complet</label>
                        <input id="u-name" className="input" maxLength={255} value={form.full_name} onChange={set('full_name')} />
                    </div>
                    <div className="sm:col-span-2">
                        <label className="label" htmlFor="u-email">E-mail *</label>
                        <input id="u-email" type="email" className="input" required value={form.email} onChange={set('email')} />
                    </div>
                    <div className="sm:col-span-2">
                        <label className="label" htmlFor="u-password">Mot de passe temporaire *</label>
                        <input id="u-password" type="password" autoComplete="new-password" className="input" required minLength={12}
                            value={form.password} onChange={set('password')} />
                        <p className="mt-1 text-xs text-gray-500">12 caractères minimum ; l&apos;utilisateur devra le changer à sa première connexion.</p>
                    </div>
                </div>
                <label className="flex items-center gap-2 text-sm text-gray-700">
                    <input type="checkbox" className="h-4 w-4 rounded border-gray-300" checked={form.is_admin} onChange={set('is_admin')} />
                    Administrateur (création, modification et suppression des contrats)
                </label>
            </form>
        </Modal>
    );
}

function ResetPasswordModal({ user, onClose }) {
    const queryClient = useQueryClient();
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const mutation = useMutation({
        mutationFn: () => usersService.resetPassword(user.id, password),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['users'] });
            setPassword('');
            onClose();
        },
        onError: (err) => setError(apiErrorMessage(err)),
    });
    return (
        <Modal open={Boolean(user)} onClose={onClose} size="sm" icon={KeyRound} title={`Réinitialiser : ${user?.display_name || ''}`}
            footer={
                <>
                    <button type="button" className="btn-secondary" onClick={onClose}>Annuler</button>
                    <button type="submit" form="reset-form" className="btn-primary" disabled={mutation.isPending}>Réinitialiser</button>
                </>
            }>
            <form id="reset-form" className="space-y-3" onSubmit={(e) => { e.preventDefault(); setError(''); mutation.mutate(); }}>
                {error && <Alert tone="error">{error}</Alert>}
                <label className="label" htmlFor="reset-password">Mot de passe temporaire</label>
                <input id="reset-password" type="password" autoComplete="new-password" className="input" minLength={12} required
                    value={password} onChange={(e) => setPassword(e.target.value)} />
                <p className="text-xs text-gray-500">Les sessions ouvertes de ce compte sont fermées ; le changement sera imposé à la prochaine connexion.</p>
            </form>
        </Modal>
    );
}

export default function UserManagement({ localAuthEnabled }) {
    const { user: me } = useAuth();
    const queryClient = useQueryClient();
    const [creating, setCreating] = useState(false);
    const [resetting, setResetting] = useState(null);
    const [error, setError] = useState('');
    const { data: users = [], isLoading } = useQuery({ queryKey: ['users'], queryFn: usersService.getAll });

    const update = useMutation({
        mutationFn: ({ id, changes }) => usersService.update(id, changes),
        onSuccess: () => { setError(''); queryClient.invalidateQueries({ queryKey: ['users'] }); },
        onError: (err) => setError(apiErrorMessage(err)),
    });
    const remove = useMutation({
        mutationFn: (id) => usersService.delete(id),
        onSuccess: () => { setError(''); queryClient.invalidateQueries({ queryKey: ['users'] }); },
        onError: (err) => setError(apiErrorMessage(err)),
    });

    // Les nouveaux comptes Microsoft sont créés inactifs tant qu'un administrateur ne les valide pas
    const pending = users.filter((u) => u.auth_provider === 'entra' && !u.is_active);

    return (
        <div className="space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="text-sm text-gray-600">
                    Les administrateurs gèrent les contrats ; les autres comptes sont en lecture seule.
                </p>
                {localAuthEnabled && (
                    <button type="button" className="btn-primary" onClick={() => setCreating(true)}>
                        <UserPlus className="h-4 w-4" /> Nouveau compte local
                    </button>
                )}
            </div>
            {pending.length > 0 && (
                <Alert tone="warning">
                    {pending.length} compte(s) Microsoft inactif(s), dont les nouveaux comptes en attente de validation :
                    activez ceux qui doivent accéder au Cockpit.
                </Alert>
            )}
            {error && <Alert tone="error">{error}</Alert>}

            <div className="card overflow-hidden">
                {isLoading ? <LoadingBlock /> : users.length === 0 ? <EmptyState title="Aucun utilisateur" /> : (
                    <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-200">
                            <thead className="bg-gray-50">
                                <tr>
                                    <th className="table-th">Utilisateur</th>
                                    <th className="table-th">Connexion</th>
                                    <th className="table-th">Rôle</th>
                                    <th className="table-th">État</th>
                                    <th className="table-th">Dernière connexion</th>
                                    <th className="table-th text-right">Actions</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-100">
                                {users.map((u) => {
                                    const self = u.id === me?.id;
                                    return (
                                        <tr key={u.id}>
                                            <td className="table-td">
                                                <span className="block font-medium text-gray-900">{u.display_name}{self && ' (vous)'}</span>
                                                <span className="block text-xs text-gray-500">{u.email}</span>
                                            </td>
                                            <td className="table-td">
                                                {u.auth_provider === 'entra' ? <span className="badge-blue">Microsoft</span> : <span className="badge-gray">Local</span>}
                                            </td>
                                            <td className="table-td">{u.is_admin ? <span className="badge-violet">Administrateur</span> : <span className="badge-gray">Lecture</span>}</td>
                                            <td className="table-td">
                                                {u.is_active ? <span className="badge-green">Actif</span>
                                                    : u.auth_provider === 'entra' ? <span className="badge-amber">En attente / désactivé</span> : <span className="badge-gray">Désactivé</span>}
                                                {u.must_change_password && <span className="badge-amber ml-1">Mot de passe à changer</span>}
                                            </td>
                                            <td className="table-td whitespace-nowrap text-xs text-gray-500">{u.last_login ? formatAgo(u.last_login) : 'Jamais'}</td>
                                            <td className="table-td">
                                                <div className="flex justify-end gap-1">
                                                    <button type="button" className="btn-ghost p-1.5" disabled={self || update.isPending}
                                                        title={u.is_active ? 'Désactiver' : 'Activer'}
                                                        onClick={() => update.mutate({ id: u.id, changes: { is_active: !u.is_active } })}>
                                                        {u.is_active ? <UserX className="h-4 w-4" /> : <UserCheck className="h-4 w-4 text-emerald-600" />}
                                                    </button>
                                                    <button type="button" className="btn-ghost p-1.5" disabled={self || update.isPending}
                                                        title={u.is_admin ? 'Retirer les droits administrateur' : 'Nommer administrateur'}
                                                        onClick={() => update.mutate({ id: u.id, changes: { is_admin: !u.is_admin } })}>
                                                        {u.is_admin ? <ShieldOff className="h-4 w-4" /> : <ShieldCheck className="h-4 w-4" />}
                                                    </button>
                                                    {localAuthEnabled && u.auth_provider === 'local' && (
                                                        <button type="button" className="btn-ghost p-1.5" title="Réinitialiser le mot de passe" onClick={() => setResetting(u)}>
                                                            <KeyRound className="h-4 w-4" />
                                                        </button>
                                                    )}
                                                    <button type="button" className="btn-ghost p-1.5 text-red-600" disabled={self || remove.isPending} title="Supprimer"
                                                        onClick={() => window.confirm(`Supprimer le compte « ${u.display_name} » ?`) && remove.mutate(u.id)}>
                                                        <Trash2 className="h-4 w-4" />
                                                    </button>
                                                </div>
                                            </td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            <CreateUserModal open={creating} onClose={() => setCreating(false)} />
            <ResetPasswordModal user={resetting} onClose={() => setResetting(null)} />
        </div>
    );
}
