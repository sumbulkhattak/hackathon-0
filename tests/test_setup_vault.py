from pathlib import Path


def test_setup_vault_creates_all_folders(tmp_path):
    from setup_vault import setup_vault
    setup_vault(tmp_path)
    expected = ["Needs_Action", "Plans", "Pending_Approval", "Approved", "Done", "Logs", "Rejected"]
    for folder in expected:
        assert (tmp_path / folder).is_dir(), f"Missing folder: {folder}"


def test_setup_vault_creates_handbook(tmp_path):
    from setup_vault import setup_vault
    setup_vault(tmp_path)
    handbook = tmp_path / "Company_Handbook.md"
    assert handbook.exists()
    content = handbook.read_text()
    assert "# Company Handbook" in content


def test_setup_vault_creates_rejected_folder(tmp_path):
    """setup_vault should create a Rejected/ folder."""
    from setup_vault import setup_vault
    setup_vault(tmp_path)
    assert (tmp_path / "Rejected").is_dir()


def test_setup_vault_creates_agent_memory(tmp_path):
    """setup_vault should create Agent_Memory.md with starter template."""
    from setup_vault import setup_vault
    setup_vault(tmp_path)
    memory = tmp_path / "Agent_Memory.md"
    assert memory.exists()
    content = memory.read_text()
    assert "# Agent Memory" in content
    assert "## Patterns" in content


def test_setup_vault_does_not_overwrite_agent_memory(tmp_path):
    """setup_vault should not overwrite existing Agent_Memory.md."""
    from setup_vault import setup_vault
    tmp_path.mkdir(parents=True, exist_ok=True)
    memory = tmp_path / "Agent_Memory.md"
    memory.write_text("# Agent Memory\n\n## Patterns\n- Custom learning here\n")
    setup_vault(tmp_path)
    content = memory.read_text()
    assert "Custom learning here" in content


def test_setup_vault_is_idempotent(tmp_path):
    from setup_vault import setup_vault
    setup_vault(tmp_path)
    setup_vault(tmp_path)
    assert (tmp_path / "Needs_Action").is_dir()
