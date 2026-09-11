%% PLV_Individual_Task_Analysis.m
% =========================================================================
% Linear mixed-effects models for the individual music listening task.
% Part of a double-blind, randomised psilocybin EEG study conducted at
% Universidad de Buenos Aires.
%
% Models:
%   Primary:   Engagement ~ zPLV_restsub + Dose + zOllen + (1|Participant) + (1|Song)
%   Secondary: Engagement ~ zPLV_restsub + Dose         + (1|Participant) + (1|Song)
%
% Also fits raw-PLV equivalents for comparison.
%
% Requires:
%   - MATLAB with Statistics and Machine Learning Toolbox (fitlme)
%   - config.m in the same folder (copy of config_template.m)
%
% Input:
%   - PLV_results_merged.csv in config.data_dir
%
% Outputs saved to config.out_dir:
%   - Cleaned CSVs and audit log
%   - Fitted model workspace
%   - Manuscript summary text file
%   - Diagnostics figure and per-song predicted means
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
infile  = fullfile(basedir, 'PLV_results_merged.csv');

if ~exist(outdir, 'dir'), mkdir(outdir); end
logfile = fullfile(outdir, 'PLV_cleaning_audit.txt');
logfid  = fopen(logfile, 'w');

fprintf('\n=== PLV LMM (Individual Task) — START ===\n');
fprintf('Input : %s\n', infile);
fprintf('Output: %s\n\n', outdir);
fprintf(logfid, 'Run started: %s\n\n', datestr(now));

%% ============================================================
%% CHUNK 1 — Load, clean, z-score, audit
%% ============================================================

T = readtable(infile);

% ---- Column sanity ----
mustHave = {'participant','session','song_PLV_summary_table','question','rating', ...
            'plv_restsub','dose','ollen'};
missingCols = setdiff(mustHave, T.Properties.VariableNames);
if ~isempty(missingCols)
    fclose(logfid);
    error('Missing expected columns in input CSV: %s', strjoin(missingCols, ', '));
end

% ---- Type coercions ----
if ~isnumeric(T.participant), T.participant = double(string(T.participant)); end
if ~isnumeric(T.session),     T.session     = double(string(T.session));     end

T.question = strtrim(string(T.question));
T.song_PLV_summary_table = strtrim(string(T.song_PLV_summary_table));
T.dose = strtrim(string(T.dose));

T.rating      = double(T.rating);
T.plv_restsub = double(T.plv_restsub);
T.ollen       = double(T.ollen);

%% ---- Filter to Engagement rows ----
isEng = strcmpi(T.question, 'Involucramiento');
n_before = height(T);
T = T(isEng, :);
fprintf('Kept %d / %d rows with question == "Involucramiento".\n', height(T), n_before);
fprintf(logfid, 'Filter: Involucramiento rows kept = %d (from %d)\n', height(T), n_before);

%% ---- Drop rows missing key fields ----
bad = isnan(T.rating) | isnan(T.plv_restsub);
if sum(bad) > 0
    fprintf('Dropped %d rows with missing rating or plv_restsub.\n', sum(bad));
    fprintf(logfid, 'Dropped %d rows with missing rating/plv_restsub.\n', sum(bad));
    T(bad, :) = [];
end

blankSong = (T.song_PLV_summary_table == "") | ismissing(T.song_PLV_summary_table);
if any(blankSong)
    fprintf('Dropped %d rows with blank song_PLV_summary_table.\n', sum(blankSong));
    fprintf(logfid, 'Dropped %d rows with blank song_PLV_summary_table.\n', sum(blankSong));
    T(blankSong, :) = [];
end

%% ---- Recode Dose ----
d = lower(T.dose);
dose_num = nan(height(T), 1);
dose_num(d == "alta") = 1;
dose_num(d == "baja") = 0;

mask = isnan(dose_num);
tmp = str2double(d(mask));
dose_num(mask) = tmp;

if any(isnan(dose_num))
    n_bad = sum(isnan(dose_num));
    fprintf(2, '[WARN] %d dose values could not be parsed. They will be dropped.\n', n_bad);
    fprintf(logfid, '[WARN] Dropping %d rows with unparsable dose.\n', n_bad);
    T(isnan(dose_num), :) = [];
    dose_num = dose_num(~isnan(dose_num));
