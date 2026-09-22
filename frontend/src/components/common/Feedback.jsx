/**
 * Composants d'état : chargement, erreur, vide, messages.
 */
import { AlertCircle, CheckCircle, Info, Loader2 } from 'lucide-react';

export function Spinner({ className = 'h-6 w-6' }) {
    return <Loader2 className={`animate-spin text-primary-600 ${className}`} aria-label="Chargement" />;
}

export function PageSpinner() {
    return (
        <div className="flex min-h-screen items-center justify-center">
            <Spinner className="h-10 w-10" />
        </div>
    );
}

export function LoadingBlock({ height = 'h-48' }) {
    return (
        <div className={`flex items-center justify-center ${height}`}>
            <Spinner />
        </div>
    );
}

const TONES = {
    error: { icon: AlertCircle, className: 'border-red-200 bg-red-50 text-red-700' },
    success: { icon: CheckCircle, className: 'border-emerald-200 bg-emerald-50 text-emerald-700' },
    info: { icon: Info, className: 'border-sky-200 bg-sky-50 text-sky-800' },
    warning: { icon: AlertCircle, className: 'border-amber-200 bg-amber-50 text-amber-800' },
};

export function Alert({ tone = 'info', children, className = '' }) {
    const { icon: Icon, className: toneClass } = TONES[tone];
    return (
        <div role={tone === 'error' ? 'alert' : 'status'} className={`flex items-start gap-2 rounded-lg border px-4 py-3 text-sm ${toneClass} ${className}`}>
            <Icon className="mt-0.5 h-4 w-4 flex-shrink-0" />
            <div className="min-w-0">{children}</div>
        </div>
    );
}

export function EmptyState({ icon: Icon = Info, title, children }) {
    return (
        <div className="flex flex-col items-center justify-center px-4 py-10 text-center">
            <Icon className="mb-3 h-8 w-8 text-gray-300" />
            <p className="text-sm font-medium text-gray-700">{title}</p>
            {children && <div className="mt-1 max-w-md text-sm text-gray-500">{children}</div>}
        </div>
    );
}
