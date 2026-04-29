import os
import json
from typing import List, Optional
from .models import Workflow


class WorkflowStorage:
    def __init__(self, data_dir: Optional[str] = None):
        if data_dir is None:
            data_dir = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "data",
                "workflows"
            )
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)

    def _get_workflow_path(self, workflow_id: str) -> str:
        return os.path.join(self.data_dir, f"{workflow_id}.json")

    def list(self) -> List[Workflow]:
        workflows = []
        if not os.path.exists(self.data_dir):
            return workflows

        for filename in os.listdir(self.data_dir):
            if not filename.endswith(".json"):
                continue

            filepath = os.path.join(self.data_dir, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    workflows.append(Workflow.from_dict(data))
            except (json.JSONDecodeError, KeyError):
                continue

        workflows.sort(key=lambda w: w.updated_at, reverse=True)
        return workflows

    def get(self, workflow_id: str) -> Optional[Workflow]:
        filepath = self._get_workflow_path(workflow_id)
        if not os.path.exists(filepath):
            return None

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                return Workflow.from_dict(data)
        except (json.JSONDecodeError, KeyError):
            return None

    def save(self, workflow: Workflow) -> Workflow:
        workflow.update_timestamp()
        filepath = self._get_workflow_path(workflow.id)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(workflow.to_dict(), f, indent=2, ensure_ascii=False)

        return workflow

    def delete(self, workflow_id: str) -> bool:
        filepath = self._get_workflow_path(workflow_id)
        if not os.path.exists(filepath):
            return False

        os.remove(filepath)
        return True
