/**
 * Mise en page de l'application : en-tête, navigation, menu utilisateur.
 */
import { useState } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { Menu, MenuButton, MenuItem, MenuItems } from '@headlessui/react';
import { ChevronDown, FileText, KeyRound, LayoutDashboard, LogOut, Settings } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import ChangePasswordModal from '../account/ChangePasswordModal';

const navClass = ({ isActive }) =>
    `inline-flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors ${isActive ? 'bg-primary-50 text-primary-700' : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
    }`;

export default function AppLayout() {
    const { user, isAdmin, logout } = useAuth();
    const navigate = useNavigate();
    const [passwordOpen, setPasswordOpen] = useState(false);

    const handleLogout = async () => {
        await logout();
        navigate('/login');
    };

    return (
        <div className="min-h-screen bg-gray-50">
            <header className="no-print sticky top-0 z-40 border-b border-gray-200 bg-white/95 backdrop-blur">
                <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3 sm:px-6 lg:px-8">
                    <div className="flex items-center gap-2">
                        <img src="/favicon.svg" alt="" className="h-8 w-8" />
                        <div>
                            <p className="text-lg font-bold leading-tight text-gray-900">Cockpit IT</p>
                            <p className="hidden text-xs text-gray-500 sm:block">Pilotage des contrats et projets</p>
                        </div>
                    </div>

                    <nav className="order-3 flex w-full gap-1 overflow-x-auto sm:order-none sm:w-auto" aria-label="Navigation principale">
                        <NavLink to="/" end className={navClass}>
                            <LayoutDashboard className="h-4 w-4" /> Tableau de bord
                        </NavLink>
                        <NavLink to="/contrats" className={navClass}>
                            <FileText className="h-4 w-4" /> Contrats
                        </NavLink>
                        {isAdmin && (
                            <NavLink to="/admin" className={navClass}>
                                <Settings className="h-4 w-4" /> Administration
                            </NavLink>
                        )}
                    </nav>

                    <Menu as="div" className="relative ml-auto">
                        <MenuButton className="btn-ghost gap-2 px-3 py-2">
                            <span className="flex h-8 w-8 items-center justify-center rounded-full bg-primary-100 text-sm font-semibold text-primary-700">
                                {(user?.display_name || '?').charAt(0).toUpperCase()}
                            </span>
                            <span className="hidden text-left md:block">
                                <span className="block text-sm font-medium text-gray-900">{user?.display_name}</span>
                                <span className="block text-xs text-gray-500">{isAdmin ? 'Administrateur' : 'Lecture seule'}</span>
                            </span>
                            <ChevronDown className="h-4 w-4 text-gray-400" />
                        </MenuButton>
                        <MenuItems
                            anchor="bottom end"
                            className="z-50 mt-2 w-56 rounded-lg border border-gray-200 bg-white p-1 shadow-lg focus:outline-none"
                        >
                            <div className="px-3 py-2 text-xs text-gray-500">{user?.email}</div>
                            {user?.has_local_password && (
                                <MenuItem>
                                    <button onClick={() => setPasswordOpen(true)} className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm text-gray-700 data-[focus]:bg-gray-100">
                                        <KeyRound className="h-4 w-4" /> Changer mon mot de passe
                                    </button>
                                </MenuItem>
                            )}
                            <MenuItem>
                                <button onClick={handleLogout} className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm text-gray-700 data-[focus]:bg-gray-100">
                                    <LogOut className="h-4 w-4" /> Déconnexion
                                </button>
                            </MenuItem>
                        </MenuItems>
                    </Menu>
                </div>
            </header>

            <main className="print-full mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
                <Outlet />
            </main>

            <ChangePasswordModal
                open={passwordOpen || Boolean(user?.must_change_password)}
                forced={Boolean(user?.must_change_password)}
                onClose={() => setPasswordOpen(false)}
            />
        </div>
    );
}
