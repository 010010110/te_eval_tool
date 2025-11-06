# metrics_evaluator.py - Métricas padronizadas da revisão de literatura
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, roc_auc_score, average_precision_score,
    classification_report
)
from sklearn.preprocessing import label_binarize
import json
from pathlib import Path

class TEMetricsEvaluator:
    """
    Avaliador de métricas padronizadas para elementos transponíveis
    Implementa todas as métricas propostas na revisão de literatura
    """
    
    def __init__(self, hierarchy_file="nodes/tree.txt"):
        # CORREÇÃO: Carregar hierarquia usando o caminho base do projeto
        self.hierarchy_path, self.hierarchy = self._load_hierarchy(hierarchy_file)
        
    def _load_hierarchy(self, hierarchy_file):
        """Carrega hierarquia de classificação"""
        hierarchy = {}
        
        try:
            # __file__ é o caminho deste script (raiz_do_projeto/metrics_evaluator.py)
            base_path = Path(__file__).parent.resolve()
        except NameError:
            # Fallback se __file__ não estiver definido (ex: REPL)
            base_path = Path.cwd()
            
        hierarchy_path = Path(hierarchy_file)
        if not hierarchy_path.is_absolute():
            hierarchy_path = (base_path / hierarchy_file).resolve()
            
        try:
            with open(hierarchy_path, 'r') as f:
                for line in f:
                    if ',' in line:
                        code, label = line.strip().split(',', 1)
                        hierarchy[label.strip()] = code.strip()
            print(f"    - Hierarquia de avaliação 'tree.txt' carregada de: {hierarchy_path}")
            return hierarchy_path, hierarchy
        except FileNotFoundError:
            print(f"⚠️ Arquivo de hierarquia não encontrado em: {hierarchy_path}")
            return hierarchy_path, {}
    
    def evaluate_predictions(self, predictions_file, output_dir):
        """
        Avalia predições usando todas as métricas padronizadas
        """
        
        # Carregar dados
        try:
            df = pd.read_csv(predictions_file)
        except Exception as e:
            print(f"❌ Erro fatal ao ler o arquivo de predições '{predictions_file}': {e}")
            return {}

        # --- INÍCIO DA CORREÇÃO (Renomear Colunas) ---
        
        # 1. Padronizar Coluna de ID (Garantia extra)
        id_col_name = None
        possible_id_names = ['id', 'Sequence ID', 'seq_id', 'sequence_id', 'header', 'name']
        
        for name in possible_id_names:
            if name in df.columns:
                id_col_name = name
                break
        if id_col_name is None and len(df.columns) > 0: 
            id_col_name = df.columns[0] # Assume a primeira
        
        if id_col_name and id_col_name != 'id':
            df = df.rename(columns={id_col_name: 'id'})

        # 2. Padronizar Coluna de PREDIÇÃO (O ERRO ATUAL)
        pred_col_name = None
        
        # CORREÇÃO CRÍTICA: Colunas que NÃO SÃO a predição
        known_non_pred_cols = [
            'id', 'Actual_Label', 'Actual_Label_Code', 'original_header', 
            'class_level', 'order_level', 'family_level', 'mapping_success',
            'Predicted_Label_Code' 
        ]
        
        # Nomes prováveis para a predição
        possible_pred_names = [
            'Predicted_Label_Name', # <--- Prioridade
            'Predicted label', 'Prediction', 'Predicted_Class', 
            'Hierarchical_Prediction', 'classifyte_prediction', 
            'terl_prediction', 'Predicted Class'
        ]
        
        # Tenta nomes conhecidos primeiro
        for name in possible_pred_names:
            if name in df.columns:
                pred_col_name = name
                break
                
        # Se não achar, procura a primeira coluna "desconhecida"
        if pred_col_name is None:
            for col in df.columns:
                if col not in known_non_pred_cols:
                    pred_col_name = col
                    print(f"    - ⚠️  Aviso: Coluna 'Predicted label' não encontrada. Usando a coluna '{pred_col_name}' como predição.")
                    break # Usa a primeira que encontrar
        
        # Se AINDA não achar
        if pred_col_name is None:
            print(f"❌ Erro: Não foi possível identificar a coluna de predição no CSV.")
            if "Actual_Label" not in df.columns:
                 return self._calculate_descriptive_stats(df, output_dir, "Unknown_Pred_Col")
            else:
                 return {} # Falha

        # Renomeia a coluna encontrada para o nome que o script espera
        if pred_col_name != 'Predicted label':
            print(f"    - Mapeando coluna de predição '{pred_col_name}' para 'Predicted label'.")
            df = df.rename(columns={pred_col_name: 'Predicted label'})
            
        # --- FIM DA CORREÇÃO ---

        # Verificar se tem labels verdadeiros (APÓS correções)
        if "Actual_Label" not in df.columns or df["Actual_Label"].isna().all():
            print("⚠️ Sem labels verdadeiros (coluna 'Actual_Label' ausente ou vazia). Calculando apenas estatísticas descritivas.")
            return self._calculate_descriptive_stats(df, output_dir, pred_col_name)
        
        # Extrair predições e labels verdadeiros
        y_true = df["Actual_Label"].fillna("Unknown")
        y_pred = df["Predicted label"].fillna("Unknown")
        
        # Calcular todas as métricas
        metrics = self._calculate_all_metrics(y_true, y_pred)
        
        # Salvar resultados
        self._save_metrics(metrics, output_dir)
        
        # Gerar relatório detalhado
        self._generate_detailed_report(y_true, y_pred, metrics, output_dir)
        
        return metrics
    
    def _calculate_all_metrics(self, y_true, y_pred):
        """Calcula todas as métricas padronizadas"""
        
        metrics = {}
        
        # Labels únicos para relatórios
        unique_labels = np.unique(np.concatenate([y_true, y_pred]))
        
        # 1. Acurácia
        metrics["accuracy"] = accuracy_score(y_true, y_pred)
        
        # 2. Precisão (macro e micro)
        metrics["precision_macro"] = precision_score(y_true, y_pred, average='macro', zero_division=0, labels=unique_labels)
        metrics["precision_micro"] = precision_score(y_true, y_pred, average='micro', zero_division=0, labels=unique_labels)
        metrics["precision_weighted"] = precision_score(y_true, y_pred, average='weighted', zero_division=0, labels=unique_labels)
        
        # 3. Recall/Sensibilidade (macro e micro)
        metrics["recall_macro"] = recall_score(y_true, y_pred, average='macro', zero_division=0, labels=unique_labels)
        metrics["recall_micro"] = recall_score(y_true, y_pred, average='micro', zero_division=0, labels=unique_labels)
        metrics["recall_weighted"] = recall_score(y_true, y_pred, average='weighted', zero_division=0, labels=unique_labels)
        
        # 4. F1-score (macro e micro)
        metrics["f1_macro"] = f1_score(y_true, y_pred, average='macro', zero_division=0, labels=unique_labels)
        metrics["f1_micro"] = f1_score(y_true, y_pred, average='micro', zero_division=0, labels=unique_labels)
        metrics["f1_weighted"] = f1_score(y_true, y_pred, average='weighted', zero_division=0, labels=unique_labels)
        
        # 5. Matriz de confusão
        cm = confusion_matrix(y_true, y_pred, labels=unique_labels)
        metrics["confusion_matrix"] = cm.tolist()
        metrics["confusion_matrix_labels"] = unique_labels.tolist()
        
        # 6. Especificidade e Youden's J Statistic
        specificity_scores = self._calculate_specificity(cm)
        metrics["specificity_macro"] = np.mean(specificity_scores)
        metrics["youdens_j"] = metrics["recall_macro"] + metrics["specificity_macro"] - 1
        
        # 7. auROC e mAP (se possível)
        try:
            if len(unique_labels) > 2:
                # Multi-class: usar One-vs-Rest
                y_true_bin = label_binarize(y_true, classes=unique_labels)
                y_pred_bin = label_binarize(y_pred, classes=unique_labels)
                
                # Garantir que y_pred_bin tenha a mesma forma
                if y_true_bin.shape[1] != y_pred_bin.shape[1]:
                     y_pred_bin = label_binarize(y_pred, classes=unique_labels)

                # auROC para cada classe
                roc_scores = []
                for i in range(y_true_bin.shape[1]):
                    if len(np.unique(y_true_bin[:, i])) > 1: # Precisa de ambas as classes
                        roc_score = roc_auc_score(y_true_bin[:, i], y_pred_bin[:, i])
                        roc_scores.append(roc_score)
                
                metrics["auroc_macro"] = np.mean(roc_scores) if roc_scores else 0.0
                
                # mAP (Mean Average Precision)
                map_scores = []
                for i in range(y_true_bin.shape[1]):
                    if len(np.unique(y_true_bin[:, i])) > 1:
                        map_score = average_precision_score(y_true_bin[:, i], y_pred_bin[:, i])
                        map_scores.append(map_score)
                
                metrics["map_macro"] = np.mean(map_scores) if map_scores else 0.0
            
            elif len(unique_labels) == 2:
                # Binary case
                y_true_bin = label_binarize(y_true, classes=unique_labels).ravel()
                y_pred_bin = label_binarize(y_pred, classes=unique_labels).ravel()
                
                if len(np.unique(y_true_bin)) == 2:
                    metrics["auroc_macro"] = roc_auc_score(y_true_bin, y_pred_bin)
                    metrics["map_macro"] = average_precision_score(y_true_bin, y_pred_bin)
                else:
                    metrics["auroc_macro"] = 0.0
                    metrics["map_macro"] = 0.0
            else:
                metrics["auroc_macro"] = 0.0
                metrics["map_macro"] = 0.0
        
        except Exception as e:
            print(f"⚠️ Erro ao calcular auROC/mAP (provavelmente classes únicas): {str(e)}")
            metrics["auroc_macro"] = "not_available"
            metrics["map_macro"] = "not_available"
        
        # 8. Métricas por classe
        class_report = classification_report(y_true, y_pred, output_dict=True, zero_division=0, labels=unique_labels)
        metrics["per_class_metrics"] = class_report
        
        # 9. Métricas hierárquicas (se hierarquia disponível)
        if self.hierarchy:
            hierarchical_metrics = self._calculate_hierarchical_metrics(y_true, y_pred)
            metrics.update(hierarchical_metrics)
        
        # 10. Estatísticas gerais
        metrics["total_samples"] = len(y_true)
        metrics["num_classes"] = len(np.unique(y_true))
        metrics["num_predicted_classes"] = len(np.unique(y_pred))
        
        return metrics
    
    def _calculate_specificity(self, cm):
        """Calcula especificidade para cada classe"""
        FP = cm.sum(axis=0) - np.diag(cm)
        FN = cm.sum(axis=1) - np.diag(cm)
        TP = np.diag(cm)
        TN = cm.sum() - (FP + FN + TP)
        
        with np.errstate(divide='ignore', invalid='ignore'):
            specificity = TN / (TN + FP)
        
        return np.nan_to_num(specificity)
    
    def _calculate_hierarchical_metrics(self, y_true, y_pred):
        """Calcula métricas hierárquicas"""
        
        hierarchical_metrics = {}
        
        try:
            # Mapear labels para códigos hierárquicos
            true_codes = [self.hierarchy.get(label, label) for label in y_true]
            pred_codes = [self.hierarchy.get(label, label) for label in y_pred]
            
            # Calcular distância hierárquica média
            distances = []
            for true_code, pred_code in zip(true_codes, pred_codes):
                distance = self._hierarchical_distance(true_code, pred_code)
                distances.append(distance)
            
            hierarchical_metrics["mean_hierarchical_distance"] = np.mean(distances)
            hierarchical_metrics["std_hierarchical_distance"] = np.std(distances)
            hierarchical_metrics["max_hierarchical_distance"] = np.max(distances)
            
            # Precisão hierárquica
            h_precision_scores = []
            h_recall_scores = []
            
            for true_code, pred_code in zip(true_codes, pred_codes):
                true_path = self._get_hierarchical_path(true_code)
                pred_path = self._get_hierarchical_path(pred_code)
                
                intersection = len(set(true_path) & set(pred_path))
                
                if pred_path:
                    h_precision = intersection / len(pred_path)
                    h_precision_scores.append(h_precision)
                else:
                    h_precision_scores.append(0.0)
                
                if true_path:
                    h_recall = intersection / len(true_path)
                    h_recall_scores.append(h_recall)
                else:
                    h_recall_scores.append(0.0)
            
            hierarchical_metrics["hierarchical_precision"] = np.mean(h_precision_scores) if h_precision_scores else 0.0
            hierarchical_metrics["hierarchical_recall"] = np.mean(h_recall_scores) if h_recall_scores else 0.0
            
            # F1 hierárquico
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
        
        # Encontrar ancestral comum
        common_length = 0
        for p1, p2 in zip(path1, path2):
            if p1 == p2:
                common_length += 1
            else:
                break
        
        # Distância = profundidade total - 2 * profundidade comum
        return len(path1) + len(path2) - 2 * common_length
    
    def _get_hierarchical_path(self, code):
        """Obtém caminho hierárquico para um código"""
        if not code or not isinstance(code, str) or '.' not in code:
            return [code] if code else []
        
        parts = code.split('.')
        path = []
        
        for i in range(1, len(parts) + 1):
            path.append('.'.join(parts[:i]))
        
        return path
    
    def _calculate_descriptive_stats(self, df, output_dir, pred_col_name="Predicted label"):
        """Calcula estatísticas descritivas sem labels verdadeiros"""
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        stats = {}
        
        if pred_col_name in df.columns:
            predictions = df[pred_col_name]
            
            stats["total_sequences"] = len(df)
            stats["unique_predictions"] = len(predictions.unique())
            stats["prediction_distribution"] = predictions.value_counts().to_dict()
            stats["most_common_prediction"] = predictions.mode().iloc[0] if len(predictions) > 0 else "N/A"
            
            stats_file = output_path / "descriptive_stats.json"
            with open(stats_file, 'w') as f:
                json.dump(stats, f, indent=2)
            
            print(f"📊 Estatísticas descritivas salvas em: {stats_file}")
        
        else:
             print(f"⚠️ Não foi possível calcular estatísticas descritivas (coluna '{pred_col_name}' não encontrada).")
             stats["error"] = "Prediction column not found"

        return stats
    
    def _save_metrics(self, metrics, output_dir):
        """Salva métricas em formato JSON"""
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        json_metrics = {}
        for key, value in metrics.items():
            if isinstance(value, np.ndarray):
                json_metrics[key] = value.tolist()
            elif isinstance(value, (np.int64, np.float64, np.float32, np.int32)):
                json_metrics[key] = float(value)
            elif isinstance(value, Path):
                json_metrics[key] = str(value)
            elif isinstance(value, pd.Timestamp):
                 json_metrics[key] = value.isoformat()
            else:
                json_metrics[key] = value
        
        metrics_file = output_path / "detailed_metrics.json"
        try:
            with open(metrics_file, 'w') as f:
                json.dump(json_metrics, f, indent=2)
        except TypeError as e:
            print(f"⚠️ Erro ao serializar 'detailed_metrics.json': {e}")
            safe_metrics = json_metrics.copy()
            if 'per_class_metrics' in safe_metrics:
                del safe_metrics['per_class_metrics']
            if 'confusion_matrix' in safe_metrics:
                 del safe_metrics['confusion_matrix']
            if 'confusion_matrix_labels' in safe_metrics:
                 del safe_metrics['confusion_matrix_labels']
            try:
                with open(metrics_file, 'w') as f:
                    json.dump(safe_metrics, f, indent=2)
            except Exception as e2:
                 print(f"❌ Falha total ao salvar 'detailed_metrics.json': {e2}")

        summary = {
            "accuracy": json_metrics.get("accuracy", 0.0),
            "precision_macro": json_metrics.get("precision_macro", 0.0),
            "recall_macro": json_metrics.get("recall_macro", 0.0),
            "f1_macro": json_metrics.get("f1_macro", 0.0),
            "specificity_macro": json_metrics.get("specificity_macro", 0.0),
            "youdens_j": json_metrics.get("youdens_j", 0.0),
            "hierarchical_f1": json_metrics.get("hierarchical_f1", "not_available"),
            "total_samples": json_metrics.get("total_samples", 0),
            "num_classes": json_metrics.get("num_classes", 0)
        }
        
        summary_file = output_path / "metrics_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
    
    def _generate_detailed_report(self, y_true, y_pred, metrics, output_dir):
        """Gera relatório detalhado em texto"""
        
        output_path = Path(output_dir)
        report_file = output_path / "evaluation_report.txt"
        
        with open(report_file, 'w') as f:
            f.write("=" * 80 + "\n")
            f.write(f"RELATÓRIO DE AVALIAÇÃO - ELEMENTOS TRANSPONÍVEIS\n")
            f.write(f"Arquivo de predições: {output_path.parent.name}/{output_path.name}\n")
            f.write("=" * 80 + "\n\n")
            
            f.write("RESUMO EXECUTIVO\n")
            f.write("-" * 40 + "\n")
            f.write(f"Total de sequências: {metrics.get('total_samples', 'N/A')}\n")
            f.write(f"Número de classes (Verdadeiro): {metrics.get('num_classes', 'N/A')}\n")
            f.write(f"Número de classes (Predito): {metrics.get('num_predicted_classes', 'N/A')}\n")
            f.write(f"Acurácia geral: {metrics.get('accuracy', 0.0):.4f}\n")
            f.write(f"F1-Score (macro): {metrics.get('f1_macro', 0.0):.4f}\n")
            
            h_f1 = metrics.get('hierarchical_f1', 'not_available')
            if h_f1 != 'not_available':
                f.write(f"F1-Score hierárquico: {h_f1:.4f}\n")
            
            f.write(f"Youden's J Statistic: {metrics.get('youdens_j', 0.0):.4f}\n\n")
            
            f.write("MÉTRICAS PADRÃO\n")
            f.write("-" * 40 + "\n")
            f.write(f"Acurácia: {metrics.get('accuracy', 0.0):.4f}\n")
            f.write(f"Precisão (macro): {metrics.get('precision_macro', 0.0):.4f}\n")
            f.write(f"Precisão (micro): {metrics.get('precision_micro', 0.0):.4f}\n")
            f.write(f"Precisão (weighted): {metrics.get('precision_weighted', 0.0):.4f}\n")
            f.write(f"Recall (macro): {metrics.get('recall_macro', 0.0):.4f}\n")
            f.write(f"Recall (micro): {metrics.get('recall_micro', 0.0):.4f}\n")
            f.write(f"Recall (weighted): {metrics.get('recall_weighted', 0.0):.4f}\n")
            f.write(f"F1-Score (macro): {metrics.get('f1_macro', 0.0):.4f}\n")
            f.write(f"F1-Score (micro): {metrics.get('f1_micro', 0.0):.4f}\n")
            f.write(f"F1-Score (weighted): {metrics.get('f1_weighted', 0.0):.4f}\n")
            f.write(f"Especificidade (macro): {metrics.get('specificity_macro', 0.0):.4f}\n\n")
            
            f.write("MÉTRICAS AVANÇADAS\n")
            f.write("-" * 40 + "\n")
            
            auroc = metrics.get('auroc_macro', 'not_available')
            if auroc != 'not_available':
                f.write(f"auROC (macro): {auroc:.4f}\n")
            else:
                f.write("auROC (macro): Não disponível\n")
            
            map_score = metrics.get('map_macro', 'not_available')
            if map_score != 'not_available':
                f.write(f"mAP (macro): {map_score:.4f}\n")
            else:
                f.write("mAP (macro): Não disponível\n")
            
            f.write(f"Youden's J Statistic: {metrics.get('youdens_j', 0.0):.4f}\n\n")
            
            if metrics.get('hierarchical_f1') != 'not_available':
                f.write("MÉTRICAS HIERÁRQUICAS\n")
                f.write("-" * 40 + "\n")
                f.write(f"Precisão hierárquica: {metrics.get('hierarchical_precision', 0.0):.4f}\n")
                f.write(f"Recall hierárquico: {metrics.get('hierarchical_recall', 0.0):.4f}\n")
                f.write(f"F1-Score hierárquico: {metrics.get('hierarchical_f1', 0.0):.4f}\n")
                f.write(f"Distância hierárquica média: {metrics.get('mean_hierarchical_distance', 0.0):.4f}\n")
                f.write(f"Distância hierárquica máxima: {metrics.get('max_hierarchical_distance', 0.0):.4f}\n\n")
            
            if 'per_class_metrics' in metrics:
                f.write("MÉTRICAS POR CLASSE\n")
                f.write("-" * 40 + "\n")
                
                try:
                    unique_labels = np.unique(np.concatenate([y_true, y_pred]))
                    report = classification_report(y_true, y_pred, zero_division=0, labels=unique_labels)
                    f.write(report)
                except Exception as e:
                    f.write(f"Erro ao gerar relatório por classe: {e}\n")
                    class_metrics = metrics['per_class_metrics']
                    for class_name, class_data in class_metrics.items():
                        if isinstance(class_data, dict) and 'precision' in class_data:
                            f.write(f"\nClasse: {class_name}\n")
                            f.write(f"  F1-Score: {class_data.get('f1-score', 0.0):.4f}\n")
                            f.write(f"  Suporte: {class_data.get('support', 0)}\n")

        
        print(f"📄 Relatório detalhado salvo em: {report_file}")


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
    
    print(f"\n✅ Avaliação concluída!")
    print(f"📁 Resultados salvos em: {output_dir}")


if __name__ == "__main__":
    main()
