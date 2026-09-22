/**
 * Sauvegarde et restauration des contrats (fichier JSON validé par le serveur).
 */
import { useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { Database, Download, Upload } from 'lucide-react';
import { Alert } from '../common/Feedback';
import systemService from '../../services/systemService';
import { apiErrorMessage } from '../../lib/api';

export default function BackupRestore() {
    const queryClient = useQueryClient();
    const fileInputRef = useRef(null);
    const [mode, setMode] = useState('merge');
    const [busy, setBusy] = useState(false);
    const [message, setMessage] = useState(null);

    const handleBackup = async () => {
        setBusy(true);
        setMessage(null);
        try {
            await systemService.downloadBackup();
            setMessage({ tone: 'success', text: 'Sauvegarde téléchargée. Conservez-la dans un espace protégé (elle contient les montants des contrats).' });
        } catch (err) {
            setMessage({ tone: 'error', text: apiErrorMessage(err, 'La sauvegarde a échoué.') });
        } finally {
            setBusy(false);
        }
    };

    const handleFile = async (event) => {
        const file = event.target.files?.[0];
        event.target.value = '';
        if (!file) return;
        const warning = mode === 'replace'
            ? 'ATTENTION : tous les contrats actuels et leur historique seront remplacés par ceux de la sauvegarde. Continuer ?'
            : 'Les contrats de la sauvegarde seront ajoutés ou mis à jour. Continuer ?';
        if (!window.confirm(warning)) return;

        setBusy(true);
        setMessage(null);
        try {
            const result = await systemService.restoreBackup(file, mode);
            queryClient.invalidateQueries();
            setMessage({
                tone: 'success',
                text: `Restauration terminée : ${result.created} contrat(s) créé(s), ${result.updated} mis à jour${result.events ? `, ${result.events} entrée(s) d'historique` : ''}.`,
            });
        } catch (err) {
            setMessage({ tone: 'error', text: apiErrorMessage(err, 'La restauration a échoué.') });
        } finally {
            setBusy(false);
        }
    };

    return (
        <div className="card space-y-4 p-5">
            <h3 className="flex items-center gap-2 text-base font-semibold text-gray-900">
                <Database className="h-5 w-5 text-primary-600" /> Sauvegarde et restauration des contrats
            </h3>
            <p className="text-sm text-gray-600">
                Export JSON des contrats et de leur historique (les comptes utilisateurs ne sont pas inclus).
                La sauvegarde complète de la base PostgreSQL se fait sur le serveur (script <code className="rounded bg-gray-100 px-1">scripts/backup_db.sh</code>).
            </p>

            {message && <Alert tone={message.tone}>{message.text}</Alert>}

            <div className="flex flex-wrap items-end gap-4">
                <button type="button" onClick={handleBackup} disabled={busy} className="btn-primary">
                    <Download className="h-4 w-4" /> Télécharger une sauvegarde
                </button>

                <div className="flex flex-wrap items-end gap-2">
                    <div>
                        <label className="label" htmlFor="restore-mode">Mode de restauration</label>
                        <select id="restore-mode" className="input" value={mode} onChange={(e) => setMode(e.target.value)}>
                            <option value="merge">Fusion (ajoute / met à jour)</option>
                            <option value="replace">Remplacement complet</option>
                        </select>
                    </div>
                    <input type="file" ref={fileInputRef} onChange={handleFile} accept=".json,application/json" className="hidden" />
                    <button type="button" onClick={() => fileInputRef.current?.click()} disabled={busy}
                        className={mode === 'replace' ? 'btn-danger' : 'btn-secondary'}>
                        <Upload className="h-4 w-4" /> Restaurer…
                    </button>
                </div>
            </div>
        </div>
    );
}
