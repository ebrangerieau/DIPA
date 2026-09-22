/**
 * État des connecteurs (Zammad, Microsoft, e-mail) et pilotage des alertes d'échéance.
 */
import { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Bell, CheckCircle2, Eye, Mail, Play, Server, ShieldCheck, XCircle } from 'lucide-react';
import { Alert, LoadingBlock } from '../common/Feedback';
import systemService from '../../services/systemService';
import { apiErrorMessage } from '../../lib/api';
import { formatAgo, formatDate } from '../../lib/format';

function StatusLine({ ok, children }) {
    return (
        <p className="flex items-start gap-2 text-sm text-gray-700">
            {ok ? <CheckCircle2 className="mt-0.5 h-4 w-4 flex-shrink-0 text-emerald-600" /> : <XCircle className="mt-0.5 h-4 w-4 flex-shrink-0 text-gray-400" />}
            <span>{children}</span>
        </p>
    );
}

function Tile({ icon: Icon, title, children }) {
    return (
        <div className="card space-y-2 p-4">
            <h3 className="flex items-center gap-2 text-sm font-semibold text-gray-900"><Icon className="h-4 w-4 text-primary-600" /> {title}</h3>
            {children}
        </div>
    );
}

function AlertResult({ result }) {
    if (!result) return null;
    return (
        <div className="space-y-2 rounded-lg border border-gray-200 bg-gray-50 p-4 text-sm">
            <p className="font-medium text-gray-900">
                {result.sent ? 'Récapitulatif envoyé.' : result.skipped_reason || 'Aperçu (aucun envoi).'}
            </p>
            {result.alerts.length === 0 && result.renewals.length === 0 ? (
                <p className="text-gray-600">Aucune alerte à envoyer aujourd&apos;hui.</p>
            ) : (
                <ul className="list-inside list-disc text-gray-700">
                    {result.alerts.map((a) => (
                        <li key={`${a.contract_id}-${a.kind}`}>
                            <strong>{a.name}</strong> ({a.supplier}) : {a.message} – {formatDate(a.reference_date)} · {a.decision_label}
                        </li>
                    ))}
                    {result.renewals.map((r) => (
                        <li key={r.contract_id}><strong>{r.name}</strong> : reconduit jusqu&apos;au {formatDate(r.apres.end_date)}</li>
                    ))}
                </ul>
            )}
        </div>
    );
}

export default function SystemStatus() {
    const [result, setResult] = useState(null);
    const [message, setMessage] = useState(null);
    const { data: status, isLoading, error, refetch } = useQuery({ queryKey: ['system-status'], queryFn: systemService.getStatus });

    const onError = (err) => setMessage({ tone: 'error', text: apiErrorMessage(err) });
    const preview = useMutation({ mutationFn: systemService.previewAlerts, onSuccess: (data) => { setMessage(null); setResult(data); }, onError });
    const run = useMutation({
        mutationFn: systemService.runAlerts,
        onSuccess: (data) => { setResult(data); setMessage(null); refetch(); },
        onError,
    });
    const test = useMutation({
        mutationFn: systemService.sendTestEmail,
        onSuccess: (data) => setMessage({ tone: 'success', text: `E-mail de test envoyé à ${data.sent_to.join(', ')}.` }),
        onError,
    });

    if (isLoading) return <LoadingBlock />;
    if (error) return <Alert tone="error">{apiErrorMessage(error)}</Alert>;

    const { zammad, auth, mail, alerts } = status;
    return (
        <div className="space-y-5">
            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                <Tile icon={Server} title="Zammad">
                    <StatusLine ok={zammad.configured}>{zammad.configured ? 'Configuré' : 'Non configuré'}</StatusLine>
                    <StatusLine ok={zammad.reachable}>{zammad.reachable ? 'Accessible' : `Inaccessible${zammad.error ? ` : ${zammad.error}` : ''}`}</StatusLine>
                    <p className="text-xs text-gray-500">Tag des projets : <code className="rounded bg-gray-100 px-1">{zammad.project_tag}</code></p>
                </Tile>
                <Tile icon={ShieldCheck} title="Connexion">
                    <StatusLine ok={auth.sso_enabled}>SSO Microsoft {auth.sso_enabled ? 'actif' : 'non configuré'}</StatusLine>
                    <StatusLine ok={!auth.local_enabled || auth.sso_enabled}>Comptes locaux {auth.local_enabled ? 'autorisés' : 'désactivés'}</StatusLine>
                    <StatusLine ok={auth.cookie_secure}>Cookies {auth.cookie_secure ? 'sécurisés (HTTPS)' : 'non sécurisés (HTTP)'}</StatusLine>
                </Tile>
                <Tile icon={Mail} title="E-mails">
                    <StatusLine ok={mail.configured}>
                        {mail.configured ? `Envoi via ${mail.backend === 'graph' ? 'Microsoft Graph' : 'SMTP'}` : 'Envoi non configuré'}
                    </StatusLine>
                    <p className="text-xs text-gray-500">Expéditeur : {mail.sender || '—'}</p>
                    <p className="text-xs text-gray-500">Destinataires : {mail.recipients.length ? mail.recipients.join(', ') : '—'}</p>
                </Tile>
            </div>

            <div className="card space-y-4 p-4">
                <h3 className="flex items-center gap-2 text-sm font-semibold text-gray-900"><Bell className="h-4 w-4 text-primary-600" /> Alertes d&apos;échéance</h3>
                <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
                    <StatusLine ok={alerts.enabled}>Alertes {alerts.enabled ? 'activées' : 'désactivées (ALERTS_ENABLED)'}</StatusLine>
                    <StatusLine ok={alerts.scheduler_enabled}>Vérification quotidienne à partir de {alerts.hour} h</StatusLine>
                    <p className="text-sm text-gray-700">
                        Rappels à J-{alerts.deadline_thresholds.join(', J-')} de la date limite de résiliation ; fin de contrat à J-{alerts.end_days}.
                    </p>
                    <p className="text-sm text-gray-700">
                        Dernière exécution : {alerts.last_run ? formatAgo(alerts.last_run) : 'jamais'}
                        {alerts.last_error && <span className="text-red-600"> – {alerts.last_error}</span>}
                    </p>
                </div>
                {message && <Alert tone={message.tone}>{message.text}</Alert>}
                <div className="flex flex-wrap gap-2">
                    <button type="button" className="btn-secondary" onClick={() => preview.mutate()} disabled={preview.isPending}>
                        <Eye className="h-4 w-4" /> Aperçu du jour
                    </button>
                    <button type="button" className="btn-secondary" onClick={() => test.mutate()} disabled={test.isPending || !mail.configured}>
                        <Mail className="h-4 w-4" /> E-mail de test
                    </button>
                    <button type="button" className="btn-primary" disabled={run.isPending}
                        onClick={() => window.confirm('Exécuter maintenant les reconductions tacites et l\'envoi des alertes ?') && run.mutate()}>
                        <Play className="h-4 w-4" /> Exécuter maintenant
                    </button>
                </div>
                <AlertResult result={result} />
            </div>
        </div>
    );
}
