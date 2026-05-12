%% CONFIGURATION FILE - Buenos Aires Neuroscience Project
% Copy this file to 'config.m' and edit the paths to match your local setup.
% Do NOT commit 'config.m' to GitHub (add it to .gitignore).

% Data directory (where your CSV files live)
config.data_dir = '/path/to/your/data/folder';

% Output directory (where results will be saved)
config.out_dir = fullfile(config.data_dir, 'analysis_outputs');

% Optional: LMM settings
config.lmm.df_method = 'Satterthwaite';   % or 'Residual'
config.lmm.alpha = 0.05;                   % significance level

% Optional: figure settings
config.figures.format = 'png';              % 'png', 'svg', 'both'
config.figures.dpi = 300;                  % resolution for raster figures