end
T.Dose = double(dose_num);

%% ---- Remove duplicates ----
key = strcat("P", string(T.participant), "_S", string(T.session), "_", T.song_PLV_summary_table);
[~, firstIdx] = unique(key, 'stable');
dupeMask = true(height(T), 1); dupeMask(firstIdx) = false;
if sum(dupeMask) > 0
    fprintf('Removed %d duplicate Involucramiento rows (kept first).\n', sum(dupeMask));
    fprintf(logfid, 'Removed %d duplicates by (participant,session,song).\n', sum(dupeMask));
    T = T(firstIdx, :);
end

%% ---- Z-score ----
zPLV = nan(height(T), 1);
[G, pid] = findgroups(T.participant);
grp_mu = splitapply(@(x) mean(x, 'omitnan'), T.plv_restsub, G);
grp_sd = splitapply(@(x) std(x, 'omitnan'),   T.plv_restsub, G);
grp_sd_fixed = grp_sd;
grp_sd_fixed(~isfinite(grp_sd_fixed) | grp_sd_fixed == 0) = NaN;

for gi = 1:numel(pid)
    rows = (G == gi);
    zPLV(rows) = (T.plv_restsub(rows) - grp_mu(gi)) ./ grp_sd_fixed(gi);
    if ~isfinite(grp_sd(gi)) || grp_sd(gi) == 0
        zPLV(rows) = 0;
        fprintf(logfid, 'Participant %g has zero/NaN PLV SD; zPLV set to 0 for %d rows.\n', pid(gi), sum(rows));
    end
end
T.zPLV_restsub = zPLV;

muO  = mean(T.ollen, 'omitnan');
sdO  = std(T.ollen,  'omitnan');
T.zOllen = (T.ollen - muO) ./ sdO;

%% ---- Build analysis tables ----
T_primary   = T(~isnan(T.zOllen), :);
T_secondary = T;

T_primary.Participant = categorical(T_primary.participant);
T_primary.Song        = categorical(T_primary.song_PLV_summary_table);
T_primary.Dose_cat    = categorical(T_primary.Dose);

T_secondary.Participant = categorical(T_secondary.participant);
T_secondary.Song        = categorical(T_secondary.song_PLV_summary_table);
T_secondary.Dose_cat    = categorical(T_secondary.Dose);

%% ---- Audit summary ----
nP_all    = numel(unique(T.participant));
nP_prim   = numel(unique(T_primary.participant));
nSongs    = numel(unique(T.song_PLV_summary_table));
nRowsPrim = height(T_primary);

fprintf('\n--- DATA SUMMARY (post-clean) ---\n');
fprintf('Participants (all in engagement data): %d\n', nP_all);
fprintf('Participants in PRIMARY (with Ollen) : %d\n', nP_prim);
fprintf('Songs used                            : %d\n', nSongs);
fprintf('Rows in PRIMARY dataset               : %d\n', nRowsPrim);
fprintf(logfid, 'Participants (all engagement) = %d\n', nP_all);
fprintf(logfid, 'Participants (primary w/ Ollen) = %d\n', nP_prim);
fprintf(logfid, 'Songs = %d\n', nSongs);
fprintf(logfid, 'Rows (primary) = %d\n', nRowsPrim);

missO = setdiff(unique(T.participant), unique(T_primary.participant));
if ~isempty(missO)
    fprintf('Participants missing Ollen (secondary-only): %s\n', strjoin("P"+string(missO), ', '));
    fprintf(logfid, 'Missing Ollen participants (secondary-only): %s\n', strjoin("P"+string(missO), ', '));
end

%% ---- Save cleaned tables ----
safe_writetable(T,           fullfile(outdir, 'PLV_Involucramiento_ALL_clean.csv'));
safe_writetable(T_primary,   fullfile(outdir, 'PLV_Involucramiento_PRIMARY_clean.csv'));
safe_writetable(T_secondary, fullfile(outdir, 'PLV_Involucramiento_SECONDARY_clean.csv'));

save(fullfile(outdir, 'PLV_clean_workspace.mat'), 'T', 'T_primary', 'T_secondary', 'muO', 'sdO');
fprintf('\nCleaned datasets saved in: %s\n', outdir);

