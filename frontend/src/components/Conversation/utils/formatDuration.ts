/**
 * 格式化duration（毫秒）为可读字符串
 * 例如: 1d1h30m, 1h30m, 30s
 *
 * @param ms - 毫秒数
 * @returns 格式化后的字符串，如果输入为空则返回 null
 */
export const formatDuration = (ms?: number): string | null => {
  if (!ms) return null;

  const totalSeconds = Math.floor(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);

  const parts: string[] = [];
  if (days > 0) parts.push(`${days}d`);
  if (hours % 24 > 0) parts.push(`${hours % 24}h`);
  if (minutes % 60 > 0) parts.push(`${minutes % 60}m`);
  if ((totalSeconds % 60 > 0) || (parts.length === 0 && totalSeconds > 0)) {
    parts.push(`${totalSeconds % 60}s`);
  }

  return parts.join('');
};
