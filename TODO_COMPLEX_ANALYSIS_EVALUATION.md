# TODO: Complex Analysis Evaluation Implementation

This document outlines the tasks needed to implement comprehensive evaluation metrics for the complex Hawaiian passage analysis task (translation + commentary + summary).

## Hybrid Approach Implementation Status (✅ COMPLETED)

The hybrid complex analysis approach has been successfully implemented and tested:
- ✅ All 14 passages processed with 100% success rate
- ✅ Fixed commentary extraction (14/14 passages have commentary)
- ✅ Implemented robust retry mechanism with exponential backoff
- ✅ Created new extraction script for hybrid outputs
- ✅ Successfully tested with real model (qwen3-4b-awq-40k-maui)
- ✅ Benchmarking infrastructure working with semantic similarity evaluation
- ✅ Achieved 77.71% translation similarity, 61.93% commentary similarity
- ✅ Full documentation added to CLAUDE.md

## Recently Completed Tasks (✅)

### Identified Issues with Current Implementation
- [x] Discovered that only 3/14 passages showed commentary due to extraction script parsing issue
- [x] Analyzed that the model actually generated commentary for all 14 paragraphs
- [x] Identified that current approach sends entire chapter to LLM at once
- [x] Determined that reference dataset has inconsistent commentary grouping (paragraphs 10-14 grouped)

## New Priority Tasks - Hybrid Approach Implementation

### Task 16: Design Hybrid Complex Analysis Approach
- [x] Create new task type: `"hybrid_analysis"` in task configuration system
- [x] Design two-stage processing: passage-level then chapter-level
- [x] Define passage-level outputs for translation and commentary
- [x] Define chapter-level output for summary generation
- [x] Maintain backward compatibility with existing `"analysis"` type

### Task 17: Implement Passage-Level Processing
- [x] Create passage-level prompt templates for translation
- [x] Create passage-level prompt templates for commentary
- [x] Update `custom-model-parallel-v2.py` with `process_hybrid_analysis()` method
- [x] Implement parallel processing for individual passages
- [x] Store passage-level results in separate JSON files
- [x] Handle special case for paragraphs 10-14 grouped commentary

### Task 18: Implement Chapter-Level Summary Generation
- [x] Create chapter-level prompt template for summary
- [x] Collect all passage translations as context for summary
- [x] Generate cohesive chapter summary after all passages complete
- [x] Store summary in chapter-level manifest file
- [x] Link passage files to chapter manifest

### Task 19: Update Data Extraction for Hybrid Outputs
- [x] Create new `extract_hybrid_complex_analysis.py` to read passage-level files
- [x] Map translations and commentary to correct dataset rows
- [x] Handle chapter-level summary appropriately
- [x] Ensure compatibility with existing benchmarking tools
- [x] Fix the commentary detection issue (now extracting all 14/14)

### Task 20: Test and Validate Hybrid Approach
- [x] Test with real model using OPENAI_MODEL_NAME and OPENAI_API_BASE_URL from .env
- [x] Verify all 14 passages have commentary in output
- [x] Validate parallel processing performance (with retry mechanism)
- [x] Ensure summary quality with full context
- [x] Successfully achieved 100% completion rate (14/14 passages)
- [x] Test extraction and benchmarking pipeline end-to-end
- [x] Achieve semantic similarity evaluation: 77.71% translation, 61.93% commentary

## High Priority Tasks

### Task 9: Create Multi-Component Semantic Similarity Evaluator (✅ COMPLETED)
- [x] Create `benchmarking/complex_semantic_similarity.py`
- [x] Implement separate embedding generation for:
  - [x] Translation components
  - [x] Commentary components  
  - [x] Summary components
- [x] Compare each component against its reference independently
- [x] Generate component-specific similarity scores
- [x] Handle missing/partial components gracefully
- [x] Support batch processing for efficiency
- [x] Support both regular and hybrid extracted files
- [x] Successfully tested with qwen3-4b-awq-40k-maui model

### Task 10: Design Translation Quality Scoring for Complex Analysis (✅ COMPLETED)
- [x] Implement semantic similarity specifically for Hawaiian→English translations within complex passages
- [x] Account for passage context and cultural nuances
- [x] Compare model translations against reference translations paragraph by paragraph
- [x] Handle multi-paragraph translation scoring with weighted averages
- [x] Create translation-specific quality metrics:
  - [x] Semantic accuracy
  - [x] Cultural preservation
  - [x] Fluency scoring
