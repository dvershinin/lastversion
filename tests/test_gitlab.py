"""Test GitLab support."""

import os

from packaging import version

from lastversion.lastversion import latest

# change dir to tests directory to make relative paths possible
os.chdir(os.path.dirname(os.path.realpath(__file__)))


def test_gitlab_1():
    """Test specifying a deep-level link at GitLab."""
    repo = "https://gitlab.com/ddcci-driver-linux/ddcci-driver-linux/-/tree/master"

    v = latest(repo)

    assert v >= version.parse("0.4.1")


def test_gitlab_format_json():
    """Test specifying a deep-level link at GitLab."""
    repo = "https://gitlab.com/ddcci-driver-linux/ddcci-driver-linux/-/tree/master"

    v = latest(repo, output_format="dict")

    assert "tag_date" in v and v["tag_date"].day == 22


def test_gitlab_at():
    """Test specifying GitLab repo with an --at parameter."""
    repo = "ddcci-driver-linux/ddcci-driver-linux"

    v = latest(repo, at="gitlab")

    assert v >= version.parse("0.4.1")


def test_gitlab_nested_subgroup_project():
    """Test specifying a nested GitLab project."""
    repo = "https://gitlab.com/librewolf-community/browser/appimage/-/releases"

    release = latest(repo, output_format="dict")

    assert release["version"] >= version.parse("122.0")


def test_gitlab_url_parsing_with_port():
    """Test that GitLab URLs with non-standard ports are parsed correctly."""
    from lastversion.holder_factory import HolderFactory
    from lastversion.repo_holders.gitlab import GitLabRepoSession
    from urllib.parse import urlparse
    from unittest.mock import Mock, patch

    # Test URL with non-standard port
    url = "https://gitlab.vci.rwth-aachen.de:9000/OpenVolumeMesh/OpenVolumeMesh"

    # Test URL parsing in holder_factory
    parsed = urlparse(url)
    hostname = parsed.netloc if parsed.port else parsed.hostname
    repo = parsed.path.lstrip("/")

    # Verify hostname includes port
    assert hostname == "gitlab.vci.rwth-aachen.de:9000"
    assert repo == "OpenVolumeMesh/OpenVolumeMesh"

    # Test is_matching_hostname strips port correctly
    assert GitLabRepoSession.is_matching_hostname("gitlab.example.com:9000") is True

    # Test get_host_repo_for_link preserves port
    hostname, repo = GitLabRepoSession.get_host_repo_for_link(url)
    assert hostname == "gitlab.vci.rwth-aachen.de:9000"
    assert repo == "OpenVolumeMesh/OpenVolumeMesh"

    # Test that GitLabRepoSession constructs correct API base URL
    with patch.object(GitLabRepoSession, "get") as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": 123,
            "path_with_namespace": "OpenVolumeMesh/OpenVolumeMesh",
        }
        mock_get.return_value = mock_response

        instance = GitLabRepoSession(
            "OpenVolumeMesh/OpenVolumeMesh", "gitlab.vci.rwth-aachen.de:9000"
        )
        assert instance.hostname == "gitlab.vci.rwth-aachen.de:9000"
        assert instance.api_base == "https://gitlab.vci.rwth-aachen.de:9000/api/v4"
