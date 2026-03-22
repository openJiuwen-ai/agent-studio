import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Message, TaskStatus, useConversationStore } from '../../../stores/useConversationStore';
import { Play, ChevronDown, ChevronUp, Plus, Trash2, X } from 'lucide-react';
import EditIcon from '@/assets/icons/edit.svg?react';

interface OutlineInteractionMessageProps {
  message: Message;
}

interface OutlineSection {
  id?: string;
  title: string;
  description?: string;
  is_core_section?: boolean;
  parent_ids?: string[];
  relationships?: any[];
  plans?: any[];
}

interface OutlineContent {
  id?: string;
  language?: string;
  thought?: string;
  title?: string;
  sections?: OutlineSection[];
  outlineInteractionCurrentRound?: number;
  outlineInteractionRemainingRounds?: number;
  outlineInteractionRemainingTip?: string;
}

export const OutlineInteractionMessage: React.FC<OutlineInteractionMessageProps> = ({ message }) => {
  const { t } = useTranslation();
  const [expandedSections, setExpandedSections] = useState<Set<number>>(new Set());
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [editableSections, setEditableSections] = useState<OutlineSection[]>([]);
  const updateMessage = useConversationStore(state => state.updateMessage);
  const updateMessageItems = useConversationStore(state => state.updateMessageItems);
  const getCurrentMessageItems = useConversationStore(state => state.getCurrentMessageItems);

  const outlineContent: OutlineContent = typeof message.content === 'string'
    ? (() => {
        try {
          return JSON.parse(message.content);
        } catch {
          return {};
        }
      })()
    : (message.content as OutlineContent) || {};

  const { sections } = outlineContent;
  const thoughtText = typeof outlineContent.thought === 'string'
    ? outlineContent.thought
    : '';
  const remainingRoundsTip = typeof outlineContent.outlineInteractionRemainingTip === 'string'
    ? outlineContent.outlineInteractionRemainingTip
    : '';

  const isWaiting = message.status === TaskStatus.PENDING || message.status === TaskStatus.IN_PROGRESS;

  const toggleSection = (index: number) => {
    setExpandedSections(prev => {
      const newSet = new Set(prev);
      if (newSet.has(index)) {
        newSet.delete(index);
      } else {
        newSet.add(index);
      }
      return newSet;
    });
  };

  const markOutlineInteractionAsCompleted = (
    userMessage: string,
    interruptFeedback: string,
    backendMessage?: string,
    updatedOutlineContent?: OutlineContent
  ) => {
    const messageItemsList = getCurrentMessageItems();
    if (!messageItemsList || messageItemsList.length === 0) return;

    const lastMessageItems = messageItemsList[messageItemsList.length - 1];
    if (!lastMessageItems) return;

    const messageUpdates: Partial<Message> = {
      status: TaskStatus.COMPLETED,
    };
    if (updatedOutlineContent) {
      messageUpdates.content = updatedOutlineContent as any;
    }

    updateMessage(lastMessageItems.id, message.id, messageUpdates);
    updateMessageItems(lastMessageItems.id, { status: TaskStatus.COMPLETED });
    useConversationStore.getState().triggerOutlineInteractionAccept(message.id, userMessage, backendMessage, interruptFeedback);
  };

  const handleStartResearch = async () => {
    const userMessage = t('apps.outlineInteraction.startResearch');
    markOutlineInteractionAsCompleted(userMessage, 'accepted', userMessage);
  };

  const handleOpenEditModal = () => {
    if (!isWaiting) return;
    setEditableSections((sections || []).map(section => ({
      ...section,
      parent_ids: Array.isArray(section.parent_ids) ? [...section.parent_ids] : [],
      relationships: Array.isArray(section.relationships) ? [...section.relationships] : [],
      plans: Array.isArray(section.plans) ? [...section.plans] : [],
    })));
    setIsEditModalOpen(true);
  };

  const handleCloseEditModal = () => {
    setIsEditModalOpen(false);
  };

  const handleUpdateSection = (index: number, key: 'title' | 'description', value: string) => {
    setEditableSections(prev => prev.map((section, sectionIndex) => {
      if (sectionIndex !== index) return section;
      return {
        ...section,
        [key]: value,
      };
    }));
  };

  const handleAddSection = () => {
    setEditableSections(prev => ([
      ...prev,
      {
        id: `new_${Date.now()}_${prev.length + 1}`,
        title: '',
        description: '',
        is_core_section: true,
        parent_ids: [],
        relationships: [],
        plans: [],
      },
    ]));
  };

  const handleDeleteSection = (index: number) => {
    setEditableSections(prev => prev.filter((_, sectionIndex) => sectionIndex !== index));
  };

  const handleSubmitOutlineEdit = () => {
    const {
      outlineInteractionCurrentRound,
      outlineInteractionRemainingRounds,
      outlineInteractionRemainingTip,
      ...restOutlineContent
    } = outlineContent;
    const revisedOutline: OutlineContent = {
      ...restOutlineContent,
      sections: editableSections.map(section => ({
        ...section,
        title: section.title || '',
        description: section.description || '',
      })),
    };
    const backendMessage = JSON.stringify(revisedOutline);
    markOutlineInteractionAsCompleted(
      t('apps.outlineInteraction.editAndRevisePrompt'),
      'revise_outline',
      backendMessage,
      revisedOutline
    );
    setIsEditModalOpen(false);
  };

  return (
    <div className="outline-interaction-message w-full mt-3">
      <div className="mb-2">
        {thoughtText && (
          <div className="text-[14px] leading-[24px] text-[#191919] whitespace-pre-wrap mb-1">
            {thoughtText}
          </div>
        )}
        <div className="text-[14px] leading-[24px] text-[#191919]">
          {t('apps.outlineInteraction.modifyTip')}
        </div>
        {remainingRoundsTip && (
          <div className="text-[14px] leading-[24px] text-orange-600 mt-1">
            {remainingRoundsTip}
          </div>
        )}
      </div>
      <div className="bg-white rounded-xl py-4 px-3">
        <div className="flex items-start">
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <h4 className="text-[16px] leading-[22px] font-semibold text-gray-900">
                  {t('apps.outlineInteraction.researchOutline')}
                </h4>
                <button
                  onClick={handleOpenEditModal}
                  disabled={!isWaiting}
                  className="inline-flex items-center justify-center text-gray-500 hover:text-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  title={t('apps.outlineInteraction.edit')}
                >
                  <EditIcon className="w-[14px] h-[14px]" />
                </button>
              </div>
            </div>

            {sections && sections.length > 0 && (
              <div className="bg-white">
                {sections.map((section, index) => {
                  const isExpanded = expandedSections.has(index);
                  return (
                    <div
                      key={index}
                      className={index !== sections.length - 1 ? 'bg-white border-b border-gray-200' : 'bg-white'}
                    >
                      <div
                        className="flex items-center gap-2 pl-2 pr-4 py-4 cursor-pointer hover:bg-gray-50 transition-colors"
                        onClick={() => toggleSection(index)}
                      >
                        <span className="flex-1 text-[14px] leading-[22px] font-semibold text-gray-900">
                          {section.title}
                        </span>
                        {isExpanded ? (
                          <ChevronUp size={16} className="text-gray-500 flex-shrink-0" />
                        ) : (
                          <ChevronDown size={16} className="text-gray-500 flex-shrink-0" />
                        )}
                      </div>
                      {isExpanded && section.description && (
                        <div className="pl-2 pr-4 pb-4 pt-0">
                          <div className="text-sm text-gray-600 leading-7">
                            {section.description}
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}

            <div className="pt-3 border-t border-gray-200">
              <button
                onClick={handleStartResearch}
                disabled={!isWaiting}
                className="btn-primary w-full h-10 flex items-center justify-center gap-1.5 text-base font-semibold transition-all"
              >
                <Play size={12} />
                {t('apps.outlineInteraction.startResearch')}
              </button>
            </div>
          </div>
        </div>
      </div>
      {isEditModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/35" onClick={handleCloseEditModal} />
          <div className="relative bg-white rounded-2xl shadow-xl w-[min(920px,calc(100vw-32px))] max-h-[85vh] flex flex-col">
            <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200">
              <h3 className="text-lg font-semibold text-gray-900">
                {t('apps.outlineInteraction.editOutline')}
              </h3>
              <div className="flex items-center gap-2">
                <button
                  onClick={handleAddSection}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-700 border border-gray-200 rounded-md hover:bg-gray-50"
                >
                  <Plus size={14} />
                  {t('apps.outlineInteraction.addSection')}
                </button>
                <button
                  onClick={handleCloseEditModal}
                  className="w-8 h-8 inline-flex items-center justify-center text-gray-500 rounded-md hover:bg-gray-100"
                >
                  <X size={16} />
                </button>
              </div>
            </div>
            <div className="flex-1 overflow-y-auto p-5 space-y-3">
              {editableSections.map((section, index) => (
                <div key={section.id || `section_${index}`} className="border border-gray-200 rounded-xl p-4 bg-white">
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-base font-semibold text-gray-900">
                      {t('apps.outlineInteraction.chapterLabel', { index: index + 1 })}
                    </span>
                    <button
                      onClick={() => handleDeleteSection(index)}
                      className="w-8 h-8 inline-flex items-center justify-center text-gray-500 rounded-md hover:bg-gray-100"
                    >
                      <Trash2 size={15} />
                    </button>
                  </div>
                  <div className="space-y-3">
                    <div>
                      <div className="text-sm text-gray-600 mb-1">{t('apps.outlineInteraction.sectionTitle')}</div>
                      <input
                        value={section.title || ''}
                        onChange={(e) => handleUpdateSection(index, 'title', e.target.value)}
                        placeholder={t('apps.outlineInteraction.titlePlaceholder')}
                        className="w-full h-10 px-3 border border-gray-300 rounded-md text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                    <div>
                      <div className="text-sm text-gray-600 mb-1">{t('apps.outlineInteraction.sectionDescription')}</div>
                      <textarea
                        value={section.description || ''}
                        onChange={(e) => handleUpdateSection(index, 'description', e.target.value)}
                        placeholder={t('apps.outlineInteraction.descriptionPlaceholder')}
                        className="w-full min-h-[92px] p-3 border border-gray-300 rounded-md text-sm text-gray-900 resize-y focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>
            <div className="px-5 py-4 border-t border-gray-200 flex items-center justify-end gap-2">
              <button
                onClick={handleCloseEditModal}
                className="px-4 h-9 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50"
              >
                {t('apps.outlineInteraction.cancelEdit')}
              </button>
              <button
                onClick={handleSubmitOutlineEdit}
                className="px-4 h-9 bg-[#8B8CFF] text-white rounded-md hover:opacity-90"
              >
                {t('apps.outlineInteraction.saveOutline')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default OutlineInteractionMessage;
