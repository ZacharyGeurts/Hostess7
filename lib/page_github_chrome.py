#!/usr/bin/env python3
"""Top + bottom GitHub repo chrome for Pages sites — always link to the repo."""
from __future__ import annotations

GITHUB_REPO = "https://github.com/ZacharyGeurts/AmmoOS"
GITHUB_RELEASES = "https://github.com/ZacharyGeurts/AmmoOS/releases"
PAGES_HOME = "https://zacharygeurts.github.io/AmmoOS/"
STACK_HUB = "https://zacharygeurts.github.io/ZacharyGeurts/stack.html"
AMMOOS_CODE_LABEL = "ZacharyGeurts/AmmoOS"


def chrome_css() -> str:
    return """
.github-chrome-top, .github-chrome-bottom {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem 1rem;
  padding: 0.55rem 0.85rem;
  margin: 0 0 1rem;
  border-radius: 8px;
  background: rgba(34, 197, 94, 0.12);
  border: 1px solid rgba(34, 197, 94, 0.35);
  font-size: 0.92rem;
}
.github-chrome-bottom { margin: 2rem 0 0; }
.github-chrome-top a.github-repo-primary,
.github-chrome-bottom a.github-repo-primary {
  font-weight: 700;
  color: #4ade80;
  text-decoration: none;
}
.github-chrome-top a.github-repo-primary:hover,
.github-chrome-bottom a.github-repo-primary:hover { text-decoration: underline; }
.github-chrome-links a { margin-right: 0.75rem; color: #94a3b8; }
"""


def chrome_top(
    repo_url: str = GITHUB_REPO,
    *,
    label: str = "ZacharyGeurts/AmmoOS",
    pages_url: str = PAGES_HOME,
    stack_url: str = STACK_HUB,
) -> str:
    return f"""<div class="github-chrome-top" role="navigation" aria-label="GitHub repo">
  <a class="github-repo-primary" href="{repo_url}">→ GitHub: {label}</a>
  <span class="github-chrome-links">
    <a href="{pages_url}">Pages</a>
    <a href="{stack_url}">Stack hub</a>
    <a href="{repo_url}/releases">Releases</a>
  </span>
</div>
"""


def chrome_bottom(
    repo_url: str = GITHUB_REPO,
    *,
    label: str = "ZacharyGeurts/AmmoOS",
    version: str = "",
) -> str:
    ver = f" · {version}" if version else ""
    return f"""<div class="github-chrome-bottom" role="contentinfo">
  <a class="github-repo-primary" href="{repo_url}">→ GitHub: {label}</a>
  <span class="github-chrome-links">AmmoOS field OS{ver}</span>
</div>
"""


def hub_chrome_top(
    sibling_repo: str,
    *,
    sibling_label: str = "",
    ammoos_repo: str = GITHUB_REPO,
    ammoos_pages: str = PAGES_HOME,
    stack_url: str = STACK_HUB,
    release_tag: str = "v2.0.0-beta4",
) -> str:
    sib = sibling_label or sibling_repo.replace("https://github.com/", "")
    rel = f"{ammoos_repo}/releases/tag/{release_tag}"
    return f"""<div class="github-chrome-top" role="navigation" aria-label="Stack navigation">
  <a class="github-repo-primary" href="{ammoos_repo}">→ Code: {AMMOOS_CODE_LABEL}</a>
  <span class="github-chrome-links">
    <a href="{sibling_repo}">{sib}</a>
    <a href="{ammoos_pages}">AmmoOS manual</a>
    <a href="{stack_url}">Stack hub</a>
    <a href="{rel}">Release {release_tag}</a>
  </span>
</div>
"""


def hub_chrome_bottom(
    sibling_repo: str = GITHUB_REPO,
    *,
    sibling_label: str = "",
    ammoos_repo: str = GITHUB_REPO,
    version: str = "",
) -> str:
    sib = sibling_label or sibling_repo.replace("https://github.com/", "")
    ver = f" · {version}" if version else ""
    return f"""<div class="github-chrome-bottom" role="contentinfo">
  <a class="github-repo-primary" href="{ammoos_repo}">→ Code: {AMMOOS_CODE_LABEL}</a>
  <span class="github-chrome-links"><a href="{sibling_repo}">{sib}</a> · ships in AmmoOS{ver}</span>
</div>
"""