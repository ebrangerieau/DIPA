/**
 * Flux hebdomadaire : tickets créés vs clos sur 12 semaines.
 * Des créations durablement supérieures aux clôtures signalent un backlog qui grossit.
 */
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { formatDate } from '../../lib/format';
import { EmptyState } from '../common/Feedback';

export default function TicketFlowChart({ weeks = [] }) {
    if (!weeks.length) return <EmptyState title="Aucune donnée sur la période" />;

    const created = weeks.reduce((s, w) => s + w.created, 0);
    const closed = weeks.reduce((s, w) => s + w.closed, 0);

    return (
        <div>
            <p className="mb-4 text-sm text-gray-600">
                12 dernières semaines : <span className="font-semibold text-gray-900">{created}</span> créés,{' '}
                <span className="font-semibold text-gray-900">{closed}</span> clos
                {created > closed
                    ? <span className="ml-1 text-amber-700">(le stock augmente de {created - closed})</span>
                    : <span className="ml-1 text-emerald-700">(le stock se résorbe)</span>}
            </p>
            <ResponsiveContainer width="100%" height={280}>
                <BarChart data={weeks} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" vertical={false} />
                    <XAxis dataKey="label" stroke="#9ca3af" tick={{ fontSize: 12 }} />
                    <YAxis stroke="#9ca3af" tick={{ fontSize: 12 }} allowDecimals={false} />
                    <Tooltip
                        cursor={{ fill: '#f3f4f6' }}
                        contentStyle={{ borderRadius: 8, border: '1px solid #e5e7eb', fontSize: 13 }}
                        labelFormatter={(label, payload) => payload?.[0] ? `Semaine du ${formatDate(payload[0].payload.week_start)}` : label}
                    />
                    <Legend wrapperStyle={{ fontSize: 13 }} />
                    <Bar dataKey="created" name="Créés" fill="#38bdf8" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="closed" name="Clos" fill="#10b981" radius={[4, 4, 0, 0]} />
                </BarChart>
            </ResponsiveContainer>
        </div>
    );
}
