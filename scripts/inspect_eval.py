import json
from collections import defaultdict

with open(r'data\golden_eval_results.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

cats = defaultdict(list)
for item in d['detailed_results']:
    c = item['category']
    cats[c].append(item)

print(f"{'Category':<22} {'Cases':<6} {'Semantic Sim':<14} {'Citation Prec':<15} {'Factual Acc':<13} {'Composite':<10}")
print('-' * 82)
for c, items in cats.items():
    sim = sum(it['semantic_similarity_pct'] for it in items) / len(items)
    cit = sum(1 for it in items if it['citation_pass']) / len(items) * 100
    fact = sum(1 for it in items if it['facts_pass']) / len(items) * 100
    comp = sum(it['composite_score_pct'] for it in items) / len(items)
    print(f"{c:<22} {len(items):<6} {sim:6.2f}%        {cit:6.1f}%         {fact:6.1f}%        {comp:6.2f}%")
print('-' * 82)
sim_all = d['average_semantic_similarity_pct']
cit_all = d['citation_precision_pct']
fact_all = d['factual_accuracy_pct']
comp_all = d['overall_composite_score_pct']
print(f"{'Comprehensive Set':<22} {d['total_evaluated']:<6} {sim_all:6.2f}%        {cit_all:6.1f}%         {fact_all:6.1f}%        {comp_all:6.2f}%")
