# PsiloCouples — Music-Evoked Neural Synchrony Analysis

EEG analysis and task scripts for a **double-blind, randomised psilocybin study** conducted at the **Universidad de Buenos Aires**, examining music-evoked neural synchrony using **phase-locking value (PLV)** and **inter-subject correlation (ISC)**. Findings presented at IDPAT conference, Dublin, October 2025.

## Study Overview

|                           |                                                                                         |
| ------------------------- | --------------------------------------------------------------------------------------- |
| **Design**                | Double-blind, randomised, within-subject                                                |
| **Participants**          | N = 20                                                                                  |
| **Primary analyses**      | Phase-locking value (PLV) and inter-subject correlation (ISC)                           |
| **Statistical modelling** | Linear mixed-effects models                                                             |
| **Presentation**          | Irish Doctors for Psychedelic Assisted Therapy (IDPAT) conference, Dublin, October 2025 |

### Tasks

* **Individual music listening** with subjective ratings
* **Synchronised shared music listening** across two participants
* **Prisoner's dilemma task** — piloted but not included in the final analysis

## Requirements

* **MATLAB R2025a** or later
* **Statistics and Machine Learning Toolbox** (`fitlme`)
* **Python 3.9** or later
* Python packages:

  * `psychopy`
  * `pylsl`
  * `pandas`
  * `openpyxl`
  * `matplotlib`
  * `pyserial`

## Configuration

The analysis scripts expect a `config.m` file in the same folder.

1. Copy `config_template.m` to `config.m`.
2. Edit the two paths inside `config.m`:

| Variable          | Description                                                     |
| ----------------- | --------------------------------------------------------------- |
| `config.data_dir` | Folder containing the input CSV files                           |
| `config.out_dir`  | Folder for outputs. Created automatically if it does not exist. |

### Task Script Configuration

The task scripts (`Music_Task_*` and `PrisonersDilemma_Jitter.py`) contain an **`EDIT ONLY THESE`** block at the top of each file.

These sections contain the configuration for:

* Audio directory
* Song filenames
* Results directory
* Server IP

> **Audio files are not redistributed with this repository.** Users must supply their own audio files with the same filenames, or edit the `SONGS` dictionaries accordingly.

## Analysis Scripts

| File                        | Description                                                                                                                                                                                                                                                                                                                            |
| --------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `PLV_Individual_Task_LMM.m` | Loads individual-task PLV data, cleans and z-scores the data, fits linear mixed-effects models using both z-scored and raw PLV, compares models, generates diagnostics, and produces a manuscript-style summary.                                                                                                                       |
| `ISC_Analysis.m`            | Loads synchronised-task ISC data, fits linear mixed-effects models with increasing random-effects structure, compares models using AIC/BIC and likelihood-ratio tests, and exports summary tables and figures. ISC values were computed using all-versus-all participant pairing because per-pair data loss reduced the usable sample. |

## Task Scripts

| File                          | Description                                                                                                                                                                     |
| ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `Music_Task_Individual.py`    | Presentation script for the individual music-listening task. Plays five music tracks and collects five subjective ratings after each track.                                     |
| `Music_Task_Shared_Server.py` | Server-side script for the synchronised shared music-listening task. Plays audio on the server and sends `START`/`END` messages to the client over TCP.                         |
| `Music_Task_Shared_Client.py` | Client-side script for the synchronised shared music-listening task. Receives `START`/`END` messages from the server and pushes matching LSL markers.                           |
| `PrisonersDilemma_Jitter.py`  | Prisoner's dilemma task with jitter analysis. Piloted but not included in the final analysis because of movement artefact and session-order effects. Included for completeness. |

## Input Data Formats

### `PLV_results_merged.csv`

Required columns:

```text
participant
session
song_PLV_summary_table
question
rating
plv_restsub
dose
ollen
```

### `ISC_merged_dose.csv`

Required columns:

```text
ISC_global
Dose
Song
P1
P2
```

## Outputs

### PLV Analysis

Running `PLV_Individual_Task_LMM.m` produces:

* Cleaned datasets:

  * `PLV_Involucramiento_*_clean.csv`
* Fitted model workspace:

  * `PLV_models_workspace.mat`
* Fixed-effects tables for z-scored and raw PLV models
* Comparison CSV of the PLV term across models
* Manuscript-style summary:

  * `PLV_LMM_manuscript_summary.txt`
* Diagnostic figure:

  * `PLV_LMM_complete_results.png`
* Per-song × dose predicted means

### ISC Analysis

Running `ISC_Analysis.m` produces:

* Model comparison table:

  * `ISC_Model_Comparison.csv`
* Raw data subset:

  * `ISC_Raw_Subset.csv`
* Model workspace:

  * `ISC_LMM_Workspace.mat`
* Figures:

  * `ISC_Analysis_Complete_Figure.png`
  * `ISC_Individual_Effects.png`
* Detailed text summary:

  * `ISC_Analysis_Summary.txt`

## Setup

1. **Clone the repository.**
2. Copy `config_template.m` to `config.m`.
3. Edit `config.m` with your local data and output paths.
4. For the task scripts, edit the **`EDIT ONLY THESE`** block at the top of each file.
5. Ensure the required Python packages are installed.
6. Run the analysis scripts in MATLAB.

## Notes

* The **Prisoner's dilemma task** was piloted but not included in the final analysis because of movement artefact and session-order effects.
* **ISC values were computed using all-versus-all participant pairing** because per-pair data loss reduced the usable sample.
* **Audio files are not redistributed** with this repository.

## License

This project is licensed under the **MIT License**.
