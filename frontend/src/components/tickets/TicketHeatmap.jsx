/**
 * Calendrier annuel de l'activité support (tickets clos par jour ouvré), façon GitHub.
 * Rendu SVG maison : jours ouvrés uniquement (lundi → vendredi), semaines en colonnes.
 */
import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { addDays, addWeeks, format, isAfter, startOfWeek } from 'date-fns';
import { fr } from 'date-fns/locale';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import ticketsService from '../../services/ticketsService';
import { apiErrorMessage } from '../../lib/api';
import { formatNumber } from '../../lib/format';
import { Alert, LoadingBlock } from '../common/Feedback';

const COLORS = ['#ebedf0', '#9be9a8', '#40c463', '#30a14e', '#216e39'];
const CELL = 13;
const GAP = 3;
const LEFT = 26;
const TOP = 18;
const WEEKDAYS = ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven'];
const YEARS_BACK = 3;

const capitalize = (text) => text.charAt(0).toUpperCase() + text.slice(1);

export default function TicketHeatmap() {
    const today = useMemo(() => new Date(), []);
    const currentYear = today.getFullYear();
    const [year, setYear] = useState(currentYear);

    const startDate = `${year}-01-01`;
    const endDate = year === currentYear ? format(today, 'yyyy-MM-dd') : `${year}-12-31`;

    const { data: stats = [], isLoading, error } = useQuery({
        queryKey: ['tickets-heatmap', year],
        queryFn: () => ticketsService.getStats({ start_date: startDate, end_date: endDate, exclude_projects: true }),
    });

    const { weeks, months, counts, thresholds, total, busiest } = useMemo(() => {
        const countMap = new Map(stats.map((s) => [s.date, s.count]));
        const first = startOfWeek(new Date(year, 0, 1), { weekStartsOn: 1 });
        const last = new Date(year, 11, 31);
        const weekList = [];
        for (let w = first; w <= last; w = addWeeks(w, 1)) weekList.push(w);

        const monthLabels = [];
        weekList.forEach((week, index) => {
            for (let d = 0; d < 7; d += 1) {
                const day = addDays(week, d);
                if (day.getFullYear() === year && day.getDate() === 1) {
                    monthLabels.push({ index, label: capitalize(format(day, 'MMM', { locale: fr })) });
                }
            }
        });

        // Paliers par quantiles : un pic isolé (rentrée) n'écrase pas le reste de l'échelle
        const sorted = stats.map((s) => s.count).filter((c) => c > 0).sort((a, b) => a - b);
        const quantile = (q) => (sorted.length ? sorted[Math.min(sorted.length - 1, Math.floor(q * sorted.length))] : 0);
        const top = stats.reduce((best, s) => (!best || s.count > best.count ? s : best), null);
        return {
            weeks: weekList,
            months: monthLabels,
            counts: countMap,
            thresholds: [quantile(0.25), quantile(0.5), quantile(0.75)],
            total: stats.reduce((sum, s) => sum + s.count, 0),
            busiest: top,
        };
    }, [stats, year]);

    const width = LEFT + weeks.length * (CELL + GAP);
    const height = TOP + WEEKDAYS.length * (CELL + GAP);
    const level = (count) => {
        if (count <= 0) return 0;
        const [q1, q2, q3] = thresholds;
        if (count <= q1) return 1;
        if (count <= q2) return 2;
        if (count <= q3) return 3;
        return 4;
    };

    return (
        <div>
            <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
                <p className="text-sm text-gray-600">
                    <span className="font-semibold text-gray-900">{formatNumber(total)}</span> tickets clos en {year}
                    {busiest && (
                        <> · record : <span className="font-semibold text-gray-900">{busiest.count}</span> le {format(new Date(`${busiest.date}T00:00:00`), 'd MMMM', { locale: fr })}</>
                    )}
                </p>
                <div className="no-print flex items-center gap-1 rounded-lg bg-gray-100 p-1">
                    <button type="button" className="btn-ghost px-2 py-1" onClick={() => setYear(year - 1)}
                        disabled={year <= currentYear - YEARS_BACK} aria-label="Année précédente">
                        <ChevronLeft className="h-4 w-4" />
                    </button>
                    <span className="px-2 text-sm font-medium text-gray-900">{year}</span>
                    <button type="button" className="btn-ghost px-2 py-1" onClick={() => setYear(year + 1)}
                        disabled={year >= currentYear} aria-label="Année suivante">
                        <ChevronRight className="h-4 w-4" />
                    </button>
                </div>
            </div>

            {error && <Alert tone="warning">{apiErrorMessage(error, 'Statistiques Zammad indisponibles.')}</Alert>}
            {isLoading ? <LoadingBlock height="h-40" /> : !error && (
                <div className="overflow-x-auto">
                    <svg width={width} height={height} role="img" aria-label={`Activité support ${year}`} className="block">
                        {months.map((m) => (
                            <text key={`${m.index}-${m.label}`} x={LEFT + m.index * (CELL + GAP)} y={11} fontSize={10} fill="#6b7280">
                                {m.label}
                            </text>
                        ))}
                        {WEEKDAYS.map((d, i) => (
                            <text key={d} x={0} y={TOP + i * (CELL + GAP) + CELL - 2} fontSize={9} fill="#9ca3af">{d}</text>
                        ))}
                        {weeks.map((week, wi) =>
                            WEEKDAYS.map((_, di) => {
                                const day = addDays(week, di);
                                if (day.getFullYear() !== year) return null;
                                const key = format(day, 'yyyy-MM-dd');
                                const count = counts.get(key) || 0;
                                const future = isAfter(day, today);
                                return (
                                    <rect key={key} x={LEFT + wi * (CELL + GAP)} y={TOP + di * (CELL + GAP)} width={CELL} height={CELL} rx={2}
                                        fill={future ? '#f9fafb' : COLORS[level(count)]} stroke={future ? '#f3f4f6' : 'none'}>
                                        <title>{`${count} ticket${count > 1 ? 's' : ''} clos le ${format(day, 'EEEE d MMMM yyyy', { locale: fr })}`}</title>
                                    </rect>
                                );
                            }),
                        )}
                    </svg>
                </div>
            )}

            <div className="mt-3 flex items-center justify-end gap-1.5 text-xs text-gray-500">
                <span>Moins</span>
                {COLORS.map((c) => <span key={c} className="h-3 w-3 rounded-sm" style={{ backgroundColor: c }} />)}
                <span>Plus</span>
            </div>
        </div>
    );
}
