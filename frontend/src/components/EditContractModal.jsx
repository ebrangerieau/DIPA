import { useState, useEffect, Fragment } from 'react';
import { Dialog, Transition } from '@headlessui/react';
import { X, Calendar, DollarSign, Building, FileText, Upload, Edit } from 'lucide-react';
import contractsService from '../services/contractsService';

export default function EditContractModal({ isOpen, onClose, onContractUpdated, contract }) {
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState('');

    // Initial state
    const initialFormState = {
        name: '',
        supplier: '',
        amount: '',
        duration_months: 12,
        start_date: '',
        end_date: '',
        notice_period_days: 90,
        sharepoint_file_url: ''
    };

    const [formData, setFormData] = useState(initialFormState);

    // Charger les données du contrat quand le modal s'ouvre
    useEffect(() => {
        if (contract && isOpen) {
            setFormData({
                name: contract.name || '',
                supplier: contract.supplier || '',
                amount: contract.amount || '',
                duration_months: contract.duration_months || 12,
                start_date: contract.start_date || '',
                end_date: contract.end_date || '',
                notice_period_days: contract.notice_period_days || 90,
                sharepoint_file_url: contract.sharepoint_file_url || ''
            });
        }
    }, [contract, isOpen]);

    // Calcul du coût annuel moyen
    const annualCost = formData.amount && formData.duration_months
        ? (parseFloat(formData.amount) / (parseInt(formData.duration_months) / 12)).toFixed(2)
        : '0.00';

    // Calcul automatique de la date de fin en fonction de la date de début et de la durée
    useEffect(() => {
        if (formData.start_date && formData.duration_months) {
            const startDate = new Date(formData.start_date);
            const endDate = new Date(startDate);
            endDate.setMonth(endDate.getMonth() + parseInt(formData.duration_months));

            // Formater la date au format YYYY-MM-DD pour l'input date
            const formattedEndDate = endDate.toISOString().split('T')[0];

            setFormData(prev => ({
                ...prev,
                end_date: formattedEndDate
            }));
        }
    }, [formData.start_date, formData.duration_months]);

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
            await contractsService.update(contract.id, {
                ...formData,
                amount: parseFloat(formData.amount),
                duration_months: parseInt(formData.duration_months),
                notice_period_days: parseInt(formData.notice_period_days)
            });

            onContractUpdated();
            onClose();
        } catch (err) {
            console.error('Erreur modification contrat:', err);
            setError(err.response?.data?.detail || "Une erreur est survenue lors de la modification du contrat.");
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
                                        <Edit className="w-5 h-5 text-primary-600" />
                                        Modifier le Contrat
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

                                        {/* Montant total */}
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">Montant total (€) *</label>
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

                                        {/* Durée du contrat */}
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">Durée (mois) *</label>
                                            <input
                                                type="number"
                                                name="duration_months"
                                                required
                                                min="1"
                                                max="120"
                                                className="w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
                                                placeholder="12"
                                                value={formData.duration_months}
                                                onChange={handleChange}
                                            />
                                            <p className="mt-1 text-xs text-gray-500">
                                                {formData.duration_months ? `${(formData.duration_months / 12).toFixed(1)} an(s)` : ''}
                                            </p>
                                        </div>

                                        {/* Coût annuel moyen calculé */}
                                        {formData.amount && formData.duration_months && (
                                            <div className="col-span-2">
                                                <div className="bg-primary-50 border border-primary-200 rounded-lg p-3">
                                                    <div className="flex items-center justify-between">
                                                        <span className="text-sm font-medium text-primary-900">
                                                            Coût annuel moyen :
                                                        </span>
                                                        <span className="text-lg font-semibold text-primary-700">
                                                            {annualCost} €/an
                                                        </span>
                                                    </div>
                                                    <p className="mt-1 text-xs text-primary-600">
                                                        Calculé sur {(formData.duration_months / 12).toFixed(1)} année(s)
                                                    </p>
                                                </div>
                                            </div>
                                        )}

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

                                        {/* Date de fin (calculée automatiquement) */}
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                                Date de fin *
                                                <span className="ml-2 text-xs font-normal text-gray-500">(calculée automatiquement)</span>
                                            </label>
                                            <div className="relative">
                                                <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                                                <input
                                                    type="date"
                                                    name="end_date"
                                                    required
                                                    disabled
                                                    className="pl-10 w-full rounded-md border-gray-300 shadow-sm bg-gray-50 text-gray-600 cursor-not-allowed sm:text-sm"
                                                    value={formData.end_date}
                                                    readOnly
                                                />
                                            </div>
                                            <p className="mt-1 text-xs text-gray-500">
                                                Calculée à partir de la date de début + {formData.duration_months} mois
                                            </p>
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
                                            {isLoading ? 'Modification...' : 'Enregistrer les modifications'}
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
