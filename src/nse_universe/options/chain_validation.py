"""Quality checks for option-chain coverage before interpreting aggregate metrics."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable
from nse_universe.options.models import OptionChainSnapshot

@dataclass(frozen=True, slots=True)
class ChainValidationReport:
    is_usable: bool
    issues: tuple[str, ...]
    missing_contracts: tuple[tuple[float, str], ...]
    complete_flag: bool

def validate_chain(snapshot: OptionChainSnapshot, *, expected_strikes: Iterable[float] | None = None,
                   require_both_sides: bool = True) -> ChainValidationReport:
    issues=[]
    present={(c.strike,c.option_type) for c in snapshot.contracts}
    strikes=set(expected_strikes) if expected_strikes is not None else {c.strike for c in snapshot.contracts}
    missing=[]
    for strike in sorted(strikes):
        sides=("CE","PE") if require_both_sides else tuple(side for side in ("CE","PE") if (strike,side) in present)
        for side in sides:
            if (strike,side) not in present: missing.append((strike,side))
    if missing: issues.append(f"{len(missing)} expected option contract(s) are missing")
    if not snapshot.contracts: issues.append("snapshot contains no contracts")
    if not snapshot.complete: issues.append("snapshot is marked incomplete; aggregate chain metrics may be misleading")
    return ChainValidationReport(bool(snapshot.contracts) and not missing and snapshot.complete,
                                 tuple(issues),tuple(missing),snapshot.complete)
