"""Load standalone ATED submodules without importing Home Assistant integration root."""
from pathlib import Path
import sys
import types

ROOT = Path(__file__).resolve().parents[1]
CC = ROOT / "custom_components"
ATED = CC / "ated_core"

custom_components = types.ModuleType("custom_components")
custom_components.__path__ = [str(CC)]
sys.modules.setdefault("custom_components", custom_components)

ated_core = types.ModuleType("custom_components.ated_core")
ated_core.__path__ = [str(ATED)]
sys.modules.setdefault("custom_components.ated_core", ated_core)
