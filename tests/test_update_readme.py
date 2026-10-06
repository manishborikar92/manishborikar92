import pytest
from update_readme import (
    replace_block,
    badge,
    render_skills,
    render_projects,
    top_repos,
    is_valid_svg,
    EXCLUDE_LANGUAGES,
    LANG_COLOURS,
)

def test_replace_block_success():
    initial = "Header\n<!-- TEST_START -->\nold content\n<!-- TEST_END -->\nFooter"
    result = replace_block(initial, "TEST", "new content")
    expected = "Header\n<!-- TEST_START -->\nnew content\n<!-- TEST_END -->\nFooter"
    assert result == expected

def test_replace_block_missing_marker():
    initial = "Header\n<!-- OTHER_START -->\ncontent\n<!-- OTHER_END -->\nFooter"
    result = replace_block(initial, "TEST", "new content")
    assert result == initial

def test_badge_escaping():
    result = badge("C++", "C++", "00599C", "cplusplus")
    assert "badge/C++-C++-00599C" in result
    assert "&logo=cplusplus" in result

    # Test hyphens and spaces
    result2 = badge("Inno-Setup", "Inno Setup", "555555")
    assert "Inno--Setup-Inno_Setup-555555" in result2

def test_render_skills_curation():
    lang_bytes = {
        "JavaScript": 1500000,
        "Python": 900000,
        "TypeScript": 200000,
        "PHP": 90000,
        "Blade": 40000,
        "Batchfile": 5000,
        "Inno Setup": 2500,
        "Shell": 1500,
        "Dockerfile": 600,
    }
    rendered = render_skills(lang_bytes, top_n=10)

    # Excluded scripts should NOT appear
    for excluded in EXCLUDE_LANGUAGES:
        assert excluded not in rendered

    # Included core languages must appear
    assert "JavaScript" in rendered
    assert "Python" in rendered
    assert "TypeScript" in rendered
    assert "PHP" in rendered
    assert "Shell" in rendered
    assert "Dockerfile" in rendered

    # PHP must use official brand purple (#777BB4)
    assert LANG_COLOURS["PHP"] == "777BB4"
    assert "777BB4" in rendered

def test_render_projects_static_badges():
    repos = [
        {
            "name": "EnRouteAR",
            "html_url": "https://github.com/manishborikar92/EnRouteAR",
            "description": "AR campus navigation",
            "language": "JavaScript",
            "stargazers_count": 2,
            "forks_count": 0,
        },
        {
            "name": "Song-Recognition-Bot",
            "html_url": "https://github.com/manishborikar92/Song-Recognition-Bot",
            "description": "Song finder bot",
            "language": "Python",
            "stargazers_count": 0,
            "forks_count": 0,
        }
    ]
    commit_counts = {"EnRouteAR": 304, "Song-Recognition-Bot": 121}

    rendered = render_projects(repos, commit_counts)

    # Verify static shields format
    assert "badge/stars-2-f59e0b" in rendered
    assert "badge/forks-0-6366f1" in rendered
    assert "badge/commits-304-7C3AED" in rendered

    # Verify dynamic shields URLs are NOT present
    assert "img.shields.io/github/stars" not in rendered
    assert "img.shields.io/github/forks" not in rendered

def test_top_repos_ranking():
    repos = [
        {"name": "repo-small"},
        {"name": "repo-large"},
        {"name": "repo-medium"},
        {"name": "repo-tiny"},
    ]
    counts = {
        "repo-small": 10,
        "repo-large": 100,
        "repo-medium": 50,
        "repo-tiny": 1,
    }
    sorted_top = top_repos(repos, counts, n=3)
    assert len(sorted_top) == 3
    assert sorted_top[0]["name"] == "repo-large"
    assert sorted_top[1]["name"] == "repo-medium"
    assert sorted_top[2]["name"] == "repo-small"

def test_is_valid_svg():
    # Genuine SVG
    valid_svg = '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><circle cx="50" cy="50" r="40"/></svg>'
    assert is_valid_svg(valid_svg) is True

    valid_xml_svg = '<?xml version="1.0"?><svg viewBox="0 0 10 10"><rect/></svg>'
    assert is_valid_svg(valid_xml_svg) is True

    # HTML error page containing an SVG icon
    html_error = '<!DOCTYPE html><html><body><h1>502 Bad Gateway</h1><svg><path/></svg></body></html>'
    assert is_valid_svg(html_error) is False

    # Error message in SVG
    error_svg = '<svg><text>Error: Rate limit exceeded</text></svg>'
    assert is_valid_svg(error_svg) is False

    # Empty content
    assert is_valid_svg("") is False
