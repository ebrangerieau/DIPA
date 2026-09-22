/**
 * Journal des dernières actions sur les contrats (tous contrats, y compris supprimés).
 */
import { useQuery } from '@tanstack/react-query';
import { History } from 'lucide-react';
import { Alert, EmptyState, LoadingBlock } from '../common/Feedback';
import systemService from '../../services/systemService';
import { apiErrorMessage } from '../../lib/api';
import { formatDateTime } from '../../lib/format';

export default function AuditLog() {
    const { data: events = [], isLoading, error } = useQuery({ queryKey: ['system-events'], queryFn: () => systemService.getEvents(150) });

    if (isLoading) return <LoadingBlock />;
    if (error) return <Alert tone="error">{apiErrorMessage(error)}</Alert>;
    if (!events.length) return <EmptyState icon={History} title="Aucune action enregistrée" />;

    return (
        <div className="card overflow-hidden">
            <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                        <tr>
                            <th className="table-th">Date</th>
                            <th className="table-th">Action</th>
                            <th className="table-th">Contrat</th>
                            <th className="table-th">Par</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                        {events.map((e) => (
                            <tr key={e.id}>
                                <td className="table-td whitespace-nowrap text-xs text-gray-500">{formatDateTime(e.created_at)}</td>
                                <td className="table-td">{e.event_label}</td>
                                <td className="table-td">
                                    {e.contract_name}
                                    {!e.contract_id && <span className="ml-2 text-xs text-gray-400">(supprimé)</span>}
                                </td>
                                <td className="table-td text-gray-500">{e.username || 'Automatique'}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
