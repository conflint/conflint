"""Rule-level tests (each rule in isolation)."""

from __future__ import annotations

from pathlib import Path

from conflint.config import Settings
from conflint.models import Entry, Language, Location, Usage
from conflint.rules.drift import DriftRule
from conflint.rules.duplicate import DuplicateRule
from conflint.rules.empty import EmptyValueRule
from conflint.rules.missing import MissingRule
from conflint.rules.secrets import SecretLeakRule
from conflint.rules.typo import TypoRule
from conflint.rules.undocumented import UndocumentedRule
from conflint.rules.unused import UnusedRule
from conflint.rules.weak import WeakSecretRule


def u(name, required=False, line=1, path="app.py", default=None):
    return Usage(
        name=name,
        location=Location(Path(path), line),
        language=Language.PYTHON,
        read_via="os.environ",
        required=required,
        has_default=default is not None,
        default=default,
    )


def e(name, value, source="dotenv", example=False, secret=False, path=".env"):
    return Entry(
        name=name,
        value=value,
        location=Location(Path(path), 1),
        source=source,
        is_secret=secret,
        is_example=example,
    )


def settings(root=Path("."), **kw):
    return Settings(root=root, **kw)


# ----------------------------------------------------------------------
# CL001 missing
# ----------------------------------------------------------------------
class TestMissing:
    def test_required_is_error(self, run_rules):
        findings = run_rules(MissingRule(), usages=[u("X", required=True)])
        assert len(findings) == 1
        assert findings[0].rule_id == "CL001"
        assert findings[0].severity.value == "error"
        assert findings[0].key == "X"

    def test_optional_is_warning(self, run_rules):
        findings = run_rules(MissingRule(), usages=[u("X")])
        assert findings[0].severity.value == "warning"

    def test_defined_key_is_ok(self, run_rules):
        findings = run_rules(MissingRule(), usages=[u("X")], entries=[e("X", "1")])
        assert findings == []

    def test_ignored_name(self, run_rules):
        findings = run_rules(
            MissingRule(),
            usages=[u("CI")],
            settings=settings(ignore_names=("CI",)),
        )
        assert findings == []


# ----------------------------------------------------------------------
# CL002 unused
# ----------------------------------------------------------------------
class TestUnused:
    def test_unused_real_entry(self, run_rules):
        findings = run_rules(UnusedRule(), entries=[e("UNUSED", "1")])
        assert [f.key for f in findings] == ["UNUSED"]

    def test_used_entry_ok(self, run_rules):
        findings = run_rules(UnusedRule(), usages=[u("USED")], entries=[e("USED", "1")])
        assert findings == []


# ----------------------------------------------------------------------
# CL003 typo
# ----------------------------------------------------------------------
class TestTypo:
    def test_typo_suggests(self, run_rules):
        findings = run_rules(TypoRule(), usages=[u("DBHOST")], entries=[e("DB_HOST", "x")])
        assert findings
        assert findings[0].data["suggestion"] == "DB_HOST"

    def test_no_suggestion_when_defined(self, run_rules):
        findings = run_rules(TypoRule(), usages=[u("DB_HOST")], entries=[e("DB_HOST", "x")])
        assert findings == []

    def test_no_match_for_unrelated(self, run_rules):
        findings = run_rules(TypoRule(), usages=[u("ZZ_QQ")], entries=[e("A_B", "x")])
        assert findings == []


# ----------------------------------------------------------------------
# CL004 secret-leak
# ----------------------------------------------------------------------
_AWS_LIKE = "AKIAIOSFODNN7EXAMPLEVALUELONGER"
_PLACEHOLDER = "changeme"


