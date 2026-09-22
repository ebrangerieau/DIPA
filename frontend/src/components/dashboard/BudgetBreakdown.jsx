/**
 * Répartition du budget annuel des contrats en cours, par catégorie et par fournisseur.
 */
import { EmptyState } from '../common/Feedback';
import { formatCurrency } from '../../lib/format';

function Bars({ rows, labelKey }) {
    const max = Math.max(...rows.map((r) => r.annual_cost), 1);
    return (
        <ul className="space-y-2.5">
            {rows.map((r) => (
                <li key={r[labelKey]}>
                    <div className="mb-1 flex justify-between gap-2 text-sm">
                        <span className="truncate text-gray-700">{r[labelKey]} <span className="text-gray-400">({r.count})</span></span>
                        <span className="whitespace-nowrap font-medium text-gray-900">{formatCurrency(r.annual_cost)}</span>
                    </div>
                    <div className="h-2 overflow-hidden rounded-full bg-gray-100">
                        <div className="h-full rounded-full bg-emerald-500" style={{ width: `${(r.annual_cost / max) * 100}%` }} />
                    </div>
                </li>
            ))}
        </ul>
    );
}

export default function BudgetBreakdown({ byCategory = [], topSuppliers = [] }) {
    if (!byCategory.length) return <EmptyState title="Aucun contrat en cours" />;
    return (
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
            <div>
                <h4 className="mb-3 text-xs font-semibold uppercase tracking-wide text-gray-500">Par catégorie</h4>
                <Bars rows={byCategory} labelKey="label" />
            </div>
            <div>
                <h4 className="mb-3 text-xs font-semibold uppercase tracking-wide text-gray-500">Principaux fournisseurs</h4>
                <Bars rows={topSuppliers} labelKey="supplier" />
            </div>
        </div>
    );
}