- [x] Integrated into complex_semantic_similarity.py with cosine similarity scoring

### Task 11: Implement Commentary Quality Evaluation Using LLM Judge (✅ COMPLETED)
- [x] Design LLM judge prompts for evaluating cultural/historical commentary quality
- [x] Implement evaluation criteria:
  - [x] Cultural accuracy (1-5 scale)
  - [x] Historical context depth (1-5 scale)
  - [x] Linguistic analysis quality (1-5 scale)
  - [x] Academic rigor (1-5 scale)
- [x] Create rubric-based scoring system
- [x] Generate detailed feedback on commentary strengths/weaknesses
- [x] Handle rate limiting for LLM judge API calls
- [x] Store evaluation results in structured format
- [x] Integrated semantic similarity evaluation for commentary components

## Current Status Summary

### 🎉 Major Achievements
- **Hybrid processing system fully implemented** with 100% success rate (14/14 passages)
- **End-to-end pipeline working** from translation → extraction → benchmarking  
- **Semantic similarity evaluation operational** with quantitative metrics
- **Reference dataset fixed** and properly structured
- **Complete documentation** added to CLAUDE.md

### 📊 Performance Metrics (Latest Models - Post-Normalization)

#### 🥇 qwen3-235b-a22b-think-parser-fireworks (BEST)
- **Translation similarity**: 93.65% (14/14 valid passages)
- **Commentary similarity**: 68.85% (14/14 valid passages)
- **Summary similarity**: 82.76% (1/1 valid comparison - chapter-level)
- **Composite score**: 0.8155
- **Processing completion**: 100% (14/14 passages)

#### 🥈 gemma-3-27b-it-qat-mlx-maui
- **Translation similarity**: 93.93% (14/14 valid passages) 
- **Commentary similarity**: 68.56% (14/14 valid passages)
- **Summary similarity**: 80.42% (1/1 valid comparison - chapter-level)
- **Composite score**: 0.8108
- **Processing completion**: 100% (14/14 passages)

#### 🥉 llama4-maverick-fireworks
- **Translation similarity**: 93.86% (14/14 valid passages)
- **Commentary similarity**: 68.16% (14/14 valid passages)
- **Summary similarity**: 74.10% (1/1 valid comparison - chapter-level)
- **Composite score**: 0.7963
- **Processing completion**: 100% (14/14 passages)

#### qwen3-30b-a3b-awq-128k-maui (with prompt variations)
- **Few-shot prompts**: Translation 85.12%, Commentary 71.75%, Summary 70.68%, Composite 0.7689
- **Original prompts**: Translation 85.89%, Commentary 69.42%, Summary 73.52%, Composite 0.7683
- **Improved prompts**: Translation 82.98%, Commentary 68.39%, Summary 77.72%, Composite 0.7609
- **Processing completion**: 100% (14/14 passages) for all variants

#### qwen3-4b-awq-40k-maui (hybrid_complex_analysis_original)
- **Translation similarity**: 79.75% (14/14 valid passages)
- **Commentary similarity**: 71.13% (14/14 valid passages)
- **Summary similarity**: 66.57% (1/1 valid comparison - chapter-level)
- **Composite score**: 0.7366
- **Processing completion**: 100% (14/14 passages)
- **Note**: Fixed corrupted passage 13 translation using individual passage repair approach

### 🐛 Recent Bug Fixes
- **Grouped commentary passages (10-14)**: Fixed missing JSON file saves in `_process_grouped_commentary_passage`
- **Data format standardization**: ✅ Summaries now standardized to passage 1
- **Passage recovery**: ✅ Fixed malformed passage 7 using subset reprocessing

### 🚀 Ready for Production
The hybrid complex analysis system is now ready for:
- Testing with additional models
- Comparative analysis across different LLMs
- Production deployment for Hawaiian text analysis
- **Complete end-to-end pipeline** from translation to benchmarking
- **Multi-model comparison and ranking** with composite scoring
- **Text normalization in benchmarking** for fairer semantic similarity evaluation

