import styled from 'styled-components'

export const NodeWrap = styled.div<{ disabled?: boolean }>`
  width: 100%;
  height: 32px;
  border-radius: 5px;
  display: flex;
  align-items: center;
  cursor: pointer;
  font-size: 19px;
  padding: 0 15px;
  transition: all 0.2s ease-in-out;
  opacity: ${props => (props.disabled ? 0.3 : 1)};
  color: var(--workflow-text-primary);

  &:hover {
    background-color: var(--workflow-bg-hover);
    color: var(--accent-primary);
    transform: translateX(2px);
  }
`

export const NodeLabel = styled.div`
  font-size: 12px;
  margin-left: 10px;
  color: var(--workflow-text-primary);
`

export const NodesContainer = styled.div`
  max-height: 500px;
  overflow: auto;
  border-radius: 8px;
  width: 100%;
  background-color: var(--workflow-bg-surface);
  cursor: pointer;

  &::-webkit-scrollbar {
    display: none;
  }
`

export const SearchContainer = styled.div`
  padding: 12px 12px 8px;
  border-bottom: 1px solid var(--workflow-border-input);
`

export const CategoriesContainer = styled.div`
  padding: 8px 8px 8px;
`

export const CategoryTitle = styled.div`
  font-size: 12px;
  font-weight: 500;
  color: var(--workflow-text-tertiary);
  padding: 4px 4px;
`

export const NodesGrid = styled.div`
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
`
