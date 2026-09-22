/**
 * Formatage (français) des montants, dates et durées.
 */
import { format, formatDistanceToNowStrict, isValid, parseISO } from 'date-fns';
import { fr } from 'date-fns/locale';

const euros = new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 });
const eurosPrecise = new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR', minimumFractionDigits: 2 });
const numbers = new Intl.NumberFormat('fr-FR');

/** "2026-10-02" est interprété en date locale (pas de décalage de fuseau). */
export function toDate(value) {
    if (!value) return null;
    const date = value instanceof Date ? value : parseISO(value);
    return isValid(date) ? date : null;
}

export function formatCurrency(value, { precise = false } = {}) {
    if (value === null || value === undefined || Number.isNaN(Number(value))) return '—';
    return (precise ? eurosPrecise : euros).format(Number(value));
}

export function formatNumber(value) {
    return value === null || value === undefined ? '—' : numbers.format(value);
}

export function formatDate(value, pattern = 'dd/MM/yyyy') {
    const date = toDate(value);
    return date ? format(date, pattern, { locale: fr }) : '—';
}

/** Les horodatages du backend sont en UTC, parfois sans suffixe de fuseau. */
function toUtcDate(value) {
    if (!value) return null;
    if (value instanceof Date) return value;
    const hasZone = /[zZ]$|[+-]\d\d:?\d\d$/.test(value);
    return toDate(value.length > 10 && !hasZone ? `${value}Z` : value);
}

export function formatDateTime(value) {
    const date = toUtcDate(value);
    return date ? format(date, "dd/MM/yyyy 'à' HH:mm", { locale: fr }) : '—';
}

/** Horodatage exprimé relativement à maintenant : « il y a 3 heures ». */
export function formatAgo(value) {
    const date = toUtcDate(value);
    return date ? `il y a ${formatDistanceToNowStrict(date, { locale: fr })}` : '—';
}

/** Nombre de jours relatif : « aujourd'hui », « dans 12 j », « il y a 3 j ». */
export function formatDays(days) {
    if (days === null || days === undefined) return '—';
    if (days === 0) return "aujourd'hui";
    if (days === 1) return 'demain';
    if (days > 0) return `dans ${days} j`;
    return `il y a ${Math.abs(days)} j`;
}

/** Durée en heures rendue lisible : « 5 h », « 2,5 j ». */
export function formatHours(hours) {
    if (hours === null || hours === undefined) return '—';
    if (hours < 24) return `${numbers.format(Math.round(hours))} h`;
    return `${numbers.format(Math.round((hours / 24) * 10) / 10)} j`;
}

export function formatMonths(months) {
    if (!months) return '—';
    if (months % 12 === 0) {
        const years = months / 12;
        return `${months} mois (${years} an${years > 1 ? 's' : ''})`;
    }
    return `${months} mois`;
}
