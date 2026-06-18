/**
 * VesperBot - Dashboard JavaScript
 * Funciones comunes para el dashboard con polling inteligente y caché persistente
 */

// ============================================
// TOAST NOTIFICATIONS
// ============================================

function showToast(message, type = 'success', duration = 4000) {
    let container = document.querySelector('.toast-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'toast-container';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    const icons = {
        success: '✅',
        error: '❌',
        warning: '⚠️',
        info: 'ℹ️'
    };
    
    toast.innerHTML = `
        <span>${icons[type] || ''}</span>
        <span>${message}</span>
        <button class="toast-close">&times;</button>
    `;
    
    container.appendChild(toast);
    
    toast.querySelector('.toast-close').addEventListener('click', function() {
        toast.remove();
    });
    
    setTimeout(() => {
        if (toast.parentNode) {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(100%)';
            toast.style.transition = 'all 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }
    }, duration);
}

// ============================================
// MODAL / POPUP
// ============================================

function showModal(title, message, confirmText = 'Confirmar', cancelText = 'Cancelar', confirmType = 'primary') {
    return new Promise((resolve) => {
        const overlay = document.createElement('div');
        overlay.className = 'modal-overlay';
        
        const modal = document.createElement('div');
        modal.className = 'modal-box';
        
        const buttonClass = confirmType === 'danger' ? 'btn-danger' : 'btn-primary';
        
        modal.innerHTML = `
            <h3>${title}</h3>
            <p>${message}</p>
            <div class="modal-actions">
                <button class="btn-secondary" id="modal-cancel">${cancelText}</button>
                <button class="${buttonClass}" id="modal-confirm">${confirmText}</button>
            </div>
        `;
        
        overlay.appendChild(modal);
        document.body.appendChild(overlay);
        
        const confirmBtn = modal.querySelector('#modal-confirm');
        const cancelBtn = modal.querySelector('#modal-cancel');
        
        function closeModal(result) {
            overlay.remove();
            resolve(result);
        }
        
        confirmBtn.addEventListener('click', () => closeModal(true));
        cancelBtn.addEventListener('click', () => closeModal(false));
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) closeModal(false);
        });
        
        document.addEventListener('keydown', function handler(e) {
            if (e.key === 'Escape') {
                closeModal(false);
                document.removeEventListener('keydown', handler);
            }
        });
    });
}

// ============================================
// API CLIENT CON CACHÉ PERSISTENTE (sessionStorage)
// ============================================

class DashboardAPI {
    constructor() {
        this.cacheKey = 'vesperbot_dashboard_cache';
        this.cacheTimestampKey = 'vesperbot_dashboard_timestamp';
        this.cacheTtl = 10000; // 10 segundos
        this.isFetching = false;
        this.subscribers = [];
        this.endpoint = '/api/dashboard-data';
        this._pendingRefresh = false;
        this._isPageVisible = true;
        this._idleCallbackId = null;
        this._pollingTimeout = null;
        this._initialized = false;
        
        // Cargar caché desde sessionStorage al iniciar
        this.cache = this._loadFromStorage();
        
        // Detectar visibilidad de la pestaña
        document.addEventListener('visibilitychange', () => {
            this._isPageVisible = document.visibilityState === 'visible';
            if (this._isPageVisible) {
                // Si la pestaña se vuelve visible, refrescar inmediatamente
                this.refresh().catch(() => {});
            }
        });
        
        // Si hay datos en caché, notificar inmediatamente a los suscriptores
        if (this.cache && this.cache.data) {
            // Usar requestAnimationFrame para no bloquear el renderizado inicial
            requestAnimationFrame(() => {
                this.notifySubscribers(this.cache.data);
            });
        }
    }

    _loadFromStorage() {
        try {
            const data = sessionStorage.getItem(this.cacheKey);
            const timestamp = parseInt(sessionStorage.getItem(this.cacheTimestampKey) || '0');
            if (data && timestamp) {
                const parsed = JSON.parse(data);
                const now = Date.now();
                if (now - timestamp < this.cacheTtl) {
                    return {
                        data: parsed,
                        timestamp: timestamp
                    };
                }
            }
        } catch (e) {
            console.warn('Error cargando caché de sessionStorage:', e);
        }
        return null;
    }

    _saveToStorage(data) {
        try {
            sessionStorage.setItem(this.cacheKey, JSON.stringify(data));
            sessionStorage.setItem(this.cacheTimestampKey, String(Date.now()));
        } catch (e) {
            console.warn('Error guardando caché en sessionStorage:', e);
        }
    }

    subscribe(callback) {
        this.subscribers.push(callback);
        // Si ya hay datos en caché, notificar inmediatamente
        if (this.cache && this.cache.data) {
            callback(this.cache.data);
        }
        return () => {
            this.subscribers = this.subscribers.filter(cb => cb !== callback);
        };
    }

    notifySubscribers(data) {
        this.subscribers.forEach(callback => {
            try {
                callback(data);
            } catch (e) {
                console.error('Error en suscriptor:', e);
            }
        });
    }

