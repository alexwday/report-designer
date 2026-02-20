import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { Components } from 'react-markdown';

interface MarkdownProps {
  content: string;
  className?: string;
}

const components: Components = {
  p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
  h1: ({ children }) => <h1 className="text-lg font-bold mb-2 mt-3 first:mt-0">{children}</h1>,
  h2: ({ children }) => <h2 className="text-base font-bold mb-2 mt-3 first:mt-0">{children}</h2>,
  h3: ({ children }) => <h3 className="text-sm font-bold mb-1 mt-2 first:mt-0">{children}</h3>,
  ul: ({ children }) => <ul className="list-disc list-inside mb-2 space-y-0.5">{children}</ul>,
  ol: ({ children }) => <ol className="list-decimal list-inside mb-2 space-y-0.5">{children}</ol>,
  li: ({ children }) => <li className="leading-relaxed">{children}</li>,
  code: (props) => {
    const { children, className } = props;
    const isCodeBlock = className?.startsWith('language-');
    if (isCodeBlock) {
      return (
        <code className="block overflow-x-auto p-3 bg-zinc-900 text-zinc-100 rounded-lg text-xs font-mono my-2">
          {children}
        </code>
      );
    }
    return (
      <code className="px-1 py-0.5 bg-zinc-200/60 text-zinc-800 rounded text-[0.85em] font-mono">
        {children}
      </code>
    );
  },
  pre: ({ children }) => <pre className="my-2">{children}</pre>,
  blockquote: ({ children }) => (
    <blockquote className="border-l-2 border-zinc-300 pl-3 italic text-zinc-500 my-2">
      {children}
    </blockquote>
  ),
  a: ({ href, children }) => (
    <a href={href} className="text-sky-600 hover:text-sky-700 underline" target="_blank" rel="noopener noreferrer">
      {children}
    </a>
  ),
  table: ({ children }) => (
    <div className="overflow-x-auto my-2">
      <table className="min-w-full text-sm border border-zinc-200 rounded">{children}</table>
    </div>
  ),
  thead: ({ children }) => <thead className="bg-zinc-100">{children}</thead>,
  th: ({ children }) => <th className="px-3 py-1.5 text-left font-medium text-zinc-700 border-b border-zinc-200">{children}</th>,
  td: ({ children }) => <td className="px-3 py-1.5 border-b border-zinc-100">{children}</td>,
  hr: () => <hr className="my-3 border-zinc-200" />,
  strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
};

export function Markdown({ content, className = '' }: MarkdownProps) {
  return (
    <div className={['markdown-content', className].filter(Boolean).join(' ')}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={components}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
