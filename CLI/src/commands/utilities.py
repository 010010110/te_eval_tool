import click
import sys
import os
import shutil
import json
import pandas as pd
from pathlib import Path
from datetime import datetime

try:
    from lib.env_manager import EnvironmentManager
except ImportError:
    EnvironmentManager = None

try:
    from lib.metrics_evaluator import TEMetricsEvaluator
except ImportError:
    TEMetricsEvaluator = None

@click.command('diagnose')
@click.option('--results-dir', required=True, type=click.Path(exists=True),
              help='Diretório com resultados para diagnosticar')
@click.option('--fix', is_flag=True, help='Tentar corrigir problemas automaticamente')
@click.option('--verbose', '-v', is_flag=True, help='Modo verboso')
@click.pass_context
def diagnose(ctx, results_dir, fix, verbose):
    """Diagnosticar problemas em diretórios de resultados"""
    
    if not verbose:
        verbose = ctx.obj.get('verbose', False)
    
    results_path = Path(results_dir)
    click.echo(f"🔍 Diagnosticando: {results_path}")
    
    issues = []
    fixable_issues = []
    
    subdirs = [d for d in results_path.iterdir() if d.is_dir()]
    
    click.echo(f"\n📁 ESTRUTURA DE DIRETÓRIOS:")
    click.echo(f"   Encontrados {len(subdirs)} subdiretórios")
    
    for subdir in subdirs:
        click.echo(f"\n📂 {subdir.name}:")
        
        prediction_files = list(subdir.glob("**/predicted_*.csv"))
        metrics_files = list(subdir.glob("**/metrics_summary.json"))
        
        click.echo(f"   📄 Arquivos de predição: {len(prediction_files)}")
        click.echo(f"   📊 Arquivos de métricas: {len(metrics_files)}")
        
        if prediction_files:
            pred_file = prediction_files[0]
            click.echo(f"   📍 Predições: {pred_file.relative_to(results_path)}")
            
            try:
                df = pd.read_csv(pred_file)
                click.echo(f"   🔢 Linhas: {len(df)}")
                click.echo(f"   📋 Colunas: {list(df.columns)}")
                
                required_cols = ['Sequence ID', 'Predicted label']
                missing_cols = [col for col in required_cols if col not in df.columns]
                
                if missing_cols:
                    issue = f"{subdir.name}: Colunas obrigatórias faltando: {missing_cols}"
                    issues.append(issue)
                    click.echo(f"   ❌ {issue}")
                
                has_actual_labels = 'Actual_Label' in df.columns
                actual_label_count = 0
                if has_actual_labels:
                    actual_label_count = df['Actual_Label'].notna().sum()
                
                click.echo(f"   🏷️  Labels verdadeiros: {'Sim' if has_actual_labels else 'Não'}")
                if has_actual_labels:
                    click.echo(f"   📊 Labels válidos: {actual_label_count}/{len(df)}")
                    
                    if actual_label_count == 0:
                        issue = f"{subdir.name}: Labels verdadeiros vazios"
                        issues.append(issue)
                        click.echo(f"   ⚠️  Todos os labels verdadeiros estão vazios")
                    elif actual_label_count < len(df):
                        issue = f"{subdir.name}: Labels verdadeiros parcialmente vazios"
                        issues.append(issue)
                        click.echo(f"   ⚠️  Alguns labels verdadeiros estão vazios")
                
                if 'Predicted label' in df.columns:
                    pred_dist = df['Predicted label'].value_counts()
                    click.echo(f"   📈 Predições únicas: {len(pred_dist)}")
                    if len(pred_dist) > 0:
                        click.echo(f"   🔝 Mais comum: {pred_dist.index[0]} ({pred_dist.iloc[0]} vezes)")
                
                if has_actual_labels and actual_label_count > 0 and not metrics_files:
                    fixable_issue = {
                        'type': 'missing_metrics',
                        'dir': subdir,
                        'pred_file': pred_file,
                        'description': f"{subdir.name}: Tem labels verdadeiros mas sem métricas"
                    }
                    fixable_issues.append(fixable_issue)
                    click.echo(f"   🔧 CORRIGÍVEL: Pode calcular métricas automaticamente")
                
            except Exception as e:
                issue = f"{subdir.name}: Erro ao ler predições: {str(e)}"
                issues.append(issue)
                click.echo(f"   ❌ Erro ao ler arquivo: {str(e)}")
        
        else:
            issue = f"{subdir.name}: Nenhum arquivo de predição encontrado"
            issues.append(issue)
            click.echo(f"   ❌ Nenhum arquivo predicted_*.csv encontrado")
        
        if metrics_files:
            metrics_file = metrics_files[0]
            try:
                with open(metrics_file, 'r') as f:
                    metrics = json.load(f)
                click.echo(f"   ✅ Métricas carregadas: {len(metrics)} campos")
                
                key_metrics = ['accuracy', 'precision_macro', 'recall_macro', 'f1_macro']
                available_key_metrics = [m for m in key_metrics if m in metrics]
                click.echo(f"   📊 Métricas principais: {len(available_key_metrics)}/{len(key_metrics)}")
                
            except Exception as e:
                issue = f"{subdir.name}: Erro ao ler métricas: {str(e)}"
                issues.append(issue)
                click.echo(f"   ❌ Erro ao ler métricas: {str(e)}")
    
    click.echo(f"\n🔍 RESUMO DO DIAGNÓSTICO:")
    click.echo("=" * 40)
    
    if issues:
        click.echo(f"❌ {len(issues)} problemas encontrados:")
        for i, issue in enumerate(issues, 1):
            click.echo(f"   {i}. {issue}")
    else:
        click.echo("✅ Nenhum problema grave encontrado")
    
    if fixable_issues:
        click.echo(f"\n🔧 {len(fixable_issues)} problemas corrigíveis:")
        for i, issue in enumerate(fixable_issues, 1):
            click.echo(f"   {i}. {issue['description']}")
        
        if fix:
            click.echo(f"\n🛠️  APLICANDO CORREÇÕES:")
            
            for issue in fixable_issues:
                if issue['type'] == 'missing_metrics':
                    click.echo(f"   🔬 Calculando métricas para {issue['dir'].name}...")
                    
                    try:
                        if TEMetricsEvaluator:
                            evaluator = TEMetricsEvaluator()
                            metrics_dir = issue['dir'] / "auto_metrics"
                            metrics_dir.mkdir(exist_ok=True)
                            
                            metrics = evaluator.evaluate_predictions(
                                str(issue['pred_file']), 
                                str(metrics_dir)
                            )
                            
                            if isinstance(metrics, dict) and 'accuracy' in metrics:
                                click.echo(f"   ✅ Métricas calculadas: F1={metrics.get('f1_macro', 0):.3f}")
                            else:
                                click.echo(f"   ⚠️  Métricas calculadas mas incompletas")
                        else:
                            click.echo(f"   ❌ TEMetricsEvaluator não disponível")
                    
                    except Exception as e:
                        click.echo(f"   ❌ Erro ao calcular métricas: {str(e)}")
        
        elif not fix:
            click.echo(f"\n💡 Para corrigir automaticamente, use: --fix")
    
    click.echo(f"\n💡 SUGESTÕES:")
    
    dirs_without_metrics = len([d for d in subdirs if not list(d.glob("**/metrics_summary.json"))])
    if dirs_without_metrics > 0:
        click.echo(f"   • {dirs_without_metrics} diretórios sem métricas")
        click.echo(f"   • Execute: te_eval_cli.py evaluate --predictions <arquivo> --output <dir>")
    
    dirs_without_actual_labels = 0
    dirs_with_partial_labels = 0
    
    for subdir in subdirs:
        pred_files = list(subdir.glob("**/predicted_*.csv"))
        if pred_files:
            try:
                df = pd.read_csv(pred_files[0])
                if 'Actual_Label' not in df.columns:
                    dirs_without_actual_labels += 1
                elif df['Actual_Label'].isna().any():
                    dirs_with_partial_labels += 1
            except:
                pass
    
    if dirs_without_actual_labels > 0:
        click.echo(f"   • {dirs_without_actual_labels} diretórios sem labels verdadeiros")
        click.echo(f"   • Execute: te_eval_cli.py map-labels --fasta <arquivo> --predictions <csv>")
    
    if dirs_with_partial_labels > 0:
        click.echo(f"   • {dirs_with_partial_labels} diretórios com labels parciais")
        click.echo(f"   • Verifique o mapeamento automático de labels")
    
    if len(subdirs) > 1:
        click.echo(f"\n🔗 PARA COMPARAÇÃO:")
        if dirs_without_metrics == 0:
            click.echo(f"   te_eval_cli.py compare --results-dir {results_path}")
        else:
            click.echo(f"   te_eval_cli.py compare --results-dir {results_path} --auto-evaluate --include-incomplete")

    return issues, fixable_issues

