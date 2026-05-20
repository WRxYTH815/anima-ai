"""
Example plugin: injects the current time into the system prompt.

Copy this file, rename it, change the class, drop it in plugins/.
It will be auto-discovered on next server start — no other changes needed.
"""

from datetime import datetime
from anima_plugin_base import AnimaPlugin


class TimePlugin(AnimaPlugin):
    def get_context(self) -> str:
        return f"[Current time: {datetime.now().strftime('%A %I:%M %p')}]"
