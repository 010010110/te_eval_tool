# fasta_label_mapper.py - Mapeamento automático de headers FASTA para códigos hierárquicos
import pandas as pd
from pathlib import Path
import re

class FASTALabelMapper:
    """
    Mapeia headers FASTA para códigos hierárquicos usando tree.txt
    
    Suporta padrões como:
    >5S|ClassI|SINE|5S
    >AACOPIA1_I|ClassI|LTR|Copia
    >hAT-9_XT|ClassII|TIR|hAT
    >Gypsy-22_DPu-I|ClassI|LTR|Gypsy
    """
    
    def __init__(self, tree_file="src/nodes/tree.txt"):
        self.tree_file = tree_file
        self.hierarchy_map = self._load_hierarchy()
        self.label_to_code = {label.lower(): code for code, label in self.hierarchy_map.items()}
        
    def _load_hierarchy(self):
        """Carrega mapeamento código -> label do tree.txt"""
        hierarchy = {}
        
        try:
            with open(self.tree_file, 'r') as f:
                for line in f:
                    if ',' in line:
                        code, label = line.strip().split(',', 1)
                        hierarchy[code.strip()] = label.strip()
        except FileNotFoundError:
            print(f"⚠️ Arquivo tree.txt não encontrado: {self.tree_file}")
        
        return hierarchy
    
    def parse_fasta_header(self, header):
        """
        Extrai informações estruturadas do header FASTA
        
        Suporta múltiplos formatos:
        - >5S|ClassI|SINE|5S
        - >AACOPIA1_I|ClassI|LTR|Copia  
        - >ATRAN (nome simples)
        - >BEL-7_Adi-I (família no nome)
        - >hAT-236_Ami (família no nome)
        
        Returns:
            dict com seq_id, class_level, order_level, family_level
        """
        
        # Remover '>' se presente
        if header.startswith('>'):
            header = header[1:]
        
        # Dividir por '|'
        parts = header.split('|')
        
        if len(parts) >= 4:
            # Formato padrão: seq|class|order|family
            return {
                'seq_id': parts[0],
                'class_level': parts[1],
                'order_level': parts[2],
                'family_level': parts[3]
            }
        elif len(parts) >= 3:
            # Formato parcial: seq|class|order
            return {
                'seq_id': parts[0],
                'class_level': parts[1],
                'order_level': parts[2],
                'family_level': parts[2]
            }
        else:
            # Formato simples: apenas nome da sequência
            # Tentar extrair informações do nome
            seq_id = parts[0]
            inferred = self._infer_classification_from_name(seq_id)
            
            return {
                'seq_id': seq_id,
                'class_level': inferred['class_level'],
                'order_level': inferred['order_level'],
                'family_level': inferred['family_level']
            }
    
    def _infer_classification_from_name(self, seq_name):
        """
        Infere classificação a partir do nome da sequência
        
        Args:
            seq_name: Nome da sequência (ex: "ATRAN", "BEL-7_Adi-I", "hAT-236_Ami")
            
        Returns:
            dict com classificação inferida
        """
        
        seq_lower = seq_name.lower()
        
        # Padrões de reconhecimento baseados em nomes conhecidos
        classification_patterns = {
            # Retrotransposons - LTR
            'copia': {'class_level': 'ClassI', 'order_level': 'LTR', 'family_level': 'Copia'},
            'gypsy': {'class_level': 'ClassI', 'order_level': 'LTR', 'family_level': 'Gypsy'},
            'bel': {'class_level': 'ClassI', 'order_level': 'LTR', 'family_level': 'Bel-Pao'},
            'pao': {'class_level': 'ClassI', 'order_level': 'LTR', 'family_level': 'Bel-Pao'},
            'erv': {'class_level': 'ClassI', 'order_level': 'LTR', 'family_level': 'ERV'},
            
            # Retrotransposons - LINE
            'line': {'class_level': 'ClassI', 'order_level': 'LINE', 'family_level': 'L1'},
            'l1': {'class_level': 'ClassI', 'order_level': 'LINE', 'family_level': 'L1'},
            'rte': {'class_level': 'ClassI', 'order_level': 'LINE', 'family_level': 'RTE'},
            'jockey': {'class_level': 'ClassI', 'order_level': 'LINE', 'family_level': 'Jockey'},
            
            # Retrotransposons - SINE
            'sine': {'class_level': 'ClassI', 'order_level': 'SINE', 'family_level': 'tRNA'},
            '5s': {'class_level': 'ClassI', 'order_level': 'SINE', 'family_level': '5S'},
            '7sl': {'class_level': 'ClassI', 'order_level': 'SINE', 'family_level': '7SL'},
            'trna': {'class_level': 'ClassI', 'order_level': 'SINE', 'family_level': 'tRNA'},
            
            # DNA Transposons - TIR
            'hat': {'class_level': 'ClassII', 'order_level': 'TIR', 'family_level': 'hAT'},
            'tc1': {'class_level': 'ClassII', 'order_level': 'TIR', 'family_level': 'Tc1-Mariner'},
            'mariner': {'class_level': 'ClassII', 'order_level': 'TIR', 'family_level': 'Tc1-Mariner'},
            'mutator': {'class_level': 'ClassII', 'order_level': 'TIR', 'family_level': 'Mutator'},
            'cacta': {'class_level': 'ClassII', 'order_level': 'TIR', 'family_level': 'CACTA'},
            'piggyb': {'class_level': 'ClassII', 'order_level': 'TIR', 'family_level': 'PiggyBac'},
            'harbinger': {'class_level': 'ClassII', 'order_level': 'TIR', 'family_level': 'PIF-Harbinger'},
            'pif': {'class_level': 'ClassII', 'order_level': 'TIR', 'family_level': 'PIF-Harbinger'},
            
            # Elementos específicos
            'atran': {'class_level': 'ClassI', 'order_level': 'LTR', 'family_level': 'Copia'},  # ATRAN é um Copia
            'dtt': {'class_level': 'ClassII', 'order_level': 'TIR', 'family_level': 'hAT'},     # DTT pode ser hAT
        }
        
        # Buscar padrões no nome
        for pattern, classification in classification_patterns.items():
            if pattern in seq_lower:
                return classification
        
        # Padrões baseados em prefixos/sufixos
        if seq_lower.startswith('ltr'):
            return {'class_level': 'ClassI', 'order_level': 'LTR', 'family_level': 'LTR'}
        
        if 'hat' in seq_lower or seq_lower.startswith('hat'):
            return {'class_level': 'ClassII', 'order_level': 'TIR', 'family_level': 'hAT'}
        
        if 'bel' in seq_lower:
            return {'class_level': 'ClassI', 'order_level': 'LTR', 'family_level': 'Bel-Pao'}
        
        # Padrões para LTR genéricos
        if any(keyword in seq_lower for keyword in ['ltr', 'retro']):
            return {'class_level': 'ClassI', 'order_level': 'LTR', 'family_level': 'LTR'}

        # Padrões para os formatos verbosos do TERL (nova adição)
        if 'class i' in seq_lower and 'sine' in seq_lower:
            return {'class_level': 'ClassI', 'order_level': 'SINE', 'family_level': 'tRNA'}
        if 'class i' in seq_lower and 'copia' in seq_lower:
            return {'class_level': 'ClassI', 'order_level': 'LTR', 'family_level': 'Copia'}
        if 'class ii' in seq_lower and 'tc1-mariner' in seq_lower:
            return {'class_level': 'ClassII', 'order_level': 'TIR', 'family_level': 'Tc1-Mariner'}
        if 'class i' in seq_lower and 'erv' in seq_lower:
            return {'class_level': 'ClassI', 'order_level': 'LTR', 'family_level': 'ERV'} # Mapeamento ERV
        if 'class i' in seq_lower and 'gypsy' in seq_lower:
            return {'class_level': 'ClassI', 'order_level': 'LTR', 'family_level': 'Gypsy'}

        # Default para elementos não reconhecidos
        return {
            'class_level': 'Unknown',
            'order_level': 'Unknown', 
            'family_level': 'Unknown'
        }
    
    def map_to_hierarchical_code(self, parsed_header):
        """
        Mapeia header parseado para código hierárquico
        
        Args:
            parsed_header: Resultado de parse_fasta_header()
            
        Returns:
            Código hierárquico (ex: "1.1.1") ou None se não encontrado
        """
        
        class_level = parsed_header['class_level']
        order_level = parsed_header['order_level'] 
        family_level = parsed_header['family_level']
        
        # Estratégia de mapeamento hierárquico:
        # 1. Tentar mapear o nível mais específico (family)
        # 2. Se não encontrar, tentar order
        # 3. Se não encontrar, tentar class
        
        # Normalizar nomes para busca
        family_normalized = self._normalize_label(family_level)
        order_normalized = self._normalize_label(order_level)
        class_normalized = self._normalize_label(class_level)
        
        # 1. Tentar nível family primeiro (mais específico)
        code = self._find_code_for_label(family_normalized)
        if code:
            return code
            
        # 2. Tentar nível order
        code = self._find_code_for_label(order_normalized)
        if code:
            return code
            
        # 3. Tentar nível class
        code = self._find_code_for_label(class_normalized)
        if code:
            return code
        
        # 4. Mapeamentos especiais para casos comuns (expandido)
        special_mappings = {
            # Classes principais
            'classi': '1',           # ClassI -> Retrotransposon
            'classii': '2',          # ClassII -> DNA transposon
            'retrotransposon': '1',
            'dnatransposon': '2',
            'dna': '2',
            
            # Orders LTR
            'ltr': '1.1',           # LTR
            
            # Families LTR
            'copia': '1.1.1',       # Copia
            'gypsy': '1.1.2',       # Gypsy
            'belpao': '1.1.3',      # Bel-Pao
            'bel': '1.1.3',         # Bel-Pao
            'pao': '1.1.3',         # Pao
            'erv': '1.1.4',         # ERV
            
            # DIRS
            'dirs': '1.2',          # DIRS
            
            # LINE
            'line': '1.4',          # LINE
            'l1': '1.4.4',          # L1
            'rte': '1.4.2',         # RTE
            'jockey': '1.4.3',      # Jockey
            'r2': '1.4.1',          # R2
            'i': '1.4.5',           # I
            
            # SINE
            'sine': '1.5',          # SINE
            'trna': '1.5.1',        # tRNA
            '7sl': '1.5.2',         # 7SL
            '5s': '1.5.3',          # 5S
            
            # DNA Transposons
            'subclassi': '2.1',     # SubclassI
            'tir': '2.1.1',         # TIRS
            'tirs': '2.1.1',        # TIRS
            
            # TIR Families
            'tc1mariner': '2.1.1.1', # Tc1-Mariner
            'tc1': '2.1.1.1',       # Tc1-Mariner
            'mariner': '2.1.1.1',   # Tc1-Mariner
            'hat': '2.1.1.2',       # hAT
            'mutator': '2.1.1.3',   # Mutator
            'merlin': '2.1.1.4',    # Merlin
            'transib': '2.1.1.5',   # Transib
            'p': '2.1.1.6',         # P
            'piggybac': '2.1.1.7',  # PiggyBac
            'piggyb': '2.1.1.7',    # PiggyBac
            'pifharbinger': '2.1.1.8', # PIF-Harbinger
            'harbinger': '2.1.1.8', # PIF-Harbinger
            'pif': '2.1.1.8',       # PIF-Harbinger
            'cacta': '2.1.1.9',     # CACTA
            
            # Elementos específicos mencionados
            'atran': '1.1.1',       # ATRAN é um Copia
            'dtt': '2.1.1.2',       # DTT como hAT
            'trep': '1.1.2',        # TREP pode ser Gypsy (comum em bancos de dados)
        }
        
        # Tentar mapeamentos especiais
        for label in [family_normalized, order_normalized, class_normalized]:
            if label in special_mappings:
                return special_mappings[label]
        
        return None
    
    def _normalize_label(self, label):
        """Normaliza label para busca (lowercase, sem caracteres especiais)"""
        if not label or label == 'Unknown':
            return ''
        
        # Converter para lowercase e remover caracteres especiais
        normalized = re.sub(r'[^a-zA-Z0-9]', '', label.lower())
        
        # Mapeamentos de normalização específicos
        normalization_map = {
            'classi': 'classi',
            'classii': 'classii', 
            'class1': 'classi',
            'class2': 'classii',
            'retrotransposon': 'classi',
            'dnatransposon': 'classii',
            'dna': 'classii'
        }
        
        return normalization_map.get(normalized, normalized)
    
    def _find_code_for_label(self, normalized_label):
        """Encontra código para label normalizado"""
        if not normalized_label:
            return None
            
        # Busca exata
        if normalized_label in self.label_to_code:
            return self.label_to_code[normalized_label]
        
        # Busca parcial (label contém o termo)
        for label, code in self.label_to_code.items():
            if normalized_label in label or label in normalized_label:
                return code
        
        return None
    
    def process_fasta_file(self, fasta_file, output_csv=None):
        """
        Processa arquivo FASTA completo e gera CSV com mapeamentos
        
        Args:
            fasta_file: Caminho para arquivo FASTA
            output_csv: Caminho para salvar CSV (opcional)
            
        Returns:
            DataFrame com mapeamentos
        """
        
        mappings = []
        
        try:
            with open(fasta_file, 'r') as f:
                for line in f:
                    if line.startswith('>'):
                        header = line.strip()
                        
                        # Parsear header
                        parsed = self.parse_fasta_header(header)
                        
                        # Mapear para código hierárquico
                        hierarchical_code = self.map_to_hierarchical_code(parsed)
                        
                        # Obter label hierárquico
                        hierarchical_label = self.hierarchy_map.get(hierarchical_code, 'Unknown') if hierarchical_code else 'Unknown'
                        
                        mapping = {
                            'sequence_id': parsed['seq_id'],
                            'original_header': header,
                            'class_level': parsed['class_level'],
                            'order_level': parsed['order_level'], 
                            'family_level': parsed['family_level'],
                            'hierarchical_code': hierarchical_code,
                            'hierarchical_label': hierarchical_label,
                            'mapping_success': hierarchical_code is not None
                        }
                        
                        mappings.append(mapping)
        
        except FileNotFoundError:
            print(f"❌ Arquivo FASTA não encontrado: {fasta_file}")
            return pd.DataFrame()
        
        df = pd.DataFrame(mappings)
        
        if output_csv:
            output_path = Path(output_csv)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(output_csv, index=False)
            print(f"📄 Mapeamentos salvos em: {output_csv}")
        
        return df
    
    def add_actual_labels_to_predictions(self, predictions_csv, fasta_file, output_csv=None):
        """
        Adiciona coluna Actual_Label ao arquivo de predições baseado no FASTA.
        Corrigido para usar a lógica de inferência de nomes no campo 'Sequence ID'
        do CSV de predições, o que o torna mais robusto para a saída do TERL.
        """
        
        # Carregar predições
        predictions_df = pd.read_csv(predictions_csv)
        
        # Processar FASTA para obter mapeamentos
        mappings_df = self.process_fasta_file(fasta_file)
        
        # Criar dicionário de mapeamento seq_id -> código/label hierárquico
        id_to_code = {}
        id_to_label = {}
        
        for _, mapping_row in mappings_df.iterrows():
            seq_id = mapping_row['sequence_id']
            code = mapping_row['hierarchical_code']
            label = mapping_row['hierarchical_label']
            
            if pd.notna(code):
                id_to_code[seq_id] = code
                id_to_label[seq_id] = label
        
        # Assegurar que as colunas existem antes de tentar acessá-las
        if 'Sequence ID' not in predictions_df.columns:
            print("❌ Coluna 'Sequence ID' não encontrada no arquivo de predição.")
            return predictions_df
            
        predictions_df['Actual_Code'] = None
        predictions_df['Actual_Label'] = None
        
        # Iterar sobre as linhas do CSV de predição e inferir o rótulo verdadeiro
        # usando a lógica de inferência de nomes
        for index, row in predictions_df.iterrows():
            seq_id = row['Sequence ID']
            parsed_header = self.parse_fasta_header(seq_id)
            inferred_label = parsed_header['family_level']
            
            # Buscar o código e o rótulo hierárquico correspondente
            if inferred_label and inferred_label != 'Unknown':
                hierarchical_code = self.map_to_hierarchical_code({'family_level': inferred_label, 'order_level': parsed_header['order_level'], 'class_level': parsed_header['class_level']})
                if hierarchical_code:
                    predictions_df.loc[index, 'Actual_Code'] = hierarchical_code
                    predictions_df.loc[index, 'Actual_Label'] = self.hierarchy_map.get(hierarchical_code, inferred_label)

        # Estatísticas de mapeamento
        successful_mappings = predictions_df['Actual_Code'].notna().sum()
        total_sequences = len(predictions_df)
        
        print(f"📊 Mapeamento concluído:")
        print(f"   Total de sequências: {total_sequences}")
        print(f"   Mapeamentos bem-sucedidos: {successful_mappings}")
        print(f"   Taxa de sucesso: {successful_mappings/total_sequences*100:.1f}%")
        
        # Mostrar distribuição de labels
        if successful_mappings > 0:
            label_distribution = predictions_df['Actual_Label'].value_counts()
            print(f"   Distribuição de labels verdadeiros:")
            for label, count in label_distribution.head().items():
                print(f"     {label}: {count}")
        
        # Salvar arquivo atualizado
        output_file = output_csv if output_csv else predictions_csv
        predictions_df.to_csv(output_file, index=False)
        
        print(f"✅ Arquivo atualizado: {output_file}")
        
        return predictions_df
    
    def validate_mapping(self, fasta_file):
        """
        Valida mapeamentos e mostra estatísticas
        
        Args:
            fasta_file: Arquivo FASTA para validar
        """
        
        print(f"🔍 Validando mapeamentos para: {fasta_file}")
        print("=" * 50)
        
        mappings_df = self.process_fasta_file(fasta_file)
        
        if mappings_df.empty:
            print("❌ Nenhum mapeamento encontrado")
            return
        
        total = len(mappings_df)
        successful = mappings_df['mapping_success'].sum()
        failed = total - successful
        
        print(f"📊 ESTATÍSTICAS DE MAPEAMENTO:")
        print(f"   Total de sequências: {total}")
        print(f"   Mapeamentos bem-sucedidos: {successful} ({successful/total*100:.1f}%)")
        print(f"   Mapeamentos falhos: {failed} ({failed/total*100:.1f}%)")
        
        # Mostrar distribuição de níveis hierárquicos
        if successful > 0:
            print(f"\n📋 DISTRIBUIÇÃO POR NÍVEL:")
            
            # Classes
            class_dist = mappings_df['class_level'].value_counts()
            print(f"   Classes: {dict(class_dist)}")
            
            # Orders
            order_dist = mappings_df['order_level'].value_counts()
            print(f"   Orders: {dict(order_dist.head())}")
            
            # Families
            family_dist = mappings_df['family_level'].value_counts()
            print(f"   Families: {dict(family_dist.head())}")
            
            # Códigos hierárquicos finais
            code_dist = mappings_df['hierarchical_code'].value_counts()
            print(f"\n🎯 CÓDIGOS HIERÁRQUICOS MAPEADOS:")
            for code, count in code_dist.head().items():
                label = self.hierarchy_map.get(code, 'Unknown')
                print(f"   {code} ({label}): {count}")
        
        # Mostrar falhas
        if failed > 0:
            print(f"\n❌ MAPEAMENTOS QUE FALHARAM:")
            failed_mappings = mappings_df[~mappings_df['mapping_success']]
            for _, row in failed_mappings.head().iterrows():
                print(f"   {row['sequence_id']}: {row['class_level']}|{row['order_level']}|{row['family_level']}")
        
        return mappings_df


def main():
    """Função principal para teste"""
    import sys
    
    if len(sys.argv) < 2:
        print("Uso:")
        print("  python fasta_label_mapper.py validate <arquivo.fasta>")
        print("  python fasta_label_mapper.py process <arquivo.fasta> [output.csv]")
        print("  python fasta_label_mapper.py add-labels <predictions.csv> <fasta.fasta> [output.csv]")
        return
    
    command = sys.argv[1]
    mapper = FASTALabelMapper()
    
    if command == 'validate':
        fasta_file = sys.argv[2]
        mapper.validate_mapping(fasta_file)
        
    elif command == 'process':
        fasta_file = sys.argv[2]
        output_csv = sys.argv[3] if len(sys.argv) > 3 else f"{Path(fasta_file).stem}_mappings.csv"
        mapper.process_fasta_file(fasta_file, output_csv)
        
    elif command == 'add-labels':
        predictions_csv = sys.argv[2]
        fasta_file = sys.argv[3]
        output_csv = sys.argv[4] if len(sys.argv) > 4 else None
        mapper.add_actual_labels_to_predictions(predictions_csv, fasta_file, output_csv)
        
    else:
        print(f"❌ Comando não reconhecido: {command}")


if __name__ == "__main__":
    main()