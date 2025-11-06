import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import itertools

import time
import datetime
from sklearn.metrics import roc_auc_score, average_precision_score
from sklearn.preprocessing import label_binarize
from sklearn import metrics as sk_m
from typing import List

class Metric:
    def __init__(self,
                 labels: List[int], 
                 predictions: List[int], 
                 classes: List[str]=[], 
                 f_beta: float=1.0, 
                 cm: List[List[int]]=[], 
                 output_dir: str='./Outputs', 
                 filename_prefix: str=''):
        self.labels = labels
        self.predictions = predictions
        self.output_dir=output_dir
        self.filename_prefix=filename_prefix
        self.f_beta = f_beta
        if cm == []:
            self.cm = sk_m.confusion_matrix(self.labels, self.predictions)
        else:
            self.cm = cm

        self.tp = self.cm.diagonal()
        self.fp = sum(self.cm) - self.tp
        self.fn = sum(np.transpose(self.cm)) - self.tp
        self.tn = sum(sum(self.cm)) - (self.tp + self.fp + self.fn)

        self.n = len(self.tp)
        if classes != []:
            self.classes = classes
        else:
            self.classes = [f'Class {i}' for i in range(self.n)]
        self.num_classes = len(self.classes)

        self.sum_tp = sum(self.tp)
        self.sum_fp = sum(self.fp)
        self.sum_fn = sum(self.fn)
        self.sum_tn = sum(self.tn)

        self.accuracies = (self.tp + self.tn)/(self.tp + self.tn + self.fp + self.fn + 1e-9) * 1.0
        self.accuracy_M = sum(self.accuracies)/self.n * 1.0
        self.accuracy_m = (self.sum_tp + self.sum_tn)/(self.sum_tp + self.sum_tn + self.sum_fp + self.sum_fn + 1e-9) * 1.0
        self.accuracy = sum(self.tp)/(sum(sum(self.cm)) + 1e-9)*1.0

        self.error_rates = (self.fp + self.fn)/(self.tp + self.tn + self.fp + self.fn + 1e-9)*1.0
        self.error_rate_M = sum(self.error_rates)/self.n * 1.0
        self.error_rate_m = (self.sum_fp + self.sum_fn)/(self.sum_tp + self.sum_fp + self.sum_fn + self.sum_tn + 1e-9) * 1.0

        self.precisions = (self.tp)/(self.tp + self.fp + 1e-9) * 1.0
        self.precision_M = sum(self.precisions)/self.n*1.0
        self.precision_m = self.sum_tp/(self.sum_tp + self.sum_fp + 1e-9) * 1.0

        self.recalls = (self.tp)/(self.tp + self.fn + 1e-9) * 1.0
        self.recall_M = sum(self.recalls)/self.n*1.0
        self.recall_m = self.sum_tp/(self.sum_tp + self.sum_fn + 1e-9)

        self.fscores = (self.f_beta**2 + 1.0)*self.precisions*self.recalls/((self.f_beta**2)*self.precisions + self.recalls + 1e-9)
        self.fscore_M = (self.f_beta**2+1.0)*self.precision_M*self.recall_M/((self.f_beta**2)*self.precision_M + self.recall_M + 1e-9)
        self.fscore_m = (self.f_beta**2+1.0)*self.precision_m*self.recall_m/((self.f_beta**2)*self.precision_m + self.recall_m + 1e-9)

        self.specificity = (self.tn)/(self.tn+self.fp + 1e-9)*1.0
        self.specificity_M = sum(self.specificity)/self.n*1.0
        self.specificity_m = self.sum_tn/(self.sum_tn + self.sum_fp + 1e-9)*1.0

        self.youdens_j = self.recalls + self.specificity - 1
        self.youdens_j_M = self.recall_M + self.specificity_M - 1

    def get_report(self):
        out = f'{"*" * 79}\n**{" " * 26} CLASSIFICATION REPORT {" " * 26}**\n{"*" * 79}\n'
        out += 'Confusion Matrix (row = true, column = predicted):\n'
        out += str(self.cm) + '\n'
        out += '\nStatistics:\n'
        
        # --- LINHA CORRIGIDA ---
        # Removido o apóstrofo de "Youden's J" para "Youdens J"
        out += f'{"Classes":<15s} {"Accuracy":>10s} {"Error":>10s} {"Precision":>10s} {"Recall":>10s} {"Specificity":>12s} {"F1-score":>10s} {"Youdens J":>12s}\n'
        # --- FIM DA CORREÇÃO ---
        
        for i in range(self.n):
            out += f'{self.classes[i]:<15s} {self.accuracies[i]:10.3f} {self.error_rates[i]:10.3f} {self.precisions[i]:10.3f} {self.recalls[i]:10.3f} {self.specificity[i]:12.3f} {self.fscores[i]:10.3f} {self.youdens_j[i]:12.3f}\n'
        out += f'\n{"Macro mean":<15s} {self.accuracy_M:10.3f} {self.error_rate_M:10.3f} {self.precision_M:10.3f} {self.recall_M:10.3f} {self.specificity_M:12.3f} {self.fscore_M:10.3f} {self.youdens_j_M:12.3f}\n'
        out += f'{"Micro mean":<15s} {self.accuracy_m:10.3f} {self.error_rate_m:10.3f} {self.precision_m:10.3f} {self.recall_m:10.3f} {self.specificity_m:12.3f} {self.fscore_m:10.3f}\n'
        out += f'{"Accuracy*":<15s} {self.accuracy:10.3f}\n'
        return out

    def get_advanced_report_str(self, y_pred_proba: np.ndarray):
        out = f'\n{"*" * 79}\n**{" " * 23} ADVANCED EVALUATION METRICS {" " * 23}**\n{"*" * 79}\n'
        y_true_binarized = label_binarize(self.labels, classes=range(self.num_classes))
        try:
            auroc_macro_ovr = roc_auc_score(y_true_binarized, y_pred_proba, multi_class='ovr', average='macro')
            out += f'Area Under ROC Curve (auROC, macro OVR): {auroc_macro_ovr:.4f}\n'
        except ValueError as e:
            out += f"Não foi possível calcular o auROC: {e}\n"
        try:
            map_score = average_precision_score(y_true_binarized, y_pred_proba, average='macro')
            out += f"Mean Average Precision (mAP, macro):       {map_score:.4f}\n"
        except ValueError as e:
            out += f"Não foi possível calcular o mAP: {e}\n"
        return out

    def save_report(self):
        report_str = self.get_report()
        time_str = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        with open(f'{self.output_dir}/PR_{self.filename_prefix}_{time_str}.txt', 'w+') as f:
            f.write(report_str)

    def save_confusion_matrix(self, normalize=False, title='Confusion Matrix', cmap=plt.cm.Blues):
        cm = np.array([[i for i in j] for j in self.cm])
        if normalize: cm = cm.astype('float') / (cm.sum(axis=1)[:, np.newaxis] + 1e-9)
        data = [[self.classes[i], self.classes[j], cm[i,j]] for i in range(self.num_classes) for j in range(self.num_classes)]
        df = pd.DataFrame(data, columns=['True','Predicted','Amount'])
        df = df.pivot(index='True', columns='Predicted', values='Amount')
        plt.figure(figsize=(12,12))
        plt.subplots_adjust(left=0.2, bottom=0.25, right=0.98, top=0.92)
        heatmap = sns.heatmap(df, annot=True, cmap=cmap, fmt='.2f' if normalize else 'd')
        heatmap.set_title(title)
        heatmap.set_xticklabels(heatmap.get_xticklabels(), rotation=45, horizontalalignment='right')
        heatmap.set_yticklabels(heatmap.get_yticklabels(), rotation=0, horizontalalignment='right')
        plt.savefig(f'{self.output_dir}/CM_{self.filename_prefix}_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.png')
        plt.clf()
        plt.close('all')

    def save_learning_curve(self,accuracies,title,acc_type=0):
        acc_type_axis_titles = ['Accuracy(micro)','Accuracy(macro)','Accuracy']
        plt.figure()
        plt.plot([e[0] for e in accuracies],[e[acc_type+1] for e in accuracies])
        plt.title(title)
        plt.xlabel('Epochs')
        plt.ylabel(acc_type_axis_titles[acc_type])
        plt.savefig(f'{self.output_dir}/LC_{self.filename_prefix}_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.png')
        plt.clf()
        plt.close('all')