    async getData(forceRefresh = false) {
        const now = Date.now();
        
        // Si la página no está visible y no se fuerza, devolver caché si existe
        if (!this._isPageVisible && !forceRefresh) {
            return this.cache?.data || null;
        }
        
        // Verificar si la caché es válida
        if (!forceRefresh && this.cache && this.cache.data) {
            if (now - this.cache.timestamp < this.cacheTtl) {
                return this.cache.data;
            }
        }

        if (this.isFetching) {
            return new Promise((resolve) => {
                const checkDone = () => {
                    if (!this.isFetching) {
                        resolve(this.cache?.data || null);
                    } else {
                        setTimeout(checkDone, 100);
                    }
                };
                checkDone();
            });
        }

        this.isFetching = true;
        
        try {
            const url = forceRefresh ? `${this.endpoint}?force=true` : this.endpoint;
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            
            // Guardar en caché de memoria y sessionStorage
            this.cache = {
                data: data,
                timestamp: now
            };
            this._saveToStorage(data);
            
            this.isFetching = false;
            this._initialized = true;
            
            this.notifySubscribers(data);
            
            return data;
        } catch (error) {
            console.error('Error fetching dashboard data:', error);
            this.isFetching = false;
            if (this.cache && this.cache.data) {
                return this.cache.data;
            }
            throw error;
        }
    }

    async refresh() {
        if (this._pendingRefresh) {
            return this._pendingRefresh;
        }
        
        this._pendingRefresh = this.getData(true);
        try {
            const result = await this._pendingRefresh;
            return result;
        } finally {
            this._pendingRefresh = null;
        }
    }

    startPolling(interval = 30000) {
        this.cacheTtl = interval;
        this._schedulePoll();
    }
    
    _schedulePoll() {
        // Cancelar cualquier polling pendiente
        if (this._pollingTimeout) {
            clearTimeout(this._pollingTimeout);
            this._pollingTimeout = null;
        }
        if (this._idleCallbackId) {
            cancelIdleCallback(this._idleCallbackId);
            this._idleCallbackId = null;
        }
        
        // Usar requestIdleCallback para no bloquear la UI
        const doPoll = () => {
            // Solo hacer polling si la página es visible
            if (this._isPageVisible) {
                this.getData(false).catch(err => {
                    console.warn('Polling error:', err);
                });
            }
            
            // Programar el siguiente ciclo
            this._pollingTimeout = setTimeout(() => {
                this._schedulePoll();
            }, this.cacheTtl);
        };
        
        // Usar requestIdleCallback si está disponible
        if ('requestIdleCallback' in window) {
            this._idleCallbackId = requestIdleCallback(() => {
                doPoll();
            }, { timeout: 1000 });
        } else {
            // Fallback para navegadores sin requestIdleCallback
            setTimeout(doPoll, 500);
        }
    }

    stopPolling() {
        if (this._pollingTimeout) {
            clearTimeout(this._pollingTimeout);
            this._pollingTimeout = null;
        }
        if (this._idleCallbackId) {
            cancelIdleCallback(this._idleCallbackId);
            this._idleCallbackId = null;
        }
    }
}

// ============================================
// INICIALIZAR LA API GLOBALMENTE
// ============================================

const dashboardAPI = new DashboardAPI();
window.dashboardAPI = dashboardAPI;
window.showToast = showToast;
window.showModal = showModal;
window.formatTime = formatTime;
window.formatDate = formatDate;
window.truncate = truncate;
window.updateBotStatus = updateBotStatus;
window.refreshModerationData = refreshModerationData;
window.forceRefresh = function() {
    dashboardAPI.refresh().then(() => {
        showToast('🔄 Datos actualizados', 'info');
    }).catch(() => {
        showToast('❌ Error al actualizar', 'error');
    });
};

// ============================================
// UTILIDADES
// ============================================

function formatTime(seconds) {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    
    if (hours > 0) {
        return `${hours}h ${minutes}m ${secs}s`;
    } else if (minutes > 0) {
        return `${minutes}m ${secs}s`;
    } else {
        return `${secs}s`;
    }
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString();
}

function truncate(text, length = 50) {
    if (text.length <= length) return text;
    return text.substring(0, length) + '...';
}

// ============================================
// ESTADO DEL BOT (INDEPENDIENTE DEL STREAM)
// ============================================

async function updateBotStatus() {
    try {
        const data = await dashboardAPI.getData();
        const emoji = document.getElementById('status-emoji');
        const text = document.getElementById('status-text');
        
        // Verificar si el bot está conectado
        if (data.status && data.status.connected) {
            emoji.textContent = '🟢';
            emoji.className = 'status-emoji online';
            text.textContent = 'Conectado';
        } else {
            emoji.textContent = '🔴';
            emoji.className = 'status-emoji offline';
            text.textContent = 'Desconectado';
        }
        
        return data;
    } catch (error) {
        console.error('Error actualizando estado:', error);
        const emoji = document.getElementById('status-emoji');
        const text = document.getElementById('status-text');
        if (emoji) {
            emoji.textContent = '🔴';
            emoji.className = 'status-emoji offline';
        }
        if (text) text.textContent = 'Desconectado';
    }
}

// ============================================
// REFRESH MODERATION DATA
// ============================================

function refreshModerationData() {
    dashboardAPI.refresh().then(() => {
        showToast('🔄 Datos de moderación actualizados', 'info');
    }).catch(() => {
        showToast('❌ Error al actualizar datos', 'error');
    });
}

// ============================================
// INICIALIZACIÓN
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    // Iniciar polling (30 segundos)
    dashboardAPI.startPolling(30000);
    // Actualizar estado del bot (usando caché si existe)
    updateBotStatus();
    console.log('🕯️ VesperBot Dashboard inicializado con caché persistente');
});

// ============================================
// EXPORTAR FUNCIONES
// ============================================

window.apiFetch = dashboardAPI.getData.bind(dashboardAPI);
window.dashboardAPI = dashboardAPI;