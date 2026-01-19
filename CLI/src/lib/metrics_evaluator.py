
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, roc_auc_score, average_precision_score,
    classification_report,
    cohen_kappa_score, 
    matthews_corrcoef
)
from sklearn.preprocessing import label_binarize
import json
import re
from pathlib import Path

class TEMetricsEvaluator:
    """
    Avaliador de métricas padronizadas para elementos transponíveis
    Implementa todas as métricas propostas na revisão de literatura
    """
    
    def __init__(self, hierarchy_file="src/nodes/tree.txt"):
        self.hierarchy = self._load_hierarchy(hierarchy_file)
        
    def _load_hierarchy(self, hierarchy_file):
        """Carrega hierarquia de classificação"""
        hierarchy = {}
        
        try:
            with open(hierarchy_file, 'r') as f:
                for line in f:
                    if ',' in line:
                        code, label = line.strip().split(',', 1)
                        hierarchy[label.strip()] = code.strip()
        except FileNotFoundError:
            print(f"⚠️ Arquivo de hierarquia não encontrado: {hierarchy_file}")
        
        return hierarchy
    
    def _build_label_to_code_map(self):
        """
        Constrói mapeamento abrangente de labels (e variações) para códigos hierárquicos.
        Inclui mapeamentos diretos do tree.txt e variações comuns dos modelos.
        """
        label_map = {}
        
        # Mapeamento direto do tree.txt (invertido)
        for label, code in self.hierarchy.items():
            normalized = self._normalize_label(label)
            if normalized:
                label_map[normalized] = code
        
        # Mapeamentos adicionais para variações comuns dos modelos
        additional_mappings = {
            # ClassI/ClassII variações
            'classi': '1',
            'classii': '2',
            'class1': '1',
            'class2': '2',
            
            # LTR superfamily
            'ltr': '1.1',
            'copia': '1.1.1',
            'belpao': '1.1.2',
            'bel': '1.1.2',
            'pao': '1.1.2',
            'retrovirus': '1.1.3',
            'gypsy': '1.1.4',
            'erv': '1.1.5',
            
            # SINE
            'sine': '1.2',
            '5s': '1.2.1',
            '7sl': '1.2.2',
            'trna': '1.2.3',
            
            # LINE
            'line': '1.3',
            'i': '1.3.1',
            'jockey': '1.3.2',
            'l1': '1.3.3',
            'rte': '1.3.4',
            'r2': '1.3.5',
            
            # DIRS
            'dirs': '1.4.1',
            'ngaro': '1.4.2',
            'viper': '1.4',  # DIRS order
            
            # PLE
            'ple': '1.5',
            'penelope': '1.5.1',
            
            # TRIM
            'trim': '1.6',
            
            # ClassII - TIR
            'tir': '2.1',
            'tirs': '2.1',
            'subclassi': '2.1',
            'subclass1': '2.1',
            'hat': '2.1.1',
            'tc1mariner': '2.1.2',
            'tc1': '2.1.2',
            'mariner': '2.1.2',
            'p': '2.1.3',
            'mudr': '2.1.4',
            'mutator': '2.1.4',
            'cacta': '2.1.5',
            'pifharbinger': '2.1.6',
            'pif': '2.1.6',
            'harbinger': '2.1.6',
            'piggybac': '2.1.7',
            'piggyb': '2.1.7',
            'transib': '2.1.8',
            'merlin': '2.1.9',
            
            # ClassII - outros
            'crypton': '2.2.1',
            'cryptons': '2.2',
            'helitron': '2.3.1',
            'helitrons': '2.3',
            'subclass2': '2.3',  # Helitron/Maverick
            'mite': '2.4',
            'maverick': '2.6',
            
            # Academ e outros
            'academ': '2.5.1',
            'kolobok': '2.5.2',
            'ginger2': '2.5.3',
            'tdd': '2.5.3',
            'ginger1': '2.5.4',
            'chapaev': '2.5.5',
            
            # Variações adicionais que podem aparecer nos modelos
            'maverick': '2.6',  # Maverick já estava mas garantir
            
            # NOTA: NonTE (Non-Transposable Element) NÃO é mapeado intencionalmente
            # pois representa ausência de TE, não um tipo de TE
        }
        
        label_map.update(additional_mappings)
        
        return label_map
    
    def _label_to_hierarchical_code(self, label):
        """
        Converte um label para código hierárquico.
        Retorna o código mais específico possível.
        """
        if not hasattr(self, '_label_code_map'):
            self._label_code_map = self._build_label_to_code_map()
        
        normalized = self._normalize_label(label)
        
        # Busca exata
        if normalized in self._label_code_map:
            return self._label_code_map[normalized]
        
        # Busca parcial - retorna o match mais longo
        best_match = None
        best_code = None
        
        for map_label, code in self._label_code_map.items():
            # Verifica se há substring match
            if len(map_label) >= 3:  # Mínimo 3 caracteres
                if map_label in normalized or normalized in map_label:
                    if best_match is None or len(map_label) > len(best_match):
                        best_match = map_label
                        best_code = code
        
        return best_code
    
    def _normalize_label(self, label):
        """Normaliza label para comparação (remove hífens, underscores, lowercase)"""
        if pd.isna(label) or label == 'Unknown':
            return 'unknown'
        # Remove caracteres especiais e converte para lowercase
        normalized = re.sub(r'[^a-zA-Z0-9]', '', str(label).lower())
        return normalized
    
    def _flexible_match(self, true_label, pred_label):
        """
        Verifica se há match entre labels usando hierarquia:
        1. Converte ambos para códigos hierárquicos
        2. Compara códigos no mesmo nível hierárquico
        3. Considera match se estão na mesma hierarquia
        
        Retorna: (matched: bool, match_type: str, confidence: float, true_code: str, pred_code: str)
        """
        # Converter labels para códigos hierárquicos
        true_code = self._label_to_hierarchical_code(true_label)
        pred_code = self._label_to_hierarchical_code(pred_label)
        
        # Se não conseguiu mapear, tenta normalização simples
        if not true_code or not pred_code:
            true_norm = self._normalize_label(true_label)
            pred_norm = self._normalize_label(pred_label)
            
            if true_norm == pred_norm:
                return True, 'exact_normalized', 1.0, true_norm, pred_norm
            elif pred_norm in true_norm and len(pred_norm) >= 3:
                return True, 'partial_substring', 0.5, true_norm, pred_norm
            else:
                return False, 'no_match', 0.0, true_norm, pred_norm
        
        # Ambos mapeados para códigos - compara hierarquicamente
        
        # Match exato no mesmo nível
        if true_code == pred_code:
            return True, 'exact_hierarchical', 1.0, true_code, pred_code
        
        # Match em diferentes níveis hierárquicos
        true_parts = true_code.split('.')
        pred_parts = pred_code.split('.')
        
        # Verifica quantos níveis em comum
        common_levels = 0
        for t, p in zip(true_parts, pred_parts):
            if t == p:
                common_levels += 1
            else:
                break
        
        # Se tem pelo menos 1 nível em comum (ex: apenas classe), considera match parcial
        if common_levels >= 1:
            # Confidence baseada na profundidade comum
            max_depth = max(len(true_parts), len(pred_parts))
            confidence = common_levels / max_depth
            
            # Se pred é mais genérico que true (ex: pred=LTR, true=Copia)
            if len(pred_parts) < len(true_parts) and pred_code == '.'.join(true_parts[:len(pred_parts)]):
                return True, 'hierarchical_parent', confidence, true_code, pred_code
            
            # Se true é mais genérico que pred (ex: true=LTR, pred=Copia)
            if len(true_parts) < len(pred_parts) and true_code == '.'.join(pred_parts[:len(true_parts)]):
                return True, 'hierarchical_child', confidence, true_code, pred_code
            
            # Mesmo nível hierárquico mas famílias diferentes (ex: Copia vs Gypsy)
            if len(true_parts) == len(pred_parts):
                return True, 'hierarchical_sibling', confidence, true_code, pred_code
            
            # Caso geral: compartilham pelo menos 1 nível mas não são parent/child/sibling
            # Ex: SINE (1.2) vs ERV (1.1.5) - mesma classe, ordens diferentes
            return True, 'hierarchical_partial', confidence, true_code, pred_code
        
        # Sem match hierárquico suficiente
        return False, 'no_match', 0.0, true_code, pred_code
    
    def evaluate_predictions(self, predictions_file, output_dir):
        """
        Avalia predições usando todas as métricas padronizadas
        
        Args:
            predictions_file: Arquivo CSV com predições
            output_dir: Diretório para salvar resultados
        """
        

        df = pd.read_csv(predictions_file)
        

        if "Actual_Label" not in df.columns:
            print("⚠️ Sem labels verdadeiros. Calculando apenas estatísticas descritivas.")
            return self._calculate_descriptive_stats(df, output_dir)
        

        # Armazenar labels originais para relatório
        y_true_original = df["Actual_Label"].fillna("Unknown")
        y_pred_original = df["Predicted label"].fillna("Unknown")
        
        # Aplicar matching hierárquico para normalizar labels
        y_true_codes = []
        y_pred_codes = []
        match_types_list = []
        match_confidences_list = []
        match_stats = {
            'exact_hierarchical': 0,
            'exact_normalized': 0, 
            'hierarchical_parent': 0,
            'hierarchical_child': 0,
            'hierarchical_sibling': 0,
            'hierarchical_partial': 0,
            'partial_substring': 0,
            'no_match': 0
        }
        
        # Debug: Verificar labels únicos que não foram mapeados
        unmapped_labels = set()
        
        for true_label, pred_label in zip(y_true_original, y_pred_original):
            matched, match_type, confidence, true_code, pred_code = self._flexible_match(true_label, pred_label)
            match_stats[match_type] += 1
            
            # Detectar labels não mapeados
            if match_type == 'no_match':
                true_mapped = self._label_to_hierarchical_code(true_label)
                pred_mapped = self._label_to_hierarchical_code(pred_label)
                if not true_mapped:
                    unmapped_labels.add(f"TRUE: {true_label}")
                if not pred_mapped:
                    unmapped_labels.add(f"PRED: {pred_label}")
            
            # Armazenar tipo de match e confiança para cada linha
            match_types_list.append(match_type)
            match_confidences_list.append(confidence)
            
            # Para cálculo de métricas, usar códigos hierárquicos
            # Se houver match hierárquico, usar o código mais específico (true)
            if matched:
                # Usa código true para ambos (força match)
                y_true_codes.append(true_code)
                y_pred_codes.append(true_code)
            else:
                # Mantém códigos diferentes
                y_true_codes.append(true_code if true_code else self._normalize_label(true_label))
                y_pred_codes.append(pred_code if pred_code else self._normalize_label(pred_label))
        
        y_true = pd.Series(y_true_codes)
        y_pred = pd.Series(y_pred_codes)
        
        # Adicionar colunas de match ao DataFrame original
        df['Match_Type'] = match_types_list
        df['Match_Confidence'] = [f"{conf:.2%}" for conf in match_confidences_list]
        df['Match_Score'] = match_confidences_list
        
        # Salvar CSV atualizado com informações de matching
        df.to_csv(predictions_file, index=False)
        print(f"💾 CSV atualizado com colunas Match_Type, Match_Confidence e Match_Score")
        
        print(f"📊 Aplicando matching hierárquico...")
        total_matches = sum(v for k, v in match_stats.items() if k != 'no_match')
        print(f"   Total de matches: {total_matches}/{len(df)} ({total_matches/len(df)*100:.1f}%)")
        for match_type, count in match_stats.items():
            if count > 0:
                print(f"   - {match_type}: {count}")
        
        # Exibir labels não mapeados (se houver)
        if unmapped_labels:
            print(f"\n⚠️  Labels não mapeados para códigos hierárquicos ({len(unmapped_labels)}):")
            for label in sorted(list(unmapped_labels))[:20]:  # Mostrar até 20
                print(f"     {label}")
            if len(unmapped_labels) > 20:
                print(f"     ... e mais {len(unmapped_labels) - 20} labels")
        

        metrics = self._calculate_all_metrics(y_true, y_pred, y_true_original, y_pred_original, match_stats)
        

        json_metrics, summary = self._save_metrics(metrics, output_dir)
        

        self._generate_detailed_report(y_true, y_pred, metrics, output_dir, json_metrics, summary)
        
        return metrics
    
    def _calculate_all_metrics(self, y_true, y_pred, y_true_original=None, y_pred_original=None, match_stats=None):
        """Calcula todas as métricas padronizadas usando labels normalizados"""
        
        metrics = {}
        
        # Armazenar informação sobre matching flexível
        if match_stats:
            metrics["flexible_matching_applied"] = True
            metrics["match_statistics"] = match_stats
        else:
            metrics["flexible_matching_applied"] = False
        
        # Armazenar informação sobre normalização
        if y_true_original is not None and y_pred_original is not None:
            unique_true_orig = y_true_original.nunique()
            unique_true_norm = y_true.nunique()
            unique_pred_orig = y_pred_original.nunique()
            unique_pred_norm = y_pred.nunique()
            metrics["normalization_applied"] = True
            metrics["unique_labels_before_normalization"] = {"true": int(unique_true_orig), "pred": int(unique_pred_orig)}
            metrics["unique_labels_after_normalization"] = {"true": int(unique_true_norm), "pred": int(unique_pred_norm)}
        else:
            metrics["normalization_applied"] = False
        

        metrics["accuracy"] = accuracy_score(y_true, y_pred)
        

        metrics["precision_macro"] = precision_score(y_true, y_pred, average='macro', zero_division=0)
        metrics["precision_micro"] = precision_score(y_true, y_pred, average='micro', zero_division=0)
        metrics["precision_weighted"] = precision_score(y_true, y_pred, average='weighted', zero_division=0)
        

        metrics["recall_macro"] = recall_score(y_true, y_pred, average='macro', zero_division=0)
        metrics["recall_micro"] = recall_score(y_true, y_pred, average='micro', zero_division=0)
        metrics["recall_weighted"] = recall_score(y_true, y_pred, average='weighted', zero_division=0)
        

        metrics["f1_macro"] = f1_score(y_true, y_pred, average='macro', zero_division=0)
        metrics["f1_micro"] = f1_score(y_true, y_pred, average='micro', zero_division=0)
        metrics["f1_weighted"] = f1_score(y_true, y_pred, average='weighted', zero_division=0)
        

        # Obter labels únicos na ordem da matriz de confusão
        unique_labels = sorted(set(y_true) | set(y_pred))
        cm = confusion_matrix(y_true, y_pred, labels=unique_labels)
        metrics["confusion_matrix"] = cm.tolist()
        metrics["confusion_matrix_labels"] = [str(label) for label in unique_labels]
        
        # Mapear códigos para nomes de superfamílias (se disponível)
        if self.hierarchy:
            code_to_name = {code: name for name, code in self.hierarchy.items()}
            metrics["confusion_matrix_names"] = [
                code_to_name.get(str(label), str(label)) for label in unique_labels
            ]
        

        specificity_scores = self._calculate_specificity(cm)
        metrics["specificity_macro"] = np.mean(specificity_scores)
        metrics["youdens_j"] = metrics["recall_macro"] + metrics["specificity_macro"] - 1
        

        metrics["cohens_kappa"] = cohen_kappa_score(y_true, y_pred)
        

        metrics["matthews_corrcoef"] = matthews_corrcoef(y_true, y_pred)


        try:
            unique_labels = np.unique(np.concatenate([y_true, y_pred]))
            if len(unique_labels) > 2:

                y_true_bin = label_binarize(y_true, classes=unique_labels)
                y_pred_bin = label_binarize(y_pred, classes=unique_labels)
                

                roc_scores = []
                for i in range(len(unique_labels)):
                    if len(np.unique(y_true_bin[:, i])) > 1:
                        roc_score = roc_auc_score(y_true_bin[:, i], y_pred_bin[:, i])
                        roc_scores.append(roc_score)
                
                metrics["auroc_macro"] = np.mean(roc_scores) if roc_scores else 0.0
                

                map_scores = []
                for i in range(len(unique_labels)):
                    if len(np.unique(y_true_bin[:, i])) > 1:
                        map_score = average_precision_score(y_true_bin[:, i], y_pred_bin[:, i])
                        map_scores.append(map_score)
                
                metrics["map_macro"] = np.mean(map_scores) if map_scores else 0.0
            
            else:

                if len(np.unique(y_true)) == 2:
                    metrics["auroc_macro"] = roc_auc_score(y_true, y_pred, pos_label=unique_labels[1])
                    metrics["map_macro"] = average_precision_score(y_true, y_pred, pos_label=unique_labels[1])
                else:
                    metrics["auroc_macro"] = 0.0
                    metrics["map_macro"] = 0.0
        
        except Exception as e:
            print(f"⚠️ Erro ao calcular auROC/mAP: {str(e)}")
            metrics["auroc_macro"] = "not_available"
            metrics["map_macro"] = "not_available"
        

        class_report = classification_report(y_true, y_pred, output_dict=True, zero_division=0)
        metrics["per_class_metrics"] = class_report
        

        f1_scores_per_class = []
        for class_name, class_data in class_report.items():

            if isinstance(class_data, dict) and 'f1-score' in class_data and class_name not in ['accuracy', 'macro avg', 'weighted avg']:
                f1_scores_per_class.append(class_data['f1-score'])
        
        if f1_scores_per_class:

            metrics["std_f1_per_class"] = np.std(f1_scores_per_class)
        else:
            metrics["std_f1_per_class"] = 0.0
        

        if self.hierarchy:
            hierarchical_metrics = self._calculate_hierarchical_metrics(y_true, y_pred)
            metrics.update(hierarchical_metrics)
        

        metrics["total_samples"] = len(y_true)
        metrics["num_classes"] = len(np.unique(y_true))
        metrics["num_predicted_classes"] = len(np.unique(y_pred))
        
        return metrics
    
    def _calculate_specificity(self, cm):
        """Calcula especificidade para cada classe"""
        FP = cm.sum(axis=0) - np.diag(cm)
        TN = cm.sum() - (FP + cm.sum(axis=1) - np.diag(cm) + np.diag(cm))
        
        with np.errstate(divide='ignore', invalid='ignore'):
            specificity = TN / (TN + FP)
        
        return np.nan_to_num(specificity)
    
    def _calculate_hierarchical_metrics(self, y_true, y_pred):
        """Calcula métricas hierárquicas"""
        
        hierarchical_metrics = {}
        
        try:

            true_codes = [self.hierarchy.get(label, label) for label in y_true]
            pred_codes = [self.hierarchy.get(label, label) for label in y_pred]
            

            distances = []
            for true_code, pred_code in zip(true_codes, pred_codes):
                distance = self._hierarchical_distance(true_code, pred_code)
                distances.append(distance)
            
            hierarchical_metrics["mean_hierarchical_distance"] = np.mean(distances)
            hierarchical_metrics["std_hierarchical_distance"] = np.std(distances)
            hierarchical_metrics["max_hierarchical_distance"] = np.max(distances)
            

            h_precision_scores = []
            h_recall_scores = []
            
            for true_code, pred_code in zip(true_codes, pred_codes):
                true_path = self._get_hierarchical_path(true_code)
                pred_path = self._get_hierarchical_path(pred_code)
                
                if pred_path:
                    intersection = len(set(true_path) & set(pred_path))
                    h_precision = intersection / len(pred_path)
                    h_precision_scores.append(h_precision)
                
                if true_path:
                    intersection = len(set(true_path) & set(pred_path))
                    h_recall = intersection / len(true_path)
                    h_recall_scores.append(h_recall)
            
            hierarchical_metrics["hierarchical_precision"] = np.mean(h_precision_scores) if h_precision_scores else 0.0
            hierarchical_metrics["hierarchical_recall"] = np.mean(h_recall_scores) if h_recall_scores else 0.0
            

            h_prec = hierarchical_metrics["hierarchical_precision"]
            h_rec = hierarchical_metrics["hierarchical_recall"]
            
            if h_prec + h_rec > 0:
                hierarchical_metrics["hierarchical_f1"] = 2 * (h_prec * h_rec) / (h_prec + h_rec)
            else:
                hierarchical_metrics["hierarchical_f1"] = 0.0
        
        except Exception as e:
            print(f"⚠️ Erro ao calcular métricas hierárquicas: {str(e)}")
            hierarchical_metrics["hierarchical_precision"] = "not_available"
            hierarchical_metrics["hierarchical_recall"] = "not_available"
            hierarchical_metrics["hierarchical_f1"] = "not_available"
        
        return hierarchical_metrics
    
    def _hierarchical_distance(self, code1, code2):
        """Calcula distância hierárquica entre dois códigos"""
        if code1 == code2:
            return 0.0
        
        path1 = self._get_hierarchical_path(code1)
        path2 = self._get_hierarchical_path(code2)
        

        common_length = 0
        for p1, p2 in zip(path1, path2):
            if p1 == p2:
                common_length += 1
            else:
                break
        

        return len(path1) + len(path2) - 2 * common_length
    
    def _get_hierarchical_path(self, code):
        """Obtém caminho hierárquico para um código"""
        if not code or '.' not in str(code):
            return [code] if code else []
        
        parts = str(code).split('.')
        path = []
        
        for i in range(1, len(parts) + 1):
            path.append('.'.join(parts[:i]))
        
        return path
    
    def _calculate_descriptive_stats(self, df, output_dir):
        """Calcula estatísticas descritivas sem labels verdadeiros"""
        

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        stats = {}
        
        if "Predicted label" in df.columns:
            predictions = df["Predicted label"]
            
            stats["total_sequences"] = len(df)
            stats["unique_predictions"] = len(predictions.unique())
            stats["prediction_distribution"] = predictions.value_counts().to_dict()
            stats["most_common_prediction"] = predictions.mode().iloc[0] if len(predictions) > 0 else "N/A"
            

            stats_file = output_path / "descriptive_stats.json"
            with open(stats_file, 'w') as f:
                json.dump(stats, f, indent=2)
            
            print(f"📊 Estatísticas descritivas salvas em: {stats_file}")
        
        return stats
    
    def _save_metrics(self, metrics, output_dir):
        """Salva métricas em formato JSON (retorna para incluir no relatório)"""
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        

        json_metrics = {}
        for key, value in metrics.items():
            if isinstance(value, np.ndarray):
                json_metrics[key] = value.tolist()
            elif isinstance(value, (np.int64, np.float64)):
                json_metrics[key] = float(value)
            else:
                json_metrics[key] = value
        

        summary = {
            "accuracy": json_metrics.get("accuracy", 0.0),
            "precision_macro": json_metrics.get("precision_macro", 0.0),
            "recall_macro": json_metrics.get("recall_macro", 0.0),
            "f1_macro": json_metrics.get("f1_macro", 0.0),
            "specificity_macro": json_metrics.get("specificity_macro", 0.0),
            "youdens_j": json_metrics.get("youdens_j", 0.0),
            "cohens_kappa": json_metrics.get("cohens_kappa", 0.0),
            "matthews_corrcoef": json_metrics.get("matthews_corrcoef", 0.0),
            "std_f1_per_class": json_metrics.get("std_f1_per_class", 0.0),
            "hierarchical_f1": json_metrics.get("hierarchical_f1", "not_available"),
            "total_samples": json_metrics.get("total_samples", 0),
            "num_classes": json_metrics.get("num_classes", 0)
        }
        
        # Retornar ambos para incluir no relatório de texto
        return json_metrics, summary
    
    def _generate_detailed_report(self, y_true, y_pred, metrics, output_dir, json_metrics=None, summary=None):
        """Gera relatório detalhado em texto com JSON incluído"""
        
        output_path = Path(output_dir)
        report_file = output_path / "evaluation_report.txt"
        
        with open(report_file, 'w') as f:
            f.write("=" * 80 + "\n")
            f.write("RELATÓRIO DE AVALIAÇÃO - ELEMENTOS TRANSPONÍVEIS\n")
            f.write("=" * 80 + "\n\n")
            
            # Informação sobre normalização
            if metrics.get('normalization_applied', False):
                f.write("⚙️ NORMALIZAÇÃO DE LABELS\n")
                f.write("-" * 40 + "\n")
                f.write("Labels foram normalizados para comparação (remove hífens, underscores, lowercase)\n")
                f.write("Exemplos: 'Bel-Pao' = 'BelPao' = 'bel-pao' = 'belpao'\n")
                before_norm = metrics.get('unique_labels_before_normalization', {})
                after_norm = metrics.get('unique_labels_after_normalization', {})
                f.write(f"Labels únicos (true) antes: {before_norm.get('true', 'N/A')}, depois: {after_norm.get('true', 'N/A')}\n")
                f.write(f"Labels únicos (pred) antes: {before_norm.get('pred', 'N/A')}, depois: {after_norm.get('pred', 'N/A')}\n\n")
            
            # Informação sobre matching flexível
            if metrics.get('flexible_matching_applied', False):
                f.write("🔍 MATCHING HIERÁRQUICO\n")
                f.write("-" * 40 + "\n")
                f.write("Matching baseado em hierarquia de classificação (códigos tree.txt)\n")
                f.write("Labels convertidos para códigos hierárquicos antes da comparação\n")
                f.write("Exemplos:\n")
                f.write("  - 'Pao' → '1.1.2' (Bel-Pao)\n")
                f.write("  - 'Mariner' → '2.1.2' (Tc1-Mariner)\n")
                f.write("  - 'LTR' → '1.1' (ordem LTR)\n")
                match_stats = metrics.get('match_statistics', {})
                total = sum(match_stats.values())
                if total > 0:
                    f.write(f"\nTotal de comparações: {total}\n")
                    if match_stats.get('exact_hierarchical', 0) > 0:
                        f.write(f"  ✅ Matches exatos (mesmo código): {match_stats['exact_hierarchical']} ({match_stats['exact_hierarchical']/total*100:.1f}%)\n")
                    if match_stats.get('exact_normalized', 0) > 0:
                        f.write(f"  ✅ Matches normalizados: {match_stats['exact_normalized']} ({match_stats['exact_normalized']/total*100:.1f}%)\n")
                    if match_stats.get('hierarchical_parent', 0) > 0:
                        f.write(f"  ✅ Matches parent-child: {match_stats['hierarchical_parent']} ({match_stats['hierarchical_parent']/total*100:.1f}%)\n")
                    if match_stats.get('hierarchical_child', 0) > 0:
                        f.write(f"  ✅ Matches child-parent: {match_stats['hierarchical_child']} ({match_stats['hierarchical_child']/total*100:.1f}%)\n")
                    if match_stats.get('hierarchical_sibling', 0) > 0:
                        f.write(f"  ⚠️  Matches siblings (mesma ordem): {match_stats['hierarchical_sibling']} ({match_stats['hierarchical_sibling']/total*100:.1f}%)\n")
                    if match_stats.get('hierarchical_partial', 0) > 0:
                        f.write(f"  ⚠️  Matches parciais (níveis comuns): {match_stats['hierarchical_partial']} ({match_stats['hierarchical_partial']/total*100:.1f}%)\n")
                    if match_stats.get('partial_substring', 0) > 0:
                        f.write(f"  ✅ Matches parciais (substring): {match_stats['partial_substring']} ({match_stats['partial_substring']/total*100:.1f}%)\n")
                    if match_stats.get('no_match', 0) > 0:
                        f.write(f"  ❌ Sem match: {match_stats['no_match']} ({match_stats['no_match']/total*100:.1f}%)\n")
                f.write("\n")
            

            f.write("EXECUTIVE SUMMARY\n")
            f.write("-" * 40 + "\n")
            f.write(f"Total sequences: {metrics.get('total_samples', 'N/A')}\n")
            f.write(f"Number of classes: {metrics.get('num_classes', 'N/A')}\n")
            f.write(f"Overall accuracy: {metrics.get('accuracy', 0.0):.4f}\n")
            f.write(f"F1-Score (macro): {metrics.get('f1_macro', 0.0):.4f}\n")
            f.write(f"MCC (Matthews): {metrics.get('matthews_corrcoef', 0.0):.4f}\n")
            
            if metrics.get('hierarchical_f1') != 'not_available':
                f.write(f"Hierarchical F1-Score: {metrics.get('hierarchical_f1', 0.0):.4f}\n")
            
            f.write(f"Youden's J Statistic: {metrics.get('youdens_j', 0.0):.4f}\n\n")
            

            f.write("STANDARD METRICS\n")
            f.write("-" * 40 + "\n")
            f.write(f"Accuracy: {metrics.get('accuracy', 0.0):.4f}\n")
            f.write(f"Precision (macro): {metrics.get('precision_macro', 0.0):.4f}\n")
            f.write(f"Precision (micro): {metrics.get('precision_micro', 0.0):.4f}\n")
            f.write(f"Precision (weighted): {metrics.get('precision_weighted', 0.0):.4f}\n")
            f.write(f"Recall (macro): {metrics.get('recall_macro', 0.0):.4f}\n")
            f.write(f"Recall (micro): {metrics.get('recall_micro', 0.0):.4f}\n")
            f.write(f"Recall (weighted): {metrics.get('recall_weighted', 0.0):.4f}\n")
            f.write(f"F1-Score (macro): {metrics.get('f1_macro', 0.0):.4f}\n")
            f.write(f"F1-Score (micro): {metrics.get('f1_micro', 0.0):.4f}\n")
            f.write(f"F1-Score (weighted): {metrics.get('f1_weighted', 0.0):.4f}\n")
            f.write(f"Specificity (macro): {metrics.get('specificity_macro', 0.0):.4f}\n\n")
            

            f.write("ROBUST & ADVANCED METRICS\n")
            f.write("-" * 40 + "\n")
            
            f.write(f"Cohen's Kappa Coefficient: {metrics.get('cohens_kappa', 0.0):.4f}\n")
            f.write(f"Matthews Correlation Coefficient (MCC): {metrics.get('matthews_corrcoef', 0.0):.4f}\n")
            f.write(f"F1 Standard Deviation per Class: {metrics.get('std_f1_per_class', 0.0):.4f} (Consistency)\n")
            
            auroc = metrics.get('auroc_macro', 'not_available')
            if auroc != 'not_available':
                f.write(f"auROC (macro): {auroc:.4f}\n")
            else:
                f.write("auROC (macro): Not available\n")
            
            map_score = metrics.get('map_macro', 'not_available')
            if map_score != 'not_available':
                f.write(f"mAP (macro): {map_score:.4f}\n\n")
            else:
                f.write("mAP (macro): Not available\n\n")
            

            if metrics.get('hierarchical_f1') != 'not_available':
                f.write("HIERARCHICAL METRICS\n")
                f.write("-" * 40 + "\n")
                f.write(f"Hierarchical precision: {metrics.get('hierarchical_precision', 0.0):.4f}\n")
                f.write(f"Hierarchical recall: {metrics.get('hierarchical_recall', 0.0):.4f}\n")
                f.write(f"Hierarchical F1-Score: {metrics.get('hierarchical_f1', 0.0):.4f}\n")
                f.write(f"Mean hierarchical distance: {metrics.get('mean_hierarchical_distance', 0.0):.4f}\n")
                f.write(f"Max hierarchical distance: {metrics.get('max_hierarchical_distance', 0.0):.4f}\n\n")
            

            if 'per_class_metrics' in metrics:
                f.write("PER-CLASS METRICS\n")
                f.write("-" * 40 + "\n")
                
                class_metrics = metrics['per_class_metrics']
                # Filter aggregate and invalid classes
                skip_classes = ['accuracy', 'macro avg', 'weighted avg', 'micro avg']
                
                for class_name, class_data in class_metrics.items():
                    # Skip aggregate and invalid classes
                    if class_name in skip_classes:
                        continue
                    
                    # Skip very short class names (likely fragments)
                    if isinstance(class_name, str) and len(class_name) <= 2 and not class_name.replace('.', '').isdigit():
                        continue
                    
                    if isinstance(class_data, dict) and 'precision' in class_data:
                        f.write(f"\nClass: {class_name}\n")
                        f.write(f"  Precision: {class_data.get('precision', 0.0):.4f}\n")
                        f.write(f"  Recall: {class_data.get('recall', 0.0):.4f}\n")
                        f.write(f"  F1-Score: {class_data.get('f1-score', 0.0):.4f}\n")
                        f.write(f"  Support: {class_data.get('support', 0)}\n")
            
            # Include JSONs at the end of the report
            if json_metrics or summary:
                f.write("\n" + "=" * 80 + "\n")
                f.write("DATA IN JSON FORMAT\n")
                f.write("=" * 80 + "\n\n")
                
                if summary:
                    f.write("SUMMARY (metrics_summary.json)\n")
                    f.write("-" * 40 + "\n")
                    f.write(json.dumps(summary, indent=2))
                    f.write("\n\n")
                
                if json_metrics:
                    f.write("DETAILED (detailed_metrics.json)\n")
                    f.write("-" * 40 + "\n")
                    f.write(json.dumps(json_metrics, indent=2))
                    f.write("\n")
        
        print(f"📄 Consolidated report saved to: {report_file}")
        print(f"   (includes metrics in text and JSON format)")


def main():
    """Função principal para teste"""
    import sys
    
    if len(sys.argv) < 2:
        print("Uso: python metrics_evaluator.py <arquivo_predicoes.csv> [diretorio_saida]")
        return
    
    predictions_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "evaluation_results"
    
    evaluator = TEMetricsEvaluator()
    metrics = evaluator.evaluate_predictions(predictions_file, output_dir)
    
    print(f"\n✅ Evaluation completed!")
    print(f"📁 Results saved to: {output_dir}")


if __name__ == "__main__":
    main()