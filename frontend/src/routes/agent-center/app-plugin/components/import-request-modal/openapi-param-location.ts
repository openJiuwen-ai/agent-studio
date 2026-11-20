/**
 * Map OpenAPI parameter `in` to tool schema location values.
 * Backend accepts only: Body | Headers | Query | Path.
 * OpenAPI uses singular "header", which must become "Headers".
 */
export function mapOpenApiParamLocation(
  paramIn: string | undefined | null,
): string {
  if (paramIn == null || paramIn === '') {
    return '';
  }
  const key = String(paramIn).trim().toLowerCase();
  const mapped: Record<string, string> = {
    header: 'Headers',
    headers: 'Headers',
    query: 'Query',
    path: 'Path',
    body: 'Body',
  };
  if (mapped[key]) {
    return mapped[key];
  }
  // Preserve previous capitalize-first behavior for unexpected values.
  const trimmed = String(paramIn).trim();
  return trimmed.slice(0, 1).toUpperCase() + trimmed.slice(1);
}
