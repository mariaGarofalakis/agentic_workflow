import importlib
from app.core.logging import get_logger
import pkgutil

import app.tools as tools_pkg
from app.tools.core.registry import ToolRegistry

logger = get_logger(__name__)

def build_registry() -> ToolRegistry:
    registry = ToolRegistry()
    
    for _, module_name, is_pkg in pkgutil.iter_modules(tools_pkg.__path__):
        if is_pkg:
            continue
        module = importlib.import_module(f"app.tools.{module_name}")
        for attr_name in dir(module):
            if attr_name.startswith("register_") and callable(getattr(module, attr_name)):
                getattr(module, attr_name)(registry)
                logger.info("Auto registered tools from %s.%s", module_name,attr_name)

    return registry
