"""Abstract base class for all watchers."""
import logging
from abc import ABC, abstractmethod
from pathlib import Path

logger = logging.getLogger("digital_fte.watcher")


class BaseWatcher(ABC):
    def __init__(self, vault_path: Path, check_interval: int = 60):
        self.vault_path = vault_path
        self.check_interval = check_interval
        self.needs_action_dir = vault_path / "Needs_Action"
        self.needs_action_dir.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def check_for_updates(self) -> list:
        ...

    @abstractmethod
    def create_action_file(self, item) -> Path:
        ...

    def run_once(self) -> int:
        items = self.check_for_updates()
        count = 0
        for item in items:
            try:
                self.create_action_file(item)
                count += 1
            except Exception as e:
                logger.error(f"Failed to create action file: {e}")
        return count