%% ============================================================
%% CHUNK 2 — Fit LMMs
%% ============================================================
fprintf('\n=== PLV LMM — FITTING MODELS ===\n');

form_primary_z     = 'rating ~ zPLV_restsub + Dose_cat + zOllen + (1|Participant) + (1|Song)';
form_secondary_z   = 'rating ~ zPLV_restsub + Dose_cat          + (1|Participant) + (1|Song)';
form_primary_raw   = 'rating ~ plv_restsub + Dose_cat + zOllen + (1|Participant) + (1|Song)';
form_secondary_raw = 'rating ~ plv_restsub + Dose_cat          + (1|Participant) + (1|Song)';

fprintf('Fitting primary LMM (zPLV)...\n');
M_primary_z   = fitlme(T_primary,   form_primary_z,   'DummyVarCoding', 'effects');
fprintf('Fitting secondary LMM (zPLV)...\n');
M_secondary_z = fitlme(T_secondary, form_secondary_z, 'DummyVarCoding', 'effects');
fprintf('Fitting primary LMM (RAW PLV)...\n');
M_primary_raw   = fitlme(T_primary,   form_primary_raw,   'DummyVarCoding', 'effects');
fprintf('Fitting secondary LMM (RAW PLV)...\n');
M_secondary_raw = fitlme(T_secondary, form_secondary_raw, 'DummyVarCoding', 'effects');

fprintf('\nModel AICs:\n');
fprintf('  Primary (z):     %.3f\n', M_primary_z.ModelCriterion.AIC);
fprintf('  Secondary (z):   %.3f\n', M_secondary_z.ModelCriterion.AIC);
fprintf('  Primary (raw):   %.3f\n', M_primary_raw.ModelCriterion.AIC);
fprintf('  Secondary (raw): %.3f\n', M_secondary_raw.ModelCriterion.AIC);

M_primary   = M_primary_z;
M_secondary = M_secondary_z;

save(fullfile(outdir, 'PLV_models_workspace.mat'), ...
     'M_primary_z', 'M_secondary_z', 'M_primary_raw', 'M_secondary_raw', ...
     'M_primary', 'M_secondary', 'T_primary', 'T_secondary');
fprintf('Models saved to: %s\n', fullfile(outdir, 'PLV_models_workspace.mat'));

%% ============================================================
%% CHUNK 3 — Diagnostics, plots, manuscript summary
%% ============================================================
fprintf('\n=== PLV LMM — DIAGNOSTICS ===\n');

summP_z = model_long_summary_plv(M_primary_z,   T_primary,   'PLV -> Engagement (Primary, z-scored PLV)');
summS_z = model_long_summary_plv(M_secondary_z, T_secondary, 'PLV -> Engagement (Secondary, z-scored PLV)');
summP_raw = model_long_summary_plv(M_primary_raw,   T_primary,   'PLV -> Engagement (Primary, RAW PLV)');
summS_raw = model_long_summary_plv(M_secondary_raw, T_secondary, 'PLV -> Engagement (Secondary, RAW PLV)');

manu_file = fullfile(outdir, 'PLV_LMM_manuscript_summary.txt');
fid = fopen(manu_file, 'w');
for i = 1:numel(summP_z),   fprintf(fid, '%s\n', summP_z{i});   end
fprintf(fid, '\n');
for i = 1:numel(summS_z),   fprintf(fid, '%s\n', summS_z{i});   end
fprintf(fid, '\n');
for i = 1:numel(summP_raw), fprintf(fid, '%s\n', summP_raw{i}); end
fprintf(fid, '\n');
for i = 1:numel(summS_raw), fprintf(fid, '%s\n', summS_raw{i}); end
fclose(fid);
fprintf('\nManuscript-style summary saved to %s\n', manu_file);

writetable(as_table(M_primary_z.Coefficients),   fullfile(outdir, 'PLV_LMM_primary_fixed_effects_z.csv'));
writetable(as_table(M_secondary_z.Coefficients), fullfile(outdir, 'PLV_LMM_secondary_fixed_effects_z.csv'));
writetable(as_table(M_primary_raw.Coefficients),   fullfile(outdir, 'PLV_LMM_primary_fixed_effects_raw.csv'));
writetable(as_table(M_secondary_raw.Coefficients), fullfile(outdir, 'PLV_LMM_secondary_fixed_effects_raw.csv'));

