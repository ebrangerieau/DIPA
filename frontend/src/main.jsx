import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import './index.css'
import App from './App.jsx'
import { AuthProvider } from './context/AuthContext.jsx'

// Configuration de React Query
const queryClient = new QueryClient({
    defaultOptions: {
        queries: {
            refetchOnWindowFocus: false,
            retry: (failureCount, error) => {
                // Inutile de réessayer une erreur d'authentification, de droits ou de validation
                const status = error?.response?.status;
                if (status && status < 500) return false;
                return failureCount < 1;
            },
            staleTime: 5 * 60 * 1000, // 5 minutes (aligné sur le cache Zammad du backend)
        },
    },
})

createRoot(document.getElementById('root')).render(
    <StrictMode>
        <QueryClientProvider client={queryClient}>
            <AuthProvider>
                <App />
            </AuthProvider>
        </QueryClientProvider>
    </StrictMode>,
)
