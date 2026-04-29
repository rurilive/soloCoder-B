const Utils = {
    generateId() {
        return 'id_' + Math.random().toString(36).substr(2, 9);
    },

    deepClone(obj) {
        return JSON.parse(JSON.stringify(obj));
    },

    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    formatJSON(obj, indent = 2) {
        try {
            return JSON.stringify(obj, null, indent);
        } catch (e) {
            return String(obj);
        }
    },

    parseJSON(str) {
        try {
            return JSON.parse(str);
        } catch (e) {
            return str;
        }
    },

    showToast(message, type = 'info') {
        const existingToast = document.querySelector('.toast');
        if (existingToast) {
            existingToast.remove();
        }

        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        document.body.appendChild(toast);

        requestAnimationFrame(() => {
            toast.classList.add('show');
        });

        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 300);
        }, 3000);
    },

    getNodeLabel(type) {
        const labels = {
            'start': 'Start',
            'end': 'End',
            'python_code': 'Python Code',
            'condition': 'Condition'
        };
        return labels[type] || type;
    },

    getNodeIcon(type) {
        const icons = {
            'start': '🚀',
            'end': '🏁',
            'python_code': '🐍',
            'condition': '🔀'
        };
        return icons[type] || '📦';
    },

    getNodeColor(type) {
        const colors = {
            'start': '#10b981',
            'end': '#f59e0b',
            'python_code': '#3b82f6',
            'condition': '#8b5cf6'
        };
        return colors[type] || '#6b7280';
    }
};

if (typeof module !== 'undefined' && module.exports) {
    module.exports = Utils;
}
