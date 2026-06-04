from __future__ import annotations

from typing import Any, Dict, List, Optional

from translator_pro.utils.storage import AppStorage


class AgentManager:
    def __init__(self, storage: AppStorage) -> None:
        self.storage = storage

    def list_agents(self) -> List[Dict[str, Any]]:
        return self.storage.get_agents()

    def get_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        for agent in self.list_agents():
            if agent.get("name") == name:
                return agent
        return None

    def get(self, agent_id: str) -> Optional[Dict[str, Any]]:
        return self.storage.get_agent(agent_id)

    def save(self, agent: Dict[str, Any]) -> Dict[str, Any]:
        return self.storage.upsert_agent(agent)

    def delete(self, agent_id: str) -> None:
        self.storage.delete_agent(agent_id)
