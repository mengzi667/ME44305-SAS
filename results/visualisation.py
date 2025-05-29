import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Data provided
data = {
    "Name": ["Traditional", "Improved-T1", "Improved-T2", "Innovated"],
    "Service Level Mean": [16.17, 19.27, 11.7, 11.83],
    "Std.": [2.83, 2.43, 1.19, 1.17],
    "Cost": [4856003.46, 4858778.82, 6368940.71, 4884859.83]
}

# Convert to DataFrame
df = pd.DataFrame(data)

# Extract data for plotting
experiments = df['Name'].values
sli_mean = df['Service Level Mean'].values
sli_std = df['Std.'].values
costs = df['Cost'].values / 1000000  # Convert to millions for better scaling

# Define colors (distinctive, works for light/dark themes)
sli_color = '#4e79a7'  # Blue for SLI
cost_color = '#f28e2b'  # Orange for Cost

# Create figure with two y-axes
fig, ax1 = plt.subplots(figsize=(10, 6))

# Plot SLI (left y-axis)
ax1.bar(experiments, sli_mean, yerr=sli_std, capsize=5, color=sli_color, edgecolor='black', label='SLI Mean', alpha=0.8)
ax1.set_xlabel('Experiment', fontsize=12)
ax1.set_ylabel('Service Level Indicator (SLI)', fontsize=12, color=sli_color)
ax1.tick_params(axis='y', labelcolor=sli_color)
ax1.set_ylim(0, 25)  # SLI range
ax1.grid(axis='y', linestyle='--', alpha=0.7)

# Add SLI value labels on top of bars
for i, (bar, mean) in enumerate(zip(ax1.patches, sli_mean)):
    height = bar.get_height()
    ax1.text(bar.get_x() + bar.get_width()/2, height + 0.5, f'{mean:.2f}', 
             ha='center', va='bottom', fontsize=10, color='black')

# Create second y-axis for Cost
ax2 = ax1.twinx()
ax2.plot(experiments, costs, '-o', color=cost_color, label='Cost (Millions $)', linewidth=2, markersize=8)
ax2.set_ylabel('Cost (Millions $)', fontsize=12, color=cost_color)
ax2.tick_params(axis='y', labelcolor=cost_color)
ax2.set_ylim(4, 7)  # Cost range in millions

# Title and legend
plt.title('SLI and Cost Comparison Across Experiments', fontsize=14)
fig.legend(loc='upper center', bbox_to_anchor=(0.5, -0.05), ncol=2, fontsize=10)

# Tight layout to avoid clipping
plt.tight_layout()

# Save the plot
plt.savefig('sli_cost_comparison.png', dpi=300, bbox_inches='tight')
plt.close()