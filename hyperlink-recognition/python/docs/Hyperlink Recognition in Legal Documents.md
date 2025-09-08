# Hyperlink Recognition in Legal Documents

Focus: identifying references to laws, statutes, and case numbers in legal documents.

## Context

Legal documents frequently reference other laws, regulations, cases, or clauses. These references can appear in multiple forms:

- Titles enclosed in `《》, “”`
- Keywords or predefined terms
- Common Abbreviations (short names)
- Case numbers

Currently, these references exist as plain text, requiring manual lookup and interpretation. This leads to several issues:

- Users cannot quickly navigate to the referenced law or case.
- References may be ambiguous or outdated.
- Manual verification and linking are time-consuming and error-prone.

**Objective**: Build an automated Hyperlink Recognition system that detects references, validates their correctness, and converts them into interactive hyperlinks while ensuring accuracy and uniqueness.


## High-Level Workflow

1. Retrieve the document from DataLake
   - Triggered by the SQS event.
   - Retrieve only the text nodes may contain entities requiring enrichment from DataLake, based on the event metadata, instead of fetching the entire document.

2. Rule-Based Extraction of Potential References and relevant Contextual Attributes

   - Scan the document for potential references (titles, case numbers, abbreviations, statutes, etc.)
   - Extract associated contextual attributes, including promulgators, issue numbers, and issue dates.

3. Dependency Resolution and Context Association

   - Process dependencies between references.
   - For example, abbreviations defined within the document cannot exist independently; they must be linked to the original law reference.
   - Associate references with relevant contextual attributes to aid validation and disambiguation.

4. Reference Text Normalization

   - Clean and standardize the reference text.
   - Remove optional prefixes, suffixes, or extraneous information while preserving the essential core of the reference.

5. Backend Validation

   - Query the validation service to verify the existence and correctness of each reference.

6. Unique Version Resolution

   - Determine a unique version for each reference using techniques such as prefix/suffix matching and leveraging contextual attributes (e.g., promulgators, issue number, issue date.).

7. Hyperlink Markup Generation

   - Convert validated references into functional hyperlinks within the document while preserving its original format.

8. Document Update

   - Send back only enriched text nodes where entities were recognized.
   - The backend automatically handles persistence, versioning, and metadata management.


```mermaid
flowchart LR
    A[Start: Retrieve the document from DataLake] --> B[Rule-Based Extractor]
    B --> C[Dependency Resolution and Context Association]
    C --> D[Reference Text Normalization]
    D --> E[Backend Validation]
    E --> F[Unique Version Resolution]
    F --> G[Hyperlink Markup Generation]
    G --> H[Document Update]
    H --> I[End: Document Enriched with Hyperlinks]
```

### Future Improvements / Advanced Extraction (MCP / LLM)

```mermaid
flowchart LR
    A[SQS Event: New Document] --> B[Hyperlink Recognition Lambda]

    B --> C[Fetch Document from DataLake【S3】]
    C --> D[Rule-Based Extractor]
    D --> E[Entities from Rules]

    D --> F[Check for Unresolved Text/Complex References?]
    F -- Yes --> G[LLM-Based Extractor【MCP Service】]
    G --> H[Entities from LLM]
    F -- No --> I[Skip LLM]

    E --> J[Merge Entities]
    H --> J
    I --> J

    J --> K[Dependency Resolution & Context Association]
    K --> L[Reference Text Normalization]
    L --> M[Backend Validation Service【REST API】]
    M --> N[Unique Version Resolution]
    N --> O[Generate Hyperlink Markup]
    O --> P[Update Document via DataLake API]
    P --> Q[Document Updated in S3]
```

## Rule-Based Entity Extraction Engine

**Purpose**: Automatically extract potential references in legal documents and extract relevant contextual attributes to support hyperlink recognition.

> [!Tip] Internally, both references and reference attributes are treated as entities, extracted from text using configurable rules. Using a generic Entity structure allows unified processing while preserving metadata for later validation and linking.

- **Input**: a paragraph of text (smallest semantic unit)
- **Output**: a list of potential entity with metadata.

```json
[
    {
        "text": "Criminal Law",
        "start": 0,
        "end": 11,
        "category": "Reference",
        "entity_type": "Abbreviation/Title/CaseNo",
        "attrs": []
    }
]
```

**Entity Definition**

```python
@dataclass
class Entity:
    text: str # Extracted text span
    start: int # Inclusive start index
    end: int # Exclusive end index
    category: str # "Reference" or "Attr"
    entity_type: str # Specific type, e.g., "Title", "CaseNo", "Abbreviation"
    attrs: list[str] | None = None # Optional list of contextual attributes
```

**Base Extractor Interface**

```python
class Extractor(ABC):
    """Abstract base class for entity extractors."""

    @abstractmethod
    def extract(self, paragraph: str) -> Iterable[Entity]:
        """
        Extract entities from a text paragraph.

        :param paragraph: The text to process.
        :returns An iterable of Entity objects containing extracted spans and metadata.
        """
        raise NotImplementedError
```

