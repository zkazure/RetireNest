"""commands：可发现的领域命令。

每个命令由 manifest（question、inputs、outputs、单位、约束）和 handler
（输入 -> 输出）组成；HTTP 层只负责发现和执行，不决定页面结构。
"""

from commands.models import Command, CommandManifest, InputSpec, OutputSpec
from commands.registry import (
    PROTOCOL_VERSION,
    execute_command,
    get_command,
    list_commands,
    manifest_to_dict,
)

__all__ = [
    "PROTOCOL_VERSION",
    "Command",
    "CommandManifest",
    "InputSpec",
    "OutputSpec",
    "execute_command",
    "get_command",
    "list_commands",
    "manifest_to_dict",
]
