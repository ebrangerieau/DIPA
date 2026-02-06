/**
 * Composant d'histogramme pour les tickets clos.
 * Affiche le volume des tickets quotidiens (sans tag #Projet).
 */
import { useQuery } from '@tanstack/react-query';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { useState } from 'react';
import { format, subDays } from 'date-fns';
import { fr } from 'date-fns/locale';
import ticketsService from '../services/ticketsService';

export default function TicketHistogram() {
    const [period, setPeriod] = useState(30); // Jours

    const { data: stats = [], isLoading } = useQuery({
        queryKey: ['tickets-stats', period],
        queryFn: () => {
            const endDate = new Date();
            const startDate = subDays(endDate, period);
            return ticketsService.getStats({
                start_date: format(startDate, 'yyyy-MM-dd'),
                end_date: format(endDate, 'yyyy-MM-dd'),
                exclude_projects: true,
            });
        },
    });

    // Formater les données pour Recharts
    const chartData = stats.map(stat => ({
        date: format(new Date(stat.date), 'dd/MM', { locale: fr }),
        fullDate: stat.date,
        count: stat.count,
    }));

    if (isLoading) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
            </div>
        );
    }

    return (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <div className="flex justify-between items-center mb-6">
                <h2 className="text-lg font-semibold text-gray-900">
                    Volume de Tickets Clos (Quotidiens)
                </h2>

                <div className="flex gap-2">
                    <button
                        onClick={() => setPeriod(7)}
                        className={`px-3 py-1 text-sm rounded-md transition-colors ${period === 7
                                ? 'bg-primary-600 text-white'
                                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                            }`}
                    >
                        7 jours
                    </button>
                    <button
                        onClick={() => setPeriod(30)}
                        className={`px-3 py-1 text-sm rounded-md transition-colors ${period === 30
                                ? 'bg-primary-600 text-white'
                                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                            }`}
                    >
                        30 jours
                    </button>
                    <button
                        onClick={() => setPeriod(90)}
                        className={`px-3 py-1 text-sm rounded-md transition-colors ${period === 90
                                ? 'bg-primary-600 text-white'
                                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                            }`}
                    >
                        90 jours
                    </button>
                </div>
            </div>

            <ResponsiveContainer width="100%" height={300}>
                <BarChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis
                        dataKey="date"
                        stroke="#6b7280"
                        style={{ fontSize: '0.75rem' }}
                    />
                    <YAxis
                        stroke="#6b7280"
                        style={{ fontSize: '0.75rem' }}
                    />
                    <Tooltip
                        contentStyle={{
                            backgroundColor: '#fff',
                            border: '1px solid #e5e7eb',
                            borderRadius: '0.375rem',
                            fontSize: '0.875rem',
                        }}
                        labelFormatter={(label, payload) => {
                            if (payload && payload[0]) {
                                return format(new Date(payload[0].payload.fullDate), 'dd MMMM yyyy', { locale: fr });
                            }
                            return label;
                        }}
                    />
                    <Bar
                        dataKey="count"
                        fill="#0ea5e9"
                        radius={[4, 4, 0, 0]}
                        name="Tickets clos"
                    />
                </BarChart>
            </ResponsiveContainer>

            <div className="mt-4 text-sm text-gray-600">
                <p>
                    Total de tickets clos sur la période : <span className="font-semibold text-gray-900">
                        {stats.reduce((sum, stat) => sum + stat.count, 0)}
                    </span>
                </p>
            </div>
        </div>
    );
}
