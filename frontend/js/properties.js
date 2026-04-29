class PropertiesManager {
    constructor(nodeManager, edgeManager) {
        this.nodeManager = nodeManager;
        this.edgeManager = edgeManager;
        this.currentNode = null;
        
        this.init();
    }

    init() {
        document.getElementById('prop-node-name').addEventListener('input', (e) => {
            this.updateNodeName(e.target.value);
        });
        
        document.getElementById('prop-condition-expr').addEventListener('input', (e) => {
            this.updateConditionParam('expression', e.target.value);
        });
        
        document.getElementById('prop-true-value').addEventListener('input', (e) => {
            this.updateConditionParam('true_value', Utils.parseJSON(e.target.value));
        });
        
        document.getElementById('prop-false-value').addEventListener('input', (e) => {
            this.updateConditionParam('false_value', Utils.parseJSON(e.target.value));
        });
        
        const codeEditor = document.getElementById('code-editor');
        codeEditor.addEventListener('input', Utils.debounce((e) => {
            this.updateNodeCode(e.target.value);
        }, 300));
        
        document.getElementById('btn-delete-node').addEventListener('click', () => {
            this.deleteCurrentNode();
        });
        
        document.getElementById('btn-add-param').addEventListener('click', () => {
            this.addParamRow();
        });
        
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Delete' || e.key === 'Backspace') {
                const focused = document.activeElement;
                if (focused.tagName === 'INPUT' || focused.tagName === 'TEXTAREA') {
                    return;
                }
                
                if (this.nodeManager.selectedNode) {
                    this.deleteCurrentNode();
                    e.preventDefault();
                } else if (this.edgeManager.getSelectedEdge()) {
                    this.edgeManager.deleteSelectedEdge();
                    e.preventDefault();
                }
            }
        });
    }

    showNoSelection() {
        document.getElementById('no-selection').style.display = 'flex';
        document.getElementById('node-properties').style.display = 'none';
        this.currentNode = null;
    }

    showNodeProperties(node) {
        if (!node) {
            this.showNoSelection();
            return;
        }
        
        this.currentNode = node;
        
        document.getElementById('no-selection').style.display = 'none';
        document.getElementById('node-properties').style.display = 'block';
        
        document.getElementById('prop-node-id').value = node.id;
        document.getElementById('prop-node-type').value = node.type;
        document.getElementById('prop-node-name').value = node.label || Utils.getNodeLabel(node.type);
        
        this.hideAllGroups();
        
        switch (node.type) {
            case 'start':
                this.showGroup('group-node-name');
                this.showGroup('group-start-params');
                this.renderParams(node.config.params || {});
                break;
            case 'end':
                this.showGroup('group-node-name');
                break;
            case 'python_code':
                this.showGroup('group-node-name');
                this.showGroup('group-code-editor');
                document.getElementById('code-editor').value = node.config.code || '';
                break;
            case 'condition':
                this.showGroup('group-node-name');
                this.showGroup('group-condition');
                const params = node.config.params || {};
                document.getElementById('prop-condition-expr').value = params.expression || '';
                document.getElementById('prop-true-value').value = JSON.stringify(params.true_value !== undefined ? params.true_value : '');
                document.getElementById('prop-false-value').value = JSON.stringify(params.false_value !== undefined ? params.false_value : '');
                break;
        }
    }

    hideAllGroups() {
        document.getElementById('group-node-name').style.display = 'none';
        document.getElementById('group-start-params').style.display = 'none';
        document.getElementById('group-code-editor').style.display = 'none';
        document.getElementById('group-condition').style.display = 'none';
    }

    showGroup(groupId) {
        document.getElementById(groupId).style.display = 'block';
    }

    updateNodeName(name) {
        if (!this.currentNode) return;
        
        this.nodeManager.updateNode(this.currentNode.id, {
            label: name
        });
        
        this.currentNode.label = name;
    }

    updateNodeCode(code) {
        if (!this.currentNode || this.currentNode.type !== 'python_code') return;
        
        const newConfig = { ...this.currentNode.config, code: code };
        this.nodeManager.updateNode(this.currentNode.id, {
            config: newConfig
        });
        
        this.currentNode.config = newConfig;
    }

    updateConditionParam(key, value) {
        if (!this.currentNode || this.currentNode.type !== 'condition') return;
        
        const newParams = { ...this.currentNode.config.params, [key]: value };
        const newConfig = { ...this.currentNode.config, params: newParams };
        
        this.nodeManager.updateNode(this.currentNode.id, {
            config: newConfig
        });
        
        this.currentNode.config = newConfig;
    }

    renderParams(params) {
        const paramsList = document.getElementById('params-list');
        paramsList.innerHTML = '';
        
        Object.entries(params).forEach(([key, value]) => {
            this.addParamRow(key, value);
        });
    }

    addParamRow(key = '', value = '') {
        const paramsList = document.getElementById('params-list');
        const row = document.createElement('div');
        row.className = 'param-row';
        
        row.innerHTML = `
            <input type="text" class="param-input param-key" value="${this.escapeHtml(key)}" placeholder="Key">
            <input type="text" class="param-input param-value" value="${this.escapeHtml(JSON.stringify(value))}" placeholder="Value (JSON)">
            <button class="btn-remove-param" type="button">×</button>
        `;
        
        const keyInput = row.querySelector('.param-key');
        const valueInput = row.querySelector('.param-value');
        const removeBtn = row.querySelector('.btn-remove-param');
        
        const updateParams = () => {
            this.collectParams();
        };
        
        keyInput.addEventListener('input', updateParams);
        valueInput.addEventListener('input', updateParams);
        
        removeBtn.addEventListener('click', () => {
            row.remove();
            this.collectParams();
        });
        
        paramsList.appendChild(row);
    }

    collectParams() {
        if (!this.currentNode || this.currentNode.type !== 'start') return;
        
        const params = {};
        const rows = document.querySelectorAll('.param-row');
        
        rows.forEach(row => {
            const key = row.querySelector('.param-key').value.trim();
            const valueStr = row.querySelector('.param-value').value.trim();
            
            if (key) {
                try {
                    params[key] = JSON.parse(valueStr);
                } catch (e) {
                    params[key] = valueStr;
                }
            }
        });
        
        const newParams = { ...this.currentNode.config.params, ...params };
        const newConfig = { ...this.currentNode.config, params: newParams };
        
        this.nodeManager.updateNode(this.currentNode.id, {
            config: newConfig
        });
        
        this.currentNode.config = newConfig;
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    deleteCurrentNode() {
        if (!this.currentNode) return;
        
        const nodeId = this.currentNode.id;
        this.nodeManager.deleteNode(nodeId);
        this.showNoSelection();
    }
}

window.PropertiesManager = PropertiesManager;
