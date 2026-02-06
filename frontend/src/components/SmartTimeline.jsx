/**
 * Composant SmartTimeline avec vis-timeline.
 * Implémente le Smart Stacking pour éviter les collisions visuelles.
 */
import { useEffect, useRef, useState } from 'react';
import { Timeline } from 'vis-timeline/standalone';
import { DataSet } from 'vis-data';
import 'vis-timeline/styles/vis-timeline-graph2d.css';
import { useQuery } from '@tanstack/react-query';
import contractsService from '../services/contractsService';
import ticketsService from '../services/ticketsService';

/**
 * Algorithme de Smart Stacking pour éviter les collisions.
 * @param {Array} items - Éléments de la timeline
 * @returns {Array} - Éléments avec groupes assignés
 */
function applySmartStacking(items) {
    // Trier les éléments par date de début
    const sortedItems = [...items].sort((a, b) =>
        new Date(a.start) - new Date(b.start)
    );

    // Groupes (lignes horizontales)
    const groups = [];

    sortedItems.forEach(item => {
        const itemStart = new Date(item.start);
        const itemEnd = item.end ? new Date(item.end) : itemStart;

        // Trouver un groupe sans collision
        let assignedGroup = null;

        for (let i = 0; i < groups.length; i++) {
            const group = groups[i];
            let hasCollision = false;

            for (const existingItem of group.items) {
                const existingStart = new Date(existingItem.start);
                const existingEnd = existingItem.end ? new Date(existingItem.end) : existingStart;

                // Vérifier le chevauchement
                if (
                    (itemStart >= existingStart && itemStart <= existingEnd) ||
                    (itemEnd >= existingStart && itemEnd <= existingEnd) ||
                    (itemStart <= existingStart && itemEnd >= existingEnd)
                ) {
                    hasCollision = true;
                    break;
                }
            }

            if (!hasCollision) {
                assignedGroup = i;
                break;
            }
        }

        // Si aucun groupe disponible, créer un nouveau
        if (assignedGroup === null) {
            assignedGroup = groups.length;
            groups.push({ id: assignedGroup, items: [] });
        }

        // Assigner l'élément au groupe
        item.group = assignedGroup;
        groups[assignedGroup].items.push(item);
    });

    return { items: sortedItems, groups };
}

