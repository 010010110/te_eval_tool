import click
import subprocess
import shutil
import pandas as pd
from pathlib import Path
import os


try:
    from fasta_label_mapper import FASTALabelMapper
except ImportError:
    FASTALabelMapper = None

try:
    from metrics_evaluator import TEMetricsEvaluator
except ImportError:
    TEMetricsEvaluator = None

class YoroRunner:

    
    def __init__(self, python_path, input_file, output_dir, verbose=False, clean_temp=False, auto_label=False, skip_evaluation=False):
        self.python_path = python_path
        self.input_file = input_file
        self.output_dir = output_dir
        self.verbose = verbose
        self.clean_temp = clean_temp
        self.auto_label = auto_label
        self.skip_evaluation = skip_evaluation

    def run(self):
        
        
        click.echo("⚙️ Executando YORO...")
        
        input_path = Path(self.input_file).resolve()
        output_path = Path(self.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        temp_dir = output_path / "yoro_temp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        script_path = "YORO-master/pipelineDomain.py"
        if not Path(script_path).exists():
            click.echo(f" Erro: Script 'pipelineDomain.py' nao encontrado em: YORO-master/")
            return False

        model_path = Path("YORO-master/models/AAqqYOLOqqdomainqqV25.hdf5").resolve()
        if not model_path.exists():
            click.echo(f"Erro: Modelo YORO nao encontrado em: {model_path}")
            return False

        
        sanitized_fasta_path = temp_dir / "sanitized_input.fasta"
        if self.verbose: click.echo(f"Sanitizando arquivo FASTA para o YORO...")
        
        original_ids = []
        try:
            with open(input_path, 'r') as f_in, open(sanitized_fasta_path, 'w') as f_out:
                for line in f_in:
                    if line.startswith(">"):
                        original_header = line.strip()[1:]
                        original_id = original_header.split()[0] 
                        sanitized_id = original_id.replace('#', '_').replace('|', '_')
                        original_ids.append(original_id)
                        
                        rest_of_header = line.strip()[1:].partition(' ')[2]
                        if rest_of_header: f_out.write(f">{sanitized_id} {rest_of_header}\n")
                        else: f_out.write(f">{sanitized_id}\n")
                    else:
                        f_out.write(line)
        except Exception as e:
            click.echo(f"Erro ao sanitizar FASTA: {e}")
            return False

        # Executa modelo
        cmd_classify = [
            self.python_path,
            script_path,
            "-f", str(sanitized_fasta_path),
            "-d", str(temp_dir),
            "-m", str(model_path)
        ]
        
        if self.verbose: click.echo(f"  Comando: {' '.join(cmd_classify)}")

        result = subprocess.run(cmd_classify, capture_output=True, text=True, cwd=Path.cwd())
        
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
                base_dir = str(Path.cwd())
                mapper = FASTALabelMapper(base_dir=base_dir) 
                
                map_success = mapper.add_actual_labels_to_predictions(
                    str(final_file.resolve()), 
                    str(Path(self.input_file).resolve())
                )
                if map_success: click.echo("✅ Labels mapeados com sucesso!")
                else: click.echo("⚠️ Falha no mapeamento de labels.")
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
