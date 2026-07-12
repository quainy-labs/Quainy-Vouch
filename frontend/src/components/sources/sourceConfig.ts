export type SourceGuideCard = {
  id: string;
  title: string;
  description: string;
  source_type: string;
};

export type SourceCopy = {
  heading: string;
  helper: string;
  titlePlaceholder: string;
  textLabel: string;
  textPlaceholder: string;
  uriLabel?: string;
  uriPlaceholder?: string;
  showUpload?: boolean;
};

export const sourceStatuses = ["approved", "disabled", "archived"];

export const sourceGuideCards: SourceGuideCard[] = [
  {
    id: "document",
    title: "Upload a company document",
    description: "Best for product source-of-truth, positioning docs, policies, and launch notes.",
    source_type: "markdown",
  },
  {
    id: "paste",
    title: "Paste approved text",
    description: "Best for short claims, customer proof, FAQs, and voice guidance.",
    source_type: "manual_note",
  },
  {
    id: "url",
    title: "Add a public URL",
    description: "Best for docs, changelogs, pages, and source material you want tracked by origin.",
    source_type: "url",
  },
  {
    id: "release",
    title: "Add release notes",
    description: "Best for product updates, changelog entries, and launch context.",
    source_type: "github_release",
  },
  {
    id: "notion",
    title: "Add a Notion page",
    description: "Best for internal knowledge that has already been approved for content use.",
    source_type: "notion_page",
  },
];

export const sourceTypeText: Record<string, SourceCopy> = {
  manual_note: {
    heading: "Paste approved company context",
    helper: "Use this for claims, positioning, proof points, FAQs, or voice guidance that is already approved for public content.",
    titlePlaceholder: "Example: Approved positioning notes",
    textLabel: "Approved note",
    textPlaceholder: "Paste approved claims, customer proof, positioning, policies, or product details.",
  },
  markdown: {
    heading: "Upload or paste a company document",
    helper: "Use this for source-of-truth documents, launch notes, product docs, or policy language.",
    titlePlaceholder: "Example: Product source of truth",
    textLabel: "Document text",
    textPlaceholder: "Upload a markdown/text file or paste the exact approved document content here.",
    uriLabel: "Document reference",
    uriPlaceholder: "Filename, doc URL, or internal reference",
    showUpload: true,
  },
  text: {
    heading: "Upload or paste a text document",
    helper: "Use this when the approved source is a plain text document.",
    titlePlaceholder: "Example: Customer proof notes",
    textLabel: "Document text",
    textPlaceholder: "Upload a text file or paste the exact approved document content here.",
    uriLabel: "Document reference",
    uriPlaceholder: "Filename, doc URL, or internal reference",
    showUpload: true,
  },
  url: {
    heading: "Add a selected public URL",
    helper: "Use this for one approved public page. The app stores only the page you provide, not a full website crawl.",
    titlePlaceholder: "Example: Public changelog page",
    textLabel: "Approved page text",
    textPlaceholder: "Paste the approved page text or relevant excerpt that should be available as source evidence.",
    uriLabel: "Public page URL",
    uriPlaceholder: "https://example.com/docs/product-update",
  },
  github_release: {
    heading: "Add release notes",
    helper: "Use this for public release notes or changelog excerpts that should support launch and product-update content.",
    titlePlaceholder: "Example: v1.8 launch notes",
    textLabel: "Approved release text",
    textPlaceholder: "Paste the public release notes, changelog excerpt, or approved launch details.",
    uriLabel: "GitHub release or repo URL",
    uriPlaceholder: "https://github.com/org/repo/releases/tag/v1.8.0",
  },
  notion_page: {
    heading: "Add a selected Notion page",
    helper: "Use this only for a page whose contents have already been approved for content generation.",
    titlePlaceholder: "Example: Approved campaign brief",
    textLabel: "Approved page text",
    textPlaceholder: "Paste the approved Notion page contents or excerpt.",
    uriLabel: "Notion page URL",
    uriPlaceholder: "https://notion.so/...",
  },
};

export const readinessCopy: Record<string, string> = {
  strong: "Strong evidence base for the current workflow. Keep adding context as the company changes.",
  ready: "Enough approved context for generation. Add more source material over time to improve ranking accuracy.",
  building: "Usable, but still missing context that would make suggestions sharper.",
  blocked: "Needs approved company context before reliable opportunities and drafts.",
};

export const readinessPriorityLabel: Record<string, string> = {
  high: "High",
  medium: "Medium",
  low: "Low",
};
