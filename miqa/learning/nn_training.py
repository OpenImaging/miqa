#!/usr/bin/env python3
import argparse
import logging
import math
import os
from pathlib import Path
import sys

import itk
import monai
from nn_inference import (
    artifacts,
    evaluate1,
    evaluate_model,
    get_model,
    regression_count,
)
import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix
import torch
from torch.utils.data import DataLoader
from torch.utils.tensorboard import SummaryWriter
import torchio
import wandb

logger = logging.getLogger(__name__)

existing_count = 0
missing_count = 0
predict_hd_data_root = 'P:/PREDICTHD_BIDS_DEFACE/'

# counts of different QA results is used to calculate class weights
qa_sample_counts = [
    374,  # number of samples with qa==0
    19,
    25,
    7,
    19,
    11,
    2903,
    521,
    2398,
    1908,
    1290,  # number of samples with qa==10
]


def get_image_dimension(path):
    image_io = itk.ImageIOFactory.CreateImageIO(path, itk.CommonEnums.IOFileMode_ReadMode)
    dim = (0, 0, 0)
    if image_io is not None:
        try:
            image_io.SetFileName(path)
            image_io.ReadImageInformation()
            assert image_io.GetNumberOfDimensions() == 3
            dim = (image_io.GetDimensions(0), image_io.GetDimensions(1), image_io.GetDimensions(2))
        except RuntimeError:
            pass
    return dim


def recursively_search_images(images, decisions, path_prefix, kind):
    count = 0
    for path in Path(path_prefix).rglob('*.nii.gz'):
        images.append(str(path))
        decisions.append(kind)
        count += 1
    logger.info(f'{count} images in prefix {path_prefix}')


def construct_path_from_csv_fields(
    participant_id, session_id, series_type, series_number, overall_qa_assessment
):
    sub_num = 'sub-' + str(participant_id).zfill(6)
    ses_num = 'ses-' + str(session_id)
    run_num = 'run-' + str(series_number).zfill(3)
    scan_type = 'PD'
    if series_type[0] == 'T':  # not PD
        scan_type = series_type[0:2] + 'w'
    if overall_qa_assessment < 6:
        scan_type = 'BAD' + scan_type
    file_name = (
        predict_hd_data_root
        + sub_num
        + '/'
        + ses_num
        + '/anat/'
        + sub_num
        + '_'
        + ses_num
        + '_'
        + run_num
        + '_'
        + scan_type
        + '.nii.gz'
    )
    return file_name


def does_file_exist(file_name):
    my_file = Path(file_name)
    global existing_count
    global missing_count
    if my_file.is_file():
        existing_count += 1
        return True
    else:
        missing_count += 1
        return False


def read_and_normalize_data_frame(tsv_path):
    df = pd.read_csv(tsv_path, sep='\t')
    df['file_path'] = df.apply(
        lambda row: construct_path_from_csv_fields(
            row['participant_id'],
            row['session_id'],
            row['series_type'],
            row['series_number'],
            row['overall_qa_assessment'],
        ),
        axis=1,
    )
    global existing_count
    global missing_count
    existing_count = 0
    missing_count = 0
    df['exists'] = df.apply(lambda row: does_file_exist(row['file_path']), axis=1)
    df['dimensions'] = df.apply(lambda row: get_image_dimension(row['file_path']), axis=1)
    logger.info(f'Existing files: {existing_count}, non-existent files: {missing_count}')
    return df


def verify_images(data_frame):
    all_ok = True
    for index, row in data_frame.iterrows():
        try:
            dim = get_image_dimension(row.file_path)
            if dim == (0, 0, 0):
                logger.info(f'{index}: size of {row.file_path} is zero')
                all_ok = False
        except Exception as e:
            logger.info(f'{index}: there is some problem with: {row.file_path}:\n{e}')
            all_ok = False
    return all_ok


