from pathlib import Path


def test_setup_vault_creates_all_folders(tmp_path):
    from setup_vault import setup_vault
    setup_vault(tmp_path)
    expected = ["Needs_Action", "Plans", "Pending_Approval", "Approved", "Done", "Logs"]
    for folder in expected:
        assert (tmp_path / folder).is_dir(), f"Missing folder: {folder}"


def test_setup_vault_creates_handbook(tmp_path):
    from setup_vault import setup_vault
    setup_vault(tmp_path)
    handbook = tmp_path / "Company_Handbook.md"
    assert handbook.exists()
    content = handbook.read_text()
    assert "# Company Handbook" in content


def test_setup_vault_is_idempotent(tmp_path):
    from setup_vault import setup_vault
    setup_vault(tmp_path)
    setup_vault(tmp_path)
    assert (tmp_path / "Needs_Action").is_dir()
