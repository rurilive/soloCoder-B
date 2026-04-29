class CanvasManager {
    constructor(containerId, wrapperId) {
        this.container = document.getElementById(containerId);
        this.wrapper = document.getElementById(wrapperId);
        
        this.scale = 1;
        this.panX = 0;
        this.panY = 0;
        this.minScale = 0.25;
        this.maxScale = 2;
        
        this.isPanning = false;
        this.lastMouseX = 0;
        this.lastMouseY = 0;
        
        this.isConnecting = false;
        this.connectingFrom = null;
        this.tempEdge = null;
        
        this.init();
    }

    init() {
        this.container.addEventListener('wheel', (e) => this.handleWheel(e));
        this.container.addEventListener('mousedown', (e) => this.handleMouseDown(e));
        document.addEventListener('mousemove', (e) => this.handleMouseMove(e));
        document.addEventListener('mouseup', (e) => this.handleMouseUp(e));
        
        document.getElementById('btn-zoom-in').addEventListener('click', () => this.zoomIn());
        document.getElementById('btn-zoom-out').addEventListener('click', () => this.zoomOut());
        document.getElementById('btn-reset-view').addEventListener('click', () => this.resetView());
        
        this.updateTransform();
    }

    handleWheel(e) {
        e.preventDefault();
        
        const delta = e.deltaY > 0 ? 0.9 : 1.1;
        const newScale = Math.max(this.minScale, Math.min(this.maxScale, this.scale * delta));
        
        const rect = this.container.getBoundingClientRect();
        const mouseX = e.clientX - rect.left;
        const mouseY = e.clientY - rect.top;
        
        const oldScale = this.scale;
        this.scale = newScale;
        
        this.panX = mouseX - (mouseX - this.panX) * (newScale / oldScale);
        this.panY = mouseY - (mouseY - this.panY) * (newScale / oldScale);
        
        this.updateTransform();
    }

    handleMouseDown(e) {
        if (e.target === this.wrapper || 
            e.target.closest('.canvas-wrapper') === this.wrapper && 
            !e.target.closest('.workflow-node') && 
            !e.target.closest('.node-handle') &&
            !e.target.closest('.edge-layer')) {
            
            if (e.button === 0) {
                this.isPanning = true;
                this.lastMouseX = e.clientX;
                this.lastMouseY = e.clientY;
                this.wrapper.classList.add('panning');
                
                if (window.App) {
                    window.App.clearSelection();
                }
            }
        }
    }

    handleMouseMove(e) {
        if (this.isPanning) {
            const dx = e.clientX - this.lastMouseX;
            const dy = e.clientY - this.lastMouseY;
            
            this.panX += dx;
            this.panY += dy;
            
            this.lastMouseX = e.clientX;
            this.lastMouseY = e.clientY;
            
            this.updateTransform();
        }
        
        if (this.isConnecting && this.tempEdge) {
            const rect = this.container.getBoundingClientRect();
            const mouseX = (e.clientX - rect.left - this.panX) / this.scale;
            const mouseY = (e.clientY - rect.top - this.panY) / this.scale;
            
            this.updateTempEdge(mouseX, mouseY);
        }
    }

    handleMouseUp(e) {
        if (this.isPanning) {
            this.isPanning = false;
            this.wrapper.classList.remove('panning');
        }
        
        if (this.isConnecting) {
            this.cancelConnecting();
        }
    }

    updateTransform() {
        this.wrapper.style.transform = `translate(${this.panX}px, ${this.panY}px) scale(${this.scale})`;
    }

    zoomIn() {
        this.scale = Math.min(this.maxScale, this.scale * 1.2);
        this.updateTransform();
    }

    zoomOut() {
        this.scale = Math.max(this.minScale, this.scale / 1.2);
        this.updateTransform();
    }

    resetView() {
        this.scale = 1;
        this.panX = 0;
        this.panY = 0;
        this.updateTransform();
    }

    getMousePosition(e) {
        const rect = this.container.getBoundingClientRect();
        return {
            x: (e.clientX - rect.left - this.panX) / this.scale,
            y: (e.clientY - rect.top - this.panY) / this.scale
        };
    }

    screenToCanvas(screenX, screenY) {
        const rect = this.container.getBoundingClientRect();
        return {
            x: (screenX - rect.left - this.panX) / this.scale,
            y: (screenY - rect.top - this.panY) / this.scale
        };
    }

    canvasToScreen(canvasX, canvasY) {
        return {
            x: canvasX * this.scale + this.panX,
            y: canvasY * this.scale + this.panY
        };
    }

    startConnecting(nodeId, handleType, startX, startY) {
        this.isConnecting = true;
        this.connectingFrom = { nodeId, handleType, x: startX, y: startY };
        
        const edgeLayer = document.getElementById('edge-layer');
        this.tempEdge = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        this.tempEdge.setAttribute('class', 'temp-edge');
        this.tempEdge.setAttribute('d', this.createPath(startX, startY, startX, startY));
        edgeLayer.appendChild(this.tempEdge);
        
        this.wrapper.classList.add('connecting');
    }

    updateTempEdge(endX, endY) {
        if (!this.tempEdge || !this.connectingFrom) return;
        
        const path = this.createPath(
            this.connectingFrom.x, 
            this.connectingFrom.y, 
            endX, 
            endY
        );
        this.tempEdge.setAttribute('d', path);
    }

    cancelConnecting() {
        this.isConnecting = false;
        this.connectingFrom = null;
        
        if (this.tempEdge) {
            this.tempEdge.remove();
            this.tempEdge = null;
        }
        
        this.wrapper.classList.remove('connecting');
    }

    createPath(x1, y1, x2, y2) {
        const dx = Math.abs(x2 - x1);
        const controlOffset = Math.min(dx * 0.5, 100);
        
        return `M ${x1} ${y1} C ${x1 + controlOffset} ${y1}, ${x2 - controlOffset} ${y2}, ${x2} ${y2}`;
    }
}

window.CanvasManager = CanvasManager;
