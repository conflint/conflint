"""Tests for the configuration sources."""

from __future__ import annotations

from pathlib import Path

from conflint.sources.docker_compose import DockerComposeSource
from conflint.sources.dotenv import DotenvSource
from conflint.sources.github_actions import GitHubActionsSource
from conflint.sources.kubernetes import KubernetesSource
from conflint.sources.terraform import TerraformSource


def _as_dict(entries):
    return {e.name: e for e in entries}


# ----------------------------------------------------------------------
# dotenv
# ----------------------------------------------------------------------
class TestDotenvSource:
    source = DotenvSource()

    def test_basic(self):
        entries = _as_dict(self.source.parse(Path(".env"), "A=1\nB=two\n"))
        assert entries["A"].value == "1"
        assert entries["B"].value == "two"
        assert entries["A"].location.line == 1

    def test_export_and_empty(self):
        entries = _as_dict(self.source.parse(Path(".env"), "export A=1\nEMPTY=\n"))
        assert "A" in entries
        assert entries["EMPTY"].is_empty is True

    def test_quoted_values(self):
        entries = _as_dict(self.source.parse(Path(".env"), "A='hello'\nB=\"world\"\n"))
        assert entries["A"].value == "hello"
        assert entries["B"].value == "world"

    def test_inline_comment(self):
        entries = _as_dict(self.source.parse(Path(".env"), "A=value # comment\n"))
        assert entries["A"].value == "value"

    def test_comment_stripping_respects_quotes(self):
        entries = _as_dict(self.source.parse(Path(".env"), 'A="va # lue"\n'))
        assert entries["A"].value == "va # lue"

    def test_comments_and_blanks_ignored(self):
        entries = self.source.parse(Path(".env"), "# head\n\nB=2\n")
        assert [e.name for e in entries] == ["B"]

    def test_no_equals_ignored(self):
        entries = self.source.parse(Path(".env"), "SOMETHING\nA=1\n")
        assert [e.name for e in entries] == ["A"]

    def test_secret_detection(self):
        entries = _as_dict(self.source.parse(Path(".env"), "API_TOKEN=x\nPORT=1\n"))
        assert entries["API_TOKEN"].is_secret is True
        assert entries["PORT"].is_secret is False

    def test_matches(self):
        for name in (".env", ".env.local", ".env.example"):
            assert self.source.matches(Path(name))
        assert not self.source.matches(Path("config.py"))


# ----------------------------------------------------------------------
# docker-compose
# ----------------------------------------------------------------------
class TestComposeSource:
    source = DockerComposeSource()
    path = Path("docker-compose.yml")

    TEXT = """\
services:
  api:
    image: x
    environment:
      HOST: localhost
      PORT: "8000"
  worker:
    environment:
      - DEBUG=true
      - WORKER_ID
"""

    def test_mapping_and_list(self):
        entries = _as_dict(self.source.parse(self.path, self.TEXT))
        assert entries["HOST"].value == "localhost"
        assert entries["PORT"].value == "8000"
        assert entries["DEBUG"].value == "true"
        assert entries["WORKER_ID"].value is None

    def test_service_notes(self):
        entries = self.source.parse(self.path, self.TEXT)
        dew = next(e for e in entries if e.name == "DEBUG")
        assert "service:worker" in dew.notes

    def test_matches(self):
        assert self.source.matches(Path("docker-compose.yml"))
        assert self.source.matches(Path("compose.yaml"))
        assert not self.source.matches(Path("docker-compose.txt"))


# ----------------------------------------------------------------------
# github actions
# ----------------------------------------------------------------------
class TestGitHubActionsSource:
    source = GitHubActionsSource()
    path = Path(".github/workflows/ci.yml")

    TEXT = """\
name: CI
env:
  GLOBAL: one
jobs:
  build:
    env:
      JOB_VAR: two
    steps:
      - name: Run
        env:
          STEP_VAR: three
        run: echo hi
"""

    def test_all_env_maps(self):
        entries = _as_dict(self.source.parse(self.path, self.TEXT))
        assert {"GLOBAL", "JOB_VAR", "STEP_VAR"} <= set(entries)
        assert entries["GLOBAL"].value == "one"

    def test_matches(self):
        assert self.source.matches(Path(".github/workflows/ci.yml"))
        assert not self.source.matches(Path("deploy/other.yaml"))


# ----------------------------------------------------------------------
# kubernetes
# ----------------------------------------------------------------------
class TestKubernetesSource:
    source = KubernetesSource()
    path = Path("k8s/deployment.yaml")

    TEXT = """\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
spec:
  template:
    spec:
      containers:
        - name: api
          env:
            - name: DB_HOST
              value: localhost
            - name: DB_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: db
                  key: password
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  FEATURE_FLAG: "on"
"""

    def test_container_env(self):
        entries = _as_dict(self.source.parse(self.path, self.TEXT))
        assert entries["DB_HOST"].value == "localhost"
        assert entries["DB_PASSWORD"].value is None
        assert any("secretKeyRef" in n for n in entries["DB_PASSWORD"].notes)

    def test_configmap_data(self):
        entries = _as_dict(self.source.parse(self.path, self.TEXT))
        assert entries["FEATURE_FLAG"].value == "on"

    def test_matches_excludes_compose_and_aliases(self):
        assert self.source.matches(Path("deploy.yaml"))
        assert not self.source.matches(Path("docker-compose.yml"))
        assert not self.source.matches(Path(".github/workflows/x.yaml"))


# ----------------------------------------------------------------------
# terraform
# ----------------------------------------------------------------------
class TestTerraformSource:
    source = TerraformSource()

    def test_variable_block(self):
        text = 'variable "API_URL" {\n  type = string\n  default = "https://x"\n}\n'
        entries = _as_dict(self.source.parse(Path("main.tf"), text))
        assert entries["API_URL"].value == "https://x"

    def test_variable_without_default(self):
        text = 'variable "SECRET" {}\n'
        entries = _as_dict(self.source.parse(Path("main.tf"), text))
        assert entries["SECRET"].value is None

    def test_environment_block(self):
        text = 'container {\n  environment = {\n    FOO = "bar"\n    N = 1\n  }\n}\n'
        entries = _as_dict(self.source.parse(Path("main.tf"), text))
        assert entries["FOO"].value == "bar"
        assert entries["N"].value == "1"

    def test_tfvars(self):
        entries = _as_dict(self.source.parse(Path("dev.tfvars"), 'FOO = "bar"'))
        assert entries["FOO"].value == "bar"

    def test_json_tfvars(self):
        entries = _as_dict(self.source.parse(Path("vars.tfvars.json"), '{"FOO": "bar"}'))
        assert entries["FOO"].value == "bar"

    def test_matches(self):
        assert self.source.matches(Path("main.tf"))
        assert self.source.matches(Path("dev.tfvars"))
        assert self.source.matches(Path("v.tfvars.json"))
        assert not self.source.matches(Path("main.py"))