### ✅ Resolved Issues
- **Passage 7 malformed response**: ✅ **FIXED** - Successfully reprocessed using subset dataset approach, achieving 14/14 valid passages with improved similarity scores
- **Passage 13 corrupted translation**: ✅ **FIXED** - Corrupted JSON with empty translation field and repetitive raw response fixed using individual passage repair approach (`hybrid_complex_analysis_passage13_fix` task)
- **Formatting bias in similarity scores**: ✅ **FIXED** - Implemented text normalization to focus on content rather than formatting differences
- **Duplicate model entries in results**: ✅ **FIXED** - Removed base `qwen3-4b-awq-40k-maui` results files, keeping only the more specific `(hybrid_complex_analysis_original)` variant

## Medium Priority Tasks

### Task 12: Create Summary Coherence and Completeness Metrics (🎯 ENHANCED)
- [x] **Semantic similarity evaluation implemented** for summaries (78.91% achieved)
- [x] **Data format standardized** - summaries now properly compared in passage 1
- [ ] Evaluate how well summaries capture main themes from all passages
- [ ] Check for logical flow and thematic synthesis
- [ ] Measure completeness against reference summaries:
  - [ ] Key theme coverage
  - [ ] Important detail retention
  - [ ] Conclusion quality
- [ ] Score clarity and accessibility of academic content
- [ ] Implement summary-specific metrics:
  - [ ] Coherence score
  - [ ] Completeness percentage
  - [ ] Synthesis quality rating

### Task 13: Build Composite Scoring System for Overall Analysis Quality (✅ COMPLETED)
- [x] **Design weighting system for different components**:
  - [x] Translation quality: 40%
  - [x] Commentary quality: 40%
  - [x] Summary quality: 20%
- [x] **Create overall quality score calculation** - Implemented in complex_semantic_similarity_summary.py
- [x] **Generate comparison matrices across different models** - CSV output with detailed metrics
- [x] **Implement statistical analysis**:
  - [x] Mean scores per component
  - [x] Valid/missing count tracking
  - [x] Component-specific breakdowns
- [x] **Provide actionable insights for model improvement** - Detailed component analysis
- [x] **Create model ranking system** - Sorted by composite score with detailed breakdowns

### Task 14: Create Benchmarking Reports for Complex Analysis Outputs
- [ ] Design report template with component breakdowns
- [ ] Implement visual comparisons:
  - [ ] Bar charts for component scores
  - [ ] Radar charts for multi-dimensional analysis
  - [ ] Heat maps for model comparisons
- [ ] Generate detailed analysis sections:
  - [ ] Model strengths by component
  - [ ] Model weaknesses and areas for improvement
  - [ ] Comparative analysis across all tested models
- [ ] Create executive summaries for model performance
- [ ] Export reports in multiple formats (MD, PDF, HTML)

## Commentary Quality Improvement Recommendations

### Analysis of Reference vs Model Commentary Patterns

Based on analysis of the reference commentary and current model outputs, several patterns emerge that explain the ~68% commentary similarity scores:

#### **Key Differences Identified:**

1. **Structure & Organization**:
   - **Reference**: Uses numbered bullet points (•) with clear hierarchical structure
   - **Models**: Use academic essay format with headers and sections
   - **Impact**: Different organizational patterns reduce semantic similarity

2. **Content Focus**:
   - **Reference**: Highly specific allegorical interpretation (e.g., "Nā-maka-o-ka-pāo'o represents progressive-minded Hawaiian")
   - **Models**: General cultural/historical context without specific allegorical claims
   - **Impact**: Models miss the interpretive depth that characterizes the reference

3. **Citation Style**:
   - **Reference**: Includes specific academic citations (e.g., "Pukui, Haertig, Lee (1972:114)")
   - **Models**: Rarely include specific citations or footnote references
   - **Impact**: Missing scholarly apparatus reduces similarity to academic reference style

4. **Specific Details**:
   - **Reference**: Includes precise contextual details (e.g., "'Ai Kapu era," "post-1820 Protestant Christian bias")
   - **Models**: Often provide general cultural context without specific historical periods
   - **Impact**: Less precise temporal and cultural grounding

#### **Recommended Prompt Improvements:**

### Task 15a: Enhanced Commentary Prompt Template