class CombinedLoss(torch.nn.Module):
    def __init__(self, binary_class_weights, focal_loss=None):
        if focal_loss is None:
            focal_loss = monai.losses.FocalLoss()
        super().__init__()
        self.binary_class_weights = binary_class_weights
        self.focal_loss = focal_loss
        self.presence_count = binary_class_weights.shape[-1]  # indicators of presence of artifacts

    def forward(self, output, target):
        assert output.shape == target.shape, "output & target size don't match"
        assert output.shape[-1] == regression_count + self.presence_count

        qa_out = output[..., 0]
        qa_target = target[..., 0]
        qa_loss = torch.mean((qa_out - qa_target) ** 2)

        # overall QA is more important than individual artifacts
        loss = 10 * qa_loss

        for i in range(self.presence_count):
            i_target = target[..., i + regression_count]
            if i_target != -1:
                i_output = output[..., i + regression_count]
                # make them required dimension (1D -> 2D)
                i_output2 = i_output.unsqueeze(0)
                i_target2 = i_target.unsqueeze(0)
                raw_loss = self.focal_loss(i_output2, i_target2)
                if i_target == 1:
                    loss += raw_loss * self.binary_class_weights[i]
                else:
                    loss += raw_loss * (1 - self.binary_class_weights[i])
            # if target is -1 then ignore difference because ground truth was missing

        return loss


def convert_bool_to_int(value: bool):
    if value is True:
        return 1
    elif value is False:
        return 0
    else:  # NaN
        return -1


def create_train_and_test_data_loaders(df, count_train):
    images = []
    regression_targets = []
    sizes = {}
    artifact_column_indices = [df.columns.get_loc(c) + 1 for c in artifacts if c in df]
    for row in df.itertuples():
        try:
            exists = row.exists
        except AttributeError:
            exists = True  # assume that it exists by default
        if exists:
            images.append(row.file_path)

            row_targets = [row.overall_qa_assessment]
            for i in range(len(artifacts)):
                artifact_value = row[artifact_column_indices[i]]
                converted_result = convert_bool_to_int(artifact_value)
                row_targets.append(converted_result)
            regression_targets.append(row_targets)

            try:
                size = row.dimensions
                if size not in sizes:
                    sizes[size] = 1
                else:
                    sizes[size] += 1
            except AttributeError:
                pass

    ground_truth = np.asarray(regression_targets)
    count_val = df.shape[0] - count_train
    train_files = [
        torchio.Subject({'img': torchio.ScalarImage(img), 'info': info})
        for img, info in zip(images[:count_train], ground_truth[:count_train])
    ]
    val_files = [
        torchio.Subject({'img': torchio.ScalarImage(img), 'info': info})
        for img, info in zip(images[-count_val:], ground_truth[-count_val:])
    ]

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    # calculate class weights
    class_count = len(artifacts)
    count0 = [0] * class_count
    count1 = [0] * class_count
    for s in range(count_train):
        for i in range(class_count):
            if regression_targets[s][i + regression_count] == 0:
                count0[i] += 1
            elif regression_targets[s][i + regression_count] == 1:
                count1[i] += 1
            # else ignore the missing data

    weights_array = np.zeros(class_count)
    for i in range(class_count):
        weights_array[i] = count0[i] / (count0[i] + count1[i])
    logger.info(f'weights_array: {weights_array}')
    class_weights = torch.tensor(weights_array, dtype=torch.float).to(device)

    qa_weights = [1000.0 / qa_sample_counts[t] for t in range(11)]
    samples_weights = []
    for s in range(count_train):
        weight = qa_weights[int(regression_targets[s][0])]
        samples_weights.append(weight)

    samples_weight = torch.from_numpy(np.array(samples_weights)).double()
    sampler = torch.utils.data.WeightedRandomSampler(samples_weight, count_train)

    rescale = torchio.RescaleIntensity(out_min_max=(0, 1))

    # create a training data loader
    train_ds = torchio.SubjectsDataset(train_files, transform=rescale)
    train_loader = DataLoader(
        train_ds, batch_size=1, sampler=sampler, num_workers=4, pin_memory=torch.cuda.is_available()
    )

    # create a validation data loader
    val_ds = torchio.SubjectsDataset(val_files, transform=rescale)
    val_loader = DataLoader(
        val_ds, batch_size=1, num_workers=4, pin_memory=torch.cuda.is_available()
    )

    return train_loader, val_loader, class_weights, sizes


