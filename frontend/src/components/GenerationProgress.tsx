import { useEffect } from 'react';
import { useGenerationStatus } from '../api/queries';
import { positionToLabel } from '../api/types';
import type { GenerationStatusType } from '../api/types';

interface GenerationProgressProps {
  templateId: string;
  jobId: string;
  onClose: () => void;
  onComplete: () => void;
}

export function GenerationProgress({ templateId, jobId, onClose, onComplete }: GenerationProgressProps) {
  const { data: status } = useGenerationStatus(templateId, jobId);

  useEffect(() => {
    if (status?.status !== 'completed') return;
    const timer = window.setTimeout(() => {
      onComplete();
    }, 1500);
    return () => window.clearTimeout(timer);
  }, [status?.status, onComplete]);

  if (!status) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md mx-4">
          <div className="flex items-center justify-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-sky-600"></div>
            <span className="ml-3 text-zinc-600">Starting generation...</span>
          </div>
        </div>
      </div>
    );
  }

  const progress = status.total_subsections > 0
    ? Math.round((status.current_index / status.total_subsections) * 100)
    : 0;

  const isComplete = status.status === 'completed';
  const isFailed = status.status === 'failed';
  const isRunning = status.status === 'in_progress' || status.status === 'pending';

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-lg mx-4">
        {/* Header */}
        <div className="px-6 py-4 border-b border-zinc-200 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-zinc-900">
            {isComplete ? 'Generation Complete' : isFailed ? 'Generation Failed' : 'Generating Content...'}
          </h2>
          {!isRunning && (
            <button
              onClick={onClose}
              className="text-zinc-400 hover:text-zinc-600"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>

        {/* Content */}
        <div className="p-6">
          {/* Overall progress */}
          <div className="mb-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-zinc-600">
                {isComplete ? 'All content generated' :
                 isFailed ? 'Generation encountered errors' :
                 `Processing ${status.current_index + 1} of ${status.total_subsections}`}
              </span>
              <span className="text-sm font-medium text-zinc-900">{progress}%</span>
            </div>
            <div className="w-full bg-zinc-200 rounded-full h-2">
              <div
                className={`h-2 rounded-full transition-all duration-300 ${
                  isComplete ? 'bg-green-500' :
                  isFailed ? 'bg-red-500' :
                  'bg-sky-600'
                }`}
                style={{ width: `${isComplete ? 100 : progress}%` }}
              />
            </div>
          </div>

          {/* Error message */}
          {status.error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-700">{status.error}</p>
            </div>
          )}

          {/* Subsection list */}
          <div className="max-h-64 overflow-y-auto space-y-2">
            {status.subsections.map((sub, index) => (
              <div
                key={sub.subsection_id}
                className={`flex items-center gap-3 p-2 rounded ${
                  index === status.current_index && isRunning ? 'bg-sky-50' : ''
                }`}
              >
                <StatusIcon status={sub.status} />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-zinc-900 truncate">
                    {sub.section_title}
                  </p>
                  <p className="text-xs text-zinc-500">
                    Subsection {positionToLabel(sub.position)}{sub.title ? `: ${sub.title}` : ''}
                  </p>
                </div>
                {sub.error && (
                  <span className="text-xs text-red-600" title={sub.error}>
                    Error
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Footer */}
        {!isRunning && (
          <div className="px-6 py-4 border-t border-zinc-200 flex justify-end">
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm bg-sky-600 text-white rounded-lg hover:bg-sky-700"
            >
              {isComplete ? 'Done' : 'Close'}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

function StatusIcon({ status }: { status: GenerationStatusType }) {
  switch (status) {
    case 'completed':
      return (
        <div className="w-5 h-5 rounded-full bg-green-100 flex items-center justify-center">
          <svg className="w-3 h-3 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
          </svg>
        </div>
      );
    case 'in_progress':
      return (
        <div className="w-5 h-5">
          <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-sky-600"></div>
        </div>
      );
    case 'failed':
      return (
        <div className="w-5 h-5 rounded-full bg-red-100 flex items-center justify-center">
          <svg className="w-3 h-3 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </div>
      );
    case 'pending':
    default:
      return (
        <div className="w-5 h-5 rounded-full bg-zinc-100 flex items-center justify-center">
          <div className="w-2 h-2 rounded-full bg-zinc-400"></div>
        </div>
      );
  }
}
