import { usePreview } from '../api/queries';
import { positionToLabel } from '../api/types';
import type { FormattingProfile, PreviewSection, PreviewSubsection } from '../api/types';
import { Markdown } from './Markdown';
import { ChartRenderer } from './ChartRenderer';
import type { CSSProperties } from 'react';

interface ReportPreviewProps {
  templateId: string;
}

function applyTitleCaseMode(value: string, mode: string | undefined): string {
  const normalized = value.trim();
  if (!normalized) return normalized;
  if (mode === 'upper') return normalized.toUpperCase();
  if (mode === 'sentence') return normalized.charAt(0).toUpperCase() + normalized.slice(1);
  if (mode === 'title') {
    return normalized
      .split(/\s+/)
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
      .join(' ');
  }
  return normalized;
}

function buildThemeStyles(profile: FormattingProfile | null | undefined): {
  containerStyle: CSSProperties;
  sectionTitleStyle: CSSProperties;
  subsectionTitleStyle: CSSProperties;
  accentColor: string;
  sectionTitleCase: string | undefined;
  subsectionTitleCase: string | undefined;
} {
  const accentColor = profile?.accent_color || '#0284c7';
  return {
    containerStyle: {
      fontFamily: profile?.font_family || undefined,
      color: profile?.body_color || undefined,
      lineHeight: profile?.line_height || undefined,
      fontSize: profile?.body_font_size_pt ? `${profile.body_font_size_pt}pt` : undefined,
    },
    sectionTitleStyle: {
      color: profile?.heading_color || undefined,
      borderBottomColor: accentColor,
      fontSize: profile?.title_font_size_pt ? `${profile.title_font_size_pt}pt` : undefined,
    },
    subsectionTitleStyle: {
      color: profile?.accent_color || undefined,
      fontSize: profile?.subsection_title_font_size_pt ? `${profile.subsection_title_font_size_pt}pt` : undefined,
    },
    accentColor,
    sectionTitleCase: profile?.section_title_case,
    subsectionTitleCase: profile?.subsection_title_case,
  };
}

export function ReportPreview({ templateId }: ReportPreviewProps) {
  const { data: preview, isLoading, error } = usePreview(templateId);

  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center bg-zinc-100">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-sky-600 mx-auto mb-4"></div>
          <p className="text-zinc-500">Loading preview...</p>
        </div>
      </div>
    );
  }

  if (error || !preview) {
    return (
      <div className="flex-1 flex items-center justify-center bg-zinc-100">
        <div className="text-center text-red-500">
          <p>Failed to load preview</p>
          <p className="text-sm text-zinc-500 mt-2">
            {error instanceof Error ? error.message : 'Unknown error'}
          </p>
        </div>
      </div>
    );
  }

  const { template, sections } = preview;
  const isLandscape = template.orientation === 'landscape';
  const themeStyles = buildThemeStyles(template.formatting_profile);

  return (
    <div className="flex-1 bg-zinc-200 overflow-auto p-6">
      <div className="max-w-4xl mx-auto space-y-8" style={themeStyles.containerStyle}>
        {/* Report header */}
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-zinc-900">{template.name}</h1>
          {template.description && (
            <p className="text-zinc-600 mt-2">{template.description}</p>
          )}
          <div className="flex items-center justify-center gap-4 mt-4 text-sm text-zinc-500">
            <span>{template.output_format.toUpperCase()}</span>
            <span>{isLandscape ? 'Landscape' : 'Portrait'}</span>
            <span>{sections.length} section{sections.length !== 1 ? 's' : ''}</span>
          </div>
        </div>

        {/* Sections */}
        {sections.length === 0 ? (
          <div className="bg-white rounded-lg shadow-lg p-12 text-center text-zinc-500">
            <svg className="w-16 h-16 mx-auto mb-4 text-zinc-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <p className="text-lg">No sections yet</p>
            <p className="text-sm mt-2">Add sections to see the preview</p>
          </div>
        ) : (
          sections.map((section, index) => (
            <SectionPreview
              key={section.id}
              section={section}
              number={index + 1}
              themeStyles={themeStyles}
            />
          ))
        )}
      </div>
    </div>
  );
}

interface SectionPreviewProps {
  section: PreviewSection;
  number: number;
  themeStyles: ReturnType<typeof buildThemeStyles>;
}

function SectionPreview({ section, number, themeStyles }: SectionPreviewProps) {
  // Sort subsections by position
  const sortedSubsections = [...section.subsections].sort((a, b) => a.position - b.position);

  return (
    <div className="bg-white rounded-lg shadow-lg overflow-hidden">
      {/* Section content */}
      <div className="p-8">
        {/* Section title */}
        <h2
          className="text-xl font-semibold text-zinc-900 pb-3 mb-6 border-b-2 border-sky-600"
          style={themeStyles.sectionTitleStyle}
        >
          <span className="text-zinc-400">{number}.</span>{' '}
          {applyTitleCaseMode(section.title || 'Untitled Section', themeStyles.sectionTitleCase)}
        </h2>

        {/* Subsections */}
        <div className="space-y-6">
          {sortedSubsections.length === 0 ? (
            <div className="text-zinc-400 italic text-center py-8">
              No subsections in this section
            </div>
          ) : (
            sortedSubsections.map((subsection) => (
              <SubsectionPreview key={subsection.id} subsection={subsection} themeStyles={themeStyles} />
            ))
          )}
        </div>

        {/* Section footer */}
        <div className="mt-6 pt-3 border-t border-zinc-200 flex justify-between text-xs text-zinc-400">
          <span>{sortedSubsections.length} subsection{sortedSubsections.length !== 1 ? 's' : ''}</span>
          <span>Section {number}</span>
        </div>
      </div>
    </div>
  );
}

interface SubsectionPreviewProps {
  subsection: PreviewSubsection;
  themeStyles: ReturnType<typeof buildThemeStyles>;
}

function SubsectionPreview({ subsection, themeStyles }: SubsectionPreviewProps) {
  const label = positionToLabel(subsection.position);
  const hasContent = subsection.content && subsection.content.trim().length > 0;

  return (
    <div className="border border-zinc-200 rounded-lg overflow-hidden">
      {/* Subsection header */}
      <div className="flex items-center gap-3 px-4 py-2 bg-zinc-50 border-b border-zinc-200">
        <span className="inline-flex items-center justify-center w-7 h-7 bg-sky-600 text-white text-sm font-bold rounded">
          {label}
        </span>
        {subsection.title && (
          <span className="font-medium text-zinc-700" style={themeStyles.subsectionTitleStyle}>
            {applyTitleCaseMode(subsection.title, themeStyles.subsectionTitleCase)}
          </span>
        )}
        <div className="flex-1" />
        {subsection.has_instructions && (
          <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded">
            Instructions
          </span>
        )}
        {subsection.has_notes && (
          <span className="text-xs bg-purple-100 text-purple-700 px-2 py-0.5 rounded">
            Notes
          </span>
        )}
      </div>

      {/* Subsection content */}
      <div className="p-4">
        {hasContent ? (
          subsection.content_type === 'markdown' || !subsection.content_type ? (
            <Markdown content={subsection.content!} className="prose prose-sm max-w-none" />
          ) : subsection.content_type === 'json' ? (
            <ChartRenderer content={subsection.content!} />
          ) : (
            <pre className="text-xs overflow-auto whitespace-pre-wrap bg-zinc-100 p-3 rounded text-zinc-700">
              {subsection.content}
            </pre>
          )
        ) : (
          <div className="text-zinc-400 italic text-sm py-4 text-center">
            No content
          </div>
        )}
      </div>
    </div>
  );
}