def train_and_save_model(df, count_train, save_path, num_epochs, val_interval, only_evaluate):
    train_loader, val_loader, class_weights, sizes = create_train_and_test_data_loaders(
        df, count_train
    )

    pretrained_path = os.path.join(os.getcwd(), 'pretrained.pth')
    if os.path.exists(save_path) and only_evaluate:
        model = get_model(save_path)
    elif os.path.exists(pretrained_path):
        model = get_model(pretrained_path)
    else:
        model = get_model()

    loss_function = CombinedLoss(class_weights)
    wandb.config.learning_rate = 9e-5
    optimizer = torch.optim.AdamW(model.parameters(), wandb.config.learning_rate)
    scheduler = torch.optim.lr_scheduler.ExponentialLR(optimizer, gamma=0.90)
    wandb.watch(model)

    # start a typical PyTorch training
    best_metric = float('-inf')
    best_metric_epoch = -1
    writer = SummaryWriter(log_dir=wandb.run.dir)

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    if only_evaluate:
        logger.info('Evaluating NN model on validation data')
        evaluate_model(model, val_loader, device, writer, 0, 'val')
        logger.info('Evaluating NN model on training data')
        evaluate_model(model, train_loader, device, writer, 0, 'train')
        return sizes

    _, file_name = os.path.split(save_path)

    for epoch in range(num_epochs):
        logger.info('-' * 25)
        logger.info(f'epoch {epoch + 1}/{num_epochs}')
        model.train()
        epoch_loss = 0
        step = 0
        epoch_len = len(train_loader.dataset) // train_loader.batch_size
        logger.info(f'epoch_len: {epoch_len}')
        y_true = []
        y_pred = []

        for batch_data in train_loader:
            step += 1
            inputs = batch_data['img'][torchio.DATA].to(device)
            info = batch_data['info'].to(device)
            optimizer.zero_grad()
            outputs = model(inputs)

            y_true.extend(info[..., 0].cpu().tolist())
            y = outputs[..., 0].cpu().tolist()
            y = [int(round(y[t])) for t in range(len(y))]
            y = [max(0, min(y[t], 10)) for t in range(len(y))]  # clamp to 0 - 10 range
            y_pred.extend(y)

            loss = loss_function(outputs, info)
            loss.backward()
            optimizer.step()
            epoch_loss += loss.item()
            logger.debug(f'{step}:{loss.item():.4f}')
            print('.', end='', flush=True)
            if step % 100 == 0:
                print('', flush=True)  # new line
            writer.add_scalar('train_loss', loss.item(), epoch_len * epoch + step)
            wandb.log({'train_loss': loss.item()})
        epoch_loss /= step
        logger.info(f'\nepoch {epoch + 1} average loss: {epoch_loss:.4f}')
        wandb.log({'epoch average loss': epoch_loss})
        epoch_cm = confusion_matrix(y_true, y_pred)
        logger.info(f'confusion matrix:\n{epoch_cm}')
        wandb.log({'confusion matrix': epoch_cm})

        if (epoch + 1) % val_interval == 0:
            logger.info('Evaluating on validation set')
            metric = evaluate_model(model, val_loader, device, writer, epoch, 'val')

            if metric >= best_metric:
                best_metric = metric
                best_metric_epoch = epoch + 1
                torch.save(model.state_dict(), save_path)

                torch.save(model.state_dict(), os.path.join(wandb.run.dir, file_name))
                logger.info(f'saved new best metric model as {save_path}')

            logger.info(
                'current epoch: {} current metric: {:.2f} best metric: {:.2f} at epoch {}'.format(
                    epoch + 1, metric, best_metric, best_metric_epoch
                )
            )

            scheduler.step()
            logger.info(f'Learning rate after epoch {epoch + 1}: {optimizer.param_groups[0]["lr"]}')
            wandb.log({'learn_rate': optimizer.param_groups[0]['lr']})

    epoch_suffix = '.epoch' + str(num_epochs)
    torch.save(model.state_dict(), save_path + epoch_suffix)
    torch.save(model.state_dict(), os.path.join(wandb.run.dir, file_name + epoch_suffix))

    logger.info(f'train completed, best_metric: {best_metric:.2f} at epoch: {best_metric_epoch}')
    writer.close()
    return sizes