%% ---- Compact z vs raw PLV comparison ----
cmp = [];
cmp = [cmp; extract_term_row('Primary',   'z',   M_primary_z,   'zPLV_restsub')];
cmp = [cmp; extract_term_row('Secondary', 'z',   M_secondary_z, 'zPLV_restsub')];
cmp = [cmp; extract_term_row('Primary',   'raw', M_primary_raw,   'plv_restsub')];
cmp = [cmp; extract_term_row('Secondary', 'raw', M_secondary_raw, 'plv_restsub')];
writetable(struct2table(cmp), fullfile(outdir, 'PLV_LMM_PLVterm_comparison.csv'));

%% ---- Diagnostics figure ----
fig = figure('Color', 'w', 'Position', [100 100 1400 800]);
tiledlayout(2, 3, 'TileSpacing', 'compact', 'Padding', 'compact');

nexttile;
boxchart(categorical(T_secondary.Dose_cat), T_secondary.rating);
xlabel('Dose'); ylabel('Engagement rating'); title('A) Engagement by Dose');

nexttile; hold on;
cats = categories(T_secondary.Dose_cat);
yh_z = predict(M_secondary_z, T_secondary, 'Conditional', false);
mZ   = splitapply(@(x) mean(x, 'omitnan'), yh_z, findgroups(T_secondary.Dose_cat));
yh_r = predict(M_secondary_raw, T_secondary, 'Conditional', false);
mR   = splitapply(@(x) mean(x, 'omitnan'), yh_r, findgroups(T_secondary.Dose_cat));
plot(1:numel(cats), mZ, '-o', 'LineWidth', 1.5);
plot(1:numel(cats), mR, '-s', 'LineWidth', 1.5);
set(gca, 'XTick', 1:numel(cats), 'XTickLabel', cats);
ylabel('Predicted rating'); title('B) Predicted Means (z vs raw)');
legend({'zPLV model', 'raw PLV model'}, 'Location', 'best');

nexttile;
labels = {'Primary z', 'Secondary z', 'Primary raw', 'Secondary raw'};
AICs = [M_primary_z.ModelCriterion.AIC, M_secondary_z.ModelCriterion.AIC, ...
        M_primary_raw.ModelCriterion.AIC, M_secondary_raw.ModelCriterion.AIC];
bar(AICs);
set(gca, 'XTickLabel', labels, 'XTickLabelRotation', 20);
ylabel('AIC'); title('C) Model Comparison (AIC)');

nexttile; hold on;
[bd1, se1] = get_beta(M_primary_z,   'Dose_cat_0');
[bd2, se2] = get_beta(M_secondary_z, 'Dose_cat_0');
[bd3, se3] = get_beta(M_primary_raw,   'Dose_cat_0');
[bd4, se4] = get_beta(M_secondary_raw, 'Dose_cat_0');
errorbar(1:4, [bd1 bd2 bd3 bd4], 1.96 * [se1 se2 se3 se4], 'o', 'LineWidth', 1.5);
yline(0, '--');
set(gca, 'XTick', 1:4, 'XTickLabel', labels, 'XTickLabelRotation', 20);
ylabel('\beta (Dose)'); title('D) Dose Effect Across Models');

nexttile;
[~, bestIdx] = min(AICs);
Ms = {M_primary_z, M_secondary_z, M_primary_raw, M_secondary_raw};
Mbest = Ms{bestIdx};
scatter(fitted(Mbest), Mbest.Residuals.Raw, 'filled'); yline(0, '--'); grid on;
xlabel('Fitted'); ylabel('Residuals'); title('E) Residuals vs Fitted');

nexttile;
qqplot(Mbest.Residuals.Raw); title('F) Q-Q Plot');

sgtitle('PLV LMM Analysis');
saveas(fig, fullfile(outdir, 'PLV_LMM_complete_results.png'));
fprintf('Diagnostics figure saved.\n');

