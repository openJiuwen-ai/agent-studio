import type { Root } from 'mdast'
import type { Position } from 'unist'

/**
 * remark-math's `singleDollarTextMath` has no way to tell a lone `$` used for
 * math (`$x=1$`) apart from one used for currency (`price from $30 to $40`).
 * VS Code's built-in KaTeX preview solves this with a regex that requires the
 * character just outside each delimiter to not be a letter/digit
 * (`(?<![a-zA-Z0-9])$...$(?![a-zA-Z0-9])`, see
 * microsoft/vscode markedKatexExtension.ts). This mirrors that rule as a
 * post-parse AST fixup: any single-`$` inline-math span touching a
 * letter/digit on either side is demoted back to plain text. `$$...$$`
 * sequences are left untouched since two dollars in a row is never currency.
 */
export function remarkDemoteFalsePositiveInlineMath() {
  return (tree: Root, file: { value: string | Uint8Array }) => {
    demoteInChildren(tree, String(file.value))
  }
}

interface InlineMathNode {
  type: 'inlineMath'
  position?: Position
}

interface WalkableNode {
  type: string
  children?: unknown[]
}

const ALNUM_PATTERN = /[a-zA-Z0-9]/

const isAlnum = (char: string | undefined): boolean => char !== undefined && ALNUM_PATTERN.test(char)

function isFalsePositiveInlineMath(node: Required<InlineMathNode>, rawMarkdown: string): boolean {
  const { start, end } = node.position
  const isSingleDollar =
    rawMarkdown[start.offset!] === '$' && rawMarkdown[start.offset! + 1] !== '$'

  if (!isSingleDollar) {
    return false
  }

  const before = rawMarkdown[start.offset! - 1]
  const after = rawMarkdown[end.offset!]
  return isAlnum(before) || isAlnum(after)
}

function demoteInChildren(node: WalkableNode, rawMarkdown: string): void {
  if (!Array.isArray(node.children)) {
    return
  }

  node.children = node.children.map((child) => {
    const candidate = child as WalkableNode & InlineMathNode

    if (candidate.type === 'inlineMath' && candidate.position) {
      if (isFalsePositiveInlineMath(candidate as Required<InlineMathNode>, rawMarkdown)) {
        const { start, end } = candidate.position
        return {
          type: 'text',
          value: rawMarkdown.slice(start.offset!, end.offset!),
          position: candidate.position,
        }
      }
    }

    demoteInChildren(candidate, rawMarkdown)
    return child
  })
}
