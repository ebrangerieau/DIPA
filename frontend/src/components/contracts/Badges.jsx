/**
 * Badges de statut, de décision et d'urgence.
 */
import { DECISIONS, STATUSES, URGENCIES } from '../../lib/constants';

export function StatusBadge({ status }) {
    const s = STATUSES[status] || STATUSES.active;
    return <span className={s.badge}>{s.label}</span>;
}

export function DecisionBadge({ decision }) {
    const d = DECISIONS[decision] || DECISIONS.pending;
    return <span className={d.badge}>{d.label}</span>;
}

export function UrgencyDot({ urgency }) {
    const u = URGENCIES[urgency] || URGENCIES.medium;
    return <span className={`inline-block h-2.5 w-2.5 flex-shrink-0 rounded-full ${u.dot}`} title={u.label} />;
}
