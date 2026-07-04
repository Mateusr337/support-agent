import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import "./MarkdownContent.css";

interface MarkdownContentProps {
  content: string;
  showCursor?: boolean;
}

export default function MarkdownContent({ content, showCursor = false }: MarkdownContentProps) {
  return (
    <div className={`markdown-content${showCursor ? " markdown-content--streaming" : ""}`}>
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
    </div>
  );
}
