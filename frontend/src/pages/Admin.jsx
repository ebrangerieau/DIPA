/**
 * Administration : utilisateurs, connecteurs et alertes, sauvegarde, journal.
 */
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Bell, Database, History, Users } from 'lucide-react';
import UserManagement from '../components/admin/UserManagement';
import SystemStatus from '../components/admin/SystemStatus';
import BackupRestore from '../components/admin/BackupRestore';
import AuditLog from '../components/admin/AuditLog';
import authService from '../services/authService';

const TABS = [
    { id: 'users', label: 'Utilisateurs', icon: Users },
    { id: 'alerts', label: 'Connecteurs et alertes', icon: Bell },
    { id: 'backup', label: 'Sauvegarde', icon: Database },
    { id: 'journal', label: 'Journal', icon: History },
];

export default function Admin() {
    const [tab, setTab] = useState('users');
    const { data: config } = useQuery({ queryKey: ['auth-config'], queryFn: authService.getConfig, staleTime: Infinity });

    return (
        <div className="space-y-5">
            <h1 className="text-2xl font-bold text-gray-900">Administration</h1>

            <div className="flex gap-1 overflow-x-auto border-b border-gray-200" role="tablist">
                {TABS.map(({ id, label, icon: Icon }) => (
                    <button key={id} type="button" role="tab" aria-selected={tab === id} onClick={() => setTab(id)}
                        className={`-mb-px inline-flex items-center gap-2 whitespace-nowrap border-b-2 px-4 py-2 text-sm font-medium transition-colors ${tab === id
                            ? 'border-primary-600 text-primary-700'
                            : 'border-transparent text-gray-600 hover:text-gray-900'}`}>
                        <Icon className="h-4 w-4" /> {label}
                    </button>
                ))}
            </div>

            {tab === 'users' && <UserManagement localAuthEnabled={config?.local_enabled ?? true} />}
            {tab === 'alerts' && <SystemStatus />}
            {tab === 'backup' && <BackupRestore />}
            {tab === 'journal' && <AuditLog />}
        </div>
    );
}
