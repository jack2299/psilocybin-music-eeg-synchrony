%% ISC_Analysis.m
% =========================================================================
% Linear mixed-effects models for the shared (synchronised) music task.
% Part of a double-blind, randomised psilocybin EEG study conducted at
% Universidad de Buenos Aires. All-versus-all pairing
%
% Models:
%   Model 1: ISC ~ Dose
%   Model 2: ISC ~ Dose + (1|Song)
%   Model 3: ISC ~ Dose + (1|P1) + (1|P2)
%   Model 4: ISC ~ Dose + (1|P1) + (1|P2) + (1|Song)
%
% Requires:
%   - MATLAB with Statistics and Machine Learning Toolbox (fitlme)
%   - config.m in the same folder (copy of config_template.m)
%
% Input:
%   - ISC_merged_dose.csv in config.data_dir
%
% Outputs saved to config.out_dir:
%   - Model comparison table
%   - Raw data subset
%   - Workspace with all models and data
%   - Text summary
%   - Figures
% =========================================================================

clear; clc;

%% ========= Configuration =========
if ~exist('config.m', 'file')
    error(['config.m not found. Copy config_template.m to config.m ' ...
           'and edit the paths inside it before running this script.']);
end
run('config.m');

basedir = config.data_dir;
outdir  = config.out_dir;
if ~exist(outdir, 'dir'), mkdir(outdir); end
infile  = fullfile(basedir, 'ISC_merged_dose.csv');

%% Version check and compatibility setup
if verLessThan('matlab', '8.5')
    warning('Using legacy MATLAB version (%s) - some features limited', version);
    legacyMode = true;
else
    legacyMode = false;
end

% Color definitions for consistent plotting
blue_color = [0 0.447 0.741];
red_color  = [1 0 0];

%% === Load and fix data ===
fprintf('Loading and fixing data...\n');
try
    T = readtable(infile);

    if height(T) == 0
        error('Loaded table is empty');
    end

    T.Song    = categorical(string(T.Song));
    T.P1_file = string(T.P1_file);
    T.P2_file = string(T.P2_file);
    T.Status  = string(T.Status);
    T.P1      = categorical(T.P1);
    T.P2      = categorical(T.P2);

    if ~isnumeric(T.Dose)
        d = lower(strtrim(string(T.Dose)));
        dose_num = nan(height(T), 1);
        dose_num(d == "1")    = 1;
        dose_num(d == "0")    = 0;
        dose_num(d == "alta") = 1;
        dose_num(d == "baja") = 0;
        mask = isnan(dose_num);
        if any(mask)
            tmp = str2double(d(mask));
            if any(isnan(tmp))
                warning('%d dose values could not be converted', sum(isnan(tmp)));
            end
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
catch ME
    error('Data loading failed: %s', ME.message);
end

%% === Fit models ===
fprintf('Fitting models...\n');

models      = cell(4, 1);
model_names = {'Dose_Only'; 'Dose_Song'; 'Dose_Participants'; 'Full_Model'};

try
    models{1} = fitlme(T, 'ISC_global ~ Dose');
    models{2} = fitlme(T, 'ISC_global ~ Dose + (1|Song)');
    models{3} = fitlme(T, 'ISC_global ~ Dose + (1|P1) + (1|P2)');
    models{4} = fitlme(T, 'ISC_global ~ Dose + (1|P1) + (1|P2) + (1|Song)');

    for m = 1:numel(models)
        try
            convOK = true;
            if isprop(models{m}, 'Converged')
                convOK = models{m}.Converged;
            elseif isprop(models{m}, 'Diagnostics') && isstruct(models{m}.Diagnostics) ...
                    && isfield(models{m}.Diagnostics, 'ConvergenceStatus')
                convOK = (models{m}.Diagnostics.ConvergenceStatus == 0);
            end
            if ~convOK
                warning('Model %s may not have converged.', model_names{m});
            end
        catch
        end
    end
catch ME
    error('Model fitting failed: %s', ME.message);
end

