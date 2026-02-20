import { useRef, useState } from 'react';
import { useUploads, useUploadFile, useDeleteUpload } from '../api/queries';
import type { Upload } from '../api/types';

interface FileUploadProps {
  templateId: string;
  onClose: () => void;
}

const ACCEPTED_TYPES = [
  'application/pdf',
  'text/plain',
  'text/markdown',
  'text/csv',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
];

const ACCEPTED_EXTENSIONS = '.pdf,.txt,.md,.csv,.docx';

export function FileUpload({ templateId, onClose }: FileUploadProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);

  const { data: uploads, isLoading } = useUploads(templateId);
  const uploadFile = useUploadFile(templateId);
  const deleteUpload = useDeleteUpload(templateId);

  const handleFileSelect = async (files: FileList | null) => {
    if (!files || files.length === 0) return;

    for (const file of Array.from(files)) {
      if (!ACCEPTED_TYPES.includes(file.type) && !file.name.match(/\.(pdf|txt|md|csv|docx)$/i)) {
        alert(`Unsupported file type: ${file.name}`);
        continue;
      }

      try {
        await uploadFile.mutateAsync(file);
      } catch (err) {
        console.error('Failed to upload:', err);
        alert(`Failed to upload ${file.name}`);
      }
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    handleFileSelect(e.dataTransfer.files);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = () => {
    setDragOver(false);
  };

  const handleDelete = async (uploadId: string) => {
    if (!confirm('Delete this file?')) return;
    try {
      await deleteUpload.mutateAsync(uploadId);
    } catch (err) {
      console.error('Failed to delete:', err);
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const getFileIcon = (contentType: string | null): string => {
    if (contentType?.includes('pdf')) return 'pdf';
    if (contentType?.includes('word')) return 'doc';
    if (contentType?.includes('csv')) return 'csv';
    return 'txt';
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-lg mx-4 max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-zinc-200 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-zinc-900">Uploaded Documents</h2>
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
          {/* Drop zone */}
          <div
            onClick={() => fileInputRef.current?.click()}
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors ${
              dragOver
                ? 'border-sky-500 bg-sky-50'
                : 'border-zinc-300 hover:border-zinc-400'
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept={ACCEPTED_EXTENSIONS}
              multiple
              onChange={(e) => handleFileSelect(e.target.files)}
              className="hidden"
            />
            <svg
              className={`w-10 h-10 mx-auto mb-3 ${dragOver ? 'text-sky-500' : 'text-zinc-400'}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
              />
            </svg>
            <p className="text-sm text-zinc-600">
              {uploadFile.isPending ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="animate-spin rounded-full h-4 w-4 border-b-2 border-sky-600"></span>
                  Uploading...
                </span>
              ) : (
                <>
                  <span className="text-sky-600 font-medium">Click to upload</span> or drag and drop
                </>
              )}
            </p>
            <p className="text-xs text-zinc-500 mt-1">
              PDF, TXT, MD, CSV, DOCX up to 10MB
            </p>
          </div>

          {/* File list */}
          <div className="mt-6">
            <h3 className="text-sm font-medium text-zinc-700 mb-3">
              Uploaded Files ({uploads?.length || 0})
            </h3>

            {isLoading ? (
              <div className="text-center py-4 text-zinc-500 text-sm">Loading...</div>
            ) : uploads && uploads.length > 0 ? (
              <div className="space-y-2">
                {uploads.map((upload) => (
                  <FileItem
                    key={upload.id}
                    upload={upload}
                    onDelete={() => handleDelete(upload.id)}
                    isDeleting={deleteUpload.isPending}
                    formatFileSize={formatFileSize}
                    getFileIcon={getFileIcon}
                  />
                ))}
              </div>
            ) : (
              <div className="text-center py-4 text-zinc-500 text-sm">
                No files uploaded yet. Upload documents to reference them in content generation.
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-zinc-200 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm bg-sky-600 text-white rounded-lg hover:bg-sky-700"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
}

interface FileItemProps {
  upload: Upload;
  onDelete: () => void;
  isDeleting: boolean;
  formatFileSize: (bytes: number) => string;
  getFileIcon: (contentType: string | null) => string;
}

function FileItem({ upload, onDelete, isDeleting, formatFileSize, getFileIcon }: FileItemProps) {
  const icon = getFileIcon(upload.content_type);

  return (
    <div className="flex items-center gap-3 p-3 bg-zinc-50 rounded-lg">
      {/* File icon */}
      <div className="w-10 h-10 flex items-center justify-center bg-white rounded border border-zinc-200">
        <span className="text-xs font-bold text-zinc-500 uppercase">{icon}</span>
      </div>

      {/* File info */}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-zinc-900 truncate">
          {upload.original_filename}
        </p>
        <div className="flex items-center gap-2 text-xs text-zinc-500">
          <span>{formatFileSize(upload.size_bytes)}</span>
          <span>•</span>
          <ExtractionStatus status={upload.extraction_status} />
        </div>
      </div>

      {/* Delete button */}
      <button
        onClick={onDelete}
        disabled={isDeleting}
        className="p-2 text-zinc-400 hover:text-red-600 disabled:opacity-50"
        title="Delete file"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
        </svg>
      </button>
    </div>
  );
}

function ExtractionStatus({ status }: { status: string }) {
  switch (status) {
    case 'completed':
      return (
        <span className="flex items-center gap-1 text-green-600">
          <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
          </svg>
          Text extracted
        </span>
      );
    case 'failed':
      return (
        <span className="flex items-center gap-1 text-amber-600">
          <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
          Extraction failed
        </span>
      );
    default:
      return (
        <span className="flex items-center gap-1 text-zinc-500">
          <span className="w-3 h-3 animate-spin rounded-full border-2 border-zinc-300 border-t-zinc-500"></span>
          Processing...
        </span>
      );
  }
}