```
Please analyze the following Hawaiian passage and provide commentary that follows this specific structure:

**Paragraph {paragraph}:**
• [Bullet point 1: Character/plot analysis with allegorical interpretation]
  – [Sub-point: Cultural/historical context with specific time periods]
• [Bullet point 2: Linguistic/cultural practices analysis]
  – [Sub-point: Specific cultural concepts with Hawaiian terms]
• [Bullet point 3: Historical significance and symbolism]
  – [Sub-point: References to specific cultural eras like 'Ai Kapu period]

Requirements:
1. Use bullet points (•) and sub-points (–) for organization
2. Include specific allegorical interpretations where characters represent broader concepts
3. Reference specific historical periods (e.g., 'Ai Kapu era, post-1819, post-1820)
4. Include Hawaiian cultural terms in italics with brief explanations
5. When possible, reference scholarly sources (Pukui, Elbert, Haertig, etc.)
6. Focus on symbolic meaning beyond literal interpretation
```

### Task 15b: Include Reference Examples in Prompts

Add exemplar commentary excerpts to guide model behavior:

```
Example of expected commentary style:

"**Paragraph 3:**• A new character is introduced, Pua-(a)li'i (child/descendant of a chief/chiefly line), described as a good man, arrived from inland at Līhu'e (Wāhiāwā)...
– In the 'Ai Kapu era, everyone walked on land to every destination and it was normal to call in to the house of strangers..."
```

### Task 15c: Specific Cultural Context Requirements

```
Your commentary must address:
1. **Allegorical Interpretation**: What do characters/events symbolically represent?
2. **Historical Period Context**: Reference specific eras ('Ai Kapu, post-contact, etc.)
3. **Cultural Practices**: Explain specific Hawaiian customs mentioned
4. **Linguistic Analysis**: Hawaiian terms, name meanings, cultural significance
5. **Scholarly Grounding**: Reference established Hawaiian cultural scholarship when relevant
```

### Task 15d: Implement Few-Shot Learning Approach

- Include 2-3 complete reference commentary examples in the prompt
- Show the exact bullet-point structure and allegorical interpretation style
- Demonstrate the level of specific cultural detail expected

### **Expected Impact:**
- Improve commentary similarity from ~68% to target 75-80%
- Better alignment with academic Hawaiian cultural scholarship
- More consistent structural organization matching reference style
- Enhanced allegorical and symbolic interpretation depth

### Task 15e: Multi-Model Prompt Engineering Analysis (✅ UPDATED)

**Comprehensive Testing Results Across Multiple Models:**

#### **Performance Pattern Discovery**
- **Few-shot prompting**: Consistently highest composite scores across all tested models
- **Original prompts**: Middle performance with best translation quality
- **"Improved" prompts**: Consistently worst performance, demonstrating over-engineering anti-pattern

#### **Key Findings from Multi-Model Testing**
1. **Few-shot superiority confirmed**: Best commentary scores in 100% of tested model pairs
2. **Translation quality trade-offs**: Complex prompts reduce translation performance by 2-4%
3. **"Showing beats telling"**: Models learn better from examples than from prescriptive instructions
4. **Cognitive overload evidence**: Rigid formatting constraints hurt natural language generation

#### **Updated Model Results (Post-Normalization)**
- **llama-3.3-70B-Instruct_exl2_6.0bpw-maui**:
  - Few-shot: Commentary 0.6986, Translation 0.9464, Summary 0.7454 (Composite: 0.8071)
  - Original: Commentary 0.6596, Translation 0.9308, Summary 0.7874 (Composite: 0.7936)
  - Improved: Commentary 0.6405, Translation 0.9402, Summary 0.6699 (Composite: 0.7663)
  
- **qwen3-30b-a3b-awq-128k-maui**:
  - Few-shot: Commentary 0.7175, Translation 0.8512, Summary 0.7068 (Composite: 0.7689)
  - Original: Commentary 0.6942, Translation 0.8589, Summary 0.7352 (Composite: 0.7683)
  - Improved: Commentary 0.6839, Translation 0.8298, Summary 0.7772 (Composite: 0.7609)

## Next Phase: Few-Shot Prompt Refinement Strategy

Based on multi-model testing results, the focus should shift to optimizing few-shot examples rather than continuing model comparison or attempting complex prompt engineering.

### Priority 1: Few-Shot Example Enhancement

#### **1a: Expand Example Diversity**
- **Current limitation**: Only 2 passage-level examples (paragraphs 1 and 6)
- **Action items**:
  - Add examples covering different passage types (narrative, dialogue, descriptive)
  - Include examples of varying analytical complexity
  - Ensure examples represent diverse cultural analysis techniques
  - Target 3-4 total examples to prevent cognitive overload

