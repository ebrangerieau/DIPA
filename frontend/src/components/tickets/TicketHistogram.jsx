/**
 * Histogramme des tickets clos par jour (CDC §2.2) : hors tickets #Projet,
 * périodes de 7, 30 ou 90 jours, total affiché sous le graphique.
 */
import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { eachDayOfInterval, format, subDays } from 'date-fns';
import { fr } from 'date-fns/locale';
import ticketsService from '../../services/ticketsService';
import { apiErrorMessage } from '../../lib/api';
import { formatNumber } from '../../lib/format';
import { Alert, LoadingBlock } from '../common/Feedback';

const PERIODS = [7, 30, 90];

export default function TicketHistogram() {
    const [period, setPeriod] = useState(30);
    const range = useMemo(() => {
        const end = new Date();
        return { start: subDays(end, period - 1), end };
    }, [period]);

    const { data: stats = [], isLoading, error } = useQuery({
        queryKey: ['tickets-stats', period],
        queryFn: () => ticketsService.getStats({
            start_date: format(range.start, 'yyyy-MM-dd'),
            end_date: format(range.end, 'yyyy-MM-dd'),
            exclude_projects: true,
        }),
    });

    // Jours sans ticket inclus : l'axe des dates reste continu
    const chartData = useMemo(() => {
        const counts = new Map(stats.map((s) => [s.date, s.count]));
        return eachDayOfInterval(range).map((day) => {
            const key = format(day, 'yyyy-MM-dd');
            return { key, label: format(day, 'dd/MM'), count: counts.get(key) || 0, day };
        });
    }, [stats, range]);

    const total = stats.reduce((sum, s) => sum + s.count, 0);
    const workingDays = chartData.filter((d) => d.day.getDay() !== 0 && d.day.getDay() !== 6).length || 1;

    return (
        <div>
            <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
                <p className="text-sm text-gray-600">Tickets clos par jour (hors projets)</p>
                <div className="no-print flex gap-1 rounded-lg bg-gray-100 p-1">
                    {PERIODS.map((p) => (
                        <button key={p} type="button" onClick={() => setPeriod(p)}
                            className={`rounded-md px-3 py-1 text-sm transition-colors ${period === p ? 'bg-white font-medium text-gray-900 shadow-sm' : 'text-gray-600 hover:text-gray-900'}`}>
                            {p} jours
                        </button>
                    ))}
                </div>
            </div>

            {error && <Alert tone="warning">{apiErrorMessage(error, 'Statistiques Zammad indisponibles.')}</Alert>}
            {isLoading ? <LoadingBlock height="h-72" /> : !error && (
                <>
                    <ResponsiveContainer width="100%" height={280}>
                        <BarChart data={chartData} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" vertical={false} />
                            <XAxis dataKey="label" stroke="#9ca3af" tick={{ fontSize: 12 }} interval="preserveStartEnd" minTickGap={16} />
                            <YAxis stroke="#9ca3af" tick={{ fontSize: 12 }} allowDecimals={false} />
                            <Tooltip
                                cursor={{ fill: '#f3f4f6' }}
                                contentStyle={{ borderRadius: 8, border: '1px solid #e5e7eb', fontSize: 13 }}
                                labelFormatter={(_, payload) => payload?.[0] ? format(payload[0].payload.day, 'EEEE d MMMM yyyy', { locale: fr }) : ''}
                                formatter={(value) => [value, 'Tickets clos']}
                            />
                            <Bar dataKey="count" fill="#0ea5e9" radius={[4, 4, 0, 0]} name="Tickets clos" />
                        </BarChart>
                    </ResponsiveContainer>
                    <p className="mt-3 text-sm text-gray-600">
                        Total sur la période : <span className="font-semibold text-gray-900">{formatNumber(total)}</span> ticket(s) clos
                        · moyenne <span className="font-semibold text-gray-900">{(total / workingDays).toLocaleString('fr-FR', { maximumFractionDigits: 1 })}</span> par jour ouvré
                    </p>
                </>
            )}
        </div>
    );
}
