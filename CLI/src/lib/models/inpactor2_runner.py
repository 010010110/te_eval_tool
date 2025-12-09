import click
import subprocess
import shutil
import pandas as pd
from pathlib import Path
import os
import sys
import re


try:
    from lib.metrics_evaluator import TEMetricsEvaluator
    from lib.fasta_label_mapper import FASTALabelMapper
except ImportError:
    TEMetricsEvaluator = None
    FASTALabelMapper = None

class Inpactor2Runner:
    
    def __init__(self, python_path, model_file, input_file, output_dir, verbose=False, clean_temp=False, auto_label=False, skip_evaluation=False, **kwargs):
        self.python_path = python_path
        self.model_file = model_file
        self.input_file = input_file
        self.output_dir = output_dir
        self.verbose = verbose
        self.clean_temp = clean_temp
        self.auto_label = auto_label
        self.skip_evaluation = skip_evaluation
        
        if self.verbose:
            click.echo(f"🛠️ Inpactor2 Runner inicializado (Modo Não-Invasivo).")

    def run(self):
        click.echo("⚙️ Preparando execução do Inpactor2...")
        
      
        TOOL_DIR = Path(self.model_file).resolve()
        REAL_SCRIPT_PATH = TOOL_DIR / "Inpactor2.py"
        
       
        WRAPPER_PATH = Path(__file__).parent / "inpactor_wrapper.py"
        
        
        BASE_SRC_DIR = Path(__file__).parents[2]
        TREE_FILE_PATH = BASE_SRC_DIR / 'nodes' / 'tree.txt'
        
        input_path = Path(self.input_file).resolve()
        output_path = Path(self.output_dir).resolve()
        output_path.mkdir(parents=True, exist_ok=True)
        
        temp_dir = output_path / "inpactor2_temp"
        temp_dir.mkdir(parents=True, exist_ok=True)

        if not REAL_SCRIPT_PATH.exists():
            click.echo(f"❌ Erro: Script original não encontrado em: {REAL_SCRIPT_PATH}")
            return False
            
        if not WRAPPER_PATH.exists():
            click.echo(f"❌ Erro: Wrapper não encontrado em: {WRAPPER_PATH}")
            return False

        
        sanitized_fasta_path = temp_dir / "input_sanitized.fasta"
        if self.verbose: click.echo(f"🧹 Sanitizando headers e limpando nucleotídeos...")
        
        original_ids_map = {}
        try:
            with open(input_path, 'r') as f_in, open(sanitized_fasta_path, 'w') as f_out:
                for line in f_in:
                    line = line.strip()
                    if not line: continue
                    if line.startswith(">"):
                        original_header = line[1:]
                        original_id = original_header.split()[0]
                        sanitized_id = original_id.replace('|', '_').replace('#', '_').replace(':', '_')
                        original_ids_map[sanitized_id] = original_id
                        f_out.write(f">{sanitized_id}\n")
                    else:
                        clean_seq = re.sub(r'[^ACGTN]', 'N', line.upper())
                        f_out.write(clean_seq + "\n")
        except Exception as e:
            click.echo(f"❌ Erro ao sanitizar FASTA: {str(e)}")
            return False

        
        cmd = [
            self.python_path,
            str(WRAPPER_PATH),
            str(REAL_SCRIPT_PATH),
            "-f", str(sanitized_fasta_path),
            "-o", str(temp_dir),
            "-t", "4"
        ]

        if self.verbose: 
            click.echo(f"💻 Comando Wrapper: {' '.join(cmd)}")
            click.echo(f"📂 CWD: {TOOL_DIR}")

       
        try:
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                cwd=str(TOOL_DIR) 
            )
            
            if result.returncode != 0:
                click.echo(f"❌ Erro na execução do Inpactor2 (Exit Code: {result.returncode}):")
                click.echo("vvvvvvvvv LOG DE ERRO vvvvvvvvv")
                click.echo(result.stderr)
                click.echo("^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^")
                return False
                
            if self.verbose:
                click.echo("✅ Execução finalizada com sucesso.")

        except Exception as e:
            click.echo(f"❌ Falha ao iniciar subprocesso: {str(e)}")
            return False

       
        output_files = list(temp_dir.glob("*classification.tab")) + list(temp_dir.glob("*.tab")) + list(temp_dir.glob("*.csv"))
        raw_output_file = None
        candidates = [f for f in output_files if f.stat().st_size > 10 and f.name != "input_sanitized.fasta"] 
        if candidates:
            raw_output_file = max(candidates, key=lambda p: p.stat().st_mtime)
        
        results = []
        
        if not raw_output_file:
            if "There is no LTR retrotransposons" in result.stdout:
                click.echo("⚠️ Aviso: O Inpactor2 rodou com sucesso, mas não encontrou LTRs válidos.")
                click.echo("   Gerando CSV com 'Rejected_Inpactor2'.")
            else:
                click.echo(f"❌ Erro: Nenhum arquivo gerado e sem aviso claro de rejeição.")
                click.echo(f"--- STDOUT ---\n{result.stdout[-1000:]}")
                return False
        else:
            click.echo(f"🔄 Processando resultados de: {raw_output_file.name}")
            try:
                with open(raw_output_file, 'r') as f:
                    for line in f:
                        if line.startswith("#") or not line.strip(): continue
                        parts = line.strip().split('\t')
                        if len(parts) >= 2:
                            s_id = parts[0].strip().lstrip('>')
                            raw_label = parts[2] if len(parts) > 2 else parts[1]
                            pred_label = raw_label.split('(')[0].strip()
                            score = 1.0 
                            orig_id = original_ids_map.get(s_id, s_id)
                            results.append({
                                'Sequence ID': orig_id,
                                'Predicted label': pred_label,
                                'Final_Confidence_Score': score
                            })
            except Exception as e:
                click.echo(f"❌ Erro ao ler tabela: {e}")
                return False

       
        final_df = pd.DataFrame(results)
        all_ids_df = pd.DataFrame({'Sequence ID': list(original_ids_map.values())})
        
        if not final_df.empty:
            final_df = pd.merge(all_ids_df, final_df, on='Sequence ID', how='left')
        else:
            final_df = all_ids_df
            final_df['Predicted label'] = None
            final_df['Final_Confidence_Score'] = 0.0

        final_df['Predicted label'] = final_df['Predicted label'].fillna('Rejected_Inpactor2')
        final_df['Final_Confidence_Score'] = final_df['Final_Confidence_Score'].fillna(0.0)

        final_file = output_path / "predicted_results.csv"
        final_df.to_csv(final_file, index=False)
        click.echo(f"📊 Resultados salvos em: {final_file}")

    
        if not TREE_FILE_PATH.exists():
            click.echo(f"⚠️ Aviso: Arquivo de hierarquia não encontrado em: {TREE_FILE_PATH}")
            click.echo("   Algumas métricas hierárquicas e mapeamentos podem falhar.")

        if self.auto_label and FASTALabelMapper:
            click.echo(f"\n🏷️  Mapeando labels verdadeiros...")
            try:
                
                mapper = FASTALabelMapper(tree_file=str(TREE_FILE_PATH))
                mapper.add_actual_labels_to_predictions(str(final_file), str(input_path))
            except Exception as e:
                click.echo(f"⚠️ Erro no mapeamento: {e}")

        if not self.skip_evaluation and TEMetricsEvaluator and final_file.exists():
            click.echo(f"\n🔬 Executando avaliação de métricas...")
            try:
                
                evaluator = TEMetricsEvaluator(hierarchy_file=str(TREE_FILE_PATH))
                evaluator.evaluate_predictions(str(final_file), str(output_path))
            except Exception as e:
                click.echo(f"⚠️ Erro na avaliação: {e}")

        if self.clean_temp:
            click.echo("🧹 Limpando arquivos temporários...")
            shutil.rmtree(temp_dir)

        return True