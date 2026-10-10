"""Readable supplementary plot from saved aggregates; original frozen figure retained."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
root=Path('.')
frame=pd.read_csv(root/'reports/phase5/policies.csv')
test=frame[frame.scenario_id=='base']
validation=pd.read_csv(root/'reports/phase4_runs/9ca62eca2665438c9c97b4889413acfa/base_policy_results.csv')
fig,axes=plt.subplots(1,2,figsize=(13,5))
for ax in axes:
    ax.scatter(test.acceptance_rate,test.benchmark_utility_per_customer,label='Final test',s=45)
    ax.scatter(validation.acceptance_rate,validation.benchmark_utility_per_customer,
               label='Policy validation (selection)',marker='x',s=45)
    ax.axhline(0,color='grey',linewidth=.7)
    ax.set(xlabel='Acceptance rate',ylabel='Synthetic benchmark utility/customer')
    ax.grid(alpha=.15)
labels={'accept_all':'all','abstain_all':'none','low_risk_fraction_0.25':'25% cutoff',
        'low_risk_fraction_0.5':'50% cutoff','low_risk_fraction_0.75':'75% cutoff',
        'probability_0_5':'p < 0.5','analytic':'analytic','empirical':'empirical'}
for _,row in test.iterrows():
    if row.policy_id not in ['low_risk_fraction_0.25','analytic','empirical']:
        axes[0].annotate(labels[row.policy_id],(row.acceptance_rate,row.benchmark_utility_per_customer),
                         xytext=(-15,10),textcoords='offset points',fontsize=8)
for pid,offset in [('empirical',(-65,-40)),('low_risk_fraction_0.25',(-60,35)),('analytic',(10,5))]:
    row=test[test.policy_id==pid].iloc[0]
    axes[1].annotate(labels[pid],(row.acceptance_rate,row.benchmark_utility_per_customer),
                     xytext=offset,textcoords='offset points',arrowprops={'arrowstyle':'-'},fontsize=9)
axes[0].set_title('All eight frozen policies')
axes[0].legend(fontsize=8,loc='lower left')
axes[1].set(xlim=(.20,.30),ylim=(0,7),title='Low-acceptance detail; cutoffs unchanged')
fig.suptitle('Base synthetic gain=50, loss=500, cost=0; dimensionless units')
fig.tight_layout()
fig.savefig(root/'reports/phase5/policy_utility_detail.png',dpi=160,bbox_inches='tight')
