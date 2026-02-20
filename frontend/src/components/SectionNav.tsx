import { useState } from 'react';
import { DragDropContext, Droppable, Draggable } from '@hello-pangea/dnd';
import type { DropResult } from '@hello-pangea/dnd';
import { useSections, useCreateSection, useUpdateSection, useDeleteSection, useUploads } from '../api/queries';
import { useWorkspaceStore } from '../store/workspace';
import type { Section } from '../api/types';

interface SectionNavProps {
  templateId: string;
  onOpenDocuments: () => void;
}

export function SectionNav({ templateId, onOpenDocuments }: SectionNavProps) {
  const [isAdding, setIsAdding] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState('');

  const { data: sections, isLoading } = useSections(templateId);
  const { data: uploads, isLoading: isUploadsLoading } = useUploads(templateId);
  const createSection = useCreateSection();
  const updateSection = useUpdateSection();
  const deleteSection = useDeleteSection();
  const { selectedSectionId, setSelectedSection } = useWorkspaceStore();

  // Sort sections by position
  const sortedSections = sections?.slice().sort((a, b) => a.position - b.position);
  const sortedUploads = uploads?.slice().sort((a, b) => (b.created_at || '').localeCompare(a.created_at || ''));

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
      <div className="w-64 rounded-xl border border-zinc-200 bg-gradient-to-b from-white to-zinc-50 shadow-sm p-4">
        <div className="text-zinc-500 text-sm">Loading sections...</div>
      </div>
    );
  }

  return (
    <div className="w-64 rounded-xl border border-zinc-200 bg-gradient-to-b from-white to-zinc-50 shadow-sm flex flex-col overflow-hidden">
      <div className="p-4 border-b border-zinc-300/80 bg-slate-100/95">
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
        <form onSubmit={handleCreate} className="p-3 border-b border-zinc-300/80 bg-slate-50/90">
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
              className="flex-1 overflow-y-auto bg-zinc-50/45"
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
                              className={`group mx-2 my-1 px-3 py-2.5 rounded-lg border cursor-pointer transition-all ${
                                snapshot.isDragging
                                  ? 'bg-sky-100 border-sky-300 shadow-md'
                                  : selectedSectionId === section.id
                                  ? 'bg-sky-50 border-sky-300 shadow-sm'
                                  : 'bg-white/70 border-zinc-200/70 hover:bg-white hover:border-zinc-300'
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

      <div className="border-t border-zinc-200/90 p-3 bg-white/80">
        <button
          onClick={onOpenDocuments}
          className="w-full px-3 py-2 text-sm border border-zinc-300 text-zinc-700 rounded-lg bg-white hover:bg-zinc-50 transition-colors flex items-center justify-between shadow-sm"
          title="Open documents manager"
        >
          <span className="flex items-center gap-2">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
            Documents
          </span>
          <span className="text-xs bg-zinc-200 text-zinc-700 px-2 py-0.5 rounded-full">
            {uploads?.length || 0}
          </span>
        </button>

        <div className="mt-3">
          <p className="text-xs font-medium text-zinc-500 uppercase tracking-wide">Uploaded files</p>

          {isUploadsLoading ? (
            <div className="mt-2 text-xs text-zinc-500">Loading documents...</div>
          ) : sortedUploads && sortedUploads.length > 0 ? (
            <ul className="mt-2 space-y-1 max-h-36 overflow-y-auto pr-1">
              {sortedUploads.map((upload) => (
                <li key={upload.id}>
                  <button
                    onClick={onOpenDocuments}
                    className="w-full px-2 py-1.5 rounded border border-transparent text-left hover:bg-zinc-100 hover:border-zinc-200 transition-colors"
                    title="Open documents manager"
                  >
                    <div className="text-xs text-zinc-700 truncate">{upload.original_filename}</div>
                    <div className="text-[11px] text-zinc-500">
                      {upload.extraction_status === 'completed'
                        ? 'Ready'
                        : upload.extraction_status === 'failed'
                        ? 'Extraction failed'
                        : 'Processing'}
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <div className="mt-2 text-xs text-zinc-500">
              No documents uploaded yet.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
