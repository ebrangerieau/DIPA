/**
 * Fiche d'un contrat : détails (CDC §2.1), décision de renouvellement, renouvellement,
 * historique et lien vers le document SharePoint.
 */
import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { addDays, addMonths, format, subDays } from 'date-fns';
import { Edit2, ExternalLink, FileText, History, RotateCcw, Trash2 } from 'lucide-react';
import Modal from '../common/Modal';
import { Alert, LoadingBlock } from '../common/Feedback';
import { DecisionBadge, StatusBadge } from './Badges';
import ContractFormModal from './ContractFormModal';
import contractsService from '../../services/contractsService';
import { useAuth } from '../../context/AuthContext';
import { apiErrorMessage } from '../../lib/api';
import { DECISIONS } from '../../lib/constants';
import { formatCurrency, formatDate, formatDateTime, formatDays, formatMonths, toDate } from '../../lib/format';

const FIELD_LABELS = {
    name: 'Nom', supplier: 'Fournisseur', category: 'Catégorie', amount: 'Montant', duration_months: 'Durée (mois)',
    start_date: 'Début', end_date: 'Fin', notice_period_days: 'Préavis (j)', auto_renewal: 'Reconduction tacite',
    sharepoint_file_url: 'Lien', notes: 'Notes', renewal_decision: 'Décision', decision_comment: 'Commentaire',
};

function Info({ label, children }) {
    return (
        <div>
            <dt className="text-xs font-medium uppercase tracking-wide text-gray-500">{label}</dt>
            <dd className="mt-0.5 text-sm text-gray-900">{children}</dd>
        </div>
    );
}

function describeEvent(event) {
    const d = event.details || {};
    if (event.event_type === 'updated' && d.changes) {
        return Object.keys(d.changes).map((k) => FIELD_LABELS[k] || k).join(', ');
    }
    if (event.event_type === 'decision') {
        return `${DECISIONS[d.apres]?.label || d.apres}${d.commentaire ? ` — ${d.commentaire}` : ''}`;
    }
    if ((event.event_type === 'renewed' || event.event_type === 'auto_renewed') && d.apres) {
        return `Nouvelle période : ${formatDate(d.apres.start_date)} → ${formatDate(d.apres.end_date)}`;
    }
    return '';
}

function RenewForm({ contract, onDone }) {
    const queryClient = useQueryClient();
    const [amount, setAmount] = useState(contract.amount);
    const [months, setMonths] = useState(contract.duration_months);
    const [comment, setComment] = useState('');
    const [error, setError] = useState('');

    const currentEnd = toDate(contract.end_date);
    const start = currentEnd ? addDays(currentEnd, 1) : null;
    const end = start && months > 0 ? subDays(addMonths(start, parseInt(months, 10)), 1) : null;

    const mutation = useMutation({
        mutationFn: () => contractsService.renew(contract.id, {
            amount: parseFloat(amount),
            duration_months: parseInt(months, 10),
            comment: comment.trim() || null,
        }),
        onSuccess: () => {
            ['contracts', 'contracts-timeline', 'dashboard-summary'].forEach((key) => queryClient.invalidateQueries({ queryKey: [key] }));
            queryClient.invalidateQueries({ queryKey: ['contract', contract.id] });
            queryClient.invalidateQueries({ queryKey: ['contract-events', contract.id] });
            onDone();
        },
        onError: (err) => setError(apiErrorMessage(err)),
    });

    return (
        <div className="space-y-3 rounded-lg border border-emerald-200 bg-emerald-50/60 p-4">
            <p className="text-sm font-medium text-emerald-900">Renouveler pour une nouvelle période</p>
            {error && <Alert tone="error">{error}</Alert>}
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <div>
                    <label className="label" htmlFor="r-amount">Nouveau montant total (€)</label>
                    <input id="r-amount" type="number" min="0" step="0.01" className="input" value={amount} onChange={(e) => setAmount(e.target.value)} />
                </div>
                <div>
                    <label className="label" htmlFor="r-months">Durée (mois)</label>
                    <input id="r-months" type="number" min="1" max="240" className="input" value={months} onChange={(e) => setMonths(e.target.value)} />
                </div>
                <div className="sm:col-span-2">
                    <label className="label" htmlFor="r-comment">Commentaire (optionnel)</label>
                    <input id="r-comment" className="input" maxLength={2000} value={comment} onChange={(e) => setComment(e.target.value)}
                        placeholder="Ex. : devis n° 2026-118 validé par la direction" />
                </div>
            </div>
            {start && end && (
                <p className="text-sm text-emerald-900">
                    Nouvelle période : <strong>{format(start, 'dd/MM/yyyy')}</strong> → <strong>{format(end, 'dd/MM/yyyy')}</strong>
                </p>
            )}
            <div className="flex justify-end gap-2">
                <button type="button" className="btn-secondary" onClick={onDone}>Annuler</button>
                <button type="button" className="btn-primary" disabled={mutation.isPending || !(months > 0) || amount === ''}
                    onClick={() => mutation.mutate()}>
                    {mutation.isPending ? 'Renouvellement…' : 'Confirmer le renouvellement'}
                </button>
            </div>
        </div>
    );
}

