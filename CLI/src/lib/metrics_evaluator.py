
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
        

        y_true = df["Actual_Label"].fillna("Unknown")
        y_pred = df["Predicted label"].fillna("Unknown")
        

        metrics = self._calculate_all_metrics(y_true, y_pred)
        

        self._save_metrics(metrics, output_dir)
        

        self._generate_detailed_report(y_true, y_pred, metrics, output_dir)
        
        return metrics
    
    def _calculate_all_metrics(self, y_true, y_pred):
        """Calcula todas as métricas padronizadas"""
        
        metrics = {}
        

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
        

        cm = confusion_matrix(y_true, y_pred)
        metrics["confusion_matrix"] = cm.tolist()
        

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
        """Salva métricas em formato JSON"""
        
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
        

        metrics_file = output_path / "detailed_metrics.json"
        with open(metrics_file, 'w') as f:
            json.dump(json_metrics, f, indent=2)
        

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
        
        summary_file = output_path / "metrics_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
    
    def _generate_detailed_report(self, y_true, y_pred, metrics, output_dir):
        """Gera relatório detalhado em texto"""
        
        output_path = Path(output_dir)
        report_file = output_path / "evaluation_report.txt"
        
        with open(report_file, 'w') as f:
            f.write("=" * 80 + "\n")
            f.write("RELATÓRIO DE AVALIAÇÃO - ELEMENTOS TRANSPONÍVEIS\n")
            f.write("=" * 80 + "\n\n")
            

            f.write("RESUMO EXECUTIVO\n")
            f.write("-" * 40 + "\n")
            f.write(f"Total de sequências: {metrics.get('total_samples', 'N/A')}\n")
            f.write(f"Número de classes: {metrics.get('num_classes', 'N/A')}\n")
            f.write(f"Acurácia geral: {metrics.get('accuracy', 0.0):.4f}\n")
            f.write(f"F1-Score (macro): {metrics.get('f1_macro', 0.0):.4f}\n")
            f.write(f"MCC (Matthews): {metrics.get('matthews_corrcoef', 0.0):.4f}\n")
            
            if metrics.get('hierarchical_f1') != 'not_available':
                f.write(f"F1-Score hierárquico: {metrics.get('hierarchical_f1', 0.0):.4f}\n")
            
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
            

            f.write("MÉTRICAS ROBUSTAS E AVANÇADAS\n")
            f.write("-" * 40 + "\n")
            
            f.write(f"Coeficiente Kappa de Cohen: {metrics.get('cohens_kappa', 0.0):.4f}\n")
            f.write(f"Coef. Correlação de Matthews (MCC): {metrics.get('matthews_corrcoef', 0.0):.4f}\n")
            f.write(f"Desvio Padrão F1 por Classe: {metrics.get('std_f1_per_class', 0.0):.4f} (Consistência)\n")
            
            auroc = metrics.get('auroc_macro', 'not_available')
            if auroc != 'not_available':
                f.write(f"auROC (macro): {auroc:.4f}\n")
            else:
                f.write("auROC (macro): Não disponível\n")
            
            map_score = metrics.get('map_macro', 'not_available')
            if map_score != 'not_available':
                f.write(f"mAP (macro): {map_score:.4f}\n\n")
            else:
                f.write("mAP (macro): Não disponível\n\n")
            

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
                
                class_metrics = metrics['per_class_metrics']
                for class_name, class_data in class_metrics.items():
                    if isinstance(class_data, dict) and 'precision' in class_data:
                        f.write(f"\nClasse: {class_name}\n")
                        f.write(f"  Precisão: {class_data.get('precision', 0.0):.4f}\n")
                        f.write(f"  Recall: {class_data.get('recall', 0.0):.4f}\n")
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