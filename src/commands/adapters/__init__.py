"""内置命令适配器。"""

from commands.adapters.deposit import COMMAND as DEPOSIT_COMMAND
from commands.adapters.inflation import COMMAND as INFLATION_COMMAND
from commands.adapters.lifecycle import COMMANDS as LIFECYCLE_COMMANDS
from commands.adapters.living import COMMAND as LIVING_COMMAND
from commands.adapters.longevity import COMMAND as LONGEVITY_COMMAND
from commands.adapters.medical import COMMAND as MEDICAL_COMMAND
from commands.adapters.pension import COMMAND as PENSION_COMMAND
from commands.adapters.savings import COMMANDS as SAVINGS_COMMANDS
from commands.adapters.simulation import COMMANDS as SIMULATION_COMMANDS

COMMANDS = (
    MEDICAL_COMMAND,
    PENSION_COMMAND,
    DEPOSIT_COMMAND,
    LIVING_COMMAND,
    *SAVINGS_COMMANDS,
    INFLATION_COMMAND,
    *SIMULATION_COMMANDS,
    LONGEVITY_COMMAND,
    *LIFECYCLE_COMMANDS,
)
"""当前注册的十三个命令，顺序即清单顺序。"""

__all__ = ["COMMANDS"]
