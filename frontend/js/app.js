class App {
    constructor() {
        this.currentWorkflowId = null;
        this.currentWorkflow = null;
        this.isUnsaved = false;
        this.isRunning = false;
        
        this.canvasManager = null;
        this.nodeManager = null;
        this.edgeManager = null;
        this.propertiesManager = null;
        
        this.init();
    }

    init() {
        this.canvasManager = new CanvasManager('canvas-container', 'canvas-wrapper');
        this.nodeManager = new NodeManager('node-layer', this.canvasManager);
        this.edgeManager = new EdgeManager('edge-layer', this.canvasManager, this.nodeManager);
        this.propertiesManager = new PropertiesManager(this.nodeManager, this.edgeManager);
        
        this.setupEventListeners();
        this.loadWorkflows();
        this.createNewWorkflow();
    }

    setupEventListeners() {
        document.getElementById('btn-new').addEventListener('click', () => {
            this.createNewWorkflow();
        });
        
        document.getElementById('btn-save').addEventListener('click', () => {
            this.saveWorkflow();
        });
        
        document.getElementById('btn-run').addEventListener('click', () => {
            this.runWorkflow();
        });
        
        document.getElementById('btn-export').addEventListener('click', () => {
            this.exportWorkflow();
        });
        
        document.getElementById('workflow-selector').addEventListener('change', (e) => {
            const workflowId = e.target.value;
            if (workflowId) {
                this.loadWorkflow(workflowId);
            }
        });
        
        document.querySelectorAll('.output-tab').forEach(tab => {
            tab.addEventListener('click', (e) => {
                this.switchOutputTab(e.target.dataset.tab);
            });
        });
        
        document.getElementById('btn-close-output').addEventListener('click', () => {
            this.hideOutputPanel();
        });
        
        window.addEventListener('beforeunload', (e) => {
            if (this.isUnsaved) {
                e.preventDefault();
                e.returnValue = '您有未保存的更改，确定要离开吗？';
                return e.returnValue;
            }
        });
    }

    async loadWorkflows() {
        try {
            const workflows = await API.listWorkflows();
            this.updateWorkflowSelector(workflows);
        } catch (error) {
            console.error('Failed to load workflows:', error);
            Utils.showToast('加载工作流列表失败', 'error');
        }
    }

    updateWorkflowSelector(workflows) {
        const selector = document.getElementById('workflow-selector');
        selector.innerHTML = '<option value="">-- 选择工作流 --</option>';
        
        workflows.forEach(workflow => {
            const option = document.createElement('option');
            option.value = workflow.id;
            option.textContent = workflow.name;
            option.selected = workflow.id === this.currentWorkflowId;
            selector.appendChild(option);
        });
    }

    createNewWorkflow() {
        if (this.isUnsaved && !confirm('您有未保存的更改，确定要新建工作流吗？')) {
            return;
        }
        
        this.currentWorkflowId = null;
        this.currentWorkflow = {
            id: null,
            name: '新建工作流',
            nodes: [],
            edges: []
        };
        
        this.nodeManager.loadNodes([]);
        this.edgeManager.loadEdges([]);
        this.nodeManager.clearSelection();
        
        this.isUnsaved = false;
        this.updateTitle();
        
        Utils.showToast('已创建新工作流', 'info');
    }

    async loadWorkflow(workflowId) {
        if (this.isUnsaved && !confirm('您有未保存的更改，确定要加载其他工作流吗？')) {
            document.getElementById('workflow-selector').value = this.currentWorkflowId || '';
            return;
        }
        
        try {
            const workflow = await API.getWorkflow(workflowId);
            
            this.currentWorkflowId = workflowId;
            this.currentWorkflow = workflow;
            
            this.nodeManager.loadNodes(workflow.nodes || []);
            this.edgeManager.loadEdges(workflow.edges || []);
            this.nodeManager.clearSelection();
            
            this.isUnsaved = false;
            this.updateTitle();
            
            Utils.showToast('工作流已加载', 'success');
        } catch (error) {
            console.error('Failed to load workflow:', error);
            Utils.showToast('加载工作流失败: ' + error.message, 'error');
        }
    }

    async saveWorkflow() {
        const workflowData = this.collectWorkflowData();
        
        try {
            if (this.currentWorkflowId) {
                const result = await API.updateWorkflow(this.currentWorkflowId, workflowData);
                this.currentWorkflow = result;
            } else {
                const result = await API.createWorkflow(workflowData);
                this.currentWorkflowId = result.id;
                this.currentWorkflow = result;
            }
            
            this.isUnsaved = false;
            this.updateTitle();
            await this.loadWorkflows();
            
            Utils.showToast('工作流已保存', 'success');
        } catch (error) {
            console.error('Failed to save workflow:', error);
            Utils.showToast('保存失败: ' + error.message, 'error');
        }
    }

    collectWorkflowData() {
        const nodes = this.nodeManager.getAllNodes();
        const edges = this.edgeManager.getAllEdges();
        
        return {
            name: this.currentWorkflow?.name || '新建工作流',
            nodes: nodes,
            edges: edges
        };
    }

    async runWorkflow() {
        if (!this.currentWorkflowId) {
            Utils.showToast('请先保存工作流', 'error');
            return;
        }
        
        if (this.isRunning) {
            return;
        }
        
        this.isRunning = true;
        const runBtn = document.getElementById('btn-run');
        runBtn.classList.add('running');
        runBtn.disabled = true;
        
        this.showOutputPanel();
        this.clearOutput();
        this.appendLog('▶️ 开始执行工作流...\n');
        
        try {
            const result = await API.runWorkflow(this.currentWorkflowId);
            
            if (result.status === 'success') {
                this.appendLog('✅ 执行成功！\n');
                
                if (result.logs) {
                    result.logs.forEach(log => {
                        this.appendLog(log + '\n');
                    });
                }
                
                if (result.result !== undefined) {
                    this.setOutputResult(result.result);
                }
                
                Utils.showToast('执行成功', 'success');
            } else {
                this.appendLog('❌ 执行失败\n');
                if (result.error) {
                    this.setOutputError(result.error);
                    this.appendLog('错误: ' + result.error + '\n');
                }
                Utils.showToast('执行失败', 'error');
            }
        } catch (error) {
            this.appendLog('❌ 请求失败: ' + error.message + '\n');
            this.setOutputError(error.message);
            Utils.showToast('执行请求失败', 'error');
        } finally {
            this.isRunning = false;
            runBtn.classList.remove('running');
            runBtn.disabled = false;
        }
    }

    async exportWorkflow() {
        if (!this.currentWorkflowId) {
            Utils.showToast('请先保存工作流', 'error');
            return;
        }
        
        try {
            const result = await API.exportWorkflow(this.currentWorkflowId);
            
            if (result.filename && result.code) {
                const blob = new Blob([result.code], { type: 'text/plain' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = result.filename;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
                
                Utils.showToast('导出成功: ' + result.filename, 'success');
            } else {
                Utils.showToast('导出数据格式错误', 'error');
            }
        } catch (error) {
            console.error('Export failed:', error);
            Utils.showToast('导出失败: ' + error.message, 'error');
        }
    }

    markUnsaved() {
        this.isUnsaved = true;
        this.updateTitle();
    }

    clearSelection() {
        this.nodeManager.clearSelection();
        this.edgeManager.clearSelection();
    }

    updateTitle() {
        let title = '低代码平台';
        if (this.currentWorkflow) {
            title = this.currentWorkflow.name;
            if (this.isUnsaved) {
                title += ' (未保存)';
            }
        }
        document.title = title;
    }

    showOutputPanel() {
        document.getElementById('output-panel').classList.add('open');
    }

    hideOutputPanel() {
        document.getElementById('output-panel').classList.remove('open');
    }

    clearOutput() {
        document.querySelector('#output-logs .output-text').textContent = '';
        document.querySelector('#output-result .output-text').textContent = '';
        document.querySelector('#output-error .output-text').textContent = '';
    }

    appendLog(text) {
        const logOutput = document.querySelector('#output-logs .output-text');
        logOutput.textContent += text;
        logOutput.scrollTop = logOutput.scrollHeight;
        this.switchOutputTab('logs');
    }

    setOutputResult(data) {
        const resultOutput = document.querySelector('#output-result .output-text');
        resultOutput.textContent = Utils.formatJSON(data, 2);
        this.switchOutputTab('result');
    }

    setOutputError(error) {
        const errorOutput = document.querySelector('#output-error .output-text');
        errorOutput.textContent = String(error);
        errorOutput.classList.add('error');
    }

    switchOutputTab(tabName) {
        document.querySelectorAll('.output-tab').forEach(tab => {
            tab.classList.toggle('active', tab.dataset.tab === tabName);
        });
        
        document.querySelectorAll('.output-tab-content').forEach(content => {
            content.classList.toggle('active', content.id === `output-${tabName}`);
        });
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.App = new App();
});
