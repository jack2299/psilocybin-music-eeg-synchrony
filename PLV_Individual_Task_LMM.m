%% PLV Individual Task LMM — Clean + Fit + Diagnostics
% Models:
%   Primary:   Engagement ~ zPLV_restsub + Dose + zOllen + (1|Participant) + (1|Song)
%   Secondary: Engagement ~ zPLV_restsub + Dose         + (1|Participant) + (1|Song)
%
% Usage:
%   1. Copy config_template.m to config.m and edit paths
%   2. Run this script

clear; clc;

%% ========= Load Configuration =========
run('config.m');  % loads config.data_dir and config.out_dir

infile    = fullfile(config.data_dir, 'PLV_results_merged.csv');
outdir    = config.out_dir;
if ~exist(outdir,'dir'), mkdir(outdir); end
logfile   = fullfile(outdir, 'PLV_cleaning_audit.txt');
logfid    = fopen(logfile,'w');

fprintf('\n=== PLV LMM (Individual Task) — START ===\n');
fprintf('Input : %s\n', infile);
fprintf('Output: %s\n\n', outdir);
fprintf(logfid, 'Run started: %s\n\n', datestr(now));

%% ========= Load =========
T = readtable(infile);

% ---- Column sanity ----
mustHave = {'participant','session','song_PLV_summary_table','question','rating', ...
            'plv_restsub','dose','ollen'};
missingCols = setdiff(mustHave, T.Properties.VariableNames);
if ~isempty(missingCols)
    fclose(logfid);
    error('Missing expected columns in input CSV: %s', strjoin(missingCols, ', '));
end

%% ========= Type coercions / cleaning =========
if ~isnumeric(T.participant), T.participant = double(string(T.participant)); end
if ~isnumeric(T.session),     T.session     = double(string(T.session));     end
T.question = string(T.question);
T.song_PLV_summary_table = string(T.song_PLV_summary_table);
T.dose = string(T.dose);
T.rating = double(T.rating);
T.plv_restsub = double(T.plv_restsub);
T.ollen = double(T.ollen);
T.question = strtrim(T.question);
T.song_PLV_summary_table = strtrim(T.song_PLV_summary_table);
T.dose = strtrim(T.dose);

%% ========= Filter to Engagement rows =========
isEng = strcmpi(T.question,'Involucramiento');
n_before = height(T);
T = T(isEng, :);
fprintf('Kept %d / %d rows with question == "Involucramiento".\n', height(T), n_before);
fprintf(logfid, 'Filter: Involucramiento rows kept = %d (from %d)\n', height(T), n_before);

%% ========= Drop rows missing key fields =========
bad = isnan(T.rating) | isnan(T.plv_restsub);
if sum(bad) > 0
    fprintf('Dropped %d rows with missing rating or plv_restsub.\n', sum(bad));
    fprintf(logfid, 'Dropped %d rows with missing rating/plv_restsub.\n', sum(bad));
    T(bad,:) = [];
end

blankSong = (T.song_PLV_summary_table == "") | ismissing(T.song_PLV_summary_table);
if any(blankSong)
    fprintf('Dropped %d rows with blank song_PLV_summary_table.\n', sum(blankSong));
    fprintf(logfid, 'Dropped %d rows with blank song_PLV_summary_table.\n', sum(blankSong));
    T(blankSong,:) = [];
end

%% ========= Recode Dose =========
d = lower(T.dose);
dose_num = nan(height(T),1);
dose_num(d=="alta") = 1;
dose_num(d=="baja") = 0;
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

%% ========= Remove duplicates =========
key = strcat("P", string(T.participant), "_S", string(T.session), "_", T.song_PLV_summary_table);
[~, firstIdx] = unique(key, 'stable');
dupeMask = true(height(T),1); dupeMask(firstIdx) = false;
if sum(dupeMask) > 0
    fprintf('Removed %d duplicate Involucramiento rows (kept first).\n', sum(dupeMask));
    fprintf(logfid, 'Removed %d duplicates by (participant,session,song).\n', sum(dupeMask));
    T = T(firstIdx, :);
end

%% ========= Z-score =========
% within-participant for PLV_restsub
zPLV = nan(height(T),1);
[G, pid] = findgroups(T.participant);
grp_mu = splitapply(@(x) mean(x,'omitnan'), T.plv_restsub, G);
grp_sd = splitapply(@(x) std(x, 'omitnan'),   T.plv_restsub, G);
grp_sd_fixed = grp_sd;
grp_sd_fixed(~isfinite(grp_sd_fixed) | grp_sd_fixed==0) = NaN;
for gi = 1:numel(pid)
    rows = (G == gi);
    zPLV(rows) = (T.plv_restsub(rows) - grp_mu(gi)) ./ grp_sd_fixed(gi);
    if ~isfinite(grp_sd(gi)) || grp_sd(gi) == 0
        zPLV(rows) = 0;
        fprintf(logfid, 'Participant %g has zero/NaN PLV SD; zPLV set to 0 for %d rows.\n', pid(gi), sum(rows));
    end
end
T.zPLV_restsub = zPLV;

% global zOllen
muO = mean(T.ollen, 'omitnan');
sdO = std(T.ollen, 'omitnan');
T.zOllen = (T.ollen - muO) ./ sdO;

%% ========= Build analysis tables =========
T_primary = T(~isnan(T.zOllen), :);
T_secondary = T;

T_primary.Participant = categorical(T_primary.participant);
T_primary.Song        = categorical(T_primary.song_PLV_summary_table);
T_primary.Dose_cat    = categorical(T_primary.Dose);
T_secondary.Participant = categorical(T_secondary.participant);
T_secondary.Song        = categorical(T_secondary.song_PLV_summary_table);
T_secondary.Dose_cat    = categorical(T_secondary.Dose);