@click.command('info')
@click.pass_context
def info(ctx):
    """Mostrar informações sobre a ferramenta e ambiente"""
    
    click.echo("🔬 TE Evaluation Tool v5.0.1")
    click.echo("=" * 40)
    
    click.echo(f"🐍 Python: {sys.version.split()[0]}")
    click.echo(f"📁 Diretório atual: {os.getcwd()}")
    
    modules_status = {
        "EnvironmentManager": EnvironmentManager is not None,
        "TEMetricsEvaluator": TEMetricsEvaluator is not None,
        "pandas": True,
        "click": True
    }
    
    click.echo(f"\n📦 Módulos disponíveis:")
    for module, available in modules_status.items():
        status = "✅" if available else "❌"
        click.echo(f"   {status} {module}")
    
    important_paths = [
        "./src/models/ClassifyTE/",
        "./src/models/ClassifyTE/generate_feature_file.py",
        "./src/models/ClassifyTE/evaluate.py",
        "./src/models/ClassifyTE/models/",
        "./src/nodes/tree.txt",
        "./src/nodes/node.txt"
    ]
    
    click.echo(f"\n📁 Estrutura do projeto:")
    for path in important_paths:
        exists = Path(path).exists()
        status = "✅" if exists else "❌"
        click.echo(f"   {status} {path}")
    
    models_dir = Path("./src/models/ClassifyTE/models")
    if models_dir.exists():
        model_files = list(models_dir.glob("*.pkl"))
        click.echo(f"\n🤖 Modelos encontrados ({len(model_files)}):")
        for model_file in model_files:
            click.echo(f"   📄 {model_file.name}")
    
    if EnvironmentManager:
        envs_dir = Path("./src/model_envs")
        if envs_dir.exists():
            env_dirs = [d for d in envs_dir.iterdir() if d.is_dir()]
            click.echo(f"\n🌍 Ambientes virtuais ({len(env_dirs)}):")
            for env_dir in env_dirs:
                python_path = env_dir / "bin" / "python"
                status = "✅" if python_path.exists() else "❌"
                click.echo(f"   {status} {env_dir.name}")

