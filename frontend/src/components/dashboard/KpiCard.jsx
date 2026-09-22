/**
 * Carte d'indicateur clé.
 */
const TONES = {
    default: 'bg-gray-100 text-gray-600',
    primary: 'bg-primary-100 text-primary-700',
    warning: 'bg-amber-100 text-amber-700',
    danger: 'bg-red-100 text-red-700',
    success: 'bg-emerald-100 text-emerald-700',
};

export default function KpiCard({ icon: Icon, label, value, hint, tone = 'default', onClick }) {
    const Wrapper = onClick ? 'button' : 'div';
    return (
        <Wrapper
            type={onClick ? 'button' : undefined}
            onClick={onClick}
            className={`card flex items-start gap-3 p-4 text-left ${onClick ? 'transition-shadow hover:shadow-md' : ''}`}
        >
            {Icon && (
                <span className={`flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg ${TONES[tone]}`}>
                    <Icon className="h-5 w-5" />
                </span>
            )}
            <span className="min-w-0">
                <span className="block text-xs font-medium uppercase tracking-wide text-gray-500">{label}</span>
                <span className="mt-0.5 block text-2xl font-semibold text-gray-900">{value}</span>
                {hint && <span className="block truncate text-xs text-gray-500">{hint}</span>}
            </span>
        </Wrapper>
    );
}
