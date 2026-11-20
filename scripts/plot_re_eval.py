import os
import matplotlib.pyplot as plt
import numpy as np

# IEEE style formatting
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['Times New Roman', 'DejaVu Serif']
plt.rcParams['font.size'] = 9
plt.rcParams['axes.labelsize'] = 9.5
plt.rcParams['axes.titlesize'] = 10
plt.rcParams['xtick.labelsize'] = 8.5
plt.rcParams['ytick.labelsize'] = 8.5
plt.rcParams['legend.fontsize'] = 8.5
plt.rcParams['figure.titlesize'] = 11

categories = ['Academics\n(7)', 'Attendance\n(5)', 'Exams\n(5)', 'Hostels\n(6)', 'Admin\n(5)', 'Campus Life\n(5)', 'Overall\n(33)']
semantic_sim = [99.16, 96.62, 89.46, 92.68, 99.62, 98.10, 96.04]
composite_score = [99.70, 98.82, 96.32, 97.43, 99.88, 99.34, 98.62]

x = np.arange(len(categories))
width = 0.36

fig, ax = plt.subplots(figsize=(6.2, 3.2), dpi=300)

rects1 = ax.bar(x - width/2, semantic_sim, width, label='Semantic Similarity (%)', color='#2b5c8f', edgecolor='black', linewidth=0.6)
rects2 = ax.bar(x + width/2, composite_score, width, label='Composite Quality (%)', color='#5c8f2b', edgecolor='black', linewidth=0.6)

ax.set_ylabel('Score (%)')
ax.set_ylim(80, 103)
ax.set_xticks(x)
ax.set_xticklabels(categories)
ax.legend(loc='lower left', frameon=True, edgecolor='#cccccc')
ax.grid(axis='y', linestyle='--', alpha=0.5)
ax.set_axisbelow(True)

# Value labels on top of bars
def autolabel(rects):
    for rect in rects:
        height = rect.get_height()
        ax.annotate(f'{height:.1f}%',
                    xy=(rect.get_x() + rect.get_width() / 2, height),
                    xytext=(0, 2),  # 2 points vertical offset
                    textcoords="offset points",
                    ha='center', va='bottom', fontsize=7.5)

autolabel(rects1)
autolabel(rects2)

plt.tight_layout()
out_dir = r'C:\Users\GOPAL\OneDrive\Desktop\AURA-IEEE-Paper\figures'
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, 're_eval_benchmark.png')
plt.savefig(out_path, dpi=300)
print(f'Successfully saved: {out_path}')
