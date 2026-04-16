/**
 * UI 模式管理器
 * 负责管理 classic 和 ai 两种 UI 模式的切换和默认值
 */

import type { AppPage, UIMode } from './pageTypes';
import { DEFAULT_PAGE } from './pageTypes';

export const MODE_DEFAULT_PAGES: Record<UIMode, AppPage> = {
  'classic': 'dashboard',
  'ai': 'ai-command-center'
};

export function getDefaultPageForMode(mode: UIMode): AppPage {
  return MODE_DEFAULT_PAGES[mode] || DEFAULT_PAGE;
}

export function isValidUIMode(mode: string): mode is UIMode {
  return mode === 'classic' || mode === 'ai';
}

export function getUIModeFromString(mode: string): UIMode {
  return isValidUIMode(mode) ? mode : 'classic';
}
