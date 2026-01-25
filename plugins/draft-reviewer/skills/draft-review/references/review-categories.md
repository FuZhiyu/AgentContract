# Review Categories Reference

Detailed criteria for each review category.

## 1. Mathematical Review

### Scope
- Derivations and proofs
- Equations and algebra
- Notation consistency
- Statistical/econometric specifications

### Verification Methods

**Symbolic Verification:**
- Check each algebraic step in derivations
- Verify equation transformations
- Confirm limit taking and approximations

**Numerical Verification:**
- For complex derivations, test with concrete values
- Check boundary conditions (e.g., when parameter → 0 or → ∞)
- Verify dimension/unit consistency

**Notation Consistency:**
- Same variable should have same meaning throughout
- Check for redefinitions without clear notice
- Verify subscript/superscript conventions are consistent

### Common Issues to Check
- Sign errors in derivatives
- Incorrect application of chain rule
- Missing terms in Taylor expansions
- Incorrect matrix algebra (transpose, inverse)
- Statistical distribution misspecifications
- Incorrect asymptotic approximations

## 2. Writing Clarity Review

### Scope
- Sentence structure and readability
- Paragraph organization
- Terminology consistency
- Definition clarity

### Clarity Criteria

**Sentence Level:**
- Avoid overly long sentences (>40 words)
- Subject-verb agreement
- Clear referents for pronouns
- Active voice preferred for key claims

**Paragraph Level:**
- Topic sentence present
- Logical flow between sentences
- One main idea per paragraph
- Transitions between paragraphs

**Terminology:**
- Key terms defined before use
- Consistent terminology throughout
- No conflicting definitions
- Technical terms explained for intended audience

### Common Issues to Check
- Ambiguous "this" or "it" references
- Passive voice obscuring who does what
- Jargon without explanation
- Inconsistent term usage (e.g., "effect" vs "impact" for same concept)
- Circular definitions

## 3. Consistency Check

### Scope
- Numbers across tables and text
- Figure/table references
- Claims match evidence
- Cross-section consistency

### What to Compare

**Tables:**
- Numbers in text match table values
- Table notes consistent with methodology
- Column/row labels clear and consistent

**Figures:**
- Figure captions match content
- Axis labels consistent with text notation
- Legend items all explained

**Claims:**
- Quantitative claims traceable to tables/figures
- Qualitative claims supported by evidence
- No contradictory statements

### Common Issues to Check
- Rounding inconsistencies between text and tables
- Wrong table/figure referenced
- "Significant" claims not matching p-values
- Sample sizes inconsistent across tables
- Time periods/variable definitions drift

## 4. Argument & Logic Review

### Scope
- Logical flow of arguments
- Claim support and evidence
- Identification strategy validity
- Causal claims appropriateness

### Argumentation Criteria

**Claim Support:**
- Each major claim has supporting evidence
- Evidence type matches claim type
- Magnitude of claims proportional to evidence

**Logical Flow:**
- Introduction sets up research question clearly
- Methodology justifies approach taken
- Results follow from methodology
- Conclusions follow from results

**Causal Reasoning:**
- Causal claims have valid identification
- Correlation vs causation distinguished
- Alternative explanations addressed
- Robustness of causal claims tested

### Common Issues to Check
- Overclaiming (strong claims from weak evidence)
- Missing logical steps
- Unaddressed alternative explanations
- Circular reasoning
- Post-hoc rationalization of results

## 5. Proofreading

### Scope
- Spelling and typos
- Grammar and punctuation
- Formatting consistency
- LaTeX/rendering issues

### Proofreading Checklist

**Spelling/Typos:**
- Common homophone errors (their/there, its/it's)
- Double words
- Missing words
- Proper nouns spelled correctly

**Grammar:**
- Subject-verb agreement
- Tense consistency
- Article usage (a/an/the)
- Comma usage

**Formatting:**
- Consistent heading styles
- Consistent number formatting (1,000 vs 1000)
- Consistent date formats
- Table/figure numbering sequential
- Consistent font/spacing

**LaTeX-Specific:**
- Missing closing braces
- Equation numbering gaps
- Broken cross-references
- Missing bibliography entries
- Overfull/underfull hbox warnings

### Common Issues to Check
- Capitalization inconsistency
- Hyphenation inconsistency
- Citation format inconsistency
- Footnote/endnote format inconsistency

## 6. Citation Check

### Scope
- Citation completeness
- Reference format
- Citation-reference matching
- Key literature coverage

### Citation Criteria

**Completeness:**
- All claims have appropriate citations
- Classic/foundational papers cited
- Recent relevant literature included
- No "orphan" citations (cited but not in bibliography)
- No "orphan" references (in bibliography but not cited)

**Format:**
- Consistent citation style (APA, Chicago, etc.)
- All required fields present (author, year, title, journal)
- DOIs/URLs functional and correctly formatted
- Page numbers included for direct quotes

**Appropriateness:**
- Citations support the claims they're attached to
- Not over-citing or under-citing
- Self-citation appropriate (not excessive)

### Common Issues to Check
- Author name spelling variations
- Year discrepancies
- Journal name abbreviation inconsistency
- Missing working paper version updates
- Broken URLs

## 7. Code-Paper Consistency

### Scope
- Methodology description matches implementation
- Variable definitions match code
- Sample construction reproducible
- Results replicable from code

### Consistency Criteria

**Methodology:**
- Equations in paper match code implementation
- Sample restrictions described match code
- Variable transformations documented

**Variables:**
- Variable names/descriptions traceable to data/code
- Missing value handling consistent
- Winsorization/trimming as described

**Results:**
- Key statistics reproducible
- Robustness checks implemented as described
- Figures generated from provided code

### Common Issues to Check
- Undocumented sample restrictions in code
- Different default values than stated
- Outdated code not matching final paper
- Hard-coded values that should be parameters
- Missing intermediate data processing steps