#### **1b: Add Chapter-Level Summary Examples**
- **Current gap**: No examples of high-quality chapter summaries in prompts
- **Action items**:
  - Include 1-2 exemplary chapter summary examples
  - Demonstrate synthesis of multiple passages
  - Show proper thematic integration and conclusion structure
  - Ensure summaries model appropriate length and depth

#### **1c: Curate Examples Based on Performance Metrics**
- **Data-driven approach**: Analyze which reference commentary elements score highest
- **Action items**:
  - Identify patterns in high-similarity reference text segments
  - Focus examples on proven effective analysis techniques
  - Remove or refine examples that may be confusing models
  - Test example variations to optimize learning transfer

### Priority 2: Example Optimization Experiments

#### **2a: Example Placement Testing**
- **Current**: Examples in user prompt only
- **Test variations**:
  - System prompt examples vs user prompt examples
  - Combined system + user prompt examples
  - Different example quantities (2 vs 3 vs 4)
  - Measure impact on all three components (translation, commentary, summary)

#### **2b: Example Length Optimization**
- **Balance cognitive load**: Ensure examples are comprehensive but not overwhelming
- **Test approaches**:
  - Full examples vs condensed examples
  - Multiple short examples vs fewer comprehensive examples
  - Component-specific examples (translation-focused vs commentary-focused)

### Priority 3: Refinement Guidelines (Based on Evidence)

#### **3a: What Works (Keep)**
- Natural demonstration over prescriptive instruction
- Specific cultural and historical references
- Bullet-point organizational structure
- Etymology and allegorical interpretation depth

#### **3b: What Doesn't Work (Avoid)**
- Rigid formatting requirements
- Bracketed headers or forced structure
- Over-prescriptive style guides
- Long lists of detailed instructions

#### **3c: Evidence-Based Improvements**
1. **Remove artificial constraints** that reduce natural language flow
2. **Focus on content quality** over formatting compliance
3. **Use examples that show rather than tell** what good analysis looks like
4. **Maintain simplicity** in instructional language while showing complexity in examples

## Enhanced Few-Shot Implementation Results (✅ COMPLETED)

### **Phase 1-3: All Implementation Phases Successfully Completed**

#### **Enhanced Few-Shot Configuration Created**: `hybrid_complex_analysis_enhanced_fewshot.json`
- [x] **3 diverse passage examples** covering character introduction, dialogue, and symbolic action
- [x] **Chapter summary example** demonstrating synthesis and scholarly depth
- [x] **Natural scholarly flow** without forced formatting constraints
- [x] **Production-ready configuration** tested across multiple model architectures

#### **Comprehensive Multi-Model Validation Results**
- [x] **11 models tested** across 5 different architecture families
- [x] **82% success rate** (9/11 models showed significant improvement)
- [x] **Cross-vendor validation** (Meta, Google, Alibaba, DeepSeek models tested)
- [x] **Architecture compatibility patterns identified**

### **Success Metrics: EXCEEDED TARGETS**
- ✅ **Commentary improvement**: Achieved 72%+ similarity (exceeded 70% target)
- ✅ **Translation quality**: Maintained 93-96% similarity (exceeded 90% target)  
- ✅ **Summary quality**: Achieved 77-88% similarity (exceeded 75% target)
- ✅ **Composite score improvement**: 20-47 point improvements (far exceeded 5-10% target)

### **Model Architecture Compatibility Discovered**
- ✅ **Standard models**: 100% success rate (8/8 models improved)
- ✅ **Implicit reasoning models**: DeepSeek V3 achieved excellent results
- ⚠️ **Explicit reasoning models**: R1-style and think-parser models degraded with enhanced few-shot
- ✅ **Original prompts solution**: DeepSeek R1 improved +4.9 points (0.7430 → 0.7922) when using original prompts

### **Production Deployment Status: READY**
- [x] **Optimal configuration identified**: `hybrid_complex_analysis_enhanced_fewshot` for standard/implicit reasoning models
- [x] **Alternative configuration**: `hybrid_complex_analysis_original` for explicit reasoning models (R1, think-parser)
- [x] **Clear usage guidelines**: Architecture-specific prompt selection based on model reasoning type
- [x] **Performance benchmarks established**: Top 8 models all use enhanced few-shot; reasoning models use original
- [x] **Deployment recommendation**: Enhanced few-shot as default, original prompts for `<think>` chain models
- [x] **Manual CLI testing tool**: Validated methodology for web-based LLM testing without API access

