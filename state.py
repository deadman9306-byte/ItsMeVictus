"""
Shared mutable runtime state.
Import this module and mutate its attributes directly — never copy values out.
"""

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from core.manager import FloodManager

current_url:          Optional[str]            = None
url_registered:       bool                     = False
shutdown_in_progress: bool                     = False
cleanup_done:         bool                     = False
flask_shutting_down:  bool                     = False
manager:              Optional["FloodManager"] = None
