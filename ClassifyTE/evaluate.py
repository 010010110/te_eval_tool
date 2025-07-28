import numpy as np
import pandas as pd
import sys
import os
import csv
import time
import argparse
from optparse import OptionParser
from sklearn.linear_model import LogisticRegression

import pickle
from HierStack import hierarchy as hie
from HierStack import lcpnb as lcpnb
from HierStack import nllcpn as nllcpn
from HierStack.stackingClassifier import *

def getSequenceName(curr_dir, feature_folder):
    input_files_dir = os.path.join(curr_dir + feature_folder) + "/kanalyze-2.0.0/input_data/"
    _, _, files = next(os.walk(input_files_dir))
    files = sorted(files)
    seqIDs = []
    for file in files:
        with open(os.path.join(input_files_dir, file), "r") as f:
            header = f.readline()
            head = header.split(">")
            ID = head[1].strip()
            seqIDs.append(ID)
    return seqIDs

def getLabel(content, predicted):
    if predicted in content:
        return content[predicted].strip("\n")
    return ""

def getCodeLabel(lines):
    content = {}
    for line in lines:
        data = line.strip().split(",")
        if len(data) >= 2:
            code, label = data[0], data[1]
            content[code] = label
    return content

def evaluate_model(test_data, parent_classifiers, algorithm, h):
    labels_evaluate = []
    for i in range(len(test_data)):
        if algorithm == "lcpnb":
            c = lcpnb.lcpnb(h)
        elif algorithm == "nllcpn":
            c = nllcpn.nllcpn(h)
        predicted = c.classify(test_data.iloc[i].values.reshape(1, -1), parent_classifiers)
        labels_evaluate.append(predicted)
    return labels_evaluate

def main(h, data, algorithm, modelname):
    model_filepath = "models/"
    pkl_filename = modelname

    test_data = data.iloc[:, 0:(pow(4,2) + pow(4,3) + pow(4,4))]

    with open(model_filepath + pkl_filename, 'rb') as fb:
        parent_classifiers = pickle.load(fb)

    print("---------------------------Evaluation Started----------------------------\n")
    labels_test = evaluate_model(test_data, parent_classifiers, algorithm, h)
    return labels_test

if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option("-f", "--filename", dest="filename", default="feature_file.csv")
    parser.add_option("-d", "--featuredir", dest="feature_dir", default="feature")
    parser.add_option("-n", "--node_file", dest="node_file", default="node.txt")
    parser.add_option("-m", "--modelname", dest="modelname")
    parser.add_option("-a", "--algorithm", dest="algorithm", default='lcpnb')

    (options, args) = parser.parse_args()

    curr_dir1 = os.getcwd()
    dataset_filepath = os.path.join(curr_dir1, "data", options.filename)
    node_filepath = os.path.join(curr_dir1, "nodes", options.node_file)
    feature_folder = "/" + options.feature_dir

    seq_names = getSequenceName(curr_dir1, feature_folder)
    h = hie.hierarchy(node_filepath)

    start_time = time.time()

    data = pd.read_csv(dataset_filepath, low_memory=False)
    with open("./nodes/tree.txt", "r") as f:
        lines = f.readlines()
    content = getCodeLabel(lines)

    hier_label = main(h, data, options.algorithm, options.modelname)

    outputs_filepath = "outputs/"
    os.makedirs(outputs_filepath, exist_ok=True)
    outputs_filename = f"predicted_out_{options.feature_dir}.csv"
    outputs_txt = f"predicted_result_{options.feature_dir}.txt"

    with open(os.path.join(outputs_filepath, outputs_filename), 'w') as f_csv, \
         open(os.path.join(outputs_filepath, outputs_txt), 'w') as f_txt:

        f_csv.write("Sequence ID,Predicted label\n")
        f_txt.write("Prediction Results\n")

        for count, k in enumerate(hier_label):
            name = seq_names[count].strip()
            seq_id = name.split(" ")[0]

            predicted_label_code = k[-1] if k else ""
            predicted_label_name = getLabel(content, str(predicted_label_code))

            print(f"Prediction for TE sequence of ID: {name}")
            f_txt.write(f"Prediction for TE sequence of ID: {name}\n")

            for i in k:
                label = getLabel(content, str(i))
                print(f"Predicted level {i} : {label}")
                f_txt.write(f"Predicted level {i} : {label}\n")

            f_txt.write(f"Final label of TE sequence is {predicted_label_name}\n\n")
            f_txt.write("###############################################################\n\n")

            f_csv.write(f"{seq_id},{predicted_label_name}\n")
            print("\n###############################################################\n")

    elapsed_time = time.time() - start_time
    print("\nTotal time elapsed in seconds\t", elapsed_time)
