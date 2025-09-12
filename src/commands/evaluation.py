import click
import json
import sys

try:
    from lib.metrics_evaluator import TEMetricsEvaluator
except ImportError:
    TEMetricsEvaluator = None

@click.command('evaluate')
@click.option('--predictions', required=True, type=click.Path(exists=True), 
              help='Arquivo CSV com predições')
@click.option('--output', 'output_dir', required=True, help='Diretório de saída para métricas')
@click.option('--hierarchy', default='src/nodes/tree.txt', help='Arquivo de hierarquia')
@click.option('--format', default='detailed', type=click.Choice(['summary', 'detailed', 'json']),
              help='Formato do relatório')
@click.option('--verbose', '-v', is_flag=True, help='Modo verboso')
@click.pass_context
def evaluate_metrics(ctx, predictions, output_dir, hierarchy, format, verbose):
    """Avaliar predições com métricas padronizadas completas"""
    
    if not verbose:
        verbose = ctx.obj.get('verbose', False)
    
    if not TEMetricsEvaluator:
        click.echo("❌ TEMetricsEvaluator não disponível")
        sys.exit(1)
    
    click.echo(f"🔬 Avaliando predições: {predictions}")
    click.echo(f"📁 Resultados em: {output_dir}")
    
    try:
        evaluator = TEMetricsEvaluator(hierarchy_file=hierarchy)
        metrics = evaluator.evaluate_predictions(predictions, output_dir)
        
        if isinstance(metrics, dict) and 'accuracy' in metrics:
            
            if format in ['summary', 'detailed']:
                click.echo(f"\n📈 MÉTRICAS PRINCIPAIS:")
                click.echo(f"{'='*50}")
                click.echo(f"🎯 Acurácia: {metrics.get('accuracy', 0.0):.4f}")
                click.echo(f"🎯 Precisão (macro): {metrics.get('precision_macro', 0.0):.4f}")
                click.echo(f"🎯 Recall (macro): {metrics.get('recall_macro', 0.0):.4f}")
                click.echo(f"🎯 F1-Score (macro): {metrics.get('f1_macro', 0.0):.4f}")
                click.echo(f"🎯 Especificidade: {metrics.get('specificity_macro', 0.0):.4f}")
                click.echo(f"🎯 Youden's J: {metrics.get('youdens_j', 0.0):.4f}")
            
            if format == 'detailed':
                auroc = metrics.get('auroc_macro')
                if auroc not in ['not_available', None]:
                    click.echo(f"📊 auROC (macro): {auroc:.4f}")
                
                map_score = metrics.get('map_macro')
                if map_score not in ['not_available', None]:
                    click.echo(f"📊 mAP (macro): {map_score:.4f}")
                
                if metrics.get('hierarchical_f1') not in ['not_available', None]:
                    click.echo(f"\n🌳 MÉTRICAS HIERÁRQUICAS:")
                    click.echo(f"   Precisão: {metrics.get('hierarchical_precision', 0.0):.4f}")
                    click.echo(f"   Recall: {metrics.get('hierarchical_recall', 0.0):.4f}")
                    click.echo(f"   F1-Score: {metrics.get('hierarchical_f1', 0.0):.4f}")
                    click.echo(f"   Distância média: {metrics.get('mean_hierarchical_distance', 0.0):.4f}")
                
                click.echo(f"\n📋 INFORMAÇÕES:")
                click.echo(f"   Amostras: {metrics.get('total_samples', 0)}")
                click.echo(f"   Classes verdadeiras: {metrics.get('num_classes', 0)}")
                click.echo(f"   Classes preditas: {metrics.get('num_predicted_classes', 0)}")
            
            if format == 'json':
                summary_metrics = {
                    "accuracy": metrics.get('accuracy', 0.0),
                    "precision_macro": metrics.get('precision_macro', 0.0),
                    "recall_macro": metrics.get('recall_macro', 0.0),
                    "f1_macro": metrics.get('f1_macro', 0.0),
                    "youdens_j": metrics.get('youdens_j', 0.0)
                }
                click.echo(json.dumps(summary_metrics, indent=2))
            
            click.echo(f"\n📄 RELATÓRIOS GERADOS:")
            click.echo(f"   📊 {output_dir}/detailed_metrics.json")
            click.echo(f"   📋 {output_dir}/metrics_summary.json")
            click.echo(f"   📖 {output_dir}/evaluation_report.txt")
            
        else:
            click.echo("📊 Apenas estatísticas descritivas (sem labels verdadeiros)")
        
        click.echo(f"\n✅ Avaliação concluída!")
        
    except Exception as e:
        click.echo(f"❌ Erro na avaliação: {str(e)}")
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)