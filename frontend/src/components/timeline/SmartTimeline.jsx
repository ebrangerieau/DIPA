/**
 * Smart Timeline (vis-timeline) : contrats et projets Zammad.
 *
 * Smart Stacking (CDC §2.1) : chaque ligne (Contrats / Projets) est empilée par
 * vis-timeline, qui calcule les collisions à partir de la taille réellement affichée
 * des éléments (libellés compris) et recalcule l'empilement à chaque zoom : aucun
 * chevauchement visuel, quelle que soit l'échelle.
 */
import { useEffect, useMemo, useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { DataSet, Timeline } from 'vis-timeline/standalone';
import 'vis-timeline/styles/vis-timeline-graph2d.css';
import { format } from 'date-fns';
import { fr } from 'date-fns/locale';
import { CalendarRange, Crosshair, Maximize2 } from 'lucide-react';
import contractsService from '../../services/contractsService';
import ticketsService from '../../services/ticketsService';
import { apiErrorMessage } from '../../lib/api';
import { TIMELINE_CLASSES, TIMELINE_LEGEND } from '../../lib/constants';
import { formatDate } from '../../lib/format';
import { Alert, LoadingBlock } from '../common/Feedback';

const DAY = 24 * 60 * 60 * 1000;

const MINOR_FORMATS = { millisecond: 'SSS', second: 's', minute: 'HH:mm', hour: 'HH:mm', weekday: 'EEE d', day: 'd', week: "'S'w", month: 'MMM', year: 'yyyy' };
const MAJOR_FORMATS = { millisecond: 'HH:mm:ss', second: 'd MMM HH:mm', minute: 'EEEE d MMMM', hour: 'EEEE d MMMM', weekday: 'MMMM yyyy', day: 'MMMM yyyy', week: 'MMMM yyyy', month: 'yyyy', year: '' };

const capitalize = (text) => text.charAt(0).toUpperCase() + text.slice(1);

const formatAxis = (formats) => (date, scale) => {
    const pattern = formats[scale];
    return pattern ? capitalize(format(new Date(date.valueOf()), pattern, { locale: fr })) : '';
};

const TIMELINE_OPTIONS = {
    width: '100%',
    minHeight: '260px',
    maxHeight: '620px',
    verticalScroll: true,
    orientation: 'top',
    stack: true,
    showCurrentTime: true,
    zoomMin: 7 * DAY,
    zoomMax: 6 * 365 * DAY,
    groupOrder: 'order',
    margin: { item: { horizontal: 6, vertical: 6 }, axis: 8 },
    locale: 'fr',
    locales: { fr: { current: 'actuel', time: 'heure', deleteSelected: 'Supprimer' } },
    format: { minorLabels: formatAxis(MINOR_FORMATS), majorLabels: formatAxis(MAJOR_FORMATS) },
    tooltip: { followMouse: true, overflowMethod: 'cap' },
    // Contenu inséré en texte brut : aucun HTML issu des titres de tickets n'est interprété
    template: (item) => {
        const span = document.createElement('span');
        span.textContent = item?.label ?? '';
        return span;
    },
};

/** Info-bulle en texte simple (filtrée par vis-timeline contre l'injection HTML). */
function tooltipFor(item) {
    const m = item.metadata || {};
    if (item.type === 'ticket') {
        return [m.title, `créé le ${formatDate(m.created_at?.slice(0, 10))}`, m.owner].filter(Boolean).join(' · ');
    }
    return `${m.name} (${m.supplier}) · échéance ${formatDate(m.end_date)} · préavis ${m.notice_period_days} j`;
}

export default function SmartTimeline({ onContractSelect, onTicketSelect }) {
    const containerRef = useRef(null);
    const timelineRef = useRef(null);
    const itemsRef = useRef(new Map());
    const initialWindowSet = useRef(false);
    const callbacksRef = useRef({ onContractSelect, onTicketSelect });
    const [showContracts, setShowContracts] = useState(true);
    const [showProjects, setShowProjects] = useState(true);
    const [hideExpired, setHideExpired] = useState(false);

    callbacksRef.current = { onContractSelect, onTicketSelect };

    const contractsQuery = useQuery({ queryKey: ['contracts-timeline'], queryFn: contractsService.getTimelineData });
    const ticketsQuery = useQuery({ queryKey: ['tickets-timeline'], queryFn: ticketsService.getTimelineData, retry: false });

    const items = useMemo(() => {
        const contracts = (contractsQuery.data || []).filter(
            (i) => showContracts && !(hideExpired && i.metadata?.computed_status === 'expired'),
        );
        const projects = showProjects ? ticketsQuery.data || [] : [];
        return [...contracts, ...projects];
    }, [contractsQuery.data, ticketsQuery.data, showContracts, showProjects, hideExpired]);

    // Création unique de la timeline
    useEffect(() => {
        if (!containerRef.current) return undefined;
        const timeline = new Timeline(containerRef.current, new DataSet([]), TIMELINE_OPTIONS);
        timeline.on('select', ({ items: selected }) => {
            const item = itemsRef.current.get(selected[0]);
            timeline.setSelection([]);
            if (!item) return;
            if (item.type === 'ticket') callbacksRef.current.onTicketSelect?.(item);
            else callbacksRef.current.onContractSelect?.(item.metadata.contract_id);
        });
        timelineRef.current = timeline;
        return () => {
            timeline.destroy();
            timelineRef.current = null;
        };
    }, []);

    // Mise à jour des données
    useEffect(() => {
        const timeline = timelineRef.current;
        if (!timeline) return;
        itemsRef.current = new Map(items.map((i) => [i.id, i]));

        const groups = [];
        if (showContracts) groups.push({ id: 'contracts', content: 'Contrats', order: 1 });
        if (showProjects) groups.push({ id: 'projects', content: 'Projets Zammad', order: 2 });

        timeline.setGroups(new DataSet(groups));
        timeline.setItems(new DataSet(items.map((item) => ({
            id: item.id,
            group: item.group,
            start: item.start,
            end: item.end || undefined,
            type: item.end ? 'range' : 'point',
            label: item.title,
            title: tooltipFor(item),
            className: TIMELINE_CLASSES[item.color] || 'tl-blue',
        }))));

        if (!initialWindowSet.current && items.length > 0) {
            const now = Date.now();
            timeline.setWindow(now - 60 * DAY, now + 300 * DAY, { animation: false });
            initialWindowSet.current = true;
        }
    }, [items, showContracts, showProjects]);

    const loading = contractsQuery.isLoading || ticketsQuery.isLoading;
    const noProjects = !ticketsQuery.isLoading && !ticketsQuery.error && (ticketsQuery.data || []).length === 0;

    return (
        <div className="card overflow-hidden">
            <div className="no-print flex flex-wrap items-center gap-x-4 gap-y-2 border-b border-gray-100 px-4 py-3">
                <label className="flex items-center gap-2 text-sm text-gray-700">
                    <input type="checkbox" className="h-4 w-4 rounded border-gray-300" checked={showContracts} onChange={(e) => setShowContracts(e.target.checked)} />
                    Contrats
                </label>
                <label className="flex items-center gap-2 text-sm text-gray-700">
                    <input type="checkbox" className="h-4 w-4 rounded border-gray-300" checked={showProjects} onChange={(e) => setShowProjects(e.target.checked)} />
                    Projets Zammad
                </label>
                <label className="flex items-center gap-2 text-sm text-gray-700">
                    <input type="checkbox" className="h-4 w-4 rounded border-gray-300" checked={hideExpired} onChange={(e) => setHideExpired(e.target.checked)} />
                    Masquer les contrats expirés
                </label>
                <div className="ml-auto flex gap-1">
                    <button type="button" className="btn-ghost text-xs" onClick={() => timelineRef.current?.moveTo(new Date())}>
                        <Crosshair className="h-4 w-4" /> Aujourd&apos;hui
                    </button>
                    <button type="button" className="btn-ghost text-xs" onClick={() => {
                        const now = Date.now();
                        timelineRef.current?.setWindow(now - 30 * DAY, now + 365 * DAY);
                    }}>
                        <CalendarRange className="h-4 w-4" /> 12 mois
                    </button>
                    <button type="button" className="btn-ghost text-xs" onClick={() => timelineRef.current?.fit()}>
                        <Maximize2 className="h-4 w-4" /> Tout afficher
                    </button>
                </div>
            </div>

            {contractsQuery.error && (
                <Alert tone="error" className="m-4">{apiErrorMessage(contractsQuery.error, 'Contrats indisponibles.')}</Alert>
            )}
            {ticketsQuery.error && (
                <Alert tone="warning" className="m-4">
                    Projets Zammad indisponibles : {apiErrorMessage(ticketsQuery.error)}
                </Alert>
            )}

            {/* Défilement horizontal sur mobile (CDC §5.1) */}
            <div className="relative overflow-x-auto">
                {loading && <div className="absolute inset-0 z-10 bg-white/70"><LoadingBlock height="h-64" /></div>}
                <div ref={containerRef} className="min-w-[680px]" />
            </div>

            <div className="flex flex-wrap items-center gap-x-5 gap-y-2 border-t border-gray-100 px-4 py-3 text-xs text-gray-600">
                {TIMELINE_LEGEND.map((l) => (
                    <span key={l.label} className="flex items-center gap-1.5">
                        <span className={`h-2.5 w-2.5 rounded-full ${l.className}`} /> {l.label}
                    </span>
                ))}
                {noProjects && showProjects && (
                    <span className="text-gray-500">
                        · Aucun ticket ne porte encore le tag projet dans Zammad.
                    </span>
                )}
            </div>
        </div>
    );
}
