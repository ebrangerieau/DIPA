/**
 * Page principale du Dashboard avec la Smart Timeline.
 */
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import SmartTimeline from '../components/SmartTimeline';
import TicketHistogram from '../components/TicketHistogram';
import NewContractModal from '../components/NewContractModal';
import { Calendar, TrendingUp, LogOut } from 'lucide-react';
import authService from '../services/authService';

export default function Dashboard() {
    const navigate = useNavigate();
    const [isModalOpen, setIsModalOpen] = useState(false);
    // State pour forcer le rafraîchissement de la timeline
    const [refreshTrigger, setRefreshTrigger] = useState(0);

    const handleLogout = () => {
        authService.removeToken();
        navigate('/login');
    };

    const handleContractCreated = () => {
        // Incrémenter pour déclencher le refresh des composants enfants
        setRefreshTrigger(prev => prev + 1);
    };

    return (
        <div className="min-h-screen bg-gray-50">
            {/* Header */}
            <header className="bg-white shadow-sm border-b border-gray-200">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
                    <div className="flex items-center justify-between">
                        <div>
                            <h1 className="text-3xl font-bold text-gray-900">Cockpit IT</h1>
                            <p className="mt-1 text-sm text-gray-600">
                                Pilotage visuel des contrats et projets
                            </p>
                        </div>

                        <div className="flex items-center gap-4">
                            <button
                                onClick={() => setIsModalOpen(true)}
                                className="inline-flex items-center px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 transition-colors"
                            >
                                <Calendar className="w-4 h-4 mr-2" />
                                Nouveau Contrat
                            </button>

                            <button
                                onClick={handleLogout}
                                className="inline-flex items-center px-4 py-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 transition-colors"
                            >
                                <LogOut className="w-4 h-4 mr-2" />
                                Déconnexion
                            </button>
                        </div>
                    </div>
                </div>
            </header>

            {/* Main Content */}
            <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <div className="space-y-8">
                    {/* Smart Timeline Section */}
                    <section>
                        <div className="flex items-center gap-2 mb-4">
                            <Calendar className="w-5 h-5 text-primary-600" />
                            <h2 className="text-xl font-semibold text-gray-900">
                                Timeline - Contrats & Projets
                            </h2>
                        </div>
                        <SmartTimeline key={refreshTrigger} />
                    </section>

                    {/* Histogram Section */}
                    <section>
                        <div className="flex items-center gap-2 mb-4">
                            <TrendingUp className="w-5 h-5 text-primary-600" />
                            <h2 className="text-xl font-semibold text-gray-900">
                                Activité Quotidienne
                            </h2>
                        </div>
                        <TicketHistogram />
                    </section>
                </div>
            </main>

            {/* Modal de création de contrat */}
            <NewContractModal
                isOpen={isModalOpen}
                onClose={() => setIsModalOpen(false)}
                onContractCreated={handleContractCreated}
            />
        </div>
    );
}
