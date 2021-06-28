# MIQA Pixel-based classifier

## Get the program
```shell
mkdir nn_work_dir
cd nn_work_dir
git clone git@github.com:OpenImaging/miqa.git
```
optionally create a python virtual environment
`python3 -m venv pyEnv` and activate it `source pyEnv/bin/activate` before installing required packages:
```shell
pip install -r ./miqa/learning/requirements.txt
```

## Get the data
For example, copy [PredictHD_small](https://drive.google.com/drive/u/1/folders/1SYY5LdKvU6fHgty1ynYXsVzqhGamsZmM) from the shared Google Drive into `nn_work_dir`, as well as files `T1_fold0.csv`, `T1_fold1.csv` and `T1_fold2.csv` from [Learning](https://drive.google.com/drive/u/1/folders/1uT24WMjZLt7IJWPXR-K7YYwiFUSomr_L).
Now edit the paths inside `T1_fold*.csv` files to match the path on your file system, e.g.:
```shell
sed -i 's+P:/PREDICTHD_BIDS_DEFACE/+/home/exampleUser/nn_work_dir/PredictHD_small/+g' T1_fold0.csv
sed -i 's+P:/PREDICTHD_BIDS_DEFACE/+/home/exampleUser/nn_work_dir/PredictHD_small/+g' T1_fold1.csv
sed -i 's+P:/PREDICTHD_BIDS_DEFACE/+/home/exampleUser/nn_work_dir/PredictHD_small/+g' T1_fold2.csv
```

## Run training
To run training on the 3-fold cross-validation using fold 0 as validation set and folds 1 and 2 as training set, use:
```shell
python ./miqa/learning/nn_classifier.py -f ./T1_fold -c 3 -v 0
```
This will produce a file called `miqa01-val0.pth`. To run full 3-fold cross validation, execute:
```shell
python ./miqa/learning/nn_classifier.py -f ./T1_fold -c 3 --all
```
This will produce `miqa01-val0.pth`, `miqa01-val1.pth` and `miqa01-val2.pth`.

## Run inference
To run inference on a single file, execute:
```shell
python ./miqa/learning/nn_classifier.py -m ./miqa01-val0.pth -1 ./PredictHD_small/sub-699312/ses-38845/anat/sub-699312_ses-38845_run-003_BADT1w.nii.gz
```
The above command uses the neural network weights produced by training on folds 1 and 2.

To run inference on one of the folds, e.g. fold 1, use:
```shell
python ./miqa/learning/nn_classifier.py -f ./T1_fold -c 3 -v 1 --evaluate
```
