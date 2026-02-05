# USENIX Artifact: LLMVul Experiments

This repository contains the datasets, model metadata, scripts, and outputs for all experiments reported in the paper. It is provided as the USENIX artifact so results can be inspected without rerunning the full pipeline.

## Repository layout
- `000_original_datasets/` - source datasets (JSON)
- `001_ground_truth_datasets/` - ground-truth function labels (JSON)
- `002_model_infos/` - model metadata and settings used in experiments
- `100_*` to `103_*` - Java zero-shot experiments (with/without assumptions and formatting)
- `110_*` to `113_*` - C/C++ zero-shot experiments (with/without assumptions and formatting)
- `201_nanf_java_code_struct/` - Java experiments focused on code structure
- `202_nanf_java_data_flow/` - Java experiments focused on data flow
- `203_nanf_java_control_flow/` - Java experiments focused on control flow
- `204_nanf_java_cross_script/` - Java experiments focused on cross-script analysis
- `llmvul.yml` - conda environment used by the scripts

## Typical experiment folder layout
Most experiment folders are organized into numbered stages:
- `01_initial_src/` - scripts for initial LLM analysis
- `02_initial_results/` - raw model outputs (JSON)
- `03_relevance_analyze_llm_src/` - scripts for relevance analysis
- `04_relevant_analysis_results/` - relevance outputs (JSON)
- `05_src_relevance_web_processing/` - web processing helpers
- `06_relevant_analysis_final_results/` - finalized relevance outputs
- `07_function_analyze_llm_src/` - scripts for function-level analysis
- `08_function_analysis_results/` - function analysis outputs
- `09_src_function_analysis_ui/` - UI tooling for review
- `10_function_results/` - final outputs

Note: not every experiment contains every stage. See each folder for its exact contents.

## Environment (optional)
If you want to rerun scripts locally, create the conda environment:

```bash
conda env create -f llmvul.yml
conda activate llmvul
```

Some scripts use Ollama and expect specific model names; check the scripts and `002_model_infos/` when rerunning.

## Notes
- This artifact is data-heavy; outputs are already included in the results folders.
- Model-specific outputs are typically named with the model identifier for traceability.
