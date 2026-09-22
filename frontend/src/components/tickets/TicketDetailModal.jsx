/**
 * Détail d'un ticket projet Zammad (CDC §2.1) avec lien direct vers Zammad.
 */
import { ExternalLink, FolderKanban } from 'lucide-react';
import Modal from '../common/Modal';
import { formatDateTime } from '../../lib/format';
import { priorityLabel, stateLabel } from '../../lib/constants';

function Info({ label, children }) {
    return (
        <div>
            <dt className="text-xs font-medium uppercase tracking-wide text-gray-500">{label}</dt>
            <dd className="mt-0.5 text-sm text-gray-900">{children || '—'}</dd>
        </div>
    );
}

export default function TicketDetailModal({ item, onClose }) {
    const m = item?.metadata || {};
    return (
        <Modal
            open={Boolean(item)}
            onClose={onClose}
            size="md"
            icon={FolderKanban}
            title={m.title || 'Ticket'}
            footer={
                <>
                    <button type="button" className="btn-secondary" onClick={onClose}>Fermer</button>
                    {m.url && (
                        <a href={m.url} target="_blank" rel="noopener noreferrer" className="btn-primary">
                            <ExternalLink className="h-4 w-4" /> Voir dans Zammad
                        </a>
                    )}
                </>
            }
        >
            <dl className="grid grid-cols-2 gap-4">
                <Info label="Numéro">{m.number ? `#${m.number}` : `ID ${m.ticket_id}`}</Info>
                <Info label="État">{stateLabel(m.state)}</Info>
                <Info label="Priorité">{priorityLabel(m.priority)}</Info>
                <Info label="Responsable">{m.owner || 'Non assigné'}</Info>
                <Info label="Groupe">{m.group}</Info>
                <Info label="Créé le">{formatDateTime(m.created_at)}</Info>
                <Info label="Clôturé le">{m.close_at ? formatDateTime(m.close_at) : 'En cours'}</Info>
                <Info label="Tags">
                    <span className="flex flex-wrap gap-1">
                        {(m.tags || []).map((t) => <span key={t} className="badge-blue">{t}</span>)}
                    </span>
                </Info>
            </dl>
        </Modal>
    );
}
