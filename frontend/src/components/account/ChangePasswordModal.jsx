/**
 * Changement de mot de passe. En mode « imposé » (mot de passe temporaire, faible
 * ou publié), la fenêtre ne peut pas être fermée avant le changement.
 */
import { useState } from 'react';
import { KeyRound } from 'lucide-react';
import Modal from '../common/Modal';
import { Alert } from '../common/Feedback';
import authService from '../../services/authService';
import { apiErrorMessage } from '../../lib/api';
import { useAuth } from '../../context/AuthContext';

const EMPTY = { current: '', next: '', confirm: '' };

export default function ChangePasswordModal({ open, onClose, forced = false }) {
    const { refresh, logout } = useAuth();
    const [values, setValues] = useState(EMPTY);
    const [error, setError] = useState('');
    const [saving, setSaving] = useState(false);

    const update = (field) => (e) => setValues((v) => ({ ...v, [field]: e.target.value }));

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        if (values.next.length < 12) {
            setError('Le nouveau mot de passe doit contenir au moins 12 caractères.');
            return;
        }
        if (values.next !== values.confirm) {
            setError('La confirmation ne correspond pas au nouveau mot de passe.');
            return;
        }
        setSaving(true);
        try {
            await authService.changePassword(values.current, values.next);
            setValues(EMPTY);
            await refresh();
            onClose?.();
        } catch (err) {
            setError(apiErrorMessage(err, 'Le mot de passe n\'a pas pu être changé.'));
        } finally {
            setSaving(false);
        }
    };

    return (
        <Modal
            open={open}
            onClose={onClose}
            dismissible={!forced}
            size="sm"
            icon={KeyRound}
            title={forced ? 'Changement de mot de passe requis' : 'Changer mon mot de passe'}
            footer={
                <>
                    {forced ? (
                        <button type="button" className="btn-secondary" onClick={logout}>Se déconnecter</button>
                    ) : (
                        <button type="button" className="btn-secondary" onClick={onClose}>Annuler</button>
                    )}
                    <button type="submit" form="change-password-form" className="btn-primary" disabled={saving}>
                        {saving ? 'Enregistrement…' : 'Changer le mot de passe'}
                    </button>
                </>
            }
        >
            <form id="change-password-form" onSubmit={handleSubmit} className="space-y-4">
                {forced && (
                    <Alert tone="warning">
                        Votre mot de passe actuel est temporaire, trop faible ou connu publiquement.
                        Choisissez-en un nouveau pour continuer.
                    </Alert>
                )}
                {error && <Alert tone="error">{error}</Alert>}
                <div>
                    <label className="label" htmlFor="pwd-current">Mot de passe actuel</label>
                    <input id="pwd-current" type="password" className="input" autoComplete="current-password"
                        value={values.current} onChange={update('current')} required />
                </div>
                <div>
                    <label className="label" htmlFor="pwd-new">Nouveau mot de passe</label>
                    <input id="pwd-new" type="password" className="input" autoComplete="new-password"
                        value={values.next} onChange={update('next')} required minLength={12} />
                    <p className="mt-1 text-xs text-gray-500">12 caractères minimum. Une phrase de passe est idéale.</p>
                </div>
                <div>
                    <label className="label" htmlFor="pwd-confirm">Confirmation</label>
                    <input id="pwd-confirm" type="password" className="input" autoComplete="new-password"
                        value={values.confirm} onChange={update('confirm')} required />
                </div>
            </form>
        </Modal>
    );
}
