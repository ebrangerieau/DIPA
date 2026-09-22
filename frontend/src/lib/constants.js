/**
 * Référentiels partagés avec le backend (libellés et styles d'affichage).
 */
export const CATEGORIES = [
    { value: 'licence', label: 'Licences logicielles' },
    { value: 'maintenance', label: 'Maintenance / support' },
    { value: 'telecom', label: 'Télécom / Internet' },
    { value: 'cloud', label: 'Hébergement / Cloud' },
    { value: 'materiel', label: 'Matériel / Location' },
    { value: 'service', label: 'Prestations de services' },
    { value: 'autre', label: 'Autre' },
];

export const DECISIONS = {
    pending: { label: 'À décider', badge: 'badge-gray' },
    renew: { label: 'À reconduire', badge: 'badge-green' },
    renegotiate: { label: 'À renégocier', badge: 'badge-amber' },
    terminate: { label: 'À résilier', badge: 'badge-red' },
};

export const STATUSES = {
    active: { label: 'Actif', badge: 'badge-green' },
    in_notice: { label: 'En préavis', badge: 'badge-amber' },
    expired: { label: 'Expiré', badge: 'badge-gray' },
};

export const URGENCIES = {
    critical: { label: 'Urgent', badge: 'badge-red', dot: 'bg-red-500' },
    high: { label: 'Prioritaire', badge: 'badge-amber', dot: 'bg-amber-500' },
    medium: { label: 'À planifier', badge: 'badge-blue', dot: 'bg-sky-500' },
};

/** Couleurs de la timeline envoyées par le backend -> classe CSS (voir index.css). */
export const TIMELINE_CLASSES = {
    '#10B981': 'tl-green',
    '#F59E0B': 'tl-orange',
    '#EF4444': 'tl-red',
    '#6B7280': 'tl-gray',
    '#3B82F6': 'tl-blue',
};

export const TIMELINE_LEGEND = [
    { className: 'bg-emerald-500', label: 'Contrat actif (échéance)' },
    { className: 'bg-amber-500', label: 'Préavis, plus de 30 j' },
    { className: 'bg-red-500', label: 'Préavis, 30 j ou moins' },
    { className: 'bg-gray-500', label: 'Contrat expiré' },
    { className: 'bg-blue-500', label: 'Projet Zammad' },
];

export const PRIORITY_LABELS = {
    '1 low': 'Basse',
    '2 normal': 'Normale',
    '3 high': 'Haute',
};

export const STATE_LABELS = {
    new: 'Nouveau',
    open: 'Ouvert',
    closed: 'Clos',
    merged: 'Fusionné',
    'pending reminder': 'En attente (rappel)',
    'pending close': 'En attente de clôture',
};

export const categoryLabel = (value) => CATEGORIES.find((c) => c.value === value)?.label || 'Autre';
export const priorityLabel = (value) => PRIORITY_LABELS[value] || value || '—';
export const stateLabel = (value) => STATE_LABELS[value] || value || '—';
