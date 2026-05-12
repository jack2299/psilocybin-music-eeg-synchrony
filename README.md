# Psilocouples-ISC-PLV-Music-Perception-Task-and-Analysis-plus-Prisoner-s-Dilemma

EEG analysis scripts for a double-blind, randomised psilocybin study examining music-evoked neural synchrony (PLV) and inter-subject correlation (ISC).

## Scripts

| File | Description |
| :--- | :--- |
| `config_template.m` | Configuration template. Copy to `config.m` and edit paths. |
| `PLV_Individual_Task_LMM.m` | Loads PLV data, fits linear mixed-effects models (z-scored and raw PLV), compares models, generates diagnostics. |
| `ISC_Analysis.m` | Loads ISC data, fits LMMs with increasing random effects, compares models via AIC/BIC/LRT. Note: All-versus-all pairing used due to data loss. |

## Setup

1. Clone this repository
2. Copy `config_template.m` to `config.m`
3. Edit `config.m` to point to your local data and output directories
4. Run the scripts in MATLAB

## Requirements

- MATLAB R2025a or later
- Statistics and Machine Learning Toolbox (for `fitlme`)

## Data Format

### PLV_results_merged.csv
Must contain columns: `participant`, `session`, `song_PLV_summary_table`, `question`, `rating`, `plv_restsub`, `dose`, `ollen`

### ISC_merged_dose.csv
Must contain columns: `ISC_global`, `Dose`, `Song`, `P1`, `P2`

## License

MIT