%% === Model comparison ===
AIC    = cellfun(@(m) m.ModelCriterion.AIC, models);
BIC    = cellfun(@(m) m.ModelCriterion.BIC, models);
LogLik = cellfun(@(m) m.LogLikelihood, models);

fprintf('Performing likelihood ratio tests...\n');
LRT_results = cell(3, 1);
try
    try
        lrt1 = compare(models{1}, models{2});
    catch
        lrt1 = compare(models{1}, models{2}, 'CheckNesting', false);
    end
    LRT_results{1} = sprintf('Dose vs Dose+Song: LRT=%.3f, p=%.4f', lrt1.LRStat(2), lrt1.pValue(2));

    try
        lrt2 = compare(models{1}, models{3});
    catch
        lrt2 = compare(models{1}, models{3}, 'CheckNesting', false);
    end
    LRT_results{2} = sprintf('Dose vs Dose+Participants: LRT=%.3f, p=%.4f', lrt2.LRStat(2), lrt2.pValue(2));

    try
        lrt3 = compare(models{3}, models{4});
    catch
        lrt3 = compare(models{3}, models{4}, 'CheckNesting', false);
    end
    LRT_results{3} = sprintf('Dose+Participants vs Full: LRT=%.3f, p=%.4f', lrt3.LRStat(2), lrt3.pValue(2));
catch ME
    LRT_results{1} = sprintf('Likelihood ratio tests failed: %s', ME.message);
end

Dose_pValue   = nan(numel(models), 1);
Dose_Estimate = nan(numel(models), 1);
Dose_CI_Lower = nan(numel(models), 1);
Dose_CI_Upper = nan(numel(models), 1);

for i = 1:numel(models)
    try
        idx = strcmp(models{i}.CoefficientNames, 'Dose');
        if any(idx)
            Dose_pValue(i)   = models{i}.Coefficients.pValue(idx);
            Dose_Estimate(i) = models{i}.Coefficients.Estimate(idx);
            ci = coefCI(models{i});
            Dose_CI_Lower(i) = ci(idx, 1);
            Dose_CI_Upper(i) = ci(idx, 2);
        end
    catch
        warning('Could not extract dose effects for model %d', i);
    end
end

[~, best_idx] = min(AIC);
best_model = models{best_idx};

