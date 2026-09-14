# Harbor — Phase 4: Knowledge Base & Document Ingestion

## Objective

Phase 4 builds Harbor's document ingestion pipeline.

The system converts knowledge-base documents into normalized,
metadata-rich chunks that can later be embedded and stored in
Supabase pgvector.

## Supported File Types

- TXT
- PDF
- DOCX

## Pipeline

Raw Document
    |
    v
Document Loader
    |
    v
Text Extraction
    |
    v
Text Cleaning
    |
    v
Chunking Strategy
    |
    +---- Fixed Character Chunking
    |
    +---- Recursive Character Chunking
    |
    v
Structured Document Chunks
    |
    v
Local JSON Output

Embeddings and vector storage are intentionally deferred to the next
phase.

## Document Loaders

Harbor contains dedicated loaders for:

- text files
- PDF files
- Microsoft Word files

All loaders produce the same LoadedDocument schema.

This prevents later pipeline components from becoming dependent on
specific file formats.

## Text Cleaning

The cleaner normalizes:

- line endings
- repeated spaces
- excessive blank lines

The pipeline intentionally preserves:

- punctuation
- capitalization
- headings
- paragraphs
- PDF page markers

These elements can contain semantic information useful for retrieval.

## Chunking Strategies

### Fixed Character Chunking

Splits text using fixed character positions.

Advantages:

- simple
- deterministic
- fast
- useful as an evaluation baseline

Disadvantages:

- may break words
- may break sentences
- may separate related information

### Recursive Character Chunking

Harbor uses LangChain's RecursiveCharacterTextSplitter.

It attempts progressively smaller boundaries:

1. paragraphs
2. newlines
3. sentence-like boundaries
4. spaces
5. characters

This generally preserves natural language structure better than
fixed character slicing.

Recursive chunking is Harbor's default strategy.

## Configurable Parameters

The ingestion pipeline supports:

- chunking strategy
- chunk size
- chunk overlap

Example:

python scripts/ingest_documents.py \
    --strategy recursive \
    --chunk-size 800 \
    --overlap 120

## Chunk Metadata

Every chunk records:

- source
- unique chunk ID
- chunk index
- chunking strategy
- chunk size
- overlap
- source metadata

This metadata will later support:

- debugging
- retrieval evaluation
- citations
- experimentation

## PDF Citations

PDF loaders preserve page markers during extraction.

This gives future Harbor RAG components the information necessary to
produce page-aware source citations.

## Strategy Evaluation

Harbor keeps both fixed and recursive chunking because the project will
later compare retrieval performance rather than assuming one strategy
is always superior.

Evaluation may compare:

- retrieval hit rate
- groundedness
- citation correctness
- no-answer accuracy

## Security

Private client knowledge-base files must not be committed to public Git
repositories.

Only synthetic sample documents should be stored in the project
repository.

## Testing

Phase 4 tests include:

- TXT loading
- fixed chunking
- recursive chunking
- chunk metadata
- overlap validation
- invalid parameter handling

## Phase 4 Completion Criteria

- TXT loading works
- PDF loading works
- DOCX loading works
- text cleaning works
- fixed chunking works
- recursive chunking works
- recursive is default
- chunk settings are configurable
- metadata is preserved
- PDF pages are preserved
- ingestion CLI works
- multiple chunk configurations can be tested
- pytest tests pass
- private files are Git ignored

## Next Phase

Phase 5 will introduce:

- embedding model selection
- embedding dimension decision
- embedding generation
- pgvector table
- vector storage
- vector similarity search
- semantic retrieval testing