function DecisionForm({ contract }) {
    const queryClient = useQueryClient();
    const [decision, setDecision] = useState(contract.renewal_decision);
    const [comment, setComment] = useState(contract.decision_comment || '');
    const [error, setError] = useState('');

    useEffect(() => {
        setDecision(contract.renewal_decision);
        setComment(contract.decision_comment || '');
    }, [contract.renewal_decision, contract.decision_comment]);

    const mutation = useMutation({
        mutationFn: () => contractsService.setDecision(contract.id, decision, comment.trim() || null),
        onSuccess: () => {
            ['contracts', 'dashboard-summary', 'contracts-timeline'].forEach((key) => queryClient.invalidateQueries({ queryKey: [key] }));
            queryClient.invalidateQueries({ queryKey: ['contract', contract.id] });
            queryClient.invalidateQueries({ queryKey: ['contract-events', contract.id] });
            setError('');
        },
        onError: (err) => setError(apiErrorMessage(err)),
    });

    const changed = decision !== contract.renewal_decision || (comment || '') !== (contract.decision_comment || '');

    return (
        <div className="space-y-3">
            {error && <Alert tone="error">{error}</Alert>}
            <div className="flex flex-wrap gap-2" role="radiogroup" aria-label="Décision de renouvellement">
                {Object.entries(DECISIONS).map(([value, d]) => (
                    <button key={value} type="button" role="radio" aria-checked={decision === value}
                        onClick={() => setDecision(value)}
                        className={`rounded-full border px-3 py-1 text-sm transition-colors ${decision === value
                            ? 'border-primary-600 bg-primary-600 text-white'
                            : 'border-gray-300 bg-white text-gray-700 hover:bg-gray-50'}`}>
                        {d.label}
                    </button>
                ))}
            </div>
            <textarea rows={2} className="input" maxLength={2000} value={comment} onChange={(e) => setComment(e.target.value)}
                placeholder="Justification, devis comparés, validation de la direction…" />
            <div className="flex justify-end">
                <button type="button" className="btn-primary" disabled={!changed || mutation.isPending} onClick={() => mutation.mutate()}>
                    {mutation.isPending ? 'Enregistrement…' : 'Enregistrer la décision'}
                </button>
            </div>
        </div>
    );
}