%% === Effect size (Cohen's d) ===
try
    mean_low  = mean(T.ISC_global(T.Dose == 0), 'omitnan');
    mean_high = mean(T.ISC_global(T.Dose == 1), 'omitnan');
    sd_low    = std(T.ISC_global(T.Dose == 0), 'omitnan');
    sd_high   = std(T.ISC_global(T.Dose == 1), 'omitnan');
    n_low     = sum(T.Dose == 0 & ~isnan(T.ISC_global));
    n_high    = sum(T.Dose == 1 & ~isnan(T.ISC_global));

    sd_pooled = sqrt(((n_low - 1) * sd_low^2 + (n_high - 1) * sd_high^2) / ...
                     (n_low + n_high - 2));

    cohens_d = (mean_high - mean_low) / sd_pooled;

    if abs(cohens_d) < 0.2
        d_interpret = 'negligible';
    elseif abs(cohens_d) < 0.5
        d_interpret = 'small-to-moderate';
    elseif abs(cohens_d) < 0.8
        d_interpret = 'moderate';
    else
        d_interpret = 'large';
    end

    fprintf('Cohen''s d = %.3f (%s effect)\n', cohens_d, d_interpret);
catch ME
    warning('Could not calculate effect size: %s', ME.message);
    cohens_d = NaN;
    d_interpret = 'undefined';
end

%% === Publication-quality figures ===
fprintf('Creating figures...\n');

fig1 = figure('Position', [100, 100, 1200, 800]);

% Panel A: Boxplot
subplot(2, 3, 1)
boxplot(T.ISC_global, T.Dose);
dose_levels = unique(T.Dose(~isnan(T.Dose)));
set(gca, 'XTick', 1:numel(dose_levels));
if all(ismember(dose_levels, [0 1]))
    lbls = cell(size(dose_levels));
    for k = 1:numel(dose_levels)
        if dose_levels(k) == 0
            lbls{k} = 'Low Dose';
        elseif dose_levels(k) == 1
            lbls{k} = 'High Dose';
        else
            lbls{k} = sprintf('Dose %.3g', dose_levels(k));
        end
    end
else
    lbls = arrayfun(@(v) sprintf('Dose %.3g', v), dose_levels, 'UniformOutput', false);
end
set(gca, 'XTickLabel', lbls);
ylabel('ISC Global');
title('A) ISC by Dose (Box Plot)');
grid on;

% Panel B: Scatter + means
subplot(2, 3, 2)
dose_jitter = T.Dose + 0.1 * randn(height(T), 1);
scatter(dose_jitter, T.ISC_global, 50, ...
    'MarkerFaceColor', blue_color, ...
    'MarkerFaceAlpha', 0.6, 'MarkerEdgeAlpha', 0.6, ...
    'DisplayName', 'Individual ISC');
hold on;
mean_low  = mean(T.ISC_global(T.Dose == 0), 'omitnan');
mean_high = mean(T.ISC_global(T.Dose == 1), 'omitnan');
plot([0, 1], [mean_low, mean_high], 'Color', red_color, 'LineWidth', 3, ...
    'DisplayName', 'Mean ISC');
scatter([0, 1], [mean_low, mean_high], 100, ...
    'MarkerFaceColor', red_color, ...
    'MarkerFaceAlpha', 1, 'MarkerEdgeAlpha', 1);
xlim([-0.5, 1.5]);
xlabel('Dose (0=Low, 1=High)');
ylabel('ISC Global');
title('B) ISC vs Dose (Scatter + Means)');
legend show; legend('Location', 'best');
grid on;

% Panel C: AIC
subplot(2, 3, 3)
bar(AIC);
set(gca, 'XTickLabel', {'Dose Only', 'Dose+Song', 'Dose+Participants', 'Full Model'});
ylabel('AIC (lower = better)');
title('C) Model Comparison (AIC)');
xtickangle(45);
grid on;

% Panel D: Dose effects
subplot(2, 3, 4)
err_lo = Dose_Estimate - Dose_CI_Lower;
err_hi = Dose_CI_Upper - Dose_Estimate;
errorbar(1:4, Dose_Estimate, err_lo, err_hi, 'o-', ...
    'Color', blue_color, 'LineWidth', 2);
set(gca, 'XTickLabel', {'Dose Only', 'Dose+Song', 'Dose+Participants', 'Full Model'});
ylabel('Dose Effect (\beta)');
title('D) Dose Effect Across Models');
xtickangle(45);
yline(0, '--k', 'LineWidth', 1.5);
grid on;

% Panel E: Residuals vs Fitted
subplot(2, 3, 5)
fitted_vals = fitted(best_model);
residuals   = best_model.Residuals.Raw;
scatter(fitted_vals, residuals, 50, ...
    'MarkerFaceColor', blue_color, ...
    'MarkerFaceAlpha', 0.6, 'MarkerEdgeAlpha', 0.6);
xlabel('Fitted Values');
ylabel('Residuals');
title('E) Residuals vs Fitted (Best Model)');
yline(0, '--k', 'LineWidth', 1.5);
grid on;

% Panel F: QQ plot
subplot(2, 3, 6)
qqplot(residuals);
title('F) Q-Q Plot of Residuals');
grid on;

sgtitle('Psilocybin ISC Analysis - Complete Results', 'FontSize', 16, 'FontWeight', 'bold');
try
    saveas(fig1, fullfile(outdir, 'ISC_Analysis_Complete_Figure.png'), 'png');
    saveas(fig1, fullfile(outdir, 'ISC_Analysis_Complete_Figure.fig'), 'fig');
catch ME
    fprintf('Could not save main figure: %s\n', ME.message);
end

%% === Figure 2: Individual random effects ===
if best_idx > 2
    fig2 = figure('Position', [200, 200, 1000, 600]);
    try
        tblRE = [];
        try
            tblRE = randomEffects(best_model);
            isTableRE = istable(tblRE);
        catch
            isTableRE = false;
        end

        if isTableRE
            P1_mask   = ismember(tblRE.Group, {'P1', 'P1:Identity', 'P1_Group', 'P1 (Intercept)'});
            P2_mask   = ismember(tblRE.Group, {'P2', 'P2:Identity', 'P2_Group', 'P2 (Intercept)'});
            Song_mask = ismember(tblRE.Group, {'Song', 'Song:Identity', 'Song_Group', 'Song (Intercept)'});

            if any(P1_mask),   B_P1   = tblRE.Estimate(P1_mask); else, B_P1   = []; end
            if any(P2_mask),   B_P2   = tblRE.Estimate(P2_mask); else, B_P2   = []; end
            if any(Song_mask), B_Song = tblRE.Estimate(Song_mask); else, B_Song = []; end
        else
            try
                [Bvec, Bnames] = randomEffects(best_model);
                isP1   = contains(Bnames, 'P1');
                isP2   = contains(Bnames, 'P2');
                isSong = contains(Bnames, 'Song');
                B_P1   = Bvec(isP1);
                B_P2   = Bvec(isP2);
                B_Song = Bvec(isSong);
            catch ME2
                error('Random effects retrieval failed in legacy mode: %s', ME2.message);
            end
        end

        subplot(1, 2, 1); hold on;
        hasLegend = false;
        if ~isempty(B_P1)
            plot(1:numel(B_P1), B_P1, 'o-', 'LineWidth', 1.2, ...
                'Color', blue_color, 'DisplayName', 'P1 Effects');
            hasLegend = true;
        end
        if ~isempty(B_P2)
            plot(1:numel(B_P2), B_P2, 's-', 'LineWidth', 1.2, ...
                'Color', red_color, 'DisplayName', 'P2 Effects');
            hasLegend = true;
        end
        if ~isempty(B_Song) && isempty(B_P1) && isempty(B_P2)
            plot(1:numel(B_Song), B_Song, '^-', 'LineWidth', 1.2, ...
                'Color', [0.3 0.3 0.3], 'DisplayName', 'Song Effects');
            hasLegend = true;
        end
        xlabel('Index');
        ylabel('Random Effect (BLUP)');
        title('Individual Random Effects');
        if hasLegend, legend('Location', 'best'); end
        grid on;

        subplot(1, 2, 2); hold on;
        didAnyHist = false;
        if exist('B_P1', 'var') && ~isempty(B_P1)
            histogram(B_P1, 'FaceColor', blue_color, 'FaceAlpha', 0.7, 'DisplayName', 'P1 Effects');
            didAnyHist = true;
        end
        if exist('B_P2', 'var') && ~isempty(B_P2)
            histogram(B_P2, 'FaceColor', red_color, 'FaceAlpha', 0.7, 'DisplayName', 'P2 Effects');
            didAnyHist = true;
        end
        if exist('B_Song', 'var') && ~isempty(B_Song) && ~didAnyHist
            histogram(B_Song, 'FaceAlpha', 0.7, 'DisplayName', 'Song Effects');
            didAnyHist = true;
        end
        if didAnyHist
            legend('Location', 'best');
        end
        xlabel('Random Effect Value');
        ylabel('Count');
        title('Distribution of Random Effects');
        grid on;

        sgtitle('Individual Participant Effects', 'FontSize', 14);
        try
            saveas(fig2, fullfile(outdir, 'ISC_Individual_Effects.png'), 'png');
        catch ME
            fprintf('Could not save ISC_Individual_Effects.png: %s\n', ME.message);
        end
    catch ME
        fprintf('Could not create individual effects plot: %s\n', ME.message);
        try, close(fig2); end %#ok<TRYNC>
    end
end

%% === Reporting and exports ===
fprintf('\n=== REPORTING & EXPORTS ===\n');

Model = string(model_names(:));
ComparisonTbl = table( ...
    Model, ...
    AIC(:), ...
    BIC(:), ...
    LogLik(:), ...
    Dose_Estimate(:), ...
    Dose_CI_Lower(:), ...
    Dose_CI_Upper(:), ...
    Dose_pValue(:), ...
    'VariableNames', {'Model', 'AIC', 'BIC', 'LogLik', 'Dose_Beta', 'Dose_CI_L', 'Dose_CI_U', 'Dose_p'});

best_flags = false(height(ComparisonTbl), 1);
best_flags(best_idx) = true;
ComparisonTbl.BestModel = best_flags;

fprintf('\nModel Comparison (lower AIC/BIC is better):\n');
disp(ComparisonTbl);

fprintf('\nLikelihood Ratio Tests:\n');
for i = 1:numel(LRT_results)
    fprintf('  %s\n', LRT_results{i});
end

fprintf('\nBest model by AIC: %s\n', model_names{best_idx});
try
    fprintf('\nBest Model Fixed Effects:\n');
    disp(best_model.Coefficients)
catch
    fprintf('Could not display coefficients for the best model.\n');
end

try
    fprintf('\nBest Model Random Effects (first 10 rows if available):\n');
    try
        tblRE = randomEffects(best_model);
        if istable(tblRE)
            disp(tblRE(1:min(10, height(tblRE)), :));
        else
            [Bvec, Bnames] = randomEffects(best_model); %#ok<ASGLU>
            n = min(10, numel(Bvec));
            for k = 1:n
                fprintf('  %s: %+0.4f\n', Bnames{k}, Bvec(k));
            end
        end
    catch ME
        fprintf('Random effects preview failed: %s\n', ME.message);
    end
catch
end

try
    writetable(ComparisonTbl, fullfile(outdir, 'ISC_Model_Comparison.csv'));
    fprintf('Saved: ISC_Model_Comparison.csv\n');
catch ME
    fprintf('Could not save ISC_Model_Comparison.csv: %s\n', ME.message);
end

try
    raw_export = table(T.Dose, T.ISC_global, T.Song, T.P1, T.P2, ...
        'VariableNames', {'Dose', 'ISC_global', 'Song', 'P1', 'P2'});
    writetable(raw_export, fullfile(outdir, 'ISC_Raw_Subset.csv'));
    fprintf('Saved: ISC_Raw_Subset.csv\n');
catch ME
    fprintf('Could not save ISC_Raw_Subset.csv: %s\n', ME.message);
end

try
    save(fullfile(outdir, 'ISC_LMM_Workspace.mat'), ...
        'T', 'models', 'model_names', 'AIC', 'BIC', 'LogLik', ...
        'Dose_pValue', 'Dose_Estimate', 'Dose_CI_Lower', 'Dose_CI_Upper', ...
        'LRT_results', 'best_idx', 'best_model', 'legacyMode', '-v7.3');
    fprintf('Saved: ISC_LMM_Workspace.mat\n');
catch ME
    fprintf('Could not save ISC_LMM_Workspace.mat: %s\n', ME.message);
end

try
    fprintf('\nANOVA-like table for best model:\n');
    try
        disp(anova(best_model, 'DFMethod', 'Satterthwaite'));
    catch
        disp(anova(best_model));
    end
catch ME
    fprintf('ANOVA display failed: %s\n', ME.message);
end

%% === Detailed text summary ===
summaryFile = fullfile(outdir, 'ISC_Analysis_Summary.txt');
try
    fid = fopen(summaryFile, 'w');
    if fid == -1
        error('Could not open summary file for writing.');
    end

    fprintf(fid, '============================\n');
    fprintf(fid, '  ISC Analysis Summary\n');
    fprintf(fid, '============================\n\n');

    fprintf(fid, 'Model Comparison (lower AIC/BIC is better):\n');
    fprintf(fid, '%-20s %-8s %-8s %-8s %-10s %-10s %-10s %-8s %-5s\n', ...
        'Model', 'AIC', 'BIC', 'LogLik', 'Dose_Beta', 'CI_Lower', 'CI_Upper', 'pValue', 'Best');
    for i = 1:height(ComparisonTbl)
        fprintf(fid, '%-20s %-8.3f %-8.3f %-8.3f %-10.4f %-10.4f %-10.4f %-8.4g %-5s\n', ...
            ComparisonTbl.Model{i}, ComparisonTbl.AIC(i), ComparisonTbl.BIC(i), ComparisonTbl.LogLik(i), ...
            ComparisonTbl.Dose_Beta(i), ComparisonTbl.Dose_CI_L(i), ComparisonTbl.Dose_CI_U(i), ...
            ComparisonTbl.Dose_p(i), string(logical(ComparisonTbl.BestModel(i))));
    end
    fprintf(fid, '\n');

    fprintf(fid, 'Best model by AIC: %s\n', model_names{best_idx});
    fprintf(fid, '  AIC = %.3f, BIC = %.3f, LogLik = %.3f\n\n', ...
        AIC(best_idx), BIC(best_idx), LogLik(best_idx));

    idxDose = strcmp(best_model.CoefficientNames, 'Dose');
    if any(idxDose)
        est  = best_model.Coefficients.Estimate(idxDose);
        pval = best_model.Coefficients.pValue(idxDose);
        ci   = coefCI(best_model);
        ciL  = ci(idxDose, 1);
        ciU  = ci(idxDose, 2);
        fprintf(fid, 'Dose effect (High vs Low) in best model:\n');
        fprintf(fid, '  beta = %.4f, 95%% CI [%.4f, %.4f], p = %.4g\n\n', est, ciL, ciU, pval);
    end

    fprintf(fid, 'Likelihood Ratio Tests (model improvements):\n');
    for i = 1:numel(LRT_results)
        fprintf(fid, '  %s\n', LRT_results{i});
    end
    fprintf(fid, '\n');

    fprintf(fid, 'Descriptive statistics by Dose:\n');
    doses = unique(T.Dose(~isnan(T.Dose)));
    for d = 1:numel(doses)
        vals = T.ISC_global(T.Dose == doses(d));
        fprintf(fid, '  Dose %.0f: Mean ISC = %.4f, SD = %.4f, N = %d\n', ...
            doses(d), mean(vals, 'omitnan'), std(vals, 'omitnan'), sum(~isnan(vals)));
    end
    fprintf(fid, '\n');

    fprintf(fid, 'Effect size (Cohen''s d) = %.3f (%s effect)\n\n', cohens_d, d_interpret);

    fprintf(fid, 'Interpretation:\n');
    if any(idxDose)
        if pval < 0.05
            fprintf(fid, '  The dose effect is statistically significant, indicating that ISC differs between high and low dose conditions.\n');
        else
            fprintf(fid, '  The dose effect is not statistically significant; ISC differences between high and low dose conditions are not reliable.\n');
        end
    end
    fprintf(fid, '  Model comparison shows how adding random intercepts for songs and/or participants changes model fit.\n');
    fprintf(fid, '  LRT results indicate which additions significantly improve the model.\n');
    if contains(model_names{best_idx}, 'Participants') || contains(model_names{best_idx}, 'Song')
        fprintf(fid, '  The best model includes random effects, suggesting that variance in ISC is partly explained by differences between participants and/or songs.\n');
    else
        fprintf(fid, '  The best model does not include random effects, implying minimal variation attributable to participants or songs.\n');
    end
    fprintf(fid, '\n');

    fprintf(fid, 'Generated output files:\n');
    fprintf(fid, '  - ISC_Model_Comparison.csv\n');
    fprintf(fid, '  - ISC_Raw_Subset.csv\n');
    fprintf(fid, '  - ISC_Analysis_Complete_Figure.png\n');
    fprintf(fid, '  - ISC_Individual_Effects.png\n');
    fprintf(fid, '  - ISC_LMM_Workspace.mat\n');
    fprintf(fid, '  - ISC_Analysis_Summary.txt\n');

    fclose(fid);
    type(summaryFile);
    fprintf('Saved detailed text summary to %s\n', summaryFile);
catch ME
    fprintf('Could not generate/save detailed summary: %s\n', ME.message);
end

fprintf('\n=== COMPLETE ===\n');
fprintf('All models fitted, figures saved, tables exported.\n');
fprintf('Best model: %s\n', model_names{best_idx});
fprintf('Outputs in: %s\n\n', outdir);
