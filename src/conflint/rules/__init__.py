"""Built-in rules.

Rule ids are stable and form part of conflint's public interface:

========  =================  ===============================
Rule      Name               Meaning
========  =================  ===============================
CL001     missing            read in code, defined nowhere
CL002     unused             defined for real, never read
CL003     typo               undefined name resembles a known one
CL004     secret-leak        committed high-entropy secret
CL005     drift              documented in example, never provided
CL006     empty-value        required value left empty
CL007     duplicate          defined twice / conflicting values
CL008     weak-secret        weak or default secret value
CL009     undocumented       missing from the example template
========  =================  ===============================
"""

from __future__ import annotations

from conflint.rules.base import Rule
from conflint.rules.drift import DriftRule
from conflint.rules.duplicate import DuplicateRule
from conflint.rules.empty import EmptyValueRule
from conflint.rules.missing import MissingRule
from conflint.rules.secrets import SecretLeakRule
from conflint.rules.typo import TypoRule
from conflint.rules.undocumented import UndocumentedRule
from conflint.rules.unused import UnusedRule
from conflint.rules.weak import WeakSecretRule

__all__ = [
    "Rule",
    "MissingRule",
    "UnusedRule",
    "TypoRule",
    "SecretLeakRule",
    "DriftRule",
    "EmptyValueRule",
    "DuplicateRule",
    "WeakSecretRule",
    "UndocumentedRule",
]