def process_folds(folds_prefix, validation_fold, evaluate_only, fold_count):
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    wandb.init(project='miqaT1', sync_tensorboard=True)

    folds = []
    for f in range(fold_count):
        csv_name = folds_prefix + f'{f}.csv'
        fold = pd.read_csv(csv_name)
        logger.info(f'Verifying input data integrity of {csv_name}')
        if not verify_images(fold):
            logger.info('Data verification failed. Exiting...')
            return
        folds.append(fold)

    df = pd.concat(folds, ignore_index=True)
    logger.info(df)

    logger.info(f'Using fold {validation_fold} for validation')
    vf = folds.pop(validation_fold)
    folds.append(vf)
    df = pd.concat(folds, ignore_index=True)

    # we should have at least 10k optimization steps and at least 20 epochs
    val_count = max(1, int(600 / df.shape[0]))
    epoch_count = max(15, int(30000 / df.shape[0]))
    epoch_count = math.ceil(epoch_count / val_count) * val_count

    count_train = df.shape[0] - vf.shape[0]
    model_path = os.getcwd() + f'/models/miqaT1-val{validation_fold}.pth'
    sizes = train_and_save_model(
        df,
        count_train,
        save_path=model_path,
        num_epochs=epoch_count,
        val_interval=val_count,
        only_evaluate=evaluate_only,
    )

    logger.info('Image size distribution:\n' + str(sizes))


if __name__ == '__main__':
    log_level = os.environ.get('LOGLEVEL', 'WARNING').upper()
    logging.basicConfig(level=log_level)

    parser = argparse.ArgumentParser()
    parser.add_argument('--predicthd', '-p', help='Path to PredictHD data', type=str)
    parser.add_argument('--ncanda', '-n', help='Path to NCANDA data', type=str)
    parser.add_argument('--folds', '-f', help='Prefix to folds CSVs', type=str)
    parser.add_argument(
        '--vfold', '-v', help='Which fold to use for validation', type=int, default=2
    )
    parser.add_argument('--nfolds', '-c', help='Number of folds', type=int, default=3)
    # add bool for evaluation
    parser.add_argument('--evaluate', dest='evaluate', action='store_true')
    parser.add_argument('-e', dest='evaluate', action='store_true')
    parser.add_argument('--train', dest='evaluate', action='store_false')
    parser.add_argument('-t', dest='evaluate', action='store_false')
    parser.set_defaults(evaluate=False)
    # add bool for full cross-validation
    parser.add_argument('--all', dest='all', action='store_true')
    parser.set_defaults(all=False)
    # add option to evaluate on just one image
    parser.add_argument('--evaluate1', '-1', help='Path to an image to evaluate', type=str)
    parser.add_argument('--modelfile', '-m', help='Path to neural network model weights', type=str)

    args = parser.parse_args()
    logger.info(args)

    monai.config.print_config()

    if args.all:
        logger.info(f'Training {args.nfolds} folds')
        for f in range(args.nfolds):
            process_folds(args.folds, f, False, args.nfolds)
        # evaluate all at the end, so results are easy to pick up from the log
        for f in range(args.nfolds):
            process_folds(args.folds, f, True, args.nfolds)
    elif args.folds is not None:
        process_folds(args.folds, args.vfold, args.evaluate, args.nfolds)
    elif args.modelfile is not None and args.evaluate1 is not None:
        evaluate1(get_model(args.modelfile), args.evaluate1)
    elif args.predicthd is not None:
        predict_hd_data_root = args.predicthd
        df = read_and_normalize_data_frame(
            predict_hd_data_root + r'phenotype/bids_image_qc_information.tsv'
        )
        logger.info(df)
        full_path = Path('bids_image_qc_information-customized.csv').absolute()
        df.to_csv(full_path, index=False)
        logger.info(f'CSV file written: {full_path}')
    elif args.ncanda is not None:
        logger.info('Adding support for NCANDA data is a TODO')
    else:
        logger.info('Not enough arguments specified')
        logger.info(parser.format_help())
