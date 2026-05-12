%% ISC Analysis — Linear Mixed Models with All-versus-All Pairing
% Due to data loss (only 19 usable within-dyad pairs), this analysis pivoted
% to an all-versus-all pairwise approach across participants within each dose condition.
%
% Usage:
%   1. Copy config_template.m to config.m and edit paths
%   2. Run this script

clear; clc;
run('config.m');

infile = fullfile(config.data_dir, 'ISC_merged_dose.csv');
outdir = config.out_dir;
if ~exist(outdir,'dir'), mkdir(outdir); end

fprintf('Loading and fixing data...\n');

%% ========= Load and fix data =========
T = readtable(infile);
if height(T) == 0, error('Loaded table is empty'); end

T.Song    = categorical(string(T.Song));
T.P1_file = string(T.P1_file);
T.P2_file = string(T.P2_file);
T.Status  = string(T.Status);
T.P1      = categorical(T.P1);
T.P2      = categorical(T.P2);

% Dose conversion
if ~isnumeric(T.Dose)
    d = lower(strtrim(string(T.Dose)));
    dose_num = nan(height(T),1);
    dose_num(d=="1")    = 1;
    dose_num(d=="0")    = 0;
    dose_num(d=="alta") = 1;
    dose_num(d=="baja") = 0;
    mask = isnan(dose_num);
    if any(mask)
        tmp = str2double(d(mask));
        dose_num(mask) = tmp;
    end
    T.Dose = double(dose_num);
end

if numel(unique(T.Dose)) == 1
    u = unique(T.Dose);
    error('All doses are identical (only %g present)', u(1));
end
if any(isnan(T.ISC_global))
    warning('%d NaN values in ISC_global - will be excluded', sum(isnan(T.ISC_global)));
end

%% ========= Fit models =========
fprintf('Fitting models...\n');
models      = cell(4,1);
model_names = {'Dose_Only'; 'Dose_Song'; 'Dose_Participants'; 'Full_Model'};

models{1} = fitlme(T, 'ISC_global ~ Dose');
models{2} = fitlme(T, 'ISC_global ~ Dose + (1|Song)');
models{3} = fitlme(T, 'ISC_global ~ Dose + (1|P1) + (1|P2)');
models{4} = fitlme(T, 'ISC_global ~ Dose + (1|P1) + (1|P2) + (1|Song)');

%% ========= Model comparison =========
AIC    = cellfun(@(m) m.ModelCriterion.AIC, models);
BIC    = cellfun(@(m) m.ModelCriterion.BIC, models);
LogLik = cellfun(@(m) m.LogLikelihood, models);

[~, best_idx] = min(AIC);
best_model = models{best_idx};

%% ========= Extract dose effects =========
Dose_Estimate = nan(4,1);
Dose_CI_Lower = nan(4,1);
Dose_CI_Upper = nan(4,1);
Dose_pValue   = nan(4,1);

for i = 1:4
    idx = strcmp(models{i}.CoefficientNames, 'Dose');
    if any(idx)
        Dose_Estimate(i) = models{i}.Coefficients.Estimate(idx);
        Dose_pValue(i)   = models{i}.Coefficients.pValue(idx);
        ci = coefCI(models{i});
        Dose_CI_Lower(i) = ci(idx,1);
        Dose_CI_Upper(i) = ci(idx,2);
    end
end

%% ========= Cohen's d (FIXED: no file handle conflict) =========
mean_low  = mean(T.ISC_global(T.Dose==0), 'omitnan');
mean_high = mean(T.ISC_global(T.Dose==1), 'omitnan');
sd_low    = std(T.ISC_global(T.Dose==0), 'omitnan');
sd_high   = std(T.ISC_global(T.Dose==1), 'omitnan');
n_low     = sum(T.Dose==0 & ~isnan(T.ISC_global));
n_high    = sum(T.Dose==1 & ~isnan(T.ISC_global));

sd_pooled = sqrt(((n_low-1)*sd_low^2 + (n_high-1)*sd_high^2) / (n_low + n_high - 2));
cohens_d = (mean_high - mean_low) / sd_pooled;

if abs(cohens_d) < 0.2,   d_interpret = 'negligible';
elseif abs(cohens_d) < 0.5, d_interpret = 'small-to-moderate';
elseif abs(cohens_d) < 0.8, d_interpret = 'moderate';
else, d_interpret = 'large';
end

fprintf('Cohen''s d = %.3f (%s effect)\n', cohens_d, d_interpret);

%% ========= Save outputs =========
ComparisonTbl = table( ...
    string(model_names), AIC(:), BIC(:), LogLik(:), ...
    Dose_Estimate(:), Dose_CI_Lower(:), Dose_CI_Upper(:), Dose_pValue(:), ...
    'VariableNames', {'Model','AIC','BIC','LogLik','Dose_Beta','Dose_CI_L','Dose_CI_U','Dose_p'});
ComparisonTbl.BestModel = (1:4)' == best_idx;

writetable(ComparisonTbl, fullfile(outdir, 'ISC_Model_Comparison.csv'));
fprintf('Saved: ISC_Model_Comparison.csv\n');

%% ========= Summary file (no file handle conflict) =========
summaryFile = fullfile(outdir, 'ISC_Analysis_Summary.txt');
fid = fopen(summaryFile, 'w');
fprintf(fid, 'ISC Analysis Summary\n');
fprintf(fid, 'Best model by AIC: %s\n', model_names{best_idx});
fprintf(fid, 'Dose effect (High vs Low): β = %.4f, 95%% CI [%.4f, %.4f], p = %.4g\n', ...
    Dose_Estimate(best_idx), Dose_CI_Lower(best_idx), Dose_CI_Upper(best_idx), Dose_pValue(best_idx));
fprintf(fid, 'Cohen''s d = %.3f (%s effect)\n', cohens_d, d_interpret);
fprintf(fid, 'Interpretation: The dose effect is %s, indicating that ISC differs between dose conditions.\n', ...
    ternary(Dose_pValue(best_idx) < 0.05, 'statistically significant', 'not statistically significant'));
fprintf(fid, 'Note: All-versus-all pairing used; within-dyad ISC was not feasible due to data loss.\n');
fclose(fid);
fprintf('Saved summary to: %s\n', summaryFile);

%% ========= Figures =========
% (Your original figure code from ISC_Analysis.m can be copied here;
%  it does not contain hardcoded paths.)

fprintf('=== COMPLETE ===\n');

function str = ternary(cond, trueStr, falseStr)
    if cond, str = trueStr; else, str = falseStr; end
end