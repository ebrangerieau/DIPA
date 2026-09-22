/**
 * Échéances à traiter : dates limites de résiliation proches et préavis en cours,
 * triées par date, avec la décision de renouvellement associée.
 */
import { CalendarClock } from 'lucide-react';
import { DecisionBadge, UrgencyDot } from '../contracts/Badges';
import { EmptyState } from '../common/Feedback';
import { formatCurrency, formatDate, formatDays } from '../../lib/format';

export default function UpcomingDeadlines({ actions = [], horizonDays, onSelect }) {
    if (!actions.length) {
        return (
            <EmptyState icon={CalendarClock} title="Aucune échéance à traiter">
                Aucun contrat n&apos;arrive à sa date limite de résiliation dans les {horizonDays} prochains jours.
            </EmptyState>
        );
    }

    return (
        <ul className="divide-y divide-gray-100">
            {actions.map((a) => (
                <li key={a.contract_id}>
                    <button type="button" onClick={() => onSelect?.(a.contract_id)}
                        className="flex w-full items-start gap-3 px-4 py-3 text-left transition-colors hover:bg-gray-50">
                        <span className="pt-1.5"><UrgencyDot urgency={a.urgency} /></span>
                        <span className="min-w-0 flex-1">
                            <span className="flex flex-wrap items-center gap-2">
                                <span className="truncate font-medium text-gray-900">{a.name}</span>
                                <DecisionBadge decision={a.decision} />
                                {a.auto_renewal && <span className="badge-violet">Tacite</span>}
                            </span>
                            <span className="block text-sm text-gray-600">{a.message}</span>
                            <span className="block text-xs text-gray-500">{a.supplier} · {formatCurrency(a.annual_cost)} / an</span>
                        </span>
                        <span className="whitespace-nowrap text-right">
                            <span className="block text-sm font-medium text-gray-900">{formatDate(a.key_date)}</span>
                            <span className={`block text-xs ${a.days <= 7 ? 'font-semibold text-red-600' : 'text-gray-500'}`}>{formatDays(a.days)}</span>
                        </span>
                    </button>
                </li>
            ))}
        </ul>
    );
}
