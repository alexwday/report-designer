import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTemplates, useCreateTemplate, useDeleteTemplate } from '../api/queries';

export function TemplateListPage() {
  const navigate = useNavigate();
  const [newTemplateName, setNewTemplateName] = useState('');
  const [isCreating, setIsCreating] = useState(false);

  const { data: templates, isLoading, error } = useTemplates();
  const createTemplate = useCreateTemplate();
  const deleteTemplate = useDeleteTemplate();

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTemplateName.trim()) return;
    try {
      const template = await createTemplate.mutateAsync({ name: newTemplateName.trim() });
      setNewTemplateName('');
      setIsCreating(false);
      navigate(`/templates/${template.id}`);
    } catch (err) {
      console.error('Failed to create template:', err);
    }
  };

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm('Delete this template?')) return;
    try {
      await deleteTemplate.mutateAsync(id);
    } catch (err) {
      console.error('Failed to delete template:', err);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#fafafa] flex items-center justify-center">
        <div className="flex items-center gap-3 text-zinc-400">
          <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          <span className="text-sm tracking-wide">Loading&hellip;</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-[#fafafa] flex items-center justify-center">
        <div className="text-center">
          <div className="w-10 h-10 rounded-full bg-red-50 border border-red-200 flex items-center justify-center mx-auto mb-3">
            <svg className="w-4 h-4 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 9v2m0 4h.01" />
            </svg>
          </div>
          <p className="text-zinc-800 text-sm font-medium">Unable to load templates</p>
          <p className="text-xs text-zinc-400 mt-1">Check that the backend server is running.</p>
        </div>
      </div>
    );
  }

  const templateCount = templates?.length ?? 0;

  return (
    <div className="min-h-screen ambient-bg dot-grid">
      <div className="relative z-10">
        {/* ── Hero ── */}
        <div className="max-w-5xl mx-auto px-6 pt-16 pb-16">
          <div className="opacity-0 animate-fade-up">
            <h1 className="text-[clamp(2.5rem,5vw,3.5rem)] font-semibold leading-[1.08] tracking-tight text-zinc-900">
              Design, generate,<br />
              <span className="hero-gradient-text animate-shimmer">and ship reports.</span>
            </h1>

            <p className="mt-6 text-[15px] text-zinc-400 max-w-lg leading-relaxed font-light">
              Build structured templates, connect MCP data sources, and let AI generate publication-ready financial documents in seconds.
            </p>
          </div>

          {/* Feature chips */}
          <div className="flex flex-wrap items-center gap-2 mt-10 opacity-0 animate-fade-up stagger-2">
            {[
              { label: 'AI Generation', color: 'sky' },
              { label: 'PDF Export', color: 'rose' },
              { label: 'PowerPoint', color: 'amber' },
              { label: 'MCP Sources', color: 'emerald' },
            ].map((f) => (
              <span
                key={f.label}
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[11px] font-medium tracking-wide border bg-white
                  ${f.color === 'sky' ? 'text-sky-600 border-sky-200' : ''}
                  ${f.color === 'rose' ? 'text-rose-600 border-rose-200' : ''}
                  ${f.color === 'amber' ? 'text-amber-600 border-amber-200' : ''}
                  ${f.color === 'emerald' ? 'text-emerald-600 border-emerald-200' : ''}
                `}
              >
                <div className={`w-1 h-1 rounded-full
                  ${f.color === 'sky' ? 'bg-sky-500' : ''}
                  ${f.color === 'rose' ? 'bg-rose-500' : ''}
                  ${f.color === 'amber' ? 'bg-amber-500' : ''}
                  ${f.color === 'emerald' ? 'bg-emerald-500' : ''}
                `} />
                {f.label}
              </span>
            ))}
          </div>
        </div>

        {/* ── Shimmer divider ── */}
        <div className="max-w-5xl mx-auto px-6">
          <div className="shimmer-line" />
        </div>

        {/* ── Templates ── */}
        <div className="max-w-5xl mx-auto px-6 pt-10 pb-24">
          <div className="opacity-0 animate-fade-up stagger-3">
            {/* Section header */}
            <div className="flex items-end justify-between mb-5">
              <div>
                <h2 className="text-lg font-semibold text-zinc-800 tracking-tight">Templates</h2>
                <p className="text-[13px] text-zinc-400 mt-0.5">
                  {templateCount === 0
                    ? 'Create a template to begin.'
                    : `${templateCount} template${templateCount !== 1 ? 's' : ''} \u2014 select one to open the editor.`}
                </p>
              </div>
              <button
                onClick={() => setIsCreating(true)}
                className="px-4 py-2 bg-zinc-900 text-white text-[13px] font-medium rounded-lg hover:bg-zinc-800 active:bg-zinc-950 transition-colors flex items-center gap-2 shadow-sm"
              >
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 4v16m8-8H4" />
                </svg>
                New Template
              </button>
            </div>

            {/* Create form */}
            {isCreating && (
              <div className="mb-5 p-5 glass rounded-xl">
                <form onSubmit={handleCreate}>
                  <label className="block text-[11px] font-medium text-zinc-400 tracking-[0.1em] uppercase mb-2">Template name</label>
                  <div className="flex gap-3">
                    <input
                      type="text"
                      value={newTemplateName}
                      onChange={(e) => setNewTemplateName(e.target.value)}
                      placeholder="e.g. Q4 2025 Annual Report"
                      className="flex-1 px-3.5 py-2.5 bg-white border border-zinc-200 rounded-lg text-sm text-zinc-800 focus:outline-none focus:ring-2 focus:ring-sky-500/20 focus:border-sky-400 placeholder:text-zinc-300"
                      autoFocus
                    />
                    <button
                      type="submit"
                      disabled={createTemplate.isPending}
                      className="px-5 py-2.5 bg-zinc-900 text-white text-sm font-medium rounded-lg hover:bg-zinc-800 disabled:opacity-50 transition-colors"
                    >
                      {createTemplate.isPending ? 'Creating\u2026' : 'Create'}
                    </button>
                    <button
                      type="button"
                      onClick={() => { setIsCreating(false); setNewTemplateName(''); }}
                      className="px-4 py-2.5 text-sm text-zinc-400 hover:text-zinc-600 transition-colors"
                    >
                      Cancel
                    </button>
                  </div>
                </form>
              </div>
            )}

            {/* Template list or empty state */}
            {templateCount === 0 ? (
              <div className="glass rounded-xl px-8 py-24 text-center">
                <div className="w-14 h-14 rounded-xl bg-zinc-100 border border-zinc-200 flex items-center justify-center mx-auto mb-5">
                  <svg className="w-6 h-6 text-zinc-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                  </svg>
                </div>
                <h3 className="text-base font-medium text-zinc-700">No templates yet</h3>
                <p className="mt-2 text-[13px] text-zinc-400 max-w-sm mx-auto leading-relaxed">
                  Templates define the structure of your reports&mdash;sections, subsections, and the data sources that generate content.
                </p>
                <button
                  onClick={() => setIsCreating(true)}
                  className="mt-8 px-5 py-2.5 bg-zinc-900 text-white text-[13px] font-medium rounded-lg hover:bg-zinc-800 transition-colors inline-flex items-center gap-2 shadow-sm"
                >
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 4v16m8-8H4" />
                  </svg>
                  Create Template
                </button>
              </div>
            ) : (
              <div className="glass rounded-xl overflow-hidden">
                <div className="divide-y divide-zinc-100">
                  {templates?.map((template, index) => (
                    <div
                      key={template.id}
                      onClick={() => navigate(`/templates/${template.id}`)}
                      className={`flex items-center px-5 py-4 glow-hover cursor-pointer group opacity-0 animate-fade-up stagger-${Math.min(index + 4, 8)}`}
                    >
                      {/* Format icon */}
                      <div className={`w-9 h-9 rounded-lg flex items-center justify-center mr-4 flex-shrink-0 border ${
                        template.output_format === 'ppt'
                          ? 'bg-amber-50 border-amber-200 text-amber-500'
                          : 'bg-rose-50 border-rose-200 text-rose-500'
                      }`}>
                        {template.output_format === 'ppt' ? (
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3.75 3v11.25A2.25 2.25 0 006 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0118 16.5h-2.25m-7.5 0h7.5m-7.5 0l-1 3m8.5-3l1 3m0 0l.5 1.5m-.5-1.5h-9.5m0 0l-.5 1.5" />
                          </svg>
                        ) : (
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                          </svg>
                        )}
                      </div>

                      {/* Info */}
                      <div className="flex-1 min-w-0">
                        <h3 className="text-[13px] font-medium text-zinc-800 group-hover:text-zinc-950 transition-colors truncate">
                          {template.name}
                        </h3>
                        <div className="flex items-center gap-2.5 mt-1">
                          <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold tracking-wider uppercase border ${
                            template.output_format === 'ppt'
                              ? 'text-amber-600 bg-amber-50 border-amber-200'
                              : 'text-rose-600 bg-rose-50 border-rose-200'
                          }`}>
                            {template.output_format?.toUpperCase()}
                          </span>
                          <span className="text-[11px] text-zinc-400">
                            {template.updated_at ? new Date(template.updated_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : 'N/A'}
                          </span>
                        </div>
                      </div>

                      {/* Actions */}
                      <div className="flex items-center gap-2 ml-4">
                        <span className="text-[11px] text-sky-500 opacity-0 group-hover:opacity-100 transition-opacity font-medium tracking-wide">
                          Open
                        </span>
                        <svg className="w-3.5 h-3.5 text-zinc-300 group-hover:text-sky-500 group-hover:translate-x-0.5 transition-all" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.25 4.5l7.5 7.5-7.5 7.5" />
                        </svg>
                        <button
                          onClick={(e) => handleDelete(template.id, e)}
                          className="p-1.5 text-zinc-300 hover:text-red-500 transition-colors rounded-lg hover:bg-red-50 opacity-0 group-hover:opacity-100 ml-1"
                          title="Delete template"
                        >
                          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
