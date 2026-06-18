import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path
from errbot.utils import entry_point_plugins


def test_entry_point_plugins_no_groups():
    result = entry_point_plugins("does_not_exist")
    assert [] == result


def test_entry_point_plugins_valid_groups():
    results = entry_point_plugins("console_scripts")
    match = False
    for result in results:
        if "errbot" in result:
            match = True
    assert match


def test_entry_point_paths_empty():
    groups = ["errbot.plugins", "errbot.backend_plugins"]
    for entry_point_group in groups:
        plugins = entry_point_plugins(entry_point_group)
        # Note: this test assumes no real backend plugins are installed in the test environment.
        assert plugins == []


class TestEntryPointDiscovery(unittest.TestCase):
    @patch("importlib.metadata.entry_points")
    @patch("importlib.util.find_spec")
    def test_entry_point_discovery_editable_logic(
        self, mock_find_spec, mock_entry_points
    ):
        """
        Test that discovery works when dist.files is missing (typical of editable installs)
        but the module is findable via find_spec.
        """
        # Mock entry point
        mock_ep = MagicMock()
        mock_ep.name = "testplugin"
        mock_ep.module = "test_module"
        # Simulate editable install: dist exists but has no files attribute or it's empty
        mock_ep.dist = MagicMock()
        mock_ep.dist.files = None

        mock_entry_points.return_value = [mock_ep]

        # Mock find_spec to return a valid path
        mock_spec = MagicMock()
        fake_path = Path("/tmp/fake_dir/test_module.py")
        mock_spec.origin = str(fake_path)
        mock_spec.submodule_search_locations = None  # It's a module, not a package
        mock_find_spec.return_value = mock_spec

        paths = entry_point_plugins("errbot.backend_plugins")

        # Should have found the parent directory of the module
        # Note: on macOS /tmp is a symlink to /private/tmp, resolve() handles this.
        expected = str(Path("/tmp/fake_dir").resolve())
        self.assertIn(expected, paths)
        mock_find_spec.assert_called_with("test_module")

    @patch("importlib.metadata.entry_points")
    @patch("importlib.util.find_spec")
    def test_entry_point_discovery_package_logic(
        self, mock_find_spec, mock_entry_points
    ):
        """
        Test that discovery works for packages via find_spec.
        """
        mock_ep = MagicMock()
        mock_ep.name = "testpackage"
        mock_ep.module = "test_pkg"
        mock_ep.dist = None  # No distribution info at all

        mock_entry_points.return_value = [mock_ep]

        mock_spec = MagicMock()
        mock_spec.origin = "/tmp/fake_pkg/__init__.py"
        mock_spec.submodule_search_locations = ["/tmp/fake_pkg"]
        mock_find_spec.return_value = mock_spec

        paths = entry_point_plugins("errbot.backend_plugins")

        expected = str(Path("/tmp/fake_pkg").resolve())
        self.assertIn(expected, paths)

    @patch("importlib.metadata.entry_points")
    @patch("importlib.util.find_spec")
    def test_entry_point_discovery_fallback_to_files(
        self, mock_find_spec, mock_entry_points
    ):
        """
        Test that it still falls back to files if find_spec fails.
        """
        mock_ep = MagicMock()
        mock_ep.name = "fallback"
        mock_ep.module = "nonexistent"

        # Method 1 fails
        mock_find_spec.side_effect = Exception("Import error")

        # Method 2 (files) should work
        mock_file = MagicMock()
        mock_file.parts = ["fallback", "plugin.py"]
        # Ensure the mock returns a resolved path consistent with expectations
        mock_file.locate.return_value.absolute.return_value.resolve.return_value.parent = Path(
            "/tmp/installed_dir"
        ).resolve()

        mock_ep.dist.files = [mock_file]
        mock_entry_points.return_value = [mock_ep]

        paths = entry_point_plugins("errbot.backend_plugins")

        expected = str(Path("/tmp/installed_dir").resolve())
        self.assertIn(expected, paths)

    @patch("importlib.metadata.entry_points")
    @patch("importlib.util.find_spec")
    @patch("errbot.utils.log")
    def test_entry_point_discovery_logs_failure(
        self, mock_log, mock_find_spec, mock_entry_points
    ):
        """
        Test that failure to find spec is logged.
        """
        mock_ep = MagicMock()
        mock_ep.name = "fallback"
        mock_ep.module = "nonexistent"
        mock_ep.dist = MagicMock()
        mock_ep.dist.files = []

        # Method 1 fails
        mock_find_spec.side_effect = Exception("Import error")

        mock_entry_points.return_value = [mock_ep]

        entry_point_plugins("errbot.backend_plugins")

        mock_log.debug.assert_called_with(
            "Spec-based discovery failed for entry point fallback (module nonexistent)",
            exc_info=True,
        )

    @patch("importlib.metadata.entry_points")
    @patch("importlib.util.find_spec")
    def test_entry_point_discovery_deduplication(
        self, mock_find_spec, mock_entry_points
    ):
        """
        Test that if both methods find the same path, it is deduplicated.
        """
        mock_ep = MagicMock()
        mock_ep.name = "double"
        mock_ep.module = "double_mod"

        # Both methods point to the same directory
        same_dir = Path("/tmp/same_dir").resolve()

        # Method 1 setup
        mock_spec = MagicMock()
        mock_spec.origin = str(same_dir / "double_mod.py")
        mock_spec.submodule_search_locations = None
        mock_find_spec.return_value = mock_spec

        # Method 2 setup
        mock_file = MagicMock()
        mock_file.parts = ["double_mod.py"]
        mock_file.locate.return_value.absolute.return_value.resolve.return_value.parent = same_dir
        mock_ep.dist.files = [mock_file]

        mock_entry_points.return_value = [mock_ep]

        paths = entry_point_plugins("errbot.backend_plugins")

        self.assertEqual(len(paths), 1)
        self.assertEqual(paths[0], str(same_dir))

    @patch("importlib.metadata.entry_points")
    @patch("importlib.util.find_spec")
    def test_entry_point_discovery_multiple_entry_points_same_package(
        self, mock_find_spec, mock_entry_points
    ):
        """
        Test that multiple entry points in the same package (common for complex backends)
        are handled and paths are correctly collected/deduplicated.
        """
        # Package with two backends
        ep1 = MagicMock()
        ep1.name = "backend_one"
        ep1.module = "multibackend.one"
        ep1.dist.files = None

        ep2 = MagicMock()
        ep2.name = "backend_two"
        ep2.module = "multibackend.two"
        ep2.dist.files = None

        mock_entry_points.return_value = [ep1, ep2]

        # Both live in the same source directory
        base_dir = Path("/tmp/multibackend").resolve()

        def side_effect(module_name):
            spec = MagicMock()
            spec.origin = str(base_dir / module_name.split(".")[-1] / "__init__.py")
            spec.submodule_search_locations = [
                str(base_dir / module_name.split(".")[-1])
            ]
            return spec

        mock_find_spec.side_effect = side_effect

        paths = entry_point_plugins("errbot.backend_plugins")

        # We expect paths to both submodules (or the parent if logic was different,
        # but our current logic adds the parent of spec.origin)
        self.assertIn(str(base_dir / "one"), paths)
        self.assertIn(str(base_dir / "two"), paths)
        self.assertEqual(len(paths), 2)