@click.command('clean')
@click.option('--target', type=click.Choice(['temp', 'envs', 'results', 'all']), 
              default='temp', help='O que limpar')
@click.confirmation_option(prompt='Confirma a limpeza?')
@click.pass_context
def clean(ctx, target):
    """Limpar arquivos temporários e caches"""
    
    verbose = ctx.obj.get('verbose', False)
    
    cleaned_items = []
    
    if target in ['temp', 'all']:
        temp_patterns = [
            "./src/models/ClassifyTE/features_*",
            "./src/models/ClassifyTE/data/*.csv",
            "./src/models/ClassifyTE/outputs/predicted_*"
        ]
        
        for pattern in temp_patterns:
            for temp_file in Path(".").glob(pattern):
                try:
                    if temp_file.is_dir():
                        shutil.rmtree(temp_file)
                    else:
                        temp_file.unlink()
                    cleaned_items.append(str(temp_file))
                    if verbose:
                        click.echo(f"🧹 Removido: {temp_file}")
                except Exception as e:
                    click.echo(f"⚠️ Erro ao remover {temp_file}: {str(e)}")
    
    if target in ['envs', 'all']:
        envs_dir = Path("./src/model_envs")
        if envs_dir.exists():
            try:
                shutil.rmtree(envs_dir)
                cleaned_items.append("./src/model_envs/")
                if verbose:
                    click.echo("🧹 Ambientes virtuais removidos")
            except Exception as e:
                click.echo(f"⚠️ Erro ao remover ambientes: {str(e)}")
    
    if target in ['results', 'all']:
        results_dir = Path("results")
        if results_dir.exists():
            try:
                shutil.rmtree(results_dir)
                cleaned_items.append("results/")
                if verbose:
                    click.echo("🧹 Resultados removidos")
            except Exception as e:
                click.echo(f"⚠️ Erro ao remover resultados: {str(e)}")
    
    if cleaned_items:
        click.echo(f"✅ Limpeza concluída: {len(cleaned_items)} itens removidos")
    else:
        click.echo("✅ Nada para limpar")