class TestSecretLeak:
    def test_flagged(self, run_rules):
        findings = run_rules(
            SecretLeakRule(),
            entries=[e("AWS_SECRET_ACCESS_KEY", _AWS_LIKE, secret=True)],
        )
        assert findings
        assert findings[0].severity.value == "error"

    def test_placeholder_not_flagged(self, run_rules):
        findings = run_rules(SecretLeakRule(), entries=[e("AWS_SECRET_ACCESS_KEY", _PLACEHOLDER)])
        assert findings == []

    def test_example_not_flagged(self, run_rules):
        findings = run_rules(
            SecretLeakRule(),
            entries=[e("API_TOKEN", _AWS_LIKE, example=True)],
        )
        assert findings == []

    def test_non_sensitive_name_not_flagged(self, run_rules):
        findings = run_rules(SecretLeakRule(), entries=[e("GREETING", "HelloWorld123!")])
        assert findings == []


# ----------------------------------------------------------------------
# CL005 drift
# ----------------------------------------------------------------------
class TestDrift:
    def test_example_only_is_drift(self, run_rules):
        findings = run_rules(
            DriftRule(), usages=[u("DATABASE_URL")], entries=[e("DATABASE_URL", "", example=True)]
        )
        assert findings
        assert findings[0].severity.value == "error"

    def test_real_definition_ok(self, run_rules):
        findings = run_rules(
            DriftRule(),
            usages=[u("DATABASE_URL")],
            entries=[e("DATABASE_URL", "postgres://x", example=True), e("DATABASE_URL", "pg://x")],
        )
        assert findings == []


# ----------------------------------------------------------------------
# CL006 empty-value
# ----------------------------------------------------------------------
class TestEmptyValue:
    def test_required_but_empty(self, run_rules):
        findings = run_rules(
            EmptyValueRule(),
            usages=[u("PORT", required=True)],
            entries=[e("PORT", "")],
        )
        assert [f.key for f in findings] == ["PORT"]

    def test_optional_empty_ok(self, run_rules):
        findings = run_rules(EmptyValueRule(), usages=[u("PORT")], entries=[e("PORT", "")])
        assert findings == []


# ----------------------------------------------------------------------
# CL007 duplicate
# ----------------------------------------------------------------------
class TestDuplicate:
    def test_duplicate_in_file(self, run_rules):
        entries = [
            e("A", "1", path=".env"),
            e("A", "2", path=".env"),
        ]
        findings = run_rules(DuplicateRule(), entries=entries)
        assert any(f.rule_id == "CL007" and "2 times" in f.message for f in findings)

    def test_distinct_files_ok(self, run_rules):
        findings = run_rules(
            DuplicateRule(),
            entries=[e("A", "1", path=".env"), e("A", "2", path=".env.local")],
        )
        assert not any(f.rule_id == "CL007" and "defined" in f.message for f in findings)


# ----------------------------------------------------------------------
# CL008 weak-secret
# ----------------------------------------------------------------------
class TestWeakSecret:
    def test_weak_value(self, run_rules):
        findings = run_rules(WeakSecretRule(), entries=[e("API_SECRET", "password", secret=True)])
        assert [f.key for f in findings] == ["API_SECRET"]

    def test_strong_value_ok(self, run_rules):
        findings = run_rules(WeakSecretRule(), entries=[e("API_SECRET", _AWS_LIKE, secret=True)])
        assert findings == []


# ----------------------------------------------------------------------
# CL009 undocumented
# ----------------------------------------------------------------------
class TestUndocumented:
    def test_missing_from_example(self, run_rules):
        findings = run_rules(
            UndocumentedRule(),
            usages=[u("API_KEY")],
            entries=[e("OTHER", "x", example=True)],
        )
        assert [f.key for f in findings] == ["API_KEY"]
        assert findings[0].severity.value == "info"

    def test_documented_ok(self, run_rules):
        findings = run_rules(
            UndocumentedRule(), usages=[u("API_KEY")], entries=[e("API_KEY", "", example=True)]
        )
        assert findings == []

    def test_no_example_file_skips(self, run_rules):
        findings = run_rules(UndocumentedRule(), usages=[u("API_KEY")])
        assert findings == []

    def test_require_example_false(self, run_rules):
        findings = run_rules(
            UndocumentedRule(),
            usages=[u("API_KEY")],
            entries=[e("OTHER", "x", example=True)],
            settings=settings(require_example=False),
        )
        assert findings == []
