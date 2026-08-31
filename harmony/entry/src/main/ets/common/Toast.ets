/**
 * 轻提示与错误提示。
 *
 * 统一出口的意义：`ApiError` 的展示格式只定义一次，
 * 且「toast 失败」永远不会反过来炸掉调用方（promptAction 在某些窗口态会抛错）。
 */
import promptAction from '@ohos.promptAction';
import { ApiError } from './ApiClient';

export function toast(message: string, durationMs: number = 2000): void {
  if (!message || message.length === 0) {
    return;
  }
  try {
    promptAction.showToast({ message: message, duration: durationMs });
  } catch (e) {
    // 窗口未就绪等极端情况下静默失败：提示不到位远好于崩溃
  }
}

/** 把任意异常转成用户可读的一句话。 */
export function errorText(err: object): string {
  if (err instanceof ApiError) {
    return err.message;
  }
  const e = err as Error;
  if (e && e.message && e.message.length > 0) {
    return e.message;
  }
  return '操作失败，请重试';
}

export function toastError(err: object): void {
  toast(errorText(err), 2500);
}