%% ---- Per-song × Dose predicted means ----
fprintf('\n=== Per-song x Dose predicted means (best AIC model) ===\n');
Tpredict = T_primary;
yhat_fix = predict(Mbest, Tpredict, 'Conditional', false);
Tpredict.Predicted = yhat_fix;

G = findgroups(Tpredict.Song, Tpredict.Dose_cat);
meanVals = splitapply(@(x) mean(x, 'omitnan'), Tpredict.Predicted, G);
sdVals   = splitapply(@(x) std(x, 'omitnan'),  Tpredict.Predicted, G);
nVals    = splitapply(@numel, Tpredict.Predicted, G);

songCats = categories(Tpredict.Song);
doseCats = categories(Tpredict.Dose_cat);
[songGrid, doseGrid] = ndgrid(1:numel(songCats), 1:numel(doseCats));
T_songdose = table( ...
    songCats(songGrid(:)), ...
    doseCats(doseGrid(:)), ...
    meanVals, sdVals, nVals, ...
    'VariableNames', {'Song', 'Dose', 'PredictedMean', 'PredictedSD', 'N'});

T_overall = groupsummary(T_songdose, "Song", "mean", "PredictedMean");
T_overall = sortrows(T_overall, "mean_PredictedMean");
sortedSongs = T_overall.Song;

meanMat = reshape(meanVals, numel(songCats), numel(doseCats));
[~, orderIdx] = ismember(sortedSongs, songCats);
meanMat_sorted = meanMat(orderIdx, :);

T_songdose_sorted = sortrows(T_songdose, "Song");
writetable(T_songdose_sorted, fullfile(outdir, 'PLV_LMM_perSongDose_predicted.csv'));

figSongDose = figure('Color', 'w', 'Position', [200 200 800 420]);
bar(meanMat_sorted, 'grouped');
xlabel('Song (sorted by overall predicted engagement)');
ylabel('Predicted engagement (fixed effects)');
set(gca, 'XTick', 1:numel(sortedSongs), 'XTickLabel', sortedSongs, 'XTickLabelRotation', 20);
legend(doseCats, 'Location', 'best');
title('Predicted means by Song x Dose');
grid on;
saveas(figSongDose, fullfile(outdir, 'PLV_LMM_perSongDose_predicted.png'));
fprintf('Per-song x dose outputs saved.\n');

fprintf(logfid, '\nRun finished: %s\n', datestr(now));
fclose(logfid);

%% ============================================================
%% Helper functions
%% ============================================================

function safe_writetable(tbl, filename)
    if ~istable(tbl)
        error('safe_writetable:NotATable', ...
            'Attempted to write "%s", but the variable is not a table. Actual type: %s', ...
            filename, class(tbl));
    end
    if isempty(tbl)
        warning('safe_writetable:EmptyTable', 'Saving empty table to "%s"', filename);
    end
    writetable(tbl, filename);
end

function [h, crit_p, adj_p] = fdr_bh_local(pvals, q)
    if nargin < 2, q = 0.05; end
    p = pvals(:);
    [ps, ix] = sort(p);
    m = numel(p);
    thr = (1:m)' / m * q;
    rej = ps <= thr;
    if any(rej)
        k = find(rej, 1, 'last'); crit_p = ps(k); h = p <= crit_p;
    else
        h = false(size(p)); crit_p = NaN;
    end
    wtd = m * ps ./ (1:m)';
    adj_sorted = min(cummin(flipud(wtd)), 1);
    adj_sorted = flipud(adj_sorted);
    adj_p = nan(size(p));
    adj_p(ix) = adj_sorted;
end

function T = as_table(X)
    if istable(X)
        T = X;
    elseif isa(X, 'dataset')
        T = dataset2table(X);
    else
        error('Unsupported coefficient container of class %s', class(X));
    end
end

function names = varnames_robust(X)
    if istable(X)
        names = X.Properties.VariableNames;
    elseif isa(X, 'dataset')
        names = get(X, 'VarNames');
    else
        try, names = X.Properties.VariableNames; catch, names = {}; end
    end
end

