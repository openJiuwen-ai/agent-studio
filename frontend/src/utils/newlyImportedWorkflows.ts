/**
 * Utility functions to manage newly imported workflow IDs
 * Uses localStorage for session-based tracking
 */

const STORAGE_KEY = 'newly_imported_workflows'

/**
 * Add a workflow ID to the newly imported list
 */
export function markWorkflowAsNewlyImported(workflowId: string): void {
  const imported = getNewlyImportedWorkflows()
  if (!imported.includes(workflowId)) {
    imported.push(workflowId)
    localStorage.setItem(STORAGE_KEY, JSON.stringify(imported))
  }
}

/**
 * Check if a workflow is newly imported
 */
export function isWorkflowNewlyImported(workflowId: string): boolean {
  const imported = getNewlyImportedWorkflows()
  return imported.includes(workflowId)
}

/**
 * Remove a workflow from the newly imported list (when user opens it)
 */
export function clearNewlyImportedFlag(workflowId: string): void {
  const imported = getNewlyImportedWorkflows()
  const filtered = imported.filter(id => id !== workflowId)
  localStorage.setItem(STORAGE_KEY, JSON.stringify(filtered))
}

/**
 * Get all newly imported workflow IDs
 */
export function getNewlyImportedWorkflows(): string[] {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    return stored ? JSON.parse(stored) : []
  } catch {
    return []
  }
}

/**
 * Clear all newly imported flags
 */
export function clearAllNewlyImportedFlags(): void {
  localStorage.removeItem(STORAGE_KEY)
}
