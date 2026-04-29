const API = {
    baseURL: '/api',

    async request(endpoint, options = {}) {
        const url = this.baseURL + endpoint;
        const config = {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        };

        try {
            const response = await fetch(url, config);
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || `HTTP error! status: ${response.status}`);
            }
            
            return data;
        } catch (error) {
            console.error('API request failed:', error);
            throw error;
        }
    },

    async listWorkflows() {
        return this.request('/workflows', {
            method: 'GET'
        });
    },

    async getWorkflow(workflowId) {
        return this.request(`/workflows/${workflowId}`, {
            method: 'GET'
        });
    },

    async createWorkflow(workflowData) {
        return this.request('/workflows', {
            method: 'POST',
            body: JSON.stringify(workflowData)
        });
    },

    async updateWorkflow(workflowId, workflowData) {
        return this.request(`/workflows/${workflowId}`, {
            method: 'PUT',
            body: JSON.stringify(workflowData)
        });
    },

    async deleteWorkflow(workflowId) {
        return this.request(`/workflows/${workflowId}`, {
            method: 'DELETE'
        });
    },

    async runWorkflow(workflowId) {
        return this.request(`/workflows/${workflowId}/run`, {
            method: 'POST'
        });
    },

    async exportWorkflow(workflowId) {
        return this.request(`/workflows/${workflowId}/export`, {
            method: 'POST'
        });
    }
};

if (typeof module !== 'undefined' && module.exports) {
    module.exports = API;
}
