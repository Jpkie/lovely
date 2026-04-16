/**
 * 导航配置模块
 * 定义所有导航项的结构、模式可见性和排序
 */

import type { AppPage, UIMode } from './pageTypes';

export type IconKey =
  | 'Dashboard'
  | 'ApplicationMenu'
  | 'FolderOpen'
  | 'Code'
  | 'Rocket'
  | 'Data'
  | 'Log'
  | 'Robot'
  | 'Calendar'
  | 'SettingTwo'
  | 'User'
  | 'Lock'
  | 'Shield'
  | 'Analysis'
  | 'Fire'
  | 'FileText'
  | 'Config'
  | 'NetworkTree'
  | 'System'
  | 'Time'
  | 'SettingConfig'
  | 'Cpu'
  | 'Memory'
  | 'Speed'
  | 'LinkCloud'
  | 'BookOpen'
  | 'Message'
  | 'CheckOne'
  | 'CloseOne'
  | 'Refresh'
  | 'Copy'
  | 'Loading'
  | 'Send';

export interface NavigationItem {
  id: AppPage;
  title: string;
  description: string;
  iconKey: IconKey;
  visibleInModes: UIMode[];
}

const ALL_NAV_ITEMS: NavigationItem[] = [
  {
    id: 'dashboard',
    title: '仪表板',
    description: '查看服务器实时状态概览',
    iconKey: 'Dashboard',
    visibleInModes: ['classic', 'ai']
  },
  {
    id: 'system-info',
    title: '系统信息',
    description: '查看详细系统配置信息',
    iconKey: 'ApplicationMenu',
    visibleInModes: ['classic', 'ai']
  },
  {
    id: 'remote-operations',
    title: 'SFTP文件',
    description: '远程文件管理与传输',
    iconKey: 'FolderOpen',
    visibleInModes: ['classic', 'ai']
  },
  {
    id: 'emergency-commands',
    title: '命令执行',
    description: '批量执行应急响应命令',
    iconKey: 'Code',
    visibleInModes: ['classic', 'ai']
  },
  {
    id: 'quick-detection',
    title: '快速检测',
    description: '一键安全检测与风险评估',
    iconKey: 'Rocket',
    visibleInModes: ['classic', 'ai']
  },
  {
    id: 'database',
    title: '数据库',
    description: '数据库管理(暂不可用)',
    iconKey: 'Data',
    visibleInModes: ['classic']
  },
  {
    id: 'log-analysis',
    title: '日志审计',
    description: '系统日志分析与溯源',
    iconKey: 'Log',
    visibleInModes: ['classic', 'ai']
  },
  {
    id: 'ai-chat',
    title: 'AI聊天',
    description: 'AI智能助手辅助分析',
    iconKey: 'Robot',
    visibleInModes: ['classic']
  },
  {
    id: 'ai-command-center',
    title: 'AI命令中心',
    description: '智能任务编排与执行',
    iconKey: 'Robot',
    visibleInModes: ['classic', 'ai']
  },
  {
    id: 'payloader',
    title: 'Payload工具',
    description: '安全测试Payload生成',
    iconKey: 'Code',
    visibleInModes: ['classic']
  },
  {
    id: 'ssh-terminal',
    title: 'SSH终端',
    description: '远程SSH终端连接',
    iconKey: 'Code',
    visibleInModes: ['classic', 'ai']
  },
  {
    id: 'settings',
    title: '设置',
    description: '应用设置',
    iconKey: 'SettingConfig',
    visibleInModes: ['classic', 'ai']
  }
];

const NAV_ORDER: Record<UIMode, AppPage[]> = {
  'classic': [
    'dashboard',
    'system-info',
    'remote-operations',
    'emergency-commands',
    'quick-detection',
    'database',
    'log-analysis',
    'ai-chat',
    'ai-command-center',
    'payloader',
    'ssh-terminal',
    'settings'
  ],
  'ai': [
    'ai-command-center',
    'quick-detection',
    'log-analysis',
    'ssh-terminal',
    'remote-operations',
    'emergency-commands',
    'system-info',
    'settings',
    'dashboard'
  ]
};

export const NAVIGATION_ITEMS: NavigationItem[] = ALL_NAV_ITEMS;

export function getNavigationItemsForMode(mode: UIMode): NavigationItem[] {
  const order = NAV_ORDER[mode];
  const visibleItems = NAVIGATION_ITEMS.filter(item => item.visibleInModes.includes(mode));

  return order
    .map(id => visibleItems.find(item => item.id === id))
    .filter((item): item is NavigationItem => item !== undefined);
}

export function getNavigationItemById(id: AppPage): NavigationItem | undefined {
  return NAVIGATION_ITEMS.find(item => item.id === id);
}