### Supported Extraction Rules

- **Symbol Pair-based Extraction**: Extract entities enclosed within special paired symbols (e.g., 《...》).
- **Keyword-based Extraction**: Extract entities using a predefined list of keywords.
- **Dynamic keyword Extraction**: Extract entities defined dynamically in the document (e.g., abbreviations). The keyword list is dynamically updated, and subsequent text is scanned again based on the updated list.
- **Regex-Based Extraction**: Extract structured entities such as case numbers, article numbers, issue numbers, and dates.


#### Symbol Pair-based Extraction

Extract entities enclosed within special paired symbols (e.g., 《...》). 

This extractor is configurable with a set of symbol pairs, where each pair explicitly defines a left and right delimiter.

- Supports multiple symbol pairs (e.g., 《...》, (...), [...]).
- Handles nested symbols based on the configured nesting strategy:
  - **outermost**: keep only the widest enclosing pair.
  - **innermost**: keep only the deepest enclosed pair.
  - **all**: keep all matched pairs (default).

```python
NestingStrategy = Literal["outermost", "innermost", "all"]

class SymbolBasedExtractor(Extractor):
    def __init__(self, symbol_pairs: dict[str, str], strategy: NestingStrategy = "all"):
        """
        :param strategy: defines how to handle nested paired symbols
                         "outermost": keep only the widest enclosing pair
                         "innermost": keep only the deepest enclosed pair
                         "all": keep all matched pairs (default)
        """
        self.strategy = strategy

    def extract(self, paragraph: str) -> Iterable[Entity]:
        """
        Extract text enclosed in paired symbols (e.g., 《...》) as entities.
        Handles nested symbols based on the configured strategy.
        """
        ...
```

#### Keyword-based Extraction

Extract entities using a predefined list of keywords. Any occurrence of these keywords is treated as an entity. 

This extractor is suitable for identifying references such as law promulgators, commonly used legal terms, or fixed phrases.

- Configurable keyword list.
- Supports exact matching and optional case-insensitive matching.
- Handles overlapping keywords with strategies such as “longest match first”.
- ~~Exclusion of invalid keywords.~~
  - ~~Ignore matches that appear as a substring in a larger term that is not relevant.~~
    - ~~Example: If "公司法" is a keyword, but the text contains "外国公司法律法规", the match for "公司法" is ignored.~~

>[!tip] Note on Invalid Keywords
Exclusion of invalid keywords (e.g., “公司法” appearing inside “外国公司法律法规”) is not handled inside the extractor.
This filtering should be done as a post-processing step, comparing matched results with known invalid contexts or exclusion lists.

**Algorithm Implementation**

- Use a Trie (prefix tree) or Aho-Corasick multi-pattern matching algorithm to efficiently match multiple keywords at once. These methods naturally handle overlapping patterns and support longest-match priority.

- Alternatively, after generating all matches, apply a post-processing step:
  - Sort matches by length (longest first).
  - Iterate through matches in order of appearance.
  - Check for conflicts/overlaps and retain the longest valid match in each overlapping region.

```python
class KeywordBasedExtractor(Extractor):
    def __init__(self, keywords: list[str], case_sensitive: bool = False):
        """
        :param keywords: List of predefined keywords to match
        :param case_sensitive: Whether matching should be case-sensitive
        """
        self.keywords = keywords
        self.case_sensitive = case_sensitive
        self.fuzzy_threshold = fuzzy_threshold

    def extract(self, paragraph: str) -> Iterable[Entity]:
        """
        Extract entities by matching against predefined keywords.
        """
        # Implementation would scan paragraph for keyword matches
        # and return Entity objects with appropriate metadata
        ...
```

#### Dynamic keyword Extraction

Extract entities based on keywords defined within the document itself. This supports abbreviations or short forms introduced in the text. The keyword list is dynamically updated, and subsequent text is scanned again based on the updated list.

This extractor operates in multiple passes, first identifying potential keyword definitions within the document, then using those discovered keywords to find additional references throughout the text.

- Recognizes common patterns for defining abbreviations and terms(e.g., “简称为... / hereinafter referred to as …”).
- Dynamically updates the keyword list as the document is scanned.
- Handles temporal validity: keywords are only valid after being defined.
- Supports nested and overlapping keywords with priority rules.

**Algorithm Implementation**

- Step 1: Identify new keyword definitions
    - Use regex patterns (e.g., "简称为 xxx", "hereinafter referred to as xxx") to extract newly defined keywords.
    - Update the dynamic keyword dictionary with discovered definitions and their valid scope (temporal and/or paragraph range).

- Step 2: Multi-pattern keyword matching
    - Use a Trie (prefix tree) or Aho-Corasick algorithm to match multiple keywords efficiently.
    - Handles overlapping or nested keywords. Apply longest-match priority for conflict resolution.

- Step 3: Post-processing
    - Sort matches by length (longest first) and position.
    - Resolve overlaps by keeping the longest valid match in each region.

- Step 4: Temporal validity
    - Only consider keywords after they are defined; ignore occurrences before the definition.