function row = extract_term_row(modelType, plvType, M, termName)
    C = as_table(M.Coefficients);
    idx = find(strcmpi(C.Name, termName) | contains(lower(string(C.Name)), lower(termName)), 1, 'first');
    if isempty(idx)
        error('PLV term "%s" not found in %s %s model.', termName, modelType, plvType);
    end
    feMask = ~strcmpi(string(C.Name), '(Intercept)');
    [~, ~, pFDR] = fdr_bh_local(C.pValue(feMask), 0.05);
    feIdx = find(find(feMask) == idx);
    if isempty(feIdx), pF = NaN; else, pF = pFDR(feIdx); end

    F = NaN; pA = NaN; df1 = NaN; df2 = NaN;
    try
        A = anova(M, 'DFMethod', 'satterthwaite');
        for i = 1:height(A)
            tnm = string(A.Term{i});
            if tnm == "" || strcmpi(tnm, '(Intercept)'), continue; end
            if contains(lower(tnm), lower(strrep(termName, '_', '')))
                F = A.FStat(i); pA = A.pValue(i); df1 = A.DF1(i); df2 = A.DF2(i);
                break;
            end
        end
    catch
    end

    row = struct( ...
        'model',       string(modelType), ...
        'plv_type',    string(plvType), ...
        'term',        string(C.Name(idx)), ...
        'beta',        C.Estimate(idx), ...
        'SE',          C.SE(idx), ...
        't',           C.Estimate(idx) ./ C.SE(idx), ...
        'p_raw',       C.pValue(idx), ...
        'p_FDR_model', pF, ...
        'F_Satt',      F, ...
        'F_df1',       df1, ...
        'F_df2',       df2, ...
        'AIC',         M.ModelCriterion.AIC );
end

function [b, se] = get_beta(M, termName)
    C = as_table(M.Coefficients);
    idx = find(strcmpi(C.Name, termName), 1, 'first');
    if isempty(idx), b = NaN; se = NaN; else, b = C.Estimate(idx); se = C.SE(idx); end
end

