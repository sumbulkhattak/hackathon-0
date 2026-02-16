from pathlib import Path
import pytest


def test_base_watcher_is_abstract():
    from src.watchers.base_watcher import BaseWatcher
    with pytest.raises(TypeError):
        BaseWatcher(vault_path=Path("."), check_interval=10)


def test_concrete_watcher_creates_action_files(tmp_path):
    from src.watchers.base_watcher import BaseWatcher

    class FakeWatcher(BaseWatcher):
        def check_for_updates(self):
            return [{"id": "1", "subject": "Test"}]
        def create_action_file(self, item):
            path = self.needs_action_dir / f"{item['id']}.md"
            path.write_text(f"# {item['subject']}")
            return path

    watcher = FakeWatcher(vault_path=tmp_path, check_interval=10)
    assert watcher.needs_action_dir == tmp_path / "Needs_Action"
    items = watcher.check_for_updates()
    assert len(items) == 1
    path = watcher.create_action_file(items[0])
    assert path.exists()


def test_run_single_cycle(tmp_path):
    from src.watchers.base_watcher import BaseWatcher

    class FakeWatcher(BaseWatcher):
        def check_for_updates(self):
            return [{"id": "1"}, {"id": "2"}]
        def create_action_file(self, item):
            path = self.needs_action_dir / f"{item['id']}.md"
            path.write_text("test")
            return path

    watcher = FakeWatcher(vault_path=tmp_path, check_interval=10)
    watcher.needs_action_dir.mkdir(parents=True, exist_ok=True)
    count = watcher.run_once()
    assert count == 2