```python
class DynamicKeywordExtractor(Extractor):
    def __init__(self, definition_patterns: list[str], default_keywords: list[str]):
        """
        :param definition_patterns: Regex patterns for identifying keyword definitions
        :param default_keywords: A list of pre-defined keywords to initialize the extractor
        """
        self.definition_patterns = definition_patterns
        self.dynamic_keywords = {**default_keywords}

    def extract(self, paragraph: str) -> Iterable[Entity]:
        """
        Extract entities using dynamically discovered keywords.
        Performs multiple passes to build and utilize the keyword dictionary.
        """
        # Pass 1: Identify new keyword definitions
        # Pass 2+: Use discovered keywords to find references
        # Return all discovered entities
        ...
```

#### Regex-Based Extraction

Use fixed patterns to extract structured entities such as case numbers, article numbers, issue numbers, and dates.

- Configurable regex patterns for different entity types.
- Captures matched text and optional named groups for contextual attributes.
- Can handle multiple patterns in a single pass.

```python
class RegexBasedExtractor(Extractor):
    def __init__(self, patterns: dict[str, str]):
        """
        :param patterns: Dictionary mapping entity types to regex patterns
        """
        self.patterns = {entity_type: re.compile(pattern) for entity_type, pattern in patterns.items()}

    def extract(self, paragraph: str) -> Iterable[Entity]:
        """
        Extract entities using predefined regex patterns.
        """
        # Apply each pattern to the paragraph
        ...
```


### Extraction Pipeline

**Pipeline Overview**

- Input paragraph → all extractors applied in parallel
- Merge extracted entities
- Post-processing:
    - Remove invalid keywords
    - Resolve overlaps based on extractor priority and longest-match
- Output final list of entities

```mermaid
flowchart LR
    A[Input: Paragraph of Text] -->|Parallel| B1[Symbol Pair-based Extraction]
    A -->|Parallel| B2[Keyword-based Extraction]
    A -->|Parallel| B3[Dynamic Keyword Extraction]
    A -->|Parallel| B4[Regex-based Extraction]

    B1 --> C[Merge Extracted Entities]
    B2 --> C
    B3 --> C
    B4 --> C

    C --> D["Post-Processing<br>(Remove Invalid Keywords & Resolve Conflicts)"]
    D --> E[Output: Final List of Entities]
```

**Rule Application by Scenario**

| scenarios        | category  | Detection Rule              |
| ---------------- | --------- | --------------------------- |
| Law Title        | Reference | Symbol & Keyword extraction |
| This Law(该法)   | Reference | Keyword extraction          |
| Hereof(本法)     | Reference | Keyword extraction          |
| Case Number      | Reference | Regex extraction            |
| Abbreviation     | Reference | Dynamic keyword extraction  |
| Article Number   | Reference | Regex extraction            |
| Issue Number     | Attr      | Regex extraction            |
| Issue Date       | Attr      | Regex extraction            |
| Promulgator      | Attr      | Keyword extraction          |
| Invalid Keywords | Other     | Keyword extraction          |


### Post-processing

After running multiple extraction rules in parallel, the results go through a unified post-processing stage to ensure correctness and consistency.

#### Remove Invalid Keywords

Sometimes a keyword match is spurious because it occurs as a substring of a larger, irrelevant phrase. In such cases, the match should be excluded.

```
假设 “公司法” 是关键字，识别 “根据外国公司法律法规...”，会错误将该文本中的 “公司法” 识别为引用，设定一组排除关键字并识别，如果关键字与识别的排除关键字 overlap, 则忽略
```

- Rule: If a keyword overlaps with an exclusion keyword, ignore the match.
- Example:
  - Keyword: 公司法 ("Company Law")
  - Text: 根据外国公司法律法规... ("according to Foreign Company Law Regulations...")
  - Incorrect extraction: 公司法
  - Correct behavior: ignore this match because it appears inside a larger, irrelevant term.

#### Overlap Conflict Resolution

When multiple rules run in parallel, overlap conflicts may occur—two candidate entities share the same character span or one contains the other.

**Resolution Strategy**
  - Entity Type Priority: Law Titles > Abbreviations
  - Longest Match Priority: always prefer the longer span.

Example: Abbreviation Overlap Case

```
根据《中华人民共和国刑法》（以下简称为 “刑法”）和《2015年刑法修正案》（以下简称为 “2015刑法”），本案裁定如下。
```

Extraction Logic:

- Symbol Pair-based Extraction
  - 《中华人民共和国刑法》 → Law Title
  - 《2015年刑法修正案》→ Law Title

- Abbreviation Definition Extraction (Dynamic keyword extraction)
  - 简称为 “刑法” -> defines 刑法 -> Abbreviation
  - 简称为 “2015刑法” → defines 2015刑法 -> Abbreviation

- Overlap Handling
  - Conflict: 刑法 vs. 2015刑法 (substring overlap)
  - Correct resolution: keep the longer abbreviation (2015刑法) to avoid splitting it into 2015 + 刑法.
