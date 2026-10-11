"""Built-in configuration sources."""

from __future__ import annotations

from conflint.sources.base import ConfigSource
from conflint.sources.docker_compose import DockerComposeSource
from conflint.sources.dotenv import DotenvSource
from conflint.sources.github_actions import GitHubActionsSource
from conflint.sources.kubernetes import KubernetesSource
from conflint.sources.terraform import TerraformSource

__all__ = [
    "ConfigSource",
    "DockerComposeSource",
    "DotenvSource",
    "GitHubActionsSource",
    "KubernetesSource",
    "TerraformSource",
]