@click.command('examples')
def examples():
    """Mostrar exemplos de uso da ferramenta"""
    
    click.echo("🚀 EXEMPLOS DE USO - TE Evaluation Tool v5.0.1")
    click.echo("=" * 50)
    
    examples = [
        {
            "title": "Setup inicial",
            "commands": [
                "python3 te_eval_cli.py env setup",
                "python3 te_eval_cli.py info"
            ]
        },
        {
            "title": "Validação de arquivos",
            "commands": [
                "python3 te_eval_cli.py validate --input data/default_dataset.fasta",
                "python3 te_eval_cli.py validate --input data/default_dataset.fasta --detailed"
            ]
        },
        {
            "title": "Classificação básica",
            "commands": [
                "python3 te_eval_cli.py run --model classifyte --input data/default_dataset.fasta --output results/basic",
                "python3 te_eval_cli.py run --model classifyte --input data/default_dataset.fasta --output results/advanced --algorithm nllcpn --clean"
            ]
        },
        {
            "title": "Avaliação de métricas",
            "commands": [
                "python3 te_eval_cli.py evaluate --predictions results/basic/predicted_results.csv --output results/metrics",
                "python3 te_eval_cli.py evaluate --predictions results/basic/predicted_results.csv --output results/metrics --format json"
            ]
        },
        {
            "title": "Comparação de resultados",
            "commands": [
                "python3 te_eval_cli.py compare --results-dir results/ --output comparison",
                "python3 te_eval_cli.py compare --results-dir results/ --metric accuracy"
            ]
        },
        {
            "title": "Manutenção",
            "commands": [
                "python3 te_eval_cli.py clean --target temp",
                "python3 te_eval_cli.py env clean"
            ]
        }
    ]
    
    for example in examples:
        click.echo(f"\n📋 {example['title']}:")
        click.echo("-" * 30)
        for cmd in example['commands']:
            click.echo(f"  {cmd}")

@click.command('quickstart')
@click.option('--input', default='data/default_dataset.fasta', help='Arquivo FASTA para teste')
@click.pass_context
def quickstart(ctx, input):
    """Execução rápida para teste inicial"""
    
    click.echo("🚀 QUICKSTART - TE Evaluation Tool")
    click.echo("=" * 40)
    
    if not Path(input).exists():
        click.echo(f"❌ Arquivo não encontrado: {input}")
        click.echo("   Certifique-se de ter um arquivo FASTA válido")
        return
    
    steps = [
        f"python3 te_eval_cli.py validate --input {input}",
        f"python3 te_eval_cli.py run --model classifyte --input {input} --output quickstart_results",
        "python3 te_eval_cli.py evaluate --predictions quickstart_results/predicted_results.csv --output quickstart_results/metrics"
    ]
    
    click.echo("Executando pipeline completo:")
    for i, step in enumerate(steps, 1):
        click.echo(f"\n{i}. {step}")
        click.echo(f"   ⏳ Executando...")
    
    click.echo(f"\n✅ Pipeline quickstart definido!")
    click.echo(f"📁 Resultados serão salvos em: quickstart_results/")
    click.echo(f"\nPara executar manualmente, rode os comandos acima em sequência.")