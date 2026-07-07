import React, { useState, useEffect, useRef, useMemo } from 'react'
import {
  Box, CircularProgress, Collapse, Dialog, DialogContent, DialogTitle, Divider, IconButton,
  List, ListItemButton, ListItemText, Typography,
} from '@mui/material'
import { ChevronDown, ChevronRight, X } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { useAuthStore } from '@/stores/useAuthStore'

// Single source of truth: docs live in docs/en/.../Evaluation Agent and Workflow/
// and are served by GET /api/v1/evaluation/docs/{filename}
const DOCS = [
  { id: 'user-guide',      label: 'User Guide',                  filename: '03_User_Guide.md' },
  { id: 'reference',       label: 'Tasks & Graders',             filename: '04_Reference.md' },
  { id: 'cookbook',        label: 'Cookbook (recipes)',           filename: '07_Cookbook.md' },
  { id: 'troubleshooting', label: 'Troubleshooting',             filename: '08_Troubleshooting.md' },
  { id: 'glossary',        label: 'Glossary',                    filename: '09_Glossary.md' },
  { id: 'import-guide',    label: 'Import from Another System',  filename: '10_Import_Guide.md' },
]

interface HeadingNode {
  id: string
  text: string
  level: number
}

// Extract headings (H2 only - ##) from markdown content
// Skips headings inside code blocks
function extractHeadings(markdown: string): HeadingNode[] {
  const headings: HeadingNode[] = []
  const lines = markdown.split('\n')
  let inCodeBlock = false

  for (const line of lines) {
    // Check for code block delimiters (``` or ~~~)
    if (line.trim().startsWith('```') || line.trim().startsWith('~~~')) {
      inCodeBlock = !inCodeBlock
      continue
    }

    // Skip headings inside code blocks
    if (inCodeBlock) continue

    const match = line.match(/^(#{2})\s+(.+)$/) // Only H2 (##)
    if (match) {
      const level = match[1].length
      const text = match[2].trim()
      // Create a simple ID from the heading text
      const id = text
        .toLowerCase()
        .replace(/[^\w\s-]/g, '')
        .replace(/\s+/g, '-')

      headings.push({ id, text, level })
    }
  }

  return headings
}

interface Props {
  open: boolean
  onClose: () => void
}

export default function EvaluationHelpModal({ open, onClose }: Props) {
  const [activeId, setActiveId] = useState(DOCS[0].id)
  const [docContent, setDocContent] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(false)
  const [fetchError, setFetchError] = useState<string | null>(null)
  const [expandedDocs, setExpandedDocs] = useState<Set<string>>(new Set()) // All collapsed by default
  const fetchedIds = useRef<Set<string>>(new Set())
  const contentRef = useRef<HTMLDivElement>(null)
  const token = useAuthStore((s) => s.token)

  const activeDoc = DOCS.find(d => d.id === activeId) ?? DOCS[0]

  // Extract headings for the active document
  const headings = useMemo(() => {
    const content = docContent[activeId]
    return content ? extractHeadings(content) : []
  }, [docContent, activeId])

  const toggleExpanded = (docId: string) => {
    setExpandedDocs(prev => {
      const next = new Set(prev)
      if (next.has(docId)) {
        next.delete(docId)
      } else {
        next.add(docId)
      }
      return next
    })
  }

  const scrollToHeading = (headingId: string) => {
    // Use requestAnimationFrame to ensure DOM is ready
    requestAnimationFrame(() => {
      const element = contentRef.current?.querySelector(`#${CSS.escape(headingId)}`)
      if (element) {
        element.scrollIntoView({ behavior: 'smooth', block: 'start' })
      }
    })
  }

  const loadDoc = async (doc: typeof DOCS[0]) => {
    if (fetchedIds.current.has(doc.id)) return
    fetchedIds.current.add(doc.id)
    setLoading(true)
    setFetchError(null)
    try {
      const res = await fetch(`/api/v1/evaluation/docs/${doc.filename}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const text = await res.text()
      setDocContent(prev => ({ ...prev, [doc.id]: text }))
    } catch {
      fetchedIds.current.delete(doc.id)
      setFetchError(`Failed to load "${doc.label}". Check backend connectivity.`)
    } finally {
      setLoading(false)
    }
  }

  // Fetch on open and on tab switch
  useEffect(() => {
    if (open) loadDoc(activeDoc)
  }, [open, activeId])

  return (
    <Dialog open={open} onClose={onClose} maxWidth="lg" fullWidth PaperProps={{ sx: { height: '85vh' } }}>
      <DialogTitle sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', py: 1.5 }}>
        <Typography variant="h6" fontWeight={600}>
          Evaluation Help - {activeDoc.label}
        </Typography>
        <IconButton size="small" onClick={onClose}><X size={18} /></IconButton>
      </DialogTitle>
      <Divider />
      <DialogContent sx={{ p: 0, display: 'flex', overflow: 'hidden' }}>
        {/* Sidebar */}
        <Box sx={{ width: 240, borderRight: '1px solid', borderColor: 'divider', flexShrink: 0, overflowY: 'auto' }}>
          <List dense disablePadding>
            {DOCS.map(doc => {
              const isActive = doc.id === activeId
              const isExpanded = expandedDocs.has(doc.id)
              const isLoaded = !!docContent[doc.id]
              const docHeadings = isActive ? headings : (isLoaded ? extractHeadings(docContent[doc.id]) : [])

              // Show chevron if: not loaded yet OR has headings after loading
              const showChevron = !isLoaded || docHeadings.length > 0

              return (
                <React.Fragment key={doc.id}>
                  <ListItemButton
                    selected={isActive}
                    onClick={() => {
                      setActiveId(doc.id)
                      if (showChevron) {
                        toggleExpanded(doc.id)
                      }
                    }}
                    sx={{
                      borderLeft: isActive ? '3px solid' : '3px solid transparent',
                      borderColor: 'primary.main',
                      pr: 0.5,
                    }}
                  >
                    <ListItemText
                      primary={doc.label}
                      primaryTypographyProps={{ variant: 'body2', fontWeight: isActive ? 600 : 400 }}
                    />
                    {showChevron && (
                      <IconButton
                        size="small"
                        onClick={(e) => {
                          e.stopPropagation()
                          toggleExpanded(doc.id)
                        }}
                        sx={{ p: 0.5 }}
                      >
                        {isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                      </IconButton>
                    )}
                  </ListItemButton>

                  {/* Sub-sections */}
                  {isLoaded && docHeadings.length > 0 && (
                    <Collapse in={isExpanded} timeout="auto" unmountOnExit>
                      <List dense disablePadding sx={{ pl: 2 }}>
                        {docHeadings.map((heading) => (
                          <ListItemButton
                            key={heading.id}
                            onClick={() => {
                              if (!isActive) {
                                setActiveId(doc.id)
                              }
                              // Always use timeout to ensure content is rendered
                              setTimeout(() => scrollToHeading(heading.id), 200)
                            }}
                            sx={{
                              py: 0.25,
                              pl: 1,
                              minHeight: 'auto',
                            }}
                          >
                            <ListItemText
                              primary={heading.text}
                              primaryTypographyProps={{
                                variant: 'caption',
                                fontSize: '0.75rem',
                                color: 'text.secondary',
                              }}
                            />
                          </ListItemButton>
                        ))}
                      </List>
                    </Collapse>
                  )}
                </React.Fragment>
              )
            })}
          </List>
        </Box>

        {/* Content */}
        <Box ref={contentRef} sx={{ flex: 1, overflowY: 'auto', p: 3 }}>
          {loading && !docContent[activeId] && (
            <Box sx={{ display: 'flex', justifyContent: 'center', pt: 6 }}>
              <CircularProgress size={32} />
            </Box>
          )}
          {fetchError && !docContent[activeId] && (
            <Typography color="error" variant="body2" sx={{ pt: 4, textAlign: 'center' }}>
              {fetchError}
            </Typography>
          )}
          {docContent[activeId] && (
            <Box
              sx={{
                '& h1': { fontSize: '1.5rem', fontWeight: 700, mb: 1, mt: 0, scrollMarginTop: '20px' },
                '& h2': { fontSize: '1.15rem', fontWeight: 600, mb: 0.75, mt: 2.5, borderBottom: '1px solid', borderColor: 'divider', pb: 0.5, scrollMarginTop: '20px' },
                '& h3': { fontSize: '1rem', fontWeight: 600, mb: 0.5, mt: 2, scrollMarginTop: '20px' },
                '& h4': { fontSize: '0.9rem', fontWeight: 600, mb: 0.5, mt: 1.5 },
                '& p': { mb: 1, lineHeight: 1.7 },
                '& ul, & ol': { pl: 2.5, mb: 1 },
                '& li': { mb: 0.25 },
                '& code': { fontFamily: 'monospace', fontSize: '0.82rem', bgcolor: 'grey.100', px: 0.5, py: 0.1, borderRadius: 0.5 },
                '& pre': { bgcolor: 'grey.100', p: 1.5, borderRadius: 1, overflowX: 'auto', mb: 1.5, fontSize: '0.8rem', fontFamily: 'monospace', border: '1px solid', borderColor: 'divider' },
                '& pre code': { bgcolor: 'transparent', p: 0 },
                '& blockquote': { borderLeft: '3px solid', borderColor: 'primary.main', pl: 2, ml: 0, color: 'text.secondary', my: 1 },
                '& table': { borderCollapse: 'collapse', width: '100%', mb: 1.5, fontSize: '0.85rem', border: '1px solid', borderColor: 'divider' },
                '& thead': { bgcolor: 'grey.50' },
                '& th': { bgcolor: 'grey.100', fontWeight: 600, border: '1px solid', borderColor: 'divider', px: 1.5, py: 1, textAlign: 'left' },
                '& td': { border: '1px solid', borderColor: 'divider', px: 1.5, py: 0.75 },
                '& tbody tr:nth-of-type(even)': { bgcolor: 'grey.50' },
                '& hr': { my: 2, borderColor: 'divider' },
                '& a': { color: 'primary.main', textDecoration: 'underline' },
              }}
            >
              <ReactMarkdown
                remarkPlugins={[[remarkGfm, { singleTilde: false }]]}
                components={{
                  // Add IDs only to H2 (##) for navigation
                  h2: ({ children, ...props }) => {
                    // Extract text from children (could be string or array)
                    const text = Array.isArray(children)
                      ? children.join('')
                      : String(children)
                    const id = text
                      .toLowerCase()
                      .replace(/[^\w\s-]/g, '')
                      .replace(/\s+/g, '-')
                    return <h2 id={id} {...props}>{children}</h2>
                  },
                }}
              >
                {docContent[activeId]}
              </ReactMarkdown>
            </Box>
          )}
        </Box>
      </DialogContent>
    </Dialog>
  )
}
