from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import os

from .models import Workflow, Node, Edge, Position, NodeConfig
from .storage import WorkflowStorage

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
storage = WorkflowStorage()


def create_app():
    app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")
    CORS(app)

    @app.route("/")
    def index():
        return send_from_directory(FRONTEND_DIR, "index.html")

    @app.route("/api/workflows", methods=["GET"])
    def list_workflows():
        workflows = storage.list()
        return jsonify([w.to_summary_dict() for w in workflows])

    @app.route("/api/workflows", methods=["POST"])
    def create_workflow():
        data = request.get_json() or {}
        name = data.get("name", "Untitled Workflow")
        
        workflow = Workflow.create(name=name)
        
        if "nodes" in data:
            workflow.nodes = [Node.from_dict(n) for n in data["nodes"]]
        if "edges" in data:
            workflow.edges = [Edge.from_dict(e) for e in data["edges"]]
        
        storage.save(workflow)
        return jsonify(workflow.to_dict()), 201

    @app.route("/api/workflows/<workflow_id>", methods=["GET"])
    def get_workflow(workflow_id):
        workflow = storage.get(workflow_id)
        if not workflow:
            return jsonify({"error": "Workflow not found"}), 404
        return jsonify(workflow.to_dict())

    @app.route("/api/workflows/<workflow_id>", methods=["PUT"])
    def update_workflow(workflow_id):
        workflow = storage.get(workflow_id)
        if not workflow:
            return jsonify({"error": "Workflow not found"}), 404
        
        data = request.get_json() or {}
        
        if "name" in data:
            workflow.name = data["name"]
        if "nodes" in data:
            workflow.nodes = [Node.from_dict(n) for n in data["nodes"]]
        if "edges" in data:
            workflow.edges = [Edge.from_dict(e) for e in data["edges"]]
        
        storage.save(workflow)
        return jsonify(workflow.to_dict())

    @app.route("/api/workflows/<workflow_id>", methods=["DELETE"])
    def delete_workflow(workflow_id):
        success = storage.delete(workflow_id)
        if not success:
            return jsonify({"error": "Workflow not found"}), 404
        return jsonify({"message": "Deleted"}), 200

    @app.route("/api/workflows/<workflow_id>/run", methods=["POST"])
    def run_workflow(workflow_id):
        workflow = storage.get(workflow_id)
        if not workflow:
            return jsonify({"error": "Workflow not found"}), 404
        
        try:
            from .runner import WorkflowRunner
            from .sandbox import CodeSandbox
            
            runner = WorkflowRunner(workflow, CodeSandbox())
            result = runner.run()
            return jsonify(result)
        except ImportError as e:
            return jsonify({
                "status": "error",
                "error": f"Runner not implemented: {e}",
                "logs": []
            }), 500
        except Exception as e:
            return jsonify({
                "status": "error",
                "error": str(e),
                "logs": []
            }), 500

    @app.route("/api/workflows/<workflow_id>/export", methods=["POST"])
    def export_workflow(workflow_id):
        workflow = storage.get(workflow_id)
        if not workflow:
            return jsonify({"error": "Workflow not found"}), 404
        
        try:
            from .exporter import WorkflowExporter
            
            exporter = WorkflowExporter(workflow)
            code = exporter.export()
            
            return jsonify({
                "code": code,
                "filename": f"{workflow.name.replace(' ', '_')}.py"
            })
        except ImportError:
            return jsonify({
                "code": "# Workflow export not yet implemented\n# Workflow: " + workflow.name,
                "filename": f"{workflow.name.replace(' ', '_')}.py"
            })

    return app


def main():
    app = create_app()
    print("Starting low-code platform server on http://0.0.0.0:2222")
    app.run(host="0.0.0.0", port=2222, debug=True)


if __name__ == "__main__":
    main()