%% ========= Quick audit =========
fprintf('\n--- DATA SUMMARY (post-clean) ---\n');
fprintf('Participants (all in engagement data): %d\n', numel(unique(T.participant)));
fprintf('Participants in PRIMARY (with Ollen) : %d\n', numel(unique(T_primary.participant)));
fprintf('Songs used                            : %d\n', numel(unique(T.song_PLV_summary_table)));
fprintf('Rows in PRIMARY dataset               : %d\n', height(T_primary));
fprintf(logfid, 'Participants (all engagement) = %d\n', numel(unique(T.participant)));
fprintf(logfid, 'Participants (primary w/ Ollen) = %d\n', numel(unique(T_primary.participant)));
fprintf(logfid, 'Songs = %d\n', numel(unique(T.song_PLV_summary_table)));
fprintf(logfid, 'Rows (primary) = %d\n', height(T_primary));

missO = setdiff(unique(T.participant), unique(T_primary.participant));
if ~isempty(missO)
    fprintf('Participants missing Ollen (secondary-only): %s\n', strjoin("P"+string(missO), ', '));
    fprintf(logfid, 'Missing Ollen participants (secondary-only): %s\n', strjoin("P"+string(missO), ', '));
end

%% ========= Save cleaned tables =========
safe_writetable(T,          fullfile(outdir, 'PLV_Involucramiento_ALL_clean.csv'));
safe_writetable(T_primary,  fullfile(outdir, 'PLV_Involucramiento_PRIMARY_clean.csv'));
safe_writetable(T_secondary,fullfile(outdir, 'PLV_Involucramiento_SECONDARY_clean.csv'));
save(fullfile(outdir, 'PLV_clean_workspace.mat'), 'T', 'T_primary', 'T_secondary', 'muO', 'sdO');

fprintf('\nCleaned datasets saved in: %s\n', outdir);
fprintf('Audit log: %s\n', logfile);
fprintf(logfid, '\nRun finished: %s\n', datestr(now));
fclose(logfid);

%% ========= CHUNK 2 — Fit LMMs =========
fprintf('\n=== PLV LMM — FITTING MODELS ===\n');

form_primary_z   = 'rating ~ zPLV_restsub + Dose_cat + zOllen + (1|Participant) + (1|Song)';
form_secondary_z = 'rating ~ zPLV_restsub + Dose_cat          + (1|Participant) + (1|Song)';
form_primary_raw   = 'rating ~ plv_restsub + Dose_cat + zOllen + (1|Participant) + (1|Song)';
form_secondary_raw = 'rating ~ plv_restsub + Dose_cat          + (1|Participant) + (1|Song)';

fprintf('Fitting primary LMM (zPLV)...\n');
M_primary_z   = fitlme(T_primary,   form_primary_z,   'DummyVarCoding','effects');
fprintf('Fitting secondary LMM (zPLV)...\n');
M_secondary_z = fitlme(T_secondary, form_secondary_z, 'DummyVarCoding','effects');
fprintf('Fitting primary LMM (RAW PLV)...\n');
M_primary_raw   = fitlme(T_primary,   form_primary_raw,   'DummyVarCoding','effects');
fprintf('Fitting secondary LMM (RAW PLV)...\n');
M_secondary_raw = fitlme(T_secondary, form_secondary_raw, 'DummyVarCoding','effects');

fprintf('\nModel AICs:\n');
fprintf('  Primary (z):   %.3f\n', M_primary_z.ModelCriterion.AIC);
fprintf('  Secondary (z): %.3f\n', M_secondary_z.ModelCriterion.AIC);
fprintf('  Primary (raw): %.3f\n', M_primary_raw.ModelCriterion.AIC);
fprintf('  Secondary (raw): %.3f\n', M_secondary_raw.ModelCriterion.AIC);

save(fullfile(outdir,'PLV_models_workspace.mat'), ...
     'M_primary_z','M_secondary_z','M_primary_raw','M_secondary_raw', ...
     'T_primary','T_secondary');

fprintf('Models saved to: %s\n', fullfile(outdir,'PLV_models_workspace.mat'));

%% ========= CHUNK 3 — Diagnostics and figures (abbreviated) =========
fprintf('\n=== PLV LMM — DIAGNOSTICS ===\n');
% (Full diagnostics and plotting code from your original script goes here)
% I have omitted the lengthy figure code for brevity; your original figure
% code can be copied as-is (it contains no hardcoded paths).

%% Helper functions (safe_writetable, fdr_bh_local, as_table, etc.)
% [Paste your helper functions from the original script here]
function safe_writetable(tbl, filename)
    if ~istable(tbl)
        error('safe_writetable:NotATable', ...
            'Attempted to write "%s", but the variable is not a table.', filename);
    end
    writetable(tbl, filename);
end

function [h, crit_p, adj_p] = fdr_bh_local(pvals, q)
    if nargin<2, q=0.05; end
    p = pvals(:);
    [ps,ix] = sort(p);
    m = numel(p);
    thr = (1:m)'/m*q;
    rej = ps <= thr;
    if any(rej), k = find(rej,1,'last'); crit_p = ps(k); h = p <= crit_p;
    else, h = false(size(p)); crit_p = NaN; end
    wtd = m*ps./(1:m)'; adj_sorted = min(cummin(flipud(wtd)),1); adj_sorted = flipud(adj_sorted);
    adj_p = nan(size(p)); adj_p(ix) = adj_sorted;
end

function T = as_table(X)
    if istable(X)
        T = X;
    elseif isa(X,'dataset')
        T = dataset2table(X);
    else
        error('Unsupported coefficient container of class %s', class(X));
    end
end