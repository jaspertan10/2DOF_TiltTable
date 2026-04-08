clc; clear; close all;

%% Load raw text file
filename = 'set point data.rtf';  % change path if needed
txt = fileread(filename);

%% Extract all entries using regex
pattern = 'T:\s*(\d+)\s*X:\s*(\d+)\s*Y:\s*(\d+)\s*Set Point X:\s*(\d+)';
tokens = regexp(txt, pattern, 'tokens');

% Convert to arrays
T = [];
X = [];
SP = [];

for i = 1:length(tokens)
    t = str2double(tokens{i}{1});
    x = str2double(tokens{i}{2});
    sp = str2double(tokens{i}{4});

    T(end+1) = t;
    X(end+1) = x;
    SP(end+1) = sp;
end

%% Find where setpoint changes to 300
idx_start = find(SP == 300, 1, 'first');

T = T(idx_start:end);
X = X(idx_start:end);

%% Convert time to seconds (normalize to 0)
T = T - T(1);       % start at 0
T = T / 100;        % adjust if needed (see note below)

%% Limit to 0–20 seconds
idx = T <= 20;

T_plot = T(idx);
X_plot = X(idx);

%% Plot
figure;
plot(T_plot, X_plot, 'LineWidth', 1.5);
hold on;
yline(300, '--', 'Setpoint', 'LineWidth', 1.5);

xlabel('Time (s)');
ylabel('X Position (ADC)');
title('Step Response: X Position (240 → 300)');
grid on;