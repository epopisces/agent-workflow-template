# Knowledge Ingestion Agent Prompt
> GitHub Copilot -> Claude Opus 4.5

Let's create the Knowledge Ingestion Agent.  It is a tool with the core function of updating the following knowledge sources listed in the PRD
- **Instructions File**: Local file with high-level org context summaries
- **Org URL Index**: Index of org-relevant URLs with metadata (domain of knowledge, context, content summary)
- **User Notes Files**: Local markdown files with frontmatter (both agent and user-generated)
    - **User Notes Index**: Index of Local markdown files with metadata (domain of knowledge, context, content summary)
- **Future**: Vector database for mature RAG implementation

It should store information in the appropriate formats (converting the incoming data to the appropriate format if necessary).

It should support a Confidence and Relevance score passed along with the content, and be capable of pausing (human-in-the-loop) to prompt the user to review/validate before committing if the confidence or relevance scores are below a certain threshold (the threshold should be stored in a config file).  Let me know if this isn't a supported feature of agent-as-tool in the framework.

The locations of the User Notes Index should be a configurable and stored in a config file in a dictionary of key/value pairs, with topic as the top level key and key value pairs for directory path, template file location, and any other useful information for processing.  This dictionary should be initially configured with just the key of 'default' with a directory path pointing to a project subdirectory named 'notes', and a generic template including sensible frontmatter defaults for quick agent reference to enable agent decisionmaking around degree of ingestion.

I'm open to other suggestions in meeting the knowledge sources goals.  Including metadata for the indexes, etc.