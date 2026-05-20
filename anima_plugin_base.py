"""
anima_plugin_base.py — Plugin architecture (inspired by Synthetic Heart).

Drop a .py file in plugins/ with a class that extends AnimaPlugin.
It's auto-discovered on start — no core modifications needed.

Plugin contract:
  get_supported_actions() -> dict  # optional — action_name: description
  get_context()           -> str   # optional — injected into system prompt
  start() / stop()                 # optional lifecycle hooks

Example plugin file (plugins/weather_plugin.py):
  from anima_plugin_base import AnimaPlugin
  class WeatherPlugin(AnimaPlugin):
      def get_context(self):
          return "[Current weather: sunny, 22°C]"
"""

import os
import importlib
import inspect


class AnimaPlugin:
    """Base class for all Anima plugins."""

    @property
    def name(self) -> str:
        return self.__class__.__name__

    def get_supported_actions(self) -> dict[str, str]:
        """Return {action_name: description} for LLM-selectable actions."""
        return {}

    def get_context(self) -> str:
        """Return a string injected into the system prompt, or empty string."""
        return ""

    def start(self):
        """Called once on discovery. Use for initialisation."""

    def stop(self):
        """Called on shutdown."""


# ── Registry ──────────────────────────────────────────────────────────────────

_registry: dict[str, AnimaPlugin] = {}


def register(plugin: AnimaPlugin):
    _registry[plugin.name] = plugin
    print(f"🔌 [Plugin] Registered: {plugin.name}", flush=True)


def discover(plugins_dir: str | None = None):
    """Auto-discover and register AnimaPlugin subclasses from plugins/."""
    if plugins_dir is None:
        plugins_dir = os.path.join(os.path.dirname(__file__), "plugins")
    if not os.path.isdir(plugins_dir):
        return

    for fname in sorted(os.listdir(plugins_dir)):
        if not fname.endswith(".py") or fname.startswith("_"):
            continue
        module_name = f"plugins.{fname[:-3]}"
        try:
            mod = importlib.import_module(module_name)
            for _, cls in inspect.getmembers(mod, inspect.isclass):
                if (issubclass(cls, AnimaPlugin)
                        and cls is not AnimaPlugin
                        and cls.__name__ not in _registry):
                    instance = cls()
                    register(instance)
                    instance.start()
        except Exception as e:
            print(f"⚠️ [Plugin] Failed to load {fname}: {e}", flush=True)


def get_all_context() -> str:
    """Collect context strings from all plugins for prompt injection."""
    parts = [p.get_context() for p in _registry.values() if p.get_context()]
    return "\n".join(parts)


def get_all_actions() -> dict[str, str]:
    actions: dict[str, str] = {}
    for plugin in _registry.values():
        actions.update(plugin.get_supported_actions())
    return actions


def stop_all():
    for plugin in _registry.values():
        try:
            plugin.stop()
        except Exception:
            pass
