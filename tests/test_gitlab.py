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


def test_gitlab_packages_integration():
    """Test that GitLab packages are correctly integrated with assets."""
    from lastversion.repo_holders.gitlab import GitLabRepoSession
    
    # Create a mock GitLabRepoSession for testing
    class MockGitLabRepoSession(GitLabRepoSession):
        def __init__(self):
            # Skip the parent __init__ to avoid network calls
            self.repo = "test-org/test-project"
            self.api_base = "https://gitlab.com/api/v4"
            
        def repo_query(self, uri, params=None):
            """Mock repo query to return sample packages data."""
            
            class MockResponse:
                def __init__(self, status_code, json_data):
                    self.status_code = status_code
                    self._json_data = json_data
                    
                def json(self):
                    return self._json_data
            
            if uri == "/packages":
                # Return mock packages data matching a specific version
                return MockResponse(200, [
                    {
                        "id": 12345,
                        "name": "testapp",
                        "version": "1.0.0",
                        "package_type": "generic",
                        "package_files": [
                            {"file_name": "testapp-1.0.0-linux-x86_64.tar.gz"},
                            {"file_name": "testapp-1.0.0-windows-x64.zip"},
                        ]
                    }
                ])
            return MockResponse(404, {})
    
    # Create session and test release
    session = MockGitLabRepoSession()
    
    # Mock release object with x86_64 asset to ensure something gets through
    release = {
        "tag_name": "1.0.0",
        "assets": {
            "links": [
                {
                    "name": "extra-asset-x86_64.txt",
                    "url": "https://gitlab.com/api/v4/projects/123/releases/1.0.0/downloads/extra-asset-x86_64.txt"
                }
            ]
        }
    }
    
    # Test get_assets includes packages
    assets = session.get_assets(release, False)
    
    # Should include both traditional assets and packages
    assert len(assets) >= 1, f"Expected at least 1 asset, got {len(assets)}: {assets}"
    
    # Check that package URLs are properly formatted
    package_urls = [url for url in assets if "packages/generic" in url]
    assert len(package_urls) > 0, "No package URLs found in assets"
    
    # Verify URL format
    expected_pattern = "api/v4/projects/test-org%2Ftest-project/packages/generic/testapp/1.0.0/"
    found_correct_format = any(expected_pattern in url for url in package_urls)
    assert found_correct_format, f"Package URLs don't match expected format. URLs: {package_urls}"
    
    # Test with assets_filter to bypass architecture filtering
    all_assets = session.get_assets(release, False, assets_filter=".*")
    package_urls_all = [url for url in all_assets if "packages/generic" in url]
    
    # Should have the Linux package
    linux_package = any("linux-x86_64" in url for url in package_urls_all)
    assert linux_package, f"Linux x86_64 package not found in: {package_urls_all}"
