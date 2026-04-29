class EdgeManager {
    constructor(layerId, canvasManager, nodeManager) {
        this.layer = document.getElementById(layerId);
        this.canvasManager = canvasManager;
        this.nodeManager = nodeManager;
        this.edges = new Map();
        this.selectedEdge = null;
        
        this.isConnecting = false;
        this.connectingFrom = null;
        this.tempEdge = null;
        
        this.init();
    }

    init() {
        this.layer.addEventListener('click', (e) => this.handleClick(e));
        document.addEventListener('mouseup', (e) => this.handleMouseUp(e));
        document.addEventListener('mousemove', (e) => this.handleMouseMove(e));
    }

    startConnection(nodeId, handleType, x, y) {
        if (handleType !== 'output') return;
        
        this.isConnecting = true;
        this.connectingFrom = { nodeId, handleType, x, y };
        
        this.tempEdge = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        this.tempEdge.setAttribute('class', 'temp-edge');
        this.tempEdge.setAttribute('d', this.createPath(x, y, x, y));
        this.layer.appendChild(this.tempEdge);
    }

    handleMouseMove(e) {
        if (!this.isConnecting || !this.tempEdge) return;
        
        const pos = this.canvasManager.getMousePosition(e);
        const path = this.createPath(
            this.connectingFrom.x,
            this.connectingFrom.y,
            pos.x,
            pos.y
        );
        this.tempEdge.setAttribute('d', path);
    }

    handleMouseUp(e) {
        if (!this.isConnecting) return;
        
        const handle = e.target.closest('.node-handle');
        if (handle && handle.dataset.handle === 'input') {
            const targetNodeId = handle.dataset.nodeId;
            
            if (this.connectingFrom.nodeId !== targetNodeId) {
                const existing = this.edges.get(`${this.connectingFrom.nodeId}_${targetNodeId}`);
                if (!existing) {
                    this.createEdge(this.connectingFrom.nodeId, targetNodeId);
                }
            }
        }
        
        this.cancelConnection();
    }

    cancelConnection() {
        this.isConnecting = false;
        this.connectingFrom = null;
        
        if (this.tempEdge) {
            this.tempEdge.remove();
            this.tempEdge = null;
        }
    }

    createPath(x1, y1, x2, y2) {
        const dx = Math.abs(x2 - x1);
        const controlOffset = Math.min(dx * 0.5, 100);
        
        return `M ${x1} ${y1} C ${x1 + controlOffset} ${y1}, ${x2 - controlOffset} ${y2}, ${x2} ${y2}`;
    }

    createEdge(fromNodeId, toNodeId) {
        const edgeId = `${fromNodeId}_${toNodeId}`;
        
        const edge = {
            id: edgeId,
            source: fromNodeId,
            target: toNodeId,
            sourceHandle: 'output',
            targetHandle: 'input'
        };
        
        this.edges.set(edgeId, edge);
        this.renderEdge(edge);
        
        if (window.App) {
            window.App.markUnsaved();
        }
        
        return edge;
    }

    renderEdge(edge) {
        const fromPos = this.nodeManager.getHandlePosition(edge.source, 'output');
        const toPos = this.nodeManager.getHandlePosition(edge.target, 'input');
        
        if (!fromPos || !toPos) return;
        
        const existing = this.layer.querySelector(`[data-edge-id="${edge.id}"]`);
        if (existing) {
            existing.remove();
        }
        
        const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        path.setAttribute('data-edge-id', edge.id);
        path.setAttribute('d', this.createPath(fromPos.x, fromPos.y, toPos.x, toPos.y));
        path.setAttribute('marker-end', 'url(#arrowhead)');
        
        this.layer.appendChild(path);
    }

    updateEdgesForNode(nodeId) {
        this.edges.forEach((edge, id) => {
            if (edge.source === nodeId || edge.target === nodeId) {
                this.renderEdge(edge);
            }
        });
    }

    deleteEdgesForNode(nodeId) {
        const edgesToDelete = [];
        
        this.edges.forEach((edge, id) => {
            if (edge.source === nodeId || edge.target === nodeId) {
                edgesToDelete.push(edge);
            }
        });
        
        edgesToDelete.forEach(edge => {
            this.deleteEdge(edge.id);
        });
    }

    deleteEdge(edgeId) {
        const path = this.layer.querySelector(`[data-edge-id="${edgeId}"]`);
        if (path) {
            path.remove();
        }
        
        this.edges.delete(edgeId);
        
        if (this.selectedEdge === edgeId) {
            this.selectedEdge = null;
        }
        
        if (window.App) {
            window.App.markUnsaved();
        }
    }

    handleClick(e) {
        const path = e.target.closest('path');
        if (path && !path.classList.contains('temp-edge')) {
            const edgeId = path.getAttribute('data-edge-id');
            
            this.selectEdge(edgeId);
            e.stopPropagation();
        }
    }

    selectEdge(edgeId) {
        if (this.selectedEdge) {
            const oldPath = this.layer.querySelector(`[data-edge-id="${this.selectedEdge}"]`);
            if (oldPath) {
                oldPath.classList.remove('selected');
            }
        }
        
        this.selectedEdge = edgeId;
        
        const path = this.layer.querySelector(`[data-edge-id="${edgeId}"]`);
        if (path) {
            path.classList.add('selected');
        }
        
        this.nodeManager.clearSelection();
    }

    clearSelection() {
        if (this.selectedEdge) {
            const path = this.layer.querySelector(`[data-edge-id="${this.selectedEdge}"]`);
            if (path) {
                path.classList.remove('selected');
            }
            this.selectedEdge = null;
        }
    }

    getAllEdges() {
        return Array.from(this.edges.values());
    }

    loadEdges(edges) {
        this.edges.clear();
        const paths = this.layer.querySelectorAll('path[data-edge-id]');
        paths.forEach(p => p.remove());
        
        edges.forEach(edge => {
            this.edges.set(edge.id, edge);
            this.renderEdge(edge);
        });
    }

    getSelectedEdge() {
        return this.selectedEdge ? this.edges.get(this.selectedEdge) : null;
    }

    deleteSelectedEdge() {
        if (this.selectedEdge) {
            this.deleteEdge(this.selectedEdge);
            return true;
        }
        return false;
    }
}

window.EdgeManager = EdgeManager;
