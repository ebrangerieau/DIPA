/**
 * Suivi du support : tickets ouverts par technicien et tickets ouverts les plus anciens.
 */
import { ExternalLink, UserX } from 'lucide-react';
import { EmptyState } from '../common/Feedback';
import { stateLabel } from '../../lib/constants';

export function WorkloadBars({ byOwner = [] }) {
    if (!byOwner.length) return <EmptyState title="Aucun ticket ouvert" />;
    const max = Math.max(...byOwner.map((o) => o.count));
    return (
        <ul className="space-y-3">
            {byOwner.map((o) => (
                <li key={o.owner}>
                    <div className="mb-1 flex justify-between text-sm">
                        <span className={`flex items-center gap-1 ${o.owner === 'Non assigné' ? 'font-medium text-amber-700' : 'text-gray-700'}`}>
                            {o.owner === 'Non assigné' && <UserX className="h-3.5 w-3.5" />}
                            {o.owner}
                        </span>
                        <span className="font-semibold text-gray-900">{o.count}</span>
                    </div>
                    <div className="h-2 overflow-hidden rounded-full bg-gray-100">
                        <div
                            className={`h-full rounded-full ${o.owner === 'Non assigné' ? 'bg-amber-400' : 'bg-primary-500'}`}
                            style={{ width: `${(o.count / max) * 100}%` }}
                        />
                    </div>
                </li>
            ))}
        </ul>
    );
}

export function OldestTickets({ tickets = [] }) {
    if (!tickets.length) return <EmptyState title="Aucun ticket ouvert" />;
    return (
        <ul className="divide-y divide-gray-100">
            {tickets.map((t) => (
                <li key={t.id} className="flex items-start gap-3 py-2.5">
                    <span className={`mt-0.5 whitespace-nowrap rounded-md px-1.5 py-0.5 text-xs font-semibold ${t.age_days > 30 ? 'bg-red-50 text-red-700' : 'bg-gray-100 text-gray-600'}`}>
                        {t.age_days} j
                    </span>
                    <span className="min-w-0 flex-1">
                        <span className="block truncate text-sm text-gray-900" title={t.title}>{t.title}</span>
                        <span className="block text-xs text-gray-500">
                            #{t.number} · {stateLabel(t.state)} · {t.owner || 'non assigné'}
                        </span>
                    </span>
                    {t.url && (
                        <a href={t.url} target="_blank" rel="noopener noreferrer" className="btn-ghost p-1" title="Ouvrir dans Zammad">
                            <ExternalLink className="h-4 w-4" />
                        </a>
                    )}
                </li>
            ))}
        </ul>
    );
}
