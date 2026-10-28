"""Contract versions (PHASE-1.md 5.0, PHASE-2.md 5). The tech lead tags `contracts-v<CONTRACTS>`.

Phase 2 raises them to 1.1.0 one contract at a time (M2.1a C1, M2.1b C2, M2.1c C3); C4 stays.
Phase 3 raises C2 to 1.2.0 (M3.1, PHASE-3.md 5); C1, C3 and C4 keep Phase 2's versions.
Phase 4 raises C3 to 1.2.0 (M4.2, PHASE-4.md 5) and the contracts to 1.3.0; C1, C2 and C4 keep
Phase 3's versions.
"""

from typing import Final

RECORD: Final = "1.1.0"
GRAPH_SCHEMA: Final = "1.2.0"
API: Final = "1.2.0"
ALERT: Final = "1.0.0"
CONTRACTS: Final = "1.3.0"
