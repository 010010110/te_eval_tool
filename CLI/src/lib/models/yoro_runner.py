import click
import subprocess
import shutil
import pandas as pd
from pathlib import Path
import os

from lib.metrics_evaluator import TEMetricsEvaluator
from lib.fasta_label_mapper import FASTALabelMapper

class YORORunner:

    
    def __init__(self, python_path, model_file, input_file, output_dir, verbose=False, clean_temp=False, auto_label=False, skip_evaluation=False,
                 window=50000, threads=None, threshold=0.8, cycles=1):
        self.python_path = python_path
        self.model_file = model_file
        self.input_file = input_file
        self.output_dir = output_dir
        self.verbose = verbose
        self.clean_temp = clean_temp
        self.auto_label = auto_label
        self.skip_evaluation = skip_evaluation
        # YORO-specific runtime options
        self.window = window
        self.threads = threads
        self.threshold = threshold
        self.cycles = cycles
        
        if self.verbose:
            click.echo(f"🛠️ YORO Runner configurado com modelo: {self.model_file}")

    def run(self):
              
        click.echo("⚙️ Executando YORO...")
        YORO_BASE_DIR = Path(__file__).parent.parent.parent / "models" / "YORO"
        
        input_path = Path(self.input_file).resolve()
        output_path = Path(self.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        temp_dir = output_path / "yoro_temp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        script_path = YORO_BASE_DIR / "pipelineDomain.py"
        if not Path(script_path).exists():
            click.echo(f" Erro: Script 'pipelineDomain.py' nao encontrado em: YORO-master/")
            return False

        model_path = Path(self.model_file).resolve()
        
        if not script_path.exists():
            click.echo(f"❌ Erro: Script 'pipelineDomain.py' nao encontrado em: {script_path.parent}")
            return False
        
        if not model_path.exists():
            click.echo(f"❌ Erro: Modelo YORO nao encontrado em: {model_path}")
            return False

        
        sanitized_fasta_path = temp_dir / "sanitized_input.fasta"
        if self.verbose: click.echo(f"Sanitizando arquivo FASTA para o YORO...")
        
        original_ids = []
        try:
            with open(input_path, 'r') as f_in, open(sanitized_fasta_path, 'w') as f_out:
                for line in f_in:
                    if line.startswith(">"):
                        # Store the full header (without '>')
                        original_header = line.strip()[1:]
                        original_ids.append(original_header)
                        
                        # Sanitize only the first token for YORO compatibility
                        first_token = original_header.split()[0]
                        sanitized_id = first_token.replace('#', '_').replace('|', '_')
                        
                        rest_of_header = line.strip()[1:].partition(' ')[2]
                        if rest_of_header: f_out.write(f">{sanitized_id} {rest_of_header}\n")
                        else: f_out.write(f">{sanitized_id}\n")
                    else:
                        f_out.write(line)
        except Exception as e:
            click.echo(f"Erro ao sanitizar FASTA: {e}")
            return False

        # Use absolute paths for command arguments so the subprocess resolves
        # files correctly even when we change cwd.
        sanitized_fasta_abs = str(sanitized_fasta_path.resolve())
        temp_dir_abs = str(temp_dir.resolve())
        script_path_abs = str(script_path.resolve())

        cmd_classify = [
            self.python_path,
            script_path_abs,
            "-f", sanitized_fasta_abs,
            "-d", temp_dir_abs,
            "-m", str(model_path),
        ]

        # Append YORO-specific flags understood by pipelineDomain.py
        try:
            if self.window is not None:
                cmd_classify.extend(["-w", str(int(self.window))])
        except Exception:
            pass

        if self.threads is not None:
            cmd_classify.extend(["-p", str(int(self.threads))])

        if self.threshold is not None:
            cmd_classify.extend(["-t", str(float(self.threshold))])

        if self.cycles is not None:
            cmd_classify.extend(["-c", str(int(self.cycles))])
        
        if self.verbose: click.echo(f"  Comando: {' '.join(cmd_classify)}")

        test_dir = temp_dir / "test"
        test_dir.mkdir(parents=True, exist_ok=True)

        result = subprocess.run(cmd_classify, capture_output=True, text=True, cwd=temp_dir_abs)
        
        if result.returncode != 0:
            click.echo(f"Erro na classificacao do YORO:")
            if self.verbose:
                click.echo(f"  STDOUT: {result.stdout}")
                click.echo(f"  STDERR: {result.stderr}")
            return False
            
        yoro_output_file = temp_dir / "output.tab"
        if not yoro_output_file.exists():
            click.echo(f"Erro: Arquivo de saida do YORO nao encontrado.")
            return False
            
        click.echo(f"Saida tabular do YORO gerada.")

        # padronizar
        click.echo("Convertendo para CSV...")
        try:
            yoro_df = pd.read_csv(yoro_output_file, sep='\t')
            yoro_df.columns = yoro_df.columns.str.replace('|', '', regex=False).str.strip()
            for col in yoro_df.columns:
                if yoro_df[col].dtype == object:
                    yoro_df[col] = yoro_df[col].astype(str).str.replace('|', '', regex=False).str.strip()

            if 'ProbabilityClass' in yoro_df.columns:
                best_predictions = yoro_df.loc[yoro_df.groupby('id')['ProbabilityClass'].idxmax()]
            else:
                best_predictions = yoro_df.groupby('id').first().reset_index()
                best_predictions['ProbabilityClass'] = 0.0
            
            final_df = best_predictions[['id', 'Class', 'ProbabilityClass']].copy()
            final_df.columns = ['sanitized_id', 'Predicted label', 'Final_Confidence_Score']
            final_df['sanitized_id'] = final_df['sanitized_id'].astype(str).str.lstrip('>')
            
            master_df = pd.DataFrame({
                'Sequence ID': original_ids,
                'sanitized_id': [id.replace('#', '_').replace('|', '_') for id in original_ids]
            })
            
            merged_df = pd.merge(master_df, final_df, on='sanitized_id', how='left')
            merged_df['Predicted label'] = merged_df['Predicted label'].fillna('Unknown_YORO')
            merged_df['Final_Confidence_Score'] = merged_df['Final_Confidence_Score'].fillna(0.0)
            
            final_csv_df = merged_df[['Sequence ID', 'Predicted label', 'Final_Confidence_Score']]
            
            final_file = output_path / "predicted_results.csv"
            final_csv_df.to_csv(final_file, index=False)
            
            click.echo(f"📊 Resultados convertidos e salvos em: {final_file}")

        except Exception as e:
            click.echo(f"Erro ao converter saida do YORO: {e}")
            return False

        # Avaliacao
        
        if self.auto_label and FASTALabelMapper:
            click.echo(f"\n🏷️  Mapeando labels automaticamente...")
            try:
                # Provide the mapper with the correct tree.txt path inside CLI/src/nodes
                tree_file = Path(__file__).parents[2] / 'nodes' / 'tree.txt'
                mapper = FASTALabelMapper(tree_file=str(tree_file))

                # Call mapper to update the CSV file
                mapper.add_actual_labels_to_predictions(
                    str(final_file.resolve()),
                    str(Path(self.input_file).resolve()),
                    output_csv=str(final_file.resolve())
                )

                df_check = pd.read_csv(final_file)
                if 'Actual_Label' in df_check.columns and df_check['Actual_Label'].notna().any():
                    actual_count = df_check['Actual_Label'].notna().sum()
                    click.echo(f"✅ Labels mapeados com sucesso! {actual_count} valores preenchidos")
                else:
                    click.echo("⚠️ Falha no mapeamento de labels.")
            except Exception as e:
                click.echo(f"⚠️ Erro no mapeamento automático: {str(e)}")
        
        if not self.skip_evaluation and TEMetricsEvaluator and final_file.exists():
            click.echo(f"\n🔬 Executando avaliação automática...")
            try:
                evaluator = TEMetricsEvaluator()
                evaluator.evaluate_predictions(str(final_file), str(output_path))
                click.echo("✅ Avaliação automática concluída!")
            except Exception as e:
                click.echo(f"⚠️ Erro na avaliação automática: {str(e)}")

        if self.clean_temp:
            click.echo("🧹 Limpando arquivos temporários do YORO...")
            shutil.rmtree(temp_dir)

        return True