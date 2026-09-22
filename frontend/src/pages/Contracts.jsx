/**
 * Liste des contrats avec filtres (CDC §2.3), export Excel et impression.
 */
import { useDeferredValue, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { FileSpreadsheet, FileText, Plus, Printer, RotateCcw, Search } from 'lucide-react';
import ContractDetailModal from '../components/contracts/ContractDetailModal';
import ContractFormModal from '../components/contracts/ContractFormModal';
import { DecisionBadge, StatusBadge } from '../components/contracts/Badges';
import { Alert, EmptyState, LoadingBlock } from '../components/common/Feedback';
import contractsService from '../services/contractsService';
import { useAuth } from '../context/AuthContext';
import { apiErrorMessage } from '../lib/api';
import { CATEGORIES, STATUSES } from '../lib/constants';
import { formatCurrency, formatDate, formatDays } from '../lib/format';

const EMPTY_FILTERS = { q: '', status: '', supplier: '', category: '' };

export default function Contracts() {
    const { isAdmin } = useAuth();
    const [filters, setFilters] = useState(EMPTY_FILTERS);
    const [selectedId, setSelectedId] = useState(null);
    const [creating, setCreating] = useState(false);
    const [exportError, setExportError] = useState('');
    const deferredQ = useDeferredValue(filters.q);
    const params = useMemo(() => ({ ...filters, q: deferredQ.trim() }), [filters, deferredQ]);

    const { data: contracts = [], isLoading, error, isFetching } = useQuery({
        queryKey: ['contracts', params],
        queryFn: () => contractsService.getAll(params),
        placeholderData: (previous) => previous,
    });
    const { data: suppliers = [] } = useQuery({ queryKey: ['contract-suppliers'], queryFn: contractsService.getSuppliers });

    const totals = useMemo(() => ({
        annual: contracts.filter((c) => !c.is_expired).reduce((s, c) => s + c.annual_cost, 0),
        amount: contracts.filter((c) => !c.is_expired).reduce((s, c) => s + c.amount, 0),
    }), [contracts]);

    const set = (field) => (e) => setFilters((f) => ({ ...f, [field]: e.target.value }));
    const hasFilters = Object.values(filters).some(Boolean);

    const handleExport = async () => {
        setExportError('');
        try {
            await contractsService.exportCsv(params);
        } catch (err) {
            setExportError(apiErrorMessage(err, "L'export a échoué."));
        }
    };

    return (
        <div className="space-y-5">
            <div className="flex flex-wrap items-end justify-between gap-3">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900">Contrats</h1>
                    <p className="text-sm text-gray-500">
                        {contracts.length} contrat(s) · coût annuel des contrats en cours : {formatCurrency(totals.annual)}
                    </p>
                </div>
                <div className="no-print flex flex-wrap gap-2">
                    <button type="button" className="btn-secondary" onClick={handleExport}>
                        <FileSpreadsheet className="h-4 w-4" /> Export Excel
                    </button>
                    <button type="button" className="btn-secondary" onClick={() => window.print()}>
                        <Printer className="h-4 w-4" /> Imprimer / PDF
                    </button>
                    {isAdmin && (
                        <button type="button" className="btn-primary" onClick={() => setCreating(true)}>
                            <Plus className="h-4 w-4" /> Nouveau contrat
                        </button>
                    )}
                </div>
            </div>

            <div className="no-print card grid grid-cols-1 gap-3 p-4 md:grid-cols-5">
                <div className="relative md:col-span-2">
                    <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                    <input className="input pl-9" placeholder="Rechercher (nom, fournisseur, notes)…" value={filters.q}
                        onChange={set('q')} aria-label="Rechercher" />
                </div>
                <select className="input" value={filters.status} onChange={set('status')} aria-label="Statut">
                    <option value="">Tous les statuts</option>
                    {Object.entries(STATUSES).map(([value, s]) => <option key={value} value={value}>{s.label}</option>)}
                </select>
                <select className="input" value={filters.supplier} onChange={set('supplier')} aria-label="Fournisseur">
                    <option value="">Tous les fournisseurs</option>
                    {suppliers.map((s) => <option key={s} value={s}>{s}</option>)}
                </select>
                <div className="flex gap-2">
                    <select className="input" value={filters.category} onChange={set('category')} aria-label="Catégorie">
                        <option value="">Toutes catégories</option>
                        {CATEGORIES.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
                    </select>
                    {hasFilters && (
                        <button type="button" className="btn-ghost" onClick={() => setFilters(EMPTY_FILTERS)} title="Réinitialiser les filtres">
                            <RotateCcw className="h-4 w-4" />
                        </button>
                    )}
                </div>
            </div>

            {exportError && <Alert tone="error">{exportError}</Alert>}
            {error && <Alert tone="error">{apiErrorMessage(error, 'Contrats indisponibles.')}</Alert>}

            <div className={`card overflow-hidden ${isFetching && !isLoading ? 'opacity-70' : ''}`}>
                {isLoading ? <LoadingBlock /> : contracts.length === 0 ? (
                    <EmptyState icon={FileText} title={hasFilters ? 'Aucun contrat ne correspond aux filtres' : 'Aucun contrat enregistré'}>
                        {isAdmin && !hasFilters && 'Créez le premier contrat avec le bouton « Nouveau contrat ».'}
                    </EmptyState>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-200">
                            <thead className="bg-gray-50">
                                <tr>
                                    <th className="table-th min-w-[16rem]">Contrat</th>
                                    <th className="table-th">Catégorie</th>
                                    <th className="table-th text-right">Coût annuel</th>
                                    <th className="table-th">Échéance</th>
                                    <th className="table-th">Limite de résiliation</th>
                                    <th className="table-th">Statut</th>
                                    <th className="table-th">Décision</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-100 bg-white">
                                {contracts.map((c) => (
                                    <tr key={c.id} onClick={() => setSelectedId(c.id)} className="cursor-pointer hover:bg-gray-50">
                                        <td className="table-td">
                                            <span className="block font-medium text-gray-900">{c.name}</span>
                                            <span className="block text-xs text-gray-500">
                                                {c.supplier}{c.auto_renewal && ' · reconduction tacite'}
                                            </span>
                                        </td>
                                        <td className="table-td whitespace-nowrap">{c.category_label}</td>
                                        <td className="table-td whitespace-nowrap text-right font-medium">{formatCurrency(c.annual_cost)}</td>
                                        <td className="table-td whitespace-nowrap">
                                            {formatDate(c.end_date)}
                                            <span className="block text-xs text-gray-500">{formatDays(c.days_until_end)}</span>
                                        </td>
                                        <td className="table-td whitespace-nowrap">
                                            <span className={!c.is_expired && c.days_until_deadline >= 0 && c.days_until_deadline <= 30 ? 'font-semibold text-red-600' : ''}>
                                                {formatDate(c.termination_deadline)}
                                            </span>
                                            <span className="block text-xs text-gray-500">
                                                {c.days_until_deadline >= 0 ? formatDays(c.days_until_deadline) : 'dépassée'}
                                            </span>
                                        </td>
                                        <td className="table-td"><StatusBadge status={c.computed_status} /></td>
                                        <td className="table-td"><DecisionBadge decision={c.renewal_decision} /></td>
                                    </tr>
                                ))}
                            </tbody>
                            <tfoot className="bg-gray-50">
                                <tr>
                                    <td className="table-td font-semibold" colSpan={2}>Total des contrats en cours</td>
                                    <td className="table-td text-right font-semibold">{formatCurrency(totals.annual)}</td>
                                    <td className="table-td text-xs text-gray-500" colSpan={4}>Montant engagé : {formatCurrency(totals.amount)}</td>
                                </tr>
                            </tfoot>
                        </table>
                    </div>
                )}
            </div>

            <ContractDetailModal open={Boolean(selectedId)} contractId={selectedId} onClose={() => setSelectedId(null)} />
            <ContractFormModal open={creating} onClose={() => setCreating(false)} onSaved={(c) => setSelectedId(c.id)} />
        </div>
    );
}
