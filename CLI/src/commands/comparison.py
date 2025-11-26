import click
import pandas as pd
import json
import os
from pathlib import Path
from datetime import datetime

try:
    from lib.metrics_evaluator import TEMetricsEvaluator
except ImportError:
    TEMetricsEvaluator = None

@click.command('compare')
@click.option('--results-dir', required=True, type=click.Path(exists=True),
              help='Diretório com múltiplos resultados')
@click.option('--output', default='comparison_results', help='Diretório de saída para comparação')
@click.option('--metric', default='f1_macro', help='Métrica principal para comparação')
@click.option('--auto-evaluate', is_flag=True, 
              help='Calcular métricas automaticamente para arquivos sem avaliação')
@click.option('--include-incomplete', is_flag=True, 
              help='Incluir resultados sem métricas completas')
@click.option('--min-samples', default=1, help='Número mínimo de amostras para incluir')
@click.option('--verbose', '-v', is_flag=True, help='Modo verboso')
@click.pass_context
def compare(ctx, results_dir, output, metric, auto_evaluate, include_incomplete, min_samples, verbose):
    """Comparar múltiplos resultados de classificação com avaliação automática"""
    
    if not verbose:
        verbose = ctx.obj.get('verbose', False)
    
    results_path = Path(results_dir)
    output_path = Path(output)
    output_path.mkdir(parents=True, exist_ok=True)
    
    click.echo(f"🔍 Comparando resultados em: {results_path}")
    click.echo(f"📊 Métrica principal: {metric}")
    
    if auto_evaluate:
        click.echo("🔬 Modo auto-avaliação ativado")
    if include_incomplete:
        click.echo("📋 Incluindo resultados incompletos")
    
    result_dirs = []
    for item in results_path.iterdir():
        if item.is_dir():
            has_predictions = bool(list(item.glob("**/predicted_*.csv")))
            has_metrics = bool(list(item.glob("**/metrics_summary.json")))
            
            if has_predictions or has_metrics:
                result_dirs.append(item)
                if verbose:
                    status = "✅ com métricas" if has_metrics else "📄 só predições"
                    click.echo(f"   {status}: {item.name}")
    
    if not result_dirs:
        click.echo("❌ Nenhum diretório de resultado encontrado")
        click.echo("   Estrutura esperada: cada subdiretório deve conter predicted_*.csv ou metrics_summary.json")
        return
    
    click.echo(f"📁 Encontrados {len(result_dirs)} diretórios de resultado")
    
    comparison_data = []
    
    for result_dir in result_dirs:
        run_name = result_dir.name
        
        if verbose:
            click.echo(f"\n🔄 Processando: {run_name}")
        
        metrics_files = list(result_dir.glob("**/metrics_summary.json"))
        prediction_files = list(result_dir.glob("**/predicted_*.csv"))
        
        run_data = {
            "run": run_name,
            "source": "unknown",
            "total_samples": 0,
            "has_metrics": len(metrics_files) > 0,
            "has_predictions": len(prediction_files) > 0
        }
        
        if metrics_files:
            metrics_file = metrics_files[0]
            try:
                with open(metrics_file, 'r') as f:
                    metrics = json.load(f)
                
                run_data.update(metrics)
                run_data["source"] = "existing_metrics"
                
                if verbose:
                    click.echo(f"   ✅ Métricas carregadas: {metrics.get(metric, 'N/A')}")
                
            except Exception as e:
                if verbose:
                    click.echo(f"   ⚠️ Erro ao ler métricas: {str(e)}")
        
        elif prediction_files:
            prediction_file = prediction_files[0]
            
            try:
                df = pd.read_csv(prediction_file)
                run_data["total_samples"] = len(df)
                run_data["source"] = "predictions_only"
                
                if "Predicted label" in df.columns:
                    predictions = df["Predicted label"].value_counts()
                    run_data["unique_predictions"] = len(predictions)
                    run_data["top_prediction"] = predictions.index[0] if len(predictions) > 0 else "N/A"
                
                if auto_evaluate and "Actual_Label" in df.columns and TEMetricsEvaluator:
                    if verbose:
                        click.echo(f"   🔬 Calculando métricas automaticamente...")
                    
                    try:
                        temp_metrics_dir = result_dir / "auto_metrics"
                        temp_metrics_dir.mkdir(exist_ok=True)
                        
                        evaluator = TEMetricsEvaluator()
                        metrics = evaluator.evaluate_predictions(
                            str(prediction_file), 
                            str(temp_metrics_dir)
                        )
                        
                        if isinstance(metrics, dict) and 'accuracy' in metrics:
                            numeric_metrics = {}
                            for key, value in metrics.items():
                                if isinstance(value, (int, float)) and not isinstance(value, bool):
                                    numeric_metrics[key] = value
                            
                            run_data.update(numeric_metrics)
                            run_data["source"] = "auto_evaluated"
                            
                            if verbose:
                                click.echo(f"   ✅ Auto-avaliação: {metrics.get(metric, 'N/A')}")
                        
                    except Exception as e:
                        if verbose:
                            click.echo(f"   ⚠️ Erro na auto-avaliação: {str(e)}")
                
                elif auto_evaluate and "Actual_Label" not in df.columns:
                    if verbose:
                        click.echo(f"   ⚠️ Sem labels verdadeiros para auto-avaliação")
                
            except Exception as e:
                if verbose:
                    click.echo(f"   ❌ Erro ao processar predições: {str(e)}")
                continue
        
        if run_data["total_samples"] < min_samples:
            if verbose:
                click.echo(f"   ⏩ Pulando: muito poucas amostras ({run_data['total_samples']})")
            continue
        
        if not include_incomplete and run_data["source"] in ["predictions_only"]:
            if verbose:
                click.echo(f"   ⏩ Pulando: sem métricas completas")
            continue
        
        comparison_data.append(run_data)
        
        if verbose:
            click.echo(f"   ✅ Adicionado à comparação")
    
    if not comparison_data:
        click.echo("❌ Nenhum resultado válido encontrado após filtros")
        click.echo("💡 Dicas:")
        click.echo("   - Use --include-incomplete para incluir resultados sem métricas")
        click.echo("   - Use --auto-evaluate para calcular métricas automaticamente") 
        click.echo("   - Verifique se os arquivos predicted_*.csv existem")
        return
    
    comparison_df = pd.DataFrame(comparison_data)
    
    comparison_file = output_path / "comparison_results.csv"
    comparison_df.to_csv(comparison_file, index=False)
    
    click.echo(f"\n📊 COMPARAÇÃO DE {len(comparison_data)} EXECUÇÕES:")
    click.echo("=" * 60)
    
    source_counts = comparison_df["source"].value_counts()
    click.echo("📋 Por tipo de dados:")
    for source, count in source_counts.items():
        source_labels = {
            "existing_metrics": "Com métricas existentes",
            "auto_evaluated": "Auto-avaliadas",
            "predictions_only": "Apenas predições"
        }
        label = source_labels.get(source, source)
        click.echo(f"   {label}: {count}")
    
    if metric in comparison_df.columns:
        metric_df = comparison_df[comparison_df[metric].notna()]
        
        if len(metric_df) > 0:
            metric_df_sorted = metric_df.sort_values(metric, ascending=False)
            
            click.echo(f"\n🏆 RANKING POR {metric.upper()}:")
            click.echo("-" * 40)
            for i, (_, row) in enumerate(metric_df_sorted.iterrows(), 1):
                metric_value = row[metric]
                source_icon = {"existing_metrics": "📊", "auto_evaluated": "🔬", "predictions_only": "📄"}.get(row["source"], "❓")
                click.echo(f"  {i:2d}. {source_icon} {row['run']:<20} : {metric_value:.4f}")
            
            metric_values = metric_df[metric]
            click.echo(f"\n📈 ESTATÍSTICAS DE {metric.upper()}:")
            click.echo(f"   Média: {metric_values.mean():.4f}")
            click.echo(f"   Mediana: {metric_values.median():.4f}")
            click.echo(f"   Desvio padrão: {metric_values.std():.4f}")
            click.echo(f"   Melhor: {metric_values.max():.4f}")
            click.echo(f"   Pior: {metric_values.min():.4f}")
        
        else:
            click.echo(f"\n⚠️ Nenhum resultado com métrica '{metric}' encontrado")
    
    else:
        click.echo(f"\n⚠️ Métrica '{metric}' não encontrada nos resultados")
        available_metrics = [col for col in comparison_df.columns if comparison_df[col].dtype in ['float64', 'int64']]
        if available_metrics:
            click.echo(f"📊 Métricas disponíveis: {', '.join(available_metrics[:5])}")
    
    click.echo(f"\n📋 RESUMO GERAL:")
    total_samples = comparison_df["total_samples"].sum()
    avg_samples = comparison_df["total_samples"].mean()
    
    click.echo(f"   Total de sequências processadas: {total_samples:,}")
    click.echo(f"   Média por execução: {avg_samples:.1f}")
    
    report_file = output_path / "comparison_report.txt"
    with open(report_file, 'w') as f:
        f.write(f"RELATÓRIO DE COMPARAÇÃO - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Total de execuções: {len(comparison_data)}\n")
        f.write(f"Métrica principal: {metric}\n\n")
        
        for _, row in comparison_df.iterrows():
            f.write(f"\nExecução: {row['run']}\n")
            f.write(f"Fonte: {row['source']}\n")
            f.write(f"Amostras: {row['total_samples']}\n")
            metric_cols = [col for col in row.index if col not in ["run", "source", "total_samples", "has_metrics", "has_predictions"]]
            for col in metric_cols:
                if pd.notna(row[col]):
                    f.write(f"  {col}: {row[col]:.4f}\n")
    
    click.echo(f"\n💾 ARQUIVOS GERADOS:")
    click.echo(f"   📊 {comparison_file}")
    click.echo(f"   📖 {report_file}")

    runs_without_metrics = len(comparison_df[comparison_df["source"] == "predictions_only"])
    if runs_without_metrics > 0:
        click.echo(f"\n💡 SUGESTÕES:")
        click.echo(f"   • {runs_without_metrics} execuções sem métricas completas")
        click.echo(f"   • Use --auto-evaluate para calcular automaticamente")
        click.echo(f"   • Ou execute 'evaluate' manualmente em cada resultado")