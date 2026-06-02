"""Issue #14 — ressources embarquées accessibles après installation."""

from importlib import resources

from src.etacomp.package_resources import read_text_resource, resource_path


def test_bundled_help_aid_md_exists():
    p = resource_path("resources", "help", "aid.md")
    assert p.is_file()
    text = read_text_resource("resources", "help", "aid.md")
    assert len(text) > 100


def test_package_data_lists_help_via_importlib():
    root = resources.files("etacomp")
    aid = root.joinpath("resources", "help", "aid.md")
    assert aid.is_file()


def test_bundled_insigne_png_exists():
    p = resource_path("resources", "14eBSMAT_insigne.png")
    assert p.is_file()