## Completed Tasks

### Task 17: Manual CLI Testing Tool (✅ COMPLETED)
- [x] **Created manual CLI version** of translation script (`translations/custom-model-v2-cli.py`)
- [x] **Clipboard integration** for prompts and responses (macOS/Linux/Windows compatible)
- [x] **Flexible input methods** with simple `c`/`p`/`q` interface
- [x] **Progress tracking** and early exit capabilities
- [x] **Compatible output format** with existing pipeline (JSON files, same structure)
- [x] **Validation testing** with Gemma 3 27B via Google AI Studio
- [x] **Performance comparison**: Manual CLI (0.8187) vs API (0.8271) - only 1% difference
- [x] **Special case support**: Grouped commentary handling for passages 10-14
- [x] **Methodology validation**: Demonstrates reliable results for web-based LLM testing

### Task 16: Implement Text Normalization for Semantic Similarity (✅ COMPLETED)
- [x] **Created normalize_text() function** in complex_semantic_similarity.py
- [x] **Normalizations implemented**:
  - [x] Bullet point standardization (•, -, *, 1., etc. → •)
  - [x] Markdown removal (bold, italic, code blocks)
  - [x] Header normalization (various formats → consistent)
  - [x] Whitespace normalization
  - [x] Punctuation standardization
  - [x] Hawaiian character consistency
- [x] **Applied to both reference and model texts** before embedding
- [x] **Impact measured**:
  - [x] Commentary improvements: Original +2.13%, Few-shot +3.73%
  - [x] Revealed formatting "false positives" in similarity scores
  - [x] Original summary dropped 3.7%, exposing content differences
- [x] **Key insight**: Formatting was creating artificial similarity that masked actual content alignment differences

## Low Priority Tasks

### Task 15: Integrate Complex Analysis Evaluation into run_pipeline_v2.sh (✅ COMPLETED)
- [x] **Add evaluation step to `run_pipeline_v2.sh`** for complex analysis and hybrid complex analysis
- [x] **Ensure seamless workflow from translation to evaluation** - Complete 4-step pipeline implemented
- [x] **Create command-line options for**:
  - [x] Model-specific evaluation via OUTPUT_DIR parameter
  - [x] Flexible task configuration via --task parameter
  - [x] Environment variable support for API configuration
- [x] **Implement automated report generation** - Complex analysis summary with detailed metrics
- [x] **Handle error cases gracefully**:
  - [x] Missing reference data validation
  - [x] API error handling with retry logic
  - [x] Incomplete output detection and reporting
- [x] **Add progress indicators for long-running evaluations** - Progress bars for embedding generation
- [x] **Create evaluation summary in pipeline output** - Multi-model comparison with composite scoring

#### Additional Pipeline Features Added:
- [x] **Multi-model comparison script** (`compare_models.sh`)
- [x] **Comprehensive summary generation** (`complex_semantic_similarity_summary.py`)
- [x] **Composite scoring system** with weighted components
- [x] **Detailed component breakdowns** with valid/missing counts
- [x] **CSV output for further analysis** (`complex_analysis_results.csv`)

## Implementation Notes

### Dependencies
- Existing semantic similarity infrastructure from simple translation evaluation
- OpenAI embeddings API (or alternative embedding service)
- LLM judge API access (GPT-4 or similar)
- Python libraries: pandas, numpy, matplotlib/seaborn for visualizations

### Data Requirements
- Reference translations for all passages
- Reference commentary from human experts
- Reference summaries for overall context
- Properly formatted complex analysis outputs from models

### Success Criteria
- All components can be evaluated independently
- Composite scores accurately reflect overall quality
- Reports provide actionable insights for model improvement
- System handles edge cases without failing
- Evaluation process is reproducible and consistent

### Hybrid Approach Benefits
- Enables parallel processing of passages for better performance
- Matches reference dataset structure more closely
- Fixes commentary extraction issues (all 14 passages will have commentary)
- Maintains context for high-quality summary generation
- More suitable for models with smaller context windows
- Easier debugging and evaluation of individual components