export default function ContractDetailModal({ contractId, open, onClose }) {
    const { isAdmin } = useAuth();
    const queryClient = useQueryClient();
    const [editing, setEditing] = useState(false);
    const [renewing, setRenewing] = useState(false);
    const [deleteError, setDeleteError] = useState('');

    const { data: contract, isLoading, error } = useQuery({
        queryKey: ['contract', contractId],
        queryFn: () => contractsService.getById(contractId),
        enabled: open && Boolean(contractId),
    });
    const { data: events = [] } = useQuery({
        queryKey: ['contract-events', contractId],
        queryFn: () => contractsService.getEvents(contractId),
        enabled: open && Boolean(contractId),
    });

    useEffect(() => {
        if (!open) {
            setRenewing(false);
            setDeleteError('');
        }
    }, [open]);

    const deletion = useMutation({
        mutationFn: () => contractsService.delete(contractId),
        onSuccess: () => {
            ['contracts', 'contracts-timeline', 'dashboard-summary', 'contract-suppliers'].forEach((key) =>
                queryClient.invalidateQueries({ queryKey: [key] }),
            );
            onClose();
        },
        onError: (err) => setDeleteError(apiErrorMessage(err)),
    });

    const handleDelete = () => {
        if (window.confirm(`Supprimer définitivement le contrat « ${contract.name} » ?`)) deletion.mutate();
    };

    const footer = contract && (
        <>
            {contract.sharepoint_file_url && (
                <a href={contract.sharepoint_file_url} target="_blank" rel="noopener noreferrer" className="btn-secondary mr-auto">
                    <ExternalLink className="h-4 w-4" /> Voir le document sur SharePoint
                </a>
            )}
            {isAdmin && (
                <>
                    <button type="button" className="btn-secondary text-red-600" onClick={handleDelete} disabled={deletion.isPending}>
                        <Trash2 className="h-4 w-4" /> Supprimer
                    </button>
                    {contract.renewal_decision !== 'terminate' && (
                        <button type="button" className="btn-secondary" onClick={() => setRenewing(true)}>
                            <RotateCcw className="h-4 w-4" /> Renouveler
                        </button>
                    )}
                    <button type="button" className="btn-primary" onClick={() => setEditing(true)}>
                        <Edit2 className="h-4 w-4" /> Modifier
                    </button>
                </>
            )}
        </>
    );

    return (
        <>
            <Modal open={open && !editing} onClose={onClose} size="xl" icon={FileText} title={contract?.name || 'Contrat'} footer={footer}>
                {isLoading && <LoadingBlock />}
                {error && <Alert tone="error">{apiErrorMessage(error, 'Contrat introuvable.')}</Alert>}
                {contract && (
                    <div className="space-y-6">
                        {deleteError && <Alert tone="error">{deleteError}</Alert>}
                        <div className="flex flex-wrap items-center gap-2">
                            <StatusBadge status={contract.computed_status} />
                            <DecisionBadge decision={contract.renewal_decision} />
                            {contract.auto_renewal && <span className="badge-violet">Reconduction tacite</span>}
                            <span className="badge-gray">{contract.category_label}</span>
                        </div>

                        <dl className="grid grid-cols-2 gap-x-6 gap-y-4 md:grid-cols-4">
                            <Info label="Fournisseur">{contract.supplier}</Info>
                            <Info label="Montant total">{formatCurrency(contract.amount, { precise: true })}</Info>
                            <Info label="Coût annuel">{formatCurrency(contract.annual_cost, { precise: true })}</Info>
                            <Info label="Durée">{formatMonths(contract.duration_months)}</Info>
                            <Info label="Période">{formatDate(contract.start_date)} → {formatDate(contract.end_date)}</Info>
                            <Info label="Échéance">{formatDate(contract.end_date)} <span className="text-gray-500">({formatDays(contract.days_until_end)})</span></Info>
                            <Info label="Préavis">{contract.notice_period_days} jours (à partir du {formatDate(contract.notice_start_date)})</Info>
                            <Info label="Date limite de résiliation">
                                <span className={contract.days_until_deadline >= 0 && contract.days_until_deadline <= 30 ? 'font-semibold text-red-600' : ''}>
                                    {formatDate(contract.termination_deadline)}
                                </span>{' '}
                                <span className="text-gray-500">({contract.days_until_deadline >= 0 ? formatDays(contract.days_until_deadline) : 'dépassée'})</span>
                            </Info>
                        </dl>

                        {contract.notes && (
                            <div className="rounded-lg bg-gray-50 p-4 text-sm text-gray-700 whitespace-pre-line">{contract.notes}</div>
                        )}

                        {renewing && <RenewForm contract={contract} onDone={() => setRenewing(false)} />}

                        <section>
                            <h3 className="mb-2 text-sm font-semibold text-gray-900">Décision de renouvellement</h3>
                            {contract.decision_at && (
                                <p className="mb-2 text-xs text-gray-500">
                                    Décision enregistrée par {contract.decision_by} le {formatDateTime(contract.decision_at)}
                                    {contract.decision_comment && ` : « ${contract.decision_comment} »`}
                                </p>
                            )}
                            {isAdmin ? (
                                <DecisionForm contract={contract} />
                            ) : (
                                <p className="text-sm text-gray-700"><DecisionBadge decision={contract.renewal_decision} /></p>
                            )}
                        </section>

                        <section>
                            <h3 className="mb-2 flex items-center gap-2 text-sm font-semibold text-gray-900">
                                <History className="h-4 w-4 text-gray-400" /> Historique
                            </h3>
                            {events.length === 0 ? (
                                <p className="text-sm text-gray-500">Aucune action enregistrée.</p>
                            ) : (
                                <ol className="space-y-2 border-l border-gray-200 pl-4">
                                    {events.map((event) => (
                                        <li key={event.id} className="text-sm">
                                            <span className="font-medium text-gray-900">{event.event_label}</span>
                                            <span className="text-gray-500"> · {formatDateTime(event.created_at)} · {event.username || 'automatique'}</span>
                                            {describeEvent(event) && <p className="text-gray-600">{describeEvent(event)}</p>}
                                        </li>
                                    ))}
                                </ol>
                            )}
                        </section>
                    </div>
                )}
            </Modal>

            <ContractFormModal open={editing} contract={contract} onClose={() => setEditing(false)} />
        </>
    );
}
