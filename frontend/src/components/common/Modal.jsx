/**
 * Fenêtre modale accessible (Headless UI) : focus piégé, fermeture par Échap.
 */
import { Dialog, DialogBackdrop, DialogPanel, DialogTitle } from '@headlessui/react';
import { X } from 'lucide-react';

const WIDTHS = {
    sm: 'max-w-md',
    md: 'max-w-lg',
    lg: 'max-w-2xl',
    xl: 'max-w-4xl',
};

export default function Modal({ open, onClose, title, icon: Icon, children, footer, size = 'lg', dismissible = true }) {
    const handleClose = dismissible ? onClose : () => {};

    return (
        <Dialog open={open} onClose={handleClose} className="relative z-50">
            <DialogBackdrop
                transition
                className="fixed inset-0 bg-gray-900/40 backdrop-blur-[1px] transition-opacity duration-200 data-[closed]:opacity-0"
            />
            <div className="fixed inset-0 overflow-y-auto">
                <div className="flex min-h-full items-center justify-center p-4">
                    <DialogPanel
                        transition
                        className={`w-full ${WIDTHS[size]} rounded-xl bg-white shadow-xl transition duration-200 data-[closed]:scale-95 data-[closed]:opacity-0`}
                    >
                        <div className="flex items-start justify-between gap-4 border-b border-gray-200 px-6 py-4">
                            <DialogTitle className="flex min-w-0 items-center gap-2 text-lg font-semibold text-gray-900">
                                {Icon && <Icon className="h-5 w-5 flex-shrink-0 text-primary-600" />}
                                <span className="truncate">{title}</span>
                            </DialogTitle>
                            {dismissible && (
                                <button type="button" onClick={onClose} className="btn-ghost -mr-2" aria-label="Fermer">
                                    <X className="h-5 w-5" />
                                </button>
                            )}
                        </div>
                        <div className="px-6 py-5">{children}</div>
                        {footer && (
                            <div className="flex flex-wrap justify-end gap-3 border-t border-gray-200 bg-gray-50 px-6 py-4 rounded-b-xl">
                                {footer}
                            </div>
                        )}
                    </DialogPanel>
                </div>
            </div>
        </Dialog>
    );
}
