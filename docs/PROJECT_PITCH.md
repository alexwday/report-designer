# Report Designer - Project Pitch

**Report Designer** is an LLM-powered internal tool that enables Finance employees to create and automate recurring reports through a conversational interface combined with a visual document builder.

## Curated Data Sources

The Digital and AI team will build and maintain enterprise-wide datasets containing the information commonly used across the organization for reporting. Each curated data source comes with multiple built-in retrieval methods and pre-designed output widgets (summaries, tables, charts, key points, etc.), giving users flexible options for how data appears in their report sections.

## Ad-hoc Uploads

Users can also upload their own documents (Excel, PDF, Word, PowerPoint) for one-off or supplementary data. Since these are unstructured, there's a more focused set of transformation methods available—but still enough to extract summaries, key points, or reference specific content.

## Conversational Instruction Building

For each section of the report, users work with the agent through natural back-and-forth conversation to describe what they want. The agent translates this dialogue into precise instructions that capture the what, how, and why—essentially teaching the system how to generate that section. These instructions become the prompt used each time the template runs, ensuring consistent, repeatable output that reflects exactly what the user refined during the initial build.

## Reusable Templates

As users build their report, the system saves it as a template—a skeleton that captures the document structure, data source mappings, retrieval methods, widgets, and the refined instructions for each section. The next time the report is needed, users simply open the template, answer a few base questions (for curated data: "Which quarter? Which year?" so the system can pull the latest data; for ad-hoc sections: "Please upload the latest version of this file"), and the agent regenerates the report following the saved instructions. If anything needs clarification with the new data, the agent will ask as it works.

## Visual Interface

The UI centers on a live preview of the document being built. Users drag and drop layouts, configure sections visually, and interact with an AI chat overlay—all while seeing their report take shape in real-time. Output is PDF (formatted like presentation slides) or PowerPoint.

---

This eliminates the repetitive manual work of rebuilding similar reports each period while keeping users in full control of content and structure.
