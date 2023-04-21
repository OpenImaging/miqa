#!/usr/bin/env python3

import pandas as pd
from sklearn.metrics import confusion_matrix

df = pd.read_csv('M:/MIQA/data.csv')  # manually converted TRUE/FALSE into 1/0
print(f'count NaN: {df.isnull().sum().sum()}')
correlation_df = df.corr()
correlation_df.to_csv('M:/MIQA/correlations2.csv')
print(correlation_df)

cm = pd.DataFrame(confusion_matrix(df['overall_qa_assessment'], df['cnr']))
cm.to_csv('M:/MIQA/oQA_CNR.csv')
print(cm)

cm = pd.DataFrame(confusion_matrix(df['overall_qa_assessment'], df['snr']))
cm.to_csv('M:/MIQA/oQA_SNR.csv')
print(cm)

# df = pd.read_csv('M:/MIQA/PredictHD_small/phenotype/bids_image_qc_information.tsv', sep='\t')
# df = df.drop(columns=['participant_id', 'session_id', 'series_number'])
# df.to_csv('M:/MIQA/dataQA.csv')
# print(f"count NaN: {df.isnull().sum().sum()}")
# correlation_df = df.corr()
# correlation_df.to_csv('M:/MIQA/correlations.csv')
# print(correlation_df)
