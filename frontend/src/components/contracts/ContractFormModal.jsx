/**
 * Formulaire de création / modification d'un contrat.
 * La date de fin est proposée à partir de la date de début et de la durée
 * (du 01/09/2026 au 31/08/2027 pour 12 mois) mais reste modifiable.
 */
import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { addMonths, differenceInCalendarDays, format, subDays } from 'date-fns';
import { Building, Calendar, Euro, FileText, Link as LinkIcon, RefreshCw } from 'lucide-react';
import Modal from '../common/Modal';
import { Alert } from '../common/Feedback';
import contractsService from '../../services/contractsService';
import { apiErrorMessage } from '../../lib/api';
import { CATEGORIES } from '../../lib/constants';
import { formatCurrency, formatDate, toDate } from '../../lib/format';

const EMPTY_FORM = {
    name: '',
    supplier: '',
    category: 'autre',
    amount: '',
    duration_months: 12,
    start_date: '',
    end_date: '',
    notice_period_days: 90,
    auto_renewal: false,
    sharepoint_file_url: '',
    notes: '',
};

function suggestedEndDate(start, months) {
    const startDate = toDate(start);
    const n = parseInt(months, 10);
    if (!startDate || !n || n < 1) return '';
    return format(subDays(addMonths(startDate, n), 1), 'yyyy-MM-dd');
}

function Field({ label, htmlFor, required, hint, children, className = '' }) {
    return (
        <div className={className}>
            <label className="label" htmlFor={htmlFor}>
                {label} {required && <span className="text-red-500">*</span>}
            </label>
            {children}
            {hint && <p className="mt-1 text-xs text-gray-500">{hint}</p>}
        </div>
    );
}

function IconInput({ icon: Icon, ...props }) {
    return (
        <div className="relative">
            <Icon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
            <input {...props} className="input pl-9" />
        </div>
    );
}

