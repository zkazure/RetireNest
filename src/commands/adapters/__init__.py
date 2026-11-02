"""内置命令适配器。"""

from commands.adapters.deposit import COMMAND as DEPOSIT_COMMAND
from commands.adapters.living import COMMAND as LIVING_COMMAND
from commands.adapters.medical import COMMAND as MEDICAL_COMMAND
from commands.adapters.pension import COMMAND as PENSION_COMMAND

COMMANDS = (
    MEDICAL_COMMAND,
    PENSION_COMMAND,
    DEPOSIT_COMMAND,
    LIVING_COMMAND,
)
"""当前注册的四个命令，顺序即清单顺序。"""

__all__ = ["COMMANDS"]
