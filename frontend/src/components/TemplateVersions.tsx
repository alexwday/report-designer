import { useState } from 'react';
import {
  useTemplateVersions,
  useCreateTemplateVersion,
  useRestoreTemplateVersion,
} from '../api/queries';
import type { TemplateVersionSummary } from '../api/types';

interface TemplateVersionsProps {
  templateId: string;
  onClose: () => void;
}

export function TemplateVersions({ templateId, onClose }: TemplateVersionsProps) {
  const [newVersionName, setNewVersionName] = useState('');
  const [isCreating, setIsCreating] = useState(false);

  const { data: versions, isLoading } = useTemplateVersions(templateId);
  const createVersion = useCreateTemplateVersion(templateId);
  const restoreVersion = useRestoreTemplateVersion(templateId);

  const handleCreateVersion = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newVersionName.trim()) return;

    try {
      await createVersion.mutateAsync({ name: newVersionName.trim() });
      setNewVersionName('');
      setIsCreating(false);
    } catch (err) {
      console.error('Failed to create version:', err);
      alert('Failed to create version. Please try again.');
    }
  };

  const handleRestore = async (version: TemplateVersionSummary) => {
    if (!confirm(`Restore to "${version.name}"? This will create a backup of your current state first.`)) {
      return;
    }

    try {
      await restoreVersion.mutateAsync(version.id);
      onClose();
    } catch (err) {
      console.error('Failed to restore version:', err);
      alert('Failed to restore version. Please try again.');
    }
  };

  const formatDate = (dateStr: string | null): string => {
    if (!dateStr) return 'Unknown';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-lg mx-4 max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-zinc-200 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-zinc-900">Version History</h2>
          <button
            onClick={onClose}
            className="text-zinc-400 hover:text-zinc-600"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {/* Create new version */}
          {isCreating ? (
            <form onSubmit={handleCreateVersion} className="mb-6 p-4 bg-zinc-50 rounded-lg">
              <label className="block text-sm font-medium text-zinc-700 mb-2">
                Version Name
              </label>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={newVersionName}
                  onChange={(e) => setNewVersionName(e.target.value)}
                  placeholder="e.g., Before Q4 updates"
                  className="flex-1 px-3 py-2 border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 text-sm"
                  autoFocus
                />
                <button
                  type="submit"
                  disabled={createVersion.isPending || !newVersionName.trim()}
                  className="px-4 py-2 text-sm bg-sky-600 text-white rounded-lg hover:bg-sky-700 disabled:opacity-50"
                >
                  {createVersion.isPending ? 'Saving...' : 'Save'}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setIsCreating(false);
                    setNewVersionName('');
                  }}
                  className="px-4 py-2 text-sm text-zinc-600 hover:text-zinc-800"
                >
                  Cancel
                </button>
              </div>
            </form>
          ) : (
            <button
              onClick={() => setIsCreating(true)}
              className="w-full mb-6 px-4 py-3 border-2 border-dashed border-zinc-300 rounded-lg text-zinc-600 hover:border-sky-500 hover:text-sky-600 transition-colors flex items-center justify-center gap-2"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              Save Current Version
            </button>
          )}

          {/* Version list */}
          {isLoading ? (
            <div className="text-center py-8 text-zinc-500">Loading versions...</div>
          ) : versions && versions.length > 0 ? (
            <div className="space-y-3">
              {versions.map((version) => (
                <VersionItem
                  key={version.id}
                  version={version}
                  onRestore={() => handleRestore(version)}
                  isRestoring={restoreVersion.isPending}
                  formatDate={formatDate}
                />
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-zinc-500">
              <svg className="w-12 h-12 mx-auto text-zinc-300 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <p>No versions saved yet.</p>
              <p className="text-sm mt-1">Save a version to create a restore point.</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-zinc-200 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-zinc-700 hover:text-zinc-900"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

interface VersionItemProps {
  version: TemplateVersionSummary;
  onRestore: () => void;
  isRestoring: boolean;
  formatDate: (dateStr: string | null) => string;
}

function VersionItem({ version, onRestore, isRestoring, formatDate }: VersionItemProps) {
  return (
    <div className="flex items-center gap-3 p-4 bg-zinc-50 rounded-lg hover:bg-zinc-100 transition-colors">
      {/* Version icon */}
      <div className="w-10 h-10 flex items-center justify-center bg-white rounded-full border border-zinc-200">
        <span className="text-sm font-bold text-zinc-500">v{version.version_number}</span>
      </div>

      {/* Version info */}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-zinc-900 truncate">
          {version.name}
        </p>
        <p className="text-xs text-zinc-500">
          {formatDate(version.created_at)}
          {version.created_by && ` by ${version.created_by}`}
        </p>
      </div>

      {/* Restore button */}
      <button
        onClick={onRestore}
        disabled={isRestoring}
        className="px-3 py-1.5 text-xs font-medium text-sky-600 hover:text-sky-700 hover:bg-sky-50 rounded disabled:opacity-50 transition-colors"
        title="Restore this version"
      >
        {isRestoring ? 'Restoring...' : 'Restore'}
      </button>
    </div>
  );
}
