import { useState } from 'react';
import { DragDropContext, Droppable, Draggable } from '@hello-pangea/dnd';
import type { DropResult } from '@hello-pangea/dnd';
import { useSections, useCreateSection, useUpdateSection, useDeleteSection } from '../api/queries';
import { useWorkspaceStore } from '../store/workspace';
import type { Section } from '../api/types';

interface SectionNavProps {
  templateId: string;
}

export function SectionNav({ templateId }: SectionNavProps) {
  const [isAdding, setIsAdding] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState('');

  const { data: sections, isLoading } = useSections(templateId);
  const createSection = useCreateSection();
  const updateSection = useUpdateSection();
  const deleteSection = useDeleteSection();
  const { selectedSectionId, setSelectedSection } = useWorkspaceStore();

  // Sort sections by position
  const sortedSections = sections?.slice().sort((a, b) => a.position - b.position);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      const section = await createSection.mutateAsync({
        templateId,
        title: newTitle.trim() || undefined,
      });
      setNewTitle('');
      setIsAdding(false);
      setSelectedSection(section.id);
    } catch (err) {
      console.error('Failed to create section:', err);
    }
  };

  const handleStartEdit = (section: Section, e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingId(section.id);
    setEditTitle(section.title || '');
  };

  const handleSaveEdit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingId) return;

    try {
      await updateSection.mutateAsync({
        id: editingId,
        templateId,
        title: editTitle.trim() || undefined,
      });
      setEditingId(null);
      setEditTitle('');
    } catch (err) {
      console.error('Failed to update section:', err);
    }
  };

  const handleCancelEdit = () => {
    setEditingId(null);
    setEditTitle('');
  };

  const handleDelete = async (sectionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!window.confirm('Delete this section and all its content?')) return;

    try {
      await deleteSection.mutateAsync({ id: sectionId, templateId });
      if (selectedSectionId === sectionId) {
        setSelectedSection(null);
      }
    } catch (err) {
      console.error('Failed to delete section:', err);
    }
  };

  const handleDragEnd = async (result: DropResult) => {
    if (!result.destination || !sortedSections) return;

    const sourceIndex = result.source.index;
    const destIndex = result.destination.index;

    if (sourceIndex === destIndex) return;

    const movedSection = sortedSections[sourceIndex];
    const newPosition = destIndex + 1; // positions are 1-indexed

    try {
      await updateSection.mutateAsync({
        id: movedSection.id,
        templateId,
        position: newPosition,
      });
    } catch (err) {
      console.error('Failed to reorder section:', err);
    }
  };

  if (isLoading) {
    return (
      <div className="w-64 border-r border-zinc-200 bg-white p-4">
        <div className="text-zinc-500 text-sm">Loading sections...</div>
      </div>
    );
  }

  return (
    <div className="w-64 border-r border-zinc-200 bg-white flex flex-col">
      <div className="p-4 border-b border-zinc-200">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold text-zinc-900">Sections</h2>
          <button
            onClick={() => setIsAdding(true)}
            className="p-1 text-sky-600 hover:text-sky-700"
            title="Add section"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
          </button>
        </div>
      </div>

      {isAdding && (
        <form onSubmit={handleCreate} className="p-3 border-b border-zinc-200">
          <input
            type="text"
            value={newTitle}
            onChange={(e) => setNewTitle(e.target.value)}
            placeholder="Section title (optional)"
            className="w-full px-2 py-1.5 text-sm border border-zinc-300 rounded focus:outline-none focus:ring-1 focus:ring-sky-500 mb-3"
            autoFocus
          />
          <div className="flex gap-2">
            <button
              type="submit"
              disabled={createSection.isPending}
              className="flex-1 px-2 py-1.5 text-xs bg-sky-600 text-white rounded hover:bg-sky-700 disabled:opacity-50"
            >
              {createSection.isPending ? 'Adding...' : 'Add Section'}
            </button>
            <button
              type="button"
              onClick={() => {
                setIsAdding(false);
                setNewTitle('');
              }}
              className="px-3 py-1.5 text-xs text-zinc-600 hover:text-zinc-800 border border-zinc-300 rounded"
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      <DragDropContext onDragEnd={handleDragEnd}>
        <Droppable droppableId="sections">
          {(provided) => (
            <div
              ref={provided.innerRef}
              {...provided.droppableProps}
              className="flex-1 overflow-y-auto"
            >
              {sortedSections && sortedSections.length === 0 ? (
                <div className="p-4 text-sm text-zinc-500 text-center">
                  No sections yet
                </div>
              ) : (
                <ul className="py-2">
                  {sortedSections?.map((section, index) => (
                    <Draggable key={section.id} draggableId={section.id} index={index}>
                      {(provided, snapshot) => (
                        <li
                          ref={provided.innerRef}
                          {...provided.draggableProps}
                        >
                          {editingId === section.id ? (
                            <form onSubmit={handleSaveEdit} className="px-3 py-2">
                              <input
                                type="text"
                                value={editTitle}
                                onChange={(e) => setEditTitle(e.target.value)}
                                placeholder="Section title"
                                className="w-full px-2 py-1 text-sm border border-zinc-300 rounded focus:outline-none focus:ring-1 focus:ring-sky-500"
                                autoFocus
                                onBlur={handleCancelEdit}
                                onKeyDown={(e) => {
                                  if (e.key === 'Escape') handleCancelEdit();
                                }}
                              />
                            </form>
                          ) : (
                            <div
                              onClick={() => setSelectedSection(section.id)}
                              className={`group px-3 py-2.5 cursor-pointer transition-colors ${
                                snapshot.isDragging
                                  ? 'bg-sky-100 shadow-lg rounded'
                                  : selectedSectionId === section.id
                                  ? 'bg-sky-50 border-r-2 border-sky-600'
                                  : 'hover:bg-zinc-50'
                              }`}
                            >
                              <div className="flex items-center gap-2">
                                {/* Drag handle */}
                                <div
                                  {...provided.dragHandleProps}
                                  className="text-zinc-400 hover:text-zinc-600 cursor-grab active:cursor-grabbing"
                                  title="Drag to reorder"
                                >
                                  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                                    <path d="M7 2a2 2 0 1 0 .001 4.001A2 2 0 0 0 7 2zm0 6a2 2 0 1 0 .001 4.001A2 2 0 0 0 7 8zm0 6a2 2 0 1 0 .001 4.001A2 2 0 0 0 7 14zm6-8a2 2 0 1 0-.001-4.001A2 2 0 0 0 13 6zm0 2a2 2 0 1 0 .001 4.001A2 2 0 0 0 13 8zm0 6a2 2 0 1 0 .001 4.001A2 2 0 0 0 13 14z" />
                                  </svg>
                                </div>

                                {/* Section info */}
                                <div className="flex-1 min-w-0">
                                  <div className={`text-sm font-medium truncate ${
                                    selectedSectionId === section.id ? 'text-sky-700' : 'text-zinc-700'
                                  }`}>
                                    <span className="text-zinc-400 mr-1">{section.position}.</span>
                                    {section.title || 'Untitled Section'}
                                  </div>
                                  <div className="text-xs text-zinc-400">
                                    {section.subsections.length} subsection{section.subsections.length !== 1 ? 's' : ''}
                                  </div>
                                </div>

                                {/* Actions */}
                                <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                  <button
                                    onClick={(e) => handleStartEdit(section, e)}
                                    className="p-1 text-zinc-400 hover:text-sky-600"
                                    title="Edit title"
                                  >
                                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                                    </svg>
                                  </button>
                                  <button
                                    onClick={(e) => handleDelete(section.id, e)}
                                    className="p-1 text-zinc-400 hover:text-red-600"
                                    title="Delete section"
                                  >
                                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                    </svg>
                                  </button>
                                </div>
                              </div>
                            </div>
                          )}
                        </li>
                      )}
                    </Draggable>
                  ))}
                  {provided.placeholder}
                </ul>
              )}
            </div>
          )}
        </Droppable>
      </DragDropContext>
    </div>
  );
}
