"""Measured fixed-slice contours and full-statistics figures."""
from run_natural import *
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--workers',type=int,default=4);args=parser.parse_args();figures=OUT/'figures';figures.mkdir(exist_ok=True)
    study=Study(args.workers);study.difficulty();meta=[];jobs=[]
    if not (OUT/'enemy_fixed_slice_contours.csv').exists():
        for s in range(6):
            for g in GENRES:
                scene=study.scene(s,g,3)
                for a in np.geomspace(max(.06,scene['p'][0]*.45),min(3.5,scene['p'][0]*1.9),11):
                    for b in np.geomspace(max(.015,scene['p'][1]*.45),min(2.5,scene['p'][1]*1.9),11):
                        p=list(scene['p']);p[0]=float(a);p[1]=float(b);meta.append(dict(stage=s,genre=g,alpha=a,beta=b));jobs.append({**scene,'p':p,'validation':True,'pool_offset':12288,'trials':64,'stream':'fixed-contour'})
        csv('enemy_fixed_slice_contours.csv',pd.concat([pd.DataFrame(meta),pd.DataFrame(study.jobs(jobs))],axis=1))
    data=pd.read_csv(OUT/'enemy_fixed_slice_contours.csv')
    for s in range(6):
        for metric in ('wr','turns'):
            fig,axes=plt.subplots(2,3,figsize=(13,8),constrained_layout=True)
            for ax,g in zip(axes.flat,GENRES):
                sub=data[(data.stage==s)&(data.genre==g)].pivot(index='beta',columns='alpha',values=metric);x=sub.columns.to_numpy();y=sub.index.to_numpy()
                cs=ax.contourf(x,y,sub.to_numpy(),levels=np.linspace(0,1,11) if metric=='wr' else 12,cmap='viridis');ax.set_xscale('log');ax.set_yscale('log');ax.set(title=g,xlabel='alpha (BP multiplier)',ylabel='beta (base-hit multiplier)');fig.colorbar(cs,ax=ax)
            fig.suptitle(f'S{s+1} / {STAGES[s][0]} members: measured {metric}; other eight inputs fixed at each flow D3 anchor; n=64/cell');fig.savefig(figures/f'contours_S{s+1}_{metric}.png',dpi=150);plt.close(fig)
        variance=pd.read_csv(OUT/f'stage_S{s+1}_pca_variance.csv');load=pd.read_csv(OUT/f'stage_S{s+1}_pca_loadings.csv',index_col=0);corr=pd.read_csv(OUT/f'stage_S{s+1}_correlations.csv',index_col=0)
        rank=(load.iloc[:,:8].pow(2)*variance.variance.iloc[:8].to_numpy()).sum(1).sort_values(ascending=False);chosen=rank.head(26).index
        fig,axes=plt.subplots(1,2,figsize=(14,7),constrained_layout=True);axes[0].bar(variance.pc,variance.variance,label='component');axes[0].plot(variance.pc,variance.cumulative,label='cumulative');axes[0].axhline(.9,color='gray',linestyle='--');axes[0].set(xlabel='principal component',ylabel='variance fraction',title=f'S{s+1}: PCA variance');axes[0].legend()
        subset=corr.loc[chosen,chosen];im=axes[1].imshow(subset,cmap='coolwarm',vmin=-1,vmax=1);axes[1].set_xticks(range(len(chosen)),chosen,rotation=90,fontsize=5);axes[1].set_yticks(range(len(chosen)),chosen,fontsize=5);axes[1].set_title('26 features: first-eight-PC loading selection');fig.colorbar(im,ax=axes[1]);fig.savefig(figures/f'discovery_S{s+1}.png',dpi=150);plt.close(fig)
        centers=pd.read_csv(OUT/f'stage_S{s+1}_cluster_centroids.csv');fig,ax=plt.subplots(figsize=(13,5),constrained_layout=True);values=centers[chosen].to_numpy();values=(values-values.mean(0))/np.maximum(values.std(0),1e-12);im=ax.imshow(values,aspect='auto',cmap='coolwarm',vmin=-2,vmax=2);ax.set_xticks(range(len(chosen)),chosen,rotation=90,fontsize=6);ax.set_yticks(range(len(centers)),[f'cluster {v}' for v in centers.cluster]);ax.set_title(f'S{s+1}: centroid differences, standardized across centroids; raw values in CSV');fig.colorbar(im,ax=ax);fig.savefig(figures/f'centroids_S{s+1}.png',dpi=150);plt.close(fig)
    study.finish('contour_manifest.json')


if __name__=='__main__':main()
