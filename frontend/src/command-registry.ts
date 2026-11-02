import { CommandApiError, executeCommand, fetchCommands } from './command-client';
import type { CommandManifest } from './command-types';

// 前端显式注册：后端新增命令不会自动出现在页面里，必须在这里放行。
const ENABLED_COMMANDS = new Set([
  'lifecycle.project',
  'lifecycle.simulate',
  'strategy.compare',
  'medical.estimate',
  'pension.basic',
  'deposit.demand',
  'living.calculate',
  'savings.project',
  'savings.goal',
  'inflation.convert',
  'simulation.retirement',
  'withdrawal.safe_rate',
  'longevity.estimate',
]);

let manifests = new Map<string, CommandManifest>();

export async function loadCommands(): Promise<CommandManifest[]> {
  const response = await fetchCommands();
  const enabled = response.commands.filter(command => ENABLED_COMMANDS.has(command.id));
  manifests = new Map(enabled.map(command => [command.id, command]));
  return [...manifests.values()];
}

export function getCommands(): CommandManifest[] {
  return [...manifests.values()];
}

export function getCommand(commandId: string): CommandManifest | undefined {
  return manifests.get(commandId);
}

export async function runCommand(
  commandId: string,
  inputs: Record<string, unknown>,
) {
  const command = manifests.get(commandId);
  if (!command) {
    throw new CommandApiError('UNREGISTERED_COMMAND', `命令未在前端注册：${commandId}`);
  }
  return executeCommand(command.id, command.version, inputs);
}