export default function SmartTimeline() {
    const timelineRef = useRef(null);
    const timelineInstance = useRef(null);
    const [selectedItem, setSelectedItem] = useState(null);

    // Récupération des données
    const { data: contractsData = [], isLoading: loadingContracts } = useQuery({
        queryKey: ['contracts-timeline'],
        queryFn: contractsService.getTimelineData,
    });

    const { data: ticketsData = [], isLoading: loadingTickets } = useQuery({
        queryKey: ['tickets-timeline'],
        queryFn: ticketsService.getTimelineData,
    });

    useEffect(() => {
        if (!timelineRef.current || loadingContracts || loadingTickets) return;

        // Combiner les données
        const allItems = [...contractsData, ...ticketsData];

        // Appliquer le Smart Stacking
        const { items, groups } = applySmartStacking(allItems);

        // Créer les datasets
        const itemsDataSet = new DataSet(items.map(item => ({
            ...item,
            content: item.title,
            style: `background-color: ${item.color}; border-color: ${item.color};`,
            type: item.end ? 'range' : 'point',
        })));

        const groupsDataSet = new DataSet(
            groups.map(g => ({
                id: g.id,
                content: `Ligne ${g.id + 1}`,
            }))
        );

        // Options de la timeline
        const options = {
            width: '100%',
            height: `${Math.max(400, groups.length * 80)}px`,
            margin: {
                item: {
                    horizontal: 10,
                    vertical: 10,
                },
            },
            orientation: 'top',
            stack: false, // On gère le stacking manuellement
            showCurrentTime: true,
            zoomMin: 1000 * 60 * 60 * 24 * 7, // 1 semaine
            zoomMax: 1000 * 60 * 60 * 24 * 365 * 2, // 2 ans
            locale: 'fr',
            format: {
                minorLabels: {
                    day: 'D',
                    month: 'MMM',
                    year: 'YYYY',
                },
                majorLabels: {
                    day: 'MMMM YYYY',
                    month: 'YYYY',
                    year: '',
                },
            },
        };

        // Créer ou mettre à jour la timeline
        if (!timelineInstance.current) {
            timelineInstance.current = new Timeline(
                timelineRef.current,
                itemsDataSet,
                groupsDataSet,
                options
            );

            // Événement de sélection
            timelineInstance.current.on('select', (properties) => {
                if (properties.items.length > 0) {
                    const itemId = properties.items[0];
                    const item = items.find(i => i.id === itemId);
                    setSelectedItem(item);
                } else {
                    setSelectedItem(null);
                }
            });
        } else {
            timelineInstance.current.setItems(itemsDataSet);
            timelineInstance.current.setGroups(groupsDataSet);
            timelineInstance.current.setOptions(options);
        }

        // Ajuster la vue initiale
        timelineInstance.current.fit();

        return () => {
            if (timelineInstance.current) {
                timelineInstance.current.destroy();
                timelineInstance.current = null;
            }
        };
    }, [contractsData, ticketsData, loadingContracts, loadingTickets]);

    if (loadingContracts || loadingTickets) {
        return (
            <div className="flex items-center justify-center h-96">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
            </div>
        );
    }

    return (
        <div className="space-y-4">
            <div
                ref={timelineRef}
                className="bg-white rounded-lg shadow-sm border border-gray-200"
            />

            {/* Modal de détails */}
            {selectedItem && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4 shadow-xl">
                        <div className="flex justify-between items-start mb-4">
                            <h3 className="text-lg font-semibold text-gray-900">
                                {selectedItem.title}
                            </h3>
                            <button
                                onClick={() => setSelectedItem(null)}
                                className="text-gray-400 hover:text-gray-600"
                            >
                                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                </svg>
                            </button>
                        </div>

                        <div className="space-y-3">
                            <div>
                                <span className="text-sm font-medium text-gray-500">Type:</span>
                                <span className="ml-2 text-sm text-gray-900">
                                    {selectedItem.type === 'contract-notice' || selectedItem.type === 'contract-milestone'
                                        ? 'Contrat'
                                        : 'Ticket'}
                                </span>
                            </div>

                            <div>
                                <span className="text-sm font-medium text-gray-500">Début:</span>
                                <span className="ml-2 text-sm text-gray-900">
                                    {new Date(selectedItem.start).toLocaleDateString('fr-FR')}
                                </span>
                            </div>

                            {selectedItem.end && (
                                <div>
                                    <span className="text-sm font-medium text-gray-500">Fin:</span>
                                    <span className="ml-2 text-sm text-gray-900">
                                        {new Date(selectedItem.end).toLocaleDateString('fr-FR')}
                                    </span>
                                </div>
                            )}

                            {selectedItem.metadata && Object.keys(selectedItem.metadata).length > 0 && (
                                <div className="pt-3 border-t border-gray-200">
                                    <h4 className="text-sm font-medium text-gray-700 mb-2">Détails:</h4>
                                    {Object.entries(selectedItem.metadata).map(([key, value]) => (
                                        <div key={key} className="text-sm">
                                            <span className="text-gray-500">{key}:</span>
                                            <span className="ml-2 text-gray-900">{String(value)}</span>
                                        </div>
                                    ))}
                                </div>
                            )}

                            {selectedItem.metadata?.sharepoint_url && (
                                <a
                                    href={selectedItem.metadata.sharepoint_url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="inline-flex items-center px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 transition-colors"
                                >
                                    Voir le PDF sur SharePoint
                                </a>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
