import type { PreviewSubsection } from '../api/types';
import { positionToLabel } from '../api/types';
import { Markdown } from './Markdown';
import { ChartRenderer } from './ChartRenderer';

interface SubsectionTileProps {
  subsection: PreviewSubsection;
  isSelected: boolean;
  isGenerating: boolean;
  onClick: () => void;
  onTitleChange?: (title: string) => void;
  onDelete?: () => void;
}

export function SubsectionTile({
  subsection,
  isSelected,
  isGenerating,
  onClick,
  onTitleChange,
  onDelete,
}: SubsectionTileProps) {
  const hasContent = subsection.content && subsection.content.trim().length > 0;
  const label = positionToLabel(subsection.position);
  const configuredInputCount = subsection.data_source_config?.inputs?.length || 0;
  const firstSourceId = configuredInputCount > 0
    ? subsection.data_source_config?.inputs?.[0]?.source_id
    : null;

  return (
    <div
      onClick={onClick}
      className={`rounded-lg border-2 transition-all duration-200 cursor-pointer relative ${
        isSelected
          ? 'border-sky-500 ring-2 ring-sky-200 bg-white shadow-md'
          : 'border-zinc-200 bg-zinc-50 hover:border-zinc-300 hover:bg-white hover:shadow-sm'
      }`}
    >
      {/* Tile header */}
      <div className={`px-4 py-3 border-b flex items-center justify-between ${
        isSelected ? 'border-sky-200 bg-sky-50' : 'border-zinc-200 bg-zinc-100'
      }`}>
        <div className="flex items-center gap-3">
          {/* Label badge */}
          <span className={`inline-flex items-center justify-center w-7 h-7 rounded-md text-sm font-bold ${
            isSelected ? 'bg-sky-600 text-white' : 'bg-zinc-300 text-zinc-700'
          }`}>
            {label}
          </span>

          {/* Title */}
          {onTitleChange ? (
            <input
              type="text"
              value={subsection.title || ''}
              onChange={(e) => {
                e.stopPropagation();
                onTitleChange(e.target.value);
              }}
              onClick={(e) => e.stopPropagation()}
              placeholder="Optional title..."
              className={`text-sm font-medium bg-transparent border-none focus:outline-none focus:ring-0 px-0 ${
                isSelected ? 'text-sky-700 placeholder-sky-300' : 'text-zinc-700 placeholder-zinc-400'
              }`}
            />
          ) : (
            <span className={`text-sm font-medium ${
              isSelected ? 'text-sky-700' : 'text-zinc-700'
            }`}>
              {subsection.title || 'Untitled'}
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          {/* Status indicators */}
          {subsection.has_instructions && (
            <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded" title="Has instructions">
              Instructions
            </span>
          )}
          {subsection.has_notes && (
            <span className="text-xs bg-purple-100 text-purple-700 px-2 py-0.5 rounded" title="Has notes">
              Notes
            </span>
          )}
          {subsection.data_source_config && (
            <span className="text-xs bg-orange-100 text-orange-700 px-2 py-0.5 rounded" title="Data source configured">
              {configuredInputCount > 1
                ? `${configuredInputCount} inputs`
                : (firstSourceId || 'configured')}
            </span>
          )}

          {/* Delete button */}
          {onDelete && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onDelete();
              }}
              className="p-1 text-zinc-400 hover:text-red-600 transition-colors"
              title="Delete subsection"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          )}
        </div>
      </div>

      {/* Tile content */}
      <div className="p-4 min-h-[120px] max-h-[400px] overflow-y-auto">
        {hasContent ? (
          subsection.content_type === 'markdown' || !subsection.content_type ? (
            <Markdown content={subsection.content!} className="prose prose-sm max-w-none text-zinc-700" />
          ) : subsection.content_type === 'json' ? (
            <ChartRenderer content={subsection.content!} />
          ) : (
            <pre className="text-sm overflow-auto whitespace-pre-wrap bg-zinc-100 p-3 rounded text-zinc-700">
              {subsection.content}
            </pre>
          )
        ) : (
          <div className="flex items-center justify-center h-full min-h-[80px] text-zinc-400 text-sm italic border border-dashed border-zinc-300 rounded bg-zinc-50">
            Click to add content
          </div>
        )}
      </div>

      {/* Loading overlay */}
      {isGenerating && (
        <div className="absolute inset-0 bg-white/80 flex items-center justify-center rounded-lg">
          <div className="flex flex-col items-center gap-2">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-sky-600" />
            <span className="text-sm text-zinc-600">Generating...</span>
          </div>
        </div>
      )}
    </div>
  );
}
