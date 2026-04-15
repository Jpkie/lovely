/**
 * @tauri-apps/api/event shim
 * 将 Tauri 事件系统替换为基于 WebSocket 的实现
 */

type EventCallback<T = any> = (event: { event: string; id: number; payload: T }) => void;

// 事件监听器存储
const listeners: Map<string, Set<EventCallback>> = new Map();

// WebSocket 连接（可选，用于服务端推送）
let ws: WebSocket | null = null;
let wsConnected = false;

const WS_URL = 'ws://127.0.0.1:3001/ws/events';

/**
 * 初始化 WebSocket 事件连接
 */
function initWebSocket() {
  if (ws) return;

  try {
    ws = new WebSocket(WS_URL);
    ws.onopen = () => {
      wsConnected = true;
      console.log('[event-shim] WebSocket 事件通道已连接');
    };
    ws.onmessage = (msg) => {
      try {
        const data = JSON.parse(msg.data);
        if (data.type && data.type !== 'pong') {
          _emitLocal(data.type, data.payload);
        }
      } catch {}
    };
    ws.onclose = () => {
      wsConnected = false;
      ws = null;
      // 3秒后重连
      setTimeout(initWebSocket, 3000);
    };
    ws.onerror = () => {};
  } catch {
    // WebSocket 不可用时静默失败
  }
}

/**
 * 内部触发本地事件
 */
function _emitLocal(event: string, payload?: any) {
  const cbs = listeners.get(event);
  if (cbs) {
    const id = Date.now();
    cbs.forEach(cb => {
      try {
        cb({ event, id, payload });
      } catch (e) {
        console.error(`[event-shim] 事件回调错误:`, e);
      }
    });
  }
}

/**
 * 监听事件
 */
export async function listen<T = any>(
  event: string,
  handler: EventCallback<T>
): Promise<() => void> {
  if (!listeners.has(event)) {
    listeners.set(event, new Set());
  }
  listeners.get(event)!.add(handler as EventCallback);

  // 尝试初始化 WebSocket
  initWebSocket();

  // 返回取消监听函数
  return () => {
    const cbs = listeners.get(event);
    if (cbs) {
      cbs.delete(handler as EventCallback);
      if (cbs.size === 0) {
        listeners.delete(event);
      }
    }
  };
}

/**
 * 监听一次性事件
 */
export async function once<T = any>(
  event: string,
  handler: EventCallback<T>
): Promise<() => void> {
  const wrappedHandler: EventCallback<T> = (e) => {
    handler(e);
    unlisten();
  };

  const unlisten = await listen(event, wrappedHandler);
  return unlisten;
}

/**
 * 触发事件（发送到服务端 + 本地广播）
 */
export async function emit(event: string, payload?: any): Promise<void> {
  // 本地广播
  _emitLocal(event, payload);

  // 尝试通过 WebSocket 发送到服务端
  if (ws && wsConnected) {
    try {
      ws.send(JSON.stringify({ type: event, payload }));
    } catch {}
  }
}

/**
 * 触发事件到指定窗口（在纯 Web 模式下等同于 emit）
 */
export async function emitTo(
  _target: string,
  event: string,
  payload?: any
): Promise<void> {
  return emit(event, payload);
}