function lines = model_long_summary_plv(M, T, label)
    lines = {};
    lines{end+1} = '============================';
    lines{end+1} = sprintf('Results: %s', label);
    lines{end+1} = '============================';

    nObs  = height(T);
    nPart = numel(categories(T.Participant));
    nSong = numel(categories(T.Song));
    lines{end+1} = sprintf('Sample: %d rows, %d participants, %d songs.', nObs, nPart, nSong);
    lines{end+1} = '';

    lines{end+1} = sprintf('Model: %s', M.Formula.char);
    lines{end+1} = sprintf('  Fit indices: AIC=%.3f, BIC=%.3f, logLik=%.3f.', ...
        M.ModelCriterion.AIC, M.ModelCriterion.BIC, M.LogLikelihood);
    try
        lines{end+1} = sprintf('  Explained variance: marginal=%.3f, conditional=%.3f.', ...
            M.Rsquared.Marginal, M.Rsquared.Conditional);
    catch
    end
    try
        resSD = std(M.Residuals.Raw, 'omitnan');
        lines{end+1} = sprintf('  Residual SD (raw): %.3f.', resSD);
    catch
    end
    lines{end+1} = '';

    coef = as_table(M.Coefficients);
    ci   = coefCI(M);
    coef.CI_Lower = ci(:, 1); coef.CI_Upper = ci(:, 2);
    if any(strcmp(varnames_robust(coef), 'tStat'))
        tcol = coef.tStat;
    else
        tcol = coef.Estimate ./ coef.SE;
    end

    feMask = ~strcmpi(string(coef.Name), '(Intercept)');
    [~, ~, p_fdr_all] = fdr_bh_local(coef.pValue(feMask), 0.05);
    fdr_ptr = 1;

    anovaMap = containers.Map('KeyType', 'char', 'ValueType', 'any');
    try
        A = anova(M, 'DFMethod', 'satterthwaite');
        for i = 1:height(A)
            term = strtrim(string(A.Term{i}));
            if term == "" || strcmpi(term, '(Intercept)'), continue; end
            anovaMap(char(term)) = [A.FStat(i), A.pValue(i), A.DF1(i), A.DF2(i)];
        end
    catch
    end

    lines{end+1} = 'Fixed effects:';
    for k = 1:height(coef)
        nm = string(coef.Name(k));
        est = coef.Estimate(k); se = coef.SE(k); lo = coef.CI_Lower(k); hi = coef.CI_Upper(k);
        p = coef.pValue(k); t = tcol(k);
        if nm == "(Intercept)"
            lines{end+1} = sprintf('  %s: beta=%.4f (SE=%.4f), t=%.3f, 95%% CI [%.4f, %.4f], p=%.4g.', ...
                nm, est, se, t, lo, hi, p);
            continue;
        end
        pFDR = p_fdr_all(fdr_ptr); fdr_ptr = fdr_ptr + 1;
        Ftxt = '';
        if isKey(anovaMap, char(nm))
            v = anovaMap(char(nm));
            Ftxt = sprintf('; ANOVA: F(%g,%g)=%.3f, p=%.4g', v(3), v(4), v(1), v(2));
        end
        lines{end+1} = sprintf('  %s: beta=%.4f (SE=%.4f), t=%.3f, 95%% CI [%.4f, %.4f], p=%.4g, FDR p=%.4g%s.', ...
            nm, est, se, t, lo, hi, p, pFDR, Ftxt);
    end
    lines{end+1} = '';

    try
        A = anova(M, 'DFMethod', 'satterthwaite');
        lines{end+1} = 'ANOVA (Satterthwaite):';
        for i = 1:height(A)
            term = string(A.Term{i});
            if term == "" || strcmpi(term, '(Intercept)'), continue; end
            lines{end+1} = sprintf('  %s: F(%g,%g)=%.3f, p=%.4g', term, A.DF1(i), A.DF2(i), A.FStat(i), A.pValue(i));
        end
        lines{end+1} = '';
    catch
    end

    if ismember('Dose_cat', T.Properties.VariableNames)
        try
            yhat_fix = predict(M, T, 'Conditional', false);
            Ttmp = table(T.Dose_cat, yhat_fix, 'VariableNames', {'Dose_cat', 'yhat_fix'});
            G = findgroups(Ttmp.Dose_cat);
            m = splitapply(@(x) mean(x, 'omitnan'), Ttmp.yhat_fix, G);
            s = splitapply(@(x) std(x, 'omitnan'),  Ttmp.yhat_fix, G);
            n = splitapply(@numel, Ttmp.yhat_fix, G);
            cats = categories(T.Dose_cat);
            lines{end+1} = 'Estimated marginal means (fixed effects only):';
            for j = 1:numel(cats)
                lines{end+1} = sprintf('  Dose=%s: mean=%.3f, SD=%.3f, n=%d', cats{j}, m(j), s(j), n(j));
            end
            lines{end+1} = '';
        catch
        end
    end

    if ismember('Dose', T.Properties.VariableNames)
        x0 = T.rating(T.Dose == 0); x1 = T.rating(T.Dose == 1);
        d  = (mean(x1, 'omitnan') - mean(x0, 'omitnan')) / ...
             sqrt(((numel(x1)-1)*var(x1, 'omitnan') + (numel(x0)-1)*var(x0, 'omitnan')) / max(numel(x1)+numel(x0)-2, 1));
        lines{end+1} = sprintf('Dose descriptives: 0 -> mean=%.3f (SD=%.3f, n=%d); 1 -> mean=%.3f (SD=%.3f, n=%d); Cohen''s d=%.2f', ...
            mean(x0, 'omitnan'), std(x0, 'omitnan'), numel(x0), ...
            mean(x1, 'omitnan'), std(x1, 'omitnan'), numel(x1), d);
        lines{end+1} = '';
    end

    lines{end+1} = 'Per-song counts and rating means:';
    Gs = findgroups(T.Song);
    ns = splitapply(@numel, T.rating, Gs);
    ms = splitapply(@(x) mean(x, 'omitnan'), T.rating, Gs);
    catsS = categories(T.Song);
    for j = 1:numel(catsS)
        lines{end+1} = sprintf('  Song=%s: n=%d, mean rating=%.3f', catsS{j}, ns(j), ms(j));
    end
    perSong = splitapply(@(x) numel(unique(x)), T.Participant, Gs);
    lines{end+1} = sprintf('\nParticipants per song: min=%d, median=%d, max=%d.', ...
        min(perSong), median(perSong), max(perSong));
end
