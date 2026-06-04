from __future__ import annotations

import json
import os
import uuid
from copy import deepcopy
from pathlib import Path
from threading import RLock
from typing import Any, Dict, List, Optional

from .defaults import CONFIG_DIR_NAME, CONFIG_FILE_NAME, DEFAULT_CONFIG, HISTORY_LIMIT


def get_config_dir() -> Path:
    path = Path.home() / CONFIG_DIR_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_config_path() -> Path:
    return get_config_dir() / CONFIG_FILE_NAME


def ensure_id(item: Dict[str, Any], prefix: str) -> Dict[str, Any]:
    if not item.get("id"):
        item["id"] = f"{prefix}-{uuid.uuid4().hex[:10]}"
    return item


class AppStorage:
    """Thread-safe JSON-backed configuration store."""

    def __init__(self) -> None:
        self._lock = RLock()
        self.path = get_config_path()
        self.data = self._load()

    def _load(self) -> Dict[str, Any]:
        if not self.path.exists():
            data = deepcopy(DEFAULT_CONFIG)
            self._write_raw(data)
            return data
        try:
            with self.path.open("r", encoding="utf-8") as f:
                loaded = json.load(f)
        except Exception:
            backup = self.path.with_suffix(".broken.json")
            try:
                self.path.replace(backup)
            except Exception:
                pass
            loaded = deepcopy(DEFAULT_CONFIG)
        return self._merge_defaults(loaded)

    def _merge_defaults(self, loaded: Dict[str, Any]) -> Dict[str, Any]:
        data = deepcopy(DEFAULT_CONFIG)
        data.update({k: v for k, v in loaded.items() if k in data})
        data["settings"] = {**DEFAULT_CONFIG["settings"], **loaded.get("settings", {})}
        data["apis"] = [ensure_id(dict(x), "api") for x in data.get("apis", [])]
        data["agents"] = [ensure_id(dict(x), "agent") for x in data.get("agents", [])]
        data["glossary"] = [ensure_id(dict(x), "term") for x in data.get("glossary", [])]
        data["history"] = list(data.get("history", []))[-HISTORY_LIMIT:]
        return data

    def _write_raw(self, data: Dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.path)

    def save(self) -> None:
        with self._lock:
            self._write_raw(self.data)

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return deepcopy(self.data)

    def get_settings(self) -> Dict[str, Any]:
        with self._lock:
            return deepcopy(self.data.get("settings", {}))

    def update_settings(self, **kwargs: Any) -> None:
        with self._lock:
            self.data.setdefault("settings", {}).update(kwargs)
            self.save()

    def get_apis(self) -> List[Dict[str, Any]]:
        with self._lock:
            return deepcopy(self.data.get("apis", []))

    def upsert_api(self, api: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            api = ensure_id(dict(api), "api")
            apis = self.data.setdefault("apis", [])
            for idx, item in enumerate(apis):
                if item.get("id") == api.get("id"):
                    apis[idx] = api
                    self.save()
                    return deepcopy(api)
            apis.append(api)
            self.save()
            return deepcopy(api)

    def delete_api(self, api_id: str) -> None:
        with self._lock:
            self.data["apis"] = [x for x in self.data.get("apis", []) if x.get("id") != api_id]
            self.save()

    def get_api(self, api_id: str) -> Optional[Dict[str, Any]]:
        for api in self.get_apis():
            if api.get("id") == api_id:
                return api
        return None

    def get_agents(self) -> List[Dict[str, Any]]:
        with self._lock:
            return deepcopy(self.data.get("agents", []))

    def upsert_agent(self, agent: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            agent = ensure_id(dict(agent), "agent")
            agents = self.data.setdefault("agents", [])
            for idx, item in enumerate(agents):
                if item.get("id") == agent.get("id"):
                    agents[idx] = agent
                    self.save()
                    return deepcopy(agent)
            agents.append(agent)
            self.save()
            return deepcopy(agent)

    def delete_agent(self, agent_id: str) -> None:
        with self._lock:
            self.data["agents"] = [x for x in self.data.get("agents", []) if x.get("id") != agent_id]
            self.save()

    def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        for agent in self.get_agents():
            if agent.get("id") == agent_id:
                return agent
        return None

    def get_glossary(self) -> List[Dict[str, Any]]:
        with self._lock:
            return deepcopy(self.data.get("glossary", []))

    def upsert_term(self, term: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            term = ensure_id(dict(term), "term")
            glossary = self.data.setdefault("glossary", [])
            for idx, item in enumerate(glossary):
                if item.get("id") == term.get("id"):
                    glossary[idx] = term
                    self.save()
                    return deepcopy(term)
            glossary.append(term)
            self.save()
            return deepcopy(term)

    def delete_term(self, term_id: str) -> None:
        with self._lock:
            self.data["glossary"] = [x for x in self.data.get("glossary", []) if x.get("id") != term_id]
            self.save()

    def add_history(self, item: Dict[str, Any]) -> None:
        with self._lock:
            item = ensure_id(dict(item), "hist")
            hist = self.data.setdefault("history", [])
            hist.append(item)
            self.data["history"] = hist[-HISTORY_LIMIT:]
            self.save()

    def get_history(self) -> List[Dict[str, Any]]:
        with self._lock:
            return deepcopy(self.data.get("history", []))

    def clear_history(self) -> None:
        with self._lock:
            self.data["history"] = []
            self.save()