export default function ContractFormModal({ open, onClose, contract = null, onSaved }) {
    const isEdit = Boolean(contract);
    const queryClient = useQueryClient();
    const [form, setForm] = useState(EMPTY_FORM);
    const [endTouched, setEndTouched] = useState(false);
    const [error, setError] = useState('');

    const { data: suppliers = [] } = useQuery({
        queryKey: ['contract-suppliers'],
        queryFn: contractsService.getSuppliers,
        enabled: open,
    });

    // Initialisation à l'ouverture
    useEffect(() => {
        if (!open) return;
        setError('');
        if (contract) {
            setForm({
                ...EMPTY_FORM,
                ...Object.fromEntries(Object.keys(EMPTY_FORM).map((k) => [k, contract[k] ?? EMPTY_FORM[k]])),
            });
            setEndTouched(true); // En modification, l'échéance enregistrée est conservée
        } else {
            setForm(EMPTY_FORM);
            setEndTouched(false);
        }
    }, [open, contract]);

    // Proposition automatique de la date de fin tant qu'elle n'a pas été saisie à la main
    useEffect(() => {
        if (endTouched) return;
        const suggestion = suggestedEndDate(form.start_date, form.duration_months);
        if (suggestion && suggestion !== form.end_date) {
            setForm((f) => ({ ...f, end_date: suggestion }));
        }
    }, [form.start_date, form.duration_months, form.end_date, endTouched]);

    const set = (field) => (e) => {
        const value = e.target.type === 'checkbox' ? e.target.checked : e.target.value;
        if (field === 'end_date') setEndTouched(true);
        setForm((f) => ({ ...f, [field]: value }));
    };

    const recomputeEnd = () => {
        setEndTouched(false);
        setForm((f) => ({ ...f, end_date: suggestedEndDate(f.start_date, f.duration_months) }));
    };

    const preview = useMemo(() => {
        const amount = parseFloat(form.amount);
        const months = parseInt(form.duration_months, 10);
        const end = toDate(form.end_date);
        const notice = parseInt(form.notice_period_days, 10);
        const deadline = end && notice >= 0 ? subDays(end, notice) : null;
        return {
            annual: amount >= 0 && months > 0 ? amount / (months / 12) : null,
            deadline,
            deadlineDays: deadline ? differenceInCalendarDays(deadline, new Date()) : null,
        };
    }, [form.amount, form.duration_months, form.end_date, form.notice_period_days]);

    const mutation = useMutation({
        mutationFn: (payload) => (isEdit ? contractsService.update(contract.id, payload) : contractsService.create(payload)),
        onSuccess: (saved) => {
            ['contracts', 'contracts-timeline', 'dashboard-summary', 'contract-suppliers'].forEach((key) =>
                queryClient.invalidateQueries({ queryKey: [key] }),
            );
            queryClient.invalidateQueries({ queryKey: ['contract', saved.id] });
            queryClient.invalidateQueries({ queryKey: ['contract-events', saved.id] });
            onSaved?.(saved);
            onClose();
        },
        onError: (err) => setError(apiErrorMessage(err, "Le contrat n'a pas pu être enregistré.")),
    });

    const handleSubmit = (e) => {
        e.preventDefault();
        setError('');
        if (form.end_date && form.start_date && form.end_date <= form.start_date) {
            setError('La date de fin doit être postérieure à la date de début.');
            return;
        }
        mutation.mutate({
            ...form,
            name: form.name.trim(),
            supplier: form.supplier.trim(),
            amount: parseFloat(form.amount),
            duration_months: parseInt(form.duration_months, 10),
            notice_period_days: parseInt(form.notice_period_days, 10),
            sharepoint_file_url: form.sharepoint_file_url.trim() || null,
            notes: form.notes.trim() || null,
        });
    };

    return (
        <Modal
            open={open}
            onClose={onClose}
            size="lg"
            icon={FileText}
            title={isEdit ? 'Modifier le contrat' : 'Nouveau contrat'}
            footer={
                <>
                    <button type="button" className="btn-secondary" onClick={onClose} disabled={mutation.isPending}>
                        Annuler
                    </button>
                    <button type="submit" form="contract-form" className="btn-primary" disabled={mutation.isPending}>
                        {mutation.isPending ? 'Enregistrement…' : isEdit ? 'Enregistrer' : 'Créer le contrat'}
                    </button>
                </>
            }
        >
            <form id="contract-form" onSubmit={handleSubmit} className="space-y-5">
                {error && <Alert tone="error">{error}</Alert>}

                <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                    <Field label="Nom du contrat" htmlFor="c-name" required className="md:col-span-2">
                        <IconInput icon={FileText} id="c-name" required maxLength={255} value={form.name}
                            onChange={set('name')} placeholder="Ex. : Maintenance des copieurs" />
                    </Field>

                    <Field label="Fournisseur" htmlFor="c-supplier" required>
                        <IconInput icon={Building} id="c-supplier" required maxLength={255} list="c-supplier-list"
                            value={form.supplier} onChange={set('supplier')} placeholder="Ex. : Microsoft" />
                        <datalist id="c-supplier-list">
                            {suppliers.map((s) => <option key={s} value={s} />)}
                        </datalist>
                    </Field>

                    <Field label="Catégorie" htmlFor="c-category">
                        <select id="c-category" className="input" value={form.category} onChange={set('category')}>
                            {CATEGORIES.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
                        </select>
                    </Field>

                    <Field label="Montant total (€)" htmlFor="c-amount" required hint="Montant sur toute la durée du contrat">
                        <IconInput icon={Euro} id="c-amount" type="number" required min="0" step="0.01"
                            value={form.amount} onChange={set('amount')} placeholder="0,00" />
                    </Field>

                    <Field label="Durée (mois)" htmlFor="c-duration" required
                        hint={form.duration_months ? `${(form.duration_months / 12).toLocaleString('fr-FR', { maximumFractionDigits: 1 })} an(s)` : ''}>
                        <input id="c-duration" type="number" className="input" required min="1" max="240"
                            value={form.duration_months} onChange={set('duration_months')} />
                    </Field>

                    <Field label="Date de début" htmlFor="c-start" required>
                        <IconInput icon={Calendar} id="c-start" type="date" required value={form.start_date} onChange={set('start_date')} />
                    </Field>

                    <Field label="Date de fin (échéance)" htmlFor="c-end" required
                        hint={endTouched ? 'Saisie manuelle' : 'Proposée : début + durée − 1 jour'}>
                        <div className="flex gap-2">
                            <div className="flex-1">
                                <IconInput icon={Calendar} id="c-end" type="date" required value={form.end_date} onChange={set('end_date')} />
                            </div>
                            <button type="button" className="btn-secondary px-3" onClick={recomputeEnd}
                                title="Recalculer à partir de la durée" disabled={!form.start_date}>
                                <RefreshCw className="h-4 w-4" />
                            </button>
                        </div>
                    </Field>

                    <Field label="Préavis (jours)" htmlFor="c-notice" required hint="Délai pour dénoncer le contrat avant l'échéance">
                        <input id="c-notice" type="number" className="input" required min="0" max="3650"
                            value={form.notice_period_days} onChange={set('notice_period_days')} />
                    </Field>

                    <div className="flex items-center md:pt-6">
                        <label className="flex cursor-pointer items-start gap-3 text-sm text-gray-700">
                            <input type="checkbox" className="mt-0.5 h-4 w-4 rounded border-gray-300 text-primary-600"
                                checked={form.auto_renewal} onChange={set('auto_renewal')} />
                            <span>
                                <span className="font-medium">Reconduction tacite</span>
                                <span className="block text-xs text-gray-500">Prolongé automatiquement à l&apos;échéance s&apos;il n&apos;est pas résilié</span>
                            </span>
                        </label>
                    </div>

                    <Field label="Lien vers le document (SharePoint)" htmlFor="c-url" className="md:col-span-2">
                        <IconInput icon={LinkIcon} id="c-url" type="url" maxLength={2000} value={form.sharepoint_file_url}
                            onChange={set('sharepoint_file_url')} placeholder="https://…sharepoint.com/…/contrat.pdf" />
                    </Field>

                    <Field label="Notes" htmlFor="c-notes" className="md:col-span-2" hint="N° de contrat, contact fournisseur, conditions particulières…">
                        <textarea id="c-notes" rows={3} maxLength={5000} className="input" value={form.notes} onChange={set('notes')} />
                    </Field>
                </div>

                <div className="grid grid-cols-1 gap-3 rounded-lg border border-primary-100 bg-primary-50 p-4 sm:grid-cols-2">
                    <div>
                        <p className="text-xs font-medium uppercase tracking-wide text-primary-700">Coût annuel moyen</p>
                        <p className="text-lg font-semibold text-primary-900">
                            {preview.annual !== null ? `${formatCurrency(preview.annual, { precise: true })} / an` : '—'}
                        </p>
                    </div>
                    <div>
                        <p className="text-xs font-medium uppercase tracking-wide text-primary-700">Date limite de résiliation</p>
                        <p className="text-lg font-semibold text-primary-900">
                            {preview.deadline ? formatDate(preview.deadline) : '—'}
                            {preview.deadlineDays !== null && (
                                <span className="ml-2 text-sm font-normal text-primary-700">
                                    ({preview.deadlineDays >= 0 ? `dans ${preview.deadlineDays} j` : 'dépassée'})
                                </span>
                            )}
                        </p>
                    </div>
                </div>
            </form>
        </Modal>
    );
}
