# fasta_label_mapper.py - Mapeamento automático de headers FASTA para códigos hierárquicos
import pandas as pd
from pathlib import Path
import re
import sys 
import json 

class FASTALabelMapper:
    """
    Mapeia headers FASTA para códigos hierárquicos usando arquivos de configuração externos.
    """
    
    def __init__(self, base_dir=None, tree_file="nodes/tree.txt", config_file="mapper_config.json"):
        """
        Inicializa o mapper, carregando a hierarquia e as regras de inferência.
        """
        if base_dir:
            # Se um base_dir foi explicitamente fornecido
            base_path = Path(base_dir).resolve()
        else:
            # Tenta encontrar a raiz subindo a partir deste script
            try:
                script_path = Path(__file__).resolve()
                # Sobe 3 níveis se estiver em src/lib, ou usa o diretório atual se estiver na raiz
                # Ajuste conforme a localização real do arquivo
                if (script_path.parent / "nodes").exists():
                    base_path = script_path.parent
                else:
                    base_path = Path.cwd() 
            except NameError:
                 base_path = Path.cwd()

        self.project_root = base_path 

        # 1. Carregar tree.txt
        tree_path = Path(tree_file)
        self.tree_file = tree_path if tree_path.is_absolute() else (self.project_root / tree_file).resolve()
        self.hierarchy_map = self._load_hierarchy() # Mapa: '1.1.1' -> 'Copia'
        self.label_to_code = {label.lower(): code for code, label in self.hierarchy_map.items()} # Mapa: 'copia' -> '1.1.1'
        
        # 2. Carregar mapper_config.json
        config_path = Path(config_file)
        self.config_file = config_path if config_path.is_absolute() else (self.project_root / config_file).resolve()
        self._load_config() # Carrega self.special_mappings e self.inference_patterns

    def _load_hierarchy(self):
        """Carrega o mapeamento código -> label do arquivo tree.txt."""
        hierarchy = {}
        try:
            with open(self.tree_file, 'r') as f:
                for line in f:
                    if ',' in line:
                        code, label = line.strip().split(',', 1)
                        hierarchy[code.strip()] = label.strip()
            print(f"    - Hierarquia 'tree.txt' carregada de: {self.tree_file}")
        except FileNotFoundError:
            print(f"⚠️  Arquivo de hierarquia não encontrado em: {self.tree_file}.")
            print("   O mapeamento para códigos numéricos pode ser limitado.")
        return hierarchy
        
    def _load_config(self):
        """Carrega as regras de mapeamento do arquivo JSON."""
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
            self.special_mappings = config.get("special_mappings", {})
            self.inference_patterns = config.get("inference_patterns", {})
            print(f"    - Regras de inferência carregadas de: {self.config_file}")
        except FileNotFoundError:
            print(f"⚠️  Arquivo de configuração '{self.config_file}' não encontrado.")
            self.special_mappings = {}
            self.inference_patterns = {}
        except json.JSONDecodeError:
            print(f"❌ Erro: O arquivo '{self.config_file}' contém um JSON inválido.")
            sys.exit(1)
    
    def parse_fasta_header(self, header):
        """
        Extrai informações estruturadas do header FASTA.
        Suporta múltiplos formatos, como Delimitado por '|' ou '#'.
        """
        clean_header = header.lstrip('>')
        
        # Estratégia 1: Tentar dividir por '#' (comum no Repbase)
        if '#' in clean_header:
            parts = clean_header.split('#')
            seq_id = parts[0]
            classification_part = parts[1].split()[0] 
            
            if classification_part and 'unknown' not in classification_part.lower():
                class_parts = classification_part.split('/')
                return {
                    'seq_id': seq_id,
                    'class_level': class_parts[0] if len(class_parts) > 0 else 'Unknown',
                    'order_level': class_parts[1] if len(class_parts) > 1 else class_parts[0],
                    'family_level': class_parts[-1]
                }

        # Estratégia 2: Tentar dividir por '|' (formatos longos)
        parts = clean_header.split('|')
        if len(parts) >= 4:
            return {'seq_id': parts[0], 'class_level': parts[1], 'order_level': parts[2], 'family_level': parts[3]}
        if len(parts) == 3:
            return {'seq_id': parts[0], 'class_level': parts[1], 'order_level': parts[2], 'family_level': parts[2]}
            
        # Estratégia 3: Capturar o formato [ID]|[CODE]
        if len(parts) == 2 and re.match(r'^[0-9\.]+$', parts[1]):
            code = parts[1]
            label = self.hierarchy_map.get(code, 'Unknown') 
            if label != 'Unknown':
                return {'seq_id': parts[0], 'class_level': label, 'order_level': label, 'family_level': label}
            
        # Estratégia 4: Inferir do nome (fallback)
        seq_id = clean_header.split()[0].split('|')[0].split('#')[0]
        inferred = self._infer_classification_from_name(seq_id)
        return {'seq_id': seq_id, **inferred}

    def _infer_classification_from_name(self, seq_name):
        """
        Infere a classificação a partir do nome da sequência usando padrões do config.
        """
        seq_lower = seq_name.lower()
        
        # Usa os padrões carregados do JSON
        for pattern, classification in self.inference_patterns.items():
            if re.search(r'\b' + re.escape(pattern) + r'\b', seq_lower):
                return classification
        for pattern, classification in self.inference_patterns.items():
            if pattern in seq_lower:
                return classification

        if 'dna' in seq_lower:
             return {'class_level': 'ClassII', 'order_level': 'Unknown', 'family_level': 'Unknown'}

        return {'class_level': 'Unknown', 'order_level': 'Unknown', 'family_level': 'Unknown'}
    
    def map_to_hierarchical_code(self, parsed_header):
        """
        Mapeia um header já processado para o código hierárquico correspondente.
        """
        family_norm = self._normalize_label(parsed_header['family_level'])
        order_norm = self._normalize_label(parsed_header['order_level'])
        class_norm = self._normalize_label(parsed_header['class_level'])
        
        # Usa os mapeamentos carregados do JSON
        for label in [family_norm, order_norm, class_norm]:
            if label in self.special_mappings:
                return self.special_mappings[label]
            code = self._find_code_for_label(label)
            if code:
                return code
        return None
    
    def _normalize_label(self, label):
        if not label or label == 'Unknown':
            return ''
        return re.sub(r'[^a-zA-Z0-9]', '', label.lower())
    
    def _find_code_for_label(self, normalized_label):
        if not normalized_label:
            return None
        return self.label_to_code.get(normalized_label)
    
    def process_fasta_file(self, fasta_file, output_csv=None):
        fasta_path = Path(fasta_file).resolve()
        mappings = []
        try:
            with open(fasta_path, 'r') as f:
                for line in f:
                    if line.startswith('>'):
                        header = line.strip()
                        parsed = self.parse_fasta_header(header)
                        hierarchical_code = self.map_to_hierarchical_code(parsed)
                        hierarchical_label = self.hierarchy_map.get(str(hierarchical_code), 'Unknown') if hierarchical_code else 'Unknown'
                        mappings.append({
                            'sequence_id': parsed['seq_id'],
                            'original_header': header,
                            'class_level': parsed['class_level'],
                            'order_level': parsed['order_level'],
                            'family_level': parsed['family_level'],
                            'hierarchical_code': hierarchical_code,
                            'hierarchical_label': hierarchical_label,
                            'mapping_success': hierarchical_code is not None
                        })
        except FileNotFoundError:
            print(f"❌ Arquivo FASTA não encontrado em: {fasta_path}")
            return pd.DataFrame()
        
        df = pd.DataFrame(mappings)
        if output_csv:
            output_path = Path(output_csv)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(output_csv, index=False)
            print(f"📄 Mapeamentos salvos em: {output_csv}")
        return df

    def validate_mapping(self, fasta_file):
        print(f"🔍 Validando mapeamentos para: {fasta_file}")
        print("=" * 50)
        mappings_df = self.process_fasta_file(fasta_file)
        if mappings_df.empty:
            print("❌ Nenhum mapeamento encontrado.")
            return
        total = len(mappings_df)
        successful = mappings_df['mapping_success'].sum()
        failed = total - successful
        print(f"📊 ESTATÍSTICAS GERAIS:")
        print(f"   Total de sequências: {total}")
        print(f"   Mapeamentos bem-sucedidos: {successful} ({successful/total*100:.1f}%)")
        print(f"   Mapeamentos com falha: {failed} ({failed/total*100:.1f}%)")
        if successful > 0:
            print(f"\n🎯 CÓDIGOS HIERÁRQUICOS MAPEADOS (Top 5):")
            code_dist = mappings_df['hierarchical_code'].value_counts().head()
            for code, count in code_dist.items():
                label = self.hierarchy_map.get(str(code), 'Unknown')
                print(f"   {code} ({label}): {count} sequências")
        if failed > 0:
            print(f"\n❌ EXEMPLOS DE MAPEAMENTOS QUE FALHARAM (Top 10):")
            failed_mappings = mappings_df[~mappings_df['mapping_success']]
            for _, row in failed_mappings.head(10).iterrows():
                print(f"   Header: {row['original_header']}")
    
    def add_actual_labels_to_predictions(self, absolute_predictions_csv_path, absolute_fasta_path, base_dir_ignored=None):
        """
        Adiciona as colunas 'Actual_Label' e 'Actual_Label_Code' (do FASTA) 
        ao arquivo CSV de predições. Gera o formato final exigido.
        """
        
        fasta_path = Path(absolute_fasta_path)
        pred_path = Path(absolute_predictions_csv_path)
        
        print(f"    - Lendo FASTA de referência: {fasta_path}")
        print(f"    - Lendo arquivo de predições: {pred_path}")
        
        # 1. Criar gabarito a partir do FASTA
        mappings = []
        try:
            with open(fasta_path, 'r') as f:
                for line in f:
                    if line.startswith('>'):
                        header = line.strip()
                        seq_id_for_merge = header[1:].split()[0] # Pega ID até o espaço
                        
                        parsed = self.parse_fasta_header(header)
                        actual_code = self.map_to_hierarchical_code(parsed)
                        actual_label = self.hierarchy_map.get(str(actual_code), 'Unknown') if actual_code else 'Unknown'
                        
                        mappings.append({
                            'Sequence ID': seq_id_for_merge, 
                            'Actual_Code': actual_code if actual_code else '0',
                            'Actual_Label': actual_label
                        })
        except FileNotFoundError:
            print(f"❌ Erro: Arquivo FASTA de referência não encontrado em: {fasta_path}")
            return False
        
        if not mappings:
            print(f"❌ Erro: Nenhum dado lido do FASTA de referência: {fasta_path}")
            return False

        actual_labels_df = pd.DataFrame(mappings)
        
        # 2. Ler predições e fazer o Merge
        if not pred_path.exists():
            print(f"❌ Erro: Arquivo de predições não encontrado em: {pred_path}")
            return False
            
        try:
            pred_df = pd.read_csv(pred_path)
            
            # Normalizar nome da coluna de ID
            if 'id' in pred_df.columns:
                pred_df = pred_df.rename(columns={'id': 'Sequence ID'})
            if 'Predicted_Label_Name' in pred_df.columns:
                pred_df = pred_df.rename(columns={'Predicted_Label_Name': 'Predicted label'})
            
            # Garantir que Sequence ID seja string para o merge
            pred_df['Sequence ID'] = pred_df['Sequence ID'].astype(str)
            actual_labels_df['Sequence ID'] = actual_labels_df['Sequence ID'].astype(str)
            
            # Merge
            merged_df = pd.merge(pred_df, actual_labels_df, on='Sequence ID', how='left')
            
            # Preencher vazios
            merged_df['Actual_Label'] = merged_df['Actual_Label'].fillna('Unknown')
            merged_df['Actual_Code'] = merged_df['Actual_Code'].fillna('0')
            
            # 3. Gerar Colunas de Código Predito
            def get_pred_code(label):
                if not label or pd.isna(label): return '0'
                return self.label_to_code.get(label.lower(), '0')
            
            # Se a coluna 'Predicted label' não existir, cria como Unknown
            if 'Predicted label' not in merged_df.columns:
                 merged_df['Predicted label'] = 'Unknown'

            merged_df['Predicted_Code'] = merged_df['Predicted label'].apply(get_pred_code)
            
            # Predicted_Path_Codes (Assume que é o mesmo que o Code)
            merged_df['Predicted_Path_Codes'] = merged_df['Predicted_Code']
            
            # Garantir Final_Confidence_Score
            if 'Final_Confidence_Score' not in merged_df.columns:
                merged_df['Final_Confidence_Score'] = 0.0
            
            # 4. Reordenar e Salvar (Formato Exigido)
            cols_order = [
                'Sequence ID', 
                'Predicted label', 
                'Final_Confidence_Score', 
                'Predicted_Code', 
                'Predicted_Path_Codes', 
                'Actual_Code', 
                'Actual_Label'
            ]
            
            # Seleciona apenas as colunas que existem
            final_cols = [c for c in cols_order if c in merged_df.columns]
            final_df = merged_df[final_cols]
            
            final_df.to_csv(pred_path, index=False)
            print(f"    - CSV padronizado e salvo em: {pred_path}")
            return True
            
        except Exception as e:
            print(f"❌ Erro ao processar CSV: {e}")
            return False

def main():
    if len(sys.argv) < 2:
        print("Uso:")
        print("  python fasta_label_mapper.py validate <arquivo.fasta>")
        print("  python fasta_label_mapper.py process <arquivo.fasta> [output.csv]")
        return
    
    command = sys.argv[1]
    mapper = FASTALabelMapper(base_dir=None) 
    
    if command == 'validate':
        if len(sys.argv) < 3:
            print("Erro: Forneça o caminho para o arquivo FASTA.")
            return
        fasta_file = sys.argv[2]
        mapper.validate_mapping(fasta_file)
        
    elif command == 'process':
        if len(sys.argv) < 3:
            print("Erro: Forneça o caminho para o arquivo FASTA.")
            return
        fasta_file = sys.argv[2]
        output_csv = sys.argv[3] if len(sys.argv) > 3 else f"{Path(fasta_file).stem}_mappings.csv"
        mapper.process_fasta_file(fasta_file, output_csv)
        
    else:
        print(f"❌ Comando não reconhecido: {command}")

if __name__ == "__main__":
    print("--- EXECUTANDO VERSÃO ATUALIZADA DO MAPPER ---")
    main()
