Psilocouples — Music-Evoked Neural Synchrony Analysis
EEG analysis and task scripts for a double-blind, randomised psilocybin study conducted at Universidad de Buenos Aires, examining music-evoked neural synchrony using phase-locking value (PLV) and inter-subject correlation (ISC).

Study overview
Design: double-blind, randomised, within-subject

N: 20 participants

Tasks:

Individual music listening with subjective ratings

Synchronised shared music listening across two participants

Prisoner’s dilemma task (piloted but not included in the final analysis)

Primary analyses: PLV and ISC, fitted with linear mixed-effects models

Presentation: Irish Doctors for Psychedelic Assisted Therapy (IDPAT) conference, Dublin, October 2025

Requirements
MATLAB R2025a or later

Statistics and Machine Learning Toolbox (fitlme)

Python 3.9 or later (for task scripts)

Python packages: psychopy, pylsl, pandas, openpyxl, matplotlib, pyserial

Configuration
The analysis scripts expect a config.m in the same folder. Copy config_template.m to config.m and edit the two paths inside it:

config.data_dir — folder containing the input CSV files

config.out_dir — folder for outputs (created automatically if it doesn’t exist)

The task scripts (Music_Task_*, PrisonersDilemma_Jitter.py) have their own EDIT ONLY THESE block at the top for the audio directory, song filenames, results directory, and server IP.

Audio files are not redistributed. Users must supply their own audio files with the same filenames, or edit the SONGS dictionaries accordingly.

Analysis scripts
File	Description
PLV_Individual_Task_LMM.m	Loads individual-task PLV data, cleans and z-scores, fits linear mixed-effects models (z-scored and raw PLV), compares models, generates diagnostics and a manuscript-style summary.
ISC_Analysis.m	Loads synchronised-task ISC data, fits LMMs with increasing random-effects structure, compares models via AIC/BIC and likelihood ratio tests, and exports summary tables and figures. ISC values were computed using all-versus-all participant pairing because per-pair data loss reduced the usable sample.
Task scripts
File	Description
Music_Task_Individual.py	Presentation script for the individual music listening task. Plays five music tracks and collects five subjective ratings after each.
Music_Task_Shared_Server.py	Server-side script for the synchronised shared music listening task. Plays audio on the server and sends START/END messages to the client over TCP.
Music_Task_Shared_Client.py	Client-side script for the synchronised shared music listening task. Receives START/END messages from the server and pushes matching LSL markers.
PrisonersDilemma_Jitter.py	Prisoner’s dilemma task with jitter analysis. Piloted but not included in the final analysis because of movement artefact and session-order effects. Included here for completeness.
Input data formats
PLV_results_merged.csv
Required columns: participant, session, song_PLV_summary_table, question, rating, plv_restsub, dose, ollen.

ISC_merged_dose.csv
Required columns: ISC_global, Dose, Song, P1, P2.

Outputs
Running PLV_Individual_Task_LMM.m produces:

Cleaned datasets (PLV_Involucramiento_*_clean.csv)

Fitted model workspace (PLV_models_workspace.mat)

Fixed-effects tables for z-scored and raw PLV models

Comparison CSV of the PLV term across models

Manuscript-style summary (PLV_LMM_manuscript_summary.txt)

Diagnostic figure (PLV_LMM_complete_results.png)

Per-song × dose predicted means

Running ISC_Analysis.m produces:

Model comparison table (ISC_Model_Comparison.csv)

Raw data subset (ISC_Raw_Subset.csv)

Workspace (ISC_LMM_Workspace.mat)

Figures (ISC_Analysis_Complete_Figure.png, ISC_Individual_Effects.png)

Detailed text summary (ISC_Analysis_Summary.txt)

Setup
Clone the repository.

Copy config_template.m to config.m.

Edit config.m with your local data and output paths.

For task scripts, edit the EDIT ONLY THESE block at the top of each file.

Run the analysis scripts in MATLAB.

Notes
The prisoner’s dilemma task was piloted but not included in the final analysis because of movement artefact and session-order effects.

ISC values were computed using all-versus-all participant pairing because per-pair data loss reduced the usable sample.

Audio files are not redistributed with this repository.

License
MIT
