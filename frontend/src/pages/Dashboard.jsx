/**
 * Tableau de bord : indicateurs clés, échéances à traiter, Smart Timeline,
 * activité du support et budget des contrats.
 */
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { format } from 'date-fns';
import { fr } from 'date-fns/locale';
import {
    AlertTriangle, CalendarClock, CheckCircle2, Clock, FileText, FolderKanban, Inbox, Plus, Printer, Wallet,
} from 'lucide-react';
import KpiCard from '../components/dashboard/KpiCard';
import UpcomingDeadlines from '../components/dashboard/UpcomingDeadlines';
import { OldestTickets, WorkloadBars } from '../components/dashboard/SupportPanel';
import BudgetBreakdown from '../components/dashboard/BudgetBreakdown';
import SmartTimeline from '../components/timeline/SmartTimeline';
import TicketHistogram from '../components/tickets/TicketHistogram';
import TicketHeatmap from '../components/tickets/TicketHeatmap';
import TicketFlowChart from '../components/tickets/TicketFlowChart';
import TicketDetailModal from '../components/tickets/TicketDetailModal';
import ContractDetailModal from '../components/contracts/ContractDetailModal';
import ContractFormModal from '../components/contracts/ContractFormModal';
import { Alert, LoadingBlock } from '../components/common/Feedback';
import dashboardService from '../services/dashboardService';
import { useAuth } from '../context/AuthContext';
import { apiErrorMessage } from '../lib/api';
import { formatCurrency, formatHours, formatNumber } from '../lib/format';

const HORIZON_DAYS = 90;
const ACTIVITY_TABS = [
    { id: 'histogram', label: 'Histogramme' },
    { id: 'heatmap', label: 'Calendrier annuel' },
    { id: 'flow', label: 'Créés / clos' },
];

function Section({ title, icon: Icon, actions, children, className = '', bodyClassName = 'p-4' }) {
    return (
        <section className={`card ${className}`}>
            <div className="flex items-center justify-between gap-2 border-b border-gray-100 px-4 py-3">
                <h2 className="flex items-center gap-2 text-base font-semibold text-gray-900">
                    {Icon && <Icon className="h-4 w-4 text-primary-600" />} {title}
                </h2>
                {actions}
            </div>
            <div className={bodyClassName}>{children}</div>
        </section>
    );
}

