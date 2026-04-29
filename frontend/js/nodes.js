class NodeManager {
    constructor(containerId, canvasManager) {
        this.container = document.getElementById(containerId);
        this.canvasManager = canvasManager;
        this.nodes = new Map();
        this.selectedNode = null;
        this.draggingNode = null;
        this.dragOffsetX = 0;
        this.dragOffsetY = 0;
        
        this.init();
    }

    init() {
        this.container.addEventListener('mousedown', (e) => this.handleMouseDown(e));
        document.addEventListener('mousemove', (e) => this.handleMouseMove(e));
        document.addEventListener('mouseup', (e) => this.handleMouseUp(e));
        
        this.setupDragFromLibrary();
    }

    setupDragFromLibrary() {
        const nodeItems = document.querySelectorAll('.node-item');
        
        nodeItems.forEach(item => {
            item.addEventListener('dragstart', (e) => {
                e.dataTransfer.setData('nodeType', item.dataset.type);
                item.classList.add('dragging');
            });
            
            item.addEventListener('dragend', (e) => {
                item.classList.remove('dragging');
            });
        });
        
        const canvasWrapper = document.getElementById('canvas-wrapper');
        
        canvasWrapper.addEventListener('dragover', (e) => {
            e.preventDefault();
            canvasWrapper.classList.add('drag-over');
        });
        
        canvasWrapper.addEventListener('dragleave', (e) => {
            canvasWrapper.classList.remove('drag-over');
        });
        
        canvasWrapper.addEventListener('drop', (e) => {
            e.preventDefault();
            canvasWrapper.classList.remove('drag-over');
            
            const nodeType = e.dataTransfer.getData('nodeType');
            if (nodeType) {
                const pos = this.canvasManager.getMousePosition(e);
                this.createNode(nodeType, pos.x, pos.y);
            }
        });
    }

    createNode(type, x, y) {
        const id = Utils.generateId();
        
        const node = {
            id: id,
            type: type,
            position: { x: x - 80, y: y - 30 },
            config: this.getDefaultConfig(type),
            label: Utils.getNodeLabel(type)
        };
        
        this.nodes.set(id, node);
        this.renderNode(node);
        this.selectNode(id);
        
        if (window.App) {
            window.App.markUnsaved();
        }
        
        return node;
    }

    getDefaultConfig(type) {
        switch (type) {
            case 'start':
                return {
                    code: '',
                    inputs: {},
                    outputs: {},
                    params: {}
                };
            case 'end':
                return {
                    code: '',
                    inputs: {},
                    outputs: {},
                    params: {}
                };
            case 'python_code':
                return {
                    code: '# Write your Python code here\n# Input variables are available as local variables\n# Assign to result or use return statement\n\nresult = "Hello World"',
                    inputs: {},
                    outputs: {},
                    params: {}
                };
            case 'condition':
                return {
                    code: '',
                    inputs: {},
                    outputs: {},
                    params: {
                        expression: 'value > 10',
                        true_value: {'status': 'high', 'message': 'Value is greater than 10'},
                        false_value: {'status': 'low', 'message': 'Value is 10 or less'}
                    }
                };
            default:
                return {
                    code: '',
                    inputs: {},
                    outputs: {},
                    params: {}
                };
        }
    }

    renderNode(node) {
        const existing = document.getElementById(`node-${node.id}`);
        if (existing) {
            existing.remove();
        }
        
        const nodeEl = document.createElement('div');
        nodeEl.id = `node-${node.id}`;
        nodeEl.className = 'workflow-node';
        nodeEl.dataset.nodeId = node.id;
        
        nodeEl.style.left = `${node.position.x}px`;
        nodeEl.style.top = `${node.position.y}px`;
        
        const icon = Utils.getNodeIcon(node.type);
        const label = node.label || Utils.getNodeLabel(node.type);
        
        let bodyContent = '';
        if (node.type === 'python_code' && node.config.code) {
            const preview = node.config.code.substring(0, 100);
            bodyContent = `<div class="code-preview">${this.escapeHtml(preview)}${node.config.code.length > 100 ? '...' : ''}</div>`;
        } else if (node.type === 'start' && Object.keys(node.config.params).length > 0) {
            const params = Object.entries(node.config.params)
                .map(([k, v]) => `${k}: ${JSON.stringify(v)}`)
                .join(', ');
            bodyContent = `<div class="code-preview">${this.escapeHtml(params)}</div>`;
        }
        
        nodeEl.innerHTML = `
            <div class="node-header">
                <span class="node-header-icon">${icon}</span>
                <span class="node-header-title">${label}</span>
            </div>
            ${bodyContent ? `<div class="node-body">${bodyContent}</div>` : ''}
            <div class="node-handle input" data-handle="input" data-node-id="${node.id}"></div>
            <div class="node-handle output" data-handle="output" data-node-id="${node.id}"></div>
        `;
        
        this.container.appendChild(nodeEl);
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    handleMouseDown(e) {
        const handle = e.target.closest('.node-handle');
        if (handle) {
            const nodeId = handle.dataset.nodeId;
            const handleType = handle.dataset.handle;
            
            if (handleType === 'output' && window.App) {
                const node = this.nodes.get(nodeId);
                if (node) {
                    const rect = handle.getBoundingClientRect();
                    const centerX = rect.left + rect.width / 2;
                    const centerY = rect.top + rect.height / 2;
                    const pos = this.canvasManager.screenToCanvas(centerX, centerY);
                    
                    window.App.edgeManager.startConnection(nodeId, 'output', pos.x, pos.y);
                }
            }
            e.stopPropagation();
            return;
        }
        
        const nodeEl = e.target.closest('.workflow-node');
        if (nodeEl) {
            const nodeId = nodeEl.dataset.nodeId;
            this.selectNode(nodeId);
            
            this.draggingNode = nodeId;
            const node = this.nodes.get(nodeId);
            
            const mousePos = this.canvasManager.getMousePosition(e);
            this.dragOffsetX = mousePos.x - node.position.x;
            this.dragOffsetY = mousePos.y - node.position.y;
            
            e.stopPropagation();
        }
    }

    handleMouseMove(e) {
        if (this.draggingNode) {
            const mousePos = this.canvasManager.getMousePosition(e);
            const node = this.nodes.get(this.draggingNode);
            
            if (node) {
                node.position.x = mousePos.x - this.dragOffsetX;
                node.position.y = mousePos.y - this.dragOffsetY;
                
                const nodeEl = document.getElementById(`node-${this.draggingNode}`);
                if (nodeEl) {
                    nodeEl.style.left = `${node.position.x}px`;
                    nodeEl.style.top = `${node.position.y}px`;
                }
                
                if (window.App && window.App.edgeManager) {
                    window.App.edgeManager.updateEdgesForNode(this.draggingNode);
                }
            }
        }
    }

    handleMouseUp(e) {
        if (this.draggingNode) {
            if (window.App) {
                window.App.markUnsaved();
            }
            this.draggingNode = null;
        }
    }

    selectNode(nodeId) {
        if (this.selectedNode) {
            const oldEl = document.getElementById(`node-${this.selectedNode}`);
            if (oldEl) {
                oldEl.classList.remove('selected');
            }
        }
        
        this.selectedNode = nodeId;
        
        const nodeEl = document.getElementById(`node-${nodeId}`);
        if (nodeEl) {
            nodeEl.classList.add('selected');
        }
        
        if (window.App && window.App.propertiesManager) {
            const node = this.nodes.get(nodeId);
            window.App.propertiesManager.showNodeProperties(node);
        }
    }

    clearSelection() {
        if (this.selectedNode) {
            const nodeEl = document.getElementById(`node-${this.selectedNode}`);
            if (nodeEl) {
                nodeEl.classList.remove('selected');
            }
            this.selectedNode = null;
        }
        
        if (window.App && window.App.propertiesManager) {
            window.App.propertiesManager.showNoSelection();
        }
    }

    deleteNode(nodeId) {
        const nodeEl = document.getElementById(`node-${nodeId}`);
        if (nodeEl) {
            nodeEl.remove();
        }
        
        this.nodes.delete(nodeId);
        
        if (window.App && window.App.edgeManager) {
            window.App.edgeManager.deleteEdgesForNode(nodeId);
        }
        
        if (this.selectedNode === nodeId) {
            this.selectedNode = null;
            if (window.App && window.App.propertiesManager) {
                window.App.propertiesManager.showNoSelection();
            }
        }
        
        if (window.App) {
            window.App.markUnsaved();
        }
    }

    updateNode(nodeId, updates) {
        const node = this.nodes.get(nodeId);
        if (!node) return;
        
        if (updates.config !== undefined) {
            node.config = updates.config;
        }
        if (updates.label !== undefined) {
            node.label = updates.label;
        }
        if (updates.position !== undefined) {
            node.position = updates.position;
        }
        
        this.renderNode(node);
        
        if (this.selectedNode === nodeId) {
            const nodeEl = document.getElementById(`node-${nodeId}`);
            if (nodeEl) {
                nodeEl.classList.add('selected');
            }
        }
        
        if (window.App) {
            window.App.markUnsaved();
        }
    }

    getNode(nodeId) {
        return this.nodes.get(nodeId);
    }

    getAllNodes() {
        return Array.from(this.nodes.values());
    }

    loadNodes(nodes) {
        this.nodes.clear();
        this.container.innerHTML = '';
        
        nodes.forEach(node => {
            this.nodes.set(node.id, node);
            this.renderNode(node);
        });
    }

    getHandlePosition(nodeId, handleType) {
        const node = this.nodes.get(nodeId);
        if (!node) return null;
        
        const nodeEl = document.getElementById(`node-${nodeId}`);
        if (!nodeEl) return null;
        
        const handle = nodeEl.querySelector(`.node-handle.${handleType}`);
        if (!handle) return null;
        
        const rect = handle.getBoundingClientRect();
        const centerX = rect.left + rect.width / 2;
        const centerY = rect.top + rect.height / 2;
        
        return this.canvasManager.screenToCanvas(centerX, centerY);
    }
}

window.NodeManager = NodeManager;
