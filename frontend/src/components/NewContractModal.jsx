import { useState, Fragment } from 'react';
import { Dialog, Transition } from '@headlessui/react';
import { X, Calendar, DollarSign, Building, FileText, Upload } from 'lucide-react';
import contractsService from '../services/contractsService';

export default function NewContractModal({ isOpen, onClose, onContractCreated }) {
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState('');

    // Initial state
    const initialFormState = {
        name: '',
        supplier: '',
        amount: '',
        start_date: '',
        end_date: '',
        notice_period_days: 90,
        sharepoint_file_url: ''
    };

    const [formData, setFormData] = useState(initialFormState);

    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({
            ...prev,
            [name]: value
        }));
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setIsLoading(true);

        // Basic validation
        if (new Date(formData.end_date) <= new Date(formData.start_date)) {
            setError('La date de fin doit être postérieure à la date de début.');
            setIsLoading(false);
            return;
        }

        try {
            await contractsService.create({
                ...formData,
                amount: parseFloat(formData.amount),
                notice_period_days: parseInt(formData.notice_period_days)
            });

            // Reset and close
            setFormData(initialFormState);
            onContractCreated();
            onClose();
        } catch (err) {
            console.error('Erreur création contrat:', err);
            setError(err.response?.data?.detail || "Une erreur est survenue lors de la création du contrat.");
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <Transition appear show={isOpen} as={Fragment}>
            <Dialog as="div" className="relative z-50" onClose={onClose}>
                <Transition.Child
                    as={Fragment}
                    enter="ease-out duration-300"
                    enterFrom="opacity-0"
                    enterTo="opacity-100"
                    leave="ease-in duration-200"
                    leaveFrom="opacity-100"
                    leaveTo="opacity-0"
                >
                    <div className="fixed inset-0 bg-black/25 backdrop-blur-sm" />
                </Transition.Child>

                <div className="fixed inset-0 overflow-y-auto">
                    <div className="flex min-h-full items-center justify-center p-4 text-center">
                        <Transition.Child
                            as={Fragment}
                            enter="ease-out duration-300"
                            enterFrom="opacity-0 scale-95"
                            enterTo="opacity-100 scale-100"
                            leave="ease-in duration-200"
                            leaveFrom="opacity-100 scale-100"
                            leaveTo="opacity-0 scale-95"
                        >
                            <Dialog.Panel className="w-full max-w-2xl transform overflow-hidden rounded-2xl bg-white p-6 text-left align-middle shadow-xl transition-all">
                                <div className="flex justify-between items-center mb-6 border-b pb-4">
                                    <Dialog.Title as="h3" className="text-xl font-semibold leading-6 text-gray-900 flex items-center gap-2">
                                        <FileText className="w-5 h-5 text-primary-600" />
                                        Nouveau Contrat
                                    </Dialog.Title>
                                    <button
                                        onClick={onClose}
                                        className="text-gray-400 hover:text-gray-500 transition-colors"
                                    >
                                        <X className="w-5 h-5" />
                                    </button>
                                </div>

                                {error && (
                                    <div className="mb-4 p-4 bg-red-50 text-red-700 rounded-lg text-sm border border-red-200">
                                        {error}
                                    </div>
                                )}

                                <form onSubmit={handleSubmit} className="space-y-6">
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                        {/* Nom du contrat */}
                                        <div className="col-span-2">
                                            <label className="block text-sm font-medium text-gray-700 mb-1">Nom du contrat *</label>
                                            <div className="relative">
                                                <FileText className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                                                <input
                                                    type="text"
                                                    name="name"
                                                    required
                                                    className="pl-10 w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
                                                    placeholder="Ex: Maintenance Serveurs 2024"
                                                    value={formData.name}
                                                    onChange={handleChange}
                                                />
                                            </div>
                                        </div>

                                        {/* Fournisseur */}
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">Fournisseur *</label>
                                            <div className="relative">
                                                <Building className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                                                <input
                                                    type="text"
                                                    name="supplier"
                                                    required
                                                    className="pl-10 w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
                                                    placeholder="Ex: Microsoft"
                                                    value={formData.supplier}
                                                    onChange={handleChange}
                                                />
                                            </div>
                                        </div>

                                        {/* Montant */}
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">Montant annuel (€) *</label>
                                            <div className="relative">
                                                <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                                                <input
                                                    type="number"
                                                    name="amount"
                                                    required
                                                    step="0.01"
                                                    min="0"
                                                    className="pl-10 w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
                                                    placeholder="0.00"
                                                    value={formData.amount}
                                                    onChange={handleChange}
                                                />
                                            </div>
                                        </div>

                                        {/* Date de début */}
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">Date de début *</label>
                                            <div className="relative">
                                                <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                                                <input
                                                    type="date"
                                                    name="start_date"
                                                    required
                                                    className="pl-10 w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
                                                    value={formData.start_date}
                                                    onChange={handleChange}
                                                />
                                            </div>
                                        </div>

                                        {/* Date de fin */}
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">Date de fin *</label>
                                            <div className="relative">
                                                <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                                                <input
                                                    type="date"
                                                    name="end_date"
                                                    required
                                                    className="pl-10 w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
                                                    value={formData.end_date}
                                                    onChange={handleChange}
                                                />
                                            </div>
                                        </div>

                                        {/* Préavis */}
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">Préavis (jours) *</label>
                                            <input
                                                type="number"
                                                name="notice_period_days"
                                                required
                                                min="0"
                                                className="w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
                                                value={formData.notice_period_days}
                                                onChange={handleChange}
                                            />
                                        </div>

                                        {/* SharePoint URL */}
                                        <div className="col-span-2">
                                            <label className="block text-sm font-medium text-gray-700 mb-1">Lien SharePoint (Optionnel)</label>
                                            <div className="relative">
                                                <Upload className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                                                <input
                                                    type="url"
                                                    name="sharepoint_file_url"
                                                    className="pl-10 w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
                                                    placeholder="https://sharepoint.com/..."
                                                    value={formData.sharepoint_file_url}
                                                    onChange={handleChange}
                                                />
                                            </div>
                                        </div>
                                    </div>

                                    <div className="mt-8 flex justify-end gap-3 border-t pt-4">
                                        <button
                                            type="button"
                                            className="inline-flex justify-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
                                            onClick={onClose}
                                            disabled={isLoading}
                                        >
                                            Annuler
                                        </button>
                                        <button
                                            type="submit"
                                            className="inline-flex justify-center rounded-md border border-transparent bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
                                            disabled={isLoading}
                                        >
                                            {isLoading ? 'Création...' : 'Créer le contrat'}
                                        </button>
                                    </div>
                                </form>
                            </Dialog.Panel>
                        </Transition.Child>
                    </div>
                </div>
            </Dialog>
        </Transition>
    );
}