export default function Dashboard() {
    const { isAdmin } = useAuth();
    const [contractId, setContractId] = useState(null);
    const [ticketItem, setTicketItem] = useState(null);
    const [creating, setCreating] = useState(false);
    const [activityTab, setActivityTab] = useState('histogram');

    const { data: summary, isLoading, error } = useQuery({
        queryKey: ['dashboard-summary', HORIZON_DAYS],
        queryFn: () => dashboardService.getSummary(HORIZON_DAYS),
    });

    const contracts = summary?.contracts;
    const tickets = summary?.tickets;
    const running = contracts ? contracts.active + contracts.in_notice : 0;

    return (
        <div className="space-y-6">
            <div className="flex flex-wrap items-end justify-between gap-3">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900">Tableau de bord</h1>
                    <p className="text-sm text-gray-500">{format(new Date(), 'EEEE d MMMM yyyy', { locale: fr })}</p>
                </div>
                <div className="no-print flex gap-2">
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

            {error && <Alert tone="error">{apiErrorMessage(error, 'Indicateurs indisponibles.')}</Alert>}
            {summary?.tickets_error && (
                <Alert tone="warning">Indicateurs Zammad indisponibles : {summary.tickets_error}</Alert>
            )}

            {isLoading ? <LoadingBlock /> : contracts && (
                <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                    <KpiCard icon={FileText} tone="primary" label="Contrats en cours" value={formatNumber(running)}
                        hint={`dont ${contracts.in_notice} en préavis · ${contracts.expired} expiré(s)`} />
                    <KpiCard icon={CalendarClock} tone={contracts.actions_count ? 'warning' : 'success'} label={`À traiter (${HORIZON_DAYS} j)`}
                        value={formatNumber(contracts.actions_count)} hint={`${contracts.pending_decisions} décision(s) à prendre`} />
                    <KpiCard icon={Wallet} tone="success" label="Budget annuel" value={formatCurrency(contracts.annual_budget)}
                        hint={`Engagé : ${formatCurrency(contracts.committed_amount)}`} />
                    <KpiCard icon={FolderKanban} tone="primary" label="Projets en cours" value={tickets ? formatNumber(tickets.project_open_count) : '—'}
                        hint="Tickets Zammad tagués projet" />
                    <KpiCard icon={Inbox} tone={tickets?.unassigned_count ? 'warning' : 'default'} label="Tickets ouverts"
                        value={tickets ? formatNumber(tickets.open_count) : '—'}
                        hint={tickets ? `${tickets.unassigned_count} non assigné(s) · ${tickets.high_priority_open} priorité haute` : ''} />
                    <KpiCard icon={AlertTriangle} tone={tickets?.older_than_30d ? 'danger' : 'default'} label="Ouverts depuis + 30 j"
                        value={tickets ? formatNumber(tickets.older_than_30d) : '—'} hint="À relancer ou clôturer" />
                    <KpiCard icon={CheckCircle2} tone="success" label="Clos sur 30 jours" value={tickets ? formatNumber(tickets.closed_30d) : '—'}
                        hint={tickets ? `${tickets.created_30d} créés sur la même période` : ''} />
                    <KpiCard icon={Clock} tone="default" label="Délai médian de résolution"
                        value={tickets ? formatHours(tickets.median_resolution_hours) : '—'} hint="Tickets clos sur 90 jours" />
                </div>
            )}

            <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
                <Section title="Échéances à traiter" icon={CalendarClock} className="lg:col-span-2" bodyClassName="">
                    {isLoading ? <LoadingBlock /> : (
                        <UpcomingDeadlines actions={summary?.actions} horizonDays={HORIZON_DAYS} onSelect={setContractId} />
                    )}
                </Section>
                <Section title="Tickets ouverts par technicien" icon={Inbox}>
                    {isLoading ? <LoadingBlock /> : tickets ? <WorkloadBars byOwner={tickets.by_owner} /> : <p className="text-sm text-gray-500">Données Zammad indisponibles.</p>}
                </Section>
            </div>

            <section>
                <h2 className="mb-3 flex items-center gap-2 text-base font-semibold text-gray-900">
                    <CalendarClock className="h-4 w-4 text-primary-600" /> Timeline – contrats et projets
                </h2>
                <SmartTimeline onContractSelect={setContractId} onTicketSelect={setTicketItem} />
            </section>

            <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
                <Section
                    title="Activité du support"
                    icon={CheckCircle2}
                    className="lg:col-span-2"
                    actions={
                        <div className="no-print flex gap-1 rounded-lg bg-gray-100 p-1">
                            {ACTIVITY_TABS.map((t) => (
                                <button key={t.id} type="button" onClick={() => setActivityTab(t.id)}
                                    className={`rounded-md px-2.5 py-1 text-xs sm:text-sm ${activityTab === t.id ? 'bg-white font-medium text-gray-900 shadow-sm' : 'text-gray-600 hover:text-gray-900'}`}>
                                    {t.label}
                                </button>
                            ))}
                        </div>
                    }
                >
                    {activityTab === 'histogram' && <TicketHistogram />}
                    {activityTab === 'heatmap' && <TicketHeatmap />}
                    {activityTab === 'flow' && (tickets ? <TicketFlowChart weeks={tickets.weekly_flow} /> : <p className="text-sm text-gray-500">Données Zammad indisponibles.</p>)}
                </Section>
                <Section title="Plus anciens tickets ouverts" icon={AlertTriangle} bodyClassName="px-4 py-2">
                    {isLoading ? <LoadingBlock /> : tickets ? <OldestTickets tickets={tickets.oldest_open} /> : <p className="py-2 text-sm text-gray-500">Données Zammad indisponibles.</p>}
                </Section>
            </div>

            {contracts && (
                <Section title="Budget annuel des contrats en cours" icon={Wallet}>
                    <BudgetBreakdown byCategory={contracts.by_category} topSuppliers={contracts.top_suppliers} />
                </Section>
            )}

            <ContractDetailModal open={Boolean(contractId)} contractId={contractId} onClose={() => setContractId(null)} />
            <TicketDetailModal item={ticketItem} onClose={() => setTicketItem(null)} />
            <ContractFormModal open={creating} onClose={() => setCreating(false)} />
        </div>
    );
}
